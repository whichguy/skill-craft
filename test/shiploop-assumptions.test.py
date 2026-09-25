#!/usr/bin/env python3
"""Hermetic tests for the plan assumption-list gate.

The pure graph functions only validate the field's shape; the CLI submission
gates require it on a done plan, route open entries to real work items and
require evidence files to exist.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/shiploop"
sys.path.insert(0, str(PACKAGE / "scripts"))
import shiploop_assumptions as assumptions  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_store as store  # noqa: E402

CORE = types.SimpleNamespace(PACKAGE_ROOT=PACKAGE, REF_DIR=PACKAGE / "references")
DONE = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}
IMPROVE = {"summary": "Synthetic Improve.", "review_refs": ["synthetic://r"],
           "check_refs": ["synthetic://c"]}


def evidenced(ident: str, ref: str) -> dict:
    return {"id": ident, "assumption": "It holds.", "disposition": "evidenced", "evidence": [ref]}


def probed(ident: str, ref: str) -> dict:
    return {"id": ident, "assumption": "It holds.", "disposition": "probed",
            "check": "run the probe", "evidence": [ref]}


def open_row(ident: str, consumer: str) -> dict:
    return {"id": ident, "assumption": "It holds.", "disposition": "open",
            "check": "call the service", "reason": "no access here", "consumer": consumer}


class ShapeTests(unittest.TestCase):
    def refused(self, value, stage="plan") -> str:
        with self.assertRaises(assumptions.AssumptionError) as caught:
            assumptions.canonical(value, stage)
        return str(caught.exception)

    def test_missing_list_is_refused_and_empty_list_is_valid(self):
        self.assertIn("requires assumptions", self.refused(None))
        self.assertEqual(assumptions.canonical([], "plan"), [])

    def test_each_disposition_needs_exactly_its_fields(self):
        self.assertIn("disposition must be one of", self.refused(
            [{"id": "A1", "assumption": "x", "disposition": "maybe"}]))
        row = open_row("A1", "W1")
        del row["reason"]
        self.assertIn("needs exactly check, consumer, reason", self.refused([row]))
        row = evidenced("A1", "https://example.test/doc")
        row["check"] = "extra"
        self.assertIn("needs exactly evidence", self.refused([row]))
        self.assertIn("evidence must be a nonempty list", self.refused(
            [{"id": "A1", "assumption": "x", "disposition": "evidenced", "evidence": []}]))

    def test_duplicate_and_unsafe_ids_are_refused(self):
        row = evidenced("A1", "https://example.test/doc")
        self.assertIn("listed twice", self.refused([row, dict(row)]))
        self.assertIn("short identifier", self.refused([evidenced("1 bad", "https://x.test")]))

    def test_open_entries_must_name_a_work_item_in_the_queue(self):
        with self.assertRaisesRegex(assumptions.AssumptionError, "not a work item"):
            assumptions.check_consumers([open_row("A1", "W9")], {"W1"})
        assumptions.check_consumers([open_row("A1", "W1"), evidenced("A2", "https://x.test")],
                                    {"W1"})

    def test_files_must_exist_and_a_probe_must_cite_saved_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "probe.txt"
            empty = Path(temp) / "empty.txt"
            empty.touch()
            with self.assertRaisesRegex(assumptions.AssumptionError, "does not exist"):
                assumptions.check_files([evidenced("A1", str(output))])
            with self.assertRaisesRegex(assumptions.AssumptionError, "absolute path or a URL"):
                assumptions.check_files([evidenced("A1", "notes/probe.txt")])
            for ref in ("https://x.test/log", str(empty)):
                with self.assertRaisesRegex(assumptions.AssumptionError, "cites no captured output"):
                    assumptions.check_files([probed("A1", ref)])
            output.write_text("observed 200\n")
            assumptions.check_files([probed("A1", str(output)),
                                     evidenced("A2", "https://x.test/doc")])

    def test_navigator_allows_the_field_only_on_a_done_plan(self):
        for stage, outcome in (("research", "done"), ("spec", "done"), ("plan", "repeat")):
            with self.assertRaisesRegex(nav.NavigatorError, "only on a done plan"):
                nav._canonical_result(dict(DONE, outcome=outcome, assumptions=[]), stage=stage)
        # Pure graph functions validate a present list but do not require one.
        self.assertNotIn("assumptions", nav._canonical_result(DONE, stage="plan"))


class GateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.run_dir = self.base / "run"
        self.run_dir.mkdir()
        self.output = self.base / "probe.txt"
        self.output.write_text("observed 200\n")
        state = nav.new_state(str(self.repo), "Assumption fixture.", improve_skill="",
                              lint_option="off")
        nav.save(self.run_dir, state)
        state = self.state()
        while nav.current_stage(state) != "plan":
            action = nav.current_action(state)["id"]
            state = nav.apply(state, action, DONE)
            if state.get("active_improve"):
                state = nav.finish_improve(state, action, IMPROVE)
        nav.save(self.run_dir, state)

    def state(self) -> dict:
        return store.read_record(self.run_dir / "state.md")

    def complete(self, result: dict) -> None:
        state = self.state()
        action = nav.current_action(state)["id"]
        path = self.run_dir / "inbox" / (action + ".md")
        path.parent.mkdir(exist_ok=True)
        store.write_record(path, result)
        with contextlib.redirect_stdout(io.StringIO()):
            nav.dispatch(CORE, self.run_dir, state, types.SimpleNamespace(
                command="complete", action=action, result=str(path)))

    def test_research_submits_without_a_list(self):
        state = nav.new_state(str(self.repo), "Research fixture.", improve_skill="",
                              lint_option="off")
        while nav.current_stage(state) != "research":
            state = nav.apply(state, nav.current_action(state)["id"], DONE)
        nav.save(self.run_dir, state)
        self.complete(DONE)
        self.assertEqual(nav.current_stage(self.state()), "spec")

    def test_plan_gate_refuses_bad_lists_and_parks_a_complete_one(self):
        items = [{"id": "W1", "title": "First item", "context": "..."}]
        with self.assertRaisesRegex(nav.NavigatorError, "requires assumptions"):
            self.complete(dict(DONE, work_items=items))
        with self.assertRaisesRegex(nav.NavigatorError, "does not exist"):
            self.complete(dict(DONE, work_items=items,
                               assumptions=[probed("A1", str(self.base / "gone.txt"))]))
        with self.assertRaisesRegex(nav.NavigatorError, "not a work item"):
            self.complete(dict(DONE, work_items=items, assumptions=[open_row("A1", "W2")]))
        self.assertIsNone(self.state().get("active_improve"))
        rows = [probed("A1", str(self.output)), open_row("A2", "W1")]
        self.complete(dict(DONE, work_items=items, assumptions=rows))
        child = self.state()["active_improve"]
        self.assertEqual(child["stage"], "plan")
        self.assertEqual([row["id"] for row in child["seed_result"]["assumptions"]], ["A1", "A2"])

    def test_non_done_plan_needs_no_list(self):
        self.complete(dict(DONE, outcome="repeat"))
        self.assertEqual(nav.current_stage(self.state()), "plan")


if __name__ == "__main__":
    unittest.main()
