#!/usr/bin/env python3
"""Hermetic checks for the repeatable-test pilot fixture and its grader.

The tests materialize only disposable local Git repositories.  They never
launch a model, contact a remote system, or reuse a worker result.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import fixtures
import grade


class RepeatableFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="shiploop-repeatable-fixture-test-")
        self.addCleanup(self.temporary.cleanup)
        self.study = Path(self.temporary.name) / "study"

    def prepare(self, case: str) -> dict:
        record = fixtures.prepare(case, self.study)
        fixture = Path(record["fixture"])
        self.assertTrue((fixture / ".git").is_dir())
        self.assertTrue(Path(record["job"]).is_file())
        self.assertIn("SPEC.md", {Path(path).name for path in record["immutable_hashes"]})
        return record

    def add_good_tests(self, case: str, record: dict) -> None:
        source = self.study / "calibration" / case / "test_reference.py"
        shutil.copyfile(source, Path(record["fixture"]) / "test_contract.py")

    @staticmethod
    def source_hashes(record: dict) -> dict[str, str]:
        paths = [*record["production_paths"], next(path for path in record["immutable_paths"] if Path(path).name == "SPEC.md")]
        return {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths}

    def test_all_cases_calibrate_and_grade_synthetic_good_tests(self) -> None:
        for case in fixtures.CASES:
            with self.subTest(case=case):
                record = self.prepare(case)
                calibration = grade.calibrate(case, self.study)
                self.assertTrue(calibration["passed"], calibration)
                self.add_good_tests(case, record)
                before = self.source_hashes(record)
                result = grade.grade(case, self.study, record)
                self.assertNotIn("passed", result)
                self.assertTrue(result["mechanical_passed"], result["checks"])
                self.assertEqual(result["status"], "mechanical-pass-with-manual-pending")
                self.assertEqual(before, self.source_hashes(record))
                self.assertTrue(all("elapsed_seconds" in run for run in result["candidate_sequence"]["runs"].values()))

    def test_full_fallback_to_smoke_is_rejected_by_actual_execution(self) -> None:
        record = self.prepare("price-format")
        self.add_good_tests("price-format", record)
        runner = Path(record["fixture"]) / "run_tests.py"
        original = runner.read_text(encoding="utf-8")
        self.assertIn("tests = selected(discovered(), args.suite)", original)
        runner.write_text(
            original.replace(
                "tests = selected(discovered(), args.suite)",
                'tests = selected(discovered(), "smoke" if args.suite == "full" else args.suite)',
            ),
            encoding="utf-8",
        )
        result = grade.grade("price-format", self.study, record)
        self.assertFalse(result["mechanical_passed"])
        self.assertEqual(result["status"], "mechanical-fail")
        self.assertFalse(result["checks"]["candidate_sequence"])
        self.assertFalse(result["checks"]["full_route"])

    def test_immutable_spec_mutation_is_the_only_failed_scored_check(self) -> None:
        record = self.prepare("price-format")
        self.add_good_tests("price-format", record)
        spec = Path(record["fixture"]) / "SPEC.md"
        spec.write_text(spec.read_text(encoding="utf-8") + "\nChanged after baseline.\n", encoding="utf-8")
        result = grade.grade("price-format", self.study, record)
        self.assertFalse(result["mechanical_passed"])
        self.assertEqual({name for name, passed in result["checks"].items() if not passed}, {"immutable_scope"})

    def test_zero_focused_and_smoke_selection_is_not_a_pass(self) -> None:
        record = self.prepare("price-format")
        self.add_good_tests("price-format", record)
        runner = Path(record["fixture"]) / "run_tests.py"
        original = runner.read_text(encoding="utf-8")
        runner.write_text(
            original.replace(
                'return tests if suite == "full" else [test for test in tests if suite in tags(test)]',
                'return tests if suite == "full" else []',
            ),
            encoding="utf-8",
        )
        result = grade.grade("price-format", self.study, record)
        self.assertFalse(result["mechanical_passed"])
        self.assertFalse(result["checks"]["selection"])
        self.assertFalse(result["selection"]["suites"]["focused"]["nonzero"])
        self.assertFalse(result["selection"]["suites"]["smoke"]["nonzero"])

    def test_product_rewrite_in_grader_clone_is_rejected_without_touching_worker(self) -> None:
        record = self.prepare("price-format")
        self.add_good_tests("price-format", record)
        before = self.source_hashes(record)
        (Path(record["fixture"]) / "test_clone_writer.py").write_text(
            '''import unittest
from pathlib import Path

class CloneWriter(unittest.TestCase):
    def test_rewrites_production_after_discovery(self):
        Path(__file__).with_name("pricing.py").write_text(
            "def price_cents(quantity, unit_cents): return 0\\n"
            "def format_price(cents): return 'rewritten'\\n",
            encoding="utf-8",
        )
''',
            encoding="utf-8",
        )
        result = grade.grade("price-format", self.study, record)
        guard = result["candidate_sequence"]["runs"]["full"]["immutable_guard"]
        self.assertFalse(result["mechanical_passed"])
        self.assertFalse(guard["passed"])
        self.assertEqual(guard["intended_sha256"], guard["before_sha256"])
        self.assertNotEqual(guard["intended_sha256"], guard["after_sha256"])
        self.assertEqual(before, self.source_hashes(record))

    def test_cli_reports_mechanical_pass_with_manual_pending(self) -> None:
        record = self.prepare("price-format")
        self.add_good_tests("price-format", record)
        baseline = self.study / "baseline.json"
        baseline.write_text(json.dumps(record), encoding="utf-8")
        output = io.StringIO()
        with patch.object(sys, "argv", ["grade.py", "--case", "price-format", "--root", str(self.study), "--baseline", str(baseline)]), redirect_stdout(output):
            self.assertEqual(grade.main(), 0)
        payload = json.loads(output.getvalue())
        self.assertNotIn("passed", payload)
        self.assertTrue(payload["mechanical_passed"])
        self.assertEqual(payload["status"], "mechanical-pass-with-manual-pending")

    def test_subtests_with_docstrings_are_observed_as_parent_tests(self) -> None:
        record = self.prepare("expected-red")
        self.add_good_tests("expected-red", record)
        fixture = Path(record["fixture"])
        (fixture / "test_subtest_docstring.py").write_text(
            '''"""A module docstring should not affect execution observation."""
import unittest
from slug import slugify


class SubtestDocstringContract(unittest.TestCase):
    """Class docstring."""

    def test_separator_runs(self):
        """Method docstring with subtests."""
        for title, expected in (("A--B", "a-b"), ("Hello   World", "hello-world")):
            with self.subTest(title=title):
                self.assertEqual(slugify(title), expected)
''',
            encoding="utf-8",
        )
        runner = fixture / "run_tests.py"
        runner.write_text(
            runner.read_text(encoding="utf-8").replace(
                "tests = selected(discovered(), args.suite)",
                "tests = list(reversed(selected(discovered(), args.suite)))",
            ),
            encoding="utf-8",
        )
        result = grade.grade("expected-red", self.study, record)
        execution = result["candidate_sequence"]["executions"]["full"]
        repeat = result["candidate_sequence"]["executions"]["repeat"]
        reverse = result["candidate_sequence"]["executions"]["reverse"]
        identifier = "test_subtest_docstring.SubtestDocstringContract.test_separator_runs"
        self.assertTrue(result["mechanical_passed"], result["checks"])
        self.assertIn(identifier, execution["executed_ids"])
        self.assertEqual(execution["unrun_ids"], [])
        self.assertNotEqual(execution["batches"][0], result["selection"]["discovered_ids"])
        self.assertEqual(repeat["batches"], [execution["batches"][0]] * 2)
        self.assertEqual(reverse["batches"], [list(reversed(execution["batches"][0]))])


if __name__ == "__main__":
    unittest.main(verbosity=2)
