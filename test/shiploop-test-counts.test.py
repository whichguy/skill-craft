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
# Real unittest output (Python 3.14, tracebacks trimmed, neutral module names): a test module that cannot be imported
# is reported as one synthetic test, ``unittest.loader._FailedTest``, that errored.  ``Ran`` and ``errors=`` count it
# as a test, but no test of the module ran.  The second form is the name Python 3.8 to 3.11 print.
UNITTEST_LOAD_FAILURE = """\
E
======================================================================
ERROR: test_widgets (unittest.loader._FailedTest.test_widgets)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_widgets
Traceback (most recent call last):
  File "unittest/loader.py", line 141, in loadTestsFromName
    module = __import__(module_name)
  File "test_widgets.py", line 1, in <module>
    import widgets
ModuleNotFoundError: No module named 'widgets'


----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (errors=1)
"""
UNITTEST_LOAD_FAILURE_OLD_NAME = UNITTEST_LOAD_FAILURE.replace("_FailedTest.test_widgets)", "_FailedTest)")
# One module loads and passes two tests, another cannot be imported: Ran 3, errors=1, but only 2 tests ran.
UNITTEST_ONE_MODULE_LOADS = UNITTEST_LOAD_FAILURE.replace("E\n=====", "..E\n=====", 1).replace("Ran 1 test", "Ran 3 tests")
# One module has a failing and a passing test, another cannot be imported: Ran 3, failures=1, errors=1.
UNITTEST_FAILING_AND_UNLOADABLE = (UNITTEST_LOAD_FAILURE.replace("E\n=====", "F.E\n=====", 1).replace("Ran 1 test", "Ran 3 tests")
                                   .replace("FAILED (errors=1)", "FAILED (failures=1, errors=1)"))
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

    def test_a_unittest_module_that_cannot_be_imported_is_not_a_test_that_ran(self):
        """The loader's synthetic ``_FailedTest`` is counted by ``Ran`` and ``errors=``; no test of that module ran."""
        self.assertRan(UNITTEST_LOAD_FAILURE, 0, 0, exit_code=1)
        self.assertRan(UNITTEST_LOAD_FAILURE_OLD_NAME, 0, 0, exit_code=1)
        self.assertRan(UNITTEST_ONE_MODULE_LOADS, 2, 0, exit_code=1)
        self.assertRan(UNITTEST_FAILING_AND_UNLOADABLE, 2, 1, exit_code=1)
        # a real error inside a test is still a failure that ran
        self.assertRan("E.\n======\nERROR: test_a (test_a.A.test_a)\nRan 2 tests in 0.001s\n\nFAILED (errors=1)\n", 2, 1,
                       exit_code=1)

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


    def test_an_unloadable_unittest_module_reads_as_no_test_ran_in_both_modes(self):
        """The W1 defect class for the most common Python runner: no listed ID, so only the count can refuse it."""
        row = {"command": "python3 -m unittest test_widgets", "suite": "focused"}
        self.assertEqual(self.status(row, 1, UNITTEST_LOAD_FAILURE), "no-tests")
        self.assertEqual(self.status(row, 1, UNITTEST_LOAD_FAILURE, red=True), "no-tests")
        self.assertEqual(self.status(row, 1, UNITTEST_ONE_MODULE_LOADS, red=True), "not-red")
        self.assertEqual(self.status(row, 1, UNITTEST_FAILING_AND_UNLOADABLE, red=True), "red")

NODE = ROOT / "test/fixtures/shiploop-node-test"


def node(name: str) -> str:
    return (NODE / name).read_text(encoding="utf-8")


class NodeTestRunnerTests(unittest.TestCase):
    """``node --test`` output as Node 25 prints it (see the fixtures README): spec, TAP, ANSI-coloured, a load failure.

    A skipped or todo test is not a test that ran; a title that merely contains ``pending``, ``skip`` or ``todo`` is."""

    def assertRan(self, name: str, ran: int, failed: int, code: int = 0) -> None:
        result = counts.count(node(name), code)
        self.assertIsNotNone(result, name)
        self.assertEqual((result["ran"], result["failed"]), (ran, failed), name)
        self.assertEqual(result["runners"], ["node"], name)

    def test_the_spec_and_tap_reporters_are_counted(self):
        self.assertRan("pass-spec.txt", 2, 0)
        self.assertRan("pass-tap.txt", 2, 0)
        self.assertRan("fail-spec.txt", 5, 1, code=1)
        self.assertRan("fail-tap.txt", 5, 1, code=1)

    def test_colour_codes_do_not_change_the_count_or_the_names(self):
        self.assertRan("fail-spec-color.txt", 5, 1, code=1)
        shown = counts.named(node("fail-spec-color.txt"), ["TC-2", "TC-3", "TC-7"])
        self.assertEqual((shown["shown"], shown["missing"]), (["TC-2", "TC-7"], ["TC-3"]))

    def test_a_file_that_cannot_be_loaded_is_not_a_test_that_ran(self):
        self.assertRan("load-spec.txt", 0, 0, code=1)
        self.assertRan("load-tap.txt", 0, 0, code=1)

    def test_reporters_without_a_summary_are_not_guessed(self):
        self.assertIsNone(counts.count(node("pass-dot.txt"), 0))
        self.assertIsNone(counts.count(node("fail-junit.txt"), 1))

    def test_a_skip_is_read_from_the_runner_syntax_not_from_a_word_in_the_title(self):
        ids = ["TC-1", "TC-2", "TC-3", "TC-4"]
        for name in ("pass-spec.txt", "pass-tap.txt"):
            with self.subTest(name):
                names = counts.named(node(name), ids)
                self.assertEqual(names["shown"], ["TC-1", "TC-2"])  # TC-2 says "pending" in its title and ran
                self.assertEqual(names["missing"], ["TC-3", "TC-4"])  # skipped and todo tests did not run

    def test_existing_runners_keep_their_skip_lines(self):
        for line in ("test_a.py::TC-5 SKIPPED (reason)", "test_x (m.C.TC-5) ... skipped 'why'", "--- SKIP: TC-5",
                     "  - TC-5", "  \u2193 TC-5 [skipped]", "ok 5 - TC-5 # SKIP"):
            with self.subTest(line=line):
                self.assertEqual(counts.named(line + "\n", ["TC-5"])["missing"], ["TC-5"])
        self.assertEqual(counts.named("--- PASS: TC-5 (0.00s)\n", ["TC-5"])["shown"], ["TC-5"])
        self.assertEqual(counts.named("    \u2713 TC-5 pending cell\n", ["TC-5"])["shown"], ["TC-5"])

    def test_a_test_runner_recorded_as_suite_check_is_still_refused_when_it_ran_nothing(self):
        """Live finding (Sonnet 2026-10-07, release-verify): `node --test` was recorded as suite `check`, judged by exit
        code alone with counts null; zero tests would have passed. Output that shows a runner summary is counted."""
        check = {"command": "node --test", "suite": "check"}
        zero = "ℹ tests 0\nℹ suites 0\nℹ pass 0\nℹ fail 0\nℹ cancelled 0\nℹ skipped 0\nℹ todo 0\n"
        self.assertEqual(test_loop.judge(check, 0, zero)["status"], "no-tests")
        ran = test_loop.judge(check, 0, node("pass-spec.txt"))
        self.assertEqual((ran["status"], ran["counts"]["ran"]), ("passed", 2))
        self.assertEqual(test_loop.judge(check, 1, node("fail-spec.txt"))["status"], "failed")
        # a command that is not a test runner is still judged by its exit code
        self.assertEqual(test_loop.judge(check, 0, "")["status"], "passed")
        self.assertEqual(test_loop.judge(check, 1, "")["status"], "failed")

    def test_the_judge_refuses_a_node_load_failure_and_accepts_the_real_runs(self):
        focused = {"command": "node --test", "suite": "focused"}
        status = lambda row, code, name, **kw: test_loop.judge(row, code, node(name), **kw)["status"]  # noqa: E731
        self.assertEqual(status(focused, 1, "load-spec.txt"), "no-tests")
        self.assertEqual(status(focused, 1, "load-spec.txt", red=True), "no-tests")
        self.assertEqual(status(focused, 0, "pass-spec.txt"), "passed")
        self.assertEqual(status(dict(focused, min_tests=3), 0, "pass-spec.txt"), "too-few-tests")
        self.assertEqual(status(dict(focused, ids=["TC-3"]), 0, "pass-tap.txt"), "ids-missing")
        self.assertEqual(status(focused, 1, "fail-spec.txt", red=True), "red")
        self.assertEqual(status(focused, 0, "pass-dot.txt"), "uncounted")


class HostDependentDriftTests(unittest.TestCase):
    """B2: a system case that needs a host tool (a browser) must not run in the project's default suite.

    The delivered Battleship repo's plain `node --test` ran two Chrome cases and needed macOS Chrome, and every gate passed
    it.  A system row marks `host_dependent`; at system-test ShipLoop also runs the accepted regression commands and
    refuses when a marked id is shown (run, pass or fail) in their output."""

    SYSTEM = {"command": "node --test test/system.test.js", "suite": "focused", "ids": ["TC-4", "TC-15"],
              "host_dependent": True}
    REGRESSION = {"command": "node --test", "suite": "regression", "min_tests": 2}

    def state(self, repo: Path) -> dict:
        return {
            "repo": str(repo), "work_items": [{"id": "W1"}],
            "history": [
                {"action": "a-sys", "stage": "system-test-author", "workitem": None, "outcome": "done"},
                {"action": "a-plan", "stage": "step-plan", "workitem": "W1", "outcome": "done"}],
            "accepted": {
                "a-sys": {"outcome": "done", "system_commands": [self.SYSTEM]},
                "a-plan": {"outcome": "done", "test_commands": [self.REGRESSION]}}}

    def run_system_test(self, default_suite_output: str):
        import tempfile
        calls = []

        def runner(argv, cwd, timeout, input_bytes=b"", env=None):
            command = argv[-1]
            calls.append(command)
            if command == self.SYSTEM["command"]:
                return "ok", 0, node("pass-spec.txt").replace("TC-1 ", "TC-4 ").replace("TC-2 ", "TC-15 ").encode(), b""
            return "ok", 0, default_suite_output.encode(), b""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "tests").mkdir()
            writes, refusal = test_loop.verify(root, self.state(root), "", "a-run", "system-test", runner=runner)
        return calls, writes, refusal

    def test_a_marked_id_shown_by_the_default_suite_is_refused_with_the_remedy(self) -> None:
        shows = "✔ TC-4 opens the page in Chrome (30ms)\n✔ TC-9 rules (1ms)\nℹ tests 2\nℹ pass 2\nℹ fail 0\nℹ cancelled 0\n"
        calls, writes, refusal = self.run_system_test(shows)
        self.assertEqual(calls, [self.SYSTEM["command"], self.REGRESSION["command"]])
        self.assertIn("TC-4", refusal)
        self.assertIn("host-dependent", refusal)
        self.assertIn("opt-in", refusal)
        record = next(iter(writes.values()))
        self.assertIn("host-dependent-in-default-suite", record)

    def test_the_default_suite_that_skips_or_omits_the_marked_ids_passes(self) -> None:
        for name, output in (
                ("omitted", "✔ TC-9 rules (1ms)\n✔ TC-10 rules (1ms)\nℹ tests 2\nℹ pass 2\nℹ fail 0\nℹ cancelled 0\n"),
                ("skipped", "﹣ TC-4 needs Chrome (0.1ms) # set BROWSER=1\n✔ TC-9 rules (1ms)\n✔ TC-10 (1ms)\n"
                            "ℹ tests 3\nℹ pass 2\nℹ fail 0\nℹ cancelled 0\nℹ skipped 1\n")):
            with self.subTest(name):
                _calls, _writes, refusal = self.run_system_test(output)
                self.assertEqual(refusal, "")

    def test_without_a_marked_row_the_default_suite_is_not_run_at_system_test(self) -> None:
        import tempfile
        state_calls = []

        def runner(argv, cwd, timeout, input_bytes=b"", env=None):
            state_calls.append(argv[-1])
            return "ok", 0, node("pass-spec.txt").encode(), b""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "tests").mkdir()
            state = self.state(root)
            state["accepted"]["a-sys"]["system_commands"] = [dict(self.SYSTEM)]
            del state["accepted"]["a-sys"]["system_commands"][0]["host_dependent"]
            _writes, refusal = test_loop.verify(root, state, "", "a-run", "system-test", runner=runner)
        self.assertEqual(state_calls, [self.SYSTEM["command"]])

    def test_host_dependent_is_a_boolean_true_and_nothing_else(self) -> None:
        row = {"command": "x", "suite": "focused", "ids": ["TC-1"], "host_dependent": True}
        self.assertTrue(test_loop.normalise_commands([row])[0]["host_dependent"])
        for bad in (False, "yes", 1):
            with self.subTest(bad=bad), self.assertRaises(test_loop.TestLoopError):
                test_loop.normalise_commands([dict(row, host_dependent=bad)])


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
