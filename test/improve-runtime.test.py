#!/usr/bin/env python3
"""Improve's bundled Until Loop runtime: a trivial first pass that changes nothing completes the loop.

Owner decision 2026-09-26. The runtime records the workspace's Git content tree
at start and, for a gate of two or more trivial reviews, completes after a
trivial, satisfied first report only when that tree is unchanged.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py"
sys.dont_write_bytecode = True  # never leave __pycache__ inside the shipped runtime
spec = importlib.util.spec_from_file_location("until_loop_ephemeral", SCRIPT)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)

TRIVIAL = {"classification": "trivial", "exit_assessment": "satisfied", "continuation_assessment": "allowed",
           "evidence": "Full review; nothing worth changing; checks pass.", "handoff": "Nothing remains."}


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


class UnchangedFirstPassTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="improve-runtime-")
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name).resolve() / "repo"
        self.state_dir = Path(temp.name).resolve() / "state"
        self.repo.mkdir()
        self.state_dir.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "r@example.invalid")
        git(self.repo, "config", "user.name", "R")
        (self.repo / "app.py").write_text("x = 1\n")
        (self.repo / ".gitignore").write_text("build/\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        (self.repo / "wip.py").write_text("# uncommitted work that was already there\n")

    def start(self, reviews: int = 2, workspace: Path | None = None) -> dict:
        contract = {"workspace": str(workspace or self.repo), "work": "Review the candidate.",
                    "exit_condition": "Reviews find nothing worth changing.", "repeat_condition": "Repeat.",
                    "required_trivial_reviews": reviews,
                    "context": {"request": "r", "scope": "s", "authority": "a", "environment": "e",
                                "resources": []}}
        return runtime.start(contract, self.state_dir)

    def done(self, packet: dict, report: dict = TRIVIAL) -> dict:
        path = packet["state_file"]
        token = next(arg.split("=", 1)[1] for arg in packet["done_argv"] if arg.startswith("--action="))
        return runtime.done(path, token, report)

    def test_a_trivial_first_pass_that_changed_nothing_completes(self) -> None:
        packet = self.start()
        (self.repo / "build").mkdir()
        (self.repo / "build" / "out.txt").write_text("ignored output\n")  # ignored files do not count
        (self.repo / ".shiploop-improve").mkdir()
        (self.repo / ".shiploop-improve" / "review-one.md").write_text("review\n")  # nor review notes
        terminal = self.done(packet)
        self.assertEqual(terminal["status"], "complete")
        self.assertTrue(terminal["progress"]["unchanged_first_pass"])
        self.assertEqual(terminal["progress"]["trivial_streak"], 1)
        self.assertIn("workspace unchanged", terminal["instruction"])

    def test_a_first_pass_that_changed_a_file_needs_the_second_review(self) -> None:
        for change in (lambda: (self.repo / "app.py").write_text("x = 2\n"),
                       lambda: (self.repo / "new_test.py").write_text("def test(): pass\n"),
                       lambda: (self.repo / "wip.py").write_text("# edited during the review\n")):
            with self.subTest(change=change):
                packet = self.start()
                change()
                active = self.done(packet)
                self.assertEqual(active["status"], "active")
                terminal = self.done(active)
                self.assertEqual(terminal["status"], "complete")
                self.assertNotIn("unchanged_first_pass", terminal["progress"])
                self.assertEqual(terminal["progress"]["trivial_streak"], 2)

    def test_a_committed_change_is_still_a_change(self) -> None:
        packet = self.start()
        (self.repo / "app.py").write_text("x = 3\n")
        git(self.repo, "commit", "-qam", "review fix")
        self.assertEqual(self.done(packet)["status"], "active")

    def test_only_a_trivial_satisfied_first_report_qualifies(self) -> None:
        packet = self.start()
        self.assertEqual(self.done(packet, dict(TRIVIAL, exit_assessment="unsatisfied"))["status"], "active")
        packet = self.start()
        self.assertEqual(self.done(packet, dict(TRIVIAL, classification="non-trivial"))["status"], "active")

    def test_outside_git_the_full_gate_applies(self) -> None:
        plain = self.state_dir.parent / "plain"
        plain.mkdir()
        packet = self.start(workspace=plain)
        self.assertEqual(self.done(packet)["status"], "active")

    def test_a_one_review_gate_is_unchanged(self) -> None:
        terminal = self.done(self.start(reviews=1))
        self.assertEqual(terminal["status"], "complete")
        self.assertNotIn("unchanged_first_pass", terminal["progress"])


if __name__ == "__main__":
    unittest.main()
