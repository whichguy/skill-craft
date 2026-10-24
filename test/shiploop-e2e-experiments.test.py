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
import unittest
from pathlib import Path

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
T_REF = "feat/shiploop-templates-6d625a"


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


if __name__ == "__main__":
    unittest.main()
