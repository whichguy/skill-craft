import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class RunnerSelection(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="catalog-runner-test-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        shutil.copyfile(Path(__file__).with_name("run_tests.py"), self.root / "run_tests.py")

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(self.root / "run_tests.py"), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_discovery_errors_fail_every_suite(self):
        (self.root / "test_broken.py").write_text(
            "raise RuntimeError('discovery sentinel')\n", encoding="utf-8"
        )
        for name in ("focused", "smoke", "full"):
            with self.subTest(suite=name):
                result = self.run_cli("--suite", name)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("_FailedTest.test_broken", result.stdout)
                self.assertIn("RuntimeError: discovery sentinel", result.stdout)

    def test_empty_execution_fails_every_suite(self):
        for name in ("focused", "smoke", "full"):
            with self.subTest(suite=name):
                result = self.run_cli("--suite", name)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("No tests selected", result.stdout + result.stderr)

    def test_empty_listing_succeeds_without_execution(self):
        result = self.run_cli("--list")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout), {"focused": [], "smoke": [], "full": []})

    def test_untagged_tests_leave_focused_and_smoke_empty(self):
        (self.root / "test_untagged.py").write_text(
            "import unittest\n"
            "class Untagged(unittest.TestCase):\n"
            "    def test_passes(self):\n"
            "        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        for name in ("focused", "smoke"):
            with self.subTest(suite=name):
                result = self.run_cli("--suite", name)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("No tests selected", result.stdout + result.stderr)
        result = self.run_cli("--suite", "full")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Ran 1 test", result.stdout)
