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

from shiploop_until import UntilError, action_reasoning, decide, review_improve_cycle  # noqa: E402


class UntilDecisionTests(unittest.TestCase):
    """The helper accepts only completed, verified, uniquely audited passes."""

    def test_action_guidance_allows_optional_memory_but_never_cached_authority(self) -> None:
        guidance = action_reasoning()
        self.assertIn("Reset-safe context:", guidance)
        self.assertIn("same-loop memory is optional", guidance)
        self.assertIn("Markdown wins", guidance)
        self.assertIn("missing proof is incomplete", guidance)
        self.assertIn("Only scripts advance/count cycles", guidance)

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

    def test_review_improve_cycle_states_the_complete_order_for_new_and_legacy_history(self) -> None:
        """One shared packet says what a converging pass actually means.

        The seven-body current policy and the ten-body legacy policy must change
        only the history window.  In particular, a callback is not a review
        pass: only a completed, audited, trivial review can advance the
        two-pass convergence streak.
        """
        for history_limit in (7, 10):
            with self.subTest(history_limit=history_limit):
                packet = review_improve_cycle(history_limit)
                self.assertEqual(packet.count("Review-and-improve cycle"), 1)
                ordered = (
                    "1. Review changes",
                    "2. Consider improvements",
                    f"3. Plan improvements using the last {history_limit} full Git commit bodies",
                    "4. Implement every approved improvement, including trivial fixes",
                    "Run required checks and create the verbose learning commit",
                    "5. Repeat until two consecutive completed trivial reviews",
                )
                positions = [packet.index(item) for item in ordered]
                self.assertEqual(positions, sorted(positions))
                self.assertIn("not callbacks", packet)
                self.assertIn("Key learnings", packet)

    def test_review_improve_cycle_rejects_an_unsafe_history_window(self) -> None:
        for invalid in (0, -1, True, False, "7", None):
            with self.subTest(invalid=invalid):
                with self.assertRaises(UntilError):
                    review_improve_cycle(invalid)  # type: ignore[arg-type]

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
            # An incomplete review has no completed audit receipt, so it
            # cannot be silently promoted into a convergence pass.
            "incomplete-no-audit-receipt": (
                [
                    self.row("I-001", commit="a" * 40),
                    {
                        "id": "I-002",
                        "outcome": "trivial",
                        "verified": True,
                    },
                ],
                [],
            ),
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
