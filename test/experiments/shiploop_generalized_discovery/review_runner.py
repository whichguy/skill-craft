#!/usr/bin/env python3
"""Bound one experimental reviewer subprocess without judging its verdict.

This helper is deliberately local to the generalized-discovery experiment.  A
``success`` result means only that the review command exited cleanly; callers
must assess the review's semantic verdict separately.  On POSIX cleanup covers
the direct child's process group, not descendants that deliberately detach into
another session, process group, or process sandbox.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any


POLL_SECONDS = 0.02
TERM_GRACE_SECONDS = 0.25
KILL_GRACE_SECONDS = 0.25


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _positive_finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite positive number")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return numeric


def _validate_command(command: object) -> list[str]:
    if (
        not isinstance(command, list)
        or not command
        or any(not isinstance(item, str) or not item or "\x00" in item for item in command)
    ):
        raise ValueError("command must be a non-empty list of non-empty strings")
    return list(command)


def _group_alive(process: subprocess.Popen[bytes]) -> bool:
    if os.name != "posix":
        return process.poll() is None
    try:
        os.killpg(process.pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # The child group is created by this process, but retain uncertainty if
        # the platform refuses the observation rather than treating it clean.
        return True


def _signal_group(process: subprocess.Popen[bytes], sig: signal.Signals) -> bool:
    try:
        if os.name == "posix":
            os.killpg(process.pid, sig)
        elif sig == signal.SIGTERM:
            process.terminate()
        else:
            process.kill()
        return True
    except (OSError, ProcessLookupError):
        return False


def _wait_for_group_exit(process: subprocess.Popen[bytes], seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while True:
        # Reap the direct child while waiting.  Otherwise a terminated zombie
        # can make its former process group look live through the whole reserve.
        process.poll()
        if not _group_alive(process):
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(POLL_SECONDS, remaining))


def _cleanup_group(process: subprocess.Popen[bytes]) -> dict[str, Any]:
    """End the private group within a finite reserve and retain the outcome."""
    started = time.monotonic()
    scope = "process_group" if os.name == "posix" else "direct_process"
    alive_before = _group_alive(process)
    result: dict[str, Any] = {
        "scope": scope,
        "attempted": alive_before,
        "group_alive_before_cleanup": alive_before,
        "term_sent": False,
        "kill_sent": False,
        "term_grace_seconds": TERM_GRACE_SECONDS,
        "kill_grace_seconds": KILL_GRACE_SECONDS,
    }
    if not alive_before:
        result["outcome"] = "not_needed"
        result["group_alive_after_cleanup"] = False
        result["direct_child_reaped"] = process.poll() is not None
        result["additional_elapsed_monotonic_seconds"] = round(time.monotonic() - started, 6)
        return result

    result["term_sent"] = _signal_group(process, signal.SIGTERM)
    if _wait_for_group_exit(process, TERM_GRACE_SECONDS):
        result["outcome"] = "terminated"
    else:
        result["kill_sent"] = _signal_group(process, signal.SIGKILL)
        if _wait_for_group_exit(process, KILL_GRACE_SECONDS):
            result["outcome"] = "killed"
        else:
            result["outcome"] = "still_running_after_cleanup_reserve"

    try:
        process.wait(timeout=KILL_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    result["direct_child_reaped"] = process.poll() is not None
    result["group_alive_after_cleanup"] = _group_alive(process)
    result["additional_elapsed_monotonic_seconds"] = round(time.monotonic() - started, 6)
    return result


def _write_result(output_dir: Path, result: dict[str, Any]) -> None:
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _new_output_dir(output_dir: Path) -> Path:
    path = Path(output_dir).resolve()
    if path.exists():
        raise FileExistsError(f"output_dir must be new: {path}")
    path.mkdir(parents=True)
    return path


def _base_result(
    command: list[str],
    cwd: Path,
    output_dir: Path,
    timeout_seconds: float,
    hard_deadline_epoch: float | None,
    stdin_path: Path | None,
    started_monotonic: float,
) -> dict[str, Any]:
    return {
        "schema": "generalized-discovery-review-runner/1",
        "command": command,
        "cwd": str(cwd),
        "output_dir": str(output_dir),
        "stdout_log": str(output_dir / "stdout.log"),
        "stderr_log": str(output_dir / "stderr.log"),
        "stdin_file": None if stdin_path is None else str(stdin_path),
        "timeout_seconds": timeout_seconds,
        "hard_deadline_epoch": hard_deadline_epoch,
        "effective_timeout_seconds": None,
        "launched": False,
        "pid": None,
        "launched_at_utc": None,
        "finished_at_utc": None,
        "elapsed_monotonic_seconds": round(time.monotonic() - started_monotonic, 6),
        "exit_code": None,
        "reason": None,
        "status": "not_started",
        "success": False,
        "cleanup": {
            "scope": "process_group" if os.name == "posix" else "direct_process",
            "attempted": False,
            "outcome": "not_started",
            "additional_elapsed_monotonic_seconds": 0.0,
        },
    }


def run_bounded(
    command: list[str],
    cwd: Path,
    output_dir: Path,
    timeout_seconds: float,
    hard_deadline_epoch: float | None = None,
    stdin_path: Path | None = None,
) -> dict[str, Any]:
    """Run one command under a relative timeout and optional absolute deadline.

    ``output_dir`` must not exist.  The helper persists raw child streams in
    files but never writes them to its own stdout.  Its status describes only
    subprocess transport and cleanup, never whether a review is favorable.
    """
    checked_command = _validate_command(command)
    configured_timeout = _positive_finite(timeout_seconds, "timeout_seconds")
    deadline: float | None = None
    if hard_deadline_epoch is not None:
        deadline = _positive_finite(hard_deadline_epoch, "hard_deadline_epoch")
    cwd_path = Path(cwd).resolve()
    if not cwd_path.is_dir():
        raise ValueError("cwd must be an existing directory")
    input_path: Path | None = None
    if stdin_path is not None:
        input_path = Path(stdin_path).resolve()
        if not input_path.is_file():
            raise ValueError("stdin_path must be an existing file")

    started_monotonic = time.monotonic()
    output_path = _new_output_dir(Path(output_dir))
    result = _base_result(
        checked_command,
        cwd_path,
        output_path,
        configured_timeout,
        deadline,
        input_path,
        started_monotonic,
    )

    def finish() -> dict[str, Any]:
        result["finished_at_utc"] = _utc_now()
        result["elapsed_monotonic_seconds"] = round(time.monotonic() - started_monotonic, 6)
        _write_result(output_path, result)
        return result

    remaining_before_launch: float | None = None
    if deadline is not None:
        remaining_before_launch = deadline - time.time()
        result["deadline_remaining_before_launch_seconds"] = round(remaining_before_launch, 6)
        if remaining_before_launch <= 0:
            result["reason"] = "hard_deadline_expired_before_launch"
            return finish()

    # Recheck immediately before Popen so setup time cannot consume the whole
    # wall allowance between the first deadline observation and launch.
    if deadline is not None:
        remaining_before_launch = deadline - time.time()
        result["deadline_remaining_before_launch_seconds"] = round(remaining_before_launch, 6)
        if remaining_before_launch <= 0:
            result["reason"] = "hard_deadline_expired_before_launch"
            return finish()
    effective_timeout = min(
        configured_timeout,
        remaining_before_launch if remaining_before_launch is not None else configured_timeout,
    )
    result["effective_timeout_seconds"] = round(effective_timeout, 6)

    stdout_path = output_path / "stdout.log"
    stderr_path = output_path / "stderr.log"
    process: subprocess.Popen[bytes] | None = None
    launched_monotonic: float | None = None
    interrupted = False
    try:
        with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
            # A direct file destination avoids a descendant holding a pipe open
            # after its direct parent exits.  The post-exit group sweep below
            # still detects and ends conventional same-group descendants.
            input_handle = input_path.open("rb") if input_path is not None else None
            try:
                try:
                    launched_monotonic = time.monotonic()
                    launched_utc = _utc_now()
                    process = subprocess.Popen(
                        checked_command,
                        cwd=os.fspath(cwd_path),
                        stdin=input_handle if input_handle is not None else subprocess.DEVNULL,
                        stdout=stdout_file,
                        stderr=stderr_file,
                        start_new_session=os.name == "posix",
                    )
                except OSError as exc:
                    result["reason"] = "spawn_failure"
                    result["spawn_error"] = type(exc).__name__
                    return finish()
            finally:
                if input_handle is not None:
                    input_handle.close()

            result["launched"] = True
            result["pid"] = process.pid
            result["launched_at_utc"] = launched_utc
            timed_out = False
            deadline_limited = deadline is not None and effective_timeout < configured_timeout
            stop_at = launched_monotonic + effective_timeout
            try:
                while process.poll() is None:
                    if deadline is not None and time.time() >= deadline:
                        result["reason"] = "hard_deadline"
                        timed_out = True
                        break
                    if time.monotonic() >= stop_at:
                        result["reason"] = "hard_deadline" if deadline_limited else "timeout"
                        timed_out = True
                        break
                    time.sleep(POLL_SECONDS)
            except BaseException:
                interrupted = True
                result["reason"] = "runner_interrupted"
                result["cleanup"] = _cleanup_group(process)
                result["exit_code"] = process.returncode
                result["status"] = "failed"
                result["success"] = False
                raise

            parent_exited = process.poll() is not None
            cleanup = _cleanup_group(process)
            result["cleanup"] = cleanup
            exit_code = process.returncode
            result["exit_code"] = exit_code
            if timed_out:
                result["status"] = "failed"
            elif cleanup["group_alive_before_cleanup"] and parent_exited:
                result["reason"] = "descendants_active_after_parent_exit"
                result["status"] = "failed"
            elif cleanup["group_alive_after_cleanup"]:
                result["reason"] = "cleanup_incomplete"
                result["status"] = "failed"
            elif exit_code != 0:
                result["reason"] = "nonzero_exit"
                result["status"] = "failed"
            else:
                result["status"] = "success"
                result["success"] = True
    finally:
        if process is not None and process.poll() is None:
            result["cleanup"] = _cleanup_group(process)
        if interrupted:
            result["exit_code"] = None if process is None else process.returncode
            result["status"] = "failed"
            result["success"] = False
            finish()
    return finish()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--timeout-seconds", required=True, type=float)
    parser.add_argument("--hard-deadline-epoch", type=float)
    parser.add_argument("--stdin-file", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER, help="command after --")
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    try:
        result = run_bounded(
            command,
            args.cwd,
            args.output_dir,
            args.timeout_seconds,
            args.hard_deadline_epoch,
            args.stdin_file,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
