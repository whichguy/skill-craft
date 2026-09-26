"""No-model suite selection is explicit and cannot route into the live runner."""
import json
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import check_suite
import layout


class CheckSuiteTests(unittest.TestCase):
    def test_all_includes_every_apparatus_test_exactly_once(self):
        selected = check_suite.selected("all")
        self.assertEqual(len(selected), len(set(selected)))
        self.assertEqual(set(selected), {p.stem for p in check_suite.HERE.glob("test_*.py")})
        self.assertNotIn("run", selected)

    def test_short_workflow_suite_lists_without_running_tests(self):
        result = subprocess.run([sys.executable, "-B", str(Path(check_suite.__file__)), "--suite", "workflow", "--list",
                                 "--skill-root", str(layout.selected_skill_root())],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        row = json.loads(result.stdout)
        self.assertEqual(row["model_calls"], 0)
        self.assertEqual(row["modules"], ["test_campaign", "test_recovery_isolation", "test_workflow_review"])
        self.assertEqual(row["selected_subject"]["selection"], "explicit")
        self.assertIn(row["selected_subject"]["default_selection"], {"source-sibling", "installed-skill-dir"})

    def test_relative_output_receipt_binds_the_explicit_subject(self):
        subject = layout.selected_skill_root()
        with tempfile.TemporaryDirectory(prefix="shiploop-e2e-check-suite-") as temporary:
            result = subprocess.run(
                [sys.executable, "-B", str(Path(check_suite.__file__)), "--suite", "mock",
                 "--output", "relative-receipt", "--skill-root", str(subject)],
                cwd=temporary, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads((Path(temporary) / "relative-receipt" / "result.json").read_text())
        self.assertEqual(receipt["harness"]["root"], str(check_suite.HERE))
        self.assertEqual(receipt["selected_subject"]["root"], str(subject.resolve()))
        self.assertEqual(receipt["selected_subject"]["selection"], "explicit")
        self.assertEqual(receipt["model_calls"], 0)

    def test_output_guard_rejects_selected_subject_before_any_write(self):
        with tempfile.TemporaryDirectory(prefix="shiploop-e2e-check-guard-") as temporary:
            subject = Path(temporary) / "subject"
            subject.mkdir()
            target = subject / "forbidden-output"
            with self.assertRaisesRegex(ValueError, "outside the audit package"):
                layout.validate_new_external_output(target, subject_root=subject)
            self.assertFalse(target.exists())

    def test_git_repository_with_a_copied_package_does_not_select_a_source_sibling(self):
        with tempfile.TemporaryDirectory(prefix="shiploop-e2e-copied-layout-") as temporary:
            checkout = Path(temporary) / "copied-package-repository"
            package = checkout / "skills" / "shiploop-e2e-audit"
            harness = package / "harness"
            harness.mkdir(parents=True)
            (checkout / ".git").mkdir()
            (package / "SKILL.md").write_text("fixture audit card\n")
            shutil.copy2(layout.__file__, harness / "layout.py")
            spec = importlib.util.spec_from_file_location("copied_audit_layout", harness / "layout.py")
            self.assertIsNotNone(spec)
            copied = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(copied)
        self.assertIsNone(copied.canonical_source_checkout())
        self.assertEqual("installed-skill-dir", copied.default_skill_binding()[1])

    def test_mock_suite_excludes_live_runner_and_full_product_oracles(self):
        self.assertEqual(check_suite.selected("mock"), [
            "test_behavior_capture", "test_dag_replay", "test_protocol_compat", "test_recovery_isolation", "test_trace_corpus",
        ])


if __name__ == "__main__":
    unittest.main()
