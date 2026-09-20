"""Calibration tests for the pure Checkers and Battleship semantic oracles.

The observations are synthetic protocol snapshots.  They exercise no browser,
model, source tree, application server, or generated product.  The private
reference-trace helper provides a known-good trace; each mutant changes a
publicly observable rule outcome so the oracle has to reject it.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import oracle_games as oracle  # noqa: E402


ALL_STEPS = (
    "checkers-create",
    "checkers-guidance",
    "checkers-hint-toggle",
    "salesforce-checkers-create",
    "battleship-create",
    "battleship-status-history",
    "battleship-history-filter",
)


def _case(case_id: str) -> dict:
    for step_id in ALL_STEPS:
        for case in oracle.cases(step_id):
            if case["id"] == case_id:
                return case
    raise AssertionError(f"unknown test case {case_id}")


class GameOracleCasesTests(unittest.TestCase):
    def test_each_step_has_cumulative_cases_and_current_level_cases(self) -> None:
        expected = {
            "checkers-create": ("checkers", "base", 6),
            "checkers-guidance": ("checkers", "guidance", 8),
            "checkers-hint-toggle": ("checkers", "refine", 9),
            "battleship-create": ("battleship", "base", 3),
            "battleship-status-history": ("battleship", "guidance", 4),
            "battleship-history-filter": ("battleship", "refine", 5),
        }
        for step_id, (game, level, count) in expected.items():
            with self.subTest(step_id=step_id):
                cases = oracle.cases(step_id)
                self.assertEqual(len(cases), count)
                self.assertTrue(all(case["game"] == game for case in cases))
                self.assertTrue(any(
                    case["step_id"] == step_id and case["level"] == level for case in cases
                ))
                self.assertTrue(all({"id", "game", "step_id", "level", "actions"} <= set(case) for case in cases))

    def test_case_copies_are_not_shared(self) -> None:
        first = oracle.cases("checkers-create")
        first[0]["actions"][0]["type"] = "mutated"
        self.assertEqual(oracle.cases("checkers-create")[0]["actions"][0]["type"], "set_fixture")

    def test_unknown_step_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            oracle.cases("connect-four-create")

    def test_salesforce_create_alias_reuses_only_base_checkers_rules_with_its_own_step_id(self) -> None:
        cases = oracle.cases("salesforce-checkers-create")
        self.assertEqual(6, len(cases))
        self.assertTrue(all(case["game"] == "checkers" for case in cases))
        self.assertTrue(all(case["step_id"] == "salesforce-checkers-create" for case in cases))
        self.assertTrue(all(case["level"] == "base" for case in cases))

    def test_known_good_synthetic_traces_cover_every_case(self) -> None:
        seen = set()
        for step_id in ALL_STEPS:
            for case in oracle.cases(step_id):
                if case["id"] in seen:
                    continue
                seen.add(case["id"])
                with self.subTest(case_id=case["id"]):
                    observations = oracle._synthetic_observations(case)
                    self.assertEqual(oracle.evaluate(case, observations), [])
        self.assertEqual(len(seen), 14)

    def test_checkers_illegal_quiet_move_under_required_capture_fails(self) -> None:
        case = _case("checkers-base-required-capture")
        observations = oracle._synthetic_observations(case)
        # Action 1 attempts a quiet move while another black piece must capture.
        observations[1]["board"][5][4] = None
        observations[1]["board"][4][3] = {"player": "black", "king": False}
        issues = oracle.evaluate(case, observations)
        self.assertTrue(any(issue["field"] == "board" for issue in issues))

    def test_checkers_capture_chain_cannot_change_piece(self) -> None:
        case = _case("checkers-base-capture-chain-lock")
        observations = oracle._synthetic_observations(case)
        # The first capture must leave the moved piece locked and selected.
        observations[1]["capture_chain_piece"] = [5, 4]
        observations[1]["selected"] = [5, 4]
        issues = oracle.evaluate(case, observations)
        self.assertTrue(any(issue["field"] == "capture_chain_piece" for issue in issues))

    def test_checkers_missing_visible_destination_highlights_fails(self) -> None:
        case = _case("checkers-guidance-selected-destinations")
        observations = oracle._synthetic_observations(case)
        observations[1]["legal_destinations"] = []
        issues = oracle.evaluate(case, observations)
        self.assertTrue(any(issue["field"] == "legal_destinations" for issue in issues))

    def test_checkers_hint_toggle_cannot_mutate_turn_or_board(self) -> None:
        case = _case("checkers-refine-hint-toggle-and-chain")
        observations = oracle._synthetic_observations(case)
        # The first hint update occurs at index 2; it must leave game state alone.
        observations[2]["active_player"] = "white"
        issues = oracle.evaluate(case, observations)
        self.assertTrue(any(
            issue["reason"] == "hint-toggle-mutated-game-state" for issue in issues
        ))

    def test_checkers_variant_drift_is_an_issue(self) -> None:
        case = _case("checkers-base-legal-diagonal-moves")
        observations = oracle._synthetic_observations(case)
        observations[2]["variant"]["capture_priority"] = "maximum"
        issues = oracle.evaluate(case, observations)
        self.assertEqual(issues, [{"index": 2, "field": "variant", "reason": "variant-changed-within-trace"}])

    def test_battleship_repeated_shot_is_rejected(self) -> None:
        case = _case("battleship-base-shots-sunk-winner-and-privacy")
        observations = oracle._synthetic_observations(case)
        # Action 3 repeats P1's first coordinate; it must leave the hit unaccepted.
        observations[3]["last_action"]["accepted"] = True
        issues = oracle.evaluate(case, observations)
        self.assertTrue(any(
            issue["field"] == "last_action.accepted" and issue["reason"] == "action-result-mismatch"
            for issue in issues
        ))

    def test_battleship_unshot_opponent_ship_leak_fails(self) -> None:
        case = _case("battleship-base-shots-sunk-winner-and-privacy")
        observations = oracle._synthetic_observations(case)
        # After P1's first shot, P2 is viewing P1's board.  P1's [0, 1]
        # patrol cell has not been fired upon and must still be unknown.
        observations[1]["visible"]["opponent_board"][0][1] = "ship"
        issues = oracle.evaluate(case, observations)
        self.assertTrue(any(issue["reason"] == "opponent-unshot-ship-visible" for issue in issues))

    def test_battleship_history_filter_must_show_only_matching_existing_entries(self) -> None:
        case = _case("battleship-refine-history-filters-preserve-game")
        observations = oracle._synthetic_observations(case)
        # Index 4 selects the hit filter, but this mutant retains all entries.
        observations[4]["visible_history"] = deepcopy(observations[4]["history"])
        issues = oracle.evaluate(case, observations)
        self.assertTrue(any(issue["reason"] == "filtered-history-mismatch" for issue in issues))

    def test_battleship_filter_turn_or_state_mutation_fails(self) -> None:
        case = _case("battleship-refine-history-filters-preserve-game")
        observations = oracle._synthetic_observations(case)
        observations[4]["active_player"] = "P1"
        issues = oracle.evaluate(case, observations)
        self.assertTrue(any(
            issue["reason"] == "history-filter-mutated-game-state" for issue in issues
        ))

    def test_missing_or_unsupported_fixture_is_unverified_input(self) -> None:
        checkers = _case("checkers-base-promotion")
        observations = oracle._synthetic_observations(checkers)
        observations[0]["fixture_applied"] = False
        with self.assertRaisesRegex(ValueError, "fixture"):
            oracle.evaluate(checkers, observations)

        battleship = _case("battleship-base-placement-rules")
        observations = oracle._synthetic_observations(battleship)
        del observations[0]["visible"]
        with self.assertRaisesRegex(ValueError, "incomplete"):
            oracle.evaluate(battleship, observations)

    def test_explicit_absent_feature_is_a_behavior_issue_not_missing_data(self) -> None:
        case = _case("checkers-refine-hint-toggle-and-chain")
        observations = oracle._synthetic_observations(case)
        observations[2]["hints_visible"] = None
        observations[2]["action_supported"] = False
        issues = oracle.evaluate(case, observations)
        self.assertTrue(any(issue["reason"] == "hint-toggle-unavailable" for issue in issues))

        case = _case("battleship-refine-history-filters-preserve-game")
        observations = oracle._synthetic_observations(case)
        observations[4]["last_action"]["supported"] = False
        issues = oracle.evaluate(case, observations)
        self.assertTrue(any(issue["reason"] == "history-filter-unavailable" for issue in issues))


if __name__ == "__main__":
    unittest.main()
