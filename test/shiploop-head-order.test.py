#!/usr/bin/env python3
"""The order and the budget of what a packet prints (efficiency plan U7, rev 6 section 6.1 and the 2026-10-17 cut addendum).

One ordered list of blocks builds the printed head, the whole print and the packet file.  What this suite checks, on a
two-item run with multi-step plans through every stage of the graph (test/shiploop_head_plans.py):

- every print ends with the HEAD_END line, so a cut (a host's, or the model's own `head -N`) is detectable;
- the printed text of every stage, on both routes, is at most 20,000 characters at the normal install (an 83-character run
  directory, the 96-character CLI path of a plugin-cache install), and the required text of a head (the callback, goal,
  Until Loop block, status, duties and rules, the stage's own inputs and the result template; the two pointer lines are the
  second and third line of the top block, in every print and in the file) ends before character 19,500: what follows is what
  the packet file repeats whole;
- a head holds every token the stage needs, at 83 and at the 163 characters of a live run: the P0 tokens (what to do and how it
  is checked) and the P1 tokens (the stage's own input: the work item, the step with its paths, skills and check commands, the
  test floors and base-run rule, the rerun list and lint mode, the queue rule, the mismatch rows, the Improve lessons);
- Grok keeps the first and last ~10,000 characters of a print over 20,000 and drops the middle: whatever it drops holds no
  required token;
- the order of the blocks (plan 6.1), the status block inside the status hook's window, one Keepalive marker, no line the
  generator prints twice in a head.
"""
from __future__ import annotations

import contextlib
import io
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
import shiploop_head_plans as plans  # noqa: E402
import shiploop_loops as loops  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_packet_view as packet_view  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_status_hook as hook  # noqa: E402
import shiploop_store as store  # noqa: E402

CLI_PATH_LENGTH = 96          # a plugin-cache install: <root>/skills/shiploop/scripts/shiploop
INSTALL_RUN_DIR = 83          # the run directory a normal install has
LIVE_RUN_DIR = 163            # the run directory of the live run the plan was measured on
HOST_CUT = 20_000             # what Grok gives a model whole (measured 2026-10-17)
REQUIRED_BOUND = 19_500       # the required text of a head ends before it, at the normal install
GROK_PART = 10_000            # the first and the last characters Grok keeps of a longer print


def grok_view(text: str) -> str:
    """What Grok gives the model of a print: all of it up to 20,000 characters, else its first and last 10,000."""
    return text if len(text) <= HOST_CUT else text[:GROK_PART] + text[-GROK_PART:]


_RENDERS: dict = {}


def renders(delegation: str, run_dir_length: int, lint: str = "report") -> dict:
    """{key: row} of the two-item run at a stated install (cached: each walk costs a second)."""
    cache_key = (delegation, run_dir_length, lint)
    if cache_key not in _RENDERS:
        walk = lambda case, route, work, run_dir: plans.full_walk(case, route, work, run_dir, lint=lint)  # noqa: E731
        _RENDERS[cache_key] = packets.offline_renders(plans.CASE, delegation, run_dir_length=run_dir_length,
                                                      cli_path_length=CLI_PATH_LENGTH, walk=walk)
    return _RENDERS[cache_key]


def item_of(state) -> str | None:
    return state["work_items"][state["work_index"]]["id"] if navigator.current_stage(state) in stage_spec.INNER else None


def tokens(key: str, row: dict, delegation: str, seen: dict) -> tuple[list[str], list[str]]:
    """(P0 tokens, P1 tokens) an active producer's printed text must hold, written from the fixture and the stage table."""
    state = row["state"]
    stage = plans.stage_of(key)
    item = item_of(state)
    # The exit conditions are worded as the packet words them: the ask-agent route issues one implement action for every
    # step of a multi-step plan, so its conditions name those steps and their paths (``loops.worded_stage``).
    spec = loops.worded_stage(stage, navigator._implement_scope(state, stage))
    p0 = ["ShipLoop navigator | " + stage + " | revision ", prompts.RECOVERY_POINTER_PREFIX, prompts.PACKET_POINTER_PREFIX,
          "Callback for this stage (", " complete --run-dir=", "Goal: ", "Checked by: ", "Keepalive marker: SHIPLOOP-RUN run=",
          "=== ShipLoop status ===", "=== end ShipLoop status ===", "Current stage guidance:", "RULES (", "Result template:",
          "Allowed outcomes: ", "Fill the template: ", navigator.HEAD_END]
    if "=== ShipLoop narrative ===" in row["whole"]:  # the narrative prints at milestones only
        p0 += ["=== ShipLoop narrative ===", "=== end ShipLoop narrative ==="]
    p0 += [header[:48] for header in plans.duty_headers(stage, delegation)]
    if stage in loops.STAGES:
        p0 += ["Until Loop (no iteration limit", loops.ARGUMENT_BEGIN, loops.ARGUMENT_END, "\nWork: ",
               "Exit when ALL of these hold:", "Repeat while ", "\nContract: ", "\nReceipt: ",
               "until_loop_ephemeral.py start --receipt", "Result: when the Receipt",
               *(f"\n{number}. {condition}\n" for number, condition in enumerate(spec.done_when, 1))]
    else:
        p0 += ["Done when"]
    p1: list[str] = []
    if item is not None:
        entry = next(work for work in state["work_items"] if work["id"] == item)
        p1 += [f"Work item: {item} ({state['work_items'].index(entry) + 1}/{len(state['work_items'])}) — {entry['title'][:60]}",
               "Work item context: " + entry["context"][:60]]
    plan = plans.PLAN if item == "W1" else plans.SECOND_PLAN
    if stage == "implement" and delegation == "inline":
        index = seen.get((item, "implement"), 0)
        step = plan["steps"][index]
        p1 += [f"Step {step['id']} ({index + 1} of {len(plan['steps'])}), the only work for this packet: "
               + step["task"], "Step paths (change only these): " + ", ".join(step["paths"]),
               "Step skills (use each; the summary says whether you did): "
               + (", ".join(skill["name"] for skill in step["skills"]) or "none"),
               "Check commands (run each after every edit; exit codes to RUN/notes/<action>.md)",
               *(f"  {number}. {row_['command']}" for number, row_ in enumerate(
                   [command for command in plan["test_commands"] if command["suite"] == "check"], 1)),
               "Lint each implementation step (report-only): "]
    if stage == "test":
        p1 += ["A command passes only when it exits 0 and actually ran tests", "Each focused and regression command must also run at least its floor",
               "Base run: before the candidate run", "Lint this item's changes (report-only): "]
    if stage in ("document", "verify"):
        p1 += ["Step plan paths: " + ", ".join(plan["paths"])]
    if stage == "verify":
        p1 += ["Test rerun: on done, ShipLoop runs every test command",
               *(f"  {number}. [{command['suite']}] {command['command']}" for number, command in enumerate(plan["test_commands"], 1))]
    if stage == "validate-existing":
        p1 += ["ShipLoop ran each expectation's check", "E2 absent  the helper is not there yet", "DOES NOT MATCH, exit 1"]
    if stage == "carry-forward":
        p1 += ["Full ordered work queue: ", "Omit work_items to retain the future queue.", "Read every pending item's full title/context"]
    if state["history"] and state["history"][-1]["action"] in state["improve_results"]:
        p1 += ["Last accepted Improve lessons (", plans.LESSONS, "Prior Improve evidence and lessons: "]
    return p0, p1


def producers(delegation: str, run_dir_length: int, lint: str = "report"):
    """(key, row, p0, p1) for every active producer packet of the run, in order."""
    seen: dict = {}
    for key, row in renders(delegation, run_dir_length, lint).items():
        state = row["state"]
        if not plans.is_producer(key, state):
            continue
        stage = plans.stage_of(key)
        item = item_of(state)
        p0, p1 = tokens(key, row, delegation, seen)
        yield key, row, p0, p1
        seen[(item, stage)] = seen.get((item, stage), 0) + 1


class PrintedHeadTests(unittest.TestCase):
    def test_every_print_ends_with_head_end_and_none_is_empty(self) -> None:
        for delegation in ("inline", "ask-agent"):
            for key, row in renders(delegation, INSTALL_RUN_DIR).items():
                with self.subTest(route=delegation, packet=key):
                    self.assertTrue(row["printed"].endswith("\n" + navigator.HEAD_END + "\n"))
                    # as a line: the packet's second pointer line names the closing line inside a sentence, so the text
                    # appears twice in a producer's print and a cut print still shows it near the top
                    self.assertEqual(row["printed"].splitlines().count(navigator.HEAD_END), 1)

    def test_the_packet_file_never_carries_the_end_line_and_a_whole_print_is_the_file_plus_it(self) -> None:
        for delegation in ("inline", "ask-agent"):
            for key, row in renders(delegation, INSTALL_RUN_DIR).items():
                with self.subTest(route=delegation, packet=key):
                    self.assertNotIn(navigator.HEAD_END, row["whole"].splitlines())
                    if not row["head"]:
                        self.assertEqual(row["printed"], row["whole"] + navigator.HEAD_END + "\n")

    def test_the_printed_text_of_every_stage_fits_the_host_at_the_normal_install(self) -> None:
        for delegation in ("inline", "ask-agent"):
            for key, row in renders(delegation, INSTALL_RUN_DIR).items():
                with self.subTest(route=delegation, packet=key):
                    self.assertLessEqual(len(row["printed"]), HOST_CUT)

    def test_the_required_text_of_a_head_ends_before_the_bound_at_the_normal_install(self) -> None:
        for delegation in ("inline", "ask-agent"):
            for key, row, p0, p1 in producers(delegation, INSTALL_RUN_DIR):
                with self.subTest(route=delegation, packet=key):
                    text = row["printed"]
                    for token in [token for token in p0 + p1 if token != navigator.HEAD_END]:
                        self.assertIn(token, text)
                        # to the end of the line that holds it: the pointer lines end the required text
                        self.assertLessEqual(text.index("\n", text.index(token)), REQUIRED_BOUND, token)

    def test_a_head_holds_its_p0_and_p1_tokens_at_both_install_lengths(self) -> None:
        for delegation in ("inline", "ask-agent"):
            for length in (INSTALL_RUN_DIR, LIVE_RUN_DIR):
                for key, row, p0, p1 in producers(delegation, length):
                    with self.subTest(route=delegation, run_dir=length, packet=key):
                        for token in p0 + p1:
                            self.assertIn(token, row["printed"], token)

    OTHER_KINDS = {  # packet kind -> (a state test, the tokens its print must hold)
        "improve": (lambda key, state: state.get("active_improve") is not None,
                    ("ShipLoop navigator | improve | revision ", "Keepalive marker: SHIPLOOP-RUN run=", "=== ShipLoop status ===",
                     ("Next command (", "1. Run the improve skill on the"))),  # unbound card, or bound
        "paused": (lambda key, state: state["status"] == "paused",
                   ("ShipLoop navigator | ", "Paused, unfinished: ", "Resume: python3 ", "Keepalive marker: SHIPLOOP-RUN run=",
                    "=== ShipLoop status ===")),
        "halted": (lambda key, state: state["status"] == "halted",
                   ("ShipLoop navigator | ", "Halted, unfinished: ", "No completion callback is valid while halted.",
                    "Keepalive marker: SHIPLOOP-RUN run=", "=== ShipLoop status ===")),
        "done": (lambda key, state: state["status"] == "done",
                 ("ShipLoop navigator | ", "It's all complete.", "Report: ", "=== ShipLoop status ===")),
    }

    def test_improve_paused_halted_and_done_prints_hold_their_required_text_inside_the_bound(self) -> None:
        for delegation in ("inline", "ask-agent"):
            for length in (INSTALL_RUN_DIR, LIVE_RUN_DIR):
                found = dict.fromkeys(self.OTHER_KINDS, 0)
                for key, row in renders(delegation, length).items():
                    for kind, (is_kind, wanted) in self.OTHER_KINDS.items():
                        if not is_kind(key, row["state"]):
                            continue
                        found[kind] += 1
                        with self.subTest(route=delegation, run_dir=length, kind=kind, packet=key):
                            text = row["printed"]
                            self.assertLessEqual(len(text), HOST_CUT)
                            for token in wanted:
                                alternatives = token if isinstance(token, tuple) else (token,)
                                hit = next((one for one in alternatives if one in text), None)
                                self.assertIsNotNone(hit, token)
                                self.assertLessEqual(text.index(hit) + len(hit), REQUIRED_BOUND, token)
                self.assertTrue(all(found.values()), found)

    def test_the_lint_mode_line_reaches_the_verify_head_when_lint_is_off(self) -> None:
        for delegation in ("inline", "ask-agent"):
            printed = [row["printed"] for key, row in renders(delegation, INSTALL_RUN_DIR, "off").items()
                       if plans.stage_of(key) == "verify" and row["state"]["status"] == "active"]
            self.assertTrue(printed)
            for text in printed:
                self.assertIn("ShipLoop lint: off (run option lint=off)", text)

    def test_grok_view_of_a_print_over_the_cut_holds_every_required_token(self) -> None:
        """Grok drops the middle of a print over 20,000 characters.  Whatever it drops may hold lines the file repeats, never a
        P0 or P1 token: the check at the live install length, where the same stages are 1,400 characters longer."""
        over = 0
        for delegation in ("inline", "ask-agent"):
            for length in (INSTALL_RUN_DIR, LIVE_RUN_DIR):
                for key, row, p0, p1 in producers(delegation, length):
                    seen = grok_view(row["printed"])
                    over += len(row["printed"]) > HOST_CUT
                    with self.subTest(route=delegation, run_dir=length, packet=key):
                        for token in p0 + p1:
                            self.assertIn(token, seen, token)
        self.assertIsNotNone(over)  # recorded in the journal: how many prints are over at 163

    def test_grok_view_helper_keeps_the_first_and_last_ten_thousand(self) -> None:
        text = "a" * 10_000 + "b" * 500 + "c" * 10_000
        self.assertEqual(grok_view(text), "a" * 10_000 + "c" * 10_000)
        self.assertEqual(grok_view(text[:20_000]), text[:20_000])


class OrderTests(unittest.TestCase):
    """Plan 6.1: the blocks of an active producer packet in print order."""

    ORDER = ("ShipLoop navigator | ", "\n" + prompts.RECOVERY_POINTER_PREFIX, "\n" + prompts.PACKET_POINTER_PREFIX,
             "\nCallback for this stage (", "\n" + prompts.OWNER_RULE, "\nGoal: ", "Keepalive marker: ", "=== ShipLoop status ===",
             "Current stage guidance:", "\nRULES (", "Result template:", "\nFill the template: ", "\n" + navigator.HEAD_END)

    def test_the_blocks_of_every_head_and_whole_print_come_in_plan_order(self) -> None:
        for delegation in ("inline", "ask-agent"):
            for key, row, _p0, _p1 in producers(delegation, INSTALL_RUN_DIR):
                with self.subTest(route=delegation, packet=key):
                    for text in (row["printed"], row["whole"]):
                        positions = [text.find(token) for token in self.ORDER if token in text]
                        self.assertEqual(positions, sorted(positions))
                        # the head, the whole print and the file alike open with the pointers, the callback and the owner rule
                        self.assertEqual(sum(token in text for token in self.ORDER[:5]), 5)

    def test_the_callback_is_the_third_line_after_the_header_in_every_producer_print_and_file(self) -> None:
        """Plan 6.2: header, the next pointer, the Full packet pointer, then the callback label, within 1,500 characters of
        the header; at the normal install and at the live one, on both routes (a whole print and a file of an inner stage
        carry the delegation prefix before the header, which the position does not count)."""
        for delegation in ("inline", "ask-agent"):
            for length in (INSTALL_RUN_DIR, LIVE_RUN_DIR):
                for key, row, _p0, _p1 in producers(delegation, length):
                    for form in ("printed", "whole"):
                        with self.subTest(route=delegation, run_dir=length, packet=key, form=form):
                            packet_view.assert_callback_after_pointers(self, row[form])

    def test_the_commands_the_top_block_prints_are_commands_the_status_hook_reads_and_a_planted_pipe_is_not(self) -> None:
        """The callback label asks for the command exactly as printed, because the status display reads the command: the
        printed callback, its --check-only form, the next command of the first pointer line and the pause command all
        return a verb from the real hook, and the same commands behind a pipe return nothing."""
        for delegation in ("inline", "ask-agent"):
            for key, row, _p0, _p1 in producers(delegation, INSTALL_RUN_DIR):
                with self.subTest(route=delegation, packet=key):
                    text = row["whole"]
                    view = packet_view.top_block(text)
                    callback = view["callback"][len(prompts.CALLBACK_LABEL):]
                    following = view["pointer"][len(prompts.RECOVERY_POINTER_PREFIX):-len(prompts.RECOVERY_POINTER_SUFFIX)]
                    pause = next(line for line in text.splitlines() if line.startswith("Pause without consuming the action: "))
                    pause = pause.split(": ", 1)[1].split(" (only when", 1)[0]
                    self.assertEqual(hook._verb(callback), ("complete", None))
                    self.assertEqual(hook._verb(callback + " --check-only"), ("complete", None))
                    self.assertEqual(hook._verb(following), ("next", None))
                    self.assertEqual(hook._verb(pause), ("pause", None))
                    self.assertIsNone(hook._verb(callback + " | head -5"))
                    self.assertIsNone(hook._verb(following + " 2>&1 | tail -3"))
                    self.assertIsNone(hook._verb("R=" + str(Path(following.split("--run-dir=")[1])) + "; " + following))

    def test_the_loop_block_sits_between_the_goal_and_the_status_in_a_looped_stage(self) -> None:
        for delegation in ("inline", "ask-agent"):
            for key, row, _p0, _p1 in producers(delegation, INSTALL_RUN_DIR):
                if plans.stage_of(key) not in loops.STAGES:
                    continue
                with self.subTest(route=delegation, packet=key):
                    text = row["printed"]
                    self.assertLess(text.index("\nChecked by: "), text.index("Until Loop (no iteration limit"))
                    self.assertLess(text.index(loops.ARGUMENT_END), text.index("Keepalive marker: "))
                    # the start command follows the argument: the layout the Until Loop unit changes (its position test
                    # tightens this to the first 14 lines after the header)
                    header = text.index("ShipLoop navigator | ")
                    start = text.index("until_loop_ephemeral.py start --receipt")
                    self.assertLessEqual(text.count("\n", header, start), 40)

    def test_the_status_block_ends_inside_the_status_hooks_window(self) -> None:
        for delegation in ("inline", "ask-agent"):
            for length in (INSTALL_RUN_DIR, LIVE_RUN_DIR):
                for key, row, _p0, _p1 in producers(delegation, length):
                    with self.subTest(route=delegation, run_dir=length, packet=key):
                        end = row["printed"].index("=== end ShipLoop status ===") + len("=== end ShipLoop status ===")
                        self.assertLess(end, hook.WINDOW)
                        if hook.NARRATIVE_BEGIN in row["printed"]:  # the hook reads the milestone narrative from the same window
                            self.assertLess(row["printed"].index(hook.NARRATIVE_END) + len(hook.NARRATIVE_END), hook.WINDOW)

    def test_a_print_names_the_keepalive_marker_once_and_a_head_repeats_no_long_line(self) -> None:
        for delegation in ("inline", "ask-agent"):
            for key, row, _p0, _p1 in producers(delegation, INSTALL_RUN_DIR):
                with self.subTest(route=delegation, packet=key):
                    for text in (row["printed"], row["whole"]):
                        self.assertEqual(text.count("Keepalive marker: SHIPLOOP-RUN"), 1)
                    long_lines = [line for line in row["printed"].splitlines() if len(line) >= 80
                                  and not line.startswith(("      ", "Contract: ", "Receipt: "))]
                    repeated = {line[:90] for line in long_lines if long_lines.count(line) > 1}
                    self.assertEqual(repeated, set())

    def test_the_hooks_still_read_a_head_and_a_whole_print(self) -> None:
        for delegation in ("inline", "ask-agent"):
            for key, row, _p0, _p1 in producers(delegation, INSTALL_RUN_DIR):
                with self.subTest(route=delegation, packet=key):
                    for text in (row["printed"], row["whole"]):
                        self.assertIn(hook.BEGIN, text)
                        self.assertIn(hook.END, text)
                        self.assertTrue(text.startswith((hook.HEADER, *hook.PREFIXES)))


class TierTests(unittest.TestCase):
    """Which tier each block of an active producer packet has (plan 6.1): the order says where a block sits, the tier says
    whether a head that would pass the cut gives it up.  The budget tests above only see a tier when a head is tight, so
    this pins them."""

    P0 = {"header", "top", "goal", "loop", "status", "duties", "result"}
    LOOKUP = {"reference-symbols", "reference-files", "builds-on", "backchain-route"}
    CHROME = {"progress-view", "pause"}
    FILE = {"delegation", "halt", "pass-log", "run-context", "last-accepted", "deltas", "lint-records", "unverified",
            "change-inventory", "chain", "discovery-links"}

    def blocks(self, delegation: str, stage: str):
        row = next(row for key, row in renders(delegation, INSTALL_RUN_DIR).items()
                   if plans.stage_of(key) == stage and plans.is_producer(key, row["state"]))
        with tempfile.TemporaryDirectory(prefix="shiploop-head-order-") as temp:
            run_dir = Path(temp) / "run"
            run_dir.mkdir()
            return navigator._producer_blocks(None, run_dir, row["state"], None, path=run_dir / "packets" / "p.md")

    def test_every_block_is_in_the_tier_the_plan_gives_it(self) -> None:
        for delegation, stage in (("inline", "implement"), ("inline", "test"), ("inline", "verify"), ("inline", "carry-forward"),
                                  ("inline", "validate-existing"), ("ask-agent", "step-plan"), ("inline", "step-plan")):
            with self.subTest(route=delegation, stage=stage):
                tiers = {block.name: block.tier for block in self.blocks(delegation, stage)}
                for names, tier in ((self.P0, navigator.P0), (self.LOOKUP, navigator.LOOKUP),
                                    (self.CHROME, navigator.CHROME), (self.FILE, navigator.FILE_ONLY)):
                    for name in names & set(tiers):
                        self.assertEqual(tiers[name], tier, name)
                self.assertEqual(tiers.get("quoted", navigator.QUOTED), navigator.QUOTED)
                for name, tier in tiers.items():
                    if tier == navigator.P1:
                        self.assertIn(name, {"work-item", "step", "commit-scope", "expectation-results", "queue-rule",
                                             "test-rules", "rerun", "observed", "lint-commands", "improve-lessons"})
                self.assertEqual([name for name in tiers if name not in
                                  self.P0 | self.LOOKUP | self.CHROME | self.FILE | {"quoted"}
                                  and tiers[name] != navigator.P1], [])

    def test_the_blocks_are_in_print_order_required_first_then_lookups_chrome_quoted_and_the_rest(self) -> None:
        # the stage's own input (P1) sits between the duties and the result template, both required: one rank
        order = [(navigator.P0, navigator.P1), (navigator.LOOKUP,), (navigator.CHROME,), (navigator.QUOTED,)]
        for delegation in ("inline", "ask-agent"):
            tiers = [block.tier for block in self.blocks(delegation, "step-plan") if block.tier != navigator.FILE_ONLY]
            ranks = [next(i for i, group in enumerate(order) if tier in group) for tier in tiers]
            self.assertEqual(ranks, sorted(ranks))

    def test_the_backchain_route_paragraph_prints_after_the_template_with_a_stub_in_the_duty(self) -> None:
        paragraph = "Follow the packet's Backchain planning guide for this stage's scoped outcome"
        for stage in ("step-plan", "carry-forward"):
            row = next(row for key, row in renders("ask-agent", INSTALL_RUN_DIR).items()
                       if plans.stage_of(key) == stage and plans.is_producer(key, row["state"]))
            with self.subTest(stage=stage):
                whole = row["whole"]
                self.assertIn(plans.prompts.BACKCHAIN_STUB, whole)
                self.assertEqual(whole.count(paragraph), 1)
                self.assertLess(whole.index("Result template:"), whole.index(paragraph))
                self.assertLess(whole.index(plans.prompts.BACKCHAIN_STUB), whole.index("Result template:"))
                self.assertNotIn(paragraph, row["printed"][:row["printed"].index("Result template:")])
        for stage in plans.stage_spec.STAGES:
            for delegation in ("inline", "ask-agent"):
                text, moved = plans.prompts.prompt_split(stage, delegation=delegation)
                full = plans.prompts.prompt(stage, delegation=delegation)
                self.assertEqual(text.replace(plans.prompts.BACKCHAIN_STUB, moved) if moved else text, full)
                self.assertEqual(plans.prompts.BACKCHAIN_STUB in text, bool(moved))


class BlockBudgetTests(unittest.TestCase):
    """``_select_head`` on synthetic blocks: what a head keeps, in what order it gives things up."""

    def block(self, name: str, tier: str, size: int = 100):
        return navigator._Block(name, tier, ["x" * size])

    def test_the_head_limit_is_the_hosts_and_the_whole_print_limit_is_not_changed(self) -> None:
        self.assertEqual(navigator.HEAD_LIMIT, HOST_CUT)
        self.assertEqual(navigator.PRINT_LIMIT, 16_000)
        self.assertEqual(protocol.OUTPUT_LIMIT, 16_000)

    def test_required_blocks_are_never_left_out_even_over_the_limit(self) -> None:
        blocks = [self.block("a", navigator.P0, 15_000), self.block("b", navigator.P1, 6_000),
                  self.block("c", navigator.P0), self.block("d", navigator.LOOKUP), self.block("e", navigator.CHROME)]
        self.assertEqual([block.name for block in navigator._select_head(blocks)], ["a", "b", "c"])

    def test_optional_blocks_are_kept_while_they_fit_and_nothing_after_the_first_that_does_not(self) -> None:
        blocks = [self.block("a", navigator.P0, 19_000), self.block("l1", navigator.LOOKUP, 400),
                  self.block("l2", navigator.LOOKUP, 900), self.block("c1", navigator.CHROME, 50)]
        self.assertEqual([block.name for block in navigator._select_head(blocks)], ["a", "l1"])

    def test_quoted_blocks_are_the_last_optional_tier_and_nothing_stands_for_them_when_they_do_not_fit(self) -> None:
        """The packet's second pointer line says the file holds the quoted knowledge files and hand-offs, so a head that drops
        them says nothing more (the stub line that did is gone: plan 6.2, "the Knowledge-files sentence (folded into line B)")."""
        small = [self.block("a", navigator.P0, 5_000), self.block("q", navigator.QUOTED, 5_000)]
        self.assertEqual([block.name for block in navigator._select_head(small)], ["a", "q"])
        large = [self.block("a", navigator.P0, 17_000), self.block("l", navigator.LOOKUP, 500),
                 self.block("q", navigator.QUOTED, 5_000)]
        self.assertEqual([block.name for block in navigator._select_head(large)], ["a", "l"])
        # a block before the quoted files that does not fit ends the head: the quoted files go with it
        crowded = [self.block("a", navigator.P0, 18_900), self.block("l", navigator.LOOKUP, 1_100),
                   self.block("q", navigator.QUOTED, 10)]
        self.assertEqual([block.name for block in navigator._select_head(crowded)], ["a"])

    def test_an_optional_block_is_kept_exactly_when_the_printed_head_then_fits_the_limit(self) -> None:
        for size in range(19_600, 19_990, 50):
            with self.subTest(required=size):
                blocks = [self.block("a", navigator.P0, size), self.block("q", navigator.QUOTED, 200)]
                printed_with_q = len(navigator._text_of(blocks, head=True)) + 1 + len(navigator.HEAD_END) + 1
                kept = [block.name for block in navigator._select_head(blocks)]
                self.assertEqual(kept, ["a", "q"] if printed_with_q <= navigator.HEAD_LIMIT else ["a"])

    def test_a_block_may_print_a_shorter_text_in_the_head(self) -> None:
        block = navigator._Block("w", navigator.P1, ["long " * 100], ["short"])
        self.assertEqual(navigator._text_of([block]), "long " * 100)
        self.assertEqual(navigator._text_of([block], head=True), "short")

    def test_the_length_a_head_is_judged_by_is_replaceable(self) -> None:
        blocks = [self.block("a", navigator.P0, 10_000), self.block("l", navigator.LOOKUP, 5_000)]
        self.assertEqual(len(navigator._select_head(blocks)), 2)
        self.assertEqual(len(navigator._select_head(blocks, measure=lambda text: 2 * len(text))), 1)


class PlanRecordTests(unittest.TestCase):
    """Step-plan duty 9 keeps its trigger words and the three conditional topics live in references/plan-record.md.

    Ladder rung 4 of the efficiency plan's print-order unit: the head could not hold the whole duty at the live install
    length, so the three topics a plan records only when the item touches them moved, word for word, to a reference.
    """

    GUIDE = ROOT / "skills/shiploop/references/plan-record.md"
    # What each moved bullet said (a phrase of it, checked verbatim): the obligation stays whole in the guide.
    MOVED = (
        "Reopen the namespace and data entries in HOME/architecture.md ## Structure and each touched environment's tree",
        "collision check (import or load test, deploy validation, or name search)",
        "migration (unneeded, earlier step, this step, deploy obligation), round-trip check",
        "Reason for a changed placement or schema (Namespace and placement guidance, Schema and storage guidance, State and data assessment)",
        "labelled a source-check fixture apart from the runtime control",
        "confirm an external oracle (golden file, fixture, snapshot) agrees with the task",
        "a Design basis paragraph or exact section links, rechecking the Interaction design guide's matching subsections",
        "copy no prior plan",
        "a human-facing UI defaults to ambitious and highly interactive: direct manipulation, inline editing, live preview, keyboard paths, animated transitions",
        "give the reason for any scaled back",
        "the UI decisions this step owns (UI planning ownership guide); locators of sources and checks",
    )

    def test_the_guide_holds_every_moved_obligation_and_stays_under_its_size(self) -> None:
        text = " ".join(self.GUIDE.read_text().split())
        self.assertLessEqual(len(self.GUIDE.read_text()), 8_000)
        for phrase in self.MOVED:
            with self.subTest(phrase=phrase[:60]):
                self.assertIn(phrase, text)

    def test_the_duty_names_each_trigger_and_the_guide_in_both_routes(self) -> None:
        for delegation in ("inline", "ask-agent"):
            duty = " ".join(plans.prompts.prompt("step-plan", delegation=delegation).split())
            with self.subTest(route=delegation):
                for trigger in ("adds or moves code or stored data", "replays a pinned value (fixed dice, seed data)",
                                "changes interactions, UI or service state", "GUIDES/plan-record.md",
                                "opening only its matching section"):
                    self.assertIn(trigger, duty)
                for gone in ("collision check", "source-check fixture", "Design basis paragraph", "round-trip check"):
                    self.assertNotIn(gone, duty)
                self.assertIn("the Coding decision guide's selection", duty)  # unconditional: stays in the duty

    def test_the_guide_is_a_stage_reference_with_a_heading_for_its_locator(self) -> None:
        label, locator = next(row for row in plans.prompts.STAGE_REFERENCES["step-plan"] if row[0] == "Plan record guide")
        self.assertEqual(locator, "plan-record.md#topics-the-item-touches")
        self.assertIn("## Topics the item touches", self.GUIDE.read_text())

    def test_a_step_plan_head_carries_the_trigger_words_in_both_routes_at_both_lengths(self) -> None:
        for delegation in ("inline", "ask-agent"):
            for length in (INSTALL_RUN_DIR, LIVE_RUN_DIR):
                for key, row, _p0, _p1 in producers(delegation, length):
                    if plans.stage_of(key) != "step-plan":
                        continue
                    with self.subTest(route=delegation, run_dir=length, packet=key):
                        self.assertIn("GUIDES/plan-record.md", row["printed"])
                        self.assertIn("interactions, UI or service state", row["printed"])


class EmitTests(unittest.TestCase):
    """``emit`` prints what ``printed_text`` says, and the file is the render."""

    def test_emit_prints_the_printed_text_and_writes_the_render(self) -> None:
        state = navigator.new_state("/repo", "Do the thing.")
        with tempfile.TemporaryDirectory(prefix="shiploop-head-order-") as temp:
            run_dir = Path(temp) / "run"
            run_dir.mkdir()
            store.write_record(run_dir / "state.md", state)
            state = store.read_record(run_dir / "state.md")
            shown = io.StringIO()
            with contextlib.redirect_stdout(shown):
                text = navigator.emit(None, run_dir, state)
            path = navigator.packet_path(run_dir, state)
            self.assertEqual(path.read_text(), text)
            self.assertEqual(shown.getvalue(), navigator.printed_text(None, run_dir, state, path, text))
            self.assertTrue(shown.getvalue().endswith(navigator.HEAD_END + "\n"))
            self.assertNotIn(navigator.HEAD_END, text.splitlines())  # the file has no closing line; its line B only names it


if __name__ == "__main__":
    unittest.main()
