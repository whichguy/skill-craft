#!/usr/bin/env python3
"""Rehydration pointers and the evidence gate.

A context lost mid-stage resumes from pointers alone: every packet names this
action's pass log, and the run context index lists what is in progress and the
script's own records.  A result may not cite a local file that does not exist.
"""

from __future__ import annotations

import contextlib
import io
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
            line = next(line for line in text.splitlines() if line.startswith("- Pass log"))
            self.assertTrue(line.endswith(f": {root / 'notes' / (action + '.md')}"), line)
            self.assertIn("if it exists", line)
            self.assertIn(str(root / "tests" / (action + "-terminal.json")), text)
            self.assertNotIn("-latest.json", text)  # nothing writes it; the receipt is the one loop record
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

    def test_the_pass_log_line_tells_the_pass_to_create_it_and_a_reset_to_open_it_only_if_it_exists(self) -> None:
        # Wording-level check, not a refusal route: the packet file is written once, when the action starts,
        # and a context lost mid-stage re-reads that file, so the line must be true whether or not the host
        # has created the log by then.
        state = drive_to("implement")
        line = next(line for line in nav.render(dry_run.CORE, dry_run.RUN, state).splitlines()
                    if line.startswith("This action's pass log"))
        for part in ("optional", "ShipLoop does not create it", "Create it when the pass starts",
                     "append after each pass what you checked and what is left",
                     "open it first if it exists", "nothing was logged"):
            self.assertIn(part, line)
        self.assertNotIn("open it first after a reset)", line)  # the unconditional promise of a file

    def test_emit_creates_the_notes_directory_the_packet_names(self) -> None:
        # Every packet names a pass log under <run>/notes and the evidence gate refuses a result that cites a file
        # that is not there, so a model that has to mkdir first loses a call (Battleship intake, events 30-34).
        # ShipLoop creates the directory beside scratch/; it still never creates the log (the rule line above).
        state = drive_to("implement")
        action = nav.current_action(state)["id"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "run"
            root.mkdir()
            with contextlib.redirect_stdout(io.StringIO()):
                nav.emit(dry_run.CORE, root, state)
            self.assertTrue((root / "scratch").is_dir())
            self.assertTrue((root / "notes").is_dir())
            log = context_index.pass_log_path(root, action)
            self.assertEqual(log.parent, root / "notes")
            self.assertFalse(log.exists())  # the directory only: the log stays the model's to create
            log.write_text("Checked the first pass; the second is left.\n")
        # The reference row says what the script now does, so a reader does not mkdir what already exists.
        reference = (ROOT / "skills" / "shiploop" / "references" / "state-files.md").read_text(encoding="utf-8")
        row = next(line for line in reference.splitlines() if line.startswith("| `notes/` |"))
        self.assertIn("ShipLoop creates the empty directory", row)
        self.assertNotIn("ShipLoop never creates", row)

    def test_the_packet_and_the_index_do_not_depend_on_whether_the_log_exists(self) -> None:
        # GUARD, green before and after: a packet is written once at action start and re-read after a loss, so
        # nothing in the render may read the host-written log; two renders around its creation are identical.
        state = drive_to("implement")
        action = nav.current_action(state)["id"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before = nav.render(dry_run.CORE, root, state)
            index_before = context_index.render(state, root, nav.current_stage(state))
            log = context_index.pass_log_path(root, action)
            log.parent.mkdir(parents=True)
            log.write_text("Checked the first pass; the second is left.\n")
            self.assertEqual(nav.render(dry_run.CORE, root, state), before)
            self.assertEqual(context_index.render(state, root, nav.current_stage(state)), index_before)
            log.write_text("")
            self.assertEqual(nav.render(dry_run.CORE, root, state), before)


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
                improve = nav.render(dry_run.CORE, dry_run.RUN, state)
                self.assertNotIn("Done when (confirm each", improve)  # the producer's heading: this packet is the review's
                for condition in spec.stage(stage).done_when:         # and it states what the review judges against
                    self.assertIn("- " + condition, improve)
                state = nav.finish_improve(state, action, step["receipt"], step.get("final_result"))
        self.assertEqual(len(seen), 34)


    def test_the_improve_packet_for_a_blocked_result_does_not_claim_the_result_meets_the_done_when(self) -> None:
        import shiploop_stage_spec as spec
        state = nav.new_state("/simulation-only/repo", "Blocked review fixture.", delegation=nav.DEFAULT_DELEGATION)
        for step in dry_run.activity():
            stage = nav.current_stage(state)
            if stage in spec.reviewed_stages("stage"):
                break
            state = nav.apply(state, nav.current_action(state)["id"], step["result"])
        blocked = nav.apply(state, nav.current_action(state)["id"],
                            {"outcome": "blocked", "blocked_by": "external", "summary": "Synthetic block.",
                             "evidence_refs": ["synthetic://evidence"]})
        self.assertIsNotNone(blocked["active_improve"])
        packet = nav.render(dry_run.CORE, dry_run.RUN, blocked)
        self.assertIn("Reviewing the returned " + stage + " result. Goal: ", packet)
        self.assertIn("Done when (a done result must meet each", packet)
        self.assertNotIn("accepted " + stage + " result", packet)  # the parent step stays pending until improve-complete


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
