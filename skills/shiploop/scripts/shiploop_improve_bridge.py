#!/usr/bin/env python3
"""Markdown bridge for a managed Improve child owned by ShipLoop.

The bridge deliberately owns storage composition, not improvement judgement. A
new-run ShipLoop state may park its public cursor at ``managed-improve`` while
one namespaced child record carries the concrete typed execution cursor. The
bundled ``_improve_managed`` controller owns phase routing and convergence; this
module only projects that cursor into existing ShipLoop validators and
atomically imports a controller certificate.

All writes are returned to the caller. ``shiploop_protocol.persist`` supplies
them to the one existing :func:`shiploop_store.transaction` call, so a parent
cursor and child receipt never become independently durable.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import stat
import uuid
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

import shiploop_store as store


VERSION = 1
CONTROLLER_VERSION = "improve-managed-controller/v1"
MARKER = "managed_improve_protocol_version"
STATE_KEY = "managed_improve"
PRIVATE_KEY = "_managed_improve_projection"
EVIDENCE_KEY = "_managed_evidence"
STAGE = "managed-improve"
DIRECTORY = "managed-improve"
CHILD_TITLE = "ShipLoop managed Improve child"
CERTIFICATE_TITLE = "ShipLoop managed Improve certificate"
IMPORT_KEY = "managed_improve_import"
RECOVERY_KEY = "managed_improve_recovery"
PIN_PATH = "references/improve-managed-controller-pin.json"
CONTRACT_PATH = "improve-managed-contract.md"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_ACTION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,160}$")
_CHILD_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{1,160}$")
_STATUSES = frozenset({"active", "converged", "blocked", "needs-prerequisite", "needs-replan", "stopped"})
_INCOMPLETE = frozenset({"blocked", "needs-prerequisite", "needs-replan", "stopped"})
_FIRST_PHASE_PROFILES = {
    "research-review": "research",
    "behavior-review": "behavior",
    "spec-review": "spec",
    "objective-review": "objective",
    "step-plan-review": "step-plan",
    "review": "product",
}
_CONTROL_KEYS = frozenset({
    "phase", "stage", "action", "completed_actions", MARKER, STATE_KEY,
    IMPORT_KEY, RECOVERY_KEY, "revision", "last_completion",
    PRIVATE_KEY, EVIDENCE_KEY,
})
_FORBIDDEN_PARENT_PATHS = frozenset({
    "state.md", "history.md", "transaction.md", "run.md", "prompt.md",
    "environment.md", "behavior.md", "spec.md", "lifecycle.md", "plan.md",
    "backchain/plan.md", "improve-policy.md", CONTRACT_PATH,
})
_PROFILE_CANDIDATE_WRITES = {
    "objective": frozenset({"environment.md"}),
    "behavior": frozenset({"behavior.md"}),
    "spec": frozenset({"spec.md", "lifecycle.md", "spec-draft.md", "lifecycle-draft.md"}),
}
_OBJECTIVE_SEQUENCE_WRITES = frozenset({"backchain/plan.md", "plan.md"})
_SAME_FAMILY_REPAIR_EVENTS = frozenset({
    "repair",
    "step-plan-repair",
    "planning-repair",
    "objective-repair-rebind",
    "objective-repair-outer-work-rebind",
})
_RECOVERY_EVIDENCE_PREFIXES = (
    "objectives/",
    "planning/",
    "planning-history/",
    "step-planning/",
    "steps/",
)
_PLANNING_REVISIT_CLEAR_FIELDS = frozenset({
    "spec_sha256",
    "lifecycle_sha256",
    "plan_sha256",
    "plan_wrapper_sha256",
    "behavior_sha256",
    "research_sha256",
    "research_certificate_sha256",
    "research_as_of",
    "environment_sha256",
    "bound_plan",
    "bound_plan_hash",
    "previous_planning",
    "planning_epoch",
    "objective_preallocation_bridge",
    "paused",
})
_PLANNING_REVISIT_PATHS = frozenset({
    "spec-draft.md",
    "lifecycle-draft.md",
    "spec.md",
    "lifecycle.md",
    "plan.md",
    "backchain/plan.md",
    "preparation.md",
    "behavior.md",
    "research.md",
    "research-evidence.md",
    "environment.md",
})
# A child owns its typed artifacts and its namespaced execution receipt.  These
# are the *only* ordinary parent-state facts that a validated child may carry
# over when its terminal certificate imports.  Keeping this list narrow makes
# a projected callback unable to replace parent configuration, repository
# identity, policy bindings, protocol versions, or the parent cursor.
_PROFILE_OVERLAY_KEYS = {
    "research": frozenset({
        "research_sha256", "research_certificate_sha256", "research_as_of",
    }),
    "behavior": frozenset({"behavior_sha256"}),
    "spec": frozenset({"spec_sha256", "lifecycle_sha256"}),
    "objective": frozenset({
        "objective", "environment_sha256", "plan_sha256", "plan_wrapper_sha256",
        "bound_plan", "bound_plan_hash", "system_test_protocol_version",
        "objective_preallocation_bridge", "outer_check_action",
    }),
    "step-plan": frozenset(),
    "product": frozenset({
        "knowledge_revision", "knowledge_sha256", "knowledge_action_id", "system_test_pending",
    }),
}
_PAUSE_OVERLAY_KEY = "paused"
_MAX_READ_BYTES = 4 * 1024 * 1024


class ManagedImproveBridgeError(ValueError):
    """A managed child is stale, corrupt, or cannot be safely imported."""


BridgeError = ManagedImproveBridgeError


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ManagedImproveBridgeError(message)


def _json_copy(value: Any, label: str) -> Any:
    try:
        return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ManagedImproveBridgeError(f"{label} is not JSON serializable") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _bytes_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_relative(relative: str, *, label: str) -> tuple[str, ...]:
    _need(isinstance(relative, str) and bool(relative), f"{label} must be a nonempty relative path")
    _need("\x00" not in relative and "\\" not in relative, f"unsafe {label}")
    candidate = Path(relative)
    _need(not candidate.is_absolute(), f"unsafe {label}")
    parts = candidate.parts
    _need(parts and all(part not in ("", ".", "..") for part in parts), f"unsafe {label}")
    return parts


def _root(root: Path | str) -> Path:
    try:
        resolved = Path(root).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ManagedImproveBridgeError(f"managed Improve root is unavailable: {root}") from exc
    _need(resolved.is_dir() and not resolved.is_symlink(), "managed Improve root must be a real directory")
    return resolved


def _safe_path(root: Path | str, relative: str, *, label: str) -> Path:
    base = _root(root)
    current = base
    for part in _safe_relative(relative, label=label):
        current = current / part
        if current.exists() or current.is_symlink():
            try:
                metadata = current.lstat()
            except OSError as exc:
                raise ManagedImproveBridgeError(f"cannot inspect {label}: {current}") from exc
            _need(not stat.S_ISLNK(metadata.st_mode), f"{label} cannot be a symlink")
    try:
        current.resolve(strict=False).relative_to(base)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ManagedImproveBridgeError(f"unsafe {label}") from exc
    return current


def _safe_read(root: Path | str, relative: str, *, label: str) -> bytes:
    path = _safe_path(root, relative, label=label)
    try:
        before = path.lstat()
        _need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, f"{label} must be a regular single-link file")
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            _need((before.st_dev, before.st_ino) == (opened.st_dev, opened.st_ino), f"{label} changed during read")
            data = handle.read(_MAX_READ_BYTES + 1)
    except ManagedImproveBridgeError:
        raise
    except OSError as exc:
        raise ManagedImproveBridgeError(f"cannot read {label}: {path}") from exc
    _need(len(data) <= _MAX_READ_BYTES, f"{label} exceeds {_MAX_READ_BYTES} bytes")
    return data


def _read_record(root: Path | str, relative: str, *, label: str) -> tuple[dict[str, Any], bytes]:
    raw = _safe_read(root, relative, label=label)
    try:
        value = store.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, store.StorageError) as exc:
        raise ManagedImproveBridgeError(f"{label} is not a valid Markdown state record") from exc
    _need(isinstance(value, dict), f"{label} must contain an object")
    return _json_copy(value, label), raw


def _bundled_read(relative: str, *, label: str) -> bytes:
    """Read one exact, regular file from the ShipLoop package tree."""
    package_root = Path(__file__).resolve().parent.parent
    _safe_relative(relative, label=label)
    path = package_root.joinpath(*Path(relative).parts)
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(package_root)
        metadata = path.lstat()
        _need(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1, f"{label} must be a regular single-link file")
        return path.read_bytes()
    except ManagedImproveBridgeError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise ManagedImproveBridgeError(f"cannot read bundled {label}") from exc


def _bundle_pin() -> dict[str, Any]:
    """Fail closed unless the vendored controller and consumer contract match its pin."""
    raw = _bundled_read(PIN_PATH, label="managed Improve controller pin")
    try:
        pin = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManagedImproveBridgeError("managed Improve controller pin is invalid") from exc
    required = {"version", "controller", "sha256", "source", "contract_source", "contract_path", "contract_sha256"}
    _need(isinstance(pin, dict) and set(pin) == required and pin.get("version") == VERSION, "managed Improve controller pin has an unsupported schema")
    _need(pin.get("controller") == CONTROLLER_VERSION, "managed Improve controller pin version is unsupported")
    _need(pin.get("source") == "skills/improve/scripts/managed_controller.py", "managed Improve controller pin source is invalid")
    _need(pin.get("contract_source") == "skills/improve/references/managed-consumer.md", "managed Improve contract pin source is invalid")
    _need(pin.get("contract_path") == "references/improve-managed-consumer.md", "managed Improve contract pin path is invalid")
    _require_sha(pin.get("sha256"), "managed Improve controller pin digest")
    _require_sha(pin.get("contract_sha256"), "managed Improve contract pin digest")
    controller_bytes = _bundled_read("scripts/_improve_managed.py", label="managed Improve controller source")
    contract_bytes = _bundled_read(pin["contract_path"], label="managed Improve consumer contract")
    _need(_bytes_digest(controller_bytes) == pin["sha256"], "managed Improve controller source differs from its pin")
    _need(_bytes_digest(contract_bytes) == pin["contract_sha256"], "managed Improve consumer contract differs from its pin")
    return _json_copy(pin, "managed Improve controller pin")


def _controller() -> Any:
    """Load only the vendored controller beside ShipLoop's scripts."""
    try:
        module = importlib.import_module("_improve_managed")
    except ImportError as exc:
        raise ManagedImproveBridgeError(
            "managed Improve controller is unavailable; restore the bundled _improve_managed module"
        ) from exc
    required = (
        "VERSION", "new_binding", "assert_binding", "new_child", "assert_child", "apply",
        "packet_metadata", "terminal_certificate", "assert_terminal_certificate",
        "resume",
    )
    for name in required:
        _need(callable(getattr(module, name, None)) or name == "VERSION", f"managed Improve controller lacks {name}")
    pin = _bundle_pin()
    _need(module.VERSION == pin["controller"] == CONTROLLER_VERSION, "unsupported managed Improve controller version")
    return module


def _executor_digest() -> str:
    module = _controller()
    raw_name = getattr(module, "__file__", None)
    _need(isinstance(raw_name, str) and raw_name, "managed Improve controller has no source file")
    expected = Path(__file__).resolve().with_name("_improve_managed.py")
    actual = Path(raw_name)
    try:
        actual_resolved = actual.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ManagedImproveBridgeError("managed Improve controller source is unavailable") from exc
    _need(actual_resolved == expected, "managed Improve controller is not the bundled source")
    try:
        metadata = actual.lstat()
        _need(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1, "managed Improve controller must be a regular single-link file")
        raw = actual.read_bytes()
    except ManagedImproveBridgeError:
        raise
    except OSError as exc:
        raise ManagedImproveBridgeError("cannot read managed Improve controller source") from exc
    return _bytes_digest(raw)


def _policy_digest(root: Path | str, state: Mapping[str, Any]) -> str:
    binding = state.get("improve_policy")
    _need(isinstance(binding, Mapping), "managed Improve requires a frozen Improve policy binding")
    expected = binding.get("sha256")
    _need(isinstance(expected, str) and _SHA256.fullmatch(expected), "managed Improve policy binding is invalid")
    actual = _bytes_digest(_safe_read(root, "improve-policy.md", label="frozen Improve policy"))
    _need(actual == expected, "frozen Improve policy digest changed; restore it before resuming")
    return expected


def _require_action(value: Any, label: str) -> str:
    _need(isinstance(value, str) and _ACTION.fullmatch(value), f"{label} is invalid")
    return value


def _require_sha(value: Any, label: str) -> str:
    _need(isinstance(value, str) and _SHA256.fullmatch(value), f"{label} is invalid")
    return value


def _child_path(child_id: str) -> str:
    _need(isinstance(child_id, str) and _CHILD_ID.fullmatch(child_id), "managed Improve child ID is unsafe")
    return f"{DIRECTORY}/{child_id}.md"


def _certificate_path(child_id: str) -> str:
    _need(isinstance(child_id, str) and _CHILD_ID.fullmatch(child_id), "managed Improve child ID is unsafe")
    return f"{DIRECTORY}/{child_id}-certificate.md"


def _requirements_from_state(
    root: Path | str, state: Mapping[str, Any], *, profile: str | None = None
) -> list[dict[str, str]]:
    pairs = (
        ("environment_sha256", "environment.md"), ("behavior_sha256", "behavior.md"),
        ("spec_sha256", "spec.md"), ("lifecycle_sha256", "lifecycle.md"),
        ("plan_sha256", "backchain/plan.md"),
        ("managed_improve_contract_sha256", CONTRACT_PATH),
    )
    mutable = {
        "behavior": {"behavior.md"},
        # A specification review is permitted to replace its candidate. Its
        # sibling lifecycle draft is also an output when the profile owns it.
        "spec": {"spec.md", "lifecycle.md"},
        # Generic objective work may own an environment/survey candidate.
        "objective": {"environment.md"},
    }.get(profile, set())
    values: list[dict[str, str]] = []
    has_domain_requirement = False
    for key, path in pairs:
        if path in mutable:
            continue
        expected = state.get(key)
        if path == CONTRACT_PATH:
            _need(expected not in (None, ""), "managed Improve requires a frozen managed consumer contract")
        if expected in (None, ""):
            continue
        expected = _require_sha(expected, key)
        actual = _bytes_digest(_safe_read(root, path, label=f"frozen requirement {path}"))
        _need(actual == expected, f"frozen requirement {path} digest changed")
        values.append({"path": path, "sha256": expected})
        has_domain_requirement = has_domain_requirement or path != CONTRACT_PATH
    # The earliest generic objective can begin before survey/spec artifacts
    # exist. Its durable prompt is still an immutable run requirement and
    # avoids fabricating an absent specification merely to start the child.
    if not has_domain_requirement:
        prompt = _safe_path(root, "prompt.md", label="frozen initial prompt")
        _need(prompt.is_file(), "managed Improve needs frozen requirements or the durable initial prompt")
        values.append(
            {
                "path": "prompt.md",
                "sha256": _bytes_digest(_safe_read(root, "prompt.md", label="frozen initial prompt")),
            }
        )
    _need(values, "managed Improve needs at least one frozen requirement artifact")
    return values


def _scope_inventory(root: Path | str, state: Mapping[str, Any]) -> dict[str, Any]:
    scope: dict[str, Any] = {"run_id": state.get("run_id"), "active_step": state.get("active_step")}
    active_step = state.get("active_step")
    if isinstance(active_step, str) and re.fullmatch(r"[SD][0-9]+", active_step):
        relative = f"steps/{active_step}.md"
        if _safe_path(root, relative, label="active step receipt").is_file():
            scope["active_step_receipt_sha256"] = _bytes_digest(_safe_read(root, relative, label="active step receipt"))
    return scope


def _validate_live_scope(
    root: Path | str, parent: Mapping[str, Any], input_value: Mapping[str, Any]
) -> None:
    """Keep stable run/step ownership bound without freezing mutable candidate bytes."""
    scope = input_value.get("scope")
    candidate = input_value.get("candidate")
    _need(isinstance(scope, Mapping) and isinstance(candidate, Mapping), "managed Improve input scope is invalid")
    _need(scope.get("run_id") == parent.get("run_id"), "managed Improve run scope changed")
    active_step = scope.get("active_step")
    _need(active_step == parent.get("active_step"), "managed Improve active step scope changed")
    if active_step is None:
        _need(not candidate, "managed Improve candidate exists outside the active step scope")
        return
    _need(isinstance(active_step, str) and re.fullmatch(r"[SD][0-9]+", active_step), "managed Improve active step scope is invalid")
    _need(candidate.get("step_id") == active_step, "managed Improve candidate step differs from active scope")
    relative = f"steps/{active_step}.md"
    receipt, _raw = _read_record(root, relative, label="managed Improve live candidate receipt")
    if "id" in receipt:
        _need(receipt.get("id") == active_step, "managed Improve live candidate step definition changed")
    for key in ("worktree", "base_sha"):
        _need(
            receipt.get(key) == candidate.get(key),
            f"managed Improve live candidate {key} changed",
        )


def _validate_imported_run_scope(
    parent: Mapping[str, Any], input_value: Mapping[str, Any]
) -> None:
    """Keep the immutable run binding after its child has released the step."""
    scope = input_value.get("scope")
    _need(isinstance(scope, Mapping), "managed Improve input scope is invalid")
    _need(scope.get("run_id") == parent.get("run_id"), "managed Improve run scope changed")


def input_identity(
    root: Path | str,
    state: Mapping[str, Any],
    *,
    profile: str | None = None,
    scope_inventory: Mapping[str, Any] | None = None,
    recovery_writes: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Snapshot immutable requirements separately from mutable candidate/audit facts."""
    requirements = _requirements_from_state(root, state, profile=profile)
    scope = _json_copy(scope_inventory if scope_inventory is not None else _scope_inventory(root, state), "scope inventory")
    _need(isinstance(scope, dict) and scope, "managed Improve scope inventory is invalid")
    candidate: dict[str, Any] = {}
    audit: dict[str, Any] = {}
    active_step = state.get("active_step")
    if isinstance(active_step, str) and re.fullmatch(r"[SD][0-9]+", active_step):
        relative = f"steps/{active_step}.md"
        if _safe_path(root, relative, label="candidate step receipt").is_file():
            receipt, raw = _read_record(root, relative, label="candidate step receipt")
            candidate = {"step_id": active_step, "initial_receipt_sha256": _bytes_digest(raw), "worktree": receipt.get("worktree"), "base_sha": receipt.get("base_sha")}
            if isinstance(receipt.get("base_sha"), str) and _GIT_SHA.fullmatch(receipt["base_sha"]):
                audit["initial_head"] = receipt["base_sha"]
    return {
        "version": VERSION,
        "requirements": requirements,
        "scope": scope,
        "candidate": candidate,
        "audit": audit,
        "recovery": _recovery_input_identity(root, state, recovery_writes),
    }


def _validate_input_identity(
    root: Path | str, value: Any, writes: Mapping[str, str] | None = None
) -> dict[str, Any]:
    _need(isinstance(value, Mapping), "managed Improve input identity must be an object")
    expected = {"version", "requirements", "scope", "candidate", "audit", "recovery"}
    _need(set(value) == expected and value.get("version") == VERSION, "managed Improve input identity has an unsupported schema")
    requirements = value.get("requirements")
    _need(isinstance(requirements, list) and requirements, "managed Improve input identity has no requirements")
    seen: set[str] = set()
    normalized: list[dict[str, str]] = []
    for row in requirements:
        _need(isinstance(row, Mapping) and set(row) == {"path", "sha256"}, "managed Improve requirement identity is invalid")
        path = row.get("path")
        _safe_relative(path, label="managed Improve requirement path")
        _need(path not in seen, "managed Improve requirement identity repeats a path")
        seen.add(path)
        digest = _require_sha(row.get("sha256"), f"managed Improve requirement {path} digest")
        actual = _bytes_digest(_safe_read(root, path, label=f"frozen requirement {path}"))
        _need(actual == digest, f"frozen requirement {path} digest changed")
        normalized.append({"path": path, "sha256": digest})
    scope = _json_copy(value.get("scope"), "managed Improve scope inventory")
    candidate = _json_copy(value.get("candidate"), "managed Improve candidate identity")
    audit = _json_copy(value.get("audit"), "managed Improve audit identity")
    _need(isinstance(scope, dict) and scope, "managed Improve scope inventory is invalid")
    _need(isinstance(candidate, dict), "managed Improve candidate identity is invalid")
    _need(isinstance(audit, dict), "managed Improve audit identity is invalid")
    recovery = _validate_recovery_input_identity(root, value.get("recovery"), writes)
    return {
        "version": VERSION,
        "requirements": normalized,
        "scope": scope,
        "candidate": candidate,
        "audit": audit,
        "recovery": recovery,
    }


def enabled(state: Mapping[str, Any]) -> bool:
    """Return whether this is a new-run managed-mode state."""
    return state.get(MARKER) == VERSION


def initialize(state: MutableMapping[str, Any]) -> None:
    """Mark a newly initialized run for managed ownership; never upgrade legacy."""
    prior = state.get(MARKER)
    _need(prior in (None, VERSION), "unsupported managed Improve protocol version")
    state[MARKER] = VERSION


def _binding_summary(binding: Mapping[str, Any], *, child_id: str, receipt: str, input_value: Mapping[str, Any]) -> dict[str, Any]:
    controller = _controller()
    checked = controller.assert_binding(_json_copy(binding, "managed Improve binding"))
    _need(isinstance(checked, Mapping), "managed Improve controller returned an invalid binding")
    result = {
        "version": VERSION, "id": child_id, "receipt": receipt,
        "parent_action": _require_action(checked.get("parent_action"), "managed Improve parent action"),
        "profile": checked.get("profile"),
        "binding_sha256": _require_sha(checked.get("binding_sha256"), "managed Improve binding digest"),
        "input_sha256": _digest(input_value),
        "policy_digest": _require_sha(checked.get("policy_digest"), "managed Improve policy digest"),
        "executor_digest": _require_sha(checked.get("executor_digest"), "managed Improve executor digest"),
        "scope_inventory_sha256": _digest(input_value["scope"]), "status": "active",
    }
    _need(isinstance(result["profile"], str) and result["profile"], "managed Improve profile is invalid")
    return result


def _validate_recovery_metadata(value: Any) -> dict[str, Any]:
    """Validate the bounded handoff left by an interrupted cross-profile child."""
    _need(isinstance(value, Mapping), "managed Improve recovery handoff is invalid")
    required = {
        "from_child", "from_parent_action", "status", "reason", "evidence_refs", "to_child",
    }
    _need(set(value) == required, "managed Improve recovery handoff has an unsupported schema")
    from_child = value.get("from_child")
    _need(isinstance(from_child, str) and _CHILD_ID.fullmatch(from_child), "managed Improve recovery source child is invalid")
    from_parent_action = _require_action(value.get("from_parent_action"), "managed Improve recovery source parent action")
    _need(value.get("status") == "needs-replan", "managed Improve recovery status is invalid")
    reason = value.get("reason")
    _need(isinstance(reason, str) and reason.strip() and "\x00" not in reason, "managed Improve recovery reason is invalid")
    refs = value.get("evidence_refs")
    _need(isinstance(refs, list) and refs and all(isinstance(item, str) for item in refs), "managed Improve recovery evidence references are invalid")
    _need(len(set(refs)) == len(refs), "managed Improve recovery evidence references repeat")
    for relative in refs:
        _safe_relative(relative, label="managed Improve recovery evidence reference")
        _need(relative.startswith(f"{DIRECTORY}/"), "managed Improve recovery evidence is not bridge-owned")
    to_child = value.get("to_child")
    _need(to_child is None or (isinstance(to_child, str) and _CHILD_ID.fullmatch(to_child)), "managed Improve recovery destination child is invalid")
    return {
        "from_child": from_child,
        "from_parent_action": from_parent_action,
        "status": "needs-replan",
        "reason": reason,
        "evidence_refs": list(refs),
        "to_child": to_child,
    }


def _recovery_identity_payload(
    *,
    from_child: str,
    from_parent_action: str,
    status: str,
    reason_sha256: str,
    source_receipt_sha256: str,
    evidence: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    return {
        "from_child": from_child,
        "from_parent_action": from_parent_action,
        "status": status,
        "reason_sha256": reason_sha256,
        "source_receipt_sha256": source_receipt_sha256,
        "evidence": [dict(row) for row in evidence],
    }


def _read_bytes_or_written(
    root: Path | str, relative: str, writes: Mapping[str, str] | None, *, label: str
) -> bytes:
    _safe_relative(relative, label=label)
    if writes is not None and relative in writes:
        body = writes[relative]
        _need(isinstance(body, str), f"{label} staged write is invalid")
        return body.encode("utf-8")
    return _safe_read(root, relative, label=label)


def _read_record_or_written(
    root: Path | str, relative: str, writes: Mapping[str, str] | None, *, label: str
) -> tuple[dict[str, Any], bytes]:
    if writes is not None and relative in writes:
        raw = _read_bytes_or_written(root, relative, writes, label=label)
        try:
            value = store.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, store.StorageError) as exc:
            raise ManagedImproveBridgeError(f"{label} staged record is invalid") from exc
        _need(isinstance(value, dict), f"{label} staged record is invalid")
        return value, raw
    return _read_record(root, relative, label=label)


def _normalize_recovery_input_identity(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    _need(isinstance(value, Mapping), "managed Improve recovery input is invalid")
    required = {
        "from_child", "from_parent_action", "status", "reason_sha256",
        "source_receipt_sha256", "evidence", "recovery_sha256",
    }
    _need(set(value) == required, "managed Improve recovery input has an unsupported schema")
    from_child = value.get("from_child")
    _need(isinstance(from_child, str) and _CHILD_ID.fullmatch(from_child), "managed Improve recovery input child is invalid")
    from_parent_action = _require_action(value.get("from_parent_action"), "managed Improve recovery input parent action")
    _need(value.get("status") == "needs-replan", "managed Improve recovery input status is invalid")
    reason_sha256 = _require_sha(value.get("reason_sha256"), "managed Improve recovery input reason digest")
    source_receipt_sha256 = _require_sha(value.get("source_receipt_sha256"), "managed Improve recovery input receipt digest")
    raw_evidence = value.get("evidence")
    _need(isinstance(raw_evidence, list) and raw_evidence, "managed Improve recovery input evidence is invalid")
    evidence: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in raw_evidence:
        _need(isinstance(row, Mapping) and set(row) == {"path", "sha256"}, "managed Improve recovery input evidence row is invalid")
        relative = row.get("path")
        _safe_relative(relative, label="managed Improve recovery input evidence path")
        _need(relative.startswith(f"{DIRECTORY}/") and relative not in seen, "managed Improve recovery input evidence path is invalid")
        seen.add(relative)
        evidence.append({"path": relative, "sha256": _require_sha(row.get("sha256"), "managed Improve recovery input evidence digest")})
    payload = _recovery_identity_payload(
        from_child=from_child,
        from_parent_action=from_parent_action,
        status="needs-replan",
        reason_sha256=reason_sha256,
        source_receipt_sha256=source_receipt_sha256,
        evidence=evidence,
    )
    _need(value.get("recovery_sha256") == _digest(payload), "managed Improve recovery input digest differs")
    return {**payload, "recovery_sha256": value["recovery_sha256"]}


def _validate_recovery_source(
    root: Path | str,
    *,
    from_child: str,
    from_parent_action: str,
    source_receipt_sha256: str,
    evidence: Sequence[Mapping[str, str]],
    writes: Mapping[str, str] | None = None,
) -> None:
    """Validate the abandoned source child without requiring live requirements."""
    relative = _child_path(from_child)
    record, raw = _read_record_or_written(
        root, relative, writes, label="managed Improve recovery source receipt"
    )
    _need(_bytes_digest(raw) == source_receipt_sha256, "managed Improve recovery source receipt changed")
    _need(isinstance(record.get("binding"), Mapping) and isinstance(record.get("child"), Mapping), "managed Improve recovery source receipt is invalid")
    controller = _controller()
    binding = controller.assert_binding(record["binding"])
    child = controller.assert_child(record["child"])
    _need(binding.get("parent_action") == from_parent_action, "managed Improve recovery source parent action differs")
    _need(child.get("binding") == binding and child.get("status") == "needs-replan", "managed Improve recovery source child is not an abandoned replan")
    phase_records = child.get("phase_records")
    _need(isinstance(phase_records, list) and phase_records and isinstance(phase_records[-1], Mapping), "managed Improve recovery source has no interruption")
    last = phase_records[-1]
    refs = last.get("evidence_refs")
    expected_refs = [row["path"] for row in evidence]
    _need(last.get("kind") == "needs-replan" and refs == expected_refs, "managed Improve recovery source evidence differs")
    _validate_phase_evidence(root, child, record.get("evidence_digests"), {} if writes is None else writes)


def _recovery_input_identity(
    root: Path | str, state: Mapping[str, Any], writes: Mapping[str, str] | None = None
) -> dict[str, Any] | None:
    recovery = state.get(RECOVERY_KEY)
    if recovery is None:
        return None
    handoff = _validate_recovery_metadata(recovery)
    # The first child begun after an abandonment is the sole successor allowed
    # to consume this handoff.  Once begin() assigns ``to_child``, later
    # unrelated bindings deliberately exclude it.
    if handoff["to_child"] is not None:
        return None
    relative = _child_path(handoff["from_child"])
    _record, raw = _read_record_or_written(
        root, relative, writes, label="managed Improve recovery source receipt"
    )
    evidence = [
        {
            "path": path,
            "sha256": _bytes_digest(
                _read_bytes_or_written(root, path, writes, label="managed Improve recovery evidence")
            ),
        }
        for path in handoff["evidence_refs"]
    ]
    payload = _recovery_identity_payload(
        from_child=handoff["from_child"],
        from_parent_action=handoff["from_parent_action"],
        status=handoff["status"],
        reason_sha256=_bytes_digest(handoff["reason"].encode("utf-8")),
        source_receipt_sha256=_bytes_digest(raw),
        evidence=evidence,
    )
    _validate_recovery_source(
        root,
        from_child=payload["from_child"],
        from_parent_action=payload["from_parent_action"],
        source_receipt_sha256=payload["source_receipt_sha256"],
        evidence=payload["evidence"],
        writes=writes,
    )
    return {**payload, "recovery_sha256": _digest(payload)}


def _validate_recovery_input_identity(
    root: Path | str, value: Any, writes: Mapping[str, str] | None = None
) -> dict[str, Any] | None:
    normalized = _normalize_recovery_input_identity(value)
    if normalized is None:
        return None
    evidence = normalized["evidence"]
    for row in evidence:
        actual = _bytes_digest(
            _read_bytes_or_written(root, row["path"], writes, label="managed Improve recovery evidence")
        )
        _need(actual == row["sha256"], "managed Improve recovery evidence changed")
    _validate_recovery_source(
        root,
        from_child=normalized["from_child"],
        from_parent_action=normalized["from_parent_action"],
        source_receipt_sha256=normalized["source_receipt_sha256"],
        evidence=evidence,
        writes=writes,
    )
    return normalized


def _recovery_input_matches_handoff(
    input_recovery: Any, handoff: Mapping[str, Any]
) -> bool:
    normalized = _normalize_recovery_input_identity(input_recovery)
    current = _validate_recovery_metadata(handoff)
    return (
        normalized is not None
        and normalized["from_child"] == current["from_child"]
        and normalized["from_parent_action"] == current["from_parent_action"]
        and normalized["status"] == current["status"]
        and normalized["reason_sha256"] == _bytes_digest(current["reason"].encode("utf-8"))
        and [row["path"] for row in normalized["evidence"]] == current["evidence_refs"]
    )


def validate_parent(state: Mapping[str, Any]) -> None:
    """Validate parent-owned binding facts; child bytes are checked on projection."""
    marker = state.get(MARKER)
    binding = state.get(STATE_KEY)
    if marker is None:
        _need(binding is None, "legacy ShipLoop state cannot contain a managed Improve binding")
        return
    _need(type(marker) is int and marker == VERSION, "unsupported managed Improve protocol version")
    recovery = state.get(RECOVERY_KEY)
    if recovery is not None:
        _validate_recovery_metadata(recovery)
    imported = state.get(IMPORT_KEY)
    if binding is None:
        if imported is not None:
            _need(isinstance(imported, Mapping), "managed Improve import receipt is invalid")
            required_import = {
                "version", "child_receipt", "child_receipt_sha256", "certificate",
                "certificate_sha256", "certificate_bytes_sha256", "binding_sha256",
                "replay_key", "profile", "parent_action", "evidence_manifest",
            }
            _need(set(imported) == required_import and imported.get("version") == VERSION, "managed Improve import receipt has an unsupported schema")
            _safe_relative(imported.get("child_receipt"), label="managed Improve import child receipt")
            _safe_relative(imported.get("certificate"), label="managed Improve import certificate")
            for key in (
                "child_receipt_sha256", "certificate_sha256", "certificate_bytes_sha256",
                "binding_sha256", "replay_key",
            ):
                _require_sha(imported.get(key), f"managed Improve import {key}")
            _need(isinstance(imported.get("profile"), str) and imported["profile"], "managed Improve import profile is invalid")
            _require_action(imported.get("parent_action"), "managed Improve import parent action")
            manifest = imported.get("evidence_manifest")
            _need(isinstance(manifest, Mapping) and manifest, "managed Improve import evidence manifest is invalid")
            for relative, value in manifest.items():
                _safe_relative(relative, label="managed Improve import evidence path")
                _require_sha(value, "managed Improve import evidence digest")
        return
    _need(isinstance(binding, Mapping), "managed Improve parent binding is invalid")
    required = {"version", "id", "receipt", "parent_action", "profile", "binding_sha256", "input_sha256", "policy_digest", "executor_digest", "scope_inventory_sha256", "status"}
    _need(set(binding) == required, "managed Improve parent binding has an unsupported schema")
    _need(binding.get("version") == VERSION, "unsupported managed Improve parent binding version")
    child_id = binding.get("id")
    _need(isinstance(child_id, str) and _CHILD_ID.fullmatch(child_id), "managed Improve parent child ID is unsafe")
    _need(binding.get("receipt") == _child_path(child_id), "managed Improve parent receipt path is invalid")
    parent_action = _require_action(binding.get("parent_action"), "managed Improve parent action")
    _need(isinstance(binding.get("profile"), str) and bool(binding["profile"]), "managed Improve parent profile is invalid")
    for key in ("binding_sha256", "input_sha256", "policy_digest", "executor_digest", "scope_inventory_sha256"):
        _require_sha(binding.get(key), f"managed Improve parent {key}")
    _need(binding.get("status") in _STATUSES, "managed Improve parent status is invalid")
    action = state.get("action")
    _need(isinstance(action, Mapping), "managed Improve parent action record is invalid")
    projection = state.get(PRIVATE_KEY)
    if isinstance(projection, Mapping):
        projected_parent = projection.get("parent")
        if isinstance(projected_parent, Mapping) and projected_parent.get(STATE_KEY) is not None:
            # A loaded child intentionally replaces the transient cursor so the
            # existing typed handlers can validate it. Its durable parent is
            # still independently bound to the parked action.
            parent_binding = projected_parent.get(STATE_KEY)
            _need(parent_binding == binding, "managed Improve transient projection differs from durable parent binding")
            parent_action_record = projected_parent.get("action")
            _need(
                isinstance(parent_action_record, Mapping)
                and projected_parent.get("stage") == STAGE
                and parent_action_record.get("stage") == STAGE
                and parent_action_record.get("id") == parent_action,
                "managed Improve transient projection has no parked parent cursor",
            )
        return
    _need(state.get("stage") == STAGE and action.get("stage") == STAGE, "managed Improve parent cursor is not parked")
    _need(action.get("id") == parent_action, "managed Improve parent action changed while child is active")


def _action_map_to_rows(value: Any, *, label: str) -> list[dict[str, str]]:
    """Store only child replay keys as rows, never the parent action ledger."""
    _need(isinstance(value, Mapping), f"{label} must be an action digest mapping")
    rows: list[dict[str, str]] = []
    for action_id, value_digest in sorted(value.items()):
        rows.append(
            {
                "id": _require_action(action_id, f"{label} action ID"),
                "digest": _require_sha(value_digest, f"{label} action digest"),
            }
        )
    return rows


def _action_rows_to_map(value: Any, *, label: str) -> dict[str, str]:
    _need(isinstance(value, list), f"{label} must be an action list")
    rows: dict[str, str] = {}
    for row in value:
        _need(isinstance(row, Mapping) and set(row) == {"id", "digest"}, f"{label} row is invalid")
        action_id = _require_action(row.get("id"), f"{label} action ID")
        _need(action_id not in rows, f"{label} repeats an action")
        rows[action_id] = _require_sha(row.get("digest"), f"{label} action digest")
    return rows


def _overlay_keys(profile: str) -> frozenset[str]:
    _need(profile in _PROFILE_OVERLAY_KEYS, "managed Improve profile has no overlay policy")
    return _PROFILE_OVERLAY_KEYS[profile] | {_PAUSE_OVERLAY_KEY}


def _validate_overlay_value(key: str, value: Any, parent: Mapping[str, Any]) -> Any:
    """Validate the small set of typed facts a profile may import."""
    if key in {
        "research_sha256", "research_certificate_sha256", "behavior_sha256",
        "spec_sha256", "lifecycle_sha256", "environment_sha256", "plan_sha256",
        "plan_wrapper_sha256", "bound_plan_hash", "knowledge_sha256",
    }:
        return _require_sha(value, f"managed Improve overlay {key}")
    if key == "research_as_of":
        _need(isinstance(value, str) and value.strip(), "managed Improve research as-of is invalid")
        return value
    if key == "bound_plan":
        _need(isinstance(value, str) and value, "managed Improve bound plan is invalid")
        return value
    if key == "system_test_protocol_version":
        _need(value == 1, "managed Improve system-test protocol version is invalid")
        return value
    if key == "knowledge_revision":
        _need(type(value) is int and value >= int(parent.get(key, 0)), "managed Improve knowledge revision is invalid")
        return value
    if key == "knowledge_action_id":
        return _require_action(value, "managed Improve knowledge action")
    if key == "outer_check_action":
        return _require_action(value, "managed Improve outer check action")
    if key == "system_test_pending":
        _need(
            isinstance(value, list)
            and len(value) <= 128
            and all(isinstance(item, str) and item for item in value)
            and len(set(value)) == len(value),
            "managed Improve system-test pending set is invalid",
        )
        return _json_copy(value, "managed Improve system-test pending set")
    if key == "paused":
        _need(isinstance(value, str) and value.strip(), "managed Improve pause state is invalid")
        return value
    if key == "objective":
        _need(isinstance(value, Mapping), "managed Improve objective state is invalid")
        prior = parent.get("objective")
        _need(isinstance(prior, Mapping), "managed Improve objective state has no parent binding")
        for name in ("loop_id", "kind", "base_stage", "receipt", "candidate"):
            _need(value.get(name) == prior.get(name), f"managed Improve objective {name} changed")
        _need(value.get("status") == "finalized", "managed Improve objective was not finalized")
        return _json_copy(value, "managed Improve objective state")
    if key == "objective_preallocation_bridge":
        _need(isinstance(value, Mapping), "managed Improve objective bridge is invalid")
        return _json_copy(value, "managed Improve objective bridge")
    raise ManagedImproveBridgeError(f"managed Improve overlay key {key!r} has no validator")


def _overlay(parent: Mapping[str, Any], execution: Mapping[str, Any], *, profile: str) -> dict[str, Any]:
    """Persist only profile-authorized child facts as a compact delta."""
    values: dict[str, Any] = {}
    removed: list[str] = []
    allowed = _overlay_keys(profile)
    keys = set(parent) | set(execution)
    for key in sorted(keys):
        if key in _CONTROL_KEYS or key.startswith("_"):
            continue
        in_parent, in_execution = key in parent, key in execution
        if in_parent == in_execution and (not in_parent or execution[key] == parent[key]):
            continue
        _need(key in allowed, f"managed Improve child cannot change parent field {key}")
        if not in_execution:
            removed.append(key)
        else:
            values[key] = _validate_overlay_value(key, execution[key], parent)
    return {"set": values, "delete": removed}


def _apply_overlay(parent: MutableMapping[str, Any], value: Any, *, profile: str) -> None:
    _need(isinstance(value, Mapping) and set(value) == {"set", "delete"}, "managed Improve execution overlay is invalid")
    additions, removals = value.get("set"), value.get("delete")
    _need(isinstance(additions, Mapping) and isinstance(removals, list), "managed Improve execution overlay is invalid")
    allowed = _overlay_keys(profile)
    for key in removals:
        _need(
            isinstance(key, str) and key in allowed and key not in _CONTROL_KEYS and not key.startswith("_"),
            "managed Improve execution overlay removes a protected field",
        )
        parent.pop(key, None)
    for key, item in additions.items():
        _need(
            isinstance(key, str) and key in allowed and key not in _CONTROL_KEYS and not key.startswith("_"),
            "managed Improve execution overlay changes a protected field",
        )
        parent[key] = _validate_overlay_value(key, item, parent)


def _new_parent_action(child_action: str, profile: str, input_value: Mapping[str, Any]) -> str:
    # Deterministic derivation makes a retry before its first transaction select
    # the same binding rather than silently creating another child identity.
    return "MI-" + _digest({"child_action": child_action, "profile": profile, "input": input_value})[:32]


def _new_child_id(parent_action: str, child_action: str, profile: str, input_value: Mapping[str, Any]) -> str:
    return "mi-" + _digest(
        {"parent_action": parent_action, "child_action": child_action, "profile": profile, "input": input_value}
    )[:32]


def _controller_binding(
    *,
    parent_action: str,
    child_action: str,
    profile: str,
    input_value: Mapping[str, Any],
    policy_digest: str,
    executor_digest: str,
    state: Mapping[str, Any],
) -> dict[str, Any]:
    controller = _controller()
    commit_policy = state.get("managed_improve_commit_policy", "audit-every-iteration")
    independent_review = state.get(
        "managed_improve_independent_review",
        {"required": False, "fallback_allowed": False},
    )
    try:
        binding = controller.new_binding(
            parent_action=parent_action,
            child_action_id=child_action,
            profile=profile,
            input_identity=_json_copy(input_value, "managed Improve input identity"),
            policy_digest=policy_digest,
            executor_digest=executor_digest,
            commit_policy=commit_policy,
            independent_review=_json_copy(independent_review, "managed Improve independent review policy"),
        )
    except Exception as exc:
        error_type = getattr(controller, "ManagedImproveError", ValueError)
        if isinstance(exc, error_type):
            raise ManagedImproveBridgeError(str(exc)) from exc
        raise
    checked = controller.assert_binding(binding)
    _need(isinstance(checked, Mapping), "managed Improve controller returned an invalid binding")
    return _json_copy(checked, "managed Improve binding")


def _new_record(
    *,
    binding: Mapping[str, Any],
    input_value: Mapping[str, Any],
    child: Mapping[str, Any],
    evidence_digests: Any = None,
) -> dict[str, Any]:
    controller = _controller()
    checked_child = controller.assert_child(_json_copy(child, "managed Improve child"))
    _need(isinstance(checked_child, Mapping), "managed Improve controller returned an invalid child")
    normalized_evidence = _normalize_phase_evidence(checked_child, evidence_digests)
    return {
        "schema": "shiploop-managed-improve-child",
        "version": VERSION,
        "binding": _json_copy(binding, "managed Improve binding"),
        "input_identity": _json_copy(input_value, "managed Improve input identity"),
        "scope_inventory_sha256": _digest(input_value["scope"]),
        "child": _json_copy(checked_child, "managed Improve child"),
        "evidence_digests": normalized_evidence,
    }


def _phase_evidence_snapshot(
    root: Path | str, refs: Any, writes: Mapping[str, str]
) -> dict[str, str]:
    _need(isinstance(refs, list) and refs, "managed Improve phase has no evidence references")
    snapshot: dict[str, str] = {}
    for relative in refs:
        _need(isinstance(relative, str), "managed Improve phase evidence reference is invalid")
        _safe_relative(relative, label="managed Improve phase evidence reference")
        _need(relative not in snapshot, "managed Improve phase evidence reference repeats")
        if relative in writes:
            body = writes[relative]
            _need(isinstance(body, str), "managed Improve phase evidence write is invalid")
            snapshot[relative] = _bytes_digest(body.encode("utf-8"))
        else:
            snapshot[relative] = _bytes_digest(
                _safe_read(root, relative, label="managed Improve phase evidence reference")
            )
    return snapshot


def _normalize_phase_evidence(child: Mapping[str, Any], value: Any) -> list[dict[str, Any]]:
    records = child.get("phase_records")
    _need(isinstance(records, list), "managed Improve child phase records are invalid")
    if value is None:
        _need(not records, "managed Improve child evidence digests are missing")
        return []
    _need(isinstance(value, list) and len(value) == len(records), "managed Improve child evidence digests are invalid")
    normalized: list[dict[str, Any]] = []
    for sequence, (phase_record, row) in enumerate(zip(records, value), start=1):
        _need(isinstance(phase_record, Mapping), "managed Improve child phase record is invalid")
        _need(isinstance(row, Mapping) and set(row) == {"sequence", "refs"}, "managed Improve evidence digest row is invalid")
        _need(row.get("sequence") == sequence, "managed Improve evidence digest sequence is invalid")
        refs = phase_record.get("evidence_refs")
        _need(isinstance(refs, list) and refs, "managed Improve phase has no evidence references")
        digests = row.get("refs")
        _need(isinstance(digests, Mapping) and set(digests) == set(refs), "managed Improve evidence digest references differ from phase evidence")
        normalized_refs: dict[str, str] = {}
        for relative in refs:
            _need(isinstance(relative, str), "managed Improve phase evidence reference is invalid")
            normalized_refs[relative] = _require_sha(digests.get(relative), "managed Improve phase evidence digest")
        normalized.append({"sequence": sequence, "refs": normalized_refs})
    return normalized


def _validate_phase_evidence(
    root: Path | str, child: Mapping[str, Any], value: Any, writes: Mapping[str, str]
) -> list[dict[str, Any]]:
    normalized = _normalize_phase_evidence(child, value)
    for row in normalized:
        actual = _phase_evidence_snapshot(root, list(row["refs"]), writes)
        _need(actual == row["refs"], "managed Improve phase evidence changed after acceptance")
    return normalized


def _append_phase_evidence(
    root: Path | str,
    old_child: Mapping[str, Any],
    old_value: Any,
    new_child: Mapping[str, Any],
    writes: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Carry validated historical refs forward and freeze one new phase."""
    prior = _validate_phase_evidence(root, old_child, old_value, writes)
    old_records = old_child.get("phase_records")
    new_records = new_child.get("phase_records")
    _need(isinstance(old_records, list) and isinstance(new_records, list), "managed Improve child phase records are invalid")
    _need(len(new_records) == len(old_records) + 1, "managed Improve controller did not append one phase record")
    latest = new_records[-1]
    _need(isinstance(latest, Mapping), "managed Improve controller phase record is invalid")
    refs = latest.get("evidence_refs")
    return [
        *prior,
        {"sequence": len(new_records), "refs": _phase_evidence_snapshot(root, refs, writes)},
    ]


def _assert_record(root: Path | str, parent: Mapping[str, Any], value: Any) -> dict[str, Any]:
    _need(isinstance(value, Mapping), "managed Improve child receipt is invalid")
    required = {"schema", "version", "binding", "input_identity", "scope_inventory_sha256", "child", "evidence_digests"}
    _need(set(value) == required, "managed Improve child receipt has an unsupported schema")
    _need(value.get("schema") == "shiploop-managed-improve-child" and value.get("version") == VERSION, "unsupported managed Improve child receipt")
    binding = parent.get(STATE_KEY)
    _need(isinstance(binding, Mapping), "managed Improve parent binding is unavailable")
    _need(value.get("binding") == binding or isinstance(value.get("binding"), Mapping), "managed Improve child binding is invalid")
    controller = _controller()
    child_binding = controller.assert_binding(_json_copy(value.get("binding"), "managed Improve child binding"))
    _need(isinstance(child_binding, Mapping), "managed Improve child binding is invalid")
    for key in ("parent_action", "profile", "binding_sha256", "policy_digest", "executor_digest"):
        _need(child_binding.get(key) == binding.get(key), f"managed Improve child {key} differs from parent binding")
    _need(_digest(value.get("input_identity")) == binding.get("input_sha256"), "managed Improve child input identity differs from parent binding")
    input_value = _validate_input_identity(root, value.get("input_identity"))
    _validate_live_scope(root, parent, input_value)
    recovery = parent.get(RECOVERY_KEY)
    if recovery is None:
        _need(input_value.get("recovery") is None, "managed Improve child has an unexpected recovery handoff")
    else:
        handoff = _validate_recovery_metadata(recovery)
        if handoff["to_child"] == binding.get("id"):
            _need(
                _recovery_input_matches_handoff(input_value.get("recovery"), handoff),
                "managed Improve child recovery handoff differs from its parent",
            )
        else:
            _need(input_value.get("recovery") is None, "managed Improve child received another recovery handoff")
    _need(
        value.get("scope_inventory_sha256") == _digest(input_value["scope"])
        and _digest(input_value["scope"]) == binding.get("scope_inventory_sha256"),
        "managed Improve child scope inventory differs from parent binding",
    )
    _need(_policy_digest(root, parent) == binding.get("policy_digest"), "managed Improve policy differs from child binding")
    _need(_executor_digest() == binding.get("executor_digest"), "managed Improve controller differs from child binding")
    child = controller.assert_child(_json_copy(value.get("child"), "managed Improve child"))
    _need(isinstance(child, Mapping), "managed Improve child is invalid")
    _need(child.get("binding") == child_binding, "managed Improve child binding differs from receipt binding")
    evidence_digests = _validate_phase_evidence(root, child, value.get("evidence_digests"), {})
    return _new_record(
        binding=child_binding, input_value=input_value, child=child,
        evidence_digests=evidence_digests,
    )


def _set_projection(
    state: MutableMapping[str, Any],
    parent: Mapping[str, Any],
    record: Mapping[str, Any],
    *,
    child_raw_sha256: str | None = None,
) -> MutableMapping[str, Any]:
    """Overlay the child cursor without changing the durable parent cursor."""
    controller = _controller()
    child = controller.assert_child(_json_copy(record["child"], "managed Improve child"))
    _need(isinstance(child, Mapping), "managed Improve child is invalid")
    execution = child.get("execution")
    _need(isinstance(execution, Mapping), "managed Improve child has no execution projection")
    phase = execution.get("phase")
    stage = execution.get("stage")
    action_id = execution.get("action")
    _need(isinstance(phase, str) and phase == child.get("current_phase"), "managed Improve execution phase differs from controller")
    _need(isinstance(stage, str) and stage == phase, "managed Improve execution stage differs from controller")
    action_id = _require_action(action_id, "managed Improve child action")
    binding = record.get("binding")
    _need(isinstance(binding, Mapping) and isinstance(binding.get("profile"), str), "managed Improve child profile is invalid")
    profile = binding["profile"]
    parent_copy = _json_copy(parent, "managed Improve parent state")
    _apply_overlay(state, execution.get("overlay"), profile=profile)
    parent_actions = parent_copy.get("completed_actions", {})
    _need(isinstance(parent_actions, Mapping), "managed Improve parent action ledger is invalid")
    child_actions = _action_rows_to_map(execution.get("completed_actions"), label="managed Improve child completed actions")
    _need(not set(parent_actions).intersection(child_actions), "managed Improve child replay conflicts with parent action ledger")
    state["phase"] = phase
    state["stage"] = stage
    state["action"] = {"id": action_id, "stage": stage}
    state["completed_actions"] = {**_json_copy(parent_actions, "managed Improve parent action ledger"), **child_actions}
    state[PRIVATE_KEY] = {
        "parent": parent_copy,
        "record": _json_copy(record, "managed Improve child record"),
        "child_raw_sha256": child_raw_sha256,
    }
    state.pop(EVIDENCE_KEY, None)
    return state


def _starting_record(
    root: Path | str,
    state: MutableMapping[str, Any],
    *,
    profile: str,
    input_value: Mapping[str, Any] | None = None,
    scope_inventory: Mapping[str, Any] | None = None,
    parent_action: str | None = None,
    recovery_writes: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _need(enabled(state), "managed Improve is not enabled for this run")
    _need(STATE_KEY not in state, "managed Improve child is already active")
    child_action = _require_action(state.get("action", {}).get("id"), "managed Improve initial child action")
    _need(isinstance(state.get("stage"), str) and state["stage"] in _FIRST_PHASE_PROFILES, "managed Improve can start only at a first convergence phase")
    _need(_FIRST_PHASE_PROFILES[state["stage"]] == profile, "managed Improve profile does not match first convergence phase")
    candidate_inputs = _validate_input_identity(
        root,
        input_value if input_value is not None else input_identity(
            root, state, profile=profile, scope_inventory=scope_inventory,
            recovery_writes=recovery_writes,
        ),
        recovery_writes,
    )
    parent_action = parent_action or _new_parent_action(child_action, profile, candidate_inputs)
    parent_action = _require_action(parent_action, "managed Improve parent action")
    policy_digest = _policy_digest(root, state)
    executor_digest = _executor_digest()
    binding = _controller_binding(
        parent_action=parent_action,
        child_action=child_action,
        profile=profile,
        input_value=candidate_inputs,
        policy_digest=policy_digest,
        executor_digest=executor_digest,
        state=state,
    )
    child_id = _new_child_id(parent_action, child_action, profile, candidate_inputs)
    receipt = _child_path(child_id)
    controller = _controller()
    child = controller.new_child(binding)
    child = controller.assert_child(child)
    _need(isinstance(child, Mapping), "managed Improve controller did not create a child")
    _need(child.get("current_phase") == state["stage"], "managed Improve controller initial phase does not match the typed stage")
    child = _json_copy(child, "managed Improve child")
    execution = child.get("execution")
    _need(isinstance(execution, MutableMapping), "managed Improve child has no mutable execution projection")
    execution.update(
        phase=state["stage"],
        stage=state["stage"],
        action=child_action,
        completed_actions=[],
        overlay={"set": {}, "delete": []},
    )
    child = controller.assert_child(child)
    record = _new_record(binding=binding, input_value=candidate_inputs, child=child)
    summary = _binding_summary(binding, child_id=child_id, receipt=receipt, input_value=candidate_inputs)
    return record, summary


def begin(
    root: Path | str,
    state: MutableMapping[str, Any],
    profile: str,
    *,
    input_value: Mapping[str, Any] | None = None,
    scope_inventory: Mapping[str, Any] | None = None,
    parent_action: str | None = None,
    recovery_writes: Mapping[str, str] | None = None,
) -> None:
    """Stage a child start; ``prepare`` makes it durable in the caller's WAL."""
    record, summary = _starting_record(
        root, state, profile=profile, input_value=input_value,
        scope_inventory=scope_inventory, parent_action=parent_action,
        recovery_writes=recovery_writes,
    )
    parent = _json_copy(state, "managed Improve starting parent state")
    recovery = state.get(RECOVERY_KEY)
    if recovery is not None:
        recovered = _validate_recovery_metadata(recovery)
        _need(recovered["to_child"] in (None, summary["id"]), "managed Improve recovery already targets another child")
        recovered["to_child"] = summary["id"]
        state[RECOVERY_KEY] = recovered
        parent[RECOVERY_KEY] = _json_copy(recovered, "managed Improve recovery handoff")
    state[STATE_KEY] = summary
    state["stage"] = STAGE
    state["action"] = {"id": summary["parent_action"], "stage": STAGE}
    # The original phase remains useful when an outer presentation labels the
    # parked parent; its action/stage are the only public control cursor.
    state[PRIVATE_KEY] = {"parent": parent, "record": record, "starting": True}


def _auto_start(root: Path | str, state: MutableMapping[str, Any], event: str) -> bool:
    if not enabled(state) or STATE_KEY in state or not event.startswith("complete:"):
        return False
    profile = _FIRST_PHASE_PROFILES.get(state.get("stage"))
    if profile is None:
        return False
    begin(root, state, profile)
    return True


def _active_record(root: Path | str, parent: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    validate_parent(parent)
    binding = parent.get(STATE_KEY)
    _need(isinstance(binding, Mapping), "managed Improve parent binding is unavailable")
    relative = binding["receipt"]
    record, raw = _read_record(root, relative, label="managed Improve child receipt")
    record = _assert_record(root, parent, record)
    child = record["child"]
    _need(child.get("status") == binding.get("status"), "managed Improve child status differs from parent binding")
    return record, _bytes_digest(raw)


def _assert_projection_current(
    root: Path | str,
    parent: Mapping[str, Any],
    projection: Mapping[str, Any],
    record: Mapping[str, Any],
    *,
    allow_updated_child: bool = False,
) -> None:
    """Reject a callback projected from a receipt replaced since ``project``."""
    expected = projection.get("child_raw_sha256")
    if expected is None:
        return
    _require_sha(expected, "managed Improve projected child receipt digest")
    current, actual = _active_record(root, parent)
    _need(actual == expected, "managed Improve child receipt changed since projection; reload the current packet")
    if allow_updated_child:
        return
    _need(current == record, "managed Improve child receipt projection is stale")
    old_execution = record.get("child", {}).get("execution") if isinstance(record.get("child"), Mapping) else None
    current_execution = current.get("child", {}).get("execution") if isinstance(current.get("child"), Mapping) else None
    _need(
        isinstance(old_execution, Mapping)
        and isinstance(current_execution, Mapping)
        and old_execution.get("action") == current_execution.get("action"),
        "managed Improve child action changed since projection; reload the current packet",
    )


def project(root: Path | str, state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Load an active child into a transient execution projection.

    The caller must later pass this object to :func:`prepare`.  The durable
    ``state.md`` remains parked at ``managed-improve`` and never receives the
    private projection key.
    """
    validate_parent(state)
    if not enabled(state) or state.get(STATE_KEY) is None:
        return state
    parent = _json_copy(state, "managed Improve durable parent state")
    record, raw_digest = _active_record(root, parent)
    status = record["child"]["status"]
    if status == "active":
        return _set_projection(state, parent, record, child_raw_sha256=raw_digest)
    # Incomplete outcomes intentionally stay at the parent waiting cursor.
    # They are useful packet state but cannot impersonate a child phase.
    state[PRIVATE_KEY] = {
        "parent": parent,
        "record": record,
        "child_raw_sha256": raw_digest,
        "terminal": True,
    }
    return state


def _recovery_packet_handoff(
    binding: Mapping[str, Any], record: Mapping[str, Any], value: Any
) -> dict[str, Any] | None:
    if value is None:
        return None
    handoff = _validate_recovery_metadata(value)
    if handoff["to_child"] != binding.get("id"):
        return None
    input_value = record.get("input_identity")
    _need(isinstance(input_value, Mapping), "managed Improve packet recovery input is unavailable")
    _need(
        _recovery_input_matches_handoff(input_value.get("recovery"), handoff),
        "managed Improve packet recovery handoff differs from its child",
    )
    normalized = _normalize_recovery_input_identity(input_value.get("recovery"))
    _need(normalized is not None, "managed Improve packet recovery input is unavailable")
    # ``sha256`` covers the immutable source handoff.  ``to_child`` stays
    # outside it because the destination identity is derived from this input.
    return {
        "from_child": handoff["from_child"],
        "from_parent_action": handoff["from_parent_action"],
        "status": handoff["status"],
        "reason": handoff["reason"],
        "evidence_refs": list(handoff["evidence_refs"]),
        "source_receipt_sha256": normalized["source_receipt_sha256"],
        "sha256": normalized["recovery_sha256"],
        "to_child": handoff["to_child"],
    }


def packet_metadata(state: Mapping[str, Any]) -> dict[str, Any] | None:
    """Expose a small, non-authoritative child orientation record for packets."""
    binding = state.get(STATE_KEY)
    if not isinstance(binding, Mapping):
        return None
    base = {
        "id": binding.get("id"),
        "receipt": binding.get("receipt"),
        "certificate": _certificate_path(binding["id"]) if isinstance(binding.get("id"), str) and _CHILD_ID.fullmatch(binding["id"]) else None,
        "binding_sha256": binding.get("binding_sha256"),
        "profile": binding.get("profile"),
        "status": binding.get("status"),
        "parent_action": binding.get("parent_action"),
    }
    projection = state.get(PRIVATE_KEY)
    if not isinstance(projection, Mapping) or not isinstance(projection.get("record"), Mapping):
        return base
    try:
        child = _controller().packet_metadata(projection["record"]["child"])
    except Exception as exc:
        error_type = getattr(_controller(), "ManagedImproveError", ValueError)
        if isinstance(exc, error_type):
            raise ManagedImproveBridgeError(str(exc)) from exc
        raise
    _need(isinstance(child, Mapping), "managed Improve packet metadata is invalid")
    result = {**base, **_json_copy(child, "managed Improve packet metadata")}
    handoff = _recovery_packet_handoff(binding, projection["record"], state.get(RECOVERY_KEY))
    if handoff is not None:
        result["recovery_handoff"] = handoff
    return result


def set_evidence(
    state: MutableMapping[str, Any],
    event: Mapping[str, Any] | None = None,
    /,
    **fields: Any,
) -> dict[str, Any]:
    """Stage one controller event after typed ShipLoop validation succeeds.

    Existing protocol handlers validate the real result, check record, commits,
    and typed artifacts first.  They then call this helper before ``persist``.
    The bridge rejects an event whose phase does not equal the saved child
    cursor, so a stale callback cannot advance an active parent.
    """
    projection = state.get(PRIVATE_KEY)
    _need(isinstance(projection, Mapping) and isinstance(projection.get("record"), Mapping), "managed Improve child is not projected")
    child = projection["record"].get("child")
    _need(isinstance(child, Mapping) and child.get("status") == "active", "managed Improve child is not active")
    payload: dict[str, Any] = {}
    if event is not None:
        _need(isinstance(event, Mapping), "managed Improve event must be an object")
        payload.update(_json_copy(event, "managed Improve event"))
    payload.update(_json_copy(fields, "managed Improve event fields"))
    payload.setdefault("kind", "complete")
    payload.setdefault("phase", child.get("current_phase"))
    payload.setdefault("flags", {})
    _need(payload.get("kind") != "done", "managed Improve does not accept a generic done event")
    _need(payload.get("phase") == child.get("current_phase"), "managed Improve event phase is stale or skipped")
    state[EVIDENCE_KEY] = _json_copy(payload, "managed Improve event")
    return _json_copy(payload, "managed Improve event")


def _resume_action(binding: Mapping[str, Any], child: Mapping[str, Any]) -> str:
    records = child.get("phase_records")
    _need(isinstance(records, list), "managed Improve child phase records are invalid")
    return "MR-" + _digest(
        {
            "binding": binding.get("binding_sha256"),
            "records": len(records),
            "phase": child.get("current_phase"),
        }
    )[:32]


def _resume_record(
    root: Path | str,
    state: MutableMapping[str, Any],
    parent: Mapping[str, Any],
    projection: Mapping[str, Any],
    record: Mapping[str, Any],
    *,
    reason: str,
    evidence_refs: Sequence[str],
) -> dict[str, Any]:
    """Apply the controller's same-child recovery record without an import."""
    _need(isinstance(reason, str) and reason.strip(), "managed Improve resume reason is invalid")
    _need(not isinstance(evidence_refs, (str, bytes)) and isinstance(evidence_refs, Sequence), "managed Improve resume evidence is invalid")
    refs = list(evidence_refs)
    _need(refs and all(isinstance(item, str) for item in refs), "managed Improve resume needs evidence references")
    for relative in refs:
        _path_exists_or_written(root, relative, {})
    _assert_projection_current(root, parent, projection, record)
    controller = _controller()
    child = controller.assert_child(record["child"])
    resumable = (
        isinstance(child, Mapping)
        and (
            child.get("status") in _INCOMPLETE
            or (child.get("status") == "active" and child.get("paused") is True)
        )
    )
    _need(resumable, "only an incomplete or paused managed Improve child can resume")
    try:
        updated, route = controller.resume(child, reason=reason, evidence_refs=refs)
    except Exception as exc:
        error_type = getattr(controller, "ManagedImproveError", ValueError)
        if isinstance(exc, error_type):
            raise ManagedImproveBridgeError(str(exc)) from exc
        raise
    updated = controller.assert_child(updated)
    _need(
        isinstance(updated, Mapping)
        and isinstance(route, Mapping)
        and route.get("status") == "active"
        and route.get("current_phase") == updated.get("current_phase"),
        "managed Improve resume did not restore an active child",
    )
    execution = _json_copy(updated.get("execution"), "managed Improve resumed execution")
    phase = updated.get("current_phase")
    _need(isinstance(execution, MutableMapping) and isinstance(phase, str), "managed Improve resumed phase is invalid")
    execution.update(phase=phase, stage=phase, action=_resume_action(record["binding"], updated))
    updated = _json_copy(updated, "managed Improve resumed child")
    updated["execution"] = execution
    evidence_digests = _append_phase_evidence(
        root, child, record.get("evidence_digests"), controller.assert_child(updated), {}
    )
    record = _new_record(
        binding=record["binding"], input_value=record["input_identity"],
        child=controller.assert_child(updated),
        evidence_digests=evidence_digests,
    )
    _set_projection(state, parent, record, child_raw_sha256=projection.get("child_raw_sha256"))
    # A resumed controller state is not a parent pause.  ``prepare`` captures
    # the deletion in its bounded overlay while it persists the same receipt.
    state.pop("paused", None)
    state[PRIVATE_KEY]["resuming"] = True
    return record


def resume(
    root: Path | str,
    state: MutableMapping[str, Any],
    *,
    reason: str,
    evidence_refs: Sequence[str],
) -> dict[str, Any]:
    """Stage a same-bound-child recovery for the caller's next transaction.

    Call this before ``persist(..., "resume")``.  It never writes directly;
    the resumed child receipt and parked parent state are committed by the
    caller's existing one transaction.
    """
    validate_parent(state)
    _need(enabled(state) and state.get(STATE_KEY) is not None, "managed Improve child is unavailable")
    projection = state.get(PRIVATE_KEY)
    if not isinstance(projection, Mapping) or not isinstance(projection.get("record"), Mapping):
        project(root, state)
        projection = state.get(PRIVATE_KEY)
    _need(
        isinstance(projection, Mapping)
        and isinstance(projection.get("parent"), Mapping)
        and isinstance(projection.get("record"), Mapping),
        "managed Improve resume projection is unavailable",
    )
    parent = _json_copy(projection["parent"], "managed Improve resuming parent")
    record = _json_copy(projection["record"], "managed Improve resuming child")
    record = _resume_record(
        root, state, parent, projection, record, reason=reason, evidence_refs=evidence_refs
    )
    child = record["child"]
    return {
        "status": child["status"], "current_phase": child["current_phase"],
        "action": child["execution"]["action"], "resumed": True,
    }


def _recorded_resume_arguments(record: Mapping[str, Any]) -> tuple[str, list[str]]:
    child = record.get("child")
    _need(isinstance(child, Mapping) and isinstance(child.get("phase_records"), list), "managed Improve child has no interruption record")
    _need(child["phase_records"], "managed Improve child has no interruption record")
    interruption = child["phase_records"][-1]
    _need(isinstance(interruption, Mapping), "managed Improve child has no resumable interruption")
    status = child.get("status")
    paused = child.get("paused") is True
    kind = interruption.get("kind")
    if status in _INCOMPLETE:
        _need(kind in _INCOMPLETE, "managed Improve child has no resumable interruption")
        reason = interruption.get("reason")
        prefix = "resume after recorded interruption"
    else:
        _need(status == "active" and paused, "managed Improve child has no resumable interruption")
        flags = interruption.get("flags")
        _need(isinstance(flags, Mapping), "managed Improve paused child flags are invalid")
        _need(
            (kind == "repair" and flags.get("disposition") == "required")
            or (kind == "complete" and flags.get("disposition") == "pause"),
            "managed Improve paused child has no controller-owned pause record",
        )
        reason = interruption.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            reason = f"controller-owned pause at {child.get('current_phase')}"
        prefix = "resume after recorded pause"
    refs = interruption.get("evidence_refs")
    _need(isinstance(reason, str) and reason.strip(), "managed Improve interruption reason is invalid")
    _need(isinstance(refs, list) and refs and all(isinstance(item, str) for item in refs), "managed Improve interruption evidence is invalid")
    return f"{prefix}: {reason}", list(refs)


def _planning_revisit_target(event: str) -> str | None:
    if not event.startswith("planning-revisit:"):
        return None
    target = event.removeprefix("planning-revisit:")
    _need(target in {"survey", "research", "behavior", "spec"}, "managed Improve planning revisit target is invalid")
    return target


def _recovery_kind(event: str, state: Mapping[str, Any]) -> str | None:
    """Map a script-owned non-success transition to the pure controller."""
    if event == "halt":
        return "stopped"
    if event == "pause":
        return "blocked"
    if event in _SAME_FAMILY_REPAIR_EVENTS:
        return "repair"
    return None


def _owned_post_inner_recovery_reason(
    state: Mapping[str, Any], writes: Mapping[str, str]
) -> str:
    """Read the CLI's actual post-inner repair reason from owned staged records."""
    active_step = state.get("active_step")
    if isinstance(active_step, str) and re.fullmatch(r"[SD][0-9]+", active_step):
        relative = f"steps/{active_step}.md"
        body = writes.get(relative)
        if body is not None:
            _need(isinstance(body, str), "managed Improve post-inner step receipt is invalid")
            try:
                receipt = store.loads(body)
            except store.StorageError as exc:
                raise ManagedImproveBridgeError("managed Improve post-inner step receipt is invalid") from exc
            _need(isinstance(receipt, Mapping), "managed Improve post-inner step receipt is invalid")
            cycles = receipt.get("improve_cycles")
            _need(isinstance(cycles, list) and cycles, "managed Improve post-inner repair is absent from the active step")
            latest = cycles[-1]
            _need(
                isinstance(latest, Mapping) and latest.get("kind") == "post-inner-objective-repair",
                "managed Improve post-inner repair is not the active step's latest record",
            )
            reason = latest.get("reason")
            _need(
                isinstance(reason, str) and reason.strip() and "\x00" not in reason,
                "managed Improve post-inner repair reason is invalid",
            )
            return reason.strip()

    reasons: list[str] = []
    for relative, body in sorted(writes.items()):
        if not (relative.startswith("objectives/") and "/abandoned/" in relative):
            continue
        _need(isinstance(body, str), "managed Improve post-inner archive is invalid")
        try:
            archive = store.loads(body)
        except store.StorageError as exc:
            raise ManagedImproveBridgeError("managed Improve post-inner archive is invalid") from exc
        _need(isinstance(archive, Mapping), "managed Improve post-inner archive is invalid")
        reason = archive.get("reason")
        _need(
            isinstance(reason, str) and reason.strip() and "\x00" not in reason,
            "managed Improve post-inner archive reason is invalid",
        )
        reasons.append(reason.strip())
    _need(len(reasons) == 1, "managed Improve post-inner recovery needs one owned abandonment reason")
    return reasons[0]


def _recovery_reason(
    event: str, state: Mapping[str, Any], writes: Mapping[str, str]
) -> str:
    if event == "post-inner-objective-repair":
        return _owned_post_inner_recovery_reason(state, writes)
    if event == "pause":
        candidate = state.get("paused")
    elif event == "halt":
        candidate = state.get("halt_reason")
    else:
        candidate = None
    if isinstance(candidate, str) and candidate.strip() and "\x00" not in candidate:
        return candidate.strip()
    return f"ShipLoop recorded {event}; see the immutable recovery evidence."


def _recovery_sources(writes: Mapping[str, str]) -> list[str]:
    """Select only typed receipts and archives the CLI already staged."""
    selected: list[str] = []
    for relative, body in sorted(writes.items()):
        _need(isinstance(relative, str) and isinstance(body, str), "managed Improve recovery write is invalid")
        if relative == "handoff.md" or relative == "knowledge.md" or relative.startswith(_RECOVERY_EVIDENCE_PREFIXES):
            _safe_relative(relative, label="managed Improve recovery source")
            selected.append(relative)
    return selected


def _recovery_note_path(child_id: str, sequence: int, payload: Mapping[str, Any]) -> str:
    _need(isinstance(child_id, str) and _CHILD_ID.fullmatch(child_id), "managed Improve recovery child ID is invalid")
    _need(type(sequence) is int and sequence > 0, "managed Improve recovery sequence is invalid")
    return f"{DIRECTORY}/{child_id}-recovery-{sequence:04d}-{_digest(payload)[:32]}.md"


def _synthetic_recovery_event(
    root: Path | str,
    state: Mapping[str, Any],
    record: Mapping[str, Any],
    event: str,
    kind: str,
    writes: MutableMapping[str, str],
) -> dict[str, Any]:
    """Create auditable controller input for a CLI recovery command.

    Normal completion callbacks supply ``_managed_evidence`` themselves.  The
    established repair, pause, and halt commands intentionally do not claim a
    successful phase result, so the bridge records their existing typed
    receipt/archive bytes and a compact recovery note instead.
    """
    binding = state.get(STATE_KEY)
    child = record.get("child")
    _need(isinstance(binding, Mapping) and isinstance(child, Mapping), "managed Improve recovery binding is unavailable")
    phase = child.get("current_phase")
    _need(isinstance(phase, str) and phase, "managed Improve recovery phase is invalid")
    source_paths = _recovery_sources(writes)
    source_digests = {
        relative: _bytes_digest(writes[relative].encode("utf-8"))
        for relative in source_paths
    }
    reason = _recovery_reason(event, state, writes)
    sequence = len(child.get("phase_records", [])) + 1
    details = {
        "event": event,
        "kind": kind,
        "phase": phase,
        "reason": reason,
        "typed_stage": state.get("stage"),
        "typed_action": _json_copy(state.get("action"), "managed Improve recovery action"),
        "source_digests": source_digests,
    }
    note_relative = _recovery_note_path(binding.get("id"), sequence, details)
    body = store.dumps(details, "ShipLoop managed Improve recovery")
    existing = writes.get(note_relative)
    if existing is not None:
        _need(existing == body, "managed Improve recovery note conflicts with this callback")
    else:
        note_path = _safe_path(root, note_relative, label="managed Improve recovery note")
        if note_path.exists():
            _need(_safe_read(root, note_relative, label="managed Improve recovery note") == body.encode("utf-8"), "managed Improve recovery note already differs")
        writes[note_relative] = body
    flags: dict[str, str] = {}
    if kind == "repair" and event == "step-plan-repair":
        if state.get("stage") == "step-plan-disposition":
            flags = {"disposition": "required"}
        elif state.get("stage") == "step-plan-review":
            flags = {"disposition": "not-required"}
    return {
        "kind": kind,
        "phase": phase,
        "evidence_refs": [note_relative, *source_paths],
        "flags": flags,
        "reason": reason,
    }


def _validate_writes(
    state: Mapping[str, Any],
    writes: Mapping[str, str],
    deletes: Sequence[str],
    *,
    record: Mapping[str, Any] | None,
    recovery_event: str | None = None,
) -> None:
    _need(isinstance(writes, Mapping), "managed Improve writes must be a mapping")
    _need(not isinstance(deletes, (str, bytes)) and isinstance(deletes, Sequence), "managed Improve deletes must be a path sequence")
    binding = state.get(STATE_KEY)
    child_path = binding.get("receipt") if isinstance(binding, Mapping) else None
    certificate = _certificate_path(binding["id"]) if isinstance(binding, Mapping) and isinstance(binding.get("id"), str) and _CHILD_ID.fullmatch(binding["id"]) else None
    allow_pending_plan = bool(state.get("_managed_pending_plan_import"))
    child_status = record.get("child", {}).get("status") if isinstance(record, Mapping) else None
    profile = binding.get("profile") if isinstance(binding, Mapping) else None
    child_phase = record.get("child", {}).get("current_phase") if isinstance(record, Mapping) else None
    objective = state.get("objective")
    sequence_finalize = (
        profile == "objective"
        and child_phase == "objective-finalize"
        and isinstance(objective, Mapping)
        and objective.get("kind") == "sequence"
    )
    revisit_target = _planning_revisit_target(recovery_event) if recovery_event is not None else None
    write_paths = set(writes)
    delete_paths = set(deletes)
    for relative in [*writes.keys(), *deletes]:
        _need(isinstance(relative, str), "managed Improve transaction path is invalid")
        _safe_relative(relative, label="managed Improve transaction path")
        _need(relative not in (child_path, certificate), "managed Improve child records are bridge-owned")
        _need(not relative.startswith(f"{DIRECTORY}/"), "managed Improve child namespace is bridge-owned")
        if revisit_target is not None:
            if relative.startswith("planning-history/"):
                _need(relative in write_paths, "managed Improve planning revisit may only write its archive")
                continue
            if relative in delete_paths and (
                relative in _PLANNING_REVISIT_PATHS or relative.startswith("planning/")
            ):
                continue
        if relative in {"environment.md", "behavior.md", "spec.md", "lifecycle.md", "spec-draft.md", "lifecycle-draft.md"}:
            _need(
                isinstance(profile, str) and relative in _PROFILE_CANDIDATE_WRITES.get(profile, frozenset()),
                f"managed Improve profile {profile!r} cannot write candidate {relative}",
            )
            continue
        if relative == "backchain/plan.md":
            _need(
                sequence_finalize or (allow_pending_plan and child_status == "needs-replan"),
                "managed Improve cannot write the dependency DAG outside an explicitly validated pending replan import",
            )
        elif relative == "plan.md" and sequence_finalize:
            continue
        else:
            _need(relative not in _FORBIDDEN_PARENT_PATHS, f"managed Improve cannot write parent control record {relative}")
    for relative, text in writes.items():
        _need(isinstance(text, str), "managed Improve write content is invalid")


def _path_exists_or_written(root: Path | str, relative: str, writes: Mapping[str, str]) -> None:
    _safe_relative(relative, label="managed Improve evidence reference")
    if relative in writes:
        _need(isinstance(writes[relative], str), "managed Improve evidence write is invalid")
        return
    path = _safe_path(root, relative, label="managed Improve evidence reference")
    _need(path.is_file(), f"managed Improve evidence reference is unavailable: {relative}")
    _safe_read(root, relative, label="managed Improve evidence reference")


def _validate_certificate_artifacts(root: Path | str, certificate: Mapping[str, Any], writes: Mapping[str, str]) -> None:
    refs = certificate.get("evidence_refs")
    _need(isinstance(refs, list) and refs, "managed Improve certificate lacks evidence references")
    for relative in refs:
        _need(isinstance(relative, str), "managed Improve certificate evidence reference is invalid")
        _path_exists_or_written(root, relative, writes)
    output = certificate.get("output_identity")
    _need(isinstance(output, Mapping), "managed Improve certificate output identity is invalid")
    artifacts = output.get("artifact_digests")
    if artifacts is not None:
        _need(isinstance(artifacts, Mapping) and artifacts, "managed Improve output artifact digests are invalid")
        for relative, expected in artifacts.items():
            _need(isinstance(relative, str), "managed Improve output artifact path is invalid")
            expected = _require_sha(expected, f"managed Improve output artifact {relative} digest")
            if relative in writes:
                actual = _bytes_digest(writes[relative].encode("utf-8"))
            else:
                actual = _bytes_digest(_safe_read(root, relative, label=f"managed Improve output artifact {relative}"))
            _need(actual == expected, f"managed Improve output artifact {relative} digest changed")


def _certificate_evidence_manifest(
    root: Path | str, certificate: Mapping[str, Any], writes: Mapping[str, str]
) -> dict[str, str]:
    """Freeze every certificate reference by bytes for later parent gates."""
    _validate_certificate_artifacts(root, certificate, writes)
    refs = certificate["evidence_refs"]
    output = certificate["output_identity"]
    artifacts = output.get("artifact_digests", {})
    _need(isinstance(refs, list) and isinstance(artifacts, Mapping), "managed Improve certificate evidence is invalid")
    manifest: dict[str, str] = {}
    for relative in sorted(set(refs) | set(artifacts)):
        _need(isinstance(relative, str), "managed Improve certificate evidence reference is invalid")
        if relative in writes:
            body = writes[relative]
            _need(isinstance(body, str), "managed Improve certificate evidence write is invalid")
            manifest[relative] = _bytes_digest(body.encode("utf-8"))
        else:
            manifest[relative] = _bytes_digest(
                _safe_read(root, relative, label="managed Improve certificate evidence")
            )
    _need(manifest, "managed Improve certificate evidence manifest is empty")
    return manifest


def _typed_pass_matches(
    root: Path | str, state: Mapping[str, Any], event: Mapping[str, Any], writes: Mapping[str, str]
) -> None:
    """Bind the controller's canonical pass to existing typed product evidence.

    The controller owns ``child.passes``.  A legacy ``improve_cycles`` row is
    consulted only as independently validated evidence, never as a second
    counter or alternate stopping rule.
    """
    completed = event.get("completed_pass")
    if completed is None:
        return
    binding = state.get(STATE_KEY)
    # Only the product profile has legacy ``improve_cycles``.  Planning,
    # objective, and step-plan receipts have their own typed archives, which
    # their adapters already validate before they emit the controller event.
    if not isinstance(binding, Mapping) or binding.get("profile") != "product":
        return
    _need(isinstance(completed, Mapping), "managed Improve completed pass is invalid")
    active_step = state.get("active_step")
    if not isinstance(active_step, str) or not re.fullmatch(r"[SD][0-9]+", active_step):
        return
    relative = f"steps/{active_step}.md"
    path = _safe_path(root, relative, label="managed Improve typed step receipt")
    if not path.is_file():
        return
    if relative in writes:
        try:
            receipt = store.loads(writes[relative])
        except store.StorageError as exc:
            raise ManagedImproveBridgeError("managed Improve staged typed step receipt is invalid") from exc
        _need(isinstance(receipt, Mapping), "managed Improve staged typed step receipt is invalid")
    else:
        receipt, _raw = _read_record(root, relative, label="managed Improve typed step receipt")
    cycles = receipt.get("improve_cycles")
    _need(isinstance(cycles, list), "managed Improve typed step receipt has no cycle evidence")
    matches = [
        row for row in cycles
        if isinstance(row, Mapping)
        and row.get("id") == completed.get("id")
        and (row.get("primary_commit") == completed.get("commit") or row.get("commit") == completed.get("commit"))
        and row.get("outcome") == completed.get("outcome")
    ]
    _need(len(matches) == 1, "managed Improve completed pass does not match one typed cycle receipt")
    _need(matches[0].get("check_action") or matches[0].get("verified") is True, "managed Improve typed cycle has no verified check evidence")


def _event_snapshot_path(child_id: str, sequence: int, source: str, digest: str) -> str:
    _need(isinstance(child_id, str) and _CHILD_ID.fullmatch(child_id), "managed Improve child ID is unsafe")
    _need(type(sequence) is int and sequence > 0, "managed Improve evidence sequence is invalid")
    _safe_relative(source, label="managed Improve event evidence source")
    _require_sha(digest, "managed Improve evidence digest")
    source_token = _digest({"source": source, "digest": digest})[:32]
    return f"{DIRECTORY}/{child_id}-evidence-{sequence:04d}-{source_token}.md"


def _event_reference_paths(event: Mapping[str, Any]) -> list[str]:
    refs = event.get("evidence_refs")
    _need(isinstance(refs, list) and refs and all(isinstance(item, str) for item in refs), "managed Improve event evidence references are invalid")
    extra: list[str] = []
    completed = event.get("completed_pass")
    if isinstance(completed, Mapping):
        value = completed.get("evidence_ref")
        if isinstance(value, str):
            extra.append(value)
        independent = completed.get("independent_review")
        if isinstance(independent, Mapping) and isinstance(independent.get("evidence_ref"), str):
            extra.append(independent["evidence_ref"])
    fresh = event.get("fresh_evidence")
    if isinstance(fresh, Mapping):
        value = fresh.get("evidence_ref")
        if isinstance(value, str):
            extra.append(value)
        checks = fresh.get("checks")
        if isinstance(checks, list):
            for check in checks:
                if isinstance(check, Mapping) and isinstance(check.get("evidence_ref"), str):
                    extra.append(check["evidence_ref"])
    _need(all(value in refs for value in extra), "managed Improve nested evidence reference is absent from phase evidence")
    return list(refs)


def _replace_event_reference(value: Any, replacements: Mapping[str, str]) -> Any:
    if isinstance(value, str):
        return replacements.get(value, value)
    return value


def _freeze_event_evidence(
    root: Path | str,
    state: Mapping[str, Any],
    record: Mapping[str, Any],
    event: Mapping[str, Any],
    writes: MutableMapping[str, str],
) -> dict[str, Any]:
    """Copy callback proof into immutable bridge-owned evidence records."""
    frozen = _json_copy(event, "managed Improve event")
    refs = _event_reference_paths(frozen)
    binding = state.get(STATE_KEY)
    _need(isinstance(binding, Mapping), "managed Improve parent binding is unavailable")
    child_id = binding.get("id")
    child = record.get("child")
    _need(isinstance(child, Mapping) and isinstance(child.get("phase_records"), list), "managed Improve child phase records are invalid")
    sequence = len(child["phase_records"]) + 1
    replacements: dict[str, str] = {}
    for relative in refs:
        _safe_relative(relative, label="managed Improve event evidence reference")
        if relative.startswith(f"{DIRECTORY}/"):
            # Resume events cite the prior bridge-owned snapshot directly.
            _path_exists_or_written(root, relative, writes)
            replacements[relative] = relative
            continue
        if relative in writes:
            source = writes[relative]
            _need(isinstance(source, str), "managed Improve event evidence write is invalid")
            raw = source.encode("utf-8")
        else:
            raw = _safe_read(root, relative, label="managed Improve event evidence reference")
            try:
                source = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ManagedImproveBridgeError("managed Improve evidence must be UTF-8 Markdown") from exc
        digest = _bytes_digest(raw)
        snapshot = _event_snapshot_path(child_id, sequence, relative, digest)
        existing = writes.get(snapshot)
        if existing is not None:
            _need(existing == source, "managed Improve evidence snapshot conflicts with this callback")
        else:
            path = _safe_path(root, snapshot, label="managed Improve evidence snapshot")
            if path.exists():
                _need(_safe_read(root, snapshot, label="managed Improve evidence snapshot") == raw, "managed Improve evidence snapshot already differs")
            writes[snapshot] = source
        replacements[relative] = snapshot
    frozen["evidence_refs"] = [replacements[relative] for relative in refs]
    completed = frozen.get("completed_pass")
    if isinstance(completed, MutableMapping):
        completed["evidence_ref"] = _replace_event_reference(completed.get("evidence_ref"), replacements)
        independent = completed.get("independent_review")
        if isinstance(independent, MutableMapping):
            independent["evidence_ref"] = _replace_event_reference(independent.get("evidence_ref"), replacements)
    fresh = frozen.get("fresh_evidence")
    if isinstance(fresh, MutableMapping):
        fresh["evidence_ref"] = _replace_event_reference(fresh.get("evidence_ref"), replacements)
        checks = fresh.get("checks")
        if isinstance(checks, list):
            for check in checks:
                if isinstance(check, MutableMapping):
                    check["evidence_ref"] = _replace_event_reference(check.get("evidence_ref"), replacements)
    return frozen


def _apply_event(
    root: Path | str,
    state: MutableMapping[str, Any],
    record: MutableMapping[str, Any],
    event: Mapping[str, Any],
    writes: MutableMapping[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    controller = _controller()
    child = controller.assert_child(record["child"])
    _need(isinstance(child, Mapping) and child.get("status") == "active", "managed Improve child is not active")
    execution = child.get("execution")
    _need(isinstance(execution, Mapping), "managed Improve child execution projection is missing")
    # The legacy typed handler has already consumed the current child action
    # and installed its proposed successor before ``persist`` reaches us. The
    # consumed action must therefore be present exactly once in its child replay
    # ledger; comparing it to the *new* transient action would reject every
    # valid transition as stale.
    action_ledger = state.get("completed_actions")
    event_kind = event.get("kind")
    if event_kind == "complete":
        _need(
            isinstance(action_ledger, Mapping) and execution.get("action") in action_ledger,
            "stale parent callback cannot advance an active managed child",
        )
    else:
        _need(
            event_kind == "repair" or event_kind in _INCOMPLETE,
            "managed Improve recovery event is unsupported",
        )
    _need(isinstance(state.get("stage"), str), "managed Improve typed handler did not select a successor stage")
    _need(event.get("phase") == child.get("current_phase"), "managed Improve event phase is stale or skipped")
    _typed_pass_matches(root, state, event, writes)
    frozen_event = _freeze_event_evidence(root, state, record, event, writes)
    try:
        updated, route = controller.apply(child, frozen_event)
    except Exception as exc:
        error_type = getattr(controller, "ManagedImproveError", ValueError)
        if isinstance(exc, error_type):
            raise ManagedImproveBridgeError(str(exc)) from exc
        raise
    updated = controller.assert_child(updated)
    _need(isinstance(updated, Mapping) and isinstance(route, Mapping), "managed Improve controller returned an invalid route")
    status = route.get("status")
    next_phase = route.get("current_phase")
    _need(status == updated.get("status") and next_phase == updated.get("current_phase"), "managed Improve controller route disagrees with child")
    if status == "active":
        # Existing typed handlers have already selected their next legacy stage.
        # The controller, not that label, is authoritative; a mismatch blocks.
        _need(state.get("stage") == next_phase, "typed handler next stage disagrees with managed Improve controller route")
        action = state.get("action")
        _need(isinstance(action, Mapping) and action.get("stage") == next_phase, "typed handler action disagrees with managed Improve controller route")
    elif status in _INCOMPLETE:
        _need(next_phase is None, "incomplete managed Improve route retains a phase")
    elif status == "converged":
        _need(next_phase is None, "converged managed Improve route retains a phase")
    else:
        raise ManagedImproveBridgeError("managed Improve controller returned an unsupported status")
    record["evidence_digests"] = _append_phase_evidence(
        root, child, record.get("evidence_digests"), updated, writes
    )
    record["child"] = _json_copy(updated, "managed Improve child")
    return record, _json_copy(route, "managed Improve controller route")


def _planning_revisit_value(root: Path | str, key: str, value: Any) -> Any:
    if key in {
        "spec_sha256", "lifecycle_sha256", "plan_sha256", "plan_wrapper_sha256",
        "behavior_sha256", "research_sha256", "research_certificate_sha256",
        "environment_sha256", "bound_plan_hash",
    }:
        _need(value == "" or (isinstance(value, str) and _SHA256.fullmatch(value)), f"managed Improve planning revisit {key} is invalid")
        return value
    if key == "research_as_of":
        _need(isinstance(value, str) and "\x00" not in value, "managed Improve planning revisit research_as_of is invalid")
        return value
    if key == "bound_plan":
        _need(isinstance(value, str) and "\x00" not in value, "managed Improve planning revisit bound plan is invalid")
        return value
    if key == "previous_planning":
        _need(isinstance(value, str) and value and "\x00" not in value, "managed Improve planning revisit archive is invalid")
        try:
            Path(value).resolve(strict=False).relative_to(_root(root))
        except (OSError, RuntimeError, ValueError) as exc:
            raise ManagedImproveBridgeError("managed Improve planning revisit archive is outside the run") from exc
        return value
    if key == "planning_epoch":
        _need(type(value) is int and value >= 1, "managed Improve planning revisit epoch is invalid")
        return value
    raise ManagedImproveBridgeError(f"managed Improve planning revisit cannot change {key}")


def _recovery_parent(
    root: Path | str,
    parent: Mapping[str, Any],
    state: Mapping[str, Any],
    event: str,
) -> dict[str, Any]:
    """Build the one explicit parent transition allowed after abandonment."""
    recovered = _json_copy(parent, "managed Improve recovery parent")
    target = _planning_revisit_target(event)
    stage = state.get("stage")
    phase = state.get("phase")
    action = state.get("action")
    _need(isinstance(stage, str) and stage and isinstance(phase, str) and phase, "managed Improve recovery cursor is invalid")
    _need(isinstance(action, Mapping) and action.get("stage") == stage, "managed Improve recovery action is invalid")
    _require_action(action.get("id"), "managed Improve recovery action")
    prior_revision = recovered.get("revision")
    current_revision = state.get("revision")
    _need(type(prior_revision) is int and type(current_revision) is int and current_revision == prior_revision + 1, "managed Improve recovery must make exactly one parent transition")

    if event == "post-inner-objective-repair":
        _need(stage == "review", "managed Improve post-inner recovery must restart product review")
        _need("objective" not in state, "managed Improve post-inner recovery did not abandon its objective")
        recovered.pop("objective", None)
        for key in _PROFILE_OVERLAY_KEYS["product"]:
            if key not in state:
                recovered.pop(key, None)
                continue
            recovered[key] = _validate_overlay_value(key, state[key], recovered)
    else:
        _need(target is not None and stage == target, "managed Improve planning revisit target disagrees with its cursor")
        for key in _PLANNING_REVISIT_CLEAR_FIELDS:
            if key in {"paused", "objective_preallocation_bridge"}:
                _need(key not in state, f"managed Improve planning revisit retained {key}")
                recovered.pop(key, None)
                continue
            if key not in state:
                recovered.pop(key, None)
                continue
            recovered[key] = _planning_revisit_value(root, key, state[key])
        if "objective" not in state:
            recovered.pop("objective", None)

    parent_actions = parent.get("completed_actions")
    _need(isinstance(parent_actions, Mapping), "managed Improve recovery parent action ledger is invalid")
    recovered["phase"] = phase
    recovered["stage"] = stage
    recovered["action"] = _json_copy(action, "managed Improve recovery action")
    recovered["completed_actions"] = _json_copy(parent_actions, "managed Improve recovery parent action ledger")
    recovered["revision"] = current_revision
    recovered.pop(STATE_KEY, None)
    recovered.pop(IMPORT_KEY, None)
    recovered.pop(PRIVATE_KEY, None)
    recovered.pop(EVIDENCE_KEY, None)
    recovered.pop("paused", None)
    recovered.pop("halt_reason", None)
    return recovered


def _cross_profile_recovery_event(event: str) -> bool:
    return event == "post-inner-objective-repair" or _planning_revisit_target(event) is not None


def _prepare_cross_profile_recovery(
    root: Path | str,
    state: MutableMapping[str, Any],
    event: str,
    writes: MutableMapping[str, str],
    deletes: list[str],
    parent: Mapping[str, Any],
    record: MutableMapping[str, Any],
    binding: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    """Abandon one child, preserve its evidence, and authorize a fresh owner."""
    _need(record.get("child", {}).get("status") == "active", "managed Improve recovery child is not active")
    recovery_event = _synthetic_recovery_event(
        root, state, record, event, "needs-replan", writes
    )
    record, route = _apply_event(root, state, record, recovery_event, writes)
    _need(route.get("status") == "needs-replan" and route.get("current_phase") is None, "managed Improve recovery did not abandon its child")
    record = _new_record(
        binding=record["binding"], input_value=record["input_identity"], child=record["child"],
        evidence_digests=record["evidence_digests"],
    )
    writes[_child_path(binding["id"])] = store.dumps(record, CHILD_TITLE)
    records = record["child"].get("phase_records")
    _need(isinstance(records, list) and records and isinstance(records[-1], Mapping), "managed Improve recovery record is invalid")
    refs = records[-1].get("evidence_refs")
    _need(isinstance(refs, list) and refs, "managed Improve recovery record has no evidence")

    recovered = _recovery_parent(root, parent, state, event)
    recovered[RECOVERY_KEY] = {
        "from_child": binding["id"],
        "from_parent_action": binding["parent_action"],
        "status": "needs-replan",
        "reason": recovery_event["reason"],
        "evidence_refs": _json_copy(refs, "managed Improve recovery evidence"),
        "to_child": None,
    }
    _replace_state(state, recovered)

    if event == "post-inner-objective-repair":
        begin(root, state, "product", recovery_writes=writes)
        new_binding = state.get(STATE_KEY)
        projection = state.get(PRIVATE_KEY)
        _need(
            isinstance(new_binding, Mapping)
            and isinstance(projection, Mapping)
            and isinstance(projection.get("parent"), Mapping)
            and isinstance(projection.get("record"), Mapping),
            "managed Improve post-inner recovery did not start its product child",
        )
        new_parent = _json_copy(projection["parent"], "managed Improve recovery product parent")
        new_record = _json_copy(projection["record"], "managed Improve recovery product child")
        new_parent[STATE_KEY] = _json_copy(new_binding, "managed Improve recovery product binding")
        new_parent["stage"] = STAGE
        new_parent["action"] = {"id": new_binding["parent_action"], "stage": STAGE}
        validate_parent(new_parent)
        writes[_child_path(new_binding["id"])] = store.dumps(new_record, CHILD_TITLE)
        _set_projection(state, new_parent, new_record)
        return new_parent, writes, deletes

    validate_parent(recovered)
    return recovered, writes, deletes


def _capture_execution(
    state: Mapping[str, Any],
    parent: Mapping[str, Any],
    record: MutableMapping[str, Any],
    *,
    terminal: bool = False,
) -> None:
    """Copy only the projected child cursor/delta back into its receipt."""
    controller = _controller()
    child = _json_copy(record["child"], "managed Improve child")
    execution = child.get("execution")
    _need(isinstance(execution, MutableMapping), "managed Improve child execution projection is missing")
    parent_actions = parent.get("completed_actions", {})
    current_actions = state.get("completed_actions", {})
    _need(isinstance(parent_actions, Mapping) and isinstance(current_actions, Mapping), "managed Improve action ledger is invalid")
    for action_id, parent_digest in parent_actions.items():
        _need(current_actions.get(action_id) == parent_digest, "managed Improve child changed a parent completion receipt")
    child_actions = {key: value for key, value in current_actions.items() if key not in parent_actions}
    phase = child.get("current_phase")
    if not terminal:
        _need(state.get("stage") == phase, "managed Improve execution stage differs from controlled phase")
    current_action = state.get("action")
    _need(isinstance(current_action, Mapping), "managed Improve execution action is invalid")
    overlay_state: Mapping[str, Any] = state
    if terminal and "halt_reason" in state:
        # Halt reason is retained in the controller's stopped record and the
        # handoff artifact.  It is not a child-authorized parent overlay.
        overlay_state = dict(state)
        overlay_state.pop("halt_reason", None)
    execution.update(
        phase=phase,
        stage=state.get("stage"),
        action=_require_action(current_action.get("id"), "managed Improve execution action"),
        completed_actions=_action_map_to_rows(child_actions, label="managed Improve child completed actions"),
        overlay=_overlay(parent, overlay_state, profile=record["binding"]["profile"]),
    )
    # Controller replay checks that phase records, status, and this adapter
    # projection agree. It never reads the overlay to decide convergence.
    record["child"] = _json_copy(controller.assert_child(child), "managed Improve child")


def _existing_certificate(root: Path | str, relative: str) -> tuple[dict[str, Any], bytes] | None:
    path = _safe_path(root, relative, label="managed Improve certificate")
    if not path.exists():
        return None
    return _read_record(root, relative, label="managed Improve certificate")


def _pending_or_existing_result(
    root: Path | str,
    relative: str,
    writes: Mapping[str, str],
    *,
    label: str,
) -> dict[str, Any] | None:
    """Read a result from this transaction first, then the durable run."""
    path = _safe_path(root, relative, label=label)
    if relative in writes:
        body = writes[relative]
        _need(isinstance(body, str), f"{label} is not text")
        try:
            value = store.loads(body)
        except store.StorageError as exc:
            raise ManagedImproveBridgeError(
                f"{label} is not a valid Markdown state record"
            ) from exc
        _need(isinstance(value, dict), f"{label} must contain an object")
        return _json_copy(value, label)
    if not path.exists():
        return None
    value, _raw = _read_record(root, relative, label=label)
    return value


def _promote_child_results(
    root: Path | str,
    completed: MutableMapping[str, Any],
    execution: Mapping[str, Any],
    writes: Mapping[str, str],
    *,
    parent_action: str,
) -> None:
    """Move verified child result fingerprints into the parent replay ledger."""
    child_actions = _action_rows_to_map(
        execution.get("completed_actions"),
        label="managed Improve child completed actions",
    )
    for action_id, result_digest in child_actions.items():
        _need(
            action_id != parent_action,
            "managed Improve child result conflicts with its parent action",
        )
        relative = f"results/{action_id}.md"
        result = _pending_or_existing_result(
            root, relative, writes, label=f"managed Improve child result {action_id}"
        )
        _need(result is not None, f"managed Improve child result {action_id} is unavailable")
        _need(
            _digest(result) == result_digest,
            f"managed Improve child result {action_id} fingerprint differs from execution receipt",
        )
        prior = completed.get(action_id)
        _need(
            prior in (None, result_digest),
            f"managed Improve child result {action_id} conflicts with parent completion ledger",
        )
        completed[action_id] = result_digest


def _parent_result_record(
    binding: Mapping[str, Any],
    certificate: Mapping[str, Any],
    certificate_relative: str,
    *,
    child_body: str,
) -> dict[str, Any]:
    """Build the ordinary result record that represents the imported child."""
    return {
        "summary": "Managed Improve converged with a controller-validated terminal certificate.",
        "status": "converged",
        "managed_improve": {
            "version": VERSION,
            "child_id": binding["id"],
            "parent_action": binding["parent_action"],
            "profile": binding["profile"],
            "child_receipt": binding["receipt"],
            "child_receipt_sha256": _bytes_digest(child_body.encode("utf-8")),
            "certificate": certificate_relative,
            "certificate_sha256": _require_sha(
                certificate.get("certificate_sha256"), "managed Improve certificate digest"
            ),
            "binding_sha256": _require_sha(
                binding.get("binding_sha256"), "managed Improve binding digest"
            ),
            "replay_key": _require_sha(
                certificate.get("replay_key"), "managed Improve certificate replay key"
            ),
        },
    }


def _certificate(
    root: Path | str,
    parent: Mapping[str, Any],
    record: Mapping[str, Any],
    writes: Mapping[str, str],
) -> tuple[dict[str, Any], str, str, dict[str, str]]:
    controller = _controller()
    child = controller.assert_child(record["child"])
    _need(isinstance(child, Mapping) and child.get("status") == "converged", "managed Improve cannot certify an incomplete child")
    _validate_phase_evidence(root, child, record.get("evidence_digests"), writes)
    certificate = controller.terminal_certificate(child)
    certificate = controller.assert_terminal_certificate(child, certificate)
    _need(isinstance(certificate, Mapping), "managed Improve controller returned an invalid certificate")
    certificate = _json_copy(certificate, "managed Improve certificate")
    binding = parent.get(STATE_KEY)
    _need(isinstance(binding, Mapping), "managed Improve parent binding is unavailable")
    for key in ("binding_sha256", "parent_action", "profile"):
        _need(certificate.get(key) == binding.get(key), f"managed Improve certificate {key} differs from active parent")
    _need(_digest(certificate.get("input_identity")) == binding.get("input_sha256"), "managed Improve certificate input identity differs from active parent")
    evidence_manifest = _certificate_evidence_manifest(root, certificate, writes)
    relative = _certificate_path(binding["id"])
    body = store.dumps(certificate, CERTIFICATE_TITLE)
    existing = _existing_certificate(root, relative)
    if existing is not None:
        existing_value, existing_raw = existing
        _need(existing_value == certificate and existing_raw == body.encode("utf-8"), "managed Improve certificate path already contains different proof")
    return certificate, relative, body, evidence_manifest


def _import_parent(
    root: Path | str,
    state: MutableMapping[str, Any],
    parent: Mapping[str, Any],
    record: Mapping[str, Any],
    certificate: Mapping[str, Any],
    certificate_relative: str,
    *,
    child_body: str,
    certificate_body: str,
    evidence_manifest: Mapping[str, str],
    writes: Mapping[str, str],
) -> tuple[dict[str, Any], str, str]:
    """Create the post-child parent state after all terminal proof checks pass."""
    binding = parent.get(STATE_KEY)
    _need(isinstance(binding, Mapping), "managed Improve parent binding is unavailable")
    # The typed adapter has selected the ordinary post-child parent cursor.
    target_action = state.get("action")
    _need(isinstance(target_action, Mapping), "managed Improve terminal import action is invalid")
    target_stage = state.get("stage")
    _need(isinstance(target_stage, str) and target_stage and target_stage != STAGE, "managed Improve terminal import lacks a parent successor")
    _need(target_action.get("stage") == target_stage, "managed Improve terminal import action stage is invalid")

    durable = _json_copy(parent, "managed Improve importing parent state")
    base_revision = durable.get("revision")
    _need(type(base_revision) is int and base_revision >= 0, "managed Improve parent revision is invalid")
    execution = record["child"].get("execution")
    _need(isinstance(execution, Mapping), "managed Improve terminal execution projection is missing")
    _apply_overlay(durable, execution.get("overlay"), profile=binding["profile"])
    recovery = durable.get(RECOVERY_KEY)
    if recovery is not None:
        handoff = _validate_recovery_metadata(recovery)
        _need(
            handoff["to_child"] == binding["id"],
            "managed Improve terminal import has an unrelated recovery handoff",
        )
        input_value = record.get("input_identity")
        _need(
            isinstance(input_value, Mapping)
            and _recovery_input_matches_handoff(input_value.get("recovery"), handoff),
            "managed Improve terminal import recovery handoff differs from its child",
        )
        # The source/destination proof remains frozen in this child receipt
        # and terminal certificate.  The active-parent marker is consumed so
        # a later, unrelated child does not inherit the completed handoff.
        durable.pop(RECOVERY_KEY)
    completed = durable.get("completed_actions")
    _need(isinstance(completed, MutableMapping), "managed Improve parent completion ledger is invalid")
    certificate_digest = _require_sha(certificate.get("certificate_sha256"), "managed Improve certificate digest")
    _promote_child_results(
        root, completed, execution, writes, parent_action=binding["parent_action"]
    )
    parent_result = _parent_result_record(
        binding, certificate, certificate_relative, child_body=child_body
    )
    parent_result_relative = f"results/{binding['parent_action']}.md"
    parent_result_digest = _digest(parent_result)
    existing_parent_result = _pending_or_existing_result(
        root,
        parent_result_relative,
        writes,
        label="managed Improve parent result",
    )
    _need(
        existing_parent_result is None or existing_parent_result == parent_result,
        "managed Improve parent result path already contains different proof",
    )
    prior = completed.get(binding["parent_action"])
    _need(
        prior in (None, parent_result_digest),
        "managed Improve parent action has a conflicting terminal import",
    )
    completed[binding["parent_action"]] = parent_result_digest
    durable["phase"] = state.get("phase")
    durable["stage"] = target_stage
    durable["action"] = _json_copy(target_action, "managed Improve terminal import action")
    durable["last_completion"] = {
        "action": binding["parent_action"],
        "stage": STAGE,
        "result_digest": parent_result_digest,
    }
    # Child callbacks deliberately do not advance the parent revision. Import
    # is the one parent transition, irrespective of how many child passes ran.
    durable["revision"] = base_revision + 1
    durable.pop(STATE_KEY, None)
    normalized_manifest: dict[str, str] = {}
    _need(isinstance(evidence_manifest, Mapping) and evidence_manifest, "managed Improve import evidence manifest is invalid")
    for relative, value in sorted(evidence_manifest.items()):
        _safe_relative(relative, label="managed Improve import evidence path")
        normalized_manifest[relative] = _require_sha(value, "managed Improve import evidence digest")
    durable[IMPORT_KEY] = {
        "version": VERSION,
        "child_receipt": binding["receipt"],
        "child_receipt_sha256": _bytes_digest(child_body.encode("utf-8")),
        "certificate": certificate_relative,
        "certificate_sha256": certificate_digest,
        "certificate_bytes_sha256": _bytes_digest(certificate_body.encode("utf-8")),
        "binding_sha256": binding["binding_sha256"],
        "replay_key": _require_sha(certificate.get("replay_key"), "managed Improve certificate replay key"),
        "profile": binding["profile"],
        "parent_action": binding["parent_action"],
        "evidence_manifest": normalized_manifest,
    }
    # A caller may carry same-turn bridge metadata while the terminal overlay is
    # being assembled.  It is never parent state and must be stripped before
    # the imported Markdown record is validated or written.
    durable.pop(PRIVATE_KEY, None)
    durable.pop(EVIDENCE_KEY, None)
    # No private projection/evidence key may cross the Markdown boundary.
    for key in tuple(durable):
        _need(not key.startswith("_"), "managed Improve private metadata cannot be imported")
    validate_parent(durable)
    return durable, parent_result_relative, store.dumps(
        parent_result, "ShipLoop managed Improve result"
    )


def validate_imported_certificate(root: Path | str, state: Mapping[str, Any]) -> dict[str, Any] | None:
    """Revalidate an imported certificate before a later parent gate relies on it."""
    imported = state.get(IMPORT_KEY)
    if imported is None:
        return None
    validate_parent(state)
    _need(isinstance(imported, Mapping), "managed Improve import receipt is invalid")
    child_record, child_raw = _read_record(root, imported["child_receipt"], label="managed Improve imported child receipt")
    _need(
        _bytes_digest(child_raw) == imported["child_receipt_sha256"],
        "managed Improve imported child receipt bytes changed",
    )
    # No active parent exists now, so validate the wrapper directly through its
    # controller binding and then compare it with the imported receipt fields.
    controller = _controller()
    _need(
        isinstance(child_record.get("binding"), Mapping)
        and isinstance(child_record.get("child"), Mapping)
        and "evidence_digests" in child_record,
        "managed Improve imported child receipt is invalid",
    )
    binding = controller.assert_binding(child_record["binding"])
    child = controller.assert_child(child_record["child"])
    _need(child.get("binding") == binding and child.get("status") == "converged", "managed Improve imported child is not converged")
    input_value = _validate_input_identity(root, child_record.get("input_identity"))
    _need(
        _digest(input_value) == binding.get("input_identity_sha256")
        and _digest(input_value["scope"]) == child_record.get("scope_inventory_sha256"),
        "managed Improve imported input identity differs from its child binding",
    )
    # A completed child has released its active-step ownership.  Later parent
    # scheduling may legally allocate a successor step, so compare only the
    # immutable run here; full scope/candidate checks apply while active.
    _validate_imported_run_scope(state, input_value)
    _validate_phase_evidence(root, child, child_record["evidence_digests"], {})
    certificate, raw = _read_record(root, imported["certificate"], label="managed Improve imported certificate")
    _need(
        _bytes_digest(raw) == imported["certificate_bytes_sha256"],
        "managed Improve imported certificate bytes changed",
    )
    checked = controller.assert_terminal_certificate(child, certificate)
    _need(
        checked.get("certificate_sha256") == imported["certificate_sha256"],
        "managed Improve imported certificate content differs",
    )
    _need(checked.get("binding_sha256") == imported["binding_sha256"], "managed Improve imported certificate binding differs")
    _need(checked.get("replay_key") == imported["replay_key"], "managed Improve imported certificate replay key differs")
    _need(checked.get("profile") == imported["profile"] and checked.get("parent_action") == imported["parent_action"], "managed Improve imported certificate parent differs")
    current_manifest = _certificate_evidence_manifest(root, checked, {})
    _need(
        current_manifest == imported["evidence_manifest"],
        "managed Improve imported evidence or output identity changed",
    )
    return _json_copy(checked, "managed Improve imported certificate")


def _replace_state(state: MutableMapping[str, Any], replacement: Mapping[str, Any]) -> None:
    state.clear()
    state.update(_json_copy(replacement, "managed Improve replacement state"))


def prepare(
    root: Path | str,
    state: MutableMapping[str, Any],
    event: str,
    writes: Mapping[str, str] | None = None,
    deletes: Sequence[str] | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    """Prepare one atomic parent/child transaction without mutating the filesystem.

    Legacy states return unchanged.  For a managed state this function either
    stages the new child, persists one child progress record while keeping the
    durable parent cursor fixed, or imports a fully verified terminal proof.
    """
    _need(isinstance(event, str) and event, "managed Improve persistence event is invalid")
    prepared_writes = dict(writes or {})
    prepared_deletes = list(deletes or [])
    validate_parent(state)
    if not enabled(state):
        return _json_copy(state, "legacy ShipLoop state"), prepared_writes, prepared_deletes

    started = _auto_start(root, state, event)
    if state.get(STATE_KEY) is None:
        return _json_copy(state, "managed-mode idle parent state"), prepared_writes, prepared_deletes

    projection = state.get(PRIVATE_KEY)
    if not isinstance(projection, Mapping) or not isinstance(projection.get("record"), Mapping):
        # A direct caller can hand us the durable parent.  Load its child once;
        # normal protocol use projects during main() before reaching persist.
        project(root, state)
        projection = state.get(PRIVATE_KEY)
    _need(isinstance(projection, Mapping) and isinstance(projection.get("parent"), Mapping) and isinstance(projection.get("record"), Mapping), "managed Improve projection is unavailable")
    parent = _json_copy(projection["parent"], "managed Improve durable parent")
    record = _json_copy(projection["record"], "managed Improve child record")
    binding = state.get(STATE_KEY)
    _need(isinstance(binding, Mapping), "managed Improve parent binding is unavailable")

    if started:
        # ``begin`` receives the already-transitioned first child phase. Build
        # its parked durable parent, then immediately restore the child view so
        # the same turn's packet and capture use the real child cursor.
        parent[STATE_KEY] = _json_copy(binding, "managed Improve parent binding")
        parent["stage"] = STAGE
        parent["action"] = {"id": binding["parent_action"], "stage": STAGE}
        _set_projection(state, parent, record)
        projection = state[PRIVATE_KEY]
        parent = _json_copy(projection["parent"], "managed Improve durable parent")
        record = _json_copy(projection["record"], "managed Improve child record")

    resuming = bool(isinstance(projection, Mapping) and projection.get("resuming") is True)
    if event == "resume" and not started and not resuming:
        child = record.get("child")
        if isinstance(child, Mapping) and (
            child.get("status") in _INCOMPLETE
            or (child.get("status") == "active" and child.get("paused") is True)
        ):
            reason, refs = _recorded_resume_arguments(record)
            record = _resume_record(
                root, state, parent, projection, record, reason=reason, evidence_refs=refs
            )
            projection = state[PRIVATE_KEY]
            parent = _json_copy(projection["parent"], "managed Improve resumed parent")
            resuming = True

    if not started:
        # The protocol holds the run lock across ``prepare`` and the one store
        # transaction.  This final read closes the stale-projection gap before
        # we prepare an overwrite of the namespaced child receipt.
        _assert_projection_current(root, parent, projection, record, allow_updated_child=resuming)

    # An automatic start began from an existing typed transition. Its first
    # phase is already selected, so that base completion is not a child review.
    child_event = state.pop(EVIDENCE_KEY, None)
    if started:
        _need(child_event is None, "managed Improve cannot apply a child event while starting")
    elif resuming:
        _need(event == "resume" and child_event is None, "managed Improve resume cannot apply a completion event")
    elif event.startswith("complete:"):
        _need(isinstance(child_event, Mapping), "managed Improve completion requires explicit typed evidence")
    elif child_event is not None:
        _need(isinstance(child_event, Mapping), "managed Improve event is invalid")

    _validate_writes(
        state, prepared_writes, prepared_deletes, record=record, recovery_event=event
    )
    _validate_phase_evidence(root, record["child"], record.get("evidence_digests"), prepared_writes)
    if _cross_profile_recovery_event(event):
        _need(not started and not resuming and child_event is None, "managed Improve cross-profile recovery cannot carry a child completion")
        return _prepare_cross_profile_recovery(
            root, state, event, prepared_writes, prepared_deletes, parent, record, binding
        )
    if child_event is None:
        recovery_kind = _recovery_kind(event, state)
        if recovery_kind is not None:
            child_event = _synthetic_recovery_event(
                root, state, record, event, recovery_kind, prepared_writes
            )
    controller_route: Mapping[str, Any] | None = None
    if isinstance(child_event, Mapping):
        record, controller_route = _apply_event(root, state, record, child_event, prepared_writes)

    child_status = record["child"].get("status")
    _need(child_status in _STATUSES, "managed Improve child has an invalid status")
    binding = dict(binding)
    binding["status"] = child_status
    state[STATE_KEY] = binding

    if child_status == "converged":
        _capture_execution(state, parent, record, terminal=True)
        # The capture must not alter controller-owned convergence evidence.
        record = _new_record(
            binding=record["binding"], input_value=record["input_identity"], child=record["child"],
            evidence_digests=record["evidence_digests"],
        )
        child_body = store.dumps(record, CHILD_TITLE)
        certificate, certificate_relative, certificate_body, evidence_manifest = _certificate(root, state, record, prepared_writes)
        prepared_writes[_child_path(binding["id"])] = child_body
        prepared_writes[certificate_relative] = certificate_body
        durable, parent_result_relative, parent_result_body = _import_parent(
            root, state, parent, record, certificate, certificate_relative,
            child_body=child_body,
            certificate_body=certificate_body,
            evidence_manifest=evidence_manifest,
            writes=prepared_writes,
        )
        prepared_writes[parent_result_relative] = parent_result_body
        _replace_state(state, durable)
        state[PRIVATE_KEY] = {"parent": _json_copy(durable, "managed Improve imported state"), "record": record, "imported": True}
        return durable, prepared_writes, prepared_deletes

    _capture_execution(state, parent, record, terminal=child_status in _INCOMPLETE)
    record = _new_record(
        binding=record["binding"], input_value=record["input_identity"], child=record["child"],
        evidence_digests=record["evidence_digests"],
    )
    prepared_writes[_child_path(binding["id"])] = store.dumps(record, CHILD_TITLE)
    durable = _json_copy(parent, "managed Improve durable parent")
    durable[STATE_KEY] = binding
    durable["stage"] = STAGE
    durable["action"] = {"id": binding["parent_action"], "stage": STAGE}
    if resuming or event == "halt":
        durable.pop("paused", None)
    elif (
        (child_status in _INCOMPLETE and event in {"pause", "step-plan-repair"})
        or (child_status == "active" and record["child"].get("paused") is True)
    ):
        paused = state.get("paused")
        _need(isinstance(paused, str) and paused.strip(), "managed Improve controller pause has no parent reason")
        durable["paused"] = paused
    validate_parent(durable)

    if child_status == "active":
        _set_projection(state, durable, record)
    else:
        _replace_state(state, durable)
        state[PRIVATE_KEY] = {"parent": _json_copy(durable, "managed Improve incomplete parent"), "record": record, "terminal": True}
    return durable, prepared_writes, prepared_deletes


__all__ = [
    "BridgeError",
    "CHILD_TITLE",
    "CONTROLLER_VERSION",
    "DIRECTORY",
    "EVIDENCE_KEY",
    "IMPORT_KEY",
    "MARKER",
    "ManagedImproveBridgeError",
    "PRIVATE_KEY",
    "STAGE",
    "STATE_KEY",
    "VERSION",
    "begin",
    "enabled",
    "initialize",
    "input_identity",
    "packet_metadata",
    "prepare",
    "project",
    "resume",
    "set_evidence",
    "validate_imported_certificate",
    "validate_parent",
]
