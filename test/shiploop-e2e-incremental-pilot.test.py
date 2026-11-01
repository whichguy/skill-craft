#!/usr/bin/env python3
"""Hermetic calibration and checkpoint tests for the incremental CSV pilot."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "docs/experiments/incremental-feature-chain-20261101"
sys.path.insert(0, str(PILOT))


class CalibrationTest(unittest.TestCase):
    def test_frozen_behavior_matrix_and_source_mapping(self):
        done = subprocess.run(
            [sys.executable, "-B", str(PILOT / "calibrate_checks.py")],
            cwd=ROOT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True, capture_output=True, timeout=900,
        )
        self.assertEqual(done.returncode, 0, (done.stderr + done.stdout)[-8000:])
        result = json.loads(done.stdout)
        self.assertEqual(result["live_model_calls"], 0)
        self.assertTrue(result["summary"]["all_expectations_matched"])
        self.assertEqual(result["summary"]["matched"], result["summary"]["cells"])
        self.assertTrue(result["source_map_coverage"]["all_conditions_mapped"])


def load_tests(loader, tests, pattern):
    spec = importlib.util.spec_from_file_location("incremental_checkpoint_tests", PILOT / "test_checkpoint.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    tests.addTests(loader.loadTestsFromModule(module))
    return tests


if __name__ == "__main__":
    unittest.main()
