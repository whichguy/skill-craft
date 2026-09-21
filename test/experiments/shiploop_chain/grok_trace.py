#!/usr/bin/env python3
"""Adapt one authoritative Grok root transcript for the native trace evaluator.

The streaming host trace can interleave root and child tool events, so it is
only used for the root-labelled terminal event.  Parent-tool policy is instead
evaluated from Grok's persisted root ``updates.jsonl`` transcript, whose
``params.sessionId`` binds every record to the one requested root session.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


_TRACE_SPEC = importlib.util.spec_from_file_location("shiploop_native_trace", Path(__file__).with_name("trace.py"))
if _TRACE_SPEC is None or _TRACE_SPEC.loader is None:
    raise RuntimeError("could not load the sibling native trace evaluator")
_TRACE = importlib.util.module_from_spec(_TRACE_SPEC)
_TRACE_SPEC.loader.exec_module(_TRACE)

TraceError = _TRACE.TraceError
UUID_RE = _TRACE.UUID_RE
build_manifest = _TRACE.build_manifest
evaluate_events = _TRACE.evaluate_events
_load_host_trace = _TRACE._load_host_trace
_regular = _TRACE._regular


_ROOT_METHODS = {"session/update", "_x.ai/session/update"}
_PASSIVE_UPDATES = {
    "agent_message_chunk",
    "agent_thought_chunk",
    "hook_execution",
    "plan",
    "subagent_finished",
    "user_message_chunk",
    "turn_completed",
    "task_backgrounded",
    "background_tasks",
    "task_completed",
}


def _session_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or UUID_RE.fullmatch(value) is None:
        raise TraceError(f"{label} must be a Grok UUID")
    return value


def _jsonl(path_value: str | Path, label: str) -> list[dict[str, Any]]:
    path = _regular(Path(path_value), label)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise TraceError(f"could not read {label}: {exc}") from exc
    if not lines:
        raise TraceError(f"{label} is empty")
    records: list[dict[str, Any]] = []
    for number, line in enumerate(lines, 1):
        if not line:
            raise TraceError(f"{label} has an empty line at {number}")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TraceError(f"{label} has invalid JSON at line {number}: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise TraceError(f"{label} has a non-object record at line {number}")
        records.append(value)
    return records


def _expected_handles(manifest: dict[str, Any]) -> set[str]:
    steps = manifest.get("steps")
    if not isinstance(steps, dict):
        raise TraceError("native trace manifest has no steps")
    values = {record.get("handle") for record in steps.values() if isinstance(record, dict)}
    if len(values) != len(steps) or not all(isinstance(value, str) and UUID_RE.fullmatch(value) for value in values):
        raise TraceError("native trace manifest has invalid retained handles")
    return {value.lower() for value in values}


def _update(record: dict[str, Any], number: int, session_id: str) -> dict[str, Any]:
    method = record.get("method")
    if method not in _ROOT_METHODS:
        raise TraceError(f"root updates has unsupported method at line {number}: {method!r}")
    params = record.get("params")
    if not isinstance(params, dict):
        raise TraceError(f"root updates has no params object at line {number}")
    actual_session = params.get("sessionId")
    if actual_session != session_id:
        raise TraceError(f"root updates has foreign or unlabelled session at line {number}")
    update = params.get("update")
    if not isinstance(update, dict):
        raise TraceError(f"root updates has no update object at line {number}")
    kind = update.get("sessionUpdate")
    if not isinstance(kind, str) or not kind:
        raise TraceError(f"root updates has no sessionUpdate at line {number}")
    return update


def _tool_call(update: dict[str, Any], number: int) -> dict[str, Any]:
    call_id, tool, raw_input = update.get("toolCallId"), update.get("title"), update.get("rawInput")
    if not isinstance(call_id, str) or not call_id:
        raise TraceError(f"root tool call has no toolCallId at line {number}")
    if not isinstance(tool, str) or not tool:
        raise TraceError(f"root tool call has no title at line {number}")
    if not isinstance(raw_input, dict):
        raise TraceError(f"root tool call has no rawInput object at line {number}")
    return {"type": "tool_call", "toolCallId": call_id, "toolName": tool, "rawInput": raw_input}


def _tool_update(update: dict[str, Any], number: int) -> dict[str, Any]:
    call_id = update.get("toolCallId")
    if not isinstance(call_id, str) or not call_id:
        raise TraceError(f"root tool update has no toolCallId at line {number}")
    event: dict[str, Any] = {"type": "tool_call_update", "toolCallId": call_id, "status": update.get("status")}
    if "rawOutput" in update:
        event["rawOutput"] = update["rawOutput"]
    if "content" in update:
        event["content"] = update["content"]
    return event


def _spawn_binding(update: dict[str, Any], number: int, session_id: str,
                   expected_handles: set[str], bindings: dict[str, dict[str, str]]) -> None:
    identifier = update.get("subagent_id")
    child = update.get("child_session_id")
    parent = update.get("parent_session_id")
    if not isinstance(identifier, str) or UUID_RE.fullmatch(identifier) is None:
        raise TraceError(f"root subagent_spawned has invalid subagent_id at line {number}")
    identifier = identifier.lower()
    if parent != session_id:
        raise TraceError(f"root subagent_spawned has an incompatible parent session at line {number}")
    if child != identifier:
        raise TraceError(f"root subagent_spawned has an incompatible child session at line {number}")
    if update.get("effective_context_source") != "new":
        raise TraceError(f"root subagent_spawned is not a fresh child at line {number}")
    if identifier not in expected_handles:
        raise TraceError(f"root subagent_spawned has an unretained child handle at line {number}")
    if identifier in bindings:
        raise TraceError(f"root subagent_spawned repeats child handle {identifier}")
    bindings[identifier] = {
        "subagent_id": identifier,
        "child_session_id": identifier,
        "parent_session_id": session_id,
    }


def normalize_root_updates(root_updates: str | Path, session_id: str,
                           manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    """Return root-owned evaluator events and exact host child-session bindings.

    This deliberately does not derive events from model text, child stdout, or
    paths.  It accepts only typed root-session records and retains the original
    typed tool inputs and outputs for the existing evaluator.
    """
    expected_session = _session_id(session_id, "expected root session id")
    expected_handles = _expected_handles(manifest)
    events: list[dict[str, Any]] = []
    bindings: dict[str, dict[str, str]] = {}
    for number, record in enumerate(_jsonl(root_updates, "root updates"), 1):
        update = _update(record, number, expected_session)
        kind = update["sessionUpdate"]
        if kind == "tool_call":
            events.append(_tool_call(update, number))
        elif kind == "tool_call_update":
            events.append(_tool_update(update, number))
        elif kind == "subagent_spawned":
            _spawn_binding(update, number, expected_session, expected_handles, bindings)
        elif kind in _PASSIVE_UPDATES:
            # Child-finished payloads and model messages are not evidence of a
            # parent tool action or native completion.  The evaluator requires
            # explicit typed collection receipts instead.
            events.append({"type": "message"})
        else:
            raise TraceError(f"root updates has unsupported sessionUpdate at line {number}: {kind!r}")
    missing = sorted(expected_handles.difference(bindings))
    if missing:
        raise TraceError("root updates lacks host subagent_spawned bindings for retained handles: " + ", ".join(missing))
    return events, bindings


def root_terminal(host_trace: str | Path, session_id: str) -> dict[str, Any]:
    """Read only the root-labelled terminal event from an interleaved host trace."""
    expected_session = _session_id(session_id, "expected root session id")
    events = _load_host_trace(host_trace)
    terminals = [event for event in events if event.get("type") == "end" and event.get("sessionId") == expected_session]
    if len(terminals) != 1:
        return {
            "event_count": len(events), "root_end_count": len(terminals), "stop_reason": None,
            "complete": False, "session_id": expected_session,
        }
    stop_reason = terminals[0].get("stopReason")
    return {
        "event_count": len(events), "root_end_count": 1,
        "stop_reason": stop_reason if isinstance(stop_reason, str) else None,
        "complete": stop_reason == "end_turn", "session_id": expected_session,
    }


def _root_tool_after_terminal(host_trace: str | Path, session_id: str, root_call_ids: set[str]) -> str | None:
    """Return a contradictory root tool ID observed after the labelled root end."""
    events = _load_host_trace(host_trace)
    terminals = [index for index, event in enumerate(events)
                 if event.get("type") == "end" and event.get("sessionId") == session_id]
    if len(terminals) != 1:
        raise TraceError("host trace lacks one root-labelled terminal event")
    for event in events[terminals[0] + 1:]:
        if event.get("type") in {"tool_call", "tool_call_update"}:
            call_id = event.get("toolCallId")
            if isinstance(call_id, str) and call_id in root_call_ids:
                return call_id
    return None


def evaluate_grok_trace(host_trace: str | Path, root_updates: str | Path,
                        session_id: str, pilot_dir: str | Path) -> dict[str, Any]:
    """Evaluate root-owned Grok actions plus the separately observed root end event."""
    manifest = build_manifest(pilot_dir)
    events, bindings = normalize_root_updates(root_updates, session_id, manifest)
    terminal = root_terminal(host_trace, session_id)
    if not terminal["complete"]:
        raise TraceError("host trace lacks one root-labelled end_turn terminal event")
    root_call_ids = {event["toolCallId"] for event in events
                     if event.get("type") in {"tool_call", "tool_call_update"}}
    post_terminal = _root_tool_after_terminal(host_trace, terminal["session_id"], root_call_ids)
    if post_terminal is not None:
        raise TraceError(f"host trace has root tool activity after its terminal event: {post_terminal}")
    events.append({"type": "end", "stopReason": "end_turn", "sessionId": terminal["session_id"]})
    result = evaluate_events(events, manifest)
    result.update({
        "schema": "shiploop-grok-root-trace-evaluation/v1",
        "host_trace": str(Path(host_trace).expanduser().resolve()),
        "root_updates": str(Path(root_updates).expanduser().resolve()),
        "root_session_id": terminal["session_id"],
        "root_terminal": terminal,
        "subagent_bindings": bindings,
        "pilot_dir": manifest["pilot_dir"],
    })
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-trace", required=True)
    parser.add_argument("--root-updates", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--pilot-dir", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = evaluate_grok_trace(args.host_trace, args.root_updates, args.session_id, args.pilot_dir)
    except TraceError as exc:
        result = {"schema": "shiploop-grok-root-trace-evaluation/v1", "passed": False, "errors": [str(exc)]}
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output.expanduser().resolve()
        if output.exists():
            print(json.dumps({"passed": False, "errors": [f"trace output already exists: {output}"]}, sort_keys=True), file=sys.stderr)
            return 2
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result.get("passed") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
