#!/usr/bin/env python3
"""No-model checks for the clear-the-context record, phase 1 (SPEC "A fresh context is recorded, not scored").

What the harness records about a fresh context, and nothing it scores:

* ``ToolLog.feed``, the one reader of a host event for tool calls and their results, shared by the whole-run reading
  (``metrics.collect``) and the windowed one (``metrics.reorientation``);
* ``sessions.jsonl``, the harness-written, append-only record of every host launch and every session end;
* ``metrics.reorientation``, the pure measure of what a fresh context did from its start to the next accepted action;
* ``fresh_starts`` in metrics.json, one such block per fresh start and per compaction;
* the two per-stage corrections (a stage with no events has no ``context``; a Grok model call is counted).

The fixtures under test/fixtures/reorientation/ are compact extracts of the saved 2026-10-05 to 2026-10-08 runs (see
extract.py there): real line numbers and runner stamps, events reduced to the keys the readers look at.  No test reads
/Users/dadleet/e2e-runs, starts a host, or touches the machine's listeners or process table.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import metrics  # noqa: E402
import run  # noqa: E402

FIXTURES = ROOT / "test" / "fixtures" / "reorientation"


def main_tests():
    """test/shiploop-e2e.test.py as a module: its fake hosts and harness cases, reused here so the through-main checks of this
    file run the same fakes as the rest of the harness. Only base classes and helpers are taken from it; none of its tests
    are collected into this file."""
    spec = importlib.util.spec_from_file_location("shiploop_e2e_main_tests", ROOT / "test" / "shiploop-e2e.test.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MAIN = main_tests()


class ToolCallEventsTest(unittest.TestCase):
    """One reader for the tool calls an event starts, whatever host wrote it (the audit's part B)."""

    def test_two_tool_use_blocks_in_one_claude_event_are_two_calls_and_text_alone_is_none(self):
        two = {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "looking"},
            {"type": "tool_use", "id": "u1", "name": "Bash", "input": {"command": "ls"}},
            {"type": "tool_use", "id": "u2", "name": "Read", "input": {"file_path": "/w/a.py"}}]}}
        text = {"type": "assistant", "message": {"content": [{"type": "text", "text": "hello"}]}}
        self.assertEqual(metrics.tool_call_events(two), [("u1", "Bash", {"command": "ls"}),
                                                         ("u2", "Read", {"file_path": "/w/a.py"})])
        self.assertEqual(metrics.tool_call_events(text), [])

    def test_a_grok_or_translated_codex_tool_call_is_one_call_and_its_updates_are_none(self):
        call = {"type": "tool_call", "toolCallId": "c1", "toolName": "run_terminal_command",
                "rawInput": {"command": "node --test"}}
        titled = {"type": "tool_call", "toolCallId": "c2", "title": "read_file", "rawInput": {"target_file": "/w/x"}}
        bare = {"type": "tool_call", "toolCallId": "c3", "toolName": "list_dir", "rawInput": None}
        self.assertEqual(metrics.tool_call_events(call), [("c1", "run_terminal_command", {"command": "node --test"})])
        self.assertEqual(metrics.tool_call_events(titled), [("c2", "read_file", {"target_file": "/w/x"})])
        self.assertEqual(metrics.tool_call_events(bare), [("c3", "list_dir", {})])
        for other in ({"type": "tool_call_update", "toolCallId": "c1", "rawOutput": {"exit_code": 0}},
                      {"type": "user", "message": {"content": []}}, {"type": "usage"}, {"type": "end"}):
            self.assertEqual(metrics.tool_call_events(other), [])


# One stream of each host's event shape; the same events go through collect and through ToolLog.feed.
CLAUDE_STREAM = [
    {"type": "assistant", "message": {"id": "m1", "content": [
        {"type": "tool_use", "id": "u1", "name": "Bash", "input": {"command": "python3 x/shiploop complete --run-dir r"}}]}},
    {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "u1",
         "content": "Exit code 2\nShipLoop navigator: result requires outcome and summary"}]}},
    {"type": "assistant", "message": {"id": "m2", "content": [
        {"type": "tool_use", "id": "u2", "name": "Bash", "input": {"command": "git add -A && git commit -m x"}},
        {"type": "tool_use", "id": "u3", "name": "AskUserQuestion", "input": {"question": "Which port?"}}]}},
    {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "u2", "content": "committed"},
        {"type": "tool_result", "tool_use_id": "u3", "content": "3000"}]}},
    {"type": "result", "subtype": "success", "num_turns": 2, "total_cost_usd": 1.0}]

GROK_STREAM = [
    {"type": "usage", "usage": {"input_tokens": 1000, "output_tokens": 10}},
    {"type": "tool_call", "toolCallId": "a", "toolName": "run_terminal_command",
     "rawInput": {"command": "python3 x/shiploop complete --run-dir r"}},
    {"type": "tool_call_update", "toolCallId": "a", "status": "in_progress",
     "rawOutput": {"exit_code": 0, "output_for_prompt": "running"}},
    {"type": "tool_call_update", "toolCallId": "a", "status": "completed", "rawOutput": {
        "exit_code": 2, "output_for_prompt": "SHIPLOOP-RUN run=x rev=1 dir=/r\nerror: result refused"}},
    {"type": "tool_call", "toolCallId": "c", "toolName": "run_terminal_command",
     "rawInput": {"command": "python3 x/shiploop next --run-dir r"}},
    {"type": "tool_call_update", "toolCallId": "c", "status": "failed", "rawOutput": {
        "exit_code": 2, "output_for_prompt": "x"}, "content": [
        {"type": "content", "content": {"type": "text", "text": "User cancelled the execution for tool"}}]},
    {"type": "end", "stopReason": "end_turn", "num_turns": 1, "total_cost_usd": 1.0}]


def collected(stream: list) -> dict:
    """metrics.collect over a hand-built stream, one second between events, with no ShipLoop records."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in stream))
        (out / "timeline.jsonl").write_text("".join(
            json.dumps({"line": n, "t": 100.0 + n}) + "\n" for n in range(len(stream))))
        return metrics.collect(out, None)


def fed(stream: list) -> "metrics.ToolLog":
    log = metrics.ToolLog()
    for number, event in enumerate(stream):
        log.feed(event, 100.0 + number)
    return log


class ToolLogFeedTest(unittest.TestCase):
    """collect reads tool calls and results through ToolLog.feed: one reader, so a window cannot read them another way."""

    def test_feed_gives_the_tool_log_collect_reports_for_each_host_shape(self):
        for label, stream in (("claude", CLAUDE_STREAM), ("grok", GROK_STREAM)):
            with self.subTest(label):
                log, total = fed(stream), collected(stream)
                self.assertEqual(log.failures, total["shiploop_failures"])
                self.assertEqual(log.glue, total["model_glue"])
                self.assertEqual(log.asked, total["asked_user"])
                self.assertEqual(sorted(log.shared), total["tmp_writes"])
        self.assertEqual([f["verb"] for f in fed(CLAUDE_STREAM).failures], ["complete"])
        self.assertEqual(len(fed(CLAUDE_STREAM).glue), 1)
        self.assertEqual(fed(CLAUDE_STREAM).asked, ["Which port?"])

    def test_a_grok_update_that_is_still_running_or_was_cancelled_is_not_a_result(self):
        log = fed(GROK_STREAM)
        self.assertEqual(len(log.failures), 1, "only the completed update of call a failed: the running placeholder and the "
                                               "cancelled update of call c are not results")
        self.assertIn("a", log.answered)
        self.assertNotIn("c", log.answered)

    def test_a_failure_is_remembered_by_its_call_so_a_window_can_count_its_own(self):
        log = fed(CLAUDE_STREAM)
        self.assertEqual(list(log.failure_of), ["u1"])
        self.assertEqual(log.failure_of["u1"]["verb"], "complete")
        self.assertEqual(log.answered, {"u1", "u2", "u3"})


CLI = "/p/build/plugins/skill-craft/skills/shiploop/scripts/shiploop"
RUN = "/r/.shiploop-runs/w/run"


def usage(tokens: int) -> dict:
    """One Grok usage event: one model call."""
    return {"type": "usage", "usage": {"input_tokens": tokens, "output_tokens": 10}}


class Stream:
    """A hand-built host stream with its runner stamps, one event per line, for the windowed reading.

    ``rows`` is what metrics.event_range yields ((line, event) pairs) and ``stamps`` the runner's timeline. Grok-shaped
    events (a `tool_call` and its final `tool_call_update`) unless ``claude`` is used.
    """

    def __init__(self, first: float = 1000.0) -> None:
        self.rows: list[tuple] = []
        self.stamps: dict = {}
        self.t = first
        self.calls = 0

    def add(self, event: dict, after: float = 0.0) -> None:
        self.t += after
        line = len(self.rows)
        self.rows.append((line, event))
        self.stamps[line] = round(self.t, 3)

    def start(self) -> "Stream":
        self.add({"type": "available_commands", "commands": []})
        return self

    def call(self, after: float, tool: str, arg: dict, output: str = "", code: int = 0) -> str:
        """One Grok-shaped call that starts ``after`` seconds after the previous event and answers 0.1 s later."""
        self.calls += 1
        call_id = f"c{self.calls}"
        self.add({"type": "tool_call", "toolCallId": call_id, "toolName": tool, "rawInput": arg}, after)
        self.add({"type": "tool_call_update", "toolCallId": call_id, "status": "completed",
                  "rawOutput": {"exit_code": code, "output_for_prompt": output}}, 0.1)
        return call_id

    def shell(self, after: float, command: str, output: str = "", code: int = 0) -> str:
        return self.call(after, "run_terminal_command", {"command": command}, output, code)

    def next(self, after: float = 1.0, run_dir: str = RUN, cli: str = CLI, output: str = "ShipLoop navigator | spec | revision 3\n",
             code: int = 0) -> str:
        return self.shell(after, f'python3 "{cli}" next --run-dir "{run_dir}"', output, code)

    def complete(self, action: str, after: float = 1.0, output: str = "ShipLoop navigator | test-red | revision 4\n") -> str:
        return self.shell(after, f'python3 "{CLI}" complete --run-dir={RUN} --action={action} --result={RUN}/inbox/{action}.md',
                          output)

    def claude(self, after: float, tool: str, arg: dict, output: str = "", message: str | None = None) -> str:
        """One Claude-shaped call: an assistant event with a tool_use block, then the user event with its result."""
        self.calls += 1
        call_id = f"u{self.calls}"
        self.add({"type": "assistant", "message": {"id": message or f"m{self.calls}", "content": [
            {"type": "tool_use", "id": call_id, "name": tool, "input": arg}]}}, after)
        self.add({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": call_id, "content": output}]}}, 0.1)
        return call_id


def stamp(stream: "Stream") -> float:
    """The engine's whole-second stamp for an action accepted just before the stream's last event (truncated, as it writes)."""
    return float(int(stream.t - 0.05))


def accepted_rows(*rows: tuple) -> list[dict]:
    """The accepted-history rows metrics.stage_results gives: (action, stage, stamp)."""
    return [{"stage": stage, "outcome": "done", "work_item": None, "action": action, "t": stamp}
            for action, stage, stamp in rows]


TOLD = {"cli": CLI, "run_dir": RUN}


class WindowEndRuleTest(unittest.TestCase):
    """The window runs from the fresh start to the tool call that SUBMITTED the next accepted action. The accept stamp is
    whole-second truncated, so a window cut at the stamp is off by up to a call in both directions (the audit's correction 4)."""

    def test_the_window_ends_at_the_submitting_call_even_when_the_truncated_stamp_is_before_it(self):
        s = Stream(first=1000.0).start()           # t 1000.0
        s.next(after=0.5)                           # call 1 at 1000.5
        s.shell(2.0, "ls")                          # call 2 at 1002.6
        s.complete("nav-b", after=1.0)              # call 3 at 1003.7: the engine accepts at 1003.8, stamp 1003 (truncated)
        s.shell(0.1, "echo after")                  # call 4 at 1003.9: after the accept, inside the stamp's second
        got = metrics.reorientation(s.rows, s.stamps, accepted_rows(("nav-a", "intake", 990.0), ("nav-b", "spec", 1003.0)), TOLD)
        self.assertTrue(got["measured"], got)
        # A cut at `t <= stamp` would read 2 calls (the submitting one, at 1003.7, is after the truncated stamp 1003.0); a cut at
        # `t < stamp + 1` would read 4 (call 4 starts at 1003.9, after the accept but inside the same second).
        self.assertEqual(got["tool_calls"], 3, "call 4 starts inside the stamp's second but after the accept")
        self.assertEqual(got["accepted"], {"stage": "spec", "action": "nav-b"})
        self.assertEqual(got["seconds"], 3.7, "to the submitting call, on the runner's clock")
        self.assertEqual(got["seconds_to_accept_stamp"], 3.0, "the engine's stamp, good to a second")

    def test_a_refused_complete_is_in_the_window_and_the_accepted_one_ends_it(self):
        s = Stream(first=2000.0).start()
        s.next(after=0.5)
        s.complete("nav-b", after=4.0, output="ShipLoop navigator: result requires outcome and summary\n")
        s.shell(3.0, "edit the result")
        s.complete("nav-b", after=1.0)
        got = metrics.reorientation(s.rows, s.stamps, accepted_rows(("nav-b", "spec", stamp(s))), TOLD)
        self.assertEqual(got["tool_calls"], 4)
        self.assertEqual([f["verb"] for f in got["failures"]["items"]], ["complete"])

    def test_reading_the_packet_of_the_pending_action_does_not_end_the_window(self):
        s = Stream(first=3000.0).start()
        s.shell(0.5, f"cat {RUN}/packets/nav-b.md")
        s.shell(1.0, "node --test")
        s.complete("nav-b", after=2.0)
        got = metrics.reorientation(s.rows, s.stamps, accepted_rows(("nav-b", "spec", stamp(s))), TOLD)
        self.assertEqual(got["tool_calls"], 3, "the packet read names nav-b but submits nothing")
        self.assertEqual((got["first_grounding"], got["calls_before_grounding"]), ("packet", 0))

    def test_a_submission_of_an_action_accepted_before_the_start_ends_nothing(self):
        # The model resubmits nav-a, accepted long before this session began: not the action this window waits for.
        s = Stream(first=4000.0).start()
        s.next(after=0.5)
        s.complete("nav-a", after=1.0)
        s.shell(1.0, "ls")
        s.complete("nav-b", after=1.0)
        got = metrics.reorientation(s.rows, s.stamps, accepted_rows(("nav-a", "intake", 3500.0), ("nav-b", "spec", stamp(s))), TOLD)
        self.assertEqual((got["tool_calls"], got["accepted"]["action"]), (4, "nav-b"))

    def test_a_window_with_no_accepted_action_is_unmeasured_with_its_reason_and_keeps_the_recovery_facts(self):
        s = Stream().start()
        s.shell(0.5, "cat SKILL.md")
        s.next(after=1.0, run_dir="/r/.shiploop-runs/w/run/../typo")
        got = metrics.reorientation(s.rows, s.stamps, accepted_rows(("nav-a", "intake", 900.0)), TOLD)
        self.assertFalse(got["measured"])
        self.assertIn("no tool call submitted an action accepted after this start", got["reason"])
        for name in ("tool_calls", "seconds", "failures", "rewrote"):
            self.assertNotIn(name, got, "an unmeasured window has no count: unknown is not zero")
        self.assertEqual((got["first_grounding"], got["calls_before_grounding"]), ("next", 1))
        self.assertEqual(got["recovery"]["first_next"]["run_dir"], "different")

    def test_a_session_that_wrote_no_event_is_unmeasured(self):
        got = metrics.reorientation([], {}, accepted_rows(("nav-a", "intake", 900.0)), TOLD)
        self.assertEqual((got["measured"], got["reason"]), (False, "the session wrote no event"))


class FirstGroundingTest(unittest.TestCase):
    """The first call that asks ShipLoop where the run stands: `next`, a read of a packet file, or another ShipLoop verb."""

    def window(self, build) -> dict:
        s = Stream(first=5000.0).start()
        build(s)
        s.complete("nav-b", after=1.0)
        return metrics.reorientation(s.rows, s.stamps, accepted_rows(("nav-b", "spec", stamp(s))), TOLD)

    def test_next_first_is_zero_calls_before_grounding(self):
        got = self.window(lambda s: s.next(after=0.5))
        self.assertEqual((got["first_grounding"], got["calls_before_grounding"]), ("next", 0))

    def test_reading_the_skill_card_first_is_one_call_before_grounding(self):
        got = self.window(lambda s: (s.shell(0.5, "cat /p/skills/shiploop/SKILL.md"), s.next()))
        self.assertEqual((got["first_grounding"], got["calls_before_grounding"]), ("next", 1))

    def test_a_packet_read_is_grounding_and_so_is_another_shiploop_verb(self):
        got = self.window(lambda s: (s.shell(0.5, "ls"), s.shell(0.5, f"cat {RUN}/packets/nav-b.md"), s.next()))
        self.assertEqual((got["first_grounding"], got["calls_before_grounding"]), ("packet", 1))
        got = self.window(lambda s: (s.shell(0.5, "ls"), s.shell(0.5, f'python3 "{CLI}" lint --run-dir={RUN}')))
        self.assertEqual((got["first_grounding"], got["calls_before_grounding"]), ("other", 1))

    def test_a_window_with_no_call_at_all_has_no_first_grounding_not_zero(self):
        s = Stream().start()
        got = metrics.reorientation(s.rows, s.stamps, accepted_rows(("nav-b", "spec", 1100.0)), TOLD)
        self.assertEqual((got["measured"], got["first_grounding"], got["calls_before_grounding"]), (False, None, None))


class RecoveryCommandTest(unittest.TestCase):
    """Was the recovery command repeated as the prompt told it? Compared after normpath and resolve: a path that differs in
    text but names the same directory ran (the recorded Luna `/./`), one that names another directory did not."""

    def first_next(self, command: str, told=TOLD, output: str = "ShipLoop navigator | spec | revision 3\n", code: int = 0):
        s = Stream().start()
        s.shell(0.5, command, output, code)
        got = metrics.reorientation(s.rows, s.stamps, [], told)
        return got["recovery"]

    def test_the_command_as_told_is_exact(self):
        got = self.first_next(f'python3 "{CLI}" next --run-dir "{RUN}"')
        self.assertEqual(got["first_next"], {"call": 1, "failed": False, "exit": None, "cli": "exact", "run_dir": "exact"})
        self.assertEqual((got["told"], got["next_calls"], got["revision_seen"]), (TOLD, 1, 3))

    def test_a_dot_segment_is_equivalent_and_a_wrong_directory_is_different(self):
        same = self.first_next(f'python3 "{CLI}" next --run-dir "/r/./.shiploop-runs/w/run"')["first_next"]
        self.assertEqual((same["cli"], same["run_dir"]), ("exact", "equivalent"))
        also = self.first_next(f'python3 "{CLI}" next --run-dir "/r/.shiploop-runs//w/run/"')["first_next"]
        self.assertEqual(also["run_dir"], "equivalent")
        wrong = self.first_next(f'python3 "/p/other/shiploop" next --run-dir "/r/20261005/.shiploop-runs/w/run"',
                                output="error: no ShipLoop run directory at x; check --run-dir\n", code=2)["first_next"]
        self.assertEqual((wrong["cli"], wrong["run_dir"], wrong["failed"], wrong["exit"]), ("different", "different", True, 2))

    def test_the_equals_form_and_a_shell_wrapper_are_read(self):
        wrapped = f"/bin/zsh -lc 'python3 \"{CLI}\" next --run-dir \"/r/./.shiploop-runs/w/run\"'"
        got = self.first_next(wrapped)["first_next"]
        self.assertEqual((got["cli"], got["run_dir"]), ("exact", "equivalent"))
        got = self.first_next(f"python3 {CLI} next --run-dir={RUN}")["first_next"]
        self.assertEqual((got["cli"], got["run_dir"]), ("exact", "exact"))

    def test_a_path_that_cannot_be_compared_is_unreadable_not_different(self):
        for command in (f'python3 "{CLI}" next --run-dir run', f'python3 "{CLI}" next',
                        f'python3 skills/shiploop/scripts/shiploop next --run-dir "{RUN}"'):
            with self.subTest(command):
                got = self.first_next(command)["first_next"]
                self.assertIn("unreadable", (got["cli"], got["run_dir"]))
                self.assertNotIn("different", (got["cli"], got["run_dir"]))

    def test_no_next_call_and_no_told_command_are_said_as_they_are(self):
        s = Stream().start()
        s.shell(0.5, "ls")
        got = metrics.reorientation(s.rows, s.stamps, [], TOLD)["recovery"]
        self.assertEqual((got["first_next"], got["next_calls"]), (None, 0))
        told_none = self.first_next(f'python3 "{CLI}" next --run-dir "{RUN}"', told=None)
        self.assertIsNone(told_none["told"])
        self.assertEqual(told_none["first_next"], {"call": 1, "failed": False, "exit": None, "cli": None, "run_dir": None})

    def test_the_revision_the_first_good_next_showed_is_recorded_beside_the_recovery_facts(self):
        s = Stream().start()
        s.next(after=0.5, run_dir="/r/typo", output="error: no ShipLoop run directory\n", code=2)
        s.next(after=1.0, output="ShipLoop navigator | spec | revision 12\nCallback ...\n")
        s.next(after=1.0, output="ShipLoop navigator | spec | revision 13\n")
        got = metrics.reorientation(s.rows, s.stamps, [], TOLD)["recovery"]
        self.assertEqual(got["revision_seen"], 12, "the first next that returned a packet, not the failed one or a later one")
        none = Stream().start()
        none.shell(0.5, "ls")
        self.assertIsNone(metrics.reorientation(none.rows, none.stamps, [], TOLD)["recovery"]["revision_seen"])
        failed = Stream().start()
        failed.next(after=0.5, output="error: no ShipLoop run directory\n", code=2)
        self.assertIsNone(metrics.reorientation(failed.rows, failed.stamps, [], TOLD)["recovery"]["revision_seen"])

    def test_only_the_first_next_is_compared_and_every_next_is_counted(self):
        s = Stream().start()
        s.next(after=0.5, run_dir="/r/typo", output="error: no ShipLoop run directory\n", code=2)
        s.next(after=1.0)
        got = metrics.reorientation(s.rows, s.stamps, [], TOLD)["recovery"]
        self.assertEqual((got["next_calls"], got["first_next"]["call"], got["first_next"]["run_dir"]), (2, 1, "different"))


class RewroteTest(unittest.TestCase):
    """`rewrote`: a path a file-edit tool wrote both before the fresh start (in the same stage) and after it. A lower bound."""

    def before(self, *paths: str):
        s = Stream(first=100.0)
        for path in paths:
            s.call(1.0, "search_replace", {"file_path": path})
        return s

    def window(self, after_calls, earlier):
        s = Stream(first=1000.0).start()
        for tool, arg in after_calls:
            s.call(1.0, tool, arg)
        s.complete("nav-b", after=1.0)
        return metrics.reorientation(s.rows, s.stamps, accepted_rows(("nav-a", "intake", 90.0), ("nav-b", "spec", stamp(s))),
                                     TOLD, earlier=earlier)

    def test_a_file_edited_in_the_stage_before_and_again_after_the_start_is_rewritten(self):
        old = self.before("/w/rules.js", "/w/server.js")
        asked = []

        def earlier(after_t):
            asked.append(after_t)
            return old.rows

        got = self.window([("write", {"file_path": "/w/rules.js"}), ("write", {"file_path": "/w/new.js"})], earlier)
        self.assertEqual(got["rewrote"]["paths"], ["/w/rules.js"])
        self.assertEqual(asked, [90.0], "the stage's pre-start portion starts at the previous accept's stamp")
        self.assertEqual(got["rewrote"]["bound"], "lower")
        self.assertEqual(got["rewrote"]["scope"], "1 seen by file-edit tools")

    def test_nothing_seen_reads_none_seen_by_file_edit_tools_not_an_empty_measurement(self):
        got = self.window([("write", {"file_path": "/w/new.js"})], lambda after_t: self.before("/w/old.js").rows)
        self.assertEqual(got["rewrote"], {"paths": [], "bound": "lower", "scope": "none seen by file-edit tools"})

    def test_a_shell_write_is_invisible_which_is_why_the_figure_is_a_lower_bound(self):
        got = self.window([("run_terminal_command", {"command": "sed -i s/a/b/ /w/rules.js"})],
                          lambda after_t: self.before("/w/rules.js").rows)
        self.assertEqual(got["rewrote"]["paths"], [])
        self.assertEqual(got["rewrote"]["bound"], "lower")

    def test_a_read_is_not_a_write(self):
        got = self.window([("read_file", {"target_file": "/w/rules.js"})], lambda after_t: self.before("/w/rules.js").rows)
        self.assertEqual(got["rewrote"]["paths"], [])

    def test_without_an_earlier_portion_or_a_previous_stamp_it_is_unknown_with_a_reason(self):
        s = Stream(first=1000.0).start()
        s.complete("nav-b", after=1.0)
        no_earlier = metrics.reorientation(s.rows, s.stamps, accepted_rows(("nav-b", "spec", stamp(s))), TOLD)
        self.assertIsNone(no_earlier["rewrote"]["paths"])
        self.assertIn("earlier", no_earlier["rewrote"]["scope"])
        unstamped = metrics.reorientation(s.rows, s.stamps, accepted_rows(("nav-a", "intake", None), ("nav-b", "spec", stamp(s))),
                                          TOLD, earlier=lambda after_t: [])
        self.assertIsNone(unstamped["rewrote"]["paths"])
        self.assertIn("no accept stamp", unstamped["rewrote"]["scope"])
        first = metrics.reorientation(s.rows, s.stamps, accepted_rows(("nav-b", "spec", stamp(s))), TOLD,
                                      earlier=lambda after_t: [])
        self.assertEqual(first["rewrote"]["paths"], [], "the first accepted action has no previous one: the whole stream before")


class WindowFailuresTest(unittest.TestCase):
    def test_failures_count_only_the_windows_own_calls_and_say_they_are_a_lower_bound(self):
        s = Stream(first=100.0).start()
        s.next(after=0.5, output="ShipLoop navigator: stale action\n", code=2)
        s.shell(1.0, "node --test", code=1)       # not a ShipLoop command: not a ShipLoop failure
        s.next(after=1.0)
        s.complete("nav-b", after=1.0)
        got = metrics.reorientation(s.rows, s.stamps, accepted_rows(("nav-b", "spec", stamp(s))), TOLD)
        self.assertEqual([(f["verb"], f["exit"]) for f in got["failures"]["items"]], [("next", 2)])
        self.assertEqual(got["failures"]["bound"], "lower")
        self.assertIn("earlier session", got["failures"]["scope"])

    def test_a_question_put_to_a_person_is_counted(self):
        s = Stream(first=100.0).start()
        s.call(0.5, "ask_user_question", {"question": "Which port?"})
        s.complete("nav-b", after=1.0)
        got = metrics.reorientation(s.rows, s.stamps, accepted_rows(("nav-b", "spec", stamp(s))), TOLD)
        self.assertEqual(got["asked_user"], 1)


class WindowHostShapesTest(unittest.TestCase):
    def test_a_claude_window_counts_each_tool_use_block_and_reads_the_exit_code_it_shows(self):
        s = Stream(first=100.0)
        s.add({"type": "system", "subtype": "init"})
        s.claude(1.0, "Bash", {"command": f'python3 "{CLI}" next --run-dir "{RUN}"'})
        s.claude(2.0, "Read", {"file_path": f"{RUN}/packets/nav-b.md"})
        s.add({"type": "assistant", "message": {"id": "m9", "content": [
            {"type": "tool_use", "id": "ua", "name": "Bash", "input": {"command": "ls"}},
            {"type": "tool_use", "id": "ub", "name": "Bash", "input": {
                "command": f'python3 "{CLI}" complete --run-dir={RUN} --action=nav-b --result=x'}}]}}, 1.0)
        s.add({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "ua", "content": "a.txt"},
            {"type": "tool_result", "tool_use_id": "ub", "content": "ShipLoop navigator | test-red | revision 4"}]}}, 0.1)
        got = metrics.reorientation(s.rows, s.stamps, accepted_rows(("nav-b", "spec", stamp(s))), TOLD)
        self.assertEqual((got["measured"], got["tool_calls"]), (True, 4))
        self.assertEqual((got["first_grounding"], got["calls_before_grounding"]), ("next", 0))


def fixture(name: str) -> types.SimpleNamespace:
    """A compact extract of a saved run (test/fixtures/reorientation/<name>/, see extract.py there)."""
    import sessionlog
    out = FIXTURES / name
    run_dir = out / ".shiploop-runs" / "work-fixture" / "run"
    return types.SimpleNamespace(out=out, run_dir=run_dir, events=out / "events.jsonl",
                                 stamps=metrics.timeline(out / "timeline.jsonl"), accepted=metrics.stage_results(run_dir),
                                 sessions=sessionlog.read(out))


def window_of(f: types.SimpleNamespace, session: int, earlier: bool = True) -> dict:
    """metrics.reorientation over the fixture's session number ``session`` (1-based), as the collector reads it."""
    start = f.sessions[session - 1]
    following = [x["events_line"] for x in f.sessions if x["events_line"] > start["events_line"]]
    ordered = sorted(f.stamps)
    times = [f.stamps[n] for n in ordered]
    import bisect

    def before(after):
        low = 0 if after is None else ordered[min(bisect.bisect_right(times, after), len(ordered) - 1)]
        return metrics.event_range(f.events, low, start["events_line"])

    return metrics.reorientation(metrics.event_range(f.events, start["events_line"], following[0] if following else None),
                                 f.stamps, f.accepted, start["told"], earlier=before if earlier else None)


class RecordedFreshStartReproductionTest(unittest.TestCase):
    """The three accidental probes of 2026-10-05..08, replayed from compact extracts. These are NOT clean samples (SPEC): they
    pin that the measure reproduces what was seen in the saved runs, not what a fresh context should do."""

    def test_the_r3_grok_resume_is_23_calls_and_163_seconds_to_the_complete_that_was_accepted(self):
        f = fixture("r3-battleship-grok-none")
        self.assertEqual([(x["kind"], x["reason"], x["events_line"]) for x in f.sessions],
                         [("first", "start", 0), ("fresh", "resume-run", 4121)])
        got = window_of(f, 2)
        self.assertTrue(got["measured"], got)
        self.assertEqual(got["accepted"]["stage"], "test-author")
        self.assertEqual(got["tool_calls"], 23)
        self.assertEqual(got["seconds"], 163.2, "to the `complete` call; the design text's 164 is the stamp")
        self.assertEqual(got["seconds_to_accept_stamp"], 164.0)
        self.assertEqual((got["first_grounding"], got["calls_before_grounding"]), ("next", 1), "SKILL.md was read first")
        self.assertEqual(got["recovery"]["first_next"], {"call": 2, "failed": False, "exit": None, "cli": "exact",
                                                         "run_dir": "exact"})
        self.assertEqual(got["failures"]["items"], [])
        before = metrics.written_paths(metrics.event_range(f.events, 3554, 4121))
        self.assertTrue({p for p in before if p.endswith("/worktree/rules.js") or p.endswith("/worktree/server.js")},
                        "the old session edited the product in this stage: the comparison is not vacuous")
        self.assertEqual(got["rewrote"]["paths"], [], "the old session edited rules.js and server.js; the fresh one wrote notes only")
        self.assertEqual(got["rewrote"]["scope"], "none seen by file-edit tools")
        self.assertEqual(got["asked_user"], 0)

    def test_the_r2_claude_fresh_start_is_6_calls_not_7_and_22_point_7_seconds_to_the_accept(self):
        f = fixture("r2-battleship-grok-none")
        got = window_of(f, 2)
        self.assertTrue(got["measured"], got)
        self.assertEqual(got["accepted"]["stage"], "implement")
        self.assertEqual(got["tool_calls"], 6, "next, a packet Read, ls, cat, lint, complete: the 7th call is 3 s after the accept")
        self.assertEqual(got["seconds"], 21.8)
        self.assertEqual(got["seconds_to_accept_stamp"], 22.7)
        self.assertEqual((got["first_grounding"], got["calls_before_grounding"]), ("next", 0))
        self.assertEqual(got["recovery"]["first_next"]["cli"], "exact")
        self.assertEqual(got["recovery"]["first_next"]["run_dir"], "exact")
        self.assertEqual(got["failures"]["items"], [])

    def test_the_r2_session_wrote_the_result_by_shell_which_a_file_edit_log_cannot_see(self):
        # The sixth call is `cat > .../inbox/<action>.md <<'EOF' ... complete`: a shell write. rewrote can only be a lower bound.
        f = fixture("r2-battleship-grok-none")
        last = [e for _n, e in metrics.event_range(f.events, 2704) if e["type"] == "assistant"][5]
        self.assertIn("cat >", last["message"]["content"][0]["input"]["command"])
        self.assertEqual(window_of(f, 2)["rewrote"]["bound"], "lower")

    def test_of_the_four_luna_xhigh_first_next_calls_two_failed_one_is_equivalent_and_one_exact(self):
        f = fixture("v1210-battleship-luna-xhigh")
        seen = []
        for number in (2, 3, 4, 5):
            got = window_of(f, number)
            self.assertFalse(got["measured"], "the extract holds only the start of each session")
            seen.append(got["recovery"]["first_next"])
        self.assertEqual([(x["failed"], x["exit"], x["run_dir"]) for x in seen],
                         [(True, 2, "different"), (True, 2, "different"), (False, None, "exact"), (False, None, "equivalent")])
        self.assertEqual({x["cli"] for x in seen}, {"exact"}, "the CLI was typed right every time")
        self.assertEqual([x["call"] for x in seen], [2, 2, 2, 2], "SKILL.md first, then the first next")
        # Said the way the audit asked: two failed, one equivalent, one exact.
        self.assertEqual((sum(x["failed"] for x in seen), sum(x["run_dir"] == "equivalent" for x in seen),
                          sum(x["run_dir"] == "exact" for x in seen)), (2, 1, 1))


class FreshStartsCollectTest(unittest.TestCase):
    """metrics.collect lists a block for every fresh start and every compaction, from sessions.jsonl and the host's events."""

    def collect(self, name: str, without: tuple = ()) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / name
            shutil.copytree(FIXTURES / name, out, ignore=shutil.ignore_patterns(*without) if without else None)
            return metrics.collect(out, out / ".shiploop-runs" / "work-fixture" / "run")

    def test_r3_lists_two_compactions_and_the_resume_in_the_order_of_their_first_event(self):
        got = self.collect("r3-battleship-grok-none")
        self.assertIsNone(got["fresh_starts_unmeasured"])
        starts = got["fresh_starts"]
        self.assertEqual([(b["kind"], b["events_line"]) for b in starts],
                         [("compaction", 1536), ("fresh", 4121), ("compaction", 8341)])
        resume = starts[1]
        self.assertEqual((resume["n"], resume["reason"], resume["host"], resume["stage_in_flight"]),
                         (2, "resume-run", "grok", "test-author"))
        self.assertEqual((resume["reorientation"]["tool_calls"], resume["reorientation"]["seconds"]), (23, 163.2))
        self.assertEqual(got["compactions"], 2, "the count the old reading gives is the number of compaction entries")

    def test_a_compaction_has_a_window_but_no_told_command_and_its_first_call_is_recorded(self):
        first = self.collect("r3-battleship-grok-none")["fresh_starts"][0]
        self.assertEqual((first["n"], first["reason"], first["host"]), (None, None, "grok"))
        window = first["reorientation"]
        self.assertTrue(window["measured"], window)
        self.assertEqual(window["accepted"]["stage"], "test-strategy")
        self.assertEqual(first["stage_in_flight"], "test-strategy")
        self.assertIsNone(window["recovery"]["told"], "a compaction is not given a recovery command")
        self.assertEqual((window["first_grounding"], window["calls_before_grounding"]), ("packet", 0),
                         "the first call after the first r3 compaction was a read of the current packet")
        self.assertEqual((window["recovery"]["next_calls"], window["recovery"]["first_next"]), (0, None),
                         "after that compaction the model never ran `next`: it read the packet by its path")

    def test_a_compaction_after_the_last_accepted_action_is_unmeasured_not_zero(self):
        last = self.collect("r3-battleship-grok-none")["fresh_starts"][2]
        self.assertFalse(last["reorientation"]["measured"])
        self.assertIsNone(last["stage_in_flight"])
        self.assertNotIn("tool_calls", last["reorientation"])

    def test_without_sessions_jsonl_only_the_compactions_are_listed_and_the_gap_is_named(self):
        got = self.collect("r3-battleship-grok-none", without=("sessions.jsonl",))
        self.assertEqual([b["kind"] for b in got["fresh_starts"]], ["compaction", "compaction"])
        self.assertTrue(got["fresh_starts_unmeasured"].startswith("not recorded"), got["fresh_starts_unmeasured"])
        self.assertIn("sessions.jsonl", got["fresh_starts_unmeasured"])

    def test_a_recorded_empty_sessions_file_is_recorded_empty_not_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text(json.dumps({"type": "usage", "usage": {"input_tokens": 1}}) + "\n")
            (out / "sessions.jsonl").write_text("")
            got = metrics.collect(out, None)
        self.assertEqual((got["fresh_starts"], got["fresh_starts_unmeasured"]), ([], None))

    def test_r2_is_a_mixed_host_run_and_its_fresh_start_belongs_to_the_claude_host_that_began_it(self):
        got = self.collect("r2-battleship-grok-none")
        self.assertEqual(len(got["fresh_starts"]), 1)
        start = got["fresh_starts"][0]
        self.assertEqual((start["kind"], start["host"], start["stage_in_flight"]), ("fresh", "claude", "implement"))
        self.assertEqual(start["reorientation"]["tool_calls"], 6)

    def test_the_four_luna_resumes_are_four_unmeasured_blocks_that_keep_their_recovery_facts(self):
        got = self.collect("v1210-battleship-luna-xhigh")
        self.assertEqual([b["n"] for b in got["fresh_starts"]], [2, 3, 4, 5])
        self.assertEqual([b["host"] for b in got["fresh_starts"]], ["codex"] * 4)
        first_next = [b["reorientation"]["recovery"]["first_next"] for b in got["fresh_starts"]]
        self.assertEqual([x["run_dir"] for x in first_next], ["different", "different", "exact", "equivalent"])
        self.assertTrue(all(not b["reorientation"]["measured"] for b in got["fresh_starts"]))

    def test_a_window_stops_at_the_next_session_start_and_never_reads_into_it(self):
        # Three Codex sessions; each numbers its calls item_1.. again. Session 2 never submits anything; session 3 does. Read
        # on past its own end, session 2's window would end at session 3's `complete` and take its item_1 for its own.
        first, second, third = Stream(first=100.0).start(), Stream(first=200.0).start(), Stream(first=300.0).start()
        first.shell(1.0, "echo old session")
        second.shell(1.0, "ls")
        third.next(after=1.0)
        third.complete("nav-b", after=1.0)
        streams = (first, second, third)
        for stream in streams:
            for number, (_line, event) in enumerate(stream.rows[1:]):
                event["toolCallId"] = f"item_{number // 2 + 1}"
        starts, offset, lines, stamps = [], 0, [], {}
        for stream in streams:
            starts.append(offset)
            lines += [event for _l, event in stream.rows]
            stamps.update({offset + n: t for n, t in stream.stamps.items()})
            offset += len(stream.rows)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in lines))
            (out / "timeline.jsonl").write_text("".join(json.dumps({"line": n, "t": t}) + "\n" for n, t in stamps.items()))
            run_dir = out / "run"
            MAIN.write_engine_records(run_dir, [("nav-b", "spec", "done", float(int(third.t - 0.05)))], status="active",
                                      stage="spec")
            kinds = (("first", "start"), ("fresh", "resume-run"), ("fresh", "resume-run"))
            (out / "sessions.jsonl").write_text("".join(json.dumps(
                {"row": "start", "n": n + 1, "kind": kind, "reason": reason, "host": "codex", "t": stamps[start] - 1.0,
                 "events_line": start, "told": None if kind == "first" else TOLD}) + "\n"
                for n, (start, (kind, reason)) in enumerate(zip(starts, kinds))))
            got = metrics.collect(out, run_dir)
        two, three = (b["reorientation"] for b in got["fresh_starts"])
        self.assertEqual((two["measured"], two["reason"][:30]), (False, "no tool call submitted an acti"))
        self.assertEqual((three["measured"], three["tool_calls"]), (True, 2))
        self.assertEqual(three["recovery"]["first_next"]["call"], 1)

    def test_a_stream_that_is_not_groks_lists_no_compaction_even_if_a_look_alike_event_appears(self):
        # Compactions are Grok's signal (GROK_SIGNALS): on another host the count is unmeasured, so the list stays empty too.
        stream = [{"type": "available_commands", "commands": []}, {"type": "auto_compact_completed"},
                  {"type": "end", "stopReason": "end_turn", "num_turns": 1, "total_cost_usd": 1.0}]
        got = MAIN.collect_stream(stream, [("A1", "intake", "done", 105.0)])
        self.assertIsNone(got["compactions"])
        self.assertEqual(got["fresh_starts"], [])

    def after_kill(self, end_revision, start_revision, next_output):
        """The `after_kill` of a two-session folder: the first session ended at ``end_revision``, the fresh one was launched
        at ``start_revision`` and its first `next` showed ``next_output``."""
        old, fresh = Stream(first=100.0).start(), Stream(first=300.0).start()
        old.shell(1.0, "ls")
        fresh.next(after=1.0, output=next_output)
        fresh.complete("nav-b", after=1.0)
        lines = [event for _l, event in old.rows] + [event for _l, event in fresh.rows]
        stamps = {**old.stamps, **{len(old.rows) + n: t for n, t in fresh.stamps.items()}}
        position = lambda revision: None if revision is None else {  # noqa: E731
            "status": "active", "stage": "spec", "revision": revision, "accepted": 1, "last_accepted": None}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in lines))
            (out / "timeline.jsonl").write_text("".join(json.dumps({"line": n, "t": t}) + "\n" for n, t in stamps.items()))
            run_dir = out / "run"
            MAIN.write_engine_records(run_dir, [("nav-b", "spec", "done", float(int(fresh.t - 0.05)))], status="active", stage="spec")
            rows = [{"row": "start", "n": 1, "kind": "first", "reason": "start", "host": "codex", "t": 99.0, "events_line": 0,
                     "told": None, "engine": None},
                    {"row": "end", "n": 1, "t": 200.0, "events_line": len(old.rows), "status": "stopped", "returncode": -9,
                     "engine": position(end_revision)},
                    {"row": "start", "n": 2, "kind": "fresh", "reason": "resume-run", "host": "codex", "t": 299.0,
                     "events_line": len(old.rows), "told": TOLD, "engine": position(start_revision)}]
            (out / "sessions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
            return metrics.collect(out, run_dir)["fresh_starts"][0]["after_kill"]

    def test_the_engine_revision_at_the_kill_is_compared_with_the_one_the_fresh_sessions_first_next_showed(self):
        quiet = self.after_kill(11, 11, "ShipLoop navigator | spec | revision 11\n")
        self.assertEqual(quiet, {"end_revision": 11, "start_revision": 11, "first_next_revision": 11, "moved": False})
        moved = self.after_kill(11, 11, "ShipLoop navigator | spec | revision 12\n")
        self.assertEqual((moved["moved"], moved["first_next_revision"]), (True, 12),
                         "something advanced the engine after the kill: an in-flight command of the killed session")
        before_launch = self.after_kill(11, 12, "ShipLoop navigator | spec | revision 12\n")
        self.assertTrue(before_launch["moved"], "it moved between the end row and the launch")

    def test_a_missing_revision_leaves_the_comparison_unknown_not_unmoved(self):
        only_one = self.after_kill(None, None, "ShipLoop navigator | spec | revision 12\n")
        self.assertEqual((only_one["moved"], only_one["end_revision"]), (None, None))
        two = self.after_kill(None, 12, "ShipLoop navigator | spec | revision 12\n")
        self.assertEqual(two["moved"], False, "two known values that agree")

    def test_a_compaction_has_no_kill_to_compare(self):
        first = MAIN.collect_stream([usage(1), {"type": "auto_compact_completed"}, usage(2)], [])["fresh_starts"]
        self.assertEqual([b["kind"] for b in first], ["compaction"])
        self.assertNotIn("after_kill", first[0])

    def test_a_row_the_reader_cannot_use_is_skipped_and_never_takes_the_metrics_down(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text(json.dumps({"type": "available_commands", "commands": []}) + "\n")
            (out / "sessions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in (
                {"row": "start", "n": 1, "kind": "fresh", "reason": "resume-run", "host": "grok", "events_line": None, "told": TOLD},
                {"row": "start", "n": 2, "kind": "fresh", "reason": "resume-run", "host": "grok", "events_line": 0,
                 "told": "not a mapping", "engine": "nor this"})))
            got = metrics.collect(out, None)
        self.assertEqual([b["n"] for b in got["fresh_starts"]], [2], "the row with no line is skipped, the other is read")
        self.assertEqual(got["fresh_starts"][0]["reorientation"]["recovery"]["told"], None)

    def test_a_defect_in_the_passive_record_never_takes_the_runs_metrics_down(self):
        # An earlier per_stage defect crashed after the host had finished and cost the run its metrics and its review export.
        with mock.patch.object(metrics, "fresh_starts", side_effect=ValueError("boom")):
            got = MAIN.collect_stream(MAIN.claude_stream(["ls"]), [("A1", "intake", "done", 105.0)])
        self.assertEqual(got["fresh_starts"], [])
        self.assertTrue(got["fresh_starts_unmeasured"].startswith("failed"), got["fresh_starts_unmeasured"])
        self.assertIn("ValueError: boom", got["fresh_starts_unmeasured"])
        self.assertEqual(len(got["stages"]), 1, "the rest of the metrics are intact")

    def test_a_codex_compaction_is_placed_from_its_rollouts(self):
        accepted = [("A1", "intake", "done", 105.0), ("A2", "spec", "done", 113.0)]
        root = MAIN.thread_calls("root", "root", 10000, [(101, "r1", 1000, False), (104.5, "r2", 3000, False),
                                                       (108, "rq", 3500, True), (110, "r3", 2000, False)])
        got = MAIN.collect_stream(MAIN.codex_stream(12), accepted, rollout_files=[root])
        compactions = [b for b in got["fresh_starts"] if b["kind"] == "compaction"]
        self.assertEqual(len(compactions), 1)
        self.assertEqual((compactions[0]["host"], compactions[0]["t"]), ("codex", 108.01))
        self.assertEqual(compactions[0]["events_line"], 9, "the first event the runner stamped after the compaction (t 109)")
        self.assertTrue(got["fresh_starts_unmeasured"].startswith("not recorded"), "collect_stream writes no sessions.jsonl")
        self.assertEqual(got["compactions"], 1)

    def test_a_claude_stream_lists_no_compaction_because_none_is_detected(self):
        got = MAIN.collect_stream(MAIN.claude_stream(["ls"]), [("A1", "intake", "done", 105.0)])
        self.assertEqual(got["fresh_starts"], [])


class PerStageContextTest(unittest.TestCase):
    """The two corrections the Run Review fork asked of per_stage: a stage with no events has no `context`, and a Grok model
    call is counted (a mixed-host run showed `calls: 0` beside a real peak)."""

    ACCEPTED = [("A1", "intake", "done", 104.5), ("A2", "spec", "done", 111.5), ("A3", "plan", "done", 118.5)]

    def test_a_stage_with_no_events_has_no_context_instead_of_a_zero_call_one(self):
        accepted = [{"stage": "a", "outcome": "done", "t": 105.0}, {"stage": "b", "outcome": "done", "t": 112.0},
                    {"stage": "c", "outcome": "done", "t": 125.0}]
        stamps = {n: 100.0 + n for n in range(30)}
        turns = [{"t": 101.5, "input": 10, "call": True}, {"t": 106.0, "input": 40, "call": True}]
        rows = metrics.per_stage(accepted, turns, {}, stamps, None, context_window=100)
        self.assertEqual([r["context"]["calls"] for r in rows[:2]], [1, 1])
        self.assertNotIn("context", rows[2], "no event fell in stage c: nothing was measured there, which is not 0 calls")
        self.assertEqual(rows[2]["turns"], 0, "the existing count of events in the window is unchanged")

    def test_a_grok_usage_event_is_a_model_call_and_counts_in_its_stage(self):
        stream = [usage(1000), usage(3000), usage(2000), {"type": "tool_call", "toolCallId": "a", "rawInput": {"command": "ls"}},
                  usage(500), usage(700), usage(9000), usage(400),
                  {"type": "end", "stopReason": "end_turn", "num_turns": 7, "total_cost_usd": 1.0}]
        # One second between events from t 100; the engine's stamps are whole seconds: A1 at 104, A2 at 111.
        got = MAIN.collect_stream(stream, self.ACCEPTED[:2])
        self.assertEqual([r["context"] for r in got["stages"]], [
            {"calls": 4, "peak": 3000, "peakPct": None},      # usage events at t 100, 101, 102 and 104
            {"calls": 3, "peak": 9000, "peakPct": None}], "Grok reports no window: peakPct is None, not 0")
        self.assertEqual(got["model_calls"], 7)
        self.assertEqual(sum(r["context"]["calls"] for r in got["stages"]), got["model_calls"],
                         "the stages add up to the whole-run count the same events give")

    def test_a_run_two_hosts_worked_on_counts_the_calls_of_both(self):
        # r2's shape: Grok usage events, then a Claude resume whose assistant messages carry `id` and usage.
        claude = [{"type": "assistant", "message": {"id": f"m{n}", "usage": {"input_tokens": 50 * (n + 1)}, "content": [
            {"type": "text", "text": "x"}]}} for n in range(3)]
        stream = [usage(1000), usage(2000), *claude, usage(10), usage(20), usage(30), usage(40), usage(50), usage(60)]
        got = MAIN.collect_stream(stream, [("A1", "intake", "done", 105.0), ("A2", "spec", "done", 109.0)])
        self.assertEqual([r["context"]["calls"] for r in got["stages"]], [6, 4])
        self.assertEqual([r["context"]["peak"] for r in got["stages"]], [2000, 50])

    def test_the_existing_mixed_row_behaviour_is_kept_rows_without_a_call_key_are_ignored(self):
        # test/shiploop-e2e.test.py :: MixedHostTurnsTest, restated: a row with no `call` key adds no call.
        accepted = [{"stage": "a", "outcome": "done", "t": 105.0}, {"stage": "b", "outcome": "done", "t": 112.0}]
        stamps = {n: 100.0 + n for n in range(21)}
        turns = [{"t": 101.5, "input": 10, "call": True}, {"t": 102.0, "input": 20},
                 {"t": 103.0, "input": 30, "call": False}, {"t": 106.0, "input": 40, "call": True}]
        rows = metrics.per_stage(accepted, turns, {}, stamps, None, context_window=100)
        self.assertEqual([(r["context"]["calls"], r["context"]["peak"], r["turns"]) for r in rows], [(1, 30, 3), (1, 40, 1)])


README = ROOT / "test" / "shiploop_e2e" / "README.md"


class ReadmeRecipeTest(unittest.TestCase):
    """The README's S-6 recipe: a watcher that creates `<output>/stop` at a stage boundary, then `--resume-run`. The watcher in
    the README is the one run here, so the recipe cannot rot into a snippet nobody ran."""

    def section(self) -> str:
        text = README.read_text()
        start = text.index("### A fresh context (S-6)")
        return text[start:text.index("\n### ", start + 5)]

    def watcher(self) -> str:
        found = re.search(r"```python\n(# stop-watcher.*?)```", self.section(), re.S)
        self.assertIsNotNone(found, "the README holds no watcher block starting with `# stop-watcher`")
        return found.group(1)

    def run_watcher(self, out: Path, where: str, stage: str, wait: float = 15.0):
        return subprocess.run([sys.executable, "-", str(out), where, stage], input=self.watcher(), text=True, cwd=ROOT,
                              capture_output=True, timeout=wait)

    def folder(self, tmp: str, accepted: list, stage: str, inbox: tuple = ()) -> Path:
        out = Path(tmp)
        run_dir = out / ".shiploop-runs" / "work-1" / "run"
        MAIN.write_engine_records(run_dir, accepted, status="active", stage=stage)
        (run_dir / "inbox").mkdir()
        for action in inbox:
            (run_dir / "inbox" / f"{action}.md").write_text("result\n")
        return out

    def test_after_a_stage_the_watcher_stops_the_run_once_the_stages_row_is_in_the_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.folder(tmp, [("A1", "intake", "done", 100.0), ("A2", "spec", "done", 110.0)], "test-strategy")
            done = self.run_watcher(out, "after", "spec")
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertTrue((out / "stop").is_file())

    def test_after_a_stage_that_is_not_accepted_yet_it_keeps_waiting_and_stops_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.folder(tmp, [("A1", "intake", "done", 100.0)], "spec")
            with self.assertRaises(subprocess.TimeoutExpired):
                self.run_watcher(out, "after", "spec", wait=1.2)
            self.assertFalse((out / "stop").exists())

    def test_inside_a_stage_it_stops_when_a_result_file_waits_for_an_action_the_ledger_has_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.folder(tmp, [("A1", "intake", "done", 100.0)], "spec", inbox=("A1", "A2"))
            done = self.run_watcher(out, "inside", "spec")
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertTrue((out / "stop").is_file())

    def test_inside_a_stage_an_accepted_actions_result_file_is_not_the_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = self.folder(tmp, [("A1", "intake", "done", 100.0)], "spec", inbox=("A1",))
            with self.assertRaises(subprocess.TimeoutExpired):
                self.run_watcher(out, "inside", "spec", wait=1.2)
            self.assertFalse((out / "stop").exists())
        with tempfile.TemporaryDirectory() as tmp:
            out = self.folder(tmp, [("A1", "intake", "done", 100.0)], "plan", inbox=("A1", "A2"))
            with self.assertRaises(subprocess.TimeoutExpired):
                self.run_watcher(out, "inside", "spec", wait=1.2)
            self.assertFalse((out / "stop").exists(), "a result file waiting in another stage is not this stage's")

    def test_the_recipe_names_the_flags_the_audit_found_missing_and_the_overshoot(self):
        text = self.section()
        for needed in ("--prompt", "--check", "--planning-review none", "--improve-skill", "--resume-run",
                       "--plugin-dir", "2.25 s", "after_kill", "fresh_starts", "never sits inside an Improve park"):
            self.assertIn(needed, text)
        self.assertNotIn("--case hello --prompt", text, "--case and --prompt cannot be combined")


class SessionLogTest(unittest.TestCase):
    """sessions.jsonl: the harness's append-only record of every host launch and every session end."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.out = Path(self._tmp.name)

    def start(self, **kw):
        import sessionlog
        return sessionlog.start(self.out, **{"kind": "first", "reason": "start", "host": "grok", "model": "m",
                                             "events_line": 0, "told": None, **kw})

    def test_a_start_row_and_its_end_row_are_paired_by_the_session_number(self):
        import sessionlog
        first = self.start()
        sessionlog.end(self.out, first, t=1002.0, events_line=40, status="exited", returncode=0,
                       engine={"status": "active", "revision": 7, "stage": "spec", "accepted": 3,
                               "last_accepted": {"stage": "research", "action": "nav-3"}})
        second = self.start(kind="fresh", reason="resume-run", events_line=40,
                            told={"cli": "/p/shiploop", "run_dir": "/r/run"})
        self.assertEqual((first["n"], second["n"]), (1, 2))
        got = sessionlog.read(self.out)
        self.assertEqual([(g["n"], g["kind"], g["reason"], g["events_line"]) for g in got],
                         [(1, "first", "start", 0), (2, "fresh", "resume-run", 40)])
        self.assertEqual(got[0]["end"], {"row": "end", "n": 1, "t": 1002.0, "events_line": 40, "status": "exited",
                                         "returncode": 0, "engine": {"status": "active", "revision": 7, "stage": "spec",
                                                                     "accepted": 3, "last_accepted": {
                                                                         "stage": "research", "action": "nav-3"}}})
        self.assertIsNone(got[1]["end"], "a harness killed mid-session writes no end row: the start row stays")
        self.assertEqual(got[1]["told"], {"cli": "/p/shiploop", "run_dir": "/r/run"}, "stored as values")

    def test_the_start_row_can_carry_the_ledger_as_the_session_inherits_it(self):
        import sessionlog
        engine = {"status": "active", "stage": "spec", "revision": 11, "accepted": 4,
                  "last_accepted": {"stage": "research", "action": "nav-4"}}
        row = self.start(kind="fresh", reason="resume-run", engine=engine)
        self.assertEqual(sessionlog.read(self.out)[0]["engine"], engine)
        self.assertIsNone(self.start()["engine"], "no ShipLoop state yet: the first launch records none")

    def test_the_file_is_append_only_one_json_object_per_line(self):
        import sessionlog
        first = self.start()
        before = (self.out / sessionlog.SESSIONS).read_text()
        sessionlog.end(self.out, first, t=1.0, events_line=1, status="exited", returncode=0, engine=None)
        self.start(kind="continued", reason="resume-loop", resumed_session="sess-1")
        text = (self.out / sessionlog.SESSIONS).read_text()
        self.assertTrue(text.startswith(before), "earlier rows are never rewritten")
        rows = [json.loads(line) for line in text.splitlines()]
        self.assertEqual([r["row"] for r in rows], ["start", "end", "start"])
        self.assertEqual(rows[2]["resumed_session"], "sess-1")

    def test_no_file_is_not_recorded_and_an_empty_file_is_recorded_empty(self):
        import sessionlog
        self.assertIsNone(sessionlog.read(self.out))
        (self.out / sessionlog.SESSIONS).write_text("")
        self.assertEqual(sessionlog.read(self.out), [])

    def test_an_unreadable_line_is_skipped_and_the_rest_are_read(self):
        import sessionlog
        self.start()
        with (self.out / sessionlog.SESSIONS).open("a") as handle:
            handle.write("{not json\n[1, 2]\n")
        self.start(kind="fresh", reason="after-interrupt")
        self.assertEqual([g["n"] for g in sessionlog.read(self.out)], [1, 2])

    def test_a_folder_that_cannot_be_written_never_raises_into_the_run(self):
        import sessionlog
        gone = self.out / "no" / "such" / "folder"
        row = sessionlog.start(gone, kind="first", reason="start", host="claude", model="m", events_line=0, told=None)
        sessionlog.end(gone, row, t=1.0, events_line=0, status="exited", returncode=0, engine=None)
        self.assertEqual(row["n"], 1)
        self.assertIsNone(sessionlog.read(gone))


class EngineSectionTest(unittest.TestCase):
    """metrics.engine_position: the ledger's revision and last accepted action, read at a session's end."""

    def test_the_position_names_the_last_accepted_action_and_how_many_there_are(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            MAIN.write_engine_records(run_dir, [("A1", "intake", "done", 100.0), ("A2", "spec", "done", 110.0)],
                                      status="active", stage="test-strategy")
            position = metrics.engine_position(run_dir)
        self.assertEqual(position, {"status": "active", "stage": "test-strategy", "revision": None, "accepted": 2,
                                    "last_accepted": {"stage": "spec", "action": "A2"}})

    def test_no_run_state_is_none_and_a_run_with_no_acceptance_has_no_last_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(metrics.engine_position(None))
            self.assertIsNone(metrics.engine_position(Path(tmp) / "run"))
            MAIN.write_engine_records(Path(tmp) / "run", [], status="active", stage="intake")
            self.assertEqual(metrics.engine_position(Path(tmp) / "run"),
                             {"status": "active", "stage": "intake", "revision": None, "accepted": 0, "last_accepted": None})


class EventsLineCountTest(unittest.TestCase):
    """The first line of a session is a number in events.jsonl and in the runner's timeline: a session killed mid-line
    must not make the next session's first event share a line with it (the missed unknown of the audit)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.out = Path(self._tmp.name)
        # launch() reaps what a session left listening under the folder: that reads the machine's process table, which no test does
        patched = MAIN.nothing_listens()
        patched.__enter__()
        self.addCleanup(patched.__exit__, None, None, None)

    def test_the_count_is_the_lines_already_written_and_a_missing_file_is_zero(self):
        self.assertEqual(run.events_line_count(self.out / "events.jsonl"), 0)
        (self.out / "events.jsonl").write_text('{"type": "a"}\n{"type": "b"}\n')
        self.assertEqual(run.events_line_count(self.out / "events.jsonl"), 2)

    def test_a_last_line_without_its_newline_is_ended_and_counted_once(self):
        path = self.out / "events.jsonl"
        path.write_bytes(b'{"type": "a"}\n{"type": "tool_ca')
        self.assertEqual(run.events_line_count(path), 2)
        self.assertEqual(path.read_bytes(), b'{"type": "a"}\n{"type": "tool_ca\n')
        self.assertEqual(run.events_line_count(path), 2, "idempotent")

    def test_a_session_appended_after_a_killed_one_starts_on_a_line_of_its_own(self):
        work = self.out / "work"
        work.mkdir()
        (self.out / "events.jsonl").write_bytes(b'{"type": "assistant"}\n{"type": "tool_ca')
        line = '{"type": "available_commands", "commands": []}'
        done = run.launch([sys.executable, "-c", f"print({line!r})"], work, self.out, dict(os.environ), 60,
                          watch=False, first=False)
        self.assertEqual(done["status"], "exited")
        lines = (self.out / "events.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(json.loads(lines[2])["type"], "available_commands")
        stamps = metrics.timeline(self.out / "timeline.jsonl")
        self.assertIn(2, stamps, "the new session's first event is line 2, as the start row will say")


class ResumeToldTest(unittest.TestCase):
    """`told` is what the resume prompt named, stored as values."""

    def test_told_holds_exactly_the_cli_and_run_directory_the_prompt_names(self):
        cli = Path("/p/build/plugins/skill-craft/skills/shiploop/scripts/shiploop")
        told = run.resume_told("/r/.shiploop-runs/w/run", cli)
        self.assertEqual(told, {"cli": str(cli), "run_dir": "/r/.shiploop-runs/w/run"})
        self.assertIn(f'python3 "{told["cli"]}" next --run-dir "{told["run_dir"]}"',
                      run.resume_prompt("/r/.shiploop-runs/w/run", cli))

    def test_a_prompt_that_names_no_run_tells_nothing(self):
        self.assertIsNone(run.resume_told(None, Path("/p/cli")))
        self.assertNotIn("next --run-dir", run.resume_prompt(None, Path("/p/cli")))


class SessionsRecordThroughMainTest(MAIN.PrintedCase):
    """run.main writes sessions.jsonl at the three places it launches a host: the first launch (or --resume-run), the
    fresh session after --interrupt-at, and a Grok or Codex resume inside the run."""

    def setUp(self):
        super().setUp()
        MAIN.isolate_git(self)
        (self.plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "9.9.9"}))
        patched = mock.patch.object(run, "POLL_SECONDS", 0.2, create=True)  # the interrupt test waits on the poll
        patched.start()
        self.addCleanup(patched.stop)

    def sessions(self, result: dict) -> list[dict]:
        import sessionlog
        return sessionlog.read(Path(result["output"]))

    def resume(self, out: Path, host: str) -> None:
        released = {"origin_main": "a" * 40, "local_head": "a" * 40, "local_behind_main": False,
                    "catalog_version": "9.9.9", "shiploop_version": None, "unreleased": [], "ci": "success"}
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(run, "released_versions", return_value=released):
            run.main(["--host", host, f"--{host}-bin", str(self.fakes[host]), "--resume-run", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), "--max-resumes", "0"])

    def test_a_first_launch_writes_a_start_row_and_an_end_row_on_every_host(self):
        for host in ("claude", "grok", "codex"):
            with self.subTest(host):
                code, result, _ = self.invoke_printed(host, "done")
                got = self.sessions(result)
                self.assertEqual(len(got), 1)
                start = got[0]
                self.assertEqual((start["n"], start["kind"], start["reason"], start["host"], start["events_line"],
                                  start["told"]), (1, "first", "start", host, 0, None))
                lines = (Path(result["output"]) / "events.jsonl").read_text().splitlines()
                self.assertEqual((start["end"]["status"], start["end"]["returncode"], start["end"]["events_line"]),
                                 ("exited", 0, len(lines)))
                self.assertLessEqual(start["t"], start["end"]["t"])
                self.assertEqual(start["end"]["engine"]["status"], "done")

    def test_the_start_row_is_on_disk_before_the_host_is_launched(self):
        import sessionlog
        seen = []

        def peek(argv, work, out, *a, **kw):
            seen.append(sessionlog.read(out))
            raise RuntimeError("the harness dies here")

        with mock.patch.object(run, "launch", side_effect=peek), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError):
                run.main(["--host", "claude", "--claude-bin", str(self.fakes["claude"]), "--output", str(self.tmp / "o"),
                          "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        self.assertEqual(len(seen[0]), 1)
        self.assertEqual((seen[0][0]["kind"], seen[0][0]["end"]), ("first", None))
        final = sessionlog.read(self.tmp / "o")
        self.assertEqual(final[0]["end"]["status"], "crashed", "an exception still leaves its end row")

    def test_a_grok_resume_inside_the_run_is_a_continued_session_that_names_the_session_it_continues(self):
        code, result, _ = self.invoke_printed("grok", "resume")
        got = self.sessions(result)
        self.assertEqual([(g["n"], g["kind"], g["reason"]) for g in got], [(1, "first", "start"),
                                                                           (2, "continued", "resume-loop")])
        self.assertEqual(got[1]["resumed_session"], "sess-1")
        self.assertEqual(got[1]["events_line"], got[0]["end"]["events_line"])
        self.assertEqual(got[0]["end"]["engine"]["status"], "active")
        self.assertEqual(got[0]["end"]["engine"]["revision"], 25)
        prompt = json.loads(Path(str(self.log) + ".sessions").read_text().splitlines()[1])["prompt"]
        self.assertIn(f'python3 "{got[1]["told"]["cli"]}" next --run-dir "{got[1]["told"]["run_dir"]}"', prompt)
        self.assertEqual(got[1]["told"]["cli"], str(self.cli))

    def test_a_resume_run_is_a_fresh_session_that_was_told_the_runs_own_cli_and_directory(self):
        code, first, _ = self.invoke_printed("claude", "active")
        os.environ["FAKE_MODE"] = "active"
        self.resume(Path(first["output"]), "claude")
        import sessionlog
        got = sessionlog.read(Path(first["output"]))
        self.assertEqual([(g["n"], g["kind"], g["reason"]) for g in got], [(1, "first", "start"),
                                                                           (2, "fresh", "resume-run")])
        self.assertEqual(got[1]["events_line"], got[0]["end"]["events_line"])
        self.assertEqual(got[1]["told"]["cli"], str(self.cli))
        self.assertIsNone(got[0]["engine"], "the first launch began before any ShipLoop state existed")
        self.assertEqual((got[1]["engine"]["status"], got[1]["engine"]["revision"]), ("active", 25),
                         "the ledger as the fresh session inherits it, read before the host started")
        self.assertEqual(got[1]["engine"], got[0]["end"]["engine"])
        argv = self.seen()["argv"]
        prompt = argv[argv.index("-p") + 1]
        self.assertIn(f'python3 "{got[1]["told"]["cli"]}" next --run-dir "{got[1]["told"]["run_dir"]}"', prompt)

    def test_the_session_after_an_interrupt_is_fresh_and_the_killed_one_ends_interrupted(self):
        code, result, _ = self.invoke_printed("claude", "chain-hang", "--interrupt-at", "chain-launched")
        got = self.sessions(result)
        self.assertEqual([(g["n"], g["kind"], g["reason"], g["end"]["status"]) for g in got],
                         [(1, "first", "start", "interrupted"), (2, "fresh", "after-interrupt", "exited")])
        self.assertEqual(got[1]["events_line"], got[0]["end"]["events_line"])
        self.assertEqual(got[1]["told"]["cli"], str(self.cli))
        self.assertTrue(got[1]["told"]["run_dir"].endswith("/run"))

    def test_a_regrade_launches_no_host_and_adds_no_row(self):
        code, first, _ = self.invoke_printed("grok", "done")
        before = (Path(first["output"]) / "sessions.jsonl").read_text()
        self.resume(Path(first["output"]), "grok")
        self.assertEqual((Path(first["output"]) / "sessions.jsonl").read_text(), before)


if __name__ == "__main__":
    unittest.main()
