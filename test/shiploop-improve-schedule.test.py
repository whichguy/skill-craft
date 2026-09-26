#!/usr/bin/env python3
"""Pin when Improve runs: every planning result plus one end-of-work review."""
import copy
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


def advance_to(state, target, *, limit=200):
    """Drive synthetic producers (and any Improve child) until ``target`` is current."""
    for _ in range(limit):
        if nav.current_stage(state) == target and state["active_improve"] is None:
            return state
        stage, action = nav.current_stage(state), nav.current_action(state)["id"]
        state = nav.apply(state, action, DONE)
        if state["active_improve"] is not None:
            state = nav.finish_improve(state, action, receipt(stage))
    raise AssertionError("did not reach " + target)


def template(packet):
    """Parse the result template the packet prints for its producer."""
    return store.loads(packet.split("Result template:\n", 1)[1].split("\nCall this when done:", 1)[0])


def after_header(packet):
    """Return the line after the navigator header (the one legal callback slot)."""
    lines = packet.splitlines()
    index = next(i for i, line in enumerate(lines) if line.startswith("ShipLoop navigator | "))
    return lines[index + 1]


class ImproveScheduleTests(unittest.TestCase):
    def new(self):
        return nav.new_state("/simulation-only/repo", "Schedule fixture.",
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

    def test_state_requires_every_planning_stage_review(self):
        state, _ = walk(self.new())
        for stage in ("plan", "spec", "step-plan"):
            with self.subTest(stage=stage):
                action = next(e["action"] for e in state["history"] if e["stage"] == stage)
                broken = dict(state, improve_results={
                    k: v for k, v in state["improve_results"].items() if k != action})
                with self.assertRaisesRegex(nav.NavigatorError, "every planning-stage result"):
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
        run = Path("/simulation-only/run")
        # Every rendered template carries the placeholder, never an empty list.
        for stage, at in (("intake", state), ("plan", advance_to(state, "plan"))):
            with self.subTest(stage=stage):
                self.assertEqual(template(nav.render(None, run, at))["evidence_refs"],
                                 [nav.EVIDENCE_PLACEHOLDER])
        action = nav.current_action(state)["id"]
        for refs in ([nav.EVIDENCE_PLACEHOLDER], ["/simulation-only/repo/notes.md", nav.EVIDENCE_PLACEHOLDER]):
            with self.subTest(refs=refs):
                before = copy.deepcopy(state)
                with self.assertRaisesRegex(nav.NavigatorError, "template placeholder"):
                    nav.apply(state, action, dict(DONE, evidence_refs=refs))
                self.assertEqual(state, before)

    def test_planning_improve_packet_has_focus_callback_first_and_honest_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp).resolve() / "repo"
            repo.mkdir()
            run = repo.parent / "run"
            run.mkdir()
            state = nav.new_state(str(repo), "Schedule fixture.", improve_skill="")
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
        text = " ".join(packet.split())
        self.assertIn("review_refs is exactly the two files of those final consecutive trivial passes", text)
        self.assertIn("only the parent imports it", text)
        self.assertNotIn("review_refs length is exactly 2", text)

    def test_unsuccessful_last_carry_forward_advances_without_improve(self):
        state = advance_to(self.new(), "carry-forward")
        self.assertEqual(len(state["work_items"]), 1)
        action = nav.current_action(state)["id"]
        records = copy.deepcopy(state["improve_results"])
        blocked = nav.apply(state, action, dict(DONE, outcome="blocked", blocked_by="external", summary="Synthetic block."))
        self.assertIsNone(blocked["active_improve"])
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["improve_results"], records)
        repeated = nav.apply(state, action, dict(DONE, outcome="repeat", summary="Synthetic retry."))
        self.assertIsNone(repeated["active_improve"])
        self.assertEqual(nav.current_stage(repeated), "carry-forward")
        self.assertNotEqual(nav.current_action(repeated)["id"], action)
        self.assertEqual(repeated["improve_results"], records)

    def test_improve_record_for_an_unrecorded_action_is_refused(self):
        state, _ = walk(self.new())
        nav.validate(state)
        broken = copy.deepcopy(state)
        broken["improve_results"]["nav-" + "0" * 32] = receipt("spec")
        with self.assertRaisesRegex(nav.NavigatorError, "must belong to completed steps"):
            nav.validate(broken)

    def test_forged_improve_child_at_a_non_checkpoint_stage_is_refused(self):
        # apply() never parks a child here; a saved run that has one was forged.
        items = [{"id": "W1", "title": "First"}, {"id": "W2", "title": "Second"}]
        for target in ("implement", "carry-forward"):
            with self.subTest(stage=target):
                state = advance_to(self.new(), "plan")
                state = nav.finish_improve(
                    nav.apply(state, nav.current_action(state)["id"], dict(DONE, work_items=items)),
                    nav.current_action(state)["id"], receipt("plan"))
                state = advance_to(state, target)
                action = nav.current_action(state)["id"]
                nav.validate(state)
                forged = copy.deepcopy(state)
                forged["active_improve"] = {
                    "action_id": action, "stage": target,
                    "binding_id": state["run_id"] + "/" + action,
                    "workspace": state["repo"], "seed_result": dict(DONE, evidence_refs=[]),
                    "skill": None,
                }
                # W1's carry-forward leaves W2 pending, so it is not the end review.
                with self.assertRaisesRegex(
                        nav.NavigatorError,
                        "Improve child is at " + target + ", a stage that never starts an "
                        "Improve child"):
                    nav.validate(forged)

    def test_improve_record_at_a_non_planning_step_is_refused(self):
        state, _ = walk(self.new())
        action = next(e["action"] for e in state["history"] if e["stage"] == "implement")
        broken = copy.deepcopy(state)
        broken["improve_results"][action] = receipt("implement")
        with self.assertRaisesRegex(
                nav.NavigatorError,
                "Improve result " + action + " is at implement, a stage that never starts"):
            nav.validate(broken)

    def test_saved_improve_cadence_key_is_refused_with_a_named_error(self):
        # Runs saved by 0.21/0.22 carry this key; the generic key check names it.
        state = nav.new_state("/simulation-only/repo", "Schedule fixture.")
        with self.assertRaises(nav.NavigatorError) as caught:
            nav.validate(dict(state, improve_cadence="planning-and-end"))
        message = str(caught.exception)
        self.assertIn("unexpected: improve_cadence", message)
        self.assertIn("saved by an older ShipLoop", message)
        self.assertIn("fresh --run-dir", message)
        # The same generic check names a missing required key.
        for key in ("inner_loops", "planning_reconciliations"):
            with self.subTest(missing=key):
                missing = dict(state)
                del missing[key]
                with self.assertRaises(nav.NavigatorError) as caught:
                    nav.validate(missing)
                self.assertIn("missing: " + key, str(caught.exception))
                self.assertIn("fresh --run-dir", str(caught.exception))

    def test_leading_line_binds_an_unbound_child_and_is_absent_when_stopped(self):
        run = Path("/simulation-only/run")
        state = advance_to(self.new(), "spec")
        action = nav.current_action(state)["id"]
        waiting = nav.apply(state, action, DONE)
        self.assertIsNone(waiting["active_improve"]["skill"])
        packet = nav.render(None, run, waiting)
        lead = after_header(packet)
        self.assertTrue(lead.startswith("Next command (bind the selected Improve card"), lead)
        lines = packet.splitlines()
        body = lines[lines.index("Bind that selected card using this command "
                                 "(replace the placeholder only if needed):") + 1]
        self.assertIn(" improve-bind ", body)
        self.assertTrue(lead.endswith(": " + body), (lead, body))
        self.assertIn("/absolute/path/to/selected/improve/SKILL.md", lead)
        # PROGRESS_REPORTING tells the host to run the packet's pause command,
        # so the unbound packet prints it.
        self.assertIn("Pause parent without losing child: "
                      + nav._callback(None, run, "pause", reason="reason"), lines)

        done, _ = walk(self.new())
        fresh = self.new()
        stopped = {
            "paused": nav.control(fresh, "pause", "Synthetic pause."),
            "paused-child": nav.control(waiting, "pause", "Synthetic pause with a parked child."),
            "blocked": nav.apply(fresh, nav.current_action(fresh)["id"],
                                 dict(DONE, outcome="blocked", blocked_by="external", summary="Synthetic block.")),
            "halted": nav.control(self.new(), "halt", "Synthetic stop."),
            "done": done,
        }
        for label, stopped_state in stopped.items():
            with self.subTest(status=label):
                packet = nav.render(None, run, stopped_state)
                for callback in ("Callback for this stage", "Next command (bind",
                                 "Callback for this Improve child"):
                    self.assertNotIn(callback, packet)


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
                                        "got 3; leave earlier material reviews on disk"):
                standalone._receipt({"summary": "s", "review_refs": refs, "check_refs": [refs[0]]},
                                    workspace, "receipt")


if __name__ == "__main__":
    unittest.main()
