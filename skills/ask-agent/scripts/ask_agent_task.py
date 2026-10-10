#!/usr/bin/env python3
"""Prepare bounded Ask Agent work and check its filesystem evidence.

This wrapper never launches or waits for a native worker. The parent retains
the binding and owns dispatch, collection, semantic acceptance, and integration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import signal
import sys
from typing import Any, Mapping, Sequence


sys.dont_write_bytecode = True
_SCRIPT = Path(__file__).resolve(strict=True)
sys.path.insert(0, os.fspath(_SCRIPT.parent))
import ask_agent_workspace as workspace  # noqa: E402


BINDING_SCHEMA = "ask-agent.task.binding.v1"
VERSION = 1
TOOL_OUTPUT_WARNING_BYTES = 20_000
PROTECTED_PARTS = frozenset({".git", ".ask-agent", ".worktrees"})
TASK_INTERFACE = "references/task-interface.md"
NEXT_STEPS = {
    "request": "Correct the request and retry before dispatch.",
    "workspace": "Preserve the source and any helper receipt, then have the parent resolve the workspace condition.",
    "worker": "Use the original binding and run the command from its assigned directory.",
    "acceptance": "Preserve the returned workspace and let the parent review its evidence and choose the next action.",
    "failures": "Preserve any receipt or worktree, inspect the cited evidence, and retry only after resolving the cause.",
}


class TaskError(RuntimeError):
    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__(payload["rationale"])
        self.payload = payload

    def as_json(self) -> dict[str, Any]:
        return {"status": "ERROR", "error": self.payload}


def _reject(
    code: str,
    expected: Any,
    observed: Any,
    rationale: str,
    *,
    anchor: str = "request",
    paths: Sequence[str] = (),
    next_step: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> None:
    error: dict[str, Any] = {
        "code": code,
        "expected": expected,
        "observed": observed,
        "rationale": rationale,
        "reference": f"{TASK_INTERFACE}#{anchor}",
        "evidence_paths": list(dict.fromkeys(os.fspath(path) for path in paths if path)),
        "safe_next_step": next_step or NEXT_STEPS.get(anchor, NEXT_STEPS["failures"]),
    }
    error.update(details or {})
    raise TaskError(error)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _has_control(value: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in value)


def _identity(skill_card: Path) -> dict[str, Any]:
    try:
        return {
            **workspace.identity(skill_card=skill_card),
            "task_script": os.fspath(_SCRIPT),
            "task_script_sha256": _hash_file(_SCRIPT),
        }
    except workspace.WorkspaceError:
        raise
    except OSError as exc:
        _reject("package_identity_failed", "a readable Ask Agent package", str(exc),
                "The wrapper cannot identify the package files that produced this task.", paths=[os.fspath(skill_card)])


def _path_patterns(value: Any, *, anchor: str = "request") -> list[str]:
    if not isinstance(value, list):
        _reject("invalid_write_set", "an array of exact relative paths or slash-marked directory prefixes", type(value).__name__,
                "The parent needs an explicit path boundary for filesystem review.", anchor=anchor)
    patterns: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item or "\\" in item or _has_control(item) or item.startswith("/"):
            _reject("invalid_write_set", "exact relative POSIX paths or slash-marked directory prefixes", item,
                    "Absolute, empty, or platform-dependent paths are not a portable scope boundary.", anchor=anchor)
        if any(char in item for char in "*?[]"):
            _reject("unsupported_write_pattern", "exact paths or directory prefixes ending in `/`", item,
                    "Glob matching can cross path components and would make scope wider than it appears.", anchor=anchor)
        directory_prefix = item.endswith("/")
        normalized = item[:-1] if directory_prefix else item
        parts = normalized.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            _reject("invalid_write_set", "paths without empty, dot, or parent components", item,
                    "Unnormalized path components make the write boundary ambiguous.", anchor=anchor)
        if any(part in PROTECTED_PARTS for part in parts):
            _reject("protected_write_set", "paths that cannot select Git or Ask Agent runtime paths", item,
                    "The path selects a protected repository or workspace location.", anchor=anchor)
        patterns.add(PurePosixPath(normalized).as_posix() + ("/" if directory_prefix else ""))
    return sorted(patterns)


def _text(value: Any, key: str, *, required: bool = False) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str) or (required and not value.strip()):
        _reject("invalid_request", f"{'a non-empty' if required else 'a'} string for `{key}`", value,
                "Task context is forwarded as plain text and cannot be safely coerced.")
    return value.strip()


def _request(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        _reject("invalid_request", "a JSON object", type(raw).__name__, "The wrapper accepts one explicit task packet.")
    unsupported = sorted(set(raw) & {"consumer_owned", "consumer_workspace", "commits"})
    if unsupported:
        _reject("unsupported_case", "current or helper-managed patch/commit/report-only/findings-only work",
                {key: raw[key] for key in unsupported},
                "Consumer-owned workspaces and parent-supplied commit lists use their existing contracts; no fallback is selected.",
                anchor="workspace")
    allowed = {"objective", "expected_result", "source", "workspace", "mode", "write_set",
               "delivery_mode", "current_learnings", "authorization", "writers_quiescent",
               "exclusive_writer", "store"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        _reject("unknown_request_field", sorted(allowed), unknown,
                "Unknown fields could silently change task or delivery semantics.")
    objective = _text(raw.get("objective"), "objective", required=True)
    expected_result = _text(raw.get("expected_result"), "expected_result", required=True)
    source_value = raw.get("source")
    if not isinstance(source_value, str) or not Path(source_value).is_absolute():
        _reject("invalid_source", "an explicit absolute source directory", source_value,
                "Preparation must bind one concrete checkout rather than depend on the host cwd.")
    if _has_control(source_value):
        _reject("invalid_source", "an absolute source path without control characters", source_value,
                "Control characters cannot be resolved safely as filesystem paths.")
    try:
        source = Path(source_value).resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        _reject("invalid_source", "an existing absolute source directory", f"{source_value}: {exc}",
                "The selected source cannot be prepared or inspected.")
    if not source.is_dir():
        _reject("invalid_source", "an existing absolute source directory", source_value,
                "The source must be a directory.")
    route = raw.get("workspace", "current")
    if not isinstance(route, str):
        _reject("invalid_workspace", "`current` or `worktree`", route,
                "Only the current route and existing helper-managed worktrees are supported.", anchor="workspace")
    if route in {"consumer", "consumer-owned", "in-place"}:
        _reject("unsupported_case", "`current` or `worktree`", route,
                "Consumer-owned workspaces use their existing contract, with no automatic fallback.", anchor="workspace")
    if route not in {"current", "worktree"}:
        _reject("invalid_workspace", "`current` or `worktree`", route,
                "The wrapper supports only these two workspace routes.", anchor="workspace")
    mode = raw.get("mode")
    if not isinstance(mode, str):
        _reject("invalid_mode", "edit, report-only, or ephemeral", mode,
                "The task mode controls which filesystem changes are permitted.")
    if mode == "commits":
        _reject("unsupported_case", "edit with delivery_mode commits", mode,
                "Commit delivery is selected as a delivery mode for worktree edits, not as a task mode.",
                anchor="workspace")
    if mode not in {"edit", "report-only", "ephemeral"}:
        _reject("invalid_mode", "edit, report-only, or ephemeral", mode,
                "The task mode controls which filesystem changes are permitted.")
    delivery_present = "delivery_mode" in raw
    delivery_value = raw.get("delivery_mode")
    if delivery_present and not isinstance(delivery_value, str):
        _reject("invalid_delivery_mode", "commits or patch for a worktree edit", delivery_value,
                "Delivery mode must be an explicit string when supplied.")
    if mode == "edit" and route == "worktree":
        delivery_mode = delivery_value if delivery_present else "commits"
        if delivery_mode not in {"commits", "patch"}:
            _reject("invalid_delivery_mode", "commits or patch for a worktree edit", delivery_mode,
                    "Worktree edits need one unambiguous return format.", anchor="workspace")
    else:
        delivery_mode = None
        if delivery_present:
            _reject("ambiguous_delivery_mode", "delivery_mode omitted outside worktree edit mode",
                    delivery_value,
                    "Current edits, report-only work, and ephemeral findings do not return commits or patches.",
                    anchor="workspace")
    write_set = _path_patterns(raw.get("write_set", []))
    if mode in {"edit", "ephemeral"} and not write_set:
        _reject("missing_write_set", "a non-empty write_set for edit and ephemeral modes", write_set,
                "Edits without a declared boundary cannot be checked for scope drift.")
    if mode == "report-only" and write_set:
        _reject("report_only_write_set", "an empty write_set for report-only mode", write_set,
                "Report-only work returns its answer in the native result and does not permit file contributions.")
    if mode == "ephemeral" and route != "worktree":
        _reject("ephemeral_requires_worktree", "workspace worktree for ephemeral mode", route,
                "Ephemeral scratch work must stay in a retained helper-managed worktree.", anchor="workspace")
    writers_quiescent = raw.get("writers_quiescent", False)
    exclusive_writer = raw.get("exclusive_writer", False)
    if type(writers_quiescent) is not bool or type(exclusive_writer) is not bool:
        _reject("invalid_attestation", "Boolean writer attestations", {
            "writers_quiescent": writers_quiescent, "exclusive_writer": exclusive_writer,
        }, "Writer claims must be explicit Booleans.", anchor="workspace")
    if route == "worktree" and not writers_quiescent:
        _reject("writers_not_quiescent", "writers_quiescent: true", writers_quiescent,
                "The helper snapshots the source before preparing an isolated worktree.", anchor="workspace")
    if route == "current" and mode == "edit" and not exclusive_writer:
        _reject("exclusive_writer_required", "exclusive_writer: true", exclusive_writer,
                "This parent attestation is not an enforced lock, so concurrent changes cannot be attributed safely.",
                anchor="workspace")
    store_value = raw.get("store")
    if route == "current" and store_value is not None:
        _reject("unsupported_store", "store omitted for current workspace", store_value,
                "Current preparation is read-only and creates no helper-managed state.", anchor="workspace")
    store = None
    if store_value is not None:
        if (route != "worktree" or not isinstance(store_value, str) or _has_control(store_value)
                or not Path(store_value).is_absolute()):
            _reject("invalid_store", "an optional absolute store path for worktree only", store_value,
                    "The helper store must be explicit and cannot be selected on the current route.", anchor="workspace")
        store = os.fspath(Path(store_value))
    return {
        "objective": objective, "expected_result": expected_result, "source": os.fspath(source),
        "route": route, "mode": mode, "delivery_mode": delivery_mode, "write_set": write_set,
        "current_learnings": _text(raw.get("current_learnings"), "current_learnings"),
        "authorization": _text(raw.get("authorization"), "authorization"),
        "writers_quiescent": writers_quiescent, "exclusive_writer": exclusive_writer, "store": store,
    }


def _matches(path: str, write_set: Sequence[str]) -> bool:
    return any(path.startswith(item) if item.endswith("/") else path == item for item in write_set)


def _overlaps_dirty(path: str, write_set: Sequence[str]) -> bool:
    return any(path == item.rstrip("/") or path.startswith(item.rstrip("/") + "/") for item in write_set)


def _digest(binding: Mapping[str, Any]) -> str:
    return hashlib.sha256(_json_bytes({key: value for key, value in binding.items() if key != "binding_sha256"})).hexdigest()


def _make_binding(package: Mapping[str, Any], task: Mapping[str, Any], bound_workspace: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": BINDING_SCHEMA, "version": VERSION, "status": "READY_TO_LAUNCH",
        "package": dict(package), "task": dict(task), "workspace": dict(bound_workspace),
        "binding_note": "Parent coordination data only; digest is not authentication or native execution proof.",
    }
    result["binding_sha256"] = _digest(result)
    return result


def _helper_failure(action: str, exc: workspace.WorkspaceError, *, anchor: str, paths: Sequence[str] = ()) -> TaskError:
    message = str(exc)
    match = re.search(r"failure record: (.+)\)$", message)
    locator = match.group(1).strip() if match else ""
    evidence = [*paths, locator if locator and not locator.startswith("unavailable ") else ""]
    return TaskError({
        "code": "workspace_helper_rejected",
        "expected": f"the existing workspace helper to {action}",
        "observed": message,
        "rationale": "The helper refused this local Git/filesystem operation and its existing evidence is retained.",
        "reference": f"{TASK_INTERFACE}#{anchor}",
        "evidence_paths": list(dict.fromkeys(path for path in evidence if path)),
        "safe_next_step": "Inspect the cited evidence and resolve the stated condition; do not silently prepare a replacement.",
        "workspace_error": message,
    })


def prepare_task(raw_request: Any, skill_card: Path) -> dict[str, Any]:
    request = _request(raw_request)
    try:
        package = _identity(skill_card)
    except workspace.WorkspaceError as exc:
        raise _helper_failure("verify package identity", exc, anchor="request", paths=[os.fspath(skill_card)]) from exc
    task = {key: request[key] for key in (
        "objective", "expected_result", "mode", "delivery_mode", "write_set", "current_learnings", "authorization",
    )}
    source = Path(request["source"])
    if request["route"] == "current":
        try:
            state = workspace.current_state(source=source, write_set=request["write_set"])
        except workspace.WorkspaceError as exc:
            raise _helper_failure("capture a current-state baseline", exc, anchor="workspace", paths=[request["source"]]) from exc
        if request["mode"] == "edit":
            if state["status"] != "ok":
                _reject("current_edit_requires_git", "a Git working tree", state["status"],
                        "Current edits need a comparable Git baseline.", anchor="workspace", paths=[request["source"]])
            dirty = sorted(entry["path"] for entry in state["entries"] if _overlaps_dirty(entry["path"], request["write_set"]))
            if dirty:
                _reject("dirty_write_set_overlap", "no pre-existing dirty paths within write_set", dirty,
                        "Existing changes in the task boundary could be overwritten or misattributed.",
                        anchor="workspace", paths=[request["source"]])
        bound_workspace: dict[str, Any] = {
            "route": "current", "source": request["source"], "root": state.get("root"),
            "launch_cwd": state.get("root") or state["cwd"], "baseline": state,
        }
        limitations = ["Current-route writer exclusivity is a parent attestation, not a lock.",
                       "Filesystem evidence does not prove which native worker made a change."]
        if state["status"] == "not-git":
            bound_workspace["no_drift_warning"] = state["limitation"]
            limitations.append("This non-Git report-only task cannot fingerprint drift; the worker must return its report without file changes.")
    else:
        try:
            prepared = workspace.prepare(
                source=source,
                store=Path(request["store"]) if request["store"] else None,
                writers_quiescent=True,
                commit_snapshot=request["delivery_mode"] == "commits",
            )
        except workspace.WorkspaceError as exc:
            raise _helper_failure("prepare a helper-managed worktree", exc, anchor="workspace",
                                  paths=[request["source"], request["store"] or ""]) from exc
        receipt = prepared["receipt"]
        try:
            inspected = workspace.inspect(receipt=Path(receipt), phase="prepared")
        except workspace.WorkspaceError as exc:
            raise _helper_failure("inspect the prepared worktree", exc, anchor="workspace",
                                  paths=[receipt, prepared.get("worktree", ""), prepared.get("baseline", "")]) from exc
        if inspected.get("phase") != "prepared":
            _reject("prepared_inspection_mismatch", "phase prepared", inspected.get("phase"),
                    "The worker cannot launch until the helper verifies its pre-dispatch baseline.",
                    anchor="workspace", paths=[receipt, prepared["worktree"]])
        bound_workspace = {
            "route": "worktree", "source": prepared["source"], "root": prepared["worktree"],
            "launch_cwd": prepared["worktree"], "receipt": receipt, "baseline": prepared["baseline"],
            "branch": prepared["branch"], "attempt": prepared["attempt"],
            "prepared_fingerprint": inspected["fingerprint"],
            "ignored_dependencies_omitted": prepared["ignored_dependencies_omitted"],
        }
        if request["delivery_mode"] == "commits":
            bound_workspace["commit_base"] = prepared["commit_base"]
            bound_workspace["snapshot"] = prepared["snapshot"]
        limitations = ["The helper receipt preserves the source snapshot and worker workspace; this wrapper does not close or integrate it.",
                       "Filesystem evidence does not prove native task lifecycle or semantic acceptance."]
        if prepared["ignored_dependencies_omitted"]:
            limitations.append("Ignored untracked inputs listed in workspace.ignored_dependencies_omitted are omitted from the helper worktree snapshot.")
    binding = _make_binding(package, task, bound_workspace)
    binding_bytes = len(_json_bytes(binding))
    if binding_bytes > TOOL_OUTPUT_WARNING_BYTES:
        limitations.append(f"Binding is {binding_bytes} bytes; the parent should verify complete tool output and native transfer.")

    def result_packet() -> dict[str, Any]:
        prompt = _worker_prompt(binding, limitations)
        return {
            "status": "READY_TO_LAUNCH", "binding": binding,
            "launch": {"cwd": bound_workspace["launch_cwd"],
                       "mode": "fresh native context; parent selects the host and retains its native handle",
                       "prompt": prompt},
            "payload_sizes": {"binding_bytes": binding_bytes, "prompt_bytes": len(prompt.encode("utf-8"))},
            "parent_next_steps": [
                "Launch a fresh native worker with launch.prompt and launch.cwd; retain its native handle in the parent record.",
                "Collect the native result, run verify-return with the unchanged binding, then decide semantic acceptance and integration in the parent.",
            ],
            "limitations": limitations,
        }

    result = result_packet()
    if len(_json_bytes(result)) > TOOL_OUTPUT_WARNING_BYTES:
        limitations.append("Grok Bash tool output has an observed 20 KB default limit. This is a tool-output limit, not a native prompt limit; the parent must verify the full JSON and prompt transfer. The wrapper never truncates output.")
        result = result_packet()
    size = len(_json_bytes(result))
    for _ in range(3):
        result["payload_sizes"]["stdout_json_bytes"] = size
        actual = len(_json_bytes(result))
        if actual == size:
            break
        size = actual
    return result


def _worker_prompt(binding: Mapping[str, Any], limitations: Sequence[str]) -> str:
    task, bound_workspace = binding["task"], binding["workspace"]
    script = binding["package"]["task_script"]
    root = bound_workspace["launch_cwd"]
    start_command = shlex.join(["python3", script, "worker-start", "--binding", "-"])
    finish_command = shlex.join(["python3", script, "worker-finish", "--binding", "-"])
    if bound_workspace["route"] == "current" and task["mode"] == "edit":
        delegation = "This current-workspace edit has one writer: do not delegate to further agents."
    else:
        delegation = ("Any native delegates must follow this task's workspace, scope and handoff constraints. "
                      "Collect their terminal results before finishing or returning.")
        if task["mode"] == "report-only":
            delegation += " You and your delegates must remain report-only and make no filesystem changes."
    if task["mode"] == "ephemeral":
        delivery_header = "No commit — findings only"
        change_rule = "Use the assigned worktree for scoped scratch edits. Do not commit or create a patch; report findings and changed paths only."
    elif task["mode"] == "report-only":
        delivery_header = "Report-only — return findings without filesystem changes"
        change_rule = "Make no filesystem changes and do not commit."
    elif bound_workspace["route"] == "current":
        delivery_header = "No commit — edit the current workspace in place"
        change_rule = "Do not commit, reset, stash, close, merge, or integrate. Keep edits within the write set."
    elif task["delivery_mode"] == "patch":
        delivery_header = "Patch — return these changes without committing"
        change_rule = "Do not commit, reset, stash, close, merge, or integrate. Keep edits within the write set."
    else:
        delivery_header = "Git commit — return these changes"
        change_rule = (
            "Keep edits within the write set and commit only the task's contribution paths. "
            "Stage every changed in-scope path explicitly with git -C " + shlex.quote(root)
            + " add -- <exact-path>, then commit with git -C " + shlex.quote(root)
            + " commit -m '<message>'. Never use git add . or git add -A; do not commit inherited parent work."
        )
    sections = [
        "You are a fresh native worker. Treat this as standalone task context; do not assume parent conversation history.",
        f"Objective: {task['objective']}\nExpected result: {task['expected_result']}\nMode: {task['mode']}\nWorking directory: {bound_workspace['launch_cwd']}\nWrite set: {json.dumps(task['write_set'])} (exact paths; a trailing slash marks all descendants)",
        "Delivery: " + delivery_header,
        f"Current learnings:\n{task['current_learnings'] or 'None supplied.'}\nAuthority:\n{task['authorization'] or 'No additional authority was supplied; follow the objective and write set.'}",
        "Use the bound directory for every shell command and absolute paths for file tools; follow its project instructions. Honor the parent’s existing authority, model, and tool inheritance contract; do not create a restricted or otherwise different agent.",
        f"Before any task operation, run `{start_command}` from the assigned directory. After the work, run `{finish_command}` there, supplying the exact binding JSON below to both commands.",
        "Preserve inherited changes and unrelated files. Remain in the assigned directory. "
        "Do not reset, stash, close, merge, or integrate; the parent owns acceptance and integration. "
        + change_rule + " If blocked, stop and return the reason with evidence.",
        delegation,
        "Run relevant actual checks for code changes. Return exact commands and observed results, changed paths, evidence locations, limits, and uncertainty. For commits, report the complete ordered contribution commit SHAs. For ephemeral work, return findings only. Script status is filesystem evidence only; it does not prove native completion or semantic correctness.",
        "Known limits:\n" + "\n".join(f"- {item}" for item in limitations),
        "Binding JSON (use this exact object on stdin; do not edit it):\n```json\n" + json.dumps(binding, sort_keys=True, indent=2) + "\n```",
    ]
    return "\n\n".join(sections)


def _read_json(argument: str, label: str) -> Any:
    try:
        content = sys.stdin.read() if argument == "-" else Path(argument).read_text(encoding="utf-8")
        return json.loads(content)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        _reject(f"invalid_{label}", "valid UTF-8 JSON on stdin or in a file", str(exc),
                f"The {label} packet could not be read as JSON.", anchor="request" if label == "request" else "worker")


def _binding(raw: Any) -> dict[str, Any]:
    keys = {"schema", "version", "status", "package", "task", "workspace", "binding_note", "binding_sha256"}
    if not isinstance(raw, dict) or set(raw) != keys:
        _reject("invalid_binding", sorted(keys), sorted(raw) if isinstance(raw, dict) else type(raw).__name__,
                "Use the complete binding returned by prepare without adding native handles or result fields.", anchor="worker")
    if raw.get("schema") != BINDING_SCHEMA or raw.get("version") != VERSION or raw.get("status") != "READY_TO_LAUNCH":
        _reject("invalid_binding", {"schema": BINDING_SCHEMA, "version": VERSION, "status": "READY_TO_LAUNCH"},
                {key: raw.get(key) for key in ("schema", "version", "status")},
                "The packet is not a supported prepared-task binding.", anchor="worker")
    if not isinstance(raw.get("binding_sha256"), str) or raw["binding_sha256"] != _digest(raw):
        _reject("binding_digest_mismatch", "a digest matching the supplied packet", raw.get("binding_sha256"),
                "This self-consistency check detects accidental edits; it is not authentication or execution proof.", anchor="worker")
    package, task, bound_workspace = raw["package"], raw["task"], raw["workspace"]
    if not all(isinstance(item, dict) for item in (package, task, bound_workspace)):
        _reject("invalid_binding", "object values for package, task, and workspace",
                [type(item).__name__ for item in (package, task, bound_workspace)],
                "The packet must retain its package, task, and workspace sections.", anchor="worker")
    card = package.get("skill_card")
    if not isinstance(card, str) or not Path(card).is_absolute():
        _reject("invalid_binding_package", "an absolute selected skill-card path", card,
                "The package identity must be rechecked at every command.", anchor="worker")
    try:
        actual = _identity(Path(card))
    except workspace.WorkspaceError as exc:
        raise _helper_failure("verify the bound package identity", exc, anchor="worker", paths=[card]) from exc
    if package != actual:
        _reject("package_identity_mismatch", actual, package,
                "The current skill card, helper, or wrapper differs from the prepared package.",
                anchor="worker", paths=[card, package.get("resolved_helper", ""), package.get("task_script", "")])
    required_task = {"objective", "expected_result", "mode", "delivery_mode", "write_set",
                     "current_learnings", "authorization"}
    if (set(task) != required_task or not isinstance(task.get("mode"), str)
            or task.get("mode") not in {"edit", "report-only", "ephemeral"}
            or (task.get("delivery_mode") is not None and not isinstance(task.get("delivery_mode"), str))
            or not isinstance(task.get("write_set"), list)):
        _reject("invalid_binding_task", sorted(required_task), task,
                "The bound task lacks supported mode or scope fields.", anchor="worker")
    if any(not isinstance(task.get(key), str) for key in required_task - {"write_set", "delivery_mode"}):
        _reject("invalid_binding_task", "string task fields and an array write_set", task,
                "Worker task metadata must remain plain text and typed scope data.", anchor="worker")
    if (_path_patterns(task["write_set"], anchor="worker") != task["write_set"]
            or (task["mode"] in {"edit", "ephemeral"} and not task["write_set"])
            or (task["mode"] == "report-only" and task["write_set"])):
        _reject("invalid_binding_write_set", "normalized edit/ephemeral scope or empty report-only scope", task["write_set"],
                "The binding's scope must retain the request's supported mode rules.", anchor="worker")
    route = bound_workspace.get("route")
    if not isinstance(route, str) or route not in {"current", "worktree"} or any(
        not isinstance(bound_workspace.get(key), str) or not Path(bound_workspace[key]).is_absolute()
        for key in ("source", "launch_cwd")
    ):
        _reject("invalid_binding_workspace", "a supported route with absolute source and launch_cwd", bound_workspace,
                "Worker checks must resolve to the parent's selected workspace.", anchor="worker")
    if route == "current":
        if task["mode"] == "ephemeral" or task["delivery_mode"] is not None:
            _reject("invalid_binding_delivery_mode", "no delivery_mode for current edit/report-only work",
                    {"mode": task["mode"], "delivery_mode": task["delivery_mode"]},
                    "Current work stays in place and never returns a commit or patch.", anchor="worker")
        baseline = bound_workspace.get("baseline")
        if not isinstance(baseline, dict) or baseline.get("schema") != workspace.CURRENT_STATE_SCHEMA or baseline.get("status") not in {"ok", "not-git"}:
            _reject("invalid_binding_baseline", "an Ask Agent current-state baseline", baseline,
                    "Current-route checks require the complete prepare-time state.", anchor="worker")
        if baseline.get("root") != bound_workspace.get("root"):
            _reject("invalid_binding_baseline", baseline.get("root"), bound_workspace.get("root"),
                    "The current workspace root and baseline disagree.", anchor="worker")
        if baseline["status"] == "not-git" and (task["mode"] != "report-only" or not bound_workspace.get("no_drift_warning")):
            _reject("invalid_binding_baseline", "non-Git report-only with a no-drift warning", baseline,
                    "Non-Git work cannot fingerprint file changes.", anchor="worker")
    else:
        if not all(isinstance(bound_workspace.get(key), str) and Path(bound_workspace[key]).is_absolute() for key in
                   ("root", "receipt", "baseline")) or not all(
                       isinstance(bound_workspace.get(key), str) and bound_workspace[key]
                       for key in ("branch", "attempt", "prepared_fingerprint")):
            _reject("invalid_binding_workspace", "absolute worktree root, receipt, and baseline plus branch, attempt, and fingerprint", bound_workspace,
                    "Worktree checks need the original helper receipt and prepared inspection.", anchor="worker")
        if bound_workspace["root"] != bound_workspace["launch_cwd"]:
            _reject("invalid_binding_workspace", bound_workspace["root"], bound_workspace["launch_cwd"],
                    "The helper-managed worktree root is also its assigned launch directory.", anchor="worker")
        if task["mode"] == "edit" and task["delivery_mode"] not in {"commits", "patch"}:
            _reject("invalid_binding_delivery_mode", "commits or patch for worktree edit",
                    task["delivery_mode"], "Worktree edit bindings need one explicit delivery mode.", anchor="worker")
        if task["mode"] in {"report-only", "ephemeral"} and task["delivery_mode"] is not None:
            _reject("invalid_binding_delivery_mode", "no delivery_mode for report-only or ephemeral work",
                    task["delivery_mode"], "This task mode does not return a patch or commit list.", anchor="worker")
        if task["delivery_mode"] == "commits":
            commit_base = bound_workspace.get("commit_base")
            snapshot = bound_workspace.get("snapshot")
            if (not isinstance(commit_base, str) or not workspace.GIT_SHA_RE.fullmatch(commit_base)
                    or not isinstance(snapshot, dict)
                    or set(snapshot) != {"mode", "commit", "tree", "created", "source_dirty"}
                    or snapshot.get("mode") != "private-commit"
                    or snapshot.get("commit") != commit_base
                    or not isinstance(snapshot.get("tree"), str)
                    or not workspace.GIT_SHA_RE.fullmatch(snapshot["tree"])
                    or type(snapshot.get("created")) is not bool
                    or type(snapshot.get("source_dirty")) is not bool):
                _reject("invalid_binding_commit_snapshot",
                        "commit_base plus private snapshot metadata matching S",
                        {"commit_base": commit_base, "snapshot": snapshot},
                        "Commit delivery requires the helper's verified prepared snapshot metadata.", anchor="worker")
        elif "commit_base" in bound_workspace or "snapshot" in bound_workspace:
            _reject("unexpected_binding_commit_snapshot", "commit snapshot metadata only for commits delivery",
                    {"commit_base": bound_workspace.get("commit_base"), "snapshot": bound_workspace.get("snapshot")},
                    "Patch, report-only, and ephemeral bindings do not use a private commit base.", anchor="worker")
    return raw


def _current(binding: Mapping[str, Any], *, process_cwd: bool) -> dict[str, Any]:
    bound = binding["workspace"]
    source = Path.cwd().resolve(strict=True) if process_cwd else Path(bound["launch_cwd"])
    if process_cwd and source != Path(bound["launch_cwd"]).resolve(strict=True):
        _reject("wrong_worker_cwd", bound["launch_cwd"], os.fspath(source),
                "Worker commands must run from the exact current-workspace directory.", anchor="worker", paths=[bound["source"]])
    try:
        if bound["baseline"]["status"] == "not-git":
            state = workspace.current_state(source=source)
            if state.get("status") != "not-git" or state.get("cwd") != bound["launch_cwd"]:
                _reject("workspace_changed", "the original non-Git report directory", state,
                        "The non-Git route cannot provide a drift fingerprint.", anchor="worker" if process_cwd else "acceptance",
                        paths=[bound["source"]])
            return state
        state = workspace.current_state(
            source=source, expect_root=Path(bound["root"]), baseline=bound["baseline"],
            write_set=binding["task"]["write_set"],
        )
    except workspace.WorkspaceError as exc:
        raise _helper_failure("compare current workspace state", exc,
                              anchor="worker" if process_cwd else "acceptance", paths=[bound["source"]]) from exc
    # current_state reports drift in JSON while returning exit status zero.
    out_of_scope = sorted(path for path in state.get("changed_paths", [])
                          if not _matches(path, binding["task"]["write_set"]))
    if state.get("verdict") == "drift" or out_of_scope:
        _reject("scope_drift", f"changes only within {binding['task']['write_set']} and no HEAD movement",
                {key: state.get(key) for key in ("head_moved", "changed_paths", "outside_write_set")},
                "The wrapper rejects current-state drift and independently checks exact paths or slash-marked directory prefixes.",
                anchor="worker" if process_cwd else "acceptance", paths=[bound["source"]])
    return state


def _ephemeral_audit(
    binding: Mapping[str, Any],
    *,
    context: Mapping[str, Any] | None,
    worker: bool,
) -> dict[str, Any]:
    bound = binding["workspace"]
    paths = [bound["receipt"], bound["root"], bound["baseline"]]
    try:
        record = workspace._load_receipt(Path(bound["receipt"]))
        with workspace._attempt_lock(record["attempt"]):
            _source, worktree = workspace._validate_binding(record)
            if worktree is None or os.fspath(worktree) != bound["root"]:
                _reject("receipt_workspace_mismatch", bound["root"],
                        os.fspath(worktree) if worktree else None,
                        "The helper receipt resolved to a different ephemeral scratch workspace.",
                        anchor="worker" if worker else "acceptance", paths=paths)
            current = workspace._worker_state(worktree)
            baseline = record["baseline_data"]["worker_state"]
            changes = workspace._changes(baseline, current)
    except workspace.WorkspaceError as exc:
        raise _helper_failure("audit ephemeral scratch changes", exc,
                              anchor="worker" if worker else "acceptance", paths=paths) from exc
    changed_git_state = {
        "head": current.get("head") != baseline.get("head"),
        "branch": current.get("branch") != baseline.get("branch"),
    }
    if changed_git_state["head"] or changed_git_state["branch"]:
        _reject("ephemeral_git_state_changed", "unchanged HEAD and branch",
                {"expected": {"head": baseline.get("head"), "branch": baseline.get("branch")},
                 "observed": {"head": current.get("head"), "branch": current.get("branch")}},
                "Ephemeral work may leave scoped scratch edits but cannot create commits or move branches.",
                anchor="worker" if worker else "acceptance", paths=paths)
    changed_paths = sorted(item["path"] for item in changes)
    outside = sorted(path for path in changed_paths if not _matches(path, binding["task"]["write_set"]))
    if outside:
        _reject("scope_drift", binding["task"]["write_set"], outside,
                "Ephemeral scratch changes outside the declared write set remain preserved in the worktree.",
                anchor="worker" if worker else "acceptance", paths=paths)
    audit: dict[str, Any] = {
        "status": "ephemeral-audit",
        "findings_only": True,
        "changed_paths": changed_paths,
        "baseline_fingerprint": workspace._state_fingerprint(baseline),
        "fingerprint": workspace._state_fingerprint(current),
        "head": current["head"],
        "branch": current["branch"],
        "scratch_retained": True,
    }
    if context is not None:
        audit["actual_cwd"] = context.get("actual_cwd")
    return {"ephemeral_audit": audit}


def _worktree(binding: Mapping[str, Any], *, phase: str, worker: bool) -> dict[str, Any]:
    bound = binding["workspace"]
    receipt = Path(bound["receipt"])
    paths = [bound["receipt"], bound["root"], bound["baseline"]]
    context = None
    if worker:
        try:
            context = workspace.check_context(receipt=receipt)
        except workspace.WorkspaceError as exc:
            raise _helper_failure("check the worker's actual worktree cwd", exc, anchor="worker", paths=paths) from exc
    if phase == "returned" and binding["task"]["mode"] == "ephemeral":
        return _ephemeral_audit(binding, context=context, worker=worker)
    delivery_mode = None
    commit_base = None
    commits: list[str] = []
    if phase == "returned":
        if binding["task"]["mode"] == "edit":
            delivery_mode = binding["task"]["delivery_mode"]
            if delivery_mode == "commits":
                commit_base = bound["commit_base"]
                try:
                    commits = workspace._git_text(
                        Path(bound["root"]), "rev-list", "--reverse", f"{commit_base}..HEAD",
                    ).splitlines()
                except workspace.WorkspaceError as exc:
                    raise _helper_failure("derive the complete contribution commit range", exc,
                                          anchor="acceptance", paths=paths) from exc
        else:
            delivery_mode = "report-only"
    try:
        inspected = workspace.inspect(
            receipt=receipt,
            phase=phase,
            delivery_mode=delivery_mode,
            commit_base=commit_base,
            commits=commits,
        )
    except workspace.WorkspaceError as exc:
        raise _helper_failure(f"inspect the {phase} worktree", exc,
                              anchor="worker" if phase == "prepared" else "acceptance", paths=paths) from exc
    if inspected.get("worktree") != bound["root"]:
        _reject("receipt_workspace_mismatch", bound["root"], inspected.get("worktree"),
                "The helper receipt resolved to a different worker workspace.", anchor="worker", paths=paths)
    if phase == "prepared" and inspected.get("fingerprint") != bound["prepared_fingerprint"]:
        _reject("prepared_baseline_mismatch", bound["prepared_fingerprint"], inspected.get("fingerprint"),
                "The helper's prepared state changed before worker edits.", anchor="worker", paths=paths)
    if phase == "returned":
        inspection_path = inspected.get("evidence", {}).get("inspection")
        try:
            inspection = json.loads(Path(inspection_path).read_text(encoding="utf-8"))
        except (OSError, TypeError, json.JSONDecodeError) as exc:
            _reject("inspection_evidence_unreadable", "the helper's returned inspection JSON", str(exc),
                    "The wrapper cannot check branch or HEAD movement without the helper's persisted inspection evidence.",
                    anchor="acceptance", paths=[*paths, inspection_path or ""])
        changed = inspection.get("git_state_changed", {})
        is_commits = binding["task"]["delivery_mode"] == "commits"
        if changed.get("branch") or (changed.get("head") and not is_commits):
            _reject("unsupported_commit_delivery", "the original branch and no HEAD movement except in commits mode",
                    changed,
                    "Only commits mode may advance HEAD; branch movement is never accepted and the receipt/worktree are retained.",
                    anchor="acceptance", paths=paths)
        contributions = inspected.get("contribution_paths", [])
        outside = sorted(path for path in contributions if not _matches(path, binding["task"]["write_set"]))
        if outside:
            _reject("scope_drift", binding["task"]["write_set"], outside,
                    "Returned contribution paths outside the declared scope remain preserved for parent review.",
                    anchor="acceptance", paths=[*paths, *inspected.get("evidence", {}).values()])
        if is_commits:
            delivery = inspected.get("delivery")
            if (not isinstance(delivery, dict) or delivery.get("mode") != "commits"
                    or delivery.get("base") != commit_base or delivery.get("commits") != commits
                    or delivery.get("commit_paths") != contributions
                    or not commits or delivery.get("residual_paths") != []):
                _reject("invalid_commit_delivery_evidence",
                        {"mode": "commits", "base": commit_base, "commits": commits,
                         "commit_paths": contributions, "residual_paths": []},
                        delivery,
                        "Commit delivery must contain the complete verified range and no residual worker changes.",
                        anchor="acceptance", paths=[*paths, *inspected.get("evidence", {}).values()])
            if bound["snapshot"]["source_dirty"]:
                contribution_patch = delivery.get("contribution_patch")
                patch_path = Path(contribution_patch) if isinstance(contribution_patch, str) else None
                if patch_path is None or not patch_path.is_absolute() or not patch_path.is_file():
                    _reject("missing_dirty_parent_contribution_patch",
                            "an absolute existing helper contribution patch for the dirty source snapshot",
                            contribution_patch,
                            "Dirty-parent commit delivery needs the verified worker contribution patch so the parent can preserve caller HEAD and index state.",
                            anchor="acceptance",
                            paths=[*paths, contribution_patch if isinstance(contribution_patch, str) else ""])
        inspected["git_state_changed"] = changed
    return {"context": context, "inspection": inspected}


def _summary(state: Mapping[str, Any]) -> dict[str, Any]:
    keys = ("schema", "status", "cwd", "root", "branch", "head", "fingerprint", "baseline_fingerprint",
            "verdict", "head_moved", "changed_paths", "outside_write_set", "write_set", "limitation")
    return {key: state[key] for key in keys if key in state}


def worker_start(raw: Any) -> dict[str, Any]:
    binding = _binding(raw)
    if binding["workspace"]["route"] == "worktree":
        evidence = _worktree(binding, phase="prepared", worker=True)
    else:
        state = _current(binding, process_cwd=True)
        if state.get("status") == "not-git":
            evidence = {"status": "no-drift-check-available", "cwd": state["cwd"],
                        "warning": binding["workspace"].get("no_drift_warning")}
        elif state.get("verdict") != "unchanged":
            _reject("baseline_changed_before_start", "unchanged current-state baseline", _summary(state),
                    "The current checkout changed after prepare and before the worker start check.",
                    anchor="worker", paths=[binding["workspace"]["source"]])
        else:
            evidence = _summary(state)
    return {"status": "WORKER_CONTEXT_READY", "binding_sha256": binding["binding_sha256"],
            "workspace_evidence": evidence, "native_lifecycle_verified": False}


def _acceptance(binding: Mapping[str, Any], evidence: Mapping[str, Any], command: str) -> dict[str, Any]:
    return {
        "status": "READY_FOR_PARENT_ACCEPTANCE", "command": command,
        "binding_sha256": binding["binding_sha256"], "workspace_evidence": dict(evidence),
        "native_lifecycle_verified": False, "semantic_acceptance": "pending",
        "limitations": ["Filesystem evidence does not prove native launch, task completion, or semantic correctness.",
                        "The parent must inspect the native result and decide acceptance and integration under existing policy."],
    }


def worker_finish(raw: Any) -> dict[str, Any]:
    binding = _binding(raw)
    if binding["workspace"]["route"] == "worktree":
        evidence = _worktree(binding, phase="returned", worker=True)
    else:
        state = _current(binding, process_cwd=True)
        if state.get("status") == "not-git":
            evidence = {"status": "no-drift-check-available", "cwd": state["cwd"],
                        "warning": binding["workspace"].get("no_drift_warning")}
        else:
            evidence = _summary(state)
    return _acceptance(binding, evidence, "worker-finish")


def verify_return(raw: Any) -> dict[str, Any]:
    binding = _binding(raw)
    if binding["workspace"]["route"] == "worktree":
        evidence = _worktree(binding, phase="returned", worker=False)
        _verify_source_capture(binding["workspace"])
    else:
        state = _current(binding, process_cwd=False)
        evidence = ({"status": "no-drift-check-available", "cwd": state["cwd"],
                     "warning": binding["workspace"].get("no_drift_warning")}
                    if state.get("status") == "not-git" else _summary(state))
    result = _acceptance(binding, evidence, "verify-return")
    task = binding["task"]
    if task["mode"] == "edit" and task["delivery_mode"] == "commits":
        snapshot = binding["workspace"]["snapshot"]
        inspection = evidence.get("inspection", {})
        delivery = inspection.get("delivery", {}) if isinstance(inspection, dict) else {}
        source_dirty = snapshot["source_dirty"]
        result["integration_strategy"] = {
            "strategy": "preserve-parent patch from commits" if source_dirty else "eligible cherry-pick",
            "source_dirty": source_dirty,
            "commit_base": binding["workspace"]["commit_base"],
            "commits": delivery.get("commits", []),
            "parent_target_revalidation_required": True,
        }
    return result


def _verify_source_capture(bound: Mapping[str, Any]) -> None:
    paths = [bound["source"], bound["receipt"], bound["baseline"]]
    try:
        record = workspace._load_receipt(Path(bound["receipt"]))
        with workspace._attempt_lock(record["attempt"]):
            _source, worktree = workspace._validate_binding(record)
            if worktree is None or os.fspath(worktree) != bound["root"]:
                _reject("receipt_workspace_mismatch", bound["root"],
                        os.fspath(worktree) if worktree else None,
                        "The helper receipt resolved to a different worker workspace.",
                        anchor="acceptance", paths=paths)
            if record["source"]["root"] != bound["source"]:
                _reject("receipt_source_mismatch", bound["source"], record["source"]["root"],
                        "The helper receipt is bound to a different original source checkout.",
                        anchor="acceptance", paths=paths)
            expected = record["baseline_data"].get("source_capture")
            if not isinstance(expected, dict):
                _reject("source_capture_missing", "the original source capture in the helper receipt",
                        expected,
                        "The parent cannot revalidate its checkout against the task's prepare-time source state.",
                        anchor="acceptance", paths=paths)
            observed = workspace._capture_source(Path(bound["source"])).comparable()
    except workspace.WorkspaceError as exc:
        raise _helper_failure("revalidate the original source capture", exc,
                              anchor="acceptance", paths=paths) from exc
    if observed != expected:
        changed_fields = sorted(key for key in set(expected) | set(observed)
                                if expected.get(key) != observed.get(key))
        _reject("source_capture_drift",
                {"sha256": hashlib.sha256(_json_bytes(expected)).hexdigest(), "fields": sorted(expected)},
                {"sha256": hashlib.sha256(_json_bytes(observed)).hexdigest(), "changed_fields": changed_fields},
                "The original checkout's HEAD, branch, index, or working files changed after prepare. "
                "Keep the worktree and receipt; the parent must resolve source drift and revalidate again immediately before any integration.",
                anchor="acceptance", paths=paths)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        _reject("invalid_cli", "prepare, worker-start, worker-finish, or verify-return with required options", message,
                "The command line did not select one complete operation.",
                next_step="Run `ask_agent_task.py --help` and retry with the required options.")


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="ask_agent_task.py", description="Prepare and verify bounded Ask Agent work")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="validate a request and emit a parent binding")
    prepare.add_argument("--skill-card", required=True, help="absolute selected package SKILL.md")
    prepare.add_argument("--request", required=True, help="JSON file path or - for stdin")
    for name in ("worker-start", "worker-finish", "verify-return"):
        command = commands.add_parser(name)
        command.add_argument("--binding", required=True, help="JSON file path or - for stdin")
    return parser


def _emit(value: Mapping[str, Any], stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n")


def _terminate(signum: int, _frame: Any) -> None:
    # The helper's prepare routine catches SystemExit and runs its own cleanup.
    raise SystemExit(128 + signum)


def main(argv: Sequence[str] | None = None) -> int:
    for signum in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, _terminate)
    try:
        parsed = _parser().parse_args(argv)
        if parsed.command == "prepare":
            result = prepare_task(_read_json(parsed.request, "request"), Path(parsed.skill_card))
        else:
            raw = _read_json(parsed.binding, "binding")
            result = {"worker-start": worker_start, "worker-finish": worker_finish,
                      "verify-return": verify_return}[parsed.command](raw)
        _emit(result)
        return 0
    except TaskError as exc:
        _emit(exc.as_json(), sys.stderr)
        return 2
    except workspace.WorkspaceError as exc:
        _emit(_helper_failure("complete the operation", exc, anchor="failures").as_json(), sys.stderr)
        return 2
    except OSError as exc:
        error = TaskError({
            "code": "filesystem_error", "expected": "readable source, package, and evidence paths",
            "observed": str(exc), "rationale": "A required local path could not be inspected.",
            "reference": f"{TASK_INTERFACE}#failures", "evidence_paths": [],
            "safe_next_step": NEXT_STEPS["failures"],
        })
        _emit(error.as_json(), sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
