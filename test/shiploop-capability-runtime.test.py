#!/usr/bin/env python3
"""Focused, host-independent regressions for the capability experiment runtime.

The real macOS sandbox lifecycle canary is intentionally an explicit operator
command.  These checks exercise the portable ledger, sanitizer, collector, and
state-backed receipt semantics without an account, model invocation, or host
sandbox dependency.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "test" / "experiments" / "shiploop_capabilities"


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, EXPERIMENTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gateway = load_module("shiploop_capability_runtime_gateway", "gateway.py")
runner = load_module("shiploop_capability_runtime_runner", "run_trials.py")
collector = load_module("shiploop_capability_runtime_collector", "collect_blind.py")
preparer = load_module("shiploop_capability_runtime_preparer", "prepare.py")


def gateway_payload(response: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    content = response.get("content")
    assert isinstance(content, list) and content and isinstance(content[0], dict)
    text = content[0].get("text")
    assert isinstance(text, str)
    parsed = json.loads(text)
    assert isinstance(parsed, dict)
    return parsed, bool(response.get("isError"))


def completed_event(arguments: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "item.completed",
        "item": {
            "type": "mcp_tool_call",
            "status": "completed",
            "arguments": arguments,
            "result": {"content": [{"type": "text", "text": json.dumps(payload)}]},
        },
    }


class CapabilityRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="shiploop-capability-runtime-")
        self.base = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def gateway_args(self, workspace: Path, ledger: Path, log: Path, *, call_limit: int = 8) -> argparse.Namespace:
        now = time.time()
        return argparse.Namespace(
            workspace=workspace,
            ledger=ledger,
            log=log,
            config=None,
            start_epoch=now,
            cutoff_epoch=now + 30,
            deadline_epoch=now + 60,
            call_limit=call_limit,
            exploration_limit=call_limit,
        )

    def test_gateway_rejects_external_and_symlink_paths_and_receipt_target_inside_workspace(self) -> None:
        workspace = self.base / "workspace"
        workspace.mkdir()
        external = self.base / "private-canary.txt"
        external.write_text("never expose\n", encoding="utf-8")
        (workspace / "outside-link").symlink_to(external)
        instance = gateway.Gateway(self.gateway_args(workspace, self.base / "ledger.json", self.base / "gateway.jsonl"))
        try:
            rejected, rejected_error = gateway_payload(instance.call({
                "name": "workspace", "arguments": {"operation": "read", "path": str(external)}
            }))
            self.assertTrue(rejected_error)
            self.assertIn("stay below", rejected["error"])
            linked, linked_error = gateway_payload(instance.call({
                "name": "workspace", "arguments": {"operation": "read", "path": "outside-link"}
            }))
            self.assertTrue(linked_error)
            self.assertIn("symbolic links", linked["error"])
            with self.assertRaises(ValueError):
                runner.child_environment(workspace, service_receipts=workspace / "service-http-receipts.jsonl")
        finally:
            instance.close()

    def test_two_gateway_processes_share_one_budget_without_persisting_request_identifiers(self) -> None:
        workspace = self.base / "workspace"
        workspace.mkdir()
        ledger, log_a, log_b = self.base / "ledger.json", self.base / "a.jsonl", self.base / "b.jsonl"
        now = time.time()

        def command(log: Path) -> list[str]:
            return [
                sys.executable, str(EXPERIMENTS / "gateway.py"),
                "--workspace", str(workspace), "--ledger", str(ledger), "--log", str(log),
                "--start-epoch", str(now), "--cutoff-epoch", str(now + 30), "--deadline-epoch", str(now + 60),
                "--call-limit", "4", "--exploration-limit", "4",
            ]

        processes = [
            subprocess.Popen(command(log), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for log in (log_a, log_b)
        ]

        def call(proc: subprocess.Popen[str], request_id: str) -> dict[str, Any]:
            assert proc.stdin and proc.stdout
            proc.stdin.write(json.dumps({
                "jsonrpc": "2.0", "id": request_id, "method": "tools/call",
                "params": {"name": "workspace", "arguments": {"operation": "list"}},
            }) + "\n")
            proc.stdin.flush()
            response = json.loads(proc.stdout.readline())
            return response["result"]

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                first = list(pool.map(lambda pair: call(*pair), zip(processes, ("caller-id-101", "caller-id-202"))))
                second = list(pool.map(lambda pair: call(*pair), zip(processes, ("caller-id-303", "caller-id-404"))))
            self.assertTrue(all(not response.get("isError") for response in first + second))
            denied = call(processes[0], "caller-id-505")
            self.assertTrue(denied.get("isError"))
        finally:
            for proc in processes:
                if proc.stdin and not proc.stdin.closed:
                    proc.stdin.close()
                proc.wait(timeout=10)
                if proc.stdout:
                    proc.stdout.close()
                if proc.stderr:
                    proc.stderr.close()
        state = json.loads(ledger.read_text(encoding="utf-8"))
        records = state["records"]
        self.assertEqual(state["tool_calls"], 4)
        self.assertEqual([row["call"] for row in records], [1, 2, 3, 4])
        self.assertTrue(all(not any("request_id" in key for key in row) for row in records))
        self.assertNotIn("caller-id-", ledger.read_text(encoding="utf-8"))

    def test_event_redaction_preserves_safe_structure_and_usage_without_code_or_output_bodies(self) -> None:
        secret = "super-secret-token-value"
        event = completed_event(
            {"operation": "exec", "argv": ["python3", "-c", f"print('token={secret}'); shiploop complete"]},
            {"exit_code": 0, "stdout": f"authorization={secret}", "input_tokens": 17, "output_tokens": 4, "cached_input_tokens": 3},
        )
        event["item"]["usage"] = {"input_tokens": 21, "output_tokens": 8, "cached_input_tokens": 5}
        sanitized = runner.redacted(event)
        rendered = json.dumps(sanitized, sort_keys=True)
        self.assertNotIn(secret, rendered)
        self.assertNotIn("shiploop complete", rendered)
        metadata = sanitized["item"]["arguments"]["argv_metadata"]
        self.assertEqual(metadata["execution_path"], "python_wrapper_cli")
        payload = sanitized["item"]["result"]["content"][0]["text"]
        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(payload["stdout"], "<redacted-body>")
        self.assertEqual(payload["input_tokens"], 17)
        self.assertEqual(sanitized["item"]["usage"]["input_tokens"], 21)

    def test_blind_accounting_keeps_note_report_and_cli_metadata_body_free(self) -> None:
        workspace = self.base / "workspace"
        workspace.mkdir()
        study = self.base / "study"
        study.mkdir()
        secret = "credential-body-must-not-escape"
        events = [
            completed_event({"operation": "read", "path": "PHASE1_NOTE.md"}, {"bytes": 12, "call": 1}),
            completed_event({"operation": "write", "path": "PHASE1_NOTE.md", "content": secret}, {"bytes": 12, "call": 2}),
            completed_event({"operation": "read", "path": "REPORT.md"}, {"bytes": 12, "call": 3}),
            completed_event({"operation": "write", "path": "REPORT.md", "content": secret}, {"bytes": 12, "call": 4}),
            completed_event(
                {"operation": "exec", "argv": ["python3", "/fixture/shiploop", "complete", "--action=nav-1"]},
                {"exit_code": 0, "stdout": f"token={secret}", "input_tokens": 9, "output_tokens": 2, "cached_input_tokens": 1},
            ),
        ]
        wrapped = completed_event(
            {"operation": "exec", "argv": ["python3", "-c", f"# {secret}\nsubprocess.run(['shiploop', 'complete'])"]},
            {"exit_code": 0, "stdout": f"token={secret}"},
        )
        events.append(runner.redacted(wrapped))
        event_path = self.base / "events.jsonl"
        event_path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
        redactor = collector.Redactor(study, [], workspace)
        payload, errors = collector.collect_event_stream(event_path, context=1, redactor=redactor)
        self.assertFalse(errors)
        accounting = payload["action_accounting"]
        self.assertEqual(accounting["completed_tool_actions"], 6)
        self.assertEqual(accounting["by_operation"], {"read": 2, "write": 2, "exec": 2})
        documents = [row for row in payload["receipts"] if row.get("record_class") == "worker_document"]
        self.assertEqual({(row["operation"], row["path_basename"]) for row in documents}, {
            ("read", "PHASE1_NOTE.md"), ("write", "PHASE1_NOTE.md"),
            ("read", "REPORT.md"), ("write", "REPORT.md"),
        })
        cli = [row for row in payload["receipts"] if row.get("operation") == "local_cli_handoff"]
        self.assertEqual({row["execution_path"] for row in cli}, {"direct_cli", "python_wrapper_cli"})
        self.assertTrue(all(row["acceptance_basis"] == "not_established_by_command_receipt" for row in cli))
        self.assertTrue(all("reported_accepted_transition" not in row for row in cli))
        direct = next(row for row in cli if row["execution_path"] == "direct_cli")
        self.assertEqual(direct["result_metadata"]["input_tokens"], 9)
        self.assertNotIn(secret, json.dumps(payload, sort_keys=True))

    def test_authoritative_http_receipt_retains_actor_status_when_exec_is_wholly_redacted(self) -> None:
        workspace = self.base / "workspace"
        workspace.mkdir()
        study = self.base / "study"
        study.mkdir()
        redactor = collector.Redactor(study, [], workspace)
        event_path = self.base / "events.jsonl"
        event_path.write_text(json.dumps(completed_event(
            {"operation": "exec", "argv": "<redacted>", "argv_metadata": {"execution_path": "python_wrapper_cli", "cli_verb": "complete", "argc": 3}},
            {"exit_code": 0, "stdout": "<redacted-body>"},
        )) + "\n", encoding="utf-8")
        tool_payload, tool_errors = collector.collect_event_stream(event_path, context=1, redactor=redactor)
        self.assertFalse(tool_errors)
        self.assertEqual(tool_payload["receipts"][0]["acceptance_basis"], "not_established_by_command_receipt")
        receipts = self.base / "service-http-receipts.jsonl"
        receipts.write_text(
            json.dumps({
                "event": "http_request", "receipt_id": "http-000001", "method": "POST", "route": "/api/move",
                "actor_class": "red", "status": 403, "error": "scope_required", "version_before": 1, "version_after": 1,
            }) + "\n" + json.dumps({"event": "http_request", "secret": "must-not-escape"}) + "\n",
            encoding="utf-8",
        )
        service_payload, service_errors = collector.collect_service_http_receipts(receipts)
        self.assertEqual(service_payload["status"], "present")
        self.assertEqual(service_payload["receipts"][0]["actor_class"], "red")
        self.assertEqual(service_payload["receipts"][0]["status"], 403)
        self.assertEqual(len(service_errors), 1)
        self.assertNotIn("must-not-escape", json.dumps(service_payload, sort_keys=True))

    def test_service_http_receipts_enforce_semantics_without_causal_inference(self) -> None:
        def receipt(receipt_id: str, *, status: int, error: str | None, before: int | None, after: int | None) -> dict[str, Any]:
            return {
                "event": "http_request", "receipt_id": receipt_id, "method": "POST", "route": "/api/move",
                "actor_class": "red", "status": status, "error": error,
                "version_before": before, "version_after": after,
            }

        self.assertIsNone(collector.valid_service_http_receipt(receipt(
            "http-000001", status=200, error="scope_required", before=1, after=1,
        )))
        self.assertIsNone(collector.valid_service_http_receipt(receipt(
            "http-000002", status=403, error=None, before=1, after=1,
        )))
        self.assertIsNone(collector.valid_service_http_receipt(receipt(
            "http-000003", status=403, error="unrecognized_error", before=1, after=1,
        )))
        extra = receipt("http-000004", status=403, error="scope_required", before=1, after=1)
        extra["untrusted"] = "extra"
        self.assertIsNone(collector.valid_service_http_receipt(extra))
        malformed = receipt("http-000005", status=403, error="scope_required", before=1, after=1)
        del malformed["error"]
        self.assertIsNone(collector.valid_service_http_receipt(malformed))

        receipts = self.base / "service-http-receipts.jsonl"
        receipts.write_text(
            "\n".join(json.dumps(value) for value in (
                receipt("http-000006", status=200, error=None, before=None, after=None),
                # These two observations can overlap; their differing versions do not identify either request's effect.
                receipt("http-000007", status=200, error=None, before=4, after=6),
                receipt("http-000008", status=403, error="scope_required", before=5, after=6),
            )) + "\n",
            encoding="utf-8",
        )
        payload, errors = collector.collect_service_http_receipts(receipts)
        self.assertFalse(errors)
        self.assertEqual(payload["status"], "present")
        self.assertEqual([row["receipt_id"] for row in payload["receipts"]], [
            "http-000006", "http-000007", "http-000008",
        ])
        self.assertTrue(all(set(row) == collector.SERVICE_HTTP_RECEIPT_KEYS for row in payload["receipts"]))
        limits = " ".join(payload["observation_limits"])
        self.assertIn("null means unresolved", limits)
        self.assertIn("concurrent requests", limits)
        self.assertIn("do not establish a causal state effect", limits)
        self.assertNotIn("specific_worker_action", json.dumps(payload, sort_keys=True))

    def test_state_backed_lifecycle_receipt_requires_persisted_expected_action(self) -> None:
        workspace = self.base / "workspace"
        state_path = workspace / "shiploop-state" / "state.md"
        state_path.parent.mkdir(parents=True)

        def write_state(value: dict[str, Any]) -> None:
            state_path.write_text(
                "# navigator\n\n```shiploop-state\n" + json.dumps(value, sort_keys=True) + "\n```\n",
                encoding="utf-8",
            )

        write_state({"action": {"id": "nav-1"}, "revision": 3, "accepted": {}, "history": []})
        baseline = runner.lifecycle_baseline(workspace)
        self.assertIsNotNone(baseline)
        write_state({
            "action": {"id": "nav-2"}, "revision": 4,
            "accepted": {"nav-1": {"outcome": "done", "summary": "safe"}},
            "history": [{"action": "nav-1"}],
        })
        receipt = runner.state_backed_lifecycle_receipt(workspace, baseline)
        self.assertEqual(receipt["status"], "accepted")
        self.assertTrue(receipt["state_backed"])

    def test_freeze_runtime_writes_versioned_snapshot_and_refuses_reuse(self) -> None:
        study = self.base / "fresh-study"
        receipt = preparer.freeze_runtime(study)
        runtime = Path(receipt["runtime"])
        self.assertEqual(receipt["runtime_version"], "shiploop-capability-runtime-v3")
        self.assertTrue((runtime / "gateway.py").is_file())
        self.assertTrue((runtime / "runtime_validation.py").is_file())
        self.assertTrue((runtime / "shiploop" / "scripts" / "shiploop").is_file())
        metadata = json.loads((runtime / "runtime-manifest.json").read_text(encoding="utf-8"))
        self.assertIn("shiploop/scripts/shiploop", metadata["files"])
        with self.assertRaises(RuntimeError):
            preparer.freeze_runtime(study)

    def test_frozen_entrypoints_do_not_create_bytecode_caches(self) -> None:
        runtime = Path(preparer.freeze_runtime(self.base / "fresh-study")["runtime"])
        environment = os.environ.copy()
        environment.pop("PYTHONDONTWRITEBYTECODE", None)
        for entrypoint in ("prepare.py", "run_trials.py"):
            completed = subprocess.run(
                [sys.executable, str(runtime / entrypoint), "--help"],
                text=True,
                capture_output=True,
                env=environment,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(any(path.name == "__pycache__" for path in runtime.rglob("*")))

    def test_prepared_arm_rejects_rehashed_runtime_manifest(self) -> None:
        study = self.base / "prepared-study"
        runtime = Path(preparer.freeze_runtime(study)["runtime"])
        arm = study / "arms" / "pinned"
        arm.mkdir(parents=True)
        original_pin = runner.sha256(runtime / "runtime-manifest.json")
        (arm / "input-manifest.json").write_text(
            json.dumps({"runtime_manifest_sha256": original_pin}), encoding="utf-8"
        )
        self.assertEqual(runner.verify_arm_runtime_manifest_pin(study, "pinned", runtime), original_pin)

        changed = runtime / "gateway.py"
        changed.write_text(changed.read_text(encoding="utf-8") + "\n# rehashed mutation\n", encoding="utf-8")
        manifest = runtime / "runtime-manifest.json"
        metadata = json.loads(manifest.read_text(encoding="utf-8"))
        metadata["files"]["gateway.py"] = runner.sha256(changed)
        manifest.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        self.assertEqual(runner.runtime_directory(study).resolve(), runtime.resolve())
        with self.assertRaises(ValueError):
            runner.verify_arm_runtime_manifest_pin(study, "pinned", runtime)
        outcome = runner.run_arm(
            study,
            "pinned",
            deadline_seconds=180,
            no_new_trials_epoch=None,
            hard_deadline_epoch=None,
            preflight_status="verified",
        )
        self.assertEqual(outcome, {"arm": "pinned", "status": "not_started_runtime_manifest_pin_mismatch"})

    def test_runtime_snapshot_rejects_tampering_and_unsafe_tree_entries(self) -> None:
        def rejected(mutator) -> None:
            study = self.base / f"study-{len(list(self.base.iterdir()))}"
            runtime = Path(preparer.freeze_runtime(study)["runtime"])
            mutator(runtime)
            with self.assertRaises(RuntimeError):
                preparer.runtime_snapshot(study)
            with self.assertRaises(ValueError):
                runner.runtime_directory(study)

        rejected(lambda runtime: (runtime / "runtime_validation.py").write_text("tampered\n", encoding="utf-8"))
        rejected(lambda runtime: (runtime / "unlisted.py").write_text("unexpected\n", encoding="utf-8"))
        rejected(lambda runtime: (runtime / "__pycache__").mkdir())

        def unsafe_manifest_path(runtime: Path) -> None:
            manifest = runtime / "runtime-manifest.json"
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["files"]["../outside.py"] = "0" * 64
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

        rejected(unsafe_manifest_path)

        def symlink_component(runtime: Path) -> None:
            scripts = runtime / "shiploop" / "scripts"
            detached = self.base / "detached-shiploop-scripts"
            scripts.rename(detached)
            scripts.symlink_to(detached, target_is_directory=True)

        rejected(symlink_component)
        rejected(lambda runtime: (runtime / "shiploop" / "SKILL.md").unlink())


if __name__ == "__main__":
    unittest.main(verbosity=2)
