"""Focused tests for host-native Claude trace evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import claude_native_trace as trace


def _dump(path: Path, value) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(payload)
    return payload


def _canonical(value: dict) -> str:
    body = {key: item for key, item in value.items() if key != "binding_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True).encode()).hexdigest()


def _tool_record(session: str, agent: str, name: str, tool_id: str, inputs: dict) -> dict:
    return {
        "type": "assistant", "sessionId": session, "agentId": agent,
        "message": {"model": "claude-sonnet-5-5", "content": [
            {"type": "tool_use", "id": tool_id, "name": name, "input": inputs},
        ]},
    }


def _tool_result(session: str, agent: str, tool_id: str, content="ok", *, is_error=False) -> dict:
    return {
        "type": "user", "sessionId": session, "agentId": agent,
        "message": {"content": [
            {"type": "tool_result", "tool_use_id": tool_id,
             "is_error": is_error, "content": content},
        ]},
    }


class ClaudeChildTranscriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.worktree = self.root / "worker-1"
        self.session = "root-session"
        self.agent = "native-task-1"
        self.prompt = "Exact compact assignment with binding and test gates."
        self.worker = {
            "worktree": self.worktree,
            "owned_path": "src/step_1.py",
            "prompt": self.prompt,
            "binding_path": self.root / "operator/compact-bindings/worker-1.json",
            "binding_sha256": "a" * 64,
            "packet_sha256": "b" * 64,
        }
        self.records = [
            {"type": "user", "sessionId": self.session, "agentId": self.agent,
             "parentUuid": None, "isSidechain": True,
             "message": {"content": self.prompt}},
            _tool_record(self.session, self.agent, "Write", "edit-1", {
                "file_path": str(self.worktree / "src/step_1.py"), "content": "source",
            }),
            _tool_result(self.session, self.agent, "edit-1"),
        ]
        self.phases = {name: {"path": self.root / f"{name}.json", "sha256": f"{name:0<2}"}
                       for name in ("start", "finish")}

    def _validate(self, records=None, worker=None, parent_model="claude-sonnet-5-5"):
        path = self.root / "child.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in (records or self.records)), encoding="utf-8")
        with mock.patch.object(trace, "_phase_records", return_value=self.phases):
            return trace._validate_child(
                "1", worker or self.worker, path, {}, self.root,
                self.session, self.agent, parent_model, {"checks": {}, "errors": []},
            )

    def test_accepts_fresh_camelcase_native_child_without_init_record(self):
        result = self._validate()
        self.assertEqual(result["model"], ["claude-sonnet-5-5"])
        self.assertEqual(result["direct_edit_paths"], [str(self.worktree / "src/step_1.py")])

    def test_rejects_changed_spawn_prompt(self):
        worker = dict(self.worker, prompt="different assignment")
        with self.assertRaisesRegex(trace.TraceError, "exact fresh dispatched prompt"):
            self._validate(worker=worker)

    def test_rejects_foreign_camelcase_child_identity(self):
        records = [dict(row) for row in self.records]
        records[1] = dict(records[1], agentId="stale-agent")
        with self.assertRaisesRegex(trace.TraceError, "foreign native session or agent ID"):
            self._validate(records=records)

    def test_rejects_non_sonnet_served_child_model(self):
        records = [dict(row) for row in self.records]
        records[1] = dict(records[1], message={"model": "claude-haiku-5-5", "content":
                                              records[1]["message"]["content"]})
        with self.assertRaisesRegex(trace.TraceError, "native model identity"):
            self._validate(records=records)

    def test_rejects_direct_edit_outside_owned_file(self):
        records = list(self.records)
        records[1] = _tool_record(self.session, self.agent, "Edit", "edit-1", {
            "file_path": str(self.worktree / "src/step_2.py"), "old_string": "a", "new_string": "b",
        })
        with self.assertRaisesRegex(trace.TraceError, "outside its owned file"):
            self._validate(records=records)

    def test_rejects_failed_direct_edit_result(self):
        records = list(self.records)
        records[2] = _tool_result(self.session, self.agent, "edit-1", "write failed", is_error=True)
        with self.assertRaisesRegex(trace.TraceError, "tool result is missing, failed, or truncated"):
            self._validate(records=records)


class ClaudeWorkerPhaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name).resolve()
        self.worktree = self.run / "worker-1"
        self.binding_path = self.run / "operator/compact-bindings/worker-1.json"
        binding = {"task": {"worker_id": "1"}, "package": {"task_script": str(self.run / "task.py")}}
        binding["binding_sha256"] = _canonical(binding)
        raw = _dump(self.binding_path, binding)
        self.worker = {
            "worktree": self.worktree,
            "owned_path": "src/step_1.py",
            "binding_path": self.binding_path,
            "binding_sha256": binding["binding_sha256"],
            "packet_sha256": hashlib.sha256(raw).hexdigest(),
        }

    def _records(self, command):
        return [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "bash-1", "name": "Bash", "input": {"command": command}},
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "bash-1", "is_error": False, "content": "ok"},
            ]}},
        ]

    def test_rejects_bash_command_with_wrong_worktree_prefix(self):
        command = f"cd {self.run / 'other'} && python3 -B checks.py --worker 1"
        with self.assertRaisesRegex(trace.TraceError, "assigned worktree cd prefix"):
            trace._phase_records(self.run, "1", self.worker, {"delivery_mode": "patch"},
                                 self._records(command), {"checks": {}, "errors": []})

    def test_rejects_missing_explicit_cd_prefix(self):
        with self.assertRaisesRegex(trace.TraceError, "assigned worktree cd prefix"):
            trace._phase_records(self.run, "1", self.worker, {"delivery_mode": "patch"},
                                 self._records("python3 -B checks.py --worker 1"),
                                 {"checks": {}, "errors": []})

    def test_rejects_changed_compact_binding(self):
        worker = dict(self.worker, binding_sha256="0" * 64)
        with self.assertRaisesRegex(trace.TraceError, "binding digest is invalid"):
            trace._phase_records(self.run, "1", worker, {"delivery_mode": "patch"}, [],
                                 {"checks": {}, "errors": []})


class ClaudeNativeEvidenceTests(unittest.TestCase):
    def test_forwarded_child_tools_are_not_parent_actions(self):
        root = {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "root", "name": "Read", "input": {}}]}}
        forwarded = {"type": "assistant", "parent_tool_use_id": "spawn", "agent_id": "worker",
                     "message": {"content": [{"type": "tool_use", "id": "child", "name": "Write", "input": {}}]}}
        calls, results = trace._calls_and_results([root, forwarded])
        self.assertEqual([call["id"] for call in calls], ["root"])
        with self.assertRaisesRegex(trace.TraceError, "incomplete native identity"):
            trace._calls_and_results([dict(forwarded, agent_id=None)])

    def test_native_file_result_may_omit_error_flag_but_errors_still_fail(self):
        call = {"id": "file", "name": "Write"}
        rows = {"file": [{"type": "tool_result", "tool_use_id": "file", "content": "updated successfully"}]}
        self.assertTrue(trace._tool_result_ok(call, rows))
        self.assertFalse(trace._tool_result_ok(dict(call, name="Bash"), rows))
        for error in (True, "false", 1):
            with self.subTest(error=error):
                self.assertFalse(trace._tool_result_ok(call, {"file": [dict(rows["file"][0], is_error=error)]}))
        self.assertFalse(trace._tool_result_ok(call, {"file": [dict(rows["file"][0], content="<tool_use_error>blocked</tool_use_error>")]}))

    def test_agent_matcher_allows_display_description_change_only(self):
        expected = {"description": "worker 1.", "subagent_type": "general-purpose",
                    "run_in_background": True, "prompt": "exact prompt"}
        observed = dict(expected, description="worker 1")
        self.assertTrue(trace.agent_arguments_match(observed, expected))
        self.assertFalse(trace.agent_arguments_match(dict(observed, prompt="changed"), expected))
        self.assertFalse(trace.agent_arguments_match(dict(observed, extra="value"), expected))
        self.assertFalse(trace.agent_arguments_match(dict(observed, description=" "), expected))

    def test_local_bash_lifecycle_filter_requires_native_command_binding(self):
        command = "python3 -B /run/operator/operations.py prepare-batch --run /run"
        call_id, task_id, session, run_id = "tool-bash", "task-bash", "session", "run"
        rows = [
            {"type": "assistant", "session_id": session, "message": {"content": [
                {"type": "tool_use", "id": call_id, "name": "Bash", "input": {"command": command}},
            ]}},
            {"type": "system", "subtype": "task_started", "task_id": task_id,
             "tool_use_id": call_id, "run_id": run_id, "session_id": session,
             "task_type": "local_bash", "description": command},
            {"type": "system", "subtype": "task_notification", "task_id": task_id,
             "tool_use_id": call_id, "run_id": run_id, "session_id": session,
             "status": "completed", "summary": command},
        ]
        filtered, shell_tasks = trace.filter_local_bash_task_events(rows)
        self.assertEqual(filtered, [rows[0]])
        self.assertEqual(shell_tasks, {call_id: {"task_id": task_id, "command": command}})
        malformed = [dict(row) for row in rows]
        malformed[1] = dict(malformed[1], description="different command")
        with self.assertRaisesRegex(ValueError, "not bound"):
            trace.filter_local_bash_task_events(malformed)

    def test_fixture_summary_requires_absolute_exact_script_path(self):
        run = Path.cwd() / "candidate-run"
        absolute = str(run / "operator" / "fixture.py")
        self.assertTrue(trace._verify_operation_command(
            ["python3", "-B", absolute, "verify", "--run", str(run), "--summary"],
            run, "fixture.py", ["verify", "--run", str(run), "--summary"],
        ))
        self.assertFalse(trace._verify_operation_command(
            ["python3", "-B", "candidate-run/operator/fixture.py", "verify", "--run", str(run), "--summary"],
            run, "fixture.py", ["verify", "--run", str(run), "--summary"],
        ))

    def test_full_audit_passes_launch_and_process_to_parent_flow(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory).resolve()
            operator = run / "operator"
            (operator / "claude-native").mkdir(parents=True)
            (operator / "stderr.log").write_text("", encoding="utf-8")
            session = "root-session"
            cwd = str(run / "caller")
            manifest = {"run_id": "run-1"}
            launch = {"session_id": session, "cwd": cwd, "model": "sonnet",
                      "argv": ["claude", "--session-id", session]}
            process = {"exit_code": 0}
            root_records = [
                {"type": "system", "subtype": "init", "session_id": session, "cwd": cwd},
                {"type": "assistant", "session_id": session,
                 "message": {"model": "claude-sonnet-5-5", "content": []}},
            ]
            observed = [{"observed_epoch": float(index), "event": row}
                        for index, row in enumerate(root_records)]
            parent_result = {"run_id": "run-1"}
            dispatch = {"1": {"arguments": {"description": "worker", "subagent_type": "general-purpose",
                                              "run_in_background": True, "prompt": "prompt"}}}

            def read_json(path):
                name = Path(path).name
                if name == "manifest.json":
                    return manifest
                if name == "launch.json":
                    return launch
                if name == "process-result.json":
                    return process
                if name == "parent-result.json":
                    return parent_result
                if name == "transcript-index.json":
                    return {"rows": [{"kind": "parent", "source_path": str(run / "parent.jsonl")}]}
                raise AssertionError(f"unexpected JSON load: {path}")

            class ParentFlowReached(RuntimeError):
                pass

            def parent_flow(run_arg, expected, dispatch_arg, starts, stops, records,
                            parent_result_arg, manifest_arg, launch_arg, process_arg, report):
                self.assertEqual(run_arg, run)
                self.assertEqual(expected, ["1"])
                self.assertIs(dispatch_arg, dispatch)
                self.assertEqual(records, root_records)
                self.assertIs(parent_result_arg, parent_result)
                self.assertIs(manifest_arg, manifest)
                self.assertIs(launch_arg, launch)
                self.assertIs(process_arg, process)
                raise ParentFlowReached()

            with (mock.patch.object(trace, "_read_json", side_effect=read_json),
                  mock.patch.object(trace, "_read_jsonl", side_effect=[root_records, observed]),
                  mock.patch.object(trace, "_manifest_workers", return_value=(["1"], manifest)),
                  mock.patch.object(trace, "_dispatch", return_value=({}, dispatch)),
                  mock.patch.object(trace, "_hooks", return_value=({}, {})),
                  mock.patch.object(trace, "_transcripts", return_value=({"1": run / "worker.jsonl"}, None, {"1": {"_agent_id": "worker"}})),
                  mock.patch.object(trace, "_validate_child", side_effect=lambda *args: self.assertIs(args[3], manifest) or {"worker_id": "1"}),
                  mock.patch.object(trace, "_verify_post_exit"),
                  mock.patch.object(trace, "_parent_flow", side_effect=parent_flow)):
                with self.assertRaises(ParentFlowReached):
                    trace.audit_run(run)

    def test_tool_result_json_accepts_one_complete_untruncated_object(self):
        call = {"id": "result-1", "name": "Bash"}
        results = {"result-1": [{"is_error": False, "content": '{"status":"PASSED"}'}]}
        self.assertEqual(trace._tool_result_json(call, results), {"status": "PASSED"})

    def test_tool_result_json_rejects_malformed_truncated_or_error_rows(self):
        call = {"id": "result-1", "name": "Bash"}
        for row in (
            {"is_error": False, "content": "not json"},
            {"is_error": False, "content": '{"status":"PASSED"} [output truncated]'},
            {"is_error": True, "content": '{"status":"PASSED"}'},
        ):
            with self.subTest(row=row), self.assertRaises(trace.TraceError):
                trace._tool_result_json(call, {"result-1": [row]})

    def test_rejects_missing_native_completion_notifications(self):
        expected = ["1", "2", "3"]
        session = "root-session"
        records = []
        dispatch = {}
        starts = {}
        for worker_id in expected:
            prompt = f"prompt-{worker_id}"
            arguments = {"description": f"worker {worker_id}", "subagent_type": "general-purpose",
                         "run_in_background": True, "prompt": prompt}
            dispatch[worker_id] = {"arguments": arguments, "prompt": prompt}
            tool_id, task_id = f"tool-{worker_id}", f"task-{worker_id}"
            records.append({"type": "assistant", "sessionId": session, "agentId": None,
                            "message": {"content": [
                                {"type": "tool_use", "id": tool_id, "name": "Agent", "input": arguments},
                                {"type": "tool_result", "tool_use_id": tool_id, "content": "launched"},
                            ]}})
            records.append({"type": "system", "subtype": "task_started", "session_id": session,
                            "task_id": task_id, "tool_use_id": tool_id, "run_id": f"run-{worker_id}",
                            "subagent_type": "general-purpose", "is_backgrounded": True,
                            "spawn_depth": 1, "task_type": "local_agent", "prompt": prompt})
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(trace.TraceError, "completion notifications are missing"):
                trace._parent_flow(Path(directory), expected, dispatch, starts, {}, records, {},
                                   {"schema_version": 1}, {"started_epoch": 1},
                                   {"finished_epoch": 20, "elapsed_s": 19},
                                   {"session_id": session, "checks": {}, "errors": []})

    def test_process_exit_alone_is_not_a_post_exit_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            operator = run / "operator"
            operator.mkdir()
            _dump(operator / "process-result.json", {"exit_code": 0})
            report = {"checks": {}, "errors": []}
            trace._verify_post_exit(run, {"run_id": "run-1"}, {"exit_code": 0}, report)
            self.assertEqual(report["checks"]["shared_post_exit_filesystem"]["status"], "INCOMPLETE")

    def test_process_only_run_does_not_pass_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            assignments = [{"worker_id": str(i), "path": f"src/step_{i}.py"} for i in range(1, 4)]
            _dump(run / "manifest.json", {"schema_version": 1, "run_id": "run-1", "workers": 3,
                                           "worker_ids": ["1", "2", "3"],
                                           "task_assignments": assignments})
            _dump(run / "operator/process-result.json", {"exit_code": 0})
            report = trace.audit_run(run)
            self.assertFalse(report["passed"])
            self.assertEqual(report["status"], "INCOMPLETE")

    def test_manifest_cannot_claim_two_workers(self):
        with self.assertRaisesRegex(trace.TraceError, "three or five"):
            trace._manifest_workers({"schema_version": 1, "workers": 2,
                                     "worker_ids": ["1", "2"],
                                     "task_assignments": [{"worker_id": "1", "path": "src/step_1.py"},
                                                          {"worker_id": "2", "path": "src/step_2.py"}]})

    def test_model_or_permission_error_text_is_typed_failure_evidence(self):
        records = [{"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Model unavailable: permission denied"},
        ]}}]
        self.assertTrue(trace._event_errors(records))


if __name__ == "__main__":
    unittest.main()
