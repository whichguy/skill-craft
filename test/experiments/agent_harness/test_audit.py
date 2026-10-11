"""Offline invariants for the reusable agent-harness experiment audit."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import json
import shlex

import experiment


def node(ident, parent, role, start, finish, task_id=None):
    value = {"id": ident, "parent_id": parent, "role": role, "start_epoch": start,
             "finish_epoch": finish, "terminal": True}
    if task_id is not None:
        value.update(task_id=task_id, phase_evidence={
            "worker-start": {"status": "WORKER_CONTEXT_READY"},
            "worker-finish": {"status": "READY_FOR_PARENT_ACCEPTANCE"},
        })
    return value


class NativeGraphAuditTests(unittest.TestCase):
    def setUp(self):
        self.direct_case = {"arm": "direct", "workers": 3}
        self.nested_case = {"arm": "nested", "workers": 3}

    def test_direct_graph_requires_three_terminal_native_workers(self):
        nodes = [node("root", None, "root", 1, 10)]
        nodes.extend(node(f"worker-{i}", "root", "worker", 2 + i / 10, 8,
                          f"module-{i:02}") for i in range(1, 4))
        result = experiment.audit_native_graph(self.direct_case, nodes)
        self.assertEqual(result["status"], "PASS")
        self.assertGreaterEqual(result["peak_native_worker_overlap"], 1)

    def test_direct_graph_rejects_missing_worker_phase_evidence(self):
        nodes = [node("root", None, "root", 1, 10)]
        nodes.extend(node(f"worker-{i}", "root", "worker", 2, 8,
                          f"module-{i:02}") for i in range(1, 4))
        nodes[1]["phase_evidence"].pop("worker-finish")
        self.assertEqual(experiment.audit_native_graph(self.direct_case, nodes)["status"], "FAIL")

    def test_distinct_worker_sessions_cannot_repeat_a_task_id(self):
        nodes = [node("root", None, "root", 1, 10),
                 node("worker-1", "root", "worker", 2, 8, "module-01"),
                 node("worker-2", "root", "worker", 3, 8, "module-01"),
                 node("worker-3", "root", "worker", 4, 8, "module-03")]
        self.assertEqual(len({item["id"] for item in nodes}), 4)

        result = experiment.audit_native_graph(self.direct_case, nodes)

        self.assertEqual(result["status"], "FAIL")
        self.assertIn("native worker identities do not equal the requested independent task set",
                      result["errors"])

    def test_nonterminal_worker_or_coordinator_fails_the_graph_audit(self):
        cases = [
            ("worker", self.direct_case,
             [node("root", None, "root", 1, 10),
              *[node(f"worker-{i}", "root", "worker", 2 + i / 10, 8,
                     f"module-{i:02}") for i in range(1, 4)]],
             "worker-1"),
            ("coordinator", self.nested_case,
             [node("root", None, "root", 1, 12),
              node("coordinator", "root", "coordinator", 2, 10),
              *[node(f"worker-{i}", "coordinator", "worker", 3 + i / 10, 8,
                     f"module-{i:02}") for i in range(1, 4)]],
             "coordinator"),
        ]
        for role, case, nodes, ident in cases:
            with self.subTest(role=role):
                target = next(item for item in nodes if item["id"] == ident)
                target["terminal"] = False

                result = experiment.audit_native_graph(case, nodes)

                self.assertEqual(result["status"], "FAIL")
                self.assertIn(f"native node '{ident}' has no terminal event", result["errors"])

    def test_nested_graph_requires_one_coordinator_and_workers_beneath_it(self):
        nodes = [node("root", None, "root", 1, 12),
                 node("coordinator", "root", "coordinator", 2, 10)]
        nodes.extend(node(f"worker-{i}", "coordinator", "worker", 3 + i / 10, 8,
                          f"module-{i:02}") for i in range(1, 4))
        self.assertEqual(experiment.audit_native_graph(self.nested_case, nodes)["status"], "PASS")
        nodes[1]["finish_epoch"] = 7
        self.assertEqual(experiment.audit_native_graph(self.nested_case, nodes)["status"], "FAIL")

    def test_native_overlap_uses_each_resume_interval_not_agent_lifetime_span(self):
        nodes = [node("root", None, "root", 1, 10)]
        first = node("worker-1", "root", "worker", 2, 9, "module-01")
        first["invocation_intervals"] = [
            {"start_epoch": 2, "finish_epoch": 3},
            {"start_epoch": 8, "finish_epoch": 9},
        ]
        nodes.extend([first,
                      node("worker-2", "root", "worker", 4, 6, "module-02"),
                      node("worker-3", "root", "worker", 5, 7, "module-03")])
        result = experiment.audit_native_graph(self.direct_case, nodes)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["peak_native_worker_overlap"], 2)

    def test_nested_coordinator_early_terminal_stop_fails_even_after_later_resume(self):
        case = {"arm": "nested", "workers": 3, "provider": "claude"}
        nodes = [node("root", None, "root", 1, 13),
                 node("coordinator", "root", "coordinator", 2, 12)]
        coordinator = nodes[1]
        coordinator["invocation_intervals"] = [
            {"start_epoch": 2, "finish_epoch": 5},
            {"start_epoch": 7, "finish_epoch": 12},
        ]
        coordinator["terminal_stop_epochs"] = [5, 12]
        coordinator["agent_launches"] = [{"subagent_type": "claude", "effective_is_backgrounded": False}]
        nodes.extend(node(f"worker-{i}", "coordinator", "worker", 3 + i / 10, 9,
                          f"module-{i:02}") for i in range(1, 4))
        for worker in nodes[2:]:
            worker["agent_launches"] = [{"subagent_type": "general-purpose",
                                          "effective_is_backgrounded": True}]
        result = experiment.audit_native_graph(case, nodes)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("coordinator returned before all native workers" in error
                            for error in result["errors"]))

    def test_invalid_worker_interval_makes_overlap_unavailable(self):
        nodes = [node("root", None, "root", 1, 10)]
        worker = node("worker-1", "root", "worker", 2, 9, "module-01")
        worker["invocation_intervals"] = [{"start_epoch": 4, "finish_epoch": 3}]
        nodes.extend([worker,
                      node("worker-2", "root", "worker", 4, 6, "module-02"),
                      node("worker-3", "root", "worker", 5, 7, "module-03")])
        result = experiment.audit_native_graph(self.direct_case, nodes)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["peak_native_worker_overlap"], "unavailable")


class ClaudeLaunchEvidenceTests(unittest.TestCase):
    def test_omitted_background_argument_uses_native_effective_state(self):
        evidence = experiment._claude_agent_launch(
            {"subagent_type": "general-purpose"},
            {"task_type": "local_agent", "subagent_type": "general-purpose",
             "is_backgrounded": True, "task_id": "worker", "tool_use_id": "call"},
            "general-purpose", role="worker",
        )
        self.assertEqual(evidence["requested_run_in_background"], "omitted")
        self.assertTrue(evidence["effective_is_backgrounded"])

    def test_coordinator_may_be_foreground_and_input_request_is_retained(self):
        evidence = experiment._claude_agent_launch(
            {"subagent_type": "claude", "run_in_background": False},
            {"task_type": "local_agent", "subagent_type": "claude",
             "is_backgrounded": False, "task_id": "coordinator", "tool_use_id": "call"},
            "claude", role="coordinator",
        )
        self.assertFalse(evidence["requested_run_in_background"])
        self.assertFalse(evidence["effective_is_backgrounded"])

    def test_worker_must_be_effectively_backgrounded_even_if_argument_omitted(self):
        with self.assertRaises(experiment.ExperimentError):
            experiment._claude_agent_launch(
                {"subagent_type": "general-purpose"},
                {"task_type": "local_agent", "subagent_type": "general-purpose",
                 "is_backgrounded": False, "task_id": "worker", "tool_use_id": "call"},
                "general-purpose", role="worker",
            )

    def test_native_launch_must_be_nonfork_and_match_hook_type(self):
        event = {"task_type": "local_agent", "subagent_type": "fork",
                 "is_backgrounded": True, "task_id": "worker", "tool_use_id": "call"}
        with self.assertRaises(experiment.ExperimentError):
            experiment._claude_agent_launch({"subagent_type": "fork"}, event, "fork", role="worker")

    def test_fixture_retains_staged_and_unstaged_dirty_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture = experiment._fixture(Path(temp) / "caller", 3)
            self.assertEqual(experiment._git(Path(temp) / "caller", "config", "--local", "user.name"), "Experiment Fixture")
            self.assertEqual(experiment._git(Path(temp) / "caller", "config", "--local", "user.email"), "fixture.invalid")
            self.assertEqual(set(fixture["staged_paths"]), {".claspignore", "context/brief.md"})
            self.assertEqual(experiment._git(Path(temp) / "caller", "rev-parse", "HEAD"), fixture["head"])
            status = experiment._git(Path(temp) / "caller", "status", "--porcelain=v1")
            self.assertIn("MM .claspignore", status)
            self.assertIn(" M .gitignore", status)
            self.assertIn("MM context/brief.md", status)


class PreparedCaseTests(unittest.TestCase):

    def test_phase_commands_require_standalone_invocations(self):
        command = "python3 /tmp/ask_agent_task.py worker-finish --binding /tmp/binding.json"
        self.assertTrue(experiment._command_matches(command, "/tmp/worker", command))
        self.assertTrue(experiment._command_matches("cd /tmp/worker && " + command, "/tmp/worker", command))
        self.assertFalse(experiment._command_matches("cd /tmp/worker && git status && " + command, "/tmp/worker", command))
        self.assertFalse(experiment._command_matches(command + " > /tmp/result", "/tmp/worker", command))

    def test_prepare_builds_valid_frozen_fixtures_for_all_modes(self):
        with tempfile.TemporaryDirectory() as temp:
            for mode in ("edit", "report-only", "ephemeral"):
                case_path = Path(temp) / mode
                prepared = experiment.prepare_case(SimpleNamespace(
                    case=case_path, provider="claude", arm="direct", workers=3,
                    mode=mode, workspace=None, integration=None,
                ))
                case = experiment._read(case_path / "case.json")
                request = experiment._read(case_path / "harness-request.json")
                normalized = experiment._normalized_request(request)
                self.assertEqual(case["normalized_request_sha256"], experiment._sha(experiment._canonical(normalized)))
                self.assertEqual(case["request_sha256"], experiment._sha((case_path / "harness-request.json").read_bytes()))
                self.assertEqual(case["source_freeze"], experiment.source_freeze())
                self.assertEqual(prepared["freeze_sha256"], case["source_freeze"]["sha256"])
                self.assertEqual(len(request["tasks"]), 3)
                self.assertEqual([task["id"] for task in request["tasks"]], [f"module-{i:02}" for i in range(1, 4)])
                self.assertEqual(experiment._git(Path(case["caller"]), "rev-parse", "HEAD"), case["fixture"]["head"])
                status = experiment._git(Path(case["caller"]), "status", "--porcelain=v1")
                self.assertIn("MM .claspignore", status)
                self.assertIn(" M .gitignore", status)
                self.assertIn("MM context/brief.md", status)
                if mode == "report-only":
                    for index, (factor, offset) in enumerate(experiment.FORMULAS[:3], 1):
                        source = (Path(case["caller"]) / f"src/module_{index:02}.py").read_text()
                        self.assertIn(f"return value * {factor} + {offset}", source)
                if mode == "ephemeral":
                    self.assertEqual(request["integration"], "return-only")
                    self.assertEqual(request["workspace"], "worktree")
                    for index, (factor, offset) in enumerate(experiment.FORMULAS[:3], 1):
                        task = request["tasks"][index - 1]
                        self.assertIn(f"transform(value) = value * {factor} + {offset}", task["objective"])
                        self.assertIn(f"transform(0) = {offset}", task["expected_result"])
                        self.assertIn(f"transform(4) = {factor * 4 + offset}", task["expected_result"])

            current_case = Path(temp) / "current-edit"
            prepared = experiment.prepare_case(SimpleNamespace(
                case=current_case, provider="claude", arm="direct", workers=3,
                mode="edit", workspace="current", integration="apply",
            ))
            raw = experiment._read(current_case / "harness-request.json")
            normalized = experiment._normalized_request(raw)
            frozen = experiment._read(current_case / "case.json")
            self.assertEqual(raw["capacity"], 3)
            self.assertEqual(normalized["capacity"], 1)
            self.assertEqual(frozen["normalized_request_sha256"], experiment._sha(experiment._canonical(normalized)))
            self.assertEqual(prepared["freeze_sha256"], frozen["freeze_sha256"])

    def test_ephemeral_audit_requires_numeric_findings_and_no_source_commit(self):
        with tempfile.TemporaryDirectory() as temp:
            case_dir = Path(temp) / "case"
            experiment.prepare_case(SimpleNamespace(
                case=case_dir, provider="claude", arm="direct", workers=3,
                mode="ephemeral", workspace=None, integration=None,
            ))
            case = experiment._read(case_dir / "case.json")
            request = experiment._read(case_dir / "harness-request.json")
            packets = Path(case["harness_run"]) / "packets"
            packets.mkdir(parents=True)
            import sys
            sys.path.insert(0, str(experiment.SKILL_ROOT / "ask-agent" / "scripts"))
            import ask_agent_task
            rows = []
            for task in request["tasks"]:
                self.assertEqual(set(task), {"id", "objective", "expected_result", "write_set"})
                worker_request = {key: request[key] for key in (
                    "source", "workspace", "mode", "current_learnings", "authorization")}
                worker_request.update({key: task[key] for key in ("objective", "expected_result", "write_set")})
                worker_request.update({"writers_quiescent": True,
                                       "store": str(Path(case["harness_run"]) / "workspaces")})
                packet_path = packets / f"{task['id']}.json"
                prepared = ask_agent_task.prepare_task(
                    worker_request, experiment.PACKAGES["ask_agent"], packet_path=packet_path)
                binding = experiment._read(packet_path)
                self.assertNotIn("id", binding["task"])
                self.assertEqual(binding["task"]["mode"], request["mode"])
                rows.append(prepared)
                worktree = Path(prepared["launch"]["cwd"])
                index = int(task["id"].split("-")[1])
                factor, offset = experiment.FORMULAS[index - 1]
                (worktree / task["write_set"][0]).write_text(
                    f"transform(value) = value * {factor} + {offset}\n"
                    f"transform(0) = {offset}\ntransform(4) = {factor * 4 + offset}\n"
                )

            result = experiment._ephemeral_worker_audit(case_dir, case, request, rows)
            self.assertEqual(result["status"], "PASS", result["errors"])
            first_worktree = Path(rows[0]["launch"]["cwd"])
            status = experiment._git(first_worktree, "status", "--porcelain=v1")
            self.assertIn("MM .claspignore", status)
            self.assertIn(" M .gitignore", status)
            self.assertIn("MM context/brief.md", status)
            first_note = first_worktree / request["tasks"][0]["write_set"][0]
            first_note.write_text(first_note.read_text().replace("transform(4) = 11", "transform(4) = 10"))
            result = experiment._ephemeral_worker_audit(case_dir, case, request, rows)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("correct transform(4) value" in error for error in result["errors"]))
            first_note.write_text(first_note.read_text().replace("transform(4) = 10", "transform(4) = 11"))
            gitignore = first_worktree / ".gitignore"
            gitignore.write_text(gitignore.read_text() + "unexpected-drift/\n")
            result = experiment._ephemeral_worker_audit(case_dir, case, request, rows)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("changed inherited workspace state" in error for error in result["errors"]))


class GrokPhaseEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.commands = {}
        self.rows = []
        self.expected = {
            "worker-start": "WORKER_CONTEXT_READY",
            "worker-finish": "READY_FOR_PARENT_ACCEPTANCE",
        }
        for index, phase in enumerate(("worker-start", "worker-finish"), 1):
            argv = ["python3", "-B", "/tmp/ask_agent_task.py", phase,
                    "--binding", f"/tmp/{phase}.json", "--expected-binding-sha256", "a" * 64]
            cwd = f"/tmp/worker-{index}"
            self.commands[phase] = {"argv": argv, "cwd": cwd}
            tool_id = f"call-{phase}"
            self.rows.extend([
                {"line": 2 * index - 1, "update": {"sessionUpdate": "tool_call", "title": "run_terminal_command",
                                                     "toolCallId": tool_id,
                                                     "rawInput": {"command": shlex.join(argv)}}},
                {"line": 2 * index, "update": {"sessionUpdate": "tool_call_update", "status": "completed",
                                                  "toolCallId": tool_id,
                                                  "rawOutput": {"type": "Bash", "exit_code": 0,
                                                                "output": json.dumps({"status": self.expected[phase],
                                                                                      **({"command": "worker-finish"} if phase == "worker-finish" else {})}),
                                                                "truncated": False}}},
            ])

    def test_grok_native_time_uses_exact_session_child_and_event(self):
        row = {"timestamp": 100, "params": {"sessionId": "root", "_meta": {"agentTimestampMs": 100123},
               "update": {"sessionUpdate": "subagent_spawned", "subagent_id": "child"}}}
        self.assertEqual(experiment._native_grok_time([row], "root", "subagent_spawned", "child"), 100.123)
        for session, kind, child in [("foreign", "subagent_spawned", "child"), ("root", "subagent_finished", "child"), ("root", "subagent_spawned", "other")]:
            with self.assertRaises(experiment.ExperimentError):
                experiment._native_grok_time([row], session, kind, child)
        with self.assertRaises(experiment.ExperimentError):
            experiment._native_grok_time([row, row], "root", "subagent_spawned", "child")

    def test_grok_native_time_rejects_invalid_timestamp(self):
        row = {"timestamp": float("nan"), "params": {"sessionId": "root",
               "update": {"sessionUpdate": "subagent_spawned", "subagent_id": "child"}}}
        with self.assertRaises(experiment.ExperimentError):
            experiment._native_grok_time([row], "root", "subagent_spawned", "child")

    def test_grok_completion_uses_native_turn_completed_after_workers(self):
        turn = {"line": 20, "update": {"sessionUpdate": "turn_completed", "stop_reason": "end_turn"}}
        child = {"line": 19, "update": {"sessionUpdate": "subagent_finished", "status": "completed"}}
        experiment._grok_completion_order([child, turn], [child])
        child["line"] = 21
        with self.assertRaises(experiment.ExperimentError):
            experiment._grok_completion_order([turn, child], [child])
        child["line"] = 19
        child["update"]["status"] = "failed"
        with self.assertRaises(experiment.ExperimentError):
            experiment._grok_completion_order([child, turn], [child])
        with self.assertRaises(experiment.ExperimentError):
            experiment._grok_completion_order([], [])

    def test_grok_phase_requires_exact_command_and_typed_success_result(self):
        result = experiment._grok_phase_evidence(self.rows, self.commands)
        self.assertEqual(set(result), {"worker-start", "worker-finish"})
        self.assertEqual(result["worker-start"]["status"], "WORKER_CONTEXT_READY")
        self.assertEqual(result["worker-finish"]["status"], "READY_FOR_PARENT_ACCEPTANCE")

    def test_grok_phase_ignores_statusless_progress_and_decodes_native_bytes(self):
        progress = {"line": 0, "update": {"sessionUpdate": "tool_call_update",
                    "toolCallId": "call-worker-start"}}
        self.rows.insert(1, progress)
        self.rows[2]["update"]["rawOutput"]["output"] = list(
            self.rows[2]["update"]["rawOutput"]["output"].encode("utf-8"))
        self.assertEqual(len(experiment._grok_phase_evidence(self.rows, self.commands)), 2)

    def test_grok_phase_rejects_duplicate_terminal_results(self):
        self.rows.append(self.rows[1])
        with self.assertRaises(experiment.ExperimentError):
            experiment._grok_phase_evidence(self.rows, self.commands)

    def test_grok_phase_rejects_invalid_native_bytes(self):
        self.rows[1]["update"]["rawOutput"]["output"] = [256]
        with self.assertRaises(experiment.ExperimentError):
            experiment._grok_phase_evidence(self.rows, self.commands)

    def test_grok_phase_rejects_success_text_in_nonzero_command_output(self):
        terminal = self.rows[1]["update"]
        terminal["rawOutput"]["exit_code"] = 1
        terminal["rawOutput"]["output"] = "ERROR: WORKER_CONTEXT_READY"
        with self.assertRaises(experiment.ExperimentError):
            experiment._grok_phase_evidence(self.rows, self.commands)

    def test_grok_phase_rejects_terminal_text_that_is_not_success_json(self):
        terminal = self.rows[1]["update"]
        terminal["rawOutput"]["output"] = "ERROR: WORKER_CONTEXT_READY"
        with self.assertRaises(experiment.ExperimentError):
            experiment._grok_phase_evidence(self.rows, self.commands)


if __name__ == "__main__":
    unittest.main()
