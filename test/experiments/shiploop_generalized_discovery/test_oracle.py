#!/usr/bin/env python3
"""Focused no-model regression checks for the generalized discovery oracle."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("generic_oracle_under_test", HERE / "oracle.py")
assert spec and spec.loader
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
init_spec = importlib.util.spec_from_file_location("generic_initializer_under_test", HERE / "initialize.py")
assert init_spec and init_spec.loader
initializer = importlib.util.module_from_spec(init_spec)
init_spec.loader.exec_module(initializer)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class OracleCalibrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.calibration = oracle.calibrate(HERE / "fixtures.py", HERE / "PUBLIC_CONTRACTS.md")

    def test_calibrates_each_reference_and_changed_observation_without_correctness_claim(self) -> None:
        self.assertTrue(self.calibration["passed"])
        self.assertIn("do not establish universal correctness", self.calibration["interpretation"])
        self.assertEqual(set(self.calibration["families"]), {"f1", "f2", "f3", "f4"})
        for family in self.calibration["families"].values():
            self.assertTrue(family["reference"]["passed"])
            self.assertTrue(family["altered_variant"]["changed_observation_detected"])

    def test_calibration_hashes_materialized_sources_before_probe_pycache(self) -> None:
        for family in self.calibration["families"].values():
            for variant in ("reference", "altered_variant"):
                self.assertNotIn("__pycache__", " ".join(family[variant]["file_hashes"]))


class OracleReceiptAndCompletionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.calibration = oracle.calibrate(HERE / "fixtures.py", HERE / "PUBLIC_CONTRACTS.md")

    def _populate_arm(self, study: Path, context: dict[str, object], receipts: list[dict[str, object]] | None = None) -> Path:
        arm, workspace, run = study / "arms" / "arm", study / "arms" / "arm" / "workspace", study / "arms" / "arm" / "run"
        workspace.mkdir(parents=True)
        (workspace / "fixture.txt").write_text("fixture\n", encoding="utf-8")
        (workspace / "REPORT.md").write_text("A report exists but does not prove execution success.\n", encoding="utf-8")
        digest = hashlib.sha256((workspace / "fixture.txt").read_bytes()).hexdigest()
        hashes = {"fixture.txt": digest}
        write_json(arm / "input-hashes.json", hashes)
        write_json(run / "input-hashes-pre.json", hashes)
        write_json(run / "input-hashes-post.json", hashes)
        write_json(run / "metadata.json", {"contexts": [context], "report": {"valid_task_required_report": True}, "fixture_edits": {}, "fixture_edits_flagged": False})
        if not (study / "study.json").is_file():
            write_json(study / "study.json", {"arms": {"arm": {"family": "f1"}}})
        else:
            state = json.loads((study / "study.json").read_text(encoding="utf-8"))
            state.setdefault("arms", {})["arm"] = {"family": "f1"}
            write_json(study / "study.json", state)
        if not (study / "private" / "oracle-calibration.json").is_file():
            write_json(study / "private" / "oracle-calibration.json", self.calibration)
        if receipts is not None:
            (study / "receipts.jsonl").write_text("".join(json.dumps(value) + "\n" for value in receipts), encoding="utf-8")
        return study

    def _study(self, temporary: str, context: dict[str, object], receipts: list[dict[str, object]] | None = None) -> Path:
        return self._populate_arm(Path(temporary), context, receipts)

    def _initialized_study(self, temporary: str, context: dict[str, object], receipts: list[dict[str, object]]) -> Path:
        root = Path(temporary)
        candidate, plan, study = root / "candidate.md", root / "plan.md", root / "study"
        candidate.write_text("# Candidate\n", encoding="utf-8")
        plan.write_text("# Plan\n", encoding="utf-8")
        initialized = initializer.initialize(study, candidate, plan)
        self.assertEqual(initialized["status"], "ready_to_prepare")
        return self._populate_arm(study, context, receipts)

    def test_receipt_recognizes_only_documented_python_probe_forms(self) -> None:
        expected = self.calibration["families"]["f1"]["reference"]["observations"]
        payload = expected["dependency"]["json"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipt = root / "receipts.jsonl"
            lines = [
                {"arm": "arm", "event": "workspace_call", "request": {"arguments": {"operation": "exec", "argv": ["/bin/cat", "probe.py", "dependency"]}}, "result": {"exit_code": 0, "stdout": json.dumps(payload)}, "is_error": False},
                {"arm": "arm", "event": "workspace_call", "request": {"arguments": {"operation": "exec", "argv": [sys.executable, "-B", "./probe.py", "dependency"]}}, "result": {"exit_code": 0, "stdout": json.dumps(payload)}, "is_error": False},
            ]
            receipt.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
            result = oracle._receipt_probes(receipt, "arm", "f1", expected, root)
        self.assertEqual([item["command"] for item in result["observed"]], ["dependency"])
        self.assertTrue(result["observed"][0]["matches_calibration"])
        self.assertEqual(result["unrecognized_execs"][0]["classification"], "unrecognized_exec_not_scored")
        self.assertTrue(result["receipt_evidence_ok"])

    def test_report_does_not_mask_missing_receipts_or_runtime_failure(self) -> None:
        context = {"exit_code": 7, "termination_reason": "hard_deadline", "elapsed_seconds": 1.25, "final_present": True}
        with tempfile.TemporaryDirectory() as temporary:
            result = oracle.grade_arm(self._study(temporary, context), "arm")
        self.assertTrue(result["completion"]["report_present"])
        self.assertEqual(result["completion"]["runtime"]["exit_code"], 7)
        self.assertEqual(result["completion"]["runtime"]["termination_reason"], "hard_deadline")
        self.assertEqual(result["completion"]["runtime"]["elapsed_seconds"], 1.25)
        self.assertFalse(result["completion"]["runtime"]["successful"])
        self.assertFalse(result["coordinator_receipts"]["available"])
        self.assertFalse(result["deterministic_evidence_ready"])

    def test_probe_execution_error_is_not_deterministic_success(self) -> None:
        context = {"exit_code": 0, "termination_reason": None, "elapsed_seconds": 0.5, "final_present": True}
        receipt = {"arm": "arm", "event": "workspace_call", "request": {"arguments": {"operation": "exec", "argv": [sys.executable, "probe.py", "dependency"]}}, "result": {"exit_code": 1, "stdout": ""}, "is_error": True}
        with tempfile.TemporaryDirectory() as temporary:
            result = oracle.grade_arm(self._study(temporary, context, [receipt]), "arm")
        self.assertTrue(result["completion"]["runtime"]["successful"])
        self.assertFalse(result["coordinator_receipts"]["receipt_evidence_ok"])
        self.assertIn("line_1: probe_execution_error", result["coordinator_receipts"]["errors"])
        self.assertFalse(result["deterministic_evidence_ready"])

    def test_mismatched_probe_receipt_is_an_evidence_failure(self) -> None:
        expected = self.calibration["families"]["f1"]["reference"]["observations"]
        payload = dict(expected["dependency"]["json"], active_parser_version="not-calibrated")
        receipt = {"arm": "arm", "event": "workspace_call", "request": {"arguments": {"operation": "exec", "argv": [sys.executable, "probe.py", "dependency"]}}, "result": {"exit_code": 0, "stdout": json.dumps(payload)}, "is_error": False}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipts = root / "receipts.jsonl"
            receipts.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
            result = oracle._receipt_probes(receipts, "arm", "f1", expected, root)
        self.assertFalse(result["receipt_evidence_ok"])
        self.assertIn("line_1: probe_output_mismatch", result["errors"])

    def test_missing_arm_evidence_or_calibration_cannot_be_ready(self) -> None:
        context = {"exit_code": 0, "termination_reason": None, "elapsed_seconds": 0.5, "final_present": True}
        read = {"arm": "arm", "event": "workspace_call", "request": {"arguments": {"operation": "read", "path": "fixture.txt"}}, "result": {"text": "fixture\n"}}
        for missing in ("receipt", "calibration", "report", "source_manifest"):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as temporary:
                study = self._initialized_study(temporary, context, [read])
                self.assertTrue(oracle.grade_arm(study, "arm")["deterministic_evidence_ready"])
                if missing == "receipt":
                    (study / "receipts.jsonl").write_text("")
                elif missing == "calibration":
                    (study / "private/oracle-calibration.json").unlink()
                elif missing == "report":
                    (study / "arms/arm/workspace/REPORT.md").unlink()
                else:
                    write_json(study / "arms/arm/input-hashes.json", {})
                    write_json(study / "arms/arm/run/input-hashes-pre.json", {})
                    write_json(study / "arms/arm/run/input-hashes-post.json", {})
                self.assertFalse(oracle.grade_arm(study, "arm")["deterministic_evidence_ready"])

    def test_invalid_frozen_inputs_return_a_diagnostic_without_crashing(self) -> None:
        context = {"exit_code": 0, "termination_reason": None, "elapsed_seconds": 0.5, "final_present": True}
        read = {"arm": "arm", "event": "workspace_call", "request": {"arguments": {"operation": "read", "path": "fixture.txt"}}, "result": {"text": "fixture\n"}}
        with tempfile.TemporaryDirectory() as temporary:
            study = self._initialized_study(temporary, context, [read])
            (study / "frozen" / "fixtures.py").write_text("tampered\n", encoding="utf-8")
            result = oracle.grade_arm(study, "arm")
        self.assertFalse(result["frozen_input_validation"]["passed"])
        self.assertIn("input_validation_error", result["frozen_input_validation"])
        self.assertFalse(result["deterministic_evidence_ready"])

    def test_grade_cli_returns_nonzero_when_evidence_is_not_ready(self) -> None:
        context = {"exit_code": 0, "termination_reason": None, "elapsed_seconds": 0.5, "final_present": True}
        with tempfile.TemporaryDirectory() as temporary:
            study = self._study(temporary, context)
            output = Path(temporary) / "grade.json"
            completed = subprocess.run([sys.executable, str(HERE / "oracle.py"), "--study", str(study), "--arm", "arm", "--output", str(output)], text=True, capture_output=True, check=False)
            result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(completed.returncode, 2)
        self.assertFalse(result["deterministic_evidence_ready"])


if __name__ == "__main__":
    unittest.main()
