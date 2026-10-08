#!/usr/bin/env python3
"""Main tenet (README top, SPEC S-6): every packet stands alone, because the context may be cleared between any two stages.

A model holding only the next packet must find, in that packet: what the stage is for, how it operates, how its result is
checked or reviewed, what it must produce, and how to recover.  This renders the real packet of every stage, and the
Improve-phase packet of every stage whose result starts an Improve child, from a cold read of ``state.md`` (what a cleared
model sees), and checks each for the five.  Synthetic results; no model, no Improve execution.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_navigator as navigator  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_store as store  # noqa: E402


def packets(planning_review: str = "stage") -> dict:
    """{(stage, 'producer' | 'improve'): the packet text a cleared model would read}."""
    with tempfile.TemporaryDirectory(prefix="shiploop-packet-completeness-") as temp:
        repo = Path(temp)
        run = repo / "run"
        run.mkdir()
        state = navigator.new_state(str(repo), "Build a thing.", delegation="inline", planning_review=planning_review)
        found = {}

        def cold(current):
            store.write_record(run / "state.md", current)
            return navigator.render(None, run, store.read_record(run / "state.md"))

        for _ in range(120):
            if state["status"] != "active":
                break
            stage = navigator.current_stage(state)
            action = navigator.current_action(state)
            found.setdefault((stage, "producer"), cold(state))
            extra = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "one", "context": "context"}]
            if stage == "step-plan":
                extra["test_commands"] = [{"command": "python3 -m unittest", "suite": "focused"}]
            waiting = navigator.apply(state, action["id"], {"outcome": "done", "summary": "Synthetic", **extra})
            if waiting.get("active_improve") is not None:
                found.setdefault((stage, "improve"), cold(waiting))
                waiting = navigator.finish_improve(waiting, action["id"], {"summary": "Synthetic review", "lessons": "x"})
            state = waiting
        return found


class PacketCompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.found = packets()

    def test_every_stage_has_a_packet_and_every_reviewed_stage_has_an_improve_packet(self) -> None:
        stages = {stage for stage, kind in self.found if kind == "producer"}
        self.assertEqual(stages, set(stage_spec.STAGE_SPEC))
        reviewed = {stage for stage, kind in self.found if kind == "improve"}
        self.assertEqual(reviewed, set(stage_spec.reviewed_stages("stage")) | {"carry-forward"})

    def test_a_producer_packet_states_purpose_operation_check_output_and_recovery(self) -> None:
        for (stage, kind), packet in sorted(self.found.items()):
            if kind != "producer":
                continue
            flat = " ".join(packet.split())
            duty = " ".join(prompts.DUTIES[stage].split())[:60]
            with self.subTest(stage):
                self.assertIn("Goal: ", packet)                       # what the stage is for
                self.assertIn("Done when", packet)
                self.assertIn(duty, flat)                             # how the stage operates
                self.assertIn("Checked by: ", packet)                 # how the result is checked
                self.assertIn("Result template", packet)             # what it must produce
                self.assertIn("Write the structured result to: ", packet)
                self.assertIn("Recovery", packet)                    # how to recover

    def test_an_improve_packet_states_purpose_operation_check_output_and_recovery(self) -> None:
        for (stage, kind), packet in sorted(self.found.items()):
            if kind != "improve":
                continue
            with self.subTest(stage):
                self.assertIn("Current action: Improve the completed " + stage + " result.", packet)  # purpose
                self.assertIn("Load the actual Improve skill", packet)  # how it operates: the selected skill runs the review
                line = next((line for line in packet.splitlines() if line.startswith("Checked by: ")), "")
                self.assertIn("improve-complete", line)               # what it produces and how that is checked
                self.assertIn("Recovery", packet)

    def test_a_producer_names_the_script_checks_its_stage_row_declares(self) -> None:
        for (stage, kind), packet in sorted(self.found.items()):
            if kind != "producer":
                continue
            row = stage_spec.stage(stage)
            line = next(line for line in packet.splitlines() if line.startswith("Checked by: "))
            with self.subTest(stage):
                if row.complete_runs:
                    self.assertNotIn("nothing automatic", line)
                else:
                    self.assertIn("you confirm each Done-when condition", line)

    # Declared here, not read from the navigator: the words a stage's Checked-by line must carry because its gate
    # exists, and the only stages that may carry them.  test/shiploop-callback-contract.test.py pairs each named fault
    # with the real refusal and an accepted correction (the step plan's skill_na fault there, the document stage's in
    # test/shiploop-test-loop.test.py, which drives that stage's gate against a real diff).
    GATE_WORDS = {
        "assumption": {"plan"},
        "criterion": {"step-plan"},
        "deps": {"step-plan"},
        "skill_na": {"step-plan", "document"},
        "system_commands": {"system-test-author"},
        "consumer_checks": {"release-plan"},
        "consumer_entry": {"release-plan"},
        "docs/shiploop": {"prepare", "test-spec", "release-plan"},
    }

    def test_a_producer_without_a_script_run_check_names_the_faults_complete_refuses(self) -> None:
        for (stage, kind), packet in sorted(self.found.items()):
            row = stage_spec.stage(stage)
            if kind != "producer" or row.complete_runs:
                continue
            lines = [line for line in packet.splitlines() if line.startswith("Checked by: ")]
            with self.subTest(stage):
                self.assertEqual(len(lines), 1)  # one line: shiploop-keepalive requires the head's lines to be one each
                line = lines[0]
                self.assertNotIn("nothing automatic", line)
                self.assertIn("ShipLoop refuses a result with a mechanical fault", line)
                self.assertIn("refusal does not advance the run", line)
                self.assertIn("run the same complete command again", line)
                self.assertIn("does not judge the work", line)
                # Claims no wider than the gates: relative evidence paths are not checked, and the credential screen is
                # conservative, not a guarantee.
                self.assertIn("absolute", line)
                self.assertIn("explicit credential pattern", line)
                for word, stages in self.GATE_WORDS.items():
                    self.assertEqual(word in line, stage in stages, f"{word!r} in the {stage} line")


if __name__ == "__main__":
    unittest.main()
