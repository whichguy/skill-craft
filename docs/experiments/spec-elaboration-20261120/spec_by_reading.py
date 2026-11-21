#!/usr/bin/env python3
"""Do Codex runs that were given little of the spec stage's instructions write shorter specifications?

Reads run folders that exist and calls no model. For each Codex run: the share of the spec stage's instruction lines
the model was given before it submitted (packet_shown.py), and the accepted specification's words and requirement ids
(guides_test.py's snapshot, which writes its copies into a temporary folder and nothing into the run). Runs are then
grouped by case and effort, because both change a specification's length on their own. What runs happened to do is not
a test, and words are not fullness.

usage: spec_by_reading.py RUNS_ROOT [RUNS_ROOT ...]
"""

from __future__ import annotations

import statistics
import sys
import tempfile
from pathlib import Path

import guides_test as g
import packet_shown

GROUPS = (
    ("under a third", lambda share: share < 1 / 3),
    ("four fifths or more", lambda share: share >= 0.8),
)


def main() -> int:
    outs = sorted(
        {
            result.parent
            for root in sys.argv[1:]
            for depth in ("*", "*/*")
            for result in Path(root).glob(f"{depth}/result.json")
        }
    )
    scratch, rows = Path(tempfile.mkdtemp()), []
    for out in outs:
        result = g.load(out / "result.json")
        spec = (
            next(
                (
                    stage
                    for stage in packet_shown.stages_of(out)
                    if stage["stage"] == "spec"
                ),
                None,
            )
            if result.get("host") == "codex"
            else None
        )
        if not spec:
            continue
        dest = scratch / f"{out.parent.name}-{out.name}"
        dest.mkdir()
        snap, accepted = g.snapshot(out, dest), dest / "spec-accepted.md"
        if not accepted.is_file():
            print(f"left out: {'/'.join(out.parts[-2:])} ({snap.get('snapshot')})")
            continue
        measures = g.measures(accepted.read_text(errors="replace"))
        share = sum(spec["instructions"]) / len(spec["instructions"])
        rows.append(
            {
                "run": "/".join(out.parts[-2:]),
                "case": str(result.get("case")),
                "effort": str(result.get("effort")),
                "share": share,
                **measures,
                "outcome": result.get("outcome_class"),
            }
        )
    print(
        f"Codex runs with an accepted specification that could be pinned: {len(rows)}"
    )
    print()
    print(
        "case | effort | instruction lines given | accepted specification, words | requirement ids | how the run ended"
    )
    for row in sorted(rows, key=lambda row: (row["case"], row["effort"], row["share"])):
        print(
            f"{row['case']} | {row['effort']} | {row['share']:.0%} | {row['words']} | {row['requirement_ids']} | {row['outcome']}"
        )
    print()
    print(
        "case | effort | instruction lines given | runs | words: median (lowest to highest) | requirement ids: median | whole deliveries that passed"
    )
    for case, effort in sorted({(row["case"], row["effort"]) for row in rows}):
        for name, keep in GROUPS:
            group = [
                row
                for row in rows
                if (row["case"], row["effort"]) == (case, effort) and keep(row["share"])
            ]
            if group:
                words, whole = (
                    [row["words"] for row in group],
                    [row for row in group if row["outcome"] in ("PASS", "FAILED")],
                )
                ids = statistics.median(row["requirement_ids"] for row in group)
                print(
                    f"{case} | {effort} | {name} | {len(group)} | {statistics.median(words):.0f} ({min(words)} to {max(words)}) | {ids:.0f} | {sum(1 for row in whole if row['outcome'] == 'PASS')} of {len(whole)}"
                )
    return 0


if __name__ == "__main__":
    sys.exit(main())
