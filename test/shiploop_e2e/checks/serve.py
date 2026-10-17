#!/usr/bin/env python3
"""Run one HTTP product check against the candidate's own server, on a port of this check's own.

Run from the case's work directory: `python3 "$E2E_CHECKS/serve.py" [--start CMD] -- COMMAND...`. It

1. takes a free port and starts the candidate (`node server.js` unless --start says otherwise) with PORT set to it, in a
   process group of its own, its stderr kept;
2. waits until the port is listening and confirms the listener is the candidate (its process group), using lsof. A
   candidate that exits first fails with its exit code and stderr; a port answered by any other process fails and names
   it; a listener nobody can identify fails;
3. runs COMMAND (an argv, not a shell line) with PORT and BASE (`http://127.0.0.1:<port>`) set, and exits with its code;
4. ends only the group it started.

Why: the catalog used to start each server on a fixed port and grade whatever answered. On 2026-10-16 the audit's sibling
probe (docs/experiments/shiploop-e2e-audit-20261016/port-probe/) passed the Battleship page check with a candidate that
could only answer "candidate", because a sibling server held the port. A free port per check keeps siblings off it; the
ownership check refuses a response the candidate did not serve.

E2E_SERVE_PORT pins the port (the regression uses it to put a sibling on the port first); nothing else sets it.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import listeners  # noqa: E402

# A ceiling for the server to start listening, the old recipes' 20 tries of 0.5 s; not a tuning value.
READY_SECONDS = 10.0
POLL_SECONDS = 0.1


def fail(reason: str) -> None:
    print("FAIL: " + reason)
    sys.exit(1)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def listening_pids(port: int) -> set[int]:
    """The pids listening on TCP `port`; raises listeners.Unobserved where lsof cannot say."""
    text = listeners._run(["lsof", "-nP", "-a", f"-iTCP:{port}", "-sTCP:LISTEN", "-Fp"])
    return {int(line[1:]) for line in text.splitlines() if line.startswith("p") and line[1:].isdigit()}


def in_group(pid: int, leader: int) -> bool:
    try:
        return pid == leader or os.getpgid(pid) == leader
    except (ProcessLookupError, PermissionError):
        return False


def tail(path: Path) -> str:
    try:
        return " ".join(path.read_text(errors="replace").split())[-600:] or "(no stderr)"
    except OSError:
        return "(stderr unreadable)"


def wait_for_candidate(proc: subprocess.Popen, port: int, stderr: Path) -> None:
    deadline = time.monotonic() + READY_SECONDS
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            fail(f"the candidate exited (rc {proc.returncode}) before it listened on PORT={port}: {tail(stderr)}")
        try:
            pids = listening_pids(port)
        except listeners.Unobserved as why:
            fail(f"cannot confirm who listens on port {port} ({why}), so no response is accepted")
        if pids and any(in_group(pid, proc.pid) for pid in pids):
            return
        if pids:
            fail(f"port {port} is answered by pid {', '.join(map(str, sorted(pids)))}, not by the candidate (pid {proc.pid}), "
                 f"so its responses are refused; candidate stderr: {tail(stderr)}")
        time.sleep(POLL_SECONDS)
    fail(f"the candidate did not listen on PORT={port} within {READY_SECONDS:.0f} s: {tail(stderr)}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", default="node server.js", help="the candidate's start command (default: node server.js)")
    p.add_argument("command", nargs=argparse.REMAINDER, help="-- then the check's argv, run once the candidate listens, "
                   "with PORT and BASE set")
    args = p.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        p.error("no check command after --")
    port = int(os.environ.get("E2E_SERVE_PORT") or free_port())
    env = dict(os.environ, PORT=str(port), BASE=f"http://127.0.0.1:{port}")
    with tempfile.TemporaryDirectory(prefix="e2e-serve-") as scratch:
        stderr = Path(scratch) / "server.stderr"
        with stderr.open("w") as err:
            proc = subprocess.Popen(shlex.split(args.start), env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=err, start_new_session=True)
        try:
            wait_for_candidate(proc, port, stderr)
            done = subprocess.run(command, env=env, stdin=subprocess.DEVNULL)
            if done.returncode:
                print(f"check exited {done.returncode}; candidate stderr: {tail(stderr)}")
            return done.returncode
        finally:
            listeners.end_group(proc.pid)  # only the group this check started
            proc.wait()


if __name__ == "__main__":
    raise SystemExit(main())
