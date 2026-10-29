#!/usr/bin/env python3
"""Summarise slices of the live session-end round as one JSON document: what ran, what the harness check read, and when the
run's keepalive claim changed hands.

    python3 docs/shiploop-owed-outcome-evidence/round_summary.py SLICE_OUTPUT_DIR [SLICE_OUTPUT_DIR ...] > summary.json

Per slice it reads the folder's own records (invocation.json, slice-result.json, clear.json, sessions.jsonl, metrics.json), the
run's trace through test/shiploop_e2e/run_trace.py (the `hook` rows and `checks`, re-read now, not the copy in metrics.json) and
owner_watch.py's owner-watch.jsonl. It reports; it does not judge. The claim timeline is relative to the first session's end,
so a takeover reads as seconds after the kill and a release by the host's hook as seconds after the signal.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "test" / "shiploop_e2e"))
import run_trace


def rows(path: Path) -> list[dict]:
    found = []
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return found
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            found.append(row)
    return found


def load(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def summarise(folder: str) -> dict:
    out = Path(folder).expanduser().resolve()
    invocation = load(out / "invocation.json") or {}
    result = load(out / "slice-result.json") or {}
    metrics = load(out / "metrics.json") or {}
    clears = load(out / "clear.json") or []
    sessions = rows(out / "sessions.jsonl")
    watch = rows(out / "owner-watch.jsonl")
    run_dir = (invocation.get("seeded") or {}).get("run_dir")
    traced = run_trace.read(Path(run_dir)) if run_dir else None
    checks = run_trace.checks(traced) if traced and "error" not in traced else None
    session_ends = [row for row in sessions if row.get("row") == "end"]
    ends_at = session_ends[0].get("t") if session_ends else None
    claims = []
    for row in watch:
        if row.get("event") != "claim":
            continue
        claim = row.get("claim")
        claims.append({"seconds_after_first_session_end": None if ends_at is None else round(row["t"] - ends_at, 2),
                       "at": row.get("at"), "owner": claim and claim.get("owner"), "pid": claim and claim.get("pid"),
                       "pid_alive": row.get("pid_alive")})
    hooks = []
    for hook in (traced or {}).get("hooks", []):
        hooks.append({key: hook.get(key) for key in ("i", "at", "host", "hook", "decision", "released", "reason", "why", "session")})
    return {
        "output": str(out),
        "build": {"local_head": invocation.get("local_head"), "plugin_versions": invocation.get("versions"),
                  "host": invocation.get("host"), "backend": invocation.get("backend"), "model": invocation.get("model"),
                  "effort": invocation.get("effort"), "clear_at": invocation.get("clear_at"),
                  "clear_signal": invocation.get("clear_signal")},
        "result": {"pass": result.get("pass"), "verdicts": result.get("verdicts"),
                   "sessions": [{"status": s.get("status"), "returncode": s.get("returncode"),
                                 "elapsed_seconds": s.get("elapsed_seconds"), "end_signal": s.get("end_signal")}
                                for s in result.get("sessions", [])],
                   "cost_usd": metrics.get("cost_usd"), "turns": metrics.get("turns"),
                   "clear_records": [{"n": c.get("n"), "stopped": c.get("stopped"), "end_signal": c.get("end_signal")}
                                     for c in clears]},
        "trace": {"status": (traced or {}).get("status"), "counts": (traced or {}).get("counts"), "hook_rows": hooks},
        "checks": {name: {"verdict": row["verdict"], "evidence": row["evidence"], "lines": row.get("lines")}
                   for name, row in (checks or {}).items()},
        "claim_timeline": claims,
    }


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    print(json.dumps([summarise(folder) for folder in argv], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
