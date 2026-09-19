"""Bounded runtime calibrations for Python coding-guidance claims.

These tests compare a reference implementation with intentionally plausible
mutants.  A passing suite means the assertions discriminate the stated cases;
it does not establish a general coding-agent treatment effect.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import ModuleType


ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures" / "python"
CHILD_SOURCE = FIXTURES / "child.py"
LEDGER_DRIVER = FIXTURES / "ledger_driver.py"


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"fixture_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load fixture: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def call_child(module: ModuleType, child: Path, audit: Path, mode: str) -> dict[str, object]:
    try:
        value = module.run_child(child, audit, mode)
    except subprocess.CalledProcessError as error:
        return {
            "kind": "CalledProcessError",
            "returncode": error.returncode,
            "stderr": error.stderr.strip(),
        }
    except Exception as error:  # The masking-cleanup mutant is expected here.
        return {"kind": type(error).__name__, "message": str(error)}
    return {"kind": "return", "value": value}


class SubprocessGuidanceTests(unittest.TestCase):
    def run_fixture(self, fixture_name: str, mode: str) -> tuple[dict[str, object], Path]:
        fixture = load_module(FIXTURES / fixture_name)
        with tempfile.TemporaryDirectory(prefix="shiploop-python-guidance-") as temporary:
            temporary_path = Path(temporary)
            child = temporary_path / "child program.py"
            shutil.copyfile(CHILD_SOURCE, child)
            audit = temporary_path / "workspace-audit.txt"
            outcome = call_child(fixture, child, audit, mode)
            workspace = Path(audit.read_text(encoding="utf-8"))
            self.assertFalse(workspace.exists(), f"{fixture_name} left its workspace behind")
            return outcome, workspace

    def test_reference_preserves_child_cause_and_cleans_up(self) -> None:
        outcome, _ = self.run_fixture("subprocess_reference.py", "fail")
        self.assertEqual(
            outcome,
            {
                "kind": "CalledProcessError",
                "returncode": 17,
                "stderr": "root-cause: fixture child failed",
            },
        )

    def test_failure_path_discriminates_swallow_masking_and_string_command_mutants(self) -> None:
        expected = {
            "kind": "CalledProcessError",
            "returncode": 17,
            "stderr": "root-cause: fixture child failed",
        }
        swallow, _ = self.run_fixture("subprocess_swallow_mutant.py", "fail")
        masking, _ = self.run_fixture("subprocess_masking_cleanup_mutant.py", "fail")
        string_command, _ = self.run_fixture("subprocess_string_command_mutant.py", "fail")
        self.assertNotEqual(swallow, expected)
        self.assertEqual(swallow["kind"], "return")
        self.assertNotEqual(masking, expected)
        self.assertEqual(masking, {"kind": "RuntimeError", "message": "cleanup telemetry failed"})
        self.assertNotEqual(string_command, expected)
        self.assertEqual(string_command["kind"], "CalledProcessError")
        self.assertEqual(string_command["returncode"], 2)

    def test_success_only_is_a_negative_control(self) -> None:
        expected = {"kind": "return", "value": "child-ok"}
        for fixture_name in (
            "subprocess_reference.py",
            "subprocess_swallow_mutant.py",
            "subprocess_masking_cleanup_mutant.py",
        ):
            with self.subTest(fixture=fixture_name):
                outcome, _ = self.run_fixture(fixture_name, "ok")
                self.assertEqual(outcome, expected)


class StateGuidanceTests(unittest.TestCase):
    def run_ledger(self, fixture_name: str) -> dict[str, object]:
        completed = subprocess.run(
            [sys.executable, "-B", str(LEDGER_DRIVER), str(FIXTURES / fixture_name)],
            check=True,
            text=True,
            capture_output=True,
        )
        return json.loads(completed.stdout)

    def test_reference_has_isolated_state_and_preserves_rejected_transitions(self) -> None:
        result = self.run_ledger("ledger_reference.py")
        self.assertEqual(
            result,
            {
                "basic_credit_result": 7,
                "second_instance_isolated": True,
                "rejected_transition_preserved_state": True,
                "trace_failures": [],
            },
        )

    def test_invariant_assertions_distinguish_shared_and_partial_commit_mutants(self) -> None:
        shared = self.run_ledger("ledger_shared_state_mutant.py")
        partial = self.run_ledger("ledger_partial_commit_mutant.py")
        self.assertFalse(shared["second_instance_isolated"])
        self.assertTrue(shared["rejected_transition_preserved_state"])
        self.assertEqual(shared["trace_failures"], [])
        self.assertTrue(partial["second_instance_isolated"])
        self.assertFalse(partial["rejected_transition_preserved_state"])
        self.assertTrue(partial["trace_failures"])
        self.assertIn("rejected transition changed state", "\n".join(partial["trace_failures"]))

    def test_basic_credit_is_a_negative_control(self) -> None:
        for fixture_name in (
            "ledger_reference.py",
            "ledger_shared_state_mutant.py",
            "ledger_partial_commit_mutant.py",
        ):
            with self.subTest(fixture=fixture_name):
                self.assertEqual(self.run_ledger(fixture_name)["basic_credit_result"], 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
