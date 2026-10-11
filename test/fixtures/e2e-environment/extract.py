#!/usr/bin/env python3
"""Rebuild the compact extracts in this folder from the saved runs under /Users/dadleet/e2e-runs (2026-10-07 and 2026-10-08).

The tests read the extracts, never the saved runs.  This script is provenance, not a test: run it by hand on the machine
that holds the runs, then commit the result.  Each extract keeps the SHAPE of the real folder (file names, invocation*.json,
timeline.jsonl lines, state.md fence) and only the keys the harness reads:

  rounds/<run>/invocation*.json   case, host, model, effort, versions, resumed_run (the launch records of the nine round runs)
  rounds/<run>/timeline.jsonl     the first two and the last two stamps (overlap reads the first and last)
  recorded/<date>/<run>.json      pass, host, process (status, returncode, regraded) and termination of each recorded result.json
  engine/<run>/state.md           the navigator state reduced to status, stage, status_reason, the last history entry and
                                  the accepted record of the last history action (the blocked detail lives there)
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

RUNS = Path("/Users/dadleet/e2e-runs")
HERE = Path(__file__).resolve().parent
ROUND_RUNS = [f"20261008/{prefix}-{app}" for prefix in ("r1", "r2", "r3")
              for app in ("battleship-sonnet", "checkers-sonnet", "battleship-grok-none")]
ROUND_RUNS = [run for run in ROUND_RUNS if (RUNS / run).is_dir()]
RECORDED = ["20261007/v1230-battleship-grok-none", "20261007/v1230-battleship-sonnet", *ROUND_RUNS]
ENGINE_RUNS = ["20261007/v1230-battleship-grok-none", "20261008/r1-battleship-grok-none", "20261008/r3-battleship-grok-none"]
FENCE = re.compile(r"```shiploop-state\n(?P<json>.*?)\n```", re.S)


def launch_record(record: dict) -> dict:
    keep = {k: record.get(k) for k in ("case", "host", "model", "effort")}
    versions = record.get("versions") or {}
    keep["versions"] = {k: versions[k] for k in ("source", "plugin_version", "shiploop_version", "regraded") if k in versions}
    if record.get("resumed_run"):
        keep["resumed_run"] = {k: record["resumed_run"].get(k) for k in ("from_host", "from_model", "stage")}
    return keep


def rounds() -> None:
    for run in ROUND_RUNS:
        src, dst = RUNS / run, HERE / "rounds" / run.split("/")[1]
        dst.mkdir(parents=True, exist_ok=True)
        for path in sorted(src.glob("invocation*.json")):
            (dst / path.name).write_text(json.dumps(launch_record(json.loads(path.read_text())), indent=1) + "\n")
        lines = [line for line in (src / "timeline.jsonl").read_text().splitlines() if line.strip()]
        (dst / "timeline.jsonl").write_text("\n".join(lines[:2] + lines[-2:]) + "\n")


def recorded() -> None:
    for run in RECORDED:
        result = json.loads((RUNS / run / "result.json").read_text())
        process = result.get("process") or {}
        out = {"pass": result.get("pass"), "host": result.get("host"),
               "process": {k: process.get(k) for k in ("status", "returncode", "regraded") if k in process},
               "termination": result.get("termination")}
        date, name = run.split("/")
        (HERE / "recorded" / date).mkdir(parents=True, exist_ok=True)
        (HERE / "recorded" / date / f"{name}.json").write_text(json.dumps(out, indent=1) + "\n")


def engine() -> None:
    for run in ENGINE_RUNS:
        found = sorted((RUNS / run).glob(".shiploop-runs/*/run/state.md"))
        state = json.loads(FENCE.search(found[0].read_text()).group("json"))
        history = state.get("history") or []
        last = history[-1] if history else {}
        record = (state.get("accepted") or {}).get(last.get("action")) or {}
        keep_record = {k: record[k] for k in ("outcome", "blocked_by", "awaiting", "headline") if k in record}
        reduced = {k: state[k] for k in ("status", "stage", "status_reason", "work_index", "work_items", "inner_loops") if k in state}
        if "inner_loops" in reduced:  # only the loop the run was in
            index = state.get("work_index")
            items = state.get("work_items") or []
            current = items[index]["id"] if isinstance(index, int) and index < len(items) else None
            reduced["inner_loops"] = {current: state["inner_loops"].get(current)} if current else {}
            reduced["work_items"] = [{"id": item.get("id")} for item in items]
        reduced["history"] = [dict(entry, summary=str(entry.get("summary"))[:120]) for entry in history[-2:]]
        reduced["accepted"] = {last.get("action"): keep_record} if last else {}
        dst = HERE / "engine" / run.split("/")[1]
        dst.mkdir(parents=True, exist_ok=True)
        (dst / "state.md").write_text("# ShipLoop navigator state\n\n```shiploop-state\n"
                                      + json.dumps(reduced, indent=2, sort_keys=True) + "\n```\n")


if __name__ == "__main__":
    if not RUNS.is_dir():
        sys.exit(f"the saved runs are not here: {RUNS}")
    for folder in ("rounds", "recorded", "engine"):
        shutil.rmtree(HERE / folder, ignore_errors=True)
    rounds()
    recorded()
    engine()
