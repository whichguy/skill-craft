#!/usr/bin/env python3
"""Hermetic tests of the ShipLoop adapter's step machinery (test/shiploop_e2e/adapter/facade.py `step`, `cleanup`). No model is called.

Plan: docs/closed-loop-phase2-plan-2026-11-15.md (version 3), gate G1. A throwaway source repository holds a copy of the live harness
with two stand-ins: `iterate.py` is test/fixtures/closed-loop-adapter/fake_iterate.py (the loop's observable contract, with knobs) and
`scorecard.py` also scores a run folder from its card.json. The facade's `setup` clones it, and every test drives the facade as
closed_loop.py would: a subprocess, with CLOSED_LOOP_WORKSPACE set, whose `step start` returns at once and whose worker runs detached.
Every iteration a test receives is also checked by the orchestrator's own `validate_facts`.

Run: python3 -B test/shiploop-e2e-adapter-steps.test.py
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "test" / "shiploop_e2e"
FACADE = HARNESS / "adapter" / "facade.py"
FIXTURE = ROOT / "test" / "fixtures" / "closed-loop-adapter" / "fake_iterate.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


queries = load("adapter_queries_test", ROOT / "test" / "shiploop-e2e-adapter.test.py")  # the source builder and its helpers
facade = queries.facade
closed_loop = load("closed_loop_script", ROOT / "skills" / "closed-loop" / "scripts" / "closed_loop.py")
git, commit_all = queries.git, queries.commit_all

# The real scorecard with one addition: a run folder that holds card.json scores as that card.
SCORE_OVERRIDE = '''

# --- test override: the facade's tests build their run folders from a fake engine, which leaves card.json
_real_score = score


def score(run, *, required_case=_CURRENT_CASE):
    import json as _json
    from pathlib import Path as _Path
    card = _Path(run) / "card.json"
    return _json.loads(card.read_text()) if card.is_file() else _real_score(run, required_case=required_case)
'''

STATE: dict = {}


RIGGED_RULE = "    return path.startswith(CANDIDATE_PREFIXES) and not path.startswith(HARNESS_PREFIXES)\n"


def build_engine_source(folder: Path, rigged: bool = False, clean: bool = False):
    """The stand-in source: the stand-in engine and scorecard, a quick tier that exits as $FAKE_TIER_EXIT says, and a build script that
    only makes its folder. `rigged` also makes the harness's boundary rule accept every path (the negative control of the planted-edit check)."""
    src, _ = queries.build_source(folder)
    harness = src / "test" / "shiploop_e2e"
    shutil.copy2(FIXTURE, harness / "iterate.py")
    (harness / "scorecard.py").write_text((harness / "scorecard.py").read_text() + SCORE_OVERRIDE)
    (src / "test" / "run-all.sh").write_text("#!/bin/sh\nexit ${FAKE_TIER_EXIT:-0}\n")
    (src / "scripts").mkdir()
    (src / "scripts" / "build-packages.py").write_text("import pathlib, sys\npathlib.Path(sys.argv[1]).mkdir(parents=True, exist_ok=True)\n")
    if clean:  # no learning record at all: nothing keeps a scope from converging but the evidence
        (src / facade.LEDGER_REL).write_text("")
    if rigged:
        text = (harness / "boundary.py").read_text()
        if RIGGED_RULE not in text:
            raise AssertionError("boundary.candidate_path changed: update the rigged copy in this test")
        (harness / "boundary.py").write_text(text.replace(RIGGED_RULE, "    return True\n", 1))
    return src, commit_all(src, "engine stand-ins")


def source_for(variant: str):
    """(source repository, base commit) of a variant, built once per run."""
    if variant not in STATE["variants"]:
        folder = STATE["folder"] / f"source-{variant}"
        folder.mkdir()
        STATE["variants"][variant] = build_engine_source(folder, rigged=(variant == "rigged"), clean=(variant == "clean"))
    return STATE["variants"][variant]


def setUpModule():
    STATE["folder"] = Path(tempfile.mkdtemp(prefix="shiploop-adapter-steps-")).resolve()
    STATE["variants"] = {}
    source_for("plain")


def tearDownModule():
    shutil.rmtree(STATE["folder"], ignore_errors=True)


LEADER_SCRIPT = """import subprocess, sys, time
subprocess.Popen([sys.executable] + sys.argv[1:])
time.sleep(0.5)
"""
MEMBER_SCRIPT = """import subprocess, sys, time
if sys.argv[1:] == ["tree"]:
    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
time.sleep(60)
"""


def orphaned_group(test, tree=False):
    """What a worker killed alone leaves behind: a process group whose leader has exited while its member lives on, and with `tree` a child
    of the member in a session of its own (a model session). Returns (the leader's pid, the member's row, the child's row or None)."""
    folder = Path(tempfile.mkdtemp(prefix="orphan-", dir=STATE["folder"]))
    (folder / "leader.py").write_text(LEADER_SCRIPT)
    (folder / "member.py").write_text(MEMBER_SCRIPT)
    starter = ("import subprocess,sys;p=subprocess.Popen([sys.executable]+sys.argv[1:],start_new_session=True,"
               "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);print(p.pid)")
    args = [str(folder / "leader.py"), str(folder / "member.py"), *(["tree"] if tree else [])]
    leader = int(subprocess.run([sys.executable, "-c", starter, *args], capture_output=True, text=True, check=True).stdout.strip())

    def ready():
        table = facade.ps_rows()
        members = facade.alive_in_group(table, leader)
        if leader in table or not members:
            return None
        below = [row for row in facade.descendants(table, members[0]["pid"]) if row["pgid"] != leader]
        if tree and not below:
            return None
        return members[0], (below[0] if below else None)
    member, child = wait_for(ready, 15)

    def end():
        for row in (member, child):
            if row:
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.kill(row["pid"], signal.SIGKILL)
    test.addCleanup(end)
    return leader, member, child


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True, check=False).stdout.strip()
    return bool(state) and not state.startswith("Z")  # a zombie is already dead


def wait_for(predicate, timeout=60.0, pause=0.2):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = predicate()
        if value:
            return value
        time.sleep(pause)
    raise AssertionError("timed out waiting for " + getattr(predicate, "__name__", "a condition"))


class StepCase(unittest.TestCase):
    """One evaluator clone, one work folder and one knob file per test; whatever a test leaves running is ended afterwards."""

    variant = "plain"

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="adapter-step-", dir=STATE["folder"])).resolve()
        self.x = self.folder / "x"
        self.work = self.folder / "work"
        src, self.base = source_for(self.variant)
        queries.run_facade("setup", "--workspace", str(self.x), "--base", self.base, "--source", str(src))
        self.layout = facade.Layout(self.x)
        self.knobs = self.folder / "knobs.json"
        self.log = self.folder / "engine.log"
        self.set_knobs({})
        self.addCleanup(self.stop_everything)

    # ---- helpers

    def set_knobs(self, knobs):
        self.knobs.write_text(json.dumps(knobs))

    def run_cli(self, *args, check=True, env=None):
        environment = {"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp"), "PYTHONDONTWRITEBYTECODE": "1",
                       "CLOSED_LOOP_WORKSPACE": str(self.x), "FAKE_ENGINE": str(self.knobs), "FAKE_LOG": str(self.log), **(env or {})}
        done = subprocess.run([sys.executable, "-B", str(FACADE), *args], capture_output=True, text=True, env=environment, check=False)
        if check:
            self.assertEqual(done.returncode, 0, f"facade {' '.join(args)} exited {done.returncode}: {done.stderr}")
            return json.loads(done.stdout)
        return done

    def build(self):
        return self.run_cli("identity")["build"]

    def intent_only(self, key="s1"):
        """The state a `step start` leaves when it wrote its intent and died before launching anything."""
        original = facade.spawn_worker
        facade.spawn_worker = lambda layout, rec: None
        try:
            os.environ["CLOSED_LOOP_WORKSPACE"] = str(self.x)
            facade.step_start(self.layout, self.start_args(key))
        finally:
            facade.spawn_worker = original

    def start_args(self, key, base=None):
        return type("Args", (), {"key": key, "scope": "s1", "cases": "hello", "mode": "iterate", "base": base or self.build(),
                                 "out": str(self.work / "runs" / key), "host": "codex", "model": "m", "effort": "high", "calibration": None,
                                 "tolerance": 0.25, "attempts": 1, "parallel": 1, "engine_arg": None})

    def prepared_step(self):
        """A finished step whose worker is gone and whose tip has not moved yet: (its key, the commit it moves the tip to)."""
        publication = PublicationTests("test_prepared_and_the_tip_still_at_the_start_is_moved_by_the_next_poll")
        publication.x, publication.layout, publication.work, publication.base, publication.build = self.x, self.layout, self.work, self.base, self.build
        result = publication.commit_on_top(self.base)
        publication.prepared(tip_to=result)
        return "p1", result

    def probe(self, claim, *flags, env=None):
        return self.run_cli("probe", "--host", "codex", "--model", "fake-model", "--effort", "high", *flags, claim, env=env)

    def start(self, key, cases, mode="iterate", env=None, check=True, base=None):
        return self.run_cli("step", "--host", "codex", "--model", "fake-model", "--effort", "high", "--tolerance", "0.25", "--attempts", "1",
                            "--parallel", "1", "start", "--key", key, "--scope", "s1", "--cases", ",".join(cases), "--mode", mode,
                            "--base", base or self.build(), "--out", str(self.work / "runs" / key), env=env, check=check)

    def poll(self, key):
        return self.run_cli("step", "poll", "--handle", key)

    def finish(self, key, timeout=180.0):
        def done():
            reply = self.poll(key)
            return reply if reply["status"] != "running" else None
        return wait_for(done, timeout, 0.4)

    def record(self, key):
        return json.loads((self.layout.steps / f"{key}.json").read_text())

    def tip(self):
        return git(self.x, "rev-parse", "--verify", "-q", facade.TIP_REF, check=False) or self.base

    def valid(self, reply, cases):
        self.assertEqual(reply["status"], "done", reply)
        self.assertEqual(closed_loop.validate_facts(reply["iteration"], cases), [], reply["iteration"])
        return reply["iteration"]

    def worktrees(self):
        return [line for line in git(self.x, "worktree", "list", "--porcelain").splitlines() if line.startswith("worktree ")][1:]

    def stop_everything(self):
        keys = [path.stem for path in sorted(self.layout.steps.glob("*.json"))] if self.layout.steps.is_dir() else []
        if keys:
            self.run_cli("cleanup", "--keys", ",".join(keys), check=False)

    def engine_calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.is_file() else []

    def x_clean(self):
        self.assertEqual(git(self.x, "status", "--porcelain"), "", "the evaluator clone must stay clean")


class QuietStepTests(StepCase):
    def test_a_quiet_exploration_derives_every_fact(self):
        self.start("s1", ["hello"])
        reply = self.finish("s1")
        it = self.valid(reply, ["hello"])
        self.assertEqual(it["cases"], {"hello": {"ran": True, "floors_met": True, "baseline": "none"}})
        self.assertEqual((it["review"], it["judge"]), ({"valid": True, "complete": True}, {"valid": True, "complete": True}))
        self.assertEqual((it["discoveries"], it["candidate"], it["acceptance"], it["invalid"]), ([], None, None, []))
        self.assertEqual(it["build_after"], it["build_before"])
        self.assertEqual(it["build_before"], self.build())
        self.assertTrue(it["cleanup"]["verified"], it["cleanup"])
        self.assertIn("1 run folder", it["cleanup"]["receipt"])
        self.assertFalse(it["tier"]["green"], "no quick-tier receipt exists for the base build yet")
        self.assertEqual(it["tier"]["build"], it["build_after"])
        self.assertEqual(it["consumed"]["runs"], 1)
        self.assertEqual(it["scoring"], self.run_cli("identity")["scoring"])
        # the new tip carries the loop's learning commit, on top of the base, and nothing else
        self.assertNotEqual(self.tip(), self.base)
        self.assertEqual(git(self.x, "rev-list", "--count", f"{self.base}..{self.tip()}"), "1")
        self.assertEqual(self.worktrees(), [])
        self.x_clean()

    def test_baseline_rows_are_captured_and_the_next_step_compares_with_them(self):
        self.start("s1", ["hello"])
        first = self.valid(self.finish("s1"), ["hello"])
        self.assertEqual(first["cases"]["hello"]["baseline"], "none", "a run is never compared with its own row")
        history = facade.lines_of(self.layout.baselines_file.read_text())
        self.assertEqual(len(history), 1)
        self.assertEqual(facade.lines_of((self.work / "runs" / "s1" / "baselines-captured.jsonl").read_text()), history)
        self.assertEqual(git(self.x, "show", f"HEAD:{facade.BASELINES_REL}"), "", "X's own baseline file is restored")
        self.start("s2", ["hello"])
        second = self.valid(self.finish("s2"), ["hello"])
        self.assertEqual(second["cases"]["hello"]["baseline"], "comparable")
        self.assertEqual(len(facade.lines_of(self.layout.baselines_file.read_text())), 2)

    def test_discoveries_are_new_then_repeats(self):
        self.set_knobs({"*": {"kind": "discover", "record": "LR-20261115-aaaaaa"}})
        self.start("s1", ["hello"])
        first = self.valid(self.finish("s1"), ["hello"])
        self.assertEqual(first["discoveries"], [{"id": "LR-20261115-aaaaaa", "material": True, "repeat": False}])
        self.start("s2", ["hello"])
        second = self.valid(self.finish("s2"), ["hello"])
        self.assertEqual(second["discoveries"], [{"id": "LR-20261115-aaaaaa", "material": True, "repeat": True}])

    def test_a_finding_about_the_evaluator_is_an_adapter_record_and_not_a_discovery(self):
        self.set_knobs({"*": {"kind": "discover", "record": "LR-20261115-bbbbbb", "target": "harness"}})
        self.start("s1", ["hello"])
        it = self.valid(self.finish("s1"), ["hello"])
        self.assertEqual(it["discoveries"], [], "a harness finding never blocks a subject iteration, or a repeat of it would keep the window from ever closing")
        by_id = {item["id"]: item for item in self.run_cli("records")["records"]}
        self.assertEqual(by_id["LR-20261115-bbbbbb"]["target"], "adapter", "it is still in the ledger, and in the report as an adapter record")

    def test_a_file_the_engine_leaves_in_the_clone_is_reported_and_removed(self):
        self.set_knobs({"*": {"stray": True}})
        self.start("s1", ["hello"])
        it = self.valid(self.finish("s1"), ["hello"])
        self.assertTrue(any("stray.txt" in text for text in it["invalid"]), it["invalid"])
        self.x_clean()

    def test_an_invalid_review_is_reported_and_the_iteration_cannot_be_quiet(self):
        self.set_knobs({"*": {"review_invalid": True}})
        self.start("s1", ["hello"])
        it = self.valid(self.finish("s1"), ["hello"])
        self.assertEqual(it["review"], {"valid": False, "complete": True})
        self.assertEqual(it["judge"], {"valid": False, "complete": False}, "the loop ends the exploration before the judge")
        self.assertTrue(any("INVALID_REVIEW on hello" in text for text in it["invalid"]), it["invalid"])
        reasons = closed_loop.quiet_reasons(it, it["invalid"])
        self.assertIn("the review was not valid and complete", reasons)
        self.assertIn("invalid or incomplete evidence was recorded", reasons)

    def test_a_run_the_harness_cannot_attribute_to_the_build_is_invalid_evidence(self):
        self.set_knobs({"*": {"attribution": False}})
        self.start("s1", ["hello"])
        it = self.valid(self.finish("s1"), ["hello"])
        self.assertTrue(any("could not attribute" in text and "the build under test was not what ran" in text for text in it["invalid"]), it["invalid"])
        self.assertTrue(it["cases"]["hello"]["floors_met"], "the strict outcome does not look at attribution: the invalid entry is what stops a quiet verdict")
        self.assertIn("invalid or incomplete evidence was recorded", closed_loop.quiet_reasons(it, it["invalid"]))

    def test_a_loop_that_stops_for_another_reason_is_invalid_evidence(self):
        self.set_knobs({"*": {"stop": "the evaluator changed: start a new loop"}})
        self.start("s1", ["hello"])
        it = self.valid(self.finish("s1"), ["hello"])
        self.assertTrue(any("stopped for another reason" in text and "the evaluator changed" in text for text in it["invalid"]), it["invalid"])

    def test_a_process_left_behind_by_a_host_is_stopped_and_named_in_the_receipt(self):
        self.set_knobs({"*": {"escape": "ledger"}})
        self.start("s1", ["hello"])
        it = self.valid(self.finish("s1"), ["hello"])
        self.assertTrue(it["cleanup"]["verified"], it["cleanup"])
        self.assertIn("1 group(s) stopped", it["cleanup"]["receipt"])
        folder = self.work / "runs" / "s1" / "inv-1" / "explore-1" / "run"
        rows = [json.loads(line) for line in (folder / "resources.jsonl").read_text().splitlines()]
        pid = next(row["pgid"] for row in rows if row["kind"] == "group")
        self.assertFalse(alive(pid), "the recorded group is gone")

    def test_the_orchestrator_accepts_the_reply_of_each_verb(self):
        reply = self.start("s1", ["hello"])
        self.assertEqual(set(reply), {"handle", "status"})
        self.assertEqual(reply["handle"], "s1")
        done = self.finish("s1")
        self.assertEqual(set(done), {"status", "iteration"})
        cleanup = self.run_cli("cleanup", "--keys", "s1")
        self.assertTrue(cleanup["verified"])
        self.assertTrue(cleanup["receipt"].strip())


class CycleStepTests(StepCase):
    """`csv-report` has an admitted, material record in the base ledger, so the loop starts a cycle for it, with `hello` (another style)
    as the confirmation case the facade chooses."""

    def test_a_promotion_moves_the_build_the_tip_and_the_records(self):
        self.set_knobs({"csv-report": {"decision": "PROMOTE"}})
        self.start("s1", ["csv-report", "hello"])
        it = self.valid(self.finish("s1"), ["csv-report", "hello"])
        self.assertEqual(it["candidate"]["outcome"], "PROMOTE")
        record = self.record("s1")
        learnings = record["invocations"][0]
        candidate = git(self.x, "rev-parse", f"{learnings['tip_after']}^")
        self.assertEqual(it["candidate"]["hash"], candidate)
        self.assertEqual(it["candidate"]["id"], "LR-20261101-000001")
        self.assertNotEqual(it["build_after"], it["build_before"])
        self.assertEqual(self.run_cli("identity")["build"], it["build_after"], "the published tip carries the promoted build")
        self.assertEqual(self.tip(), learnings["tip_after"])
        self.assertTrue(it["tier"]["green"], "the quick tier ran in the loop worktree and its receipt is kept for the build")
        self.assertEqual(it["tier"]["build"], it["build_after"])
        self.assertIn("a confirmation case of another style (hello) took part", it["acceptance"]["evidence"])
        self.assertEqual(it["acceptance"]["candidate"], candidate)
        self.assertEqual(it["cases"]["csv-report"], {"ran": True, "floors_met": True, "baseline": "none"})
        self.assertEqual(it["cases"]["hello"], {"ran": False, "floors_met": False, "baseline": "none"}, "a cycle ends the step")
        by_id = {item["id"]: item for item in self.run_cli("records")["records"]}
        self.assertEqual(by_id["LR-20261101-000001"]["status"], "verified")
        self.assertEqual(by_id["LR-20261101-000001"]["evidence"], "the epoch promoted it")

    def test_a_failing_tier_is_reported_not_hidden(self):
        self.set_knobs({"csv-report": {"decision": "PROMOTE"}})
        self.start("s1", ["csv-report"], env={"FAKE_TIER_EXIT": "1"})
        it = self.valid(self.finish("s1"), ["csv-report"])
        self.assertFalse(it["tier"]["green"])
        self.assertEqual(it["tier"]["build"], it["build_after"])

    def test_a_dropped_candidate_keeps_the_build_and_names_the_kept_ref(self):
        facade.write_json(self.layout.tier_file(self.build()), {"green": True, "build": self.build(), "at": "2026-11-15T00:00:00Z"})
        self.set_knobs({"csv-report": {"decision": "DROP"}})
        self.start("s1", ["csv-report", "hello"])
        it = self.valid(self.finish("s1"), ["csv-report", "hello"])
        self.assertEqual(it["candidate"]["outcome"], "DROP")
        refs = git(self.x, "for-each-ref", "--format=%(objectname)", "refs/shiploop-loop/")
        self.assertEqual(it["candidate"]["hash"], refs)
        self.assertEqual(it["build_after"], it["build_before"])
        self.assertTrue(it["tier"]["green"], "an unchanged build carries the last green receipt kept for it")
        self.assertEqual(it["acceptance"], None)
        self.assertNotEqual(self.tip(), self.base, "the learning commit is published although the build did not move")
        by_id = {item["id"]: item for item in self.run_cli("records")["records"]}
        self.assertEqual(by_id["LR-20261101-000001"]["status"], "refuted")

    def test_the_cycles_arms_are_compared_with_the_baselines_of_both_destinations(self):
        self.set_knobs({"csv-report": {"decision": "DROP"}})
        self.start("s1", ["csv-report", "hello"])
        self.valid(self.finish("s1"), ["csv-report", "hello"])
        history = facade.lines_of(self.layout.baselines_file.read_text())
        self.assertEqual(len(history), 4, "two arms times two cases, from the epoch's own file")
        self.set_knobs({})
        self.start("s2", ["hello"])
        it = self.valid(self.finish("s2"), ["hello"])
        self.assertEqual(it["cases"]["hello"]["baseline"], "comparable", "an epoch's rows are a basis for a later exploration")

    def test_an_unreadable_cycle_outcome_is_not_a_candidate_and_is_not_clean(self):
        self.set_knobs({"csv-report": {"decision": "UNKNOWN_LAUNCH"}})
        self.start("s1", ["csv-report"])
        it = self.valid(self.finish("s1"), ["csv-report"])
        self.assertIsNone(it["candidate"])
        self.assertFalse(it["cleanup"]["verified"])
        self.assertTrue(any("UNKNOWN_LAUNCH" in text for text in it["invalid"]), it["invalid"])

    def test_a_sweep_does_not_run_a_case_whose_record_is_offered(self):
        self.start("s1", ["csv-report", "hello"], mode="sweep")
        it = self.valid(self.finish("s1"), ["csv-report", "hello"])
        self.assertEqual(it["cases"]["csv-report"], {"ran": False, "floors_met": False, "baseline": "none"})
        self.assertTrue(it["cases"]["hello"]["ran"])
        self.assertEqual([call["argv"][call["argv"].index("--case") + 1] for call in self.engine_calls()], ["hello"])
        self.assertIsNone(it["candidate"])

    def test_the_generality_case_is_the_first_other_style_case_outside_the_records_sources(self):
        self.start("s1", ["csv-report", "hello"])
        self.finish("s1")
        first = self.engine_calls()[0]["argv"]
        self.assertEqual(first[first.index("--case") + 1], "csv-report")
        self.assertEqual(first[first.index("--generality-case") + 1], "hello")
        self.log.unlink()
        self.set_knobs({})
        self.start("s2", ["hello"])
        self.finish("s2")
        alone = self.engine_calls()[0]["argv"]
        self.assertNotIn("--generality-case", alone, "a scope of one style makes a single-style claim")

    def test_the_second_step_continues_from_the_tip_the_first_published(self):
        self.set_knobs({"csv-report": {"decision": "PROMOTE"}})
        self.start("s1", ["csv-report"])
        first = self.valid(self.finish("s1"), ["csv-report"])
        stale = self.start("s2", ["hello"], base=first["build_before"], check=False)
        self.assertEqual(stale.returncode, 2)
        self.assertIn("the published build is", stale.stderr)
        self.set_knobs({})
        self.start("s2", ["hello"])
        second = self.valid(self.finish("s2"), ["hello"])
        self.assertEqual(second["build_before"], first["build_after"])
        self.assertEqual(subprocess.run(["git", "-C", str(self.x), "merge-base", "--is-ancestor", self.record("s1")["prepared"]["tip_to"], self.tip()],
                                        check=False).returncode, 0, "the first step's published tip is in the second step's history")
        self.assertEqual(subprocess.run(["git", "-C", str(self.x), "merge-base", "--is-ancestor", first["candidate"]["hash"], self.tip()],
                                        check=False).returncode, 0, "the promoted candidate is in the second step's history")

    def test_records_are_read_at_the_published_tip_not_at_the_checkout(self):
        self.set_knobs({"csv-report": {"decision": "PROMOTE"}})
        self.start("s1", ["csv-report"])
        self.valid(self.finish("s1"), ["csv-report"])
        checked_out = git(self.x, "show", f"HEAD:{facade.LEDGER_REL}")
        self.assertIn('"event": "admitted"', checked_out)
        self.assertNotIn('"outcome": "verified", "reason": "the epoch promoted it"', checked_out, "X's checkout is at an older position")
        by_id = {item["id"]: item for item in self.run_cli("records")["records"]}
        self.assertEqual(by_id["LR-20261101-000001"]["status"], "verified")


class ProcessTests(StepCase):
    def hung(self, key, knob=None):
        """A step whose engine has staged a ledger row and waits; returns its worker and engine pids once the row is staged."""
        self.set_knobs({"*": {"fault": "hang", **(knob or {})}})
        self.start(key, ["hello"])

        def staged():  # the content, not the file name: while `git worktree add` runs, its index is empty and every file looks staged
            trees = self.worktrees()
            if not trees:
                return None
            path = Path(trees[0].split(" ", 1)[1])
            return path if "LR-20261115-feed01" in git(path, "diff", "--cached", "--", facade.LEDGER_REL, check=False) else None
        tree = wait_for(staged, 90)
        record = self.record(key)
        return record["worker"]["pid"], record["invocations"][0]["engine_pid"], tree

    def test_cancel_ends_the_group_and_archives_a_staged_ledger_row(self):
        worker, engine, tree = self.hung("s1")
        self.assertTrue(alive(worker) and alive(engine))
        reply = self.run_cli("step", "cancel", "--handle", "s1")
        self.assertEqual(reply["status"], "cancelled")
        self.assertFalse(alive(worker) or alive(engine))
        record = self.record("s1")
        self.assertEqual(record["state"], "cancelled")
        archive = Path(record["archives"][0]["path"])
        self.assertIn("LR-20261115-feed01", (archive / "learning-records.jsonl").read_text())
        self.assertIn("LR-20261115-feed01", (archive / "staged.diff").read_text(), "the staged row is archived although the file was never committed")
        self.assertEqual(record["archives"][0]["ledger_rows"], 1)
        self.assertIn("1 ledger row(s)", record["error"])
        self.assertEqual(self.worktrees(), [])
        self.assertEqual(self.tip(), self.base, "a cancelled step publishes nothing")
        self.assertTrue(git(self.x, "rev-parse", "--verify", "-q", "refs/heads/" + tree.name.replace("shiploop-loop", "auto/shiploop-loop")), "the loop branch stays")
        self.x_clean()
        poll = self.poll("s1")
        self.assertEqual(poll["status"], "cancelled")
        self.assertIn("seconds", poll["iteration"]["consumed"])

    def test_cancel_also_ends_the_sessions_below_the_worker_that_nothing_recorded(self):
        _worker, engine, _tree = self.hung("s1", {"escape": "tree"})
        table = facade.ps_rows()
        below = [row for row in facade.descendants(table, engine) if row["pgid"] != table[engine]["pgid"]]
        self.assertEqual(len(below), 1, "a model session in a session of its own, a child of the engine")
        self.run_cli("step", "cancel", "--handle", "s1")
        self.assertFalse(alive(below[0]["pid"]), "the snapshot of the worker's descendants ended it")
        self.assertEqual(self.record("s1")["kill"]["sessions"], 1)

    def test_cancel_runs_the_lifecycle_cleanup_for_hosts_the_harness_recorded(self):
        _worker, _engine, _tree = self.hung("s1", {"escape": "ledger"})
        self.run_cli("step", "cancel", "--handle", "s1")
        record = self.record("s1")
        folders = record["cleanup"]["folders"]
        first = next(iter(folders.values()))["first"]
        self.assertEqual(len(first["stopped"]), 1, "the first result is kept: a second cleanup is idempotent and would hide it")
        cleanup = self.run_cli("cleanup", "--keys", "s1")
        self.assertTrue(cleanup["verified"], cleanup)
        self.assertEqual(len(next(iter(self.record("s1")["cleanup"]["folders"].values()))["first"]["stopped"]), 1)

    def test_a_worker_killed_alone_is_found_dead_by_the_next_poll_and_its_engine_is_stopped(self):
        worker, engine, _tree = self.hung("s1")
        os.kill(worker, signal.SIGKILL)
        self.assertTrue(wait_for(lambda: not alive(worker), 10))
        self.assertTrue(alive(engine), "the engine is a separate process in the worker's group")
        reply = self.poll("s1")
        self.assertEqual(reply["status"], "failed")
        self.assertIn("worker ended without a result", reply["error"])
        self.assertFalse(alive(engine))
        record = self.record("s1")
        self.assertEqual(record["archives"][0]["ledger_rows"], 1)
        self.assertEqual(self.worktrees(), [])
        self.assertEqual(self.tip(), self.base)
        self.x_clean()

    def test_cleanup_ends_a_step_whose_handle_was_lost(self):
        worker, engine, _tree = self.hung("s1")
        reply = self.run_cli("cleanup", "--keys", "s1,never-started")
        self.assertTrue(reply["verified"], reply)
        self.assertIn("never-started: no step record", reply["receipt"])
        self.assertFalse(alive(worker) or alive(engine))
        self.assertEqual(self.record("s1")["state"], "cancelled")

    def test_a_crashing_engine_fails_the_step_and_publishes_nothing(self):
        self.set_knobs({"*": {"fault": "crash"}})
        self.start("s1", ["hello"])
        reply = self.finish("s1")
        self.assertEqual(reply["status"], "failed")
        self.assertIn("the engine exited 3", reply["error"])
        self.assertEqual(set(reply["iteration"]["consumed"]), {"seconds", "runs"})
        self.assertEqual(self.tip(), self.base)
        self.assertEqual(self.worktrees(), [])
        self.x_clean()

    def test_one_step_at_a_time_and_a_duplicate_start_launches_nothing_twice(self):
        self.set_knobs({"*": {"sleep": 4}})
        first = self.start("s1", ["hello"])
        again = self.start("s1", ["hello"])
        self.assertEqual((again["handle"], again["status"]), (first["handle"], "running"))
        refused = self.start("s2", ["hello"], check=False)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("step s1 has not finished", refused.stderr)
        done = self.finish("s1")
        self.assertEqual(len(self.engine_calls()), 1, "the duplicate start launched no second engine")
        replay = self.start("s1", ["hello"])
        self.assertEqual(replay["status"], "done")
        self.assertEqual(replay["iteration"], done["iteration"])


class PublicationTests(StepCase):
    """The on-disk states a kill leaves around the two-phase publication, and around the start intent."""

    def prepared(self, key="p1", tip_from=None, tip_to=None):
        out = self.work / "runs" / key
        out.mkdir(parents=True)
        rec = {"schema": facade.STEP_SCHEMA, "key": key, "scope": "s1", "cases": ["hello"], "mode": "iterate", "base": self.build(), "out": str(out),
               "profile": {}, "tip_from": tip_from or self.base, "build_before": self.build(), "scoring_before": "s", "state": "prepared",
               "created_at": "t", "created_epoch": time.time(), "worker": None, "invocations": [], "error": None,
               "iteration": {"consumed": {"seconds": 1.0, "runs": 0}},
               "prepared": {"tip_from": tip_from or self.base, "tip_to": tip_to}}
        facade.save_step(self.layout, rec)
        return rec

    def commit_on_top(self, parent):
        git(self.x, "checkout", "-q", "--detach", parent)
        git(self.x, "commit", "-q", "--allow-empty", "-m", "a learning commit")
        return git(self.x, "rev-parse", "HEAD")

    def test_prepared_and_the_tip_still_at_the_start_is_moved_by_the_next_poll(self):
        result = self.commit_on_top(self.base)
        self.prepared(tip_to=result)
        reply = self.poll("p1")
        self.assertEqual(reply["status"], "done")
        self.assertEqual(self.tip(), result)

    def test_prepared_and_the_tip_already_at_the_result_completes_without_moving_it(self):
        result = self.commit_on_top(self.base)
        git(self.x, "update-ref", facade.TIP_REF, result)
        self.prepared(tip_to=result)
        self.assertEqual(self.poll("p1")["status"], "done")
        self.assertEqual(self.tip(), result)
        self.assertEqual(self.record("p1")["state"], "published")

    def test_prepared_and_the_tip_somewhere_else_is_refused_and_reported(self):
        result = self.commit_on_top(self.base)
        elsewhere = self.commit_on_top(result)
        git(self.x, "update-ref", facade.TIP_REF, elsewhere)
        self.prepared(tip_to=result)
        reply = self.poll("p1")
        self.assertEqual(reply["status"], "failed")
        self.assertIn("neither", reply["error"])
        self.assertEqual(self.tip(), elsewhere, "the tip was not moved")

    def test_a_publication_that_loses_the_race_to_the_same_move_is_still_a_success(self):
        result = self.commit_on_top(self.base)
        rec = self.prepared(tip_to=result)
        real_git = facade.git

        def racing(repo, *args, **kwargs):
            if args[:2] == ("update-ref", facade.TIP_REF):
                real_git(repo, *args)  # the other actor's move lands first ...
                raise facade.FacadeError("cannot lock ref: reference already exists")  # ... and ours is the one that fails
            return real_git(repo, *args, **kwargs)
        facade.git = racing
        try:
            facade.publish(self.layout, rec)
        finally:
            facade.git = real_git
        self.assertEqual(self.record("p1")["state"], "published")
        self.assertEqual(self.tip(), result)

    def test_a_start_intent_with_no_worker_is_begun_by_a_later_poll(self):
        out = self.work / "runs" / "s1"
        original = facade.spawn_worker
        facade.spawn_worker = lambda layout, rec: None  # the call died after writing its intent and before launching anything
        try:
            os.environ["CLOSED_LOOP_WORKSPACE"] = str(self.x)
            args = type("Args", (), {"key": "s1", "scope": "s1", "cases": "hello", "mode": "iterate", "base": self.build(), "out": str(out),
                                     "host": "codex", "model": "m", "effort": "high", "calibration": None, "tolerance": 0.25,
                                     "attempts": 1, "parallel": 1, "engine_arg": None})
            facade.step_start(self.layout, args)
        finally:
            facade.spawn_worker = original
        record = self.record("s1")
        self.assertEqual((record["state"], record["worker"]), ("starting", None))
        record["created_epoch"] -= 60  # past the boot grace
        facade.save_step(self.layout, record)
        reply = self.poll("s1")
        self.assertEqual(reply["status"], "running", "the replay began the worker")
        self.assertEqual(self.valid(self.finish("s1"), ["hello"])["cases"]["hello"]["ran"], True)


class RaceTests(StepCase):
    def test_polls_that_race_the_worker_never_turn_a_published_step_into_a_failed_one(self):
        """Two actors act on a finished step, the worker that publishes and whoever polls it: the first version let a poll publish a
        `prepared` record while the worker did, lose the race on `update-ref`, and overwrite the record with `failed` (seen in a full run)."""
        import threading
        self.start("s1", ["hello"])
        replies, raised, stop = [], [], threading.Event()

        def hammer():
            try:
                while not stop.is_set():
                    replies.append(self.poll("s1")["status"])
            except BaseException as error:  # noqa: BLE001 - a poll that raised is a failure of the test, not a lost thread
                raised.append(repr(error))
        threads = [threading.Thread(target=hammer) for _ in range(3)]
        for thread in threads:
            thread.start()
        try:
            wait_for(lambda: self.record("s1")["state"] in ("published", "failed", "cancelled"), 120, 0.1)
            time.sleep(1.0)  # polls that start after the worker published, and ones still in flight
        finally:
            stop.set()
            for thread in threads:
                thread.join()
        self.assertEqual(raised, [], "no polling thread raised")
        self.assertEqual(self.record("s1")["state"], "published")
        self.assertEqual(set(replies) - {"running", "done"}, set(), replies)
        self.assertEqual(self.tip(), self.record("s1")["prepared"]["tip_to"])


class ProbeTests(StepCase):
    """The model-free probes. The ones that start a model session (`cases.runs`) and read its run are in the real-engine suite."""

    def test_the_bounded_claim_needs_a_build_a_green_tier_and_a_caught_planted_edit(self):
        reply = self.probe("improver.bounded")
        self.assertEqual(reply["state"], "bounded", reply)
        for words in ("the plugin build passed", "the quick tier passed", "was caught: out of scope ['test/shiploop_e2e/cases.json']"):
            self.assertIn(words, reply["evidence"])
        receipt = json.loads(self.layout.tier_file(self.build()).read_text())
        self.assertEqual((receipt["green"], receipt["build"]), (True, self.build()))
        self.x_clean()
        self.assertEqual(git(self.x, "rev-parse", "HEAD"), self.base, "a probe works in a clone under the state folder, never in X")
        self.assertTrue(list(self.layout.probes.glob("bounded/*/x")))
        self.start("s1", ["hello"])
        self.assertTrue(self.valid(self.finish("s1"), ["hello"])["tier"]["green"], "an unchanged build carries the receipt the probe kept")

    def test_a_red_quick_tier_leaves_the_claim_declared_and_the_receipt_red(self):
        reply = self.probe("improver.bounded", env={"FAKE_TIER_EXIT": "1"})
        self.assertEqual(reply["state"], "declared")
        self.assertIn("the quick tier exited 1", reply["evidence"])
        self.assertFalse(json.loads(self.layout.tier_file(self.build()).read_text())["green"])

    def test_the_scores_claim_needs_a_stored_real_run(self):
        reply = self.probe("grading.scores")
        self.assertEqual(reply["state"], "declared")
        self.assertIn("no stored real run folder", reply["evidence"])

    def report(self, driver, tamper=False, name="calibration.json", cases=("hello",), attempts=6, compared=20, k=3, tolerance=0.45):
        """A calibration/1 report in the shape spread.calibrate writes: per case the sealed attempts, a false-decision rate at every grid
        tolerance (above the 0.10 threshold below 0.45, under it from 0.45, so spread.recommend gives 0.45) and the compared splits."""
        digest = facade.bridge(self.layout, "scoring_digest", {"cases": list(cases)})["sha256"]
        rates = {f"{0.05 * step:.2f}": (0.5 if step < 9 else 0.04) for step in range(1, 11)}
        path = self.folder / name
        path.write_text(json.dumps({"contract": "calibration/1", "driver": driver, "attempts_sealed": attempts * len(cases),
                                    "cases": {case: {"attempts": attempts, "false_decision": {"tokens": {**rates, "compared": compared}}}
                                              for case in cases},
                                    "scoring": {"cases": list(cases), "sha256": "0" * 64 if tamper else digest},
                                    "recommended": {"attempts": k, "tolerance": tolerance, "metric": "tokens", "why": None}}))
        return path

    def test_the_calibrated_claim_needs_a_report_for_this_profile_whose_digest_still_holds(self):
        claim = "grading.calibrated:codex/fake-model/high"
        driver = {"host": "codex", "model": "fake-model", "effort": "high"}
        proven = self.probe(claim, "--calibration", str(self.report(driver)))
        self.assertEqual(proven["state"], "calibrated", proven)
        self.assertIn("3 attempts per arm at tolerance 0.45 on tokens", proven["evidence"])
        cases = (("no report", (), "no calibration report was given"),
                 ("a changed scoring digest", ("--calibration", str(self.report(driver, tamper=True, name="tampered.json"))), "scoring files or case entries changed"),
                 ("another driver", ("--calibration", str(self.report({**driver, "model": "other"}, name="other.json"))), "the report is for codex/other/high"),
                 ("no such file", ("--calibration", str(self.folder / "missing.json")), "not a usable calibration"),
                 ("no case at all", ("--calibration", str(self.report(driver, cases=(), name="empty.json"))), "covers no case"),
                 ("too few attempts to make two arms", ("--calibration", str(self.report(driver, attempts=4, name="thin.json"))),
                  "holds no measured noise for hello"),
                 ("no compared splits", ("--calibration", str(self.report(driver, compared=0, name="unmeasured.json"))),
                  "holds no measured noise for hello"),
                 ("zero attempts per arm", ("--calibration", str(self.report(driver, k=0, name="zero.json"))), "not a positive whole number"),
                 ("a recommendation its own rates do not give", ("--calibration", str(self.report(driver, tolerance=0.25, name="inconsistent.json"))),
                  "does not follow from what was measured"))
        for label, flags, words in cases:
            with self.subTest(label):
                refused = self.probe(claim, *flags)
                self.assertEqual(refused["state"], "unmeasured")
                self.assertIn(words, refused["evidence"])

    def test_a_claim_the_facade_cannot_prove_is_an_error_not_a_state(self):
        refused = self.run_cli("probe", "grading.sensitive:accuracy", check=False)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("has no probe for", refused.stderr)


class RiggedBoundaryTests(StepCase):
    """A positive control is worth something only if the check can fail: with a harness whose boundary rule lets every path through, the
    planted edit to a harness file is not caught, and the claim stays declared."""

    variant = "rigged"

    def test_a_boundary_that_lets_a_harness_edit_through_is_not_bounded(self):
        reply = self.probe("improver.bounded")
        self.assertEqual(reply["state"], "declared")
        self.assertIn("NOT separated by boundary.candidate_path", reply["evidence"])
        self.assertIn("the quick tier passed", reply["evidence"], "the other two parts held, so the failure is the planted edit's alone")


class BootWindowTests(StepCase):
    """The worker owns its record while it lives; a canceller must not rewrite it until the worker is gone, and a worker that starts after
    a cancel must do nothing."""

    def test_a_worker_that_starts_after_a_cancel_does_nothing(self):
        self.intent_only()
        self.run_cli("step", "cancel", "--handle", "s1")
        self.assertEqual(self.record("s1")["state"], "cancelled")
        done = subprocess.run([sys.executable, "-B", str(FACADE), "worker", "--key", "s1"], capture_output=True, text=True, check=False,
                              env={"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp"), "CLOSED_LOOP_WORKSPACE": str(self.x),
                                   "FAKE_ENGINE": str(self.knobs), "FAKE_LOG": str(self.log)})
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.record("s1")["state"], "cancelled", "the late worker did not run the step or rewrite its record")
        self.assertEqual(self.engine_calls(), [])

    def test_a_cancel_waits_for_a_worker_that_is_still_booting_and_then_settles_the_record(self):
        self.intent_only()
        booting = facade.WorkerLock(self.layout.lock_file("s1"))  # a worker that holds its lock but has not recorded who it is
        self.assertTrue(booting.acquire())
        cancel = subprocess.Popen([sys.executable, "-B", str(FACADE), "step", "cancel", "--handle", "s1"], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True,
                                  env={"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp"), "CLOSED_LOOP_WORKSPACE": str(self.x)})
        time.sleep(1.5)
        self.assertIsNone(cancel.poll(), "the cancel waits: the lock is held, so the record is not its to rewrite")
        self.assertEqual(self.record("s1")["state"], "starting")
        booting.release()  # the worker ends (here: never was)
        out, err = cancel.communicate(timeout=30)
        self.assertEqual(cancel.returncode, 0, err)
        self.assertEqual(json.loads(out)["status"], "cancelled")
        self.assertEqual(self.record("s1")["state"], "cancelled")


class ReviewFindingsTests(StepCase):
    """Regression tests for the Sol max review of the facade's contract (docs/experiments/closed-loop-phase2-review-20261115/g1-sol-answer.txt)."""

    def test_two_steps_started_at_the_same_moment_are_not_both_admitted(self):
        """Both starts are held where each asks whether another step is unsettled. Without the admission lock both would see none and both
        would be admitted; with it the second waits, then sees the first's intent (the barrier times out, which is the serialisation)."""
        import threading
        barrier = threading.Barrier(2)
        real_unsettled, real_spawn = facade.unsettled_keys, facade.spawn_worker

        def held(layout):
            with contextlib.suppress(threading.BrokenBarrierError):
                barrier.wait(timeout=2)
            return real_unsettled(layout)
        os.environ["CLOSED_LOOP_WORKSPACE"] = str(self.x)
        base, results = self.build(), {}

        def start(key):
            try:
                results[key] = facade.step_start(self.layout, self.start_args(key, base))["status"]
            except facade.FacadeError as error:
                results[key] = str(error)
        facade.unsettled_keys, facade.spawn_worker = held, (lambda layout, rec: None)
        try:
            threads = [threading.Thread(target=start, args=(key,)) for key in ("a1", "b1")]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=60)
        finally:
            facade.unsettled_keys, facade.spawn_worker = real_unsettled, real_spawn
        self.assertEqual(sorted(value == "running" for value in results.values()), [False, True], results)
        self.assertTrue(any("has not finished" in value for value in results.values()), results)

    def test_a_decision_is_refused_while_a_step_has_not_been_settled_and_accepted_after(self):
        publication = PublicationTests("test_prepared_and_the_tip_still_at_the_start_is_moved_by_the_next_poll")
        publication.x, publication.layout, publication.work, publication.base = self.x, self.layout, self.work, self.base
        publication.build, publication.poll, publication.record = self.build, self.poll, self.record
        result = publication.commit_on_top(self.base)
        publication.prepared(tip_to=result)  # a finished step whose worker is gone and whose tip has not moved yet
        refused = self.run_cli("decide", "--record", "LR-20261101-000002", "--outcome", "accept", "--reason", "the owner's words", check=False)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("has not finished", refused.stderr)
        self.assertEqual(self.poll("p1")["status"], "done", "the poll publishes the step's tip")
        accepted = self.run_cli("decide", "--record", "LR-20261101-000002", "--outcome", "accept", "--reason", "the owner's words")
        self.assertEqual(git(self.x, "rev-parse", f"{accepted['tip']}^"), result, "the decision sits on the step's published tip")

    def test_the_replay_of_a_start_whose_step_failed_or_was_cancelled_answers_running_and_the_poll_reports_it(self):
        self.set_knobs({"*": {"fault": "crash"}})
        first = self.start("s1", ["hello"])
        self.assertEqual(first, {"handle": "s1", "status": "running"})
        self.assertEqual(self.finish("s1")["status"], "failed")
        replay = self.start("s1", ["hello"])
        self.assertEqual(replay, {"handle": "s1", "status": "running"}, "the orchestrator accepts only running or done from a start")
        poll = self.poll("s1")
        self.assertEqual((poll["status"], sorted(poll["iteration"]["consumed"])), ("failed", ["runs", "seconds"]))
        self.set_knobs({"*": {"fault": "hang"}})
        self.start("s2", ["hello"])
        self.assertEqual(self.run_cli("step", "cancel", "--handle", "s2")["status"], "cancelled")
        self.assertEqual(self.start("s2", ["hello"]), {"handle": "s2", "status": "running"}, "a cancelled step is answered the same way")
        self.assertEqual(self.poll("s2")["status"], "cancelled")

    def test_a_judge_that_recovered_on_a_retry_is_valid_and_one_that_never_did_is_not(self):
        self.set_knobs({"*": {"judge_retry": "recovered"}})
        self.start("s1", ["hello"])
        recovered = self.valid(self.finish("s1"), ["hello"])
        self.assertEqual(recovered["judge"], {"valid": True, "complete": True}, "the last assessment is the one that counts, not the first folder")
        self.set_knobs({"*": {"judge_retry": "exhausted"}})
        self.start("s2", ["hello"])
        exhausted = self.valid(self.finish("s2"), ["hello"])
        self.assertEqual(exhausted["judge"], {"valid": False, "complete": True})

    def test_an_epoch_review_that_was_redone_is_complete(self):
        self.set_knobs({"csv-report": {"decision": "DROP", "review_retry": "recovered"}})
        self.start("s1", ["csv-report"])
        recovered = self.valid(self.finish("s1"), ["csv-report"])
        self.assertEqual(recovered["review"], {"valid": True, "complete": True}, "an incomplete review that was redone is not still incomplete")

    def test_an_epoch_review_left_incomplete_is_incomplete(self):
        self.set_knobs({"csv-report": {"decision": "DROP", "review_retry": "incomplete"}})
        self.start("s1", ["csv-report"])
        left = self.valid(self.finish("s1"), ["csv-report"])
        self.assertEqual(left["review"], {"valid": False, "complete": False})

    def test_a_cleanup_that_races_a_finishing_step_does_not_turn_it_into_a_cancelled_one(self):
        """The worker publishes while cleanup waits for it: the record stays `published` with its iteration."""
        publication = PublicationTests("test_prepared_and_the_tip_still_at_the_start_is_moved_by_the_next_poll")
        publication.x, publication.layout, publication.work, publication.base = self.x, self.layout, self.work, self.base
        publication.build = self.build
        result = publication.commit_on_top(self.base)
        rec = publication.prepared(tip_to=result)
        finishing = facade.WorkerLock(self.layout.lock_file("p1"))
        self.assertTrue(finishing.acquire())  # a live worker, between `prepared` and `published`
        cleanup = subprocess.Popen([sys.executable, "-B", str(FACADE), "cleanup", "--keys", "p1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, env={"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp"), "CLOSED_LOOP_WORKSPACE": str(self.x)})
        time.sleep(1.5)
        self.assertIsNone(cleanup.poll(), "cleanup waits for a step that is only finishing: it never stops one")
        git(self.x, "update-ref", facade.TIP_REF, result)
        rec.update(state="published")
        facade.save_step(self.layout, rec)  # the worker's last save
        finishing.release()
        _out, err = cleanup.communicate(timeout=30)
        self.assertEqual(cleanup.returncode, 0, err)
        self.assertEqual(self.record("p1")["state"], "published")
        self.assertEqual(self.record("p1")["iteration"], rec["iteration"])

    def test_a_kill_that_left_something_running_is_a_blocker_for_a_verified_cleanup(self):
        for kill, words in (({"group": "survived", "survivors": []}, "process group survived"),
                            ({"group": "protected", "survivors": []}, "process group protected"),
                            ({"group": "unverified", "survivors": []}, "process group unverified"),
                            ({"group": "stopped", "survivors": [123, 456]}, "2 process(es) below the worker did not end")):
            self.assertIn(words, " ".join(facade.kill_problems(kill)))
        for kill in ({"group": "stopped", "survivors": []}, {"group": "gone", "survivors": []}, {"group": "reused", "survivors": []}, None):
            self.assertEqual(facade.kill_problems(kill), [])
        self.intent_only()
        rec = self.record("s1")
        rec["kill"] = {"group": "survived", "detail": {}, "sessions": 0, "survivors": [], "at": "t"}
        facade.settle(self.layout, rec, "cancelled", "cancelled by the operator")
        self.assertIn("process group survived", self.record("s1")["error"], "the settle says what the kill left")

    def test_a_worker_that_cannot_read_the_process_table_fails_the_step_and_is_not_started_again_forever(self):
        self.intent_only()
        real = facade.ps_rows

        def broken(*_args, **_kwargs):
            raise facade.FacadeError("ps could not be run: [Errno 1] Operation not permitted")
        facade.ps_rows = broken
        try:
            facade.worker_main(self.layout, "s1")
        finally:
            facade.ps_rows = real
        record = self.record("s1")
        self.assertEqual(record["state"], "failed")
        self.assertIn("ps could not be run", record["error"])
        # and a start that never produced a worker is begun again a bounded number of times
        self.intent_only("s2")
        started = []
        original = facade.spawn_worker
        facade.spawn_worker = lambda layout, rec: started.append(rec["key"])
        try:
            for _ in range(facade.MAX_SPAWNS + 2):
                rec = self.record("s2")
                rec["spawned_epoch"] -= 60
                facade.save_step(self.layout, rec)
                facade.advance(self.layout, self.record("s2"))
        finally:
            facade.spawn_worker = original
        self.assertEqual(len(started), facade.MAX_SPAWNS - 1, "the first spawn was the start's own; the rest are bounded")
        failed = self.record("s2")
        self.assertEqual(failed["state"], "failed")
        self.assertIn(f"did not start in {facade.MAX_SPAWNS} attempts", failed["error"])


class SecondReviewTests(StepCase):
    """Regression tests for Sol's verification review of the G1 fixes (docs/experiments/closed-loop-phase2-review-20261115/g1b-sol-answer.txt)."""

    def dead_worker_step(self, leader, member):
        self.intent_only()
        rec = self.record("s1")
        rec.update(state="running", worker={"pid": leader, "pgid": leader, "started": member["started"], "at": time.time()})
        facade.save_step(self.layout, rec)

    def test_cleanup_stops_what_a_worker_that_died_alone_left_in_its_group(self):
        """The worker's lock is free at once, which proves nothing about its group: the engine it left behind is stopped."""
        leader, member, _child = orphaned_group(self)
        self.dead_worker_step(leader, member)
        reply = self.run_cli("cleanup", "--keys", "s1")
        self.assertTrue(reply["verified"], reply)
        self.assertTrue(wait_for(lambda: not alive(member["pid"]), 10), "the process the dead worker left in its group was stopped")
        record = self.record("s1")
        self.assertEqual((record["state"], record["kill"]["group"]), ("cancelled", "stopped"))

    def test_a_cancel_stops_what_a_worker_that_died_alone_left_in_its_group(self):
        leader, member, _child = orphaned_group(self)
        self.dead_worker_step(leader, member)
        self.assertEqual(self.run_cli("step", "cancel", "--handle", "s1")["status"], "cancelled")
        self.assertTrue(wait_for(lambda: not alive(member["pid"]), 10))

    def test_a_cleanup_whose_kill_left_a_survivor_is_not_verified(self):
        self.intent_only()
        rec = self.record("s1")
        rec.update(state="running", worker={"pid": 999999, "pgid": 999999, "started": "x", "at": time.time()})
        facade.save_step(self.layout, rec)
        real = facade.kill_step
        facade.kill_step = lambda layout, rec: {"group": "survived", "detail": {}, "sessions": 1, "survivors": [4242], "at": "t"}
        os.environ["CLOSED_LOOP_WORKSPACE"] = str(self.x)
        try:
            reply = facade.cmd_cleanup(type("Args", (), {"keys": "s1"}))
        finally:
            facade.kill_step = real
        self.assertFalse(reply["verified"], reply)
        self.assertIn("process group survived", reply["receipt"])
        self.assertIn("1 process(es) below the worker did not end", reply["receipt"])

    def test_a_poll_does_not_publish_while_another_caller_holds_the_step(self):
        """The poll saw the lock free (its liveness probe), then a cleanup took the step: the publication itself must need the lock."""
        key, result = self.prepared_step()
        holder = facade.WorkerLock(self.layout.lock_file(key))
        self.assertTrue(holder.acquire())  # a cleanup or a cancel holds the step
        real_alive = facade.worker_alive
        facade.worker_alive = lambda layout, name: False  # the probe ran a moment before the cleanup took the lock
        try:
            self.assertEqual(facade.advance(self.layout, self.record(key))["status"], "running")
            self.assertEqual((self.tip(), self.record(key)["state"]), (self.base, "prepared"), "nothing is published while the step is someone else's")
        finally:
            facade.worker_alive = real_alive
            holder.release()
        self.assertEqual(self.poll(key)["status"], "done")
        self.assertEqual(self.tip(), result)

    def test_cleanup_publishes_a_finished_step_whose_worker_is_gone(self):
        key, result = self.prepared_step()
        reply = self.run_cli("cleanup", "--keys", key)
        self.assertTrue(reply["verified"], reply)
        self.assertEqual((self.record(key)["state"], self.tip()), ("published", result), "a cleanup never leaves a finished step unsettled")
        self.assertEqual(self.start("s9", ["hello"])["status"], "running", "and the workspace is free for the next step")

    def test_a_poll_that_read_an_old_spawn_time_does_not_begin_a_second_worker(self):
        self.intent_only()
        rec = self.record("s1")
        rec["spawned_epoch"] -= 60
        facade.save_step(self.layout, rec)
        stale, started = dict(rec), []
        real_spawn, real_load = facade.spawn_worker, facade.load_step
        facade.spawn_worker = lambda layout, rec: started.append(rec["spawns"])
        try:
            facade.advance(self.layout, self.record("s1"))  # poll A: the grace has passed, it begins a worker
            reads = []

            def stale_first(layout, key):  # poll B read the record before A updated it
                if not reads:
                    reads.append(key)
                    return dict(stale)
                return real_load(layout, key)
            facade.load_step = stale_first
            facade.advance(self.layout, stale)
        finally:
            facade.spawn_worker, facade.load_step = real_spawn, real_load
        self.assertEqual(started, [2], "one respawn: the second poll checked the spawn time again under the lock")
        self.assertEqual(self.record("s1")["spawns"], 2)

    def test_a_start_reads_the_tip_only_after_no_step_is_unsettled(self):
        order = []
        real_unsettled, real_tip, real_spawn = facade.unsettled_keys, facade.published_tip, facade.spawn_worker
        facade.unsettled_keys = lambda layout: order.append("unsettled") or real_unsettled(layout)
        facade.published_tip = lambda layout: order.append("tip") or real_tip(layout)
        facade.spawn_worker = lambda layout, rec: None
        os.environ["CLOSED_LOOP_WORKSPACE"] = str(self.x)
        try:
            args = self.start_args("s1", base=self.build())
            order.clear()
            facade.step_start(self.layout, args)
        finally:
            facade.unsettled_keys, facade.published_tip, facade.spawn_worker = real_unsettled, real_tip, real_spawn
        self.assertLess(order.index("unsettled"), order.index("tip"), "with none unsettled and admission held, nothing can move the tip")

    def test_an_epoch_receipt_changed_after_its_review_is_not_a_review(self):
        self.set_knobs({"csv-report": {"decision": "DROP", "review_retry": "rewritten"}})
        self.start("s1", ["csv-report"])
        it = self.valid(self.finish("s1"), ["csv-report"])
        self.assertEqual(it["review"], {"valid": False, "complete": False}, "epoch.state demotes an attempt whose receipt no longer matches its seal")

    def test_the_last_decision_of_an_epoch_is_the_one_that_counts(self):
        out = Path(tempfile.mkdtemp(prefix="epoch-", dir=STATE["folder"]))
        epoch = out / "cycle-1" / "epoch"
        (epoch / "receipts").mkdir(parents=True)
        (epoch / "receipts" / "a-1.json").write_text("{}")
        seal = hashlib.sha256((epoch / "receipts" / "a-1.json").read_bytes()).hexdigest()
        events = [{"kind": "decision", "result": {"decision": "UNDECIDED", "attempts": [{"id": "a"}]}},
                  {"kind": "reviewed", "attempt_id": "a", "receipt": "receipts/a-1.json", "receipt_sha256": seal},
                  {"kind": "decision", "result": {"decision": "DROP", "attempts": [{"id": "a"}]}}]
        (epoch / "events.jsonl").write_text("".join(json.dumps(event) + "\n" for event in events))
        found = facade.epoch_evidence(out)
        self.assertEqual(found["decision"]["decision"], "DROP", "epoch.state takes the last decision")
        self.assertEqual((found["incomplete"], len(found["receipts"])), (0, 1))


class OrchestratorConvergenceTests(StepCase):
    """The real orchestrator with the facade's real step verbs, on stand-in evidence and an empty ledger, with readiness answered by a stub:
    evidence that is quiet and comparable converges the scope, and evidence that misses its floors never does. (The real-engine suite's
    fake hosts leave fidelity unobserved, so they can show only the second.)"""

    variant = "clean"

    def campaign(self, knobs, iterations):
        self.set_knobs(knobs)
        facade.write_json(self.layout.tier_file(self.build()), {"green": True, "build": self.build(), "at": "2026-11-15T00:00:00Z"})
        stub = self.folder / "probe_stub.py"
        stub.write_text("import json, sys\nTOP = {'cases.runs': 'runs', 'grading.scores': 'scores', 'improver.bounded': 'bounded', "
                        "'grading.calibrated': 'calibrated'}\nprint(json.dumps({'state': TOP[sys.argv[-1].split(':')[0]], "
                        "'evidence': 'stub: ' + sys.argv[-1], 'consumed': {'seconds': 0}}))\n")
        manifest = json.loads((HARNESS / "adapter" / "adapter.json").read_text())
        manifest["execution"]["pin"] = [str(FACADE), str(HARNESS / "adapter" / "allowlist.json"), str(stub)]
        manifest["execution"]["cwd"] = str(self.folder)
        manifest["execution"]["env_allow"] = sorted({*manifest["execution"]["env_allow"], "FAKE_ENGINE", "FAKE_LOG", "FAKE_TIER_EXIT",
                                                     "PYTHONDONTWRITEBYTECODE"})
        for name in ("cases", "records", "identity", "step"):
            manifest["commands"][name][1] = str(FACADE)
        manifest["commands"]["probe"] = [sys.executable, str(stub)]
        manifest["execution"]["cleanup"][1] = str(FACADE)
        path = self.folder / "adapter.json"
        path.write_text(json.dumps(manifest))
        campaign = self.folder / "campaign"

        def loop(*args, ok=(0,)):
            done = subprocess.run([sys.executable, "-B", str(ROOT / "skills" / "closed-loop" / "scripts" / "closed_loop.py"), *args],
                                  capture_output=True, text=True, check=False,
                                  env={"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp"), "CLOSED_LOOP_WORKSPACE": str(self.x),
                                       "FAKE_ENGINE": str(self.knobs), "FAKE_LOG": str(self.log), "PYTHONDONTWRITEBYTECODE": "1"})
            self.assertIn(done.returncode, ok, f"closed_loop.py {' '.join(args)}: {done.stdout[-500:]} {done.stderr[-300:]}")
            return json.loads(done.stdout)
        loop("init", "--manifest", str(path), "--campaign", str(campaign), "--workspace", str(self.x), "--cases", "hello", "--budget",
             "seconds=3600,runs=50", "--quiet-window", "1")
        loop("ratify", "--campaign", str(campaign), "--yes-owner-approved", "--note", "rehearsal: the test plays the owner")
        self.assertTrue(loop("readiness", "--manifest", str(path), "--campaign", str(campaign), "--workspace", str(self.x), "--require-start")["start_ok"])
        certificate = status = None
        for _ in range(80):
            loop("step", "--campaign", str(campaign), ok=(0, 1))
            certificate = loop("certificate", "--campaign", str(campaign), ok=(0, 1))
            status = loop("status", "--campaign", str(campaign), "--no-certificate")
            if certificate["status"] == "converged" or status["iterations"] >= iterations:
                break
            time.sleep(0.4)
        return certificate, status

    def test_quiet_and_comparable_evidence_converges_the_scope(self):
        certificate, status = self.campaign({"*": {}}, 4)
        self.assertEqual(certificate["status"], "converged", certificate.get("reasons"))
        self.assertEqual(status["iterations"], 2, "the first iteration has no comparable baseline, the second has")

    def test_evidence_that_misses_its_floors_never_converges(self):
        certificate, status = self.campaign({"*": {"oracle": "fail"}}, 3)
        self.assertEqual(certificate["status"], "incomplete")
        self.assertTrue(any("floors" in reason for reason in certificate["reasons"]), certificate["reasons"])
        self.assertGreaterEqual(status["iterations"], 1)


class RefusalTests(StepCase):
    def refused(self, *cases, mode="iterate", out=None, base=None, text):
        done = self.run_cli("step", "--tolerance", "0.25", "--attempts", "1", "start", "--key", "r1", "--scope", "s1", "--cases", ",".join(cases),
                            "--mode", mode, "--base", base or self.build(), "--out", str(out or self.work / "runs" / "r1"), check=False)
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertIn(text, done.stderr)
        self.assertFalse((self.layout.steps / "r1.json").exists(), "a refused start writes no intent")

    def test_the_preflight_limits(self):
        self.refused("nonesuch", text="not in the allowlist")
        self.refused("hello", "hello", text="each once")
        self.refused("hello", mode="grind", text="iterate or sweep")
        self.refused("hello", base="b-stale", text="the published build is")
        self.refused("hello", out=self.x / "inside", text="outside the evaluator clone")
        full = self.folder / "occupied"
        full.mkdir()
        (full / "file").write_text("x")
        self.refused("hello", out=full, text="not empty")
        (self.x / "dirty.txt").write_text("an uncommitted path")
        self.refused("hello", text="uncommitted paths: dirty.txt")

    def test_a_poll_for_an_unknown_handle_is_an_error(self):
        done = self.run_cli("step", "poll", "--handle", "missing", check=False)
        self.assertEqual(done.returncode, 2)
        self.assertIn("no step with handle missing", done.stderr)


class PureTests(unittest.TestCase):
    def test_a_cleanup_that_is_not_proof_of_nothing_left_is_rejected(self):
        problems = facade.lifecycle_problems
        self.assertEqual(problems({"observed": True, "stopped": [{}], "survived": [], "unverified": [], "protected": []}), [])
        self.assertTrue(problems({"observed": False, "reason": "ps failed"}))
        self.assertIn("1 group(s) survived", problems({"observed": True, "survived": [{}]}))
        self.assertIn("1 group(s) unverified", problems({"observed": True, "unverified": [{}]}), "the CLI exits 0 for these two")
        self.assertIn("1 group(s) protected", problems({"observed": True, "protected": [{}]}))

    def test_loop_journal_facts(self):
        text = ("# Qualified loop: hello\n\n- worktree /a/b, c, branch auto/shiploop-loop-123abc\n\n## Exploration 1\n\n- records opened: none\n\n"
                "## Cycle 1: LR-20261101-000001\n\n- decision: DROP\n\n## Result\n\n- stopped: reached --iterations 1\n")
        found = facade.parse_loop(text)
        self.assertEqual((found["worktree"], found["branch"], found["explored"], found["cycle"], found["stop"]),
                         ("/a/b, c", "auto/shiploop-loop-123abc", True, "LR-20261101-000001", "reached --iterations 1"))

    def test_a_group_is_not_stopped_when_its_leader_pid_names_another_process(self):
        stranger = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"], start_new_session=True)
        self.addCleanup(lambda: (stranger.kill(), stranger.wait()))
        how, _detail = facade.stop_group({"pid": stranger.pid, "pgid": stranger.pid, "started": "Mon Jan  1 00:00:00 1990"})
        self.assertEqual(how, "reused")
        self.assertTrue(alive(stranger.pid))

    def test_a_zombie_is_not_a_survivor(self):
        """A dead process its parent has not reaped still shows in the table: stopping a group must not wait on it or call it a survivor."""
        child = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
        self.addCleanup(child.wait)
        wait_for(lambda: facade.ps_rows([child.pid]).get(child.pid, {}).get("stat", "").startswith("Z"), 10)
        ident = facade.identity_of(child.pid)
        how, _detail = facade.stop_group(ident)
        self.assertEqual(how, "gone")

    def test_a_group_whose_leader_is_gone_is_left_alone_when_its_record_is_old_and_stopped_when_it_is_recent(self):
        leader, member, child = orphaned_group(self, tree=True)
        old = {"pid": leader, "pgid": leader, "started": member["started"], "at": time.time() - 16 * 3600}
        killed = facade.kill_step(None, {"worker": old})
        self.assertEqual((killed["group"], killed["sessions"]), ("unverified", 0), "an old record proves no ownership: nothing below it is collected")
        self.assertTrue(alive(member["pid"]) and alive(child["pid"]), "neither the member nor the session below it was signalled")
        killed = facade.kill_step(None, {"worker": {**old, "at": time.time()}})
        self.assertEqual((killed["group"], killed["sessions"]), ("stopped", 1))
        self.assertTrue(wait_for(lambda: not alive(member["pid"]) and not alive(child["pid"]), 10))

    def test_an_identity_with_no_time_proves_no_ownership_of_a_leaderless_group(self):
        leader, member, _child = orphaned_group(self)
        self.assertEqual(facade.stop_group({"pid": leader, "pgid": leader, "started": member["started"]})[0], "unverified")
        self.assertTrue(alive(member["pid"]))

    def test_this_process_and_its_ancestors_are_never_signalled(self):
        how, _detail = facade.stop_group({"pid": os.getpid(), "pgid": os.getpgrp(), "started": facade.identity_of(os.getpid())["started"]})
        self.assertEqual(how, "protected")


if __name__ == "__main__":
    unittest.main()
