#!/usr/bin/env python3
"""Focused tests for final promotion of a run-local current spec."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_current_spec as current_spec  # noqa: E402
import shiploop_spec_promotion as promotion  # noqa: E402
import shiploop_store as store  # noqa: E402


class SimulatedCrash(RuntimeError):
    """Models interruption after or before the aggregate replacement."""


class SpecPromotionTests(unittest.TestCase):
    def make_run(self, base: Path, prior: str | None = None, candidate: str = "") -> tuple[Path, Path, dict[str, object]]:
        repo = base / "repo"
        home = repo / "docs" / "shiploop"
        home.mkdir(parents=True)
        if prior is not None:
            (home / "spec.md").write_bytes(prior.encode("utf-8"))
        run = base / "run"
        run.mkdir()
        state: dict[str, object] = {
            "version": 12,
            "run_id": "nav-promotion-run",
            "repo": str(repo.resolve()),
            "spec_root": "",
            "stage": "handoff",
            "action": {"id": "handoff-final", "stage": "handoff"},
        }
        writes = current_spec.initialize_writes(run, state)
        state["spec_root"] = str(run.resolve())
        store.transaction(run, writes)
        if candidate:
            current_spec.path(state).write_bytes(candidate.encode("utf-8"))
        return repo, run, state

    def reconciliation(self, state: dict[str, object], summary: str = "Reviewed current spec and preserved prior intent.") -> dict[str, str]:
        return {**promotion.hashes(state), "summary": summary}

    def test_hashes_and_reconciliation_validate_exact_prior_and_current(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo, _run, state = self.make_run(
                Path(temporary), "# Prior\r\nR-1: Existing need\r\n", "# Current\r\nR-1: Existing need\r\nR-2: New need ✓\r\n")
            self.assertEqual(promotion.hashes(state), {
                "current_sha256": hashlib.sha256(current_spec.path(state).read_bytes()).hexdigest(),
                "prior_sha256": hashlib.sha256(b"# Prior\r\nR-1: Existing need\r\n").hexdigest(),
            })
            record = self.reconciliation(state)
            self.assertIsNone(promotion.validate(state, record))
            with self.assertRaises(promotion.PromotionError):
                promotion.validate(state, {**record, "extra": "not allowed"})
            with self.assertRaises(promotion.PromotionError):
                promotion.validate(state, {**record, "summary": "  "})
            with self.assertRaises(promotion.PromotionError):
                promotion.promote(Path(state["spec_root"]), state, "handoff-other", record)
            self.assertFalse((repo / promotion.AGGREGATE).is_symlink())

    def test_absent_aggregate_is_created_with_exact_candidate_bytes_and_retry_is_identical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo, run, state = self.make_run(Path(temporary), candidate="# Résumé\r\nR-1: Full current intent 🌱\r\n")
            candidate = current_spec.path(state).read_bytes()
            self.assertEqual(promotion.aggregate_refusal(state), "")

            first = promotion.promote(run, state, "handoff-final", self.reconciliation(state))

            aggregate = repo / promotion.AGGREGATE
            self.assertEqual(aggregate.read_bytes(), candidate)
            self.assertEqual(first["status"], "promoted")
            self.assertEqual(first["candidate_sha256"], hashlib.sha256(candidate).hexdigest())
            self.assertEqual(store.read_record(run / promotion.JOURNAL), first)
            self.assertEqual(promotion.promote(run, state, "handoff-final", self.reconciliation(state)), first)
            self.assertEqual(promotion.aggregate_refusal(state), "")

    def test_existing_aggregate_is_replaced_by_the_full_candidate_not_a_delta(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            prior = "# Prior spec\r\nR-1: Preserve this requirement\r\n"
            candidate = "# Consolidated current spec\r\nR-1: Preserve this requirement\r\nR-2: Add the new behavior\r\n"
            repo, run, state = self.make_run(Path(temporary), prior, candidate)
            aggregate = repo / promotion.AGGREGATE
            prior_bytes = aggregate.read_bytes()
            self.assertEqual(prior_bytes, prior.encode("utf-8"))

            record = promotion.promote(run, state, "handoff-final", self.reconciliation(state))

            self.assertEqual(aggregate.read_bytes(), candidate.encode("utf-8"))
            self.assertEqual(record["prior_sha256"], hashlib.sha256(prior_bytes).hexdigest())
            self.assertTrue(promotion.aggregate_refusal(state) == "")

    def test_interrupted_write_recovers_from_pending_journal_and_finalizes_after_readback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate_text = "# Final spec\r\nR-1: Keep prior\r\nR-2: Add item\r\n"
            repo, run, state = self.make_run(Path(temporary), "R-1: Keep prior\r\n", candidate_text)
            aggregate = repo / promotion.AGGREGATE
            real_write = store.atomic_write_text

            def crash_after_aggregate_write(target: Path, text: str) -> None:
                real_write(target, text)
                if Path(target).resolve() == aggregate.resolve():
                    raise SimulatedCrash("stopped after aggregate replacement")

            with patch.object(store, "atomic_write_text", side_effect=crash_after_aggregate_write):
                with self.assertRaises(SimulatedCrash):
                    promotion.promote(run, state, "handoff-final", self.reconciliation(state))

            pending = store.read_record(run / promotion.JOURNAL)
            self.assertEqual(pending["status"], "pending")
            self.assertEqual(aggregate.read_bytes(), candidate_text.encode("utf-8"))
            self.assertEqual(promotion.aggregate_refusal(state), "")

            recovered = promotion.promote(run, state, "handoff-final", self.reconciliation(state))
            self.assertEqual(recovered["status"], "promoted")
            self.assertEqual(store.read_record(run / promotion.JOURNAL), recovered)
            self.assertEqual(promotion.promote(run, state, "handoff-final", self.reconciliation(state)), recovered)

    def test_candidate_drift_after_pending_record_refuses_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            prior = "R-1: Preserve\n"
            repo, run, state = self.make_run(Path(temporary), prior, "R-1: Reviewed\nR-2: New\n")
            prior_bytes = prior.encode("utf-8")
            real_write = store.atomic_write_text

            def stop_before_aggregate_write(target: Path, text: str) -> None:
                if Path(target).resolve() == (repo / promotion.AGGREGATE).resolve():
                    raise SimulatedCrash("stopped before aggregate replacement")
                real_write(target, text)

            reviewed = self.reconciliation(state)
            with patch.object(store, "atomic_write_text", side_effect=stop_before_aggregate_write):
                with self.assertRaises(SimulatedCrash):
                    promotion.promote(run, state, "handoff-final", reviewed)
            self.assertEqual(store.read_record(run / promotion.JOURNAL)["status"], "pending")

            current_spec.path(state).write_text("R-1: Revised after review\nR-2: New\n", encoding="utf-8")
            self.assertNotEqual(promotion.aggregate_refusal(state), "")
            with self.assertRaises(promotion.PromotionError):
                promotion.promote(run, state, "handoff-final", reviewed)
            self.assertEqual((repo / promotion.AGGREGATE).read_bytes(), prior_bytes)

    def test_external_source_drift_and_unjournaled_equal_candidate_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo, run, state = self.make_run(Path(temporary), "R-1: Initial\n", "R-1: Initial\nR-2: Reviewed\n")
            aggregate = repo / promotion.AGGREGATE
            aggregate.write_text("R-1: External edit\n", encoding="utf-8")
            self.assertNotEqual(promotion.aggregate_refusal(state), "")
            with self.assertRaises(promotion.PromotionError):
                promotion.promote(run, state, "handoff-final", self.reconciliation(state))
            self.assertFalse((run / promotion.JOURNAL).exists())

        with tempfile.TemporaryDirectory() as temporary:
            repo, run, state = self.make_run(Path(temporary), prior="", candidate="R-1: Current\n")
            (repo / promotion.AGGREGATE).unlink()
            self.assertNotEqual(promotion.aggregate_refusal(state), "")
            with self.assertRaises(promotion.PromotionError):
                promotion.promote(run, state, "handoff-final", self.reconciliation(state))

        with tempfile.TemporaryDirectory() as temporary:
            repo, run, state = self.make_run(Path(temporary), candidate="R-1: Candidate only\n")
            aggregate = repo / promotion.AGGREGATE
            aggregate.write_bytes(current_spec.path(state).read_bytes())
            self.assertNotEqual(promotion.aggregate_refusal(state), "")
            with self.assertRaises(promotion.PromotionError):
                promotion.promote(run, state, "handoff-final", self.reconciliation(state))
            self.assertFalse((run / promotion.JOURNAL).exists())

    def test_journal_identity_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo, run, state = self.make_run(Path(temporary), "R-1: Prior\n", "R-1: Current\nR-2: New\n")
            real_write = store.atomic_write_text

            def stop_before_aggregate_write(target: Path, text: str) -> None:
                if Path(target).resolve() == (repo / promotion.AGGREGATE).resolve():
                    raise SimulatedCrash("leave pending record")
                real_write(target, text)

            with patch.object(store, "atomic_write_text", side_effect=stop_before_aggregate_write):
                with self.assertRaises(SimulatedCrash):
                    promotion.promote(run, state, "handoff-final", self.reconciliation(state))
            journal = run / promotion.JOURNAL
            record = store.read_record(journal)
            record["run_id"] = "nav-other-run"
            store.atomic_write_text(journal, store.dumps(record, title="ShipLoop spec promotion"))

            self.assertNotEqual(promotion.aggregate_refusal(state), "")
            with self.assertRaises(promotion.PromotionError):
                promotion.promote(run, state, "handoff-final", self.reconciliation(state))
            self.assertEqual((repo / promotion.AGGREGATE).read_bytes(), b"R-1: Prior\n")

    def test_prior_requirement_ids_cannot_disappear(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _repo, run, state = self.make_run(Path(temporary), "R-1: Required prior entry\n", "R-2: New only\n")
            reconciliation = self.reconciliation(state)
            with self.assertRaisesRegex(promotion.PromotionError, "R-1"):
                promotion.validate(state, reconciliation)
            with self.assertRaisesRegex(promotion.PromotionError, "R-1"):
                promotion.promote(run, state, "handoff-final", reconciliation)
            self.assertFalse((run / promotion.JOURNAL).exists())

    def test_symlink_and_hardlinked_aggregate_paths_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo, run, state = self.make_run(base, candidate="R-1: Candidate\n")
            outside = base / "outside.md"
            outside.write_text("outside\n", encoding="utf-8")
            aggregate = repo / promotion.AGGREGATE
            aggregate.symlink_to(outside)
            self.assertNotEqual(promotion.aggregate_refusal(state), "")
            with self.assertRaises(promotion.PromotionError):
                promotion.promote(run, state, "handoff-final", self.reconciliation(state))
            self.assertEqual(outside.read_text(encoding="utf-8"), "outside\n")

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo, run, state = self.make_run(base, candidate="R-1: Candidate\n")
            external_dir = base / "external"
            external_dir.mkdir()
            (external_dir / "shiploop").mkdir()
            (external_dir / promotion.AGGREGATE.split("/")[-1]).write_text("outside\n", encoding="utf-8")
            (repo / "docs" / "shiploop").rmdir()
            (repo / "docs").rmdir()
            (repo / "docs").symlink_to(external_dir, target_is_directory=True)
            self.assertNotEqual(promotion.aggregate_refusal(state), "")
            with self.assertRaises(promotion.PromotionError):
                promotion.promote(run, state, "handoff-final", self.reconciliation(state))

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo, run, state = self.make_run(base, candidate="R-1: Candidate\n")
            external = base / "external.md"
            external.write_text("external\n", encoding="utf-8")
            (repo / promotion.AGGREGATE).unlink(missing_ok=True)
            (repo / promotion.AGGREGATE).hardlink_to(external)
            with self.assertRaises(promotion.PromotionError):
                promotion.promote(run, state, "handoff-final", self.reconciliation(state))
            self.assertEqual(external.read_text(encoding="utf-8"), "external\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
