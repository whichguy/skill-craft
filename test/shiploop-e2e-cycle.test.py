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
import cycle
import epoch
import iterate
import learning_records as lr
import purpose_check
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

    def improver(self, line="x = 2  # an unattended run records the default and proceeds\n"):
        def improve(worktree, findings, stage, args, prompt=None):
            self.assertIn(f"Learning-Record: {self.record}", prompt)
            self.assertIn('"prediction"', prompt)
            stage.mkdir()
            self.write("skills/shiploop/scripts/x.py", line)
            self.git("commit", "-qam", f"fix\n\nLearning-Record: {self.record}")
            return {"process": {"status": "exited"}, "report": {"prediction": self.prediction}, "base": self.tip,
                    "commits": [self.git("rev-parse", "HEAD")], "changed": ["skills/shiploop/scripts/x.py"],
                    "out_of_scope": [], "uncommitted": [], "withheld": [], "held_out_named": 0,
                    "grading": {"changed": []}}
        return improve

    def build(self, worktree, out):
        plugin = out / "plugins" / "skill-craft"
        (plugin / "skills" / "shiploop").mkdir(parents=True)
        (plugin / "skills" / "shiploop" / "SKILL.md").write_text("built from " + self.git("rev-parse", "HEAD"))
        return plugin

    def launch_all(self, root, plugins, parallel, logs):
        for row in epoch.state(root)["attempts"]:
            intent = epoch.launch_intent(root, row["id"], plugins[row["arm"]])
            output = Path(intent["output"])
            output.mkdir()
            (output / "result.json").write_text(json.dumps({"case": row["case"], "pass": True}))
            epoch.record_run(root, row["id"])
        return []

    def run_cycle(self, decision="DROP", candidate_tokens=1_200_000, review=None, improver=None, launch=None):
        def cards(root):
            return (epoch.registration(root), json.loads((root / "prediction.json").read_text()),
                    [card("hello"), card("csv-report")], [card("hello", candidate_tokens), card("csv-report")])
        review = review or mock.Mock(return_value={"validity": {"status": "valid"}, "verdict": "aligned", "summary": "ok"})
        with mock.patch.object(iterate, "improve", side_effect=improver or self.improver()), \
                mock.patch.object(purpose_check, "review", review), \
                mock.patch.object(cycle, "build", side_effect=self.build), \
                mock.patch.object(cycle, "launch_all", side_effect=launch or self.launch_all), \
                mock.patch.object(epoch, "decide", return_value={"decision": decision, "reasons": ["a stated reason"]}), \
                mock.patch.object(cycle.predictions, "_epoch_cards", side_effect=cards):
            result = cycle.qualify(self.worktree, "loop-test", self.record, self.temp / "out" / "cycle-1", self.args,
                                   self.calibration)
        return result, review

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

    def test_a_promote_with_its_effect_observed_verifies_the_record_and_advances_the_tip(self):
        result, _ = self.run_cycle("PROMOTE", 800_000)
        self.assertEqual((result["decision"], result["verdict"]["verdict"]), ("PROMOTE", "confirmed"))
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
        self.assertEqual(result["decision"], "REJECTED_AT_PURPOSE")
        self.assertFalse((self.temp / "out" / "cycle-1" / "epoch").exists())
        self.assertEqual(self.git("rev-parse", "HEAD"), self.tip)
        self.assertEqual(lr.current(self.ledger)[self.record]["status"], "deferred")

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


if __name__ == "__main__":
    unittest.main()
