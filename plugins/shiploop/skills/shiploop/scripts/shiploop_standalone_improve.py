#!/usr/bin/env python3
"""Read-only import bridge for an actual standalone Improve/Until Loop run.

ShipLoop owns its graph cursor.  Improve owns its own review loop and the
bound Until Loop runtime owns that loop's state.  This module deliberately
does not invoke that runtime, write its state, or infer Improve convergence.
The host follows the selected Improve card; once the host reports a completed
child, ShipLoop uses these functions to bind and import durable evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, Mapping

import shiploop_store as store


VERSION = 1
RUN_DIRECTORY = ".until-loop"
_ACTION = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,159}$")
_MAX_BYTES = 4 * 1024 * 1024

__all__ = [
    "StandaloneImproveError",
    "binding",
    "complete",
    "resolve_skill",
]


class StandaloneImproveError(ValueError):
    """The selected skill or external child is unavailable or unsafe."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise StandaloneImproveError(message)


def _copy(value: Any, label: str) -> Any:
    try:
        return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise StandaloneImproveError(f"{label} must be JSON-compatible") from exc


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _utf8(raw: bytes, label: str) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StandaloneImproveError(f"{label} is not UTF-8 text and cannot be archived") from exc


def _safe_file(path: Path, label: str, *, allow_selected_symlink: bool = False) -> Path:
    try:
        supplied = path.lstat()
        _need(allow_selected_symlink or not stat.S_ISLNK(supplied.st_mode),
              f"{label} cannot be a symlink")
        value = path.resolve(strict=True)
        metadata = value.lstat()
    except (OSError, RuntimeError) as exc:
        raise StandaloneImproveError(f"{label} is unavailable: {path}") from exc
    _need(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1,
          f"{label} must be a regular single-link file")
    return value


def _safe_dir(path: Path, label: str) -> Path:
    try:
        value = path.resolve(strict=True)
        metadata = value.lstat()
    except (OSError, RuntimeError) as exc:
        raise StandaloneImproveError(f"{label} is unavailable: {path}") from exc
    _need(stat.S_ISDIR(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode),
          f"{label} must be a real directory")
    return value


def _workspace_file(workspace: Path, relative: Path, label: str) -> Path:
    """Read a regular file below workspace without following child links."""
    _need(not relative.is_absolute(), f"{label} must be relative to its workspace")
    current = workspace
    for part in relative.parts:
        _need(part not in ("", ".", ".."), f"unsafe {label}")
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as exc:
            raise StandaloneImproveError(f"{label} is unavailable: {current}") from exc
        _need(not stat.S_ISLNK(metadata.st_mode), f"{label} cannot be a symlink")
    _need(stat.S_ISREG(current.lstat().st_mode) and current.lstat().st_nlink == 1,
          f"{label} must be a regular single-link file")
    return current


def _read_workspace(workspace: Path, relative: Path, label: str) -> bytes:
    return _read(_workspace_file(workspace, relative, label), label)


def _under(path: Path, root: Path, label: str) -> Path:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise StandaloneImproveError(f"{label} escapes its expected root") from exc
    return path


def _read(path: Path, label: str) -> bytes:
    file_path = _safe_file(path, label)
    try:
        before = file_path.stat()
        with file_path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            _need((before.st_dev, before.st_ino) == (opened.st_dev, opened.st_ino),
                  f"{label} changed during read")
            raw = handle.read(_MAX_BYTES + 1)
    except StandaloneImproveError:
        raise
    except OSError as exc:
        raise StandaloneImproveError(f"cannot read {label}") from exc
    _need(len(raw) <= _MAX_BYTES, f"{label} exceeds {_MAX_BYTES} bytes")
    return raw


def _json(raw: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise StandaloneImproveError(f"{label} has duplicate key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StandaloneImproveError(f"{label} is not valid UTF-8 JSON") from exc
    _need(isinstance(value, dict), f"{label} must be an object")
    return _copy(value, label)


def _text(value: Any, label: str) -> str:
    _need(isinstance(value, str) and bool(value.strip()) and "\x00" not in value,
          f"{label} must be nonempty text")
    return value


def _action(value: Any, label: str) -> str:
    _need(isinstance(value, str) and _ACTION.fullmatch(value) is not None,
          f"{label} is unsafe")
    return value


def _workspace(value: Any, label: str = "workspace") -> Path:
    _need(isinstance(value, str) and value, f"{label} must be an absolute path")
    path = Path(value)
    _need(path.is_absolute(), f"{label} must be absolute")
    return _safe_dir(path, label)


def _card_text(path: Path, label: str) -> str:
    try:
        return _read(path, label).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StandaloneImproveError(f"{label} is not UTF-8") from exc


def _skill_kind(text: str) -> None:
    _need(re.search(r"^name:\s*improve\s*$", text, re.MULTILINE) is not None,
          "selected skill card is not the Improve card")
    _need("until-loop" in text.lower(), "selected Improve card does not bind Until Loop")


def _declared_version(text: str) -> str:
    """Return a card's explicit frontmatter version without inventing one."""
    match = re.search(r"^version:\s*([^\s#][^\r\n]*)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match is not None else "unversioned"


def resolve_skill(path: str) -> dict[str, str]:
    """Resolve only a caller-selected Improve card and its documented runtime.

    Supported layouts are the standalone package (``runtime/until-loop``) and
    the installed Improve example whose documented parent is ``../../SKILL.md``.
    No PATH or ambient same-name skill discovery is performed.
    """
    _need(isinstance(path, str) and path, "skill card path is required")
    supplied = Path(path)
    _need(supplied.is_absolute(), "skill card path must be absolute")
    skill_card = _safe_file(supplied, "selected Improve card", allow_selected_symlink=True)
    text = _card_text(skill_card, "selected Improve card")
    _skill_kind(text)
    root = skill_card.parent

    bundled_card = root / "runtime" / "until-loop" / "ADAPTER.md"
    bundled_cli = root / "runtime" / "until-loop" / "scripts" / "until-loop"
    if bundled_card.exists() or bundled_card.is_symlink():
        runtime_card = _safe_file(bundled_card, "bound Until Loop adapter")
        runtime_cli = _safe_file(bundled_cli, "bound Until Loop CLI")
    elif "../../SKILL.md" in text:
        runtime_card = _safe_file(root.parent.parent / "SKILL.md", "bound Until Loop card")
        runtime_cli = _safe_file(runtime_card.parent / "scripts" / "until-loop", "bound Until Loop CLI")
    else:
        raise StandaloneImproveError("selected Improve card has no supported bound Until Loop layout")
    runtime_text = _card_text(runtime_card, "bound Until Loop card")
    _need(re.search(r"^name:\s*until-loop\s*$", runtime_text, re.MULTILINE) is not None,
          "bound runtime card is not Until Loop")
    return {
        "skill_card": str(skill_card),
        "skill_version": _declared_version(text),
        "runtime_card": str(runtime_card),
        "runtime_cli": str(runtime_cli),
        "runtime_version": _declared_version(runtime_text),
    }


def _run_dir(workspace: Path) -> Path:
    path = workspace / RUN_DIRECTORY
    try:
        _need(not stat.S_ISLNK(path.lstat().st_mode), "Until Loop run directory cannot be a symlink")
    except OSError as exc:
        raise StandaloneImproveError(f"Until Loop run directory is unavailable: {path}") from exc
    return _safe_dir(path, "Until Loop run directory")


def _state_paths(workspace: Path) -> tuple[Path, Path, Path]:
    run_dir = _run_dir(workspace)
    return run_dir, run_dir / "state.json", run_dir / "history.jsonl"


def _binding_marker(binding_id: str) -> str:
    return f"ShipLoop standalone Improve binding: {binding_id}"


def _marked_binding_id(state: Mapping[str, Any]) -> str | None:
    """Return the one exact ShipLoop marker in a frozen child contract."""
    contract = state.get("contract")
    request = contract.get("original_request") if isinstance(contract, Mapping) else None
    _need(isinstance(request, str), "Until Loop state has no original request")
    prefix = "ShipLoop standalone Improve binding: "
    identifiers: list[str] = []
    for line in request.splitlines():
        if not line.startswith(prefix):
            continue
        identifier = line[len(prefix):]
        pieces = identifier.split("/")
        _need(len(pieces) == 2 and all(_ACTION.fullmatch(piece) is not None for piece in pieces),
              "Until Loop ShipLoop binding marker is invalid")
        identifiers.append(identifier)
    _need(len(identifiers) <= 1, "Until Loop contract has multiple ShipLoop binding markers")
    return identifiers[0] if identifiers else None


def _state_for(workspace: Path) -> tuple[dict[str, Any], bytes, Path, bytes]:
    run_dir, state_path, history_path = _state_paths(workspace)
    for pending in (run_dir / ".pending-v2.json", run_dir / ".pending.json"):
        if pending.exists() or pending.is_symlink():
            raise StandaloneImproveError(
                "Until Loop has a pending journal; use its bound adapter next, then retry"
            )
    state_raw = _read_workspace(workspace, state_path.relative_to(workspace), "Until Loop state")
    # A freshly initialized active v2 run has no accepted assessment and may
    # legitimately have no history yet.  Terminal import below still requires
    # the history file, because a completed child must have a receipt.
    history_raw = b"" if not (history_path.exists() or history_path.is_symlink()) else _read_workspace(
        workspace, history_path.relative_to(workspace), "Until Loop history"
    )
    state = _json(state_raw, "Until Loop state")
    return state, state_raw, run_dir, history_raw


def _assert_v2_state(state: Mapping[str, Any], workspace: Path) -> Mapping[str, Any]:
    required = {
        "version", "phase", "repo_root", "max_cycles", "cycle", "contract",
        "policy_snapshot", "verify_cmd", "last_verify", "recovery", "action",
        "last_assessment", "pause",
    }
    _need(set(state) == required, "Until Loop state has an unsupported schema")
    _need(state.get("version") == 2, "Until Loop state is not v2")
    _need(state.get("repo_root") == str(workspace), "Until Loop state is bound to another workspace")
    _need(isinstance(state.get("contract"), Mapping), "Until Loop state has no contract")
    return state


def _settled_done(state: Mapping[str, Any]) -> None:
    _need(state.get("phase") == "done", "previous Improve child is not settled")
    _need(state.get("action") is None and state.get("recovery") is None,
          "previous Improve child has active or uncertain work")
    assessment = state.get("last_assessment")
    _need(isinstance(assessment, Mapping) and assessment.get("decision") == "complete",
          "previous Improve child has no accepted complete assessment")
    if state.get("verify_cmd") is not None:
        verify = state.get("last_verify")
        _need(isinstance(verify, Mapping) and verify.get("ok") is True,
              "previous Improve child verifier did not pass")


def _binding_matches(state: Mapping[str, Any], binding_id: str) -> None:
    _need(_marked_binding_id(state) == binding_id,
          "Until Loop frozen contract is not bound to this ShipLoop action")


def _binding_imported(parent: Mapping[str, Any], binding_id: str) -> bool:
    """Check only ShipLoop's durable import ledger, never a host claim."""
    records = parent.get("improve_results")
    if not isinstance(records, Mapping):
        return False
    return any(
        isinstance(record, Mapping) and record.get("binding_id") == binding_id
        for record in records.values()
    )


def _current_child(workspace: Path) -> dict[str, Any] | None:
    run_dir = workspace / RUN_DIRECTORY
    if not (run_dir.exists() or run_dir.is_symlink()):
        return None
    state, raw, _run, _history = _state_for(workspace)
    return {"state": state, "digest": _digest(raw)}


def binding(
    state: Mapping[str, Any], parent_action: str, stage: str,
    pending_result: Mapping[str, Any] | None, skill: Mapping[str, Any],
) -> dict[str, Any]:
    """Make a non-mutating parent-to-child binding for one graph action."""
    _need(isinstance(state, Mapping), "ShipLoop state must be an object")
    action = _action(parent_action, "parent action")
    stage_text = _text(stage, "stage")
    run_id = _action(state.get("run_id"), "ShipLoop run ID")
    workspace_value = state.get("repo", state.get("repo_root"))
    _need(isinstance(workspace_value, str) and workspace_value, "workspace must be an absolute path")
    workspace = _workspace(workspace_value)
    expected_skill = {"skill_card", "skill_version", "runtime_card", "runtime_cli", "runtime_version"}
    _need(isinstance(skill, Mapping) and set(skill) == expected_skill,
          "skill binding has an unsupported schema")
    resolved = resolve_skill(_text(skill.get("skill_card"), "skill card"))
    _need(resolved == dict(skill), "skill binding is not the selected card's bound runtime")
    binding_id = f"{run_id}/{action}"
    existing = _current_child(workspace)
    if existing is not None:
        child_state = _assert_v2_state(existing["state"], workspace)
        phase = child_state["phase"]
        if phase == "done":
            _settled_done(child_state)
            prior_binding = _marked_binding_id(child_state)
            if prior_binding is not None and prior_binding != binding_id:
                _need(_binding_imported(state, prior_binding),
                      "previous completed ShipLoop Improve child was not imported")
        else:
            _binding_matches(child_state, binding_id)
        # A settled `done` child is preserved by Until Loop history and may be
        # replaced by the host's authorized v2 init --force for this next action.
    return {
        "version": VERSION,
        "binding_id": binding_id,
        # Retain the parent's supplied absolute locator for cold recovery and
        # cursor validation.  Filesystem checks below use ``workspace``'s
        # resolved physical identity, so `/tmp` versus `/private/tmp` cannot
        # become an authority bypass.
        "workspace": workspace_value,
        "action_id": action,
        "stage": stage_text,
        "skill": resolved,
        "contract_marker": _binding_marker(binding_id),
        "seed_result": _copy(dict(pending_result or {}), "pending result"),
    }


def _local_reference(workspace: Path, locator: str, value: Any, label: str) -> str:
    _need(isinstance(value, str) and value.strip(), f"{label} must be a local path")
    raw = Path(value)
    if raw.is_absolute():
        try:
            relative = raw.relative_to(workspace)
        except ValueError as exc:
            # The parent stores its exact lexical workspace locator for cold
            # recovery.  An agent may therefore return `/tmp/...` while the
            # runtime canonicalizes to `/private/tmp/...`.  Derive a relative
            # path lexically, then re-read it below the validated physical
            # workspace; do not resolve the untrusted reference itself.
            try:
                relative = raw.relative_to(Path(locator))
            except ValueError:
                raise StandaloneImproveError(f"{label} escapes its expected root") from exc
    else:
        relative = raw
    file_path = _workspace_file(workspace, relative, label)
    return str(file_path.relative_to(workspace))


def _receipt(receipt: Mapping[str, Any], workspace: Path, locator: str) -> dict[str, Any]:
    _need(isinstance(receipt, Mapping), "Improve receipt must be an object")
    allowed = {"summary", "review_refs", "check_refs", "lessons", "final_result"}
    _need(set(receipt) <= allowed and {"summary", "review_refs", "check_refs"} <= set(receipt),
          "Improve receipt has unsupported or missing fields")
    review_raw = receipt["review_refs"]
    check_raw = receipt["check_refs"]
    _need(isinstance(review_raw, list) and len(review_raw) == 2,
          "Improve receipt requires exactly two review references")
    _need(isinstance(check_raw, list) and bool(check_raw),
          "Improve receipt requires at least one check reference")
    reviews = [_local_reference(workspace, locator, value, "review reference") for value in review_raw]
    _need(len(set(reviews)) == 2, "Improve review references must be distinct")
    checks = [_local_reference(workspace, locator, value, "check reference") for value in check_raw]
    copied: dict[str, Any] = {
        "summary": _text(receipt["summary"], "receipt summary"),
        "review_refs": reviews,
        "check_refs": checks,
    }
    if "lessons" in receipt:
        copied["lessons"] = _text(receipt["lessons"], "receipt lessons")
    if "final_result" in receipt:
        copied["final_result"] = _copy(receipt["final_result"], "receipt final result")
    return copied


def _last_result_path(run_dir: Path, state: Mapping[str, Any]) -> Path | None:
    last = state.get("last_assessment")
    action_id = last.get("action_id") if isinstance(last, Mapping) else None
    if not isinstance(action_id, str) or not re.fullmatch(r"[0-9a-f]{32}", action_id):
        return None
    return run_dir / "results" / f"{action_id}.json"


def _reference_digests(workspace: Path, receipt: Mapping[str, Any]) -> dict[str, str]:
    """Capture the bytes actually observed for caller-declared evidence files."""
    values = list(receipt["review_refs"]) + list(receipt["check_refs"])
    result: dict[str, str] = {}
    for reference in values:
        if reference not in result:
            result[reference] = _digest(
                _read_workspace(workspace, Path(reference), "Improve receipt evidence")
            )
    return result


def _evidence_archives(workspace: Path, action: str, receipt: Mapping[str, Any]) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Copy declared terminal evidence so a later edit cannot rewrite the proof."""
    writes: dict[str, str] = {}
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    values = list(receipt["review_refs"]) + list(receipt["check_refs"])
    for index, reference in enumerate(values, start=1):
        if reference in seen:
            continue
        seen.add(reference)
        raw = _read_workspace(workspace, Path(reference), "Improve receipt evidence")
        archive_path = f"improve/{action}/evidence/{index:02d}-{Path(reference).name}"
        writes[archive_path] = _utf8(raw, "Improve receipt evidence")
        entries.append({
            "source": reference,
            "archive": archive_path,
            "sha256": _digest(raw),
        })
    return writes, entries


def _runtime_digest(value: Any) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise StandaloneImproveError("Until Loop data is not JSON-safe") from exc
    return _digest(raw)


def _terminal_receipt(history_raw: bytes, state: Mapping[str, Any]) -> None:
    """Bind terminal state to its actual final accepted runtime history row."""
    try:
        lines = history_raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise StandaloneImproveError("Until Loop history is not UTF-8") from exc
    _need(lines, "Improve child has no accepted history receipt")
    rows: list[dict[str, Any]] = []
    for line in lines:
        if not line:
            continue
        rows.append(_json(line.encode("utf-8"), "Until Loop history row"))
    _need(rows, "Improve child has no accepted history receipt")
    row = rows[-1]
    assessment = state["last_assessment"]
    _need(row.get("type") == "assessment" and row.get("decision") == "complete" and row.get("phase") == "done",
          "Until Loop terminal history does not contain a completed assessment")
    _need(row.get("assessment") == assessment and row.get("digest") == _runtime_digest(assessment),
          "Until Loop terminal history does not match its final assessment")
    _need(row.get("state_digest") == _runtime_digest(dict(state)),
          "Until Loop terminal history does not match current state")


def complete(binding: Mapping[str, Any], receipt: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Validate an actual terminal child and return immutable parent archive writes.

    The caller must have already used the selected runtime's ``next`` command
    for recovery.  This pure reader rejects pending journals rather than
    duplicating the runtime's recovery implementation.
    """
    expected = {"version", "binding_id", "workspace", "action_id", "stage", "skill", "contract_marker", "seed_result"}
    _need(isinstance(binding, Mapping) and set(binding) == expected,
          "standalone Improve binding has an unsupported schema")
    _need(binding.get("version") == VERSION, "unsupported standalone Improve binding version")
    action = _action(binding.get("action_id"), "binding action")
    binding_id = _text(binding.get("binding_id"), "binding ID")
    _need(binding_id.endswith("/" + action), "binding ID does not match parent action")
    workspace = _workspace(binding.get("workspace"))
    _need(binding.get("contract_marker") == _binding_marker(binding_id), "binding marker is invalid")
    resolved = resolve_skill(_text(binding.get("skill", {}).get("skill_card") if isinstance(binding.get("skill"), Mapping) else None, "bound skill card"))
    _need(resolved == binding.get("skill"), "bound Improve runtime differs from selected card")
    state, state_raw, run_dir, history_raw = _state_for(workspace)
    _assert_v2_state(state, workspace)
    _binding_matches(state, binding_id)
    _need(state["phase"] == "done", "Improve child is not completed")
    _settled_done(state)
    assessment = state["last_assessment"]
    _need(bool(history_raw), "Improve child has no accepted history receipt")
    _terminal_receipt(history_raw, state)
    if state["verify_cmd"] is not None:
        verify = state["last_verify"]
        _need(isinstance(verify, Mapping) and verify.get("ok") is True,
              "Improve child's configured verifier did not pass")
    checked_receipt = _receipt(receipt, workspace, binding["workspace"])
    evidence_digests = _reference_digests(workspace, checked_receipt)
    working_path = run_dir / "working.md"
    working_raw = _read_workspace(workspace, working_path.relative_to(workspace), "Improve working notebook")
    result_path = _last_result_path(run_dir, state)
    _need(result_path is not None, "Improve child has no runtime-issued final result path")
    result_raw = _read_workspace(workspace, result_path.relative_to(workspace), "Improve final assessment result")
    _need(_json(result_raw, "Improve final assessment result") == _copy(assessment, "final assessment"),
          "Improve final assessment result does not match terminal state")
    prefix = f"improve/{action}"
    archive: dict[str, str] = {
        f"{prefix}/state.json": _utf8(state_raw, "Until Loop state"),
        f"{prefix}/history.jsonl": _utf8(history_raw, "Until Loop history"),
        f"{prefix}/working.md": _utf8(working_raw, "Improve working notebook"),
        f"{prefix}/result.json": _utf8(result_raw, "Improve final assessment result"),
    }
    evidence_writes, evidence_entries = _evidence_archives(workspace, action, checked_receipt)
    archive.update(evidence_writes)
    identities: dict[str, Any] = {
        "state_sha256": _digest(state_raw),
        "history_sha256": _digest(history_raw),
        "working_sha256": _digest(working_raw),
        "contract_sha256": _runtime_digest(state["contract"]),
        "evidence_sha256": evidence_digests,
    }
    identities["result_sha256"] = _digest(result_raw)
    record = {
        "version": VERSION,
        "binding_id": binding_id,
        "workspace": str(workspace),
        "action_id": action,
        "stage": binding["stage"],
        "skill": resolved,
        "runtime_phase": "done",
        "identities": identities,
        "evidence": evidence_entries,
        "receipt": checked_receipt,
        "stale_check_note": "This import records current bytes for declared local evidence and validates the terminal Until Loop record. It does not establish future freshness, candidate scope, or semantic Improve convergence; those remain the selected Improve skill and parent action's responsibility.",
    }
    archive[f"{prefix}/receipt.md"] = store.dumps(record, "ShipLoop standalone Improve receipt")
    return record, archive
