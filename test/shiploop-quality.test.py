#!/usr/bin/env python3
"""Hermetic tests for verify's review inputs: the Code craft rubric file and the change inventory.

The static-checks quality loop became verify's stage loop on 2026-10-10 (17 -> 8 inner stages).  Its contract,
invoke block and terminal check belong to ``shiploop_loops`` with every inner stage's and are tested in
shiploop-loops.test.py.  This suite keeps what only verify's review reads (``shiploop_quality``) and the prompts that
carry the Code craft rubric.  The run binds the repository's source Improve card and walks the real ``complete``
gates, every inner stage's loop run through the bundled Until Loop runtime.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/shiploop"
IMPROVE_CARD = ROOT / "skills/improve/SKILL.md"
sys.path.insert(0, str(PACKAGE / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import shiploop_inner_fixture as fx  # noqa: E402
import shiploop_lint as lint  # noqa: E402
import shiploop_loops as loops  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_quality as quality  # noqa: E402

CORE = fx.CORE


class QualityLoopTests(fx.RunDriver):
    def test_verify_is_the_review_stage_and_its_entry_writes_the_rubric_and_the_inventory(self):
        self.assertEqual(quality.STAGE, "verify")
        self.start()
        self.drive_to(quality.STAGE)
        packet = self.packet()
        action = self.action()
        self.assertEqual((self.run_dir / quality.RUBRIC_PATH).read_text(), prompts.CODE_CRAFT)
        self.assertEqual(quality.rubric_writes(), {quality.RUBRIC_PATH: prompts.CODE_CRAFT})
        contract = json.loads((self.run_dir / loops.contract_path(action)).read_text())
        self.assertEqual(contract["required_trivial_reviews"], 1)
        purposes = {row["purpose"]: row["locator"] for row in contract["context"]["resources"]}
        self.assertEqual(Path(purposes["Code craft rubric the review applies"]).read_text(), prompts.CODE_CRAFT)
        self.assertEqual(purposes["change inventory: the files in scope"],
                         str(self.run_dir / lint.inventory_path(action)))
        self.assertIn("accepted step plan: steps, criteria, paths, commands and expectations", purposes)
        # Inventory: tracked edit and new untracked file; ignored file and run directory excluded.
        self.assertIn("Change inventory for W1", packet)
        rows = [line for line in packet.split("Change inventory for W1", 1)[1].splitlines()
                if line.startswith("  ")]
        self.assertEqual(rows[:2], ["  M a.py", "  A new_mod.py"])
        self.assertNotIn("ignored.txt", "\n".join(rows))
        self.assertNotIn("runs/", "\n".join(rows))
        self.assertEqual(quality.inventory_lines(self.run_dir, self.state(), "W1", action),
                         lint.render_inventory_lines(self.run_dir, action, "W1"))

    def test_the_inventory_and_the_loop_block_render_without_git(self):
        """The inventory is recorded at verify entry and only read at render; so is the loop contract.

        Since verify took over integrate's commit, its packet also prints the commit-scope lines, which read the item's
        diff (``item_scope.changed_paths``) at render; this test covers the parts verify's review renders."""
        self.start()
        self.drive_to(quality.STAGE)
        state, action = self.state(), self.action()
        with mock.patch.object(lint, "_git", side_effect=AssertionError("render ran Git")):
            self.assertIn("  A new_mod.py", "\n".join(quality.inventory_lines(self.run_dir, state, "W1", action)))
            self.assertIn(loops.INVOKE_LINE, loops.invoke_lines(self.run_dir, state))

    def test_non_git_checkout_records_unavailable_inventory_and_completes(self):
        plain = self.base / "plain"
        plain.mkdir()
        text = lint.inventory_writes(self.run_dir, plain, "W1", "A1")[lint.inventory_path("A1")]
        self.assertIn("unavailable", text)
        self.assertIn("not a Git checkout", text)
        (self.run_dir / "lint").mkdir(exist_ok=True)
        (self.run_dir / lint.inventory_path("A1")).write_text(text)
        self.assertIn("No change inventory recorded for W1 (not a Git checkout)",
                      "\n".join(lint.render_inventory_lines(self.run_dir, "A1", "W1")))

    def test_end_of_work_improve_carries_the_full_rubric(self):
        self.start()
        state = self.drive_to("carry-forward", improve_stage="carry-forward")
        with contextlib.redirect_stdout(io.StringIO()):
            nav.dispatch(CORE, self.run_dir, state, types.SimpleNamespace(
                command="improve-bind", action=state["active_improve"]["action_id"],
                skill_card=str(IMPROVE_CARD)))
        packet = self.packet()
        self.assertIn(prompts.END_REVIEW_FOCUS.strip().splitlines()[0], packet)
        self.assertIn("2. Fail at the door.", packet)
        self.assertIn("4. Spend tokens on information.", packet)

    def test_each_implement_step_improve_carries_the_step_focus_with_the_full_rubric(self):
        """Owner decision 2026-10-10: an Improve child reviews every accepted implement step with the Code craft
        rubric (IMPLEMENT_STEP_REVIEW_FOCUS carries it verbatim), even under --planning-review none."""
        self.assertIn(prompts.CODE_CRAFT.strip(), prompts.IMPLEMENT_STEP_REVIEW_FOCUS)
        self.start()
        state = self.drive_to("implement", improve_stage="implement")
        with contextlib.redirect_stdout(io.StringIO()):
            nav.dispatch(CORE, self.run_dir, state, types.SimpleNamespace(
                command="improve-bind", action=state["active_improve"]["action_id"],
                skill_card=str(IMPROVE_CARD)))
        packet = self.packet()
        self.assertIn(prompts.IMPLEMENT_STEP_REVIEW_FOCUS.strip().splitlines()[0], packet)
        self.assertEqual(packet.count("2. Fail at the door."), 1)
        self.assertNotIn(prompts.END_REVIEW_FOCUS.strip().splitlines()[0], packet)

    def test_planning_improve_does_not_carry_the_end_focus(self):
        self.start()
        state = self.drive_to("spec", improve_stage="spec")
        with contextlib.redirect_stdout(io.StringIO()):
            nav.dispatch(CORE, self.run_dir, state, types.SimpleNamespace(
                command="improve-bind", action=state["active_improve"]["action_id"],
                skill_card=str(IMPROVE_CARD)))
        self.assertIn("Planning review focus", self.packet())
        self.assertNotIn("End-of-work code review focus", self.packet())


VERIFY_REVIEW = " ".join(loops.WORK["verify"].split())  # verify's loop work: the review static-checks ran


class PromptTests(unittest.TestCase):
    def test_code_craft_appears_once_in_code_stages_for_both_routes(self):
        for delegation in (prompts.ASK_AGENT, prompts.INLINE):
            for stage in ("implement", "test", "document", "verify"):
                text = prompts.prompt(stage, delegation=delegation)
                with self.subTest(delegation=delegation, stage=stage):
                    self.assertEqual(text.count("2. Fail at the door."), 1)
        self.assertNotIn("Fail at the door", prompts.prompt("spec"))

    def test_code_craft_keeps_user_facing_text_translatable(self):
        rubric = " ".join(prompts.CODE_CRAFT.split())
        self.assertIn("7. Write text that can be translated.", rubric)
        self.assertIn("never assembled from fragments", rubric)
        self.assertIn("Keep log text, error codes and machine identifiers stable and untranslated", rubric)
        self.assertIn("user text that is concatenated or bypasses the catalog", VERIFY_REVIEW)

    def test_namespace_placement_is_planned_and_reviewed(self):
        rubric = " ".join(prompts.CODE_CRAFT.split())
        self.assertIn("8. Put it where it belongs.", rubric)
        self.assertIn("narrowest visibility a present consumer needs", rubric)
        self.assertIn("names outside the planned namespace or exported wider than needed", VERIFY_REVIEW)
        plan = " ".join(prompts.prompt("plan").split())
        self.assertIn("When the work adds code or stored data, forecast where it lives.", plan)
        self.assertIn("a remote runtime behind an MCP server", plan)
        self.assertIn("each service of a multi-service system", plan)
        self.assertIn("Record both as a short", plan)
        step = " ".join(prompts.prompt("step-plan").split())
        self.assertIn("reopen the plan's Namespace and data map and the current tree of each environment it touches.", step)
        self.assertIn("Stored data follows the planned schema", rubric)
        self.assertIn("Using Schema and storage guidance, decide how each environment stores the data", plan)
        self.assertIn("Namespace and data map", plan)
        self.assertIn("each stored field, key, table or payload with its owning environment, migration", step)
        self.assertIn("and round-trip check; record a changed placement or schema with its reason", step)
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
        self.assertIn("a plain interaction where the plan called for a rich one", VERIFY_REVIEW)
        for stage in ("plan", "step-plan"):
            with self.subTest(stage=stage):
                self.assertIn("For a human-facing UI, default to an ambitious, highly interactive design",
                              " ".join(prompts.prompt(stage).split()))

    def test_supporting_stages_carry_their_code_quality_duties(self):
        expected = {
            "step-plan": "each such entry point checks its arguments and carries a contract",
            "test-spec": "one rejection case per\nconstraint it checks",
            "test": "Each new or changed public entry point gets its rejection cases",
            "system-test-author": "shared test helpers check their arguments",
        }
        for stage, phrase in expected.items():
            with self.subTest(stage=stage):
                self.assertIn(" ".join(phrase.split()), " ".join(prompts.prompt(stage).split()))
        # verify's entry-point walk is its loop's work, which the packet prints in the invoke block.
        self.assertIn("list every new or changed public entry point", VERIFY_REVIEW)
        self.assertIn("walk one valid, one boundary and one invalid input", VERIFY_REVIEW)
        self.assertIn("argument checks and contract docstrings at each entry point", VERIFY_REVIEW)


if __name__ == "__main__":
    unittest.main()
