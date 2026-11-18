#!/usr/bin/env python3
"""Run one HTTP product check against the candidate's own server, on a port of this check's own.

Run from the case's work directory: `python3 "$E2E_CHECKS/serve.py" [--start CMD] -- COMMAND...`. It

1. takes a free port and starts the candidate (`node server.js` unless --start says otherwise) with PORT set to it, in a
   process group of its own, its stderr kept;
2. waits until the port is listening and confirms the listener is the candidate (its process group), using lsof. A
   candidate that exits first fails with its exit code and stderr; a port answered by any other process fails and names
   it; a listener nobody can identify fails. A port that another process took between the choice and the bind (the
   candidate exits with EADDRINUSE naming PORT, or another process listens on PORT) is chosen again: the candidate is
   ended and started on another free port, at most TRIES starts in all, the rule quality.serve_on_free_port has for the
   held-out checks. Nothing else is started again: a candidate that exits for another reason, one that names another
   port, one that never listens and a table lsof cannot read are the product's or the machine's;
3. runs COMMAND (an argv, not a shell line) with PORT and BASE (`http://127.0.0.1:<port>`) set, and exits with its code;
4. ends only the group it started (each start's).

Why: the catalog used to start each server on a fixed port and grade whatever answered. On 2026-10-16 the audit's sibling
probe (docs/experiments/shiploop-e2e-audit-20261016/port-probe/) passed the Battleship page check with a candidate that
could only answer "candidate", because a sibling server held the port. A free port per check keeps siblings off it; the
ownership check refuses a response the candidate did not serve. Choosing the port and binding it are two steps, so
another process can take the number in between, and the check then failed for a reason that is not the product's (the
release run of 2026-11-14; measurements in docs/experiments/serve-port-race-20261115/ and the journal's Round 6). The
retry changes nothing the check accepts: every start must again be the only listener on its own port.

E2E_SERVE_PORT pins the port (the regression uses it to put a sibling on the port first); a pinned port is tried once and
never chosen again; nothing else sets it.
"""

from __future__ import annotations

import argparse
import ipaddress
import os
from pathlib import Path
import re
import shlex
import socket
import subprocess
import sys
import tempfile
import time
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import listeners  # noqa: E402

# A ceiling for the server to start listening, the old recipes' 20 tries of 0.5 s; not a tuning value.
READY_SECONDS = 10.0
POLL_SECONDS = 0.1
# At most this many candidates are started in all when the port one was handed is taken by another process: the three that
# quality.LISTEN_TRIES allows the held-out checks.
TRIES = 3


def fail(reason: str) -> None:
    print("FAIL: " + reason)
    sys.exit(1)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def listening_pids(port: int) -> set[int]:
    """The pids listening on TCP `port`; raises listeners.Unobserved where lsof cannot say."""
    return listeners.listening_pids(port)


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


class Problem(NamedTuple):
    """Why a candidate is not ready, and whether another process holds the port it was handed."""

    reason: str
    taken: bool


def port_taken(stderr: Path, port: int) -> bool:
    """Recognize one Node listen collision whose reported TCP endpoint uses the assigned port."""
    try:
        text = stderr.read_text(errors="replace")
    except OSError:
        return False
    # Count Node error headers as well as bare listen/bind diagnostics. Stack
    # metadata cannot supply a missing endpoint or resolve mixed startup errors.
    errors = re.findall(
        r"^[ \t]*((?:[\w.$]*Error(?: \[[A-Z][A-Z0-9_]*\])?:|(?:listen|bind) [A-Z][A-Z0-9_]*\b).*)$",
        text, re.MULTILINE,
    )
    if len(errors) != 1:
        return False
    endpoint = re.fullmatch(r"listen EADDRINUSE: address already in use (\S+):([0-9]+)", errors[0].removeprefix("Error: "))
    if endpoint is None or endpoint[2] != str(port):
        return False
    try:
        ipaddress.ip_address(endpoint[1])
    except ValueError:
        return False
    return True


def candidate_problem(proc: subprocess.Popen, port: int, stderr: Path) -> Problem | None:
    """None once the port listens and every listener on it is the candidate's; else why not. `taken` is true where another
    process holds the port: the candidate exited with EADDRINUSE naming it, or a process outside the candidate's group listens."""
    deadline = time.monotonic() + READY_SECONDS
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return Problem(f"the candidate exited (rc {proc.returncode}) before it listened on PORT={port}: {tail(stderr)}",
                           port_taken(stderr, port))
        try:
            pids = listening_pids(port)
        except listeners.Unobserved as why:
            return Problem(f"cannot confirm who listens on port {port} ({why}), so no response is accepted", False)
        if pids:
            candidate = {pid: in_group(pid, proc.pid) for pid in pids}
            if all(candidate.values()):
                return None
            foreign = sorted(pid for pid, belongs in candidate.items() if not belongs)
            return Problem(f"port {port} is answered by pid {', '.join(map(str, foreign))}, not by the candidate (pid {proc.pid}), "
                           f"so its responses are refused; candidate stderr: {tail(stderr)}", True)
        time.sleep(POLL_SECONDS)
    return Problem(f"the candidate did not listen on PORT={port} within {READY_SECONDS:.0f} s: {tail(stderr)}", False)


def wait_for_candidate(proc: subprocess.Popen, port: int, stderr: Path) -> None:
    """Return once the candidate listens and is the port's only listener; else print the FAIL line and exit 1."""
    problem = candidate_problem(proc, port, stderr)
    if problem:
        fail(problem.reason)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", default="node server.js", help="the candidate's start command (default: node server.js)")
    p.add_argument("command", nargs=argparse.REMAINDER, help="-- then the check's argv, run once the candidate listens, "
                   "with PORT and BASE set")
    args = p.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        p.error("no check command after --")
    pinned = os.environ.get("E2E_SERVE_PORT")
    handed = []
    with tempfile.TemporaryDirectory(prefix="e2e-serve-") as scratch:
        for attempt in range(1, TRIES + 1):
            port = int(pinned or free_port())
            handed.append(port)
            env = dict(os.environ, PORT=str(port), BASE=f"http://127.0.0.1:{port}")
            stderr = Path(scratch) / f"server-{attempt}.stderr"
            with stderr.open("w") as err:
                proc = subprocess.Popen(shlex.split(args.start), env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                        stderr=err, start_new_session=True)
            try:
                problem = candidate_problem(proc, port, stderr)
                if problem is None:
                    done = subprocess.run(command, env=env, stdin=subprocess.DEVNULL)
                    if done.returncode:
                        print(f"check exited {done.returncode}; candidate stderr: {tail(stderr)}")
                    return done.returncode
            finally:
                listeners.end_group(proc.pid)  # only the group this check started
                proc.wait()
            if pinned or not problem.taken:
                fail(problem.reason)
            if attempt == TRIES:
                fail(f"{problem.reason} (started {attempt} times, on ports {', '.join(map(str, handed))}; each was taken by another process)")
            print(f"serve.py: another process took PORT={port}; starting the candidate again on another port (start {attempt + 1} of {TRIES})",
                  file=sys.stderr)
    return 1  # not reached: the last start returns or fails


if __name__ == "__main__":
    raise SystemExit(main())
