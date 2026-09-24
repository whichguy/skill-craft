#!/usr/bin/env python3
"""Pin when Improve runs: every planning result plus one end-of-work review."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/shiploop"
CLI = PACKAGE / "scripts/shiploop"
CARD = ROOT / "skills/improve/SKILL.md"
sys.path.insert(0, str(PACKAGE / "scripts"))
import shiploop_navigator as nav  # noqa: E402
import shiploop_standalone_improve as standalone  # noqa: E402
import shiploop_store as store  # noqa: E402

DONE = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}


def receipt(stage):
    return {"summary": "Synthetic Improve completion for " + stage + ".",
            "review_refs": ["synthetic://review/" + stage], "check_refs": ["synthetic://check/" + stage]}


def walk(state, *, plan_items=None, end_final=None, limit=200):
    """Drive the pure navigator to done; return the stages that started an Improve child."""
    reviewed = []
    for _ in range(limit):
        if state["status"] == "done":
            return state, reviewed
        stage, action = nav.current_stage(state), nav.current_action(state)["id"]
        result = dict(DONE, work_items=plan_items) if stage == "plan" and plan_items else DONE
        state = nav.apply(state, action, result)
        if state["active_improve"] is not None:
            reviewed.append((stage, nav._current_work_item(state)))
            final = end_final.pop(0) if stage == "carry-forward" and end_final else None
            state = nav.finish_improve(state, action, receipt(stage), final)
    raise AssertionError("walk did not finish")


class ImproveScheduleTests(unittest.TestCase):
    def new(self):
        return nav.new_state("/simulation-only/repo", "Schedule fixture.", protocol_version=3,
                             improve_skill="")

    def test_planning_stages_and_the_end_start_improve(self):
        items = [{"id": "W1", "title": "First"}, {"id": "W2", "title": "Second"}]
        state, reviewed = walk(self.new(), plan_items=items)
        self.assertEqual(reviewed, [
            ("spec", None), ("test-strategy", None), ("plan", None),
            ("step-plan", "W1"), ("test-spec", "W1"),
            ("step-plan", "W2"), ("test-spec", "W2"), ("carry-forward", "W2"),
            ("system-test-author", None), ("release-plan", None),
        ])
        self.assertEqual(state["status"], "done")

    def test_end_review_that_adds_work_moves_to_the_new_last_item(self):
        added = dict(DONE, work_items=[{"id": "W2", "title": "Found by the end review"}])
        _, reviewed = walk(self.new(), end_final=[added])
        ends = [entry for entry in reviewed if entry[0] == "carry-forward"]
        self.assertEqual(ends, [("carry-forward", "W1"), ("carry-forward", "W2")])

    def test_state_still_requires_the_plan_review(self):
        state, _ = walk(self.new())
        plan = next(e["action"] for e in state["history"] if e["stage"] == "plan")
        broken = dict(state, improve_results={k: v for k, v in state["improve_results"].items() if k != plan})
        with self.assertRaisesRegex(nav.NavigatorError, "every plan result"):
            nav.validate(broken)

    def test_producer_packet_leads_with_its_callback_and_says_no_child_runs(self):
        state = self.new()
        lines = nav.render(None, Path("/simulation-only/run"), state).splitlines()
        self.assertTrue(lines[0].startswith("ShipLoop navigator | intake"))
        self.assertIn(" complete ", lines[1])
        self.assertIn(nav.current_action(state)["id"], lines[1])
        self.assertIn("This result advances directly; no Improve child runs", "\n".join(lines))

    def test_template_placeholder_is_refused(self):
        state = self.new()
        action = nav.current_action(state)["id"]
        with self.assertRaisesRegex(nav.NavigatorError, "template placeholder"):
            nav.apply(state, action, dict(DONE, evidence_refs=[nav.EVIDENCE_PLACEHOLDER]))

    def test_planning_improve_packet_has_focus_callback_first_and_honest_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp).resolve() / "repo"
            repo.mkdir()
            run = repo.parent / "run"
            run.mkdir()
            state = nav.new_state(str(repo), "Schedule fixture.", protocol_version=3, improve_skill="")
            while nav.current_stage(state) != "spec":
                # Unreviewed predecessors have no Improve receipt to point at.
                self.assertNotIn("Prior Improve evidence", nav.render(None, run, state))
                state = nav.apply(state, nav.current_action(state)["id"], DONE)
            action = nav.current_action(state)["id"]
            state = nav.apply(state, action, DONE)
            child = state["active_improve"]
            state["active_improve"] = standalone.binding(
                state, action, "spec", child["seed_result"], standalone.resolve_skill(str(CARD)))
            packet = nav.render(None, run, state)
        self.assertIn("improve-complete", packet.splitlines()[1])
        self.assertIn("Planning review focus", packet)
        self.assertIn("self-passes by this same executor, not independent reviewers", packet)
        self.assertNotIn("Capture separate durable review files", packet)


class ReceiptCountTests(unittest.TestCase):
    def test_three_review_refs_are_refused_with_the_fix(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp).resolve()
            refs = []
            for name in ("material", "one", "two"):
                path = workspace / (name + ".md")
                path.write_text(name)
                refs.append(str(path))
            with self.assertRaisesRegex(standalone.StandaloneImproveError,
                                        "got 3; list only the two trivial-streak reviews"):
                standalone._receipt({"summary": "s", "review_refs": refs, "check_refs": [refs[0]]},
                                    workspace, "receipt")


if __name__ == "__main__":
    unittest.main()
