#!/usr/bin/env python3
"""Pin when Improve runs: every planning result plus one end-of-work review."""
import copy
import os
from pathlib import Path
import shlex
import shutil
import subprocess
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
from shiploop_packet_view import assert_top_block  # noqa: E402

DONE = {"outcome": "done", "summary": "Synthetic declaration; no work executed."}
SERVICE_WAIT = {"kind": "service", "service": "the synthetic upstream", "check": "curl -fsS https://upstream.example.test/health",
                "no_default": "Nothing else can proceed until it answers."}


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


def full_packet(head):
    """The complete packet: the file a ``Full packet:`` pointer names, else the head itself (a short packet is whole)."""
    row = next((r for r in head.splitlines() if r.startswith("Full packet: ")), None)
    return Path(row.removeprefix("Full packet: ").split(" - ", 1)[0]).read_text(encoding="utf-8") if row else head


class ImproveScheduleTests(unittest.TestCase):
    def new(self):
        return nav.new_state("/simulation-only/repo", "Schedule fixture.",
                             improve_skill="")

    def test_planning_stages_and_the_end_start_improve(self):
        items = [{"id": "W1", "title": "First"}, {"id": "W2", "title": "Second"}]
        state, reviewed = walk(self.new(), plan_items=items)
        self.assertEqual(reviewed, [
            ("spec", None), ("test-strategy", None), ("plan", None),
            ("step-plan", "W1"), ("test-spec", "W1"), ("implement", "W1"),
            ("implement", "W2"), ("carry-forward", "W2"),
            ("system-test-author", None), ("release-plan", None),
        ])  # W2's step-plan and test-spec follow W1's reviewed pattern (rule first-item, owner 2026-10-19)
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
        view = assert_top_block(self, lines)
        self.assertEqual(view.index("header"), 0)  # nothing precedes the first line of an outer stage's packet
        self.assertTrue(view["header"].startswith("ShipLoop navigator | intake"), view["header"])
        callback = view["callback"]
        self.assertTrue(callback.startswith("Callback for this stage"), callback)
        self.assertIn(" complete ", callback)
        self.assertIn(nav.current_action(state)["id"], callback)
        # A stage with no Improve child says nothing about Improve (owner rule 2026-10-10) and prints an empty line
        # in the Improve line's place.  How to report a stop has one home, the outcome shapes (2026-10-11 dedupe):
        # the trailing "If work cannot continue, submit outcome 'blocked'..." sentence is gone from the Improve line.
        text = "\n".join(lines)
        self.assertNotIn("advances directly", text)
        self.assertNotIn("If work cannot continue, submit outcome 'blocked'", text)
        self.assertFalse([line for line in lines if line.startswith("Improve:")])
        self.assertIn("Allowed outcomes: done | blocked.", text)
        self.assertIn('blocked (only a person or an outside service can unblock it): {"outcome": "blocked", '
                      '"summary": "<what stopped the work>", "awaiting": {...}}', text)

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
                state, action, "spec", child["seed_result"], standalone.resolve_skill(str(CARD)),
                improve_action=child["improve_action"])
            # ShipLoop starts the review at the transition; a synthetic state stands in for that start with a receipt.
            receipt_file = standalone.receipt_path(state["active_improve"])
            receipt_file.parent.mkdir(parents=True, exist_ok=True)
            receipt_file.write_text("{}", encoding="utf-8")
            packet = nav.render(None, run, state)
            handoff = nav.improve_handoff_text(None, run, state)
            handoff_path = nav.improve_handoff_path(state["active_improve"])
            improve = nav.improve_id(state)
        # The packet is two instructions (2026-10-11 re-cut): the improve skill on the handoff file, then the Improve
        # stage's complete (it is its own stage with its own id since 2026-10-11).
        lines = packet.splitlines()
        self.assertTrue(lines[0].startswith("ShipLoop navigator | improve | revision "), lines[0])
        self.assertIn("       " + nav.IMPROVE_ARGUMENT_PREFIX + str(handoff_path), lines)
        callback = assert_top_block(self, lines)["callback"]
        self.assertTrue(callback.startswith("2. When the improve skill has completed, run:"), callback)
        self.assertIn(" complete ", callback)
        self.assertIn("--action=" + improve, callback)
        self.assertNotEqual(improve, action)
        self.assertNotIn("improve-start", packet)
        self.assertNotIn("improve-complete", packet)
        self.assertNotIn("Planning review focus", packet)
        # The child is already started: the handoff does not ask the model to write an opening or start it.
        self.assertIn("ShipLoop started this review", handoff)
        self.assertIn("Do not write the opening or start the runtime yourself", handoff)
        self.assertIn("improve-start", handoff)  # only the stopped-child restart route, --restart-stopped
        self.assertIn("--restart-stopped", handoff)
        self.assertNotIn("improve-complete", handoff)
        self.assertNotIn("--opening", handoff)
        self.assertIn("Planning review focus", handoff)
        self.assertIn("self-passes by this same executor, not independent reviewers", handoff)
        self.assertNotIn("independent broader review", handoff)  # one text never calls the same review both
        # LOST OBLIGATION (re-cut 2026-10-11): the goal and done-when list the review judges the result against were
        # only in the old Improve packet's head; neither the new packet nor the handoff file states them.
        self.assertIn("Reviewing the returned spec result. Goal:", handoff)
        self.assertIn("- every request outcome maps to at least one acceptance criterion", handoff)
        self.assertNotIn("Capture separate durable review files", handoff)
        text = " ".join(handoff.split())
        # P12: the child writes review-<n>.md per pass; the complete command picks the passes itself.
        self.assertIn("The complete command imports the last two passes", text)
        self.assertIn("review-<n>.md", text)
        self.assertNotIn("review_refs length is exactly 2", text)

    def test_unsuccessful_last_carry_forward_advances_without_improve(self):
        state = advance_to(self.new(), "carry-forward")
        self.assertEqual(len(state["work_items"]), 1)
        action = nav.current_action(state)["id"]
        records = copy.deepcopy(state["improve_results"])
        blocked = nav.apply(state, action, dict(DONE, outcome="blocked", awaiting=SERVICE_WAIT, summary="Synthetic block."))
        self.assertIsNone(blocked["active_improve"])
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["improve_results"], records)
        # repeat is retired at every stage: carry-forward's Until Loop repeats the work itself.
        with self.assertRaisesRegex(nav.NavigatorError, "must be one of done, blocked at carry-forward .*repeat are retired"):
            nav.apply(state, action, dict(DONE, outcome="repeat", summary="Synthetic retry."))

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
        for target in ("verify", "carry-forward"):
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
                    "skill": None, "improve_action": "nav-" + "1" * 32,
                }
                # W1's carry-forward leaves W2 pending, so it is not the end review.
                with self.assertRaisesRegex(
                        nav.NavigatorError,
                        "Improve child is at " + target + ", a stage that does not start an "
                        r"Improve child in this run \(planning_review: stage\)"):
                    nav.validate(forged)

    def test_improve_record_at_a_non_planning_step_is_refused(self):
        state, _ = walk(self.new())
        action = next(e["action"] for e in state["history"] if e["stage"] == "verify")
        broken = copy.deepcopy(state)
        broken["improve_results"][action] = receipt("verify")
        with self.assertRaisesRegex(
                nav.NavigatorError,
                "Improve result " + action + " is at verify, a stage that never starts"):
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
        lead = assert_top_block(self, packet)["callback"]
        # The packet is two instructions (2026-10-11 re-cut): an unbound child prints the bind command, then `next`.
        self.assertTrue(lead.startswith("No Improve card is recorded for this run. Next command (bind the Improve "
                        "skill's SKILL.md"), lead)
        self.assertIn("Then run the recovery command for the Improve instruction: "
                      + nav._callback(None, run, "next"), packet.splitlines())
        # Batch 1009 B1a: no card is recorded in this state, so the packet prints a marked blank, never a
        # path-shaped template a host could run as if it were real.
        self.assertNotIn("/absolute/path/to", packet)
        self.assertIn(" improve-bind ", lead)
        self.assertIn(shlex.quote("--skill-card=" + nav.IMPROVE_CARD_BLANK), lead)
        # Where ShipLoop looks, and the pause route, moved to the handoff file ShipLoop writes for the child.
        handoff = nav.improve_handoff_text(None, run, waiting)
        lines = handoff.splitlines()
        body = lines[next(i for i, line in enumerate(lines) if line.startswith("No Improve card is recorded for this run.")) + 1]
        self.assertIn(" improve-bind ", body)
        self.assertEqual(body, nav._callback(None, run, "improve-bind", action=nav.improve_id(waiting),
                                             **{"skill-card": nav.IMPROVE_CARD_BLANK}))
        self.assertIn(str(nav.guidance.installed_improve_card()), handoff)
        self.assertIn("Pause parent without losing child: "
                      + nav._callback(None, run, "pause", reason="reason"), lines)

        done, _ = walk(self.new())
        fresh = self.new()
        stopped = {
            "paused": nav.control(fresh, "pause", "Synthetic pause."),
            "paused-child": nav.control(waiting, "pause", "Synthetic pause with a parked child."),
            "blocked": nav.apply(fresh, nav.current_action(fresh)["id"],
                                 dict(DONE, outcome="blocked", awaiting=SERVICE_WAIT, summary="Synthetic block.")),
            "halted": nav.control(self.new(), "halt", "Synthetic stop."),
            "done": done,
        }
        for label, stopped_state in stopped.items():
            with self.subTest(status=label):
                packet = nav.render(None, run, stopped_state)
                for callback in ("Callback for this stage", "Next command (bind",
                                 "Callback for this Improve child"):
                    self.assertNotIn(callback, packet)

    def test_a_recorded_card_is_the_value_the_packet_prints_and_its_body_line_names_no_origin(self):
        """The recorded value may have come from `--improve-skill`, from `init`'s installed-card lookup or from an earlier
        `improve-bind`, so the line says only that the card is the recorded one."""
        run = Path("/simulation-only/run")
        recorded = advance_to(nav.new_state("/simulation-only/repo", "Schedule fixture.", improve_skill=str(CARD)), "spec")
        waiting = nav.apply(recorded, nav.current_action(recorded)["id"], DONE)
        packet = nav.render(None, run, waiting)
        lead = assert_top_block(self, packet)["callback"]
        self.assertTrue(lead.startswith("Next command (bind the Improve skill's SKILL.md"), lead)
        self.assertIn("--skill-card=" + str(CARD), lead)
        handoff = nav.improve_handoff_text(None, run, waiting)
        lines = handoff.splitlines()
        said = next(i for i, line in enumerate(lines) if line.startswith("Bind the Improve card recorded for this run"))
        body = lines[said + 1]
        self.assertTrue(lead.endswith(": " + body), (lead, body))
        for origin in ("--improve-skill", "installed beside"):
            self.assertNotIn(origin, lines[said])
        self.assertNotIn("No Improve card is recorded", packet + handoff)
        self.assertNotIn(nav.IMPROVE_CARD_BLANK, packet + handoff)

def render_walk(state, run, *, plan_items=None, limit=300):
    """Drive the pure navigator to done, rendering every packet on the way; return the stages that started a child."""
    reviewed = []
    for _ in range(limit):
        if state["status"] == "done":
            return state, reviewed
        packet = nav.render(None, run, state)
        assert "Callback for this stage (run once after its work" in packet or state["active_improve"] is not None, packet
        assert "Call this when done:" not in packet, packet
        stage, action = nav.current_stage(state), nav.current_action(state)["id"]
        result = dict(DONE, work_items=plan_items) if stage == "plan" and plan_items else DONE
        state = nav.apply(state, action, result)
        if state["active_improve"] is not None:
            reviewed.append(stage)
            nav.render(None, run, state)
            state = nav.finish_improve(state, action, receipt(stage))
    raise AssertionError("render_walk did not finish")


ITEMS = [{"id": "W1", "title": "First"}, {"id": "W2", "title": "Second"}]
# The validator's refusal of a missing planning record names the option that decides which records exist.
SCHEDULED_RECORDS = r"every planning-stage result this run's planning_review option reviews"
# Declared here, independently of stage_spec: the children a two-item run starts, by planning_review.
# implement's per-step Improve runs in both modes (owner decisions 5 and 6, 2026-10-10).
# step-plan and test-spec are reviewed for the first item only (rule first-item, owner 2026-10-19, chess run 3).
STAGE_CHILDREN = [("spec", None), ("test-strategy", None), ("plan", None), ("step-plan", "W1"),
                  ("test-spec", "W1"), ("implement", "W1"),
                  ("implement", "W2"), ("carry-forward", "W2"), ("system-test-author", None), ("release-plan", None)]
NONE_CHILDREN = [("implement", "W1"), ("implement", "W2"), ("carry-forward", "W2"), ("system-test-author", None),
                 ("release-plan", None)]
PLANNING_CHOICE = ("spec", "test-strategy", "plan", "step-plan", "test-spec")


class PlanningReviewScheduleTests(unittest.TestCase):
    """The run option `planning_review` decides which planning results start an Improve child.

    Pure navigator first (the schedule, the validator's required records, the forged-child refusal), then the
    shipped CLI for what only the real gates show: the load-time refusal, the knowledge commit, the missing bind
    and reconcile routes.
    """

    def new(self, mode, **extra):
        return nav.new_state("/simulation-only/repo", "Schedule fixture.", improve_skill="",
                             planning_review=mode, **extra)

    def test_a_two_item_walk_starts_the_children_the_mode_names(self):
        for mode, expected in (("stage", STAGE_CHILDREN), ("none", NONE_CHILDREN)):
            with self.subTest(mode=mode):
                state, reviewed = walk(self.new(mode), plan_items=ITEMS)
                self.assertEqual(reviewed, expected)
                self.assertEqual(state["status"], "done")
                nav.validate(state)
                recorded = {entry["stage"] for entry in state["history"]
                            if entry["action"] in state["improve_results"]}
                self.assertEqual(recorded, {stage for stage, _ in expected})

    def test_none_leaves_no_child_in_the_planning_window_and_the_end_review_still_moves_to_the_last_item(self):
        state = self.new("none")
        for stage in ("intake", "discovery", "research", *PLANNING_CHOICE[:3], "prepare"):
            self.assertEqual(nav.current_stage(state), stage)
            state = nav.apply(state, nav.current_action(state)["id"], DONE)
            self.assertIsNone(state["active_improve"], stage)
        self.assertEqual(state["improve_results"], {})
        # an end review that adds work still moves to the new last item's carry-forward
        added = dict(DONE, work_items=[{"id": "W2", "title": "Found by the end review"}])
        _, reviewed = walk(self.new("none"), end_final=[added])
        self.assertEqual([entry for entry in reviewed if entry[0] == "carry-forward"],
                         [("carry-forward", "W1"), ("carry-forward", "W2")])

    def test_the_validator_requires_the_records_the_mode_reviews(self):
        state, _ = walk(self.new("none"), plan_items=ITEMS)
        nav.validate(state)  # no planning record at the five choice stages is valid
        for stage in ("system-test-author", "release-plan"):
            with self.subTest(stage=stage):
                action = next(e["action"] for e in state["history"] if e["stage"] == stage)
                broken = dict(state, improve_results={
                    k: v for k, v in state["improve_results"].items() if k != action})
                with self.assertRaisesRegex(nav.NavigatorError, SCHEDULED_RECORDS):
                    nav.validate(broken)
        stage_state, _ = walk(self.new("stage"), plan_items=ITEMS)
        action = next(e["action"] for e in stage_state["history"] if e["stage"] == "spec")
        with self.assertRaisesRegex(nav.NavigatorError, SCHEDULED_RECORDS):
            nav.validate(dict(stage_state, improve_results={
                k: v for k, v in stage_state["improve_results"].items() if k != action}))

    def test_a_child_forged_at_a_planning_stage_is_refused_only_where_the_mode_starts_none(self):
        for mode, refused in (("stage", False), ("none", True)):
            with self.subTest(mode=mode):
                state = advance_to(self.new(mode), "spec")
                action = nav.current_action(state)["id"]
                forged = copy.deepcopy(state)
                forged["active_improve"] = {
                    "action_id": action, "stage": "spec", "binding_id": state["run_id"] + "/" + action,
                    "workspace": state["repo"], "seed_result": dict(DONE, evidence_refs=[]), "skill": None,
                    "improve_action": "nav-" + "1" * 32}
                if refused:
                    with self.assertRaisesRegex(
                            nav.NavigatorError,
                            "Improve child is at spec, a stage that does not start an Improve child in "
                            r"this run \(planning_review: none\)"):
                        nav.validate(forged)
                else:
                    nav.validate(forged)

    def test_the_assumption_list_is_still_checked_at_plan_in_every_mode(self):
        """GUARD for stage (passes on the unchanged code); none gets the same gate, not a lighter one."""
        open_entry = dict(DONE, assumptions=[{
            "id": "A1", "assumption": "A server seam exists.", "disposition": "open",
            "check": "import it", "reason": "not run", "consumer": "W9"}])
        for mode in ("stage", "none"):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(nav.NavigatorError, "W9"):
                    nav._check_submitted_assumptions(self.new(mode), "plan", open_entry)

    def test_every_backchain_passes_value_renders_and_walks_in_every_mode(self):
        run = Path("/simulation-only/run")
        for passes in nav.BACKCHAIN_PASSES_MODES:
            for mode, expected in (("stage", [c[0] for c in STAGE_CHILDREN]), ("none", [c[0] for c in NONE_CHILDREN])):
                with self.subTest(backchain_passes=passes, planning_review=mode):
                    state, reviewed = render_walk(self.new(mode, backchain_passes=passes), run, plan_items=ITEMS)
                    self.assertEqual(reviewed, expected)

    def test_the_plan_packet_names_no_review_the_run_does_not_have(self):
        run = Path("/simulation-only/run")
        plan = advance_to(self.new("none"), "plan")
        packet = nav.render(None, run, plan)
        for absent in ("improve-reconcile", "Planning experiments guide", "Planning investigation notebook",
                       "its Improve child evaluates", "mandatory actual Improve handoff",
                       "starts this action's Improve child", "Proposed queue awaiting Improve"):
            self.assertNotIn(absent, packet)
        # A producer packet no longer announces its Improve child at all (re-cut 2026-10-11, item 2); the none-mode
        # sentence is gone with it, and the stage-mode promise below is gone too.
        self.assertNotIn("Improve: ", packet)
        # In stage mode the producer packet is just as silent; the experiment locators and the review live in the
        # child's handoff file, which exists only for the planning_review modes that start a child.
        staged = advance_to(self.new("stage"), "plan")
        self.assertNotIn("Planning experiments guide", nav.render(None, run, staged))
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp).resolve() / "repo"
            repo.mkdir()
            state = nav.new_state(str(repo), "Schedule fixture.", improve_skill="", planning_review="stage")
            state = advance_to(state, "plan")
            action = nav.current_action(state)["id"]
            state = nav.apply(state, action, DONE)
            state["active_improve"] = standalone.binding(
                state, action, "plan", state["active_improve"]["seed_result"], standalone.resolve_skill(str(CARD)),
                improve_action=state["active_improve"]["improve_action"])
            handoff = nav.improve_handoff_text(None, Path(temp).resolve() / "run", state)
        for present in ("Planning experiments guide", "Planning investigation notebook"):
            self.assertIn(present, handoff)


class CliRunCase(unittest.TestCase):
    """A temporary repository, run directories and the shipped CLI, with the machine's Git configuration ignored."""

    cli_path = CLI

    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory(prefix="shiploop-improve-schedule-cli-")
        self.addCleanup(self._temporary.cleanup)
        self.base = Path(self._temporary.name).resolve()
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CONFIG_NOSYSTEM="1")

    def run_argv(self, argv, status=0):
        done = subprocess.run(argv, cwd=self.base, env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, status, done.stdout + done.stderr)
        return done

    def cli(self, *argv, status=0):
        return self.run_argv([sys.executable, "-B", str(self.cli_path), *map(str, argv)], status)

    def repository(self, name):
        repo = self.base / name
        repo.mkdir()
        (repo / "a.txt").write_text("x\n")
        for argv in (["init", "-q"], ["add", "."],
                     ["-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-qm", "init"]):
            subprocess.run(["git", *argv], cwd=repo, env=self.env, check=True)
        return repo

    @staticmethod
    def saved(run):
        return store.read_record(run / "state.md")

    def complete(self, run, **result):
        action = self.saved(run)["action"]["id"]
        path = run / "inbox" / (action + ".md")
        store.write_record(path, dict(DONE, **result))
        return self.cli("complete", "--run-dir", run, "--action", action, "--result", path)

    def advance_to(self, run, stage, limit=60):
        for _ in range(limit):  # a regression in the schedule fails here in seconds, not at the suite's time limit
            if self.saved(run)["stage"] == stage:
                return self.saved(run)["action"]["id"]
            self.complete(run)
        raise AssertionError("did not reach " + stage + "; stuck at " + self.saved(run)["stage"])


class PlanningReviewNoneCliTests(CliRunCase):
    """`--planning-review none` through the shipped CLI: the gates a host meets, not the pure functions."""

    def start(self, mode):
        """A fresh repository and run recorded with ``mode``; returns the run directory."""
        self.repo = self.repository("repo-" + mode)
        run = self.base / ("run-" + mode)
        # A none run starts no child that would bind the card, so it names the card at its start.
        card = ("--improve-skill", CARD) if mode == "none" else ()
        self.cli("init", "--repo", self.repo, "--run-dir", run, "--prompt=add hello", "--planning-review", mode, *card)
        return run

    def knowledge_commits(self):
        subjects = subprocess.run(["git", "-C", str(self.repo), "log", "--format=%s"], env=self.env, check=True,
                                  capture_output=True, text=True).stdout.splitlines()
        return [line for line in subjects if "knowledge after spec" in line]

    def test_the_spec_is_accepted_and_committed_at_complete_with_no_review(self):
        """S-11 under none: the knowledge home is committed when the spec is accepted; under stage a child holds it."""
        commits = {}
        for mode in ("stage", "none"):
            run = self.start(mode)
            self.advance_to(run, "spec")
            spec = self.repo / "docs" / "shiploop" / "spec.md"
            spec.parent.mkdir(parents=True)
            spec.write_text("# spec\n\nR-1: Say hello.\n")
            self.complete(run)
            state = self.saved(run)
            if mode == "none":
                self.assertEqual(state["stage"], "test-strategy")
                self.assertIsNone(state.get("active_improve"))
                self.assertEqual(state["improve_results"], {})
            else:
                self.assertEqual(state["stage"], "spec")
                self.assertIsNotNone(state["active_improve"])
            commits[mode] = self.knowledge_commits()
        self.assertEqual(commits["stage"], [])
        self.assertEqual(len(commits["none"]), 1, commits)

    def test_a_none_run_has_no_child_to_bind_and_nothing_to_reconcile(self):
        run = self.start("none")
        self.advance_to(run, "plan")
        action = self.saved(run)["action"]["id"]
        result = run / "inbox" / (action + "-reconcile.md")
        store.write_record(result, {"summary": "Reconcile.", "target": "research", "evidence_refs": []})
        refused = self.cli("improve-reconcile", "--run-dir", run, "--action", action, "--result", result,
                           status=2)
        # A none run has no Improve stage, so no action id names one (an Improve stage is the only thing these verbs accept).
        self.assertIn("is not this run's Improve stage", refused.stdout + refused.stderr)
        self.complete(run, assumptions=[])
        state = self.saved(run)
        self.assertEqual(state["stage"], "prepare")
        self.assertIsNone(state.get("active_improve"))
        bind = self.cli("improve-bind", "--run-dir", run, "--action", action, "--skill-card", CARD, status=2)
        self.assertIn("is not this run's Improve stage", bind.stdout + bind.stderr)

    def test_a_child_forged_at_spec_in_a_none_run_is_refused_when_the_run_loads(self):
        run = self.start("none")
        action = self.advance_to(run, "spec")
        saved = self.saved(run)
        saved["active_improve"] = {
            "action_id": action, "stage": "spec", "binding_id": saved["run_id"] + "/" + action,
            "workspace": saved["repo"], "seed_result": dict(DONE, evidence_refs=[]), "skill": None,
            "improve_action": "nav-" + "1" * 32}
        store.write_record(run / "state.md", saved, title="Saved ShipLoop state")
        before = (run / "state.md").read_bytes()
        refused = self.cli("next", "--run-dir", run, status=2)
        self.assertIn("a stage that does not start an Improve child in this run (planning_review: none)",
                      refused.stdout + refused.stderr)
        self.assertNotIn("Traceback", refused.stdout + refused.stderr)
        self.assertEqual((run / "state.md").read_bytes(), before)

    NEEDS_CARD = "--planning-review none needs --improve-skill"

    def test_a_none_run_must_name_its_card_at_init_because_no_planning_child_binds_it(self):
        """F1: the stage Until Loops read the recorded card at the first item, and under none the first child
        (the one that binds it) is the last item's carry-forward: a run started without the card would block at its
        first inner stage. The refusal leaves the run directory empty."""
        repo = self.repository("repo-nocard")
        run = self.base / "run-nocard"
        refused = self.cli("init", "--repo", repo, "--run-dir", run, "--prompt=add hello",
                           "--planning-review", "none", status=2)
        self.assertIn(self.NEEDS_CARD + "=", refused.stdout + refused.stderr)
        self.assertIn("before the first item's stage Until Loops, which read it", " ".join((refused.stdout + refused.stderr).split()))
        self.assertFalse((run / "state.md").exists())
        missing = self.cli("init", "--repo", repo, "--run-dir", run, "--prompt=add hello", "--planning-review", "none",
                           "--improve-skill", self.base / "no-such-card" / "SKILL.md", status=2)
        self.assertIn("the selected Improve card cannot be resolved", missing.stdout + missing.stderr)
        self.assertFalse((run / "state.md").exists())
        # the flag is optional where a planning child binds the card: init records the card installed beside ShipLoop
        stage_run = self.base / "run-stage-nocard"
        self.cli("init", "--repo", repo, "--run-dir", stage_run, "--prompt=add hello", "--planning-review", "stage")
        self.assertEqual(self.saved(stage_run)["improve_skill"], str(CARD))

    def test_a_none_run_started_with_its_card_records_it_and_recovers_without_repeating_it(self):
        run = self.start("none")
        self.assertEqual(self.saved(run)["improve_skill"], str(CARD))
        self.assertEqual(self.saved(run)["planning_review"], "none")
        # an identical retry is recovery: it neither needs the card again nor changes the recorded one
        self.cli("init", "--repo", self.repo, "--run-dir", run, "--prompt=add hello", "--planning-review", "none")
        self.assertEqual(self.saved(run)["improve_skill"], str(CARD))

    def test_workspace_start_refuses_a_none_run_without_its_card_before_it_creates_anything(self):
        repo = self.repository("repo-ws")
        branches = lambda: subprocess.run(["git", "-C", str(repo), "branch", "--list"], env=self.env, check=True,
                                          capture_output=True, text=True).stdout
        before = branches()
        root = self.base / "ws-none"
        refused = self.cli("workspace", "start", "--repo", repo, "--workspace-root", root, "--prompt=add hello",
                           "--planning-review", "none", status=2)
        self.assertIn(self.NEEDS_CARD + "=", refused.stdout + refused.stderr)
        self.assertFalse(root.exists(), "no workspace, worktree or run directory is created")
        self.assertEqual(branches(), before)
        self.cli("workspace", "start", "--repo", repo, "--workspace-root", root, "--prompt=add hello",
                 "--planning-review", "none", "--improve-skill", CARD)
        self.assertEqual(self.saved(root / "run")["improve_skill"], str(CARD))

    def test_the_assumption_list_is_refused_at_plan_in_a_none_run(self):
        run = self.start("none")
        self.advance_to(run, "plan")
        open_entry = [{"id": "A1", "assumption": "A server seam exists.", "disposition": "open",
                       "check": "import it", "reason": "not run", "consumer": "W9"}]
        action = self.saved(run)["action"]["id"]
        path = run / "inbox" / (action + ".md")
        store.write_record(path, dict(DONE, assumptions=open_entry))
        refused = self.cli("complete", "--run-dir", run, "--action", action, "--result", path, status=2)
        self.assertIn("W9", refused.stdout + refused.stderr)
        self.assertEqual(self.saved(run)["stage"], "plan")


class InstalledCardCliTests(CliRunCase):
    """Batch 1009 B1a: `init` records the Improve card installed beside ShipLoop, so the first bind prints a real path.

    Both round-1 Sonnet runs assembled the path by hand (`IMP=.../skills/improve/SKILL.md; ls $IMP`) from the CLI path;
    the packet printed a template.  ShipLoop's sibling card is found by file location and validated by `resolve_skill`
    (no name or PATH search), and the ledger records it once; an explicit `--improve-skill` still wins.
    """

    def init(self, *flags, name="installed"):
        self.repo = self.repository("repo-" + name)
        run = self.base / ("run-" + name)
        self.cli("init", "--repo", self.repo, "--run-dir", run, "--prompt=add hello", *flags)
        return run

    def to_the_bind(self, run):
        """The packet the spec result's acceptance prints: the first one that binds the Improve card."""
        self.advance_to(run, "spec")
        return self.complete(run).stdout

    @staticmethod
    def printed_bind(head):
        """The bind command a head leads with, as the shell words it prints."""
        lead = next(line for line in head.splitlines() if line.startswith("No Improve card is recorded for this run. Next command (bind the Improve skill's SKILL.md"))
        return lead, shlex.split(lead.split("SKILL.md): ", 1)[1])

    def test_a_stage_run_started_without_a_card_records_the_installed_one_and_binds_it_at_the_transition(self):
        """ShipLoop binds the recorded card itself (re-cut 2026-10-11, item 3): no bind command is printed at all."""
        run = self.init()
        self.assertEqual(self.saved(run)["improve_skill"], str(CARD))
        head = self.to_the_bind(run)
        self.assertEqual(self.saved(run)["active_improve"]["skill"]["skill_card"], str(CARD))
        full = full_packet(head)
        for text in (head, full):
            self.assertNotIn("/absolute/path/to", text)
            self.assertNotIn(nav.IMPROVE_CARD_BLANK, text)
            self.assertNotIn("improve-bind", text)
        self.assertIn("       " + nav.IMPROVE_ARGUMENT_PREFIX, full)

    def test_an_explicit_improve_skill_wins_over_the_installed_card(self):
        """GUARD (passes on the unchanged tree): the flag is recorded as given, and the transition binds that card."""
        elsewhere = self.base / "elsewhere" / "improve"
        shutil.copytree(CARD.parent, elsewhere, symlinks=True)
        run = self.init("--improve-skill", elsewhere / "SKILL.md", name="explicit")
        self.assertEqual(self.saved(run)["improve_skill"], str(elsewhere / "SKILL.md"))
        self.to_the_bind(run)
        self.assertEqual(self.saved(run)["active_improve"]["skill"]["skill_card"], str(elsewhere / "SKILL.md"))

    def test_the_help_does_not_promise_a_default_that_planning_review_none_refuses(self):
        """`--improve-skill` has no default under `none`: the run is refused without it.  A help line that said
        "default: the card installed beside ShipLoop" promised what the script refuses."""
        self.env["COLUMNS"] = "1000"  # argparse wraps (and may break at a hyphen) to the terminal width
        for argv in (("init",), ("workspace", "start")):
            text = " ".join(self.cli(*argv, "--help").stdout.split())
            self.assertIn("a stage run without it records the card installed beside ShipLoop", text, argv)
            self.assertIn("required with --planning-review none", text, argv)
            self.assertNotIn("(default: the card installed beside ShipLoop)", text, argv)


class NoInstalledCardCliTests(CliRunCase):
    """Batch 1009 B1a: where no usable sibling card exists the packet says so; it never prints a path that looks real.

    A copy of the ShipLoop package alone in a temporary `skills/` directory is run through its own CLI, so the
    installed-card location the copy computes holds no Improve skill (or only part of one).
    """

    @classmethod
    def setUpClass(cls):
        cls._shared = tempfile.TemporaryDirectory(prefix="shiploop-no-installed-card-")
        cls.addClassCleanup(cls._shared.cleanup)
        cls.skills = Path(cls._shared.name).resolve() / "skills"
        shutil.copytree(PACKAGE, cls.skills / "shiploop", ignore=shutil.ignore_patterns("__pycache__"))
        cls.cli_path = cls.skills / "shiploop" / "scripts" / "shiploop"

    def init(self):
        self.repo = self.repository("repo-nocard")
        run = self.base / "run-nocard"
        self.cli("init", "--repo", self.repo, "--run-dir", run, "--prompt=add hello")
        return run

    def at_the_bind(self, run):
        self.advance_to(run, "spec")
        head = self.complete(run).stdout
        full = full_packet(head)
        return head, full

    def check_the_honest_blank(self, run):
        self.assertEqual(self.saved(run)["improve_skill"], "")
        head, full = self.at_the_bind(run)
        for text in (head, full):
            self.assertNotIn("/absolute/path/to", text)
        # The head leads with the one command; the sentence that says why its value is blank is in the full packet.
        # The re-cut round 2 packet says both in its one command line: no card is recorded, and where ShipLoop looks.
        self.assertIn("No Improve card is recorded for this run.", full)
        self.assertIn(str(self.skills / "improve" / "SKILL.md"), full)
        lead = next(line for line in head.splitlines() if line.startswith("No Improve card is recorded for this run. Next command (bind the Improve skill's SKILL.md"))
        # The marked blank is one quoted argument that the bind refuses honestly, rather than a wrong path it runs.
        refused = self.run_argv(shlex.split(lead.split("SKILL.md): ", 1)[1]), status=2)
        self.assertIn("skill card path must be absolute", refused.stdout + refused.stderr)
        # Selecting the real card, as the packet says to, binds it.
        # The command names the Improve stage's own id, never the reviewed action's.
        action = self.saved(run)["active_improve"]["improve_action"]
        self.assertIn("--action=" + action, lead)
        self.cli("improve-bind", "--run-dir", run, "--action", action, "--skill-card", CARD)
        self.assertEqual(self.saved(run)["active_improve"]["skill"]["skill_card"], str(CARD))
        # Binding leaves a bound child at the transition, so ShipLoop starts it (opening, contract and receipt).
        child = self.saved(run)["active_improve"]
        self.assertTrue(standalone.receipt_path(child).exists())
        self.assertTrue(standalone.receipt_path(child).with_name("opening.md").exists())
        return head, full

    def test_a_stage_run_starts_and_its_first_bind_says_no_card_is_recorded_instead_of_printing_a_fake_path(self):
        self.check_the_honest_blank(self.init())

    def test_a_card_that_is_present_but_unusable_is_not_called_missing(self):
        """Only the SKILL.md sits beside ShipLoop (no runtime directory): init records nothing, and the packet's sentence
        stays true by naming where ShipLoop looks and not by claiming the file is absent."""
        (self.skills / "improve").mkdir()
        self.addCleanup(shutil.rmtree, self.skills / "improve", True)
        shutil.copy(CARD, self.skills / "improve" / "SKILL.md")
        head, full = self.check_the_honest_blank(self.init())
        for text in (head, full):
            self.assertNotIn("not found", text)
            self.assertNotIn("no Improve card exists", text)


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


class FirstItemReviewTests(unittest.TestCase):
    """step-plan and test-spec are reviewed for the first work item and for an item that was sent back (rule
    first-item, owner 2026-10-19). Chess run 3 spent 99 of 236 min in Improve; the step plan's review alone took
    5-14 min on every item, although later items follow the pattern the first item's review set."""

    ITEMS = [{"id": "W1", "title": "First"}, {"id": "W2", "title": "Second"}, {"id": "W3", "title": "Third"}]

    def new(self):
        return nav.new_state("/simulation-only/repo", "Schedule fixture.", improve_skill="")

    def to(self, state, stage, item):
        """Drive with synthetic results (finishing any Improve child) until ``stage`` of ``item`` is current."""
        for _ in range(300):
            if (nav.current_stage(state), nav._current_work_item(state)) == (stage, item) \
                    and state["active_improve"] is None:
                return state
            current, action = nav.current_stage(state), nav.current_action(state)["id"]
            state = nav.apply(state, action, dict(DONE, work_items=self.ITEMS) if current == "plan" else DONE)
            if state["active_improve"] is not None:
                state = nav.finish_improve(state, action, receipt(current))
        raise AssertionError("did not reach " + stage + " of " + item)

    def test_only_the_first_items_step_plan_and_test_spec_start_a_child(self):
        state, reviewed = walk(self.new(), plan_items=self.ITEMS)
        planned = [entry for entry in reviewed if entry[0] in ("step-plan", "test-spec")]
        self.assertEqual(planned, [("step-plan", "W1"), ("test-spec", "W1")])
        self.assertEqual([entry for entry in reviewed if entry[0] == "implement"],
                         [("implement", "W1"), ("implement", "W2"), ("implement", "W3")])
        nav.validate(state)  # no Improve record is required for a later item's step plan or test spec

    def test_a_sent_back_items_redone_plan_and_spec_are_reviewed(self):
        state = self.to(self.new(), "implement", "W2")
        state = nav.apply(state, nav.current_action(state)["id"],
                          {"outcome": "send-back", "summary": "W2's step plan cannot meet a criterion."})
        self.assertEqual((nav.current_stage(state), state["active_improve"]), ("step-plan", None))
        for stage in ("step-plan", "test-spec"):
            with self.subTest(stage=stage):
                self.assertEqual(nav.current_stage(state), stage)
                action = nav.current_action(state)["id"]
                state = nav.apply(state, action, DONE)
                self.assertIsNotNone(state["active_improve"], stage + " of a sent-back item is reviewed")
                state = nav.finish_improve(state, action, receipt(stage))
        nav.validate(state)

    def test_a_later_items_done_step_plan_advances_straight_to_its_test_spec(self):
        state = self.to(self.new(), "step-plan", "W2")
        state = nav.apply(state, nav.current_action(state)["id"], DONE)
        self.assertIsNone(state["active_improve"])
        self.assertEqual((nav.current_stage(state), nav._current_work_item(state)), ("test-spec", "W2"))

    def test_a_missing_record_for_the_first_items_step_plan_is_still_refused(self):
        state, _ = walk(self.new(), plan_items=self.ITEMS)
        action = next(e["action"] for e in state["history"] if e["stage"] == "step-plan" and e["workitem"] == "W1")
        broken = dict(state, improve_results={key: value for key, value in state["improve_results"].items()
                                              if key != action})
        with self.assertRaisesRegex(nav.NavigatorError, SCHEDULED_RECORDS):
            nav.validate(broken)


if __name__ == "__main__":
    unittest.main()
