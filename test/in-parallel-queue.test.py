#!/usr/bin/env python3
"""Offline black-box queue tests for In Parallel's coordinator contract."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
_FIXTURE_SPEC = importlib.util.spec_from_file_location(
    "agent_harness_queue_fixtures", ROOT / "test/agent-harness.test.py"
)
assert _FIXTURE_SPEC is not None and _FIXTURE_SPEC.loader is not None
_FIXTURES = importlib.util.module_from_spec(_FIXTURE_SPEC)
_FIXTURE_SPEC.loader.exec_module(_FIXTURES)


class InParallelQueueTests(unittest.TestCase):
    """Borrow selected fixture methods without inheriting its test methods."""

    setUp = _FIXTURES.AgentHarnessOfflineContractTests.setUp
    _git = _FIXTURES.AgentHarnessOfflineContractTests._git
    _write_json = _FIXTURES.AgentHarnessOfflineContractTests._write_json
    _harness = _FIXTURES.AgentHarnessOfflineContractTests._harness
    _json_command = _FIXTURES.AgentHarnessOfflineContractTests._json_command
    _task = _FIXTURES.AgentHarnessOfflineContractTests._task
    _request = _FIXTURES.AgentHarnessOfflineContractTests._request
    _init = _FIXTURES.AgentHarnessOfflineContractTests._init
    _dispatch = _FIXTURES.AgentHarnessOfflineContractTests._dispatch
    _launches = _FIXTURES.AgentHarnessOfflineContractTests._launches
    _prepared = _FIXTURES.AgentHarnessOfflineContractTests._prepared
    _prepared_command = _FIXTURES.AgentHarnessOfflineContractTests._prepared_command
    _worker = _FIXTURES.AgentHarnessOfflineContractTests._worker
    _handle = _FIXTURES.AgentHarnessOfflineContractTests._handle
    _confirm_launch = _FIXTURES.AgentHarnessOfflineContractTests._confirm_launch
    _result = _FIXTURES.AgentHarnessOfflineContractTests._result
    _collect = _FIXTURES.AgentHarnessOfflineContractTests._collect
    _accept = _FIXTURES.AgentHarnessOfflineContractTests._accept
    _write_verification = _FIXTURES.AgentHarnessOfflineContractTests._write_verification
    _verification = _FIXTURES.AgentHarnessOfflineContractTests._verification
    _sha256 = _FIXTURES.AgentHarnessOfflineContractTests._sha256
    _git_snapshot = _FIXTURES.AgentHarnessOfflineContractTests._git_snapshot
    _make_dirty_parent = _FIXTURES.AgentHarnessOfflineContractTests._make_dirty_parent
    _worktree_registered = _FIXTURES.AgentHarnessOfflineContractTests._worktree_registered

    def _tasks(self, prefix: str, count: int) -> list[dict[str, Any]]:
        return [self._task(f"{prefix}-{number}", write_set=[]) for number in range(1, count + 1)]

    def _expected_findings(self, task_ids: list[str]) -> dict[str, str]:
        return {task_id: f"finding::{task_id}::decision=verified" for task_id in task_ids}

    def _new_run(self, tasks: list[dict[str, Any]], name: str, *, capacity: int | None = None) -> Path:
        run = self._init(self._request(
            tasks, workspace="current", mode="report-only", capacity=capacity,
        ), name)
        return run

    def _run_worker(self, run: Path, launch: Mapping[str, Any], *, finding: str,
                    status: str = "SUCCEEDED", edits: Mapping[str, str] | None = None,
                    commit: bool = False) -> dict[str, Any]:
        handle = self._confirm_launch(run, launch)
        start, _finish = self._worker(run, launch, edits=edits, commit=commit)
        self.assertFalse(start.get("native_lifecycle_verified"), start)
        result = self._result(launch, handle, status=status)
        result["summary"] = f"[OFFLINE SIMULATED NATIVE RESULT] {finding}"
        result["criteria"][0]["observed"] = f"OFFLINE FIXTURE OBSERVED: {finding}"
        collected = self._collect(run, launch, result, name="queue-fixture")
        self.assertEqual(collected.get("status"), "AWAITING_VERIFICATION", collected)
        record = json.loads(
            (run / "collected" / f"{launch['attempt']}.json").read_text(encoding="utf-8")
        )
        self.assertEqual(record.get("native_evidence_kind"), "coordinator_attestation", record)
        self.assertIn("[OFFLINE SIMULATED NATIVE RESULT]", record["result"]["summary"])
        self.assertFalse(record["verified"].get("native_lifecycle_verified"), record)
        return record

    def _accept_finding(self, run: Path, launch: Mapping[str, Any], finding: str,
                        *, edits: Mapping[str, str] | None = None,
                        commit: bool = False) -> dict[str, Any]:
        record = self._run_worker(run, launch, finding=finding, edits=edits, commit=commit)
        response = self._accept(run, launch)
        self.assertEqual(response.get("status"), "RECORDED_STATUS", response)
        return record

    def _reject_finding(self, run: Path, launch: Mapping[str, Any], finding: str) -> dict[str, Any]:
        record = self._run_worker(run, launch, finding=finding, status="FAILED")
        verification = self._write_verification(
            launch, passed=False, reason=f"OFFLINE FIXTURE rejected failed attempt for {launch['task']}."
        )
        response = self._harness(
            "accept", "--run", str(run), "--attempt", launch["attempt"],
            "--verification", str(verification),
        )
        self.assertEqual(response.get("status"), "RECORDED_STATUS", response)
        saved = json.loads((run / "verified" / f"{launch['attempt']}.json").read_text(encoding="utf-8"))
        self.assertFalse(saved["passed"], saved)
        return record

    def _active_attempts(self, run: Path, capacity: int) -> set[str]:
        status = self._harness("status", "--run", str(run))
        self.assertEqual(status.get("status"), "RECORDED_STATUS", status)
        active = status.get("active")
        self.assertIsInstance(active, list, status)
        attempts = [item["attempt"] for item in active]
        self.assertEqual(len(attempts), len(set(attempts)), attempts)
        reservations = [item for item in active if item.get("status") in ("claimed", "launching", "running")]
        self.assertLessEqual(len(reservations), capacity, active)
        return {item["attempt"] for item in reservations}

    def _assert_final_aggregate(self, finished: dict[str, Any], task_ids: list[str],
                                findings: Mapping[str, str], records: Mapping[str, dict[str, Any]],
                                *, integration: str = "current-workspace-unchanged") -> None:
        self.assertEqual(finished.get("status"), "SUCCEEDED", finished)
        self.assertEqual(finished["integration"]["outcome"], integration, finished)
        workers = finished.get("workers")
        self.assertIsInstance(workers, list, finished)
        worker_ids = [worker["id"] for worker in workers]
        self.assertEqual(len(worker_ids), len(set(worker_ids)), worker_ids)
        self.assertEqual(set(worker_ids), set(task_ids))
        expected_summaries = {
            task_id: f"[OFFLINE SIMULATED NATIVE RESULT] {findings[task_id]}"
            for task_id in task_ids
        }
        self.assertEqual({worker["id"]: worker["summary"] for worker in workers}, expected_summaries)
        for task_id in task_ids:
            record = records[task_id]
            self.assertEqual(record["result"]["summary"], expected_summaries[task_id])
            self.assertEqual(record["result"]["criteria"][0]["observed"],
                             f"OFFLINE FIXTURE OBSERVED: {findings[task_id]}")
        self.assertEqual(finished.get("native_lifecycle"),
                         "coordinator-attested; experiment host traces are separate evidence")

    def _finish_blocked(self, run: Path) -> dict[str, Any]:
        blocked = self._harness("finish", "--run", str(run), success=False)
        self.assertEqual(blocked.get("code"), "WORKERS_NOT_ACCEPTED", blocked)
        self.assertFalse((run / "result.json").exists())
        return blocked

    def _worktree_outputs(self, task_id: str) -> dict[str, str]:
        return {
            f"contributions/{task_id}.txt": f"contribution::{task_id}\n",
            f"resources/{task_id}.json": json.dumps(
                {"id": task_id, "resource": f"resource::{task_id}"}, sort_keys=True,
            ) + "\n",
        }

    def _exercise_worktree_output_queue(self, *, run_name: str, task_count: int,
                                        capacity: int | None, expected_capacity: int) -> None:
        before = self._make_dirty_parent()
        parent_files = {
            name: (self.source / name).read_bytes()
            for name in (".gitignore", ".claspignore", "caller.txt", "caller-note.txt")
        }
        task_ids = [f"{run_name}-{number}" for number in range(1, task_count + 1)]
        outputs_by_task = {task_id: self._worktree_outputs(task_id) for task_id in task_ids}
        expected_files = {
            path: content
            for task_outputs in outputs_by_task.values()
            for path, content in task_outputs.items()
        }
        tasks = [self._task(task_id, write_set=list(outputs_by_task[task_id])) for task_id in task_ids]
        check_code = (
            "from pathlib import Path; expected = " + repr(expected_files) +
            "; actual = {path: Path(path).read_text(encoding='utf-8') for path in expected}; "
            "assert actual == expected, (actual, expected); "
            "print('all queued contributions and resources verified')"
        )
        request = self._request(
            tasks, workspace="worktree", mode="edit", capacity=capacity, integration="apply",
            checks=[[sys.executable, "-c", check_code]],
        )
        self.assertEqual("capacity" in request, capacity is not None, request)
        run = self._init(request, run_name)
        metadata = json.loads((run / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["request"]["capacity"], expected_capacity, metadata["request"])
        self.assertEqual(list((run / "prepared").glob("*.json")), [],
                         "Planning the full backlog must not prepare workers eagerly")
        self.assertTrue(all(not (self.source / path).exists() for path in expected_files))

        response = self._dispatch(run)
        self.assertEqual(response.get("status"), "LAUNCH_REQUIRED", response)
        initial = response.get("launches", [])
        self.assertEqual(len(initial), expected_capacity, initial)
        self.assertEqual({launch["task"] for launch in initial}, set(task_ids[:expected_capacity]))

        scheduled: list[dict[str, Any]] = []
        scheduled_ids: list[str] = []
        attempts: set[str] = set()
        handles: set[str] = set()
        handles_by_attempt: dict[str, str] = {}
        worktree_cwds: set[str] = set()
        launch_by_task: dict[str, dict[str, Any]] = {}
        active: dict[str, dict[str, Any]] = {}
        records: dict[str, dict[str, Any]] = {}
        completion_order: list[str] = []

        def remember_launches(launches: list[dict[str, Any]]) -> None:
            for launch in launches:
                task_id = launch["task"]
                attempt = launch["attempt"]
                cwd = launch["cwd"]
                worker_root = Path(cwd)
                handle = self._handle(launch)
                self.assertIn(task_id, task_ids, launch)
                self.assertNotIn(task_id, scheduled_ids, launch)
                self.assertNotIn(attempt, attempts, launch)
                self.assertNotIn(handle, handles, launch)
                self.assertNotIn(cwd, worktree_cwds, launch)
                self.assertTrue(worker_root.is_absolute(), launch)
                self.assertTrue(worker_root.is_dir(), launch)
                self.assertTrue(self._worktree_registered(worker_root), launch)
                for name, contents in parent_files.items():
                    self.assertEqual((worker_root / name).read_bytes(), contents, (launch, name))
                for path in expected_files:
                    self.assertFalse((worker_root / path).exists(), (launch, path))
                attempts.add(attempt)
                handles.add(handle)
                handles_by_attempt[attempt] = handle
                worktree_cwds.add(cwd)
                scheduled_ids.append(task_id)
                scheduled.append(launch)
                launch_by_task[task_id] = launch
                active[attempt] = launch

        def assert_parent_untouched() -> None:
            self.assertEqual(self._git_snapshot(self.source), before)
            for name, contents in parent_files.items():
                self.assertEqual((self.source / name).read_bytes(), contents, name)
            for path in expected_files:
                self.assertFalse((self.source / path).exists(), path)

        remember_launches(initial)
        self.assertEqual({path.stem for path in (run / "prepared").glob("*.json")}, attempts)
        self.assertEqual(self._active_attempts(run, expected_capacity), set(active))
        assert_parent_untouched()

        # Finish a later initial task first, then an earlier one, so refill is
        # exercised while other initially reserved contexts remain active.
        completion_queue = [initial[-1], *initial[:-1]]
        while completion_queue:
            launch = completion_queue.pop(0)
            task_id = launch["task"]
            self.assertIn(launch["attempt"], active)
            self.assertNotIn(task_id, records)
            if len(records) == task_count - 1:
                self._finish_blocked(run)
                assert_parent_untouched()

            record = self._accept_finding(
                run, launch, self._expected_findings([task_id])[task_id],
                edits=outputs_by_task[task_id], commit=True,
            )
            self.assertEqual(record["result"]["native_handle"], handles_by_attempt[launch["attempt"]])
            records[task_id] = record
            completion_order.append(task_id)
            active.pop(launch["attempt"])
            assert_parent_untouched()

            pending = set(task_ids) - set(scheduled_ids)
            response = self._dispatch(run)
            new_launches = response.get("launches", [])
            expected_new = min(expected_capacity - len(active), len(pending))
            self.assertEqual(len(new_launches), expected_new, response)
            self.assertEqual(response.get("status"),
                             "LAUNCH_REQUIRED" if expected_new else "NO_NEW_LAUNCH", response)
            reserved_before_refill = set(active)
            remember_launches(new_launches)
            if len(records) == 1:
                self.assertEqual(len(new_launches), 1, response)
                self.assertEqual(len(active), expected_capacity, active)
                self.assertEqual({item["attempt"] for item in initial[:-1]}, reserved_before_refill)
                self.assertTrue(reserved_before_refill.issubset(active), active)
                self._finish_blocked(run)
                assert_parent_untouched()
            completion_queue.extend(new_launches)
            self.assertLessEqual(len(active), expected_capacity, active)
            self.assertEqual(self._active_attempts(run, expected_capacity), set(active))
            self.assertEqual({path.stem for path in (run / "prepared").glob("*.json")}, attempts,
                             "Only yielded queue items may have prepared worker contexts")

        self.assertEqual(completion_order[:2], [initial[-1]["task"], initial[0]["task"]])
        self.assertNotEqual(completion_order[:2], [launch["task"] for launch in initial[:2]])
        self.assertEqual(set(scheduled_ids), set(task_ids))
        self.assertEqual(len(scheduled_ids), task_count)
        self.assertEqual(len(attempts), task_count)
        self.assertEqual(len(handles), task_count)
        self.assertEqual(len(worktree_cwds), task_count)
        self.assertEqual(set(records), set(task_ids))
        self.assertEqual(active, {})
        self.assertEqual(self._active_attempts(run, expected_capacity), set())
        self.assertEqual(self._dispatch(run).get("status"), "NO_NEW_LAUNCH")
        assert_parent_untouched()

        finished = self._harness("finish", "--run", str(run))
        self._assert_final_aggregate(finished, task_ids, self._expected_findings(task_ids), records,
                                     integration="applied")
        self.assertEqual(finished.get("cleanup_status"), "complete", finished)
        applied_paths = finished["integration"]["applied_paths"]
        self.assertEqual(len(applied_paths), len(expected_files))
        self.assertEqual(set(applied_paths), set(expected_files))
        self.assertTrue(finished["integration"]["postcondition"]["head_and_index_preserved"])
        self.assertTrue(finished["integration"]["postcondition"]["worker_files_match"])
        for path, content in expected_files.items():
            self.assertEqual((self.source / path).read_text(encoding="utf-8"), content, path)
        for name, contents in parent_files.items():
            self.assertEqual((self.source / name).read_bytes(), contents, name)
        after = self._git_snapshot(self.source)
        for key in ("head", "index_bytes", "index_entries", "cached_diff"):
            self.assertEqual(after[key], before[key], key)
        self.assertIn("caller.txt", after["status"])
        self.assertIn("caller-note.txt", after["status"])

        committed_workers = finished["integration"].get("workers")
        self.assertIsInstance(committed_workers, list, finished["integration"])
        self.assertEqual({worker["id"] for worker in committed_workers}, set(task_ids))
        registered = self._git(self.source, "worktree", "list", "--porcelain").stdout.splitlines()
        for worker in committed_workers:
            self.assertTrue(worker.get("commits"), worker)
            worker_root = Path(launch_by_task[worker["id"]]["cwd"])
            self.assertFalse(worker_root.exists(), worker)
            self.assertNotIn("worktree " + str(worker_root), registered)
            for commit in worker["commits"]:
                self.assertIn(commit, finished["retained_locations"])
                self._git(self.source, "cat-file", "-e", f"{commit}^{{commit}}")
            accepted = next(item for item in finished["workers"] if item["id"] == worker["id"])
            self._git(self.source, "show-ref", "--verify", "refs/heads/" + accepted["branch"])

    def test_worktree_output_queue_drains_eight_tasks_at_explicit_capacity_three(self) -> None:
        self._exercise_worktree_output_queue(
            run_name="worktree-queue-eight-cap-three", task_count=8,
            capacity=3, expected_capacity=3,
        )

    def test_worktree_output_queue_defaults_to_five_for_eleven_tasks(self) -> None:
        self._exercise_worktree_output_queue(
            run_name="worktree-queue-eleven-default-capacity", task_count=11,
            capacity=None, expected_capacity=5,
        )

    def _drain_queue(self, run: Path, initial: list[dict[str, Any]], task_ids: list[str],
                     findings: Mapping[str, str], capacity: int,
                     *, first_order: list[dict[str, Any]] | None = None) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        scheduled = list(initial)
        scheduled_ids = [launch["task"] for launch in scheduled]
        attempts = [launch["attempt"] for launch in scheduled]
        self.assertEqual({path.stem for path in (run / "prepared").glob("*.json")}, set(attempts))
        self.assertEqual(len(scheduled_ids), len(set(scheduled_ids)), scheduled_ids)
        self.assertEqual(len(attempts), len(set(attempts)), attempts)
        active = {launch["attempt"]: launch for launch in scheduled}
        self.assertEqual(self._active_attempts(run, capacity), set(active))
        queue = list(first_order or initial)
        records: dict[str, dict[str, Any]] = {}

        while queue:
            launch = queue.pop(0)
            task_id = launch["task"]
            self.assertNotIn(task_id, records)
            records[task_id] = self._accept_finding(run, launch, findings[task_id])
            active.pop(launch["attempt"])

            response = self._dispatch(run)
            pending = set(task_ids) - set(scheduled_ids)
            expected_new = min(capacity - len(active), len(pending))
            new_launches = response.get("launches", [])
            self.assertEqual(len(new_launches), expected_new, response)
            self.assertEqual(response.get("status"),
                             "LAUNCH_REQUIRED" if expected_new else "NO_NEW_LAUNCH", response)
            for new in new_launches:
                self.assertNotIn(new["task"], scheduled_ids, new)
                self.assertNotIn(new["attempt"], attempts, new)
                scheduled_ids.append(new["task"])
                attempts.append(new["attempt"])
                scheduled.append(new)
                active[new["attempt"]] = new
                queue.append(new)
            self.assertLessEqual(len(active), capacity, active)
            self.assertEqual(self._active_attempts(run, capacity), set(active))
            self.assertEqual({path.stem for path in (run / "prepared").glob("*.json")}, set(attempts),
                             "Only yielded queue items may have prepared worker contexts")

        self.assertEqual(set(scheduled_ids), set(task_ids))
        self.assertEqual(len(scheduled_ids), len(task_ids))
        self.assertEqual(active, {})
        self.assertEqual(len(records), len(task_ids))
        self.assertEqual(self._dispatch(run).get("status"), "NO_NEW_LAUNCH")
        return records, scheduled

    def test_distinct_queue_items_require_distinct_native_handles(self) -> None:
        run = self._new_run(self._tasks("fresh-context", 2), "fresh-contexts", capacity=2)
        first, second = self._dispatch(run)["launches"]
        handle = self._confirm_launch(run, first)
        before = self._harness("status", "--run", str(run))["active"]
        # Replaying a known registration is safe; assigning its context to another item is not.
        self._harness("launched", "--run", str(run), "--attempt", first["attempt"], "--handle", handle)
        refused = self._harness("launched", "--run", str(run), "--attempt", second["attempt"],
                                "--handle", handle, success=False)
        self.assertEqual(refused["code"], "HELPER_FAILED")
        self.assertIn("fresh native handle", refused["observed"]["diagnostic"])
        self.assertEqual(self._harness("status", "--run", str(run))["active"], before)
        self.assertTrue(all(Path(path).is_file() for path in refused["evidence"]))
        self.assertNotEqual(self._confirm_launch(run, second), handle)
        self.assertEqual(self._active_attempts(run, 2), {first["attempt"], second["attempt"]})

    def test_small_omitted_capacity_and_current_edit_serialization(self) -> None:
        small_tasks = self._tasks("small", 2)
        small_run = self._new_run(small_tasks, "default-cap-small")
        small_meta = json.loads((small_run / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(small_meta["request"]["capacity"], 2)
        small_launches = self._dispatch(small_run)["launches"]
        self.assertEqual(len(small_launches), 2, small_launches)
        self.assertEqual(self._active_attempts(small_run, 2),
                         {launch["attempt"] for launch in small_launches})

        edit_tasks = [
            self._task("edit-one", write_set=["one.txt"]),
            self._task("edit-two", write_set=["two.txt"]),
        ]
        edit_request = self._request(
            edit_tasks, workspace="current", mode="edit", capacity=5,
            checks=[[sys.executable, "-c", "print('offline current edit capacity check')"]],
        )
        edit_run = self._init(edit_request, "current-edit-still-serial")
        edit_meta = json.loads((edit_run / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(edit_meta["request"]["capacity"], 1)
        self.assertEqual(edit_meta["warnings"][0]["code"], "CURRENT_EDIT_SERIALIZED")
        self.assertEqual(len(self._dispatch(edit_run)["launches"]), 1)

    def test_current_edit_queue_stays_serial_and_validates_all_three_outputs(self) -> None:
        tasks = [self._task(f"current-edit-{number}", write_set=[f"contributions/current-{number}.txt"])
                 for number in range(1, 4)]
        task_ids = [task["id"] for task in tasks]
        findings = self._expected_findings(task_ids)
        expected_files = {
            f"contributions/current-{number}.txt": f"current-edit-{number}\n"
            for number in range(1, 4)
        }
        check_code = (
            "from pathlib import Path; expected = " + repr(expected_files) +
            "; assert all(Path(path).read_text(encoding='utf-8') == content "
            "for path, content in expected.items()); print('all current edit contributions verified')"
        )
        request = self._request(
            tasks, workspace="current", mode="edit", capacity=3,
            checks=[[sys.executable, "-c", check_code]],
        )
        run = self._init(request, "current-edit-queue-three")
        metadata = json.loads((run / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["request"]["capacity"], 1)
        self.assertEqual(metadata["warnings"][0]["code"], "CURRENT_EDIT_SERIALIZED")
        initial = self._dispatch(run)["launches"]
        self.assertEqual(len(initial), 1, initial)
        head_before = self._git(self.source, "rev-parse", "HEAD").stdout.strip()
        index_before = self._git_snapshot(self.source)

        launches = list(initial)
        attempts: set[str] = set()
        records: dict[str, dict[str, Any]] = {}
        launch = initial[0]
        while True:
            self.assertNotIn(launch["attempt"], attempts)
            attempts.add(launch["attempt"])
            task_id = launch["task"]
            self.assertNotIn(task_id, records)
            path = f"contributions/current-{task_id.rsplit('-', 1)[1]}.txt"
            records[task_id] = self._accept_finding(
                run, launch, findings[task_id], edits={path: f"{task_id}\n"},
            )
            self.assertEqual(self._active_attempts(run, 1), set())
            self.assertEqual(self._git(self.source, "rev-parse", "HEAD").stdout.strip(), head_before)
            self.assertEqual(self._git(self.source, "diff", "--cached", "--binary").stdout,
                             index_before["cached_diff"])
            self.assertEqual((self.source / path).read_text(encoding="utf-8"), f"{task_id}\n")

            if len(records) == len(task_ids):
                break
            response = self._dispatch(run)
            next_launches = response.get("launches", [])
            self.assertEqual(response.get("status"), "LAUNCH_REQUIRED", response)
            self.assertEqual(len(next_launches), 1, response)
            launch = next_launches[0]
            self.assertNotIn(launch["task"], {item["task"] for item in launches})
            self.assertNotIn(launch["attempt"], attempts)
            launches.append(launch)
            self.assertEqual(self._active_attempts(run, 1), {launch["attempt"]})

        self.assertEqual({launch["task"] for launch in launches}, set(task_ids))
        self.assertEqual(len(attempts), 3)
        self.assertEqual(self._dispatch(run).get("status"), "NO_NEW_LAUNCH")
        finished = self._harness("finish", "--run", str(run))
        self._assert_final_aggregate(
            finished, task_ids, findings, records, integration="current-workspace-validated",
        )
        self.assertEqual(set(finished["integration"]["applied_paths"]), {
            f"contributions/current-{number}.txt" for number in range(1, 4)
        })
        after = self._git_snapshot(self.source)
        for key in ("head", "index_bytes", "index_entries", "cached_diff"):
            self.assertEqual(after[key], index_before[key], key)
        self.assertEqual(self._git(self.source, "log", "-1", "--format=%s").stdout.strip(),
                         "offline fixture baseline")

    def test_worktree_edit_queue_applies_only_after_final_worker_acceptance(self) -> None:
        before = self._make_dirty_parent()
        parent_inputs = {
            name: (self.source / name).read_bytes()
            for name in (".gitignore", ".claspignore", "caller.txt", "caller-note.txt")
        }
        tasks = [self._task(f"worktree-edit-{number}") for number in range(1, 4)]
        task_ids = [task["id"] for task in tasks]
        findings = self._expected_findings(task_ids)
        expected_files = {f"contributions/{task_id}.txt": f"{task_id}\n" for task_id in task_ids}
        check_code = (
            "from pathlib import Path; expected = " + repr(expected_files) +
            "; assert all(Path(path).read_text(encoding='utf-8') == content "
            "for path, content in expected.items()); print('all worktree contributions verified')"
        )
        run = self._init(self._request(
            tasks, workspace="worktree", mode="edit", capacity=2, integration="apply",
            checks=[[sys.executable, "-c", check_code]],
        ), "worktree-edit-queue-three")
        initial = self._dispatch(run)["launches"]
        self.assertEqual(len(initial), 2, initial)
        self.assertEqual({launch["task"] for launch in initial}, set(task_ids[:2]))
        self.assertEqual(self._active_attempts(run, 2), {launch["attempt"] for launch in initial})
        launches = list(initial)
        records: dict[str, dict[str, Any]] = {}

        first = initial[0]
        first_path = f"contributions/{first['task']}.txt"
        records[first["task"]] = self._accept_finding(
            run, first, findings[first["task"]], edits={first_path: f"{first['task']}\n"}, commit=True,
        )
        self.assertEqual(self._git_snapshot(self.source), before)

        refill = self._dispatch(run)
        self.assertEqual(refill.get("status"), "LAUNCH_REQUIRED", refill)
        self.assertEqual(len(refill.get("launches", [])), 1, refill)
        third = refill["launches"][0]
        self.assertEqual(third["task"], task_ids[2])
        self.assertNotIn(third["attempt"], {launch["attempt"] for launch in launches})
        launches.append(third)
        self.assertEqual(self._active_attempts(run, 2), {
            initial[1]["attempt"], third["attempt"],
        })

        second = initial[1]
        second_path = f"contributions/{second['task']}.txt"
        records[second["task"]] = self._accept_finding(
            run, second, findings[second["task"]], edits={second_path: f"{second['task']}\n"}, commit=True,
        )
        self.assertEqual(self._git_snapshot(self.source), before)
        self._finish_blocked(run)

        third_path = f"contributions/{third['task']}.txt"
        records[third["task"]] = self._accept_finding(
            run, third, findings[third["task"]], edits={third_path: f"{third['task']}\n"}, commit=True,
        )
        self.assertEqual(self._dispatch(run).get("status"), "NO_NEW_LAUNCH")
        finished = self._harness("finish", "--run", str(run))
        self._assert_final_aggregate(finished, task_ids, findings, records, integration="applied")
        self.assertEqual(finished.get("cleanup_status"), "complete", finished)
        expected_paths = {f"contributions/{task_id}.txt" for task_id in task_ids}
        self.assertEqual(set(finished["integration"]["applied_paths"]), expected_paths)
        self.assertTrue(finished["integration"]["postcondition"]["head_and_index_preserved"])
        self.assertTrue(finished["integration"]["postcondition"]["worker_files_match"])
        for task_id in task_ids:
            self.assertEqual((self.source / f"contributions/{task_id}.txt").read_text(encoding="utf-8"),
                             f"{task_id}\n")
        for name, contents in parent_inputs.items():
            self.assertEqual((self.source / name).read_bytes(), contents, name)
        after = self._git_snapshot(self.source)
        for key in ("head", "index_bytes", "index_entries", "cached_diff"):
            self.assertEqual(after[key], before[key], key)
        self.assertIn("caller-note.txt", after["status"])

        committed_workers = finished["integration"].get("workers")
        self.assertIsInstance(committed_workers, list, finished["integration"])
        self.assertEqual({worker["id"] for worker in committed_workers}, set(task_ids))
        launch_by_task = {launch["task"]: launch for launch in launches}
        for worker in committed_workers:
            commits = worker.get("commits")
            self.assertTrue(commits, worker)
            worker_root = Path(launch_by_task[worker["id"]]["cwd"])
            self.assertFalse(worker_root.exists(), worker)
            registered = self._git(self.source, "worktree", "list", "--porcelain").stdout.splitlines()
            self.assertNotIn("worktree " + str(worker_root), registered)
            for commit in commits:
                self.assertIn(commit, finished["retained_locations"])
                self._git(self.source, "cat-file", "-e", f"{commit}^{{commit}}")
            accepted = next(item for item in finished["workers"] if item["id"] == worker["id"])
            self._git(self.source, "show-ref", "--verify", "refs/heads/" + accepted["branch"])

    def test_omitted_capacity_defaults_to_five_for_seven_tasks(self) -> None:
        tasks = [self._task(f"review-{number}", write_set=[]) for number in range(1, 8)]
        request = self._request(tasks, workspace="current", mode="report-only")
        self.assertNotIn("capacity", request)

        run = self._init(request, "default-cap-seven")
        self.assertEqual(list((run / "prepared").glob("*.json")), [],
                         "Planning the full backlog must not eagerly prepare every worker")
        launches = self._dispatch(run)["launches"]
        self.assertEqual(len(launches), 5, launches)
        metadata = json.loads((run / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["request"]["capacity"], 5, metadata["request"])
        self.assertEqual(len({launch["task"] for launch in launches}), 5, launches)
        self.assertEqual(len({launch["attempt"] for launch in launches}), 5, launches)
        self.assertEqual(self._active_attempts(run, 5), {launch["attempt"] for launch in launches})
        self._finish_blocked(run)

        task_ids = [task["id"] for task in tasks]
        findings = self._expected_findings(task_ids)
        records, _scheduled = self._drain_queue(
            run, launches, task_ids, findings, 5, first_order=list(reversed(launches)),
        )
        finished = self._harness("finish", "--run", str(run))
        self._assert_final_aggregate(finished, task_ids, findings, records)

    def test_explicit_capacities_two_and_five_drain_all_seven_tasks(self) -> None:
        for capacity in (2, 5):
            with self.subTest(capacity=capacity):
                tasks = self._tasks(f"explicit-{capacity}", 7)
                task_ids = [task["id"] for task in tasks]
                findings = self._expected_findings(task_ids)
                run = self._new_run(tasks, f"explicit-cap-{capacity}", capacity=capacity)
                metadata = json.loads((run / "run.json").read_text(encoding="utf-8"))
                self.assertEqual(metadata["request"]["capacity"], capacity)
                initial = self._dispatch(run)["launches"]
                self.assertEqual(len(initial), capacity, initial)
                records, _scheduled = self._drain_queue(
                    run, initial, task_ids, findings, capacity,
                )
                finished = self._harness("finish", "--run", str(run))
                self._assert_final_aggregate(finished, task_ids, findings, records)

    def test_rejected_task_advances_queue_and_requires_confirmed_stop_retry(self) -> None:
        tasks = self._tasks("retry", 5)
        task_ids = [task["id"] for task in tasks]
        findings = self._expected_findings(task_ids)
        failed_finding = "failed::retry attempt must not enter the final aggregate"
        run = self._new_run(tasks, "rejected-task-queue", capacity=2)
        initial = self._dispatch(run)["launches"]
        self.assertEqual(len(initial), 2, initial)
        failed_launch, peer_launch = initial
        self._reject_finding(run, failed_launch, failed_finding)
        accepted_records = {
            peer_launch["task"]: self._accept_finding(run, peer_launch, findings[peer_launch["task"]]),
        }
        self._finish_blocked(run)

        scheduled = list(initial)
        scheduled_ids = [launch["task"] for launch in scheduled]
        attempts = [launch["attempt"] for launch in scheduled]
        active = {}
        pending = set(task_ids) - set(scheduled_ids) - {failed_launch["task"]}
        first_response = self._dispatch(run)
        first_wave = first_response.get("launches", [])
        self.assertEqual(len(first_wave), 2, first_response)
        self.assertEqual(first_response.get("status"), "LAUNCH_REQUIRED", first_response)
        self.assertNotIn(failed_launch["task"], {launch["task"] for launch in first_wave})
        for launch in first_wave:
            self.assertNotIn(launch["task"], scheduled_ids, launch)
            self.assertNotIn(launch["attempt"], attempts, launch)
            scheduled.append(launch)
            scheduled_ids.append(launch["task"])
            attempts.append(launch["attempt"])
            active[launch["attempt"]] = launch

        queue = list(first_wave)
        while queue:
            launch = queue.pop(0)
            accepted_records[launch["task"]] = self._accept_finding(
                run, launch, findings[launch["task"]],
            )
            active.pop(launch["attempt"])
            pending = set(task_ids) - set(scheduled_ids) - {failed_launch["task"]}
            response = self._dispatch(run)
            new_launches = response.get("launches", [])
            expected_new = min(2 - len(active), len(pending))
            self.assertEqual(len(new_launches), expected_new, response)
            self.assertEqual(response.get("status"),
                             "LAUNCH_REQUIRED" if expected_new else "NO_NEW_LAUNCH", response)
            for new in new_launches:
                self.assertNotIn(new["task"], scheduled_ids, new)
                self.assertNotIn(new["attempt"], attempts, new)
                scheduled.append(new)
                scheduled_ids.append(new["task"])
                attempts.append(new["attempt"])
                active[new["attempt"]] = new
                queue.append(new)
            self.assertLessEqual(len(active), 2, active)
            self.assertEqual(self._active_attempts(run, 2), set(active))

        self.assertEqual(set(scheduled_ids), set(task_ids))
        self.assertEqual(len(scheduled_ids), 5)
        self.assertEqual(active, {})
        self.assertEqual(set(accepted_records), set(task_ids) - {failed_launch["task"]})
        self._finish_blocked(run)

        retry = self._harness(
            "retry", "--run", str(run), "--attempt", failed_launch["attempt"],
            "--reason", "Offline fixture replaces the terminal failed result with a successful one.",
            "--confirmed-stopped",
        )
        self.assertEqual(retry.get("status"), "RECORDED_STATUS", retry)
        replacement = self._dispatch(run)["launches"]
        self.assertEqual(len(replacement), 1, replacement)
        replacement_launch = replacement[0]
        self.assertEqual(replacement_launch["task"], failed_launch["task"])
        self.assertNotEqual(replacement_launch["attempt"], failed_launch["attempt"])
        self.assertNotIn(replacement_launch["attempt"], attempts)
        scheduled_ids.append(replacement_launch["task"])
        attempts.append(replacement_launch["attempt"])
        self._finish_blocked(run)

        accepted_records[replacement_launch["task"]] = self._accept_finding(
            run, replacement_launch, findings[replacement_launch["task"]],
        )
        self.assertEqual(self._dispatch(run).get("status"), "NO_NEW_LAUNCH")
        finished = self._harness("finish", "--run", str(run))
        self._assert_final_aggregate(finished, task_ids, findings, accepted_records)
        self.assertEqual(len(scheduled_ids), 6)
        self.assertEqual(scheduled_ids.count(failed_launch["task"]), 2)
        self.assertTrue(all(scheduled_ids.count(task_id) == 1
                            for task_id in set(task_ids) - {failed_launch["task"]}), scheduled_ids)
        self.assertEqual(len(attempts), len(set(attempts)), attempts)
        final_worker = next(worker for worker in finished["workers"]
                            if worker["id"] == failed_launch["task"])
        self.assertEqual(final_worker["summary"],
                         f"[OFFLINE SIMULATED NATIVE RESULT] {findings[failed_launch['task']]}")
        self.assertEqual(len(finished["workers"]), 5)

    def test_uncertain_launch_holds_capacity_while_other_tasks_drain(self) -> None:
        tasks = self._tasks("uncertain", 5)
        task_ids = [task["id"] for task in tasks]
        findings = self._expected_findings(task_ids)
        run = self._new_run(tasks, "uncertain-launch-capacity", capacity=2)
        initial = self._dispatch(run)["launches"]
        self.assertEqual(len(initial), 2, initial)
        uncertain, first_confirmed = initial
        self.assertEqual(self._active_attempts(run, 2),
                         {uncertain["attempt"], first_confirmed["attempt"]})

        scheduled = list(initial)
        scheduled_ids = [launch["task"] for launch in scheduled]
        attempts = [launch["attempt"] for launch in scheduled]
        active = {uncertain["attempt"]: uncertain, first_confirmed["attempt"]: first_confirmed}
        queue = [first_confirmed]
        records: dict[str, dict[str, Any]] = {}
        while queue:
            launch = queue.pop(0)
            records[launch["task"]] = self._accept_finding(
                run, launch, findings[launch["task"]],
            )
            active.pop(launch["attempt"])
            pending = set(task_ids) - set(scheduled_ids)
            response = self._dispatch(run)
            new_launches = response.get("launches", [])
            expected_new = min(2 - len(active), len(pending))
            self.assertEqual(len(new_launches), expected_new, response)
            self.assertEqual(response.get("status"),
                             "LAUNCH_REQUIRED" if expected_new else "NO_NEW_LAUNCH", response)
            for new in new_launches:
                self.assertNotIn(new["task"], scheduled_ids, new)
                self.assertNotIn(new["attempt"], attempts, new)
                scheduled.append(new)
                scheduled_ids.append(new["task"])
                attempts.append(new["attempt"])
                active[new["attempt"]] = new
                queue.append(new)
            self.assertLessEqual(len(active), 2, active)
            self.assertIn(uncertain["attempt"], active)
            self.assertEqual(self._active_attempts(run, 2), set(active))

        self.assertEqual(set(scheduled_ids), set(task_ids))
        self.assertEqual(len(scheduled_ids), len(task_ids))
        self.assertEqual(len(attempts), len(set(attempts)))
        self.assertEqual(set(records), set(task_ids) - {uncertain["task"]})
        self.assertEqual(active, {uncertain["attempt"]: uncertain})
        self.assertEqual(self._dispatch(run).get("status"), "NO_NEW_LAUNCH")
        blocked_retry = self._harness(
            "retry", "--run", str(run), "--attempt", uncertain["attempt"],
            "--reason", "An uncertain launch has no collected terminal evidence.",
            "--confirmed-stopped", success=False,
        )
        self.assertEqual(blocked_retry.get("code"), "RETRY_NOT_READY", blocked_retry)
        self.assertEqual(self._active_attempts(run, 2), {uncertain["attempt"]})
        self._finish_blocked(run)


if __name__ == "__main__":
    unittest.main(verbosity=2)
