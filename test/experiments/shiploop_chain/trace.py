#!/usr/bin/env python3
"""Fail-closed evaluator for a captured Grok native-chain host trace.

This is an external observer.  It neither starts Grok nor changes the pilot,
worktrees, Git state, or worker handoff files.  A passing result establishes
that the captured parent used typed native spawn and collection events tied to
the retained pilot records.  It deliberately treats missing telemetry as
insufficient for native-overlap claims.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import re
import shlex
import sys
from typing import Any


STEPS = ("A", "B", "C", "J")
HANDOFF_DIRECTORY = ".shiploop-handoff"
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
UUID_IN_TEXT_RE = re.compile(r"\bsubagent_id:\s*([0-9a-f-]{36})\b", re.IGNORECASE)
PASSIVE_TYPES = {"available_commands", "thought", "text", "usage", "system", "session", "message"}
MUTATING_TOOLS = {"write", "search_replace", "apply_patch", "edit_file", "write_file"}
READ_ONLY_TOOLS = {"read_file", "list_directory", "list_dir", "search", "grep", "glob"}
HOST_STATE_ONLY_TOOLS = {"todo_write"}
NONTERMINAL_TASK_STATUSES = {"", "pending", "running", "in_progress", "in-progress", "queued"}
DRIVER_ACTIONS = {
    "claim", "start", "launched", "import-handoff", "prepare-integration", "done", "show", "finish", "packet",
}


class TraceError(RuntimeError):
    """A retained trace or pilot record cannot support the requested claim."""


def _regular(path: Path, label: str) -> Path:
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = candidate.resolve()
    if not candidate.is_file() or candidate.is_symlink():
        raise TraceError(f"{label} must be a regular file: {candidate}")
    return candidate


def _json_file(path: Path, label: str) -> dict[str, Any]:
    candidate = _regular(path, label)
    try:
        value = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TraceError(f"{label} is not JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise TraceError(f"{label} must contain a JSON object")
    return value


def _absolute(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise TraceError(f"{label} must be a nonempty absolute path")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise TraceError(f"{label} must be an absolute path")
    return str(path.resolve(strict=False))


def _under(value: str, root: str) -> bool:
    try:
        Path(value).resolve(strict=False).relative_to(Path(root).resolve(strict=False))
        return True
    except ValueError:
        return False


def _option(tokens: list[str], name: str) -> str | None:
    values = [tokens[index + 1] for index, token in enumerate(tokens[:-1]) if token == name]
    return values[0] if len(values) == 1 else None


def _packet_workspace(packet: dict[str, Any]) -> str:
    context = packet.get("context")
    value = context.get("workspace") if isinstance(context, dict) else packet.get("workspace")
    return _absolute(value, "saved packet workspace")


def _records_by_step(directory: Path, label: str) -> dict[str, dict[str, Any]]:
    if not directory.is_dir() or directory.is_symlink():
        raise TraceError(f"{label} directory is absent: {directory}")
    values: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.json")):
        value = _json_file(path, f"{label} record")
        step = value.get("step")
        if step not in STEPS:
            raise TraceError(f"{label} record has an unsupported step: {path}")
        if step in values:
            raise TraceError(f"{label} has more than one record for {step}")
        values[step] = value
    missing = [step for step in STEPS if step not in values]
    if missing:
        raise TraceError(f"{label} is missing records for {', '.join(missing)}")
    return values


def build_manifest(pilot_dir: str | Path) -> dict[str, Any]:
    """Bind the trace to retained pilot records after a completed four-step run."""
    pilot = Path(pilot_dir).expanduser().resolve()
    context = _json_file(pilot / "context.json", "pilot context")
    fixture = context.get("fixture")
    if not isinstance(fixture, dict):
        raise TraceError("pilot context has no fixture")
    feature = _absolute(fixture.get("initiating_feature"), "initiating feature")
    selected = context.get("selected")
    if not isinstance(selected, dict):
        raise TraceError("pilot context has no selected runtime")
    driver_python = _absolute(selected.get("python"), "selected native-driver Python")
    source_root = _absolute(selected.get("source_root"), "selected native-driver source root")
    driver_path = str((Path(source_root) / "test/experiments/shiploop_chain/native_pilot.py").resolve(strict=False))
    workspace_records = _records_by_step(pilot / "workspaces", "caller workspace")
    packets = _records_by_step(pilot / "packets", "worker packet")
    handles = _records_by_step(pilot / "handles", "native handle")
    accepted = _records_by_step(pilot / "accepted", "accepted contribution")
    steps: dict[str, dict[str, str]] = {}
    for step in STEPS:
        workspace = workspace_records[step]
        packet = packets[step]
        handle = handles[step]
        accepted_record = accepted[step]
        attempt = workspace.get("attempt")
        if not isinstance(attempt, str) or not attempt:
            raise TraceError(f"caller workspace record has no attempt for {step}")
        if packet.get("step") != step or packet.get("attempt") != attempt:
            raise TraceError(f"saved packet identity differs from workspace record for {step}")
        if handle.get("step") != step or handle.get("attempt") != attempt:
            raise TraceError(f"native handle identity differs from workspace record for {step}")
        if accepted_record.get("step") != step or accepted_record.get("attempt") != attempt:
            raise TraceError(f"accepted identity differs from workspace record for {step}")
        workspace_path = _absolute(workspace.get("workspace"), f"workspace for {step}")
        if _packet_workspace(packet) != workspace_path:
            raise TraceError(f"saved packet does not bind the caller workspace for {step}")
        native_handle = handle.get("handle")
        if not isinstance(native_handle, str) or UUID_RE.fullmatch(native_handle) is None:
            raise TraceError(f"native handle for {step} is not a Grok subagent UUID")
        source = _absolute(handle.get("source"), f"native handle source for {step}")
        expected_source = str((pilot / f"{step}-handle.json").resolve(strict=False))
        if source != expected_source:
            raise TraceError(f"native handle source for {step} is not its canonical retained handle path")
        handoff = str(Path(workspace_path) / HANDOFF_DIRECTORY / attempt / "handoff.json")
        steps[step] = {
            "step": step,
            "attempt": attempt,
            "workspace": workspace_path,
            "packet": str((pilot / "packets" / f"{step}-{attempt}.json").resolve(strict=False)),
            "handle": native_handle.lower(),
            "handle_source": source,
            "handoff": handoff,
        }
    return {
        "schema": "shiploop-native-trace-manifest/v1",
        "pilot_dir": str(pilot),
        "feature": feature,
        "driver_python": driver_python,
        "driver_path": driver_path,
        "steps": steps,
    }


def _load_host_trace(path_value: str | Path) -> list[dict[str, Any]]:
    path = _regular(Path(path_value), "host trace")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise TraceError(f"could not read host trace: {exc}") from exc
    if not lines:
        raise TraceError("host trace is empty")
    events: list[dict[str, Any]] = []
    for number, line in enumerate(lines, 1):
        if not line:
            raise TraceError(f"host trace has an empty line at {number}")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TraceError(f"host trace has invalid JSON at line {number}: {exc.msg}") from exc
        if not isinstance(value, dict) or not isinstance(value.get("type"), str):
            raise TraceError(f"host trace has malformed event at line {number}")
        events.append(value)
    return events


def host_terminal(host_trace: str | Path) -> dict[str, Any]:
    """Return the typed terminal observation without treating it as success."""
    events = _load_host_trace(host_trace)
    terminal = [event for event in events if event.get("type") == "end"]
    if len(terminal) != 1:
        return {"event_count": len(events), "end_count": len(terminal), "stop_reason": None, "complete": False}
    stop_reason = terminal[0].get("stopReason")
    return {
        "event_count": len(events), "end_count": 1,
        "stop_reason": stop_reason if isinstance(stop_reason, str) else None,
        "complete": stop_reason == "end_turn",
    }


def _text_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [part for item in value for part in _text_values(item)]
    if not isinstance(value, dict):
        return []
    texts: list[str] = []
    for key in ("text", "output", "output_for_prompt", "content", "message"):
        texts.extend(_text_values(value.get(key)))
    return texts


def _spawn_identifier(raw_output: Any) -> str | None:
    if isinstance(raw_output, dict):
        for key in ("subagent_id", "subagentId", "task_id", "taskId", "id"):
            value = raw_output.get(key)
            if isinstance(value, str) and UUID_RE.fullmatch(value):
                return value.lower()
    for text in _text_values(raw_output):
        match = UUID_IN_TEXT_RE.search(text)
        if match and UUID_RE.fullmatch(match.group(1)):
            return match.group(1).lower()
    return None


def _rows(raw_output: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_output, dict):
        return []
    if raw_output.get("type") == "TaskOutput":
        multi = raw_output.get("MultiResult")
        if isinstance(multi, dict) and isinstance(multi.get("results"), list):
            return [row for row in multi["results"] if isinstance(row, dict)]
        result = raw_output.get("Result")
        if isinstance(result, dict):
            return [result]
    if raw_output.get("type") == "TaskOutput.MultiResult" and isinstance(raw_output.get("results"), list):
        return [row for row in raw_output["results"] if isinstance(row, dict)]
    if isinstance(raw_output.get("results"), list):
        return [row for row in raw_output["results"] if isinstance(row, dict)]
    return [raw_output]


def _row_identifier(row: dict[str, Any]) -> str | None:
    for key in ("task_id", "taskId", "subagent_id", "subagentId", "id"):
        value = row.get(key)
        if isinstance(value, str) and UUID_RE.fullmatch(value):
            return value.lower()
    return None


def _row_succeeded(row: dict[str, Any], expected_id: str) -> bool:
    if _row_identifier(row) != expected_id:
        return False
    if str(row.get("status", "")).lower() != "completed":
        return False
    exit_code = row.get("exit_code", row.get("exitCode"))
    return type(exit_code) is int and exit_code == 0


def _terminal_task_failure(row: dict[str, Any]) -> str | None:
    """Describe a terminal task failure without treating pending polls as failures."""
    status = row.get("status")
    if not isinstance(status, str):
        return None
    normalized = status.strip().lower()
    if normalized in NONTERMINAL_TASK_STATUSES:
        return None
    if normalized == "completed":
        exit_code = row.get("exit_code", row.get("exitCode"))
        if type(exit_code) is int and exit_code == 0:
            return None
        return f"completed with invalid exit_code {exit_code!r}"
    return f"terminal status {status!r}"


def _completion_identity(row: dict[str, Any], identifier: str, interval: dict[str, Any] | None) -> tuple[Any, ...]:
    """Normalize durable task-result fields while excluding host-tool metadata."""
    if interval is None:
        timing: tuple[Any, ...] = (
            "raw",
            row.get("started", row.get("start")),
            row.get("ended", row.get("end")),
            row.get("started_monotonic_ms", row.get("started_ms", row.get("start_monotonic_ms", row.get("start_ms")))),
            row.get("ended_monotonic_ms", row.get("ended_ms", row.get("end_monotonic_ms", row.get("end_ms")))),
        )
    else:
        timing = ("normalized", interval["clock"], interval["started"], interval["ended"])
    return (
        identifier,
        str(row.get("status", "")).strip().lower(),
        row.get("exit_code", row.get("exitCode")),
        timing,
    )


def _parse_iso(value: Any) -> tuple[float, bool] | None:
    if not isinstance(value, str):
        return None
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    fractional = bool(re.search(r"\.\d+(?:Z|[+-]\d\d:?\d\d)$", value))
    return parsed.timestamp(), fractional


def _finite_monotonic(value: Any) -> float | None:
    if type(value) not in (int, float):
        return None
    try:
        normalized = float(value)
    except (OverflowError, ValueError):
        return None
    if type(value) is int and normalized != value:
        return None
    return normalized if math.isfinite(normalized) else None


def _interval(row: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    start_iso = row.get("started", row.get("start"))
    end_iso = row.get("ended", row.get("end"))
    has_iso = start_iso is not None or end_iso is not None
    start_mono = row.get("started_monotonic_ms", row.get("started_ms", row.get("start_monotonic_ms", row.get("start_ms"))))
    end_mono = row.get("ended_monotonic_ms", row.get("ended_ms", row.get("end_monotonic_ms", row.get("end_ms"))))
    has_mono = start_mono is not None or end_mono is not None
    if has_iso:
        start = _parse_iso(start_iso)
        end = _parse_iso(end_iso)
        if start is None or end is None:
            return None, "requires valid started and ended ISO timestamps"
        if end[0] <= start[0]:
            return None, "ended at or before started"
        precise = start[1] and end[1]
        if precise:
            guaranteed_started, guaranteed_ended, resolution = start[0], end[0], "subsecond"
        else:
            # Whole-second ISO fields are host task-event times quantized to seconds,
            # not collection receipt times.  Only this inner interval is guaranteed.
            guaranteed_started, guaranteed_ended, resolution = start[0] + 1.0, end[0] - 1.0, "whole-second"
        return {
            "clock": "epoch",
            "started": start[0],
            "ended": end[0],
            "precise": precise,
            "resolution": resolution,
            "guaranteed_started": guaranteed_started,
            "guaranteed_ended": guaranteed_ended,
        }, None
    if has_mono:
        start = _finite_monotonic(start_mono)
        end = _finite_monotonic(end_mono)
        if start is None or end is None:
            return None, "requires finite int or float started and ended monotonic timestamps without integer precision loss"
        if end <= start:
            return None, "ended at or before started"
        return {
            "clock": "monotonic",
            "started": start,
            "ended": end,
            "precise": True,
            "resolution": "monotonic",
            "guaranteed_started": start,
            "guaranteed_ended": end,
        }, None
    return None, "has no start/end telemetry"


def _driver_options(tokens: list[str], action: str) -> tuple[dict[str, list[str]] | None, str | None]:
    value_options = {"--pilot-dir"}
    flag_options: set[str] = set()
    if action == "claim":
        value_options.add("--steps")
    elif action not in {"show", "finish"}:
        value_options.update({"--step", "--attempt"})
        if action == "launched":
            value_options.add("--handle-file")
        if action == "import-handoff":
            value_options.add("--handoff-manifest")
        if action in {"import-handoff", "prepare-integration", "done"}:
            flag_options.add("--confirmed-stopped")
    required = value_options | flag_options
    options: dict[str, list[str]] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token.startswith("--"):
            return None, f"terminal command has unexpected positional argument {token!r}"
        if "=" in token:
            return None, f"terminal command uses inline option assignment {token!r}"
        if token not in value_options and token not in flag_options:
            return None, f"terminal command has unsupported option {token!r}"
        if token in options:
            return None, f"terminal command repeats {token}"
        if token in flag_options:
            options[token] = []
            index += 1
            continue
        if token == "--steps":
            index += 1
            values: list[str] = []
            while index < len(tokens) and not tokens[index].startswith("--"):
                values.append(tokens[index])
                index += 1
            if not values:
                return None, "terminal command lacks values for --steps"
            options[token] = values
            continue
        if index + 1 >= len(tokens) or tokens[index + 1].startswith("--"):
            return None, f"terminal command lacks a value for {token}"
        options[token] = [tokens[index + 1]]
        index += 2
    missing = sorted(required.difference(options))
    if missing:
        return None, f"terminal command lacks required option {missing[0]}"
    return options, None


def _safe_driver_command(command: Any, manifest: dict[str, Any]) -> tuple[bool, str | None, str]:
    if not isinstance(command, str) or not command.strip():
        return False, None, "terminal command is absent"
    if "\n" in command or any(character in command for character in ";|&<>"):
        return False, None, "terminal command uses shell composition"
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return False, None, "terminal command cannot be parsed"
    if not tokens or str(Path(tokens[0]).resolve(strict=False)) != manifest["driver_python"]:
        return False, None, "terminal command does not use the selected Python executable"
    index = 1
    if index < len(tokens) and tokens[index] == "-B":
        index += 1
    if index >= len(tokens) or str(Path(tokens[index]).resolve(strict=False)) != manifest["driver_path"]:
        return False, None, "terminal command does not use the selected native_pilot.py path"
    remaining = tokens[index + 1:]
    if not remaining:
        return False, None, "terminal command lacks Python or driver action"
    if remaining[0] == "--help":
        if remaining == ["--help"]:
            return True, None, ""
        return False, None, "terminal command uses --help with extra arguments"
    action = remaining[0]
    if action not in DRIVER_ACTIONS:
        return False, None, f"terminal command has unsupported pilot action {action!r}"
    if "--help" in remaining[1:]:
        if remaining[1:] == ["--help"]:
            return True, None, ""
        return False, None, "terminal command uses --help with extra arguments"
    options, issue = _driver_options(remaining[1:], action)
    if options is None:
        return False, None, issue or "terminal command has invalid options"
    if options["--pilot-dir"][0] != manifest["pilot_dir"]:
        return False, None, "terminal command targets a different pilot directory"
    step = options.get("--step", [None])[0]
    attempt = options.get("--attempt", [None])[0]
    if action not in {"show", "finish", "claim"}:
        if step not in manifest["steps"] or attempt != manifest["steps"][step]["attempt"]:
            return False, None, "terminal command has an unknown step or attempt"
    if action == "claim":
        claimed = options["--steps"]
        if any(item not in manifest["steps"] for item in claimed):
            return False, None, "claim command names an unknown step"
    if action == "launched":
        source = options["--handle-file"][0]
        if source != manifest["steps"][step]["handle_source"]:
            return False, None, "launched command does not use the retained handle source"
    if action == "import-handoff":
        if options["--handoff-manifest"][0] != manifest["steps"][step]["handoff"]:
            return False, None, "import-handoff does not use the exact worker-local handoff"
    return True, action, ""


def _successful_driver_terminal(call: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Return the final successful Bash receipt, or a precise rejection reason.

    A ``tool_call_update`` status is only transport state.  The lifecycle
    commands change the pilot, so their captured terminal result must also
    prove that the exact command completed successfully.
    """
    terminal = [update for update in call["updates"] if str(update["status"] or "").lower() not in {
        "", "pending", "running", "in_progress", "in-progress", "queued",
    }]
    if not terminal or str(terminal[-1]["status"] or "").lower() != "completed":
        return None, "has no completed parent terminal receipt"
    result = terminal[-1]["output"]
    if not isinstance(result, dict):
        return None, "terminal result is absent"
    if result.get("type") != "Bash":
        return None, "terminal result is not a Bash result"
    if result.get("command") != call["input"]["command"]:
        return None, "terminal result command differs from its rawInput command"
    if type(result.get("exit_code")) is not int or result["exit_code"] != 0:
        return None, "terminal result exit_code is not zero"
    if result.get("signal") is not None:
        return None, "terminal result signal is not null"
    if result.get("timed_out") is not False:
        return None, "terminal result timed_out is not false"
    return terminal[-1], None


def _path_from_input(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in ("target_file", "path", "file_path", "file"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def evaluate_events(events: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    """Evaluate parsed raw `--output-format streaming-json` records."""
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    calls: dict[str, dict[str, Any]] = {}
    driver_calls: dict[str, list[dict[str, Any]]] = {step: [] for step in STEPS}
    global_driver_calls: list[dict[str, Any]] = []
    parent_end: int | None = None
    def fail(name: str, detail: str) -> None:
        checks.append({"name": name, "passed": False, "detail": detail})
        errors.append(f"{name}: {detail}")
    def passed(name: str, detail: str) -> None:
        checks.append({"name": name, "passed": True, "detail": detail})
    protected = [manifest["feature"], *(record["workspace"] for record in manifest["steps"].values())]
    handle_sources = {record["handle_source"] for record in manifest["steps"].values()}
    for index, event in enumerate(events):
        event_type = event.get("type")
        if event_type in PASSIVE_TYPES:
            continue
        if event_type == "end":
            if parent_end is not None:
                fail("host_end", "host trace has more than one terminal end event")
            elif event.get("stopReason") != "end_turn":
                fail("host_end", "host terminal event is not end_turn")
            else:
                parent_end = index
            continue
        if event_type not in {"tool_call", "tool_call_update"}:
            fail("stream", f"unrecognized host event type {event_type!r} at line {index + 1}")
            continue
        if parent_end is not None:
            fail("host_end", f"tool activity appears after host end at line {index + 1}")
        call_id = event.get("toolCallId")
        if not isinstance(call_id, str) or not call_id:
            fail("stream", f"tool event at line {index + 1} has no toolCallId")
            continue
        if event_type == "tool_call":
            tool = event.get("toolName")
            if not isinstance(tool, str) or not tool:
                fail("stream", f"tool call {call_id} has no toolName")
                continue
            if call_id in calls:
                fail("stream", f"tool call {call_id} is duplicated")
                continue
            raw_input = event.get("rawInput")
            if raw_input is None:
                raw_input = {}
            if not isinstance(raw_input, dict):
                fail("stream", f"tool call {call_id} has non-object rawInput")
                continue
            call = {"id": call_id, "tool": tool, "input": raw_input, "index": index, "updates": []}
            calls[call_id] = call
            if tool == "run_terminal_command":
                safe, action, reason = _safe_driver_command(raw_input.get("command"), manifest)
                if not safe:
                    fail("parent_authoring", reason)
                elif action in {"claim", "finish"}:
                    call["driver_action"] = action
                    global_driver_calls.append(call)
                elif action and action not in {"show", "finish", "claim"}:
                    step = _option(shlex.split(raw_input["command"]), "--step")
                    call["driver_action"] = action
                    call["driver_step"] = step
                    driver_calls[step].append(call)
            elif tool in MUTATING_TOOLS:
                target = _path_from_input(raw_input)
                if target is None or not Path(target).is_absolute():
                    fail("parent_authoring", f"parent {tool} has no absolute safe handle-file target")
                elif str(Path(target).resolve(strict=False)) not in handle_sources:
                    fail("parent_authoring", f"parent {tool} is not limited to a retained native-handle file")
            elif tool not in {"spawn_subagent", "get_command_or_subagent_output", *READ_ONLY_TOOLS, *HOST_STATE_ONLY_TOOLS}:
                fail("parent_authoring", f"parent tool {tool} is not allowed")
            continue
        call = calls.get(call_id)
        if call is None:
            fail("stream", f"tool update {call_id} arrived before its tool call")
            continue
        call["updates"].append({"index": index, "status": event.get("status"), "output": event.get("rawOutput")})
    if parent_end is None:
        fail("host_end", "host trace has no terminal end_turn event")
    else:
        passed("host_end", "one terminal end_turn event is present")

    driver_actions: dict[str, dict[str, dict[str, int]]] = {step: {} for step in STEPS}
    for step, records in driver_calls.items():
        for call in records:
            action = call["driver_action"]
            terminal, issue = _successful_driver_terminal(call)
            if terminal is None:
                fail("driver_receipt", f"{step} {action} {issue}")
                continue
            if action in driver_actions[step]:
                fail("driver_receipt", f"{step} repeats parent {action} command")
                continue
            driver_actions[step][action] = {"call": call["index"], "completed": terminal["index"]}

    claim_receipts: dict[str, list[int]] = {step: [] for step in STEPS}
    finish_calls: list[int] = []
    for call in global_driver_calls:
        action = call["driver_action"]
        terminal, issue = _successful_driver_terminal(call)
        if terminal is None:
            fail("driver_receipt", f"{action} {issue}")
            continue
        if action == "finish":
            finish_calls.append(call["index"])
        else:
            tokens = shlex.split(call["input"]["command"])
            for step in tokens[tokens.index("--steps") + 1:]:
                claim_receipts[step].append(terminal["index"])
    for step in STEPS:
        start = driver_actions[step].get("start")
        if start is not None and not any(index < start["call"] for index in claim_receipts[step]):
            fail("claim", f"{step} start has no preceding successful claim receipt")
    done_receipts = [driver_actions[step]["done"]["completed"] for step in STEPS
                     if "done" in driver_actions[step]]
    if not finish_calls:
        fail("finish", "host trace has no successful finish receipt")
    elif len(done_receipts) != len(STEPS) or min(finish_calls) <= max(done_receipts):
        fail("finish", "finish does not follow every completed integration")
    else:
        passed("finish", "successful finish follows all step integrations")

    workers: dict[str, dict[str, Any]] = {}
    ids: dict[str, str] = {}
    for call in calls.values():
        if call["tool"] != "spawn_subagent":
            continue
        workspace = call["input"].get("cwd")
        matching = [step for step, record in manifest["steps"].items() if workspace == record["workspace"]]
        if len(matching) != 1:
            fail("dispatch", f"native spawn {call['id']} has an unbound workspace")
            continue
        step = matching[0]
        if step in workers:
            fail("dispatch", f"native spawn is duplicated for {step}")
            continue
        if call["input"].get("background") is not True:
            fail("dispatch", f"native spawn for {step} is not background")
        if call["input"].get("resume_from") not in (None, ""):
            fail("dispatch", f"native spawn for {step} resumes prior context")
        if call["input"].get("isolation") == "worktree":
            fail("dispatch", f"native spawn for {step} uses Grok-managed worktree isolation")
        prompt = call["input"].get("prompt")
        expected = manifest["steps"][step]
        markers = (
            f"fresh native Ask-Agent worker for ShipLoop step {step}, attempt {expected['attempt']}",
            expected["workspace"], expected["handoff"],
        )
        if not isinstance(prompt, str) or any(marker not in prompt for marker in markers):
            fail("dispatch", f"native spawn for {step} is not bound to its inline worker assignment")
        completed = [update for update in call["updates"] if str(update["status"] or "").lower() == "completed"]
        identifiers = {_spawn_identifier(update["output"]) for update in completed}
        identifiers.discard(None)
        if len(identifiers) != 1:
            fail("dispatch", f"native spawn for {step} has no unique typed subagent_id receipt")
            continue
        identifier = identifiers.pop()
        if identifier != expected["handle"]:
            fail("dispatch", f"native spawn ID for {step} does not equal retained handle")
        if identifier in ids:
            fail("dispatch", f"native child ID for {step} duplicates {ids[identifier]}")
        ids[identifier] = step
        receipt_indexes = [update["index"] for update in completed if _spawn_identifier(update["output"]) == identifier]
        workers[step] = {
            "step": step, "handle": identifier, "spawn_index": call["index"],
            "spawn_receipt_index": min(receipt_indexes), "collections": [],
        }
    for step in STEPS:
        if step not in workers:
            fail("dispatch", f"missing typed native dispatch for {step}")
        else:
            passed("dispatch", f"{step} native spawn matches its retained UUID and workspace")

    terminal_task_failures: dict[str, list[str]] = {step: [] for step in STEPS}
    completion_identities: dict[str, tuple[Any, ...]] = {}
    conflicting_completions: dict[str, list[str]] = {step: [] for step in STEPS}
    for call in calls.values():
        if call["tool"] != "get_command_or_subagent_output":
            continue
        task_ids = call["input"].get("task_ids", call["input"].get("taskIds"))
        if not isinstance(task_ids, list) or not all(isinstance(value, str) for value in task_ids):
            fail("collection", f"native collection {call['id']} has no typed task_ids")
            continue
        for update in call["updates"]:
            if str(update["status"] or "").lower() != "completed":
                continue
            for row in _rows(update["output"]):
                identifier = _row_identifier(row)
                if identifier not in ids or identifier not in task_ids:
                    continue
                failure = _terminal_task_failure(row)
                if failure is not None:
                    terminal_task_failures[ids[identifier]].append(failure)
                    continue
                if not _row_succeeded(row, identifier):
                    continue
                interval, issue = _interval(row)
                step = ids[identifier]
                identity = _completion_identity(row, identifier, interval)
                previous = completion_identities.get(step)
                if previous is None:
                    completion_identities[step] = identity
                elif previous != identity:
                    conflicting_completions[step].append("same requested UUID has different status, exit, or timing")
                workers[step]["collections"].append({
                    "call_index": call["index"], "receipt_index": update["index"], "row": row,
                    "interval": interval, "interval_issue": issue,
                })
    for step in STEPS:
        worker = workers.get(step)
        if worker is None:
            continue
        if terminal_task_failures[step]:
            fail("collection", f"{step} has non-success terminal native collection: {terminal_task_failures[step][0]}")
        if conflicting_completions[step]:
            fail("collection", f"{step} has contradictory successful native completion records: {conflicting_completions[step][0]}")
        successful = worker["collections"]
        if not successful:
            fail("collection", f"{step} has no completed zero-exit typed native collection")
            continue
        successful.sort(key=lambda item: item["receipt_index"])
        collection = successful[0]
        worker["collection"] = collection
        if worker["spawn_receipt_index"] >= collection["call_index"]:
            fail("collection", f"{step} collection started before its native dispatch receipt")
        action_indexes = driver_actions[step]
        for action in ("start", "launched", "import-handoff", "prepare-integration", "done"):
            if action not in action_indexes:
                fail("lifecycle", f"{step} has no exact parent {action} command")
        start_index = action_indexes.get("start")
        if start_index is not None and start_index["completed"] >= worker["spawn_index"]:
            fail("lifecycle", f"{step} start success does not precede native dispatch")
        launched_index = action_indexes.get("launched")
        if launched_index is not None and launched_index["call"] <= worker["spawn_receipt_index"]:
            fail("lifecycle", f"{step} launched record precedes its typed native spawn receipt")
        if launched_index is not None and launched_index["completed"] >= collection["call_index"]:
            fail("lifecycle", f"{step} launched success does not precede native collection")
        import_index = action_indexes.get("import-handoff")
        if import_index is not None and collection["receipt_index"] >= import_index["call"]:
            fail("collection", f"{step} import-handoff precedes completed native collection")
        if import_index is not None and action_indexes.get("prepare-integration", {}).get("call", -1) <= import_index["completed"]:
            fail("lifecycle", f"{step} prepare-integration does not follow import-handoff")
        if (action_indexes.get("prepare-integration") is not None
                and action_indexes.get("done", {}).get("call", -1) <= action_indexes["prepare-integration"]["completed"]):
            fail("lifecycle", f"{step} done does not follow prepare-integration")
        if not any(check["name"] == "collection" and check["detail"].startswith(step + " ") and check["passed"] for check in checks):
            passed("collection", f"{step} completed native collection precedes import and parent integration")

    a, b = workers.get("A"), workers.get("B")
    if not a or not b:
        fail("parallel_dispatch", "A/B typed native dispatch is unavailable")
    else:
        action_indexes = {step: driver_actions[step] for step in ("A", "B")}
        starts = [action_indexes[step].get("start") for step in ("A", "B")]
        initial_spawns = sorted((a["spawn_index"], b["spawn_index"]))
        interposed = [call["id"] for call in calls.values()
                      if initial_spawns[0] < call["index"] < initial_spawns[1]]
        if interposed:
            fail("parallel_dispatch", "A/B native spawn calls are not adjacent among parent tool calls: " + ", ".join(interposed))
        elif (any(index is None for index in starts)
                or max(index["completed"] for index in starts if index is not None) >= min(a["spawn_index"], b["spawn_index"])):
            fail("parallel_dispatch", "A/B assignments were not both prepared before either native dispatch")
        else:
            collection_calls = []
            for call in calls.values():
                if call["tool"] != "get_command_or_subagent_output":
                    continue
                task_ids = call["input"].get("task_ids", call["input"].get("taskIds"))
                if isinstance(task_ids, list) and (a["handle"] in task_ids or b["handle"] in task_ids):
                    collection_calls.append(call["index"])
            if not collection_calls:
                fail("parallel_dispatch", "A/B has no native collection call")
            elif max(a["spawn_receipt_index"], b["spawn_receipt_index"]) >= min(collection_calls):
                fail("parallel_dispatch", "A/B were not both dispatch-confirmed before collection")
            else:
                passed("parallel_dispatch", "A/B assignments were prepared then both dispatched before collection")

    lifecycle = driver_actions
    if all("done" in lifecycle[step] for step in STEPS) and "start" in lifecycle["C"] and "start" in lifecycle["J"]:
        if not (lifecycle["A"]["done"]["completed"] < lifecycle["C"]["start"]["call"] < lifecycle["B"]["done"]["call"]):
            fail("dependency_order", "C was not started after A integration and before B integration")
        elif lifecycle["J"]["start"]["call"] <= max(lifecycle["B"]["done"]["completed"], lifecycle["C"]["done"]["completed"]):
            fail("dependency_order", "J was started before B and C integration")
        else:
            passed("dependency_order", "C and J native dispatch follow the required dependent graph")

    def overlap_pair(left_step: str, right_step: str, check_name: str) -> dict[str, Any]:
        label = f"{left_step}/{right_step}"
        result: dict[str, Any] = {"required": [left_step, right_step], "observed": False, "passed": False}
        left_worker, right_worker = workers.get(left_step), workers.get(right_step)
        if not left_worker or not right_worker or "collection" not in left_worker or "collection" not in right_worker:
            fail(check_name, f"{label} typed collection is unavailable")
            return result
        left_collection, right_collection = left_worker["collection"], right_worker["collection"]
        left, right = left_collection["interval"], right_collection["interval"]
        if left is None or right is None:
            reasons = [left_collection.get("interval_issue"), right_collection.get("interval_issue")]
            fail(check_name, f"{label} interval telemetry is unavailable: " + "; ".join(str(item) for item in reasons if item))
        elif left["clock"] != right["clock"]:
            fail(check_name, f"{label} interval telemetry uses incompatible clocks")
        else:
            raw_overlap = {
                "started": max(left["started"], right["started"]),
                "ended": min(left["ended"], right["ended"]),
            }
            raw_overlap["passed"] = raw_overlap["started"] < raw_overlap["ended"]
            guaranteed_overlap = {
                "started": max(left["guaranteed_started"], right["guaranteed_started"]),
                "ended": min(left["guaranteed_ended"], right["guaranteed_ended"]),
            }
            guaranteed_overlap["passed"] = guaranteed_overlap["started"] < guaranteed_overlap["ended"]
            result = {
                "required": [left_step, right_step],
                "observed": True,
                "passed": guaranteed_overlap["passed"],
                "clock": left["clock"],
                "resolution": {left_step: left["resolution"], right_step: right["resolution"]},
                "raw_overlap": raw_overlap,
                "guaranteed_overlap": guaranteed_overlap,
                left_step: left,
                right_step: right,
            }
            if not raw_overlap["passed"]:
                fail(check_name, f"{label} typed native execution intervals are sequential")
            elif guaranteed_overlap["passed"]:
                passed(check_name, f"{label} typed native execution intervals guarantee strict overlap")
            else:
                fail(check_name, f"{label} typed native execution intervals overlap only ambiguously at reported resolution")
        return result

    overlap = overlap_pair("A", "B", "native_overlap")
    eager_refill_overlap = overlap_pair("B", "C", "eager_refill_overlap")
    return {
        "schema": "shiploop-native-host-trace-evaluation/v1",
        "passed": not errors,
        "checks": checks,
        "errors": errors,
        "overlap": overlap,
        "overlap_pairs": {
            "initial_fanout": overlap,
            "eager_refill": eager_refill_overlap,
        },
        "workers": {
            step: {key: value for key, value in worker.items() if key != "collections"}
            for step, worker in workers.items()
        },
    }


def evaluate_host_trace(host_trace: str | Path, pilot_dir: str | Path) -> dict[str, Any]:
    manifest = build_manifest(pilot_dir)
    events = _load_host_trace(host_trace)
    result = evaluate_events(events, manifest)
    result["host_trace"] = str(Path(host_trace).expanduser().resolve())
    result["pilot_dir"] = manifest["pilot_dir"]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-trace", required=True)
    parser.add_argument("--pilot-dir", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = evaluate_host_trace(args.host_trace, args.pilot_dir)
    except TraceError as exc:
        result = {"schema": "shiploop-native-host-trace-evaluation/v1", "passed": False, "errors": [str(exc)]}
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
