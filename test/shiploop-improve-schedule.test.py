#!/usr/bin/env python3
"""Pin when Improve runs: every planning result plus one end-of-work review."""
import copy
import os
from pathlib import Path
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
        # A bound inline child that has not started leads with improve-start; the
        # improve-complete callback follows in the body.
        self.assertIn("improve-start", packet.splitlines()[1])
        self.assertIn("improve-complete", packet)
        self.assertIn("Planning review focus", packet)
        self.assertIn("self-passes by this same executor, not independent reviewers", packet)
        self.assertNotIn("Capture separate durable review files", packet)
        text = " ".join(packet.split())
        # P12: the child writes review-<n>.md per pass; improve-complete picks the passes itself.
        self.assertIn("improve-complete imports the last two passes", text)
        self.assertIn("review-<n>.md", text)
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
                        "Improve child is at " + target + ", a stage that does not start an "
                        r"Improve child in this run \(planning_review: stage\)"):
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


def render_walk(state, run, *, plan_items=None, limit=300):
    """Drive the pure navigator to done, rendering every packet on the way; return the stages that started a child."""
    reviewed = []
    for _ in range(limit):
        if state["status"] == "done":
            return state, reviewed
        packet = nav.render(None, run, state)
        assert "Call this when done:" in packet or state["active_improve"] is not None, packet
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
STAGE_CHILDREN = [("spec", None), ("test-strategy", None), ("plan", None), ("step-plan", "W1"),
                  ("test-spec", "W1"), ("step-plan", "W2"), ("test-spec", "W2"), ("carry-forward", "W2"),
                  ("system-test-author", None), ("release-plan", None)]
NONE_CHILDREN = [("carry-forward", "W2"), ("system-test-author", None), ("release-plan", None)]
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
                    "workspace": state["repo"], "seed_result": dict(DONE, evidence_refs=[]), "skill": None}
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
        self.assertIn("Improve: no Improve child starts after this result in this run (planning_review: none)",
                      packet)
        # the same producer packet in stage mode still promises the child and carries the experiment locators
        staged = nav.render(None, run, advance_to(self.new("stage"), "plan"))
        for present in ("Planning experiments guide", "Planning investigation notebook",
                        "its Improve child evaluates", "starts this action's Improve child"):
            self.assertIn(present, staged)


class PlanningReviewNoneCliTests(unittest.TestCase):
    """`--planning-review none` through the shipped CLI: the gates a host meets, not the pure functions."""

    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory(prefix="shiploop-planning-review-none-")
        self.addCleanup(self._temporary.cleanup)
        self.base = Path(self._temporary.name).resolve()
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CONFIG_NOSYSTEM="1")

    def cli(self, *argv, status=0):
        done = subprocess.run([sys.executable, "-B", str(CLI), *map(str, argv)], cwd=self.base, env=self.env,
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, status, done.stdout + done.stderr)
        return done

    def start(self, mode):
        """A fresh repository and run recorded with ``mode``; returns the run directory."""
        self.repo = self.base / ("repo-" + mode)
        self.repo.mkdir()
        (self.repo / "a.txt").write_text("x\n")
        for argv in (["init", "-q"], ["add", "."],
                     ["-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-qm", "init"]):
            subprocess.run(["git", *argv], cwd=self.repo, env=self.env, check=True)
        run = self.base / ("run-" + mode)
        # A none run starts no child that would bind the card, so it names the card at its start.
        card = ("--improve-skill", CARD) if mode == "none" else ()
        self.cli("init", "--repo", self.repo, "--run-dir", run, "--prompt=add hello", "--planning-review", mode, *card)
        return run

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
        self.assertIn("reconciliation requires the bound active initial plan Improve child",
                      refused.stdout + refused.stderr)
        self.complete(run, assumptions=[])
        state = self.saved(run)
        self.assertEqual(state["stage"], "prepare")
        self.assertIsNone(state.get("active_improve"))
        bind = self.cli("improve-bind", "--run-dir", run, "--action", action, "--skill-card", CARD, status=2)
        self.assertIn("no matching active Improve parent", bind.stdout + bind.stderr)

    def test_a_child_forged_at_spec_in_a_none_run_is_refused_when_the_run_loads(self):
        run = self.start("none")
        action = self.advance_to(run, "spec")
        saved = self.saved(run)
        saved["active_improve"] = {
            "action_id": action, "stage": "spec", "binding_id": saved["run_id"] + "/" + action,
            "workspace": saved["repo"], "seed_result": dict(DONE, evidence_refs=[]), "skill": None}
        store.write_record(run / "state.md", saved, title="Saved ShipLoop state")
        before = (run / "state.md").read_bytes()
        refused = self.cli("next", "--run-dir", run, status=2)
        self.assertIn("a stage that does not start an Improve child in this run (planning_review: none)",
                      refused.stdout + refused.stderr)
        self.assertNotIn("Traceback", refused.stdout + refused.stderr)
        self.assertEqual((run / "state.md").read_bytes(), before)

    NEEDS_CARD = "--planning-review none needs --improve-skill"

    def test_a_none_run_must_name_its_card_at_init_because_no_planning_child_binds_it(self):
        """F1: the quality and test loops read the recorded card at the first item, and under none the first child
        (the one that binds it) is the last item's carry-forward: a run started without the card would block at its
        first static-checks. The refusal leaves the run directory empty."""
        repo = self.repository("repo-nocard")
        run = self.base / "run-nocard"
        refused = self.cli("init", "--repo", repo, "--run-dir", run, "--prompt=add hello",
                           "--planning-review", "none", status=2)
        self.assertIn(self.NEEDS_CARD + "=", refused.stdout + refused.stderr)
        self.assertIn("quality and test loops", " ".join((refused.stdout + refused.stderr).split()))
        self.assertFalse((run / "state.md").exists())
        missing = self.cli("init", "--repo", repo, "--run-dir", run, "--prompt=add hello", "--planning-review", "none",
                           "--improve-skill", self.base / "no-such-card" / "SKILL.md", status=2)
        self.assertIn("the selected Improve card cannot be resolved", missing.stdout + missing.stderr)
        self.assertFalse((run / "state.md").exists())
        # the card is optional where a planning child binds it
        stage_run = self.base / "run-stage-nocard"
        self.cli("init", "--repo", repo, "--run-dir", stage_run, "--prompt=add hello", "--planning-review", "stage")
        self.assertEqual(self.saved(stage_run)["improve_skill"], "")

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
