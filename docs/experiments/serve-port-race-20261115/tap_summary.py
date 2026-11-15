#!/usr/bin/env python3
"""The table of a tapped run: how many times each suite started a candidate through serve.py, and how those runs ended.

    python3 tap_summary.py OUT_DIR SUITE [SUITE ...]       (OUT_DIR holds run_tap.sh's tap-SUITE.jsonl files)

A run that printed nothing passed. "check exited N" is the check's own verdict (a defect the calibration expects to fail is one). A FAIL line is
serve.py refusing: "answered by pid" (another process listens on the port: the ownership check), "exited ... before it listened" (and, of
those, how many name EADDRINUSE: the signature of the CI failure), or any other FAIL.
"""

import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
print(f"{'suite':20} {'runs':>5} {'passed':>7} {'check exited N':>15} {'FAIL answered by pid':>21} {'FAIL exited early':>18} {'of them EADDRINUSE':>19} {'other FAIL':>11}")
for suite in sys.argv[2:]:
    path = out / f"tap-{suite}.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    printed = [r["printed"] for r in rows]
    answered = sum("answered by pid" in text for text in printed)
    early = [text for text in printed if "before it listened" in text]
    other = sum("FAIL:" in text and "answered by pid" not in text and "before it listened" not in text for text in printed)
    print(f"{suite:20} {len(rows):5} {sum(not text for text in printed):7} {sum(text.startswith('check exited') for text in printed):15} "
          f"{answered:21} {len(early):18} {sum('EADDRINUSE' in text for text in early):19} {other:11}")
