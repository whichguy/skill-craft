#!/usr/bin/env python3
"""test/shiploop_e2e/status_card.py: the owner's status card renders a JSON model and nothing else, no model needed."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import status_card  # noqa: E402

MODEL = {
    "plan": [{"step": "R0 harness", "state": "done"}, {"step": "R1 K3", "state": "running", "note": "4 of 12"},
             {"step": "K2, K4", "state": "waiting", "note": "if arms separate"}, {"step": "Report", "state": "later"}],
    "progress": {"done": 2, "total": 6, "unit": "samples", "running": 1, "stamp": "18:36", "eta": "20:27"},
    "columns": ["T control", "C gate"],
    "rows": [{"name": "K1 chess engine", "sub": "band 3+ steps", "cells": [
        {"slots": [{"state": "below", "label": "2", "tip": "2 steps"}, {"state": "running", "label": "11m"},
                   {"state": "pending"}], "summary": "mean 0.00"},
        {"slots": [{"state": "pass", "label": "6"}, {"state": "error", "label": "err", "tip": "no step plan"},
                   {"state": "bogus"}], "summary": "mean 1.00", "verdict": "supports"}]}],
    "legend": {"pass": "scored 1", "note": "number = steps planned"}}


class StatusCard(unittest.TestCase):
    def test_each_slot_state_draws_its_own_mark_and_an_error_is_never_a_pass(self):
        found = status_card.render(MODEL)
        self.assertEqual(found.count('<i class="f"></i>'), 1)
        self.assertEqual(found.count('<i class="o"></i>'), 2)  # the below slot and its legend mark
        self.assertEqual(found.count('<i class="e"></i>'), 2)  # the error slot and its legend mark
        self.assertEqual(found.count('title="pending"'), 1)
        self.assertEqual(found.count('title="bogus"'), 1)  # an unknown state is drawn as pending
        self.assertIn('title="no step plan"', found)
        self.assertIn('<b class="ok">supports</b>', found)

    def test_the_plan_strip_gives_every_state_an_icon_and_an_unknown_one_reads_pending(self):
        found = status_card.render(MODEL)
        for icon in ("ti-check", "ti-loader-2", "ti-hourglass", "ti-circle-dashed"):
            self.assertIn(icon, found)
        self.assertIn('<span class="ch pending"><i class="ti ti-circle-dashed" aria-hidden="true"></i>Report', found)
        self.assertIn("R1 K3 · 4 of 12", found)

    def test_the_progress_line_and_legend_come_from_the_model(self):
        found = status_card.render(MODEL)
        self.assertIn("2 of 6 samples", found)
        self.assertIn("ETA about 20:27", found)
        self.assertIn("width:33%", found)
        self.assertIn("scored 1", found)
        self.assertIn("number = steps planned", found)
        self.assertIn('<h2 class="sr-only">Status at 18:36: 2 of 6 samples finished, 1 running.</h2>', found)

    def test_the_legend_names_only_the_states_the_grid_draws(self):
        """R3's card (2026-10-26) listed passed and below-target slots it did not have, and no mark for its errors."""
        found = status_card.render({"rows": [{"name": "K2", "cells": [{"slots": [
            {"state": "running", "label": "6m"}, {"state": "error", "label": "err", "tip": "host refused"}]}]}],
            "legend": {"error": "host refused, reruns"}})
        legend = found[found.rindex('<div class="ft" style="justify-content:flex-start'):]
        self.assertIn("running (minutes)", legend)
        self.assertIn('<i class="e"></i>host refused, reruns', legend)
        for absent in ("passed", "below target", "pending"):
            self.assertNotIn(absent, legend)

    def test_text_is_escaped_and_only_rows_are_required(self):
        found = status_card.render({"rows": [{"name": "<b>x</b>", "cells": [{"slots": [{"state": "pass", "tip": '"a"'}]}]}]})
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", found)
        self.assertIn('title="&quot;a&quot;"', found)
        self.assertNotIn('class="pl"', found)

    def test_the_cli_reads_a_model_file_or_stdin(self):
        script = ROOT / "test" / "shiploop_e2e" / "status_card.py"
        done = subprocess.run([sys.executable, "-B", str(script)], input=json.dumps(MODEL), capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("2 of 6", done.stdout)


NOW = datetime(2026, 10, 26, 9, 0, tzinfo=timezone(timedelta(hours=-7)))


def slots(model: dict, row: int) -> list[tuple[str, str]]:
    return [(slot["state"], slot.get("label", "")) for slot in model["rows"][row]["cells"][0]["slots"]]


class Builders(unittest.TestCase):
    """One builder per kind of long job (status consolidation, owner 2026-10-26): each reads the job's own files."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def test_a_tier_receipt_draws_each_family_and_counts_running_lanes_and_failures(self):
        selected = [{"id": name, "family": family} for family, name in
                    (("core", "a"), ("core", "b"), ("shiploop", "c"), ("shiploop", "d"))]
        (self.base / "receipt.json").write_text(json.dumps({
            "groups": ["quick"], "jobs": 1, "status": "running", "selected": selected,
            "completed": [dict(selected[0], status="passed", duration_seconds=60.0),
                          dict(selected[1], status="failed", duration_seconds=120.0)]}), encoding="utf-8")
        model, meta = status_card.build_tier(self.base, NOW)
        self.assertEqual(slots(model, 0), [("pass", ""), ("error", "")])
        self.assertEqual(slots(model, 1), [("running", ""), ("pending", "")])   # one lane: the next suite runs
        self.assertEqual(model["rows"][0]["cells"][0]["verdict"], "failed: b")
        self.assertEqual(model["progress"], {"done": 2, "total": 4, "unit": "suites", "running": 1, "stamp": "09:00",
                                             "eta": "09:03"})            # 2 left x 90 s mean, one lane
        self.assertEqual([step["state"] for step in model["plan"]], ["done", "running"])
        self.assertEqual((meta["title"], meta["status"]), ("Test tier (quick)", "running"))
        self.assertEqual(meta["events"][0]["text"], "FAIL b")
        self.assertIn("4 of 4 suites", status_card.render(dict(model, progress=dict(model["progress"], done=4))))

    def test_a_tier_log_without_a_receipt_reads_what_it_printed_so_far(self):
        log = self.base / "tier.log"
        log.write_text("==> [core] a\nOK   a\n==> [core] b\nFAIL b\nrun-all.sh: 2 suites in 3.0 s wall (--jobs 8); "
                       "slowest: b 2.0 s\nrun-all.sh: FAILED\n", encoding="utf-8")
        model, meta = status_card.build_tier(log, NOW)
        self.assertEqual(slots(model, 0), [("pass", ""), ("error", "")])
        self.assertEqual(meta["status"], "failed")
        self.assertEqual(meta["events"][0], {"at": "2026-10-26T09:00:00-07:00", "kind": "error",
                                             "text": "tier failed: 1 of 2 suites OK"})
        self.assertIn("read from the log", model["legend"]["note"])

    def test_an_advisors_run_draws_each_seat_per_pass_and_a_failed_seat_is_an_error(self):
        run = self.base / "20261025T211947Z-fadb"
        run.mkdir()
        (run / "prompt.txt").write_text("question", encoding="utf-8")
        for seat in ("opus", "codex", "grok", "qwen"):   # each seat's prompt is written as the pass starts
            (run / ("pass1-" + seat + "-prompt.md")).write_text("prompt", encoding="utf-8")
        (run / "pass1-opus.md").write_text("x" * 300, encoding="utf-8")
        (run / "pass1-codex.md").write_text("x" * 300, encoding="utf-8")
        (run / "pass1-host.log").write_text("✅ pass1 opus: 300s exit=0\n❌ pass1 grok: 2s exit=6\n", encoding="utf-8")
        model, meta = status_card.build_advisors(run, NOW)
        # A non-default Ollama family (qwen here) is a seat too, named by its prompt file.
        self.assertEqual(slots(model, 0), [("pass", "O"), ("pass", "A"), ("error", "G"), ("running", "Q")])
        self.assertEqual(slots(model, 1), [("pending", "O"), ("pending", "A"), ("pending", "G"), ("pending", "Q")])
        self.assertEqual([step["state"] for step in model["plan"]], ["running", "pending", "pending"])
        self.assertEqual(model["progress"]["done"], 2)
        self.assertEqual(meta["events"][0]["text"], "❌ pass1 grok: 2s exit=6")   # newest first
        (run / "pass1-meta.json").write_text("{}", encoding="utf-8")       # pass 1 ended: a seat with no answer failed
        model, _meta = status_card.build_advisors(run, NOW)
        self.assertEqual(slots(model, 0)[3], ("error", "Q"))

    def e2e_folder(self) -> Path:
        folder = self.base / "chess-sf-full-abc123"
        run = folder / ".shiploop-runs" / "work-1" / "run"
        run.mkdir(parents=True)
        history = ([{"stage": stage, "outcome": "done", "workitem": None, "action": "p" + stage}
                    for stage in ("intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare")]
                   + [{"stage": stage, "outcome": "done", "workitem": "W1", "action": "w" + stage}
                      for stage in ("step-plan", "test-spec", "implement", "test", "document", "verify")]
                   + [{"stage": "implement", "outcome": "send-back", "workitem": "W1", "action": "sb"},
                      {"stage": "implement", "outcome": "done", "workitem": "W1", "action": "again"},
                      {"stage": "step-plan", "outcome": "done", "workitem": "W2", "action": "w2"}])
        state = {"status": "active", "stage": "inner-loop", "work_index": 1, "completed_work_items": ["W1"],
                 "work_items": [{"id": "W1"}, {"id": "W2"}], "history": history, "active_improve": {"action_id": "x"},
                 "inner_loops": {"W1": {"stage": "done"}, "W2": {"stage": "test-spec"}}}
        (run / "state.md").write_text("# state\n\n```shiploop-state\n" + json.dumps(state) + "\n```\n", encoding="utf-8")
        (folder / "events.jsonl").write_text('{"text": "ShipLoop navigator: refused"}\n{"text": "fine"}\n'
                                             '{"text": "ShipLoop navigator: refused again"}\n', encoding="utf-8")
        (folder / "resume-1.txt").write_text("", encoding="utf-8")
        (folder / "flow.html").write_text("<html></html>", encoding="utf-8")
        (folder / "review-export").mkdir()
        (folder / "review-export" / "run-review.html").write_text("<html></html>", encoding="utf-8")
        return folder

    def test_an_e2e_run_draws_stages_by_item_with_the_current_one_and_its_improve_review(self):
        model, meta = status_card.build_e2e(self.e2e_folder(), NOW)
        names = [row["name"] for row in model["rows"]]
        self.assertEqual(names, ["Prelude", "W1", "W2", "Outer"])
        self.assertEqual(slots(model, 0), [("pass", "")] * 7)
        # A finished item shows only the stages it ran; implement ran twice, after one send-back.
        self.assertEqual(slots(model, 1), [("pass", ""), ("pass", ""), ("pass", "2"), ("pass", ""), ("pass", ""),
                                           ("pass", "")])
        self.assertEqual(model["rows"][1]["sub"], "1 sent back or added work")
        self.assertEqual(slots(model, 2)[:3], [("pass", ""), ("running", "I"), ("pending", "")])
        self.assertTrue(all(state == "pending" for state, _label in slots(model, 3)))
        self.assertEqual([step["state"] for step in model["plan"]],
                         ["done", "done", "running", "pending", "pending"])
        self.assertIn("2 refusals · 1 host restarts", meta["subtitle"])
        # The run-level page first, the per-action flow viewer beside it; both reach the inline card.
        self.assertEqual([link["label"] for link in model["links"]], ["Run Review", "flow"])
        self.assertIn("Run Review: " + str(self.base / "chess-sf-full-abc123" / "review-export" / "run-review.html"),
                      status_card.render(model))
        self.assertEqual((meta["status"], meta["events"][0]["text"]), ("running", "done: step-plan (W2)"))

    def test_the_job_document_carries_the_live_card_keys_and_the_cli_prints_each_view(self):
        folder = self.e2e_folder()
        model, meta = status_card.build_e2e(folder, NOW)
        job = {"title": "Run 6", "findings": [{"tag": "F1", "status": "early", "title": "t", "text": "x"}],
               "events": [{"at": "2026-10-26T08:59:00-07:00", "kind": "info", "text": "started by hand"}]}
        document = status_card.job_document(model, meta, job, NOW)
        self.assertEqual((document["title"], document["status"], document["updatedAt"]),
                         ("Run 6", "running", "2026-10-26T09:00:00-07:00"))
        self.assertEqual(document["progress"]["updatedAt"], "2026-10-26T09:00:00-07:00")
        self.assertEqual(document["events"][0]["text"], "started by hand")
        self.assertLessEqual(len(document["events"]), status_card.EVENTS)
        self.assertEqual(document["findings"], job["findings"])
        script = ROOT / "test" / "shiploop_e2e" / "status_card.py"
        (self.base / "job.json").write_text(json.dumps(job), encoding="utf-8")
        for flag, expect in (([], '"rows"'), (["--html"], '<div class="pl">'),
                             (["--job", str(self.base / "job.json")], '"findings"')):
            done = subprocess.run([sys.executable, "-B", str(script), "build", "e2e", str(folder), *flag],
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn(expect, done.stdout)


if __name__ == "__main__":
    unittest.main()
