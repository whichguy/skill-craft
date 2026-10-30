"""SG2 (docs/shiploop-sdlc-gates-proposal-2026-10-30.md §5): does the step review remove a seeded defect, inline or in
a fresh context?

- ``score``: 1 when the case's seeded-defect probe finds the defect absent from the final tree (seeded_defects.score).
  The Improve fix commits since the seeded start (e5_regression.fix_commits) are counted beside it, so a defect the
  implementer never wrote can be told from one a review fixed.
- ``verify``: seeded_defects verify for each SG2 case: its probe fails on the naive tree, whose own checks pass, and
  passes on the fixed one.
"""
from __future__ import annotations

import json
from pathlib import Path

import common

BINARY = True
CASES = ("node-seeded-case-compare", "node-seeded-numeric-sort", "node-seeded-empty-guard",
         "node-seeded-early-validation")


def score(sample: Path) -> dict:
    import e5_regression  # noqa: PLC0415 - its reader of Improve fix commits
    import seeded_defects  # noqa: PLC0415
    tree = common.worktree(sample)
    if tree is None or not tree.is_dir():
        return {"value": None, "why": "no final tree"}
    invocation = json.loads((Path(sample) / "invocation.json").read_text())
    name = invocation.get("case")
    if name not in CASES:
        return {"value": None, "why": f"case {name!r} is not an SG2 case"}
    probe = seeded_defects.score(common.case(name), tree)
    fixes = e5_regression.fix_commits(tree, invocation["seeded"]["start_head"])
    return {"value": 0 if probe["present"] else 1, "case": name, "delegation": invocation.get("delegation"),
            "improve_fix_commits": len(fixes)}


def verify() -> list[dict]:
    import seeded_defects  # noqa: PLC0415
    return [row for name in CASES for row in seeded_defects.verify(name)]
