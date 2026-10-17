#!/usr/bin/env python3
"""The packet re-cut's own rules (owner, 2026-10-11; docs/shiploop-packet-recut-2026-10-11.md), checked by behaviour.

The wording pins in other suites show where each sentence went; these tests check the rules themselves:
- an Improve packet is two instructions, the improve skill with a literal example and then the done command, and
  ShipLoop binds its recorded card, writes the opening, starts the child and writes the handoff the skill reads;
- no producer packet mentions an upcoming Improve;
- every stage's goal is an action that names where its output goes;
- every "duty items n-m" a loop Work line cites exists in that stage's duty;
- no packet states a long sentence twice;
- producer and Improve packets stay under the ceilings measured when the re-cut landed;
- the owner rule and the pointer to the run's master index are the two lines under every packet's first line
  (owner, 2026-10-16);
- the helper that finds those lines by label (test/shiploop_packet_view.py) fails on a packet whose callback sits below
  its goal and on a lookup that finds nothing.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
sys.path.insert(0, str(ROOT / "test/shiploop_e2e"))
sys.path.insert(0, str(ROOT / "test"))
import packets  # noqa: E402
import shiploop_head_budget as budget  # noqa: E402
import shiploop_loops as loops  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_packet_view as packet_view  # noqa: E402
from shiploop_packet_view import assert_top_block  # noqa: E402

CORE = types.SimpleNamespace(PACKAGE_ROOT=ROOT / "skills/shiploop", REF_DIR=ROOT / "skills/shiploop/references")
CASES = {name: case for name, case in json.loads((ROOT / "test/shiploop_e2e/step_cases.json").read_text()).items()
         if not name.startswith("_")}
MODES = [(delegation, review, passes) for delegation in prompts.DELEGATIONS for review in ("stage", "none")
         for passes in prompts.BACKCHAIN_PASSES_MODES]
# Ceilings in characters for the offline node-fix-bug inner loop, set from its sizes when the re-cut landed plus about
# 10% headroom: a packet that grows past one is the repetition the re-cut removed coming back. Raise one only with
# a recorded reason (a new obligation), never to make room for a restatement.
PRODUCER_CEILING = 33_000
IMPROVE_CEILING = 3_000


def _offline(case: str = "node-fix-bug") -> dict[str, str]:
    return packets.offline_packets(CASES[case])


class ImprovePacketTests(unittest.TestCase):
    """An Improve run is "just calling the improve skill and then, once complete, invoking the done activity"."""

    def _bound_state(self, temp: str) -> tuple[Path, dict]:
        card = prompts.installed_improve_card()
        if not card.is_file():
            self.skipTest("no installed Improve card beside this ShipLoop package: " + str(card))
        run = Path(temp) / "run"
        run.mkdir()
        state = navigator.new_state(temp, "Add a greeting.", delegation="inline", improve_skill=str(card))
        while navigator.current_stage(state) != "spec":
            action = navigator.current_action(state)["id"]
            state = navigator.apply(state, action, {"outcome": "done", "summary": "Synthetic"})
        state = navigator.apply(state, navigator.current_action(state)["id"],
                                {"outcome": "done", "summary": "Synthetic spec"})
        self.assertIsNotNone(state.get("active_improve"), "spec should start a planning Improve child")
        self.assertIsNone(state["active_improve"]["skill"])
        bound, writes = navigator._improve_entry(run, state)
        return run, bound

    def _started_state(self, temp: str) -> tuple[Path, dict]:
        """The state after ShipLoop's own transition into the Improve stage: bound, opening written, child started."""
        card = prompts.installed_improve_card()
        if not card.is_file():
            self.skipTest("no installed Improve card beside this ShipLoop package: " + str(card))
        run = Path(temp) / "run"
        run.mkdir()
        state = navigator.new_state(temp, "Add a greeting.", delegation="inline", improve_skill=str(card))
        navigator.save(run, state)
        while navigator.current_stage(state) != "spec":
            state = navigator.apply(state, navigator.current_action(state)["id"],
                                    {"outcome": "done", "summary": "Synthetic"})
        before = state
        after = navigator.apply(state, navigator.current_action(state)["id"],
                                {"outcome": "done", "summary": "Synthetic spec"})
        after, writes, _payload = navigator._transition(CORE, run, before, after)
        navigator.save(run, after, writes)
        return run, after

    def test_shiploop_binds_the_recorded_card_at_the_transition(self) -> None:
        with tempfile.TemporaryDirectory(prefix="recut-improve-") as temp:
            _run, state = self._bound_state(temp)
            self.assertIsNotNone(state["active_improve"]["skill"])
            self.assertEqual(state["improve_skill"], state["active_improve"]["skill"]["skill_card"])

    def test_an_unresolvable_card_leaves_the_child_unbound_and_the_packet_prints_the_bind_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="recut-improve-") as temp:
            run = Path(temp) / "run"
            run.mkdir()
            state = navigator.new_state(temp, "Add a greeting.", delegation="inline",
                                        improve_skill=str(Path(temp) / "missing" / "SKILL.md"))
            while state.get("active_improve") is None:
                state = navigator.apply(state, navigator.current_action(state)["id"],
                                        {"outcome": "done", "summary": "Synthetic"})
            unbound, writes = navigator._improve_entry(run, state)
            self.assertIsNone(unbound["active_improve"]["skill"])
            self.assertEqual(writes, {})
            packet = navigator.render(None, run, unbound)
            self.assertIn("improve-bind", packet)
            self.assertNotIn("/improve ShipLoop Improve:", packet)

    def test_the_packet_is_two_instructions_with_a_literal_example(self) -> None:
        with tempfile.TemporaryDirectory(prefix="recut-improve-") as temp:
            run, state = self._started_state(temp)
            packet = navigator.render(None, run, state)
            child = state["active_improve"]
            handoff = navigator.improve_handoff_path(child)
            improve_id = navigator.improve_id(state)
            self.assertTrue(packet.startswith("ShipLoop navigator | improve | revision "), packet.splitlines()[0])
            self.assertIn("1. Run the improve skill on the spec result.", packet)
            self.assertIn("       /improve " + navigator.IMPROVE_ARGUMENT_PREFIX + str(handoff), packet)
            self.assertRegex(packet, r"(?m)^2\. When the improve skill has completed, run: .* complete .*--action="
                             + re.escape(improve_id))
            self.assertNotIn("improve-complete", packet)
            # ShipLoop started the child: the packet asks for no start, no restart, no opening.
            self.assertNotIn("improve-start", packet)
            self.assertNotIn("--restart-stopped", packet)
            # Nothing else instructs: no goal, references, rules, result shapes or stage guidance.
            for absent in ("Goal:", "References (", "Rules", "Result template", "Current stage guidance",
                           "Checked by", "Done when", "opening file", "Write the opening"):
                self.assertNotIn(absent, packet, absent)
            # The hooks' machine lines stay.
            self.assertIn("Keepalive marker: ", packet)
            self.assertIn("=== ShipLoop status ===", packet)
            self.assertLess(len(packet), IMPROVE_CEILING)

    def test_shiploop_writes_the_opening_and_starts_the_child_at_the_transition(self) -> None:
        with tempfile.TemporaryDirectory(prefix="recut-improve-") as temp:
            _run, state = self._started_state(temp)
            child = state["active_improve"]
            self.assertEqual(state["stage"], "spec")                       # the reviewed action is still the producer's
            self.assertNotEqual(child["improve_action"], child["action_id"])
            opening = navigator.improve_opening_path(child)
            self.assertTrue(opening.is_file(), "ShipLoop writes opening.md itself")
            self.assertIn("## Current context and desired improvements", opening.read_text(encoding="utf-8"))
            import shiploop_standalone_improve as standalone
            receipt = standalone.receipt_path(child)
            self.assertTrue(opening.with_name("start.json").is_file())
            self.assertTrue(receipt.is_file(), "the bound runtime was started with --receipt packet.json")
            self.assertEqual(json.loads(receipt.read_text(encoding="utf-8")).get("status"), "active")

    def test_emit_writes_the_handoff_the_skill_reads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="recut-improve-") as temp:
            run, state = self._started_state(temp)
            navigator.save(run, state)
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                navigator.emit(None, run, state)
            child = state["active_improve"]
            text = navigator.improve_handoff_path(child).read_text(encoding="utf-8")
            self.assertIn(child["contract_marker"], text)        # how the improve skill knows it is a ShipLoop subcall
            self.assertIn("ShipLoop started this review", text)
            # The only improve-start the hand-off names is the restart of a stopped child.
            self.assertTrue(all("--restart-stopped" in line for line in re.findall(r"improve-start[^\n]*", text)))
            self.assertFalse(re.search(r"improve-start[^\n]*--opening", text), "no --opening")
            self.assertNotIn("improve-complete", text)
            self.assertIn(" complete --run-dir=", text)
            self.assertIn("improve-commit", text)


class NoAdvanceImproveTests(unittest.TestCase):
    def test_no_producer_prompt_mentions_improve(self) -> None:
        for stage in prompts.STAGES:
            for delegation, review, passes in MODES:
                with self.subTest(stage=stage, delegation=delegation, review=review, passes=passes):
                    text = prompts.prompt(stage, delegation=delegation, planning_review=review,
                                          backchain_passes=passes)
                    self.assertNotRegex(text, r"\bImprove\b")

    def test_no_producer_packet_announces_an_improve_child(self) -> None:
        for key, text in _offline().items():
            if key.endswith("-improve"):
                continue
            with self.subTest(packet=key):
                self.assertNotIn("starts this action's Improve child", text)
                self.assertNotIn("Improve child's context", text)
                self.assertNotRegex(text, r"(?m)^Improve: ")


class ActionGoalTests(unittest.TestCase):
    # A goal names where its outcome goes: a result field in backticks, a knowledge or run file, or the product.
    OUTPUT = re.compile(r"`[a-z_]+`|HOME/|RUN/|WORKTREE|\b(spec|environment|architecture)\.md\b|evidence_refs|"
                        r"\bsummary\b|\bresult\b|checkout|repository|commit")

    def test_every_goal_is_one_action_that_names_its_output(self) -> None:
        for stage in prompts.STAGES:
            goal = stage_spec.stage(stage).goal
            with self.subTest(stage=stage):
                self.assertRegex(goal, r"^[A-Za-z]")
                self.assertRegex(goal, self.OUTPUT, goal)


class WorkLineTests(unittest.TestCase):
    def test_every_cited_duty_item_exists(self) -> None:
        for stage in stage_spec.INNER:
            duty = prompts.duty(stage, delegation=prompts.INLINE)
            items = {int(n) for n in re.findall(r"(?m)^(\d+)\. ", duty)}
            work = str(loops.WORK.get(stage, "")) if hasattr(loops, "WORK") else ""
            for first, last in re.findall(r"duty items (\d+)(?:-|–| to )(\d+)", work):
                with self.subTest(stage=stage, cited=first + "-" + last):
                    for number in range(int(first), int(last) + 1):
                        self.assertIn(number, items)


class OneHomeTests(unittest.TestCase):
    def test_no_packet_states_a_long_sentence_twice(self) -> None:
        for name in CASES:
            for key, text in _offline(name).items():
                prose = " ".join(line for line in text.splitlines() if not line.startswith("  | "))
                sentences = [s.strip() for s in re.split(r"(?<=[.;:])\s+", " ".join(prose.split()))
                             if len(s.strip()) > 80]
                repeated = sorted({s for s in sentences if sentences.count(s) > 1})
                with self.subTest(case=name, packet=key):
                    self.assertEqual(repeated, [])

    def test_packets_stay_under_the_ceilings(self) -> None:
        for key, text in _offline().items():
            with self.subTest(packet=key):
                ceiling = IMPROVE_CEILING if key.endswith("-improve") else PRODUCER_CEILING
                self.assertLess(len(text), ceiling)


class PrintedHeadTests(unittest.TestCase):
    """What a reader of the printed text alone sees (owner, 2026-10-16).

    A packet longer than PRINT_LIMIT prints a head and keeps the rest in its file.  Measured on node-fix-bug at 2686b427,
    the head of all five such packets left out the stage's duties and rules, which began at 10,400 to 15,000 characters
    of the file, so a model that read only what was printed never saw what to do.

    Length is checked against the journaled value of each stage (``test/shiploop_e2e/head_table.json``), at a reference
    install, so a head cannot grow unnoticed and the result does not move with the machine's paths
    (``shiploop_head_budget``: the head's own budget decisions are made at that install too).  A head above the
    ~20,000-character cut some hosts apply is a recorded gap in that table (``over_the_cut``); none is, since the print
    order of the efficiency plan (U7): every head fits."""

    def check_length(self, route: str, key: str, printed: str, whole: str) -> None:
        stage = key.split("-", 1)[1]
        mode = "whole" if budget.at_reference_install(whole) <= navigator.PRINT_LIMIT else "head"
        length = budget.at_reference_install(printed)
        self.assertLessEqual(length, budget.ceiling(route, stage, mode),
                             f"{route} {stage} printed as a {mode} is {length} characters at the reference install: above its "
                             f"journaled value; raise it in head_table.json with the reason, or shorten the packet")
        if stage not in budget.known_over_the_cut(route):
            self.assertLess(length, budget.HOST_CUT, f"{route} {stage} crosses the host's output cut and is not a recorded gap")

    def test_the_printed_text_of_every_producer_packet_holds_its_duties(self) -> None:
        with budget.reference_tmpdir():
            printed = packets.offline_packets(CASES["node-fix-bug"], printed=True, measure_for=budget.reference_measure)
            full = _offline()
        over = [key for key, text in full.items() if len(text) > navigator.PRINT_LIMIT and not key.endswith("-improve")]
        self.assertGreaterEqual(len(over), 4, "the case no longer has packets over the limit: pick a larger one")
        for key, text in printed.items():
            if key.endswith("-improve"):
                continue
            with self.subTest(packet=key):
                self.assertIn("Current stage guidance:", text)
                self.assertIn("\nRULES ", text)  # the duties' own closing rules came with them
                self.check_length("inline", key, text, full[key])

    def test_the_status_block_ends_inside_the_status_hooks_window_and_leads_the_duties(self) -> None:
        import shiploop_status_hook as hook
        for key, text in packets.offline_packets(CASES["node-fix-bug"], printed=True).items():
            if key.endswith("-improve"):
                continue
            with self.subTest(packet=key):
                end = text.index("=== end ShipLoop status ===")
                self.assertLess(end + len("=== end ShipLoop status ==="), hook.WINDOW)
                self.assertLess(end, text.index("Current stage guidance:"))

    def test_the_ask_agent_route_keeps_the_duties_and_the_status_window_and_no_head_is_over_the_cut(self) -> None:
        """Before the print-order unit (efficiency plan U7) the opt-in ask-agent route's step-plan head was about 22,300
        characters at the reference install, above the ~20,000 some hosts cut at (inline: 20,600), and Grok showed only the
        first and last ~10,000 of it (journal, LP-1).  One ordered list now puts the lookups last and leaves out what does
        not fit, so every head of both routes fits."""
        import shiploop_status_hook as hook
        with budget.reference_tmpdir():
            printed = packets.offline_packets(CASES["node-fix-bug"], delegation="ask-agent", printed=True,
                                              measure_for=budget.reference_measure)
            whole = packets.offline_packets(CASES["node-fix-bug"], delegation="ask-agent")
        self.assertEqual(budget.known_over_the_cut("ask-agent"), [])
        for key, text in printed.items():
            if key.endswith("-improve"):
                continue
            with self.subTest(packet=key):
                self.assertIn("Current stage guidance:", text)
                self.assertLess(text.index("=== end ShipLoop status ==="), hook.WINDOW)
                self.check_length("ask-agent", key, text, whole[key])

    def test_a_head_that_would_pass_the_host_cut_drops_the_quoted_knowledge_not_the_duties(self) -> None:
        """The quoted knowledge files and hand-offs are the last thing a head carries, and only while the head stays within
        the host's cut (efficiency plan U7; before it, while the head stayed within PRINT_LIMIT): else one line says they
        are in the packet file.  The duties and the rules are never dropped."""
        with budget.reference_tmpdir():
            heads = packets.offline_packets(CASES["node-fix-bug"], printed=True, measure_for=budget.reference_measure)
        for key, text in heads.items():
            if "Full packet:" not in text:
                continue
            with self.subTest(packet=key):
                quoted = ("Knowledge files this stage reads, each quoted whole" in text
                          or "Handed off by earlier stages, quoted by value" in text)
                stub = "in the full packet, each quoted whole" in text
                self.assertNotEqual(quoted, stub, "a head quotes the files or says where they are, not both and not neither")
                self.assertIn("Current stage guidance:", text)
                self.assertIn("Never end the turn while a ShipLoop command is still running.", text)


class OwnerLinesTests(unittest.TestCase):
    """The owner, 2026-10-16: "the first line of each packet should say something like: read this file if you don't have
    context about prior paths and what you're doing, or if you're uncertain in any way ... be clear at the top of each
    packet about where the master reference index is".  Measured in the Salesforce chess run: the model never opened the
    run's context-index.md (0 reads across five compactions) although a mid-packet line named it, so the pointer moved
    under the first line and the mid-packet line went."""

    POINTER = re.compile(r"^Lost context, or unsure of anything about this run\? Read (/\S+/context-index\.md) first: "
                         r"it maps every file of this run and what it holds; open the file you need from there\.$")

    def check(self, text: str, label: str) -> None:
        # Both lines under the header, in order (found by constant and label, not by line number: shiploop_packet_view).
        view = assert_top_block(self, text, require=("owner", "pointer"), label=label)
        self.assertRegex(view["pointer"], self.POINTER, label)
        # Once each, and the old mid-packet line is gone (nothing says the pointer twice).
        self.assertEqual(text.count("Owner rule:"), 1, label)
        self.assertEqual(text.count("Lost context, or unsure"), 1, label)
        self.assertEqual(text.count("context-index.md"), 1, label)
        self.assertNotIn("Run context index", text, label)

    def test_every_offline_packet_has_both_lines_directly_under_its_header_once(self) -> None:
        seen = 0
        for delegation in prompts.DELEGATIONS:
            for printed in (False, True):
                for key, text in packets.offline_packets(CASES["node-fix-bug"], delegation, printed=printed).items():
                    with self.subTest(delegation=delegation, printed=printed, packet=key):
                        self.check(text, key)
                        seen += 1
        self.assertGreater(seen, 40)  # inner producers and Improve packets, both routes, whole and printed

    def test_the_constants_are_defined_once_and_the_pointer_takes_the_path(self) -> None:
        self.assertEqual(prompts.OWNER_RULE,
                         "Owner rule: concise and exact; no restating. Keep every command, path, ID and expected value.")
        self.assertEqual(prompts.index_pointer("/r/run/context-index.md"),
                         "Lost context, or unsure of anything about this run? Read /r/run/context-index.md first: it maps "
                         "every file of this run and what it holds; open the file you need from there.")
        scripts = ROOT / "skills/shiploop/scripts"
        for needle in ("Owner rule: concise and exact", "Lost context, or unsure of anything"):
            homes = sorted(path.name for path in scripts.glob("*.py") if needle in path.read_text(encoding="utf-8"))
            self.assertEqual(homes, ["shiploop_prompts.py"], needle)

    def test_the_lines_reach_every_kind_of_packet_a_run_prints(self) -> None:
        """Producers of every stage, the Improve packet (unbound and started), and the paused, halted and done packets."""
        import shiploop_navigator_dry_run as dry_run
        state = navigator.new_state("/simulation-only/repo", "Owner lines fixture.", delegation="inline")
        stages, improves = set(), 0
        for step in dry_run.activity():
            action = navigator.current_action(state)["id"]
            stage = navigator.current_stage(state)
            if step["command"] == "produce":
                stages.add(stage)
                self.check(navigator.render(dry_run.CORE, dry_run.RUN, state), stage)
                state = navigator.apply(state, action, step["result"])
                if state.get("active_improve") is not None:  # the unbound Improve packet (improve-bind)
                    improves += 1
                    self.check(navigator.render(dry_run.CORE, dry_run.RUN, state), stage + " improve")
            else:
                state = navigator.finish_improve(state, action, step["receipt"], step.get("final_result"))
        self.assertEqual(stages, set(stage_spec.STAGES))
        self.assertGreater(improves, 5)
        self.assertEqual(state["status"], "done")
        self.check(navigator.render(dry_run.CORE, dry_run.RUN, state), "done")
        fresh = navigator.new_state("/simulation-only/repo", "Owner lines fixture.", delegation="inline")
        self.check(navigator.render(dry_run.CORE, dry_run.RUN, navigator.control(fresh, "pause", "The user asked.")), "paused")
        self.check(navigator.render(dry_run.CORE, dry_run.RUN, navigator.control(fresh, "halt", "The user stopped.")), "halted")

    def test_a_started_improve_packet_has_both_lines_and_stays_under_its_ceiling(self) -> None:
        with tempfile.TemporaryDirectory(prefix="recut-owner-") as temp:
            run, state = ImprovePacketTests()._started_state(temp)
            packet = navigator.render(None, run, state)
            self.check(packet, "started improve")
            self.assertLess(len(packet), IMPROVE_CEILING)
            self.assertEqual(navigator.improve_packet(None, run, state), packet)

    def test_the_pointer_names_the_real_index_and_emit_leaves_that_file_on_disk(self) -> None:
        import contextlib
        import io
        with tempfile.TemporaryDirectory(prefix="recut-owner-") as temp:
            run = Path(temp) / "run"
            run.mkdir()
            state = navigator.new_state(temp, "Owner lines fixture.", delegation="inline")
            index = run / "context-index.md"
            for saved in (True, False):
                if saved:
                    navigator.save(run, state)
                else:
                    index.unlink()  # a run saved without the file (the index is derived, so emit makes it again)
                self.assertEqual(index.exists(), saved)
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    navigator.emit(CORE, run, state)
                self.assertTrue(index.is_file())
                view = assert_top_block(self, out.getvalue(), require=("owner", "pointer"))
                self.assertEqual(view["pointer"], prompts.index_pointer(index))
                self.assertIn(f"revision {state['revision']}", index.read_text(encoding="utf-8"))


class ImproveInvocationTests(unittest.TestCase):
    _started_state = ImprovePacketTests._started_state
    """Owner, 2026-10-16: the last live run invoked the improve skill for 1 of 4 Improve stages, because the handoff said to
    read the skill once per context.  The packet now says to invoke it at every Improve stage."""

    def test_the_improve_packet_says_to_invoke_the_skill_at_every_improve_stage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="recut-improve-") as temp:
            run, state = self._started_state(temp)
            packet = navigator.render(CORE, run, state)
        self.assertIn("at every Improve stage and not from memory of an earlier one", packet)
        # the lines the readers match on are unchanged
        self.assertRegex(packet, r"(?m)^1\. Run the improve skill on the .+ result\. For example, on Claude Code:$")
        self.assertRegex(packet, r"(?m)^\s+/improve ShipLoop Improve: .+/handoff\.md$")
        self.assertRegex(packet, r"(?m)^2\. When the improve skill has completed, run: ")


class TopBlockHelperTests(unittest.TestCase):
    """NEGATIVE self-test of test/shiploop_packet_view.py (efficiency plan, test-economy review rows 2 and 5): the helper
    that five suites use to find a packet's top block by label must fail on a wrong order and on a lookup that finds
    nothing.  A helper whose label lookup silently finds nothing would pass all five vacuously."""

    @classmethod
    def setUpClass(cls) -> None:
        found = packets.offline_packets(CASES["node-fix-bug"])
        cls.lines = found["08-test"].splitlines()

    def fails(self, lines, expect: str, **kwargs):
        """The helper raises on ``lines`` and its message names ``expect``."""
        with self.assertRaises(AssertionError) as caught:
            assert_top_block(self, lines, **kwargs)
        self.assertIn(expect, str(caught.exception))

    def test_a_real_packet_passes_and_the_view_names_each_part_in_order(self) -> None:
        view = assert_top_block(self, self.lines, require=("owner", "pointer", "callback", "goal", "done_when"))
        self.assertEqual(sorted(view.at, key=view.at.get), list(packet_view.TOP_ORDER))
        self.assertEqual(view["owner"], prompts.OWNER_RULE)
        self.assertTrue(view["callback"].startswith("Callback for this stage"))

    def test_a_callback_moved_below_the_goal_fails(self) -> None:
        view = packet_view.top_block(self.lines)
        lines = list(self.lines)
        callback = lines.pop(view.index("callback"))
        lines.insert(view.index("goal"), callback)  # the goal's old index is now the line after it: callback below Goal
        self.assertLess(packet_view.top_block(lines).index("goal"), packet_view.top_block(lines).index("callback"))
        self.fails(lines, "callback", require=("callback", "goal"))

    def test_an_owner_rule_or_pointer_out_of_order_fails(self) -> None:
        view = packet_view.top_block(self.lines)
        swapped = list(self.lines)
        owner, pointer = view.index("owner"), view.index("pointer")
        swapped[owner], swapped[pointer] = swapped[pointer], swapped[owner]
        self.fails(swapped, "owner")
        below = list(self.lines)
        below.insert(view.index("callback") + 1, below.pop(view.index("pointer")))  # the pointer below the callback
        self.fails(below, "pointer")

    def test_a_part_that_is_required_and_not_found_fails_never_passes(self) -> None:
        view = packet_view.top_block(self.lines)
        for part in ("owner", "pointer", "callback", "goal", "done_when"):
            with self.subTest(part=part):
                lines = [line for number, line in enumerate(self.lines) if number != view.index(part)]
                self.fails(lines, "has no " + part + " line", require=("owner", "pointer", "callback", "goal", "done_when"))
        self.fails(self.lines[view.index("header") + 1:], "no line starts with")   # no header at all
        self.fails(self.lines, "is not a part of the top block", require=("calback",))  # a misspelt part is refused
        with self.assertRaises(AssertionError):
            packet_view.top_block(self.lines).find("a line no packet prints")

    def test_a_callback_that_sank_out_of_the_top_block_fails_even_without_a_goal(self) -> None:
        view = packet_view.top_block(self.lines)
        # A packet with no goal (the bound Improve packet is one): only the bound can say the callback left the top.
        lines = [line for number, line in enumerate(self.lines) if number not in (view.index("goal"), view.index("done_when"))]
        callback = lines.pop(view.index("callback"))
        lines.insert(view.index("header") + packet_view.TOP_WINDOW + 5, callback)
        self.fails(lines, "not within", require=("owner", "pointer", "callback"))
        assert_top_block(self, lines, require=("owner", "pointer", "callback"), within=None)  # the bound is the only failure

    def test_a_line_inserted_between_the_parts_is_tolerated(self) -> None:
        """The later layouts add lines (a recovery pointer, a Full packet pointer, a style slot) between the parts: the
        order holds and nothing addresses a line, so nothing fails."""
        view = packet_view.top_block(self.lines)
        lines = list(self.lines)
        lines.insert(view.index("pointer") + 1, "A line a later layout adds under the pointer.")
        lines.insert(view.index("header") + 1, "A line a later layout adds under the header.")
        assert_top_block(self, lines, require=("owner", "pointer", "callback", "goal", "done_when"))

    def test_a_reported_outcome_the_stage_does_not_accept_is_found(self) -> None:
        """named_outcomes reads only 'report <outcome>' and 'Report outcome <outcome>'; unaccepted_outcomes compares them
        with the stage table (no outcome word is listed in the helper)."""
        self.assertEqual(packet_view.named_outcomes("Report outcome replan now; or report blocked; report it, reported."),
                         ["replan", "blocked"])
        self.assertTrue({"done", "blocked", "revise", "replan"} <= packet_view.OUTCOME_WORDS)
        self.assertEqual(packet_view.unaccepted_outcomes("test", "Report outcome replan now."), ["replan"])
        self.assertEqual(packet_view.unaccepted_outcomes("system-test", "report revise rather than retrying it"), ["revise"])
        self.assertEqual(packet_view.unaccepted_outcomes("test", "report revise, or report blocked"), [])
        self.assertEqual(packet_view.unaccepted_outcomes("system-test", "no instruction to report anything"), [])


if __name__ == "__main__":
    unittest.main()
