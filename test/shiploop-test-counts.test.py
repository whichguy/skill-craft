#!/usr/bin/env python3
"""Hermetic tests for reading executed-test counts and named IDs from runner output.

The outputs below are the summary lines each runner prints; the Jest
skipped-only case is the one a Battleship run recorded when ``-t <filter>``
matched no test name and ``npm test`` still exited 0.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_test_counts as counts  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402

JEST_SKIPPED = """\
> fleet@1.0.0 test
> sfdx-lwc-jest -- -t TC-9

Test Suites: 1 skipped, 0 of 1 total
Tests:       2 skipped, 2 total
Snapshots:   0 total
Time:        0.412 s
Ran all test suites with tests matching "TC-9".
"""
JEST_PASS = """\
 PASS  force-app/main/default/lwc/fleetCommand/__tests__/fleetCommand.test.js
  fleetCommand
    ✓ TC-9 places a fleet (12 ms)
    ✓ TC-10 rejects an overlapping ship (3 ms)
    ○ skipped TC-11 reload keeps the fleet

Test Suites: 1 passed, 1 total
Tests:       1 skipped, 2 passed, 3 total
"""
JEST_SUITE_ERROR = """\
 FAIL  force-app/main/default/lwc/fleetCommand/__tests__/fleetCommand.test.js
  ● Test suite failed to run
    SyntaxError: Unexpected token (4:10)

Test Suites: 1 failed, 1 total
Tests:       0 total
"""
JEST_RED = """\
 FAIL  force-app/main/default/lwc/fleetCommand/__tests__/fleetCommand.test.js
    ✕ TC-9 places a fleet (8 ms)

Tests:       1 failed, 1 total
"""
VITEST = " Test Files  1 passed (1)\n      Tests  1 failed | 3 passed | 2 skipped (6)\n"
PYTEST_DESELECTED = "============ 5 deselected in 0.02s ============\n"
PYTEST_PASS = "tests/test_board.py::test_tc_9 PASSED\n====== 3 passed, 1 skipped in 0.12s ======\n"
PYTEST_QUIET = "..F\n1 failed, 2 passed in 0.05s\n"
UNITTEST_SKIPPED = "ss\n----------------------------------------------------------------------\nRan 2 tests in 0.000s\n\nOK (skipped=2)\n"
UNITTEST_ZERO = "\n----------------------------------------------------------------------\nRan 0 tests in 0.000s\n\nNO TESTS RAN\n"
MOCHA = "  board\n    ✓ TC-1 places\n\n  3 passing (12ms)\n  1 failing\n"
CARGO = ("running 2 tests\ntest a ... ok\ntest b ... ok\n\ntest result: ok. 2 passed; 0 failed; 0 ignored; "
         "0 measured; 3 filtered out; finished in 0.00s\n\nrunning 0 tests\n\ntest result: ok. 0 passed; 0 failed; "
         "0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n")
GO_NONE = "testing: warning: no tests to run\nPASS\nok  \texample.com/board\t0.002s [no tests to run]\n"
GO_NO_FILES = "?   \texample.com/board\t[no test files]\n"
GO_VERBOSE = "=== RUN   TestPlace\n--- PASS: TestPlace (0.00s)\n--- FAIL: TestSink (0.00s)\nFAIL\n"
DOTNET_NONE = "No test matches the given testcase filter `FullyQualifiedName~TC9` in /src/bin/Board.Tests.dll\n"
DOTNET = "Passed!  - Failed:     0, Passed:     3, Skipped:     1, Total:     4, Duration: 12 ms\n"


class CountTests(unittest.TestCase):
    def assertRan(self, output: str, ran: int, failed: int = 0, exit_code: int = 0) -> None:
        result = counts.count(output, exit_code)
        self.assertIsNotNone(result, output)
        self.assertEqual((result["ran"], result["failed"]), (ran, failed), output)

    def test_zero_executed_runs_are_recognised(self):
        for output, code in ((JEST_SKIPPED, 0), ("No tests found, exiting with code 0\n", 0),
                             ("No test files found, exiting with code 1\n", 1), (PYTEST_DESELECTED, 5),
                             ("", 5), (UNITTEST_SKIPPED, 0), (UNITTEST_ZERO, 5), (GO_NONE, 0),
                             (GO_NO_FILES, 0), (DOTNET_NONE, 0)):
            with self.subTest(output=output[:40]):
                self.assertRan(output, 0, exit_code=code)

    def test_executed_and_failed_counts(self):
        self.assertRan(JEST_PASS, 2)
        self.assertRan(JEST_RED, 1, 1)
        self.assertRan(JEST_SUITE_ERROR, 0)
        self.assertRan(VITEST, 4, 1)
        self.assertRan(PYTEST_PASS, 3)
        self.assertRan(PYTEST_QUIET, 3, 1)
        self.assertRan(MOCHA, 4, 1)
        self.assertRan(CARGO, 2)
        self.assertRan(GO_VERBOSE, 2, 1)
        self.assertRan(DOTNET, 3)

    def test_unrecognised_output_is_not_guessed(self):
        self.assertIsNone(counts.count("all good\n", 0))
        self.assertIsNone(counts.count("", 0))

    def test_ids_on_skip_lines_do_not_count_as_run(self):
        names = counts.named(JEST_PASS, ["TC-9", "TC-10", "TC-11", "TC-1"])
        self.assertEqual(names["shown"], ["TC-9", "TC-10"])
        self.assertEqual(names["missing"], ["TC-11", "TC-1"])


class JudgeTests(unittest.TestCase):
    FOCUSED = {"command": "npm test -- -t TC-9", "suite": "focused", "ids": ["TC-9", "TC-10"]}

    def status(self, row: dict, code: int, output: str, **kw) -> str:
        return test_loop.judge(row, code, output, **kw)["status"]

    def test_the_battleship_filter_that_matched_nothing_is_refused(self):
        self.assertEqual(self.status(self.FOCUSED, 0, JEST_SKIPPED), "no-tests")

    def test_pass_needs_count_and_every_listed_id(self):
        self.assertEqual(self.status(self.FOCUSED, 0, JEST_PASS), "passed")
        row = dict(self.FOCUSED, ids=["TC-9", "TC-11"])
        self.assertEqual(self.status(row, 0, JEST_PASS), "ids-missing")
        self.assertEqual(self.status(dict(self.FOCUSED, min_tests=3), 0, JEST_PASS), "too-few-tests")
        self.assertEqual(self.status(self.FOCUSED, 1, JEST_RED), "failed")

    def test_uncounted_output(self):
        focused = {"command": "./run", "suite": "focused"}
        regression = {"command": "./run-all", "suite": "regression"}
        self.assertEqual(self.status(focused, 0, "ok\n"), "uncounted")
        self.assertEqual(self.status(dict(focused, ids=["TC-9"]), 0, "TC-9 ok\n"), "passed")
        self.assertEqual(self.status(regression, 0, "ok\n"), "passed-uncounted")
        self.assertEqual(self.status(dict(regression, min_tests=1), 0, "ok\n"), "uncounted")

    def test_red_needs_a_failing_test_not_a_setup_error(self):
        row = {"command": "npm test -- -t TC-9", "suite": "focused", "ids": ["TC-9"]}
        self.assertEqual(self.status(row, 1, JEST_RED, red=True), "red")
        self.assertEqual(self.status(row, 1, JEST_SUITE_ERROR, red=True), "no-tests")
        self.assertEqual(self.status(row, 0, JEST_PASS, red=True), "green")
        self.assertEqual(self.status(row, 1, "Ran 1 test in 0.01s\nOK\n", red=True), "not-red")
        self.assertEqual(self.status({"command": "./t", "suite": "focused"}, 1, "boom\n", red=True), "uncounted")


class CommandSchemaTests(unittest.TestCase):
    def test_ids_and_min_tests_are_validated(self):
        rows = test_loop.normalise_commands([
            {"command": " npm test ", "suite": "focused", "ids": ["TC-9"], "min_tests": 2},
            {"command": "npm run all", "suite": "regression"},
        ])
        self.assertEqual(rows, [{"command": "npm test", "suite": "focused", "ids": ["TC-9"], "min_tests": 2},
                                {"command": "npm run all", "suite": "regression"}])
        for bad in ({"ids": []}, {"ids": ["TC 9"]}, {"ids": ["A", "A"]}, {"min_tests": 0},
                    {"min_tests": True}, {"other": 1}):
            with self.subTest(bad=bad), self.assertRaises(test_loop.TestLoopError):
                test_loop.normalise_commands([dict({"command": "x", "suite": "focused"}, **bad)])


if __name__ == "__main__":
    unittest.main()
