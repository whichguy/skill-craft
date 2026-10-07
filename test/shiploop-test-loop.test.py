#!/usr/bin/env python3
"""Hermetic tests for ShipLoop's script-enforced test loops at test-green and regression.

The run binds the repository's source Improve card, so each loop uses the real
bundled Until Loop runtime, and ShipLoop really runs the recorded commands
(``sh check.sh <file>``, which prints a unittest-style summary) before it accepts done.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/shiploop"
IMPROVE_CARD = ROOT / "skills/improve/SKILL.md"
sys.path.insert(0, str(PACKAGE / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import shiploop_knowledge_support as knowledge_support  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_item_scope as item_scope  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402

CORE = types.SimpleNamespace(PACKAGE_ROOT=PACKAGE, REF_DIR=PACKAGE / "references")
DONE = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}
TRIVIAL = {"classification": "trivial", "exit_assessment": "satisfied", "continuation_assessment": "allowed",
           "evidence": "Synthetic iteration: every command exited 0.", "handoff": "Synthetic; nothing remains."}
MATERIAL = dict(TRIVIAL, classification="non-trivial", exit_assessment="unsatisfied",
                evidence="Synthetic iteration: a command failed and the code was fixed.")
# A one-test runner: prints a unittest summary, fails while its file is missing.
CHECK = ('echo "Ran 1 test in 0.001s"\n'
         'if test -f "$1"; then echo OK; else echo "FAILED (failures=1)"; exit 1; fi\n')
COMMANDS = [{"command": "sh check.sh fixed.txt", "suite": "focused"},
            {"command": "test -f retained.txt", "suite": "regression"}]
# A test file that loads something this item creates dies before any test runs while that file is missing.  LOADER is
# a neutral one-test runner that does so; NODE_LOAD_FAILURE and NODE_ONE_FAILING are real node:test outputs (v25, a
# neutral module name, paths trimmed): the whole file fails before a test runs, then one of two named tests fails.
LOADER = ('if test ! -f widgets.txt; then echo "Error: Cannot find module \'./widgets\'"; exit 1; fi\n'
          'echo "Ran 1 test in 0.001s"; echo OK\n')
UNITTEST_OK = "..\nRan 2 tests in 0.001s\n\nOK\n"
UNITTEST_FAIL = "F.\n======\nFAIL: test_a\nRan 2 tests in 0.001s\n\nFAILED (failures=1)\n"
UNITTEST_ZERO = "\nRan 0 tests in 0.000s\n\nOK\n"
# Real unittest output (Python 3.14, trimmed): a test module that cannot be imported is one synthetic test of
# ``unittest.loader._FailedTest`` that errored, and ``Ran`` and ``errors=`` count it, though no test of it ran.
UNITTEST_LOAD_FAILURE = (
    "E\n" + "=" * 70 + "\nERROR: test_widgets (unittest.loader._FailedTest.test_widgets)\n" + "-" * 70 + "\n"
    "ImportError: Failed to import test module: test_widgets\nTraceback (most recent call last):\n"
    "  File \"test_widgets.py\", line 1, in <module>\n    import widgets\n"
    "ModuleNotFoundError: No module named 'widgets'\n\n\n" + "-" * 70 + "\nRan 1 test in 0.000s\n\nFAILED (errors=1)\n")
UNITTEST_ONE_MODULE_LOADS = UNITTEST_LOAD_FAILURE.replace("E\n=", "..E\n=", 1).replace("Ran 1 test", "Ran 3 tests")
UNITTEST_FAILING_AND_UNLOADABLE = (UNITTEST_LOAD_FAILURE.replace("E\n=", "F.E\n=", 1).replace("Ran 1 test", "Ran 3 tests")
                                   .replace("FAILED (errors=1)", "FAILED (failures=1, errors=1)"))
NODE_LOAD_FAILURE = """node:internal/modules/cjs/loader:1478
  throw err;
  ^

Error: Cannot find module '../widgets.js'
Require stack:
- test/widgets.test.js
    at Module._resolveFilename (node:internal/modules/cjs/loader:1475:15)
    at Module.require (node:internal/modules/helpers:191:16)
    at Object.<anonymous> (test/widgets.test.js:3:17) {
  code: 'MODULE_NOT_FOUND',
  requireStack: [
    'test/widgets.test.js'
  ]
}

Node.js v25.9.0
\u2716 test/widgets.test.js (55.125209ms)
\u2139 tests 1
\u2139 suites 0
\u2139 pass 0
\u2139 fail 1
\u2139 cancelled 0
\u2139 skipped 0
\u2139 todo 0
\u2139 duration_ms 59.189125

\u2716 failing tests:

test at test/widgets.test.js:1:1
\u2716 test/widgets.test.js (55.125209ms)
  'test failed'
"""
NODE_ONE_FAILING = """\u2716 TC-01 makes a widget (1.238625ms)
\u2714 TC-02 counts widgets (0.092542ms)
\u2139 tests 2
\u2139 suites 0
\u2139 pass 1
\u2139 fail 1
\u2139 cancelled 0
\u2139 skipped 0
\u2139 todo 0
\u2139 duration_ms 61.397291

\u2716 failing tests:

test at test/widgets.test.js:4:1
\u2716 TC-01 makes a widget (1.238625ms)
  AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:

  2 !== 1
"""


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


class TestLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-test-loop-")
        self.addCleanup(temp.cleanup)
        base = Path(temp.name).resolve()
        self.repo = base / "repo"
        self.run_dir = base / "run"
        self.repo.mkdir()
        self.run_dir.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "loop@example.invalid")
        git(self.repo, "config", "user.name", "Loop Test")
        (self.repo / "a.py").write_text("x = 1\n")
        (self.repo / "check.sh").write_text(CHECK)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")

    # -- driving -----------------------------------------------------------------

    def start(self, improve_skill: str = str(IMPROVE_CARD)) -> None:
        nav.save(self.run_dir, nav.new_state(str(self.repo), "Test loop fixture.", improve_skill=improve_skill,
                                             lint_option="off"))

    def state(self) -> dict:
        return store.read_record(self.run_dir / "state.md")

    def action(self) -> str:
        return nav.current_action(self.state())["id"]

    def packet(self) -> str:
        return nav.render(CORE, self.run_dir, self.state())

    def complete(self, result: dict) -> str:
        state = self.state()
        action = nav.current_action(state)["id"]
        if nav.current_stage(state) == "plan" and result.get("outcome") == "done" and "assumptions" not in result:
            result = dict(result, assumptions=[])
        path = self.run_dir / "inbox" / (action + ".md")
        path.parent.mkdir(exist_ok=True)
        path.write_text(store.dumps(result, "result"))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            nav.dispatch(CORE, self.run_dir, state,
                         types.SimpleNamespace(command="complete", action=action, result=str(path)))
        return buffer.getvalue()

    def finish_improve(self) -> None:
        state = self.state()
        action = state["active_improve"]["action_id"]
        updated = nav.finish_improve(state, action, {"summary": "Synthetic Improve.",
                                                     "review_refs": ["synthetic://r"],
                                                     "check_refs": ["synthetic://c"]})
        writes, payload = nav._lint_transition(CORE, self.run_dir, state, updated)
        nav.save(self.run_dir, updated, writes)
        nav._lint_finish(self.run_dir, payload)

    def drive_to(self, stage: str, *, step_plan: dict | None = None) -> dict:
        """Advance with synthetic results; the step plan records ``step_plan`` (default: COMMANDS)."""
        recorded = ({"test_commands": [dict(COMMANDS[0], criteria=["C1"]), *COMMANDS[1:]], "paths": ["a.py"],
                     "criteria": [{"id": "C1", "text": "The item's focused check passes."}]}
                    if step_plan is None else step_plan)
        if recorded.get("test_commands") and "criteria" not in recorded:
            recorded = dict(recorded, test_commands=[dict(recorded["test_commands"][0], criteria=["C1"]),
                                                     *recorded["test_commands"][1:]],
                            criteria=[{"id": "C1", "text": "The item's focused check passes."}])
        recorded = {"steps": [{"id": "S1", "task": "Make the planned change."}], **recorded}
        for _ in range(200):
            state = self.state()
            if state.get("active_improve") is not None:
                self.finish_improve()
                continue
            current = nav.current_stage(state)
            if current == stage:
                return state
            if current in knowledge_support.knowledge.CLOSES:
                knowledge_support.write(state)
            if current == "step-plan":
                self.complete(dict(DONE, **recorded))
            elif current == "release-plan":
                self.complete(dict(DONE, consumer_entry={"how": "run python3 a.py", "sources": ["a.py"]},
                                   consumer_checks=[COMMANDS[1]]))
            elif current == "system-test-author":
                self.complete(dict(DONE, system_commands=[COMMANDS[1]]))
            elif current in test_loop.STAGES:
                self.pass_loop()
            elif current == "static-checks":
                self.run_quality_loop()
                self.complete(dict(DONE, evidence_refs=[str(self.run_dir / "quality"
                                                            / (self.action() + "-terminal.json"))]))
            else:
                self.complete(DONE)
        raise AssertionError("did not reach " + stage)

    # -- the bound Until Loop ------------------------------------------------------

    def terminal(self) -> Path:
        return self.run_dir / test_loop.terminal_path(self.action())

    def run_loop(self, reports: list, *, contract_edit=None) -> dict:
        """Start the packet's printed command and submit ``reports`` in order.

        A callable entry runs between reports (the host's fix).  The last
        returned packet is saved to the printed terminal path.
        """
        start = next(line for line in self.packet().splitlines() if line.startswith("Start: "))
        words = shlex.split(start[len("Start: "):])
        self.assertEqual(words[-2], "<")
        contract = json.loads(Path(words[-1]).read_text())
        if contract_edit is not None:
            contract_edit(contract)
        packet = json.loads(subprocess.run(words[:-2], input=json.dumps(contract), text=True,
                                           capture_output=True, check=True, timeout=30).stdout)
        raw = ""
        for report in reports:
            if callable(report):
                report()
                continue
            self.assertEqual(packet["status"], "active")
            raw = subprocess.run(packet["done_argv"], input=json.dumps(report), text=True,
                                 capture_output=True, check=True, timeout=30).stdout
            packet = json.loads(raw)
        # The runtime, started with the printed --receipt, already wrote the last packet there.
        self.assertEqual(json.loads(self.terminal().read_text()), packet)
        return packet

    def pass_loop(self) -> None:
        """Make both commands pass, run one trivial iteration and submit done."""
        (self.repo / "fixed.txt").write_text("fixed\n")
        (self.repo / "retained.txt").write_text("retained\n")
        self.run_loop([TRIVIAL])
        self.complete(dict(DONE, evidence_refs=[str(self.terminal())]))

    def assert_refused(self, result: dict, pattern: str) -> None:
        before = (self.run_dir / "state.md").read_bytes()
        with self.assertRaisesRegex(nav.NavigatorError, pattern):
            self.complete(result)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before)

    def test_a_none_run_started_with_its_card_binds_the_quality_and_test_loops(self):
        """GUARD (passes on the unchanged tree; F1): both loops read the run's recorded Improve card at every item,
        and under `--planning-review none` no planning child binds it, so a none run is started with the card and
        the loops are then enforced exactly as in a stage run: done without the loop is refused."""
        nav.save(self.run_dir, nav.new_state(str(self.repo), "Test loop fixture.", improve_skill=str(IMPROVE_CARD),
                                             lint_option="off", planning_review="none"))
        self.drive_to("test-green")
        packet = self.packet()
        self.assertIn("Test loop (bound Until Loop; the loop script counts iterations", packet)
        self.assertNotIn("no Improve card is bound", packet)
        self.assert_refused(DONE, "the test loop has not run: no terminal packet exists")
        self.drive_to("static-checks")
        packet = self.packet()
        self.assertIn("Bound Until Loop card", packet)
        self.assertNotIn("no Improve card is bound", packet)
        self.assert_refused(dict(DONE, evidence_refs=[]), "the quality loop has not run: no terminal packet exists")

    def test_a_started_loop_packet_says_to_continue_from_its_receipt(self):
        """X10 (e9_loop_recovery.py): after context loss mid-loop the packet gave no way back but Start."""
        self.start()
        self.drive_to("test-green")
        self.assertNotIn("already started", self.packet())
        self.run_loop([])  # started; the receipt holds the active packet
        self.assertIn("The loop already started: do not run Start again. While the receipt's status is "
                      "active, run its next_argv once", self.packet())

    # -- step plan -----------------------------------------------------------------

    def test_step_plan_must_record_its_test_commands(self):
        self.start()
        self.drive_to("step-plan")
        self.assert_refused(DONE, "a done step-plan result must list test_commands")
        canonical = nav._canonical_result
        for bad, message in (
            ([{"command": "pytest", "suite": "unit"}], "suite must be focused, regression or check"),
            ([{"command": "pytest\nrm -rf x", "suite": "focused"}], "one nonblank line"),
            ([{"command": "pytest"}], "command and suite, and optionally ids, min_tests and criteria"),
            ([], "an empty test_commands list needs test_commands_na"),
        ):
            with self.subTest(bad=bad), self.assertRaisesRegex(nav.NavigatorError, message):
                canonical(dict(DONE, test_commands=bad), stage="step-plan")
        with self.assertRaisesRegex(nav.NavigatorError, "only for an empty test_commands list"):
            canonical(dict(DONE, test_commands=COMMANDS, test_commands_na="x"), stage="step-plan")
        with self.assertRaisesRegex(nav.NavigatorError, "only on a done step-plan result"):
            canonical(dict(DONE, test_commands=COMMANDS), stage="test-green")
        self.assertEqual(canonical(dict(DONE, test_commands=[], test_commands_na="Docs only."),
                                   stage="step-plan")["test_commands_na"], "Docs only.")
        # The step-plan Improve child's final result passes the same CLI gate.
        with self.assertRaisesRegex(nav.NavigatorError, "must list test_commands"):
            nav._check_submitted_test_commands("step-plan", DONE)

    def test_a_command_list_too_large_for_the_loop_contract_is_refused_where_it_is_submitted(self):
        """The test loop's contract is written at a transition, so an oversized list needs a refusal point (F3)."""
        def rows(count, ids):
            return [{"command": f"python3 -m unittest -v test_{n}", "suite": "focused",
                     "ids": [f"test_{n}_{i}_" + "a" * 70 for i in range(ids)]} for n in range(count)]

        def plan(commands):
            return dict(DONE, test_commands=commands, paths=["src/a.py"], criteria=[{"id": "C1", "text": "x"}], steps=[])

        self.assertIsNone(test_loop.listing_problem(rows(2, 3)))
        nav._check_submitted_test_commands("step-plan", plan(rows(2, 3)))
        problem = test_loop.listing_problem(rows(6, 15))
        self.assertRegex(problem, r"renders to [\d,]+ bytes, but the test loop's contract holds only about [\d,]+")
        self.assertIn("shorten the ids lists", problem)
        with self.assertRaisesRegex(nav.NavigatorError, "test command list renders to"):
            nav._check_submitted_test_commands("step-plan", plan(rows(6, 15)))
        # the built contract for a list the check accepts stays inside the budget
        self.assertIsNone(test_loop.listing_problem(rows(3, 6)))
        self.assertIsNone(test_loop.listing_problem([]))
        # a malformed row is the shape check's to refuse, not this one's
        self.assertIsNone(test_loop.listing_problem([{"command": "pytest"}]))

    # -- contract and packet -------------------------------------------------------

    def test_each_stage_loops_on_its_exact_commands(self):
        self.start()
        self.drive_to("test-green")
        contract = json.loads((self.run_dir / test_loop.contract_path(self.action())).read_text())
        self.assertIn("Test command list:\n1. [focused] sh check.sh fixed.txt\n", contract["work"])
        self.assertNotIn("retained.txt", contract["work"])
        self.assertEqual(contract["exit_condition"], prompts.TEST_EXIT_CONDITION)
        self.assertEqual(contract["required_trivial_reviews"], 1)
        packet = self.packet()
        self.assertIn("Allowed outcomes: done | blocked | revise (", packet)
        self.assertIn("Test loop (bound Until Loop; the loop script counts iterations; there is no iteration limit):", packet)
        self.assertIn("  1. [focused] sh check.sh fixed.txt", packet)
        self.assertIn("ShipLoop checks the terminal packet against the contract and then runs every listed command",
                      " ".join(packet.split()))
        self.pass_loop()
        self.assertEqual(nav.current_stage(self.state()), "test-refine")
        self.drive_to("regression")
        contract = json.loads((self.run_dir / test_loop.contract_path(self.action())).read_text())
        self.assertIn("1. [focused] sh check.sh fixed.txt\n2. [regression] test -f retained.txt\n", contract["work"])

    def test_failing_tests_loop_until_fixed_then_the_script_accepts(self):
        self.start()
        self.drive_to("test-green")
        terminal = self.run_loop([MATERIAL, lambda: (self.repo / "fixed.txt").write_text("fixed\n"), TRIVIAL])
        self.assertEqual(terminal["status"], "complete")
        action = self.action()
        self.complete(dict(DONE, evidence_refs=[str(self.terminal())]))
        self.assertEqual(nav.current_stage(self.state()), "test-refine")
        record = store.read_record(self.run_dir / test_loop.verify_path(action, 1))
        self.assertTrue(record["passed"])
        self.assertEqual([(row["command"], row["exit"]) for row in record["runs"]], [("sh check.sh fixed.txt", 0)])

    def test_script_rerun_refuses_a_loop_that_claimed_green(self):
        self.start()
        self.drive_to("test-green")
        self.run_loop([TRIVIAL])  # claims every command passed; fixed.txt does not exist
        action = self.action()
        done = dict(DONE, evidence_refs=[str(self.terminal())])
        self.assert_refused(done, r"(?s)test-green is not done.*\[focused\] sh check.sh fixed.txt -> exit 1")
        record = store.read_record(self.run_dir / test_loop.verify_path(action, 1))
        self.assertFalse(record["passed"])
        (self.repo / "fixed.txt").write_text("fixed\n")
        # A complete packet never traps the step: blocked is still accepted.
        blocked = self.state()
        self.complete(dict(DONE, outcome="blocked", blocked_by="external", evidence_refs=[str(self.terminal())]))
        self.assertEqual(self.state()["status"], "blocked")
        nav.save(self.run_dir, blocked)
        self.complete(done)
        self.assertEqual(nav.current_stage(self.state()), "test-refine")
        self.assertTrue(store.read_record(self.run_dir / test_loop.verify_path(action, 2))["passed"])

    def test_results_the_terminal_packet_does_not_support_are_refused(self):
        self.start()
        self.drive_to("test-green")
        (self.repo / "fixed.txt").write_text("fixed\n")
        self.assert_refused(dict(DONE, outcome="repeat"), "accepts only done, revise or blocked")
        self.run_loop([TRIVIAL], contract_edit=lambda c: c.update(work="Run nothing."))
        self.assert_refused(dict(DONE, evidence_refs=[str(self.terminal())]),
                            "not from a run of this action's contract")
        self.run_loop([TRIVIAL])
        self.assert_refused(DONE, "list the saved terminal packet in evidence_refs")
        # No iteration limit: a long loop that ends complete is done.
        self.run_loop([MATERIAL] * 6 + [TRIVIAL])
        self.assert_refused(dict(DONE, outcome="revise", evidence_refs=[str(self.terminal())]),
                            "a complete test loop reports outcome done")
        self.complete(dict(DONE, evidence_refs=[str(self.terminal())]))
        self.assertEqual(nav.current_stage(self.state()), "test-refine")

    def test_stopped_loop_reports_blocked_and_runs_no_command(self):
        self.start()
        self.drive_to("test-green")
        stopped = self.run_loop([dict(MATERIAL, continuation_assessment="blocked")])
        self.assertEqual(stopped["status"], "stopped")
        with mock.patch.object(test_loop, "verify", side_effect=AssertionError("no command runs")):
            self.assert_refused(dict(DONE, evidence_refs=[str(self.terminal())]),
                                "a test loop stopped as blocked reports outcome blocked")
            self.complete(dict(DONE, outcome="blocked", blocked_by="external", evidence_refs=[str(self.terminal())]))
        self.assertEqual(self.state()["status"], "blocked")

    def test_an_empty_command_list_skips_the_loop_with_its_reason(self):
        self.start()
        # The declared path is code, so the test stages still run; the loop has nothing to run.
        self.drive_to("test-green", step_plan={"test_commands": [], "test_commands_na": "Docs-only item.",
                                               "paths": ["a.py"]})
        action = self.action()
        self.assertFalse((self.run_dir / test_loop.contract_path(action)).exists())
        self.assertIn("No command to run: Docs-only item. Report done with that reason", self.packet())
        self.complete(DONE)
        self.assertEqual(nav.current_stage(self.state()), "test-refine")
        self.assertFalse((self.run_dir / test_loop.verify_path(action, 1)).exists())

    def test_integrate_commits_the_items_declared_changes_and_names_the_rest(self):
        """Committing is mechanical: ShipLoop does it when integrate is accepted, not model shell."""
        self.start()
        self.drive_to("integrate")
        (self.repo / "a.py").write_text("x = 2\n")
        (self.repo / "server.log").write_text("listening 3000\n")
        before = git(self.repo, "rev-parse", "HEAD").strip()
        output = self.complete(DONE)
        head = git(self.repo, "rev-parse", "HEAD").strip()
        self.assertNotEqual(head, before)
        self.assertIn("ShipLoop committed W1's declared changes as " + head[:12], output)
        self.assertIn("a.py", git(self.repo, "show", "--name-only", "--format=", "HEAD").split())
        undeclared = next(line for line in output.splitlines() if line.startswith("Not committed"))
        self.assertIn("server.log", undeclared)
        self.assertNotIn("a.py", undeclared)
        self.assertIn("?? server.log", git(self.repo, "status", "--porcelain"))
        self.assertNotIn(" M a.py", git(self.repo, "status", "--porcelain"))

    NO_TESTS = {"test_commands": [], "test_commands_na": "Navigation metadata only.",
                "paths": ["force-app/main/default/tabs/Fleet_command.tab-meta.xml", "docs/fleet.md"]}

    def test_an_item_that_declares_only_non_code_paths_leaves_its_test_stages_out(self):
        self.start()
        self.drive_to("implement", step_plan=self.NO_TESTS)
        state = self.state()
        rows = [row for row in state["history"] if row["stage"] in item_scope.TEST_STAGES[:4]]
        self.assertEqual([row["stage"] for row in rows], ["test-spec", "baseline", "test-author", "test-red"])
        for row in rows:
            self.assertIn("Not applicable to this item", row["summary"])
            self.assertTrue((self.run_dir / "results" / (row["action"] + ".md")).is_file())
        step = next(row for row in state["history"] if row["stage"] == "step-plan")
        self.assertTrue((self.run_dir / "results" / (step["action"] + ".md")).is_file())
        tab = self.repo / "force-app/main/default/tabs/Fleet_command.tab-meta.xml"
        tab.parent.mkdir(parents=True)
        tab.write_text("<CustomTab/>\n")
        self.complete(DONE)
        self.assertEqual(nav.current_stage(self.state()), "document")
        later = [row["stage"] for row in self.state()["history"][-3:]]
        self.assertEqual(later, ["test-green", "test-refine", "regression"])

    def test_implement_outside_the_declared_non_code_paths_is_refused(self):
        self.start()
        self.drive_to("implement", step_plan=self.NO_TESTS)
        (self.repo / "a.py").write_text("x = 2\n")
        self.assert_refused(DONE, r"(?s)declared only non-code paths.*- a.py \(code\).*report blocked")
        (self.repo / "a.py").write_text("x = 1\n")
        (self.repo / "notes.txt").write_text("stray\n")
        self.assert_refused(DONE, r"- notes.txt \(code\)")  # a path no rule matches counts as code
        (self.repo / "notes.txt").unlink()
        (self.repo / "NOTES.md").write_text("stray\n")
        self.assert_refused(DONE, r"- NOTES.md \(not declared\)")
        (self.repo / "NOTES.md").unlink()
        self.complete(DONE)
        self.assertEqual(nav.current_stage(self.state()), "document")

    def test_a_release_plan_must_name_an_existing_consumer_entry(self):
        self.start()
        self.drive_to("release-plan")
        self.assert_refused(DONE, "must record consumer_entry")
        self.assert_refused(dict(DONE, consumer_entry={"how": "App Launcher: Fleet command",
                                                       "sources": ["force-app/main/default/tabs/Fleet.tab-meta.xml"]}),
                            "consumer_entry sources do not exist in the repository: force-app/main/default/tabs/")
        self.assert_refused(dict(DONE, consumer_entry={"how": "run the tool",
                                                       "sources": [str(self.repo / "missing.py")]}),
                            "must be repository-relative paths")  # refused by name, never globbed (pathlib raises)
        self.complete(dict(DONE, consumer_entry={"how": "run python3 a.py", "sources": ["a.py"]},
                           consumer_checks=[], consumer_checks_na="Synthetic fixture."))

    def test_outer_stages_after_a_non_code_replan_are_scoped_to_the_delta(self):
        self.start()
        self.drive_to("release-verify")
        self.complete(dict(DONE, outcome="replan", summary="No navigation entry.",
                           work_items=[{"id": "W2", "title": "Add the tab and app"}]))
        self.drive_to("system-test-author", step_plan=self.NO_TESTS)
        packet = self.packet()
        self.assertIn("Delta after the replan at release-verify: the corrective item W2 changed only non-code "
                      "paths: docs/fleet.md, force-app/main/default/tabs/Fleet_command.tab-meta.xml.", packet)
        self.assertRegex(packet, r"This stage's result before the replan: .*/results/nav-[0-9a-f]+\.md\. Keep its "
                                 r"evidence")

    def test_prepare_commits_the_repository_knowledge_home(self):
        self.start()
        self.drive_to("get-next-work-item")
        log = git(self.repo, "log", "--format=%s", "-n", "3")
        self.assertIn("docs(shiploop): record", log)
        self.assertIn("knowledge at prepare", log)
        self.assertIn("docs/shiploop/spec.md", git(self.repo, "ls-files", "docs/shiploop"))

    def test_a_done_step_plan_must_declare_its_paths(self):
        self.start()
        self.drive_to("step-plan")
        self.assert_refused(dict(DONE, test_commands=COMMANDS), "must list paths")
        self.assert_refused(dict(DONE, test_commands=COMMANDS, paths=["a.py"]), "must list criteria")
        self.assert_refused(dict(DONE, test_commands=COMMANDS, paths=["../x"]), "inside the repository")

    def test_without_a_bound_runtime_the_script_still_runs_the_commands(self):
        self.start()
        self.drive_to("test-green")
        state = self.state()
        state["improve_skill"] = ""  # a run whose card was never bound: no Until Loop runtime
        nav.save(self.run_dir, state)
        self.assertIn("Unavailable: no Improve card is bound", self.packet())
        self.assert_refused(DONE, r"sh check.sh fixed.txt -> exit 1")
        (self.repo / "fixed.txt").write_text("fixed\n")
        self.complete(DONE)
        self.assertEqual(nav.current_stage(self.state()), "test-refine")

    def test_stages_that_edit_code_rerun_every_command_before_done(self):
        self.start()
        for stage in test_loop.RERUN_STAGES:
            with self.subTest(stage=stage):
                self.drive_to(stage)
                self.assertIn("Test rerun: on done, ShipLoop runs every test command", self.packet())
                (self.repo / "retained.txt").unlink()  # this stage broke a regression test
                if stage == "static-checks":
                    self.run_quality_loop()
                    done = dict(DONE, evidence_refs=[str(self.run_dir / "quality" / (self.action()
                                                                                     + "-terminal.json"))])
                else:
                    done = DONE
                self.assert_refused(done, r"(?s)" + stage + r" is not done.*\[regression\] test -f retained.txt"
                                    r" -> exit 1.*Fix the code so every command passes")
                (self.repo / "retained.txt").write_text("retained\n")
                self.complete(done)
                self.assertNotEqual(nav.current_stage(self.state()), stage)

    def test_a_done_system_test_with_a_person_only_open_item_advances_and_still_reruns_the_commands(self):
        """a13, S-14: a person-only case is recorded as an open item in the result and never blocks done.

        The script still reruns the recorded system commands (S-9): the open item
        replaces no script-run check, and the next stage's packet carries it.
        """
        self.start()
        self.drive_to("system-test")
        action = self.action()
        # The rendered packet names the route the result below takes.
        self.assertIn("does not make this result blocked", " ".join(self.packet().split()))
        open_item = ("Open item SYS-RENDER-1 (required, person only; this host has no route): owner a person, "
                     "due handoff. Open the page in a signed-in browser, take one turn, report what shows. "
                     "Unverified.")
        (self.repo / "retained.txt").unlink()  # a recorded command fails: the open item cannot excuse it
        self.assert_refused(dict(DONE, summary=open_item),
                            r"(?s)system-test is not done.*\[regression\] test -f retained.txt -> exit 1")
        self.assertFalse(store.read_record(self.run_dir / test_loop.verify_path(action, 1))["passed"])
        (self.repo / "retained.txt").write_text("retained\n")
        self.complete(dict(DONE, summary=open_item))
        state = self.state()
        self.assertEqual(nav.current_stage(state), "product-acceptance")
        self.assertEqual(state["status"], "active")
        self.assertTrue(store.read_record(self.run_dir / test_loop.verify_path(action, 2))["passed"])
        self.assertIn("SYS-RENDER-1", self.packet())  # the last accepted summary reaches the next stage

    def test_after_seven_refused_runs_only_blocked_is_accepted(self):
        self.start()
        self.drive_to("test-refine")
        (self.repo / "retained.txt").unlink()
        for attempt in range(1, 8):
            self.assert_refused(DONE, "Refused runs for this action: " + str(attempt) + " of 7")
        (self.repo / "retained.txt").write_text("retained\n")  # even a now-passing tree
        with mock.patch.object(test_loop, "lint", wraps=test_loop.lint) as runner:
            self.assert_refused(DONE, "was refused 7 times; done is no longer accepted")
            runner.run_argv.assert_not_called()
        self.complete(dict(DONE, outcome="blocked", blocked_by="external"))
        self.assertEqual(self.state()["status"], "blocked")

    # -- the route out of a run that could not run ---------------------------------
    #
    # A refusal after a command timed out says "report revise" (INNER) or "replan" (OUTER).
    # These submit that outcome through the navigator with the real Until Loop, because the
    # text alone once named a route the navigator refused at test-green, regression and
    # static-checks.

    TIMED_OUT = ("timeout", None, b"partial output\n", b"")

    def restart(self) -> None:
        """A fresh run in this test's own temporary repository (earlier subtests leave no files behind)."""
        for name in os.listdir(self.run_dir):
            path = self.run_dir / name
            shutil.rmtree(path) if path.is_dir() else path.unlink()
        for name in ("fixed.txt", "retained.txt"):
            (self.repo / name).unlink(missing_ok=True)
        self.start()

    def quality_refs(self) -> list:
        return [str(self.run_dir / "quality" / (self.action() + "-terminal.json"))]

    def refuse_unrunnable(self, done: dict, attempts: int = 1) -> None:
        """ShipLoop's own rerun of the recorded commands times out ``attempts`` times; each refuses done."""
        action = self.action()
        for number in range(1, attempts + 1):
            with mock.patch.object(test_loop.lint, "run_argv", return_value=self.TIMED_OUT):
                self.assert_refused(done, "timed out, so it reached no verdict")
            record = store.read_record(self.run_dir / test_loop.verify_path(action, number))
            self.assertEqual(record["disposition"], "could-not-run")
        self.assertEqual(test_loop.refused_runs(self.run_dir, action), 0)  # the cap never advances

    def test_revise_is_accepted_at_the_test_loop_stages_after_a_could_not_run_attempt(self):
        for stage in test_loop.STAGES:
            with self.subTest(stage=stage):
                self.restart()
                self.drive_to(stage)
                (self.repo / "fixed.txt").write_text("fixed\n")
                (self.repo / "retained.txt").write_text("retained\n")
                self.run_loop([TRIVIAL])
                done = dict(DONE, evidence_refs=[str(self.terminal())])
                revise = dict(done, outcome="revise")
                # Before ShipLoop has any record, a complete loop supports only done.
                self.assert_refused(revise, "a complete test loop reports outcome done")
                self.refuse_unrunnable(done, attempts=3)
                self.complete(revise)  # the route the refusal names
                self.assertEqual(nav.current_stage(self.state()), "step-plan")

    def test_a_failed_run_does_not_open_revise_before_the_cap_and_a_complete_loop_still_needs_done(self):
        self.start()
        self.drive_to("test-green")
        self.run_loop([TRIVIAL])  # complete, but fixed.txt is missing, so ShipLoop's own run fails
        done = dict(DONE, evidence_refs=[str(self.terminal())])
        self.assert_refused(done, r"Refused runs for this action: 1 of 7")
        self.assertEqual(test_loop.refused_runs(self.run_dir, self.action()), 1)
        self.assert_refused(dict(done, outcome="revise"), "a complete test loop reports outcome done")
        (self.repo / "fixed.txt").write_text("fixed\n")
        self.complete(done)
        self.assertEqual(nav.current_stage(self.state()), "test-refine")

    def test_a_later_failed_run_closes_the_could_not_run_route(self):
        """Only ShipLoop's latest record counts: a product failure after a hang is a product failure."""
        self.start()
        self.drive_to("test-green")
        self.run_loop([TRIVIAL])
        done = dict(DONE, evidence_refs=[str(self.terminal())])
        self.refuse_unrunnable(done)
        self.assert_refused(done, r"Refused runs for this action: 1 of 7")  # fixed.txt missing: a real failure
        self.assert_refused(dict(done, outcome="revise"), "a complete test loop reports outcome done")

    def test_revise_and_blocked_are_accepted_at_static_checks_after_a_could_not_run_attempt(self):
        for outcome in ("revise", "blocked"):
            with self.subTest(outcome=outcome):
                self.restart()
                self.drive_to("static-checks")
                self.run_quality_loop()
                done = dict(DONE, evidence_refs=self.quality_refs())
                chosen = dict(done, outcome=outcome, **({"blocked_by": "external"} if outcome == "blocked" else {}))
                self.assert_refused(chosen, "a complete quality loop reports outcome done")  # no record yet
                self.refuse_unrunnable(done, attempts=2)
                self.complete(chosen)
                if outcome == "revise":
                    self.assertEqual(nav.current_stage(self.state()), "step-plan")
                else:
                    self.assertEqual(self.state()["status"], "blocked")

    def test_revise_is_accepted_at_static_checks_after_the_cap_the_refusal_names(self):
        """After 7 refused runs `verify` says "Report outcome revise"; the quality gate must accept it."""
        self.start()
        self.drive_to("static-checks")
        self.run_quality_loop()
        done = dict(DONE, evidence_refs=self.quality_refs())
        (self.repo / "retained.txt").unlink()  # a regression command fails on every run
        for attempt in range(1, test_loop.MAX_REFUSED_RUNS + 1):
            self.assert_refused(done, "Refused runs for this action: " + str(attempt) + " of 7")
        self.assert_refused(done, "was refused 7 times; done is no longer accepted")
        self.complete(dict(done, outcome="revise"))  # the route the refusal names
        self.assertEqual(nav.current_stage(self.state()), "step-plan")

    def test_the_remedy_outcome_is_accepted_at_every_stage_after_a_could_not_run_attempt(self):
        """Guard: stages with no loop packet already accepted their remedy; the outer ones need work_items."""
        corrective = [{"id": "W2", "title": "Make the recorded command fit its budget"}]
        for stage in ("test-refine", "verify", "integration-verify", "system-test", "release-verify"):
            with self.subTest(stage=stage):
                self.restart()
                self.drive_to(stage)
                self.refuse_unrunnable(DONE)
                if stage in ("system-test", "release-verify"):
                    self.complete(dict(DONE, outcome="replan", work_items=corrective))
                    self.assertIn("W2", [row["id"] for row in self.state()["work_items"]])
                else:
                    self.complete(dict(DONE, outcome="revise"))
                    self.assertEqual(nav.current_stage(self.state()), "step-plan")

    def test_test_red_runs_the_focused_commands_and_expects_a_failing_test(self):
        self.start()
        self.drive_to("test-red")
        self.assertIn("Expected-RED run: on done, ShipLoop runs each focused command", self.packet())
        (self.repo / "fixed.txt").write_text("already\n")  # the new test passes before implementation
        self.assert_refused(DONE, r"(?s)test-red is not done.*did not fail as expected.*passed, but test-red "
                                  r"expects the new tests to fail")
        (self.repo / "fixed.txt").unlink()
        action = self.action()
        self.complete(DONE)
        self.assertEqual(nav.current_stage(self.state()), "implement")
        record = store.read_record(self.run_dir / test_loop.verify_path(action, 2))
        self.assertTrue(record["passed"])
        self.assertEqual(record["expect"], "red")
        self.assertEqual(record["runs"][0]["status"], "red")

    def test_red_na_expects_the_tests_to_pass_and_to_have_run(self):
        self.start()
        self.drive_to("test-red")
        characterise = dict(DONE, red_na="characterisation tests of existing behaviour")
        self.assert_refused(characterise, r"sh check.sh fixed.txt -> exit 1")
        (self.repo / "fixed.txt").write_text("existing\n")
        self.complete(characterise)
        self.assertEqual(nav.current_stage(self.state()), "implement")
        with self.assertRaisesRegex(nav.NavigatorError, "red_na is allowed only on a done test-red result"):
            nav._canonical_result(characterise, stage="test-green")

    # -- the test-author probe -------------------------------------------------------
    #
    # test-author's own done-when is "each case has a test the focused command runs", and nothing checked it: a
    # test file that loads something the item creates died before any test ran, the host reported test-author done,
    # and test-red (which forbids product edits) was the first stage that could notice.  ShipLoop now runs the
    # focused commands once at test-author's done and accepts only when a test ran: exit 0 needs a counted test (and
    # every listed ID shown), a non-zero exit needs a failing test inside a test.  The refusal comes where creating
    # the smallest loadable placeholder is allowed.

    def probe_item(self, ids=None, **row_extra) -> dict:
        """A step plan whose one focused command is ``sh run.sh`` (the test writes run.sh) and one regression command."""
        row = dict({"command": "sh run.sh", "suite": "focused"}, **row_extra)
        if ids:
            row["ids"] = ids
        return {"test_commands": [row, COMMANDS[1]], "paths": ["a.py"]}

    PROBE_CASES = (
        # The recorded outputs of the design's judge table plus the other refusal statuses.  The first draft judged
        # every exit code in red mode and so accepted the 1st and 2nd rows (an exit-0 run that ran nothing).
        dict(name="exit 0, no countable output", code=0, out="", status="uncounted", accepted=False),
        dict(name="exit 0, a listed ID never shown", ids=["TC-1"], code=0, out="all good\n", status="ids-missing",
             accepted=False),
        dict(name="exit 0, two tests ran", code=0, out=UNITTEST_OK, status="passed", accepted=True),
        dict(name="exit 0, zero tests ran", code=0, out=UNITTEST_ZERO, status="no-tests", accepted=False),
        dict(name="exit 0, fewer tests than min_tests", row=dict(min_tests=3), code=0, out=UNITTEST_OK,
             status="too-few-tests", accepted=False),
        dict(name="exit 1, a load failure before any test, no ids", code=1, out=NODE_LOAD_FAILURE,
             status="no-tests", accepted=False),
        dict(name="exit 1, a load failure before any test, ids listed", ids=["TC-01"], code=1,
             out=NODE_LOAD_FAILURE, status="no-tests", accepted=False),
        dict(name="exit 1, tests ran and none failed", code=1, out=UNITTEST_OK, status="not-red", accepted=False),
        dict(name="exit 1, one failing test", code=1, out=UNITTEST_FAIL, status="red", accepted=True),
        dict(name="exit 1, a failing test named by its ID", ids=["TC-01", "TC-02"], code=1, out=NODE_ONE_FAILING,
             status="red", accepted=True),
        # The runner every Python project has: its loader reports a module it cannot import as a test that errored.
        dict(name="exit 1, a unittest module that cannot be imported, no ids", code=1, out=UNITTEST_LOAD_FAILURE,
             status="no-tests", accepted=False),
        dict(name="exit 1, one unittest module loads and passes, another cannot be imported", code=1,
             out=UNITTEST_ONE_MODULE_LOADS, status="not-red", accepted=False),
        dict(name="exit 1, known limit: a failing test and an unimportable module in one command, no ids", code=1,
             out=UNITTEST_FAILING_AND_UNLOADABLE, status="red", accepted=True),
    )

    def test_the_probe_accepts_a_run_only_when_a_test_ran(self):
        for case in self.PROBE_CASES:
            with self.subTest(case["name"]):
                self.restart()
                self.drive_to("test-author", step_plan=self.probe_item(case.get("ids"), **case.get("row", {})))
                action = self.action()
                canned = ("passed" if case["code"] == 0 else "failed", case["code"], case["out"].encode(), b"")
                with mock.patch.object(test_loop.lint, "run_argv", return_value=canned):
                    if case["accepted"]:
                        self.complete(DONE)
                        self.assertEqual(nav.current_stage(self.state()), "test-red")
                    else:
                        self.assert_refused(DONE, r"test-author is not done")
                record = store.read_record(self.run_dir / test_loop.verify_path(action, 1))
                self.assertEqual(record["stage"], "test-author")
                self.assertEqual(record["runs"][0]["status"], case["status"])
                self.assertEqual(record["passed"], case["accepted"])
                self.assertEqual(record["expect"], "a test ran")
                self.assertEqual([row["command"] for row in record["runs"]], ["sh run.sh"])  # focused only

    def test_a_load_failure_is_refused_with_the_placeholder_rule_until_the_file_exists(self):
        """The defect class: tests load a file the item creates, the file is missing, no test runs."""
        self.start()
        (self.repo / "run.sh").write_text(LOADER)
        self.drive_to("test-author", step_plan=self.probe_item())
        action = self.action()
        with self.assertRaises(nav.NavigatorError) as raised:
            self.complete(DONE)
        refusal = str(raised.exception)
        self.assertRegex(refusal, r"(?s)test-author is not done.*did not show a usable test run.*\[focused\] sh run.sh -> ")
        self.assertIn("Cannot find module './widgets'", refusal)  # the runner's own tail, as at every stage
        flat = " ".join(refusal.split())
        self.assertIn(test_loop.PROBE_RULE, flat)
        self.assertIn("smallest loadable placeholder", flat)
        self.assertIn("`paths`", flat)
        self.assertIn("Refused runs for this action: 1 of 7; after that the item goes back to its step plan (revise).",
                      flat)
        # Not the wording of the stage that forbids product edits: the way out here is to create the file.
        self.assertNotIn("did not fail as expected", flat)
        self.assertNotIn("not the product code", flat)
        self.assertEqual(nav.current_stage(self.state()), "test-author")
        (self.repo / "widgets.txt").write_text("created at test-author\n")  # the placeholder
        self.complete(DONE)  # the same result, now accepted
        self.assertEqual(nav.current_stage(self.state()), "test-red")
        record = store.read_record(self.run_dir / test_loop.verify_path(action, 2))
        self.assertTrue(record["passed"])
        self.assertEqual(record["runs"][0]["status"], "passed")

    def test_after_seven_refused_probe_runs_done_is_refused_and_revise_is_accepted(self):
        self.start()
        (self.repo / "run.sh").write_text(LOADER)
        self.drive_to("test-author", step_plan=self.probe_item())
        for attempt in range(1, test_loop.MAX_REFUSED_RUNS + 1):
            self.assert_refused(DONE, "Refused runs for this action: " + str(attempt) + " of 7")
        (self.repo / "widgets.txt").write_text("created too late\n")  # even a now-passing tree
        with mock.patch.object(test_loop, "lint", wraps=test_loop.lint) as runner:
            self.assert_refused(DONE, r"test-author was refused 7 times; done is no longer accepted for this action"
                                      r"\. Report outcome revise, naming the failing command")
            runner.run_argv.assert_not_called()
        self.complete(dict(DONE, outcome="revise"))  # the named remedy, through the same gate
        self.assertEqual(nav.current_stage(self.state()), "step-plan")

    def test_a_probe_command_that_reaches_no_verdict_is_refused_without_spending_a_refused_run(self):
        self.start()
        self.drive_to("test-author")
        self.refuse_unrunnable(DONE, attempts=2)
        self.complete(dict(DONE, outcome="revise"))  # revise stays open on ShipLoop's own record
        self.assertEqual(nav.current_stage(self.state()), "step-plan")

    def test_a_probe_attempt_that_reached_no_verdict_names_its_own_fix_and_not_the_placeholder_rule(self):
        """The rule is about what the tests load; a run that never reached a verdict has nothing to say about that."""
        self.start()
        self.drive_to("test-author")
        with mock.patch.object(test_loop.lint, "run_argv", return_value=self.TIMED_OUT):
            with self.assertRaises(nav.NavigatorError) as raised:
                self.complete(DONE)
        flat = " ".join(str(raised.exception).split())
        self.assertNotIn(test_loop.PROBE_RULE, flat)
        self.assertIn("this item's own test or fixture is yours to fix here", flat)  # the stage forbids product edits
        self.assertNotIn("own code, test or fixture", flat)

    def test_a_probe_refusal_for_a_run_in_which_tests_ran_does_not_say_none_ran(self):
        """E2: exit 1 with only passing tests is refused, but the tests ran: the header and the reason must not say
        otherwise, and must not tell the author to make a passing test fail (test-author accepts a counted pass)."""
        self.start()
        self.drive_to("test-author", step_plan=self.probe_item())
        with mock.patch.object(test_loop.lint, "run_argv", return_value=("failed", 1, UNITTEST_OK.encode(), b"")):
            with self.assertRaises(nav.NavigatorError) as raised:
                self.complete(DONE)
        flat = " ".join(str(raised.exception).split())
        self.assertNotIn("did not run a test", flat)
        self.assertNotIn("fail on the missing behaviour", flat)
        self.assertIn("exited non-zero but no test failed (unittest reported 2 run, 0 failed)", flat)
        self.assertIn("Make the command exit 0 when its tests pass, or fail inside a test.", flat)
        # test-red keeps its own wording: there a passing run is the defect
        self.assertIn("fail on the missing behaviour", test_loop._explain(
            {"status": "not-red", "counts": {"runners": ["unittest"], "ran": 2, "failed": 0}}, test_loop.RED_STAGE))

    def test_the_probe_never_gates_an_outcome_other_than_done(self):
        """GUARD (passes on the unchanged tree): the host can always revise or block, so no command runs for them."""
        for outcome, extra in (("revise", {}), ("blocked", {"blocked_by": "external"})):
            with self.subTest(outcome=outcome):
                self.restart()
                (self.repo / "run.sh").write_text(LOADER)
                self.drive_to("test-author", step_plan=self.probe_item())
                with mock.patch.object(test_loop, "verify", side_effect=AssertionError("no command runs")):
                    self.complete(dict(DONE, outcome=outcome, **extra))
                self.assertEqual(self.state()["status"], "active" if outcome == "revise" else "blocked")

    def test_the_probe_accepts_a_real_failing_test_and_a_real_counted_pass(self):
        """GUARD (passes on the unchanged tree): the probe refuses only a run in which no test ran, never a test
        that fails (the usual RED at test-author) or one that already passes (characterisation tests)."""
        for name, fixed in (("a failing test", False), ("a counted pass", True)):
            with self.subTest(name):
                self.restart()
                self.drive_to("test-author")  # the default focused command is `sh check.sh fixed.txt`
                if fixed:
                    (self.repo / "fixed.txt").write_text("fixed\n")
                self.complete(DONE)
                self.assertEqual(nav.current_stage(self.state()), "test-red")

    def test_an_item_with_no_focused_command_has_nothing_to_probe(self):
        """GUARD (passes on the unchanged tree): no focused command, no probe, and no record."""
        for name, plan in (("test_commands_na", {"test_commands": [], "test_commands_na": "Docs-only item.",
                                                 "paths": ["a.py"]}),
                           ("regression only", {"test_commands": [COMMANDS[1]], "paths": ["a.py"]})):
            with self.subTest(name):
                self.restart()
                self.drive_to("test-author", step_plan=plan)
                action = self.action()
                self.complete(DONE)
                self.assertEqual(nav.current_stage(self.state()), "test-red")
                self.assertFalse((self.run_dir / test_loop.verify_path(action, 1)).exists())

    def test_the_judge_reads_recorded_node_output_as_a_load_failure(self):
        """A file that fails to load is one synthetic failing test named by its path; no test of it ran, so it reads as
        zero tests with or without listed IDs (before the node reader the same output was uncounted or ids-missing)."""
        self.assertEqual(test_loop.counts.count(NODE_LOAD_FAILURE, 1)["ran"], 0)
        focused = {"suite": "focused", "command": "x"}
        listed = dict(focused, ids=["TC-01"])
        self.assertEqual(test_loop.judge(focused, 1, NODE_LOAD_FAILURE, red=True)["status"], "no-tests")
        self.assertEqual(test_loop.judge(listed, 1, NODE_LOAD_FAILURE, red=True)["status"], "no-tests")
        self.assertEqual(test_loop.judge(listed, 1, NODE_ONE_FAILING, red=True)["status"], "red")

    def test_the_judge_reads_recorded_unittest_load_failure_as_no_test_ran(self):
        """The unittest counterpart of the Node characterisation above: no ID is listed, so only the count refuses it."""
        focused = {"suite": "focused", "command": "x"}
        self.assertEqual(test_loop.counts.count(UNITTEST_LOAD_FAILURE, 1)["ran"], 0)
        self.assertEqual(test_loop.judge(focused, 1, UNITTEST_LOAD_FAILURE, red=True)["status"], "no-tests")
        self.assertEqual(test_loop.judge(focused, 1, UNITTEST_LOAD_FAILURE)["status"], "no-tests")  # test-green too

    def test_the_probe_rule_and_the_two_duty_sentences_name_no_technology(self):
        """S-8: the engine's prose speaks of a file or module and a test, never of a runner, a language or a product."""
        texts = [test_loop.PROBE_RULE]
        for stage, first, last in (("test-author", "On done, ShipLoop runs the item's focused commands once",
                                    "fails that test and not the run."),
                                   ("step-plan", "A test that loads something this item creates",
                                    "fails a test and not the whole run.")):
            duty = " ".join(prompts.duty(stage).split())
            self.assertIn(first, duty)
            texts.append(duty[duty.index(first):duty.index(last) + len(last)])
        for text in texts:
            for word in ("node", "npm", "jest", "pytest", "python", "javascript", "java ", "game", "widget"):
                self.assertNotIn(word, text.lower(), word)

    def run_quality_loop(self) -> None:
        """One trivial quality-loop iteration, saved to the static-checks terminal path."""
        start = next(line for line in self.packet().splitlines() if line.startswith("Start: "))
        words = shlex.split(start[len("Start: "):])
        packet = json.loads(subprocess.run(words[:-2], input=Path(words[-1]).read_text(), text=True,
                                           capture_output=True, check=True, timeout=30).stdout)
        raw = subprocess.run(packet["done_argv"], input=json.dumps(TRIVIAL), text=True,
                             capture_output=True, check=True, timeout=30).stdout
        saved = self.run_dir / "quality" / (self.action() + "-terminal.json")
        self.assertEqual(json.loads(saved.read_text()), json.loads(raw))


class VerifyLimitTests(unittest.TestCase):
    def state(self, repo: Path, command: str) -> dict:
        return {"repo": str(repo), "history": [{"stage": "step-plan", "workitem": "W1", "action": "S1"}],
                "accepted": {"S1": dict(DONE, test_commands=[{"command": command, "suite": "focused"}])}}

    def test_a_command_past_its_timeout_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            writes, refusal = test_loop.verify(root, self.state(root, "sleep 5"), "W1", "A1", "test-green",
                                               command_timeout=0.5)
        self.assertIn("[focused] sleep 5 -> timed out", refusal)
        self.assertIn("tests/A1-verify1.md", writes)

    def test_a_zero_test_run_is_refused_with_the_ids_to_show(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = self.state(root, "echo 'Tests:       2 skipped, 2 total'")
            state["accepted"]["S1"]["test_commands"][0]["ids"] = ["TC-9", "TC-10"]
            writes, refusal = test_loop.verify(root, state, "W1", "A1", "test-green")
            record = store.loads(writes["tests/A1-verify1.md"])
        self.assertEqual(record["runs"][0]["status"], "no-tests")
        self.assertRegex(refusal, r"ran no tests \(jest reported 0 run, 0 failed\).*so the output names TC-9, TC-10")
        self.assertIn("running the whole suite instead does not satisfy this", refusal)
        for red_na in (None, "characterisation"):
            with self.subTest(red_na=red_na), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                _writes, refusal = test_loop.verify(root, self.state(root, "echo 'Tests:       2 skipped, 2 total'"),
                                                    "W1", "A1", "test-red", red_na=red_na)
                self.assertIn("ran no tests", refusal)

    def test_a_spent_stage_budget_skips_and_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _writes, refusal = test_loop.verify(root, self.state(root, "true"), "W1", "A1", "test-green",
                                                budget=0.5)
        self.assertIn("[focused] true -> skipped", refusal)


class UnavailableExecutionTests(unittest.TestCase):
    """A command that never reached a verdict refuses its stage without blaming the product.

    Each case writes its own record through the real ``verify``, so the recorded
    disposition and the refusal text are checked together.
    """

    def state(self, repo: Path, *commands: str) -> dict:
        """A state whose INNER step plan and both OUTER sources record the same commands.

        The outer verify stages take their commands from ``system-test-author``
        and ``release-plan``, not from the step plan, so every VERIFY_STAGES
        case needs all three seeded.
        """
        rows = [{"command": command, "suite": "focused"} for command in commands]
        regression = [dict(row, suite="regression") for row in rows]
        return {"repo": str(repo),
                "history": [{"stage": "step-plan", "workitem": "W1", "action": "S1", "outcome": "done"},
                            {"stage": "system-test-author", "workitem": None, "action": "S2",
                             "outcome": "done"},
                            {"stage": "release-plan", "workitem": None, "action": "S3", "outcome": "done"}],
                "accepted": {"S1": dict(DONE, test_commands=rows),
                             "S2": dict(DONE, system_commands=regression),
                             "S3": dict(DONE, consumer_checks=regression)}}

    def record(self, writes: dict, number: int = 1) -> dict:
        return store.loads(writes["tests/A1-verify" + str(number) + ".md"])

    def test_a_command_that_cannot_start_is_recorded_as_error_not_as_a_test_failure(self):
        def explode(*_args, **_kwargs):
            raise OSError("no such interpreter")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            writes, refusal = test_loop.verify(root, self.state(root, "pytest -q"), "W1", "A1", "test-green",
                                               runner=explode)
            record = self.record(writes)
            for relative, text in writes.items():
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text(text)
            self.assertEqual(test_loop.refused_runs(root, "A1"), 0)
        self.assertEqual(record["runs"][0]["status"], "error")
        self.assertEqual(record["disposition"], "could-not-run")
        self.assertFalse(record["passed"])
        self.assertIn("could not start", refusal)
        self.assertIn("says nothing about the product", refusal)

    def assert_unavailable(self, root: Path, stage: str, **kwargs) -> str:
        """Run one attempt that cannot reach a verdict; return its refusal text."""
        writes, refusal = test_loop.verify(root, self.state(root, "sleep 5"), "W1", "A1", stage, **kwargs)
        record = self.record(writes, test_loop._verify_count(root, "A1") + 1)
        self.assertEqual(record["disposition"], "could-not-run")
        for relative, text in writes.items():
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_text(text)
        return refusal

    def test_unavailable_attempts_never_reach_the_refused_run_cap(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for _attempt in range(test_loop.MAX_REFUSED_RUNS + 3):
                refusal = self.assert_unavailable(root, "test-green", command_timeout=0.2)
                self.assertIn("does not count toward the 7 refused runs", refusal)
                self.assertEqual(test_loop.refused_runs(root, "A1"), 0)
            # The gate never closed, so ShipLoop still runs the commands.
            self.assertNotIn("done is no longer accepted", refusal)

    def test_an_always_unavailable_command_is_given_routes_out_not_a_dead_end(self):
        """The gate cannot fire on could-not-run attempts, so the packet must name the exits.

        Otherwise a command that always hangs loops forever: it can never pass,
        its own hang is run-fixable so `blocked` would be illegal, and the
        refusal cap it would need to reach the stage's remedy never advances.
        """
        for stage, remedy in (("test-green", "revise"), ("system-test", "replan")):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                _writes, refusal = test_loop.verify(root, self.state(root, "sleep 5"), "W1", "A1", stage,
                                                    command_timeout=0.2)
                self.assertIn("is yours to fix here and is not a blocker", refusal)
                self.assertIn("report " + remedy + " rather than retrying it", refusal)
                self.assertIn("blocked only for what the user, an access grant or an outside dependency",
                              refusal)
                self.assertNotIn("step plan's command", refusal)  # outer stages have no step plan

    def test_a_real_failure_beside_a_timeout_is_still_a_product_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            writes, refusal = test_loop.verify(root, self.state(root, "false", "sleep 5"), "W1", "A1",
                                               "test-green", command_timeout=0.2)
            record = self.record(writes)
            for relative, text in writes.items():
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text(text)
            self.assertEqual(test_loop.refused_runs(root, "A1"), 1)
        self.assertEqual(record["disposition"], "failed")
        self.assertIn("Refused runs for this action: 1 of 7", refusal)
        self.assertNotIn("does not count toward", refusal)

    def test_the_remedy_named_at_the_cap_is_the_one_its_stage_allows(self):
        for stage in test_loop.VERIFY_STAGES:
            outcomes = stage_spec.STAGE_SPEC[stage].outcomes
            expected = "revise" if "revise" in outcomes else "replan"
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                (root / "tests").mkdir()
                for number in range(1, test_loop.MAX_REFUSED_RUNS + 1):
                    store.write_record(root / test_loop.verify_path("A1", number),
                                       {"schema": test_loop.SCHEMA, "passed": False, "disposition": "failed",
                                        "runs": [{"status": "failed"}]})
                writes, refusal = test_loop.verify(root, self.state(root, "true"), "W1", "A1", stage)
                self.assertEqual(writes, {})  # the gate refuses before running anything
                self.assertIn("was refused 7 times; done is no longer accepted", refusal)
                self.assertIn("Report outcome " + expected, refusal)
                self.assertNotIn("Report outcome " + ("replan" if expected == "revise" else "revise"), refusal)
                self.assertIn(expected, stage_spec.STAGE_SPEC[stage].outcomes)
                if expected == "replan":
                    self.assertIn("corrective work_items", refusal)

    def test_a_label_that_is_not_a_graph_stage_has_no_remedy_and_does_not_raise(self):
        """`verify` is also called with the navigator's `end-of-work review` gate label.

        It is not in STAGE_SPEC, so looking its outcomes up by subscript raised
        KeyError and broke the gate (caught by shiploop-improve-changes, not by
        this file's own stages).
        """
        self.assertEqual(test_loop._remedy("end-of-work review"), "")
        self.assertEqual(test_loop._remedy_sentence("end-of-work review"),
                         "done is no longer accepted for this action")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            commands = [{"command": "false", "suite": "regression"}]
            writes, refusal = test_loop.verify(root, self.state(root, "false"), "", "A1",
                                               "end-of-work review", commands=commands)
            self.assertIn("tests/A1-verify1.md", writes)
            self.assertIn("end-of-work review is not done", refusal)
            # A failing run is fixable, so the text never offers blocked as where a failure ends.
            self.assertNotIn("reports blocked", refusal)
            self.assertIn("Refused runs for this action: 1 of 7; after that done is no longer accepted", refusal)
            # No remedy outcome is named for something that is not a graph stage.
            self.assertNotIn("revise", refusal)
            self.assertNotIn("replan", refusal)

    def test_an_uncounted_command_names_the_exit_its_stage_has(self):
        """The outer stages cannot edit a recorded command: they are told replan and suite check, naming the recorder."""
        pipeline = [{"command": "echo ok | grep -q ok", "suite": "focused"}]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for stage, source, field in (("system-test", "system-test-author", "system_commands"),
                                         ("release-verify", "release-plan", "consumer_checks")):
                with self.subTest(stage=stage):
                    _writes, refusal = test_loop.verify(root, self.state(root, "true"), "", "A-" + stage, stage,
                                                        commands=pipeline)
                    self.assertIn(source + " recorded this command and " + stage + " cannot edit it", refusal)
                    self.assertIn("belongs in suite `check`, judged by its exit code", refusal)
                    self.assertIn("Report outcome replan now, with one corrective work item", refusal)
                    self.assertIn("as suite check in " + field + ". The outer stages then run again, and "
                                  + source + " records it.", refusal)
                    self.assertNotIn("Give the command ids", refusal)
                    self.assertNotIn("Fix the code so every command passes", refusal)
                    self.assertIn("Report replan as named above, not done", refusal)
            # A stage that does not take commands from an outer recorder keeps the ids-and-flag reply, plus check.
            for stage in ("test-green", "test-refine", "end-of-work review"):
                with self.subTest(stage=stage):
                    _writes, refusal = test_loop.verify(root, self.state(root, "true"), "", "A-" + stage, stage,
                                                        commands=pipeline)
                    self.assertIn("Give the command ids and a runner flag that prints test names", refusal)
                    self.assertIn("for a command that is not a test runner, record it as suite `check`", refusal)
                    self.assertNotIn("Report outcome replan now", refusal)
            # One counted failure beside an uncounted command: the code can still be at fault, so the fix line stays.
            both = [*pipeline, {"command": "echo '=== 1 failed in 0.01s ==='; exit 1", "suite": "focused"}]
            _writes, refusal = test_loop.verify(root, self.state(root, "true"), "", "A-both", "system-test",
                                                commands=both)
            self.assertIn("Report outcome replan now", refusal)
            self.assertIn("Fix the code so every command passes", refusal)
            self.assertNotIn("Report replan as named above, not done", refusal)

    def test_the_rerun_packet_names_its_own_stage_remedy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = self.state(root, "true")
            self.assertIn("the item goes back to its step plan (revise)",
                          "\n".join(test_loop.rerun_lines(state, "W1", "test-refine")))
            outer = "\n".join(test_loop.rerun_lines(state, "W1", "system-test"))
            self.assertIn("the outer loop takes corrective work items (replan)", outer)
            self.assertNotIn("step plan (revise)", outer)

    def test_the_rerun_packet_names_where_its_commands_were_recorded(self):
        """The outer stages have no step plan: their commands come from system-test-author and release-plan."""
        with tempfile.TemporaryDirectory() as temp:
            state = self.state(Path(temp), "true")
            for stage, source in (("test-refine", "the step plan"), ("verify", "the step plan"),
                                  ("system-test", "system-test-author"), ("release-verify", "release-plan")):
                with self.subTest(stage=stage):
                    packet = "\n".join(test_loop.rerun_lines(state, "W1", stage))
                    self.assertIn("runs every test command " + source + " recorded from", packet)
            self.assertNotIn("the step plan recorded",
                             "\n".join(test_loop.rerun_lines(state, "W1", "system-test")))

    # -- budget-skipped commands, and records written before the disposition field ---

    class Clock:
        """A fake clock the runner advances, so a run can spend its whole budget in no real time."""

        now = 0.0

        def __call__(self) -> float:
            return self.now

    def slow_passing_attempt(self, root: Path, stage: str = "test-green") -> tuple:
        """Five commands that each pass in 500 s against an 1800 s budget: the last never starts."""
        clock = self.Clock()

        def passes_slowly(*_args, **_kwargs):
            clock.now += 500.0
            return "passed", 0, b"Ran 1 test in 0.001s\nOK\n", b""

        state = self.state(root, *("true " + str(number) for number in range(5)))
        writes, refusal = test_loop.verify(root, state, "W1", "A1", stage, runner=passes_slowly, clock=clock)
        for relative, text in writes.items():
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_text(text)
        return self.record(writes, test_loop._verify_count(root, "A1")), refusal

    def test_a_command_skipped_for_budget_is_could_not_run_and_never_reaches_the_cap(self):
        """A budget skip is deterministic: the same tail is skipped on every attempt, so it must not count."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for _attempt in range(test_loop.MAX_REFUSED_RUNS + 2):
                record, refusal = self.slow_passing_attempt(root)
                self.assertEqual([run["status"] for run in record["runs"]],
                                 ["passed", "passed", "passed", "passed", "skipped"])
                self.assertEqual(record["disposition"], "could-not-run")
                self.assertFalse(record["passed"])
                self.assertEqual(test_loop.refused_runs(root, "A1"), 0)
            self.assertIn("does not count toward the 7 refused runs", refusal)
            self.assertNotIn("done is no longer accepted", refusal)

    def test_a_budget_skip_names_the_budget_and_a_route_that_can_change_it(self):
        """The model cannot raise the budget; it can record commands that fit, which is the stage's remedy."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            record, refusal = self.slow_passing_attempt(root)
            skipped = record["runs"][-1]
            self.assertIn("1800-second budget of this ShipLoop test run ran out before this command started",
                          skipped["stderr"])
            self.assertNotIn("stage budget", skipped["stderr"])
            self.assertIn("A skipped command never started", refusal)
            self.assertIn("a retry skips it again", refusal)
            self.assertIn("too slow to fit (600 seconds each, 1800 for the whole run), report revise rather "
                          "than retrying it", refusal)
            self.assertIn("ShipLoop's own record of this attempt is the evidence, so no new loop packet", refusal)
            _record, outer = self.slow_passing_attempt(Path(temp) / "outer", "system-test")
            self.assertIn("report replan rather than retrying it, with the corrective work_items", outer)
            self.assertNotIn("no new loop packet", outer)  # the outer stages run no loop

    def test_a_timeout_text_does_not_ask_for_product_code_at_test_red(self):
        """test-red fixes the tests, not the product, so a hang there is the test's or the fixture's own."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _writes, red = test_loop.verify(root, self.state(root, "sleep 5"), "W1", "A1", "test-red",
                                            command_timeout=0.2)
            _writes, green = test_loop.verify(root, self.state(root, "sleep 5"), "W1", "A2", "test-green",
                                              command_timeout=0.2)
        self.assertIn("(not the product code)", red)
        self.assertIn("because of this item's own test or fixture is yours to fix", red)
        self.assertNotIn("own code, test or fixture", red)
        self.assertIn("because of this item's own code, test or fixture is yours to fix", green)

    def test_a_record_written_before_the_disposition_field_counts_as_a_failure(self):
        """Old records meant a failed run; reading one as could-not-run would reopen the cap for old runs."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tests").mkdir()
            legacy = {"schema": test_loop.SCHEMA, "passed": False, "runs": [{"status": "timeout"}]}
            for number in range(1, test_loop.MAX_REFUSED_RUNS + 1):
                store.write_record(root / test_loop.verify_path("A1", number), dict(legacy))
                self.assertEqual(test_loop.refused_runs(root, "A1"), number)
                self.assertFalse(test_loop.latest_attempt_could_not_run(root, "A1"))
            self.assertTrue(test_loop.remedy_open(root, "A1"))  # seven failures open the remedy as before

    def test_only_the_latest_record_decides_whether_the_run_could_not_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tests").mkdir()
            self.assertFalse(test_loop.latest_attempt_could_not_run(root, "A1"))
            self.assertFalse(test_loop.remedy_open(root, "A1"))
            for number, (passed, disposition) in enumerate(
                    ((False, "could-not-run"), (False, "failed"), (False, "could-not-run")), 1):
                store.write_record(root / test_loop.verify_path("A1", number),
                                   {"schema": test_loop.SCHEMA, "passed": passed, "disposition": disposition,
                                    "runs": []})
                expected = disposition == "could-not-run"
                self.assertEqual(test_loop.latest_attempt_could_not_run(root, "A1"), expected, number)
                self.assertEqual(test_loop.remedy_open(root, "A1"), expected, number)
            self.assertEqual(test_loop.refused_runs(root, "A1"), 1)  # only the failed one counts


if __name__ == "__main__":
    unittest.main()
