#!/usr/bin/env python3
"""Unit coverage for ShipLoop's Markdown-backed until-loop policy.

The incorporated helper deliberately owns no state and never declares final
success.  These tests make its small evidence contract explicit so callers
cannot accidentally turn a host claim, partial SHA, or repeated receipt into a
convergence pass.
"""

from __future__ import annotations

import itertools
from pathlib import Path
import sys
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from shiploop_until import UntilError, decide  # noqa: E402


class UntilDecisionTests(unittest.TestCase):
    """The helper accepts only completed, verified, uniquely audited passes."""

    @staticmethod
    def row(
        pass_id: str,
        outcome: str = "trivial",
        *,
        commit: str = "a" * 40,
        verified: object = True,
    ) -> dict[str, object]:
        return {
            "id": pass_id,
            "outcome": outcome,
            "verified": verified,
            "commit": commit,
        }

    def test_two_consecutive_verified_trivial_receipts_are_ready_not_success(self) -> None:
        result = decide(
            [
                self.row("I-001", commit="a" * 40),
                self.row("I-002", commit="b" * 40),
            ],
            open_findings=[],
        )

        self.assertEqual(result, {"phase": "ready", "trivial_streak": 2})
        self.assertNotIn("done", result)
        self.assertNotIn("success", result)
        self.assertNotIn("final", result)

    def test_material_pass_resets_the_current_repair_epoch_streak(self) -> None:
        result = decide(
            [
                self.row("I-001", commit="a" * 40),
                self.row("I-002", "material", commit="b" * 40),
                self.row("I-003", commit="c" * 40),
            ],
            open_findings=[],
        )

        self.assertEqual(result, {"phase": "active", "trivial_streak": 1})

    def test_open_findings_keep_a_two_trivial_streak_active(self) -> None:
        result = decide(
            [
                self.row("I-001", commit="a" * 40),
                self.row("I-002", commit="b" * 40),
            ],
            open_findings=[{"id": "F-remaining"}],
        )

        self.assertEqual(result, {"phase": "active", "trivial_streak": 2})

    def test_empty_completed_passes_are_active(self) -> None:
        self.assertEqual(
            decide([], open_findings=[]),
            {"phase": "active", "trivial_streak": 0},
        )

    def test_rejects_noncanonical_or_replayed_evidence(self) -> None:
        cases: dict[str, tuple[object, object]] = {
            "passes-not-list": ({}, []),
            "findings-not-list": ([], {}),
            "row-not-record": (["not-a-record"], []),
            "unsafe-id": ([self.row("I 001")], []),
            "missing-id": ([self.row("")], []),
            "partial-commit": ([self.row("I-001", commit="a" * 39)], []),
            "uppercase-commit": ([self.row("I-001", commit="A" * 40)], []),
            "unverified": ([self.row("I-001", verified=1)], []),
            "invalid-outcome": ([self.row("I-001", "no-change")], []),
            "duplicate-id": (
                [
                    self.row("I-001", commit="a" * 40),
                    self.row("I-001", commit="b" * 40),
                ],
                [],
            ),
            "duplicate-commit": (
                [
                    self.row("I-001", commit="a" * 40),
                    self.row("I-002", commit="a" * 40),
                ],
                [],
            ),
        }

        for name, (passes, findings) in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(UntilError):
                    decide(passes, open_findings=findings)  # type: ignore[arg-type]

    def test_accepts_a_full_sha256_commit(self) -> None:
        self.assertEqual(
            decide([self.row("I-001", commit="a" * 64)], open_findings=[]),
            {"phase": "active", "trivial_streak": 1},
        )

    def test_all_short_outcome_histories_recompute_streak_and_readiness_from_evidence(self) -> None:
        """No host-cached streak can change any material/trivial decision."""
        for length in range(9):
            for outcomes in itertools.product(("material", "trivial"), repeat=length):
                trailing_trivial = 0
                for outcome in reversed(outcomes):
                    if outcome != "trivial":
                        break
                    trailing_trivial += 1
                passes = [
                    self.row(
                        f"P-{index}",
                        outcome,
                        commit=f"{index + 1:040x}",
                    )
                    for index, outcome in enumerate(outcomes)
                ]
                for open_findings in ([], [{"id": "F-open"}]):
                    with self.subTest(outcomes=outcomes, open=bool(open_findings)):
                        self.assertEqual(
                            decide(passes, open_findings=open_findings),
                            {
                                "phase": (
                                    "ready"
                                    if trailing_trivial >= 2 and not open_findings
                                    else "active"
                                ),
                                "trivial_streak": trailing_trivial,
                            },
                        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
