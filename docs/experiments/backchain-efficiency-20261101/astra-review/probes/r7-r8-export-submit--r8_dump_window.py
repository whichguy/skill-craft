#!/usr/bin/env python3
"""Print every shell command (truncated) from the first `record` to `finish` in the named cohort runs, with exit
codes and a short output head. Read-only over argv[1]."""
import json
import re
import sys
from pathlib import Path

RUNS = Path(sys.argv[1])
WIDTH = 700
for name in sys.argv[2:]:
    cmds = []
    for line in (RUNS / name / "events.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        item = e.get("item") or {}
        if e.get("type") == "item.completed" and item.get("type") == "command_execution":
            cmds.append(item)
    first = next((i for i, c in enumerate(cmds) if re.search(r"backchain\.py['\"]? +record\b| record --run", c["command"])), None)
    print("=" * 30, name, "first record at", first, "of", len(cmds))
    for i, c in enumerate(cmds):
        if first is None or i < first - 1:
            continue
        cmd = c["command"]
        out = (c.get("aggregated_output") or "").strip().replace("\n", " | ")
        print(f"[{i}] exit={c.get('exit_code')} CMD: {cmd[:WIDTH]}")
        print(f"      OUT: {out[:300]}")
