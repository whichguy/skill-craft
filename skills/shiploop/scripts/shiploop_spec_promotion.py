#!/usr/bin/env python3
"""Durable, run-bound promotion of the reviewed current spec."""

from __future__ import annotations

import hashlib
import re
import stat
from pathlib import Path
from typing import Any, Mapping

import shiploop_current_spec as current_spec
import shiploop_store as store


class PromotionError(ValueError):
    """A spec promotion, reconciliation, or aggregate identity is invalid."""


SCHEMA = "shiploop-spec-promotion"
VERSION = 1
JOURNAL = "spec/promotion.md"
AGGREGATE = "docs/shiploop/spec.md"
CANDIDATE = current_spec.CANDIDATE
_ACTION_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,159}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIREMENT_ID = re.compile(r"\bR-\d+\b")
_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
_RECONCILIATION_KEYS = {"current_sha256", "prior_sha256", "summary"}
_RECORD_KEYS = {
    "schema", "version", "status", "run_id", "repo", "root", "handoff_action",
    "aggregate", "candidate", "candidate_sha256", "current_sha256", "prior_sha256",
    "prior_present", "summary",
}

__all__ = [
    "AGGREGATE",
    "CANDIDATE",
    "JOURNAL",
    "PromotionError",
    "aggregate_refusal",
    "hashes",
    "promote",
    "validate",
]


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise PromotionError(message)


def _state_root(state: Mapping[str, Any]) -> Path:
    _need(isinstance(state, Mapping), "state must be a mapping")
    value = state.get("spec_root")
    _need(isinstance(value, str) and value and Path(value).is_absolute(),
          "state has no absolute bound spec_root")
    try:
        root = Path(value).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PromotionError(f"run root does not resolve: {value}: {exc}") from exc
    _need(root.is_dir() and str(root) == value, "state spec_root is not the canonical run root")
    return root


def _context(root: Path, state: Mapping[str, Any]) -> tuple[Path, Path, str, dict[str, Any]]:
    try:
        resolved_root = Path(root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError) as exc:
        raise PromotionError(f"run root does not resolve: {root}: {exc}") from exc
    _need(resolved_root.is_dir(), f"run root is not a directory: {resolved_root}")
    bound = _state_root(state)
    _need(bound == resolved_root, "run root does not match state spec_root")
    try:
        binding = current_spec.assert_binding(resolved_root, state)
    except current_spec.SpecError as exc:
        raise PromotionError(str(exc)) from exc
    repo_value = state.get("repo")
    try:
        repo = Path(str(repo_value)).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PromotionError(f"repo does not resolve: {repo_value}: {exc}") from exc
    _need(repo.is_dir(), f"repo is not a directory: {repo}")
    run_id = state.get("run_id")
    _need(isinstance(run_id, str) and _ACTION_ID.fullmatch(run_id) is not None,
          "state has an unsafe or missing run ID")
    return resolved_root, repo, run_id, binding


def _from_state(state: Mapping[str, Any]) -> tuple[Path, Path, str, dict[str, Any]]:
    root = _state_root(state)
    return _context(root, state)


def _candidate(state: Mapping[str, Any], *, require_content: bool = True) -> tuple[bytes, str, str]:
    try:
        target = current_spec.path(state)
    except current_spec.SpecError as exc:
        raise PromotionError(str(exc)) from exc
    try:
        raw = target.read_bytes()
    except OSError as exc:
        raise PromotionError(f"cannot read current-spec candidate {target}: {exc}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PromotionError(f"current-spec candidate is not valid UTF-8: {exc}") from exc
    _need(not require_content or bool(text.strip()), "current-spec candidate must be nonblank before promotion")
    return raw, text, hashlib.sha256(raw).hexdigest()


def _prior(state: Mapping[str, Any], binding: Mapping[str, Any]) -> tuple[bool, bytes | None, str]:
    metadata = binding["snapshots"]["spec"]
    present = metadata["present"]
    if not present:
        return False, None, _EMPTY_SHA256
    try:
        text = current_spec.prior_snapshot(state, "spec")
    except current_spec.SpecError as exc:
        raise PromotionError(str(exc)) from exc
    _need(text is not None, "prior spec snapshot is missing despite a present binding")
    raw = text.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    _need(digest == metadata["sha256"], "prior spec snapshot digest changed")
    return True, raw, digest


def hashes(state: Mapping[str, Any]) -> dict[str, str]:
    """Return exact candidate and immutable prior SHA-256 digests."""
    _root, _repo, _run_id, binding = _from_state(state)
    _raw, _text, current_digest = _candidate(state, require_content=False)
    _present, _prior_raw, prior_digest = _prior(state, binding)
    return {"current_sha256": current_digest, "prior_sha256": prior_digest}


def _check_requirement_ids(prior_text: str | None, current_text: str) -> None:
    if prior_text is None:
        return
    old_ids = set(_REQUIREMENT_ID.findall(prior_text))
    new_ids = set(_REQUIREMENT_ID.findall(current_text))
    missing = sorted(old_ids - new_ids)
    _need(not missing, "current spec drops prior requirement IDs: " + ", ".join(missing))


def validate(state: Mapping[str, Any], record: Mapping[str, Any]) -> None:
    """Validate an exact reconciliation against the current and immutable prior text."""
    _need(isinstance(record, Mapping) and set(record) == _RECONCILIATION_KEYS,
          "reconciliation must contain exactly current_sha256, prior_sha256, and summary")
    current_digest = record.get("current_sha256")
    prior_digest = record.get("prior_sha256")
    summary = record.get("summary")
    _need(isinstance(current_digest, str) and _SHA256.fullmatch(current_digest) is not None,
          "reconciliation current_sha256 is invalid")
    _need(isinstance(prior_digest, str) and _SHA256.fullmatch(prior_digest) is not None,
          "reconciliation prior_sha256 is invalid")
    _need(isinstance(summary, str) and bool(summary.strip()), "reconciliation summary must be nonblank")

    actual = hashes(state)
    _need(current_digest == actual["current_sha256"], "reconciliation current hash does not match current spec")
    _need(prior_digest == actual["prior_sha256"], "reconciliation prior hash does not match the initial spec")
    prior_text = current_spec.prior_snapshot(state, "spec")
    _raw, current_text, _current_hash = _candidate(state)
    _check_requirement_ids(prior_text, current_text)


def _safe_run_file(root: Path, relative: str, *, required: bool) -> Path:
    _need(relative and "\x00" not in relative and "\\" not in relative and not relative.startswith("/"),
          f"unsafe run path: {relative!r}")
    parts = relative.split("/")
    _need(all(part not in ("", ".", "..") for part in parts), f"unsafe run path: {relative!r}")
    current = root
    for index, part in enumerate(parts):
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            if required:
                raise PromotionError(f"required promotion record is missing: {current}")
            return root.joinpath(*parts)
        except OSError as exc:
            raise PromotionError(f"cannot inspect run path {current}: {exc}") from exc
        _need(not stat.S_ISLNK(info.st_mode), f"promotion path must not contain a symlink: {current}")
        if index < len(parts) - 1:
            _need(stat.S_ISDIR(info.st_mode), f"promotion parent is not a directory: {current}")
        else:
            _need(stat.S_ISREG(info.st_mode), f"promotion record is not a regular file: {current}")
            _need(info.st_nlink == 1, f"promotion record must not be hard-linked: {current}")
    return current


def _read_journal(root: Path) -> dict[str, Any] | None:
    target = _safe_run_file(root, JOURNAL, required=False)
    try:
        target.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise PromotionError(f"cannot inspect promotion journal {target}: {exc}") from exc
    try:
        record = store.read_record(target)
    except store.StorageError as exc:
        raise PromotionError(f"malformed promotion journal {target}: {exc}") from exc
    _need(isinstance(record, dict), "promotion journal must be a record")
    return record


def _write_journal(root: Path, record: Mapping[str, Any]) -> None:
    target = _safe_run_file(root, JOURNAL, required=False)
    try:
        store.atomic_write_text(target, store.dumps(dict(record), title="ShipLoop spec promotion"))
    except store.StorageError as exc:
        raise PromotionError(f"cannot persist promotion journal {target}: {exc}") from exc


def _aggregate_file(repo: Path) -> tuple[Path, bool, bytes | None]:
    parts = AGGREGATE.split("/")
    target = repo.joinpath(*parts)
    current = repo
    for index, part in enumerate(parts):
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            return target, False, None
        except OSError as exc:
            raise PromotionError(f"cannot inspect aggregate path {current}: {exc}") from exc
        _need(not stat.S_ISLNK(info.st_mode), f"aggregate path must not contain a symlink: {current}")
        if index < len(parts) - 1:
            _need(stat.S_ISDIR(info.st_mode), f"aggregate parent is not a directory: {current}")
        else:
            _need(stat.S_ISREG(info.st_mode), f"aggregate target is not a regular file: {current}")
            _need(info.st_nlink == 1, f"aggregate target must not be hard-linked: {current}")
            try:
                return target, True, current.read_bytes()
            except OSError as exc:
                raise PromotionError(f"cannot read aggregate spec {current}: {exc}") from exc
    return target, False, None


def _ensure_aggregate_parent(repo: Path) -> Path:
    parent = repo
    for part in ("docs", "shiploop"):
        parent = parent / part
        try:
            info = parent.lstat()
        except FileNotFoundError:
            try:
                parent.mkdir()
            except OSError as exc:
                raise PromotionError(f"cannot create aggregate directory {parent}: {exc}") from exc
            try:
                info = parent.lstat()
            except OSError as exc:
                raise PromotionError(f"cannot inspect new aggregate directory {parent}: {exc}") from exc
        except OSError as exc:
            raise PromotionError(f"cannot inspect aggregate directory {parent}: {exc}") from exc
        _need(not stat.S_ISLNK(info.st_mode) and stat.S_ISDIR(info.st_mode),
              f"aggregate parent is unsafe: {parent}")
    return parent


def _same_snapshot(actual_present: bool, actual_raw: bytes | None,
                   expected_present: bool, expected_raw: bytes | None) -> bool:
    return actual_present == expected_present and (not actual_present or actual_raw == expected_raw)


def _journal_record(state: Mapping[str, Any], root: Path, repo: Path, run_id: str,
                    handoff_action: str, reconciliation: Mapping[str, Any],
                    binding: Mapping[str, Any]) -> dict[str, Any]:
    prior_present, _prior_raw, prior_digest = _prior(state, binding)
    current_digest = str(reconciliation["current_sha256"])
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "pending",
        "run_id": run_id,
        "repo": str(repo),
        "root": str(root),
        "handoff_action": handoff_action,
        "aggregate": AGGREGATE,
        "candidate": CANDIDATE,
        "candidate_sha256": current_digest,
        "current_sha256": current_digest,
        "prior_sha256": prior_digest,
        "prior_present": prior_present,
        "summary": str(reconciliation["summary"]),
    }


def _validate_journal(state: Mapping[str, Any], root: Path, repo: Path, run_id: str,
                      binding: Mapping[str, Any], record: Any,
                      handoff_action: str | None = None) -> dict[str, Any]:
    _need(isinstance(record, dict) and set(record) == _RECORD_KEYS,
          "promotion journal has an unexpected schema")
    _need(record.get("schema") == SCHEMA and type(record.get("version")) is int
          and record.get("version") == VERSION,
          "promotion journal uses an unsupported schema")
    status = record.get("status")
    _need(isinstance(status, str) and status in {"pending", "promoted"},
          "promotion journal has an invalid status")
    _need(record.get("run_id") == run_id and record.get("repo") == str(repo)
          and record.get("root") == str(root), "promotion journal identity does not match this run")
    action = record.get("handoff_action")
    _need(isinstance(action, str) and _ACTION_ID.fullmatch(action) is not None,
          "promotion journal has an invalid handoff action")
    if handoff_action is not None:
        _need(action == handoff_action, "promotion journal belongs to a different handoff action")
    _need(record.get("aggregate") == AGGREGATE and record.get("candidate") == CANDIDATE,
          "promotion journal names an unexpected source or candidate")
    _need(type(record.get("prior_present")) is bool, "promotion journal prior presence is invalid")
    metadata = binding["snapshots"]["spec"]
    _need(record["prior_present"] == metadata["present"], "promotion journal prior presence does not match binding")
    reconciliation = {
        "current_sha256": record.get("current_sha256"),
        "prior_sha256": record.get("prior_sha256"),
        "summary": record.get("summary"),
    }
    validate(state, reconciliation)
    _need(record.get("candidate_sha256") == record.get("current_sha256"),
          "promotion journal candidate byte identity does not match its reviewed hash")
    _need(record.get("prior_sha256") == (metadata["sha256"] if metadata["present"] else _EMPTY_SHA256),
          "promotion journal prior hash does not match its binding")
    return record


def _state_handoff_action(state: Mapping[str, Any]) -> str | None:
    action = state.get("action")
    if state.get("stage") != "handoff" or not isinstance(action, Mapping):
        return None
    action_id = action.get("id")
    if action.get("stage") != "handoff" or not isinstance(action_id, str) or _ACTION_ID.fullmatch(action_id) is None:
        return None
    return action_id


def _require_handoff_action(state: Mapping[str, Any], handoff_action: str) -> str:
    _need(isinstance(handoff_action, str) and _ACTION_ID.fullmatch(handoff_action) is not None,
          "handoff action ID is invalid")
    _need(_state_handoff_action(state) == handoff_action,
          "promotion must run for the state's current handoff action")
    return handoff_action


def _complete_pending(root: Path, repo: Path,
                      record: Mapping[str, Any], candidate_raw: bytes, candidate_text: str,
                      prior_present: bool, prior_raw: bytes | None) -> dict[str, Any]:
    target, present, actual_raw = _aggregate_file(repo)
    if present and actual_raw == candidate_raw:
        pass  # A previous attempt replaced the aggregate and stopped before finalizing the journal.
    else:
        _need(_same_snapshot(present, actual_raw, prior_present, prior_raw),
              "aggregate spec changed after promotion was prepared")
        _ensure_aggregate_parent(repo)
        # Recheck after directory creation and immediately before replacement.
        target, present, actual_raw = _aggregate_file(repo)
        if not (present and actual_raw == candidate_raw):
            _need(_same_snapshot(present, actual_raw, prior_present, prior_raw),
                  "aggregate spec changed before promotion write")
            try:
                store.atomic_write_text(target, candidate_text)
            except store.StorageError as exc:
                raise PromotionError(f"cannot atomically promote aggregate spec {target}: {exc}") from exc
            target, present, actual_raw = _aggregate_file(repo)
            _need(present and actual_raw == candidate_raw,
                  "aggregate spec read-back does not match the exact reviewed candidate bytes")

    promoted = {**record, "status": "promoted"}
    _write_journal(root, promoted)
    return promoted


def promote(root: Path, state: Mapping[str, Any], handoff_action: str,
            reconciliation: Mapping[str, Any]) -> dict[str, Any]:
    """Promote the reviewed full candidate with a pending journal and crash-safe retry."""
    resolved_root, repo, run_id, binding = _context(root, state)
    action = _require_handoff_action(state, handoff_action)
    validate(state, reconciliation)
    candidate_raw, candidate_text, current_digest = _candidate(state)
    prior_present, prior_raw, prior_digest = _prior(state, binding)
    _need(reconciliation["current_sha256"] == current_digest
          and reconciliation["prior_sha256"] == prior_digest,
          "reconciliation hashes changed before promotion")

    prior_record = _read_journal(resolved_root)
    if prior_record is None:
        _target, aggregate_present, aggregate_raw = _aggregate_file(repo)
        _need(_same_snapshot(aggregate_present, aggregate_raw, prior_present, prior_raw),
              "aggregate spec drifted from the exact prior snapshot; refusing promotion")
        record = _journal_record(state, resolved_root, repo, run_id, action, reconciliation, binding)
        # The pending identity reaches disk before any aggregate directory or file changes.
        _write_journal(resolved_root, record)
    else:
        record = _validate_journal(state, resolved_root, repo, run_id, binding, prior_record, action)
        _need(record["summary"] == reconciliation["summary"],
              "promotion retry reconciliation summary differs from its pending record")

    if record["status"] == "promoted":
        _target, aggregate_present, aggregate_raw = _aggregate_file(repo)
        _need(aggregate_present and aggregate_raw == candidate_raw,
              "promoted aggregate differs from its journaled candidate")
        return record

    return _complete_pending(resolved_root, repo, record, candidate_raw, candidate_text,
                             prior_present, prior_raw)


def aggregate_refusal(state: Mapping[str, Any]) -> str:
    """Refuse unjournaled aggregate edits while allowing the unchanged prior or a bound handoff retry."""
    try:
        root, repo, run_id, binding = _from_state(state)
        prior_present, prior_raw, _prior_digest = _prior(state, binding)
        _target, aggregate_present, aggregate_raw = _aggregate_file(repo)
        journal = _read_journal(root)
        if journal is None:
            return "" if _same_snapshot(aggregate_present, aggregate_raw, prior_present, prior_raw) else (
                "aggregate spec changed outside a journaled final handoff promotion")

        record = _validate_journal(state, root, repo, run_id, binding, journal)
        active_action = _state_handoff_action(state)
        if active_action is not None and active_action != record["handoff_action"]:
            return "promotion journal belongs to a different handoff action"
        if record["status"] == "pending" and _same_snapshot(
                aggregate_present, aggregate_raw, prior_present, prior_raw):
            return ""
        candidate_raw, _candidate_text, _candidate_digest = _candidate(state)
        if (record["status"] == "promoted" and prior_present and prior_raw == candidate_raw
                and _same_snapshot(aggregate_present, aggregate_raw, prior_present, prior_raw)):
            return ""
        if aggregate_present and aggregate_raw == candidate_raw and active_action == record["handoff_action"]:
            return ""
        if record["status"] == "promoted":
            return "promoted aggregate no longer matches its bound handoff record"
        return "aggregate spec is neither the exact prior snapshot nor the current journaled handoff candidate"
    except (PromotionError, current_spec.SpecError) as exc:
        return str(exc)
