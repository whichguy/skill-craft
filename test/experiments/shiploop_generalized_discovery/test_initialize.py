#!/usr/bin/env python3
"""Focused no-model checks for generalized-discovery study initialization."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest


HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


initializer = load_module("generalized_discovery_initializer_under_test", HERE / "initialize.py")
prepare = load_module("generalized_discovery_prepare_under_test", HERE / "prepare.py")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class InitializeStudyTest(unittest.TestCase):
    def _inputs(self, root: Path) -> tuple[Path, Path]:
        baseline = (HERE.parents[2] / "skills" / "shiploop" / "references" / "research-loop.md").read_text(encoding="utf-8")
        candidate = root / "candidate.md"
        candidate.write_text(baseline + "\n\nCandidate-only discovery wording.\n", encoding="utf-8")
        plan = root / "plan.md"
        plan.write_text("# Frozen experiment plan\n\nLocal-only setup.\n", encoding="utf-8")
        return candidate, plan

    def _study(self, root: Path) -> Path:
        candidate, plan = self._inputs(root)
        study = root / "study"
        initializer.initialize(study, candidate, plan)
        return study

    def _assert_refused_before_fixture_load(self, study: Path) -> None:
        calls: list[Path] = []
        original = prepare.load_fixtures

        def forbidden(path: Path):
            calls.append(path)
            raise AssertionError("fixture module must not load after input validation fails")

        prepare.load_fixtures = forbidden
        try:
            with self.assertRaises(ValueError):
                prepare.prepare_pair(study, "f1", 0)
        finally:
            prepare.load_fixtures = original
        self.assertEqual(calls, [])
        self.assertEqual(list((study / "arms").iterdir()), [])

    def _refresh_manifest_state(self, study: Path) -> None:
        manifest_path = study / "frozen-inputs.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        calibration = study / "private" / "oracle-calibration.json"
        manifest["private/oracle-calibration.json"] = sha256(calibration)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        state_path = study / "study.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["hashes"]["frozen_inputs_manifest"] = sha256(manifest_path)
        state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def test_creates_calibrated_frozen_study_and_matched_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate, plan = self._inputs(root)
            study = root / "study"
            copy_started: list[float] = []
            original_copy = initializer._copy_inputs

            def recording_copy(*args):
                copy_started.append(time.time())
                return original_copy(*args)

            initializer._copy_inputs = recording_copy
            try:
                result = initializer.initialize(study, candidate, plan)
            finally:
                initializer._copy_inputs = original_copy

            self.assertTrue(result["calibration_passed"])
            self.assertEqual(result["status"], "ready_to_prepare")
            state = json.loads((study / "study.json").read_text(encoding="utf-8"))
            self.assertEqual(state["schema"], "generalized-discovery-study/1")
            self.assertEqual(state["hard_deadline_epoch"] - state["started_epoch"], 90 * 60)
            self.assertEqual(state["closeout_start_epoch"] - state["started_epoch"], 75 * 60)
            self.assertEqual(state["aggregate_active_limit_seconds"], 180 * 60)
            self.assertIn("Coordinator responsibility", state["aggregate_active_limit_note"])
            self.assertEqual(state["max_arm_launches"], 12)
            self.assertEqual(state["parallel"], 3)
            self.assertEqual(state["seconds_per_arm"], 480)
            self.assertEqual(state["calls_per_arm"], 32)
            self.assertEqual(state["exploration_seconds"], 360)
            self.assertEqual(state["exploration_calls"], 24)
            self.assertEqual(state["blind_order_seed"], 29017)
            self.assertEqual(state["arms"], {})
            self.assertLessEqual(state["started_epoch"], copy_started[0])

            frozen = study / "frozen"
            self.assertTrue((frozen / "study_inputs.py").is_file())
            calibration = json.loads((study / "private" / "oracle-calibration.json").read_text(encoding="utf-8"))
            self.assertTrue(calibration["passed"])
            self.assertEqual(calibration["bindings"]["oracle.py"], sha256(frozen / "oracle.py"))
            self.assertEqual(calibration["bindings"]["fixtures.py"], sha256(frozen / "fixtures.py"))
            self.assertEqual(calibration["bindings"]["PUBLIC_CONTRACTS.md"], sha256(frozen / "PUBLIC_CONTRACTS.md"))

            manifest_path = study / "frozen-inputs.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertNotIn("study.json", manifest)
            self.assertIn("private/oracle-calibration.json", manifest)
            self.assertEqual(state["hashes"]["frozen_inputs_manifest"], sha256(manifest_path))

            names = prepare.prepare_pair(study, "f1", 0)
            self.assertEqual(len(names), 2)
            first = json.loads((study / "arms" / names[0] / "input-hashes.json").read_text(encoding="utf-8"))
            second = json.loads((study / "arms" / names[1] / "input-hashes.json").read_text(encoding="utf-8"))
            self.assertEqual(set(first), set(second))
            changed = {name for name in first if first[name] != second[name]}
            self.assertEqual(changed, {"guidance/research-loop.md"})

    def test_tampered_study_inputs_refuse_before_fixture_load(self) -> None:
        def frozen_file(study: Path) -> None:
            path = study / "frozen" / "fixtures.py"
            path.write_text(path.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")

        def guide(study: Path) -> None:
            path = study / "guides" / "baseline.md"
            path.write_text(path.read_text(encoding="utf-8") + "\nTampered guide.\n", encoding="utf-8")

        def unexpected_file(study: Path) -> None:
            (study / "guides" / "unexpected.md").write_text("unexpected\n", encoding="utf-8")

        def symlink(study: Path) -> None:
            (study / "guides" / "unexpected-link.md").symlink_to("baseline.md")

        def calibration_parent_symlink(study: Path) -> None:
            private = study / "private"
            relocated = study / "private-relocated"
            private.rename(relocated)
            private.symlink_to(relocated, target_is_directory=True)

        def failed_calibration(study: Path) -> None:
            path = study / "private" / "oracle-calibration.json"
            calibration = json.loads(path.read_text(encoding="utf-8"))
            calibration["passed"] = False
            path.write_text(json.dumps(calibration, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            self._refresh_manifest_state(study)

        def missing_manifest(study: Path) -> None:
            (study / "frozen-inputs.json").unlink()

        def manifest_hash_mismatch(study: Path) -> None:
            state_path = study / "study.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["hashes"]["frozen_inputs_manifest"] = "0" * 64
            state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        def unready_status(study: Path) -> None:
            state_path = study / "study.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["status"] = "initializing"
            state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")

        cases = {
            "frozen_file": frozen_file,
            "guide": guide,
            "unexpected_file": unexpected_file,
            "symlink": symlink,
            "calibration_parent_symlink": calibration_parent_symlink,
            "failed_calibration": failed_calibration,
            "missing_manifest": missing_manifest,
            "manifest_hash_mismatch": manifest_hash_mismatch,
            "unready_status": unready_status,
        }
        for label, mutate in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                study = self._study(Path(temporary))
                mutate(study)
                self._assert_refused_before_fixture_load(study)

    def test_refuses_existing_destination_and_missing_inputs_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate, plan = self._inputs(root)
            existing = root / "existing-study"
            existing.mkdir()
            sentinel = existing / "keep.txt"
            sentinel.write_text("preserve\n", encoding="utf-8")
            before = sentinel.read_bytes()
            with self.assertRaises(FileExistsError):
                initializer.initialize(existing, candidate, plan)
            self.assertEqual(sentinel.read_bytes(), before)
            self.assertEqual(sorted(path.name for path in existing.iterdir()), ["keep.txt"])

            dangling = root / "dangling-study"
            dangling.symlink_to(root / "missing-target")
            with self.assertRaises(FileExistsError):
                initializer.initialize(dangling, candidate, plan)
            self.assertTrue(dangling.is_symlink())

            missing_candidate_study = root / "missing-candidate-study"
            with self.assertRaises(ValueError):
                initializer.initialize(missing_candidate_study, root / "missing-candidate.md", plan)
            self.assertFalse(missing_candidate_study.exists())

            missing_plan_study = root / "missing-plan-study"
            with self.assertRaises(ValueError):
                initializer.initialize(missing_plan_study, candidate, root / "missing-plan.md")
            self.assertFalse(missing_plan_study.exists())


if __name__ == "__main__":
    unittest.main()
