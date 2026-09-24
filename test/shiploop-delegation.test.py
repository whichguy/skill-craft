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
import shiploop_store as store  # noqa: E402

# Instructions that route work to a delegated executor.  Inline packets may
# name Ask Agent only to forbid it, so these are the positive route phrases.
DELEGATED_ROUTE_TEXT = (
    "Prefer a native fresh worker",
    "run the host-selected improve-agent card",
    "ask-agent/consumer-owned-workspace/v1",
    "Workspace route: consumer-owned",
    "Native owner record:",
    "bind this action to the default parallel",
    "Parallel-chain guide:",
    "for the default parallel chain",
)
# Delegated wording that only bound Improve packets or duties can carry.
BOUND_DELEGATED_TEXT = DELEGATED_ROUTE_TEXT + (
    "dispatch step",
    "every worker",
    "source-bound parent update",
    "parallel or serial execution graph",
)


def bound_walk(repo, delegation, protocol_version=3):
    """Render every producer and its bound ephemeral Improve packet for one item."""
    selected = standalone.resolve_skill(str(CARD))
    state = nav.new_state(str(repo), "Synthetic bound walk.", protocol_version=protocol_version,
                          delegation=delegation)
    run = Path(repo).parent / ("run-" + str(delegation) + "-" + str(protocol_version))
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
                                                         child["seed_result"], selected)
            packets.append((stage, "improve", nav.render(None, run, state)))
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

    def state(self, delegation="inline", protocol_version=3):
        return nav.new_state("/simulation-only/repo", "Synthetic delegation request.",
                             protocol_version=protocol_version, delegation=delegation)

    def render(self, state):
        return nav.render(None, self.run, state)

    def test_every_run_records_delegation_and_a_run_without_it_is_refused(self):
        default = nav.new_state("/r", "Synthetic.", protocol_version=3)
        self.assertEqual((default["delegation"], nav.delegation(default)), ("inline", "inline"))
        # A run saved before the setting existed is not routed through ask-agent.
        unrecorded = dict(default)
        del unrecorded["delegation"]
        with self.assertRaises(nav.NavigatorError) as caught:
            nav.validate(unrecorded)
        self.assertIn("navigator state has no recorded delegation", str(caught.exception))
        self.assertIn("fresh --run-dir", str(caught.exception))
        for version in (3, 4):
            for value in ("inline", "ask-agent"):
                with self.subTest(version=version, value=value):
                    state = self.state(value, version)
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

    def test_inline_clears_once_per_work_item_then_continues_in_context(self):
        state = self.state()
        self.assertTrue(self.render(state).startswith("ShipLoop navigator | intake |"))
        state = advance(state, "select-work")
        entry = self.render(state)
        self.assertTrue(entry.startswith("Clear and then execute the prompt.\n\nDelegation: inline."))
        self.assertIn("Clear once here", entry)
        self.assertIn("already fresh: when this prefix repeats", entry)
        self.assertIn("Pause without consuming the action:", entry)
        # step-plan is a planning-review stage, so completing it starts an
        # actual Improve child (select-work itself no longer does).
        improve = self.render(advance(state, "step-plan", stop_after_apply=True))
        self.assertTrue(improve.startswith(
            "Keep the invoking parent alive and run this Improve invocation inline.\n"))
        for stage in ("step-plan", "implement", "carry-forward"):
            with self.subTest(stage=stage):
                packet = self.render(advance(state, stage))
                self.assertTrue(packet.startswith("Continue in this context and execute the prompt.\n"))
                self.assertIn("context boundary was its select-work", packet)

    def test_inline_implement_runs_reviewed_steps_directly_without_a_chain(self):
        inline = self.render(advance(self.state(), "implement"))
        self.assertIn("Delegation is inline: execute a reviewed multi-step plan directly", inline)
        step_plan = self.render(advance(self.state(), "step-plan"))
        self.assertIn("record its ordered steps here", step_plan)
        self.assertIn("Each reviewed step's task/ready/done criteria", step_plan)
        for packet in (inline, step_plan):
            for text in DELEGATED_ROUTE_TEXT:
                self.assertNotIn(text, packet)

    def test_no_inline_packet_in_a_full_walk_routes_work_to_a_delegate(self):
        for version in (3, 4):
            scenarios = dry_run.scenarios()
            report = dry_run.run_scenario("delivery", scenarios["delivery"],
                                          protocol_version=version, delegation="inline")
            self.assertTrue(report["ok"], report.get("error"))
            for event in report["events"]:
                for text in DELEGATED_ROUTE_TEXT:
                    self.assertNotIn(text, event["prompt"], (version, event["from"], text))

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
        self.assertEqual(pending.split("\n\n", 1)[0], "Clear and then execute the prompt.")
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
        self.assertIn("Keep the invoking parent alive and follow Improve's selected context ownership.",
                      held_child)
        lines = held_child.splitlines()
        callback = lines[lines.index(change) + 1]
        # The parked child is unbound, so its one legal callback is improve-bind.
        self.assertTrue(callback.startswith("Next command (bind the selected Improve card"), callback)
        self.assertIn(" improve-bind ", callback)
        self.assertIn("--action=" + action, callback)
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


class PacketContractTests(DelegationStateTests):
    """Packet fields a fresh inline context needs, pinned on both routes where shared."""

    def test_producer_packets_state_outcomes_and_explicit_commands(self):
        entry = self.render(advance(self.state(), "select-work"))
        self.assertIn("Allowed outcomes: done | repeat | blocked.\nCall this when done:\n", entry)
        self.assertIn("Context-boundary pause (no callable host reset): ", entry)
        self.assertIn("'--reason=context-boundary: clear, then run Recovery and Resume'", entry)
        self.assertIn("Halt (terminal and irreversible; only on an explicit user stop): ", entry)
        # select-work is not a planning/checkpoint stage; it advances directly.
        self.assertIn("This result advances directly; no Improve child runs for this stage.", entry)
        self.assertNotIn("Context-boundary pause", self.render(advance(self.state(), "step-plan")))
        self.assertNotIn("Context-boundary pause", self.render(advance(self.state("ask-agent"), "select-work")))
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
        self.assertIn("ShipLoop skill card: " + str(card) + "\n", packet)
        self.assertTrue(card.is_file())
        step_plan = next(entry["action"] for entry in state["history"] if entry["stage"] == "step-plan")
        self.assertIn("Current item step-plan source action: " + step_plan, packet)
        self.assertIn("Current item test-decision source action:", packet)
        # Right after step-plan it is already the test-decision source; do not print it twice.
        test_spec = self.render(advance(self.state(), "test-spec"))
        self.assertNotIn("Current item step-plan source", test_spec)
        self.assertIn("Current item test-decision source action:", test_spec)
        self.assertNotIn("Current item step-plan source", self.render(advance(self.state(), "step-plan")))
        self.assertIn("Execute this packet in this conversation, submit its current callback yourself", packet)
        delegated = self.render(dict(state, delegation="ask-agent"))
        self.assertIn("Give the executing agent only the current action packet", delegated)
        self.assertIn("Current item step-plan source action: " + step_plan, delegated)

    def test_integrate_assembles_direct_or_chain_work(self):
        for route in ("inline", "ask-agent"):
            with self.subTest(route=route):
                text = " ".join(nav.guidance3.prompt("integrate", delegation=route).split())
                self.assertIn("confirm its finish commit is an ancestor of the execution checkout HEAD", text)
                self.assertIn("assemble or commit this item's candidate in the execution checkout", text)

    def test_final_result_must_list_the_reviewed_queue(self):
        receipt = {"summary": "Synthetic receipt; no review claim."}
        queue = [{"id": "W1", "title": "Reviewed item"}, {"id": "W2", "title": "Second item"}]
        for stage, proposal in (("plan", queue), ("carry-forward", [])):
            with self.subTest(stage=stage):
                state = advance(self.state(), stage)
                action = nav.current_action(state)["id"]
                waiting = nav.apply(state, action, {"outcome": "done", "summary": "Proposed.",
                                                    "work_items": proposal})
                self.assertIn("A done final_result must list the complete intended queue", self.render(waiting))
                with self.assertRaisesRegex(nav.NavigatorError, "must list the complete intended queue"):
                    nav.finish_improve(waiting, action, receipt, {"outcome": "done", "summary": "Revised."})
                # Non-done dispositions and an explicit queue are unaffected.
                nav.finish_improve(waiting, action, receipt, {"outcome": "repeat", "summary": "Redo."})
                nav.finish_improve(waiting, action, receipt,
                                   {"outcome": "done", "summary": "Revised.", "work_items": proposal})

    def test_bound_improve_packets_carry_only_their_route(self):
        with tempfile.TemporaryDirectory(prefix="shiploop-bound-walk-") as temp:
            repo = Path(temp).resolve() / "repo"
            repo.mkdir()
            inline = bound_walk(repo, "inline")
            delegated = bound_walk(repo, "ask-agent") + bound_walk(repo, "ask-agent", protocol_version=4)
            v4 = bound_walk(repo, "inline", protocol_version=4)
        self.assertEqual(len(inline), 42)
        for stage, kind, packet in inline + v4:
            for text in BOUND_DELEGATED_TEXT:
                self.assertNotIn(text, packet, (stage, kind, text))
            if kind == "improve":
                self.assertIn("Delegation: inline. Run the selected Improve card", packet)
                self.assertIn("start no reviewer, test-runner or executor agent unless the user asked for "
                              "independent review", packet)
        # Positive control: every phrase is live on the delegated route, so the
        # inline sweep above cannot pass merely because the wording changed.
        delegated_text = "\n".join(packet for _stage, _kind, packet in delegated)
        for text in BOUND_DELEGATED_TEXT:
            self.assertIn(text, delegated_text)

    def test_every_active_packet_leads_with_its_legal_callback_and_schedule_text(self):
        with tempfile.TemporaryDirectory(prefix="shiploop-callback-walk-") as temp:
            repo = Path(temp).resolve() / "repo"
            repo.mkdir()
            walks = {(route, version): bound_walk(repo, route, protocol_version=version)
                     for route, version in (("inline", 3), ("ask-agent", 3), ("ask-agent", 4),
                                            ("inline", 4))}
        planning = nav.guidance3.PLANNING_REVIEW_STAGES
        for (route, version), packets in walks.items():
            for stage, kind, packet in packets:
                with self.subTest(route=route, version=version, stage=stage, kind=kind):
                    # Producers stay within the cold-packet bound. A bound child adds
                    # its runtime contract (about 39,300 chars at most, before temp
                    # paths); the v4 initial plan child also carries the
                    # planning-experiment contract (about 44,700 chars; 43,500 in
                    # 0.22.0), so it alone gets a wider bound.
                    if kind == "produce":
                        bound = 40_000
                    elif version == 4 and stage == "plan":
                        bound = 46_000
                    else:
                        bound = 42_000
                    self.assertLess(len(packet), bound)
                    self.assertNotIn("Improve cadence", packet)
                    lines = packet.splitlines()
                    # An inline prefix may precede the header; nothing else may.
                    header = next(i for i, line in enumerate(lines)
                                  if line.startswith("ShipLoop navigator | "))
                    self.assertRegex(lines[header],
                                     r"^ShipLoop navigator \| " + re.escape(stage) + r" \| revision \d+$")
                    lead = lines[header + 1]
                    if kind == "produce":
                        self.assertTrue(lead.startswith("Callback for this stage "), lead)
                        done = lines[lines.index("Call this when done:") + 1]
                        self.assertEqual(shlex.split(lead.split("): ", 1)[1]), shlex.split(done))
                        if stage in planning:
                            self.assertIn("Improve: Every " + stage + " result, including blocked and "
                                          "repeat, starts this action's Improve child.", packet)
                        elif stage == "carry-forward":
                            self.assertIn("starts the run's single end-of-work Improve child", packet)
                        else:
                            self.assertIn("Improve: This result advances directly; no Improve child "
                                          "runs for this stage.", packet)
                        continue
                    self.assertTrue(lead.startswith("Callback for this Improve child "), lead)
                    argv = shlex.split(lead.split("): ", 1)[1])
                    self.assertEqual(argv[2], "improve-complete")
                    evidence = next(line for line in lines
                                    if line.startswith("Write completion evidence to: "))
                    self.assertIn("--result=" + evidence.split(": ", 1)[1], argv)
                    parent = next(i for i, line in enumerate(lines)
                                  if line.startswith(("Parent callback;", "Parent-only callback;")))
                    self.assertEqual(argv, shlex.split(lines[parent + 1]))
                    if stage == "carry-forward":
                        self.assertIn("End-of-work review: this is the run's single Improve", packet)
                        self.assertNotIn("Planning review focus", packet)
                    else:
                        self.assertIn(stage, planning)
                        self.assertIn("Planning review focus.", packet)
                        self.assertNotIn("End-of-work review", packet)


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
        return subprocess.run([sys.executable, "-B", str(CLI), *map(str, args)], cwd=self.base,
                              text=True, capture_output=True, timeout=60, env=self.env)

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
                          "--delegation", "ask-agent", "--navigator-version", "4")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(store.read_record(other / "state.md")["delegation"], "ask-agent")

    def test_removed_init_modes_are_rejected_before_creating_a_run(self):
        # The single home for rejecting removed init modes and protocol 2.
        for extra in (("--execution-mode", "navigator-v2"), ("--navigator-version", "2"),
                      ("--execution-mode", "navigator-v1"), ("--execution-mode", "managed"),
                      ("--execution-mode", "legacy")):
            for delegation in ((), ("--delegation", "inline")):
                with self.subTest(extra=extra, delegation=delegation):
                    result = self.init(*delegation, *extra)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertIn("invalid choice", result.stderr)
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
            self.assertEqual(self.cli("done", "--run-dir", self.run, "--action", action,
                                      "--result", result_path).returncode, 0)
        self.assertEqual(self.saved()["stage"], "spec")
        action = self.saved()["action"]["id"]
        result_path = self.run / "inbox" / (action + ".md")
        store.write_record(result_path, {"outcome": "done", "summary": "Synthetic spec."})
        self.assertEqual(self.cli("done", "--run-dir", self.run, "--action", action,
                                  "--result", result_path).returncode, 0)
        bound = self.cli("improve-bind", "--run-dir", self.run, "--action", action, "--skill-card", CARD)
        self.assertEqual(bound.returncode, 0, bound.stderr)
        switched = self.cli("delegation", "--run-dir", self.run, "--set", "ask-agent")
        self.assertEqual(switched.returncode, 0, switched.stderr)
        # The bound child keeps its inline route; later actions use ask-agent.
        self.assertIn("Delegation: inline. Run the selected Improve card", switched.stdout)
        self.assertIn("Delegation change: this action keeps inline", switched.stdout)
        self.assertEqual(self.saved()["delegation_hold"], {"action": action, "route": "inline"})

    def test_chain_bind_is_refused_on_inline_runs_before_any_side_effect(self):
        state = advance(nav.new_state(str(self.repo), "Synthetic chain refusal.", protocol_version=3,
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
        self.assertIn("Delegation: inline.", default.stdout)
        delegated = self.cli("graph-dry-run", "--scenario", "delivery", "--format", "markdown",
                             "--delegation", "ask-agent")
        self.assertEqual(delegated.returncode, 0, delegated.stderr)
        self.assertIn("Prefer a native fresh worker", delegated.stdout)


if __name__ == "__main__":
    unittest.main()
