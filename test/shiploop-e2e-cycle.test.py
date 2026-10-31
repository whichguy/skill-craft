"""No-model campaign of one qualified cycle (cycle.py): a real worktree, ledger and epoch; the improver, the purpose
review, the decision and the cards stand in for the model and the runs."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import state_home

state_home.isolate()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import boundary
import cycle
import epoch
import iterate
import learning_records as lr
import purpose_check
import review as reviewer
import run as runner
import spread

CASES = ("hello", "csv-report")
JOURNAL = cycle.JOURNAL  # in the temporary worktree; this suite never reads the checked-in journal


def card(case, tokens=1_000_000, ok=True):
    return {"case": case, "floors": {"accuracy": "pass" if ok else "fail", "fidelity": "pass"},
            "validity": {"correctness": {"valid": True}, "attribution": {"valid": True}, "timing": {"valid": False}},
            "efficiency": {"tokens": tokens, "turns": 200, "totals_lower_bound": False}}


class CycleTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.worktree = self.temp / "worktree"
        self.worktree.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        self.write("skills/shiploop/scripts/x.py", "x = 1\n")
        self.write(JOURNAL, "# Learnings\n")
        self.ledger = self.worktree / "test" / "shiploop_e2e" / lr.LEDGER.name
        self.record = lr.new_id()
        lr.append("opened", self.record, self.ledger, title="the packet says how to proceed unattended",
                  anchor={"clause_id": "S-14", "relationship": "supports"}, materiality="material", confidence="high",
                  target="shiploop", files=["skills/shiploop/scripts/x.py"], proposal="say so")
        lr.append("admitted", self.record, self.ledger)
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        self.tip = self.git("rev-parse", "HEAD")
        catalog = json.loads((ROOT / "test" / "shiploop_e2e" / "cases.json").read_text())
        self.calibration = {"attempts": 1, "tolerance": 0.10, "metric": "tokens",
                            "sha256": spread.scoring_digest({c: catalog[c] for c in CASES})["sha256"]}
        self.args = argparse.Namespace(case="hello", generality_case="csv-report", host=None, model=None, effort=None,
                                       parallel=2, skip_reviews=True, budget=None, codex_bin="codex")
        self.prediction = {"contract": "prediction/1", "record": self.record, "anchor": "S-14",
                           "because": "a stated default replaces the pause, so fewer turns are spent waiting",
                           "effects": [{"case": "hello", "measure": "tokens", "direction": "down", "at_least": 0.15}],
                           "guards": [{"case": "*", "measure": "accuracy", "direction": "not_down"}]}

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.worktree), *args], check=True, capture_output=True,
                              text=True).stdout.strip()

    def write(self, path, text):
        target = self.worktree / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def improver(self, line="x = 2  # an unattended run records the default and proceeds\n", prediction=None, record=None):
        record = record or self.record
        prediction = prediction if prediction is not None else {**self.prediction, "record": record}

        def improve(worktree, findings, stage, args, prompt=None):
            self.assertIn(f"Learning-Record: {record}", prompt)
            self.assertIn('"prediction"', prompt)
            before = self.git("status", "--porcelain").splitlines()
            stage.mkdir()
            self.write("skills/shiploop/scripts/x.py", line)
            self.git("add", "skills/shiploop/scripts/x.py")
            self.git("commit", "-qm", f"candidate proposal: record the unattended default\n\nLearning-Record: {record}")
            return {"process": {"status": "exited"}, "report": {"prediction": prediction},
                    "base": self.git("rev-parse", "HEAD~1"),
                    "commits": [self.git("rev-parse", "HEAD")], "changed": ["skills/shiploop/scripts/x.py"],
                    "out_of_scope": [], "uncommitted": before, "withheld": [], "held_out_named": 0,
                    "grading": {"changed": []}}
        return improve

    def build(self, worktree, out):
        plugin = out / "plugins" / "skill-craft"
        (plugin / "skills" / "shiploop").mkdir(parents=True)
        (plugin / "skills" / "shiploop" / "SKILL.md").write_text("built from " + self.git("rev-parse", "HEAD"))
        return plugin

    def scheduler_epoch(self, name, cases):
        plugin = self.temp / f"{name}-plugin"
        (plugin / "skills" / "shiploop").mkdir(parents=True)
        (plugin / "skills" / "shiploop" / "SKILL.md").write_text("scheduler fixture")
        driver = {"host": "codex", "model": "test-model", "effort": "high"}
        build = runner.tree_digest(plugin)
        registration = {
            "contract": "promotion/5", "purpose": "calibration",
            "cases": {case: {"role": "regression", "attempts": count} for case, count in cases.items()},
            "arms": {arm: {"shiploop_build": build, "driver": driver} for arm in ("control", "candidate")},
            "attempts": [{"id": f"{arm}-{case}-{number}", "arm": arm, "case": case}
                         for case, count in cases.items() for arm in ("control", "candidate")
                         for number in range(1, count + 1)],
            "qualification": boundary.qualification_snapshot(ROOT / "test" / "shiploop_e2e", list(cases)),
        }
        template = self.temp / f"{name}-registration.json"
        template.write_text(json.dumps(registration))
        root = self.temp / f"{name}-epoch"
        epoch.initialise(root, template)
        return root, {"control": plugin, "candidate": plugin}

    def run_scheduler(self, root, plugins, cleanup_by_case=None):
        spawned, started, finished, violations = [], [], set(), []
        active, previous = {}, {}
        cleanup_by_case = cleanup_by_case or {}

        class Child:
            def __init__(child, argv, **_kwargs):
                child.attempt_id = argv[argv.index("--attempt") + 1]
                child.output = None
                child.returncode = None
                child.polls = 0
                row = next(item for item in epoch.registration(root)["attempts"]
                           if item["id"] == child.attempt_id)
                child.case = row["case"]
                platform = runner.case_platform(child.case)
                child.target = (platform.get("kind"), platform.get("org")) if platform else None
                spawned.append(child.attempt_id)
                if child.target is not None:
                    if child.target in active:
                        violations.append(f"{child.attempt_id} spawned while {active[child.target]} was running")
                        child.returncode = 1
                        return
                    prior = previous.get(child.target)
                    if prior is not None:
                        try:
                            output, _receipt = epoch.sealed_run(root, prior)
                            cleanup = (json.loads((output / "result.json").read_text()).get("platform") or {}).get("cleanup")
                        except (OSError, ValueError):
                            cleanup = None
                        if (prior not in finished or not isinstance(cleanup, dict) or cleanup.get("ran") is not True
                                or cleanup.get("ok") is not True or cleanup.get("kept") is True):
                            violations.append(f"{child.attempt_id} started before {prior} had a sealed clean receipt")
                            child.returncode = 1
                            return
                    active[child.target] = child.attempt_id
                intent = epoch.launch_intent(root, child.attempt_id, plugins[row["arm"]])
                child.output = Path(intent["output"])
                started.append(child.attempt_id)

            def poll(child):
                if child.returncode is not None:
                    return child.returncode
                child.polls += 1
                if child.polls < 2:
                    return None
                child.output.mkdir()
                result = {"case": child.case, "pass": child.target is None}
                if child.target is not None:
                    cleanup = cleanup_by_case.get(child.case, {"ran": True, "ok": True})
                    if cleanup is not None:
                        result["platform"] = {"cleanup": cleanup}
                        platform_dir = child.output / "platform"
                        platform_dir.mkdir()
                        (platform_dir / "cleanup-record.json").write_text(json.dumps(cleanup))
                (child.output / "result.json").write_text(json.dumps(result))
                epoch.record_run(root, child.attempt_id)
                finished.add(child.attempt_id)
                if child.target is not None:
                    active.pop(child.target, None)
                    previous[child.target] = child.attempt_id
                child.returncode = 0
                return child.returncode

        ticks = 0
        def fast_sleep(_seconds):
            nonlocal ticks
            ticks += 1
            if ticks > 200:
                raise AssertionError("launch_all did not stop with only blocked targets pending")

        with mock.patch.object(cycle.subprocess, "Popen", side_effect=Child), \
                mock.patch.object(cycle.time, "sleep", side_effect=fast_sleep):
            cycle.launch_all(root, plugins, parallel=2, logs=root.parent / f"{root.name}-logs")
        return spawned, started, violations

    def launch_all(self, root, plugins, parallel, logs):
        for row in epoch.state(root)["attempts"]:
            intent = epoch.launch_intent(root, row["id"], plugins[row["arm"]])
            output = Path(intent["output"])
            output.mkdir()
            (output / "result.json").write_text(json.dumps({"case": row["case"], "pass": True}))
            epoch.record_run(root, row["id"])
        return []

    def run_cycle(self, decision="DROP", candidate_tokens=1_200_000, review=None, improver=None, launch=None,
                  builder=None, calibration=None):
        def cards(root):
            return (epoch.registration(root), json.loads((root / "prediction.json").read_text()),
                    [card("hello"), card("csv-report")], [card("hello", candidate_tokens), card("csv-report")])
        review = review or mock.Mock(return_value={"validity": {"status": "valid"}, "verdict": "aligned", "summary": "ok"})
        with mock.patch.object(iterate, "improve", side_effect=improver or self.improver()), \
                mock.patch.object(purpose_check, "review", review), \
                mock.patch.object(cycle, "build", side_effect=builder or self.build), \
                mock.patch.object(cycle, "launch_all", side_effect=launch or self.launch_all), \
                mock.patch.object(epoch, "decide", return_value={"decision": decision, "reasons": ["a stated reason"]}), \
                mock.patch.object(cycle.predictions, "_epoch_cards", side_effect=cards):
            result = cycle.qualify(self.worktree, "loop-test", self.record, self.temp / "out" / "cycle-1", self.args,
                                   calibration or self.calibration)
        return result, review

    def identical_build(self, worktree, out):
        plugin = self.temp / "identical-plugin"
        skill = plugin / "skills" / "shiploop"
        skill.mkdir(parents=True, exist_ok=True)
        (skill / "SKILL.md").write_text("same control and candidate build")
        return plugin

    def assert_early_learning(self, result, decision, record=None):
        record = record or self.record
        self.assertEqual(result["decision"], decision)
        self.assertEqual(self.git("status", "--porcelain"), "")
        message = self.git("log", "-1", "--format=%B")
        self.assertIn(record, message)
        self.assertIn(decision, message)
        lowered = message.lower()
        self.assertTrue(any(marker in lowered for marker in
                            ("unmeasured", "unknown measurement", "measurement unknown", "measurement: unknown")),
                        message)
        events = [row["event"] for row in lr.rows(self.ledger) if row["record"] == record]
        self.assertIn("rejected_at_purpose", events)

    def test_a_drop_keeps_the_candidate_as_a_ref_and_the_records_survive_the_reset(self):
        result, _ = self.run_cycle("DROP", 1_200_000)
        self.assertEqual(result["decision"], "DROP")
        self.assertEqual(self.git("rev-parse", "HEAD~1"), self.tip)
        candidate = self.git("rev-parse", f"refs/shiploop-loop/loop-test/{self.record}")
        self.assertNotEqual(candidate, self.tip)
        self.assertEqual((self.worktree / "skills/shiploop/scripts/x.py").read_text(), "x = 1\n")
        self.assertEqual(self.git("status", "--porcelain"), "")
        state = lr.current(self.ledger)[self.record]
        self.assertEqual((state["status"], state["decision"], state["verdict"]), ("refuted", "DROP", "refuted"))
        events = [row["event"] for row in lr.rows(self.ledger) if row["record"] == self.record]
        self.assertEqual(events[-3:], ["predicted", "decided", "verdict"])
        journal = (self.worktree / JOURNAL).read_text()
        self.assertIn(f"## Qualified cycle: {self.record}", journal)
        self.assertIn("kept as refs/shiploop-loop/loop-test/", journal)
        self.assertIn("| hello | tokens |", journal)
        message = self.git("log", "-1", "--format=%B")
        self.assertIn(self.tip, message)
        self.assertIn(candidate, message)
        self.assertIn(f"Learning-Record: {self.record}", message)
        self.assertIn(f"Candidate diff stat (`{self.tip}..{candidate}`)", message)
        self.assertIn("skills/shiploop/scripts/x.py", message)
        self.assertIn("UNADOPTED PROPOSAL", message.upper())
        self.assertIn("Decision DROP:", message)

    def test_a_promote_with_its_effect_observed_verifies_the_record_and_advances_the_tip(self):
        result, _ = self.run_cycle("PROMOTE", 800_000)
        self.assertEqual((result["decision"], result["verdict"]["verdict"]), ("PROMOTE", "confirmed"))
        message = self.git("log", "-1", "--format=%B")
        self.assertIn("Promoted candidate source — disposition: PROMOTE", message)
        self.assertNotIn("UNADOPTED PROPOSAL", message)
        self.assertNotEqual(self.git("rev-parse", "HEAD~1"), self.tip)
        self.assertEqual(self.git("rev-parse", "HEAD~2"), self.tip)
        self.assertEqual(lr.current(self.ledger)[self.record]["status"], "verified")

    def test_a_promote_the_prediction_does_not_explain_leaves_the_record_open(self):
        self.run_cycle("PROMOTE", 990_000)
        self.assertEqual(lr.current(self.ledger)[self.record]["status"], "unexplained_gain")

    def test_registration_binds_the_prediction_and_the_calibrated_attempts(self):
        self.run_cycle("DROP")
        root = self.temp / "out" / "cycle-1" / "epoch"
        registered = epoch.events(root)[0]
        self.assertIn("prediction_sha256", registered)
        reg = json.loads((root / "registration.json").read_text())
        self.assertEqual(reg["cases"], {"hello": {"role": "regression", "attempts": 1},
                                        "csv-report": {"role": "regression", "attempts": 1}})
        self.assertEqual((reg["efficiency"], reg["tolerance"], reg["purpose"]), (["tokens"], 0.10, "product_change"))

    def test_a_misaligned_purpose_rejects_before_any_run(self):
        review = mock.Mock(return_value={"validity": {"status": "valid"}, "verdict": "misaligned", "summary": "a rename"})
        result, _ = self.run_cycle(review=review)
        self.assert_early_learning(result, "REJECTED_AT_PURPOSE")
        self.assertFalse((self.temp / "out" / "cycle-1" / "epoch").exists())
        self.assertEqual(self.git("rev-parse", "HEAD^1"), self.tip)
        self.assertEqual(self.git("show", "HEAD:skills/shiploop/scripts/x.py"), "x = 1")
        message = self.git("log", "-1", "--format=%B")
        self.assertIn("UNADOPTED PROPOSAL", message.upper())
        self.assertIn("Decision REJECTED_AT_PURPOSE:", message)
        self.assertEqual(lr.current(self.ledger)[self.record]["status"], "deferred")

    def test_an_improver_with_no_candidate_commits_the_rejection_and_unknown_measurement(self):
        def no_candidate(worktree, findings, stage, args, prompt=None):
            return {"process": {"status": "exited"}, "report": {}, "base": self.git("rev-parse", "HEAD"),
                    "commits": [], "changed": [], "out_of_scope": [],
                    "uncommitted": self.git("status", "--porcelain").splitlines(), "withheld": [],
                    "held_out_named": 0, "grading": {"changed": []}}

        result, _ = self.run_cycle(improver=no_candidate)
        self.assert_early_learning(result, "NO_CANDIDATE")

    def test_an_unusable_committed_candidate_keeps_its_identity_without_adopting_its_source(self):
        candidate = []
        improve = self.improver()

        def out_of_scope(worktree, findings, stage, args, prompt=None):
            change = improve(worktree, findings, stage, args, prompt)
            candidate.append(change["commits"][-1])
            change["out_of_scope"] = ["another file"]
            return change

        result, _ = self.run_cycle(improver=out_of_scope)
        self.assert_early_learning(result, "NO_CANDIDATE")
        message = self.git("log", "-1", "--format=%B")
        self.assertIn(candidate[0], message)
        self.assertIn("Improve artifacts remain at", message)
        self.assertNotIn("Candidate source (full commit message", message)
        self.assertNotIn("Candidate diff stat", message)
        self.assertEqual(self.git("rev-parse", "HEAD^1"), self.tip)
        self.assertEqual(self.git("show", "HEAD:skills/shiploop/scripts/x.py"), "x = 1")

    def test_an_unusable_prediction_commits_the_rejection_and_unknown_measurement(self):
        invalid_prediction = {**self.prediction,
                              "effects": [{**self.prediction["effects"][0], "measure": "not-registered"}]}
        result, _ = self.run_cycle(improver=self.improver(prediction=invalid_prediction))
        self.assert_early_learning(result, "NO_PREDICTION")

    def test_a_refused_registration_commits_the_rejection_and_unknown_measurement(self):
        result, _ = self.run_cycle(builder=self.identical_build)
        self.assert_early_learning(result, "REFUSED")

    def test_a_rejected_cycle_cannot_make_the_next_candidate_look_uncommitted(self):
        next_record = lr.new_id()
        lr.append("opened", next_record, self.ledger, title="the other admitted lesson",
                  anchor={"clause_id": "S-14", "relationship": "supports"}, materiality="material",
                  confidence="high", target="shiploop", files=["skills/shiploop/scripts/x.py"], proposal="say so")
        lr.append("admitted", next_record, self.ledger)
        self.git("add", f"test/shiploop_e2e/{lr.LEDGER.name}")
        self.git("commit", "-qm", "seed second admitted record")
        self.tip = self.git("rev-parse", "HEAD")

        def no_candidate(worktree, findings, stage, args, prompt=None):
            return {"process": {"status": "exited"}, "report": {}, "base": self.git("rev-parse", "HEAD"),
                    "commits": [], "changed": [], "out_of_scope": [],
                    "uncommitted": self.git("status", "--porcelain").splitlines(), "withheld": [],
                    "held_out_named": 0, "grading": {"changed": []}}

        first, _ = self.run_cycle(improver=no_candidate)
        self.assertEqual(first["decision"], "NO_CANDIDATE")
        second_args = argparse.Namespace(**vars(self.args))
        with mock.patch.object(iterate, "improve", side_effect=self.improver(record=next_record)), \
                mock.patch.object(purpose_check, "review", mock.Mock(return_value={
                    "validity": {"status": "valid"}, "verdict": "aligned", "summary": "ok"})), \
                mock.patch.object(cycle, "build", side_effect=self.identical_build):
            second = cycle.qualify(self.worktree, "loop-test", next_record, self.temp / "out" / "cycle-2",
                                   second_args, self.calibration)

        self.assertNotEqual(second["decision"], "NO_CANDIDATE",
                            "the previous cycle's rejected ledger append looked like improver work")
        self.assert_early_learning(second, "REFUSED", next_record)
        events = {(row["record"], row["event"]) for row in lr.rows(self.ledger)}
        self.assertIn((self.record, "rejected_at_purpose"), events)
        self.assertIn((next_record, "rejected_at_purpose"), events)

    def test_an_unexpected_launch_exception_preserves_prediction_and_does_not_poison_the_next_record(self):
        next_record = lr.new_id()
        lr.append("opened", next_record, self.ledger, title="the other admitted lesson",
                  anchor={"clause_id": "S-14", "relationship": "supports"}, materiality="material",
                  confidence="high", target="shiploop", files=["skills/shiploop/scripts/x.py"], proposal="say so")
        lr.append("admitted", next_record, self.ledger)
        self.git("add", f"test/shiploop_e2e/{lr.LEDGER.name}")
        self.git("commit", "-qm", "seed second admitted record")
        self.tip = self.git("rev-parse", "HEAD")

        candidate = []
        improve = self.improver()

        def tracked_improver(worktree, findings, stage, args, prompt=None):
            change = improve(worktree, findings, stage, args, prompt)
            candidate.append(change["commits"][-1])
            return change

        def fail_after_prediction(root, plugins, parallel, logs):
            self.assertIn((self.record, "predicted"),
                          {(row["record"], row["event"]) for row in lr.rows(self.ledger)})
            raise RuntimeError("unexpected launch failure sentinel")

        with self.assertRaisesRegex(RuntimeError, "unexpected launch failure sentinel"):
            self.run_cycle(improver=tracked_improver, launch=fail_after_prediction)

        first_events = {(row["record"], row["event"]) for row in lr.rows(self.ledger)}
        self.assertIn((self.record, "predicted"), first_events)
        self.assertEqual(self.git("status", "--porcelain"), "")
        committed_rows = [json.loads(line) for line in self.git(
            "show", f"HEAD:test/shiploop_e2e/{lr.LEDGER.name}").splitlines()]
        self.assertIn((self.record, "predicted"), {(row["record"], row["event"]) for row in committed_rows})
        self.assertEqual(self.git("rev-parse", "HEAD^1"), self.tip)
        self.assertEqual(self.git("show", "HEAD:skills/shiploop/scripts/x.py"), "x = 1")
        self.assertNotEqual(candidate[0], self.git("rev-parse", "HEAD"))
        self.assertEqual(self.git("rev-parse", f"refs/shiploop-loop/loop-test/{self.record}"), candidate[0])
        self.assertFalse((self.temp / "out" / "cycle-1" / "cycle-result.json").exists())
        self.assertTrue((self.temp / "out" / "cycle-1" / f"interrupted-ledger-{self.record}.jsonl").is_file())
        self.assertTrue((self.temp / "out" / "cycle-1" / f"interrupted-exception-{self.record}.txt").is_file())
        interruption = self.git("log", "-1", "--format=%B")
        self.assertIn("Decision INTERRUPTED:", interruption)
        self.assertIn("unknown/incomplete", interruption.lower())
        self.assertIn(str(self.temp / "out" / "cycle-1" / "epoch"), interruption)
        self.assertNotIn("Improvement remains unmeasured", interruption)

        improve_second = self.improver(line="x = 3  # other record candidate\n", record=next_record)
        second_status = []

        def observe_second_status(worktree, findings, stage, args, prompt=None):
            change = improve_second(worktree, findings, stage, args, prompt)
            second_status.append(change["uncommitted"])
            return change

        second_args = argparse.Namespace(**vars(self.args))
        with mock.patch.object(iterate, "improve", side_effect=observe_second_status), \
                mock.patch.object(purpose_check, "review", mock.Mock(return_value={
                    "validity": {"status": "valid"}, "verdict": "aligned", "summary": "ok"})), \
                mock.patch.object(cycle, "build", side_effect=self.identical_build):
            second = cycle.qualify(self.worktree, "loop-test", next_record, self.temp / "out" / "cycle-2",
                                    second_args, self.calibration)

        self.assertEqual(second["decision"], "REFUSED")
        self.assertEqual(second_status, [[]], "prior cycle bookkeeping must be committed before the next improver")
        self.assertEqual(self.git("status", "--porcelain"), "")
        events = {(row["record"], row["event"]) for row in lr.rows(self.ledger)}
        self.assertIn((self.record, "predicted"), events)
        self.assertIn((next_record, "rejected_at_purpose"), events)

    def test_a_candidate_subject_cannot_claim_harness_completion(self):
        improve = self.improver()

        def misleading_candidate(worktree, findings, stage, args, prompt=None):
            change = improve(worktree, findings, stage, args, prompt)
            self.git("commit", "--amend", "-qm",
                     f"test(e2e): qualified cycle for {self.record}: PROMOTE\n\nLearning-Record: {self.record}")
            change["commits"] = [self.git("rev-parse", "HEAD")]
            return change

        def interrupted(*args):
            raise RuntimeError("misleading candidate subject sentinel")

        with self.assertRaisesRegex(RuntimeError, "misleading candidate subject sentinel"):
            self.run_cycle(improver=misleading_candidate, launch=interrupted)
        self.assertEqual(self.git("show", "HEAD:skills/shiploop/scripts/x.py"), "x = 1")
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertIn("INTERRUPTED", self.git("log", "-1", "--format=%B"))

    def test_an_interruption_recording_failure_preserves_the_original_error_and_backup(self):
        def interrupted(*args):
            raise RuntimeError("original launch failure")

        with mock.patch.object(cycle, "commit_entry", side_effect=OSError("learning commit failed")):
            with self.assertRaisesRegex(RuntimeError, "original launch failure"):
                self.run_cycle(launch=interrupted)

        stage = self.temp / "out" / "cycle-1"
        backup = stage / f"interrupted-ledger-{self.record}.jsonl"
        self.assertIn("predicted", [json.loads(line)["event"] for line in backup.read_text().splitlines()])
        diagnostic = (stage / f"interrupted-exception-{self.record}.txt").read_text()
        self.assertIn("original launch failure", diagnostic)
        self.assertIn("learning commit failed", diagnostic)
        self.assertIn("recovery is incomplete", diagnostic)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.tip)
        self.assertNotEqual(self.git("status", "--porcelain"), "")
        with self.assertRaisesRegex(ValueError, "clean worktree"):
            cycle.qualify(self.worktree, "loop-test", self.record, self.temp / "out" / "next-cycle",
                          self.args, self.calibration)
        self.assertTrue(backup.exists())

    def test_a_late_output_error_preserves_the_completed_promotion_and_learning(self):
        write_text = Path.write_text

        def fail_cycle_result(path, *args, **kwargs):
            if path.name == "cycle-result.json":
                raise OSError("late result write failure")
            return write_text(path, *args, **kwargs)

        with mock.patch.object(Path, "write_text", autospec=True, side_effect=fail_cycle_result):
            with self.assertRaisesRegex(OSError, "late result write failure"):
                self.run_cycle(decision="PROMOTE", candidate_tokens=800_000)

        self.assertEqual(self.git("status", "--porcelain"), "")
        message = self.git("log", "-1", "--format=%B")
        self.assertIn(f"qualified cycle for {self.record}: PROMOTE", message)
        self.assertFalse(any(row["event"] == "deferred" for row in lr.rows(self.ledger)))
        self.assertFalse((self.temp / "out" / "cycle-1" / f"interrupted-ledger-{self.record}.jsonl").exists())

    def test_qualify_refuses_a_dirty_initial_worktree_without_resetting_it(self):
        self.write("local-edit.txt", "keep this caller change\n")
        head = self.git("rev-parse", "HEAD")
        with self.assertRaisesRegex(ValueError, "clean worktree"):
            cycle.qualify(self.worktree, "loop-test", self.record, self.temp / "out" / "dirty-cycle",
                          self.args, self.calibration)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertEqual((self.worktree / "local-edit.txt").read_text(), "keep this caller change\n")
        self.assertIn("local-edit.txt", self.git("status", "--porcelain"))

    def test_interrupted_valid_but_rewritten_ledger_cannot_replace_accepted_history(self):
        backup = self.temp / "out" / "cycle-1" / f"interrupted-ledger-{self.record}.jsonl"
        expected_history = {(self.record, "opened"), (self.record, "admitted")}

        def rewrite_ledger_after_prediction(root, plugins, parallel, logs):
            predicted = [row for row in lr.rows(self.ledger)
                         if row["record"] == self.record and row["event"] == "predicted"]
            self.assertEqual(len(predicted), 1)
            self.ledger.write_text(json.dumps(predicted[0]) + "\n")
            raise RuntimeError("ledger rewrite failure sentinel")

        with self.assertRaisesRegex(RuntimeError, "ledger rewrite failure sentinel"):
            self.run_cycle(launch=rewrite_ledger_after_prediction)

        self.assertTrue(backup.is_file())
        backed_up_rows = [json.loads(line) for line in backup.read_text().splitlines()]
        self.assertEqual([(row["record"], row["event"]) for row in backed_up_rows], [(self.record, "predicted")])
        retained = {(row["record"], row["event"]) for row in lr.rows(self.ledger)}
        self.assertTrue(expected_history.issubset(retained))
        self.assertIn((self.record, "deferred"), retained)
        self.assertNotIn((self.record, "predicted"), retained)
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertIn("Decision INTERRUPTED:", self.git("log", "-1", "--format=%B"))

    def test_qualify_refuses_an_existing_stage_without_rewriting_its_evidence(self):
        stage = self.temp / "out" / "existing-cycle"
        stage.mkdir(parents=True)
        prior_receipt = stage / "epoch" / "ledger.jsonl"
        prior_receipt.parent.mkdir()
        prior_receipt.write_text("preserve prior epoch evidence\n")
        head = self.git("rev-parse", "HEAD")

        with self.assertRaisesRegex(FileExistsError, "stage already exists"):
            cycle.qualify(self.worktree, "loop-test", self.record, stage, self.args, self.calibration)

        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual(prior_receipt.read_text(), "preserve prior epoch evidence\n")

    def test_an_invalid_discovery_review_is_committed_after_exploration(self):
        tip = self.git("rev-parse", "HEAD")
        explore_args = argparse.Namespace(**{**vars(self.args), "host": iterate.hosts.RUN_DEFAULT_HOST,
                                             "permission_mode": "auto"})

        def run_with_known_metrics(argv):
            run_dir = Path(argv[argv.index("--output") + 1])
            run_dir.mkdir(parents=True)
            (run_dir / "result.json").write_text(json.dumps({
                "process": {"elapsed_seconds": 4.5},
                "cli": {"num_turns": 19, "cost_usd": None},
                "checks": [{"pass": True}],
            }))
            return 0

        review = mock.Mock(return_value={"validity": {"discovery_qualified": False, "status": "invalid",
                                                       "reason": "review receipt is incomplete"},
                                        "outcome": "invalid review sentinel"})
        with mock.patch.object(cycle, "build", side_effect=self.build), \
                mock.patch.object(runner, "main", side_effect=run_with_known_metrics), \
                mock.patch.object(reviewer, "review", review):
            opened = cycle.explore(self.worktree, self.temp / "out" / "explore", explore_args)

        self.assertEqual(opened, [])
        review.assert_called_once()
        self.assertNotEqual(self.git("rev-parse", "HEAD"), tip)
        self.assertEqual(self.git("status", "--porcelain"), "")
        message = self.git("log", "-1", "--format=%B")
        self.assertIn("invalid review", message.lower())
        self.assertIn("review receipt is incomplete", message)
        self.assertIn("19 turns", message)
        self.assertIn("host elapsed 4.5 seconds", message)
        self.assertIn("1/1 checks passed", message)
        self.assertIn("cost unknown (reported cost_usd is null)", message)
        self.assertIn("Product comparison.", message)
        self.assertIn("Improvement remains unmeasured", message)

    def test_a_probe_word_rejects_without_asking_the_review(self):
        result, review = self.run_cycle(improver=self.improver("x = 2  # sink the fleet\n"))
        self.assertEqual(result["decision"], "REJECTED_AT_PURPOSE")
        review.assert_not_called()
        self.assertIn("S-13", result["reasons"][0])

    def test_an_unsealed_attempt_is_reconciled_never_relaunched_and_the_tip_stays(self):
        def partial(root, plugins, parallel, logs):
            rows = epoch.state(root)["attempts"]
            epoch.launch_intent(root, rows[0]["id"], plugins[rows[0]["arm"]])
            return [rows[0]["id"]]
        result, _ = self.run_cycle(launch=partial)
        self.assertEqual(result["decision"], "UNKNOWN_LAUNCH")
        self.assertIn("never retry", result["reasons"][0])
        self.assertEqual(self.git("rev-parse", "HEAD~1"), self.tip)

    def test_launch_all_serializes_same_org_attempts_until_a_clean_receipt_is_sealed(self):
        cases = {"chess-salesforce": 1, "battleship-salesforce": 1, "hello": 1}
        root, plugins = self.scheduler_epoch("clean-target-queue", cases)
        chess = runner.case_platform("chess-salesforce")
        battleship = runner.case_platform("battleship-salesforce")
        self.assertEqual((chess["kind"], chess["org"]), (battleship["kind"], battleship["org"]))
        self.assertNotEqual(chess["prefix"], battleship["prefix"])

        spawned, started, violations = self.run_scheduler(root, plugins)

        attempts = epoch.registration(root)["attempts"]
        expected = {row["id"] for row in attempts}
        self.assertEqual(violations, [])
        self.assertEqual(set(spawned), expected)
        self.assertEqual(set(started), expected)
        self.assertEqual({row["attempt_id"] for row in epoch.events(root) if row["kind"] == "launch_intent"}, expected)
        self.assertTrue(all(row["status"] == "recorded" for row in epoch.state(root)["attempts"]))

    def test_launch_all_leaves_unclean_targets_queued_while_other_targets_and_local_runs_complete(self):
        cases = {"chess-salesforce": 2, "battleship-salesforce": 2, "csv-report": 2, "hello": 1}
        root, plugins = self.scheduler_epoch("blocked-target-queue", cases)
        real_case_platform = runner.case_platform
        base = real_case_platform("chess-salesforce")
        declarations = {
            "chess-salesforce": {**base, "org": "org-a"},
            "battleship-salesforce": {**base, "org": "org-b", "prefix": "SLBattle"},
            "csv-report": {**base, "org": "org-c", "prefix": "SLReport"},
        }
        cleanup = {"chess-salesforce": None,
                   "battleship-salesforce": {"ran": True, "ok": False},
                   "csv-report": {"ran": True, "ok": True, "kept": True}}

        def declared_target(case):
            return declarations.get(case, real_case_platform(case))

        with mock.patch.object(runner, "case_platform", side_effect=declared_target):
            spawned, started, violations = self.run_scheduler(root, plugins, cleanup)

        attempts = epoch.registration(root)["attempts"]
        launch_intents = {row["attempt_id"] for row in epoch.events(root) if row["kind"] == "launch_intent"}
        states = {row["id"]: row["status"] for row in epoch.state(root)["attempts"]}
        for case in declarations:
            launched = [row["id"] for row in attempts if row["case"] == case and row["id"] in started]
            self.assertEqual(len(launched), 1, case)
            self.assertEqual(len([attempt for attempt in spawned
                                  if f"-{case}-" in f"-{attempt}-"]), 1, case)
            for row in attempts:
                if row["case"] == case and row["id"] != launched[0]:
                    self.assertNotIn(row["id"], launch_intents)
                    self.assertEqual(states[row["id"]], "not_launched")
        local = {row["id"] for row in attempts if row["case"] == "hello"}
        self.assertTrue(local.issubset(set(started)))
        self.assertTrue(all(states[attempt] == "recorded" for attempt in local))
        self.assertTrue(all(states[attempt] == "recorded" for attempt in started))
        self.assertEqual(violations, [])

    def test_a_case_is_capability_only_when_the_prediction_raises_its_floor(self):
        self.assertEqual(cycle.roles_for(self.prediction, "hello", "csv-report"),
                         {"hello": "regression", "csv-report": "regression"})
        raised = {**self.prediction, "effects": [{"case": "hello", "measure": "accuracy", "direction": "up",
                                                  "at_least": 0.3}]}
        self.assertEqual(cycle.roles_for(raised, "hello", None), {"hello": "capability"})

    def test_a_calibration_from_other_scoring_files_or_without_a_tolerance_is_refused(self):
        catalog = json.loads((ROOT / "test" / "shiploop_e2e" / "cases.json").read_text())
        report = {"contract": spread.CONTRACT, "cases": {case: {} for case in CASES},
                  "scoring": spread.scoring_digest({case: catalog[case] for case in CASES}),
                  "recommended": {"attempts": 3, "tolerance": 0.2, "metric": "tokens"}}
        path = self.temp / "calibration.json"
        path.write_text(json.dumps(report))
        self.assertEqual(cycle.load_calibration(path, list(CASES))["tolerance"], 0.2)
        with self.assertRaisesRegex(ValueError, "did not calibrate"):
            cycle.load_calibration(path, ["hello", "battleship"])
        path.write_text(json.dumps({**report, "scoring": {**report["scoring"], "sha256": "0" * 64}}))
        with self.assertRaisesRegex(ValueError, "changed since the calibration"):
            cycle.load_calibration(path, list(CASES))
        path.write_text(json.dumps({**report, "recommended": {"attempts": 3, "tolerance": None, "metric": "tokens",
                                                              "why": "too loose"}}))
        with self.assertRaisesRegex(ValueError, "cannot decide"):
            cycle.load_calibration(path, list(CASES))

    # Owner decision, 2026-10-31: with no calibration, the owner states the tolerance and attempts, and every record
    # says they were not measured.

    @staticmethod
    def stated(**given):
        return argparse.Namespace(**{"calibration": None, "tolerance": None, "attempts": None, **given})

    def test_a_stated_basis_is_explicit_checked_and_never_mixed_with_a_measurement(self):
        stated = cycle.resolve_calibration(self.stated(tolerance=0.25, attempts=3), list(CASES))
        self.assertEqual((stated["attempts"], stated["tolerance"], stated["metric"], stated["measured"], stated["basis"]),
                         (3, 0.25, "tokens", False, cycle.UNMEASURED))
        for given in (self.stated(), self.stated(tolerance=0.25), self.stated(attempts=3)):
            with self.subTest(given=vars(given)), self.assertRaisesRegex(ValueError, "needs --calibration"):
                cycle.resolve_calibration(given, list(CASES))
        with self.assertRaisesRegex(ValueError, "do not also pass"):
            cycle.resolve_calibration(self.stated(calibration=Path("report.json"), tolerance=0.25), list(CASES))
        for given, why in ((self.stated(tolerance=0, attempts=3), "above 0"),
                           (self.stated(tolerance=1.5, attempts=3), "at most 1"),
                           (self.stated(tolerance=float("nan"), attempts=3), "above 0"),
                           (self.stated(tolerance=0.25, attempts=0), "positive whole"),
                           (self.stated(tolerance=0.25, attempts=True), "positive whole")):
            with self.subTest(why=why, given=vars(given)), self.assertRaisesRegex(ValueError, why):
                cycle.resolve_calibration(given, list(CASES))

    def test_an_unmeasured_cycle_says_so_in_its_events_its_record_and_its_journal(self):
        result, _ = self.run_cycle("PROMOTE", 800_000, calibration=cycle.stated_calibration(1, 0.10))
        self.assertEqual(result["decision"], "PROMOTE")
        events = {row["event"]: row for row in lr.rows(self.ledger) if row["record"] == self.record}
        self.assertEqual(events["decided"]["calibration"], cycle.UNMEASURED)
        self.assertEqual(events["verdict"]["calibration"], cycle.UNMEASURED)
        self.assertIn("tolerance and attempts stated, not measured", events["verdict"]["reason"])
        self.assertEqual(lr.current(self.ledger)[self.record]["status"], "verified")
        journal = (self.worktree / JOURNAL).read_text()
        self.assertIn("stated, not measured: the false-decision rate is unknown", journal)
        self.assertNotIn("calibration None", journal)

    def test_a_measured_cycle_is_not_labelled_unmeasured(self):
        self.run_cycle("PROMOTE", 800_000)
        events = {row["event"]: row for row in lr.rows(self.ledger) if row["record"] == self.record}
        self.assertEqual(events["decided"]["calibration"], self.calibration["sha256"])
        self.assertNotIn("calibration", events["verdict"])
        self.assertNotIn("stated, not measured", (self.worktree / JOURNAL).read_text())

    def test_an_early_exit_under_an_unmeasured_basis_says_so_in_its_commit(self):
        review = mock.Mock(return_value={"validity": {"status": "valid"}, "verdict": "misaligned", "summary": "a rename"})
        result, _ = self.run_cycle(review=review, calibration=cycle.stated_calibration(3, 0.25))
        self.assertEqual(result["decision"], "REJECTED_AT_PURPOSE")
        message = self.git("log", "-1", "--format=%B")
        self.assertIn("3 attempts per arm, tolerance 0.25", message)
        self.assertIn("stated, not measured: the false-decision rate is unknown", message)
        self.assertNotIn("SHA256 `None`", message)


if __name__ == "__main__":
    unittest.main()
