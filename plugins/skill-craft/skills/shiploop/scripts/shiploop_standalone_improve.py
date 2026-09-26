#!/usr/bin/env python3
"""Read-only import bridge for an actual standalone Improve/Until Loop run.

ShipLoop owns its graph cursor.  Improve owns its own review loop and the
bound ephemeral Until Loop runtime owns that loop's private state.  This
module deliberately does not invoke that runtime, write its state, or infer
Improve convergence.  The host follows the selected Improve card; once the
host reports a completed child, ShipLoop uses these functions to bind the
child and import its host-preserved terminal packet.
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
_ACTION = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,159}$")
_MAX_BYTES = 4 * 1024 * 1024
_EPHEMERAL_DECLARATION = "scripts/until_loop_ephemeral.py"
_EPHEMERAL_CLI = "until_loop_ephemeral.py"
_RECEIPT_DIRECTORY = ".shiploop-improve"
_TERMINAL_PACKET_NAME = "packet.json"
_SKILL_FIELDS = {"skill_card", "skill_version", "runtime_card", "runtime_cli", "runtime_version"}
_BINDING_FIELDS = {
    "version", "binding_id", "workspace", "action_id", "stage", "skill",
    "contract_marker", "seed_result",
}
_CONTEXT_FIELDS = {"request", "scope", "authority", "environment", "resources"}
_RESOURCE_FIELDS = {"purpose", "locator"}
_REPORT_FIELDS = {
    "classification", "exit_assessment", "continuation_assessment", "evidence", "handoff",
}
_INCOMPLETE_RECEIPT_FIELDS = {"summary", "target", "evidence_refs"}
_RECONCILIATION_TARGETS = {"discovery", "research", "spec", "test-strategy"}
_TERMINAL_PACKET_FIELDS = {
    "status", "state_file", "workspace", "work", "conditions", "progress", "context",
    "status_semantics", "last_report", "instruction", "next_argv",
    "done_argv", "report_schema",
}

__all__ = [
    "StandaloneImproveError",
    "binding",
    "complete",
    "receipt_path",
    "resolve_skill",
    "settle_incomplete",
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


_UNSUPPORTED_RUNTIME = (
    "durable Until Loop runtimes are no longer supported; select the current Improve card"
)


def resolve_skill(path: str) -> dict[str, str]:
    """Resolve only a caller-selected Improve card and its ephemeral runtime.

    The one supported layout is the Improve package whose
    ``runtime/until-loop/ADAPTER.md`` declares ``scripts/until_loop_ephemeral.py``.
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
    _need(bundled_card.exists() or bundled_card.is_symlink(), _UNSUPPORTED_RUNTIME)
    runtime_card = _safe_file(bundled_card, "bound Until Loop adapter")
    runtime_root = runtime_card.parent
    runtime_text = _card_text(runtime_card, "bound Until Loop card")
    _need(re.search(r"^name:\s*until-loop\s*$", runtime_text, re.MULTILINE) is not None,
          "bound runtime card is not Until Loop")
    # The runtime comes only from the selected card's declared binding.  Do not
    # discover a same-named file or infer a protocol from ambient workspace state.
    _need(_EPHEMERAL_DECLARATION in runtime_text, _UNSUPPORTED_RUNTIME)
    runtime_cli = _safe_file(runtime_root / "scripts" / _EPHEMERAL_CLI, "bound Until Loop CLI")
    return {
        "skill_card": str(skill_card),
        "skill_version": _declared_version(text),
        "runtime_card": str(runtime_card),
        "runtime_cli": str(runtime_cli),
        "runtime_version": _declared_version(runtime_text),
    }


def _binding_marker(binding_id: str) -> str:
    return f"ShipLoop standalone Improve binding: {binding_id}"


def _marked_request_binding_id(request: Any, label: str) -> str | None:
    """Return the one exact ShipLoop marker in a frozen request string."""
    request_text = _text(request, f"{label} request")
    prefix = "ShipLoop standalone Improve binding: "
    identifiers: list[str] = []
    for line in request_text.splitlines():
        if not line.startswith(prefix):
            continue
        identifier = line[len(prefix):]
        pieces = identifier.split("/")
        _need(len(pieces) == 2 and all(_ACTION.fullmatch(piece) is not None for piece in pieces),
              f"{label} ShipLoop binding marker is invalid")
        identifiers.append(identifier)
    _need(len(identifiers) <= 1, f"{label} contract has multiple ShipLoop binding markers")
    return identifiers[0] if identifiers else None


def _binding_identity(binding: Mapping[str, Any]) -> tuple[str, str, Path, str]:
    """Validate stable binding identity without resolving its selected package."""
    _need(isinstance(binding, Mapping) and set(binding) == _BINDING_FIELDS,
          "standalone Improve binding has an unsupported schema")
    _need(binding.get("version") == VERSION, "unsupported standalone Improve binding version")
    action = _action(binding.get("action_id"), "binding action")
    binding_id = _text(binding.get("binding_id"), "binding ID")
    pieces = binding_id.split("/")
    _need(len(pieces) == 2 and all(_ACTION.fullmatch(piece) is not None for piece in pieces),
          "binding ID is invalid")
    _need(pieces[1] == action, "binding ID does not match parent action")
    workspace_value = _text(binding.get("workspace"), "binding workspace")
    workspace = _workspace(workspace_value)
    _text(binding.get("stage"), "binding stage")
    _need(binding.get("contract_marker") == _binding_marker(binding_id), "binding marker is invalid")
    _need(isinstance(binding.get("skill"), Mapping) and set(binding["skill"]) == _SKILL_FIELDS,
          "skill binding has an unsupported schema")
    for key, value in binding["skill"].items():
        _text(value, f"bound skill {key}")
    _copy(binding.get("seed_result"), "pending result")
    return action, binding_id, workspace, workspace_value


def _receipt_relative(binding_id: str, action: str) -> Path:
    run_id, marked_action = binding_id.split("/", 1)
    _need(marked_action == action, "binding ID does not match parent action")
    return Path(_RECEIPT_DIRECTORY) / run_id / action / _TERMINAL_PACKET_NAME


def receipt_path(binding: Mapping[str, Any]) -> Path:
    """Return the deterministic host receipt location for an ephemeral child.

    This is a host-owned copy of the latest raw runtime packet.  It is not an
    Until Loop state file and this bridge never creates or advances it.
    """
    action, binding_id, _workspace, workspace_value = _binding_identity(binding)
    # Preserve the parent-selected lexical locator for the printed recovery
    # packet.  `_binding_identity` has already resolved and checked its
    # physical directory; import reads below that physical identity with its
    # no-follow helper.
    return Path(workspace_value) / _receipt_relative(binding_id, action)


def binding(
    state: Mapping[str, Any], parent_action: str, stage: str,
    pending_result: Mapping[str, Any] | None, skill: Mapping[str, Any],
) -> dict[str, Any]:
    """Make a non-mutating parent-to-child binding for one graph action."""
    _need(isinstance(state, Mapping), "ShipLoop state must be an object")
    action = _action(parent_action, "parent action")
    stage_text = _text(stage, "stage")
    run_id = _action(state.get("run_id"), "ShipLoop run ID")
    workspace_value = state.get("repo")
    _need(isinstance(workspace_value, str) and workspace_value, "workspace must be an absolute path")
    _workspace(workspace_value)
    _need(isinstance(skill, Mapping) and set(skill) == _SKILL_FIELDS,
          "skill binding has an unsupported schema")
    resolved = resolve_skill(_text(skill.get("skill_card"), "skill card"))
    _need(resolved == dict(skill), "skill binding is not the selected card's bound runtime")
    binding_id = f"{run_id}/{action}"
    # An ephemeral child has one private tempfile per invocation.  It has no
    # ambient workspace ownership record for this parent to inspect.
    return {
        "version": VERSION,
        "binding_id": binding_id,
        # Retain the parent's supplied absolute locator for cold recovery and
        # cursor validation.  Import checks use the workspace's resolved
        # physical identity, so `/tmp` versus `/private/tmp` cannot become an
        # authority bypass.
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


def _absolute_local_reference(workspace: Path, locator: str, value: Any, label: str) -> str:
    _need(isinstance(value, str) and value.strip(), f"{label} must be a local path")
    _need(Path(value).is_absolute(), f"{label} must be an absolute local path")
    return _local_reference(workspace, locator, value, label)


def _receipt(receipt: Mapping[str, Any], workspace: Path, locator: str) -> dict[str, Any]:
    _need(isinstance(receipt, Mapping), "Improve receipt must be an object")
    allowed = {"summary", "review_refs", "check_refs", "lessons", "final_result", "no_commit"}
    _need(set(receipt) <= allowed and {"summary", "review_refs", "check_refs"} <= set(receipt),
          "Improve receipt has unsupported or missing fields")
    review_raw = receipt["review_refs"]
    check_raw = receipt["check_refs"]
    _need(isinstance(review_raw, list) and len(review_raw) in (1, 2),
          "Improve receipt requires the trivial-streak review references (two, or one when the first pass "
          "changed nothing), got " + (str(len(review_raw)) if isinstance(review_raw, list) else "a non-list")
          + "; leave earlier material reviews on disk")
    _need(isinstance(check_raw, list) and bool(check_raw),
          "Improve receipt requires at least one check reference")
    reviews = [_local_reference(workspace, locator, value, "review reference") for value in review_raw]
    _need(len(set(reviews)) == len(reviews), "Improve review references must be distinct")
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
    if "no_commit" in receipt:
        # The user's or repository's instruction not to commit the review's edits.
        copied["no_commit"] = _text(receipt["no_commit"], "receipt no_commit reason")
    return copied


def _incomplete_receipt(receipt: Mapping[str, Any], workspace: Path, locator: str) -> dict[str, Any]:
    """Normalize a non-success reconciliation submission without success fields."""
    _need(isinstance(receipt, Mapping) and set(receipt) == _INCOMPLETE_RECEIPT_FIELDS,
          "incomplete Improve receipt has unsupported or missing fields")
    target = receipt.get("target")
    _need(isinstance(target, str) and target in _RECONCILIATION_TARGETS,
          "incomplete Improve receipt target is invalid")
    raw_references = receipt.get("evidence_refs")
    _need(isinstance(raw_references, list) and bool(raw_references),
          "incomplete Improve receipt requires at least one evidence reference")
    references = [
        _absolute_local_reference(workspace, locator, value, "incomplete Improve evidence reference")
        for value in raw_references
    ]
    _need(len(set(references)) == len(references),
          "incomplete Improve evidence references must be distinct")
    return {
        "summary": _text(receipt.get("summary"), "incomplete Improve receipt summary"),
        "target": target,
        "evidence_refs": references,
    }


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


def _incomplete_evidence_snapshot(
    workspace: Path, action: str, receipt: Mapping[str, Any],
) -> tuple[dict[str, str], list[dict[str, str]], dict[str, str]]:
    """Capture each declared incomplete evidence file once for archive and identity."""
    writes: dict[str, str] = {}
    entries: list[dict[str, str]] = []
    identities: dict[str, str] = {}
    for index, reference in enumerate(receipt["evidence_refs"], start=1):
        raw = _read_workspace(workspace, Path(reference), "incomplete Improve receipt evidence")
        archive_path = f"improve/{action}/evidence/{index:02d}-{Path(reference).name}"
        digest = _digest(raw)
        writes[archive_path] = _utf8(raw, "incomplete Improve receipt evidence")
        identities[reference] = digest
        entries.append({
            "source": reference,
            "archive": archive_path,
            "sha256": digest,
        })
    return writes, entries, identities


def _runtime_digest(value: Any) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise StandaloneImproveError("Until Loop data is not JSON-safe") from exc
    return _digest(raw)


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    _need(type(value) is int and value >= minimum, f"{label} must be an integer of at least {minimum}")
    return value


def _ephemeral_context(value: Any) -> dict[str, Any]:
    _need(isinstance(value, Mapping) and set(value) == _CONTEXT_FIELDS,
          "Until Loop terminal context has an invalid schema")
    resources = value.get("resources")
    _need(isinstance(resources, list), "Until Loop terminal context.resources must be a list")
    copied: dict[str, Any] = {
        "request": _text(value.get("request"), "Until Loop terminal context.request"),
        "scope": _text(value.get("scope"), "Until Loop terminal context.scope"),
        "authority": _text(value.get("authority"), "Until Loop terminal context.authority"),
        "environment": _text(value.get("environment"), "Until Loop terminal context.environment"),
        "resources": [],
    }
    for index, resource in enumerate(resources):
        _need(isinstance(resource, Mapping) and set(resource) == _RESOURCE_FIELDS,
              f"Until Loop terminal context.resources[{index}] has an invalid schema")
        copied["resources"].append({
            "purpose": _text(resource.get("purpose"), f"Until Loop terminal context.resources[{index}].purpose"),
            "locator": _text(resource.get("locator"), f"Until Loop terminal context.resources[{index}].locator"),
        })
    return copied


def _ephemeral_report(value: Any) -> dict[str, str]:
    _need(isinstance(value, Mapping) and set(value) == _REPORT_FIELDS,
          "Until Loop terminal last_report has an invalid schema")
    classification = value.get("classification")
    exit_assessment = value.get("exit_assessment")
    continuation = value.get("continuation_assessment")
    _need(classification in {"trivial", "non-trivial", "unresolved"},
          "Until Loop terminal report classification is invalid")
    _need(exit_assessment in {"satisfied", "unsatisfied", "unknown"},
          "Until Loop terminal report exit assessment is invalid")
    _need(continuation in {"allowed", "blocked", "cancelled"},
          "Until Loop terminal report continuation assessment is invalid")
    return {
        "classification": classification,
        "exit_assessment": exit_assessment,
        "continuation_assessment": continuation,
        "evidence": _text(value.get("evidence"), "Until Loop terminal report evidence"),
        "handoff": _text(value.get("handoff"), "Until Loop terminal report handoff"),
    }


def _ephemeral_stopped_report(value: Any) -> dict[str, str]:
    """Validate a stopped report without changing success-import validation."""
    _need(isinstance(value, Mapping) and set(value) == _REPORT_FIELDS,
          "Until Loop stopped last_report has an invalid schema")
    classification = value.get("classification")
    exit_assessment = value.get("exit_assessment")
    continuation = value.get("continuation_assessment")
    _need(isinstance(classification, str) and classification in {"trivial", "non-trivial", "unresolved"},
          "Until Loop stopped report classification is invalid")
    _need(isinstance(exit_assessment, str) and exit_assessment in {"satisfied", "unsatisfied", "unknown"},
          "Until Loop stopped report exit assessment is invalid")
    _need(isinstance(continuation, str) and continuation in {"allowed", "blocked", "cancelled"},
          "Until Loop stopped report continuation assessment is invalid")
    return {
        "classification": classification,
        "exit_assessment": exit_assessment,
        "continuation_assessment": continuation,
        "evidence": _text(value.get("evidence"), "Until Loop stopped report evidence"),
        "handoff": _text(value.get("handoff"), "Until Loop stopped report handoff"),
    }


def _terminal_state_absent(value: Any) -> str:
    """Require a terminal ephemeral state path to be absent without trusting it."""
    state_file = _text(value, "Until Loop terminal state_file")
    path = Path(state_file)
    _need(path.is_absolute(), "Until Loop terminal state_file must be absolute")
    try:
        path.lstat()
    except FileNotFoundError:
        return state_file
    except (OSError, RuntimeError) as exc:
        raise StandaloneImproveError(
            "Until Loop terminal state_file cannot be checked for absence"
        ) from exc
    raise StandaloneImproveError("Until Loop terminal state_file remains present")


def _ephemeral_terminal_packet(
    packet: Mapping[str, Any], *, workspace: Path, binding_id: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    """Validate the exact complete packet saved by the bound ephemeral runtime."""
    _need(isinstance(packet, Mapping) and set(packet) == _TERMINAL_PACKET_FIELDS,
          "Until Loop terminal packet has an unsupported schema")
    _need(packet.get("status") == "complete", "Until Loop terminal packet is not complete")
    state_file = _text(packet.get("state_file"), "Until Loop terminal state_file")
    _need(Path(state_file).is_absolute(), "Until Loop terminal state_file must be absolute")
    packet_workspace = _workspace(packet.get("workspace"), "Until Loop terminal workspace")
    _need(packet_workspace == workspace, "Until Loop terminal packet is bound to another workspace")
    _text(packet.get("work"), "Until Loop terminal work")
    conditions = packet.get("conditions")
    _need(isinstance(conditions, Mapping) and set(conditions) == {"exit", "repeat"},
          "Until Loop terminal conditions have an invalid schema")
    _text(conditions.get("exit"), "Until Loop terminal exit condition")
    _text(conditions.get("repeat"), "Until Loop terminal repeat condition")
    progress = packet.get("progress")
    _need(isinstance(progress, Mapping) and set(progress) in ({
        "action_number", "trivial_streak", "required_trivial_reviews",
    }, {"action_number", "trivial_streak", "required_trivial_reviews", "unchanged_first_pass"}),
        "Until Loop terminal progress has an invalid schema")
    unchanged_first_pass = progress.get("unchanged_first_pass", False)
    _need(isinstance(unchanged_first_pass, bool), "Until Loop terminal unchanged_first_pass must be a boolean")
    action_number = _integer(progress.get("action_number"), "Until Loop terminal action number", minimum=1)
    trivial_streak = _integer(progress.get("trivial_streak"), "Until Loop terminal trivial streak")
    required_reviews = _integer(
        progress.get("required_trivial_reviews"), "Until Loop terminal required trivial reviews"
    )
    _need(required_reviews >= 2,
          "Until Loop terminal packet does not meet Improve's two-review minimum")
    # The runtime closes on one trivial pass only when it saw the workspace unchanged (Git tree).
    _need(trivial_streak >= required_reviews
          or (unchanged_first_pass and trivial_streak == 1 and action_number == 1),
          "Until Loop terminal packet does not meet its required trivial-review gate")
    _need(trivial_streak <= action_number,
          "Until Loop terminal progress has an incoherent trivial streak")
    context = _ephemeral_context(packet.get("context"))
    _need(_marked_request_binding_id(context["request"], "Until Loop terminal context") == binding_id,
          "Until Loop terminal context is not bound to this ShipLoop action")
    semantics = packet.get("status_semantics")
    _need(isinstance(semantics, Mapping) and set(semantics) == {
        "active", "complete", "stopped", "error",
    }, "Until Loop terminal status semantics have an invalid schema")
    for status, description in semantics.items():
        _text(status, "Until Loop terminal status semantics key")
        _text(description, "Until Loop terminal status semantics value")
    report = _ephemeral_report(packet.get("last_report"))
    _need(report["classification"] == "trivial" and report["exit_assessment"] == "satisfied",
          "Until Loop terminal report is not a satisfied trivial review")
    _need(report["continuation_assessment"] != "cancelled",
          "Until Loop terminal report was cancelled")
    _text(packet.get("instruction"), "Until Loop terminal instruction")
    _need(packet.get("next_argv") is None and packet.get("done_argv") is None
          and packet.get("report_schema") is None,
          "Until Loop terminal packet still exposes a callback")
    return _copy(dict(packet), "Until Loop terminal packet"), context, report


def _ephemeral_stopped_packet(
    packet: Mapping[str, Any], *, workspace: Path, binding_id: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    """Validate the exact stopped packet saved by the bound ephemeral runtime."""
    _need(isinstance(packet, Mapping) and set(packet) == _TERMINAL_PACKET_FIELDS,
          "Until Loop stopped packet has an unsupported schema")
    _need(packet.get("status") == "stopped", "Until Loop stopped packet is not stopped")
    _terminal_state_absent(packet.get("state_file"))
    packet_workspace = _workspace(packet.get("workspace"), "Until Loop stopped workspace")
    _need(packet_workspace == workspace, "Until Loop stopped packet is bound to another workspace")
    _text(packet.get("work"), "Until Loop stopped work")
    conditions = packet.get("conditions")
    _need(isinstance(conditions, Mapping) and set(conditions) == {"exit", "repeat"},
          "Until Loop stopped conditions have an invalid schema")
    _text(conditions.get("exit"), "Until Loop stopped exit condition")
    _text(conditions.get("repeat"), "Until Loop stopped repeat condition")
    progress = packet.get("progress")
    _need(isinstance(progress, Mapping) and set(progress) == {
        "action_number", "trivial_streak", "required_trivial_reviews",
    }, "Until Loop stopped progress has an invalid schema")
    action_number = _integer(progress.get("action_number"), "Until Loop stopped action number", minimum=1)
    trivial_streak = _integer(progress.get("trivial_streak"), "Until Loop stopped trivial streak")
    _integer(progress.get("required_trivial_reviews"), "Until Loop stopped required trivial reviews")
    _need(trivial_streak <= action_number,
          "Until Loop stopped progress has an incoherent trivial streak")
    context = _ephemeral_context(packet.get("context"))
    _need(_marked_request_binding_id(context["request"], "Until Loop stopped context") == binding_id,
          "Until Loop stopped context is not bound to this ShipLoop action")
    semantics = packet.get("status_semantics")
    _need(isinstance(semantics, Mapping) and set(semantics) == {
        "active", "complete", "stopped", "error",
    }, "Until Loop stopped status semantics have an invalid schema")
    for status, description in semantics.items():
        _text(status, "Until Loop stopped status semantics key")
        _text(description, "Until Loop stopped status semantics value")
    report = _ephemeral_stopped_report(packet.get("last_report"))
    _need(report["classification"] in {"non-trivial", "unresolved"},
          "Until Loop stopped report is not incomplete")
    _need(report["exit_assessment"] in {"unsatisfied", "unknown"},
          "Until Loop stopped report has an invalid exit assessment")
    _need(report["continuation_assessment"] == "cancelled",
          "Until Loop stopped report was not cancelled")
    _text(packet.get("instruction"), "Until Loop stopped instruction")
    _need(packet.get("next_argv") is None and packet.get("done_argv") is None
          and packet.get("report_schema") is None,
          "Until Loop stopped packet still exposes a callback")
    return _copy(dict(packet), "Until Loop stopped packet"), context, report


def _complete_ephemeral(
    binding: Mapping[str, Any], receipt: Mapping[str, Any], *, action: str,
    binding_id: str, workspace: Path, workspace_value: str, resolved: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Import a host-preserved terminal packet from the ephemeral runtime.

    The packet proves only that the host saved a structurally valid terminal
    response.  Its report fields remain agent declarations; this bridge does
    not treat a deleted tempfile as completion or independently prove review
    semantics, checks, candidate scope, or future freshness.
    """
    packet_relative = _receipt_relative(binding_id, action)
    packet_raw = _read_workspace(workspace, packet_relative, "Until Loop terminal packet")
    packet, context, report = _ephemeral_terminal_packet(
        _json(packet_raw, "Until Loop terminal packet"), workspace=workspace, binding_id=binding_id,
    )
    checked_receipt = _receipt(receipt, workspace, workspace_value)
    single = bool(packet["progress"].get("unchanged_first_pass"))
    _need(len(checked_receipt["review_refs"]) == (1 if single else 2),
          "Improve receipt lists " + str(len(checked_receipt["review_refs"])) + " review references; this run "
          + ("ended on one unchanged trivial pass, so list that one review"
             if single else "needs the two trivial-streak reviews"))
    evidence_digests = _reference_digests(workspace, checked_receipt)
    prefix = f"improve/{action}"
    archive: dict[str, str] = {
        f"{prefix}/terminal.json": _utf8(packet_raw, "Until Loop terminal packet"),
    }
    evidence_writes, evidence_entries = _evidence_archives(workspace, action, checked_receipt)
    archive.update(evidence_writes)
    record = {
        "version": VERSION,
        "binding_id": binding_id,
        "workspace": str(workspace),
        "action_id": action,
        "stage": binding["stage"],
        "skill": dict(resolved),
        "runtime_phase": "complete",
        "identities": {
            "terminal_packet_sha256": _digest(packet_raw),
            "context_sha256": _runtime_digest(context),
            "last_report_sha256": _runtime_digest(report),
            "evidence_sha256": evidence_digests,
        },
        "evidence": evidence_entries,
        "receipt": checked_receipt,
        "stale_check_note": (
            "This import records a host-preserved structurally valid terminal Until Loop packet "
            "and current declared local evidence. It does not prove the packet was issued by the "
            "runtime, review or check claims, candidate scope, semantic Improve convergence, or "
            "future freshness; those remain the selected Improve skill and parent action's responsibility."
        ),
    }
    archive[f"{prefix}/receipt.md"] = store.dumps(record, "ShipLoop standalone Improve receipt")
    return record, archive


def _settle_incomplete_ephemeral(
    binding: Mapping[str, Any], receipt: Mapping[str, Any], *, action: str,
    binding_id: str, workspace: Path, workspace_value: str, resolved: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Import one host-preserved stopped packet for an incomplete plan reconciliation."""
    packet_relative = _receipt_relative(binding_id, action)
    packet_raw = _read_workspace(workspace, packet_relative, "Until Loop stopped packet")
    packet, context, report = _ephemeral_stopped_packet(
        _json(packet_raw, "Until Loop stopped packet"), workspace=workspace, binding_id=binding_id,
    )
    checked_receipt = _incomplete_receipt(receipt, workspace, workspace_value)
    submission = _copy(dict(receipt), "incomplete Improve receipt submission")
    prefix = f"improve/{action}"
    archive: dict[str, str] = {
        f"{prefix}/terminal.json": _utf8(packet_raw, "Until Loop stopped packet"),
    }
    evidence_writes, evidence_entries, evidence_digests = _incomplete_evidence_snapshot(
        workspace, action, checked_receipt,
    )
    archive.update(evidence_writes)
    record = {
        "version": VERSION,
        "binding_id": binding_id,
        "workspace": str(workspace),
        "action_id": action,
        "stage": binding["stage"],
        "seed_result": _copy(binding["seed_result"], "pending result"),
        "skill": dict(resolved),
        "runtime_phase": "stopped",
        "identities": {
            "terminal_packet_sha256": _digest(packet_raw),
            "context_sha256": _runtime_digest(context),
            "last_report_sha256": _runtime_digest(report),
            "evidence_sha256": evidence_digests,
        },
        "evidence": evidence_entries,
        "submission": submission,
        "receipt": checked_receipt,
        "stale_check_note": (
            "This import records a host-preserved structurally valid stopped Until Loop packet, "
            "the observed absence of the packet-reported state_file path, and current declared "
            "local evidence. That missing path does not authenticate the selected worker's death. "
            "This import does not prove the packet was issued by the runtime, establish review "
            "claims, candidate scope, semantic Improve convergence, or future freshness. "
            "The parent must collect or cancel the actual worker before this settlement."
        ),
    }
    archive[f"{prefix}/receipt.md"] = store.dumps(record, "ShipLoop standalone Improve receipt")
    return record, archive


def complete(binding: Mapping[str, Any], receipt: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Validate an actual terminal child and return immutable parent archive writes.

    The ephemeral child must have its final raw packet preserved by the host.
    This pure reader never replays callbacks, creates a replacement run, or
    infers completion from a missing child state file.
    """
    action, binding_id, workspace, workspace_value = _binding_identity(binding)
    skill = binding["skill"]
    resolved = resolve_skill(_text(skill.get("skill_card"), "bound skill card"))
    _need(resolved == dict(skill), "bound Improve runtime differs from selected card")
    return _complete_ephemeral(
        binding, receipt, action=action, binding_id=binding_id, workspace=workspace,
        workspace_value=workspace_value, resolved=resolved,
    )


def settle_incomplete(
    binding: Mapping[str, Any], receipt: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Archive a stopped selected ephemeral plan child without importing success.

    The caller must first collect or cancel the actual child worker. A preserved
    packet can establish only the stopped runtime declaration and the observed
    absence of its private state file; it cannot authenticate worker death.
    """
    action, binding_id, workspace, workspace_value = _binding_identity(binding)
    skill = binding["skill"]
    resolved = resolve_skill(_text(skill.get("skill_card"), "bound skill card"))
    _need(resolved == dict(skill), "bound Improve runtime differs from selected card")
    _need(binding.get("stage") == "plan",
          "stopped settlement is only available for the bound plan Improve child")
    return _settle_incomplete_ephemeral(
        binding, receipt, action=action, binding_id=binding_id, workspace=workspace,
        workspace_value=workspace_value, resolved=resolved,
    )
