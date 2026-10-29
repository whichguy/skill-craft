#!/usr/bin/env python3
"""Hermetic tests for the homes of the Code craft rubric: implement's packet, each step's review and the end-of-work
review.

Verify's review inputs (its rubric file and the change inventory, ``shiploop_quality``) retired with verify (design T
§9.1 2b-4c): each step's review, after its document stage, applies the rubric to the step's code, tests and docs.  The
run binds the repository's source Improve card and walks the real ``complete`` gates, every inner stage's loop run
through the bundled Until Loop runtime.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/shiploop"
IMPROVE_CARD = ROOT / "skills/improve/SKILL.md"
sys.path.insert(0, str(PACKAGE / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import shiploop_inner_fixture as fx  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_standalone_improve as standalone  # noqa: E402

CORE = fx.CORE
# The step plan's conditional record topics (code or stored data, pinned values, interactions) live in this guide since the
# print-order unit (U7); the step-plan duty names their triggers and the guide.
PLAN_RECORD = " ".join((PACKAGE / "references/plan-record.md").read_text(encoding="utf-8").split())


class QualityLoopTests(fx.RunDriver):
    def assert_improve_stage_started(self, state):
        """ShipLoop binds the run's Improve card and starts the review at the transition (owner, 2026-10-11): the
        model runs neither improve-bind nor improve-start, and the packet asks it to write no opening."""
        child = state["active_improve"]
        self.assertEqual(nav.sequence_stage(state), nav.IMPROVE_STAGE)
        self.assertEqual(Path(child["skill"]["skill_card"]), IMPROVE_CARD.resolve())
        self.assertTrue(nav.improve_opening_path(child).is_file())
        self.assertTrue(nav.improve_opening_path(child).with_name("start.json").is_file())
        self.assertTrue(standalone.receipt_path(child).is_file())
        self.assertNotIn("write the opening file", nav.improve_handoff_text(CORE, self.run_dir, state))
        self.assertIn("complete --run-dir=" + str(self.run_dir) + " --action=" + nav.improve_id(state), self.packet())
    def test_end_of_work_improve_carries_the_full_rubric(self):
        self.start()
        state = self.drive_to("carry-forward", improve_stage="carry-forward")
        self.assert_improve_stage_started(state)
        packet = nav.improve_handoff_text(CORE, self.run_dir, self.state())  # the file the improve skill reads
        self.assertIn(prompts.END_REVIEW_FOCUS.strip().splitlines()[0], packet)
        self.assertIn("2. Fail at the door.", packet)
        self.assertIn("4. Spend tokens on information.", packet)

    def test_each_steps_review_carries_the_step_focus_with_the_full_rubric(self):
        """Owner decision 2026-10-10: an Improve child reviews every step with the Code craft rubric
        (IMPLEMENT_STEP_REVIEW_FOCUS carries it verbatim), even under --planning-review none.  Design T section 8: it
        starts once the step is built, tested and documented, after the step's document stage."""
        self.assertIn(prompts.CODE_CRAFT.strip(), prompts.IMPLEMENT_STEP_REVIEW_FOCUS)
        self.start()
        state = self.drive_to("document", improve_stage="document")
        self.assert_improve_stage_started(state)
        packet = nav.improve_handoff_text(CORE, self.run_dir, self.state())  # the file the improve skill reads
        self.assertIn(prompts.IMPLEMENT_STEP_REVIEW_FOCUS.strip().splitlines()[0], packet)
        self.assertEqual(packet.count("2. Fail at the door."), 1)
        self.assertNotIn(prompts.END_REVIEW_FOCUS.strip().splitlines()[0], packet)

    def test_planning_improve_does_not_carry_the_end_focus(self):
        self.start()
        state = self.drive_to("spec", improve_stage="spec")
        self.assert_improve_stage_started(state)
        handoff = nav.improve_handoff_text(CORE, self.run_dir, self.state())  # the file the improve skill reads
        self.assertIn("Planning review focus", handoff)
        self.assertNotIn("End-of-work code review focus", handoff)


# Each step's review (design T §8, after its document stage): the review list that applies the rubric to the step.
STEP_REVIEW = " ".join(prompts.IMPLEMENT_STEP_REVIEW_FOCUS_HEAD.split())


class PromptTests(unittest.TestCase):
    def test_code_craft_appears_once_in_code_stages_for_both_routes(self):
        """Owner decision 2026-10-11: the full rubric prints at implement only; each step's Improve review
        (IMPLEMENT_STEP_REVIEW_FOCUS) applies it."""
        for delegation in (prompts.ASK_AGENT, prompts.INLINE):
            for stage in ("implement", "test", "document"):
                text = prompts.prompt(stage, delegation=delegation)
                with self.subTest(delegation=delegation, stage=stage):
                    self.assertEqual(text.count("2. Fail at the door."), 1 if stage == "implement" else 0)
        self.assertNotIn("Fail at the door", prompts.prompt("spec"))

    def test_code_craft_keeps_user_facing_text_translatable(self):
        rubric = " ".join(prompts.CODE_CRAFT.split())
        self.assertIn("7. Write text that can be translated.", rubric)
        self.assertIn("never assembled from fragments", rubric)
        self.assertIn("Keep log text, error codes and machine identifiers stable and untranslated", rubric)
        self.assertIn("user-facing text built from fragments or bypassing the catalog", STEP_REVIEW)

    def test_namespace_placement_is_planned_and_reviewed(self):
        rubric = " ".join(prompts.CODE_CRAFT.split())
        self.assertIn("8. Put it where it belongs.", rubric)
        self.assertIn("narrowest visibility a present consumer needs", rubric)
        self.assertIn("a name that collides or is exported wider than needed (rule 8)", STEP_REVIEW)
        plan = " ".join(prompts.prompt("plan").split())
        self.assertIn("Code or stored data added: write the namespace and data entries in KNOWLEDGE/architecture.md "
                      "## Structure with an AD-<n> per decision", plan)
        self.assertIn("remote runtime behind an MCP server", plan)
        self.assertIn("each service", plan)
        self.assertIn("data storage per environment (Schema and storage guidance): existing and destination schema",
                      plan)
        step = " ".join(prompts.prompt("step-plan").split())
        self.assertIn("when the item adds or moves code or stored data", step)
        self.assertIn("GUIDES/plan-record.md", step)
        self.assertIn("Reopen the namespace and data entries in KNOWLEDGE/architecture.md ## Structure and each touched "
                      "environment's tree", PLAN_RECORD)
        self.assertIn("Stored data follows the planned schema", rubric)
        self.assertIn("Per stored field, key, table or payload: owning environment, migration", PLAN_RECORD)
        self.assertIn("round-trip check", PLAN_RECORD)
        self.assertIn("Reason for a changed placement or schema", PLAN_RECORD)
        routes = (
            ("Namespace and placement guidance", "coding-practices.md#namespaces-and-placement"),
            ("Schema and storage guidance", "coding-practices.md#schema-and-storage"),
        )
        for stage in ("plan", "step-plan"):
            for route in routes:
                with self.subTest(stage=stage, route=route[0]):
                    self.assertIn(route, prompts.STAGE_REFERENCES[stage])

    def test_ui_work_defaults_to_a_rich_interactive_interface(self):
        self.assertIn("or the rich UI interaction the plan calls for", " ".join(prompts.CODE_CRAFT.split()))
        self.assertIn("a plain interaction where the plan calls for a rich one", STEP_REVIEW)
        # The request's stated ambition governs; rich is the default only when it states none (packet review
        # 2026-10-17, A8-1: a "simple" request had to argue against the default).
        self.assertIn("A human-facing UI takes the ambition the request states (a simple one when it asks for simple); "
                      "one that states none defaults to an ambitious, highly interactive design",
                      " ".join(prompts.prompt("plan").split()))
        # step-plan: the interactions topic moved to the Plan record guide (U7); the duty names its trigger
        self.assertIn("changes interactions, UI or service state", " ".join(prompts.prompt("step-plan").split()))
        self.assertIn("a human-facing UI takes the ambition the request states, and with none stated defaults to "
                      "ambitious and highly interactive", PLAN_RECORD)

    def test_supporting_stages_carry_their_code_quality_duties(self):
        expected = {
            "step-plan": "A new or changed public entry point: a criterion that it checks its arguments, executed by its",
            "test-spec": "Each new or changed public entry point: one rejection case per constraint",
            "test": "Each new or changed public entry point gets a valid, a boundary and an invalid case",
            "system-test-author": "shared helpers check their arguments",
        }
        for stage, phrase in expected.items():
            with self.subTest(stage=stage):
                self.assertIn(" ".join(phrase.split()), " ".join(prompts.prompt(stage).split()))
        # Verify's entry-point walk moved to each step's review (design T §9.1 2b-4c): every finding verify made in five
        # runs came from it (design §7.2).
        self.assertIn("a path through a new or changed public entry point that is wrong, unhandled or untested",
                      STEP_REVIEW)
        self.assertIn("walk one valid, one boundary and one invalid input to its return, error or side effect",
                      STEP_REVIEW)
        self.assertIn("a public function with no contract docstring", STEP_REVIEW)


if __name__ == "__main__":
    unittest.main()
