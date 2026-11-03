#!/usr/bin/env python3
"""Fail-closed and successful replay tests for current-spec run transactions."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
sys.path.insert(0, str(SCRIPTS))

import shiploop_current_spec as current_spec  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402


SPEC = "# Product\r\n\r\n## Requirements\r\n\r\n### R-1. Existing\r\nKeep exact bytes. Café.\r\n"
ARCHITECTURE = "# Architecture\r\n\r\nAD-1: preserve the established boundary.\r\n"
ENVIRONMENT = "# Environment\r\n\r\nCommands: run the focused suite.\r\n"


class SimulatedCrash(RuntimeError):
    """An injected transaction interruption after its first real target write."""


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


class CurrentSpecRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="shiploop-current-spec-recovery-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.repo = self.base / "repo"
        home = self.repo / "docs" / "shiploop"
        home.mkdir(parents=True)
        (home / "spec.md").write_bytes(SPEC.encode("utf-8"))
        (home / "architecture.md").write_bytes(ARCHITECTURE.encode("utf-8"))
        (home / "environment.md").write_bytes(ENVIRONMENT.encode("utf-8"))

    def new_state(self, root: Path) -> dict:
        root.mkdir()
        state = navigator.new_state(str(self.repo.resolve()), "Preserve current behavior and add one outcome.")
        return state

    def save_run(self, root: Path) -> dict:
        state = self.new_state(root)
        navigator.save(root, state)
        return store.read_record(root / "state.md")

    @staticmethod
    def interrupt_after_first_target(root: Path, writes: dict[str, str]) -> None:
        def crash(phase: str, index: int) -> None:
            if phase == "after-target" and index == 1:
                raise SimulatedCrash("simulated process interruption")

        with unittest.TestCase().assertRaisesRegex(SimulatedCrash, "simulated process interruption"):
            store.transaction(root, writes, fault=crash)

    def cli_next(self, root: Path) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "SHIPLOOP_PROGRESS": "off"}
        return subprocess.run([sys.executable, "-B", str(CLI), "next", "--run-dir", str(root)],
                              cwd=self.repo, env=env, capture_output=True, text=True, timeout=45)

    def test_v11_pending_transaction_is_refused_before_any_recovery_mutation(self) -> None:
        root = self.base / "v11-run"
        state = self.save_run(root)
        self.interrupt_after_first_target(root, {"recovery-marker.md": "must remain pending\n"})
        state["version"] = 11
        state.pop("spec_root")
        store.atomic_write_text(root / "state.md", store.dumps(state, "ShipLoop navigator state"))
        before = tree_bytes(root)

        refused = self.cli_next(root)

        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn("prior intent cannot be reconstructed safely", refused.stderr)
        self.assertEqual(tree_bytes(root), before)
        self.assertFalse((root / ".lock").exists())
        self.assertTrue((root / store.JOURNAL_NAME).is_file())

    def test_moved_v12_root_with_pending_transaction_is_refused_unchanged(self) -> None:
        original = self.base / "original-run"
        self.save_run(original)
        self.interrupt_after_first_target(original, {"recovery-marker.md": "must remain pending\n"})
        moved = self.base / "moved-run"
        shutil.copytree(original, moved)
        before = tree_bytes(moved)

        refused = self.cli_next(moved)

        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn("run root does not match state spec_root", refused.stderr)
        self.assertEqual(tree_bytes(moved), before)
        self.assertFalse((moved / ".lock").exists())
        self.assertTrue((moved / store.JOURNAL_NAME).is_file())
        self.assertTrue((original / store.JOURNAL_NAME).is_file())

    def test_interrupted_first_save_recovers_bound_state_and_exact_prior_bytes(self) -> None:
        root = self.base / "interrupted-init"
        state = self.new_state(root)
        real_transaction = store.transaction

        def interrupt_bootstrap(transaction_root, writes, deletes=None, **kwargs) -> None:
            self.assertIn("state.md", writes)
            self.assertIn(current_spec.BINDING, writes)
            self.assertIn(current_spec.CANDIDATE, writes)

            def crash(phase: str, index: int) -> None:
                if phase == "after-target" and index == 1:
                    raise SimulatedCrash("first-save interruption")

            return real_transaction(transaction_root, writes, deletes, fault=crash, **kwargs)

        with patch.object(store, "transaction", side_effect=interrupt_bootstrap):
            with self.assertRaisesRegex(SimulatedCrash, "first-save interruption"):
                navigator.save(root, state)

        self.assertFalse((root / "state.md").exists())
        self.assertTrue((root / store.JOURNAL_NAME).is_file())
        journal = store.read_record(root / store.JOURNAL_NAME)
        staged = {entry["path"]: entry["text"] for entry in journal["writes"]}
        self.assertEqual(staged["state.md"], store.dumps(state, "ShipLoop navigator state"))
        self.assertEqual(staged[current_spec.CANDIDATE].encode("utf-8"), SPEC.encode("utf-8"))
        self.assertEqual(staged["spec/prior-spec.md"].encode("utf-8"), SPEC.encode("utf-8"))
        self.assertEqual(staged["spec/prior-architecture.md"].encode("utf-8"), ARCHITECTURE.encode("utf-8"))
        self.assertEqual(staged["spec/prior-environment.md"].encode("utf-8"), ENVIRONMENT.encode("utf-8"))

        recovered = self.cli_next(root)

        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        self.assertFalse((root / store.JOURNAL_NAME).exists())
        saved = store.read_record(root / "state.md")
        self.assertEqual(saved["spec_root"], str(root.resolve()))
        self.assertEqual(saved["run_id"], state["run_id"])
        self.assertEqual((root / current_spec.CANDIDATE).read_bytes(), SPEC.encode("utf-8"))
        self.assertEqual((root / "spec" / "prior-spec.md").read_bytes(), SPEC.encode("utf-8"))
        self.assertEqual((root / "spec" / "prior-architecture.md").read_bytes(), ARCHITECTURE.encode("utf-8"))
        self.assertEqual((root / "spec" / "prior-environment.md").read_bytes(), ENVIRONMENT.encode("utf-8"))
        current_spec.assert_binding(root, saved)

    def test_ordinary_v12_pending_transition_recovers_on_same_run(self) -> None:
        root = self.base / "ordinary-pending"
        saved = self.save_run(root)
        self.interrupt_after_first_target(root, {"recovery-marker.md": "same-run recovery\n"})
        candidate_before = (root / current_spec.CANDIDATE).read_bytes()

        recovered = self.cli_next(root)

        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        self.assertFalse((root / store.JOURNAL_NAME).exists())
        self.assertEqual((root / "recovery-marker.md").read_text(encoding="utf-8"), "same-run recovery\n")
        self.assertEqual((root / current_spec.CANDIDATE).read_bytes(), candidate_before)
        after = store.read_record(root / "state.md")
        self.assertEqual(after["version"], 12)
        self.assertEqual(after["spec_root"], str(root.resolve()))
        self.assertEqual(after["run_id"], saved["run_id"])
        current_spec.assert_binding(root, after)

    def test_wrong_root_binding_in_real_pending_journal_is_refused_before_replay(self) -> None:
        root = self.base / "wrong-binding-run"
        saved = self.save_run(root)
        binding_path = root / current_spec.BINDING
        original_binding_bytes = binding_path.read_bytes()
        wrong_binding = store.read_record(binding_path)
        wrong_binding["root"] = str((self.base / "elsewhere").resolve())
        writes = {
            "000-already-written.md": "fault callback stops after this target\n",
            current_spec.CANDIDATE: "must not be replayed\n",
            current_spec.BINDING: store.dumps(wrong_binding, "ShipLoop current-spec binding"),
        }
        self.interrupt_after_first_target(root, writes)
        before = tree_bytes(root)
        candidate_before = (root / current_spec.CANDIDATE).read_bytes()

        refused = self.cli_next(root)

        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        self.assertIn("pending initialization binding belongs to another run", refused.stderr)
        self.assertEqual(tree_bytes(root), before)
        self.assertEqual((root / current_spec.CANDIDATE).read_bytes(), candidate_before)
        self.assertEqual(binding_path.read_bytes(), original_binding_bytes)
        self.assertEqual(store.read_record(root / "state.md"), saved)
        self.assertFalse((root / ".lock").exists())
        self.assertTrue((root / store.JOURNAL_NAME).is_file())


if __name__ == "__main__":
    unittest.main()
