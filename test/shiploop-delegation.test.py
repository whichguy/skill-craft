#!/usr/bin/env python3
"""Run-level execution delegation: inline default for new runs, ask-agent opt-in."""

from pathlib import Path
import os
import re
import shlex
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
import shiploop_navigator_dry_run as dry_run  # noqa: E402
import shiploop_loops as loops  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_reference as reference  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_store as store  # noqa: E402


def _with_packet_file(stdout: str) -> str:
    """Append the full packet's file text when stdout only printed the head.

    An active-state ``emit()`` prints a short head with a ``Full packet:
    <path>`` line and writes the complete packet to that file; a non-active
    print (paused/blocked/halted/done) already carries the full text and has
    no such line, so it passes through unchanged.
    """
    marker = "Full packet: "
    for line in stdout.splitlines():
        if line.startswith(marker):
            packet_file = Path(line[len(marker):])
            if packet_file.is_file():
                return stdout + "\n" + packet_file.read_text(encoding="utf-8")
    return stdout

# Instructions that route work to a delegated executor.  Inline packets may
# name Ask Agent only to forbid it, so these are the positive route phrases.
OWNER = 2  # the owner rule and the index pointer sit directly under every header (2026-10-16)


def owner_lines_follow(test: unittest.TestCase, lines: list, header: int = 0) -> None:
    """The two lines under the header are the owner rule and the pointer to the run's context-index.md."""
    test.assertEqual(lines[header + 1], prompts.OWNER_RULE)
    test.assertTrue(lines[header + 2].startswith(prompts.INDEX_POINTER_PREFIX), lines[header + 2])
    test.assertTrue(lines[header + 2].endswith(prompts.INDEX_POINTER_SUFFIX), lines[header + 2])


DELEGATED_ROUTE_TEXT = (
    "Prefer a native fresh worker",
    "run the host-selected improve-agent card",
    "ask-agent/consumer-owned-workspace/v1",
    "Workspace route: consumer-owned",
    "Native owner record:",
    "bind the default parallel mode",
    "Parallel-chain guide:",
    "so the parallel chain can run them together",
    "its own step (`deps` [])",
)
# Delegated wording that only bound Improve packets or duties can carry.
BOUND_DELEGATED_TEXT = DELEGATED_ROUTE_TEXT + (
    "dispatch step",
    "every worker",
    "source-bound parent update",
    "parallel or serial execution graph",
)


def bound_walk(repo, delegation, handoffs=False, started=True):
    """Render every producer and its bound ephemeral Improve packet for one item.

    With ``handoffs`` each Improve packet is followed by a ``handoff`` entry: the file text ShipLoop writes beside the
    opening (everything the improve skill needs, re-cut 2026-10-11), since the packet itself is two instructions.
    ShipLoop binds the card and starts the child at the transition (owner, 2026-10-11); ``started`` stands in for that
    start by leaving a receipt where the runtime would have written one, without running the runtime.  Without it the
    walk renders a child ShipLoop could not start.
    """
    selected = standalone.resolve_skill(str(CARD))
    state = nav.new_state(str(repo), "Synthetic bound walk.", delegation=delegation)
    run = Path(repo).parent / ("run-" + str(delegation))
    run.mkdir()
    packets = []
    while state["status"] == "active":
        stage = nav.current_stage(state)
        action = nav.current_action(state)["id"]
        packets.append((stage, "produce", nav.render(None, run, state)))
        result = {"outcome": "done", "summary": "Synthetic " + stage + " declaration."}
        if stage == "plan":
            result["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
        state = nav.apply(state, action, result)
        child = state.get("active_improve")
        if child is not None:
            state["active_improve"] = standalone.binding(state, action, child["stage"],
                                                         child["seed_result"], selected,
                                                         improve_action=child["improve_action"])
            if started:
                receipt = standalone.receipt_path(state["active_improve"])
                receipt.parent.mkdir(parents=True, exist_ok=True)
                receipt.write_text("{}", encoding="utf-8")
            packets.append((stage, "improve", nav.render(None, run, state)))
            if handoffs:
                packets.append((stage, "handoff", nav.improve_handoff_text(None, run, state)))
            state["active_improve"] = child
            state = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
    return packets


def advance(state, target, *, stop_after_apply=False):
    """Walk synthetic producers and Improve receipts until ``target`` is current."""
    while nav.current_stage(state) != target:
        stage = nav.current_stage(state)
        action = nav.current_action(state)["id"]
        result = {"outcome": "done", "summary": "Synthetic " + stage + " declaration."}
        if stage == "plan":
            result["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
        state = nav.apply(state, action, result)
        if state.get("active_improve") is not None:
            state = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
    if stop_after_apply:
        action = nav.current_action(state)["id"]
        state = nav.apply(state, action, {"outcome": "done", "summary": "Synthetic " + target + "."})
    return state


class DelegationStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-delegation-")
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / "run"
        self.run.mkdir()

    def state(self, delegation="inline"):
        return nav.new_state("/simulation-only/repo", "Synthetic delegation request.",
                             delegation=delegation)

    def render(self, state):
        return nav.render(None, self.run, state)

    def test_every_run_records_delegation_and_a_run_without_it_is_refused(self):
        default = nav.new_state("/r", "Synthetic.")
        self.assertEqual((default["delegation"], nav.delegation(default)), ("inline", "inline"))
        # A run saved before the setting existed is not routed through ask-agent.
        unrecorded = dict(default)
        del unrecorded["delegation"]
        with self.assertRaises(nav.NavigatorError) as caught:
            nav.validate(unrecorded)
        self.assertIn("navigator state has no recorded delegation", str(caught.exception))
        self.assertIn("fresh --run-dir", str(caught.exception))
        for value in ("inline", "ask-agent"):
            with self.subTest(value=value):
                state = self.state(value)
                self.assertEqual(state["delegation"], value)
                self.assertEqual(nav.delegation(state), value)

    def test_delegation_is_limited_to_known_values(self):
        for value in ("parallel", None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(nav.NavigatorError, "inline or ask-agent"):
                    self.state(value)
        bad = self.state()
        bad["delegation"] = "Inline"
        with self.assertRaisesRegex(nav.NavigatorError, "unsupported delegation"):
            nav.validate(bad)

    def test_inline_continues_in_context_at_every_stage_including_a_new_work_item(self):
        # No packet, script or hook output can clear a host conversation, so a
        # pause for a clear stopped every work item until the user came back.
        state = self.state()
        self.assertTrue(self.render(state).startswith("ShipLoop navigator | intake |"))
        state = advance(state, "step-plan")
        entry = self.render(state)
        # The preamble (two lines since the 2026-10-11 re-cut) says to do this stage here, submit its callback and never
        # clear or hand it off; it no longer names step-plan, because every stage, step-plan included, gets the same
        # line.
        self.assertTrue(entry.startswith(
            "Continue in this context and execute the prompt. Delegation: inline: do this stage here and submit its "
            "callback\nyourself; never clear or hand it off. After lost context, run the Recovery command.\n"))
        self.assertNotIn("Execute the prompt in a fresh context", entry)
        self.assertIn("Pause without consuming the action:", entry)
        # step-plan is a planning-review stage, so completing it starts an
        # actual Improve child.
        # The Improve packet is the two instructions (re-cut 2026-10-11): it opens with its own header, not a prefix.
        improve = self.render(advance(state, "step-plan", stop_after_apply=True))
        # Improve is a stage of its own (owner, 2026-10-11): its header names the stage `improve` and the result.
        self.assertTrue(improve.startswith("ShipLoop navigator | improve | revision "), improve[:80])
        self.assertTrue(improve.splitlines()[0].endswith("| the step-plan result"), improve.splitlines()[0])
        for stage in ("step-plan", "implement", "carry-forward"):
            with self.subTest(stage=stage):
                packet = self.render(advance(state, stage))
                self.assertTrue(packet.startswith("Continue in this context and execute the prompt. Delegation: inline"))
                self.assertIn("never clear or hand it off", packet.split("\n\n", 1)[0])
                self.assertNotIn("Execute the prompt in a fresh context", packet)

    def test_ask_agent_step_plan_splits_independent_changes_into_separate_steps(self):
        # Live 2026-10-04 (p1-temperature-plain): without this rule the model put two modules
        # that do not use each other into one step, so the chain had nothing to run in parallel.
        packet = self.render(advance(self.state("ask-agent"), "step-plan"))
        # Duty 11 (Execution graph) of the re-cut step-plan states the rule once.
        flat = " ".join(packet.split())
        self.assertIn("Give each change that needs no other its own step (`deps` [])", flat)
        self.assertIn("joined by a later step that needs both", flat)

    def test_inline_implement_runs_reviewed_steps_directly_without_a_chain(self):
        inline = self.render(advance(self.state(), "implement"))
        self.assertIn("**Inline.** Do the one step on the packet's Step lines (task, paths, skills, check commands, "
                      "lint command) in this conversation. Bind no chain and dispatch no worker.", " ".join(inline.split()))
        step_plan = self.render(advance(self.state(), "step-plan"))
        flat_plan = " ".join(step_plan.split())
        self.assertIn("steps lists every implementation step in the order to do them", flat_plan)
        self.assertIn("`steps`**: every implementation step in order (one is fine)", flat_plan)
        # The "sole execution directive" sentence became this one in duty 9 (re-cut 2026-10-11).
        self.assertIn("each step's task and criteria stay its only directive", flat_plan)
        for packet in (inline, step_plan):
            for text in DELEGATED_ROUTE_TEXT:
                self.assertNotIn(text, packet)

    def test_no_inline_packet_in_a_full_walk_routes_work_to_a_delegate(self):
        scenarios = dry_run.scenarios()
        report = dry_run.run_scenario("delivery", scenarios["delivery"], delegation="inline")
        self.assertTrue(report["ok"], report.get("error"))
        for event in report["events"]:
            for text in DELEGATED_ROUTE_TEXT:
                self.assertNotIn(text, event["prompt"], (event["from"], text))

    def test_toggle_records_the_setting_once_for_new_actions(self):
        state = self.state()
        switched = nav.set_delegation(state, "ask-agent")
        self.assertEqual((switched["delegation"], switched["revision"]), ("ask-agent", state["revision"] + 1))
        self.assertEqual(nav.set_delegation(switched, "ask-agent"), switched)
        with self.assertRaisesRegex(nav.NavigatorError, "inline or ask-agent"):
            nav.set_delegation(state, "serial")

    def test_switch_never_reroutes_the_pending_action_or_its_improve_checkpoint(self):
        # A native worker may already own this ask-agent producer: it keeps its
        # route. step-plan is a planning-review stage, so it still starts an
        # actual Improve checkpoint on this same held action.
        at_test_author = advance(self.state("ask-agent"), "step-plan")
        action = nav.current_action(at_test_author)["id"]
        switched = nav.set_delegation(at_test_author, "inline")
        self.assertEqual(switched["delegation_hold"], {"action": action, "route": "ask-agent"})
        pending = self.render(switched)
        self.assertEqual(pending.split("\n\n", 1)[0], "Execute the prompt in a fresh context.")
        self.assertIn("Prefer a native fresh worker", pending)
        change = "Delegation change: this action keeps ask-agent; actions issued after it use inline."
        self.assertIn(change, pending)
        # The held-route line never displaces the one legal callback after it.
        lines = pending.splitlines()
        callback = lines[lines.index(change) + 1]
        self.assertTrue(callback.startswith("Callback for this stage"), callback)
        self.assertIn("--action=" + action, callback)
        checkpoint = nav.apply(switched, action, {"outcome": "done", "summary": "Synthetic."})
        held_child = self.render(checkpoint)
        # The re-cut Improve packet is the two instructions plus the status block (2026-10-11): it names no route, so it
        # no longer prints the "Delegation change" line (REPORTED: that line is now only on producer packets).  The hold
        # stays recorded on the state, the parked child is unbound, and its first line is the one legal callback.
        self.assertEqual(checkpoint["delegation_hold"], {"action": action, "route": "ask-agent"})
        lines = held_child.splitlines()
        self.assertTrue(lines[0].startswith("ShipLoop navigator | improve | revision ") and
                        lines[0].endswith("| the step-plan result"), lines[0])
        for text in DELEGATED_ROUTE_TEXT:
            self.assertNotIn(text, held_child)
        owner_lines_follow(self, lines)
        callback = lines[1 + OWNER]
        # The parked child is unbound, so its one legal callback is improve-bind, which names the Improve stage's id,
        # never the reviewed action's.
        self.assertTrue(callback.startswith("No Improve card is recorded for this run. Next command (bind the Improve "
                                            "skill's SKILL.md"), callback)
        self.assertIn(" improve-bind ", callback)
        improve_action = checkpoint["active_improve"]["improve_action"]
        self.assertIn("--action=" + improve_action, callback)
        self.assertNotIn("--action=" + action, callback)
        following = nav.finish_improve(checkpoint, action, {"summary": "Synthetic receipt."})
        self.assertTrue(self.render(following).startswith("Continue in this context and execute the prompt."))
        # Switching back before the next action cancels the pending change.
        restored = nav.set_delegation(switched, "ask-agent")
        self.assertNotIn("delegation_hold", restored)
        self.assertEqual(self.render(restored), self.render(dict(at_test_author, revision=restored["revision"])))
        # A chain-bound or Improve-bound current action is safe for the same reason.
        at_implement = advance(self.state("ask-agent"), "implement")
        chained = dict(at_implement, chain_bindings={nav.current_action(at_implement)["id"]: "0" * 64})
        self.assertEqual(nav.delegation(nav.set_delegation(chained, "inline")), "ask-agent")

    def test_toggle_refuses_terminal_runs(self):
        halted = nav.control(self.state(), "halt", "Synthetic stop.")
        with self.assertRaisesRegex(nav.NavigatorError, "terminal"):
            nav.set_delegation(halted, "ask-agent")
        bad = dict(self.state(), delegation_hold={"action": "x", "route": "inline"})
        with self.assertRaisesRegex(nav.NavigatorError, "invalid delegation hold"):
            nav.validate(bad)


class StepTests(DelegationStateTests):
    """The script, not the host, walks a work item's step plan: one implement packet per step."""

    STEPS = [{"id": "S1", "task": "Add divide() to calc.py.", "paths": ["calc.py"]},
             {"id": "S2", "task": "Document divide in README.", "paths": ["README.md"]}]

    def at_implement(self, delegation="inline", steps=None):
        state = advance(self.state(delegation), "step-plan")
        action = nav.current_action(state)["id"]
        state = nav.apply(state, action, {"outcome": "done", "summary": "Synthetic step plan.",
                                          "steps": steps or self.STEPS})
        if state.get("active_improve") is not None:
            state = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
        return advance(state, "implement")

    def done(self, state, summary):
        """Accept the current producer; an implement step's Improve child (owner decision 2026-10-10) is finished."""
        action = nav.current_action(state)["id"]
        state = nav.apply(state, action, {"outcome": "done", "summary": summary})
        if state.get("active_improve") is not None:
            state = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
        return state

    def test_inline_implement_issues_one_packet_per_step_in_order(self):
        state = self.at_implement()
        first = self.render(state)
        self.assertIn("Step S1 (1 of 2), the only work for this packet: Add divide() to calc.py.", first)
        self.assertIn("Later steps (ShipLoop issues each one after this callback; do not start them): "
                      "S2 Document divide in README.", first)
        self.assertNotIn("one step at a time in dependency order", first)
        first_action = nav.current_action(state)["id"]
        state = self.done(state, "divide() added.")
        self.assertEqual(nav.current_stage(state), "implement")
        self.assertNotEqual(nav.current_action(state)["id"], first_action)
        second = self.render(state)
        self.assertIn("Step S2 (2 of 2), the only work for this packet: Document divide in README.", second)
        self.assertIn("Accepted step S1: divide() added.", second)
        self.assertNotIn("Later steps", second)
        # Recovery is a re-render of the saved state: the same step comes back.
        self.assertEqual(self.render(nav.loads(nav.dumps(state))) if hasattr(nav, "loads") else second, second)
        state = self.done(state, "README documents divide.")
        self.assertNotEqual(nav.current_stage(state), "implement")

    def test_the_snapshot_does_not_list_implement_as_done_while_steps_remain(self):
        # On steps 2..N the Progress snapshot listed implement among the accepted-done stages and dropped it from the
        # pending list beside "Current: implement", which a model that lost its context could read as finished (seen in
        # 3 packets of one checkers run; packet review 2026-10-10, P-implement-1).  The packet no longer prints the
        # snapshot (2026-10-11 dedupe): its status block is the one saved-position display, and report.html keeps the
        # snapshot (nav._progress_lines), so the rule is pinned on both homes.
        def status_of(packet):
            return packet.split("=== ShipLoop status ===", 1)[1].split("=== end ShipLoop status ===", 1)[0]

        state = self.at_implement()
        for step, accepted in ((state, 0), (self.done(state, "divide() added."), 1)):
            packet = self.render(step)
            self.assertNotIn("Progress snapshot", packet)
            status = status_of(packet)
            self.assertIn("Build \u25b6", status)  # the Build group is current, never done, while steps remain
            self.assertNotIn("Build \u2713", status)
            self.assertIn("Next:      implement:", status)
            snapshot = "\n".join(nav._progress_lines(step))
            self.assertIn("Current: implement", snapshot)
            self.assertIn(f"Current stage implement: in progress ({accepted} of 2 steps accepted)", snapshot)
            self.assertNotRegex(snapshot, r"stages completed \(accepted done\):.*\bimplement\b")
        last = self.done(self.done(state, "divide() added."), "README documents divide.")
        self.assertNotIn("Current stage implement: in progress", "\n".join(nav._progress_lines(last)))
        # Only the last accepted step makes implement a completed stage.
        self.assertRegex("\n".join(nav._progress_lines(last)), r"stages completed \(accepted done\):.*\bimplement\b")

    def test_a_chain_implement_has_no_step_count_in_the_snapshot(self):
        # The chain runs every step inside its one implement action: there is no per-step acceptance to count.
        self.assertNotIn("Current stage implement: in progress", self.render(self.at_implement("ask-agent")))

    def test_one_step_is_one_implement_packet(self):
        state = self.at_implement(steps=[{"id": "S1", "task": "Make the change."}])
        self.assertIn("Step S1 (1 of 1)", self.render(state))
        self.assertNotEqual(nav.current_stage(self.done(state, "Changed.")), "implement")

    def test_ask_agent_implement_stays_one_action(self):
        # The chain executes every step inside the one implement action.
        state = self.at_implement("ask-agent")
        self.assertNotIn("Step S1", self.render(state))
        self.assertNotEqual(nav.current_stage(self.done(state, "Chain finished.")), "implement")

    def test_a_revised_step_plan_restarts_its_steps(self):
        state = self.done(self.at_implement(), "divide() added.")
        state = nav.apply(state, nav.current_action(state)["id"],
                          {"outcome": "revise", "summary": "S2 cannot be done as planned."})
        self.assertEqual(nav.current_stage(state), "step-plan")
        action = nav.current_action(state)["id"]
        state = nav.apply(state, action, {"outcome": "done", "summary": "Revised plan.",
                                          "steps": [{"id": "T1", "task": "Do it differently."}]})
        if state.get("active_improve") is not None:
            state = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
        state = advance(state, "implement")
        self.assertIn("Step T1 (1 of 1)", self.render(state))

    def test_step_dependencies_preserve_legacy_plans_and_reject_invalid_edges(self):
        legacy = [{"id": "S1", "task": "First"}, {"id": "S2", "task": "Second"}]
        self.assertEqual(nav._normalise_steps(legacy), legacy)
        declared = [{"id": "S1", "task": "First", "deps": []},
                    {"id": "S2", "task": "Second", "deps": ["S1"]}]
        self.assertEqual(nav._normalise_steps(declared), declared)
        state = self.at_implement(steps=declared)
        nav.validate(state)
        self.assertIn('"deps"', nav._result_template(state, "step-plan"))
        for deps in (["S2"], ["unknown"], ["S1", "S1"], "S1", [7]):
            with self.subTest(deps=deps), self.assertRaises(nav.NavigatorError):
                nav._normalise_steps([declared[0], {"id": "S2", "task": "Second", "deps": deps}])
        with self.assertRaisesRegex(nav.NavigatorError, "earlier steps"):
            nav._normalise_steps([{"id": "S1", "task": "First", "deps": ["S2"]}, declared[1]])

    def test_steps_are_required_and_well_formed(self):
        plan = {"outcome": "done", "summary": "s", "paths": ["calc.py", "README.md"], "test_commands": [],
                "test_commands_na": "synthetic"}
        with self.assertRaisesRegex(nav.NavigatorError, "must list steps"):
            nav._check_submitted_test_commands("step-plan", plan)
        nav._check_submitted_test_commands("step-plan", dict(plan, steps=self.STEPS))
        for steps, message in (([], "nonempty"), ([{"id": "S1"}], "each step is"),
                               ([{"id": "S 1", "task": "t"}], "no spaces"),
                               ([{"id": "S1", "task": "a"}, {"id": "S1", "task": "b"}], "unique")):
            with self.subTest(steps=steps), self.assertRaisesRegex(nav.NavigatorError, message):
                nav._canonical_result(dict(plan, steps=steps), stage="step-plan")
        with self.assertRaisesRegex(nav.NavigatorError, "only on a done step-plan"):
            nav._canonical_result({"outcome": "done", "summary": "s", "steps": self.STEPS}, stage="implement")


class PacketContractTests(DelegationStateTests):
    """Packet fields a fresh inline context needs, pinned on both routes where shared."""

    def test_producer_packets_state_outcomes_and_explicit_commands(self):
        entry = self.render(advance(self.state(), "verify"))
        # The callback leads and is printed once (the "Write the structured result to:" line and the tail's "Call this when
        # done:" callback are gone, 2026-10-11 dedupe); the result contract follows the duties and rules and ends the
        # required text (the print order of the efficiency plan, section 6.1).
        head = entry.split("Current stage guidance:", 1)[0]
        self.assertIn("\nCallback for this stage (run once after its work, with the result written to the file it "
                      "names): ", head)
        self.assertIn("--result=", head.split("\nCallback for this stage", 1)[1].split("\n", 1)[0])
        self.assertNotIn("Write the structured result to: ", entry)
        # repeat is no longer an inner outcome (8-stage loop, 2026-10-10).
        self.assertIn("\nAllowed outcomes: done | blocked | revise", entry)
        self.assertLess(entry.index("Current stage guidance:"), entry.index("\nAllowed outcomes: "))
        self.assertNotIn("Call this when done:", entry)
        self.assertEqual(entry.count("Callback for this stage"), 1)
        self.assertIn("Halt (terminal and irreversible; only on an explicit user stop): ", entry)
        # verify starts no Improve child, and its packet says nothing about Improve (owner rule 2026-10-10: Improve is
        # mentioned only as a directive); how to report a stop is the outcome shapes' (the trailing Improve-line sentence
        # is gone, 2026-10-11 dedupe), and the stage prints no Improve line.
        self.assertNotIn("advances directly", entry)
        self.assertNotIn("If work cannot continue, submit outcome 'blocked'", entry)
        self.assertFalse([line for line in entry.splitlines() if line.startswith("Improve:")])
        self.assertIn('blocked: {"outcome": "blocked", "blocked_by": "user | access | external"', entry)
        # No route offers a pause for a context clear: the host cannot be cleared from a packet.
        for route in ("inline", "ask-agent"):
            with self.subTest(route=route):
                packet = self.render(advance(self.state(route), "verify"))
                self.assertNotIn("context-boundary", packet)
                self.assertNotIn("Recovery command, then the printed Resume", packet)
        self.assertIn("Optional work_items replaces the whole queue", self.render(advance(self.state(), "plan")))
        self.assertIn("replaces the queue after this item",
                      self.render(advance(self.state(), "carry-forward")))
        outer = self.render(advance(self.state(), "system-test-author"))
        self.assertIn("Allowed outcomes: done | repeat | blocked | replan (corrective work_items", outer)
        for packet in (entry, outer):
            self.assertNotIn("reconcile", packet.split("Allowed outcomes:", 1)[1].split("\n", 1)[0])

    def test_fresh_contexts_find_the_skill_card_and_the_item_plan(self):
        state = advance(self.state(), "implement")
        packet = self.render(state)
        card = PACKAGE / "SKILL.md"
        # The skill card line left the run rules (2026-10-11 dedupe): reference.md#policies lists it, and the packet's
        # one pointer line names that file.
        self.assertNotIn("ShipLoop skill card: ", packet)
        self.assertIn("(#policies, #rules, #recovery)", packet)
        self.assertIn("- ShipLoop skill card: " + str(card) + "\n", reference.render(state, Path("/simulation-only/run")))
        self.assertTrue(card.is_file())
        step_plan = next(entry["action"] for entry in state["history"] if entry["stage"] == "step-plan")
        # A source that "Results this stage builds on" lists is not printed again as a test source (2026-10-11
        # dedupe): the step-plan result and plan section are listed there, by the action id in the result path.
        self.assertIn("- W1 step-plan result: RUN/results/" + step_plan + ".md", packet)
        self.assertNotIn("Current item step-plan source action", packet)
        # Right after step-plan it is already the test-decision source; do not print it twice.
        test_spec = self.render(advance(self.state(), "test-spec"))
        self.assertNotIn("Current item step-plan source", test_spec)
        # ... and, listed under "Results this stage builds on", it is not printed as a test-decision source either.
        self.assertNotIn("Current item test-decision source action:", test_spec)
        self.assertIn("- W1 step-plan result: RUN/results/", test_spec)
        self.assertNotIn("Current item step-plan source", self.render(advance(self.state(), "step-plan")))
        # The inline route's "Execute this packet in this conversation..." run-rule line is gone: the preamble says it.
        # The Repository knowledge index line and the pointer to reference.md are one run-rule line since the second
        # re-cut pass; the card line is still listed in reference.md#policies.
        self.assertNotIn("Execute this packet in this conversation, submit its current callback yourself", packet)
        self.assertIn("do this stage here and submit its callback\nyourself; never clear or hand it off", packet)
        delegated = self.render(dict(state, delegation="ask-agent"))
        self.assertIn("Give the executing agent only the current action packet", delegated)
        self.assertIn("- W1 step-plan result: RUN/results/" + step_plan + ".md", delegated)
        self.assertNotIn("Current item step-plan source action", delegated)

    def test_verify_assembles_direct_or_chain_work(self):
        # integrate is folded into verify (8-stage loop, 2026-10-10).
        for route in ("inline", "ask-agent"):
            with self.subTest(route=route):
                text = " ".join(nav.guidance.prompt("verify", delegation=route).split())
                # ShipLoop commits the declared files when verify is accepted; no route tells the model to commit.
                # Duty 8 (Assembly) prints on the ask-agent route only (U11, VR-6): an inline run builds every step in
                # the execution checkout and binds no chain, so there is nothing to assemble; the other items keep
                # their numbers.  Its fallback sentence still names the execution checkout where a chain is not bound.
                self.assertNotIn("assemble or commit", text)
                self.assertEqual("candidate is assembled in the execution checkout" in text.lower(), route == "ask-agent")
                self.assertEqual("8. **assembly.**" in text.lower(), route == "ask-agent")
                self.assertIn("9. **later checks.**", text.lower())
                # A chain exists only when delegation is ask-agent, so only that route confirms its finish commit.
                self.assertEqual("confirm its finish commit is an ancestor of the execution checkout HEAD" in text,
                                 route == "ask-agent")

    def test_final_result_must_list_the_reviewed_queue(self):
        receipt = {"summary": "Synthetic receipt; no review claim."}
        queue = [{"id": "W1", "title": "Reviewed item"}, {"id": "W2", "title": "Second item"}]
        for stage, proposal in (("plan", queue), ("carry-forward", [])):
            with self.subTest(stage=stage):
                state = advance(self.state(), stage)
                action = nav.current_action(state)["id"]
                waiting = nav.apply(state, action, {"outcome": "done", "summary": "Proposed.",
                                                    "work_items": proposal})
                # The Improve detail is in the handoff file ShipLoop writes (re-cut 2026-10-11), not the packet.
                self.assertIn("A done final_result must list the complete intended queue",
                              " ".join(nav.improve_handoff_text(None, self.run, waiting).split()))
                self.assertNotIn("complete intended queue", self.render(waiting))
                with self.assertRaisesRegex(nav.NavigatorError, "must list the complete intended queue"):
                    nav.finish_improve(waiting, action, receipt, {"outcome": "done", "summary": "Revised."})
                # Non-done dispositions and an explicit queue are unaffected.
                # carry-forward runs an Until Loop, so repeat is not one of its outcomes; blocked is its non-done one.
                other = ({"outcome": "repeat", "summary": "Redo."} if "repeat" in nav.stage_spec.stage(stage).outcomes
                         else {"outcome": "blocked", "summary": "Waiting on a service.", "blocked_by": "external"})
                nav.finish_improve(waiting, action, receipt, other)
                nav.finish_improve(waiting, action, receipt,
                                   {"outcome": "done", "summary": "Revised.", "work_items": proposal})

    def test_bound_improve_packets_carry_only_their_route(self):
        # The Improve packet is two instructions (re-cut 2026-10-11); the route text lives in the handoff file.
        with tempfile.TemporaryDirectory(prefix="shiploop-bound-walk-") as temp:
            repo = Path(temp).resolve() / "repo"
            repo.mkdir()
            inline = bound_walk(repo, "inline", handoffs=True)
            delegated = bound_walk(repo, "ask-agent", handoffs=True)
        self.assertEqual(len([entry for entry in inline if entry[1] != "handoff"]), 33)
        for stage, kind, packet in inline:
            for text in BOUND_DELEGATED_TEXT:
                self.assertNotIn(text, packet, (stage, kind, text))
            if kind == "improve":
                self.assertNotIn("Delegation:", packet)
            if kind == "handoff":
                self.assertIn("Delegation: inline. Run the selected Improve card", packet)
                self.assertIn("start no reviewer, test-runner or executor agent unless the user asked for "
                              "independent review", packet)
        # Positive control: every phrase is live on the delegated route, so the
        # inline sweep above cannot pass merely because the wording changed.
        delegated_text = "\n".join(packet for _stage, _kind, packet in delegated)
        for text in BOUND_DELEGATED_TEXT:
            self.assertIn(text, delegated_text)

    def test_a_bound_improve_packet_prints_the_commit_command_right_after_improve_start(self):
        # The command and the exact commit-message path sat at about 30 KB of a 47 KB packet, below improve-start: one
        # review wrote the wrong file name and was refused, another searched for the command (packet review
        # 2026-10-10, P-improve-1).  The planning packet prints no command: it names parent-return.md, which improve-start
        # writes with the command and its message rules, right after its Commit policy line.  Since 8f3d4cbe improve-commit
        # refuses a message with no Key learnings line, so the line shows that format and ends with the command.
        with tempfile.TemporaryDirectory(prefix="shiploop-commit-walk-") as temp:
            repo = Path(temp).resolve() / "repo"
            repo.mkdir()
            walks = {route: bound_walk(repo, route, handoffs=True) for route in ("inline", "ask-agent")}
        checked = planned = 0
        for route, packets in walks.items():
            for stage, kind, packet in packets:
                # The commit rules moved from the Improve packet into the handoff file (re-cut 2026-10-11).
                if kind != "handoff":
                    continue
                lines = packet.splitlines()
                with self.subTest(route=route, stage=stage):
                    commits = [i for i, line in enumerate(lines) if " improve-commit --run-dir=" in line]
                    if stage == "plan":
                        self.assertEqual(commits, [])
                        policy = next(i for i, line in enumerate(lines) if line.startswith("Commit policy:"))
                        pointer = lines[policy + 1]
                        self.assertRegex(pointer, r"^To commit a review iteration's changes, run the improve-commit "
                                                  r"command in \S+/parent-return\.md; its message rules are there\.")
                        self.assertIn("Do not run git commit yourself.", pointer)
                        planned += 1
                        continue
                    # ShipLoop starts the child itself (owner, 2026-10-11): the paragraph saying so replaces the old
                    # improve-start line, and the commit command still follows it directly.
                    start = next(i for i, line in enumerate(lines)
                                 if line.startswith("ShipLoop started this review when the Improve stage began"))
                    self.assertNotIn("improve-start --run-dir=", "\n".join(lines[start:start + 2]))
                    self.assertEqual(commits, [start + 1])
                    commit = lines[start + 1]
                    self.assertTrue(commit.startswith("To commit a review iteration's changes"), commit)
                    written = re.search(r"write the commit message to (\S+) with a file-writing tool", commit).group(1)
                    self.assertIn("`Key learnings: none`", commit)
                    self.assertIn("column 1", commit)
                    command = commit.rsplit("Then run: ", 1)[1]
                    self.assertEqual(command.split()[2], "improve-commit")
                    self.assertTrue(command.endswith("--message=" + written), command)  # one file; nothing after it
                    # improve-commit names the Improve stage's id: the one the complete callback in this file names.
                    complete = next(line for line in lines if line.startswith("python3 shiploop complete --run-dir="))
                    self.assertEqual(shlex.split(command)[4], shlex.split(complete)[4])
                    self.assertTrue(shlex.split(command)[4].startswith("--action="), command)
                    checked += 1
        self.assertGreaterEqual(checked, 12)
        self.assertEqual(planned, 2)

    def test_a_child_shiploop_could_not_start_leads_with_the_restart_command(self):
        """A start the runtime refused leaves the Improve stage pending: its packet's first instruction is the one
        restart route (improve-start --restart-stopped, with the Improve stage's id), then the usual two lines."""
        with tempfile.TemporaryDirectory(prefix="shiploop-restart-walk-") as temp:
            repo = Path(temp).resolve() / "repo"
            repo.mkdir()
            packets = [(stage, text) for stage, kind, text in bound_walk(repo, "inline", started=False)
                       if kind == "improve"]
        self.assertTrue(packets)
        for stage, packet in packets:
            with self.subTest(stage=stage):
                lines = packet.splitlines()
                self.assertTrue(lines[0].startswith("ShipLoop navigator | improve | revision "), lines[0])
                owner_lines_follow(self, lines)
                self.assertTrue(lines[1 + OWNER].startswith("ShipLoop could not start this review; start it again first: "),
                                lines[1 + OWNER])
                argv = shlex.split(lines[1 + OWNER].split("first: ", 1)[1])
                self.assertEqual(argv[2], "improve-start")
                self.assertEqual(argv[-1], "--restart-stopped")
                self.assertFalse(any(arg.startswith("--opening") for arg in argv), argv)
                complete = next(line for line in lines if line.startswith("2. When the improve skill"))
                self.assertEqual(shlex.split(complete.split("run: ", 1)[1])[4], argv[4])  # one id for both commands

    def test_no_improve_packet_may_perform_a_release_effect(self):
        # SPEC S-3 and environment-lifecycle.md#release-operation-ownership: a stage-scoped Improve assesses and records
        # its handoff, and no Improve child runs at release itself.  The release-plan Improve packet said "Improve may
        # perform deployments" in the packet that says it plans without executing release (packet review 2026-10-10,
        # P-imp-1).
        with tempfile.TemporaryDirectory(prefix="shiploop-release-guard-") as temp:
            repo = Path(temp).resolve() / "repo"
            repo.mkdir()
            packets = bound_walk(repo, "inline", handoffs=True)
        # The Improve detail is in the handoff file, not the two-instruction packet (re-cut 2026-10-11).
        improve = {stage: " ".join(packet.split()) for stage, kind, packet in packets if kind == "handoff"}
        self.assertNotIn("release", improve)  # the walk binds no Improve child at the release stage
        for stage, packet in improve.items():
            self.assertNotIn("may perform deployments", packet, stage)
        text = improve["release-plan"]
        self.assertIn("does not execute or replay a release effect", text)
        self.assertIn("without executing release", text)

    def test_every_active_packet_leads_with_its_legal_callback_and_schedule_text(self):
        with tempfile.TemporaryDirectory(prefix="shiploop-callback-walk-") as temp:
            repo = Path(temp).resolve() / "repo"
            repo.mkdir()
            walks = {route: bound_walk(repo, route, handoffs=True) for route in ("inline", "ask-agent")}
        planning = nav.guidance.PLANNING_REVIEW_STAGES
        for route, packets in walks.items():
            for stage, kind, packet in packets:
                with self.subTest(route=route, stage=stage, kind=kind):
                    # No packet-size bound: the owner prefers complete prompts (2026-09-25).
                    self.assertNotIn("Improve cadence", packet)
                    lines = packet.splitlines()
                    if kind == "handoff":
                        self.check_handoff(stage, planning, lines, packet)
                        continue
                    # An inline prefix may precede the header; nothing else may.
                    header = next(i for i, line in enumerate(lines)
                                  if line.startswith("ShipLoop navigator | "))
                    if kind == "improve":
                        # The bound Improve packet is two instructions (re-cut 2026-10-11): run the improve skill with
                        # the handoff path, then the Improve stage's complete.  Its header names the stage (owner,
                        # 2026-10-11: Improve is a stage of its own) and the reviewed result.
                        self.assertEqual(lines[header], "ShipLoop navigator | improve | revision "
                                         + lines[header].split("revision ", 1)[1].split(" |")[0]
                                         + " | the " + stage + " result")
                        self.assertEqual(header, 0)
                        owner_lines_follow(self, lines)
                        self.assertTrue(lines[1 + OWNER].startswith("1. Run the improve skill on the " + stage + " result."),
                                        lines[1 + OWNER])
                        self.assertTrue(lines[2 + OWNER].lstrip().startswith("/improve ShipLoop Improve: "), lines[2 + OWNER])
                        self.assertTrue(lines[2 + OWNER].rstrip().endswith("/handoff.md"), lines[2 + OWNER])
                        callback = next(line for line in lines if line.startswith("2. When the improve skill"))
                        argv = shlex.split(callback.split("run: ", 1)[1])
                        self.assertEqual(argv[2], "complete")
                        # P12: no completion record; ShipLoop derives it from the review files.
                        self.assertFalse(any(arg.startswith("--result") for arg in argv), argv)
                        self.assertNotIn("improve-complete", packet)  # the verb is gone
                        self.assertNotIn("improve-start", packet)     # ShipLoop started the child
                        self.assertNotIn("improve-bind", packet)  # the card is bound at the transition
                        continue
                    self.assertRegex(lines[header],
                                     r"^ShipLoop navigator \| " + re.escape(stage) + r" \| revision \d+$")
                    owner_lines_follow(self, lines, header)
                    lead = lines[header + 1 + OWNER]
                    self.assertTrue(lead.startswith("Callback for this stage "), lead)
                    # The first callback line is the only one: "Call this when done:" is gone (2026-10-11 dedupe),
                    # so the lead carries the complete command and the result file it reads.
                    self.assertNotIn("Call this when done:", packet)
                    command = shlex.split(lead.split("): ", 1)[1])
                    self.assertEqual(command[2], "complete")
                    self.assertTrue(any(arg.startswith("--result=") and arg.endswith(".md") for arg in command),
                                    command)
                    # No producer packet mentions Improve ahead of time (owner rule 2026-10-10, re-cut 2026-10-11):
                    # no "Improve:" line, no "starts this action's Improve child" sentence.
                    self.assertFalse([line for line in lines if line.startswith("Improve:")])
                    self.assertNotIn("starts this action's Improve child", packet)
                    self.assertNotIn("single end-of-work Improve child", packet)
                    self.assertNotIn("the Improve child's", packet)
                    if stage == "implement":
                        # An Improve child reviews every accepted step (owner decision 2026-10-10), so the
                        # packet must not say the result advances with no child.
                        self.assertNotIn("no Improve child runs for this stage", packet)
                    elif stage not in planning and stage != "carry-forward":
                        # The blocked route is the outcome shapes' (the trailing sentence is gone, 2026-10-11 dedupe).
                        self.assertNotIn("advances directly", packet)
                        self.assertNotIn("If work cannot continue, submit outcome 'blocked'", packet)
                        self.assertIn("blocked", next(line for line in lines if line.startswith("Allowed outcomes:")))

    def check_handoff(self, stage, planning, lines, packet):
        """The handoff file holds what the old Improve packet led with (re-cut 2026-10-11)."""
        self.assertTrue(lines[0].startswith("# ShipLoop Improve handoff: the " + stage + " result"), lines[0])
        # ShipLoop wrote the opening and started the child (owner, 2026-10-11): the hand-off says so, names the opening
        # it wrote, and never asks the model to write it or to run improve-start; then the Improve stage's complete.
        started = next(line for line in lines
                       if line.startswith("ShipLoop started this review when the Improve stage began"))
        self.assertRegex(started, r"it wrote the opening \S+/opening\.md from the run's state")
        self.assertIn("Do not write the opening or start the runtime yourself", started)
        self.assertNotIn("--opening", packet)
        self.assertNotIn("improve-complete", packet)
        self.assertFalse([line for line in lines if " improve-start " in line and "--restart-stopped" not in line])
        parent = next(i for i, line in enumerate(lines)
                      if line.startswith(("Parent callback;", "Parent-only callback;")))
        argv = shlex.split(lines[parent + 1])
        self.assertEqual(argv[2], "complete")
        self.assertFalse(any(arg.startswith("--result") for arg in argv), argv)
        reviewed = re.search(r"\((nav-[0-9a-f]+)\)", lines[0]).group(1)
        self.assertEqual(argv[4].startswith("--action=nav-"), True, argv)
        self.assertNotEqual(argv[4], "--action=" + reviewed)  # the Improve stage's id, not the reviewed action's
        self.assertTrue(any(line.startswith("Evidence: write each review pass to ") for line in lines))
        if stage == "carry-forward":
            self.assertIn("End-of-work review: this is the run's single Improve", packet)
            self.assertNotIn("Planning review focus", packet)
        elif stage == "implement":
            self.assertIn("Implementation step review focus.", packet)
            self.assertNotIn("Planning review focus", packet)
            self.assertNotIn("End-of-work review", packet)
        else:
            self.assertIn(stage, planning)
            self.assertIn("Planning review focus.", packet)
            self.assertNotIn("End-of-work review", packet)


class AggregateImplementWordingTests(unittest.TestCase):
    """The ask-agent route issues one implement action for every step of the plan (its chain runs them), so the Goal,
    the Done-when, the loop's exit conditions and the Improve review focus name those steps and their paths instead of
    "this step" (U11, rev 4 Step 0.2).  The inline route issues one action per step and keeps the per-step wording."""

    STEPS = [{"id": "S1", "task": "Make change one.", "paths": ["a.py"]},
             {"id": "S2", "task": "Make change two.", "paths": ["pkg/b.py"]}]

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-aggregate-")
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / "run"
        self.run.mkdir()
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()

    def state(self, delegation="inline"):
        return nav.new_state(str(self.repo), "Synthetic delegation request.", delegation=delegation)

    def render(self, state):
        return nav.render(None, self.run, state)

    def at_implement(self, delegation, steps=None):
        state = self.state(delegation)
        while nav.current_stage(state) != "implement":
            stage, action = nav.current_stage(state), nav.current_action(state)["id"]
            result = {"outcome": "done", "summary": "Synthetic " + stage + " declaration."}
            if stage == "plan":
                result["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            if stage == "step-plan":
                result.update(steps=steps or self.STEPS, paths=["a.py", "pkg/b.py"])
            state = nav.apply(state, action, result)
            if state.get("active_improve") is not None:
                state = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
        return state

    def handoff(self, state):
        action = nav.current_action(state)["id"]
        state = nav.apply(state, action, {"outcome": "done", "summary": "Synthetic implement declaration."})
        child = state["active_improve"]
        selected = standalone.resolve_skill(str(CARD))
        state["active_improve"] = standalone.binding(state, action, child["stage"], child["seed_result"], selected,
                                                     improve_action=child["improve_action"])
        receipt = standalone.receipt_path(state["active_improve"])
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text("{}", encoding="utf-8")
        return nav.improve_handoff_text(None, self.run, state)

    def flat(self, text):
        return " ".join(text.split())

    def test_a_two_step_ask_agent_handoff_names_the_steps_and_both_paths(self):
        text = self.flat(self.handoff(self.at_implement("ask-agent")))
        self.assertIn("steps S1 to S2", text)
        self.assertIn("(a.py, pkg/b.py)", text)
        for stale in ("one step", "the step's paths", "this step's change", "since the step began"):
            self.assertNotIn(stale, text)
        self.assertIn("Implementation step review focus.", text)
        # the Code craft rubric that ends the focus is verbatim, and the shared bullets are untouched
        self.assertIn(self.flat(prompts.CODE_CRAFT), text)
        self.assertIn("a recorded check command that fails, or a new lint finding on a changed line with no waiver", text)

    def test_the_inline_handoff_keeps_the_per_step_wording_byte_for_byte(self):
        text = self.handoff(self.at_implement("inline"))
        self.assertIn(prompts.IMPLEMENT_STEP_REVIEW_FOCUS.rstrip(), text)
        row = stage_spec.stage("implement")
        self.assertIn("Goal: " + row.goal[0].upper() + row.goal[1:], text)
        for condition in row.done_when:
            self.assertIn("- " + condition + "\n", text)
        self.assertNotIn("S1 to S2", text)

    def test_a_one_step_ask_agent_plan_keeps_the_per_step_wording(self):
        text = self.handoff(self.at_implement("ask-agent", self.STEPS[:1]))
        self.assertIn(prompts.IMPLEMENT_STEP_REVIEW_FOCUS.rstrip(), text)
        self.assertNotIn(" to S1", text)

    def test_the_packet_goal_and_the_loop_contract_say_the_same_steps(self):
        state = self.at_implement("ask-agent")
        action = nav.current_action(state)["id"]
        packet = self.flat(self.render(state))
        self.assertIn("Goal: Make the change of steps S1 to S2 on their paths (a.py, pkg/b.py) in WORKTREE", packet)
        contract = loops.contract(self.run, state, action)
        first = contract["exit_condition"].splitlines()[0]
        self.assertEqual(first, "1. only the paths of steps S1 to S2 (a.py, pkg/b.py) changed since the first of them "
                                "began, and no work outside those steps is in them")
        self.assertIn("1. only the paths of steps S1 to S2", packet)    # the packet prints the contract's own text
        self.assertNotIn("the step's paths", packet.split("Current stage guidance:", 1)[0])
        # the loop's work says it once, as a list, with no stray comma before the sentence stop
        self.assertIn("for the change of every step, S1 to S2, in order. Write no tests", contract["work"])
        cold = self.at_implement("inline")
        inline = loops.contract(self.run, cold, nav.current_action(cold)["id"])
        self.assertEqual(inline["exit_condition"].splitlines()[0],
                         "1. " + stage_spec.stage("implement").done_when[0])

    def test_the_stage_row_words_itself_only_where_it_has_aggregate_wording(self):
        for name in stage_spec.STAGES:
            row = stage_spec.stage(name)
            self.assertIs(stage_spec.for_steps(row, "S1 to S2", "a.py") is row, row.steps_goal is None, name)
        worded = stage_spec.for_steps(stage_spec.stage("implement"), "S1 to S2", "a.py, b.py")
        self.assertEqual(len(worded.done_when), len(stage_spec.stage("implement").done_when))
        self.assertEqual(worded.name, "implement")


class DelegationCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-delegation-cli-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "product"
        self.repo.mkdir()
        self.run = self.base / "run"
        self.env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull}

    def cli(self, *args):
        completed = subprocess.run([sys.executable, "-B", str(CLI), *map(str, args)], cwd=self.base,
                                   text=True, capture_output=True, timeout=60, env=self.env)
        if completed.stdout:
            completed.stdout = _with_packet_file(completed.stdout)
        return completed

    def init(self, *args):
        return self.cli("init", "--repo", self.repo, "--run-dir", self.run,
                        "--prompt", "Synthetic delegation CLI request.", *args)

    def saved(self):
        return store.read_record(self.run / "state.md")

    def test_new_runs_default_to_inline_and_accept_ask_agent(self):
        result = self.init()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.saved()["delegation"], "inline")
        other = self.base / "ask-run"
        result = self.cli("init", "--repo", self.repo, "--run-dir", other, "--prompt", "Other.",
                          "--delegation", "ask-agent")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(store.read_record(other / "state.md")["delegation"], "ask-agent")

    def test_removed_init_modes_are_rejected_before_creating_a_run(self):
        # The single home for rejecting removed init modes and the retired
        # protocol selector.
        for extra in (("--execution-mode", "navigator-v2"),
                      ("--execution-mode", "navigator-v1"), ("--execution-mode", "managed"),
                      ("--execution-mode", "legacy")):
            for delegation in ((), ("--delegation", "inline")):
                with self.subTest(extra=extra, delegation=delegation):
                    result = self.init(*delegation, *extra)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertIn("invalid choice", result.stderr)
                    self.assertFalse(self.run.exists())
        for version in ("2", "3", "4"):
            with self.subTest(navigator_version=version):
                result = self.init("--navigator-version", version)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("unrecognized arguments: --navigator-version", result.stderr)
                self.assertFalse(self.run.exists())

    def test_init_retry_cannot_change_delegation_and_toggle_is_explicit(self):
        self.assertEqual(self.init().returncode, 0)
        before = (self.run / "state.md").read_bytes()
        refused = self.init("--delegation", "ask-agent")
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("differs from this run's recorded delegation inline; rerun without --delegation",
                      refused.stderr)
        self.assertEqual(before, (self.run / "state.md").read_bytes())
        self.assertEqual(self.init("--delegation", "inline").returncode, 0)
        self.assertEqual(before, (self.run / "state.md").read_bytes())

        switched = self.cli("delegation", "--run-dir", self.run, "--set", "ask-agent")
        self.assertEqual(switched.returncode, 0, switched.stderr)
        self.assertIn("ShipLoop navigator | intake |", switched.stdout)
        after = self.saved()
        self.assertEqual((after["delegation"], after["revision"]), ("ask-agent", 1))
        same = (self.run / "state.md").read_bytes()
        self.assertEqual(self.cli("delegation", "--run-dir", self.run, "--set", "ask-agent").returncode, 0)
        self.assertEqual(same, (self.run / "state.md").read_bytes())

    def test_toggle_requires_a_value_and_an_existing_v3_v4_run(self):
        self.run.mkdir()
        missing = self.cli("delegation", "--run-dir", self.run, "--set", "inline")
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("delegation needs an existing run", missing.stderr)
        self.assertFalse((self.run / "state.md").exists())
        self.assertNotEqual(self.cli("delegation", "--run-dir", self.run).returncode, 0)

    def test_toggle_during_a_bound_improve_child_applies_from_the_next_action(self):
        self.assertEqual(self.init("--improve-skill", CARD).returncode, 0)
        # intake, discovery and research are not planning stages and advance
        # directly with no Improve checkpoint; bind at the next stage, spec.
        for _ in range(3):
            action = self.saved()["action"]["id"]
            result_path = self.run / "inbox" / (action + ".md")
            store.write_record(result_path, {"outcome": "done", "summary": "Synthetic advance."})
            self.assertEqual(self.cli("complete", "--run-dir", self.run, "--action", action,
                                      "--result", result_path).returncode, 0)
        self.assertEqual(self.saved()["stage"], "spec")
        action = self.saved()["action"]["id"]
        result_path = self.run / "inbox" / (action + ".md")
        store.write_record(result_path, {"outcome": "done", "summary": "Synthetic spec."})
        self.assertEqual(self.cli("complete", "--run-dir", self.run, "--action", action,
                                  "--result", result_path).returncode, 0)
        # ShipLoop bound the run's Improve card and started the review at the transition (owner, 2026-10-11): no
        # improve-bind, and the child's opening and receipt are already on disk.
        child = self.saved()["active_improve"]
        self.assertIsNotNone(child["skill"])
        self.assertTrue(standalone.receipt_path(child).is_file())
        self.assertTrue(standalone.receipt_path(child).with_name("opening.md").is_file())
        switched = self.cli("delegation", "--run-dir", self.run, "--set", "ask-agent")
        self.assertEqual(switched.returncode, 0, switched.stderr)
        # The bound child keeps its inline route; later actions use ask-agent.
        # The Improve packet is two instructions (re-cut 2026-10-11): the route text is in the handoff file it names,
        # and the "Delegation change" line (REPORTED) is no longer printed on Improve packets; the hold is on the state.
        self.assertIn("1. Run the improve skill on the spec result.", switched.stdout)
        handoff = Path(re.search(r"/improve ShipLoop Improve: (\S+)", switched.stdout).group(1))
        self.assertIn("Delegation: inline. Run the selected Improve card", handoff.read_text(encoding="utf-8"))
        self.assertNotIn("Prefer a native fresh worker", switched.stdout + handoff.read_text(encoding="utf-8"))
        self.assertEqual(self.saved()["delegation_hold"], {"action": action, "route": "inline"})

    def test_chain_bind_is_refused_on_inline_runs_before_any_side_effect(self):
        state = advance(nav.new_state(str(self.repo), "Synthetic chain refusal.",
                                      delegation="inline"), "implement")
        self.run.mkdir()
        nav.save(self.run, state)
        before = (self.run / "state.md").read_bytes()
        action = nav.current_action(state)["id"]
        refused = self.cli("chain", "bind", "--run-dir", self.run, "--action", action,
                           "--graph", self.base / "graph.json", "--dispatcher-skill", self.base / "d",
                           "--ask-agent-skill", self.base / "a", "--worktree-parent", self.base)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("delegation is inline", refused.stdout + refused.stderr)
        self.assertEqual(before, (self.run / "state.md").read_bytes())
        self.assertFalse((self.run / "chains").exists())

    def test_workspace_start_passes_delegation_and_refuses_a_changed_retry(self):
        def git(*args):
            subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True,
                           env=self.env)
        git("init", "-q", "-b", "main")
        git("config", "user.name", "Delegation Fixture")
        git("config", "user.email", "delegation@example.invalid")
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        git("add", "README.md")
        git("commit", "-qm", "baseline")
        root = self.base / "workspace"
        args = ("workspace", "start", "--repo", self.repo, "--workspace-root", root,
                "--prompt", "Synthetic workspace delegation.")
        started = self.cli(*args, "--delegation", "ask-agent")
        self.assertEqual(started.returncode, 0, started.stderr)
        self.assertEqual(store.read_record(root / "run/state.md")["delegation"], "ask-agent")
        retry = self.cli(*args, "--delegation", "inline")
        self.assertNotEqual(retry.returncode, 0)
        self.assertIn("differs from this run's recorded delegation ask-agent; rerun without --delegation",
                      retry.stderr)
        self.assertEqual(self.cli(*args).returncode, 0)
        default_root = self.base / "default-workspace"
        started = self.cli("workspace", "start", "--repo", self.repo, "--workspace-root", default_root,
                           "--prompt", "Default workspace delegation.")
        self.assertEqual(started.returncode, 0, started.stderr)
        self.assertEqual(store.read_record(default_root / "run/state.md")["delegation"], "inline")

    def test_graph_dry_run_defaults_to_new_run_delegation(self):
        default = self.cli("graph-dry-run", "--scenario", "delivery", "--format", "markdown")
        self.assertEqual(default.returncode, 0, default.stderr)
        # Inner packets open with "Delegation: inline: ..." (the two-line preamble, re-cut 2026-10-11).
        self.assertIn("Delegation: inline: do this stage here", default.stdout)
        delegated = self.cli("graph-dry-run", "--scenario", "delivery", "--format", "markdown",
                             "--delegation", "ask-agent")
        self.assertEqual(delegated.returncode, 0, delegated.stderr)
        self.assertIn("Prefer a native fresh worker", delegated.stdout)


if __name__ == "__main__":
    unittest.main()
