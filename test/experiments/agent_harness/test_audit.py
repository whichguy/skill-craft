"""Offline invariants for the reusable agent-harness experiment audit."""
import tempfile
import subprocess
import sys
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

    def test_queued_graph_rejects_overlap_above_effective_capacity(self):
        case = {"arm": "direct", "workers": 4, "task_count": 4,
                "effective_capacity": 2, "fixture_version": experiment.RESOURCE_FIXTURE_VERSION}
        nodes = [node("root", None, "root", 1, 10)]
        nodes.extend(node(f"worker-{i}", "root", "worker", 2, 8, f"module-{i:02}")
                     for i in range(1, 5))

        result = experiment.audit_native_graph(case, nodes)

        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["peak_native_worker_overlap"], 4)
        self.assertIn("native worker overlap exceeded effective capacity: peak 4, capacity 2",
                      result["errors"])

    def test_queued_graph_records_capacity_and_refill_during_peer_activity(self):
        case = {"arm": "direct", "workers": 4, "task_count": 4,
                "effective_capacity": 2, "fixture_version": experiment.RESOURCE_FIXTURE_VERSION}
        nodes = [node("root", None, "root", 1, 20),
                 node("worker-1", "root", "worker", 2, 10, "module-01"),
                 node("worker-2", "root", "worker", 2, 5, "module-02"),
                 node("worker-3", "root", "worker", 6, 11, "module-03"),
                 node("worker-4", "root", "worker", 12, 13, "module-04")]

        result = experiment.audit_native_graph(case, nodes)

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["effective_worker_capacity"], 2)
        self.assertTrue(result["reached_capacity"])
        self.assertTrue(result["queued_refill_observed"])

    def test_queued_graph_rejects_an_omitted_last_task(self):
        case = {"arm": "direct", "workers": 4, "task_count": 4,
                "effective_capacity": 2, "fixture_version": experiment.RESOURCE_FIXTURE_VERSION}
        nodes = [node("root", None, "root", 1, 10)]
        nodes.extend(node(f"worker-{i}", "root", "worker", 2 + i / 10, 8,
                          f"module-{i:02}") for i in range(1, 4))

        result = experiment.audit_native_graph(case, nodes)

        self.assertEqual(result["status"], "FAIL")
        self.assertIn("native worker identities do not equal the requested independent task set",
                      result["errors"])

    def test_reused_native_session_handle_is_rejected(self):
        nodes = [node("root", None, "root", 1, 10),
                 node("worker-shared", "root", "worker", 2, 7, "module-01"),
                 node("worker-shared", "root", "worker", 3, 8, "module-02"),
                 node("worker-3", "root", "worker", 4, 9, "module-03")]

        result = experiment.audit_native_graph(self.direct_case, nodes)

        self.assertEqual(result["status"], "FAIL")
        self.assertIn("native node id is missing or duplicated", result["errors"])

    def test_queued_trial_rejects_a_resumed_worker_context(self):
        case = {"arm": "direct", "workers": 3, "task_count": 3,
                "effective_capacity": 2, "fixture_version": experiment.RESOURCE_FIXTURE_VERSION}
        nodes = [node("root", None, "root", 1, 10),
                 node("worker-1", "root", "worker", 2, 8, "module-01"),
                 node("worker-2", "root", "worker", 2, 6, "module-02"),
                 node("worker-3", "root", "worker", 3, 7, "module-03")]
        nodes[1]["invocation_intervals"] = [
            {"start_epoch": 2, "finish_epoch": 4}, {"start_epoch": 6, "finish_epoch": 8}]

        result = experiment.audit_native_graph(case, nodes)

        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["native_invocation_count"], 4)
        self.assertEqual(result["resumed_worker_task_ids"], ["module-01"])
        self.assertTrue(any("one native invocation per task" in error for error in result["errors"]))

    def test_queued_graph_requires_native_terminal_for_every_task(self):
        case = {"arm": "direct", "workers": 4, "task_count": 4,
                "effective_capacity": 2, "fixture_version": experiment.RESOURCE_FIXTURE_VERSION}
        nodes = [node("root", None, "root", 1, 10)]
        nodes.extend(node(f"worker-{i}", "root", "worker", 2 + i / 10, 8,
                          f"module-{i:02}") for i in range(1, 5))
        nodes[-1]["terminal"] = False

        result = experiment.audit_native_graph(case, nodes)

        self.assertEqual(result["status"], "FAIL")
        self.assertIn("native node 'worker-4' has no terminal event", result["errors"])


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

    def test_task_count_is_independent_of_explicit_or_default_capacity(self):
        with tempfile.TemporaryDirectory() as temp:
            explicit_path = Path(temp) / "eight-cap-three"
            explicit = experiment.prepare_case(SimpleNamespace(
                case=explicit_path, provider="claude", arm="direct", workers=3, tasks=8,
                mode="edit", workspace=None, integration=None,
            ))
            explicit_case = experiment._read(explicit_path / "case.json")
            explicit_request = experiment._read(explicit_path / "harness-request.json")
            self.assertEqual(explicit["task_count"], 8)
            self.assertEqual(explicit_case["effective_capacity"], 3)
            self.assertEqual(explicit_request["capacity"], 3)
            self.assertEqual(len(explicit_request["tasks"]), 8)
            self.assertEqual(explicit_request["tasks"][0]["write_set"],
                             ["src/module_01.py", "src/module_01.json"])
            self.assertEqual(experiment._formula(5), experiment.FORMULAS[4])
            self.assertEqual(experiment._formula(6), (7, 15))

            omitted_path = Path(temp) / "eleven-default-capacity"
            omitted = experiment.prepare_case(SimpleNamespace(
                case=omitted_path, provider="claude", arm="direct", workers=None, tasks=11,
                mode="edit", workspace=None, integration=None,
            ))
            omitted_case = experiment._read(omitted_path / "case.json")
            omitted_request = experiment._read(omitted_path / "harness-request.json")
            self.assertEqual(omitted["task_count"], 11)
            self.assertEqual(omitted["effective_capacity"], 5)
            self.assertNotIn("capacity", omitted_request)
            self.assertEqual(experiment._normalized_request(omitted_request)["capacity"], 5)
            self.assertEqual(len(omitted_request["tasks"]), 11)
            self.assertEqual(omitted_case["fixture"]["resource_paths"][-1], "src/module_11.json")

    def test_combined_fixture_verifier_detects_a_missing_last_resource(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "caller"
            fixture = experiment._fixture(root, 6)
            for index in range(1, 7):
                factor, offset = experiment._formula(index)
                module = root / f"src/module_{index:02}.py"
                module.write_text(f"def transform(value):\n    return value * {factor} + {offset}\n")
                metadata = root / f"src/module_{index:02}.json"
                if index != 6:
                    metadata.write_text(json.dumps(experiment._resource_metadata(
                        f"src/module_{index:02}.py", factor, offset), sort_keys=True) + "\n")

            missing = subprocess.run(["python3", "-B", fixture["verifier"]], cwd=root,
                                     capture_output=True, text=True)
            self.assertNotEqual(missing.returncode, 0)

            factor, offset = experiment._formula(6)
            (root / "src/module_06.json").write_text(json.dumps(
                experiment._resource_metadata("src/module_06.py", factor, offset), sort_keys=True) + "\n")
            complete = subprocess.run(["python3", "-B", fixture["verifier"]], cwd=root,
                                      capture_output=True, text=True)
            self.assertEqual(complete.returncode, 0, complete.stderr)
            self.assertIn("6 complete module/resource pairs", complete.stdout)


class QueuedCleanupAuditTests(unittest.TestCase):
    def test_production_harness_delivery_and_cleanup_records_pass_join_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "caller"
            fixture = experiment._fixture(source, 2)
            case = {"arm": "direct", "workers": 2, "task_count": 2,
                    "requested_capacity": 1, "effective_capacity": 1,
                    "capacity_explicit": True, "fixture_version": experiment.RESOURCE_FIXTURE_VERSION,
                    "mode": "edit", "workspace": "worktree", "integration": "apply",
                    "caller": str(source), "fixture": fixture}
            sys.path.insert(0, str(experiment.SKILL_ROOT / "in-parallel" / "scripts"))
            import delivery
            import harness as production_harness
            case["parent_snapshot"] = delivery.capture(source)
            case["parent_index_sha256"] = experiment._sha((source / ".git" / "index").read_bytes())
            raw_request = experiment._request(case, "edit", "worktree", "apply")
            run = root / "harness"
            request_path = root / "request.json"
            experiment._write_new(request_path, raw_request)
            initialized = production_harness.execute(
                "init", run=str(run), request=str(request_path.resolve()),
                ask_agent_card=str(experiment.PACKAGES["ask_agent"]),
                dispatcher_card=str(experiment.PACKAGES["plan_dispatcher"]),
            )
            self.assertEqual(initialized["status"], "READY")

            native_nodes = []
            while True:
                dispatched = production_harness.execute("dispatch", run=str(run))
                launches = dispatched.get("launches", [])
                if not launches:
                    break
                for launch in launches:
                    task_id, attempt = launch["task"], launch["attempt"]
                    handle = "offline-simulated-native:" + task_id
                    native_nodes.append({"id": handle, "role": "worker", "task_id": task_id})
                    production_harness.execute("launched", run=str(run), attempt=attempt, handle=handle)
                    prepared = experiment._read(run / "prepared" / f"{attempt}.json")
                    for phase in ("worker-start",):
                        command = prepared["commands"][phase]
                        started = subprocess.run(command["argv"], cwd=command["cwd"],
                                                 capture_output=True, text=True)
                        self.assertEqual(started.returncode, 0, started.stderr)
                        self.assertEqual(json.loads(started.stdout)["status"], "WORKER_CONTEXT_READY")
                    index = int(task_id.split("-")[-1])
                    factor, offset = experiment._formula(index)
                    worker_root = Path(launch["cwd"])
                    (worker_root / f"src/module_{index:02}.py").write_text(
                        f"def transform(value):\n    return value * {factor} + {offset}\n")
                    (worker_root / f"src/module_{index:02}.json").write_text(json.dumps(
                        experiment._resource_metadata(f"src/module_{index:02}.py", factor, offset),
                        sort_keys=True) + "\n")
                    task = next(row for row in raw_request["tasks"] if row["id"] == task_id)
                    experiment._git(worker_root, "add", "--", *task["write_set"])
                    experiment._git(worker_root, "commit", "-qm", f"offline worker {task_id}")
                    command = prepared["commands"]["worker-finish"]
                    finished_worker = subprocess.run(command["argv"], cwd=command["cwd"],
                                                     capture_output=True, text=True)
                    self.assertEqual(finished_worker.returncode, 0, finished_worker.stderr)
                    self.assertEqual(json.loads(finished_worker.stdout)["status"], "READY_FOR_PARENT_ACCEPTANCE")

                    criteria = [{"criterion": row["criterion"], "check": "offline formula and metadata check",
                                 "observed": "module and exact JSON metadata committed",
                                 "level": "confirmed"} for row in launch["result_contract"]["criteria"]]
                    result_path = root / f"{attempt}-native-result.json"
                    experiment._write_new(result_path, {
                        "native_handle": handle, "native_terminal": True, "status": "SUCCEEDED",
                        "summary": "[OFFLINE SIMULATED NATIVE RESULT] module and metadata implemented",
                        "criteria": criteria, "evidence": [],
                    })
                    collected = production_harness.execute(
                        "collect", run=str(run), attempt=attempt, result=str(result_path.resolve()))
                    self.assertEqual(collected["status"], "AWAITING_VERIFICATION")

                    proof_path = root / f"{attempt}-verification-evidence.txt"
                    proof_path.write_text(f"independent verification for {task_id}\n")
                    verification_path = root / f"{attempt}-verification.json"
                    experiment._write_new(verification_path, {
                        "passed": True, "reason": "independent offline fixture inspected the exact return",
                        "evidence": [{"path": str(proof_path), "sha256": experiment._sha(proof_path.read_bytes())}],
                    })
                    accepted = production_harness.execute(
                        "accept", run=str(run), attempt=attempt,
                        verification=str(verification_path.resolve()))
                    self.assertEqual(accepted["status"], "RECORDED_STATUS")

            final_result = production_harness.execute("finish", run=str(run))
            status_result = production_harness.execute("status", run=str(run))
            delivery_result = experiment._read(run / "delivery" / "result.json")
            audited = experiment._new_fixture_delivery_audit(
                case, run, final_result, delivery_result, status_result, native_nodes, raw_request)

            self.assertEqual(audited["status"], "PASS", audited["errors"])
            self.assertEqual(final_result["cleanup_status"], "complete")

            alias = root / "harness-alias"
            alias.symlink_to(run, target_is_directory=True)
            through_alias = experiment._new_fixture_delivery_audit(
                case, alias, final_result, delivery_result, status_result, native_nodes, raw_request)
            self.assertEqual(through_alias["status"], "PASS", through_alias["errors"])

            prepared_path = next((run / "prepared").glob("*.json"))
            prepared = experiment._read(prepared_path)
            packet_path = Path(prepared["packet"]["path"])
            original_packet = packet_path.read_bytes()
            packet_path.write_bytes(original_packet + b"\n")
            changed_packet = experiment._new_fixture_delivery_audit(
                case, run, final_result, delivery_result, status_result, native_nodes, raw_request)
            self.assertTrue(any("packet bytes differ from their pinned hash" in error
                                for error in changed_packet["errors"]))
            packet_path.write_bytes(original_packet)

            cleanup_by_id = {row["id"]: row for row in final_result["cleanup"]["workers"]}
            module_one = cleanup_by_id["module-01"]
            module_two = cleanup_by_id["module-02"]
            task_two_acceptance = module_two["acceptance"]
            module_two["acceptance"] = module_one["acceptance"]
            wrong_acceptance = experiment._new_fixture_delivery_audit(
                case, run, final_result, delivery_result, status_result, native_nodes, raw_request)
            self.assertTrue(any("module-02 cleanup is not bound to its terminal result" in error
                                for error in wrong_acceptance["errors"]))
            module_two["acceptance"] = task_two_acceptance

            packet_document = experiment._read(Path(prepared["packet"]["path"]))
            packet_workspace = packet_document["workspace"]
            packet_task = packet_document["task"]
            task_id = next(row["id"] for row in raw_request["tasks"]
                           if packet_task.get("objective") == row.get("objective")
                           and packet_task.get("expected_result") == row.get("expected_result")
                           and packet_task.get("write_set") == sorted(row.get("write_set", [])))
            actual_worktree = Path(packet_workspace["root"])
            branch = packet_workspace["branch"]
            experiment._git(source, "worktree", "add", "--detach", str(actual_worktree), branch)
            wrong_worktree = root / "absent-sibling-worktree"
            cleanup_row = cleanup_by_id[task_id]
            original_worktree = cleanup_row["worktree"]
            cleanup_row["worktree"] = str(wrong_worktree)
            try:
                wrong_path = experiment._new_fixture_delivery_audit(
                    case, run, final_result, delivery_result, status_result, native_nodes, raw_request)
                self.assertTrue(any(f"{task_id} worktree remains or is still registered" in error
                                    for error in wrong_path["errors"]))
            finally:
                cleanup_row["worktree"] = original_worktree
                if actual_worktree.exists():
                    experiment._git(source, "worktree", "remove", "--force", str(actual_worktree))

    def test_cleanup_audit_rejects_a_worktree_left_on_disk(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            harness = root / "harness"
            (harness / "delivery").mkdir(parents=True)
            worktree = root / "worker-tree"
            worktree.mkdir()
            task = {"id": "module-01", "objective": "implement module-01",
                    "expected_result": "module-01 is correct", "write_set": ["src/module_01.py"]}
            case = {"fixture_version": experiment.RESOURCE_FIXTURE_VERSION,
                    "workers": 1, "task_count": 1, "effective_capacity": 1,
                    "mode": "edit", "workspace": "worktree", "integration": "apply",
                    "caller": str(source), "fixture": {"owned_paths": ["src/module_01.py"]}}
            delivery_result = {"status": "SUCCEEDED", "workers": [{"id": "module-01",
                                 "branch": "worker/module-01", "worktree": str(worktree),
                                 "write_set": task["write_set"], "delivery": {"commits": []}}],
                               "integration": {"outcome": "applied", "applied_paths": ["src/module_01.py"],
                                               "workers": [{"id": "module-01", "paths": ["src/module_01.py"]}]},
                               "checks": []}
            delivery_path = harness / "delivery" / "result.json"
            delivery_path.write_text(json.dumps(delivery_result))
            final_result = {"status": "SUCCEEDED", "cleanup_status": "complete",
                            "cleanup": {"status": "complete", "workers": [{"id": "module-01",
                                        "status": "closed", "worktree": str(worktree),
                                        "worktree_path_status": "removed",
                                        "helper_outcome": {"status": "closed", "removed": True}}]}}
            status_result = {"workers_accepted": True, "active": [],
                             "progress": {"completed": [{"step": "module-01"}]}}

            result = experiment._new_fixture_delivery_audit(
                case, harness, final_result, delivery_result, status_result, [], {"tasks": [task], "checks": []})

            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("worktree remains or is still registered" in error for error in result["errors"]))

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
