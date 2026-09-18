#!/usr/bin/env python3
"""Focused no-model checks for the generalized discovery runner."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("generic_runner_under_test", HERE / "runner.py")
assert spec and spec.loader
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

initializer_spec = importlib.util.spec_from_file_location("generalized_discovery_initializer_for_runner_test", HERE / "initialize.py")
assert initializer_spec and initializer_spec.loader
initializer = importlib.util.module_from_spec(initializer_spec)
initializer_spec.loader.exec_module(initializer)


class FakeActionWatch:
    def __init__(self, **_: object) -> None:
        self.stop_reason = None

    def snapshot(self) -> dict[str, object]:
        return {"count": 0, "records": []}


class FakeRuntime:
    ACTION_TYPES = {"mcp_tool_call"}
    ActionWatch = FakeActionWatch

    def __init__(self, context: dict[str, object], *, write_report: bool = True, edit_fixture: bool = False) -> None:
        self.context = context
        self.write_report = write_report
        self.edit_fixture = edit_fixture
        self.workspace: Path | None = None

    def codex_command(self, workspace: Path, *_: object) -> list[str]:
        self.workspace = workspace
        return ["codex", "-c", 'mcp_servers.shiploop_workspace.args=["gateway"]']

    def stream_context(self, *_: object, **__: object) -> dict[str, object]:
        assert self.workspace is not None
        if self.write_report:
            (self.workspace / "REPORT.md").write_text("# report\n", encoding="utf-8")
        if self.edit_fixture:
            (self.workspace / "fixture.txt").write_text("changed\n", encoding="utf-8")
        return dict(self.context)


def make_study(root: Path, arm: str = "arm-a") -> tuple[Path, dict[str, object]]:
    study = root / "study"
    workspace = study / "arms" / arm / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "fixture.txt").write_text("original\n", encoding="utf-8")
    prompt = workspace.parent / "prompt.md"
    prompt.write_text("do work\n", encoding="utf-8")
    (workspace.parent / "input-hashes.json").write_text(json.dumps(runner.snapshot(workspace)), encoding="utf-8")
    now = runner.time.time()
    state: dict[str, object] = {
        "arms": {arm: {"prompt_sha256": runner.sha256(prompt)}},
        "max_arm_launches": 12,
        "hard_deadline_epoch": now + 120,
        "closeout_start_epoch": now + 90,
    }
    return study, state


def initialize_study(root: Path) -> Path:
    baseline = (HERE.parents[2] / "skills" / "shiploop" / "references" / "research-loop.md").read_text(encoding="utf-8")
    candidate, plan, study = root / "candidate.md", root / "plan.md", root / "initialized-study"
    candidate.write_text(baseline + "\nCandidate wording.\n", encoding="utf-8")
    plan.write_text("# Frozen plan\n", encoding="utf-8")
    initializer.initialize(study, candidate, plan)
    return study


class LaunchLedgerTest(unittest.TestCase):
    def test_preserves_history_and_refuses_duplicate_or_over_cap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            study = Path(temporary)
            self.assertEqual(runner.reserve_launch(study, "arm-a", 2), 1)
            self.assertEqual(runner.reserve_launch(study, "arm-b", 2), 2)
            with self.assertRaises(ValueError):
                runner.reserve_launch(study, "arm-a", 2)
            with self.assertRaises(ValueError):
                runner.reserve_launch(study, "arm-c", 2)
            state = runner.json_file(study / "launch-ledger.json")
            self.assertEqual([entry["arm"] for entry in state["launches"]], ["arm-a", "arm-b"])


class ArmOutcomeTest(unittest.TestCase):
    def run_case(self, context: dict[str, object], *, write_report: bool = True,
                 edit_fixture: bool = False) -> tuple[dict[str, object], dict[str, object]]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        study, state = make_study(Path(temporary.name))
        with mock.patch.object(runner, "validate_study_inputs", return_value={}):
            result = runner.run_arm(study, state, FakeRuntime(context, write_report=write_report, edit_fixture=edit_fixture), "arm-a")
        metadata = runner.json_file(Path(str(result["run"])) / "metadata.json")
        return result, metadata

    def test_success_requires_clean_context_and_report(self) -> None:
        result, metadata = self.run_case({"context": 1, "exit_code": 0, "termination_reason": None})
        self.assertEqual(result["status"], "completed")
        self.assertEqual(metadata["completion"], {"status": "completed", "reasons": [],
                                                     "exit_code": 0, "termination_reason": None})

    def test_nonzero_exit_and_termination_fail(self) -> None:
        result, _ = self.run_case({"context": 1, "exit_code": 3, "termination_reason": None})
        self.assertEqual(result["status"], "failed")
        self.assertIn("context_nonzero_exit", result["completion"]["reasons"])
        result, _ = self.run_case({"context": 1, "exit_code": -15, "termination_reason": "deadline"})
        self.assertEqual(result["status"], "failed")
        self.assertIn("context_terminated", result["completion"]["reasons"])

    def test_missing_report_is_incomplete_and_fixture_edit_fails(self) -> None:
        result, _ = self.run_case({"context": 1, "exit_code": 0, "termination_reason": None}, write_report=False)
        self.assertEqual(result["status"], "incomplete")
        self.assertIn("report_missing_or_invalid", result["completion"]["reasons"])
        result, metadata = self.run_case({"context": 1, "exit_code": 0, "termination_reason": None}, edit_fixture=True)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(metadata["fixture_edits_flagged"])
        self.assertIn("fixture_edits_detected", result["completion"]["reasons"])

    def test_refused_precondition_and_batch_outcome_are_not_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            study, state = make_study(Path(temporary))
            (study / "arms" / "arm-a" / "run").mkdir()
            with mock.patch.object(runner, "validate_study_inputs", return_value={}):
                result = runner.run_arm(study, state, FakeRuntime({"exit_code": 0, "termination_reason": None}), "arm-a")
        self.assertEqual(result["status"], "refused_existing_run")
        self.assertEqual(runner.batch_status([{"status": "completed"}]), "completed")
        self.assertEqual(runner.batch_status([{"status": "completed"}, {"status": "incomplete"}]), "incomplete")
        self.assertEqual(runner.batch_status([{"status": "completed"}, {"status": "failed"}]), "failed")

    def test_invalid_study_inputs_refuse_before_launch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            study, state = make_study(Path(temporary))
            runtime = FakeRuntime({"context": 1, "exit_code": 0, "termination_reason": None})
            with mock.patch.object(runner, "validate_study_inputs", side_effect=ValueError("frozen input hash does not match")):
                result = runner.run_arm(study, state, runtime, "arm-a")
            self.assertEqual(result["status"], "not_started_study_inputs_invalid")
            self.assertIsNone(runtime.workspace)
            self.assertFalse((study / "launch-ledger.json").exists())
            self.assertFalse((study / "arms" / "arm-a" / "run").exists())


class StudyInputValidationTest(unittest.TestCase):
    def test_read_study_rejects_tampered_initialized_study(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            study = initialize_study(Path(temporary))
            self.assertEqual(runner.read_study(study)[0], study.resolve())
            frozen_runner = study / "frozen" / "runner.py"
            frozen_runner.write_text(frozen_runner.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "frozen input hash"):
                runner.read_study(study)

    def test_tampered_initialized_study_refuses_startup_before_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            study = initialize_study(Path(temporary))
            frozen_runner = study / "frozen" / "runner.py"
            frozen_runner.write_text(frozen_runner.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
            runtime = FakeRuntime({"context": 1, "exit_code": 0, "termination_reason": None})
            result = runner.run_arm(study, runner.json_file(study / "study.json"), runtime, "not-prepared")
            self.assertEqual(result["status"], "not_started_study_inputs_invalid")
            self.assertIsNone(runtime.workspace)
            self.assertFalse((study / "launch-ledger.json").exists())

    def test_read_study_rejects_calibration_failed_with_consistent_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            study = initialize_study(Path(temporary))
            calibration_path = study / "private" / "oracle-calibration.json"
            calibration = runner.json_file(calibration_path)
            calibration["passed"] = False
            runner.write_json(calibration_path, calibration)
            manifest_path = study / "frozen-inputs.json"
            manifest = runner.json_file(manifest_path)
            manifest["private/oracle-calibration.json"] = runner.sha256(calibration_path)
            runner.write_json(manifest_path, manifest)
            state = runner.json_file(study / "study.json")
            state["status"] = "calibration_failed"
            state["hashes"]["oracle_calibration"] = runner.sha256(calibration_path)
            state["hashes"]["frozen_inputs_manifest"] = runner.sha256(manifest_path)
            runner.write_json(study / "study.json", state)
            with self.assertRaisesRegex(ValueError, "study status is not ready|oracle calibration did not pass"):
                runner.read_study(study)


if __name__ == "__main__":
    unittest.main()
