#!/usr/bin/env python3
"""Confirmation by passing commands: criteria, check commands, system and consumer checks.

A criterion is confirmed only by a command ShipLoop runs.  verify, system-test
and release-verify rerun the commands their planning stage recorded and refuse
done unless each passes.  No real command runs here: a fake runner stands in.
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_navigator as nav  # noqa: E402
import shiploop_navigator_dry_run as dry_run  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402

CRITERIA = [{"id": "C1", "text": "greet() returns the default greeting"},
            {"id": "C2", "text": "README documents --greeting"}]
COMMANDS = [{"command": "python3 -m pytest tests -k greet -v", "suite": "focused", "ids": ["test_greet"],
             "criteria": ["C1"]},
            {"command": "grep -q -- '--greeting' README.md", "suite": "check", "criteria": ["C2"]}]


def step_plan(**extra):
    return {"outcome": "done", "summary": "Plan the greeting change.", "paths": ["src/greet.py"],
            "test_commands": COMMANDS, "criteria": CRITERIA, **extra}


def drive(stage: str, overrides: dict) -> dict:
    """Walk the dry-run declarations to ``stage``, replacing results where ``overrides`` says."""
    state = nav.new_state("/simulation-only/repo", "Confirmation fixture.", delegation=nav.DEFAULT_DELEGATION)
    for step in dry_run.activity():
        if nav.current_stage(state) == stage and step["command"] == "produce":
            return state
        action = nav.current_action(state)["id"]
        if step["command"] == "produce":
            state = nav.apply(state, action, overrides.get(step["at"], step["result"]))
        else:
            state = nav.finish_improve(state, action, step["receipt"], step.get("final_result"))
    raise AssertionError("stage not reached: " + stage)


def runner(exits: dict):
    def run(argv, cwd, timeout, *, input_bytes=b"", env=None):
        command = argv[-1]
        code = exits.get(command, 0)
        out = b"1 passed in 0.01s\ntest_greet PASSED\n" if "pytest" in command and code == 0 else b""
        return "exit", code, out, b""
    return run


class CommandShapeTests(unittest.TestCase):
    def test_check_commands_take_no_test_count_and_pass_on_exit_zero(self) -> None:
        rows = test_loop.normalise_commands(COMMANDS)
        self.assertEqual(rows[1]["suite"], "check")
        self.assertEqual(test_loop.judge(rows[1], 0, "")["status"], "passed")
        self.assertEqual(test_loop.judge(rows[1], 1, "")["status"], "failed")
        with self.assertRaisesRegex(test_loop.TestLoopError, "check command .* takes no ids or min_tests"):
            test_loop.normalise_commands([{"command": "grep -q x f", "suite": "check", "ids": ["T1"]}])
        with self.assertRaisesRegex(test_loop.TestLoopError, "criteria must be a nonempty list"):
            test_loop.normalise_commands([{"command": "x", "suite": "focused", "criteria": []}])

    def test_every_criterion_needs_a_confirming_command(self) -> None:
        nav._canonical_result(step_plan(), stage="step-plan")
        uncovered = [dict(row) for row in COMMANDS]
        uncovered[1] = {"command": "grep -q -- '--greeting' README.md", "suite": "check"}
        with self.assertRaisesRegex(nav.NavigatorError, "uncovered: C2"):
            nav._canonical_result(step_plan(test_commands=uncovered), stage="step-plan")
        unknown = [dict(COMMANDS[0], criteria=["C9"]), COMMANDS[1]]
        with self.assertRaisesRegex(nav.NavigatorError, "not listed: C9"):
            nav._canonical_result(step_plan(test_commands=unknown), stage="step-plan")
        with self.assertRaisesRegex(nav.NavigatorError, "criteria are allowed only on a done step-plan"):
            nav._canonical_result({"outcome": "done", "summary": "x", "criteria": CRITERIA}, stage="verify")

    def test_cli_gates_require_criteria_and_the_outer_command_lists(self) -> None:
        plan = step_plan()
        plan.pop("criteria")
        with self.assertRaisesRegex(nav.NavigatorError, "must list criteria"):
            nav._check_submitted_test_commands("step-plan", plan)
        nav._check_submitted_test_commands("step-plan", step_plan())
        for stage, field in (("system-test-author", "system_commands"), ("release-plan", "consumer_checks")):
            with self.subTest(stage=stage):
                with self.assertRaisesRegex(nav.NavigatorError, f"must list {field}"):
                    nav._check_submitted_recorded_commands(stage, {"outcome": "done", "summary": "x"})
                nav._check_submitted_recorded_commands(stage, {"outcome": "done", "summary": "x", field: [],
                                                           field + "_na": "No command can reach it."})


class ScriptRunTests(unittest.TestCase):
    def test_system_test_and_release_verify_run_the_recorded_commands(self) -> None:
        overrides = {
            "step-plan": step_plan(),
            "system-test-author": {"outcome": "done", "summary": "System tests authored.",
                                   "system_commands": [{"command": "sh e2e.sh", "suite": "check"}]},
            "release-plan": {"outcome": "done", "summary": "Release planned.",
                             "consumer_checks": [{"command": "curl -fsS https://example.test/health",
                                                  "suite": "check"}]},
        }
        for stage, command in (("system-test", "sh e2e.sh"),
                               ("release-verify", "curl -fsS https://example.test/health")):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as temporary:
                state = drive(stage, overrides)
                self.assertIn(stage, test_loop.RERUN_STAGES)
                commands, _ = test_loop.stage_commands(state, stage, "")
                self.assertEqual([row["command"] for row in commands], [command])
                action = nav.current_action(state)["id"]
                root = Path(temporary)
                writes, refusal = test_loop.verify(root, state, "", action, stage, runner=runner({command: 1}))
                self.assertIn(stage + " is not done", refusal)
                writes, refusal = test_loop.verify(root, state, "", action, stage, runner=runner({}))
                self.assertEqual(refusal, "")

    def test_verify_reruns_every_step_plan_command_with_its_criteria(self) -> None:
        state = drive("verify", {"step-plan": step_plan()})
        commands, _ = test_loop.stage_commands(state, "verify", "W1")
        self.assertEqual([row.get("criteria") for row in commands], [["C1"], ["C2"]])
        with tempfile.TemporaryDirectory() as temporary:
            _, refusal = test_loop.verify(Path(temporary), state, "W1", nav.current_action(state)["id"], "verify",
                                          runner=runner({"grep -q -- '--greeting' README.md": 1}))
            self.assertIn("grep -q -- '--greeting' README.md", refusal)


if __name__ == "__main__":
    unittest.main()
