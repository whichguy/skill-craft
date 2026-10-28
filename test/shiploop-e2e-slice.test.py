#!/usr/bin/env python3
"""Step slices (test/shiploop_e2e/slice.py), no model: the seed, the stop, the grade and the packet archive.

A fake host stands in for the model. It is a script that reprints each packet through the real CLI's `next`, moves the
seeded run through the item's inner loop with the navigator's own API (the seed's pattern), commits a product change
at implement, and then keeps running as a model would. The slice stop must end it once the item's inner loop is over,
must not be resumed, and must report an overrun (a host that accepted an outer stage before the poll saw the stop).
The fake commits its change; a model leaves it assembled and uncommitted, which the slice grades the same way.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import clear  # noqa: E402
import flow  # noqa: E402
import metrics  # noqa: E402
import packets  # noqa: E402
import run  # noqa: E402
import sessionlog  # noqa: E402
import slice as step_slice  # noqa: E402
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
import shiploop_item_scope as item_scope  # noqa: E402
import shiploop_knowledge_home as knowledge_home  # noqa: E402
import shiploop_lint as lint  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402

CLI = ROOT / "skills" / "shiploop" / "scripts" / "shiploop"
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
IDENTITY = ["-c", "user.name=Fake host", "-c", "user.email=fake-host@example.invalid"]

# argv: scripts dir, CLI, run dir, mode (normal | overrun | grow). Prints nothing: the harness reads files only.
FAKE_HOST = textwrap.dedent('''
    import json, subprocess, sys, time
    from pathlib import Path
    scripts, cli, run_dir, mode = sys.argv[1:5]
    pause_at = (sys.argv[5] if len(sys.argv) > 5 else "").split(",")  # stages to stay at once, e.g. "implement,test"
    sys.path.insert(0, scripts)
    import shiploop_navigator as nav, shiploop_stage_spec as spec, shiploop_store as store
    run_dir = Path(run_dir)
    memo = run_dir.parent / "fake-paused.txt"  # a fresh session of the fake does not stay where an earlier one did
    paused = set(memo.read_text().split()) if memo.exists() else set()
    worktree = run_dir.parent / "worktree"
    git = ["git", "-C", str(worktree), "-c", "user.name=Fake host", "-c", "user.email=fake-host@example.invalid"]
    extra_outer = 2 if mode == "overrun" else 0
    while True:
        subprocess.run([sys.executable, cli, "next", f"--run-dir={run_dir}"], capture_output=True)  # emit the packet
        state = store.read_record(run_dir / "state.md")
        stage = nav.current_stage(state)
        past = state["status"] != "active" or state["work_index"] > 0 or stage in spec.OUTER
        if past:
            break
        action = nav.current_action(state)["id"]
        if stage in pause_at and action not in paused:
            paused.add(action)
            memo.write_text("\\n".join(sorted(paused)))
            time.sleep(6)  # a model reading the packet: the probe's poll stops it here
            continue
        extra = {}
        if stage == "step-plan":
            extra["test_commands"] = [{"command": "test -f src/feature.js", "suite": "focused"}]
        if stage == "implement":
            (worktree / "src").mkdir(exist_ok=True)
            (worktree / "src" / "feature.js").write_text("module.exports = 1;\\n")
            subprocess.run([*git, "add", "src/feature.js"], check=True, capture_output=True)
            subprocess.run([*git, "commit", "-qm", "feature"], check=True, capture_output=True)
        if stage == "carry-forward" and mode == "grow":
            extra["work_items"] = [{"id": "W2", "title": "A follow-up the review found"}]
        state = nav.apply(state, action, {"outcome": "done", "summary": "Fake host", **extra})
        if state.get("active_improve") is not None:
            state = nav.finish_improve(state, action, {"summary": "Fake review", "lessons": "x"})
        # An overrun accepts the outer stages before anything is saved, so no poll can see the boundary state first
        # (saving each one let a 2 s poll under load stop the host between them, a flaky overrun test).
        while extra_outer and nav.current_stage(state) in spec.OUTER:
            outer = nav.current_action(state)["id"]
            state = nav.apply(state, outer, {"outcome": "done", "summary": "Fake host overrun"})
            if state.get("active_improve") is not None:
                state = nav.finish_improve(state, outer, {"summary": "Fake review", "lessons": "x"})
            extra_outer -= 1
        nav.save(run_dir, state)
        # late-packet: wait past a poll before the next `next` writes the outer stage's packet, so the slice stop lands
        # between the saved state and its packet (the race a loaded machine hits now and then).
        time.sleep(2.5 if mode == "late-packet" and nav.current_stage(state) in spec.OUTER else 0.02)
    time.sleep(120)  # a model would go on to the next packet; only the slice stop ends this
''')

NODE_BASE = ROOT / "test" / "shiploop_e2e" / "fixtures" / "node-base"
CASE = {"prompt": "Add src/feature.js exporting 1.", "work_item": {"id": "W1", "title": "Add src/feature.js"},
        "expect_paths": ["src/feature.js"], "checks": ["test -f src/feature.js"]}


class SliceCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-slice-")
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.work = self.out / "work"
        self.work.mkdir()

    def seed(self, fixture: Path | None = None, item: dict | None = None, **options) -> dict:
        """The seed as slice.py makes it: the case's item and checks, inline."""
        return run.seed_run(CLI, self.work, self.out, CASE["prompt"], "step-plan", fixture=fixture,
                            work_item=item or CASE["work_item"], delegation="inline",
                            **{"checks": CASE["checks"], **options})

    def fake(self, seeded: dict, mode: str, *, pause_at: str = "", clear_at: list[dict] | None = None,
             first: bool = True) -> dict:
        script = self.out / "fake_host.py"
        script.write_text(FAKE_HOST)
        argv = [sys.executable, str(script), str(CLI.parent), str(CLI), seeded["run_dir"], mode, pause_at]
        started = time.time()
        process = step_slice.drive(argv, work=self.work, out=self.out, env=GIT_ENV, run_dir=Path(seeded["run_dir"]),
                                   timeout=90, watch=False, clear_at=clear_at, first=first)
        process["wall"] = time.time() - started
        return process


class SeedTests(SliceCase):
    def test_a_fixture_seed_commits_the_fixture_and_records_the_case_item_inline(self):
        seeded = self.seed(fixture=ROOT / "test/shiploop_e2e/fixtures/node-base")
        self.assertEqual((seeded["stage"], seeded["delegation"]), ("step-plan", "inline"))
        tracked = subprocess.run(["git", "-C", str(self.work), "ls-files"], capture_output=True, text=True).stdout.split()
        self.assertIn("src/paginate.js", tracked)
        state = step_slice.read_state(Path(seeded["run_dir"]))
        self.assertEqual([item["id"] for item in state["work_items"]], ["W1"])
        self.assertEqual(state["work_items"][0]["title"], "Add src/feature.js")
        self.assertFalse(step_slice.slice_complete(state))

    def test_the_default_seed_is_unchanged(self):
        seeded = run.seed_run(CLI, self.work, self.out, CASE["prompt"], "step-plan")
        self.assertEqual(seeded["delegation"], "ask-agent")
        state = step_slice.read_state(Path(seeded["run_dir"]))
        self.assertEqual(state["work_items"][0]["id"], "seeded-request")

    def test_the_seed_records_the_item_base_the_gates_read(self):
        """X-2 / TD-5: a seeded item enters its inner loop with the base snapshot a real run takes (lint.on_transition), so the
        base run, the mutation check, the change inventory and the item commit have what they read. Without it each recorded
        "skipped: no item base was recorded" and did nothing, and every slice baseline covered fewer gates than it claimed."""
        seeded = self.seed(fixture=NODE_BASE)
        run_dir = Path(seeded["run_dir"])
        self.assertEqual(seeded["item_bases"], ["W1"])
        self.assertTrue((run_dir / "lint" / "items" / "W1.md").is_file())
        base = lint.read_base(run_dir, "W1")
        self.assertIsNotNone(base, "lint.read_base answers None for a missing or unavailable record")
        self.assertEqual(base["work_item"], "W1")
        # The input of the item commit and the document stage's change check: known and empty (None is what no base gives).
        self.assertEqual(item_scope.changed_paths(run_dir, "W1"), [])

    def test_the_base_run_gate_runs_on_a_seeded_item_instead_of_skipping(self):
        seeded = self.seed(fixture=NODE_BASE)
        run_dir = Path(seeded["run_dir"])
        state = step_slice.read_state(run_dir)
        action = nav.current_action(state)["id"]
        state = nav.apply(state, action, {"outcome": "done", "summary": "Fake plan.",
                                          "test_commands": [{"command": "test -f src/feature.js", "suite": "focused"}]})
        state = nav.finish_improve(state, action, {"summary": "Fake review."})  # step-plan is an Improve checkpoint
        record, refusal = test_loop._base_run(run_dir, state, "W1", "A1", None)
        self.assertNotIn("skipped", record, record)
        self.assertEqual([(row["command"], row["status"]) for row in record["runs"]], [("test -f src/feature.js", "red")])
        self.assertEqual(refusal, "")

    def test_the_seed_commits_a_neutral_home_the_gates_can_read(self):
        """SP-7a: a test case's requirement must have an entry in HOME/spec.md and a command list is read from
        HOME/environment.md; the seed skipped the stages that write them, so the first test-spec result was refused for a
        requirement no file held and the model wrote the spec itself."""
        seeded = self.seed(fixture=NODE_BASE)
        repo = Path(step_slice.read_state(Path(seeded["run_dir"]))["repo"])
        self.assertEqual(seeded["home"], ["docs/shiploop/spec.md", "docs/shiploop/environment.md"])
        self.assertEqual(list(knowledge_home.entries(repo, "spec.md")), ["R-1"])
        self.assertTrue(knowledge_home.entries(repo, "spec.md")["R-1"].text.startswith("R-1: " + CASE["prompt"]))
        environment = (repo / "docs" / "shiploop" / "environment.md").read_text()
        self.assertIn("## Commands", environment)
        for check in CASE["checks"]:
            self.assertIn(check, environment)
        # Committed in the checkout the run starts from: nothing is dirty, and the item's base already holds them.
        self.assertEqual(subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True,
                                        text=True).stdout, "")
        self.assertEqual(item_scope.changed_paths(Path(seeded["run_dir"]), "W1"), [])

    def test_the_flagged_no_home_seed_commits_no_home_and_still_records_the_base(self):
        seeded = self.seed(fixture=NODE_BASE, home=False)
        repo = Path(step_slice.read_state(Path(seeded["run_dir"]))["repo"])
        self.assertEqual(seeded["home"], [])
        self.assertFalse((repo / "docs" / "shiploop").exists())
        self.assertEqual(seeded["item_bases"], ["W1"])
        self.assertIsNotNone(lint.read_base(Path(seeded["run_dir"]), "W1"))

    def test_a_home_file_the_fixture_holds_is_kept_and_a_case_with_no_checks_says_so(self):
        fixture = self.out / "fixture"
        (fixture / "docs" / "shiploop").mkdir(parents=True)
        (fixture / "docs" / "shiploop" / "spec.md").write_text("R-7: the fixture's own requirement\n")
        (fixture / "README.md").write_text("# x\n")
        seeded = self.seed(fixture=fixture, checks=[])
        repo = Path(step_slice.read_state(Path(seeded["run_dir"]))["repo"])
        self.assertEqual(seeded["home"], ["docs/shiploop/environment.md"])
        self.assertEqual(list(knowledge_home.entries(repo, "spec.md")), ["R-7"])
        self.assertIn("none recorded", (repo / "docs" / "shiploop" / "environment.md").read_text())

    def test_the_no_home_variant_is_a_flag_of_the_slice_and_of_the_seeded_run(self):
        self.assertTrue(step_slice.parser().parse_args(["--case", "node-fix-bug", "--seed-without-home"]).seed_without_home)
        self.assertFalse(step_slice.parser().parse_args(["--case", "node-fix-bug"]).seed_without_home)
        with self.assertRaises(SystemExit) as refused:
            run.main(["--case", "hello", "--seed-without-home", "--quiet"])
        self.assertIn("--seed-without-home needs --seed-at", str(refused.exception))

    def test_every_step_case_names_a_fixture_that_exists(self):
        cases = json.loads((ROOT / "test/shiploop_e2e/step_cases.json").read_text())
        for name, case in cases.items():
            if not name.startswith("_"):
                with self.subTest(name):
                    # A replay case (E6) starts from a saved run's tree, which may hold no package.json (a Salesforce
                    # project, or a zero-dependency Node app) and keeps that run's item ID.
                    fixture = step_slice.FIXTURES / case["fixture"]
                    self.assertTrue(fixture.is_dir() and any(fixture.iterdir()))
                    self.assertRegex(case["work_item"]["id"], r"^W\d+$")
                    self.assertTrue(case["checks"] and case["expect_paths"])


class StopTests(SliceCase):
    def test_the_stop_ends_the_host_after_the_inner_loop_and_the_slice_passes(self):
        seeded = self.seed()
        process = self.fake(seeded, "normal")
        self.assertEqual(process["status"], "slice-complete")
        self.assertLess(process["wall"], 60)  # killed by the poll, not the fake's 120 s sleep or the timeout
        result = step_slice.grade(self.out, Path(seeded["run_dir"]), seeded, CASE, [process])
        self.assertTrue(result["pass"], result)
        self.assertEqual(result["overshoot"], [])
        self.assertEqual(result["item_history"][-1], {"stage": "carry-forward", "outcome": "done"})
        self.assertEqual(result["stage_at_stop"], "system-test-author")

    def test_an_overrun_past_the_stop_fails_no_overshoot(self):
        seeded = self.seed()
        process = self.fake(seeded, "overrun")
        self.assertEqual(process["status"], "slice-complete")
        result = step_slice.grade(self.out, Path(seeded["run_dir"]), seeded, CASE, [process])
        self.assertEqual(result["overshoot"], ["system-test-author", "system-test"])
        self.assertFalse(result["verdicts"]["no_overshoot"])
        self.assertFalse(result["pass"])

    def test_a_carry_forward_that_adds_work_stops_after_the_first_item(self):
        seeded = self.seed()
        process = self.fake(seeded, "grow")
        self.assertEqual(process["status"], "slice-complete")
        result = step_slice.grade(self.out, Path(seeded["run_dir"]), seeded, CASE, [process])
        self.assertEqual(result["queue_growth"], 1)
        self.assertEqual(result["overshoot"], [])
        self.assertTrue(result["verdicts"]["inner_loop"])

    def test_the_archive_and_report_cover_every_packet_the_fake_was_sent(self):
        seeded = self.seed()
        self.fake(seeded, "normal")
        archived = sorted(p.name for p in (self.out / packets.ARCHIVE).iterdir())
        report = packets.write_report(self.out)
        # The fake drives the real CLI, so the run has a trace (shiploop 1.12.0 and later): the report reads each packet as sent
        # from it, and the archive the poll still writes covers only the packets the trace never printed.
        self.assertTrue(report["emissions_source"].startswith("run trace"), report["emissions_source"])
        stages = {row["stage"] for row in report["packets"]}
        inner = {"step-plan", "test-spec", "validate-existing", "implement", "test", "document", "verify", "carry-forward"}
        self.assertTrue(inner <= stages, stages)  # every inner stage printed at least once
        self.assertGreaterEqual(len(archived), len(inner))
        self.assertTrue((self.out / packets.REPORT_MD).is_file())


def load_test_loop_driver():
    """test/shiploop-test-loop.test.py, loaded as a module: its TestLoopTests drive a run through the real `complete`, which the
    hermetic suites for the test stage and for the item commit already rely on (WorktreeItemCommitTests borrows it too)."""
    spec = importlib.util.spec_from_file_location("e2e_slice_test_loop_driver", ROOT / "test" / "shiploop-test-loop.test.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


LOOP = load_test_loop_driver()
# One focused command that exercises the changed line, so the mutation check has mutants to kill; the regression command is the
# test_loop suite's own (`test -f retained.txt`).
# python3 -B and an ignored __pycache__: a bytecode file written while the base and candidate ran would be copied into a mutant's
# checkout beside its changed source and could load instead of it.
CHECK_A = ('echo "Ran 1 test in 0.001s"\n'
           'if python3 -B -c "import a; assert a.x == 3"; then echo OK; else echo "FAILED (failures=1)"; exit 1; fi\n')


class RealCompleteDriver(SliceCase):
    """A seeded run walked through the real `complete` by test/shiploop-test-loop.test.py's driver (no test methods of its own)."""

    state = LOOP.TestLoopTests.state
    action = LOOP.TestLoopTests.action
    packet = LOOP.TestLoopTests.packet
    complete = LOOP.TestLoopTests.complete
    finish_improve = LOOP.TestLoopTests.finish_improve
    drive_to = LOOP.TestLoopTests.drive_to
    terminal = LOOP.TestLoopTests.terminal
    run_loop = LOOP.TestLoopTests.run_loop
    START = LOOP.TestLoopTests.START

    def start_driver(self, seeded: dict, *, base: bool) -> None:
        isolated = mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
        isolated.start()
        self.addCleanup(isolated.stop)
        self.run_dir = Path(seeded["run_dir"])
        self.repo = Path(self.state()["repo"])
        if not base:  # what the seed on main left: no lint/items/W1.md
            (self.run_dir / "lint" / "items" / "W1.md").unlink(missing_ok=True)
        for key, value in (("user.email", "loop@example.invalid"), ("user.name", "Loop Test"), ("commit.gpgsign", "false")):
            subprocess.run(["git", "-C", str(self.repo), "config", key, value], check=True, capture_output=True)

    def gate_records(self) -> list[dict]:
        records = [store.read_record(path) for path in sorted((self.run_dir / "tests").glob("*.md"))]
        return [record for record in records if record.get("schema") in ("shiploop-test-base/v1", "shiploop-test-mutation/v1")]

    def subjects(self) -> list[str]:
        return subprocess.run(["git", "-C", str(self.repo), "log", "--format=%s"], capture_output=True, text=True).stdout.splitlines()


class SeededRunsRunTheGatesTests(RealCompleteDriver):
    """X-2 / TD-5, end to end: a harness-seeded item driven through the real `complete` to carry-forward.

    The base run, the mutation check and the item commit run for real once the seed has recorded the item base; on a run seeded
    the way main did (no base) the same drive records both gates as skipped and commits nothing.
    """

    pass_loop = LOOP.TestLoopTests.pass_loop  # makes both commands pass (fixed.txt, retained.txt) and submits done

    def drive(self, *, base: bool) -> list[dict]:
        (self.work / "a.py").write_text("x = 1\n")
        (self.work / ".gitignore").write_text("__pycache__/\n")
        (self.work / "check.sh").write_text(CHECK_A)
        self.start_driver(run.seed_run(CLI, self.work, self.out, "Make a.x equal 3.", "step-plan",
                                       work_item={"id": "W1", "title": "Make a.x equal 3"}, delegation="inline",
                                       checks=["sh check.sh fixed.txt"]), base=base)
        self.drive_to("carry-forward", each=lambda state: nav.current_stage(state) == "implement"
                      and (self.repo / "a.py").write_text("x = 2 + 1\n"))
        return self.gate_records()

    def test_a_seeded_item_runs_the_base_run_the_mutation_check_and_the_item_commit(self):
        gates = self.drive(base=True)
        self.assertEqual(sorted(record["schema"] for record in gates), ["shiploop-test-base/v1", "shiploop-test-mutation/v1"])
        for record in gates:
            self.assertNotIn("skipped", record, record)
        mutation = next(record for record in gates if record["schema"] == "shiploop-test-mutation/v1")
        self.assertTrue(mutation["mutants"] and mutation["killed"] == len(mutation["mutants"]), mutation)
        # ShipLoop committed the change as the item's one step (build plan S3.2); verify's item commit had nothing left.
        self.assertTrue(self.subjects()[0].startswith("feat(W1/S1): "), self.subjects())
        self.assertEqual(packets.build(self.out)["effectiveness"]["gates"], {"records": 2, "skipped": []})

    def test_the_same_drive_on_a_run_seeded_without_the_base_skips_both_gates_and_commits_nothing(self):
        gates = self.drive(base=False)
        self.assertEqual([record["skipped"] for record in gates],
                         ["no item base was recorded (not a Git checkout, or the base was not captured)"] * 2)
        self.assertEqual(self.subjects(), ["seed: baseline"])
        report = packets.build(self.out)
        self.assertEqual([row["gate"] for row in report["effectiveness"]["gates"]["skipped"]], ["base", "mutation"])
        self.assertIn("**Gates not exercised:** base W1 (no item base was recorded), mutation W1 (no item base was recorded)",
                      packets.render(report))


NODE_REGRESSION_TEST = """
test('TC-1 paginate keeps the partial last page', () => {
  assert.deepEqual(paginate([1, 2, 3, 4, 5], 3, 2), { page: 3, pages: 3, items: [5] });
  assert.deepEqual(paginate([1, 2, 3, 4], 2, 2), { page: 2, pages: 2, items: [3, 4] });
});
"""


@unittest.skipUnless(shutil.which("node"), "the node-base fixture's tests need node")
class SeededCaseFixtureRunsTheGatesTests(RealCompleteDriver):
    """A correct fix of the node-fix-bug case on its own fixture is accepted by the real gates once the seed has recorded the item
    base, so a seeded slice's gates are exercised without refusing a normal run (a refusal would be a fixture to fix, not a gate)."""

    def pass_loop(self):  # the model ran its tests; ShipLoop reruns them itself
        self.run_loop([LOOP.TRIVIAL])
        self.complete(dict(LOOP.DONE, evidence_refs=[str(self.terminal())]))

    def test_the_real_gates_accept_a_correct_fix_of_the_case_on_its_fixture(self):
        case = step_slice.load_step_case("node-fix-bug")
        self.start_driver(run.seed_run(CLI, self.work, self.out, case["prompt"], "step-plan", fixture=step_slice.FIXTURES / case["fixture"],
                                       work_item=case["work_item"], delegation="inline", checks=case["checks"]), base=True)
        plan = {"test_commands": [{"command": "node --test test/paginate.test.js", "suite": "focused", "ids": ["TC-1"], "criteria": ["C1"]},
                                  {"command": "node --test", "suite": "regression"}],
                "paths": ["src/paginate.js", "test/paginate.test.js"],
                "criteria": [{"id": "C1", "text": "paginate keeps the partial last page."}]}

        def fix(state):
            if nav.current_stage(state) == "implement":
                source = self.repo / "src" / "paginate.js"
                source.write_text(source.read_text().replace("Math.floor(items.length / size)", "Math.ceil(items.length / size)"))
                tests = self.repo / "test" / "paginate.test.js"
                tests.write_text(tests.read_text() + NODE_REGRESSION_TEST)

        self.drive_to("carry-forward", step_plan=plan, each=fix)
        base = next(record for record in self.gate_records() if record["schema"] == "shiploop-test-base/v1")
        self.assertNotIn("skipped", base, base)
        # The new test fails on the item's base, as a regression test for the bug must; the suite around it passes.
        self.assertEqual([(row["command"], row["status"]) for row in base["runs"]],
                         [("node --test test/paginate.test.js", "red"), ("node --test", "counted")])
        # ShipLoop committed the change as the item's one step (build plan S3.2); verify's item commit had nothing left.
        self.assertTrue(self.subjects()[0].startswith("feat(W1/S1): "), self.subjects())


class GatesNotExercisedLineTests(SliceCase):
    """X-2 / TD-5: the packet report says which test-stage gates wrote a record that says skipped (fidelity.gates_not_exercised)."""

    def record(self, run_dir: Path, name: str, schema: str, **fields) -> None:
        (run_dir / "tests").mkdir(exist_ok=True)
        record = {"schema": schema, "action": "nav-t", "stage": "test", "work_item": "W1", "passed": True, **fields}
        (run_dir / "tests" / name).write_text("```shiploop-state\n" + json.dumps(record) + "\n```\n")

    def report_line(self) -> tuple[dict, str]:
        report = packets.build(self.out)
        return report["effectiveness"]["gates"], next(line for line in packets.render(report).splitlines()
                                                      if line.lstrip("*").startswith("Gates not exercised"))

    def test_a_run_that_has_not_reached_the_test_stage_says_not_measured_and_never_none(self):
        self.seed()
        gates, line = self.report_line()
        self.assertEqual(gates, {"records": 0, "skipped": []})
        self.assertEqual(line, "Gates not exercised: not measured (no base-run or mutation-check record: the test stage was "
                               "not reached).")

    def test_skipped_records_are_named_and_counted_against_the_records_read(self):
        seeded = self.seed()
        run_dir = Path(seeded["run_dir"])
        none = "no item base was recorded (not a Git checkout, or the base was not captured)"
        self.record(run_dir, "nav-t-base1.md", "shiploop-test-base/v1", skipped=none, disposition="passed", runs=[])
        self.record(run_dir, "nav-t-mutation1.md", "shiploop-test-mutation/v1", mutants=[], killed=2)
        gates, line = self.report_line()
        self.assertEqual([row["gate"] for row in gates["skipped"]], ["base"])
        self.assertEqual(line, "**Gates not exercised:** base W1 (no item base was recorded) (1 of 2 base-run and mutation-check "
                               "records say skipped: the gate wrote a record and did nothing).")

    def test_records_that_ran_say_none_with_their_count(self):
        seeded = self.seed()
        run_dir = Path(seeded["run_dir"])
        self.record(run_dir, "nav-t-base1.md", "shiploop-test-base/v1", disposition="passed", runs=[{"command": "c"}])
        _gates, line = self.report_line()
        self.assertEqual(line, "Gates not exercised: none (1 base-run and mutation-check records, none says skipped).")

    def test_a_run_folder_that_cannot_be_read_is_not_measured_and_the_report_still_renders(self):
        self.assertIsNone(packets.gate_facts(None))
        self.assertEqual(packets.gates_line(None), "Gates not exercised: not measured (the run folder cannot be read).")


class AssembledProductTests(SliceCase):
    """The inner loop assembles an item uncommitted (plan-return commits at release), so a slice grades the candidate."""

    def repo(self) -> tuple[Path, str]:
        repo = self.out / "worktree"
        repo.mkdir()
        (repo / "README.md").write_text("x\n")
        (repo / ".gitignore").write_text("node_modules/\n")
        for args in (["init", "-q"], ["add", "-A"], [*IDENTITY, "commit", "-qm", "seed"]):
            subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=GIT_ENV)
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        return repo, head

    def write(self, repo: Path, path: str, commit: bool = False) -> None:
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_text("change\n")
        if commit:
            for args in (["add", path], [*IDENTITY, "commit", "-qm", f"add {path}"]):
                subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=GIT_ENV)

    def test_only_shiploop_files_is_not_a_product(self):
        repo, head = self.repo()
        self.write(repo, "docs/shiploop/spec.md", commit=True)
        self.write(repo, ".shiploop-improve/nav-1/opening.md")
        found = step_slice.assembled_product(repo, head, ["src/*.js"])
        self.assertFalse(found["pass"])
        self.assertIn("only ShipLoop's own files", found["reason"])

    def test_an_uncommitted_candidate_is_assembled_and_checked(self):
        repo, head = self.repo()
        self.write(repo, "src/a.js")                  # untracked, as the first live slice left its new test
        self.write(repo, "README.md")                 # a tracked file modified in place
        found = step_slice.assembled_product(repo, head, ["src/a.js", "README.md"])
        self.assertTrue(found["pass"], found)
        self.assertEqual(found["committed_since_seed"], [])
        self.assertEqual(found["uncommitted_product"], ["README.md", "src/a.js"])

    def test_the_checks_see_the_candidate_but_not_ignored_files_or_run_evidence(self):
        repo, head = self.repo()
        self.write(repo, "src/a.js")
        self.write(repo, "node_modules/dep/index.js")
        self.write(repo, ".shiploop-improve/nav-1/opening.md")
        checks = step_slice.checks_on_candidate(repo, self.out, [
            "test -f src/a.js", "test ! -e node_modules", "test ! -e .shiploop-improve", "test -f README.md"])
        self.assertEqual([c["pass"] for c in checks], [True, True, True, True])

    def test_a_missing_expected_path_fails(self):
        repo, head = self.repo()
        self.write(repo, "src/a.js", commit=True)
        found = step_slice.assembled_product(repo, head, ["src/a.js", "test/*.test.js"])
        self.assertFalse(found["pass"])
        self.assertIn("test/*.test.js", found["reason"])


class ArchiveTests(SliceCase):
    def test_a_rewritten_packet_is_archived_once_per_distinct_content(self):
        run_dir = self.out / "run"
        (run_dir / "packets").mkdir(parents=True)
        packet = run_dir / "packets" / "nav-1.md"
        for text, added in (("first", 1), ("first", 0), ("second", 1), ("first", 1)):
            packet.write_text(text)
            self.assertEqual(packets.archive_packets(run_dir, self.out), added, text)
        self.assertEqual(len(list((self.out / packets.ARCHIVE / "nav-1").iterdir())), 3)

    def test_overlap_counts_lines_sent_before(self):
        line = "a line long enough to be counted as repeated text"
        self.assertEqual(packets.overlap_shares([line, line + "\n" + line.upper()]), [0.0, 0.5])


def _stream(path: Path, rows: list[dict]) -> None:
    """A Claude-shaped stream. Each row: {"call": command or {tool input}, "tool": name, "result": text or None}.
    A row whose result is None is a call cut off before its result."""
    lines = []
    for n, row in enumerate(rows):
        call = row["call"]
        lines.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"t{n}",
                      "name": row.get("tool", "Bash"), "input": call if isinstance(call, dict) else {"command": call}}]}})
        if row.get("result") is not None:
            lines.append({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{n}",
                                                                    "content": row["result"]}]}})
    path.write_text("".join(json.dumps(x) + "\n" for x in lines))


class ClearMetricTests(unittest.TestCase):
    """clear.redone: only completed state-changing work repeated after the clear counts (SPEC S-6)."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-clear-")
        self.addCleanup(self.temp.cleanup)
        self.events = Path(self.temp.name) / "events.jsonl"

    def redone(self, before: list[dict], after: list[dict]) -> list[dict]:
        _stream(self.events, before)
        clear_line = len(self.events.read_text().splitlines())
        _stream(self.events, before + after)
        return clear.redone(self.events, clear_line)

    WRITE = {"tool": "Write", "call": {"file_path": "/w/src/a.js", "content": "x = 1"}, "result": "ok"}

    def test_a_completed_write_repeated_is_redone_work(self):
        found = self.redone([self.WRITE], [self.WRITE])
        self.assertEqual([f["kind"] for f in found], ["write"])

    def test_an_unfinished_write_repeated_is_not(self):
        self.assertEqual(self.redone([dict(self.WRITE, result=None)], [self.WRITE]), [])

    def test_a_write_with_other_content_is_new_work(self):
        other = {"tool": "Write", "call": {"file_path": "/w/src/a.js", "content": "x = 2"}, "result": "ok"}
        self.assertEqual(self.redone([self.WRITE], [other]), [])

    def test_a_heredoc_write_is_a_write(self):
        heredoc = {"call": "cat > src/a.js <<'EOF'\nx = 1\nEOF\nnpm test", "result": "ok"}
        found = self.redone([heredoc], [heredoc])
        self.assertEqual([f["kind"] for f in found], ["write"])  # the repeated write fails the gate; its test follows a write

    RECORD = {"call": "python3 /p/scripts/shiploop complete --run-dir=/r --action=nav-" + "b" * 32 + " --result=/r/x.md",
              "result": "ShipLoop navigator | test | revision 5"}

    def test_a_test_rerun_after_a_change_is_legitimate_and_without_one_is_redone(self):
        test = {"call": "npm test 2>&1 | tail -3", "result": "pass 9"}
        self.assertEqual(self.redone([test, self.RECORD], [self.WRITE, test]), [])
        self.assertEqual([f["kind"] for f in self.redone([test, self.RECORD], [test])], ["test"])

    def test_a_rerun_of_a_test_whose_result_shiploop_never_recorded_is_verification(self):
        # The 2026-10-11 probe (node-fix-bug, implement:inside, build fbabc74f): one call edited and tested, the kill
        # landed before any callback recorded that result, and the fresh session reran the test to see where it stood.
        # It cannot know a result that only the cleared context saw.
        edit_and_test = {"call": "sed -i '' 's|a|b|' src/paginate.js && npm test 2>&1 | grep -E 'pass|fail'",
                         "result": "pass 9"}
        rerun = {"call": "git diff; node --check src/paginate.js; npm test 2>&1 | grep -E 'pass|fail'",
                 "result": "pass 9"}
        self.assertEqual(self.redone([edit_and_test], [rerun]), [])
        self.assertEqual(self.redone([{"call": "npm test", "result": "pass 9"}], [{"call": "npm test", "result": "ok"}]),
                         [])

    def test_a_script_write_or_a_same_call_write_makes_the_rerun_legitimate(self):
        test = {"call": "npm test 2>&1 | tail -3", "result": "pass 9"}
        python_edit = {"call": "python3 - <<'EOF'\np='t.js';s=open(p).read();open(p,'w').write(s+'x')\nEOF\nnpm test",
                       "result": "pass 10"}
        append_and_test = {"call": "cat >> test/a.test.js <<'EOF'\ntest('x', () => {});\nEOF\nnpm test 2>&1", "result": "ok"}
        self.assertEqual(self.redone([test], [python_edit]), [])
        self.assertEqual(self.redone([test], [append_and_test]), [])

    def test_read_only_orientation_never_counts(self):
        rows = [{"call": "python3 /p/scripts/shiploop next --run-dir /r", "result": "ShipLoop navigator | implement | revision 3"},
                {"call": "cat /r/packets/nav-1.md; git status --short; git diff", "result": "..."}]
        self.assertEqual(self.redone(rows, rows), [])

    def test_a_repeated_callback_for_the_same_action_is_redone(self):
        done = {"call": "python3 /p/scripts/shiploop complete --run-dir=/r --action=nav-" + "a" * 32 + " --result=/r/x.md",
                "result": "ShipLoop navigator | test-green | revision 4"}
        self.assertEqual([f["kind"] for f in self.redone([done], [done])], ["callback"])

    def test_a_redo_is_counted_in_the_window_of_the_clear_it_follows_and_no_other(self):
        def write(name):
            return {"tool": "Write", "call": {"file_path": f"/w/{name}.js", "content": name}, "result": "ok"}
        rows = [write("a"), write("b"), write("a"), write("c")]  # session 3 repeats session 1's write
        _stream(self.events, rows)
        first, second, third = 2, 4, 6                            # each row is a call and its result: the stop lines
        self.assertEqual(clear.redone(self.events, first, second), [])
        self.assertEqual([f["kind"] for f in clear.redone(self.events, second, third)], ["write"])
        self.assertEqual(clear.redone(self.events, third), [])
        # Unbounded (the last clear's window), a repeat after the second clear would also fail the first.
        self.assertEqual([f["kind"] for f in clear.redone(self.events, first)], ["write"])


class ClearTriggerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-clear-trigger-")
        self.addCleanup(self.temp.cleanup)
        self.events = Path(self.temp.name) / "events.jsonl"
        self.state = {"status": "active", "stage": "implement", "action": {"id": "nav-x"}, "revision": 9}

    def stage_of(self, state):
        return state["stage"]

    def test_the_boundary_stops_once_the_stage_is_current_and_inside_waits_for_a_completed_call(self):
        head = {"call": "python3 /p/scripts/shiploop complete --run-dir=/r --action=nav-y", "result":
                "ShipLoop navigator | implement | revision 9"}
        _stream(self.events, [head])
        at = clear.trigger(self.events, self.state, {"stage": "implement", "inside": False}, self.stage_of)
        self.assertEqual((at["stage"], at["action"], at["revision"]), ("implement", "nav-x", 9))
        inside = {"stage": "implement", "inside": True}
        self.assertIsNone(clear.trigger(self.events, self.state, inside, self.stage_of))
        _stream(self.events, [head, {"call": "sed -n 1,5p src/a.js", "result": None}])  # in flight: not yet
        self.assertIsNone(clear.trigger(self.events, self.state, inside, self.stage_of))
        _stream(self.events, [head, {"call": "sed -n 1,5p src/a.js", "result": "..."}])
        self.assertIsNotNone(clear.trigger(self.events, self.state, inside, self.stage_of))
        self.assertIsNone(clear.trigger(self.events, dict(self.state, stage="test-red"), inside, self.stage_of))

    IMPLEMENT_HEAD = {"call": "python3 /p/scripts/shiploop next --run-dir=/r", "result": "ShipLoop navigator | implement | revision 9"}
    IMPROVE_HEAD = {"call": "python3 /p/scripts/shiploop complete --run-dir=/r --action=nav-x",
                    "result": "ShipLoop navigator | improve | revision 10 | the implement result"}
    READ = {"call": "sed -n 1,5p src/a.js", "result": "..."}

    def reviewing(self):
        # The producer's result waits at its Improve stage: the stage is still implement, the Improve child is bound.
        return dict(self.state, active_improve={"action_id": "nav-x", "stage": "implement", "improve_action": "nav-i"})

    def test_an_improve_position_stops_while_the_child_is_bound_and_a_stage_position_does_not(self):
        improve = {"stage": "improve", "inside": False}
        _stream(self.events, [self.IMPROVE_HEAD])
        self.assertIsNone(clear.trigger(self.events, self.state, improve, self.stage_of), "no child, no Improve stage")
        at = clear.trigger(self.events, self.reviewing(), improve, self.stage_of)
        self.assertEqual((at["stage"], at["action"]), ("improve", "nav-i"), "the Improve stage is its own position")
        for inside in (False, True):
            self.assertIsNone(clear.trigger(self.events, self.reviewing(), {"stage": "implement", "inside": inside},
                                            self.stage_of), "the reviewed stage is not current while its review runs")

    def test_inside_an_improve_stage_waits_for_its_packet_and_a_completed_call_that_is_not_shiploops(self):
        inside = {"stage": "improve", "inside": True}
        _stream(self.events, [self.IMPROVE_HEAD])
        self.assertIsNone(clear.trigger(self.events, self.reviewing(), inside, self.stage_of))
        review = {"tool": "Skill", "call": {"skill": "skill-craft:improve"}, "result": None}
        _stream(self.events, [self.IMPROVE_HEAD, review])        # the skill call is in flight
        self.assertIsNone(clear.trigger(self.events, self.reviewing(), inside, self.stage_of))
        _stream(self.events, [self.IMPROVE_HEAD, dict(review, result="Launching skill")])
        self.assertIsNotNone(clear.trigger(self.events, self.reviewing(), inside, self.stage_of))
        ledger = {"call": "python3 /p/scripts/shiploop improve-pass --run-dir=/r --action=nav-i", "result": "ok"}
        _stream(self.events, [self.IMPROVE_HEAD, ledger])
        self.assertIsNone(clear.trigger(self.events, self.reviewing(), inside, self.stage_of), "ShipLoop's own calls never count")

    def test_a_later_clear_counts_only_the_packet_and_calls_that_came_after_the_earlier_stop(self):
        inside = {"stage": "implement", "inside": True}
        _stream(self.events, [self.IMPLEMENT_HEAD, self.READ])
        self.assertIsNotNone(clear.trigger(self.events, self.state, inside, self.stage_of))
        stopped = len(self.events.read_text().splitlines())
        self.assertIsNone(clear.trigger(self.events, self.state, inside, self.stage_of, since=stopped),
                          "the cleared session's packet and call are not the fresh session's")
        _stream(self.events, [self.IMPLEMENT_HEAD, self.READ, self.READ])
        self.assertIsNone(clear.trigger(self.events, self.state, inside, self.stage_of, since=stopped),
                          "a call with no packet shown after the stop")
        _stream(self.events, [self.IMPLEMENT_HEAD, self.READ, self.IMPLEMENT_HEAD])
        self.assertIsNone(clear.trigger(self.events, self.state, inside, self.stage_of, since=stopped), "the packet, no call yet")
        _stream(self.events, [self.IMPLEMENT_HEAD, self.READ, self.IMPLEMENT_HEAD, self.READ])
        self.assertIsNotNone(clear.trigger(self.events, self.state, inside, self.stage_of, since=stopped))

    def test_a_stream_the_harness_cannot_read_stops_at_a_boundary_and_never_inside(self):
        # Grok and Codex events are tool_call / tool_call_update lines, not Claude's message blocks (hosts.CodexTranslator):
        # the calls cannot be read, so an inside position has nothing to wait on. It is accepted, recorded as requested
        # (invocation.json clear_at) and reported unfired; it is not refused, and a boundary is state-based.
        grok = [{"type": "tool_call", "toolCallId": "c1", "toolName": "run_terminal_command",
                 "rawInput": {"command": "sed -n 1,5p src/a.js"}},
                {"type": "tool_call_update", "toolCallId": "c1", "status": "completed",
                 "rawOutput": {"output_for_prompt": "ShipLoop navigator | implement | revision 9"}}]
        self.events.write_text("".join(json.dumps(x) + "\n" for x in grok))
        self.assertIsNotNone(clear.trigger(self.events, self.state, {"stage": "implement", "inside": False}, self.stage_of))
        self.assertIsNone(clear.trigger(self.events, self.state, {"stage": "implement", "inside": True}, self.stage_of))


class ClearProbeTests(SliceCase):
    def test_a_clear_at_the_boundary_records_the_stop_and_a_fresh_session_finishes_the_slice(self):
        seeded = self.seed()
        first = self.fake(seeded, "normal", pause_at="implement", clear_at=[{"stage": "implement", "inside": False}])
        self.assertEqual(first["status"], "cleared")
        records = json.loads((self.out / step_slice.CLEAR_RECORD).read_text())
        self.assertEqual(len(records), 1, "clear.json is a list, one record per clear")
        record = records[0]
        self.assertEqual((record["n"], record["stage"], record["inside"]), (1, "implement", False))
        self.assertEqual(record["stopped"]["stage"], "implement")
        self.assertEqual(record["triggered"]["action"], record["stopped"]["action"])
        second = self.fake(seeded, "normal", first=False)  # the fresh session: the fake reads the packet again
        self.assertEqual(second["status"], "slice-complete")
        result = step_slice.grade(self.out, Path(seeded["run_dir"]), seeded, CASE, [first, second])
        self.assertTrue(result["verdicts"]["no_redo"])  # the fake's stream holds no calls: nothing to redo
        self.assertTrue(result["pass"], result["verdicts"])
        self.assertEqual([c["pass"] for c in result["clear"]], [True])

    def test_each_session_ends_at_the_next_position_not_yet_cleared_and_three_clears_give_three_records(self):
        seeded = self.seed()
        specs = clear.parse_spec(["implement", "test", "verify"])
        statuses, first = [], True
        for _ in range(6):                                   # the loop in slice.main: continue while a clear ended the session
            process = self.fake(seeded, "normal", pause_at="implement,test,verify", clear_at=specs, first=first)
            statuses.append(process["status"])
            first = False
            if process["status"] != "cleared":
                break
        self.assertEqual(statuses, ["cleared", "cleared", "cleared", "slice-complete"])
        records = json.loads((self.out / step_slice.CLEAR_RECORD).read_text())
        self.assertEqual([(r["n"], r["stage"], r["stopped"]["stage"]) for r in records],
                         [(1, "implement", "implement"), (2, "test", "test"), (3, "verify", "verify")])
        lines = [r["stopped"]["events_line"] for r in records]
        self.assertEqual(lines, sorted(lines))


class ClearRecordTests(SliceCase):
    """clear.json is a list; each clear is measured against its own stop, and a clear that never happened is reported."""

    def stream_with_clears(self, rows: list[dict], stops: list[int], asked: list[str] | None = None) -> dict:
        _stream(self.out / "events.jsonl", rows)
        records = [{"n": n, "stage": "implement", "inside": False, "triggered": {}, "stopped": {"stage": "implement",
                    "action": "", "revision": 5, "events_line": line, "last_answered_line": line - 1}}
                   for n, line in enumerate(stops, 1)]
        (self.out / step_slice.CLEAR_RECORD).write_text(json.dumps(records))
        if asked is not None:
            (self.out / "invocation.json").write_text(json.dumps({"clear_at": asked}))
        return self.seed()

    @staticmethod
    def write(name: str) -> dict:
        return {"tool": "Write", "call": {"file_path": f"/w/{name}.js", "content": name}, "result": "ok"}

    def test_a_stream_redoing_a_call_after_the_second_clear_fails_that_clear_only(self):
        seeded = self.stream_with_clears([self.write("a"), self.write("b"), self.write("a"), self.write("c")], [2, 4, 6])
        facts = step_slice.clear_facts(self.out)
        self.assertEqual([f["pass"] for f in facts], [True, False, True])
        self.assertEqual([r["kind"] for r in facts[1]["redone"]], ["write"])
        self.assertEqual([f["n"] for f in facts], [1, 2, 3])
        result = step_slice.grade(self.out, Path(seeded["run_dir"]), seeded, CASE, [{"status": "slice-complete"}])
        self.assertFalse(result["verdicts"]["no_redo"], "one failed clear fails the verdict")
        self.assertEqual([c["pass"] for c in result["clear"]], [True, False, True])

    def test_three_clean_clears_pass_and_a_position_that_never_fired_is_listed_not_hidden(self):
        seeded = self.stream_with_clears([self.write("a"), self.write("b"), self.write("c")], [2, 4, 6],
                                         asked=["implement", "implement:inside", "improve", "verify"])
        result = step_slice.grade(self.out, Path(seeded["run_dir"]), seeded, CASE, [{"status": "slice-complete"}])
        self.assertTrue(result["verdicts"]["no_redo"])
        self.assertEqual(len(result["clear"]), 3)
        self.assertEqual(result["clear_unfired"], ["verify"])

    def test_no_clear_means_no_verdict_and_nothing_unfired_without_a_request(self):
        seeded = self.seed()
        result = step_slice.grade(self.out, Path(seeded["run_dir"]), seeded, CASE, [{"status": "slice-complete"}])
        self.assertNotIn("no_redo", result["verdicts"])
        self.assertEqual((result["clear"], result["clear_unfired"]), ([], []))

    def test_a_record_from_the_one_clear_layout_is_refused_not_read_as_empty(self):
        (self.out / step_slice.CLEAR_RECORD).write_text(json.dumps({"stage": "implement", "inside": False, "stopped": {}}))
        with self.assertRaises(SystemExit) as raised:
            step_slice.clear_facts(self.out)
        self.assertIn("older", str(raised.exception))


class ResumePromptTests(unittest.TestCase):
    CLI = Path("/p/skills/shiploop/scripts/shiploop")

    def test_names_next_is_the_runs_own_resume_prompt_and_told_says_so(self):
        prompt, told = step_slice.continue_prompt("names-next", "/r/run", self.CLI)
        self.assertEqual(prompt, run.resume_prompt("/r/run", self.CLI))
        self.assertEqual(told, {"cli": str(self.CLI), "run_dir": "/r/run"})
        self.assertIn("next --run-dir", prompt)

    def test_withheld_names_no_command_no_path_and_no_stage(self):
        prompt, told = step_slice.continue_prompt("withheld", "/r/run", self.CLI)
        self.assertEqual(prompt, "Continue the ShipLoop work for the repository in this directory.")
        self.assertIsNone(told, "sessions.jsonl records that the prompt named no recovery command")
        for named in ("next", "/r/run", str(self.CLI), "--run-dir", "complete"):
            self.assertNotIn(named, prompt)

    def test_the_command_line_collects_every_position_and_offers_the_two_conditions(self):
        args = step_slice.parser().parse_args(["--case", "x", "--clear-at", "implement:inside", "--clear-at", "test",
                                               "--clear-at", "improve"])
        self.assertEqual(args.clear_at, ["implement:inside", "test", "improve"])
        self.assertEqual(args.resume_prompt, "names-next", "the default is today's prompt")
        self.assertEqual(step_slice.parser().parse_args(["--resume-prompt", "withheld"]).resume_prompt, "withheld")
        self.assertIsNone(step_slice.parser().parse_args([]).clear_at)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            step_slice.parser().parse_args(["--resume-prompt", "hint"])


class ClearSpecTests(unittest.TestCase):
    def test_the_flag_repeats_and_each_position_parses_in_the_order_given(self):
        self.assertEqual(clear.parse_spec(["implement:inside", "test", "improve"]), [
            {"stage": "implement", "inside": True}, {"stage": "test", "inside": False},
            {"stage": "improve", "inside": False}])
        self.assertEqual(clear.parse_spec(["improve:inside"]), [{"stage": "improve", "inside": True}])
        self.assertEqual(clear.parse_spec(None), [])
        self.assertEqual([clear.label(s) for s in clear.parse_spec(["implement:inside", "improve"])],
                         ["implement:inside", "improve"])

    def test_a_malformed_position_is_refused_before_anything_starts(self):
        for text in ("test:outside", ":inside", "", "test:inside:more"):
            with self.subTest(text), self.assertRaises(SystemExit):
                clear.parse_spec([text])


class SeedGapTests(unittest.TestCase):
    def test_a_seed_past_step_plan_with_no_steps_is_refused_before_anything_starts(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "slice"
            with self.assertRaises(SystemExit) as caught:
                step_slice.main(["--case", "node-fix-bug", "--seed-at", "test-spec", "--output", str(out)])
            self.assertFalse(out.exists())
        self.assertIn("no step to build its loop from", str(caught.exception))
        self.assertIn("Nothing was started", str(caught.exception))

    def test_seeds_up_to_step_plan_need_no_steps(self):
        for seed_at in ("test-strategy", "step-plan"):
            with self.subTest(seed_at):
                self.assertEqual(step_slice.seed_gap(seed_at, None), "")

    def test_every_experiment_seeded_past_step_plan_gives_step_plan_steps(self):
        experiments = json.loads((step_slice.HERE / "experiments.json").read_text())
        past = [e for e in experiments.values() if isinstance(e, dict) and e.get("seed_at") == "test-spec"]
        self.assertTrue(past)
        for experiment in past:
            with self.subTest(experiment["case"]):
                records = step_slice.merged_records(step_slice.load_step_case(experiment["case"]), None)
                self.assertEqual(step_slice.seed_gap(experiment["seed_at"], records), "")


FAKE_CLAUDE = textwrap.dedent('''
    import json, os, subprocess, sys, time
    from pathlib import Path
    cfg = json.loads(Path(os.environ["FAKE_SLICE_CONFIG"]).read_text())
    prompt = sys.argv[sys.argv.index("-p") + 1]
    with open(cfg["prompts"], "a") as handle:
        handle.write(json.dumps(prompt) + "\\n")
    sys.path.insert(0, cfg["scripts"])
    import shiploop_navigator as nav, shiploop_stage_spec as spec, shiploop_store as store
    cli, run_dir = cfg["cli"], Path(cfg["run_dir"])
    worktree = run_dir.parent / "worktree"
    git = ["git", "-C", str(worktree), "-c", "user.name=Fake host", "-c", "user.email=fake-host@example.invalid"]
    memo = run_dir.parent / "fake-holds.json"
    held = json.loads(memo.read_text()) if memo.exists() else {}   # how many sessions have already stayed at each place
    here, count = set(), [0]

    def shown(command, output):
        count[0] += 1
        ident = f"f{os.getpid()}-{count[0]}"
        for event in ({"type": "assistant", "message": {"content": [
                          {"type": "tool_use", "id": ident, "name": "Bash", "input": {"command": command}}]}},
                      {"type": "user", "message": {"content": [
                          {"type": "tool_result", "tool_use_id": ident, "content": output}]}}):
            print(json.dumps(event), flush=True)

    def hold(place, sessions):
        # Stay long enough for the harness poll to end this session: once per session, for `sessions` sessions in all.
        if place in here or held.get(place, 0) >= sessions:
            return False
        here.add(place)
        held[place] = held.get(place, 0) + 1
        memo.write_text(json.dumps(held))
        time.sleep(8)
        return True

    while True:
        printed = subprocess.run([sys.executable, cli, "next", f"--run-dir={run_dir}"], capture_output=True, text=True).stdout
        shown(f"python3 {cli} next --run-dir={run_dir}", printed)
        state = store.read_record(run_dir / "state.md")
        stage = nav.current_stage(state)
        if state["status"] != "active" or state["work_index"] > 0 or stage in spec.OUTER:
            break
        child = state.get("active_improve")
        if child is not None:
            if child["stage"] == cfg["improve_of"] and hold("improve:" + child["action_id"], 1):
                continue
            nav.save(run_dir, nav.finish_improve(state, child["action_id"], {"summary": "Fake review", "lessons": "x"}))
            continue
        action = nav.current_action(state)["id"]
        if stage == "implement" and "read" not in here:
            here.add("read")
            shown("sed -n 1,5p src/paginate.js", "module.exports = {};")
        if stage in cfg["holds"] and hold(stage + ":" + action, cfg["holds"].count(stage)):
            continue
        extra = {}
        if stage == "step-plan":
            extra["test_commands"] = [{"command": "test -f src/feature.js", "suite": "focused"}]
        if stage == "implement":
            (worktree / "src").mkdir(exist_ok=True)
            (worktree / "src" / "feature.js").write_text("module.exports = 1;\\n")
            subprocess.run([*git, "add", "src/feature.js"], check=True, capture_output=True)
            subprocess.run([*git, "commit", "-qm", "feature"], check=True, capture_output=True)
        nav.save(run_dir, nav.apply(state, action, {"outcome": "done", "summary": "Fake host", **extra}))
    time.sleep(120)
''')


class ClearThroughMainTests(unittest.TestCase):
    """slice.main with a fake `claude` that prints Claude-shaped events: the positions, the prompt condition and the
    records as the live battery will produce them. The fake stays at a position for one poll; a fresh process of it
    (the next session) continues from the ledger."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-slice-main-")
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name).resolve()
        self.plugin = self.tmp / "plugin"
        (self.plugin / "skills").mkdir(parents=True)
        (self.plugin / "skills" / "shiploop").symlink_to(ROOT / "skills" / "shiploop")
        self.out = self.tmp / "slice"
        self.cli = self.plugin / "skills" / "shiploop" / "scripts" / "shiploop"
        self.run_dir = self.out / ".shiploop-runs" / "seed" / "run"
        self.fake = self.tmp / "claude"
        self.fake.write_text(f"#!{sys.executable}\n{FAKE_CLAUDE}")
        self.fake.chmod(0o755)
        self.prompts = self.tmp / "prompts.jsonl"
        self.handlers = {n: signal.getsignal(n) for n in (signal.SIGTERM, signal.SIGHUP)}  # slice.main takes them over
        self.addCleanup(self.restore_signals)

    def restore_signals(self):
        for number, handler in self.handlers.items():
            signal.signal(number, handler)

    def main(self, holds: list[str], *flags: str, backend: tuple = ("--backend", "anthropic"), ready: str | None = None) -> dict:
        """The fake claude answers the Anthropic route unless ``backend`` names another (a slice's default is Ollama)."""
        config = self.tmp / "config.json"
        config.write_text(json.dumps({"prompts": str(self.prompts), "scripts": str(CLI.parent), "cli": str(CLI),
                                      "run_dir": str(self.run_dir), "holds": holds, "improve_of": "implement"}))
        case = {**CASE, "fixture": "node-base"}
        with mock.patch.dict(os.environ, {"FAKE_SLICE_CONFIG": str(config),
                                          "SHIPLOOP_KEEPALIVE_HOME": str(self.tmp / "keepalive")}), \
                mock.patch.object(step_slice, "load_step_case", return_value=case), \
                mock.patch.object(step_slice.hosts, "ollama_ready", return_value=ready), \
                contextlib.redirect_stdout(io.StringIO()):
            step_slice.main(["--case", "fake", "--host", "claude", *backend, "--claude-bin", str(self.fake),
                             "--plugin-dir", str(self.plugin), "--output", str(self.out), "--timeout", "300", "--quiet",
                             *flags])
        return json.loads((self.out / "slice-result.json").read_text())

    def sent(self) -> list[str]:
        return [json.loads(line) for line in self.prompts.read_text().splitlines()]

    def test_a_slice_with_no_backend_runs_on_ollama_and_is_refused_when_ollama_is_not_ready(self):
        self.main(["implement"], backend=())
        invocation = json.loads((self.out / "invocation.json").read_text())
        self.assertEqual((invocation["backend"], invocation["model"]), ("ollama", step_slice.hosts.OLLAMA_MODEL),
                         "a step slice is an E2E run: it takes run.py's default backend")
        self.out = self.tmp / "out-refused"
        with self.assertRaises(SystemExit) as refused:
            self.main(["implement"], backend=(), ready="the Ollama server does not answer")
        self.assertIn("--backend ollama: the Ollama server does not answer", str(refused.exception))

    def test_three_positions_with_the_prompt_withheld_give_three_records_a_flow_and_the_unfired_one_named(self):
        result = self.main(["implement", "implement"], "--clear-at", "implement", "--clear-at", "implement:inside",
                           "--clear-at", "improve", "--clear-at", "carry-forward:inside", "--resume-prompt", "withheld")
        records = json.loads((self.out / step_slice.CLEAR_RECORD).read_text())
        self.assertEqual([(r["n"], r["stage"], r["inside"], r["stopped"]["stage"]) for r in records],
                         [(1, "implement", False, "implement"), (2, "implement", True, "implement"),
                          (3, "improve", False, "improve")])
        self.assertEqual([s["status"] for s in result["sessions"]], ["cleared", "cleared", "cleared", "slice-complete"])
        self.assertTrue(result["verdicts"]["no_redo"], result["clear"])
        self.assertEqual([c["pass"] for c in result["clear"]], [True, True, True])
        self.assertEqual(result["clear_unfired"], ["carry-forward:inside"])
        # The condition reached the host, three times and never the opening, and the record says nothing was named.
        sent = self.sent()
        self.assertEqual(len(sent), 4)
        self.assertEqual(sent[1:], [step_slice.WITHHELD_PROMPT] * 3)
        self.assertIn("/skill-craft:shiploop", sent[0])
        self.assertEqual([s["told"] for s in sessionlog.read(self.out)][1:], [None, None, None])
        invocation = json.loads((self.out / "invocation.json").read_text())
        self.assertEqual((invocation["clear_at"], invocation["resume_prompt"]),
                         (["implement", "implement:inside", "improve", "carry-forward:inside"], "withheld"))
        flow = json.loads((self.out / "flow.json").read_text())
        self.assertEqual([(c["n"], c["stage"], c["inside"], c["pass"]) for c in flow["clear"]],
                         [(1, "implement", False, True), (2, "implement", True, True), (3, "improve", False, True)])

    def test_the_default_condition_names_next_and_the_record_says_what_it_named(self):
        result = self.main(["implement"], "--clear-at", "implement")
        sent = self.sent()
        self.assertEqual(len(sent), 2)
        self.assertEqual(sent[1], run.resume_prompt(str(self.run_dir), self.cli))
        self.assertEqual(sessionlog.read(self.out)[1]["told"], {"cli": str(self.cli), "run_dir": str(self.run_dir)})
        self.assertEqual(json.loads((self.out / "invocation.json").read_text())["resume_prompt"], "names-next")
        self.assertEqual((len(result["clear"]), result["clear_unfired"]), (1, []))

    def owner_of_the_run(self) -> str | None:
        import shiploop_keepalive as keepalive
        with mock.patch.dict(os.environ, {"SHIPLOOP_KEEPALIVE_HOME": str(self.tmp / "keepalive")}):
            return keepalive._load_owner(str(self.run_dir)).get("owner")

    def claim_for_a_session_that_will_die(self) -> None:
        import shiploop_keepalive as keepalive
        with mock.patch.dict(os.environ, {"SHIPLOOP_KEEPALIVE_HOME": str(self.tmp / "keepalive")}):
            self.assertTrue(keepalive.claim_owner(str(self.run_dir), "claude", "the-cleared-session"))

    def test_a_clear_frees_the_runs_keepalive_owner_as_the_driver_does_between_sessions(self):
        # The cleared session cannot release its own claim; while it held one, the stop hook let the fresh session stop
        # as "another session owns this run" (arm B hook-owed 3, 2026-10-28).
        self.claim_for_a_session_that_will_die()
        self.main(["implement"], "--clear-at", "implement")
        self.assertIsNone(self.owner_of_the_run())

    def test_without_a_clear_the_owner_is_left_to_the_hooks(self):
        self.claim_for_a_session_that_will_die()
        self.main(["implement"])
        self.assertEqual(self.owner_of_the_run(), "claude:the-cleared-session")


VIEWER_STUB = r"""
/* Enough of the browser for flow_viewer.html's script: elements by id, the run section's markup, scrolls recorded. */
function El(id){this.id=id;this.hidden=false;this.innerHTML="";this.textContent="";this.dataset={};this.classList={add(){},remove(){}};}
El.prototype.addEventListener=El.prototype.insertAdjacentHTML=function(){};
El.prototype.querySelector=function(){return null;};El.prototype.querySelectorAll=function(){return [];};
El.prototype.removeAttribute=function(k){delete this[k];};El.prototype.scrollIntoView=function(){SCROLLED.push(this.id);};
var REG={},SCROLLED=[];
var document={addEventListener(){},getElementById(id){
  if(id==="flow-runs")return {textContent:A.runs,hasAttribute(k){return k==="data-home"&&A.home;}};
  if(id==="detail")return /id="detail"/.test((REG.run||{}).innerHTML||"")?new El("detail"):null;
  return REG[id]=REG[id]||new El(id);}};
var location={hash:A.hash,protocol:A.protocol},history={replaceState(){}},window={addEventListener(){}};
"""


def viewer_probe(run: dict, hash_: str, protocol: str, home: bool) -> dict:
    """flow_viewer.html's script run in node against VIEWER_STUB with one run embedded (`home`: as the run's own flow.html
    writes it), opened at `hash_` over `protocol`: the row it opened
    (`data-a` of the row before the detail, None for none), whether it scrolled to the detail, and the header link."""
    node = shutil.which("node")
    if node is None:
        raise unittest.SkipTest("node is not installed")
    script = re.findall(r"<script>([\s\S]*?)</script>", flow.TEMPLATE.read_text())[-1]
    program = ("const vm=require('vm'),fs=require('fs');const A=JSON.parse(fs.readFileSync(process.argv[1],'utf8'));"
               "const ctx=vm.createContext({A,console});vm.runInContext(A.stub,ctx);vm.runInContext(A.script,ctx);"
               "console.log(JSON.stringify(vm.runInContext('[REG.run.innerHTML,REG[\"review-link\"].hidden,'"
               "+'REG[\"review-link\"].href===undefined?null:REG[\"review-link\"].href,SCROLLED]',ctx)));")
    with tempfile.TemporaryDirectory() as tmp:
        arg = Path(tmp) / "arg.json"
        arg.write_text(json.dumps({"stub": VIEWER_STUB, "script": script, "runs": json.dumps([run]), "hash": hash_,
                                   "protocol": protocol, "home": home}))
        done = subprocess.run([node, "-e", program, str(arg)], capture_output=True, text=True, timeout=60)
    if done.returncode != 0:
        raise AssertionError(f"the viewer script failed:\n{done.stderr}")
    markup, hidden, href, scrolled = json.loads(done.stdout.strip().splitlines()[-1])
    before = markup.split('id="detail"')[0] if 'id="detail"' in markup else None
    rows = re.findall(r'data-a="(\d+)"', before) if before is not None else []
    return {"open": int(rows[-1]) if rows else None, "hidden": hidden, "href": href, "scrolled": scrolled}


class FlowTests(SliceCase):
    """flow.py: the sequence the viewer shows, from files only."""

    def claude_stream(self, seeded: dict, rows: list[dict]) -> None:
        """A Claude-shaped event stream: each row is a tool call and its result."""
        lines, stamps = [], []
        for n, row in enumerate(rows):
            lines.append({"type": "assistant", "message": {"content": [
                *([{"type": "text", "text": row["say"]}] if row.get("say") else []),
                {"type": "tool_use", "id": f"t{n}", "name": "Bash", "input": {"command": row["call"]}}]}})
            lines.append({"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": f"t{n}", "content": row.get("result", "")}]}})
        (self.out / "events.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
        (self.out / "timeline.jsonl").write_text("".join(json.dumps({"line": i, "t": 1000.0 + i}) + "\n"
                                                         for i in range(len(lines))))

    def test_events_follow_the_last_head_and_scripts_are_flagged(self):
        seeded = self.seed()
        run_dir = Path(seeded["run_dir"])
        step_plan = seeded["action"]
        head = subprocess.run([sys.executable, str(CLI), "next", f"--run-dir={run_dir}"], capture_output=True,
                              text=True).stdout
        self.claude_stream(seeded, [
            {"call": f"python3 shiploop next --run-dir={run_dir}", "result": head, "say": "Starting the plan."},
            {"call": "cat > /x/cycle.sh <<'XEOF'\ncat > $D/reviews/review-1.md <<EOF\nNo change warranted.\nEOF\n"
                     "printf '%s' '{\"classification\":\"trivial\"}'\nXEOF\n/x/cycle.sh A"},
            {"call": "/x/cycle.sh B", "result": "ShipLoop navigator | test-spec | revision 99\n"
                                                 "Callback: shiploop complete --action=nav-" + "f" * 32},
            {"call": "echo after the head"},
        ])
        found = flow.build(self.out)
        by_action = {a["action"]: a for a in found["actions"]}
        mine = by_action[step_plan]["phases"][0]
        self.assertEqual(found["events_source"], "claude")
        self.assertIn("Starting the plan.", [e["body"]["text"] for e in mine["events"] if e["kind"] == "say"])
        self.assertTrue(mine["head"].startswith("ShipLoop navigator | step-plan"))
        flags = mine["flags"]
        self.assertIn("defines-script:cycle.sh", flags)
        self.assertIn("runs-script:cycle.sh", flags)
        self.assertIn("scripted-review", flags)
        self.assertIn("trivial-pass", flags)
        later = by_action["nav-" + "f" * 32]["phases"][0]  # a head names the next action; the run stopped there
        self.assertFalse(by_action["nav-" + "f" * 32]["accepted"])
        self.assertEqual([e["body"]["text"] for e in later["events"] if e["kind"] == "call"], ["echo after the head"])
        self.assertTrue(all(a["seeded"] for a in found["actions"] if a["stage"] in ("intake", "plan")))

    def test_the_improve_stage_is_an_action_row_of_its_own_and_an_old_layout_run_keeps_its_improve_phase(self):
        seeded = self.seed()
        run_dir = Path(seeded["run_dir"])
        state = store.read_record(run_dir / "state.md")
        spec = next(h["action"] for h in state["history"] if h["stage"] == "spec")
        plan = next(h["action"] for h in state["history"] if h["stage"] == "plan")
        stage_id = "nav-" + "c" * 32
        # New layout: the Improve stage has its own id, recorded at import, and its own packet file. Old layout (plan):
        # the Improve child's packet sits beside the producer's as <action>-improve.md.
        state["improve_results"][spec]["improve_action"] = stage_id
        store.write_record(run_dir / "state.md", state)
        packet_dir = run_dir / "packets"
        packet_dir.mkdir(exist_ok=True)
        improve_head = (f"ShipLoop navigator | improve | revision 4 | the spec result\n1. Run the improve skill on the spec result.\n"
                        f"2. When the improve skill has completed, run: python3 shiploop complete --run-dir={run_dir} --action={stage_id}\n")
        (packet_dir / f"{spec}.md").write_text("ShipLoop navigator | spec | revision 3\nproducer\n")
        (packet_dir / f"{stage_id}.md").write_text(improve_head)
        (packet_dir / f"{stage_id}-bind.md").write_text(improve_head.replace("revision 4", "revision 3"))
        (packet_dir / f"{plan}.md").write_text("ShipLoop navigator | plan | revision 5\nproducer\n")
        (packet_dir / f"{plan}-improve.md").write_text("ShipLoop navigator | plan | revision 6 | Improve\nold child\n")
        self.claude_stream(seeded, [{"call": "shiploop next", "result": improve_head},
                                    {"call": "echo review", "say": "Reviewing the spec."}])
        found = flow.build(self.out)
        rows = found["actions"]
        names = [(r["stage"], r["action"]) for r in rows]
        at = names.index(("improve", stage_id))
        self.assertEqual(names[at - 1], ("spec", spec), "the Improve stage is listed right after the action it reviews")
        row = rows[at]
        self.assertEqual((row["reviewed"], row["reviewed_stage"], row["accepted"]), (spec, "spec", True))
        self.assertEqual([p["kind"] for p in row["phases"]], ["improve"])
        self.assertEqual(row["phases"][0]["packet"]["chars"], len(improve_head))
        self.assertIn("Reviewing the spec.", [e["body"]["text"] for e in row["phases"][0]["events"] if e["kind"] == "say"])
        self.assertEqual([p["kind"] for p in rows[at - 1]["phases"]], ["producer"], "the producer has no Improve phase of its own")
        old = next(r for r in rows if r["action"] == plan)
        self.assertEqual([p["kind"] for p in old["phases"]], ["producer", "improve"])
        self.assertNotIn(("improve", plan), names)
        self.assertEqual(sum(1 for r in rows if r["stage"] == "improve"), 1)
        self.assertEqual(found["flow_version"], 2)
        report = packets.build(self.out)
        by_packet = {r["packet"]: r for r in report["packets"]}
        self.assertEqual((by_packet[stage_id]["kind"], by_packet[stage_id]["stage"], by_packet[stage_id]["reviewed_stage"],
                          by_packet[stage_id]["action"]), ("improve", "improve", "spec", spec))
        self.assertEqual(by_packet[f"{stage_id}-bind"]["action"], spec)
        self.assertEqual((by_packet[f"{plan}-improve"]["kind"], by_packet[f"{plan}-improve"]["action"]), ("improve", plan))
        self.assertEqual(by_packet[spec]["kind"], "producer")

    def test_a_fake_host_run_gives_a_flow_and_a_page_that_cannot_be_closed_by_its_data(self):
        seeded = self.seed()
        self.fake(seeded, "normal")
        found = flow.write(self.out)
        self.assertEqual(found["flow_version"], flow.FLOW_VERSION)
        self.assertEqual(found["actions"][-1]["stage"], "system-test-author")  # the ledger names the stop action
        found["prompt"] = "</script><b>not markup</b>"
        page = flow.bundle(self.out / "two.html", [found, found]).read_text()
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertEqual(page.count("</script>"), 2)  # the data block and the viewer's own script, nothing from the data
        self.assertFalse(flow.bundle(self.out / "a.html", [found], standalone=False).read_text().startswith("<!doctype"))

    def test_the_viewer_opens_an_action_by_its_nav_id_and_links_back_to_the_runs_review_page(self):
        """The Review page links each visit to `flow.html#action=<nav id>`; flow.json records the Review page once it exists,
        and the header links there: relative from the run's own flow.html, by file URL from a bundle opened from disk."""
        seeded = self.seed()
        self.fake(seeded, "normal")
        self.assertIsNone(flow.write(self.out)["review_page"])  # no Review page yet: no link
        (self.out / "review-export").mkdir()
        (self.out / flow.REVIEW_PAGE).write_text("<!doctype html>\n")
        found = flow.write(self.out)
        self.assertEqual(found["review_page"], "review-export/run-review.html")
        self.assertIn('<script id="flow-runs" type="application/json" data-home>', (self.out / "flow.html").read_text())
        wanted = [a for a in found["actions"] if not a["seeded"]][1]
        for protocol in ("file:", "http:"):  # the run's own page, from disk or from a server of the run's folder
            opened = viewer_probe(found, "#action=" + wanted["action"], protocol, True)
            self.assertEqual((opened["open"], opened["scrolled"]), (wanted["index"], ["detail"]))
            self.assertEqual((opened["hidden"], opened["href"]), (False, "review-export/run-review.html"))
        self.assertEqual(viewer_probe(found, "#action=%E0%A4%A", "file:", True)["open"], None)  # bad escaping: the page still opens
        bundled = viewer_probe(found, "#action=nav-" + "0" * 32, "file:", False)
        self.assertEqual((bundled["open"], bundled["scrolled"]), (None, []))  # an unknown action opens nothing
        self.assertEqual(bundled["href"], "file://" + str(self.out.resolve()) + "/review-export/run-review.html")
        published = viewer_probe(found, "#r0-a%d" % wanted["index"], "https:", False)  # the page's own form still opens
        self.assertEqual((published["open"], published["hidden"], published["href"]), (wanted["index"], True, None))

    def test_the_stop_action_is_named_by_the_ledger_when_the_slice_stopped_before_its_packet(self):
        """A slice stop between the host's save and its next `next` leaves the stop action with no packet; the flow
        names its stage from the ledger's current action, not '?'."""
        seeded = self.seed()
        self.fake(seeded, "late-packet")
        state = step_slice.read_state(Path(seeded["run_dir"]))
        stop = step_slice.navigator.current_action(state)["id"]
        self.assertFalse((Path(seeded["run_dir"]) / "packets" / (stop + ".md")).exists())  # the race this pins
        found = flow.write(self.out)
        self.assertEqual((found["actions"][-1]["action"], found["actions"][-1]["stage"]), (stop, "system-test-author"))


if __name__ == "__main__":
    unittest.main()
