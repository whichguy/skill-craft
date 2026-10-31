#!/usr/bin/env python3
"""Count classification.json against peek.json; refuse when the two no longer describe the same rows.

classification.json is one reader's hand classification of the strict rows (README.md section 2).  A rerun of peek.py on a
grown run set changes the rows, and a stale classification would then count the wrong texts, so this script checks every
row's run and text start before it prints a number.

Usage: ``python3 summarize.py``
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    peek = json.loads((HERE / "peek.json").read_text(encoding="utf-8"))
    classification = json.loads((HERE / "classification.json").read_text(encoding="utf-8"))
    rows, entries, classes = peek["strict"], classification["entries"], classification["classes"]
    problems = []
    if len(rows) != len(entries):
        problems.append(f"peek.json has {len(rows)} strict rows, classification.json {len(entries)}")
    for index, (row, entry) in enumerate(zip(rows, entries), 1):
        if row["run"] != entry["run"] or not row["text"].startswith(entry["text_start"]):
            problems.append(f"row {index} is {row['run']!r}, classification.json holds {entry['run']!r}")
        if entry["class"] not in classes:
            problems.append(f"row {index} has the unknown class {entry['class']!r}")
    if problems:
        print("REFUSED: classification.json does not match peek.json:", *problems, sep="\n  ")
        return 1
    summary = peek["summary"]
    fine = Counter(entry["class"] for entry in entries)
    coarse = Counter(classification["coarse"][entry["class"]] for entry in entries)
    print(f"runs that reached handoff: {summary['reached_handoff']} of {summary['readable']} readable")
    print(f"`Open for the next run` has text (loose): {summary['open_next_loose']}; real content (strict): {len(entries)}")
    print("\nfine classes (one reader, README.md section 2):")
    for name, meaning in classes.items():
        print(f"  {name:<11} {fine.get(name, 0):>2}  {meaning}")
    print("\ncoarse:")
    for name in dict.fromkeys(classification["coarse"].values()):
        print(f"  {name:<30} {coarse.get(name, 0):>2}")
    arguable = [str(index) for index, entry in enumerate(entries, 1) if entry["arguable"]]
    print("\narguable rows (a second reader could move them): " + ", ".join(arguable))
    print("\nrows (* = arguable):")
    for index, entry in enumerate(entries, 1):
        print(f"{index:>3} {entry['class']:<10}{'*' if entry['arguable'] else ' '} {entry['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
