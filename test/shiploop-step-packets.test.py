#!/usr/bin/env python3
"""Step-slice packets, no model: each step case's inner-loop packets, as a cleared model reads them.

For every case in test/shiploop_e2e/step_cases.json, the checkout's navigator walks the run with synthetic results
(packets.offline_packets: the plan's only item is the case's work item, and the step plan records the case's first check
as its test command). Every inner-loop stage, and every Improve packet the item's loop starts, must render:
- naming the case's work item;
- with each skill reference it names present on disk;
- with the printed head inside the host's shell-output limit.
Each packet that runs the item's tests (test, verify) must also name the recorded test command.

Run `python3 test/shiploop_e2e/packets.py --offline <case>` to see sizes, sections and the cross-packet overlap.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
sys.path.insert(0, str(ROOT / "test/shiploop_e2e"))
import packets  # noqa: E402
import shiploop_loops as loops  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_store as store  # noqa: E402

CASES = {name: case for name, case in json.loads((ROOT / "test/shiploop_e2e/step_cases.json").read_text()).items()
         if not name.startswith("_")}
# The stages whose packets carry the item's recorded test commands to run them: the test stage (its /until-loop
# argument) and verify (its Test rerun list).  Declared here; a test below pins them to the stage table's runs.
RUNS_THE_TESTS = ("test", "verify")


class StepPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.found = {name: packets.offline_packets(case) for name, case in CASES.items()}

    def test_every_inner_stage_renders_once_for_the_one_item(self) -> None:
        for name, found in self.found.items():
            producers = [key.split("-", 1)[1] for key in found if not key.endswith("-improve")]
            with self.subTest(name):
                self.assertEqual(producers, list(stage_spec.INNER))
                self.assertIn("carry-forward-improve", " ".join(found))  # the last item's end review

    def test_each_packet_names_the_case_work_item(self) -> None:
        for name, found in self.found.items():
            title = CASES[name]["work_item"]["title"]
            for key, text in found.items():
                with self.subTest(case=name, packet=key):
                    self.assertIn(title, text)

    def test_named_skill_references_exist(self) -> None:
        for name, found in self.found.items():
            for key, text in found.items():
                with self.subTest(case=name, packet=key):
                    self.assertEqual(packets.references(text)["missing"], [])

    def test_stages_that_run_the_tests_name_the_recorded_command(self) -> None:
        for name, found in self.found.items():
            command = CASES[name]["checks"][0]
            checked = set()
            for key, text in found.items():
                if key.split("-", 1)[1] in RUNS_THE_TESTS:
                    checked.add(key.split("-", 1)[1])
                    with self.subTest(case=name, packet=key):
                        self.assertIn(command, text)
            self.assertEqual(checked, set(RUNS_THE_TESTS), name)  # a renamed stage cannot leave this checking nothing

    def test_the_stages_that_run_the_tests_are_the_inner_stages_that_run_them_at_done(self) -> None:
        runs = set(stage_spec.with_complete_run("test-loop")) | set(stage_spec.with_complete_run("test-rerun"))
        self.assertEqual(set(RUNS_THE_TESTS), runs & set(stage_spec.INNER))

    def test_each_exit_condition_and_recorded_command_appears_once(self) -> None:
        """Each thing once (owner, 2026-10-11): the /until-loop argument is the one home of the exit conditions and the
        test stage's command list, so no inner producer packet repeats either.

        A condition is counted as its text; a recorded command as its listing ("[<suite>] <command>"), because the
        bare command text can sit inside a rule (the count rule names "node --test" as a runner example).
        """
        for name, found in self.found.items():
            listing = "[focused] " + CASES[name]["checks"][0]
            for key, text in found.items():
                if key.endswith("-improve"):
                    continue
                stage = key.split("-", 1)[1]
                # The synthetic step plan has no steps, so implement's argument cannot be built: its invoke block says
                # why and the head keeps the itemised list, still once.
                argument = "\n" + loops.ARGUMENT_BEGIN + "\n" in text
                with self.subTest(case=name, packet=key):
                    self.assertEqual(navigator.DONE_WHEN_LOOP in text, argument)
                    for number, condition in enumerate(stage_spec.stage(stage).done_when, 1):
                        self.assertEqual(text.count(condition), 1, condition)
                        self.assertIn(("\n" + str(number) + ". " if argument else "- ") + condition + "\n", text)
                    # test and verify list it in their loop; test-spec gets it once, as the step plan's hand-off
                    # (navigator.CONSUMES, consumer contract section 4).
                    self.assertEqual(text.count(listing), 1 if stage in ("test", "verify", "test-spec") else 0)

    def test_the_printed_head_fits_the_host_output_limit(self) -> None:
        case = CASES["node-fix-bug"]
        with tempfile.TemporaryDirectory(prefix="shiploop-step-head-") as temp:
            run_dir = Path(temp) / "run"
            run_dir.mkdir()
            state = navigator.new_state(temp, case["prompt"], delegation="inline")
            while navigator.current_stage(state) != "step-plan":
                action = navigator.current_action(state)["id"]
                extra = {"work_items": [case["work_item"]]} if navigator.current_stage(state) == "plan" else {}
                state = navigator.apply(state, action, {"outcome": "done", "summary": "Synthetic", **extra})
                if state.get("active_improve") is not None:
                    state = navigator.finish_improve(state, action, {"summary": "Synthetic review", "lessons": "x"})
            store.write_record(run_dir / "state.md", state)
            shown = io.StringIO()
            with contextlib.redirect_stdout(shown):
                full = navigator.emit(None, run_dir, store.read_record(run_dir / "state.md"))
        printed = shown.getvalue()
        # The head leads with the stage's duties (2026-10-16), and step-plan's alone are 9,000 characters, so its head
        # (19,400) passes PRINT_LIMIT, which bounds a packet printed whole.  It stays under the ~20,000-character cut
        # some hosts apply to shell output.
        self.assertLessEqual(len(printed), 20_000)
        self.assertIn("Current stage guidance:", printed)
        self.assertGreater(len(full), len(printed))  # the packet file holds the rest

    def test_offline_report_counts_every_packet(self) -> None:
        report = packets.offline_report("node-add-function", CASES["node-add-function"])
        self.assertEqual(report["totals"]["packets"], len(self.found["node-add-function"]))
        self.assertEqual(report["packets"][0]["repeated_share"], 0.0)  # nothing was sent before the first packet
        self.assertTrue(all(row["chars"] > 0 and row["sections"] for row in report["packets"]))


if __name__ == "__main__":
    unittest.main()
