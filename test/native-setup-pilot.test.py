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
            typed_mutants = (
                "typed-mutant:typed_record_id_extraction",
                "typed-mutant:typed_expected_version_coercion",
                "typed-mutant:typed_idempotency_key_stringification",
                "typed-mutant:typed_changes_pair_list_conversion",
            )
            candidates = ("correct", "alternative", *typed_mutants)
            candidate_arg = ",".join(candidates)
            result = self.run_python(
                str(API_ORACLE), "--tests", str(examples),
                "--candidates", candidate_arg, "--output", str(output),
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            receipt = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(receipt["suite_valid"])
            self.assertEqual(set(receipt["results"]), set(candidates))
            self.assertEqual(set(receipt["typed_mutant_requirements"]), {
                name.split(":", 1)[1] for name in typed_mutants
            })
            typed_failure_tests = {
                "typed-mutant:typed_record_id_extraction":
                    "test_non_string_record_id_is_rejected_without_mutation",
                "typed-mutant:typed_expected_version_coercion":
                    "test_non_integer_version_is_rejected_without_mutation",
                "typed-mutant:typed_idempotency_key_stringification":
                    "test_non_string_key_is_rejected_without_mutation",
                "typed-mutant:typed_changes_pair_list_conversion":
                    "test_non_dict_changes_are_rejected_without_mutation",
            }
            for name in ("correct", "alternative"):
                self.assertEqual(receipt["results"][name]["classification"], "PASS")
                self.assertEqual(receipt["results"][name]["tests"], 4)
            for name in typed_mutants:
                mutant = receipt["results"][name]
                self.assertEqual(mutant["classification"], "KILLED")
                self.assertEqual(mutant["tests"], 4)
                failure_tests = {
                    failure["test"].split(" (", 1)[0].rsplit(".", 1)[-1]
                    for failure in mutant["failures"]
                }
                self.assertEqual(failure_tests, {typed_failure_tests[name]}, name)

            for label, tests in (
                ("reference", FIXTURE / "api-fixture" / "oracle" / "reference_tests.py"),
                ("existing", FIXTURE / "api-fixture" / "subject" / "test_existing.py"),
            ):
                suite_output = Path(temp) / f"typed-{label}.json"
                suite_result = self.run_python(
                    str(API_ORACLE), "--tests", str(tests),
                    "--candidates", candidate_arg, "--output", str(suite_output),
                )
                self.assertEqual(suite_result.returncode, 0, suite_result.stderr or suite_result.stdout)
                suite_receipt = json.loads(suite_output.read_text(encoding="utf-8"))
                self.assertTrue(suite_receipt["suite_valid"], label)
                for name in ("correct", "alternative"):
                    self.assertEqual(suite_receipt["results"][name]["classification"], "PASS", label)
                for name in typed_mutants:
                    self.assertIn(
                        suite_receipt["results"][name]["classification"],
                        {"KILLED", "SURVIVED"},
                        f"{label}: {name}",
                    )

            error_output = Path(temp) / "typed-error-control.json"
            error_tests = Path(temp) / "typed-invalid-probe.py"
            error_tests.write_text(
                "\n".join([
                    "import unittest",
                    "import change_app",
                    "",
                    "class InvalidTypedCandidateProbe(unittest.TestCase):",
                    "    def test_unexpected_acceptance_is_an_error(self):",
                    "        change_app.fixture_seed()",
                    "        common = {",
                    '            "actor": "alice",',
                    '            "record_id": "demo-1",',
                    '            "expected_version": 1,',
                    '            "changes": {"amount": 25},',
                    '            "idempotency_key": "typed-invalid-probe",',
                    "        }",
                    "        invalid_values = (",
                    '            ("record_id", {"id": "demo-1"}),',
                    '            ("expected_version", "1"),',
                    '            ("idempotency_key", 7),',
                    '            ("changes", [("amount", 25)]),',
                    "        )",
                    "        for parameter, value in invalid_values:",
                    "            arguments = dict(common)",
                    "            arguments[parameter] = value",
                    "            result = change_app.propose_change(**arguments)",
                    "            if result.get(\"ok\") is True:",
                    "                raise RuntimeError(f\"accepted invalid {parameter}\")",
                ]) + "\n",
                encoding="utf-8",
            )
            error_result = self.run_python(
                str(API_ORACLE), "--tests", str(error_tests),
                "--candidates", candidate_arg, "--output", str(error_output),
            )
            self.assertEqual(error_result.returncode, 0, error_result.stderr or error_result.stdout)
            error_receipt = json.loads(error_output.read_text(encoding="utf-8"))
            self.assertTrue(error_receipt["suite_valid"])
            for name in ("correct", "alternative"):
                self.assertEqual(error_receipt["results"][name]["classification"], "PASS")
            for name in typed_mutants:
                self.assertEqual(error_receipt["results"][name]["classification"], "INVALID")
                self.assertEqual(error_receipt["results"][name]["status"], "invalid")
                self.assertNotEqual(error_receipt["results"][name]["classification"], "KILLED")

    def test_recovery_fixture_discriminates_stale_setup_and_false_success(self) -> None:
        with tempfile.TemporaryDirectory(prefix="native-setup-recovery-calibration-") as temp:
            recovery = FIXTURE / "recovery"
            output = Path(temp) / "recovery-calibration"
            result = self.run_python(
                str(recovery / "operator" / "recovery_calibrate.py"),
                "--corpus-root", str(recovery / "corpus-v1"),
                "--input-manifest", str(recovery / "input-manifest.json"),
                "--output-dir", str(output),
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            receipt = json.loads(
                (output / "calibration-result.json").read_text(encoding="utf-8")
            )
            self.assertTrue(receipt["pass"], result.stdout)
            self.assertEqual(receipt["check_count"], 17)
            self.assertEqual(receipt["passed_check_count"], 17)
            self.assertEqual(receipt["expected_control_count"], 10)
            self.assertEqual(receipt["model_calls"], 0)
            controls = receipt["controls"]
            self.assertTrue(controls["stale_target_control_rejected_without_test_setup"])
            self.assertTrue(controls["completion_before_setup_rejected"])

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
