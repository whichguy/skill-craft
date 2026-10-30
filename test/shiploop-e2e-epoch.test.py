"""No-model controller fixtures: receipts, interrupted dispatch, source drift and qualification routing."""
from __future__ import annotations

import contextlib
import io
import json
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
import epoch
import hosts
import judge
import review
import run as runner


class EpochTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.root = self.temp / "epoch"
        self.plugin = self.temp / "plugin"
        (self.plugin / "skills" / "shiploop").mkdir(parents=True)
        (self.plugin / "skills" / "shiploop" / "SKILL.md").write_text("a fixture plugin")
        build = runner.tree_digest(self.plugin)
        self.reg = {"contract": "promotion/5", "purpose": "calibration",
                    "cases": {"hello": {"role": "regression", "attempts": 1}},
                    "arms": {arm: {"shiploop_build": build, "driver": hosts.ROLE_DEFAULTS["subject"]}
                             for arm in ("control", "candidate")},
                    "attempts": [{"id": arm + "-hello", "arm": arm, "case": "hello"}
                                 for arm in ("control", "candidate")]}
        self.template = self.temp / "template.json"
        self.template.write_text(json.dumps(self.reg))
        epoch.initialise(self.root, self.template)

    def intent(self, arm="control"):
        return epoch.launch_intent(self.root, arm + "-hello", self.plugin)

    def completed(self, arm="control"):
        intent = self.intent(arm)
        output = Path(intent["output"])
        output.mkdir()
        (output / "result.json").write_text(json.dumps({"case": "hello", "pass": False}))
        return epoch.record_run(self.root, arm + "-hello")

    def test_init_records_profiles_and_printing_next_starts_nothing(self):
        original = (self.root / epoch.LEDGER).read_bytes()
        with mock.patch.object(runner, "main", side_effect=AssertionError("must not launch")):
            self.assertEqual(epoch.next_action(self.root)["action"], "launch")
            self.assertEqual(epoch.state(self.root)["publication"], "not_performed")
        self.assertEqual((self.root / epoch.LEDGER).read_bytes(), original)
        self.assertEqual(json.loads((self.root / "roles.json").read_text())["improver"]["model"], "gpt-6.1-sol")

    def test_crash_after_intent_blocks_a_duplicate_dispatch(self):
        self.intent()
        self.assertEqual(epoch.next_action(self.root)["action"], "reconcile")
        with self.assertRaisesRegex(ValueError, "already dispatched"):
            self.intent()
        with self.assertRaisesRegex(ValueError, "remains unknown"):
            epoch.record_run(self.root, "control-hello")
        self.assertEqual(len([r for r in epoch.events(self.root) if r["kind"] == "launch_intent"]), 1)

    def test_runner_is_dispatched_only_after_durable_intent(self):
        def fake(argv):
            self.assertEqual(epoch.events(self.root)[-1]["kind"], "launch_intent")
            output = Path(argv[argv.index("--output") + 1])
            output.mkdir()
            (output / "result.json").write_text('{"pass": false}')
            self.assertEqual(argv[argv.index("--model") + 1], "gpt-6.1-terra")
            return 1
        with mock.patch.object(runner, "main", side_effect=fake):
            epoch.launch(self.root, "control-hello", self.plugin)
        self.assertEqual(epoch.state(self.root)["attempts"][0]["status"], "recorded")
        self.assertEqual([r["returncode"] for r in epoch.events(self.root) if r["kind"] == "runner_returned"], [1])

    def test_ambiguous_dispatch_can_reconcile_a_retained_result_once(self):
        record = self.completed()
        self.assertIn("result.json", record["files"])
        with self.assertRaisesRegex(ValueError, "already sealed"):
            epoch.record_run(self.root, "control-hello")

    def test_partial_result_of_running_harness_is_not_sealed(self):
        intent = self.intent()
        Path(intent["output"]).mkdir()
        (Path(intent["output"]) / "result.json").write_text('{}')
        with mock.patch.object(epoch.listeners, "case_alive", return_value=True), \
                self.assertRaisesRegex(ValueError, "still running"):
            epoch.record_run(self.root, "control-hello")

    def test_changed_plugin_cannot_start_an_attempt(self):
        (self.plugin / "skills" / "shiploop" / "SKILL.md").write_text("changed candidate")
        with self.assertRaisesRegex(ValueError, "registered ShipLoop build"):
            self.intent()
        self.assertEqual(epoch.next_action(self.root)["action"], "launch")

    def test_changed_sealed_result_is_not_accepted(self):
        self.completed()
        (self.root / "runs" / "control-hello" / "result.json").write_text('{"pass": true}')
        with self.assertRaisesRegex(ValueError, "sealed attempt evidence changed"):
            epoch.sealed_run(self.root, "control-hello")

    def test_post_seal_product_or_review_evidence_changes_are_unknown(self):
        self.completed()
        output = self.root / "runs" / "control-hello"
        (output / "work").mkdir()
        (output / "work" / "app.py").write_text("changed after run")
        self.assertEqual(epoch.state(self.root)["attempts"][0]["status"], "invalid_evidence")
        self.assertEqual(epoch.next_action(self.root)["action"], "new_registration")
        self.assertEqual(epoch.decide(self.root)["decision"], "UNDECIDED")

    def test_registration_and_role_mutation_are_detected(self):
        (self.root / "roles.json").write_text('{}')
        with self.assertRaisesRegex(ValueError, "frozen roles.json changed"):
            epoch.state(self.root)

    def test_frozen_scorer_drift_blocks_resume(self):
        real = boundary.qualification_snapshot
        def changed(*args, **kwargs):
            snapshot = real(*args, **kwargs)
            return {**snapshot, "sha256": "0" * 64}
        with mock.patch.object(boundary, "qualification_snapshot", side_effect=changed), \
                self.assertRaisesRegex(ValueError, "inputs changed"):
            epoch.next_action(self.root)

    def test_missing_attempts_remain_undecided_not_complete(self):
        result = epoch.decide(self.root)
        self.assertEqual(result["decision"], "UNDECIDED")
        self.assertEqual(epoch.next_action(self.root)["action"], "launch")

    def assessment(self, *, valid=True, discoveries=None):
        payload = {"version": 2, "outcome": "Fixture observation", "learnings": [],
                   "missing_considerations": [], "optimizations": [], "harness": {},
                   "discoveries": discoveries or []}
        payload["validity"] = review.validity(payload, {"status": "exited", "returncode": 0})
        verdict = {"validity": {"status": "valid" if valid else "failed"},
                   "assessments": [{"id": d["id"], "status": "unknown", "reason": "Needs an experiment",
                                    "evidence": ["result.json"], "disposition": "investigate"}
                                   for d in payload["discoveries"]]}
        return payload, verdict

    def test_review_uses_separate_roles_and_seals_a_qualified_assessment(self):
        self.completed()
        payload, verdict = self.assessment()
        with mock.patch.object(review, "review", return_value=payload) as reviewer, \
                mock.patch.object(judge, "judge", return_value=verdict) as independent:
            event = epoch.review_attempt(self.root, "control-hello")
        self.assertEqual(event["kind"], "reviewed")
        self.assertEqual(reviewer.call_args.kwargs["model"], "gpt-6-astra")
        self.assertEqual(independent.call_args.kwargs["model"], "gpt-6-astra")
        self.assertEqual(reviewer.call_args.kwargs["assessment_id"], independent.call_args.kwargs["assessment_id"])
        self.assertEqual(epoch.next_action(self.root)["attempt_id"], "candidate-hello")
        with self.assertRaisesRegex(ValueError, "already recorded"):
            epoch.review_attempt(self.root, "control-hello")
        (self.root / event["receipt"]).write_text("{}")
        self.assertEqual(epoch.next_action(self.root)["action"], "review")

    def test_failed_judgment_retains_exposure_and_needs_a_fresh_assessment(self):
        self.completed()
        payload, verdict = self.assessment(valid=False)
        with mock.patch.object(review, "review", return_value=payload) as reviewer, \
                mock.patch.object(judge, "judge", return_value=verdict):
            self.assertEqual(epoch.review_attempt(self.root, "control-hello")["kind"], "review_incomplete")
            first = reviewer.call_args.kwargs["assessment_id"]
            epoch.review_attempt(self.root, "control-hello")
            second = reviewer.call_args.kwargs["assessment_id"]
        self.assertNotEqual(first, second)
        self.assertEqual(epoch.next_action(self.root)["action"], "review")
        self.assertEqual(len([row for row in epoch.events(self.root) if row["kind"] == "exposure"]), 2)

    def test_review_cannot_change_the_evidence_and_then_claim_completion(self):
        self.completed()
        payload, verdict = self.assessment()
        def mutate(*args, **kwargs):
            (self.root / "runs" / "control-hello" / "transcript.md").write_text("rewritten evidence")
            return payload
        with mock.patch.object(review, "review", side_effect=mutate), \
                mock.patch.object(judge, "judge", return_value=verdict), \
                self.assertRaisesRegex(ValueError, "sealed attempt evidence changed"):
            epoch.review_attempt(self.root, "control-hello")
        self.assertFalse(any(row["kind"] == "reviewed" for row in epoch.events(self.root)))
        self.assertTrue(any(row["kind"] == "exposure" for row in epoch.events(self.root)))

    def test_material_challenge_requires_an_owner_decision_and_does_not_rewrite_spec(self):
        self.completed()
        finding = {"id": "new-position", "title": "A different recovery contract", "target": "shiploop",
                   "mission_anchor": {"clause_id": None, "relationship": "novel", "challenge": "New purpose question"},
                   "materiality": "material", "confidence": "low", "implementation_eligible": False,
                   "proposed_disposition": "owner_review", "files": [], "proposal": "Investigate an alternative",
                   "potential_impact": "Could improve recovery", "alternatives": ["Keep current contract"],
                   "next_experiment": "Exercise both recovery paths",
                   "evidence": [{"reference": "result.json", "observation": "Recovery was blocked",
                                 "interpretation": "An alternative might help"}]}
        payload, verdict = self.assessment(discoveries=[finding])
        with mock.patch.object(review, "review", return_value=payload), \
                mock.patch.object(judge, "judge", return_value=verdict):
            self.assertEqual(epoch.review_attempt(self.root, "control-hello")["kind"], "reviewed")
        snapshot = (self.root / "specification.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "owner-decision"):
            epoch.disposition(self.root, "control-hello", "new-position", "accept", "Worth pursuing")
        accepted = epoch.disposition(self.root, "control-hello", "new-position", "accept", "Owner chose this direction",
                                     owner_decision="owner-decision-123")
        self.assertEqual(accepted["implementation"], "pending")
        self.assertFalse(accepted["specification_changed"])
        self.assertEqual((self.root / "specification.json").read_bytes(), snapshot)

    def test_torn_event_is_not_silently_ignored(self):
        with (self.root / epoch.LEDGER).open("a") as handle:
            handle.write('{"sequence": 2')
        with self.assertRaisesRegex(ValueError, "incomplete"):
            epoch.events(self.root)

    def test_two_controllers_cannot_dispatch_together(self):
        with epoch.locked(self.root), self.assertRaises(BlockingIOError), epoch.locked(self.root):
            self.fail("second lock entered")

    def test_cli_resume_is_read_only_and_does_not_retry(self):
        self.intent()
        original = (self.root / epoch.LEDGER).read_bytes()
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            code = epoch.main(["resume", "--output", str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(captured.getvalue())["action"], "reconcile")
        self.assertEqual((self.root / epoch.LEDGER).read_bytes(), original)


class EpochLaunchAndPredictionTest(unittest.TestCase):
    """Launches hold the lock only around their intent and seal; a prediction is bound before any attempt."""

    setUp = EpochTest.setUp

    def test_two_attempts_run_side_by_side_and_both_seal(self):
        import threading
        inside = threading.Barrier(2, timeout=20)

        def fake(argv):
            inside.wait()  # both runs are inside the runner at once: neither holds the epoch's lock
            output = Path(argv[argv.index("--output") + 1])
            output.mkdir()
            (output / "result.json").write_text('{"pass": true}')
            return 0
        errors = []

        def launch(arm):
            try:
                epoch.launch(self.root, arm + "-hello", self.plugin)
            except Exception as error:  # noqa: BLE001 - reported below
                errors.append(error)
        with mock.patch.object(runner, "main", side_effect=fake):
            threads = [threading.Thread(target=launch, args=(arm,)) for arm in ("control", "candidate")]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(30)
        self.assertEqual(errors, [])
        self.assertEqual([row["status"] for row in epoch.state(self.root)["attempts"]], ["recorded", "recorded"])
        self.assertEqual([row["sequence"] for row in epoch.events(self.root)], list(range(1, len(epoch.events(self.root)) + 1)))

    def test_a_second_launch_of_a_running_attempt_is_refused(self):
        def fake(argv):
            with self.assertRaisesRegex(ValueError, "already dispatched"):
                epoch.launch(self.root, "control-hello", self.plugin)
            output = Path(argv[argv.index("--output") + 1])
            output.mkdir()
            (output / "result.json").write_text('{"pass": true}')
            return 0
        with mock.patch.object(runner, "main", side_effect=fake):
            epoch.launch(self.root, "control-hello", self.plugin)
        self.assertEqual(len([r for r in epoch.events(self.root) if r["kind"] == "launch_intent"]), 1)

    def test_a_held_lock_waits_when_asked_and_refuses_after_its_wait(self):
        with epoch.locked(self.root), self.assertRaises(BlockingIOError), epoch.locked(self.root, wait=0.5):
            self.fail("second lock entered")

    def prediction(self, **change):
        return {"contract": "prediction/1", "record": "LR-20261030-abcdef", "anchor": "S-7",
                "because": "a shorter packet head costs fewer tokens",
                "effects": [{"case": "hello", "measure": "tokens", "direction": "down", "at_least": 0.15}], **change}

    def test_a_prediction_is_bound_before_any_attempt_and_cannot_change(self):
        root, path = self.temp / "predicted", self.temp / "prediction.json"
        path.write_text(json.dumps(self.prediction()))
        registered = epoch.initialise(root, self.template, path)
        self.assertEqual(registered["contract"], "shiploop-epoch/2")
        self.assertIn("prediction_sha256", registered)
        self.assertEqual(epoch.state(root)["prediction"]["record"], "LR-20261030-abcdef")
        (root / "prediction.json").chmod(0o644)
        (root / "prediction.json").write_text(json.dumps(self.prediction(because="edited after the runs")))
        with self.assertRaisesRegex(ValueError, "frozen prediction.json changed"):
            epoch.registration(root)

    def test_a_prediction_the_epoch_cannot_resolve_refuses_the_registration(self):
        root, path = self.temp / "refused", self.temp / "prediction.json"
        path.write_text(json.dumps(self.prediction(effects=[{"case": "hello", "measure": "tokens", "direction": "down",
                                                             "at_least": 0.01}])))
        with self.assertRaisesRegex(ValueError, "prediction refused: .*tolerance"):
            epoch.initialise(root, self.template, path)
        self.assertEqual(epoch.events(root)[-1]["kind"], "registration_refused")
        self.assertFalse((root / "prediction.json").exists())


if __name__ == "__main__":
    unittest.main()
