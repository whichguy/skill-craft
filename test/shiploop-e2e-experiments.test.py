#!/usr/bin/env python3
"""Template-field experiments (test/shiploop_e2e/experiment.py), no model: the seed and stop points, the overlay applier,
the decision rule and every evaluator's verify.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import itertools
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / "test" / "shiploop_e2e"
sys.path.insert(0, str(E2E))
sys.path.insert(0, str(E2E / "evaluators"))
import experiment  # noqa: E402
import overlay  # noqa: E402
import run  # noqa: E402
import slice as step_slice  # noqa: E402
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
import shiploop_item_scope as item_scope  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_store as store  # noqa: E402

CLI = ROOT / "skills" / "shiploop" / "scripts" / "shiploop"
T_REF = "9ed4ec24"

SG2_POOL = ROOT / "docs" / "experiments" / "sdlc-gates-20261030" / "sg2_pool.py"
_pool_spec = importlib.util.spec_from_file_location("sg2_pool", SG2_POOL)
sg2_pool = importlib.util.module_from_spec(_pool_spec)
_pool_spec.loader.exec_module(sg2_pool)


def _write_invocation(sample: Path, *, host="grok", model="grok-4.7", effort="medium", **fields) -> Path:
    folder = sample / "slice"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "invocation.json"
    path.write_text(json.dumps({"host": host, "model": model, "effort": effort, **fields}))
    return path


def _digest(folder: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(folder.glob("*.py")):
        h.update(path.name.encode() + path.read_bytes())
    return h.hexdigest()


def _next(cli: Path, run_dir: str) -> str:
    done = subprocess.run([sys.executable, str(cli), "next", "--run-dir", run_dir], capture_output=True, text=True)
    packet = sorted((Path(run_dir) / "packets").glob("*.md"), key=lambda p: p.stat().st_mtime)
    return done.stdout + (packet[-1].read_text() if packet else "")


class Seeds(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-exp-")
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)

    def seed(self, stage: str, case: str = "stand-in-parser") -> dict:
        spec = step_slice.load_step_case(case)
        work = self.out / stage / "work"
        work.mkdir(parents=True)
        return run.seed_run(CLI, work, self.out / stage, spec["prompt"], stage, fixture=step_slice.FIXTURES / spec["fixture"],
                            work_item=spec["work_item"], delegation="inline", checks=spec["checks"],
                            records=step_slice.merged_records(spec, None))

    def test_a_seed_at_test_strategy_records_the_prelude_before_it_and_no_item(self):
        seeded = self.seed("test-strategy")
        self.assertEqual(seeded["stage"], "test-strategy")
        self.assertEqual(seeded["skipped"], ["intake", "discovery", "research", "spec"])
        self.assertEqual(seeded["item_bases"], [])

    def test_a_seed_at_test_spec_records_the_cases_step_plan_and_its_packet_lists_the_focused_ids(self):
        seeded = self.seed("test-spec")
        self.assertEqual(seeded["stage"], "test-spec")
        self.assertIn("step-plan", seeded["skipped"])
        self.assertEqual(seeded["item_bases"], ["W1"])
        text = _next(CLI, seeded["run_dir"])
        self.assertIn("TC-4", text)
        self.assertIn("test/records.test.js", text)

    def test_an_arms_seed_records_merge_over_the_cases(self):
        extra = self.out / "extra.json"
        extra.write_text(json.dumps({"step-plan": {"summary": "targets: keeps_state: yes"}}))
        merged = step_slice.merged_records(step_slice.load_step_case("stateful-target"), extra)
        self.assertEqual(merged["step-plan"]["summary"], "targets: keeps_state: yes")
        self.assertIn("test_commands", merged["step-plan"])

    def test_the_stop_after_a_stage_waits_for_its_accepted_result_and_the_cursor_to_move_on(self):
        seeded = self.seed("test-spec")
        run_dir = Path(seeded["run_dir"])
        state = store.read_record(run_dir / "state.md")
        self.assertFalse(step_slice.stop_reached(state, "test-spec"))
        state = nav.apply(state, nav.current_action(state)["id"], {"outcome": "done", "summary": "x"})
        while state.get("active_improve") is not None:
            state = nav.finish_improve(state, nav.current_action(state)["id"], {"summary": "r", "lessons": "x"})
        self.assertTrue(step_slice.stop_reached(state, "test-spec"))
        self.assertFalse(step_slice.stop_reached(state, "test"))
        self.assertEqual(step_slice.overshoot_after(state, "test-spec"), [])
        self.assertEqual(step_slice.overshoot_after(state, "step-plan"), ["test-spec"])

    def test_a_stateful_target_is_preloaded_outside_the_checkout_and_named_in_the_hosts_environment(self):
        env: dict = {}
        found = step_slice.seed_state(step_slice.load_step_case("stateful-target"), self.out, env)
        self.assertEqual(env["LOCAL_TARGET"], str(self.out / "target"))
        self.assertIn("src/pricing.js", found["files"])

    def test_the_gas_case_seeds_at_test_strategy_and_its_packet_points_to_the_apps_script_card(self):
        """AS1 tells the card's effect only if the test-strategy packet reaches the card, and only if nothing in the case
        already says the deployment keeps state (a ceiling: E1 and E3 scored 1.0 in every arm on 2026-10-24)."""
        seeded = self.seed("test-strategy", "gas-deployed-target")
        self.assertEqual((seeded["stage"], seeded["skipped"], seeded["item_bases"]),
                         ("test-strategy", ["intake", "discovery", "research", "spec"], []))
        text = _next(CLI, seeded["run_dir"])
        self.assertIn("Platform testing guide: ", text)
        self.assertIn("platforms/apps-script.md#testing", text)
        spec = step_slice.load_step_case("gas-deployed-target")
        fixture = step_slice.FIXTURES / spec["fixture"]
        given = json.dumps(spec) + "".join(p.read_text() for p in sorted(fixture.rglob("*")) if p.is_file())
        self.assertIsNone(re.search(r"keeps? (its |their )?state|between (commands|runs)|stale|persist", given, re.I))

    def test_a_seed_at_test_lays_an_earlier_slices_implementation_uncommitted_after_the_item_base(self):
        """D4 (docs/shiploop-test-stage-prompt-design-2026-10-30.md §9): a seed at test holds implement fixed. It takes the
        earlier slice's test-spec and implement results without their locators, and implement's change from its last passed
        step proof, so the new run's test stage sees the same cases, hand-off and diff, and only the test stage varies."""
        spec = step_slice.load_step_case("stand-in-parser")
        earlier = {"test-spec": {"summary": "Cases written.", "test_cases": [
            {"id": "TC-4", "criterion": "C3", "requirement": "R-1", "oracle": "parseRecords(7) throws TypeError ORACLE-MARK",
             "red": "absent", "green": "throws"}]}}
        work = self.out / "earlier" / "work"
        work.mkdir(parents=True)
        source = run.seed_run(CLI, work, self.out / "earlier", spec["prompt"], "implement",
                              fixture=step_slice.FIXTURES / spec["fixture"], work_item=spec["work_item"], delegation="inline",
                              checks=spec["checks"], records=step_slice.merged_records(spec, None, earlier))
        run_dir = Path(source["run_dir"])
        state = store.read_record(run_dir / "state.md")
        repo, action = Path(state["repo"]), nav.current_action(state)["id"]
        (repo / "src" / "records.js").write_text("module.exports = {};\n")
        (repo / "src" / "text.js").write_text((repo / "src" / "text.js").read_text() + "// changed by implement\n")
        (repo / "README.md").unlink()
        index = {"GIT_INDEX_FILE": str(self.out / "proof-index")}
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, env={**run.os.environ, **index})
        tree = subprocess.run(["git", "-C", str(repo), "write-tree"], check=True, capture_output=True, text=True,
                              env={**run.os.environ, **index}).stdout.strip()
        (run_dir / "tests").mkdir(exist_ok=True)
        for number, (passed, trees) in enumerate(((True, [tree]), (False, ["0" * 40])), 1):
            (run_dir / "tests" / f"{action}-step-proof{number}.md").write_text(
                store.dumps({"kind": "step-proof", "passed": passed, "trees": trees}, "ShipLoop step proof"))
        state = nav.apply(state, action, {"outcome": "done", "summary": "Built records.js IMPLEMENT-MARK.",
                                          "decisions": ["Kept text.js."], "evidence_refs": [str(run_dir / "notes" / "x.md")],
                                          "learned_from": ["abc1234"]})
        nav.save(run_dir, state, {})

        delivery = step_slice.recorded_delivery(self.out / "earlier")
        self.assertEqual((delivery["action"], delivery["tree"]), (action, tree))
        self.assertEqual(sorted(delivery["files"]), ["src/records.js", "src/text.js"])
        self.assertEqual(delivery["deleted"], ["README.md"])
        self.assertEqual(delivery["records"]["implement"],
                         {"summary": "Built records.js IMPLEMENT-MARK.", "decisions": ["Kept text.js."]})
        self.assertEqual(delivery["records"]["test-spec"]["test_cases"][0]["id"], "TC-4")

        records = step_slice.merged_records(spec, None, delivery["records"])
        self.assertIn("--seed-from", step_slice.seed_gap("test", records, None))
        self.assertIn("--seed-from", step_slice.seed_gap("test-spec", records, self.out / "earlier"))
        self.assertEqual(step_slice.seed_gap("test", records, self.out / "earlier"), "")
        work = self.out / "test" / "work"
        work.mkdir(parents=True)
        seeded = run.seed_run(CLI, work, self.out / "test", spec["prompt"], "test", fixture=step_slice.FIXTURES / spec["fixture"],
                              work_item=spec["work_item"], delegation="inline", checks=spec["checks"], records=records,
                              implementation=delivery)
        new_run = Path(seeded["run_dir"])
        self.assertEqual((seeded["stage"], seeded["skipped"][-2:]), ("test", ["validate-existing", "implement"]))
        self.assertEqual(nav.current_stage(store.read_record(new_run / "state.md")), "test")
        new_repo = Path(store.read_record(new_run / "state.md")["repo"])
        status = subprocess.run(["git", "-C", str(new_repo), "status", "--porcelain"], capture_output=True, text=True,
                                check=True).stdout
        self.assertEqual(sorted(status.splitlines()), [" D README.md", " M src/text.js", "?? src/records.js"])
        self.assertEqual(sorted(item_scope.changed_paths(new_run, "W1")), ["README.md", "src/records.js", "src/text.js"])
        text = _next(CLI, seeded["run_dir"])
        self.assertIn("IMPLEMENT-MARK", text)
        self.assertIn("ORACLE-MARK", text)
        self.assertIn("implementation is in the run's worktree", run.seed_prompt(CLI, str(new_run), "p", "inline", "test"))

    def test_the_slice_command_line_takes_the_experiment_flags(self):
        args = step_slice.parser().parse_args(["--case", "stand-in-parser", "--seed-at", "test-spec", "--stop-after", "test",
                                               "--ref", "HEAD", "--overlay", "x.json", "--opening-note", "n.txt"])
        self.assertEqual((args.seed_at, args.stop_after, args.ref), ("test-spec", "test", "HEAD"))
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            step_slice.parser().parse_args(["--case", "x", "--seed-at", "plan"])


class Overlays(unittest.TestCase):
    OVERLAY = {"edits": [{"module": "shiploop_prompts.py", "constant": "DUTIES", "key": "test-spec",
                          "old": "Write no test code in this stage.", "new": "Write no test code in this stage. OVERLAY-MARK-7."}]}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-overlay-")
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name)

    def test_an_overlay_changes_the_rendered_packet_of_a_build_copy_and_leaves_the_source_untouched(self):
        source = ROOT / "skills" / "shiploop" / "scripts"
        before = _digest(source)
        plugin = self.tmp / "plugin"
        shutil.copytree(ROOT / "skills" / "shiploop", plugin / "skills" / "shiploop",
                        ignore=shutil.ignore_patterns("__pycache__"))
        path = self.tmp / "o.json"
        path.write_text(json.dumps(self.OVERLAY))
        applied = overlay.apply_to_plugin(path, plugin)
        self.assertEqual([m["module"] for m in applied["modules"]], ["shiploop_prompts.py"])
        spec = step_slice.load_step_case("stand-in-parser")
        work = self.tmp / "work"
        work.mkdir()
        cli = plugin / "skills" / "shiploop" / "scripts" / "shiploop"
        seeded = run.seed_run(cli, work, self.tmp, spec["prompt"], "test-spec", fixture=step_slice.FIXTURES / spec["fixture"],
                              work_item=spec["work_item"], delegation="inline", checks=spec["checks"],
                              records=spec["seed_records"])
        self.assertIn("OVERLAY-MARK-7", _next(cli, seeded["run_dir"]))
        self.assertEqual(_digest(source), before)
        self.assertNotIn("OVERLAY-MARK-7", (source / "shiploop_prompts.py").read_text())

    def test_the_source_checkout_is_refused(self):
        with self.assertRaises(overlay.OverlayError):
            overlay.apply(self.OVERLAY, ROOT / "skills" / "shiploop" / "scripts")

    def test_text_that_is_not_in_the_named_entry_is_refused_before_anything_is_written(self):
        copy = self.tmp / "scripts"
        shutil.copytree(ROOT / "skills" / "shiploop" / "scripts", copy, ignore=shutil.ignore_patterns("__pycache__"))
        before = _digest(copy)
        bad = {"edits": [self.OVERLAY["edits"][0],
                         {"module": "shiploop_prompts.py", "constant": "DUTIES", "key": "plan",
                          "old": "Write no test code in this stage.", "new": "x"}]}
        with self.assertRaises(overlay.OverlayError):
            overlay.apply(bad, copy)
        self.assertEqual(_digest(copy), before)

    def test_every_committed_overlay_applies_to_the_ref_its_arm_names(self):
        for exp_id, exp in experiment.load().items():
            for name, arm in exp["arms"].items():
                if not arm.get("overlay"):
                    continue
                with self.subTest(exp=exp_id, arm=name):
                    if subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "-q", arm["ref"] + "^{commit}"],
                                      capture_output=True).returncode:
                        self.skipTest(f"{arm['ref']} is not in this clone")
                    self.assertEqual(experiment._overlay_problems(overlay, E2E / arm["overlay"], arm["ref"]), [])


class Decide(unittest.TestCase):
    @staticmethod
    def rows(values, gate=None):
        return [{"sample": n, "value": v, **({"defect_caught": gate[n - 1]} if gate else {})}
                for n, v in enumerate(values, 1)]

    def test_better_with_a_permutation_p_below_significance_supports(self):
        # Five against five: 6 of the 252 splits put all five ones in the second group, p = 6/252.
        found = experiment.judge(self.rows([0, 0, 0, 0, 1]), self.rows([1, 1, 1, 1, 1]))
        self.assertEqual(found["verdict"], "supports")
        self.assertAlmostEqual(found["p"], 6 / 252)
        self.assertNotIn("spread", found)

    def test_no_better_contradicts(self):
        self.assertEqual(experiment.judge(self.rows([1, 0, 1, 0, 1]), self.rows([0, 1, 0, 0, 1]))["verdict"], "contradicts")

    def test_better_within_noise_is_inconclusive_and_says_the_p(self):
        found = experiment.judge(self.rows([1, 1, 0, 0, 0]), self.rows([1, 0, 1, 0, 1]))
        self.assertEqual(found["verdict"], "inconclusive")
        self.assertGreaterEqual(found["p"], experiment.SIGNIFICANCE)
        self.assertIn(f"p {found['p']:.2g}", found["reason"])

    def test_a_gap_the_old_spread_read_as_supports_is_inconclusive_by_the_permutation_p(self):
        # E7-F D (6aa1f024): +0.02 on a discrete metric whose 2-against-2 spread was exactly 0.00 read "supports" at p 0.50.
        found = experiment.judge(self.rows([0.5, 0.5, 0.5, 0.5, 0.75, 0.75, 0.5, 0.5]),
                                 self.rows([0.5, 0.5, 0.5, 0.5, 0.75, 0.75, 0.5, 0.75]))
        self.assertEqual(found["verdict"], "inconclusive")
        self.assertGreater(found["p"], 0.2)

    def test_two_samples_each_cannot_reach_significance_and_no_sample_number_is_required(self):
        found = experiment.judge(self.rows([0, 0]), self.rows([1, 1]))
        self.assertEqual(found["verdict"], "inconclusive")
        self.assertAlmostEqual(found["p"], 1 / 6)
        # Any samples count, whatever their numbers: three against three bottoms out at 0.05, which is not below it.
        found = experiment.judge([{"sample": n, "value": 0} for n in (2, 5, 7)], [{"sample": n, "value": 1} for n in (1, 2, 3)])
        self.assertEqual((found["verdict"], found["p"]), ("inconclusive", 1 / 20))

    def test_a_perfect_split_of_four_against_four_supports_at_one_in_seventy(self):
        found = experiment.judge(self.rows([0.25, 0.5, 0.25, 0.25]), self.rows([0.75, 1, 0.75, 0.75]))
        self.assertEqual((found["verdict"], found["p"]), ("supports", 1 / 70))

    def test_the_permutation_p_is_the_exact_share_of_splits_at_least_as_good(self):
        rng = random.Random(5)
        for _ in range(40):
            nx, ny = rng.randint(1, 5), rng.randint(1, 5)
            control = [rng.choice((0, 0.25, 0.5, 2 / 3, 1)) for _ in range(nx)]
            candidate = [rng.choice((0, 0.25, 0.5, 2 / 3, 1)) for _ in range(ny)]
            pooled = control + candidate
            observed = sum(candidate) / ny - sum(control) / nx
            splits = list(itertools.combinations(range(nx + ny), nx))
            hits = sum(sum(pooled[i] for i in range(nx + ny) if i not in s) / ny - sum(pooled[i] for i in s) / nx
                       >= observed - 1e-12 for s in splits)
            self.assertAlmostEqual(experiment.permutation_p(control, candidate), hits / len(splits), msg=(control, candidate))

    def test_every_sample_at_one_is_a_ceiling_even_below_four_samples(self):
        for n in (3, 4):
            found = experiment.judge(self.rows([1] * n), self.rows([1] * n))
            self.assertEqual(found["verdict"], "ceiling", n)
            self.assertNotIn("samples 1-4", found["reason"])

    def test_every_sample_at_zero_is_a_floor(self):
        self.assertEqual(experiment.judge(self.rows([0, 0, 0]), self.rows([0, 0, 0, 0]))["verdict"], "floor")

    def test_a_tie_inside_the_bounds_is_no_better(self):
        found = experiment.judge(self.rows([0.5] * 4), self.rows([0.5] * 4))
        self.assertEqual(found["verdict"], "contradicts")
        self.assertIn("no better", found["reason"])

    def test_too_few_samples_for_any_split_to_reach_significance_decide_nothing_either_way(self):
        # 3 against 3 bottoms out at p = 0.05 and 2 against 4 at 1/15: no verdict, not even "no better" (E2's n=2 records).
        for x, y in (([0.5] * 3, [0.5] * 3), ([1, 0.5], [0.5, 0.25]), ([0.5, 0.75], [0.25, 0.25, 0.25, 0.25])):
            found = experiment.judge(self.rows(x), self.rows(y))
            self.assertEqual(found["verdict"], "inconclusive", (x, y))
            self.assertIn("no verdict is possible", found["reason"])

    def test_one_arm_at_the_bound_is_not_a_ceiling(self):
        self.assertNotEqual(experiment.judge(self.rows([1, 1, 1, 1]), self.rows([1, 1, 0.75, 1]))["verdict"], "ceiling")

    def test_fractional_values_decide_on_the_permutation_p(self):
        found = experiment.judge(self.rows([0.25, 0.25, 0.25, 0.5]), self.rows([1, 0.75, 1, 1]))
        self.assertEqual((found["verdict"], found["p"]), ("supports", 1 / 70))

    def test_every_experiment_runs_four_samples_and_pins_each_arm_to_a_commit(self):
        # A descriptive experiment measures and reports (R3: owner, "3 full slices each"); 3 per arm cannot reach p < 0.05.
        for exp_id, exp in experiment.load().items():
            with self.subTest(exp=exp_id):
                self.assertEqual(exp["samples"], 3 if exp.get("descriptive") else 4)
                for name, arm in exp["arms"].items():
                    self.assertRegex(arm["ref"], r"^[0-9a-f]{8,40}$", f"{exp_id}/{name}")

    def test_a_lower_gate_rate_contradicts_whatever_the_score(self):
        found = experiment.judge(self.rows([0, 0, 0, 0], [True] * 4), self.rows([1, 1, 1, 1], [True, False, True, True]),
                                 "defect_caught")
        self.assertEqual(found["verdict"], "contradicts")

    def test_decide_writes_the_record_and_one_journal_line_for_any_two_arms(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for arm, values in (("T", [0, 0, 0, 0, 0]), ("B", [1, 1, 1, 0, 1])):
                for n, v in enumerate(values, 1):
                    _write_invocation(out / "E1" / arm / str(n))
                    (out / "E1" / arm / str(n) / "score.json").write_text(json.dumps({"sample": n, "value": v}))
            journal = out / "journal.md"
            report = experiment.decide("E1", "T", "B", out, journal)
            self.assertEqual(report["verdict"], "supports")
            self.assertEqual(json.loads((out / "E1" / "decision.json").read_text())["verdict"], "supports")
            self.assertTrue((out / "E1" / "decision-T-B.json").is_file())
            lines = [line for line in journal.read_text().splitlines() if line.startswith("| 2")]
            self.assertEqual(len(lines), 1)
            self.assertIn("e1-stand-in.json", lines[0])

    def test_check_single_commit_ignores_missing_commits_and_catches_a_real_mismatch(self):
        experiment._check_single_commit([{"commit": None}, {"commit": "abc"}], "E1", "T")
        experiment._check_single_commit([{"commit": "abc"}, {"commit": "abc"}], "E1", "T")
        with self.assertRaises(SystemExit):
            experiment._check_single_commit([{"commit": "abc"}, {"commit": "def"}], "E1", "T")

    def test_decide_refuses_a_ref_that_moved_mid_round(self):
        """A branch ref (e.g. T) resolved to two different commits across samples must not be averaged together."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for n in range(1, 6):
                _write_invocation(out / "E1" / "A" / str(n))
                (out / "E1" / "A" / str(n) / "score.json").write_text(
                    json.dumps({"sample": n, "value": 0, "commit": "fixed-commit"}))
            moved = {"1": "9ed4ec24f8481a1841820033a35d31804ebb9dab", "2": "9ed4ec24f8481a1841820033a35d31804ebb9dab",
                     "3": "d21c770e5c71888069f239c7e2156b22ae515b61"}
            for n, commit in moved.items():
                _write_invocation(out / "E1" / "T" / n)
                (out / "E1" / "T" / n / "score.json").write_text(json.dumps({"sample": int(n), "value": 1, "commit": commit}))
            with self.assertRaisesRegex(SystemExit, "different commits"):
                experiment.decide("E1", "A", "T", out)
            self.assertFalse((out / "E1" / "decision.json").exists(), "a refused decide must not write a decision file")

    def test_run_records_the_arms_resolved_commit_in_command_json(self):
        commit = experiment._resolved_commit("HEAD")
        self.assertRegex(commit, r"^[0-9a-f]{40}$")
        self.assertIsNone(experiment._resolved_commit(None))


class PooledSg2(unittest.TestCase):
    """SG2 read as one experiment of four cases (docs/experiments/sdlc-gates-20261030/sg2_pool.py; owner, 2026-10-31):
    at 4 binary samples per arm one case reaches p < 0.05 only as 4 against 0, so the four cases are blocks of one test."""

    @staticmethod
    def rows(values):
        return [{"sample": n, "value": v} for n, v in enumerate(values, 1)]

    def pool(self, a, b, n=4):
        """Four cases where arm A catches a[i] of n samples in case i and arm B b[i]."""
        return {f"SG2-K{i}": (self.rows([1] * x + [0] * (n - x)), self.rows([1] * y + [0] * (n - y)))
                for i, (x, y) in enumerate(zip(a, b), 1)}

    def test_the_pooled_p_is_the_exact_share_of_within_case_permutations(self):
        rng = random.Random(11)
        for _ in range(25):
            nx, ny = rng.randint(1, 3), rng.randint(1, 3)
            blocks = [([rng.choice((0, 0.25, 0.5, 0.75, 1)) for _ in range(nx)],
                       [rng.choice((0, 0.25, 0.5, 0.75, 1)) for _ in range(ny)]) for _ in range(rng.randint(1, 3))]
            pooled = [[Fraction(v) for v in control + candidate] for control, candidate in blocks]
            observed = sum(sum(Fraction(v) for v in candidate) for _, candidate in blocks)
            splits = [list(itertools.combinations(range(nx + ny), ny)) for _ in blocks]
            total = hits = 0
            for choice in itertools.product(*splits):
                total += 1
                hits += sum(sum(block[i] for i in picked) for block, picked in zip(pooled, choice)) >= observed
            self.assertAlmostEqual(sg2_pool.pooled_p(blocks), hits / total, msg=blocks)

    def test_one_case_is_the_harnesss_own_permutation_test(self):
        for control, candidate in (([0, 0, 0, 0], [1, 1, 1, 1]), ([1, 0, 0, 0], [1, 1, 1, 1]), ([0.5, 0.25, 0.5, 0.5], [1, 0.75, 1, 1])):
            self.assertAlmostEqual(sg2_pool.pooled_p([(control, candidate)]), experiment.permutation_p(control, candidate))

    def test_four_cases_that_each_read_inconclusive_alone_support_the_pool(self):
        # B catches 3 of 4 where A catches 1 of 4, in every case: 1 against 3 gives one case p 0.243.
        found = sg2_pool.judge_pool(self.pool((1, 1, 1, 1), (3, 3, 3, 3)))
        self.assertEqual(found["verdict"], "supports")
        self.assertLess(found["p"], experiment.SIGNIFICANCE)
        self.assertEqual([case["verdict"] for case in found["cases"]], ["inconclusive"] * 4)
        self.assertEqual((found["n"], found["difference"]), ([16, 16], 0.5))
        self.assertIn("pooled over 4 cases of 4 against 4", found["reason"])

    def test_the_thresholds_the_guide_states_for_evenly_spread_catches(self):
        # A catches a of 16, spread evenly over the cases: the fewest catches by B, also spread evenly, that support.
        needed = {0: 5, 1: 6, 2: 8, 3: 9, 4: 10, 5: 11, 6: 12, 7: 13, 8: 14}

        def spread(total):
            return tuple(total // 4 + (1 if i < total % 4 else 0) for i in range(4))
        for a, b in needed.items():
            self.assertEqual(sg2_pool.judge_pool(self.pool(spread(a), spread(b)))["verdict"], "supports", (a, b))
            self.assertEqual(sg2_pool.judge_pool(self.pool(spread(a), spread(b - 1)))["verdict"], "inconclusive", (a, b - 1))

    def test_no_better_contradicts_and_a_gain_within_noise_is_inconclusive(self):
        self.assertEqual(sg2_pool.judge_pool(self.pool((3, 3, 3, 3), (2, 2, 2, 2)))["verdict"], "contradicts")
        self.assertEqual(sg2_pool.judge_pool(self.pool((2, 2, 2, 2), (2, 2, 2, 2)))["verdict"], "contradicts")
        found = sg2_pool.judge_pool(self.pool((2, 2, 2, 2), (3, 3, 3, 2)))
        self.assertEqual(found["verdict"], "inconclusive")
        self.assertGreaterEqual(found["p"], experiment.SIGNIFICANCE)
        self.assertIn(f"p {found['p']:.2g}", found["reason"])

    def test_every_sample_at_a_bound_is_a_ceiling_or_a_floor_for_the_whole_pool(self):
        self.assertEqual(sg2_pool.judge_pool(self.pool((4, 4, 4, 4), (4, 4, 4, 4)))["verdict"], "ceiling")
        self.assertEqual(sg2_pool.judge_pool(self.pool((0, 0, 0, 0), (0, 0, 0, 0)))["verdict"], "floor")
        # One case at the ceiling in both arms adds nothing and does not stop the others from deciding.
        self.assertEqual(sg2_pool.judge_pool(self.pool((4, 0, 0, 0), (4, 4, 4, 3)))["verdict"], "supports")

    def test_a_pool_with_unequal_sample_counts_is_refused_not_guessed(self):
        short = self.pool((0, 0, 0, 0), (4, 4, 4, 4))
        short["SG2-K3"] = (short["SG2-K3"][0], short["SG2-K3"][1][:3])
        with self.assertRaisesRegex(SystemExit, r"SG2-K3 4/3"):
            sg2_pool.judge_pool(short)
        with self.assertRaisesRegex(SystemExit, "same number of scored samples"):
            sg2_pool.judge_pool({name: ([], []) for name in self.pool((0,) * 4, (0,) * 4)})

    def test_a_missing_value_is_not_a_sample(self):
        full = self.pool((0, 0, 0, 0), (4, 4, 4, 4))
        full["SG2-K2"] = (full["SG2-K2"][0], full["SG2-K2"][1] + [{"sample": 5, "value": None}])
        self.assertEqual(sg2_pool.judge_pool(full)["verdict"], "supports")

    def _write(self, out, a, b):
        for number, (exp_id, (rows_a, rows_b)) in enumerate(self.pool(a, b).items(), 1):
            for arm, rows in (("A", rows_a), ("B", rows_b)):
                for row in rows:
                    folder = out / exp_id / arm / str(row["sample"])
                    folder.mkdir(parents=True)
                    (folder / "score.json").write_text(json.dumps(row))

    def test_decide_pool_writes_the_record_and_one_journal_line_and_changes_no_experiment(self):
        before = (E2E / "experiments.json").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            out, journal = Path(tmp) / "out", Path(tmp) / "journal.md"
            self._write(out, (1, 1, 1, 1), (3, 3, 3, 3))
            report = sg2_pool.decide_pool(out, "A", "B", journal)
            self.assertEqual((report["experiment"], report["verdict"]), ("SG2", "supports"))
            self.assertEqual(report["members"], ["SG2-K1", "SG2-K2", "SG2-K3", "SG2-K4"])
            self.assertEqual(json.loads((out / "SG2" / "decision.json").read_text())["verdict"], "supports")
            self.assertTrue((out / "SG2" / "decision-A-B.json").is_file())
            lines = [line for line in journal.read_text().splitlines() if line.startswith("| 2")]
            self.assertEqual(len(lines), 1)
            self.assertIn("| SG2 |", lines[0])
            self.assertIn("**supports**", lines[0])
            self.assertIn("+ask-agent", lines[0])
            self.assertIn("16/16", lines[0])
            dry_journal = Path(tmp) / "dry.md"
            sg2_pool.decide_pool(out, "A", "B", dry_journal, record=False)
            self.assertFalse(dry_journal.exists())
        self.assertEqual((E2E / "experiments.json").read_bytes(), before)

    def test_decide_pool_refuses_a_case_the_queue_stopped_early(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self._write(out, (1, 1, 1, 1), (3, 3, 3, 3))
            for arm in ("A", "B"):
                for n in (3, 4):
                    shutil.rmtree(out / "SG2-K2" / arm / str(n))
            with self.assertRaisesRegex(SystemExit, "SG2-K2 2/2"):
                sg2_pool.decide_pool(out, "A", "B", out / "journal.md")
            self.assertFalse((out / "SG2" / "decision.json").exists())

    def test_decide_pool_refuses_samples_built_from_different_commits(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self._write(out, (1, 1, 1, 1), (3, 3, 3, 3))
            for exp_id, commit in (("SG2-K1", "a" * 40), ("SG2-K2", "b" * 40)):
                for n in range(1, 5):
                    path = out / exp_id / "B" / str(n) / "score.json"
                    path.write_text(json.dumps({**json.loads(path.read_text()), "commit": commit}))
            with self.assertRaisesRegex(SystemExit, "different commits"):
                sg2_pool.decide_pool(out, "A", "B", out / "journal.md")

    def test_the_pool_is_the_four_sg2_cases_on_one_build_and_the_reader_stays_out_of_the_digest(self):
        self.assertEqual(sg2_pool.members(), [f"SG2-K{n}" for n in range(1, 5)])
        self.assertEqual({json.dumps(experiment.load(i)["arms"]["B"], sort_keys=True) for i in sg2_pool.members()}.__len__(), 1)
        self.assertFalse(str(SG2_POOL.resolve()).startswith(str(E2E.resolve())), "the reader sits in docs/, outside the digest")
        guide = (SG2_POOL.parent / "README.md").read_text()
        section = guide[guide.index("## SG2"):]
        self.assertIn("--no-early-stop", section)
        self.assertIn("sg2_pool.py", section)


class RunOneSample(unittest.TestCase):
    def test_sample_n_runs_exactly_that_sample_and_samples_n_runs_one_to_n(self):
        from unittest import mock  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            calls = []

            def fake(argv, *a, **k):
                calls.append(Path(argv[argv.index("--output") + 1]).parent.name)
                return subprocess.CompletedProcess(argv, 0)

            with mock.patch.object(experiment.subprocess, "run", fake), \
                    mock.patch.object(experiment, "_resolved_commit", lambda ref: "c" * 40), \
                    contextlib.redirect_stdout(io.StringIO()):
                experiment.main(["run", "E1b", "--arm", "B", "--sample", "3", "--out", str(out)])
                self.assertEqual(calls, ["3"])
                self.assertEqual([p.name for p in (out / "E1b" / "B").iterdir()], ["3"])
                experiment.main(["run", "E1b", "--arm", "A", "--out", str(out)])
                self.assertEqual(calls[1:], ["1", "2", "3", "4"])
                with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                    experiment.main(["run", "E1b", "--arm", "A", "--sample", "1", "--samples", "2", "--out", str(out)])


class LaunchProfiles(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="shiploop-experiment-profile-")
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name)
        exp = {"arms": {"A": {}, "B": {}}, "case": "fake", "seed_at": "step-plan", "claim": "fake"}
        loaded = mock.patch.object(experiment, "load", return_value=exp)
        loaded.start()
        self.addCleanup(loaded.stop)

    def _sample(self, arm, *, model="gpt-6.1-terra", effort="xhigh", finished=True, n=1):
        sample = self.out / "Q" / arm / str(n)
        folder = _write_invocation(sample, host="codex", model=model, effort=effort, backend=None).parent
        if finished:
            (folder / "slice-result.json").write_text('{"pass": true}')
        return sample

    def test_run_refuses_the_new_default_for_an_old_round_but_honors_its_explicit_profile(self):
        retained = self._sample("A")
        invocation = retained / "slice" / "invocation.json"
        before = invocation.read_bytes()

        def complete(argv):
            self.assertIn("--model=gpt-6.1-terra", argv)
            self.assertIn("--effort=xhigh", argv)
            self._sample("B")
            return subprocess.CompletedProcess(argv, 0)

        with mock.patch.object(experiment.subprocess, "run", side_effect=complete) as launched, \
                contextlib.redirect_stdout(io.StringIO()):
            for options in ([], ["--model=gpt-6.1-terra", "--effort=high"]):
                with self.subTest(options=options), self.assertRaisesRegex(
                    SystemExit, r"Continue with --host codex --model=gpt-6.1-terra --effort=xhigh"
                ):
                    experiment.run("Q", "B", 1, "codex", self.out, options)
            launched.assert_not_called()
            self.assertFalse((self.out / "Q" / "B").exists())
            self.assertEqual(experiment.run("Q", "B", 1, "codex", self.out,
                                            ["--model=gpt-6.1-terra", "--effort=xhigh"]), 0)
            launched.assert_called_once()
        self.assertEqual(invocation.read_bytes(), before)

    def test_run_pins_the_new_default_on_an_empty_output(self):
        def complete(argv):
            self.assertEqual(argv[argv.index("--host") + 1], "codex")
            self.assertIn("--model=gpt-6.1-sol", argv)
            self.assertIn("--effort=medium", argv)
            self._sample("B", model="gpt-6.1-sol", effort="medium")
            return subprocess.CompletedProcess(argv, 0)

        with mock.patch.object(experiment.subprocess, "run", side_effect=complete) as launched, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(experiment.run("Q", "B", 1, "codex", self.out, []), 0)
            launched.assert_called_once()

    def test_queue_refuses_a_profile_change_before_any_dispatch_even_without_early_stop(self):
        self._sample("A")
        runner = mock.Mock()
        with self.assertRaisesRegex(SystemExit, "differs from Q/A/1"):
            experiment.queue(["Q"], ["B"], 2, 2, "codex", self.out, [], early_stop=False, runner=runner)
        runner.assert_not_called()
        self.assertFalse((self.out / ".queue.lock").exists())
        self.assertFalse((self.out / "Q" / "B").exists())

    def test_unknown_finished_profile_blocks_resume_even_if_model_is_explicit(self):
        (self._sample("A") / "slice" / "invocation.json").unlink()
        with mock.patch.object(experiment.subprocess, "run") as launched:
            with self.assertRaisesRegex(SystemExit, "unknown launch profile"):
                experiment.run("Q", "B", 1, "codex", self.out, ["--model=gpt-6.1-terra", "--effort=xhigh"])
            launched.assert_not_called()

    def test_scoring_and_decisions_reject_mixed_and_unknown_receipts_even_with_cached_scores(self):
        self._sample("A")
        sample = self._sample("B", effort="high")
        invocation = sample / "slice" / "invocation.json"
        cached = sample / "score.json"
        cached.write_text('{"sample": 1, "value": 1, "model": "gpt-6.1-terra", "effort": "xhigh"}')
        before = cached.read_bytes()
        journal = self.out / "journal.md"
        with mock.patch.object(experiment, "evaluator") as evaluator:
            evaluator.return_value.BINARY = True
            for receipt, error in ((invocation.read_text(), "different launch profiles"),
                                   ('{"host": "codex", "model": "gpt-6.1-terra"}', "unknown launch profile"),
                                   ('[]', "unknown launch profile")):
                invocation.write_text(receipt)
                with self.subTest(error=error):
                    for action in (lambda: experiment.score("Q", self.out),
                                   lambda: experiment.settled("Q", self.out, ["A", "B"], 4),
                                   lambda: experiment.decide("Q", "A", "B", self.out, journal)):
                        with self.assertRaisesRegex(SystemExit, error):
                            action()
            evaluator.return_value.score.assert_not_called()
        self.assertEqual(cached.read_bytes(), before)
        self.assertFalse(journal.exists())
        self.assertFalse((self.out / "Q" / "decision.json").exists())

    def test_cached_only_score_needs_invocation_evidence_to_decide(self):
        sample = self._sample("B", finished=False)
        (sample / "slice" / "invocation.json").unlink()
        (sample / "score.json").write_text('{"sample": 1, "value": 1}')
        with self.assertRaisesRegex(SystemExit, "unknown launch profile"):
            experiment.decide("Q", "A", "B", self.out, self.out / "journal.md")

    def test_legacy_claude_without_backend_matches_anthropic_and_refuses_ollama(self):
        sample = self.out / "Q" / "A" / "1"
        legacy = _write_invocation(sample, host="claude", model="claude-sonnet-5-5", effort=None)
        (legacy.parent / "slice-result.json").write_text('{"pass": true}')
        with mock.patch.object(experiment.subprocess, "run") as launched, contextlib.redirect_stdout(io.StringIO()):
            options = ["--backend=ollama", "--model=claude-sonnet-5-5"]
            with self.assertRaisesRegex(SystemExit, "differs from Q/A/1"):
                experiment.run("Q", "B", 1, "claude", self.out, options)
            launched.assert_not_called()
            experiment.run("Q", "B", 1, "claude", self.out, [])
            argv = launched.call_args.args[0]
            self.assertIn("--backend=anthropic", argv)
            self.assertIn("--model=claude-sonnet-5-5", argv)
            self.assertFalse(any(arg.startswith("--effort=") for arg in argv))


class Evaluators(unittest.TestCase):
    def check(self, exp_id: str, needs_run4: bool = False):
        import common  # noqa: PLC0415
        if needs_run4 and not common.RUN4.is_dir():
            self.skipTest("run 4's saved records are not on this machine")
        if shutil.which("node") is None:
            self.skipTest("node is not installed")
        rows = experiment.evaluator(experiment.load(exp_id)).verify()
        self.assertTrue(rows)
        self.assertTrue(all(r["ok"] for r in rows), json.dumps(rows, indent=2, default=str)[:3000])

    def test_e1_weak_tests_let_both_stand_ins_survive_and_strong_tests_kill_them(self):
        self.check("E1")

    def test_e1b_weak_tests_let_all_four_subtle_stand_ins_survive_and_strong_tests_kill_them(self):
        self.check("E1b")

    def test_e1b_scores_the_fraction_killed(self):
        import e1b_subtle_stand_ins as e1b  # noqa: PLC0415
        from unittest import mock  # noqa: PLC0415
        with mock.patch.object(e1b.e1_stand_ins, "judge", lambda *a: {"value": 0, "own_tests_pass": True, "killed": ["x"],
                                                                      "killed_fraction": 0.25, "stand_ins": {}}), \
                mock.patch.object(e1b.common, "worktree", lambda s: Path(tempfile.gettempdir())), \
                mock.patch.object(e1b.common, "run_dir", lambda s: None):
            found = e1b.score(Path("unused"))
        self.assertEqual((found["value"], found["all_killed"]), (0.25, 0))

    def test_e7_weak_tests_kill_fewer_limit_and_guard_mutants_than_boundary_tests(self):
        self.check("E7-K1")

    def test_e7_arm_t_samples_the_limit_and_guard_mutants_first_and_flips_a_line_ending_or(self):
        guard = ("function check(name) {\n"
                 "  if (name !== null && (typeof name !== 'string' || name.trim() !== name ||\n"
                 "      !name || name.length > 64 || /\\s/.test(name))) throw new Error('bad');\n"
                 "  const total = 1 + 2;\n"
                 "  return total === 3;\n"
                 "}\n")
        probe = ("import json, sys\nsys.path.insert(0, sys.argv[1])\nimport shiploop_mutation as m\n"
                 "rows = m.candidates(sys.argv[2], [2, 3, 4, 5])\n"
                 "print(json.dumps([[r['operator'], r['line'], r['column']] for r in m.sample({'src/a.js': rows})]))\n")

        def sampled(overlay_name: str) -> list:
            scripts = Path(tmp) / overlay_name
            shutil.copytree(overlay.SCRIPTS, scripts, ignore=shutil.ignore_patterns("__pycache__"))
            overlay.apply(json.loads((E2E / "overlays" / f"{overlay_name}.json").read_text()), scripts)
            done = subprocess.run([sys.executable, "-B", "-c", probe, str(scripts), guard], capture_output=True,
                                  text=True, check=False)
            self.assertEqual(done.returncode, 0, done.stderr[-2000:])
            return json.loads(done.stdout)

        with tempfile.TemporaryDirectory() as tmp:
            catalog_only, targeted = sampled("e7-m"), sampled("e7-t")
        limit_and_guard = ("rel-bound", "logic-flip")
        self.assertLess(sum(row[0] in limit_and_guard for row in catalog_only), 6)
        self.assertEqual([row[0] in limit_and_guard for row in targeted], [True] * 6 + [False] * 2)
        self.assertIn(["logic-flip", 2, guard.splitlines()[1].rindex("||") + 1], targeted)

    def test_e7_mutates_tracked_changes_and_untracked_source_but_never_a_test_file(self):
        import e7_tests  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            (tree / "src").mkdir()
            (tree / "test").mkdir()
            (tree / "src" / "a.js").write_text("const a = 1;\nconst b = 2;\n")
            subprocess.run(["git", "init", "-q", str(tree)], check=True)
            subprocess.run(["git", "-C", str(tree), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(tree), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit",
                            "-qm", "seed"], check=True)
            seed = e7_tests._git(tree, "rev-parse", "HEAD").strip()
            (tree / "src" / "a.js").write_text("const a = 1;\nconst b = a > 1 || a < 0;\n")
            (tree / "src" / "b.js").write_text("module.exports = (n) =>\n  n >= 64\n  && n !== 0;\n")
            (tree / "test" / "b.test.js").write_text("require('node:assert').ok(true);\n")
            self.assertEqual(e7_tests.changed_lines(tree, seed), {"src/a.js": {2}, "src/b.js": {1, 2, 3}})
            self.assertEqual(e7_tests.new_test_files(tree, seed), ["test/b.test.js"])

    def test_e7_request_variants_change_one_line_once_and_the_scorer_restores_the_file(self):
        import e7_request  # noqa: PLC0415
        names = [variant[0] for variant in e7_request.VARIANTS]
        self.assertEqual(len(names), len(set(names)))
        for _, _, _, find, replace, witness in e7_request.VARIANTS:
            self.assertNotEqual(find, replace)
            self.assertIn("api.", witness)
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            (tree / "src").mkdir()
            once = ("limit-65", "clause", "src/a.js", "= 64 }", "= 65 }", "")
            (tree / "src" / "a.js").write_text("const L = 64 };\n")
            original = e7_request._lay(tree, once)
            self.assertEqual(original, b"const L = 64 };\n")
            self.assertEqual((tree / "src" / "a.js").read_text(), "const L = 65 };\n")
            (tree / "src" / "a.js").write_text("= 64 } = 64 }\n")
            with self.assertRaisesRegex(ValueError, "2 matches"):
                e7_request._lay(tree, once)
        self.assertEqual(e7_request._failed("✔ ok\n✖ TC-1 a (3ms)\n✖ TC-1 a (3ms)\n✖ failing tests:\n"),
                         ["TC-1 a", "failing tests:"])

    def test_e2_flags_run_4s_strategy_and_step_plan_and_credits_a_planted_good_record(self):
        self.check("E2", needs_run4=True)

    def test_e3_reads_run_4s_focused_command_as_guarded_and_a_clean_one_as_behavioural(self):
        self.check("E3", needs_run4=True)

    def test_e4_reproduces_the_false_red_on_a_stale_target_and_a_clean_first_command_fails(self):
        self.check("E4")

    def test_e5_credits_a_fix_only_when_its_test_fails_with_the_fix_reverted(self):
        self.check("E5")

    def test_sg2s_four_seeded_cases_each_tell_the_naive_tree_from_the_fixed_one(self):
        self.check("SG2-K1")

    def test_sg2s_arms_differ_only_in_delegation_and_b_reaches_slice_py_as_ask_agent(self):
        exps = {f"SG2-K{n}": experiment.load(f"SG2-K{n}") for n in range(1, 5)}
        self.assertEqual(len({exp["case"] for exp in exps.values()}), 4)
        for exp_id, exp in exps.items():
            with self.subTest(exp=exp_id):
                a, b = exp["arms"]["A"], exp["arms"]["B"]
                self.assertEqual({k: v for k, v in b.items() if k != "delegation"}, a)
                out = Path("/nonexistent/out")
                argv_a = experiment.slice_argv(exp, a, out, "codex", None)
                argv_b = experiment.slice_argv(exp, b, out, "codex", None)
                self.assertNotIn("--delegation", argv_a)
                self.assertEqual(argv_b[argv_b.index("--delegation") + 1], "ask-agent")
                self.assertEqual([w for w in argv_b if w not in ("--delegation", "ask-agent")], argv_a)

    def test_as1s_scorer_credits_only_a_deployment_target_that_keeps_state(self):
        self.check("AS1")

    def test_as1s_two_builds_differ_in_the_apps_script_card_alone(self):
        exp = experiment.load("AS1")
        a, b = exp["arms"]["A"]["ref"], exp["arms"]["B"]["ref"]
        self.assertNotEqual(a, b)
        self.assertEqual((exp["seed_at"], exp["stop_after"], exp["evaluator"]),
                         ("test-strategy", "test-strategy", "probes/target_state_declared.py"))
        shown = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", a, b, "--", "skills", "agents", "plugins"],
                               capture_output=True, text=True)
        if shown.returncode:
            self.skipTest(f"{a[:8]} and {b[:8]} are not both in this clone")
        self.assertEqual(shown.stdout.split(), ["skills/shiploop/references/platforms/apps-script.md"])

    def test_e3s_detector_and_e2s_source_search_on_plain_commands(self):
        import e2_layers  # noqa: PLC0415
        import e3_red  # noqa: PLC0415
        self.assertTrue(e3_red.guarded("test -f src/a.js && node --test"))
        self.assertTrue(e3_red.guarded("printf '%s\\n' src/a.js && npm test"))
        self.assertFalse(e3_red.guarded("node --test --test-reporter=spec test/a.test.js"))
        self.assertTrue(e2_layers.source_search("grep -q x src/a.js && test -f b", None))
        self.assertFalse(e2_layers.source_search("node --test", None))


E6 = sorted(k for k in experiment.load() if k.startswith("E6-"))
# Arm C's gate, run against arm T's own navigator with the overlay applied (argv: scripts dir, cases JSON).
GATE_PROBE = """
import json, sys
sys.path.insert(0, sys.argv[1])
import shiploop_navigator as nav
out = {}
for name, result in json.loads(sys.argv[2]).items():
    try:
        nav._check_step_sizing(result)
        out[name] = "accepted"
    except nav.NavigatorError as exc:
        out[name] = "refused: " + str(exc)
print(json.dumps(out))
"""


class PlanSizing(unittest.TestCase):
    """E6 (docs/shiploop-plan-sizing-experiment-plan-2026-10-24.md): cases, seeds, the fake sf and arm C's gate."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-e6-")
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name)

    def test_the_evaluator_fails_run_4s_one_step_plans_and_passes_the_split_ones(self):
        rows = experiment.evaluator(experiment.load("E6-K1")).verify()
        self.assertGreaterEqual(len(rows), 10)
        self.assertTrue(all(r["ok"] for r in rows), json.dumps(rows, indent=2, default=str)[:3000])

    def test_every_e6_case_has_a_band_and_a_fixture_and_every_arm_names_a_commit(self):
        for exp_id in E6:
            exp = experiment.load(exp_id)
            case = step_slice.load_step_case(exp["case"])
            with self.subTest(exp=exp_id):
                low, high = case["shape"]["steps"]
                self.assertTrue(low >= 1 and (high is None or high >= low))
                self.assertTrue((step_slice.FIXTURES / case["fixture"]).is_dir())
                self.assertEqual((exp["seed_at"], exp["stop_after"]), ("step-plan", "step-plan"))
                self.assertLessEqual({"A", "B", "C", "T"}, set(exp["arms"]))

    def test_each_replay_seeds_at_step_plan_with_its_plan_records_and_the_packet_names_its_item(self):
        for name in ("sf-chess-engine", "sf-chess-board-entry", "node-battleship-server", "node-chess-engine"):
            spec = step_slice.load_step_case(name)
            with self.subTest(case=name):
                work = self.tmp / name / "work"
                work.mkdir(parents=True)
                seeded = run.seed_run(CLI, work, self.tmp / name, spec["prompt"], "step-plan",
                                      fixture=step_slice.FIXTURES / spec["fixture"], work_item=spec["work_item"],
                                      delegation="inline", checks=spec["checks"],
                                      records=step_slice.merged_records(spec, None))
                self.assertEqual(seeded["stage"], "step-plan")
                self.assertIn(spec["work_item"]["title"], _next(CLI, seeded["run_dir"]))
                self.assertTrue((work / "docs" / "shiploop" / "spec.md").read_text().startswith("# "))

    def test_fake_sf_is_first_on_both_paths_and_answers_without_a_real_org(self):
        from unittest import mock  # noqa: PLC0415
        out = self.tmp / "out"
        out.mkdir()
        env = {"PATH": "/usr/bin:/bin"}
        with mock.patch.dict("os.environ", {}):
            shim = step_slice.fake_sf(step_slice.load_step_case("sf-chess-engine"), out, env)
            import os  # noqa: PLC0415
            self.assertEqual(shutil.which("sf", path=os.environ["PATH"]), shim["shim"])
        self.assertEqual(shutil.which("sf", path=env["PATH"]), shim["shim"])
        done = subprocess.run(["sf", "org", "list", "--json"], env=env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('"alias": "de"', done.stdout)
        self.assertTrue(Path(shim["log"]).read_text().strip())
        self.assertIsNone(step_slice.fake_sf(step_slice.load_step_case("node-chess-engine"), out, {}))

    def _gate(self, overlay_name: str, cases: dict) -> dict:
        """Each case's outcome from _check_step_sizing on arm T's navigator with the overlay applied."""
        if subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "-q", T_REF + "^{commit}"],
                          capture_output=True).returncode:
            self.skipTest(f"{T_REF} is not in this clone")
        tar = subprocess.run(["git", "-C", str(ROOT), "archive", T_REF, "skills/shiploop/scripts",
                              "skills/shiploop/references"], check=True, capture_output=True).stdout
        import tarfile  # noqa: PLC0415
        root = self.tmp / overlay_name
        with tarfile.open(fileobj=io.BytesIO(tar)) as archive:
            archive.extractall(root, filter="data")
        scripts = root / "skills" / "shiploop" / "scripts"
        overlay.apply(json.loads((E2E / "overlays" / f"{overlay_name}.json").read_text()), scripts)
        done = subprocess.run([sys.executable, "-B", "-c", GATE_PROBE, str(scripts), json.dumps(cases)],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr[-2000:])
        return json.loads(done.stdout)

    def test_the_generic_gate_counts_a_companion_file_with_its_file_and_names_no_stack(self):
        files = "src/game/"
        cases = {
            "run 4 W1 (no step paths)": json.loads((E2E / "evaluators" / "e6_records" / "run4-w1.json").read_text()),
            "a file, its descriptor and its proof script": {
                "criteria": [{"id": "C1", "text": "One."}], "paths": [files + "*", "scripts/*"],
                "steps": [{"id": "S1", "criteria": ["C1"], "check": "sh scripts/s1-check.sh",
                           "paths": [files + "a.cls", files + "a.cls-meta.xml", files + "b.js", files + "b.js.map",
                                     files + "c.js", "scripts/s1-check.sh"]}]},
            "a.json is not a.js's companion": {
                "criteria": [{"id": "C1", "text": "One."}], "paths": [files + "*"],
                "steps": [{"id": "S1", "criteria": ["C1"], "check": "true",
                           "paths": [files + "a.js", files + "a.json", files + "b.js", files + "c.js"]}]}}
        got = self._gate("e6-size-gate-generic", cases)
        self.assertIn("must list paths", got["run 4 W1 (no step paths)"])
        self.assertEqual(got["a file, its descriptor and its proof script"], "accepted")
        self.assertIn("4 product files", got["a.json is not a.js's companion"])
        for name in ("e6-size-prose-generic", "e6-size-gate-generic"):
            shipped = " ".join(e["new"] for e in json.loads((E2E / "overlays" / f"{name}.json").read_text())["edits"])
            self.assertNotRegex(shipped.lower(), r"meta\.xml|\.apex|salesforce|sfdx|\blwc\b|lightning")

    def test_arm_c_refuses_an_oversized_or_undeclared_step_and_accepts_a_split_plan(self):
        records = E2E / "evaluators" / "e6_records"
        engine = "force-app/main/default/classes/SLChess"
        crit = [{"id": f"C{n}", "text": f"Criterion {n}."} for n in range(1, 6)]
        cases = {
            "run 4 W1 (no step paths)": json.loads((records / "run4-w1.json").read_text()),
            "battleship-1 W2 (six one-file steps)": json.loads((records / "battleship1-w2.json").read_text()),
            "four product files": {"criteria": crit[:1], "paths": [engine + "*", "scripts/*"],
                                   "steps": [{"id": "S1", "criteria": ["C1"], "check": "sh scripts/s1-check.sh",
                                              "paths": [f"{engine}{n}.cls" for n in "ABCD"] + ["scripts/s1-check.sh"]}]},
            "five criteria": {"criteria": crit, "paths": [engine + "A.cls"],
                              "steps": [{"id": "S1", "criteria": [c["id"] for c in crit], "check": "true",
                                         "paths": [engine + "A.cls"]}]},
            "three files, a sidecar and its proof script": {
                "criteria": crit[:2], "paths": [engine + "*", "scripts/*"],
                "steps": [{"id": "S1", "criteria": ["C1", "C2"], "check": "sh scripts/s1-check.sh",
                           "paths": [engine + "A.cls", engine + "A.cls-meta.xml", engine + "B.cls", engine + "C.cls",
                                     "scripts/s1-check.sh"]}]}}
        got = self._gate("e6-size-gate", cases)
        self.assertIn("must list paths", got["run 4 W1 (no step paths)"])
        self.assertEqual(got["battleship-1 W2 (six one-file steps)"], "accepted")
        self.assertIn("4 product files", got["four product files"])
        self.assertIn("5 criteria", got["five criteria"])
        self.assertEqual(got["three files, a sidecar and its proof script"], "accepted")


class RoundSpeedups(unittest.TestCase):
    """E6 R2 (2026-10-25) spent half of each shape slice in the step-plan Improve child, which changed no step count in
    80 samples, ran in fixed lanes whose slowest set the end, and ran every sample after a verdict could no longer
    change. A shape round can now skip the planning Improve children, runs as one queue, and stops a settled case."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-round-")
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name)

    def _seed(self, **options):
        spec = step_slice.load_step_case("node-fix-bug")
        work = self.tmp / "work"
        work.mkdir()
        return run.seed_run(CLI, work, self.tmp, spec["prompt"], "step-plan", fixture=step_slice.FIXTURES / spec["fixture"],
                            work_item=spec["work_item"], delegation="inline", checks=spec["checks"],
                            records=step_slice.merged_records(spec, None), **options)

    def test_a_slice_seeded_with_planning_review_none_starts_no_step_plan_review_and_needs_the_card(self):
        with self.assertRaisesRegex(SystemExit, "--planning-review none needs --improve-skill"):
            self._seed(planning_review="none")
        shutil.rmtree(self.tmp / "work")
        seeded = self._seed(planning_review="none", improve_skill=str(ROOT / "skills" / "improve" / "SKILL.md"))
        state = store.read_record(Path(seeded["run_dir"]) / "state.md")
        self.assertEqual(nav.recorded_planning_review(state), "none")
        self.assertNotIn("step-plan", nav.stage_spec.reviewed_stages(nav.recorded_planning_review(state)))
        self.assertIn("step-plan", nav.stage_spec.reviewed_stages("stage"))

    def test_a_verdict_is_settled_only_when_every_completion_of_the_missing_samples_gives_it(self):
        def rows(values):
            return [{"sample": n, "value": v} for n, v in enumerate(values, 1)]
        self.assertEqual(experiment.possible_verdicts(rows([1, 1, 1, 1]), rows([0, 0]), 4), {"contradicts"})
        # Four against four binary samples reach p < 0.05 only as a perfect split, so "supports" is never settled early.
        self.assertEqual(experiment.possible_verdicts(rows([0, 0, 0, 0]), rows([1, 1, 1]), 4), {"supports", "inconclusive"})
        self.assertEqual(experiment.possible_verdicts(rows([0, 0, 0, 0]), rows([0, 0]), 4), {"floor", "inconclusive"})
        self.assertGreater(len(experiment.possible_verdicts(rows([0, 1, 0, 0]), rows([1, 0]), 4)), 1)  # R1g K1 midway
        full = experiment.possible_verdicts(rows([0, 1, 0, 1]), rows([0, 1, 1, 1]), 4)  # R2's K2
        self.assertEqual(full, {experiment.judge(rows([0, 1, 0, 1]), rows([0, 1, 1, 1]))["verdict"]})

    def _fake(self, values):
        """A binary experiment Q whose sample of arm A scores values[A]; the runner records what ran and when."""
        from types import SimpleNamespace  # noqa: PLC0415
        exp = {"arms": {"T": {}, "Cg": {}}, "samples": 4, "evaluator": "unused.py", "case": "fake", "claim": "fake"}
        ran, live, peak, guard = [], [0], [0], threading.Lock()

        def runner(exp_id, arm, count, host, out, extra, n):
            with guard:
                live[0] += 1
                peak[0] = max(peak[0], live[0])
                ran.append((exp_id, arm, n))
            time.sleep(0.05)
            folder = _write_invocation(out / exp_id / arm / str(n)).parent
            (folder / "value.json").write_text(json.dumps({"value": values[arm]}))
            (folder / "slice-result.json").write_text(json.dumps({"pass": True}))
            with guard:
                live[0] -= 1
            return 0

        module = SimpleNamespace(BINARY=True, score=lambda folder: json.loads((folder / "value.json").read_text()))
        patches = [mock.patch.object(experiment, "load", side_effect=lambda exp_id=None: exp),
                   mock.patch.object(experiment, "evaluator", return_value=module)]
        return runner, ran, peak, patches

    def test_the_queue_runs_each_open_sample_once_at_most_jobs_at_a_time(self):
        runner, ran, peak, patches = self._fake({"T": 1, "Cg": 1})
        done = _write_invocation(self.tmp / "Q" / "T" / "2").parent
        (done / "slice-result.json").write_text("{}")
        with patches[0], patches[1], contextlib.redirect_stdout(io.StringIO()):
            status = experiment.queue(["Q"], ["T", "Cg"], 4, 3, "grok", self.tmp, [], early_stop=False, runner=runner)
        self.assertEqual(status, 0)
        self.assertEqual(sorted(ran), sorted((("Q", a, n) for n in range(1, 5) for a in ("T", "Cg") if (a, n) != ("T", 2))))
        self.assertEqual(len(ran), len(set(ran)))
        self.assertTrue(1 < peak[0] <= 3, peak[0])
        self.assertFalse((self.tmp / ".queue.lock").exists())

    def test_the_queue_stops_an_experiment_once_its_verdict_cannot_change(self):
        runner, ran, _peak, patches = self._fake({"T": 1, "Cg": 0})
        printed = io.StringIO()
        with patches[0], patches[1], contextlib.redirect_stdout(printed):
            experiment.queue(["Q"], ["T", "Cg"], 4, 1, "grok", self.tmp, [], runner=runner)
        # After T 1-2 all 1 and Cg 1-2 all 0, no completion of samples 3 and 4 leaves Cg above T: they are skipped.
        self.assertEqual(ran, [("Q", "T", 1), ("Q", "Cg", 1), ("Q", "T", 2), ("Q", "Cg", 2)])
        self.assertIn("Q/T/3: skipped, the verdict cannot change", printed.getvalue())
        self.assertIn("Q: stopped early, T vs Cg: contradicts", printed.getvalue())

    def test_the_queue_never_stops_a_supporting_experiment_before_its_last_sample(self):
        """Four against four binary samples reach p < 0.05 only as a perfect split, so one missing sample can still undo it."""
        runner, ran, _peak, patches = self._fake({"T": 0, "Cg": 1})
        with patches[0], patches[1], contextlib.redirect_stdout(io.StringIO()):
            experiment.queue(["Q"], ["T", "Cg"], 4, 1, "grok", self.tmp, [], runner=runner)
        self.assertEqual(len(ran), 8)

    def test_a_round_of_fewer_than_four_samples_is_never_stopped_early(self):
        """With 3 samples no completion reaches p < 0.05, so every one reads "inconclusive": a settled check
        there would stop the round after its first sample. R3 runs 3 full slices per arm, so it must run them all."""
        runner, ran, _peak, patches = self._fake({"T": 0, "Cg": 1})
        with patches[0], patches[1], contextlib.redirect_stdout(io.StringIO()):
            experiment.queue(["Q"], ["T", "Cg"], 3, 1, "grok", self.tmp, [], runner=runner)
        self.assertEqual(len(ran), 6)

    def test_the_downstream_experiments_run_the_whole_item_and_their_evaluator_verifies(self):
        for exp_id in ("E6D-K2", "E6D-K4"):
            exp = experiment.load(exp_id)
            with self.subTest(exp=exp_id):
                self.assertNotIn("stop_after", exp)
                self.assertEqual((exp["samples"], sorted(exp["arms"])), (3, ["Cg", "T"]))
                argv = experiment.slice_argv(exp, exp["arms"]["Cg"], self.tmp / "slice", "grok", None)
                self.assertNotIn("--stop-after", argv)
                self.assertEqual(argv[argv.index("--seed-at") + 1], "step-plan")
                missing = [a["ref"] for a in exp["arms"].values() if subprocess.run(
                    ["git", "-C", str(ROOT), "rev-parse", "--verify", "-q", a["ref"] + "^{commit}"], capture_output=True).returncode]
                if missing:  # verify builds each arm's ref; a clone without it (CI's) cannot
                    self.skipTest(f"{missing[0]} is not in this clone")
                rows = experiment.verify(exp_id)
                self.assertTrue(rows and all(r["ok"] for r in rows), rows)
        shape = experiment.slice_argv(experiment.load("E6-K2"), {"ref": T_REF}, self.tmp / "slice", "grok", None)
        self.assertEqual(shape[shape.index("--stop-after") + 1], "step-plan")

    def test_r3_on_todays_shiploop_differs_only_in_the_bound_and_runs_on_the_default_host(self):
        """R3 keeps its original arm shape; new dispatches use the owner-selected Sol/medium default from 2026-11-08.
        Cg is ShipLoop as shipped, T the same commit with the sizing bullet before the bound."""
        source = overlay.SCRIPTS / "shiploop_prompts.py"
        for exp_id, case in (("E6D2-K2", "node-chess-engine"), ("E6D2-K4", "node-battleship-server")):
            exp = experiment.load(exp_id)
            with self.subTest(exp=exp_id):
                self.assertEqual((exp["case"], exp["samples"], exp.get("descriptive")), (case, 3, True))
                self.assertNotIn("stop_after", exp)
                self.assertEqual(exp["arms"]["T"]["ref"], exp["arms"]["Cg"]["ref"])
                self.assertNotIn("overlay", exp["arms"]["Cg"])
                self.assertEqual(exp["arms"]["T"]["overlay"], "overlays/e6-no-size-bound.json")
        edits = json.loads((E2E / "overlays" / "e6-no-size-bound.json").read_text())["edits"]
        self.assertEqual(len(edits), 1)
        self.assertIn("at most 4 criteria and 3 product files", edits[0]["old"])
        self.assertNotIn("at most 4 criteria", edits[0]["new"])
        self.assertIn(edits[0]["old"], source.read_text())  # a later edit of the bullet makes this round's arms stale
        launched = []
        with mock.patch.object(experiment, "queue", side_effect=lambda *a, **k: launched.append(a) or 0):
            experiment.main(["queue", "E6D2-K2", "E6D2-K4", "--arms", "T,Cg", "--out", str(self.tmp)])
            self.assertEqual(launched[0][4], "codex")  # New runs use the owner-selected Sol/medium subject profile.

    def test_a_slice_option_written_as_two_words_is_refused_with_the_one_word_form(self):
        """R3's first launch (2026-10-26): `--timeout 10800` made "10800" an experiment id and the queue ran nothing."""
        for argv in (["queue", "E6D-K2", "--arms", "T,Cg", "--timeout", "10800"],
                     ["run", "E6D-K2", "--arm", "T", "--sample", "1", "--timeout", "10800"]):
            with self.subTest(command=argv[0]), self.assertRaises(SystemExit), \
                    contextlib.redirect_stderr(io.StringIO()) as err:
                experiment.main(argv + ["--out", str(self.tmp)])
            self.assertIn("--timeout=10800", err.getvalue())

    def test_a_job_document_carries_its_refresh_stats_and_a_cancelled_host_is_counted(self):
        import progress_card  # noqa: PLC0415
        found = {"progress": {"updatedAt": "2026-10-26T07:00:00-07:00"}, "events": [], "legend": {"pass": "scored 1"}}
        job = progress_card.job_document(found, {"title": "R3", "refresh": {"count": 4, "everySeconds": 210},
                                                 "legend": {"pass": "delivered"}})
        self.assertEqual((job["refresh"], job["legend"]["pass"]), ({"count": 4, "everySeconds": 210}, "delivered"))
        self.assertNotIn("refresh", progress_card.job_document(found, {"title": "R3"}))
        sys.path.insert(0, str(E2E / "evaluators"))
        import e6_downstream  # noqa: PLC0415
        (self.tmp / "events.jsonl").write_text('{"stopReason":"cancelled"}\n{"stopReason":"end_turn"}\n'
                                               '{"stopReason": "cancelled"}\n')
        self.assertEqual(e6_downstream.host_cancelled(self.tmp), 2)
        self.assertEqual(e6_downstream.host_cancelled(self.tmp / "none"), 0)

    # R3's T 1 stderr.txt, verbatim (2026-10-26): every Grok call after the balance ran out.
    REFUSED = ('Error: Internal error: {\n  "message": "API error (status 402 Payment Required): Grok Build usage balance '
               'exhausted",\n  "http_status": 402\n}')

    def _slice(self, sample: Path, passed: bool, stderr: str = "", value: int = 1) -> Path:
        folder = _write_invocation(sample).parent
        (folder / "slice-result.json").write_text(json.dumps({"pass": passed}))
        (folder / "value.json").write_text(json.dumps({"value": value}))
        (folder / "stderr.txt").write_text(stderr)
        return folder

    def test_a_slice_the_host_refused_is_a_host_failure_never_a_score(self):
        """R3 (journal F37): six slices failed on Grok's HTTP 402 and would have scored 0, as items not delivered."""
        refused = self.tmp / "Q" / "T" / "1"
        self._slice(refused, False, self.REFUSED)
        self.assertEqual(experiment.host_failure(refused), "HTTP 402: Grok Build usage balance exhausted")
        self.assertFalse(experiment.finished(refused))
        signed_out = self.tmp / "Q" / "T" / "3"
        self._slice(signed_out, False, '{"error": "unauthorized", "http_status": 401}')
        self.assertEqual(experiment.host_failure(signed_out), "HTTP 401")
        for name, stderr, passed in (("a passing slice", self.REFUSED, True), ("a rate limit", "API error (status 429)", False),
                                     ("a product's 404", "GET /games/9 -> status 404", False), ("no stderr", "", False)):
            sample = self.tmp / "other" / name.replace(" ", "-")
            self._slice(sample, passed, stderr)
            with self.subTest(name):
                self.assertIsNone(experiment.host_failure(sample))
                self.assertTrue(experiment.finished(sample))
        self._slice(self.tmp / "Q" / "T" / "2", False, value=0)
        _runner, _ran, _peak, patches = self._fake({})
        with patches[0], patches[1]:
            table = experiment.score("Q", self.tmp)
        self.assertEqual([(r["sample"], r["value"]) for r in table["T"]], [(2, 0)])
        record = json.loads((refused / "score.json").read_text())
        self.assertEqual((record["value"], record["host_failure"]), (None, "HTTP 402: Grok Build usage balance exhausted"))
        rows = [{"sample": 1, "value": None}, {"sample": 2, "value": 0}]
        self.assertEqual(experiment.possible_verdicts(rows, [{"sample": n, "value": 1} for n in (1, 2, 3, 4)], 4),
                         experiment.possible_verdicts(rows[1:], [{"sample": n, "value": 1} for n in (1, 2, 3, 4)], 4))

    def test_run_moves_a_refused_slice_aside_reruns_it_and_stops_at_a_new_refusal(self):
        refused = self.tmp / "Q" / "T" / "1"
        self._slice(refused, False, self.REFUSED)
        (refused / "score.json").write_text(json.dumps({"sample": 1, "value": None, "host_failure": "HTTP 402"}))
        exp = {"arms": {"T": {}}, "samples": 4, "case": "fake", "seed_at": "step-plan", "evaluator": "unused.py"}
        launched = []

        def slice_run(argv, *a, **k):
            output = Path(argv[argv.index("--output") + 1])
            launched.append(output.parent.name)
            self._slice(output.parent, False, self.REFUSED if output.parent.name == "2" else "")
            return subprocess.CompletedProcess(argv, 0)
        printed = io.StringIO()
        with mock.patch.object(experiment, "load", return_value=exp), \
                mock.patch.object(experiment.subprocess, "run", side_effect=slice_run), contextlib.redirect_stdout(printed):
            status = experiment.run("Q", "T", 4, "grok", self.tmp, [])
        self.assertEqual((status, launched), (1, ["1", "2"]))  # sample 1 reran; sample 2's refusal stopped 3 and 4
        self.assertEqual(len(list(refused.glob("slice.host-failed-*"))), 1)
        self.assertFalse((refused / "score.json").exists())
        self.assertTrue(experiment.finished(refused))
        self.assertIn("Q/T/2: the host refused its calls (HTTP 402: Grok Build usage balance exhausted)", printed.getvalue())

    def test_the_queue_starts_no_more_samples_after_a_host_refusal(self):
        ran = []

        def runner(exp_id, arm, count, host, out, extra, n):
            ran.append((arm, n))
            self._slice(out / exp_id / arm / str(n), False, self.REFUSED if (arm, n) == ("Cg", 1) else "")
            return 1 if (arm, n) == ("Cg", 1) else 0
        _runner, _ran, _peak, patches = self._fake({})
        printed = io.StringIO()
        with patches[0], patches[1], contextlib.redirect_stdout(printed):
            status = experiment.queue(["Q"], ["T", "Cg"], 4, 1, "grok", self.tmp, [], early_stop=False, runner=runner)
        self.assertEqual((status, ran), (1, [("T", 1), ("Cg", 1)]))
        self.assertIn("Q/Cg/1: the host refused its calls (HTTP 402", printed.getvalue())
        self.assertIn("with 6 samples not started", printed.getvalue())
        self.assertFalse((self.tmp / ".queue.lock").exists())

    def test_a_second_queue_in_the_same_folder_is_refused(self):
        import os  # noqa: PLC0415
        (self.tmp / ".queue.lock").write_text(f"{os.getppid()} now\n")
        with self.assertRaisesRegex(SystemExit, "another queue"):
            experiment.queue(["E6-K5"], ["T", "Cg"], 4, 2, "grok", self.tmp, [], runner=lambda *a: 0)

    def test_decide_refuses_arms_run_under_different_planning_review_options(self):
        for arm, mode in (("T", "stage"), ("Cg", "none")):
            sample = self.tmp / "E6-K5" / arm / "1"
            _write_invocation(sample)
            (sample / "score.json").write_text(json.dumps({"sample": 1, "value": 1, "planning_review": mode}))
            (sample / "command.json").write_text(json.dumps({"argv": ["slice.py", "--planning-review", mode]}))
            self.assertEqual(experiment._sample_planning_review(sample), mode)
        with self.assertRaisesRegex(SystemExit, "different planning-review options"):
            experiment.decide("E6-K5", "T", "Cg", self.tmp, journal=self.tmp / "journal.md")
        (self.tmp / "x").mkdir()
        (self.tmp / "x" / "command.json").write_text(json.dumps({"argv": ["slice.py", "--planning-review=none"]}))
        self.assertEqual(experiment._sample_planning_review(self.tmp / "x"), "none")
        self.assertEqual(experiment._sample_planning_review(self.tmp / "missing"), "stage")


class ProgressCard(unittest.TestCase):
    """progress_card.py: the inline status card for experiment runs reads run folders and writes nothing."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-card-")
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)

    def test_samples_show_as_scored_running_or_pending_with_the_plan_strip_and_the_verdict(self):
        import progress_card  # noqa: PLC0415
        done = self.out / "E6-K1" / "C" / "1" / "slice"
        done.mkdir(parents=True)
        (done / "slice-result.json").write_text("{}")
        (self.out / "E6-K1" / "T" / "1" / "slice").mkdir(parents=True)
        (self.out / "E6-K1" / "decision-T-C.json").write_text(json.dumps({"verdict": "supports"}))
        plan = [{"step": "R1 K1", "state": "done"}, {"step": "R1 K3", "state": "running", "note": "4 of 12"}]
        found = progress_card.card(self.out, ["E6-K1"], ["T", "C"], plan, 2,
                                   scorer=lambda folder: {"value": 1, "steps": 6})
        self.assertIn("1 of 8 samples", found)
        self.assertEqual(found.count('<i class="f">'), 1)
        self.assertEqual(found.count('<i class="r">'), 1)
        self.assertEqual(found.count('title="pending"'), 6)  # the legend reuses the marker, not the title
        self.assertIn('<em>6</em>', found)
        self.assertIn('<b class="ok">supports</b>', found)
        self.assertIn("ti-check", found)
        self.assertIn("R1 K3 · 4 of 12", found)
        self.assertIn("band 3+ steps", found)

    def test_a_failing_evaluator_shows_an_error_slot_not_a_pass(self):
        import progress_card  # noqa: PLC0415
        done = self.out / "E6-K5" / "T" / "1" / "slice"
        done.mkdir(parents=True)
        (done / "slice-result.json").write_text("{}")

        def broken(folder):
            raise ValueError("no step plan")
        found = progress_card.card(self.out, ["E6-K5"], ["T"], scorer=broken)
        self.assertIn('<i class="e">', found)
        self.assertNotIn('<i class="f">', found)
        self.assertIn("exactly 1 step", found)

    def test_a_sample_the_host_refused_shows_an_error_slot_not_a_below_one_result(self):
        import progress_card  # noqa: PLC0415
        done = self.out / "E6D-K2" / "T" / "1" / "slice"
        done.mkdir(parents=True)
        (done / "slice-result.json").write_text(json.dumps({"pass": False}))
        (done / "stderr.txt").write_text(RoundSpeedups.REFUSED)
        state = progress_card.sample_state(done.parent, None, now=0.0, scorer=lambda folder: {"value": 0})
        self.assertEqual(state, {"state": "error", "why": "host refused: HTTP 402: Grok Build usage balance exhausted"})
        # R3's Cg 3 (2026-10-26) was refused before it wrote a result; the card counted it as a fifth running slice.
        (done / "slice-result.json").unlink()
        state = progress_card.sample_state(done.parent, None, now=0.0, scorer=lambda folder: {"value": 0})
        self.assertEqual(state["state"], "error")

    def test_the_model_carries_iso_times_for_a_live_card_and_renders_as_the_card(self):
        import progress_card  # noqa: PLC0415
        import status_card  # noqa: PLC0415
        (self.out / "E6-K1" / "T" / "1" / "slice").mkdir(parents=True)
        done = self.out / "E6-K1" / "T" / "2" / "slice"
        done.mkdir(parents=True)
        (done / "slice-result.json").write_text("{}")
        early = progress_card.model(self.out, ["E6-K1"], ["T"], now=1_800_000_000.0,
                                    scorer=lambda folder: {"value": 1, "steps": 3})
        # No finished sample has a measured span yet: no ETA rather than a guessed one (R3, 2026-10-26).
        self.assertEqual((early["progress"]["eta"], early["progress"]["etaAt"]), (None, None))
        self.assertNotIn("ETA", status_card.render(early))
        (done / "metrics.json").write_text(json.dumps({"span": {"started": 1_799_998_800.0, "ended": 1_800_000_000.0}}))
        found = progress_card.model(self.out, ["E6-K1"], ["T"], now=1_800_000_000.0,
                                    scorer=lambda folder: {"value": 1, "steps": 3})
        self.assertEqual(found["progress"]["eta"], time.strftime("%H:%M", time.localtime(1_800_000_000.0 + 3 * 20 * 60)))
        progress = found["progress"]
        self.assertEqual((progress["done"], progress["total"], progress["running"]), (1, 4, 1))
        self.assertEqual([(e["kind"], e["text"]) for e in found["events"]],
                         [("done", "E6-K1 T sample 2 finished: value 1, 3 steps")])
        self.assertRegex(progress["updatedAt"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")
        self.assertRegex(progress["etaAt"], r"^\d{4}-\d\d-\d\dT")
        running = found["rows"][0]["cells"][0]["slots"][0]
        self.assertEqual(running["state"], "running")
        self.assertRegex(running["since"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")
        self.assertEqual(json.loads(json.dumps(found)), found)
        self.assertEqual(status_card.render(found),
                         progress_card.card(self.out, ["E6-K1"], ["T"], now=1_800_000_000.0,
                                            scorer=lambda folder: {"value": 1, "steps": 3}))
        job = progress_card.job_document(found, {"title": "R9", "notes": [
            {"at": "1999-01-01T00:00:00+00:00", "kind": "info", "text": "launched"}]})
        self.assertEqual((job["title"], job["status"], job["updatedAt"]), ("R9", "running", progress["updatedAt"]))
        self.assertEqual([e["text"] for e in job["events"]], ["E6-K1 T sample 2 finished: value 1, 3 steps", "launched"])

    def test_a_running_sample_starts_at_its_recorded_launch_and_needs_no_birth_time(self):
        """Linux's os.stat has no st_birthtime, so the card failed on main CI (2026-10-26, run 40340118933)."""
        import progress_card  # noqa: PLC0415
        from types import SimpleNamespace  # noqa: PLC0415
        sample = self.out / "E6-K1" / "T" / "1"
        (sample / "slice").mkdir(parents=True)
        linux = SimpleNamespace(st_mtime=1_700_000_100.0)
        with mock.patch.object(Path, "stat", return_value=linux):
            self.assertEqual(progress_card.started(sample), 1_700_000_100.0)
        (sample / "command.json").write_text(json.dumps({"argv": [], "started": 1_700_000_000.0}))
        state = progress_card.sample_state(sample, None, now=1_700_000_600.0)
        self.assertEqual((state["state"], state["minutes"], state["since"]), ("running", 10.0, 1_700_000_000.0))


if __name__ == "__main__":
    unittest.main()
