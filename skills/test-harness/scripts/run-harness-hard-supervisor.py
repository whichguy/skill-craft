#!/usr/bin/env python3
"""Hard wall-clock supervisor for the complete test-harness lifecycle.

The worker runs in a new session/process group.  The advertised timeout covers
the worker, report/audit reserve, descendant cleanup, and supervisor exit.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import signal
import subprocess
import sys
import time


MAX_TIMEOUT_SECONDS = 3600
TIMEOUT_EXIT_CODE = 124


def open_exclusive_private(path: Path) -> int:
    """Create a private regular artifact without following or replacing paths."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    return os.open(path, flags, 0o600)


def write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("short write")
        view = view[written:]


def write_hard_timeout_evidence(
    run_dir: Path,
    args: argparse.Namespace,
    started: float,
) -> bool:
    """Write timeout evidence through the descriptor that won path creation."""
    path = run_dir / "hard-timeout.json"
    try:
        fd = open_exclusive_private(path)
    except OSError as exc:
        print(
            "test-harness hard supervisor: refusing to replace timeout "
            f"evidence at {path.name}: {exc}",
            file=sys.stderr,
        )
        return False

    payload = (
        json.dumps(
            {
                "stop": "hard_timeout",
                "timeout_secs": args.timeout_secs,
                "elapsed_ms": int((time.monotonic() - started) * 1000),
                "worker_executable": Path(args.command[0]).name,
                "worker_argument_count": max(0, len(args.command) - 1),
            },
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    try:
        write_all(fd, payload)
        os.fsync(fd)
    except OSError:
        return False
    finally:
        os.close(fd)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--timeout-secs", required=True, type=int)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--run-dir")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not 1 <= args.timeout_secs <= MAX_TIMEOUT_SECONDS:
        parser.error(
            f"--timeout-secs must be from 1 to {MAX_TIMEOUT_SECONDS}"
        )
    if not args.command or args.command[0] != "--" or len(args.command) < 2:
        parser.error("expected -- followed by the worker command")
    args.command = args.command[1:]
    return args


def remaining_seconds(
    deadline_ns: int,
    *,
    reserve_seconds: int = 0,
    now_ns: int | None = None,
) -> int:
    """Return whole usable seconds without allowing a negative budget."""
    if now_ns is None:
        now_ns = time.monotonic_ns()
    raw = (deadline_ns - now_ns) // 1_000_000_000
    return max(0, int(raw) - reserve_seconds)


def finalization_reserve_seconds(timeout_seconds: int) -> int:
    """Reserve five percent, bounded to 1..60 seconds, inside the cap."""
    return min(60, max(1, timeout_seconds // 20))


def default_run_root() -> Path:
    """The user's state directory, outside every repository under test.

    ``$XDG_STATE_HOME`` when set and non-empty, else ``~/.local/state``; run-harness.sh computes the same default.
    """
    state = os.environ.get("XDG_STATE_HOME")
    base = Path(state).expanduser() if state else Path.home() / ".local" / "state"
    return base / "test-harness" / "runs"


def resolve_run_dir(args: argparse.Namespace) -> Path:
    if args.run_dir:
        return Path(args.run_dir).expanduser().resolve()
    repo_name = Path(args.repo).expanduser().resolve().name or "repo"
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", repo_name).strip("-") or "repo"
    root_raw = os.environ.get("TEST_HARNESS_RUN_ROOT")
    root = Path(root_raw).expanduser() if root_raw else default_run_root()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (root / slug / f"{stamp}-{secrets.token_hex(3)}").resolve()


def main() -> int:
    args = parse_args()
    # Captured suite output can contain credentials, prompts, or provider
    # response excerpts. Make every directory/file created by this lifecycle
    # private by default, including emergency timeout evidence.
    os.umask(0o077)
    started = time.monotonic()
    timeout = float(args.timeout_secs)

    # Start the independent failsafe before any caller-controlled path
    # resolution or filesystem setup. The normal process-group cleanup path
    # aims to finish earlier; this alarm is the final bound if setup or teardown
    # itself blocks.
    accounting_margin = min(0.25, max(0.05, timeout / 10))
    hard_deadline = started + max(0.1, timeout - accounting_margin)
    run_dir_for_timeout: Path | None = None
    pgid_for_timeout: int | None = None

    def hard_alarm(_sig: int, _frame: object) -> None:
        if pgid_for_timeout is not None:
            try:
                os.killpg(pgid_for_timeout, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        message = (
            "test-harness hard timeout: enclosing lifecycle exceeded "
            f"{args.timeout_secs}s; owned process group terminated\n"
        ).encode("utf-8", errors="replace")
        try:
            os.write(sys.stderr.fileno(), message)
            if run_dir_for_timeout is not None:
                os.write(
                    sys.stdout.fileno(),
                    f"RUN_DIR={run_dir_for_timeout}\n".encode(
                        "utf-8", errors="replace"
                    ),
                )
        finally:
            os._exit(TIMEOUT_EXIT_CODE)

    signal.signal(signal.SIGALRM, hard_alarm)
    signal.setitimer(
        signal.ITIMER_REAL,
        max(0.001, hard_deadline - time.monotonic()),
    )

    def finish(exit_code: int) -> int:
        signal.setitimer(signal.ITIMER_REAL, 0)
        return exit_code

    run_dir = resolve_run_dir(args)
    run_dir_for_timeout = run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    run_dir.chmod(0o700)

    # All reserves are inside the advertised timeout.  A normal worker receives
    # a separate suite deadline so it can audit and emit before the failsafe
    # must terminate the complete lifecycle.
    cleanup_reserve = min(
        7.0,
        max(0.2, (hard_deadline - started) / 4),
    )
    worker_deadline = hard_deadline - cleanup_reserve
    report_reserve = float(finalization_reserve_seconds(args.timeout_secs))
    suite_deadline = max(started, worker_deadline - report_reserve)

    wall_now_ms = int(time.time() * 1000)
    monotonic_now = time.monotonic()

    def wall_epoch_ms(deadline: float) -> int:
        return wall_now_ms + int((deadline - monotonic_now) * 1000)

    env = os.environ.copy()
    capability_read_fd, capability_write_fd = os.pipe()
    os.set_inheritable(capability_read_fd, True)
    os.set_blocking(capability_read_fd, False)
    capability_nonce = secrets.token_hex(32)
    os.write(capability_write_fd, (capability_nonce + "\n").encode("ascii"))
    env.update(
        {
            "TEST_HARNESS_INTERNAL_RUN_DIR": str(run_dir),
            "TEST_HARNESS_HARD_SUPERVISED": "1",
            "TEST_HARNESS_HARD_SUPERVISOR_PID": str(os.getpid()),
            "TEST_HARNESS_HARD_CAPABILITY_FD": str(capability_read_fd),
            "TEST_HARNESS_HARD_CAPABILITY_NONCE": capability_nonce,
            "TEST_HARNESS_HARD_DEADLINE_EPOCH_MS": str(
                wall_epoch_ms(hard_deadline)
            ),
            "TEST_HARNESS_SUITE_DEADLINE_EPOCH_MS": str(
                wall_epoch_ms(suite_deadline)
            ),
        }
    )

    try:
        proc = subprocess.Popen(
            args.command,
            env=env,
            pass_fds=(capability_read_fd,),
            start_new_session=True,
        )
    except OSError as exc:
        os.close(capability_read_fd)
        os.close(capability_write_fd)
        print(f"test-harness hard supervisor: spawn failed: {exc}", file=sys.stderr)
        return finish(127)
    os.close(capability_read_fd)

    pgid = proc.pid
    pgid_for_timeout = pgid
    forwarded_signal: int | None = None

    def group_alive() -> bool:
        proc.poll()
        try:
            os.killpg(pgid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    def signal_group(sig: int) -> None:
        try:
            os.killpg(pgid, sig)
        except (ProcessLookupError, PermissionError):
            pass

    def receive_signal(sig: int, _frame: object) -> None:
        nonlocal forwarded_signal
        if forwarded_signal is None:
            forwarded_signal = sig
            signal_group(sig)

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, receive_signal)

    def cleanup_group(stop_by: float) -> None:
        if not group_alive():
            return
        signal_group(signal.SIGTERM)
        remaining = max(0.0, stop_by - time.monotonic())
        kill_margin = min(0.25, max(0.05, remaining / 4))
        grace_deadline = min(time.monotonic() + 5.0, stop_by - kill_margin)
        while time.monotonic() < grace_deadline:
            if not group_alive():
                return
            time.sleep(min(0.05, max(0.0, grace_deadline - time.monotonic())))
        if group_alive():
            signal_group(signal.SIGKILL)
            while time.monotonic() < stop_by and group_alive():
                time.sleep(min(0.025, max(0.0, stop_by - time.monotonic())))

    def cleanup_after_forwarded_signal(stop_by: float) -> None:
        """Give nested supervisors time to forward before terminating workers."""
        if not group_alive():
            return
        remaining = max(0.0, stop_by - time.monotonic())
        kill_margin = min(0.25, max(0.05, remaining / 5))
        cooperative_deadline = min(
            time.monotonic() + 2.0,
            stop_by - kill_margin,
        )
        while time.monotonic() < cooperative_deadline:
            if not group_alive():
                return
            time.sleep(
                min(
                    0.05,
                    max(0.0, cooperative_deadline - time.monotonic()),
                )
            )
        if group_alive():
            signal_group(signal.SIGTERM)
        term_deadline = min(
            time.monotonic() + 0.5,
            stop_by - kill_margin,
        )
        while time.monotonic() < term_deadline:
            if not group_alive():
                return
            time.sleep(min(0.05, max(0.0, term_deadline - time.monotonic())))
        if group_alive():
            signal_group(signal.SIGKILL)
            while time.monotonic() < stop_by and group_alive():
                time.sleep(min(0.025, max(0.0, stop_by - time.monotonic())))

    timed_out = False
    leader_rc: int | None = None
    while True:
        leader_rc = proc.poll()
        if leader_rc is not None:
            break
        if forwarded_signal is not None:
            break
        if time.monotonic() >= worker_deadline:
            leader_rc = proc.poll()
            if leader_rc is not None:
                break
            timed_out = True
            cleanup_group(hard_deadline)
            leader_rc = proc.poll()
            break
        time.sleep(0.05)

    if forwarded_signal is not None:
        cleanup_after_forwarded_signal(
            min(hard_deadline, time.monotonic() + 3.0)
        )
        leader_rc = proc.poll()
    elif not timed_out:
        cleanup_group(hard_deadline)

    if proc.poll() is None:
        signal_group(signal.SIGKILL)
        try:
            proc.wait(timeout=max(0.0, hard_deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass

    try:
        os.close(capability_write_fd)
    except OSError:
        pass

    if timed_out:
        write_hard_timeout_evidence(run_dir, args, started)
        print(
            "test-harness hard timeout: enclosing lifecycle exceeded "
            f"{args.timeout_secs}s; owned process group terminated",
            file=sys.stderr,
        )
        print(f"RUN_DIR={run_dir}")
        return finish(TIMEOUT_EXIT_CODE)

    if forwarded_signal is not None:
        return finish(128 + forwarded_signal)
    if leader_rc is None:
        return finish(1)
    if leader_rc < 0:
        return finish(128 + (-leader_rc))
    return finish(leader_rc)


if __name__ == "__main__":
    raise SystemExit(main())
