#!/usr/bin/env python3
"""Log every change to one slice's ShipLoop keepalive owner claim, with the time it happened.

    python3 docs/shiploop-owed-outcome-evidence/owner_watch.py SLICE_OUTPUT_DIR [--seconds N] [--interval S]

The run trace holds no claim row, and it records a stop decision only when the session that took a run happens to end
a turn, so a slice can free a run and have it taken without the trace showing either. The claim file is the record of
both: `<keepalive home>/runs/<sha256(run_dir)[:32]>.json` (shiploop_keepalive._owner_path) holds the owner, when it was
last seen and the host process it recorded. This reads that file from outside the run, every INTERVAL seconds, and
appends a line to `SLICE_OUTPUT_DIR/owner-watch.jsonl` whenever the owner, the recorded process or that process's
liveness changes, or the file appears or goes. It writes nothing else and touches nothing of the run's.

What each line shows in a round (times are the watcher's own wall clock, to the millisecond):
- the session's SessionEnd hook freed the run: the claim goes (`claim: null`) within a second or so of the signal, while the
  recorded process may still be alive; the next session's claim is a later line with a different owner;
- a killed host (SIGKILL): the claim stays with the dead owner (`pid_alive: false`), and the next session's claim replaces
  it at once, well inside OWNER_STALE_SECONDS, which is the takeover.

The watcher waits for SLICE_OUTPUT_DIR/invocation.json (the slice writes it once seeded), reads the run directory from it,
and stops after SECONDS (default 7200), when slice-result.json appears, or on SIGTERM or SIGINT. It uses the keepalive
module of this checkout for the claim's path, with the environment it was started in (SHIPLOOP_KEEPALIVE_HOME and
XDG_STATE_HOME, as the slice's host sees them: the Claude host keeps the real HOME).
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "shiploop" / "scripts"))
import shiploop_keepalive as keepalive

LOG = "owner-watch.jsonl"
stopping = False


def _stop(*_: object) -> None:
    global stopping
    stopping = True


def pid_alive(pid: object) -> bool | None:
    """Whether a process with this pid exists (signal 0), None when no pid was recorded. A reused pid reads alive; the
    claim's own start time is in the line for anyone who needs the distinction."""
    if not isinstance(pid, int):
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def snapshot(run_dir: str) -> dict:
    """The claim as it is now: {claim: {owner, seen, pid, start} or None, pid_alive}."""
    path = keepalive._owner_path(run_dir)
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {"claim": None, "pid_alive": None}
    if not isinstance(data, dict) or not data.get("owner"):
        return {"claim": None, "pid_alive": None}
    process = data.get("process") if isinstance(data.get("process"), dict) else {}
    return {"claim": {"owner": data.get("owner"), "seen": data.get("seen"), "pid": process.get("pid"),
                      "start": process.get("start")},
            "pid_alive": pid_alive(process.get("pid"))}


def key(shot: dict) -> tuple:
    claim = shot["claim"]
    return (None,) if claim is None else (claim["owner"], claim["pid"], shot["pid_alive"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("output", type=Path, help="the slice's output folder")
    parser.add_argument("--seconds", type=float, default=7200, help="stop after this long (default 7200)")
    parser.add_argument("--interval", type=float, default=0.25, help="seconds between reads (default 0.25)")
    args = parser.parse_args(argv)
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    out = args.output.expanduser().resolve()
    deadline = time.monotonic() + args.seconds
    run_dir = None
    while run_dir is None and not stopping and time.monotonic() < deadline:
        try:
            run_dir = json.loads((out / "invocation.json").read_text())["seeded"]["run_dir"]
        except (OSError, ValueError, KeyError, TypeError):
            time.sleep(1)
    if run_dir is None:
        print("owner_watch: no run directory seen (invocation.json never named one); nothing watched", file=sys.stderr)
        return 1
    last = object()
    with open(out / LOG, "a") as log:
        log.write(json.dumps({"t": round(time.time(), 3), "at": datetime.now(UTC).isoformat(timespec="milliseconds"),
                              "event": "watching", "run_dir": run_dir, "claim_file": str(keepalive._owner_path(run_dir)),
                              "interval": args.interval}) + "\n")
        log.flush()
        while not stopping and time.monotonic() < deadline and not (out / "slice-result.json").exists():
            shot = snapshot(run_dir)
            if key(shot) != last:
                last = key(shot)
                log.write(json.dumps({"t": round(time.time(), 3),
                                      "at": datetime.now(UTC).isoformat(timespec="milliseconds"),
                                      "event": "claim", **shot}) + "\n")
                log.flush()
            time.sleep(args.interval)
        log.write(json.dumps({"t": round(time.time(), 3), "at": datetime.now(UTC).isoformat(timespec="milliseconds"),
                              "event": "stopped", "why": "signal" if stopping else "slice finished"
                              if (out / "slice-result.json").exists() else "time"}) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
