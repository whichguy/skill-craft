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
import shlex
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
        self.drive_to("select-work")
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
        self.assertEqual(test_loop._remedy_sentence("end-of-work review"), "the stage reports blocked")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            commands = [{"command": "false", "suite": "regression"}]
            writes, refusal = test_loop.verify(root, self.state(root, "false"), "", "A1",
                                               "end-of-work review", commands=commands)
            self.assertIn("tests/A1-verify1.md", writes)
            self.assertIn("end-of-work review is not done", refusal)
            # No remedy outcome is named for something that is not a graph stage.
            self.assertNotIn("revise", refusal)
            self.assertNotIn("replan", refusal)

    def test_the_rerun_packet_names_its_own_stage_remedy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = self.state(root, "true")
            self.assertIn("the item goes back to its step plan (revise)",
                          "\n".join(test_loop.rerun_lines(state, "W1", "test-refine")))
            outer = "\n".join(test_loop.rerun_lines(state, "W1", "system-test"))
            self.assertIn("the outer loop takes corrective work items (replan)", outer)
            self.assertNotIn("step plan (revise)", outer)


if __name__ == "__main__":
    unittest.main()
