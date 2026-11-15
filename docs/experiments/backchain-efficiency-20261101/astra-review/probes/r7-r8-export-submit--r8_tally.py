#!/usr/bin/env python3
"""Tally, over all candidate cohort runs: cycles recorded, shell calls from each successful record to the done that
submits it, whether done was called directly or through a hand-written Python wrapper, and failed records/dones.
Read-only over argv[1]."""
import json
import re
import statistics
import sys
from pathlib import Path

RUNS = Path(sys.argv[1])
REC = re.compile(r"backchain\.py['\"]? +record\b| record --run")
DONE_DIRECT = re.compile(r"until_loop_ephemeral\.py['\"]? +done\b")
rows = []
for run in sorted(p for p in RUNS.iterdir() if "-candidate-" in p.name):
    cmds = []
    for line in (run / "events.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        item = e.get("item") or {}
        if e.get("type") == "item.completed" and item.get("type") == "command_execution":
            cmds.append(item)
    kinds = []
    for c in cmds:
        cmd, out = c["command"], c.get("aggregated_output") or ""
        k = set()
        if REC.search(cmd):
            k.add("record_ok" if "recorded:" in out else "record_refused")
        if "UNTIL-LOOP-CHECK" in cmd:
            k.add("verify")
        if DONE_DIRECT.search(cmd):
            k.add("done_direct")
        elif "done_argv" in cmd:
            k.add("done_wrapped")
        kinds.append(k)
    windows = []
    for i, k in enumerate(kinds):
        if "record_ok" in k:
            j = next((j for j in range(i, len(kinds)) if kinds[j] & {"done_direct", "done_wrapped"}), None)
            if j is not None:
                windows.append((j - i + 1, sorted(kinds[j] & {"done_direct", "done_wrapped"})[0],
                                sum("verify" in kinds[x] for x in range(i, j + 1))))
    rows.append({"run": run.name, "shell_calls": len(cmds), "records_ok": sum("record_ok" in k for k in kinds),
                 "records_refused": sum("record_refused" in k for k in kinds),
                 "windows": windows})

all_w = [w for r in rows for w in r["windows"]]
print("candidate runs:", len(rows))
print("successful records:", sum(r["records_ok"] for r in rows), " refused records:", sum(r["records_refused"] for r in rows))
print("record->done windows:", len(all_w))
print("calls per window (inclusive) distribution:", {n: sum(1 for w in all_w if w[0] == n) for n in sorted({w[0] for w in all_w})})
print("done via direct argv:", sum(1 for w in all_w if w[1] == "done_direct"), " via hand-written python wrapper:",
      sum(1 for w in all_w if w[1] == "done_wrapped"))
print("verify runs per window:", {n: sum(1 for w in all_w if w[2] == n) for n in sorted({w[2] for w in all_w})})
print("shell calls per run: median", statistics.median(r["shell_calls"] for r in rows), "range",
      min(r["shell_calls"] for r in rows), max(r["shell_calls"] for r in rows))
for r in rows:
    print(" ", r["run"], r["shell_calls"], "calls; records ok/refused", r["records_ok"], r["records_refused"], r["windows"])
