#!/usr/bin/env python3
"""Deterministic, local-only Grok-shaped callback transport for DAG replay.

This is deliberately *not* a Grok CLI shim.  It accepts the narrow JSONL
request schema below on stdin and emits two streaming-JSON events per request:
``tool_call`` and ``tool_call_update``.  The response echoes the callback,
action, stage, and hash of the exact request bytes so a replay can prove which
synthetic callback the real navigator consumed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from typing import Any


REQUEST_SCHEMA = "shiploop-e2e-mock-grok-request/1"
RESPONSE_SCHEMA = "shiploop-e2e-mock-grok-response/1"
SIMULATION_NOTICE = (
    "SHIPLOOP_E2E_SIMULATION_ONLY mock_grok: local JSONL callback transport; "
    "no model, network, repository work, or shell command execution."
)
_REQUIRED = frozenset(("schema", "simulation_only", "callback_id", "action_id", "stage", "owner", "command"))
_OPTIONAL = frozenset(("result", "receipt", "final_result"))


class MockGrokError(ValueError):
    """Raised when a caller sends an unsafe or ambiguous mock request."""


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _load(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MockGrokError("request must be one UTF-8 JSON object") from exc
    if not isinstance(value, dict):
        raise MockGrokError("request must be an object")
    keys = set(value)
    if not _REQUIRED <= keys or not keys <= _REQUIRED | _OPTIONAL:
        raise MockGrokError("request has unsupported or missing fields")
    if value["schema"] != REQUEST_SCHEMA or value["simulation_only"] is not True:
        raise MockGrokError("request is not an explicit simulation-only mock request")
    for key in ("callback_id", "action_id", "stage", "owner", "command"):
        if not isinstance(value[key], str) or not value[key]:
            raise MockGrokError(f"request {key} must be nonempty text")
    return value


def response_events(raw: bytes) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return native-shaped callback events bound to one exact input line."""
    request = _load(raw)
    request_sha256 = hashlib.sha256(raw).hexdigest()
    binding = {
        "schema": RESPONSE_SCHEMA,
        "simulation_only": True,
        "callback_id": request["callback_id"],
        "action_id": request["action_id"],
        "stage": request["stage"],
        "owner": request["owner"],
        "command": request["command"],
        "request_sha256": request_sha256,
    }
    for key in _OPTIONAL:
        if key in request:
            binding[key] = request[key]
    call = {
        "type": "tool_call",
        "toolCallId": request["callback_id"],
        "toolName": "shiploop_e2e_mock_callback",
        "synthetic": True,
        "rawInput": request,
    }
    update = {
        "type": "tool_call_update",
        "toolCallId": request["callback_id"],
        "status": "completed",
        "synthetic": True,
        "rawOutput": binding,
    }
    return call, update


def main() -> int:
    print(SIMULATION_NOTICE, file=sys.stderr, flush=True)
    for line_number, line in enumerate(sys.stdin.buffer, 1):
        # ``request_sha256`` is over the JSON payload bytes, excluding exactly
        # one JSONL delimiter.  Both LF and CRLF are accepted; arbitrary
        # trailing newlines are data and are never silently stripped.
        raw = line[:-1] if line.endswith(b"\n") else line
        if line.endswith(b"\r\n"):
            raw = raw[:-1]
        if not raw:
            print(f"mock_grok input error at line {line_number}: empty request", file=sys.stderr, flush=True)
            return 2
        try:
            call, update = response_events(raw)
        except MockGrokError as exc:
            print(f"mock_grok input error at line {line_number}: {exc}", file=sys.stderr, flush=True)
            return 2
        print(_json(call), flush=True)
        print(_json(update), flush=True)
    print(_json({"type": "end", "synthetic": True, "modelCalls": 0, "modelUsage": {}}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
