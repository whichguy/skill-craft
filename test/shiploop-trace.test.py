#!/usr/bin/env python3
"""The run trace (RUN/trace.jsonl) and its reader (`shiploop trace`).

The owner asked to inspect a run while it runs: what steps have been run, what is still scheduled, what prompt
messages were injected (2026-10-25).  These tests drive real ShipLoop runs in temporary directories through the CLI
(init, a reprint, a refused and an accepted callback, pause and resume), the keepalive stop hook with a recorded host
payload, and in-memory states saved with the navigator for the later stages.  No host CLI or model is started.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
sys.path.insert(0, str(SCRIPTS))

import shiploop_keepalive as keepalive  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_trace as trace  # noqa: E402

ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "SHIPLOOP_PROGRESS": "off"}
INTAKE = '```shiploop-state\n{"outcome": "done", "summary": "Intake done.", "headline": "Scope: one greeting script", ' \
         '"evidence_refs": []}\n```\n'


def _load(name: str, file: str):
    """A sibling test file as a module (their names have hyphens), for its fixture class."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "test" / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


keepalive_tests = _load("shiploop_keepalive_trace_fixture", "shiploop-keepalive.test.py")
status_display = _load("shiploop_status_display_trace_fixture", "shiploop-status-display.test.py")


def events(run: Path) -> list[dict]:
    return [json.loads(line) for line in (run / trace.TRACE_FILE).read_text(encoding="utf-8").splitlines()]


class CliRun(unittest.TestCase):
    """A real run in a temporary directory, driven through the CLI."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-trace-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.repo, self.run = self.base / "repo", self.base / "run"
        self.repo.mkdir()
        self.ok("init", "--repo", str(self.repo), "--prompt", "Add a greeting script.")

    def cli(self, *argv: str) -> subprocess.CompletedProcess:
        args = [argv[0], "--run-dir", str(self.run), *argv[1:]] if argv[0] != "trace" else [*argv]
        return subprocess.run([sys.executable, "-B", str(CLI), *args], env=ENV, text=True, capture_output=True,
                              timeout=60)

    def ok(self, *argv: str) -> subprocess.CompletedProcess:
        result = self.cli(*argv)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def action(self) -> str:
        return navigator.current_action(store.read_record(self.run / "state.md"))["id"]

    def drive(self) -> tuple[str, str]:
        """init (setUp), next, a refused callback, the accepted intake, pause, resume and status."""
        intake = self.action()
        self.ok("next")
        (self.run / "inbox" / f"{intake}.md").write_text("no record here\n", encoding="utf-8")
        refused = self.cli("complete", "--action", intake)
        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        (self.run / "inbox" / f"{intake}.md").write_text(INTAKE, encoding="utf-8")
        self.ok("complete", "--action", intake)
        discovery = self.action()
        self.ok("pause", "--reason", "owner break")
        self.ok("resume")
        self.ok("status")
        return intake, discovery


class TraceWriterTests(CliRun):
    def test_each_command_and_packet_is_one_line_in_order(self) -> None:
        intake, discovery = self.drive()
        rows = events(self.run)
        self.assertEqual([(row["kind"], row.get("verb")) for row in rows], [
            ("packet", None), ("command", "init"),
            ("packet", None), ("command", "next"),
            ("command", "complete"),                      # refused: no packet
            ("packet", None), ("command", "complete"),    # accepted: the discovery packet, then the command
            ("packet", None), ("command", "pause"),
            ("packet", None), ("command", "resume"),
            ("command", "status"),
        ])
        init, refused, accepted = rows[1], rows[4], rows[6]
        self.assertEqual((init["exit"], init["rev"], init["cursor"]), (0, [None, 0], [None, intake]))
        self.assertEqual((refused["exit"], refused["action"], refused["rev"]), (2, intake, [0, 0]))
        self.assertIn("exactly one shiploop-state fence", refused["error"])
        self.assertEqual(accepted["accepted"], [{"action": intake, "stage": "intake", "item": None, "outcome": "done"}])
        self.assertEqual((accepted["stage"], accepted["cursor"]), (["intake", "discovery"], [intake, discovery]))
        self.assertEqual(rows[8]["status"], "paused")
        for row in rows:
            self.assertEqual((row["v"], type(row["ts"]), row["at"][-1]), (1, float, "Z"))

    def test_every_packet_is_kept_as_sent(self) -> None:
        intake, discovery = self.drive()
        packets = [row for row in events(self.run) if row["kind"] == "packet"]
        self.assertEqual([row["stage"] for row in packets], ["intake", "intake", "discovery", "discovery", "discovery"])
        self.assertEqual(packets[0]["sha"], packets[1]["sha"])        # next reprinted the same text
        for row in packets:
            sent = (self.run / row["file"]).read_text(encoding="utf-8")
            self.assertEqual(len(sent), row["chars"])
            self.assertTrue(row["whole"])
            self.assertTrue(row["file"].startswith("packets/sent/"))
        # packets/<action>.md holds only the last text; the paused packet survives in sent/.
        paused = packets[3]
        self.assertEqual(paused["status"], "paused")
        self.assertNotEqual((self.run / "packets" / f"{discovery}.md").read_text(encoding="utf-8"),
                            (self.run / paused["file"]).read_text(encoding="utf-8"))

    def test_reads_and_displays_are_not_activity(self) -> None:
        before = (self.run / trace.TRACE_FILE).read_bytes()
        subprocess.run([sys.executable, "-B", str(CLI), "hook-status", "--run-dir", str(self.run)], env=ENV,
                       capture_output=True, timeout=60)
        self.ok("trace", "--run-dir", str(self.run))
        self.ok("trace", "--run-dir", str(self.run), "--json")
        self.assertEqual((self.run / trace.TRACE_FILE).read_bytes(), before)

    def test_a_failed_append_never_fails_and_never_follows_a_symlink(self) -> None:
        elsewhere = self.base / "elsewhere.jsonl"
        elsewhere.write_text("", encoding="utf-8")
        (self.run / trace.TRACE_FILE).unlink()
        (self.run / trace.TRACE_FILE).symlink_to(elsewhere)
        self.ok("next")                                   # the command still succeeds
        self.assertEqual(elsewhere.read_text(encoding="utf-8"), "")
        self.assertFalse(trace.record(self.run, "command", verb="x"))
        self.assertFalse(trace.record(self.base / "not-a-run", "command", verb="x"))

    def test_the_trace_stops_growing_at_its_cap(self) -> None:
        size = (self.run / trace.TRACE_FILE).stat().st_size
        with mock.patch.object(trace, "TRACE_LIMIT", size):
            self.assertFalse(trace.record(self.run, "command", verb="x"))
            model = trace.build(self.run)
        self.assertTrue(model["run"]["capped"])
        self.assertEqual((self.run / trace.TRACE_FILE).stat().st_size, size)


class TraceReaderTests(CliRun):
    def test_the_digest_shows_now_the_plan_steps_and_recent_events(self) -> None:
        intake, discovery = self.drive()
        text = self.ok("trace", "--run-dir", str(self.run), "--last", "0").stdout
        self.assertTrue(text.startswith("=== ShipLoop trace ===\n") and text.endswith("=== end ShipLoop trace ===\n"))
        self.assertIn(f"Now:      discovery · action {discovery}", text)
        self.assertIn("  Preparation                 ✓intake!1 ▶discovery ·research ·spec", text)  # !1: one refusal
        self.assertIn("  Work items                  (set by the plan stage)", text)
        self.assertIn("  Release                     9 stages pending", text)
        self.assertIn("Steps run (1 of 1 shown):", text)
        self.assertIn("intake                       done", text)
        self.assertIn("Scope: one greeting script", text)
        self.assertIn("refused: RUN/inbox/" + intake + ".md: record must contain exactly one shiploop-state fence", text)
        self.assertIn("reprint, same text", text)
        self.assertIn("accepted intake (done)", text)
        self.assertIn("Totals:   1 accepted · 7 commands · 1 refused · 0 checks failed · 5 packets (1 reprints)", text)

    def test_a_failed_check_only_run_is_a_check_not_a_refusal(self) -> None:
        intake = self.action()
        (self.run / "inbox" / f"{intake}.md").write_text('```shiploop-state\n{"outcome": "done"}\n```\n', encoding="utf-8")
        self.assertNotEqual(self.cli("complete", "--action", intake, "--check-only").returncode, 0)
        model = trace.build(self.run)
        self.assertEqual((model["counts"]["refusals"], model["counts"]["checks_failed"]), (0, 1))
        self.assertIn("check: result requires outcome and summary", trace.digest(model))

    def test_one_action_lists_its_packets_commands_and_files(self) -> None:
        intake, _ = self.drive()
        text = self.ok("trace", "--run-dir", str(self.run), "--action", intake[-10:]).stdout
        self.assertIn(f"=== ShipLoop trace: action {intake} ===", text)
        self.assertIn("Step:     #1 intake, done at", text)
        self.assertIn("Packets sent: 2", text)
        self.assertIn("      RUN/inbox/" + intake + ".md: record must contain exactly one shiploop-state fence", text)
        self.assertIn(f"RUN/results/{intake}.md", text)
        missing = self.cli("trace", "--run-dir", str(self.run), "--action", "nav-")
        self.assertEqual(missing.returncode, 2)
        self.assertIn("no single action matches", missing.stderr)

    def test_json_is_the_whole_model(self) -> None:
        self.drive()
        model = json.loads(self.ok("trace", "--run-dir", str(self.run), "--json").stdout)
        self.assertEqual(model["schema"], trace.SCHEMA)
        self.assertEqual([row["phase"] for row in model["plan"]], ["preparation", "work", "release"])
        self.assertEqual(model["counts"]["refusals"], 1)
        self.assertEqual([step["stage"] for step in model["steps"]], ["intake"])
        self.assertEqual(model["steps"][0]["refusals"], 1)
        self.assertEqual(model["steps"][0]["packets"], 2)
        # A command without --action belongs to the action current when it ran.
        status = [row for row in model["events"] if row.get("verb") == "status"][0]
        self.assertEqual(status["for_action"], model["now"]["action"])

    def test_the_page_embeds_the_model_and_each_packet_screened(self) -> None:
        self.drive()
        sent = [row for row in events(self.run) if row["kind"] == "packet"][-1]
        path = self.run / sent["file"]
        path.write_text(path.read_text(encoding="utf-8") + "api_key=sk-live-abcdefghijklmnop1234567890\n", encoding="utf-8")
        printed = self.ok("trace", "--run-dir", str(self.run), "--html").stdout.strip()
        self.assertEqual(printed, str(self.run / trace.PAGE))
        page = (self.run / trace.PAGE).read_text(encoding="utf-8")
        self.assertNotIn(trace.DATA_MARK, page)
        self.assertNotIn("sk-live-abcdefghijklmnop", page)
        start = page.index("const TRACE = ") + len("const TRACE = ")
        data = json.loads(page[start:page.index(";\n", start)].replace("<\\/", "</"))
        self.assertEqual(data["schema"], trace.SCHEMA)
        self.assertIn("[redacted sensitive value]", data["texts"][sent["file"]])
        self.assertEqual(set(data["texts"]), {row["file"] for row in events(self.run) if row["kind"] == "packet"})

    def test_a_progress_snapshot_also_writes_the_page(self) -> None:
        self.drive()
        self.assertFalse((self.run / trace.PAGE).exists())
        self.ok("view", "--run-dir", str(self.run))
        self.assertIn("const TRACE = {", (self.run / trace.PAGE).read_text(encoding="utf-8"))


class TracePlanTests(unittest.TestCase):
    """The plan of a run past planning, from saved state: work-item rows, the current slot, reruns and Improve."""

    def setUp(self) -> None:
        self.driver = status_display.StatusBlockTests()
        self.driver.setUp()
        self.addCleanup(self.driver.temp.cleanup)
        self.run = Path(self.driver.temp.name) / "run"
        self.run.mkdir()

    def saved(self, state: dict) -> dict:
        navigator.save(self.run, state)
        return trace.build(self.run)

    def test_work_items_appear_once_planned_and_the_current_slot_moves(self) -> None:
        state = self.driver.planned(self.driver.ROWS)
        state = self.driver.advance_to(state, "implement")
        model = self.saved(state)
        rows = {row["label"]: row for row in model["plan"]}
        self.assertEqual(list(rows), ["Preparation", "W1 Config loader refactor", "W2 Add --version flag", "Release"])
        self.assertTrue(all(slot["state"] == "done" for slot in rows["Preparation"]["slots"]))
        w1 = {slot["stage"]: slot for slot in rows["W1 Config loader refactor"]["slots"]}
        self.assertEqual(w1["implement"]["state"], "current")
        self.assertEqual(w1["step-plan"]["state"], "done")
        self.assertTrue(w1["step-plan"]["improve"])
        self.assertEqual({slot["state"] for slot in rows["W2 Add --version flag"]["slots"]}, {"pending"})
        self.assertEqual(model["now"]["item"], "W1")
        text = trace.digest(model)
        self.assertIn("W2 Add --version flag", text)
        self.assertIn("8 stages pending", text)
        self.assertIn("▶implement", text)

    def test_a_run_before_the_trace_reads_from_state_and_timeline(self) -> None:
        model = self.saved(self.driver.advance_to(self.driver.state(), "spec"))
        self.assertFalse(model["run"]["traced"])
        self.assertEqual([row["kind"] for row in model["events"]], ["accepted"] * 3)
        self.assertEqual([step["stage"] for step in model["steps"]], ["intake", "discovery", "research"])
        self.assertIn("this run has no trace.jsonl (it predates the trace)", trace.digest(model))


class TraceHookTests(keepalive_tests.KeepaliveTestCase):
    def test_a_stop_decision_records_what_the_hook_put_into_the_turn(self) -> None:
        self.hook("observe", "claude", self.payload("claude", "observe"))
        reply = self.hook("stop", "claude", self.payload("claude", "stop"))
        self.assertEqual(reply["decision"], "block")
        hooks = [row for row in events(self.run_dir) if row["kind"] == "hook"]
        self.assertEqual(len(hooks), 1)
        self.assertEqual((hooks[0]["hook"], hooks[0]["host"], hooks[0]["decision"]), ("stop", "claude", "continue"))
        self.assertEqual(hooks[0]["text"], reply["reason"])
        self.assertEqual(len(hooks[0]["session"]), 12)                # a hash, never the session id
        model = trace.build(self.run_dir)
        self.assertEqual(model["counts"]["continuations"], 1)
        self.assertIn("hook     stop → continue", trace.digest(model))

    def test_an_unbound_session_writes_nothing(self) -> None:
        before = (self.run_dir / trace.TRACE_FILE).read_bytes()
        self.hook("stop", "claude", self.payload("claude", "stop", "never-bound"))
        self.assertEqual((self.run_dir / trace.TRACE_FILE).read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
