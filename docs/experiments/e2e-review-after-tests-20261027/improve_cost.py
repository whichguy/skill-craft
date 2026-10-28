"""Where each run's Improve minutes went: planning reviews, implement reviews and end-of-work reviews, from the
``improve-windows.txt`` tables earlier validations derived (awake minutes, one row per Improve window).

Usage: python3 improve_cost.py [LABEL:]IMPROVE_WINDOWS_TXT...  (LABEL names a file that holds one run without a
"== <run>" header)
"""

import re
import sys
from pathlib import Path

PLANNING = {"spec", "test-strategy", "plan", "step-plan", "test-spec"}
END = {"carry-forward", "system-test-author", "release-plan"}


def runs(argument):
    label, _, path = argument.rpartition(":")
    path = Path(path)
    name, rows, span = label or path.parent.name, [], None
    for line in path.read_text().splitlines():
        if line.startswith("== "):
            if rows:
                yield name, span, rows
            name, rows = line[3:].strip(), []
        elif match := re.match(r"run span .* awake ([\d.]+)", line):
            span = float(match.group(1))
        elif match := re.match(r"\s+improve after (\S+)\s+raw\s+[\d.]+\s+awake\s+([\d.]+)", line):
            rows.append((match.group(1), float(match.group(2))))
    if rows:
        yield name, span, rows


print("# Improve awake minutes by kind of review (planning / implement / end of work), and Improve's share of the run.")
print(f"{'run':36} {'run min':>8} {'Improve':>8} {'share':>6} {'planning':>9} {'implement':>10} {'end':>6}")
for argument in sys.argv[1:]:
    for name, span, rows in runs(argument):
        total = sum(minutes for _stage, minutes in rows)
        kinds = {kind: sum(m for stage, m in rows if (stage in group if group else stage == "implement"))
                 for kind, group in (("planning", PLANNING), ("implement", None), ("end", END))}
        reviews = sum(stage == "implement" for stage, _m in rows)
        print(f"{name:36} {span:8.1f} {total:8.1f} {total / span:6.0%} {kinds['planning']:9.1f} "
              f"{kinds['implement']:6.1f} ({reviews:2}) {kinds['end']:6.1f}  "
              f"implement share {kinds['implement'] / total:.0%}")
