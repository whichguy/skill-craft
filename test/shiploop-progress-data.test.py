#!/usr/bin/env python3
"""Focused fixtures for the read-only ShipLoop progress snapshot projection."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

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
        self.assertEqual(self.document(snapshot, "current-action-notes")["status"], "missing")
        self.assertIn("source_fingerprint", snapshot)
        self.assertTrue(snapshot["observed_at"].endswith("Z"))

    def test_current_plan_and_accepted_results_stay_separate_from_living_drafts(self) -> None:
        outside = self.base / "outside-plan.md"
        outside.write_text("External material must not be read.", encoding="utf-8")
        state = self.plan_state(evidence_refs=[str(outside)])
        live_spec = self.repo / knowledge_home.HOME / "spec.md"
        live_spec.parent.mkdir(parents=True)
        live_spec.write_text("# Draft spec\n", encoding="utf-8")
        self.write_result_record(state, "spec")
        self.write_result_record(state, "plan")
        self.save_state(state)

        first = progress_data.build_snapshot(self.run_root)
        self.assertTrue(first["plan_accepted"])
        self.assertEqual([row["id"] for row in first["work_items"]], ["W1", "W2"])
        self.assertEqual(self.document(first, "living-spec")["status"], "draft")
        self.assertEqual(self.document(first, "accepted-spec-result")["status"], "accepted-result")
        self.assertEqual(self.document(first, "accepted-plan-result")["status"], "accepted-result")
        self.assertTrue(any("outside the repository/run root" in warning for warning in first["warnings"]))
        self.assertFalse(any(str(outside) in repr(row) for row in first["documents"]))

        old_sha = self.document(first, "living-spec")["sha256"]
        live_spec.write_text("# Draft spec\n## Added detail\n", encoding="utf-8")
        second = progress_data.build_snapshot(self.run_root)
        self.assertNotEqual(self.document(second, "living-spec")["sha256"], old_sha)
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

    def test_a_result_with_credential_looking_text_is_recorded_as_written_and_the_view_still_redacts_it(self) -> None:
        """Owner decision 2026-10-16: ShipLoop refuses no credential pattern, so the run keeps the result's text as
        written; the progress projection is display only and withholds that text from the page."""
        secret = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345"
        summary = "The service answered with " + secret
        state = self.accept(self.state(), summary=summary)
        action = state["history"][-1]["action"]
        self.assertEqual(state["accepted"][action]["summary"], summary)  # the record is not rewritten
        self.save_state(state)
        snapshot = progress_data.build_snapshot(self.run_root)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz012345", repr(snapshot))
        self.assertIn("Credential-like", repr(snapshot))

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

        send_back_action = navigator.current_action(state)["id"]
        state = navigator.apply(state, send_back_action,
                                {"outcome": "send-back", "summary": "Replace the parser plan."})
        self.assertIsNone(state.get("active_improve"))  # Improve starts only on a done result.
        state = self.accept(state, steps=[{"id": "S3", "task": "Use the revised parser"}])
        self.save_state(state)
        after = progress_data.build_snapshot(self.run_root)
        self.assertEqual([row["id"] for row in after["graphs"][0]["nodes"]], ["S3"])
        self.assertNotEqual(first["source_fingerprint"], after["source_fingerprint"])

    def test_history_visit_retains_send_back_and_blocked_callback_outcomes(self) -> None:
        state = self.plan_state()
        while navigator.current_stage(state) != "step-plan":
            state = self.accept(state)
        state = self.accept(state, steps=[{"id": "S1", "task": "Parse input"}])
        send_back = navigator.current_action(state)["id"]
        state = navigator.apply(state, send_back,
                                {"outcome": "send-back", "summary": "Replace the parser plan."})
        blocked = navigator.current_action(state)["id"]
        state = navigator.apply(state, blocked, {
            "outcome": "blocked", "summary": "Await the synthetic planning dependency.",
            "awaiting": {"kind": "service", "service": "Synthetic planning dependency",
                         "check": "Read the recorded dependency status.",
                         "no_default": "The required planning input has no recorded substitute."},
        })
        self.save_state(state)
        story = progress_data.build_snapshot(self.run_root)["story"]
        visits = {row["id"]: row for row in story["visits"]}
        for action, outcome in ((send_back, "send-back"), (blocked, "blocked")):
            visit = visits["visit:" + action]
            self.assertEqual(visit["status"], outcome)
            self.assertTrue(visit["callback_accepted"])
            accepted = [row for row in story["events"] if row["id"] == "accepted:" + action]
            self.assertEqual(len(accepted), 1)
            self.assertEqual(accepted[0]["status"], outcome)
        self.assertEqual(len([row for row in story["events"] if row["kind"] == "accepted"]), len(state["history"]))
        self.assertEqual(story["lifecycle"]["engine"]["status"], "blocked")
        self.assertEqual(story["lifecycle"]["acceptance"]["status"], "unknown")

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

    # --- consumer contract 6.2: the run's records are result fields, shown by the report ---------------------------------
    def test_the_progress_view_lists_no_feature_or_test_strategy_document(self) -> None:
        state = self.plan_state()
        feature = self.repo / knowledge_home.HOME / "features" / "old-run-aaaaaa"
        feature.mkdir(parents=True)
        for name in ("spec.md", "plan.md", "test-spec.md"):
            (feature / name).write_text("# an earlier version's record\n", encoding="utf-8")
        (self.repo / knowledge_home.HOME / "test-strategy.md").write_text("# test strategy\n", encoding="utf-8")
        self.save_state(state)
        snapshot = progress_data.build_snapshot(self.run_root)
        ids = [row["id"] for row in snapshot["documents"]]
        for removed in ("feature-spec", "feature-plan", "feature-test-spec", "test-strategy"):
            self.assertNotIn(removed, ids)
        self.assertIn("living-spec", ids)
        self.assertFalse([row for row in snapshot["documents"] if row.get("status") == "retired"])
        self.assertFalse([warning for warning in snapshot["warnings"] if "feature" in warning or "test-strategy" in warning])


class StoryObservationTests(unittest.TestCase):
    """Coherent synthetic generations; never reads a real run or launches a process."""

    def setUp(self):
        import shiploop_story as story
        import shiploop_observation_io as observation_io
        self.story, self.io = story, observation_io
        self.temp = tempfile.TemporaryDirectory(prefix="story-observation-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.state = navigator.new_state(str(self.repo), "Read synthetic evidence", improve_skill="")
        self.action = navigator.current_action(self.state)["id"]
        self.timeline = {"started": "2026-01-01T00:00:00Z", "accepted": {}}

    def append(self, name, row):
        store.append_jsonl(self.root / name, row)

    def build(self, **kwargs):
        return self.story.build(self.root, self.state, self.timeline, **kwargs)

    def observation(self, **fields):
        return {"schema": "shiploop-progress-observation/v1", "id": "exit", "run_id": self.state["run_id"],
                "producer": "fixture-harness", "scope": "fixture execution", "kind": "fact", "title": "Stopped",
                "summary": "Harness recorded process exit.", "status": "stopped",
                "observed_at": "2026-01-01T00:00:02Z", "logged_at": "2026-01-01T00:00:03Z", **fields}

    def test_trace_only_update_and_identical_packets_remain_distinct(self):
        before, _ = self.build()
        row = {"kind": "packet", "action": self.action, "sha": "same", "at": "2026-01-01T00:00:01Z"}
        self.append("trace.jsonl", row)
        first, _ = self.build()
        self.append("trace.jsonl", row)
        after, _ = self.build()
        self.assertNotEqual(before["activity_fingerprint"], first["activity_fingerprint"])
        self.assertEqual(first["events"][0]["id"], after["events"][0]["id"])
        self.assertNotEqual(after["events"][0]["id"], after["events"][1]["id"])

    def test_state_before_command_reconciles_one_stable_acceptance(self):
        self.state = navigator.apply(self.state, self.action, {"outcome": "done", "summary": "Accepted scope."})
        before, _ = self.build()
        self.append("trace.jsonl", {"kind": "command", "verb": "complete", "exit": 0, "action": self.action,
                                    "accepted": [{"action": self.action}], "ms": 17})
        after, _ = self.build()
        accepted = lambda value: [event["id"] for event in value["events"] if event["kind"] == "accepted"]
        self.assertEqual(accepted(before), ["accepted:" + self.action])
        self.assertEqual(accepted(before), accepted(after))
        self.assertEqual([e["duration_ms"] for e in after["events"] if e["kind"] == "command"], [17])

    def test_literal_unicode_partial_tail_and_interior_damage_are_distinct(self):
        import json
        raw = (json.dumps({"kind": "hook", "text": "a\u2028b"}, ensure_ascii=False) + "\n{damaged}\n" +
               json.dumps({"kind": "hook", "text": "next"}) + "\n{unfinished").encode()
        (self.root / "trace.jsonl").write_bytes(raw)
        story, _ = self.build()
        source = next(row for row in story["sources"] if row["path"] == "trace.jsonl")
        self.assertEqual(source["status"], "partial")
        self.assertEqual(source["rows"], 2)
        self.assertIn("Interior damaged records: 1", source["message"])
        self.assertIn("unfinished tail: True", source["message"])
        self.assertEqual([e["source"]["line"] for e in story["events"] if e["source"]["path"] == "trace.jsonl"], [1, 3])
        self.assertIn("a\u2028b", story["events"][0]["summary"])
        self.assertEqual(len(store.read_jsonl(self.root / "trace.jsonl")), 2)

    def test_valid_unterminated_json_retains_reader_contract_and_labels_coverage(self):
        raw = b'{"kind":"hook","text":"complete object without newline"}'
        (self.root / "trace.jsonl").write_bytes(raw)
        self.assertEqual(len(store.read_jsonl(self.root / "trace.jsonl")), 1)
        story, _ = self.build()
        source = next(row for row in story["sources"] if row["path"] == "trace.jsonl")
        self.assertEqual(source["status"], "partial")
        self.assertIn("final newline absent: True", source["message"])

    def test_active_until_retry_and_reused_records_are_visible(self):
        import json
        (self.root / "loops").mkdir()
        (self.root / "loops" / (self.action + "-terminal.json")).write_text(json.dumps({"status": "active", "step": 2}))
        (self.root / "tests").mkdir()
        (self.root / "tests" / (self.action + "-verify1.md")).write_text(store.dumps({"passed": True, "reused": "check.md"}))
        for code in (1, 1, 0):
            self.append("trace.jsonl", {"kind": "command", "action": self.action, "verb": "check", "exit": code})
        story, _ = self.build()
        attempts = [e for e in story["events"] if e["kind"] == "command"]
        self.assertEqual(len({e["id"] for e in attempts}), 3)
        self.assertEqual(next(e for e in story["events"] if e["kind"] == "until")["status"], "active")
        self.assertIn("not a new execution", next(e for e in story["events"] if e["kind"] == "test")["summary"])
        self.assertTrue(all(e["sha256"] and e["line"] == 1 for e in story["evidence"] if e["status"] == "ok"))
        receipt = self.root / "loops" / (self.action + "-terminal.json")
        receipt.write_text(json.dumps({"status": "stopped", "progress": {"reason": "producer stop"}}))
        stopped, _ = self.build()
        until = lambda value: next(e for e in value["events"] if e["kind"] == "until")
        self.assertEqual(until(stopped)["status"], "stopped")
        self.assertEqual(until(story)["id"], until(stopped)["id"])
        self.assertNotEqual(story["activity_fingerprint"], stopped["activity_fingerprint"])

    def test_paths_links_and_all_serialized_fields_are_screened(self):
        import json
        secret = "api_key=abcdefghijk1234567890"
        external = self.repo / "private.txt"
        external.write_text("EXTERNAL SHOULD NOT APPEAR")
        (self.root / "linked").symlink_to(self.repo, target_is_directory=True)
        self.append("trace.jsonl", {"kind": "packet", "action": self.action, "file": "../private.txt", "error": secret})
        self.append("trace.jsonl", {"kind": "packet", "action": self.action, "file": "linked/private.txt"})
        self.append("progress-observations.jsonl", self.observation(title=secret, **{secret: secret}))
        story, _ = self.build()
        payload = json.dumps(story)
        self.assertNotIn(secret, payload)
        self.assertNotIn("EXTERNAL SHOULD NOT APPEAR", payload)
        self.assertTrue(story["warnings"])
        self.assertTrue(any(row["status"] == "unsafe" for row in story["sources"]))

    def test_missing_foreign_and_bound_observations_keep_lifecycle_independent(self):
        story, _ = self.build()
        self.assertEqual(story["lifecycle"]["execution"]["status"], "unknown")
        self.append("progress-observations.jsonl", self.observation(run_id="foreign-run"))
        story, _ = self.build()
        self.assertEqual(story["observations"], [])
        self.append("progress-observations.jsonl", self.observation(lifecycle={"execution": {"status": "stopped"},
                                                                              "owner_hold": {"status": "held"}}))
        story, _ = self.build()
        self.assertEqual(story["lifecycle"]["execution"]["status"], "stopped")
        self.assertEqual(story["lifecycle"]["engine"]["status"], self.state["status"])
        self.assertEqual(story["lifecycle"]["acceptance"]["status"], "unknown")
        self.assertIsNone(story["lifecycle"]["execution"]["at"])

    def test_observation_heartbeats_do_not_change_content_or_activity(self):
        self.append("progress-observations.jsonl", self.observation())
        before, _ = self.build(observed_at="first")
        self.append("progress-observations.jsonl", self.observation(observed_at="later", logged_at="later"))
        after, _ = self.build(observed_at="second")
        self.assertEqual(before["content_fingerprint"], after["content_fingerprint"])
        self.assertEqual(before["activity_fingerprint"], after["activity_fingerprint"])
        self.assertEqual(len(after["observations"]), 1)

    def test_transient_failure_retains_optional_capture_not_core_state(self):
        self.append("trace.jsonl", {"kind": "hook", "text": "retained"})
        before, cache = self.build(observed_at="original")
        original = self.io._read_beneath
        def read(root, relative, *args, **kwargs):
            if relative == "trace.jsonl":
                raise OSError("synthetic transient failure")
            return original(root, relative, *args, **kwargs)
        self.state = navigator.apply(self.state, self.action, {"outcome": "done", "summary": "Fresh accepted core."})
        with mock.patch.object(self.io, "_read_beneath", side_effect=read):
            after, _ = self.build(previous=cache, observed_at="new core")
        source = next(row for row in after["sources"] if row["path"] == "trace.jsonl")
        self.assertEqual((source["status"], source["observed_at"]), ("stale", "original"))
        self.assertTrue(any(e["id"] == "accepted:" + self.action for e in after["events"]))
        self.assertEqual(before["events"][0]["id"], after["events"][0]["id"])

    def test_latest_recorded_timestamp_beats_stream_concatenation_and_earlier_state(self):
        self.state = navigator.apply(self.state, self.action, {"outcome": "done", "summary": "Earlier acceptance"})
        self.timeline["accepted"][self.action] = "2026-01-01T16:00:00Z"
        self.append("trace.jsonl", {"kind": "hook", "at": "2026-01-01T23:09:11Z", "text": "Latest hook"})
        self.append("skill-calls.jsonl", {"gate": "coverage", "at": "2026-01-01T16:21:26Z", "why": "Older skill note"})
        self.append("progress-observations.jsonl", self.observation(event_at="2026-01-01T15:00:00Z", logged_at="2026-01-02T00:00:00Z"))
        story, _ = self.build()
        self.assertEqual(story["summary"]["changed"], "Latest hook")
        self.assertEqual(story["last_event_at"], "2026-01-01T23:09:11Z")
        self.assertEqual(story["last_knowledge_at"], "2026-01-02T00:00:00Z")
        rows = [e for e in story["events"] if e["kind"] in ("hook", "skill")]
        self.assertEqual([e["kind"] for e in rows], ["hook", "skill"])
        self.assertIn(":1:", rows[0]["id"])

    def test_untimed_sources_do_not_fabricate_a_latest_activity_time(self):
        self.append("trace.jsonl", {"kind": "hook", "text": "Untimed assertion"})
        story, _ = self.build()
        self.assertIsNone(story["last_event_at"])
        self.assertIn("No reliably timestamped event", story["summary"]["changed"])
        self.assertIsNone(story["events"][0]["at"])

    def test_small_preview_bound_preserves_current_gate_and_recent_prior_receipt(self):
        import json
        for _ in range(3):
            action = navigator.current_action(self.state)["id"]
            self.state = navigator.apply(self.state, action, {"outcome": "done", "summary": "Prior accepted visit"})
        current = navigator.current_action(self.state)["id"]
        prior = self.state["history"][-1]["action"]
        oldest = self.state["history"][0]["action"]
        (self.root / "loops").mkdir()
        for entry in self.state["history"]:
            action = entry["action"]
            (self.root / "loops" / (action + "-terminal.json")).write_text(json.dumps({"run_id": self.state["run_id"], "action": action, "status": "stopped"}))
        (self.root / "checks").mkdir()
        (self.root / "checks" / (current + ".md")).write_text(store.dumps({"run_id": self.state["run_id"], "action": current, "answer": "yes"}))
        (self.root / "packets").mkdir()
        (self.root / "packets" / "repeat.md").write_text("Repeated packet")
        for _ in range(10):
            self.append("trace.jsonl", {"kind": "packet", "action": current, "file": "packets/repeat.md"})
        with mock.patch.object(self.story, "EVIDENCE_FILES", 2):
            story, _ = self.build()
        by_path = {e["relative_path"]: e for e in story["evidence"]}
        self.assertIsNotNone(by_path["checks/" + current + ".md"]["sha256"])
        self.assertIsNotNone(by_path["loops/" + prior + "-terminal.json"]["sha256"])
        self.assertEqual(by_path["loops/" + oldest + "-terminal.json"]["status"], "unavailable")
        self.assertEqual(len([e for e in story["evidence"] if e["relative_path"] == "packets/repeat.md"]), 1)
        self.assertEqual(story["coverage"]["previews_read"], 2)
        self.assertGreater(story["coverage"]["previews_not_read"], 0)
        self.assertTrue(any("File existence/content" in warning for warning in story["warnings"]))
        self.assertEqual([v["action"] for v in story["visits"]], [entry["action"] for entry in self.state["history"]] + [current])

    def test_evidence_previews_have_screened_absolute_disk_locators(self):
        (self.root / "packets").mkdir()
        (self.root / "packets" / "sent.md").write_text("Prompt as sent")
        self.append("trace.jsonl", {"kind": "packet", "action": self.action, "file": "packets/sent.md"})
        story, _ = self.build()
        entry = next(e for e in story["evidence"] if e["relative_path"] == "packets/sent.md")
        self.assertEqual(entry["path"], str(self.root / "packets/sent.md"))
        self.assertTrue(Path(entry["path"]).is_absolute())

    def test_structured_identity_mismatch_is_visible_without_owning_visit_status(self):
        import json
        (self.root / "loops").mkdir()
        receipt = {"run_id": self.state["run_id"], "action": self.action, "status": "complete",
                   "receipt": str(self.root / "loops" / (self.action + "-terminal.json")),
                   "context": {"resources": [{"locator": str(self.root / "packets/foreign-action.md")}]}}
        (self.root / "loops" / (self.action + "-terminal.json")).write_text(json.dumps(receipt))
        (self.root / "checks").mkdir()
        (self.root / "checks" / (self.action + ".md")).write_text(store.dumps({"run_id": "foreign-run", "action": self.action, "answer": "yes"}))
        story, _ = self.build()
        mismatches = [e for e in story["events"] if e["kind"] in ("until", "check")]
        self.assertTrue(all(e["status"] == "mismatched" and e["binding"] == "unbound" for e in mismatches))
        self.assertEqual(story["visits"][-1]["status"], self.state["status"])
        self.assertTrue(any("Until context action" in w for w in story["warnings"]))
        self.assertTrue(any("run_id" in w for w in story["warnings"]))
        previews = [e for e in story["evidence"] if e["status"] == "mismatched"]
        self.assertEqual(len(previews), 2)
        self.assertTrue(any('"status": "complete"' in e["content"] for e in previews))

    def test_skill_stream_cannot_inherit_a_later_trace_packet(self):
        self.append("trace.jsonl", {"kind": "packet", "action": "A", "at": "2026-01-01T00:00:01Z"})
        self.append("trace.jsonl", {"kind": "packet", "action": "B", "at": "2026-01-01T00:00:03Z"})
        self.append("skill-calls.jsonl", {"skill": "fixture", "at": "2026-01-01T00:00:02Z"})
        projected, _ = self.build()
        rows = [row for row in projected["events"] if row["kind"] in ("packet", "skill")]
        self.assertEqual([row["kind"] for row in rows], ["packet", "packet", "skill"])
        self.assertIsNone(rows[-1]["action"])
        self.assertEqual(rows[-1]["binding"], "unbound")
        self.assertIn(":1:", rows[-1]["id"])

    def test_optional_timestamp_types_are_unknown_with_coverage_and_fresh_core(self):
        import json
        self.state = navigator.apply(self.state, self.action, {"outcome": "done", "summary": "Fresh accepted state"})
        (self.root / "state.md").write_text(store.dumps(self.state))
        for started, ended in ((1, {"bad": "stamp"}), ([1], 17), ("not a date", "2026-01-01T00:00:00")):
            with self.subTest(started=started, ended=ended):
                (self.root / "timeline.json").write_text(json.dumps({"started": started, "accepted": {self.action: ended}}))
                core = self.story.capture_core(self.root)
                snapshot = progress_data.build_snapshot(self.root, core=core)
                visit = next(v for v in snapshot["story"]["visits"] if v["action"] == self.action)
                self.assertIsNone(visit["started_at"])
                self.assertIsNone(visit["ended_at"])
                self.assertIsNone(visit["duration_seconds"])
                self.assertEqual(snapshot["run"]["revision"], self.state["revision"])
                source = next(row for row in snapshot["story"]["sources"] if row["id"] == "timeline.json")
                self.assertEqual(source["status"], "partial")

    def test_deep_optional_json_and_fenced_records_do_not_hide_fresh_state(self):
        import sys
        deep = '{"nested":' + '[' * (sys.getrecursionlimit() + 50) + '0' + ']' * (sys.getrecursionlimit() + 50) + '}'
        (self.root / "state.md").write_text(store.dumps(self.state))
        (self.root / "timeline.json").write_text(deep)
        (self.root / "trace.jsonl").write_text(deep + '\n{"kind":"hook","text":"valid remaining row"}\n')
        (self.root / "loops").mkdir()
        (self.root / "loops" / (self.action + "-terminal.json")).write_text(deep)
        (self.root / "checks").mkdir()
        (self.root / "checks" / (self.action + ".md")).write_text('# Check\n```shiploop-state\n' + deep + '\n```\n')
        snapshot = progress_data.build_snapshot(self.root, core=self.story.capture_core(self.root))
        self.assertEqual(snapshot["run"]["revision"], self.state["revision"])
        sources = {row["id"]: row for row in snapshot["story"]["sources"]}
        for name in ("timeline.json", "trace.jsonl", "loops/" + self.action + "-terminal.json", "checks/" + self.action + ".md"):
            self.assertEqual(sources[name]["status"], "partial")
        self.assertTrue(any(row["summary"] == "valid remaining row" for row in snapshot["story"]["events"]))
        (self.root / "state.md").write_text('```shiploop-state\n' + deep + '\n```\n')
        # A decoder may accept this depth; the resulting object still fails
        # navigator validation explicitly. Do not prescribe which layer rejects it.
        with self.assertRaises(ValueError):
            progress_data.build_snapshot(self.root)
        # Exact malformed-state wording belongs to deterministic syntax damage.
        (self.root / "state.md").write_text('```shiploop-state\n{"broken":\n```\n')
        with self.assertRaisesRegex(ValueError, "authoritative state.md is malformed"):
            progress_data.build_snapshot(self.root)

    def test_activity_ignores_jsonl_layout_and_source_generation_but_tracks_records(self):
        import json
        row = {"kind": "hook", "at": "2026-01-01T00:00:01Z", "text": "First recorded activity"}
        self.append("trace.jsonl", row)
        first, _ = self.build()
        with (self.root / "trace.jsonl").open("a") as handle:
            handle.write('\n   \n')
        whitespace, _ = self.build()
        self.assertEqual(first["activity_fingerprint"], whitespace["activity_fingerprint"])
        self.assertNotEqual(first["content_fingerprint"], whitespace["content_fingerprint"])
        replacement = self.root / "replacement.jsonl"
        replacement.write_text(json.dumps(row, separators=(', ', ' : ')) + '\n')
        os.replace(replacement, self.root / "trace.jsonl")
        replaced, _ = self.build()
        self.assertEqual(first["activity_fingerprint"], replaced["activity_fingerprint"])
        self.append("trace.jsonl", dict(row, text="Actual changed recorded activity"))
        changed, _ = self.build()
        self.assertNotEqual(first["activity_fingerprint"], changed["activity_fingerprint"])

    def test_snapshot_activity_ignores_state_markdown_formatting(self):
        path = self.root / "state.md"
        path.write_text(store.dumps(self.state, "Original state heading"))
        first = progress_data.build_snapshot(self.root)
        path.write_text(store.dumps(self.state, "Reformatted heading for same recorded state"))
        reformatted = progress_data.build_snapshot(self.root)
        self.assertEqual(first["activity_fingerprint"], reformatted["activity_fingerprint"])
        self.assertNotEqual(first["source_fingerprint"], reformatted["source_fingerprint"])

    def test_observation_a_heartbeat_after_a_b_preserves_activity_and_lifecycle(self):
        a = self.observation(id="A", lifecycle={"execution": {"status": "running"}})
        b = self.observation(id="B", lifecycle={"execution": {"status": "stopped"}})
        self.append("progress-observations.jsonl", a)
        self.append("progress-observations.jsonl", b)
        first, _ = self.build()
        self.append("progress-observations.jsonl", dict(a, observed_at="2026-01-03T00:00:00Z", logged_at="2026-01-03T00:00:01Z"))
        heartbeat, _ = self.build()
        self.assertEqual(first["activity_fingerprint"], heartbeat["activity_fingerprint"])
        self.assertEqual(heartbeat["lifecycle"]["execution"]["status"], "stopped")
        self.assertEqual([o["id"] for o in first["observations"]], [o["id"] for o in heartbeat["observations"]])
        self.append("progress-observations.jsonl", dict(a, lifecycle={"execution": {"status": "running", "at": "2026-01-04T00:00:00Z"}}))
        changed, _ = self.build()
        self.assertNotEqual(first["activity_fingerprint"], changed["activity_fingerprint"])

    def test_packet_previews_check_each_full_and_head_digest_reference(self):
        import hashlib
        packet = self.root / "packets/sent"
        packet.mkdir(parents=True)
        original, head = b"Issued full packet", b"Issued printed head"
        full_sha, head_sha = hashlib.sha256(original).hexdigest(), hashlib.sha256(head).hexdigest()
        full_path, head_path = "packets/sent/" + full_sha[:16] + ".md", "packets/sent/" + head_sha[:16] + ".md"
        (self.root / full_path).write_bytes(original)
        (self.root / head_path).write_bytes(head)
        self.append("trace.jsonl", {"kind": "packet", "action": self.action, "file": full_path, "sha": full_sha[:16], "head_file": head_path})
        self.append("trace.jsonl", {"kind": "packet", "action": self.action, "file": full_path, "sha": full_sha})
        matched, _ = self.build()
        by_path = {e["relative_path"]: e for e in matched["evidence"]}
        self.assertEqual(by_path[full_path]["references"][0]["status"], "digest-match")
        self.assertEqual(by_path[head_path]["references"][0]["status"], "digest-match")
        self.assertEqual(by_path[head_path]["references"][0]["expected_sha256"], head_sha[:16])
        self.append("trace.jsonl", {"kind": "packet", "action": self.action, "file": full_path, "sha": "0" * 64})
        conflicting, _ = self.build()
        entry = next(e for e in conflicting["evidence"] if e["relative_path"] == full_path)
        self.assertEqual(entry["status"], "mismatched")
        self.assertEqual({ref["status"] for ref in entry["references"]}, {"digest-match", "digest-mismatch"})
        (self.root / full_path).write_bytes(b"Replaced current packet")
        replaced, _ = self.build()
        entry = next(e for e in replaced["evidence"] if e["relative_path"] == full_path)
        self.assertEqual(entry["status"], "mismatched")
        self.assertEqual(entry["content"], "Replaced current packet")
        self.assertEqual(entry["sha256"], hashlib.sha256(b"Replaced current packet").hexdigest())

    def test_packet_without_recorded_digest_is_current_file_unverified(self):
        (self.root / "packet.md").write_text("Current file only")
        self.append("trace.jsonl", {"kind": "packet", "action": self.action, "file": "packet.md"})
        projected, _ = self.build()
        entry = next(e for e in projected["evidence"] if e["relative_path"] == "packet.md")
        self.assertEqual(entry["status"], "unverified")
        self.assertIn("no supported issued digest", entry["summary"])
        self.assertNotEqual(entry["title"], "Packet as issued")

    def test_active_improve_visit_retains_reviewed_parent_stage(self):
        state = navigator.new_state(str(self.repo), "Synthetic Improve visit")
        while navigator.current_stage(state) != "spec":
            state = navigator.apply(state, navigator.current_action(state)["id"],
                                    {"outcome": "done", "summary": "Accepted earlier planning input"})
        action = navigator.current_action(state)["id"]
        parent = navigator.current_stage(state)
        state = navigator.apply(state, action, {"outcome": "done", "summary": "Review the accepted scope"})
        self.assertTrue(state.get("active_improve"))
        projected, _ = self.story.build(self.root, state, self.timeline)
        visit = projected["visits"][-1]
        self.assertEqual(visit["stage"], "improve")
        self.assertEqual(visit["parent_stage"], parent)
        self.assertEqual(visit["action"], state["active_improve"]["improve_action"])
        self.assertEqual(projected["summary"]["now"], "improve")

    def test_replacement_and_cap_have_explicit_coverage(self):
        self.append("trace.jsonl", {"kind": "hook"})
        first = self.io.capture(self.root, "trace.jsonl", 100, "first")
        replacement = self.root / "replacement.jsonl"
        replacement.write_bytes((self.root / "trace.jsonl").read_bytes())
        os.replace(replacement, self.root / "trace.jsonl")
        second = self.io.capture(self.root, "trace.jsonl", 100, "second", first)
        self.assertNotEqual(first["generation"], second["generation"])
        self.assertIn("replaced", second["source"]["message"])
        capped = self.io.capture(self.root, "trace.jsonl", 1, "third")
        self.io.stream(capped)
        self.assertEqual(capped["source"]["status"], "partial")
        self.assertIsNone(capped["source"]["omitted"])


if __name__ == "__main__":
    unittest.main()
