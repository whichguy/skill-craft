#!/usr/bin/env python3
"""Lay the `defaults` rows of the Ratchet session's deliveries beside the asking-later lists (journal section 61).

No model is called. From a git ref it reads, for each delivery of the `defaults` list, the rows the specification
recorded for the requester, the specification as accepted and the blind reader's answer; from this folder it reads
the first decision of each of the 27 lists of the asking-later test. It prints every line it matched, so that the
reading can be checked by eye: the word patterns only find lines, they do not judge them.

Usage: cross_reading.py [--ref REF] > evidence/ask-later/cross-reading-defaults.txt
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
THEIRS = "docs/experiments/ratchet-pilot-20261120/shiploop-defaults/evidence"
DELIVERIES = (
    ("wave-1/d1", "Sol"),
    ("wave-1/d2", "Sol"),
    ("wave-1/d3", "Sol"),
    ("wave-2/d4", "Sol"),
    ("wave-2/d5", "Sol"),
    ("wave-2/d6", "Sol"),
    ("sonnet-1/s1", "Sonnet"),
)
WAY_BACK = re.compile(r"roll(?:ed|ing|s)?[ -]?back|\b1\.4\.0\b", re.IGNORECASE)
LOSS = re.compile(r"drop|discard|strip|preserv|restore|re-sav|separate copy|due-bearing copy", re.IGNORECASE)
POINTS = {"S": "after the specification", "P": "plan and test cases written", "T": "after the tests ran"}


def shown(ref: str, path: str) -> list[str]:
    """Return the lines of one file at a git ref."""
    out = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{ref}:{path}"], capture_output=True, text=True, check=True
    )
    return out.stdout.splitlines()


def theirs(ref: str) -> None:
    """Print, per delivery, the rows and every line of the specification and the reader that names the way back."""
    told = {"Sol": [0, 0, 0], "Sonnet": [0, 0, 0]}  # deliveries, rows, deliveries with a row on the way back
    spoken = {"Sol": 0, "Sonnet": 0}
    for name, driver in DELIVERIES:
        rows = [line for line in shown(ref, f"{THEIRS}/{name}/rows.txt") if line.strip()]
        on_rows = [line for line in rows if WAY_BACK.search(line)]
        spec = [line for line in shown(ref, f"{THEIRS}/{name}/spec-as-accepted.md") if WAY_BACK.search(line)]
        loss = [line for line in spec if LOSS.search(line)]
        reader = [line for line in shown(ref, f"{THEIRS}/{name}/reader-answer.md") if WAY_BACK.search(line)]
        told[driver][0] += 1
        told[driver][1] += len(rows)
        told[driver][2] += bool(on_rows)
        spoken[driver] += bool(loss)
        print(f"== {name} ({driver}): {len(rows)} rows; rows naming the way back: {len(on_rows)}")
        for line in rows:
            print(f"   row   {line[:150]}")
        print(f"   specification lines naming the way back: {len(spec)}; of them with a word of loss or keeping: {len(loss)}")
        for line in spec:
            mark = "LOSS" if LOSS.search(line) else "    "
            print(f"   spec {mark} {line.strip()[:330]}")
        print(f"   blind reader's lines naming the way back: {len(reader)}")
        for line in reader:
            print(f"   reader {line.strip()[:330]}")
        print()
    for driver, (deliveries, rows, with_row) in told.items():
        print(
            f"{driver}: {deliveries} deliveries, {rows} rows; a row names the way back in {with_row};"
            f" the specification has a line on it with a word of loss or keeping in {spoken[driver]}"
        )


def mine() -> None:
    """Print the first decision of each asking-later list and count those that name the way back."""
    evidence = HERE / "evidence" / "ask-later"
    key = json.loads((evidence / "key.json").read_text(encoding="utf-8"))
    rows = []
    for path in sorted((evidence / "lists").glob("*.json")):
        one = json.loads(path.read_text(encoding="utf-8"))
        cut = key[one["code"]]
        first = one["decisions"][0]["decision"]
        rows.append((list(POINTS).index(cut["point"]), Path(cut["delivery"]).name, one["repeat"], first))
    rows.sort()
    named = sum(bool(WAY_BACK.search(first)) for *_, first in rows)
    print()
    print(f"asking-later lists: {len(rows)}; the first decision names the way back in {named}")
    for point, delivery, repeat, first in rows:
        mark = "WAY-BACK" if WAY_BACK.search(first) else "        "
        print(f"   {list(POINTS)[point]} {delivery} r{repeat} {mark} {first[:210]}")


def main() -> int:
    """Print both sides."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ref", default="shiploop-defaults-2c3d50", help="git ref that holds the Ratchet evidence")
    args = parser.parse_args()
    ref = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", args.ref], capture_output=True, text=True, check=True
    ).stdout.strip()
    print(f"the Ratchet session's evidence read at {args.ref} = {ref}")
    print("patterns: way back = " + WAY_BACK.pattern)
    print("          loss or keeping = " + LOSS.pattern)
    print()
    theirs(ref)
    mine()
    return 0


if __name__ == "__main__":
    sys.exit(main())
