"""Synthetic verifier tests; they exercise the fixture without launching agents."""

from __future__ import annotations

import json
import builtins
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import fixture


class FixtureVerifierTests(unittest.TestCase):
    """Construct fully synthetic child worktrees for local verifier checks."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ask-agent-fixture-test-")
        self.addCleanup(self.temp.cleanup)
        self.temp_root = Path(self.temp.name)
        self.source_skill = self.temp_root / "source" / "ask-agent"
        (self.source_skill / "scripts").mkdir(parents=True)
        (self.source_skill / "references").mkdir()
        (self.source_skill / "SKILL.md").write_text(
            "---\nname: ask-agent\n---\nSynthetic package fixture.\n", encoding="utf-8"
        )
        (self.source_skill / "scripts" / "ask_agent_workspace.py").write_text(
            "def helper():\n    return 'synthetic'\n", encoding="utf-8"
        )
        (self.source_skill / "references" / "contract.md").write_text(
            "Synthetic package content.\n", encoding="utf-8"
        )
        self.run_path = self.temp_root / "run"
        self.manifest = fixture.prepare_fixture(
            self.run_path,
            3,
            "parallel",
            source_skill=self.source_skill,
        )

    def test_capture_repo_state_uses_private_index_when_shared_lock_exists(self) -> None:
        caller = Path(self.manifest["paths"]["caller"])
        index_path = Path(self.manifest["caller_snapshot"]["index_path"])
        lock_path = index_path.with_name(index_path.name + ".lock")
        original_index = index_path.read_bytes()
        lock_payload = b"active writer sentinel\n"
        lock_path.write_bytes(lock_payload)
        state = None
        try:
            state = fixture.capture_repo_state(caller)
        finally:
            lock_after = lock_path.read_bytes() if lock_path.exists() else None
            index_after = index_path.read_bytes()
            if lock_path.exists():
                lock_path.unlink()

        self.assertEqual(lock_after, lock_payload)
        self.assertEqual(index_after, original_index)
        self.assertIsNotNone(state)
        self.assertEqual(state["index_tree"], self.manifest["caller_snapshot"]["index_tree"])

    def _write_dirty_snapshot(self, root: Path) -> None:
        (root / "dual.txt").write_text("staged\n", encoding="utf-8")
        fixture.git(root, "add", "dual.txt")
        (root / "dual.txt").write_text("unstaged\n", encoding="utf-8")
        (root / "notes.txt").write_text("snapshot notes\n", encoding="utf-8")
        (root / "added.txt").write_text("staged add\n", encoding="utf-8")
        fixture.git(root, "add", "added.txt")
        (root / "deleted.txt").unlink()

    def _synthetic_worker_set(self) -> list[Path]:
        """Create known correct task edits for verifier tests, never a live agent."""
        primary = Path(self.manifest["paths"]["primary"])
        caller = Path(self.manifest["paths"]["caller"])
        head = self.manifest["caller_snapshot"]["head"]
        children: list[Path] = []
        for task in self.manifest["task_assignments"]:
            task_id = int(task["worker_id"])
            child = self.run_path / f"synthetic-worker-{task_id}"
            fixture.git(primary, "worktree", "add", "-b", f"synthetic-worker-{task_id}", str(child), head)
            self._write_dirty_snapshot(child)
            fixture.probe_run(self.run_path, task["worker_id"], "start", cwd=child)
            (child / task["path"]).write_text(
                "def transform(x):\n"
                f"    return ({task_id} + 1) * x + {task_id} * {task_id}\n",
                encoding="utf-8",
            )
            fixture.probe_run(self.run_path, task["worker_id"], "finish", cwd=child)
            (caller / task["path"]).write_bytes((child / task["path"]).read_bytes())
            children.append(child)
        return children

    def _mutate_probe(self, selected_worker: str, selected_phase: str, **changes: Any) -> None:
        path = self.run_path / "operator" / "probes" / f"worker-{selected_worker}-{selected_phase}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record.update(changes)
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _set_hold_timeline(self, *, seconds: float, mode: str, stride: float = 2) -> None:
        manifest_path = self.run_path / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["mode"] = mode
        manifest["hold_seconds"] = seconds
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        base_utc = datetime(2026, 1, 1, tzinfo=timezone.utc)
        base_monotonic = 1000.0
        for task in manifest["task_assignments"]:
            worker_id = task["worker_id"]
            offset = (int(worker_id) - 1) * stride
            start_utc = base_utc + timedelta(seconds=offset)
            finish_utc = start_utc + timedelta(seconds=seconds)
            start_mono = base_monotonic + offset
            finish_mono = start_mono + seconds
            hold_fields = {
                "hold_started_at_utc": start_utc.isoformat(timespec="milliseconds"),
                "hold_finished_at_utc": finish_utc.isoformat(timespec="milliseconds"),
                "hold_started_monotonic_seconds": start_mono,
                "hold_finished_monotonic_seconds": finish_mono,
                "hold_elapsed_seconds": seconds,
            }
            self._mutate_probe(
                worker_id,
                "start",
                hold_seconds_requested=seconds,
                **hold_fields,
            )
            self._mutate_probe(worker_id, "finish", **hold_fields)

    def test_synthetic_correct_workers_pass(self) -> None:
        self.assertFalse(self.manifest["seed_feedback_backlog"])
        self.assertFalse(
            (Path(self.manifest["paths"]["primary"])
             / "tasks/in-progress/prompt-improvements-backlog.md").exists()
        )
        self._synthetic_worker_set()
        report = fixture.verify_fixture(self.run_path)
        self.assertTrue(report["passed"], report["errors"])
        self.assertTrue(report["checks"]["worker_roots_distinct_from_parent_and_each_other"])
        self.assertTrue(report["checks"]["worker_index_paths_unique"])
        self.assertTrue(report["checks"]["combined_pipeline_oracle_passes"])

    def test_seeded_feedback_backlog_is_hashed_and_preserved(self) -> None:
        self.run_path = self.temp_root / "seeded-run"
        self.manifest = fixture.prepare_fixture(
            self.run_path,
            3,
            "parallel",
            source_skill=self.source_skill,
            seed_feedback_backlog=True,
        )
        relative_path = "tasks/in-progress/prompt-improvements-backlog.md"
        expected = (
            b"# Prompt Improvement Backlog\n\n"
            b"Generated by feedback-collector plugin.\n\n"
        )
        expected_hash = 'sha256:' + fixture.sha256_bytes(expected)
        primary = Path(self.manifest["paths"]["primary"])
        caller = Path(self.manifest["paths"]["caller"])
        self.assertTrue(self.manifest["seed_feedback_backlog"])
        self.assertEqual((primary / relative_path).read_bytes(), expected)
        self.assertEqual(
            self.manifest["primary_snapshot"]["working_tree"]["files"][relative_path],
            expected_hash,
        )
        self.assertEqual(
            self.manifest["caller_snapshot"]["working_tree"]["files"][relative_path],
            expected_hash,
        )

        self._synthetic_worker_set()
        report = fixture.verify_fixture(self.run_path)
        self.assertTrue(report["passed"], report["errors"])
        self.assertTrue(report["checks"]["primary_pristine_fingerprint_preserved"])
        self.assertTrue(report["checks"]["caller_dirty_head_index_and_content_preserved"])

        (caller / relative_path).write_bytes(expected + b"unexpected append\n")
        changed_report = fixture.verify_fixture(self.run_path)
        self.assertFalse(changed_report["checks"]["exact_allowed_caller_source_changes"])
        self.assertFalse(changed_report["checks"]["caller_dirty_head_index_and_content_preserved"])

    def test_missing_probe_fails_closed_and_writes_report(self) -> None:
        report = fixture.verify_fixture(self.run_path)
        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["worker_probe_completeness"])
        self.assertTrue((self.run_path / "operator" / "verification.json").is_file())

    def test_duplicate_child_root_is_rejected(self) -> None:
        children = self._synthetic_worker_set()
        duplicate_root = str(children[0].resolve())
        self._mutate_probe("2", "start", root=duplicate_root)
        self._mutate_probe("2", "finish", root=duplicate_root)
        report = fixture.verify_fixture(self.run_path)
        self.assertFalse(report["checks"]["worker_roots_distinct_from_parent_and_each_other"])
        self.assertFalse(report["passed"])

    def test_empty_probe_checks_and_tampered_identity_fail_closed(self) -> None:
        self._synthetic_worker_set()
        self._mutate_probe("1", "finish", checks={})
        self._mutate_probe("2", "start", run_id="wrong-run")
        self._mutate_probe("2", "finish", worker_id="wrong-worker")
        self._mutate_probe("3", "finish", phase="start", root="")
        report = fixture.verify_fixture(self.run_path)
        self.assertFalse(report["checks"]["worker_probe_completeness"])
        self.assertFalse(report["passed"])
        workers = {item["worker_id"]: item for item in report["worker_results"]}
        self.assertFalse(workers["1"]["record_schema"]["finish"]["passed"])
        self.assertFalse(workers["2"]["record_schema"]["start"]["passed"])
        self.assertFalse(workers["2"]["record_schema"]["finish"]["passed"])
        self.assertFalse(workers["3"]["record_schema"]["finish"]["passed"])

    def test_duplicate_probe_does_not_replace_existing_record_bytes(self) -> None:
        children = self._synthetic_worker_set()
        for phase in ("start", "finish"):
            record_path = self.run_path / "operator" / "probes" / f"worker-1-{phase}.json"
            original = record_path.read_bytes()
            with self.assertRaises(fixture.FixtureError):
                fixture.probe_run(self.run_path, "1", phase, cwd=children[0])
            self.assertEqual(record_path.read_bytes(), original)

    def test_wrong_integrated_output_fails_independent_oracles(self) -> None:
        self._synthetic_worker_set()
        caller = Path(self.manifest["paths"]["caller"])
        (caller / "src" / "step_2.py").write_text(
            "def transform(x):\n    return 999\n", encoding="utf-8"
        )
        report = fixture.verify_fixture(self.run_path)
        self.assertFalse(report["checks"]["integrated_per_task_result_oracles_pass"])
        self.assertFalse(report["checks"]["combined_pipeline_oracle_passes"])
        self.assertFalse(report["passed"])

    def test_dirty_parent_input_corruption_is_rejected(self) -> None:
        self._synthetic_worker_set()
        caller = Path(self.manifest["paths"]["caller"])
        (caller / "dual.txt").write_text("corrupted\n", encoding="utf-8")
        report = fixture.verify_fixture(self.run_path)
        self.assertFalse(report["checks"]["exact_allowed_caller_source_changes"])
        self.assertFalse(report["checks"]["caller_dirty_head_index_and_content_preserved"])
        self.assertFalse(report["passed"])

    def test_parallel_hold_intervals_without_overlap_fail(self) -> None:
        self._synthetic_worker_set()
        self._set_hold_timeline(seconds=1, mode="parallel")
        report = fixture.verify_fixture(self.run_path)
        self.assertTrue(report["checks"]["hold_intervals_valid"])
        self.assertFalse(report["checks"]["parallel_hold_intervals_overlap"])
        self.assertFalse(report["passed"])

    def test_sequential_hold_intervals_do_not_need_overlap(self) -> None:
        self._synthetic_worker_set()
        self._set_hold_timeline(seconds=1, mode="sequential")
        report = fixture.verify_fixture(self.run_path)
        self.assertTrue(report["checks"]["hold_intervals_valid"])
        self.assertFalse(report["parallel_overlap"]["required"])
        self.assertTrue(report["checks"]["parallel_hold_intervals_overlap"])

    def test_module_oracle_timeout_isolated_from_parent_interpreter(self) -> None:
        module = self.temp_root / "slow_step.py"
        marker = "_ask_agent_fixture_child_process_marker"
        module.write_text(
            "import builtins, time\n"
            f"builtins.{marker} = True\n"
            "def transform(x):\n"
            "    time.sleep(30)\n"
            "    return 2 * x + 1\n",
            encoding="utf-8",
        )
        result = fixture.check_module_oracle(module, 1, timeout=0.5)
        self.assertTrue(result.get("timed_out"))
        self.assertFalse(hasattr(builtins, marker))


if __name__ == "__main__":
    unittest.main()
