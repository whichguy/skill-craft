#!/usr/bin/env python3
"""How often a "trailer by shape" rule and a "trailer by name" rule disagree on real commit messages (read-only).

Repeat with:  PYTHONDONTWRITEBYTECODE=1 python3 docs/experiments/commit-contract-engine-20261010/scan_trailer_shapes.py [RUNS_ROOT]

The first draft of skills/shiploop/scripts/shiploop_lessons.py treated the last paragraph of a message as the trailer
block when every line looked like ``Hyphenated-Token: value``.  Review found that a lesson written as such lines
(``Root-cause: x``, ``Follow-up: y``) would then read as empty.  This script asks, over this repository's history and
every saved E2E work repository under RUNS_ROOT (default ~/e2e-runs), how many final paragraphs have that shape, how many of
them hold none of the four trailers ShipLoop's commits end with (the names the grammar now knows), and which other
``Hyphenated-Token:`` line starts occur, i.e. what lesson text of that shape looks like in practice.  Only ``git log`` is
run.  Writes trailer-shapes.json beside this file.
"""
import collections
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
KNOWN = {"co-authored-by", "signed-off-by", "no-change-note", "skill-craft-release"}
SHAPE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+:[ \t]")
runs = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "e2e-runs"
repos = [ROOT] + [Path(r) for r in sorted(glob.glob(str(runs / "*" / "*" / "work"))) if os.path.exists(r + "/.git")]
count = collections.Counter()
other_tokens = collections.Counter()
for repo in repos:
    out = subprocess.run(["git", "-C", str(repo), "log", "--format=%H%x00%B%x01"], capture_output=True, text=True).stdout
    for entry in out.split("\x01"):
        entry = entry.strip("\n")
        if not entry:
            continue
        body = entry.split("\x00", 1)[1]
        count["commits"] += 1
        lines = body.replace("\r\n", "\n").split("\n")
        for row in lines:
            token = SHAPE.match(row)
            if token and row.split(":")[0].lower() not in KNOWN:
                other_tokens[row.split(":")[0]] += 1
        end = len(lines)
        while end and not lines[end - 1].strip():
            end -= 1
        start = end
        while start and lines[start - 1].strip():
            start -= 1
        block = lines[start:end]
        if start > 0 and block and SHAPE.match(block[0]) and all(SHAPE.match(r) or r[:1] in (" ", "\t") for r in block):
            count["final_paragraphs_that_are_all_trailer_shaped"] += 1
            names = {r.split(":")[0].lower() for r in block if SHAPE.match(r)}
            count["of_which_hold_a_known_trailer" if names & KNOWN else "of_which_hold_no_known_trailer"] += 1
result = {"repositories": len(repos), **count,
          "other_hyphenated_line_starts_top12": other_tokens.most_common(12),
          "distinct_other_hyphenated_line_starts": len(other_tokens)}
(HERE / "trailer-shapes.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
print(json.dumps(result, indent=1))
