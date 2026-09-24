#!/usr/bin/env python3
"""Hermetic adversarial coverage for managed Ask Agent v2 evidence validation."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shlex
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "test/experiments/ask_agent_managed_workspaces/managed_workspaces.py"
SPEC = importlib.util.spec_from_file_location("managed_workspaces", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
managed_workspaces = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(managed_workspaces)

# Representative public tool labels, not runtime adapters or API allowlists.
HOST_TOOLS = {
    "grok": ("spawn_subagent", "get_command_or_subagent_output"),
    "claude": ("Agent", "task-notification"),
    "codex": ("collaboration.spawn_agent", "collaboration.wait_agent"),
    "cursor": ("Task", "task-notification"),
    "opencode": ("task", "task-notification"),
}


class ManagedWorkspaceEvidenceV2Tests(unittest.TestCase):
    """Exercise only disposable evidence files; no model process is launched."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="ask-agent-managed-harness-")
        self.root = Path(self.tmp.name)
        self.operator = self.root / "operator"
        self.caller = self.root / "caller"
        self.store = self.root / "workspace-store"
        self.operator.mkdir()
        self.caller.mkdir()
        self._git(self.caller, "init", "-q", "--initial-branch=main")
        self._git(self.caller, "config", "user.email", "managed-harness@example.invalid")
        self._git(self.caller, "config", "user.name", "Managed Harness")
        (self.caller / "pricing.json").write_text('{"currency":"USD","base_price":100}\n', encoding="utf-8")
        self._git(self.caller, "add", "pricing.json")
        self._git(self.caller, "commit", "-q", "-m", "fixture baseline")
        self.manifest = {"host": "codex", "caller": str(self.caller)}
        self.helper_path = ROOT / "skills/ask-agent/scripts/ask_agent_workspace.py"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_json(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _digest(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _git(self, cwd: Path, *arguments: str) -> str:
        result = subprocess.run(["git", *arguments], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode:
            self.fail(f"git {' '.join(arguments)} failed:\n{result.stderr}")
        return result.stdout

    def _helper(self, *arguments: str) -> dict[str, Any]:
        result = subprocess.run([sys.executable, "-B", str(self.helper_path), *arguments], cwd=self.root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            self.fail(f"helper did not return JSON: {error}\nstdout={result.stdout}\nstderr={result.stderr}")
        if result.returncode:
            self.fail(f"helper {' '.join(arguments)} failed: {payload}\nstderr={result.stderr}")
        return payload

    def _prepare_cli_run(self) -> Path:
        run = self.root / "cli-run"
        result = subprocess.run(
            [sys.executable, "-B", str(MODULE_PATH), "prepare", "--run", str(run), "--host", "codex"],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.operator = run / "operator"
        self.caller = Path(payload["caller"])
        self.store = self.operator / "workspace-state"
        self.manifest = json.loads((self.operator / "manifest.json").read_text(encoding="utf-8"))
        self.helper_path = Path(self.manifest["workspace_helper"])
        return run

    def _attempt(
        self,
        *,
        role: str,
        attempt_id: str,
        worker_id: str,
        mode: str,
        state: str = "closed",
    ) -> dict[str, Any]:
        prepared = self._helper(
            "prepare", "--source", str(self.caller), "--store", str(self.store),
            "--label", f"{role}-{attempt_id}", "--writers-quiescent",
        )
        actual_attempt_id = str(prepared["attempt"])
        receipt_path = Path(prepared["receipt"])
        worktree = Path(prepared["worktree"])
        record: dict[str, Any] = {
            "worker_id": worker_id,
            "attempt_id": actual_attempt_id,
            "role": role,
            "delivery_mode": mode,
            "helper_receipt": str(receipt_path),
            "observed_git_root": str(worktree),
            "state": state,
        }
        if state == "retained":
            return record
        artifacts = list(managed_workspaces.EXPECTED_ARTIFACTS[role])
        reports = worktree / "reports"
        reports.mkdir()
        for relative in artifacts:
            (worktree / relative).write_text(f"{role}:{relative}\n", encoding="utf-8")
        if role == "code":
            (worktree / "pricing.json").write_text('{"currency":"USD","base_price":100,"discount_rate":0.10}\n', encoding="utf-8")
        inspect_args = managed_workspaces.returned_inspection_args(receipt_path, role)
        inspected = self._helper(*inspect_args)
        inspection_path = Path(inspected["evidence"]["inspection"])
        helper_acceptance = self.operator / "helper-acceptance" / f"{actual_attempt_id}.json"
        self._write_json(helper_acceptance, {
            "schema": "ask-agent.acceptance.v1",
            "inspection_fingerprint": inspected["fingerprint"],
            "decision": "integrated" if role == "code" else "report-consumed",
            "workers_stopped": True,
            "completion_reference": f"native return {worker_id}",
            "acceptance_reference": f"accepted {worker_id}",
            "artifacts": [{"path": relative, "purpose": "test retained report"} for relative in artifacts],
            "discard": [],
        })
        closed = self._helper("close", "--receipt", str(receipt_path), "--acceptance", str(helper_acceptance))
        record.update({
            "inspection": str(inspection_path),
            "delivery": inspected["delivery"],
            "delivery_evidence": inspected["delivery_evidence"],
            "close": str(Path(closed["receipt"]).parent / "close.json"),
            "artifacts": closed["archived_artifacts"],
            "helper_acceptance": str(helper_acceptance),
        })
        return record

    def _write_outcomes(self, records: list[dict[str, Any]]) -> None:
        self._write_json(self.operator / "helper-outcomes.json", {
            "schema": managed_workspaces.OUTCOMES_SCHEMA,
            "workers": [{key: value for key, value in record.items() if key != "helper_acceptance"} for record in records],
        })

    def _write_acceptance(self, records: list[dict[str, Any]]) -> None:
        accepted = []
        for record in records:
            if record["state"] != "closed":
                continue
            accepted.append({
                "worker_id": record["worker_id"],
                "attempt_id": record["attempt_id"],
                "role": record["role"],
                "delivery_mode": record["delivery_mode"],
                "helper_receipt": record["helper_receipt"],
                "native_launch_reference": f"launch:{record['worker_id']}",
                "native_return_reference": f"return:{record['worker_id']}",
                "helper_acceptance": record["helper_acceptance"],
            })
        self._write_json(self.operator / "integration.patch", {"fixture": "patch integration evidence"})
        code = next(record for record in records if record["role"] == "code" and record["state"] == "closed")
        self._write_json(self.operator / "acceptance.json", {
            "schema": managed_workspaces.ACCEPTANCE_SCHEMA,
            "accepted": accepted,
            "integration": {"delivery_mode": code["delivery_mode"], "patch_evidence": str(self.operator / "integration.patch")},
        })

    def _identity(self, record: dict[str, Any]) -> dict[str, str]:
        return {
            "worker_id": record["worker_id"],
            "attempt_id": record["attempt_id"],
            "role": record["role"],
            "delivery_mode": record["delivery_mode"],
            "helper_receipt": record["helper_receipt"],
        }

    def _launch(self, record: dict[str, Any]) -> dict[str, Any]:
        host = self.manifest["host"]
        return {
            "kind": "native_launch",
            **self._identity(record),
            "native": {
                "host": host, "tool": HOST_TOOLS[host][0], "session_id": "parent-session",
                "task_id": f"task-{record['worker_id']}", "locator": f"launch:{record['worker_id']}",
                "terminal_state": "running", "cwd_binding": {
                    "mode": "native_spawn_cwd_argument" if host == "grok" else "explicit_operations",
                    "observed": host == "grok",
                },
            },
        }

    def _operation(self, record: dict[str, Any]) -> dict[str, Any]:
        root = Path(record["observed_git_root"])
        return {
            "kind": "operation",
            **self._identity(record),
            "operation": {"cwd": str(root / "reports"), "git_root": str(root), "locator": f"operation:{record['worker_id']}"},
        }

    def _returned(self, record: dict[str, Any], status: str = "success", route: str = "native_join") -> dict[str, Any]:
        terminal = "completed" if status == "success" else status
        host = self.manifest["host"]
        return {
            "kind": "native_return",
            **self._identity(record),
            "native": {
                "host": host, "tool": HOST_TOOLS[host][1], "session_id": "parent-session",
                "task_id": f"task-{record['worker_id']}", "locator": f"return:{record['worker_id']}",
                "terminal_state": terminal, "return_kind": route,
                "cwd_binding": {"mode": "unsupported", "observed": False},
            },
            "task_result": {"status": status},
        }

    def _accept_event(self, record: dict[str, Any]) -> dict[str, Any]:
        return {"kind": "parent_acceptance", **self._identity(record), "locator": f"accept:{record['worker_id']}", "helper_acceptance": record["helper_acceptance"]}

    def _cleanup(self, record: dict[str, Any]) -> dict[str, Any]:
        return {"kind": "cleanup", **self._identity(record), "locator": f"cleanup:{record['worker_id']}", "close": record["close"]}

    def _write_events(self, events: list[dict[str, Any]], schema: str | None = None) -> Path:
        path = self.operator / "public-native-events.json"
        self._write_json(path, {
            "schema": schema or managed_workspaces.EVENT_SCHEMA,
            "parent": {"host": self.manifest["host"], "session_id": "parent-session", "locator": "parent:1"},
            "events": events,
        })
        return path

    def _valid_records(self) -> list[dict[str, Any]]:
        code = self._attempt(role="code", attempt_id="code-a1", worker_id="native-code-a1", mode="patch")
        report = self._attempt(role="report", attempt_id="report-a1", worker_id="native-report-a1", mode="report-only")
        self._write_outcomes([code, report])
        self._write_acceptance([code, report])
        return [code, report]

    def _valid_events(self, code: dict[str, Any], report: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            self._launch(code), self._launch(report),
            {"kind": "parent_work", "parent": {"session_id": "parent-session", "locator": "parent:3"}, "description": "18 * 12.50 + 85 - 10"},
            self._operation(code), self._operation(report),
            self._returned(code), self._returned(report),
            self._accept_event(code), self._accept_event(report),
            self._cleanup(code), self._cleanup(report),
        ]

    def _validate(self, events: list[dict[str, Any]], schema: str | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        trace_path = self._write_events(events, schema)
        outcomes = managed_workspaces._outcome_validation(self.manifest, self.operator)
        acceptance = managed_workspaces._acceptance_validation(self.operator, outcomes["attempts"])
        trace = managed_workspaces._trace_v2_validation(self.manifest, self.operator, trace_path, outcomes, acceptance)
        return outcomes, acceptance, trace

    def test_valid_v2_trace_binds_real_receipts_archives_and_parent_work(self) -> None:
        code, report = self._valid_records()
        outcomes, acceptance, trace = self._validate(self._valid_events(code, report))
        self.assertTrue(outcomes["pass"], outcomes)
        self.assertTrue(acceptance["pass"], acceptance)
        self.assertTrue(trace["pass"], trace)
        self.assertEqual(trace["status"], "OBSERVED")
        self.assertEqual(set(trace["layers"]), set(managed_workspaces.TRACE_LAYER_KEYS))
        self.assertTrue(all(layer["pass"] for layer in trace["layers"].values()), trace)

    def test_all_hosts_share_the_normalized_lifecycle_contract(self) -> None:
        self.assertEqual(set(HOST_TOOLS), set(managed_workspaces.HOSTS))
        code, report = self._valid_records()
        # Immutable Git evidence can be shared; only disposable event records vary.
        # Both routes are valid at the shared contract layer, not a claim that
        # every installed host actually exposes both native return mechanisms.
        for host in managed_workspaces.HOSTS:
            self.manifest["host"] = host
            for route in ("automatic_notification", "native_join"):
                with self.subTest(host=host, route=route):
                    events = self._valid_events(code, report)
                    for event in events:
                        if event["kind"] == "native_return":
                            event["native"]["return_kind"] = route
                    _, _, trace = self._validate(events)
                    self.assertTrue(trace["pass"], trace)
                    self.assertTrue(all(layer["pass"] for layer in trace["layers"].values()), trace)

    def test_all_hosts_reject_context_and_async_collection_counterexamples(self) -> None:
        code, report = self._valid_records()
        mutations = {
            "missing_context": "operation_cwd_root_binding",
            "git_target_without_cwd": "operation_cwd_root_binding",
            "second_worktree": "operation_cwd_root_binding",
            "missing_return": "native_return",
            "duplicate_return": "native_return",
            "after_exit_resume": "native_return",
            "different_parent": "native_return",
            "work_before_launch": "parent_continuation",
            "work_after_return": "parent_continuation",
        }
        for host in managed_workspaces.HOSTS:
            self.manifest["host"] = host
            for mutation, layer in mutations.items():
                with self.subTest(host=host, mutation=mutation):
                    events = self._valid_events(code, report)
                    operation = next(e for e in events if e["kind"] == "operation")
                    returned = next(e for e in events if e["kind"] == "native_return")
                    if mutation == "missing_context":
                        events.remove(operation)
                    elif mutation == "git_target_without_cwd":
                        operation["operation"]["cwd"] = str(self.caller)
                    elif mutation == "second_worktree":
                        operation["operation"].update(cwd=report["observed_git_root"], git_root=report["observed_git_root"])
                    elif mutation == "missing_return":
                        events.remove(returned)
                    elif mutation == "duplicate_return":
                        events.insert(events.index(returned) + 1, copy.deepcopy(returned))
                    elif mutation == "after_exit_resume":
                        returned["native"]["return_kind"] = "after_exit_resume"
                    elif mutation == "different_parent":
                        returned["native"]["session_id"] = "later-parent-session"
                    else:
                        work = events.pop(2)
                        events.insert(0 if mutation == "work_before_launch" else len(events), work)
                    _, _, trace = self._validate(events)
                    self.assertFalse(trace["pass"], trace)
                    self.assertFalse(trace["layers"][layer]["pass"], trace)

    def test_grok_requires_native_cwd_even_with_correct_operation_context(self) -> None:
        self.manifest["host"] = "grok"
        code, report = self._valid_records()
        events = self._valid_events(code, report)
        events[0]["native"]["cwd_binding"]["observed"] = False
        _, _, trace = self._validate(events)
        self.assertFalse(trace["layers"]["native_launch"]["pass"], trace)
        self.assertTrue(trace["layers"]["operation_cwd_root_binding"]["pass"], trace)
        self.assertIn("Grok Build requires observed native cwd binding at launch", trace["errors"])

    def test_cancelled_retry_requires_confirmed_native_cancellation(self) -> None:
        cancelled = self._attempt(role="code", attempt_id="cancelled", worker_id="cancelled-worker", mode="patch", state="retained")
        code, report = self._valid_records()
        self._write_outcomes([cancelled, code, report])
        self._write_acceptance([cancelled, code, report])
        for host in managed_workspaces.HOSTS:
            self.manifest["host"] = host
            events = [
                self._launch(cancelled), self._launch(report),
                {"kind": "parent_work", "parent": {"session_id": "parent-session", "locator": "parent:3"}, "description": "parent calculation"},
                self._operation(cancelled), self._operation(report), self._returned(cancelled, "cancelled"),
                self._launch(code), self._operation(code), self._returned(report), self._returned(code),
                self._accept_event(report), self._accept_event(code), self._cleanup(report), self._cleanup(code),
            ]
            with self.subTest(host=host, terminal="cancelled"):
                _, _, trace = self._validate(events)
                self.assertTrue(trace["pass"], trace)
            for terminal in ("completed", "failed", "unknown", "blocked"):
                with self.subTest(host=host, terminal=terminal):
                    inconsistent = copy.deepcopy(events)
                    inconsistent[5]["native"]["terminal_state"] = terminal
                    _, _, trace = self._validate(inconsistent)
                    self.assertFalse(trace["pass"], trace)
                    self.assertTrue(any("without confirmed native cancellation" in e for e in trace["errors"]), trace)
        self.assertTrue(Path(cancelled["observed_git_root"]).is_dir())

    def test_parent_final_response_is_diagnosed_separately_from_task_lifecycle(self) -> None:
        code, report = self._valid_records()
        for host in managed_workspaces.HOSTS:
            self.manifest["host"] = host
            for mutation in ("missing", "completed", "failed", "different_parent", "no_locator", "early", "duplicate", "final_only"):
                with self.subTest(host=host, response=mutation):
                    events = self._valid_events(code, report)
                    final = {"kind": "parent_final", "parent": {"session_id": "parent-session", "locator": "parent:final"},
                             "status": "completed", "summary": "Both contributions accepted; workspaces closed."}
                    if mutation == "failed":
                        final["status"] = "failed"
                    elif mutation == "different_parent":
                        final["parent"]["session_id"] = "resumed-parent"
                    elif mutation == "no_locator":
                        final["parent"]["locator"] = ""
                    if mutation != "missing":
                        events.insert(3 if mutation == "early" else len(events), final)
                    if mutation == "duplicate":
                        events.append(copy.deepcopy(final))
                    elif mutation == "final_only":
                        events = [final]
                    _, _, trace = self._validate(events)
                    self.assertEqual(trace["pass"], mutation != "final_only", trace)
                    response = managed_workspaces._parent_final_validation(self.manifest, self.operator / "public-native-events.json")
                    expected = "UNOBSERVED" if mutation == "missing" else "PASS" if mutation in {"completed", "final_only"} else "FAIL"
                    self.assertEqual(response["status"], expected, response)
            path = self.operator / "public-native-events.json"
            payload = json.loads(path.read_text())
            del payload["parent"]["locator"]
            self._write_json(path, payload)
            self.assertEqual(managed_workspaces._parent_final_validation(self.manifest, path)["status"], "UNOBSERVED")

    def test_prompt_inspection_arguments_are_executed_by_the_real_helper(self) -> None:
        # _attempt executes this same builder, archives both reports, and closes
        # only after real helper inspection succeeds for patch and report-only.
        records = self._valid_records()
        package_run = self.root / "package path with spaces"
        for host in managed_workspaces.HOSTS:
            prompt = managed_workspaces.parent_prompt(package_run, host)
            commands = [shlex.split(line) for line in prompt.splitlines() if line.startswith("python3 ")]
            self.assertEqual(len(commands), 2)
            for record, command in zip(records, commands):
                self.assertEqual(command[:2], ["python3", str(package_run / "package/ask-agent/scripts/ask_agent_workspace.py")])
                self.assertEqual(command[2:], managed_workspaces.returned_inspection_args("REPLACE_WITH_WORKER_RECEIPT", record["role"]))
                self.assertEqual({row["path"] for row in record["artifacts"]}, set(managed_workspaces.EXPECTED_ARTIFACTS[record["role"]]))
        bad_args = managed_workspaces.returned_inspection_args(records[0]["helper_receipt"], "code")
        bad_args[bad_args.index("--artifact")] = "--report"
        rejected = subprocess.run([sys.executable, "-B", str(self.helper_path), *bad_args], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(rejected.returncode, 2)
        error = json.loads(rejected.stdout)
        self.assertEqual(error["status"], "error")
        self.assertIn("unrecognized arguments: --report", error["error"])

    def test_unrelated_profile_file_fails_caller_preservation_with_valid_returns(self) -> None:
        run = self._prepare_cli_run()
        self.manifest["host"] = "claude"
        self._write_json(self.operator / "manifest.json", self.manifest)
        code, report = self._valid_records()
        (self.caller / "pricing.json").write_text('{"currency":"USD","base_price":100,"discount_rate":0.10}\n', encoding="utf-8")
        pollution = self.caller / "tasks/in-progress/prompt-improvements-backlog.md"
        pollution.parent.mkdir(parents=True)
        pollution.write_text("unrequested profile output\n", encoding="utf-8")
        self._write_events(self._valid_events(code, report))
        result = subprocess.run([sys.executable, "-B", str(MODULE_PATH), "verify", "--run", str(run)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        verdict = json.loads(result.stdout)
        self.assertEqual(verdict["status"], "FAILED")
        layers = verdict["checks"]["lifecycle_layers"]
        self.assertFalse(layers["caller_preservation"]["pass"], layers)
        self.assertTrue(layers["native_return"]["pass"], layers)
        self.assertTrue(layers["operation_cwd_root_binding"]["pass"], layers)
        self.assertTrue(layers["reports_cleanup"]["pass"], layers)

    def test_failed_cancelled_blocked_and_unknown_returns_never_count_as_success(self) -> None:
        for status in ("failed", "cancelled", "blocked", "unknown"):
            with self.subTest(status=status):
                code, report = self._valid_records()
                events = self._valid_events(code, report)
                code_return = next(event for event in events if event.get("kind") == "native_return" and event.get("worker_id") == code["worker_id"])
                code_return["task_result"]["status"] = status
                code_return["native"]["terminal_state"] = status
                _, _, trace = self._validate(events)
                self.assertFalse(trace["pass"], trace)
                self.assertIn("role code must have exactly one successful task result", trace["errors"])
                self.assertTrue(trace["layers"]["native_launch"]["pass"], trace)
                self.assertTrue(trace["layers"]["operation_cwd_root_binding"]["pass"], trace)
                self.assertFalse(trace["layers"]["native_return"]["pass"], trace)

    def test_missing_return_keeps_correct_binding_visible(self) -> None:
        code, report = self._valid_records()
        events = self._valid_events(code, report)
        events = [
            event for event in events
            if not (
                event.get("kind") == "native_return"
                and event.get("worker_id") == code["worker_id"]
            )
        ]
        _, _, trace = self._validate(events)
        self.assertFalse(trace["pass"], trace)
        self.assertTrue(trace["layers"]["native_launch"]["pass"], trace)
        self.assertTrue(trace["layers"]["parent_continuation"]["pass"], trace)
        self.assertTrue(trace["layers"]["operation_cwd_root_binding"]["pass"], trace)
        self.assertFalse(trace["layers"]["native_return"]["pass"], trace)

    def test_layered_verdict_keeps_transport_passes_when_actual_cwd_is_wrong(self) -> None:
        run = self._prepare_cli_run()
        code, report = self._valid_records()
        (self.caller / "pricing.json").write_text(
            '{"currency":"USD","base_price":100,"discount_rate":0.10}\n',
            encoding="utf-8",
        )
        events = self._valid_events(code, report)
        code_operation = next(
            event for event in events
            if event.get("kind") == "operation"
            and event.get("worker_id") == code["worker_id"]
        )
        # This models Claude's failure mode: git operations can target the helper
        # worktree while the actual shell remains in the caller checkout.
        code_operation["operation"]["cwd"] = str(self.caller)
        self._write_events(events)
        output = self.operator / "verification-wrong-cwd.json"
        result = subprocess.run(
            [
                sys.executable, "-B", str(MODULE_PATH), "verify",
                "--run", str(run), "--events", str(self.operator / "public-native-events.json"),
                "--output", str(output),
            ],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(result.returncode, 1, f"stdout={result.stdout}\nstderr={result.stderr}")
        written = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(written["status"], "PARTIAL")
        layers = written["checks"]["lifecycle_layers"]
        for name in ("native_launch", "parent_continuation", "native_return", "caller_preservation", "delivery_acceptance", "reports_cleanup"):
            self.assertTrue(layers[name]["pass"], {name: layers[name], "all": layers})
        self.assertFalse(layers["operation_cwd_root_binding"]["pass"], layers)
        self.assertTrue(any("operation root/cwd" in error for error in layers["operation_cwd_root_binding"]["errors"]), layers)

    def test_after_exit_resume_is_distinguished_from_native_return_delivery(self) -> None:
        code, report = self._valid_records()
        events = self._valid_events(code, report)
        code_return = next(event for event in events if event.get("kind") == "native_return" and event.get("worker_id") == code["worker_id"])
        code_return["native"]["return_kind"] = "after_exit_resume"
        _, _, trace = self._validate(events)
        self.assertFalse(trace["pass"], trace)
        self.assertTrue(any("automatic notification or native join" in error for error in trace["errors"]), trace)

    def test_operation_root_swap_outside_and_shared_roots_are_rejected(self) -> None:
        for mutation in ("swap", "outside", "shared"):
            with self.subTest(mutation=mutation):
                code, report = self._valid_records()
                events = self._valid_events(code, report)
                if mutation == "swap":
                    next(event for event in events if event.get("kind") == "operation" and event.get("worker_id") == code["worker_id"])["operation"]["git_root"] = report["observed_git_root"]
                elif mutation == "outside":
                    operation = next(event for event in events if event.get("kind") == "operation" and event.get("worker_id") == code["worker_id"])["operation"]
                    operation["git_root"] = str(self.root / "outside")
                    operation["cwd"] = str(self.root / "outside")
                else:
                    outcomes = managed_workspaces._outcome_validation(self.manifest, self.operator)
                    code_key = (code["worker_id"], code["attempt_id"])
                    report_key = (report["worker_id"], report["attempt_id"])
                    outcomes["attempts"][report_key]["receipt"]["worktree"] = outcomes["attempts"][code_key]["receipt"]["worktree"]
                    acceptance = managed_workspaces._acceptance_validation(self.operator, outcomes["attempts"])
                    trace = managed_workspaces._trace_v2_validation(self.manifest, self.operator, self._write_events(events), outcomes, acceptance)
                    self.assertFalse(trace["pass"], trace)
                    self.assertTrue(any("share a helper worktree" in error for error in trace["errors"]), trace)
                    continue
                _, _, trace = self._validate(events)
                self.assertFalse(trace["pass"], trace)
                self.assertTrue(any("operation root/cwd" in error for error in trace["errors"]), trace)

    def test_missing_or_forged_receipt_cannot_bind_an_outcome(self) -> None:
        code, report = self._valid_records()
        Path(code["helper_receipt"]).unlink()
        outcomes, _, trace = self._validate(self._valid_events(code, report))
        self.assertFalse(outcomes["pass"], outcomes)
        self.assertFalse(trace["pass"], trace)

    def test_duplicate_task_and_wrong_worker_identity_are_rejected(self) -> None:
        code, report = self._valid_records()
        events = self._valid_events(code, report)
        report_launch = next(event for event in events if event.get("kind") == "native_launch" and event.get("worker_id") == report["worker_id"])
        report_launch["native"]["task_id"] = f"task-{code['worker_id']}"
        _, _, trace = self._validate(events)
        self.assertFalse(trace["pass"], trace)
        self.assertTrue(any("reuses native task id" in error for error in trace["errors"]), trace)

    def test_parent_work_and_cleanup_must_follow_the_full_lifecycle(self) -> None:
        code, report = self._valid_records()
        events = self._valid_events(code, report)
        parent_work = events.pop(2)
        events.insert(0, parent_work)
        cleanup = next(event for event in events if event.get("kind") == "cleanup" and event.get("worker_id") == code["worker_id"])
        events.remove(cleanup)
        code_return_index = next(index for index, event in enumerate(events) if event.get("kind") == "native_return" and event.get("worker_id") == code["worker_id"])
        events.insert(code_return_index + 1, cleanup)
        _, _, trace = self._validate(events)
        self.assertFalse(trace["pass"], trace)
        self.assertTrue(any("parent work" in error or "cleanup occurred" in error for error in trace["errors"]), trace)

    def test_fresh_retry_requires_new_worker_attempt_root_and_retained_failure_history(self) -> None:
        failed = self._attempt(role="code", attempt_id="code-a1", worker_id="native-code-a1", mode="patch", state="retained")
        code = self._attempt(role="code", attempt_id="code-a2", worker_id="native-code-a2", mode="patch")
        report = self._attempt(role="report", attempt_id="report-a1", worker_id="native-report-a1", mode="report-only")
        self._write_outcomes([failed, code, report])
        self._write_acceptance([failed, code, report])
        events = [
            self._launch(failed), self._launch(report),
            {"kind": "parent_work", "parent": {"session_id": "parent-session", "locator": "parent:3"}, "description": "parent calculation"},
            self._operation(failed), self._operation(report), self._returned(failed, "failed"),
            self._launch(code), self._operation(code), self._returned(report), self._returned(code),
            self._accept_event(report), self._accept_event(code), self._cleanup(report), self._cleanup(code),
        ]
        outcomes, acceptance, trace = self._validate(events)
        self.assertTrue(outcomes["pass"], outcomes)
        self.assertTrue(acceptance["pass"], acceptance)
        self.assertTrue(trace["pass"], trace)
        events[6]["worker_id"] = failed["worker_id"]
        events[6]["native"]["task_id"] = f"task-{failed['worker_id']}"
        _, _, rejected = self._validate(events)
        self.assertFalse(rejected["pass"], rejected)

    def test_fake_archived_report_bytes_cannot_pass_by_count(self) -> None:
        code, report = self._valid_records()
        archive = Path(code["artifacts"][0]["archive"])
        archive.chmod(0o644)
        archive.write_text("forged bytes\n", encoding="utf-8")
        outcomes, _, trace = self._validate(self._valid_events(code, report))
        self.assertFalse(outcomes["pass"], outcomes)
        self.assertFalse(trace["pass"], trace)

    def test_cleanup_before_acceptance_fails_the_reports_cleanup_layer(self) -> None:
        # Ordering: a workspace may be closed only after its return and its
        # parent acceptance, never between them.
        code, report = self._valid_records()
        for mutation in ("cleanup_before_acceptance", "acceptance_before_return"):
            with self.subTest(mutation=mutation):
                events = self._valid_events(code, report)
                if mutation == "cleanup_before_acceptance":
                    moved = next(event for event in events if event.get("kind") == "cleanup" and event.get("worker_id") == code["worker_id"])
                    anchor = next(event for event in events if event.get("kind") == "parent_acceptance" and event.get("worker_id") == code["worker_id"])
                else:
                    moved = next(event for event in events if event.get("kind") == "parent_acceptance" and event.get("worker_id") == code["worker_id"])
                    anchor = next(event for event in events if event.get("kind") == "native_return" and event.get("worker_id") == code["worker_id"])
                events.remove(moved)
                events.insert(events.index(anchor), moved)
                _, _, trace = self._validate(events)
                self.assertFalse(trace["pass"], trace)
                self.assertFalse(trace["layers"]["reports_cleanup"]["pass"], trace)
                self.assertTrue(trace["layers"]["native_return"]["pass"], trace)
                self.assertTrue(any("cleanup occurred before completed acceptance" in error for error in trace["errors"]), trace)

    def test_archived_reports_must_be_exact_regular_files_inside_helper_results(self) -> None:
        # Archival: count-matching is not enough; each report must be a regular
        # file at its own path under the attempt's durable results directory.
        for mutation, message in (
            ("symlinked_archive", "archived report must not be a symlink"),
            ("archive_outside_results", "archived report path escapes the helper durable results directory"),
            ("missing_detail_report", "close evidence does not archive the exact required report artifacts"),
        ):
            with self.subTest(mutation=mutation):
                code, report = self._valid_records()
                close_path = Path(code["close"])
                close = json.loads(close_path.read_text(encoding="utf-8"))
                row = close["archived_artifacts"][0]
                archive = Path(row["archive"])
                outside = self.root / f"outside-{mutation}.md"
                outside.write_bytes(archive.read_bytes())
                if mutation == "symlinked_archive":
                    archive.chmod(0o644)
                    archive.unlink()
                    archive.symlink_to(outside)
                else:
                    if mutation == "archive_outside_results":
                        row["archive"] = str(outside)
                    else:
                        close["archived_artifacts"] = [
                            item for item in close["archived_artifacts"]
                            if item.get("path", item.get("source")) == "reports/handoff-index.md"
                        ]
                    close_path.chmod(0o644)
                    self._write_json(close_path, close)
                outcomes, _, trace = self._validate(self._valid_events(code, report))
                self.assertFalse(outcomes["pass"], outcomes)
                self.assertTrue(any(message in error for error in outcomes["errors"]), outcomes)
                self.assertFalse(trace["pass"], trace)

    def test_verdict_never_copies_trace_payload_text(self) -> None:
        # Redaction: the durable verdict records identities, paths and layer
        # results only; parent prose and host payload text stay in the trace.
        run = self._prepare_cli_run()
        code, report = self._valid_records()
        (self.caller / "pricing.json").write_text('{"currency":"USD","base_price":100,"discount_rate":0.10}\n', encoding="utf-8")
        markers = {
            "parent_work": "PRIVATE-PARENT-WORK-7c1e",
            "launch_prompt": "PRIVATE-LAUNCH-PROMPT-7c1e",
            "return_output": "PRIVATE-RETURN-OUTPUT-7c1e",
            "reasoning": "PRIVATE-REASONING-7c1e",
            "parent_final": "PRIVATE-PARENT-FINAL-7c1e",
        }
        events = self._valid_events(code, report)
        next(event for event in events if event["kind"] == "parent_work")["description"] = markers["parent_work"]
        for event in events:
            if event["kind"] == "native_launch":
                event["native"]["prompt"] = markers["launch_prompt"]
            elif event["kind"] == "native_return":
                event["native"]["output"] = markers["return_output"]
                event["native"]["reasoning"] = markers["reasoning"]
        events.append({"kind": "parent_final", "parent": {"session_id": "parent-session", "locator": "parent:final"},
                       "status": "completed", "summary": markers["parent_final"]})
        self._write_events(events)
        output = self.operator / "verification-redaction.json"
        result = subprocess.run(
            [sys.executable, "-B", str(MODULE_PATH), "verify", "--run", str(run), "--output", str(output)],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(result.returncode, 0, f"stdout={result.stdout}\nstderr={result.stderr}")
        written = output.read_text(encoding="utf-8")
        self.assertEqual(json.loads(written)["status"], "COMPLETE")
        self.assertEqual(json.loads(written)["checks"]["parent_final_response"]["status"], "PASS")
        for name, marker in markers.items():
            with self.subTest(field=name):
                self.assertNotIn(marker, written)
                self.assertNotIn(marker, result.stdout)
                self.assertNotIn(marker, result.stderr)

    def test_non_v2_event_trace_is_refused_as_unobserved(self) -> None:
        code, report = self._valid_records()
        for schema in ("ask-agent-managed-workspaces.events.v1", "ask-agent-managed-workspaces.events.v3"):
            with self.subTest(schema=schema):
                _, _, trace = self._validate(self._valid_events(code, report), schema)
                self.assertFalse(trace["pass"], trace)
                self.assertEqual(trace["status"], "UNOBSERVED")
                self.assertEqual(trace["errors"], [f"public event trace must use {managed_workspaces.EVENT_SCHEMA}"])

    def test_manifest_schema_must_be_current(self) -> None:
        run = self._prepare_cli_run()
        manifest_path = self.operator / "manifest.json"
        current = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(current["schema"], managed_workspaces.SCHEMA)
        self.assertEqual(managed_workspaces.load_manifest(manifest_path), current)
        without_head = {key: value for key, value in current.items() if key != "source_head"}
        cases = (
            ("v1 manifest", {**current, "schema": "ask-agent-managed-workspaces.v1"}, "fixture manifest must use ask-agent-managed-workspaces.v2"),
            ("unversioned manifest", {key: value for key, value in current.items() if key != "schema"}, "fixture manifest must use ask-agent-managed-workspaces.v2"),
            ("manifest without source_head", without_head, "fixture manifest lacks source_head"),
        )
        for index, (name, manifest, message) in enumerate(cases):
            with self.subTest(name=name):
                self._write_json(manifest_path, manifest)
                with self.assertRaisesRegex(managed_workspaces.ContractError, message):
                    managed_workspaces.load_manifest(manifest_path)
                output = self.operator / f"verification-refused-{index}.json"
                result = subprocess.run(
                    [sys.executable, "-B", str(MODULE_PATH), "verify", "--run", str(run), "--output", str(output)],
                    cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
                )
                self.assertEqual(result.returncode, 2, f"stdout={result.stdout}\nstderr={result.stderr}")
                self.assertEqual(result.stdout, "")
                error = json.loads(result.stderr)
                self.assertEqual(error["status"], "CONTRACT_ERROR")
                self.assertIn(message, error["error"])
                self.assertFalse(output.exists())

    def test_receipt_uses_immutable_baseline_head_after_parent_head_advances(self) -> None:
        initial_head = self._git(self.caller, "rev-parse", "HEAD").strip()
        self.manifest["source_head"] = initial_head
        code, report = self._valid_records()
        (self.caller / "parent-follow-up.txt").write_text("parent commit after worker preparation\n", encoding="utf-8")
        self._git(self.caller, "add", "parent-follow-up.txt")
        self._git(self.caller, "commit", "-q", "-m", "parent integration commit")
        self.assertNotEqual(self._git(self.caller, "rev-parse", "HEAD").strip(), initial_head)
        outcomes = managed_workspaces._outcome_validation(self.manifest, self.operator)
        self.assertTrue(outcomes["pass"], outcomes)
        self.assertEqual({record["worker_id"] for record in outcomes["attempts"].values()}, {code["worker_id"], report["worker_id"]})

    def test_opencode_is_a_declared_host_and_uses_persistent_tui_guidance(self) -> None:
        self.assertIn("opencode", managed_workspaces.HOSTS)
        prompt = managed_workspaces.parent_prompt(self.root, "opencode")
        self.assertIn("OpenCode qualification uses its persistent TUI", prompt)
        self.assertIn("current opencode route in Host capabilities", prompt)
        self.assertIn("check-context command", prompt)
        self.assertIn("git -C target is not an operation-directory check", prompt)
        self.assertIn("--delivery-mode patch", prompt)
        self.assertIn("--delivery-mode report-only", prompt)

    def test_verify_cli_writes_a_parseable_complete_v2_verdict_from_real_helper_evidence(self) -> None:
        run = self._prepare_cli_run()
        code, report = self._valid_records()
        (self.caller / "pricing.json").write_text('{"currency":"USD","base_price":100,"discount_rate":0.10}\n', encoding="utf-8")
        self._write_events(self._valid_events(code, report))
        output = self.operator / "verification-e2e.json"
        result = subprocess.run(
            [sys.executable, "-B", str(MODULE_PATH), "verify", "--run", str(run), "--events", str(self.operator / "public-native-events.json"), "--output", str(output)],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(result.returncode, 0, f"stdout={result.stdout}\nstderr={result.stderr}")
        stdout = json.loads(result.stdout)
        written = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(stdout["status"], "COMPLETE")
        self.assertEqual(written["status"], "COMPLETE")
        self.assertEqual(written["checks"]["parent_final_response"]["status"], "UNOBSERVED")
        self.assertIsInstance(written["checks"]["helper_receipts_and_outcomes"]["attempts"], list)
        self.assertIsInstance(written["checks"]["acceptance"]["accepted"], list)
        layers = written["checks"]["lifecycle_layers"]
        self.assertEqual(
            set(layers),
            {
                "native_launch",
                "parent_continuation",
                "native_return",
                "operation_cwd_root_binding",
                "caller_preservation",
                "delivery_acceptance",
                "reports_cleanup",
            },
        )
        self.assertTrue(all(layer["pass"] for layer in layers.values()), layers)
        repeated = subprocess.run(
            [sys.executable, "-B", str(MODULE_PATH), "verify", "--run", str(run), "--events", str(self.operator / "public-native-events.json"), "--output", str(output)],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(repeated.returncode, 2, f"stdout={repeated.stdout}\nstderr={repeated.stderr}")
        self.assertEqual(json.loads(repeated.stderr)["status"], "CONTRACT_ERROR")

    def test_verify_cli_failure_still_emits_parseable_json(self) -> None:
        run = self._prepare_cli_run()
        output = self.operator / "verification-missing-evidence.json"
        result = subprocess.run(
            [sys.executable, "-B", str(MODULE_PATH), "verify", "--run", str(run), "--output", str(output)],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(result.returncode, 1, f"stdout={result.stdout}\nstderr={result.stderr}")
        stdout = json.loads(result.stdout)
        written = json.loads(output.read_text(encoding="utf-8"))
        self.assertIn(stdout["status"], {"PARTIAL", "FAILED"})
        self.assertEqual(stdout["status"], written["status"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
