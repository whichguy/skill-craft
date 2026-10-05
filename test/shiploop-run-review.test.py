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


def make_run(root: Path, accepts=ACCEPTS, status: str = "active", loops: bool = True) -> Path:
    """A run output directory shaped like test/shiploop_e2e/run.py writes it."""
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
    (run / "improve" / IDS["plan"]).mkdir(parents=True)
    (run / "improve" / f"{IDS['plan']}-bind.md").write_text("bind")  # a file per child: not a second child
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
        "improve_reviews": {"children": 1, "passes": 3, "max_passes": 3,
                            "per_child": [{"child": IDS["plan"], "passes": 3, "seconds": 120.0, "bytes": 900}]}})
    if loops:
        make_plan_loop(run / "scratch" / "backchain-plan")
        make_step_plan_loop(run / "scratch" / "backchain-step-plan")
    return out


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
        self.assertEqual(run["improve"], [{"stage": "plan", "passes": 3, "seconds": 120.0, "bytes": 900}])
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
                                             "packetBytes": 100, "resultBytes": run["stages"][-1]["resultBytes"]})
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
                                                "phases": ["done", "maybe"], "time": "t", "imp": "i", "glue": 0})
        self.assertTrue(any("'refusals'" in p for p in problems), problems)
        self.assertTrue(any("order: expected a number" in p for p in problems), problems)
        self.assertTrue(any("'maybe' is not one of" in p for p in problems), problems)
        self.assertEqual(export.validate_doc("nope", {}), ["unknown collection 'nope'"])
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



def script_text() -> str:
    html = TEMPLATE.read_text(encoding="utf-8")
    blocks = re.findall(r"<script(?![^>]*type=\"application/json\")[^>]*>([\s\S]*?)</script>", html)
    assert len(blocks) == 1, "the template has exactly one script"
    return blocks[0]


class TemplateHasNoDataTests(unittest.TestCase):
    def test_no_embedded_data_or_placeholder(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8")
        self.assertNotIn("__SEED__", html)
        self.assertIsNone(re.search(r"<script[^>]*application/json", html), "no embedded JSON data block")

    def test_content_constants_live_in_data(self) -> None:
        js = script_text()
        for name in ("PHASES", "CRIT", "SEED", "ART_URL", "DEF["):
            self.assertNotIn(name, js, f"{name} is content or data and belongs in the database")

    def test_only_documented_collections_are_read(self) -> None:
        schema = SCHEMA_MD.read_text(encoding="utf-8")
        used = set(re.findall(r"collection\(\"([a-z]+)\"\)", script_text())) | set(re.findall(r"\[\"([a-z]+)\",\"(?:runs|obs|acts|bc|iters|exp|cfg)\"\]", script_text()))
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
            path = Path(tmp) / "page.js"
            path.write_text(script_text(), encoding="utf-8")
            done = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 0, done.stderr)


class DefaultsMatchTheTemplateTests(unittest.TestCase):
    def test_expectation_defaults_have_the_fields_the_template_reads(self) -> None:
        docs = json.loads((DEFAULTS_DIR / "expectations.json").read_text(encoding="utf-8"))
        kinds = {d["kind"] for d in docs}
        self.assertLessEqual(kinds, {"phase", "group", "criterion", "iter"})
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


if __name__ == "__main__":
    unittest.main()
