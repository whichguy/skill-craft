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
import shiploop_loops as loops  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_stage_spec as spec  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402

PRELUDE = ("intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare")
# Verify is retired (design T §9.1 2b-4c): each step's document stage and its review close the step, and the commit
# stage, ShipLoop's own, commits it.
INNER = ("step-plan", "test-spec", "validate-existing", "implement", "test", "document", "carry-forward")
OUTER = ("system-test-author", "system-test", "product-acceptance", "release-plan", "release-check",
         "release", "release-verify", "operations", "handoff")


class StageTableTest(unittest.TestCase):
    def test_graph_order_is_the_fixed_23_stages(self) -> None:
        self.assertEqual(len(spec.STAGES), 23)
        self.assertEqual(spec.PRELUDE, PRELUDE)
        self.assertEqual(spec.INNER, INNER)
        self.assertEqual(spec.OUTER, OUTER)
        self.assertEqual(prompts.STAGES, PRELUDE + INNER + OUTER)

    def test_every_row_states_a_goal_and_how_it_is_confirmed(self) -> None:
        for name, row in spec.STAGE_SPEC.items():
            with self.subTest(stage=name):
                self.assertTrue(row.goal.strip())
                # A goal is one action sentence that also says where its output goes (packet re-cut R1, tightened in
                # round 2 to about 140 characters), so it is longer than the old 80-character label.  Nothing
                # downstream truncates it: the status block's Next line and the narrative show the short goal.
                self.assertLessEqual(len(row.goal), 160)
                self.assertTrue(row.short_goal.strip())
                self.assertLessEqual(len(row.short_goal), 60)
                self.assertTrue(row.goal.rstrip().endswith("."))
                self.assertTrue(row.done_when)
                self.assertTrue(all(item.strip() for item in row.done_when))
                # An Improve contract's exit joins the entries with "; " (loop_contract.stage_exit), so an entry that
                # holds a "; " of its own would read there as two conditions.
                self.assertTrue(all(";" not in item for item in row.done_when))
                self.assertEqual(prompts.STAGE_PURPOSE[name], row.short_goal)

    def test_no_goal_or_condition_names_a_folder_the_knowledge_layout_removed(self) -> None:
        """The spec goal said this run's ID changes were in FEATURE/spec.md; there is no FEATURE folder since the
        knowledge layout moved to HOME (consumer contract 4b), and ShipLoop derives the changes from the spec diff."""
        for name, row in spec.STAGE_SPEC.items():
            with self.subTest(stage=name):
                for text in (row.goal, *row.done_when):
                    self.assertNotIn("FEATURE", text)
        self.assertIn("ShipLoop derives this run's ID changes from the spec diff", spec.stage("spec").goal)

    def test_no_stage_row_has_wording_for_an_action_that_builds_several_steps(self) -> None:
        """Design T section 9.1 2c-1: every route issues one implement action per step, so a row has one goal and one
        list of conditions, and nothing words itself for 'S1 to S2'."""
        for name, row in spec.STAGE_SPEC.items():
            with self.subTest(stage=name):
                self.assertFalse(hasattr(row, "steps_goal"))
                self.assertFalse(hasattr(row, "steps_done_when"))
        self.assertFalse(hasattr(spec, "for_steps"))

    def test_improve_rules(self) -> None:
        self.assertEqual(prompts.PLANNING_REVIEW_STAGES, frozenset({
            "spec", "test-strategy", "plan", "step-plan", "system-test-author", "release-plan"}))
        self.assertEqual(spec.with_improve("last-item"), frozenset({"carry-forward"}))
        # Rule item (owner, 2026-10-26, design 560c396f P0): one implement review per work item; test-spec has none.
        self.assertEqual(spec.IMPROVE_RULES, ("always", "last-item", "item", "first-item"))
        # Design T §8 (owner 2026-10-27/28): each step's one review follows its document stage.
        self.assertEqual(spec.with_improve("item"), frozenset({"document"}))
        self.assertIsNone(spec.stage("test-spec").improve)

    def test_planning_review_modes(self) -> None:
        """The run option `planning_review`: the registered modes and the stages a mode reviews."""
        self.assertEqual(spec.PLANNING_REVIEW_MODES, ("stage", "none"))
        self.assertEqual(spec.DEFAULT_PLANNING_REVIEW, "stage")
        self.assertIn(spec.DEFAULT_PLANNING_REVIEW, spec.PLANNING_REVIEW_MODES)
        # `stage`: every stage whose rule is `always` starts an Improve child, and the `first-item` stage (step-plan)
        # does for the first work item and an item that was sent back (owner, 2026-10-19).
        self.assertEqual(spec.with_improve("first-item"), frozenset({"step-plan"}))
        self.assertEqual(spec.reviewed_stages("stage"), spec.with_improve("always") | spec.with_improve("first-item"))
        self.assertEqual(spec.reviewed_stages("stage"), frozenset({
            "spec", "test-strategy", "plan", "step-plan", "system-test-author", "release-plan"}))
        # `none` starts no child at the four planning stages the option covers; the children after
        # system-test-author and release-plan stay, and the last carry-forward's rule is not the option's.
        self.assertEqual(spec.PLANNING_CHOICE_STAGES, frozenset({"spec", "test-strategy", "plan", "step-plan"}))
        self.assertEqual(spec.reviewed_stages("none"), frozenset({"system-test-author", "release-plan"}))
        self.assertEqual(spec.with_improve("last-item"), frozenset({"carry-forward"}))
        for mode in spec.PLANNING_REVIEW_MODES:
            self.assertLessEqual(spec.reviewed_stages(mode), spec.with_improve("always") | spec.with_improve("first-item"))
        # the six-stage set the option does not redefine still drives the source-printing packets
        self.assertEqual(prompts.PLANNING_REVIEW_STAGES, spec.reviewed_stages("stage"))
        with self.assertRaises(ValueError):
            spec.reviewed_stages("two")

    def test_prompt_block_sets(self) -> None:
        self.assertEqual(prompts.TEST_FACILITY_STAGES, frozenset({
            "test-strategy", "plan", "step-plan", "test-spec", "test", "carry-forward", "system-test-author",
            "release-plan"}))
        self.assertEqual(prompts.TEST_DECISION_STAGES, frozenset({"step-plan", "test-spec", "test"}))
        self.assertEqual(prompts.BACKCHAIN_STAGES, frozenset({
            "spec", "plan", "step-plan", "carry-forward", "product-acceptance"}))
        self.assertEqual(prompts.BACKCHAIN_AUDIT_STAGES, frozenset({
            "spec", "step-plan", "carry-forward", "product-acceptance"}))
        self.assertEqual(prompts.RECONCILIATION_STAGES, frozenset({
            "system-test", "product-acceptance", "release-verify", "handoff"}))
        # The Code craft block prints where product code is written: implement only (owner, 2026-10-11).  test and
        # document cite the rules they apply in their own duties, and the step review carries the rubric.
        self.assertEqual(prompts.IMPLEMENTATION_STAGES, frozenset({"implement"}))
        # step-plan's duty carries its own design-basis point (2026-10-11 dedupe), so it left this block.
        self.assertEqual(spec.with_block("interaction-design"),
                         frozenset({"discovery", "research", "spec", "plan"}))
        self.assertNotIn("interaction-design", spec.stage("step-plan").blocks)
        self.assertEqual(spec.with_block("work-items"), frozenset({"plan", "carry-forward"}))
        self.assertEqual(set(prompts.ENVIRONMENT_DISCOVERY_REQUIREMENTS), {"discovery", "research"})

    def test_assistive_tool_runs(self) -> None:
        # Document's done is gated on its own edits and reruns what they could affect (design T §8.2, 2b-4b).
        self.assertEqual(lint.GATE_STAGES, ("implement", "test", "document"))
        self.assertEqual(lint.GATE_STAGE, "implement")
        self.assertFalse(hasattr(lint, "LINT_STAGES"))  # verify's advisory entry pass is gone with it
        self.assertEqual(test_loop.STAGES, ("test",))
        self.assertEqual(test_loop.RERUN_STAGES, ("document", "system-test", "release-verify"))
        self.assertEqual(test_loop.STEP_RERUN_STAGE, "document")
        self.assertFalse(hasattr(test_loop, "RED_STAGE"))
        self.assertFalse(hasattr(test_loop, "PROBE_STAGE"))
        self.assertEqual(spec.with_complete_run("test-base"), ("test",))
        self.assertNotIn("test-probe", spec.COMPLETE_RUNS)
        self.assertEqual(spec.with_complete_run("expectation-check"), ("validate-existing",))
        self.assertEqual(spec.ENTRY_RUNS, frozenset({"lint-base", "loop-contract", "expectation-check"}))
        self.assertEqual(spec.with_entry_run("lint-base"), ("step-plan",))
        # Every inner stage is an Until Loop: its contract is written on entry and its receipt checked at complete.
        self.assertEqual(spec.with_entry_run("loop-contract"), spec.INNER)
        self.assertEqual(spec.with_complete_run("loop-terminal"), spec.INNER)
        self.assertEqual(loops.STAGES, spec.INNER)
        # ShipLoop loops are unbounded (owner decision 2026-09-26): no stage carries a limit.
        self.assertFalse(any(hasattr(spec.stage(name), "loop_limit") for name in spec.STAGES))
        for name in spec.INNER:
            with self.subTest(stage=name):
                self.assertIn("no iteration limit", loops.REPEAT[name])
                self.assertNotIn("Stop cancelled when", loops.REPEAT[name])
        # Owner 2026-10-24: no run caps.  No refused-run cap, send-back cap or keepalive release remains.
        self.assertFalse(hasattr(test_loop, "MAX_REFUSED_RUNS") or hasattr(spec, "MAX_SEND_BACKS"))

    def test_no_count_stop_remains_and_every_copy_of_the_stuck_rule_carries_its_anchor(self) -> None:
        """SPEC S-10 (amended 2026-10-28): the model's stopping rule is a criterion, not a count.  The refused-run cap,
        the send-back cap and the keepalive release were removed on 2026-10-24 and the genuine-fix count on 2026-10-28
        (owner: no count stops), so no text may state one: a leftover copy would tell a model a stop rule that no gate
        applies.  The prompts carry the rule itself and every prose copy its anchor."""
        import re
        import shiploop_chain as chain
        import shiploop_keepalive as keepalive
        import shiploop_loops as loops
        import shiploop_prompts as prompts
        self.assertFalse(hasattr(keepalive, "STUCK_CONTINUATIONS"))
        self.assertFalse(hasattr(spec, "GENUINE_FIX_ATTEMPTS"))
        self.assertIn(spec.STUCK_FIX_ANCHOR, spec.STUCK_FIX)
        for name, text in (("implement repeat", loops.REPEAT["implement"]), ("step repeat", loops.REPEAT_STEP),
                           ("implement duty", prompts.prompt("implement", delegation=prompts.INLINE))):
            with self.subTest(prompt=name):
                self.assertIn(spec.STUCK_FIX, " ".join(text.split()))
        self.assertIn(spec.STUCK_FIX_ANCHOR, " ".join(chain._EXIT_CRITERIA_INSTRUCTION.split()))
        gone = (
            re.compile(r"\b(?:\d+|seven|three)\s+genuine\s+fix\s+attempts\b", re.IGNORECASE),
            re.compile(r"GENUINE_FIX_ATTEMPTS"),
            re.compile(r"\b\d+\s+refused\s+runs\b"),
            re.compile(r"\b\d+(?:st|nd|rd|th)\s+refused\s+run\b"),
            re.compile(r"\b(?:spend one of|reach) the \d+\b"),
            re.compile(r"count\s+only\s+so\s+far:\s+after\s+\d+|\b\d+\s+continuations\s+without\s+an\s+accepted\s+result"),
            re.compile(r"MAX_REFUSED_RUNS|STUCK_CONTINUATIONS|MAX_SEND_BACKS"),
            re.compile(r"at most twice per (?:item|destination)|sent back twice|has used its \d+ send-backs"),
            re.compile(r"no longer accepted for this action"),
        )
        sources = [*sorted((ROOT / "skills/shiploop").rglob("*.md")), *sorted((ROOT / "skills/shiploop/scripts").glob("*.py")),
                   ROOT / "test/shiploop_e2e/SPEC.md"]
        lead = spec.STUCK_FIX_ANCHOR.removesuffix("genuine fix")
        copies = 0
        for path in sources:
            raw = path.read_text(encoding="utf-8")
            if path.name == "SPEC.md":
                self.assertIn(spec.STUCK_FIX_ANCHOR, " ".join(raw.split()))
                continue  # its carve-out names the removed constants and the old count as history
            if path.suffix == ".md":
                text = " ".join(raw.split())
                for match in re.finditer("genuine fix", text):
                    copies += 1
                    with self.subTest(file=str(path.relative_to(ROOT)), text=text[match.start() - 40:match.end()]):
                        self.assertEqual(text[match.start() - len(lead):match.start()], lead)
            for pattern in gone:
                with self.subTest(file=str(path.relative_to(ROOT)), removed=pattern.pattern):
                    self.assertIsNone(pattern.search(raw))
        self.assertGreaterEqual(copies, 4)  # the scan reaches the copies: the skill card and the references

    def test_stages_that_edit_code_run_a_script_check_before_done(self) -> None:
        # A stage that may change code or tests must end with a script-run lint
        # gate, test run or loop check.  Exempt, checked by a later stage:
        # system-test-author (its tests run at system-test).
        exempt = {"system-test-author"}
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
