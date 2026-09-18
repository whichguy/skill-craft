#!/usr/bin/env python3
"""Hermetic ACP contract checks for the optional Grok ShipLoop transport."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("shiploop_host_grok", SCRIPTS / "shiploop_host_grok.py")
grok = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = grok
SPEC.loader.exec_module(grok)


SERVER = r'''
import json
import os
from pathlib import Path
import sys

scenario = sys.argv[1]
session_id = "grok-session-1"
turn = 0

def reply(identifier, result=None, error=None):
    value = {"jsonrpc": "2.0", "id": identifier}
    if error is None:
        value["result"] = result
    else:
        value["error"] = error
    print(json.dumps(value), flush=True)

for line in sys.stdin:
    value = json.loads(line)
    method = value.get("method")
    if method == "initialize":
        if value.get("params", {}).get("clientCapabilities") != {}:
            reply(value["id"], error={"code": -32602, "message": "unexpected client capabilities"})
        else:
            reply(value["id"], {
                "protocolVersion": 1,
                "agentCapabilities": {"loadSession": True},
                "_meta": {"agentVersion": "test-grok"},
            })
    elif method == "session/new":
        if not isinstance(value.get("params", {}).get("mcpServers"), list):
            reply(value["id"], error={"code": -32602, "message": "missing mcpServers"})
        else:
            reply(value["id"], {"sessionId": session_id})
    elif method == "session/load":
        params = value.get("params", {})
        if params.get("sessionId") != session_id or not isinstance(params.get("mcpServers"), list):
            reply(value["id"], error={"code": -32602, "message": "bad session/load params"})
        else:
            reply(value["id"], {"_meta": {"sessionId": session_id}})
    elif method == "session/prompt":
        if scenario == "failed":
            reply(value["id"], error={"code": -32000, "message": "synthetic failure"})
            continue
        if scenario == "permission":
            print(json.dumps({
                "jsonrpc": "2.0", "id": "permission-1",
                "method": "session/request_permission", "params": {"kind": "tool"},
            }), flush=True)
            continue
        turn += 1
        prompt_id = "prompt-" + str(turn)
        params = value["params"]
        print(json.dumps({
            "jsonrpc": "2.0", "method": "session/update",
            "params": {
                "sessionId": params["sessionId"],
                "update": {"sessionUpdate": "agent_thought_chunk", "content": {"type": "text", "text": "ignore"}},
                "_meta": {"promptId": prompt_id},
            },
        }), flush=True)
        for text in ("CONT", "INUE"):
            print(json.dumps({
                "jsonrpc": "2.0", "method": "session/update",
                "params": {
                    "sessionId": params["sessionId"],
                    "update": {"sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": text}},
                    "_meta": {"promptId": prompt_id},
                },
            }), flush=True)
        reply(value["id"], {
            "stopReason": "end_turn",
            "_meta": {
                "promptId": prompt_id,
                "usage": {"inputTokens": 7, "outputTokens": 2, "totalTokens": 9},
            },
        })
    elif value.get("id") == "permission-1":
        audit = Path(os.environ["FAKE_GROK_AUDIT"])
        audit.write_text(json.dumps(value), encoding="utf-8")
'''


class GrokTransportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.calls = []
        self.audit = self.repo / "approval.json"
        self.real_popen = subprocess.Popen

    def tearDown(self):
        self.tmp.cleanup()

    def test_native_permissions_are_required_before_starting_a_process(self):
        with self.assertRaisesRegex(grok.HostError, "writable_roots"):
            grok.GrokTransport(self.repo, writable_roots=[self.repo])
        with self.assertRaisesRegex(grok.HostError, "network_access"):
            grok.GrokTransport(self.repo, network_access=False)
        self.assertEqual(self.calls, [])

    def test_new_resume_and_prompt_preserve_native_usage_and_worker_marker(self):
        with patch.object(grok.subprocess, "Popen", self._popen("normal")):
            with grok.GrokTransport(self.repo, timeout=5, telemetry_grace=0) as transport:
                session_id = transport.start_thread(self.repo)
                result = transport.run_turn(session_id, "reply CONTINUE")
                self.assertEqual(transport.resume_thread(session_id), session_id)
                resumed = transport.run_turn(session_id, "reply CONTINUE again")

        self.assertEqual(session_id, "grok-session-1")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["thread_id"], "grok-session-1")
        self.assertEqual(result["turn_id"], "prompt-1")
        self.assertEqual(result["text"], "CONTINUE")
        self.assertEqual(result["usage"], {"inputTokens": 7, "outputTokens": 2, "totalTokens": 9})
        self.assertIsNone(result["error"])
        self.assertGreaterEqual(result["elapsed_seconds"], 0)
        self.assertEqual(resumed["turn_id"], "prompt-1")
        self.assertEqual(resumed["text"], "CONTINUE")
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[0][0], ["grok", "agent", "--no-leader", "stdio"])
        self.assertEqual(self.calls[0][1]["env"]["SHIPLOOP_CONTEXT_HOST_WORKER"], "1")
        self.assertEqual(self.calls[0][1]["env"]["GROK_MEMORY"], "0")
        self.assertNotIn("--always-approve", self.calls[0][0])
        self.assertNotIn("--sandbox", self.calls[0][0])

    def test_prompt_rpc_error_is_a_failed_turn_with_no_fabricated_usage(self):
        with patch.object(grok.subprocess, "Popen", self._popen("failed")):
            with grok.GrokTransport(self.repo, timeout=5, telemetry_grace=0) as transport:
                session_id = transport.start_thread(self.repo)
                result = transport.run_turn(session_id, "fail")

        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["turn_id"])
        self.assertEqual(result["text"], "")
        self.assertIsNone(result["usage"])
        self.assertIn("synthetic failure", result["error"])

    def test_interactive_request_is_rejected_without_autoapproval(self):
        with patch.object(grok.subprocess, "Popen", self._popen("permission")):
            with grok.GrokTransport(self.repo, timeout=5, telemetry_grace=0) as transport:
                session_id = transport.start_thread(self.repo)
                with self.assertRaisesRegex(grok.HostError, "interactive host action"):
                    transport.run_turn(session_id, "request a tool")

        observed = json.loads(self.audit.read_text(encoding="utf-8"))
        self.assertEqual(observed["id"], "permission-1")
        self.assertEqual(observed["error"]["code"], -32001)
        self.assertIn("cannot relay or auto-approve", observed["error"]["message"])

    def _popen(self, scenario):
        def fake_popen(command, *args, **kwargs):
            self.calls.append((list(command), dict(kwargs)))
            env = {**kwargs["env"], "FAKE_GROK_AUDIT": str(self.audit)}
            return self.real_popen(
                [sys.executable, "-u", "-c", SERVER, scenario],
                *args,
                **{**kwargs, "env": env},
            )

        return fake_popen


if __name__ == "__main__":
    unittest.main()
