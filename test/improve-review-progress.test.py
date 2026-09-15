#!/usr/bin/env python3
"""Focused coverage for Improve's receipt-derived review convergence."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


# Direct test invocation must not contaminate the relocatable skill package.
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "improve" / "scripts" / "review_progress.py"
SPEC = importlib.util.spec_from_file_location("improve_review_progress", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load {MODULE_PATH}")
progress = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(progress)


def review(
    *,
    before: str = "candidate-a",
    after: str = "candidate-a",
    classification: str = "trivial",
    checks: str = "passed",
    improvements_complete: bool = True,
    open_findings: list[str] | None = None,
) -> dict:
    return {
        "candidate_before": before,
        "candidate_after": after,
        "classification": classification,
        "checks": checks,
        "improvements_complete": improvements_complete,
        "open_findings": [] if open_findings is None else open_findings,
    }


_DEFAULT_REVIEW = object()


def receipt(
    ident: str,
    *,
    outcome: str = "done",
    review_value: object = _DEFAULT_REVIEW,
) -> dict:
    if review_value is _DEFAULT_REVIEW:
        review_value = review() if outcome == "done" else None
    return {
        "id": ident,
        "outcome": outcome,
        "review": review_value,
    }


class ReviewProgressNormalizationTests(unittest.TestCase):
    def test_normalize_review_returns_only_the_canonical_fields(self) -> None:
        raw = review(before="before", after="after", classification="none")

        self.assertEqual(progress.normalize_review(raw), raw)
        self.assertIsNot(progress.normalize_review(raw), raw)

    def test_normalize_review_rejects_wrong_shapes_and_types(self) -> None:
        cases = (
            None,
            [],
            {"candidate_before": "only-one-field"},
            {**review(), "unexpected": "field"},
            review(before=""),
            review(after="   "),
            review(classification="green"),
            review(classification=[]),
            review(checks="green"),
            review(checks=[]),
            review(improvements_complete=1),
            review(open_findings="open"),
            review(open_findings=[""]),
            review(open_findings=[1]),
        )
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(progress.ReviewProgressError):
                    progress.normalize_review(value)


class ReviewProgressDecisionTests(unittest.TestCase):
    def test_ready_boundary_requires_two_current_eligible_reviews(self) -> None:
        first = receipt("review-1")
        second = receipt("review-2")

        self.assertEqual(progress.decide([]), {"ready": False, "trivial_streak": 0})
        self.assertEqual(progress.decide([first]), {"ready": False, "trivial_streak": 1})
        self.assertEqual(
            progress.decide([first, second]), {"ready": True, "trivial_streak": 2}
        )

    def test_no_change_reviews_count_without_commit_receipts(self) -> None:
        receipts = [
            receipt("review-1", review_value=review(classification="none")),
            receipt("review-2", review_value=review(classification="none")),
        ]

        self.assertEqual(progress.decide(receipts), {"ready": True, "trivial_streak": 2})

    def test_duplicate_replay_record_is_rejected(self) -> None:
        rows = [receipt("review-1"), receipt("review-1")]

        with self.assertRaises(progress.ReviewProgressError):
            progress.decide(rows)

    def test_candidate_drift_resets_before_counting_the_new_review(self) -> None:
        rows = [
            receipt("review-1", review_value=review(before="a", after="b")),
            receipt("review-2", review_value=review(before="c", after="d")),
            receipt("review-3", review_value=review(before="d", after="d")),
        ]

        self.assertEqual(progress.decide(rows[:2]), {"ready": False, "trivial_streak": 1})
        self.assertEqual(progress.decide(rows), {"ready": True, "trivial_streak": 2})

    def test_material_review_and_incomplete_work_reset_the_streak(self) -> None:
        prefix = [receipt("review-1"), receipt("review-2")]
        material = receipt(
            "review-3", review_value=review(classification="material")
        )
        uncertain = receipt(
            "review-4", review_value=review(classification="uncertain")
        )
        incomplete = receipt(
            "review-5", review_value=review(improvements_complete=False)
        )

        self.assertEqual(
            progress.decide([*prefix, material]), {"ready": False, "trivial_streak": 0}
        )
        self.assertEqual(
            progress.decide([*prefix, uncertain]), {"ready": False, "trivial_streak": 0}
        )
        self.assertEqual(
            progress.decide([*prefix, incomplete]), {"ready": False, "trivial_streak": 0}
        )

    def test_nonpassing_checks_and_open_findings_reset_the_streak(self) -> None:
        prefix = [receipt("review-1"), receipt("review-2")]
        for index, checks in enumerate(("failed", "stale", "incomplete"), start=3):
            with self.subTest(checks=checks):
                rows = [
                    *prefix,
                    receipt(f"review-{index}", review_value=review(checks=checks)),
                ]
                self.assertEqual(
                    progress.decide(rows), {"ready": False, "trivial_streak": 0}
                )

        rows = [
            *prefix,
            receipt("review-findings", review_value=review(open_findings=["F-1"])),
        ]
        self.assertEqual(progress.decide(rows), {"ready": False, "trivial_streak": 0})

    def test_repeat_and_blocked_break_continuity_and_never_count(self) -> None:
        rows = [
            receipt("review-1"),
            receipt("retry-1", outcome="repeat", review_value=None),
            receipt("review-2"),
            receipt("blocked-1", outcome="blocked", review_value=None),
            receipt("review-3"),
        ]

        self.assertEqual(progress.decide(rows[:3]), {"ready": False, "trivial_streak": 1})
        self.assertEqual(progress.decide(rows), {"ready": False, "trivial_streak": 1})

    def test_decide_rejects_malformed_records_and_wrong_types(self) -> None:
        cases = (
            None,
            {},
            [None],
            [{"id": "review-1", "outcome": "done", "review": review(), "extra": True}],
            [{**receipt("review-1"), "trivial_streak": 99}],
            [receipt("", review_value=review())],
            [receipt("review-1", outcome="unknown", review_value=None)],
            [receipt("review-1", outcome=[], review_value=None)],
            [receipt("review-1", outcome="done", review_value=None)],
            [receipt("review-1", outcome="repeat", review_value=review())],
            [receipt("review-1", outcome="blocked", review_value=[])],
        )
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(progress.ReviewProgressError):
                    progress.decide(value)


if __name__ == "__main__":
    unittest.main()
