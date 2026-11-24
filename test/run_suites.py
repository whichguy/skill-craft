#!/usr/bin/env python3
"""Execute fixed hermetic suites selected from :mod:`suite_catalog`.

This runner intentionally owns process lifecycle, output receipts and catalog
coverage checks.  ``test/run-all.sh`` is its one public Bash entrypoint and only
forwards here, so it cannot drift into a separate inventory.  Up to ``--jobs``
suites run at once; their output and receipt records still appear one suite at
a time in catalog order.
"""

from __future__ import annotations

import argparse
from concurrent import futures
import contextlib
from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from typing import Callable, Iterable, Iterator, Sequence

import suite_catalog


ROOT = Path(__file__).resolve().parents[1]
# Assumptions behind running suites side by side (docs/local-validation-journal.md, round 1).  Each is guarded by the
# test named after it in test/test-groups.test.py; change one only together with its guard.
# - Every catalog suite is hermetic: its own process group, its own temporary directories, a private state home
#   (run_process), and no fixed port, shared path or global Git setting.  A suite that fails only beside others has a
#   test defect, which is fixed in that suite (journal F11, F16), not by running everything serially; `--jobs 1` is for
#   diagnosis.
# - No verdict depends on how fast a loaded machine runs.  Under --jobs every suite shares the CPU, so a time bound
#   inside a test needs generous headroom; a tight one fails under load (F11's 20 s hold) or when a Mac sleeps (F14).
# - A parallel run reports what a serial one reports: output, OK/FAIL lines and receipt records in catalog order, and
#   exit 1 if any suite failed (test_parallel_jobs_report_what_one_job_reports).
# - `--jobs 1` starts a suite only after the previous one is in the receipt
#   (test_execution_continues_after_failure_and_persists_incremental_receipt).
# - An interrupted parallel run stops the suites it started (test_an_interrupted_parallel_run_stops_the_suites_it_started).
# The cap below is a default for a shared machine, not a correctness bound: any N works.  Eight kept seven ShipLoop
# suites at 5.4 minutes against about 14 serially (2026-10-25); more mostly adds contention.
MAX_DEFAULT_JOBS = 8
DEFAULT_JOBS = min(os.cpu_count() or 1, MAX_DEFAULT_JOBS)
TOP_LEVEL_TEST_ALLOWLIST = frozenset({
    # Compatibility command; its three constituent suites are cataloged once each.
    "test/shiploop-e2e.test.py",
    # Explicit host-dependent checks are invoked through test/run-integration.sh.
    "test/advisors.test.sh",
    "test/cursor-imported-skills.test.sh",
    "test/review-plan.test.sh",
})
_TEST_SUFFIXES = (".test.py", ".test.sh", ".test.js", ".test.cjs")


class UsageParser(argparse.ArgumentParser):
    """Keep the established CLI's usage failures at EX_USAGE (64)."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(64, f"{self.prog}: error: {message}\n")


@dataclass
class ProcessOutcome:
    status: str
    returncode: int | None
    duration_seconds: float
    stdout: str
    stderr: str
    error: str | None = None


def _jobs(value: str) -> int:
    try:
        jobs = int(value)
    except ValueError:
        jobs = 0
    if jobs < 1:
        raise argparse.ArgumentTypeError(f"must be a positive integer: {value!r}")
    return jobs


def _parser() -> UsageParser:
    parser = UsageParser(
        prog="bash test/run-all.sh",
        description="Run a deduplicated union of fixed hermetic test groups.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Groups: " + ", ".join(suite_catalog.GROUPS) + "\n"
            "Use --output with a new directory outside the checkout to retain a "
            "selected/completed receipt and per-suite logs."
        ),
    )
    parser.add_argument("--group", action="append", metavar="GROUP",
                        help="repeatable group; unions are deduplicated in catalog order")
    parser.add_argument("--changed-from", metavar="REF",
                        help="with --group quick, quick-1, quick-2 or affected: also run the suites matching files changed since REF; "
                             "with --group prompt: also run the suites whose own files changed; "
                             "uncommitted and untracked files count")
    parser.add_argument("--jobs", type=_jobs, default=DEFAULT_JOBS, metavar="N",
                        help=f"run up to N suites at once (default: CPU count capped at {MAX_DEFAULT_JOBS}, "
                             f"here {DEFAULT_JOBS}); output and the receipt stay per suite in catalog order; "
                             "--jobs 1 runs one suite at a time")
    parser.add_argument("--list", action="store_true", help="list selected catalog entries without executing")
    parser.add_argument("--output", type=Path, help="new external receipt directory")
    return parser


def parse_args(argv: Sequence[str] | None = None) -> tuple[argparse.Namespace, tuple[str, ...]]:
    """Parse the one runner dialect without doing any work."""

    parser = _parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.list and args.output is not None:
        parser.error("--output cannot be used with --list")
    groups = tuple(args.group or ("all",))
    unknown = set(groups) - set(suite_catalog.GROUPS)
    if unknown:
        parser.error("unknown group: " + ", ".join(sorted(unknown)))
    if args.changed_from is not None and not {"quick", "quick-1", "quick-2", "prompt", "affected"} & set(groups):
        parser.error("--changed-from applies only to --group quick, quick-1, quick-2, prompt or affected")
    return args, groups


def changed_paths(root: Path, ref: str) -> tuple[str, ...]:
    """Paths changed since REF in the checkout, both sides of a rename included.

    Uncommitted and untracked files count, so a local run covers the edit being
    tested; a CI checkout is clean, where this equals REF..HEAD.
    """

    tracked = subprocess.check_output(
        ["git", "diff", "--no-renames", "--name-only", "-z", ref], cwd=root)
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=root)
    names = (p.decode("utf-8", "surrogateescape") for p in (tracked + untracked).split(b"\0") if p)
    return tuple(dict.fromkeys(names))


def _inside(path: Path, possible_parent: Path) -> bool:
    try:
        path.relative_to(possible_parent)
    except ValueError:
        return False
    return True


def prepare_output(path: Path, root: Path) -> Path:
    """Create only a new external receipt directory."""

    output = path.expanduser().resolve()
    checkout = root.resolve()
    if output.exists():
        raise ValueError("--output must name a new directory")
    if _inside(output, checkout):
        raise ValueError("--output must be outside the checkout")
    output.mkdir(parents=True)
    (output / "logs").mkdir()
    return output


def _fixed_top_level_tests(root: Path) -> set[str]:
    test_root = root / "test"
    if not test_root.is_dir():
        return set()
    return {
        path.relative_to(root).as_posix()
        for path in test_root.iterdir()
        if path.is_file() and path.name.endswith(_TEST_SUFFIXES)
    }


def catalog_omissions(root: Path, suites: Iterable[suite_catalog.Suite] = suite_catalog.SUITES) -> tuple[str, ...]:
    """Report missing fixed targets and unclassified top-level test files."""

    entries = tuple(suites)
    missing = [suite.path for suite in entries if not (root / suite.path).is_file()]
    cataloged_top_level = {
        suite.path for suite in entries
        if suite.path.startswith("test/") and "/" not in suite.path.removeprefix("test/")
    }
    unclassified = sorted(
        _fixed_top_level_tests(root) - cataloged_top_level - TOP_LEVEL_TEST_ALLOWLIST
    )
    return tuple([*(f"missing catalog target: {path}" for path in missing),
                  *(f"unclassified top-level test: {path}" for path in unclassified)])


def _read_command(argv: Sequence[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    except OSError as exc:
        return f"unavailable: {exc}"
    if result.returncode:
        return f"unavailable (exit {result.returncode}): {result.stderr.strip()}"
    return (result.stdout or result.stderr).strip()


def source_identity(root: Path) -> dict[str, object]:
    """Collect checkout evidence without mutating the checkout."""

    def git(*args: str) -> str | None:
        value = _read_command(("git", *args), root)
        return value if value and not value.startswith("unavailable") else None

    status = git("status", "--porcelain=v1")
    try:
        dirty = subprocess.run(
            ("git", "diff", "--binary", "HEAD"), cwd=root,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
        )
    except OSError:
        dirty_digest = None
    else:
        dirty_digest = hashlib.sha256(dirty.stdout).hexdigest() if dirty.returncode == 0 else None
    return {
        "head": git("rev-parse", "HEAD"),
        "tree": git("rev-parse", "HEAD^{tree}"),
        "status": status.splitlines() if status else [],
        "dirty_diff_sha256": dirty_digest,
    }


def runtime_versions(root: Path) -> dict[str, str | None]:
    """Record resolved local runtimes, never an arbitrary environment dump."""

    return {
        "python3": _read_command(("python3", "--version"), root),
        "node": _read_command(("node", "--version"), root),
        "bash": _read_command(("bash", "--version"), root),
    }


def _exit_probe() -> Callable[[int], bool]:
    """Observe child exit without reaping, including Darwin Python without os.waitid.

    Darwin's libc has waitid even where Python does not expose it. Its siginfo
    layout and constants below are Darwin ABI, not Linux values. No reaping
    fallback is safe: an unsupported POSIX host must fail before launch.
    """

    if all(hasattr(os, name) for name in ("waitid", "P_PID", "WEXITED", "WNOHANG", "WNOWAIT")):
        def exited(pid: int) -> bool:
            return os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
        return exited
    if sys.platform == "darwin":
        import ctypes

        class Siginfo(ctypes.Structure):
            _fields_ = [("signo", ctypes.c_int), ("error", ctypes.c_int),
                        ("code", ctypes.c_int), ("pid", ctypes.c_int),
                        ("uid", ctypes.c_uint), ("status", ctypes.c_int),
                        ("addr", ctypes.c_void_p), ("value", ctypes.c_void_p),
                        ("band", ctypes.c_long), ("pad", ctypes.c_ulong * 7)]

        if ctypes.sizeof(ctypes.c_void_p) != 8 or ctypes.sizeof(Siginfo) != 104:
            raise RuntimeError("unsupported Darwin siginfo ABI; refusing unsafe process ownership")
        waitid = ctypes.CDLL(None, use_errno=True).waitid
        waitid.argtypes = (ctypes.c_int, ctypes.c_uint, ctypes.POINTER(Siginfo), ctypes.c_int)
        waitid.restype = ctypes.c_int

        def exited(pid: int) -> bool:
            import errno
            info = Siginfo()
            while waitid(1, pid, ctypes.byref(info), 0x04 | 0x01 | 0x20) != 0:
                error = ctypes.get_errno()
                if error == errno.EINTR:
                    continue
                if error == errno.ECHILD:
                    raise ChildProcessError(error, os.strerror(error))
                raise OSError(error, os.strerror(error))
            return info.pid != 0
        return exited
    raise RuntimeError("waitid(WNOWAIT) unavailable; refusing unsafe process ownership")


# Capture the real base once: factory replacements must not turn inspection into
# another suite owner. Public on_start still receives the actual Popen subclass.
_PopenBase = subprocess.Popen
# Only the inspecting thread defers suite polls invoked by Popen._cleanup.
_inspection_state = threading.local()


def _darwin_zombie_only_group(pgid: int) -> bool:
    """Read numeric process state only; uncertainty is never evidence of cleanup.

    Caller retains the suite owner lock and its unreaped-child authority. The
    plain base Popen below has no owner hooks, callbacks or group cleanup. It
    still invokes global subprocess._cleanup during construction. A thread-local
    guard makes every suite _internal_poll defer before taking any owner lock,
    preventing recursive inspection and cross-owner lock inversion. A full
    numeric snapshot avoids ps legacy-mode group-selection ambiguity.
    """

    inspecting = getattr(_inspection_state, "active", False)
    _inspection_state.active = True
    try:
        observer = None
        output = None
        try:
            observer = _PopenBase(
                ['/bin/ps', '-A', '-o', 'pid=,pgid=,stat='],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, start_new_session=True,
                env={'LC_ALL': 'C', 'PATH': '/usr/bin:/bin'},
            )
            output, _ = observer.communicate(timeout=2)
            if observer.returncode != 0:
                output = None
        except Exception:
            output = None
        finally:
            if observer is not None:
                # Never signal a group here, nor use the suite cleanup machinery.
                # No context manager: its implicit wait could be unbounded.
                try:
                    if observer.returncode is None:
                        observer.kill()
                        observer.wait(timeout=2)
                except Exception:
                    output = None
                finally:
                    for stream in (observer.stdout, observer.stderr):
                        if stream is not None:
                            try:
                                stream.close()
                            except Exception:
                                output = None
    finally:
        _inspection_state.active = inspecting
    # No return from finally: an interrupt during inspection must still escape.
    if output is None or len(output) > 1024 * 1024:
        return False
    leader_seen = False
    seen = set()
    for row in output.splitlines():
        fields = row.split()
        if (len(fields) != 3 or not fields[0].isdigit()
                or not fields[1].isdigit()):
            return False
        pid, group = int(fields[0]), int(fields[1])
        if group != pgid:
            continue
        state = fields[2]
        # T (stopped), sleeping, running, exiting and unknown are not dead.
        # Only documented Z plus documented ps state modifiers is accepted.
        if (pid <= 0 or pid in seen or not state.startswith(b'Z')
                or any(c not in b'+<>AELNSsVWX' for c in state[1:])):
            return False
        seen.add(pid)
        leader_seen = leader_seen or pid == pgid
    return leader_seen


class _SuiteProcess(_PopenBase):
    """The actual Popen, with one lock covering every group signal and reap.

    communicate keeps its existing pipe/EOF/deadline semantics. Its waits and
    polls, and public callback wait/poll/terminate/kill calls, pass this owner.
    No callback or pipe read holds the ownership lock. Raw os.waitpid on this
    child (or mutating returncode) is outside the Popen callback contract.
    """

    def __init__(self, *args, **kwargs):
        self._owner_lock = threading.RLock()
        self._probe = _exit_probe() if os.name == "posix" else None
        self.cleanup_warnings: list[str] = []
        self._child_created = False
        self.pid = None
        self.returncode = None
        self.stdin = self.stdout = self.stderr = None
        self._constructor_failed = False
        try:
            # CPython's exec-error path calls waitpid directly, rather than
            # _internal_poll. Keep that real constructor reap under our lock.
            with self._owner_lock:
                super().__init__(*args, **kwargs)
        except BaseException:
            self._constructor_failed = True
            # The actual CPython base constructor initializes pid=None, then
            # publishes a positive pid only from fork_exec/posix_spawn's return,
            # before _child_created may be set. That returned child is authority
            # even if interruption precedes the flag. No callback runs here;
            # arbitrary callbacks or external pid mutation are outside this
            # private contract and provide no child-ownership authority.
            if isinstance(self.pid, int) and self.pid > 0:
                self._child_created = True
                try:
                    _abort_process(self)
                except BaseException:
                    _cleanup_diagnostic("suite constructor cleanup failed while preserving primary exception")
            raise

    def send_signal(self, sig):
        # Preserve Popen's leader-only public signal contract, but serialize
        # its implicit poll/reap and signal with the private group authority.
        with self._owner_lock:
            if not self._child_created or not isinstance(self.pid, int) or self.pid <= 0:
                return
            return super().send_signal(sig)

    def _signal_group(self, sig):
        with self._owner_lock:
            if (not self._child_created or not isinstance(self.pid, int)
                    or self.pid <= 0 or self.returncode is not None):
                return
            if os.name != "posix":
                return self.kill()
            # ECHILD is an ownership violation, not permission to signal a PID.
            exited = self._probe(self.pid)
            try:
                # An actual fork may precede setsid when construction fails.
                # In that case only the still-owned direct child is signalable.
                # Unknown getpgid/probe identity raises; never guess a group.
                if (self._constructor_failed and not exited
                        and os.getpgid(self.pid) != self.pid):
                    os.kill(self.pid, sig)
                else:
                    os.killpg(self.pid, sig)
            except ProcessLookupError:
                pass
            except PermissionError:
                # Historical Darwin EPERM is benign only with positive zombie
                # evidence while this lock still prevents reaping the leader.
                if (sys.platform == "darwin" and exited
                        and _darwin_zombie_only_group(self.pid)):
                    return
                self.cleanup_warnings.append(f"signal {sig}: PermissionError; group cleanup unconfirmed")

    def _internal_poll(self, _deadstate=None):
        # Plain observers still call global Popen._cleanup. Defer all owners
        # on this thread before acquiring even the first owner lock. Other
        # threads keep their genuine signal/reap ownership unchanged.
        if getattr(_inspection_state, "active", False):
            return self.returncode
        with self._owner_lock:
            if not self._child_created or not isinstance(self.pid, int) or self.pid <= 0:
                return self.returncode
            if os.name != "posix":
                return super()._internal_poll(_deadstate=_deadstate)
            if self.returncode is None and self._probe(self.pid):
                # The unreaped leader pins this identity, including on Darwin
                # where getpgid can fail for a zombie. End the owned group first.
                self._signal_group(signal.SIGKILL)
                return super()._internal_poll(_deadstate=_deadstate)
            return self.returncode

    def _wait(self, timeout):
        if os.name != "posix":
            return super()._wait(timeout)
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            result = self._internal_poll()
            if result is not None:
                return result
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(self.args, timeout)
                time.sleep(min(0.01, remaining))
            else:
                time.sleep(0.01)


def _terminate_process_group(process: subprocess.Popen[str]) -> str | None:
    """TERM, allow the existing one-second grace, then KILL through the owner."""

    if not isinstance(process, _SuiteProcess):
        raise TypeError("suite termination requires its owned Popen")
    if os.name == "posix":
        process._signal_group(signal.SIGTERM)
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
        process._signal_group(signal.SIGKILL)  # A reaped owner makes this a locked no-op.
    elif process.poll() is None:
        process.kill()
    return "; ".join(process.cleanup_warnings) or None


def _cleanup_diagnostic(message: str) -> None:
    """One bounded-size best-effort write; never format a pending exception."""

    try:
        sys.stderr.write(message[:240] + "\n")
    except BaseException:
        pass


def _abort_process(process: _SuiteProcess) -> None:
    """Attempt all bounded cleanup stages before primary-safe diagnostics."""

    # Partial construction must supply actual creation and numeric identity.
    # No wait, communicate (which waits), or signal is safe without both.
    if (not getattr(process, "_child_created", False)
            or not isinstance(getattr(process, "pid", None), int) or process.pid <= 0):
        return
    failed = False
    warning = None
    drain_timed_out = False
    unreaped = False
    try:
        warning = _terminate_process_group(process)
    except BaseException:
        failed = True
    # A failed TERM/wait must not prevent the final owned KILL attempt.
    # Only then (docs/local-validation-journal.md, round 7, F27): a completed termination has just sent this KILL;
    # macOS answers a second one EPERM while the group it reached is still exiting and its leader not yet waitable,
    # which _signal_group records as unconfirmed cleanup; the reap's KILL (_internal_poll) covers what the first missed.
    if failed:
        try:
            process._signal_group(signal.SIGKILL)
        except BaseException:
            failed = True
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        drain_timed_out = True
    except BaseException:
        failed = True
    try:
        process.wait(timeout=0)
    except subprocess.TimeoutExpired:
        unreaped = True
    except BaseException:
        failed = True
    for stream in (getattr(process, "stdin", None), getattr(process, "stdout", None),
                   getattr(process, "stderr", None)):
        if stream is not None:
            try:
                stream.close()
            except BaseException:
                failed = True
    # No exception __str__, repr, notes or stderr failure can replace the
    # exact callback/capture/interrupt object re-raised by the caller.
    if failed or warning or process.cleanup_warnings:
        _cleanup_diagnostic("suite cleanup: failure or uncertainty during bounded cleanup")
    if unreaped:
        _cleanup_diagnostic("suite cleanup: leader still unreaped after bounded drain")
    if drain_timed_out:
        _cleanup_diagnostic("suite cleanup: output drain timed out")


# Overrides that would send a suite's state to the developer's own directories, so a suite never inherits them.
_STATE_OVERRIDES = ("UNTIL_LOOP_STATE_DIR", "SHIPLOOP_KEEPALIVE_HOME", "SHIPLOOP_STATE_HOME")
# Overrides that would change every Git call a suite makes.  A shell with `GIT_CONFIG_COUNT=1, GIT_CONFIG_KEY_0=
# core.quotePath, GIT_CONFIG_VALUE_0=false` set is a common local setup, and ask-agent's workspace guard refuses it by
# design ("prepare refuses Git context environment overrides").  Inherited, it failed three suites that shell out to Git --
# ask-agent-parallel, agent-harness-audit and install-arbitrary-skill -- on 2026-11-04, and all three passed with these
# unset.  A suite's Git identity and configuration must come from the fixture, never from the developer's shell.
_GIT_CONTEXT_OVERRIDES = ("GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0",
                          "GIT_CONFIG_KEY_1", "GIT_CONFIG_VALUE_1", "GIT_CONFIG_KEY_2", "GIT_CONFIG_VALUE_2")
_INHERITED_OVERRIDES = _STATE_OVERRIDES + _GIT_CONTEXT_OVERRIDES


def _state_home_error(state_home: Path) -> str | None:
    """Name what a suite left in its private state home, if anything.

    Run outside this runner, the same write lands in the developer's
    ``~/.local/state``, keyed to their live session.  Until Loop keeps session
    stacks there, and a SessionStart hook offers an active one to the next real
    session as saved work: on 2026-10-18 a vendor test left a placeholder stack
    in the owner's directory.  ShipLoop's keepalive keeps per-session health
    records there: 32 of the owner's 170 named test temp directories on 2026-10-26.
    """

    written = sorted(path.relative_to(state_home).as_posix() for path in state_home.rglob("*")
                     if not path.is_dir() or not any(path.iterdir()))
    if not written:
        return None
    names = ", ".join(written[:6]) + (f" and {len(written) - 6} more" if len(written) > 6 else "")
    return (f"the suite left state in its private XDG_STATE_HOME ({names}); outside run-all.sh that lands in the "
            "developer's ~/.local/state. Give its processes their own XDG_STATE_HOME, as "
            "git_fixture.isolate_git_environment does, or the store's own override (UNTIL_LOOP_STATE_DIR, "
            "SHIPLOOP_KEEPALIVE_HOME, SHIPLOOP_STATE_HOME), and leave out the host session markers that key the records "
            "(CLAUDECODE, CLAUDE_CODE_SESSION_ID, GROK_AGENT, GROK_SESSION_ID). A private HOME alone is not "
            "enough: XDG_STATE_HOME takes precedence over it")


@contextlib.contextmanager
def _scratch_directory(prefix: str) -> Iterator[str]:
    """A temporary directory removed on exit, whose removal errors are ignored.

    Cleanup errors must not replace the suite result.
    """

    name = tempfile.mkdtemp(prefix=prefix)
    try:
        yield name
    finally:
        shutil.rmtree(name, ignore_errors=True)


def run_process(
    argv: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: float,
    on_start: Callable[[subprocess.Popen[str]], None] | None = None,
) -> ProcessOutcome:
    """Run a fixed argv with a bounded lifetime, collected output and a private state home.

    ``on_start`` receives the process once it exists, so a parallel caller can
    stop its group when the run is interrupted.  The process gets its own
    ``XDG_STATE_HOME`` and none of ``_INHERITED_OVERRIDES`` -- the state overrides, so a suite that forgets to isolate its
    state cannot write the developer's, and the Git context overrides, so a developer's ``GIT_CONFIG_*`` shell setup cannot
    reach a suite's Git calls.  One that leaves anything in that home fails.
    """

    # Resolved: macOS temporary paths sit under the /var symlink, which Until Loop refuses as a state root.
    with _scratch_directory("skill-craft-suite-state-") as name:
        state_home = Path(name).resolve()
        environment = {key: value for key, value in os.environ.items() if key not in _INHERITED_OVERRIDES}
        # Ordinary hermetic fixtures must not leave per-run observers.
        # Progress integration tests explicitly enable and stop their own.
        # No bytecode: the runner's own `python3 -B` does not reach the processes it starts, and a suite that created
        # test/__pycache__ made a sibling suite's GNU `tar` of the checkout exit 1 ("file changed as we read it").
        environment.update({"SHIPLOOP_PROGRESS": "off", "XDG_STATE_HOME": str(state_home),
                            "PYTHONDONTWRITEBYTECODE": "1"})
        outcome = _run_bounded(argv, cwd=cwd, timeout_seconds=timeout_seconds, on_start=on_start, env=environment)
        error = _state_home_error(state_home)
    if error is None:
        return outcome
    return replace(outcome, status="failed" if outcome.status == "passed" else outcome.status,
                   error="; ".join(filter(None, (outcome.error, error))))


def _run_bounded(
    argv: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: float,
    on_start: Callable[[subprocess.Popen[str]], None] | None,
    env: dict[str, str],
) -> ProcessOutcome:
    started = time.monotonic()
    try:
        process = _SuiteProcess(
            list(argv), cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors="replace", start_new_session=True, env=env,
        )
    except OSError as exc:
        return ProcessOutcome(
            status="failed", returncode=None, duration_seconds=time.monotonic() - started,
            stdout="", stderr="", error=str(exc),
        )
    try:
        if on_start is not None:
            on_start(process)
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            cleanup_warning = _terminate_process_group(process)
            cleanup_detail = f"; cleanup: {cleanup_warning}" if cleanup_warning else ""
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired as drain:
                # Do not turn a timeout into an unbounded wait if an escaped child
                # kept a captured descriptor open.  The leader's result is enough
                # to report the bounded failure, and the pipe handles are closed.
                try:
                    process.wait(timeout=0)
                except subprocess.TimeoutExpired:
                    cleanup_detail += "; cleanup: leader still unreaped after bounded drain"
                stdout = drain.output or ""
                stderr = drain.stderr or ""
                if isinstance(stdout, bytes):
                    stdout = stdout.decode("utf-8", errors="replace")
                if isinstance(stderr, bytes):
                    stderr = stderr.decode("utf-8", errors="replace")
                for stream in (process.stdout, process.stderr):
                    if stream is not None:
                        stream.close()
                return ProcessOutcome(
                    status="timed_out", returncode=process.returncode,
                    duration_seconds=time.monotonic() - started, stdout=stdout, stderr=stderr,
                    error=f"timed out after {timeout_seconds:g} seconds; output drain timed out{cleanup_detail}",
                )
            return ProcessOutcome(
                status="timed_out", returncode=process.returncode,
                duration_seconds=time.monotonic() - started, stdout=stdout, stderr=stderr,
                error=f"timed out after {timeout_seconds:g} seconds{cleanup_detail}",
            )
        cleanup_warning = "; ".join(process.cleanup_warnings) or None
        return ProcessOutcome(
            status="passed" if process.returncode == 0 and cleanup_warning is None else "failed",
            returncode=process.returncode, duration_seconds=time.monotonic() - started,
            stdout=stdout, stderr=stderr, error=f"cleanup: {cleanup_warning}" if cleanup_warning else None,
        )
    except BaseException:
        # Includes callback, timeout-handler, grace/drain/close and outcome
        # failures. A cleanup failure alone escapes here too; no ambient
        # caller exception can cause it to be swallowed.
        try:
            _abort_process(process)
        except BaseException:
            _cleanup_diagnostic("suite cleanup failed while preserving primary exception")
        raise


def _run_suite(
    suite: suite_catalog.Suite,
    on_start: Callable[[subprocess.Popen[str]], None] | None = None,
) -> ProcessOutcome:
    return run_process(suite.argv, cwd=ROOT, timeout_seconds=suite.timeout_seconds, on_start=on_start)


class _SuiteDispatch:
    """Cancellation and registration share a lock, not a one-time snapshot.

    Registration after stop begins terminates its own late process. Neither a
    registry lock nor an owner lock is held across user callbacks or drainage.
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.stopping = False
        self.processes: list[subprocess.Popen[str]] = []

    def register(self, process: subprocess.Popen[str]) -> None:
        with self.lock:
            self.processes.append(process)
            stopping = self.stopping
        if stopping:
            _terminate_process_group(process)

    def stop(self) -> None:
        with self.lock:
            self.stopping = True
            processes = tuple(self.processes)
        # No future state is used as a proxy for ownership. Each signal and
        # reap is serialized by the process itself, even after future completion.
        errors = []
        for process in processes:
            try:
                process._signal_group(signal.SIGTERM)
            except Exception as exc:
                errors.append(f"{process.pid} TERM failed")
        if processes:
            deadline = time.monotonic() + 1
            for process in processes:
                try:
                    process.wait(timeout=max(0, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    pass
                except Exception as exc:
                    errors.append(f"{process.pid} wait failed")
            for process in processes:
                try:
                    process._signal_group(signal.SIGKILL)
                except Exception as exc:
                    errors.append(f"{process.pid} KILL failed")
        for process in processes:
            if process.cleanup_warnings:
                errors.append(f"{process.pid} group cleanup unconfirmed")
        if errors:
            raise RuntimeError("suite dispatch cleanup failed: " + "; ".join(errors))


def _outcomes(selected: Sequence[suite_catalog.Suite], jobs: int) -> Iterator[ProcessOutcome]:
    """Yield each selected suite's outcome in catalog order, running up to JOBS at once.

    With one job a suite starts only when the caller asks for its outcome, so
    the receipt written after each suite is complete before the next starts.
    """

    if jobs == 1:
        for suite in selected:
            yield _run_suite(suite)
        return
    dispatch = _SuiteDispatch()
    pool = futures.ThreadPoolExecutor(max_workers=jobs, thread_name_prefix="suite")
    escaping = False
    try:
        pending = [pool.submit(_run_suite, suite, dispatch.register) for suite in selected]
        for future in pending:
            yield future.result()
    except BaseException:
        # This operation's escape only: sys.exc_info() in finally can instead
        # expose an unrelated exception already handled by the caller (F2).
        escaping = True
        raise
    finally:
        cleanup_error = None
        try:
            pool.shutdown(wait=False, cancel_futures=True)
        except BaseException as exc:
            cleanup_error = exc
        try:
            dispatch.stop()
        except BaseException as exc:
            if cleanup_error is None:
                cleanup_error = exc
            else:
                _cleanup_diagnostic("suite dispatch cleanup: additional failure")
        if cleanup_error is not None:
            if not escaping:
                raise cleanup_error
            _cleanup_diagnostic("suite dispatch cleanup failed while preserving primary exception")


def _write_log(output: Path | None, index: int, identifier: str, stream: str, value: str) -> str | None:
    if output is None:
        return None
    relative = Path("logs") / f"{index:03d}-{identifier}.{stream}.log"
    (output / relative).write_text(value, encoding="utf-8")
    return relative.as_posix()


def _emit(outcome: ProcessOutcome) -> None:
    if outcome.stdout:
        print(outcome.stdout, end="" if outcome.stdout.endswith("\n") else "\n")
    if outcome.stderr:
        print(outcome.stderr, end="" if outcome.stderr.endswith("\n") else "\n", file=sys.stderr)
    if outcome.error:
        print(outcome.error, file=sys.stderr)


def _command_record(suite: suite_catalog.Suite) -> dict[str, object]:
    return {
        "id": suite.id,
        "family": suite.family,
        "path": suite.path,
        "command": shlex.join(suite.argv),
        "timeout_seconds": suite.timeout_seconds,
        "hermetic": suite.hermetic,
    }


def _outcome_record(
    suite: suite_catalog.Suite,
    outcome: ProcessOutcome,
    output: Path | None,
    index: int,
) -> dict[str, object]:
    result = _command_record(suite)
    result.update({
        "status": outcome.status,
        "returncode": outcome.returncode,
        "duration_seconds": round(outcome.duration_seconds, 3),
        "stdout_log": _write_log(output, index, suite.id, "stdout", outcome.stdout),
        "stderr_log": _write_log(output, index, suite.id, "stderr", outcome.stderr),
    })
    if outcome.error:
        result["error"] = outcome.error
    return result


def _write_receipt(output: Path, receipt: dict[str, object]) -> None:
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _timing_line(completed: Sequence[dict[str, object]], wall: float, jobs: int) -> str:
    """The run's wall time and its slowest suites: the floor a parallel run cannot go under."""

    slowest = sorted(completed, key=lambda record: -float(record["duration_seconds"]))[:3]
    named = ", ".join(f"{record['id']} {float(record['duration_seconds']):.1f} s" for record in slowest)
    return f"run-all.sh: {len(completed)} suites in {wall:.1f} s wall (--jobs {jobs}); slowest: {named or 'none'}"


def _print_list(selected: Iterable[suite_catalog.Suite]) -> None:
    for suite in selected:
        print(f"{suite.family}\t{suite.id}\t{shlex.join(suite.argv)}")


def main(argv: Sequence[str] | None = None) -> int:
    args, groups = parse_args(argv)
    changed: tuple[str, ...] = ()
    if args.changed_from:
        try:
            changed = changed_paths(ROOT, args.changed_from)
        except subprocess.CalledProcessError:
            _parser().error(f"--changed-from: cannot diff {args.changed_from} against the checkout")
    selected = suite_catalog.select(groups, changed)
    if args.list:
        _print_list(selected)
        return 0

    problems = catalog_omissions(ROOT)
    if problems:
        for problem in problems:
            print(f"run-suites: {problem}", file=sys.stderr)
        return 1

    try:
        output = prepare_output(args.output, ROOT) if args.output else None
    except ValueError as exc:
        _parser().error(str(exc))
        raise AssertionError("unreachable")

    from ci_summary import selection_counts

    receipt: dict[str, object] = {
        "schema": "skill-craft-hermetic-receipt/1",
        "entrypoint": "run-all",
        "groups": list(groups),
        "changed_from": args.changed_from,
        "changed": list(changed),
        "selection": selection_counts(groups, changed),
        "source": source_identity(ROOT),
        "runtimes": runtime_versions(ROOT),
        "selected": [_command_record(suite) for suite in selected],
        "jobs": args.jobs,
        "completed": [],
        "status": "running",
    }
    if output is not None:
        _write_receipt(output, receipt)
    failures = False
    completed: list[dict[str, object]] = []
    started = time.monotonic()
    with contextlib.closing(_outcomes(selected, args.jobs)) as outcomes:
        for index, suite in enumerate(selected, start=1):
            print(f"==> [{suite.family}] {suite.id}")
            outcome = next(outcomes)
            _emit(outcome)
            record = _outcome_record(suite, outcome, output, index)
            completed.append(record)
            receipt["completed"] = completed
            if output is not None:
                _write_receipt(output, receipt)
            if outcome.status != "passed":
                failures = True
                print(f"FAIL {suite.id}", file=sys.stderr)
            else:
                print(f"OK   {suite.id}")
    wall = time.monotonic() - started
    receipt["wall_seconds"] = round(wall, 3)
    receipt["status"] = "failed" if failures else "passed"
    if output is not None:
        _write_receipt(output, receipt)
        print(f"receipt: {output / 'receipt.json'}")
    print(_timing_line(completed, wall, args.jobs))

    if failures:
        print("run-all.sh: FAILED", file=sys.stderr)
        return 1
    print(f"run-all.sh: PASS ({', '.join(groups)} hermetic group selection)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
