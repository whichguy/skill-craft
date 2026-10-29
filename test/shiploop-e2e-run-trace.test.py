#!/usr/bin/env python3
"""The E2E harness reads ShipLoop's run trace (RUN/trace.jsonl, shiploop 1.12.0 and later) where the host stream only hints.

The fixture is a real ShipLoop run driven through the checkout's CLI in a temporary E2E output folder, with a Claude stream
written around the calls it made (the CLI's own output as each tool result, stamped on the same clock as the trace):
init; a `next` that reprints the intake packet; a failed `shiploop check` the stream shows (exit 2); three failures the
harness reads from the stream on every release: a `workspace plan-return --workspace-root` refusal and a `complete` with no
`--action` (a usage error), neither of which loads the run, and a `lint` that could not run (a routed verb: shiploop 1.12.0
traced it without text, 1.13.1 not at all); a refused `complete` the model piped through `| tail -1`, so the stream shows
neither the exit nor the refusal line; a keepalive stop decision that continued the turn; the accepted intake and a reprint
of the discovery packet. The stream alone counts four failures and misses the refusal; the trace counts the refusal and the
check, two reprints and one continuation; the harness's list holds all five, in order.

The same folder with its trace removed is a run before 1.12.0 and must read exactly as before; a trace that began after a
step the model ran does not cover the run, so the counts stay the stream's, and say why. No host CLI or model is started.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / "test" / "shiploop_e2e"
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
sys.path.insert(0, str(E2E))
sys.path.insert(0, str(SCRIPTS))
import arms  # noqa: E402
import fidelity  # noqa: E402
import flow  # noqa: E402
import metrics  # noqa: E402
import owner_note  # noqa: E402
import owner_page  # noqa: E402
import packets  # noqa: E402
import run_trace  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_trace  # noqa: E402

ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "SHIPLOOP_PROGRESS": "off"}
RUN = ".shiploop-runs/work-trace/run"
INTAKE = '```shiploop-state\n{"outcome": "done", "summary": "S1 outcome: greet.py prints Hello and the name (fact).", ' \
         '"headline": "Scope: one greeting script", "evidence_refs": []}\n```\n'
CONTINUED = "ShipLoop run is active: continue with the packet's next step; do not end the turn."
# Hook rows as the reader gives them, for the session_end check: a session end that freed the run, and the next session's
# stop decision 30 s later that continued its turn.
RELEASED_END = {"i": 40, "ts": 5000.0, "hook": "session-end", "decision": "release", "host": "claude",
                "session": "old000000000", "reason": "other", "released": True}
NEXT_CLAIM = {"i": 41, "ts": 5030.0, "hook": "stop", "decision": "continue", "host": "claude", "session": "new000000000",
              "text": CONTINUED}


def traced_output(base: Path) -> Path:
    """An E2E output folder: a real run under .shiploop-runs/, a Claude stream of the calls that drove it, and its timeline."""
    out, repo = base / "out", base / "repo"
    run = out / RUN
    repo.mkdir(parents=True)
    run.parent.mkdir(parents=True)
    stream: list[dict] = []
    stamps: list[float] = []
    cli = f"python3 {CLI}"

    def shell(command: str, argv: list[str], shown=None) -> subprocess.CompletedProcess:
        """One Bash call: the command as the model wrote it, the CLI run, and the tool result as Claude records it."""
        call_id = f"toolu_{len(stream):03d}"
        stream.append({"type": "assistant", "message": {"id": f"msg_{len(stream):03d}", "content": [
            {"type": "tool_use", "id": call_id, "name": "Bash", "input": {"command": command}}]}})
        stamps.append(time.time())
        done = subprocess.run([sys.executable, "-B", str(CLI), *argv], env=ENV, text=True, capture_output=True, timeout=60)
        text = shown(done) if shown else (f"Exit code {done.returncode}\n" if done.returncode else "") + done.stdout + done.stderr
        stream.append({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": call_id, "content": text}]}})
        stamps.append(time.time())
        return done

    def ok(command: str, argv: list[str]) -> subprocess.CompletedProcess:
        done = shell(command, argv)
        assert done.returncode == 0, done.stdout + done.stderr
        return done

    ok(f"{cli} init --run-dir {run} --repo {repo} --prompt 'Add a greeting script.'",
       ["init", "--run-dir", str(run), "--repo", str(repo), "--prompt", "Add a greeting script."])
    intake = navigator.current_action(store.read_record(run / "state.md"))["id"]
    ok(f"{cli} next --run-dir {run}", ["next", "--run-dir", str(run)])
    (run / "inbox" / f"{intake}.md").write_text("no record here\n", encoding="utf-8")
    check = shell(f"{cli} check --run-dir {run} --action={intake}",
                  ["check", "--run-dir", str(run), f"--action={intake}"])
    assert check.returncode != 0, check.stdout + check.stderr
    # Two failures no trace can hold: a workspace verb that names no run, and a command line that does not parse.
    missing = base / "missing-workspace"
    blocked = shell(f"{cli} workspace plan-return --workspace-root {missing}", ["workspace", "plan-return", "--workspace-root", str(missing)])
    assert blocked.returncode != 0 and "ShipLoop workspace blocked" in blocked.stderr, blocked.stdout + blocked.stderr
    usage = shell(f"{cli} complete --run-dir {run}", ["complete", "--run-dir", str(run)])
    assert usage.returncode == 2 and "error:" in usage.stderr, usage.stdout + usage.stderr
    lint = shell(f"{cli} lint --run-dir {run} --action={intake}", ["lint", "--run-dir", str(run), f"--action={intake}"])
    assert lint.returncode == 3 and "could not run" in lint.stdout + lint.stderr, lint.stdout + lint.stderr
    # The model piped the callback: the host saw the pipe's exit (0) and the last line only.
    hidden = shell(f"{cli} complete --run-dir {run} --action={intake} 2>&1 | tail -1",
                   ["complete", "--run-dir", str(run), f"--action={intake}"],
                   shown=lambda done: (done.stdout + done.stderr).strip().splitlines()[-1])
    assert hidden.returncode == 2, hidden.stdout + hidden.stderr
    # The keepalive's stop hook, as it records a decision that put text into the turn. It fires after that result arrives; the
    # trace stamps to the millisecond, so a hook recorded within 0.5 ms of the result would round below it and sort first.
    while round(time.time(), 3) <= stamps[-1]:
        time.sleep(0.001)
    assert shiploop_trace.record_stop(str(run), "claude", "session-1",
                                      {"decision": "continue", "why": "the run is active", "reason": CONTINUED})
    (run / "inbox" / f"{intake}.md").write_text(INTAKE, encoding="utf-8")
    ok(f"{cli} complete --run-dir {run} --action={intake}", ["complete", "--run-dir", str(run), f"--action={intake}"])
    ok(f"{cli} next --run-dir {run}", ["next", "--run-dir", str(run)])
    (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in stream))
    (out / "timeline.jsonl").write_text("".join(json.dumps({"line": n, "t": t}) + "\n" for n, t in enumerate(stamps)))
    (out / "invocation.json").write_text(json.dumps({"kind": "run", "case": "trace-fixture", "host": "claude"}))
    return out


def without_trace(out: Path, into: Path) -> Path:
    """The same output folder as a run before shiploop 1.12.0: no trace.jsonl and no packets/sent/."""
    copy = into / "untraced"
    shutil.copytree(out, copy)
    (copy / RUN / run_trace.FILE).unlink()
    shutil.rmtree(copy / RUN / shiploop_trace.SENT_DIR)
    return copy


class TracedRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="shiploop-e2e-run-trace-")
        base = Path(cls.temp.name).resolve()
        cls.out = traced_output(base)
        cls.run_dir = cls.out / RUN
        cls.state = store.read_record(cls.run_dir / "state.md")
        cls.intake = cls.state["history"][0]["action"]
        cls.discovery = navigator.current_action(cls.state)["id"]
        cls.untraced = without_trace(cls.out, base)
        cls.metrics = metrics.collect(cls.out, cls.run_dir)
        cls.flow = flow.build(cls.out)
        cls.first = flow.read_first(cls.out, repo=ROOT)
        # metrics.json, as slice.py writes it beside each run (arms.summarise reads it).
        for out in (cls.out, cls.untraced):
            (out / "metrics.json").write_text(json.dumps(metrics.collect(out, out / RUN)))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    # --- the reader ---------------------------------------------------------------------------------------------------

    def test_the_reader_holds_every_failure_print_and_hook_with_its_text(self):
        traced = run_trace.read(self.run_dir)
        self.assertTrue(run_trace.covers(traced))
        self.assertEqual([(f["verb"], f["exit"], f["check_only"], f["stage"], f["action"]) for f in traced["failures"]],
                         [("check", 2, True, "intake", self.intake), ("complete", 2, False, "intake", self.intake)])
        self.assertIn("exactly one shiploop-state fence", traced["failures"][1]["text"])
        self.assertEqual([(s["stage"], s["repeat"]) for s in traced["packets"][self.intake]], [("intake", False), ("intake", True)])
        self.assertEqual([s["repeat"] for s in traced["packets"][self.discovery]], [False, True])
        self.assertEqual([(h["decision"], h["text"], h["action"]) for h in traced["hooks"]],
                         [("continue", CONTINUED, self.intake)])
        self.assertIsNone(run_trace.read(self.untraced / RUN))
        self.assertIsNone(run_trace.read(None))

    def test_which_stream_failures_the_trace_cannot_hold(self):
        cli, run = "python3 /x/skills/shiploop/scripts/shiploop", "/e2e/.shiploop-runs/w/run"
        refusal = "ShipLoop navigator: record must contain exactly one shiploop-state fence"
        self.assertFalse(metrics.outside_trace(f"{cli} complete --run-dir {run} --action=nav-1 2>&1 | tail -1", refusal))
        self.assertFalse(metrics.outside_trace(f"RUN={run}; {cli} next --run-dir \"$RUN\"", refusal))
        self.assertTrue(metrics.outside_trace(f"{cli} workspace plan-return --workspace-root /e2e/.shiploop-runs/w", refusal))
        self.assertTrue(metrics.outside_trace(f"{cli} lint --run-dir {run} --action=nav-1", "ShipLoop lint could not run: x"))
        self.assertTrue(metrics.outside_trace(f"{cli} red-check --run-dir {run} --action=nav-1", "x"))
        self.assertTrue(metrics.outside_trace(f"{cli} complete --run-dir {run}",
                                              "shiploop complete: error: the following arguments are required: --action"))
        # A line that also runs a traced verb on the run is the trace's, whichever of its verbs failed.
        self.assertFalse(metrics.outside_trace(f"{cli} lint --run-dir {run} --action=nav-1 && {cli} complete --run-dir {run} "
                                               "--action=nav-1", refusal))
        self.assertEqual(run_trace.ROUTED_VERBS, {"chain", "lint", "red-check", "backchain-check"})
        self.assertNotIn("lint", {f["verb"] for f in run_trace.read(self.run_dir)["failures"]})

    def test_an_unreadable_trace_is_an_error_record_never_an_exception(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "run"
            run.mkdir()
            (run / "state.md").write_text("not a record\n")
            (run / run_trace.FILE).write_text("{}\n")
            traced = run_trace.read(run)
        self.assertIn("error", traced)
        self.assertFalse(run_trace.covers(traced))
        self.assertIn("could not be read", run_trace.why_not(traced))

    # --- metrics.json: the list the Run Review exporter and the reports read ------------------------------------------

    def test_metrics_failures_come_from_the_trace_and_name_it(self):
        m = self.metrics
        self.assertEqual([(f["verb"], f["exit"], f.get("check_only", False), f.get("source", "trace")) for f in m["shiploop_failures"]],
                         [("check", 2, True, "trace"), ("workspace", 2, False, "events.jsonl"),
                          ("complete", 2, False, "events.jsonl"), ("lint", 3, False, "events.jsonl"),
                          ("complete", 2, False, "trace")])
        self.assertIn("exactly one shiploop-state fence", m["shiploop_failures"][4]["line"])
        self.assertIn("ShipLoop workspace blocked", m["shiploop_failures"][1]["line"])
        # The routed verb's refusal keeps its own line (until 2026-10-28 it was recorded as "").
        self.assertIn("ShipLoop lint could not run: ", m["shiploop_failures"][3]["line"])
        self.assertEqual(m["failures_source"], {"file": "<run>/trace.jsonl", "why": None})
        # The stream saw the check and the three it is the source of: the piped refusal hid both its exit and its refusal line.
        self.assertEqual(m["run_trace"]["stream_failures"], 4)
        self.assertEqual({k: m["run_trace"][k] for k in ("refusals", "checks_failed", "packets", "reprints", "continuations")},
                         {"refusals": 1, "checks_failed": 1, "packets": 4, "reprints": 2, "continuations": 1})
        self.assertEqual(sum(row["fired"] for row in m["gate_counts"].values()), len(m["shiploop_failures"]))

    def test_fidelity_refusals_are_the_same_list_with_the_stage_the_run_was_in(self):
        block = fidelity.refusals(_log(self.out), self.out, self.run_dir, self.state)  # the log metrics.collect filled
        self.assertEqual(block["count"], len(self.metrics["shiploop_failures"]))
        self.assertEqual(block["source"], "<run>/trace.jsonl")
        self.assertEqual([(i["source"], i.get("check_only", False)) for i in block["items"]],
                         [("trace", True), ("events.jsonl", False), ("events.jsonl", False), ("events.jsonl", False),
                          ("trace", False)])
        traced = [i for i in block["items"] if i["source"] == "trace"]
        self.assertEqual([(i["stage"], i["event"]) for i in traced], [("intake", None), ("intake", None)])
        self.assertTrue(all(isinstance(i["trace_line"], int) for i in traced))
        self.assertTrue(all(isinstance(i["event"], int) and i["trace_line"] is None
                            for i in block["items"] if i["source"] == "events.jsonl"))

    # --- the live checks: what a live run must show that the fixtures prove -------------------------------------------

    def test_the_checks_pass_the_keepalive_text_and_reprints_and_say_no_note_was_written(self):
        found = self.metrics["run_trace"]["checks"]
        self.assertEqual({name: row["verdict"] for name, row in found.items()},
                         {"keepalive_text": "pass", "packet_copies": "pass", "owner_note": "not exercised",
                          "session_end": "not exercised"})
        self.assertIn(CONTINUED[:60], found["keepalive_text"]["evidence"])
        prints = sum(len(sends) for sends in run_trace.read(self.run_dir)["packets"].values())
        self.assertGreater(prints, 2)  # every print is checked, not only the two reprints
        self.assertEqual(found["packet_copies"]["evidence"], f"{prints} prints (2 reprints), each with its kept copy")
        self.assertEqual(self.metrics["run_trace"]["notes"], {"written": 0, "held": 0, "delivered": 0, "cited": 0})
        line = run_trace.checks_line(found)
        self.assertTrue(line.startswith("keepalive text pass ("), line)
        self.assertTrue(line.endswith("owner note not exercised; session end not exercised"), line)
        self.assertEqual(found["session_end"]["evidence"], "no session end reached the run's trace")

    # --- the session_end check: the host's session-end hook freed the run, and the next session took it ----------------

    def session_end_check(self, *rows: dict) -> dict:
        """The check over ``rows`` as the run's hooks (hook rows as the reader gives them: i, ts, session, ...), the rest of
        this fixture's trace as it is."""
        traced = run_trace.read(self.run_dir)
        traced["hooks"] = [dict(row) for row in rows]
        return run_trace.checks(traced)["session_end"]

    def test_a_release_followed_by_the_next_sessions_claim_passes(self):
        found = self.session_end_check(RELEASED_END, NEXT_CLAIM)
        self.assertEqual(found["verdict"], "pass", found)
        self.assertEqual(found["lines"], [40, 41])
        self.assertEqual(found["evidence"], "freed the run at line 40 (claude, other); the next session continued it 30 s later")

    def test_a_release_the_next_session_never_claimed_is_a_failure_or_not_exercised(self):
        refused = {**NEXT_CLAIM, "decision": "allow", "why": "another session owns this run"}
        found = self.session_end_check(RELEASED_END, refused)
        self.assertEqual(found["verdict"], "fail", found)
        self.assertIn("was allow: another session owns this run", found["evidence"])
        late = {**NEXT_CLAIM, "ts": RELEASED_END["ts"] + run_trace.CLAIM_WITHIN_SECONDS + 1}
        self.assertEqual(self.session_end_check(RELEASED_END, late)["verdict"], "fail")      # past the stale-claim path's margin
        edge = {**NEXT_CLAIM, "ts": RELEASED_END["ts"] + run_trace.CLAIM_WITHIN_SECONDS}
        self.assertEqual(self.session_end_check(RELEASED_END, edge)["verdict"], "pass")
        # No other session decided after the release (the run ended, or the harness did): not a pass.
        found = self.session_end_check(RELEASED_END)
        self.assertEqual((found["verdict"], found["lines"]), ("not exercised", [40]), found)
        same = {**NEXT_CLAIM, "session": RELEASED_END["session"]}                              # the ended session's own earlier word
        self.assertEqual(self.session_end_check(RELEASED_END, same)["verdict"], "not exercised")

    def test_a_session_end_that_freed_nothing_is_never_a_pass_and_never_a_failure(self):
        normal_exit = {**RELEASED_END, "released": False}      # the stop hook had freed the run before the host ended the session
        found = self.session_end_check(normal_exit, NEXT_CLAIM)
        self.assertEqual(found["verdict"], "not exercised", found)
        self.assertIn("1 session end recorded, none freed a claim", found["evidence"])
        self.assertEqual(self.session_end_check()["verdict"], "not exercised")

    def test_a_later_released_end_does_not_hide_an_earlier_one_the_next_session_missed(self):
        refused = {**NEXT_CLAIM, "decision": "allow", "why": "another session owns this run"}
        second = {**RELEASED_END, "i": 50, "ts": 6000.0, "session": "new000000000"}
        taken = {**NEXT_CLAIM, "i": 51, "ts": 6020.0, "session": "third0000000"}
        found = self.session_end_check(RELEASED_END, refused, second, taken)
        self.assertEqual(found["verdict"], "fail", found)

    def test_the_checks_fail_a_continuation_without_text_and_a_reprint_whose_copy_changed(self):
        with tempfile.TemporaryDirectory(prefix="shiploop-e2e-run-trace-checks-") as temp:
            run = Path(temp) / "run"
            shutil.copytree(self.run_dir, run)
            traced = run_trace.read(run)
            traced["hooks"][0]["text"] = ""
            reprint = next(send for sends in traced["packets"].values() for send in sends if send["repeat"])
            (run / reprint["file"]).write_text("not the text that was sent\n", encoding="utf-8")
            found = run_trace.checks(traced)
        self.assertEqual((found["keepalive_text"]["verdict"], found["keepalive_text"]["evidence"]),
                         ("fail", "1 of 1 continuations recorded no text"))
        self.assertEqual(found["packet_copies"]["verdict"], "fail")
        self.assertIn(reprint["i"], found["packet_copies"]["lines"])

    def test_a_first_print_whose_kept_copy_is_missing_fails_too(self):
        # A print that is not a repeat: the reprint a fresh session gets from `next` differs from the first print, so
        # only checking repeats never saw it (docs/shiploop-trims-plan-2026-10-28.md, T3).
        with tempfile.TemporaryDirectory(prefix="shiploop-e2e-run-trace-copies-") as temp:
            run = Path(temp) / "run"
            shutil.copytree(self.run_dir, run)
            traced = run_trace.read(run)
            single = next(send for sends in traced["packets"].values() for send in sends if not send["repeat"])
            single["file"] = "packets/sent/never-written.md"  # its reprint keeps the shared copy, which still passes
            found = run_trace.checks(traced)
        self.assertEqual(found["packet_copies"]["verdict"], "fail")
        self.assertEqual(found["packet_copies"]["lines"], [single["i"]])

    def test_a_run_before_the_trace_keeps_the_stream_counts(self):
        m = metrics.collect(self.untraced, self.untraced / RUN)
        self.assertEqual([(f["verb"], f["exit"]) for f in m["shiploop_failures"]],
                         [("check", 2), ("workspace", 2), ("complete", 2), ("lint", 3)])  # the piped refusal is missing
        self.assertEqual(m["failures_source"]["file"], "events.jsonl")
        self.assertIn("no trace.jsonl", m["failures_source"]["why"])
        self.assertIsNone(m["run_trace"])
        self.assertNotIn("source", fidelity.refusals(_log(self.untraced), self.untraced, self.untraced / RUN,
                                                     store.read_record(self.untraced / RUN / "state.md")))

    def test_a_trace_that_began_after_a_step_the_model_ran_does_not_cover_the_run(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "partial"
            shutil.copytree(self.out, out)
            trace_file = out / RUN / run_trace.FILE
            rows = [json.loads(line) for line in trace_file.read_text().splitlines()]
            # The intake's accepting command is gone: the step reads as accepted before the trace began.
            kept = [row for row in rows if not row.get("accepted")]
            trace_file.write_text("".join(json.dumps(row) + "\n" for row in kept))
            traced = run_trace.read(out / RUN)
            self.assertFalse(run_trace.covers(traced))
            self.assertIn("1 accepted step the model ran before the trace began", traced["partial"])
            m = metrics.collect(out, out / RUN)
            self.assertEqual(m["failures_source"]["file"], "events.jsonl")
            self.assertIn("does not cover the run", m["failures_source"]["why"])
            self.assertFalse(m["run_trace"]["covers"])
            self.assertIn("partial: 1 accepted step", flow.build(out)["sources"]["refusals"])
            # A step the harness seeded (synthetic) was never the model's: the trace still covers the run.
            state = store.read_record(out / RUN / "state.md")
            record = state["accepted"][self.intake]
            (record.get("result", record) if isinstance(record, dict) else record)["summary"] = "Synthetic: seeded."
            store.write_record(out / RUN / "state.md", state, "ShipLoop navigator state")
            traced = run_trace.read(out / RUN)
            self.assertTrue(run_trace.covers(traced))
            self.assertEqual(traced["seeded_steps"], 1)

    def test_arms_never_gate_on_refusals_counted_by_two_instruments(self):
        traced, old = arms.summarise(self.out), arms.summarise(self.untraced)
        self.assertEqual((traced["refusals"], traced["refusals_source"]), (3, "<run>/trace.jsonl"))
        self.assertEqual((old["refusals"], old["refusals_source"]), (2, "events.jsonl"))
        aa = {"s1": {"refusals": 0, "warm_next_calls": 5, "ingest_chars": 10**9, "orientation_bytes": 10**9}}
        report = arms.decide({"s1": old}, {"s1": traced}, aa)
        self.assertIsNone(report["decision"])
        self.assertIn("s1 refusals", report["reason"])
        self.assertTrue(any("counted from events.jsonl on control and <run>/trace.jsonl on candidate" in n for n in report["notes"]))
        # The same instrument on both arms gates as before: 3 refusals against 2 plus a spread of 0 rejects the candidate.
        report = arms.decide({"s1": {**traced, "refusals": 2}}, {"s1": traced}, aa)
        self.assertEqual((report["decision"], [g["gate"] for g in report["gates_failed"]]), ("control", ["refusals"]))

    # --- flow.json: the sequence ----------------------------------------------------------------------------------------

    def phase(self, flow_data: dict, action: str) -> dict:
        row = next(a for a in flow_data["actions"] if a["action"] == action)
        return row["phases"][0]

    def test_flow_packets_are_the_texts_as_sent_with_their_prints(self):
        self.assertEqual(self.flow["packets_source"], "trace")
        self.assertIn("trace.jsonl", self.flow["sources"]["packets"])
        intake, discovery = self.phase(self.flow, self.intake), self.phase(self.flow, self.discovery)
        self.assertEqual((intake["packet"]["prints"], intake["packet"]["reprints"], intake["packet"]["emissions"]), (2, 1, 1))
        self.assertEqual((discovery["packet"]["prints"], discovery["packet"]["reprints"]), (2, 1))
        sent = (self.run_dir / intake["packet"]["sends"][0]["file"]).read_text()
        self.assertEqual(intake["packet"]["chars"], len(sent))
        self.assertTrue(all(s["file"].startswith("packets/sent/") for s in intake["packet"]["sends"]))

    def test_flow_refusals_and_the_keepalive_are_events_in_their_action(self):
        events = self.phase(self.flow, self.intake)["events"]
        kinds = [e["kind"] for e in events]
        refusals = [e for e in events if e["kind"] == "refusal"]
        self.assertEqual([(e["check_only"], e["source"], e["stage"]) for e in refusals],
                         [(True, "trace", "intake"), (False, "trace", "intake")])
        self.assertIn("exactly one shiploop-state fence", refusals[1]["body"]["text"])
        self.assertEqual(self.phase(self.flow, self.intake)["refusals"], 1)
        keepalive = next(e for e in events if e["kind"] == "keepalive")
        self.assertEqual((keepalive["decision"], keepalive["body"]["text"]), ("continue", CONTINUED))
        # Placed by time among the host's events: each refusal right after the call that caused it, before its result.
        for refusal in refusals:
            at = kinds.index("refusal", events.index(refusal))
            self.assertEqual((kinds[at - 1], kinds[at + 1]), ("call", "result"))
        self.assertLess(events.index(refusals[1]), events.index(keepalive))
        self.assertTrue(self.flow["sources"]["refusals"].startswith(f"{RUN}/trace.jsonl (each refused command on the run"))
        self.assertEqual(self.flow["trace"]["refusals"], 1)

    def test_flow_of_a_run_before_the_trace_is_unchanged_and_says_why(self):
        old = flow.build(self.untraced)
        self.assertEqual(old["packets_source"], "retained")
        self.assertIsNone(old["trace"])
        self.assertIn("no trace.jsonl", old["sources"]["refusals"])
        self.assertIn("not recorded", old["sources"]["keepalive"])
        events = [e for a in old["actions"] for p in a["phases"] for e in p["events"]]
        self.assertFalse([e for e in events if e["kind"] in ("refusal", "keepalive")])
        intake = self.phase(old, self.intake)
        # Not recorded is not zero: a run before the trace has no prints or refusals to count.
        self.assertEqual((intake["packet"]["prints"], intake["packet"]["emissions"], intake["refusals"]), (None, 1, None))

    def test_the_viewer_renders_a_traced_flow(self):
        page = flow.bundle(self.out / "viewer.html", [self.flow]).read_text()
        self.assertIn('e.kind === "refusal"', page)
        self.assertIn('"kind": "keepalive"', page)
        report = packets.build(self.out)
        self.assertTrue(report["emissions_source"].startswith("run trace"))

    # --- the owner page's Read first panel ------------------------------------------------------------------------------

    def test_read_first_refusals_come_from_the_trace_beside_the_stream_count(self):
        r = self.first["refusals"]
        # The refusal from the trace, and from the stream the workspace refusal and the lint that could not run (the panel
        # counts refusal lines, so the usage error is in neither); the stream's own count is the check's, the workspace's and
        # the lint's lines. The lint's line is a refusal line since 2026-10-28.
        self.assertEqual((r["count"], r["checks_failed"], r["stream_count"], r["source"]), (3, 1, 3, "trace"))
        self.assertEqual((r["file"], r["outside_file"]), (f"{RUN}/trace.jsonl", "events.jsonl"))
        self.assertEqual([(row["stage"], row["count"], row["source"]) for row in r["rows"]],
                         [("intake", 1, "trace"), ("intake", 1, "events.jsonl"), ("intake", 1, "events.jsonl")])
        self.assertIn("exactly one shiploop-state fence", r["rows"][0]["cause"])
        self.assertIn("exactly one shiploop-state fence", r["rows"][0]["text"])
        self.assertIn("cannot read record", r["rows"][1]["cause"])
        self.assertIn("not a Git checkout", r["rows"][2]["cause"])
        t = self.first["trace"]
        self.assertEqual((t["measured"], t["packets"], t["reprints"], t["continuations"], t["checks_failed"]),
                         (True, 4, 2, 1, 1))
        self.assertTrue(any("named no run" in line for line in self.first["cannot_show"]))

    def test_read_first_of_a_run_before_the_trace_counts_from_the_stream(self):
        first = flow.read_first(self.untraced, repo=ROOT)
        self.assertEqual((first["refusals"]["count"], first["refusals"]["file"], first["refusals"]["source"]),
                         (3, "events.jsonl", "events.jsonl"))  # the check's, the workspace's and the lint's lines; the piped refusal is missing
        self.assertEqual(first["trace"], {"measured": False, "reason": "the run has no trace.jsonl (ShipLoop before 1.12.0)"})
        self.assertTrue(any("a pipe hid" in line for line in first["cannot_show"]))

    def test_the_owner_page_names_where_the_refusals_came_from(self):
        traced = owner_page.render(_page_data(self.first))
        self.assertIn("From ShipLoop's run trace", traced)
        self.assertIn("the host stream showed 3", traced)
        self.assertIn("2 reprints", traced)
        old = owner_page.render(_page_data(flow.read_first(self.untraced, repo=ROOT)))
        self.assertIn("From the host stream's refusal lines", old)


class OwnerNoteMidStep(unittest.TestCase):
    """--owner-note-at: the harness writes one note once the step's packet has printed, with the run's own CLI; the next
    complete is held to show it, a packet that quotes it is read, the step accepted after delivers it, and the owner_note
    check follows it to the end."""

    def test_the_watcher_writes_mid_step_and_the_check_follows_the_note_to_delivery(self):
        with tempfile.TemporaryDirectory(prefix="shiploop-e2e-owner-note-") as temp:
            base = Path(temp).resolve()
            out, repo = base / "out", base / "repo"
            run = out / RUN
            repo.mkdir(parents=True)
            run.parent.mkdir(parents=True)

            def cli(*argv: str) -> subprocess.CompletedProcess:
                return subprocess.run([sys.executable, "-B", str(CLI), *argv], env=ENV, text=True, capture_output=True,
                                      timeout=60)

            self.assertIsNone(owner_note.due(run, "intake"))  # no run yet
            # init prints the intake packet: the step has started, so a note now is mid-step.
            self.assertEqual(cli("init", "--run-dir", str(run), "--repo", str(repo), "--prompt", "Add a greeting script.")
                             .returncode, 0)
            intake = navigator.current_action(store.read_record(run / "state.md"))["id"]
            self.assertEqual(owner_note.due(run, "intake"), {"stage": "intake", "action": intake})
            self.assertIsNone(owner_note.due(run, "spec"))
            trace = run / shiploop_trace.TRACE_FILE
            printed = trace.read_text()
            trace.write_text("".join(row + "\n" for row in printed.splitlines() if '"kind":"packet"' not in row))
            self.assertIsNone(owner_note.due(run, "intake"))  # no packet line for the action: the step has not started
            trace.write_text(printed)
            with mock.patch.object(owner_note, "POLL_SECONDS", 0.05):
                watcher = owner_note.Watcher(out, CLI, "intake", lambda: str(run)).start()
                deadline = time.monotonic() + 30
                while not (out / owner_note.FILE).exists() and time.monotonic() < deadline:
                    time.sleep(0.05)
                watcher.stop()
            record = json.loads((out / owner_note.FILE).read_text())
            self.assertEqual((record["exit"], record["id"], record["stage"], record["action"]), (0, "N1", "intake", intake),
                             record)
            self.assertEqual(run_trace.checks(run_trace.read(run))["owner_note"]["verdict"], "open")  # active, not delivered
            # A resume finds the record and starts no second watcher.
            self.assertFalse(owner_note.Watcher(out, CLI, "intake", lambda: str(run)).start().thread.is_alive())
            (run / "inbox" / f"{intake}.md").write_text(INTAKE.replace("(fact).", "(fact). Read owner note N1."),
                                                        encoding="utf-8")
            held = cli("complete", "--run-dir", str(run), f"--action={intake}")
            self.assertNotEqual(held.returncode, 0, held.stdout + held.stderr)
            self.assertIn(owner_note.TEXT[:40], held.stdout + held.stderr)
            # A held callback shows the note but never delivers it: the packet the model reads next quotes it again.
            self.assertIn(owner_note.TEXT[:40], cli("next", "--run-dir", str(run)).stdout)
            accepted = cli("complete", "--run-dir", str(run), f"--action={intake}")
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
            found = run_trace.checks(run_trace.read(run))["owner_note"]
            self.assertEqual((found["verdict"], found["evidence"]),
                             ("pass", f"N1 delivered by {intake}, held once in {intake}, cited"))
            self.assertEqual(run_trace.summary(run_trace.read(run))["notes"],
                             {"written": 1, "held": 1, "delivered": 1, "cited": 1})


def _log(out: Path) -> metrics.ToolLog:
    log = metrics.ToolLog()
    metrics.collect(out, None, tools=log)
    return log


def _page_data(first: dict) -> dict:
    return {"read_first": first, "built": "2026-10-25", "sizes": [], "deltas": [], "aa_spread": {}, "earlier": "-",
            "compare_text": "", "decisions": []}


if __name__ == "__main__":
    unittest.main()
