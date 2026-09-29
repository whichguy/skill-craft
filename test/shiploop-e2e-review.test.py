#!/usr/bin/env python3
"""Focused review, iteration and reviewer-calibration regressions."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import calibrate  # noqa: E402
import evidence  # noqa: E402
import hosts  # noqa: E402
import iterate  # noqa: E402
import review  # noqa: E402


CRITERIA = {
    "requirements": [{"id": "R-1", "description": "Produce the requested result."}],
    "workflow": ["S-1", "S-9"],
    "kind": "delivery",
    "expected_terminal": "done",
}


def response(*, findings=None, unresolved=None, harness=None):
    return {
        "summary": "The requested result is present and checked.",
        "observed_terminal": "done",
        "requirements": [{"id": "R-1", "status": "verified", "evidence": ["result.json#/checks/0"],
                           "contrary_evidence": [], "reason": "The retained check passed."}],
        "workflow": [{"id": "S-1", "status": "pass", "evidence": ["transcript.md#final"],
                      "contrary_evidence": [], "reason": "The script-owned state is retained."},
                     {"id": "S-9", "status": "pass", "evidence": ["result.json#/checks/0"],
                      "contrary_evidence": [], "reason": "A recorded check passed."}],
        "findings": findings or [],
        "unresolved_material": unresolved or [],
        "harness_dispositions": harness or [],
    }


def material_finding(*, preserves=True, remedy="proposed", scope="shiploop", disposition="open"):
    return {
        "id": "F-1", "scope": scope, "severity": "material", "title": "A supported defect",
        "evidence": ["result.json#/checks/0"], "contrary_evidence": [],
        "preserves_premise": preserves, "premise_clause": "S-1" if preserves else None,
        "premise_note": "The proposed change keeps or breaks the script-owned graph.",
        "cause": {"status": "supported", "explanation": "The script omitted a verified transition."},
        "hypotheses": [], "falsifier": "Replay with the transition recorded.",
        "disposition": disposition, "disposition_reason": "The issue remains material.",
        "resolution_evidence": [], "remedy": {"disposition": remedy, "proposal": "Restore the recorded transition."},
    }


def run_fixture(*, source="checkout", passed=True, ci=None):
    identity = {"invocation_id": "invoke-1", "subject_digest": "subject-1",
                "evaluator_digest": "evaluator-1", "case_digest": "case-1"}
    result = {
        "identity": {**identity, "candidate_digest": "candidate-1"},
        "evidence": {"status": "valid", "reasons": []},
        "pass": passed,
        "checks": [{"pass": True}],
        "shiploop": {"status": "done"},
        "versions": {"source": source, "released": {"origin_main": "abc123"}},
        "process": {"ci": ci} if ci is not None else {},
    }
    evaluation = {"identity": identity, "criteria": CRITERIA}
    return result, evaluation


def qualified_record(result, payload=None):
    return {
        "schema": review.REVIEW_SCHEMA,
        "identity": result["identity"],
        "process": {"status": "exited", "returncode": 0, "capture_errors": [], "cleanup_error": None},
        "reviewer": {"host": "grok", "model": "test-model", "effort": "medium"},
        **(payload or response()),
    }


class ReviewSchemaTests(unittest.TestCase):
    def test_complete_requirements_and_workflow_are_required(self):
        self.assertEqual(review.validate_response(response(), CRITERIA), [])
        incomplete = response()
        incomplete["workflow"] = incomplete["workflow"][:-1]
        self.assertTrue(any("workflow coverage must match" in error
                            for error in review.validate_response(incomplete, CRITERIA)))

    def test_empty_criteria_and_n_a_without_frozen_condition_are_rejected(self):
        self.assertTrue(review.validate_response(response(), {**CRITERIA, "requirements": []}))
        invalid = response()
        invalid["requirements"][0]["status"] = "not_applicable"
        self.assertTrue(any("without a frozen condition" in error
                            for error in review.validate_response(invalid, CRITERIA)))

    def test_malformed_model_field_types_return_errors_instead_of_raising(self):
        for field in review.RESPONSE_FIELDS:
            for wrong_type in (None, 4, {}, [None]):
                payload = response()
                payload[field] = wrong_type
                with self.subTest(field=field, value=wrong_type):
                    self.assertTrue(review.validate_response(payload, CRITERIA))

    def test_prior_open_finding_must_remain_and_rejected_remedy_does_not_close_it(self):
        finding = material_finding(remedy="rejected")
        payload = response(findings=[finding], unresolved=[{"finding_id": "F-1", "disposition": "open",
                                                            "reason": "The proposed remedy is rejected; defect remains."}])
        self.assertEqual(review.validate_response(payload, CRITERIA, prior_findings=[finding]), [])
        self.assertEqual(review.actionable(payload), [])
        payload["findings"] = []
        self.assertTrue(any("previously unresolved" in error
                            for error in review.validate_response(payload, CRITERIA, prior_findings=[finding])))

    def test_premise_breaking_remedy_is_not_actionable(self):
        finding = material_finding(preserves=False, remedy="rejected")
        payload = response(findings=[finding], unresolved=[{"finding_id": "F-1", "disposition": "open",
                                                            "reason": "The rejected remedy leaves the finding open."}])
        self.assertEqual(review.validate_response(payload, CRITERIA), [])
        self.assertEqual(review.actionable(payload), [])

    def test_timeouts_capture_errors_identity_and_raw_failure_block_qualification(self):
        result, evaluation = run_fixture()
        record = qualified_record(result)
        record["process"]["status"] = "timeout"
        record["process"]["capture_errors"] = ["reader failed"]
        qualification = review.qualify_review(record, result, evaluation, calibration={"status": "passed"})
        self.assertFalse(record["validity"]["pass"])
        self.assertFalse(qualification["clean"])

        result, evaluation = run_fixture(passed=False)
        record = qualified_record(result)
        qualification = review.qualify_review(record, result, evaluation, calibration={"status": "passed"})
        self.assertEqual(qualification["status"], "unresolved")
        self.assertFalse(qualification["clean"])

    def test_calibration_pending_keeps_valid_review_provisional(self):
        result, evaluation = run_fixture()
        record = qualified_record(result)
        qualification = review.qualify_review(record, result, evaluation, calibration={"status": "not_run"})
        self.assertTrue(record["validity"]["pass"])
        self.assertEqual(qualification["status"], "pending_calibration")
        self.assertFalse(review.is_clean(record))

    def test_release_uses_final_pinned_ci_only(self):
        result, evaluation = run_fixture(source="marketplace")
        result["versions"]["released"]["ci"] = {"status": "success", "commit": "abc123"}
        record = qualified_record(result)
        qualification = review.qualify_review(record, result, evaluation, calibration={"status": "passed"})
        self.assertEqual(qualification["status"], "pending_release_ci")
        result["process"]["ci"] = {"status": "success", "commit": "wrong", "failed": False}
        record = qualified_record(result)
        qualification = review.qualify_review(record, result, evaluation, calibration={"status": "passed"})
        self.assertEqual(qualification["status"], "pending_release_ci")
        result["process"]["ci"] = {"status": "success", "commit": "abc123", "failed": False}
        record = qualified_record(result)
        qualification = review.qualify_review(record, result, evaluation, calibration={"status": "passed"})
        self.assertEqual(qualification["status"], "qualified")
        self.assertEqual(qualification["scope"], "release")


class CalibrationIntegrityTests(unittest.TestCase):
    def make_receipt(self, parent):
        spec_path = ROOT / "test" / "shiploop_e2e" / "SPEC.md"
        receipt_path = parent / "judge.json"
        evidence_root = parent / "judge.evidence-test"
        evidence_root.mkdir()
        identity = review.calibration_identity(host="grok", model="test-model", effort="medium",
                                               spec_path=spec_path, control_digest=calibrate.control_digest())
        attempts = []
        for attempt_id in review.CALIBRATION_CONTROL_IDS:
            stage = evidence_root / attempt_id
            stage.mkdir()
            (stage / "evaluation").mkdir()
            (stage / "evaluation" / "SPEC.md").write_text("frozen spec")
            for name in ("evaluation.json", "prompt.txt", "result.json", "transcript.md", "events.jsonl",
                         "metrics.json", "review-prompt.txt"):
                (stage / name).write_text(name)
            (stage / "review-events.jsonl").write_text("{}\n")
            (stage / "review-stderr.txt").write_text("")
            (stage / "calibration-result.json").write_text("{}\n")
            expected = review.CALIBRATION_CONTROL_EXPECTED[attempt_id]
            inputs = review.retained_calibration_inputs(stage)
            outputs = review.retained_calibration_outputs(stage)
            attempts.append({"attempt_id": attempt_id, "expected": expected, "observed": expected,
                             "result": "matched", "reasons": [], "error": None,
                             "process": {"status": "exited", "returncode": 0, "capture_errors": [],
                                         "cleanup_error": None},
                             "evidence_path": attempt_id, "input_digests": inputs,
                             "input_digest": evidence.object_digest(inputs), "output_digests": outputs})
        receipt = {"schema": review.CALIBRATION_SCHEMA, "status": "passed", "identity": identity,
                   "summary": {"controls": 5, "matched": 5, "false_alarms": 0, "misses": 0, "unknown": 0},
                   "attempts": attempts, "evidence_dir": str(evidence_root)}
        evidence.atomic_json(receipt_path, receipt)
        return receipt_path, evidence_root

    def test_empty_receipt_cannot_claim_model_calibration(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "empty.json"
            evidence.atomic_json(receipt, {"schema": review.CALIBRATION_SCHEMA, "status": "passed",
                                           "identity": {}, "summary": {"controls": 0, "matched": 0,
                                           "false_alarms": 0, "misses": 0, "unknown": 0}, "attempts": []})
            status = review._calibration_status(receipt, {"host": "grok", "model": "test-model", "effort": "medium"},
                                                ROOT / "test" / "shiploop_e2e" / "SPEC.md")
            self.assertNotEqual(status["status"], "passed")
            self.assertTrue(any("five" in reason or "exactly five" in reason for reason in status["reasons"]))

    def test_valid_complete_receipt_passes_then_tampering_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt, evidence_root = self.make_receipt(Path(tmp))
            reviewer = {"host": "grok", "model": "test-model", "effort": "medium"}
            spec = ROOT / "test" / "shiploop_e2e" / "SPEC.md"
            self.assertEqual(review._calibration_status(receipt, reviewer, spec)["status"], "passed")
            (evidence_root / "control-01" / "result.json").write_text("tampered")
            status = review._calibration_status(receipt, reviewer, spec)
            self.assertEqual(status["status"], "failed")
            self.assertTrue(any("inputs changed" in reason for reason in status["reasons"]))

    def test_controls_keep_check_evidence_rows_and_boundary_gate_applicability(self):
        controls = {row["id"]: row for row in calibrate.load_controls()}
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp) / "blocked"
            stage.mkdir()
            result, _ = calibrate._write_control_files(stage, controls["blocked"],
                                                       ROOT / "test" / "shiploop_e2e" / "SPEC.md", {}, "control-02")
            self.assertTrue(result["pass"])
            self.assertEqual(len(result["checks"]), 2)
            self.assertEqual(result["shiploop"]["status"], "awaiting")
            self.assertTrue(result["process"]["questions_awaiting_reply"])
            self.assertEqual(result["process"]["timeout_seconds"], 60)
            state = (stage / "state.md").read_text()
            for required in ("question:", "no_default:", "independent_work:", "resume_command:",
                             "--run-dir /fixture/run --answer"):
                self.assertIn(required, state)
            for check in result["checks"]:
                self.assertEqual(check["stdin"], "closed")
                self.assertEqual(check["timeout_seconds"], 10)
            defect_stage = Path(tmp) / "defect"
            defect_stage.mkdir()
            defect, _ = calibrate._write_control_files(defect_stage, controls["defect"],
                                                        ROOT / "test" / "shiploop_e2e" / "SPEC.md", {}, "control-04")
            self.assertFalse(defect["pass"])
            self.assertIn("expected open=2", defect["checks"][0]["command"])
            self.assertTrue(defect["checks"][1]["pass"])
            self.assertEqual(json.loads((defect_stage / "work/input.json").read_text())["records"],
                             [{"status": "open"}, {"status": "closed"}, {"status": "open"}])
            self.assertEqual(defect["process"]["stdin"], "closed")
            for check in defect["checks"]:
                self.assertEqual(check["stdin"], "closed")
                self.assertEqual(check["timeout_seconds"], 10)
            self.assertIn('"timeout_seconds": 10', (defect_stage / "run/tests/report-verify1.md").read_text())
            incomplete_stage = Path(tmp) / "incomplete"
            incomplete_stage.mkdir()
            calibrate._write_control_files(incomplete_stage, controls["incomplete"],
                                            ROOT / "test" / "shiploop_e2e" / "SPEC.md", {}, "control-05")
            self.assertIn("truncated JSON record", (incomplete_stage / "events.jsonl").read_text())

    def test_positive_control_label_cannot_manufacture_a_passing_verification(self):
        for totals in ({"open": 0, "closed": 1, "blocked": 0},
                       {"open": 2, "closed": 1, "blocked": 0, "invented": 99}):
            control = next(row for row in calibrate.load_controls() if row["id"] == "correct")
            report = next(row for row in control["run"]["primary_evidence"]
                          if row["locator"] == "work/report.json#/totals")
            report["text"] = json.dumps({"totals": totals})
            with self.subTest(totals=totals), tempfile.TemporaryDirectory() as tmp:
                stage = Path(tmp)
                result, _ = calibrate._write_control_files(stage, control,
                    ROOT / "test" / "shiploop_e2e" / "SPEC.md", {}, "control-03")
                self.assertFalse(result["pass"])
                self.assertFalse(result["checks"][0]["pass"])
                self.assertIn('"passed": false', (stage / "run/tests/report-verify1.md").read_text())
                self.assertEqual(evidence.read_json(stage / "metrics.json")["script_verifications"]["passed"], 0)

    def test_unknown_materiality_cannot_pass_calibration_as_clean(self):
        finding = material_finding()
        finding["severity"] = "unknown"
        payload = response(findings=[finding])
        observed, reasons = calibrate.classify_response(payload, {
            "criteria": CRITERIA, "run": {"evidence_status": "valid"}})
        self.assertEqual(observed, "unknown")
        self.assertTrue(reasons)

    def test_a_matching_response_with_integrity_reasons_is_unknown(self):
        control = {"id": "correct", "expected_class": "clean"}
        row = calibrate.compare_control(control, "clean", ["retained inputs changed"], True)
        self.assertEqual(row["result"], "unknown")


class IterationAndHostTests(unittest.TestCase):
    def test_improver_paths_are_explicit_and_evaluator_is_excluded(self):
        self.assertEqual(iterate.validate_allow_tests(["test/unit/example.test.py"]), ["test/unit/example.test.py"])
        for path in ("test/shiploop_e2e/review.py", "test/shiploop-e2e-review.test.py", "test/../outside.py"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                iterate.validate_allow_tests([path])

    def test_improver_report_requires_process_success_and_adversarial_record(self):
        process = {"status": "exited", "returncode": 0, "capture_errors": [], "cleanup_error": None}
        good = {"applied": [{"title": "Fix", "anchor": ["S-13"],
                             "adversarial": [{"consequence": "Could specialize by case", "disposition": "mitigated",
                                              "how": "Kept the generic script check."}]}],
                "skipped": [], "tests": "quick tier passed"}
        self.assertEqual(iterate.validate_improve_report(good, process), [])
        bad = json.loads(json.dumps(good))
        bad["applied"][0]["adversarial"] = []
        self.assertTrue(iterate.validate_improve_report(bad, process))
        process["cleanup_error"] = "child survived"
        self.assertTrue(iterate.validate_improve_report(good, process))

    def test_codex_reviewer_uses_supported_read_only_sandbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_file = root / "prompt.txt"
            argv = hosts.CodexHost("codex").argv(prompt="review", prompt_file=prompt_file, cwd=root,
                                                 model="model", effort="low", permission_mode="auto",
                                                 max_turns=1, read_only=True)
            self.assertIn("read-only", argv)
            self.assertNotIn("danger-full-access", argv)


if __name__ == "__main__":
    unittest.main()
