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
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import state_home

state_home.isolate()


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
sys.path.insert(0, str(SCRIPTS))

import shiploop_keepalive as keepalive  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_trace as trace  # noqa: E402
import shiploop_trace_page as trace_page  # noqa: E402

ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "SHIPLOOP_PROGRESS": "off"}
INTAKE = '```shiploop-state\n{"outcome": "done", "summary": "S1 outcome: greet.py prints Hello and the name (fact).", ' \
         '"headline": "Scope: one greeting script", "evidence_refs": []}\n```\n'


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
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True, capture_output=True)
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

    def test_workspace_start_is_one_command_though_it_runs_init_or_next(self) -> None:
        # The 2026-10-25 E2E run recorded `workspace start` twice, as init and as workspace, both creating the run.
        repo, root = self.base / "source", self.base / "workspace"
        repo.mkdir()
        # No system or global Git config: a host's own filters (CI runners configure git-lfs) make workspace start refuse.
        env = {**ENV, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
        for argv in (["init", "-q", "-b", "main"], ["-c", "user.name=T", "-c", "user.email=t@example.invalid",
                                                     "commit", "-q", "--allow-empty", "-m", "baseline"]):
            subprocess.run(["git", "-C", str(repo), *argv], check=True, capture_output=True, env=env)
        start = ["workspace", "start", "--repo", str(repo), "--workspace-root", str(root), "--prompt", "Add a greeting."]
        for _ in range(2):                                # the second is an identical re-entry: it runs next
            result = subprocess.run([sys.executable, "-B", str(CLI), *start], env=env, text=True, capture_output=True,
                                    timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        commands = [row for row in events(root / "run") if row["kind"] == "command"]
        self.assertEqual([(row["verb"], row["rev"]) for row in commands], [("workspace", [None, 0]), ("workspace", [0, 0])])

    def test_every_packet_is_kept_as_sent(self) -> None:
        intake, discovery = self.drive()
        packets = [row for row in events(self.run) if row["kind"] == "packet"]
        self.assertEqual([row["stage"] for row in packets], ["intake", "intake", "discovery", "discovery", "discovery"])
        self.assertEqual(packets[0]["sha"], packets[1]["sha"])        # next reprinted the same text
        for row in packets:
            sent = (self.run / row["file"]).read_text(encoding="utf-8")
            self.assertEqual(len(sent), row["chars"])
            self.assertTrue(row["file"].startswith("packets/sent/"))
            # A packet over the print limit prints a head (how long depends on the install's paths); it is kept too.
            if not row["whole"]:
                self.assertEqual(len((self.run / row["head_file"]).read_text(encoding="utf-8")), row["printed"])
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


class TraceFormatTests(CliRun):
    """The journal's line format (audit of 2026-11-01, docs/shiploop-run-trace-journal.md)."""

    def test_unicode_line_ends_and_lone_surrogates_keep_their_line(self) -> None:
        """A raw U+2028 or U+0085 once cut a line for a reader splitting with splitlines(), and a lone surrogate (an
        undecodable file name) failed the encode and lost the whole row: every line is ASCII now."""
        text = "one\u2028two\u0085three " + os.fsdecode(b"caf\xe9.txt")
        self.assertTrue(trace.record(self.run, "command", verb="x", exit=2, error=text))
        raw = (self.run / trace.TRACE_FILE).read_bytes()
        raw.decode("ascii")                                          # pure ASCII: nothing for a reader to split on
        self.assertEqual([row["error"] for row in store.read_jsonl(self.run / trace.TRACE_FILE) if row.get("verb") == "x"],
                         [text])
        self.assertIn(text, [event.get("error") for event in trace.build(self.run)["events"]])

    def test_a_line_from_before_the_escape_still_reads_whole(self) -> None:
        """A line written raw (UTF-8, as before the audit) with a U+2028 inside a value is one line to the reader."""
        line = json.dumps({"v": 1, "ts": 1.0, "at": "x", "kind": "command", "verb": "y", "exit": 2, "error": "a\u2028b"},
                          ensure_ascii=False)
        with (self.run / trace.TRACE_FILE).open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        self.assertIn("a\u2028b", [row.get("error") for row in store.read_jsonl(self.run / trace.TRACE_FILE)])

    def test_long_text_is_cut_with_a_marker_and_short_text_is_not(self) -> None:
        self.assertTrue(trace.record(self.run, "hook", hook="stop", text="x" * (trace.TEXT_LIMIT + 1000), why="short"))
        row = events(self.run)[-1]
        self.assertTrue(row["text"].startswith("x" * trace.TEXT_LIMIT))
        self.assertTrue(row["text"].endswith("… [1000 more characters]"))
        self.assertEqual(row["why"], "short")

    def test_an_interrupted_command_is_not_a_refusal(self) -> None:
        """The start-route trials of 2026-11-01 stopped the host as `init` printed its packet; 45 such rows read exit 2
        with no text, so every reader counted a refusal ShipLoop never made."""
        import importlib.machinery
        import contextlib
        import io
        import shiploop_protocol as protocol

        loader = importlib.machinery.SourceFileLoader("shiploop_cli_for_interrupt", str(CLI))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        core = importlib.util.module_from_spec(spec)
        loader.exec_module(core)
        for raised, code, label in ((KeyboardInterrupt(), 130, "interrupted: "), (RuntimeError("boom"), 1, "crashed: ")):
            with mock.patch.object(navigator, "emit", side_effect=raised), \
                    mock.patch.dict(os.environ, {"SHIPLOOP_PROGRESS": "off"}), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                    self.assertRaises(type(raised)):
                protocol.main(core, ["next", "--run-dir", str(self.run)])
            row = events(self.run)[-1]
            self.assertEqual((row["verb"], row["exit"], row["crashed"]), ("next", code, type(raised).__name__))
            model = trace.build(self.run)
            self.assertEqual(model["counts"]["refusals"], 0)
            self.assertIn(label, trace.digest(model))
        self.assertEqual(model["counts"]["crashed"], 2)


class TraceReviewFindingTests(CliRun):
    """Findings of the independent review of the run trace (Sol, 2026-10-25), each pinned through the real route."""

    def test_a_fifo_in_place_of_the_trace_is_refused_not_waited_on(self) -> None:
        (self.run / trace.TRACE_FILE).unlink()
        os.mkfifo(self.run / trace.TRACE_FILE)
        self.assertFalse(trace.record(self.run, "command", verb="x"))     # returns at once: no reader, no block
        self.ok("next")                                                    # the command still runs (60 s timeout)

    def test_a_command_is_credited_only_with_its_own_transition(self) -> None:
        """Another command that runs once this one releases the lock must not be read as this command's work."""
        import importlib.machinery
        import contextlib
        import io
        import shiploop_progress as progress
        import shiploop_protocol as protocol

        loader = importlib.machinery.SourceFileLoader("shiploop_cli_for_trace", str(CLI))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        core = importlib.util.module_from_spec(spec)
        loader.exec_module(core)
        intake = self.action()
        (self.run / "inbox" / f"{intake}.md").write_text(INTAKE, encoding="utf-8")

        def next_command(root: Path) -> None:  # runs after the lock is released, before the trace line is written
            self.ok("pause", "--reason", "a second command")

        with mock.patch.object(progress, "ensure", side_effect=next_command), \
                mock.patch.dict(os.environ, {"SHIPLOOP_PROGRESS": "off"}), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(protocol.main(core, ["complete", "--run-dir", str(self.run), "--action", intake]), 0)
        complete = [row for row in events(self.run) if row.get("verb") == "complete"][-1]
        pause = [row for row in events(self.run) if row.get("verb") == "pause"][-1]
        self.assertEqual((complete["rev"], complete["stage"][1], complete["status"]), ([0, 1], "discovery", "active"))
        self.assertEqual([row["stage"] for row in complete["accepted"]], ["intake"])
        self.assertEqual((pause["rev"], pause["status"]), ([1, 2], "paused"))

    def test_nothing_is_written_into_a_run_that_cannot_be_loaded(self) -> None:
        keepalive_home = self.base / "keepalive"
        with mock.patch.dict(os.environ, {"SHIPLOOP_KEEPALIVE_HOME": str(keepalive_home)}):
            (self.run / "state.md").write_text("not a run any more\n", encoding="utf-8")
            before = (self.run / trace.TRACE_FILE).read_bytes()
            self.assertFalse(trace.record_stop(str(self.run), "claude", None, {"decision": "allow", "why": "x"}))
            self.assertEqual((self.run / trace.TRACE_FILE).read_bytes(), before)
        refused = self.cli("trace", "--run-dir", str(self.run), "--html")
        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn("retired or cannot be loaded", refused.stderr)
        self.assertFalse((self.run / trace.PAGE).exists())

    def test_a_prompt_with_script_markup_cannot_break_the_page(self) -> None:
        run = self.base / "markup-run"
        made = subprocess.run([sys.executable, "-B", str(CLI), "init", "--run-dir", str(run), "--repo", str(self.repo),
                               "--prompt", "Render <!--<script> and </script> as text."],
                              env=ENV, text=True, capture_output=True, timeout=60)
        self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
        page = trace.render_html(run, trace.build(run))
        start = page.index("const TRACE = ") + len("const TRACE = ")
        payload = page[start:page.index(";\n", start)]
        self.assertNotIn("<", payload)                                    # no raw "<" can open or close an element
        self.assertEqual(json.loads(payload)["run"]["prompt"], "Render <!--<script> and </script> as text.")

    def test_steps_from_before_the_trace_stay_in_the_timeline(self) -> None:
        """A run upgraded mid-flight: its first traced command must not hide the steps accepted before it."""
        intake, _ = self.drive()
        # Make the intake acceptance look older than the trace, as if this ShipLoop had been installed afterwards.
        rows = [row for row in events(self.run) if not row.get("accepted")]
        (self.run / trace.TRACE_FILE).write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        model = trace.build(self.run)
        accepted = [row for row in model["events"] if row["kind"] == "accepted"]
        self.assertEqual([(row["action"], row["stage"]) for row in accepted], [(intake, "intake")])
        self.assertEqual(model["run"]["untraced_steps"], 1)
        self.assertIn(f"1 accepted step before it come from state.md", trace.digest(model))


class TraceReaderTests(CliRun):
    def test_actionless_command_keeps_recorded_cursor_context(self) -> None:
        action = self.action()
        trace.record(self.run, "command", verb="status", exit=0, cursor=[action, action])
        model = trace.build(self.run)
        status = [row for row in model["events"] if row.get("verb") == "status"][-1]
        self.assertFalse(status.get("action"))
        self.assertEqual(status["for_action"], action)
        self.assertEqual(status["binding"], "contextual")

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
        self.assertIn("Totals:   1 accepted · 7 commands · 1 refused · 0 checks failed · 5 packets (1 reprint)", text)

    def test_a_failed_check_is_a_check_not_a_refusal(self) -> None:
        intake = self.action()
        (self.run / "inbox" / f"{intake}.md").write_text('```shiploop-state\n{"outcome": "done"}\n```\n', encoding="utf-8")
        self.assertNotEqual(self.cli("check", "--action", intake).returncode, 0)
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
        # The digest prints `nav-7d0f97f9…`; the 2026-10-25 E2E check copied the hex and was refused.
        bare = self.ok("trace", "--run-dir", str(self.run), "--action", intake.split("-", 1)[1][:8]).stdout
        self.assertIn(f"=== ShipLoop trace: action {intake} ===", bare)

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
        self.assertFalse((self.run / trace.CONTENT).exists())             # --html writes the page alone
        page = (self.run / trace.PAGE).read_text(encoding="utf-8")
        self.assertNotIn(trace_page.DATA_MARK, page)
        self.assertNotIn("sk-live-abcdefghijklmnop", page)
        start = page.index("const TRACE = ") + len("const TRACE = ")
        data = json.loads(page[start:page.index(";\n", start)].replace("<\\/", "</"))
        self.assertEqual(data["schema"], trace.SCHEMA)
        self.assertIn("[redacted sensitive value]", data["texts"][sent["file"]])
        sent_files = {row[key] for row in events(self.run) if row["kind"] == "packet" for key in ("file", "head_file")
                      if row.get(key)}
        self.assertEqual(set(data["texts"]), sent_files)

    def test_a_progress_snapshot_also_writes_the_page(self) -> None:
        self.drive()
        self.assertFalse((self.run / trace.PAGE).exists())
        self.ok("view", "--run-dir", str(self.run))
        self.assertIn("const TRACE = {", (self.run / trace.PAGE).read_text(encoding="utf-8"))


class TraceRequestTests(CliRun):
    """The original request beside its expansion by planning (owner, 2026-10-25: "we always want the ability to see
    what the original prompt was and what the expanded prompt was")."""

    def test_intakes_reading_is_split_by_request_sentence(self) -> None:
        readings = trace.sentence_readings("S1 outcome: a CLI flag (fact). S2 boundary: no new dependency. "
                                           "S3 open question: which version source? (asked).")
        self.assertEqual(readings, {1: [{"kind": "outcome", "text": "a CLI flag (fact)."}],
                                    2: [{"kind": "boundary", "text": "no new dependency."}],
                                    3: [{"kind": "open question", "text": "which version source? (asked)."}]})
        self.assertEqual(trace.sentence_readings("No sentence markers here."), {})

    def test_intakes_reading_is_split_however_the_host_words_the_citation(self) -> None:
        # Shapes from real intake summaries (2026-10-24/25 E2E runs on Claude Sonnet, Codex and Grok); before the fix
        # 11 of 27 real intakes that cite every sentence were read as "0 of N sentences".
        readings = trace.sentence_readings(
            'S1: outcome = report.py at the root (fact). S2: Outcome: one JSON object. S3: outcome - rows skipped. '
            'S4: outcome is a header-only file adds nothing. S5 (page shows "shots (and hits)"): boundary = no new '
            'route. S6 (create hello.py): Outcome 1: hello.py prints. Outcome 2: test_hello.py runs it. '
            'S7: Deliver hello.py and its test. S8 maps to the unittest suite. | S9 open question: which port? '
            'Defaults recorded: stdlib only; see AWS S3 for nothing.')
        self.assertEqual({n: [(r["kind"], r["text"]) for r in found] for n, found in readings.items()}, {
            1: [("outcome", "report.py at the root (fact).")], 2: [("outcome", "one JSON object.")],
            3: [("outcome", "rows skipped.")], 4: [("outcome", "a header-only file adds nothing.")],
            5: [("boundary", "no new route.")],
            6: [("outcome", "hello.py prints. Outcome 2: test_hello.py runs it.")],
            7: [("reading", "Deliver hello.py and its test.")], 8: [("reading", "the unittest suite.")],
            9: [("open question", "which port? Defaults recorded: stdlib only; see AWS S3 for nothing.")]})

    def test_an_intake_summary_with_no_cited_sentence_stays_in_the_request_view(self) -> None:
        model = {"request": {"original": {"chars": 5, "file": "request.md", "text": "Hi.",
                                          "sentences": [{"n": 1, "text": "Hi.", "readings": []}]},
                             "expanded": {"through": "intake", "mapped": 0, "requirements": [], "spec_file": "spec.md",
                                          "work_items": [], "assumptions": [], "answers": [], "superseded": 0,
                                          "stages": [{"stage": "intake", "state": "accepted", "headline": "Read",
                                                      "summary": "Greets the owner in one line.", "improve": False}]}}}
        text = trace.request_digest(model)
        self.assertIn("→ no clause of intake's summary cites it", text)
        self.assertIn("Greets the owner in one line.", text)

    def test_the_request_shows_the_original_and_each_planning_result(self) -> None:
        self.drive()
        spec = self.repo / "docs" / "shiploop" / "spec.md"
        spec.parent.mkdir(parents=True)
        spec.write_text("# Living spec\n\n## Requirements\n\n### R-1. Greeting\n\n- Positive: prints Hello.\n\n"
                        "## Non-functional requirements\n\n### R-2. Secrets\n\napi_key=sk-live-abcdefghijklmnop1234567890\n",
                        encoding="utf-8")
        (self.run / "decisions").mkdir(exist_ok=True)
        (self.run / "decisions" / "nav-answer.md").write_text("Use the user's login name.\n", encoding="utf-8")
        request = trace.build(self.run)["request"]
        self.assertEqual(request["original"]["text"], "Add a greeting script.")
        self.assertEqual(request["original"]["sentences"], [
            {"n": 1, "text": "Add a greeting script.",
             "readings": [{"kind": "outcome", "text": "greet.py prints Hello and the name (fact)."}]}])
        expanded = request["expanded"]
        self.assertEqual(expanded["through"], "intake")
        self.assertEqual([(stage["stage"], stage["state"]) for stage in expanded["stages"]][:2],
                         [("intake", "accepted"), ("discovery", "pending")])
        self.assertEqual([(r["id"], r["title"], r["section"]) for r in expanded["requirements"]],
                         [("R-1", "Greeting", "Requirements"), ("R-2", "Secrets", "Non-functional requirements")])
        self.assertEqual(expanded["requirements"][1]["body"], "[redacted sensitive value]")
        self.assertEqual(expanded["answers"], [{"file": "decisions/nav-answer.md", "action": "nav-answer",
                                                "text": "Use the user's login name."}])
        self.assertEqual(expanded["work_items"], [])                 # set by the plan stage
        text = self.ok("trace", "--run-dir", str(self.run), "--request").stdout
        self.assertIn("Original, sentence by sentence (joined, the verbatim RUN/request.md; 22 chars)", text)
        self.assertEqual(text.count("Add a greeting script."), 1)          # the request is printed once
        self.assertIn("  S1   Add a greeting script.\n       → outcome: greet.py prints Hello and the name (fact).", text)
        self.assertNotIn("    " + " " * 14 + " S1 outcome:", text)            # intake's summary is the readings, not repeated
        self.assertIn("  ✓ intake         Scope: one greeting script", text)
        self.assertIn("  · discovery", text)
        self.assertIn("  R-1    Greeting  [Requirements]", text)
        self.assertIn("  set by the plan stage", text)
        self.assertIn("  RUN/decisions/nav-answer.md: Use the user's login name.", text)
        digest = self.ok("trace", "--run-dir", str(self.run)).stdout
        self.assertIn("Request:  original 22 chars, 1 sentence (RUN/request.md): “Add a greeting script.”", digest)
        self.assertIn("Expanded: through intake · intake read 1 of 1 sentence · 2 requirements · 0 work items · "
                      "0 assumptions · 1 owner answer", digest)


class TracePlanTests(unittest.TestCase):
    """The plan of a run past planning, from saved state: work-item rows, the current slot, reruns and Improve."""

    def setUp(self) -> None:
        self.driver = status_display.StatusBlockTests()
        self.driver.setUp()
        self.addCleanup(self.driver.temp.cleanup)
        self.run = Path(self.driver.temp.name) / "run"
        self.run.mkdir()

    def saved(self, state: dict) -> dict:
        (self.run / ".lock").touch(exist_ok=True)  # coherent fixture for the read-only shared-lock reader
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
        self.assertEqual(w1["implement"]["steps"], 1)                  # implement counts its step plan's steps
        self.assertEqual([item["id"] for item in model["request"]["expanded"]["work_items"]], ["W1", "W2"])
        self.assertEqual(model["request"]["expanded"]["work_items"][0]["steps"],
                         [{"id": "S1", "task": "Make the change.", "deps": []}])
        self.assertEqual(model["now"]["item"], "W1")
        text = trace.digest(model)
        self.assertIn("W2 Add --version flag", text)
        self.assertIn("7 stages pending", text)  # the 7-stage inner loop (design T §9.1 2b-4: verify retired)
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


class SafeTraceObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="safe-trace-observation-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        (self.root / ".lock").touch()
        self.state = navigator.new_state(str(self.repo), "Synthetic trace", improve_skill="")
        (self.root / "state.md").write_text(store.dumps(self.state))

    def test_actual_sparse_status_card_archive_keeps_unknown_identities_and_workspace(self):
        status_card_tests = _load("sparse_status_card_fixture", "shiploop-e2e-status-card.test.py")
        fixture = status_card_tests.Builders()
        fixture.base = self.root
        folder = fixture.traced_folder()
        run = folder / ".shiploop-runs/work-1/run"
        cwd = self.root / "unrelated-cwd"
        (cwd / "docs/shiploop").mkdir(parents=True)
        (cwd / "docs/shiploop/spec.md").write_text("### R-99. Unrelated cwd requirement\nUNRELATED_CWD")
        for relative in ("packets/None.md", "results/None.md", "checks/None.md"):
            path = run / relative
            path.parent.mkdir(exist_ok=True)
            path.write_text("UNRELATED_NULL_ARTIFACT")
        original_read = trace.observation_io._read_beneath
        for locked in (False, True):
            with self.subTest(locked=locked):
                if locked:
                    (run / ".lock").touch()
                before = {str(path.relative_to(run)): (path.stat().st_ino, path.stat().st_size,
                          path.stat().st_mtime_ns, path.stat().st_ctime_ns,
                          path.read_bytes() if path.is_file() else None) for path in run.rglob("*")}
                old_cwd = Path.cwd()
                try:
                    os.chdir(cwd)
                    with mock.patch.object(trace.observation_io, "_read_beneath", wraps=original_read) as reads:
                        model = trace.build(run)
                        rendered = trace.render_html(run, model)
                finally:
                    os.chdir(old_cwd)
                after = {str(path.relative_to(run)): (path.stat().st_ino, path.stat().st_size,
                         path.stat().st_mtime_ns, path.stat().st_ctime_ns,
                         path.read_bytes() if path.is_file() else None) for path in run.rglob("*")}
                self.assertEqual(before, after)
                self.assertEqual((run / ".lock").exists(), locked)
                self.assertIsNone(model["now"]["action"])
                expanded = model["request"]["expanded"]
                self.assertEqual(expanded["requirements"], [])
                self.assertIsNone(expanded["spec_file"])
                self.assertIsNone(expanded["architecture_file"])
                accepted = [row for row in model["story"]["events"] if row["kind"] == "accepted"]
                self.assertEqual(len(accepted), 3)
                self.assertEqual(len({row["id"] for row in accepted}), 3)
                self.assertTrue(all(row["action"] is None and row["binding"] == "unbound" for row in accepted))
                visits = model["story"]["visits"]
                self.assertEqual(len(visits), 3)
                self.assertEqual(len({row["id"] for row in visits}), 3)
                self.assertTrue(all(row["action"] is None and len(row["events"]) == 1 and not row["evidence"] for row in visits))
                self.assertTrue(all(row["result"] is None for row in model["steps"]))
                self.assertEqual(len(trace.page_texts(run, model)), 2)
                self.assertNotIn("UNRELATED_", rendered)
                for call in reads.call_args_list:
                    self.assertNotIn("None.md", str(call.args[1]))
                    self.assertNotIn(str(cwd), str(call.args[0]))

    def test_sparse_archive_cannot_bind_producer_observations_without_run_identity(self):
        status_card_tests = _load("sparse_producer_status_card_fixture", "shiploop-e2e-status-card.test.py")
        fixture = status_card_tests.Builders()
        fixture.base = self.root
        run = fixture.traced_folder() / ".shiploop-runs/work-1/run"
        row = {"schema": "shiploop-progress-observation/v1", "id": "sparse-producer",
               "producer": "fixture-harness", "scope": "fixture execution", "kind": "fact",
               "title": "Stopped", "summary": "Typed producer claim", "status": "stopped",
               "observed_at": "2026-01-01T00:00:00Z", "logged_at": "2026-01-01T00:00:00Z",
               "lifecycle": {key: {"status": "claimed"} for key in ("execution", "acceptance", "owner_hold")}}
        # Both missing and explicitly null producer identities used to compare equal
        # to this fixture's missing run identity.
        for candidate in (row, dict(row, id="null-producer", run_id=None)):
            store.append_jsonl(run / "progress-observations.jsonl", candidate)
        story = trace.build(run)["story"]
        self.assertEqual(story["observations"], [])
        for key in ("execution", "acceptance", "owner_hold"):
            self.assertEqual(story["lifecycle"][key]["status"], "unknown")
        source = next(row for row in story["sources"] if row["id"] == "progress-observations.jsonl")
        self.assertEqual(source["status"], "partial")
        self.assertIn("observations ignored", source["message"])
        self.assertEqual(sum("Ignored unbound or invalid producer observation" in warning
                             for warning in story["warnings"]), 2)

    def test_unknown_workspace_never_becomes_cwd_knowledge(self):
        for repo in (None, "", "relative-repo", 42, {}, "bad\x00path"):
            with self.subTest(repo=repo):
                self.state["repo"] = repo
                (self.root / "state.md").write_text(store.dumps(self.state))
                with mock.patch.object(trace, "requirements", side_effect=AssertionError("unknown workspace read")):
                    expanded = trace.build(self.root)["request"]["expanded"]
                self.assertEqual(expanded["requirements"], [])
                self.assertIsNone(expanded["spec_file"])
                self.assertIsNone(expanded["architecture_file"])

    def test_legacy_archive_without_lock_is_nonmutating_and_qualified(self):
        self.state["execution_mode"] = "legacy"
        (self.root / "state.md").write_text(store.dumps(self.state))
        (self.root / ".lock").unlink()
        before = {str(path.relative_to(self.root)): (path.stat(), path.read_bytes() if path.is_file() else None)
                  for path in self.root.rglob("*")}
        model = trace.build(self.root)
        after = {str(path.relative_to(self.root)): (path.stat(), path.read_bytes() if path.is_file() else None)
                 for path in self.root.rglob("*")}
        # Reads may update atime; entries, bytes, identity and modification clocks must not change.
        stable = lambda snapshot: {name: (info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns,
                                         info.st_ctime_ns, raw) for name, (info, raw) in snapshot.items()}
        self.assertEqual(stable(before), stable(after))
        self.assertEqual(model["run"]["id"], self.state["run_id"])
        source = next(row for row in model["story"]["sources"] if row["id"] == "state.md")
        self.assertEqual(source["consistency"], "unlocked-archive")
        self.assertEqual(source["status"], "partial")
        self.assertIn("without a shared lock", source["message"])
        self.assertTrue(any("without a shared lock" in warning for warning in model["story"]["warnings"]))

    def test_explicit_lock_allows_legacy_display_without_resume_validation(self):
        self.state["execution_mode"] = "legacy"
        (self.root / "state.md").write_text(store.dumps(self.state))
        model = trace.build(self.root)
        source = next(row for row in model["story"]["sources"] if row["id"] == "state.md")
        self.assertEqual(model["run"]["id"], self.state["run_id"])
        self.assertEqual(source["consistency"], "shared-lock")
        self.assertEqual(source["status"], "ok")

    def test_pending_transaction_refused_with_or_without_lock(self):
        journal = self.root / store.JOURNAL_NAME
        journal.write_text("retained pending transaction")
        for locked in (True, False):
            with self.subTest(locked=locked):
                if not locked:
                    (self.root / ".lock").unlink()
                with self.assertRaisesRegex(ValueError, "transaction pending"):
                    trace.build(self.root)
                self.assertEqual(journal.read_text(), "retained pending transaction")

    def test_archive_capture_refuses_transaction_or_lock_appearing_during_read(self):
        import shiploop_story as story
        (self.root / ".lock").unlink()
        original = story.capture_core
        for name in (store.JOURNAL_NAME, ".lock"):
            with self.subTest(name=name):
                def capture_then_change(*args, **kwargs):
                    core = original(*args, **kwargs)
                    (self.root / name).write_text("appeared during capture")
                    return core
                with mock.patch.object(story, "capture_core", side_effect=capture_then_change):
                    with self.assertRaisesRegex(ValueError, "during archive capture"):
                        trace.build(self.root)
                (self.root / name).unlink()

    def test_unsafe_and_busy_locks_never_use_archive_fallback(self):
        import fcntl
        lock = self.root / ".lock"
        with lock.open("rb") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, "busy"):
                trace.build(self.root)
        lock.unlink()
        lock.symlink_to(self.root / "absent-lock-target")
        with self.assertRaises(ValueError):
            trace.build(self.root)
        lock.unlink()
        target = self.root / "other-lock"
        target.touch()
        os.link(target, lock)
        with self.assertRaises(ValueError):
            trace.build(self.root)

    def test_malformed_state_remains_refused_in_archive_and_locked_reads(self):
        for raw in ("not a state record", "```shiploop-state\n{broken}\n```",
                    "```shiploop-state\n[]\n```"):
            (self.root / "state.md").write_text(raw)
            for locked in (True, False):
                with self.subTest(raw=raw, locked=locked):
                    lock = self.root / ".lock"
                    if locked:
                        lock.touch()
                    elif lock.exists():
                        lock.unlink()
                    with self.assertRaises((store.StorageError, ValueError)):
                        trace.build(self.root)

    def test_packet_paths_cannot_escape_run_or_follow_parent_links(self):
        (self.repo / "private.md").write_text("must remain private")
        (self.root / "linked").symlink_to(self.repo, target_is_directory=True)
        model = {"events": [{"kind": "packet", "file": "../repo/private.md"},
                             {"kind": "packet", "file": "linked/private.md"},
                             {"kind": "packet", "file": str(self.repo / "private.md")}], "steps": []}
        self.assertEqual(trace.page_texts(self.root, model), {})

    def test_trace_screens_prompt_arguments_paths_and_hidden_fields(self):
        secret = "api_key=abcdefghijk1234567890"
        self.state["prompt"] = secret
        (self.root / "state.md").write_text(store.dumps(self.state))
        store.append_jsonl(self.root / "skill-calls.jsonl", {"skill": secret, "args": [secret]})
        model = trace.build(self.root)
        self.assertNotIn(secret, json.dumps(model))
        self.assertNotIn(secret, trace.render_html(self.root, model))

    def test_surrogate_source_text_remains_readable_and_the_page_encodes(self):
        text = "Undecodable filename " + os.fsdecode(b"caf\xe9.txt")
        store.append_jsonl(self.root / trace.TRACE_FILE, {"kind": "command", "verb": "check", "error": text})
        model = trace.build(self.root)
        self.assertIn(text, [row.get("error") for row in model["events"]])
        trace.render_html(self.root, model).encode("utf-8")

    def test_source_key_covers_timeline_spec_and_packet_content(self):
        spec = self.repo / "docs/shiploop/spec.md"
        spec.parent.mkdir(parents=True)
        spec.write_text("### R-1. First requirement\nRead the first source.")
        packets = self.root / "packets"
        packets.mkdir()
        packet = packets / "sent.md"
        packet.write_text("First prompt")
        store.append_jsonl(self.root / trace.TRACE_FILE, {"kind": "packet", "file": "packets/sent.md", "ts": 1.0})
        first = trace.source_key(self.root)
        spec.write_text("### R-1. Revised requirement\nRead the second source.")
        second = trace.source_key(self.root)
        self.assertNotEqual(first, second)
        packet.write_text("Revised prompt")
        third = trace.source_key(self.root)
        self.assertNotEqual(second, third)
        (self.root / "timeline.json").write_text(json.dumps({"started": "2026-01-01T00:00:00Z", "accepted": {}}))
        self.assertNotEqual(third, trace.source_key(self.root))

    def test_shared_observation_time_is_exposed_without_invalidating_heartbeat_key(self):
        import shiploop_progress as progress
        snapshot = progress.sample(self.root)
        first = trace.build(self.root, core=snapshot.core, captures=snapshot.captures, now=1.0)
        self.assertEqual(first["observed_at"], snapshot.core["observed_at"])
        self.assertEqual(snapshot.core["consistency"], "shared-lock")
        source = next(row for row in first["story"]["sources"] if row["id"] == "state.md")
        self.assertEqual(source["consistency"], "shared-lock")
        self.assertEqual(source["message"], "Shared-lock core generation.")
        self.assertFalse(any("without a shared lock" in warning for warning in first["story"]["warnings"]))
        later_core = dict(snapshot.core, observed_at="2026-01-02T03:04:05Z")
        with mock.patch("shiploop_story.capture_core", side_effect=AssertionError("must reuse supplied core")):
            later = trace.build(self.root, core=later_core, captures=snapshot.captures, now=2.0)
        self.assertEqual(later["observed_at"], later_core["observed_at"])
        self.assertNotEqual(first["observed_at"], later["observed_at"])
        self.assertNotEqual(first["generated"], later["generated"])
        self.assertEqual(trace.source_key(self.root, model=first), trace.source_key(self.root, model=later))

    def test_accepted_anchor_survives_delayed_command_and_optional_damage(self):
        action = navigator.current_action(self.state)["id"]
        self.state = navigator.apply(self.state, action, {"outcome": "done", "summary": "Accepted scope"})
        (self.root / "state.md").write_text(store.dumps(self.state))
        first = trace.build(self.root)
        store.append_jsonl(self.root / trace.TRACE_FILE, {"kind": "command", "action": action,
                            "accepted": [{"action": action}], "ts": "not a timestamp", "ms": 12, "exit": 0})
        second = trace.build(self.root)
        accepted = lambda model: [e["id"] for e in model["story"]["events"] if e["kind"] == "accepted"]
        self.assertEqual(accepted(first), ["accepted:" + action])
        self.assertEqual(accepted(first), accepted(second))

    def test_legacy_accepted_events_only_fill_timestamped_uncovered_history(self):
        actions = []
        for _ in range(3):
            action = navigator.current_action(self.state)["id"]
            actions.append(action)
            self.state = navigator.apply(self.state, action, {"outcome": "done", "summary": "Accepted scope"})
        (self.root / "state.md").write_text(store.dumps(self.state))
        (self.root / "timeline.json").write_text(json.dumps({"accepted": {
            actions[0]: "2026-01-01T00:00:01Z", actions[1]: "2026-01-01T00:00:02Z"}}))
        store.append_jsonl(self.root / trace.TRACE_FILE, {"kind": "command", "verb": "complete",
                          "accepted": [{"action": actions[0]}], "ts": 1767225601, "exit": 0})
        model = trace.build(self.root)
        self.assertEqual([row["action"] for row in model["events"] if row["kind"] == "accepted"], [actions[1]])
        self.assertEqual(model["run"]["untraced_steps"], 1)
        accepted = [row for row in model["story"]["events"] if row["kind"] == "accepted"]
        self.assertEqual({row["id"] for row in accepted}, {"accepted:" + action for action in actions})
        self.assertIsNone(next(row for row in accepted if row["action"] == actions[2])["at"])


class LiveRun(unittest.TestCase):
    """A run folder with a state and no trace: enough for the model, the page and its update file."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="trace-live-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        (self.root / ".lock").touch()
        self.state = navigator.new_state(str(self.repo), "Live trace goal", improve_skill="")
        (self.root / "state.md").write_text(store.dumps(self.state))

    def watched(self, **extra) -> dict:
        """The model as the observer publishes it: a watching observer and the key of its displayed content."""
        model = trace.build(self.root)
        model["observer"] = {"mode": "watch", "final": False, "error": ""}
        model["version"] = "key-one"
        model.update(extra)
        return model


class TraceLiveFilesTests(LiveRun):
    """The observer writes the page and trace-content.js from one payload; the open page loads the latter."""

    CALL = "window.__shiploopTrace&&window.__shiploopTrace("

    @staticmethod
    def inlined(page: str) -> str:
        start = page.index("const TRACE = ") + len("const TRACE = ")
        return page[start:page.index(";\n", start)]

    def test_write_live_writes_the_page_and_its_update_file_from_one_payload(self) -> None:
        model = self.watched()
        order: list[str] = []
        real_write = store.atomic_write_text
        def recording(path, text):
            order.append(Path(path).name)
            return real_write(path, text)
        with mock.patch.object(store, "atomic_write_text", side_effect=recording), \
                mock.patch.object(trace, "page_payload", wraps=trace.page_payload) as payload:
            self.assertIsNone(trace.write_live(self.root, model=model, texts={}))
        self.assertEqual(payload.call_count, 1)                           # one payload feeds both files
        self.assertEqual(order, [trace.CONTENT, trace.PAGE])              # the content is there before the page changes
        content = (self.root / trace.CONTENT).read_text(encoding="utf-8")
        self.assertTrue(content.startswith(self.CALL))
        self.assertTrue(content.endswith(");\n"))
        self.assertEqual(content.count("\n"), 1)                          # one statement on one line
        body = content[len(self.CALL):-len(");\n")]
        inlined = self.inlined((self.root / trace.PAGE).read_text(encoding="utf-8"))
        self.assertEqual(body, inlined)
        self.assertEqual(json.loads(body), json.loads(inlined))
        self.assertEqual(json.loads(body)["version"], "key-one")
        self.assertEqual(json.loads(body)["run"]["goal"], "Live trace goal")
        self.assertNotIn("<", body)                                       # "</script>" in a prompt cannot end the file
        self.assertEqual(trace.CONTENT, "trace-content.js")

    def test_write_live_screens_the_content_file_like_the_page(self) -> None:
        secret = "api_key=abcdefghijk1234567890"
        self.state["prompt"] = secret
        (self.root / "state.md").write_text(store.dumps(self.state))
        trace.write_live(self.root, model=self.watched(), texts={"packets/a.md": "token: " + secret})
        for name in (trace.CONTENT, trace.PAGE):
            self.assertNotIn(secret, (self.root / name).read_text(encoding="utf-8"), name)

    def test_write_html_still_writes_only_the_page(self) -> None:
        trace.write_html(self.root, model=self.watched(), texts={})
        self.assertTrue((self.root / trace.PAGE).is_file())
        self.assertFalse((self.root / trace.CONTENT).exists())
        self.assertEqual(json.loads(self.inlined((self.root / trace.PAGE).read_text(encoding="utf-8")))["version"], "key-one")

    def test_the_source_key_does_not_depend_on_the_version_it_names(self) -> None:
        model = self.watched()
        plain = {key: value for key, value in model.items() if key != "version"}
        self.assertEqual(trace.source_key(self.root, model=model, texts={}), trace.source_key(self.root, model=plain, texts={}))
        self.assertEqual(trace.source_key(self.root, model=model, texts={}),
                         trace.source_key(self.root, model={**model, "version": "key-two"}, texts={}))
        changed = {**model, "run": {**model["run"], "goal": "Another goal"}}
        self.assertNotEqual(trace.source_key(self.root, model=model, texts={}), trace.source_key(self.root, model=changed, texts={}))


def script_of(page: str) -> str:
    start = page.rindex("<script>\n") + len("<script>\n")
    return page[start:page.index("\n</script>", start)]


class TraceLivePageTests(LiveRun):
    """The page checks for new content in the background and re-renders in place; it never reloads."""

    def test_the_page_has_no_reload_and_its_policy_allows_its_own_scripts(self) -> None:
        page = trace_page.PAGE
        self.assertNotIn("location.reload", page)
        self.assertNotIn(".reload(", page)
        self.assertNotIn("location.href", page)
        self.assertNotIn("reload every 10 s", page)
        self.assertIn("live updates (checks every 5 s, no reload)", page)
        policy = re.search(r'http-equiv="Content-Security-Policy" content="([^"]*)"', page).group(1)
        directives = {part.split()[0]: part.split()[1:] for part in policy.split(";") if part.strip()}
        self.assertEqual(directives["script-src"], ["'unsafe-inline'", "'self'"])
        self.assertEqual(directives["connect-src"], ["'none'"])
        self.assertEqual(directives["default-src"], ["'none'"])
        self.assertEqual(directives["img-src"], ["'none'"])
        # One Escape listener for the page's life, registered outside the function that renders a model.
        self.assertEqual(page.count('document.addEventListener("keydown"'), 1)
        self.assertLess(page.index('document.addEventListener("keydown"'), page.index("function bootTrace(TRACE) {"))
        self.assertIn('"observer-read"', page)                             # the clock the version call updates in place

    def test_the_model_marker_and_data_extraction_points_are_unchanged(self) -> None:
        page = trace_page.PAGE
        self.assertEqual(page.count("const TRACE = " + trace_page.DATA_MARK + ";\n"), 1)
        self.assertEqual(page.count(trace_page.DATA_MARK), 1)


@unittest.skipUnless(shutil.which("node"), "Node required for the page-script probes")
class TraceLiveNodeProbeTests(LiveRun):
    """The page script run under node with small stand-ins for the browser."""

    CONTROLLER = r"""
const assert = require('assert');
const timers = [];
const setTimeout = (fn, ms) => { const t = {fn, ms, cancelled: false, fired: false}; timers.push(t); return t; };
const clearTimeout = (t) => { if (t) t.cancelled = true; };
const heads = [];
const viewer = {open: false, classList: {contains: (name) => name === 'open' && viewer.open}};
const observer = {textContent: 'unset'};
const selection = {isCollapsed: true, toString: () => ''};
const window = {scrollY: 0, scrolled: [], scrollTo(x, y) { this.scrolled.push([x, y]); this.scrollY = y; }, getSelection: () => selection};
const document = {
  activeElement: null, listeners: {},
  addEventListener(kind, fn) { (this.listeners[kind] = this.listeners[kind] || []).push(fn); },
  getElementById: (id) => ({viewer, 'observer-read': observer}[id] || null),
  createElement: (tag) => ({tag, src: '', remove() { const i = heads.indexOf(this); if (i >= 0) heads.splice(i, 1); }}),
  head: {appendChild: (node) => heads.push(node)},
};
const booted = [];
// The render itself is not under test here: a stand-in that does what bootTrace ends with.
function bootTrace(model) { booted.push(model); window.scrollY = 0; LIVE.version = model.version; LIVE.on = model.watch !== false; }
const live = () => timers.filter((t) => !t.cancelled && !t.fired);
const fire = () => { const t = live()[0]; assert(t, 'a check is scheduled'); assert.equal(t.ms, 5000); t.fired = true; t.fn(); };
const loads = (name) => heads.filter((s) => s.src.startsWith(name + '?t='));
"""

    def controller(self) -> str:
        page = trace_page.PAGE
        start = page.index("// ---------------------------------------------------------------- live updates")
        return page[start:page.index("function bootTrace(TRACE) {")]

    def node(self, script: str, *, gc: bool = False) -> None:
        path = self.root / "probe.js"
        path.write_text(script, encoding="utf-8")
        result = subprocess.run([shutil.which("node"), *(["--expose-gc"] if gc else []), str(path)],
                                capture_output=True, text=True, timeout=60, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_version_call_with_the_same_key_requests_nothing_and_a_new_key_requests_the_content_once(self) -> None:
        self.node(self.CONTROLLER + self.controller() + r"""
bootTrace({version: 'k1', run: {}}); liveSchedule();
assert.equal(live().length, 1);
fire();                                                    // the background check: one version script
assert.equal(loads('progress-version.js').length, 1);
assert(/^progress-version\.js\?t=\d+$/.test(heads[0].src), heads[0].src);
const first = heads[0].src;
heads[0].onload();                                         // removed once it has run
assert.equal(heads.length, 0);
assert.equal(live().length, 1);                            // and the next check is already waiting
fire(); assert.notEqual(heads[0].src, first); heads[0].onerror();   // a failed load is silent and removed too
assert.equal(heads.length, 0);
assert.equal(live().length, 1);
window.__shiploopVersion({trace: 'k1', observed_at: 'T1', status: 'watching'});
assert.equal(heads.length, 0);                             // the key on show: nothing requested
assert.equal(observer.textContent, 'T1');                  // only the observer clock moved
window.__shiploopVersion({trace: 'k2', observed_at: 'T2'});
assert.equal(loads('trace-content.js').length, 1);
window.__shiploopVersion({trace: 'k2', observed_at: 'T3'});
assert.equal(loads('trace-content.js').length, 1);         // one request at a time
assert.equal(observer.textContent, 'T3');
heads[0].onerror();                                        // a failed request is silent, and asked again
assert.equal(heads.length, 0);
window.__shiploopVersion({trace: 'k2'});
assert.equal(loads('trace-content.js').length, 1);
heads[0].onload();
for (const odd of [{}, {trace: ''}, {trace: 7}, null, 'text']) {   // malformed calls change nothing
  window.__shiploopVersion(odd);
  assert.equal(heads.length, 0);
}
""")

    def test_new_content_re_renders_in_place_where_the_reader_stands_and_the_check_goes_on(self) -> None:
        self.node(self.CONTROLLER + self.controller() + r"""
bootTrace({version: 'k1', run: {}}); liveSchedule();
const before = live()[0];
window.__shiploopVersion({trace: 'k2'});
window.scrollY = 1234;
const second = {version: 'k2', run: {}};
window.__shiploopTrace(second);
assert.deepEqual(booted.map((m) => m.version), ['k1', 'k2']);
assert.equal(booted[1], second);
assert.deepEqual(window.scrolled[window.scrolled.length - 1], [0, 1234]);   // the scroll position is restored
assert(before.cancelled, 'the old timer is stopped');
assert.equal(live().length, 1, 'exactly one timer runs');
heads[0].onload();
window.__shiploopVersion({trace: 'k2'});                   // it is now the key on show
assert.equal(heads.length, 0);
window.__shiploopVersion({trace: 'k3'});                   // and a later key is fetched again
assert.equal(loads('trace-content.js').length, 1);
""")

    def test_a_busy_page_keeps_the_new_content_pending_until_it_is_not_busy(self) -> None:
        self.node(self.CONTROLLER + self.controller() + r"""
bootTrace({version: 'k1', run: {}}); liveSchedule();
const third = {version: 'k3', run: {}};
window.__shiploopVersion({trace: 'k3'}); heads[0].onload();
viewer.open = true;                                        // the packet viewer is open
window.__shiploopTrace(third);
assert.equal(booted.length, 1);                            // deferred
assert.equal(LIVE.pending, third);
fire();                                                    // the next tick: still busy, so only the check goes on
assert.equal(booted.length, 1);
assert.equal(loads('progress-version.js').length, 1);
heads[0].onload();
window.__shiploopVersion({trace: 'k3'});                   // the pending content is already in hand
assert.equal(heads.length, 0);
viewer.open = false;
fire();                                                    // not busy: applied at this tick
assert.equal(booted.length, 2);
assert.equal(booted[1], third);
assert.equal(LIVE.pending, null);
assert.equal(live().length, 1);
const wait = (value) => { window.__shiploopTrace({version: value, run: {}}); const n = booted.length; fire(); heads.splice(0); return n; };
document.activeElement = {type: 'search', tagName: 'INPUT'};              // typing in the search box
let n = wait('k4'); assert.equal(booted.length, n); assert.equal(LIVE.pending.version, 'k4');
document.activeElement = {type: 'text', tagName: 'TEXTAREA'};             // or in the note box
fire(); heads.splice(0); assert.equal(booted.length, n);
document.activeElement = null; selection.isCollapsed = false; selection.toString = () => 'abc';   // or selecting text
fire(); heads.splice(0); assert.equal(booted.length, n);
selection.isCollapsed = true; selection.toString = () => '';
fire(); assert.equal(booted.length, n + 1); assert.equal(booted[n].version, 'k4');
""")

    def test_a_page_whose_model_has_no_version_fetches_each_new_key_once(self) -> None:
        self.node(self.CONTROLLER + self.controller() + r"""
bootTrace({run: {}}); liveSchedule();                      // written by `shiploop trace --html`, outside the observer
window.__shiploopVersion({trace: 'x1'});
assert.equal(loads('trace-content.js').length, 1);        // the first key the page is told of is new
heads[0].onload();
window.__shiploopTrace({run: {}});                         // the content arrives without a version of its own
assert.equal(booted.length, 2);
window.__shiploopVersion({trace: 'x1'});                   // the same key again is not fetched again
assert.equal(heads.length, 0);
window.__shiploopVersion({trace: 'x2'});
assert.equal(loads('trace-content.js').length, 1);
""")

    def test_a_page_that_is_not_watchable_never_schedules_a_check(self) -> None:
        self.node(self.CONTROLLER + self.controller() + r"""
bootTrace({version: 'final', run: {}, watch: false}); liveSchedule();   // done, halted, a snapshot, or checks switched off
assert.equal(timers.length, 0);
window.__shiploopVersion({trace: 'other', observed_at: 'T1'});
assert.equal(heads.length, 0);                             // no request either
assert.equal(timers.length, 0);
// An update in flight when checks are switched off waits; it is not applied behind the reader's back.
bootTrace({version: 'k1', run: {}}); liveSchedule(); assert.equal(live().length, 1);
LIVE.on = false; liveSchedule(); assert.equal(live().length, 0);
window.__shiploopTrace({version: 'k2', run: {}});
assert.equal(booted.length, 2); assert.equal(LIVE.pending.version, 'k2');
LIVE.on = true; liveSchedule(); fire();
assert.equal(booted.length, 3); assert.equal(booted[2].version, 'k2');
""")

    FAKE_DOM = r"""
const assert = require('assert');
const registry = {};
const timers = [];
const setTimeout = (fn, ms) => { const t = {fn, ms, cancelled: false, fired: false}; timers.push(t); return t; };
const clearTimeout = (t) => { if (t) t.cancelled = true; };
class Node {}
class Text extends Node {
  constructor(data) { super(); this.data = String(data); }
  get textContent() { return this.data; }
}
class Element extends Node {
  constructor(tag) {
    super(); this.tag = tag; this.children = []; this.attrs = {}; this.listeners = {}; this.className = ''; this._text = null;
    const names = new Set();
    this.classList = {add: (n) => names.add(n), remove: (n) => names.delete(n), contains: (n) => names.has(n),
                      toggle: (n, on) => (on ? names.add(n) : names.delete(n))};
  }
  setAttribute(name, value) { this.attrs[name] = value; if (name === 'id') registry[value] = this; }
  append(...kids) { this.children.push(...kids); }
  appendChild(kid) { this.children.push(kid); }
  replaceChildren(...kids) { this.children = kids; }
  addEventListener(kind, fn) { (this.listeners[kind] = this.listeners[kind] || []).push(fn); }
  remove() {}
  querySelectorAll() { return []; }
  querySelector() { return null; }
  get textContent() { return this._text !== null ? this._text : this.children.map((c) => c.textContent).join(''); }
  set textContent(value) { this._text = String(value); this.children = []; }
}
for (const id of ['app', 'viewer', 'viewer-title', 'viewer-meta', 'viewer-text', 'viewer-close', 'viewer-copy']) {
  registry[id] = new Element(id); registry[id].setAttribute('id', id);
}
const document = {
  activeElement: null, listeners: {}, head: new Element('head'),
  addEventListener(kind, fn) { (this.listeners[kind] = this.listeners[kind] || []).push(fn); },
  getElementById: (id) => registry[id] || null,
  createElement: (tag) => new Element(tag),
  createTextNode: (text) => new Text(text),
};
const window = {scrollY: 0, scrolled: [], scrollTo(x, y) { this.scrolled.push([x, y]); }, getSelection: () => ({isCollapsed: true})};
// No `location`, `fetch` or `navigator` here: reaching for one fails the probe.
const memory = new Map();
const sessionStorage = {getItem: (key) => (memory.has(key) ? memory.get(key) : null), setItem: (key, value) => memory.set(key, String(value))};
const walk = (node, found = []) => { found.push(node); for (const child of node.children || []) walk(child, found); return found; };
const h1 = () => walk(registry.app).find((n) => n.tag === 'h1').textContent;
const active = () => timers.filter((t) => !t.cancelled && !t.fired);
"""

    def test_only_a_watched_page_offers_the_switch_and_checks_for_content(self) -> None:
        trace.write_live(self.root, model=self.watched(), texts={})
        script = script_of((self.root / trace.PAGE).read_text(encoding="utf-8"))
        self.node(self.FAKE_DOM + script + r"""
const clone = (model, edits) => Object.assign(JSON.parse(JSON.stringify(model)), edits);
// [status, observer.mode, observer.final, the reader's switch, a watched page]
const cases = [
  ['blocked', 'watch', false, true, true], ['active', 'watch', false, true, true], ['done', 'watch', false, true, true],
  ['halted', 'watch', false, true, true], ['done', 'watch', true, true, false], ['halted', 'watch', true, true, false],
  ['done', 'snapshot', false, true, false], ['halted', 'stopped', false, true, false], ['blocked', 'stopped', false, true, false],
  ['active', undefined, undefined, true, true], ['done', undefined, undefined, true, false], ['halted', undefined, undefined, true, false],
  ['paused', undefined, undefined, true, false], ['blocked', 'snapshot', false, true, false], ['blocked', 'watch', true, true, false],
  ['blocked', 'watch', false, false, true]];
for (const [status, mode, final, live, watched] of cases) {
  memory.clear();
  const model = clone(TRACE, {version: 'v-' + status});
  model.run.status = status;
  model.observer = {};
  if (mode !== undefined) model.observer.mode = mode;
  if (final !== undefined) model.observer.final = final;
  if (!live) memory.set('trace:' + (model.run.id || '') + ':ui', JSON.stringify({live: false}));
  liveApply(model);
  const where = JSON.stringify({status, mode, final, live});
  const label = walk(registry.app).find((n) => n.tag === 'label' && n.textContent.includes('live updates'));
  assert.equal(!!label, watched, where);                                   // the switch is offered to a watched page only
  if (label) assert.equal(label.children[0].attrs.checked !== undefined, live, where);
  assert.equal(LIVE.on, watched && live, where);
  assert.equal(active().length, watched && live ? 1 : 0, where);           // and only then is a check waiting
}
""")

    def test_the_whole_page_renders_a_new_model_in_place_without_accumulating_anything(self) -> None:
        trace.write_live(self.root, model=self.watched(), texts={})
        script = script_of((self.root / trace.PAGE).read_text(encoding="utf-8"))
        self.node(self.FAKE_DOM + script + r"""
const clone = (model, edits) => Object.assign(JSON.parse(JSON.stringify(model)), edits);
assert.equal(h1(), 'Live trace goal');
assert.equal(active().length, 1); assert.equal(active()[0].ms, 5000);   // watched: one check is waiting
assert.equal(document.listeners.keydown.length, 1);
const box = walk(registry.app).find((n) => n.tag === 'label' && n.textContent.includes('live updates'));
assert(box, 'the checkbox label'); assert(box.textContent.includes('no reload'));

// The observer's clock moves without a re-render.
const header = registry.app.children[0];
window.__shiploopVersion({trace: 'key-one', observed_at: 'OBSERVED-A'});   // the key on show: nothing to fetch
assert.equal(document.head.children.length, 0);
assert.equal(registry['observer-read'].textContent, 'OBSERVED-A');
assert.strictEqual(registry.app.children[0], header);

// New content: asked for once, then rendered in place.
window.__shiploopVersion({trace: 'key-two', observed_at: 'OBSERVED-B'});
assert.equal(document.head.children.length, 1);
assert(document.head.children[0].src.startsWith('trace-content.js?t='));
window.scrollY = 321;
let second = clone(TRACE, {version: 'key-two'}); second.run.goal = 'SECOND GOAL';
window.__shiploopTrace(second);
assert.equal(h1(), 'SECOND GOAL');
assert.notStrictEqual(registry.app.children[0], header);
assert.deepEqual(window.scrolled[window.scrolled.length - 1], [0, 321]);
assert.equal(registry['observer-read'].textContent, 'OBSERVED-B');         // the newest read stays on show
assert.equal(document.listeners.keydown.length, 1);                        // nothing accumulated
assert.equal(active().length, 1);

// The checkbox stops and resumes the checks.
const toggle = walk(registry.app).find((n) => n.tag === 'label' && n.textContent.includes('live updates')).children[0];
toggle.listeners.change[0]({target: {checked: false}});
assert.equal(active().length, 0);
toggle.listeners.change[0]({target: {checked: true}});
assert.equal(active().length, 1);

// A model that ends the run is shown and the checks stop.
const weak = new WeakRef(second);
second = null;
let third = clone(TRACE, {version: 'key-three'}); third.run.goal = 'THIRD GOAL';
window.__shiploopTrace(third);
assert.equal(h1(), 'THIRD GOAL');
let last = clone(TRACE, {version: 'key-four', observer: {mode: 'watch', final: true, error: ''}});
last.run.goal = 'LAST GOAL'; last.run.status = 'done';
window.__shiploopTrace(last);
assert.equal(h1(), 'LAST GOAL');
assert.equal(active().length, 0); assert.equal(LIVE.on, false);
third = null; last = null;
// The first model stays in the page's own constant; a model it replaced must not be held by a timer, a listener or a closure.
setImmediate(() => { gc(); assert.equal(weak.deref(), undefined, 'the replaced model is still referenced'); });
""", gc=True)


class StageLifecycleAndUsageTelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()

    def test_stage_entry_pause_active_duration_and_no_packet_stage_attribution(self) -> None:
        import shiploop_navigator as nav
        import shiploop_story as story_mod
        from unittest import mock

        repo = self.base / "repo"
        repo.mkdir()
        run_dir = self.base / "run"
        run_dir.mkdir()
        state = nav.new_state(str(repo), "Stage timing fixture.", improve_skill="")
        first = nav.current_action(state)["id"]
        with mock.patch.object(nav, "_utc_now", return_value="2026-01-01T10:00:00Z"):
            nav.save(run_dir, state)
        paused = nav.control(state, "pause", "Owner pause")
        with mock.patch.object(nav, "_utc_now", return_value="2026-01-01T10:01:00Z"):
            nav.save(run_dir, paused)
        resumed = nav.control(paused, "resume", "")
        with mock.patch.object(nav, "_utc_now", return_value="2026-01-01T10:03:00Z"):
            nav.save(run_dir, resumed)
        # Advance without writing any packet event (models validate-existing no-packet transition).
        accepted = nav.apply(resumed, first, {"outcome": "done", "summary": "Completed without packet"})
        second = nav.current_action(accepted)["id"]
        with mock.patch.object(nav, "_utc_now", return_value="2026-01-01T10:05:00Z"):
            nav.save(run_dir, accepted)

        tl = nav.load_timeline(run_dir)
        self.assertEqual(tl["entered"][first], "2026-01-01T10:00:00Z")
        self.assertEqual(tl["entered"][second], "2026-01-01T10:05:00Z")
        self.assertAlmostEqual(tl["paused_seconds"][first], 120.0)
        self.assertNotIn("paused_since", tl)

        trace.record(str(run_dir), "hook", hook="model", host="codex", session="s1",
                     model="gpt-5.4", effort="high", stage="intake", action=first)
        trace.record_usage(str(run_dir), "codex", "s1",
                           usage={"input": 5000, "cached_input": 4000, "output": 1000, "total": 6000, "context_tokens": 3000},
                           action=first, stage="intake", model="gpt-5.4", effort="high")
        # Next snapshot in same session increases totals cleanly via monotonic delta.
        trace.record_usage(str(run_dir), "codex", "s1",
                           usage={"input": 8000, "cached_input": 6000, "output": 1500, "total": 9500, "context_tokens": 4100},
                           action=second, stage="discovery", model="gpt-5.4", effort="high")

        model = trace.build(run_dir, now=1767262200.0)
        step = model["steps"][0]
        self.assertEqual(step["duration_basis"], "recorded_entry")
        self.assertEqual(step["wall_seconds"], 300.0)
        self.assertEqual(step["paused_seconds"], 120.0)
        self.assertEqual(step["active_seconds"], 180.0)
        self.assertEqual(step["seconds"], 180)
        self.assertEqual(step["tokens"]["total"], 6000)
        self.assertEqual(step["model"], "gpt-5.4")
        self.assertEqual(step["effort"], "high")
        self.assertEqual(model["now"]["tokens"]["total"], 3500)
        self.assertEqual(model["run"]["tokens"]["total"], 9500)
        self.assertEqual(model["run"]["tokens"]["peak_context"], 4100)
        self.assertEqual(model["counts"]["continuations"], 0)
        self.assertEqual(step["hooks"], 0)

        story, _ = story_mod.build(run_dir, accepted, tl, observed_at="2026-01-01T10:06:00Z")
        v0 = story["visits"][0]
        self.assertEqual(v0["duration_basis"], "recorded entry to accept")
        self.assertEqual(v0["paused_seconds"], 120.0)
        self.assertEqual(v0["active_seconds"], 180.0)
        self.assertEqual(v0["tokens"]["total"], 6000)

        text_digest = trace.digest(model, now=1767262200.0)
        self.assertIn("Tokens:   total 9,500", text_digest)
        self.assertIn("6,000 tok", text_digest)
        html_path = trace.write_html(run_dir, now=1767262200.0)
        html_text = html_path.read_text(encoding="utf-8")
        self.assertIn("9500", html_text)
        self.assertIn("recorded_entry", html_text)

    def test_legacy_two_key_timeline_still_builds_without_usage_or_entered(self) -> None:
        import shiploop_navigator as nav

        repo = self.base / "legacy-repo"
        repo.mkdir()
        run_dir = self.base / "legacy-run"
        run_dir.mkdir()
        state = nav.new_state(str(repo), "Legacy timeline fixture.", improve_skill="")
        first = nav.current_action(state)["id"]
        accepted = nav.apply(state, first, {"outcome": "done", "summary": "Legacy accepted"})
        (run_dir / "state.md").write_text(
            nav.store.dumps(accepted, "ShipLoop navigator state"),
            encoding="utf-8",
        )
        (run_dir / "timeline.json").write_text(json.dumps({
            "started": "2026-01-01T10:00:00Z",
            "accepted": {first: "2026-01-01T10:02:00Z"},
        }), encoding="utf-8")

        model = trace.build(run_dir, now=1767261780.0)
        self.assertEqual(model["steps"][0]["seconds"], 120)
        self.assertEqual(model["steps"][0]["duration_basis"], "accept_delta")
        self.assertIsNone(model["steps"][0]["tokens"])
        self.assertIsNone(model["run"]["tokens"])


if __name__ == "__main__":
    unittest.main()
