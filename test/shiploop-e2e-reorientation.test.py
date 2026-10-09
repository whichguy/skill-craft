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
