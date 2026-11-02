"""Registered continuation wiring; no model calls."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import os
import shutil
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
import delivery
import epoch
import predecessor
import run as runner
import scorecard


_HELPER_MODULES = {}


def fixture_module(filename):
    if filename not in _HELPER_MODULES:
        name = "_shiploop_fixture_" + filename.replace("-", "_").replace(".", "_")
        spec = importlib.util.spec_from_file_location(name, ROOT / "test" / filename)
        if spec is None or spec.loader is None:
            raise AssertionError(f"could not load fixture helpers from {filename}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        _HELPER_MODULES[filename] = module
    return _HELPER_MODULES[filename]


class PredecessorWiringTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)

    def helper(self, filename, class_name, method_name):
        test_class = getattr(fixture_module(filename), class_name)
        fixture = test_class(method_name)
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def predecessor_fixture(self):
        fixture = self.helper(
            "shiploop-e2e-predecessor.test.py", "PredecessorTest",
            "test_validate_registration_enforces_follow_mapping_from_frozen_cases",
        )
        # battleship-scoring is a real frozen follow-on case whose predecessor has no hidden acceptance suite.
        fixture.result["case"] = "battleship"
        fixture._write_run_records()
        fixture._refresh_entry()
        return fixture

    def plugin_fixture(self):
        plugin = self.temp / "plugin"
        skill = plugin / "skills" / "shiploop"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("fixture ShipLoop build\n")
        return plugin

    def qualification_fixture(self, prior_fixture, plugin, *, epoch_ids=False):
        fixture = self.helper(
            "shiploop-e2e-qualification.test.py", "QualificationTest",
            "test_strict_registration_freezes_inputs_and_uses_versioned_apis",
        )
        case = "battleship-scoring"
        driver = {"host": "claude", "model": "model-a", "effort": "high"}
        arms = {
            "control": {"shiploop_build": runner.tree_digest(plugin), "driver": driver},
            "candidate": {"shiploop_build": "b" * 12, "driver": driver},
        }
        changes = {"predecessors": {case: prior_fixture.entry}, "arms": arms}
        if epoch_ids:
            changes["attempts"] = [
                {"id": f"{arm}-{case}", "arm": arm, "case": case}
                for arm in ("control", "candidate")
            ]
        with mock.patch.dict(os.environ, {"SHIPLOOP_E2E_RUNS_ROOT": str(fixture.runs)}):
            prior_fixture._refresh_entry()
            changes["predecessors"] = {case: prior_fixture.entry}
            reg = fixture.registration({case: "capability"}, raw_changes=changes)
        return fixture, reg

    def linked_run(self, fixture, reg, entry, plugin, arm, *, passed, start, run=None, attempt_id=None,
                   linkage="valid"):
        case = "battleship-scoring"
        attempt_id = attempt_id or f"{arm}:{case}"
        card = fixture.card(reg, arm, case, passed=passed, start=start, run=run, attempt_id=attempt_id)
        output = Path(card["run"])
        with mock.patch.dict(os.environ, {"SHIPLOOP_E2E_RUNS_ROOT": str(fixture.runs)}):
            work = output / "work"
            shutil.rmtree(work)
            bundle = output / delivery.BUNDLE
            if bundle.exists():
                bundle.unlink()
            work.mkdir()
            follow_on = predecessor.restore(entry, work, "battleship")
            subprocess.run(["git", "-C", str(work), "config", "user.name", "Wiring fixture"], check=True)
            subprocess.run(["git", "-C", str(work), "config", "user.email", "wiring@example.invalid"], check=True)
            (work / "product.txt").write_text(f"{arm} follow-on\n")
            subprocess.run(["git", "-C", str(work), "add", "product.txt"], check=True)
            subprocess.run(["git", "-C", str(work), "commit", "-q", "-m", f"{arm} follow-on"], check=True)
            before = delivery.capture(work, output)
            after = delivery.fingerprint(work)

            result_path = output / "result.json"
            invocation_path = output / "invocation.json"
            result = json.loads(result_path.read_text())
            invocation = json.loads(invocation_path.read_text())
            if linkage == "missing":
                result.pop("follow_on", None)
                invocation.pop("follow_on", None)
            else:
                if linkage == "wrong":
                    follow_on = {**follow_on, "prior": str(output / "unregistered-prior")}
                result["follow_on"] = follow_on
                invocation["follow_on"] = follow_on
            result["delivery"] = {"before": before, "after": after}
            invocation["plugin_dir"] = str(plugin)
            result_path.write_text(json.dumps(result) + "\n")
            invocation_path.write_text(json.dumps(invocation) + "\n")
            return self.refresh_card(fixture, reg, output, attempt_id)

    @staticmethod
    def refresh_card(fixture, reg, output, attempt_id):
        with mock.patch.dict(os.environ, {"SHIPLOOP_E2E_RUNS_ROOT": str(fixture.runs)}):
            card = scorecard.score(output, required_case=reg["qualification"]["cases"]["battleship-scoring"])
        card["attempt_id"] = attempt_id
        return card, card["started"]

    def epoch_attempt(self, prior, qualification, plugin, label, *, linkage="valid"):
        root = self.temp / f"epoch-{label}"
        raw = {key: value for key, value in qualification.items() if key not in ("sha256", "payload_sha256")}
        template = self.temp / f"registration-{label}.json"
        template.write_text(json.dumps(raw))
        attempt_id = "control-battleship-scoring"
        with mock.patch.dict(os.environ, {"SHIPLOOP_E2E_RUNS_ROOT": str(self.qualification_helper.runs)}):
            epoch.initialise(root, template)
            intent = epoch.launch_intent(root, attempt_id, plugin)
            output = Path(intent["output"])
            card = self.linked_run(
                fixture=self.qualification_helper, reg=qualification, entry=prior, plugin=plugin,
                arm="control", passed=True, start=2000, run=output, attempt_id=attempt_id, linkage=linkage,
            )
        return root, attempt_id, output, card

    def set_up_qualification_helper(self, prior_fixture, plugin, *, epoch_ids=False):
        self.qualification_helper, reg = self.qualification_fixture(prior_fixture, plugin, epoch_ids=epoch_ids)
        return reg

    def test_epoch_passes_frozen_registration_to_existing_runner(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            registration = root / "registration.json"
            registration.write_text('{"predecessors": {"next": {}}}\n')
            wanted = hashlib.sha256(registration.read_bytes()).hexdigest()
            intent = {
                "case": "next", "driver": {"host": "codex", "model": "gpt-6.1-terra", "effort": "high"},
                "plugin": str(root / "plugin"), "output": str(root / "runs" / "a"),
                "registration_sha256": wanted,
                "predecessor": {"run": str(root / "prior"), "receipt_sha256": "a" * 64},
            }
            with mock.patch.object(epoch, "locked", return_value=contextlib.nullcontext()), \
                    mock.patch.object(epoch, "launch_intent", return_value=intent), \
                    mock.patch.object(epoch, "settle_siblings"), \
                    mock.patch.object(epoch, "append"), \
                    mock.patch.object(epoch, "record_run", return_value={}), \
                    mock.patch.object(runner, "main", return_value=0) as launch:
                epoch.launch(root, "a", root / "plugin")
            argv = launch.call_args.args[0]
            self.assertIn("--predecessor-registration", argv)
            self.assertEqual(argv[argv.index("--predecessor-registration") + 1], str(registration))
            self.assertEqual(argv[argv.index("--predecessor-registration-sha256") + 1], wanted)
            self.assertNotIn("--continue-from", argv)

    def test_runner_accepts_registered_input_flags(self):
        args = runner.parser().parse_args([
            "--case", "user-summary", "--predecessor-registration", "/tmp/registration.json",
            "--predecessor-registration-sha256", "a" * 64,
        ])
        self.assertEqual(args.predecessor_registration, Path("/tmp/registration.json"))
        self.assertEqual(args.predecessor_registration_sha256, "a" * 64)

    def test_runner_refuses_changed_registration_before_validation_or_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "registration.json"
            path.write_text('{"predecessors": {}}')
            args = runner.parser().parse_args([])
            args.predecessor_registration = path
            args.predecessor_registration_sha256 = "a" * 64
            with self.assertRaisesRegex(SystemExit, "registration.*changed|digest"):
                runner.registered_predecessor(args, "user-summary")

    def test_runner_refuses_registered_predecessor_with_legacy_run_overrides(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            registration = root / "registration.json"
            registration.write_text("{}\n")
            wanted = hashlib.sha256(registration.read_bytes()).hexdigest()
            for option, value in (
                ("--continue-from", str(root / "prior-run")),
                ("--resume-run", str(root / "resume-run")),
                ("--seed-at", "step-plan"),
                ("--suite", "smoke"),
            ):
                with self.subTest(option=option), \
                        mock.patch.object(predecessor, "validate_registration",
                                          side_effect=AssertionError("must refuse before reading registration")) as validate, \
                        mock.patch.object(predecessor, "restore",
                                          side_effect=AssertionError("must refuse before restoring")) as restore, \
                        self.assertRaisesRegex(SystemExit, "without continuation, resume, seed or suite overrides"):
                    runner.main([
                        "--case", "battleship-scoring", "--output", str(root / "output"),
                        "--predecessor-registration", str(registration), "--predecessor-registration-sha256", wanted,
                        option, value,
                    ])
                validate.assert_not_called()
                restore.assert_not_called()
                self.assertFalse((root / "output").exists())

    def test_runner_refuses_an_unpaired_registration_path_or_digest_before_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            registration = root / "registration.json"
            registration.write_text("{}\n")
            wanted = hashlib.sha256(registration.read_bytes()).hexdigest()
            incomplete = (
                ["--predecessor-registration", str(registration)],
                ["--predecessor-registration-sha256", wanted],
            )
            for pair in incomplete:
                with self.subTest(pair=pair), \
                        mock.patch.object(predecessor, "validate_registration",
                                          side_effect=AssertionError("must refuse before reading registration")) as validate, \
                        mock.patch.object(predecessor, "restore",
                                          side_effect=AssertionError("must refuse before restoring")) as restore, \
                        self.assertRaisesRegex(SystemExit, "needs its registration path and SHA256 digest"):
                    runner.main([
                        "--case", "battleship-scoring", "--output", str(root / "output"), *pair,
                    ])
                validate.assert_not_called()
                restore.assert_not_called()
                self.assertFalse((root / "output").exists())

    def test_epoch_record_run_refuses_missing_or_wrong_registered_linkage(self):
        prior = self.predecessor_fixture()
        plugin = self.plugin_fixture()
        reg = self.set_up_qualification_helper(prior, plugin, epoch_ids=True)

        for linkage in ("missing", "wrong"):
            with self.subTest(linkage=linkage):
                root, attempt_id, _output, _card = self.epoch_attempt(prior.entry, reg, plugin, linkage,
                                                                      linkage=linkage)
                with mock.patch.dict(os.environ, {"SHIPLOOP_E2E_RUNS_ROOT": str(self.qualification_helper.runs)}):
                    with self.assertRaisesRegex(ValueError, "registered predecessor linkage"):
                        epoch.record_run(root, attempt_id)
                self.assertFalse(any(row["kind"] == "recorded" for row in epoch.events(root)))

    def test_epoch_record_run_seals_valid_linkage_and_its_evidence_receipt(self):
        prior = self.predecessor_fixture()
        plugin = self.plugin_fixture()
        reg = self.set_up_qualification_helper(prior, plugin, epoch_ids=True)
        root, attempt_id, _output, _card = self.epoch_attempt(prior.entry, reg, plugin, "valid")

        with mock.patch.dict(os.environ, {"SHIPLOOP_E2E_RUNS_ROOT": str(self.qualification_helper.runs)}):
            recorded = epoch.record_run(root, attempt_id)
            output, sealed = epoch.sealed_run(root, attempt_id)

        self.assertEqual(recorded["kind"], "recorded")
        self.assertTrue(recorded["evidence"]["observed"])
        self.assertIn("result.json", recorded["files"])
        self.assertEqual(output, Path(recorded["output"]))
        self.assertEqual(sealed, recorded)

    def test_strict_promotion_requires_run_linkage_and_keeps_valid_predecessor_evidence(self):
        prior = self.predecessor_fixture()
        plugin = self.plugin_fixture()
        qualification = self.set_up_qualification_helper(prior, plugin)
        helper = self.qualification_helper
        control = self.linked_run(helper, qualification, prior.entry, plugin, "control", passed=False, start=2000)
        candidate = self.linked_run(helper, qualification, prior.entry, plugin, "candidate", passed=True, start=3000)

        valid = helper.decide(qualification, [control], [candidate])

        self.assertEqual(valid["decision"], "PROMOTE")
        self.assertEqual(valid["evidence_issues"], [])
        self.assertTrue(all(row["evidence_valid"] for row in valid["attempts"]))

        candidate_path = Path(candidate[0]["run"])
        result_path = candidate_path / "result.json"
        invocation_path = candidate_path / "invocation.json"
        for path in (result_path, invocation_path):
            record = json.loads(path.read_text())
            record.pop("follow_on", None)
            path.write_text(json.dumps(record) + "\n")
        missing = self.refresh_card(helper, qualification, candidate_path, candidate[0]["attempt_id"])
        rejected = helper.decide(qualification, [control], [missing])

        self.assertNotEqual(rejected["decision"], "PROMOTE")
        self.assertTrue(any("has no follow_on binding" in issue["reason"] for issue in rejected["evidence_issues"]))

    def test_changed_registered_predecessor_source_receipt_blocks_sealing_and_promotion(self):
        prior = self.predecessor_fixture()
        plugin = self.plugin_fixture()
        qualification = self.set_up_qualification_helper(prior, plugin, epoch_ids=True)
        root, attempt_id, _output, _card = self.epoch_attempt(prior.entry, qualification, plugin, "source-change")
        helper = self.qualification_helper
        control = self.linked_run(helper, qualification, prior.entry, plugin, "control", passed=False, start=4000)
        candidate = self.linked_run(helper, qualification, prior.entry, plugin, "candidate", passed=True, start=5000)
        prompt = Path(prior.entry["run"]) / "prompt.txt"
        prompt.write_text(prompt.read_text() + "changed after predecessor registration\n")

        with mock.patch.dict(os.environ, {"SHIPLOOP_E2E_RUNS_ROOT": str(helper.runs)}):
            with self.assertRaisesRegex(ValueError, "receipt changed"):
                epoch.record_run(root, attempt_id)
            rejected = helper.decide(qualification, [control], [candidate])

        self.assertNotEqual(rejected["decision"], "PROMOTE")
        self.assertTrue(any("receipt changed since registration" in error
                            for error in rejected["global_errors"]))


if __name__ == "__main__":
    unittest.main()

