#!/usr/bin/env python3
"""Run deterministic native-setup-pilot calibrations and CLI boundary checks."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "test" / "fixtures" / "native-setup-pilot"
API_ORACLE = FIXTURE / "api-fixture" / "oracle" / "run_fixture.py"
READINESS_CALIBRATION = FIXTURE / "readiness_calibration.py"
ADAPTER = FIXTURE / "native_slice.py"


class NativeSetupPilotTests(unittest.TestCase):
    def run_python(self, *args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", *args],
            cwd=cwd,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )

    def clean_harness_clone(self, destination: Path) -> tuple[Path, str]:
        cloned = subprocess.run(
            ["git", "clone", "--quiet", "--shared", str(ROOT), str(destination)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(cloned.returncode, 0, cloned.stderr)
        head = subprocess.run(
            ["git", "-C", str(destination), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(destination), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout
        self.assertEqual(status, "")
        return destination, head

    def test_api_oracle_calibrates_reference_mutants_invalid_and_classification_controls(self) -> None:
        with tempfile.TemporaryDirectory(prefix="native-setup-api-calibration-") as temp:
            output = Path(temp) / "api-calibration.json"
            result = self.run_python(str(API_ORACLE), "--calibrate", "--output", str(output))
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            receipt = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(receipt["valid"], result.stdout)

    def test_typed_boundary_examples_pass_both_correct_implementations(self) -> None:
        with tempfile.TemporaryDirectory(prefix="native-setup-typed-boundaries-") as temp:
            output = Path(temp) / "typed-boundaries.json"
            examples = FIXTURE / "api-fixture" / "oracle" / "suite-controls" / "typed_boundary_examples.py"
            result = self.run_python(
                str(API_ORACLE), "--tests", str(examples),
                "--candidates", "correct,alternative", "--output", str(output),
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            receipt = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(receipt["suite_valid"])
            self.assertEqual(set(receipt["results"]), {"correct", "alternative"})
            for candidate in receipt["results"].values():
                self.assertEqual(candidate["classification"], "PASS")
                self.assertEqual(candidate["tests"], 4)

    def test_readiness_fixture_calibrates_local_authority_and_journey_behavior(self) -> None:
        with tempfile.TemporaryDirectory(prefix="native-setup-readiness-calibration-") as temp:
            output = Path(temp) / "readiness-calibration.json"
            result = self.run_python(
                str(READINESS_CALIBRATION),
                "--fixture", str(FIXTURE / "readiness-fixture"),
                "--seed-state", str(FIXTURE / "readiness-state"),
                "--output", str(output),
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            receipt = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(receipt["valid"], result.stdout)

    def test_adapter_forwarding_contract(self) -> None:
        result = self.run_python(str(FIXTURE / "test_native_slice.py"), cwd=FIXTURE)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_dirty_harness_rejected_before_output_or_host_activity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="native-setup-dirty-harness-") as temp:
            harness, actual_head = self.clean_harness_clone(Path(temp) / "harness")
            adjacent = harness / "test" / "shiploop_e2e" / "native_setup_pilot_dirty_probe.py"
            adjacent.write_text("# adjacent untracked input\n", encoding="utf-8")
            output = Path(temp) / "must-not-be-created"
            host_marker = Path(temp) / "host-started"
            host_stub = Path(temp) / "codex-stub"
            host_stub.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                f"Path({str(host_marker)!r}).touch()\n"
                "raise SystemExit(17)\n",
                encoding="utf-8",
            )
            host_stub.chmod(0o755)
            result = self.run_python(
                str(ADAPTER),
                "--harness-root", str(harness),
                "--expected-head", actual_head,
                "--case-catalog", str(FIXTURE / "cases.json"),
                "--fixture-root", str(FIXTURE),
                "--case", "readiness-plan",
                "--seed-at", "test-strategy",
                "--stop-after", "plan",
                "--host", "codex",
                "--codex-bin", str(host_stub),
                "--output", str(output),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must be clean", result.stderr)
            self.assertFalse(output.exists())
            self.assertFalse(host_marker.exists())

    def test_outer_stage_seed_without_stop_fails_before_output_or_host_start(self) -> None:
        with tempfile.TemporaryDirectory(prefix="native-setup-invalid-seed-") as temp:
            harness, actual_head = self.clean_harness_clone(Path(temp) / "harness")
            output = Path(temp) / "must-not-be-created"
            host_stub = Path(temp) / "codex-stub"
            host_stub.write_text("#!/bin/sh\nexit 17\n", encoding="utf-8")
            host_stub.chmod(0o755)
            result = self.run_python(
                str(ADAPTER),
                "--harness-root", str(harness),
                "--expected-head", actual_head,
                "--case-catalog", str(FIXTURE / "cases.json"),
                "--fixture-root", str(FIXTURE),
                "--case", "readiness-plan",
                "--seed-at", "test-strategy",
                "--host", "codex",
                "--codex-bin", str(host_stub),
                "--output", str(output),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--stop-after", result.stderr)
            self.assertFalse(output.exists())

    def test_adapter_reaches_frozen_slice_help_and_rejects_a_wrong_head(self) -> None:
        with tempfile.TemporaryDirectory(prefix="native-setup-help-") as temp:
            harness, actual_head = self.clean_harness_clone(Path(temp) / "harness")
            adapter_args = [
                "--harness-root", str(harness),
                "--expected-head", actual_head,
                "--case-catalog", str(FIXTURE / "cases.json"),
                "--fixture-root", str(FIXTURE),
                "--help",
            ]
            help_result = self.run_python(str(ADAPTER), *adapter_args)
            self.assertEqual(help_result.returncode, 0, help_result.stderr)
            for option in ("usage:", "--case CASE", "--model MODEL", "--effort EFFORT"):
                self.assertIn(option, help_result.stdout)

            wrong_head_args = [*adapter_args]
            wrong_head_args[wrong_head_args.index(actual_head)] = "0" * 40
            wrong_head = self.run_python(str(ADAPTER), *wrong_head_args)
            self.assertNotEqual(wrong_head.returncode, 0)
            self.assertIn("expected", wrong_head.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
