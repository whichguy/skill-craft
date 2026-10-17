#!/usr/bin/env python3
"""ShipLoop's fixed stage table and the per-stage sets derived from it.

The expected values below are written out independently of the table, so a
change to a stage's behaviour has to change both the table and this suite.
"""

from __future__ import annotations

import dataclasses
import importlib.util
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
import shiploop_quality as quality  # noqa: E402
import shiploop_stage_spec as spec  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402

PRELUDE = ("intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare")
INNER = ("step-plan", "test-spec", "validate-existing", "implement", "test", "document", "verify", "carry-forward")
OUTER = ("system-test-author", "system-test", "product-acceptance", "release-plan", "release-check",
         "release", "release-verify", "operations", "handoff")


class StageTableTest(unittest.TestCase):
    def test_graph_order_is_the_fixed_24_stages(self) -> None:
        self.assertEqual(len(spec.STAGES), 24)
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
                for text in (row.goal, *row.done_when, row.steps_goal or "", *row.steps_done_when):
                    self.assertNotIn("FEATURE", text)
        self.assertIn("ShipLoop derives this run's ID changes from the spec diff", spec.stage("spec").goal)

    def test_the_several_steps_wording_is_a_pair_of_the_goal_and_each_condition_of_one_row(self) -> None:
        """Only implement words itself for the steps one ask-agent action builds; a condition keeps the row's rules."""
        self.assertEqual([name for name, row in spec.STAGE_SPEC.items() if row.steps_goal is not None], ["implement"])
        row = spec.stage("implement")
        worded = spec.for_steps(row, "S1 to S2", "a.py, b.py")
        self.assertEqual(len(worded.done_when), len(row.done_when))
        self.assertTrue(worded.goal.rstrip().endswith("."))
        self.assertTrue(all(";" not in item for item in worded.done_when))   # the Improve contract joins them with "; "
        self.assertIn("S1 to S2", worded.goal)
        self.assertIn("S1 to S2", worded.done_when[0])
        self.assertEqual(worded.done_when[1], row.done_when[1])               # shared conditions are word for word
        with self.assertRaises(ValueError):                                   # a goal without one condition per entry
            dataclasses.replace(row, steps_done_when=row.steps_done_when[:2])

    def test_improve_rules(self) -> None:
        self.assertEqual(prompts.PLANNING_REVIEW_STAGES, frozenset({
            "spec", "test-strategy", "plan", "step-plan", "test-spec", "system-test-author", "release-plan"}))
        self.assertEqual(spec.with_improve("last-item"), frozenset({"carry-forward"}))

    def test_the_improve_review_gate_of_each_stage(self) -> None:
        """D-6 / R1 (a proposal awaiting the owner's S-10 text): the document stages' reviews stop on one unchanged pass
        (gate 2); an implement step's and the last carry-forward's, which review code, need two in a row once a pass has
        changed the content (gate 3).  Written out here independently of the table, and tied to the runtime's constants."""
        expected = {name: 2 for name in ("spec", "test-strategy", "plan", "step-plan", "test-spec", "system-test-author",
                                         "release-plan")}
        expected.update({"implement": 3, "carry-forward": 3})
        self.assertEqual({name: spec.improve_gate(name) for name in spec.STAGES if spec.STAGE_SPEC[name].improve},
                         expected)
        self.assertEqual(dict(spec.IMPROVE_GATES), {"always": 2, "step": 3, "last-item": 3})
        with self.assertRaisesRegex(ValueError, "starts no Improve child"):
            spec.improve_gate("verify")
        runtime_spec = importlib.util.spec_from_file_location(
            "until_loop_ephemeral_gates", ROOT / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py")
        runtime = importlib.util.module_from_spec(runtime_spec)
        runtime_spec.loader.exec_module(runtime)
        self.assertEqual((spec.ONE_PASS_GATE, spec.TWO_PASS_GATE),
                         (runtime.UNCHANGED_GATE, runtime.UNCHANGED_AFTER_EDIT_GATE))

    def test_planning_review_modes(self) -> None:
        """The run option `planning_review`: the registered modes and the stages a mode reviews."""
        self.assertEqual(spec.PLANNING_REVIEW_MODES, ("stage", "none"))
        self.assertEqual(spec.DEFAULT_PLANNING_REVIEW, "stage")
        self.assertIn(spec.DEFAULT_PLANNING_REVIEW, spec.PLANNING_REVIEW_MODES)
        # `stage` is today's behaviour: every stage whose rule is `always` starts an Improve child.
        self.assertEqual(spec.reviewed_stages("stage"), spec.with_improve("always"))
        self.assertEqual(spec.reviewed_stages("stage"), frozenset({
            "spec", "test-strategy", "plan", "step-plan", "test-spec", "system-test-author", "release-plan"}))
        # `none` starts no child at the five planning stages the option covers; the children after
        # system-test-author and release-plan stay, and the last carry-forward's rule is not the option's.
        self.assertEqual(spec.PLANNING_CHOICE_STAGES, frozenset({
            "spec", "test-strategy", "plan", "step-plan", "test-spec"}))
        self.assertEqual(spec.reviewed_stages("none"), frozenset({"system-test-author", "release-plan"}))
        self.assertEqual(spec.with_improve("last-item"), frozenset({"carry-forward"}))
        for mode in spec.PLANNING_REVIEW_MODES:
            self.assertLessEqual(spec.reviewed_stages(mode), spec.with_improve("always"))
        # the seven-stage set the option does not redefine still drives the source-printing packets
        self.assertEqual(prompts.PLANNING_REVIEW_STAGES, spec.with_improve("always"))
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
            "verify", "system-test", "product-acceptance", "release-verify", "handoff"}))
        # The Code craft block prints where product code is written: implement only (owner, 2026-10-11).  test,
        # document and verify cite the rules they apply in their own duties.
        self.assertEqual(prompts.IMPLEMENTATION_STAGES, frozenset({"implement"}))
        # step-plan's duty carries its own design-basis point (2026-10-11 dedupe), so it left this block.
        self.assertEqual(spec.with_block("interaction-design"),
                         frozenset({"discovery", "research", "spec", "plan"}))
        self.assertNotIn("interaction-design", spec.stage("step-plan").blocks)
        self.assertEqual(spec.with_block("work-items"), frozenset({"plan", "carry-forward"}))
        self.assertEqual(set(prompts.ENVIRONMENT_DISCOVERY_REQUIREMENTS), {"discovery", "research"})

    def test_assistive_tool_runs(self) -> None:
        self.assertEqual(lint.GATE_STAGES, ("implement", "test", "verify"))
        self.assertEqual(lint.GATE_STAGE, "implement")
        self.assertEqual(lint.LINT_STAGES, ("verify",))
        self.assertEqual(test_loop.STAGES, ("test",))
        self.assertEqual(test_loop.RERUN_STAGES, ("verify", "system-test", "release-verify"))
        self.assertFalse(hasattr(test_loop, "RED_STAGE"))
        self.assertFalse(hasattr(test_loop, "PROBE_STAGE"))
        self.assertEqual(spec.with_complete_run("test-base"), ("test",))
        self.assertNotIn("test-probe", spec.COMPLETE_RUNS)
        self.assertEqual(spec.with_complete_run("expectation-check"), ("validate-existing",))
        self.assertEqual(quality.STAGE, "verify")
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
        self.assertEqual(test_loop.MAX_REFUSED_RUNS, 11)

    def test_every_prose_copy_of_a_cap_names_its_constant_value(self) -> None:
        """SPEC S-10 carve-out (owner decision 2026-10-10): the refused-run cap, the genuine-fix-attempt rule and the
        keepalive release are constants, and every copy of them in ShipLoop's text and the SPEC says the same number.
        The caps went 7 -> 11, 3 -> 7 and 14 -> 22 on 2026-10-10, and a copy that kept an old number would tell a model
        a different rule than the gate applies."""
        import re
        import shiploop_keepalive as keepalive
        words = {"seven": 7, "eleven": 11, "three": 3, "fourteen": 14, "twenty-two": 22}
        refused, attempts, stuck = test_loop.MAX_REFUSED_RUNS, spec.GENUINE_FIX_ATTEMPTS, keepalive.STUCK_CONTINUATIONS
        self.assertEqual((refused, attempts, stuck), (11, 7, 2 * test_loop.MAX_REFUSED_RUNS))
        rules = (
            (re.compile(r"\b(\d+)\s+refused\s+runs\b"), refused),
            (re.compile(r"\b(\d+)(?:st|nd|rd|th)\s+refused\s+run\b"), refused),
            (re.compile(r"\b(?:spend one of|reach) the (\d+)\b"), refused),
            (re.compile(r"\bup\s+to\s+(\w+(?:-\w+)?)\s+times\b"), refused),
            (re.compile(r"\b(\d+)\s+genuine\s+fix\s+attempts\b"), attempts),
            # ShipLoop's release only; "Grok ends a turn after 8 continuations" is the host's own limit.
            (re.compile(r"count\s+only\s+so\s+far:\s+after\s+(\d+)|\b(\d+)\s+continuations\s+without\s+an\s+accepted\s+result"), stuck),
            (re.compile(r"MAX_REFUSED_RUNS` \((\d+)\)"), refused),
            (re.compile(r"GENUINE_FIX_ATTEMPTS` \((\d+)\)"), attempts),
            (re.compile(r"STUCK_CONTINUATIONS` \((\d+)"), stuck),
        )
        sources = [*sorted((ROOT / "skills/shiploop").rglob("*.md")), *sorted((ROOT / "skills/shiploop/scripts").glob("*.py")),
                   ROOT / "test/shiploop_e2e/SPEC.md"]
        found = 0
        for path in sources:
            text = path.read_text(encoding="utf-8")
            for pattern, value in rules:
                for match in pattern.finditer(text):
                    number = next(group for group in match.groups() if group)
                    number = words.get(number.lower(), number)
                    if not str(number).isdigit():
                        continue  # "up to N times" also reads other quantities; only a number word is a cap copy
                    found += 1
                    with self.subTest(file=str(path.relative_to(ROOT)), text=match.group(0)):
                        self.assertEqual(int(number), value)
        self.assertGreater(found, 10)  # the scan reaches the copies (SKILL.md, references, prompts, SPEC)

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
