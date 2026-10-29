"""No-model qualification tests for the strict promotion/5 contract."""

from __future__ import annotations

import copy
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "test" / "shiploop_e2e"
sys.path.insert(0, str(HARNESS))
import boundary
import promotion
import scorecard


class QualificationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runs = Path(self.temp.name) / "runs"
        self.runs.mkdir()
        self.next_start = 5000

    def registration(self, roles=None, *, purpose="product_change", same_build=False, efficiency=None,
                     budget=None, hard_floors=None, registered_at=1000, raw_changes=None):
        roles = roles or {"hello": "capability"}
        cases = {case: {"role": role, "attempts": 1} for case, role in roles.items()}
        snapshot = boundary.qualification_snapshot(HARNESS, cases)
        control_build = "a" * 12
        candidate_build = control_build if same_build else "b" * 12
        control_driver = {"host": "claude", "model": "model-a", "effort": "high"}
        candidate_driver = dict(control_driver)
        if purpose == "model_only":
            candidate_driver["model"] = "model-b"
        reg = {"contract": "promotion/5", "registered_at": registered_at, "purpose": purpose,
               "cases": cases, "floors": ["accuracy", "fidelity"], "quality_tolerance": 0.0,
               "tolerance": 0.1, "budget": budget if budget is not None else {},
               "hard_floors": hard_floors if hard_floors is not None else [],
               "qualification": snapshot,
               "arms": {"control": {"shiploop_build": control_build, "driver": control_driver},
                        "candidate": {"shiploop_build": candidate_build, "driver": candidate_driver}},
               "attempts": [{"id": f"{arm}:{case}", "arm": arm, "case": case}
                            for arm in ("control", "candidate") for case in cases]}
        if efficiency is not None:
            reg["efficiency"] = efficiency
        if raw_changes:
            reg.update(raw_changes)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registration.json"
            path.write_text(json.dumps(reg))
            return promotion.load_registration(path)

    def card(self, reg, arm, case, *, passed=True, start=None, no_start=False, attempt_id=None, run=None, build=None,
             tokens=100, minutes=10, cost=1.0, fidelity=None, correctness=True,
             attributed=True, timed=True, lower=False, driver=None):
        attempt_id = attempt_id or f"{arm}:{case}"
        if no_start:
            start = None
        elif start is None:
            start = self.next_start
            self.next_start += 1000
        folder = Path(run) if run is not None else self.runs / attempt_id.replace(":", "-")
        folder.mkdir(parents=True, exist_ok=True)
        build = build or reg["arms"][arm]["shiploop_build"]
        driver = driver or dict(reg["arms"][arm]["driver"])
        end = start + minutes * 60 if isinstance(start, (int, float)) and isinstance(minutes, (int, float)) else start
        work = folder / "work"
        work.mkdir(exist_ok=True)
        (work / "product.txt").write_text(attempt_id)
        if not (work / ".git").exists():
            subprocess.run(["git", "-C", str(work), "init", "-q"], check=True)
            subprocess.run(["git", "-C", str(work), "config", "user.name", "Qualification Fixture"], check=True)
            subprocess.run(["git", "-C", str(work), "config", "user.email", "fixture@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(work), "add", "product.txt"], check=True)
            subprocess.run(["git", "-C", str(work), "commit", "-q", "-m", "product"], check=True)
        product = scorecard.delivery.fingerprint(work)
        bundle = folder / "delivery" / "work.bundle"
        bundle.parent.mkdir(exist_ok=True)
        subprocess.run(["git", "-C", str(work), "bundle", "create", str(bundle), "--all"], check=True)
        if fidelity is None:
            fidelity_record = {"end_state": {"status": "done", "unverified": {"entries": 0, "not_restated": 0}},
                               "evidence": {"counts": {"skipped": 0}}, "edits": {"script_owned": []}, "refusals": {}}
        elif fidelity == "unobserved":
            fidelity_record = {"end_state": {"status": "done"}, "evidence": {"counts": {"skipped": 0}}}
        else:
            fidelity_record = {"end_state": {"status": "stopped", "unverified": {"entries": 0, "not_restated": 0}},
                               "evidence": {"counts": {"skipped": 0}}}
        run_metrics = {"span": {"started": start, "ended": end}, "tokens": {"processed": tokens, "output": tokens},
                       "cost_usd": cost, "turns": 2, "unreported_sessions": 1 if lower else 0,
                       "tmp_writes": [], "fidelity": fidelity_record}
        result = {"case": case, "host": driver["host"], "backend": "anthropic", "model": driver["model"],
                  "effort": driver["effort"], "pass": passed, "outcome_class": "DONE" if passed else "FAILED",
                  "attempt_id": attempt_id, "resumed_run": not timed,
                  "versions": {"plugin_sha256": build, "plugin_version": "1.0", "shiploop_version": "1.0"},
                  "boundary": {"evaluator": "e" * 12, "oracle": "o" * 12, "case": f"c-{case}"},
                  "environment": {"mixed_host": not attributed,
                                  "environments": [{"host": driver["host"], "host_build": "host-build-1"}]},
                  "left_behind": {"observed": True, "survived": []},
                  "quality": {"held_out_seen": 0},
                  "delivery": {"before": {**product, "bundle": "delivery/work.bundle"}, "after": dict(product)}}
        (folder / "result.json").write_text(json.dumps(result, allow_nan=True))
        (folder / "metrics.json").write_text(json.dumps(run_metrics, allow_nan=True))
        (folder / "timeline.jsonl").write_text(
            "" if start is None else f'{{"line":1,"t":{start}}}\n{{"line":2,"t":{end}}}\n')
        (folder / "invocation.json").write_text(json.dumps({"case": case, "host": driver["host"], "model": driver["model"],
                                                             "effort": driver["effort"], "plugin_dir": str(ROOT)}))
        (folder / "prompt.txt").write_text("fixture prompt\n")
        (folder / "transcript.md").write_text("fixture transcript\n")
        (folder / "events.jsonl").write_text("{}\n")
        (folder / "stderr.txt").write_text("")
        with mock.patch.dict(os.environ, {"SHIPLOOP_E2E_RUNS_ROOT": str(self.runs)}):
            result["environment"]["overlap"] = scorecard.environment.overlap(folder)
            (folder / "result.json").write_text(json.dumps(result, allow_nan=True))
            card = scorecard.score(folder, required_case=reg["qualification"]["cases"].get(case))
        card["attempt_id"] = attempt_id
        return card

    def arms(self, reg, *, control=None, candidate=None):
        control_cards = control or [self.card(reg, "control", case, start=2000 + i * 2000)
                                   for i, case in enumerate(reg["cases"])]
        candidate_cards = candidate or [self.card(reg, "candidate", case, start=3000 + i * 2000)
                                        for i, case in enumerate(reg["cases"])]
        return ([(card, card["started"]) for card in control_cards],
                [(card, card["started"]) for card in candidate_cards])

    def decide(self, reg, control, candidate, *, harness_root=None):
        with mock.patch.dict(os.environ, {"SHIPLOOP_E2E_RUNS_ROOT": str(self.runs)}):
            return promotion.decide(reg, control, candidate, harness_root=harness_root)

    def test_strict_registration_freezes_inputs_and_uses_versioned_apis(self):
        reg = self.registration()
        self.assertEqual(reg["contract"], "promotion/5")
        self.assertEqual(reg["efficiency"], ["tokens", "minutes"])
        self.assertEqual(reg["qualification"]["scorecard"], "scorecard/6")
        self.assertIn("test/shiploop_e2e/SPEC.md", reg["qualification"]["files"])
        self.assertTrue(any(path.startswith("test/shiploop_e2e/evaluators/")
                            for path in reg["qualification"]["files"]))
        report = self.decide(reg, *self.arms(reg))
        self.assertEqual(report["contract"], "promotion/5")
        self.assertEqual(report["decision"], "UNDECIDED")
        self.assertEqual(report["qualification"]["scorecard"], "scorecard/6")

    def test_late_or_missing_start_and_card_file_bypass_cannot_qualify(self):
        reg = self.registration(registered_at=2500)
        control = [(self.card(reg, "control", "hello", start=3000), 3000)]
        candidate = [(self.card(reg, "candidate", "hello", start=2400), 2400)]
        late = self.decide(reg, control, candidate)
        self.assertEqual(late["decision"], "UNDECIDED")
        self.assertTrue(any("registration was written after the run began" in reason for reason in late["reasons"]))
        missing = self.card(reg, "candidate", "hello", no_start=True)
        no_start = self.decide(reg, control, [(missing, None)])
        self.assertEqual(no_start["decision"], "UNDECIDED")
        self.assertTrue(any("run start is missing" in reason for reason in no_start["reasons"]))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cards.json"
            path.write_text("[]")
            with self.assertRaisesRegex(SystemExit, "cannot use card files"):
                promotion.arm([path], reg)

    def test_duplicate_attempt_ids_and_run_paths_are_rejected(self):
        reg = self.registration()
        card = self.card(reg, "control", "hello", start=2000)
        duplicate = copy.deepcopy(card)
        duplicate["started"] = 2001
        duplicate["run"] = str(Path(card["run"]).with_name("other"))
        report = self.decide(reg, [(card, 2000), (duplicate, 2001)],
                             [(self.card(reg, "candidate", "hello", start=3000), 3000)])
        self.assertEqual(report["decision"], "UNDECIDED")
        self.assertTrue(any("attempt ID 'control:hello' is duplicated" in reason for reason in report["reasons"]))
        path_duplicate = copy.deepcopy(card)
        path_duplicate["attempt_id"] = "candidate:hello"
        path_duplicate["boundary"]["candidate"] = reg["arms"]["candidate"]["shiploop_build"]
        report = self.decide(reg, [(card, 2000)], [(path_duplicate, 2001)])
        self.assertTrue(any("run path" in reason and "duplicated" in reason for reason in report["reasons"]))

    def test_mixed_arm_build_and_driver_must_match_bindings(self):
        reg = self.registration()
        control = [(self.card(reg, "control", "hello", start=2000), 2000)]
        changed_driver = {"host": "claude", "model": "unregistered-model", "effort": "high"}
        candidate_card = self.card(reg, "candidate", "hello", start=3000, build="c" * 12, driver=changed_driver)
        report = self.decide(reg, control, [(candidate_card, 3000)])
        self.assertEqual(report["decision"], "UNDECIDED")
        self.assertTrue(any("ShipLoop build does not match" in reason for reason in report["reasons"]))
        self.assertTrue(any("host/model/effort does not match" in reason for reason in report["reasons"]))

    def test_same_build_requires_calibration_or_model_only_purpose(self):
        with self.assertRaisesRegex(SystemExit, "product_change needs different ShipLoop builds"):
            self.registration(same_build=True)
        calibration = self.registration(purpose="calibration", same_build=True)
        control = [self.card(calibration, "control", "hello", passed=False, start=2000)]
        candidate = [self.card(calibration, "candidate", "hello", passed=True, start=3000)]
        report = self.decide(calibration, *self.arms(calibration, control=control, candidate=candidate))
        self.assertEqual(report["purpose"], "calibration")
        self.assertEqual(report["decision"], "UNDECIDED")
        self.assertEqual(report["diagnostic_decision"], "PROMOTE")
        self.assertIn("calibration", report["reasons"][0])
        model_only = self.registration(purpose="model_only", same_build=True)
        report = self.decide(model_only, *self.arms(model_only))
        self.assertEqual(report["decision"], "UNDECIDED")
        self.assertEqual(report["qualification"]["attribution"], "model-only")
        self.assertIn("model-only result", " ".join(report["notes"]))

    def test_product_change_gain_requires_measured_budget_even_when_quality_rises(self):
        reg = self.registration(budget={"tokens": 1000})
        control = [self.card(reg, "control", "hello", passed=False, start=2000)]
        candidate = [self.card(reg, "candidate", "hello", passed=True, start=3000, tokens=None)]
        report = self.decide(reg, *self.arms(reg, control=control, candidate=candidate))
        self.assertEqual(report["decision"], "UNDECIDED")
        self.assertIn("budget evidence is unknown", report["reasons"][0])
        candidate = [self.card(reg, "candidate", "hello", passed=True, start=3000, tokens=1200)]
        report = self.decide(reg, *self.arms(reg, control=control, candidate=candidate))
        self.assertEqual(report["decision"], "DROP")
        self.assertIn("over the registered budget", report["reasons"][0])

    def test_known_regression_or_explicit_hard_floor_survives_unrelated_unknowns(self):
        reg = self.registration({"hello": "regression", "battleship": "capability"})
        control = [self.card(reg, "control", "hello", passed=True, start=2000),
                   self.card(reg, "control", "battleship", passed=False, start=4000)]
        candidate = [self.card(reg, "candidate", "hello", passed=False, start=3000)]
        report = self.decide(reg, *self.arms(reg, control=control, candidate=candidate))
        self.assertEqual(report["decision"], "DROP")
        self.assertIn("hello", report["reasons"][0])
        self.assertTrue(any("candidate:battleship" in row["reason"]
                            for row in report["evidence_issues"]))
        self.assertIsNone(report["cases"]["battleship"]["candidate"]["share"])

        hard = self.registration({"hello": "capability", "battleship": "capability"}, hard_floors=["accuracy"])
        control = [self.card(hard, "control", "hello", passed=False, start=2000),
                   self.card(hard, "control", "battleship", passed=True, start=4000)]
        candidate = [self.card(hard, "candidate", "hello", passed=True, start=3000),
                     self.card(hard, "candidate", "battleship", passed=False,
                               fidelity="unobserved", start=5000)]
        report = self.decide(hard, *self.arms(hard, control=control, candidate=candidate))
        self.assertEqual(report["decision"], "DROP")
        self.assertTrue(report["hard_floor_failures"])
        self.assertTrue(report["unknown_floor_evidence"])

    def test_capability_failures_are_share_evidence_and_do_not_override_another_gain(self):
        reg = self.registration({"hello": "capability", "battleship": "capability"})
        control = [self.card(reg, "control", "hello", passed=True, start=2000),
                   self.card(reg, "control", "battleship", passed=False, start=4000)]
        candidate = [self.card(reg, "candidate", "hello", passed=False, start=3000),
                     self.card(reg, "candidate", "battleship", passed=True, start=5000)]
        report = self.decide(reg, *self.arms(reg, control=control, candidate=candidate))
        self.assertEqual(report["decision"], "PROMOTE")
        self.assertIn("battleship", report["reasons"][0])

    def test_default_tokens_precede_minutes_and_dollars_are_budget_only(self):
        reg = self.registration()
        control = [self.card(reg, "control", "hello", tokens=1000, minutes=10, cost=1, start=2000)]
        candidate = [self.card(reg, "candidate", "hello", tokens=500, minutes=20, cost=100, start=3000)]
        report = self.decide(reg, *self.arms(reg, control=control, candidate=candidate))
        self.assertEqual(report["decision"], "PROMOTE")
        self.assertIn("tokens per success", report["reasons"][0])

    def test_cleanup_or_a_runs_root_override_cannot_erase_observed_interference(self):
        reg = self.registration()
        control = self.card(reg, "control", "hello", passed=False, start=2000)
        neighbour = self.runs / "interference"
        neighbour.mkdir()
        (neighbour / "timeline.jsonl").write_text('{"line":1,"t":3001}\n{"line":2,"t":3500}\n')
        (neighbour / "metrics.json").write_text('{"tmp_writes":["/tmp/shared"]}')
        candidate = self.card(reg, "candidate", "hello", passed=True, start=3000)
        self.assertIn("interference", candidate["run_receipt"]["ambient"]["neighbours"])
        arms = ([(control, 2000)], [(candidate, 3000)])
        empty = Path(self.temp.name) / "empty-root"
        empty.mkdir()
        with mock.patch.dict(os.environ, {"SHIPLOOP_E2E_RUNS_ROOT": str(empty)}):
            changed_root = promotion.decide(reg, *arms)
        self.assertEqual(changed_root["decision"], "UNDECIDED")
        shutil.rmtree(neighbour)
        cleaned = self.decide(reg, *arms)
        self.assertEqual(cleaned["decision"], "UNDECIDED")
        self.assertTrue(any("sealed run receipt" in issue["reason"] for issue in cleaned["evidence_issues"]))
        with mock.patch.dict(os.environ, {"SHIPLOOP_E2E_RUNS_ROOT": str(self.runs)}):
            fresh = scorecard.score(candidate["run"], required_case=reg["qualification"]["cases"]["hello"])
        self.assertEqual(fresh["validity"]["overlapped_runs"], 1, "cleanup cannot erase the recorded neighbour")
        self.assertFalse(fresh["validity"]["timing"]["valid"])

    def test_missing_run_time_overlap_baseline_cannot_be_replaced_by_an_empty_live_root(self):
        for baseline in (None, {"observed": False, "reason": "runs root unavailable"}):
            with self.subTest(baseline=baseline):
                reg = self.registration()
                control = self.card(reg, "control", "hello", passed=False, start=2000)
                candidate = self.card(reg, "candidate", "hello", passed=True, start=3000)
                folder = Path(candidate["run"])
                result = json.loads((folder / "result.json").read_text())
                result["environment"]["overlap"] = baseline
                (folder / "result.json").write_text(json.dumps(result))
                with mock.patch.dict(os.environ, {"SHIPLOOP_E2E_RUNS_ROOT": str(self.runs)}):
                    fresh = scorecard.score(folder, required_case=reg["qualification"]["cases"]["hello"])
                self.assertFalse(fresh["run_receipt"]["observed"])
                self.assertIsNone(fresh["validity"]["timing"]["valid"])
                fresh["attempt_id"] = "candidate:hello"
                report = self.decide(reg, [(control, 2000)], [(fresh, 3000)])
                self.assertEqual(report["decision"], "UNDECIDED")

    def test_malformed_efficiency_and_invalid_comparability_never_win(self):
        for value in (True, float("nan"), -1):
            with self.subTest(value=value):
                reg = self.registration(efficiency=["tokens"])
                control = [self.card(reg, "control", "hello", tokens=1000, start=2000)]
                candidate = [self.card(reg, "candidate", "hello", tokens=value, start=3000)]
                report = self.decide(reg, *self.arms(reg, control=control, candidate=candidate))
                self.assertEqual(report["decision"], "UNDECIDED")
                if isinstance(value, float) and math.isnan(value):
                    self.assertTrue(any("malformed" in reason for reason in report["reasons"]))
                else:
                    self.assertIn("not measured", " ".join(report["notes"]))
        reg = self.registration(efficiency=["tokens"])
        control = [self.card(reg, "control", "hello", tokens=1000, start=2000)]
        candidate = [self.card(reg, "candidate", "hello", tokens=500, attributed=False, start=3000)]
        report = self.decide(reg, *self.arms(reg, control=control, candidate=candidate))
        self.assertEqual(report["decision"], "UNDECIDED")
        self.assertIn("not comparable", " ".join(report["notes"]))

    def test_frozen_requiredness_scores_run_folder_without_rereading_current_catalog(self):
        snapshot = boundary.qualification_snapshot(HARNESS, ["checkers"])
        frozen_case = snapshot["cases"]["checkers"]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            run.mkdir()
            (run / "result.json").write_text(json.dumps({"case": "checkers", "host": "claude", "model": "m",
                "effort": "high", "pass": True, "quality": {"acceptance": {"observed": False}, "held_out_seen": 0}}))
            (run / "metrics.json").write_text(json.dumps({"tmp_writes": []}))
            (run / "timeline.jsonl").write_text('{"line":1,"t":1234.5}\n')
            empty_catalog = Path(tmp) / "cases.json"
            empty_catalog.write_text('{"checkers":{}}')
            with mock.patch.object(scorecard, "CASES", empty_catalog):
                strict = scorecard.score(run, required_case=frozen_case)
                legacy = scorecard.score(run)
        self.assertEqual(strict["scorecard"], "scorecard/6")
        self.assertTrue(strict["accuracy"]["acceptance_required"])
        self.assertEqual(strict["floors"]["accuracy"], "unobserved")
        self.assertFalse(legacy["accuracy"]["acceptance_required"])
        self.assertEqual(legacy["floors"]["accuracy"], "pass")

    def test_run_receipt_captures_internal_symlink_bytes_and_rejects_external_targets(self):
        reg = self.registration()
        card = self.card(reg, "control", "hello", start=2000)
        folder = Path(card["run"])
        prompt = folder / "prompt.txt"
        prompt.unlink()
        target = folder / "prompt-source.txt"
        target.write_text("first\n")
        prompt.symlink_to(target.name)
        before = scorecard.run_receipt(folder)
        target.write_text("second\n")
        after = scorecard.run_receipt(folder)
        self.assertNotEqual(before["sha256"], after["sha256"])

        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("external\n")
        (folder / "work" / "external-link").symlink_to(outside, target_is_directory=True)
        unsafe = scorecard.run_receipt(folder)
        self.assertFalse(unsafe["observed"])
        self.assertTrue(unsafe["unsafe_symlinks"])

    def test_snapshot_hashes_nested_evaluators_and_blocks_unreadable_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp) / "repo" / "test" / "shiploop_e2e"
            (harness / "checks" / "nested").mkdir(parents=True)
            (harness / "evaluators" / "nested").mkdir(parents=True)
            (harness / "SPEC.md").write_text("spec")
            (harness / "cases.json").write_text('{"case":{"quality":{"acceptance":{"module":"check"}}}}')
            (harness / "suites.json").write_text('{"suite":{"cases":["case"]}}')
            for name in ("scorecard.py", "boundary.py", "metrics.py", "delivery.py", "environment.py", "runrecord.py"):
                (harness / name).write_text(name)
            evaluator = harness / "evaluators" / "nested" / "rule.py"
            evaluator.write_text("one")
            (harness / "checks" / "nested" / "oracle.py").write_text("check")
            frozen = boundary.qualification_snapshot(harness, ["case"])
            evaluator.write_text("two")
            changed = boundary.qualification_changes(frozen, harness, ["case"])
            self.assertIn("test/shiploop_e2e/evaluators/nested/rule.py", changed)
            (harness / "scorecard.py").unlink()
            changed = boundary.qualification_changes(frozen, harness, ["case"])
            self.assertTrue(any("unavailable" in reason for reason in changed))

    def test_mutated_registration_or_current_scorer_mismatch_stays_undecided(self):
        reg = self.registration()
        control, candidate = self.arms(reg)
        changed = copy.deepcopy(reg)
        changed["qualification"]["cases"]["hello"]["quality"] = {"acceptance": {"module": "unknown"}}
        report = self.decide(changed, control, candidate)
        self.assertEqual(report["decision"], "UNDECIDED")
        self.assertTrue(any("registration is no longer valid" in reason for reason in report["reasons"]))
        with tempfile.TemporaryDirectory() as tmp:
            report = self.decide(reg, control, candidate, harness_root=Path(tmp))
        self.assertEqual(report["decision"], "UNDECIDED")
        self.assertTrue(any("qualification inputs changed" in reason for reason in report["reasons"]))

    def test_duplicate_or_malformed_registration_fields_are_refused(self):
        reg = self.registration()
        bads = []
        duplicate = copy.deepcopy(reg)
        duplicate["attempts"][1]["id"] = duplicate["attempts"][0]["id"]
        bads.append(duplicate)
        bad_numeric = copy.deepcopy(reg)
        bad_numeric["tolerance"] = True
        bads.append(bad_numeric)
        bad_hard_floor = copy.deepcopy(reg)
        bad_hard_floor["hard_floors"] = ["enterprise"]
        bads.append(bad_hard_floor)
        for bad in bads:
            with (self.subTest(bad=bad.get("tolerance", bad.get("attempts"))),
                  tempfile.TemporaryDirectory() as tmp):
                path = Path(tmp) / "registration.json"
                path.write_text(json.dumps(bad))
                with self.assertRaises(SystemExit):
                    promotion.load_registration(path)


if __name__ == "__main__":
    unittest.main()
