#!/usr/bin/env python3
"""Focused identity checks for Improve's run-local current-spec review."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))

import shiploop_current_spec as current_spec  # noqa: E402
import shiploop_improve_changes as improve_changes  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_standalone_improve as standalone  # noqa: E402
import shiploop_store as store  # noqa: E402


class SpecReviewIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="shiploop-spec-review-identity-")
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name).resolve()
        self.repo = base / "repo"
        self.run = base / "run"
        self.repo.mkdir()
        self.run.mkdir()
        (self.repo / "docs/shiploop").mkdir(parents=True)
        (self.repo / "docs/shiploop/spec.md").write_bytes(
            "# Product\r\n\r\n## Requirements\r\nR-1: keep ñ and exact line endings\r\n".encode("utf-8"))
        self.state = self._initialize_run(self.repo, self.run, "nav-identity-01")
        self.action = "A-review-01"
        skill = standalone.resolve_skill(str(ROOT / "skills/improve/SKILL.md"))
        self.child = standalone.binding(self.state, self.action, "document", {}, skill, improve_action="A-improve-01")
        self.state["active_improve"] = self.child
        self.reviews = standalone.receipt_path(self.child).parent / "reviews"
        self.reviews.mkdir(parents=True)

    @staticmethod
    def _initialize_run(repo: Path, run: Path, run_id: str) -> dict:
        state = navigator.new_state(str(repo.resolve()), "Review the exact current spec.")
        state["run_id"] = run_id
        writes = current_spec.initialize_writes(run, state)
        state["spec_root"] = str(run.resolve())
        writes["state.md"] = store.dumps(state, "ShipLoop navigator state")
        store.transaction(run, writes)
        return state

    def _bind(self) -> tuple[str, bytes]:
        raw = current_spec.path(self.state).read_bytes()
        for relative, text in improve_changes.bind_writes(self.run, self.repo, self.action, self.state).items():
            store.atomic_write_text(self.run / relative, text)
        record = store.read_record(self.run / improve_changes.bind_path(self.action))
        self.assertEqual(record["current_spec"], hashlib.sha256(raw).hexdigest())
        self.assertEqual((self.run / improve_changes.bind_spec_path(self.action)).read_bytes(), raw)
        return record["current_spec"], raw

    def _pass(self, number: int, digest: str) -> Path:
        path = self.reviews / f"pass-{number}.json"
        store.atomic_write_text(path, json.dumps({"pass": number, "current_spec": digest}) + "\n")
        return path

    def test_reads_passes_from_the_bound_child_and_detects_current_edits(self) -> None:
        digest, _raw = self._bind()
        self._pass(1, digest)
        self.assertEqual(improve_changes.current_spec_changed_since_review(self.run, self.state, self.action), False)

        candidate = current_spec.path(self.state)
        candidate.write_bytes(candidate.read_bytes() + b"R-2: changed after review\r\n")
        self.assertEqual(improve_changes.current_spec_changed_since_review(self.run, self.state, self.action), True)

    def test_missing_or_wrong_action_evidence_is_unknown(self) -> None:
        self._bind()
        self.assertIsNone(improve_changes.current_spec_changed_since_review(self.run, self.state, self.action))
        self.assertIsNone(improve_changes.current_spec_changed_since_review(self.run, self.state, "A-other"))
        with self.assertRaisesRegex(navigator.NavigatorError, "no valid current-spec digest"):
            navigator._improve_change_gate(None, self.run, self.state, "A-other", self.child, {})

    def test_restart_uses_newest_pass_not_archived_higher_number(self) -> None:
        digest, _raw = self._bind()
        archived_reviews = self.reviews.with_name("reviews.stopped-20261102T010203Z")
        archived_reviews.mkdir()
        archived = archived_reviews / "pass-9.json"
        store.atomic_write_text(archived, json.dumps({"pass": 9, "current_spec": "0" * 64}) + "\n")
        restarted = self._pass(1, digest)
        self.assertGreater(restarted.stat().st_mtime_ns, archived.stat().st_mtime_ns)
        self.assertEqual(improve_changes.current_spec_changed_since_review(self.run, self.state, self.action), False)

    def test_import_review_record_binds_exact_current_bytes_and_run_action(self) -> None:
        self.state["accepted"] = {"A-review-01": {"outcome": "done"}}
        self.state["improve_results"] = {"A-review-01": {"runtime_phase": "complete"}}
        writes = current_spec.reviewed_writes(self.state, "A-review-01", current_spec.digest(self.state))
        for relative, text in writes.items():
            store.atomic_write_text(self.run / relative, text)
        current_spec.check_reviewed(self.state)

        with self.assertRaisesRegex(current_spec.SpecError, "changed after its accepted Improve"):
            current_spec.path(self.state).write_bytes(current_spec.path(self.state).read_bytes() + b"R-2: later\n")
            current_spec.check_reviewed(self.state)

        with self.assertRaisesRegex(current_spec.SpecError, "accepted completed Improve"):
            current_spec.reviewed_writes(self.state, "A-other", current_spec.digest(self.state))

    def test_review_record_from_another_run_is_rejected(self) -> None:
        self.state["accepted"] = {"A-review-01": {"outcome": "done"}}
        self.state["improve_results"] = {"A-review-01": {"runtime_phase": "complete"}}
        for relative, text in current_spec.reviewed_writes(
                self.state, "A-review-01", current_spec.digest(self.state)).items():
            store.atomic_write_text(self.run / relative, text)

        other_run = self.run.parent / "other-run"
        other_run.mkdir()
        other_state = self._initialize_run(self.repo, other_run, "nav-identity-02")
        store.atomic_write_text(other_run / current_spec.REVIEWED,
                                (self.run / current_spec.REVIEWED).read_text(encoding="utf-8"))
        with self.assertRaisesRegex(current_spec.SpecError, "belongs to another run"):
            current_spec.check_reviewed(other_state)

    def test_an_edit_between_the_import_gate_and_recording_cannot_become_reviewed(self) -> None:
        digest, _raw = self._bind()
        self._pass(1, digest)
        navigator._improve_change_gate(None, self.run, self.state, self.action, self.child, {})
        self.state["accepted"] = {self.action: {"outcome": "done"}}
        self.state["improve_results"] = {self.action: {"runtime_phase": "complete"}}
        candidate = current_spec.path(self.state)
        candidate.write_bytes(candidate.read_bytes() + b"R-2: concurrent, unreviewed edit\r\n")

        # Acceptance must use the immutable pass identity, never bless a fresh
        # hash of the file after the gate returned.
        reviewed = improve_changes.current_spec_review_digest(self.run, self.state, self.action)
        self.assertEqual(reviewed, digest)
        with self.assertRaisesRegex(current_spec.SpecError, "changed before its Improve acceptance"):
            current_spec.reviewed_writes(self.state, self.action, reviewed)
        self.assertFalse((self.run / current_spec.REVIEWED).exists())


if __name__ == "__main__":
    unittest.main()
