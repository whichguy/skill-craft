"""Calibrate workflow findings against explicit evidence, without model calls."""
from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile
import unittest

from workflow_review import DIMENSIONS, validate_review


class WorkflowReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "evidence.txt").write_text("Observed interaction and scoped independent review")
        self.ref = {"path": "evidence.txt", "sha256": hashlib.sha256((self.root / "evidence.txt").read_bytes()).hexdigest()}
        self.result = {"trial_id": "t", "candidate_digest": "c", "baseline_digest": None,
                       "skill_digest": "s", "harness_snapshot": {"package_sha256": "h"}}
        self.review = {"schema": "shiploop-e2e-workflow-review/2", "trial_id": "t", "candidate_digest": "c",
                       "baseline_digest": None, "skill_digest": "s", "harness_digest": "h",
                       "reviewer": "Independent fixture reviewer", "reviewed_at": "2026-09-17", "scope": "Fixture only",
                       "inventory": {"selected_test_ids": ["A9"], "improve_action_ids": ["i1"], "evidence": [self.ref]},
                       "dimensions": [{"id": key, "status": "supported-pass", "evidence": [self.ref], "notes": "Observed"} for key in DIMENSIONS],
                       "selected_tests": [{"id": "A9", "required_method": "interaction", "observed_method": "interaction",
                                           "disposition": "passed", "evidence": [self.ref]}],
                       "improve_reviews": [{"action_id": "i1", "independent_availability": "available", "fresh_review_completed": True,
                                            "scope": "Current source", "current_candidate": True, "evidence": [self.ref]}]}

    def assess(self, review=None):
        return validate_review(review or self.review, self.result, self.root)

    def nav_state(self, *, history, improve_results, run_id="current", protocol=4, **extra):
        return {
            "run_id": run_id,
            "navigator_protocol_version": protocol,
            "history": history,
            "improve_results": improve_results,
            **extra,
        }

    def use_inventory(self, action_ids):
        self.result["lifecycle"] = {"run_id": "current"}
        self.review["inventory"]["improve_action_ids"] = list(action_ids)
        self.review["improve_reviews"] = [
            {
                "action_id": action_id,
                "independent_availability": "available",
                "fresh_review_completed": True,
                "scope": "Current source",
                "current_candidate": True,
                "evidence": [self.ref],
            }
            for action_id in action_ids
        ]

    def test_improve_inventory_uses_completed_child_records(self):
        self.use_inventory(["nav-plan"])
        self.result["navigation"] = {"states": [{"state": self.nav_state(
            history=[{"action": "nav-intake", "stage": "intake"}, {"action": "nav-plan", "stage": "plan"}],
            improve_results={"nav-plan": {"summary": "Completed child."}},
        )}]}
        self.assertEqual(self.assess()["status"], "supported-pass")

        self.review["inventory"]["improve_action_ids"] = ["wrong"]
        self.review["improve_reviews"][0]["action_id"] = "wrong"
        self.assertEqual(self.assess()["status"], "supported-gap")

        self.review["inventory"]["improve_action_ids"] = []
        self.review["improve_reviews"] = []
        self.assertEqual(self.assess()["status"], "supported-gap")

    def test_active_producer_does_not_fabricate_completed_improve_inventory(self):
        self.use_inventory(["nav-i1"])
        self.result["navigation"] = {"states": [{"state": self.nav_state(
            history=[], improve_results={}, active_improve={"action_id": "nav-i1"},
        )}]}
        self.assertEqual(self.assess()["status"], "supported-gap")

    def test_missing_pair_is_unverified_and_extra_or_malformed_pair_is_invalid(self):
        self.use_inventory(["nav-plan"])
        state = self.nav_state(
            history=[{"action": "nav-intake", "stage": "intake"}, {"action": "nav-plan", "stage": "plan"}],
            improve_results={},
        )
        self.result["navigation"] = {"states": [{"state": state}]}
        assessment = self.assess()
        self.assertEqual(assessment["status"], "unverified")
        self.assertIn("current-run accepted planning-stage result has no Improve record",
                      assessment["unverified"])
        # Every planning stage, not only plan, requires its Improve record.
        state["history"].append({"action": "nav-spec", "stage": "spec"})
        state["improve_results"] = {"nav-plan": {}}
        self.assertEqual(self.assess()["status"], "unverified")
        state["history"].pop()

        # A non-checkpoint action without a record is the normal schedule.
        state["improve_results"] = {"nav-plan": {}}
        self.assertEqual(self.assess()["status"], "supported-pass")

        state["improve_results"] = {"nav-plan": {}, "extra": {}}
        self.assertEqual(self.assess()["status"], "invalid")
        state["improve_results"] = {"nav-plan": "not an object"}
        self.assertEqual(self.assess()["status"], "invalid")

    def test_inventory_excludes_other_runs_and_unsupported_protocols_are_unverified(self):
        self.result["lifecycle"] = {"run_id": "current"}
        foreign = {"state": self.nav_state(
            run_id="other", history=[{"action": "foreign", "stage": "plan"}],
            improve_results={"foreign": {}},
        )}
        self.result["navigation"] = {"states": [
            {"state": {"run_id": "current", "navigator_protocol_version": 2, "history": [
                {"action": "i1", "stage": "plan"},
            ], "improve_results": {"i1": {}}}},
            foreign,
        ]}
        assessment = self.assess()
        self.assertEqual(assessment["status"], "unverified", assessment)
        self.assertIn(
            "current-run navigator protocol is unsupported; only protocol 4 supplies Improve inventory",
            assessment["unverified"],
        )

        self.result["navigation"]["states"][0] = {"state": self.nav_state(
            history=[{"action": "i1", "stage": "plan"}], improve_results={"i1": {}},
        )}
        self.assertEqual(self.assess()["status"], "supported-pass")

    def test_divergent_snapshots_are_unverified_but_identical_views_are_comparable(self):
        self.use_inventory(["nav-i1"])
        snapshot = self.nav_state(
            history=[{"action": "nav-i1", "stage": "intake"}],
            improve_results={"nav-i1": {}},
        )
        self.result["navigation"] = {"states": [{"state": snapshot}, {"state": deepcopy(snapshot)}]}
        self.assertEqual(self.assess()["status"], "supported-pass")

        self.use_inventory(["nav-i1", "nav-i2"])
        self.result["navigation"]["states"] = [
            {"state": snapshot},
            {"state": self.nav_state(
                history=[{"action": "nav-i2", "stage": "discovery"}],
                improve_results={"nav-i2": {}},
            )},
        ]
        self.assertEqual(self.assess()["status"], "unverified")

    def test_mixed_current_run_unsupported_and_v4_snapshots_are_unverified(self):
        self.use_inventory(["nav-i1"])
        self.result["navigation"] = {"states": [
            {"state": {"run_id": "current", "navigator_protocol_version": 2, "history": [
                {"action": "nav-i1", "stage": "plan"},
            ], "improve_results": {"nav-i1": {}}}},
            {"state": self.nav_state(
                history=[{"action": "nav-i1", "stage": "plan"}],
                improve_results={"nav-i1": {}},
            )},
        ]}
        assessment = self.assess()
        self.assertEqual(assessment["status"], "unverified")
        self.assertIn("current-run navigator protocol is ambiguous across snapshots", assessment["unverified"])

    def test_checkpoint_records_form_the_inventory_and_plan_record_is_required(self):
        history = [{"action": "a-intake", "stage": "intake"}, {"action": "a-plan", "stage": "plan"}]
        self.use_inventory(["a-plan"])
        state = self.nav_state(history=history, improve_results={"a-plan": {}})
        self.result["navigation"] = {"states": [{"state": state}]}
        assessment = self.assess()
        self.assertEqual(assessment["status"], "supported-pass", assessment)
        self.assertNotIn(
            "current-run navigator protocol is unsupported; only protocol 4 supplies Improve inventory",
            assessment["unverified"],
        )

        # The un-reviewed intake action is not an Improve inventory item.
        self.use_inventory(["a-intake", "a-plan"])
        self.assertEqual(self.assess()["status"], "supported-gap")

        self.use_inventory(["a-plan"])
        state["improve_results"] = {}
        self.assertEqual(self.assess()["status"], "unverified")
        state["improve_results"] = {"a-plan": {}, "not-accepted": {}}
        self.assertEqual(self.assess()["status"], "invalid")

        # A retired protocol 3 snapshot cannot supply the inventory.
        self.result["navigation"] = {"states": [{"state": self.nav_state(
            history=history, improve_results={"a-plan": {}}, protocol=3)}]}
        assessment = self.assess()
        self.assertEqual(assessment["status"], "unverified")
        self.assertIn(
            "current-run navigator protocol is unsupported; only protocol 4 supplies Improve inventory",
            assessment["unverified"],
        )

    def test_malformed_present_navigation_containers_do_not_raise_or_support_inventory(self):
        for lifecycle, navigation in ((None, None), ([], {}), ({"run_id": "current"}, [])):
            with self.subTest(lifecycle=lifecycle, navigation=navigation):
                self.result["lifecycle"] = lifecycle
                self.result["navigation"] = navigation
                self.assertEqual(self.assess()["status"], "unverified")

    def test_missing_current_run_state_cannot_support_inventory(self):
        self.use_inventory(["nav-i1"])
        foreign = self.nav_state(
            run_id="other", history=[{"action": "nav-i1", "stage": "intake"}],
            improve_results={"nav-i1": {}},
        )
        for states in ([], [{"state": foreign}], [None, {"state": None}]):
            with self.subTest(states=states):
                self.result["navigation"] = {"states": states}
                assessment = self.assess()
                self.assertEqual(assessment["status"], "unverified", assessment)
                self.assertIn("current-run navigator state is missing", assessment["unverified"])

    def test_real_interaction_and_fresh_scoped_review_support_declarations(self):
        self.assertEqual(self.assess()["status"], "supported-pass")

    def test_dom_http_or_engine_do_not_satisfy_selected_ui_interaction(self):
        for method in ("dom", "http", "engine"):
            with self.subTest(method=method):
                review = deepcopy(self.review)
                review["selected_tests"][0]["observed_method"] = method
                self.assertEqual(self.assess(review)["status"], "supported-gap")

    def test_unrun_and_unjustified_na_remain_gaps(self):
        for disposition in ("unrun", "blocked", "not-applicable", "failed"):
            with self.subTest(disposition=disposition):
                review = deepcopy(self.review)
                review["selected_tests"][0]["disposition"] = disposition
                self.assertEqual(self.assess(review)["status"], "supported-gap")

    def test_unavailable_with_limitation_differs_from_missing_availability(self):
        row = self.review["improve_reviews"][0]
        row.update(independent_availability="unavailable", fresh_review_completed=False,
                   fallback_limitation="No independent reviewer was available; self-review has correlated blind spots.")
        self.assertEqual(self.assess()["status"], "supported-pass")
        del row["fallback_limitation"]
        self.assertEqual(self.assess()["status"], "supported-gap")
        del row["independent_availability"]
        self.assertEqual(self.assess()["status"], "unverified")

    def test_stale_evidence_bindings_duplicates_and_missing_scope_rejected(self):
        review = deepcopy(self.review)
        review["candidate_digest"] = "stale"
        self.assertEqual(self.assess(review)["status"], "invalid")
        review = deepcopy(self.review)
        review["dimensions"].append(review["dimensions"][0])
        self.assertEqual(self.assess(review)["status"], "invalid")
        self.review["improve_reviews"][0]["current_candidate"] = False
        self.assertEqual(self.assess()["status"], "supported-gap")
        (self.root / "evidence.txt").write_text("changed")
        self.assertEqual(self.assess()["status"], "invalid")

    def test_retired_review_schema_is_refused(self):
        self.review["schema"] = "shiploop-e2e-workflow-review/1"
        assessment = self.assess()
        self.assertEqual(assessment["status"], "invalid")
        self.assertIn(
            "unsupported workflow review schema; only shiploop-e2e-workflow-review/2 is accepted",
            assessment["errors"],
        )

    def test_omitted_selected_case_and_improve_action_cannot_pass(self):
        self.review["inventory"]["selected_test_ids"].append("A10")
        self.assertEqual(self.assess()["status"], "supported-gap")
        self.review["inventory"]["selected_test_ids"].remove("A10")
        self.review["inventory"]["improve_action_ids"].append("i2")
        self.assertEqual(self.assess()["status"], "supported-gap")
        self.review["inventory"]["improve_action_ids"].remove("i2")
        self.result["lifecycle"] = {"run_id": "current"}
        self.result["navigation"] = {"states": [{"state": self.nav_state(
            history=[{"action": "i1", "stage": "plan"}, {"action": "i2", "stage": "release-plan"}],
            improve_results={"i1": {}, "i2": {}},
        )}]}
        self.assertEqual(self.assess()["status"], "supported-gap")


if __name__ == "__main__":
    unittest.main()
