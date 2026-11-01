#!/usr/bin/env python3
"""SG2: does a linked step Improve review remove a seeded defect?

    python3 test/shiploop_e2e/evaluators/sg2_recall.py score <sample>
    python3 test/shiploop_e2e/evaluators/sg2_recall.py verify

``value`` preserves the final seeded-defect outcome: 1 when the defect is absent and 0 when it remains, provided the
case's public checks pass; otherwise it is null. The separate
``review_repair`` result attributes a repair only to a change between that action's Improve bind and recorded pass
trees. A clean review bind is ``not_applicable`` with ``repair_count`` 0 and no numeric review value; an entry defect
left in place or introduced by a review is 0; missing or ambiguous snapshot evidence is ``unknown`` with a null value.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common

BINARY = True
CASES = ("node-seeded-case-compare", "node-seeded-numeric-sort", "node-seeded-empty-guard",
         "node-seeded-early-validation")


def score(sample: Path) -> dict:
    import seeded_defects  # noqa: PLC0415
    import improve_attribution  # noqa: PLC0415
    tree = common.worktree(sample)
    if tree is None or not tree.is_dir():
        return {"value": None, "review_repair": {"status": "unknown", "value": None,
                "repair_count": None, "why": "no final worktree or linked snapshot can be checked"}}
    try:
        invocation = json.loads((Path(sample) / "invocation.json").read_text())
    except (OSError, ValueError, TypeError):
        return {"value": None, "why": "sample invocation is missing or unreadable",
                "review_repair": {"status": "unknown", "value": None, "repair_count": None,
                                  "why": "sample invocation is missing or unreadable"}}
    if not isinstance(invocation, dict) or not isinstance(invocation.get("case"), str):
        return {"value": None, "why": "sample invocation has no valid case name",
                "review_repair": {"status": "unknown", "value": None, "repair_count": None,
                                  "why": "sample invocation has no valid case name"}}
    name = invocation.get("case")
    if name not in CASES:
        why = f"case {name!r} is not an SG2 case"
        return {"value": None, "why": why,
                "review_repair": {"status": "unknown", "value": None, "repair_count": None, "why": why}}
    probe = seeded_defects.score(common.case(name), tree)
    review = improve_attribution.evaluate(sample, common.case(name), tree, test_repairs=False)
    review_result = {key: review[key] for key in ("status", "value", "repair_count", "why")}
    final_value = None if not probe["checks_pass"] else 0 if probe["present"] else 1
    return {"value": final_value, "case": name,
            "delegation": invocation.get("delegation"),
            "defect_caught": None if not probe["checks_pass"] else not probe["present"],
            "review_repair": review_result, "review_actions": review["actions"]}


def verify() -> list[dict]:
    import seeded_defects  # noqa: PLC0415
    return [row for name in CASES for row in seeded_defects.verify(name)]


if __name__ == "__main__":
    raise SystemExit(common.cli(sys.modules[__name__], sys.argv[1:]))
