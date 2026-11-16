"""POSIX test subprocess ownership; never used by the grading oracle.

Ownership comes from start_new_session, whose session/group ID is the child PID.
Descendants must remain in that group. ps supplies only PID/group/state, including
orphaned workers; zombies are stopped, not evidence of a live worker.
"""

import os
import signal
import subprocess
import time


class CleanupError(RuntimeError):
    """Owned processes or captured pipes could not be confirmed stopped."""


def live_members(pgid):
    try:
        result = subprocess.run(["ps", "-axo", "pid=,pgid=,stat="], capture_output=True,
                                text=True, timeout=2, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CleanupError(f"cannot inspect owned process group {pgid}") from error
    if result.returncode:
        raise CleanupError(f"cannot inspect owned process group {pgid}: ps rc {result.returncode}")
    try:
        return [int(pid) for pid, group, state in
                (line.split() for line in result.stdout.splitlines() if line.strip())
                if int(group) == pgid and not state.startswith("Z")]
    except ValueError as error:
        raise CleanupError(f"cannot parse owned process group {pgid} states") from error


def stop_group(pgid):
    """Idempotent, bounded TERM/KILL; permission errors require state evidence."""
    errors = []
    for sig in (signal.SIGTERM, signal.SIGKILL):
        if not live_members(pgid):
            return
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            pass
        except PermissionError as error:
            errors.append(str(error))
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            if not live_members(pgid):
                return
            time.sleep(0.02)
    remaining = live_members(pgid)
    if remaining:
        raise CleanupError(f"owned group {pgid} still live: {remaining}; signal errors: {errors}")


def stop_child(child):
    """Terminate and reap the direct Popen child independently of group inspection."""
    errors = []
    for stop in (child.terminate, child.kill):
        if child.poll() is not None:
            return
        try:
            stop()
        except ProcessLookupError:
            pass
        except OSError as error:
            errors.append(str(error))
        try:
            child.wait(timeout=1)
            return
        except subprocess.TimeoutExpired:
            pass
    raise CleanupError(f"owned direct child {child.pid} not reaped; signal errors: {errors}")


def run_owned(argv, *, cwd, timeout=600):
    if os.name != "posix":
        return subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout, stdin=subprocess.DEVNULL)
    child = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, stdin=subprocess.DEVNULL, start_new_session=True)
    # No inspection or other fallible operation between launch and ownership scope.
    pgid = child.pid
    try:
        deadline = time.monotonic() + timeout
        while True:
            try:
                stdout, stderr = child.communicate(timeout=max(0.001, min(0.1, deadline - time.monotonic())))
                return subprocess.CompletedProcess(argv, child.returncode, stdout, stderr)
            except subprocess.TimeoutExpired as error:
                # communicate waits for EOF, even when only an orphan holds the
                # pipe. Stop that group before attempting a bounded final drain.
                if child.poll() is not None:
                    stop_group(pgid)
                    try:
                        stdout, stderr = child.communicate(timeout=2)
                    except subprocess.TimeoutExpired as drain_error:
                        raise CleanupError(f"owned group {pgid} stopped but pipes remain open") from drain_error
                    return subprocess.CompletedProcess(argv, child.returncode, stdout, stderr)
                if time.monotonic() >= deadline:
                    raise subprocess.TimeoutExpired(argv, timeout, output=error.output, stderr=error.stderr) from None
    finally:
        try:
            try:
                stop_group(pgid)
            finally:
                # Inspection uncertainty must remain loud, but cannot bypass
                # termination/reaping of the direct child we still own.
                try:
                    stop_child(child)
                finally:
                    try:
                        child.communicate(timeout=2)
                    except subprocess.TimeoutExpired as error:
                        raise CleanupError(f"owned group {pgid} cleanup left pipes open") from error
        finally:
            child.stdout.close()
            child.stderr.close()
