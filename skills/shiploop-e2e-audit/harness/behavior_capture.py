#!/usr/bin/env python3
"""Create a compact, sanitized observation bundle from one retained E2E trial.

The live trial remains the evidence source.  This module never invokes Grok,
ShipLoop, a browser, or a project command.  It only hashes and normalizes files
already retained beneath a trial directory.  In particular, it deliberately
omits prompts, paths, model prose, shell commands, tool arguments, and raw
stdout/stderr/event lines from its portable output.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping


SCHEMA = "shiploop-e2e-live-behavior/1"
_HASH = re.compile(r"^[0-9a-f]{64}$")
_MAX_JSON_BYTES = 16 * 1024 * 1024
_MAX_EVENT_LINE_BYTES = 1024 * 1024

# These lists are intentionally closed.  A value read from a live transcript is
# not portable merely because it looks harmless; unknown strings become a fixed
# qualification rather than being copied into a fixture.
_STAGES = frozenset(
    {
        "intake", "discovery", "research", "spec", "test-strategy", "plan",
        "prepare", "select-work", "step-plan", "test-spec", "baseline",
        "test-author", "test-red", "implement", "test-green", "test-refine",
        "regression", "document", "skill-assess", "skill-validate",
        "static-checks", "verify", "integrate", "integration-verify",
        "carry-forward", "system-test-author", "system-test", "product-acceptance",
        "release-plan", "release-check", "release", "release-verify",
        "operations", "handoff", "done",
    }
)
# Navigator protocol 4 is the only observed protocol; any other protocol is
# retained only as an ``unsupported-protocol`` qualification.
_SUPPORTED_PROTOCOLS = frozenset({4})
# The live runner's public partial-stop keys (run.PARTIAL_STAGES).
_STOP_STAGES = frozenset({"intake", "discovery", "research", "spec", "test-strategy", "plan"})
_STATE_STATUSES = frozenset({"active", "paused", "blocked", "halted", "done"})
_OUTCOMES = frozenset({"done", "repeat", "blocked", "replan", "reconcile"})
_NATIVE_TYPES = frozenset(
    {
        "available_commands", "end", "plan", "text", "thought", "tool_call",
        "tool_call_update", "usage", "error",
    }
)
_NATIVE_STATUSES = frozenset(
    {"pending", "started", "in_progress", "completed", "failed", "cancelled"}
)
_REASONING = frozenset({"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"})
_PERMISSION = frozenset({"default", "bypassPermissions"})
_SCENARIO_KINDS = frozenset({"create", "feature", "refine", "refinement"})
_OVERALL_STATUSES = frozenset(
    {
        "passed", "product-failed", "invalid-trial", "awaiting-independent-verification",
        "incomplete", "run-isolation-failed", "partial-smoke-passed",
        "partial-smoke-failed", "partial-smoke-overshot", "interrupted",
        "harness-or-environment-error", "unverified",
    }
)
_STATUS_VALUES = _OVERALL_STATUSES | frozenset(
    {
        "failed", "exited", "failed-or-budget-exhausted", "selected-stable",
        "changed-during-run-invalid", "stable", "changed-during-observation-invalid",
        "declared-complete-return-observed", "unverified-no-new-matching-state",
        "not-applicable", "observed", "stopped-at-observed-boundary",
    }
)
_STATUS_KEYS = (
    "overall", "product", "process", "skill", "observer", "protocol",
    "incrementality", "lifecycle", "partial",
)


class _InvalidJson(ValueError):
    """Raised internally for an unsupported retained JSON document."""


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _source_record(path: Path) -> dict[str, Any]:
    """Return only a logical source name, presence, bytes, and digest."""
    if not path.is_file():
        return {"present": False}
    try:
        sha256, size = _sha256_file(path)
    except OSError:
        return {"present": False, "readable": False}
    return {"present": True, "bytes": size, "sha256": sha256}


def _no_duplicates(items: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in items:
        if key in value:
            raise _InvalidJson("duplicate-key")
        value[key] = item
    return value


def _read_json_source(path: Path) -> tuple[dict[str, Any] | None, str | None, dict[str, Any]]:
    """Read, hash, and parse a bounded JSON source from the same bytes."""
    try:
        if not path.is_file():
            return None, "missing", {"present": False}
        if path.stat().st_size > _MAX_JSON_BYTES:
            sha256, size = _sha256_file(path)
            return None, "oversized", {"present": True, "bytes": size, "sha256": sha256}
        data = path.read_bytes()
    except (OSError, UnicodeError, json.JSONDecodeError, _InvalidJson):
        return None, "malformed", {"present": False, "readable": False}
    record = {"present": True, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_no_duplicates)
    except (UnicodeError, json.JSONDecodeError, _InvalidJson):
        return None, "malformed", record
    if not isinstance(value, dict):
        return None, "not-object", record
    return value, None, record


def _hash_json(value: Any) -> str | None:
    try:
        encoded = json.dumps(
            value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError):
        return None
    return hashlib.sha256(encoded).hexdigest()


def _safe_hash(value: Any) -> str | None:
    return value if isinstance(value, str) and _HASH.fullmatch(value) else None


def _safe_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    if isinstance(value, float):
        return round(value, 3)
    return value


def _safe_stage(value: Any, protocol_version: int | None) -> str | None:
    allowed = _STAGES if protocol_version in _SUPPORTED_PROTOCOLS else frozenset()
    return value if isinstance(value, str) and value in allowed else None


def _safe_status(value: Any) -> str | None:
    return value if isinstance(value, str) and value in _STATE_STATUSES else None


def _safe_result_outcome(value: Any) -> str | None:
    return value if isinstance(value, str) and value in _OUTCOMES else None


def _append_once(values: list[str], code: str) -> None:
    if code not in values:
        values.append(code)


def _state_from_markdown(data: bytes) -> dict[str, Any] | None:
    """Parse only the fenced state object retained by the evidence archive."""
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeError:
        return None
    openings = [index for index, line in enumerate(lines) if line.strip() == "```shiploop-state"]
    if len(openings) != 1:
        return None
    closing = next((index for index in range(openings[0] + 1, len(lines)) if lines[index].strip() == "```"), None)
    if closing is None:
        return None
    try:
        value = json.loads("\n".join(lines[openings[0] + 1:closing]), object_pairs_hook=_no_duplicates)
    except (json.JSONDecodeError, _InvalidJson):
        return None
    return value if isinstance(value, dict) else None


def _read_prompt(trial: Path, manifest: Mapping[str, Any], limits: list[str]) -> str | None:
    path = trial / "prompt.txt"
    try:
        if not path.is_file() or path.stat().st_size > _MAX_JSON_BYTES:
            _append_once(limits, "prompt-identity-unavailable")
            return None
        data = path.read_bytes()
        prompt = data.decode("utf-8")
    except (OSError, UnicodeError):
        _append_once(limits, "prompt-identity-unavailable")
        return None
    declared = _safe_hash(manifest.get("prompt_sha256"))
    if declared is None or hashlib.sha256(data).hexdigest() != declared:
        _append_once(limits, "prompt-identity-mismatch")
        return None
    return prompt


def _matching_prompt(value: Any, prompt: str | None) -> bool:
    if prompt is None or not isinstance(value, str):
        return False
    return value in {prompt, prompt.removeprefix("/shiploop ")}


def _initial_states(trial: Path, initial: Mapping[str, Any] | None, limits: list[str]) -> list[dict[str, Any]]:
    """Read only safely rooted state blobs from a retained initial archive."""
    if not isinstance(initial, Mapping):
        _append_once(limits, "initial-archive-unavailable")
        return []
    output_value = initial.get("output")
    if not isinstance(output_value, str) or not output_value:
        _append_once(limits, "initial-archive-unavailable")
        return []
    try:
        archive = Path(output_value).resolve(strict=True)
        trial_root = trial.resolve(strict=True)
        archive.relative_to(trial_root)
    except (OSError, RuntimeError, ValueError):
        _append_once(limits, "initial-archive-outside-trial")
        return []
    rows = initial.get("artifacts")
    if not isinstance(rows, list):
        _append_once(limits, "initial-archive-malformed")
        return []
    states: list[dict[str, Any]] = []
    for artifact in rows:
        if not isinstance(artifact, Mapping) or artifact.get("kind") != "state":
            continue
        relative = artifact.get("archive_path")
        declared = _safe_hash(artifact.get("sha256"))
        if not isinstance(relative, str) or not relative or declared is None:
            _append_once(limits, "initial-archive-malformed")
            continue
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            _append_once(limits, "initial-archive-malformed")
            continue
        try:
            candidate = archive / relative_path
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(archive)
            if not resolved.is_file() or resolved.is_symlink() or resolved.stat().st_size > _MAX_JSON_BYTES:
                raise ValueError
            data = resolved.read_bytes()
            if hashlib.sha256(data).hexdigest() != declared:
                raise ValueError
        except (OSError, RuntimeError, ValueError):
            _append_once(limits, "initial-archive-malformed")
            continue
        state = _state_from_markdown(data)
        if state is None:
            _append_once(limits, "initial-state-malformed")
            continue
        # Source paths remain internal to the supplemental isolation assessor.
        # They are never copied into the portable behavior bundle.
        states.append({"state": state, "source_path": artifact.get("source_path")})
    return states


def _initial_state_value(row: Mapping[str, Any]) -> Mapping[str, Any] | None:
    value = row.get("state") if isinstance(row, Mapping) else None
    return value if isinstance(value, Mapping) else None


def _initial_archive_verified(limits: Iterable[str]) -> bool:
    blockers = {
        "initial-archive-unavailable", "initial-archive-outside-trial",
        "initial-archive-malformed", "initial-state-malformed", "initial-archive-missing",
        "initial-archive-malformed", "initial-archive-not-object", "initial-archive-oversized",
    }
    return not any(code in blockers for code in limits)


def _synthetic_work_items(
    value: Any, work_map: Mapping[str, str], limits: list[str]
) -> list[dict[str, str]] | None:
    if not isinstance(value, list):
        _append_once(limits, "unsupported-result-work-items")
        return None
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in value:
        raw_id = item.get("id") if isinstance(item, Mapping) else None
        alias = work_map.get(raw_id) if isinstance(raw_id, str) else None
        if alias is None or alias in seen:
            _append_once(limits, "unsupported-result-work-items")
            return None
        seen.add(alias)
        rows.append({"id": alias, "title": f"Synthetic work item {alias}"})
    return rows


def _synthetic_choices(value: Any, limits: list[str]) -> dict[str, bool] | None:
    if not isinstance(value, Mapping) or set(value) != {"skill_required"}:
        _append_once(limits, "unsupported-result-choices")
        return None
    flag = value.get("skill_required")
    if type(flag) is not bool:
        _append_once(limits, "unsupported-result-choices")
        return None
    return {"skill_required": flag}


def _canonical_state(
    state: Mapping[str, Any], *, initial_states: Iterable[Mapping[str, Any]], prompt: str | None,
    limits: list[str],
) -> tuple[dict[str, Any], bool]:
    """Normalize one selected state without preserving its free-text fields."""
    protocol = state.get("navigator_protocol_version")
    protocol_version = protocol if type(protocol) is int and protocol in _SUPPORTED_PROTOCOLS else None
    if protocol_version is None:
        _append_once(limits, "unsupported-protocol")
    stage = _safe_stage(state.get("stage"), protocol_version)
    status = _safe_status(state.get("status"))
    if stage is None:
        _append_once(limits, "unsupported-state-stage")
    if status is None:
        _append_once(limits, "unsupported-state-status")

    raw_items = state.get("work_items")
    work_map: dict[str, str] = {}
    items: list[dict[str, str]] = []
    if not isinstance(raw_items, list):
        _append_once(limits, "malformed-work-items")
    else:
        for index, item in enumerate(raw_items, 1):
            if not isinstance(item, Mapping) or not isinstance(item.get("id"), str):
                _append_once(limits, "malformed-work-items")
                continue
            raw_id = item["id"]
            if raw_id in work_map:
                _append_once(limits, "malformed-work-items")
                continue
            alias = f"W{index}"
            work_map[raw_id] = alias
            items.append({"id": alias, "title": f"Synthetic work item {alias}"})

    accepted = state.get("accepted")
    if not isinstance(accepted, Mapping):
        accepted = {}
        _append_once(limits, "malformed-accepted-results")
    raw_history = state.get("history")
    history: list[dict[str, Any]] = []
    history_valid = isinstance(raw_history, list)
    if not history_valid:
        _append_once(limits, "malformed-history")
        raw_history = []
    for index, entry in enumerate(raw_history, 1):
        if not isinstance(entry, Mapping):
            _append_once(limits, "malformed-history")
            history_valid = False
            continue
        entry_stage = _safe_stage(entry.get("stage"), protocol_version)
        outcome = _safe_result_outcome(entry.get("outcome"))
        raw_owner = entry.get("workitem")
        if raw_owner is None:
            owner = "root"
        elif isinstance(raw_owner, str) and raw_owner in work_map:
            owner = work_map[raw_owner]
        else:
            owner = "unsupported"
            _append_once(limits, "unsupported-history-owner")
            history_valid = False
        if entry_stage is None:
            entry_stage = "unsupported"
            _append_once(limits, "unsupported-history-stage")
            history_valid = False
        if outcome is None:
            outcome = "unsupported"
            _append_once(limits, "unsupported-history-outcome")
            history_valid = False
        raw_action = entry.get("action")
        result = accepted.get(raw_action) if isinstance(raw_action, str) else None
        result_sha256 = _hash_json(result) if isinstance(result, Mapping) else None
        if result_sha256 is None:
            _append_once(limits, "missing-accepted-result")
            history_valid = False
        result_outcome = _safe_result_outcome(result.get("outcome")) if isinstance(result, Mapping) else None
        if result_outcome != outcome:
            _append_once(limits, "accepted-result-outcome-mismatch")
            history_valid = False
        normalized_result: dict[str, Any] = {
            "outcome": outcome,
            "summary": f"Recorded acceptance at {entry_stage} (free text omitted).",
        }
        if isinstance(result, Mapping) and "work_items" in result:
            normalized_items = _synthetic_work_items(result.get("work_items"), work_map, limits)
            if normalized_items is None:
                history_valid = False
            else:
                normalized_result["work_items"] = normalized_items
        if isinstance(result, Mapping) and "choices" in result:
            normalized_choices = _synthetic_choices(result.get("choices"), limits)
            if normalized_choices is None:
                history_valid = False
            else:
                normalized_result["choices"] = normalized_choices
        history.append(
            {
                "sequence": index,
                "at": entry_stage,
                "owner": owner,
                "result": normalized_result,
                "status": "accepted",
                "accepted_result_sha256": result_sha256,
            }
        )

    accepted_count = len(accepted)
    history_count = len(raw_history)
    if accepted_count != history_count or len(history) != history_count:
        _append_once(limits, "accepted-history-mismatch")
        history_valid = False

    initial_rows = list(initial_states)
    initial_matching = [
        row for row in initial_rows
        if (initial_state := _initial_state_value(row)) is not None
        and _matching_prompt(initial_state.get("prompt"), prompt)
    ]
    current_run_id = state.get("run_id")
    preexisting = (
        isinstance(current_run_id, str)
        and any(
            (initial_state := _initial_state_value(row)) is not None
            and initial_state.get("run_id") == current_run_id
            for row in initial_matching
        )
    )
    if not _initial_archive_verified(limits):
        preexisting_scope = "unverified"
    else:
        preexisting_scope = "captured-initial-archive-only"

    revision = state.get("revision")
    return (
        {
            "protocol_version": protocol_version,
            "final": {"stage": stage or "unverified", "status": status or "unverified"},
            "revision": revision if type(revision) is int and revision >= 0 else None,
            "accepted_count": accepted_count,
            "history_count": history_count,
            "work_items": items,
            "accepted_history": history,
            "preexisting": {
                "scope": preexisting_scope,
                "initial_archive_verified": _initial_archive_verified(limits),
                "initial_state_count": len(initial_rows),
                "matching_initial_state_count": len(initial_matching),
                "selected_run_preexisting": preexisting,
            },
        },
        history_valid,
    )


def _select_state(
    navigation: Mapping[str, Any] | None, prompt: str | None, initial_states: Iterable[Mapping[str, Any]],
    limits: list[str],
) -> tuple[dict[str, Any] | None, bool]:
    if not isinstance(navigation, Mapping):
        _append_once(limits, "navigation-unavailable")
        return None, False
    rows = navigation.get("states")
    if not isinstance(rows, list):
        _append_once(limits, "navigation-malformed")
        return None, False
    matches = [row.get("state") for row in rows if isinstance(row, Mapping)
               and isinstance(row.get("state"), Mapping)
               and _matching_prompt(row["state"].get("prompt"), prompt)]
    if len(matches) != 1:
        _append_once(limits, "matching-run-unverified")
        return None, False
    return _canonical_state(matches[0], initial_states=initial_states, prompt=prompt, limits=limits)


def _event_payload(value: Mapping[str, Any]) -> Mapping[str, Any] | None:
    payload = value.get("payload")
    if isinstance(payload, Mapping):
        return payload
    return value if isinstance(value.get("type"), str) else None


def _exit_bucket(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return "zero" if value == 0 else "nonzero"


def _summarize_events(path: Path) -> tuple[dict[str, Any], bool]:
    """Hash and summarize events in a single bounded streaming pass."""
    if not path.is_file():
        return {"present": False}, False
    digest = hashlib.sha256()
    bytes_read = 0
    lines = 0
    in_oversized_line = False
    type_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    exit_counts: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    complete = True
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.readline(_MAX_EVENT_LINE_BYTES + 1)
                if not chunk:
                    break
                digest.update(chunk)
                bytes_read += len(chunk)
                if in_oversized_line:
                    if chunk.endswith(b"\n"):
                        lines += 1
                        in_oversized_line = False
                    continue
                if len(chunk) > _MAX_EVENT_LINE_BYTES and not chunk.endswith(b"\n"):
                    errors["oversized-line"] += 1
                    in_oversized_line = True
                    complete = False
                    continue
                lines += 1
                try:
                    row = json.loads(chunk.decode("utf-8"), object_pairs_hook=_no_duplicates)
                except (UnicodeError, json.JSONDecodeError, _InvalidJson):
                    errors["malformed-json"] += 1
                    complete = False
                    continue
                if not isinstance(row, Mapping):
                    errors["non-object"] += 1
                    complete = False
                    continue
                # Capture wraps both streams.  A JSON-looking diagnostic on
                # stderr is not host-native protocol evidence.
                stream = row.get("stream")
                if stream == "stderr":
                    errors["stderr-wrapper"] += 1
                    continue
                if stream is not None and stream != "stdout":
                    errors["unknown-event-stream"] += 1
                    complete = False
                    continue
                if row.get("line_truncated") is True:
                    errors["line-truncated"] += 1
                    complete = False
                    continue
                payload = _event_payload(row)
                if payload is None:
                    errors["non-native-event"] += 1
                    continue
                native_type = payload.get("type")
                if not isinstance(native_type, str) or native_type not in _NATIVE_TYPES:
                    errors["unknown-native-event"] += 1
                    complete = False
                    continue
                type_counts[native_type] += 1
                status = payload.get("status")
                if status is not None:
                    if isinstance(status, str) and status in _NATIVE_STATUSES:
                        status_counts[status] += 1
                        if status == "failed":
                            errors["native-failed-status"] += 1
                    else:
                        errors["unknown-native-status"] += 1
                        complete = False
                if native_type == "error":
                    errors["native-error-event"] += 1
                raw_output = payload.get("rawOutput")
                if isinstance(raw_output, Mapping):
                    bucket = _exit_bucket(raw_output.get("exitCode"))
                    if bucket is not None:
                        exit_counts[bucket] += 1
                        if bucket == "nonzero":
                            errors["native-nonzero-exit"] += 1
                bucket = _exit_bucket(payload.get("exitCode"))
                if bucket is not None:
                    exit_counts[bucket] += 1
                    if bucket == "nonzero":
                        errors["native-nonzero-exit"] += 1
    except OSError:
        return {"present": True, "readable": False}, False
    if in_oversized_line:
        lines += 1
        errors["truncated-oversized-line"] += 1
        complete = False
    if not type_counts:
        # A separately derived metadata file cannot substitute for a retained
        # native stdout stream when deciding whether this observation is whole.
        errors["native-stdout-unobserved"] += 1
        complete = False
    return (
        {
            "present": True,
            "bytes": bytes_read,
            "sha256": digest.hexdigest(),
            "line_count": lines,
            "native_event_counts": dict(sorted(type_counts.items())),
            "native_status_counts": dict(sorted(status_counts.items())),
            "exit_code_counts": dict(sorted(exit_counts.items())),
            "error_counts": dict(sorted(errors.items())),
        },
        complete,
    )


def _requested_settings(manifest: Mapping[str, Any] | None, limits: list[str]) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        _append_once(limits, "manifest-unavailable")
        return {
            "timeout_seconds": None, "max_turns": None, "reasoning_effort": "unverified",
            "permission_mode": "unverified", "partial": None, "stop_after_stage": None,
            "scenario_kind": "unverified", "prompt_sha256": None,
        }
    scenario = manifest.get("scenario")
    kind = scenario.get("kind") if isinstance(scenario, Mapping) else None
    raw_stop = manifest.get("stop_after_stage")
    stop = raw_stop if isinstance(raw_stop, str) and raw_stop in _STOP_STAGES else None
    if manifest.get("stop_after_stage") is not None and stop is None:
        _append_once(limits, "unsupported-stop-stage")
    effort = manifest.get("reasoning_effort_requested")
    permission = manifest.get("permission_mode")
    if not isinstance(effort, str) or effort not in _REASONING:
        _append_once(limits, "unsupported-reasoning-effort")
    if not isinstance(permission, str) or permission not in _PERMISSION:
        _append_once(limits, "unsupported-permission-mode")
    if not isinstance(kind, str) or kind not in _SCENARIO_KINDS:
        _append_once(limits, "unsupported-scenario-kind")
    return {
        "timeout_seconds": _safe_number(manifest.get("timeout_seconds")),
        "max_turns": manifest.get("max_turns") if type(manifest.get("max_turns")) is int and manifest["max_turns"] > 0 else None,
        "reasoning_effort": effort if isinstance(effort, str) and effort in _REASONING else "unverified",
        "permission_mode": permission if isinstance(permission, str) and permission in _PERMISSION else "unverified",
        "partial": manifest.get("partial") if type(manifest.get("partial")) is bool else None,
        "stop_after_stage": stop,
        "scenario_kind": kind if isinstance(kind, str) and kind in _SCENARIO_KINDS else "unverified",
        "prompt_sha256": _safe_hash(manifest.get("prompt_sha256")),
    }


def _process(process: Any, limits: list[str]) -> dict[str, Any]:
    if not isinstance(process, Mapping):
        _append_once(limits, "process-unavailable")
        return {"exit_code": None, "timed_out": None, "truncated": None,
                "capture_error": None, "duration_seconds": None, "termination": "unverified"}
    exit_code = process.get("exit_code")
    if type(exit_code) is not int:
        exit_code = None
    reason = process.get("termination_reason")
    termination = reason if reason is None or isinstance(reason, str) and reason in {"requested_boundary", "timeout", "signal"} else "other"
    return {
        "exit_code": exit_code,
        "timed_out": process.get("timed_out") if type(process.get("timed_out")) is bool else None,
        "truncated": process.get("truncated") if type(process.get("truncated")) is bool else None,
        "capture_error": process.get("capture_error") is not None,
        "duration_seconds": _safe_number(process.get("duration_seconds")),
        "termination": termination,
    }


def _original_statuses(result: Mapping[str, Any] | None, limits: list[str]) -> dict[str, str]:
    statuses = result.get("statuses") if isinstance(result, Mapping) else None
    if not isinstance(statuses, Mapping):
        _append_once(limits, "original-statuses-unavailable")
        return {"overall": "unverified"}
    output: dict[str, str] = {}
    for key in _STATUS_KEYS:
        if key not in statuses:
            continue
        value = statuses.get(key)
        if isinstance(value, str) and value in _STATUS_VALUES:
            output[key] = value
        else:
            output[key] = "unverified"
            _append_once(limits, "unsupported-original-status")
    if "overall" not in output:
        output["overall"] = "unverified"
        _append_once(limits, "original-statuses-unavailable")
    return output


def _stability(result: Mapping[str, Any] | None, manifest: Mapping[str, Any] | None) -> dict[str, Any]:
    result = result if isinstance(result, Mapping) else {}
    manifest = manifest if isinstance(manifest, Mapping) else {}
    return {
        "selected_skill_sha256": _safe_hash(result.get("skill_digest")),
        "selected_skill_stable": result.get("skill_stable") if type(result.get("skill_stable")) is bool else None,
        "observer_before_sha256": _safe_hash(result.get("observer_digest")),
        "observer_after_sha256": _safe_hash(result.get("observer_after_digest")),
        "observer_stable": result.get("observer_stable") if type(result.get("observer_stable")) is bool else None,
        "harness_sha256": _safe_hash(manifest.get("harness_sha256")),
        "baseline_digest": _safe_hash(result.get("baseline_digest")),
        "candidate_digest": _safe_hash(result.get("candidate_digest")),
    }


def _derive_isolation(
    initial_states: Iterable[Mapping[str, Any]], navigation: Mapping[str, Any] | None,
    result: Mapping[str, Any] | None, prompt: str | None, limits: list[str],
) -> dict[str, Any]:
    """Use the existing pure assessor when archives support it, never alter grade."""
    if prompt is None or not isinstance(navigation, Mapping):
        return {"status": "unverified", "basis": "unavailable"}
    try:
        from recovery_isolation import assess_isolation

        initial_rows = []
        for index, record in enumerate(initial_states):
            state = _initial_state_value(record)
            source_path = record.get("source_path") if isinstance(record, Mapping) else None
            if state is None:
                continue
            # The archive source path is needed only to correlate a recorded
            # `next` callback.  A missing/unsafe locator stays synthetic and
            # therefore cannot turn an unknown attribution into a pass/fail.
            if not isinstance(source_path, str) or not Path(source_path).is_absolute():
                source_path = f"/initial-unattributed/{index}/state.md"
            initial_rows.append({"source_path": source_path, "state": state})
        initial = {"states": initial_rows}
        final_rows = navigation.get("states")
        final = {"states": final_rows if isinstance(final_rows, list) else []}
        events = result.get("host_observations") if isinstance(result, Mapping) else {}
        # Host observations are already a derived local summary.  It has no raw
        # transcript text here, and the assessor needs only attributed argv tails.
        if not isinstance(events, Mapping):
            events = {}
        assessment = assess_isolation(initial, final, events, prompt=prompt)
        status = assessment.get("status")
        if status not in {"pass", "fail", "unverified", "not-applicable"}:
            raise ValueError
        return {"status": status, "basis": "supplemental-recovery-isolation/1"}
    except (ImportError, KeyError, TypeError, ValueError):
        _append_once(limits, "supplemental-isolation-unavailable")
        return {"status": "unverified", "basis": "unavailable"}


def _replay_metadata(dag: Mapping[str, Any] | None, original: Mapping[str, str]) -> dict[str, Any]:
    """Qualify a retained trial; none is exported as a DAG replay case.

    DAG replay uses independently authored synthetic protocol 4 cases. A
    retained trial does not record the complete producer and Improve callback
    sequence, and the exporter never invents one.
    """
    if not isinstance(dag, Mapping):
        return {"status": "not-replayable", "reason": "dag-unavailable"}
    preexisting = dag.get("preexisting")
    if isinstance(preexisting, Mapping) and preexisting.get("selected_run_preexisting") is True:
        return {"status": "not-replayable", "reason": "preexisting-run-not-fresh-one-shot"}
    if original.get("overall") in {"interrupted", "harness-or-environment-error", "incomplete", "invalid-trial"}:
        return {"status": "not-replayable", "reason": "original-live-trial-ineligible"}
    if dag.get("protocol_version") not in _SUPPORTED_PROTOCOLS:
        return {"status": "not-replayable", "reason": "unsupported-protocol"}
    return {"status": "not-replayable", "reason": "callback-sequence-not-derivable"}


def export_trial(trial: Path) -> dict[str, Any]:
    """Return a portable observation bundle for ``trial`` without executing it."""
    trial = Path(trial)
    source_paths = {
        "result.json": trial / "result.json",
        "manifest.json": trial / "manifest.json",
        "navigation.json": trial / "navigation.json",
        "events.jsonl": trial / "capture" / "events.jsonl",
        "initial-evidence.json": trial / "initial-evidence.json",
    }
    limits: list[str] = []
    if not trial.is_dir():
        sources = {name: _source_record(path) for name, path in source_paths.items()}
        return {
            "schema": SCHEMA,
            "capture_status": "unavailable",
            "provenance": {"source_hashes": sources, "canonical_result_sha256": None},
            "limitations": ["trial-directory-unavailable"],
        }

    result, result_error, result_source = _read_json_source(source_paths["result.json"])
    manifest, manifest_error, manifest_source = _read_json_source(source_paths["manifest.json"])
    navigation, navigation_error, navigation_source = _read_json_source(source_paths["navigation.json"])
    initial, initial_error, initial_source = _read_json_source(source_paths["initial-evidence.json"])
    for name, error in (
        ("result", result_error), ("manifest", manifest_error),
        ("navigation", navigation_error), ("initial-archive", initial_error),
    ):
        if error is not None:
            _append_once(limits, f"{name}-{error}")

    prompt = _read_prompt(trial, manifest or {}, limits)
    initial_states = _initial_states(trial, initial, limits)
    dag, history_valid = _select_state(navigation, prompt, initial_states, limits)
    if dag is not None and not history_valid:
        _append_once(limits, "dag-history-partial")
    events, events_complete = _summarize_events(source_paths["events.jsonl"])
    event_source = {
        key: events[key] for key in ("present", "readable", "bytes", "sha256") if key in events
    }
    sources = {
        "result.json": result_source,
        "manifest.json": manifest_source,
        "navigation.json": navigation_source,
        "events.jsonl": event_source,
        "initial-evidence.json": initial_source,
    }
    if not events_complete:
        _append_once(limits, "native-events-partial")

    original = _original_statuses(result, limits)
    process = _process(result.get("process") if isinstance(result, Mapping) else None, limits)
    if process["truncated"] is True:
        _append_once(limits, "process-truncated")
    if process["capture_error"] is True:
        _append_once(limits, "process-capture-error")
    process_eligible = (
        process["exit_code"] == 0
        and process["timed_out"] is False
        and process["truncated"] is False
        and process["capture_error"] is False
    )
    if not process_eligible:
        _append_once(limits, "process-incomplete")
    behavior = {
        "schema": SCHEMA,
        "capture_status": "complete",
        "provenance": {
            "canonical_result_sha256": sources["result.json"].get("sha256"),
            "source_hashes": sources,
            "scope": "sanitized observational export; no command, model, workspace, return, or product behavior was replayed.",
        },
        "requested_settings": _requested_settings(manifest, limits),
        "source_stability": _stability(result, manifest),
        "process": process,
        "original_statuses": original,
        "native_events": events,
        "dag": dag if dag is not None else {
            "status": "unverified", "accepted_history": [],
            "preexisting": {"scope": "unverified", "initial_state_count": len(initial_states),
                            "matching_initial_state_count": 0, "selected_run_preexisting": None},
        },
        "supplemental_isolation": _derive_isolation(initial_states, navigation, result, prompt, limits),
        "limitations": limits,
    }
    behavior["replay"] = _replay_metadata(
        behavior["dag"] if isinstance(behavior["dag"], Mapping) else None,
        original,
    )
    # The result, manifest, navigation, and native event stream are the minimum
    # source set.  A parsed selected state is additionally required for a
    # complete DAG observation.  Initial archive absence itself is a retained
    # qualification, not a fabricated fresh-run conclusion.
    required = (result is not None and manifest is not None and navigation is not None
                and events.get("present") is True and dag is not None and history_valid
                and process_eligible)
    behavior["capture_status"] = "complete" if required and events_complete else "partial"
    if result is None and manifest is None and navigation is None and not events.get("present"):
        behavior["capture_status"] = "unavailable"
    return behavior


def _write_json(path: Path, value: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def _write_new_json(path: Path, value: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, indent=2, sort_keys=True) + "\n"
    # `x` is intentionally used instead of check-then-replace: an export is
    # immutable evidence and a competing writer must not overwrite one.
    with path.open("x", encoding="utf-8") as handle:
        handle.write(encoded)
    return path


def write_trial_behavior(trial: Path) -> Path:
    """Write the sanitized behavior bundle beside the retained trial."""
    trial = Path(trial)
    return _write_json(trial / "behavior.json", export_trial(trial))


def _arguments() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a sanitized ShipLoop E2E behavior export.")
    parser.add_argument("--trial", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="New behavior JSON path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _arguments().parse_args(argv)
    if args.output.exists():
        raise SystemExit("--output must name a new JSON file")
    bundle = export_trial(args.trial)
    _write_new_json(args.output, bundle)
    print(json.dumps({"schema": SCHEMA, "capture_status": bundle["capture_status"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
