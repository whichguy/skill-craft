#!/usr/bin/env python3
"""Read archived deliveries of the due-times case: what the spec stage recorded about the start-up point.

Usage: ``baseline_read.py RUN [RUN ...]``, each RUN a delivery's output folder relative to the home directory.  For each
it prints the accepted spec result's summary and keys, the lines of the living specification that touch the point
(marked CHOICE-WORD when the line also holds a word such as default, assumed, chose or unresolved; read each, because
"by default" in a sentence about hours is not a choice recorded), intake's questions on the point, and whether the
report's Open items mention it.  It reads the runs' files and changes nothing.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

HOME = pathlib.Path.home()
FENCE = re.compile(r"```shiploop-state\n(.*?)\n```", re.DOTALL)
POINT = re.compile(r"start|boot|launch|backfill|back-fill|migrat", re.IGNORECASE)
CHOICE = re.compile(r"default|assum|chose|chosen|decid|decision|open gap|unresolved|not stated|does not say|"
                    r"unspecified|left open", re.IGNORECASE)
OPEN_ITEMS = re.compile(r"<h2>Open items</h2>(.*?)<h2>", re.DOTALL)


def results(run: pathlib.Path) -> list[dict]:
    """Every stage result record of the run that parses, in file order."""
    found = []
    for path in sorted(run.glob("**/run/results/*.md")):
        fenced = FENCE.search(path.read_text(errors="replace"))
        if not fenced:
            continue
        try:
            found.append(json.loads(fenced.group(1)))
        except json.JSONDecodeError:
            print(f"  unreadable result record: {path.name}")
    return found


def read(relative: str) -> None:
    run = HOME / relative
    records = results(run)
    spec = [record for record in records if record.get("stage") == "spec" and isinstance(record.get("result"), dict)
            and record["result"].get("outcome") == "done"]
    intake = [record for record in records if record.get("stage") == "intake"]
    print("=" * 110)
    print(relative, "| results", len(records), "| spec results", len(spec))
    if not spec:
        return
    result = spec[-1]["result"]
    summary = str(result.get("summary", ""))
    print(f"  spec summary ({len(summary)} chars): {summary[:900]}")
    print("  keys:", sorted(result))
    specs = sorted(run.glob("work/**/docs/shiploop/spec.md")) or sorted(run.glob("**/docs/shiploop/spec.md"))
    if specs:
        text = specs[0].read_text(errors="replace")
        lines = [line.strip() for line in text.splitlines() if POINT.search(line)]
        ids = set(re.findall(r"\bR-\d+\b", text))
        print(f"  spec.md: {len(text.split())} words, {len(ids)} R ids; lines on the point: {len(lines)}")
        for line in lines[:6]:
            print(f"    [{'CHOICE-WORD' if CHOICE.search(line) else 'plain'}] {line[:330]}")
    for record in intake[-1:]:
        questions = (record.get("result") or {}).get("questions") or []
        hits = [(row.get("id"), row.get("route"), str(row.get("question"))[:140], "default=" + str(row.get("default"))[:120])
                for row in questions if POINT.search(json.dumps(row))]
        print(f"  intake questions: {len(questions)}; on the point: {hits}")
    reports = sorted(run.glob("**/run/report.html"))
    if reports:
        section = OPEN_ITEMS.search(reports[0].read_text(errors="replace"))
        body = section.group(1) if section else ""
        rows = body.count("<tr>") - (1 if "<thead>" in body else 0) if body else "no section"
        print(f"  report Open items: {rows} rows; mentions the point: {bool(POINT.search(body))}")


if __name__ == "__main__":
    for name in sys.argv[1:]:
        read(name)
