#!/usr/bin/env python3
"""R8 probe: in cohort traces, list the shell commands between each `backchain.py record` and the Until Loop `done`.

Read-only over argv[1] (the cohort runs/ directory). Prints, per candidate run, every command_execution with a
short label, then for each record the commands up to and including the next `done` call.
"""
import json
import re
import sys
from pathlib import Path

RUNS = Path(sys.argv[1])
names = sys.argv[2:] or sorted(p.name for p in RUNS.iterdir() if "-candidate-" in p.name)


def label(cmd):
    if re.search(r"backchain\.py['\"]? +record\b|backchain\.py record| record --run", cmd):
        return "RECORD"
    if "UNTIL-LOOP-CHECK" in cmd or re.search(r"until_loop_ephemeral\.py['\"]? +record\b", cmd):
        return "VERIFY_SCRIPT"
    if re.search(r"until_loop_ephemeral\.py['\"]? +done\b", cmd) or " done --state" in cmd:
        return "DONE"
    if re.search(r"until_loop_ephemeral\.py['\"]? +start\b", cmd):
        return "START"
    if re.search(r"backchain\.py['\"]? +(\w+)", cmd):
        return "BC_" + re.search(r"backchain\.py['\"]? +(\w+)", cmd).group(1).upper()
    return "OTHER"


summary = {}
for name in names:
    events = RUNS / name / "events.jsonl"
    cmds = []
    for line in events.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        item = e.get("item") or {}
        if e.get("type") == "item.completed" and item.get("type") == "command_execution":
            cmds.append(item.get("command", ""))
    labels = [label(c) for c in cmds]
    # combined commands: one shell call can contain several steps
    multi = []
    for c in cmds:
        parts = [p for p in ("RECORD" if re.search(r"backchain\.py['\"]? +record\b| record --run", c) else None,
                             "VERIFY" if "UNTIL-LOOP-CHECK" in c else None,
                             "DONE" if re.search(r"until_loop_ephemeral\.py['\"]? +done\b", c) else None) if p]
        multi.append(parts)
    windows = []
    for i, lab in enumerate(labels):
        if "RECORD" in multi[i]:
            j = i
            while j < len(cmds) and "DONE" not in multi[j]:
                j += 1
            windows.append({"record_index": i, "done_index": j if j < len(cmds) else None,
                            "calls_record_to_done_inclusive": (j - i + 1) if j < len(cmds) else None,
                            "steps_in_window": [multi[k] or [labels[k]] for k in range(i, min(j + 1, len(cmds)))]})
    summary[name] = {"total_shell_calls": len(cmds), "labels": labels, "windows": windows}
    if "-v" in sys.argv[0:0]:
        pass

for name, s in summary.items():
    print(name, "shell calls:", s["total_shell_calls"])
    print("  sequence:", " ".join(s["labels"]))
    for w in s["windows"]:
        print("  record->done:", w["calls_record_to_done_inclusive"], "calls;", w["steps_in_window"])
