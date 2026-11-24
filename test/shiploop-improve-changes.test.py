#!/usr/bin/env python3
"""Hermetic tests: an Improve review commits what it changes, and an end review that changed files reruns tests.

Real Git repositories in temporary directories; the navigator gate is called
directly with a synthetic state.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_improve_changes as changes  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_store as store  # noqa: E402


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


class ImproveChangesTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-improve-changes-")
        self.addCleanup(temp.cleanup)
        base = Path(temp.name).resolve()
        self.repo, self.run = base / "repo", base / "run"
        self.repo.mkdir()
        self.run.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@example.invalid")
        git(self.repo, "config", "user.name", "T")
        (self.repo / "app.py").write_text("x = 1\n")
        (self.repo / "check.sh").write_text('echo "Ran 1 test in 0.001s"; grep -q "x = " app.py\n')
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        (self.repo / "wip.py").write_text("# the user's own uncommitted work\n")

    def bind(self, action: str = "A1") -> None:
        for relative, text in changes.bind_writes(self.run, self.repo, action).items():
            store.atomic_write_text(self.run / relative, text)

    def test_uncommitted_review_edits_are_refused_and_earlier_work_is_not_counted(self) -> None:
        self.bind()
        found = changes.review_changes(self.run, self.repo, "A1")
        self.assertEqual(found, ([], []))  # wip.py was dirty before the review
        (self.repo / "app.py").write_text("x = 2\n")
        (self.repo / "new_test.py").write_text("def test(): pass\n")
        found = changes.review_changes(self.run, self.repo, "A1")
        self.assertEqual(found, (["app.py", "new_test.py"], ["app.py", "new_test.py"]))
        owed = changes.uncommitted(found, {})
        self.assertEqual(owed, ["app.py", "new_test.py"])
        refusal = changes.commit_refusal(owed, "/run/commit-message.md", "python3 shiploop improve-commit --x",
                                         "python3 shiploop complete --x")
        self.assertIn("did not commit them:\n- app.py\n- new_test.py", refusal)
        self.assertEqual(refusal.splitlines()[0], "Commit this review's changes first: write the message to "
                         "/run/commit-message.md with a file tool, then run: python3 shiploop improve-commit --x")
        self.assertIn("Then run the callback again: python3 shiploop complete --x\n", refusal)
        self.assertEqual(refusal.splitlines()[-1], "If the user or repository said not to commit, record their instruction "
                         "instead: python3 shiploop complete --x --no-commit \"<their instruction>\"")
        self.assertNotIn("receipt", refusal)
        self.assertEqual(changes.uncommitted(found, {"no_commit": "The user said: do not commit."}), [])
        git(self.repo, "add", "app.py", "new_test.py")
        git(self.repo, "commit", "-qm", "review fixes")
        found = changes.review_changes(self.run, self.repo, "A1")
        self.assertEqual(found, (["app.py", "new_test.py"], []))
        self.assertEqual(changes.uncommitted(found, {}), [])

    def test_no_bind_snapshot_means_unknown(self) -> None:
        self.assertIsNone(changes.review_changes(self.run, self.repo, "missing"))
        self.assertEqual(changes.uncommitted(None, {}), [])

    def state(self) -> dict:
        return {"repo": str(self.repo), "completed_work_items": ["W1"], "work_items": [{"id": "W1", "title": "t"}],
                "history": [{"stage": "step-plan", "workitem": "W1", "action": "S1"}],
                "accepted": {"S1": {"outcome": "done", "summary": "s", "paths": ["app.py"], "test_commands": [
                    {"command": "sh check.sh", "suite": "focused"},
                    {"command": "sh check.sh", "suite": "regression"}]}}}

    def test_the_end_review_reruns_tests_only_when_it_changed_the_tree(self) -> None:
        child = {"stage": "reflect-and-revise"}
        self.assertEqual([row["command"] for row in changes.rerun_commands(self.state())], ["sh check.sh"])
        self.bind()
        nav._improve_change_gate(None, self.run, self.state(), "A1", child, {})
        self.assertFalse((self.run / "tests" / "A1-verify1.md").exists())  # unchanged: recorded passes stand
        (self.repo / "app.py").write_text("y = 1\n")  # the review broke the check and committed it
        git(self.repo, "commit", "-qam", "review edit")
        with self.assertRaisesRegex(nav.NavigatorError, r"(?s)end-of-work review is not done.*sh check.sh"):
            nav._improve_change_gate(None, self.run, self.state(), "A1", child, {})
        (self.repo / "app.py").write_text("x = 3\n")
        git(self.repo, "commit", "-qam", "review fix")
        nav._improve_change_gate(None, self.run, self.state(), "A1", child, {})
        self.assertTrue(store.read_record(self.run / "tests" / "A1-verify2.md")["passed"])

    def test_a_planning_review_does_not_rerun_tests(self) -> None:
        self.bind()
        (self.repo / "app.py").write_text("y = 1\n")
        git(self.repo, "commit", "-qam", "plan review edit")
        nav._improve_change_gate(None, self.run, self.state(), "A1", {"stage": "step-plan"}, {})
        self.assertFalse((self.run / "tests").exists())

    def test_rerun_commands_merges_added_tests_and_unions_shared_command_ids(self) -> None:
        state = {
            "repo": str(self.repo),
            "completed_work_items": ["W1", "W2"],
            "work_items": [{"id": "W1", "title": "t1"}, {"id": "W2", "title": "t2"}],
            "history": [
                {"stage": "step-plan", "workitem": "W1", "action": "SP1", "outcome": "done"},
                {"stage": "document", "workitem": "W1", "action": "D1", "outcome": "done"},
                {"stage": "step-plan", "workitem": "W2", "action": "SP2", "outcome": "done"},
            ],
            "accepted": {
                "SP1": {"outcome": "done", "summary": "s", "paths": ["app.py"], "steps": [{"id": "S1"}],
                        "test_commands": [{"command": "sh check.sh", "suite": "focused", "ids": ["TC-1"], "min_tests": 1}]},
                "D1": {"outcome": "done", "summary": "s",
                       "added_tests": [{"id": "TC-ADDED", "command": "sh check.sh"}]},
                "SP2": {"outcome": "done", "summary": "s", "paths": ["app.py"],
                        "test_commands": [{"command": "sh check.sh", "suite": "focused", "ids": ["TC-2"], "min_tests": 3}]},
            },
        }
        rows = changes.rerun_commands(state)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["command"], "sh check.sh")
        self.assertEqual(rows[0]["ids"], ["TC-1", "TC-ADDED", "TC-2"])
        self.assertEqual(rows[0]["min_tests"], 3)

    def test_end_review_runs_review_lint_gate_when_it_changed_files(self) -> None:
        state = dict(self.state(), lint="report",
                     active_improve={"action_id": "A1", "stage": "reflect-and-revise", "improve_action": "IMP1"})
        child = {"stage": "reflect-and-revise"}
        self.bind()
        (self.repo / "app.py").write_text("x = 2\n")
        git(self.repo, "commit", "-qam", "review edit")
        with mock.patch.object(nav.lint, "gate", return_value=(
                {}, None, "ShipLoop lint gate: end-of-work review is not done while 1 new lint finding stands.")
                ) as gate_mock:
            with self.assertRaisesRegex(nav.NavigatorError, "end-of-work review is not done"):
                nav._improve_change_gate(None, self.run, state, "A1", child, {})
        self.assertEqual(gate_mock.call_args.kwargs["stage"], "end-of-work review")

    def test_test_stage_evaluate_enforces_step_spec_refusal_and_opens_send_back(self) -> None:
        """_evaluate must check _step_spec_refusal on `test` done submissions as well as implement/document."""
        import shiploop_loops as loops
        state = {
            "repo": str(self.repo),
            "prompt": "Synthetic prompt",
            "lint": "off",
            "planning_review": "all",
            "work_index": 0,
            "work_items": [{"id": "W1", "title": "t"}],
            "completed_work_items": [],
            "revisions": {},
            "history": [
                {"stage": "step-plan", "workitem": "W1", "action": "SP1", "outcome": "done"},
            ],
            "accepted": {
                "SP1": {"outcome": "done", "summary": "s", "paths": ["app.py"],
                        "steps": [{"id": "S1", "task": "t", "paths": ["app.py"], "criteria": [], "proof": "true"}],
                        "test_commands": [{"command": "sh check.sh", "suite": "focused"}]},
            },
            "action": {"stage": "test", "id": "T1"},
        }
        submitted = {"outcome": "done", "summary": "s", "evidence_refs": []}
        with mock.patch.object(nav, "current_stage", return_value="test"), \
                mock.patch.object(nav, "_loop_receipt", return_value={}), \
                mock.patch.object(nav, "_check_submitted_evidence"), \
                mock.patch.object(nav, "_handoff_gate"), \
                mock.patch.object(nav, "_test_loop_gate", return_value=[]), \
                mock.patch.object(nav, "_step_spec_refusal", return_value="spec rewrite without (W1/S1)") as spec_ref, \
                mock.patch.object(loops, "open_send_back") as open_sb:
            with self.assertRaisesRegex(nav.NavigatorError, "spec rewrite without"):
                nav._evaluate(None, self.run, state, "T1", "test", "W1", submitted, count=True)
        spec_ref.assert_called_once_with(state, "W1")
        open_sb.assert_called_once_with(self.run, "T1", "spec rewrite without (W1/S1)")


if __name__ == "__main__":
    unittest.main()
