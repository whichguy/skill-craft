#!/usr/bin/env python3
"""Hermetic checks for the probe-decision fixture corpus."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import fixtures


class ProbeDecisionFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="shiploop-probe-fixture-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_worker_trees_exclude_coordinator_tasks_and_start_clean(self) -> None:
        for family, case in fixtures.CASES.items():
            with self.subTest(family=family):
                fixture = self.root / family
                record = fixtures.materialize(family, fixture)
                self.assertEqual(record["task"], case["task"])
                self.assertTrue((fixture / "scratch").is_dir())
                self.assertFalse((fixture / "scratch" / "probe-log.jsonl").exists())
                tree_text = "\n".join(path.read_text(encoding="utf-8") for path in fixture.rglob("*") if path.is_file())
                self.assertNotIn(case["task"], tree_text)
                self.assertNotIn("required_findings", tree_text)
                self.assertNotIn("forbidden_findings", tree_text)
                if family in {"f1", "f2", "f3"}:
                    self.assertNotIn("bounded observation", case["task"].lower())

    def test_f1_public_receipt_contract_binds_current_evidence(self) -> None:
        fixture = self.root / "contract"
        fixtures.materialize("f1", fixture)
        contract = (fixture / "contracts" / "service-receipt-v1.md").read_text(encoding="utf-8")
        ledger = json.loads((fixture / "evidence" / "ledger-current.json").read_text(encoding="utf-8"))
        self.assertIn("exactly match", contract)
        self.assertEqual(ledger["schema"], "service-read-receipt/v1")
        self.assertEqual(ledger["binding"], {"target": "ledger-current", "role": "export.read"})

    def test_materialize_rejects_unknown_or_nonempty_destinations(self) -> None:
        with self.assertRaises(ValueError):
            fixtures.materialize("unknown", self.root / "unknown")
        destination = self.root / "nonempty"
        destination.mkdir()
        (destination / "keep.txt").write_text("keep", encoding="utf-8")
        with self.assertRaises(ValueError):
            fixtures.materialize("f1", destination)

    def test_f1_probe_logs_under_scratch_only(self) -> None:
        fixture = self.root / "f1"
        fixtures.materialize("f1", fixture)
        completed = subprocess.run(
            [sys.executable, "-B", "capability.py", "read", "--target", "fulfillment-current"],
            cwd=fixture, text=True, capture_output=True, check=True,
        )
        self.assertEqual(json.loads(completed.stdout)["target"], "fulfillment-current")
        log = fixture / "scratch" / "probe-log.jsonl"
        self.assertTrue(log.is_file())
        self.assertFalse((fixture / "probe-log.jsonl").exists())
        self.assertEqual(len(log.read_text(encoding="utf-8").splitlines()), 1)

    def test_public_probe_help_is_available(self) -> None:
        commands = {"f1": "capability.py", "f2": "probe.py", "f3": "probe.py", "f4": "mcp_sim.py"}
        for family, command in commands.items():
            with self.subTest(family=family):
                fixture = self.root / f"help-{family}"
                fixtures.materialize(family, fixture)
                completed = subprocess.run([sys.executable, "-B", command, "--help"], cwd=fixture, text=True, capture_output=True, check=True)
                self.assertIn("usage:", completed.stdout)

    def test_calibration_distinguishes_all_reference_mutant_pairs(self) -> None:
        result = fixtures.calibrate(self.root)
        self.assertTrue(result["passed"], result)
        families = result["families"]
        self.assertEqual(families["f1"]["reference"]["receipt_drift"], ["fulfillment"])
        self.assertEqual(families["f1"]["mutant"]["receipt_drift"], [])
        self.assertEqual(families["f2"]["reference"]["preview"]["status"], "accepted")
        self.assertTrue(families["f2"]["reference"]["write"]["previous_output_preserved"])
        self.assertEqual(families["f2"]["mutant"]["write"]["status"], "ok")
        self.assertTrue(families["f3"]["checks"]["mutant_loses_unicode"])
        self.assertEqual([row["status"] for row in families["f4"]["reference"]["reads"]], ["scope_required", "timeout"])
        self.assertEqual([row["status"] for row in families["f4"]["mutant"]["reads"]], ["ok", "ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
