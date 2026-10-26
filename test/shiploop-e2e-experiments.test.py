#!/usr/bin/env python3
"""Template-field experiments (test/shiploop_e2e/experiment.py), no model: the seed and stop points, the overlay applier,
the decision rule and every evaluator's verify.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / "test" / "shiploop_e2e"
sys.path.insert(0, str(E2E))
sys.path.insert(0, str(E2E / "evaluators"))
import experiment  # noqa: E402
import overlay  # noqa: E402
import run  # noqa: E402
import slice as step_slice  # noqa: E402
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
import shiploop_navigator as nav  # noqa: E402
import shiploop_store as store  # noqa: E402

CLI = ROOT / "skills" / "shiploop" / "scripts" / "shiploop"
T_REF = "9ed4ec24"


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

    def test_better_beyond_the_aa_spread_supports(self):
        found = experiment.judge(self.rows([0, 0, 0, 0, 1]), self.rows([1, 1, 1, 1, 1]))
        self.assertEqual((found["verdict"], found["spread"]), ("supports", 0))

    def test_no_better_contradicts(self):
        self.assertEqual(experiment.judge(self.rows([1, 0, 1, 0, 1]), self.rows([0, 1, 0, 0, 1]))["verdict"], "contradicts")

    def test_better_inside_the_spread_is_inconclusive(self):
        found = experiment.judge(self.rows([1, 1, 0, 0, 0]), self.rows([1, 0, 1, 0, 1]))
        self.assertEqual((found["verdict"], found["spread"]), ("inconclusive", 1.0))

    def test_without_four_control_samples_nothing_is_decided(self):
        self.assertEqual(experiment.judge(self.rows([0, 0]), self.rows([1, 1]))["verdict"], "inconclusive")

    def test_every_sample_at_one_is_a_ceiling_even_below_four_samples(self):
        for n in (3, 4):
            found = experiment.judge(self.rows([1] * n), self.rows([1] * n))
            self.assertEqual(found["verdict"], "ceiling", n)
            self.assertNotIn("samples 1-4", found["reason"])

    def test_every_sample_at_zero_is_a_floor(self):
        self.assertEqual(experiment.judge(self.rows([0, 0, 0]), self.rows([0, 0, 0, 0]))["verdict"], "floor")

    def test_a_tie_inside_the_bounds_at_three_samples_is_inconclusive_for_want_of_sample_four(self):
        found = experiment.judge(self.rows([0.5] * 3), self.rows([0.5] * 3))
        self.assertEqual(found["verdict"], "inconclusive")
        self.assertIn("samples 1-4", found["reason"])

    def test_one_arm_at_the_bound_is_not_a_ceiling(self):
        self.assertNotEqual(experiment.judge(self.rows([1, 1, 1, 1]), self.rows([1, 1, 0.75, 1]))["verdict"], "ceiling")

    def test_fractional_values_decide_on_the_spread(self):
        found = experiment.judge(self.rows([0.25, 0.25, 0.25, 0.5]), self.rows([1, 0.75, 1, 1]))
        self.assertEqual((found["verdict"], found["spread"]), ("supports", 0.125))

    def test_every_experiment_runs_four_samples_and_pins_each_arm_to_a_commit(self):
        # A descriptive experiment measures and reports (R3: owner, "3 full slices each"); decide needs 4 per arm.
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
                    (out / "E1" / arm / str(n)).mkdir(parents=True)
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
                (out / "E1" / "A" / str(n)).mkdir(parents=True)
                (out / "E1" / "A" / str(n) / "score.json").write_text(
                    json.dumps({"sample": n, "value": 0, "commit": "fixed-commit"}))
            moved = {"1": "9ed4ec24f8481a1841820033a35d31804ebb9dab", "2": "9ed4ec24f8481a1841820033a35d31804ebb9dab",
                     "3": "d21c770e5c71888069f239c7e2156b22ae515b61"}
            for n, commit in moved.items():
                (out / "E1" / "T" / n).mkdir(parents=True)
                (out / "E1" / "T" / n / "score.json").write_text(json.dumps({"sample": int(n), "value": 1, "commit": commit}))
            with self.assertRaises(SystemExit):
                experiment.decide("E1", "A", "T", out)
            self.assertFalse((out / "E1" / "decision.json").exists(), "a refused decide must not write a decision file")

    def test_run_records_the_arms_resolved_commit_in_command_json(self):
        commit = experiment._resolved_commit("HEAD")
        self.assertRegex(commit, r"^[0-9a-f]{40}$")
        self.assertIsNone(experiment._resolved_commit(None))


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

    def test_e2_flags_run_4s_strategy_and_step_plan_and_credits_a_planted_good_record(self):
        self.check("E2", needs_run4=True)

    def test_e3_reads_run_4s_focused_command_as_guarded_and_a_clean_one_as_behavioural(self):
        self.check("E3", needs_run4=True)

    def test_e4_reproduces_the_false_red_on_a_stale_target_and_a_clean_first_command_fails(self):
        self.check("E4")

    def test_e5_credits_a_fix_only_when_its_test_fails_with_the_fix_reverted(self):
        self.check("E5")

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
        self.assertEqual(experiment.possible_verdicts(rows([0, 0, 0, 0]), rows([1]), 4), {"supports"})
        self.assertEqual(experiment.possible_verdicts(rows([1, 1, 1, 1]), rows([0, 0]), 4), {"contradicts"})
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
            folder = out / exp_id / arm / str(n) / "slice"
            folder.mkdir(parents=True, exist_ok=True)
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
        done = self.tmp / "Q" / "T" / "2" / "slice"
        done.mkdir(parents=True)
        (done / "slice-result.json").write_text("{}")
        with patches[0], patches[1], contextlib.redirect_stdout(io.StringIO()):
            status = experiment.queue(["Q"], ["T", "Cg"], 4, 3, "grok", self.tmp, [], early_stop=False, runner=runner)
        self.assertEqual(status, 0)
        self.assertEqual(sorted(ran), sorted((("Q", a, n) for n in range(1, 5) for a in ("T", "Cg") if (a, n) != ("T", 2))))
        self.assertEqual(len(ran), len(set(ran)))
        self.assertTrue(1 < peak[0] <= 3, peak[0])
        self.assertFalse((self.tmp / ".queue.lock").exists())

    def test_the_queue_stops_an_experiment_once_its_verdict_cannot_change(self):
        runner, ran, _peak, patches = self._fake({"T": 0, "Cg": 1})
        printed = io.StringIO()
        with patches[0], patches[1], contextlib.redirect_stdout(printed):
            experiment.queue(["Q"], ["T", "Cg"], 4, 1, "grok", self.tmp, [], runner=runner)
        # After T 1-4 all 0 and Cg 1-3 all 1, Cg 4 can only leave "supports": it is skipped.
        self.assertEqual(ran, [("Q", "T", 1), ("Q", "Cg", 1), ("Q", "T", 2), ("Q", "Cg", 2), ("Q", "T", 3), ("Q", "Cg", 3),
                               ("Q", "T", 4)])
        self.assertIn("Q/Cg/4: skipped, the verdict cannot change", printed.getvalue())
        self.assertIn("Q: stopped early, T vs Cg: supports", printed.getvalue())

    def test_a_round_of_fewer_than_four_samples_is_never_stopped_early(self):
        """With 3 samples the A/A spread is never measured, so every completion reads "inconclusive": a settled check
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
                rows = experiment.verify(exp_id)
                self.assertTrue(rows and all(r["ok"] for r in rows), rows)
        shape = experiment.slice_argv(experiment.load("E6-K2"), {"ref": T_REF}, self.tmp / "slice", "grok", None)
        self.assertEqual(shape[shape.index("--stop-after") + 1], "step-plan")

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

    def test_a_second_queue_in_the_same_folder_is_refused(self):
        import os  # noqa: PLC0415
        (self.tmp / ".queue.lock").write_text(f"{os.getppid()} now\n")
        with self.assertRaisesRegex(SystemExit, "another queue"):
            experiment.queue(["E6-K5"], ["T", "Cg"], 4, 2, "grok", self.tmp, [], runner=lambda *a: 0)

    def test_decide_refuses_arms_run_under_different_planning_review_options(self):
        for arm, mode in (("T", "stage"), ("Cg", "none")):
            sample = self.tmp / "E6-K5" / arm / "1"
            sample.mkdir(parents=True)
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

    def test_the_model_carries_iso_times_for_a_live_card_and_renders_as_the_card(self):
        import progress_card  # noqa: PLC0415
        import status_card  # noqa: PLC0415
        (self.out / "E6-K1" / "T" / "1" / "slice").mkdir(parents=True)
        done = self.out / "E6-K1" / "T" / "2" / "slice"
        done.mkdir(parents=True)
        (done / "slice-result.json").write_text("{}")
        found = progress_card.model(self.out, ["E6-K1"], ["T"], now=1_800_000_000.0,
                                    scorer=lambda folder: {"value": 1, "steps": 3})
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


if __name__ == "__main__":
    unittest.main()
