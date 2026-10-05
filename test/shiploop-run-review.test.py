#!/usr/bin/env python3
"""Run Review: the exporter, its contract and its page template (skills/shiploop-run-review).

The exporter turns a run output directory into documents that follow SCHEMA.md; the template holds no data and
no content and reads only the collections SCHEMA.md documents. Every run here is synthetic, built in a temporary
directory; nothing outside it is read except the skill's own contract files and the selected ShipLoop's stage
table. Which suites a change under the leaf selects is pinned in test/test-groups.test.py.
"""
from __future__ import annotations

import contextlib
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "shiploop-run-review"
TEMPLATE = SKILL_ROOT / "template" / "index.html"
SCHEMA_MD = SKILL_ROOT / "SCHEMA.md"
DEFAULTS_DIR = SKILL_ROOT / "defaults"
SNAPSHOT = ROOT / "test" / "shiploop_e2e" / "evidence" / "run-review-db-snapshot-2026-10-04.json"
LUNA_EVIDENCE = ROOT / "test" / "shiploop_e2e" / "evidence" / "codex-gpt-6-luna-1.16.1-battleship-20261003.json"
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
        self.assertIn("packet and result file sizes", page)
        self.assertNotIn("bytes printed and returned", page)  # packetBytes is a packet file's size, not what the model read
        self.assertIn("minutesText(r.a.min)", page)
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
        self.assertEqual(out[1], "Selected 1 option.")
        other = page_probe('L.run="r2";renderAll();textOf("selcount")', setup=SAMPLE_SETUP,
                           stored=json.dumps({"step": 3, "run": "r1", "sel": {"r1": {"opts": {"a1": True}, "find": {}}}}))
        self.assertEqual(other, "Nothing selected yet. Tick options in step 3.")
        for junk in ("not json", "[1]", json.dumps({"step": 9, "sel": 5}), "null"):
            self.assertEqual(page_probe(STEP_SECTIONS, setup=SAMPLE_SETUP, stored=junk), [True, False, False, False], junk)

    def test_a_tick_is_kept_for_that_run_only_and_the_sticky_bar_counts_it(self) -> None:
        out = page_probe('var boxes=byClass("cards","opt");boxes[0].children[0].checked=true;boxes[0].children[0].onchange();'
                         'var n1=textOf("stickybar");L.run="r2";renderAll();var n2=textOf("stickybar");'
                         'L.run="r1";renderAll();[n1,n2,textOf("stickybar"),REG.stickybar.hidden,textOf("selcount"),JSON.parse(STORED).sel.r1.opts]',
                         setup=SAMPLE_SETUP)
        self.assertEqual(out, ["1 tickedYour plan", "", "1 tickedYour plan", False, "Selected 1 option.", {"a1": True}])

    def test_the_run_detail_reads_the_new_run_fields_defensively(self) -> None:
        bare = page_probe('textOf("rundetail")', setup=SAMPLE_SETUP)
        for line in ("Model calls (main thread)not measured", "Context peak (main thread)not measured",
                     "Compactionsnot measured", "Improve passes: not measured."):
            self.assertIn(line, bare)
        self.assertNotRegex(bare, r"undefined|NaN|null")
        rich = page_probe(
            'Object.assign(data.runs[0],{calls:149,contextPeak:271220,contextWindow:1000000,compactions:0,improvePasses:19,improveMin:3.7,'
            'unmeasured:{}});data.runs[0].stages[0].improve={passes:3,min:1.2};data.runs[0].stages[1].improve={passes:2};'
            'data.runs[0].stages[1].skipped=true;renderAll();textOf("rundetail")', setup=SAMPLE_SETUP)
        for line in ("Model calls (main thread)149", "Context peak (main thread)271,220 tokens of 1,000,000 (27%)",
                     "Compactions0", "19 review passes in 2 visits, 3.7 min, 12% of elapsed.", "intake3 passes1.2 min".replace("intake", "")):
            self.assertIn(line, rich)
        self.assertIn("blocked, skipped, 2 Improve passes", rich)
        self.assertIn("n/a", rich)  # the second visit's Improve minutes were not measured
        reason = page_probe('data.runs[0].unmeasured={improvePasses:"no improve children recorded"};renderAll();textOf("rundetail")',
                            setup=SAMPLE_SETUP)
        self.assertIn("Improve passes: not measured (no improve children recorded).", reason)


class PageShellLogicTests(unittest.TestCase):
    def test_measured_text_adds_the_harness_reason_to_not_measured_and_leaves_numbers_alone(self) -> None:
        self.assertEqual(run_logic('[measuredText({unmeasured:{calls:"no per-call usage"}},"calls"), measuredText({},"calls"),'
                                   ' measuredText({calls:0,unmeasured:{calls:"x"}},"calls"), reasonFor({unmeasured:{a:5}},"a"),'
                                   ' reasonFor(null,"a")]'),
                         ["not measured (no per-call usage)", "not measured", "0", "", ""])

    def test_context_text_is_a_share_of_the_window_only_when_both_were_measured(self) -> None:
        self.assertEqual(run_logic('[contextText({contextPeak:271220,contextWindow:1000000}), contextText({contextPeak:5000}),'
                                   ' contextText({unmeasured:{contextPeak:"Codex rollouts are not read"}}), contextText({})]'),
                         ["271,220 tokens of 1,000,000 (27%)", "5,000 tokens", "not measured (Codex rollouts are not read)",
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
                         'byClass(f,"fig")[0].innerHTML.indexOf("fg-bar")>0,byClass(f,"opt").length,byClass(f,"adv").length,'
                         'byClass(f,"chip").map(function(e){return e.textContent;}),byClass(c[1],"noopt").length]', setup=SAMPLE_SETUP)
        self.assertEqual(out[0], 2)
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
        self.assertEqual(ticked, [{"o2": True}, "Selected 1 finding to investigate.", "3. Findings and options2 open, 1 ticked"])

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
        self.assertEqual(sorted(cfg["prompt"]), ["closing", "concatPreamble", "constraints"])
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


if __name__ == "__main__":
    unittest.main()
