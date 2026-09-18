"""Regression checks for honest discovery and execution results in the runner."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
PROBE = """\
import sys
from pathlib import Path
import run_tests
run_tests.ROOT = Path(sys.argv.pop(1))
raise SystemExit(run_tests.main())
"""
GOOD_TEST = """\
import unittest
from test_support import suite
@suite("focused", "smoke")
class Example(unittest.TestCase):
    def test_example(self):
        self.assertEqual(2 + 2, 4)
"""


class RunnerContract(unittest.TestCase):
    def invoke(self, files, *args):
        # Each subprocess has isolated discovery/import state and temporary files.
        with tempfile.TemporaryDirectory(prefix="slug-runner-test-") as directory:
            for name, source in files.items():
                Path(directory, name).write_text(source, encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-B", "-c", PROBE, directory, *args],
                cwd=ROOT, capture_output=True, text=True, timeout=10,
            )

    def test_empty_execution_is_not_a_pass(self):
        for suite in ("full", "focused", "smoke"):
            with self.subTest(suite=suite):
                result = self.invoke({}, "--suite", suite)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("no tests selected", result.stderr)

    def test_empty_subset_is_not_a_pass(self):
        files = {"test_example.py": GOOD_TEST.replace('@suite("focused", "smoke")', "")}
        for suite in ("focused", "smoke"):
            with self.subTest(suite=suite):
                result = self.invoke(files, "--suite", suite)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("no tests selected", result.stderr)

    def test_discovery_errors_are_not_filtered_or_listed_as_success(self):
        files = {
            "test_example.py": GOOD_TEST,
            "test_broken.py": 'raise RuntimeError("deliberate discovery failure")\n',
        }
        for args in (("--list",), ("--suite", "focused"),
                     ("--suite", "smoke"), ("--suite", "full")):
            with self.subTest(args=args):
                result = self.invoke(files, *args)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("deliberate discovery failure", result.stderr)

    def test_successful_selection_reverse_and_repeat(self):
        for suite in ("full", "focused", "smoke"):
            with self.subTest(suite=suite):
                result = self.invoke(
                    {"test_example.py": GOOD_TEST}, "--suite", suite,
                    "--reverse", "--repeat", "2",
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(result.stdout.count("Ran 1 test in"), 2)
                self.assertEqual(result.stdout.count("\nOK\n"), 2)
