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
