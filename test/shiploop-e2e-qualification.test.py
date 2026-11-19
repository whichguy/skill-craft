"""Model-free tests for promotion/5 and the harness inputs it freezes."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
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
import cycle
import hosts
import iterate
import learning_records
import packet_anatomy
import promotion
import run
import scorecard
import spread


class QualificationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runs = Path(self.temp.name) / "runs"
        self.runs.mkdir()
        self.next_start = 5000

    def registration_payload(self, roles=None, *, purpose="product_change", same_build=False, efficiency=None,
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
        return reg

    def registration(self, *args, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registration.json"
            path.write_text(json.dumps(self.registration_payload(*args, **kwargs)))
            return promotion.load_registration(path)

    def test_discovery_case_is_refused_by_strict_registration(self):
        name = "grok-chat-outcome"
        reg = self.registration_payload({name: "capability"})
        self.assertIs(scorecard.requires_acceptance(name, reg["qualification"]["cases"][name]), False)
        with self.assertRaisesRegex(SystemExit, "grok-chat-outcome.*discovery-only"):
            promotion._strict_registration(reg, json.dumps(reg).encode())

    def card(self, reg, arm, case, *, passed=True, start=None, no_start=False, attempt_id=None, run=None, build=None,
             tokens=100, minutes=10, cost=1.0, fidelity=None, correctness=True,
             attributed=True, timed=True, lower=False, driver=None, host_build="host-build-1"):
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
                                  "environments": [{"host": driver["host"], "host_build": host_build}]},
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
        self.assertTrue(any("sealed evidence" in issue["reason"] for issue in cleaned["evidence_issues"]))
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

    def test_legacy_run_receipt_without_selector_remains_complete_and_unbound(self):
        reg = self.registration()
        card = self.card(reg, "control", "hello", start=2000)
        folder = Path(card["run"])

        with mock.patch.dict(os.environ, {"SHIPLOOP_E2E_RUNS_ROOT": str(self.runs)}):
            receipt = scorecard.run_receipt(folder)

        self.assertNotIn("shiploop-run.json", receipt["files"])
        self.assertTrue(receipt["observed"])
        self.assertFalse(receipt["selected_run"]["observed"])
        self.assertEqual(receipt["selected_run"]["reason"], "shiploop-run.json is absent")

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

    def test_reference_fixture_bytes_are_frozen_in_all_scoring_digests(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp) / "repo" / "test" / "shiploop_e2e"
            (harness / "checks").mkdir(parents=True)
            (harness / "evaluators").mkdir()
            (harness / "SPEC.md").write_text("spec")
            case = {"quality": {"acceptance": {"module": "check"}}}
            cases = {"case": case}
            (harness / "cases.json").write_text(json.dumps(cases))
            (harness / "suites.json").write_text('{"suite":{"cases":["case"]}}')
            for name in ("scorecard.py", "boundary.py", "metrics.py", "delivery.py", "environment.py",
                         "runrecord.py", "promotion.py"):
                (harness / name).write_text(name)
            fixture = harness / "fixtures" / "reference" / "value.txt"
            fixture.parent.mkdir(parents=True)
            fixture.write_text("first")

            oracle_before = boundary.fingerprint(harness, case)["oracle"]
            qualification_before = boundary.qualification_snapshot(harness, ["case"])
            scoring_before = spread.scoring_digest(cases, harness)
            fixture.write_text("second")
            oracle_after = boundary.fingerprint(harness, case)["oracle"]
            qualification_after = boundary.qualification_snapshot(harness, ["case"])
            scoring_after = spread.scoring_digest(cases, harness)

            changed = {
                "oracle": oracle_before != oracle_after,
                "qualification": qualification_before["sha256"] != qualification_after["sha256"],
                "spread scoring": scoring_before["sha256"] != scoring_after["sha256"],
                "frozen fixture path": "test/shiploop_e2e/fixtures/reference/value.txt"
                in qualification_after["files"],
            }
            self.assertEqual(changed, {name: True for name in changed})

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

    def test_mismatched_observed_host_cli_builds_across_arms_prevent_promotion(self):
        reg = self.registration({"hello": "regression"}, efficiency=["tokens"])
        same_ctrl, same_cand = self.arms(
            reg,
            control=[self.card(reg, "control", "hello", tokens=1000, start=2000, host_build="codex 0.170.0")],
            candidate=[self.card(reg, "candidate", "hello", tokens=750, start=4000, host_build="codex 0.170.0")],
        )
        self.assertEqual(self.decide(reg, same_ctrl, same_cand)["decision"], "PROMOTE")

        diff_ctrl, diff_cand = self.arms(
            reg,
            control=[self.card(reg, "control", "hello", run=self.runs / "diff-ctrl", tokens=1000, start=6000,
                               host_build="codex 0.170.0")],
            candidate=[self.card(reg, "candidate", "hello", run=self.runs / "diff-cand", tokens=750, start=8000,
                                 host_build="codex 0.171.0")],
        )
        verdict = self.decide(reg, diff_ctrl, diff_cand)
        self.assertEqual(verdict["decision"], "UNDECIDED")
        self.assertTrue(any("host CLI builds" in err for err in verdict["reasons"]), verdict)


class FileBackedCaseTest(unittest.TestCase):
    NAME = "grok-chat-outcome"

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.harness = self.root / "test" / "shiploop_e2e"
        self.harness.mkdir(parents=True)
        self.cases = json.loads(run.CASES.read_text())
        self.case = self.cases[self.NAME]
        self.prompt = self.harness / self.case["prompt_file"]
        self.readiness = self.harness / self.case["readiness_file"]
        self.prompt.parent.mkdir(parents=True)
        for path in (self.prompt, self.readiness):
            shutil.copyfile(HARNESS / path.relative_to(self.harness), path)
        self.baseline = self.root / "baseline.jsonl"
        self.baseline.write_bytes(b"prior baseline\n")
        self.out = self.root / "output"
        for patch in (mock.patch.object(run, "HERE", self.harness),
                      mock.patch.object(run, "CASES", self.harness / "cases.json")):
            patch.start()
            self.addCleanup(patch.stop)
        self.write_catalog()

    def write_catalog(self):
        run.CASES.write_text(json.dumps(self.cases))

    def write_prompt(self, data):
        self.prompt.write_bytes(data)
        self.case["prompt_sha256"] = hashlib.sha256(data).hexdigest()
        self.write_catalog()

    def args(self, *extra):
        return ["--case", self.NAME, "--host", "codex", "--quiet", "--output", str(self.out),
                "--baseline", str(self.baseline), *extra]

    def load(self, *extra):
        return run.load_case(run.parser().parse_args(self.args(*extra)))

    def assert_refused(self, reason, *argv):
        effects = ("new_output_dir", "take_leases", "the_host", "marketplace_preflight", "platform_preflight", "launch")
        with contextlib.ExitStack() as stack:
            for name in effects:
                stack.enter_context(mock.patch.object(run, name, side_effect=AssertionError(f"unexpected {name}")))
            with self.assertRaisesRegex(SystemExit, reason) as error:
                run.main(list(argv) if argv else self.args())
        self.assertFalse(self.out.exists())
        self.assertEqual(self.baseline.read_bytes(), b"prior baseline\n")
        return str(error.exception)

    def test_registered_discovery_is_inspectable_and_outside_live_suites_and_allowlist(self):
        name, prompt, checks, follows = self.load()
        self.assertEqual((name, checks, follows), (self.NAME, [], None))
        self.assertEqual(prompt.encode("utf-8"), self.prompt.read_bytes())
        self.assertIsNone(run.case_platform(name))
        self.assertEqual(run.case_quality(name), {})
        suites = json.loads(run.SUITES.read_text())
        self.assertTrue(all(name not in suite["cases"] + suite.get("gate", [])
                            for key, suite in suites.items() if not key.startswith("_")))
        self.assertNotIn(name, json.loads((HARNESS / "adapter" / "allowlist.json").read_text())["cases"])

    def test_operator_ready_fixture_reaches_real_codex_argv_with_exact_prompt_and_empty_workspace(self):
        # Mock an operator assertion and the host environment. This tests runner additions, not inherited PATH or E2E_*.
        self.readiness.write_text(json.dumps({"scenario": self.NAME, "live_launch": "READY", "launch_blockers": []}))
        expected = self.prompt.read_bytes()
        codex = hosts.CodexHost("fixture-codex")

        class ReachedLaunch(Exception):
            pass

        def capture(argv, work, out, env, *args, **kwargs):
            self.assertEqual(argv[:2], ["fixture-codex", "exec"])
            self.assertEqual(argv[-1].encode("utf-8"), expected)
            self.assertEqual(argv[-1].count("$skill-craft:shiploop"), 1)
            self.assertEqual((out / "host-prompt.txt").read_bytes(), expected)
            self.assertEqual((out / "prompt.txt").read_bytes(), expected)
            self.assertTrue(kwargs["fresh"])
            self.assertEqual(list(work.iterdir()), [])
            self.assertNotIn("E2E_CHECKS", env)
            invocation = json.loads((out / "invocation.json").read_text())
            self.assertEqual(invocation["checks"], [])
            self.assertNotIn("platform", invocation)
            self.assertFalse((out / "platform").exists())
            raise ReachedLaunch

        with (mock.patch.dict(os.environ), mock.patch.object(run, "the_host", return_value=codex),
              mock.patch.object(codex, "env", return_value={}), mock.patch.object(codex, "cli_version", return_value=("fake", None)),
              mock.patch.object(run, "refuse_stale_listeners"), mock.patch.object(run, "refuse_lifecycle"),
              mock.patch.object(run, "take_leases"), mock.patch.object(run.listeners, "hold_case", return_value=None),
              mock.patch.object(run, "marketplace_preflight", return_value=(self.root, None, {"gate": []})),
              mock.patch.object(run.environment, "start_record", return_value={}),
              mock.patch.object(run.lifecycle, "contention"),
              mock.patch.object(run, "platform_preflight", side_effect=AssertionError("platform helper inherited")),
              mock.patch.object(run, "launch", side_effect=capture), self.assertRaises(ReachedLaunch)):
            run.main(self.args())

    def test_inline_and_custom_paths_still_get_host_invocations_and_checks(self):
        codex = hosts.CodexHost()
        hello = self.cases["hello"]
        name, prompt, checks, follows = self.load("--case", "hello", "--check", "extra")
        self.assertEqual((name, prompt, checks, follows), ("hello", hello["prompt"], hello["checks"] + ["extra"], None))
        self.assertEqual(run.case_opening(codex, codex.skill, prompt), "$skill-craft:shiploop " + hello["prompt"])
        name, prompt, checks, follows = self.load("--prompt", "  test\r\n", "--check", "custom-check")
        self.assertEqual((name, prompt, checks, follows), ("custom", "  test\r\n", ["custom-check"], None))
        self.assertEqual(run.case_opening(codex, codex.skill, prompt), "$skill-craft:shiploop   test\r\n")

    def test_utf8_and_newline_bytes_survive_loading_and_codex_argv(self):
        expected = "$skill-craft:shiploop\r\n\r\nCafé\r\n\r\n".encode()
        self.write_prompt(expected)
        host = hosts.CodexHost()
        opening = run.case_opening(host, host.skill, self.load()[1], preinvoked=True)
        argv = host.argv(prompt=opening, prompt_file=self.root / "host.txt", cwd=self.root, model="fixture",
                         effort=None, permission_mode=None, max_turns=None)
        self.assertEqual(argv[-1].encode("utf-8"), expected)
        self.assertEqual((self.root / "host.txt").read_bytes(), expected)

    def test_refuses_unpinned_changed_invalid_and_missing_prompt(self):
        expected = self.case.pop("prompt_sha256")
        self.write_catalog()
        with self.assertRaisesRegex(SystemExit, "needs a full lowercase prompt_sha256"):
            self.load()
        self.case["prompt_sha256"] = expected[:12]
        self.write_catalog()
        with self.assertRaisesRegex(SystemExit, "needs a full lowercase prompt_sha256"):
            self.load()
        self.case["prompt_sha256"] = expected
        self.write_catalog()
        self.prompt.write_bytes(self.prompt.read_bytes() + b"\n")
        with self.assertRaisesRegex(SystemExit, "prompt_sha256 mismatch"):
            self.load()
        for data, reason in ((b"\xff", "utf-8"), (b"x\0", "without NULs"), (b"", "nonempty")):
            with self.subTest(data=data):
                self.write_prompt(data)
                with self.assertRaisesRegex(SystemExit, reason):
                    self.load()
        self.prompt.unlink()
        with self.assertRaisesRegex(SystemExit, "missing"):
            self.load()

    def test_refuses_absolute_parent_and_symlink_escape(self):
        outside = self.harness.parent / "outside.md"
        outside.write_bytes(self.prompt.read_bytes())
        symlink = self.harness / "alias.md"
        symlink.symlink_to(outside)
        for path, reason in ((str(outside), "relative path"), ("../outside.md", "escapes"), (symlink.name, "escapes")):
            with self.subTest(path=path):
                self.case["prompt_file"] = path
                self.write_catalog()
                with self.assertRaisesRegex(SystemExit, reason):
                    self.load()

    def test_incompatible_invocation_and_prompt_rewriting_flags_refuse_before_setup(self):
        self.case.pop("readiness_file")
        self.write_catalog()
        for extra, reason in ((("--host", "claude"), "incompatible with --host claude"),
                              (("--host", "grok"), "incompatible with --host grok"),
                              (("--skill", "other:shiploop"), "first line must be"),
                              (("--seed-at", "step-plan"), "does not support --seed-at"),
                              (("--planning-review", "none"), "does not support.*--planning-review none")):
            with self.subTest(extra=extra):
                with (mock.patch.object(hosts.Host, "env", side_effect=AssertionError("host setup")),
                      mock.patch.object(hosts.CodexHost, "env", side_effect=AssertionError("host setup")),
                      mock.patch.object(run, "new_output_dir", side_effect=AssertionError("output setup")),
                      self.assertRaisesRegex(SystemExit, reason)):
                    run.main(self.args(*extra))
        self.assertFalse(self.out.exists())

    def test_blocked_run_preflight_and_resume_stop_before_side_effects(self):
        resume = self.root / "resume"
        resume.mkdir()
        (resume / "invocation.json").write_text(json.dumps({"case": self.NAME}))
        for argv in (self.args(), self.args("--stop-after-start"), self.args("--preflight-only", "--host", "all"),
                     ["--resume-run", str(resume), "--baseline", str(self.baseline)]):
            with self.subTest(argv=argv):
                message = self.assert_refused("live launch BLOCKED", *argv)
                for blocker in ("canonical org", "verified startup reset", "independent read-only observation"):
                    self.assertIn(blocker, message)
        self.assertEqual([path.name for path in resume.iterdir()], ["invocation.json"])

    def test_suite_checks_readiness_before_shared_host_setup(self):
        suites = self.root / "suites.json"
        suites.write_text(json.dumps({"fixture": {"gate": ["hello"], "cases": [self.NAME]}}))
        with mock.patch.object(run, "SUITES", suites):
            self.assert_refused("live launch BLOCKED", "--suite", "fixture", "--output", str(self.out))

    def test_conflicting_resume_modes_are_refused_before_side_effects(self):
        resume = self.root / "resume"
        resume.mkdir()
        invocation = resume / "invocation.json"
        recorded = json.dumps({"case": self.NAME})
        invocation.write_text(recorded)
        suites = self.root / "suites.json"
        suites.write_text(json.dumps({"fixture": {"gate": ["hello"], "cases": ["hello"]}}))
        resume_args = ["--resume-run", str(resume), "--baseline", str(self.baseline), "--output", str(self.out)]
        for other in (["--preflight-only"], ["--suite", "fixture"]):
            for argv in (resume_args + other, other + resume_args):
                with (self.subTest(argv=argv), mock.patch.object(run, "SUITES", suites),
                      contextlib.redirect_stderr(stderr := io.StringIO())):
                    self.assert_refused("^2$", *argv)
                    self.assertRegex(stderr.getvalue(), r"error: argument --.*: not allowed with argument --")
                    self.assertIn(other[0], stderr.getvalue().splitlines()[-1])
                    self.assertIn("--resume-run", stderr.getvalue().splitlines()[-1])
        self.assertEqual(list(resume.iterdir()), [invocation])
        self.assertEqual(invocation.read_text(), recorded)

    def test_invalid_readiness_fails_closed(self):
        records = ((b"{", "readiness refused"),
                   (b'{"scenario":"other","live_launch":"READY","launch_blockers":[]}', "scenario must be exactly"),
                   (b'{"scenario":"grok-chat-outcome","live_launch":"ready","launch_blockers":[]}', "live_launch must be"),
                   (b'{"scenario":"grok-chat-outcome","live_launch":"READY"}', "launch_blockers must be"),
                   (b'{"scenario":"grok-chat-outcome","live_launch":"READY","launch_blockers":["unresolved"]}',
                    "launch_blockers must be"),
                   (b'{"scenario":"grok-chat-outcome","live_launch":"BLOCKED","live_launch":"READY","launch_blockers":[]}',
                    "duplicate readiness fields"))
        for record, reason in records:
            with self.subTest(record=record):
                self.readiness.write_bytes(record)
                self.assert_refused(reason)
        self.readiness.unlink()
        self.assert_refused("readiness refused: .*missing")

    def test_ordinary_iteration_refuses_blocked_case_before_setup(self):
        argv = ["--case", self.NAME, "--iterations", "1", "--output", str(self.out)]

        def unexpected_worktree(_name):
            raise AssertionError(f"reached new_worktree (output exists: {self.out.exists()})")

        with (mock.patch.object(iterate, "new_worktree", side_effect=unexpected_worktree),
              mock.patch.object(iterate.subprocess, "run", side_effect=AssertionError("reached build")),
              mock.patch.object(run, "main", side_effect=AssertionError("reached runner")),
              self.assertRaisesRegex(SystemExit, "live launch BLOCKED")):
            iterate.main(argv)
        self.assertFalse(self.out.exists())

    def test_ordinary_iteration_allows_ready_discovery_and_legacy_case(self):
        self.readiness.write_text(json.dumps({"scenario": self.NAME, "live_launch": "READY", "launch_blockers": []}))
        for case in (self.NAME, "hello"):
            out = self.root / case
            argv = ["--case", case, "--iterations", "1", "--output", str(out)]
            with (self.subTest(case=case),
                  mock.patch.object(iterate, "new_worktree", side_effect=RuntimeError("fixture reached setup")),
                  self.assertRaisesRegex(RuntimeError, "fixture reached setup")):
                iterate.main(argv)
            self.assertTrue(out.is_dir())

    def test_qualified_iteration_refuses_discovery_in_either_case_role_before_setup(self):
        self.copy_qualification_inputs()
        exposing = "roundtable-agent-work"
        self.assertEqual(learning_records.select(HARNESS / "learning-records.jsonl", exposing, self.NAME),
                         "LR-20261108-4bc6cb")
        self.assertIs(self.case["discovery_only"], True)
        for index, marker in enumerate((True, "false", None, 0, [])):
            self.case["discovery_only"] = marker
            self.write_catalog()
            for first, second in ((exposing, self.NAME), (self.NAME, exposing)):
                out = self.root / f"qualify-{index}-{first}"
                argv = ["--qualify", "--case", first, "--generality-case", second, "--iterations", "1",
                        "--attempts", "1", "--tolerance", "0.25", "--output", str(out)]
                with (self.subTest(exposing=first, generality=second, marker=marker),
                      mock.patch.object(cycle, "HERE", self.harness),
                      mock.patch.object(iterate, "new_worktree", side_effect=AssertionError("reached new_worktree")) as worktree,
                      mock.patch.object(cycle, "build", side_effect=AssertionError("reached build")) as build,
                      mock.patch.object(iterate, "improve", side_effect=AssertionError("reached improve")) as improve):
                    with self.assertRaisesRegex(SystemExit, r"--qualify: .*grok-chat-outcome.*discovery-only"):
                        iterate.main(argv)
                    worktree.assert_not_called()
                    build.assert_not_called()
                    improve.assert_not_called()
                    self.assertFalse(out.exists())

    def test_nonfinite_readiness_numbers_refuse_setup_and_invalidate_both_identities(self):
        self.copy_qualification_inputs()
        frozen = boundary.qualification_snapshot(self.harness, [self.NAME])
        for number in (b"NaN", b"Infinity", b"-Infinity"):
            self.readiness.write_bytes(b'{"scenario":"grok-chat-outcome","live_launch":"READY","launch_blockers":[],'
                                       b'"observation":' + number + b'}')
            reason = f"invalid JSON number {number.decode()}"
            with self.subTest(number=number, check="setup"):
                self.assert_refused(f"readiness refused: .*{reason}")
            with self.subTest(number=number, check="qualification"):
                changes = boundary.qualification_changes(frozen, self.harness, [self.NAME])
                self.assertEqual(len(changes), 1, changes)
                self.assertRegex(changes[0], f"current qualification inputs are unavailable: .*{reason}")
            with self.subTest(number=number, check="case fingerprint"):
                invalid = boundary.fingerprint(self.harness, self.case)
                self.assertIsNone(invalid["case"])
                self.assertIn(reason, invalid["unmeasured"]["case"])

    def copy_qualification_inputs(self):
        for name in ("SPEC.md", "suites.json", "scorecard.py", "boundary.py", "metrics.py", "delivery.py",
                     "environment.py", "runrecord.py"):
            shutil.copyfile(HARNESS / name, self.harness / name)

    def test_prompt_mutation_changes_both_qualification_and_case_fingerprints(self):
        self.copy_qualification_inputs()
        frozen = boundary.qualification_snapshot(self.harness, [self.NAME])
        before = boundary.fingerprint(self.harness, self.case)
        catalog_bytes = run.CASES.read_bytes()
        relative = self.prompt.relative_to(self.root).as_posix()
        self.assertEqual(frozen["files"][relative], self.case["prompt_sha256"])
        self.prompt.write_bytes(self.prompt.read_bytes() + b"\n")
        current = boundary.qualification_snapshot(self.harness, [self.NAME])
        self.assertEqual(run.CASES.read_bytes(), catalog_bytes)
        self.assertNotEqual(current["sha256"], frozen["sha256"])
        self.assertEqual(boundary.qualification_changes(frozen, self.harness, [self.NAME]), [relative])
        self.assertEqual(boundary.changed(before, boundary.fingerprint(self.harness, self.case)), ["case"])

    def test_readiness_mutation_changes_both_qualification_and_case_fingerprints(self):
        self.copy_qualification_inputs()
        frozen = boundary.qualification_snapshot(self.harness, [self.NAME])
        before = boundary.fingerprint(self.harness, self.case)
        relative = self.readiness.relative_to(self.root).as_posix()
        original = self.readiness.read_bytes()
        record = json.loads(original)
        self.readiness.write_text(json.dumps({**record, "live_launch": "READY", "launch_blockers": []}))
        current = boundary.qualification_snapshot(self.harness, [self.NAME])
        with self.subTest(identity="qualification"):
            self.assertEqual(boundary.qualification_changes(frozen, self.harness, [self.NAME]), [relative])
            self.assertNotEqual(current["sha256"], frozen["sha256"])
            self.assertEqual(frozen["files"][relative], hashlib.sha256(original).hexdigest())
        with self.subTest(identity="case"):
            self.assertEqual(boundary.changed(before, boundary.fingerprint(self.harness, self.case)), ["case"])

    def test_readiness_path_and_parse_failures_invalidate_both_identities(self):
        self.copy_qualification_inputs()
        frozen = boundary.qualification_snapshot(self.harness, [self.NAME])
        for bad_input, reason in ((b"{", "READINESS.json"), (None, "missing")):
            if bad_input is None:
                self.readiness.unlink()
            else:
                self.readiness.write_bytes(bad_input)
            with self.subTest(bad_input=bad_input, identity="qualification"):
                changes = boundary.qualification_changes(frozen, self.harness, [self.NAME])
                self.assertEqual(len(changes), 1, changes)
                self.assertRegex(changes[0], f"current qualification inputs are unavailable: .*{reason}")
            with self.subTest(bad_input=bad_input, identity="case"):
                invalid = boundary.fingerprint(self.harness, self.case)
                self.assertIsNone(invalid["case"])
                self.assertIn("READINESS.json", invalid["unmeasured"]["case"])

    def test_inline_case_fingerprint_still_hashes_only_the_catalog_entry(self):
        case = self.cases["hello"]
        digest = hashlib.sha256(json.dumps(case, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:12]
        self.assertEqual(boundary.fingerprint(self.harness, case)["case"], digest)

    def test_packet_walk_submits_exact_pinned_or_inline_prompt(self):
        for name, expected in ((self.NAME, self.prompt.read_bytes()),
                               ("hello", self.cases["hello"]["prompt"].encode("utf-8"))):
            with (self.subTest(name=name),
                  mock.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as child):
                packet_anatomy.walk(self.root / f"walk-{name}", case=name)
                commands = [call.args[0] for call in child.call_args_list]
                [start] = [argv for argv in commands if argv[2:4] == ["workspace", "start"]]
                self.assertEqual(start[-1].encode("utf-8"), b"--prompt=" + expected)
                if name == self.NAME:
                    self.assertEqual(hashlib.sha256(expected).hexdigest(), self.case["prompt_sha256"])

    def test_packet_walk_refuses_changed_prompt_before_creating_scratch(self):
        self.prompt.write_bytes(self.prompt.read_bytes() + b"\n")
        with (mock.patch.object(packet_anatomy, "__file__", str(self.harness / "packet_anatomy.py")),
              mock.patch.object(subprocess, "run", side_effect=AssertionError("scratch child")),
              self.assertRaisesRegex(SystemExit, "prompt_sha256 mismatch")):
            packet_anatomy.walk(self.out, case=self.NAME)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
