#!/usr/bin/env python3
"""E5: does an action-linked Improve repair have a defect-specific regression test?

    python3 test/shiploop_e2e/evaluators/e5_regression.py score <sample>
    python3 test/shiploop_e2e/evaluators/e5_regression.py verify

The score compares a bounded counterfactual of the seeded Basket constructor/guard and changed test behavior at the
Improve bind and recorded pass trees. Unsupported counterfactual layouts remain unknown. Only a repair in a linked
Improve pass can receive E5 credit; producer commits and their learning notes do not establish review ownership.
``defect_caught`` reports the final seeded-defect probe independently of review attribution. ``review_repair`` separately
reports ``repaired``, ``unrepaired``, ``introduced``, ``no_repair``,
``not_applicable`` (a valid review bind had no defect), or ``unknown`` (required snapshot evidence is missing or
ambiguous). ``value`` is ``None`` for not-applicable or unknown evidence, 0 for an entry defect without an effective
regression test, and 1 when every attributed repair's changed test passes after and fails before the repair.
``verify`` checks the seeded-defect probe's naive/fixed references; runtime attribution fixtures are in
``test/shiploop-e2e-review-attribution.test.py``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import improve_attribution  # noqa: E402

CASE = "node-seeded-early-validation"


def score(sample: Path) -> dict:
    tree = common.worktree(sample)
    if tree is None or not tree.is_dir():
        review = {"status": "unknown", "value": None, "repair_count": None,
                  "why": "no final worktree or linked snapshot can be checked"}
        return {"value": None, "review_repair": review, "fixes": [], "why": review["why"],
                "defect_caught": None}
    import seeded_defects  # noqa: PLC0415
    try:
        final_probe = seeded_defects.score(common.case(CASE), tree)
    except (OSError, ValueError, KeyError, RuntimeError):
        final_probe = None
    defect_caught = (not final_probe["present"] if isinstance(final_probe, dict)
                     and final_probe.get("checks_pass") is True
                     and isinstance(final_probe.get("present"), bool) else None)
    result = improve_attribution.evaluate(sample, common.case(CASE), tree, test_repairs=True)
    review = {key: result[key] for key in ("status", "value", "repair_count", "why")}
    return {"value": result.get("e5_value"), "review_repair": review, "fixes": result["fixes"],
            "actions": result["actions"],
            "defect_caught": defect_caught}


def verify() -> list[dict]:
    import seeded_defects  # noqa: PLC0415
    rows = seeded_defects.verify(CASE)
    return [{"check": "seeded-defect probe references", "rows": rows,
             "ok": bool(rows) and all(row["ok"] for row in rows)}]


if __name__ == "__main__":
    raise SystemExit(common.cli(sys.modules[__name__], sys.argv[1:]))
