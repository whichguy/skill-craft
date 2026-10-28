#!/usr/bin/env python3
"""The run reference file (`<run>/reference.md`, shiploop_reference): run-wide detail packets name by section.

Owner, 2026-10-10: a packet holds the key file references, what to do, when it is complete and what to execute;
detail a stage seldom needs lives in this file, in labelled sections a packet cites as reference#<anchor>. These
checks: save() writes it with every anchor; every policy it lists resolves to a package file; a run saved before the
file existed (or by another version) gets it on its next `next`, with its cursor unchanged.
"""
from __future__ import annotations

import io
import contextlib
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_navigator as navigator  # noqa: E402
import shiploop_reference as reference  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_store as store  # noqa: E402


class ReferenceFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-reference-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "run"
        self.root.mkdir()
        self.state = navigator.new_state(self.temp.name, "Build a thing.", delegation="inline")
        navigator.save(self.root, self.state)
        self.path = self.root / reference.REFERENCE_FILE

    def test_save_writes_every_section_with_its_anchor_and_the_package_version(self):
        text = self.path.read_text()
        self.assertEqual(text.splitlines()[0], reference.VERSION_LINE.format(version=reference.package_version()))
        self.assertTrue(reference.package_version())
        anchors = re.findall(r"^## .+ \{#([\w-]+)\}$", text, re.M)
        self.assertEqual(anchors, [anchor for anchor, _ in reference.SECTIONS])

    def test_every_policy_and_guide_resolves_to_a_package_file_and_section(self):
        for label, target in reference.POLICIES:
            path, _, anchor = target.partition("#")
            with self.subTest(label):
                file = reference.REFERENCES / path
                self.assertTrue(file.is_file(), file)
                if anchor:
                    slugs = {re.sub(r"[^\w\s-]", "", line.lstrip("#").strip().lower()).replace(" ", "-")
                             for line in file.read_text().splitlines() if line.startswith("#")}
                    self.assertIn(anchor, slugs)

    def test_a_run_without_the_file_gets_it_on_next_and_its_cursor_does_not_move(self):
        self.path.unlink()
        before = store.read_record(self.root / "state.md")
        with contextlib.redirect_stdout(io.StringIO()):
            navigator.emit(None, self.root, before)
        self.assertTrue(self.path.is_file())
        after = store.read_record(self.root / "state.md")
        self.assertEqual((after["revision"], after["action"]), (before["revision"], before["action"]))

    def test_a_file_written_by_another_version_is_replaced(self):
        self.path.write_text(reference.VERSION_LINE.format(version="0.0.1") + "\nold\n")
        self.assertTrue(reference.stale(self.root, reference.package_version()))
        with contextlib.redirect_stdout(io.StringIO()):
            navigator.emit(None, self.root, store.read_record(self.root / "state.md"))
        self.assertFalse(reference.stale(self.root, reference.package_version()))
        self.assertIn("{#rules}", self.path.read_text())


def _rules_section(text: str) -> str:
    """The text of the `rules` section of a reference file, whitespace collapsed."""
    body = re.search(r"## Rules for every stage \{#rules\}\n(.*?)\n## ", text, re.S)
    return " ".join(body.group(1).split())


def _walk_reviewed(state: dict) -> set:
    """Drive the pure navigator to done with synthetic results; the stages whose accepted result started an Improve child."""
    reviewed = set()
    for _ in range(300):
        if state["status"] == "done":
            return reviewed
        stage, action = navigator.current_stage(state), navigator.current_action(state)["id"]
        result = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}
        if stage == "plan":
            result["work_items"] = [{"id": "W1", "title": "One item"}]
        state = navigator.apply(state, action, result)
        if state["active_improve"] is not None:
            reviewed.add(stage)
            state = navigator.finish_improve(state, action, {"summary": "Synthetic Improve completion."})
    raise AssertionError("the walk did not finish")


class ReviewScheduleSentenceTests(unittest.TestCase):
    """The reference's rules section says which results start an Improve stage; it was the stage-mode list in every run,
    so a `none` run was told its planning results get a review that the engine never starts (U11, rev 4 Step 0.1)."""

    def render(self, mode: str, delegation: str) -> str:
        state = navigator.new_state("/simulation-only/repo", "Build a thing.", delegation=delegation, planning_review=mode)
        return reference.render(state, Path("/simulation-only/run"))

    def listed(self, text: str) -> list:
        found = re.search(r"starts an Improve stage after planning results \(([^)]*)\)", _rules_section(text))
        self.assertTrue(found, "the rules section names no planning results")
        # After "; " the stage mode says when the first-item stages are reviewed (rule first-item, 2026-10-19).
        return found.group(1).split(";")[0].split(", ")

    def test_the_listed_planning_results_are_the_stages_the_mode_reviews_in_graph_order(self):
        for mode in stage_spec.PLANNING_REVIEW_MODES:
            for delegation in ("inline", "ask-agent"):
                with self.subTest(mode=mode, delegation=delegation):
                    expected = [name for name in stage_spec.STAGES if name in stage_spec.reviewed_stages(mode)]
                    self.assertEqual(self.listed(self.render(mode, delegation)), expected)

    def test_none_lists_the_two_planning_results_it_still_reviews_and_stage_lists_six(self):
        self.assertEqual(self.listed(self.render("none", "inline")), ["system-test-author", "release-plan"])
        self.assertEqual(len(self.listed(self.render("stage", "inline"))), 6)
        self.assertIn("step-plan only for the first work item and after a send-back",
                      " ".join(_rules_section(self.render("stage", "inline")).split()))

    def test_the_rest_of_the_rules_text_is_the_same_in_both_modes(self):
        """Only the schedule's list differs: nothing else in the section is swapped."""
        staged, none = (_rules_section(self.render(mode, "inline")) for mode in ("stage", "none"))
        listed = lambda text: re.search(r"after planning results \([^)]*\)", text).group(0)
        self.assertTrue(listed(staged) != listed(none), "the two modes print the same schedule")
        self.assertTrue(staged.replace(listed(staged), "X") == none.replace(listed(none), "X"),
                        "the rules sections differ beyond the schedule list")

    def test_the_sentence_matches_the_children_a_run_of_that_mode_starts(self):
        """Paired with the behaviour it describes: a walk of a run starts a child after the listed planning results, after
        each step's document stage (design T section 8) and after the last carry-forward, and after nothing else."""
        for mode in stage_spec.PLANNING_REVIEW_MODES:
            with self.subTest(mode=mode):
                state = navigator.new_state("/simulation-only/repo", "Build a thing.", delegation="inline",
                                            planning_review=mode)
                listed = set(self.listed(self.render(mode, "inline")))
                self.assertEqual(_walk_reviewed(state), listed | {"document", "carry-forward"})


if __name__ == "__main__":
    unittest.main()
