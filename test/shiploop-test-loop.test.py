#!/usr/bin/env python3
"""Hermetic tests for ShipLoop's script-enforced test loops at test-green and regression.

The run binds the repository's source Improve card, so each loop uses the real
bundled Until Loop runtime, and ShipLoop really runs the recorded commands
(``test -f <file>``) before it accepts done.
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
import shiploop_navigator as nav  # noqa: E402
import shiploop_navigator_v3_prompts as prompts  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402

CORE = types.SimpleNamespace(PACKAGE_ROOT=PACKAGE, REF_DIR=PACKAGE / "references")
DONE = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}
TRIVIAL = {"classification": "trivial", "exit_assessment": "satisfied", "continuation_assessment": "allowed",
           "evidence": "Synthetic iteration: every command exited 0.", "handoff": "Synthetic; nothing remains."}
MATERIAL = dict(TRIVIAL, classification="non-trivial", exit_assessment="unsatisfied",
                evidence="Synthetic iteration: a command failed and the code was fixed.")
COMMANDS = [{"command": "test -f fixed.txt", "suite": "focused"},
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
        recorded = {"test_commands": COMMANDS} if step_plan is None else step_plan
        for _ in range(200):
            state = self.state()
            if state.get("active_improve") is not None:
                self.finish_improve()
                continue
            current = nav.current_stage(state)
            if current == stage:
                return state
            if current == "step-plan":
                self.complete(dict(DONE, **recorded))
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
        self.terminal().write_text(raw)
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

    # -- step plan -----------------------------------------------------------------

    def test_step_plan_must_record_its_test_commands(self):
        self.start()
        self.drive_to("step-plan")
        self.assert_refused(DONE, "a done step-plan result must list test_commands")
        canonical = nav._canonical_result
        for bad, message in (
            ([{"command": "pytest", "suite": "unit"}], "suite must be focused or regression"),
            ([{"command": "pytest\nrm -rf x", "suite": "focused"}], "one nonblank line"),
            ([{"command": "pytest"}], "exactly command and suite"),
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

    # -- contract and packet -------------------------------------------------------

    def test_each_stage_loops_on_its_exact_commands(self):
        self.start()
        self.drive_to("test-green")
        contract = json.loads((self.run_dir / test_loop.contract_path(self.action())).read_text())
        self.assertIn("Test command list:\n1. [focused] test -f fixed.txt\n", contract["work"])
        self.assertNotIn("retained.txt", contract["work"])
        self.assertEqual(contract["exit_condition"], prompts.TEST_EXIT_CONDITION)
        self.assertEqual(contract["required_trivial_reviews"], 1)
        packet = self.packet()
        self.assertIn("Allowed outcomes: done | blocked.", packet)
        self.assertIn("Test loop (bound Until Loop; the loop script counts iterations, at most 4):", packet)
        self.assertIn("  1. [focused] test -f fixed.txt", packet)
        self.assertIn("ShipLoop checks the terminal packet\nagainst the contract and then runs every listed command",
                      packet)
        self.pass_loop()
        self.assertEqual(nav.current_stage(self.state()), "test-refine")
        self.drive_to("regression")
        contract = json.loads((self.run_dir / test_loop.contract_path(self.action())).read_text())
        self.assertIn("1. [focused] test -f fixed.txt\n2. [regression] test -f retained.txt\n", contract["work"])

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
        self.assertEqual([(row["command"], row["exit"]) for row in record["runs"]], [("test -f fixed.txt", 0)])

    def test_script_rerun_refuses_a_loop_that_claimed_green(self):
        self.start()
        self.drive_to("test-green")
        self.run_loop([TRIVIAL])  # claims every command passed; fixed.txt does not exist
        action = self.action()
        done = dict(DONE, evidence_refs=[str(self.terminal())])
        self.assert_refused(done, r"(?s)test-green is not done.*\[focused\] test -f fixed.txt -> exit 1")
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
        self.assert_refused(dict(DONE, outcome="repeat"), "accepts only done or blocked")
        self.run_loop([TRIVIAL], contract_edit=lambda c: c.update(work="Run nothing."))
        self.assert_refused(dict(DONE, evidence_refs=[str(self.terminal())]),
                            "not from a run of this action's contract")
        self.run_loop([TRIVIAL])
        self.assert_refused(DONE, "list the saved terminal packet in evidence_refs")
        self.run_loop([MATERIAL] * 4 + [TRIVIAL])
        self.assert_refused(dict(DONE, evidence_refs=[str(self.terminal())]),
                            "ran 5 iterations; more than 4 is outside the contract")
        self.complete(dict(DONE, outcome="blocked", blocked_by="external", evidence_refs=[str(self.terminal())]))
        self.assertEqual(self.state()["status"], "blocked")

    def test_stopped_loop_reports_blocked_and_runs_no_command(self):
        self.start()
        self.drive_to("test-green")
        stopped = self.run_loop([dict(MATERIAL, continuation_assessment="blocked")])
        self.assertEqual(stopped["status"], "stopped")
        with mock.patch.object(test_loop, "verify", side_effect=AssertionError("no command runs")):
            self.assert_refused(dict(DONE, evidence_refs=[str(self.terminal())]),
                                "a stopped test loop reports outcome blocked")
            self.complete(dict(DONE, outcome="blocked", blocked_by="external", evidence_refs=[str(self.terminal())]))
        self.assertEqual(self.state()["status"], "blocked")

    def test_an_empty_command_list_skips_the_loop_with_its_reason(self):
        self.start()
        self.drive_to("test-green", step_plan={"test_commands": [], "test_commands_na": "Docs-only item."})
        action = self.action()
        self.assertFalse((self.run_dir / test_loop.contract_path(action)).exists())
        self.assertIn("No command to run: Docs-only item. Report done with that reason", self.packet())
        self.complete(DONE)
        self.assertEqual(nav.current_stage(self.state()), "test-refine")
        self.assertFalse((self.run_dir / test_loop.verify_path(action, 1)).exists())

    def test_without_a_bound_runtime_the_script_still_runs_the_commands(self):
        self.start()
        self.drive_to("test-green")
        state = self.state()
        state["improve_skill"] = ""  # a run whose card was never bound: no Until Loop runtime
        nav.save(self.run_dir, state)
        self.assertIn("Unavailable: no Improve card is bound", self.packet())
        self.assert_refused(DONE, r"test -f fixed.txt -> exit 1")
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

    def test_after_three_refused_runs_only_blocked_is_accepted(self):
        self.start()
        self.drive_to("test-refine")
        (self.repo / "retained.txt").unlink()
        for attempt in (1, 2, 3):
            self.assert_refused(DONE, "Refused runs for this action: " + str(attempt) + " of 3")
        (self.repo / "retained.txt").write_text("retained\n")  # even a now-passing tree
        with mock.patch.object(test_loop, "lint", wraps=test_loop.lint) as runner:
            self.assert_refused(DONE, "was refused 3 times; done is no longer accepted")
            runner.run_argv.assert_not_called()
        self.complete(dict(DONE, outcome="blocked", blocked_by="external"))
        self.assertEqual(self.state()["status"], "blocked")

    def run_quality_loop(self) -> None:
        """One trivial quality-loop iteration, saved to the static-checks terminal path."""
        start = next(line for line in self.packet().splitlines() if line.startswith("Start: "))
        words = shlex.split(start[len("Start: "):])
        packet = json.loads(subprocess.run(words[:-2], input=Path(words[-1]).read_text(), text=True,
                                           capture_output=True, check=True, timeout=30).stdout)
        raw = subprocess.run(packet["done_argv"], input=json.dumps(TRIVIAL), text=True,
                             capture_output=True, check=True, timeout=30).stdout
        (self.run_dir / "quality" / (self.action() + "-terminal.json")).write_text(raw)


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

    def test_a_spent_stage_budget_skips_and_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _writes, refusal = test_loop.verify(root, self.state(root, "true"), "W1", "A1", "test-green",
                                                budget=0.5)
        self.assertIn("[focused] true -> skipped", refusal)


if __name__ == "__main__":
    unittest.main()
