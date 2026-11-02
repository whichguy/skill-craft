#!/usr/bin/env python3
"""Focused tests for ShipLoop's run-local current-spec storage."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_current_spec as current_spec  # noqa: E402
import shiploop_store as store  # noqa: E402


def state_for(repo: Path) -> dict[str, object]:
    return {
        "version": 12,
        "run_id": "nav-test-run",
        "repo": str(repo.resolve()),
        "spec_root": "",
    }


def initialize(run: Path, state: dict[str, object]) -> None:
    writes = current_spec.initialize_writes(run, state)
    state["spec_root"] = str(run.resolve())
    store.transaction(run, writes)


class CurrentSpecStorageTests(unittest.TestCase):
    def make_repo(self, base: Path) -> Path:
        repo = base / "repo"
        (repo / "docs" / "shiploop").mkdir(parents=True)
        return repo

    def test_init_preserves_exact_utf8_crlf_and_binds_prior_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo = self.make_repo(base)
            source = repo / "docs" / "shiploop" / "spec.md"
            original = "# Café 🔧\r\n\r\nR-1: Keep exact bytes.\r\n"
            raw = original.encode("utf-8")
            source.write_bytes(raw)
            (repo / "docs" / "shiploop" / "architecture.md").write_bytes("AD-1: naïve\r\n".encode("utf-8"))
            (repo / "docs" / "shiploop" / "environment.md").write_bytes("# Tests\r\n✓ pytest\r\n".encode("utf-8"))
            run = base / "run"
            run.mkdir()
            state = state_for(repo)

            writes = current_spec.initialize_writes(run, state)

            self.assertEqual(writes["current-spec.md"].encode("utf-8"), raw)
            self.assertEqual(writes["spec/prior-spec.md"].encode("utf-8"), raw)
            self.assertEqual(source.read_bytes(), raw)  # initialization does not mutate repository sources
            initialize(run, state)
            self.assertEqual(current_spec.path(state).read_bytes(), raw)
            self.assertEqual(current_spec.prior_text(state), original)
            self.assertEqual(current_spec.prior_snapshot(state, "architecture"), "AD-1: naïve\r\n")
            self.assertEqual(current_spec.prior_snapshot(state, "environment"), "# Tests\r\n✓ pytest\r\n")
            self.assertEqual(current_spec.digest(state), hashlib.sha256(raw).hexdigest())
            self.assertEqual(current_spec.assert_binding(run, state)["repo"], str(repo.resolve()))

    def test_missing_prior_spec_is_explicit_and_candidate_starts_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo = self.make_repo(base)
            run = base / "run"
            run.mkdir()
            state = state_for(repo)

            writes = current_spec.initialize_writes(run, state)

            self.assertEqual(writes["current-spec.md"], "")
            self.assertNotIn("spec/prior-spec.md", writes)
            initialize(run, state)
            metadata = current_spec.assert_binding(run, state)["snapshots"]["spec"]
            self.assertEqual(metadata, {"path": "spec/prior-spec.md", "present": False, "sha256": None})
            self.assertIsNone(current_spec.prior_snapshot(state, "spec"))
            self.assertEqual(current_spec.prior_text(state), "")
            self.assertEqual(current_spec.digest(state), hashlib.sha256(b"").hexdigest())

    def test_binding_rejects_version_run_root_and_repo_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo = self.make_repo(base)
            other_repo = self.make_repo(base / "other")
            run = base / "run"
            other_run = base / "other-run"
            run.mkdir()
            other_run.mkdir()
            state = state_for(repo)
            initialize(run, state)

            for changes, explicit_root in (
                ({"version": 11}, run),
                ({"run_id": "nav-other-run"}, run),
                ({"spec_root": str(other_run.resolve())}, run),
                ({"repo": str(other_repo.resolve())}, run),
            ):
                with self.subTest(changes=changes):
                    changed = {**state, **changes}
                    with self.assertRaises(current_spec.SpecError):
                        current_spec.assert_binding(explicit_root, changed)
            with self.assertRaises(current_spec.SpecError):
                current_spec.assert_binding(other_run, state)

    def test_unbound_state_and_missing_candidate_or_manifest_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo = self.make_repo(base)
            run = base / "run"
            run.mkdir()
            state = state_for(repo)
            with self.assertRaises(current_spec.SpecError):
                current_spec.path(state)
            initialize(run, state)
            candidate = run / current_spec.CANDIDATE
            candidate.unlink()
            with self.assertRaises(current_spec.SpecError):
                current_spec.assert_binding(run, state)
            with self.assertRaises(current_spec.SpecError):
                current_spec.path(state)

    def test_missing_or_malformed_binding_manifest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo = self.make_repo(base)
            run = base / "run"
            run.mkdir()
            state = state_for(repo)
            initialize(run, state)
            manifest = run / current_spec.BINDING
            exact = manifest.read_bytes()

            manifest.unlink()
            with self.assertRaises(current_spec.SpecError):
                current_spec.assert_binding(run, state)

            manifest.write_text("not a ShipLoop record\n", encoding="utf-8")
            with self.assertRaises(current_spec.SpecError):
                current_spec.assert_binding(run, state)

            manifest.write_bytes(exact)
            current_spec.assert_binding(run, state)

    def test_prior_snapshot_tampering_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo = self.make_repo(base)
            (repo / "docs" / "shiploop" / "spec.md").write_text("R-1: Original\n", encoding="utf-8")
            run = base / "run"
            run.mkdir()
            state = state_for(repo)
            initialize(run, state)

            (run / "spec" / "prior-spec.md").write_text("R-1: Changed\n", encoding="utf-8")
            with self.assertRaises(current_spec.SpecError):
                current_spec.prior_text(state)
            with self.assertRaises(current_spec.SpecError):
                current_spec.assert_binding(run, state)

    def test_initialization_never_reseeds_an_existing_or_bound_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo = self.make_repo(base)
            original = repo / "docs" / "shiploop" / "spec.md"
            original.write_text("R-1: Initial\n", encoding="utf-8")
            run = base / "run"
            run.mkdir()
            state = state_for(repo)
            initialize(run, state)
            (run / current_spec.CANDIDATE).write_text("R-1: Edited current intent\n", encoding="utf-8")
            original.write_text("R-1: Later repo content\n", encoding="utf-8")

            with self.assertRaises(current_spec.SpecError):
                current_spec.initialize_writes(run, state)
            unbound_retry = {**state, "spec_root": ""}
            with self.assertRaises(current_spec.SpecError):
                current_spec.initialize_writes(run, unbound_retry)
            self.assertEqual((run / current_spec.CANDIDATE).read_text(encoding="utf-8"),
                             "R-1: Edited current intent\n")
            self.assertEqual(current_spec.prior_text(state), "R-1: Initial\n")

    def test_step_baseline_is_once_only_and_bound_to_run_and_plan_action(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo = self.make_repo(base)
            (repo / "docs" / "shiploop" / "spec.md").write_text("R-1: Prior\n", encoding="utf-8")
            run = base / "run"
            run.mkdir()
            state = state_for(repo)
            initialize(run, state)
            candidate = current_spec.path(state)
            accepted = "R-1: Accepted current candidate\r\n"
            candidate.write_bytes(accepted.encode("utf-8"))

            writes = current_spec.step_snapshot_writes(state, "step-plan-1")
            self.assertEqual(writes["spec/steps/step-plan-1.md"].encode("utf-8"), accepted.encode("utf-8"))
            store.transaction(run, writes)
            self.assertEqual(current_spec.step_baseline(state, "step-plan-1"), accepted)

            candidate.write_text("R-1: Later candidate\n", encoding="utf-8")
            self.assertEqual(current_spec.step_snapshot_writes(state, "step-plan-1"), {})
            self.assertEqual(current_spec.step_baseline(state, "step-plan-1"), accepted)
            with self.assertRaises(current_spec.SpecError):
                current_spec.step_baseline(state, "step-plan-2")
            with self.assertRaises(current_spec.SpecError):
                current_spec.step_snapshot_writes(state, "../step-plan-1")

    def test_step_snapshot_manifest_and_content_tampering_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo = self.make_repo(base)
            run = base / "run"
            run.mkdir()
            state = state_for(repo)
            initialize(run, state)
            store.transaction(run, current_spec.step_snapshot_writes(state, "plan-accepted"))
            baseline = run / "spec" / "steps" / "plan-accepted.md"
            baseline.write_text("tampered\n", encoding="utf-8")
            with self.assertRaises(current_spec.SpecError):
                current_spec.step_baseline(state, "plan-accepted")

            # Repair the content but change the manifest identity; neither is silently rewritten.
            baseline.write_text("", encoding="utf-8")
            manifest = run / "spec" / "steps" / "plan-accepted.manifest.md"
            record = store.read_record(manifest)
            record["run_id"] = "nav-someone-else"
            store.atomic_write_text(manifest, store.dumps(record, title="ShipLoop step current-spec baseline"))
            with self.assertRaises(current_spec.SpecError):
                current_spec.step_baseline(state, "plan-accepted")
            with self.assertRaises(current_spec.SpecError):
                current_spec.step_snapshot_writes(state, "plan-accepted")

    def test_repository_and_run_snapshot_symlinks_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo = self.make_repo(base)
            external = base / "external.md"
            external.write_text("R-1: Outside\n", encoding="utf-8")
            source = repo / "docs" / "shiploop" / "spec.md"
            source.symlink_to(external)
            run = base / "run"
            run.mkdir()
            with self.assertRaises(current_spec.SpecError):
                current_spec.initialize_writes(run, state_for(repo))

            source.unlink()
            state = state_for(repo)
            initialize(run, state)
            candidate = run / current_spec.CANDIDATE
            candidate.unlink()
            candidate.symlink_to(external)
            with self.assertRaises(current_spec.SpecError):
                current_spec.path(state)

    def test_prior_and_step_snapshot_symlinks_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo = self.make_repo(base)
            (repo / "docs" / "shiploop" / "spec.md").write_text("R-1: Prior\n", encoding="utf-8")
            run = base / "run"
            run.mkdir()
            state = state_for(repo)
            initialize(run, state)
            prior = run / "spec" / "prior-spec.md"
            prior.unlink()
            prior.symlink_to(repo / "docs" / "shiploop" / "spec.md")
            with self.assertRaises(current_spec.SpecError):
                current_spec.assert_binding(run, state)

            prior.unlink()
            prior.write_text("R-1: Prior\n", encoding="utf-8")
            current_spec.assert_binding(run, state)
            store.transaction(run, current_spec.step_snapshot_writes(state, "plan-safe"))
            baseline = run / "spec" / "steps" / "plan-safe.md"
            baseline.unlink()
            baseline.symlink_to(repo / "docs" / "shiploop" / "spec.md")
            with self.assertRaises(current_spec.SpecError):
                current_spec.step_baseline(state, "plan-safe")


if __name__ == "__main__":
    unittest.main(verbosity=2)
