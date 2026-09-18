#!/usr/bin/env python3
"""No-model adversarial checks for the ShipLoop E2E receipt validator."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("shiploop_e2e_grading_under_test", HERE / "grading.py")
assert spec and spec.loader
grading = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grading)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReceiptValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "evidence"
        self.root.mkdir()
        self.trial_id = "ttt-highlight-01"
        self.candidate_digest = "candidate-tree-sha"

    def template(self, checks: list[str], *, baseline_digest: str | None = None) -> dict:
        receipt_path = Path(self.temporary.name) / "receipt.json"
        grading.write_template(
            receipt_path,
            trial_id=self.trial_id,
            candidate_digest=self.candidate_digest,
            required_checks=checks,
            baseline_digest=baseline_digest,
        )
        return json.loads(receipt_path.read_text(encoding="utf-8"))

    def artifact(self, name: str, content: str = "verification output\n") -> dict[str, str]:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"path": path.relative_to(self.root).as_posix(), "sha256": sha256(path)}

    def set_passing_check(self, receipt: dict, check_id: str, artifact: dict[str, str]) -> None:
        for check in receipt["checks"]:
            if check["id"] == check_id:
                check["status"] = "pass"
                check["evidence"] = [artifact]
                return
        self.fail(f"missing check {check_id}")

    def validate(self, receipt: dict, checks: list[str], *, baseline_digest: str | None = None) -> dict:
        return grading.validate_receipt(
            receipt,
            trial_id=self.trial_id,
            candidate_digest=self.candidate_digest,
            required_checks=checks,
            evidence_root=self.root,
            baseline_digest=baseline_digest,
        )

    @staticmethod
    def error_codes(result: dict) -> set[str]:
        return {entry["code"] for entry in result["errors"]}

    def test_template_is_versioned_and_all_unverified(self) -> None:
        destination = Path(self.temporary.name) / "nested" / "verification-receipt.json"
        written = grading.write_template(
            destination,
            trial_id=self.trial_id,
            candidate_digest=self.candidate_digest,
            required_checks=["unit", "browser"],
        )
        self.assertEqual(written, json.loads(destination.read_text(encoding="utf-8")))
        self.assertEqual(written["schema"], grading.RECEIPT_SCHEMA)
        self.assertEqual([check["status"] for check in written["checks"]], ["unverified", "unverified"])
        self.assertEqual(written["incremental_review"]["status"], "unverified")

    def test_valid_artifact_backed_required_checks_pass(self) -> None:
        checks = ["local-tests", "browser-smoke"]
        receipt = self.template(checks)
        self.set_passing_check(receipt, "local-tests", self.artifact("local-tests.log"))
        self.set_passing_check(receipt, "browser-smoke", self.artifact("browser-smoke.log"))

        result = self.validate(receipt, checks)

        self.assertEqual(result["product_status"], "passed")
        self.assertTrue(result["receipt_valid"])
        self.assertTrue(result["all_required_checks_pass"])
        self.assertEqual(result["incremental_status"], "not-applicable")
        self.assertEqual(result["unknown_checks"], [])

    def test_false_green_candidate_binding_is_rejected(self) -> None:
        receipt = self.template(["local-tests"])
        self.set_passing_check(receipt, "local-tests", self.artifact("local-tests.log"))
        receipt["candidate_digest"] = "forged-candidate-tree-sha"

        result = self.validate(receipt, ["local-tests"])

        self.assertEqual(result["product_status"], "error")
        self.assertFalse(result["receipt_valid"])
        self.assertIn("binding_mismatch", self.error_codes(result))

    def test_forged_or_missing_pass_evidence_cannot_go_green(self) -> None:
        for name, artifact, expected_error in (
            ("forged", {"path": "actual.log", "sha256": "0" * 64}, "evidence_digest_mismatch"),
            ("missing", {"path": "gone.log", "sha256": hashlib.sha256(b"gone").hexdigest()}, "missing_evidence"),
        ):
            with self.subTest(name=name):
                receipt = self.template(["local-tests"])
                if name == "forged":
                    self.artifact("actual.log", "actual verification output\n")
                self.set_passing_check(receipt, "local-tests", artifact)

                result = self.validate(receipt, ["local-tests"])

                self.assertEqual(result["product_status"], "error")
                self.assertIn(expected_error, self.error_codes(result))
                self.assertFalse(result["required_checks"]["local-tests"]["valid"])

    def test_duplicate_check_declaration_is_an_error(self) -> None:
        receipt = self.template(["local-tests"])
        self.set_passing_check(receipt, "local-tests", self.artifact("local-tests.log"))
        receipt["checks"].append(copy.deepcopy(receipt["checks"][0]))

        result = self.validate(receipt, ["local-tests"])

        self.assertEqual(result["product_status"], "error")
        self.assertIn("duplicate_check", self.error_codes(result))
        self.assertFalse(result["required_checks"]["local-tests"]["valid"])

    def test_all_unverified_receipt_stays_unverified(self) -> None:
        receipt = self.template(["local-tests", "browser-smoke"])

        result = self.validate(receipt, ["local-tests", "browser-smoke"])

        self.assertEqual(result["product_status"], "unverified")
        self.assertTrue(result["receipt_valid"])
        self.assertEqual(result["incremental_status"], "not-applicable")
        self.assertEqual(
            {reason["code"] for reason in result["unverified_reasons"]},
            {"required_check_not_passed"},
        )

    def test_unknown_extra_check_is_retained_without_blocking_required_passes(self) -> None:
        receipt = self.template(["local-tests"])
        self.set_passing_check(receipt, "local-tests", self.artifact("local-tests.log"))
        receipt["checks"].append({"id": "informational-extra", "status": "unverified", "evidence": []})

        result = self.validate(receipt, ["local-tests"])

        self.assertEqual(result["product_status"], "passed")
        self.assertEqual(result["unknown_checks"], [{"id": "informational-extra", "index": 1, "status": "unverified", "valid": True}])

    def test_symlinked_evidence_is_rejected_even_when_its_digest_matches(self) -> None:
        outside = Path(self.temporary.name) / "outside.log"
        outside.write_text("outside verification output\n", encoding="utf-8")
        link = self.root / "escaped.log"
        try:
            link.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        receipt = self.template(["local-tests"])
        self.set_passing_check(
            receipt,
            "local-tests",
            {"path": "escaped.log", "sha256": sha256(outside)},
        )

        result = self.validate(receipt, ["local-tests"])

        self.assertEqual(result["product_status"], "error")
        self.assertIn("evidence_symlink", self.error_codes(result))

    def test_declared_required_failure_is_preserved(self) -> None:
        checks = ["local-tests", "browser-smoke"]
        receipt = self.template(checks)
        self.set_passing_check(receipt, "local-tests", self.artifact("local-tests.log"))
        for check in receipt["checks"]:
            if check["id"] == "browser-smoke":
                check.update(
                    status="fail",
                    evidence=[self.artifact("browser-smoke-failure.log", "browser smoke failed\n")],
                )

        result = self.validate(receipt, checks)

        self.assertEqual(result["product_status"], "failed")
        self.assertTrue(result["receipt_valid"])
        self.assertEqual(result["required_checks"]["browser-smoke"]["status"], "fail")

    def test_missing_empty_or_forged_failure_evidence_cannot_attribute_failure(self) -> None:
        cases = {
            "missing": (None, "invalid_evidence"),
            "empty": ([], "missing_failure_evidence"),
            "forged": ([{"path": "failure.log", "sha256": "0" * 64}], "evidence_digest_mismatch"),
        }
        for name, (evidence, expected_error) in cases.items():
            with self.subTest(name=name):
                receipt = self.template(["local-tests"])
                if name == "forged":
                    self.artifact("failure.log", "actual failed-check output\n")
                check = receipt["checks"][0]
                check["status"] = "fail"
                if evidence is None:
                    check.pop("evidence")
                else:
                    check["evidence"] = evidence

                result = self.validate(receipt, ["local-tests"])

                self.assertEqual(result["product_status"], "error")
                self.assertFalse(result["receipt_valid"])
                self.assertEqual(result["required_checks"]["local-tests"]["status"], "fail")
                self.assertIn(expected_error, self.error_codes(result))

    def test_incremental_failure_requires_pinned_evidence(self) -> None:
        baseline = "baseline-tree-sha"
        receipt = self.template(["local-tests"], baseline_digest=baseline)
        self.set_passing_check(receipt, "local-tests", self.artifact("local-tests.log"))
        receipt["incremental_review"].update(status="fail", evidence=[])

        invalid = self.validate(receipt, ["local-tests"], baseline_digest=baseline)

        self.assertEqual(invalid["product_status"], "error")
        self.assertFalse(invalid["receipt_valid"])
        self.assertEqual(invalid["incremental_review"]["status"], "fail")
        self.assertEqual(invalid["incremental_status"], "unverified")
        self.assertIn("missing_failure_evidence", self.error_codes(invalid))

        receipt["incremental_review"]["evidence"] = [
            self.artifact("incremental-failure.log", "incremental review failed\n")
        ]
        pinned = self.validate(receipt, ["local-tests"], baseline_digest=baseline)

        self.assertEqual(pinned["product_status"], "failed")
        self.assertTrue(pinned["receipt_valid"])
        self.assertEqual(pinned["incremental_status"], "failed")

    def test_stale_binding_with_declared_failure_is_not_attributed_to_candidate(self) -> None:
        baseline = "baseline-tree-sha"
        receipt = self.template(["local-tests"], baseline_digest=baseline)
        receipt["checks"][0].update(
            status="fail",
            evidence=[self.artifact("local-tests-failure.log", "local tests failed\n")],
        )
        receipt["incremental_review"] = {
            "status": "pass",
            "evidence": [self.artifact("incremental-review.log", "reviewed source preservation\n")],
        }
        receipt["candidate_digest"] = "stale-candidate-tree-sha"

        result = self.validate(receipt, ["local-tests"], baseline_digest=baseline)

        self.assertEqual(result["product_status"], "error")
        self.assertFalse(result["receipt_valid"])
        self.assertEqual(result["required_checks"]["local-tests"]["status"], "fail")
        self.assertEqual(result["incremental_review"]["status"], "pass")
        self.assertEqual(result["incremental_status"], "unverified")
        self.assertIn("binding_mismatch", self.error_codes(result))

    def test_invalid_artifact_with_declared_failure_is_not_attributed_to_candidate(self) -> None:
        checks = ["local-tests", "browser-smoke"]
        receipt = self.template(checks)
        receipt["checks"][0].update(
            status="fail",
            evidence=[self.artifact("local-tests-failure.log", "local tests failed\n")],
        )
        self.artifact("browser-smoke.log", "actual browser output\n")
        self.set_passing_check(
            receipt,
            "browser-smoke",
            {"path": "browser-smoke.log", "sha256": "0" * 64},
        )

        result = self.validate(receipt, checks)

        self.assertEqual(result["product_status"], "error")
        self.assertFalse(result["receipt_valid"])
        self.assertEqual(result["required_checks"]["local-tests"]["status"], "fail")
        self.assertFalse(result["required_checks"]["browser-smoke"]["valid"])
        self.assertIn("evidence_digest_mismatch", self.error_codes(result))

    def test_incremental_requires_exact_baseline_and_passed_external_review(self) -> None:
        baseline = "baseline-tree-sha"
        receipt = self.template(["local-tests"], baseline_digest=baseline)
        self.set_passing_check(receipt, "local-tests", self.artifact("local-tests.log"))

        result = self.validate(receipt, ["local-tests"], baseline_digest=baseline)
        self.assertEqual(result["product_status"], "unverified")
        self.assertEqual(result["incremental_status"], "unverified")

        receipt["incremental_review"] = {
            "status": "pass",
            "evidence": [self.artifact("incremental-review.log", "reviewed source preservation\n")],
        }
        result = self.validate(receipt, ["local-tests"], baseline_digest=baseline)
        self.assertEqual(result["product_status"], "passed")
        self.assertEqual(result["incremental_status"], "passed")

        wrong_baseline = self.validate(receipt, ["local-tests"], baseline_digest="other-baseline-tree-sha")
        self.assertEqual(wrong_baseline["product_status"], "error")
        self.assertIn("binding_mismatch", self.error_codes(wrong_baseline))

    def test_cli_prints_one_json_result_and_nonzero_only_for_nonpass(self) -> None:
        receipt = self.template(["local-tests"])
        self.set_passing_check(receipt, "local-tests", self.artifact("local-tests.log"))
        receipt_path = Path(self.temporary.name) / "receipt.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

        completed = subprocess.run(
            [
                sys.executable,
                str(HERE / "grading.py"),
                "--receipt", str(receipt_path),
                "--trial-id", self.trial_id,
                "--candidate-digest", self.candidate_digest,
                "--required-check", "local-tests",
                "--evidence-root", str(self.root),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["product_status"], "passed")
        self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()
