"""Fast checks for named E2E suite selection; no host or model calls."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import suites  # noqa: E402
import run  # noqa: E402


class SuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.families = suites.load_scenario_families()

    def test_list_exposes_named_bounds_without_copying_prompts(self) -> None:
        rows = suites.list_suites(self.families)
        self.assertEqual(
            ["launch-smoke", "planning-smoke", "ttt-full", "checkers-full", "battleship-full", "games-full", "salesforce-checkers-full"],
            [row["id"] for row in rows],
        )
        launch = rows[0]
        self.assertTrue(launch["partial"])
        self.assertEqual("partial-prefix", launch["completion_claim"])
        self.assertEqual("intake", launch["cases"][0]["stop_after_stage"])
        self.assertNotIn("prompt", launch["cases"][0])

    def test_partial_smokes_are_independent_and_bounded(self) -> None:
        launch = suites.resolve_suite("launch-smoke", self.families)
        self.assertTrue(launch["partial"])
        self.assertEqual("partial-prefix", launch["completion_claim"])
        self.assertEqual(["ttt-create", "checkers-create"], [case["step_id"] for case in launch["cases"]])
        self.assertEqual(["tic-tac-toe-launch-smoke", "checkers-launch-smoke"], [case["product_key"] for case in launch["cases"]])
        self.assertTrue(all(case["depends_on"] == [] for case in launch["cases"]))
        self.assertTrue(all(case["timeout_seconds"] == 7200 and case["max_turns"] == 1000 for case in launch["cases"]))

    def test_planning_smoke_stops_at_plan_improve(self) -> None:
        planning = suites.resolve_suite("planning-smoke", self.families)
        self.assertEqual(1, len(planning["cases"]))
        case = planning["cases"][0]
        self.assertEqual("ttt-create", case["step_id"])
        self.assertEqual("plan-improve", case["stop_after_stage"])
        self.assertEqual((7200, 1000), (case["timeout_seconds"], case["max_turns"]))
        self.assertTrue(case["prompt"].startswith("/shiploop "))

    def test_partial_boundaries_match_runner_prelude_only(self) -> None:
        self.assertEqual(frozenset(run.PARTIAL_STAGES), suites.STOP_AFTER_STAGES)
        document = {
            "schema_version": 1,
            "suites": [{
                "id": "bad-inner-boundary",
                "title": "Bad inner boundary",
                "description": "Inner-loop boundaries cannot make a stable partial smoke.",
                "mode": "partial",
                "cases": [{
                    "id": "bad-inner-case",
                    "step": "ttt-create",
                    "product_key": "bad-inner-product",
                    "depends_on": [],
                    "stop_after_stage": "implement",
                    "timeout_seconds": 1,
                    "max_turns": 1,
                }],
            }],
        }
        with self.assertRaisesRegex(suites.SuiteError, "valid stop_after_stage"):
            suites.validate_suites(document, self.families)

    def test_full_suite_keeps_explicit_predecessor_order(self) -> None:
        full = suites.resolve_suite("ttt-full", self.families)
        self.assertFalse(full["partial"])
        self.assertEqual("full-chain", full["completion_claim"])
        self.assertEqual(
            [("ttt-create", []), ("ttt-guidance", ["ttt-create"]), ("ttt-best-move", ["ttt-guidance"])],
            [(case["step_id"], case["depends_on"]) for case in full["cases"]],
        )
        self.assertTrue(all(case["stop_after_stage"] is None for case in full["cases"]))
        self.assertTrue(full["selection"]["dependency_complete"])

    def test_games_full_contains_three_ordered_product_chains(self) -> None:
        full = suites.resolve_suite("games-full", self.families)
        self.assertEqual(9, len(full["cases"]))
        self.assertEqual(
            ["tic-tac-toe", "checkers", "battleship"],
            list(dict.fromkeys(case["product_key"] for case in full["cases"])),
        )
        self.assertTrue(full["selection"]["dependency_complete"])

    def test_salesforce_checkers_is_an_independent_one_case_full_suite(self) -> None:
        suite = suites.resolve_suite("salesforce-checkers-full", self.families)
        self.assertFalse(suite["partial"])
        self.assertEqual(["salesforce-checkers-create"], [case["step_id"] for case in suite["cases"]])
        self.assertEqual("salesforce-checkers", suite["cases"][0]["product_key"])
        self.assertTrue(suite["selection"]["dependency_complete"])

    def test_all_successors_require_platform_compatibility_and_family_suites(self) -> None:
        for family in self.families:
            if family.get("platform") == "salesforce-lightning":
                self.assertEqual("checkers", family["oracle_family"])
                self.assertEqual(
                    ["salesforce-authorized-deployment", "salesforce-hosted-lightning-behavior", "salesforce-source-candidate"],
                    family["steps"][0]["required_checks"][:3],
                )
                self.assertNotIn("gas-compatible-local-artifact", family["steps"][0]["required_checks"])
                continue
            for step in family["steps"]:
                self.assertIn("gas-compatible-local-artifact", step["required_checks"])
        for family in ("checkers", "battleship"):
            suite = suites.resolve_suite(family + "-full", self.families)
            self.assertEqual(3, len(suite["cases"]))
            self.assertTrue(suite["selection"]["dependency_complete"])
            self.assertEqual(["create", "feature", "refine"], [case["kind"] for case in suite["cases"]])

    def test_selected_feature_retains_missing_predecessor_metadata(self) -> None:
        selected = suites.resolve_suite("ttt-full", self.families, only_case_ids=["ttt-guidance"])
        self.assertEqual(["ttt-guidance"], [case["step_id"] for case in selected["cases"]])
        self.assertFalse(selected["selection"]["dependency_complete"])
        self.assertEqual(["ttt-create"], selected["selection"]["missing_predecessor_step_ids"])

    def test_validation_rejects_a_dependent_partial_case(self) -> None:
        document = {
            "schema_version": 1,
            "suites": [{
                "id": "bad",
                "title": "Bad partial suite",
                "description": "Dependent partial cases would misrepresent a prefix as independent.",
                "mode": "partial",
                "cases": [{
                    "id": "bad-feature",
                    "step": "ttt-guidance",
                    "product_key": "bad-product",
                    "depends_on": ["ttt-create"],
                    "stop_after_stage": "intake",
                    "timeout_seconds": 1,
                    "max_turns": 1,
                }],
            }],
        }
        with self.assertRaisesRegex(suites.SuiteError, "not independent"):
            suites.validate_suites(document, deepcopy(self.families))

    def test_validation_rejects_wrong_full_dependency_or_stop_boundary(self) -> None:
        document = {
            "schema_version": 1,
            "suites": [{
                "id": "bad",
                "title": "Bad full suite",
                "description": "The source scenario dependency must be preserved.",
                "mode": "full",
                "cases": [{
                    "id": "bad-feature",
                    "step": "ttt-guidance",
                    "product_key": "bad-product",
                    "depends_on": [],
                    "stop_after_stage": None,
                    "timeout_seconds": 1,
                    "max_turns": 1,
                }],
            }],
        }
        with self.assertRaisesRegex(suites.SuiteError, "dependencies do not match"):
            suites.validate_suites(document, self.families)

    def test_validation_rejects_path_like_output_keys(self) -> None:
        document = {
            "schema_version": 1,
            "suites": [{
                "id": "safe-suite",
                "title": "Safe fields with one unsafe path key",
                "description": "Suite-owned output keys must not traverse paths.",
                "mode": "partial",
                "cases": [{
                    "id": "safe-case",
                    "step": "ttt-create",
                    "product_key": "safe-product",
                    "depends_on": [],
                    "stop_after_stage": "intake",
                    "timeout_seconds": 1,
                    "max_turns": 1,
                }],
            }],
        }
        for field, location in (("id", "suite"), ("id", "case"), ("product_key", "case")):
            for unsafe in ("../escape", "/absolute", "nested/path", r"nested\\path", ".", ".."):
                candidate = deepcopy(document)
                target = candidate["suites"][0] if location == "suite" else candidate["suites"][0]["cases"][0]
                target[field] = unsafe
                with self.subTest(field=field, location=location, unsafe=unsafe):
                    with self.assertRaisesRegex(suites.SuiteError, "slug"):
                        suites.validate_suites(candidate, self.families)


if __name__ == "__main__":
    unittest.main()
