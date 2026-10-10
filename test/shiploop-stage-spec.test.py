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
import shiploop_prompts as prompts  # noqa: E402
import shiploop_quality as quality  # noqa: E402
import shiploop_stage_spec as spec  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402

PRELUDE = ("intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare")
INNER = ("get-next-work-item", "step-plan", "test-spec", "baseline", "test-author", "test-red", "implement",
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
                # An Improve contract's exit joins the entries with "; " (loop_contract.stage_exit), so an entry that
                # holds a "; " of its own would read there as two conditions.
                self.assertTrue(all(";" not in item for item in row.done_when))
                self.assertEqual(prompts.STAGE_PURPOSE[name], row.goal)

    def test_improve_rules(self) -> None:
        self.assertEqual(prompts.PLANNING_REVIEW_STAGES, frozenset({
            "spec", "test-strategy", "plan", "step-plan", "test-spec", "system-test-author", "release-plan"}))
        self.assertEqual(spec.with_improve("last-item"), frozenset({"carry-forward"}))

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
        self.assertEqual(test_loop.RERUN_STAGES, ("test-refine", "static-checks", "verify", "integration-verify",
                                                 "system-test", "release-verify"))
        self.assertEqual(test_loop.RED_STAGE, "test-red")
        self.assertEqual(test_loop.PROBE_STAGE, "test-author")
        self.assertEqual(spec.with_complete_run("test-probe"), ("test-author",))
        self.assertIn("test-probe", spec.COMPLETE_RUNS)
        self.assertEqual(spec.stage("test-author").complete_runs, ("test-probe",))
        self.assertEqual(quality.STAGE, "static-checks")
        self.assertEqual(spec.with_entry_run("lint-base"), ("get-next-work-item",))
        # ShipLoop loops are unbounded (owner decision 2026-09-26): no stage carries a limit.
        self.assertFalse(any(hasattr(spec.stage(name), "loop_limit") for name in spec.STAGES))
        for condition in (prompts.QUALITY_REPEAT_CONDITION, prompts.TEST_REPEAT_CONDITION):
            self.assertIn("no iteration limit", condition)
            self.assertNotIn("Stop cancelled when", condition)
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
        # gate, test run or loop check.  Exempt, each checked by a later stage:
        # integrate (integration-verify reruns every command) and
        # system-test-author (its tests run at system-test).  test-author is not
        # exempt: ShipLoop runs its focused commands once and requires that a test ran
        # (the test-probe run), so a test that cannot load is refused where it can be fixed.
        exempt = {"integrate", "system-test-author"}
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
