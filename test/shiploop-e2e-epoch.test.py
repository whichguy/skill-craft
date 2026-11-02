"""No-model controller fixtures: receipts, interrupted dispatch, source drift and qualification routing."""
from __future__ import annotations

import contextlib
import fcntl
import io
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import state_home

state_home.isolate()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import boundary
import environment
import epoch
import hosts
import judge
import listeners
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

    def target_epoch(self, name, cases):
        registration = json.loads(self.template.read_text())
        registration["cases"] = {case: {"role": "regression", "attempts": count}
                                  for case, count in cases.items()}
        registration["attempts"] = [
            {"id": f"{arm}-{case}-{number}", "arm": arm, "case": case}
            for case, count in cases.items() for arm in ("control", "candidate")
            for number in range(1, count + 1)
        ]
        registration["qualification"] = boundary.qualification_snapshot(
            ROOT / "test" / "shiploop_e2e", list(cases))
        template = self.temp / f"{name}-registration.json"
        template.write_text(json.dumps(registration))
        root = self.temp / name
        epoch.initialise(root, template)
        return root

    def complete_target_attempt(self, root, attempt_id, cleanup=None, *, passed=False):
        intent = epoch.launch_intent(root, attempt_id, self.plugin)
        output = Path(intent["output"])
        output.mkdir()
        attempt = next(row for row in epoch.registration(root)["attempts"] if row["id"] == attempt_id)
        result = {"case": attempt["case"], "pass": passed}
        if cleanup is not None:
            result["platform"] = {"cleanup": cleanup}
            platform = output / "platform"
            platform.mkdir()
            (platform / "cleanup-record.json").write_text(json.dumps(cleanup))
        (output / "result.json").write_text(json.dumps(result))
        return epoch.record_run(root, attempt_id)

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

    def test_launch_retains_summary_rows_in_epoch_without_mutating_source_baseline(self):
        source_baseline = self.temp / "source-baselines.jsonl"
        accepted = '{"case": "accepted-history"}\n'
        source_baseline.write_text(accepted)
        campaign_baseline = self.root / "baselines.jsonl"
        campaign_baseline.write_text('{"case": "earlier-campaign-run"}\n')

        def completed_run(argv):
            # Exercise the real parser's baseline default/override without starting a model.
            args = runner.parser().parse_args(argv)
            with args.baseline.open("a") as handle:
                handle.write(json.dumps({"case": args.case, "attempt": args.output.name}) + "\n")
            args.output.mkdir()
            (args.output / "result.json").write_text(json.dumps({"case": args.case, "pass": True}))
            return 0

        with mock.patch.object(runner, "BASELINES", source_baseline), \
                mock.patch.object(runner, "main", side_effect=completed_run):
            for arm in ("control", "candidate"):
                epoch.launch(self.root, arm + "-hello", self.plugin)

        self.assertEqual(source_baseline.read_text(), accepted)
        rows = [json.loads(line) for line in campaign_baseline.read_text().splitlines()]
        self.assertEqual(rows, [{"case": "earlier-campaign-run"},
                                {"case": "hello", "attempt": "control-hello"},
                                {"case": "hello", "attempt": "candidate-hello"}])
        self.assertEqual([row["status"] for row in epoch.state(self.root)["attempts"]],
                         ["recorded", "recorded"])

    def test_crash_after_intent_blocks_a_duplicate_dispatch(self):
        self.intent()
        self.assertEqual(epoch.next_action(self.root)["action"], "reconcile")
        with self.assertRaisesRegex(ValueError, "already dispatched"):
            self.intent()
        with self.assertRaisesRegex(ValueError, "remains unknown"):
            epoch.record_run(self.root, "control-hello")
        self.assertEqual(len([r for r in epoch.events(self.root) if r["kind"] == "launch_intent"]), 1)

    def test_an_unsealed_platform_target_blocks_a_different_prefix_without_consuming_its_intent(self):
        root = self.target_epoch("same-org", {"chess-salesforce": 1, "battleship-salesforce": 1})
        chess = runner.case_platform("chess-salesforce")
        battleship = runner.case_platform("battleship-salesforce")
        self.assertEqual((chess["kind"], chess["org"]), (battleship["kind"], battleship["org"]))
        self.assertNotEqual(chess["prefix"], battleship["prefix"])
        epoch.launch_intent(root, "control-chess-salesforce-1", self.plugin)
        before = epoch.events(root)

        with self.assertRaises(ValueError):
            epoch.launch_intent(root, "control-battleship-salesforce-1", self.plugin)

        self.assertEqual(epoch.events(root), before)
        self.assertFalse((root / "runs" / "control-battleship-salesforce-1").exists())

    def test_only_a_sealed_clean_cleanup_releases_a_platform_target(self):
        cases = (
            ("missing", None),
            ("not-ran", {"ran": False, "ok": True}),
            ("failed", {"ran": True, "ok": False}),
            ("kept", {"ran": True, "ok": True, "kept": True}),
            ("kept-unfinished", {"ran": True, "ok": True, "kept_unfinished": True}),
        )
        for label, cleanup in cases:
            with self.subTest(cleanup=label):
                root = self.target_epoch(f"unclean-{label}", {"chess-salesforce": 1, "battleship-salesforce": 1})
                self.complete_target_attempt(root, "control-chess-salesforce-1", cleanup)
                before = epoch.events(root)

                with self.assertRaises(ValueError):
                    epoch.launch_intent(root, "control-battleship-salesforce-1", self.plugin)

                self.assertEqual(epoch.events(root), before)
                self.assertFalse((root / "runs" / "control-battleship-salesforce-1").exists())
                self.assertEqual(next(row for row in epoch.state(root)["attempts"]
                                      if row["id"] == "control-battleship-salesforce-1")["status"], "not_launched")

    def test_clean_cleanup_releases_target_even_when_the_product_failed(self):
        root = self.target_epoch("clean-after-failure", {"chess-salesforce": 1, "battleship-salesforce": 1})
        self.complete_target_attempt(root, "control-chess-salesforce-1", {"ran": True, "ok": True}, passed=False)
        output, _receipt = epoch.sealed_run(root, "control-chess-salesforce-1")
        self.assertFalse(json.loads((output / "result.json").read_text())["pass"])

        intent = epoch.launch_intent(root, "control-battleship-salesforce-1", self.plugin)

        self.assertEqual(intent["attempt_id"], "control-battleship-salesforce-1")

    def test_local_and_different_org_targets_can_launch_beside_an_unsealed_platform_target(self):
        root = self.target_epoch("independent-targets", {
            "chess-salesforce": 1, "battleship-salesforce": 1, "hello": 1,
        })
        epoch.launch_intent(root, "control-chess-salesforce-1", self.plugin)
        real_case_platform = runner.case_platform

        def another_org(case):
            spec = real_case_platform(case)
            return {**spec, "org": "another-org"} if case == "battleship-salesforce" else spec

        with mock.patch.object(runner, "case_platform", side_effect=another_org):
            local = epoch.launch_intent(root, "control-hello-1", self.plugin)
            other_org = epoch.launch_intent(root, "control-battleship-salesforce-1", self.plugin)

        self.assertEqual(local["attempt_id"], "control-hello-1")
        self.assertEqual(other_org["attempt_id"], "control-battleship-salesforce-1")
        self.assertEqual(len([row for row in epoch.events(root) if row["kind"] == "launch_intent"]), 3)

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


    def test_status_after_a_decision_prints_the_state_and_exits_cleanly(self):
        """Found live in the stage 4 pilot: state() carries the whole decision event under "decision", and main() used that
        dict as a key into promotion.EXIT, so epoch.py status raised TypeError after printing, once any decision existed."""
        epoch.append(self.root, "decision", result={"decision": "DROP", "reasons": ["a stated reason"]})
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            code = epoch.main(["status", "--output", str(self.root)])
        self.assertEqual(code, 0)
        self.assertTrue(captured.getvalue().strip().startswith("{"))
        with mock.patch.object(epoch, "decide", return_value={"decision": "DROP", "reasons": []}), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(epoch.main(["decide", "--output", str(self.root)]), 3, "decide still exits with the decision's code")


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

    def clean_runs_root(self):
        """The receipt's neighbours come from environment.runs_root, which an exported variable would move off the epoch."""
        self.enterContext(mock.patch.dict(os.environ))
        os.environ.pop(environment.RUNS_ROOT_ENV, None)

    def test_an_attempt_that_ends_before_a_sibling_waits_for_it_so_its_seal_stays_valid(self):
        """Found live in the stage 4 pilot: scorecard.run_receipt binds the timeline, metrics and invocation files of every run
        that overlapped an attempt, so an attempt sealed while a sibling was still writing read as changed evidence the moment the
        sibling wrote again. Four of five parallel attempts ended invalid_evidence.

        No sleeps decide the order: the candidate keeps running until the control has either started waiting for it (the fix)
        or sealed (the fault), and only then writes again and lets go."""
        self.clean_runs_root()
        both_started, control_decided = threading.Barrier(2, timeout=20), threading.Event()
        spans = {"control-hello": (1000.0, 1500.0), "candidate-hello": (1200.0, 1700.0)}
        real_unsettled, real_record = epoch.unsettled_siblings, epoch.record_run

        def timeline(output, first, last):
            stamps = [first, first + (last - first) / 3, first + 2 * (last - first) / 3, last]
            (output / "timeline.jsonl").write_text("".join(json.dumps({"line": n, "t": t}) + "\n"
                                                           for n, t in enumerate(stamps)))

        def unsettled(root, output):
            if Path(output).name == "control-hello":
                control_decided.set()  # the control is looking at its siblings before it seals
            return real_unsettled(root, output)

        def record(root, attempt_id):
            sealed = real_record(root, attempt_id)
            if attempt_id == "control-hello":
                control_decided.set()  # without the fix the control seals here, beside a candidate that still runs
            return sealed

        def fake(argv):
            output = Path(argv[argv.index("--output") + 1])
            output.mkdir()
            descriptor = os.open(output / listeners.LOCK_NAME, os.O_CREAT | os.O_RDWR)
            fcntl.flock(descriptor, fcntl.LOCK_EX)  # run.py takes the folder's lock before its first stamp, and keeps it
            try:
                timeline(output, *spans[output.name])
                (output / "invocation.json").write_text(json.dumps({"case": "hello", "host": "codex", "versions": {}}))
                both_started.wait()  # each timeline exists before either result records its overlap
                if output.name == "candidate-hello":
                    control_decided.wait(20)
                    timeline(output, 1200.0, 1750.0)  # still running after its sibling returned, and still writing
                (output / "result.json").write_text(json.dumps({"pass": True, "environment": {
                    "overlap": environment.overlap(output)}}))
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)
            return 0
        errors = []

        def launch(arm):
            try:
                epoch.launch(self.root, arm + "-hello", self.plugin)
            except Exception as error:  # noqa: BLE001 - reported below
                errors.append(error)
        with mock.patch.object(runner, "main", side_effect=fake), mock.patch.object(epoch, "SIBLING_POLL", 0.05), \
                mock.patch.object(epoch, "SIBLING_WAIT", 20.0), mock.patch.object(epoch, "unsettled_siblings", unsettled), \
                mock.patch.object(epoch, "record_run", record):
            threads = [threading.Thread(target=launch, args=(arm,)) for arm in ("control", "candidate")]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(60)
        self.assertEqual(errors, [])
        self.assertEqual([row["status"] for row in epoch.state(self.root)["attempts"]], ["recorded", "recorded"],
                         "an attempt sealed beside a sibling that was still writing is invalid evidence")

    def run_folder(self, name, first, last, inside=True):
        folder = (self.root / "runs" if inside else self.temp / "elsewhere") / name
        folder.mkdir(parents=True)
        timeline = folder / "timeline.jsonl"
        if first is None:  # a run that has opened its timeline and not stamped it yet
            timeline.write_text("")
        else:
            stamps = [first, first + (last - first) / 3, first + 2 * (last - first) / 3, last]
            timeline.write_text("".join(json.dumps({"line": n, "t": t}) + "\n" for n, t in enumerate(stamps)))
        (folder / "invocation.json").write_text(json.dumps({"case": "hello", "host": "codex", "versions": {}}))
        return folder

    def running(self, folder):
        """A harness holding the folder's lock, as run.py does for as long as its run lives; returns the way to let go."""
        descriptor = os.open(folder / listeners.LOCK_NAME, os.O_CREAT | os.O_RDWR)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        state = {"open": True}

        def release():
            if state["open"]:
                state["open"] = False
                fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)
        self.addCleanup(release)
        return release

    def test_a_sibling_is_unsettled_while_it_runs_if_it_began_before_this_run_ended_or_has_not_stamped_yet(self):
        self.clean_runs_root()
        mine = self.run_folder("mine", 1000.0, 2000.0)
        overlapping = self.run_folder("overlapping", 1500.0, 2500.0)
        silent = self.run_folder("silent", 100.0, 150.0)  # began long before, and wrote nothing during this whole run
        starting = self.run_folder("starting", None, None)
        later = self.run_folder("later", 2500.0, 3000.0)  # began after this run ended: it never overlaps it
        finished = self.run_folder("finished", 1500.0, 2500.0)  # overlapped, and its harness has let go
        elsewhere = self.run_folder("elsewhere-run", 1500.0, 2500.0, inside=False)
        releases = {folder.name: self.running(folder) for folder in (overlapping, silent, starting, later, elsewhere)}
        with mock.patch.dict(os.environ, {environment.RUNS_ROOT_ENV: str(self.temp)}):
            self.assertEqual(epoch.unsettled_siblings(self.root, mine),
                             sorted(folder.resolve() for folder in (overlapping, silent, starting)),
                             "a sibling that began after this run ended, one that has finished and one outside the epoch "
                             "are not waited for; a silent one and one still starting are")
            (starting / "timeline.jsonl").write_text(json.dumps({"line": 0, "t": 2600.0}) + "\n")
            releases["overlapping"]()
            self.assertEqual(epoch.unsettled_siblings(self.root, mine), [silent.resolve()],
                             "a sibling that has stamped after this run ended is settled, as is one that let go")
        self.assertTrue(finished.is_dir())

    def test_a_sibling_still_starting_is_waited_for_until_it_stamps(self):
        self.clean_runs_root()
        mine = self.run_folder("mine", 1000.0, 2000.0)
        starting = self.run_folder("starting", None, None)
        self.running(starting)
        timer = threading.Timer(0.3, lambda: (starting / "timeline.jsonl").write_text(
            json.dumps({"line": 0, "t": 2600.0}) + "\n"))
        timer.start()
        self.addCleanup(timer.join)
        began = time.monotonic()
        self.assertEqual(epoch.settle_siblings(self.root, mine, wait=10.0, poll=0.05), [])
        self.assertGreaterEqual(time.monotonic() - began, 0.25, "it returned before the sibling had stamped")

    def test_settling_gives_up_after_its_wait_and_the_seal_is_then_refused_not_made_unstable(self):
        self.clean_runs_root()
        mine = self.run_folder("mine", 1000.0, 2000.0)
        sibling = self.run_folder("sibling", 1500.0, 2500.0)
        self.running(sibling)
        began = time.monotonic()
        left = epoch.settle_siblings(self.root, mine, wait=0.3, poll=0.05)
        self.assertEqual(left, [sibling.resolve()])
        self.assertGreaterEqual(time.monotonic() - began, 0.25)
        with mock.patch.object(epoch, "registration", return_value={}), mock.patch.object(epoch, "attempt_spec"), \
                mock.patch.object(epoch, "events", return_value=[
                    {"kind": "launch_intent", "attempt_id": "mine", "output": str(mine), "at": "t"}]):
            (mine / "result.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "still running.*sibling"):
                epoch.record_run(self.root, "mine")

    def test_the_wait_for_siblings_does_not_hold_the_epoch_lock(self):
        """A sibling that ends needs the lock to seal itself; a finished attempt that waited while holding it would block that."""
        held, real = [], epoch.settle_siblings

        def spy(root, output, *args, **kwargs):
            try:
                with epoch.locked(root, 0.0):
                    held.append(False)
            except BlockingIOError:
                held.append(True)
            return real(root, output, *args, **kwargs)

        def fake(argv):
            output = Path(argv[argv.index("--output") + 1])
            output.mkdir()
            (output / "result.json").write_text('{"pass": true}')
            return 0
        with mock.patch.object(runner, "main", side_effect=fake), mock.patch.object(epoch, "settle_siblings", spy):
            epoch.launch(self.root, "control-hello", self.plugin)
        self.assertEqual(held, [False])

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


    # The independent review of 2026-10-31.

    def test_a_prediction_file_added_to_an_epoch_registered_without_one_is_refused(self):
        (self.root / "prediction.json").write_text(json.dumps(self.prediction()))
        with self.assertRaisesRegex(ValueError, "prediction.json"):
            epoch.registration(self.root)

    def test_a_row_still_being_written_is_waited_for_and_a_torn_row_is_still_refused(self):
        import threading
        import time
        ledger = self.root / epoch.LEDGER
        whole = json.dumps({"sequence": len(epoch.events(self.root)) + 1, "at": 0, "kind": "probe"})
        with ledger.open("a") as handle:
            handle.write(whole[:12])  # a writer is mid-row

        def finish():
            time.sleep(0.15)
            with ledger.open("a") as handle:
                handle.write(whole[12:] + "\n")
        writer = threading.Thread(target=finish)
        writer.start()
        self.assertEqual(epoch.events(self.root)[-1]["kind"], "probe")
        writer.join()


    def test_appends_stay_exclusive_when_two_launches_seal_at_the_same_moment(self):
        """The review showed the lock around a launch's intent and seal could be removed with no test noticing, because
        the window between reading the ledger's length and writing the next row is microseconds. Here that window is
        widened, so unlocked appends collide on one sequence number."""
        import threading
        import time
        real_events = epoch.events
        both_done = threading.Barrier(2, timeout=20)

        def slow_events(root):
            rows = real_events(root)
            time.sleep(0.05)
            return rows

        def fake(argv):
            both_done.wait()  # both runs end together, so both seal together
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
        with mock.patch.object(runner, "main", side_effect=fake), mock.patch.object(epoch, "events", side_effect=slow_events):
            threads = [threading.Thread(target=launch, args=(arm,)) for arm in ("control", "candidate")]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(120)
        self.assertEqual(errors, [])
        rows = real_events(self.root)  # refuses a duplicated or skipped sequence number
        self.assertEqual([row["sequence"] for row in rows], list(range(1, len(rows) + 1)))
        self.assertEqual([row["status"] for row in epoch.state(self.root)["attempts"]], ["recorded", "recorded"])


if __name__ == "__main__":
    unittest.main()
