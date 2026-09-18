"""No-model suite selection is explicit and cannot route into the live runner."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

import check_suite


class CheckSuiteTests(unittest.TestCase):
    def test_all_includes_every_apparatus_test_exactly_once(self):
        selected = check_suite.selected("all")
        self.assertEqual(len(selected), len(set(selected)))
        self.assertEqual(set(selected), {p.stem for p in check_suite.HERE.glob("test_*.py")})
        self.assertNotIn("run", selected)

    def test_short_workflow_suite_lists_without_running_tests(self):
        result = subprocess.run([sys.executable, "-B", str(Path(check_suite.__file__)), "--suite", "workflow", "--list"],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        row = json.loads(result.stdout)
        self.assertEqual(row["model_calls"], 0)
        self.assertEqual(row["modules"], ["test_campaign", "test_recovery_isolation", "test_workflow_review"])

    def test_mock_suite_excludes_live_runner_and_full_product_oracles(self):
        self.assertEqual(check_suite.selected("mock"), [
            "test_behavior_capture", "test_dag_replay", "test_protocol_compat", "test_recovery_isolation", "test_trace_corpus",
        ])


if __name__ == "__main__":
    unittest.main()
