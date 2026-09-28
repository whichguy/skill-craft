#!/usr/bin/env python3
"""Focused fixtures for the read-only ShipLoop progress snapshot projection."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_chain_ledger as chain_ledger  # noqa: E402
import shiploop_knowledge_home as knowledge_home  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_progress_data as progress_data  # noqa: E402
import shiploop_store as store  # noqa: E402


def _improve_receipt(stage: str) -> dict:
    return {"summary": f"Synthetic Improve completion for {stage}.",
            "review_refs": [f"synthetic://review/{stage}"],
            "check_refs": [f"synthetic://check/{stage}"],
            "lessons": f"Retain the verified learning from {stage}."}


class ProgressDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-progress-data-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.run_root = self.base / "run"
        self.run_root.mkdir()

    def state(self, *, prompt: str = "Add a parser.") -> dict:
        return navigator.new_state(str(self.repo), prompt)

    def save_state(self, state: dict) -> bytes:
        text = store.dumps(state, "ShipLoop navigator state")
        (self.run_root / "state.md").write_text(text, encoding="utf-8")
        return text.encode("utf-8")

    def accept(self, state: dict, **fields) -> dict:
        action = navigator.current_action(state)["id"]
        stage = navigator.current_stage(state)
        result = {"outcome": "done", "summary": f"Accepted {stage} fixture.", **fields}
        state = navigator.apply(state, action, result)
        if state.get("active_improve"):
            state = navigator.finish_improve(state, action, _improve_receipt(stage))
        return state

    def plan_state(self, *, evidence_refs: list[str] | None = None) -> dict:
        state = self.state()
        while navigator.current_stage(state) != "plan":
            state = self.accept(state)
        return self.accept(state, summary="Accepted plan fixture.",
                           evidence_refs=evidence_refs or [],
                           work_items=[{"id": "W1", "title": "Parser implementation",
                                        "context": "Read fixtures, then implement parsing."},
                                       {"id": "W2", "title": "Parser tests"}])

    def write_result_record(self, state: dict, stage: str) -> None:
        entry = next(row for row in state["history"] if row["stage"] == stage)
        action = entry["action"]
        record = {"navigator_protocol_version": state["navigator_protocol_version"],
                  "run_id": state["run_id"], "action": action, "stage": stage,
                  "workitem": entry["workitem"], "result": state["accepted"][action]}
        path = self.run_root / "results" / f"{action}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(store.dumps(record, "ShipLoop navigator result"), encoding="utf-8")

    def document(self, snapshot: dict, doc_id: str) -> dict:
        return next(row for row in snapshot["documents"] if row["id"] == doc_id)

    def test_schema_missing_documents_and_placeholder_plan_are_explicit(self) -> None:
        state = self.state()
        self.save_state(state)
        snapshot = progress_data.build_snapshot(self.run_root)

        self.assertEqual(snapshot["schema"], "shiploop-progress/v1")
        self.assertFalse(snapshot["plan_accepted"])
        self.assertEqual(snapshot["work_items"][0]["id"], "W1")
        self.assertEqual(snapshot["work_items"][0]["plan"], "")
        self.assertEqual(self.document(snapshot, "living-spec")["status"], "missing")
        self.assertEqual(self.document(snapshot, "feature-plan")["status"], "missing")
        self.assertEqual(self.document(snapshot, "current-action-notes")["status"], "missing")
        self.assertIn("source_fingerprint", snapshot)
        self.assertTrue(snapshot["observed_at"].endswith("Z"))

    def test_current_plan_and_accepted_results_stay_separate_from_living_drafts(self) -> None:
        outside = self.base / "outside-plan.md"
        outside.write_text("External material must not be read.", encoding="utf-8")
        state = self.plan_state(evidence_refs=[str(outside)])
        feature = self.repo / knowledge_home.feature_dir(state)
        feature.mkdir(parents=True)
        live_spec = feature / "spec.md"
        live_spec.write_text("# Draft spec\n", encoding="utf-8")
        (feature / "plan.md").write_text("# Draft plan\n", encoding="utf-8")
        self.write_result_record(state, "spec")
        self.write_result_record(state, "plan")
        self.save_state(state)

        first = progress_data.build_snapshot(self.run_root)
        self.assertTrue(first["plan_accepted"])
        self.assertEqual([row["id"] for row in first["work_items"]], ["W1", "W2"])
        self.assertEqual(self.document(first, "feature-spec")["status"], "draft")
        self.assertEqual(self.document(first, "accepted-spec-result")["status"], "accepted-result")
        self.assertEqual(self.document(first, "accepted-plan-result")["status"], "accepted-result")
        self.assertTrue(any("outside the repository/run root" in warning for warning in first["warnings"]))
        self.assertFalse(any(str(outside) in repr(row) for row in first["documents"]))

        old_sha = self.document(first, "feature-spec")["sha256"]
        live_spec.write_text("# Draft spec\n## Added detail\n", encoding="utf-8")
        second = progress_data.build_snapshot(self.run_root)
        self.assertNotEqual(self.document(second, "feature-spec")["sha256"], old_sha)
        self.assertNotEqual(second["source_fingerprint"], first["source_fingerprint"])

    def test_optional_document_symlink_hardlink_and_fifo_are_withheld(self) -> None:
        directory = self.repo / "docs" / "shiploop"
        directory.mkdir(parents=True)
        outside = self.base / "secret-spec.md"
        outside.write_text("Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345", encoding="utf-8")
        spec = directory / "spec.md"
        spec.symlink_to(outside)
        self.save_state(self.state())
        linked = progress_data.build_snapshot(self.run_root)
        self.assertEqual(self.document(linked, "living-spec")["status"], "withheld")
        self.assertNotIn("Authorization: Bearer", repr(linked))

        spec.unlink()
        os.link(outside, spec)
        linked = progress_data.build_snapshot(self.run_root)
        self.assertEqual(self.document(linked, "living-spec")["status"], "withheld")
        spec.unlink()

        if hasattr(os, "mkfifo"):
            os.mkfifo(spec)
            fifo = progress_data.build_snapshot(self.run_root)
            self.assertEqual(self.document(fifo, "living-spec")["status"], "withheld")

    def test_credential_content_and_unstable_optional_document_are_withheld(self) -> None:
        directory = self.repo / "docs" / "shiploop"
        directory.mkdir(parents=True)
        spec = directory / "spec.md"
        secret = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345"
        spec.write_text(secret, encoding="utf-8")
        self.save_state(self.state())
        screened = progress_data.build_snapshot(self.run_root)
        self.assertEqual(self.document(screened, "living-spec")["status"], "withheld")
        self.assertNotIn(secret, repr(screened))

        spec.write_text("A harmless initial draft.", encoding="utf-8")
        target = spec.stat()
        original_read = os.read
        changed = False

        def mutate_after_read(fd: int, size: int) -> bytes:
            nonlocal changed
            data = original_read(fd, size)
            current = os.fstat(fd)
            if not changed and current.st_ino == target.st_ino and data:
                changed = True
                with spec.open("a", encoding="utf-8") as handle:
                    handle.write(" changed during snapshot")
            return data

        with mock.patch.object(progress_data.os, "read", side_effect=mutate_after_read):
            unstable = progress_data.build_snapshot(self.run_root)
        self.assertTrue(changed)
        self.assertEqual(self.document(unstable, "living-spec")["status"], "withheld")
        self.assertIn("changed while reading", self.document(unstable, "living-spec")["error"])

    def test_chain_activity_changes_snapshot_without_changing_parent_state(self) -> None:
        state = self.plan_state()
        while navigator.current_stage(state) != "implement":
            state = self.accept(state)
        action_id = navigator.current_action(state)["id"]
        state["chain_bindings"] = {action_id: "a" * 64}
        navigator.validate(state)
        state_bytes = self.save_state(state)
        before = progress_data.build_snapshot(self.run_root)

        events = self.run_root / "chains" / action_id / "events"
        chain_ledger.append_event(events, "fixture-one", "contribution_recorded",
                                  {"summary": "Implementation reported by the child."})
        after = progress_data.build_snapshot(self.run_root)

        self.assertEqual((self.run_root / "state.md").read_bytes(), state_bytes)
        self.assertEqual(after["run"]["revision"], before["run"]["revision"])
        self.assertNotEqual(after["source_fingerprint"], before["source_fingerprint"])
        self.assertTrue(any(row["stream"] == "chain:" + action_id and row["seq"] == 1
                            for row in after["activity"]))

    def test_inline_step_plan_exposes_declared_branching_dependencies(self) -> None:
        state = self.plan_state()
        while navigator.current_stage(state) != "step-plan":
            state = self.accept(state)
        state = self.accept(state, steps=[
            {"id": "A", "task": "Build the reader", "deps": []},
            {"id": "B", "task": "Build the renderer", "deps": []},
            {"id": "C", "task": "Connect both pieces", "deps": ["A", "B"]},
        ])
        self.save_state(state)
        snapshot = progress_data.build_snapshot(self.run_root)
        graph = snapshot["graphs"][0]
        self.assertTrue(graph["dependencies_known"])
        self.assertEqual({(edge["from"], edge["to"]) for edge in graph["edges"]},
                         {("A", "C"), ("B", "C")})
        self.assertEqual([node["id"] for node in graph["nodes"]], ["A", "B", "C"])

    def test_generated_step_plan_replacement_updates_nodes_without_inventing_dependencies(self) -> None:
        state = self.plan_state()
        while navigator.current_stage(state) != "step-plan":
            state = self.accept(state)
        state = self.accept(state, steps=[{"id": "S1", "task": "Parse input"},
                                         {"id": "S2", "task": "Validate output"}])
        self.save_state(state)
        first = progress_data.build_snapshot(self.run_root)
        self.assertEqual([row["id"] for row in first["graphs"][0]["nodes"]], ["S1", "S2"])
        self.assertFalse(first["graphs"][0]["dependencies_known"])
        self.assertEqual(first["graphs"][0]["edges"], [])

        revise_action = navigator.current_action(state)["id"]
        revise_stage = navigator.current_stage(state)
        state = navigator.apply(state, revise_action,
                                {"outcome": "revise", "summary": "Replace the parser plan."})
        if state.get("active_improve"):
            state = navigator.finish_improve(state, revise_action, _improve_receipt(revise_stage))
        state = self.accept(state, steps=[{"id": "S3", "task": "Use the revised parser"}])
        self.save_state(state)
        after = progress_data.build_snapshot(self.run_root)
        self.assertEqual([row["id"] for row in after["graphs"][0]["nodes"]], ["S3"])
        self.assertNotEqual(first["source_fingerprint"], after["source_fingerprint"])

    def test_unreadable_authoritative_state_and_malformed_state_fail_closed(self) -> None:
        state_path = self.run_root / "state.md"
        external = self.base / "state-external.md"
        external.write_text(store.dumps(self.state(), "ShipLoop navigator state"), encoding="utf-8")
        state_path.symlink_to(external)
        with self.assertRaises(ValueError):
            progress_data.build_snapshot(self.run_root)

        state_path.unlink()
        state_path.write_bytes(external.read_bytes())
        hard_link = self.run_root / "state-copy.md"
        os.link(state_path, hard_link)
        with self.assertRaises(ValueError):
            progress_data.build_snapshot(self.run_root)
        hard_link.unlink()

        state_path.unlink()
        if hasattr(os, "mkfifo"):
            os.mkfifo(state_path)
            with self.assertRaises(ValueError):
                progress_data.build_snapshot(self.run_root)
            state_path.unlink()

        state_path.write_text("# malformed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "malformed"):
            progress_data.build_snapshot(self.run_root)


if __name__ == "__main__":
    unittest.main()
