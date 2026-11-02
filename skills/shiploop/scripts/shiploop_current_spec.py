#!/usr/bin/env python3
"""Run-local current-spec snapshots and their durable binding.

This module deliberately does not import the navigator or knowledge-home
modules. Its public write builders return paths relative to the run root so
callers can persist them together with navigator state through
``shiploop_store.transaction`` while holding the run lock.
"""

from __future__ import annotations

import hashlib
import re
import stat
from pathlib import Path
from typing import Any, Mapping

import shiploop_store as store


class SpecError(ValueError):
    """A current-spec binding, snapshot, or path is missing or invalid."""


STATE_VERSION = 12
MANIFEST_SCHEMA = "shiploop-current-spec"
MANIFEST_VERSION = 1
STEP_SCHEMA = "shiploop-current-spec-step"
STEP_VERSION = 1

CANDIDATE = "current-spec.md"
BINDING = "spec/binding.md"
ACCEPTED = "spec/accepted.md"
_ACTION_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,159}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_SNAPSHOTS = {
    "spec": ("docs/shiploop/spec.md", "spec/prior-spec.md"),
    "architecture": ("docs/shiploop/architecture.md", "spec/prior-architecture.md"),
    "environment": ("docs/shiploop/environment.md", "spec/prior-environment.md"),
}
_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()

__all__ = [
    "BINDING",
    "ACCEPTED",
    "accepted_text",
    "accepted_writes",
    "CANDIDATE",
    "MANIFEST_SCHEMA",
    "MANIFEST_VERSION",
    "STATE_VERSION",
    "SpecError",
    "assert_binding",
    "digest",
    "initialize_writes",
    "path",
    "prior_snapshot",
    "prior_text",
    "step_baseline",
    "step_snapshot_writes",
    "reviewed_writes",
    "check_reviewed",
    "recovery_preflight",
]


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise SpecError(message)


def _resolve_root(root: Path | str) -> Path:
    _need(not isinstance(root, str) or bool(root), "run root must be an explicit filesystem path")
    try:
        resolved = Path(root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError) as exc:
        raise SpecError(f"run root does not resolve: {root}: {exc}") from exc
    _need(resolved.is_dir(), f"run root is not a directory: {resolved}")
    return resolved


def _state(state: Mapping[str, Any]) -> tuple[str, Path]:
    _need(isinstance(state, Mapping), "state must be a mapping")
    _need(type(state.get("version")) is int and state.get("version") == STATE_VERSION,
          "current-spec storage requires navigator state version 12; older runs must start fresh")
    run_id = state.get("run_id")
    _need(isinstance(run_id, str) and _ACTION_ID.fullmatch(run_id) is not None,
          "unsafe or missing run ID")
    repo_value = state.get("repo")
    _need(isinstance(repo_value, str) and repo_value and Path(repo_value).is_absolute(),
          "repo must be an absolute path")
    try:
        repo = Path(repo_value).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise SpecError(f"repo does not resolve: {repo_value}: {exc}") from exc
    _need(repo.is_dir(), f"repo is not a directory: {repo}")
    return run_id, repo


def _bound_root(state: Mapping[str, Any]) -> Path:
    _need(isinstance(state, Mapping), "state must be a mapping")
    value = state.get("spec_root")
    _need(isinstance(value, str) and value, "state has no bound spec_root")
    _need(Path(value).is_absolute(), "state spec_root must be absolute")
    root = _resolve_root(value)
    _need(str(root) == value, "state spec_root is not the canonical absolute run root")
    return root


def _safe_file(root: Path, relative: str, *, required: bool) -> Path:
    """Resolve a known relative path without following any symlink component."""
    _need(isinstance(relative, str) and relative and "\x00" not in relative and "\\" not in relative,
          f"unsafe snapshot path: {relative!r}")
    parts = relative.split("/")
    _need(not relative.startswith("/") and all(part not in ("", ".", "..") for part in parts),
          f"unsafe snapshot path: {relative!r}")
    current = root
    for index, part in enumerate(parts):
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            if required:
                raise SpecError(f"required snapshot file is missing: {current}")
            return root.joinpath(*parts)
        except OSError as exc:
            raise SpecError(f"cannot inspect snapshot path {current}: {exc}") from exc
        _need(not stat.S_ISLNK(mode), f"snapshot path must not contain a symlink: {current}")
        if index < len(parts) - 1:
            _need(stat.S_ISDIR(mode), f"snapshot parent is not a directory: {current}")
        else:
            _need(stat.S_ISREG(mode), f"snapshot target is not a regular file: {current}")
            _need(current.stat().st_nlink == 1, f"snapshot target must not be hard-linked: {current}")
    return current


def _exists(path: Path) -> bool:
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise SpecError(f"cannot inspect snapshot path {path}: {exc}") from exc


def _read_bytes(root: Path, relative: str, *, required: bool = True) -> bytes | None:
    target = _safe_file(root, relative, required=required)
    if not _exists(target):
        return None
    try:
        return target.read_bytes()
    except OSError as exc:
        raise SpecError(f"cannot read snapshot file {target}: {exc}") from exc


def _decode(raw: bytes, label: str) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SpecError(f"{label} is not valid UTF-8: {exc}") from exc


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _source_snapshot(repo: Path, relative: str) -> tuple[bytes | None, str | None]:
    target = _safe_file(repo, relative, required=False)
    raw = _read_bytes(repo, relative, required=False)
    if raw is None:
        return None, None
    return raw, _decode(raw, f"repository source {target}")


def _read_record(root: Path, relative: str, label: str) -> Any:
    target = _safe_file(root, relative, required=True)
    try:
        return store.read_record(target)
    except store.StorageError as exc:
        raise SpecError(f"malformed {label} {target}: {exc}") from exc


def _binding_payload(run_id: str, repo: Path, root: Path, snapshots: Mapping[str, Any],
                     candidate_sha256: str) -> dict[str, Any]:
    return {
        "schema": MANIFEST_SCHEMA,
        "version": MANIFEST_VERSION,
        "run_id": run_id,
        "repo": str(repo),
        "root": str(root),
        "candidate": CANDIDATE,
        "candidate_initial_sha256": candidate_sha256,
        "snapshots": dict(snapshots),
    }


def initialize_writes(root: Path, state: Mapping[str, Any]) -> dict[str, str]:
    """Build the first run-local candidate, prior snapshots, and binding record.

    The caller persists these relative-path text writes together with state via
    ``shiploop_store.transaction``. This function never changes the repo or run
    tree. Only an unbound, fresh v12 state may initialize; existing artifacts
    or a nonempty ``spec_root`` are never reseeded.
    """
    resolved_root = _resolve_root(root)
    run_id, repo = _state(state)
    _need(state.get("spec_root") == "", "current-spec binding is already bound or has invalid spec_root")

    spec_dir = resolved_root / "spec"
    _need(not spec_dir.is_symlink(), f"run spec directory must not be a symlink: {spec_dir}")
    _need(not _exists(spec_dir), f"run spec artifacts already exist; refusing to reseed: {spec_dir}")
    candidate_path = _safe_file(resolved_root, CANDIDATE, required=False)
    _need(not _exists(candidate_path), f"current-spec candidate already exists; refusing to reseed: {candidate_path}")

    writes: dict[str, str] = {}
    snapshots: dict[str, Any] = {}
    candidate_text = ""
    for name, (source_relative, snapshot_relative) in _SNAPSHOTS.items():
        raw, text = _source_snapshot(repo, source_relative)
        if raw is None:
            snapshots[name] = {"path": snapshot_relative, "present": False, "sha256": None}
        else:
            assert text is not None
            snapshots[name] = {"path": snapshot_relative, "present": True, "sha256": _sha(raw)}
            writes[snapshot_relative] = text
        if name == "spec" and text is not None:
            candidate_text = text

    candidate_raw = candidate_text.encode("utf-8")
    writes[CANDIDATE] = candidate_text
    payload = _binding_payload(run_id, repo, resolved_root, snapshots, _sha(candidate_raw))
    writes[BINDING] = store.dumps(payload, title="ShipLoop current-spec binding")
    writes[ACCEPTED] = store.dumps({"schema": "shiploop-spec-accepted-v1", "run_id": run_id,
                                   "repo": str(repo), "root": str(resolved_root), "action": None,
                                   "sha256": _sha(candidate_raw), "text": candidate_text},
                                  title="ShipLoop accepted requirement intent")
    return writes


def _validate_snapshot_entries(root: Path, payload: Any) -> dict[str, Any]:
    _need(isinstance(payload, dict), "current-spec binding must be a record")
    expected = {"schema", "version", "run_id", "repo", "root", "candidate", "candidate_initial_sha256", "snapshots"}
    _need(set(payload) == expected, "current-spec binding has an unexpected schema")
    _need(payload.get("schema") == MANIFEST_SCHEMA and type(payload.get("version")) is int
          and payload.get("version") == MANIFEST_VERSION,
          "current-spec binding uses an unsupported schema")
    _need(payload.get("candidate") == CANDIDATE, "current-spec binding names an unexpected candidate")
    _need(isinstance(payload.get("candidate_initial_sha256"), str)
          and _SHA256.fullmatch(payload["candidate_initial_sha256"]) is not None,
          "current-spec binding has an invalid initial candidate digest")

    snapshots = payload.get("snapshots")
    _need(isinstance(snapshots, dict) and set(snapshots) == set(_SNAPSHOTS),
          "current-spec binding must name spec, architecture, and environment snapshots")
    for name, (_source_relative, expected_path) in _SNAPSHOTS.items():
        item = snapshots[name]
        _need(isinstance(item, dict) and set(item) == {"path", "present", "sha256"},
              f"current-spec binding has malformed {name} snapshot metadata")
        _need(item.get("path") == expected_path, f"current-spec binding has unsafe {name} snapshot path")
        present = item.get("present")
        _need(type(present) is bool, f"current-spec binding has invalid {name} snapshot presence")
        digest_value = item.get("sha256")
        if present:
            _need(isinstance(digest_value, str) and _SHA256.fullmatch(digest_value) is not None,
                  f"current-spec binding has invalid {name} snapshot digest")
            raw = _read_bytes(root, expected_path)
            assert raw is not None
            _decode(raw, f"prior {name} snapshot")
            _need(_sha(raw) == digest_value, f"prior {name} snapshot digest does not match its binding")
        else:
            _need(digest_value is None, f"absent {name} snapshot must not have a digest")
            target = _safe_file(root, expected_path, required=False)
            _need(not _exists(target), f"absent {name} snapshot unexpectedly exists: {target}")

    spec_snapshot = snapshots["spec"]
    expected_initial = spec_snapshot["sha256"] if spec_snapshot["present"] else _EMPTY_SHA256
    _need(payload["candidate_initial_sha256"] == expected_initial,
          "current-spec initial candidate digest does not match the prior spec snapshot")
    return snapshots


def assert_binding(root: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    """Validate v12 state identity and all immutable prior snapshots."""
    resolved_root = _resolve_root(root)
    run_id, repo = _state(state)
    bound_root = _bound_root(state)
    _need(bound_root == resolved_root, "run root does not match state spec_root")

    payload = _read_record(resolved_root, BINDING, "current-spec binding")
    _need(isinstance(payload, dict), "current-spec binding must be a record")
    _need(payload.get("run_id") == run_id, "current-spec binding run ID does not match state")
    _need(payload.get("repo") == str(repo), "current-spec binding repo does not match state")
    _need(payload.get("root") == str(resolved_root), "current-spec binding root does not match run root")
    snapshots = _validate_snapshot_entries(resolved_root, payload)

    candidate_raw = _read_bytes(resolved_root, CANDIDATE)
    assert candidate_raw is not None
    _decode(candidate_raw, "current-spec candidate")
    # The initial digest is provenance; the candidate may evolve. The last
    # accepted text preserves IDs introduced during this run as well as prior runs.
    _accepted_record(resolved_root, state, payload)
    return {**payload, "snapshots": snapshots}


def path(state: Mapping[str, Any]) -> Path:
    """Return the bound candidate path after validating the binding and file."""
    root = _bound_root(state)
    assert_binding(root, state)
    return _safe_file(root, CANDIDATE, required=True)


def prior_snapshot(state: Mapping[str, Any], name: str) -> str | None:
    """Return an immutable prior snapshot, or ``None`` when it was absent at init."""
    _need(isinstance(name, str) and name in _SNAPSHOTS,
          "prior snapshot name must be spec, architecture, or environment")
    root = _bound_root(state)
    metadata = assert_binding(root, state)["snapshots"][name]
    if not metadata["present"]:
        return None
    raw = _read_bytes(root, metadata["path"])
    assert raw is not None
    return _decode(raw, f"prior {name} snapshot")


def prior_text(state: Mapping[str, Any]) -> str:
    """Return the prior aggregate spec, using empty text for an explicitly absent source."""
    return prior_snapshot(state, "spec") or ""


def digest(state: Mapping[str, Any]) -> str:
    """Return the SHA-256 digest of the candidate's exact current UTF-8 bytes."""
    root = _bound_root(state)
    assert_binding(root, state)
    raw = _read_bytes(root, CANDIDATE)
    assert raw is not None
    return _sha(raw)


def _step_paths(plan_action: str) -> tuple[str, str]:
    _need(isinstance(plan_action, str) and _ACTION_ID.fullmatch(plan_action) is not None,
          "unsafe step-plan action ID")
    base = f"spec/steps/{plan_action}"
    return base + ".md", base + ".manifest.md"


def _step_payload(run_id: str, repo: Path, root: Path, plan_action: str,
                  baseline_relative: str, baseline_raw: bytes) -> dict[str, Any]:
    return {
        "schema": STEP_SCHEMA,
        "version": STEP_VERSION,
        "run_id": run_id,
        "repo": str(repo),
        "root": str(root),
        "plan_action": plan_action,
        "baseline": baseline_relative,
        "sha256": _sha(baseline_raw),
    }


def _read_step(root: Path, state: Mapping[str, Any], plan_action: str,
               baseline_relative: str, manifest_relative: str) -> tuple[dict[str, Any], bytes]:
    run_id, repo = _state(state)
    payload = _read_record(root, manifest_relative, "step current-spec manifest")
    expected = {"schema", "version", "run_id", "repo", "root", "plan_action", "baseline", "sha256"}
    _need(isinstance(payload, dict) and set(payload) == expected,
          "step current-spec manifest has an unexpected schema")
    _need(payload.get("schema") == STEP_SCHEMA and type(payload.get("version")) is int
          and payload.get("version") == STEP_VERSION,
          "step current-spec manifest uses an unsupported schema")
    _need(payload.get("run_id") == run_id and payload.get("repo") == str(repo)
          and payload.get("root") == str(root) and payload.get("plan_action") == plan_action,
          "step current-spec manifest identity does not match this run and plan action")
    _need(payload.get("baseline") == baseline_relative, "step current-spec manifest has an unsafe baseline path")
    _need(isinstance(payload.get("sha256"), str) and _SHA256.fullmatch(payload["sha256"]) is not None,
          "step current-spec manifest has an invalid digest")
    raw = _read_bytes(root, baseline_relative)
    assert raw is not None
    _decode(raw, "step current-spec baseline")
    _need(_sha(raw) == payload["sha256"], "step current-spec baseline digest does not match its manifest")
    return payload, raw


def step_snapshot_writes(state: Mapping[str, Any], plan_action: str) -> dict[str, str]:
    """Build a once-only snapshot of the current candidate for an accepted step plan.

    A complete existing snapshot is validated and left untouched, even when
    the live candidate has since advanced. A partial, malformed, or tampered
    snapshot fails closed.
    """
    baseline_relative, manifest_relative = _step_paths(plan_action)
    root = _bound_root(state)
    assert_binding(root, state)
    run_id, repo = _state(state)
    baseline_raw = _read_bytes(root, CANDIDATE)
    assert baseline_raw is not None
    baseline_text = _decode(baseline_raw, "current-spec candidate")

    baseline_path = _safe_file(root, baseline_relative, required=False)
    manifest_path = _safe_file(root, manifest_relative, required=False)
    baseline_exists, manifest_exists = _exists(baseline_path), _exists(manifest_path)
    if baseline_exists or manifest_exists:
        _need(baseline_exists and manifest_exists, "step current-spec snapshot is incomplete; refusing to replace it")
        _read_step(root, state, plan_action, baseline_relative, manifest_relative)
        return {}

    payload = _step_payload(run_id, repo, root, plan_action, baseline_relative, baseline_raw)
    return {
        baseline_relative: baseline_text,
        manifest_relative: store.dumps(payload, title="ShipLoop step current-spec baseline"),
    }


def step_baseline(state: Mapping[str, Any], plan_action: str) -> str:
    """Read and validate the immutable current-spec content accepted for a step plan."""
    baseline_relative, manifest_relative = _step_paths(plan_action)
    root = _bound_root(state)
    assert_binding(root, state)
    _payload, raw = _read_step(root, state, plan_action, baseline_relative, manifest_relative)
    return _decode(raw, "step current-spec baseline")


REVIEWED = "spec/reviewed.md"


def reviewed_writes(state: Mapping[str, Any], action: str, expected_sha256: str) -> dict[str, str]:
    """Bind the current spec to a successfully imported Improve in the state transaction."""
    root = _bound_root(state)
    binding = assert_binding(root, state)
    _need(isinstance(action, str) and _ACTION_ID.fullmatch(action) is not None, "unsafe reviewed action ID")
    _need(action in state.get("improve_results", {}) and action in state.get("accepted", {})
          and state["accepted"][action].get("outcome") == "done",
          "current spec review must name an accepted completed Improve")
    raw = _read_bytes(root, CANDIDATE)
    assert raw is not None
    _need(isinstance(expected_sha256, str) and _SHA256.fullmatch(expected_sha256) is not None,
          "accepted current-spec review has no valid pass digest")
    _need(_sha(raw) == expected_sha256,
          "RUN/current-spec.md changed before its Improve acceptance was recorded; restart and review the current "
          "spec again before importing it")
    record = {"schema": "shiploop-spec-reviewed-v1", "run_id": binding["run_id"], "repo": binding["repo"],
              "root": binding["root"], "action": action, "sha256": expected_sha256}
    return {REVIEWED: store.dumps(record, "ShipLoop accepted current-spec review")}


def check_reviewed(state: Mapping[str, Any]) -> None:
    """Refuse terminal promotion of bytes changed since the last accepted review."""
    root = _bound_root(state)
    binding = assert_binding(root, state)
    record = _read_record(root, REVIEWED, "accepted current-spec review")
    _need(isinstance(record, dict) and set(record) == {"schema", "run_id", "repo", "root", "action", "sha256"}
          and record.get("schema") == "shiploop-spec-reviewed-v1", "invalid accepted current-spec review")
    _need(all(record.get(key) == binding[key] for key in ("run_id", "repo", "root")),
          "accepted current-spec review belongs to another run")
    action = record.get("action")
    _need(isinstance(action, str) and action in state.get("improve_results", {})
          and action in state.get("accepted", {}) and state["accepted"][action].get("outcome") == "done",
          "current-spec review is not an accepted completed Improve")
    _need(record.get("sha256") == digest(state),
          "RUN/current-spec.md changed after its accepted Improve. Restore the reviewed spec from that review's "
          "snapshot, or report add-work for a corrective item and review it before handoff; no aggregate was promoted")


def recovery_preflight(root: Path, state: Mapping[str, Any], writes: Mapping[str, str]) -> None:
    """Validate a pending navigator transaction's identity before replaying any file.

    Initial creation may have stopped before state or snapshots reached disk.
    Its complete journal supplies those exact files; ordinary transitions must
    already have a valid binding and may not reseed immutable prior content.
    """
    resolved = _resolve_root(root)
    run_id, repo = _state(state)
    _need(_bound_root(state) == resolved, "pending transaction belongs to another spec_root")
    if BINDING not in writes:
        _need(CANDIDATE not in writes and not any(relative in writes for _source, relative in _SNAPSHOTS.values()),
              "ordinary transaction cannot reseed current or prior spec files")
        binding = assert_binding(resolved, state)
        if ACCEPTED in writes:
            _validate_accepted(store.loads(writes[ACCEPTED]), state, binding)
        return
    try:
        binding = store.loads(writes[BINDING])
    except store.StorageError as exc:
        raise SpecError("pending initialization has malformed current-spec binding") from exc
    expected = {"schema", "version", "run_id", "repo", "root", "candidate", "candidate_initial_sha256", "snapshots"}
    _need(isinstance(binding, dict) and set(binding) == expected
          and binding.get("schema") == MANIFEST_SCHEMA and type(binding.get("version")) is int
          and binding.get("version") == MANIFEST_VERSION,
          "pending initialization has invalid current-spec binding")
    _need(binding.get("run_id") == run_id and binding.get("repo") == str(repo)
          and binding.get("root") == str(resolved) and binding.get("candidate") == CANDIDATE,
          "pending initialization binding belongs to another run")
    if (resolved / BINDING).exists():
        _need(_read_record(resolved, BINDING, "current-spec binding") == binding,
              "pending initialization would replace a different current-spec binding")
    snapshots = binding.get("snapshots")
    _need(isinstance(snapshots, dict) and set(snapshots) == set(_SNAPSHOTS), "pending initialization has invalid snapshots")
    for name, (_source, relative) in _SNAPSHOTS.items():
        entry = snapshots[name]
        _need(isinstance(entry, dict) and set(entry) == {"path", "present", "sha256"}
              and entry.get("path") == relative and type(entry.get("present")) is bool,
              "pending initialization has invalid " + name + " metadata")
        if entry["present"]:
            _need(relative in writes, "pending initialization lacks prior " + name + " bytes")
            _need(_sha(writes[relative].encode("utf-8")) == entry["sha256"],
                  "pending prior " + name + " digest does not match its binding")
        else:
            _need(entry["sha256"] is None and relative not in writes and not (resolved / relative).exists(),
                  "pending absent prior " + name + " unexpectedly has content")
    initial = snapshots["spec"]["sha256"] if snapshots["spec"]["present"] else _EMPTY_SHA256
    _need(binding["candidate_initial_sha256"] == initial and CANDIDATE in writes
          and _sha(writes[CANDIDATE].encode("utf-8")) == initial,
          "pending initial candidate does not match exact prior content")
    _need(ACCEPTED in writes, "pending initialization lacks accepted intent")
    accepted = _validate_accepted(store.loads(writes[ACCEPTED]), state, binding)
    _need(accepted["sha256"] == initial and accepted["action"] is None,
          "pending accepted intent does not match initial content")


def _accepted_record(root: Path, state: Mapping[str, Any], binding: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_accepted(_read_record(root, ACCEPTED, "accepted requirement intent"), state, binding)


def _validate_accepted(record: Any, state: Mapping[str, Any], binding: Mapping[str, Any]) -> dict[str, Any]:
    _need(isinstance(record, dict) and set(record) == {"schema", "run_id", "repo", "root", "action", "sha256", "text"}
          and record.get("schema") == "shiploop-spec-accepted-v1", "invalid accepted requirement snapshot")
    _need(all(record.get(key) == binding[key] for key in ("run_id", "repo", "root")),
          "accepted requirement snapshot belongs to another run")
    _need(isinstance(record.get("text"), str) and _sha(record["text"].encode("utf-8")) == record.get("sha256"),
          "accepted requirement snapshot digest does not match its text")
    action = record.get("action")
    _need(action is None or isinstance(action, str) and action in state.get("accepted", {})
          and state["accepted"][action].get("outcome") == "done",
          "requirement snapshot does not name an accepted done result")
    return record


def accepted_text(state: Mapping[str, Any]) -> str:
    """The last accepted candidate text; file changes and send-backs never advance it."""
    root = _bound_root(state)
    binding = assert_binding(root, state)
    return _accepted_record(root, state, binding)["text"]


def accepted_writes(state: Mapping[str, Any], action: str) -> dict[str, str]:
    """Advance accepted intent only with a newly accepted done result, in its state transaction."""
    root = _bound_root(state)
    binding = assert_binding(root, state)
    old = _accepted_record(root, state, binding)
    _need(action in state.get("accepted", {}) and state["accepted"][action].get("outcome") == "done",
          "accepted intent needs a completed accepted action")
    raw = _read_bytes(root, CANDIDATE)
    assert raw is not None
    if _sha(raw) == old["sha256"]:
        return {}
    record = {**old, "action": action, "sha256": _sha(raw), "text": _decode(raw, "current spec")}
    return {ACCEPTED: store.dumps(record, "ShipLoop accepted requirement intent")}
