#!/usr/bin/env python3
"""Hermetic contract tests for the optional Claude host transport."""

from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))

from shiploop_host import HostError  # noqa: E402
from shiploop_host_claude import ClaudeTransport  # noqa: E402


PROBE_SPEC = importlib.util.spec_from_file_location(
    "production_claude_probe",
    ROOT / "test/experiments/shiploop_context_reset/production-claude/probe.py",
)
probe = importlib.util.module_from_spec(PROBE_SPEC)
assert PROBE_SPEC.loader is not None
PROBE_SPEC.loader.exec_module(probe)


THREAD_A = "10000000-0000-4000-8000-000000000001"
THREAD_B = "10000000-0000-4000-8000-000000000002"
TURN_A = "20000000-0000-4000-8000-000000000001"


def response(*, session_id=THREAD_A, result="OK", is_error=False, subtype="success", usage=None):
    payload = {
        "session_id": session_id,
        "uuid": TURN_A,
        "result": result,
        "is_error": is_error,
        "subtype": subtype,
    }
    if usage is not None:
        payload["usage"] = usage
    return subprocess.CompletedProcess(
        args=["claude"], returncode=0, stdout=json.dumps(payload), stderr=""
    )


class ClaudeTransportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="shiploop-host-claude-")
        self.root = Path(self.temporary.name).resolve()

    def tearDown(self):
        self.temporary.cleanup()

    def test_rejects_sandbox_requests_the_claude_cli_cannot_enforce(self):
        with self.assertRaisesRegex(HostError, "writable roots"):
            ClaudeTransport(self.root, writable_roots=[self.root])
        with self.assertRaisesRegex(HostError, "network denial"):
            ClaudeTransport(self.root, network_access=False)
        with ClaudeTransport(self.root) as host:
            self.assertEqual(host.permission_metadata["mode"], "existing-native-claude-cli-permissions")
            self.assertFalse(host.permission_metadata["enforced_network_access"])
            self.assertEqual(host.capabilities["fresh_context"], "new-session-id")

    @patch("shiploop_host_claude.uuid.uuid4", return_value=uuid.UUID(THREAD_A))
    @patch("shiploop_host_claude.subprocess.run")
    def test_new_session_then_retained_turn_uses_session_id_then_resume(self, run, _uuid4):
        run.side_effect = [
            response(usage={"input_tokens": 3}),
            response(result="RETAINED", usage={"input_tokens": 5}),
        ]
        with ClaudeTransport(self.root, timeout=12) as host:
            thread = host.start_thread(self.root)
            first = host.run_turn(thread, "remember test value")
            second = host.run_turn(thread, "recall it")

        self.assertEqual(thread, THREAD_A)
        self.assertEqual(first["status"], "completed")
        self.assertEqual(second["text"], "RETAINED")
        self.assertEqual(second["usage"], {"input_tokens": 5})
        self.assertEqual(run.call_count, 2)
        first_argv = run.call_args_list[0].args[0]
        second_argv = run.call_args_list[1].args[0]
        self.assertEqual(first_argv[-2:], ["--session-id", THREAD_A])
        self.assertEqual(second_argv[-2:], ["--resume", THREAD_A])
        for argv in (first_argv, second_argv):
            self.assertNotIn("--bare", argv)
            self.assertNotIn("--dangerously-skip-permissions", argv)
            self.assertNotIn("--permission-mode", argv)
        call_kwargs = run.call_args_list[0].kwargs
        self.assertEqual(call_kwargs["cwd"], str(self.root))
        self.assertEqual(call_kwargs["env"]["SHIPLOOP_CONTEXT_HOST_WORKER"], "1")

    @patch("shiploop_host_claude.subprocess.run", return_value=response(session_id=THREAD_B, result="RESUMED"))
    def test_resume_preserves_supplied_session_identity(self, run):
        with ClaudeTransport(self.root) as host:
            self.assertEqual(host.resume_thread(THREAD_B), THREAD_B)
            result = host.run_turn(THREAD_B, "continue")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(run.call_args.args[0][-2:], ["--resume", THREAD_B])

    @patch("shiploop_host_claude.uuid.uuid4", return_value=uuid.UUID(THREAD_A))
    @patch("shiploop_host_claude.subprocess.run", return_value=response(session_id=THREAD_B))
    def test_session_identity_mismatch_is_a_failed_owner(self, run, _uuid4):
        with ClaudeTransport(self.root) as host:
            result = host.run_turn(host.start_thread(self.root), "one owner")
        self.assertEqual(result["status"], "failed")
        self.assertIn("different session identity", result["error"])
        self.assertEqual(result["thread_id"], THREAD_A)

    @patch("shiploop_host_claude.uuid.uuid4", return_value=uuid.UUID(THREAD_A))
    @patch("shiploop_host_claude.subprocess.run")
    def test_malformed_and_timeout_results_are_failed_without_replay(self, run, _uuid4):
        run.side_effect = [
            subprocess.CompletedProcess(args=["claude"], returncode=0, stdout="not json", stderr="bad output"),
            subprocess.TimeoutExpired(cmd=["claude"], timeout=1),
        ]
        with ClaudeTransport(self.root, timeout=1) as host:
            thread = host.start_thread(self.root)
            malformed = host.run_turn(thread, "first")
            timed_out = host.run_turn(thread, "second")
        self.assertEqual(malformed["status"], "failed")
        self.assertEqual(malformed["error"], "bad output")
        self.assertEqual(timed_out["status"], "failed")
        self.assertIn("do not automatically replay", timed_out["error"])
        # A possibly-created failed initial session is resumed, never recreated.
        self.assertEqual(run.call_args_list[1].args[0][-2:], ["--resume", THREAD_A])

    def test_closed_and_unknown_sessions_fail_before_model_launch(self):
        host = ClaudeTransport(self.root)
        with self.assertRaisesRegex(HostError, "unknown"):
            host.run_turn(THREAD_A, "no")
        host.close()
        with self.assertRaisesRegex(HostError, "closed"):
            host.start_thread(self.root)

    def test_missing_script_marker_becomes_a_failed_assertion(self):
        turn = {"status": "completed", "text": "SCRIPT_EXECUTED"}
        assertion = probe.continuation_assertion(turn, self.root / "missing-marker.txt")
        self.assertFalse(assertion["passed"])
        self.assertIsNone(assertion["marker"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
