#!/usr/bin/env python3
"""Calibrate the independent quality gate; no model, org or browser calls."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "test/shiploop_e2e/checks/grok_chat_full_quality.py"
spec = importlib.util.spec_from_file_location("grok_quality", PATH)
quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)


class QualityGateTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.product = self.base / "work"
        self.product.mkdir()
        self.platform = self.base / "platform"
        self.platform.mkdir()
        subprocess.run(["git", "-C", str(self.product), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(self.product), "-c", "user.name=Fixture",
                        "-c", "user.email=fixture@example.invalid", "commit", "--allow-empty", "-qm", "fixture"], check=True)
        (self.product / "force-app").mkdir()
        (self.product / "sfdx-project.json").write_text('{"packageDirectories":[{"path":"force-app"}]}\n')
        (self.product / "force-app/Example.cls").write_text("public class Example {}\n")
        self.identity = quality.snapshot(self.product)
        self.directory = self.platform / "grok-chat-quality" / self.identity["sha256"]
        self.directory.mkdir(parents=True)

    def valid(self):
        raw = b"Independent review performed against the registered source.\n"
        (self.directory / "review-evidence.txt").write_bytes(raw)
        return {
            "schema": "shiploop-grok-chat-quality-review/1", "status": "PASS",
            "source_sha256": self.identity["sha256"],
            "reviewer": {"independent": True, "actor": "fixture-reviewer",
                         "execution_id": "fixture-review", "provenance": "calibration fixture"},
            "dimensions": {key: {"status": "PASS", "reason": "Fixture evidence"} for key in quality.DIMENSIONS},
            "findings": [],
            "evidence": [{"path": "review-evidence.txt", "sha256": hashlib.sha256(raw).hexdigest()}],
        }

    def test_accepts_complete_review_and_reuses_same_source(self):
        (self.directory / "review.json").write_text(json.dumps(self.valid()))
        self.assertEqual(quality.run(self.product, self.platform, "builder", wait_seconds=0), 0)
        self.assertEqual(quality.run(self.product, self.platform, "final", wait_seconds=0), 0)

    def test_missing_review_is_incomplete_and_retains_request(self):
        self.assertEqual(quality.run(self.product, self.platform, "builder", wait_seconds=0), 2)
        request = json.loads((self.directory / "request.json").read_text())
        self.assertEqual(request["source"]["sha256"], self.identity["sha256"])

    def test_required_dimensions_and_independent_identity_cannot_be_omitted(self):
        for key in quality.DIMENSIONS:
            review = self.valid()
            del review["dimensions"][key]
            self.assertIn("review-dimensions-incomplete", quality.validate_review(review, self.identity, self.directory))
        review = self.valid()
        review["reviewer"]["independent"] = False
        self.assertIn("independent-reviewer-missing", quality.validate_review(review, self.identity, self.directory))
        for key in ("actor", "execution_id", "provenance"):
            review = self.valid()
            del review["reviewer"][key]
            self.assertIn("independent-reviewer-missing", quality.validate_review(review, self.identity, self.directory))

    def test_ignored_deployable_source_is_included_and_changes_review_identity(self):
        (self.product / ".gitignore").write_text("force-app/Ignored.cls\n")
        before = quality.snapshot(self.product)
        ignored = self.product / "force-app/Ignored.cls"
        ignored.write_text("public class Ignored {}\n")
        after = quality.snapshot(self.product)
        self.assertNotEqual(before["sha256"], after["sha256"])
        self.assertIn("force-app/Ignored.cls", [row["path"] for row in after["files"]])

    def test_symbolic_deployable_source_is_refused(self):
        (self.product / "force-app/Alias").symlink_to(self.platform, target_is_directory=True)
        with self.assertRaises(ValueError):
            quality.snapshot(self.product)

    def test_wrong_source_unknown_status_and_active_findings_fail(self):
        changes = (
            ("source_sha256", "0" * 64, "review-source-mismatch"),
            ("status", "UNKNOWN", "review-not-passed"),
            ("findings", [{"actionable": True, "message": "Missing authorization check"}], "actionable-findings-remain"),
        )
        for field, value, reason in changes:
            review = self.valid()
            review[field] = value
            self.assertIn(reason, quality.validate_review(review, self.identity, self.directory))

    def test_missing_tampered_and_escaping_evidence_fail(self):
        for kind in ("missing", "tampered", "escaping"):
            review = self.valid()
            if kind == "missing":
                (self.directory / "review-evidence.txt").unlink()
            elif kind == "tampered":
                (self.directory / "review-evidence.txt").write_text("Different evidence")
            else:
                review["evidence"][0]["path"] = "../../outside.txt"
            self.assertIn("review-evidence-invalid", quality.validate_review(review, self.identity, self.directory))

    def test_source_mutation_during_review_invalidates_result(self):
        (self.directory / "review.json").write_text(json.dumps(self.valid()))
        changed = dict(self.identity, sha256="1" * 64)
        with mock.patch.object(quality, "snapshot", side_effect=[self.identity, changed]):
            self.assertEqual(quality.run(self.product, self.platform, "final", wait_seconds=0), 1)

    def test_unsupported_phase_stops_before_candidate_or_platform_activity(self):
        with mock.patch.object(quality, "snapshot", side_effect=AssertionError("must not inspect")):
            for phase in ("unknown", "product_at_stop", "review"):
                self.assertEqual(quality.run(self.product, self.platform, phase, wait_seconds=0), 2)

    def test_candidate_outside_run_is_refused(self):
        with tempfile.TemporaryDirectory() as other:
            self.assertEqual(quality.run(Path(other), self.platform, "builder", wait_seconds=0), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
