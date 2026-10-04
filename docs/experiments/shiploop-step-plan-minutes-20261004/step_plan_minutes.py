#!/usr/bin/env python3
"""Wall minutes of the first step-plan stage in an E2E run output directory (read-only).

Usage: python3 step_plan_minutes.py <run output dir containing events.jsonl and timeline.jsonl>

What it measures: the time from the step-plan HEAD line to the COMPLETE line, both found in events.jsonl and
timed through timeline.jsonl (line number to wall-clock seconds).
  * head line: the first tool result whose text starts "ShipLoop navigator | step-plan" (the packet head the
    model receives when the step-plan action begins; its action id is read from the printed --action=nav-...);
  * end: the first `shiploop complete` tool call that names that action id.
It reads nothing but those two files and writes nothing, so it is safe on a run that is still live.

Why it exists: metrics.json attributed 1,679.5 s to the step-plan stage on the Luna 1.16.1 battleship run
(/Users/dadleet/e2e-runs/20261003/v1161-battleship-luna), which is wrong (see test/shiploop_e2e/LEARNINGS.md,
"superseded 2026-10-04"). This method reproduced 163.9 minutes on that baseline (head line 2179, complete line
2950; the plan doc records the Backchain loop alone as 135.8 minutes of it). Run it on a later run's output directory and compare
against 163.9; the I2b verification (docs/shiploop-i2b-trim-planning-prompts-plan-2026-10-04.md, V2 signal c)
uses it that way.

Limits: it reports the FIRST step-plan stage only, and the line-to-time mapping needs the timeline.jsonl the
harness writes; a run without one prints nothing useful. A run that never completes step-plan prints
"no completed step-plan found".
"""
import json, re, sys
out = sys.argv[1]
t = {}
for line in open(f"{out}/timeline.jsonl"):
    d = json.loads(line); t[d["line"]] = d["t"]
def at(i):
    return next(t[j] for j in range(i, i + 50) if j in t)
lines = open(f"{out}/events.jsonl").read().splitlines()
head = action = None
for i, s in enumerate(lines):
    if head is None and "ShipLoop navigator | step-plan" in s and '"tool_call_update"' in s[:30]:
        m = re.search(r"--action=(nav-[0-9a-f]+)", s)
        head, action = i, m.group(1) if m else None
    elif head is not None and s.startswith('{"type": "tool_call"') and "shiploop complete" in s and f"--action={action}" in s:
        print(f"step-plan head line {head}, complete line {i}: {(at(i) - at(head)) / 60:.1f} min")
        break
else:
    print("no completed step-plan found")
