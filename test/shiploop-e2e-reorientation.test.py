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
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import metrics  # noqa: E402

FIXTURES = ROOT / "test" / "fixtures" / "reorientation"


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


if __name__ == "__main__":
    unittest.main()
