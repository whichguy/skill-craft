#!/usr/bin/env python3
"""ShipLoop's fixed stage table and the per-stage sets derived from it.

The expected values below are written out independently of the table, so a
change to a stage's behaviour has to change both the table and this suite.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_context_index as context_index  # noqa: E402
import shiploop_lint as lint  # noqa: E402
import shiploop_navigator_v3_prompts as prompts  # noqa: E402
import shiploop_quality as quality  # noqa: E402
import shiploop_stage_spec as spec  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402

PRELUDE = ("intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare")
INNER = ("select-work", "step-plan", "test-spec", "baseline", "test-author", "test-red", "implement",
         "test-green", "test-refine", "regression", "document", "skill-assess", "skill-validate",
         "static-checks", "verify", "integrate", "integration-verify", "carry-forward")
OUTER = ("system-test-author", "system-test", "product-acceptance", "release-plan", "release-check",
         "release", "release-verify", "operations", "handoff")


class StageTableTest(unittest.TestCase):
    def test_graph_order_is_the_fixed_34_stages(self) -> None:
        self.assertEqual(spec.PRELUDE, PRELUDE)
        self.assertEqual(spec.INNER, INNER)
        self.assertEqual(spec.OUTER, OUTER)
        self.assertEqual(prompts.STAGES, PRELUDE + INNER + OUTER)

    def test_every_row_states_a_goal_and_how_it_is_confirmed(self) -> None:
        for name, row in spec.STAGE_SPEC.items():
            with self.subTest(stage=name):
                self.assertTrue(row.goal.strip())
                self.assertLessEqual(len(row.goal), 80)
                self.assertTrue(row.done_when)
                self.assertTrue(all(item.strip() for item in row.done_when))
                self.assertEqual(prompts.STAGE_PURPOSE[name], row.goal)

    def test_improve_rules(self) -> None:
        self.assertEqual(prompts.PLANNING_REVIEW_STAGES, frozenset({
            "spec", "test-strategy", "plan", "step-plan", "test-spec", "system-test-author", "release-plan"}))
        self.assertEqual(spec.with_improve("last-item"), frozenset({"carry-forward"}))

    def test_prompt_block_sets(self) -> None:
        self.assertEqual(prompts.TEST_FACILITY_STAGES, frozenset({
            "test-strategy", "plan", "step-plan", "test-spec", "test-author", "test-red", "test-refine",
            "regression", "carry-forward", "system-test-author", "release-plan"}))
        self.assertEqual(prompts.TEST_DECISION_STAGES, frozenset({
            "step-plan", "test-spec", "test-author", "test-refine", "regression"}))
        self.assertEqual(prompts.BACKCHAIN_STAGES, frozenset({
            "spec", "plan", "step-plan", "carry-forward", "product-acceptance"}))
        self.assertEqual(prompts.BACKCHAIN_AUDIT_STAGES, frozenset({
            "spec", "step-plan", "carry-forward", "product-acceptance"}))
        self.assertEqual(prompts.RECONCILIATION_STAGES, frozenset({
            "verify", "integration-verify", "system-test", "product-acceptance", "release-verify", "handoff"}))
        # Code craft goes where code or tests are written or reviewed, not to
        # the planning stages step-plan and test-spec.
        self.assertEqual(prompts.IMPLEMENTATION_STAGES, frozenset({
            "test-author", "test-red", "implement", "test-green", "test-refine",
            "regression", "document", "static-checks", "verify", "integrate", "integration-verify"}))
        self.assertEqual(spec.with_block("interaction-design"),
                         frozenset({"discovery", "research", "spec", "plan", "step-plan"}))
        self.assertEqual(spec.with_block("work-items"), frozenset({"plan", "carry-forward"}))
        self.assertEqual(prompts.PASS_OR_STOP_STAGES, frozenset({"test-refine", "integration-verify"}))
        self.assertEqual(set(prompts.ENVIRONMENT_DISCOVERY_REQUIREMENTS), {"discovery", "research"})

    def test_assistive_tool_runs(self) -> None:
        self.assertEqual(lint.GATE_STAGES, ("implement", "test-green", "regression"))
        self.assertEqual(lint.GATE_STAGE, "implement")
        self.assertEqual(lint.LINT_STAGES, ("static-checks", "verify"))
        self.assertEqual(test_loop.STAGES, ("test-green", "regression"))
        self.assertEqual(test_loop.RERUN_STAGES, ("test-refine", "static-checks", "integration-verify"))
        self.assertEqual(test_loop.RED_STAGE, "test-red")
        self.assertEqual(quality.STAGE, "static-checks")
        self.assertEqual(spec.with_entry_run("lint-base"), ("select-work",))
        self.assertEqual(prompts.TEST_LOOP_LIMIT, 4)
        self.assertEqual(prompts.QUALITY_LOOP_LIMIT, 3)

    def test_stages_that_edit_code_run_a_script_check_before_done(self) -> None:
        # A stage that may change code or tests must end with a script-run lint
        # gate, test run or loop check.  Exempt, each checked by a later stage:
        # test-author (test-red runs its tests next), integrate
        # (integration-verify reruns every command) and system-test-author (its
        # tests run at system-test).
        exempt = {"test-author", "integrate", "system-test-author"}
        for name, row in spec.STAGE_SPEC.items():
            if {"code", "tests"} & row.edits and name not in exempt:
                with self.subTest(stage=name):
                    self.assertTrue(row.complete_runs, name)

    def test_reads_are_earlier_stages(self) -> None:
        order = {name: index for index, name in enumerate(spec.STAGES)}
        self.assertEqual(set(context_index.STAGE_READS), set(spec.STAGES))
        for name, reads in context_index.STAGE_READS.items():
            for read in reads:
                source = read[5:] if read.startswith("item:") else read
                with self.subTest(stage=name, read=read):
                    self.assertLess(order[source], order[name])

    def test_unknown_names_are_refused(self) -> None:
        with self.assertRaises(ValueError):
            spec.stage("deploy")
        with self.assertRaises(ValueError):
            spec.with_block("nope")
        with self.assertRaises(ValueError):
            spec.Stage("x", "inner", goal="g", done_when=("d",), blocks=frozenset({"nope"}))
        with self.assertRaises(ValueError):
            spec.Stage("x", "middle", goal="g", done_when=("d",))
        with self.assertRaises(ValueError):
            spec.Stage("x", "inner", goal="g", done_when=())


if __name__ == "__main__":
    unittest.main()
