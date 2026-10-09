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
    ("intake", "spec", "test-strategy", "plan", "get-next-work-item", "step-plan", "implement", "extra"))}
INNER = ("get-next-work-item", "step-plan", "test-spec", "baseline", "test-author", "test-red", "implement", "test-green",
         "test-refine", "regression")  # the stages that belong to a work item (the fixture uses the first of them)
# (action, stage, minutes after T0 when accepted, outcome)
ACCEPTS = [("intake", "intake", 5, "done"), ("spec", "spec", 15, "done"), ("test-strategy", "test-strategy", 35, "done"),
           ("plan", "plan", 95, "done"), ("get-next-work-item", "get-next-work-item", 97, "done"),
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
    # state.md as ShipLoop writes it: each history row names its work item (None at an outer stage) and the run records
    # its delegation route, so the plan and execution can be read (R17).
    history = [{"action": IDS[a], "stage": s, "outcome": o, "summary": "x", "workitem": "W1" if s in INNER else None}
               for a, s, _, o in accepts]
    record(run / "state.md", {"status": status, "stage": "inner-loop" if status != "done" else "done",
                              "delegation": "inline",
                              "work_items": [{"id": "W1", "title": "Build the thing"}], "work_index": 0,
                              "inner_loops": {"W1": {"stage": "test-green", "action": {"id": "nav-x", "stage": "test-green"}}},
                              "history": history})
    write_json(run / "timeline.json", {"started": iso(0), "accepted": {IDS[a]: iso(m) for a, _, m, _ in accepts}})
    for action, stage, _, outcome in accepts:
        body = {"outcome": outcome, "summary": "s"}
        if stage == "step-plan":
            body["steps"] = [{"id": "S1", "task": "Write the rules module"}, {"id": "S2", "task": "Write the server"}]
        record(run / "results" / f"{IDS[action]}.md", {"action": IDS[action], "stage": stage, "result": body})
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
                          ("get-next-work-item", 2.0), ("step-plan", 30.0), ("implement", 13.0)])
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
                                             "action": IDS["extra"], "packetBytes": 100, "packetDoc": True,
                                             "resultBytes": run["stages"][-1]["resultBytes"], "resultFile": True,
                                             "summary": "x",  # the fixture's packet text carries none of the labels
                                             "carried": {label: False for label, _, _ in export.CARRIED}})
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
        # PHASES lists the first (canonical) name of an alias group, the engine's own
        self.assertEqual(set(listed), {export.stage_names(stage)[0] for stage in stage_spec.STAGES})
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
        stages = json.loads((SKILL_ROOT / "defaults" / "stages.json").read_text())["stages"]
        self.assertEqual(json.loads((target / "docs" / "config" / "stages.json").read_text()), {"stages": stages})
        writes = json.loads((target / "writes.json").read_text())
        self.assertEqual(len(writes), len(entries) + 3)  # the expectations, config/page, config/prompt and config/stages
        self.assertTrue(all(set(w) == {"op", "collection", "doc_id", "file_path"} and w["op"] == "set" for w in writes))

    def test_writes_json_lists_every_document_in_a_stable_order_with_absolute_paths(self):
        _, target = self.export(make_run(self.tmp))
        writes = json.loads((target / "writes.json").read_text())
        key = "codex-gpt-6-luna-1.16.1-battleship-20261003"
        self.assertEqual([(w["collection"], w["doc_id"]) for w in writes[:3]],
                         [("runs", key), ("backchain", f"{key}-plan"), ("backchain", f"{key}-step-plan")])
        # The packets follow, last and in their own sorted run, so a publish can upload them as separate batches (R17).
        self.assertEqual([w["collection"] for w in writes[3:]], ["packets"] * len(ACCEPTS))
        self.assertEqual([w["doc_id"] for w in writes[3:]], sorted(f"{key}--{IDS[a[0]]}" for a in ACCEPTS))
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
                          ("get-next-work-item", 2.0), ("step-plan", None), ("implement", None)])
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
        # Every field a SCHEMA.md table names is known to the validator for that collection. The table under config/stages
        # holds the fields of one catalog entry; a markdown heading ends a collection's tables.
        fields = None
        for line in text.splitlines():
            heading = re.match(r"\*\*`(\w+)/(\w*)", line)
            if line.startswith("#"):
                fields = None
            elif heading:
                collection = heading.group(1)
                fields = (export.SCHEMA["config"]["stages"][0][1] if heading.group(2) == "stages"
                          else export.SCHEMA[collection])
            elif fields is not None and line.startswith("| `"):
                for field in re.findall(r"`(\w+)`", line.split("|")[1]):
                    self.assertIn(field, fields, field)


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
        (run_dir_of(out) / "packets" / f"{IDS['get-next-work-item']}.md").unlink()
        run, facts = self.build(out)
        self.assertEqual([r["stage"] for r in run["stages"] if r.get("skipped")], ["get-next-work-item"])
        self.assertIs(self.row(run, "get-next-work-item")["skipped"], True)
        self.assertNotIn("packetBytes", self.row(run, "get-next-work-item"))
        self.assertEqual(sum("skipped" in r for r in run["stages"]), 1)
        self.assertIn("7 accepted actions (6 work, 1 skipped, 0 seeded)", "\n".join(facts))

    def test_no_packets_at_all_marks_nothing_because_absence_then_says_nothing(self):
        out = make_run(self.tmp, loops=False)
        shutil.rmtree(run_dir_of(out) / "packets")
        run, _ = self.build(out)
        self.assertTrue(all("skipped" not in r and "packetBytes" not in r for r in run["stages"]))
        self.assertEqual(self.row(run, "plan")["action"], IDS["plan"])

    def test_a_model_authored_not_applicable_visit_with_a_packet_and_four_seconds_stays_work(self):
        accepts = [*ACCEPTS[:4], ("get-next-work-item", "get-next-work-item", 95 + 4 / 60, "done"), *ACCEPTS[5:]]
        out = make_run(self.tmp, accepts, loops=False)
        run_dir = run_dir_of(out)
        for text in ("Not applicable: nothing to select", "Not applicable to this item"):  # the engine's own phrase too
            record(run_dir / "results" / f"{IDS['get-next-work-item']}.md", {"action": IDS["get-next-work-item"], "stage": "get-next-work-item",
                                                                    "result": {"outcome": "done", "summary": text}})
            run, _ = self.build(out)
            row = self.row(run, "get-next-work-item")
            self.assertEqual((row["min"], row["packetBytes"], "skipped" in row), (0.1, 100, False), text)
            self.assertEqual(row["action"], IDS["get-next-work-item"])

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


# ---------------------------------------------------------------- R16: the loops ShipLoop 1.21.0 keeps under run/backchain/

START_STEPS = [{"id": "S1", "x": 1}, {"id": "S2", "x": 1}]
FINAL_STEPS = [{"id": "S1", "x": 2}, {"id": "S2", "x": 1}]
# A check receipt's candidate_sha256 is the digest of the bytes the snapshot candidate-<sha12>.json keeps (write_json's text).
START_DIGEST, FINAL_DIGEST = (hashlib.sha256(json.dumps({"steps": s}, indent=1).encode()).hexdigest()
                              for s in (START_STEPS, FINAL_STEPS))
LATER_DIGEST = "c" * 64  # the parent's later edit of the plan, which the loop never saw
RECEIPT_1_21 = {"status": "complete", "progress": {"action_number": 1, "trivial_streak": 0, "required_trivial_reviews": 0},
                "last_report": {"classification": "non-trivial", "exit_assessment": "satisfied"},
                "conditions": {"exit": "One complete dependency review/fix/check cycle has run"}}


def set_state(out: Path, **fields) -> None:
    """Add keys to (or with None remove them from) the shiploop-state record of a fixture run's state.md."""
    path = run_dir_of(out) / "state.md"
    state = export._record(path)
    for name, value in fields.items():
        state.pop(name, None) if value is None else state.__setitem__(name, value)
    record(path, state)


def snapshot(loop: Path, digest: str, steps: list[dict]) -> None:
    """candidate-<sha12>.json, the snapshot `shiploop backchain-check` keeps of the bytes it checked."""
    write_json(loop / f"candidate-{digest[:12]}.json", {"steps": steps})


def make_1_21_loop(out: Path, action: str = "plan", receipt: dict | None = None, check_at: float | None = 79,
                   start_at: float | None = 40, receipt_at: float = 80, record_at: float | None = 81) -> Path:
    """run/backchain/<action id>/ as a 1.21.0 one-pass loop leaves it: the start contract, the runtime's receipt and its
    terminal copy, the candidate snapshots with the backchain-check receipt of the final one, and the review record the
    host kept under notes/. A None leaves that file out."""
    run = run_dir_of(out)
    loop = run / "backchain" / IDS[action]
    snapshot(loop, START_DIGEST, START_STEPS)
    snapshot(loop, FINAL_DIGEST, FINAL_STEPS)
    if start_at is not None:
        write_json(loop / "until-loop-start-contract.json", {"required_trivial_reviews": 0, "work": "binding"}, at=start_at)
    write_json(loop / "until-loop-receipt.json", receipt or RECEIPT_1_21, at=receipt_at)
    write_json(loop / "until-loop-terminal-packet.json", receipt or RECEIPT_1_21, at=receipt_at + 1)
    if check_at is not None:
        write_json(loop / f"check-{FINAL_DIGEST[:12]}.json", {"schema": "shiploop-backchain-check/v1",
                   "candidate_sha256": FINAL_DIGEST, "ok": True, "completion": "complete"}, at=check_at)
    if record_at is not None:  # a Backchain review record: new draft, so its own input is "unavailable"
        write_json(run / "notes" / f"{IDS[action]}-backchain-review-record.json",
                   {"candidate": {"input_sha256": "unavailable", "output_sha256": FINAL_DIGEST},
                    "convergence": {"candidate": {"input_sha256": START_DIGEST, "output_sha256": FINAL_DIGEST}}}, at=record_at)
    return loop


class BackchainLoopRecordsTest(unittest.TestCase):
    """R16: the exporter reads the loops 1.21.0 keeps under run/backchain/<action>/ and records, without enforcing
    anything, the run's backchain_passes option and whether the last check receipt is for the loop's final candidate."""

    KEY = RunReviewTest.KEY
    PLAN = f"{KEY}-plan"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def run_out(self, option: str | None = "one", **loop) -> Path:
        out = make_run(Path(tempfile.mkdtemp(dir=self.tmp)), loops=False)
        set_state(out, backchain_passes=option)
        make_1_21_loop(out, **loop)
        return out

    def export(self, out: Path) -> tuple[dict, list[str]]:
        docs, facts = export.build_run(out)
        for doc_id, doc in docs["backchain"].items():
            self.assertEqual(export.validate_doc("backchain", doc), [], doc_id)
        return docs["backchain"], facts

    @staticmethod
    def facts_of(doc: dict) -> dict:
        return {f["k"]: f["v"] for f in doc["facts"]}

    def test_a_loop_under_run_backchain_is_found_and_built_from_the_runtime_receipt(self):
        loops, facts = self.export(self.run_out())
        self.assertEqual(list(loops), [self.PLAN])
        doc, f = loops[self.PLAN], self.facts_of(loops[self.PLAN])
        self.assertEqual((doc["loop"], doc["phase"], doc["order"], doc["stageMin"]), ("plan", 2, 1, 60))
        self.assertEqual([(s["label"], s["min"], s["kind"]) for s in doc["segments"]],
                         [("Before the loop", 5, "neutral"), ("Pass 1", 40, "unclear"), ("After the loop", 15, "neutral")])
        self.assertEqual(sum(s["min"] for s in doc["segments"]), doc["stageMin"])
        one = doc["segments"][1]
        self.assertEqual((one["pass"], one["change"], one["streak"]), (1, "1 step changed", 0))
        self.assertIn("non-trivial", one["note"])
        self.assertIn("exit was assessed as satisfied", one["note"])
        self.assertEqual((f["Passes"], f["Final status"]), ("1", "complete"))
        self.assertEqual(f["Receipt"], f"backchain/{IDS['plan']}/until-loop-receipt.json")
        self.assertEqual(f["Stage"], "plan, 60 min accept to accept")
        line = next(x for x in facts if x.startswith("- Backchain loops:"))
        self.assertIn("plan 1 passes, complete, stage 60 min, candidate match yes", line)
        self.assertNotIn("none found", line)

    def test_the_run_option_is_recorded_as_written_and_not_recorded_when_the_key_is_absent(self):
        for written, shown in (("one", "one"), ("converge", "converge"), ("none", "none"), ("maybe", "maybe"),
                               (2, "2"), (None, "not recorded")):
            with self.subTest(written=written):
                loops, facts = self.export(self.run_out(option=written))
                doc = loops[self.PLAN]
                self.assertEqual(doc["backchainPasses"], shown)
                self.assertEqual(self.facts_of(doc)["Backchain passes option"], shown)
                self.assertIn(f"- Backchain passes option (state.md): {shown}", facts)

    def test_candidate_match_is_true_for_the_loops_final_candidate_false_for_another_and_unknown_without_either_digest(self):
        match = self.export(self.run_out())[0][self.PLAN]
        self.assertIs(match["candidateMatch"], True)
        self.assertEqual(self.facts_of(match)["Candidate match"],
                         f"yes: the last check receipt (ok) is for the loop's final candidate {FINAL_DIGEST[:12]}")
        out = self.run_out()
        write_json(run_dir_of(out) / "backchain" / IDS["plan"] / f"check-{LATER_DIGEST[:12]}.json",
                   {"candidate_sha256": LATER_DIGEST, "ok": False}, at=100)  # the parent rechecked an edited plan
        other = self.export(out)[0][self.PLAN]
        self.assertIs(other["candidateMatch"], False)
        self.assertEqual(self.facts_of(other)["Candidate match"],
                         f"no: the last check receipt (not ok) is for {LATER_DIGEST[:12]}, "
                         f"the loop's final candidate is {FINAL_DIGEST[:12]}")
        no_check = self.export(self.run_out(check_at=None))[0][self.PLAN]
        self.assertEqual(no_check["candidateMatch"], "unknown")
        self.assertIn("no backchain-check receipt", self.facts_of(no_check)["Candidate match"])
        no_digest = self.export(self.run_out(record_at=None))[0][self.PLAN]
        self.assertEqual(no_digest["candidateMatch"], "unknown")
        self.assertIn("candidate.output_sha256", self.facts_of(no_digest)["Candidate match"])

    def test_the_last_check_receipt_is_the_newest_by_file_time_not_by_name(self):
        out = self.run_out()
        folder = run_dir_of(out) / "backchain" / IDS["plan"]
        write_json(folder / "check-000000000000.json", {"candidate_sha256": LATER_DIGEST, "ok": True}, at=60)  # older, sorts first
        self.assertIs(self.export(out)[0][self.PLAN]["candidateMatch"], True)
        write_json(folder / "check-zzzzzzzzzzzz.json", {"candidate_sha256": LATER_DIGEST, "ok": True}, at=90)  # newest
        self.assertIs(self.export(out)[0][self.PLAN]["candidateMatch"], False)

    def test_a_zero_trivial_requirement_is_a_neutral_note_and_a_real_one_still_reads_x_of_y(self):
        zero = self.export(self.run_out())[0][self.PLAN]
        self.assertEqual(zero["trivialRequired"], 0)
        self.assertEqual(self.facts_of(zero)["Trivial streak"], "no trivial-streak requirement on this loop")
        self.assertNotIn("0 of 0", json.dumps(zero))
        converge = dict(RECEIPT_1_21, progress={"action_number": 2, "trivial_streak": 1, "required_trivial_reviews": 2})
        two = self.export(self.run_out(option="converge", receipt=converge))[0][self.PLAN]
        self.assertEqual((two["trivialRequired"], self.facts_of(two)["Trivial streak"]), (2, "1 of 2 required"))
        bare = dict(RECEIPT_1_21, progress={"action_number": 1})  # a receipt that names no requirement
        none = self.export(self.run_out(receipt=bare))[0][self.PLAN]
        self.assertNotIn("trivialRequired", none)
        self.assertNotIn("Trivial streak", self.facts_of(none))

    def test_a_loop_of_several_passes_with_no_per_pass_record_is_one_span_not_invented_passes(self):
        many = dict(RECEIPT_1_21, progress={"action_number": 3, "trivial_streak": 2, "required_trivial_reviews": 2})
        doc = self.export(self.run_out(option="converge", receipt=many))[0][self.PLAN]
        self.assertEqual(self.facts_of(doc)["Passes"], "3")
        span = [s for s in doc["segments"] if s["label"].startswith("Passes")]
        self.assertEqual([(s["label"], s["min"]) for s in span], [("Passes 1 to 3", 40)])
        self.assertNotIn("pass", span[0])
        self.assertIn("no per-pass record", span[0]["note"])

    def test_a_loop_with_no_start_record_has_no_segments_and_says_so_never_a_zero(self):
        doc = self.export(self.run_out(start_at=None))[0][self.PLAN]
        self.assertEqual((doc["segments"], doc["stageMin"]), ([], None))
        self.assertIn("not recorded", self.facts_of(doc)["Timing"])
        self.assertEqual(self.facts_of(doc)["Passes"], "1")
        self.assertIs(doc["candidateMatch"], True)  # the digests do not need the start

    def test_a_directory_with_only_check_receipts_is_no_loop_and_the_facts_name_both_places_looked(self):
        out = make_run(Path(tempfile.mkdtemp(dir=self.tmp)), loops=False)
        set_state(out, backchain_passes="none")
        write_json(run_dir_of(out) / "backchain" / IDS["plan"] / f"check-{FINAL_DIGEST[:12]}.json",
                   {"candidate_sha256": FINAL_DIGEST, "ok": True})
        loops, facts = self.export(out)
        self.assertEqual(loops, {})
        self.assertIn("- Backchain loops: none found under scratch/ or backchain/", facts)
        self.assertIn("- Backchain passes option (state.md): none", facts)  # a run with option none has no loop to carry it

    def test_a_second_loop_is_ordered_by_its_start_and_named_by_its_stage(self):
        out = self.run_out()
        make_1_21_loop(out, action="step-plan", start_at=100, receipt_at=110, check_at=None, record_at=None)
        loops, _ = self.export(out)
        self.assertEqual([(d["loop"], d["order"]) for d in loops.values()], [("plan", 1), ("step-plan", 2)])
        self.assertEqual(list(loops), [self.PLAN, f"{self.KEY}-step-plan"])

    def test_the_scratch_layout_the_committed_runs_use_still_exports_as_before_with_the_new_facts_unknown(self):
        out = make_run(Path(tempfile.mkdtemp(dir=self.tmp)))  # scratch/backchain-plan and -step-plan, no backchain_passes key
        docs, facts = export.build_run(out)
        plan = docs["backchain"][self.PLAN]
        self.assertEqual([(s["label"], s["min"]) for s in plan["segments"]],
                         [("Before the loop", 5), ("Pass 1", 10), ("Pass 2", 12), ("Pass 3", 8), ("After the loop", 25)])
        f = self.facts_of(plan)
        self.assertEqual((f["Passes"], f["Trivial streak"], plan["trivialRequired"]), ("3", "1 of 1 required", 1))
        self.assertEqual(f["Receipt"], "scratch/backchain-plan/until-loop-receipt.json")
        self.assertEqual((plan["backchainPasses"], plan["candidateMatch"]), ("not recorded", "unknown"))
        self.assertIn("no backchain-check receipt", f["Candidate match"])
        self.assertEqual(self.facts_of(docs["backchain"][f"{self.KEY}-step-plan"])["Passes"], "2")

    def test_an_unreadable_loop_reports_unknown_passes_not_zero(self):
        out = make_run(Path(tempfile.mkdtemp(dir=self.tmp)), loops=False)
        write_json(run_dir_of(out) / "scratch" / "group" / "backchain-carry-forward" / "until-loop-receipt.json",
                   {"status": "active"})
        doc = self.export(out)[0][f"{self.KEY}-carry-forward"]
        self.assertEqual(self.facts_of(doc)["Passes"], "unknown")
        self.assertEqual(doc["candidateMatch"], "unknown")

    def test_schema_validates_the_new_fields_and_schema_md_documents_them_and_the_layouts(self):
        base = {"run": "r", "loop": "plan", "phase": 2, "order": 1, "title": "t", "segments": [], "facts": []}
        for value in (True, False, "unknown"):
            self.assertEqual(export.validate_doc("backchain", dict(base, candidateMatch=value, backchainPasses="one",
                                                                   trivialRequired=0)), [])
        problems = "\n".join(export.validate_doc("backchain", dict(base, candidateMatch="maybe", backchainPasses=1,
                                                                    trivialRequired="0")))
        for needle in ('candidateMatch: expected true, false or "unknown"', "backchainPasses: expected a string",
                       "trivialRequired: expected a number"):
            self.assertIn(needle, problems)
        text = SCHEMA_MD.read_text(encoding="utf-8")
        for phrase in ("`backchainPasses`", "`candidateMatch`", "`trivialRequired`", "run/backchain/<action>/",
                       "`scratch/**/`", "`candidate.output_sha256`", "no trivial-streak requirement on this loop"):
            self.assertIn(phrase, text)

    def test_schema_md_documents_why_the_first_visit_reads_shorter_than_the_harness_line(self):
        text = " ".join(SCHEMA_MD.read_text(encoding="utf-8").split())
        for phrase in ("The first visit's `min` runs from `timeline.json` `started`", "host's first event",
                       "2.5 min here (2.45 before the export rounds to a tenth) and 3.4 in the harness line"):
            self.assertIn(phrase, text)


# ---------------------------------------------------------------- R17: the plan's work items and each visit's packet

def make_plan_run(root: Path, rows: list, delegation: str = "inline", queue: list | None = None,
                  loops: bool = False) -> Path:
    """A run whose history follows the engine's own shape. `rows` are (name, stage, outcome, workitem, result body):
    the body holds what that visit's result carries (`steps` for a step plan, `work_items` for a plan or a replan).
    `queue` is state.md's final work_items (default: every id a plan or replan row lists)."""
    for name, *_ in rows:
        IDS.setdefault(name, f"nav-{hashlib.sha256(name.encode()).hexdigest()[:32]}")
    out = make_run(root, [(name, stage, 5 * (i + 1), outcome) for i, (name, stage, outcome, *_) in enumerate(rows)],
                   status="active", loops=loops)
    run = run_dir_of(out)
    listed = [item for *_, body in rows for item in body.get("work_items", [])]
    set_state(out, delegation=delegation, work_items=queue if queue is not None else listed,
              history=[{"action": IDS[name], "stage": stage, "outcome": outcome, "summary": "x", "workitem": item}
                       for name, stage, outcome, item, _ in rows])
    for name, stage, outcome, _, body in rows:
        record(run / "results" / f"{IDS[name]}.md",
               {"action": IDS[name], "stage": stage, "result": {"outcome": outcome, "summary": "s", **body}})
    return out


def steps_of(*ids: str) -> dict:
    return {"steps": [{"id": step, "task": f"do {step}"} for step in ids]}


# W1 is planned; its first step plan has three steps, two are built, the third comes back `revise`; the second plan has two
# steps, S1 needs one more attempt (`repeat`), both are built, and the item finishes. W2 is added by a replan at system-test:
# its plan has two steps and the run stops after the first implement visit, so S2 is never executed.
PLAN_ROWS = [
    ("plan", "plan", "done", None, {"work_items": [{"id": "W1", "title": "First item"}]}),
    ("get-next-work-item", "get-next-work-item", "done", "W1", {}),
    ("sp1", "step-plan", "done", "W1", steps_of("S1", "S2", "S3")),
    ("i1", "implement", "done", "W1", {}), ("i2", "implement", "done", "W1", {}),
    ("i3", "implement", "revise", "W1", {}),
    ("sp2", "step-plan", "done", "W1", steps_of("S1", "S2")),
    ("i4", "implement", "repeat", "W1", {}), ("i5", "implement", "done", "W1", {}), ("i6", "implement", "done", "W1", {}),
    ("test-green", "test-green", "done", "W1", {}),
    ("carry-forward", "carry-forward", "done", "W1", {"work_items": []}),
    ("replan", "system-test", "replan", None, {"work_items": [{"id": "W2", "title": "Corrective item"}]}),
    ("get-next-work-item-2", "get-next-work-item", "done", "W2", {}),
    ("sp3", "step-plan", "done", "W2", steps_of("S1", "S2")),
    ("i7", "implement", "done", "W2", {}),
]


class PlanAndExecutionTest(unittest.TestCase):
    """R17: the run document names each work item, how many times it went through the steps loop and which implement
    visit executed each planned step, from state.md and the results only."""

    KEY = RunReviewTest.KEY

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def build(self, out: Path) -> tuple[dict, list[str]]:
        docs, facts = export.build_run(out)
        run = docs["runs"][self.KEY]
        self.assertEqual(export.validate_doc("runs", run), [])
        return run, facts

    def fresh(self) -> Path:
        return Path(tempfile.mkdtemp(dir=self.tmp))

    def test_each_work_item_counts_its_loops_plans_and_implement_visits_and_pairs_steps_with_visits(self):
        run, _ = self.build(make_plan_run(self.fresh(), PLAN_ROWS))
        w1, w2 = run["workItems"]
        self.assertEqual((w1["id"], w1["title"], w1["origin"]), ("W1", "First item", "plan"))
        self.assertEqual((w1["stepPlans"], w1["loops"], w1["revises"], w1["repeats"]), (2, 2, 1, 1))
        self.assertEqual(w1["implementVisits"], {"done": 4, "repeat": 1, "revise": 1, "replan": 0, "blocked": 0})
        # the steps of the LATEST accepted plan, each with the done visit that executed it (the repeat is not it)
        self.assertEqual([(s["id"], s["action"]) for s in w1["steps"]], [("S1", IDS["i5"]), ("S2", IDS["i6"])])
        self.assertEqual((w1["stepsPlanned"], w1["stepsExecuted"]), (2, 2))
        self.assertEqual((w2["id"], w2["origin"], w2["stepPlans"], w2["loops"], w2["revises"]), ("W2", "replan", 1, 1, 0))
        self.assertEqual(w2["implementVisits"]["done"], 1)
        self.assertEqual([(s["id"], s["action"]) for s in w2["steps"]], [("S1", IDS["i7"]), ("S2", None)])
        self.assertEqual((w2["stepsPlanned"], w2["stepsExecuted"]), (2, 1))
        self.assertEqual((run["stepsPlanned"], run["stepsExecuted"]), (4, 3))  # steps executed < planned
        self.assertNotIn("workItems", run["unmeasured"])
        self.assertTrue(w2["steps"][1]["action"] is None and "action" in w2["steps"][1])  # None is written, not omitted

    def test_each_visit_row_names_its_work_item_loop_and_the_step_its_packet_was_for(self):
        run, _ = self.build(make_plan_run(self.fresh(), PLAN_ROWS))
        by_action = {r["action"]: r for r in run["stages"]}
        mark = lambda name: {k: by_action[IDS[name]].get(k) for k in ("workitem", "loop", "step")}
        self.assertEqual(mark("plan"), {"workitem": None, "loop": None, "step": None})  # an outer stage has none
        self.assertEqual(mark("sp1"), {"workitem": "W1", "loop": 1, "step": None})
        self.assertEqual([mark(n)["step"] for n in ("i1", "i2", "i3")], ["S1", "S2", "S3"])  # the plan then in force
        self.assertEqual(mark("i3")["loop"], 1)  # the revise visit ends loop 1
        self.assertEqual(mark("sp2")["loop"], 2)
        # a repeat is another attempt at the step that was still open
        self.assertEqual([(mark(n)["loop"], mark(n)["step"]) for n in ("i4", "i5", "i6")], [(2, "S1"), (2, "S1"), (2, "S2")])
        self.assertEqual((mark("test-green")["workitem"], mark("i7")["workitem"], mark("i7")["step"]), ("W1", "W2", "S1"))
        self.assertEqual(mark("replan")["workitem"], None)

    def test_a_not_yet_started_item_has_zero_loops_and_no_steps_and_a_title_is_cut_with_a_flag(self):
        rows = [*PLAN_ROWS[:1], PLAN_ROWS[1], PLAN_ROWS[2]]
        queue = [{"id": "W1", "title": "t" * 250}, {"id": "W9", "title": "later"}]
        run, _ = self.build(make_plan_run(self.fresh(), rows, queue=queue))
        w1, w9 = run["workItems"]
        self.assertEqual((len(w1["title"]), w1["titleTruncated"]), (200, True))
        self.assertEqual((w9["loops"], w9["stepPlans"], w9["steps"], w9["stepsPlanned"], w9["stepsExecuted"]), (0, 0, [], 0, 0))
        self.assertNotIn("origin", w9)  # no accepted result lists it
        self.assertEqual((run["stepsPlanned"], run["stepsExecuted"]), (3, 0))

    def test_a_step_task_over_200_characters_keeps_200_and_says_truncated(self):
        rows = [PLAN_ROWS[0], PLAN_ROWS[1],
                ("sp", "step-plan", "done", "W1", {"steps": [{"id": "S1", "task": "x" * 201}, {"id": "S2", "task": "y" * 200}]})]
        run, _ = self.build(make_plan_run(self.fresh(), rows))
        s1, s2 = run["workItems"][0]["steps"]
        self.assertEqual((len(s1["task"]), s1["truncated"], len(s2["task"]), "truncated" in s2), (200, True, 200, False))

    def test_a_run_on_the_ask_agent_route_has_steps_but_no_pairing(self):
        out = make_plan_run(self.fresh(), PLAN_ROWS, delegation="ask-agent")
        run, facts = self.build(out)
        w1 = run["workItems"][0]
        self.assertEqual((w1["stepsPlanned"], w1["loops"]), (2, 2))  # what the records do say stays
        self.assertTrue(all("action" not in s for item in run["workItems"] for s in item["steps"]))
        self.assertTrue(all("stepsExecuted" not in item for item in run["workItems"]) and "stepsExecuted" not in run)
        self.assertEqual(run["stepsPlanned"], 4)
        self.assertIn("ask-agent", run["unmeasured"]["stepsExecuted"])
        self.assertTrue(all("step" not in r for r in run["stages"]))  # no packet named a step on this route
        self.assertTrue(all(r.get("workitem") for r in run["stages"] if r["stage"] == "implement"))
        self.assertIn("executed not measured (", "\n".join(facts))

    def test_counts_that_do_not_line_up_with_one_packet_per_step_are_unknown_not_guessed(self):
        # one implement visit for a two-step plan, then the item moved on: it was not paired step by step
        rows = [PLAN_ROWS[0], PLAN_ROWS[1], ("sp", "step-plan", "done", "W1", steps_of("S1", "S2")),
                ("i1", "implement", "done", "W1", {}), ("test-green", "test-green", "done", "W1", {})]
        run, _ = self.build(make_plan_run(self.fresh(), rows))
        item = run["workItems"][0]
        self.assertNotIn("stepsExecuted", item)
        self.assertTrue(all("action" not in s for s in item["steps"]))
        self.assertIn("W1: it moved past implement with 1 done implement visits for 2 steps", run["unmeasured"]["stepsExecuted"])
        self.assertEqual(run["stepsPlanned"], 2)
        # more done visits than the plan has steps
        rows = [PLAN_ROWS[0], PLAN_ROWS[1], ("sp", "step-plan", "done", "W1", steps_of("S1")),
                ("i1", "implement", "done", "W1", {}), ("i2", "implement", "done", "W1", {})]
        run, _ = self.build(make_plan_run(self.fresh(), rows))
        self.assertIn("2 done implement visits follow a plan of 1 steps", run["unmeasured"]["stepsExecuted"])
        self.assertNotIn("stepsExecuted", run)

    def test_a_step_plan_that_lists_no_readable_steps_leaves_its_item_unmeasured(self):
        rows = [PLAN_ROWS[0], PLAN_ROWS[1], ("sp", "step-plan", "done", "W1", {})]
        run, _ = self.build(make_plan_run(self.fresh(), rows))
        item = run["workItems"][0]
        self.assertTrue("steps" not in item and "stepsPlanned" not in item and "stepsExecuted" not in item)
        self.assertEqual((item["stepPlans"], item["loops"]), (1, 1))
        self.assertNotIn("stepsPlanned", run)
        self.assertIn("W1: its latest step plan lists no readable steps", run["unmeasured"]["stepsPlanned"])
        self.assertIn("W1:", run["unmeasured"]["stepsExecuted"])

    def test_a_seeded_plan_visit_leaves_the_work_items_unmeasured_with_the_reason(self):
        out = make_plan_run(self.fresh(), PLAN_ROWS)
        edit_json(out / "result.json", lambda r: r.update(seeded={"skipped": ["plan"], "stage": "get-next-work-item"}))
        run, _ = self.build(out)
        self.assertTrue(all(k not in run for k in ("workItems", "stepsPlanned", "stepsExecuted")))
        self.assertIn("recorded by the E2E seed", run["unmeasured"]["workItems"])
        self.assertTrue(all("workitem" not in r and "loop" not in r and "step" not in r for r in run["stages"]))
        self.assertTrue(run["stages"][0]["seeded"])  # the visits themselves are still marked as seeded

    def test_the_old_shapes_say_what_is_missing_instead_of_counting_zero(self):
        out = make_plan_run(self.fresh(), PLAN_ROWS)
        set_state(out, work_items=None)
        run, facts = self.build(out)
        self.assertNotIn("workItems", run)
        self.assertIn("no work_items queue", run["unmeasured"]["workItems"])
        self.assertIn("Work items and steps loop: not measured (state.md has no work_items queue", "\n".join(facts))
        out = make_plan_run(self.fresh(), PLAN_ROWS)
        state = export._record(run_dir_of(out) / "state.md")
        for entry in state["history"]:
            del entry["workitem"]
        set_state(out, history=state["history"])
        run, _ = self.build(out)
        self.assertNotIn("workItems", run)
        self.assertIn("carry no workitem", run["unmeasured"]["workItems"])

    def test_a_run_with_no_visit_yet_has_an_empty_measured_list_not_a_missing_one(self):
        out = make_plan_run(self.fresh(), PLAN_ROWS[:1], queue=[])
        run, _ = self.build(out)
        self.assertEqual((run["workItems"], run["stepsPlanned"], run["stepsExecuted"]), ([], 0, 0))

    def test_the_facts_line_reports_the_headline_numbers(self):
        _, facts = self.build(make_plan_run(self.fresh(), PLAN_ROWS))
        line = next(f for f in facts if f.startswith("- Work items:"))
        self.assertEqual(line, "- Work items: 2 (1 added by replan); 3 step plans; 3 passes through the steps loop "
                               "(1 revises); 5 done implement visits; steps planned 4, executed 3")

    def test_the_table_of_stages_after_implement_is_the_engines(self):
        path = ROOT / "skills" / "shiploop" / "scripts" / "shiploop_stage_spec.py"
        spec = importlib.util.spec_from_file_location("run_review_selected_stage_spec_2", path)
        stage_spec = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = stage_spec
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(stage_spec)
        inner = list(stage_spec.INNER)
        self.assertEqual(export.AFTER_IMPLEMENT, tuple(inner[inner.index("implement") + 1:]))
        self.assertEqual((stage_spec.REVISE_TO, stage_spec.MAX_REVISES), ("step-plan", 2))  # SCHEMA.md says "at most twice"

    def test_schema_md_defines_loops_the_pairing_and_the_unknown_cases(self):
        text = " ".join(SCHEMA_MD.read_text(encoding="utf-8").split())
        for phrase in ("steps loop", "1 plus `revises`", "latest accepted (done) step plan", "implement_progress",
                       "k-th done implement visit", "ask-agent", "recorded by the E2E seed", "never 0",
                       "unmeasured.workItems", "unmeasured.stepsExecuted", "unmeasured.stepsPlanned"):
            self.assertIn(phrase, text, phrase)
        for name in ("workItems", "stepsPlanned", "stepsExecuted", "titleTruncated", "implementVisits", "origin",
                     "stages[].workitem", "stages[].packetDoc"):
            self.assertIn(name, text, name)


class PacketDocumentTest(unittest.TestCase):
    """R17: the packet text of each visit goes into its own collection, never into the committed export."""

    KEY = RunReviewTest.KEY

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def export(self, out: Path) -> tuple[dict, Path]:
        target = self.tmp / f"export-{len(list(self.tmp.glob('export-*')))}"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(export.main([str(out), "--out", str(target)]), 0)
        return json.loads((target / "docs" / "runs" / f"{self.KEY}.json").read_text()), target

    def packet(self, out: Path, name: str) -> Path:
        return run_dir_of(out) / "packets" / f"{IDS[name]}.md"

    def test_each_visit_with_a_packet_file_gets_a_document_with_its_size_digest_and_text(self):
        out = make_run(self.tmp, loops=False)
        self.packet(out, "plan").write_text("# Packet\nline two é\n", encoding="utf-8")
        run, target = self.export(out)
        doc = json.loads((target / "docs" / "packets" / f"{self.KEY}--{IDS['plan']}.json").read_text())
        raw = self.packet(out, "plan").read_bytes()
        self.assertEqual(doc, {"run": self.KEY, "action": IDS["plan"], "stage": "plan", "bytes": len(raw),
                               "shownBytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                               "text": "# Packet\nline two é\n"})
        self.assertEqual(export.validate_doc("packets", doc), [])
        self.assertEqual(len(list((target / "docs" / "packets").glob("*.json"))), len(ACCEPTS))
        self.assertTrue(all(r["packetDoc"] is True and r["packetBytes"] == 100 or r["stage"] == "plan" for r in run["stages"]))
        self.assertEqual(len([r for r in run["stages"] if r.get("packetDoc")]), len(ACCEPTS))
        self.assertIn(f"- Packet documents: {len(ACCEPTS)} written", (target / "facts.md").read_text())
        self.assertIn("0 truncated; 0 packet files unreadable", (target / "facts.md").read_text())

    def test_the_committed_export_leaves_the_packets_out_and_writes_json_lists_them_last(self):
        out = make_run(self.tmp, loops=False)
        _, target = self.export(out)
        bundle = json.loads((target / "review-export.json").read_text())
        self.assertEqual(sorted(bundle["docs"]), ["backchain", "runs"])
        self.assertNotIn("P" * 100, (target / "review-export.json").read_text())  # no packet text (the fixture's packets)
        self.assertIn(self.KEY, (target / "review-export.json").read_text())
        writes = json.loads((target / "writes.json").read_text())
        collections = [w["collection"] for w in writes]
        self.assertEqual(collections, sorted(collections, key=lambda c: export.COLLECTION_ORDER.index(c)))
        self.assertEqual(collections[-1], "packets")
        self.assertEqual(export.COLLECTION_ORDER[-1], "packets")

    def test_a_packet_over_150000_bytes_is_cut_at_a_line_boundary_and_keeps_the_whole_files_size_and_digest(self):
        out = make_run(self.tmp, loops=False)
        text = "".join(f"line {n:06d} of the packet\n" for n in range(7000))[:200_000 // 1]
        self.packet(out, "plan").write_text(text, encoding="utf-8")
        self.assertGreater(len(text.encode()), 150_000)
        run, target = self.export(out)
        doc = json.loads((target / "docs" / "packets" / f"{self.KEY}--{IDS['plan']}.json").read_text())
        raw = text.encode()
        self.assertEqual((doc["bytes"], doc["sha256"], doc["truncated"]), (len(raw), hashlib.sha256(raw).hexdigest(), True))
        self.assertLessEqual(doc["shownBytes"], export.MAX_PACKET_TEXT)
        self.assertGreater(doc["shownBytes"], export.MAX_PACKET_TEXT - 100)  # cut at the last line that fits
        self.assertTrue(doc["text"].endswith("\n") and text.startswith(doc["text"]))
        self.assertEqual(len(doc["text"].encode()), doc["shownBytes"])
        self.assertEqual(export.validate_doc("packets", doc), [])
        self.assertIn("1 truncated", (target / "facts.md").read_text())
        plan = next(r for r in run["stages"] if r["stage"] == "plan")
        self.assertEqual((plan["packetBytes"], plan["packetDoc"]), (len(raw), True))  # the row keeps the full size

    def test_a_packet_whose_json_would_pass_the_database_limit_is_cut_further(self):
        out = make_run(self.tmp, loops=False)
        self.packet(out, "plan").write_text('"\n' * 75_000, encoding="utf-8")  # 150,000 bytes, 300,000 once escaped
        _, target = self.export(out)
        doc = json.loads((target / "docs" / "packets" / f"{self.KEY}--{IDS['plan']}.json").read_text())
        self.assertEqual((doc["bytes"], doc["truncated"]), (150_000, True))
        self.assertLess(doc["shownBytes"], 150_000)
        self.assertLessEqual(export._serialized_bytes(doc), export.MAX_DOC_BYTES)
        self.assertEqual(export.validate_doc("packets", doc), [])
        big = dict(doc, text="x" * (export.MAX_DOC_BYTES + 1))
        self.assertIn("limit for one document", "\n".join(export.validate_doc("packets", big)))

    def test_a_visit_with_no_packet_file_has_no_document_and_no_flag(self):
        out = make_run(self.tmp, loops=False)
        self.packet(out, "get-next-work-item").unlink()
        run, target = self.export(out)
        row = next(r for r in run["stages"] if r["stage"] == "get-next-work-item")
        self.assertTrue(row["skipped"] and "packetDoc" not in row and "packetBytes" not in row)
        self.assertFalse((target / "docs" / "packets" / f"{self.KEY}--{IDS['get-next-work-item']}.json").exists())
        self.assertEqual(len(list((target / "docs" / "packets").glob("*.json"))), len(ACCEPTS) - 1)
        shutil.rmtree(run_dir_of(out) / "packets")
        run, target = self.export(out)
        self.assertTrue(all("packetDoc" not in r for r in run["stages"]))
        self.assertFalse((target / "docs" / "packets").exists())

    def test_a_packet_file_that_cannot_be_read_gets_no_document_and_facts_count_it(self):
        out = make_run(self.tmp, loops=False)
        self.packet(out, "spec").write_bytes(b"\xff\xfe not utf-8 \x80")
        run, target = self.export(out)
        row = next(r for r in run["stages"] if r["stage"] == "spec")
        self.assertEqual((row["packetBytes"], "packetDoc" in row), (len(b"\xff\xfe not utf-8 \x80"), False))
        self.assertFalse((target / "docs" / "packets" / f"{self.KEY}--{IDS['spec']}.json").exists())
        self.assertEqual(len(list((target / "docs" / "packets").glob("*.json"))), len(ACCEPTS) - 1)
        self.assertIn(f"{len(ACCEPTS) - 1} written", (target / "facts.md").read_text())
        self.assertIn("1 packet files unreadable (no document written)", (target / "facts.md").read_text())

    def test_a_second_export_drops_the_packet_documents_the_first_wrote(self):
        out = make_run(self.tmp, loops=False)
        target = self.tmp / "same"
        with contextlib.redirect_stdout(io.StringIO()):
            export.main([str(out), "--out", str(target)])
            self.packet(out, "plan").unlink()
            export.main([str(out), "--out", str(target)])
        self.assertFalse((target / "docs" / "packets" / f"{self.KEY}--{IDS['plan']}.json").exists())
        writes = json.loads((target / "writes.json").read_text())
        self.assertEqual(len([w for w in writes if w["collection"] == "packets"]), len(ACCEPTS) - 1)

    def test_a_review_bundle_may_not_carry_packets_and_the_validator_knows_the_collection(self):
        out = make_run(self.tmp, loops=False)
        docs, _ = export.build_run(out)
        self.assertEqual(sorted(docs), ["backchain", "packets", "runs"])
        self.assertTrue(all(export.validate_doc("packets", d) == [] for d in docs["packets"].values()))
        bad = dict(next(iter(docs["packets"].values())))
        del bad["sha256"]
        self.assertIn("missing required field 'sha256'", "\n".join(export.validate_doc("packets", bad)))
        failures, _ = export.check_bundle({"schema": export.SCHEMA_ID, "docs": {"packets": docs["packets"]}})
        self.assertTrue(any("packets documents are not part of a review bundle" in f for f in failures))
        failures, _ = export.check_bundle({"schema": export.SCHEMA_ID, "docs": {"runs": docs["runs"]}})
        self.assertEqual(failures, [])

    def test_schema_md_and_skill_md_name_the_packets_collection_and_how_it_is_uploaded(self):
        schema = " ".join(SCHEMA_MD.read_text(encoding="utf-8").split())
        skill = " ".join(SKILL_MD.read_text(encoding="utf-8").split())
        for phrase in ("`packets/<runKey>--<action>`", "not** part of `review-export.json`", "150,000 bytes",
                       "256 KiB", "at most 50 documents and 1 MiB", "`packetDoc`", "unreadable"):
            self.assertIn(phrase, schema, phrase)
        for phrase in ("packets", "at most 50 documents and 1 MiB each", "in `ArtifactData` batches of their own"):
            self.assertIn(phrase, skill, phrase)


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


class LoopStreakTests(unittest.TestCase):
    """R16: a loop with no trivial-streak requirement (a one-pass loop reads 0 of 0) is drawn neutrally, never as a failure."""

    DOC = ('{title:"Plan loop",run:"r1",order:1,stageMin:60,facts:[{k:"Trivial streak",v:"no trivial-streak requirement on this loop"},'
           '{k:"Backchain passes option",v:"one"},{k:"Candidate match",v:"no: the last check receipt (ok) is for 25aecd520d40, '
           'the loop\'s final candidate is 85f180cd6cd4"}],segments:[{label:"Pass 1",min:22,kind:"unclear",pass:1,change:"6 steps changed",'
           'note:"n",streak:0}]%s}')

    def strip_text(self, doc: str) -> dict:
        probe = ('(function(){var svg=passStrip(%s);var texts=walk(svg,function(e){return e._text;}).map(function(e){return e._text;});'
                 'return {texts:texts,label:svg.getAttribute("aria-label"),box:svg.getAttribute("viewBox")};})()' % doc)
        return page_probe(probe)

    def test_the_streak_target_keeps_a_zero_and_defaults_to_two_only_for_a_document_with_none(self):
        self.assertEqual(run_logic('[streakTarget({}), streakTarget(null), streakTarget({trivialRequired: 0}),'
                                   ' streakTarget({trivialRequired: 1}), streakTarget({trivialRequired: "0"}),'
                                   ' streakTarget({trivialRequired: -1})]'), [2, 2, 0, 1, 2, 2])
        self.assertEqual(run_logic('[streakNote({trivialRequired: 0}), streakNote({}), streakNote({trivialRequired: 1})]'),
                         ["no trivial-streak requirement on this loop", "the loop closes at a clean streak of 2",
                          "the loop closes at a clean streak of 1"])

    def test_a_zero_requirement_draws_no_streak_axis_target_or_closing_line_and_says_so(self):
        drawn = self.strip_text(self.DOC % ",trivialRequired:0")
        self.assertIn("no trivial-streak requirement on this loop", drawn["texts"])
        self.assertNotIn("streak", drawn["texts"])
        self.assertFalse([x for x in drawn["texts"] if "closes at" in x], drawn["texts"])
        self.assertNotIn("clean streak 0", drawn["label"])
        self.assertTrue(drawn["label"].endswith("No trivial-streak requirement on this loop."), drawn["label"])
        self.assertEqual(drawn["box"].split()[3], "96")

    def test_a_document_with_no_trivial_required_is_drawn_exactly_as_before_with_the_target_at_two(self):
        drawn = self.strip_text(self.DOC % "")
        self.assertIn("the loop closes at 2", drawn["texts"])
        self.assertIn("streak", drawn["texts"])
        self.assertTrue(drawn["label"].endswith("The loop closes at a clean streak of 2."), drawn["label"])
        self.assertIn("clean streak 0", drawn["label"])
        self.assertEqual(drawn["box"].split()[3], "176")
        one = self.strip_text(self.DOC % ",trivialRequired:1")
        self.assertIn("the loop closes at 1", one["texts"])

    def test_the_loop_card_shows_the_option_the_candidate_match_and_the_neutral_streak_note(self):
        card = page_probe('loopCard(%s).textContent' % (self.DOC % ",trivialRequired:0"), setup="live=false;")
        for phrase in ("Backchain passes optionone", "Candidate matchno: the last check receipt (ok) is for 25aecd520d40",
                       "Trivial streakno trivial-streak requirement on this loop"):
            self.assertIn(phrase, card)
        self.assertNotIn("0 of 0", card)
        self.assertEqual(card.count("no trivial-streak requirement on this loop"), 2)  # the fact, and the note under the strip
        self.assertNotIn("closes at", card)


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

    def test_the_head_names_the_run_the_repo_the_page_the_evidence_and_the_review_bundles(self) -> None:
        head = build_prompt().split("\n")[0]
        self.assertEqual(head, "Repair work from the Run Review of Luna max, battleship (skill-craft 1.16.1, ShipLoop 0.48.1; codex gpt-6-luna; "
                               "2026-10-03; blocked). In the skill-craft repository. Page: https://example.test/page. Run evidence: /runs/r1. "
                               "Review files: the *.review.json bundles in test/shiploop_e2e/evidence/ (find each ticked id below in the "
                               "bundle that has it, for example grep -l '\"a1\"' test/shiploop_e2e/evidence/*.review.json; edit it there).")
        text = build_prompt()
        self.assertIn("You ticked 1 option (1 fix ShipLoop). Plan them as one plan: merge overlap, resolve conflicts, order by dependency, "
                      "split into the smallest verifiable increments, mark what can run in parallel.", text)
        bare = build_prompt(run={"key": "k"}, config={"constraints": "", "closing": "", "artifactUrl": ""})
        self.assertTrue(bare.startswith("Repair work from the Run Review of the chosen run. In the skill-craft repository. Review files:"), bare)
        self.assertNotIn("Page:", bare)
        self.assertNotIn("Rules:", bare)

    def test_the_head_names_no_review_file_of_a_run_only_the_bundles_directory_and_a_ticked_id(self) -> None:
        """A finding can span runs and lives in one run's review bundle, so a file named from the page's primary run key
        (hello-1190b.review.json, which does not exist) sends Claude Code to nothing."""
        for key in ("r1", "hello-1190b", "claude-sonnet-5-5-1.19.0-hello-20261004"):
            with self.subTest(key=key):
                text = build_prompt(run={**prompt_state()["run"], "key": key}, selected={"options": {"a1": True, "a2": True}, "find": {}})
                head = text.split("\n")[0]
                self.assertEqual(re.findall(r"[\w.-]+\.review\.json", text), [], "a per-run review file is named")
                self.assertNotIn("Review file:", text)
                self.assertIn("Review files: the *.review.json bundles in test/shiploop_e2e/evidence/ (find each ticked id below in the "
                              "bundle that has it, for example grep -l '\"a1\"' test/shiploop_e2e/evidence/*.review.json; edit it there).", head)
                self.assertIn("\n1. a1 ", text)  # the id in the example is the first ticked option, printed below
        ask = build_prompt(selected={"options": {}, "find": {"f4": True}}).split("\n")[0]
        self.assertIn("grep -l '\"f4\"' test/shiploop_e2e/evidence/*.review.json", ask)  # investigate only: the finding's id
        odd = build_prompt(options=[{"id": "a'1", "title": "t", "goal": "Do: x."}], selected={"options": {"a'1": True}, "find": {}})
        self.assertIn("for example grep -l '\"<id>\"' test/", odd.split("\n")[0])  # an id that is not plain is never put into a shell line

    def test_the_report_back_says_to_set_the_status_in_the_review_file_that_holds_the_option(self) -> None:
        closing = json.loads((DEFAULTS_DIR / "config.json").read_text(encoding="utf-8"))["prompt"]["closing"]
        self.assertIn("set its status to done in the review file that holds it, citing the commit", closing)
        self.assertTrue(build_prompt().endswith(closing))

    def test_a_finding_spanning_runs_prints_once_with_the_primary_run_and_one_of_another_run_prints_that_runs_directory(self) -> None:
        span = {"id": "f5", "title": "Spans", "status": "open", "runs": ["r1", "r2"], "expected": "e5", "observed": "s5"}
        findings = [*prompt_state()["findings"], span]
        options = [*prompt_state()["options"], {"id": "a8", "title": "Fix spans", "kind": "fix-shiploop", "findings": ["f5", "f4"], "goal": "Do: x."}]
        picked = {"options": {"a8": True}, "find": {}}
        for key, directory in (("r1", "/runs/r1"), ("r2", "/runs/r2")):
            run = {**prompt_state()["run"], "key": key, "evidence": directory}
            others = [r for r in (prompt_state()["run"], *prompt_state()["runs"]) if r["key"] != key]
            text = build_prompt(run=run, runs=others, findings=findings, options=options, selected=picked)
            evidence = text.split("\nEVIDENCE\n")[1]
            self.assertEqual(len(re.findall(r"^- f5 ", evidence, re.M)), 1)
            self.assertIn(f"- f5 [open] Spans. Expected: e5 Saw: s5 (run: {key} at {directory})", evidence)
            self.assertIn(f"Run evidence: {directory}.", text.split("\n")[0])
        text = build_prompt(findings=findings, options=options, selected=picked)  # primary r1: f4 belongs to r2 only
        self.assertIn("- f4 [open] Elsewhere. Expected: e4 Saw: s4 (evidence: run/x; run: r2 at /runs/r2)", text)

    def test_the_page_prints_the_url_stored_in_config_page_artifact_url_and_nothing_when_it_is_empty_or_absent(self) -> None:
        def head(page: str) -> str:
            return page_probe('document.getElementById("prompt").value.split("\\n")[0]',
                              setup=SAMPLE_SETUP + 'data.cfg.page=%s;S().opts.a1=true;renderAll();' % page)
        self.assertIn(" Page: https://claude.ai/artifact/abc.", head('{title:"t",artifactUrl:"https://claude.ai/artifact/abc"}'))
        for page in ('{title:"t",artifactUrl:""}', '{title:"t"}', "undefined"):
            self.assertNotIn("Page:", head(page), page)

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
        stages = json.loads((DEFAULTS_DIR / "stages.json").read_text(encoding="utf-8"))["stages"]
        # config/page holds the page's URL: left alone; config/stages is the derived catalog, always the defaults'
        self.assertEqual(docs["config"], {"prompt": cfg["prompt"], "stages": {"stages": stages}})
        self.assertEqual(set(docs["expectations"]), set(self.defaults))
        self.assertFalse([k for k in docs["expectations"] if k.startswith("iter-")])
        self.assertEqual(set(docs), {"expectations", "config"})
        self.assertEqual(notes, [
            "expectations/phase-1: the page's text, which has no revision of its own, is replaced by the defaults' text",
            "expectations/group-principles: the page's text, which has no revision of its own, is replaced by the "
            "defaults' text",
            "config/prompt: replaced by the defaults (fields the defaults do not have are dropped)"])
        bare = {"expectations": {}, "config": {}}
        self.assertEqual(export.upgrade_docs(bare)[0]["config"], {**cfg, "stages": {"stages": stages}})  # a page with no settings gets all three

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
                         sorted([("config", "prompt"), ("config", "stages")] + [("expectations", k) for k in self.defaults]))
        bad = self.tmp / "bad.json"
        bad.write_text(json.dumps({"docs": {"expectations": {"P1": {"text": "a bare document, not a row"}}}}))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(export.main(["--defaults", "--live", str(bad), "--out", str(self.tmp / "bad")]), 2)
        self.assertIn('expectations/P1 has no document under "data"', err.getvalue())
        with contextlib.redirect_stderr(io.StringIO()) as usage, self.assertRaises(SystemExit):
            export.main(["--check", str(SAMPLE_REVIEW), "--live", str(SNAPSHOT)])
        self.assertIn("--live goes with --defaults", usage.getvalue())


class PageUrlTests(unittest.TestCase):
    """A page cannot read its own URL, so publish writes it: `--defaults --page-url URL` sets config/page.artifactUrl, which
    the prompt's head prints as `Page:`. The draft page's database starts from the defaults, whose artifactUrl is empty."""

    URL = "https://claude.ai/artifact/abc123"

    def setUp(self):
        self.live = export.read_live(SNAPSHOT)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def cli(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            return export.main(list(args)), out.getvalue(), err.getvalue()

    def test_an_empty_page_gets_config_page_with_the_url_and_the_defaults_title(self):
        code, _, err = self.cli("--defaults", "--page-url", self.URL, "--out", str(self.tmp / "d"))
        self.assertEqual((code, err), (0, ""))
        page = json.loads((self.tmp / "d" / "docs" / "config" / "page.json").read_text())
        defaults = json.loads((DEFAULTS_DIR / "config.json").read_text())["page"]
        self.assertEqual(page, {**defaults, "artifactUrl": self.URL})
        self.assertEqual(export.validate_doc("config", page), [])
        code, _, _ = self.cli("--defaults", "--out", str(self.tmp / "plain"))  # without the flag the defaults are as they were
        self.assertEqual(json.loads((self.tmp / "plain" / "docs" / "config" / "page.json").read_text()), defaults)

    def test_a_draft_page_whose_config_page_has_an_empty_url_is_given_the_url_and_keeps_its_own_fields(self):
        live = {**self.live, "config": {**self.live["config"], "page": {"title": "Draft review", "artifactUrl": "", "extra": "kept"}}}
        docs, notes = export.upgrade_docs(live, self.URL)
        self.assertEqual(docs["config"]["page"], {"title": "Draft review", "artifactUrl": self.URL, "extra": "kept"})
        self.assertEqual([n for n in notes if "config/page" in n], [])  # an empty URL is nothing to replace
        none, _ = export.upgrade_docs(live)  # no URL given: the page's document is left alone, as before
        self.assertNotIn("page", none["config"])

    def test_a_different_url_is_replaced_with_a_note_and_the_same_url_writes_nothing(self):
        saved = self.live["config"]["page"]["artifactUrl"]
        self.assertTrue(saved.startswith("https://"))
        docs, notes = export.upgrade_docs(self.live, self.URL)
        self.assertEqual(docs["config"]["page"], {**self.live["config"]["page"], "artifactUrl": self.URL})
        self.assertIn(f"config/page: artifactUrl {saved} is replaced by {self.URL}", notes)
        again, quiet = export.upgrade_docs(self.live, saved)
        self.assertNotIn("page", again["config"])
        self.assertEqual([n for n in quiet if "config/page" in n], [])

    def test_a_live_page_with_no_config_page_gets_the_defaults_document_with_the_url(self):
        live = {**self.live, "config": {"prompt": self.live["config"]["prompt"]}}
        docs, _ = export.upgrade_docs(live, self.URL)
        defaults = json.loads((DEFAULTS_DIR / "config.json").read_text())["page"]
        self.assertEqual(docs["config"]["page"], {**defaults, "artifactUrl": self.URL})

    def test_the_cli_refuses_a_url_that_is_not_http_and_the_flag_without_defaults(self):
        code, _, err = self.cli("--defaults", "--page-url", "claude.ai/artifact/x", "--out", str(self.tmp / "bad"))
        self.assertEqual(code, 2)
        self.assertIn("is not an http(s) URL", err)
        self.assertFalse((self.tmp / "bad").exists())
        with contextlib.redirect_stderr(io.StringIO()) as usage, self.assertRaises(SystemExit):
            export.main(["--check", str(SAMPLE_REVIEW), "--page-url", self.URL])
        self.assertIn("--page-url goes with --defaults", usage.getvalue())
        code, out, _ = self.cli("--defaults", "--live", str(SNAPSHOT), "--page-url", self.URL, "--out", str(self.tmp / "up"))
        self.assertEqual(code, 0)
        self.assertIn("note: config/page: artifactUrl", out)
        writes = json.loads((self.tmp / "up" / "writes.json").read_text())
        self.assertIn(("config", "page"), [(w["collection"], w["doc_id"]) for w in writes])

    def test_schema_md_and_skill_md_say_publish_sets_the_url_and_the_page_cannot_read_it(self):
        text = " ".join(SCHEMA_MD.read_text(encoding="utf-8").split())
        for phrase in ("`artifactUrl` (optional string: the artifact's own URL)", "A page cannot read its own URL",
                       "export.py --defaults --page-url URL", "`Page: <url>`"):
            self.assertIn(phrase, text)
        skill = " ".join(SKILL_MD.read_text(encoding="utf-8").split())
        self.assertIn("this page's artifact URL, which the page cannot read itself; the prompt's head prints it", skill)


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

    # ---- R17: the plan's work items and the packets of the five real runs

    PLAN = {  # key: (work items, step plans, loops per item, steps planned, steps executed, done implement visits)
        "luna1": (1, 2, [2], 5, 5, 7), "hello-1161": (1, 1, [1], 2, 2, 2), "hello-1180": (1, 1, [1], 1, 1, 1),
        "hello-1190a": (1, 1, [1], 1, 1, 1), "hello-1190b": (2, 2, [1, 1], 2, 2, 2)}

    def test_the_work_items_and_steps_loop_of_each_real_run(self):
        for key, (count, plans, loops, planned, executed, done) in self.PLAN.items():
            with self.subTest(run=key):
                run = self.run_doc(key)
                items = run["workItems"]
                self.assertEqual((len(items), sum(i["stepPlans"] for i in items), [i["loops"] for i in items]),
                                 (count, plans, loops))
                self.assertEqual((run["stepsPlanned"], run["stepsExecuted"]), (planned, executed))
                self.assertEqual(sum(i["implementVisits"]["done"] for i in items), done)
                self.assertNotIn("workItems", run["unmeasured"])
                by_action = {row["action"]: row for row in run["stages"]}
                for item in items:  # every executed step names an accepted implement visit of its own item
                    self.assertEqual(item["stepsPlanned"], len(item["steps"]))
                    self.assertEqual(item["stepsExecuted"], sum(1 for s in item["steps"] if s["action"]))
                    for step in item["steps"]:
                        if step["action"]:
                            row = by_action[step["action"]]
                            self.assertEqual((row["stage"], row["outcome"], row["workitem"], row["step"]),
                                             ("implement", "done", item["id"], step["id"]))

    def test_luna_1_16_1_went_through_the_steps_loop_twice_and_built_all_five_steps_of_its_second_plan(self):
        run = self.run_doc("luna1")
        item = run["workItems"][0]
        self.assertEqual((item["id"], item["origin"], item["revises"], item["repeats"]), ("W1", "plan", 1, 0))
        self.assertEqual(item["implementVisits"], {"done": 7, "repeat": 0, "revise": 1, "replan": 0, "blocked": 0})
        self.assertEqual([s["id"] for s in item["steps"]], ["S1", "S2", "S3", "S4", "S5"])
        marks = [(r["loop"], r["step"], r["outcome"]) for r in run["stages"] if r["stage"] == "implement"]
        self.assertEqual(marks, [(1, "S1", "done"), (1, "S2", "done"), (1, "S3", "revise")] + [
            (2, f"S{n}", "done") for n in range(1, 6)])
        self.assertTrue(item["steps"][2]["truncated"] and len(item["steps"][2]["task"]) == 200)

    def test_hello_1_19_0_second_run_added_a_second_work_item_by_replan(self):
        first, second = self.run_doc("hello-1190b")["workItems"]
        self.assertEqual((first["origin"], second["origin"]), ("plan", "replan"))
        self.assertEqual(second["title"], "Correct the system-test plan so ShipLoop can judge ST-1")

    def test_packets_are_not_in_the_committed_files_and_every_visit_with_a_packet_file_has_a_document(self):
        for name, key in EVIDENCE_RUNS.items():
            with self.subTest(file=name):
                self.assertNotIn("packets", self.bundles[name]["docs"])
                rows = self.run_doc(key)["stages"]
                self.assertTrue(all(("packetDoc" in r) == ("packetBytes" in r) for r in rows))
                self.assertTrue(all(r["packetDoc"] is True for r in rows if "packetDoc" in r))
        self.assertEqual(sum("packetDoc" in r for r in self.run_doc("luna1")["stages"]), 39)
        self.assertEqual(sum("packetDoc" in r for r in self.run_doc("hello-1190b")["stages"]), 47)  # 7 visits were skipped


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
            self.assertIn("give one of RUN_DIR, --defaults, --stages, --check FILE or --docs FILE", err.getvalue())


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
        # o16 has neither (unknown cause), o17 is the owner's choice, o23 and o30 wait for one; o34 is fixed since R22c
        # (the harness reads Claude's tool blocks, c7a8187d to 4e656d23), so it no longer warns
        self.assertEqual(warned, ["o16:effect", "o16:option", "o17:effect", "o23:option", "o30:option"])

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
        self.assertIn("export.py --defaults --live FILE --page-url URL --out DIR", self.skill)
        self.assertIn("`--defaults --page-url URL --out DIR`", self.skill)
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
            '{stage:"plan",outcome:"done",min:4},{stage:"get-next-work-item",outcome:"done",min:0,skipped:true},'
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
            {"stage": "plan", "outcome": "done", "min": 4}, {"stage": "get-next-work-item", "outcome": "done", "min": 0},
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
            'chips=byClass("seqdetail","chip").filter(function(c){return c.tagName==="button";}).map(function(c){return c.textContent;}),sel=REG.seqscroll.innerHTML.indexOf("sq-sel")>0;'
            'byClass("seqdetail","btn")[0].onclick();var b=textOf("seqdetail");'
            'setCol(1);byClass("seqdetail","btn")[2].onclick();[a,btns,chips,sel,b,textOf("seqdetail"),pickedCol]', setup=SAMPLE_SETUP)
        self.assertIn("Visit 2: Spec", out[0])
        self.assertIn("blocked (marked B)", out[0])
        self.assertIn("25 min, 83.3% of elapsed", out[0])
        self.assertEqual(out[1], ["Previous visit:false", "Next visit:true", "Close:false"])
        self.assertEqual(out[2], ["#1 First finding"])  # the finding marked at the Specify phase for this run
        self.assertTrue(out[3])
        self.assertIn("Visit 1: Intake", out[4])  # Previous
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
                     "Refusals13refusal lines or failed ShipLoop commands"):
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



# ---------------------------------------------------------------- R17: the plan and execution panel and the packet box

# A fake database for the page: it records every call so a test can say what the page asked for and what it subscribed to.
# get() and writeText() answer with a thenable that resolves at once, because page_probe evaluates synchronously.
FAKE_DB = """
var DB_CALLS=[],PACKET_DOCS={};
function sync(v,fail){return {then:function(ok,no){if(fail){if(no)no(v);}else if(ok)ok(v);return this;}};}
db={doc:function(path){return {get:function(){DB_CALLS.push(["get",path]);var d=PACKET_DOCS[path];
        return sync({exists:d!==undefined,data:function(){return d;}});},
      onSnapshot:function(){DB_CALLS.push(["doc-snapshot",path]);}};},
    collection:function(name){var q={orderBy:function(){return q;},onSnapshot:function(){DB_CALLS.push(["subscribe",name]);},
        doc:function(){return {};},add:function(){return sync();}};return q;}};
live=true;
"""

# A run with a revise in W1, a replan-added W2 and a planned step that was never executed, as the exporter writes it.
PLAN_RUN = {
    "key": "pr", "name": "Plan run", "order": 1, "release": "r", "time": "t", "imp": "i", "wallMin": 30,
    "phases": ["done", "done", "done", "running", "none", "none", "none", "none"],
    "stages": [
        {"stage": "plan", "outcome": "done", "min": 3, "action": "nav-p", "packetBytes": 40, "packetDoc": True},
        {"stage": "step-plan", "outcome": "done", "min": 2, "action": "nav-s1", "workitem": "W1", "loop": 1, "packetDoc": True},
        {"stage": "implement", "outcome": "done", "min": 5, "action": "nav-i1", "workitem": "W1", "loop": 1, "step": "S1", "packetDoc": True},
        {"stage": "implement", "outcome": "revise", "min": 4, "action": "nav-i2", "workitem": "W1", "loop": 1, "step": "S2"},
        {"stage": "step-plan", "outcome": "done", "min": 2, "action": "nav-s2", "workitem": "W1", "loop": 2},
        {"stage": "implement", "outcome": "done", "min": 6, "action": "nav-i3", "workitem": "W1", "loop": 2, "step": "S1"},
        {"stage": "implement", "outcome": "done", "min": 6, "action": "nav-i4", "workitem": "W2", "loop": 1, "step": "S1"}],
    "workItems": [
        {"id": "W1", "title": "First <b>item</b>", "origin": "plan", "stepPlans": 2, "loops": 2, "revises": 1, "repeats": 0,
         "implementVisits": {"done": 2, "repeat": 0, "revise": 1, "replan": 0, "blocked": 0}, "stepsPlanned": 1, "stepsExecuted": 1,
         "steps": [{"id": "S1", "task": "do S1 <script>alert(1)</script>", "action": "nav-i3"}]},
        {"id": "W2", "title": "Corrective", "origin": "replan", "stepPlans": 1, "loops": 1, "revises": 0, "repeats": 0,
         "implementVisits": {"done": 1, "repeat": 0, "revise": 0, "replan": 0, "blocked": 0}, "stepsPlanned": 2, "stepsExecuted": 1,
         "steps": [{"id": "S1", "task": "do S1", "action": "nav-i4"}, {"id": "S2", "task": "x" * 200, "truncated": True, "action": None}]}],
    "stepsPlanned": 3, "stepsExecuted": 2, "unmeasured": {}}


def plan_setup(run: dict = PLAN_RUN, extra: str = "") -> str:
    return ("data.runs=[" + json.dumps(run) + "];data.bc=[];Object.keys(loaded).forEach(function(k){loaded[k]=true;});"
            + FAKE_DB + extra + "renderAll();")


class PlanPanelTests(unittest.TestCase):
    """R17: the Plan and execution panel on step 1: one row per work item, its steps loop badge and one cell per planned step."""

    def model(self, run: dict) -> dict:
        return run_logic("planModel(" + json.dumps(run) + ")")

    def test_planmodel_reads_the_headline_numbers_the_badges_the_counts_and_the_cells_of_a_real_run(self) -> None:
        luna = self.model(evidence_run("luna1"))
        item = luna["items"][0]
        self.assertTrue(luna["measured"])
        self.assertEqual((luna["headline"], luna["line"]), ("1 work item, 2 passes through the steps loop", "Steps planned 5, executed 5"))
        self.assertEqual((item["badge"], item["added"]), ("steps loop x2", ""))
        self.assertEqual(item["counts"], "2 step plans, 8 implement visits: 7 done, 1 revise, 0 repeat")
        self.assertEqual([(c["id"], c["state"]) for c in item["cells"]], [(f"S{n}", "executed") for n in range(1, 6)])
        rows = evidence_run("luna1")["stages"]
        done = [i + 1 for i, r in enumerate(rows) if r["stage"] == "implement" and r["outcome"] == "done"][-5:]
        self.assertEqual([c["visit"] for c in item["cells"]], done)  # the visit each cell points at, 1-based
        hello = self.model(evidence_run("hello-1190b"))
        self.assertEqual([(i["badge"], i["added"]) for i in hello["items"]],
                         [("steps loop once", ""), ("steps loop once", "added by replan")])
        self.assertEqual(hello["headline"], "2 work items, 2 passes through the steps loop")

    def test_a_planned_step_no_visit_executed_is_never_and_a_run_whose_pairing_is_unknown_says_unknown(self) -> None:
        model = self.model(PLAN_RUN)
        w2 = model["items"][1]
        self.assertEqual([(c["id"], c["state"], c["visit"]) for c in w2["cells"]], [("S1", "executed", 7), ("S2", "never", None)])
        self.assertEqual(w2["stepsText"], "1 of 2 planned steps executed")
        self.assertEqual(model["line"], "Steps planned 3, executed 2")
        ask = json.loads(json.dumps(PLAN_RUN))
        for item in ask["workItems"]:
            del item["stepsExecuted"]
            for step in item["steps"]:
                step.pop("action", None)
        del ask["stepsExecuted"]
        ask["unmeasured"] = {"stepsExecuted": "this run's delegation is ask-agent"}
        unknown = self.model(ask)
        self.assertEqual({c["state"] for i in unknown["items"] for c in i["cells"]}, {"unknown"})
        self.assertEqual(unknown["line"], "Steps planned 3, executed not measured (this run's delegation is ask-agent)")
        self.assertIn("which visit ran each is not recorded", unknown["items"][0]["stepsText"])

    def test_a_run_with_no_work_items_record_says_not_measured_with_the_reason_never_zero(self) -> None:
        for run, why in (({"unmeasured": {"workItems": "the plan visit was recorded by the E2E seed"}},
                          "the plan visit was recorded by the E2E seed"),
                         ({}, "this run's document has no work item record; export the run again"),
                         ({"workItems": None, "unmeasured": {"workItems": "r"}}, "r")):
            model = self.model(run)
            self.assertEqual((model["measured"], model["why"], model["items"]), (False, why, []))
        out = page_probe('[textOf("plancard"),REG.plancard.hidden]', setup=with_run("hello-1190b").replace(
            'renderAll();', 'delete data.runs[0].workItems;delete data.runs[0].stepsPlanned;renderAll();'))
        self.assertEqual(out[0].split("Plan and execution")[1][:40], "Not measured: this run's document has no")
        self.assertFalse(out[1])
        self.assertNotRegex(out[0], r"Steps planned|steps loop x?0")

    def test_the_badge_reads_once_for_one_pass_x_n_from_two_and_never_a_bare_zero(self) -> None:
        self.assertEqual(run_logic('[loopsBadge(1),loopsBadge(2),loopsBadge(7),loopsBadge(0),loopsBadge(undefined),loopsBadge("2")]'),
                         ["steps loop once", "steps loop x2", "steps loop x7", "steps loop not started",
                          "steps loop not recorded", "steps loop not recorded"])
        self.assertEqual(run_logic('itemCounts({stepPlans:1,implementVisits:{done:1,blocked:2,replan:1,repeat:3}})'),
                         "1 step plan, 7 implement visits: 1 done, 0 revise, 3 repeat, 1 replan, 2 blocked")
        self.assertEqual(run_logic('itemCounts({})'), "step plans not recorded, implement visits not recorded")

    def test_the_panel_draws_one_row_per_item_a_filled_cell_per_executed_step_and_an_outlined_one_for_a_step_never_run(self) -> None:
        out = page_probe(
            '[textOf("plancard"),byClass("plancard","pl-item").length,byClass("plancard","pl-cell").map(function(c){return c.className+"|"+c.textContent;}),'
            'byClass("plancard","chip").map(function(c){return c.textContent;}),byClass("plancard","pl-tasks").map(function(o){return o.textContent;}),'
            'REG.kpis.children.length,REG.plancard.hidden]', setup=plan_setup())
        text, rows, cells, chips, tasks, kpis, hidden = out
        self.assertIn("Plan and execution", text)
        self.assertEqual((rows, kpis, hidden), (2, 6, False))  # still six cards: the panel is not a seventh
        self.assertIn("2 work items, 3 passes through the steps loop", text)
        self.assertIn("Steps planned 3, executed 2", text)
        self.assertIn("2 step plans, 3 implement visits: 2 done, 1 revise, 0 repeat", text)
        self.assertEqual(cells, ["pl-cell executed|S1visit 6", "pl-cell executed|S1visit 7", "pl-cell never|S2not run"])
        self.assertEqual(chips, ["steps loop x2", "steps loop once", "added by replan"])
        self.assertIn("S2: " + "x" * 200 + " (cut at 200 characters) [never executed]", tasks[1])

    def test_a_step_task_and_a_title_with_markup_are_text_never_elements(self) -> None:
        out = page_probe('[textOf("plancard"),walk(REG.plancard,function(e){return e.tagName==="script"||e.tagName==="b";}).length,'
                         'byClass("plancard","pl-title")[0].textContent]', setup=plan_setup())
        self.assertIn("do S1 <script>alert(1)</script>", out[0])
        self.assertEqual((out[1], out[2]), (0, "W1: First <b>item</b>"))
        html = TEMPLATE.read_text(encoding="utf-8")
        panel = html[html.index("function renderPlan"):html.index("function packetBox")]
        self.assertNotIn("innerHTML", panel)  # built with createElement and textContent only

    def test_tapping_an_item_shades_its_columns_and_tapping_a_step_selects_the_visit_that_ran_it_or_says_never_executed(self) -> None:
        out = page_probe(
            'var cells=function(){return byClass("plancard","pl-cell");};'
            'byClass("plancard","pl-title")[0].onclick();var shaded=REG.seqscroll.innerHTML.split("sq-item").length-1,cap=textOf("seqcap");'
            'cells()[0].onclick();var a=[pickedCol,pickedItem,textOf("seqdetail").indexOf("Visit 6: Implement")>=0,textOf("seqdetail").indexOf("steps-loop pass 2")>=0];'
            'cells()[2].onclick();var b=[pickedItem,textOf("plancard").indexOf("Step S2 of W2 was never executed: no implement visit is recorded for it.")>=0];'
            'byClass("plancard","pl-title")[1].onclick();[shaded,cap,a,b,pickedItem,REG.seqscroll.innerHTML.split("sq-item").length-1]', setup=plan_setup())
        self.assertEqual(out[0], 5)  # the five visits of W1 are shaded (the picture has seven columns; W2's and the plan are not)
        self.assertIn("Shaded columns are the visits of work item W1.", out[1])
        self.assertEqual(out[2], [5, "W1", True, True])
        self.assertEqual(out[3], ["W2", True])
        self.assertEqual((out[4], out[5]), ("", 0))  # tapping the selected item (W2, chosen by its step) again clears the shading

    def test_the_picture_marks_columns_of_an_item_and_finds_the_column_of_a_visit(self) -> None:
        model = run_logic("(function(){var m=sequenceModel(" + json.dumps(PLAN_RUN) + ",{item:'W2'});"
                          "return {inItem:m.columns.map(function(c){return c.inItem;}),col:columnOfVisit(m,6),none:columnOfVisit(m,99)};})()")
        self.assertEqual(model["inItem"], [False] * 6 + [True])
        self.assertEqual((model["col"], model["none"]), (6, -1))
        skipped = {"stages": [{"stage": "a", "outcome": "done"}, {"stage": "b", "outcome": "done", "skipped": True},
                              {"stage": "c", "outcome": "done", "skipped": True}, {"stage": "d", "outcome": "done"}]}
        self.assertEqual(run_logic("[0,1,2,3,4].map(function(i){return columnOfVisit(sequenceModel(" + json.dumps(skipped) + ",{}),i);})"),
                         [0, 1, 1, 2, -1])  # two skipped visits in a row are one column
        svg = run_logic("sequenceSvg(sequenceModel(" + json.dumps(PLAN_RUN) + ",{item:'W1'}),-1)")
        self.assertEqual(svg.count('class="sq-item"'), 5)
        self.assertEqual(run_logic("sequenceSvg(sequenceModel(" + json.dumps(PLAN_RUN) + ",{}),-1)").count("sq-item"), 0)

    def test_a_column_detail_names_its_work_item_loop_and_step_and_a_run_without_them_is_unchanged(self) -> None:
        out = page_probe('setCol(5);textOf("seqdetail")', setup=plan_setup())
        self.assertIn("Work itemW1, steps-loop pass 2", out)
        self.assertIn("StepS1 (the step this packet named)", out)
        plain = page_probe('setCol(1);textOf("seqdetail")', setup=SAMPLE_SETUP)
        for absent in ("Work item", "Step", "Packet"):
            self.assertNotIn(absent, plain.replace("Previous visit", "").replace("Next visit", "").replace("Stages", ""), absent)
        self.assertEqual(page_probe('setCol(1);byClass("seqdetail","pkt").length', setup=SAMPLE_SETUP + FAKE_DB), 0)

    def test_template_places_the_panel_below_the_six_cards_and_above_the_picture(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8")
        self.assertLess(html.index('id="kpis"'), html.index('id="plancard"'))
        self.assertLess(html.index('id="plancard"'), html.index('id="seqcard"'))
        self.assertEqual(run_logic("kpiCards({},[]).length"), 6)


class PacketBoxTests(unittest.TestCase):
    """R17: a tapped visit's Packet box loads its document on demand, with one get, and the page never subscribes to packets."""

    DOC = {"run": "pr", "action": "nav-i1", "stage": "implement", "bytes": 200_000, "shownBytes": 149_990,
           "sha256": "ab12cd34ef56" + "0" * 52, "text": "# Packet\nline <script>alert(1)</script>\n", "truncated": True}

    def probe(self, expression: str, docs: dict | None = None, extra: str = "", stored_db: bool = True):
        setup = plan_setup(extra=("PACKET_DOCS=" + json.dumps(docs or {}) + ";") + extra)
        if not stored_db:
            setup = setup.replace("live=true;", "db=null;live=false;")
        return page_probe(expression, setup=setup)

    def test_the_packet_is_loaded_with_one_get_of_the_right_path_only_when_opened_and_never_again(self) -> None:
        out = self.probe(
            'setCol(2);var box=byClass("seqdetail","pkt")[0],before=DB_CALLS.slice(),closed=textOf("seqdetail").indexOf("# Packet");'
            'box.open=true;box.ontoggle();var once=DB_CALLS.slice();'
            'box.open=false;box.ontoggle();box.open=true;box.ontoggle();'
            'renderAll();var again=byClass("seqdetail","pkt")[0];var kept=again.open;'
            '[before,closed,once,DB_CALLS.length,kept,byClass("seqdetail","pkt-text")[0].textContent]',
            docs={"packets/pr--nav-i1": self.DOC})
        before, closed, once, calls, kept, text = out
        self.assertEqual((before, closed), ([], -1))  # nothing is read until the box is opened
        self.assertEqual(once, [["get", "packets/pr--nav-i1"]])
        self.assertEqual((calls, kept), (1, True))  # reopened and redrawn: still one get, and the box stays open
        self.assertEqual(text, self.DOC["text"])

    def test_the_box_shows_the_text_in_a_scroll_box_with_size_digest_and_the_truncation_note_and_never_as_markup(self) -> None:
        out = self.probe('setCol(2);var b=byClass("seqdetail","pkt")[0];b.open=true;b.ontoggle();'
                         '[textOf("seqdetail"),walk(REG.seqdetail,function(e){return e.tagName==="script";}).length,'
                         'byClass("seqdetail","pkt-text")[0].tagName,byClass("seqdetail","pkt-text")[0].attrs.tabindex]',
                         docs={"packets/pr--nav-i1": self.DOC})
        self.assertIn("195.3 KB, sha256 ab12cd34ef56; truncated: showing the first 149,990 of 200,000 bytes", out[0])
        self.assertIn("line <script>alert(1)</script>", out[0])
        self.assertEqual(out[1:], [0, "pre", "0"])
        css = TEMPLATE.read_text(encoding="utf-8").split("</style>")[0]
        rule = re.search(r"\.pkt-text\{([^}]*)\}", css).group(1)
        for needed in ("max-height", "overflow:auto", "white-space:pre", "font-family:var(--mono)"):
            self.assertIn(needed, rule)
        self.assertEqual(run_logic('[packetMeta({bytes:100,sha256:"abcdef0123456789"}),packetMeta({}),'
                                   'packetMeta({truncated:true,bytes:300000})]'),
                         ["100 B, sha256 abcdef012345", "", "293 KB; truncated: showing the first part of 300,000 bytes"])

    def test_a_document_that_does_not_exist_reads_packet_not_uploaded_and_a_failed_read_says_so(self) -> None:
        out = self.probe('setCol(2);var b=byClass("seqdetail","pkt")[0];b.open=true;b.ontoggle();textOf("seqdetail")')
        self.assertIn("packet not uploaded for this run", out)
        failed = self.probe('db.doc=function(p){return {get:function(){return sync({code:"unavailable"},true);}};};'
                            'setCol(2);var b=byClass("seqdetail","pkt")[0];b.open=true;b.ontoggle();textOf("seqdetail")')
        self.assertIn("Could not read the packet.", failed)
        self.assertNotIn("not uploaded", failed)

    def test_without_the_database_or_a_packet_document_the_box_prints_nothing(self) -> None:
        self.assertEqual(self.probe('setCol(2);byClass("seqdetail","pkt").length', stored_db=False), 0)
        # visit 4 (the revise) has no packetDoc: no box
        self.assertEqual(self.probe('setCol(3);byClass("seqdetail","pkt").length'), 0)
        self.assertEqual(self.probe('setCol(2);byClass("seqdetail","pkt").length'), 1)

    def test_the_copy_button_writes_the_text_to_the_clipboard_from_its_click_and_a_failure_says_so(self) -> None:
        open_box = 'setCol(2);var b=byClass("seqdetail","pkt")[0];b.open=true;b.ontoggle();'
        docs = {"packets/pr--nav-i1": self.DOC}
        ok = self.probe(open_box + 'var copied=null;navigator.clipboard={writeText:function(t){copied=t;return sync();}};'
                        'var btn=byClass("seqdetail","btn").filter(function(x){return x.textContent==="Copy";})[0];btn.onclick();'
                        '[copied,textOf("seqdetail").indexOf("Copied.")>=0]', docs)
        self.assertEqual(ok, [self.DOC["text"], True])
        rejected = self.probe(open_box + 'navigator.clipboard={writeText:function(t){return sync("no",true);}};'
                              'byClass("seqdetail","btn").filter(function(x){return x.textContent==="Copy";})[0].onclick();'
                              'textOf("seqdetail").indexOf("Could not copy")>=0', docs)
        self.assertTrue(rejected)
        absent = self.probe(open_box + 'byClass("seqdetail","btn").filter(function(x){return x.textContent==="Copy";})[0].onclick();'
                            'textOf("seqdetail").indexOf("Could not copy")>=0', docs)  # navigator has no clipboard in the stub
        self.assertTrue(absent)

    def test_the_page_never_subscribes_to_the_packets_collection_and_reads_it_by_get_only(self) -> None:
        out = self.probe('subscribe();DB_CALLS.map(function(c){return c[1];})')
        self.assertEqual(sorted(out), sorted(["runs", "observations", "actions", "backchain", "expectations", "config", "reviews"]))
        page = script_text()
        self.assertNotIn('collection("packets")', page)
        self.assertNotIn('["packets"', page)
        self.assertEqual(re.findall(r'db\.doc\("packets/"\+id\)\.get\(\)', page), ['db.doc("packets/"+id).get()'])
        self.assertNotIn("onSnapshot", page[page.index("function loadPacket"):page.index("function fillPacket")])

    def test_the_template_has_no_packet_data_and_the_page_asks_for_no_collection_the_contract_lacks(self) -> None:
        self.assertIn("**`packets/", SCHEMA_MD.read_text(encoding="utf-8"))
        self.assertEqual(run_logic('[packetId({key:"k"},{packetDoc:true,action:"nav-a"}),packetId({key:"k"},{action:"nav-a"}),'
                                   'packetId({},{packetDoc:true,action:"nav-a"})]'), ["k--nav-a", "", ""])


# ---------------------------------------------------------------- R18: the run option planning_review

STATE_FIXTURES = ROOT / "test" / "fixtures" / "run-review"
PLANNING_NONE_TEXT = "planning stages skipped by design (planning_review none)"
PLANNING_STAGES = ("spec", "test-strategy", "plan", "step-plan", "test-spec")
# The planning stages, then the stages after them whose results start a child under none (the last item's carry-forward and
# system-test-author). (action, stage, minutes after T0 when accepted, outcome), as in ACCEPTS.
PLANNING_ACCEPTS = [("intake", "intake", 5, "done"), ("spec", "spec", 15, "done"), ("test-strategy", "test-strategy", 35, "done"),
                    ("plan", "plan", 95, "done"), ("get-next-work-item", "get-next-work-item", 97, "done"),
                    ("step-plan", "step-plan", 127, "done"), ("test-spec", "test-spec", 140, "done"),
                    ("carry-forward", "carry-forward", 180, "done"), ("system-test-author", "system-test-author", 200, "done")]
# improve/<child>/ of a run by the mode it started with, (passes, bind time, receipt time), as the engine's own walk of its
# pure navigator leaves them (the two state fixtures): stage starts a child after each planning result, none starts none there.
STAGE_CHILDREN = {"spec": (2, 16, 24), "test-strategy": (1, 36, 41), "plan": (3, 96, 110),
                  "carry-forward": (2, 172, 178.5), "system-test-author": (1, 192, 195)}
NONE_CHILDREN = {"carry-forward": (2, 172, 178.5), "system-test-author": (1, 192, 195)}


def real_state(mode: str) -> dict:
    """The shiploop-state record of a genuine state.md: `shiploop init --planning-review <mode>` of the plugin's own CLI at
    45f163d0, advanced to its first inner stage on its pure navigator with no model; its two paths are normalised and the stage
    name is the engine's current get-next-work-item (that release wrote select-work, which ShipLoop now refuses)."""
    return export._record(STATE_FIXTURES / f"state-{mode}.md")


def planning_run(root: Path, mode: str | None, children: dict, **state) -> Path:
    """A run whose state.md records the option the way the engine does (the value is read from the genuine state of `mode`;
    None leaves the key out, as a run before ShipLoop 1.22.0 does) and whose improve/ directory holds only `children`: make_run's
    one child, at plan, is removed first. Extra keyword arguments are written into the state record as they are."""
    for name, *_ in PLANNING_ACCEPTS:
        IDS.setdefault(name, f"nav-{hashlib.sha256(name.encode()).hexdigest()[:32]}")
    out = make_run(root, PLANNING_ACCEPTS, loops=False)
    run = run_dir_of(out)
    shutil.rmtree(run / "improve")
    for name, (passes, bind_at, receipt_at) in children.items():
        make_improve_child(run, IDS[name], passes, bind_at, receipt_at)
    set_state(out, planning_review=real_state(mode)["planning_review"] if mode else None)
    if state:
        set_state(out, **state)
    return out


class PlanningReviewExportTest(unittest.TestCase):
    """R18: the run-level planning_review option, exported as state.md wrote it and never defaulted, and what a none run's
    Improve numbers mean. The fixtures take the option's value from a genuine state.md of each mode."""

    KEY = RunReviewTest.KEY

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def build(self, mode: str | None, children: dict | None = None, **state) -> tuple[dict, list[str]]:
        out = planning_run(Path(tempfile.mkdtemp(dir=self.tmp)), mode, STAGE_CHILDREN if children is None else children, **state)
        docs, facts = export.build_run(out)
        run = docs["runs"][self.KEY]
        self.assertEqual(export.validate_doc("runs", run), [])
        return run, facts

    def test_a_genuine_state_md_of_each_mode_carries_the_key_the_exporter_reads(self):
        for mode in ("stage", "none"):
            state = real_state(mode)
            self.assertEqual(state["planning_review"], mode)
            self.assertEqual(export._recorded_option(state, "planning_review"), mode)
        self.assertEqual(set(real_state("stage")), set(real_state("none")))  # one key set; the option is a value, not a shape
        # what each mode did in the engine's own walk: stage parked a child after spec, test-strategy and plan, none none
        self.assertEqual((len(real_state("stage")["improve_results"]), len(real_state("none")["improve_results"])), (3, 0))
        for mode in ("stage", "none"):  # the current engine resolves the Improve card at init in both modes
            self.assertEqual(real_state(mode)["improve_skill"], "/plugin/skills/improve/SKILL.md", mode)

    def test_the_option_is_exported_as_state_md_wrote_it_and_is_not_recorded_when_the_key_is_absent(self):
        for written, shown in (("stage", "stage"), ("none", "none"), ("once", "once"), (2, "2"), (None, "not recorded")):
            with self.subTest(written=written):
                run, facts = self.build(None, planning_review=written)
                self.assertEqual(run["planningReview"], shown)
                self.assertIn(f"- Planning review option (state.md): {shown}", facts)
        bare, _ = self.build(None)  # the fixture's state has no key at all: every run before 1.22.0
        self.assertEqual(bare["planningReview"], "not recorded")

    def test_a_none_run_keeps_the_numbers_its_improve_directories_hold_and_says_planning_stages_were_skipped_by_design(self):
        run, facts = self.build("none", NONE_CHILDREN)
        self.assertEqual((run["planningReview"], run["improveScope"]), ("none", PLANNING_NONE_TEXT))
        self.assertEqual((run["improvePasses"], run["improveMin"], run["imp"]), (3, 9.5, "2 children, 3 review passes"))
        self.assertEqual([r["stage"] for r in run["stages"] if "improve" in r], ["carry-forward", "system-test-author"])
        for row in run["stages"]:
            if row["stage"] in PLANNING_STAGES:
                self.assertNotIn("improve", row, row["stage"])  # no child by design: a row never gets an improve map
        self.assertEqual(next(f for f in facts if f.startswith("- Improve:")),
                         "- Improve: 2 children, 3 review passes; most passes in one child: 2; 9.5 min bind to receipt; "
                         + PLANNING_NONE_TEXT)
        self.assertIn("- Planning review option (state.md): none", facts)

    def test_a_none_run_that_has_not_reached_a_later_child_keeps_its_measured_zeros_and_the_scope(self):
        run, facts = self.build("none", {})
        self.assertEqual((run["improvePasses"], run["improveMin"], run["imp"]), (0, 0, "0 children"))  # what the directories give
        self.assertEqual(run["improveScope"], PLANNING_NONE_TEXT)
        self.assertTrue(next(f for f in facts if f.startswith("- Improve:")).endswith("; " + PLANNING_NONE_TEXT))

    def test_a_stage_run_an_unknown_value_and_a_run_with_no_record_claim_nothing_about_improve(self):
        """Guard (it passes before the change too): the Improve numbers and the facts line of these runs do not move."""
        for label, mode, extra in (("stage", "stage", {}), ("not recorded", None, {}), ("unknown", None, {"planning_review": "once"})):
            with self.subTest(option=label):
                run, facts = self.build(mode, **extra)
                self.assertNotIn("improveScope", run)
                self.assertEqual((run["improvePasses"], run["improveMin"]), (9, 36.5))
                self.assertEqual(next(f for f in facts if f.startswith("- Improve:")),
                                 "- Improve: 5 children, 9 review passes; most passes in one child: 3; 36.5 min bind to receipt")
                self.assertEqual([r["stage"] for r in run["stages"] if "improve" in r],
                                 ["spec", "test-strategy", "plan", "carry-forward", "system-test-author"])
                self.assertNotIn("by design", json.dumps(run) + "\n".join(facts))

    def test_the_contract_types_both_fields_documents_them_and_states_the_bundle_convention(self):
        base = {"key": "k", "name": "n", "order": 1, "release": "r", "phases": ["done"], "time": "t", "imp": "i"}
        self.assertEqual(export.validate_doc("runs", dict(base, planningReview="none", improveScope="x")), [])
        problems = "\n".join(export.validate_doc("runs", dict(base, planningReview=1, improveScope=True)))
        self.assertIn("planningReview: expected a string", problems)
        self.assertIn("improveScope: expected a string", problems)
        schema = " ".join(SCHEMA_MD.read_text(encoding="utf-8").split())
        for phrase in ("`planningReview`", "`improveScope`", "`not recorded` when the key is absent", PLANNING_NONE_TEXT,
                       "no Improve at planning stages (planning_review none)", "A bundle named for a run holds that run's reviews",
                       "`general.review.json` holds the findings that belong to no single run"):
            self.assertIn(phrase, schema)
        self.assertIn("`test/shiploop_e2e/evidence/general.review.json`", " ".join(SKILL_MD.read_text(encoding="utf-8").split()))

    def test_the_exporter_and_the_page_know_the_modes_and_planning_stages_the_engine_registers(self):
        path = ROOT / "skills" / "shiploop" / "scripts" / "shiploop_stage_spec.py"
        spec = importlib.util.spec_from_file_location("run_review_selected_stage_spec_3", path)
        stage_spec = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = stage_spec
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(stage_spec)
        # a mode the engine adds that the exporter and the page were not written for fails here instead of reading silently
        self.assertEqual(tuple(stage_spec.PLANNING_REVIEW_MODES), ("stage", export.PLANNING_NONE))
        self.assertEqual(set(run_logic("PLANNING_REVIEW_STAGES")), set(stage_spec.PLANNING_CHOICE_STAGES))
        self.assertEqual(set(PLANNING_STAGES), set(stage_spec.PLANNING_CHOICE_STAGES))
        self.assertFalse(stage_spec.reviewed_stages("none") & stage_spec.PLANNING_CHOICE_STAGES)


def mode_page(run: dict) -> str:
    """Page setup that shows one exported run, with one phase document so the run header is drawn."""
    return ("data.runs=[" + json.dumps(run) + "];data.bc=[];data.exp={'phase-0':{kind:'phase',order:0,title:'Understand',short:'Intake',"
            "text:'Understand the request.'}};Object.keys(loaded).forEach(function(k){loaded[k]=true;});renderAll();")


class PlanningReviewPageTests(unittest.TestCase):
    """R18: the run header, its chip, the Improve card and a planning visit's detail, over run documents the exporter wrote
    for a none run, a stage run, a run with no record and a run with a value the page does not know."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()

        def doc(mode: str | None, children: dict, **state) -> dict:
            out = planning_run(Path(tempfile.mkdtemp(dir=cls.tmp.name)), mode, children, **state)
            return export.build_run(out)[0]["runs"][RunReviewTest.KEY]

        cls.runs = {"none": doc("none", NONE_CHILDREN), "bare": doc("none", {}), "stage": doc("stage", STAGE_CHILDREN),
                    "absent": doc(None, STAGE_CHILDREN), "unknown": doc(None, STAGE_CHILDREN, planning_review="once")}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def card(self, run: dict, key: str = "improve") -> dict:
        return next(c for c in run_logic("kpiCards(%s, [])" % json.dumps(run)) if c["key"] == key)

    def details(self, run: dict) -> dict:
        """{stage: {label: text}} of the detail of every column of the picture."""
        rows = run_logic("(function(r){var m=sequenceModel(r,{});return m.columns.map(function(c,k){"
                         "return {stage:c.stage,lines:columnDetail(m,k,r,[]).lines};});})(%s)" % json.dumps(run))
        return {row["stage"]: dict(row["lines"]) for row in rows}

    def test_the_header_line_names_a_recorded_mode_and_prints_nothing_for_an_absent_or_not_recorded_one(self):
        none, stage, absent, unknown = (self.runs[k] for k in ("none", "stage", "absent", "unknown"))
        lines = run_logic("(function(a){return a.map(headerFacts);})(%s)" % json.dumps([none, stage, absent, unknown]))
        self.assertTrue(lines[0].endswith(" | 2 children, 3 review passes | planning review: none"), lines[0])
        self.assertTrue(lines[1].endswith(" | planning review: stage"), lines[1])
        self.assertTrue(lines[3].endswith(" | planning review: once"), lines[3])  # an unknown value is shown as written
        self.assertEqual(absent["planningReview"], "not recorded")
        self.assertNotIn("planning review", lines[2])  # not recorded: the run reads as it always did
        plain = 'release:"r",time:"t",imp:"i"'
        self.assertEqual(run_logic(f'[headerFacts({{{plain}}}), headerFacts({{{plain},planningReview:""}}),'
                                   f' headerFacts({{{plain},planningReview:"not recorded"}}), headerFacts({{{plain},planningReview:2}}),'
                                   f' headerFacts({{{plain},planningReview:"none"}})]'),
                         ["r | t | refusals not measured | glue not measured | i"] * 4
                         + ["r | t | refusals not measured | glue not measured | i | planning review: none"])

    def test_a_none_run_gets_a_chip_and_no_other_run_does(self):
        chips = run_logic('[modeChip({planningReview:"none"}), modeChip({planningReview:"stage"}), modeChip({planningReview:"once"}),'
                          ' modeChip({planningReview:"not recorded"}), modeChip({}), modeChip(null)]')
        self.assertEqual(chips[0]["text"], "no Improve at planning stages")
        self.assertIn("planning_review none", chips[0]["title"])
        self.assertIn("not comparable with a stage run's", chips[0]["title"])
        self.assertEqual(chips[1:], [None] * 5)

    def test_the_improve_card_of_a_none_run_keeps_its_measured_numbers_names_the_scope_and_prints_no_share(self):
        card = self.card(self.runs["none"])
        self.assertEqual((card["value"], card["note"], card["measured"]),
                         ("3 passes", "9.5 min; no Improve at planning stages (planning_review none)", True))
        self.assertNotIn("%", card["text"])
        none_yet = self.card(self.runs["bare"])  # measured zero children: by design, and never a bare 0%
        self.assertEqual((none_yet["value"], none_yet["note"]), ("0 passes", "0 min; no Improve at planning stages (planning_review none)"))
        self.assertNotRegex(none_yet["text"], r"\d%")

    def test_the_improve_card_says_the_scope_when_the_passes_or_the_minutes_of_a_none_run_were_not_measured(self):
        scope = "no Improve at planning stages (planning_review none)"
        unknown_passes, unknown_minutes = run_logic(
            '[kpiCards({planningReview:"none",unmeasured:{improvePasses:"1 of 2 Improve children has no terminal.json"}},[]),'
            ' kpiCards({planningReview:"none",improvePasses:3,wallMin:60,unmeasured:{improveMin:"a child lacks its receipt"}},[])]')
        passes, minutes = (next(c for c in cards if c["key"] == "improve") for cards in (unknown_passes, unknown_minutes))
        self.assertEqual((passes["value"], passes["measured"]), ("not measured", False))
        self.assertEqual(passes["note"], f"1 of 2 Improve children has no terminal.json; {scope}")
        self.assertEqual((minutes["value"], minutes["note"]), ("3 passes", f"minutes not measured: a child lacks its receipt; {scope}"))

    def test_a_stage_run_an_unknown_value_and_a_run_with_no_record_keep_the_card_they_always_had(self):
        """Guard (it passes before the change too): nothing about these runs' Improve card moves."""
        for key in ("stage", "absent", "unknown"):
            card = self.card(self.runs[key])
            self.assertEqual((card["value"], card["note"]), ("9 passes", "36.5 min, 18% of elapsed"), key)
        self.assertEqual(self.card({"stages": []})["note"], "no Improve record")

    def test_the_detail_of_a_planning_visit_in_a_none_run_says_improve_was_not_run_by_design_and_nothing_else_does(self):
        lines = self.details(self.runs["none"])
        for stage in PLANNING_STAGES:
            self.assertEqual(lines[stage]["Improve"], "not run by design (planning_review none)", stage)
        for stage in ("intake", "get-next-work-item"):
            self.assertNotIn("Improve", lines[stage], stage)  # no child here in any mode: nothing to say
        self.assertEqual((lines["carry-forward"]["Improve"], lines["system-test-author"]["Improve"]), ("2 passes, 6.5 min", "1 pass, 3 min"))
        for key in ("stage", "absent", "unknown"):
            other = self.details(self.runs[key])
            self.assertFalse([s for s, rows in other.items() if "by design" in rows.get("Improve", "")], key)
        self.assertEqual(self.details(self.runs["stage"])["spec"]["Improve"], "2 passes, 8 min")
        for stage in ("step-plan", "test-spec"):  # a stage run's planning visit with no child recorded claims nothing
            self.assertNotIn("Improve", self.details(self.runs["stage"])[stage])

    def test_a_skipped_or_seeded_planning_visit_and_a_visit_with_a_child_are_not_told_they_were_not_run_by_design(self):
        run = copy.deepcopy(self.runs["none"])
        by_stage = {row["stage"]: row for row in run["stages"]}
        by_stage["spec"]["skipped"] = True
        by_stage["test-strategy"]["seeded"] = True
        by_stage["plan"]["improve"] = {"passes": 1}  # a child that should not exist: shown as measured, never contradicted
        lines = self.details(run)
        self.assertNotIn("Improve", lines["spec"])
        self.assertNotIn("Improve", lines["test-strategy"])
        self.assertEqual(lines["plan"]["Improve"], "1 pass, minutes not measured")
        self.assertEqual(lines["step-plan"]["Improve"], "not run by design (planning_review none)")

    def test_the_page_draws_the_header_line_the_chip_the_improve_card_and_the_detail_of_a_planning_visit(self):
        probe = '[textOf("runfacts"),REG.runmode.hidden,REG.runmode.textContent,REG.runmode.title,textOf("kpis")]'
        none = page_probe(probe, setup=mode_page(self.runs["none"]))
        self.assertTrue(none[0].endswith(" | planning review: none"), none[0])
        self.assertEqual(none[1:3], [False, "no Improve at planning stages"])
        self.assertIn("planning_review none", none[3])
        self.assertIn("Improve3 passes9.5 min; no Improve at planning stages (planning_review none)", none[4])
        for key in ("stage", "absent"):
            other = page_probe(probe, setup=mode_page(self.runs[key]))
            self.assertTrue(other[1], key)  # the chip is hidden
            self.assertEqual((other[2], other[3]), ("", ""), key)
            self.assertIn("Improve9 passes36.5 min, 18% of elapsed", other[4], key)
        self.assertEqual(page_probe('textOf("runfacts").indexOf("planning review")', setup=mode_page(self.runs["absent"])), -1)
        detail = page_probe('setCol(1);textOf("seqdetail")', setup=mode_page(self.runs["none"]))
        self.assertIn("Visit 2: Spec", detail)
        self.assertIn("Improvenot run by design (planning_review none)", detail)
        self.assertNotIn("Improve", page_probe('setCol(0);textOf("seqdetail")', setup=mode_page(self.runs["none"])))


GENERAL_REVIEW = EVIDENCE_DIR / "general.review.json"
# phase-1's text in defaults/expectations.json before the ticked a26 was applied from the repo (expectation changes are prompt-only).
PHASE_1_TEXT = ("The model writes a spec and a test strategy from the notes, one stage at a time. The script accepts each only after "
                "its Improve review, and the spec is committed to docs/shiploop/.")


class GeneralReviewBundleTests(unittest.TestCase):
    """R18: findings that belong to no single run live in general.review.json. It passes the check, its option amends the Specify
    expectation with the SPEC's own carve-out wording (the defaults carry that text since the owner ticked it), and the page's
    prompt names the evidence directory and the ticked option."""

    @classmethod
    def setUpClass(cls):
        cls.docs = json.loads(GENERAL_REVIEW.read_text(encoding="utf-8"))["docs"]
        cls.finding, cls.option = cls.docs["observations"]["o44"], cls.docs["actions"]["a26"]
        # a26 is applied, so the bundle holds o44 fixed and a26 done; the page views below are of the rows while open.
        cls.open_docs = {c: {i: {**d, "status": "open"} for i, d in rows.items()} for c, rows in cls.docs.items()}
        cls.defaults = {e["key"]: e for e in json.loads((DEFAULTS_DIR / "expectations.json").read_text(encoding="utf-8"))}

    def test_it_passes_the_check_with_no_failure(self):
        # R22c added the findings of the 2026-10-08 runs; RoundRunFindingsTests pins the one warning left on purpose.
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = export.main(["--check", str(GENERAL_REVIEW)])
        self.assertEqual((code, err.getvalue()), (0, ""))
        self.assertRegex(out.getvalue().strip().splitlines()[-1], r"^check: ok \(\d+ documents, 0 failures, \d+ warnings?\)$")

    def test_its_finding_and_option_are_shaped_as_the_handoff_asks_and_reuse_no_id_of_another_bundle(self):
        f, o = self.finding, self.option
        self.assertEqual([f[k] for k in ("run", "kind", "status", "effect", "criterion")], ["any", "decision", "fixed", "bent", "phase-1"])
        self.assertNotIn("phase", f)  # it belongs to no stage of one run
        self.assertLessEqual(len(re.findall(r"[.!?](?:\s|$)", f["advice"])), 3)
        for text in ("45f163d0", "docs/shiploop-planning-review-plan-2026-10-05.md", "state-files.md", "'Planning review'"):
            self.assertIn(text, f["evidence"])
        self.assertEqual([o[k] for k in ("kind", "effort", "recommended", "status", "findings")],
                         ["change-expectation", "S", True, "done", ["o44"]])
        self.assertRegex(o["ref"], r"; [0-9a-f]{8}$")  # a done option cites the commit that landed it
        self.assertEqual((o["criterion"], o["change"]["target"]), ("phase-1", "page"))
        self.assertTrue(re.fullmatch(r"Do: .* Files and symbols: .* Test: .* Done when: [^:]*", o["goal"]), o["goal"])
        self.assertIn("skills/shiploop-run-review/defaults/expectations.json", o["goal"])
        self.assertNotIn("reviews", self.docs)  # no run, so no arc and no basis
        luna = json.loads(LUNA_REVIEW.read_text(encoding="utf-8"))["docs"]
        self.assertFalse(set(self.docs["observations"]) & set(luna["observations"]))
        self.assertFalse(set(self.docs["actions"]) & set(luna["actions"]))

    def test_the_amended_text_is_the_original_phase_1_text_plus_the_words_of_the_specs_carve_out(self):
        to = self.option["change"]["to"]
        self.assertTrue(to.startswith(PHASE_1_TEXT + " "))
        self.assertEqual(self.defaults["phase-1"]["text"], to)  # the owner ticked a26 and the defaults carry its text
        spec = " ".join(SPEC_MD.read_text(encoding="utf-8").split())
        carve_out = spec[spec.index("**S-10 carve-out, owner decision 2026-10-05**"):spec.index("**S-11")]
        for phrase in ("recorded in `state.md` at `init` or `workspace start`, never changed afterwards",
                       "selects which of the five planning results `spec`, `test-strategy`, `plan`, `step-plan` and `test-spec` start an Improve child",
                       "`--planning-review stage` starts one after each of the five, as before", "`--planning-review none` starts none",
                       "In `none` a planning result is accepted without a review loop",
                       "the spec and test strategy are committed to the knowledge home when each is accepted and no Improve child reviews "
                       "them afterwards, so later runs inherit them unreviewed",
                       "The Improve children after `system-test-author` and `release-plan` and the last `carry-forward` start in every mode"):
            self.assertIn(phrase, to)
            self.assertIn(phrase, carve_out)

    def test_a_prompt_with_a26_ticked_names_the_evidence_directory_the_option_and_the_expectation_change(self):
        cfg = json.loads((DEFAULTS_DIR / "config.json").read_text(encoding="utf-8"))
        state = {"run": {"key": "r1", "name": "Run", "evidence": "/runs/r1"}, "runs": [],
                 "findings": [{"id": i, **d} for i, d in self.open_docs["observations"].items()],
                 "options": [{"id": i, **d} for i, d in self.open_docs["actions"].items()], "review": None, "after": "wait", "notes": "",
                 "expectations": self.defaults, "selected": {"options": {"a26": True}, "find": {}},
                 "config": {**cfg["prompt"], "artifactUrl": ""}}
        text = run_logic("buildPrompt(%s)" % json.dumps(state))
        self.assertIn("Review files: the *.review.json bundles in test/shiploop_e2e/evidence/ (find each ticked id below in the bundle "
                      "that has it, for example grep -l '\"a26\"' test/shiploop_e2e/evidence/*.review.json; edit it there).",
                      text.split("\n")[0])
        self.assertIn("CHANGE AN EXPECTATION", text)
        self.assertIn("1. a26 phase-1 Amend the Specify expectation for planning_review none: target page. Now: " + self.option["change"]["to"], text)
        self.assertIn(" Was: " + self.defaults["phase-1"]["text"] + " Why: " + self.option["change"]["reason"] + " Resolves: o44.", text)
        self.assertIn("A page change means editing skills/shiploop-run-review/defaults/expectations.json", text)
        self.assertIn("- o44 [phase-1, open] " + self.finding["title"], text)
        self.assertIn("a26 ", text)

    def test_the_general_finding_shows_under_the_general_filter_with_its_option_and_not_under_other_runs(self):
        state = {"findings": [{"id": i, **d} for i, d in self.open_docs["observations"].items()],
                 "options": [{"id": i, **d} for i, d in self.open_docs["actions"].items()], "runKey": "r1"}
        general, open_for_run, other = run_logic("(function(S){return ['general','open','other'].map(function(f){"
                                                 "return cardsFor(Object.assign({filter:f},S));});})(%s)" % json.dumps(state))
        self.assertEqual([c["finding"]["id"] for c in general["cards"]], ["o44"])
        self.assertEqual([o["id"] for o in general["cards"][0]["options"]], ["a26"])
        self.assertFalse(general["cards"][0]["noOption"])
        self.assertEqual([c["finding"]["id"] for c in open_for_run["cards"]], ["o44"])  # `any` applies to every run
        # the R22c findings list the runs they apply to, so they are other runs' findings here, never general ones
        self.assertNotIn("o44", [c["finding"]["id"] for c in other["cards"]])
        self.assertTrue(all(c["finding"].get("runs") for c in other["cards"]))

    def test_the_defaults_record_the_revision_of_phase_1_naming_its_finding_and_option(self):
        doc, change = self.defaults["phase-1"], self.option["change"]
        self.assertEqual(len(doc["revs"]), 1)
        rev = doc["revs"][0]
        self.assertEqual({k: rev[k] for k in ("from", "to", "reason", "obs", "option")},
                         {"from": PHASE_1_TEXT, "to": change["to"], "reason": change["reason"], "obs": "o44", "option": "a26"})
        self.assertRegex(rev["at"], r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?Z")
        self.assertEqual(export.validate_doc("expectations", doc), [])

    def test_the_saved_page_upgrades_to_the_amended_phase_1_text_and_gains_its_revision(self):
        live = export.read_live(SNAPSHOT)
        self.assertEqual(live["expectations"]["phase-1"]["text"], PHASE_1_TEXT)  # the page still holds the original sentence
        self.assertFalse(live["expectations"]["phase-1"].get("revs"))
        docs, notes = export.upgrade_docs(live)
        written = docs["expectations"]["phase-1"]
        self.assertEqual((written["text"], written["revs"]), (self.defaults["phase-1"]["text"], self.defaults["phase-1"]["revs"]))
        self.assertIn("expectations/phase-1: the page's text, which has no revision of its own, is replaced by the defaults' text", notes)

    def test_once_applied_a26_is_listed_as_done_and_is_not_offered_again_under_its_finding(self):
        state = {"findings": [{"id": i, **d} for i, d in self.docs["observations"].items()],
                 "options": [{"id": i, **d} for i, d in self.docs["actions"].items()], "runKey": "r1"}
        general = run_logic("cardsFor(Object.assign({filter:'general'},%s))" % json.dumps(state))
        self.assertIn("a26", [o["id"] for o in general["done"]])  # R22c's done options are listed there too
        self.assertEqual([c["finding"]["id"] for c in general["cards"]], ["o44"])
        self.assertEqual([o["id"] for c in general["cards"] for o in c["options"]], [])


# ---------------------------------------------------------------- R22c: the findings layer for the runs of 2026-10-07 and 2026-10-08
# One contiguous block (another session appends tests elsewhere in this file). Every number is checked against a committed
# file: the analysis JSONs of the rounds and the run-folder extract docs/experiments/run-review-r22c-20261009/figures.json
# (written by its collect.py); the run folders themselves are never read here.

R22C_DIR = ROOT / "docs" / "experiments" / "run-review-r22c-20261009"
R22C_ANALYSIS = ROOT / "docs" / "experiments" / "batch-1010-round2-round3-analysis-20261008"
R22C_ROUND1 = ROOT / "docs" / "experiments" / "batch-1009-round1-analysis-20261008" / "analysis.json"
R22C_FIRST = (45, 27)  # the first finding and option numbers this increment adds (o44 and a26 were the last before it)
# A sentence that states the withdrawn explanation of the Grok-host Chrome failure (LEARNINGS 'Rounds 2 and 3', correction 2,
# and 'Correction of 2026-10-09'): the display asleep, off or sleeping as the cause, or keeping it awake as the remedy.
R22C_WITHDRAWN = re.compile(r"(?i)\bdisplay(?:[- ](?:asleep|sleep|off)\b|\s+(?:was|is|being|went)\s+(?:asleep|off)\b)"
                            r"|\bdisplay[- ]sleep\b|\bkeep(?:ing)?\s+the\s+display\s+awake\b")


def r22c_bundles() -> dict[str, dict]:
    """{file name: docs} of every committed review bundle."""
    return {p.name: json.loads(p.read_text(encoding="utf-8"))["docs"] for p in sorted(EVIDENCE_DIR.glob("*.review.json"))}


def r22c_numbered(ids, prefix: str, first: int) -> list[int]:
    return sorted(int(i[1:]) for i in ids if re.fullmatch(prefix + r"\d+", i) and int(i[1:]) >= first)


def r22c_texts(doc: dict) -> str:
    """Every string a finding or an option shows (the prompt prints title, the instruction, the change and the evidence)."""
    return " ".join(str(v) for k, v in doc.items() if isinstance(v, str)) + " " + " ".join(
        str(v) for v in (doc.get("change") or {}).values())


class RoundRunFindingsTests(unittest.TestCase):
    """R22c: findings, options and reviews for the eleven runs of 2026-10-07 and 2026-10-08, from the synthesized analyses,
    the run folders (through figures.json) and git; checked by --check, by id and key rules, and by their numbers."""

    @classmethod
    def setUpClass(cls):
        cls.bundles = r22c_bundles()
        cls.general = json.loads(GENERAL_REVIEW.read_text(encoding="utf-8"))["docs"]
        cls.figures = json.loads((R22C_DIR / "figures.json").read_text(encoding="utf-8"))
        cls.r2 = json.loads((R22C_ANALYSIS / "round2-analysis.json").read_text(encoding="utf-8"))["synthesis"]
        cls.r3 = json.loads((R22C_ANALYSIS / "round3-analysis.json").read_text(encoding="utf-8"))["synthesis"]
        cls.r1 = json.loads(R22C_ROUND1.read_text(encoding="utf-8"))["synthesis"]
        cls.defaults = {e["key"]: e for e in json.loads((DEFAULTS_DIR / "expectations.json").read_text(encoding="utf-8"))}
        cls.new_findings = {f"o{n}": cls.general["observations"][f"o{n}"]
                            for n in r22c_numbered(cls.general["observations"], "o", R22C_FIRST[0])}
        cls.new_options = {f"a{n}": cls.general["actions"][f"a{n}"]
                           for n in r22c_numbered(cls.general["actions"], "a", R22C_FIRST[1])}

    def bars(self, fid: str) -> dict:
        return {item["label"]: item["value"] for item in self.general["observations"][fid]["figure"]["items"]}

    def test_every_bundle_passes_the_check_and_warns_only_where_left_on_purpose(self):
        self.assertIn("general.review.json", self.bundles)
        warned = []
        for name in self.bundles:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = export.main(["--check", str(EVIDENCE_DIR / name)])
            self.assertEqual((code, err.getvalue()), (0, ""), name)
            if name == "general.review.json":
                warned = [line for line in out.getvalue().splitlines() if line.startswith("warning: ")]
        # o68 is the owner's choice (keep or remove the refused-run cap) and was never exercised, so it is not rated
        self.assertEqual(warned, ["warning: observations/o68: open finding with no effect (the page shows it as 'not rated')"])

    def test_ids_are_unique_across_bundles_and_continue_from_o45_and_a27(self):
        seen: dict[str, str] = {}
        for name, docs in self.bundles.items():
            for collection in ("observations", "actions"):
                for i in docs.get(collection) or {}:
                    self.assertNotIn(i, seen, f"{i} is in {seen.get(i)} and {name}")
                    seen[i] = name
        findings = r22c_numbered(self.general["observations"], "o", R22C_FIRST[0])
        options = r22c_numbered(self.general["actions"], "a", R22C_FIRST[1])
        self.assertGreaterEqual(len(findings), 30)
        self.assertEqual(findings, list(range(R22C_FIRST[0], R22C_FIRST[0] + len(findings))))
        self.assertEqual(options, list(range(R22C_FIRST[1], R22C_FIRST[1] + len(options))))

    def test_every_runs_key_is_a_run_folder_and_every_criterion_a_key_of_the_defaults(self):
        folders = set(self.figures["runs"])
        self.assertEqual(len(folders), 11)
        self.assertTrue(self.new_findings)
        for fid, finding in self.new_findings.items():
            self.assertEqual(finding.get("run"), "any", fid)
            self.assertTrue(finding.get("runs"), fid)
            self.assertLessEqual(set(finding["runs"]), folders, fid)
            self.assertIn(finding["criterion"], self.defaults, fid)
            if finding.get("status", "open") == "open" and fid != "o68":
                self.assertIn(finding.get("effect"), ("broken", "bent"), fid)
            if "advice" in finding:
                self.assertLessEqual(len(re.findall(r"[.!?](?:\s|$)", finding["advice"])), 3, fid)
            for item in (finding.get("figure") or {}).get("items", []):
                self.assertLessEqual(len(item["label"]), 22, f"{fid}: {item['label']}")
        proposed = {json.loads(o["change"]["to"])["key"] for o in self.new_options.values()
                    if o.get("kind") == "change-expectation" and o["change"]["to"].startswith("{")}
        for aid, option in self.new_options.items():
            self.assertIn(option["criterion"], set(self.defaults) | proposed, aid)
            self.assertTrue(set(option["findings"]) <= set(self.new_findings), aid)
            self.assertTrue(re.fullmatch(r"Do: .* Files and symbols: .* Test: .* Done when: [^:]*", option["goal"]), aid)
            if option.get("kind") in ("fix-shiploop", "fix-harness"):
                self.assertRegex(option["why"], r"^For: .* Against: .* Verdict: ", aid)
        for fid in self.new_findings:  # one to four options each, at most one recommended
            linked = [o for o in self.new_options.values() if fid in o["findings"]]
            self.assertTrue(1 <= len(linked) <= 4, fid)
            self.assertLessEqual(sum(o.get("recommended") is True for o in linked), 1, fid)

    def test_a_fixed_finding_cites_its_commit_in_a_done_option_and_every_done_or_built_option_has_a_ref(self):
        fixed = [fid for fid, f in self.new_findings.items() if f.get("status") == "fixed"]
        self.assertGreaterEqual(len(fixed), 10)
        for fid in fixed:
            refs = [o.get("ref", "") for o in self.new_options.values() if fid in o["findings"] and o["status"] in ("done", "built")]
            self.assertTrue(any(re.search(r"\b[0-9a-f]{8}\b", r) for r in refs), fid)
            self.assertNotIn("effect", self.new_findings[fid], fid)
        for aid, option in self.new_options.items():
            if option["status"] in ("done", "built", "planned"):
                self.assertTrue(option.get("ref"), aid)

    def test_no_bundle_states_the_withdrawn_explanation_and_the_chrome_findings_name_the_grok_host(self):
        for name, docs in self.bundles.items():
            for collection, items in docs.items():
                for i, doc in items.items():
                    text = json.dumps(doc, ensure_ascii=False)
                    self.assertIsNone(R22C_WITHDRAWN.search(text), f"{name} {collection}/{i}")
        self.assertIsNone(R22C_WITHDRAWN.search("Chrome hung in the Grok host while the display was held on"))  # a fact, not the cause
        self.assertIsNotNone(R22C_WITHDRAWN.search("the display was asleep, so Chrome stayed on about:blank"))
        chrome = [fid for fid, f in self.new_findings.items() if "Chrome" in f["title"]]
        self.assertTrue(chrome)
        for fid in chrome:
            self.assertIn("Grok host", self.new_findings[fid]["title"] + self.new_findings[fid]["observed"], fid)
        mixed = self.new_findings["o73"]  # r2 is mixed host: Claude, not Grok, ran its browser check
        self.assertIn("Claude Sonnet", mixed["observed"])
        self.assertIn("browser check", mixed["observed"])

    def test_the_figures_equal_the_numbers_of_the_analyses_and_the_run_extract(self):
        cost = self.r2["cost_finding"]
        for text in ("$5.1613 to $8.5146", "calls 105 to 152", "17.73M to 30.84M", "$5.70 to $5.81"):
            self.assertIn(text, cost)
        loop = next(c for c in self.r3["loop_done_check"] if "B9" in c["condition"])["evidence"]
        self.assertIn("Checkers cost is $6.65 against r1 $5.16 and r2 $8.51, Battleship $5.67 against r1 $5.70 and r2 $5.81", loop)
        self.assertEqual(self.bars("o69"), {"r1 Checkers": 5.16, "r2 Checkers": 8.51, "r3 Checkers": 6.65,
                                            "r1 Battleship": 5.70, "r2 Battleship": 5.81, "r3 Battleship": 5.67})
        for text in ("$5.1613", "$8.5146", "105 to 152", "17.73M to 30.84M"):
            self.assertIn(text, self.general["observations"]["o69"]["observed"])
        a5 = next(c for c in self.r2["candidates"] if c["id"] == "A5")["evidence"]
        self.assertIn("(44-47%)", a5)
        self.assertIn("(80-89%)", a5)
        self.assertIn("67-74% of it in Checkers", next(c for c in self.r3["batch4_scorecard"] if c["change"].startswith("A5 per-item"))["evidence"])
        self.assertEqual(self.bars("o55"), {"Floor after ratchet": 100, "r2 Checkers, low": 44, "r2 Checkers, high": 47,
                                            "r2 Battleship, low": 80, "r2 Battleship, high": 89, "r3 Checkers model, low": 67})
        self.assertIn("Met 1 of 4", next(c for c in self.r3["new_candidates"] if c["id"] == "R3-2")["evidence"])
        self.assertEqual(self.bars("o46"), {"Rollbacks read": 4, "Printed recipe used": 1})
        self.assertIn("8 calls, 34 s", next(c for c in self.r1["candidates"] if c["id"] == "R1")["evidence"])
        self.assertIn("(round 1: 7 and 8 calls with a hand sed)", next(c for c in self.r2["batch3_scorecard"] if c["change"].startswith("R1 "))["evidence"])
        self.assertEqual(self.bars("o58"), {"r1 Battleship calls": 8, "r1 Checkers calls": 7, "r2 calls, each run": 1})
        fig, runs = self.figures, self.figures["runs"]
        round_runs = fig["round_runs"]
        self.assertEqual(self.bars("o65"), {"Round runs": len(round_runs), "Backchain loop ran": len(fig["backchain_loop_round_runs"]),
                                            "Graph check ran": len(fig["graph_checked_round_runs"])})
        self.assertEqual((len(fig["backchain_loop_round_runs"]), len(fig["graph_checked_round_runs"])), (0, 3))
        self.assertEqual(set(self.general["observations"]["o65"]["runs"]), set(round_runs) - set(fig["graph_checked_round_runs"]))
        windows = {k: runs[k]["planning_window_min"] for k in round_runs}
        self.assertEqual(windows, {k: round(runs[k]["planning_window_seconds"] / 60, 1) for k in round_runs})
        sonnet = [windows[k] for k in round_runs if k.endswith("sonnet")]
        self.assertEqual(self.bars("o70"), {"Owner's rule": 30, "Grok r1": windows["r1-battleship-grok-none"],
                                            "Grok r2, mixed run": windows["r2-battleship-grok-none"], "Grok r3": windows["r3-battleship-grok-none"],
                                            "Sonnet, slowest": max(sonnet), "Sonnet, fastest": min(sonnet)})
        self.assertEqual([windows[k] for k in ("r1-battleship-grok-none", "r2-battleship-grok-none", "r3-battleship-grok-none")], [23.3, 15.7, 23.2])
        self.assertLess(max(windows.values()), 30)
        # the second planning figure: round 1's planning_minutes is the harness's stage seconds from intake to prepare
        round1 = json.loads((ROOT / "docs" / "experiments" / "round1-20261008" / "evidence.json").read_text(encoding="utf-8"))["runs"]
        for run in round1.values():
            seconds = sum(v for k, v in run["stage_seconds"].items() if int(k.split(":")[0]) <= 6)
            self.assertEqual(round(seconds / 60, 1), run["planning_minutes"])
        self.assertEqual(self.bars("o71"), {"r1 blocked visit": fig["r1_grok_blocked_visit_min"],
                                            "r3 open implement": fig["r3_grok"]["open_implement_min"]})
        self.assertEqual((fig["r1_grok_blocked_visit_min"], fig["r3_grok"]["open_implement_min"]), (21.1, 27.1))
        mixed = fig["r2_mixed"]
        self.assertEqual(self.bars("o73"), {"Grok-host visits": mixed["grok_visits"], "Claude-host visits": mixed["claude_visits"]})
        self.assertEqual((mixed["grok_visits"], mixed["claude_visits"], mixed["first_claude_visit"]), (31, 21, 32))
        self.assertEqual(self.bars("o76"), {f"r3 {name} {what}": runs[key]["narrative_" + what]
                                            for name, key in (("Battleship", "r3-battleship-sonnet"), ("Checkers", "r3-checkers-sonnet"),
                                                              ("Grok", "r3-battleship-grok-none")) for what in ("emitted", "shown")})
        skipped = {k: runs[k]["skipped_visits"] for k in round_runs if runs[k]["skipped_visits"]}
        self.assertEqual(self.bars("o80"), {"Round runs": 9, "Runs with skill_na": len(skipped),
                                            "Visits recorded N/A": sum(len(v) for v in skipped.values())})
        self.assertEqual(sorted(self.general["observations"]["o80"]["runs"]), sorted(skipped))

    def test_the_credential_finding_names_the_trigger_the_screen_replay_shows(self):
        sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
        try:
            import shiploop_privacy
        finally:
            sys.path.remove(str(ROOT / "skills" / "shiploop" / "scripts"))
        replay = self.figures["credential_replay"]
        self.assertEqual(sorted(replay), ["r2-battleship-grok-none", "r3-battleship-grok-none"])
        hex_lines = 0
        for rows in replay.values():
            for row in rows:
                self.assertTrue(shiploop_privacy.sensitive_text(row["line"]))  # the screen of this checkout still refuses it
                self.assertFalse(shiploop_privacy.sensitive_text(re.sub(r"(?i)\bsignature\s*:", "", row["line"])))
                self.assertTrue(row["trips_on"] and all("Signature:" in part for part in row["trips_on"]))
                hex_lines += bool(re.search(r"#[0-9a-fA-F]{6}\b", row["line"]))
        self.assertGreaterEqual(hex_lines, 1)  # the hex colours are on the refused line, and they are not what trips it
        x1 = self.new_findings["o75"]
        self.assertIn("the trigger is the label, not the hex values", x1["observed"])
        self.assertEqual(sum(self.figures["runs"][k]["credential_refusals"] for k in x1["runs"]), 4)
        self.assertIn("E2E session's engine", x1["advice"])

    def test_a_prompt_for_new_options_stays_within_the_size_contract_and_names_no_unticked_option(self):
        findings = [{"id": i, **d} for docs in self.bundles.values() for i, d in (docs.get("observations") or {}).items()]
        options = [{"id": i, **d} for docs in self.bundles.values() for i, d in (docs.get("actions") or {}).items()]
        cfg = json.loads((DEFAULTS_DIR / "config.json").read_text(encoding="utf-8"))
        run = {"key": "r3-battleship-sonnet", "name": "r3 Battleship Sonnet", "evidence": "/Users/dadleet/e2e-runs/20261008/r3-battleship-sonnet"}
        state = {"run": run, "runs": [run], "findings": findings, "options": options, "expectations": self.defaults,
                 "review": None, "after": "wait", "notes": "", "selected": {"options": {}, "find": {}},
                 "config": {**cfg["prompt"], "artifactUrl": ""}}

        def own_words(ticked):
            chosen = [o for o in options if o["id"] in ticked]
            ids = {f for o in chosen for f in o["findings"]}
            said = sum(len(o["goal"]) + len(o["title"]) + len(o.get("cost", ""))
                       + sum(len(v) for v in (o.get("change") or {}).values()) for o in chosen)
            return said + sum(len(f["title"]) + len(f["expected"]) + len(f["observed"]) + len(f.get("evidence", ""))
                              for f in findings if f["id"] in ids)

        live = [i for i, o in self.new_options.items() if o["status"] != "done"]
        changes = [i for i, o in self.new_options.items() if o.get("kind") == "change-expectation" and o["change"]["target"] == "page"]
        ticks = [["a27", "a75"]] + ([changes[:2]] if len(changes) >= 2 else []) + [[i] for i in live]
        texts = run_logic("(function(S){return %s.map(function(t){var s=JSON.parse(JSON.stringify(S));"
                          "t.forEach(function(i){s.selected.options[i]=true;});return buildPrompt(s);});})(%s)"
                          % (json.dumps(ticks), json.dumps(state)))
        for ticked, text in zip(ticks, texts):
            with self.subTest(ticked=ticked):
                self.assertLessEqual(len(text) - own_words(ticked), 3000, len(text))
                for other in options:
                    if other["id"] not in ticked:
                        self.assertNotRegex(text, rf"\b{other['id']}\b")
        self.assertIn("FIX SHIPLOOP", texts[0])
        self.assertIn("FIX THE HARNESS", texts[0])
        self.assertLess(texts[0].index("FIX SHIPLOOP"), texts[0].index("FIX THE HARNESS"))

    def test_stale_luna_statements_are_marked_superseded_in_place_with_their_evidence(self):
        luna = self.bundles["luna1.review.json"]
        obs, act = luna["observations"], luna["actions"]
        expect = {  # id: (status, the dated mark, a token of its evidence)
            "o34": ("fixed", "[Superseded 2026-10-09:", "c7a8187d"), "o40": ("fixed", "[Superseded 2026-10-09:", "9c593a37"),
            "o41": ("accepted", "[Superseded in part 2026-10-09:", "ce32a143"),
            "a21": ("done", "[Superseded 2026-10-09:", "9c593a37"), "a17": ("done", "[2026-10-09: shipped in 1.21.0", "1411d5f1"),
            "a23": ("built", "[2026-10-09: built in 41c45512", "d1cca62f"), "a09": ("built", "is unknown", "1411d5f1")}
        for i, (status, note, token) in expect.items():
            doc = (obs if i.startswith("o") else act)[i]
            text = r22c_texts(doc)
            self.assertEqual(doc["status"], status, i)
            self.assertIn(note, text, i)
            self.assertIn(token, text, i)
            # kept as written: the dated mark is appended after the old text, never a rewrite (a21 had no ref; its ref is new)
            marked = [doc[f] for f in ("observed", "why", "ref", "advice") if "2026-10-09" in doc.get(f, "")
                      and not (i == "a21" and f == "ref")]
            self.assertTrue(marked, i)
            for field in marked:
                self.assertTrue(field.endswith("]"), i)
                self.assertGreater(field.index("2026-10-09"), 20, i)
        self.assertIn("f6f1ac2f", obs["o41"]["observed"])
        self.assertEqual(self.figures["luna_recollect"], {"failures": 13, "generic_tails": 0, "own_line": 13})
        self.assertIn("[Superseded 2026-10-09: o40 is fixed (9c593a37).]", luna["reviews"]["luna1"]["basis"]["P5"])

    def test_the_phase_changes_keep_the_current_text_and_the_owners_sentence_and_append_the_engine_today(self):
        changes = {o["criterion"]: (i, o) for i, o in self.new_options.items()
                   if o.get("kind") == "change-expectation" and o["change"]["target"] == "page"}
        for key, finding, appended in (("phase-2", "o65", "the plan packet makes the Backchain child the host's choice"),
                                       ("phase-4", "o80", "when the accepted step plan records skill_na")):
            aid, option = changes[key]
            now = self.defaults[key]["text"]
            self.assertTrue(option["change"]["to"].startswith(now), key)  # nothing of the current text is removed
            self.assertIn(appended, option["change"]["to"][len(now):], key)
            self.assertEqual((option["findings"], option.get("recommended")), ([finding], True), key)
            self.assertIn(key, option["goal"])
        self.assertTrue(self.defaults["phase-2"]["text"].endswith("there is no limit to this"))  # the owner's sentence
        self.assertIn("there is no limit to this", changes["phase-2"][1]["change"]["to"])
        self.assertIn("'there is no limit to this' is kept word for word", changes["phase-2"][1]["change"]["reason"])

    def test_the_new_criteria_are_documents_in_the_specs_words_for_clauses_no_criterion_carries(self):
        spec = " ".join(SPEC_MD.read_text(encoding="utf-8").split())
        carried = {c for e in self.defaults.values() for c in e.get("clauses") or []}
        phrases = {"S-14": ("When a step meets an open question, it takes a stated, recorded default", "instead of waiting",
                            "When a step needs something only a person can supply",
                            "the run records it as an open item, continues with everything that does not depend on it",
                            "truly cannot proceed"),
                   "S-15": ("What the user sees about progress is rendered by ShipLoop's scripts from saved state: a short status at every "
                            "step and, at milestones, a narrative of what is achieved, what is happening, what comes next and the observed pace.",
                            "The model never composes, paraphrases or estimates progress itself"),
                   "S-3": ("SKILL.md and the reference cards tell the model how to invoke the scripts and to follow what they return.",
                           "When a card and a script disagree, the script wins, and the disagreement is a defect to fix.")}
        proposed = {}
        for aid, option in self.new_options.items():
            if option.get("kind") == "change-expectation" and option["change"]["to"].startswith("{"):
                doc = json.loads(option["change"]["to"])
                proposed[doc["clauses"][0]] = (aid, option, doc)
        self.assertEqual(sorted(proposed), ["S-14", "S-15", "S-3"])
        for clause, (aid, option, doc) in proposed.items():
            self.assertNotIn(clause, carried, clause)  # the gap is real
            self.assertNotIn(doc["key"], self.defaults, clause)
            self.assertEqual((option["criterion"], doc["kind"], doc["group"]), (doc["key"], "criterion", "group-principles"))
            self.assertEqual(export.validate_doc("expectations", {k: v for k, v in doc.items() if k != "key"}), [], clause)
            self.assertLessEqual(len(re.findall(r"[.!?](?:\s|$)", doc["text"])), 2, clause)
            for phrase in phrases[clause]:
                self.assertIn(phrase, spec, clause)
                self.assertIn(phrase.rstrip("."), doc["text"], clause)
            reason = option["change"]["reason"]
            for gap in ("S-3", "S-8", "S-12", "S-13", "S-14", "S-15"):
                self.assertIn(gap, reason, clause)
            self.assertTrue(option["findings"] and all(self.new_findings[f].get("status", "open") == "open" for f in option["findings"]))
            self.assertIn(f"key {doc['key']}", option["goal"])
        # the prompt reads a new criterion as one with no current text
        text = run_logic("buildPrompt(%s)" % json.dumps({
            "run": {"key": "r1-battleship-grok-none"}, "findings": [{"id": i, **d} for i, d in self.new_findings.items()],
            "options": [{"id": i, **d} for i, d in self.new_options.items()], "expectations": self.defaults,
            "selected": {"options": {proposed["S-14"][0]: True}, "find": {}}, "config": {}}))
        self.assertIn(f"{proposed['S-14'][0]} P7 Add a criterion for S-14: unattended by default: target page. Now: {{", text)
        self.assertIn(" Was: (not recorded) Why: ", text)

    def test_the_two_round_3_reviews_ground_every_basis_line_and_derive_the_chips_they_describe(self):
        findings = [{"id": i, **d} for docs in self.bundles.values() for i, d in (docs.get("observations") or {}).items()]
        criteria = [k for k, e in self.defaults.items() if e["kind"] == "criterion"]
        expected = {"r3-battleship-sonnet": {"P1": "holds", "P2": "holds", "P3": "bent", "P4": "holds", "P5": "broken",
                                             "P6": "unexamined", "B1": "unexamined", "B2": "bent", "B3": "unexamined",
                                             "B4": "unexamined", "B5": "unexamined"},
                    "r3-battleship-grok-none": {"P1": "holds", "P2": "holds", "P3": "unexamined", "P4": "holds", "P5": "broken",
                                                "P6": "broken", "B1": "unexamined", "B2": "bent", "B3": "unexamined",
                                                "B4": "unexamined", "B5": "unexamined"}}
        for key, chips in expected.items():
            with self.subTest(run=key):
                name = f"{key}.review.json"
                self.assertIn(name, self.bundles)
                self.assertEqual(sorted(self.bundles[name]), ["reviews"])  # its findings live in general.review.json
                review = self.bundles[name]["reviews"][key]
                self.assertTrue(3 <= len(review["summary"]) <= 6)
                self.assertEqual(review["reviewedAt"], "2026-10-09T16:00:00Z")
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = export.main(["--check", str(EVIDENCE_DIR / name)])
                self.assertEqual((code, err.getvalue(), out.getvalue().strip()), (0, "", "check: ok (1 document, 0 failures, 0 warnings)"))
                applying = {f["id"]: f for f in findings if key in (f.get("runs") or []) and f.get("status", "open") == "open"}
                for criterion, line in review["basis"].items():
                    mine = {fid: f for fid, f in applying.items() if f["criterion"] == criterion}
                    if line.startswith("Holds"):
                        self.assertEqual(mine, {}, criterion)
                    else:
                        cited = set(re.findall(r"\bo\d+\b", line))
                        self.assertEqual(cited, set(mine), criterion)  # every open finding of the criterion, and only those
                        for fid in cited:
                            word = "Broken by" if mine[fid]["effect"] == "broken" else "Bent by"
                            self.assertRegex(line, rf"(?i){word}[^.;]*\b{fid}\b", f"{criterion} {fid}")
                    self.assertTrue(re.search(r"\b(?:o\d+|state\.md|metrics\.json|result\.json|run/backchain/|revision \d+)", line), criterion)
                got = run_logic("(function(F,R){return %s.map(function(k){return chipFor(k,%s,F,R);});})(%s,%s)"
                                % (json.dumps(criteria), json.dumps(key), json.dumps(findings), json.dumps(review)))
                self.assertEqual(dict(zip(criteria, got)), chips)
        runs, g3 = self.figures["runs"], self.figures["r3_grok"]
        sonnet = self.bundles["r3-battleship-sonnet.review.json"]["reviews"]["r3-battleship-sonnet"]["summary"][0]
        bs = runs["r3-battleship-sonnet"]
        for fact in (f"in {bs['wall_min']} min", f"{bs['visits']} accepted visits", f"{bs['calls']} model calls", f"${bs['cost_usd']:.2f}",
                     f"{bs['planning_window_min']} min ({bs['planning_window_seconds']:.0f} s)"):
            self.assertIn(fact, sonnet)
        grok = " ".join(self.bundles["r3-battleship-grok-none.review.json"]["reviews"]["r3-battleship-grok-none"]["summary"])
        for fact in ("STOPPED", f"{g3['accepted_visits']} accepted visits", f"{g3['open_implement_min']} unaccepted minutes",
                     f"{g3['resumed_session_min']} minutes", f"{g3['first_browser_line_second']} s in", "Grok host"):
            self.assertIn(fact, grok)
        self.assertEqual((g3["stop"], g3["earlier_stop"], g3["last_accepted_stage"]), ("stopped", ["terminated by SIGTERM"], "implement"))


# ---------------------------------------------------------------- R20a: the stage catalog, the card fields and the stage card

STAGES_JSON = DEFAULTS_DIR / "stages.json"
FIXTURES = ROOT / "test" / "fixtures" / "run-review"
ENGINE_SPEC_PATH = ROOT / "skills" / "shiploop" / "scripts" / "shiploop_stage_spec.py"
CARD_FIELDS = ("summary", "summaryTruncated", "resultFile", "carried", "packetImprove")
MODES = (None, "stage", "none", "not recorded", "a mode the engine adds later")


def engine_spec():
    return export.load_stage_spec(ENGINE_SPEC_PATH)


class StageCatalogTests(unittest.TestCase):
    """The catalog is derived from the engine's stage table, never written by hand, and its exit-check rule is exact."""

    def setUp(self):
        self.spec = engine_spec()
        self.catalog = export.stage_catalog(self.spec)
        self.by_name = {e["stage"]: e for e in self.catalog}
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def test_the_committed_catalog_equals_what_the_engines_stage_table_yields(self):
        committed = json.loads(STAGES_JSON.read_text(encoding="utf-8"))
        self.assertEqual(committed["stages"], self.catalog, "stage table changed: run export.py --stages")
        self.assertEqual([e["stage"] for e in committed["stages"]], list(self.spec.STAGES))  # graph order, every stage once
        for entry in self.catalog:  # nothing is hand-written: the purpose is the row's goal as the engine states it
            self.assertEqual(entry["purpose"], self.spec.STAGE_SPEC[entry["stage"]].goal)
            self.assertEqual(entry["reads"], list(self.spec.STAGE_SPEC[entry["stage"]].reads))

    def test_the_stages_command_rewrites_the_committed_file_byte_for_byte(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(export.main(["--stages", "--out", str(self.tmp)]), 0)
        written = self.tmp / "stages.json"
        self.assertEqual(out.getvalue().strip(), str(written.resolve()))
        self.assertEqual(written.read_bytes(), STAGES_JSON.read_bytes())

    def test_the_stages_command_names_a_missing_engine_table_and_refuses_a_second_mode(self):
        with self.assertRaises(export.ExportError) as raised:
            export.write_stages(self.tmp, spec_path=self.tmp / "no-such-spec.py")
        self.assertIn("missing", str(raised.exception))
        self.assertIn("stage table of the shiploop skill", str(raised.exception))
        with contextlib.redirect_stderr(io.StringIO()) as err, self.assertRaises(SystemExit):
            export.main(["--stages", "--defaults"])
        self.assertIn("give one of", err.getvalue())

    def entry(self, stage: str) -> dict:
        """The catalog entry of a stage under either name of an alias group, so the engine's rename changes nothing here."""
        return next(e for e in self.catalog if e["stage"] in export.stage_names(stage))

    def test_each_exit_check_class_has_a_real_stage_and_the_rule_reads_only_the_rows_own_fields(self):
        self.assertEqual({n: self.entry(n)["exitCheck"] for n in
                          ("implement", "test-green", "verify", "intake", "get-next-work-item", "document", "release",
                           "spec", "plan", "step-plan", "carry-forward", "release-plan")},
                         {"implement": "script-run", "test-green": "script-run", "verify": "script-run",
                          "intake": "model judgement", "get-next-work-item": "model judgement", "document": "model judgement",
                          "release": "model judgement", "spec": "review loop", "plan": "review loop",
                          "step-plan": "review loop", "carry-forward": "review loop", "release-plan": "review loop"})
        for stage in self.spec.STAGES:
            row = self.spec.STAGE_SPEC[stage]
            self.assertEqual(self.by_name[stage]["exitCheck"],
                             "script-run" if row.complete_runs else "review loop" if row.improve else "model judgement", stage)
        # the rule on its own, including the precedence no engine row exercises today
        self.assertEqual([export.exit_check(r, i) for r, i in (((), None), ((), "always"), ((), "last-item"),
                                                               (("lint-gate",), None), (("lint-gate",), "always"))],
                         ["model judgement", "review loop", "review loop", "script-run", "script-run"])
        self.assertEqual({e["exitCheck"] for e in self.catalog}, set(export.EXIT_CHECKS))
        self.assertFalse([s for s in self.spec.STAGES if self.spec.STAGE_SPEC[s].complete_runs
                          and self.spec.STAGE_SPEC[s].improve], "a stage with both would be script-run by rule, not by an example")

    def test_the_mode_none_case_follows_the_engines_own_reviewed_stages(self):
        self.assertEqual({e["stage"] for e in self.catalog if e.get("planningChoice")}, set(self.spec.PLANNING_CHOICE_STAGES))
        for stage in self.spec.PLANNING_CHOICE_STAGES:  # only a stage the Improve rule `always` covers can be the option's
            self.assertEqual(self.by_name[stage]["improve"], "always", stage)
        last_item = {e["stage"] for e in self.catalog if e.get("improve") == "last-item"}
        for mode in self.spec.PLANNING_REVIEW_MODES:
            reviewed = {e["stage"] for e in self.catalog if export.effective_exit_check(e, mode) == "review loop"}
            self.assertEqual(reviewed, set(self.spec.reviewed_stages(mode)) | last_item, mode)
        for stage in ("spec", "test-strategy", "plan", "step-plan", "test-spec"):
            self.assertEqual([export.effective_exit_check(self.by_name[stage], m) for m in MODES],
                             ["review loop", "review loop", "model judgement", "review loop", "review loop"], stage)
        for stage in ("carry-forward", "system-test-author", "release-plan", "implement", "intake"):
            self.assertEqual({export.effective_exit_check(self.by_name[stage], m) for m in MODES},
                             {self.by_name[stage]["exitCheck"]}, stage)  # the option does not touch these

    def test_catalog_entries_validate_and_the_defaults_documents_carry_them(self):
        docs = export.defaults_docs()
        self.assertEqual(docs["config"]["stages"], {"stages": self.catalog})
        self.assertEqual(export.validate_doc("config", docs["config"]["stages"]), [])
        bad = {"stages": [dict(self.catalog[0], exitCheck="by hand"), {"stage": "x"}]}
        problems = "\n".join(export.validate_doc("config", bad))
        self.assertIn("'by hand' is not one of", problems)
        self.assertIn("missing required field 'purpose'", problems)

    def test_a_page_whose_catalog_differs_is_replaced_and_told_so_and_a_page_with_none_gets_it_quietly(self):
        live = export.read_live(SNAPSHOT)
        docs, notes = export.upgrade_docs(live)
        self.assertEqual(docs["config"]["stages"], {"stages": self.catalog})
        self.assertFalse([n for n in notes if "config/stages" in n])  # the saved page has none: nothing is replaced
        live["config"]["stages"] = {"stages": [{"stage": "old", "purpose": "p", "exitCheck": "script-run", "reads": []}]}
        _, notes = export.upgrade_docs(live)
        self.assertTrue([n for n in notes if n.startswith("config/stages: replaced by the defaults")])
        live["config"]["stages"] = {"stages": self.catalog}
        self.assertFalse([n for n in export.upgrade_docs(live)[1] if "config/stages" in n])

    def test_schema_md_documents_the_catalog_the_rule_the_aliases_and_every_marker(self):
        schema = " ".join(SCHEMA_MD.read_text(encoding="utf-8").split())
        for phrase in ("`config/stages`", "`export.py --stages`", "`defaults/stages.json`", "script-run", "review loop",
                       "model judgement", "`planningChoice`", "`STAGE_ALIASES`", "get-next-work-item",
                       "not found in the packet text", "`summaryTruncated`", "`packetImprove`"):
            self.assertIn(phrase, schema, phrase)
        for label, description, _ in export.CARRIED:
            self.assertIn(f"`{label}` | {description}", schema.replace("\\|", "|"), label)  # the table escapes the pipes


class StageAliasTests(unittest.TestCase):
    """select-work and get-next-work-item are one group, resolved once, so old evidence and new runs both render."""

    def test_both_names_resolve_to_the_same_group_phase_and_catalog_entry(self):
        self.assertEqual(export.STAGE_ALIASES, (("get-next-work-item", "select-work"),))  # the engine's name first: canonical
        self.assertEqual(export.stage_names("select-work"), export.stage_names("get-next-work-item"))
        self.assertEqual(export.stage_names("select-work")[0], "get-next-work-item")
        self.assertEqual([stage for _, stages in export.PHASES for stage in stages if "work-item" in stage or stage == "select-work"],
                         ["get-next-work-item"])  # the old name is in the alias table only
        self.assertEqual(export.stage_names("spec"), ("spec",))
        self.assertEqual(export.STAGE_PHASE["select-work"], export.STAGE_PHASE["get-next-work-item"])
        self.assertEqual(export.PHASES[export.STAGE_PHASE["get-next-work-item"]][0], "Plan")
        # the table goes both ways: a table that lists the new name gives the old one the same value
        self.assertEqual(export._with_aliases({"get-next-work-item": 7, "spec": 1}),
                         {"get-next-work-item": 7, "select-work": 7, "spec": 1})
        self.assertEqual(export._with_aliases({"select-work": 7, "spec": 1}), {"get-next-work-item": 7, "select-work": 7, "spec": 1})

    def test_a_run_whose_rows_carry_either_name_exports_the_same_phases_and_lists_no_unknown_stage(self):
        results = []
        for stage in ("select-work", "get-next-work-item"):
            accepts = [(a, stage if a == "get-next-work-item" else s, m, o) for a, s, m, o in ACCEPTS]
            tmp = tempfile.TemporaryDirectory()
            self.addCleanup(tmp.cleanup)
            docs, facts = export.build_run(make_run(Path(tmp.name), accepts, loops=False))
            run = next(iter(docs["runs"].values()))
            self.assertIn(stage, [r["stage"] for r in run["stages"]])
            self.assertNotIn("not in the phase table", "\n".join(facts))
            results.append(run["phases"])
        self.assertEqual(results[0], results[1])

# A packet text is one real line of each marker, in order, taken verbatim from a real packet of its era: the Luna run on
# ShipLoop 1.16.1 (skill-validate) and the Sonnet run on 1.22.0 (implement). The whole sets were counted by the journal entry.
def packet_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def carried_of(text: str) -> dict:
    return export.carried_markers(text)


class CardRowFieldsTests(unittest.TestCase):
    """The stage row's summary, result file and packet checklist, from the run's own records."""

    KEY = RunReviewTest.KEY

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def row(self, out: Path, stage: str) -> dict:
        docs, _ = export.build_run(out)
        return next(r for r in docs["runs"][self.KEY]["stages"] if r["stage"] == stage)

    def set_summary(self, out: Path, name: str, summary) -> None:
        def change(state):
            for entry in state["history"]:
                if entry["action"] == IDS[name]:
                    if summary is None:
                        entry.pop("summary")
                    else:
                        entry["summary"] = summary
        path = run_dir_of(out) / "state.md"
        value = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", path.read_text(), re.S).group(1))
        change(value)
        record(path, value)

    def test_the_summary_is_the_accepted_text_cut_at_300_characters_with_a_flag_only_when_cut(self):
        out = make_run(self.tmp, loops=False)
        self.set_summary(out, "spec", "s" * 300)
        self.set_summary(out, "plan", "p" * 301)
        self.set_summary(out, "intake", "  padded  ")
        spec, plan, intake = (self.row(out, s) for s in ("spec", "plan", "intake"))
        self.assertEqual((spec["summary"], "summaryTruncated" in spec), ("s" * 300, False))
        self.assertEqual((plan["summary"], plan["summaryTruncated"]), ("p" * 300, True))
        self.assertEqual(intake["summary"], "padded")
        self.assertEqual(export.validate_doc("runs", export.build_run(out)[0]["runs"][self.KEY]), [])

    def test_a_visit_with_no_history_summary_falls_back_to_its_result_record_and_with_neither_has_none(self):
        out = make_run(self.tmp, loops=False)
        self.set_summary(out, "spec", None)  # the fixture's result record says "s"
        self.assertEqual(self.row(out, "spec")["summary"], "s")
        self.set_summary(out, "plan", None)
        (run_dir_of(out) / "results" / f"{IDS['plan']}.md").unlink()
        row = self.row(out, "plan")
        self.assertNotIn("summary", row)
        self.assertNotIn("summaryTruncated", row)

    def test_the_result_file_is_true_when_it_exists_false_when_it_does_not_and_the_size_stays_its_own(self):
        out = make_run(self.tmp, loops=False)
        (run_dir_of(out) / "results" / f"{IDS['spec']}.md").unlink()
        spec, plan = self.row(out, "spec"), self.row(out, "plan")
        self.assertIs(spec["resultFile"], False)
        self.assertNotIn("resultBytes", spec)  # a size only for a file that exists
        self.assertEqual((plan["resultFile"], plan["resultBytes"] > 0), (True, True))

    def test_the_real_packet_lines_of_each_era_carry_every_label_and_removing_a_labels_lines_flips_only_that_label(self):
        labels = [label for label, _, _ in export.CARRIED]
        for name in ("packet-lines-1161.txt", "packet-lines-1220.txt"):
            text = packet_fixture(name)
            self.assertEqual(carried_of(text), {label: True for label in labels}, name)
            for label, _, rules in export.CARRIED:
                rxs = [re.compile(rx, re.M) for rule in rules for group in rule for rx in group]
                kept = "\n".join(l for l in text.split("\n") if not any(rx.search(l) for rx in rxs))
                got = carried_of(kept)
                self.assertFalse(got[label], f"{name} {label}")
                # a line may serve two labels (the blocked line carries the recovery sentence and, in 1.22.0, the shape)
                self.assertGreaterEqual(sum(got.values()), len(labels) - 2, f"{name} {label}")

    def test_the_two_eras_differ_only_in_the_blocked_by_sentence_and_the_purpose_marker(self):
        old, new = packet_fixture("packet-lines-1161.txt"), packet_fixture("packet-lines-1220.txt")
        self.assertIn("A blocked result adds blocked_by", old)
        self.assertNotIn("A blocked result adds blocked_by", new)
        self.assertIn('blocked: {"outcome": "blocked"', new)
        self.assertNotIn("Step S1 (1 of 3)", old)  # the implement packet's step line is the purpose marker's second pattern
        # recovery needs both sentences: the blocked_by one alone is not enough
        only = "\n".join(l for l in old.split("\n") if not l.startswith("A blocked result adds"))
        self.assertFalse(carried_of(only)["recovery"])
        no_goal = "\n".join(l for l in new.split("\n") if not l.startswith("Goal: "))
        self.assertTrue(carried_of(no_goal)["purpose"])  # the Step line alone says the purpose of an implement packet

    def test_a_checked_by_line_is_an_additional_way_for_checked_to_be_found_and_nothing_needs_it(self):
        old, new = packet_fixture("packet-lines-1161.txt"), packet_fixture("packet-lines-1220.txt")
        for text in (old, new):  # packets that predate the line keep the old pair of markers
            self.assertNotIn("Checked by:", text)
            self.assertTrue(carried_of(text)["checked"])
        without = "\n".join(l for l in new.split("\n") if not l.startswith(("Done when (", "Improve: ")))
        self.assertFalse(carried_of(without)["checked"])
        with_line = without + "\nChecked by: the lint gate and the focused test command\n"
        got = carried_of(with_line)
        self.assertTrue(got["checked"])
        self.assertEqual(got, {label: True for label, _, _ in export.CARRIED})  # the two dropped lines served no other label
        only = carried_of("Checked by: a review loop\n")
        self.assertEqual([k for k, v in only.items() if v], ["checked"])
        self.assertFalse(carried_of("The result is Checked by: nobody\n")["checked"])  # a line starting with it, not a mention
        half = "\n".join(l for l in new.split("\n") if not l.startswith("Done when ("))
        self.assertFalse(carried_of(half)["checked"])  # the old rule still needs both of its groups

    def test_a_row_gets_carried_from_the_whole_packet_text_and_a_packet_with_a_late_marker_counts(self):
        out = make_run(self.tmp, loops=False)
        packet = run_dir_of(out) / "packets" / f"{IDS['implement']}.md"
        text = packet_fixture("packet-lines-1220.txt").replace("\nImprove: ", "\n" + "filler\n" * 40_000 + "Improve: ")
        packet.write_text(text, encoding="utf-8")
        self.assertGreater(len(text.encode()), export.MAX_PACKET_TEXT)  # past the document's cut: still read whole
        row = self.row(out, "implement")
        self.assertEqual(row["carried"], {label: True for label, _, _ in export.CARRIED})
        self.assertIs(row["packetDoc"], True)
        self.assertNotIn("packetImprove", row)

    def test_an_improve_childs_packet_is_marked_and_no_label_is_read_from_it(self):
        out = make_run(self.tmp, loops=False)
        (run_dir_of(out) / "packets" / f"{IDS['spec']}.md").write_text(
            packet_fixture("packet-lines-1220-improve.txt"), encoding="utf-8")
        row = self.row(out, "spec")
        self.assertIs(row["packetImprove"], True)
        self.assertNotIn("carried", row)
        self.assertIs(row["packetDoc"], True)  # the packet box still shows the file that exists
        self.assertEqual(export.validate_doc("runs", export.build_run(out)[0]["runs"][self.KEY]), [])

    def test_carried_is_absent_when_the_packet_text_was_not_readable_or_there_was_no_packet(self):
        out = make_run(self.tmp, loops=False)
        run = run_dir_of(out)
        (run / "packets" / f"{IDS['spec']}.md").write_bytes(b"\xff\xfe not utf-8 \x80")
        (run / "packets" / f"{IDS['plan']}.md").unlink()
        docs, facts = export.build_run(out)
        rows = {r["stage"]: r for r in docs["runs"][self.KEY]["stages"]}
        for stage in ("spec", "plan"):
            self.assertNotIn("carried", rows[stage], stage)
            self.assertNotIn("packetImprove", rows[stage], stage)
        self.assertIn("carried", rows["intake"])  # the fixture's other packets are readable text: every label false, none invented
        self.assertEqual(set(rows["intake"]["carried"].values()), {False})
        self.assertIn("producer packets read", "\n".join(facts))

    def test_facts_count_the_labels_the_packets_carried_and_the_improve_packets_not_read(self):
        out = make_run(self.tmp, loops=False)
        run = run_dir_of(out)
        (run / "packets" / f"{IDS['spec']}.md").write_text(packet_fixture("packet-lines-1220-improve.txt"), encoding="utf-8")
        (run / "packets" / f"{IDS['intake']}.md").write_text(packet_fixture("packet-lines-1161.txt"), encoding="utf-8")
        line = next(l for l in export.build_run(out)[1] if l.startswith("- Packet text carried"))
        self.assertIn(f"producer packets read {len(ACCEPTS) - 1}; 0 visits have a separate Improve packet file; "
                      "1 visits (old layout) keep only an Improve child's packet", line)
        self.assertIn("where 1, purpose 1, operates 1, checked 1, produces 1, recovery 1, inputs 1", line)

    def test_validate_doc_rejects_wrong_shapes_for_the_card_fields(self):
        run, _ = export.build_run(make_run(self.tmp, loops=False))
        run = run["runs"][self.KEY]
        bad = dict(run, stages=[dict(run["stages"][0], summary=3, summaryTruncated="yes", resultFile=1, carried={"where": "yes"},
                                     packetImprove="no")])
        problems = "\n".join(export.validate_doc("runs", bad))
        for needle in ("stages[0].summary: expected a string", "stages[0].summaryTruncated: expected a boolean",
                       "stages[0].resultFile: expected a boolean", "stages[0].carried.where: expected a boolean",
                       "stages[0].packetImprove: expected a boolean"):
            self.assertIn(needle, problems)

    def test_the_committed_evidence_still_validates_without_any_card_field(self):  # a guard: it passes before this change too
        for name in EVIDENCE_RUNS:
            for run in json.loads((EVIDENCE_DIR / name).read_text())["docs"]["runs"].values():
                self.assertEqual(export.validate_doc("runs", run), [], name)


# ================================================================ R20a part 2: the page (template)

class StageCatalogPageTests(unittest.TestCase):
    """The page's reading of the catalog: aliases, readers and the labels it shares with the exporter."""

    def test_readers_are_the_inverse_of_reads_and_the_page_computes_the_same_list(self):
        inverse = {}
        for entry in export.stage_catalog(engine_spec()):
            for read in entry["reads"]:
                inverse.setdefault(read.removeprefix("item:"), []).append(
                    {"stage": entry["stage"], "item": read.startswith("item:")})
        page = run_logic("(function(c){var o={};" + json.dumps(list(engine_spec().STAGES)) +
                         ".forEach(function(s){o[s]=readersOf(c,s);});return o;})(" + json.dumps(export.stage_catalog(engine_spec())) + ")")
        for stage in engine_spec().STAGES:
            self.assertEqual(page[stage], inverse.get(stage, []), stage)
        self.assertEqual(page["handoff"], [])  # nothing reads the last stage
        self.assertIn({"stage": "test-green", "item": True}, page["implement"])
        self.assertIsNone(run_logic('readersOf(null,"spec")'))  # no catalog: unknown, never "no readers"

    def test_the_page_aliases_resolve_either_name_to_one_group_and_one_phase(self):
        self.assertEqual(run_logic('[stageNames("select-work"),stageNames("get-next-work-item"),stageNames("spec")]'),
                         [list(g) for g in export.STAGE_ALIASES] * 2 + [["spec"]])
        self.assertEqual(run_logic("STAGE_ALIASES"), [list(g) for g in export.STAGE_ALIASES])  # the page's table equals the exporter's
        self.assertEqual(run_logic('[phaseOfStage("select-work",-1),phaseOfStage("get-next-work-item",-1),phaseOfStage("nothing",5)]'),
                         [2, 2, 5])

    def test_a_catalog_naming_either_stage_is_found_under_either_name(self):
        for catalog_name in ("select-work", "get-next-work-item"):
            catalog = [{"stage": "spec", "purpose": "p", "exitCheck": "review loop", "reads": []},
                       {"stage": catalog_name, "purpose": "pick", "exitCheck": "model judgement", "reads": ["spec"]}]
            found = run_logic('[stageInfo(%s,"select-work"),stageInfo(%s,"get-next-work-item"),stageInfo(%s,"nothing"),'
                              'stageInfo(null,"spec"),readersOf(%s,"spec")]' % ((json.dumps(catalog),) * 4))
            self.assertEqual(found[0], catalog[1], catalog_name)
            self.assertEqual(found[1], catalog[1], catalog_name)
            self.assertEqual((found[2], found[3]), (None, None))
            self.assertEqual(found[4], [{"stage": catalog_name, "item": False}])

    def test_the_page_draws_a_row_of_each_name_in_the_plan_phase(self):
        for stage in ("select-work", "get-next-work-item"):
            # an unknown stage takes the phase of the visit before it, so the name must be known to land in Plan after intake
            run = {"key": "k", "stages": [{"stage": "intake", "outcome": "done"}, {"stage": stage, "outcome": "done"},
                                          {"stage": "step-plan", "outcome": "done"}]}
            strip = run_logic('whereStrip(%s,{phase:2})' % json.dumps(run))
            self.assertIn("Plan: 2 of 3 visits", strip, stage)

    def test_schema_md_documents_the_stage_card_the_reader_labels_and_the_reserved_audit(self):
        schema = " ".join(SCHEMA_MD.read_text(encoding="utf-8").split())
        for phrase in ("## The stage card", "\"Stage cards\" list", "declared by the stage spec",
                       "no stage declares reading it", "records no observed reads", "not recorded per visit", "xN skipped"):
            self.assertIn(phrase, schema, phrase)


# A run for the card tests: a real-shaped run with a revise, an Improve child's packet, skipped visits, a seeded one and a
# visit whose packet text lacked its recovery sentence.
CARRIED_KEYS = ("where", "purpose", "operates", "checked", "produces", "recovery", "inputs")  # a test keeps them equal to export.CARRIED
ALL_CARRIED = {label: True for label in CARRIED_KEYS}
CARD_RUN = {
    "key": "cr", "name": "Card run", "order": 1, "release": "r", "time": "t", "imp": "i", "wallMin": 40, "refusals": 13,
    "planningReview": "stage", "phases": ["done"] * 4 + ["none"] * 4, "unmeasured": {},
    "stages": [
        {"stage": "intake", "outcome": "done", "min": 1, "action": "nav-a1", "packetBytes": 27_172, "packetDoc": True,
         "resultFile": True, "resultBytes": 1_593, "summary": "Outcomes: <script>alert(1)</script> and more", "summaryTruncated": True,
         "carried": dict(ALL_CARRIED, inputs=False)},
        {"stage": "spec", "outcome": "done", "min": 4, "action": "nav-a2", "packetBytes": 46_170, "packetDoc": True,
         "packetImprove": True, "improve": {"passes": 3, "min": 3.3}, "resultFile": True, "resultBytes": 1_239, "summary": "Living spec"},
        {"stage": "get-next-work-item", "outcome": "done", "min": 1, "action": "nav-a3", "workitem": "W1", "loop": 1, "packetBytes": 30_000,
         "packetDoc": True, "resultFile": True, "resultBytes": 700, "summary": "Still the right item", "carried": ALL_CARRIED},
        {"stage": "skill-assess", "outcome": "done", "action": "nav-a4", "workitem": "W1", "loop": 1, "skipped": True, "min": 0,
         "resultFile": True, "resultBytes": 300},
        {"stage": "skill-validate", "outcome": "done", "action": "nav-a5", "workitem": "W1", "loop": 1, "skipped": True, "min": 0,
         "resultFile": True, "resultBytes": 300},
        {"stage": "implement", "outcome": "revise", "min": 6, "action": "nav-a6", "workitem": "W1", "loop": 1, "step": "S1",
         "packetBytes": 40_677, "packetDoc": True, "resultFile": True, "resultBytes": 1_300, "summary": "S1 cannot be built",
         "carried": dict(ALL_CARRIED, recovery=False), "context": {"calls": 9, "peak": 100_000, "peakPct": 10, "compactions": 0}},
        {"stage": "implement", "outcome": "done", "min": 8, "action": "nav-a7", "workitem": "W1", "loop": 2, "step": "S1",
         "packetBytes": 41_000, "packetDoc": True, "resultFile": False, "summary": "Built S1", "carried": ALL_CARRIED,
         "context": {"calls": 12, "peak": 120_000, "peakPct": 12, "compactions": 1}},
        {"stage": "system-test-author", "outcome": "done", "seeded": True, "action": "nav-a8", "resultFile": True}],
    "workItems": [{"id": "W1", "title": "The item", "stepPlans": 1, "loops": 2, "revises": 1, "repeats": 0,
                   "implementVisits": {"done": 1, "repeat": 0, "revise": 1, "replan": 0, "blocked": 0}}]}


def readers_text(stage: str) -> str:
    """The card's 'Read by' text for a stage, worked out in Python from the committed catalog (the inverse of every `reads`)."""
    catalog = json.loads(STAGES_JSON.read_text(encoding="utf-8"))["stages"]
    run = [e["stage"] for e in catalog if stage in e["reads"]]
    item = [e["stage"] for e in catalog if f"item:{stage}" in e["reads"]]
    parts = [", ".join(run)] if run else []
    if item:
        parts.append(", ".join(item) + (" (these read this work item's result)" if run else " (each reads this work item's result)"))
    return "; ".join(parts) or "no stage declares reading it"


def catalog_json() -> str:
    return json.dumps(json.loads(STAGES_JSON.read_text(encoding="utf-8"))["stages"])


def card_setup(run: dict = CARD_RUN, extra: str = "", catalog: bool = True) -> str:
    return plan_setup(run, ("data.cfg={stages:{stages:" + catalog_json() + "}};" if catalog else "") + extra)


def card(run: dict, index: int, catalog: bool = True) -> dict:
    return run_logic("stageCard(%s,%d,%s)" % (json.dumps(run), index, catalog_json() if catalog else "null"))


class StageCardLogicTests(unittest.TestCase):
    """stageCard is pure: one visit in, the three blocks out, and only what the export holds."""

    def lines(self, block: list) -> dict:
        return {k: v for k, v in block}

    def test_a_work_visit_reads_purpose_check_checklist_sizes_and_declared_readers_from_the_catalog(self):
        c = card(CARD_RUN, 5)  # the revise visit of implement
        self.assertEqual((c["title"], c["stage"], c["kind"], c["outcome"]), ("Visit 6: Implement", "implement", "work", "revise"))
        self.assertEqual(c["purpose"], "Make the planned change")
        self.assertEqual(c["check"]["kind"], "script-run")
        self.assertIn("lint-gate", c["check"]["why"])
        self.assertEqual(c["sent"]["bytes"], 40_677)
        self.assertEqual([(i["key"], i["found"]) for i in c["sent"]["carried"]],
                         [(l, l != "recovery") for l, _, _ in export.CARRIED])
        recovery = next(i for i in c["sent"]["carried"] if i["key"] == "recovery")
        self.assertIn("not found in the packet text", recovery["tip"])
        self.assertIn("not whether the model needed it", recovery["tip"])
        self.assertTrue(all("found in the packet text:" in i["tip"] for i in c["sent"]["carried"] if i["found"]))
        done = self.lines(c["done"]["lines"])
        self.assertEqual(done["Outcome"], "revise (marked R)")
        self.assertEqual(done["Minutes"], "6 min, 15% of elapsed")
        self.assertEqual((done["Work item"], done["Step"]), ("W1, steps-loop pass 1", "S1 (the step this packet named)"))
        self.assertEqual(done["Revises of this item"], "1 (each sent it back to step-plan)")
        self.assertEqual(done["Refusals"], "not recorded per visit; run-level: 13 (not attributed to a visit)")
        self.assertEqual(done["Context (main thread)"], "9 calls, peak 100,000 tokens (10% of the window), 0 compactions")
        written = self.lines(c["written"]["lines"])
        self.assertEqual(c["written"]["summary"], "S1 cannot be built")
        self.assertEqual(written["Result file"], "written, 1.3 KB")
        self.assertEqual(written["Read by (declared by the stage spec)"], readers_text("implement"))
        self.assertEqual(readers_text("implement"), "test-green, test-refine, document, static-checks, verify "
                         "(each reads this work item's result)")

    def test_readers_read_as_run_level_stages_then_those_that_read_this_work_items_result(self):
        text = run_logic('[readersText([]),readersText(null),readersText([{stage:"a",item:false},{stage:"b",item:false}]),'
                         'readersText([{stage:"c",item:true},{stage:"d",item:true}]),'
                         'readersText([{stage:"a",item:false},{stage:"c",item:true}])]')
        self.assertEqual(text, ["no stage declares reading it", "no stage declares reading it", "a, b",
                                "c, d (each reads this work item's result)", "a; c (these read this work item's result)"])
        self.assertEqual(readers_text("handoff"), "no stage declares reading it")

    def test_a_visit_whose_result_file_is_absent_says_the_result_is_read_from_state_md(self):
        written = self.lines(card(CARD_RUN, 6)["written"]["lines"])
        self.assertEqual(written["Result file"], "none: the accepted result is read from state.md")

    def test_a_visit_that_kept_only_an_improve_childs_packet_shows_no_checklist_and_says_why(self):
        c = card(CARD_RUN, 1)
        self.assertIsNone(c["sent"]["carried"])
        self.assertIn("Improve child's", c["sent"]["carriedNote"])
        self.assertEqual(c["sent"]["bytesLabel"], "Packet file kept (the Improve child's)")
        self.assertEqual(self.lines(c["done"]["lines"])["Improve"], "3 passes, 3.3 min")
        self.assertEqual(c["check"]["kind"], "review loop")
        self.assertEqual(card(CARD_RUN, 0)["sent"]["bytesLabel"], "Packet size")

    def test_a_stage_that_reads_nothing_is_not_marked_missing_its_inputs(self):
        items = {i["key"]: i for i in card(CARD_RUN, 0)["sent"]["carried"]}
        self.assertEqual((items["inputs"]["found"], items["inputs"]["na"]), (False, True))
        self.assertIn("reads no earlier result", items["inputs"]["tip"])
        self.assertFalse(items["purpose"]["na"])
        self.assertEqual(self.lines(card(CARD_RUN, 0)["written"]["lines"])["Read by (declared by the stage spec)"],
                         readers_text("intake"))
        self.assertEqual(readers_text("intake"), "discovery, research, spec, plan, product-acceptance, handoff")

    def test_a_skipped_and_a_seeded_visit_say_so_and_claim_neither_a_packet_nor_a_reader_list(self):
        skipped, seeded = card(CARD_RUN, 3), card(CARD_RUN, 7)
        self.assertEqual((skipped["kind"], skipped["outcome"], seeded["kind"], seeded["outcome"]), ("skipped", "skipped", "seeded", "seeded"))
        self.assertIn("No packet was issued", skipped["sent"]["note"])
        self.assertIn("harness recorded this visit itself", seeded["sent"]["note"])
        for c in (skipped, seeded):
            self.assertIsNone(c["sent"]["carried"])
            self.assertNotIn("Read by (declared by the stage spec)", self.lines(c["written"]["lines"]))
        self.assertEqual(self.lines(skipped["done"]["lines"])["Minutes"], "0 min")  # a skipped visit's span, as the table has it
        self.assertEqual(self.lines(seeded["done"]["lines"])["Outcome"], "seeded: the harness recorded this visit without running it")
        self.assertEqual(self.lines(seeded["done"]["lines"])["Minutes"], "n/a (seeded, never timed)")

    def test_a_run_whose_refusals_are_not_measured_says_so_with_the_reason_never_a_count(self):
        run = json.loads(json.dumps(CARD_RUN))
        del run["refusals"]
        run["unmeasured"] = {"shiploop_failures": "Claude's events cannot show it"}
        self.assertEqual(self.lines(card(run, 0)["done"]["lines"])["Refusals"],
                         "not recorded per visit; run-level not measured (the reason is on the Refusals card)")
        del run["unmeasured"]
        self.assertEqual(self.lines(card(run, 0)["done"]["lines"])["Refusals"], "not recorded per visit; run-level not measured")

    def test_a_planning_stage_of_a_none_run_is_the_models_judgement_and_the_card_says_why(self):
        run = dict(CARD_RUN, planningReview="none")
        spec = card(run, 1)
        self.assertEqual(spec["check"]["kind"], "model judgement")
        self.assertIn("planning_review none", spec["check"]["why"])
        self.assertEqual(self.lines(spec["done"]["lines"])["Improve"], "3 passes, 3.3 min")  # measured figures stay, as in R18
        self.assertEqual(card(dict(CARD_RUN, planningReview="stage"), 1)["check"]["kind"], "review loop")
        self.assertIn("last work item", run_logic('exitCheckWhy({stage:"carry-forward",exitCheck:"review loop",improve:"last-item"},{})'))

    def test_the_exit_check_of_every_stage_in_every_mode_equals_the_exporters_rule(self):
        catalog = export.stage_catalog(engine_spec())
        modes = [m for m in MODES]
        page = run_logic("(function(c,modes){return c.map(function(e){return modes.map(function(m){"
                         "return exitCheckOf(e,m===null?{}:{planningReview:m});});});})(%s,%s)" % (json.dumps(catalog), json.dumps(modes)))
        for entry, got in zip(catalog, page):
            self.assertEqual(got, [export.effective_exit_check(entry, m) for m in modes], entry["stage"])
        self.assertEqual(run_logic('[exitCheckOf(null,{}),exitCheckOf({exitCheck:"nonsense"},{}),exitCheckWhy(null,{})]'), ["", "", ""])

    def test_an_old_row_with_none_of_the_new_fields_prints_only_what_exists_and_names_nothing_as_zero(self):
        run = {"key": "old", "stages": [{"stage": "plan", "outcome": "done", "min": 3.5, "action": "nav-p"}], "wallMin": 35}
        c = card(run, 0, catalog=False)
        self.assertEqual((c["purpose"], c["check"], c["sent"]["bytes"], c["sent"]["carried"], c["sent"]["carriedNote"], c["sent"]["packet"]),
                         ("", None, None, None, "", None))
        self.assertEqual(c["written"], {"summary": "", "truncated": False, "lines": [], "readers": None})
        self.assertEqual([k for k, _ in c["done"]["lines"]], ["Outcome", "Minutes", "Refusals"])
        self.assertEqual(self.lines(c["done"]["lines"])["Minutes"], "3.5 min, 10% of elapsed")
        self.assertNotRegex(json.dumps(c), r'"0 |\b0 KB|undefined|null"')
        withcat = card(run, 0)  # the catalog alone adds purpose, check and readers, still no packet or result claim
        self.assertEqual((withcat["purpose"], withcat["check"]["kind"]), ("Build the dependency plan and the work-item queue", "review loop"))
        self.assertEqual(self.lines(withcat["written"]["lines"]), {"Read by (declared by the stage spec)": readers_text("plan")})
        self.assertIsNone(run_logic("stageCard({stages:[]},0,null)"))
        self.assertIsNone(run_logic("stageCard(null,0,null)"))

    def test_a_bare_export_with_a_packet_file_but_no_checklist_says_it_is_not_recorded_in_this_export(self):
        run = {"key": "k", "stages": [{"stage": "plan", "outcome": "done", "min": 1, "action": "nav-p", "packetBytes": 100, "packetDoc": True}]}
        c = card(run, 0, catalog=False)
        self.assertIn("not recorded in this export", c["sent"]["carriedNote"])
        self.assertEqual(c["sent"]["packet"], {"id": "k--nav-p"})

    def test_the_old_and_new_detail_lines_agree_where_they_overlap(self):
        model = "sequenceModel(%s,{})" % json.dumps(CARD_RUN)
        detail = run_logic("(function(m){return [5,6].map(function(k){var d=columnDetail(m,k,%s,[],%s);return {lines:d.lines,card:d.card};});})(%s)"
                           % (json.dumps(CARD_RUN), catalog_json(), model))
        for d in detail:
            card_lines = self.lines(d["card"]["done"]["lines"])
            old = self.lines(d["lines"])
            for label in ("Outcome", "Minutes", "Work item", "Step", "Improve", "Context (main thread)"):
                if label in old:
                    self.assertEqual(card_lines.get(label), old[label], label)

    def test_the_packet_head_is_the_first_twelve_non_empty_lines(self):
        text = "\n".join(["", "one", "", "two   ", *[f"line {n}" for n in range(3, 30)]])
        head = run_logic("packetHeadLines(%s,12)" % json.dumps(text))
        self.assertEqual(head, ["one", "two"] + [f"line {n}" for n in range(3, 13)])
        self.assertEqual(run_logic('[packetHeadLines("",12),packetHeadLines(null,12),packetHeadLines("a\\n\\n \\nb",12)]'), [[], [], ["a", "b"]])

    def test_the_labels_these_tests_use_are_the_exporters_in_the_exporters_order(self):  # a consistency check: the exporter half exists before the page does
        self.assertEqual(CARRIED_KEYS, tuple(label for label, _, _ in export.CARRIED))

    def test_the_page_labels_and_aliases_equal_the_exporters(self):
        self.assertEqual(run_logic("CARRIED_LABELS"), [[label, label, description] for label, description, _ in export.CARRIED])
        self.assertEqual(run_logic("EXIT_CHECKS"), list(export.EXIT_CHECKS))
        self.assertEqual(export.EXIT_CHECKS, ("script-run", "model judgement", "review loop"))


class StageLabelTests(unittest.TestCase):
    """A stage is named for display by one derived rule: hyphens to spaces, first letter upper-cased; the raw name stays."""

    def test_the_label_is_derived_from_the_name_and_the_raw_name_is_shown_only_when_it_differs(self):
        self.assertEqual(run_logic('["get-next-work-item","system-test-author","select-work","spec","implement","",undefined,null,7].map(stageLabel)'),
                         ["Get next work item", "System test author", "Select work", "Spec", "Implement", "", "", "", ""])
        self.assertEqual(run_logic('["get-next-work-item","spec","",undefined].map(rawShown)'), [True, False, False, False])
        for stage in engine_spec().STAGES:  # every engine stage reads as plain words, with no hyphen left
            label = run_logic("stageLabel(%s)" % json.dumps(stage))
            words = stage.replace("-", " ")
            self.assertEqual(label, words[0].upper() + words[1:])
            self.assertNotIn("-", label)

    def test_the_card_titles_use_the_label_with_the_raw_name_as_tooltip_and_secondary_text_for_a_hyphenated_stage(self):
        run = json.loads(json.dumps(CARD_RUN))
        run["stages"][7]["stage"] = "get-next-work-item"
        self.assertEqual((card(run, 7)["title"], card(run, 7)["label"], card(run, 7)["rawShown"]),
                         ("Visit 8: Get next work item", "Get next work item", True))
        out = page_probe('setCol(6);var h3=walk(REG.seqdetail,function(e){return e.tagName==="h3";})[0];'
                         '[h3.textContent,h3.title,byClass(h3,"sc-raw").map(function(x){return x.textContent;})]', setup=card_setup(run))
        self.assertEqual(out, ["Visit 8: Get next work itemget-next-work-item", "get-next-work-item", ["get-next-work-item"]])
        plain = page_probe('setCol(4);var h3=walk(REG.seqdetail,function(e){return e.tagName==="h3";})[0];[h3.textContent,h3.title,byClass(h3,"sc-raw").length]',
                           setup=card_setup())
        self.assertEqual(plain, ["Visit 6: Implement", "implement", 0])  # one word: the raw name would only repeat it

    def test_the_list_rows_use_the_label_with_the_raw_name_as_tooltip_and_the_skipped_group_keeps_its_own_text(self):
        for stage, label in (("get-next-work-item", "Get next work item"), ("select-work", "Select work")):  # the old name is history
            run = json.loads(json.dumps(CARD_RUN))
            run["stages"][2]["stage"] = stage
            out = page_probe('var rows=byClass("sclist","sc-row");[rows[2].title,byClass(rows[2],"sc-name")[0].textContent,'
                             'byClass(rows[2],"sc-raw").map(function(x){return x.textContent;}),rows[3].title||"",byClass(rows[3],"sc-name")[0].textContent,'
                             'byClass(rows[4],"sc-raw").length]', setup=card_setup(run))
            self.assertEqual(out, [stage, label + stage, [stage], "", "x2 skipped", 0], stage)


class StageCardListTests(unittest.TestCase):
    """One row per column of the picture, so a tap selects the same visit as a tap on the picture."""

    def rows(self, run: dict = CARD_RUN, catalog: bool = True) -> list:
        return run_logic("cardRows(sequenceModel(%s,{}),%s,%s)" % (json.dumps(run), json.dumps(run), catalog_json() if catalog else "null"))

    def test_rows_follow_the_columns_collapse_skipped_visits_and_print_only_what_the_export_holds(self):
        rows = self.rows()
        self.assertEqual([r["col"] for r in rows], list(range(7)))  # eight visits, two skipped in a row are one column
        self.assertEqual([(r["visit"], r["stage"]) for r in rows],
                         [("1", "Intake"), ("2", "Spec"), ("3", "Get next work item"), ("4 to 5", "x2 skipped"), ("6", "Implement"),
                          ("7", "Implement"), ("8", "System test author")])
        self.assertEqual([(r["raw"], r["rawShown"]) for r in rows],
                         [("intake", False), ("spec", False), ("get-next-work-item", True), ("", False), ("implement", False),
                          ("implement", False), ("system-test-author", True)])
        spec, skipped, revise = rows[1], rows[3], rows[4]
        self.assertEqual((spec["sent"], spec["written"], spec["check"], spec["outcome"], spec["min"]),
                         ("45.1 KB (the Improve child's)", "1.2 KB", "review loop", "done", "4 min"))
        self.assertEqual(spec["purpose"], "Define required behavior and acceptance criteria")
        self.assertEqual((skipped["outcome"], skipped["check"], skipped["sent"], skipped["written"], skipped["readBy"], skipped["purpose"]),
                         ("skipped", "", "", "", None, ""))
        self.assertEqual((revise["outcome"], revise["check"], revise["readBy"], revise["sent"], revise["written"]),
                         ("revise", "script-run", 5, "39.7 KB", "1.3 KB"))
        self.assertEqual(rows[6]["outcome"], "seeded")
        self.assertEqual(rows[6]["min"], "")

    def test_a_stage_no_one_declares_reading_says_so_instead_of_a_count_that_reads_as_observed(self):
        run = {"key": "k", "stages": [{"stage": "handoff", "outcome": "done", "min": 1, "action": "nav-h", "resultBytes": 100}]}
        row = run_logic("cardRows(sequenceModel(%s,{}),%s,%s)" % (json.dumps(run), json.dumps(run), catalog_json()))[0]
        self.assertEqual(row["readBy"], 0)  # the model keeps the number; the page words it
        out = page_probe('byClass("sclist","sc-bit").map(function(b){return b.textContent;})', setup=card_setup(dict(CARD_RUN, **run)))
        self.assertIn("no declared reader", out)
        self.assertNotIn("declared readers 0", out)
        self.assertFalse([b for b in out if re.search(r"\bread by\b", b)])  # no wording that could pass for an observation

    def test_a_row_without_a_catalog_or_sizes_prints_nothing_for_them(self):
        rows = self.rows({"key": "old", "stages": [{"stage": "plan", "outcome": "done", "min": 3.5}]}, catalog=False)
        self.assertEqual(rows, [{"col": 0, "visit": "1", "stage": "Plan", "raw": "plan", "rawShown": False, "purpose": "",
                                 "outcome": "done", "kind": "work", "check": "", "sent": "", "written": "", "readBy": None,
                                 "min": "3.5 min"}])

    def test_a_run_of_skipped_visits_is_one_row_and_a_single_skipped_visit_keeps_its_name(self):
        run = {"key": "k", "stages": [{"stage": "a", "outcome": "done", "min": 1}, {"stage": "skill-assess", "outcome": "done", "skipped": True},
                                      {"stage": "b", "outcome": "done", "min": 1}, {"stage": "skill-validate", "outcome": "done", "skipped": True}]}
        rows = self.rows(run, catalog=False)
        self.assertEqual([(r["visit"], r["stage"], r["outcome"]) for r in rows],
                         [("1", "A", "done"), ("2", "Skill assess", "skipped"), ("3", "B", "done"), ("4", "Skill validate", "skipped")])


class StageCardPageTests(unittest.TestCase):
    """The card on the page: three labelled blocks, Prev and Next that keep working, the list, escaping and the shared packet get."""

    def test_the_card_has_the_three_blocks_the_chips_the_checklist_and_the_purpose(self):
        out = page_probe('setCol(4);[byClass("seqdetail","sc-block").map(function(b){return b.children[0].textContent;}),'
                         'byClass("seqdetail","chip").map(function(c){return c.textContent;}),textOf("seqdetail")]', setup=card_setup())
        blocks, chips, text = out
        self.assertEqual(blocks, ["Sent: the packet", "Done: how the visit went", "Written: the result"])
        self.assertIn("revise", chips)
        self.assertIn("exit check: script-run", chips)
        self.assertIn("✓ where", chips)
        self.assertIn("✗ recovery", chips)
        self.assertIn("What the stage is for. Make the planned change.", text)
        self.assertIn("How it is checked: script-run. ShipLoop runs lint-gate before it accepts done.", text)
        self.assertIn("not found in the packet text", text)  # the legend, readable without hovering
        self.assertIn("Packet size39.7 KB", text)
        self.assertIn("Summary. S1 cannot be built", text)
        self.assertIn("Read by (declared by the stage spec)", text)

    def test_previous_and_next_walk_the_visits_and_the_card_follows(self):
        out = page_probe('setCol(2);var go=function(label){byClass("seqdetail","btn").filter(function(b){return b.textContent===label;})[0].onclick();};'
                         'var a=textOf("seqdetail").indexOf("Visit 3: Get next work item")>=0;go("Next visit");var b=pickedCol,t1=textOf("seqdetail").indexOf("Visits 4 to 5: 2 skipped")>=0;'
                         'go("Next visit");var c=textOf("seqdetail").indexOf("Visit 6: Implement")>=0;go("Previous visit");go("Previous visit");'
                         '[a,b,t1,c,pickedCol,byClass("seqdetail","btn").map(function(x){return x.textContent+":"+x.disabled;}).filter(function(s){return s.indexOf("Show")<0;})]', setup=card_setup())
        self.assertEqual(out[:5], [True, 3, True, True, 2])
        self.assertEqual(out[5], ["Previous visit:false", "Next visit:false", "Close:false"])

    def test_a_collapsed_skipped_column_keeps_the_old_lines_and_no_card(self):  # a guard: it passes before this change too
        out = page_probe('setCol(3);[byClass("seqdetail","sc-block").length,textOf("seqdetail")]', setup=card_setup())
        self.assertEqual(out[0], 0)
        self.assertIn("Visits 4 to 5: 2 skipped", out[1])
        self.assertIn("skill-assess, skill-validate", out[1])

    def test_the_summary_with_markup_is_text_never_an_element_and_the_cut_is_said(self):
        out = page_probe('setCol(0);[textOf("seqdetail"),walk(REG.seqdetail,function(e){return e.tagName==="script";}).length]', setup=card_setup())
        self.assertIn("Summary. Outcomes: <script>alert(1)</script> and more\u2026 (cut at 300 characters)", out[0])
        self.assertEqual(out[1], 0)
        html = TEMPLATE.read_text(encoding="utf-8")
        code = html[html.index("function renderCard("):html.index("/* The \"scroll sideways\" hint")]
        self.assertNotIn("innerHTML", code)  # built with createElement and textContent only

    def test_the_list_has_a_row_per_column_marks_the_picked_one_and_a_tap_selects_the_same_visit(self):
        out = page_probe('var rows=function(){return byClass("sclist","sc-row");};var n=rows().length,hidden=REG.sclist.hidden,first=rows()[4].textContent,'
                         'bits=byClass(rows()[4],"sc-bit").map(function(b){return b.textContent;});'
                         'rows()[4].onclick();var a=[pickedCol,rows()[4].className,rows()[4].attrs["aria-pressed"],rows()[0].attrs["aria-pressed"]];'
                         'rows()[3].onclick();[n,hidden,first,a,pickedCol,textOf("seqdetail").indexOf("Visits 4 to 5")>=0,rows()[3].textContent,bits]', setup=card_setup())
        self.assertEqual((out[0], out[1]), (7, False))
        for part in ("6", "Implement", "revise", "script-run", "Make the planned change"):
            self.assertIn(part, out[2])
        self.assertEqual(out[7], ["6 min", "sent 39.7 KB", "written 1.3 KB", "declared readers 5"])  # one span each, so a phone wraps between them
        self.assertEqual(out[3], [4, "sc-row sel", "true", "false"])
        self.assertEqual(out[4], 3)
        self.assertTrue(out[5])
        self.assertIn("x2 skipped", out[6])
        self.assertIn("skipped", out[6])

    def test_the_list_sits_between_the_card_and_the_table_and_a_run_with_no_visits_hides_it(self):
        html = TEMPLATE.read_text(encoding="utf-8")
        self.assertLess(html.index('id="seqdetail"'), html.index('id="sclist"'))
        self.assertLess(html.index('id="sclist"'), html.index('id="seqtabbox"'))
        out = page_probe('[REG.sclist.hidden,byClass("sclist","sc-row").length]', setup=card_setup(dict(CARD_RUN, stages=[])))
        self.assertEqual(out, [True, 0])

    def test_without_the_catalog_or_the_new_fields_the_page_still_draws_a_card_and_a_list_from_what_exists(self):
        old = {"key": "old", "name": "Old", "order": 1, "release": "r", "time": "t", "imp": "i", "wallMin": 10,
               "phases": ["done"] * 8, "stages": [{"stage": "plan", "outcome": "done", "min": 3.5, "action": "nav-p", "packetBytes": 100,
                                                  "resultBytes": 50}]}
        out = page_probe('setCol(0);[textOf("seqdetail"),textOf("sclist"),byClass("seqdetail","chip").map(function(c){return c.textContent;})]',
                         setup=card_setup(old, catalog=False))
        self.assertIn("Visit 1: Plan", out[0])
        self.assertIn("Packet size100 B", out[0])
        self.assertIn("Result filewritten, 50 B", out[0])
        self.assertNotIn("exit check", " ".join(out[2]))
        self.assertNotRegex(out[0] + out[1], r"undefined|NaN|\bnull\b")
        self.assertIn("Plan", out[1])

    def test_the_real_evidence_rows_render_a_card_and_a_list_with_and_without_the_catalog(self):
        for key in ("luna1", "hello-1190b"):
            for with_catalog in (True, False):
                setup = with_run(key).replace("renderAll();", ("data.cfg={stages:{stages:" + catalog_json() + "}};" if with_catalog else "") + "renderAll();")
                out = page_probe('setCol(10);[textOf("seqdetail"),byClass("sclist","sc-row").length,textOf("sclist")]', setup=setup)
                self.assertIn("Visit 11:", out[0], (key, with_catalog))
                self.assertGreater(out[1], 10)
                self.assertNotRegex(out[0] + out[2], r"undefined|NaN|\bnull\b", (key, with_catalog))
                self.assertEqual("exit check:" in out[0], with_catalog, (key, with_catalog))
                self.assertEqual("script-run" in out[2] or "review loop" in out[2] or "model judgement" in out[2], with_catalog)

    def test_a_select_work_visit_and_a_get_next_work_item_visit_both_get_the_catalogs_card(self):
        for stage in ("select-work", "get-next-work-item"):
            run = json.loads(json.dumps(CARD_RUN))
            run["stages"][2]["stage"] = stage
            c = card(run, 2)
            purpose = next(e["purpose"] for e in export.stage_catalog(engine_spec()) if e["stage"] in export.stage_names(stage))
            self.assertEqual((c["purpose"], c["check"]["kind"]), (purpose[0].upper() + purpose[1:], "model judgement"), stage)


class PacketHeadTests(unittest.TestCase):
    """The card's packet head is the same document as the Packet box: one get, one cache, loaded on demand."""

    TEXT = "\n".join(["Continue in this context.", "", *[f"line {n}" for n in range(1, 40)]]) + "\n"
    DOC = {"run": "cr", "action": "nav-a6", "stage": "implement", "bytes": len(TEXT), "shownBytes": len(TEXT), "sha256": "ab" * 32, "text": TEXT}

    def probe(self, expression: str, docs: dict | None = None, extra: str = ""):
        return page_probe(expression, setup=card_setup(extra=("PACKET_DOCS=" + json.dumps(docs if docs is not None else {"packets/cr--nav-a6": self.DOC}) + ";") + extra))

    def test_nothing_is_read_until_the_viewer_asks_and_then_one_get_serves_the_head_and_the_box(self):
        out = self.probe('setCol(4);var before=DB_CALLS.slice(),btn=byClass("seqdetail","btn").filter(function(b){return b.textContent==="Show the packet head";})[0];'
                         'btn.onclick();var after=DB_CALLS.slice(),head=byClass("seqdetail","pkt-head")[0].textContent;'
                         'var box=byClass("seqdetail","pkt")[0];box.open=true;box.ontoggle();renderAll();'
                         '[before,after,head,DB_CALLS.length,byClass("seqdetail","pkt-text")[0].textContent.length,'
                         'byClass("seqdetail","btn").filter(function(b){return b.textContent==="Show the packet head";}).length]')
        before, after, head, calls, full, buttons = out
        self.assertEqual(before, [])
        self.assertEqual(after, [["get", "packets/cr--nav-a6"]])
        self.assertEqual(head.split("\n"), ["Continue in this context."] + [f"line {n}" for n in range(1, 12)])  # 12 non-empty lines
        self.assertEqual((calls, full, buttons), (1, len(self.TEXT), 0))  # the box reused the cache; the head survived a redraw

    def test_opening_the_box_first_fills_the_head_too_and_a_second_visit_loads_its_own_document(self):
        out = self.probe('setCol(4);var box=byClass("seqdetail","pkt")[0];box.open=true;box.ontoggle();'
                         '[byClass("seqdetail","pkt-head").length,DB_CALLS.length]')
        self.assertEqual(out, [1, 1])
        two = self.probe('setCol(4);byClass("seqdetail","btn").filter(function(b){return b.textContent==="Show the packet head";})[0].onclick();'
                         'setCol(5);var b=byClass("seqdetail","btn").filter(function(b){return b.textContent==="Show the packet head";}),before=DB_CALLS.length;'
                         'b[0].onclick();[b.length,before,DB_CALLS.slice(),textOf("seqdetail").indexOf("packet not uploaded for this run")>=0]')
        self.assertEqual(two, [1, 1, [["get", "packets/cr--nav-a6"], ["get", "packets/cr--nav-a7"]], True])  # visit 7 asks only when tapped, for its own document

    def test_a_missing_document_and_a_failed_read_say_so_and_the_head_can_be_tried_again(self):
        missing = self.probe('setCol(4);byClass("seqdetail","btn").filter(function(b){return b.textContent==="Show the packet head";})[0].onclick();textOf("seqdetail")',
                             docs={})
        self.assertIn("packet not uploaded for this run", missing)
        failed = self.probe('db.doc=function(p){return {get:function(){return sync({code:"unavailable"},true);}};};setCol(4);'
                            'byClass("seqdetail","btn").filter(function(b){return b.textContent==="Show the packet head";})[0].onclick();'
                            '[textOf("seqdetail").indexOf("Could not read the packet.")>=0,byClass("seqdetail","btn").map(function(b){return b.textContent;}).indexOf("Try again")>=0]')
        self.assertEqual(failed, [True, True])

    def test_the_head_text_is_never_markup_and_without_a_database_there_is_no_head_or_box(self):
        evil = dict(self.DOC, text="<script>alert(1)</script>\n<b>bold</b>\n")
        out = self.probe('setCol(4);byClass("seqdetail","btn").filter(function(b){return b.textContent==="Show the packet head";})[0].onclick();'
                         '[byClass("seqdetail","pkt-head")[0].textContent,walk(REG.seqdetail,function(e){return e.tagName==="script";}).length,'
                         'byClass("seqdetail","pkt-head")[0].children.length]', docs={"packets/cr--nav-a6": evil})
        self.assertEqual(out, ["<script>alert(1)</script>\n<b>bold</b>", 0, 0])
        setup = card_setup().replace("live=true;", "db=null;live=false;")
        self.assertEqual(page_probe('setCol(4);[byClass("seqdetail","pkt").length,byClass("seqdetail","pkt-headbox").length]', setup=setup), [0, 0])

    def test_the_page_has_one_packet_fetch_path_and_never_subscribes_to_packets(self):  # a guard: it passes before this change too
        page = script_text()
        self.assertEqual(re.findall(r'db\.doc\("packets/"\+id\)\.get\(\)', page), ['db.doc("packets/"+id).get()'])
        self.assertNotIn('collection("packets")', page)


# ================================================================ R21: the two packet files of a visit, and the packet head

ENGINE_SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
# The harness's seed pattern (test/shiploop_e2e/run.py SEED_SCRIPT) on the checkout's own navigator, with no model: it walks the
# graph on synthetic results to the first inner stage and PRINTS every packet (navigator.emit), so packets/ is what that engine
# writes: one file per action up to ShipLoop 1.22.0, a producer file plus `<action>-improve.md` for a reviewed stage after.
REAL_ENGINE_SEED = r"""
import contextlib, io, json, os, subprocess, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
scripts, out = Path(sys.argv[1]), Path(sys.argv[2])
work = out / "work"
work.mkdir(parents=True)
env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
for args in (["init", "-q"], ["add", "README.md"], ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "seed"]):
    if args[0] == "init":
        (work / "README.md").write_text("# seeded\n")
    subprocess.run(["git", "-C", str(work), *args], check=True, capture_output=True, env=env)
root = out / ".shiploop-runs" / "seed"
started = subprocess.run([sys.executable, str(scripts / "shiploop"), "workspace", "start", f"--repo={work}",
                          f"--workspace-root={root}", "--delegation=inline", "--prompt=Build a tiny thing."],
                         capture_output=True, text=True, env=env)
assert started.returncode == 0, started.stderr[-1500:] + started.stdout[-1500:]
run_dir = root / "run"
sys.path.insert(0, str(scripts))
import shiploop_navigator as nav, shiploop_store as store
state = store.read_record(run_dir / "state.md")
stop = nav.stage_spec.INNER[0]
t0 = datetime(2026, 10, 7, 9, 0, tzinfo=timezone.utc)
accepted, visits = {}, []
def emit(s):
    with contextlib.redirect_stdout(io.StringIO()):
        nav.emit(None, run_dir, s)
while nav.current_stage(state) != stop:
    stage, action = nav.current_stage(state), str(nav.current_action(state)["id"])
    emit(state)
    result = {"outcome": "done", "headline": "Synthetic", "summary": f"Synthetic {stage} result.", "evidence_refs": ["/synthetic"]}
    if stage == "plan":
        result["work_items"] = [{"id": "W1", "title": "The whole request"}]
    state = nav.apply(state, action, result)
    nav.save(run_dir, state)
    reviewed = state["active_improve"] is not None
    if reviewed:
        emit(state)
        state = nav.finish_improve(state, action, {"summary": "Synthetic Improve receipt."})
        nav.save(run_dir, state)
    accepted[action] = (t0 + timedelta(minutes=2 * (len(visits) + 1))).strftime("%Y-%m-%dT%H:%M:%SZ")
    visits.append({"stage": stage, "action": action, "reviewed": reviewed})
(run_dir / "timeline.json").write_text(json.dumps({"started": t0.strftime("%Y-%m-%dT%H:%M:%SZ"), "accepted": accepted}))
(out / "metrics.json").write_text(json.dumps({"unmeasured": {}, "shiploop_failures": [], "model_glue": [], "model_calls": 1}))
print(json.dumps(visits))
"""


def real_engine_run(tmp: Path) -> tuple[Path, list[dict]]:
    """(a run output directory the checkout's own navigator wrote with no model, its visits as {stage, action, reviewed})."""
    out = tmp / "engine-run"
    done = subprocess.run([sys.executable, "-B", "-c", REAL_ENGINE_SEED, str(ENGINE_SCRIPTS), str(out)],
                          capture_output=True, text=True, timeout=300)
    if done.returncode:
        raise AssertionError(f"the engine seed failed:\n{done.stderr[-2000:]}")
    return out, json.loads(done.stdout.strip().splitlines()[-1])


class ImprovePacketLayoutTests(unittest.TestCase):
    """The two layouts of a visit's packet files: new (producer file intact, Improve child's file beside it) and old (one file)."""

    KEY = RunReviewTest.KEY

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def build(self, out: Path) -> tuple[dict, dict, list[str]]:
        docs, facts = export.build_run(out)
        return docs["runs"][self.KEY], docs["packets"], facts

    def row(self, run: dict, stage: str) -> dict:
        return next(r for r in run["stages"] if r["stage"] == stage)

    def new_layout(self) -> Path:
        """spec has its real-shaped producer packet and an Improve child's file beside it; plan is a visit with no Improve child."""
        out = make_run(self.tmp, loops=False)
        packets = run_dir_of(out) / "packets"
        (packets / f"{IDS['spec']}.md").write_text(packet_fixture("packet-lines-1220.txt"), encoding="utf-8")
        (packets / f"{IDS['spec']}-improve.md").write_text(packet_fixture("packet-lines-1220-improve.txt"), encoding="utf-8")
        return out

    def test_the_new_layout_writes_a_second_document_and_reads_the_checklist_from_the_intact_producer_packet(self):
        out = self.new_layout()
        run, packets, facts = self.build(out)
        spec = self.row(run, "spec")
        improve = (run_dir_of(out) / "packets" / f"{IDS['spec']}-improve.md")
        self.assertEqual((spec["improvePacketDoc"], spec["improvePacketBytes"], spec["packetDoc"]), (True, improve.stat().st_size, True))
        self.assertEqual(spec["carried"], {label: True for label, _, _ in export.CARRIED})  # read from the producer packet
        self.assertNotIn("packetImprove", spec)
        doc = packets[f"{self.KEY}--{IDS['spec']}-improve"]
        raw = improve.read_bytes()
        self.assertEqual(doc, {"run": self.KEY, "action": IDS["spec"], "stage": "spec", "bytes": len(raw), "shownBytes": len(raw),
                               "sha256": hashlib.sha256(raw).hexdigest(), "text": raw.decode(), "kind": "improve"})
        self.assertEqual(export.validate_doc("packets", doc), [])
        producer = packets[f"{self.KEY}--{IDS['spec']}"]
        self.assertNotIn("kind", producer)  # the producer's document is as before
        self.assertTrue(producer["text"].startswith("ShipLoop navigator | implement"))
        self.assertEqual(export.validate_doc("runs", run), [])

    def test_a_visit_with_no_improve_child_has_no_improve_fields_and_no_second_document(self):
        out = self.new_layout()
        run, packets, _ = self.build(out)
        plan = self.row(run, "plan")
        for field in ("improvePacketDoc", "improvePacketBytes", "packetImprove"):
            self.assertNotIn(field, plan)
        self.assertNotIn(f"{self.KEY}--{IDS['plan']}-improve", packets)
        self.assertEqual(len(packets), len(ACCEPTS) + 1)  # one producer document per visit and the one Improve document

    def test_the_old_layout_keeps_its_packet_improve_mark_and_has_no_improve_fields(self):  # a guard: it passes before this change too
        out = make_run(self.tmp, loops=False)
        (run_dir_of(out) / "packets" / f"{IDS['spec']}.md").write_text(packet_fixture("packet-lines-1220-improve.txt"), encoding="utf-8")
        run, packets, _ = self.build(out)
        spec = self.row(run, "spec")
        self.assertIs(spec["packetImprove"], True)
        self.assertNotIn("carried", spec)
        for field in ("improvePacketDoc", "improvePacketBytes"):
            self.assertNotIn(field, spec)
        self.assertFalse([d for d in packets.values() if d.get("kind")])

    def test_a_beside_file_means_the_producer_file_is_the_producer_even_if_it_mentions_the_improve_line(self):
        out = self.new_layout()
        producer = run_dir_of(out) / "packets" / f"{IDS['spec']}.md"
        producer.write_text(packet_fixture("packet-lines-1220.txt") + "Current action: Improve the completed spec result.\n", encoding="utf-8")
        run, _, _ = self.build(out)
        spec = self.row(run, "spec")
        self.assertNotIn("packetImprove", spec)
        self.assertIn("carried", spec)

    def test_the_two_layouts_can_meet_in_one_run_each_visit_told_by_its_own_files(self):
        out = self.new_layout()  # spec: new layout
        (run_dir_of(out) / "packets" / f"{IDS['plan']}.md").write_text(packet_fixture("packet-lines-1220-improve.txt"), encoding="utf-8")  # old
        run, packets, facts = self.build(out)
        self.assertEqual((self.row(run, "spec").get("improvePacketDoc"), self.row(run, "spec").get("packetImprove")), (True, None))
        self.assertEqual((self.row(run, "plan").get("improvePacketDoc"), self.row(run, "plan").get("packetImprove")), (None, True))
        line = next(l for l in facts if l.startswith("- Packet text carried"))
        self.assertIn("1 visits have a separate Improve packet file; 1 visits (old layout) keep only an Improve child's packet", line)
        self.assertIn("1 of the documents are an Improve child's packet", "\n".join(facts))

    def test_an_improve_file_that_cannot_be_read_keeps_its_size_gets_no_document_and_is_counted(self):
        out = self.new_layout()
        (run_dir_of(out) / "packets" / f"{IDS['spec']}-improve.md").write_bytes(b"\xff\xfe not utf-8 \x80")
        run, packets, facts = self.build(out)
        spec = self.row(run, "spec")
        self.assertEqual((spec["improvePacketBytes"], "improvePacketDoc" in spec, spec["packetDoc"]), (len(b"\xff\xfe not utf-8 \x80"), False, True))
        self.assertNotIn(f"{self.KEY}--{IDS['spec']}-improve", packets)
        self.assertIn("1 packet files unreadable (no document written)", "\n".join(facts))

    def test_an_improve_file_with_no_producer_file_is_not_a_skipped_visit(self):
        out = self.new_layout()
        (run_dir_of(out) / "packets" / f"{IDS['spec']}.md").unlink()
        run, packets, _ = self.build(out)
        spec = self.row(run, "spec")
        self.assertNotIn("skipped", spec)
        self.assertEqual((spec["improvePacketDoc"], "packetDoc" in spec, "carried" in spec), (True, False, False))

    def test_both_documents_are_written_listed_in_order_and_dropped_again_with_their_files(self):
        out = self.new_layout()
        target = self.tmp / "twice"
        with contextlib.redirect_stdout(io.StringIO()):
            export.main([str(out), "--out", str(target)])
        ids = [w["doc_id"] for w in json.loads((target / "writes.json").read_text()) if w["collection"] == "packets"]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(ids.index(f"{self.KEY}--{IDS['spec']}-improve"), ids.index(f"{self.KEY}--{IDS['spec']}") + 1)
        (run_dir_of(out) / "packets" / f"{IDS['spec']}-improve.md").unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            export.main([str(out), "--out", str(target)])
        self.assertFalse((target / "docs" / "packets" / f"{self.KEY}--{IDS['spec']}-improve.json").exists())

    def test_the_committed_export_never_carries_a_packet_text_of_either_file(self):  # a guard: it passes before this change too
        out = self.new_layout()
        target = self.tmp / "bundle"
        with contextlib.redirect_stdout(io.StringIO()):
            export.main([str(out), "--out", str(target)])
        text = (target / "review-export.json").read_text()
        self.assertNotIn("ShipLoop navigator", text)
        self.assertNotIn("Current action: Improve", text)
        bundle = json.loads(text)
        self.assertEqual(sorted(bundle["docs"]), ["backchain", "runs"])
        self.assertEqual(export.check_bundle(bundle)[0], [])

    def test_the_contract_rejects_a_kind_that_is_not_improve_and_shapes_for_the_new_row_fields(self):
        out = self.new_layout()
        run, packets, _ = self.build(out)
        doc = dict(packets[f"{self.KEY}--{IDS['spec']}-improve"], kind="producer")
        self.assertIn("'producer' is not one of improve", "\n".join(export.validate_doc("packets", doc)))
        bad = dict(run, stages=[dict(run["stages"][0], improvePacketBytes="big", improvePacketDoc="yes")])
        problems = "\n".join(export.validate_doc("runs", bad))
        for needle in ("stages[0].improvePacketBytes: expected a number", "stages[0].improvePacketDoc: expected a boolean"):
            self.assertIn(needle, problems)

    def test_schema_md_documents_both_layouts_the_kind_and_the_second_document(self):
        schema = " ".join(SCHEMA_MD.read_text(encoding="utf-8").split())
        for phrase in ("`stages[].improvePacketBytes`", "`improvePacketDoc`", "<action>-improve.md", "new layout", "old layout history",
                       "`<runKey>--<action>-improve`", "| `kind` | `improve` |", "the E2E session's record register of 2026-10-07"):
            self.assertIn(phrase, schema, phrase)

    def test_the_checkouts_own_navigator_writes_the_layout_the_exporter_reads_for_every_reviewed_stage(self):  # old engine: a guard of the old layout; new engine: fails before this change
        """No model: the navigator prints each packet on synthetic results, so this reads what that engine writes. Up to ShipLoop
        1.22.0 a reviewed stage keeps only the Improve child's packet; after it the producer packet stays and the child's file
        sits beside it. Either way the exporter must say so, and no reviewed visit may read as if it had both or neither."""
        out, visits = real_engine_run(self.tmp)
        packets = next((out / ".shiploop-runs").glob("*/run/packets"))
        new = any(packets.glob("*-improve.md"))
        docs, _ = export.build_run(out, key="real")
        run = docs["runs"]["real"]
        reviewed = [v["stage"] for v in visits if v["reviewed"]]
        self.assertTrue({"spec", "test-strategy", "plan"} <= set(reviewed), reviewed)  # planning_review stage, the default
        for visit, row in zip(visits, run["stages"]):
            self.assertEqual(row["stage"], visit["stage"])
            if visit["reviewed"] and new:
                self.assertTrue(row["improvePacketDoc"], visit["stage"])
                self.assertNotIn("packetImprove", row)
                self.assertTrue(all(row["carried"].values()) or visit["stage"] == "intake", (visit["stage"], row.get("carried")))
                self.assertIn(f"real--{visit['action']}-improve", docs["packets"])
            elif visit["reviewed"]:
                self.assertTrue(row["packetImprove"], visit["stage"])  # the old engine's one file is the child's
                self.assertNotIn("improvePacketDoc", row)
            else:
                self.assertEqual({f for f in ("improvePacketDoc", "improvePacketBytes", "packetImprove") if f in row}, set(), visit["stage"])
                self.assertIn("carried", row)
        self.assertEqual(export.validate_doc("runs", run), [])


def new_layout_run() -> dict:
    """CARD_RUN with its spec visit (column 1) in the new layout: the producer packet intact, an Improve child's file beside it."""
    run = json.loads(json.dumps(CARD_RUN))
    spec = run["stages"][1]
    del spec["packetImprove"]
    spec.update({"improvePacketDoc": True, "improvePacketBytes": 52_000, "carried": ALL_CARRIED})
    return run


PRODUCER_TEXT = "\n".join(["Continue in this context.", "Delegation: inline.", "", "ShipLoop navigator | spec | revision 5",
                           "Callback for this stage: run it", "Goal: Define required behavior and acceptance criteria.",
                           "Done when (confirm each):", "- every request outcome maps to a criterion",
                           "Checked by: nothing automatic.", *[f"line {n}" for n in range(1, 30)]]) + "\n"
IMPROVE_TEXT = "ShipLoop navigator | spec | revision 5\nCurrent action: Improve the completed spec result.\n<script>alert(1)</script>\n"
NEW_DOCS = {"packets/cr--nav-a2": {"run": "cr", "action": "nav-a2", "stage": "spec", "bytes": len(PRODUCER_TEXT), "shownBytes": len(PRODUCER_TEXT),
                                   "sha256": "ab" * 32, "text": PRODUCER_TEXT},
            "packets/cr--nav-a2-improve": {"run": "cr", "action": "nav-a2", "stage": "spec", "bytes": len(IMPROVE_TEXT), "shownBytes": len(IMPROVE_TEXT),
                                           "sha256": "cd" * 32, "text": IMPROVE_TEXT, "kind": "improve"}}


class ImprovePacketCardTests(unittest.TestCase):
    """The card for a new-layout visit: the checklist is real, and the Improve child's packet is a second, closed, on-demand box."""

    def probe(self, expression: str, run: dict | None = None, docs: dict | None = None, db: bool = True):
        setup = card_setup(run or new_layout_run(), "PACKET_DOCS=" + json.dumps(NEW_DOCS if docs is None else docs) + ";")
        if not db:
            setup = setup.replace("live=true;", "db=null;live=false;")
        return page_probe(expression, setup=setup)

    def test_the_ids_and_the_card_data_name_the_second_document_and_keep_a_real_checklist(self):
        self.assertEqual(run_logic('[improvePacketId({key:"k"},{improvePacketDoc:true,action:"nav-a"}),improvePacketId({key:"k"},{action:"nav-a"}),'
                                   'improvePacketId({key:"k"},{improvePacketDoc:false,action:"nav-a"}),improvePacketId({},{improvePacketDoc:true,action:"nav-a"})]'),
                         ["k--nav-a-improve", "", "", ""])
        c = card(new_layout_run(), 1)
        self.assertEqual((c["sent"]["improvePacket"], c["sent"]["improveBytes"], c["sent"]["packet"]),
                         ({"id": "cr--nav-a2-improve"}, 52_000, {"id": "cr--nav-a2"}))
        self.assertEqual(c["sent"]["bytesLabel"], "Packet size")  # the size is the producer packet's
        self.assertEqual(c["sent"]["carriedNote"], "")
        self.assertEqual([i["found"] for i in c["sent"]["carried"]], [True] * len(export.CARRIED))
        old = card(CARD_RUN, 1)  # the old layout of the same visit
        self.assertEqual((old["sent"]["improvePacket"], old["sent"]["improveBytes"], old["sent"]["carried"]), (None, None, None))
        self.assertIn("1.22.0 or earlier", old["sent"]["carriedNote"])

    def test_the_card_shows_the_checklist_both_sizes_and_a_second_closed_box_for_the_improve_childs_packet(self):
        out = self.probe('setCol(1);var boxes=byClass("seqdetail","pkt");[boxes.map(function(b){return b.children[0].textContent+":"+b.open;}),'
                         'textOf("seqdetail"),byClass("seqdetail","chip").map(function(c){return c.textContent;}),DB_CALLS.length]')
        boxes, text, chips, calls = out
        self.assertEqual(boxes, ["Packet:false", "Improve child's packet:false"])
        self.assertIn("Packet size45.1 KB", text)
        self.assertIn("Improve child's packet file50.8 KB", text)
        self.assertNotIn("The packet file kept for this visit is the Improve child's", text)
        self.assertEqual([c for c in chips if c.startswith("✗")], [])
        self.assertEqual(sum(1 for c in chips if c.startswith("✓")), len(export.CARRIED))
        self.assertEqual(calls, 0)  # nothing is read until the viewer asks

    def test_opening_the_improve_box_does_one_get_of_its_own_document_and_never_again_and_shows_text_not_markup(self):
        out = self.probe('setCol(1);var boxes=byClass("seqdetail","pkt"),b=boxes[1];b.open=true;b.ontoggle();var once=DB_CALLS.slice();'
                         'b.open=false;b.ontoggle();b.open=true;b.ontoggle();renderAll();var again=byClass("seqdetail","pkt")[1];'
                         '[once,DB_CALLS.length,again.open,byClass(again,"pkt-text")[0].textContent,'
                         'walk(REG.seqdetail,function(e){return e.tagName==="script";}).length,byClass("seqdetail","pkt-head").length]')
        once, calls, kept, text, scripts, heads = out
        self.assertEqual(once, [["get", "packets/cr--nav-a2-improve"]])
        self.assertEqual((calls, kept, scripts, heads), (1, True, 0, 0))  # no head for the Improve packet; the producer's head is its own
        self.assertEqual(text, IMPROVE_TEXT)

    def test_the_producer_packet_and_its_head_load_by_their_own_one_get_independent_of_the_improve_box(self):
        out = self.probe('setCol(1);byClass("seqdetail","btn").filter(function(b){return b.textContent==="Show the packet head";})[0].onclick();'
                         'var a=DB_CALLS.slice();var boxes=byClass("seqdetail","pkt");boxes[0].open=true;boxes[0].ontoggle();boxes[1].open=true;boxes[1].ontoggle();'
                         '[a,DB_CALLS.slice(),byClass("seqdetail","pkt-head")[0].textContent.split("\\n")]')
        self.assertEqual(out[0], [["get", "packets/cr--nav-a2"]])
        self.assertEqual(out[1], [["get", "packets/cr--nav-a2"], ["get", "packets/cr--nav-a2-improve"]])  # the box reused the head's get
        self.assertEqual(out[2][0], "ShipLoop navigator | spec | revision 5")  # (c): the head starts at the navigator line

    def test_a_visit_without_the_second_document_has_one_box_and_without_a_database_none(self):  # a guard: it passes before this change too
        run = new_layout_run()
        del run["stages"][1]["improvePacketDoc"]
        self.assertEqual(self.probe('setCol(1);byClass("seqdetail","pkt").map(function(b){return b.children[0].textContent;})', run=run), ["Packet"])
        self.assertEqual(self.probe('setCol(1);byClass("seqdetail","pkt").length', db=False), 0)
        old = self.probe('setCol(1);[byClass("seqdetail","pkt").map(function(b){return b.children[0].textContent;}),textOf("seqdetail")]', run=CARD_RUN)
        self.assertEqual(old[0], ["Packet"])  # old layout: the one file that exists, the Improve child's, shown as a plain Packet box
        self.assertIn("Packet file kept (the Improve child's)", old[1])

    def test_a_missing_improve_document_reads_not_uploaded_and_a_failed_read_says_so(self):
        out = self.probe('setCol(1);var b=byClass("seqdetail","pkt")[1];b.open=true;b.ontoggle();textOf("seqdetail")', docs={})
        self.assertIn("packet not uploaded for this run", out)
        failed = self.probe('db.doc=function(p){return {get:function(){return sync({code:"unavailable"},true);}};};setCol(1);'
                            'var b=byClass("seqdetail","pkt")[1];b.open=true;b.ontoggle();textOf("seqdetail")')
        self.assertIn("Could not read the packet.", failed)

    def test_the_page_still_has_one_packet_fetch_path(self):  # a guard: it passes before this change too
        page = script_text()
        self.assertEqual(re.findall(r'db\.doc\("packets/"\+id\)\.get\(\)', page), ['db.doc("packets/"+id).get()'])
        self.assertNotIn('collection("packets")', page)


class PacketHeadStartTests(unittest.TestCase):
    """The head starts at the first line beginning 'ShipLoop navigator |', so Goal, Done when, Checked by and the callback show."""

    PREAMBLE = "\n".join(["Continue in this context and execute the prompt.", "", "Delegation: inline. Execute this INNER stage in this conversation,",
                          "including the get-next-work-item stage that opens each work item.", "", "", "ShipLoop navigator | implement | revision 37",
                          "Callback for this stage: python3 shiploop complete", "Goal: Make the planned change.",
                          "Done when (confirm each before calling done):", "- every step is confirmed", "- the lint gate is clean",
                          "Checked by: ShipLoop lints this item's changes.", "Considerations for this stage:", "- Develop: x",
                          "- Test: y", "- Tools: z", "Write the structured result to: /x"]) + "\n"

    def test_the_head_is_twelve_non_empty_lines_from_the_navigator_line_and_the_preamble_is_left_out(self):
        head = run_logic("packetHeadLines(%s,12)" % json.dumps(self.PREAMBLE))
        self.assertEqual(head[0], "ShipLoop navigator | implement | revision 37")
        self.assertEqual(len(head), 12)
        for wanted in ("Goal: Make the planned change.", "Done when (confirm each before calling done):", "Checked by: ShipLoop lints this item's changes."):
            self.assertIn(wanted, head)
        self.assertNotIn("Delegation: inline. Execute this INNER stage in this conversation,", head)
        self.assertEqual(head[-1], "Write the structured result to: /x")  # the twelfth non-empty line from the navigator line

    def test_a_packet_with_no_navigator_line_falls_back_to_its_first_twelve_non_empty_lines_and_a_mention_mid_line_does_not_count(self):
        text = "\n".join(["", "first", "", "see the ShipLoop navigator | line below", *[f"line {n}" for n in range(1, 20)]])
        self.assertEqual(run_logic("packetHeadLines(%s,12)" % json.dumps(text)), ["first", "see the ShipLoop navigator | line below"] + [f"line {n}" for n in range(1, 11)])
        self.assertEqual(run_logic('[packetHeadStart(%s),packetHeadStart(%s),packetHeadStart(""),packetHeadStart(null)]'
                                   % (json.dumps(text), json.dumps(self.PREAMBLE))), [-1, 6, -1, -1])
        self.assertEqual(run_logic('packetHeadLines("ShipLoop navigator | a\\nb",12)'), ["ShipLoop navigator | a", "b"])  # a first line is the start too
        self.assertEqual(run_logic('[packetHeadLines("",12),packetHeadLines(undefined,12)]'), [[], []])

    def test_the_card_says_which_start_it_used(self):
        def probe(text: str) -> str:
            doc = {"run": "cr", "action": "nav-a6", "stage": "implement", "bytes": len(text), "shownBytes": len(text), "sha256": "ab" * 32, "text": text}
            return page_probe('setCol(4);byClass("seqdetail","btn").filter(function(b){return b.textContent==="Show the packet head";})[0].onclick();'
                              'byClass("seqdetail","pkt-headbox")[0].textContent',
                              setup=card_setup(extra="PACKET_DOCS=" + json.dumps({"packets/cr--nav-a6": doc}) + ";"))
        with_line, without = probe(self.PREAMBLE), probe("one\ntwo\nthree\n")
        self.assertIn("from the 'ShipLoop navigator |' line", with_line)
        self.assertIn("with what comes before that line", with_line)
        self.assertNotIn("Delegation: inline.", with_line.split("Packet box below)")[1])
        self.assertNotIn("from the 'ShipLoop navigator |' line", without)
        self.assertIn("the first 3 non-empty lines of the packet", without)


# ---------------------------------------------------------------- R22a: how the run ended, hosts, blocked, left behind

# Excerpts of the real records of a Grok run the harness stopped (ShipLoop 0.58.0), the shapes the exporter reads; the paths
# and ids are synthetic. result.json `termination`, `earlier_terminations`, `left_behind` and `shiploop.worktree_checks`.
TERMINATION_STOPPED = {"process_status": "stopped", "returncode": -9, "sessions": 1, "resumes": 0, "session_stops": ["unknown"],
                       "resume_stop": "stopped by /e2e/r3-battleship-grok-none/stop", "engine_status": "active",
                       "engine_stage": "test-green", "engine_unaccepted_stage": "test-green", "engine_status_reason": None}
EARLIER_TERMINATION = {"process_status": "stopped", "returncode": -9, "sessions": 1, "resumes": 0, "session_stops": ["unknown"],
                       "resume_stop": "terminated by SIGTERM", "engine_status": "active", "engine_stage": "test-author",
                       "engine_unaccepted_stage": "test-author", "engine_status_reason": None}
LEFT_BEHIND = {"observed": True, "survived": [], "reaped": [
    {"pid": 39510, "command": "node", "ports": [64332], "ended_by": "SIGTERM",
     "cwd": "/e2e/r3/.shiploop-runs/work-20261009-062034-d142b0/worktree", "argv": "/opt/homebrew/Cellar/node/25.9.0_2/bin/node server.js"},
    {"pid": 39511, "command": "Google Chrome", "ports": [64335], "ended_by": "SIGTERM", "cwd": "/e2e/r3/work",
     "argv": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --headless=new --remote-debugging-port=64335 about:blank"}]}
INCOMPLETE_ROW = {"stage": "test-green", "outcome": None, "incomplete": True, "seconds": 1626.6, "turns": 104, "tool_calls": 128}


def ended_run(root: Path, *, process_status: str = "stopped", termination: dict | None = None, status: str = "active",
              incomplete: dict | None = INCOMPLETE_ROW, packet: bool = True, **result) -> Path:
    """A run the harness ended: ShipLoop's state still reads `status`, result.json carries the harness's termination record
    (a stopped Grok run's, by default), metrics.json the `incomplete` stage row for the stage never accepted, and the packet
    issued for it (state.md names its action `nav-x`) is on disk."""
    rows = harness_rows(ACCEPTS) + ([incomplete] if incomplete else [])
    out = make_run(root, status=status, loops=False, metrics={"stages": rows})
    if packet:
        (run_dir_of(out) / "packets" / "nav-x.md").write_text("ShipLoop navigator | test-green | revision 9\n" + "x" * 300)
    def write(r: dict) -> None:
        r.update(termination=dict(TERMINATION_STOPPED, process_status=process_status) if termination is None else termination,
                 process={"status": process_status, "returncode": -9})
        for name, value in result.items():  # `shiploop` extends the record that names the run directory
            r[name] = {**r.get(name, {}), **value} if name == "shiploop" else value
    edit_json(out / "result.json", write)
    return out


class RunEndingExportTests(unittest.TestCase):
    """R22a gaps 1 and 2: a run the harness ended reads stopped, not running, and its unaccepted tail is not lost."""

    KEY = RunReviewTest.KEY

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def build(self, out: Path) -> tuple[dict, list[str]]:
        docs, facts = export.build_run(out)
        run = docs["runs"][self.KEY]
        self.assertEqual(export.validate_doc("runs", run), [])
        return run, facts

    def test_an_active_run_whose_host_the_harness_stopped_reads_stopped_with_the_phase_the_header_and_the_cause(self):
        run, facts = self.build(ended_run(self.tmp))
        self.assertEqual(run["status"], "stopped")
        self.assertEqual(run["phases"], ["done", "done", "done", "stopped", "none", "none", "none", "none"])
        self.assertEqual(run["time"], "stopped after 2.3 h, then 27 min of unaccepted work")
        self.assertEqual(run["ending"]["by"], "stopped by the stop file")  # the absolute path is not exported
        self.assertNotIn("/e2e", json.dumps(run))
        self.assertIn("- Ended: stopped: stopped by the stop file; test-green never accepted, 27.1 min after the last accept, "
                      "104 turns; 1 session, 0 resumes", "\n".join(facts))
        self.assertEqual(run["wallMin"], 140.0)  # the accepted work only: the tail is not in it

    def test_the_phase_map_pins_stopped_apart_from_running_and_blocked(self):
        self.assertEqual(export.derive_phases([0, 1, 2], 2, "stopped"), ["done", "done", "stopped"] + ["none"] * 5)
        self.assertEqual(export.derive_phases([0, 1, 2], 2, "active")[2], "running")
        self.assertEqual(export.derive_phases([0, 1, 2], 2, "blocked")[2], "blocked")
        self.assertEqual(export.derive_phases([0, 1, 2], 2, "halted")[2], "blocked")
        self.assertEqual(export.derive_phases(list(range(8)), None, "done"), ["done"] * 8)
        self.assertIn("stopped", export.PHASE_STATES)
        self.assertEqual(export.validate_doc("runs", {"key": "k", "name": "n", "order": 1, "release": "r", "time": "t",
                                                       "imp": "i", "phases": ["stopped"], "status": "stopped"}), [])
        self.assertTrue(export.validate_doc("runs", {"key": "k", "name": "n", "order": 1, "release": "r", "time": "t",
                                                      "imp": "i", "phases": ["halted"]}))

    def test_a_timeout_a_spent_resume_budget_and_a_failed_host_are_stopped_too_and_say_why(self):
        for process_status, resume_stop, said in (
                ("timeout", "host is not resumable", "host timeout; host is not resumable"),
                ("exited", "resume budget spent (3)", "resume budget spent (3)"),
                ("failed", "no host session id to resume", "host failed; no host session id to resume"),
                ("stopped", "terminated by SIGTERM", "terminated by SIGTERM")):
            with self.subTest(process_status=process_status):
                out = ended_run(Path(tempfile.mkdtemp(dir=self.tmp)), process_status=process_status,
                                termination=dict(TERMINATION_STOPPED, process_status=process_status, resume_stop=resume_stop))
                run, _ = self.build(out)
                self.assertEqual((run["status"], run["ending"]["by"]), ("stopped", said))

    def test_only_a_run_whose_engine_reads_active_and_whose_host_the_harness_saw_end_is_stopped(self):
        self.assertEqual(self.build(ended_run(Path(tempfile.mkdtemp(dir=self.tmp))))[0]["status"], "stopped")  # the positive case
        for label, kwargs, expected in (
                ("blocked keeps the engine's status", dict(status="blocked"), "blocked"),
                ("paused keeps the engine's status", dict(status="paused"), "paused"),
                ("a regrade observed no process", dict(process_status="not observed (regraded: no host ran)"), "active")):
            with self.subTest(label):
                run, _ = self.build(ended_run(Path(tempfile.mkdtemp(dir=self.tmp)), **kwargs))
                self.assertEqual(run["status"], expected)
        out = make_run(Path(tempfile.mkdtemp(dir=self.tmp)), loops=False)  # no termination record at all: as before
        run, _ = self.build(out)
        self.assertEqual((run["status"], run["time"]), ("active", "running, 2.3 h at snapshot"))
        self.assertNotIn("ending", run)

    def test_a_stopped_run_with_no_timing_for_its_tail_has_no_unaccepted_minutes_and_says_nothing_of_them(self):
        no_timing = {"stage": "test-green", "outcome": None, "incomplete": True, "timing": "unavailable"}
        run, _ = self.build(ended_run(self.tmp, incomplete=no_timing))
        self.assertNotIn("unacceptedMin", run["ending"])
        self.assertNotIn("unacceptedTurns", run["ending"])
        self.assertEqual(run["ending"]["stage"], "test-green")  # the engine still names the stage
        self.assertEqual(run["time"], "stopped after 2.3 h")  # nothing invented, not "then 0 min"
        none = Path(tempfile.mkdtemp(dir=self.tmp))
        gone = self.build(ended_run(none, incomplete=None))[0]
        self.assertTrue(all(k not in gone["ending"] for k in ("unacceptedMin", "unacceptedTurns")))

    def test_the_packet_issued_for_the_unaccepted_stage_is_named_sized_and_written_as_a_document(self):
        out = ended_run(self.tmp)
        docs, _ = export.build_run(out)
        run = docs["runs"][self.KEY]
        size = (run_dir_of(out) / "packets" / "nav-x.md").stat().st_size
        self.assertGreater(size, 300)
        self.assertEqual((run["ending"]["action"], run["ending"]["packetBytes"], run["ending"]["packetDoc"]), ("nav-x", size, True))
        document = docs["packets"][f"{self.KEY}--nav-x"]
        self.assertEqual((document["stage"], document["bytes"]), ("test-green", size))
        self.assertEqual(export.validate_doc("packets", document), [])
        bare = Path(tempfile.mkdtemp(dir=self.tmp))
        docs, _ = export.build_run(ended_run(bare, packet=False))
        self.assertTrue(all(k not in docs["runs"][self.KEY]["ending"] for k in ("action", "packetBytes", "packetDoc")))
        self.assertNotIn(f"{self.KEY}--nav-x", docs["packets"])

    def test_sessions_resumes_and_earlier_terminations_are_kept_for_a_resumed_run_and_a_clean_run_has_no_ending(self):
        resumed = ended_run(self.tmp, status="done", process_status="exited", incomplete=None, packet=False,
                            termination=dict(TERMINATION_STOPPED, process_status="exited", sessions=2, resumes=1,
                                             resume_stop="ShipLoop run is done", engine_status="done",
                                             engine_unaccepted_stage=None),
                            earlier_terminations=[EARLIER_TERMINATION])
        run, facts = self.build(resumed)
        self.assertEqual(run["status"], "done")
        self.assertEqual(run["ending"], {"sessions": 2, "resumes": 1, "earlier": [{"by": "terminated by SIGTERM", "stage": "test-author"}]})
        self.assertIn("earlier: terminated by SIGTERM at test-author", "\n".join(facts))
        clean = ended_run(Path(tempfile.mkdtemp(dir=self.tmp)), status="done", process_status="exited", incomplete=None, packet=False,
                          termination=dict(TERMINATION_STOPPED, process_status="exited", resume_stop="host is not resumable",
                                           engine_status="done", engine_unaccepted_stage=None))
        self.assertNotIn("ending", self.build(clean)[0])  # guard: one clean session is nothing to report

    def test_the_stop_files_path_is_replaced_by_its_name_and_a_cause_without_one_is_kept_as_written(self):
        self.assertEqual(export._ended_by("stopped by /Users/x/e2e/run-1/stop", "stopped"), "stopped by the stop file")
        self.assertEqual(export._ended_by("run deadline spent", "exited"), "run deadline spent")
        self.assertEqual(export._ended_by("host is not resumable", "timeout"), "host timeout; host is not resumable")
        self.assertIsNone(export._ended_by(None, "exited"))
        self.assertIsNone(export._ended_by("   ", "exited"))


class RunHostsExportTests(unittest.TestCase):
    """R22a gaps 3 and 4: a run two hosts wrote is not one host's measure, and a visit never prints an unmeasured 0 calls."""

    KEY = RunReviewTest.KEY

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def build(self, out: Path) -> tuple[dict, list[str]]:
        docs, facts = export.build_run(out)
        run = docs["runs"][self.KEY]
        self.assertEqual(export.validate_doc("runs", run), [])
        return run, facts

    def two_hosts(self, root: Path) -> Path:
        """A Grok run resumed on Claude: one visit of each host's events has a context row, the Grok visits have calls 0."""
        contexts = {0: {"calls": 0, "peak": 63_417, "peakPct": 6.3}, 1: {"calls": 0, "peak": None, "peakPct": None},
                    5: {"calls": 5, "peak": 71_202, "peakPct": 7.1}, 6: {"calls": 3, "peak": 92_119, "peakPct": 9.2}}
        out = make_run(root, loops=False, metrics={"stages": harness_rows(ACCEPTS, contexts), "model_calls": 182,
                                                   "window_tokens": 1_000_000, "compactions": 1,
                                                   "tokens": {"input_peak": 257_816}})
        write_json(out / "invocation-resume-claude-1791508003.json", {"host": "claude", "model": "claude-sonnet-5-5", "case": "custom"})
        write_json(out / "invocation-resume-codex-1791509021.json", json.loads((out / "invocation.json").read_text()))
        return out

    def test_a_run_resumed_on_another_host_lists_both_and_exports_no_figure_that_mixes_them(self):
        run, facts = self.build(self.two_hosts(self.tmp))
        self.assertEqual(run["hosts"], [{"host": "codex", "model": "gpt-6-luna", "effort": "max"},
                                        {"host": "claude", "model": "claude-sonnet-5-5"}])  # the repeat of the first is one entry
        for field in ("calls", "contextPeak", "contextWindow", "compactions"):
            self.assertNotIn(field, run)
            self.assertIn("2 hosts ran this (codex gpt-6-luna, claude claude-sonnet-5-5)", run["unmeasured"][field])
            self.assertIn("not a measure", run["unmeasured"][field])
        self.assertTrue(all("context" not in row for row in run["stages"]))
        self.assertEqual(run["unmeasured"]["visitContext"], run["unmeasured"]["calls"])
        self.assertEqual(run["host"], "codex")  # the run's own host, model and effort stay those of invocation.json
        text = "\n".join(facts)
        self.assertIn("- Hosts: codex gpt-6-luna max; claude claude-sonnet-5-5 (more than one:", text)
        self.assertIn("calls not measured (2 hosts ran this", text)

    def test_hosts_are_ordered_by_the_resume_time_not_the_file_name_and_a_one_host_run_keeps_its_figures(self):
        out = make_run(self.tmp, loops=False)
        write_json(out / "invocation-resume-grok-1791509021.json", {"host": "grok", "model": "grok-4.7", "effort": "medium"})
        write_json(out / "invocation-resume-claude-1791508003.json", {"host": "claude", "model": "claude-sonnet-5-5"})
        self.assertEqual([h["host"] for h in export._hosts(out)], ["codex", "claude", "grok"])
        single, _ = self.build(make_run(Path(tempfile.mkdtemp(dir=self.tmp)), loops=False))
        self.assertEqual(single["hosts"], [{"host": "codex", "model": "gpt-6-luna", "effort": "max"}])
        self.assertEqual((single["calls"], single["contextPeak"], single["contextWindow"], single["compactions"]), (120, 250_000, 1_000_000, 0))
        resumed_same = make_run(Path(tempfile.mkdtemp(dir=self.tmp)), loops=False)
        write_json(resumed_same / "invocation-resume-codex-1791509021.json", json.loads((resumed_same / "invocation.json").read_text()))
        again, _ = self.build(resumed_same)
        self.assertEqual(len(again["hosts"]), 1)  # a resume on the same host and model is not a second host
        self.assertEqual(again["calls"], 120)

    def test_a_visit_whose_row_counts_no_model_call_has_no_context_and_one_with_calls_keeps_it(self):
        contexts = {0: {"calls": 0, "peak": 63_417, "peakPct": 6.3, "compactions": 0}, 1: {"calls": 0, "peak": None, "peakPct": None},
                    2: {"calls": 7, "peak": 123_219, "peakPct": 12.3}}
        out = make_run(self.tmp, loops=False, metrics={"stages": harness_rows(ACCEPTS, contexts)})
        run, _ = self.build(out)
        self.assertNotIn("context", run["stages"][0])  # a peak beside 0 calls is another host's, not this visit's
        self.assertNotIn("context", run["stages"][1])
        self.assertEqual(run["stages"][2]["context"], {"calls": 7, "peak": 123_219, "peakPct": 12.3})
        self.assertNotIn('"calls": 0', json.dumps(run))
        for row in run["stages"]:
            self.assertNotEqual((row.get("context") or {}).get("calls"), 0)
        self.assertNotIn("visitContext", run["unmeasured"])  # some visits are measured

    def test_the_reason_no_visit_has_a_context_is_per_host_and_names_what_the_harness_reads(self):
        for host, same in (("grok", False), ("claude", True), ("codex", True)):
            with self.subTest(host=host):
                out = make_run(Path(tempfile.mkdtemp(dir=self.tmp)), loops=False, metrics={"stages": harness_rows(ACCEPTS)})
                edit_json(out / "invocation.json", lambda r: r.update(host=host))
                run = next(iter(export.build_run(out)[0]["runs"].values()))  # the key names the host: it moved with it
                self.assertEqual(export.validate_doc("runs", run), [])
                reason = run["unmeasured"]["visitContext"]
                self.assertEqual(reason, export.NO_VISIT_CONTEXT if same else export.NO_VISIT_CONTEXT_GROK)
                self.assertNotIn("only from a Codex run", reason)
        self.assertIn("Grok's events", export.NO_VISIT_CONTEXT_GROK)
        self.assertIn("Claude's per-message usage", export.NO_VISIT_CONTEXT)


class RunBlockedAndLeftBehindExportTests(unittest.TestCase):
    """R22a gaps 5, 6 and 7: a blocked run's own words, the listeners the harness ended, and the unreturned product's checks."""

    KEY = RunReviewTest.KEY
    AWAITING = {"kind": "answer", "no_default": "Recording a passing case would claim an observation that did not happen.",
                "options": ["Accept the HTTP check and leave the browser steps unverified", "Wait until a browser can open the page"],
                "question": "Headless Chrome does not finish loading the page and no browser tool is connected. How should TC-16 proceed?"}

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def build(self, out: Path) -> dict:
        docs, _ = export.build_run(out)
        run = docs["runs"][self.KEY]
        self.assertEqual(export.validate_doc("runs", run), [])
        return run

    def blocked_run(self, root: Path, reason: str = "access: SYS-SERVE passed. TC-16 did not run.", **body) -> Path:
        out = make_run(root, loops=False, status="blocked")
        run_dir = run_dir_of(out)
        action = IDS["implement"]
        set_state(out, status_reason=reason, history=[*export._record(run_dir / "state.md")["history"][:-1],
                                                         {"action": action, "stage": "implement", "outcome": "blocked",
                                                          "summary": "s", "workitem": "W1"}])
        record(run_dir / "results" / f"{action}.md", {"action": action, "stage": "implement", "result": {
            "outcome": "blocked", "summary": "s", "blocked_by": "access", "headline": "TC-16 needs a browser",
            "awaiting": self.AWAITING, **body}})
        return out

    def test_a_blocked_run_exports_its_class_reason_headline_question_options_and_why_no_default(self):
        run = self.build(self.blocked_run(self.tmp))
        self.assertEqual(run["status"], "blocked")
        self.assertEqual(run["blocked"], {
            "by": "access", "reason": "access: SYS-SERVE passed. TC-16 did not run.", "headline": "TC-16 needs a browser",
            "question": self.AWAITING["question"], "options": self.AWAITING["options"], "noDefault": self.AWAITING["no_default"]})

    def test_the_reason_is_cut_at_600_characters_and_a_run_that_is_not_blocked_has_no_blocked_object(self):
        run = self.build(self.blocked_run(self.tmp, reason="r" * 900))
        self.assertEqual(len(run["blocked"]["reason"]), 600)
        self.assertNotIn("blocked", self.build(make_run(Path(tempfile.mkdtemp(dir=self.tmp)), loops=False)))
        self.assertNotIn("blocked", self.build(make_run(Path(tempfile.mkdtemp(dir=self.tmp)), loops=False, status="done")))

    def test_a_blocked_run_whose_last_visit_is_not_the_blocked_result_keeps_only_the_engines_reason(self):
        out = make_run(self.tmp, loops=False, status="blocked")
        set_state(out, status_reason="lint: the gate refused")
        run = self.build(out)
        self.assertEqual(run["blocked"], {"reason": "lint: the gate refused"})  # no question was asked: none is invented

    def test_left_behind_keeps_command_ports_where_and_signal_and_drops_pids_argument_lists_and_paths(self):
        run = self.build(ended_run(self.tmp, left_behind=LEFT_BEHIND))
        self.assertEqual(run["leftBehind"], {"observed": True, "survived": [], "reaped": [
            {"command": "node", "ports": [64332], "where": "worktree", "endedBy": "SIGTERM"},
            {"command": "Google Chrome", "ports": [64335], "where": "work", "endedBy": "SIGTERM"}]})
        text = json.dumps(run)
        for leaked in ("39510", "argv", "opt/homebrew", "remote-debugging", "/e2e/", "cwd"):
            self.assertNotIn(leaked, text)

    def test_a_survivor_has_no_signal_and_a_table_the_harness_could_not_read_stays_unobserved_with_its_reason(self):
        survivor = {"observed": True, "reaped": [], "survived": [{"pid": 7, "command": "/usr/bin/node", "ports": [3000],
                                                                 "cwd": "/somewhere/else", "argv": "node server.js"}]}
        run = self.build(ended_run(self.tmp, left_behind=survivor))
        self.assertEqual(run["leftBehind"]["survived"], [{"command": "node", "ports": [3000], "where": "other"}])
        unread = self.build(ended_run(Path(tempfile.mkdtemp(dir=self.tmp)), left_behind={"observed": False, "reason": "lsof timed out after 5s"}))
        self.assertEqual(unread["leftBehind"], {"observed": False, "reason": "lsof timed out after 5s"})  # never an empty list
        none = self.build(ended_run(Path(tempfile.mkdtemp(dir=self.tmp)), left_behind={"observed": True, "reaped": [], "survived": []}))
        self.assertEqual(none["leftBehind"], {"observed": True, "reaped": [], "survived": []})  # a measured none
        self.assertNotIn("leftBehind", self.build(make_run(Path(tempfile.mkdtemp(dir=self.tmp)), loops=False)))

    def test_where_is_read_from_the_path_components_so_a_copied_run_classifies_the_same(self):
        self.assertEqual([export._where(p) for p in ("/a/.shiploop-runs/work-1/worktree", "/b/worktree/src", "/a/run-out/work",
                                                      "/a/work/sub", "/a/.shiploop-runs/work-1/run", None)],
                         ["worktree", "worktree", "work", "work", "other", "other"])

    def test_the_unreturned_products_checks_are_a_verdict_beside_the_checks_that_ran_where_it_was_not_returned(self):
        shiploop = {"pass": False, "worktree_checks": [{"command": "node --test", "pass": True}, {"command": "curl", "pass": True}]}
        out = ended_run(self.tmp, shiploop=shiploop)
        run = self.build(out)
        self.assertEqual((run["verdicts"]["checks"], run["verdicts"]["worktreeChecks"]), (False, True))
        failing = dict(shiploop, worktree_checks=[{"command": "a", "pass": True}, {"command": "b", "pass": False}])
        self.assertFalse(self.build(ended_run(Path(tempfile.mkdtemp(dir=self.tmp)), shiploop=failing))["verdicts"]["worktreeChecks"])
        self.assertNotIn("worktreeChecks", self.build(make_run(Path(tempfile.mkdtemp(dir=self.tmp)), loops=False))["verdicts"])  # none ran there
        text = "\n".join(export.build_run(ended_run(Path(tempfile.mkdtemp(dir=self.tmp)), shiploop=shiploop))[1])
        self.assertIn("- Checks in the worktree (product not returned): all pass; in the work folder: not all pass", text)

    def test_the_default_run_name_carries_the_case_and_a_given_name_still_wins(self):
        out = make_run(self.tmp, loops=False)
        run = self.build(out)
        self.assertEqual(run["name"], "codex gpt-6-luna max, battleship, release 1.16.1")
        named = export.build_run(out, name="My name")[0]["runs"][self.KEY]["name"]
        self.assertEqual(named, "My name")
        edit_json(out / "invocation.json", lambda r: r.pop("case"))
        edit_json(out / "result.json", lambda r: r.pop("case"))
        bare = next(iter(export.build_run(out)[0]["runs"].values()))
        self.assertEqual(bare["name"], "codex gpt-6-luna max, release 1.16.1")  # no case recorded: none printed
        self.assertEqual(bare["key"], "codex-gpt-6-luna-1.16.1-unknown-20261003")  # the key rule is unchanged


class RunEndingContractTests(unittest.TestCase):
    """R22a: the contract names the new fields, rejects wrong shapes, and no longer states what the E2E runs disproved."""

    def run_doc(self, **fields) -> dict:
        return dict({"key": "k", "name": "n", "order": 1, "release": "r", "phases": ["done"], "time": "t", "imp": "i"}, **fields)

    def test_the_new_fields_validate_and_wrong_shapes_are_named(self):
        good = self.run_doc(status="stopped", hosts=[{"host": "grok", "model": "grok-4.7", "effort": "medium"}],
                            ending={"by": "stopped by the stop file", "stage": "implement", "unacceptedMin": 27.1, "unacceptedTurns": 104,
                                    "packetBytes": 47475, "packetDoc": True, "sessions": 1, "resumes": 0,
                                    "earlier": [{"by": "terminated by SIGTERM", "stage": "test-author"}]},
                            blocked={"by": "access", "options": ["a", "b"]},
                            leftBehind={"observed": True, "reaped": [{"command": "node", "ports": [3000], "where": "work", "endedBy": "SIGTERM"}],
                                        "survived": []},
                            verdicts={"checks": False, "worktreeChecks": True})
        self.assertEqual(export.validate_doc("runs", good), [])
        bad = self.run_doc(status="sleeping", hosts=[{"model": "m"}], ending={"unacceptedMin": "27", "earlier": [{"by": 1}]},
                           blocked={"options": "one"}, leftBehind={"reaped": [{"command": "node", "where": "attic"}]})
        problems = "\n".join(export.validate_doc("runs", bad))
        for needle in ("'sleeping' is not one of", "hosts[0]: missing required field 'host'", "ending.unacceptedMin: expected a number",
                       "ending.earlier[0].by: expected a string", "blocked.options: expected an array",
                       "leftBehind: missing required field 'observed'", "'attic' is not one of"):
            self.assertIn(needle, problems)

    def test_schema_md_documents_the_new_fields_and_states_what_the_runs_showed(self):
        text = " ".join(SCHEMA_MD.read_text().split())
        for phrase in ("`hosts`", "`ending`", "`blocked`", "`leftBehind`", "`worktreeChecks`", "ending.unacceptedMin", "`stopped`",
                       "How the run ended", "not a measure", "refusal lines", "never on a Grok run", "a reason per host",
                       "every producer packet carries a `Checked by:` line"):
            self.assertIn(phrase, text)
        for stale in ("such as Claude's", "Today only a Codex run", "no packet on disk has a 'Checked by:' line yet",
                      "ShipLoop commands that exited non-zero"):
            self.assertNotIn(stale, text)
        self.assertNotIn("no packet on disk has", (SKILL_ROOT / "scripts" / "export.py").read_text())

    def test_a_state_md_fixture_of_each_mode_resolves_the_improve_card_as_the_current_engine_does(self):
        for mode in ("stage", "none"):
            self.assertEqual(real_state(mode)["improve_skill"], "/plugin/skills/improve/SKILL.md", mode)
        self.assertEqual(set(real_state("stage")), set(real_state("none")))


# ---------------------------------------------------------------- R22a: the page shows how a run ended

# Run documents shaped like the exporter's for a stopped Grok run, a blocked one and a run two hosts wrote. Excerpts only.
ROWS_STOPPED = [{"stage": "intake", "outcome": "done", "min": 1.8, "action": "nav-a"},
                {"stage": "spec", "outcome": "done", "min": 3.1, "action": "nav-b"},
                {"stage": "implement", "outcome": "done", "min": 4.8, "action": "nav-c"}]
STOPPED_RUN = {
    "key": "s1", "name": "grok grok-4.7 medium, custom, release 1.26.0", "order": 5, "release": "skill-craft 1.26.0, ShipLoop 0.58.0",
    "phases": ["done", "done", "done", "stopped", "none", "none", "none", "none"], "status": "stopped", "imp": "0 children",
    "time": "stopped after 36 min, then 27 min of unaccepted work", "wallMin": 36.5, "stages": ROWS_STOPPED,
    "ending": {"by": "stopped by the stop file", "stage": "implement", "action": "nav-d", "unacceptedMin": 27.1, "unacceptedTurns": 104,
               "packetBytes": 47_475, "packetDoc": True, "sessions": 1, "resumes": 0,
               "earlier": [{"by": "terminated by SIGTERM", "stage": "test-author"}]},
    "leftBehind": {"observed": True, "survived": [], "reaped": [
        {"command": "node", "ports": [64332], "where": "worktree", "endedBy": "SIGTERM"},
        {"command": "Google Chrome", "ports": [64335], "where": "work", "endedBy": "SIGTERM"}]},
    "verdicts": {"checks": False, "worktreeChecks": True}, "unmeasured": {}}
BLOCKED_RUN = {
    "key": "b1", "name": "grok grok-4.7 medium, custom, release 1.24.0", "order": 4, "release": "skill-craft 1.24.0", "status": "blocked",
    "phases": ["done", "done", "done", "done", "done", "done", "blocked", "none"], "imp": "0 children", "time": "blocked after 90 min",
    "stages": ROWS_STOPPED, "unmeasured": {},
    "blocked": {"by": "access", "reason": "access: SYS-SERVE passed. TC-16 did not run.", "headline": "TC-16 needs a browser",
                "question": "Headless Chrome does not finish loading the page. How should TC-16 proceed?",
                "options": ["Accept the HTTP check and leave the browser steps unverified", "Wait until a browser can open the page"],
                "noDefault": "Recording a pass would claim an observation that did not happen."},
    "verdicts": {"checks": False, "worktreeChecks": False}}
DONE_RUN = {"key": "d1", "name": "claude claude-sonnet-5-5, battleship, release 1.26.0", "order": 3, "release": "skill-craft 1.26.0",
            "status": "done", "phases": ["done"] * 8, "imp": "5 children", "time": "done in 80 min", "stages": ROWS_STOPPED,
            "unmeasured": {}, "verdicts": {"checks": True}}
TWO_HOSTS_RUN = dict(DONE_RUN, key="h1", name="grok grok-4.7 medium, custom, release 1.25.0", hosts=[
    {"host": "grok", "model": "grok-4.7", "effort": "medium"}, {"host": "claude", "model": "claude-sonnet-5-5"}],
    unmeasured={"calls": "2 hosts ran this (grok grok-4.7, claude claude-sonnet-5-5): the harness mixes their events in one "
                         "figure, so it is not a measure",
                "contextPeak": "2 hosts ran this: not a measure", "visitContext": "2 hosts ran this: not a measure"})


def ended_page(run: dict, extra: str = "") -> str:
    """The sample page with one run in place of the first, chosen, drawn, and the eight phases the exporter's table has."""
    phases = "".join('data.exp["phase-%d"]={kind:"phase",order:%d,title:%s,short:"",text:"t"};' % (i, i, json.dumps(title))
                     for i, (title, _) in enumerate(export.PHASES))
    return (SAMPLE_SETUP + phases + "data.runs=[Object.assign(" + json.dumps(run) + ",{order:9})];L.run=" + json.dumps(run["key"]) + ";"
            + extra + "renderAll();")


def ending_rows(run: dict) -> dict:
    model = run_logic("endingModel(%s)" % json.dumps(run))
    return {label: text for label, text in model["rows"]} if model else {}


class EndingCardLogicTests(unittest.TestCase):
    """endingModel is pure: the run in, the rows of the "How it ended" card out, and only what the export holds."""

    def test_a_stopped_run_says_by_what_which_stage_how_long_and_what_came_before(self):
        model = run_logic("endingModel(%s)" % json.dumps(STOPPED_RUN))
        self.assertEqual((model["kind"], model["title"]), ("stopped", "How it ended: stopped by the harness"))
        rows = dict(model["rows"])
        self.assertEqual(rows["Stopped by"], "stopped by the stop file")
        self.assertEqual(rows["Never accepted"], "Implement: 27.1 min and 104 turns of work after the last accept, none of it in a visit "
                                                  "above (the hatched column at the end of the picture)")
        self.assertEqual(rows["Earlier invocation"], "terminated by SIGTERM, Test author left unaccepted")
        self.assertEqual(rows["Listeners the harness ended"],
                         "node :64332 (in the worktree, ended by SIGTERM); Google Chrome :64335 (in the work folder, ended by SIGTERM)")
        self.assertEqual(rows["Product that was never returned"],
                         "passes its checks in the worktree; the copy in the work folder fails them because nothing was returned there")
        self.assertNotIn("Sessions", rows)  # one session, no resume: nothing to say
        self.assertEqual([label for label, _ in model["rows"]][:2], ["Stopped by", "Never accepted"])

    def test_minutes_the_harness_could_not_time_say_so_and_a_stop_without_a_cause_says_that(self):
        run = dict(STOPPED_RUN, ending={"stage": "implement"})
        rows = ending_rows(run)
        self.assertEqual(rows["Stopped by"], "the harness's record names no cause")
        self.assertTrue(rows["Never accepted"].startswith("Implement: work after the last accept (minutes not measured), none of it"))
        self.assertNotIn("0 min", json.dumps(rows))
        self.assertNotRegex(json.dumps(rows), r"undefined|NaN|null")

    def test_a_blocked_run_gives_its_class_reason_question_options_and_why_no_default(self):
        model = run_logic("endingModel(%s)" % json.dumps(BLOCKED_RUN))
        self.assertEqual((model["kind"], model["title"]), ("blocked", "How it ended: blocked"))
        rows = dict(model["rows"])
        self.assertEqual(rows["Blocked by"], "access: TC-16 needs a browser")
        self.assertEqual(rows["Reason"], "access: SYS-SERVE passed. TC-16 did not run.")
        self.assertEqual(rows["Question put to a person"], BLOCKED_RUN["blocked"]["question"])
        self.assertEqual(rows["Options"], "1. Accept the HTTP check and leave the browser steps unverified\n2. Wait until a browser can open the page")
        self.assertEqual(rows["Why no default was taken"], BLOCKED_RUN["blocked"]["noDefault"])
        self.assertEqual(rows["Product that was never returned"], "fails its checks in the worktree too, as the work folder does")

    def test_a_finished_run_shows_the_card_only_for_what_it_resumed_or_left_behind_and_a_plain_one_has_none(self):
        self.assertIsNone(run_logic("endingModel(%s)" % json.dumps(DONE_RUN)))
        self.assertEqual(run_logic("[endingModel(null),endingModel({}),endingModel({status:'done',ending:{}})]"), [None, None, None])
        resumed = dict(DONE_RUN, ending={"sessions": 2, "resumes": 1})
        model = run_logic("endingModel(%s)" % json.dumps(resumed))
        self.assertEqual((model["kind"], model["title"], dict(model["rows"])), (
            "note", "How it ended: done", {"Sessions": "2 sessions, 1 resume in the last invocation"}))
        left = dict(DONE_RUN, leftBehind={"observed": True, "reaped": [{"command": "node", "ports": [3471], "where": "worktree", "endedBy": "SIGTERM"}], "survived": []})
        self.assertEqual(ending_rows(left), {"Listeners the harness ended": "node :3471 (in the worktree, ended by SIGTERM)"})
        self.assertEqual(ending_rows(dict(DONE_RUN, leftBehind={"observed": True, "reaped": [], "survived": []})), {})  # a measured none says nothing
        self.assertEqual(ending_rows(dict(DONE_RUN, leftBehind={"observed": False, "reason": "lsof timed out after 5s"})),
                         {"Listeners": "not observed: lsof timed out after 5s"})
        survivor = dict(DONE_RUN, leftBehind={"observed": True, "reaped": [], "survived": [{"command": "node", "ports": [3000], "where": "other"}]})
        self.assertEqual(ending_rows(survivor), {"Listeners still running": "node :3000 (elsewhere)"})
        passes = dict(DONE_RUN, verdicts={"checks": True, "worktreeChecks": True})
        self.assertEqual(ending_rows(passes), {"Product that was never returned": "checks in the worktree pass"})

    def test_the_host_chip_appears_only_for_a_run_two_hosts_wrote_and_names_the_later_host(self):
        chip = run_logic("hostChip(%s)" % json.dumps(TWO_HOSTS_RUN))
        self.assertEqual(chip["text"], "resumed on claude-sonnet-5-5")
        self.assertIn("2 hosts (grok grok-4.7 medium; claude claude-sonnet-5-5)", chip["title"])
        self.assertIn("are not measured", chip["title"])
        one = {"hosts": [{"host": "claude", "model": "claude-sonnet-5-5"}]}
        self.assertEqual(run_logic("[hostChip(%s),hostChip({}),hostChip(null)]" % json.dumps(one)), [None, None, None])
        self.assertEqual(run_logic("hostChip({hosts:[{host:'a'},{host:'b'},{host:'c',model:'m'}]}).text"), "resumed on b and m")


class EndingCardPageTests(unittest.TestCase):
    """What the page draws on step 1: the card under the header, the chip, the chevron and the figures."""

    def test_the_stopped_run_shows_the_card_the_header_the_hatched_chevron_and_is_not_called_running(self):
        out = page_probe('[textOf("endcard"),REG.endcard.hidden,REG.endcard.className,textOf("runfacts"),'
                         'byClass("flow","st-stopped").map(function(c){return c.textContent;})]',
                         setup=ended_page(STOPPED_RUN))
        self.assertFalse(out[1])
        self.assertEqual(out[2], "card endcard stopped")
        self.assertIn("How it ended: stopped by the harness", out[0])
        self.assertIn("Stopped bystopped by the stop file", out[0])
        self.assertIn("node :64332 (in the worktree, ended by SIGTERM)", out[0])
        self.assertIn("stopped after 36 min, then 27 min of unaccepted work", out[3])
        self.assertNotIn("running", out[3])
        self.assertEqual(out[4], ["Buildstopped by the harness"])  # only the current phase, and no other chevron says stopped

    def test_the_chevrons_keep_blocked_here_and_stopped_by_the_harness_apart(self):
        stopped = page_probe('byClass("flow","chev").map(function(c){return c.textContent;})', setup=ended_page(STOPPED_RUN))
        blocked = page_probe('byClass("flow","chev").map(function(c){return c.textContent;})', setup=ended_page(BLOCKED_RUN))
        self.assertIn("Buildstopped by the harness", "".join(stopped))
        self.assertNotIn("blocked here", "".join(stopped))
        self.assertIn("blocked here", "".join(blocked))
        self.assertNotIn("stopped here", "".join(blocked))  # the old label is gone
        legend = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("red blocked here, hatched amber stopped by the harness", legend)  # the key under the chevrons says it too
        self.assertNotIn("red stopped", legend)
        self.assertNotIn("stopped by the harness", "".join(blocked))

    def test_the_blocked_run_shows_its_question_and_options_on_the_card(self):
        out = page_probe('[textOf("endcard"),REG.endcard.className]', setup=ended_page(BLOCKED_RUN))
        self.assertEqual(out[1], "card endcard blocked")
        for text in ("How it ended: blocked", "Blocked byaccess: TC-16 needs a browser", "Question put to a personHeadless Chrome",
                     "1. Accept the HTTP check", "Why no default was takenRecording a pass"):
            self.assertIn(text, out[0])

    def test_a_plain_finished_run_has_no_card_and_no_chip_and_a_two_host_run_has_the_chip(self):
        plain = page_probe('[REG.endcard.hidden,REG.runhosts.hidden]', setup=ended_page(DONE_RUN))
        self.assertEqual(plain, [True, True])
        two = page_probe('[REG.runhosts.hidden,textOf("runhosts"),REG.runhosts.title,textOf("kpis")]', setup=ended_page(TWO_HOSTS_RUN))
        self.assertFalse(two[0])
        self.assertEqual(two[1], "resumed on claude-sonnet-5-5")
        self.assertIn("2 hosts", two[2])
        self.assertIn("Context (main thread)not measured2 hosts ran this: not a measure", two[3])  # the card gives the exporter's reason
        self.assertNotRegex(two[3], r"undefined|NaN|null")

    def test_a_visit_context_with_zero_calls_is_not_printed_as_a_measurement(self):
        rows = [{"stage": "intake", "outcome": "done", "min": 2, "context": {"calls": 0, "peak": 63417, "peakPct": 6.3}},
                {"stage": "spec", "outcome": "done", "min": 3, "context": {"calls": 4, "peak": 90000, "peakPct": 9}}]
        run = dict(DONE_RUN, stages=rows, contextWindow=1_000_000, contextPeak=90000)
        out = page_probe('setCol(0);var a=textOf("seqdetail");setCol(1);[a,textOf("seqdetail"),REG.seqnote.hidden]', setup=ended_page(run))
        self.assertNotIn("0 calls", out[0])
        self.assertIn("Context (main thread)not measured for this visit", out[0])
        self.assertIn("4 calls", out[1])
        self.assertEqual(run_logic("contextOf([{context:{calls:0,peak:5}}],1000)"), None)
        self.assertEqual(run_logic("contextOf([{context:{calls:2,peak:5}}],1000)")["calls"], 2)

    def test_the_refusals_card_and_the_failures_heading_say_refusal_lines_not_exit_codes(self):
        run = dict(DONE_RUN, refusals=3, failures=[{"verb": "complete", "line": "refused"}, {"verb": "unknown", "line": "refused 2"},
                                                   {"verb": "workspace", "line": "refused 3"}])
        out = page_probe('[textOf("kpis"),textOf("rundetail")]', setup=ended_page(run))
        self.assertIn("Refusals3refusal lines or failed ShipLoop commands", out[0])
        self.assertIn("3 refusals: refusal lines or failed ShipLoop commands", out[1])
        self.assertNotIn("exited non-zero", out[0] + out[1])
        self.assertNotIn("exited non-zero", TEMPLATE.read_text(encoding="utf-8"))


class EndingCardStyleTests(unittest.TestCase):
    """What a render at 375 px showed and a node test cannot: the legend's hidden entries stay hidden (an inline-flex rule
    beat the hidden attribute), and the card's two-column facts grid gives way to one column on a phone."""

    CSS = TEMPLATE.read_text(encoding="utf-8").split("</style>")[0]

    def test_a_hidden_legend_entry_is_not_displayed_by_an_inline_flex_rule(self):
        self.assertRegex(self.CSS, r"\.sqleg span\[hidden\]\s*\{[^}]*display:none")
        self.assertRegex(self.CSS, r"\.sqleg span\{[^}]*display:inline-flex")  # the rule the attribute has to beat

    def test_the_options_of_a_question_are_one_per_line(self):
        self.assertRegex(self.CSS, r"\.endcard \.facts dd\{[^}]*white-space:pre-line")  # the rows join the options with a newline

    def test_the_how_it_ended_facts_are_one_column_on_a_phone(self):
        phone = self.CSS.split("@media (max-width:640px)")[1]
        self.assertRegex(phone, r"\.endcard \.facts[^{]*\{grid-template-columns:1fr\}")

    def test_the_elapsed_card_of_a_stopped_run_says_how_much_more_work_was_never_accepted(self):
        cards = {c["key"]: c for c in run_logic("sequenceModel(%s,{}).cards" % json.dumps(STOPPED_RUN))}
        self.assertEqual(cards["elapsed"]["note"], "start to the last accept; then 27.1 min never accepted")
        plain = {c["key"]: c for c in run_logic("sequenceModel(%s,{}).cards" % json.dumps(DONE_RUN))}
        self.assertNotIn("never accepted", plain["elapsed"]["note"])
        untimed = {c["key"]: c for c in run_logic("sequenceModel(%s,{}).cards" % json.dumps(dict(STOPPED_RUN, ending={"stage": "implement"})))}
        self.assertNotIn("never accepted", untimed["elapsed"]["note"])  # no minutes known: none printed


class TailColumnTests(unittest.TestCase):
    """The unaccepted stage is the picture's last column, outside the visits, the scale and the context band."""

    def model(self, run: dict) -> dict:
        return run_logic("sequenceModel(%s,{})" % json.dumps(run))

    def test_a_stopped_run_gets_a_hatched_last_column_outside_the_visits_and_the_scale(self):
        model = self.model(STOPPED_RUN)
        columns = model["columns"]
        self.assertEqual((len(columns), model["visits"]), (4, 3))  # three visits and the tail
        tail = columns[-1]
        self.assertEqual((tail["kind"], tail["stage"], tail["outcome"], tail["min"], tail["mark"], tail["packetBytes"]),
                         ("tail", "implement", "unaccepted", 27.1, "U", 47_475))
        self.assertEqual(model["maxMin"], {"min": 4.8, "stage": "implement", "visit": 3})  # the tail does not set the scale
        self.assertEqual(max(c["h"] for c in columns[:3]), model["lay"]["plot"])
        self.assertLessEqual(tail["h"], model["lay"]["plot"])
        self.assertEqual(model["lay"]["width"], 8 + 4 * 16 + 8)
        self.assertEqual([c["kind"] for c in columns[:3]], ["work"] * 3)
        self.assertEqual(tail["phases"], [3])  # implement belongs to Build

    def test_a_run_with_no_unaccepted_stage_has_no_tail_and_a_tail_with_no_minutes_is_a_fixed_stub(self):
        self.assertEqual([c["kind"] for c in self.model(DONE_RUN)["columns"]], ["work"] * 3)
        bare = self.model(dict(STOPPED_RUN, ending={"stage": "implement"}))["columns"][-1]
        self.assertEqual((bare["min"], bare["h"]), (None, 26))
        no_stage = self.model(dict(STOPPED_RUN, ending={"by": "stopped by the stop file"}))
        self.assertEqual(len(no_stage["columns"]), 3)

    def test_the_svg_draws_the_tail_with_its_own_pattern_a_u_mark_and_no_context_bar(self):
        run = dict(STOPPED_RUN)
        run["stages"] = [dict(r, context={"calls": 5, "peak": 100, "peakPct": 10}) for r in ROWS_STOPPED]
        svg = run_logic("sequenceSvg(sequenceModel(%s,{}),-1)" % json.dumps(run))
        self.assertEqual(re.findall(r'class="sq-col ([^"]+)"', svg), ["o-done", "o-done", "o-done", "tail"])
        self.assertIn('id="sq-tail"', svg)
        self.assertEqual(svg.count(">U</text>"), 1)
        self.assertEqual(len(re.findall(r'class="sq-ctx[ "]', svg)), 3)  # the three visits have a bar, the tail has none
        self.assertEqual(svg.count('class="sq-hit"'), 4)
        self.assertIn("a hatched last column for the stage the run never accepted", svg)
        self.assertNotRegex(svg, r"NaN|undefined|null|Infinity")

    def test_tapping_the_tail_gives_its_detail_and_never_a_stage_card(self):
        detail = run_logic("columnDetail(sequenceModel(%s,{}),3,%s,[],null)" % (json.dumps(STOPPED_RUN), json.dumps(STOPPED_RUN)))
        self.assertEqual(detail["title"], "Unaccepted: Implement (the run ended here)")
        self.assertIsNone(detail["card"])
        self.assertEqual(dict(detail["lines"]), {
            "Outcome": "never accepted: the run ended while this stage was running",
            "Minutes": "27.1 min after the last accept (not in the elapsed time above)",
            "Turns": "104 turns (main thread)", "Packet file": "46.4 KB, the packet issued for this stage"})
        self.assertEqual((detail["packet"], detail["prev"], detail["next"]), ({"id": "s1--nav-d"}, 2, None))
        names = run_logic("sequenceModel(%s,{}).columns.map(columnName)" % json.dumps(STOPPED_RUN))
        self.assertEqual(names[-1], "unaccepted implement, 27.1 min, the run ended here")

    def test_the_stage_card_list_ends_with_the_unaccepted_stage_and_the_visits_card_counts_it(self):
        rows = run_logic("cardRows(sequenceModel(%s,{}),%s,null)" % (json.dumps(STOPPED_RUN), json.dumps(STOPPED_RUN)))
        last = rows[-1]
        self.assertEqual((last["visit"], last["stage"], last["outcome"], last["min"], last["sent"]),
                         ("end", "Implement", "unaccepted", "27.1 min", "46.4 KB"))
        cards = {c["key"]: c for c in self.model(STOPPED_RUN)["cards"]}
        self.assertEqual(cards["visits"]["note"], "3 work, 1 unaccepted: Implement")
        self.assertEqual(cards["visits"]["value"], "3")

    def test_the_page_draws_the_tail_and_lets_a_tap_select_it_with_its_packet_head(self):
        out = page_probe('setCol(3);[REG.seqscroll.innerHTML.indexOf("sq-col tail")>0,textOf("seqdetail"),byClass("sclist","sc-row").length]',
                         setup=ended_page(STOPPED_RUN))
        self.assertTrue(out[0])
        self.assertIn("Unaccepted: Implement (the run ended here)", out[1])
        self.assertIn("27.1 min after the last accept", out[1])
        self.assertEqual(out[2], 4)

    def test_the_legend_lists_only_the_kinds_the_picture_draws(self):
        legend = lambda run: run_logic("sequenceModel(%s,{}).legend" % json.dumps(run))
        self.assertEqual(legend(STOPPED_RUN), ["done", "tail"])
        self.assertEqual(legend(DONE_RUN), ["done"])
        mixed = {"stages": [{"stage": "intake", "outcome": "done", "min": 1, "improve": {"passes": 2}},
                            {"stage": "spec", "outcome": "revise", "min": 2}, {"stage": "plan", "outcome": "blocked", "min": 3},
                            {"stage": "step-plan", "outcome": "done", "min": None},
                            {"stage": "test-spec", "outcome": "done", "min": None, "seeded": True},
                            {"stage": "baseline", "outcome": "done", "min": 0, "skipped": True}]}
        self.assertEqual(legend(mixed), ["done", "rev", "blk", "skip", "seed", "na", "imp"])
        band = {"stages": [{"stage": "intake", "outcome": "done", "min": 1, "context": {"calls": 3, "peak": 5, "peakPct": 95, "compactions": 2}},
                           {"stage": "spec", "outcome": "done", "min": 1, "context": {"calls": 3, "peak": 5, "peakPct": 20, "compactions": 0}}]}
        self.assertEqual(legend(band), ["done", "ctx", "warn", "tri"])
        calm = {"stages": [{"stage": "intake", "outcome": "done", "min": 1, "context": {"calls": 3, "peak": 5, "peakPct": 20, "compactions": 0}}]}
        self.assertEqual(legend(calm), ["done", "ctx"])  # no compaction measured: no triangle in the legend; none over 90%: no warning
        self.assertEqual(run_logic("sequenceModel({},{}).legend"), [])

    def test_the_page_hides_the_legend_entries_the_picture_does_not_need(self):
        out = page_probe('["done","rev","blk","skip","seed","na","tail","imp","ctx","warn","tri"].filter(function(k){return !REG["sql-"+k].hidden;})',
                         setup=ended_page(STOPPED_RUN))
        self.assertEqual(out, ["done", "tail"])
        self.assertEqual(page_probe('REG.sqlegband.hidden', setup=ended_page(STOPPED_RUN)), True)


if __name__ == "__main__":
    unittest.main()
