#!/usr/bin/env python3
"""Improve's bundled Until Loop runtime: the review gates the Backchain packet and Improve rely on.

Owner decision 2026-09-26. The runtime records the workspace's Git content tree
at start and, for a gate of two or more trivial reviews, completes after a
trivial, satisfied first report only when that tree is unchanged.

Owner decision 2026-10-04 (fast planning, increment I2). The ShipLoop plan packet's one-pass text tells the host
to write `required_trivial_reviews: 0` for the Backchain planning child. OnePassGateTests reads the gate from the
printed text and drives this runtime with it, so the one-pass exit is proved through the real gate.
"""
from __future__ import annotations

import importlib.util
import re
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
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_prompts as prompts  # noqa: E402

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


class OnePassGateTests(unittest.TestCase):
    """The gate the plan packet prints for the Backchain child, started on the real runtime.

    The packet text, not a constant in this test, supplies the gate: a host copies the printed
    `required_trivial_reviews` into the child's start contract, so that is the value driven here.
    """

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="one-pass-gate-")
        self.addCleanup(temp.cleanup)
        self.workspace = Path(temp.name).resolve() / "plan"
        self.state_dir = Path(temp.name).resolve() / "state"
        self.workspace.mkdir()
        self.state_dir.mkdir()
        (self.workspace / "candidate.json").write_text("{}\n")

    @staticmethod
    def printed(mode: str) -> tuple[int, str]:
        """The gate, and the verbatim exit condition when the packet prints one, from the plan packet of `mode`."""
        text = " ".join(prompts._backchain_guidance("plan", backchain_passes=mode).split())
        gates = re.findall(r"`required_trivial_reviews: (\d+)`", text)
        assert len(gates) == 1, (mode, gates)
        exit_text = re.search(r"verbatim, appending only case-specific clauses: (.+?)\. A pass that completes", text)
        return int(gates[0]), (exit_text.group(1) if exit_text else "Two consecutive reviews find nothing to change.")

    def start(self, mode: str) -> dict:
        gate, exit_condition = self.printed(mode)
        contract = {"workspace": str(self.workspace), "work": "One dependency review/fix/check cycle.",
                    "exit_condition": exit_condition, "repeat_condition": "Repeat for a named open gap.",
                    "required_trivial_reviews": gate,
                    "context": {"request": "r", "scope": "s", "authority": "a", "environment": "e",
                                "resources": []}}
        return runtime.start(contract, self.state_dir)

    @staticmethod
    def report(packet: dict, **fields: str) -> dict:
        token = next(arg.split("=", 1)[1] for arg in packet["done_argv"] if arg.startswith("--action="))
        report = dict(TRIVIAL, **fields)
        return runtime.done(packet["state_file"], token, report)

    def test_the_one_pass_text_prints_gate_zero_and_the_converge_text_prints_two(self) -> None:
        self.assertEqual(self.printed("one")[0], 0)
        self.assertEqual(self.printed("converge")[0], 2)

    def test_a_repairing_first_pass_that_assesses_the_exit_satisfied_completes_after_one_action(self) -> None:
        packet = self.start("one")
        self.assertEqual(packet["progress"]["required_trivial_reviews"], 0)
        terminal = self.report(packet, classification="non-trivial", exit_assessment="satisfied")
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["progress"]["action_number"], 1)
        self.assertEqual(terminal["progress"]["trivial_streak"], 0)

    def test_an_unsatisfied_report_continues_and_the_next_satisfied_report_completes(self) -> None:
        packet = self.start("one")
        active = self.report(packet, classification="non-trivial", exit_assessment="unsatisfied")
        self.assertEqual(active["status"], "active")
        self.assertEqual(active["progress"]["action_number"], 2)  # no ceiling: the open gap keeps the loop going
        terminal = self.report(active, classification="trivial", exit_assessment="satisfied")
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["progress"]["action_number"], 2)

    def test_an_unresolved_report_cannot_claim_a_satisfied_exit(self) -> None:
        packet = self.start("one")
        with self.assertRaisesRegex(runtime.StateError, "unresolved report cannot claim a satisfied exit"):
            self.report(packet, classification="unresolved", exit_assessment="satisfied")
        # the refusal changed nothing: the same action still takes a valid report
        self.assertEqual(self.report(packet, classification="trivial", exit_assessment="satisfied")["status"],
                         "complete")

    def test_a_blocked_report_stops_the_loop(self) -> None:
        packet = self.start("one")
        stopped = self.report(packet, classification="unresolved", exit_assessment="unsatisfied",
                              continuation_assessment="blocked")
        self.assertEqual(stopped["status"], "stopped")

    def test_the_converge_gate_printed_in_the_packet_still_needs_two_trivial_reviews(self) -> None:
        packet = self.start("converge")
        active = self.report(packet, classification="non-trivial", exit_assessment="satisfied")
        self.assertEqual(active["status"], "active")
        active = self.report(active, classification="trivial", exit_assessment="satisfied")
        self.assertEqual(active["status"], "active")  # one trivial review of the repaired candidate is not two
        self.assertEqual(self.report(active, classification="trivial", exit_assessment="satisfied")["status"],
                         "complete")


if __name__ == "__main__":
    unittest.main()
