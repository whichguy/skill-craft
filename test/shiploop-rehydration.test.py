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
import re
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
import shiploop_prompts as prompts  # noqa: E402

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
        state = drive_to("test")
        action = nav.current_action(state)["id"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            text = context_index.render(state, root, "test")
            self.assertIn("## In progress", text)
            line = next(line for line in text.splitlines() if line.startswith("- Pass log"))
            self.assertTrue(line.endswith(f": {root / 'notes' / (action + '.md')}"), line)
            self.assertIn("if it exists", line)
            # Every inner stage runs one Until Loop; its receipt is the one loop record (shiploop_loops.receipt_path).
            self.assertIn(str(root / "loops" / (action + "-terminal.json")), text)
            self.assertNotIn("-latest.json", text)  # nothing writes it; the receipt is the one loop record
            self.assertLess(text.index("## In progress"), text.index("## Request"))

    def test_script_records_list_what_the_script_wrote(self) -> None:
        state = drive_to("test")
        action = nav.current_action(state)["id"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertNotIn("## Script records", context_index.render(state, root, "test"))
            (root / "tests").mkdir()
            record = root / "tests" / (action + "-verify1.md")
            record.write_text("record\n")
            text = context_index.render(state, root, "test")
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
        # test absorbed test-green and regression; verify itself now runs static-checks' review loop.
        self.assertTrue({"item:step-plan", "item:test-spec", "item:implement", "item:test"}
                        <= set(context_index.STAGE_READS["verify"]))
        self.assertTrue({"product-acceptance", "operations"} <= set(context_index.STAGE_READS["handoff"]))


class MasterIndexTests(unittest.TestCase):
    """context-index.md is the run's master index (owner, 2026-10-16): every packet's second line points at it, so a model
    that lost its context finds every other file of the run from here.  It stays a derived view (the existing tests)."""

    MAP_LIMIT = 3_500  # "about 3 KB" of map; the paths in its lines (run, repository, package) take the rest

    @staticmethod
    def map_text(text: str) -> str:
        """The map: from the current-stage line to the first record section (In progress, else Request)."""
        end = text.index("## In progress") if "## In progress" in text else text.index("## Request")
        return text[text.index("- Current stage"):end]

    def test_the_index_opens_with_a_map_of_about_three_kilobytes(self) -> None:
        state = drive_to("implement")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "run"
            text = context_index.render(state, root, "implement")
        head = self.map_text(text)
        self.assertLess(len(head.encode("utf-8")), self.MAP_LIMIT)
        self.assertGreater(len(head.encode("utf-8")), 1_500)  # a real table, not a pointer
        self.assertLess(text.index("## What is where"), text.index("## Request"))  # the map comes first
        self.assertIn("| Path | Holds | Read it when |", text)
        # One row per file or folder, saying what it holds and when to read it.
        rows = [line for line in head.splitlines() if line.startswith("| ") and not line.startswith(("| Path", "|---"))]
        self.assertEqual(len(rows), len(context_index.MAP_ROWS))
        for row in rows:
            self.assertEqual(row.count(" | "), 2, row)

    def test_the_map_gives_the_current_stage_and_the_next_and_recovery_commands(self) -> None:
        state = drive_to("implement")
        action = nav.current_action(state)["id"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "run"
            head = self.map_text(context_index.render(state, root, "implement"))
            lines = head.splitlines()
            self.assertEqual(lines[0], f"- Current stage: implement (active, revision {state['revision']}); "
                                       f"its packet in full: {root / 'packets' / (action + '.md')}")
            self.assertTrue(lines[1].startswith("- Next command: the callback at the top of that packet"), lines[1])
            self.assertIn(nav._callback(dry_run.CORE, root, "next"), lines[2])  # the packet's own recovery command
            self.assertIn("moves nothing", lines[2])
            self.assertIn(f"RUN = {root} · HOME = {Path(state['repo']) / 'docs/shiploop'} · GUIDES = "
                          f"{context_index.GUIDES}", head)
            self.assertTrue((context_index.GUIDES / "state-files.md").is_file())  # GUIDES is the real references directory

    def test_a_packet_for_an_improve_stage_is_the_one_the_map_names(self) -> None:
        state = nav.new_state("/simulation-only/repo", "Improve packet fixture.", delegation="inline")
        while state.get("active_improve") is None:
            state = nav.apply(state, nav.current_action(state)["id"], {"outcome": "done", "summary": "Synthetic."})
        root = Path("/simulation-only/run")
        head = self.map_text(context_index.render(state, root, nav.current_stage(state)))
        self.assertIn(f"its packet in full: {nav.packet_path(root, state)}", head)

    def test_the_map_lists_every_top_level_entry_a_run_directory_gets(self) -> None:
        """A real run (init, a refused and an accepted callback) plus the entries the catalog and the code add later."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            repo, run = base / "repo", base / "run"
            repo.mkdir()
            env = {**ENV, "SHIPLOOP_PROGRESS": "off"}
            started = subprocess.run([sys.executable, "-B", str(CLI), "init", "--repo", str(repo), "--prompt", "Add a thing.",
                                      "--run-dir", str(run)], env=env, text=True, capture_output=True, timeout=60)
            self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
            action = nav.current_action(store_read(run))["id"]
            bad = base / "elsewhere.md"
            bad.write_text("no result here\n")
            subprocess.run([sys.executable, "-B", str(CLI), "complete", "--run-dir", str(run), "--action", action,
                            "--result", str(bad)], env=env, text=True, capture_output=True, timeout=60)  # refused: callback-attempts
            result = run / "inbox" / (action + ".md")
            result.write_text('```shiploop-state\n{"outcome": "done", "summary": "Intake done.", "evidence_refs": []}\n```\n')
            accepted = subprocess.run([sys.executable, "-B", str(CLI), "complete", "--run-dir", str(run), "--action", action,
                                       "--result", str(result)], env=env, text=True, capture_output=True, timeout=60)
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
            entries = {entry.name + ("/" if entry.is_dir() else "") for entry in run.iterdir()}
            index = (run / "context-index.md").read_text(encoding="utf-8")
            self.assertTrue({"state.md", "results/", "inbox/", "notes/", "packets/", "scratch/", "callback-attempts"} <= entries, entries)
        # Names the catalog lists (references/state-files.md: first path component of each backticked file or directory,
        # minus the workspace files, which live beside the run) and the ones the code writes without listing them there.
        catalog = (ROOT / "skills/shiploop/references/state-files.md").read_text(encoding="utf-8")
        table = catalog[catalog.index("| File or directory |"):catalog.index("The live Improve child keeps")]
        named = set()
        for cell in re.findall(r"(?m)^\| ([^|]+) \|", table)[1:]:
            for name in re.findall(r"`([^`]+)`", cell):
                if name not in ("workspace.md", "return-plan.md", "return-receipt.md"):
                    first = name.split("/")[0]
                    named.add(first + "/" if "/" in name else first)
        named |= {"packets/", "scratch/", "reference.md", "context-index.md", "timeline.json", "backchain/", "chains/",
                  "transaction.md", ".lock", "callback-attempts", "run-baseline.txt"}
        self.assertTrue({"state.md", "decisions/", "loops/", "tests/", "lint/", "expectations/", "quality/", "improve/",
                         "report.html", "progress.html"} <= named, named)
        for entry in sorted(entries | named):
            with self.subTest(entry=entry):
                self.assertIn(entry.rstrip("/"), index, f"the master index does not list {entry}")
                if entry.endswith("/"):
                    self.assertIn("RUN/" + entry, index)

    def test_the_map_names_the_three_knowledge_files_and_the_guides(self) -> None:
        import shiploop_knowledge_home as knowledge
        state = drive_to("implement")
        text = context_index.render(state, Path("/simulation-only/run"), "implement")
        for name in knowledge.LIVING:
            self.assertIn("| HOME/" + name + " |", text)
        self.assertIn("| GUIDES/ |", text)
        self.assertIn("| RUN/reference.md |", text)
        for anchor in ("rules", "blocked", "outcomes", "recovery", "policies"):  # the sections reference.md really has
            self.assertIn("#" + anchor, text)
            self.assertIn(anchor, __import__("shiploop_reference").ANCHORS)


def store_read(run: Path) -> dict:
    import shiploop_store
    return shiploop_store.read_record(run / "state.md")


class PacketTests(unittest.TestCase):
    def test_active_and_paused_packets_name_the_pass_log(self) -> None:
        state = drive_to("implement")
        action = nav.current_action(state)["id"]
        expected = "This action's pass log"  # its own line; the index pointer is the packet's second line (2026-10-16)
        packet = nav.render(dry_run.CORE, dry_run.RUN, state)
        self.assertIn(expected, packet)
        # A prose path prints as the References block's symbol (2026-10-16); RUN is defined in the same packet.
        self.assertIn("RUN/notes/" + action + ".md", packet)
        self.assertIn(" · RUN = " + str(dry_run.RUN) + " (run records)", packet)
        paused = nav.control(state, "pause", "The user asked to stop for now.")
        self.assertIn("RUN/notes/" + action + ".md", nav.render(dry_run.CORE, dry_run.RUN, paused))

    def test_the_pass_log_line_tells_the_pass_to_create_it_and_a_reset_to_open_it_only_if_it_exists(self) -> None:
        # Wording-level check, not a refusal route: the packet file is written once, when the action starts,
        # and a context lost mid-stage re-reads that file, so the line must be true whether or not the host
        # has created the log by then.
        state = drive_to("implement")
        line = next(line for line in nav.render(dry_run.CORE, dry_run.RUN, state).splitlines()
                    if line.startswith("This action's pass log"))
        # PASS_LOG_RULE was shortened (2026-10-11 dedupe): "ShipLoop does not create it" and "nothing was logged"
        # went; the host creates it ("create it and append ...") and opens it first only if it exists.
        for part in ("optional", "never a completion gate", "create it and append",
                     "what each pass checked and what is left",
                     "open it first if it exists"):
            self.assertIn(part, line)
        self.assertNotIn("ShipLoop creates it", line)
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
                    # The owner rule and the index pointer sit directly under the header (2026-10-16); the callback,
                    # goal and done-when follow them.
                    self.assertEqual(lines[header + 1], prompts.OWNER_RULE)
                    self.assertTrue(lines[header + 2].startswith(prompts.INDEX_POINTER_PREFIX))
                    owner = 2
                    self.assertTrue(lines[header + owner + 1].startswith("Callback for this stage"))
                    # A goal is one action sentence naming its output (packet re-cut, 2026-10-11) and may end in its own period.
                    self.assertEqual(lines[header + owner + 2], "Goal: " + row.goal[0].upper() + row.goal[1:]
                                     + ("" if row.goal.endswith(".") else "."))
                    if stage in spec.INNER:
                        # Each thing once (owner, 2026-10-11): the head points at the /until-loop argument, which
                        # numbers the conditions; they are not listed a second time.
                        self.assertEqual(lines[header + owner + 3], nav.DONE_WHEN_LOOP)
                        for number, condition in enumerate(row.done_when, 1):
                            self.assertEqual(packet.count(condition), 1, condition)
                            self.assertIn("    " + str(number) + ". " + condition, packet)
                    else:
                        for condition in row.done_when:
                            self.assertIn("- " + condition, packet)
            action = nav.current_action(state)["id"]
            if step["command"] == "produce":
                state = nav.apply(state, action, step["result"])
            else:
                improve = nav.render(dry_run.CORE, dry_run.RUN, state)
                self.assertNotIn("Done when (confirm each", improve)  # the producer's heading: this packet is the review's
                # The review's goal and done-when moved into the Improve handoff file (round 2); the packet holds two
                # instructions only.
                handoff = nav.improve_handoff_text(dry_run.CORE, dry_run.RUN, state)
                for condition in spec.stage(stage).done_when:
                    self.assertIn("- " + condition, handoff)
                    self.assertNotIn("- " + condition, improve)
                state = nav.finish_improve(state, action, step["receipt"], step.get("final_result"))
        self.assertEqual(seen, set(spec.STAGES))  # every one of the 24 stages issued a producer packet


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
        packet = nav.improve_handoff_text(dry_run.CORE, dry_run.RUN, blocked)  # the review's goal lives in the handoff
        self.assertIn("Reviewing the returned " + stage + " result. Goal: ", packet)
        self.assertIn("Done when (a done result must meet each", packet)
        self.assertNotIn("accepted " + stage + " result", packet)  # the parent step stays pending until the Improve stage's complete


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
