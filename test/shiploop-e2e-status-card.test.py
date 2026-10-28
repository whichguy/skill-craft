#!/usr/bin/env python3
"""test/shiploop_e2e/status_card.py: the owner's status card renders a JSON model and nothing else, no model needed."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
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

    def traced_folder(self) -> Path:
        """A run on W1's test-spec whose trace holds two accepted prelude stages, a review, a refusal and a check."""
        folder = self.base / "battleship-traced"
        run = folder / ".shiploop-runs" / "work-1" / "run"
        run.mkdir(parents=True)
        history = [{"stage": stage, "outcome": "done", "workitem": None} for stage in ("intake", "discovery")]
        history.append({"stage": "step-plan", "outcome": "done", "workitem": "W1"})
        state = {"status": "active", "stage": "inner-loop", "work_index": 0, "work_items": [{"id": "W1"}],
                 "history": history, "inner_loops": {"W1": {"stage": "test-spec"}}}
        (run / "state.md").write_text("# state\n\n```shiploop-state\n" + json.dumps(state) + "\n```\n", encoding="utf-8")
        rows = [{"kind": "command", "verb": "workspace", "exit": 0, "ts": 1000.0},
                {"kind": "packet", "action": "a1", "stage": "intake", "item": None, "ts": 1001.0},
                {"kind": "command", "verb": "complete", "exit": 0, "stage": ["intake", "discovery"], "action": "a1", "ts": 1060.0},
                {"kind": "command", "verb": "complete", "exit": 2, "stage": ["discovery", "discovery"], "action": "a2",
                 "ts": 1090.0, "error": "every primary requirement needs a test case. Missing: R-6."},
                {"kind": "command", "verb": "complete", "exit": 0, "stage": ["discovery", "improve"], "action": "a2", "ts": 1120.0},
                {"kind": "command", "verb": "improve-pass", "exit": 0, "stage": ["improve", "improve"], "action": "i1", "ts": 1200.0},
                {"kind": "command", "verb": "complete", "exit": 0, "stage": ["improve", "step-plan"], "action": "i1", "ts": 1300.0},
                {"kind": "packet", "action": "a3", "stage": "step-plan", "item": "W1", "ts": 1301.0},
                {"kind": "command", "verb": "complete", "exit": 2, "check_only": True, "stage": ["step-plan", "step-plan"],
                 "action": "a3", "ts": 1320.0, "error": "no result file"},
                {"kind": "command", "verb": "complete", "exit": 0, "check_only": True, "stage": ["step-plan", "step-plan"],
                 "action": "a3", "ts": 1330.0},
                {"kind": "command", "verb": "complete", "exit": 0, "stage": ["step-plan", "test-spec"], "action": "a3", "ts": 1400.0}]
        (run / "trace.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows) + "not json\n", encoding="utf-8")
        (folder / "events.jsonl").write_text("", encoding="utf-8")
        return folder

    def test_an_e2e_trace_puts_each_stage_and_review_on_one_time_axis_with_refusals_marked(self):
        model, _meta = status_card.build_e2e(self.traced_folder(), NOW)
        line = model["timeline"]
        self.assertEqual((line["start"], line["end"], line["lanes"]), (1000.0, None, ["Prelude", "W1"]))
        # Each accepted callback closes its stage's span; a review sits in the lane of the stage it reviews; a passed
        # --check-only check moves nothing; the stage the run is on is open (end None).
        self.assertEqual([(s["lane"], s["stage"], s["kind"], s["start"], s["end"]) for s in line["spans"]],
                         [("Prelude", "intake", "stage", 1000.0, 1060.0), ("Prelude", "discovery", "stage", 1060.0, 1120.0),
                          ("Prelude", "discovery", "improve", 1120.0, 1300.0), ("W1", "step-plan", "stage", 1300.0, 1400.0),
                          ("W1", "test-spec", "stage", 1400.0, None)])
        self.assertEqual([(m["lane"], m["stage"], m["kind"], m["at"]) for m in line["marks"]],
                         [("Prelude", "discovery", "refusal", 1090.0), ("W1", "step-plan", "check", 1320.0)])
        self.assertIn("Missing: R-6", line["marks"][0]["text"])
        # Each span names the action it ran, so the card can open that action's prompt and dialogue.
        self.assertEqual([s["action"] for s in line["spans"]], ["a1", "a2", "i1", "a3", None])
        tiles = {tile["label"]: tile for tile in model["tiles"]}
        self.assertEqual((tiles["Elapsed"]["live"], tiles["Elapsed"]["since"]), ("elapsed", 1000.0))
        self.assertEqual((tiles["Improve reviews"]["value"], tiles["Improve reviews"]["sub"]), ("1", "3.0 min"))
        self.assertEqual((tiles["Refusals"]["value"], tiles["Refusals"]["sub"]), ("2", "1 a --check-only check"))
        self.assertEqual(tiles["Stages"]["value"], "3 of " + str(model["progress"]["total"]))
        # A run before the trace has no timeline, and the inline card ignores the new keys.
        untraced, _meta = status_card.build_e2e(self.e2e_folder(), NOW)
        self.assertNotIn("timeline", untraced)
        self.assertNotIn("timeline", status_card.render(model))

    def test_a_refusal_is_material_unless_it_is_a_length_cap_or_an_ordering_slip(self):
        material = status_card.refusal_is_material
        self.assertTrue(material("every primary requirement (spec primary) needs a test case naming it ... Missing: R-6."))
        self.assertTrue(material("ShipLoop mutation check: test is not done. 2 of 8 mutants ... survived"))
        self.assertTrue(material("test_layers gives public page HTML in server.js no unit or component row."))
        for minor in ("test_layers[0].code is 74 characters; keep it within 60 (the packets print it whole)",
                      "no result file at RUN/inbox/nav-1.md: write the result there",
                      "evidence_refs cite files that do not exist: RUN/tests/x.md. Write the file or remove the reference.",
                      "the verify loop is still active: run the receipt's next_argv once",
                      "W1's concern rows are 1,411 characters together; the limit is 1,200 because its step plan prints them",
                      "headline must be one line of at most 100 characters",
                      "result requires outcome and summary: the shiploop-state block is a stored-record wrapper",
                      "assumptions[0].id must be a short identifier such as A1",
                      "assumption A1.disposition must be one of evidenced, probed, open",
                      "Run the improve skill on this test-strategy result first: no call to it has been recorded",
                      "Complete <worktree>/.shiploop-improve/x/reviews/review-2.md (missing or invalid: exit (satisfied)), then run:",
                      'not_covered is [{"behaviour": "<what>", "reason": "<why>"}], each nonblank, or []; then run it again.'):
            self.assertFalse(material(minor), minor)

    def test_review_passes_read_each_review_file_in_order(self):
        reviews = self.base / "wt" / ".shiploop-improve" / "implement-0000abcd" / "reviews"
        reviews.mkdir(parents=True)
        (reviews / "review-2.md").write_text("---\nclassification: trivial\n---\nFound: nothing material.\nChanged: nothing.\n",
                                             encoding="utf-8")
        (reviews / "review-1.md").write_text("---\nclassification: non-trivial\nexit: satisfied\n---\nRead: game.js.\n"
                                             "Found: GET // crashed the server.\nChanged: the URL parse is wrapped.\n"
                                             "Checked: proof-s2.js exits 0.\n", encoding="utf-8")
        (reviews / "checks.md").write_text("not a review", encoding="utf-8")
        # Another host writes each section as a numbered list on the lines below its heading.
        (reviews / "review-10.md").write_text("---\nclassification: non-trivial\n---\n\nRead: spec.md.\n\nFound:\n"
                                              "1. **A-R10.2 named no observable predicate.** It required a test that\n"
                                              "   asserts consistency.\n2. **The NFR row had no acceptance line.**\n\n"
                                              "Changed: A-R10.2 rewritten.\n\n## Handoff\nState: open.\n", encoding="utf-8")
        passes = status_card.review_passes(self.base / "wt", "implement", "nav-ffff0000abcd")
        self.assertEqual([(p["pass"], p["classification"]) for p in passes],
                         [(1, "non-trivial"), (2, "trivial"), (10, "non-trivial")])
        self.assertEqual((passes[0]["found"], passes[0]["changed"], passes[0]["checked"]),
                         ("GET // crashed the server.", "the URL parse is wrapped.", "proof-s2.js exits 0."))
        self.assertEqual(passes[0]["title"], "GET // crashed the server.")
        self.assertEqual(passes[2]["title"], "A-R10.2 named no observable predicate.")
        self.assertIn("2. **The NFR row had no acceptance line.**", passes[2]["found"])
        self.assertEqual(passes[2]["changed"], "A-R10.2 rewritten.")
        self.assertEqual(status_card._review_title("1.\nR-1 and decision 10 state different port rules. Fixed."),
                         "R-1 and decision 10 state different port rules.")
        self.assertEqual(status_card.review_passes(self.base / "wt", "spec", "nav-nothere1"), [])

    def test_action_documents_carry_the_prompt_the_dialogue_and_what_was_material(self):
        def event(kind, t, text, **extra):
            return {"kind": kind, "t": t, "body": {"text": text}, **extra}
        many = [event("call", 100 + n, "echo " + str(n), tool="Bash") for n in range(status_card.ACTION_EVENTS + 5)]
        flow_doc = {"actions": [
            {"action": "nav-spec", "index": 0, "stage": "spec", "work_item": None, "outcome": "done", "accepted": True,
             "phases": [{"packet": {"text": "Goal: write the spec.", "chars": 21, "prints": 2, "reprints": 1,
                                    "sends": [{"file": "packets/sent/a.md"}]},
                         "events": [event("say", 10, "I'll write the spec."), event("call", 11, "x" * 5000, tool="Bash"),
                                    event("result", 12, "ok"),
                                    event("refusal", 13, "test_layers[0].code is 74 characters; keep it within 60", check_only=True),
                                    event("refusal", 14, "every primary requirement needs a test case. Missing: R-6.")]}]},
            {"action": "nav-review", "index": 1, "stage": "improve", "reviewed": "nav-spec", "reviewed_stage": "spec",
             "work_item": None, "outcome": "done", "accepted": True, "phases": [{"packet": None, "events": many}]}]}
        passes = [{"pass": 1, "classification": "non-trivial", "found": "the 100-cell check can't be confirmed",
                   "title": "the 100-cell check can't be confirmed", "changed": "acceptance lines tightened", "checked": "grep"},
                  {"pass": 2, "classification": "trivial", "found": "nothing material", "title": "nothing material",
                   "changed": "nothing", "checked": ""}]
        index, docs, material = status_card.action_documents(flow_doc, lambda stage, action: passes if stage == "spec" else [])
        spec, review = docs["nav-spec"], docs["nav-review"]
        self.assertEqual((spec["prompt"]["text"], spec["prompt"]["prints"], spec["prompt"]["file"]),
                         ("Goal: write the spec.", 2, "packets/sent/a.md"))
        self.assertEqual([d["kind"] for d in spec["dialogue"]], ["say", "call", "result", "refusal", "refusal"])
        self.assertTrue(spec["dialogue"][1]["clipped"])
        self.assertLessEqual(len(spec["dialogue"][1]["text"]), status_card.CLIP["call"] + 1)
        self.assertEqual([(r["check"], r["material"]) for r in spec["refusals"]], [(True, False), (False, True)])
        # A long action keeps its first and last events and counts what it left out.
        self.assertEqual(len(review["dialogue"]), status_card.ACTION_EVENTS)
        self.assertEqual(review["omitted"], 5)
        self.assertEqual(review["dialogue"][-1]["text"], "echo " + str(status_card.ACTION_EVENTS + 4))
        self.assertEqual([p["classification"] for p in review["review"]], ["non-trivial", "trivial"])
        self.assertEqual([(m["action"], m["kind"]) for m in material], [("nav-spec", "refusal"), ("nav-review", "review")])
        self.assertIn("Missing: R-6", material[0]["title"])
        self.assertEqual(material[1]["title"], "the 100-cell check can't be confirmed")
        self.assertEqual([(i["id"], i["stage"], i["material"], i["refusals"]) for i in index],
                         [("nav-spec", "spec", 1, 2), ("nav-review", "spec review", 1, 0)])

    def test_the_trace_checks_are_tiles_with_a_tone_only_for_a_verdict_and_none_without_a_trace(self):
        model, _meta = status_card.build_e2e(self.traced_folder(), NOW)
        checks = [tile for tile in model["tiles"] if tile.get("check")]
        self.assertEqual([(t["label"], t["value"], t["tone"]) for t in checks],
                         [("Keepalive text", "not exercised", ""), ("Packet reprint", "not exercised", ""),
                          ("Owner note", "not exercised", "")])
        self.assertEqual(checks[0]["sub"], "no stop decision continued a turn")
        self.assertEqual(model["tiles"][:4], [t for t in model["tiles"] if not t.get("check")])  # headline tiles first
        # The same run once a stop is continued, a packet is printed twice and the owner writes a note.
        folder = self.base / "battleship-traced"
        run = folder / ".shiploop-runs" / "work-1" / "run"
        text = "the step-plan packet\n"
        sha = hashlib.sha256(text.encode()).hexdigest()[:16]
        (run / "packets" / "sent").mkdir(parents=True)
        (run / "packets" / "sent" / f"{sha}.md").write_text(text, encoding="utf-8")
        sent = {"kind": "packet", "action": "a4", "stage": "test-spec", "item": "W1", "sha": sha, "file": f"packets/sent/{sha}.md"}
        rows = [dict(sent, ts=1401.0), dict(sent, ts=1402.0),
                {"kind": "hook", "decision": "continue", "text": "ShipLoop run is active: continue.", "ts": 1403.0}]
        with (run / "trace.jsonl").open("a", encoding="utf-8") as trace:
            trace.write("".join(json.dumps(row) + "\n" for row in rows))
        notes = run / "owner-notes"
        notes.mkdir()
        (notes / "N1.md").write_text("# ShipLoop owner note\n\n```shiploop-state\n" + json.dumps(
            {"id": "N1", "written_at": "2026-10-28T18:00:00Z", "text": "cite me"}) + "\n```\n", encoding="utf-8")
        model, _meta = status_card.build_e2e(folder, NOW)
        checks = {tile["check"]: tile for tile in model["tiles"] if tile.get("check")}
        self.assertEqual({name: (t["value"], t["tone"]) for name, t in checks.items()},
                         {"keepalive_text": ("pass", "ok"), "packet_reprint": ("pass", "ok"), "owner_note": ("open", "warn")})
        self.assertEqual(checks["owner_note"]["sub"], "N1 waiting")
        # A changed kept copy fails the reprint check, drawn as a failure.
        (run / "packets" / "sent" / f"{sha}.md").write_text("not what was sent\n", encoding="utf-8")
        model, _meta = status_card.build_e2e(folder, NOW)
        failed = next(t for t in model["tiles"] if t.get("check") == "packet_reprint")
        self.assertEqual((failed["value"], failed["tone"]), ("fail", "bad"))
        # A run before the trace has no check tiles.
        untraced, _meta = status_card.build_e2e(self.e2e_folder(), NOW)
        self.assertFalse([t for t in untraced.get("tiles") or () if t.get("check")])

    def test_the_job_document_passes_tiles_comparison_and_bands_through(self):
        model, meta = status_card.build_e2e(self.traced_folder(), NOW)
        job = {"tiles": [{"label": "Improve windows", "value": "11 → 8", "tone": "ok"}],
               "comparison": {"columns": ["Baseline", "This run"],
                              "rows": [{"label": "Verdict", "values": ["PASS", "PASS"], "verdict": {"text": "met", "tone": "ok"}}]},
               "bands": [{"start": 1100.0, "end": 1250.0, "label": "Mac asleep"}]}
        document = status_card.job_document(model, meta, job, NOW)
        # The job's own tiles replace the builder's headline numbers; the run's trace checks follow them.
        self.assertEqual(document["tiles"][:1], job["tiles"])
        self.assertEqual([tile["check"] for tile in document["tiles"][1:]], ["keepalive_text", "packet_reprint", "owner_note"])
        self.assertEqual(document["comparison"], job["comparison"])
        self.assertEqual(document["timeline"]["bands"], job["bands"])
        self.assertEqual(document["timeline"]["spans"], model["timeline"]["spans"])
        plain = status_card.job_document(model, meta, {}, NOW)
        self.assertEqual(plain["tiles"], model["tiles"])
        self.assertNotIn("comparison", plain)

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
