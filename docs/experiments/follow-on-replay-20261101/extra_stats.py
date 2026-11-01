"""Post-hoc statistics for the M1 replay, written after the readers answered (not pre-registered; compare.py is).

Prints how many rows all four readers labelled alike, the class totals of each reader, and every row on which any two
readers differ, with each reader's label.  Usage: ``python3 -B extra_stats.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import compare

HERE = Path(__file__).resolve().parent


def main() -> int:
    labels, arguable, coarse, classes, notes = compare.load_all()
    rows = sorted(labels["first"])
    readers = [name for name in compare.READERS if name in labels]
    texts = {row["id"]: row["text"] for row in json.loads((HERE / "rows.json").read_text(encoding="utf-8"))["rows"]}
    same = [row for row in rows if len({labels[name][row] for name in readers}) == 1]
    print(f"rows labelled alike by all {len(readers)} readers: {len(same)} of {len(rows)}")
    print(f"... by all four at the coarse level: {sum(1 for row in rows if len({coarse[labels[name][row]] for name in readers}) == 1)} of {len(rows)}")
    print("\nclass totals per reader")
    print(f"{'':<8}" + "".join(f"{name:>9}" for name in readers))
    for kind in classes:
        print(f"{kind:<8}" + "".join(f"{sum(1 for row in rows if labels[name][row] == kind):>9}" for name in readers))
    print("\nrows on which any two readers differ (an asterisk marks a row the first reader called arguable)")
    for row in rows:
        if row in same:
            continue
        cells = "  ".join(f"{name} {labels[name][row]}" + (f" (alt {notes[name][row]['alt']})" if name in notes and notes[name][row]["alt"] else "") for name in readers)
        print(f"{row}{'*' if arguable[row] else ' '} {cells}\n      {texts[row][:150]}")
    print("\nunanimous rows by the first reader's class")
    for kind in classes:
        mine = [row for row in rows if labels["first"][row] == kind]
        if mine:
            print(f"  {kind:<11} {sum(1 for row in mine if row in same)} of {len(mine)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
