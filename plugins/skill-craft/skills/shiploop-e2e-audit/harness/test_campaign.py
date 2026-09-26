"""Campaign accounting cannot hide failures, missing cases or incomparable arms."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from campaign import summarize, _settings
from grading import write_template, validate_receipt
from workflow_review import DIMENSIONS
import hashlib


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.document = {"schema": "shiploop-e2e-campaign/1", "arms": [
            {"id": "baseline", "expected_skill_digest": "s1", "cases": [{"step_id": "ttt-create", "repetition": 1, "trial": "one"}]},
            {"id": "candidate", "expected_skill_digest": "s2", "cases": [{"step_id": "ttt-create", "repetition": 1, "trial": "two"}]}]}
        for name, skill, status in [("one", "s1", "product-failed"), ("two", "s2", "passed")]:
            folder = self.root / name
            folder.mkdir()
            manifest = {"trial_id": name, "scenario": {"id": "ttt-create"}, "prompt_sha256": "p",
                        "preflight": {"model_requested": "grok-4.6"}, "reasoning_effort_requested": "xhigh",
                        "timeout_seconds": 4800, "max_turns": 1000, "permission_mode": "default",
                        "partial": False, "stop_after_stage": None, "harness_sha256": "observer"}
            result = {"trial_id": name, "step_id": "ttt-create", "statuses": {"overall": status},
                      "skill_digest": skill, "skill_stable": True, "observer_stable": True,
                      "candidate_digest": name, "baseline_digest": None, "process": {"duration_seconds": 25}}
            (folder / "manifest.json").write_text(json.dumps(manifest))
            (folder / "result.json").write_text(json.dumps(result))
            (folder / "verification.json").write_text(json.dumps({"verifier": "oracle/1"}))
            (folder / "before.json").write_text(json.dumps({"new_empty_folder": True, "head": None, "files": [], "status": []}))

    def fully_bound_pair(self):
        for arm in self.document["arms"]:
            case = arm["cases"][0]
            folder = self.root / case["trial"]
            result = json.loads((folder / "result.json").read_text())
            manifest = json.loads((folder / "manifest.json").read_text())
            required = ["local-check"]
            result.update(required_checks=required, harness_snapshot={"package_sha256": "observer"})
            manifest["scenario"]["required_checks"] = required
            evidence = folder / "verification"
            evidence.mkdir()
            (evidence / "observation.txt").write_text("Recorded UI interaction and independent review")
            ref = {"path": "observation.txt", "sha256": hashlib.sha256((evidence / "observation.txt").read_bytes()).hexdigest()}
            receipt = write_template(folder / "verification.json", trial_id=result["trial_id"],
                                     candidate_digest=result["candidate_digest"], required_checks=required)
            receipt.update(verifier="oracle/1", verifier_inputs_sha256="a" * 64)
            receipt["checks"][0].update(status="pass" if result["statuses"]["overall"] == "passed" else "fail", evidence=[ref])
            (folder / "verification.json").write_text(json.dumps(receipt))
            grade = validate_receipt(receipt, trial_id=result["trial_id"], candidate_digest=result["candidate_digest"],
                                     baseline_digest=None, required_checks=required, evidence_root=evidence)
            (folder / "grade.json").write_text(json.dumps(grade))
            (folder / "manifest.json").write_text(json.dumps(manifest))
            (folder / "result.json").write_text(json.dumps(result))
            arm["expected_settings"] = _settings(manifest, result, json.loads((folder / "before.json").read_text()))
            arm["expected_settings"].update(verifier_identity="oracle/1", verifier_inputs_sha256="a" * 64)
            review = {"schema": "shiploop-e2e-workflow-review/2", "trial_id": result["trial_id"],
                      "candidate_digest": result["candidate_digest"], "baseline_digest": None,
                      "skill_digest": result["skill_digest"], "harness_digest": "observer", "reviewer": "fixture reviewer",
                      "reviewed_at": "2026-09-17", "scope": "Fixture UI and source",
                      "inventory": {"selected_test_ids": ["A1"], "improve_action_ids": ["i1"], "evidence": [ref]},
                      "dimensions": [{"id": key, "status": "supported-pass", "evidence": [ref], "notes": "Observed"} for key in DIMENSIONS],
                      "selected_tests": [{"id": "A1", "required_method": "interaction", "observed_method": "interaction", "disposition": "passed", "evidence": [ref]}],
                      "improve_reviews": [{"action_id": "i1", "independent_availability": "available", "fresh_review_completed": True,
                                           "scope": "Current source", "current_candidate": True, "evidence": [ref]}]}
            (evidence / "review.json").write_text(json.dumps(review))
            case["workflow_review"] = str((evidence / "review.json").relative_to(self.root))

    def test_preregistered_bound_evidence_supports_comparison_without_declaring_winner(self):
        self.fully_bound_pair()
        report = summarize(self.document, self.root)
        self.assertEqual(report["pairs"][0]["status"], "settings-matched")
        self.assertEqual(report["pairs"][0]["limits"], [])
        self.assertEqual(report["attempts"][0]["receipt_revalidation"]["product_status"], "failed")
        self.assertEqual(report["attempts"][1]["receipt_revalidation"]["product_status"], "passed")
        self.assertNotIn("winner", report)

    def test_tampered_receipt_evidence_and_saved_grade_invalidate_comparison(self):
        self.fully_bound_pair()
        (self.root / "two/verification/observation.txt").write_text("Replaced evidence")
        report = summarize(self.document, self.root)
        self.assertEqual(report["pairs"][0]["status"], "descriptive-only")
        self.assertIn("receipt evidence/binding invalid", report["pairs"][0]["limits"])
        self.assertIn("saved grade missing or differs from current validation", report["pairs"][0]["limits"])

    def test_every_selected_attempt_and_missing_review_remains_visible(self):
        self.document["arms"][1]["cases"].append({"step_id": "ttt-create", "repetition": 2, "trial": None})
        report = summarize(self.document, self.root)
        self.assertEqual(report["selected"], 3)
        self.assertEqual(report["counted"], 3)
        self.assertEqual(report["arms"][0]["statuses"], {"product-failed": 1})
        self.assertEqual(report["arms"][1]["statuses"], {"not-run": 1, "passed": 1})
        self.assertTrue(all(pair["status"] == "descriptive-only" for pair in report["pairs"]))

    def test_reusing_trial_or_duplicate_repetition_cannot_inflate_denominator(self):
        document = deepcopy(self.document)
        document["arms"][1]["cases"][0]["trial"] = "one"
        with self.assertRaisesRegex(ValueError, "same trial"):
            summarize(document, self.root)
        document = deepcopy(self.document)
        document["arms"][0]["cases"].append(document["arms"][0]["cases"][0])
        with self.assertRaisesRegex(ValueError, "duplicate case"):
            summarize(document, self.root)

    def test_budget_effort_observer_and_baseline_differences_are_descriptive(self):
        path = self.root / "two/manifest.json"
        manifest = json.loads(path.read_text())
        manifest.update(timeout_seconds=240, reasoning_effort_requested="low", harness_sha256="other")
        path.write_text(json.dumps(manifest))
        path = self.root / "two/result.json"
        result = json.loads(path.read_text())
        result["baseline_digest"] = "different-baseline"
        path.write_text(json.dumps(result))
        limits = summarize(self.document, self.root)["pairs"][0]["limits"]
        for field in ("timeout_seconds", "reasoning_effort", "observer_digest", "baseline_digest"):
            self.assertIn("different " + field, limits)

    def test_forged_step_and_unregistered_skill_are_not_clean_comparisons(self):
        self.document["arms"][1]["expected_skill_digest"] = "wrong"
        report = summarize(self.document, self.root)
        self.assertIn("skill differs from registered arm", report["pairs"][0]["limits"])
        self.document["arms"][1]["cases"][0]["step_id"] = "ttt-guidance"
        report = summarize(self.document, self.root)
        self.assertEqual(report["attempts"][1]["status"], "invalid-record")

    def test_seeded_repository_wrong_shared_settings_and_ungraded_receipt_are_limited(self):
        path = self.root / "two/before.json"
        path.write_text(json.dumps({"new_empty_folder": False, "head": "readme-commit", "files": [{"path": "README.md", "sha256": "s"}]}))
        for arm in self.document["arms"]:
            arm["expected_settings"] = {"reasoning_effort": "xhigh"}
            path = self.root / arm["cases"][0]["trial"] / "manifest.json"
            manifest = json.loads(path.read_text())
            manifest["reasoning_effort_requested"] = "low"
            path.write_text(json.dumps(manifest))
        limits = summarize(self.document, self.root)["pairs"][0]["limits"]
        self.assertIn("different initial_source_digest", limits)
        self.assertIn("reasoning_effort differs from registered setting", limits)
        self.assertIn("receipt requirements/bindings incomplete", limits)


if __name__ == "__main__":
    unittest.main()
