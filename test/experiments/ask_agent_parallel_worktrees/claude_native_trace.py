#!/usr/bin/env python3
"""Audit retained native Claude Code worker evidence for one experiment run.

This is an offline observer. It never launches a model and never treats worker
narrative as proof. Agent identity comes from the root stream, task lifecycle,
native hooks, and retained Claude transcripts.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import sys
from typing import Any

from claude_briefs import worker_prefix
from claude_controller import agent_arguments_match, filter_local_bash_task_events


SCHEMA = "ask-agent.claude-native-audit/v1"
DISPATCH_SCHEMA = "ask-agent.claude-dispatch-index/v1"
ASSIGNMENT_SCHEMA = "ask-agent.claude-dispatch-assignment/v1"
TRANSCRIPT_SCHEMA = "ask-agent.claude-transcript-index/v1"
FORBIDDEN_RESUME_FLAGS = {"--resume", "--continue", "--fork-session", "--fork", "--isolation"}
ERROR_TEXT = re.compile(
    r"\b(permission denied|permission error|not authorized|unauthorized|authentication failed|"
    r"model (?:not found|unavailable|error|failed|failure)|failed to load model)\b",
    re.IGNORECASE,
)
TRUNCATED_TEXT = re.compile(r"(?:\[\s*output truncated\s*\]|\btruncated output\b|\boutput omitted\b)", re.IGNORECASE)


class TraceError(RuntimeError):
    """The retained evidence is malformed or contradicts the requested claim."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    if not isinstance(value, dict):
        raise TraceError(f"{path} must contain a JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise TraceError(f"{path} is empty")
    result = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            raise TraceError(f"{path} has a blank line at {number}")
        value = json.loads(line, object_pairs_hook=_unique_object)
        if not isinstance(value, dict):
            raise TraceError(f"{path} has a non-object row at {number}")
        result.append(value)
    return result


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise TraceError(f"evidence is not a regular file: {path}")
    return _sha256(path.read_bytes())


def _ref(path: Path, line: int | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"path": str(path.resolve(strict=False))}
    if line is not None:
        value["line"] = line
    if path.is_file() and not path.is_symlink():
        value["sha256"] = _file_sha(path)
    return value


def _inside_run(run: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise TraceError(f"{label} must be a nonempty path")
    path = Path(value)
    if not path.is_absolute():
        raise TraceError(f"{label} must be absolute; the auditor does not invent a cwd")
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(run)
    except ValueError as exc:
        raise TraceError(f"{label} resolves outside this run: {resolved}") from exc
    return resolved


def _finite(value: Any) -> float | None:
    if type(value) not in (int, float):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _gate(report: dict[str, Any], name: str, passed: bool, detail: str,
          evidence: list[dict[str, Any]] | None = None, *, incomplete: bool = False) -> None:
    status = "PASS" if passed else ("INCOMPLETE" if incomplete else "FAIL")
    report["checks"][name] = {"status": status, "detail": detail, "evidence": evidence or []}
    if not passed:
        report["errors"].append(f"{name}: {detail}")


def _content_blocks(record: dict[str, Any]) -> list[dict[str, Any]]:
    message = record.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if isinstance(content, dict):
        content = [content]
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict)]


def _calls_and_results(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    calls: list[dict[str, Any]] = []
    results: dict[str, list[dict[str, Any]]] = {}
    for line, record in enumerate(records, 1):
        # Forwarded child events are mirrors, not actions by the root context.
        # Their native identity is checked in _parent_flow; child transcripts
        # supply the authoritative child call/result pairs.
        if record.get("parent_tool_use_id") is not None or record.get("agent_id") is not None:
            if not all(isinstance(record.get(key), str) and record[key]
                       for key in ("parent_tool_use_id", "agent_id")):
                raise TraceError("forwarded child event has incomplete native identity")
            continue
        for block in _content_blocks(record):
            if block.get("type") == "tool_use":
                calls.append({
                    "line": line,
                    "id": block.get("id"),
                    "name": block.get("name"),
                    "input": block.get("input") if isinstance(block.get("input"), dict) else {},
                    "record": record,
                })
            elif block.get("type") == "tool_result":
                use_id = block.get("tool_use_id")
                results.setdefault(str(use_id), []).append({**block, "line": line})
    return calls, results


def _result_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_result_text(item.get("text", "")) if isinstance(item, dict) else str(item)
                         for item in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return "" if value is None else str(value)


def _tool_result_ok(call: dict[str, Any], results: dict[str, list[dict[str, Any]]],
                    *, native_spawn: bool = False) -> bool:
    rows = results.get(str(call.get("id")), [])
    if len(rows) != 1:
        return False
    row = rows[0]
    if native_spawn or call.get("name") in {"Read", "Write", "Edit"}:
        # Successful native file tools and async acknowledgements may omit
        # is_error. Bash helper JSON still requires explicit false.
        if row.get("is_error") is not None and row.get("is_error") is not False:
            return False
    elif row.get("is_error") is not False:
        return False
    text = _result_text(row.get("content"))
    return (bool(text.strip()) and TRUNCATED_TEXT.search(text) is None
            and "<tool_use_error>" not in text)


def _tool_result_json(call: dict[str, Any], results: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    rows = results.get(str(call.get("id")), [])
    if len(rows) != 1 or rows[0].get("is_error") is not False:
        raise TraceError(f"{call.get('name')} has no unique successful native tool result")
    text = _result_text(rows[0].get("content"))
    if TRUNCATED_TEXT.search(text):
        raise TraceError(f"{call.get('name')} native result is truncated")
    try:
        value = json.loads(text, object_pairs_hook=_unique_object)
    except (ValueError, TypeError) as exc:
        raise TraceError(f"{call.get('name')} native result is not one complete JSON object") from exc
    if not isinstance(value, dict):
        raise TraceError(f"{call.get('name')} native result is not a JSON object")
    return value


def _event_errors(records: list[dict[str, Any]]) -> list[str]:
    errors = []
    for line, record in enumerate(records, 1):
        subtype = str(record.get("subtype", "")).lower()
        if record.get("type") == "error" or subtype in {
            "error", "api_error", "model_error", "permission_error", "authentication_error",
        }:
            errors.append(f"line {line}: typed error event {record.get('type')}/{subtype}")
        if record.get("is_error") is True or record.get("error") not in (None, False, "", {}):
            errors.append(f"line {line}: error field is present")
        if ERROR_TEXT.search(json.dumps(record, sort_keys=True, ensure_ascii=False)):
            errors.append(f"line {line}: model or permission error text")
    return errors


def _tool_flag(tokens: list[str], flag: str) -> list[str]:
    found = []
    for index, token in enumerate(tokens):
        if token == flag and index + 1 < len(tokens):
            found.append(tokens[index + 1])
        elif token.startswith(flag + "="):
            found.append(token.split("=", 1)[1])
    return found


def _tokens_after_cd(command: str, expected_root: Path | None = None) -> tuple[list[str], bool]:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return [], False
    if len(tokens) < 4 or tokens[0] != "cd" or tokens[2] != "&&":
        return tokens, False
    if expected_root is not None and Path(tokens[1]).resolve(strict=False) != expected_root.resolve(strict=False):
        return tokens[3:], False
    return tokens[3:], True


def _parent_command_tokens(command: str) -> list[str]:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return []
    if len(tokens) >= 4 and tokens[0] == "cd" and tokens[2] == "&&":
        return tokens[3:]
    return tokens


def _is_external_model_command(tokens: list[str]) -> bool:
    names = {"claude", "codex", "grok", "gemini", "aider"}
    for token in tokens:
        name = Path(token).name.lower()
        if name in names or name in {f"{item}.exe" for item in names}:
            return True
    return False


def _verify_post_exit(run: Path, manifest: dict[str, Any], process: dict[str, Any],
                      report: dict[str, Any]) -> None:
    operator = run / "operator"
    refs = [operator / name for name in (
        "process-result.json", "integrity-result.json", "post-exit-verification.json", "post-exit-result.json",
    )]
    try:
        integrity = _read_json(refs[1])
        verification = _read_json(refs[2])
        post = _read_json(refs[3])
        passed = (
            process.get("exit_code") == 0
            and type(process.get("exit_code")) is int
            and post.get("status") == "PASS"
            and post.get("passed") is True
            and post.get("parent_exit_code") == 0
            and post.get("filesystem_passed") is True
            and post.get("verifier_exit_code") == 0
            and integrity.get("passed") is True
            and isinstance(integrity.get("checks"), dict)
            and bool(integrity["checks"])
            and all(value is True for value in integrity["checks"].values())
            and verification.get("run_id") == manifest.get("run_id")
            and verification.get("passed") is True
            and verification.get("errors") == []
            and isinstance(verification.get("checks"), dict)
            and bool(verification["checks"])
            and all(value is True for value in verification["checks"].values())
        )
        _gate(report, "shared_post_exit_filesystem", passed,
              "Parent exit, frozen-input integrity, and fresh post-exit fixture verification all pass"
              if passed else "Shared post-exit, integrity, process, or fixture evidence is not a complete pass",
              [_ref(path) for path in refs])
    except FileNotFoundError as exc:
        _gate(report, "shared_post_exit_filesystem", False, f"Required shared verifier evidence is missing: {exc}",
              [_ref(path) for path in refs], incomplete=True)
    except (OSError, ValueError, TraceError) as exc:
        _gate(report, "shared_post_exit_filesystem", False, f"Shared verifier evidence is malformed: {exc}",
              [_ref(path) for path in refs], incomplete=False)


def _manifest_workers(manifest: dict[str, Any]) -> tuple[list[str], dict[str, dict[str, Any]]]:
    count = manifest.get("workers")
    expected = [str(i) for i in range(1, count + 1)] if type(count) is int and count in (3, 5) else []
    assignments = manifest.get("task_assignments")
    ids = [row.get("worker_id") for row in assignments if isinstance(row, dict)] if isinstance(assignments, list) else []
    if (manifest.get("schema_version") != 1 or not expected
            or manifest.get("worker_ids") != expected or ids != expected):
        raise TraceError("manifest must define three or five ordered task assignments")
    by_id = {row["worker_id"]: row for row in assignments}
    if [by_id[worker_id].get("path") for worker_id in expected] != [
        f"src/step_{worker_id}.py" for worker_id in expected
    ]:
        raise TraceError("manifest task paths do not match the owned worker files")
    return expected, by_id


def _dispatch(run: Path, expected: list[str], manifest: dict[str, Any],
              report: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    op = run / "operator"
    index_path = op / "claude-dispatch" / "index.json"
    setup_path = op / "setup-result.json"
    treatment_path = op / "treatment.json"
    try:
        index = _read_json(index_path)
        setup = _read_json(setup_path)
        treatment = _read_json(treatment_path)
        if (index.get("schema") != DISPATCH_SCHEMA or index.get("run_id") != manifest.get("run_id")
                or index.get("manifest_sha256") != _file_sha(run / "manifest.json")
                or index.get("common_index_path") != str((op / "compact-dispatch" / "index.json").resolve())
                or index.get("common_index_sha256") != _file_sha(op / "compact-dispatch" / "index.json")
                or setup.get("status") != "PREPARED" or setup.get("run_id") != manifest.get("run_id")
                or setup.get("treatment") != "compact"
                or setup.get("compact_startup_contract") != "action-packet/v1"
                or treatment.get("treatment") != "compact" or treatment.get("version") != 4
                or treatment.get("verification_output") != "summary-v1"):
            raise TraceError("dispatch index, setup, or treatment is not this prepared compact v4 run")
        setup_rows = setup.get("workers")
        assignments = index.get("assignments")
        if not isinstance(setup_rows, list) or not isinstance(assignments, list):
            raise TraceError("dispatch or setup worker rows are missing")
        setup_ids = [row.get("worker_id") for row in setup_rows if isinstance(row, dict)]
        dispatch_ids = [row.get("worker_id") for row in assignments if isinstance(row, dict)]
        if setup_ids != expected or dispatch_ids != expected:
            raise TraceError("setup and dispatch rows must contain every worker exactly once in manifest order")
        setup_by_id = {row["worker_id"]: row for row in setup_rows}
        dispatch_by_id: dict[str, dict[str, Any]] = {}
        for row in assignments:
            worker_id = row["worker_id"]
            assignment_path = _inside_run(run, row.get("assignment_path"), "dispatch assignment path")
            source_path = _inside_run(run, row.get("source_assignment_path"), "source assignment path")
            if _file_sha(assignment_path) != row.get("sha256"):
                raise TraceError(f"worker {worker_id} dispatch assignment hash changed")
            if _file_sha(source_path) != row.get("source_assignment_sha256"):
                raise TraceError(f"worker {worker_id} source assignment hash changed")
            assignment = _read_json(assignment_path)
            source = _read_json(source_path)
            args = assignment.get("agent_arguments")
            if assignment.get("schema") != ASSIGNMENT_SCHEMA or assignment.get("worker_id") != worker_id:
                raise TraceError(f"worker {worker_id} assignment schema or identity is invalid")
            if not isinstance(args, dict) or set(args) != {
                "description", "subagent_type", "run_in_background", "prompt",
            }:
                raise TraceError(f"worker {worker_id} does not have the exact Agent argument shape")
            worker = setup_by_id[worker_id]
            worktree_value = worker.get("worktree")
            if not isinstance(worktree_value, str) or not Path(worktree_value).is_absolute():
                raise TraceError(f"worker {worker_id} has no prepared absolute worktree")
            worktree = Path(worktree_value).resolve(strict=False)
            if not worker.get("compact_binding_path") or not worker.get("compact_binding_sha256"):
                raise TraceError(f"worker {worker_id} prepared compact binding is missing")
            binding_path = _inside_run(run, worker.get("compact_binding_path"), "compact binding path")
            source_args = source.get("native_arguments")
            if not isinstance(source_args, dict):
                raise TraceError(f"worker {worker_id} source assignment lacks native arguments")
            source_prompt = source_args.get("prompt")
            if not isinstance(source_prompt, str) or not source_prompt:
                raise TraceError(f"worker {worker_id} source assignment has no common compact prompt")
            source_prompt_sha = _sha256(source_prompt.encode("utf-8"))
            expected_prompt = worker_prefix(worktree) + "\n\n" + source_prompt
            prompt = args.get("prompt")
            if (assignment.get("source_assignment_path") != row.get("source_assignment_path")
                    or assignment.get("source_assignment_sha256") != row.get("source_assignment_sha256")
                    or assignment.get("source_prompt_sha256") != source_prompt_sha
                    or row.get("source_prompt_sha256") != source_prompt_sha
                    or row.get("prompt_sha256") != _sha256(prompt.encode("utf-8") if isinstance(prompt, str) else b"")
                    or prompt != expected_prompt
                    or args.get("description") != source_args.get("description")
                    or args.get("subagent_type") != "general-purpose"
                    or args.get("run_in_background") is not True
                    or not isinstance(args.get("description"), str) or not args["description"]):
                raise TraceError(f"worker {worker_id} prompt or native Agent arguments do not match the prepared mapping")
            if assignment.get("source_prompt_sha256") not in (None, source_prompt_sha):
                raise TraceError(f"worker {worker_id} source prompt digest conflicts with its assignment")
            dispatch_by_id[worker_id] = {
                "arguments": args,
                "prompt": prompt,
                "prompt_sha256": row["prompt_sha256"],
                "worktree": worktree,
                "owned_path": manifest["task_assignments"][int(worker_id) - 1]["path"],
                "binding_path": binding_path,
                "binding_sha256": worker.get("compact_binding_sha256"),
                "packet_sha256": worker.get("compact_packet_sha256"),
                "receipt": worker.get("receipt"),
                "assignment_path": assignment_path,
                "assignment_sha256": row["sha256"],
            }
        _gate(report, "dispatch_prompt_binding", True,
              "Each native argument object is the exact mapped prompt with the common compact prompt preserved",
              [_ref(index_path), *[_ref(_inside_run(run, row["assignment_path"], "assignment path"))
                                   for row in assignments]])
        return setup_by_id, dispatch_by_id
    except FileNotFoundError as exc:
        _gate(report, "dispatch_prompt_binding", False, f"Dispatch evidence is missing: {exc}",
              [_ref(index_path), _ref(setup_path), _ref(treatment_path)], incomplete=True)
    except (OSError, ValueError, KeyError, TypeError, TraceError) as exc:
        _gate(report, "dispatch_prompt_binding", False, f"Dispatch evidence is invalid: {exc}",
              [_ref(index_path), _ref(setup_path), _ref(treatment_path)])
    return {}, {}


def _hooks(run: Path, session_id: str, expected: list[str], root_source_path: str,
           report: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    directory = run / "operator" / "claude-native" / "hooks"
    try:
        paths = sorted(directory.glob("*.json"))
        if not paths:
            raise FileNotFoundError(directory)
        starts: dict[str, dict[str, Any]] = {}
        stops: dict[str, dict[str, Any]] = {}
        event_counts: Counter[str] = Counter()
        refs = []
        for path in paths:
            wrapper = _read_json(path)
            payload = wrapper.get("payload")
            epoch = _finite(wrapper.get("observed_epoch"))
            raw_input = wrapper.get("raw_input")
            try:
                parsed_raw = json.loads(raw_input, object_pairs_hook=_unique_object)
            except (TypeError, ValueError) as exc:
                raise TraceError(f"hook raw input is malformed: {path}") from exc
            if (wrapper.get("schema") != "ask-agent.claude-hook/v1"
                    or not isinstance(payload, dict) or parsed_raw != payload or epoch is None
                    or wrapper.get("parse_error")):
                raise TraceError(f"hook wrapper is malformed: {path}")
            refs.append(_ref(path))
            if payload.get("session_id") != session_id:
                raise TraceError(f"hook is not bound to the launched root session: {path}")
            name = payload.get("hook_event_name")
            event_counts[str(name)] += 1
            if name not in {"SessionStart", "SubagentStart", "SubagentStop", "SessionEnd"}:
                raise TraceError(f"unexpected native hook event {name!r}: {path}")
            if payload.get("transcript_path") != root_source_path:
                raise TraceError(f"{name} hook transcript_path does not identify the root parent transcript")
            if name not in {"SubagentStart", "SubagentStop"}:
                continue
            agent_id = payload.get("agent_id")
            if not isinstance(agent_id, str) or not agent_id:
                raise TraceError(f"{name} hook lacks agent_id: {path}")
            item = {"epoch": epoch, "payload": payload, "path": path}
            target = starts if name == "SubagentStart" else stops
            if agent_id in target:
                raise TraceError(f"duplicate {name} hook for agent {agent_id}")
            target[agent_id] = item
            if name == "SubagentStart" and payload.get("agent_type") != "general-purpose":
                raise TraceError(f"agent {agent_id} was not a general-purpose subagent")
            if name == "SubagentStop":
                source = payload.get("agent_transcript_path")
                if not isinstance(source, str) or not source:
                    raise TraceError(f"agent {agent_id} stop hook lacks child transcript path")
                if not isinstance(payload.get("last_assistant_message"), str):
                    raise TraceError(f"agent {agent_id} stop hook lacks terminal message evidence")
            if name == "SubagentStop" and payload.get("agent_type") != "general-purpose":
                raise TraceError(f"agent {agent_id} stopped with an unexpected native type")
        if (set(starts) != set(stops) or len(starts) != len(expected)
                or event_counts["SessionStart"] != 1 or event_counts["SessionEnd"] != 1):
            raise TraceError("SubagentStart and SubagentStop IDs are not a unique complete worker set")
        _gate(report, "native_hook_lifecycle", True,
              "Unique SubagentStart and SubagentStop hooks bind every worker to the parent session",
              refs)
        return starts, stops
    except FileNotFoundError as exc:
        _gate(report, "native_hook_lifecycle", False, f"Native hook evidence is missing: {exc}",
              [_ref(directory)], incomplete=True)
    except (OSError, ValueError, TypeError, TraceError) as exc:
        _gate(report, "native_hook_lifecycle", False, f"Native hook evidence is invalid: {exc}",
              [_ref(directory)])
    return {}, {}


def _transcripts(run: Path, session_id: str, expected: list[str], starts: dict[str, dict[str, Any]],
                 stops: dict[str, dict[str, Any]], root_records: list[dict[str, Any]],
                 dispatch: dict[str, dict[str, Any]], report: dict[str, Any]
                 ) -> tuple[dict[str, Path], Path | None, dict[str, dict[str, Any]]]:
    index_path = run / "operator" / "claude-native" / "transcript-index.json"
    capture_path = run / "operator" / "claude-native" / "capture_result.json"
    try:
        index = _read_json(index_path)
        capture = _read_json(capture_path)
        rows = index.get("rows")
        if (index.get("schema") != TRANSCRIPT_SCHEMA or index.get("session_id") != session_id
                or not isinstance(rows, list) or capture.get("schema") != "ask-agent.claude-capture-result/v1"
                or capture.get("status") != "PASS" or capture.get("passed") is not True
                or capture.get("session_id") != session_id
                or capture.get("transcript_index_path") != str(index_path.resolve())
                or capture.get("transcript_index_sha256") != _file_sha(index_path)
                or capture.get("captured_transcripts") != len(expected) + 1):
            raise TraceError("capture or transcript index is not a passing retained evidence record")
        parent_rows = [row for row in rows if isinstance(row, dict) and row.get("kind") == "parent"]
        worker_rows = [row for row in rows if isinstance(row, dict) and row.get("kind") == "worker"]
        if len(parent_rows) != 1 or len(worker_rows) != len(expected) or len(rows) != len(expected) + 1:
            raise TraceError("transcript index must contain exactly one root parent transcript")
        parent = parent_rows[0]
        if (parent.get("session_id") != session_id
                or index.get("parent_source_path") != parent.get("source_path")):
            raise TraceError("retained parent transcript is not bound to launch session")
        parent_source = parent.get("source_path")
        if not isinstance(parent_source, str) or not parent_source:
            raise TraceError("parent transcript index row lacks source path")
        parent_retained = _inside_run(run, parent.get("retained_path"), "parent retained transcript")
        parent_source_path = Path(parent_source)
        if (not parent_source_path.is_absolute()
                or _file_sha(parent_source_path) != parent.get("source_sha256")
                or _file_sha(parent_retained) != parent.get("sha256")
                or parent.get("source_sha256") != parent.get("sha256")):
            raise TraceError("retained parent transcript digest does not match its source digest")
        parent_records = _read_jsonl(parent_retained)
        if any(record.get("sessionId") != session_id or record.get("agentId")
               or record.get("isSidechain") is True for record in parent_records):
            raise TraceError("retained parent transcript contains a foreign or sidechain session record")
        root_calls, _ = _calls_and_results(root_records)
        retained_calls, _ = _calls_and_results(parent_records)
        def native_agents(calls):
            return [(call.get("id"), call.get("input")) for call in calls if call.get("name") == "Agent"]
        if native_agents(root_calls) != native_agents(retained_calls):
            raise TraceError("retained parent transcript Agent calls differ from the raw stream")
        root_agent_calls = [call for call in root_calls if call.get("name") == "Agent"]
        root_lifecycle, _ = filter_local_bash_task_events(root_records)
        started = [record for record in root_lifecycle if record.get("type") == "system"
                   and record.get("subtype") == "task_started"]
        call_by_worker: dict[str, dict[str, Any]] = {}
        task_by_tool: dict[str, str] = {}
        for call in root_agent_calls:
            matches = [worker_id for worker_id in expected
                       if agent_arguments_match(call.get("input"), dispatch[worker_id]["arguments"])]
            if len(matches) != 1 or matches[0] in call_by_worker:
                raise TraceError("root Agent calls do not map uniquely to dispatch rows")
            call_by_worker[matches[0]] = call
        for record in started:
            tool_id, task_id = record.get("tool_use_id"), record.get("task_id")
            if (not isinstance(tool_id, str) or not isinstance(task_id, str)
                    or tool_id in task_by_tool or task_id in task_by_tool.values()):
                raise TraceError("root task_started identity is missing or duplicated")
            task_by_tool[tool_id] = task_id
        by_id: dict[str, dict[str, Any]] = {}
        retained: dict[str, Path] = {}
        for row in worker_rows:
            worker_id = row.get("worker_id")
            if worker_id in by_id:
                raise TraceError(f"duplicate retained transcript row for worker {worker_id}")
            by_id[worker_id] = row
        if set(by_id) != set(expected):
            raise TraceError("transcript index worker rows are not a complete unique set")
        for worker_id in expected:
            row = by_id[worker_id]
            agent_id = row.get("agent_id")
            call = call_by_worker.get(worker_id)
            tool_id = call.get("id") if call else None
            if (agent_id not in stops or row.get("task_id") != agent_id or row.get("session_id") != session_id
                    or row.get("tool_use_id") != tool_id or task_by_tool.get(tool_id) != agent_id):
                raise TraceError(f"worker {worker_id} transcript identity is not bound to its native task")
            source = stops[agent_id]["payload"].get("agent_transcript_path")
            if row.get("source_path") != source:
                raise TraceError(f"worker {worker_id} transcript source differs from SubagentStop")
            target = _inside_run(run, row.get("retained_path"), "worker retained transcript")
            digest = _file_sha(target)
            source_path = Path(source)
            if (not source_path.is_absolute() or _file_sha(source_path) != row.get("source_sha256")
                    or digest != row.get("sha256") or row.get("source_sha256") != digest):
                raise TraceError(f"worker {worker_id} retained transcript digest differs from its source")
            hook_refs = row.get("hook_refs")
            expected_hooks = [starts[agent_id], stops[agent_id]]
            if (not isinstance(hook_refs, list) or len(hook_refs) != 2
                    or any(hook_refs[index].get("path") != str(expected_hooks[index]["path"].resolve())
                           or hook_refs[index].get("sha256") != _file_sha(expected_hooks[index]["path"])
                           for index in range(2))):
                raise TraceError(f"worker {worker_id} transcript index hook references are not exact")
            retained[worker_id] = target
            by_id[worker_id]["_agent_id"] = agent_id
            by_id[worker_id]["_tool_use_id"] = tool_id
        _gate(report, "retained_transcripts", True,
              "Parent and child transcripts are retained, hashed, and bound to Claude hook identities",
              [_ref(index_path), _ref(capture_path), _ref(parent_retained),
               *[_ref(retained[worker_id]) for worker_id in expected]])
        return retained, parent_retained, by_id
    except FileNotFoundError as exc:
        _gate(report, "retained_transcripts", False, f"Transcript capture evidence is missing: {exc}",
              [_ref(index_path), _ref(capture_path)], incomplete=True)
    except (OSError, ValueError, KeyError, TypeError, TraceError) as exc:
        _gate(report, "retained_transcripts", False, f"Transcript capture evidence is invalid: {exc}",
              [_ref(index_path), _ref(capture_path)])
    return {}, None, {}


def _phase_records(run: Path, worker_id: str, worker: dict[str, Any], setup: dict[str, Any],
                   child_records: list[dict[str, Any]], report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    owned_path = worker["owned_path"]
    binding_path = worker["binding_path"]
    try:
        binding = _read_json(binding_path)
        canonical = _sha256(json.dumps(
            {key: value for key, value in binding.items() if key != "binding_sha256"},
            sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        ).encode("utf-8"))
        if (binding.get("binding_sha256") != canonical or worker.get("binding_sha256") != canonical
                or _file_sha(binding_path) != worker.get("packet_sha256")):
            raise TraceError(f"worker {worker_id} compact binding digest is invalid")
        child_calls, child_results = _calls_and_results(child_records)
        bash_calls = [call for call in child_calls if call.get("name") == "Bash"]
        phase_calls: dict[str, list[dict[str, Any]]] = {"start": [], "finish": []}
        parsed_commands: dict[str, list[str]] = {}
        for call in bash_calls:
            command = call["input"].get("command")
            if not isinstance(command, str):
                raise TraceError(f"worker {worker_id} has a Bash call without a command string")
            tokens, root_ok = _tokens_after_cd(command, worker["worktree"])
            if not root_ok:
                raise TraceError(f"worker {worker_id} Bash command lacks the assigned worktree cd prefix")
            if not _tool_result_ok(call, child_results):
                raise TraceError(f"worker {worker_id} Bash tool result is missing, failed, or truncated")
            if _is_external_model_command(tokens):
                raise TraceError(f"worker {worker_id} invoked an external model command")
            parsed_commands[str(call.get("id"))] = tokens
            if "worker_phase.py" in " ".join(tokens):
                phases = _tool_flag(tokens, "--phase")
                if len(phases) != 1 or phases[0] not in phase_calls:
                    raise TraceError(f"worker {worker_id} has malformed worker phase command")
                phase = phases[0]
                phase_calls[phase].append(call)
                expected = {
                    "--run": str(run),
                    "--worker": worker_id,
                    "--phase": phase,
                    "--compact-binding": str(binding_path),
                    "--expected-binding-sha256": canonical,
                }
                for flag, value in expected.items():
                    values = _tool_flag(tokens, flag)
                    if len(values) != 1 or values[0] != value:
                        if flag == "--run" and len(values) == 1:
                            if (worker["worktree"] / values[0]).resolve(strict=False) == run:
                                continue
                        raise TraceError(f"worker {worker_id} {phase} wrapper does not use exact {flag} value")
                script_paths = [Path(token) for token in tokens if "worker_phase.py" in token]
                if (len(script_paths) != 1
                        or (worker["worktree"] / script_paths[0]).resolve(strict=False)
                        != (run / "operator" / "worker_phase.py").resolve(strict=False)):
                    raise TraceError(f"worker {worker_id} {phase} wrapper does not invoke the retained helper")
        if any(len(phase_calls[phase]) != 1 for phase in ("start", "finish")):
            raise TraceError(f"worker {worker_id} must invoke exactly one start and one finish wrapper")
        phases = {}
        for phase in ("start", "finish"):
            path = run / "operator" / "worker-phases" / f"worker-{worker_id}-{phase}" / "attempt.json"
            record = _read_json(path)
            checks = record.get("checks")
            expected_status = "WORKER_CONTEXT_READY" if phase == "start" else "READY_FOR_PARENT_ACCEPTANCE"
            production = record.get("compact_worker_result")
            workspace_evidence = (production.get("workspace_evidence", {})
                                  if isinstance(production, dict) else {})
            inspection = workspace_evidence.get("inspection", {}) if isinstance(workspace_evidence, dict) else {}
            inspection = inspection if isinstance(inspection, dict) else {}
            delivery_mode = setup.get("delivery_mode", "patch")
            if phase == "finish" and delivery_mode == "ephemeral":
                audit = workspace_evidence.get("ephemeral_audit") if isinstance(workspace_evidence, dict) else None
                ephemeral_ok = (
                    isinstance(audit, dict) and workspace_evidence == {"ephemeral_audit": audit}
                    and audit.get("status") == "ephemeral-audit" and audit.get("findings_only") is True
                    and audit.get("scratch_retained") is True
                    and audit.get("actual_cwd") == str(worker["worktree"])
                    and set(audit.get("changed_paths", [])) == {owned_path, ".experiment-local/owner.txt"}
                    and len(audit.get("changed_paths", [])) == 2
                )
            else:
                ephemeral_ok = True
            if (record.get("schema") != "ask-agent.worker-phase/v1"
                    or record.get("status") != "PASSED"
                    or record.get("run_id") != setup.get("run_id")
                    or record.get("worker_id") != worker_id or record.get("phase") != phase
                    or record.get("root") != str(worker["worktree"])
                    or record.get("compact_binding_path") != str(binding_path)
                    or record.get("compact_binding_sha256") != canonical
                    or not isinstance(checks, dict) or not checks or checks.get("phase_passed") is not True
                    or any(value is not True for value in checks.values())
                    or not isinstance(production, dict)
                    or production.get("status") != expected_status
                    or production.get("binding_sha256") != canonical
                    or (phase == "start" and inspection.get("worktree") != str(worker["worktree"]))
                    or (phase == "finish" and delivery_mode != "ephemeral"
                        and inspection.get("contribution_paths") != [owned_path])
                    or not ephemeral_ok):
                raise TraceError(f"worker {worker_id} {phase} production evidence is not a successful exact binding")
            call = phase_calls[phase][0]
            native_result = _tool_result_json(call, child_results)
            output_fields = ("status", "run_id", "worker_id", "phase", "root", "branch", "receipt",
                             "baseline", "package_tree_sha256", "checks", "patch_path", "patch_sha256",
                             "commit_base", "contribution_commits", "ephemeral_audit", "action_packet",
                             "compact_binding_sha256", "compact_packet_sha256", "evidence")
            expected_result = {key: record.get(key) for key in output_fields}
            expected_result["evidence"] = str(path.resolve())
            if native_result != expected_result:
                raise TraceError(f"worker {worker_id} {phase} native result differs from its retained attempt")
            attempt_calls = record.get("calls")
            if not isinstance(attempt_calls, list):
                raise TraceError(f"worker {worker_id} {phase} attempt lacks production command records")
            label = f"compact-worker-{phase}"
            matching_calls = [item for item in attempt_calls if isinstance(item, dict) and item.get("label") == label]
            if len(matching_calls) != 1:
                raise TraceError(f"worker {worker_id} {phase} lacks one production wrapper command record")
            command_path = _inside_run(run, matching_calls[0].get("evidence"), "phase command evidence")
            command = _read_json(command_path)
            production_result = record.get("compact_worker_result")
            argv = command.get("argv")
            expected_verb = "worker-start" if phase == "start" else "worker-finish"
            if (command.get("schema") != "ask-agent.worker-phase-command/v1"
                    or command.get("label") != label or command.get("status") != "COMPLETED"
                    or command.get("exit_code") != 0 or type(command.get("exit_code")) is not int
                    or command.get("cwd") != str(worker["worktree"])
                    or not isinstance(argv, list) or len(argv) != 8
                    or argv[1] != "-B" or Path(str(argv[2])).resolve(strict=False)
                    != Path(str(binding.get("package", {}).get("task_script", ""))).resolve(strict=False)
                    or argv[3] != expected_verb or argv[4:6] != ["--binding", str(binding_path)]
                    or argv[6:8] != ["--expected-binding-sha256", canonical]
                    or command.get("json") != production_result
                    or production_result != record.get("compact_worker_result")
                    or matching_calls[0].get("status") != "COMPLETED"
                    or matching_calls[0].get("exit_code") != 0
                    or matching_calls[0].get("evidence") != str(command_path.resolve())):
                raise TraceError(f"worker {worker_id} {phase} production command record is not a successful exact binding")
            try:
                printed_result = json.loads(command.get("stdout", ""), object_pairs_hook=_unique_object)
            except (ValueError, TypeError) as exc:
                raise TraceError(f"worker {worker_id} {phase} production command output is malformed") from exc
            if printed_result != production_result:
                raise TraceError(f"worker {worker_id} {phase} production stdout differs from its retained result")
            phases[phase] = {"path": path, "sha256": _file_sha(path), "call": call,
                             "line": call.get("line", -1), "record": record}

        start_line = phases["start"]["line"]
        finish_line = phases["finish"]["line"]
        if start_line < 1 or finish_line <= start_line:
            raise TraceError(f"worker {worker_id} start and finish native calls are out of order")
        edits = [call for call in child_calls if call.get("name") in {"Write", "Edit"}]
        task_checks = []
        commit_calls = []
        start_record = phases["start"]["record"]
        packet = start_record.get("action_packet")
        if not isinstance(packet, dict):
            raise TraceError(f"worker {worker_id} start phase lacks the retained action packet")
        task_test = packet.get("task_test")
        if (not isinstance(task_test, dict) or task_test.get("cwd") != str(worker["worktree"])
                or task_test.get("argv") != ["python3", "-B", "checks.py", "--worker", worker_id]):
            raise TraceError(f"worker {worker_id} action packet lacks its exact task test")
        finish_calls = phases["finish"]["record"].get("calls")
        check_refs = [item for item in finish_calls if isinstance(item, dict)
                      and item.get("label") == "worker-check"] if isinstance(finish_calls, list) else []
        if len(check_refs) != 1:
            raise TraceError(f"worker {worker_id} finish attempt lacks one production task-check record")
        check_record = _read_json(_inside_run(run, check_refs[0].get("evidence"), "task check evidence"))
        check_argv = check_record.get("argv")
        if (check_record.get("schema") != "ask-agent.worker-phase-command/v1"
                or check_record.get("label") != "worker-check"
                or check_record.get("status") != "COMPLETED"
                or check_record.get("exit_code") != 0 or type(check_record.get("exit_code")) is not int
                or check_record.get("cwd") != str(worker["worktree"])
                or not isinstance(check_argv, list) or len(check_argv) != 5
                or check_argv[1:] != ["-B", "checks.py", "--worker", worker_id]):
            raise TraceError(f"worker {worker_id} production task-check record is not a successful exact command")
        commit_proof = packet.get("commit_proof")
        if not isinstance(commit_proof, list):
            raise TraceError(f"worker {worker_id} action packet has malformed commit proof")
        expected_commit_proof = []
        if setup.get("delivery_mode") == "commits":
            expected_commit_proof = [
                {"argv": ["git", "-C", str(worker["worktree"]), "add", "--", owned_path],
                 "cwd": str(worker["worktree"])},
                {"argv": ["git", "-C", str(worker["worktree"]), "commit", "-m",
                           f"Ask Agent fixture worker {worker_id}"], "cwd": str(worker["worktree"])},
                {"argv": ["git", "-C", str(worker["worktree"]), "rev-parse", "HEAD"],
                 "cwd": str(worker["worktree"])},
            ]
        if commit_proof != expected_commit_proof:
            raise TraceError(f"worker {worker_id} action packet commit proof does not match delivery mode")
        for call in bash_calls:
            tokens = parsed_commands[str(call.get("id"))]
            without_env = tokens[1:] if tokens and tokens[0] == "PYTHONDONTWRITEBYTECODE=1" else tokens
            if without_env == task_test["argv"]:
                task_checks.append(call)
            if any(without_env == item["argv"] for item in expected_commit_proof):
                commit_calls.append(call)
        if (len(task_checks) != 1 or not start_line < task_checks[0]["line"] < finish_line
                or not edits or any(not start_line < call.get("line", -1) < task_checks[0]["line"]
                                    for call in edits)):
            raise TraceError(f"worker {worker_id} must edit its owned file after start and pass its task check before finish")
        expected_commit_lines = [call["line"] for call in commit_calls]
        if (len(commit_calls) != len(expected_commit_proof)
                or (expected_commit_lines and (expected_commit_lines != sorted(expected_commit_lines)
                                               or not task_checks[0]["line"] < expected_commit_lines[0]
                                               or expected_commit_lines[-1] >= finish_line))):
            raise TraceError(f"worker {worker_id} exact commit proof must follow its task check and precede finish")
        if any(not _tool_result_ok(call, child_results) for call in [*task_checks, *commit_calls]):
            raise TraceError(f"worker {worker_id} task check or commit proof result failed or was truncated")
        return phases
    except FileNotFoundError as exc:
        raise TraceError(f"worker {worker_id} phase or binding evidence is missing: {exc}") from exc


def _validate_child(worker_id: str, worker: dict[str, Any], transcript_path: Path,
                    setup: dict[str, Any], run: Path, session_id: str, agent_id: str,
                    parent_model: str, report: dict[str, Any]) -> dict[str, Any]:
    records = _read_jsonl(transcript_path)
    models = {record.get("message", {}).get("model") for record in records
              if record.get("type") == "assistant" and isinstance(record.get("message"), dict)
              and isinstance(record.get("message", {}).get("model"), str)}
    first = records[0] if records else {}
    first_message = first.get("message") if isinstance(first.get("message"), dict) else {}
    if (not models or len(models) != 1 or not parent_model.startswith("claude-sonnet-")
            or models != {parent_model}):
        raise TraceError(f"worker {worker_id} child transcript has no native model identity")
    if (first.get("type") != "user" or first.get("sessionId") != session_id
            or first.get("agentId") != agent_id or first.get("parentUuid") is not None
            or first.get("isSidechain") is not True
            or first_message.get("content") != worker.get("prompt")):
        raise TraceError(f"worker {worker_id} first native message is not the exact fresh dispatched prompt")
    for record in records:
        if record.get("type") in {"user", "assistant", "attachment"}:
            if record.get("sessionId") != session_id or record.get("agentId") != agent_id:
                raise TraceError(f"worker {worker_id} transcript contains a foreign native session or agent ID")
    event_errors = _event_errors(records)
    if event_errors:
        raise TraceError(f"worker {worker_id} child transcript contains an error: {event_errors[0]}")
    calls, results = _calls_and_results(records)
    nested = [call for call in calls if call.get("name") in {
        "Agent", "Task", "RemoteTrigger", "EnterWorktree", "ExitWorktree",
    }]
    if nested:
        raise TraceError(f"worker {worker_id} started a nested or external child")
    direct_edits = []
    for call in calls:
        name, inputs = call.get("name"), call.get("input", {})
        if name in {"Read", "Write", "Edit"}:
            file_path = inputs.get("file_path", inputs.get("path"))
            if not isinstance(file_path, str) or not Path(file_path).is_absolute():
                raise TraceError(f"worker {worker_id} {name} tool uses a non-absolute path")
            if name in {"Write", "Edit"}:
                expected = (worker["worktree"] / worker["owned_path"]).resolve(strict=False)
                if Path(file_path).resolve(strict=False) != expected:
                    raise TraceError(f"worker {worker_id} {name} tool edits outside its owned file")
                direct_edits.append(file_path)
            if not _tool_result_ok(call, results):
                raise TraceError(f"worker {worker_id} {name} tool result is missing, failed, or truncated")
    phases = _phase_records(run, worker_id, worker, setup, records, report)
    return {
        "worker_id": worker_id,
        "model": sorted(models),
        "native_status": "COMPLETED",
        "worktree": str(worker["worktree"]),
        "owned_path": worker["owned_path"],
        "phase_records": {name: {"path": str(value["path"]), "sha256": value["sha256"]}
                          for name, value in phases.items()},
        "direct_edit_paths": direct_edits,
        "transcript": _ref(transcript_path),
    }


def _parent_flow(run: Path, expected: list[str], dispatch: dict[str, dict[str, Any]],
                 starts: dict[str, dict[str, Any]], stops: dict[str, dict[str, Any]],
                 parent_records: list[dict[str, Any]], parent_result: dict[str, Any],
                 manifest: dict[str, Any], launch: dict[str, Any], process: dict[str, Any],
                 report: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    calls, results = _calls_and_results(parent_records)
    session_id = report["session_id"]
    launches = [call for call in calls if call.get("name") == "Agent"]
    parent_lifecycle, _ = filter_local_bash_task_events(parent_records)
    started = [record for record in parent_lifecycle if record.get("type") == "system"
               and record.get("subtype") == "task_started"]
    notifications = [record for record in parent_lifecycle if record.get("type") == "system"
                     and record.get("subtype") == "task_notification"]
    if len(launches) != len(expected) or len(started) != len(expected):
        raise TraceError("root stream must contain exactly one Agent launch and task_started per worker")
    launch_by_handle: dict[str, dict[str, Any]] = {}
    by_task_id: dict[str, dict[str, Any]] = {}
    used_tool_ids = set()
    for call in launches:
        args = call.get("input", {})
        matches = [worker_id for worker_id in expected
                   if agent_arguments_match(args, dispatch[worker_id]["arguments"])]
        if len(matches) != 1:
            raise TraceError("root Agent arguments differ from the unique generated dispatch assignment")
        worker_id = matches[0]
        tool_id = call.get("id")
        if not isinstance(tool_id, str) or tool_id in used_tool_ids:
            raise TraceError("root Agent tool_use IDs are missing or duplicated")
        used_tool_ids.add(tool_id)
        if not _tool_result_ok(call, results, native_spawn=True):
            raise TraceError(f"worker {worker_id} Agent launch result is missing, failed, or truncated")
        launch_by_handle[tool_id] = {"worker_id": worker_id, "call": call}
    for record in started:
        tool_id = record.get("tool_use_id")
        task_id = record.get("task_id")
        if (not isinstance(task_id, str) or task_id in by_task_id or tool_id not in launch_by_handle
                or not isinstance(record.get("run_id"), str) or not record.get("run_id")
                or record.get("session_id") != session_id
                or record.get("subagent_type") != "general-purpose"
                or record.get("is_backgrounded") is not True
                or record.get("spawn_depth") != 1
                or record.get("task_type") != "local_agent"
                or record.get("prompt") != dispatch[launch_by_handle[tool_id]["worker_id"]]["prompt"]):
            raise TraceError("task_started does not identify one fresh background general-purpose Agent launch")
        worker_id = launch_by_handle[tool_id]["worker_id"]
        by_task_id[task_id] = {"worker_id": worker_id, "tool_use_id": tool_id, "start_record": record}
        if worker_id in [item["worker_id"] for item in by_task_id.values() if item is not by_task_id[task_id]]:
            raise TraceError("multiple native handles map to the same worker")
    if set(item["worker_id"] for item in by_task_id.values()) != set(expected):
        raise TraceError("task_started rows do not cover every worker")
    task_by_tool = {value["tool_use_id"]: task_id for task_id, value in by_task_id.items()}
    for record in parent_records:
        if record.get("parent_tool_use_id") is not None or record.get("agent_id") is not None:
            if (record.get("parent_tool_use_id") not in task_by_tool
                    or record.get("agent_id") != task_by_tool[record["parent_tool_use_id"]]
                    or record.get("session_id") != session_id):
                raise TraceError("forwarded child event does not match a launched native worker")
    if len(notifications) != len(expected):
        raise TraceError("native successful completion notifications are missing or ambiguous")
    note_by_id: dict[str, dict[str, Any]] = {}
    for record in notifications:
        task_id = record.get("task_id")
        if task_id in note_by_id:
            raise TraceError(f"duplicate completion notification for task {task_id}")
        if task_id in by_task_id:
            note_by_id[task_id] = record
    if set(note_by_id) != set(by_task_id):
        raise TraceError("native successful completion notifications are missing or ambiguous")
    for task_id, record in note_by_id.items():
        if (record.get("status") != "completed"
                or record.get("tool_use_id") != by_task_id[task_id]["tool_use_id"]
                or record.get("session_id") != session_id
                or record.get("run_id") != by_task_id[task_id]["start_record"].get("run_id")
                or not isinstance(record.get("summary"), str) or not record["summary"].strip()):
            raise TraceError(f"worker {by_task_id[task_id]['worker_id']} notification is not a successful completion")
    worker_to_handle = {value["worker_id"]: task_id for task_id, value in by_task_id.items()}
    if set(starts) != set(worker_to_handle.values()) or set(stops) != set(worker_to_handle.values()):
        raise TraceError("native hooks do not match root task handles")
    for task_id, value in by_task_id.items():
        worker_id = value["worker_id"]
        if (starts[task_id]["epoch"] >= stops[task_id]["epoch"]
                or stops[task_id]["payload"].get("agent_type") != "general-purpose"):
            raise TraceError(f"worker {worker_id} hook interval or type is invalid")
    parent_started = _finite(launch.get("started_epoch"))
    parent_finished = _finite(process.get("finished_epoch"))
    parent_elapsed = _finite(process.get("elapsed_s"))
    if (parent_started is None or parent_finished is None or parent_elapsed is None
            or parent_finished < parent_started or parent_elapsed < 0
            or any(item["epoch"] < parent_started or item["epoch"] > parent_finished
                   for item in [*starts.values(), *stops.values()])):
        raise TraceError("native hook intervals fall outside the launched parent process")
    parent_start = min(record["epoch"] for record in starts.values())
    parent_finish = max(record["epoch"] for record in stops.values())
    intervals = []
    workers = []
    for worker_id in expected:
        task_id = worker_to_handle[worker_id]
        start, stop = starts[task_id]["epoch"], stops[task_id]["epoch"]
        intervals.append((worker_id, start, stop))
        workers.append({
            "worker_id": worker_id,
            "agent_id": task_id,
            "native_handle": task_id,
            "tool_use_id": by_task_id[task_id]["tool_use_id"],
            "notification_status": note_by_id[task_id]["status"],
            "started_epoch": start,
            "stopped_epoch": stop,
            "elapsed_seconds": round(stop - start, 6),
            "start_hook": _ref(starts[task_id]["path"]),
            "stop_hook": _ref(stops[task_id]["path"]),
        })
    all_overlap = max(0.0, min(stop for _, _, stop in intervals) - max(start for _, start, _ in intervals))
    pair_overlaps = {}
    for index, (worker_a, start_a, stop_a) in enumerate(intervals):
        for worker_b, start_b, stop_b in intervals[index + 1:]:
            pair_overlaps[f"{worker_a}:{worker_b}"] = round(max(0.0, min(stop_a, stop_b) - max(start_a, start_b)), 6)
    timing = {
        "parent_started_epoch": parent_started,
        "parent_finished_epoch": parent_finished,
        "parent_elapsed_seconds": round(parent_elapsed, 6),
        "worker_intervals": [{"worker_id": wid, "start_epoch": start, "stop_epoch": stop,
                              "elapsed_seconds": round(stop - start, 6)}
                             for wid, start, stop in intervals],
        "all_worker_overlap_seconds": round(all_overlap, 6),
        "pair_overlap_seconds": pair_overlaps,
        "overlap_caveat": "Hook-observed wall-clock interval overlap does not establish CPU concurrency or causal speedup.",
    }
    _validate_parent_artifacts(run, expected, worker_to_handle, by_task_id, note_by_id,
                               calls, results, parent_records, parent_result, manifest, report)
    return {worker["worker_id"]: worker for worker in workers}, timing




def _verify_operation_command(tokens: list[str], run: Path, operation: str,
                              expected_arguments: list[str]) -> bool:
    """Bind a parent command to the retained helper and its exact CLI arguments."""
    if tokens and tokens[0] == "PYTHONDONTWRITEBYTECODE=1":
        tokens = tokens[1:]
    script = run / "operator" / ("fixture.py" if operation == "fixture.py" else "operations.py")
    return (len(tokens) >= 3 and tokens[0] in {"python3", sys.executable}
            and tokens[1] == "-B"
            and (operation != "fixture.py" or Path(tokens[2]).is_absolute())
            and Path(tokens[2]).resolve(strict=False) == script.resolve(strict=False)
            and tokens[3:] == expected_arguments)


def _validate_parent_artifacts(run: Path, expected: list[str], worker_to_handle: dict[str, str],
                               by_task_id: dict[str, dict[str, Any]], note_by_id: dict[str, dict[str, Any]],
                               calls: list[dict[str, Any]], results: dict[str, list[dict[str, Any]]],
                               parent_records: list[dict[str, Any]], parent_result: dict[str, Any],
                               manifest: dict[str, Any], report: dict[str, Any]) -> None:
    """Check that native receipts, operation outputs, and final artifacts agree."""
    op = run / "operator"
    run_text = str(run)
    mode = manifest.get("delivery_mode", "patch")
    setup = _read_json(op / "setup-result.json")
    setup_rows = setup.get("workers")
    if not isinstance(setup_rows, list):
        raise TraceError("prepared setup has no worker rows")
    worker_roots = {Path(row["worktree"]).resolve(strict=False) for row in setup_rows
                    if isinstance(row, dict) and isinstance(row.get("worktree"), str)}
    call_positions = {id(call): index for index, call in enumerate(calls)}
    verify_calls: list[tuple[int, str, dict[str, Any], list[str]]] = []
    integration_calls: list[tuple[int, dict[str, Any], list[str]]] = []
    summary_calls: list[tuple[int, dict[str, Any], list[str]]] = []
    writer_calls: list[tuple[int, dict[str, Any], list[str]]] = []
    for call in calls:
        tokens = _parent_command_tokens(call.get("input", {}).get("command", ""))
        if call.get("name") in {"Write", "Edit"}:
            value = call.get("input", {}).get("file_path", call.get("input", {}).get("path"))
            if isinstance(value, str) and Path(value).is_absolute():
                path = Path(value).resolve(strict=False)
                if any(path == root or root in path.parents for root in worker_roots):
                    raise TraceError("parent directly edited a worker worktree")
        if call.get("name") != "Bash":
            continue
        if any(any(token == str(root) or str(root) in token for token in tokens) for root in worker_roots):
            if not any(value in tokens for value in ("verify-return", "integrate-batch", "finish-ephemeral")):
                raise TraceError("parent shell command directly targeted a worker worktree")
        index = call_positions[id(call)]
        if "verify-return" in tokens:
            ids, runs = _tool_flag(tokens, "--worker"), _tool_flag(tokens, "--run")
            if len(ids) == len(runs) == 1 and runs[0] == run_text:
                verify_calls.append((index, ids[0], call, tokens))
        if "integrate-batch" in tokens or "finish-ephemeral" in tokens:
            integration_calls.append((index, call, tokens))
        fixture_script = run / "operator" / "fixture.py"
        if (any(Path(token).is_absolute() and Path(token).name == "fixture.py"
                and Path(token).resolve(strict=False) == fixture_script.resolve(strict=False)
                for token in tokens)
                and "verify" in tokens and "--summary" in tokens):
            summary_calls.append((index, call, tokens))
        if "write-parent-result" in tokens:
            writer_calls.append((index, call, tokens))

    if Counter(worker_id for _, worker_id, _, _ in verify_calls) != Counter({wid: 1 for wid in expected}):
        raise TraceError("parent must run exactly one verify-return for every worker")
    if len(integration_calls) != 1 or len(summary_calls) != 1 or len(writer_calls) != 1:
        raise TraceError("parent must run exactly one integration/finalizer, fixture summary, and final writer")
    if any(call.get("name") in {"Task", "RemoteTrigger", "EnterWorktree", "ExitWorktree"}
           for call in calls):
        raise TraceError("parent invoked a nested, external, or worktree-management tool")
    launch_calls = [call for call in calls if call.get("name") == "Agent"]
    first_verify = min(index for index, _, _, _ in verify_calls)
    if not launch_calls or max(call_positions[id(call)] for call in launch_calls) >= first_verify:
        raise TraceError("parent must launch every native worker before collecting any result")
    native_task_ids = set(by_task_id)
    notice_lines = [line for line, record in enumerate(parent_records, 1)
                    if record.get("type") == "system" and record.get("subtype") == "task_notification"
                    and record.get("task_id") in native_task_ids]
    if len(notice_lines) != len(expected):
        raise TraceError("native successful completion notification evidence is incomplete")
    first_verify_line = calls[first_verify].get("line", 10**9)
    if max(notice_lines) >= first_verify_line:
        raise TraceError("parent began verify-return before receiving every native completion notification")

    for _, worker_id, call, tokens in verify_calls:
        if not _tool_result_ok(call, results):
            raise TraceError(f"worker {worker_id} verify-return native result failed or was truncated")
        if not _verify_operation_command(tokens, run, "operations.py",
                                         ["verify-return", "--run", run_text, "--worker", worker_id]):
            raise TraceError(f"worker {worker_id} verify-return command is not the exact retained operation")
        output = _tool_result_json(call, results)
        binding_path = op / "compact-bindings" / f"worker-{worker_id}.json"
        binding = _read_json(binding_path)
        binding_sha = _sha256(json.dumps({key: value for key, value in binding.items()
                                          if key != "binding_sha256"}, sort_keys=True,
                                         separators=(",", ":"), ensure_ascii=True).encode("utf-8"))
        return_path = op / "compact-returns" / f"worker-{worker_id}.json"
        returned = _read_json(return_path)
        owned = manifest["task_assignments"][int(worker_id) - 1]["path"]
        if (returned.get("status") != "PASSED" or returned.get("worker_id") != worker_id
                or returned.get("binding_sha256") != binding_sha or returned.get("delivery_mode") != mode
                or returned.get("exit_code") != 0 or type(returned.get("exit_code")) is not int
                or returned.get("phase") != "verify-return"
                or returned.get("evidence_path") != str(return_path.resolve())
                or returned.get("result", {}).get("status") != "READY_FOR_PARENT_ACCEPTANCE"):
            raise TraceError(f"worker {worker_id} retained verify-return is not a successful bound record")
        expected_output = {"status": "PASSED", "worker_id": worker_id,
                           "binding_sha256": binding_sha, "delivery_mode": mode,
                           "evidence_path": str(return_path.resolve()), "contribution_paths": [owned]}
        if any(output.get(key) != value for key, value in expected_output.items()):
            raise TraceError(f"worker {worker_id} native verify-return output differs from retained evidence")

    integration_index, integration_call, integration_tokens = integration_calls[0]
    summary_index, summary_call, summary_tokens = summary_calls[0]
    writer_index, writer_call, writer_tokens = writer_calls[0]
    if not (max(index for index, _, _, _ in verify_calls) < integration_index < summary_index < writer_index):
        raise TraceError("parent return, integration, summary, and final-writer calls are out of order")
    if not all(_tool_result_ok(call, results) for call in (integration_call, summary_call, writer_call)):
        raise TraceError("parent integration, summary, or final-writer native result failed or was truncated")
    if writer_index != len(calls) - 1 or summary_index + 1 != writer_index:
        raise TraceError("parent made a tool call after the final writer or between summary and writer")

    collected = _tool_flag(integration_tokens, "--collected-worker")
    if collected != expected:
        raise TraceError("parent integration/finalizer did not include every worker in manifest order")
    if mode in {"patch", "commits"}:
        expected_op = ["integrate-batch", "--run", run_text, "--delivery-mode", mode,
                       *[part for wid in expected for part in ("--collected-worker", wid)]]
        if not _verify_operation_command(integration_tokens, run, "operations.py", expected_op):
            raise TraceError("parent integration command does not match the exact delivery mode and worker set")
    elif mode == "ephemeral":
        expected_op = ["finish-ephemeral", "--run", run_text,
                       *[part for wid in expected for part in ("--collected-worker", wid)]]
        if not _verify_operation_command(integration_tokens, run, "operations.py", expected_op):
            raise TraceError("parent ephemeral finalizer does not match the exact worker set")
    else:
        raise TraceError(f"unsupported parent delivery mode {mode!r}")

    integration_path = op / "integration-result.json"
    integration = _read_json(integration_path)
    integration_hash = _file_sha(integration_path)
    integration_output = _tool_result_json(integration_call, results)
    if mode == "ephemeral":
        integration_valid = (integration.get("status") == "NO_INTEGRATION"
                             and integration.get("run_id") == manifest.get("run_id")
                             and integration.get("caller_unchanged") is True
                             and integration_output.get("caller_snapshot_sha256"))
        expected_output = {"status": "NO_INTEGRATION", "delivery_mode": "ephemeral",
                           "worker_ids": expected, "result_path": str(integration_path.resolve()),
                           "result_sha256": integration_hash}
    else:
        integration_valid = (integration.get("status") == "INTEGRATED"
                             and integration.get("run_id") == manifest.get("run_id")
                             and integration.get("delivery_mode") == mode
                             and integration.get("applied_worker_ids") == expected
                             and integration.get("fixture_verification", {}).get("passed") is True)
        expected_output = {"status": "INTEGRATED", "delivery_mode": mode,
                           "applied_worker_ids": expected,
                           "result_path": str(integration_path.resolve()), "result_sha256": integration_hash}
    if not integration_valid or any(integration_output.get(key) != value
                                    for key, value in expected_output.items()):
        raise TraceError("native integration/finalizer result differs from its retained successful record")

    verification_path = op / "verification.json"
    archive_path = op / "parent-verification.json"
    verification_hash = _file_sha(archive_path)
    summary_output = _tool_result_json(summary_call, results)
    expected_summary_command = ["verify", "--run", run_text, "--summary"]
    if (not _verify_operation_command(summary_tokens, run, "fixture.py", expected_summary_command)
            or summary_output.get("schema") != "ask-agent-fixture-verification-summary/v1"
            or summary_output.get("run_id") != manifest.get("run_id")
            or summary_output.get("passed") is not True or summary_output.get("errors") != []
            or type(summary_output.get("check_count")) is not int or summary_output["check_count"] < 1
            or summary_output.get("failed_checks") != []
            or summary_output.get("report_path") != str(verification_path.resolve())
            or summary_output.get("report_bytes") != archive_path.stat().st_size
            or summary_output.get("report_sha256") != verification_hash):
        raise TraceError("parent fixture summary does not prove the archived pre-exit report")

    writer_handles = []
    for value in _tool_flag(writer_tokens, "--worker-handle"):
        if "=" not in value:
            raise TraceError("final writer has a malformed worker handle")
        writer_handles.append(value.split("=", 1))
    if (len(writer_handles) != len(expected)
            or {wid: handle for wid, handle in writer_handles} != worker_to_handle):
        raise TraceError("final writer handles do not match actual native task IDs")
    writer_tail = writer_tokens[6:] if len(writer_tokens) >= 6 else []
    expected_writer_tail = [part for wid in expected
                            for part in ("--worker-handle", f"{wid}={worker_to_handle[wid]}")]
    if (not _verify_operation_command(writer_tokens[:6], run, "operations.py",
                                      ["write-parent-result", "--run", run_text])
            or _tool_flag(writer_tokens, "--verification-sha256") != [verification_hash]
            or _tool_flag(writer_tokens, "--integration-sha256") != [integration_hash]
            or Counter(writer_tail) != Counter([*expected_writer_tail,
                                                "--verification-sha256", verification_hash,
                                                "--integration-sha256", integration_hash])):
        raise TraceError("final writer command is not bound to actual handles and retained hashes")
    parent_path = op / "parent-result.json"
    writer_output = _tool_result_json(writer_call, results)
    if (writer_output.get("status") != "PARENT_ASSERTED"
            or writer_output.get("run_id") != manifest.get("run_id")
            or writer_output.get("result_path") != str(parent_path.resolve())
            or writer_output.get("result_sha256") != _file_sha(parent_path)
            or writer_output.get("worker_ids") != expected):
        raise TraceError("native final-writer result differs from persisted parent result")
    writer_results = results.get(str(writer_call.get("id")), [])
    final_rows = [(line, record) for line, record in enumerate(parent_records, 1)
                  if record.get("type") == "result"]
    if len(writer_results) != 1 or not final_rows:
        raise TraceError("parent final native result or writer tool result is missing")
    final_line, final_record = final_rows[-1]
    final_text = final_record.get("result")
    if (final_line <= writer_results[0].get("line", 10**9)
            or final_record.get("subtype") != "success" or final_record.get("is_error") is not False
            or final_record.get("stop_reason") != "end_turn"
            or final_record.get("terminal_reason") != "completed"
            or not isinstance(final_text, str) or not final_text.strip()
            or _event_errors([final_record])):
        raise TraceError("parent final native result is not a successful completed turn after the writer")
    if parent_result.get("schema") != "ask-agent.parent-result-index/v1":
        raise TraceError("parent result index has an unsupported schema")
    rows = parent_result.get("workers")
    if not isinstance(rows, list) or [row.get("worker_id") for row in rows if isinstance(row, dict)] != expected:
        raise TraceError("parent result worker rows are not in exact manifest order")
    for row in rows:
        wid = row["worker_id"]
        task_id = worker_to_handle[wid]
        binding_path = op / "compact-bindings" / f"worker-{wid}.json"
        binding = _read_json(binding_path)
        binding_sha = _sha256(json.dumps({key: value for key, value in binding.items()
                                          if key != "binding_sha256"}, sort_keys=True,
                                         separators=(",", ":"), ensure_ascii=True).encode("utf-8"))
        if (row.get("native_handle") != task_id or row.get("native_lifecycle") != "parent_asserted"
                or row.get("status") != "PARENT_ASSERTED" or row.get("binding_sha256") != binding_sha
                or row.get("packet_sha256") != _file_sha(binding_path)):
            raise TraceError(f"parent result identity or binding for worker {wid} is invalid")
        refs = row.get("records")
        if not isinstance(refs, dict):
            raise TraceError(f"parent result lacks record refs for worker {wid}")
        for name, relative in (("start", Path("worker-phases") / f"worker-{wid}-start" / "attempt.json"),
                               ("finish", Path("worker-phases") / f"worker-{wid}-finish" / "attempt.json"),
                               ("verify_return", Path("compact-returns") / f"worker-{wid}.json")):
            evidence_path = op / relative
            ref = refs.get(name)
            if (not isinstance(ref, dict) or ref.get("path") != str(evidence_path.resolve())
                    or ref.get("sha256") != _file_sha(evidence_path)):
                raise TraceError(f"parent result {name} reference for worker {wid} is invalid")
    verification_record = parent_result.get("verification")
    integration_record = parent_result.get("integration")
    if (not isinstance(verification_record, dict) or not isinstance(integration_record, dict)
            or verification_record.get("source_path") != str(verification_path.resolve())
            or verification_record.get("source_sha256") != verification_hash
            or verification_record.get("archive_path") != str(archive_path.resolve())
            or verification_record.get("archive_sha256") != verification_hash
            or integration_record.get("sha256") != integration_hash
            or integration_record.get("path") != str(integration_path.resolve())
            or parent_result.get("run_id") != manifest.get("run_id")):
        raise TraceError("parent result hashes differ from exact archived verification/integration bytes")
    _gate(report, "parent_collection_return_integration", True,
          "Native completions, successful returns, delivery, summary, and parent result are correlated",
          [_ref(parent_path), _ref(archive_path), _ref(integration_path)])


def audit_run(run_path: str | Path) -> dict[str, Any]:
    run = Path(run_path).expanduser().resolve(strict=False)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "run_id": None,
        "status": "INCOMPLETE",
        "passed": False,
        "session_id": None,
        "checks": {},
        "errors": [],
        "timing": {},
        "workers": [],
        "evidence": {},
    }
    try:
        manifest = _read_json(run / "manifest.json")
        report["run_id"] = manifest.get("run_id")
        expected, manifest_tasks = _manifest_workers(manifest)
        report["worker_ids"] = expected
        operator = run / "operator"
        launch_path = operator / "launch.json"
        process_path = operator / "process-result.json"
        stdout_path = operator / "stdout.jsonl"
        observed_path = operator / "observed.jsonl"
        stderr_path = operator / "stderr.log"
        dispatch_path = operator / "claude-dispatch" / "index.json"
        root_records = _read_jsonl(stdout_path)
        observed = _read_jsonl(observed_path)
        launch = _read_json(launch_path)
        process = _read_json(process_path)
        parent_result = _read_json(operator / "parent-result.json")
        if not stderr_path.is_file() or stderr_path.is_symlink():
            raise FileNotFoundError(stderr_path)
        stderr = stderr_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        _gate(report, "evidence_available", False, f"Required run evidence is missing: {exc}", incomplete=True)
        report["status"] = "INCOMPLETE"
        return report
    except (OSError, ValueError, TypeError, TraceError) as exc:
        _gate(report, "evidence_available", False, f"Required run evidence is malformed: {exc}")
        report["status"] = "FAIL"
        return report

    _gate(report, "manifest", True, "Manifest identifies the exact ordered three or five worker assignments",
          [_ref(run / "manifest.json")])
    session_id = launch.get("session_id")
    report["session_id"] = session_id
    root_cwd = launch.get("cwd")
    init_records = [record for record in root_records if record.get("type") == "system"
                    and record.get("subtype") == "init"]
    served_models = {record.get("message", {}).get("model") for record in root_records
                     if record.get("type") == "assistant" and isinstance(record.get("message"), dict)
                     and isinstance(record.get("message", {}).get("model"), str)}
    init_sessions = {record.get("session_id") for record in init_records}
    init_cwds = {record.get("cwd") for record in init_records}
    argv = launch.get("argv")
    argv_tokens = [str(value) for value in argv] if isinstance(argv, list) else []
    lowered = {token.lower() for token in argv_tokens}
    identity_ok = (
        isinstance(session_id, str) and bool(session_id)
        and isinstance(root_cwd, str) and Path(root_cwd).is_absolute()
        and len(init_records) >= 1 and init_sessions == {session_id}
        and init_cwds == {root_cwd} and len(served_models) == 1
        and all(isinstance(model, str) and model.startswith("claude-sonnet-") for model in served_models)
        and launch.get("model") == "sonnet"
        and not (lowered & FORBIDDEN_RESUME_FLAGS)
        and "--session-id" in argv_tokens
        and argv_tokens.index("--session-id") + 1 < len(argv_tokens)
        and argv_tokens[argv_tokens.index("--session-id") + 1] == session_id
        and all(record.get("session_id") == session_id for record in root_records)
        and process.get("exit_code") == 0 and type(process.get("exit_code")) is int
    )
    report["requested_model"] = launch.get("model")
    report["served_model"] = next(iter(served_models)) if len(served_models) == 1 else None
    event_errors = _event_errors(root_records)
    if event_errors or ERROR_TEXT.search(stderr):
        identity_ok = False
    _gate(report, "parent_session_and_process", identity_ok,
          "Root Claude session, fresh CLI identity, model, and parent process are successful"
          if identity_ok else "Root session, CLI launch, process, model, or permission/error evidence is invalid",
          [_ref(launch_path), _ref(process_path), _ref(stdout_path), _ref(stderr_path)])
    if not identity_ok:
        report["errors"].extend(event_errors)
    if isinstance(observed, list) and len(observed) == len(root_records):
        times = [_finite(item.get("observed_epoch")) for item in observed]
        events_match = all(isinstance(item, dict) and item.get("event") == root_records[index]
                           for index, item in enumerate(observed))
        time_ordered = all(value is not None for value in times) and times == sorted(times)
        _gate(report, "raw_observed_stream", events_match and time_ordered,
              "Observed wrappers preserve every raw Claude stream event and ordered observation timestamps"
              if events_match and time_ordered else "Raw stream and observed event wrappers differ or are unordered",
              [_ref(stdout_path), _ref(observed_path)])
    else:
        _gate(report, "raw_observed_stream", False, "Observed stream does not contain every raw event",
              [_ref(stdout_path), _ref(observed_path)])

    setup_by_id, dispatch = _dispatch(run, expected, manifest, report)
    if not dispatch:
        report["status"] = "FAIL"
        return report
    dispatch_index_path = operator / "claude-dispatch" / "index.json"
    try:
        transcript_index = _read_json(operator / "claude-native" / "transcript-index.json")
        index_rows = transcript_index.get("rows", [])
        parent_rows = [row for row in index_rows if isinstance(row, dict) and row.get("kind") == "parent"]
        if len(parent_rows) != 1:
            raise TraceError("transcript index must have one parent row")
        parent_source = parent_rows[0].get("source_path")
        starts, stops = _hooks(run, session_id, expected, parent_source, report)
        retained, parent_retained, transcript_rows = _transcripts(
            run, session_id, expected, starts, stops, root_records, dispatch, report,
        )
    except (OSError, ValueError, TypeError, TraceError) as exc:
        _gate(report, "native_hook_lifecycle", False, f"Hook/transcript identity could not be loaded: {exc}",
              incomplete=isinstance(exc, FileNotFoundError))
        starts, stops, retained, parent_retained, transcript_rows = {}, {}, {}, None, {}

    _verify_post_exit(run, manifest, process, report)
    native_workers: dict[str, dict[str, Any]] = {}
    child_errors = []
    for worker_id in expected:
        if worker_id not in retained or worker_id not in dispatch:
            continue
        try:
            native_workers[worker_id] = _validate_child(worker_id, dispatch[worker_id],
                                                        retained[worker_id], manifest, run,
                                                        session_id, transcript_rows[worker_id]["_agent_id"],
                                                        report["served_model"], report)
        except (OSError, ValueError, TypeError, TraceError) as exc:
            child_errors.append(f"worker {worker_id}: {exc}")
    if child_errors:
        _gate(report, "child_worktree_and_phase_evidence", False, "; ".join(child_errors),
              [_ref(retained[worker_id]) for worker_id in retained])
    elif len(native_workers) == len(expected):
        _gate(report, "child_worktree_and_phase_evidence", True,
              "Every child used assigned-root Bash commands, successful tool results, and bound start/finish evidence",
              [_ref(retained[worker_id]) for worker_id in expected])
    else:
        _gate(report, "child_worktree_and_phase_evidence", False,
              "Child transcript evidence is incomplete", incomplete=True)

    root_calls, root_results = _calls_and_results(root_records)
    try:
        for record in root_records:
            if record.get("type") in {"error"} or record.get("subtype") in {
                "api_error", "permission_error", "model_error",
            }:
                raise TraceError("root stream contains a model-shaped or permission error")
        workers_by_id, timing = _parent_flow(run, expected, dispatch, starts, stops, root_records,
                                             parent_result, manifest, launch, process, report)
        report["timing"] = timing
        for worker in native_workers.values():
            worker.update(workers_by_id.get(worker["worker_id"], {}))
        report["workers"] = [native_workers[worker_id] for worker_id in expected if worker_id in native_workers]
        report["evidence"] = {
            "root_stream": _ref(stdout_path),
            "observed_stream": _ref(observed_path),
            "dispatch_index": _ref(dispatch_index_path),
            "parent_transcript": _ref(parent_retained) if parent_retained else None,
            "parent_result": _ref(operator / "parent-result.json"),
        }
    except (OSError, ValueError, KeyError, TypeError, TraceError) as exc:
        _gate(report, "parent_collection_return_integration", False, f"Parent flow is invalid: {exc}",
              [_ref(stdout_path), _ref(operator / "parent-result.json")])
    statuses = [check["status"] for check in report["checks"].values()]
    report["passed"] = bool(statuses) and all(status == "PASS" for status in statuses)
    report["status"] = "PASS" if report["passed"] else (
        "FAIL" if "FAIL" in statuses else "INCOMPLETE"
    )
    return report


def _write_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        view = memoryview(encoded)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="prepared experiment run directory")
    args = parser.parse_args(argv)
    run = Path(args.run).expanduser().resolve(strict=False)
    report = audit_run(run)
    report["auditor_implementation"] = {
        "path": str(Path(__file__).resolve()),
        "sha256": _file_sha(Path(__file__).resolve()),
    }
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    target = run / "operator" / "claude-native-audit.json"
    try:
        _write_exclusive(target, report)
    except FileExistsError:
        print(f"Refusing to replace immutable audit report: {target}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"Could not write audit report {target}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
