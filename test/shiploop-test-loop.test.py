#!/usr/bin/env python3
"""Hermetic tests for ShipLoop's script-enforced test runs at the test stage and the rerun stages (verify and outer).

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
import shiploop_inner_fixture as inner  # noqa: E402
import shiploop_loop_support as support  # noqa: E402
import shiploop_knowledge_support as knowledge_support  # noqa: E402
import shiploop_loops as loops  # noqa: E402
import shiploop_mutation as mutation  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_packet_view as packet_view  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_quality as quality  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_item_scope as item_scope  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_status_hook as status_hook  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402
import shiploop_workspace as workspace  # noqa: E402

CORE = types.SimpleNamespace(PACKAGE_ROOT=PACKAGE, REF_DIR=PACKAGE / "references")
DONE = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}
TRIVIAL = {"classification": "trivial", "exit_assessment": "satisfied", "continuation_assessment": "allowed",
           "evidence": "Synthetic iteration: every command exited 0.", "handoff": "Synthetic; nothing remains."}
MATERIAL = dict(TRIVIAL, classification="non-trivial", exit_assessment="unsatisfied",
                evidence="Synthetic iteration: a command failed and the code was fixed.")
# A one-test runner: prints a unittest summary, fails while its file is missing.
CHECK = ('echo "Ran 1 test in 0.001s"\n'
         'if test -f "$1"; then echo OK; else echo "FAILED (failures=1)"; exit 1; fi\n')
def one_step(result: dict) -> dict:
    """The one implement step of a synthetic step plan, sized as the submit gate requires: it changes all of the
    item's paths and satisfies all of its criteria."""
    step = {"id": "S1", "task": "Make the planned change.", "paths": list(result.get("paths") or ["a.py"])}
    if result.get("criteria"):
        step["criteria"] = [row["id"] for row in result["criteria"]]
    return step


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


# What an in-place run (no workspace, so no plan-return) says about a changed file ShipLoop does not commit.
IN_PLACE_LEFT = ("ShipLoop commits no other changed file, and you commit nothing yourself: if the product needs one, "
                 "report revise so the step plan declares it; otherwise delete it.")
NOT_APPLICABLE = "Not applicable to this item"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


class TestLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        # Real-git tests must not read the machine's Git configuration (a CI runner's global config carries git-lfs
        # filters), as ReleaseVerifyReturnedResultTests below and the workspace suite do.
        isolated = mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
        isolated.start()
        self.addCleanup(isolated.stop)
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

    def complete(self, result: dict, *, loop: bool | None = None, fill: bool = True) -> str:
        """Submit ``result`` through the real ``complete``.

        At an inner stage the result is filled with the fields its gates need (``inner_fixture.fill``) and, unless it
        already cites this action's receipt or ``loop`` is False, the stage's Until Loop is run through the real
        runtime first (done ends it satisfied, revise stops it blocked).
        """
        state = self.state()
        action = nav.current_action(state)["id"]
        stage = nav.current_stage(state)
        if stage == "plan" and result.get("outcome") == "done" and "assumptions" not in result:
            result = dict(result, assumptions=[])
        if stage == "product-acceptance" and result.get("outcome") == "done" and "unverified" not in result:
            result = dict(result, unverified=[])
        if result.get("outcome") == "done":
            # The consumer contract's open items and lessons (2026-10-11): none here unless the test sets them.
            if stage in inner.assumptions.OPEN_ITEM_STAGES and "assumptions" not in result:
                result = dict(result, assumptions=[])
            if stage == "release-verify" and "lessons" not in result:
                result = dict(result, lessons=dict(inner.LESSONS))
        if loops.cursor(state) is not None:
            if fill:
                result = inner.fill(state, stage, result, self.run_dir)
            cited = str(loops.receipt_path(self.run_dir, action)) in [str(ref) for ref in result.get("evidence_refs", [])]
            if loop is None:
                loop = not cited
            if loop:
                result = inner.loop(self.run_dir, state, result)
        if stage in knowledge_support.knowledge.CLOSES:
            knowledge_support.write(state)
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
        updated, writes, payload = nav._transition(CORE, self.run_dir, state, updated)
        nav.save(self.run_dir, updated, writes)
        nav._lint_finish(self.run_dir, payload)
        nav._skill_commit(self.run_dir, state, updated, action)  # as the CLI's Improve stage complete does after save

    def settle(self) -> dict:
        """The saved state with any pending Improve child finished."""
        while self.state().get("active_improve") is not None:
            self.finish_improve()
        return self.state()

    def drive_to(self, stage: str, *, step_plan: dict | None = None, each=None) -> dict:
        """Advance with synthetic results; the step plan records ``step_plan`` (default: COMMANDS).

        ``each`` is called with the state at every producer stage before it is completed.  The test stage is passed
        by ``pass_loop`` (both commands made to pass); every other inner stage's loop runs through the real runtime."""
        recorded = ({"test_commands": [dict(COMMANDS[0], criteria=["C1"]), *COMMANDS[1:]], "paths": ["a.py"],
                     "criteria": [{"id": "C1", "text": "The item's focused check passes."}]}
                    if step_plan is None else step_plan)
        if recorded.get("test_commands") and "criteria" not in recorded:
            recorded = dict(recorded, test_commands=[dict(recorded["test_commands"][0], criteria=["C1"]),
                                                     *recorded["test_commands"][1:]],
                            criteria=[{"id": "C1", "text": "The item's focused check passes."}])
        recorded = {"steps": [one_step(recorded)], **recorded}
        for _ in range(200):
            state = self.state()
            if state.get("active_improve") is not None:
                self.finish_improve()
                continue
            current = nav.current_stage(state)
            if current == stage:
                return state
            if each is not None:
                each(state)
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
            else:
                self.complete(DONE)
        raise AssertionError("did not reach " + stage)

    # -- the bound Until Loop ------------------------------------------------------

    # The packet's Until Loop block (2026-10-16): the RUN line, which the literal start command follows, anchors it in the packet.
    START = loops.INVOKE_LINE

    def terminal(self) -> Path:
        return loops.receipt_path(self.run_dir, self.action())

    def run_loop(self, reports: list, *, contract_edit=None) -> dict:
        """Start the packet's printed command and submit ``reports`` in order.

        A callable entry runs between reports (the host's fix).  The runtime writes every packet to the receipt.
        """
        # The command is the one the packet prints.
        # A packet read after the start prints none (a second start resets the loop); a test that starts again on
        # purpose builds the same command the gate names.
        block = support.LoopBlock(self.packet())
        command = loops.start_command(loops.runtime(self.state()), Path(block.field("Receipt: ")),
                                      Path(block.field("Contract: ")))
        self.assertIn(block.command, (command, None))
        words = shlex.split(command)
        self.assertEqual(words[-2], "<")
        contract = json.loads(Path(words[-1]).read_text())
        if contract_edit is not None:
            contract_edit(contract)
        packet = json.loads(subprocess.run(words[:-2], input=json.dumps(contract), text=True,
                                           capture_output=True, check=True, timeout=30).stdout)
        for report in reports:
            if callable(report):
                report()
                continue
            self.assertEqual(packet["status"], "active")
            packet = json.loads(subprocess.run(packet["done_argv"], input=json.dumps(report), text=True,
                                               capture_output=True, check=True, timeout=30).stdout)
        packet = support.full_packet(packet)  # the receipt holds the full packet behind the lean print (U21)
        self.assertEqual(json.loads(self.terminal().read_text()), packet)
        return packet

    def pass_loop(self) -> None:
        """Make both commands pass, run one satisfied iteration and submit done."""
        (self.repo / "fixed.txt").write_text("fixed\n")
        (self.repo / "retained.txt").write_text("retained\n")
        self.run_loop([TRIVIAL])
        self.complete(dict(DONE, evidence_refs=[str(self.terminal())]))

    def assert_refused(self, result: dict, pattern: str, *, loop: bool = False, fill: bool = True) -> None:
        """``result`` is refused and nothing is saved; ``loop`` runs the stage's loop first, so a gate after the
        receipt check is reached."""
        before = (self.run_dir / "state.md").read_bytes()
        with self.assertRaisesRegex(nav.NavigatorError, pattern):
            self.complete(result, loop=loop, fill=fill)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before)

    def test_a_none_run_started_with_its_card_binds_the_test_and_verify_loops(self):
        """GUARD (F1): every inner loop reads the run's recorded Improve card at every item, and under
        `--planning-review none` no planning child binds it, so a none run is started with the card and the loops
        are then enforced exactly as in a stage run: done without the loop is refused."""
        nav.save(self.run_dir, nav.new_state(str(self.repo), "Test loop fixture.", improve_skill=str(IMPROVE_CARD),
                                             lint_option="off", planning_review="none"))
        self.drive_to("test")
        packet = self.packet()
        self.assertIn(loops.INVOKE_LINE, packet)
        self.assertIn(" " + str(ROOT / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py") + " start ", packet)
        self.assert_refused(DONE, "the test loop has not run: no terminal packet exists")
        self.drive_to("verify")
        self.assertIn(loops.INVOKE_LINE, self.packet())
        self.assert_refused(dict(DONE, evidence_refs=[]), "the verify loop has not run: no terminal packet exists")

    def test_a_started_loop_packet_says_to_continue_from_its_receipt(self):
        """X10 (e9_loop_recovery.py): after context loss mid-loop the packet gave no way back but Start."""
        self.start()
        self.drive_to("test")
        self.assertNotIn("already started", self.packet())
        self.run_loop([])  # started; the receipt holds the active packet
        self.assertIn("The loop already started: do not start it again (a second start resets it). While the receipt's "
                      "status is active, run its next_argv once", self.packet())

    def test_step_plan_must_record_its_test_commands(self):
        self.start()
        self.drive_to("step-plan")
        self.assert_refused(DONE, "a done step-plan result must list test_commands", loop=True, fill=False)
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
            canonical(dict(DONE, test_commands=COMMANDS), stage="test")
        self.assertEqual(canonical(dict(DONE, test_commands=[], test_commands_na="Docs only."),
                                   stage="step-plan")["test_commands_na"], "Docs only.")
        # The step-plan Improve child's final result passes the same CLI gate.
        with self.assertRaisesRegex(nav.NavigatorError, "must list test_commands"):
            nav._check_submitted_test_commands("step-plan", DONE)

    def test_a_long_command_list_is_accepted_where_it_is_submitted_and_the_test_contract_lists_every_command(self):
        """The test stage's contract lists every recorded command; the Until Loop runtime has no size limit, so
        step-plan's gate refuses no list for its length."""
        def rows(count, ids):
            return [{"command": f"python3 -m unittest -v test_{n}", "suite": "focused",
                     "ids": [f"test_{n}_{i}_" + "a" * 70 for i in range(ids)]} for n in range(count)]

        def plan(commands):
            return dict(DONE, test_commands=commands, paths=["src/a.py"], criteria=[{"id": "C1", "text": "x"}],
                        steps=[{"id": "S1", "task": "x", "criteria": ["C1"], "paths": ["src/a.py"]}])

        nav._check_submitted_test_commands("step-plan", plan(rows(2, 3)))
        nav._check_submitted_test_commands("step-plan", plan(rows(6, 15)))  # about 10 KB: over the old 9,216-byte budget
        nav._check_submitted_test_commands("step-plan", plan(rows(40, 40)))
        # the real gate takes it too, and the test stage's contract then carries every command
        long_rows = [dict(row, criteria=["C1"]) for row in rows(12, 15)]
        self.start()
        self.drive_to("test", step_plan={"test_commands": long_rows, "paths": ["a.py"],
                                         "criteria": [{"id": "C1", "text": "The item's focused check passes."}]})
        contract = json.loads((self.run_dir / loops.contract_path(self.action())).read_text())
        self.assertGreater(len(json.dumps(contract, separators=(",", ":"), sort_keys=True).encode()), 16_384)
        for row in long_rows:
            self.assertIn(loops.command_listing([row]).split(". ", 1)[1], contract["work"])

    def test_the_test_stage_loops_on_its_exact_commands(self):
        self.start()
        self.drive_to("test")
        contract = json.loads((self.run_dir / loops.contract_path(self.action())).read_text())
        self.assertIn("\n" + loops.COMMANDS_HEAD + "\n1. [focused] sh check.sh fixed.txt\n2. [regression] test -f "
                      "retained.txt", contract["work"])
        self.assertEqual(contract["exit_condition"], loops.exit_condition("test"))
        self.assertEqual(contract["required_trivial_reviews"], 0)
        packet = self.packet()
        # The commands are part of the Work field, between the argument's marker lines.
        argument = support.LoopBlock(packet).argument
        self.assertEqual(argument[argument.index(loops.COMMANDS_HEAD) + 1:][:2],
                         ["1. [focused] sh check.sh fixed.txt", "2. [regression] test -f retained.txt"])
        self.assertIn(loops.INVOKE_LINE, packet)
        self.pass_loop()
        self.assertNotEqual(nav.current_stage(self.settle()), "test")

    def test_failing_tests_loop_until_fixed_then_the_script_accepts(self):
        self.start()
        self.drive_to("test")
        (self.repo / "retained.txt").write_text("retained\n")
        terminal = self.run_loop([MATERIAL, lambda: (self.repo / "fixed.txt").write_text("fixed\n"), TRIVIAL])
        self.assertEqual(terminal["status"], "complete")
        action = self.action()
        self.complete(dict(DONE, evidence_refs=[str(self.terminal())]))
        self.assertNotEqual(nav.current_stage(self.settle()), "test")
        record = store.read_record(self.run_dir / test_loop.verify_path(action, 1))
        self.assertTrue(record["passed"])
        self.assertEqual([(row["command"], row["exit"]) for row in record["runs"]],
                         [("sh check.sh fixed.txt", 0), ("test -f retained.txt", 0)])

    def test_script_rerun_refuses_a_loop_that_claimed_green(self):
        self.start()
        self.drive_to("test")
        (self.repo / "retained.txt").write_text("retained\n")
        self.run_loop([TRIVIAL])  # claims every command passed; fixed.txt does not exist
        action = self.action()
        done = dict(DONE, evidence_refs=[str(self.terminal())])
        self.assert_refused(done, r"(?s)test is not done.*\[focused\] sh check.sh fixed.txt -> exit 1")
        record = store.read_record(self.run_dir / test_loop.verify_path(action, 1))
        self.assertFalse(record["passed"])
        (self.repo / "fixed.txt").write_text("fixed\n")
        # A complete packet never traps the step: it supports only done, but the loop can be started again (the
        # runtime replaces the receipt) and stopped blocked, which supports blocked.
        self.assert_refused(dict(DONE, outcome="blocked", blocked_by="external", evidence_refs=[str(self.terminal())]),
                            "a complete test loop reports outcome done")
        blocked = self.state()
        self.run_loop([dict(MATERIAL, continuation_assessment="blocked")])
        self.complete(dict(DONE, outcome="blocked", blocked_by="external", evidence_refs=[str(self.terminal())]))
        self.assertEqual(self.state()["status"], "blocked")
        nav.save(self.run_dir, blocked)
        self.run_loop([TRIVIAL])
        self.complete(done)
        self.assertNotEqual(nav.current_stage(self.settle()), "test")
        self.assertTrue(store.read_record(self.run_dir / test_loop.verify_path(action, 2))["passed"])

    def test_results_the_terminal_packet_does_not_support_are_refused(self):
        self.start()
        self.drive_to("test")
        (self.repo / "fixed.txt").write_text("fixed\n")
        (self.repo / "retained.txt").write_text("retained\n")
        self.assert_refused(dict(DONE, outcome="repeat"), "test accepts only done, blocked, revise")
        self.run_loop([TRIVIAL], contract_edit=lambda c: c.update(work="Run nothing."))
        self.assert_refused(dict(DONE, evidence_refs=[str(self.terminal())]),
                            "not from a run of this action's contract")
        self.run_loop([TRIVIAL])
        # ShipLoop lists the receipt itself (U10, X-15): a result that leaves it out passes the loop check, which returns it.
        self.assertEqual(loops.check_terminal(self.run_dir, self.state(), dict(DONE)), self.terminal())
        # No iteration limit: a long loop that ends complete is done.
        self.run_loop([MATERIAL] * 6 + [TRIVIAL])
        self.assert_refused(dict(DONE, outcome="revise", evidence_refs=[str(self.terminal())]),
                            "a complete test loop reports outcome done")
        action, receipt = self.action(), str(self.terminal())
        self.complete(dict(DONE), loop=False)  # no evidence_refs of its own: the receipt is listed in what ShipLoop stores
        state = self.state()
        kept = (state["accepted"].get(action) or state["active_improve"]["seed_result"])["evidence_refs"]
        self.assertIn(receipt, [str(ref) for ref in kept])
        self.assertNotEqual(nav.current_stage(self.settle()), "test")

    def test_stopped_loop_reports_blocked_and_runs_no_command(self):
        self.start()
        self.drive_to("test")
        stopped = self.run_loop([dict(MATERIAL, continuation_assessment="blocked")])
        self.assertEqual(stopped["status"], "stopped")
        with mock.patch.object(test_loop, "verify", side_effect=AssertionError("no command runs")), \
                mock.patch.object(test_loop, "base_check", side_effect=AssertionError("no base run")):
            self.assert_refused(dict(DONE, evidence_refs=[str(self.terminal())]),
                                "a test loop stopped as blocked reports outcome blocked")
            self.complete(dict(DONE, outcome="blocked", blocked_by="external", evidence_refs=[str(self.terminal())]))
        self.assertEqual(self.state()["status"], "blocked")

    def test_an_empty_command_list_runs_nothing_and_says_why(self):
        self.start()
        # The declared path is code, so the test stage still runs; it has no command to run.
        self.drive_to("test", step_plan={"test_commands": [], "test_commands_na": "Docs-only item.",
                                         "paths": ["a.py"]})
        action = self.action()
        self.assertIn("No command to run: Docs-only item. Report done with that reason", self.packet())
        self.complete(DONE)
        self.assertNotEqual(nav.current_stage(self.settle()), "test")
        self.assertFalse((self.run_dir / test_loop.verify_path(action, 1)).exists())

    def test_verify_commits_the_items_declared_changes_and_names_the_rest(self):
        """Committing is mechanical: ShipLoop does it when verify (which took over integrate's commit) is accepted."""
        self.start()
        self.drive_to("verify")
        (self.repo / "a.py").write_text("x = 2\n")
        (self.repo / "server.log").write_text("listening 3000\n")
        before = git(self.repo, "rev-parse", "HEAD").strip()
        output = self.complete(DONE)
        head = git(self.repo, "rev-parse", "HEAD").strip()
        self.assertNotEqual(head, before)
        self.assertIn("ShipLoop committed W1's changes (its declared paths and documentation) as " + head[:12], output)
        self.assertIn("a.py", git(self.repo, "show", "--name-only", "--format=", "HEAD").split())
        undeclared = next(line for line in output.splitlines() if line.startswith("Not committed"))
        self.assertIn("server.log", undeclared)
        self.assertNotIn("a.py", undeclared)
        self.assertIn("?? server.log", git(self.repo, "status", "--porcelain"))
        self.assertNotIn(" M a.py", git(self.repo, "status", "--porcelain"))

    def test_verify_commits_a_declared_file_and_a_document_whose_text_looks_like_a_credential(self):
        """Owner decision 2026-10-16: no credential-pattern skip. The item commit takes a file by its path and class,
        never by what its text resembles, so nothing is left uncommitted for the return to carry."""
        self.start()
        self.drive_to("verify")
        (self.repo / "a.py").write_text("AUTH = 'Auth: sf login (alias de)'\nPASSWORD = os.environ['PASSWORD']\n"
                                        "TOKEN = 'ghp_" + "A" * 36 + "'\n")
        (self.repo / "README.md").write_text("# Notes\n\nAuthorization: Bearer 0123456789abcdefghij\n")
        output = self.complete(DONE)
        self.assertEqual(sorted(git(self.repo, "show", "--name-only", "--format=", "HEAD").split()),
                         ["README.md", "a.py"])
        self.assertNotIn("look like they hold a credential", output)
        for line in output.splitlines():
            if line.startswith("Not committed"):  # the fixture's own undeclared files only
                self.assertNotIn("a.py", line)
                self.assertNotIn("README.md", line)
        status = git(self.repo, "status", "--porcelain")
        self.assertNotIn("a.py", status)
        self.assertNotIn("README.md", status)

    def test_verify_also_commits_changed_documentation_the_step_plan_did_not_declare(self):
        """P-document-1: a README the document stage adds is committed by ShipLoop, so the model never commits it.

        Four hand commits of an undeclared README/AGENTS.md in 16 recorded runs broke SPEC S-4/S-5.  Documentation is
        the one undeclared class ShipLoop commits (the document stage's ``edits``); any other undeclared file stays
        for plan-return, which commits files left uncommitted at the return.
        """
        self.start()
        self.drive_to("verify")
        (self.repo / "a.py").write_text("x = 2\n")
        (self.repo / "README.md").write_text("# Notes\n")
        (self.repo / "docs").mkdir(exist_ok=True)
        (self.repo / "docs" / "guide.md").write_text("guide\n")
        (self.repo / "server.log").write_text("listening 3000\n")
        output = self.complete(DONE)
        committed = git(self.repo, "show", "--name-only", "--format=", "HEAD").split()
        self.assertEqual(sorted(committed), ["README.md", "a.py", "docs/guide.md"])
        notice = next(line for line in output.splitlines() if line.startswith("Not committed"))
        self.assertIn("server.log", notice)
        self.assertNotIn("README.md", notice)
        self.assertNotIn("README.md", git(self.repo, "status", "--porcelain"))
        self.assertIn("?? server.log", git(self.repo, "status", "--porcelain"))

    def test_the_verify_packet_lists_what_shiploop_will_commit_and_what_it_leaves_with_one_sentence(self):
        """P-integrate-1/-3: the lists come from the script; the undeclared-file sentence is the Return route's."""
        self.start()
        self.drive_to("verify")
        (self.repo / "a.py").write_text("x = 2\n")
        (self.repo / "README.md").write_text("# Notes\n")
        (self.repo / "server.log").write_text("listening 3000\n")
        packet = self.packet()
        lines = packet.splitlines()
        will = next(line for line in lines if line.startswith("Changed, ShipLoop will commit: "))
        self.assertEqual(will, "Changed, ShipLoop will commit: README.md, a.py")
        left = next(line for line in lines if line.startswith("Changed, ShipLoop will not commit: "))
        self.assertIn("server.log", left.split(": ", 1)[1].split(", "))  # the driver's own scratch files are listed too
        self.assertNotIn("README.md", left)
        self.assertIn("Step plan paths: a.py", packet)
        # One consistent sentence: the contradicting "commit the ones the product needs" is gone.  This run is in
        # place (no workspace, no plan-return), so the sentence is the in-place one (F1 of the 2026-10-10 review).
        self.assertNotIn("commit the ones the product needs", packet)
        self.assertIn(IN_PLACE_LEFT, " ".join(packet.split()))
        self.assertNotIn("plan-return", packet)
        self.assertNotIn("working branch", packet)

    # -- efficiency plan U16: document, verify and carry-forward (rows TD-8, VR-2, VR-3, VR-5, VR-7) -------------------

    def drive_with_change(self, stage: str) -> dict:
        """``drive_to`` with a code change made at implement, so the item's diff touches code and document is issued."""
        def change(state):
            if nav.current_stage(state) == "implement":
                (self.repo / "a.py").write_text("import os\n")  # code, with no token a mutant could change
        return self.drive_to(stage, each=change)

    def test_the_document_packet_lists_the_script_derived_changed_paths_its_duty_names(self):
        """TD-8: the inventory document's duty 1 lists behaviours from exists at document, derived by the script."""
        self.start()
        self.drive_with_change("document")
        packet = self.packet()
        line = next(row for row in packet.splitlines() if row.startswith(nav.CHANGED_SINCE_BASE))
        self.assertIn("a.py", line[len(nav.CHANGED_SINCE_BASE):].split(", "))
        self.assertIn("1. **List** the changed public behaviours from the changed paths below,", packet)
        self.assertLess(packet.index("1. **List**"), packet.index(nav.CHANGED_SINCE_BASE))  # "below" holds
        with mock.patch.object(item_scope.lint, "read_base", return_value=None):
            self.assertIn(nav.CHANGED_SINCE_BASE + "not computed: " + item_scope.NO_BASE, self.packet())

    def test_commit_item_raises_when_the_items_changes_cannot_be_read(self):
        """VR-7: an unknown change is no 'nothing to commit'; verify's notice names why."""
        self.start()
        state = self.drive_to("verify")
        with mock.patch.object(item_scope.lint, "read_base", return_value=None):
            with self.assertRaisesRegex(item_scope.ItemScopeError, r"^the item's changes cannot be read "
                                        r"\(no base snapshot was captured when it started\)$"):
                item_scope.commit_item(self.run_dir, state, "W1", "feat: W1")
        with mock.patch.object(item_scope, "changed_since", return_value=None):
            with self.assertRaisesRegex(item_scope.ItemScopeError, item_scope.UNREADABLE):
                item_scope.commit_item(self.run_dir, state, "W1", "feat: W1")

    def test_the_item_commit_locator_names_the_commit_only_when_the_log_has_its_subject(self):
        """VR-7: the carry-forward reference 'W1 verify item commit' printed even when verify committed nothing."""
        self.start()
        state = self.drive_to("verify")
        verify = self.action()
        self.assertIsNone(nav._item_commit_product(self.run_dir, state, "W1", verify))
        (self.repo / "a.py").write_text("x = 2\n")
        self.complete(DONE)
        state = self.drive_to("carry-forward")
        self.assertEqual(nav._item_commit_product(self.run_dir, state, "W1", verify),
                         "the WORKTREE commit whose subject starts 'feat: W1 '")
        self.assertIn("- W1 verify item commit: the WORKTREE commit whose subject starts 'feat: W1 '", self.packet())
        self.assertIsNone(nav._item_commit_product(self.run_dir, state, "W", verify))  # 'feat: W1' is not item W's

    def test_a_one_step_one_item_carry_forward_prints_the_short_queue_and_skill_duties(self):
        """VR-2: one step in one item and no pending item, proved from state: the short duties, the path-only queue
        line and a Work line without the trial clause (the short duty 3 names the trial file)."""
        self.start()
        state = self.drive_to("carry-forward")
        self.assertEqual(loops.one_step_run(state), "W1")
        packet = self.packet()
        flat = " ".join(packet.split())
        self.assertIn("2. **Queue** (Carry-forward mapping guidance). No item follows W1: omit `work_items`.", flat)
        self.assertIn("this run has 1 step in 1 item and no pending item, so no procedure repeated.", flat)
        self.assertIn("write the trial to RUN/notes/<action>-skill-trial.md.", flat)
        self.assertIn("(and a created or updated skill, item 3)", flat)
        for gone in ("Read every pending item's full title/context", "Omit work_items to retain the future queue",
                     "*Write it deterministic.*", "item 3.7"):
            self.assertNotIn(gone, flat)
        self.assertIn("Full ordered work queue: RUN/state.md; field work_items.", packet)
        work = loops.contract(self.run_dir, state, self.action())["work"]
        self.assertEqual(work, loops.WORK_ONE_STEP.replace("{items}", "1-4").replace("{run}", str(self.run_dir))
                         .replace("{action}", self.action()))

    def test_carry_forward_names_the_verify_commands_environment_md_lacks_and_its_notice_never_refuses(self):
        """VR-3: the commands that passed at verify and HOME/environment.md does not name, in the packet, and one counted
        notice when carry-forward is accepted."""
        self.start()
        state = self.drive_to("carry-forward")
        environment = self.repo / "docs/shiploop/environment.md"
        environment.parent.mkdir(parents=True, exist_ok=True)
        environment.write_text("# Environment\n\n## Commands\n\n- `sh check.sh fixed.txt`\n")
        self.assertEqual(nav._verify_passed_commands(self.run_dir, state, "W1"),
                         ["sh check.sh fixed.txt", "test -f retained.txt"])
        line = next(row for row in self.packet().splitlines() if row.startswith("Commands that passed at verify"))
        self.assertEqual(line, "Commands that passed at verify and are not named in HOME/environment.md: "
                               "`test -f retained.txt`. Write each under ## Commands, or say in the summary why one "
                               "does not belong.")
        self.complete(DONE)
        after = self.settle()  # the carry-forward row is recorded when its Improve child finishes
        self.assertNotEqual(nav.current_stage(after), "carry-forward")  # accepted: a notice, not a refusal
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):  # what the CLI's Improve-stage complete prints after it saves
            nav._knowledge_close(state, after, self.run_dir)
        notices = [row for row in buffer.getvalue().splitlines()
                   if row.startswith(knowledge_support.knowledge.NOTICE_PREFIX) and "passed at verify" in row]
        self.assertEqual(len(notices), 1)
        self.assertTrue(notices[0].endswith("`test -f retained.txt`"))

    def test_the_verify_duty_runs_check_only_and_keeps_the_assembly_item_on_the_ask_agent_route(self):
        """VR-5: duty 1 points at the check-only record ShipLoop writes, duty 11 asks for no exit codes; item 8 stays
        on the ask-agent route only."""
        for route in prompts.DELEGATIONS:
            duty = prompts.duty("verify", delegation=route)
            self.assertIn("1. **Run** the Callback command with `--check-only` after your last edit", duty)
            self.assertIn("RUN/" + test_loop.check_only_path("<action>"), duty)
            summary = next(row for row in duty.splitlines() if row.startswith("11. **Summary:**"))
            self.assertNotIn("exit code", summary)
            self.assertEqual("8. **Assembly.**" in duty, route == prompts.ASK_AGENT)

    def test_the_carry_forward_duty_is_unchanged_without_the_one_step_item(self):
        """VR-2: multi-step, multi-item and pending-item runs keep today's text byte for byte."""
        for route in prompts.DELEGATIONS:
            self.assertEqual(prompts.duty("carry-forward", delegation=route),
                             prompts.duty("carry-forward", delegation=route, one_step_item=None))
            self.assertIn("2. **Queue** (Carry-forward mapping guidance). Read RUN/state.md `work_items`",
                          prompts.duty("carry-forward", delegation=route))
            self.assertIn("item 3.7", prompts.duty("carry-forward", delegation=route))
        self.assertEqual(prompts.duty("verify", one_step_item="W1"), prompts.duty("verify"))

    def test_the_commit_lists_are_absent_when_the_changes_are_unknown_and_say_nothing_changed_when_none(self):
        self.start()
        self.drive_to("verify")
        with mock.patch.object(item_scope, "changed_paths", return_value=None):
            packet = self.packet()
        self.assertIn("Step plan paths: a.py", packet)
        self.assertNotIn("ShipLoop will commit: ", packet)
        with mock.patch.object(item_scope, "changed_paths", return_value=[]):
            self.assertIn("Changed since this item's base: nothing.", self.packet())

    def test_a_case_that_cannot_run_is_submitted_as_an_open_item_and_the_run_continues(self):
        """P-sta-2, SPEC S-14: the route the system-test-author packet names goes through the real complete gate.

        The summary names the case, the requirement left unverified and the due stage; the command that cannot pass
        stays out of system_commands, so ShipLoop's rerun at system-test has nothing it must fail on, and the next
        stage carries the open item.  Both Grok BLOCKED runs stopped here instead.
        """
        self.start()
        self.drive_to("system-test-author")
        duty = " ".join(self.packet().split())
        self.assertIn("Record it as an open item in `assumptions`", duty)
        self.assertNotIn("blocked, blocked_by access", duty)
        self.complete(dict(DONE, system_commands=[COMMANDS[1]], summary=(
            "Open item TC-16 (needs a browser this host cannot reach): requirement R-4 stays unverified; a person "
            "runs the check by hand and reports what it shows; due handoff.")))
        self.drive_to("system-test")
        self.assertEqual(self.state()["status"], "active")
        self.assertIn("Run any open item system-test-author recorded", " ".join(self.packet().split()))

    def test_the_document_packet_prints_the_declared_paths_and_the_commit_rule(self):
        self.start()
        # document is issued when the item's diff touches code (owner decision 7), so the item changes a.py too.
        def edit(state):
            if nav.current_stage(state) == "implement":
                (self.repo / "a.py").write_text("x = 2\n")
        self.drive_to("document", step_plan={**self.NO_TESTS, "paths": ["a.py", "docs/fleet.md", "docs/ops.md"]},
                      each=edit)
        packet = self.packet()
        self.assertIn("Step plan paths: a.py, docs/fleet.md, docs/ops.md", packet)
        self.assertIn("changed documentation files (for example README.md or files under docs/)", packet)
        self.assertIn(IN_PLACE_LEFT, " ".join(packet.split()))
        self.assertNotIn("plan-return", packet)

    def test_an_in_place_run_names_no_plan_return_and_leaves_an_undeclared_file_uncommitted(self):
        """F1/#3 of the 2026-10-10 review (repro_inplace.py): an in-place run has no workspace and no plan-return, yet
        the integrate packet and notice said plan-return commits the leftovers, and helper.py stayed untracked."""
        self.start()
        self.drive_to("verify")
        self.assertEqual(self.state()["execution_mode"], "navigator")
        (self.repo / "helper.py").write_text("y = \"helper\"\n")
        packet = self.packet()
        self.assertIn(IN_PLACE_LEFT, " ".join(packet.split()))
        self.assertNotIn("plan-return", packet)
        output = self.complete(DONE)
        notice = next(line for line in output.splitlines() if line.startswith("Not committed"))
        self.assertIn("helper.py", notice)
        self.assertIn(IN_PLACE_LEFT, notice)
        self.assertNotIn("plan-return", output)
        self.assertIn("?? helper.py", git(self.repo, "status", "--porcelain"))

    def test_in_place_revise_declares_the_file_and_the_next_verify_commits_it(self):
        """GUARD (green before and after): the in-place route the sentence names goes through the real gates: revise at
        verify is accepted, the redone step plan declares the file, and the next verify commits it."""
        self.start()
        self.drive_to("verify")
        (self.repo / "helper.py").write_text("y = \"helper\"\n")
        self.complete(dict(DONE, outcome="revise", summary="helper.py is product code the step plan did not declare."))
        self.assertEqual(nav.current_stage(self.state()), "step-plan")
        (self.repo / "fixed.txt").unlink()  # the redone item's test stage runs its base check again
        self.drive_to("verify", step_plan={"test_commands": COMMANDS, "paths": ["a.py", "helper.py"]})
        self.complete(DONE)
        self.assertIn("helper.py", git(self.repo, "show", "--name-only", "--format=", "HEAD").split())
        self.assertNotIn("helper.py", git(self.repo, "status", "--porcelain"))

    def test_a_case_an_inner_stage_cannot_run_goes_back_through_the_gate(self):
        """B2/#4: the test stage routes an unachievable case by revise, the outcome its gate accepts (the loop stops
        blocked, which supports revise)."""
        self.start()
        self.drive_to("test")
        self.assertIn("revise", stage_spec.stage("test").outcomes)
        self.complete(dict(DONE, outcome="revise", summary=(
            "TC-4 needs a device this host does not have; the step plan should observe R-2 another way.")))
        self.assertIn(nav.current_stage(self.settle()), ("step-plan", "test-spec"))

    def test_a_recorded_system_command_that_fails_at_system_test_is_refused_and_no_line_promises_done(self):
        """B1 of the 2026-10-10 review (probe_system_test.py): the packet said a route that fails when the case is run
        is an open item and the result is done, but the case's command is recorded, and the rerun refuses done."""
        self.start()
        (self.repo / "page.txt").write_text("ok\n")
        self.drive_to("system-test-author")
        self.complete(dict(DONE, system_commands=[{"command": "test -f page.txt", "suite": "check"}]))
        self.drive_to("system-test")
        (self.repo / "page.txt").unlink()  # the route fails at run time
        packet = " ".join(self.packet().split())
        self.assertNotIn("the route fails when the case is run", packet)
        self.assertIn("A recorded system command that fails here is no open item", packet)
        self.assert_refused(dict(DONE, summary=("Open item ST-1: the page never loads in this host; R-1 unverified; "
                                                "a person opens it and reports it renders; due handoff.")),
                            r"test -f page\.txt")

    NO_TESTS = {"test_commands": [], "test_commands_na": "Navigation metadata only.",
                "paths": ["force-app/main/default/tabs/Fleet_command.tab-meta.xml", "docs/fleet.md"]}

    def test_an_item_that_declares_only_non_code_paths_leaves_its_test_stage_out(self):
        self.start()
        self.drive_to("implement", step_plan=self.NO_TESTS)
        tab = self.repo / "force-app/main/default/tabs/Fleet_command.tab-meta.xml"
        tab.parent.mkdir(parents=True)
        tab.write_text("<CustomTab/>\n")
        self.complete(DONE)
        state = self.settle()
        self.assertNotIn(nav.current_stage(state), ("implement", "test"))
        rows = [row for row in state["history"] if row["stage"] in item_scope.TEST_STAGES]
        self.assertEqual([row["stage"] for row in rows], ["test"])
        self.assertIn(NOT_APPLICABLE, rows[0]["summary"])
        self.assertTrue((self.run_dir / "results" / (rows[0]["action"] + ".md")).is_file())
        step = next(row for row in state["history"] if row["stage"] == "step-plan")
        self.assertTrue((self.run_dir / "results" / (step["action"] + ".md")).is_file())

    # -- carry-forward's skill decision (it replaced skill-assess and skill-validate, 2026-10-10) -------------------

    def skill_file(self, text: str = "---\nname: review\ndescription: Review a change.\n---\n") -> str:
        path = self.repo / ".claude" / "skills" / "review" / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return ".claude/skills/review/SKILL.md"

    def test_carry_forward_needs_a_skill_decision_with_its_reason(self):
        self.start()
        self.drive_to("carry-forward")
        refused = lambda result, message: self.assert_refused(result, message, loop=True, fill=False)  # noqa: E731
        refused(DONE, r"carry-forward needs skill: \{\"decision\"")
        refused(dict(DONE, skill={"decision": "maybe", "reason": "x"}), "carry-forward needs skill")
        refused(dict(DONE, skill={"decision": "none", "reason": " "}), "carry-forward needs skill")
        self.complete(dict(DONE, skill={"decision": "reuse", "reason": "The review skill already covers it."}))
        self.assertNotEqual(nav.current_stage(self.settle()), "carry-forward")

    def test_a_created_skill_must_exist_with_frontmatter_and_repeat_evidence(self):
        self.start()
        self.drive_to("carry-forward")
        refused = lambda result, message: self.assert_refused(result, message, loop=True, fill=False)  # noqa: E731
        create = {"decision": "create", "reason": "The same review ran in two steps.", "path": ".claude/skills/review/SKILL.md",
                  "evidence": ["S1 and S2 ran the same review"]}
        refused(dict(DONE, skill=create), "names a SKILL.md that does not exist")
        self.skill_file("# no frontmatter\n")
        refused(dict(DONE, skill=create), "needs frontmatter with name and description")
        self.skill_file()
        refused(dict(DONE, skill=dict(create, evidence=[])), "a create skill decision lists its repeat evidence")
        refused(dict(DONE, skill=dict(create, path="README.md")), "names a SKILL.md that does not exist")
        before = git(self.repo, "rev-parse", "HEAD").strip()
        # A follow-up item keeps this carry-forward from being the last item's, so no end review runs first.
        output = self.complete(dict(DONE, skill=create, work_items=[{"id": "W2", "title": "Follow-up"}]))
        self.assertEqual(nav.current_stage(self.state()), "step-plan")
        # ShipLoop commits the created skill; the model commits nothing.
        head = git(self.repo, "rev-parse", "HEAD").strip()
        self.assertNotEqual(head, before)
        self.assertIn("ShipLoop committed the review skill as " + head[:12], output)
        self.assertEqual(git(self.repo, "show", "--name-only", "--format=", "HEAD").split(),
                         [".claude/skills/review/SKILL.md"])
        self.assertNotIn("SKILL.md", git(self.repo, "status", "--porcelain"))

    def test_the_last_items_created_skill_is_committed_after_its_end_review(self):
        """The last item's carry-forward is accepted when its end-of-work Improve child completes; the skill it created
        must be committed then, as it is when no child runs."""
        self.start()
        self.drive_to("carry-forward")
        self.skill_file()
        before = git(self.repo, "rev-parse", "HEAD").strip()
        self.complete(dict(DONE, skill={"decision": "create", "reason": "The same review ran in two steps.",
                                        "path": ".claude/skills/review/SKILL.md", "evidence": ["S1 and S2"]}))
        self.assertEqual(self.state()["active_improve"]["stage"], "carry-forward")
        self.settle()
        self.assertNotEqual(git(self.repo, "rev-parse", "HEAD").strip(), before,
                            "the skill was not committed after the end review accepted carry-forward")
        self.assertNotIn("SKILL.md", git(self.repo, "status", "--porcelain"))

    def test_document_is_issued_when_the_changes_cannot_be_read(self):
        """Owner decision 7 (2026-10-10): document is left out only on proof that the item's diff touches no code or
        test path; an unreadable diff is no proof, so the stage is issued."""
        self.start()
        self.drive_to("test")
        (self.repo / "fixed.txt").write_text("fixed\n")
        (self.repo / "retained.txt").write_text("retained\n")
        self.run_loop([TRIVIAL])
        with mock.patch.object(item_scope, "changed_paths", return_value=None):
            self.complete(dict(DONE, evidence_refs=[str(self.terminal())]))
        self.assertEqual(nav.current_stage(self.settle()), "document")

    def test_document_is_left_out_when_the_diff_touches_no_code_or_test_path(self):
        self.start()
        self.drive_to("implement", step_plan=self.NO_TESTS)
        (self.repo / "docs").mkdir(exist_ok=True)
        (self.repo / "docs" / "fleet.md").write_text("# Fleet\n")
        self.complete(DONE)
        state = self.settle()
        self.assertEqual(nav.current_stage(state), "verify")
        row = next(row for row in state["history"] if row["stage"] == "document")
        self.assertTrue(row["summary"].startswith(NOT_APPLICABLE), row["summary"])

    def test_implement_outside_the_declared_non_code_paths_is_refused(self):
        self.start()
        self.drive_to("implement", step_plan=self.NO_TESTS)
        (self.repo / "a.py").write_text("x = 2\n")
        self.assert_refused(DONE, r"(?s)declared only non-code paths.*- a.py \(code\).*report revise", loop=True)
        (self.repo / "a.py").write_text("x = 1\n")
        (self.repo / "notes.txt").write_text("stray\n")
        self.assert_refused(DONE, r"- notes.txt \(code\)", loop=True)  # a path no rule matches counts as code
        (self.repo / "notes.txt").unlink()
        (self.repo / "NOTES.md").write_text("stray\n")
        self.assert_refused(DONE, r"- NOTES.md \(not declared\)", loop=True)
        (self.repo / "NOTES.md").unlink()
        self.complete(DONE)
        self.assertNotEqual(nav.current_stage(self.settle()), "implement")

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
        self.drive_to("step-plan")
        log = git(self.repo, "log", "--format=%s", "-n", "3")
        self.assertIn("docs(shiploop): record", log)
        self.assertIn("knowledge at prepare", log)
        self.assertIn("docs/shiploop/spec.md", git(self.repo, "ls-files", "docs/shiploop"))

    def test_a_done_step_plan_must_declare_its_paths(self):
        self.start()
        self.drive_to("step-plan")
        refused = lambda result, message: self.assert_refused(result, message, loop=True, fill=False)  # noqa: E731
        refused(dict(DONE, test_commands=COMMANDS), "must list paths")
        refused(dict(DONE, test_commands=COMMANDS, paths=["a.py"]), "must list criteria")
        refused(dict(DONE, test_commands=COMMANDS, paths=["../x"]), "inside the repository")

    def test_without_a_resolvable_runtime_the_packet_says_unavailable_and_blocked_is_accepted(self):
        """Since 2026-10-10 a run with no selected card binds the bundled runtime; one whose card cannot be resolved
        has no loop, so the packet says so and names blocked, which the gate accepts without a receipt."""
        self.start()
        self.drive_to("test")
        state = self.state()
        state["improve_skill"] = str(self.repo / "missing" / "SKILL.md")
        nav.save(self.run_dir, state)
        packet = self.packet()
        self.assertIn("Unavailable: the Until Loop runtime cannot be resolved", packet)
        self.assertIn("Report outcome blocked with this reason.", packet)
        self.assert_refused(DONE, "Until Loop terminal packet is missing")   # done still needs the loop's receipt
        self.complete(dict(DONE, outcome="blocked", blocked_by="external", summary="No Until Loop runtime."))
        self.assertEqual(self.state()["status"], "blocked")

    def test_stages_that_edit_code_rerun_every_command_before_done(self):
        self.start()
        for stage in test_loop.RERUN_STAGES:
            with self.subTest(stage=stage):
                self.drive_to(stage)
                self.assertIn("Test rerun: on done, ShipLoop runs every test command", self.packet())
                (self.repo / "retained.txt").unlink()  # this stage broke a regression test
                self.assert_refused(DONE, r"(?s)" + stage + r" is not done.*\[regression\] test -f retained.txt"
                                    r" -> exit 1.*Fix the code so every command passes", loop=True)
                (self.repo / "retained.txt").write_text("retained\n")
                self.complete(DONE)
                self.assertNotEqual(nav.current_stage(self.settle()), stage)

    def test_a_done_system_test_with_a_person_only_open_item_advances_and_still_reruns_the_commands(self):
        """a13, S-14: a person-only case is recorded as an open item in the result and never blocks done.

        The script still reruns the recorded system commands (S-9): the open item
        replaces no script-run check, and the next stage's packet carries it.
        """
        self.start()
        self.drive_to("system-test")
        action = self.action()
        # The rendered packet names the route the result below takes.
        self.assertIn("does not block this result", " ".join(self.packet().split()))
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

    def test_after_the_last_refused_run_only_blocked_or_revise_is_accepted(self):
        self.start()
        self.drive_to("test")
        (self.repo / "fixed.txt").write_text("fixed\n")  # the candidate's regression command fails every run
        for attempt in range(1, test_loop.MAX_REFUSED_RUNS + 1):
            self.assert_refused(DONE, "Refused runs for this action so far: " + str(attempt) + r" \(base, candidate and mutation",
                                loop=True)
        (self.repo / "retained.txt").write_text("retained\n")  # even a now-passing tree
        with mock.patch.object(test_loop, "lint", wraps=test_loop.lint) as runner:
            self.assert_refused(DONE, "was refused 11 times; done is no longer accepted", loop=True)
            runner.run_argv.assert_not_called()
        blocked = self.state()
        self.complete(dict(DONE, outcome="blocked", blocked_by="external"), loop=False)
        self.assertEqual(self.state()["status"], "blocked")
        nav.save(self.run_dir, blocked)
        self.complete(dict(DONE, outcome="revise", summary="sh check.sh keeps failing."), loop=False)
        self.assertNotEqual(nav.current_stage(self.settle()), "test")

    TIMED_OUT = ("timeout", None, b"partial output\n", b"")

    def restart(self) -> None:
        """A fresh run in this test's own temporary repository (earlier subtests leave no files behind)."""
        for name in os.listdir(self.run_dir):
            path = self.run_dir / name
            shutil.rmtree(path) if path.is_dir() else path.unlink()
        for name in ("fixed.txt", "retained.txt"):
            (self.repo / name).unlink(missing_ok=True)
        self.start()

    def refuse_unrunnable(self, done: dict, attempts: int = 1) -> None:
        """ShipLoop's own run of the recorded commands times out ``attempts`` times; each refuses done.

        At the test stage the first run to time out is the base run; at a rerun stage it is the candidate run."""
        action = self.action()
        for _number in range(1, attempts + 1):
            with mock.patch.object(test_loop.lint, "run_argv", return_value=self.TIMED_OUT):
                self.assert_refused(done, "timed out, so it reached no verdict", loop=True)
            self.assertTrue(test_loop.latest_attempt_could_not_run(self.run_dir, action))
        self.assertEqual(test_loop.refused_runs(self.run_dir, action), 0)  # the cap never advances

    def test_revise_is_accepted_at_the_test_stage_after_a_could_not_run_attempt(self):
        self.start()
        self.drive_to("test")
        (self.repo / "fixed.txt").write_text("fixed\n")
        (self.repo / "retained.txt").write_text("retained\n")
        self.run_loop([TRIVIAL])
        done = dict(DONE, evidence_refs=[str(self.terminal())])
        revise = dict(done, outcome="revise")
        # Before ShipLoop has any record, a complete loop supports only done.
        self.assert_refused(revise, "a complete test loop reports outcome done")
        self.refuse_unrunnable(done, attempts=3)
        self.complete(revise)  # the route the refusal names
        self.assertNotEqual(nav.current_stage(self.settle()), "test")

    def test_a_failed_run_does_not_open_revise_before_the_cap_and_a_complete_loop_still_needs_done(self):
        self.start()
        self.drive_to("test")
        (self.repo / "retained.txt").write_text("retained\n")
        self.run_loop([TRIVIAL])  # complete, but fixed.txt is missing, so ShipLoop's own run fails
        done = dict(DONE, evidence_refs=[str(self.terminal())])
        self.assert_refused(done, r"Refused runs for this action so far: 1 \(base, candidate and mutation")
        self.assertEqual(test_loop.refused_runs(self.run_dir, self.action()), 1)
        self.assert_refused(dict(done, outcome="revise"), "a complete test loop reports outcome done")
        (self.repo / "fixed.txt").write_text("fixed\n")
        self.complete(done)
        self.assertNotEqual(nav.current_stage(self.settle()), "test")

    def test_a_later_failed_run_closes_the_could_not_run_route(self):
        """Only ShipLoop's latest record counts: a product failure after a hang is a product failure."""
        self.start()
        self.drive_to("test")
        (self.repo / "retained.txt").write_text("retained\n")
        self.run_loop([TRIVIAL])
        done = dict(DONE, evidence_refs=[str(self.terminal())])
        self.refuse_unrunnable(done)
        self.assert_refused(done, r"Refused runs for this action so far: 1 \(base")  # fixed.txt missing: a real failure
        self.assert_refused(dict(done, outcome="revise"), "a complete test loop reports outcome done")

    def test_revise_and_blocked_are_accepted_at_verify_after_a_could_not_run_attempt(self):
        """verify took over static-checks' review loop: its rerun's refusal names revise, so the gate must accept
        revise (and blocked) once ShipLoop's latest run could not run, as the quality gate did."""
        for outcome in ("revise", "blocked"):
            with self.subTest(outcome=outcome):
                self.restart()
                self.drive_to("verify")
                self.run_loop([TRIVIAL])
                done = dict(DONE, evidence_refs=[str(self.terminal())])
                chosen = dict(done, outcome=outcome, **({"blocked_by": "external"} if outcome == "blocked" else {}))
                self.assert_refused(chosen, "a complete verify loop reports outcome done")  # no record yet
                self.refuse_unrunnable(done, attempts=2)
                self.complete(chosen)
                if outcome == "revise":
                    self.assertNotEqual(nav.current_stage(self.settle()), "verify")
                else:
                    self.assertEqual(self.state()["status"], "blocked")

    def test_revise_is_accepted_at_verify_after_the_cap_the_refusal_names(self):
        """After 11 refused runs `verify` says "Report outcome revise"; verify's gate must accept it."""
        self.start()
        self.drive_to("verify")
        self.run_loop([TRIVIAL])
        done = dict(DONE, evidence_refs=[str(self.terminal())])
        (self.repo / "retained.txt").unlink()  # a regression command fails on every run
        for attempt in range(1, test_loop.MAX_REFUSED_RUNS + 1):
            self.assert_refused(done, "Refused runs for this action so far: " + str(attempt) + r" \(base, candidate and mutation")
        self.assert_refused(done, "was refused 11 times; done is no longer accepted")
        self.complete(dict(done, outcome="revise"))  # the route the refusal names
        self.assertNotEqual(nav.current_stage(self.settle()), "verify")

    def test_the_remedy_outcome_is_accepted_at_every_outer_stage_after_a_could_not_run_attempt(self):
        """Guard: the outer rerun stages have no loop packet; their remedy is replan with work_items."""
        corrective = [{"id": "W2", "title": "Make the recorded command fit its budget"}]
        for stage in ("system-test", "release-verify"):
            with self.subTest(stage=stage):
                self.restart()
                self.drive_to(stage)
                self.refuse_unrunnable(DONE)
                self.complete(dict(DONE, outcome="replan", work_items=corrective))
                self.assertIn("W2", [row["id"] for row in self.state()["work_items"]])

    def reach_could_not_run(self, stage: str) -> tuple:
        """A fresh run at ``stage`` whose latest ShipLoop run never reached a verdict: ``(the done result the gate refused,
        the refusal text)``.  An inner stage ends its Until Loop first; an outer one has none."""
        self.restart()
        self.drive_to(stage)
        done = DONE
        if loops.cursor(self.state()) is not None:
            self.run_loop([TRIVIAL])
            done = dict(DONE, evidence_refs=[str(self.terminal())])
        with mock.patch.object(test_loop.lint, "run_argv", return_value=self.TIMED_OUT):
            with self.assertRaises(nav.NavigatorError) as caught:
                self.complete(done, loop=True)
        self.assertTrue(test_loop.latest_attempt_could_not_run(self.run_dir, self.action()))
        return done, str(caught.exception)

    def checkpoint(self) -> Path:
        """Copies of the run directory and the repository as they stand, so one state can take several submissions."""
        base = Path(tempfile.mkdtemp(prefix="shiploop-checkpoint-", dir=self.run_dir.parent))
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        shutil.copytree(self.run_dir, base / "run")
        shutil.copytree(self.repo, base / "repo")
        return base

    def rollback(self, base: Path) -> None:
        for live, saved in ((self.run_dir, base / "run"), (self.repo, base / "repo")):
            shutil.rmtree(live)
            shutil.copytree(saved, live)

    def test_every_exit_a_could_not_run_refusal_names_is_accepted_by_the_gate_at_its_stage(self):
        """ROUTE test (memory test-the-route-not-the-wording; test-economy review, 2026-10-17, row 5): a refusal names the
        exits the model may take, and A1 shipped one the gate itself refused.  At every stage that reruns recorded
        commands, the real refusal text is read for the outcomes it tells the model to report, each is submitted through
        the real ``complete``, and each is accepted.  The tests above submit a hand-picked ``revise`` or ``replan``; this
        one takes the outcome from the text, so a refusal that names an exit its stage does not take fails here."""
        corrective = [{"id": "W2", "title": "Make the recorded command fit its budget"}]
        shape = {"blocked": {"blocked_by": "external"}, "replan": {"work_items": corrective}}
        for stage in test_loop.VERIFY_STAGES:
            remedy = next(outcome for outcome in ("revise", "replan") if outcome in stage_spec.STAGE_SPEC[stage].outcomes)
            with self.subTest(stage=stage):
                done, refusal = self.reach_could_not_run(stage)
                named = packet_view.named_outcomes(refusal)
                self.assertIn(remedy, named, "the refusal must name the remedy its stage takes: " + refusal)
                self.assertEqual(packet_view.unaccepted_outcomes(stage, refusal), [], refusal)
                saved = self.checkpoint()
                for outcome in named:
                    with self.subTest(stage=stage, outcome=outcome):
                        self.rollback(saved)
                        self.complete(dict(done, outcome=outcome, **shape.get(outcome, {})))
                        recorded = self.state()["history"][-1]
                        self.assertEqual((recorded["stage"], recorded["outcome"]), (stage, outcome))
                        self.assertEqual(self.state()["status"], "blocked" if outcome == "blocked" else "active")

    ID_CHECK = ('if test -f "$1"; then echo "\u2714 TC-1 makes a widget"; echo "Ran 1 test in 0.001s"; echo OK; '
                'else echo "\u2716 TC-1 makes a widget"; echo "Ran 1 test in 0.001s"; echo "FAILED (failures=1)"; '
                'exit 1; fi\n')

    def id_item(self, **row_extra) -> dict:
        (self.repo / "idcheck.sh").write_text(self.ID_CHECK)
        git(self.repo, "add", "idcheck.sh")
        git(self.repo, "commit", "-qm", "id check", "--allow-empty")
        row = dict({"command": "sh idcheck.sh fixed.txt", "suite": "focused", "ids": ["TC-1"]}, **row_extra)
        return {"test_commands": [row, COMMANDS[1]], "paths": ["a.py", "fixed.txt"]}

    def canned(self, base: tuple, candidate: tuple):
        """A ``run_argv`` stand-in: ``base`` for a run outside the checkout (the base worktree), else ``candidate``."""
        def run(argv, cwd, timeout, **_kw):
            return base if Path(cwd).resolve() != self.repo else candidate
        return run

    def test_the_base_run_refuses_a_new_test_that_passes_without_the_change(self):
        self.start()

        def present_on_base(state):  # the product file already exists when the item's base is taken
            if nav.current_stage(state) == "prepare":
                (self.repo / "fixed.txt").write_text("already\n")
        self.drive_to("test", step_plan=self.id_item(), each=present_on_base)
        self.assertIn(test_loop.BASE_RULE, " ".join(self.packet().split()))
        (self.repo / "retained.txt").write_text("retained\n")
        action = self.action()
        self.assert_refused(DONE, r"(?s)ShipLoop base run: test is not done.*passed TC-1 on the item's base, "
                                  r"without this item's change", loop=True)
        record = store.read_record(self.run_dir / test_loop.base_path(action, 1))
        self.assertFalse(record["passed"])
        self.assertEqual(record["runs"][0]["status"], "passes-on-base")
        self.assertEqual(test_loop.refused_runs(self.run_dir, action), 1)  # a refused base run counts
        # The named exit: a characterisation test goes in red_na, through the same gate.
        self.assert_refused(dict(DONE, red_na=[{"id": "TC-9", "reason": "x"}]), "red_na", loop=True)
        self.complete(dict(DONE, red_na=[{"id": "TC-1", "reason": "Characterises the widget that already exists."}]))
        self.assertNotEqual(nav.current_stage(self.settle()), "test")
        with self.assertRaisesRegex(nav.NavigatorError, "red_na"):
            nav._canonical_result(dict(DONE, red_na=[{"id": "TC-1", "reason": "x"}]), stage="verify")

    def test_a_new_test_that_fails_on_the_base_is_accepted_once_it_passes_on_the_candidate(self):
        self.start()
        self.drive_to("test", step_plan=self.id_item())
        (self.repo / "retained.txt").write_text("retained\n")
        action = self.action()
        self.assert_refused(DONE, r"(?s)test is not done.*sh idcheck.sh fixed.txt -> exit 1", loop=True)
        base = store.read_record(self.run_dir / test_loop.base_path(action, 1))
        self.assertTrue(base["passed"])
        self.assertEqual(base["runs"][0]["status"], "red")
        self.assertEqual(base["runs"][0]["id_outcomes"], {"TC-1": "failed"})
        (self.repo / "fixed.txt").write_text("fixed\n")
        self.complete(DONE)
        self.assertNotEqual(nav.current_stage(self.settle()), "test")

    def test_a_load_failure_is_red_on_the_base_only_when_it_names_a_file_the_item_adds(self):
        """The defect class test-author's probe guarded: tests load a file the item creates.  On the base that file
        is missing, so the test fails to load; owner decision 3 counts that as RED, and only that."""
        loader = ('if test ! -f widgets.txt; then echo "Error: Cannot find module \'./widgets\'"; exit 1; fi\n'
                  'echo "\u2714 TC-01 makes a widget"; echo "Ran 1 test in 0.001s"; echo OK\n')
        for adds, accepted in ((True, True), (False, False)):
            with self.subTest(adds_the_loaded_file=adds):
                self.restart()
                (self.repo / "run.sh").write_text(loader)
                if not adds:
                    (self.repo / "widgets.txt").write_text("on the base\n")
                self.drive_to("test", step_plan={"test_commands": [
                    {"command": "sh run.sh", "suite": "focused", "ids": ["TC-01"]}, COMMANDS[1]],
                    "paths": ["a.py", "widgets.txt", "run.sh"]})
                (self.repo / "retained.txt").write_text("retained\n")
                if not adds:
                    (self.repo / "widgets.txt").unlink()
                    with mock.patch.object(test_loop.lint, "run_argv", side_effect=self.canned(
                            ("failed", 1, b"Error: Cannot find module './gadgets'\n", b""),
                            ("passed", 0, "\u2714 TC-01 x\nRan 1 test in 0.001s\nOK\n".encode(), b""))):
                        self.assert_refused(DONE, r"did not run TC-01 on the base, and no load failure in its output "
                                                  r"names a file this item adds", loop=True)
                    continue
                (self.repo / "widgets.txt").write_text("created by the item\n")
                action = self.action()
                self.complete(DONE)
                record = store.read_record(self.run_dir / test_loop.base_path(action, 1))
                self.assertEqual(record["runs"][0]["status"], "red")
                self.assertEqual(record["runs"][0]["load_failure_names"], ["widgets.txt"])

    def test_the_base_run_never_gates_an_outcome_other_than_done(self):
        """GUARD: the host can always revise or block, so no command runs for them."""
        for outcome, extra in (("revise", {}), ("blocked", {"blocked_by": "external"})):
            with self.subTest(outcome=outcome):
                self.restart()
                self.drive_to("test", step_plan=self.id_item())
                with mock.patch.object(test_loop, "verify", side_effect=AssertionError("no command runs")), \
                        mock.patch.object(test_loop, "base_check", side_effect=AssertionError("no base run")):
                    self.complete(dict(DONE, outcome=outcome, **extra))
                self.assertEqual(self.state()["status"], "active" if outcome == "revise" else "blocked")

    def test_an_item_with_no_focused_command_has_no_new_test_to_hold_red(self):
        """GUARD: no command, no base command run; a regression command alone is only counted on the base."""
        for name, plan, based in (("test_commands_na", {"test_commands": [], "test_commands_na": "Docs-only item.",
                                                        "paths": ["a.py"]}, False),
                                  ("regression only", {"test_commands": [COMMANDS[1]], "paths": ["a.py"]}, True)):
            with self.subTest(name):
                self.restart()
                self.drive_to("test", step_plan=plan)
                (self.repo / "retained.txt").write_text("retained\n")
                action = self.action()
                self.complete(DONE)
                self.assertNotEqual(nav.current_stage(self.settle()), "test")
                path = self.run_dir / test_loop.base_path(action, 1)
                runs = store.read_record(path)["runs"] if path.exists() else []
                self.assertEqual([run["status"] for run in runs], ["counted"] if based else [])

    def test_the_judge_reads_recorded_node_output_as_a_load_failure(self):
        """A file that fails to load is one synthetic failing test named by its path; no test of it ran, so it reads as
        zero tests at the candidate run, and on the base it is RED only when it names a file the item adds."""
        self.assertEqual(test_loop.counts.count(NODE_LOAD_FAILURE, 1)["ran"], 0)
        focused = {"suite": "focused", "command": "x"}
        listed = dict(focused, ids=["TC-01"])
        self.assertEqual(test_loop.judge(focused, 1, NODE_LOAD_FAILURE)["status"], "no-tests")
        self.assertEqual(test_loop.judge(listed, 1, NODE_LOAD_FAILURE)["status"], "no-tests")
        base = lambda row, out, added: test_loop._judge_base(row, 1, out, [], [], added)["status"]  # noqa: E731
        self.assertEqual(base(listed, NODE_LOAD_FAILURE, []), "not-run")
        self.assertEqual(base(listed, NODE_LOAD_FAILURE, ["widgets.js"]), "red")
        self.assertEqual(base(listed, NODE_ONE_FAILING, []), "red")
        self.assertEqual(base(dict(focused, ids=["TC-02"]), NODE_ONE_FAILING, []), "passes-on-base")

    def test_the_judge_reads_recorded_unittest_load_failure_as_no_test_ran(self):
        """The unittest counterpart of the Node characterisation above: no ID is listed, so only the count refuses it."""
        focused = {"suite": "focused", "command": "x"}
        self.assertEqual(test_loop.counts.count(UNITTEST_LOAD_FAILURE, 1)["ran"], 0)
        self.assertEqual(test_loop.judge(focused, 1, UNITTEST_LOAD_FAILURE)["status"], "no-tests")
        listed = dict(focused, ids=["test_tc_1"])
        self.assertEqual(test_loop._judge_base(listed, 1, UNITTEST_LOAD_FAILURE, [], [], ["widgets.py"])["status"],
                         "red")

    def test_the_base_rules_and_the_duty_sentences_name_no_technology(self):
        """S-8: the engine's prose speaks of a file or module and a test, never of a runner, a language or a product."""
        texts = [test_loop.BASE_RULE, test_loop.FLOOR_RULE, test_loop.RATCHET_RULE]
        for stage, first, last in (("test", "`red_na`: each new test passing on the item base without this change",
                                    "is refused)"),
                                   ("test-spec", "RED: how it fails on the item's base",
                                    "if it already passes.")):
            duty = " ".join(prompts.duty(stage).split())
            self.assertIn(first, duty)
            texts.append(duty[duty.index(first):duty.index(last) + len(last)])
        for text in texts:
            for word in ("node", "npm", "jest", "pytest", "python", "javascript", "java ", "game", "widget"):
                self.assertNotIn(word, text.lower(), word)

    def test_the_whole_word_rule_is_stated_on_the_refusal_and_the_title_fix_is_accepted(self):
        """A1 (a Checkers run, 2026-10-09): tests titled `TC-4a` while the step plan listed `TC-4`.  The refusal named
        `--verbose`, though the runner already printed the names, and the model read the engine source for the rule."""
        self.start()
        self.drive_to("test", step_plan=self.id_item(ids=["TC-4"]))
        (self.repo / "retained.txt").write_text("retained\n")
        action = self.action()
        red = ("failed", 1, "\u2716 TC-4 initial position\nRan 1 test in 0.001s\nFAILED (failures=1)\n".encode(), b"")
        titled = b"\xe2\x9c\x94 TC-4a initial position (0.6ms)\n..\nRan 2 tests in 0.001s\n\nOK\n"
        with mock.patch.object(test_loop.lint, "run_argv", side_effect=self.canned(red, ("passed", 0, titled, b""))):
            with self.assertRaises(nav.NavigatorError) as raised:
                self.complete(DONE)
        flat = " ".join(str(raised.exception).split())
        self.assertIn("did not show TC-4 as a whole word (unittest reported 2 run, 0 failed). A listed ID counts only "
                      "as its own word in a test's printed name", flat)
        self.assertIn("TC-4 appears only inside: \u2714 TC-4a initial position (0.6ms)", flat)
        self.assertIn("`TC-4 (a)`", flat)
        self.assertNotIn("--verbose", flat)
        record = store.read_record(self.run_dir / test_loop.verify_path(action, 1))
        self.assertEqual(record["runs"][0]["ids_inside"], {"TC-4": "\u2714 TC-4a initial position (0.6ms)"})
        renamed = titled.replace(b"TC-4a", b"TC-4 (a)")
        with mock.patch.object(test_loop.lint, "run_argv", side_effect=self.canned(red, ("passed", 0, renamed, b""))):
            self.complete(DONE)
        self.assertNotEqual(nav.current_stage(self.settle()), "test")

    def test_an_id_that_starts_another_id_is_a_missing_test_not_a_title_to_fix(self):
        """GUARD (kills a raw substring match): `TC-1` listed, `TC-10` and `TC-13` printed.  The test is missing;
        "title each test so its ID stands alone" would send the model to retitle tests that are fine, so the
        select-and-print remedy stays."""
        self.start()
        self.drive_to("test", step_plan=self.id_item(ids=["TC-1", "TC-3"]))
        (self.repo / "retained.txt").write_text("retained\n")
        red = ("failed", 1, "\u2716 TC-1 a\n\u2716 TC-3 b\nRan 2 tests in 0.001s\nFAILED (failures=2)\n".encode(), b"")
        printed = (b"\xe2\x9c\x94 TC-10 a (1ms)\n\xe2\x9c\x94 TC-13 b (1ms)\n\xe2\x9c\x94 TC-2 c (1ms)\n"
                   b"...\nRan 3 tests in 0.001s\n\nOK\n")
        with mock.patch.object(test_loop.lint, "run_argv", side_effect=self.canned(red, ("passed", 0, printed, b""))):
            with self.assertRaises(nav.NavigatorError) as raised:
                self.complete(DONE)
        flat = " ".join(str(raised.exception).split())
        self.assertIn("did not show TC-1, TC-3 running (unittest reported 3 run, 0 failed). Make the command select "
                      "those cases and print test names (for example --verbose).", flat)
        self.assertNotIn("as a whole word", flat)
        self.assertNotIn("appears only inside", flat)

    def floor_item(self) -> dict:
        """A step plan whose focused command prints `Ran N tests`, failing while fixed.txt is missing.

        N is read from docs/count.txt in the directory the command runs in, else from n.txt beside the script: the base
        run (a worktree without docs/count.txt) counts ``ran``'s number, the candidate run ``ran_here``'s.  The tally
        lives under docs/ so the mutation check does not take the runner's own number for product code."""
        script = self.repo.parent / "counted.sh"
        script.write_text('n=$(cat docs/count.txt 2>/dev/null || cat "$(dirname "$0")/n.txt")\n'
                          'echo "Ran $n tests in 0.001s"\n'
                          'if test -f "$1"; then echo OK; else echo "FAILED (failures=1)"; exit 1; fi\n')
        command = "sh " + shlex.quote(str(script)) + " fixed.txt"
        return {"test_commands": [{"command": command, "suite": "focused"}, COMMANDS[1]], "paths": ["a.py"]}

    def ran(self, tests: int) -> None:
        (self.repo.parent / "n.txt").write_text(str(tests))

    def ran_here(self, tests: int) -> None:
        (self.repo / "docs").mkdir(exist_ok=True)
        (self.repo / "docs" / "count.txt").write_text(str(tests))

    def loop_done(self) -> dict:
        """The files both commands need, one trivial loop iteration, and the done that cites its terminal packet."""
        (self.repo / "fixed.txt").write_text("fixed\n")
        (self.repo / "retained.txt").write_text("retained\n")
        self.run_loop([TRIVIAL])
        return dict(DONE, evidence_refs=[str(self.terminal())])

    def test_a_test_run_of_fewer_tests_than_the_base_is_refused_and_restoring_them_is_accepted(self):
        """Owner decision 2 (2026-10-10): the floor is the larger of the base run's count and the most an earlier run of
        this action counted, so a test removed or skipped to get green is refused at the same stage."""
        self.start()
        self.ran(3)
        self.drive_to("test", step_plan=self.floor_item())
        self.assertIn(" ".join(test_loop.FLOOR_RULE.split()), " ".join(self.packet().split()))
        action = self.action()
        self.ran_here(2)
        done = self.loop_done()
        with self.assertRaises(nav.NavigatorError) as raised:
            self.complete(done)
        flat = " ".join(str(raised.exception).split())
        self.assertIn("ran fewer tests than its floor (at least 3: 3 on the base) (unittest reported 2 run, 0 failed). "
                      "Restore the tests that were removed or now skip.", flat)
        self.assertNotIn("report revise", flat)  # revise is not open yet at this loop stage
        record = store.read_record(self.run_dir / test_loop.verify_path(action, 1))
        self.assertEqual(record["runs"][0]["status"], "too-few-tests")
        self.assertEqual(test_loop.refused_runs(self.run_dir, action), 1)  # a product failure: it counts toward the cap
        self.assert_refused(dict(done, outcome="revise"), "a complete test loop reports outcome done")
        self.ran_here(3)
        self.complete(done)
        self.assertNotEqual(nav.current_stage(self.settle()), "test")

    def test_the_most_an_earlier_run_of_the_action_counted_is_also_the_floor(self):
        """A command that passed with 5 tests in a run another command failed may not run 4 in the next."""
        self.start()
        self.ran(2)
        self.drive_to("test", step_plan=self.floor_item())
        (self.repo / "fixed.txt").write_text("fixed\n")
        self.ran_here(5)
        self.run_loop([TRIVIAL])
        done = dict(DONE, evidence_refs=[str(self.terminal())])
        self.assert_refused(done, r"\[regression\] test -f retained.txt -> exit 1")  # the focused command ran 5
        (self.repo / "retained.txt").write_text("retained\n")
        self.ran_here(4)
        self.assert_refused(done, r"ran fewer tests than its floor \(at least 5: the larger of 2 on the base and 5 in "
                                  r"an earlier run\)")
        self.ran_here(5)
        self.complete(done)

    def test_a_deliberate_retirement_lowers_the_floor_only_for_a_test_the_base_showed(self):
        self.start()
        self.ran(3)
        plan = self.floor_item()
        script = self.repo.parent / "counted.sh"
        script.write_text('n=$(cat docs/count.txt 2>/dev/null || cat "$(dirname "$0")/n.txt")\n'
                          'test -f docs/count.txt || echo "\u2716 OLD-1 legacy behaviour"\n'
                          'echo "Ran $n tests in 0.001s"\n'
                          'if test -f "$1"; then echo OK; else echo "FAILED (failures=1)"; exit 1; fi\n')
        self.drive_to("test", step_plan=plan)
        self.ran_here(2)
        done = self.loop_done()
        self.assert_refused(dict(done, retired_tests=[{"id": "NEVER-1", "reason": "x"}]),
                            "retired_tests names NEVER-1, which ShipLoop cannot see removed")
        self.assert_refused(dict(done, retired_tests=[{"id": "OLD-1"}]), "retired_tests")
        self.complete(dict(done, retired_tests=[{"id": "OLD-1", "reason": "R-2 replaced the legacy behaviour."}]))
        self.assertNotEqual(nav.current_stage(self.settle()), "test")

    def test_a_verify_rerun_is_held_to_the_count_the_test_stage_accepted(self):
        """The rerun stages hold the ratchet: no fewer tests than ShipLoop accepted for this item since its latest step
        plan; a revised step plan starts the count again."""
        self.start()
        self.ran(3)
        self.drive_to("test", step_plan=self.floor_item())
        self.ran_here(5)
        self.complete(self.loop_done())
        self.drive_to("verify")
        self.assertIn(" ".join(test_loop.RATCHET_RULE.split()), " ".join(self.packet().split()))
        action = self.action()
        self.ran_here(4)
        self.run_loop([TRIVIAL])
        done = dict(DONE, evidence_refs=[str(self.terminal())])
        self.assert_refused(done, r"(?s)verify is not done.*ran fewer tests than its floor \(at least 5: an earlier run "
                                  r"of this command that ShipLoop accepted for this item\)")
        self.assertEqual(store.read_record(self.run_dir / test_loop.verify_path(action, 1))["runs"][0]["accepted_ran"],
                         5)
        self.ran_here(5)
        self.complete(done)
        self.assertNotEqual(nav.current_stage(self.settle()), "verify")

    def test_the_revise_a_verify_floor_refusal_names_is_accepted(self):
        """The verify rerun's floor refusal says "report revise naming what was removed and why"; that route must
        pass verify's real gate (owner rule: test the route, not the wording)."""
        self.start()
        self.ran(3)
        self.drive_to("test", step_plan=self.floor_item())
        self.ran_here(5)
        self.complete(self.loop_done())
        self.drive_to("verify")
        self.ran_here(4)
        self.run_loop([TRIVIAL])
        done = dict(DONE, evidence_refs=[str(self.terminal())])
        self.assert_refused(done, "report revise naming what was removed and why")
        self.complete(dict(done, outcome="revise", summary="The plan changed: one case was removed with R-3."))
        self.assertNotEqual(nav.current_stage(self.settle()), "verify")

    # -- the mutation check (owner decision 2026-10-11: tests after the build must catch something) ----------------

    CALC = "def add(a, b):\n    return a + b\n\n\ndef is_big(n):\n    return n > 10\n"
    EMPTY_TEST = ("import unittest\n\nimport calc  # noqa: F401\n\n\nclass CalcTests(unittest.TestCase):\n"
                  "    def test_tc1(self):\n        self.assertTrue(True)\n")
    REAL_TEST = ("import unittest\n\nimport calc\n\n\nclass CalcTests(unittest.TestCase):\n"
                 "    def test_tc1(self):\n        self.assertEqual(calc.add(2, 3), 5)\n"
                 "        self.assertTrue(calc.is_big(11))\n        self.assertFalse(calc.is_big(10))\n")

    def calc_item(self, test_text: str) -> None:
        """Drive to the test stage of an item that adds calc.py, then write ``test_text`` as its focused test file.

        On the base calc.py is missing, so the test fails to load there: RED by the base rule, whatever it asserts."""
        isolated = mock.patch.dict(os.environ, {"PYTHONDONTWRITEBYTECODE": "1"})
        isolated.start()
        self.addCleanup(isolated.stop)
        self.start()
        self.drive_to("test", step_plan={"test_commands": [
            {"command": "python3 -m unittest -v test_calc", "suite": "focused", "ids": ["test_tc1"]}, COMMANDS[1]],
            "paths": ["a.py", "calc.py", "test_calc.py"]})
        (self.repo / "calc.py").write_text(self.CALC)
        (self.repo / "test_calc.py").write_text(test_text)

    def item(self) -> str:
        return nav._active_cursor(self.state())[2] or ""

    def tree_bytes(self) -> dict:
        files = {str(path.relative_to(self.repo)): path.read_bytes() for path in self.repo.rglob("*")
                 if path.is_file() and ".git" not in path.relative_to(self.repo).parts}
        return {"files": files, "status": git(self.repo, "status", "--porcelain"),
                "worktrees": git(self.repo, "worktree", "list", "--porcelain")}

    def test_a_test_that_only_loads_the_new_module_is_refused_by_the_mutation_check(self):
        """The Checkers defect (88d412e9): every new test was RED on the base only because rules.js could not load.
        The base run still accepts that, and the mutation check refuses the test that asserts nothing."""
        self.calc_item(self.EMPTY_TEST)
        action = self.action()
        self.assertIn("mutates a sample of the changed product lines", " ".join(self.packet().split()))
        self.assert_refused(self.loop_done(), r"(?s)ShipLoop mutation check: test is not done.*"
                                              r"- calc.py:2: ' \+ ' -> ' - '.*the test spec's oracle states")
        base = store.read_record(self.run_dir / test_loop.base_path(action, 1))
        self.assertEqual(base["runs"][0]["status"], "red")  # the load failure of an added file is still RED
        record = store.read_record(self.run_dir / test_loop.mutation_path(action, 1))
        self.assertFalse(record["passed"])
        self.assertEqual(record["killed"], 0)
        self.assertEqual(record["survived"], len(record["mutants"]))
        self.assertGreater(record["survived"], 0)
        self.assertLessEqual(len(record["mutants"]), mutation.MUTANT_SAMPLE)
        self.assertEqual(test_loop.refused_runs(self.run_dir, action), 1)  # counts toward the cap

    def test_a_test_with_a_real_assertion_kills_a_mutant_and_is_accepted(self):
        self.calc_item(self.REAL_TEST)
        action = self.action()
        self.complete(self.loop_done())
        self.assertNotEqual(nav.current_stage(self.settle()), "test")
        record = store.read_record(self.run_dir / test_loop.mutation_path(action, 1))
        self.assertTrue(record["passed"])
        self.assertGreater(record["killed"], 0)
        self.assertEqual(record["unmutated"]["status"], "passed")
        self.assertEqual({row["file"] for row in record["mutants"]}, {"calc.py"})  # never the test file

    def test_a_docs_only_change_passes_with_no_mutants(self):
        self.start()
        self.drive_to("test")
        (self.repo / "docs").mkdir(exist_ok=True)
        (self.repo / "docs" / "guide.md").write_text("Set `limit = 10` when x == 1 is true.\n")
        (self.repo / "fixed.txt").write_text("fixed\n")
        lines = test_loop.mutation_check(self.run_dir, self.state(), self.item(), self.action())
        self.assertEqual(lines, ["mutation: skipped (no mutants: no changed product line matched an operator)"])
        record = store.read_record(self.run_dir / test_loop.mutation_path(self.action(), 1))
        self.assertTrue(record["passed"])
        self.assertEqual(record["mutants"], [])

    def test_the_checkout_is_byte_identical_after_the_check(self):
        self.calc_item(self.REAL_TEST)
        before = self.tree_bytes()
        lines = test_loop.mutation_check(self.run_dir, self.state(), self.item(), self.action())
        self.assertRegex(lines[0], r"^mutation: [1-9]\d* of \d+ mutants")
        self.assertEqual(self.tree_bytes(), before)
        with self.assertRaises(test_loop.TestLoopError):
            (self.repo / "test_calc.py").write_text(self.EMPTY_TEST)
            before = self.tree_bytes()
            test_loop.mutation_check(self.run_dir, self.state(), self.item(), self.action())
        self.assertEqual(self.tree_bytes(), before)

    def test_check_only_runs_the_mutation_check_without_counting(self):
        self.calc_item(self.EMPTY_TEST)
        action = self.action()
        done = self.loop_done()
        path = self.run_dir / "inbox" / (action + ".md")
        path.parent.mkdir(exist_ok=True)
        path.write_text(store.dumps(inner.fill(self.state(), "test", done, self.run_dir), "result"))
        with self.assertRaisesRegex(nav.NavigatorError, r"(?s)mutation check: test is not done.*This check-only run "
                                                        r"does not count toward the refused runs"):
            nav.dispatch(CORE, self.run_dir, self.state(), types.SimpleNamespace(
                command="complete", action=action, result=str(path), check_only=True))
        self.assertTrue((self.run_dir / test_loop.mutation_check_only_path(action)).is_file())
        self.assertFalse((self.run_dir / test_loop.mutation_path(action, 1)).exists())
        self.assertEqual(test_loop.refused_runs(self.run_dir, action), 0)

    def test_the_mutants_skip_comments_and_strings_and_spread_across_files(self):
        rows = mutation.candidates('x = "a == b"  # n > 1 is true\ny = 1 + 2 // 3 < 4\n', [1, 2])
        self.assertEqual([(row["line"], row["original"]) for row in rows], [(2, "1"), (2, " + "), (2, "2")])
        self.assertEqual(mutation.candidates('s = """\nn == 1\n"""\nm = true\n', [2, 4])[0]["replacement"], "false")
        picked = mutation.sample({"a.js": [{"line": i} for i in range(1, 21)], "b.py": [{"line": 1}]}, 8)
        self.assertEqual(len(picked), 8)
        self.assertEqual({row["file"] for row in picked}, {"a.js", "b.py"})
        self.assertEqual(picked, mutation.sample({"a.js": [{"line": i} for i in range(1, 21)], "b.py": [{"line": 1}]},
                                                 8))

    # -- the loop contract travels with the callback (packet review 2026-10-10, rows 3, 8 and 13) -------------------
    #
    # The loop stages were refused 3 times for a terminal packet path missing from evidence_refs (stated only at "Do step 3"),
    # and 3 more times for a loop that had not run, was still active or was not complete (the exit condition was
    # paraphrased as "until every command passes").  Each test renders the real head the CLI prints and submits what it
    # printed.

    def head(self) -> str:
        state = self.state()
        return nav.packet_head(CORE, self.run_dir, state, nav.packet_path(self.run_dir, state))

    @staticmethod
    def template_of(text: str) -> dict:
        return store.loads(text.split("Result template:\n", 1)[1].split("\nAllowed outcomes:", 1)[0])

    def assert_loop_contract_in_head(self, head: str, stage: str, receipt: Path) -> None:
        self.assertEqual(self.template_of(head)["evidence_refs"], [str(receipt)])  # prefilled: nothing to look up
        self.assertIn("receipt (in evidence_refs)",
                      next(row for row in head.splitlines() if row.startswith("Checked by: ")))
        lines = head.splitlines()
        for condition in loops.exit_condition(stage).splitlines():  # the contract's words, not a paraphrase
            self.assertIn(condition, lines)
        self.assertIn(loops.REPEAT[stage], lines)
        self.assertIn(loops.INVOKE_LINE, lines)
        self.assertIn("Receipt: " + str(receipt), lines)
        self.assertNotIn(loops.RECEIPT_REF_LINE, lines)  # the prefilled template and the Checked-by line carry it

    def test_a_loop_head_prefills_the_receipt_prints_the_exit_and_accepts_its_template(self):
        self.start()
        for stage in ("test", "verify"):
            with self.subTest(stage=stage):
                self.drive_to(stage)
                head = self.head()
                self.assert_loop_contract_in_head(head, stage, self.terminal())
                full = self.packet()
                self.assertEqual(full.count("\n" + self.START), 1)  # in the head, not repeated at the tail
                self.assertLess(full.index("\n" + self.START), full.index("Current stage guidance:"))
                # the Until Loop block follows the goal and precedes the status block (the print order of the efficiency
                # plan, 6.1: the start command is in the first part of any print, whatever a cut keeps)
                self.assertGreater(full.index("\n" + self.START), full.index("\nChecked by: "))
                self.assertLess(full.index("\n" + self.START), full.index(nav.STATUS_END))
                # a status hook reads only the first WINDOW bytes (16,000; 8000 before 2026-10-10)
                self.assertLess(head.index(nav.STATUS_END), status_hook.WINDOW)
                if stage == "verify":
                    self.assertGreater(full.index("Change inventory for"), full.index("\n" + self.START))
                (self.repo / "fixed.txt").write_text("fixed\n")
                (self.repo / "retained.txt").write_text("retained\n")
                self.run_loop([TRIVIAL])
                # The printed template, headline and summary written and the evidence_refs left as printed.
                # Re-cut: the template carries an example open item; "fill the template" means replacing it ([] = none).
                filled = dict(self.template_of(head), headline="The loop ran clean.", summary="Every command passed.")
                if "assumptions" in filled:
                    filled["assumptions"] = []
                self.complete(filled)
                self.assertNotEqual(nav.current_stage(self.settle()), stage)

    def test_a_blocked_result_before_the_loop_ran_may_keep_the_prefilled_receipt_and_done_may_not(self):
        """The template prefills evidence_refs with the loop receipt and the head says keep it; blocked before the
        loop ran must not be refused for citing that unwritten file.  Through the real complete gate, at the test stage
        and at verify."""
        for stage in ("test", "verify"):
            with self.subTest(stage=stage):
                self.restart()
                self.drive_to(stage)
                head = self.head()
                template = self.template_of(head)
                receipt = Path(template["evidence_refs"][0])
                self.assertTrue(receipt.name.endswith("-terminal.json"))
                self.assertFalse(receipt.exists())
                filled = dict(template, headline="The loop cannot start here.",
                              summary="The runner the loop needs is not installed in this environment.")
                # done without the receipt is still refused, by the loop's own check.
                self.assert_refused(filled, "terminal|receipt|loop")
                self.complete(dict({k: v for k, v in filled.items() if k != "assumptions"},  # hand-off keys are done-only
                                   outcome="blocked", blocked_by="access"))
                self.assertEqual(self.state()["status"], "blocked")
                self.assertEqual(nav.current_stage(self.state()), stage)
                # the template carries the receipt (kept when you report done) and the Checked-by line names the gate
                self.assertIn("receipt (in evidence_refs)", head)

    def test_a_loop_stage_without_a_resolvable_runtime_accepts_its_template_as_blocked(self):
        """No runtime, no loop: the packet names blocked, and the printed template submitted as blocked (its
        prefilled receipt kept, though no loop can write it) is accepted through the real gate."""
        self.start()
        self.drive_to("test")
        state = self.state()
        state["improve_skill"] = str(self.repo / "missing" / "SKILL.md")
        nav.save(self.run_dir, state)
        head = self.head()
        self.assertIn("Report outcome blocked with this reason.", head)
        template = self.template_of(head)
        self.assert_refused(dict(template, headline="x", summary="y"), "loop has not run|terminal")
        self.complete(dict(template, outcome="blocked", blocked_by="external", headline="No Until Loop runtime.",
                           summary="The bound Improve card cannot be resolved, so no loop can run."))
        self.assertEqual(self.state()["status"], "blocked")

    def test_every_head_keeps_its_status_block_and_milestone_narrative_inside_the_hook_window(self):
        """A status hook reads only the first WINDOW bytes of a head.  The loop lines (conditions, Start, receipt and
        a command list that grows with the commands and the run-dir path) printed before the narrative once pushed the
        milestone's narrative END to byte 8430 while the head told the model the hook already showed it.  Walked with a
        long run directory and six commands, under the CLI entry point that hands the narrative to it."""
        import shiploop_status_hook as hook
        long_run = self.run_dir / ("long-run-directory-" * 6) / "run"
        long_run.mkdir(parents=True)
        self.run_dir = long_run
        commands = [{"command": "sh check.sh fixed.txt --case " + "x" * 40 + str(index), "suite": "focused"}
                    for index in range(5)] + [COMMANDS[1]]
        seen: dict[str, str] = {}

        def check(state: dict) -> None:
            if state.get("active_improve") is not None:
                return
            stage = nav.current_stage(state)
            head = nav.packet_head(CORE, self.run_dir, state, nav.packet_path(self.run_dir, state))
            with self.subTest(stage=stage):
                self.assertLess(head.index(nav.STATUS_END), hook.WINDOW)
                if nav.narrative.BEGIN in head:
                    seen[stage] = head
                    self.assertLess(head.index(nav.narrative.END), hook.WINDOW)
                    self.assertIsNotNone(hook.narrative_text(head))

        with mock.patch.dict(os.environ, {"CLAUDE_CODE_ENTRYPOINT": "cli"}):
            self.start()
            self.drive_to("handoff", step_plan={"test_commands": commands, "paths": ["a.py"]}, each=check)
        loop_heads = [stage for stage in seen if stage in loops.STAGES]
        self.assertTrue(loop_heads, "no inner loop stage carried a milestone narrative")
        for stage in loop_heads:
            self.assertIn("\n" + self.START, seen[stage])

    def test_the_test_stage_done_when_claims_only_what_the_loop_and_the_runs_check(self):
        done = " ".join(stage_spec.stage("test").done_when)
        self.assertNotIn("nothing that passed at baseline fails now", done)
        self.assertIn("every recorded command", done)
        self.assertIn("no new test ID passes on the item's base checkout, unless red_na names it", done)

    # -- the test stage prints what the gate judges -------------------------------------------------------------------

    def test_the_test_packet_lists_the_commands_ids_rules_and_the_red_check_command(self):
        self.start()
        self.drive_to("test", step_plan=self.id_item(ids=["TC-1", "TC-2"], min_tests=2))
        packet = self.packet()
        flat = " ".join(packet.split())
        self.assertIn("1. [focused] sh idcheck.sh fixed.txt (must run: TC-1, TC-2) (at least 2 tests)", packet)
        self.assertIn("2. [regression] test -f retained.txt", packet)
        self.assertIn(" ".join(prompts.ID_WORD_RULE.split()), flat)
        for rule in (test_loop.COUNT_RULE, test_loop.FLOOR_RULE, test_loop.BASE_RULE):
            self.assertIn(" ".join(rule.split()), flat)
        # The loop's work says to run "the red-check command printed in the packet": the packet must print it.
        self.assertIn("run every recorded command, the red-check command", flat)
        red_check = next((line for line in packet.splitlines() if line.lstrip().startswith("red-check: ")), None)
        self.assertIsNotNone(red_check, "the test packet prints no red-check command")
        self.assertIn("--action=" + self.action(), red_check)

    def test_the_red_na_and_retired_tests_shapes_print_once_in_the_test_packet_and_the_rules_point_at_them(self):
        """The shapes of `red_na` and `retired_tests` live in the test duty's item 6 (efficiency plan U13, TD-7): the base
        and floor rules say "(shape: duty 6)" and the template has no "Optional at test" line that prints them again."""
        for route in ("inline", "ask-agent"):
            with self.subTest(route=route):
                header = next(line for line in prompts.prompt("test", delegation=route).splitlines() if line.startswith("6. "))
                self.assertTrue(header.startswith("6. **Result fields.** `red_na`:"), header)
                self.assertIn("`retired_tests`:", " ".join(prompts.duty("test", delegation=route).split()))
        for rule in (test_loop.BASE_RULE, test_loop.FLOOR_RULE):
            self.assertIn("(shape: duty 6)", rule)
            self.assertNotIn('{"id"', rule)
        self.start()
        self.drive_to("test", step_plan=self.id_item())
        packet = self.packet()
        self.assertNotIn("Optional at test:", packet)
        self.assertEqual(packet.count('`[{"id", "reason"}]`'), 1)             # red_na's shape, in duty 6
        self.assertEqual(packet.count('[{"id", "reason": "<the R-<n> or AD-<n> that retires'), 1)    # retired_tests', in duty 6
        self.assertEqual(sum(1 for line in packet.splitlines() if '"reason"' in line and "red_na" in line), 1)
        self.assertEqual(packet.count("(shape: duty 6)"), 2)

    def test_the_red_check_command_runs_the_base_check_without_counting(self):
        """`shiploop red-check` (the loop's own view of the base rule) through the real CLI."""
        self.start()
        self.drive_to("test", step_plan=self.id_item())
        action = self.action()
        cli = [sys.executable, str(PACKAGE / "scripts" / "shiploop"), "red-check", "--run-dir=" + str(self.run_dir),
               "--action=" + action]
        run = subprocess.run(cli, capture_output=True, text=True, timeout=120)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("not counted toward the refused runs", run.stdout)
        self.assertTrue((self.run_dir / test_loop.red_check_path(action)).is_file())
        self.assertEqual(test_loop.refused_runs(self.run_dir, action), 0)
        wrong = subprocess.run(cli[:-1] + ["--action=nav-" + "0" * 32], capture_output=True, text=True, timeout=60)
        self.assertEqual(wrong.returncode, 3)
        self.assertIn("red-check runs only for the current test action", wrong.stderr)

    def test_an_inner_stage_never_offers_replan_and_an_outer_one_still_does(self):
        for name in stage_spec.INNER:
            with self.subTest(stage=name):
                row = stage_spec.stage(name)
                self.assertNotIn("replan", row.outcomes)
                self.assertNotIn("repeat", row.outcomes)
        for name in ("system-test-author", "system-test"):
            with self.subTest(stage=name):
                self.assertIn("replan", stage_spec.stage(name).outcomes)
                self.assertIn("replan", stage_spec.stage(name).test)

    def test_the_test_template_holds_neither_key_duty_6_offers_both_and_the_fill_rule_says_each_key_once(self):
        """The shapes are offered once, by the duty (efficiency plan U13, TD-7); the template's notes no longer repeat them."""
        self.start()
        self.drive_to("test")
        head = self.head()
        template = self.template_of(head)
        self.assertNotIn("red_na", template)  # a placeholder there would flip the stage's judgement
        self.assertNotIn("retired_tests", template)
        tail = head.split("\nAllowed outcomes:", 1)[1]
        self.assertNotIn("red_na", tail)
        self.assertNotIn("retired_tests", tail)
        flat = " ".join(head.split())
        self.assertIn('6. **Result fields.** `red_na`: each new test passing on the item base without this change, '
                      '`[{"id", "reason"}]`. `retired_tests`: each test this item deliberately retires, '
                      '`[{"id", "reason": "<the R-<n> or AD-<n> that retires it>"}]`', flat)
        self.assertIn("each key once", tail)
        self.assertIn("every placeholder", tail)

    def test_a_mismatched_expectation_issues_validate_existing_with_its_check_results(self):
        """validate-existing replaced baseline: ShipLoop runs every expectation's check on the unchanged checkout and
        issues the stage only when one does not match; the packet shows each result, and done is rechecked."""
        self.start()
        plan = {**self.NO_TESTS, "paths": ["a.py"], "test_commands": [], "test_commands_na": "Synthetic fixture.",
                "expectations": [{"id": "E1", "state": "works", "statement": "a.py defines y", "steps": ["S1"],
                                  "paths": ["a.py"], "check": "grep -q '^y = ' a.py"}]}
        self.drive_to("validate-existing", step_plan=plan)
        packet = self.packet()
        self.assertIn("E1", packet)
        self.assertIn("grep -q '^y = ' a.py", packet)
        record = store.read_record(self.run_dir / "expectations" / (self.action() + ".md"))
        self.assertEqual([(row["id"], row["matches"]) for row in record["results"]], [("E1", False)])
        self.assert_refused(DONE, "E1", loop=True)
        self.run_loop([dict(MATERIAL, continuation_assessment="blocked")])  # the loop stops: the plan is wrong
        self.complete(dict(DONE, outcome="revise", evidence_refs=[str(self.terminal())], summary="a.py never defined y; the plan assumed it.",
                           failed_expectations=[{"id": "E1", "actual": "no y in a.py", "route": "steps"}]))
        self.assertEqual(nav.current_stage(self.settle()), "step-plan")


    # -- the gates' outcomes are printed (TD-3) and the refused-run tally shows no cap (TD-10) -------------------------

    def complete_output(self, result: dict, *, check_only: bool = False) -> str:
        """The stdout of the real ``complete`` (or ``complete --check-only``) for the current action."""
        state = self.state()
        action = nav.current_action(state)["id"]
        path = self.run_dir / "inbox" / (action + ".md")
        path.parent.mkdir(exist_ok=True)
        path.write_text(store.dumps(inner.fill(state, "test", result, self.run_dir), "result"))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            nav.dispatch(CORE, self.run_dir, state, types.SimpleNamespace(
                command="complete", action=action, result=str(path), **({"check_only": True} if check_only else {})))
        return buffer.getvalue()

    def status_display_reads(self, output: str) -> bool:
        """Whether the status display (a host hook) finds its block in this print of the callback command."""
        action = self.action()
        command = " ".join(["python3", str(PACKAGE / "scripts" / "shiploop"), "complete", "--run-dir=" + str(self.run_dir),
                            "--action=" + action, "--result=" + str(self.run_dir / "inbox" / (action + ".md"))])
        payload = {"tool_name": "Bash", "tool_input": {"command": command}, "tool_response": {"stdout": output}}
        return status_hook.status_block(payload) is not None

    def gate_lines_of(self, output: str) -> list[str]:
        return [line for line in output.splitlines() if line.startswith("Gates: ")]

    def test_a_gate_that_did_nothing_says_skipped_in_its_record_and_in_the_complete_output(self):
        """TD-3: with no focused or regression command the base run and the mutation check do nothing.  Their records
        said `disposition: passed` (the same word a proof files); they now say `skipped`, keep `passed` true, and
        `complete` prints a Gates line for each after the next packet."""
        self.start()
        self.drive_to("test", step_plan={"test_commands": [], "test_commands_na": "Docs-only item.", "paths": ["a.py"]})
        action = self.action()
        (self.repo / "retained.txt").write_text("retained\n")
        output = self.complete_output(self.loop_done())
        base = store.read_record(self.run_dir / test_loop.base_path(action, 1))
        mutation_record = store.read_record(self.run_dir / test_loop.mutation_path(action, 1))
        for record in (base, mutation_record):
            self.assertEqual(record["disposition"], "skipped")
            self.assertIs(record["passed"], True)
            self.assertTrue(record["skipped"])
        self.assertEqual(self.gate_lines_of(output),
                         ["Gates: base: skipped (no focused or regression command)",
                          "Gates: mutation: skipped (no focused command)"])
        # After the packet, never before it: the status display reads a print that starts at the packet's header.
        self.assertLess(output.index("ShipLoop navigator | "), output.index("Gates: "))
        self.assertTrue(output.rstrip().splitlines()[-1].startswith("Gates: mutation: skipped"))
        self.assertTrue(self.status_display_reads(output), "a Gates line before the header would hide the status display")
        # Every reader of passed/disposition behaves as before: the skipped record is not a refused run.
        self.assertEqual(test_loop.refused_runs(self.run_dir, action), 0)
        self.assertFalse(test_loop.latest_attempt_could_not_run(self.run_dir, action))
        self.assertIsNotNone(test_loop._latest_base(self.run_dir, action, passed=True))

    def test_a_run_whose_item_base_was_never_recorded_skips_two_gates_and_the_candidate_run_still_judges(self):
        """The seeded slices of 1.3.0 ran this way (no item base, so no base run and no mutants) and every record said
        passed.  The candidate run is the one gate left, and the output says so."""
        self.calc_item(self.REAL_TEST)
        action = self.action()
        base_file = self.run_dir / "lint" / "items" / (self.item() + ".md")
        self.assertTrue(base_file.is_file())
        base_file.unlink()
        output = self.complete_output(self.loop_done())
        reason = "no item base was recorded (not a Git checkout, or the base was not captured)"
        lines = self.gate_lines_of(output)
        self.assertEqual(lines[0], "Gates: base: skipped (" + reason + ")")
        self.assertRegex(lines[1], r"^Gates: candidate: \[focused\] python3 -m unittest -v test_calc -> passed")
        self.assertEqual(lines[-1], "Gates: mutation: skipped (" + reason + ")")
        for path in (test_loop.base_path(action, 1), test_loop.mutation_path(action, 1)):
            record = store.read_record(self.run_dir / path)
            self.assertEqual((record["disposition"], record["passed"], record["skipped"]), ("skipped", True, reason))
        self.assertEqual(store.read_record(self.run_dir / test_loop.verify_path(action, 1))["disposition"], "passed")

    def test_a_proof_prints_one_gates_line_per_run_and_the_record_stays_passed(self):
        self.calc_item(self.REAL_TEST)
        action = self.action()
        output = self.complete_output(self.loop_done())
        lines = self.gate_lines_of(output)
        self.assertRegex(lines[0], r"^Gates: base: \[focused\] python3 -m unittest -v test_calc -> red \(\d+ ran\)$")
        self.assertEqual(lines[1], "Gates: base: [regression] test -f retained.txt -> counted")
        self.assertRegex(lines[2], r"^Gates: candidate: \[focused\] python3 -m unittest -v test_calc -> passed \(\d+ ran")
        self.assertEqual(lines[3], "Gates: candidate: [regression] test -f retained.txt -> passed-uncounted")
        self.assertRegex(lines[4], r"^Gates: mutation: [1-9]\d* of \d+ mutants of the changed product lines killed")
        self.assertEqual(len(lines), 5)
        self.assertTrue(self.status_display_reads(output))
        for record in (store.read_record(self.run_dir / test_loop.base_path(action, 1)),
                       store.read_record(self.run_dir / test_loop.mutation_path(action, 1))):
            self.assertEqual(record["disposition"], "passed")
            self.assertNotIn("skipped", record)

    def test_check_only_prints_the_gates_after_its_sentence_and_nothing_is_counted(self):
        self.calc_item(self.REAL_TEST)
        action = self.action()
        output = self.complete_output(self.loop_done(), check_only=True)
        lines = output.rstrip().splitlines()
        self.assertTrue(lines[0].startswith("ShipLoop check-only: every script gate for test accepts this result"))
        self.assertEqual([line.split(" ")[1] for line in lines[1:]], ["base:", "base:", "candidate:", "candidate:", "mutation:"])
        self.assertTrue(all(line.startswith("Gates: ") for line in lines[1:]))
        self.assertEqual(test_loop.refused_runs(self.run_dir, action), 0)
        self.assertFalse((self.run_dir / test_loop.base_path(action, 1)).exists())

    # -- one run per command (U9, packet review 2026-10-17 D-1, DX-2, D-11b; owner decision D5) ------------------------

    def counting_runner(self, calls: list):
        """``run_argv`` that runs each command and records the ones it runs in the checkout (the candidate run or a
        rerun; the base run and the mutation check run elsewhere)."""
        real = test_loop.lint.run_argv

        def run(argv, cwd, timeout, **kw):
            if Path(cwd).resolve() == self.repo:
                calls.append(argv[-1])
            return real(argv, cwd, timeout, **kw)
        return run

    def dispatch(self, result: dict, *, check_only: bool = False) -> str:
        """The stdout of the real ``complete`` (``--check-only`` too) for ``result`` as it stands."""
        state = self.state()
        action = nav.current_action(state)["id"]
        path = self.run_dir / "inbox" / (action + ".md")
        path.parent.mkdir(exist_ok=True)
        path.write_text(store.dumps(result, "result"))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            nav.dispatch(CORE, self.run_dir, state, types.SimpleNamespace(
                command="complete", action=action, result=str(path), **({"check_only": True} if check_only else {})))
        return buffer.getvalue()

    def verify_checked(self) -> tuple:
        """At verify, the loop ended and a passing ``complete --check-only``: (action, done result, its output)."""
        self.start()
        self.drive_to("verify")
        action = self.action()
        self.run_loop([TRIVIAL])
        done = inner.fill(self.state(), "verify", dict(DONE, evidence_refs=[str(self.terminal())]), self.run_dir)
        output = self.dispatch(done, check_only=True)
        self.assertTrue((self.run_dir / test_loop.check_only_path(action)).is_file())
        return action, done, output

    def test_a_command_recorded_twice_is_one_row_and_runs_once_per_run(self):
        """D-1: the chess step plan copied the Focused and Full-suite fences, so rows 7-9 were rows 1-3 again and every
        run deployed and ran them twice.  A regression row that repeats a focused row folds into it, and verify runs it
        once."""
        twice = [{"command": "sh check.sh fixed.txt", "suite": "focused", "criteria": ["C1"]},
                 {"command": "test -f retained.txt", "suite": "regression"},
                 {"command": "sh check.sh fixed.txt", "suite": "regression"}]
        self.start()
        self.drive_to("verify", step_plan={"test_commands": twice, "paths": ["a.py"],
                                           "criteria": [{"id": "C1", "text": "The item's focused check passes."}]})
        self.assertEqual(test_loop.stage_commands(self.state(), "verify", self.item())[0],
                         [{"command": "sh check.sh fixed.txt", "suite": "focused", "criteria": ["C1"], "regression": True},
                          {"command": "test -f retained.txt", "suite": "regression"}])
        self.assertIn("1. [focused] sh check.sh fixed.txt (also recorded as regression)", self.packet())
        calls: list = []
        self.run_loop([TRIVIAL])
        with mock.patch.object(test_loop.lint, "run_argv", side_effect=self.counting_runner(calls)):
            self.complete(dict(DONE, evidence_refs=[str(self.terminal())]))
        self.assertEqual(calls, ["sh check.sh fixed.txt", "test -f retained.txt"])

    def test_complete_after_a_passing_check_only_on_an_unchanged_tree_takes_that_run_and_says_so(self):
        """D5 (D-11b): after a passing check-only the real complete reran all ten org commands (about 104 s) on a tree
        that had not changed.  It now takes the check-only run, and its counted record names which one."""
        action, done, output = self.verify_checked()
        self.assertIn("That complete takes this test run (" + str(self.run_dir / test_loop.check_only_path(action))
                      + ") instead of running the commands again", " ".join(output.split()))
        checked = store.read_record(self.run_dir / test_loop.check_only_path(action))
        with mock.patch.object(test_loop.lint, "run_argv") as runner:
            self.complete(done, loop=False)
            runner.assert_not_called()
        record = store.read_record(self.run_dir / test_loop.verify_path(action, 1))
        self.assertEqual((record["passed"], record["disposition"]), (True, "passed"))
        self.assertEqual(record["reused"]["path"], test_loop.check_only_path(action))
        self.assertEqual(record["reused"]["created_at"], checked["created_at"])
        self.assertIn(record["reused"]["tree"], checked["trees"])
        self.assertEqual([run["command"] for run in record["runs"]], [run["command"] for run in checked["runs"]])
        self.assertNotEqual(nav.current_stage(self.settle()), "verify")

    def test_a_one_byte_edit_or_another_command_list_after_check_only_runs_the_commands_again(self):
        for change in ("tree", "commands"):
            with self.subTest(change=change):
                self.restart()
                action, done, _output = self.verify_checked()
                if change == "tree":
                    (self.repo / "a.py").write_text("x = 2\n")  # one byte
                else:
                    path = self.run_dir / test_loop.check_only_path(action)
                    record = store.read_record(path)
                    record["commands"] = record["commands"][:1]
                    path.write_text(store.dumps(record, "ShipLoop test-loop verification"))
                calls: list = []
                with mock.patch.object(test_loop.lint, "run_argv", side_effect=self.counting_runner(calls)):
                    self.complete(done, loop=False)
                self.assertEqual(calls, ["sh check.sh fixed.txt", "test -f retained.txt"])
                self.assertNotIn("reused", store.read_record(self.run_dir / test_loop.verify_path(action, 1)))

    def test_the_test_stage_takes_a_passing_check_only_candidate_run_held_to_the_new_base_floor(self):
        """At the test stage the base run and the mutation check still run at complete; the candidate run is the
        check-only one, held to the floor the base run sets then, and a Gates line says so."""
        self.start()
        self.ran(3)
        self.drive_to("test", step_plan=self.floor_item())
        action = self.action()
        self.ran_here(3)
        done = self.loop_done()
        self.complete_output(done, check_only=True)
        self.assertNotIn("accepted_ran", store.read_record(self.run_dir / test_loop.check_only_path(action))["runs"][0])
        calls: list = []
        with mock.patch.object(test_loop.lint, "run_argv", side_effect=self.counting_runner(calls)):
            output = self.complete_output(done)
        self.assertEqual(calls, [])
        lines = self.gate_lines_of(output)
        self.assertTrue(lines[2].startswith("Gates: candidate: reused the passed check-only run of "), lines)
        record = store.read_record(self.run_dir / test_loop.verify_path(action, 1))
        self.assertEqual(record["reused"]["path"], test_loop.check_only_path(action))
        self.assertEqual((record["runs"][0]["accepted_ran"], record["runs"][0]["floor_from"]), (3, "3 on the base"))
        self.assertTrue((self.run_dir / test_loop.base_path(action, 1)).is_file())
        self.assertTrue((self.run_dir / test_loop.mutation_path(action, 1)).is_file())

    def test_a_check_only_run_below_the_floor_the_base_run_sets_at_complete_is_run_again_not_taken(self):
        """A refusal always comes from a run made now: the check-only run of 2 tests passed before any base run set a
        floor; at complete the base run counts 3, so the candidate commands run again and that run is refused."""
        self.start()
        self.ran(3)
        self.drive_to("test", step_plan=self.floor_item())
        action = self.action()
        self.ran_here(2)
        done = self.loop_done()
        self.complete_output(done, check_only=True)
        calls: list = []
        with mock.patch.object(test_loop.lint, "run_argv", side_effect=self.counting_runner(calls)):
            with self.assertRaisesRegex(nav.NavigatorError, r"ran fewer tests than its floor \(at least 3: 3 on the base\)"):
                self.complete(done, loop=False)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("reused", store.read_record(self.run_dir / test_loop.verify_path(action, 1)))

    def test_the_test_packet_prints_the_refused_runs_only_above_zero_and_never_the_cap(self):
        self.start()
        self.drive_to("test", step_plan=self.id_item())
        packet = self.packet()
        self.assertNotIn("Refused runs", packet)
        (self.repo / "retained.txt").write_text("retained\n")
        self.assert_refused(DONE, r"Refused runs for this action so far: 1 \(base, candidate and mutation", loop=True)
        packet = " ".join(self.packet().split())
        self.assertIn("Refused runs for this action so far: 1 (base, candidate and mutation runs together); if they keep "
                      "coming, the item goes back to its step plan (revise). A run that times out, cannot start or is "
                      "skipped on budget refuses without counting.", packet)
        self.assertNotIn(" of " + str(test_loop.MAX_REFUSED_RUNS), packet)

    def test_the_test_result_template_asks_the_summary_for_what_no_record_holds(self):
        self.start()
        self.drive_to("test")
        summary = self.template_of(self.head())["summary"]
        self.assertEqual(summary, nav.TEST_SUMMARY_PLACEHOLDER)
        for need in ("tests added by ID and what each asserts", "test decisions retained, refined or superseded and why",
                     "any test changed to pass a run and its independent reason", "ShipLoop's records hold the counts"):
            self.assertIn(need, summary)
        self.restart()
        self.drive_to("verify")  # another looped stage has its own placeholder (U25: what its duty 11 used to list)
        self.assertEqual(self.template_of(self.head())["summary"], prompts.summary_placeholder("verify"))


class ItemScopePathClassTests(unittest.TestCase):
    def test_a_skill_file_is_classified_by_its_path_class(self):
        """GUARD: the skill-stage N/A machinery is gone (carry-forward's skill decision replaced it); a skill's card is
        documentation and its script is code, so document runs for a script change and not for a card change alone."""
        self.assertEqual(item_scope.classify("skills/x/scripts/run.py"), "code")
        self.assertEqual(item_scope.classify("skills/x/SKILL.md"), "docs")
        self.assertFalse(item_scope.behavioural(["skills/x/SKILL.md"]))
        self.assertTrue(item_scope.behavioural(["skills/x/scripts/run.py"]))
        catalog = json.loads(item_scope.CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(catalog["order"], ["test", "metadata-nav", "docs", "config"])
        self.assertEqual(catalog["non_behavioural"], ["metadata-nav", "docs", "config"])
        self.assertEqual(sorted(catalog["classes"]), ["config", "docs", "metadata-nav", "test"])


class ReleaseVerifyReturnedResultTests(unittest.TestCase):
    """Batch 1008, B3 through the real gate: ``complete`` at release-verify in an isolated run that has returned.

    The test-loop driver of ``TestLoopTests`` needs only ``self.repo``, ``self.run_dir`` and its own helpers, so it is
    borrowed; the run here is a real workspace (a worktree beside a source checkout) driven by real ``dispatch`` calls,
    the real Until Loop, the real knowledge gate and a real return.  Only the model's results are synthetic.
    """

    state = TestLoopTests.state
    action = TestLoopTests.action
    packet = TestLoopTests.packet
    complete = TestLoopTests.complete
    finish_improve = TestLoopTests.finish_improve
    drive_to = TestLoopTests.drive_to
    terminal = TestLoopTests.terminal
    run_loop = TestLoopTests.run_loop
    pass_loop = TestLoopTests.pass_loop
    assert_refused = TestLoopTests.assert_refused
    settle = TestLoopTests.settle
    START = TestLoopTests.START

    def setUp(self) -> None:
        # The workspace refuses a repository with custom Git filters; a CI runner's global config carries git-lfs
        # filters, so these real-git tests must not read the machine's Git configuration (as the workspace suite does).
        isolated = mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
        isolated.start()
        self.addCleanup(isolated.stop)
        temp = tempfile.TemporaryDirectory(prefix="shiploop-release-verify-")
        self.addCleanup(temp.cleanup)
        base = Path(temp.name).resolve()
        self.source = base / "source"
        self.source.mkdir()
        git(self.source, "init", "-q")
        git(self.source, "branch", "-M", "main")
        git(self.source, "config", "user.email", "loop@example.invalid")
        git(self.source, "config", "user.name", "Loop Test")
        git(self.source, "config", "commit.gpgsign", "false")
        git(self.source, "config", "core.hooksPath", os.devnull)
        (self.source / "a.py").write_text("x = 1\n")
        (self.source / "check.sh").write_text(CHECK)
        git(self.source, "add", "-A")
        git(self.source, "commit", "-qm", "base")
        self.root = base / "workspace"
        record = workspace.prepare(self.source, self.root)
        self.repo = Path(record["worktree"])
        self.run_dir = Path(record["run_dir"])
        nav.save(self.run_dir, nav.new_state(str(self.repo), "Release-verify fixture.", worktree=True,
                                             improve_skill=str(IMPROVE_CARD), lint_option="off"))

    def return_result(self, exclude: tuple = ()) -> dict:
        """What the host does at release: commit leftovers, review every path in the plan, return."""
        workspace.commit_leftovers(self.root)
        workspace.plan_return(self.root)
        plan = store.read_record(self.root / "return-plan.md")
        for row in plan["paths"]:
            row["disposition"] = "exclude" if row["path"] in exclude or row["disposition"] == "exclude" else "keep"
        store.write_record(self.root / "return-plan.md", plan, "ShipLoop workspace return plan")
        return workspace.execute_return(self.root)

    def test_a_check_that_passes_only_in_the_work_area_is_refused_and_replan_is_the_accepted_exit(self):
        self.drive_to("release")
        self.assertEqual(self.return_result(exclude=("retained.txt",))["kind"], "working-tree-return")
        self.drive_to("release-verify")
        self.assertTrue((self.repo / "retained.txt").exists(), "control: the work area holds the excluded file")
        self.assertFalse((self.source / "retained.txt").exists())
        packet = self.packet()
        self.assertIn("recorded from a clean copy of the result returned to " + str(self.source), packet)
        knowledge_support.write(self.state())  # the knowledge gate runs before the test rerun
        action = self.action()
        before = {path: path.read_bytes() for path in self.source.rglob("*")
                  if path.is_file() and ".git" not in path.parts}

        self.assert_refused(DONE, r"(?s)release-verify is not done.*result returned to.*test -f retained\.txt.*replan")

        record = store.read_record(self.run_dir / test_loop.verify_path(action, 1))
        self.assertEqual(record["observed"]["where"], "returned-result")
        self.assertFalse(record["passed"])
        self.assertEqual(test_loop.refused_runs(self.run_dir, action), 1)
        self.assertEqual({path: path.read_bytes() for path in self.source.rglob("*")
                          if path.is_file() and ".git" not in path.parts}, before, "the user's checkout is untouched")
        # The exit the refusal names is accepted through the same gate, and the corrective item is queued.
        self.complete(dict(DONE, outcome="replan", work_items=[{"id": "W2", "title": "Return retained.txt"}]))
        self.assertIn("W2", [row["id"] for row in self.state()["work_items"]])

    def test_the_handoff_packet_names_the_returned_copy_after_a_passing_release_verify(self):
        self.drive_to("release")
        self.return_result()
        self.drive_to("handoff")
        line = next(row for row in self.packet().splitlines() if row.startswith("Consumer checks (release-verify)"))
        self.assertIn("ran in a clean copy of the result returned to " + str(self.source), line)
        self.assertIn("fast-forward-merge at ", line)
        self.assertNotIn("did not observe", line)

    def test_the_handoff_packet_says_the_checks_did_not_observe_the_checkout_when_nothing_was_returned(self):
        self.drive_to("handoff")  # release-verify passed in the work area: no return was recorded before it
        line = next(row for row in self.packet().splitlines() if row.startswith("Consumer checks (release-verify)"))
        self.assertIn("ran in the work area " + str(self.repo), line)
        self.assertIn("did not observe the user's checkout", line)

    def test_the_handoff_packet_says_no_consumer_check_ran_when_release_plan_recorded_none(self):
        """No consumer check means no test record, and the handoff duty still points at this line, so it is printed."""
        self.drive_to("release-plan")
        self.complete(dict(DONE, consumer_entry={"how": "run python3 a.py", "sources": ["a.py"]},
                           consumer_checks=[], consumer_checks_na="A script with nothing to observe."))
        self.drive_to("handoff")
        line = next(row for row in self.packet().splitlines() if row.startswith("Consumer checks (release-verify)"))
        self.assertIn("did not run: release-plan recorded no consumer check (A script with nothing to observe)", line)

    def test_the_release_verify_packet_before_any_return_says_the_stage_cannot_return_once(self):
        """One statement per packet: the duty says an isolated run's release-verify cannot return; the rerun block must not."""
        self.drive_to("release-verify")
        text = " ".join(self.packet().split())
        self.assertIn("recorded from the work area WORKTREE", text)   # WORKTREE: the References block (2026-10-16)
        self.assertEqual(text.count("cannot return"), 1, text)


class WorktreeItemCommitTests(unittest.TestCase):
    """What a worktree run says and does about the files the item commit leaves (F1, F2 and #5 of the 2026-10-10 review;
    the commit moved from integrate to verify on 2026-10-10).

    The run is a real workspace prepared with ``--exclude notes.md`` (a transient file the caller declared), driven by
    real ``dispatch`` calls; the driver is borrowed from ``TestLoopTests``.
    """

    state = TestLoopTests.state
    action = TestLoopTests.action
    packet = TestLoopTests.packet
    complete = TestLoopTests.complete
    finish_improve = TestLoopTests.finish_improve
    drive_to = TestLoopTests.drive_to
    terminal = TestLoopTests.terminal
    run_loop = TestLoopTests.run_loop
    pass_loop = TestLoopTests.pass_loop
    assert_refused = TestLoopTests.assert_refused
    settle = TestLoopTests.settle
    START = TestLoopTests.START

    def setUp(self) -> None:
        isolated = mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
        isolated.start()
        self.addCleanup(isolated.stop)
        temp = tempfile.TemporaryDirectory(prefix="shiploop-item-commit-")
        self.addCleanup(temp.cleanup)
        base = Path(temp.name).resolve()
        self.source = base / "source"
        self.source.mkdir()
        git(self.source, "init", "-q")
        git(self.source, "branch", "-M", "main")
        git(self.source, "config", "user.email", "loop@example.invalid")
        git(self.source, "config", "user.name", "Loop Test")
        git(self.source, "config", "commit.gpgsign", "false")
        git(self.source, "config", "core.hooksPath", os.devnull)
        (self.source / "a.py").write_text("x = 1\n")
        (self.source / "check.sh").write_text(CHECK)
        git(self.source, "add", "-A")
        git(self.source, "commit", "-qm", "base")
        self.root = base / "workspace"
        record = workspace.prepare(self.source, self.root, exclude=["notes.md"])
        self.repo = Path(record["worktree"])
        self.run_dir = Path(record["run_dir"])
        nav.save(self.run_dir, nav.new_state(str(self.repo), "Item-commit fixture.", worktree=True,
                                             improve_skill=str(IMPROVE_CARD), lint_option="off"))

    def test_the_verify_packet_and_notice_print_plan_returns_rule_from_the_return_routes_one_constant(self):
        """F2 (S-12): the item sentence and the Return route line describe the same commit_leftovers with one text."""
        self.drive_to("verify")
        self.assertEqual(self.state()["execution_mode"], "navigator-worktree")
        (self.repo / "server.log").write_text("listening 3000\n")
        packet = self.packet()
        # The "Considerations" list (with its Develop line) is gone from packets; the rule prints once, in the packet.
        self.assertEqual(" ".join(packet.split()).count(" ".join(stage_spec.RETURN_LEFTOVERS.split())), 1)
        self.assertIn(stage_spec.RETURN_LEFTOVERS, workspace.route_sentence(self.root))
        output = self.complete(DONE)
        notice = next(line for line in output.splitlines() if line.startswith("Not committed"))
        self.assertIn("server.log", notice)
        self.assertIn(stage_spec.RETURN_LEFTOVERS, notice)

    def test_the_item_commit_never_commits_a_path_the_workspace_excludes(self):
        """#5: commit_leftovers honours the caller's --exclude and the protected paths; the item commit did not, so a
        transient notes.md (documentation class) was committed at integrate and reached the return."""
        self.drive_to("verify")
        (self.repo / "a.py").write_text("x = 2\n")
        (self.repo / "README.md").write_text("# Notes\n")
        (self.repo / "notes.md").write_text("scratch\n")
        left = next(line for line in self.packet().splitlines() if line.startswith("Changed, ShipLoop will not commit: "))
        self.assertIn("notes.md", left.split(": ", 1)[1].split(", "))
        self.complete(DONE)
        committed = git(self.repo, "show", "--name-only", "--format=", "HEAD").split()
        self.assertIn("README.md", committed)
        self.assertIn("a.py", committed)
        self.assertNotIn("notes.md", committed)
        self.assertIn("?? notes.md", git(self.repo, "status", "--porcelain"))


class VerifyLimitTests(unittest.TestCase):
    def state(self, repo: Path, command: str) -> dict:
        return {"repo": str(repo), "history": [{"stage": "step-plan", "workitem": "W1", "action": "S1"}],
                "accepted": {"S1": dict(DONE, test_commands=[{"command": command, "suite": "focused"}])}}

    def test_a_command_past_its_timeout_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            writes, refusal = test_loop.verify(root, self.state(root, "sleep 5"), "W1", "A1", "test",
                                               command_timeout=0.5)
        self.assertIn("[focused] sleep 5 -> timed out", refusal)
        self.assertIn("tests/A1-verify1.md", writes)

    def test_a_zero_test_run_is_refused_with_the_ids_to_show(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = self.state(root, "echo 'Tests:       2 skipped, 2 total'")
            state["accepted"]["S1"]["test_commands"][0]["ids"] = ["TC-9", "TC-10"]
            writes, refusal = test_loop.verify(root, state, "W1", "A1", "test")
            record = store.loads(writes["tests/A1-verify1.md"])
        self.assertEqual(record["runs"][0]["status"], "no-tests")
        self.assertRegex(refusal, r"ran no tests \(jest reported 0 run, 0 failed\).*so the output names TC-9, TC-10")
        self.assertIn("running the whole suite instead does not satisfy this", refusal)
        # On the base a skipped-only run did not run the new tests either: not RED, whatever red_na exempts.
        row = {"command": "x", "suite": "focused", "ids": ["TC-9", "TC-10"]}
        skipped = "Tests:       2 skipped, 2 total\n"
        self.assertEqual(test_loop._judge_base(row, 0, skipped, [], [], [])["status"], "not-run")
        self.assertEqual(test_loop._judge_base(row, 0, skipped, ["TC-9"], [], [])["status"], "not-run")

    def test_a_spent_stage_budget_skips_and_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _writes, refusal = test_loop.verify(root, self.state(root, "true"), "W1", "A1", "test",
                                                budget=0.5)
        self.assertIn("[focused] true -> skipped", refusal)


class WholeWordIdTests(unittest.TestCase):
    """A1: what the ids-missing refusal says when a listed ID appears only inside a longer token."""

    PRINT = "printf '%s\\n' '\u2714 TC-4a initial (1ms)' '\u2714 TC-7 move (1ms)' 'Ran 2 tests in 0.001s' '' OK"

    def verify(self, command: str, ids: list, stage: str = "test"):
        state = {"repo": "/", "history": [{"stage": "step-plan", "workitem": "W1", "action": "S1"}],
                 "accepted": {"S1": dict(DONE, test_commands=[{"command": command, "suite": "focused", "ids": ids}])}}
        with tempfile.TemporaryDirectory() as temp:
            writes, refusal = test_loop.verify(Path(temp), state, "W1", "A1", stage)
        return store.loads(writes["tests/A1-verify1.md"])["runs"][0], " ".join(refusal.split())

    def test_an_id_inside_a_longer_token_is_refused_with_the_rule_the_line_and_no_verbose_hint(self):
        run, flat = self.verify(self.PRINT, ["TC-4", "TC-7"])
        self.assertEqual(run["status"], "ids-missing")
        self.assertEqual(run["ids_inside"], {"TC-4": "\u2714 TC-4a initial (1ms)"})
        self.assertIn("did not show TC-4 as a whole word (unittest reported 2 run, 0 failed). "
                      "A listed ID counts only as its own word", flat)
        self.assertIn("TC-4 appears only inside: \u2714 TC-4a initial (1ms)", flat)
        self.assertIn("title it `TC-4 (a)`", flat)
        self.assertNotIn("--verbose", flat)

    def test_an_id_that_never_appears_keeps_the_select_and_print_names_remedy(self):
        """GUARD (passes on the unchanged tree): an ID no line holds keeps the remedy it always had."""
        run, flat = self.verify(self.PRINT, ["TC-9"])
        self.assertNotIn("ids_inside", run)
        self.assertIn("did not show TC-9 running (unittest reported 2 run, 0 failed). Make the command select those "
                      "cases and print test names (for example --verbose).", flat)
        self.assertNotIn("its own word", flat.split("Full output")[0])

    def test_one_refusal_names_both_causes_when_the_ids_differ(self):
        _run, flat = self.verify(self.PRINT, ["TC-4", "TC-9"])
        self.assertIn("did not show TC-4 as a whole word", flat)
        self.assertIn("Also did not show TC-9 running. Make the command select those cases", flat)

    def test_an_id_that_starts_another_id_is_not_reported_inside_it(self):
        """The judge's verdict carries `ids_inside` only for a real whole-token relation (TC-4a), never for TC-10 vs TC-1."""
        row = {"command": "x", "suite": "focused", "ids": ["TC-1", "TC-4"]}
        output = "\u2714 TC-10 a (1ms)\n\u2714 TC-4a b (1ms)\nRan 2 tests in 0.001s\n\nOK\n"
        verdict = test_loop.judge(row, 0, output)
        self.assertEqual((verdict["status"], verdict["ids_missing"]), ("ids-missing", ["TC-1", "TC-4"]))
        self.assertEqual(verdict["ids_inside"], {"TC-4": "\u2714 TC-4a b (1ms)"})
        self.assertNotIn("ids_inside", test_loop.judge(dict(row, ids=["TC-1"]), 0, output))
        run, flat = self.verify("printf '%s\\n' '\u2714 TC-10 a (1ms)' 'Ran 1 test in 0.001s' '' OK", ["TC-1"])
        self.assertNotIn("as a whole word", flat)

    def test_a_longer_token_that_is_itself_a_listed_id_leaves_the_shorter_one_a_missing_test(self):
        """Review of A1: `TC-4` and `TC-4a` are both listed and only `TC-4a` is printed.  `TC-4a` is shown, as listed;
        `TC-4` is a test that is missing, so the select-and-print remedy stays and no title is called wrong."""
        row = {"command": "x", "suite": "focused", "ids": ["TC-4", "TC-4a"]}
        verdict = test_loop.judge(row, 0, "✔ TC-4a b (1ms)\nRan 1 test in 0.001s\n\nOK\n")
        self.assertEqual((verdict["status"], verdict["ids_missing"]), ("ids-missing", ["TC-4"]))
        self.assertNotIn("ids_inside", verdict)
        run, flat = self.verify("printf '%s\\n' '✔ TC-4a b (1ms)' 'Ran 1 test in 0.001s' '' OK", ["TC-4", "TC-4a"])
        self.assertNotIn("ids_inside", run)
        self.assertIn("did not show TC-4 running (unittest reported 1 run, 0 failed). Make the command select those "
                      "cases and print test names (for example --verbose).", flat)
        self.assertNotIn("as a whole word", flat)
        self.assertNotIn("appears only inside", flat)

    def test_the_refusal_quotes_the_first_listed_id_that_is_inside_a_longer_token(self):
        """Several IDs can be inside longer tokens; the one line quoted belongs to the first of them in the step plan's order."""
        command = "printf '%s\\n' '✔ TC-5b five (1ms)' '✔ TC-4a four (1ms)' 'Ran 2 tests in 0.001s' '' OK"
        run, flat = self.verify(command, ["TC-4", "TC-5"])
        self.assertEqual(list(run["ids_inside"]), ["TC-4", "TC-5"])
        self.assertIn("did not show TC-4, TC-5 as a whole word", flat)
        self.assertIn("TC-4 appears only inside: ✔ TC-4a four (1ms)", flat)
        self.assertNotIn("TC-5 appears only inside", flat)

    def test_every_packet_that_says_a_listed_id_is_shown_says_how_it_is_matched(self):
        rule = " ".join(test_loop.guidance.ID_WORD_RULE.split())
        state = {"repo": "/", "history": [{"stage": "step-plan", "workitem": "W1", "action": "S1", "outcome": "done"}],
                 "accepted": {"S1": dict(DONE, test_commands=[{"command": "x", "suite": "focused", "ids": ["TC-4"]},
                                                              {"command": "y", "suite": "regression"}])}}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            parts = {
                "step-plan duty": test_loop.guidance.duty("step-plan"),
                # The head carries loop_lines and the full packet's tail rule_lines.
                "test commands and rules": "\n".join(test_loop.loop_lines(root, state, "W1", "A1", "test")
                                                     + test_loop.rule_lines(state, "W1", "test")),
                "verify rerun": "\n".join(test_loop.rerun_lines(root, state, "W1", "verify")),
            }
        for name, text in parts.items():
            with self.subTest(part=name):
                self.assertEqual(" ".join(text.split()).count(rule), 1)  # each part states it once
        # The test packet prints the rule once, in its command rules; its duty no longer repeats it (2026-10-11).
        self.assertNotIn(rule, " ".join(test_loop.guidance.duty("test").split()))


class CountFloorTests(unittest.TestCase):
    """A5: a run may not run fewer tests than the most an accepted run of the same command ran for the item."""

    COMMAND = 'echo "Ran $(cat n.txt) tests in 0.001s"; echo OK'

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-count-floor-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.state = {"repo": str(self.root), "accepted": {"P1": dict(
            DONE, test_commands=[{"command": self.COMMAND, "suite": "focused"}])},
            "history": [{"stage": "step-plan", "workitem": "W1", "action": "P1", "outcome": "done"}]}

    def run_stage(self, action: str, stage: str, ran: int, item: str = "W1", commands=None, accept: bool = True) -> str:
        """ShipLoop's own run of the command at ``stage`` when it prints ``ran`` tests; returns the refusal.  The action
        enters the history (is accepted) unless the refusal says otherwise or ``accept`` is false."""
        (self.root / "n.txt").write_text(str(ran))
        writes, refusal = test_loop.verify(self.root, self.state, item, action, stage, commands=commands)
        for relative, text in writes.items():
            store.atomic_write_text(self.root / relative, text)
        if not refusal and item and accept:
            self.state["history"].append({"stage": stage, "workitem": item, "action": action, "outcome": "done"})
        return " ".join(refusal.split())

    def record(self, action: str, number: int = 1) -> dict:
        return store.read_record(self.root / test_loop.verify_path(action, number))

    def test_the_highest_accepted_count_is_the_floor_and_both_numbers_are_in_the_refusal(self):
        self.assertEqual(self.run_stage("A1", "test", 5), "")
        self.assertEqual(self.run_stage("A2", "verify", 7), "")  # growth raises the floor
        refusal = self.run_stage("A3", "verify", 6)
        self.assertIn("ran fewer tests than its floor (at least 7: an earlier run of this command that ShipLoop "
                      "accepted for this item) (unittest reported 6 run, 0 failed).", refusal)
        run = self.record("A3")["runs"][0]
        self.assertEqual((run["status"], run["accepted_ran"], run["counts"]["ran"]), ("too-few-tests", 7, 6))
        self.assertEqual(test_loop.refused_runs(self.root, "A3"), 1)
        self.assertEqual(self.run_stage("A3", "verify", 7), "")  # the same action, restored
        self.assertEqual(self.record("A3", 2)["runs"][0]["accepted_ran"], 7)  # a floor that held is recorded too

    def test_the_equal_count_is_accepted(self):
        """GUARD (passes on the unchanged tree; kills a floor that also refuses the count it is)."""
        self.assertEqual(self.run_stage("A1", "test", 5), "")
        self.assertEqual(self.run_stage("A2", "verify", 5), "")

    def test_a_revised_step_plan_starts_the_count_again_and_another_item_has_its_own(self):
        self.assertEqual(self.run_stage("A1", "test", 5), "")
        self.assertIn("at least 5", self.run_stage("A2", "verify", 3))
        self.state["history"] += [{"stage": "verify", "workitem": "W1", "action": "A2", "outcome": "revise"},
                                  {"stage": "step-plan", "workitem": "W1", "action": "P2", "outcome": "done"}]
        self.state["accepted"]["P2"] = dict(DONE, test_commands=self.state["accepted"]["P1"]["test_commands"])
        self.assertEqual(self.run_stage("A4", "test", 3), "")  # the 5 is before W1's latest step plan
        self.state["accepted"]["Q1"] = self.state["accepted"]["P2"]
        self.state["history"].append({"stage": "step-plan", "workitem": "W2", "action": "Q1", "outcome": "done"})
        self.assertEqual(self.run_stage("B1", "test", 1, item="W2"), "")  # W1's records do not floor W2

    def test_only_a_run_ShipLoop_accepted_sets_the_floor(self):
        """GUARD (passes on the unchanged tree): a refused record's counts are not accepted evidence, because a record
        passes only when every command did."""
        both = [{"command": self.COMMAND, "suite": "focused"}, {"command": "test -f ok.txt", "suite": "regression"}]
        self.state["accepted"]["P1"] = dict(DONE, test_commands=both)
        self.assertIn("test -f ok.txt -> exit 1", self.run_stage("A1", "verify", 9))
        self.assertFalse(self.record("A1")["passed"])
        (self.root / "ok.txt").write_text("ok\n")
        self.assertEqual(self.run_stage("A1", "verify", 4), "")  # the retry: the 9 sat in a refused record
        self.assertEqual(self.run_stage("A2", "verify", 4), "")  # and A1, now accepted, still leaves the floor at 4

    def test_a_pass_whose_action_ShipLoop_has_not_accepted_sets_no_floor(self):
        """GUARD (passes on the unchanged tree): the record passed, but a later gate refused the same done, so the action
        is not in the history; the floor is read from accepted actions only (the rule the module states)."""
        self.assertEqual(self.run_stage("A1", "test", 9, accept=False), "")
        self.assertTrue(self.record("A1")["passed"])
        self.assertEqual(self.run_stage("A2", "test", 7), "")  # another action: A1's 9 was never accepted
        # Within one test action every earlier run counts (owner decision 2, 2026-10-10), accepted or not.
        self.assertIn("(at least 9: 9 in an earlier run)", self.run_stage("A1", "test", 7))

    def test_another_items_records_are_not_this_items_floor(self):
        """GUARD (passes on the unchanged tree): each item is held to its own count."""
        self.assertEqual(self.run_stage("A1", "test", 2), "")
        self.state["accepted"]["Q1"] = self.state["accepted"]["P1"]
        self.state["history"] += [{"stage": "step-plan", "workitem": "W2", "action": "Q1", "outcome": "done"}]
        self.assertEqual(self.run_stage("B1", "test", 9, item="W2"), "")
        self.assertEqual(self.run_stage("A2", "verify", 2), "")  # W1 is held to its own 2, not to W2's 9

    def test_a_run_refused_for_another_reason_keeps_that_reason(self):
        """GUARD (passes on the unchanged tree): a run no accepted run precedes has no floor, so its own refusal stands."""
        self.state["accepted"]["P1"]["test_commands"][0]["min_tests"] = 8
        self.state["accepted"]["P1"]["test_commands"][0]["ids"] = ["TC-9"]
        refusal = self.run_stage("A1", "test", 10)  # the ID never shows: refused for that, not for a floor
        self.assertEqual(self.record("A1")["runs"][0]["status"], "ids-missing")
        self.assertNotIn("accepted_ran", self.record("A1")["runs"][0])  # nothing accepted yet: no floor
        self.assertIn("did not show TC-9", refusal)

    def test_the_plans_own_minimum_keeps_its_wording_and_an_accepted_run_is_never_below_it(self):
        self.state["accepted"]["P1"]["test_commands"][0]["min_tests"] = 8
        refusal = self.run_stage("A1", "test", 7)  # nothing accepted yet: the step plan's guess decides
        self.assertIn("ran fewer tests than the step plan requires (at least 8)", refusal)
        self.assertNotIn("earlier run of this command", refusal)
        self.assertNotIn("accepted_ran", self.record("A1")["runs"][0])
        self.assertEqual(self.run_stage("A1", "test", 9), "")  # accepted at 9 against a minimum of 8
        refusal = self.run_stage("A2", "verify", 8)  # now the accepted 9 is the floor, above the plan's 8
        self.assertIn("(at least 9: an earlier run of this command", refusal)

    def test_the_outer_stages_and_the_end_of_work_review_are_not_held_to_a_floor(self):
        """GUARD (passes on the unchanged tree): they rerun commands another stage recorded and have no revise to lower
        a floor, so a floor there could be a dead end; the known limit is written in the module docstring."""
        self.assertEqual(self.run_stage("A1", "test", 9), "")
        rows = [{"command": self.COMMAND, "suite": "focused"}]
        self.assertEqual(self.run_stage("E1", "end-of-work review", 3, item="", commands=rows), "")
        self.state["history"].append({"stage": "system-test-author", "workitem": None, "action": "S2", "outcome": "done"})
        self.state["accepted"]["S2"] = dict(DONE, system_commands=rows)
        self.assertEqual(self.run_stage("Y1", "system-test", 2, item=""), "")
        # The navigator passes no work item at an outer stage; the stage itself is what exempts it, so a caller that did
        # pass the item whose step plan lists the same command would still not be held to that item's count.
        self.assertEqual(self.run_stage("Y2", "system-test", 2, accept=False), "")

    def test_a_count_the_runner_does_not_print_is_never_a_floor(self):
        """An uncounted regression pass, and a focused pass whose IDs all appear though its count cannot be read, have no
        number to hold a rerun to."""
        self.state["accepted"]["P1"]["test_commands"] = [
            {"command": "echo ok", "suite": "regression"},
            {"command": 'echo "TC-1 ok"', "suite": "focused", "ids": ["TC-1"]}]
        self.assertEqual(self.run_stage("A1", "verify", 0), "")  # every command runs here
        self.assertEqual([run["status"] for run in self.record("A1")["runs"]], ["passed-uncounted", "passed"])
        self.assertIsNone(self.record("A1")["runs"][1]["counts"])
        self.assertEqual(test_loop.accepted_counts(self.root, self.state, "W1"), {})

    def test_an_uncounted_pass_after_a_counted_one_is_accepted_and_records_the_floor_it_was_not_held_to(self):
        """Known limit, pinned: a focused command whose IDs all show passes with no readable count, so a floor has no
        number to hold it to (a reporter the counter does not read).  ``accepted_ran`` still says what it was not held to."""
        command = 'if test -f quiet.txt; then echo "TC-1 ok"; else echo "Ran 5 tests in 0.001s"; echo "TC-1 ok"; fi'
        self.state["accepted"]["P1"]["test_commands"] = [{"command": command, "suite": "focused", "ids": ["TC-1"]}]
        self.assertEqual(self.run_stage("A1", "test", 0), "")
        self.assertEqual(self.record("A1")["runs"][0]["counts"]["ran"], 5)
        (self.root / "quiet.txt").write_text("")
        self.assertEqual(self.run_stage("A2", "verify", 0), "")
        run = self.record("A2")["runs"][0]
        self.assertEqual((run["status"], run["counts"], run["accepted_ran"]), ("passed", None, 5))

    def test_the_refusal_names_the_exit_each_stage_really_has(self):
        run = {"status": "too-few-tests", "accepted_ran": 5, "min_tests": 2,
               "counts": {"runners": ["unittest"], "ran": 4, "failed": 0}}
        flat = " ".join(test_loop._explain(run, "test").split())
        self.assertIn("Restore the tests that were removed or now skip.", flat)
        self.assertNotIn("report revise", flat)  # the test stage's exit for a deliberate removal is retired_tests
        self.assertIn("goes in the result's retired_tests with its reason", flat)
        flat = " ".join(test_loop._explain(run, "verify").split())
        self.assertIn("Restore the tests that were removed or now skip.", flat)
        self.assertIn("report revise naming what was removed and why, and the redone step plan starts the "
                      "count again", flat)

    def test_the_item_stage_packets_state_the_floor_and_the_rest_do_not(self):
        self.assertIn(test_loop.RATCHET_RULE, test_loop.rerun_lines(self.root, self.state, "W1", "verify"))
        self.state["accepted"]["S2"] = dict(DONE, system_commands=[{"command": "true", "suite": "regression"}])
        self.state["history"].append({"stage": "system-test-author", "workitem": None, "action": "S2", "outcome": "done"})
        outer = test_loop.rerun_lines(self.root, self.state, "", "system-test")
        self.assertIn(test_loop.COUNT_RULE, outer)
        self.assertNotIn(test_loop.RATCHET_RULE, outer)
        self.assertNotIn(test_loop.FLOOR_RULE, outer)
        rules = test_loop.rule_lines(self.state, "W1", "test")  # the counting rules the test packet prints
        self.assertEqual(rules, [test_loop.COUNT_RULE, test_loop.FLOOR_RULE, test_loop.BASE_RULE])
        self.assertNotIn("revise", test_loop.RATCHET_RULE.replace("is a revise", ""))  # it defers; the refusal names the exit

    def test_the_test_duty_says_what_a_drop_below_the_floor_needs(self):
        duty = " ".join(test_loop.guidance.duty("test").split())
        self.assertIn("`retired_tests`: each test this item deliberately retires", duty)
        self.assertIn("any other drop below a command's floor is refused", duty)


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
            writes, refusal = test_loop.verify(root, self.state(root, "pytest -q"), "W1", "A1", "test",
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
                refusal = self.assert_unavailable(root, "test", command_timeout=0.2)
                self.assertIn("does not count as a refused run", refusal)
                self.assertEqual(test_loop.refused_runs(root, "A1"), 0)
            # The gate never closed, so ShipLoop still runs the commands.
            self.assertNotIn("done is no longer accepted", refusal)

    def test_an_always_unavailable_command_is_given_routes_out_not_a_dead_end(self):
        """The gate cannot fire on could-not-run attempts, so the packet must name the exits.

        Otherwise a command that always hangs loops forever: it can never pass,
        its own hang is run-fixable so `blocked` would be illegal, and the
        refusal cap it would need to reach the stage's remedy never advances.
        """
        for stage, remedy in (("test", "revise"), ("system-test", "replan")):
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
                                               "test", command_timeout=0.2)
            record = self.record(writes)
            for relative, text in writes.items():
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text(text)
            self.assertEqual(test_loop.refused_runs(root, "A1"), 1)
        self.assertEqual(record["disposition"], "failed")
        self.assertIn("Refused runs for this action so far: 1 (base, candidate and mutation runs together)", refusal)
        self.assertNotIn("does not count as a refused run", refusal)

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
                self.assertIn("was refused 11 times; done is no longer accepted", refusal)
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
            self.assertIn("Refused runs for this action so far: 1 (base, candidate and mutation runs together); if they "
                          "keep coming, done is no longer accepted", refusal)
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
            for stage in ("test", "verify", "end-of-work review"):
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
                          "\n".join(test_loop.rerun_lines(root, state, "W1", "verify")))
            outer = "\n".join(test_loop.rerun_lines(root, state, "W1", "system-test"))
            self.assertIn("the outer loop takes corrective work items (replan)", outer)
            self.assertNotIn("step plan (revise)", outer)

    def test_the_rerun_packet_names_where_its_commands_were_recorded(self):
        """The outer stages have no step plan: their commands come from system-test-author and release-plan."""
        with tempfile.TemporaryDirectory() as temp:
            state = self.state(Path(temp), "true")
            for stage, source in (("verify", "the step plan"),
                                  ("system-test", "system-test-author"), ("release-verify", "release-plan")):
                with self.subTest(stage=stage):
                    packet = "\n".join(test_loop.rerun_lines(Path(temp), state, "W1", stage))
                    self.assertIn("runs every test command " + source + " recorded from", packet)
            self.assertNotIn("the step plan recorded",
                             "\n".join(test_loop.rerun_lines(Path(temp), state, "W1", "system-test")))

    def test_the_release_verify_packet_names_where_its_commands_run(self):
        """Batch 1008, B3: the packet says where the recorded consumer checks run, computed afresh at each render."""
        returned = {"kind": "fast-forward-merge", "tree": "a" * 40, "head": "b" * 40, "ahead": False,
                    "source": "/src/repo", "receipt": "/ws/return-receipt.md", "plan": "/ws/return-plan.md",
                    "copy": "/ws/consumer-check"}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            state = dict(self.state(Path(temp), "true"), execution_mode="navigator-worktree")
            with mock.patch.object(test_loop.workspace, "returned_result", return_value=returned):
                packet = "\n".join(test_loop.rerun_lines(root, state, "", "release-verify"))
            self.assertIn("runs every test command release-plan recorded from a clean copy of the result returned to "
                          "/src/repo (fast-forward-merge at " + "b" * 12 + "; receipt /ws/return-receipt.md), made "
                          "fresh at /ws/consumer-check on each done and refuses unless each passes", packet)
            self.assertIn("the copy holds exactly the returned tree", packet)
            with mock.patch.object(test_loop.workspace, "returned_result", return_value=None):
                packet = "\n".join(test_loop.rerun_lines(root, state, "", "release-verify"))
            self.assertIn("recorded from the work area " + temp, packet)
            self.assertIn("do not observe the user's checkout", packet)
            self.assertNotIn("cannot return", packet, "the release-verify duty says it; one statement per packet")
            with mock.patch.object(test_loop.workspace, "returned_result",
                                   side_effect=test_loop.workspace.WorkspaceError("receipt unreadable")):
                packet = "\n".join(test_loop.rerun_lines(root, state, "", "release-verify"))  # never raises
            self.assertIn("not currently known", packet)
            self.assertIn("receipt unreadable", packet)
            # an in-place run, and every stage but release-verify, keep the text they always had
            inplace = self.state(Path(temp), "true")
            self.assertIn("recorded from " + temp + " and refuses", "\n".join(
                test_loop.rerun_lines(root, inplace, "", "release-verify")))
            for stage in ("system-test", "verify"):
                with mock.patch.object(test_loop.workspace, "returned_result", return_value=returned) as read:
                    text = "\n".join(test_loop.rerun_lines(root, dict(state, execution_mode="navigator-worktree"),
                                                              "W1", stage))
                self.assertIn("recorded from " + temp + " and refuses", text)
                read.assert_not_called()

    def test_release_verify_in_place_run_still_runs_in_the_checkout_and_records_it(self):
        """GUARD (the cwd half passes on the unchanged tree): an in-place run never touches a workspace."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "marker.txt").write_text("here\n")
            state = self.state(root, "test -f marker.txt")
            with mock.patch.object(test_loop.workspace, "returned_result",
                                   side_effect=AssertionError("an in-place run reads no workspace")):
                writes, refusal = test_loop.verify(root, state, "", "A-rv", "release-verify")
            record = store.loads(writes["tests/A-rv-verify1.md"])
        self.assertEqual(refusal, "")
        self.assertEqual(record["cwd"], str(root))
        self.assertEqual(record["observed"], {"where": "in-place"})

    def test_the_handoff_packet_carries_where_release_verify_ran(self):
        """A cleared handoff model cannot read a record nothing points to, so the script renders the line."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = self.state(root, "true")
            self.assertEqual(test_loop.observed_lines(root, state), [])  # release-verify not accepted yet: nothing to report
            state["history"].append({"stage": "release-verify", "workitem": None, "action": "A-rv", "outcome": "done"})
            (root / "tests").mkdir()
            record = {"schema": test_loop.SCHEMA, "passed": True, "runs": [], "disposition": "passed"}
            for observed, expected in (
                    ({"where": "work-area", "reason": "no completed return is recorded"},
                     "ran in the work area " + temp + ". No completed return was recorded then, so they did not "
                     "observe the user's checkout: list that as a limit."),
                    ({"where": "returned-result", "kind": "fast-forward-merge", "head": "c" * 40, "source": "/src/repo",
                      "receipt": "/ws/return-receipt.md", "copy": "/ws/consumer-check"},
                     "ran in a clean copy of the result returned to /src/repo (fast-forward-merge at " + "c" * 12),
                    ({"where": "in-place"}, "ran in " + temp + ".")):
                with self.subTest(where=observed["where"]):
                    (root / "tests" / "A-rv-verify1.md").write_text(store.dumps(dict(record, observed=observed), "t"))
                    lines = test_loop.observed_lines(root, state)
                    self.assertEqual(len(lines), 1)
                    self.assertIn("Consumer checks (release-verify) " + expected, lines[0])
                    self.assertIn("Record: " + str(root / "tests" / "A-rv-verify1.md"), lines[0])

    def test_the_handoff_line_says_none_ran_when_release_plan_recorded_no_consumer_check(self):
        """No consumer check means no test record, so the line comes from the plan's own reason, not from a record."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = self.state(root, "true")
            state["accepted"]["S3"] = dict(DONE, consumer_checks=[], consumer_checks_na="A static page; nothing to run.")
            state["history"].append({"stage": "release-verify", "workitem": None, "action": "A-rv", "outcome": "done"})
            self.assertEqual(test_loop.observed_lines(root, state),
                             ["Consumer checks (release-verify) did not run: release-plan recorded no consumer check "
                              "(A static page; nothing to run)."])

    # -- budget-skipped commands, and records written before the disposition field ---

    class Clock:
        """A fake clock the runner advances, so a run can spend its whole budget in no real time."""

        now = 0.0

        def __call__(self) -> float:
            return self.now

    def slow_passing_attempt(self, root: Path, stage: str = "test") -> tuple:
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
            self.assertIn("does not count as a refused run", refusal)
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

    def test_a_timeout_text_at_the_test_stage_names_the_items_own_code_test_or_fixture(self):
        """test-red, which fixed only the tests, is gone; the test stage may fix the product, so a hang there is the
        item's own code, test or fixture to fix."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _writes, refusal = test_loop.verify(root, self.state(root, "sleep 5"), "W1", "A2", "test",
                                                command_timeout=0.2)
        self.assertIn("because of this item's own code, test or fixture is yours to fix", refusal)
        self.assertNotIn("(not the product code)", refusal)

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
            self.assertTrue(test_loop.remedy_open(root, "A1"))  # MAX_REFUSED_RUNS failures open the remedy as before

    def test_a_skipped_gate_record_is_neither_a_refused_run_nor_a_could_not_run_attempt(self):
        """TD-3: a gate that did nothing says `disposition: skipped` and keeps `passed: true`, so every reader behaves as it
        did when the same record said `passed`: it is not a refused run, it is not an attempt that could not run, it does
        not open the remedy, and a passed base record with no runs is still the base the floor reads."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tests").mkdir()
            skipped = {"passed": True, "disposition": "skipped", "skipped": "no item base was recorded", "runs": []}
            store.write_record(root / test_loop.base_path("A1", 1), dict(skipped, schema=test_loop.BASE_SCHEMA, attempt=1))
            store.write_record(root / test_loop.mutation_path("A1", 1), dict(skipped, schema=mutation.SCHEMA, attempt=2))
            self.assertEqual(test_loop.refused_runs(root, "A1"), 0)
            self.assertFalse(test_loop.latest_attempt_could_not_run(root, "A1"))
            self.assertFalse(test_loop.remedy_open(root, "A1"))
            self.assertEqual(test_loop._latest_base(root, "A1", passed=True)["disposition"], "skipped")
            # A refused candidate counts once, and a skipped record after it neither undoes the count nor opens the remedy.
            store.write_record(root / test_loop.verify_path("A1", 1),
                               {"schema": test_loop.SCHEMA, "passed": False, "disposition": "failed", "attempt": 3,
                                "runs": [{"status": "failed"}]})
            store.write_record(root / test_loop.mutation_path("A1", 2), dict(skipped, schema=mutation.SCHEMA, attempt=4))
            self.assertEqual(test_loop.refused_runs(root, "A1"), 1)
            self.assertFalse(test_loop.latest_attempt_could_not_run(root, "A1"))
            self.assertFalse(test_loop.remedy_open(root, "A1"))

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


class RefusedRunTallyTests(unittest.TestCase):
    """TD-10 (owner rule 7, plan decision N3): no text the model reads shows the refused-run cap, and the count shows only
    above zero.  The cap is patched to a number no other text prints, so any digit of it in a text can only come from the
    constant: `grep "of 11"` found nothing before this change because the text was built from the constant, so a grep
    cannot fail; this walk can."""

    CAP = 4242
    REFUSED = range(0, 13)
    TALLY = "Refused runs for this action so far: {n} (base, candidate and mutation runs together)"

    def setUp(self) -> None:
        patched = mock.patch.object(test_loop, "MAX_REFUSED_RUNS", self.CAP)
        patched.start()
        self.addCleanup(patched.stop)

    @staticmethod
    def state(repo: Path, *commands: str) -> dict:
        return UnavailableExecutionTests.state(None, repo, *commands)

    @staticmethod
    def seed(root: Path, refused: int, action: str = "A1") -> None:
        """``refused`` candidate records the product failed, as earlier refused submissions left them."""
        (root / "tests").mkdir(parents=True, exist_ok=True)
        for number in range(1, refused + 1):
            store.write_record(root / test_loop.verify_path(action, number),
                               {"schema": test_loop.SCHEMA, "passed": False, "disposition": "failed",
                                "runs": [{"status": "failed"}]})

    def refusal_texts(self, root: Path, refused: int) -> dict:
        """Every refusal that carries the tally, for a run already refused ``refused`` times."""
        texts: dict[str, str] = {}
        for action in ("A1", "A2", "A3", "A4", "A5"):  # one action per refusal, each already refused ``refused`` times
            self.seed(root, refused, action)
        failing = self.state(root, "false")
        # verify, the product-failure tail (an inner stage) and the uncounted-command tail (an outer stage).
        _writes, texts["verify: product failure"] = test_loop.verify(root, failing, "W1", "A1", "test")
        pipeline = [{"command": "echo ok | grep -q ok", "suite": "focused"}]
        _writes, texts["verify: uncounted outer command"] = test_loop.verify(
            root, self.state(root, "true"), "", "A2", "system-test", commands=pipeline)
        # base_check, both tails: the base run itself is stubbed, since only the tail is under test.
        record = {"disposition": "failed", "passed": False, "runs": [{"status": "passes-on-base"}]}
        with mock.patch.object(test_loop, "check_result_fields"), \
                mock.patch.object(test_loop, "_base_run", return_value=(record, "ShipLoop base run: refused")):
            with self.assertRaises(test_loop.TestLoopError) as caught:
                test_loop.base_check(root, failing, "W1", "A5", None)
        texts["base_check: product failure"] = str(caught.exception)
        unrun = dict(record, disposition="could-not-run", runs=[{"status": "timeout"}])
        with mock.patch.object(test_loop, "check_result_fields"), \
                mock.patch.object(test_loop, "_base_run", return_value=(unrun, "ShipLoop base run: refused")):
            with self.assertRaises(test_loop.TestLoopError) as caught:
                test_loop.base_check(root, failing, "W1", "A3", None)
        texts["base_check: could not run"] = str(caught.exception)
        # The two sentences verify also builds from, called directly with the tally they were given.
        texts["_place_reply"] = test_loop._place_reply("test", refused)
        texts["_unavailable_sentence"] = test_loop._unavailable_sentence(
            "test", refused, [{"status": "skipped"}, {"status": "timeout"}], 600.0, 1800.0)
        # The mutation check refuses a test that kills nothing: its tail is the third tally.
        survivor = {"file": "calc.py", "line": 2, "column": 11, "operator": "arith", "original": " + ",
                    "replacement": " - ", "status": "survived", "seconds": 0.0}
        mutated = {"schema": mutation.SCHEMA, "stage": "test", "work_item": "W1", "mutants": [survivor], "killed": 0,
                   "survived": 1, "not_run": 0}
        with mock.patch.object(mutation, "_check", return_value=mutated):
            with self.assertRaises(test_loop.TestLoopError) as caught:
                mutation.mutation_check(root, failing, "W1", "A4")
        texts["mutation_check"] = str(caught.exception)
        return texts

    def test_no_refusal_and_no_packet_line_prints_the_cap_at_any_count_from_zero_to_twelve(self):
        for refused in self.REFUSED:
            with self.subTest(refused=refused), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.seed(root, refused)
                state = self.state(root, "true")
                packet = "\n".join(test_loop.loop_lines(root, state, "W1", "A1", "test", cli="shiploop"))
                reruns = "\n".join(test_loop.rerun_lines(root, state, "W1", "verify")
                                   + test_loop.rerun_lines(root, state, "", "system-test"))
                texts = {"test packet": packet, "rerun list": reruns, **self.refusal_texts(root, refused)}
                for name, text in texts.items():
                    self.assertTrue(text.strip(), name)
                    self.assertNotIn(str(self.CAP), text, name + " prints the refused-run cap")

    def test_the_test_packet_prints_no_refused_runs_line_at_zero_and_the_count_above_zero(self):
        for refused in self.REFUSED:
            with self.subTest(refused=refused), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.seed(root, refused)
                lines = test_loop.loop_lines(root, self.state(root, "true"), "W1", "A1", "test", cli="shiploop")
                tallies = [line for line in lines if line.startswith("Refused runs")]
                if refused == 0:
                    self.assertEqual(tallies, [])
                    self.assertNotIn("times out", "\n".join(lines))
                else:
                    self.assertEqual(len(tallies), 1)
                    self.assertTrue(tallies[0].startswith(self.TALLY.format(n=refused) + "; if they keep coming, "))
                    self.assertIn("A run that times out, cannot start or is skipped on budget refuses without counting.",
                                  tallies[0])

    def test_every_refusal_names_the_count_so_far_and_counts_the_refusal_it_is(self):
        for refused in (0, 1, 5, 12):
            with self.subTest(refused=refused), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.seed(root, refused)
                texts = self.refusal_texts(root, refused)
                for name in ("verify: product failure", "base_check: product failure", "mutation_check"):
                    self.assertIn(self.TALLY.format(n=refused + 1) + "; if they keep coming, the item goes back to its "
                                  "step plan (revise).", texts[name], name)
                self.assertIn(self.TALLY.format(n=refused + 1) + "; replan does not wait for them.",
                              texts["verify: uncounted outer command"])
                for name in ("_place_reply", "_unavailable_sentence", "base_check: could not run"):
                    clause = "does not count as a refused run" + (" (refused so far: " + str(refused) + ")" if refused else "")
                    self.assertIn(clause, texts[name], name)

    def test_the_route_out_is_kept_without_a_number_and_the_cap_refusal_still_names_the_count(self):
        self.assertEqual(test_loop.refused_note(3, "test"), self.TALLY.format(n=3)
                         + "; if they keep coming, the item goes back to its step plan (revise).")
        self.assertEqual(test_loop.refused_note(3, "system-test"), self.TALLY.format(n=3)
                         + "; if they keep coming, the outer loop takes corrective work items (replan).")
        self.assertIn("if they keep coming, done is no longer accepted for this action.",
                      test_loop.refused_note(1, "end-of-work review"))
        # The stop itself stays script-side: once reached, the refusal names the count and the route out.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.seed(root, self.CAP)
            _writes, refusal = test_loop.verify(root, self.state(root, "true"), "W1", "A1", "test")
            self.assertIn("was refused " + str(self.CAP) + " times; done is no longer accepted", refusal)
            self.assertIn("Report outcome revise", refusal)


if __name__ == "__main__":
    unittest.main()
