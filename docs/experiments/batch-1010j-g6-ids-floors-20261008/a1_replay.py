#!/usr/bin/env python3
"""Replay the recorded ids-missing outputs of a Checkers run through ``shiploop_test_counts.named``.

Question: which missing IDs does the whole-token ``inside`` relation report, against a raw substring match?  The raw match
reports ``TC-1`` as "inside" ``TC-13a ...``, a different ID, which would drop the select-and-print remedy for a test
that is simply missing.  Run from the repository root: ``python3 docs/experiments/batch-1010j-g6-ids-floors-20261008/a1_replay.py``.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_test_counts as counts  # noqa: E402

recorded = json.loads((Path(__file__).with_name("a1-recorded-ids-missing.json")).read_text())
for run in recorded["runs"]:
    names = counts.named(run["output"], run["ids"])
    lines = [line for line in counts._plain(run["output"]).splitlines() if not counts._ANNOUNCEMENT.match(line)]
    raw = sorted(i for i in names["missing"] if any(i in line and not counts._SKIP_LINE.search(line) for line in lines))
    print(run["command"])
    print("  missing:", names["missing"])
    print("  raw substring reports inside:", raw)
    print("  whole-token relation reports inside:", sorted(names["inside"]))
    for test_id in sorted(set(raw) - set(names["inside"])):
        line = next(line.strip() for line in lines if test_id in line and not counts._SKIP_LINE.search(line))
        print("  false hit of the raw match:", test_id, "in:", line[:counts.INSIDE_CHARS])
