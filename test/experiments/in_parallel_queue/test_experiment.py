"""Offline simulated checks for the prompt-led queue apparatus (not live proof)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


EXPERIMENT_PATH = Path(__file__).with_name("experiment.py")
SPEC = importlib.util.spec_from_file_location("in_parallel_queue_experiment", EXPERIMENT_PATH)
experiment = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(experiment)


def _json_new(path: Path, value: object) -> str:
    data = experiment._json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return experiment._sha(data)


def _utc(seconds: int) -> str:
    base = datetime(2026, 10, 1, tzinfo=timezone.utc)
    return (base + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


def _record(kind: str, payload: dict, second: int) -> dict:
    return {"timestamp": _utc(second), "type": kind, "payload": payload}


def _rollout(path: Path, count: int = 3, schedule: str = "bounded",
             fork_turns: str = "none", mismatch: str | None = None,
             followup: bool = False) -> None:
    root, turn = "coordinator-thread", "coordinator-turn"
    rows = [_record("event_msg", {"type": "task_started", "thread_id": root,
                                   "turn_id": turn}, 0)]
    children = [f"10000000-0000-0000-0000-{i:012d}" for i in range(1, count + 1)]
    calls = [f"spawn-call-{i}" for i in range(count)]
    for index, (call_id, child_id) in enumerate(zip(calls, children), 1):
        args = {"task_name": f"worker-{index}", "fork_turns": fork_turns,
                "message": "opaque-argument-must-not-be-retained"}
        rows.append(_record("response_item", {
            "type": "function_call", "namespace": "collaboration", "name": "spawn_agent",
            "call_id": call_id, "arguments": json.dumps(args),
        }, index))

    def activity(kind: str, index: int, second: int, *, bad: str | None = None) -> None:
        call_id, child_id = calls[index], children[index]
        child_turn = f"20000000-0000-0000-0000-{index + 1:012d}"
        item_id = call_id if kind == "started" else f"subagent-completed-{child_turn}"
        path_value = f"/native/worker-{index + 1}"
        event_child_id = child_id
        if bad == "id":
            item_id = "not-the-spawn-call" if kind == "started" else "not-the-child-completion"
        if bad == "path":
            path_value += "-changed"
        if bad == "child":
            event_child_id = f"unexpected-child-thread-{index + 1}"
        item = {"type": "SubAgentActivity", "kind": kind, "id": item_id,
                "agent_thread_id": event_child_id, "agent_path": path_value}
        rows.append(_record("event_msg", {"type": "item_completed", "thread_id": root,
                                           "turn_id": turn, "item": item}, second))

    if schedule == "overlap":
        for i in range(count):
            activity("started", i, 5 + i)
        for i in range(count):
            activity("completed", i, 10 + i)
    else:
        activity("started", 0, 5)
        activity("started", 1, 6)
        activity("completed", 0, 8)
        activity("started", 2, 8)  # Completion is recorded first at this exact tie.
        activity("completed", 1, 10)
        if mismatch:
            activity("completed", 2, 12, bad=mismatch)
        elif schedule != "missing":
            activity("completed", 2, 12)
    if followup:
        rows.append(_record("response_item", {
            "type": "function_call", "namespace": "collaboration", "name": "followup_task",
            "call_id": "followup-call", "arguments": "{}",
        }, 13))
    rows.append(_record("event_msg", {"type": "item_completed", "thread_id": root,
                                       "turn_id": turn, "item": {"type": "AgentMessage",
                                       "phase": "final_answer", "id": "final-answer"}}, 14))
    rows.append(_record("event_msg", {"type": "task_complete", "thread_id": root,
                                       "turn_id": turn, "root_turn_id": turn}, 15))
    path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
                    encoding="utf-8")


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="in-parallel-queue-prepare-")
        self.root = Path(self.temp.name)
        self.skills = experiment.APPARATUS_REPO / "skills"

    def tearDown(self):
        self.temp.cleanup()

    def test_omitted_capacity_normalizes_to_five_and_keeps_oracle_external(self):
        case_dir = self.root / "default-five"
        result = experiment.prepare_case(str(case_dir), str(self.skills), 7, None)
        self.assertEqual(result["expected_capacity"], 5)
        case = experiment._read_json(case_dir / "case.json")
        prompt = (case_dir / "prompt.txt").read_text(encoding="utf-8")
        self.assertEqual(case["configuration"]["effective_capacity"], 5)
        self.assertEqual(case["configuration"]["result_evidence_role"], "coordinator-response")
        self.assertIn("Omit capacity entirely", prompt)
        self.assertIn("result_evidence_role=coordinator-response", prompt)
        self.assertIn("normalized effective capacity as 5", prompt)
        self.assertNotIn("7 * value +", prompt)
        self.assertFalse((case_dir / "fixture" / "expected.json").exists())
        self.assertTrue((case_dir / "expected.json").is_file())
        self.assertNotEqual((case_dir / "expected.json").parent, case_dir / "fixture")

    def test_explicit_capacity_is_honored_and_existing_case_is_rejected(self):
        case_dir = self.root / "explicit-two"
        result = experiment.prepare_case(str(case_dir), str(self.skills), 7, 2)
        self.assertEqual(result["expected_capacity"], 2)
        self.assertIn("Request at most 2 concurrent workers", (case_dir / "prompt.txt").read_text())
        with self.assertRaises(experiment.ExperimentError):
            experiment.prepare_case(str(case_dir), str(self.skills), 7, 2)

    def test_capacity_at_or_above_task_count_does_not_claim_a_queue_trial(self):
        with self.assertRaisesRegex(experiment.ExperimentError, "must exceed effective worker capacity"):
            experiment.prepare_case(str(self.root / "not-queued"), str(self.skills), 5, 5)

    def test_legacy_case_role_is_resolved_only_from_its_hash_pinned_prompt(self):
        case_dir = self.root / "legacy-dispatcher-contract"
        experiment.prepare_case(str(case_dir), str(self.skills), 3, 2)
        case_path = case_dir / "case.json"
        case_path.chmod(0o644)
        case = experiment._read_json(case_path)
        case["configuration"].pop("result_evidence_role")
        legacy_prompt = (
            '"raw_result_path": "/absolute/harness-run-root/dispatcher/artifacts/'
            'actual-attempt-id/result.json"\n'
            "under this harness run root, and point `raw_result_path` at the actual\n"
            "`dispatcher/artifacts/<attempt>/result.json`."
        )
        prompt_path = case_dir / "prompt.txt"
        prompt_path.write_text(legacy_prompt, encoding="utf-8")
        case["prompt_sha256"] = experiment._sha(legacy_prompt.encode("utf-8"))
        case.pop("integrity_sha256")
        case["integrity_sha256"] = experiment._sha(experiment._canonical(case))
        case_path.write_bytes(experiment._json_bytes(case))
        case_path.chmod(0o444)

        _, _, values = experiment._verify_case(case_dir)
        self.assertEqual(values["result_evidence_role"], "dispatcher-artifact")
        self.assertEqual(values["result_evidence_role_source"], "hash-verified prompt.txt")

    def test_legacy_raw_response_prompt_resolves_and_ambiguous_or_invalid_roles_fail(self):
        response_prompt = (
            '"raw_result_path": "/absolute/coordinator/raw-results/module-01.json"\n'
            "Retain the actual worker responses under\n`coordinator/raw-results/`"
        )
        self.assertEqual(experiment._resolve_result_evidence_role({}, response_prompt),
                         ("coordinator-response", "hash-verified prompt.txt"))
        dispatcher_prompt = (
            '"raw_result_path": "/absolute/harness-run-root/dispatcher/artifacts/'
            'actual-attempt-id/result.json"\n'
            "under this harness run root, and point `raw_result_path` at the actual\n"
            "`dispatcher/artifacts/<attempt>/result.json`."
        )
        with self.assertRaisesRegex(experiment.ExperimentError, "ambiguous"):
            experiment._resolve_result_evidence_role({}, response_prompt + "\n" + dispatcher_prompt)
        with self.assertRaisesRegex(experiment.ExperimentError, "known result evidence contract"):
            experiment._resolve_result_evidence_role({}, "an unrelated prompt")
        with self.assertRaisesRegex(experiment.ExperimentError, "must be 'coordinator-response'"):
            experiment._resolve_result_evidence_role(
                {"result_evidence_role": "dispatcher-artifact"}, dispatcher_prompt)


class AuditScopeTests(unittest.TestCase):
    def test_failed_audit_still_reports_blinding_and_git_metadata_limits(self):
        with tempfile.TemporaryDirectory(prefix="in-parallel-queue-scope-") as temp:
            root = Path(temp)
            output = root / "audit.json"
            result = experiment.audit_case(str(root / "missing-case"),
                                           str(root / "missing-rollout.jsonl"),
                                           str(root / "missing-aggregate.json"),
                                           str(output))
            self.assertEqual(result["status"], "FAIL")
            self.assertFalse(result["proof_scope"]["oracle"]["access_restricted"])
            self.assertFalse(result["proof_scope"]["oracle"]["non_reading_proven"])
            self.assertFalse(result["proof_scope"]["fixture_git"]["all_git_metadata_checked"])
            self.assertFalse(result["proof_scope"]["native_overlap"]["cpu_parallelism_proven"])
            self.assertEqual(json.loads(output.read_text())["proof_scope"], result["proof_scope"])


class NativeRolloutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="in-parallel-queue-trace-")
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _audit_error(self, name: str, **kwargs) -> str:
        path = self.root / f"{name}.jsonl"
        _rollout(path, **kwargs)
        with self.assertRaises(experiment.ExperimentError) as caught:
            experiment.audit_native_rollout(str(path), 3, 2)
        return str(caught.exception)

    def test_valid_refill_wave_proves_two_worker_peak_and_opaque_spawn_messages_are_not_retained(self):
        path = self.root / "bounded.jsonl"
        _rollout(path)
        result = experiment.audit_native_rollout(str(path), 3, 2)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["peak_active_children"], 2)
        self.assertEqual(result["native_child_count"], 3)
        self.assertTrue(all(child["fork_turns"] == "none" for child in result["children"]))
        first = result["children"][0]
        self.assertNotEqual(first["agent_thread_id"],
                            first["completion_event_id"].removeprefix("subagent-completed-"))
        self.assertNotIn("opaque-argument-must-not-be-retained", json.dumps(result))

    def test_over_capacity_wave_is_rejected(self):
        self.assertIn("exceeds expected capacity", self._audit_error("overlap", schedule="overlap"))

    def test_equal_timestamps_preserve_recorded_start_before_completion(self):
        path = self.root / "same-timestamp-overlap.jsonl"
        _rollout(path)
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        tied = [index for index, row in enumerate(rows) if row["timestamp"] == _utc(8)]
        self.assertEqual(len(tied), 2)
        # Start the third context while both prior contexts still occupy slots.
        # Reversing these records must not be hidden by completion-first sorting.
        rows[tied[0]], rows[tied[1]] = rows[tied[1]], rows[tied[0]]
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        with self.assertRaisesRegex(experiment.ExperimentError, "observed native peak 3 exceeds expected capacity 2"):
            experiment.audit_native_rollout(str(path), 3, 2)

    def test_missing_completion_is_rejected(self):
        self.assertIn("typed native completed events", self._audit_error("missing", schedule="missing"))

    def test_native_child_handle_does_not_override_wrong_coordinator_or_turn_identity(self):
        cases = [
            ("wrong-parent", "started", "thread_id", "foreign-coordinator",
             "expected one coordinator payload.thread_id"),
            ("wrong-turn", "completed", "turn_id", "foreign-turn",
             "expected one coordinator payload.turn_id"),
        ]
        for name, kind, field, value, expected_error in cases:
            with self.subTest(identity=field), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / f"{name}.jsonl"
                _rollout(path)
                rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                event = next(row for row in rows
                             if row.get("type") == "event_msg"
                             and row.get("payload", {}).get("type") == "item_completed"
                             and row["payload"].get("item", {}).get("type") == "SubAgentActivity"
                             and row["payload"]["item"].get("kind") == kind
                             and row["payload"]["item"].get("agent_thread_id")
                             == "10000000-0000-0000-0000-000000000001")
                self.assertEqual(event["payload"]["item"]["agent_thread_id"],
                                 "10000000-0000-0000-0000-000000000001")
                event["payload"][field] = value
                path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
                                encoding="utf-8")
                with self.assertRaises(experiment.ExperimentError) as caught:
                    experiment.audit_native_rollout(str(path), 3, 2)
                self.assertIn(expected_error, str(caught.exception))

    def test_duplicate_completion_cannot_mask_another_child_missing_completion(self):
        path = self.root / "duplicate-masks-missing.jsonl"
        _rollout(path)
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        completed = [row for row in rows
                     if row.get("type") == "event_msg"
                     and row.get("payload", {}).get("type") == "item_completed"
                     and row["payload"].get("item", {}).get("type") == "SubAgentActivity"
                     and row["payload"]["item"].get("kind") == "completed"]
        missing = next(row for row in completed
                       if row["payload"]["item"]["agent_thread_id"]
                       == "10000000-0000-0000-0000-000000000002")
        duplicate = next(row for row in completed
                         if row["payload"]["item"]["agent_thread_id"]
                         == "10000000-0000-0000-0000-000000000001")
        rows.remove(missing)
        rows.insert(rows.index(duplicate) + 1, json.loads(json.dumps(duplicate)))
        path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
                        encoding="utf-8")

        with self.assertRaises(experiment.ExperimentError) as caught:
            experiment.audit_native_rollout(str(path), 3, 2)
        error = str(caught.exception)
        self.assertIn("native child thread completed more than once", error)
        self.assertIn("missing completions=", error)
        self.assertIn("10000000-0000-0000-0000-000000000002", error)

    def test_mismatched_lifecycle_join_is_rejected(self):
        self.assertIn("path changed across lifecycle", self._audit_error("join", mismatch="path"))
        self.assertIn("start/completion IDs do not join",
                      self._audit_error("child-id", mismatch="child"))

    def test_nonfresh_spawn_and_followup_are_rejected(self):
        self.assertIn("fork_turns to none", self._audit_error("forked", fork_turns="all"))
        self.assertIn("followup_task/resume", self._audit_error("followup", followup=True))


class AggregateArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="in-parallel-queue-aggregate-")
        cls.root = Path(cls.temp.name)
        cls.case_dir = cls.root / "prepared"
        cls.skills = experiment.APPARATUS_REPO / "skills"
        experiment.prepare_case(str(cls.case_dir), str(cls.skills), 3, 2)
        cls.case, cls.expected, values = experiment._verify_case(cls.case_dir)
        cls.repo_root = Path(values["source"]["repository_root"])
        cls.fixture_root = Path(values["source"]["fixture_root"])
        cls.capacity = 2
        cls.result_evidence_role = values["result_evidence_role"]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def _build_aggregate(self, suffix: str = "valid") -> tuple[dict, list[dict], Path]:
        run_root = self.root / f"harness-{suffix}"
        coordinator_root = self.root / f"coordinator-{suffix}"
        for sub in ("packets", "collected", "verified", "dispatcher/inbox"):
            (run_root / sub).mkdir(parents=True, exist_ok=True)
        for sub in ("diagnostics", "raw-results", "verification-notes"):
            (coordinator_root / sub).mkdir(parents=True, exist_ok=True)
        task_ids = [f"inspect-{i}-arbitrary-id" for i in range(1, 4)]
        native_handles = [f"/native/fresh-worker-{i}" for i in range(1, 4)]
        attempts = [f"attempt-{i}" for i in range(1, 4)]
        request_tasks = []
        worker_manifest = []
        rows = []
        for index, expected in enumerate(self.expected["modules"], 1):
            task_id, handle, attempt = task_ids[index - 1], native_handles[index - 1], attempts[index - 1]
            module = expected["module"]
            request_tasks.append({"id": task_id, "objective": f"Inspect {module} and report its formula.", "write_set": []})
            packet = {"schema": "ask-agent.task.binding.v1", "status": "READY_TO_LAUNCH",
                      "task": {"mode": "report-only", "objective": f"Inspect {module} and report its formula."},
                      "workspace": {"route": "current", "root": str(self.fixture_root)}}
            packet_path = run_root / "packets" / f"{attempt}.json"
            packet_sha = _json_new(packet_path, packet)
            collected = {
                "result": {"status": "SUCCEEDED", "native_handle": handle,
                           "native_terminal": True},
                "verified": {
                    "status": "READY_FOR_PARENT_ACCEPTANCE",
                    "workspace_evidence": {
                        "status": "ok", "verdict": "unchanged", "head_moved": False,
                        "root": str(self.fixture_root),
                    },
                },
            }
            collected_path = run_root / "collected" / f"{attempt}.json"
            collected_sha = _json_new(collected_path, collected)
            raw_path = run_root / "dispatcher" / "artifacts" / attempt / "result.json"
            dispatcher_result = {"status": "SUCCEEDED", "native_handle": handle,
                                 "native_terminal": True}
            dispatcher_result_sha = _json_new(raw_path, dispatcher_result)
            inbox = {"attempt": attempt, "step": task_id, "status": "SUCCEEDED",
                     "evidence": {"path": str(raw_path), "sha256": dispatcher_result_sha}}
            _json_new(run_root / "dispatcher" / "inbox" / f"{attempt}.json", inbox)
            raw_worker_path = coordinator_root / "raw-results" / f"{task_id}.json"
            raw_worker_result = {"status": "SUCCEEDED", "native_handle": handle,
                                 "native_terminal": True}
            raw_worker_sha = _json_new(raw_worker_path, raw_worker_result)
            verification_note_path = coordinator_root / "verification-notes" / f"{task_id}.json"
            _json_new(verification_note_path, {
                "task_id": task_id, "attempt_id": attempt, "native_handle": handle,
                "module": module, "inspection": "AST and output evidence checked",
            })
            verified = {
                "passed": True,
                "reason": "Pinned worker output and independent inspection evidence were checked.",
                "evidence": [
                    {"path": str(self.fixture_root / module),
                     "sha256": experiment._sha((self.fixture_root / module).read_bytes())},
                    {"path": str(verification_note_path),
                     "sha256": experiment._sha(verification_note_path.read_bytes())},
                    {"path": str(raw_worker_path), "sha256": raw_worker_sha},
                ],
            }
            verified_path = run_root / "verified" / f"{attempt}.json"
            verified_sha = _json_new(verified_path, verified)
            worker_manifest.append({"id": task_id, "packet_path": str(packet_path),
                                    "packet_sha256": packet_sha, "write_set": []})
            rows.append({
                "task_id": task_id, "attempt_id": attempt, "native_handle": handle,
                "module": module, "a": expected["a"], "b": expected["b"],
                "zero": expected["zero"], "four": expected["four"], "state": "accepted",
                "evidence": {
                    name: {"state": state, "task_id": task_id, "attempt_id": attempt,
                           "native_handle": handle, "locator": str(path), "sha256": digest}
                    for name, state, path, digest in (
                        ("packet", "prepared", packet_path, packet_sha),
                        ("collected", "collected", collected_path, collected_sha),
                        ("verified", "verified", verified_path, verified_sha),
                    )
                },
                "raw_result_path": str(raw_worker_path), "raw_result_sha256": raw_worker_sha,
            })
        run_request = {"capacity": 2, "mode": "report-only", "workspace": "current",
                       "tasks": request_tasks}
        diagnostic_path = coordinator_root / "diagnostics" / "simulated-note.json"
        diagnostic_sha = _json_new(diagnostic_path, {"status": "SIMULATED"})
        _json_new(run_root / "run.json", {"schema": "agent-harness/v1", "request": run_request})
        _json_new(run_root / "result.json", {
            "schema": "agent-harness.delivery.v1", "status": "SUCCEEDED",
            "run": str(run_root.resolve()), "integration": {"application_attempted": False, "applied_paths": []},
            "workers": worker_manifest,
        })
        aggregate = {
            "schema": experiment.AGGREGATE_SCHEMA,
            "request": {"task_count": 3, "capacity": 2, "mode": "report-only",
                        "workspace": "current", "tasks": [
                            {"task_id": task_id, "module": self.expected["modules"][i]["module"]}
                            for i, task_id in enumerate(task_ids)]},
            "run": {"status": "SUCCEEDED", "mode": "report-only", "workspace": "current",
                    "final_run_path": str(run_root.resolve())},
            "tasks": rows,
            "totals": dict(self.expected["totals"]),
            "diagnostics": [{"path": str(diagnostic_path), "sha256": diagnostic_sha,
                             "summary": "Synthetic simulated diagnostic."}],
        }
        children = [{"task_name": f"independent-worker-name-{i}", "agent_path": handle}
                    for i, handle in enumerate(native_handles, 1)]
        return aggregate, children, coordinator_root

    def _pin_dispatcher_artifacts_as_result_evidence(self, aggregate: dict) -> None:
        run_root = Path(aggregate["run"]["final_run_path"])
        for row in aggregate["tasks"]:
            path = run_root / "dispatcher" / "artifacts" / row["attempt_id"] / "result.json"
            row["raw_result_path"] = str(path)
            row["raw_result_sha256"] = experiment._sha(path.read_bytes())

    def test_actual_harness_artifacts_pass_and_task_ids_need_not_match_worker_names(self):
        aggregate, children, coordinator_root = self._build_aggregate()
        result = experiment.validate_aggregate(aggregate, self.expected, self.capacity,
                                              self.result_evidence_role,
                                              self.repo_root, self.fixture_root,
                                              coordinator_root, children)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["accepted_tasks"], 3)
        self.assertEqual(result["result_evidence_role"], "coordinator-response")

    def test_current_contract_rejects_dispatcher_artifact_as_coordinator_response(self):
        aggregate, children, coordinator_root = self._build_aggregate("wrong-role")
        self._pin_dispatcher_artifacts_as_result_evidence(aggregate)
        with self.assertRaisesRegex(experiment.ExperimentError, "must be retained under coordinator/raw-results"):
            experiment.validate_aggregate(aggregate, self.expected, self.capacity,
                                          self.result_evidence_role, self.repo_root,
                                          self.fixture_root, coordinator_root, children)

    def test_hash_resolved_legacy_role_accepts_only_its_dispatcher_artifact(self):
        aggregate, children, coordinator_root = self._build_aggregate("legacy-role")
        self._pin_dispatcher_artifacts_as_result_evidence(aggregate)
        dispatcher_prompt = (
            '"raw_result_path": "/absolute/harness-run-root/dispatcher/artifacts/'
            'actual-attempt-id/result.json"\n'
            "under this harness run root, and point `raw_result_path` at the actual\n"
            "`dispatcher/artifacts/<attempt>/result.json`."
        )
        role, source = experiment._resolve_result_evidence_role({}, dispatcher_prompt)
        self.assertEqual(role, "dispatcher-artifact")
        self.assertEqual(source, "hash-verified prompt.txt")
        result = experiment.validate_aggregate(aggregate, self.expected, self.capacity,
                                              role, self.repo_root, self.fixture_root,
                                              coordinator_root, children)
        self.assertEqual(result["result_evidence_role"], "dispatcher-artifact")
        self.assertTrue(all(row["result_evidence"]["role"] == "dispatcher-artifact"
                            for row in result["tasks"]))

    def test_duplicate_and_omitted_aggregate_tasks_are_rejected(self):
        aggregate, children, coordinator_root = self._build_aggregate("duplicates")
        aggregate["tasks"][1] = dict(aggregate["tasks"][0])
        with self.assertRaisesRegex(experiment.ExperimentError, "duplicate aggregate task_id"):
            experiment.validate_aggregate(aggregate, self.expected, self.capacity,
                                          self.result_evidence_role,
                                          self.repo_root, self.fixture_root,
                                          coordinator_root, children)
        aggregate, children, coordinator_root = self._build_aggregate("omitted")
        aggregate["tasks"].pop()
        with self.assertRaisesRegex(experiment.ExperimentError, "exactly 3 rows"):
            experiment.validate_aggregate(aggregate, self.expected, self.capacity,
                                          self.result_evidence_role,
                                          self.repo_root, self.fixture_root,
                                          coordinator_root, children)

    def test_wrong_totals_are_rejected(self):
        aggregate, children, coordinator_root = self._build_aggregate("wrong-totals")
        aggregate["totals"]["four"] += 1
        with self.assertRaisesRegex(experiment.ExperimentError, "aggregate.totals.four"):
            experiment.validate_aggregate(aggregate, self.expected, self.capacity,
                                          self.result_evidence_role,
                                          self.repo_root, self.fixture_root,
                                          coordinator_root, children)

    def test_claimed_wrapper_cannot_hide_a_failed_actual_verifier(self):
        aggregate, children, coordinator_root = self._build_aggregate("actual-verifier")
        evidence = aggregate["tasks"][0]["evidence"]["verified"]
        path = Path(evidence["locator"])
        actual = json.loads(path.read_text())
        actual["passed"] = False
        evidence["sha256"] = _json_new(path, actual)
        with self.assertRaisesRegex(experiment.ExperimentError, "actual verification artifact did not pass"):
            experiment.validate_aggregate(aggregate, self.expected, self.capacity,
                                          self.result_evidence_role,
                                          self.repo_root, self.fixture_root,
                                          coordinator_root, children)

    def test_source_freshness_detects_fixture_drift(self):
        case_dir = self.root / "freshness-case"
        experiment.prepare_case(str(case_dir), str(self.skills), 3, 2)
        case, _, values = experiment._verify_case(case_dir)
        source = values["source"]
        source_file = Path(source["fixture_root"]) / "modules/module_01.py"
        source_file.write_text(source_file.read_text() + "# drift\n")
        ignored_cache = Path(source["fixture_root"]) / "modules/__pycache__/module_05.cpython-314.pyc"
        ignored_cache.parent.mkdir()
        ignored_cache.write_bytes(b"synthetic ignored cache drift")
        result = experiment._source_check(source)
        self.assertFalse(result["source_files_unchanged"])
        self.assertTrue(result["head_unchanged"])
        self.assertFalse(result["git_status_unchanged"])
        deltas = result["file_deltas"]
        self.assertEqual(deltas["added"][0]["path"], "modules/__pycache__/module_05.cpython-314.pyc")
        self.assertEqual(deltas["added"][0]["observed_sha256"],
                         experiment._sha(b"synthetic ignored cache drift"))
        self.assertEqual(deltas["changed"][0]["path"], "modules/module_01.py")
        self.assertNotEqual(deltas["changed"][0]["expected_sha256"],
                            deltas["changed"][0]["observed_sha256"])


if __name__ == "__main__":
    unittest.main()
