#!/usr/bin/env python3
"""Derived planning-revision state for navigator protocol 4.

The navigator history remains the chronological authority.  This module keeps
the one reconciliation projection and archive checks separate from
consumer-specific readers so every consumer can make the same currentness
decision without storing another planning ledger.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

import shiploop_stage_spec as stage_spec

import shiploop_store as store


PLANNING_STAGES = (
    "discovery",
    "research",
    "spec",
    "test-strategy",
    "plan",
    "prepare",
)
RECONCILIATION_TARGETS = PLANNING_STAGES[:4]
_PRE_DISPATCH_STAGES = frozenset(("intake", *PLANNING_STAGES[:-1]))
_ACTION = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,159}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UTC_TIMESTAMP = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z$"
)
_EVENT_FIELDS = {
    "action", "target", "binding_id", "recorded_at", "clock_source", "receipt_sha256",
}
_RECONCILE_RESULT_FIELDS = {
    "outcome", "summary", "evidence_refs", "reconciliation_target",
}
_RECONCILE_RECEIPT_FIELDS = {"summary", "target", "evidence_refs"}
_RECEIPT_TITLE = "ShipLoop standalone Improve receipt"
_MAX_ARCHIVE_BYTES = 4 * 1024 * 1024


class PlanningRevisionError(ValueError):
    """Raised when a planning reconciliation is malformed or unavailable."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise PlanningRevisionError(message)


def _text(value: Any, label: str) -> str:
    _need(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty text")
    return value


def _receipt_bytes(record: Mapping[str, Any]) -> bytes:
    try:
        return store.dumps(dict(record), _RECEIPT_TITLE).encode("utf-8")
    except store.StorageError as exc:
        raise PlanningRevisionError("reconciliation Improve record is not serializable") from exc


def _runtime_digest(value: Any, label: str) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PlanningRevisionError(f"{label} is not JSON-safe") from exc
    return hashlib.sha256(raw).hexdigest()


def _timestamp(value: Any) -> str:
    text = _text(value, "reconciliation recorded_at")
    _need(_UTC_TIMESTAMP.fullmatch(text) is not None,
          "reconciliation recorded_at must be local UTC ISO-8601 with a Z suffix")
    try:
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as exc:
        raise PlanningRevisionError("reconciliation recorded_at is not a valid UTC timestamp") from exc
    return text


def _history_and_accepted(state: Mapping[str, Any]) -> tuple[list[Any], Mapping[str, Any]]:
    history = state.get("history")
    accepted = state.get("accepted")
    _need(isinstance(history, list), "navigator history is invalid")
    _need(isinstance(accepted, Mapping), "navigator accepted ledger is invalid")
    return history, accepted


def current_actions(state: Mapping[str, Any]) -> dict[tuple[str | None, str], str]:
    """Return the current accepted ``done`` action for each stage.

    This deliberately reads only ``history`` and ``accepted``.  It is therefore
    usable by source readers that receive a compact/synthetic state projection.
    It keeps the latest done result per (workitem, stage); a chronological
    reconcile row removes the root planning suffix beginning at its target,
    and a revise row removes its work item's results from the step plan on.
    """
    if not isinstance(state, Mapping):
        return {}
    history = state.get("history")
    accepted = state.get("accepted")
    if not isinstance(history, list) or not isinstance(accepted, Mapping):
        return {}
    result: dict[tuple[str | None, str], str] = {}
    for entry in history:
        if not isinstance(entry, Mapping):
            continue
        action = entry.get("action")
        stage = entry.get("stage")
        outcome = entry.get("outcome")
        if not isinstance(action, str) or not isinstance(stage, str):
            continue
        if outcome == "done" and action in accepted:
            workitem = entry.get("workitem")
            result[(workitem if isinstance(workitem, str) else None, stage)] = action
            continue
        if outcome == "revise":
            workitem = entry.get("workitem")
            reopened = frozenset(stage_spec.INNER[stage_spec.INNER.index(stage_spec.REVISE_TO):])
            for key in tuple(result):
                if key[0] == workitem and key[1] in reopened:
                    result.pop(key)
            continue
        if outcome != "reconcile":
            continue
        accepted_result = accepted.get(action)
        if not isinstance(accepted_result, Mapping):
            continue
        target = accepted_result.get("reconciliation_target")
        if target not in RECONCILIATION_TARGETS:
            continue
        first = PLANNING_STAGES.index(target)
        invalidated = frozenset(PLANNING_STAGES[first:])
        for key in tuple(result):
            if key[0] is None and key[1] in invalidated:
                result.pop(key)
    return result


def validate(state: Mapping[str, Any]) -> None:
    """Validate reconciliation bindings without reading a run directory."""
    _need(isinstance(state, Mapping), "navigator state must be an object")
    history, accepted = _history_and_accepted(state)
    events = state.get("planning_reconciliations")
    records = state.get("improve_results")
    run_id = state.get("run_id")
    _need(isinstance(events, list), "planning reconciliations must be a list")
    _need(isinstance(records, Mapping), "Improve results must be an object")
    _need(isinstance(run_id, str) and _ACTION.fullmatch(run_id) is not None,
          "unsafe navigator run ID")

    history_by_action: dict[str, tuple[int, Mapping[str, Any]]] = {}
    reconcile_actions: set[str] = set()
    for index, entry in enumerate(history):
        _need(isinstance(entry, Mapping), "navigator history entry is invalid")
        action = entry.get("action")
        _need(isinstance(action, str) and _ACTION.fullmatch(action) is not None,
              "navigator history action is unsafe")
        history_by_action[action] = (index, entry)
        if entry.get("outcome") == "reconcile":
            reconcile_actions.add(action)

    event_actions: set[str] = set()
    prior_history_index = -1
    for event in events:
        _need(isinstance(event, Mapping) and set(event) == _EVENT_FIELDS,
              "planning reconciliation event has an unsupported schema")
        action = event.get("action")
        target = event.get("target")
        _need(isinstance(action, str) and _ACTION.fullmatch(action) is not None,
              "planning reconciliation action is unsafe")
        _need(action not in event_actions, "planning reconciliation repeats an action")
        event_actions.add(action)
        _need(target in RECONCILIATION_TARGETS, "planning reconciliation target is invalid")
        binding_id = _text(event.get("binding_id"), "planning reconciliation binding_id")
        _need(binding_id == run_id + "/" + action,
              "planning reconciliation binding does not match its parent action")
        _timestamp(event.get("recorded_at"))
        _need(event.get("clock_source") == "local-utc",
              "planning reconciliation clock source is invalid")
        receipt_sha256 = event.get("receipt_sha256")
        _need(isinstance(receipt_sha256, str) and _SHA256.fullmatch(receipt_sha256) is not None,
              "planning reconciliation receipt digest is invalid")

        _need(action in history_by_action,
              "planning reconciliation action has no history entry")
        history_index, entry = history_by_action[action]
        _need(history_index > prior_history_index,
              "planning reconciliations must follow navigator history order")
        prior_history_index = history_index
        _need(entry.get("stage") == "plan" and entry.get("outcome") == "reconcile"
              and entry.get("workitem") is None,
              "planning reconciliation must bind a root plan reconcile result")
        result = accepted.get(action)
        _need(isinstance(result, Mapping) and set(result) == _RECONCILE_RESULT_FIELDS
              and result.get("outcome") == "reconcile"
              and result.get("reconciliation_target") == target,
              "planning reconciliation accepted result is invalid")
        result_summary = _text(result.get("summary"), "planning reconciliation result summary")
        refs = result.get("evidence_refs")
        _need(isinstance(refs, list) and all(isinstance(ref, str) and ref.strip() for ref in refs),
              "planning reconciliation evidence references are invalid")

        record = records.get(action)
        _need(isinstance(record, Mapping), "planning reconciliation Improve record is missing")
        _need(record.get("binding_id") == binding_id and record.get("action_id") == action
              and record.get("stage") == "plan" and record.get("runtime_phase") == "stopped",
              "planning reconciliation Improve record does not bind the stopped child")
        submission = record.get("submission")
        archived_receipt = record.get("receipt")
        _need(isinstance(submission, Mapping) and set(submission) == _RECONCILE_RECEIPT_FIELDS
              and submission.get("target") == target,
              "planning reconciliation submission is invalid")
        _need(submission.get("summary") == result_summary
              and submission.get("evidence_refs") == refs,
              "planning reconciliation accepted result differs from its stopped submission")
        _need(isinstance(archived_receipt, Mapping) and set(archived_receipt) == _RECONCILE_RECEIPT_FIELDS
              and archived_receipt.get("target") == target
              and archived_receipt.get("summary") == result_summary
              and isinstance(archived_receipt.get("evidence_refs"), list)
              and bool(archived_receipt["evidence_refs"])
              and all(isinstance(ref, str) and ref.strip() for ref in archived_receipt["evidence_refs"]),
              "planning reconciliation receipt is invalid")
        expected_digest = hashlib.sha256(_receipt_bytes(record)).hexdigest()
        _need(receipt_sha256 == expected_digest,
              "planning reconciliation receipt digest differs from its Improve record")

        # A reconcile is valid only while the initial planning frontier is
        # still intact.  Later states may have dispatch effects; history order
        # proves they happened after this historical event, not before it.
        for preceding in history[:history_index]:
            _need(isinstance(preceding, Mapping)
                  and preceding.get("workitem") is None
                  and preceding.get("stage") in _PRE_DISPATCH_STAGES,
                  "planning reconciliation occurred after prepare or work execution")

    _need(event_actions == reconcile_actions,
          "every reconcile history result requires one planning reconciliation event")


def _regular_file(root: Path, relative: str, label: str) -> bytes:
    """Read one immutable archive through no-follow directory descriptors.

    The archive paths are state-derived, but a later filesystem substitution
    must still fail closed rather than turn a validated lstat into a different
    file read.  The descriptor remains bound to the originally opened inode,
    and its final identity is checked again after the bounded read.
    """
    path = Path(relative)
    _need(not path.is_absolute() and bool(path.parts), f"unsafe {label} path")
    _need(all(part not in ("", ".", "..") for part in path.parts),
          f"unsafe {label} path")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    _need(nofollow != 0, "safe no-follow archive reads are unavailable")
    directory = getattr(os, "O_DIRECTORY", 0)
    nonblock = getattr(os, "O_NONBLOCK", 0)
    descriptors: list[int] = []
    try:
        try:
            current = os.open(root, os.O_RDONLY | directory | nofollow)
        except OSError as exc:
            raise PlanningRevisionError(f"{label} is unavailable") from exc
        descriptors.append(current)
        root_metadata = os.fstat(current)
        _need(stat.S_ISDIR(root_metadata.st_mode), "planning run root must be a real directory")
        for index, part in enumerate(path.parts):
            final = index == len(path.parts) - 1
            flags = os.O_RDONLY | nofollow | (nonblock if final else directory)
            try:
                opened = os.open(part, flags, dir_fd=current)
            except OSError as exc:
                raise PlanningRevisionError(f"{label} is unavailable") from exc
            descriptors.append(opened)
            metadata = os.fstat(opened)
            if not final:
                _need(stat.S_ISDIR(metadata.st_mode), f"{label} path component is not a directory")
                current = opened
                continue
            _need(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1,
                  f"{label} must be a regular single-link file")
            identity = (metadata.st_dev, metadata.st_ino)
            chunks: list[bytes] = []
            size = 0
            while True:
                try:
                    chunk = os.read(opened, min(64 * 1024, _MAX_ARCHIVE_BYTES + 1 - size))
                except OSError as exc:
                    raise PlanningRevisionError(f"cannot read {label}") from exc
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                _need(size <= _MAX_ARCHIVE_BYTES, f"{label} exceeds {_MAX_ARCHIVE_BYTES} bytes")
            final_metadata = os.fstat(opened)
            _need(stat.S_ISREG(final_metadata.st_mode) and final_metadata.st_nlink == 1
                  and (final_metadata.st_dev, final_metadata.st_ino) == identity,
                  f"{label} changed while it was read")
            return b"".join(chunks)
    except OSError as exc:
        raise PlanningRevisionError(f"{label} is unavailable") from exc
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass


def validate_archives(
    state: Mapping[str, Any], root: Path | str, writes: Mapping[str, str] | None = None,
) -> None:
    """Verify immutable stopped-child archives for a navigator state.

    This is intentionally root-aware and separate from :func:`validate`: a
    state can be syntactically sound while its required archived evidence has
    been removed or changed after the transaction completed.
    """
    validate(state)
    root_path = Path(root)
    pending = dict(writes or {})

    def archive_bytes(relative: str, label: str) -> bytes:
        path = Path(relative)
        _need(not path.is_absolute() and bool(path.parts)
              and all(part not in ("", ".", "..") for part in path.parts),
              f"unsafe {label} path")
        if relative not in pending:
            return _regular_file(root_path, relative, label)
        text = pending[relative]
        _need(isinstance(text, str), f"{label} write must be text")
        return text.encode("utf-8")

    events = state["planning_reconciliations"]
    records = state["improve_results"]
    for event in events:
        action = event["action"]
        record = records[action]
        prefix = f"improve/{action}"
        receipt_raw = archive_bytes(prefix + "/receipt.md", "reconciliation receipt")
        expected_receipt = _receipt_bytes(record)
        _need(receipt_raw == expected_receipt,
              "reconciliation receipt archive differs from its Improve record")
        _need(hashlib.sha256(receipt_raw).hexdigest() == event["receipt_sha256"],
              "reconciliation receipt archive digest differs from its event")

        identities = record.get("identities")
        _need(isinstance(identities, Mapping), "reconciliation archive identities are invalid")
        packet_digest = identities.get("terminal_packet_sha256")
        _need(isinstance(packet_digest, str) and _SHA256.fullmatch(packet_digest) is not None,
              "reconciliation terminal packet digest is invalid")
        packet_raw = archive_bytes(prefix + "/terminal.json", "reconciliation terminal packet")
        _need(hashlib.sha256(packet_raw).hexdigest() == packet_digest,
              "reconciliation terminal packet archive differs from its record")
        try:
            packet = json.loads(packet_raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PlanningRevisionError("reconciliation terminal packet archive is invalid JSON") from exc
        _need(isinstance(packet, Mapping), "reconciliation terminal packet archive is invalid")
        _need(_runtime_digest(packet.get("context"), "reconciliation terminal context")
              == identities.get("context_sha256"),
              "reconciliation terminal context digest differs from its record")
        _need(_runtime_digest(packet.get("last_report"), "reconciliation terminal report")
              == identities.get("last_report_sha256"),
              "reconciliation terminal report digest differs from its record")

        evidence_digests = identities.get("evidence_sha256")
        evidence = record.get("evidence")
        _need(isinstance(evidence_digests, Mapping) and isinstance(evidence, list) and evidence,
              "reconciliation evidence archives are invalid")
        observed_sources: dict[str, str] = {}
        observed_archives: set[str] = set()
        for row in evidence:
            _need(isinstance(row, Mapping) and set(row) == {"source", "archive", "sha256"},
                  "reconciliation evidence archive entry is invalid")
            source = _text(row.get("source"), "reconciliation evidence source")
            archive = _text(row.get("archive"), "reconciliation evidence archive")
            digest = row.get("sha256")
            _need(isinstance(digest, str) and _SHA256.fullmatch(digest) is not None,
                  "reconciliation evidence digest is invalid")
            _need(source not in observed_sources and archive not in observed_archives
                  and archive.startswith(prefix + "/evidence/"),
                  "reconciliation evidence archive is not unique or is outside its action")
            observed_sources[source] = digest
            observed_archives.add(archive)
            raw = archive_bytes(archive, "reconciliation evidence")
            _need(hashlib.sha256(raw).hexdigest() == digest,
                  "reconciliation evidence archive differs from its record")
        _need(dict(evidence_digests) == observed_sources,
              "reconciliation evidence identities differ from archived evidence")


__all__ = [
    "PLANNING_STAGES",
    "RECONCILIATION_TARGETS",
    "PlanningRevisionError",
    "current_actions",
    "validate",
    "validate_archives",
]
