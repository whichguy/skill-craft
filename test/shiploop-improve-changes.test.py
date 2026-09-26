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
        refusal = changes.commit_refusal(found, {})
        self.assertIn("did not commit them:\n- app.py\n- new_test.py", refusal)
        self.assertEqual(changes.commit_refusal(found, {"no_commit": "The user said: do not commit."}), "")
        git(self.repo, "add", "app.py", "new_test.py")
        git(self.repo, "commit", "-qm", "review fixes")
        found = changes.review_changes(self.run, self.repo, "A1")
        self.assertEqual(found, (["app.py", "new_test.py"], []))
        self.assertEqual(changes.commit_refusal(found, {}), "")

    def test_no_bind_snapshot_means_unknown(self) -> None:
        self.assertIsNone(changes.review_changes(self.run, self.repo, "missing"))
        self.assertEqual(changes.commit_refusal(None, {}), "")

    def state(self) -> dict:
        return {"repo": str(self.repo), "completed_work_items": ["W1"], "work_items": [{"id": "W1", "title": "t"}],
                "history": [{"stage": "step-plan", "workitem": "W1", "action": "S1"}],
                "accepted": {"S1": {"outcome": "done", "summary": "s", "paths": ["app.py"], "test_commands": [
                    {"command": "sh check.sh", "suite": "focused"},
                    {"command": "sh check.sh", "suite": "regression"}]}}}

    def test_the_end_review_reruns_tests_only_when_it_changed_the_tree(self) -> None:
        child = {"stage": "carry-forward"}
        self.assertEqual([row["command"] for row in changes.rerun_commands(self.state())], ["sh check.sh"])
        self.bind()
        nav._improve_change_gate(self.run, self.state(), "A1", child, {})
        self.assertFalse((self.run / "tests" / "A1-verify1.md").exists())  # unchanged: recorded passes stand
        (self.repo / "app.py").write_text("y = 1\n")  # the review broke the check and committed it
        git(self.repo, "commit", "-qam", "review edit")
        with self.assertRaisesRegex(nav.NavigatorError, r"(?s)end-of-work review is not done.*sh check.sh"):
            nav._improve_change_gate(self.run, self.state(), "A1", child, {})
        (self.repo / "app.py").write_text("x = 3\n")
        git(self.repo, "commit", "-qam", "review fix")
        nav._improve_change_gate(self.run, self.state(), "A1", child, {})
        self.assertTrue(store.read_record(self.run / "tests" / "A1-verify2.md")["passed"])

    def test_a_planning_review_does_not_rerun_tests(self) -> None:
        self.bind()
        (self.repo / "app.py").write_text("y = 1\n")
        git(self.repo, "commit", "-qam", "plan review edit")
        nav._improve_change_gate(self.run, self.state(), "A1", {"stage": "step-plan"}, {})
        self.assertFalse((self.run / "tests").exists())


if __name__ == "__main__":
    unittest.main()
