#!/usr/bin/env python3
"""Public CLI boundaries for the opt-in consumer-delivery navigator contract."""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/shiploop"
sys.path.insert(0, str(PACKAGE / "scripts"))
import shiploop_store as store  # noqa: E402


class ConsumerDeliveryCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-consumer-cli-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "product with spaces"
        self.repo.mkdir()
        self.run = self.repo / ".shiploop"

    def cli(self, *args, package=PACKAGE):
        return subprocess.run(
            [sys.executable, str(package / "scripts/shiploop"), *args],
            cwd=self.repo, text=True, capture_output=True, timeout=30,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def init(self, *args, package=PACKAGE):
        return self.cli("init", "--repo", str(self.repo), "--run-dir", str(self.run),
                        "--prompt", "Improve the existing consumer within authority.",
                        *args, package=package)

    def test_opt_in_persists_and_cold_next_does_not_mutate(self):
        result = self.init("--delivery-contract")
        self.assertEqual(result.returncode, 0, result.stderr)
        state_path = self.run / "state.md"
        before = state_path.read_bytes()
        state = store.loads(before.decode())
        self.assertEqual(state["delivery_contract_version"], 1)
        self.assertEqual(state["navigator_protocol_version"], 3)
        recovered = self.cli("next", "--run-dir", str(self.run))
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        self.assertEqual(before, state_path.read_bytes())
        self.assertIn(state["action"]["id"], recovered.stdout)
        self.assertIn("delivery_assessment", recovered.stdout)

    def test_default_run_stays_unmarked_and_cannot_be_retrofitted(self):
        result = self.init()
        self.assertEqual(result.returncode, 0, result.stderr)
        before = (self.run / "state.md").read_bytes()
        self.assertNotIn("delivery_contract_version", store.loads(before.decode()))
        result = self.init("--delivery-contract")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot retrofit", result.stderr)
        self.assertEqual(before, (self.run / "state.md").read_bytes())

    def test_marked_init_without_flag_cannot_remove_recorded_mode(self):
        result = self.init("--delivery-contract")
        self.assertEqual(result.returncode, 0, result.stderr)
        before = (self.run / "state.md").read_bytes()
        result = self.init()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, (self.run / "state.md").read_bytes())

    def test_next_does_not_accept_initialization_flag(self):
        result = self.cli("next", "--run-dir", str(self.run), "--delivery-contract")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.run.exists())

    def test_copied_package_binds_its_own_cli(self):
        copied = Path(self.temp.name) / "relocated package"
        shutil.copytree(PACKAGE, copied, ignore=shutil.ignore_patterns("__pycache__"))
        result = self.init("--delivery-contract", package=copied)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(copied / "scripts/shiploop"), result.stdout)
        self.assertIn(str(self.repo), result.stdout)
        self.assertNotIn(str(PACKAGE / "scripts/shiploop"), result.stdout)


if __name__ == "__main__":
    unittest.main()
