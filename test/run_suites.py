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
import functools
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
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
                        help="with --group quick: also run the suites matching files changed since REF; "
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
    if args.changed_from is not None and not {"quick", "prompt"} & set(groups):
        parser.error("--changed-from applies only to --group quick or prompt")
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


def _terminate_process_group(process: subprocess.Popen[str]) -> str | None:
    """Terminate a timed-out process and its descendants on supported hosts."""

    warnings = []
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError as exc:
            warnings.append(f"TERM: {exc}")
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
        # The leader can exit before a descendant that inherited its pipes.
        # Kill the process group even after that leader has exited; otherwise a
        # TERM-ignoring descendant can make communicate() wait indefinitely.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError as exc:
            # Darwin can return EPERM once an orphaned group has disappeared.
            # Retain the diagnostic; the timeout still fails and draining stays bounded.
            warnings.append(f"KILL: {exc}")
    else:
        if process.poll() is None:
            process.kill()
    return "; ".join(warnings) or None


# Overrides that would send a suite's state to the developer's own directories, so a suite never inherits them.
_STATE_OVERRIDES = ("UNTIL_LOOP_STATE_DIR", "SHIPLOOP_KEEPALIVE_HOME")


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
            "SHIPLOOP_KEEPALIVE_HOME), and leave out the host session markers that key the records "
            "(CLAUDECODE, CLAUDE_CODE_SESSION_ID, GROK_AGENT, GROK_SESSION_ID). A private HOME alone is not "
            "enough: XDG_STATE_HOME takes precedence over it")


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
    ``XDG_STATE_HOME`` and none of ``_STATE_OVERRIDES``, so a suite that forgets
    to isolate its state cannot write the developer's; one that leaves anything
    in that home fails.
    """

    # Resolved: macOS temporary paths sit under the /var symlink, which Until Loop refuses as a state root.
    with tempfile.TemporaryDirectory(prefix="skill-craft-suite-state-", ignore_cleanup_errors=True) as name:
        state_home = Path(name).resolve()
        environment = {key: value for key, value in os.environ.items() if key not in _STATE_OVERRIDES}
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
        process = subprocess.Popen(
            list(argv), cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors="replace", start_new_session=True, env=env,
        )
    except OSError as exc:
        return ProcessOutcome(
            status="failed", returncode=None, duration_seconds=time.monotonic() - started,
            stdout="", stderr="", error=str(exc),
        )
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
    return ProcessOutcome(
        status="passed" if process.returncode == 0 else "failed",
        returncode=process.returncode, duration_seconds=time.monotonic() - started,
        stdout=stdout, stderr=stderr,
    )


def _run_suite(
    suite: suite_catalog.Suite,
    on_start: Callable[[subprocess.Popen[str]], None] | None = None,
) -> ProcessOutcome:
    return run_process(suite.argv, cwd=ROOT, timeout_seconds=suite.timeout_seconds, on_start=on_start)


def _signal_groups(processes: Iterable[subprocess.Popen[str]], sig: signal.Signals) -> None:
    for process in processes:
        try:
            if os.name == "posix":
                os.killpg(process.pid, sig)
            else:
                process.kill()
        except (ProcessLookupError, PermissionError):
            pass


def _stop_process_groups(running: dict[futures.Future, subprocess.Popen[str]]) -> None:
    """Stop the suites still running when a parallel run is interrupted.

    Each suite leads its own session, so an interrupt at the terminal never
    reaches it, and the interpreter would wait at exit for every one.  TERM each
    group, give the workers a second to collect their processes, then KILL the
    groups whose suite is still running (its leader is not yet reaped, so the
    group id cannot have been reused).
    """

    _signal_groups(running.values(), signal.SIGTERM)
    _, still_running = futures.wait(running, timeout=1)
    _signal_groups((running[future] for future in still_running), signal.SIGKILL)


def _outcomes(selected: Sequence[suite_catalog.Suite], jobs: int) -> Iterator[ProcessOutcome]:
    """Yield each selected suite's outcome in catalog order, running up to JOBS at once.

    With one job a suite starts only when the caller asks for its outcome, so
    the receipt written after each suite is complete before the next starts.
    """

    if jobs == 1:
        for suite in selected:
            yield _run_suite(suite)
        return
    processes: dict[int, subprocess.Popen[str]] = {}
    pool = futures.ThreadPoolExecutor(max_workers=jobs, thread_name_prefix="suite")
    pending = [pool.submit(_run_suite, suite, functools.partial(processes.__setitem__, index))
               for index, suite in enumerate(selected)]
    try:
        for future in pending:
            yield future.result()
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
        running = {future: processes[index] for index, future in enumerate(pending)
                   if not future.done() and index in processes}
        if running:
            _stop_process_groups(running)


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

    receipt: dict[str, object] = {
        "schema": "skill-craft-hermetic-receipt/1",
        "entrypoint": "run-all",
        "groups": list(groups),
        "changed_from": args.changed_from,
        "changed": list(changed),
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
