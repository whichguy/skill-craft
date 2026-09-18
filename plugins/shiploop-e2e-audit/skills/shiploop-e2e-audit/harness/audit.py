"""Read-only performance observations for captured ShipLoop E2E trials."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Mapping


_KNOWN = {"text", "thought", "tool_call", "tool_call_update", "usage", "plan", "available_commands", "end", "error", "max_turns_reached"}
_FAILED = {"failed", "error", "cancelled", "canceled", "timeout"}


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _numeric(value: Any) -> Any:
    if _number(value):
        return value
    if isinstance(value, Mapping):
        copied = {str(key): item for key, raw in value.items() if (item := _numeric(raw)) is not None}
        return copied or None
    return None


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _call_id(event: Mapping[str, Any], fallback: int) -> str:
    value = event.get("toolCallId", event.get("tool_call_id"))
    return value if isinstance(value, str) and value else f"line:{fallback}"


def _tool_name(event: Mapping[str, Any]) -> str:
    for key in ("toolName", "tool_name", "name", "tool", "kind"):
        value = event.get(key)
        if isinstance(value, str) and value:
            return value
    return "<unknown>"


def _command(event: Mapping[str, Any]) -> Any:
    raw = event.get("rawInput")
    if not isinstance(raw, Mapping):
        return None
    for key in ("argv", "command", "cmd"):
        value = raw.get(key)
        if isinstance(value, str) or (isinstance(value, list) and all(isinstance(item, str) for item in value)):
            return value
    return None


def _exit(event: Mapping[str, Any]) -> int | None:
    raw = event.get("rawOutput")
    if not isinstance(raw, Mapping):
        return None
    value = raw.get("exitCode", raw.get("exit_code"))
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _state_rows(navigation: Mapping[str, Any], warnings: list[str]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in navigation.get("states", []) if isinstance(navigation.get("states"), list) else []:
        if not isinstance(row, Mapping) or not isinstance(row.get("state"), Mapping):
            warnings.append("unparsed-navigation-state")
            continue
        state = row["state"]
        run_id = state.get("run_id")
        if isinstance(run_id, str) and run_id:
            grouped[run_id].append(state)
        else:
            warnings.append("navigation-state-without-run-id")
    rows = []
    for run_id, states in sorted(grouped.items()):
        state = max(states, key=lambda item: item.get("revision") if isinstance(item.get("revision"), int) else -1)
        accepted = state.get("accepted") if isinstance(state.get("accepted"), Mapping) else {}
        history = state.get("history") if isinstance(state.get("history"), list) else []
        stages: Counter[str] = Counter()
        repeats = blocked = 0
        for item in history:
            if not isinstance(item, Mapping):
                continue
            action, outcome, stage = item.get("action"), item.get("outcome"), item.get("stage")
            result = accepted.get(action) if isinstance(action, str) else None
            if not isinstance(result, Mapping) or result.get("outcome") != outcome:
                continue
            if isinstance(stage, str):
                stages[stage] += 1
            repeats += outcome == "repeat"
            blocked += outcome == "blocked"
        planned = state.get("work_items") if isinstance(state.get("work_items"), list) else []
        complete = state.get("completed_work_items") if isinstance(state.get("completed_work_items"), list) else []
        rows.append({"run_id": run_id, "observed_state_count": len(states), "revision": state.get("revision") if isinstance(state.get("revision"), int) else None, "status": state.get("status") if isinstance(state.get("status"), str) else None, "stage": state.get("stage") if isinstance(state.get("stage"), str) else None, "work_items_planned": len(planned), "work_items_completed": len(complete), "accepted_stage_counts": dict(sorted(stages.items())), "repeat_count": repeats, "blocked_count": blocked})
    return rows


def summarize_trial(process: dict, navigation: dict, events_path: Path) -> dict:
    """Summarize observed capture telemetry; it never infers delivery or quality.

    Only wrapper records whose stream is ``stdout`` count as native host events.
    Terminal usage is copied from the last terminal modelUsage/usage mapping;
    intermediate usage is counted, never summed.
    """
    warnings: list[str] = []
    duration = process.get("duration_seconds") if _number(process.get("duration_seconds")) else None
    if duration is None:
        warnings.append("wall-duration-unavailable")
    event_types: Counter[str] = Counter()
    unknown: Counter[str] = Counter()
    tools: dict[str, dict[str, Any]] = {}
    terminal: list[Mapping[str, Any]] = []
    usage_events = stdout_events = ignored_stderr = invalid = truncated_receipts = unusable_stdout = 0
    path = Path(events_path)
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        lines = []
        warnings.append("events-file-unavailable")
    for line_number, line in enumerate(lines, 1):
        try:
            wrapper = json.loads(line)
        except json.JSONDecodeError:
            invalid += 1
            continue
        if not isinstance(wrapper, Mapping) or wrapper.get("stream") != "stdout" or not isinstance(wrapper.get("payload"), Mapping):
            ignored_stderr += isinstance(wrapper, Mapping) and wrapper.get("stream") == "stderr"
            unusable_stdout += isinstance(wrapper, Mapping) and wrapper.get("stream") == "stdout"
            continue
        event = wrapper["payload"]
        stdout_events += 1
        truncated_receipts += bool(wrapper.get("line_truncated"))
        kind = event.get("type") if isinstance(event.get("type"), str) else "<missing>"
        event_types[kind] += 1
        if kind not in _KNOWN:
            unknown[kind] += 1
        if kind == "usage":
            usage_events += 1
        if kind == "end":
            terminal.append(event)
        if kind not in {"tool_call", "tool_call_update"}:
            continue
        call_id = _call_id(event, line_number)
        row = tools.setdefault(call_id, {"tool_call_id": call_id, "tool": _tool_name(event), "raw_command": None, "start_received_at": None, "end_received_at": None, "start_event_line": None, "update_event_lines": [], "statuses": [], "exit_codes": []})
        if kind == "tool_call":
            row["tool"] = _tool_name(event)
            row["raw_command"] = _command(event)
            row["start_received_at"] = wrapper.get("received_at")
            row["start_event_line"] = line_number
        else:
            row["end_received_at"] = wrapper.get("received_at")
            row["update_event_lines"].append(line_number)
            if isinstance(event.get("status"), str):
                row["statuses"].append(event["status"])
            if (code := _exit(event)) is not None:
                row["exit_codes"].append(code)
    if invalid:
        warnings.append("invalid-event-json")
    if ignored_stderr:
        warnings.append("stderr-events-ignored")
    if truncated_receipts:
        warnings.append("event-line-truncated")
    terminal_event = next((event for event in reversed(terminal) if isinstance(event.get("modelUsage"), Mapping) or isinstance(event.get("usage"), Mapping)), None)
    usage_source = "end.modelUsage" if terminal_event and isinstance(terminal_event.get("modelUsage"), Mapping) else "end.usage" if terminal_event and isinstance(terminal_event.get("usage"), Mapping) else None
    reported_usage = _numeric(terminal_event.get("modelUsage") if usage_source == "end.modelUsage" else terminal_event.get("usage")) if terminal_event else None
    if usage_source is None:
        warnings.append("terminal-usage-unavailable")
    tool_rows = []
    for row in tools.values():
        start, end = _timestamp(row["start_received_at"]), _timestamp(row["end_received_at"])
        duration_seconds = round((end - start).total_seconds(), 6) if start and end and end >= start else None
        if row["start_received_at"] and row["end_received_at"] and duration_seconds is None:
            warnings.append("tool-observer-duration-unavailable")
        status_failed = any(status.lower() in _FAILED for status in row["statuses"])
        exit_failed = any(code != 0 for code in row["exit_codes"])
        completed = any(status.lower() == "completed" for status in row["statuses"])
        row.update(observer_duration_seconds=duration_seconds, failed=status_failed or exit_failed, succeeded=completed and bool(row["exit_codes"]) and all(code == 0 for code in row["exit_codes"]))
        tool_rows.append(row)
    if any(not row["statuses"] for row in tool_rows):
        warnings.append("tool-update-missing")
    bottlenecks = [{"tool": row["tool"], "raw_command": row["raw_command"], "observer_duration_seconds": row["observer_duration_seconds"], "failed": row["failed"], "truncated": bool(process.get("truncated"))} for row in tool_rows if row["raw_command"] is not None]
    if process.get("truncated") or isinstance(process.get("events"), Mapping) and process["events"].get("truncated"):
        warnings.append("capture-truncated")
    budget = {"timed_out": process.get("timed_out") if isinstance(process.get("timed_out"), bool) else None, "termination_reason": process.get("termination_reason") if isinstance(process.get("termination_reason"), str) else None, "max_turns_event_count": event_types["max_turns_reached"]}
    return {"process": {"wall_duration_seconds": duration, "exit_code": process.get("exit_code") if isinstance(process.get("exit_code"), int) and not isinstance(process.get("exit_code"), bool) else None, "timed_out": budget["timed_out"], "termination_reason": budget["termination_reason"], "truncated": bool(process.get("truncated"))}, "budget": budget, "native_events": {"stdout_event_count": stdout_events, "event_types": dict(sorted(event_types.items())), "unknown_event_types": dict(sorted(unknown.items())), "error_event_count": event_types["error"], "tool_call_count": len(tools), "tool_failed_count": sum(row["failed"] for row in tool_rows), "tool_succeeded_count": sum(row["succeeded"] for row in tool_rows), "tool_names": dict(sorted(Counter(row["tool"] for row in tool_rows).items())), "invalid_json_lines": invalid, "ignored_stderr_receipts": ignored_stderr, "unusable_stdout_receipts": unusable_stdout, "truncated_receipt_count": truncated_receipts}, "usage": {"reported_terminal_usage": reported_usage, "reported_terminal_usage_source": usage_source, "actual_model_usage": _numeric(terminal_event.get("modelUsage")) if terminal_event and isinstance(terminal_event.get("modelUsage"), Mapping) else None, "usage_event_count": usage_events, "terminal_event_count": len(terminal)}, "runs": _state_rows(navigation, warnings), "tool_chronology_basis": "stdout receipt order and matching toolCallId timestamps only", "tools": tool_rows, "tool_chronology": tool_rows, "bottlenecks": bottlenecks, "warnings": sorted(set(warnings))}
