#!/usr/bin/env python3
"""Regenerate compactions.json: what the model did first after each compaction of the saved 2026-10 runs.

Reads the full saved runs under /Users/dadleet/e2e-runs (no test does), runs the harness's own metrics.collect on each, and keeps
one compact row per compaction from ``fresh_starts`` (kind "compaction"): the window to the next accepted action, the first
grounding call, and the very first tool call after the compaction, classified by the same function the windows use (metrics.call_kind: `next`,
`improve-next`, `packet`, another ShipLoop `verb`, `skill-card`, `plain`). Record-only; no verdict.

    python3 docs/experiments/reorientation-20261009/measure.py > docs/experiments/reorientation-20261009/compactions.json
"""

from __future__ import annotations

import glob
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import metrics  # noqa: E402

RUNS = Path("/Users/dadleet/e2e-runs")
GROK = ["20261005/v1210-battleship-grok-medium", "20261006/v1220-battleship-grok-medium-none",
        "20261007/v1230-battleship-grok-none", "20261008/r1-battleship-grok-none", "20261008/r2-battleship-grok-none",
        "20261008/r3-battleship-grok-none"]
CODEX = ["20261003/battleship-luna", "20261003/v1161-battleship-luna", "20261004/v1200-battleship-luna",
         "20261005/v1210-battleship-luna-xhigh"]
# The three Grok runs of the prototype that first counted "a packet read in 6 of 12".
PROTOTYPE = ["20261007/v1230-battleship-grok-none", "20261008/r1-battleship-grok-none", "20261008/r3-battleship-grok-none"]


def first_call(events: Path, line: int) -> dict | None:
    """The first tool call at or after ``line``, as the harness's own classifier (metrics.call_kind) reads it, and its tool name."""
    log = metrics.ToolLog()
    for _number, event in metrics.event_range(events, line, line + 3000):
        for call_id, tool, arg in metrics.tool_call_events(event):
            return {"kind": metrics.call_kind(log.calls[log.call(None, call_id, tool, arg)]), "tool": tool}
    return None


def main() -> None:
    rows = []
    for name in GROK + CODEX:
        out = RUNS / name
        runs = glob.glob(str(out / ".shiploop-runs" / "*" / "run"))
        collected = metrics.collect(out, Path(runs[0]) if runs else None)
        for block in collected["fresh_starts"]:
            if block["kind"] != "compaction":
                continue
            window = block["reorientation"]
            first = first_call(out / "events.jsonl", block["events_line"])
            rows.append({"run": name, "host": block["host"], "events_line": block["events_line"],
                         "measured": window["measured"], "reason": window.get("reason"),
                         "stage_in_flight": block["stage_in_flight"],
                         "first_call": first and first["kind"], "first_grounding": window["first_grounding"],
                         "calls_before_grounding": window["calls_before_grounding"], "tool_calls": window.get("tool_calls"),
                         "seconds": window.get("seconds"), "next_calls": window["recovery"]["next_calls"],
                         "rewrote": (window.get("rewrote") or {}).get("paths"),
                         "failures": len(window["failures"]["items"]) if window["measured"] else None})
    summary = {}
    for label, names in (("prototype (r1, r3, v1230 Grok)", PROTOTYPE), ("all six Grok runs", GROK), ("all four Luna runs", CODEX)):
        picked = [r for r in rows if r["run"] in names]
        summary[label] = {"compactions": len(picked), "first_call": dict(Counter(r["first_call"] for r in picked)),
                          "first_grounding": dict(Counter(r["first_grounding"] for r in picked)),
                          "grounding_is_the_first_call": sum(r["calls_before_grounding"] == 0 for r in picked)}
    print(json.dumps({"summary": summary, "compactions": rows}, indent=1))


if __name__ == "__main__":
    main()
