"""Strict report-gate classification tests using only temporary evidence."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import report


class ReportClassificationTests(unittest.TestCase):
    def evidence(self):
        return (
            {"status": "PASS", "passed": True},
            {"exit_code": 0, "elapsed_s": 1.25},
            {"passed": True, "checks": {"manifest.json": True, "prompt.txt": True}},
            {"status": "PASS", "passed": True, "parent_exit_code": 0,
             "filesystem_passed": True, "verifier_exit_code": 0},
            {"passed": True},
        )

    def test_complete_required_evidence_passes(self):
        result = report.classify_verdict(*self.evidence())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["failed_gates"], [])
        self.assertEqual(result["incomplete_gates"], [])
        self.assertIn("integrity", result["reasons"][0])

    def test_native_nonpass_statuses_with_passed_false_are_incomplete(self):
        for native_status in ("UNKNOWN", "INCOMPLETE", "RECOVERED"):
            with self.subTest(native_status=native_status):
                _native, process, integrity, gate, filesystem = self.evidence()
                native = {"status": native_status, "passed": False}
                result = report.classify_verdict(native, process, integrity, gate, filesystem)
                self.assertEqual(result["status"], "INCOMPLETE")
                self.assertEqual(result["failed_gates"], [])
                self.assertTrue(any(native_status in reason for reason in result["incomplete_gates"]))

    def test_native_pass_with_passed_false_is_explicit_failure(self):
        _native, process, integrity, gate, filesystem = self.evidence()
        native = {"status": "PASS", "passed": False}
        result = report.classify_verdict(native, process, integrity, gate, filesystem)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("contradicts itself" in reason for reason in result["failed_gates"]))

    def test_explicit_integrity_failure_is_fail(self):
        native, process, integrity, gate, filesystem = self.evidence()
        integrity["checks"]["manifest.json"] = False
        integrity["passed"] = False
        result = report.classify_verdict(native, process, integrity, gate, filesystem)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("integrity checks failed" in reason for reason in result["failed_gates"]))

    def test_explicit_post_exit_gate_failure_is_fail(self):
        native, process, integrity, gate, filesystem = self.evidence()
        gate.update(status="FAIL", passed=False, verifier_exit_code=1)
        result = report.classify_verdict(native, process, integrity, gate, filesystem)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("post-exit-result.json explicitly reports failure" in reason
                            for reason in result["failed_gates"]))

    def test_missing_gate_is_incomplete_even_with_historical_native_pass(self):
        native, process, integrity, _gate, filesystem = self.evidence()
        result = report.classify_verdict(native, process, integrity, None, filesystem)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertTrue(any("historical gates are not inferred" in reason
                            for reason in result["incomplete_gates"]))

    def test_parent_exit_mismatch_is_fail(self):
        native, process, integrity, gate, filesystem = self.evidence()
        gate["parent_exit_code"] = 1
        result = report.classify_verdict(native, process, integrity, gate, filesystem)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("does not match process exit_code" in reason
                            for reason in result["failed_gates"]))

    def test_malformed_and_minimal_flags_are_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.json"
            path.write_text("{broken", encoding="utf-8")
            self.assertIsNone(report.read_required(path))
        native, process, integrity, gate, filesystem = self.evidence()
        integrity["checks"] = {}
        gate.pop("parent_exit_code")
        gate.pop("filesystem_passed")
        gate.pop("verifier_exit_code")
        result = report.classify_verdict(native, process, integrity, gate, filesystem)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertTrue(any("nonempty checks" in reason for reason in result["incomplete_gates"]))
        self.assertTrue(any("parent_exit_code" in reason for reason in result["incomplete_gates"]))

    def test_summary_and_html_keep_recorded_verdict_and_gate_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            campaign = Path(tmp)
            run = campaign / "historical"
            op = run / "operator"
            op.mkdir(parents=True)
            (run / "manifest.json").write_text(json.dumps({"workers": 3, "mode": "parallel"}), encoding="utf-8")
            (op / "native-verification.json").write_text(
                json.dumps({"status": "PASS", "passed": True}), encoding="utf-8"
            )
            (op / "process-result.json").write_text(
                json.dumps({"exit_code": 0, "elapsed_s": 1}), encoding="utf-8"
            )
            (op / "integrity-result.json").write_text(
                json.dumps({"passed": True, "checks": {"manifest.json": True}}), encoding="utf-8"
            )
            (op / "post-exit-verification.json").write_text(
                json.dumps({"passed": True}), encoding="utf-8"
            )
            (campaign / "suite-result.json").write_text(
                json.dumps({"cases": [{"name": "historical", "status": "PASS"}]}), encoding="utf-8"
            )

            row = report.summarize(run)
            self.assertEqual(row["status"], "INCOMPLETE")
            self.assertEqual(row["recorded_verdict"], "PASS")
            self.assertTrue(any("post-exit-result.json is missing" in reason
                                for reason in row["acceptance_reasons"]))
            self.assertEqual(Path(row["integrity_report"]), op / "integrity-result.json")
            self.assertEqual(Path(row["post_exit_result_report"]), op / "post-exit-result.json")

            output = campaign / "report.html"
            with patch.object(sys, "argv", ["report.py", "--runs", str(run), "--output", str(output)]):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(report.main(), None)
            body = output.read_text(encoding="utf-8")
            self.assertIn("Recorded verdict: PASS", body)
            self.assertIn("Acceptance:", body)
            self.assertIn("Integrity", body)
            self.assertIn("Exit gate", body)
            self.assertIn("post-exit-result.json is missing", body)


if __name__ == "__main__":
    unittest.main()
