#!/usr/bin/env python3
"""Run Review: the exporter, its contract and its page template (skills/shiploop-run-review).

The exporter turns a run output directory into documents that follow SCHEMA.md; the template holds no data and
no content and reads only the collections SCHEMA.md documents. Every run here is synthetic, built in a temporary
directory; nothing outside it is read except the skill's own contract files and the selected ShipLoop's stage
table. Which suites a change under the leaf selects is pinned in test/test-groups.test.py.
"""
from __future__ import annotations

import contextlib
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "shiploop-run-review"
TEMPLATE = SKILL_ROOT / "template" / "index.html"
SCHEMA_MD = SKILL_ROOT / "SCHEMA.md"
DEFAULTS_DIR = SKILL_ROOT / "defaults"
SNAPSHOT = ROOT / "test" / "shiploop_e2e" / "evidence" / "run-review-db-snapshot-2026-10-04.json"
LUNA_EVIDENCE = ROOT / "test" / "shiploop_e2e" / "evidence" / "codex-gpt-6-luna-1.16.1-battleship-20261003.json"
SAMPLE_REVIEW = ROOT / "test" / "fixtures" / "run-review" / "sample.review.json"
SKILL_MD = SKILL_ROOT / "SKILL.md"
ADVICE_MD = SKILL_ROOT / "references" / "advice.md"
_spec = importlib.util.spec_from_file_location("run_review_export", SKILL_ROOT / "scripts" / "export.py")
export = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(export)

T0 = datetime(2026, 10, 3, 10, 0, tzinfo=timezone.utc)
IDS = {name: f"nav-{index:02d}{hashlib.sha256(name.encode()).hexdigest()[:30]}" for index, name in enumerate(
    ("intake", "spec", "test-strategy", "plan", "select-work", "step-plan", "implement", "extra"))}
# (action, stage, minutes after T0 when accepted, outcome)
ACCEPTS = [("intake", "intake", 5, "done"), ("spec", "spec", 15, "done"), ("test-strategy", "test-strategy", 35, "done"),
           ("plan", "plan", 95, "done"), ("select-work", "select-work", 97, "done"),
           ("step-plan", "step-plan", 127, "done"), ("implement", "implement", 140, "revise")]


def iso(minutes: float) -> str:
    return (T0 + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def record(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# ShipLoop record\n\n```shiploop-state\n" + json.dumps(value, indent=2) + "\n```\n")


def write_json(path: Path, value, at: float | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1))
    if at is not None:
        stamp = (T0 + timedelta(minutes=at)).timestamp()
        os.utime(path, (stamp, stamp))
    return path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp(path: Path, minutes: float) -> Path:
    """Set a file's modification time to `minutes` after T0."""
    at = (T0 + timedelta(minutes=minutes)).timestamp()
    os.utime(path, (at, at))
    return path


def make_improve_child(run: Path, action: str, passes: int | None = 3, bind_at: float | None = 50,
                       receipt_at: float | None = 62.5) -> Path:
    """improve/<action>/ with terminal.json and receipt.md and improve/<action>-bind.md beside it, as ShipLoop writes
    them; a None leaves that file out. The span is bind to receipt by modification time."""
    child = run / "improve" / action
    child.mkdir(parents=True, exist_ok=True)
    if passes is not None:
        write_json(child / "terminal.json", {"status": "complete", "progress": {"action_number": passes}})
    for path, text, at in ((child / "receipt.md", "receipt", receipt_at),
                           (run / "improve" / f"{action}-bind.md", "bind", bind_at)):  # bind: a file, not a second child
        if at is not None:
            path.write_text(text)
            stamp(path, at)
    return child


def make_run(root: Path, accepts=ACCEPTS, status: str = "active", loops: bool = True,
             metrics: dict | None = None) -> Path:
    """A run output directory shaped like test/shiploop_e2e/run.py writes it; `metrics` overrides keys of its metrics.json."""
    out = root / "run-out"
    run = out / ".shiploop-runs" / "work-1" / "run"
    history = [{"action": IDS[a], "stage": s, "outcome": o, "summary": "x"} for a, s, _, o in accepts]
    record(run / "state.md", {"status": status, "stage": "inner-loop" if status != "done" else "done",
                              "work_items": [{"id": "W1"}], "work_index": 0,
                              "inner_loops": {"W1": {"stage": "test-green", "action": {"id": "nav-x", "stage": "test-green"}}},
                              "history": history})
    write_json(run / "timeline.json", {"started": iso(0), "accepted": {IDS[a]: iso(m) for a, _, m, _ in accepts}})
    for action, stage, _, outcome in accepts:
        record(run / "results" / f"{IDS[action]}.md", {"action": IDS[action], "stage": stage,
                                                        "result": {"outcome": outcome, "summary": "s"}})
        (run / "packets").mkdir(parents=True, exist_ok=True)
        (run / "packets" / f"{IDS[action]}.md").write_text("P" * 100)
    make_improve_child(run, IDS["plan"])
    worktree = run.parent / "worktree" / "docs" / "shiploop"
    for name, size in (("spec.md", 100), ("test-strategy.md", 300), ("features/f/plan.md", 200)):
        (worktree / name).parent.mkdir(parents=True, exist_ok=True)
        (worktree / name).write_text("k" * size)
    (out / "work" / "docs" / "shiploop").mkdir(parents=True)
    (out / "work" / "docs" / "shiploop" / "spec.md").write_text("old")
    write_json(out / "invocation.json", {"case": "battleship", "host": "codex", "model": "gpt-6-luna", "effort": "max",
                                         "versions": {"plugin_version": "1.16.1", "shiploop_version": "0.48.1"}})
    write_json(out / "result.json", {"case": "battleship", "host": "codex", "invoked": {"pass": True},
                                     "plugin": {"pass": True}, "process": {"pass": False}, "shiploop": {"pass": False,
                                     "run_dir": str(run)}, "committed": {"pass": True},
                                     "checks": [{"command": "a", "pass": True}, {"command": "b", "pass": False}]})
    write_json(out / "metrics.json", {
        # The harness's own stage minutes misattribute time; the export must not use them.
        "stages": [{"stage": "plan", "seconds": 300.0}, {"stage": "test-strategy", "seconds": 7200.0}],
        "shiploop_failures": [{"verb": "complete", "exit": 2, "line": "E" * 300}],
        "model_glue": [{"reasons": ["git commit/add by the model"], "command": "git commit"}] * 2,
        "unmeasured": {},  # every counter measured, as on a Grok run
        "model_calls": 120, "window_tokens": 1_000_000, "tokens": {"input_peak": 250_000}, "compactions": 0,
        **(metrics or {})})
    if loops:
        make_plan_loop(run / "scratch" / "backchain-plan")
        make_step_plan_loop(run / "scratch" / "backchain-step-plan")
    return out


def drop_stamps(out: Path, *names: str, started: bool = False) -> None:
    """Remove the named actions' accept stamps (and optionally the run's start) from the run's timeline.json."""
    path = out / ".shiploop-runs" / "work-1" / "run" / "timeline.json"
    timeline = json.loads(path.read_text())
    for name in names:
        del timeline["accepted"][IDS[name]]
    if started:
        del timeline["started"]
    path.write_text(json.dumps(timeline, indent=1))


def make_plan_loop(loop: Path) -> None:
    """The plan layout: review-records/action-N-review.json and pass-reports/actionN-done-packet.json."""
    write_json(loop / "until-loop-start-input.json", {"work": "binding"}, at=40)
    write_json(loop / "review-records" / "action-1-review.json", {"candidate_identity": {"sha256": "h1"},
                                                                  "classification": "non-trivial"}, at=50)
    write_json(loop / "review-records" / "action-2-review.json", {"candidate_input_sha256": "h1",
                                                                  "candidate_output_sha256": "h2"}, at=62)
    write_json(loop / "review-records" / "action-3-review.json", {"candidate_input_sha256": "h2",
                                                                  "candidate_output_sha256": "h2"}, at=70)
    for number, streak, cls in ((1, 0, "non-trivial"), (2, 0, "non-trivial"), (3, 1, "trivial")):
        write_json(loop / "pass-reports" / f"action{number}-done-packet.json",
                   {"progress": {"trivial_streak": streak}, "last_report": {"classification": cls}})
    write_json(loop / "until-loop-receipt.json", {"status": "complete", "work": f"binding {IDS['plan']}",
                                                  "progress": {"trivial_streak": 1, "required_trivial_reviews": 1}})


def make_step_plan_loop(loop: Path) -> None:
    """The step-plan layout: review-NN.json with candidate snapshots and callback stdout."""
    records = loop / "review-records"
    write_json(loop / "until-loop-start-input.json", {"work": "binding"}, at=100)
    first = write_json(records / "review-01-candidate-plan.json", {"steps": [{"id": "A", "x": 1}, {"id": "B", "x": 1}]})
    second = write_json(records / "review-02-candidate-plan.json",
                        {"steps": [{"id": "A", "x": 2}, {"id": "B", "x": 1}, {"id": "C", "x": 1}]})
    write_json(records / "review-01.json", {"proposed_changes": {"candidate_from_sha256": "h0",
                                                                 "candidate_to_sha256": sha(first)}}, at=110)
    write_json(records / "review-02.json", {"proposed_changes": {"candidate_from_sha256": sha(first),
                                                                 "candidate_to_sha256": sha(second)}}, at=120)
    (records / "review-01-callback-result.stdout").write_text('noise {"progress": {"trivial_streak": 9}}')
    (records / "review-01-callback-result-corrected.stdout").write_text('{"progress": {"trivial_streak": 0}}')
    (records / "review-02-callback-result.stdout").write_text('out\n{"progress": {"trivial_streak": 1}}\n')
    # Only the eight-character prefix names the action, as the real step-plan binding does.
    write_json(loop / "until-loop-receipt.json", {"status": "complete", "work": f"binding {IDS['step-plan'][:12]}"})


class RunReviewTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def export(self, out: Path, *args: str) -> tuple[int, Path]:
        target = self.tmp / f"export-{len(list(self.tmp.glob('export-*')))}"
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = export.main([str(out), "--out", str(target), *args])
        return code, target

    def docs(self, target: Path) -> dict:
        return json.loads((target / "review-export.json").read_text())["docs"]

    def test_stage_minutes_are_accept_deltas_and_the_harness_metric_is_ignored(self):
        code, target = self.export(make_run(self.tmp))
        self.assertEqual(code, 0)
        run = self.docs(target)["runs"]["codex-gpt-6-luna-1.16.1-battleship-20261003"]
        self.assertEqual([(s["stage"], s["min"]) for s in run["stages"]],
                         [("intake", 5.0), ("spec", 10.0), ("test-strategy", 20.0), ("plan", 60.0),
                          ("select-work", 2.0), ("step-plan", 30.0), ("implement", 13.0)])
        self.assertEqual(run["stages"][-1]["outcome"], "revise")
        self.assertEqual((run["stages"][0]["packetBytes"], run["wallMin"], run["order"]),
                         (100, 140.0, int(T0.timestamp())))
        self.assertGreater(run["stages"][0]["resultBytes"], 0)
        self.assertEqual((run["refusals"], run["glue"], run["imp"]), (1, 2, "1 children, 3 review passes"))
        self.assertEqual(len(run["failures"][0]["line"]), 240)
        self.assertEqual((run["improvePasses"], run["improveMin"]), (3, 12.5))
        self.assertEqual(run["stages"][3]["improve"], {"passes": 3, "min": 12.5})  # the plan visit started the child
        self.assertNotIn("improve", run)
        self.assertEqual(run["verdicts"], {"invoked": True, "plugin": True, "process": False, "shiploop": False,
                                           "committed": True, "checks": False})
        self.assertEqual(run["knowledge"], {"docs/shiploop/test-strategy.md": 300,
                                            "docs/shiploop/features/f/plan.md": 200, "docs/shiploop/spec.md": 100})
        self.assertEqual((run["status"], run["time"], run["release"]),
                         ("active", "running, 2.3 h at snapshot", "skill-craft 1.16.1, ShipLoop 0.48.1"))
        facts = (target / "facts.md").read_text().splitlines()
        self.assertTrue(10 <= len(facts) <= 25, facts)
        self.assertIn("plan 60.0", "\n".join(facts))

    def test_phases_follow_the_stage_table_and_the_current_stage(self):
        _, target = self.export(make_run(self.tmp))
        run = self.docs(target)["runs"]["codex-gpt-6-luna-1.16.1-battleship-20261003"]
        self.assertEqual(run["phases"], ["done", "done", "done", "running", "none", "none", "none", "none"])
        self.assertEqual(export.derive_phases([0, 1, 2], 2, "blocked"), ["done", "done", "blocked"] + ["none"] * 5)
        self.assertEqual(export.derive_phases([0, 1, 2, 3, 2], 2, "active")[:4], ["done", "done", "running", "done"])
        self.assertEqual(export.derive_phases(list(range(8)), None, "done"), ["done"] * 8)

    def test_an_unknown_stage_takes_the_previous_phase_and_is_listed(self):
        accepts = [*ACCEPTS, ("extra", "brand-new-stage", 150, "done")]
        code, target = self.export(make_run(self.tmp, accepts, loops=False))
        self.assertEqual(code, 0)
        run = self.docs(target)["runs"]["codex-gpt-6-luna-1.16.1-battleship-20261003"]
        self.assertEqual(run["stages"][-1], {"stage": "brand-new-stage", "outcome": "done", "min": 10.0,
                                             "action": IDS["extra"], "packetBytes": 100,
                                             "resultBytes": run["stages"][-1]["resultBytes"]})
        self.assertEqual(run["phases"][3], "running")
        self.assertIn("brand-new-stage", (target / "facts.md").read_text())

    def test_phase_table_covers_every_shiploop_stage_once_in_graph_order(self):
        path = ROOT / "skills" / "shiploop" / "scripts" / "shiploop_stage_spec.py"
        self.assertTrue(path.is_file(), path)
        spec = importlib.util.spec_from_file_location("run_review_selected_stage_spec", path)
        stage_spec = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = stage_spec  # dataclasses look their module up while the class is built
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(stage_spec)
        listed = [stage for _, stages in export.PHASES for stage in stages]
        self.assertEqual(len(listed), len(set(listed)))
        self.assertEqual(set(listed), set(stage_spec.STAGES))
        orders = [export.STAGE_PHASE[stage] for stage in stage_spec.STAGES]
        self.assertEqual(orders, sorted(orders), "a phase must not start before an earlier phase's stages end")
        phases = sorted((e for e in json.loads((SKILL_ROOT / "defaults" / "expectations.json").read_text())
                         if e["kind"] == "phase"), key=lambda e: e["order"])
        self.assertEqual([e["title"] for e in phases], [title for title, _ in export.PHASES])

    def test_every_exported_document_passes_validate_doc(self):
        _, target = self.export(make_run(self.tmp))
        docs = self.docs(target)
        self.assertEqual(sorted(docs), ["backchain", "runs"])
        for collection, items in docs.items():
            for doc_id, doc in items.items():
                self.assertEqual(export.validate_doc(collection, doc), [], doc_id)
                self.assertEqual(json.loads((target / "docs" / collection / f"{doc_id}.json").read_text()), doc)

    def test_validate_doc_reports_missing_fields_wrong_types_and_bad_enums(self):
        problems = export.validate_doc("runs", {"key": "k", "name": "n", "order": True, "release": "r",
                                                "phases": ["done", "maybe"], "imp": "i", "glue": 0})
        self.assertTrue(any("'time'" in p for p in problems), problems)
        self.assertTrue(any("order: expected a number" in p for p in problems), problems)
        self.assertTrue(any("'maybe' is not one of" in p for p in problems), problems)
        self.assertEqual(export.validate_doc("nope", {}), ["unknown collection 'nope'"])
        measured_nothing = {"key": "k", "name": "n", "order": 1, "release": "r", "phases": ["done"], "time": "t",
                            "imp": "i", "unmeasured": {"model_glue": "a reason"},
                            "stages": [{"stage": "intake", "outcome": "done", "min": None}]}
        self.assertEqual(export.validate_doc("runs", measured_nothing), [])  # no refusals, no glue, a null min
        self.assertTrue(any("unmeasured.model_glue: expected a string" in p for p in export.validate_doc(
            "runs", dict(measured_nothing, unmeasured={"model_glue": 0}))))
        with self.assertRaisesRegex(export.ExportError, "segments\\[0\\]: missing required field 'note'"):
            export.write_export(self.tmp / "bad", {"backchain": {"x": {"segments": [{"label": "a", "min": 1,
                                                                                      "kind": "neutral"}]}}})
        self.assertFalse((self.tmp / "bad").exists())

    def test_plan_loop_layout_gives_passes_changes_streaks_and_the_stage_split(self):
        _, target = self.export(make_run(self.tmp))
        doc = self.docs(target)["backchain"]["codex-gpt-6-luna-1.16.1-battleship-20261003-plan"]
        self.assertEqual((doc["loop"], doc["phase"], doc["order"], doc["stageMin"]), ("plan", 2, 1, 60))
        segments = doc["segments"]
        self.assertEqual([(s["label"], s["min"], s["kind"]) for s in segments],
                         [("Before the loop", 5, "neutral"), ("Pass 1", 10, "unclear"), ("Pass 2", 12, "unclear"),
                          ("Pass 3", 8, "unclear"), ("After the loop", 25, "neutral")])
        self.assertEqual([(s["change"], s["streak"]) for s in segments[1:4]], [("unknown", 0), ("changed", 0), ("none", 1)])
        self.assertEqual(sum(s["min"] for s in segments), doc["stageMin"])
        self.assertIn("trivial", segments[3]["note"])
        facts = {f["k"]: f["v"] for f in doc["facts"]}
        self.assertEqual((facts["Passes"], facts["Final status"], facts["Trivial streak"]), ("3", "complete", "1 of 1 required"))
        self.assertEqual(facts["Receipt"], "scratch/backchain-plan/until-loop-receipt.json")

    def test_step_plan_loop_layout_diffs_snapshots_and_prefers_the_corrected_callback(self):
        _, target = self.export(make_run(self.tmp))
        doc = self.docs(target)["backchain"]["codex-gpt-6-luna-1.16.1-battleship-20261003-step-plan"]
        self.assertEqual((doc["loop"], doc["order"], doc["stageMin"]), ("step-plan", 2, 30))
        passes = [s for s in doc["segments"] if "pass" in s]
        self.assertEqual([(s["min"], s["change"], s["streak"]) for s in passes],
                         [(10, "changed", 0), (10, "1 step changed, added C", 1)])
        self.assertEqual([s["min"] for s in doc["segments"]], [3, 10, 10, 7])

    def test_an_unrecognized_loop_layout_gives_empty_segments_and_says_why(self):
        out = make_run(self.tmp, loops=False)
        loop = out / ".shiploop-runs" / "work-1" / "run" / "scratch" / "group" / "backchain-carry-forward"
        write_json(loop / "until-loop-receipt.json", {"status": "active"})
        code, target = self.export(out)
        self.assertEqual(code, 0)
        doc = self.docs(target)["backchain"]["codex-gpt-6-luna-1.16.1-battleship-20261003-carry-forward"]
        self.assertEqual((doc["segments"], doc["stageMin"], doc["loop"]), ([], None, "carry-forward"))
        self.assertIn("not recognized", {f["k"]: f["v"] for f in doc["facts"]}["Layout"])

    def test_defaults_export_equals_the_defaults_and_is_create_only(self):
        target = self.tmp / "defaults"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(export.main(["--defaults", "--out", str(target)]), 0)
        entries = json.loads((SKILL_ROOT / "defaults" / "expectations.json").read_text())
        config = json.loads((SKILL_ROOT / "defaults" / "config.json").read_text())
        for entry in entries:
            written = json.loads((target / "docs" / "expectations" / f"{entry['key']}.json").read_text())
            self.assertEqual(written, {k: v for k, v in entry.items() if k != "key"})
        for doc_id in ("page", "prompt"):
            self.assertEqual(json.loads((target / "docs" / "config" / f"{doc_id}.json").read_text()), config[doc_id])
        writes = json.loads((target / "writes.json").read_text())
        self.assertEqual(len(writes), len(entries) + 2)
        self.assertTrue(all(set(w) == {"op", "collection", "doc_id", "file_path"} and w["op"] == "set" for w in writes))

    def test_writes_json_lists_every_document_in_a_stable_order_with_absolute_paths(self):
        _, target = self.export(make_run(self.tmp))
        writes = json.loads((target / "writes.json").read_text())
        self.assertEqual([(w["collection"], w["doc_id"]) for w in writes],
                         [("runs", "codex-gpt-6-luna-1.16.1-battleship-20261003"),
                          ("backchain", "codex-gpt-6-luna-1.16.1-battleship-20261003-plan"),
                          ("backchain", "codex-gpt-6-luna-1.16.1-battleship-20261003-step-plan")])
        for write in writes:
            self.assertEqual(write["op"], "set")
            self.assertNotIn("if_version", write)
            self.assertTrue(Path(write["file_path"]).is_absolute() and Path(write["file_path"]).is_file())
        self.assertLess((target / "review-export.json").stat().st_size, export.MAX_COMPACT_BYTES)

    def test_export_is_byte_identical_when_run_twice_and_drops_stale_documents(self):
        out = make_run(self.tmp)
        target = self.tmp / "same"
        with contextlib.redirect_stdout(io.StringIO()):
            export.main([str(out), "--out", str(target)])
            stale = target / "docs" / "backchain" / "codex-gpt-6-luna-1.16.1-battleship-20261003-gone.json"
            stale.write_text("{}")
            first = {p.relative_to(target): p.read_bytes() for p in sorted(target.rglob("*")) if p.is_file()}
            export.main([str(out), "--out", str(target)])
        second = {p.relative_to(target): p.read_bytes() for p in sorted(target.rglob("*")) if p.is_file()}
        del first[stale.relative_to(target)]
        self.assertEqual(first, second)

    def test_absence_is_loud(self):
        out = make_run(self.tmp, loops=False)
        run = out / ".shiploop-runs" / "work-1" / "run"
        (run / "timeline.json").unlink()
        with self.assertRaisesRegex(export.ExportError, "timeline.json"):
            export.build_run(out)
        code, target = self.export(out)
        self.assertEqual(code, 2)
        self.assertFalse(target.exists())
        (out / "metrics.json").unlink()
        with self.assertRaisesRegex(export.ExportError, "metrics.json"):
            export.build_run(out)
        empty = self.tmp / "empty"
        write_json(empty / "metrics.json", {})
        with self.assertRaisesRegex(export.ExportError, "no ShipLoop run directory"):
            export.build_run(empty)

    def test_the_run_directory_result_json_names_wins_and_a_repo_local_run_is_found(self):
        out = make_run(self.tmp, loops=False)
        local = out / "work" / ".shiploop" / "run"
        record(local / "state.md", {"status": "active"})
        os.utime(local / "state.md", (T0.timestamp() + 10**6,) * 2)  # newer, but not the graded run
        self.assertEqual(export.find_run_dir(out, str(out / ".shiploop-runs" / "work-1" / "run")).name, "run")
        self.assertEqual(export.find_run_dir(out, str(out / ".shiploop-runs" / "work-1" / "run")).parent.name, "work-1")
        self.assertEqual(export.find_run_dir(out), local)

    # ---- counters a host cannot measure are absent with a reason, never 0 (R3)

    KEY = "codex-gpt-6-luna-1.16.1-battleship-20261003"

    def test_a_counter_the_harness_names_unmeasured_is_omitted_with_its_reason_never_exported_as_zero(self):
        reasons = {"shiploop_failures": "Claude's tool calls arrive as tool_use blocks, so 0 is a lower bound",
                   "model_glue": "the same blind spot", "tmp_writes": "the same blind spot"}
        # What the Claude harness records: empty lists, which the v1 exporter turned into refusals 0 and glue 0.
        out = make_run(self.tmp, metrics={"unmeasured": reasons, "shiploop_failures": [], "model_glue": []})
        code, target = self.export(out)
        self.assertEqual(code, 0)
        run = self.docs(target)["runs"][self.KEY]
        for field in ("refusals", "glue", "failures"):
            self.assertNotIn(field, run)
        self.assertEqual(run["unmeasured"], {**reasons, "visitContext": export.NO_VISIT_CONTEXT})  # no stage row has one
        self.assertEqual(export.validate_doc("runs", run), [])
        facts = (target / "facts.md").read_text()
        self.assertIn(f"- ShipLoop command failures: not measured ({reasons['shiploop_failures']})", facts)
        self.assertIn(f"- Model glue: not measured ({reasons['model_glue']})", facts)
        self.assertNotIn("failures: 0", facts)
        self.assertNotIn("glue: 0", facts)

    def test_a_counter_the_host_measured_is_still_exported_as_a_number(self):
        failures = [{"verb": "complete", "exit": 2, "line": f"refused {n}"} for n in range(13)]
        out = make_run(self.tmp, metrics={"shiploop_failures": failures,
                                          "unmeasured": {"stage_turns": "no per-call usage events"}})
        code, target = self.export(out)
        self.assertEqual(code, 0)
        run = self.docs(target)["runs"][self.KEY]
        self.assertEqual((run["refusals"], run["glue"], len(run["failures"])), (13, 2, 13))
        self.assertEqual(run["unmeasured"], {"stage_turns": "no per-call usage events",
                                             "visitContext": export.NO_VISIT_CONTEXT})
        self.assertIn("- ShipLoop command failures: 13 (complete 13)", (target / "facts.md").read_text())

    def test_a_metrics_file_without_the_unmeasured_key_is_refused_and_says_how_to_get_one(self):
        for status in ("done", "blocked", "active", "paused"):
            with self.subTest(status=status):
                out = make_run(self.tmp / status, status=status, loops=False)
                metrics = json.loads((out / "metrics.json").read_text())
                del metrics["unmeasured"]
                write_json(out / "metrics.json", metrics)
                with self.assertRaises(export.ExportError) as caught:
                    export.build_run(out)
                message = str(caught.exception)
                self.assertIn("no 'unmeasured' record", message)
                self.assertIn("measured zeros", message)
                if status in ("done", "blocked"):  # run.py --resume-run grades both again and starts no host
                    self.assertIn("--resume-run", message)
                    self.assertIn("starts no host", message)
                    self.assertNotIn("without a host", message)
                else:  # resuming an unfinished run would launch a host: the message must not suggest it
                    self.assertNotIn("--resume-run", message)
                    self.assertIn(f"status is {status}", message)
        code, target = self.export(out)
        self.assertEqual(code, 2)
        self.assertFalse(target.exists())

    def test_the_export_file_names_the_v2_schema_and_the_contract_documents_it(self):
        _, target = self.export(make_run(self.tmp))
        self.assertEqual(json.loads((target / "review-export.json").read_text())["schema"], "run-review-export/v2")
        text = SCHEMA_MD.read_text()
        self.assertIn("run-review-export/v2", text)
        row = next(line for line in text.splitlines() if line.startswith("| `refusals`, `glue`"))
        self.assertIn("optional", row)
        self.assertTrue(any(line.startswith("| `unmeasured`") for line in text.splitlines()))

    # ---- a visit with no accept stamp has unknown minutes, not 0.0 (the E2E peer's cheap fix 1)

    def test_a_visit_with_no_accept_stamp_has_null_minutes_and_the_one_after_it_cannot_be_timed(self):
        out = make_run(self.tmp)
        drop_stamps(out, "step-plan")  # the last visit before implement; the step-plan loop ran inside it
        code, target = self.export(out)
        self.assertEqual(code, 0)
        run = self.docs(target)["runs"][self.KEY]
        self.assertEqual([(s["stage"], s["min"]) for s in run["stages"]],
                         [("intake", 5.0), ("spec", 10.0), ("test-strategy", 20.0), ("plan", 60.0),
                          ("select-work", 2.0), ("step-plan", None), ("implement", None)])
        self.assertEqual(export.validate_doc("runs", run), [])
        self.assertEqual(run["wallMin"], 140.0)  # start to the last stamped accept (implement)
        self.assertIn('"min": null', (target / "docs" / "runs" / f"{self.KEY}.json").read_text())
        facts = (target / "facts.md").read_text()
        self.assertIn("Stages with no minutes", facts)
        self.assertIn("2 of 7", facts)
        loop = self.docs(target)["backchain"][f"{self.KEY}-step-plan"]
        self.assertIsNone(loop["stageMin"])  # an unstamped visit owns no stage window; the ledger still builds

    def test_stage_rows_follow_the_engine_history_not_the_timeline_map(self):
        out = make_run(self.tmp, loops=False)
        timeline = out / ".shiploop-runs" / "work-1" / "run" / "timeline.json"
        data = json.loads(timeline.read_text())
        data["accepted"][IDS["extra"]] = iso(150)  # stamped, but state.md's history never accepted it
        timeline.write_text(json.dumps(data))
        code, target = self.export(out)
        self.assertEqual(code, 0)
        run = self.docs(target)["runs"][self.KEY]
        self.assertEqual([s["stage"] for s in run["stages"]], [a[1] for a in ACCEPTS])

    def test_without_a_run_start_the_first_visit_has_null_minutes(self):
        out = make_run(self.tmp, loops=False)
        drop_stamps(out, started=True)
        code, target = self.export(out)
        self.assertEqual(code, 0)
        run = self.docs(target)["runs"][self.KEY]
        self.assertEqual([s["min"] for s in run["stages"]], [None, 10.0, 20.0, 60.0, 2.0, 30.0, 13.0])
        self.assertNotIn("wallMin", run)

    def test_defaults_and_schema_agree(self):
        for collection, items in export.defaults_docs().items():
            for doc_id, doc in items.items():
                self.assertEqual(export.validate_doc(collection, doc), [], doc_id)
                self.assertEqual(export.extra_fields(collection, doc), [], doc_id)
        text = (SKILL_ROOT / "SCHEMA.md").read_text()
        named = set(re.findall(r"\*\*`(\w+)/", text))
        self.assertEqual(named - set(export.SCHEMA), set())
        self.assertIn("config", named)
        # Every field a SCHEMA.md table names is known to the validator for that collection.
        collection = None
        for line in text.splitlines():
            heading = re.match(r"\*\*`(\w+)/", line)
            if heading:
                collection = heading.group(1)
            elif collection and line.startswith("| `"):
                for field in re.findall(r"`(\w+)`", line.split("|")[1]):
                    self.assertIn(field, export.SCHEMA[collection], f"{collection}.{field}")


# ---------------------------------------------------------------- what a visit is, and the run's measures (R12)

def run_dir_of(out: Path) -> Path:
    return out / ".shiploop-runs" / "work-1" / "run"


def edit_json(path: Path, change) -> None:
    value = json.loads(path.read_text())
    change(value)
    path.write_text(json.dumps(value, indent=1))


def harness_rows(accepts, contexts: dict | None = None, trailing: bool = False) -> list[dict]:
    """metrics.json `stages` as the harness builds it: one row per history entry in order, no action id, and a
    trailing `incomplete` row for the stage the run stopped in. contexts maps a position to that row's `context`."""
    rows = [{"stage": stage, "outcome": outcome, "seconds": 60.0, "turns": None, "tool_calls": None,
             **({"context": (contexts or {})[index]} if index in (contexts or {}) else {})}
            for index, (_, stage, _, outcome) in enumerate(accepts)]
    if trailing:
        rows.append({"stage": "test-green", "outcome": None, "incomplete": True, "seconds": 5.0,
                     "context": {"calls": 99, "peak": 1, "peakPct": 0.1, "compactions": 9}})
    return rows


class RunVisitsTest(unittest.TestCase):
    """R12: a visit's identity (action, skipped, seeded, Improve, context) and the run-level measures."""

    KEY = RunReviewTest.KEY

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def fresh(self) -> Path:
        """A new empty directory for one more run in the same test."""
        return Path(tempfile.mkdtemp(dir=self.tmp))

    def build(self, out: Path) -> tuple[dict, list[str]]:
        docs, facts = export.build_run(out)
        run = docs["runs"][self.KEY]
        self.assertEqual(export.validate_doc("runs", run), [])
        return run, facts

    def row(self, run: dict, name: str) -> dict:
        return run["stages"][[a[0] for a in ACCEPTS].index(name)]

    # ---- identity: the action id, and a visit the engine skipped

    def test_each_stage_row_carries_its_action_id(self):
        run, _ = self.build(make_run(self.tmp))
        self.assertEqual([row["action"] for row in run["stages"]], [IDS[a[0]] for a in ACCEPTS])

    def test_a_visit_with_no_packet_among_issued_packets_is_skipped_and_the_others_are_work(self):
        out = make_run(self.tmp, loops=False)
        (run_dir_of(out) / "packets" / f"{IDS['select-work']}.md").unlink()
        run, facts = self.build(out)
        self.assertEqual([r["stage"] for r in run["stages"] if r.get("skipped")], ["select-work"])
        self.assertIs(self.row(run, "select-work")["skipped"], True)
        self.assertNotIn("packetBytes", self.row(run, "select-work"))
        self.assertEqual(sum("skipped" in r for r in run["stages"]), 1)
        self.assertIn("7 accepted actions (6 work, 1 skipped, 0 seeded)", "\n".join(facts))

    def test_no_packets_at_all_marks_nothing_because_absence_then_says_nothing(self):
        out = make_run(self.tmp, loops=False)
        shutil.rmtree(run_dir_of(out) / "packets")
        run, _ = self.build(out)
        self.assertTrue(all("skipped" not in r and "packetBytes" not in r for r in run["stages"]))
        self.assertEqual(self.row(run, "plan")["action"], IDS["plan"])

    def test_a_model_authored_not_applicable_visit_with_a_packet_and_four_seconds_stays_work(self):
        accepts = [*ACCEPTS[:4], ("select-work", "select-work", 95 + 4 / 60, "done"), *ACCEPTS[5:]]
        out = make_run(self.tmp, accepts, loops=False)
        run_dir = run_dir_of(out)
        for text in ("Not applicable: nothing to select", "Not applicable to this item"):  # the engine's own phrase too
            record(run_dir / "results" / f"{IDS['select-work']}.md", {"action": IDS["select-work"], "stage": "select-work",
                                                                    "result": {"outcome": "done", "summary": text}})
            run, _ = self.build(out)
            row = self.row(run, "select-work")
            self.assertEqual((row["min"], row["packetBytes"], "skipped" in row), (0.1, 100, False), text)
            self.assertEqual(row["action"], IDS["select-work"])

    # ---- Improve per visit and in total

    def test_an_improve_child_gives_passes_and_the_bind_to_receipt_span_on_its_visit(self):
        run, facts = self.build(make_run(self.tmp, loops=False))
        self.assertEqual(self.row(run, "plan")["improve"], {"passes": 3, "min": 12.5})
        self.assertTrue(all("improve" not in r for r in run["stages"] if r["action"] != IDS["plan"]))
        self.assertEqual((run["improvePasses"], run["improveMin"], run["imp"]), (3, 12.5, "1 children, 3 review passes"))
        self.assertIn("- Improve: 1 children, 3 review passes; most passes in one child: 3; 12.5 min bind to receipt",
                      "\n".join(facts))

    def test_a_child_with_no_receipt_has_passes_only_and_the_run_total_minutes_are_unknown_with_a_reason(self):
        out = make_run(self.tmp, loops=False)
        make_improve_child(run_dir_of(out), IDS["implement"], passes=2, receipt_at=None)
        run, facts = self.build(out)
        self.assertEqual(self.row(run, "implement")["improve"], {"passes": 2})  # no min: not 0
        self.assertEqual(self.row(run, "plan")["improve"], {"passes": 3, "min": 12.5})
        self.assertEqual(run["improvePasses"], 5)
        self.assertNotIn("improveMin", run)
        self.assertIn("1 of 2 Improve children lacks a bind.md or receipt.md", run["unmeasured"]["improveMin"])
        self.assertIn("minutes not measured (1 of 2", "\n".join(facts))

    def test_a_child_with_no_terminal_record_has_minutes_only_and_the_passes_total_is_unknown(self):
        out = make_run(self.tmp, loops=False)
        make_improve_child(run_dir_of(out), IDS["implement"], passes=None, bind_at=100, receipt_at=104)
        run, _ = self.build(out)
        self.assertEqual(self.row(run, "implement")["improve"], {"min": 4.0})
        self.assertEqual(run["improveMin"], 16.5)
        self.assertNotIn("improvePasses", run)
        self.assertIn("1 of 2 Improve children has no terminal.json progress.action_number",
                      run["unmeasured"]["improvePasses"])
        self.assertEqual(run["imp"], "2 children")

    def test_a_span_running_backwards_is_unknown_not_negative(self):
        out = make_run(self.tmp, loops=False)
        make_improve_child(run_dir_of(out), IDS["plan"], passes=3, bind_at=70, receipt_at=62.5)
        run, _ = self.build(out)
        self.assertEqual(self.row(run, "plan")["improve"], {"passes": 3})
        self.assertNotIn("improveMin", run)

    def test_a_run_with_no_improve_child_has_zero_passes_and_zero_minutes_measured(self):
        out = make_run(self.tmp, loops=False)
        shutil.rmtree(run_dir_of(out) / "improve")
        run, _ = self.build(out)
        self.assertEqual((run["improvePasses"], run["improveMin"], run["imp"]), (0, 0, "0 children"))
        self.assertTrue(all("improve" not in r for r in run["stages"]))

    # ---- status

    def test_a_paused_run_keeps_the_status_paused(self):
        run, _ = self.build(make_run(self.tmp, status="paused", loops=False))
        self.assertEqual(run["status"], "paused")
        self.assertTrue(run["time"].startswith("paused after"), run["time"])
        self.assertEqual(export.RUN_STATUS["paused"], "paused")

    # ---- the run's calls, context and compactions: present only when measured, else a reason

    def test_a_claude_shaped_run_has_calls_peak_and_window_and_no_compactions(self):
        why = "only Grok's events carry this signal"
        out = make_run(self.tmp, loops=False, metrics={
            "model_calls": 149, "window_tokens": 1_000_000, "tokens": {"input_peak": 271_220}, "compactions": None,
            "unmeasured": {"compactions": why}})
        run, facts = self.build(out)
        self.assertEqual((run["calls"], run["contextPeak"], run["contextWindow"]), (149, 271_220, 1_000_000))
        self.assertNotIn("compactions", run)
        self.assertEqual(run["unmeasured"]["compactions"], why)
        text = "\n".join(facts)
        self.assertIn("calls 149; context peak 271,220; window 1,000,000; compactions not measured (only Grok's", text)

    def test_a_host_that_reported_nothing_has_none_of_them_and_each_reason_sits_under_the_runs_own_name(self):
        out = make_run(self.tmp, loops=False, metrics={
            "model_calls": None, "window_tokens": None, "tokens": {"input_peak": None}, "compactions": None,
            "unmeasured": {"model_calls": "no rollouts", "window_tokens": "no window", "compactions": "no signal"}})
        run, _ = self.build(out)
        for field in ("calls", "contextPeak", "contextWindow", "compactions"):
            self.assertNotIn(field, run)
        self.assertEqual({k: run["unmeasured"][k] for k in ("calls", "contextPeak", "contextWindow", "compactions")},
                         {"calls": "no rollouts", "contextPeak": "no rollouts", "contextWindow": "no window",
                          "compactions": "no signal"})
        self.assertNotIn("model_calls", run["unmeasured"])  # the harness's names are renamed, not duplicated
        self.assertNotIn("window_tokens", run["unmeasured"])

    def test_a_codex_run_with_rollouts_has_all_four_measured_including_zero_compactions(self):
        out = make_run(self.tmp, loops=False, metrics={
            "model_calls": 2565, "window_tokens": 258_400, "tokens": {"input_peak": 251_867}, "compactions": 34})
        run, _ = self.build(out)
        self.assertEqual((run["calls"], run["contextPeak"], run["contextWindow"], run["compactions"]),
                         (2565, 251_867, 258_400, 34))
        for field in ("calls", "contextPeak", "contextWindow", "compactions"):
            self.assertNotIn(field, run["unmeasured"])
        out = make_run(self.fresh(), loops=False, metrics={"compactions": 0})
        self.assertEqual(self.build(out)[0]["compactions"], 0)  # a measured 0 stays 0

    def test_a_metrics_file_that_carries_no_figure_gives_a_reason_and_an_old_default_zero_is_not_a_measurement(self):
        out = make_run(self.tmp, loops=False, metrics={"unmeasured": {}})
        metrics = json.loads((out / "metrics.json").read_text())
        for key in ("model_calls", "window_tokens", "tokens", "compactions"):
            del metrics[key]
        write_json(out / "metrics.json", metrics)
        run, _ = self.build(out)
        for field in ("calls", "contextPeak", "contextWindow", "compactions"):
            self.assertNotIn(field, run)
            self.assertIn("names no reason", run["unmeasured"][field])
        write_json(out / "metrics.json", {**metrics, "model_calls": 0, "tokens": {"input_peak": 0},
                                          "window_tokens": 0, "compactions": None})
        run, _ = self.build(out)
        self.assertTrue(all(field not in run for field in ("calls", "contextPeak", "contextWindow")))

    # ---- per-visit context: joined to the visit's action id, only where measured

    CTX = {2: {"calls": 40, "peak": 100_000, "peakPct": 38.7, "compactions": 1},
           6: {"calls": 7, "peak": 200_000, "peakPct": 77.4, "compactions": 0}}

    def context_run(self, **extra):
        accepts = [*ACCEPTS, ("extra", "implement", 150, "done")]  # the stage name implement appears twice
        contexts = {**self.CTX, 7: {"calls": 3, "peak": None, "peakPct": None, "compactions": 0}, **extra.pop("contexts", {})}
        out = make_run(self.fresh(), accepts, loops=False, metrics={"stages": extra.pop("rows", None) or harness_rows(
            accepts, contexts, trailing=True)})
        return self.build(out)[0]

    def test_a_visit_context_is_joined_by_position_to_its_action_even_when_a_stage_name_repeats(self):
        run = self.context_run()
        by_action = {r["action"]: r.get("context") for r in run["stages"]}
        self.assertEqual(by_action[IDS["test-strategy"]], self.CTX[2])
        self.assertEqual(by_action[IDS["implement"]], self.CTX[6])  # implement, revise
        self.assertEqual(by_action[IDS["extra"]], {"calls": 3, "compactions": 0})  # implement, done: no peak figure, omitted
        self.assertIsNone(by_action[IDS["plan"]])  # the harness could not attribute it: no context, not an empty one
        self.assertNotIn("visitContext", run["unmeasured"])
        self.assertEqual(sum("context" in r for r in run["stages"]), 3)  # the trailing incomplete row joins no visit

    def test_rows_that_do_not_line_up_with_the_history_join_nothing_and_the_run_says_why(self):
        accepts = [*ACCEPTS, ("extra", "implement", 150, "done")]
        rows = harness_rows(accepts, self.CTX)
        rows[6], rows[7] = rows[7], rows[6]  # revise and done swapped: the same stage name, a different outcome
        run = self.context_run(rows=rows)
        self.assertTrue(all("context" not in r for r in run["stages"]))
        self.assertIn("do not line up one to one", run["unmeasured"]["visitContext"])
        shorter = self.context_run(rows=harness_rows(accepts, self.CTX)[:-1])
        self.assertTrue(all("context" not in r for r in shorter["stages"]))
        self.assertIn("7 stage rows do not line up one to one with state.md's 8 visits", shorter["unmeasured"]["visitContext"])

    def test_a_host_whose_stage_rows_carry_no_context_gets_one_run_level_reason(self):
        out = make_run(self.tmp, loops=False, metrics={"stages": harness_rows(ACCEPTS)})
        run, _ = self.build(out)
        self.assertTrue(all("context" not in r for r in run["stages"]))
        self.assertEqual(run["unmeasured"]["visitContext"], export.NO_VISIT_CONTEXT)

    # ---- visits the harness seeded, and stamps that run backwards

    def seeded(self, names=("intake", "spec"), **extra):
        out = make_run(self.fresh(), loops=False)
        edit_json(out / "result.json", lambda r: r.update(seeded={"skipped": list(names), "stage": "test-strategy",
                                                                   "run_dir": "x", "start_head": "abc", **extra}))
        return out

    def test_seeded_visits_read_null_minutes_are_marked_and_are_not_work(self):
        out = self.seeded()
        for name in ("intake", "spec"):  # the seed issues no packet for most of them
            (run_dir_of(out) / "packets" / f"{IDS[name]}.md").unlink()
        run, facts = self.build(out)
        first, second, third = run["stages"][:3]
        self.assertEqual((first["seeded"], first["min"], second["seeded"], second["min"]), (True, None, True, None))
        self.assertTrue("skipped" not in first and "skipped" not in second)  # seeded, not engine-skipped
        self.assertEqual((third["min"], "seeded" in third), (20.0, False))  # timed from the seeded visit's own stamp
        text = "\n".join(facts)
        self.assertIn("7 accepted actions (5 work, 0 skipped, 2 seeded)", text)
        self.assertNotIn("Stages with no minutes", text)  # null by design, not a missing stamp
        self.assertNotIn("Seeded visits not marked", text)

    def test_seeded_names_that_do_not_match_the_history_in_order_mark_nothing_and_facts_say_why(self):
        run, facts = self.build(self.seeded(names=("spec", "intake")))
        self.assertTrue(all("seeded" not in r for r in run["stages"]))
        self.assertEqual([r["min"] for r in run["stages"][:3]], [5.0, 10.0, 20.0])
        self.assertIn("Seeded visits not marked: result.json says the harness seeded spec, intake, but the first 2 "
                      "visits of state.md are intake, spec", "\n".join(facts))
        out = self.seeded()
        edit_json(out / "result.json", lambda r: r["seeded"].update(skipped="intake"))  # not a list
        run, facts = self.build(out)
        self.assertTrue(all("seeded" not in r for r in run["stages"]))
        self.assertIn("not a list of stage names", "\n".join(facts))

    def test_only_result_json_names_seeded_visits_a_synthetic_summary_alone_marks_nothing(self):
        out = self.seeded(names=("intake",))
        state = run_dir_of(out) / "state.md"
        text = state.read_text().replace('"summary": "x"', '"summary": "Synthetic: recorded by the E2E seed"')
        self.assertEqual(text.count("Synthetic: recorded by the E2E seed"), 7)  # every visit says so, one is named
        state.write_text(text)
        run, _ = self.build(out)
        self.assertEqual([bool(r.get("seeded")) for r in run["stages"]], [True] + [False] * 6)
        self.assertTrue(all(r["min"] is not None for r in run["stages"][1:]))

    def test_a_stamp_running_backwards_gives_null_minutes_not_negative_or_clamped(self):
        accepts = [ACCEPTS[0], ("spec", "spec", 3, "done"), *ACCEPTS[2:]]  # spec is stamped before intake
        run, _ = self.build(make_run(self.tmp, accepts))
        self.assertEqual([r["min"] for r in run["stages"][:4]], [5.0, None, 32.0, 60.0])  # the next visit is timed from it
        self.assertEqual(export.validate_doc("runs", run), [])
        self.assertEqual(run["wallMin"], 140.0)

    # ---- the contract names every field it validates, and rejects wrong shapes

    def test_schema_md_documents_every_run_and_stage_field_and_the_labels_that_matter(self):
        text = SCHEMA_MD.read_text()
        for name in (*export.SCHEMA["runs"], *export.SCHEMA["runs"]["stages"][0][1]):
            self.assertRegex(text, rf"\b{re.escape(name)}\b", name)
        for phrase in ("cp -p", "main thread", "input side", "a call's total tokens", "paused", "never 0"):
            self.assertIn(phrase, text)
        self.assertNotIn("`improve` | array", text)

    def test_validate_doc_rejects_wrong_shapes_for_the_new_fields(self):
        run, _ = self.build(make_run(self.tmp, loops=False))
        bad = dict(run, stages=[dict(run["stages"][0], skipped="yes", seeded=1, improve={"passes": "3"},
                                     context={"calls": None}, action=7)], calls="many", status="sleeping")
        problems = "\n".join(export.validate_doc("runs", bad))
        for needle in ("stages[0].skipped: expected a boolean", "stages[0].improve.passes: expected a number",
                       "stages[0].action: expected a string", "calls: expected a number", "'sleeping' is not one of"):
            self.assertIn(needle, problems)


# ---------------------------------------------------------------- the page template and its pure logic
#
# The template has two scripts: <script id="logic"> holds pure functions (no DOM, storage, network or global read) and
# the page script calls them. Every test of what the page decides (countText, headerFacts, minutesText now; cardsFor,
# chipFor, buildPrompt and sequenceModel when they land) goes through run_logic below, against the logic block alone.

def script_blocks() -> dict[str, str]:
    """{"logic": the pure block, "page": the page script}; the template has exactly these two."""
    html = TEMPLATE.read_text(encoding="utf-8")
    found = re.findall(r"<script(?![^>]*type=\"application/json\")([^>]*)>([\s\S]*?)</script>", html)
    blocks = {"logic" if 'id="logic"' in attrs else "page": body for attrs, body in found}
    assert len(found) == 2 and set(blocks) == {"logic", "page"}, \
        "the template has exactly two scripts: the pure logic block, then the page script"
    assert html.index('id="logic"') < html.index("<script>\n"), "the logic block comes before the page script"
    return blocks


def script_text() -> str:
    """The page script (not the logic block)."""
    return script_blocks()["page"]


def run_logic(expression: str):
    """Evaluate one JavaScript expression against the template's logic block and return its JSON value.

    The block runs alone in a node `vm` context that has no document, window, storage or network, so a function that
    reached for any of them would throw here. Pass an array literal to check several calls in one node run, for
    example run_logic('[countText({}, "glue"), minutesText(null)]'). Skips the calling test when node is absent.
    """
    node = shutil.which("node")
    if node is None:
        raise unittest.SkipTest("node is not installed; the structural tests of the template still ran")
    program = ("const vm = require('vm'), fs = require('fs');"
               "const context = vm.createContext({});"
               "vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);"
               "const value = vm.runInContext(process.argv[2], context);"
               "console.log(value === undefined ? 'undefined' : JSON.stringify(value));")
    with tempfile.TemporaryDirectory() as tmp:
        logic = Path(tmp) / "logic.js"
        logic.write_text(script_blocks()["logic"], encoding="utf-8")
        done = subprocess.run([node, "-e", program, str(logic), expression], capture_output=True, text=True,
                              timeout=60)
    if done.returncode != 0:
        raise AssertionError(f"the logic block failed on {expression}:\n{done.stderr}")
    return None if done.stdout.strip() == "undefined" else json.loads(done.stdout)


PAGE_STUB = r"""
/* A small stand-in for the browser: enough of the DOM for the page script to build its view, so a test can set the
   documents the page would read, call its render functions and look at what it drew. No layout, no events. */
function El(tag){this.tagName=tag;this.children=[];this.attrs={};this.style={};this.className="";this._text="";this.innerHTML="";
  this.hidden=false;this.value="";this.checked=false;this.disabled=false;this.parent=null;this.onclick=null;this.onchange=null;this.oninput=null;this.ontoggle=null;}
El.prototype.appendChild=function(c){c.parent=this;this.children.push(c);return c;};
Object.defineProperty(El.prototype,"firstChild",{get:function(){return this.children[0]||null;}});
El.prototype.removeChild=function(c){this.children.splice(this.children.indexOf(c),1);c.parent=null;return c;};
El.prototype.setAttribute=function(k,v){this.attrs[k]=String(v);};
El.prototype.getAttribute=function(k){return this.attrs[k]===undefined?null:this.attrs[k];};
El.prototype.scrollIntoView=El.prototype.focus=El.prototype.select=function(){};
Object.defineProperty(El.prototype,"textContent",{get:function(){return this._text+this.children.map(function(c){return c.textContent;}).join("");},
  set:function(v){this._text=String(v);this.children=[];}});
var REG={},NAMED={};
HTML_TAGS.forEach(function(t){var e=new El(t.tag);e.attrs.id=t.id;e.hidden=t.hidden;REG[t.id]=e;});
HTML_RADIOS.forEach(function(r){var e=new El("input");e.value=r.value;e.attrs.name=r.name;(NAMED[r.name]=NAMED[r.name]||[]).push(e);});
var document={title:"",getElementById:function(id){return REG[id]||null;},getElementsByName:function(n){return NAMED[n]||[];},
  createElement:function(t){return new El(t);},createElementNS:function(ns,t){return new El(t);},createTextNode:function(s){var e=new El("#text");e._text=String(s);return e;}};
var window={scrollTo:function(){}},navigator={},localStorage={getItem:function(){return STORED;},setItem:function(k,v){STORED=v;}};
function setTimeout(){}
function walk(el,pred,out){out=out||[];if(pred(el))out.push(el);el.children.forEach(function(c){walk(c,pred,out);});return out;}
function byClass(root,cls){return walk(typeof root==="string"?REG[root]:root,function(e){return(" "+e.className+" ").indexOf(" "+cls+" ")>=0;});}
function textOf(id){return REG[id].textContent;}
"""


def page_probe(expression: str, stored: str | None = None, setup: str = ""):
    """Run the page script against PAGE_STUB, run `setup` (JavaScript that sets data and calls render functions), then
    evaluate `expression` and return its JSON value. `stored` is what localStorage holds. Skips when node is absent."""
    node = shutil.which("node")
    if node is None:
        raise unittest.SkipTest("node is not installed; the structural tests of the template still ran")
    html = TEMPLATE.read_text(encoding="utf-8")
    tags = [{"tag": m.group(1), "id": m.group(3), "hidden": bool(re.search(r"\shidden(\s|$)", m.group(2)))}
            for m in re.finditer(r'<(\w+)((?:\s[^>]*?)?\sid="([^"]+)"[^>]*)>', html.split('<script id="logic">')[0])]
    radios = [{"name": m.group(1), "value": m.group(2)}
              for m in re.finditer(r'<input[^>]*name="(\w+)"[^>]*value="(\w+)"', html)]
    blocks = script_blocks()
    program = ("const vm=require('vm'),fs=require('fs');const a=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));"
               "const ctx=vm.createContext({HTML_TAGS:a.tags,HTML_RADIOS:a.radios,STORED:a.stored,console});"
               "vm.runInContext(a.stub,ctx);vm.runInContext(a.logic,ctx);vm.runInContext(a.page,ctx);"
               "vm.runInContext(a.setup,ctx);const v=vm.runInContext(a.expr,ctx);"
               "console.log(v===undefined?'undefined':JSON.stringify(v));")
    with tempfile.TemporaryDirectory() as tmp:
        arg = Path(tmp) / "arg.json"
        arg.write_text(json.dumps({"tags": tags, "radios": radios, "stored": stored, "stub": PAGE_STUB,
                                   "logic": blocks["logic"], "page": blocks["page"], "setup": setup,
                                   "expr": expression}), encoding="utf-8")
        done = subprocess.run([node, "-e", program, str(arg)], capture_output=True, text=True, timeout=60)
    if done.returncode != 0:
        raise AssertionError(f"the page script failed on {expression}:\n{done.stderr}")
    return None if done.stdout.strip().splitlines()[-1] == "undefined" else json.loads(done.stdout.strip().splitlines()[-1])


class TemplateHasNoDataTests(unittest.TestCase):
    def test_no_embedded_data_or_placeholder(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8")
        self.assertNotIn("__SEED__", html)
        self.assertIsNone(re.search(r"<script[^>]*application/json", html), "no embedded JSON data block")

    def test_content_constants_live_in_data(self) -> None:
        for block, js in script_blocks().items():
            for name in ("PHASES", "CRIT", "SEED", "ART_URL", "DEF["):
                self.assertNotIn(name, js, f"{name} in the {block} script is content or data and belongs in the database")

    def test_only_documented_collections_are_read(self) -> None:
        schema = SCHEMA_MD.read_text(encoding="utf-8")
        used = set(re.findall(r"collection\(\"([a-z]+)\"\)", script_text())) | set(re.findall(r"\[\"([a-z]+)\",\"(?:runs|obs|acts|bc|exp|cfg|rev)\"\]", script_text()))
        self.assertTrue(used, "the template reads the database")
        for name in used:
            self.assertRegex(schema, r"\*\*`%s[/`]" % re.escape(name), f"collection {name} is documented in SCHEMA.md")

    def test_reads_db_through_the_capability_and_degrades_without_it(self) -> None:
        js = script_text()
        self.assertIn('claude.use("db")', js)
        self.assertIn("function offline()", js)

    def test_javascript_parses(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not installed; the structural tests above still ran")
        with tempfile.TemporaryDirectory() as tmp:
            for block, js in script_blocks().items():
                path = Path(tmp) / f"{block}.js"
                path.write_text(js, encoding="utf-8")
                done = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, timeout=60)
                self.assertEqual(done.returncode, 0, f"{block}: {done.stderr}")


class LogicBlockTests(unittest.TestCase):
    """What the page says about a number is decided by pure functions, so an unmeasured counter cannot read as 0."""

    def test_the_logic_block_reads_no_page_state(self) -> None:
        code = re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", "", script_blocks()["logic"])
        code = re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', code)  # a string literal is data (a stage may be called "document")
        self.assertIsNone(re.search(r"\b(document|window|localStorage|sessionStorage|navigator|claude|fetch|"
                                    r"XMLHttpRequest|setTimeout|byId)\b", code), "the logic block must be pure")
        self.assertIn("function countText(", code)

    def test_a_counter_the_run_does_not_carry_reads_not_measured_and_a_measured_zero_stays_zero(self) -> None:
        self.assertEqual(run_logic('[countText({}, "refusals"), countText({refusals: 13}, "refusals"),'
                                   ' countText({glue: 0}, "glue"), countText(null, "glue"),'
                                   ' countText({refusals: "13"}, "refusals")]'),
                         ["not measured", "13", "0", "not measured", "not measured"])

    def test_the_header_line_never_prints_undefined_for_a_missing_counter(self) -> None:
        unmeasured, measured = run_logic(
            '[headerFacts({release: "r", time: "t", imp: "i"}),'
            ' headerFacts({release: "r", time: "t", imp: "i", refusals: 13, glue: 0})]')
        self.assertEqual(unmeasured, "r | t | refusals not measured | glue not measured | i")
        self.assertEqual(measured, "r | t | 13 refusals | 0 glue | i")
        self.assertNotIn("undefined", unmeasured + measured)

    def test_a_stage_with_no_minutes_reads_n_a_never_zero(self) -> None:
        self.assertEqual(run_logic("[minutesText(null), minutesText(undefined), minutesText(0), minutesText(4.5)]"),
                         ["n/a", "n/a", "0 min", "4.5 min"])

    def test_the_page_uses_them_and_labels_its_file_sizes_for_what_they_are(self) -> None:
        page = script_text()
        self.assertIn("headerFacts(run)", page)
        self.assertNotIn("run.refusals", page)
        self.assertIn("packet and result are file sizes, not what the model read", page)
        self.assertNotIn("bytes printed and returned", page)  # packetBytes is a packet file's size, not what the model read
        self.assertIn("visitTable(run,model)", page)
        self.assertNotIn('(r.a.min||0)+" min"', page)  # a missing minute is not drawn as 0 min


# A small document set: two runs, the phase and criterion documents, one finding and one option. Most page tests start here.
SAMPLE_SETUP = """
data.runs=[
 {key:"r1",name:"Run one",order:2,release:"skill-craft 1.0",phases:["done","blocked","none","none","none","none","none","none"],time:"t",imp:"i",wallMin:30,
  stages:[{stage:"intake",outcome:"done",min:5},{stage:"spec",outcome:"blocked",min:25}]},
 {key:"r2",name:"Run two",order:1,release:"skill-craft 1.0",phases:["done","done","none","none","none","none","none","none"],time:"t",imp:"i",wallMin:12,
  stages:[{stage:"intake",outcome:"done",min:2},{stage:"spec",outcome:"done",min:10}]}];
data.exp={"phase-0":{kind:"phase",order:0,title:"Understand",short:"Intake",text:"Understand the request."},
 "phase-1":{kind:"phase",order:1,title:"Specify",short:"Spec",text:"Write the spec."},
 "group-principles":{kind:"group",order:1,title:"Principles",text:"What every run is held to."},
 "P1":{kind:"criterion",group:"group-principles",order:1,title:"The script owns the flow",text:"The model never chooses the next stage."},
 "P2":{kind:"criterion",group:"group-principles",order:2,title:"Loop contracts",text:"The script writes every loop contract."}};
data.obs=[{id:"o1",title:"First finding",criterion:"P1",kind:"defect",status:"open",phase:1,run:"r1",expected:"It holds.",observed:"It broke.",evidence:"run/x.md",
  effect:"broken",advice:"Fix it in the script.",figure:{kind:"bars",items:[{label:"refusals",value:0,tone:"expected"},{label:"seen",value:13,tone:"saw"}]}},
 {id:"o2",title:"Second finding",criterion:"P2",kind:"decision",status:"open",phase:2,run:"r1",expected:"e2",observed:"s2",evidence:""}];
data.acts=[{id:"a1",title:"Fix the flow",goal:"Make the script own it.",why:"Because.",criterion:"P1",status:"open",findings:["o1"],kind:"fix-shiploop",effort:"S",recommended:true,cost:"one live run"},
 {id:"a2",title:"Accept the limit",goal:"Write it down.",why:"w",status:"open",kind:"accept"}];
Object.keys(loaded).forEach(function(k){loaded[k]=true;});renderAll();
"""
STEP_SECTIONS = "[1,2,3,4].map(function(n){return !REG['step-'+n].hidden;})"


class PageShellTests(unittest.TestCase):
    """R4: the page is four steps, one shown at a time, with the viewer's working set kept per run in the browser."""

    def test_the_template_has_exactly_four_step_sections_and_none_of_the_removed_ones(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8")
        steps = re.findall(r'<section class="step" id="(step-\d)" data-step="(\d)"', html)
        self.assertEqual(steps, [("step-1", "1"), ("step-2", "2"), ("step-3", "3"), ("step-4", "4")])
        self.assertEqual(len(re.findall(r"<section\b", html)), 4, "every section of the page is one of the four steps")
        for gone in ("seqsvg", "seqwords", "iterstrip", 'id="timeline"', "h-iter", "unexp", "unx-impact", "unx-where",
                     'id="react"', 'id="include"', 'name="mode"', "renderSequence", "SEQ_ACTORS", "renderIterations",
                     "iterCard", "renderInclude", "renderReact", "statusSeg", "saveExp", "openEdit", "submitEdit",
                     "UNX_IMPACT", "concatPreamble", "slrr4", "iterBase"):
            self.assertNotIn(gone, html, f"{gone} was removed with the section it served")

    def test_the_page_reads_and_writes_no_iterations_and_the_contract_no_longer_documents_them(self) -> None:
        self.assertNotIn("iterations", script_text())
        self.assertNotIn("iterations/", SCHEMA_MD.read_text(encoding="utf-8"))
        self.assertNotIn("iterations", export.SCHEMA)

    def test_one_step_shows_at_a_time_and_the_stepper_carries_live_counts(self) -> None:
        out = page_probe('[' + STEP_SECTIONS + ', REG.steps.children.map(function(b){return b.textContent;}),'
                         ' REG.steps.children.map(function(b){return b.getAttribute("aria-current");})]',
                         setup=SAMPLE_SETUP)
        self.assertEqual(out[0], [True, False, False, False])
        self.assertEqual(out[1], ["1. What happened2 visits", "2. Expected versus seen1 broken, 1 not rated",
                                  "3. Findings and options2 open, 0 ticked", "4. Your plan0 ticked"])
        self.assertEqual(out[2], ["step", None, None, None])
        moved = page_probe('go(3);[' + STEP_SECTIONS + ', REG.steps.children.map(function(b){return b.getAttribute("aria-current");}),'
                           ' REG.stepnav.children.map(function(b){return b.textContent+":"+b.disabled;})]', setup=SAMPLE_SETUP)
        self.assertEqual(moved[0], [False, False, True, False])
        self.assertEqual(moved[1], [None, None, "step", None])
        self.assertEqual(moved[2], ["Back:false", "Build my plan:false"])

    def test_the_step_and_the_ticks_survive_a_reload_per_run_and_garbage_storage_is_ignored(self) -> None:
        page = script_text()  # every storage access is guarded, so a blocked or empty store never breaks the page
        for at in [m.start() for m in re.finditer(r"localStorage", page)]:
            self.assertIn("try{", page[max(0, at - 90):at], f"localStorage at {page[at - 30:at + 40]!r} is not guarded")
        out = page_probe('[' + STEP_SECTIONS + ', textOf("selcount")]', setup=SAMPLE_SETUP,
                         stored=json.dumps({"step": 3, "run": "r1", "sel": {"r1": {"opts": {"a1": True}, "find": {}}}}))
        self.assertEqual(out[0], [False, False, True, False])
        self.assertEqual(out[1], "You ticked 1 option. They become one plan.")
        other = page_probe('L.run="r2";renderAll();textOf("selcount")', setup=SAMPLE_SETUP,
                           stored=json.dumps({"step": 3, "run": "r1", "sel": {"r1": {"opts": {"a1": True}, "find": {}}}}))
        self.assertEqual(other, "Nothing ticked yet. Tick options in step 3.")
        for junk in ("not json", "[1]", json.dumps({"step": 9, "sel": 5}), "null"):
            self.assertEqual(page_probe(STEP_SECTIONS, setup=SAMPLE_SETUP, stored=junk), [True, False, False, False], junk)

    def test_a_tick_is_kept_for_that_run_only_and_the_sticky_bar_counts_it(self) -> None:
        out = page_probe('var boxes=byClass("cards","opt");boxes[0].children[0].checked=true;boxes[0].children[0].onchange();'
                         'var n1=textOf("stickybar");L.run="r2";renderAll();var n2=textOf("stickybar");'
                         'L.run="r1";renderAll();[n1,n2,textOf("stickybar"),REG.stickybar.hidden,textOf("selcount"),JSON.parse(STORED).sel.r1.opts]',
                         setup=SAMPLE_SETUP)
        self.assertEqual(out, ["1 tickedYour plan", "", "1 tickedYour plan", False, "You ticked 1 option. They become one plan.", {"a1": True}])

    def test_the_run_detail_reads_the_new_run_fields_defensively(self) -> None:
        bare = page_probe('textOf("rundetail")', setup=SAMPLE_SETUP)
        for line in ("Model calls (main thread)not measured", "Context peak (main thread)not measured",
                     "Compactionsnot measured"):
            self.assertIn(line, bare)
        self.assertNotRegex(bare, r"undefined|NaN|null")
        rich = page_probe(
            'Object.assign(data.runs[0],{calls:149,contextPeak:271220,contextWindow:1000000,compactions:0,improvePasses:19,improveMin:3.7,'
            'unmeasured:{}});renderAll();textOf("rundetail")', setup=SAMPLE_SETUP)
        for line in ("Model calls (main thread)149", "Context peak (main thread)271,220 tokens of 1,000,000 (27.1%)", "Compactions0"):
            self.assertIn(line, rich)
        self.assertNotIn("Stages: minutes between accepts", rich)  # the old stage table is replaced by the picture and its table

    def test_the_improve_card_reads_the_stage_rows_and_totals_and_says_when_it_was_not_measured(self) -> None:
        bare = page_probe('textOf("kpis")', setup=SAMPLE_SETUP)
        self.assertIn("Improvenot measuredno Improve record", bare)
        rich = page_probe(
            'Object.assign(data.runs[0],{improvePasses:19,improveMin:3.7,unmeasured:{}});data.runs[0].stages[0].improve={passes:3,min:1.2};'
            'data.runs[0].stages[1].improve={passes:2};renderAll();textOf("kpis")', setup=SAMPLE_SETUP)
        self.assertIn("Improve19 passes3.7 min, 12% of elapsed", rich)
        reason = page_probe('data.runs[0].unmeasured={improvePasses:"no improve children recorded"};renderAll();textOf("kpis")',
                            setup=SAMPLE_SETUP)
        self.assertIn("Improvenot measuredno improve children recorded", reason)


class PageShellLogicTests(unittest.TestCase):
    def test_measured_text_adds_the_harness_reason_to_not_measured_and_leaves_numbers_alone(self) -> None:
        self.assertEqual(run_logic('[measuredText({unmeasured:{calls:"no per-call usage"}},"calls"), measuredText({},"calls"),'
                                   ' measuredText({calls:0,unmeasured:{calls:"x"}},"calls"), reasonFor({unmeasured:{a:5}},"a"),'
                                   ' reasonFor(null,"a")]'),
                         ["not measured (no per-call usage)", "not measured", "0", "", ""])

    def test_context_text_is_a_share_of_the_window_only_when_both_were_measured(self) -> None:
        self.assertEqual(run_logic('[contextText({contextPeak:271220,contextWindow:1000000}), contextText({contextPeak:5000}),'
                                   ' contextText({unmeasured:{contextPeak:"Codex rollouts are not read"}}), contextText({})]'),
                         ["271,220 tokens of 1,000,000 (27.1%)", "5,000 tokens", "not measured (Codex rollouts are not read)",
                          "not measured"])

    def test_fact_rows_list_text_facts_when_present_and_the_counters_always(self) -> None:
        rows = run_logic('[factRows({host:"codex",wallMin:12.5,calls:3}), factRows({}).map(function(r){return r[0];})]')
        self.assertEqual(rows[0], [["Host", "codex"], ["Elapsed (accept to accept)", "12.5 min"],
                                   ["Model calls (main thread)", "3"], ["Context peak (main thread)", "not measured"],
                                   ["Compactions", "not measured"]])
        self.assertEqual(rows[1], ["Model calls (main thread)", "Context peak (main thread)", "Compactions"])

    def test_improve_facts_read_the_stage_rows_and_totals_and_never_invent_a_zero(self) -> None:
        none, some = run_logic(
            '[improveFacts({stages:[{stage:"spec",outcome:"done"}]}),'
            ' improveFacts({wallMin:1158.5,improvePasses:41,improveMin:360.3,stages:[{stage:"spec"},{stage:"plan",improve:{passes:3,min:24.5}},'
            '{stage:"step-plan",improve:{passes:1}}]})]')
        self.assertEqual(none, {"rows": [], "passes": None, "min": None, "share": None})
        self.assertEqual(some, {"rows": [{"visit": 2, "stage": "plan", "passes": 3, "min": 24.5},
                                         {"visit": 3, "stage": "step-plan", "passes": 1, "min": None}],
                                "passes": 41, "min": 360.3, "share": 31})
        self.assertEqual(run_logic('improveFacts(null)'), {"rows": [], "passes": None, "min": None, "share": None})


def luna_run() -> dict:
    """The real Luna battleship run document (39 visits) from the committed evidence."""
    return next(iter(json.loads(LUNA_EVIDENCE.read_text())["docs"]["runs"].values()))


def phases_of(rows: list[dict]) -> list[int]:
    """The phase of each visit as the exporter's table gives it; an unknown stage takes the visit before it."""
    previous, out = -1, []
    for row in rows:
        previous = export.STAGE_PHASE.get(row["stage"], previous)
        out.append(previous)
    return out


# Options and findings for the step 3 tests: f1 has options of every kind and rank, f2 shares one, f3 is closed, f4 belongs
# to another run, f5 is general, f6 is open with no option.
FINDINGS_JS = """[
 {id:"f1",run:"r1",status:"open",criterion:"P1"},{id:"f2",run:"r1",status:"open",criterion:"P2"},
 {id:"f3",run:"r1",status:"fixed",criterion:"P1"},{id:"f4",run:"r2",status:"open"},{id:"f5",run:"any",status:"open"},
 {id:"f6",runs:["r1","r3"],status:"open"},{id:"f7",run:"r1"}]"""
OPTIONS_JS = """[
 {id:"x1",title:"t",kind:"accept",effort:"S",findings:["f1"]},
 {id:"x2",title:"t",kind:"fix-harness",effort:"L",findings:["f1"]},
 {id:"x3",title:"t",kind:"fix-shiploop",effort:"S",findings:["f1"]},
 {id:"x4",title:"t",kind:"fix-shiploop",effort:"M",recommended:true,findings:["f1"]},
 {id:"y1",title:"t",kind:"gather-evidence",effort:"M",findings:["f1"]},
 {id:"y2",title:"t",kind:"gather-evidence",effort:"S",findings:["f1"]},
 {id:"s1",title:"shared",kind:"fix-shiploop",effort:"M",findings:["f2","f1"]},
 {id:"d1",title:"done",status:"done",findings:["f1"]},
 {id:"c1",title:"closed only",kind:"accept",findings:["f3"]},
 {id:"l1",title:"loose"},{id:"l2",title:"ghost",findings:["nope"]}]"""


class FindingsAndOptionsTests(unittest.TestCase):
    """R5: the findings and options fields, the step 3 grouping, the pictures and the cards that show them."""

    def test_validate_doc_accepts_the_new_fields_and_rejects_bad_ones(self) -> None:
        finding = {"title": "t", "runs": ["a", "b"], "effect": "bent", "advice": "Inferred: x.",
                   "figure": {"kind": "bars", "items": [{"label": "saw", "value": 13, "unit": "refusals",
                                                          "lowerBound": True, "tone": "saw"}]}}
        option = {"title": "t", "status": "planned", "findings": ["o1"], "kind": "change-expectation", "effort": "M",
                  "recommended": True, "cost": "a live run", "ref": "docs/x.md",
                  "change": {"target": "spec", "to": "new", "reason": "why"}}
        self.assertEqual(export.validate_doc("observations", finding), [])
        self.assertEqual(export.validate_doc("actions", option), [])
        for field, value in (("kind", "fix-it"), ("effort", "XL"), ("status", "building"), ("recommended", "yes"),
                             ("findings", "o1"), ("change", {"target": "repo", "to": "t", "reason": "r"}),
                             ("change", {"target": "page", "to": "t"})):
            self.assertTrue(export.validate_doc("actions", {**option, field: value}), f"actions.{field}={value!r}")
        for field, value in (("effect", "holds"), ("runs", "a"), ("advice", 3)):
            self.assertTrue(export.validate_doc("observations", {**finding, field: value}), f"observations.{field}")
        self.assertNotIn("base", export.SCHEMA["actions"])  # no longer read

    def test_a_figure_is_a_small_structured_spec_never_markup(self) -> None:
        def check(figure):
            return export.validate_doc("observations", {"figure": figure})
        bar = {"label": "a", "value": 1}
        self.assertEqual(check({"kind": "bars", "items": [bar] * 6}), [])
        self.assertTrue(check({"kind": "pie", "items": [bar]}))                       # unknown kind
        self.assertTrue(check({"kind": "bars", "items": [bar] * 7}))                  # more than 6 items
        self.assertTrue(check({"kind": "bars", "items": []}))                         # nothing to draw
        self.assertTrue(check({"kind": "bars", "items": [{"label": "a", "value": -1}]}))
        self.assertTrue(check({"kind": "bars", "items": [{"label": "a", "value": float("inf")}]}))
        self.assertTrue(check({"kind": "bars", "items": [{"label": "a", "value": True}]}))
        self.assertTrue(check({"kind": "bars", "items": [{"label": 5, "value": 1}]}))
        self.assertTrue(check({"kind": "bars", "items": [{**bar, "tone": "loud"}]}))
        self.assertTrue(check({"kind": "bars", "items": [{**bar, "svg": "<svg onload=x>"}]}))   # no raw markup field
        self.assertTrue(check({"kind": "bars", "items": [bar], "html": "<b>"}))
        self.assertTrue(check("bars"))

    def test_the_contract_documents_every_new_field(self) -> None:
        text = SCHEMA_MD.read_text(encoding="utf-8")
        for field in ("runs", "effect", "advice", "figure", "findings", "kind", "effort", "recommended", "cost", "change", "ref"):
            self.assertRegex(text, rf"\| `[^|]*\b{field}\b[^|]*` \|", field)
        for word in ("lowerBound", "fix-shiploop", "gather-evidence", "`base` is no longer read"):
            self.assertIn(word, text)

    def test_every_option_appears_once_a_shared_one_under_its_first_finding_and_done_ones_apart(self) -> None:
        res = run_logic('cardsFor({findings:%s,options:%s,runKey:"r1",filter:"all"})' % (FINDINGS_JS, OPTIONS_JS))
        shown = [o["id"] for c in res["cards"] for o in c["options"]]
        every = shown + [o["id"] for o in res["loose"]] + [o["id"] for o in res["done"]] + [o["id"] for o in res["elsewhere"]]
        self.assertEqual(sorted(every), sorted(["x1", "x2", "x3", "x4", "y1", "y2", "s1", "d1", "c1", "l1", "l2"]))
        self.assertEqual(len(every), len(set(every)), "each option once")
        by = {c["finding"]["id"]: c for c in res["cards"]}
        self.assertIn("s1", [o["id"] for o in by["f2"]["options"]])   # s1 names f2 first, so f2 hosts it ...
        self.assertEqual([r["id"] for r in by["f1"]["refs"]], ["s1"])  # ... and f1 only refers to it
        self.assertEqual([r["id"] for r in by["f2"]["refs"]], [])
        self.assertEqual([o["id"] for o in res["done"]], ["d1"])
        self.assertEqual(sorted(o["id"] for o in res["loose"]), ["l1", "l2"])

    def test_a_shared_option_is_hosted_by_the_first_finding_in_view_and_referenced_from_the_other(self) -> None:
        res = run_logic('cardsFor({findings:%s,options:[{id:"s1",title:"shared",findings:["f1","f2"]},'
                        '{id:"s2",title:"swapped",findings:["f2","f1"]}],runKey:"r1",filter:"open"})' % FINDINGS_JS)
        by = {c["finding"]["id"]: c for c in res["cards"]}
        self.assertEqual([o["id"] for o in by["f1"]["options"]], ["s1"])
        self.assertEqual([o["id"] for o in by["f2"]["options"]], ["s2"])
        self.assertEqual(by["f2"]["refs"], [{"id": "s1", "title": "shared", "host": "f1"}])
        self.assertEqual(by["f1"]["refs"], [{"id": "s2", "title": "swapped", "host": "f2"}])
        # with f1 filtered out by the expectation filter, f2 hosts the option f1 would have hosted
        only = run_logic('cardsFor({findings:%s,options:[{id:"s1",title:"shared",findings:["f1","f2"]}],runKey:"r1",'
                         'filter:"open",crit:"P2"})' % FINDINGS_JS)
        self.assertEqual([[o["id"] for o in c["options"]] for c in only["cards"]], [["s1"]])
        self.assertEqual(only["cards"][0]["refs"], [])

    def test_options_rank_recommended_then_kind_then_effort_and_done_ones_never_mix_in(self) -> None:
        res = run_logic('cardsFor({findings:%s,options:%s,runKey:"r1",filter:"all"})' % (FINDINGS_JS, OPTIONS_JS))
        f1 = next(c for c in res["cards"] if c["finding"]["id"] == "f1")
        self.assertEqual([o["id"] for o in f1["options"]], ["x4", "x3", "x2", "y2", "y1", "x1"])
        self.assertEqual(run_logic('rankOptions([{id:"a"},{id:"b",kind:"accept"},{id:"c",kind:"fix-shiploop",effort:"L"},'
                                   '{id:"d",kind:"fix-shiploop",effort:"S"},{id:"e",kind:"nonsense"}]).map(function(o){return o.id;})'),
                         ["d", "c", "b", "a", "e"])  # no kind and an unknown kind tie, and keep the order given

    def test_an_open_finding_no_option_names_is_flagged_and_the_filters_choose_the_findings(self) -> None:
        res = run_logic('cardsFor({findings:%s,options:%s,runKey:"r1",filter:"open"})' % (FINDINGS_JS, OPTIONS_JS))
        self.assertEqual([(c["finding"]["id"], c["noOption"]) for c in res["cards"]],
                         [("f1", False), ("f2", False), ("f5", True), ("f6", True), ("f7", True)])
        self.assertEqual([o["id"] for o in res["elsewhere"]], ["c1"])  # its only finding is closed, so not in the open view
        views = run_logic('["open","all","other","general"].map(function(f){return cardsFor({findings:%s,options:[],runKey:"r1",'
                          'filter:f}).cards.map(function(c){return c.finding.id;});})' % FINDINGS_JS)
        self.assertEqual(views, [["f1", "f2", "f5", "f6", "f7"], ["f1", "f2", "f3", "f5", "f6", "f7"], ["f4"], ["f5"]])
        self.assertEqual(run_logic('filterCounts({findings:%s,runKey:"r1"})' % FINDINGS_JS),
                         {"open": 5, "all": 6, "other": 1, "general": 1})
        self.assertEqual(run_logic('cardsFor({findings:%s,options:[{id:"d",status:"done",findings:["f6"]}],runKey:"r1",filter:"open"})'
                                   '.cards.filter(function(c){return c.finding.id==="f6";})[0].noOption' % FINDINGS_JS), False)

    def test_the_where_strip_draws_one_cell_per_visit_outlines_the_phase_and_marks_what_did_not_finish(self) -> None:
        run = luna_run()
        rows = run["stages"]
        self.assertEqual(len(rows), 39)
        svg = run_logic("whereStrip(%s, {phase: 2})" % json.dumps(run))
        self.assertEqual(svg.count("<rect "), 39)
        hits = phases_of(rows).count(2)
        self.assertGreater(hits, 3)
        self.assertEqual(len(re.findall(r'<rect class="ws-cell [^"]*\bhl\b', svg)), hits)
        self.assertIn(f"Plan: {hits} of 39 visits", svg)
        not_done = [r["outcome"] for r in rows if r["outcome"] != "done"]
        self.assertEqual(len(not_done), 2)  # one revise, one blocked
        self.assertEqual(svg.count('class="ws-mark"'), 2)
        self.assertRegex(svg, r'>R</text>')
        self.assertRegex(svg, r'>B</text>')
        self.assertEqual(svg.count("ws-hatch"), 0)
        self.assertTrue(svg.startswith('<svg class="ws" viewBox="0 0 562 64"'))
        last = run_logic("whereStrip(%s, {phase: 6})" % json.dumps(run))  # the run ends there: the label must not run off the strip
        self.assertIn('text-anchor="end"', last)
        view = int(re.search(r'data-view="(\d+)"', last).group(1))  # a narrow screen scrolls the strip to the phase, label included
        self.assertTrue(300 < view < 562, view)
        self.assertEqual(re.search(r'data-view="(\d+)"', run_logic("whereStrip(%s, {phase: 0})" % json.dumps(run))).group(1), "0")
        self.assertNotIn('text-anchor="end"', run_logic("whereStrip(%s, {phase: 0})" % json.dumps(run)))
        for no_strip in ("{}", "{phase: -1}", "{phase: 8}", '{phase: "2"}'):
            self.assertEqual(run_logic("whereStrip(%s, %s)" % (json.dumps(run), no_strip)), "", no_strip)
        self.assertEqual(run_logic("[whereStrip({}, {phase: 1}), whereStrip({stages: []}, {phase: 1}), whereStrip(null, {phase: 1})]"),
                         ["", "", ""])

    def test_the_where_strip_hatches_skipped_and_seeded_visits_and_escapes_what_it_prints(self) -> None:
        rows = [{"stage": "intake", "outcome": "done", "min": 1.5}, {"stage": "<script>x</script>", "outcome": "done", "skipped": True},
                {"stage": "spec", "outcome": "replan", "seeded": True, "min": None}, {"stage": "plan", "outcome": "<b>bad</b>"}]
        svg = run_logic("whereStrip(%s, {phase: 1})" % json.dumps({"stages": rows}))
        self.assertEqual(svg.count("<rect "), 4)
        self.assertEqual(svg.count('<path class="ws-hatch"'), 2)
        self.assertNotIn("<script", svg)
        self.assertNotIn("<b>", svg)
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", svg)
        self.assertIn("o-bbadb", svg)  # an outcome becomes a class name only as letters
        self.assertIn("Specify: 1 of 4 visits", svg)
        self.assertIn("visit 2: ", svg)
        # the unknown stage takes the phase of the visit before it (here intake, then spec is Specify)
        again = run_logic("whereStrip(%s, {phase: 0})" % json.dumps({"stages": rows}))
        self.assertIn("Understand: 2 of 4 visits", again)

    def test_the_stage_to_phase_table_in_the_page_equals_the_exporters(self) -> None:
        page = run_logic("STAGE_FLOW")
        self.assertEqual([[title, list(stages)] for title, stages in page], [[title, list(stages)] for title, stages in export.PHASES])

    def test_a_bars_figure_is_drawn_with_exact_elements_open_ends_for_lower_bounds_and_escaped_labels(self) -> None:
        svg = run_logic('figureSvg({kind:"bars",items:[{label:"expected",value:0,tone:"expected"},{label:"saw",value:13,unit:"refusals",tone:"saw"}]})')
        self.assertEqual((svg.count("<rect "), svg.count("<text "), svg.count("<path ")), (2, 4, 0))
        self.assertIn("t-expected", svg)
        self.assertIn("13 refusals", svg)
        bound = run_logic('figureSvg({kind:"bars",items:[{label:"seen",value:13,lowerBound:true},{label:"limit",value:9.5,unit:"KB",tone:"limit"}]})')
        self.assertEqual((bound.count("<rect "), bound.count('<path class="fg-open"')), (2, 1))
        self.assertIn("&gt;= 13", bound)
        self.assertIn("9.5 KB", bound)
        evil = run_logic('figureSvg({kind:"bars",items:[{label:"<script>alert(1)</script>",value:2,unit:"\\"><img src=x>"}]})')
        self.assertNotIn("<script", evil)
        self.assertNotIn("<img", evil)
        self.assertIn("&lt;script&gt;", evil)
        self.assertEqual(run_logic('[figureSvg({kind:"pie",items:[{label:"a",value:1}]}), figureSvg({kind:"bars",items:[]}), figureSvg(null),'
                                   ' figureSvg({kind:"bars",items:[{label:"a",value:-1},{label:5,value:1}]})]'), ["", "", "", ""])
        many = run_logic('figureSvg({kind:"bars",items:[1,2,3,4,5,6,7,8].map(function(n){return {label:"i"+n,value:n};})})')
        self.assertEqual(many.count("<rect "), 6)
        zero = run_logic('figureSvg({kind:"bars",items:[{label:"none",value:0},{label:"also",value:0}]})')
        self.assertEqual(zero.count("<rect "), 2)  # a measured zero is a stub, not an absent bar and not a NaN width
        self.assertNotIn("NaN", zero)

    def test_the_step_3_card_carries_the_pictures_the_rationale_the_advice_and_its_options(self) -> None:
        out = page_probe('var c=byClass("cards","fcard");var f=c[0];[c.length,f.textContent,byClass(f,"strip")[0].innerHTML.length>0,'
                         'byClass(f,"viz")[0].innerHTML.indexOf("fg-bar")>0,byClass(f,"opt").length,byClass(f,"adv").length,'
                         'byClass(f,"chip").map(function(e){return e.textContent;}),byClass(c[1],"noopt").length]', setup=SAMPLE_SETUP)
        self.assertEqual(out[0], 2)
        scrolled = page_probe('data.obs[0].phase=2;data.runs[0].stages=data.runs[0].stages.concat(new Array(30).fill({stage:"intake",outcome:"done"}),[{stage:"plan",outcome:"done"},{stage:"step-plan",outcome:"done"}]);renderAll();'
                              'var s=byClass("cards","strip")[0];s.scrollLeft=0;go(3);[s.scrollLeft,/data-view="(\\d+)"/.exec(s.innerHTML)[1]]', setup=SAMPLE_SETUP)
        self.assertGreater(scrolled[0], 300)
        self.assertEqual(scrolled[0], int(scrolled[1]))  # the page scrolls a long strip to the phase once its step shows
        for text in ("First finding", "Expected. It holds.", "Saw. It broke.", "Evidence. run/x.md", "Advice. Fix it in the script.",
                     "Fix the flow", "Fix ShipLoop", "recommended", "ask me first", "The script owns the flow", "Specify"):
            self.assertIn(text, out[1])
        self.assertEqual(out[2:5], [True, True, 1])
        self.assertEqual(out[5], 1)
        self.assertEqual(out[6][:3], ["broken", "P1", "defect"])
        self.assertEqual(out[7], 1)  # the second finding has no option: it asks for one

    def test_a_finding_without_a_phase_or_figure_still_shows_its_text_and_ticks_become_a_request_for_options(self) -> None:
        out = page_probe('data.obs[1].phase=undefined;renderAll();var c=byClass("cards","fcard")[1];'
                         '[byClass(c,"viz").length,c.textContent.indexOf("Expected. e2")>0,byClass(c,"noopt")[0].textContent]', setup=SAMPLE_SETUP)
        self.assertEqual(out, [0, True, "No option yet. Ask Claude to propose options."])
        ticked = page_probe('var b=byClass("cards","noopt")[0].children[0];b.checked=true;b.onchange();'
                            '[S().find,textOf("selcount"),REG.steps.children[2].textContent]', setup=SAMPLE_SETUP)
        self.assertEqual(ticked, [{"o2": True}, "You ticked 1 finding to investigate. They become one plan.", "3. Findings and options2 open, 1 ticked"])

    def test_tick_recommended_ticks_the_recommended_option_of_each_open_finding_only(self) -> None:
        out = page_probe('data.acts.push({id:"a3",title:"closed one",findings:["o3"],recommended:true,kind:"accept"});'
                         'data.obs.push({id:"o3",title:"Closed",run:"r1",status:"fixed"});renderAll();'
                         'var tr=byClass("filters","btn")[0];tr.onclick();[S().opts,tr.textContent]', setup=SAMPLE_SETUP)
        self.assertEqual(out, [{"a1": True}, "Tick recommended"])

    def test_filters_show_their_counts_and_a_second_run_sees_only_its_own_findings(self) -> None:
        out = page_probe('var chips=function(){return byClass("filters","chip").map(function(e){return e.textContent+":"+e.getAttribute("aria-pressed");});};'
                         'var a=chips();L.run="r2";renderAll();[a,chips(),byClass("cards","fcard").length]', setup=SAMPLE_SETUP)
        self.assertEqual(out[0], ["Open for this run (2):true", "All for this run (2):false", "Other runs (0):false", "General (0):false"])
        self.assertEqual(out[1], ["Open for this run (0):true", "All for this run (0):false", "Other runs (2):false", "General (0):false"])
        self.assertEqual(out[2], 0)

    def test_ticks_on_an_option_that_is_gone_or_done_are_dropped_with_a_notice_only_with_a_live_database(self) -> None:
        stored = json.dumps({"run": "r1", "sel": {"r1": {"opts": {"a1": True, "gone": True}, "find": {"nope": True, "o2": True}}}})
        offline = page_probe("[S().opts,S().find,textOf('notice')]", setup=SAMPLE_SETUP, stored=stored)
        self.assertEqual(offline, [{"a1": True, "gone": True}, {"nope": True, "o2": True}, ""])  # no database: keep the viewer's ticks
        live = page_probe("live=true;renderAll();[S().opts,S().find,textOf('notice')]", setup=SAMPLE_SETUP, stored=stored)
        self.assertEqual(live[0], {"a1": True})
        self.assertEqual(live[1], {"o2": True})
        self.assertEqual(live[2], "2 ticked items dropped because they are gone or done.")
        done = page_probe('live=true;data.acts[0].status="done";renderAll();[S().opts,textOf("donesum"),REG.donebox.hidden]',
                          setup=SAMPLE_SETUP, stored=stored)
        self.assertEqual(done, [{}, "Already done (1)", False])

    def test_the_flat_observation_and_action_lists_are_replaced_by_the_cards(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8")
        for gone in ("obsfilter", "renderObs", "renderActs", "obsCard", "openCount", "score("):
            self.assertNotIn(gone, html)
        for there in ("cardsFor(", "renderFindings", "whereStrip(", "figureSvg("):
            self.assertIn(there, html)


SPEC_MD = ROOT / "test" / "shiploop_e2e" / "SPEC.md"


class DerivedExpectationChipTests(unittest.TestCase):
    """R6: how an expectation stands for a run is derived from its findings and the run's review, never stored."""

    @staticmethod
    def chip(findings: str, review: str = "null", criterion: str = "P5", run: str = '"r1"') -> str:
        return run_logic('chipFor("%s", %s, %s, %s)' % (criterion, run, findings, review))

    def test_the_worst_effect_among_the_open_findings_wins(self) -> None:
        both = '[{id:"a",criterion:"P5",status:"open",effect:"bent",run:"r1"},{id:"b",criterion:"P5",status:"open",effect:"broken",run:"r1"}]'
        self.assertEqual(self.chip(both), "broken")
        self.assertEqual(self.chip('[{id:"a",criterion:"P5",status:"open",effect:"bent",run:"r1"}]'), "bent")
        self.assertEqual(self.chip(both, run='{key:"r1"}'), "broken")  # a run document works as well as a key

    def test_fixed_accepted_and_re_expected_findings_do_not_count(self) -> None:
        closed = ('[{id:"a",criterion:"P5",status:"fixed",effect:"broken",run:"r1"},{id:"b",criterion:"P5",status:"accepted",effect:"broken",run:"r1"},'
                  '{id:"c",criterion:"P5",status:"reexpected",effect:"bent",run:"r1"}]')
        self.assertEqual(self.chip(closed), "unexamined")
        self.assertEqual(self.chip(closed, review='{basis:{P5:"Examined: the grade is the engine."}}'), "holds")

    def test_holds_needs_a_basis_in_the_review_and_no_open_finding(self) -> None:
        self.assertEqual(self.chip("[]", '{basis:{P5:"Checked the grade by hand."}}'), "holds")
        for review in ("null", "{}", '{basis:{}}', '{basis:{P1:"another criterion"}}', '{basis:{P5:"  "}}', '{basis:{P5:5}}'):
            self.assertEqual(self.chip("[]", review), "unexamined", review)
        # a basis never hides an open finding
        self.assertEqual(self.chip('[{id:"a",criterion:"P5",status:"open",effect:"bent",run:"r1"}]', '{basis:{P5:"fine"}}'), "bent")

    def test_a_findings_runs_list_limits_it_to_those_runs(self) -> None:
        limited = '[{id:"a",criterion:"P5",status:"open",effect:"broken",runs:["r2"]}]'
        self.assertEqual(self.chip(limited), "unexamined")
        self.assertEqual(self.chip(limited, run='"r2"'), "broken")
        self.assertEqual(self.chip('[{id:"a",criterion:"P5",status:"open",effect:"broken",run:"any"}]', run='"r9"'), "broken")
        self.assertEqual(self.chip('[{id:"a",criterion:"P5",status:"open",effect:"broken",run:"r2"}]'), "unexamined")

    def test_five_open_defects_never_read_holds_even_when_no_effect_was_written(self) -> None:
        defects = '[1,2,3,4,5].map(function(n){return {id:"d"+n,criterion:"P5",kind:"defect",status:"open",run:"r1"};})'
        for review in ("null", '{basis:{P5:"looked fine"}}'):
            self.assertEqual(self.chip(defects, review), "unrated")  # the old page showed P5 as holds with 5 open defects
        rated = ('[1,2,3,4,5].map(function(n){return {id:"d"+n,criterion:"P5",kind:"defect",status:"open",run:"r1",effect:n===1?"broken":"bent"};})')
        self.assertEqual(self.chip(rated), "broken")
        self.assertEqual(run_logic('openFindings("P5","r1",%s).length' % defects), 5)
        self.assertEqual(run_logic('openFindings("P1","r1",%s).length' % defects), 0)

    def test_the_defaults_name_the_spec_clauses_and_carry_no_status(self) -> None:
        docs = json.loads((DEFAULTS_DIR / "expectations.json").read_text(encoding="utf-8"))
        spec = {f"S-{n}" for n in re.findall(r"^\*\*S-(\d+) ", SPEC_MD.read_text(encoding="utf-8"), re.M)}
        self.assertGreaterEqual(len(spec), 15)
        criteria = [d for d in docs if d["kind"] == "criterion"]
        self.assertEqual(len(criteria), 11)
        for doc in criteria:
            self.assertIn("clauses", doc, doc["key"])
            self.assertNotIn("status", doc, doc["key"])
            for clause in doc["clauses"]:
                self.assertRegex(clause, r"^S-\d+$")
                self.assertIn(clause, spec, f"{doc['key']} names {clause}, which SPEC.md does not define")
        self.assertEqual({d["key"]: d["clauses"] for d in criteria}["P6"], [])
        self.assertTrue(all(d["clauses"] for d in criteria if d["key"] != "P6"))
        for doc in docs:
            self.assertNotEqual(doc["kind"], "iter")

    def test_the_schema_has_clauses_option_and_reviews_but_no_status_and_no_iter(self) -> None:
        self.assertNotIn("status", export.SCHEMA["expectations"])
        self.assertTrue(export.validate_doc("expectations", {"kind": "iter"}))
        self.assertEqual(export.validate_doc("expectations", {"kind": "criterion", "clauses": ["S-1"],
                         "revs": [{"at": "2026-10-04T00:00:00Z", "from": "a", "to": "b", "reason": "r", "option": "a07"}]}), [])
        self.assertTrue(export.validate_doc("expectations", {"kind": "criterion", "clauses": "S-1"}))
        review = {"summary": ["a", "b"], "basis": {"P1": "reason"}, "reviewedAt": "2026-10-05T00:00:00Z"}
        self.assertEqual(export.validate_doc("reviews", review), [])
        for bad in ({"summary": "one line"}, {"basis": ["P1"]}, {"basis": {"P1": 3}}, {"reviewedAt": "yesterday"}):
            self.assertTrue(export.validate_doc("reviews", bad), bad)
        text = SCHEMA_MD.read_text(encoding="utf-8")
        self.assertIn("**`reviews/<runKey>`**", text)
        self.assertIn("An expectation has **no status**", text)

    def test_step_2_shows_one_row_per_criterion_with_a_derived_chip_clauses_and_a_jump_to_its_findings(self) -> None:
        setup = SAMPLE_SETUP + """
data.obs[1].criterion="P3";data.exp.P1.clauses=["S-1","S-2"];data.exp.P1.status="holds";data.exp.P1.revs=[{at:"2026-10-03T00:00:00Z",from:"old wording",to:"new",reason:"because",option:"a07"}];
data.rev={r1:{summary:["Line one.","Line two."],basis:{P2:"Examined the contracts by hand."},reviewedAt:"2026-10-05T00:00:00Z"}};
renderAll();"""
        out = page_probe('var rows=byClass("groups","card");[rows.length,rows.map(function(r){return byClass(r,"chip")[0].textContent;}),'
                         'rows[0].textContent,rows[1].textContent,textOf("expsum"),REG.steps.children[1].textContent,textOf("arc")]', setup=setup)
        self.assertEqual(out[0], 2)
        self.assertEqual(out[1], ["broken", "holds"])  # P1 has an open broken finding (its stored status "holds" is ignored); P2 has a basis
        for text in ("The script owns the flow", "S-1", "S-2", "revised 1x", "1 open finding", "by option a07", "old wording"):
            self.assertIn(text, out[2])
        self.assertIn("Basis. Examined the contracts by hand.", out[3])
        self.assertIn("no open findings for this run", out[3])
        self.assertEqual(out[4], "This run: 1 broken, 1 hold.")
        self.assertEqual(out[5], "2. Expected versus seen1 broken")
        self.assertIn("Line two.", out[6])
        jump = page_probe('byClass(byClass("groups","card")[0],"btn")[0].onclick();[L.step,L.crit,L.filter,byClass("cards","fcard").map(function(c){return c.id;}),'
                          'byClass("filters","chip").pop().textContent]', setup=SAMPLE_SETUP)
        self.assertEqual(jump, [3, "P1", "open", ["f-o1"], "Expectation P1: clear"])

    def test_a_criterion_nothing_was_said_about_reads_not_examined_and_no_review_means_no_arc(self) -> None:
        out = page_probe('data.obs=[];renderAll();[byClass("groups","card").map(function(r){return byClass(r,"chip")[0].textContent;}),textOf("expsum"),textOf("arc")]',
                         setup=SAMPLE_SETUP)
        self.assertEqual(out, [["not examined", "not examined"], "This run: 2 not examined.", ""])

    def test_the_status_editor_and_the_saw_list_are_gone(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8")
        for gone in ("sawList", "critCard", "pill", "unjudged", "statusSeg"):
            self.assertNotIn(gone, html)


def snapshot_docs(collection: str) -> dict:
    """{id: document data} of one collection of the committed database snapshot."""
    return {i: row["data"] for i, row in json.loads(SNAPSHOT.read_bytes())["docs"][collection].items()}


def prompt_state(**overrides) -> dict:
    """A buildPrompt state: a small run, findings f1 (P1, open) and f2 (P2, open) with options, and the new defaults."""
    cfg = json.loads((DEFAULTS_DIR / "config.json").read_text(encoding="utf-8"))
    state = {
        "run": {"key": "r1", "name": "Luna max, battleship", "release": "skill-craft 1.16.1, ShipLoop 0.48.1", "host": "codex",
                "model": "gpt-6-luna", "startedAt": "2026-10-03T10:00:00Z", "status": "blocked", "evidence": "/runs/r1",
                "stages": [{"stage": "intake", "outcome": "done"}] * 3, "wallMin": 15.2, "improvePasses": 19},
        "runs": [{"key": "r2", "name": "Other", "evidence": "/runs/r2"}],
        "findings": [
            {"id": "f1", "title": "First finding", "criterion": "P1", "status": "open", "effect": "broken", "run": "r1",
             "expected": "It holds.", "observed": "It broke.", "evidence": "run/state.md"},
            {"id": "f2", "title": "Second finding", "criterion": "P2", "status": "open", "run": "r1", "expected": "e2", "observed": "s2"},
            {"id": "f3", "title": "Third finding", "criterion": "P1", "status": "open", "run": "r1", "expected": "e3", "observed": "s3"},
            {"id": "f4", "title": "Elsewhere", "status": "open", "run": "r2", "expected": "e4", "observed": "s4", "evidence": "run/x"}],
        "options": [
            {"id": "a1", "title": "Fix the flow", "kind": "fix-shiploop", "effort": "M", "status": "built", "criterion": "P1", "findings": ["f1", "f3"],
             "goal": "Do: make the script own it. Done when: a test pins it."},
            {"id": "a2", "title": "Fix the grader", "kind": "fix-harness", "effort": "S", "criterion": "P2", "findings": ["f2"], "goal": "Grade the engine."},
            {"id": "a3", "title": "Reword P1", "kind": "change-expectation", "effort": "S", "criterion": "P1", "findings": ["f1"], "goal": "Do: edit it.",
             "change": {"target": "spec", "to": "A new sentence.", "reason": "Luna showed it."}},
            {"id": "a4", "title": "Rerun Luna", "kind": "gather-evidence", "effort": "L", "findings": ["f1"], "cost": "about 10 h of Luna", "goal": "Run it once."},
            {"id": "a5", "title": "Accept the limit", "kind": "accept", "findings": ["f2"], "goal": "Write it down."},
            {"id": "a6", "title": "No kind yet", "goal": "Something."},
            {"id": "a7", "title": "Unticked", "kind": "fix-shiploop", "goal": "Do not mention me."}],
        "expectations": {"P1": {"title": "The script owns the flow", "text": "The model never chooses the next stage.", "clauses": ["S-1", "S-2"]},
                         "P2": {"title": "Loop contracts", "text": "The script writes every loop contract.", "clauses": []},
                         "P9": {"title": "Unrelated expectation", "text": "Not touched.", "clauses": ["S-9"]}},
        "review": {"basis": {"P2": "Examined by hand."}},
        "selected": {"options": {"a1": True}, "find": {}}, "after": "stop", "notes": "",
        "config": {"constraints": cfg["prompt"]["constraints"], "closing": cfg["prompt"]["closing"], "artifactUrl": "https://example.test/page"},
    }
    state.update(overrides)
    return state


def build_prompt(**overrides) -> str:
    return run_logic("buildPrompt(%s)" % json.dumps(prompt_state(**overrides)))


class PromptBuilderTests(unittest.TestCase):
    """R7: one pure builder; what is ticked is all that is printed; expectation changes first; wait by default."""

    ALL = {"a1": True, "a2": True, "a3": True, "a4": True, "a5": True, "a6": True}

    def test_the_prompt_for_the_saved_option_a01_is_small_names_nothing_else_and_has_no_revision_dump(self) -> None:
        options = [{"id": i, **d} for i, d in snapshot_docs("actions").items()]
        findings = [{"id": i, **d} for i, d in snapshot_docs("observations").items()]
        exps = snapshot_docs("expectations")
        revised = {k: d for k, d in exps.items() if d.get("revs")}
        self.assertGreaterEqual(len(revised), 9)  # the saved documents carry ten revisions, which the old builder dumped
        state = prompt_state(options=options, findings=findings, expectations=exps, review=None,
                             selected={"options": {"a01": True}, "find": {}}, run={"key": "luna1", "name": "Luna max, release 1.16.1"})
        state["config"]["artifactUrl"] = snapshot_docs("config")["page"]["artifactUrl"]
        text = run_logic("buildPrompt(%s)" % json.dumps(state))
        a01 = next(o for o in options if o["id"] == "a01")
        self.assertLessEqual(len(text), 3000 + len(a01["goal"]), len(text))
        self.assertIn(a01["title"], text)
        self.assertIn(a01["goal"], text)
        self.assertNotIn("Revised expectations", text)
        for key, doc in revised.items():
            for rev in doc["revs"]:
                self.assertNotIn(rev["reason"], text, key)
                self.assertNotIn(rev["from"], text, key)
        for other in options:
            if other["id"] != "a01":
                self.assertNotIn(other["title"], text, other["id"])
                self.assertNotRegex(text, rf"\b{other['id']}\b")
        for key, doc in exps.items():
            if key != "B1" and doc.get("kind") == "criterion":
                self.assertNotIn(doc["title"], text, key)
        self.assertIn("Every pass earns its time", text)  # a01 serves B1

    def test_nothing_ticked_gives_no_prompt_and_wait_is_the_default_after_line(self) -> None:
        self.assertEqual(build_prompt(selected={"options": {}, "find": {}}), "")
        self.assertEqual(build_prompt(selected={"options": {"a1": False}, "find": {"f2": False}}), "")
        wait, wait2, go = build_prompt(), build_prompt(after="anything"), build_prompt(after="execute")
        self.assertEqual(wait, wait2)
        self.assertIn("Present the plan and wait for my go-ahead.", wait)
        self.assertNotIn("Then execute it.", wait)
        self.assertIn("Then execute it.", go)
        self.assertNotIn("wait for my go-ahead", go)

    def test_the_head_names_the_run_the_repo_the_page_the_evidence_and_the_review_file(self) -> None:
        head = build_prompt().split("\n")[0]
        self.assertEqual(head, "Repair work from the Run Review of Luna max, battleship (skill-craft 1.16.1, ShipLoop 0.48.1; codex gpt-6-luna; "
                               "2026-10-03; blocked). In the skill-craft repository. Page: https://example.test/page. Run evidence: /runs/r1. "
                               "Review file: test/shiploop_e2e/evidence/r1.review.json.")
        text = build_prompt()
        self.assertIn("You ticked 1 option (1 fix ShipLoop). Plan them as one plan: merge overlap, resolve conflicts, order by dependency, "
                      "split into the smallest verifiable increments, mark what can run in parallel.", text)
        bare = build_prompt(run={"key": "k"}, config={"constraints": "", "closing": "", "artifactUrl": ""})
        self.assertTrue(bare.startswith("Repair work from the Run Review of the chosen run. In the skill-craft repository. Review file:"), bare)
        self.assertNotIn("Page:", bare)
        self.assertNotIn("Rules:", bare)

    def test_run_facts_print_measured_values_only_and_name_what_was_not_measured(self) -> None:
        self.assertIn("Run facts: 3 visits, 15.2 min elapsed, 19 Improve passes; refusals not measured, glue not measured.", build_prompt())
        full = build_prompt(run={**prompt_state()["run"], "refusals": 13, "glue": 0})
        self.assertIn("Run facts: 3 visits, 15.2 min elapsed, 19 Improve passes, 13 refusals, 0 glue.", full)
        none = build_prompt(run={"key": "r1", "name": "n"})
        self.assertIn("Run facts: Improve passes not measured, refusals not measured, glue not measured.", none)
        self.assertNotRegex(none, r"\b0 (Improve|refusals|glue)")

    def test_options_are_grouped_by_kind_with_expectation_changes_first(self) -> None:
        text = build_prompt(selected={"options": self.ALL, "find": {}})
        heads = ["CHANGE AN EXPECTATION", "FIX SHIPLOOP", "FIX THE HARNESS", "GATHER EVIDENCE", "ACCEPT AS KNOWN LIMIT", "OTHER OPTIONS"]
        positions = [text.index(h) for h in heads]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("You ticked 6 options (1 change expectation, 1 fix ShipLoop, 1 fix harness, 1 gather evidence, 1 accept as known limit, 1 no kind set).", text)
        self.assertEqual([m.group(1) for m in re.finditer(r"^(\d+)\. ", text, re.M)], ["1", "2", "3", "4", "5", "6"])
        self.assertNotIn("a7", text)
        self.assertNotIn("Unticked", text)

    def test_an_option_line_carries_what_it_resolves_its_expectation_chip_and_clauses_and_its_instruction(self) -> None:
        text = build_prompt()
        self.assertIn("1. a1 Fix the flow [built, effort M]. Resolves: f1, f3. Expectation: P1 The script owns the flow (broken); clauses S-1, S-2.", text)
        self.assertIn("   Do: make the script own it. Done when: a test pins it.", text)
        self.assertNotIn("Do: Do:", text)  # an instruction that already starts "Do:" is not prefixed again
        both = build_prompt(selected={"options": {"a2": True}, "find": {}})
        self.assertIn("   Do: Grade the engine.", both)
        self.assertIn("Expectation: P2 Loop contracts (not rated)", both)  # f2 is open with no effect

    def test_the_ask_me_line_appears_only_for_an_option_with_a_cost(self) -> None:
        text = build_prompt(selected={"options": self.ALL, "find": {}})
        self.assertEqual(text.count("Ask me before starting"), 1)
        self.assertIn("Ask me before starting: costs about 10 h of Luna.", text)
        self.assertNotIn("Ask me before starting", build_prompt())

    def test_a_change_expectation_option_names_the_target_now_was_and_why_and_a_spec_change_names_spec_md_first(self) -> None:
        text = build_prompt(selected={"options": {"a1": True, "a3": True}, "find": {}})
        self.assertIn("1. a3 P1 Reword P1: target spec. Now: A new sentence. Was: The model never chooses the next stage. Why: Luna showed it. Resolves: f1.", text)
        self.assertIn("A spec change means amending test/shiploop_e2e/SPEC.md first, in its own commit, stating why.", text)
        self.assertNotIn("defaults/expectations.json", text.split("FIX SHIPLOOP")[0])
        self.assertLess(text.index("SPEC.md"), text.index("FIX SHIPLOOP"))
        page = build_prompt(options=[{**o, "change": {**o["change"], "target": "page"}} if o["id"] == "a3" else o for o in prompt_state()["options"]],
                            selected={"options": {"a3": True}, "find": {}})
        self.assertIn("A page change means editing skills/shiploop-run-review/defaults/expectations.json (the text, the clauses and a revs entry naming the option)", page)
        self.assertNotIn("A spec change", page)

    def test_investigate_lists_only_ticked_findings_no_option_names_and_each_finding_is_printed_once(self) -> None:
        text = build_prompt(selected={"options": {"a1": True, "a3": True}, "find": {"f3": True, "f4": True}})
        self.assertIn("INVESTIGATE", text)
        self.assertIn("- f4 Elsewhere", text.split("EVIDENCE")[0])  # f3 has an option (a1), so only f4 is asked about
        self.assertNotIn("- f3 Third finding", text.split("EVIDENCE")[0])
        evidence = text.split("\nEVIDENCE\n")[1].split("\n\nRules:")[0]
        ids = re.findall(r"^- (f\d) ", evidence, re.M)
        self.assertEqual(ids, ["f1", "f3", "f4"])  # f1 is linked to two ticked options and appears once
        self.assertIn("- f1 [P1, open] First finding. Expected: It holds. Saw: It broke. (evidence: run/state.md; run: r1 at /runs/r1)", evidence)
        self.assertIn("- f4 [open] Elsewhere. Expected: e4 Saw: s4 (evidence: run/x; run: r2 at /runs/r2)", evidence)  # another run's directory
        self.assertNotIn("Second finding", text)

    def test_rules_notes_and_the_report_back_close_the_prompt_in_that_order(self) -> None:
        text = build_prompt(notes="  Ask me before releasing.  ")
        cfg = prompt_state()["config"]
        self.assertTrue(text.endswith(f"Rules: {cfg['constraints']}\nNotes: Ask me before releasing.\n{cfg['closing']}"), text[-400:])
        self.assertNotIn("Notes:", build_prompt(notes="   "))

    def test_the_default_rules_and_closing_are_run_specific_and_short(self) -> None:
        cfg = json.loads((DEFAULTS_DIR / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(cfg["prompt"]), ["closing", "constraints"])
        rules = cfg["prompt"]["constraints"]
        self.assertTrue(450 <= len(rules) <= 750, len(rules))
        for need in ("script-run test", "S-clauses", "never zero", "known limits", "scripts/release.py", "ask me first", "last three commits"):
            self.assertIn(need, rules)
        closing = cfg["prompt"]["closing"]
        for need in ("done, not done or blocked", "engine or our expectation", "status to done in the review file", "/skill-craft:shiploop-run-review publish"):
            self.assertIn(need, closing)
        for gone in ("Do these in order", "concatPreamble", "synth"):
            self.assertNotIn(gone, json.dumps(cfg))
        self.assertEqual(export.validate_doc("config", cfg["prompt"]), [])
        self.assertEqual(export.extra_fields("config", cfg["prompt"]), [])

    def test_step_4_lists_what_was_ticked_by_kind_flags_the_cost_untick_works_and_the_prompt_is_the_builders(self) -> None:
        setup = SAMPLE_SETUP + """
data.acts.push({id:"a3",title:"Rerun it",kind:"gather-evidence",effort:"L",cost:"10 h",findings:["o1"],goal:"Run it once.",status:"planned"});
S().opts.a1=true;S().opts.a3=true;renderAll();"""
        out = page_probe('[textOf("selcount"),byClass("kindcounts","chip").map(function(c){return c.textContent;}),textOf("ticked"),'
                         'byId("prompt").value===buildPrompt(promptState()),REG.live.hidden,textOf("livesum")]'.replace("byId", "document.getElementById"),
                         setup=setup)
        self.assertEqual(out[0], "You ticked 2 options. They become one plan.")
        self.assertEqual(out[1], ["1 fix ShipLoop", "1 gather evidence"])
        for text in ("FIX SHIPLOOP", "Fix the flow", "GATHER EVIDENCE", "Rerun it", "ask me first", "Costs: 10 h", "Untick"):
            self.assertIn(text, out[2])
        self.assertTrue(out[3])
        self.assertFalse(out[4])
        self.assertIn("Live prompt: 2 options (", out[5])
        gone = page_probe('byClass(byClass("ticked","tick")[0],"btn")[0].onclick();[S().opts,textOf("selcount"),REG.stepnav.children.length,textOf("livesum")]', setup=setup)
        self.assertEqual(gone[0], {"a1": False, "a3": True})
        self.assertEqual(gone[1], "You ticked 1 option. They become one plan.")
        self.assertIn("Live prompt: 1 option (", gone[3])

    def test_the_wait_or_execute_choice_and_the_notes_are_kept_per_run_and_reach_the_prompt(self) -> None:
        out = page_probe('S().opts.a1=true;var go=REG.step-4;document.getElementsByName("after")[1].onchange();document.getElementById("notes").value="Be careful.";'
                         'document.getElementById("notes").oninput();var p=document.getElementById("prompt").value;L.run="r2";renderAll();'
                         '[p.indexOf("Then execute it.")>0,p.indexOf("Notes: Be careful.")>0,S().after,S().notes,document.getElementsByName("after")[0].checked]'
                         .replace("var go=REG.step-4;", ""), setup=SAMPLE_SETUP)
        self.assertEqual(out, [True, True, "stop", "", True])

    def test_nothing_ticked_shows_a_hint_not_a_prompt_and_hides_the_live_box(self) -> None:
        out = page_probe('[document.getElementById("prompt").value,REG.live.hidden,textOf("selcount")]', setup=SAMPLE_SETUP)
        self.assertEqual(out, ["Tick at least one option in step 3.", True, "Nothing ticked yet. Tick options in step 3."])

    def test_every_step_and_the_prompt_work_from_documents_with_every_optional_field_absent(self) -> None:
        bare = """
data.runs=[{key:"r",name:"Bare run",order:1,release:"x",phases:[],time:"",imp:""}];
data.obs=[{id:"o",title:"A bare finding"}];data.acts=[{id:"a",title:"A bare option"}];
Object.keys(loaded).forEach(function(k){loaded[k]=true;});live=true;renderAll();"""
        out = page_probe('S().opts.a=true;S().find.o=true;var seen=[];for(var n=1;n<=4;n++){go(n);renderAll();seen.push(REG["step-"+n].hidden);}'
                         '[seen,textOf("cards").indexOf("A bare finding")>=0,textOf("loose").indexOf("A bare option")>=0,document.getElementById("prompt").value,'
                         'textOf("rundetail").indexOf("undefined")<0,textOf("rundetail").indexOf("NaN")<0]', setup=bare)
        self.assertEqual(out[0], [False, False, False, False])  # each step shows when it is chosen
        self.assertTrue(out[1] and out[2] and out[4] and out[5], out)
        self.assertIn("1. a A bare option [open].", out[3])
        self.assertIn("INVESTIGATE", out[3])
        empty = page_probe("[textOf('cards'),textOf('groups'),document.getElementById('prompt').value]",
                           setup="Object.keys(loaded).forEach(function(k){loaded[k]=true;});renderAll();")
        self.assertEqual(empty[0], "No findings yet. Add the first one below.")
        self.assertIn("No expectations are seeded yet", empty[1])
        self.assertEqual(empty[2], "Tick at least one option in step 3.")

    def test_the_old_prompt_string_building_is_gone(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8")
        for gone in ("Revised expectations", "Backchain ledger,", "Aggregated selection", "inc.rev", "kinds(s)"):
            self.assertNotIn(gone, html)
        self.assertEqual(html.count("function buildPrompt("), 1)
        self.assertEqual(script_blocks()["page"].count("out.push("), 0)  # the page never builds prompt text itself


class DefaultsMatchTheTemplateTests(unittest.TestCase):
    def test_expectation_defaults_have_the_fields_the_template_reads(self) -> None:
        docs = json.loads((DEFAULTS_DIR / "expectations.json").read_text(encoding="utf-8"))
        kinds = {d["kind"] for d in docs}
        self.assertLessEqual(kinds, {"phase", "group", "criterion"})
        self.assertTrue({"phase", "group", "criterion"} <= kinds)
        keys = [d["key"] for d in docs]
        self.assertEqual(len(keys), len(set(keys)))
        groups = {d["key"] for d in docs if d["kind"] == "group"}
        for d in docs:
            self.assertIn("order", d)
            self.assertTrue(d.get("title") and d.get("text"), d["key"])
            if d["kind"] == "criterion":
                self.assertIn(d["group"], groups, f"{d['key']} names a group document")
        orders = sorted(d["order"] for d in docs if d["kind"] == "phase")
        self.assertEqual(orders, list(range(len(orders))), "phase orders are 0..N-1")

    def test_prompt_config_keys_match_the_schema(self) -> None:
        cfg = json.loads((DEFAULTS_DIR / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(cfg["prompt"]), ["closing", "constraints"])
        self.assertIn("title", cfg["page"])



class DbSnapshotTest(unittest.TestCase):
    """The page's database exists only in the artifact until it is committed; the snapshot is that copy."""

    COLLECTIONS = {"observations", "actions", "expectations", "iterations", "backchain", "runs", "config"}

    def setUp(self):
        self.raw = SNAPSHOT.read_bytes()
        self.snapshot = json.loads(self.raw)

    def test_it_is_the_documented_snapshot_with_every_collection_and_a_counts_header_that_matches(self):
        self.assertEqual(self.snapshot["schema"], "run-review-db-snapshot/v1")
        self.assertTrue(self.snapshot["pulledAt"] and self.snapshot["artifact"].startswith("https://"))
        docs = self.snapshot["docs"]
        self.assertEqual(set(docs), self.COLLECTIONS)
        self.assertEqual(self.snapshot["counts"], {name: len(items) for name, items in docs.items()})
        self.assertEqual(sum(self.snapshot["counts"].values()), 109)

    def test_every_document_has_an_id_and_the_database_row_shape(self):
        for collection, items in self.snapshot["docs"].items():
            for doc_id, row in items.items():
                self.assertTrue(isinstance(doc_id, str) and doc_id.strip(), f"{collection}: empty id")
                self.assertEqual(set(row), {"data", "version", "updatedAt"}, f"{collection}/{doc_id}")
                self.assertIsInstance(row["data"], dict, f"{collection}/{doc_id}")

    def test_it_holds_what_exists_nowhere_else(self):
        docs = self.snapshot["docs"]
        self.assertEqual(sorted(docs["iterations"]), ["I0", "I1", "I2", "I2b", "I2c", "I2r", "I3", "I4", "I5", "I6"])
        self.assertEqual({k: len(v["data"]["segments"]) for k, v in docs["backchain"].items()
                          if k.startswith("luna1")}, {"luna1-plan": 11, "luna1-step-plan": 8})
        revised = {k: len(v["data"]["revs"]) for k, v in docs["expectations"].items() if v["data"].get("revs")}
        self.assertEqual(sum(revised.values()), 10)
        self.assertEqual(sorted(revised), ["iter-I1", "iter-I2", "iter-I2b", "iter-I2r", "iter-I3", "iter-I4",
                                           "iter-I5", "iter-I6", "phase-2"])

    def test_the_file_is_compact_and_byte_stable(self):
        self.assertEqual(json.dumps(self.snapshot, separators=(",", ":")).encode("utf-8"), self.raw)


class DefaultsUpgradeTests(unittest.TestCase):
    """The one-time upgrade of the live page's expectations and settings is code (`--defaults --live`), not a hand merge:
    the committed snapshot is the saved live page."""

    def setUp(self):
        self.live = export.read_live(SNAPSHOT)
        self.defaults = {d["key"]: d for d in json.loads((DEFAULTS_DIR / "expectations.json").read_text(encoding="utf-8"))}
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def test_the_owner_revised_phase_2_text_and_its_revision_are_in_the_defaults(self):
        page = self.live["expectations"]["phase-2"]
        self.assertEqual(len(page["revs"]), 1)
        self.assertEqual(self.defaults["phase-2"]["text"], page["text"])
        self.assertEqual(self.defaults["phase-2"]["revs"], page["revs"])

    def test_the_saved_p1_keeps_its_text_and_revs_gains_clauses_and_loses_its_status(self):
        docs, _ = export.upgrade_docs(self.live)
        page, written = self.live["expectations"]["P1"], docs["expectations"]["P1"]
        self.assertEqual(page["status"], "holds")  # the saved document carries the old hand-set status
        self.assertEqual(written["text"], page["text"])
        self.assertEqual(written.get("revs", []), page["revs"])
        self.assertEqual(written["clauses"], ["S-1", "S-2"])
        self.assertNotIn("status", written)
        for key, doc in docs["expectations"].items():
            self.assertNotIn("status", doc, key)
            self.assertEqual(export.validate_doc("expectations", doc), [], key)
            if doc["kind"] == "criterion":
                self.assertIn("clauses", doc, key)
            if self.live["expectations"][key].get("revs"):
                self.assertEqual(doc["revs"], self.live["expectations"][key]["revs"], key)
                self.assertEqual(doc["text"], self.live["expectations"][key]["text"], key)

    def test_config_prompt_comes_from_the_defaults_and_nothing_underived_is_written(self):
        docs, notes = export.upgrade_docs(self.live)
        cfg = json.loads((DEFAULTS_DIR / "config.json").read_text(encoding="utf-8"))
        self.assertIn("concatPreamble", self.live["config"]["prompt"])
        self.assertEqual(docs["config"], {"prompt": cfg["prompt"]})  # config/page holds the page's URL: left alone
        self.assertEqual(set(docs["expectations"]), set(self.defaults))
        self.assertFalse([k for k in docs["expectations"] if k.startswith("iter-")])
        self.assertEqual(set(docs), {"expectations", "config"})
        self.assertEqual(notes, [
            "expectations/group-principles: the page's text, which has no revision of its own, is replaced by the "
            "defaults' text",
            "config/prompt: replaced by the defaults (fields the defaults do not have are dropped)"])
        bare = {"expectations": {}, "config": {}}
        self.assertEqual(export.upgrade_docs(bare)[0]["config"], cfg)  # a page with no settings gets both

    def test_a_page_revision_the_defaults_lack_refuses_the_upgrade_and_names_each_document(self):
        live = copy.deepcopy(self.live)
        live["expectations"]["P3"]["revs"] = [{"at": "2026-10-05T08:00:00Z", "from": "a", "to": "b", "reason": "r"}]
        live["expectations"]["phase-2"]["revs"].append({"at": "2026-10-05T09:00:00Z", "from": "c", "to": "d", "reason": "r"})
        with self.assertRaises(export.ExportError) as raised:
            export.upgrade_docs(live)
        message = str(raised.exception)
        self.assertIn("expectations/P3: the page holds 1 revision the defaults lack (the latest at 2026-10-05T08:00:00Z)",
                      message)
        self.assertIn("expectations/phase-2", message)
        self.assertIn("copy the page's text and revs into defaults/expectations.json first", message)

    def test_the_cli_writes_the_upgrade_and_its_writes_json_and_prints_the_notes(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = export.main(["--defaults", "--live", str(SNAPSHOT), "--out", str(self.tmp / "up")])
        self.assertEqual((code, err.getvalue()), (0, ""))
        self.assertIn("note: expectations/group-principles", out.getvalue())
        writes = json.loads((self.tmp / "up" / "writes.json").read_text())
        self.assertEqual(sorted((w["collection"], w["doc_id"]) for w in writes),
                         sorted([("config", "prompt")] + [("expectations", k) for k in self.defaults]))
        bad = self.tmp / "bad.json"
        bad.write_text(json.dumps({"docs": {"expectations": {"P1": {"text": "a bare document, not a row"}}}}))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(export.main(["--defaults", "--live", str(bad), "--out", str(self.tmp / "bad")]), 2)
        self.assertIn('expectations/P1 has no document under "data"', err.getvalue())
        with contextlib.redirect_stderr(io.StringIO()) as usage, self.assertRaises(SystemExit):
            export.main(["--check", str(SAMPLE_REVIEW), "--live", str(SNAPSHOT)])
        self.assertIn("--live goes with --defaults", usage.getvalue())


EVIDENCE_DIR = ROOT / "test" / "shiploop_e2e" / "evidence"
# The five regraded runs: the committed file (named by the exporter's default key, as before) and the run key the
# page's database already uses, so that uploading a file updates that page document and creates no second one.
EVIDENCE_RUNS = {
    "codex-gpt-6-luna-1.16.1-battleship-20261003.json": "luna1",
    "claude-claude-sonnet-5-5-1.16.1-hello-20261003.json": "hello-1161",
    "claude-claude-sonnet-5-5-1.18.0-hello-20261004.json": "hello-1180",
    "claude-claude-sonnet-5-5-1.19.0-hello-20261004.json": "hello-1190a",
    "claude-claude-sonnet-5-5-1.19.0-hello-20261004-b.json": "hello-1190b",
}
# Each measure is a number, or absent with a reason in runs.unmeasured under this name (the harness's own name for
# the two counters it records per host, the run field's own name for the rest).
MEASURES = {"refusals": "shiploop_failures", "glue": "model_glue", "calls": "calls", "contextPeak": "contextPeak"}


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class CommittedEvidenceTest(unittest.TestCase):
    """The five committed run exports are the v2 contract applied to real runs (regraded, no host started)."""

    @classmethod
    def setUpClass(cls):
        cls.bundles = {name: json.loads((EVIDENCE_DIR / name).read_text()) for name in EVIDENCE_RUNS}
        cls.snapshot_runs = json.loads(SNAPSHOT.read_text())["docs"]["runs"]

    def run_doc(self, key):
        """The run document under the page's key, in the file that carries it."""
        name = next(n for n, k in EVIDENCE_RUNS.items() if k == key)
        run = self.bundles[name]["docs"]["runs"].get(key)
        self.assertIsNotNone(run, f"{name} has no run document under the page's key {key!r}")
        return run

    @property
    def runs(self):
        return {key: self.run_doc(key) for key in EVIDENCE_RUNS.values()}

    def test_every_file_is_the_v2_export_of_one_run_under_the_key_the_page_uses(self):
        for name, key in EVIDENCE_RUNS.items():
            with self.subTest(file=name):
                bundle = self.bundles[name]
                self.assertEqual(bundle["schema"], "run-review-export/v2")
                self.assertEqual(list(bundle["docs"]["runs"]), [key])
                for collection, items in bundle["docs"].items():
                    for doc_id, doc in items.items():
                        self.assertEqual(export.validate_doc(collection, doc), [], f"{collection}/{doc_id}")
                # The page already has a run document under this key; the same run, so an upload updates it.
                page = self.snapshot_runs[key]["data"]
                for field in ("release", "host", "model", "case", "status", "startedAt", "endedAt"):
                    self.assertEqual(self.run_doc(key).get(field), page.get(field), f"{key}.{field}")

    def test_every_visit_names_its_action_and_a_seeded_visit_has_no_minutes(self):
        for key, run in self.runs.items():
            with self.subTest(run=key):
                actions = [row.get("action") for row in run["stages"]]
                self.assertTrue(all(isinstance(a, str) and a for a in actions), "a visit has no action")
                self.assertEqual(len(set(actions)), len(actions), "an action id appears twice")
                for row in run["stages"]:
                    self.assertTrue(row["min"] is None or is_number(row["min"]))
                    if row.get("seeded"):
                        self.assertIsNone(row["min"])

    def test_each_measure_is_a_number_or_absent_with_its_reason_never_both_and_never_zero_by_default(self):
        for key, run in self.runs.items():
            for field, reason in MEASURES.items():
                with self.subTest(run=key, measure=field):
                    reasons = run["unmeasured"]
                    if field in run:
                        self.assertTrue(is_number(run[field]), f"{field} is not a number")
                        self.assertNotIn(reason, reasons, f"{field} is measured and also has a reason")
                    else:
                        self.assertTrue(isinstance(reasons.get(reason), str) and reasons[reason].strip(),
                                        f"{field} is absent with no reason under {reason!r}")

    def test_the_improve_rows_add_up_to_the_run_totals(self):
        for key, run in self.runs.items():
            with self.subTest(run=key):
                rows = [row["improve"] for row in run["stages"] if row.get("improve")]
                self.assertEqual(sum(r["passes"] for r in rows), run["improvePasses"])
                self.assertAlmostEqual(sum(r["min"] for r in rows), run["improveMin"], delta=0.05)

    def test_luna_1_16_1_the_blocked_codex_run_regraded_with_no_host(self):
        run = self.run_doc("luna1")
        self.assertEqual((run["host"], run["status"], len(run["stages"])), ("codex", "blocked", 39))
        # Improve: nine children, 41 passes, bind to receipt (the volatile review-note count said 135.8 min).
        self.assertEqual((run["improvePasses"], sum(1 for r in run["stages"] if r.get("improve"))), (41, 9))
        self.assertAlmostEqual(run["improveMin"], 360.3, delta=0.1)
        # The current harness: 13 refused commands and 20 glue commands (the stored 21 was stale).
        self.assertEqual((run["refusals"], run["glue"], len(run["failures"])), (13, 20, 13))
        # Main-thread calls, heaviest call and compactions read from the Codex rollouts.
        self.assertEqual((run["calls"], run["contextPeak"], run["contextWindow"], run["compactions"]),
                         (2565, 251867, 258400, 34))
        self.assertEqual(sum(1 for row in run["stages"] if row.get("context")), 39)
        self.assertFalse(any(row.get("skipped") or row.get("seeded") for row in run["stages"]))

    def test_the_claude_hello_runs_leave_refusals_glue_and_compactions_out_with_their_reasons(self):
        calls = {"hello-1161": 84, "hello-1180": 94, "hello-1190a": 113, "hello-1190b": 149}
        for key, expected in calls.items():
            with self.subTest(run=key):
                run = self.run_doc(key)
                self.assertEqual(run["host"], "claude")
                for field in ("refusals", "glue", "failures", "compactions"):
                    self.assertNotIn(field, run)
                for reason in ("shiploop_failures", "model_glue", "compactions"):
                    self.assertTrue(run["unmeasured"][reason].strip(), reason)
                self.assertEqual((run["calls"], run["contextWindow"]), (expected, 1_000_000))
                self.assertLess(run["contextPeak"], run["contextWindow"])

    def test_hello_1_19_0_second_run_has_seven_skipped_of_54_visits_and_eleven_improve_children(self):
        run = self.run_doc("hello-1190b")
        self.assertEqual(len(run["stages"]), 54)
        skipped = [row for row in run["stages"] if row.get("skipped")]
        self.assertEqual([row["stage"] for row in skipped],
                         ["test-spec", "baseline", "test-author", "test-red", "test-green", "test-refine", "regression"])
        self.assertTrue(all(row["min"] == 0.0 and not row.get("improve") for row in skipped))
        self.assertEqual((run["improvePasses"], sum(1 for r in run["stages"] if r.get("improve"))), (19, 11))
        self.assertAlmostEqual(run["improveMin"], 3.73, delta=0.1)
        self.assertEqual((run["calls"], run["contextPeak"]), (149, 271220))
        for key in ("hello-1161", "hello-1180", "hello-1190a"):
            self.assertFalse(any(row.get("skipped") for row in self.run_doc(key)["stages"]), key)


class ReviewBundleCheckTests(unittest.TestCase):
    """`export.py --check FILE` and `--docs FILE`: the review rules over a bundle of documents (SKILL.md)."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.sample = json.loads(SAMPLE_REVIEW.read_text(encoding="utf-8"))

    def cli(self, *args) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = export.main([str(a) for a in args])
        return code, out.getvalue(), err.getvalue()

    def bundle_file(self, bundle) -> Path:
        path = self.tmp / f"bundle-{len(list(self.tmp.glob('bundle-*.json')))}.json"
        path.write_text(json.dumps(bundle), encoding="utf-8")
        return path

    def edited(self, change) -> dict:
        """A copy of the passing sample after `change(docs)`."""
        bundle = copy.deepcopy(self.sample)
        change(bundle["docs"])
        return bundle

    def check(self, change) -> tuple[int, str, str]:
        return self.cli("--check", self.bundle_file(self.edited(change)))

    # ---- the sample and the failures

    def test_the_sample_review_passes_with_no_warnings_and_has_the_shape_the_rules_need(self):
        code, out, err = self.cli("--check", SAMPLE_REVIEW)
        self.assertEqual((code, err), (0, ""))
        self.assertIn("check: ok (6 documents, 0 failures, 0 warnings)", out)
        docs = self.sample["docs"]
        self.assertEqual(len(docs["observations"]), 2)
        self.assertEqual(sum("figure" in f for f in docs["observations"].values()), 1)
        kinds = {o["kind"]: o for o in docs["actions"].values()}
        self.assertEqual(sorted(kinds), ["accept", "change-expectation", "fix-shiploop"])
        self.assertEqual(kinds["change-expectation"]["change"]["target"], "spec")

    def test_each_rule_fails_the_check_and_names_the_document(self):
        def two_recommended(docs):
            docs["actions"]["a-accept-paths"]["recommended"] = True

        def goal(docs, text):
            docs["actions"]["a-accept-paths"]["goal"] = text

        cases = {
            "an option linking a finding that is not in the bundle":
                (lambda d: d["actions"]["a-accept-paths"].update(findings=["f-gone"]),
                 ["actions/a-accept-paths", "f-gone"]),
            "a bad enum": (lambda d: d["actions"]["a-callback-alias"].update(kind="fix-everything"),
                           ["actions/a-callback-alias", "fix-everything"]),
            "a bad finding status": (lambda d: d["observations"]["f-context"].update(status="wontfix"),
                                     ["observations/f-context", "wontfix"]),
            "a change-expectation with no change": (lambda d: d["actions"]["a-spec-context"].pop("change"),
                                                    ["actions/a-spec-context", "change-expectation", "change"]),
            "a change on any other kind": (lambda d: d["actions"]["a-accept-paths"].update(
                change={"target": "page", "to": "x", "reason": "y"}),
                                           ["actions/a-accept-paths", "only a change-expectation"]),
            "a change whose target is not page or spec": (lambda d: d["actions"]["a-spec-context"]["change"].update(
                target="code"), ["actions/a-spec-context", "code"]),
            "an instruction that stops before Done when": (
                lambda d: goal(d, "Do: record it. Done when: the entry exists. Test: none."),
                ["actions/a-accept-paths", "Done when"]),
            "an instruction with no Done when": (lambda d: goal(d, "Do: record it. Test: none."),
                                                 ["actions/a-accept-paths", "Done when"]),
            "a Done when with no condition": (lambda d: goal(d, "Do: record it. Done when:"),
                                              ["actions/a-accept-paths", "Done when"]),
            "an option with no instruction": (lambda d: d["actions"]["a-accept-paths"].pop("goal"),
                                              ["actions/a-accept-paths", "Done when"]),
            "two recommended options on one finding": (two_recommended, ["observations/f-refusals", "2 recommended",
                                                                         "a-accept-paths", "a-callback-alias"]),
            "a clause id the defaults do not use": (
                lambda d: d.update(expectations={"P3": {"kind": "criterion", "clauses": ["S-2", "S-99"]}}),
                ["expectations/P3", "S-99", "defaults/expectations.json"]),
            "a clause id that is not S-n": (
                lambda d: d.update(expectations={"P3": {"kind": "criterion", "clauses": ["S3"]}}),
                ["expectations/P3", "S3", "S-n"]),
        }
        for name, (change, needles) in cases.items():
            with self.subTest(name):
                code, out, err = self.check(change)
                self.assertEqual(code, 2, err)
                for needle in needles:
                    self.assertIn(needle, err)
                self.assertNotIn("check: ok", out)
                self.assertIn("check: FAILED", err)

    def test_a_bundle_in_another_schema_or_shape_fails_and_an_unreadable_file_is_an_error(self):
        for name, bundle in {"v1": {"schema": "run-review-export/v1", "docs": {}}, "no docs": {"schema": export.SCHEMA_ID},
                             "not an object": [1], "a collection that is not a map": {
                                 "schema": export.SCHEMA_ID, "docs": {"actions": [1]}}}.items():
            with self.subTest(name):
                code, _, err = self.cli("--check", self.bundle_file(bundle))
                self.assertEqual(code, 2)
                self.assertIn("fail: bundle:", err)
        code, _, err = self.cli("--check", self.tmp / "missing.json")
        self.assertEqual(code, 2)
        self.assertIn("cannot read the review bundle", err)
        broken = self.tmp / "broken.json"
        broken.write_text("{not json")
        self.assertEqual(self.cli("--check", broken)[0], 2)

    def test_every_failure_is_listed_one_per_line_and_none_is_dropped(self):
        def three(docs):
            docs["actions"]["a-callback-alias"]["kind"] = "nonsense"
            docs["actions"]["a-accept-paths"]["findings"] = ["f-gone"]
            docs["actions"]["a-spec-context"].pop("change")

        code, _, err = self.check(three)
        lines = [line for line in err.splitlines() if line.startswith("fail: ")]
        self.assertEqual(code, 2)
        self.assertEqual(len(lines), 3, err)
        self.assertEqual(sorted(line.split(":")[1].strip() for line in lines),
                         ["actions/a-accept-paths", "actions/a-callback-alias", "actions/a-spec-context"])
        self.assertIn("check: FAILED (3 failures, 0 warnings)", err)

    def test_a_clause_id_the_defaults_use_passes(self):
        clauses = sorted({c for e in json.loads((DEFAULTS_DIR / "expectations.json").read_text())
                          for c in e.get("clauses", [])})
        self.assertIn("S-2", clauses)
        code, out, err = self.check(lambda d: d.update(expectations={"P3": {"kind": "criterion", "clauses": clauses}}))
        self.assertEqual((code, err), (0, ""), err)

    def test_a_criterion_or_basis_key_the_defaults_lack_fails_and_any_key_they_have_passes(self):
        def typo(docs):
            docs["observations"]["f-refusals"]["criterion"] = "P33"
            docs["reviews"]["luna1"]["basis"]["B9"] = "A basis for a criterion that does not exist."

        code, out, err = self.check(typo)
        self.assertEqual(code, 2, err)
        self.assertIn("fail: observations/f-refusals: criterion 'P33' is not a key of defaults/expectations.json", err)
        self.assertIn("fail: reviews/luna1: basis names 'B9', which is not a key of defaults/expectations.json", err)
        self.assertIn("check: FAILED (2 failures", err)

        def known(docs):  # a phase key is an expectation key too (the saved finding o35 uses phase-6); none is fine
            docs["observations"]["f-refusals"]["criterion"] = "phase-6"
            docs["observations"]["f-context"].pop("criterion")
            docs["reviews"]["luna1"]["basis"] = {"B5": "Examined.", "phase-2": "Examined."}

        code, out, err = self.check(known)
        self.assertEqual((code, err), (0, ""), err)

    def test_a_done_when_clause_may_follow_other_parts_and_a_condition_may_mention_a_test(self):
        for text in ("Do: x. Files and symbols: y. Test: z. Done when: z passes.",
                     "Do: x. Done when the test passes", "Do: x.\nDone when: both tests pass and the page reads 'ok'."):
            with self.subTest(text):
                code, _, err = self.check(lambda d: d["actions"]["a-accept-paths"].update(goal=text))
                self.assertEqual((code, err), (0, ""), err)

    # ---- the warnings

    def test_an_open_finding_no_option_names_warns_and_does_not_fail(self):
        def orphan(docs):
            del docs["actions"]["a-spec-context"]

        code, out, err = self.check(orphan)
        self.assertEqual((code, err), (0, ""))
        self.assertIn("warning: observations/f-context: open finding with no option", out)
        self.assertIn("no option yet", out)
        self.assertIn("1 warning)", out)

    def test_evidence_with_no_path_or_commit_token_warns_and_does_not_fail(self):
        code, out, err = self.check(lambda d: d["observations"]["f-refusals"].update(
            evidence="luna1 status: ShipLoop failures 9"))
        self.assertEqual((code, err), (0, ""))
        self.assertIn("warning: observations/f-refusals: evidence has no path or commit token", out)
        self.assertIn("ShipLoop failures 9", out)

    def test_an_open_finding_with_no_evidence_warns_the_same_way_and_a_closed_one_does_not(self):
        code, out, _ = self.check(lambda d: d["observations"]["f-refusals"].pop("evidence"))
        self.assertEqual(code, 0)
        self.assertIn("observations/f-refusals: evidence has no path or commit token (none given)", out)

        def closed(docs):
            docs["observations"]["f-refusals"].update(status="fixed")
            for key in ("evidence", "effect"):
                docs["observations"]["f-refusals"].pop(key)
            docs["actions"]["a-callback-alias"]["findings"] = ["f-context"]
            docs["actions"]["a-accept-paths"]["findings"] = ["f-context"]
            docs["actions"]["a-accept-paths"]["recommended"] = False

        code, out, err = self.check(closed)
        self.assertEqual((code, err), (0, ""), err)
        self.assertNotIn("warning: observations/f-refusals", out)

    def test_an_open_finding_with_no_effect_warns_that_the_page_shows_it_as_not_rated(self):
        code, out, err = self.check(lambda d: d["observations"]["f-context"].pop("effect"))
        self.assertEqual((code, err), (0, ""))
        self.assertIn("warning: observations/f-context: open finding with no effect", out)
        self.assertIn("not rated", out)

    def test_a_finding_with_no_status_reads_as_open_for_the_warnings(self):
        def unset(docs):
            for key in ("status", "effect"):
                docs["observations"]["f-context"].pop(key)

        code, out, _ = self.check(unset)
        self.assertEqual(code, 0)
        self.assertIn("observations/f-context: open finding with no effect", out)

    def test_all_three_warnings_together_exit_zero_and_are_counted(self):
        def all_three(docs):
            del docs["actions"]["a-spec-context"]
            docs["observations"]["f-refusals"]["evidence"] = "see the journal"
            docs["observations"]["f-context"].pop("effect")

        code, out, err = self.check(all_three)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(sorted(line.split(":")[1].strip() for line in out.splitlines() if line.startswith("warning: ")),
                         ["observations/f-context", "observations/f-context", "observations/f-refusals"])
        self.assertIn("0 failures, 3 warnings", out)

    def test_the_evidence_token_is_a_path_a_file_name_or_a_commit_and_not_prose(self):
        for text in ("release 1.16.1, shiploop_loop_contract.py", "run/improve/terminal.json", "v1161-luna: run/state.md",
                     "/Users/me/e2e-runs/1", "commit 1ff8c841", "skills/shiploop-run-review", "~/notes"):
            with self.subTest(text):
                self.assertTrue(export.EVIDENCE_TOKEN.search(text), text)
        for text in ("luna1 status: ShipLoop failures 9", "he said and/or that", "the journal", "defaced effaced",
                     "1158500 minutes", "yes/no", "n/a"):
            with self.subTest(text):
                self.assertIsNone(export.EVIDENCE_TOKEN.search(text), text)

    def test_the_check_reads_the_saved_page_data_as_the_defects_the_redesign_listed(self):
        """The R2 snapshot is what unchecked authoring produced; the check must find what the plan found in it."""
        saved = json.loads(SNAPSHOT.read_text())["docs"]
        bundle = {"schema": export.SCHEMA_ID, "docs": {c: {i: row["data"] for i, row in saved[c].items()}
                                                       for c in ("observations", "actions")}}
        failures, warnings = export.check_bundle(bundle)
        # all 16 saved instructions are status narratives with no Done when; three statuses are the old vocabulary
        self.assertEqual(sorted(f.split(":")[0] for f in failures if "Done when" in f), sorted(
            f"actions/{i}" for i in saved["actions"]))
        self.assertEqual(sorted(f.split(":")[0] for f in failures if "actions.status" in f),
                         ["actions/a13", "actions/a14", "actions/a16"])
        # 5 of 39 evidence strings name no path or commit; 29 findings are open, and none has an option or an effect
        self.assertEqual(sorted(w.split(":")[0].split("/")[1] for w in warnings if "evidence" in w),
                         ["o05", "o06", "o12", "o17", "o39"])
        self.assertEqual(sum("open finding with no option" in w for w in warnings), 29)
        self.assertEqual(sum("open finding with no effect" in w for w in warnings), 29)

    # ---- the order and --docs

    def test_collection_order_lists_every_schema_collection_once_and_the_review_sits_before_its_findings(self):
        order = list(export.COLLECTION_ORDER)
        self.assertEqual(sorted(order), sorted(export.SCHEMA))
        self.assertNotIn("iterations", order)
        self.assertLess(order.index("config"), order.index("reviews"))
        self.assertLess(order.index("reviews"), order.index("observations"))
        self.assertLess(order.index("observations"), order.index("actions"))

    def test_docs_writes_every_document_and_writes_json_in_collection_order_and_each_file_validates(self):
        target = self.tmp / "docs-out"
        code, out, err = self.cli("--docs", SAMPLE_REVIEW, "--out", target)
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(out.strip().endswith(str(target.resolve())), out)
        writes = json.loads((target / "writes.json").read_text())
        self.assertEqual([(w["collection"], w["doc_id"]) for w in writes],
                         [("reviews", "luna1"), ("observations", "f-context"), ("observations", "f-refusals"),
                          ("actions", "a-accept-paths"), ("actions", "a-callback-alias"), ("actions", "a-spec-context")])
        for write in writes:
            self.assertEqual((write["op"], "if_version" in write), ("set", False))
            path = Path(write["file_path"])
            self.assertTrue(path.is_absolute() and path.is_file())
            written = json.loads(path.read_text())
            self.assertEqual(written, self.sample["docs"][write["collection"]][write["doc_id"]])
            self.assertEqual(export.validate_doc(write["collection"], written), [])
        self.assertFalse((target / "review-export.json").exists(), "the review file is the record, not a second copy")
        self.assertFalse((target / "facts.md").exists())

    def test_docs_refuses_a_bundle_that_fails_the_check_and_writes_nothing(self):
        target = self.tmp / "refused"
        code, _, err = self.cli("--docs", self.bundle_file(self.edited(
            lambda d: d["actions"]["a-accept-paths"].update(findings=["f-gone"]))), "--out", target)
        self.assertEqual(code, 2)
        self.assertIn("f-gone", err)
        self.assertFalse(target.exists())

    def test_docs_without_out_writes_to_a_new_temporary_directory_and_prints_it(self):
        with mock.patch.object(tempfile, "tempdir", str(self.tmp)):
            first = self.cli("--docs", SAMPLE_REVIEW)
            second = self.cli("--docs", SAMPLE_REVIEW)
        paths = [Path(run[1].strip().splitlines()[-1]) for run in (first, second)]
        self.assertNotEqual(paths[0], paths[1])
        for path in paths:
            self.assertEqual(path.parent.resolve(), self.tmp.resolve())
            self.assertTrue(path.name.startswith("run-review-docs-") and (path / "writes.json").is_file())

    def test_exactly_one_mode_is_given(self):
        for args in ([], ["--check", str(SAMPLE_REVIEW), "--defaults"], ["--check", str(SAMPLE_REVIEW), "--docs", str(SAMPLE_REVIEW)],
                     ["--docs", str(SAMPLE_REVIEW), str(self.tmp)]):
            err = io.StringIO()
            with self.subTest(args=args), contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as raised:
                export.main(args)
            self.assertEqual(raised.exception.code, 2)
            self.assertIn("give one of RUN_DIR, --defaults, --check FILE or --docs FILE", err.getvalue())


LUNA_REVIEW = EVIDENCE_DIR / "luna1.review.json"
CRITERIA = ("P1", "P2", "P3", "P4", "P5", "P6", "B1", "B2", "B3", "B4", "B5")


class LunaReviewTests(unittest.TestCase):
    """The committed review of the Luna 1.16.1 run (R9): it passes the check, keeps every saved finding and option,
    takes its figures from the committed evidence, and its prompt stays within the size contract."""

    @classmethod
    def setUpClass(cls):
        cls.docs = json.loads(LUNA_REVIEW.read_text(encoding="utf-8"))["docs"]
        cls.saved = {c: snapshot_docs(c) for c in ("observations", "actions", "runs")}
        cls.luna = json.loads(LUNA_EVIDENCE.read_text())["docs"]["runs"]["luna1"]

    def test_it_passes_the_check_and_its_warnings_are_the_findings_left_on_purpose(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = export.main(["--check", str(LUNA_REVIEW)])
        self.assertEqual((code, err.getvalue()), (0, ""))
        warned = sorted(line.split(":")[1].strip().split("/")[1] + ":" + ("option" if "no option" in line else "effect")
                        for line in out.getvalue().splitlines() if line.startswith("warning: "))
        # o16 and o34 have neither (unknown cause; not this run), o17 is the owner's choice, o23 and o30 wait for one
        self.assertEqual(warned, ["o16:effect", "o16:option", "o17:effect", "o23:option", "o30:option", "o34:effect",
                                  "o34:option"])

    def test_every_saved_document_is_kept_and_every_option_is_rewritten_normalised_and_linked(self):
        findings, options = self.docs["observations"], self.docs["actions"]
        self.assertLessEqual(set(self.saved["observations"]), set(findings))
        self.assertLessEqual(set(self.saved["actions"]), set(options))
        for fid, saved in self.saved["observations"].items():
            for field in ("title", "expected", "kind", "criterion", "createdAt"):
                self.assertEqual(findings[fid].get(field), saved.get(field), f"{fid}.{field}")
            if fid != "o37":  # o37 is restated with model calls; every other change is appended, never a deletion
                self.assertTrue(findings[fid]["observed"].startswith(saved["observed"]), fid)
            if saved.get("status") in ("fixed", "accepted"):
                self.assertNotIn("advice", findings[fid], fid)
        for aid, option in options.items():
            self.assertTrue(option.get("kind") and option.get("effort") and option.get("findings"), aid)
            self.assertNotIn("base", option)
        self.assertEqual({a: options[a]["status"] for a in ("a13", "a14", "a16")},
                         {"a13": "built", "a14": "done", "a16": "planned"})  # building, analysed and waiting before
        self.assertIn("1.19.0", options["a06"]["ref"])
        self.assertEqual((options["a11"]["status"], options["a08"].get("recommended", False)), ("done", False))
        page_runs = set(self.saved["runs"])
        for fid, saved in self.saved["observations"].items():
            if saved.get("run") in ("any", "sonnet"):
                self.assertTrue(findings[fid].get("runs"), fid)
                self.assertLessEqual(set(findings[fid]["runs"]), page_runs, fid)

    def test_every_open_finding_with_a_live_option_has_its_effect_and_advice(self):
        findings, options = self.docs["observations"], self.docs["actions"]
        linked = {f for o in options.values() if o["status"] != "done" for f in o["findings"]}
        for fid, finding in findings.items():
            if finding.get("status", "open") == "open" and fid in linked:
                self.assertIn("advice", finding, fid)
                if fid != "o17":  # a choice for the owner hits no expectation (references/advice.md, "Effect")
                    self.assertIn(finding.get("effect"), ("broken", "bent"), fid)

    def test_the_figures_take_their_numbers_from_the_committed_evidence(self):
        def bars(fid):
            return {item["label"]: item for item in self.docs["observations"][fid]["figure"]["items"]}

        luna, failures = self.luna, self.luna["failures"]
        paths = sum("unrecognized arguments" in f["line"] or "no ShipLoop run directory" in f["line"] for f in failures)
        tails = sum(f["line"].startswith("Read the current packet with next") for f in failures)
        self.assertEqual((len(failures), paths, tails), (13, 4, 8))
        self.assertEqual({k: v["value"] for k, v in bars("o43").items() if k in ("Expected refusals", "Refused commands",
                                                                                "Run-path copy errors")},
                         {"Expected refusals": 0, "Refused commands": luna["refusals"], "Run-path copy errors": paths})
        self.assertEqual(sum(v["value"] for k, v in bars("o43").items() if k not in ("Expected refusals",
                                                                                    "Refused commands")), 13)
        self.assertEqual([bars("o40")[k]["value"] for k in ("Refusals recorded", "Line names the cause",
                                                            "Generic tail line", "AssertionError line")],
                         [len(failures), paths, tails, sum(f["line"] == "AssertionError" for f in failures)])
        page = sum(child["seconds"] for child in self.saved["runs"]["luna1"]["improve"]) / 60
        self.assertEqual([bars("o42")[k]["value"] for k in ("Page showed", "Bind to receipt", "Run elapsed")],
                         [round(page, 1), round(luna["improveMin"], 1), luna["wallMin"]])
        runs = [json.loads((EVIDENCE_DIR / n).read_text())["docs"]["runs"][k] for n, k in EVIDENCE_RUNS.items()]
        hello = max(r["contextPeak"] / r["contextWindow"] for r in runs if r["key"].startswith("hello"))
        self.assertEqual([bars("o06")[k]["value"] for k in ("Luna peak, % window", "Sonnet hello max, %")],
                         [round(100 * luna["contextPeak"] / luna["contextWindow"], 1), round(100 * hello, 1)])
        turns = bars("o41")["Turns, resume only"]
        self.assertEqual((bars("o41")["Main-thread calls"]["value"], turns["value"], turns.get("lowerBound")),
                         (luna["calls"], 2189, True))
        loops = json.loads(LUNA_EVIDENCE.read_text())["docs"]["backchain"]
        minutes = {(loop, s["pass"]): s["min"] for loop, d in loops.items() for s in d["segments"] if "pass" in s}
        self.assertEqual([bars("o12")[k]["value"] for k in ("Plan passes 1-5", "Plan clean passes 6-7",
                                                            "Step-plan passes 1-2", "Step-plan clean 3-4")],
                         [sum(minutes["luna1-plan", n] for n in range(1, 6)), minutes["luna1-plan", 6] + minutes["luna1-plan", 7],
                          minutes["luna1-step-plan", 1] + minutes["luna1-step-plan", 2],
                          minutes["luna1-step-plan", 3] + minutes["luna1-step-plan", 4]])
        for fid, finding in self.docs["observations"].items():
            for item in finding.get("figure", {}).get("items", []):
                self.assertLessEqual(len(item["label"]), 22, f"{fid}: {item['label']}")
                self.assertEqual(item.get("lowerBound", False), item["label"] == "Turns, resume only", fid)

    def test_its_chips_for_the_luna_run_and_a_basis_for_every_criterion(self):
        findings = [{"id": i, **d} for i, d in self.docs["observations"].items()]
        review = self.docs["reviews"]["luna1"]
        self.assertEqual(sorted(review["basis"]), sorted(CRITERIA))
        self.assertTrue(3 <= len(review["summary"]) <= 6)
        chips = run_logic("(function(F,R){return %s.map(function(k){return chipFor(k,'luna1',F,R);});})(%s,%s)"
                          % (json.dumps(CRITERIA), json.dumps(findings), json.dumps(review)))
        self.assertEqual(dict(zip(CRITERIA, chips)), {
            "P1": "bent", "P2": "bent", "P3": "broken", "P4": "holds", "P5": "broken", "P6": "broken",
            "B1": "bent", "B2": "broken", "B3": "broken", "B4": "bent", "B5": "unrated"})

    def test_a_prompt_for_three_ticked_options_adds_at_most_3000_characters_to_what_they_and_their_findings_say(self):
        """The size contract: the builder's own text (head, counts, option lines, rules, report-back) stays within about
        3,000 characters; the rest is the ticked options' instructions and changes and their findings, each once."""
        findings = [{"id": i, **d} for i, d in self.docs["observations"].items()]
        options = [{"id": i, **d} for i, d in self.docs["actions"].items()]
        cfg = json.loads((DEFAULTS_DIR / "config.json").read_text(encoding="utf-8"))
        exps = {d["key"]: d for d in json.loads((DEFAULTS_DIR / "expectations.json").read_text(encoding="utf-8"))}

        def state(ticked):
            return {"run": self.luna, "runs": [self.luna], "findings": findings, "options": options,
                    "expectations": exps, "review": self.docs["reviews"]["luna1"], "after": "wait", "notes": "",
                    "selected": {"options": {i: True for i in ticked}, "find": {}},
                    "config": {**cfg["prompt"], "artifactUrl": snapshot_docs("config")["page"]["artifactUrl"]}}

        def own_words(ticked):
            chosen = [o for o in options if o["id"] in ticked]
            ids = {f for o in chosen for f in o["findings"]}
            said = sum(len(o["goal"]) + len(o["title"]) + len(o.get("cost", ""))
                       + sum(len(v) for v in (o.get("change") or {}).values()) for o in chosen)
            return said + sum(len(f["title"]) + len(f["expected"]) + len(f["observed"]) + len(f.get("evidence", ""))
                              for f in findings if f["id"] in ids)

        live = [o["id"] for o in options if o["status"] != "done"]
        ticks = [["a19", "a13", "a21"]] + [[i] for i in live]
        texts = run_logic("(function(S){return %s.map(function(t){var s=JSON.parse(JSON.stringify(S));"
                          "t.forEach(function(i){s.selected.options[i]=true;});return buildPrompt(s);});})(%s)"
                          % (json.dumps(ticks), json.dumps(state([]))))
        for ticked, text in zip(ticks, texts):
            with self.subTest(ticked=ticked):
                self.assertLessEqual(len(text) - own_words(ticked), 3000, len(text))
                for other in options:
                    if other["id"] not in ticked:
                        self.assertNotRegex(text, rf"\b{other['id']}\b")
        three = texts[0]
        self.assertEqual([three.count(f"- {f} [") for f in ("o35", "o40")], [1, 1])  # o35 is shared, printed once
        self.assertLess(three.index("CHANGE AN EXPECTATION"), three.index("FIX SHIPLOOP"))
        self.assertIn("Ask me before starting: costs a live run", three)
        for key in CRITERIA:
            if key != "P5":
                self.assertNotIn(exps[key]["title"], three, key)


class ReviewSkillTextTests(unittest.TestCase):
    """SKILL.md and references/advice.md carry the procedure the exporter's rules enforce."""

    @classmethod
    def setUpClass(cls):
        # Whitespace is collapsed so a phrase the file wraps across two lines still counts.
        cls.skill = " ".join(SKILL_MD.read_text(encoding="utf-8").split())
        cls.advice = " ".join(ADVICE_MD.read_text(encoding="utf-8").split()) if ADVICE_MD.is_file() else ""
        cls.advice_raw = ADVICE_MD.read_text(encoding="utf-8") if ADVICE_MD.is_file() else ""

    def test_skill_md_links_the_advice_rubric_and_the_contract_and_both_files_exist(self):
        self.assertIn("(references/advice.md)", self.skill)
        self.assertIn("(SCHEMA.md)", self.skill)
        self.assertTrue(ADVICE_MD.is_file())

    def test_skill_md_gives_the_four_invocations_and_the_installed_package_binding(self):
        for line in ("/skill-craft:shiploop-run-review advise RUN_DIR_OR_KEY", "/skill-craft:shiploop-run-review export RUN_DIR",
                     "/skill-craft:shiploop-run-review publish", "/skill-craft:shiploop-run-review check FILE"):
            self.assertIn(line, self.skill)
        self.assertIn("SKILL_ROOT", self.skill)
        self.assertRegex(self.skill, r'python3 -B "\$SKILL_ROOT/scripts/export\.py" --check')
        self.assertRegex(self.skill, r"selected, loaded `?SKILL\.md")

    def test_skill_md_states_the_split_between_numbers_and_advice_and_the_four_steps(self):
        for text in ("scripts own the numbers", "Claude owns the advice", "unmeasured is never zero",
                     "What happened", "Expected versus seen", "Findings and options", "Your plan"):
            self.assertIn(text.lower(), self.skill.lower(), text)

    def test_skill_md_names_every_check_rule_and_every_warning(self):
        for rule in ("schema and enums", "findings exist", "change-expectation", "Done when", "at most one recommended",
                     "S-n", "defaults/expectations.json", "exit 2", "no option yet", "path or commit token", "not rated"):
            self.assertIn(rule, self.skill, rule)

    def test_skill_md_publish_procedure_keeps_every_guard(self):
        for text in ("ShipLoop Run Review", "capabilities", "artifact-capabilities", "if_version", "never overwrite",
                     "luna1-plan", "luna1-step-plan", "draft", "never create a second page", "ArtifactData", "batch",
                     "writes.json", "not updated", "never republish"):
            self.assertIn(text.lower(), self.skill.lower(), text)
        self.assertIn("capabilities: {db: {}}", self.skill)

    def test_skill_md_has_the_script_merge_the_defaults_over_the_page_and_names_the_criterion_key_rule(self):
        self.assertIn("export.py --defaults --live FILE --out DIR", self.skill)
        self.assertIn("The script merges, never you", self.skill)
        self.assertIn("a finding's `criterion` and each key of a review's `basis` is a key of "
                      "`defaults/expectations.json`", self.skill)

    def test_skill_md_has_none_of_the_stale_phrases(self):
        for stale in ("iterations with editable expectations", "iteration card", "result of the iteration",
                      "create-only", "apply mode", "apply on the page", "include toggles", "expectation editor",
                      "unexpected", "process diagram", "synth", "concatenate", "Add the judgment", "README"):
            self.assertNotIn(stale.lower(), self.skill.lower(), stale)

    def test_advice_md_holds_the_form_the_honesty_rules_and_the_triage_words(self):
        self.assertTrue(self.advice, "references/advice.md is missing")
        for text in ("Do: ... Files and symbols: ... Test: ... Done when: ...", "Inferred:", "unmeasured", "not-measured",
                     "at most one recommended", "for, against and verdict", "git log", "not rated", "lowerBound",
                     "22 characters", "6 items", "raw SVG or HTML", "phase", "mismatch.md", "facts.md", "SPEC.md"):
            self.assertIn(text.lower(), self.advice.lower(), text)
        for triage in ("product", "environment", "expectation", "known limit", "owner", "rerun-first"):
            self.assertRegex(self.advice_raw, rf"(?m)^\|\s*{triage}\s*\|", triage)
        schema_kinds = export.SCHEMA["actions"]["kind"][0][1]
        for kind in schema_kinds:
            self.assertIn(kind, self.advice, kind)
        for effect in export.SCHEMA["observations"]["effect"][0][1]:
            self.assertIn(effect, self.advice, effect)

    def test_the_worked_example_in_advice_md_passes_the_check_and_uses_the_committed_luna_numbers(self):
        _, _, tail = self.advice_raw.partition("## Worked example")
        block = re.search(r"```json\n(.*?)\n```", tail, re.S)
        self.assertIsNotNone(block, "no ```json block after '## Worked example'")
        example = json.loads(block.group(1))
        failures, warnings = export.check_bundle(example)
        self.assertEqual((failures, warnings), ([], []))
        (finding,) = example["docs"]["observations"].values()
        bars = {item["label"]: item["value"] for item in finding["figure"]["items"]}
        luna = json.loads(LUNA_EVIDENCE.read_text())["docs"]["runs"]["luna1"]
        self.assertEqual(luna["refusals"], 13)
        self.assertEqual(bars["Refused commands"], luna["refusals"])
        self.assertEqual(bars["Expected refusals"], 0)
        self.assertEqual(sum("unrecognized arguments" in f["line"] or "no ShipLoop run directory at" in f["line"] and "/ v1161" in f["line"]
                             for f in luna["failures"]), bars["Broken paths"])
        self.assertGreaterEqual(len(example["docs"]["actions"]), 2)
        self.assertEqual(sum(a.get("recommended") is True for a in example["docs"]["actions"].values()), 1)


class SequenceModelTests(unittest.TestCase):
    """R14: the sequence picture as pure data (sequenceModel, columnDetail, visitTable), over the five committed v2 runs
    and a few fixtures. What the page draws is decided here, so an unmeasured visit or counter cannot read as zero."""

    _cache: dict = {}

    def load(self):
        """The five runs and sequenceModel of each, from one node run shared by the tests (an exception is not cached,
        so a template with no sequenceModel fails every test here, not just the first)."""
        if not self._cache:
            bundles = {key: json.loads((EVIDENCE_DIR / name).read_text()) for name, key in EVIDENCE_RUNS.items()}
            runs = {key: b["docs"]["runs"][key] for key, b in bundles.items()}
            loops = {key: list(b["docs"]["backchain"].values()) for key, b in bundles.items()}
            models = run_logic(
                "(function(a){var o={};Object.keys(a.runs).forEach(function(k){o[k]=sequenceModel(a.runs[k],{loops:a.loops[k]});});return o;})("
                + json.dumps({"runs": runs, "loops": loops}) + ")")
            self._cache.update(runs=runs, models=models)
        return self._cache

    @property
    def runs(self):
        return self.load()["runs"]

    @property
    def models(self):
        return self.load()["models"]

    def card(self, key, name):
        return next(c for c in self.models[key]["cards"] if c["key"] == name)

    def test_one_column_per_visit_and_consecutive_skipped_visits_collapse_into_one(self) -> None:
        for key, run in self.runs.items():
            with self.subTest(run=key):
                rows, groups, streak = run["stages"], [], 0
                for row in rows + [{}]:
                    if row.get("skipped"):
                        streak += 1
                    elif streak:
                        groups.append(streak)
                        streak = 0
                columns = self.models[key]["columns"]
                self.assertEqual(len(columns), len(rows) - sum(n - 1 for n in groups))
                self.assertEqual(sum(c["n"] for c in columns), len(rows), "every visit is in a column")
        self.assertEqual(len(self.models["luna1"]["columns"]), 39)
        columns = self.models["hello-1190b"]["columns"]
        self.assertEqual(len(columns), 49)  # 47 work visits plus two collapsed runs of skipped ones (4 then 3 in a row)
        self.assertEqual(sum(1 for c in columns if c["kind"] == "work"), 47)
        self.assertEqual([(c["first"] + 1, c["last"] + 1, c["label"]) for c in columns if c["kind"] == "skipped"],
                         [(30, 33, "x4"), (35, 37, "x3")])

    def test_height_is_the_square_root_of_minutes_on_the_runs_own_scale_and_the_tallest_fills_the_plot(self) -> None:
        for key, model in self.models.items():
            with self.subTest(run=key):
                plot = model["lay"]["plot"]
                work = [c for c in model["columns"] if c["kind"] == "work" and c["min"] is not None]
                for column in model["columns"]:
                    self.assertTrue(is_number(column["h"]) and 2 <= column["h"] <= plot, f"{column['stage']}: {column['h']}")
                tallest = max(work, key=lambda c: c["min"])
                self.assertEqual(tallest["h"], plot)
                self.assertEqual(model["maxMin"], {"min": tallest["min"], "stage": tallest["stage"], "visit": tallest["first"] + 1})
                for column in work:
                    expected = max(2, math.sqrt(column["min"] / tallest["min"]) * plot)
                    self.assertAlmostEqual(column["h"], expected, delta=0.11)
        self.assertEqual(self.models["luna1"]["maxMin"], {"min": 196.4, "stage": "plan", "visit": 6})
        self.assertEqual(self.models["hello-1190b"]["maxMin"], {"min": 2.2, "stage": "spec", "visit": 4})

    def test_a_work_visit_timed_to_zero_still_gets_two_pixels_and_a_run_of_zeros_makes_no_nan(self) -> None:
        columns = self.models["hello-1190b"]["columns"]
        quick = next(c for c in columns if c["stage"] == "skill-validate" and c["first"] == 39)
        self.assertEqual((quick["kind"], quick["min"], quick["h"]), ("work", 0.0, 2))
        zeros, empty, nothing = run_logic(
            '[sequenceModel({stages:[{stage:"intake",min:0},{stage:"spec",min:0}]}),'
            ' sequenceModel({}), sequenceModel(null)]')
        self.assertEqual([c["h"] for c in zeros["columns"]], [2, 2])
        self.assertIsNone(zeros["maxMin"])
        for model in (empty, nothing):
            self.assertEqual((model["columns"], model["band"], model["bandNote"], model["visits"]), ([], None, "", 0))
            self.assertEqual(len(model["cards"]), 6)

    def test_a_visit_that_did_not_finish_done_carries_a_text_mark(self) -> None:
        luna = self.models["luna1"]["columns"]
        self.assertEqual((luna[-1]["outcome"], luna[-1]["mark"], luna[-1]["stage"]), ("blocked", "B", "system-test"))
        self.assertEqual([(c["first"] + 1, c["mark"]) for c in luna if c["mark"]], [(16, "R"), (39, "B")])
        hello = self.models["hello-1190b"]["columns"]
        self.assertEqual([(c["first"] + 1, c["mark"], c["outcome"]) for c in hello if c["mark"]], [(27, "P", "replan")])
        self.assertTrue(all(c["mark"] == "" for c in luna if c["outcome"] == "done"))

    def test_the_visits_card_splits_work_from_skipped_and_the_improve_card_counts_passes(self) -> None:
        self.assertEqual(self.card("hello-1190b", "visits")["text"], "54 (47 work, 7 skipped)")
        self.assertEqual(self.card("luna1", "visits")["text"], "39 (39 work)")
        self.assertEqual(self.card("hello-1190b", "improve")["value"], "19 passes")
        luna = self.card("luna1", "improve")
        self.assertEqual((luna["value"], luna["note"]), ("41 passes", "360.3 min, 31% of elapsed"))
        self.assertEqual(self.card("hello-1161", "improve")["value"], "8 passes")
        elapsed = self.card("luna1", "elapsed")
        self.assertEqual((elapsed["label"], elapsed["value"]), ("Elapsed (accept to accept)", "19.3 h"))
        self.assertIn("1,158.5 min", elapsed["note"])
        self.assertEqual(self.card("hello-1190b", "elapsed")["value"], "15.2 min")
        self.assertEqual(self.card("luna1", "loops")["value"], "2 loops")
        self.assertEqual(self.card("hello-1190b", "loops")["value"], "none")

    def test_context_and_refusals_are_numbers_or_not_measured_with_the_hosts_reason(self) -> None:
        luna = self.card("luna1", "context")
        self.assertEqual((luna["value"], luna["label"]), ("97.5%", "Context (main thread)"))
        self.assertIn("251,867 of 258,400 tokens", luna["note"])
        self.assertIn("34 compactions", luna["note"])
        self.assertEqual(self.card("luna1", "refusals")["value"], "13")
        hello = self.card("hello-1190b", "context")
        self.assertEqual(hello["value"], "27.1%")
        self.assertIn("compactions not measured", hello["note"])
        for key in ("hello-1161", "hello-1180", "hello-1190a", "hello-1190b"):
            refusals = self.card(key, "refusals")
            self.assertEqual((refusals["value"], refusals["measured"]), ("not measured", False))
            self.assertEqual(refusals["note"], self.runs[key]["unmeasured"]["shiploop_failures"])
            self.assertNotRegex(refusals["text"], r"^0\b")
        fixture = run_logic('sequenceModel({stages:[],unmeasured:{contextPeak:"the host reports no usage"}}).cards')
        by_key = {c["key"]: c for c in fixture}
        self.assertEqual((by_key["context"]["value"], by_key["context"]["measured"]), ("not measured", False))
        self.assertIn("the host reports no usage", by_key["context"]["note"])
        self.assertEqual(by_key["context"]["text"], "not measured: the host reports no usage")
        self.assertEqual(by_key["improve"]["value"], "not measured")
        bare = run_logic('sequenceModel({}).cards.map(function(c){return c.value;})')
        self.assertEqual(bare, ["0", "not measured", "not measured", "not loaded", "not measured", "not measured"])

    def test_the_context_band_exists_for_a_run_with_per_visit_context_and_reads_the_window_share(self) -> None:
        luna = self.models["luna1"]
        bars = luna["band"]["bars"]
        self.assertEqual(len(bars), 39)
        peak = max(bars, key=lambda b: b["pct"])
        self.assertEqual(peak["pct"], 97.5)
        self.assertAlmostEqual(peak["pct"], 100 * 251867 / 258400, delta=0.05)  # the run's own peak over its window
        self.assertEqual(luna["columns"][peak["col"]]["stage"], "static-checks")
        self.assertEqual(luna["band"]["ticksTotal"], 34)
        self.assertEqual(sum(b["ticks"] for b in bars), 34)
        self.assertEqual(luna["bandNote"], "")
        rows = self.runs["luna1"]["stages"]
        self.assertEqual([b["warn"] for b in bars], [r["context"]["peakPct"] >= 90 for r in rows])
        self.assertTrue(all(is_number(b["h"]) and b["h"] > 0 for b in bars))
        self.assertEqual(luna["lay"]["bandH"], 34)

    def test_a_run_with_no_per_visit_context_has_no_band_and_says_why(self) -> None:
        for key in ("hello-1161", "hello-1180", "hello-1190a", "hello-1190b"):
            with self.subTest(run=key):
                model = self.models[key]
                self.assertIsNone(model["band"])
                self.assertEqual(model["bandNote"], "Per-visit context not measured on this host: "
                                 + self.runs[key]["unmeasured"]["visitContext"])
        self.assertEqual(run_logic('sequenceModel({stages:[{stage:"intake",min:1}]}).bandNote'),
                         "Per-visit context not measured on this host")

    def test_a_visit_without_a_context_in_a_run_that_has_some_is_not_measured_never_a_zero_bar(self) -> None:
        model = run_logic(
            'sequenceModel({contextWindow:1000,stages:[{stage:"intake",min:1,context:{peak:500,compactions:0,calls:3}},'
            '{stage:"spec",min:2},{stage:"plan",min:3,context:{calls:2}}]})')
        bars = model["band"]["bars"]
        self.assertEqual([(b["pct"], b["h"], b["warn"], b["ticks"]) for b in bars],
                         [(50, 17, False, 0), (None, None, False, None), (None, None, False, None)])
        self.assertEqual(model["band"]["ticksTotal"], 0)

    def test_a_seeded_visit_is_never_a_zero_bar_and_a_visit_with_no_time_is_n_a(self) -> None:
        model = run_logic(
            'sequenceModel({wallMin:10,stages:[{stage:"intake",outcome:"done",min:null},{stage:"spec",outcome:"done",min:null,seeded:true},'
            '{stage:"plan",outcome:"done",min:4},{stage:"select-work",outcome:"done",min:0,skipped:true},'
            '{stage:"step-plan",outcome:"done",min:0,skipped:true}]})')
        none, seeded, work, skipped = model["columns"]
        self.assertEqual((none["kind"], none["na"], none["min"], none["h"]), ("work", True, None, 26))
        self.assertEqual((seeded["kind"], seeded["na"], seeded["min"], seeded["mark"], seeded["h"]), ("seeded", False, None, "S", 20))
        self.assertEqual((work["h"], work["min"], work["share"]), (96, 4, 40))
        self.assertEqual((skipped["kind"], skipped["n"], skipped["label"], skipped["h"], skipped["min"]), ("skipped", 2, "x2", 14, 0))
        self.assertEqual(len(model["columns"]), 4)
        self.assertEqual(model["cards"][0]["text"], "5 (2 work, 2 skipped, 1 seeded)")

    def test_the_column_detail_names_the_visit_its_files_improve_context_and_the_findings_at_its_phase(self) -> None:
        findings = [{"id": "o1", "title": "A plan defect", "phase": 2, "run": "luna1", "status": "open"},
                    {"id": "o2", "title": "A build defect", "phase": 3, "runs": ["luna1"], "status": "fixed"},
                    {"id": "o3", "title": "Another run", "phase": 2, "run": "hello-1161"},
                    {"id": "o4", "title": "Any run, plan", "phase": 2, "run": "any"}]
        details = run_logic(
            "(function(a){var m=sequenceModel(a.run,{});return [5,0,38].map(function(k){return columnDetail(m,k,a.run,a.findings);});})("
            + json.dumps({"run": self.runs["luna1"], "findings": findings}) + ")")
        plan, intake, last = details
        self.assertEqual(plan["title"], "Visit 6: plan")
        lines = dict(plan["lines"])
        self.assertEqual(lines["Outcome"], "done")
        self.assertEqual(lines["Minutes"], "196.4 min, 17% of elapsed")
        self.assertEqual((lines["Packet file"], lines["Result file"]), ("63.6 KB", "24.1 KB"))
        self.assertEqual(lines["Improve"], "3 passes, 39.18 min")
        self.assertEqual(lines["Context (main thread)"], "566 calls, peak 243,615 tokens (94.3% of the window), 4 compactions")
        self.assertEqual([f["id"] for f in plan["findings"]], ["o1", "o4"])
        self.assertEqual((plan["prev"], plan["next"]), (4, 6))
        self.assertEqual((intake["prev"], intake["findings"]), (None, []))
        self.assertEqual(dict(last["lines"])["Outcome"], "blocked (marked B)")
        self.assertEqual(last["next"], None)
        skipped = run_logic("(function(r){var m=sequenceModel(r,{});return columnDetail(m,29,r,[]);})("
                            + json.dumps(self.runs["hello-1190b"]) + ")")
        self.assertEqual(skipped["title"], "Visits 30 to 33: 4 skipped")
        self.assertEqual(dict(skipped["lines"])["Stages"], "test-spec, baseline, test-author, test-red")
        self.assertIn("no packet was issued", dict(skipped["lines"])["Outcome"])
        self.assertEqual(run_logic("columnDetail(sequenceModel({stages:[]}),0,{},[])"), None)

    def test_the_table_has_a_row_per_visit_and_context_columns_only_with_a_band(self) -> None:
        tables = run_logic(
            "(function(a){return Object.keys(a).map(function(k){return visitTable(a[k],sequenceModel(a[k],{}));});})("
            + json.dumps({k: self.runs[k] for k in ("luna1", "hello-1190b")}) + ")")
        luna, hello = tables
        self.assertEqual((len(luna["rows"]), len(hello["rows"])), (39, 54))
        self.assertEqual(luna["head"][-2:], ["Context peak", "Compactions"])
        self.assertEqual(hello["head"], ["#", "Stage", "Outcome", "Minutes", "Improve", "Packet file", "Result file"])
        self.assertEqual(luna["rows"][38], ["39", "system-test", "blocked", "11.2 min", "", "36.5 KB", "5.8 KB", "87.6%", "0"])
        self.assertEqual(hello["rows"][29], ["30", "test-spec", "done, skipped", "0 min", "", "none issued", "814 B"])
        self.assertEqual(hello["rows"][39][3], "under 0.1 min")
        self.assertTrue(all(len(r) == len(luna["head"]) for r in luna["rows"]))
        self.assertTrue(all(len(r) == len(hello["head"]) for r in hello["rows"]))
        self.assertNotRegex(json.dumps(tables), r"NaN|undefined|null")

    def test_the_shared_text_helpers_read_one_decimal_and_the_hosts_reason(self) -> None:
        self.assertEqual(run_logic('[pctText(97.47), pctText(27), pctText(100), kbText(814), kbText(55492), spanText(1158.5), spanText(15.2), spanText(119)]'),
                         ["97.5%", "27%", "100%", "814 B", "54.2 KB", "19.3 h", "15.2 min", "119 min"])
        self.assertEqual(run_logic('[whyNot({unmeasured:{shiploop_failures:"a"}},"refusals"), whyNot({unmeasured:{refusals:"b",shiploop_failures:"a"}},"refusals"),'
                                   ' whyNot({},"refusals"), whyNot({unmeasured:{contextPeak:"c"}},"contextPeak")]'), ["a", "b", "", "c"])


def evidence_run(key: str) -> dict:
    name = next(n for n, k in EVIDENCE_RUNS.items() if k == key)
    return json.loads((EVIDENCE_DIR / name).read_text())["docs"]["runs"][key]


def with_run(key: str) -> str:
    """Page setup that shows a committed v2 run (Luna or a hello run) and nothing else."""
    return ("data.runs=[Object.assign(" + json.dumps(evidence_run(key)) + ",{order:1})];data.bc=[];"
            "Object.keys(loaded).forEach(function(k){loaded[k]=true;});renderAll();")


class SequencePictureTests(unittest.TestCase):
    """R14: what the page draws from the model: the SVG, the six cards, a tapped column, the table and the comparison."""

    def svg(self, run: dict, picked: int = -1) -> str:
        return run_logic("sequenceSvg(sequenceModel(" + json.dumps(run) + ",{}),%d)" % picked)

    def test_every_column_has_a_bar_and_a_hit_area_and_the_run_with_context_has_a_band_of_bars_flags_and_ticks(self) -> None:
        run = evidence_run("luna1")
        svg = self.svg(run)
        self.assertEqual((svg.count('class="sq-col '), svg.count('class="sq-hit"')), (39, 39))
        self.assertEqual(len(re.findall(r'class="sq-ctx[ "]', svg)), 39)
        self.assertEqual(svg.count('class="sq-ctx warn"'), sum(1 for r in run["stages"] if r["context"]["peakPct"] >= 90))
        counts = [r["context"]["compactions"] for r in run["stages"]]
        self.assertEqual(svg.count('class="sq-tri"'), sum(c for c in counts if 0 < c <= 3))
        for many in sorted({c for c in counts if c > 3}):  # more than three: the count as a number
            self.assertRegex(svg, r'class="sq-mark"[^>]*>%d</text>' % many)
        self.assertEqual(svg.count("sq-100"), 1)
        self.assertIn(">100%</text>", svg)
        self.assertEqual(svg.count("sq-mark"), 2 + 1 + 1)  # B and R under the columns, and the counts 4 and 5 in the band
        self.assertEqual(sum(r.get("improve", {}).get("passes", 0) > 0 for r in run["stages"]), svg.count('class="sq-imp"'))
        self.assertEqual(svg.count("sq-sel"), 0)
        self.assertEqual(self.svg(run, 5).count('class="sq-sel"'), 1)

    def test_a_run_without_per_visit_context_draws_no_band_and_collapses_the_skipped_visits_to_xn_labels(self) -> None:
        svg = self.svg(evidence_run("hello-1190b"))
        self.assertEqual((svg.count('class="sq-col '), svg.count('class="sq-hit"')), (49, 49))
        for absent in ("sq-ctx", "sq-bandbg", "sq-100", "sq-tri", "sq-nm"):
            self.assertNotIn(absent, svg)
        self.assertEqual((svg.count(">x4</text>"), svg.count(">x3</text>"), svg.count(" skip\"")), (1, 1, 2))
        self.assertEqual(svg.count('class="sq-imp"'), 11)
        self.assertEqual(len(re.findall(r">P</text>", svg)), 1)

    def test_skipped_seeded_and_untimed_visits_are_drawn_apart_and_no_bar_has_zero_height(self) -> None:
        run = {"wallMin": 10, "stages": [
            {"stage": "intake", "outcome": "done", "min": None}, {"stage": "spec", "outcome": "done", "min": None, "seeded": True},
            {"stage": "plan", "outcome": "done", "min": 4}, {"stage": "select-work", "outcome": "done", "min": 0},
            {"stage": "step-plan", "outcome": "done", "min": 0.0, "skipped": True}]}
        svg = self.svg(run)
        classes = re.findall(r'class="sq-col ([^"]+)"', svg)
        self.assertEqual(classes, ["na", "seed", "o-done", "o-done", "skip"])
        self.assertIn(">n/a</text>", svg)
        self.assertEqual(svg.count(">S</text>"), 1)
        heights = [float(h) for h in re.findall(r'class="sq-col [^"]+" x="[^"]+" y="[^"]+" width="[^"]+" height="([^"]+)"', svg)]
        self.assertEqual(heights, [26, 20, 96, 2, 14])  # n/a, seeded, the tallest, a work visit timed to zero, skipped
        self.assertTrue(all(h >= 2 for h in heights))
        skipped = self.svg({"stages": [{"stage": "test-spec", "skipped": True, "min": 0}, {"stage": "baseline", "skipped": True, "min": 0}]})
        self.assertEqual((re.findall(r'class="sq-col ([^"]+)"', skipped), skipped.count(">x2</text>")), (["skip"], 1))
        self.assertIn('id="sq-hatch"', skipped)
        self.assertIn('id="sq-cross"', skipped)

    def test_the_svg_takes_every_colour_from_the_page_tokens_and_escapes_what_it_prints(self) -> None:
        svg = self.svg(evidence_run("luna1"), 3)
        self.assertNotRegex(svg, r'(?i)#[0-9a-f]{3,8}\b(?!\))|rgb\(|hsl\(', "a colour literal would not follow dark mode")
        self.assertNotRegex(svg, r"NaN|undefined|null|Infinity")
        css = TEMPLATE.read_text(encoding="utf-8").split("</style>")[0]
        for rule in re.findall(r"^\.(?:sq|sw|kpi)[^{]*\{[^}]*\}", css, re.M):
            self.assertNotRegex(rule, r"(?i)#[0-9a-f]{3,8}\b|rgb\(|hsl\(", rule)
        hostile = self.svg({"stages": [{"stage": "<img src=x onerror=alert(1)>", "outcome": '"><script>', "min": 1}]})
        self.assertNotIn("<img", hostile)
        self.assertNotIn("<script", hostile)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", hostile)

    def test_step_1_has_six_cards_the_picture_and_a_table_and_the_old_stage_table_is_gone(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8")
        for gone in ("hideshort", "hideShort", "Hide stages under 1 minute", "Stages: minutes between accepts"):
            self.assertNotIn(gone, html)
        out = page_probe('[REG.kpis.children.map(function(c){return c.textContent;}), REG.seqscroll.innerHTML.slice(0,4),'
                         ' REG.seqcard.hidden, textOf("seqtabsum"), walk(REG.seqtable,function(e){return e.tagName==="tr";}).length]',
                         setup=SAMPLE_SETUP)
        self.assertEqual(out[0], ["Visits22 work", "Elapsed (accept to accept)30 minstart to the last accept",
                                  "Improvenot measuredno Improve record", "Backchain loopsnoneno Backchain loop recorded for this run",
                                  "Context (main thread)not measuredno reason recorded", "Refusalsnot measuredno reason recorded"])
        self.assertEqual((out[1], out[2], out[3], out[4]), ("<svg", False, "Table of the 2 visits (packet and result are file sizes, not what the model read)", 3))

    def test_tapping_a_column_shows_its_detail_with_the_findings_at_its_stage_and_previous_and_next_walk_the_visits(self) -> None:
        out = page_probe(
            'setCol(1);var a=textOf("seqdetail"),btns=byClass("seqdetail","btn").map(function(b){return b.textContent+":"+b.disabled;}),'
            'chips=byClass("seqdetail","chip").map(function(c){return c.textContent;}),sel=REG.seqscroll.innerHTML.indexOf("sq-sel")>0;'
            'byClass("seqdetail","btn")[0].onclick();var b=textOf("seqdetail");'
            'setCol(1);byClass("seqdetail","btn")[2].onclick();[a,btns,chips,sel,b,textOf("seqdetail"),pickedCol]', setup=SAMPLE_SETUP)
        self.assertIn("Visit 2: spec", out[0])
        self.assertIn("blocked (marked B)", out[0])
        self.assertIn("25 min, 83.3% of elapsed", out[0])
        self.assertEqual(out[1], ["Previous visit:false", "Next visit:true", "Close:false"])
        self.assertEqual(out[2], ["#1 First finding"])  # the finding marked at the Specify phase for this run
        self.assertTrue(out[3])
        self.assertIn("Visit 1: intake", out[4])  # Previous
        self.assertEqual((out[5], out[6]), ("", -1))  # Close

    def test_the_click_handler_selects_the_tapped_column_again_deselects_and_another_run_starts_clean(self) -> None:
        out = page_probe(
            'var hit=function(k){return {target:{closest:function(){return {getAttribute:function(){return String(k);}};}}};};'
            'REG.seqscroll.onclick(hit(0));var a=pickedCol;REG.seqscroll.onclick(hit(1));var b=pickedCol;REG.seqscroll.onclick(hit(1));var c=pickedCol;'
            'REG.seqscroll.onclick({target:{closest:function(){return null;}}});var d=pickedCol;REG.seqscroll.onclick(hit(0));'
            'L.run="r2";renderAll();[a,b,c,d,pickedCol,textOf("seqdetail")]', setup=SAMPLE_SETUP)
        self.assertEqual(out, [0, 1, -1, -1, -1, ""])

    def test_the_table_lists_every_visit_and_a_run_with_no_visits_hides_the_picture_but_keeps_its_cards(self) -> None:
        luna = page_probe('[walk(REG.seqtable,function(e){return e.tagName==="tr";}).length,walk(REG.seqtable,function(e){return e.tagName==="th";}).length,'
                          'textOf("seqtabsum"),textOf("kpis"),textOf("seqnote"),REG.seqnote.hidden,REG.sqlegband.hidden,REG.seqscroll.innerHTML.split("sq-col ").length-1]',
                          setup=with_run("luna1"))
        self.assertEqual((luna[0], luna[1], luna[5], luna[6]), (40, 9, True, False))
        self.assertEqual((luna[2][:24], luna[7]), ("Table of the 39 visits (", 39))
        for text in ("Visits3939 work", "Elapsed (accept to accept)19.3 hstart to the last accept, 1,158.5 min",
                     "Improve41 passes360.3 min, 31% of elapsed", "Context (main thread)97.5%251,867 of 258,400 tokens; 34 compactions",
                     "Refusals13ShipLoop commands that exited non-zero"):
            self.assertIn(text, luna[3])
        self.assertEqual(luna[4], "")
        hello = page_probe('[textOf("kpis"),textOf("seqnote"),REG.seqnote.hidden,REG.sqlegband.hidden,walk(REG.seqtable,function(e){return e.tagName==="th";}).length]',
                           setup=with_run("hello-1190b"))
        self.assertIn("Visits5447 work, 7 skipped", hello[0])
        self.assertIn("Improve19 passes", hello[0])
        self.assertIn("Refusalsnot measured", hello[0])
        self.assertIn(evidence_run("hello-1190b")["unmeasured"]["shiploop_failures"], hello[0])
        self.assertEqual(hello[1], "Per-visit context not measured on this host: " + evidence_run("hello-1190b")["unmeasured"]["visitContext"])
        self.assertEqual((hello[2], hello[3], hello[4]), (False, True, 7))
        for text in (luna[3], hello[0], hello[1]):
            self.assertNotRegex(text, r"undefined|NaN|null")
        empty = page_probe('data.runs[0].stages=[];renderAll();[REG.seqcard.hidden,REG.seqtabbox.hidden,REG.kpis.children.length,textOf("seqdetail")]',
                           setup=SAMPLE_SETUP)
        self.assertEqual(empty, [True, True, 6, ""])

    def test_the_comparison_shows_the_same_six_numbers_for_both_runs_side_by_side(self) -> None:
        out = page_probe('L.cmp="r2";renderAll();[textOf("rundetail"),walk(REG.rundetail,function(e){return e.tagName==="tr"&&e.parent&&e.parent.tagName==="tbody";}).length]',
                         setup=SAMPLE_SETUP)
        self.assertIn("The same six numbers, side by side", out[0])
        self.assertIn("MeasureRun oneRun two", out[0])
        self.assertIn("Elapsed (accept to accept)30 minstart to the last accept12 minstart to the last accept", out[0])
        self.assertEqual(out[1], 6)
        none = page_probe('L.cmp="";renderAll();textOf("rundetail")', setup=SAMPLE_SETUP)
        self.assertNotIn("side by side", none)

    def test_the_path_chevrons_say_how_many_findings_each_stage_has_for_this_run(self) -> None:
        out = page_probe('byClass("flow","fc").map(function(c){return c.textContent;})', setup=SAMPLE_SETUP)
        self.assertEqual(out, ["1 finding, 1 open"])  # o1 sits at the Specify phase; o2's phase has no chevron in this sample
        more = page_probe('data.obs.push({id:"o3",title:"t",phase:1,run:"r1",status:"fixed"},{id:"o4",title:"u",phase:1,runs:["r2"],status:"open"},'
                          '{id:"o5",title:"v",phase:0,run:"any",status:"open"});renderAll();byClass("flow","fc").map(function(c){return c.textContent;})',
                          setup=SAMPLE_SETUP)
        self.assertEqual(more, ["1 finding, 1 open", "2 findings, 1 open"])  # o4 names only r2, so it is not r1's


if __name__ == "__main__":
    unittest.main()
