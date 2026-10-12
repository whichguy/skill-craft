#!/usr/bin/env python3
"""The packet re-cut's own rules (owner, 2026-10-11; docs/shiploop-packet-recut-2026-10-11.md), checked by behaviour.

The wording pins in other suites show where each sentence went; these tests check the rules themselves:
- an Improve packet is two instructions, the improve skill with a literal example and then the done command, and
  ShipLoop binds its recorded card and writes the handoff the skill reads;
- no producer packet mentions an upcoming Improve;
- every stage's goal is an action that names where its output goes;
- every "duty items n-m" a loop Work line cites exists in that stage's duty;
- no packet states a long sentence twice;
- producer and Improve packets stay under the ceilings measured when the re-cut landed.
"""
from __future__ import annotations

import json
import re
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
import shiploop_prompts as prompts  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402

CASES = {name: case for name, case in json.loads((ROOT / "test/shiploop_e2e/step_cases.json").read_text()).items()
         if not name.startswith("_")}
MODES = [(delegation, review, passes) for delegation in prompts.DELEGATIONS for review in ("stage", "none")
         for passes in prompts.BACKCHAIN_PASSES_MODES]
# Ceilings in characters for the offline node-fix-bug inner loop, set from its sizes when the re-cut landed plus about
# 10% headroom: a packet that grows past one is the repetition the re-cut removed coming back. Raise one only with
# a recorded reason (a new obligation), never to make room for a restatement.
PRODUCER_CEILING = 33_000
IMPROVE_CEILING = 3_000


def _offline(case: str = "node-fix-bug") -> dict[str, str]:
    return packets.offline_packets(CASES[case])


class ImprovePacketTests(unittest.TestCase):
    """An Improve run is "just calling the improve skill and then, once complete, invoking the done activity"."""

    def _bound_state(self, temp: str) -> tuple[Path, dict]:
        card = prompts.installed_improve_card()
        if not card.is_file():
            self.skipTest("no installed Improve card beside this ShipLoop package: " + str(card))
        run = Path(temp) / "run"
        run.mkdir()
        state = navigator.new_state(temp, "Add a greeting.", delegation="inline", improve_skill=str(card))
        while navigator.current_stage(state) != "spec":
            action = navigator.current_action(state)["id"]
            state = navigator.apply(state, action, {"outcome": "done", "summary": "Synthetic"})
        state = navigator.apply(state, navigator.current_action(state)["id"],
                                {"outcome": "done", "summary": "Synthetic spec"})
        self.assertIsNotNone(state.get("active_improve"), "spec should start a planning Improve child")
        self.assertIsNone(state["active_improve"]["skill"])
        bound, writes = navigator._improve_entry(run, state)
        return run, bound

    def test_shiploop_binds_the_recorded_card_at_the_transition(self) -> None:
        with tempfile.TemporaryDirectory(prefix="recut-improve-") as temp:
            _run, state = self._bound_state(temp)
            self.assertIsNotNone(state["active_improve"]["skill"])
            self.assertEqual(state["improve_skill"], state["active_improve"]["skill"]["skill_card"])

    def test_an_unresolvable_card_leaves_the_child_unbound_and_the_packet_prints_the_bind_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="recut-improve-") as temp:
            run = Path(temp) / "run"
            run.mkdir()
            state = navigator.new_state(temp, "Add a greeting.", delegation="inline",
                                        improve_skill=str(Path(temp) / "missing" / "SKILL.md"))
            while state.get("active_improve") is None:
                state = navigator.apply(state, navigator.current_action(state)["id"],
                                        {"outcome": "done", "summary": "Synthetic"})
            unbound, writes = navigator._improve_entry(run, state)
            self.assertIsNone(unbound["active_improve"]["skill"])
            self.assertEqual(writes, {})
            packet = navigator.render(None, run, unbound)
            self.assertIn("improve-bind", packet)
            self.assertNotIn("/improve ShipLoop Improve:", packet)

    def test_the_packet_is_two_instructions_with_a_literal_example(self) -> None:
        with tempfile.TemporaryDirectory(prefix="recut-improve-") as temp:
            run, state = self._bound_state(temp)
            packet = navigator.render(None, run, state)
            child = state["active_improve"]
            handoff = navigator.improve_handoff_path(child)
            self.assertIn("1. Run the improve skill on the spec result.", packet)
            self.assertIn("       /improve " + navigator.IMPROVE_ARGUMENT_PREFIX + str(handoff), packet)
            self.assertRegex(packet, r"(?m)^2\. When the improve skill has completed, run: .*improve-complete")
            # Nothing else instructs: no goal, references, rules, result shapes or stage guidance.
            for absent in ("Goal:", "References (", "Rules", "Result template", "Current stage guidance",
                           "Checked by", "Done when", "opening file"):
                self.assertNotIn(absent, packet, absent)
            # The hooks' machine lines stay.
            self.assertIn("Keepalive marker: ", packet)
            self.assertIn("=== ShipLoop status ===", packet)
            self.assertLess(len(packet), IMPROVE_CEILING)

    def test_emit_writes_the_handoff_the_skill_reads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="recut-improve-") as temp:
            run, state = self._bound_state(temp)
            navigator.save(run, state)
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                navigator.emit(None, run, state)
            child = state["active_improve"]
            text = navigator.improve_handoff_path(child).read_text(encoding="utf-8")
            self.assertIn(child["contract_marker"], text)        # how the improve skill knows it is a ShipLoop subcall
            self.assertIn("improve-start", text)
            self.assertIn("improve-complete", text)
            self.assertIn("improve-commit", text)


class NoAdvanceImproveTests(unittest.TestCase):
    def test_no_producer_prompt_mentions_improve(self) -> None:
        for stage in prompts.STAGES:
            for delegation, review, passes in MODES:
                with self.subTest(stage=stage, delegation=delegation, review=review, passes=passes):
                    text = prompts.prompt(stage, delegation=delegation, planning_review=review,
                                          backchain_passes=passes)
                    self.assertNotRegex(text, r"\bImprove\b")

    def test_no_producer_packet_announces_an_improve_child(self) -> None:
        for key, text in _offline().items():
            if key.endswith("-improve"):
                continue
            with self.subTest(packet=key):
                self.assertNotIn("starts this action's Improve child", text)
                self.assertNotIn("Improve child's context", text)
                self.assertNotRegex(text, r"(?m)^Improve: ")


class ActionGoalTests(unittest.TestCase):
    # A goal names where its outcome goes: a result field in backticks, a knowledge or run file, or the product.
    OUTPUT = re.compile(r"`[a-z_]+`|HOME/|RUN/|WORKTREE|\b(spec|environment|architecture)\.md\b|evidence_refs|"
                        r"\bsummary\b|\bresult\b|checkout|repository|commit")

    def test_every_goal_is_one_action_that_names_its_output(self) -> None:
        for stage in prompts.STAGES:
            goal = stage_spec.stage(stage).goal
            with self.subTest(stage=stage):
                self.assertRegex(goal, r"^[A-Za-z]")
                self.assertRegex(goal, self.OUTPUT, goal)


class WorkLineTests(unittest.TestCase):
    def test_every_cited_duty_item_exists(self) -> None:
        for stage in stage_spec.INNER:
            duty = prompts.duty(stage, delegation=prompts.INLINE)
            items = {int(n) for n in re.findall(r"(?m)^(\d+)\. ", duty)}
            work = str(loops.WORK.get(stage, "")) if hasattr(loops, "WORK") else ""
            for first, last in re.findall(r"duty items (\d+)(?:-|–| to )(\d+)", work):
                with self.subTest(stage=stage, cited=first + "-" + last):
                    for number in range(int(first), int(last) + 1):
                        self.assertIn(number, items)


class OneHomeTests(unittest.TestCase):
    def test_no_packet_states_a_long_sentence_twice(self) -> None:
        for name in CASES:
            for key, text in _offline(name).items():
                prose = " ".join(line for line in text.splitlines() if not line.startswith("  | "))
                sentences = [s.strip() for s in re.split(r"(?<=[.;:])\s+", " ".join(prose.split()))
                             if len(s.strip()) > 80]
                repeated = sorted({s for s in sentences if sentences.count(s) > 1})
                with self.subTest(case=name, packet=key):
                    self.assertEqual(repeated, [])

    def test_packets_stay_under_the_ceilings(self) -> None:
        for key, text in _offline().items():
            with self.subTest(packet=key):
                ceiling = IMPROVE_CEILING if key.endswith("-improve") else PRODUCER_CEILING
                self.assertLess(len(text), ceiling)


if __name__ == "__main__":
    unittest.main()
