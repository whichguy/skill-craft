#!/usr/bin/env python3
"""Rehydration pointers and the evidence gate.

A context lost mid-stage resumes from pointers alone: every packet names this
action's pass log, and the run context index lists what is in progress and the
script's own records.  A result may not cite a local file that does not exist.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
sys.path.insert(0, str(SCRIPTS))

import shiploop_context_index as context_index  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_navigator_dry_run as dry_run  # noqa: E402

ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "SHIPLOOP_KEEPALIVE": "off"}


def drive_to(stage: str) -> dict:
    state = nav.new_state("/simulation-only/repo", "Rehydration fixture.", delegation=nav.DEFAULT_DELEGATION)
    for step in dry_run.activity():
        if nav.current_stage(state) == stage and step["command"] == "produce":
            return state
        action = nav.current_action(state)["id"]
        if step["command"] == "produce":
            state = nav.apply(state, action, step["result"])
        else:
            state = nav.finish_improve(state, action, step["receipt"], step.get("final_result"))
    raise AssertionError("stage not reached: " + stage)


class IndexTests(unittest.TestCase):
    def test_in_progress_names_the_pass_log_and_loop_packets(self) -> None:
        state = drive_to("test-green")
        action = nav.current_action(state)["id"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            text = context_index.render(state, root, "test-green")
            self.assertIn("## In progress", text)
            self.assertIn(f"Pass log (what each pass checked and what is left): {root / 'notes' / (action + '.md')}", text)
            self.assertIn(str(root / "tests" / (action + "-terminal.json")), text)
            self.assertLess(text.index("## In progress"), text.index("## Request"))

    def test_script_records_list_what_the_script_wrote(self) -> None:
        state = drive_to("test-green")
        action = nav.current_action(state)["id"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertNotIn("## Script records", context_index.render(state, root, "test-green"))
            (root / "tests").mkdir()
            record = root / "tests" / (action + "-verify1.md")
            record.write_text("record\n")
            text = context_index.render(state, root, "test-green")
            self.assertIn("## Script records", text)
            self.assertIn(f"- {record}", text)
            self.assertIn("ShipLoop test runs for this action: 1", text)

    def test_revisions_show_in_progress(self) -> None:
        state = drive_to("implement")
        state = nav.apply(state, nav.current_action(state)["id"],
                          {"outcome": "revise", "summary": "Criterion unachievable as planned."})
        text = context_index.render(state, Path("/tmp/run"), nav.current_stage(state))
        self.assertIn("W1 has gone back to step-plan 1 of 2 times", text)

    def test_verify_and_handoff_read_the_evidence_they_judge(self) -> None:
        self.assertTrue({"item:implement", "item:test-green", "item:regression", "item:static-checks"}
                        <= set(context_index.STAGE_READS["verify"]))
        self.assertTrue({"product-acceptance", "operations"} <= set(context_index.STAGE_READS["handoff"]))


class PacketTests(unittest.TestCase):
    def test_active_and_paused_packets_name_the_pass_log(self) -> None:
        state = drive_to("implement")
        action = nav.current_action(state)["id"]
        expected = "This action's pass log"
        packet = nav.render(dry_run.CORE, dry_run.RUN, state)
        self.assertIn(expected, packet)
        self.assertIn(str(dry_run.RUN / "notes" / (action + ".md")), packet)
        paused = nav.control(state, "pause", "The user asked to stop for now.")
        self.assertIn(str(dry_run.RUN / "notes" / (action + ".md")), nav.render(dry_run.CORE, dry_run.RUN, paused))


class GoalFirstTests(unittest.TestCase):
    def test_every_producer_packet_leads_with_its_goal_and_done_when(self) -> None:
        import shiploop_stage_spec as spec
        state = nav.new_state("/simulation-only/repo", "Goal-first fixture.", delegation=nav.DEFAULT_DELEGATION)
        seen = set()
        for step in dry_run.activity():
            stage = nav.current_stage(state)
            if step["command"] == "produce" and stage not in seen:
                seen.add(stage)
                packet = nav.render(dry_run.CORE, dry_run.RUN, state)
                row = spec.stage(stage)
                lines = packet.splitlines()
                header = next(i for i, line in enumerate(lines) if line.startswith("ShipLoop navigator |"))
                with self.subTest(stage=stage):
                    self.assertTrue(lines[header + 1].startswith("Callback for this stage"))
                    self.assertEqual(lines[header + 2], "Goal: " + row.goal[0].upper() + row.goal[1:] + ".")
                    for condition in row.done_when:
                        self.assertIn("- " + condition, packet)
            action = nav.current_action(state)["id"]
            if step["command"] == "produce":
                state = nav.apply(state, action, step["result"])
            else:
                self.assertNotIn("Done when (confirm each", nav.render(dry_run.CORE, dry_run.RUN, state))
                state = nav.finish_improve(state, action, step["receipt"], step.get("final_result"))
        self.assertEqual(len(seen), 34)


class EvidenceGateTests(unittest.TestCase):
    def test_missing_local_files_are_refused_and_other_locators_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            present = Path(temporary) / "note.md"
            present.write_text("note\n")
            nav._check_submitted_evidence({"evidence_refs": [
                str(present), str(present) + "#section", str(present) + ":12", str(present) + ":12:4",
                str(present) + "::Suite::test_case", "https://example.com/x",
                "synthetic://review/spec"]})
            with self.assertRaisesRegex(nav.NavigatorError, "cite files that do not exist: .*missing.md"):
                nav._check_submitted_evidence({"evidence_refs": [str(present), temporary + "/missing.md"]})

    def test_complete_refuses_a_missing_evidence_file_without_advancing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            repo, run = root / "repo", root / "run"
            repo.mkdir()
            init = subprocess.run([sys.executable, str(CLI), "init", f"--repo={repo}", f"--run-dir={run}",
                                   "--prompt=Evidence gate fixture."], capture_output=True, text=True, env=ENV)
            self.assertEqual(init.returncode, 0, init.stderr)
            action = next(part.split("=", 1)[1] for part in init.stdout.split() if part.startswith("--action="))
            inbox = run / "inbox" / (action + ".md")
            result = {"outcome": "done", "summary": "Intake recorded.", "evidence_refs": [str(root / "nope.md")]}
            inbox.write_text("```shiploop-state\n" + json.dumps(result) + "\n```\n")
            before = (run / "state.md").read_bytes()
            refused = subprocess.run([sys.executable, str(CLI), "complete", f"--run-dir={run}",
                                      f"--action={action}", f"--result={inbox}"],
                                     capture_output=True, text=True, env=ENV)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("cite files that do not exist", refused.stderr)
            self.assertEqual((run / "state.md").read_bytes(), before)
            (root / "nope.md").write_text("intake note\n")
            accepted = subprocess.run([sys.executable, str(CLI), "complete", f"--run-dir={run}",
                                       f"--action={action}", f"--result={inbox}"],
                                      capture_output=True, text=True, env=ENV)
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            self.assertIn("| discovery |", accepted.stdout)


if __name__ == "__main__":
    unittest.main()
