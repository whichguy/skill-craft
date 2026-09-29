#!/usr/bin/env python3
"""Focused tests for E2E cost accounting and fair comparison decisions."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import comparison  # noqa: E402
import metrics  # noqa: E402


CONDITIONS = {
    "host": "codex",
    "model": "test-model",
    "effort": None,
    "case_digest": "case-sha",
    "evaluator_digest": "evaluator-sha",
    "inputs_digest": "inputs-sha",
    "environment": {"python": "3.12", "settings": {"safe": True}},
    "budget": {"max_attempts": 2, "seconds": 600},
    "concurrency": 1,
    "dependency_digest": "dependencies-sha",
}
JUDGE = {"host": "codex", "model": "test-judge", "effort": "medium",
         "prompt_digest": "judge-prompt-sha", "evaluator_digest": "judge-evaluator-sha",
         "control_digest": "controls-sha"}


def row(invocation: str, *, passed: bool = True, subject: str = "subject-sha",
        qualified: bool = True, **fields) -> dict:
    result = {
        "case": "neutral-case",
        "style": "cli-files",
        "suite": "focused",
        "source": "checkout",
        "pass": passed,
        "turns": 100,
        "cost_usd": 100.0,
        "comparison": {**CONDITIONS, "subject_digest": subject},
        "identity": {
            "invocation_id": invocation,
            "subject_digest": subject,
            "evaluator_digest": CONDITIONS["evaluator_digest"],
            "case_digest": CONDITIONS["case_digest"],
        },
        "qualification": {"status": "qualified", "scope": "candidate"} if qualified else None,
        "review_identity": dict(JUDGE),
        "verdicts": {"process": passed, "shiploop": passed, "committed": passed},
        "checks_passed": 3,
        "checks": 3,
    }
    result.update(fields)
    return result


class MetricsCostTests(unittest.TestCase):
    def collect_sessions(self, sessions):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        out = Path(folder.name)
        (out / "events.jsonl").write_text("".join(json.dumps(event) + "\n" for event in sessions))
        return metrics.collect(out)

    def test_mixed_session_prices_keep_total_unknown_and_report_known_subtotal(self):
        result = self.collect_sessions([
            {"type": "end", "total_cost_usd": 0.0},
            {"type": "end", "total_cost_usd": None},
            {"type": "end", "total_cost_usd": 0.25},
        ])
        self.assertIsNone(result["cost_usd"])
        self.assertEqual(result["cost_status"], "partial")
        self.assertEqual(result["cost_known_subtotal_usd"], 0.25)

    def test_zero_cost_is_known_and_all_missing_prices_are_unknown(self):
        zero = self.collect_sessions([{"type": "end", "total_cost_usd": 0.0}])
        unknown = self.collect_sessions([{"type": "end", "total_cost_usd": None}])
        self.assertEqual(zero["cost_usd"], 0.0)
        self.assertEqual(zero["cost_status"], "known")
        self.assertEqual(zero["cost_known_subtotal_usd"], 0.0)
        self.assertIsNone(unknown["cost_usd"])
        self.assertEqual(unknown["cost_status"], "unknown")
        self.assertEqual(unknown["cost_known_subtotal_usd"], 0.0)

    def test_stage_cost_share_is_labeled_estimate_and_preserves_zero(self):
        stages = metrics.per_stage(
            [{"stage": "build", "t": 20.0}], [{"t": 20.0, "output": 0}], {}, {1: 10.0}, 0.0)
        self.assertEqual(stages[0]["cost_share_usd"], 0.0)
        self.assertTrue(stages[0]["cost_share_estimated"])


class ComparisonTests(unittest.TestCase):
    def test_baseline_row_preserves_existing_summary_fields_and_adds_identity(self):
        result = {
            **row("run-a"),
            "versions": {"source": "checkout", "plugin_version": "1", "shiploop_version": "2"},
            "metrics": {"turns": 17, "cost_usd": None, "cost_status": "partial",
                        "cost_known_subtotal_usd": 1.25, "model_glue": 2},
            "criteria": {"kind": "delivery", "expected_terminal": "done"},
            "process": {"sessions": [{"id": "s1"}]},
            "checks": [{"pass": True}, {"pass": False}],
            "invoked": {"pass": True},
        }
        saved = comparison.baseline_row(result, "cli-files", "focused")
        self.assertEqual(saved["checks_passed"], 1)
        self.assertEqual(saved["checks"], 2)
        self.assertEqual(saved["mandatory_check_failures"], 1)
        self.assertEqual(saved["turns"], 17)
        self.assertIsNone(saved["cost_usd"])
        self.assertEqual(saved["cost_known_subtotal_usd"], 1.25)
        self.assertEqual(saved["host"], "codex")
        self.assertIsNone(saved["effort"])
        self.assertEqual(saved["comparison_identity"]["dependency_digest"], "dependencies-sha")
        self.assertEqual(saved["identity"]["invocation_id"], "run-a")
        self.assertEqual(saved["criteria"]["kind"], "delivery")
        loaded = comparison._row_for_cli(saved)
        self.assertEqual(loaded["source"], "checkout")
        self.assertEqual(loaded["checks"], 2)
        self.assertEqual(loaded["cost_known_subtotal_usd"], 1.25)

    def test_previous_row_ignores_legacy_and_mismatched_conditions(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "rows.jsonl"
        legacy = {"case": "neutral-case", "source": "checkout", "pass": True}
        wrong = row("wrong", comparison={**CONDITIONS, "host": "claude"})
        matching = row("matching", subject="older-subject")
        path.write_text("\n".join(json.dumps(item) for item in (legacy, wrong, matching)) + "\n")
        found = comparison.previous_row(path, "neutral-case", "checkout", CONDITIONS)
        self.assertEqual(found["identity"]["invocation_id"], "matching")
        self.assertIsNone(comparison.previous_row(path, "neutral-case", "checkout", {"host": "codex"}))
        self.assertIsNone(comparison.previous_row(path, "neutral-case", "checkout"))

    def test_raw_pass_without_qualification_is_inconclusive(self):
        baseline = row("baseline", qualified=False)
        candidate = row("candidate", qualified=False, cost_usd=50.0)
        self.assertEqual(comparison.compare(baseline, candidate, "cost_usd", 0.1)["decision"], "inconclusive")

    def test_condition_mismatch_is_inconclusive_even_with_qualified_rows(self):
        baseline = row("baseline")
        candidate = row("candidate", comparison={**CONDITIONS, "model": "other-model"})
        self.assertEqual(comparison.compare(baseline, candidate)["decision"], "inconclusive")

    def test_different_or_missing_judge_identity_cannot_establish_improvement(self):
        baseline = row("baseline")
        for field in comparison.JUDGE_IDENTITY_FIELDS:
            candidate = row("candidate", cost_usd=50.0, review_identity={**JUDGE, field: "changed"})
            with self.subTest(field=field):
                result = comparison.compare(baseline, candidate, "cost_usd", 0.1)
                self.assertEqual(result["decision"], "inconclusive")
                self.assertIn("reviewer calibration identities differ", result["reasons"][0])
        self.assertEqual(comparison.compare(baseline, row("candidate", review_identity=None),
                                            "cost_usd", 0.1)["decision"], "inconclusive")

    def test_dependency_mismatch_is_inconclusive_but_subject_may_change(self):
        baseline = row("baseline", subject="old-subject")
        candidate = row("candidate", subject="new-subject")
        self.assertEqual(comparison.compare(baseline, candidate)["decision"], "no_demonstrated_change")
        changed_dependency = row(
            "candidate-2", comparison={**CONDITIONS, "dependency_digest": "other-dependencies"})
        self.assertEqual(comparison.compare(baseline, changed_dependency)["decision"], "inconclusive")

    def test_missing_run_identity_is_inconclusive(self):
        baseline = row("baseline")
        candidate = row("candidate")
        candidate.pop("identity")
        self.assertEqual(comparison.compare(baseline, candidate)["decision"], "inconclusive")

    def test_reviewed_mandatory_failure_is_a_regression_even_when_unresolved(self):
        baseline = row("baseline", passed=True)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        result_path = Path(folder.name) / "result.json"
        review_path = Path(folder.name) / "review.json"
        identity = {"invocation_id": "candidate", "subject_digest": "subject-sha",
                    "evaluator_digest": CONDITIONS["evaluator_digest"],
                    "case_digest": CONDITIONS["case_digest"]}
        retained = {
            **row("candidate", passed=False),
            "identity": identity,
            "qualification": {"status": "pending_review", "scope": "candidate"},
            "checks": [{"pass": False}, {"pass": True}, {"pass": True}],
            "process": {"pass": True, "sessions": []},
            "evidence": {"status": "valid", "reasons": []},
        }
        review = {
            "schema": "shiploop-e2e-review/1",
            "identity": identity,
            "validity": {"pass": True},
            "process": {"status": "exited", "returncode": 0, "capture_errors": [], "cleanup_error": None},
            "judge_calibration": {"status": "passed", "identity": dict(JUDGE)},
            "qualification": {"status": "unresolved", "scope": "candidate",
                              "reasons": ["one mandatory check failed", "semantic coverage remains unknown"]},
            "seal_digest_after": "seal-digest",
        }
        result_path.write_text(json.dumps(retained))
        review_path.write_text(json.dumps(review))
        with patch.object(comparison.evidence, "verify_seal", return_value=[]), \
                patch.object(comparison.evidence, "tree_digest", return_value="seal-digest"):
            reviewed, errors = comparison._overlay_review(retained, result_path, review_path)
        self.assertEqual(errors, [])
        self.assertEqual(reviewed["qualification"]["status"], "unresolved")
        candidate = comparison.baseline_row(reviewed, "cli-files", "focused")
        result = comparison.compare(baseline, candidate, "cost_usd", 0.2)
        self.assertEqual(result["decision"], "regressed")
        self.assertFalse(result["reliability_claim"])
        self.assertEqual(result["known_mandatory_check_failures"], 1)
        self.assertIn("semantic coverage remains unknown", result["unknowns"])

    def test_unresolved_candidate_without_complete_evidence_cannot_claim_regression(self):
        baseline = row("baseline")
        candidate = row(
            "candidate", passed=False, qualified=False,
            qualification={"status": "unresolved", "scope": "candidate", "reasons": ["check failed"]},
            mandatory_check_failures=1, evidence_status="valid", process={"pass": True},
            review_validity_pass=True, review_calibration_pass=True, review_process_pass=True,
            review_schema_valid=True)
        for changes in (
            {"review_process_pass": False},
            {"evidence_status": "incomplete"},
            {"process": {"pass": False}},
            {"qualification": {"status": "pending_review", "scope": "candidate"}},
        ):
            with self.subTest(changes=changes):
                incomplete = {**candidate, **changes}
                self.assertEqual(comparison.compare(baseline, incomplete)["decision"], "inconclusive")

    def test_cost_benefit_must_meet_declared_relative_threshold(self):
        baseline = row("baseline", cost_usd=100.0)
        candidate = row("candidate", cost_usd=80.0, subject="new-subject")
        self.assertEqual(comparison.compare(baseline, candidate, "cost_usd", 0.15)["decision"], "improved")
        below_threshold = comparison.compare(baseline, row("candidate-2", cost_usd=90.0), "cost_usd", 0.15)
        self.assertEqual(below_threshold["decision"], "no_demonstrated_change")
        self.assertEqual(comparison.compare(baseline, candidate, "cost_usd")["decision"],
                         "no_demonstrated_change")
        self.assertEqual(comparison.compare(baseline, candidate, threshold=0.15)["decision"], "inconclusive")

    def test_zero_baseline_keeps_absolute_delta_without_relative_benefit_claim(self):
        baseline = row("baseline", success_count=0.0)
        candidate = row("candidate", success_count=1.0)
        result = comparison.compare(baseline, candidate, "success_count", 0.1)
        self.assertEqual(result["decision"], "inconclusive")
        self.assertEqual(result["absolute_delta"], 1.0)
        self.assertIsNone(result["benefit_fraction"])

    def test_missing_cost_cannot_be_scored_as_zero(self):
        baseline = row("baseline", cost_usd=4.0)
        candidate = row("candidate", cost_usd=None, cost_status="partial", cost_known_subtotal_usd=1.0)
        self.assertEqual(comparison.compare(baseline, candidate, "cost_usd", 0.1)["decision"], "inconclusive")

    def test_suite_counts_keep_retries_out_of_independent_denominator(self):
        verified = {"status": "checks_passed", "pass": True,
                    "qualification": {"status": "qualified", "scope": "candidate"},
                    "criteria": {"kind": "delivery"}}
        scenario = {"status": "checks_passed", "pass": True,
                    "qualification": {"status": "qualified", "scope": "candidate"},
                    "criteria": {"kind": "boundary"}}
        no_op = {"status": "checks_passed", "pass": True,
                 "qualification": {"status": "qualified", "scope": "candidate"},
                 "criteria": {"kind": "noop"}}
        pending = {"status": "checks_passed", "pass": True,
                   "qualification": {"status": "pending_review", "scope": "candidate"},
                   "criteria": {"kind": "delivery"}}
        rows = [
            {"suite": "focused", "case": "a", "attempt": 1, "status": "failed", "pass": False},
            {"suite": "focused", "case": "a", "attempt": 2, "retry_of": "a-1", **verified},
            {"suite": "focused", "case": "b", "status": "skipped", "pass": None},
            {"suite": "focused", "case": "c", **pending},
            {"suite": "focused", "case": "d", "status": "blocked_preflight", "pass": None},
            {"suite": "focused", "case": "e", **scenario},
            {"suite": "focused", "case": "f", **no_op},
            {"suite": "focused", "case": "g", "status": "checks_passed", "pass": True,
             "qualification": {"status": "qualified", "scope": "candidate"}},
        ]
        counts = comparison.suite_counts(rows)["focused"]
        self.assertEqual(counts["slots"], 7)
        self.assertEqual(counts["required_slots"], 7)
        self.assertEqual(counts["started_attempts"], 6)
        self.assertEqual(counts["independent_started_trials"], 5)
        self.assertEqual(counts["retry_attempts"], 1)
        self.assertEqual(counts["first_attempt"]["failed"], 1)
        self.assertEqual(counts["latest_attempt"]["verified_delivery"], 1)
        self.assertEqual(counts["verified_scenarios"], 2)
        self.assertEqual(counts["verified_boundary_scenarios"], 1)
        self.assertEqual(counts["verified_noop_scenarios"], 1)
        self.assertEqual(counts["skipped_slots"], 1)
        self.assertEqual(counts["unknown_slots"], 3)

    def test_cli_review_overlay_requires_exact_identity_validity_process_and_seal(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        result_path = Path(folder.name) / "result.json"
        review_path = Path(folder.name) / "review.json"
        identity = {"invocation_id": "run-a"}
        result = {"identity": identity, "process": {"pass": True},
                  "qualification": {"status": "pending_review"}}
        review = {
            "schema": "shiploop-e2e-review/1",
            "identity": identity,
            "validity": {"pass": True},
            "process": {"status": "exited", "returncode": 0, "capture_errors": [], "cleanup_error": None},
            "judge_calibration": {"status": "passed", "identity": dict(JUDGE)},
            "qualification": {"status": "qualified", "scope": "candidate"},
            "seal_digest_after": "seal-digest",
        }
        review_path.write_text(json.dumps(review))
        with patch.object(comparison.evidence, "verify_seal", return_value=[]), \
                patch.object(comparison.evidence, "tree_digest", return_value="seal-digest"):
            merged, errors = comparison._overlay_review(result, result_path, review_path)
        self.assertEqual(errors, [])
        self.assertEqual(merged["qualification"]["status"], "qualified")
        self.assertTrue(merged["review_validity_pass"])
        self.assertTrue(merged["review_calibration_pass"])
        self.assertTrue(merged["review_process_pass"])
        self.assertTrue(merged["review_schema_valid"])
        self.assertEqual(result["qualification"]["status"], "pending_review")

        with patch.object(comparison.evidence, "verify_seal", return_value=["changed events"]), \
                patch.object(comparison.evidence, "tree_digest", return_value="seal-digest"):
            rejected, errors = comparison._overlay_review(result, result_path, review_path)
        self.assertTrue(any("evidence seal" in error for error in errors))
        self.assertEqual(rejected["qualification"]["status"], "pending_review")

    def test_cli_review_overlay_rejects_invalid_envelopes_and_resealed_attempts(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        result_path = Path(folder.name) / "result.json"
        review_path = Path(folder.name) / "review.json"
        identity = {"invocation_id": "run-a"}
        result = {"identity": identity, "process": {"pass": True},
                  "qualification": {"status": "pending_review"}}
        base = {
            "schema": "shiploop-e2e-review/1",
            "identity": identity,
            "validity": {"pass": True},
            "process": {"status": "exited", "returncode": 0, "capture_errors": [], "cleanup_error": None},
            "judge_calibration": {"status": "passed", "identity": dict(JUDGE)},
            "qualification": {"status": "qualified", "scope": "candidate"},
            "seal_digest_after": "current-seal",
        }
        invalid = []
        for label, change in (
            ("schema", lambda review: review.pop("schema")),
            ("identity", lambda review: review.update(identity={"invocation_id": "other"})),
            ("validity", lambda review: review.update(validity={"pass": False})),
            ("process status", lambda review: review["process"].update(status="failed")),
            ("process return code", lambda review: review["process"].update(returncode=1)),
            ("capture errors", lambda review: review["process"].update(capture_errors=["truncated stream"])),
            ("cleanup error", lambda review: review["process"].update(cleanup_error="owned child remains")),
            ("calibration", lambda review: review.update(judge_calibration={"status": "failed"})),
            ("re-sealed evidence", lambda review: review.update(seal_digest_after="old-seal")),
        ):
            review = json.loads(json.dumps(base))
            change(review)
            review_path.write_text(json.dumps(review))
            with patch.object(comparison.evidence, "verify_seal", return_value=[]), \
                    patch.object(comparison.evidence, "tree_digest", return_value="current-seal"):
                rejected, errors = comparison._overlay_review(result, result_path, review_path)
            self.assertTrue(errors, label)
            self.assertEqual(rejected["qualification"]["status"], "pending_review", label)
            invalid.append(label)
        self.assertEqual(len(invalid), 9)


if __name__ == "__main__":
    unittest.main()
