#!/usr/bin/env python3
"""Focused fixtures for the read-only ShipLoop progress snapshot projection."""

from __future__ import annotations

import json
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
        # A structured record past the embedding budget is still read; only its preview is left out.
        left_out = by_path["loops/" + oldest + "-terminal.json"]
        self.assertEqual((left_out["status"], left_out["content"]), ("not embedded", ""))
        self.assertIsNotNone(left_out["sha256"])
        self.assertEqual(next(e["status"] for e in story["events"] if e["kind"] == "until" and e["action"] == oldest), "stopped")
        # Packet copies past the budget are not read at all.
        self.assertEqual(by_path["packets/repeat.md"]["status"], "not loaded")
        self.assertEqual(len([e for e in story["evidence"] if e["relative_path"] == "packets/repeat.md"]), 1)
        self.assertEqual(story["coverage"]["previews_read"], 2)
        self.assertGreater(story["coverage"]["previews_not_read"], 0)
        self.assertGreater(story["coverage"]["previews_not_embedded"], 0)
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
        # The stage under review has no history row yet: its events show in the one current visit, beside the
        # pass's own, and not outside every visit.
        self.assertEqual(visit["reviewed_action"], action)
        self.assertNotIn(action, {row["action"] for row in projected["visits"]})
        self.append("trace.jsonl", {"kind": "command", "verb": "check", "action": action, "exit": 0})
        projected, _ = self.story.build(self.root, state, self.timeline)
        event = next(e for e in projected["events"] if e["source"]["path"] == "trace.jsonl")
        self.assertIn(event["id"], projected["visits"][-1]["events"])
        self.assertNotIn("improve_of", event)

    def trace_events(self, story, path="trace.jsonl"):
        return [e for e in story["events"] if e["source"]["path"] == path]

    def test_trace_events_use_plain_status_words_and_keep_the_raw_exit(self):
        rows = [
            {"kind": "command", "verb": "complete", "exit": 0},
            {"kind": "command", "verb": "complete", "exit": 2, "error": "stage refused"},
            {"kind": "command", "verb": "check", "exit": 1},
            {"kind": "command", "verb": "next", "exit": 130, "crashed": "KeyboardInterrupt"},
            {"kind": "command", "verb": "next", "exit": 1, "crashed": "ValueError"},
            {"kind": "command", "verb": "next"},
            {"kind": "command", "verb": "next", "exit": True},
            {"kind": "packet", "stage": "spec"},
            {"kind": "packet", "stage": "spec", "repeat": True},
            {"kind": "hook", "hook": "stop", "decision": "allow", "why": "run is idle"},
            {"kind": "hook", "hook": "stop", "why": "no decision recorded"},
            {"kind": "hook", "hook": "stop", "decision": ""},
            {"kind": "mystery"},
            {"why": "no kind at all"},
        ]
        for row in rows:
            self.append("trace.jsonl", row)
        self.append("skill-calls.jsonl", {"gate": "not enforced", "why": "not a Claude Code session"})
        self.append("skill-calls.jsonl", {"skill": "fixture", "args": "x"})
        self.append("skill-calls.jsonl", {"skill": "fixture", "gate": ""})
        story, _ = self.build()
        got = [(e["kind"], e["status"], e["exit"]) for e in self.trace_events(story)]
        self.assertEqual(got, [
            ("command", "ok", 0), ("command", "refused (exit 2)", 2), ("command", "not passed (exit 1)", 1),
            ("command", "interrupted (exit 130)", 130),
            ("command", "crashed (exit 1)", 1), ("command", None, None), ("command", None, None),
            ("packet", "sent", None), ("packet", "sent again (same text)", None),
            ("hook", "allow", None), ("hook", None, None), ("hook", None, None),
            ("mystery", None, None), ("unknown", None, None)])
        skills = self.trace_events(story, "skill-calls.jsonl")
        self.assertEqual([e["status"] for e in skills], ["not enforced", "called", "called"])
        self.assertTrue(all(e["exit"] is None for e in skills))
        text = json.dumps(story)
        self.assertNotIn("unknown", [e["status"] for e in story["events"]])
        self.assertNotIn('"status": 0', text)

    def test_packet_events_describe_the_packet_instead_of_falling_back_to_their_kind(self):
        self.append("trace.jsonl", {"kind": "packet", "action": self.action, "item": "W2", "stage": "improve",
                                    "reviewed": "document", "chars": 1504, "printed": 1531, "whole": True,
                                    "at": "2026-01-01T00:00:01Z"})
        self.append("trace.jsonl", {"kind": "packet", "stage": "spec", "chars": 20000, "printed": 1531, "whole": False})
        self.append("trace.jsonl", {"kind": "packet", "stage": "plan", "whole": True})
        self.append("trace.jsonl", {"kind": "packet"})
        self.append("trace.jsonl", {"kind": "packet", "stage": "plan", "why": "an explicit reason wins"})
        self.append("trace.jsonl", {"kind": "command", "verb": "next", "exit": 0})
        self.append("trace.jsonl", {"kind": "hook", "text": "hook text"})
        story, _ = self.build()
        self.assertEqual([e["summary"] for e in self.trace_events(story)], [
            "W2 improve packet (reviewing document), 1,504 chars, printed whole",
            "spec packet, 20,000 chars, printed head 1,531 chars",
            "plan packet, printed whole", "packet", "an explicit reason wins", "next", "hook text"])
        self.assertEqual(story["summary"]["changed"], "W2 improve packet (reviewing document), 1,504 chars, printed whole")

    def test_a_stage_that_wrote_no_structured_file_has_no_missing_candidates(self):
        story, _ = self.build()
        self.assertFalse([e for e in story["events"] if e["kind"] in ("until", "check", "expectation", "test")])
        structured = ("loops/", "checks/", "expectations/", "tests/")
        self.assertFalse([e for e in story["evidence"] if e["relative_path"].startswith(structured)])
        # Other actions' files, and unrelated names, do not make this action's candidates exist.
        for directory in ("loops", "checks", "expectations"):
            (self.root / directory).mkdir()
            (self.root / directory / "nav-other-terminal.json").write_text("{}")
        (self.root / "checks" / (self.action + ".md.bak")).write_text("not a record")
        story, _ = self.build()
        self.assertFalse([e for e in story["events"] if e["kind"] in ("until", "check", "expectation", "test")])
        self.assertFalse([e for e in story["evidence"] if e["relative_path"].startswith(("loops/", "checks/", "expectations/"))])
        # Exactly the files this action wrote become candidates, each once.
        (self.root / "checks" / (self.action + ".md")).write_text(store.dumps({"run_id": self.state["run_id"], "action": self.action, "answer": "yes"}))
        story, _ = self.build()
        self.assertEqual([(e["kind"], e["status"]) for e in story["events"] if e["kind"] in ("until", "check", "expectation", "test")],
                         [("check", "yes")])

    def test_a_listed_file_that_vanishes_before_the_read_still_shows_missing(self):
        listing = lambda root, directory: [self.action + ".md"] if directory == "checks" else []
        with mock.patch.object(self.story, "_listing", side_effect=listing):
            story, _ = self.build()
        checks = [e for e in story["events"] if e["kind"] == "check"]
        self.assertEqual([e["status"] for e in checks], ["missing"])

    def test_every_structured_record_is_read_and_only_the_previews_are_budgeted(self):
        for _ in range(3):
            action = navigator.current_action(self.state)["id"]
            self.state = navigator.apply(self.state, action, {"outcome": "done", "summary": "Prior accepted visit"})
        current = navigator.current_action(self.state)["id"]
        history = [entry["action"] for entry in self.state["history"]]
        for directory in ("loops", "checks", "expectations", "tests", "packets"):
            (self.root / directory).mkdir()
        run_id = self.state["run_id"]
        for action in history:
            (self.root / "loops" / (action + "-terminal.json")).write_text(json.dumps({"run_id": run_id, "action": action, "status": "stopped"}))
            (self.root / "tests" / (action + "-verify1.md")).write_text(store.dumps({"status": "passed", "run_id": run_id, "action": action}))
            (self.root / "tests" / (action + "-verify2.md")).write_text(store.dumps({"status": "skipped", "run_id": run_id, "action": action}))
        (self.root / "expectations" / (history[0] + ".md")).write_text(store.dumps(
            {"schema": "shiploop-expectations/v1", "action": history[0],
             "results": [{"id": "E1", "matches": True}, {"id": "E2", "matches": False}, {"id": "E3", "matches": True}]}))
        (self.root / "checks" / (current + ".md")).write_text(store.dumps({"run_id": run_id, "action": current, "answer": "yes"}))
        (self.root / "checks" / (history[1] + ".md")).write_text(store.dumps({"run_id": run_id, "action": history[1]}))
        (self.root / "packets" / "repeat.md").write_text("Repeated packet")
        self.append("trace.jsonl", {"kind": "packet", "action": current, "file": "packets/repeat.md"})
        with mock.patch.object(self.story, "EVIDENCE_FILES", 2):
            story, _ = self.build()
        records = [e for e in story["events"] if e["kind"] in ("until", "check", "expectation", "test")]
        self.assertEqual(len(records), 3 + 6 + 1 + 2)
        self.assertEqual(sorted(e["status"] for e in records if e["kind"] == "test"), ["passed"] * 3 + ["skipped"] * 3)
        self.assertEqual([e["status"] for e in records if e["kind"] == "until"], ["stopped"] * 3)
        self.assertEqual([e["status"] for e in records if e["kind"] == "expectation"], ["2 of 3 matched"])
        self.assertEqual(sorted(e["status"] or "" for e in records if e["kind"] == "check"), ["", "yes"])
        structured = [e for e in story["evidence"] if e["relative_path"].startswith(("loops/", "checks/", "expectations/", "tests/"))]
        self.assertEqual(len(structured), len(records))
        embedded = [e for e in structured if e["status"] != "not embedded"]
        left_out = [e for e in structured if e["status"] == "not embedded"]
        self.assertEqual(len(embedded), 2)
        self.assertEqual(len(left_out), len(records) - 2)
        for entry in left_out:
            self.assertEqual(entry["content"], "")
            self.assertIsNotNone(entry["sha256"])
            self.assertIn("2-file display budget", entry["summary"])
            self.assertIn("record itself was read", entry["summary"])
        self.assertTrue(all(e["content"] for e in embedded))
        # Packet copies past the budget are not read; the warning and counts cover only those.
        not_loaded = [e for e in story["evidence"] if e["status"] == "not loaded"]
        self.assertEqual({e["relative_path"] for e in not_loaded}, {"packets/repeat.md", "packets/" + current + ".md"})
        self.assertEqual(story["coverage"], {"preview_candidates": len(structured) + 2, "previews_read": 2,
                                              "previews_not_read": 2, "previews_not_embedded": len(left_out),
                                              "scope": story["coverage"]["scope"]})
        self.assertTrue(any(w.startswith("2 registered source previews were not read") for w in story["warnings"]))
        partial = {row["path"] for row in story["sources"] if row["status"] == "partial" and row["path"].startswith("packets/")}
        self.assertEqual(partial, {"packets/repeat.md", "packets/" + current + ".md"})
        self.assertNotIn("unavailable", [e["status"] for e in records])
        # A record status that changes after the budget still changes what the page shows.
        before = story["content_fingerprint"]
        (self.root / "loops" / (history[0] + "-terminal.json")).write_text(json.dumps({"run_id": run_id, "action": history[0], "status": "complete"}))
        with mock.patch.object(self.story, "EVIDENCE_FILES", 2):
            changed, _ = self.build()
        self.assertNotEqual(before, changed["content_fingerprint"])
        self.assertEqual(next(e["status"] for e in changed["events"] if e["kind"] == "until" and e["action"] == history[0]), "complete")

    def test_a_record_with_no_status_says_so_instead_of_unknown(self):
        (self.root / "checks").mkdir()
        (self.root / "checks" / (self.action + ".md")).write_text(store.dumps({"run_id": self.state["run_id"], "action": self.action}))
        (self.root / "expectations").mkdir()
        (self.root / "expectations" / (self.action + ".md")).write_text(store.dumps({"schema": "shiploop-expectations/v1", "action": self.action, "results": []}))
        story, _ = self.build()
        records = [e for e in story["events"] if e["kind"] in ("check", "expectation")]
        self.assertEqual([e["status"] for e in records], [None, None])
        self.assertTrue(all("no status recorded" in e["summary"] and "unknown" not in e["summary"] for e in records))

    def test_unchanged_files_are_reused_without_a_read_and_changed_ones_are_read_again(self):
        (self.root / "loops").mkdir()
        (self.root / "checks").mkdir()
        receipt = self.root / "loops" / (self.action + "-terminal.json")
        check = self.root / "checks" / (self.action + ".md")
        receipt.write_text(json.dumps({"run_id": self.state["run_id"], "action": self.action, "status": "active"}))
        check.write_text(store.dumps({"run_id": self.state["run_id"], "action": self.action, "answer": "yes"}))
        self.append("trace.jsonl", {"kind": "hook", "text": "first"})
        first, captures = self.build(observed_at="first read")
        calls = []
        real = self.io.capture
        def counting(root, relative, *args, **kwargs):
            calls.append(relative)
            return real(root, relative, *args, **kwargs)
        with mock.patch.object(self.io, "capture", side_effect=counting):
            second, reused = self.build(previous=captures, observed_at="second read")
        # Only the three JSONL streams are captured fresh; the unchanged evidence files are not read.
        # (A missing current packet copy is never reused: there is nothing to reuse.)
        self.assertEqual(sorted(c for c in calls if not c.startswith("packets/")),
                         ["progress-observations.jsonl", "skill-calls.jsonl", "trace.jsonl"])
        self.assertNotIn("loops/" + self.action + "-terminal.json", calls)
        self.assertNotIn("checks/" + self.action + ".md", calls)
        def shown(value):
            if isinstance(value, dict):
                return {k: shown(v) for k, v in value.items() if k != "observed_at"}
            return [shown(v) for v in value] if isinstance(value, list) else value
        self.assertEqual(shown(first), shown(second))
        self.assertEqual(first["content_fingerprint"], second["content_fingerprint"])
        self.assertEqual(first["activity_fingerprint"], second["activity_fingerprint"])
        rel = "loops/" + self.action + "-terminal.json"
        self.assertEqual(reused[rel]["raw"], captures[rel]["raw"])
        self.assertEqual(reused[rel]["generation"], captures[rel]["generation"])
        self.assertEqual(next(s for s in second["sources"] if s["path"] == rel)["observed_at"], "second read")
        self.assertEqual(captures[rel]["source"]["observed_at"], "first read")  # the retained capture is not mutated
        # A different size is read again and shows the new content.
        receipt.write_text(json.dumps({"run_id": self.state["run_id"], "action": self.action, "status": "stopped", "pad": "x"}))
        calls.clear()
        with mock.patch.object(self.io, "capture", side_effect=counting):
            third, _ = self.build(previous=reused, observed_at="third read")
        self.assertIn(rel, calls)
        self.assertNotIn("checks/" + self.action + ".md", calls)
        self.assertEqual(next(e["status"] for e in third["events"] if e["kind"] == "until"), "stopped")
        self.assertNotEqual(second["content_fingerprint"], third["content_fingerprint"])
        self.assertNotEqual(second["activity_fingerprint"], third["activity_fingerprint"])
        # Same size, different mtime is read again too.
        raw = check.read_bytes()
        check.write_bytes(raw.replace(b"yes", b"no_"))
        os.utime(check, ns=(captures["checks/" + self.action + ".md"]["mtime_ns"] + 5_000_000_000,) * 2)
        calls.clear()
        with mock.patch.object(self.io, "capture", side_effect=counting):
            fourth, _ = self.build(previous=reused, observed_at="fourth read")
        self.assertIn("checks/" + self.action + ".md", calls)
        self.assertEqual(next(e["status"] for e in fourth["events"] if e["kind"] == "check"), "no_")

    def test_unchanged_trusts_only_a_matching_good_capture_of_a_regular_single_link_file(self):
        target = self.root / "note.txt"
        target.write_text("one")
        good = self.io.capture(self.root, "note.txt", 1024, "t")
        self.assertTrue(self.io.unchanged(self.root, "note.txt", good))
        self.assertFalse(self.io.unchanged(self.root, "note.txt", None))
        self.assertFalse(self.io.unchanged(self.root, "note.txt", {}))
        self.assertFalse(self.io.unchanged(self.root, "missing.txt", good))
        self.assertFalse(self.io.unchanged(self.root, "../outside.txt", good))
        self.assertFalse(self.io.unchanged(self.root, "no-such-dir/note.txt", good))
        stale = dict(good, source=dict(good["source"], status="stale"))
        self.assertFalse(self.io.unchanged(self.root, "note.txt", stale))
        target.write_text("three")  # size differs
        self.assertFalse(self.io.unchanged(self.root, "note.txt", good))
        target.write_text("one")
        again = self.io.capture(self.root, "note.txt", 1024, "t")
        os.utime(target, ns=(again["mtime_ns"] + 1_000_000_000,) * 2)  # same size, mtime differs
        self.assertFalse(self.io.unchanged(self.root, "note.txt", again))
        fresh = self.io.capture(self.root, "note.txt", 1024, "t")
        replacement = self.root / "replacement.txt"
        replacement.write_text("one")
        os.utime(replacement, ns=(fresh["mtime_ns"],) * 2)
        os.replace(replacement, target)  # same size and mtime, new inode
        self.assertFalse(self.io.unchanged(self.root, "note.txt", fresh))
        kept = self.io.capture(self.root, "note.txt", 1024, "t")
        os.link(target, self.root / "second-link.txt")
        self.assertFalse(self.io.unchanged(self.root, "note.txt", kept))
        os.unlink(self.root / "second-link.txt")
        self.assertTrue(self.io.unchanged(self.root, "note.txt", kept))
        target.unlink()
        target.symlink_to(self.root / "state-never.txt")
        self.assertFalse(self.io.unchanged(self.root, "note.txt", kept))

    def reviewed_state(self):
        """A state whose spec visit was reviewed by a finished Improve pass (its ids named as a real run records them)."""
        state = navigator.new_state(str(self.repo), "Synthetic Improve visit")
        while navigator.current_stage(state) != "spec":
            state = navigator.apply(state, navigator.current_action(state)["id"], {"outcome": "done", "summary": "Accepted planning input"})
        reviewed = navigator.current_action(state)["id"]
        state = navigator.apply(state, reviewed, {"outcome": "done", "summary": "Review the accepted scope"})
        child = state["active_improve"]["improve_action"]
        state = navigator.finish_improve(state, reviewed, _improve_receipt("spec"))
        state["improve_results"][reviewed].update(improve_action=child, runtime_phase="complete")
        return state, reviewed, child

    def test_improve_pass_events_belong_to_the_visit_it_reviewed(self):
        state, reviewed, child = self.reviewed_state()
        self.assertTrue(state["improve_results"][reviewed])
        self.append("trace.jsonl", {"kind": "hook", "text": "names no action and follows no packet"})
        self.append("trace.jsonl", {"kind": "packet", "action": child, "stage": "improve", "reviewed": "spec", "chars": 100, "whole": True})
        self.append("trace.jsonl", {"kind": "command", "verb": "improve-pass", "action": child, "exit": 0})
        self.append("trace.jsonl", {"kind": "command", "verb": "complete", "action": reviewed, "exit": 0})
        story, _ = self.story.build(self.root, state, self.timeline)
        visit = next(v for v in story["visits"] if v["action"] == reviewed)
        owned = [e for e in story["events"] if e["id"] in visit["events"]]
        self.assertEqual(visit["improve"], {"action": child, "phase": "complete"})
        self.assertEqual([e["kind"] for e in owned if e["kind"] != "accepted"], ["packet", "command", "command"])
        self.assertEqual({e["improve_of"] for e in owned if e["action"] == child}, {reviewed})
        self.assertEqual(sum(1 for e in owned if e["action"] == child), 2)
        self.assertTrue(all("improve_of" not in e for e in owned if e["action"] != child))
        # Only the hook, which names no action and follows no packet, is left unowned; no Improve event is.
        claimed = {eid for v in story["visits"] for eid in v["events"]}
        self.assertEqual([e["kind"] for e in story["events"] if e["id"] not in claimed], ["hook"])
        self.assertTrue(all("improve" not in v for v in story["visits"] if v["action"] != reviewed))

    def test_improve_ownership_ignores_malformed_records_and_leaves_the_active_pass_alone(self):
        state, reviewed, _child = self.reviewed_state()
        results = state["improve_results"]
        results["not-a-visit"] = {"improve_action": "nav-orphan"}
        results["broken"] = "junk"
        results[reviewed + "-x"] = {"improve_action": 7}
        results[42] = {"improve_action": "nav-int-key"}
        self.append("trace.jsonl", {"kind": "command", "verb": "improve-pass", "action": "nav-orphan", "exit": 0})
        story, _ = self.story.build(self.root, state, self.timeline)
        orphan = next(e for e in story["events"] if e["action"] == "nav-orphan")
        self.assertNotIn("improve_of", orphan)
        self.assertNotIn(orphan["id"], {eid for v in story["visits"] for eid in v["events"]})
        # An active Improve pass keeps its own visit and its own events, as before.
        active = navigator.new_state(str(self.repo), "Synthetic Improve visit")
        while navigator.current_stage(active) != "spec":
            active = navigator.apply(active, navigator.current_action(active)["id"], {"outcome": "done", "summary": "Accepted planning input"})
        active = navigator.apply(active, navigator.current_action(active)["id"], {"outcome": "done", "summary": "Review the accepted scope"})
        pass_action = active["active_improve"]["improve_action"]
        self.append("trace.jsonl", {"kind": "command", "verb": "improve-pass", "action": pass_action, "exit": 0})
        story, _ = self.story.build(self.root, active, self.timeline)
        visit = story["visits"][-1]
        self.assertEqual((visit["stage"], visit["action"]), ("improve", pass_action))
        self.assertNotIn("improve", visit)
        owned = [e for e in story["events"] if e["id"] in visit["events"]]
        self.assertEqual([e["verb"] if "verb" in e else e["summary"] for e in owned], ["improve-pass"])
        self.assertTrue(all("improve_of" not in e for e in story["events"]))

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
