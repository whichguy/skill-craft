#!/usr/bin/env python3
"""Immutable Markdown event records for ShipLoop bridge intent and receipts.

This module deliberately does not acquire a lock.  Callers must hold the
ShipLoop run lock (or an equivalent external fcntl lock) across append_event.
The file name sequence, rather than either timestamp, is the ledger order.

Each canonical event is published by fsyncing a unique temporary file, adding
the canonical name with link(), and fsyncing the directory.  The source
temporary file is then unlinked and the directory is fsynced again, leaving
the canonical event as a regular file with exactly one link.  A private
.shiploop-chain-ledger-*.tmp file left before publication is ignored by
readers; it is never recovered or reused.  A crash after the hard link but
before the temporary unlink leaves a multi-link canonical file, and readers
fail closed until the caller-held lock runs recover_pending_temporary().  That
helper unlinks only the exact matching private second hardlink.  This module
does not claim power-loss or NFS guarantees.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Union

import shiploop_store as store


class LedgerError(ValueError):
    """Raised when a chain-ledger request or on-disk record is invalid."""


LedgerPath = Union[str, os.PathLike[str]]

EVENT_SCHEMA = "shiploop-chain-event/v1"
_TEMP_PREFIX = ".shiploop-chain-ledger-"
_TEMP_SUFFIX = ".tmp"
_SAFE_EVENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$", re.ASCII)
_EVENT_NAME = re.compile(
    r"^(?P<seq>[0-9]{8,})-(?P<event_id>[A-Za-z0-9][A-Za-z0-9._-]{0,127})\.md$",
    re.ASCII,
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_UTC_RFC3339 = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?Z$",
    re.ASCII,
)

__all__ = [
    "EVENT_SCHEMA",
    "LedgerError",
    "append_event",
    "read_events",
    "recover_pending_temporary",
]


def _as_directory(directory: LedgerPath) -> Path:
    try:
        return Path(directory).absolute()
    except TypeError as exc:
        raise LedgerError("ledger directory must be a filesystem path") from exc


def _directory_exists_and_is_safe(directory: Path) -> bool:
    """Return whether the ledger directory exists after rejecting unsafe kinds."""
    try:
        metadata = os.lstat(directory)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise LedgerError(f"cannot inspect ledger directory {directory}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise LedgerError(f"ledger directory must not be a symlink: {directory}")
    if not stat.S_ISDIR(metadata.st_mode):
        raise LedgerError(f"ledger path is not a directory: {directory}")
    return True


def _assert_parent_is_safe(directory: Path) -> None:
    """Reject a symlinked immediate parent before creating a ledger directory."""
    parent = directory.parent
    try:
        metadata = os.lstat(parent)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise LedgerError(f"cannot inspect ledger parent {parent}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise LedgerError(f"ledger parent must not be a symlink: {parent}")
    if not stat.S_ISDIR(metadata.st_mode):
        raise LedgerError(f"ledger parent is not a directory: {parent}")


def _fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(os.fspath(directory), flags)
    except OSError as exc:
        raise LedgerError(f"cannot open ledger directory for fsync: {directory}: {exc}") from exc
    try:
        os.fsync(fd)
    except OSError as exc:
        raise LedgerError(f"cannot fsync ledger directory {directory}: {exc}") from exc
    finally:
        os.close(fd)


def _ensure_ledger_directory(directory: Path) -> None:
    if _directory_exists_and_is_safe(directory):
        return
    _assert_parent_is_safe(directory)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise LedgerError(f"cannot create ledger directory {directory}: {exc}") from exc
    if not _directory_exists_and_is_safe(directory):
        raise LedgerError(f"cannot establish ledger directory: {directory}")
    _fsync_directory(directory.parent)


def _require_regular(path: Path, *, label: str) -> os.stat_result:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError as exc:
        raise LedgerError(f"{label} is missing: {path}") from exc
    except OSError as exc:
        raise LedgerError(f"cannot inspect {label} {path}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise LedgerError(f"{label} must not be a symlink: {path}")
    if not stat.S_ISREG(metadata.st_mode):
        raise LedgerError(f"{label} must be a regular file: {path}")
    return metadata


def _require_regular_single_link(path: Path, *, label: str) -> os.stat_result:
    metadata = _require_regular(path, label=label)
    if metadata.st_nlink != 1:
        raise LedgerError(f"{label} must have exactly one link: {path}")
    return metadata


def _read_regular_bytes(path: Path, *, label: str) -> bytes:
    _require_regular_single_link(path, label=label)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(os.fspath(path), flags)
    except OSError as exc:
        raise LedgerError(f"cannot open {label} {path}: {exc}") from exc
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise LedgerError(f"{label} changed while opening: {path}")
        with os.fdopen(fd, "rb") as handle:
            fd = -1
            return handle.read()
    except OSError as exc:
        raise LedgerError(f"cannot read {label} {path}: {exc}") from exc
    finally:
        if fd != -1:
            os.close(fd)


def _require_event_id(event_id: Any) -> str:
    if not isinstance(event_id, str) or not _SAFE_EVENT_ID.fullmatch(event_id):
        raise LedgerError(
            "event_id must match [A-Za-z0-9][A-Za-z0-9._-]{0,127}"
        )
    return event_id


def _require_kind(kind: Any) -> str:
    if not isinstance(kind, str) or not kind.strip():
        raise LedgerError("event kind must be a nonempty string")
    return kind


def _require_timestamp(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not _UTC_RFC3339.fullmatch(value):
        raise LedgerError(f"{label} must be a UTC RFC3339 timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError as exc:
        raise LedgerError(f"{label} is not a valid UTC RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise LedgerError(f"{label} must be UTC")
    return value


def _canonical_data(data: Any, *, label: str) -> str:
    if not isinstance(data, dict):
        raise LedgerError(f"{label} must be a JSON object")
    try:
        return json.dumps(
            data,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise LedgerError(f"{label} is not JSON serializable: {exc}") from exc


def _event_filename(seq: int, event_id: str) -> str:
    return f"{seq:08d}-{event_id}.md"


def _event_title(seq: int) -> str:
    return f"ShipLoop chain event {seq}"


def _render_event(event: Dict[str, Any]) -> str:
    try:
        return store.dumps(event, title=_event_title(event["seq"]))
    except (KeyError, TypeError, store.StorageError) as exc:
        raise LedgerError(f"cannot render chain event: {exc}") from exc


def _parse_event(path: Path, *, seq_from_name: int, event_id_from_name: str) -> Tuple[Dict[str, Any], str]:
    raw = _read_regular_bytes(path, label="ledger event")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LedgerError(f"ledger event is not UTF-8: {path}") from exc
    try:
        event = store.loads(text)
    except store.StorageError as exc:
        raise LedgerError(f"cannot parse ledger event {path}: {exc}") from exc
    if not isinstance(event, dict):
        raise LedgerError(f"ledger event must be a JSON object: {path}")
    _validate_event(
        event,
        path=path,
        seq_from_name=seq_from_name,
        event_id_from_name=event_id_from_name,
    )
    expected = _render_event(event).encode("utf-8")
    if raw != expected:
        raise LedgerError(f"ledger event is not canonical store Markdown: {path}")
    return event, hashlib.sha256(raw).hexdigest()


def _validate_event(
    event: Dict[str, Any],
    *,
    path: Path,
    seq_from_name: int,
    event_id_from_name: str,
) -> None:
    expected_keys = {
        "schema",
        "seq",
        "event_id",
        "kind",
        "recorded_at",
        "previous_sha256",
        "data",
    }
    actual_keys = set(event)
    if "occurred_at" in actual_keys:
        expected_keys.add("occurred_at")
    if actual_keys != expected_keys:
        raise LedgerError(f"ledger event has an unexpected schema: {path}")
    if event["schema"] != EVENT_SCHEMA:
        raise LedgerError(f"ledger event schema is unsupported: {path}")
    seq = event["seq"]
    if isinstance(seq, bool) or not isinstance(seq, int) or seq < 1:
        raise LedgerError(f"ledger event sequence is invalid: {path}")
    if seq != seq_from_name:
        raise LedgerError(f"ledger event sequence does not match filename: {path}")
    event_id = _require_event_id(event["event_id"])
    if event_id != event_id_from_name:
        raise LedgerError(f"ledger event id does not match filename: {path}")
    if _event_filename(seq, event_id) != path.name:
        raise LedgerError(f"ledger event filename is not canonical: {path}")
    _require_kind(event["kind"])
    _require_timestamp(event["recorded_at"], label="recorded_at")
    if "occurred_at" in event:
        _require_timestamp(event["occurred_at"], label="occurred_at")
    previous = event["previous_sha256"]
    if previous is not None and (
        not isinstance(previous, str) or not _SHA256.fullmatch(previous)
    ):
        raise LedgerError(f"ledger event previous_sha256 is invalid: {path}")
    _canonical_data(event["data"], label="ledger event data")


def _is_own_temporary_name(name: str) -> bool:
    return name.startswith(_TEMP_PREFIX) and name.endswith(_TEMP_SUFFIX)


def recover_pending_temporary(directory: LedgerPath) -> bool:
    """Repair only an exact private temp/canonical hardlink pair.

    The caller must hold the same external run lock used for append_event.
    Reads stay non-mutating and fail closed until this explicit recovery runs.
    A repair requires a canonical event with exactly two links and exactly one
    direct child named with this module's private temporary prefix that has the
    same device and inode, also with exactly two links.  Any unmatched,
    ambiguous, symlinked, or otherwise multi-link entry is rejected without
    unlinking it.  Canonical event bytes and names are never rewritten.
    """
    root = _as_directory(directory)
    if not _directory_exists_and_is_safe(root):
        return False
    try:
        paths = list(root.iterdir())
    except OSError as exc:
        raise LedgerError(f"cannot list ledger directory {root}: {exc}") from exc

    canonical: List[Path] = []
    temporary: Dict[Path, os.stat_result] = {}
    for path in paths:
        if _is_own_temporary_name(path.name):
            temporary[path] = _require_regular(path, label="ledger temporary")
            continue
        if _EVENT_NAME.fullmatch(path.name) is None:
            raise LedgerError(f"unexpected ledger entry: {path}")
        canonical.append(path)

    repairs: List[Tuple[Path, Path]] = []
    claimed_temporary = set()
    for path in canonical:
        metadata = _require_regular(path, label="ledger event")
        if metadata.st_nlink == 1:
            continue
        if metadata.st_nlink != 2:
            raise LedgerError(f"ledger event has an unsafe link count: {path}")
        matches = [
            temporary_path
            for temporary_path, temporary_metadata in temporary.items()
            if (
                temporary_metadata.st_nlink == 2
                and temporary_metadata.st_dev == metadata.st_dev
                and temporary_metadata.st_ino == metadata.st_ino
            )
        ]
        if len(matches) != 1 or matches[0] in claimed_temporary:
            raise LedgerError(
                f"ledger event has no unique private temporary hardlink: {path}"
            )
        repairs.append((path, matches[0]))
        claimed_temporary.add(matches[0])

    for path, metadata in temporary.items():
        if path not in claimed_temporary and metadata.st_nlink != 1:
            raise LedgerError(
                f"ledger temporary has no matching canonical event: {path}"
            )

    if not repairs:
        return False
    for event_path, temporary_path in repairs:
        event_metadata = _require_regular(event_path, label="ledger event")
        temporary_metadata = _require_regular(
            temporary_path, label="ledger temporary"
        )
        if (
            event_metadata.st_nlink != 2
            or temporary_metadata.st_nlink != 2
            or event_metadata.st_dev != temporary_metadata.st_dev
            or event_metadata.st_ino != temporary_metadata.st_ino
        ):
            raise LedgerError(
                f"ledger temporary is no longer the exact hardlink pair: "
                f"{temporary_path}"
            )
        try:
            os.unlink(temporary_path)
        except OSError as exc:
            raise LedgerError(
                f"cannot remove recovered ledger temporary {temporary_path}: {exc}"
            ) from exc
        _fsync_directory(root)
        _require_regular_single_link(event_path, label="recovered ledger event")

    # A repaired link count alone is not enough: retain fail-closed validation
    # for event shape, sequence, duplicate ids, and the hash chain.
    read_events(root)
    return True


def read_events(directory: LedgerPath) -> List[Dict[str, Any]]:
    """Read and validate all immutable chain events in sequence order.

    A missing ledger directory is a cold, empty ledger.  Only regular,
    single-link files with this module's temporary-file prefix are ignored.
    Any other non-event entry, malformed event, sequence gap, duplicate id, or
    hash-chain mismatch raises LedgerError.
    """
    root = _as_directory(directory)
    if not _directory_exists_and_is_safe(root):
        return []
    try:
        paths = list(root.iterdir())
    except OSError as exc:
        raise LedgerError(f"cannot list ledger directory {root}: {exc}") from exc

    candidates: List[Tuple[int, str, Path]] = []
    for path in paths:
        if _is_own_temporary_name(path.name):
            _require_regular_single_link(path, label="ledger temporary")
            continue
        match = _EVENT_NAME.fullmatch(path.name)
        if match is None:
            raise LedgerError(f"unexpected ledger entry: {path}")
        candidates.append(
            (int(match.group("seq")), match.group("event_id"), path)
        )

    candidates.sort(key=lambda item: item[0])
    previous_sha256: Optional[str] = None
    seen_event_ids = set()
    rows: List[Dict[str, Any]] = []
    for expected_seq, (seq_from_name, event_id_from_name, path) in enumerate(
        candidates, start=1
    ):
        if seq_from_name != expected_seq:
            raise LedgerError(
                f"ledger event sequence is not contiguous at {path}: "
                f"expected {expected_seq}, found {seq_from_name}"
            )
        event, digest = _parse_event(
            path,
            seq_from_name=seq_from_name,
            event_id_from_name=event_id_from_name,
        )
        if event_id_from_name in seen_event_ids:
            raise LedgerError(f"ledger event id is duplicated: {event_id_from_name}")
        if event["previous_sha256"] != previous_sha256:
            raise LedgerError(f"ledger hash chain is broken at {path}")
        seen_event_ids.add(event_id_from_name)
        rows.append({"event": event, "sha256": digest, "path": str(path)})
        previous_sha256 = digest
    return rows


def _replay_or_conflict(
    rows: List[Dict[str, Any]],
    *,
    event_id: str,
    kind: str,
    data_json: str,
    occurred_at: Optional[str],
    recorded_at: Optional[str],
) -> Optional[Dict[str, Any]]:
    for row in rows:
        event = row["event"]
        if event["event_id"] != event_id:
            continue
        same_payload = (
            event["kind"] == kind
            and _canonical_data(event["data"], label="ledger event data") == data_json
            and event.get("occurred_at") == occurred_at
        )
        if not same_payload:
            raise LedgerError(f"event_id {event_id!r} already has a conflicting event")
        if recorded_at is not None and event["recorded_at"] != recorded_at:
            raise LedgerError(
                f"event_id {event_id!r} already has a different recorded_at"
            )
        return row
    return None


def _new_recorded_at() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _assert_target_absent(target: Path) -> None:
    try:
        os.lstat(target)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise LedgerError(f"cannot inspect ledger target {target}: {exc}") from exc
    raise LedgerError(f"ledger event already exists; refusing to overwrite: {target}")


def _remove_unpublished_temporary(temp: Path) -> None:
    """Best-effort cleanup only for this call's not-yet-published temp file."""
    try:
        os.unlink(temp)
    except FileNotFoundError:
        return
    except OSError:
        return


def _publish_new_event(root: Path, filename: str, text: str) -> None:
    """Publish text under filename without replacing an existing entry."""
    target = root / filename
    _assert_target_absent(target)
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=_TEMP_PREFIX,
            suffix=_TEMP_SUFFIX,
            dir=os.fspath(root),
        )
    except OSError as exc:
        raise LedgerError(f"cannot create ledger temporary in {root}: {exc}") from exc

    temp = Path(temp_name)
    linked = False
    try:
        with os.fdopen(fd, "wb") as handle:
            fd = -1
            handle.write(text.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        _require_regular_single_link(temp, label="ledger temporary")
        if not _directory_exists_and_is_safe(root):
            raise LedgerError(f"ledger directory changed during publish: {root}")
        _assert_target_absent(target)
        os.link(
            os.fspath(temp),
            os.fspath(target),
            follow_symlinks=False,
        )
        linked = True
        _fsync_directory(root)
        os.unlink(temp)
        _fsync_directory(root)
        _require_regular_single_link(target, label="published ledger event")
    except LedgerError:
        raise
    except OSError as exc:
        raise LedgerError(f"cannot publish ledger event {target}: {exc}") from exc
    finally:
        if fd != -1:
            try:
                os.close(fd)
            except OSError:
                pass
        if not linked:
            _remove_unpublished_temporary(temp)


def append_event(
    directory: LedgerPath,
    event_id: str,
    kind: str,
    data: Dict[str, Any],
    *,
    occurred_at: Optional[str] = None,
    recorded_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Append one immutable event, or return its exact idempotent replay.

    event_id is the idempotency key.  A replay with identical kind, JSON data,
    and occurred_at returns the original row without rewriting its bytes.  A
    generated recorded_at is intentionally ignored for a replay.  If the
    caller supplied recorded_at, it must exactly match the original value.
    """
    root = _as_directory(directory)
    safe_event_id = _require_event_id(event_id)
    safe_kind = _require_kind(kind)
    data_json = _canonical_data(data, label="event data")
    safe_occurred_at = (
        None
        if occurred_at is None
        else _require_timestamp(occurred_at, label="occurred_at")
    )
    safe_recorded_at = (
        None
        if recorded_at is None
        else _require_timestamp(recorded_at, label="recorded_at")
    )

    # append_event has the caller-held lock required by recovery.  It can
    # therefore clear only a provable post-link temporary before reading the
    # immutable prefix; read_events itself deliberately never mutates storage.
    recover_pending_temporary(root)
    rows = read_events(root)
    replay = _replay_or_conflict(
        rows,
        event_id=safe_event_id,
        kind=safe_kind,
        data_json=data_json,
        occurred_at=safe_occurred_at,
        recorded_at=safe_recorded_at,
    )
    if replay is not None:
        return replay

    _ensure_ledger_directory(root)
    # Re-read after creating the directory so callers that obey the external
    # lock always derive the next sequence from the current immutable prefix.
    rows = read_events(root)
    replay = _replay_or_conflict(
        rows,
        event_id=safe_event_id,
        kind=safe_kind,
        data_json=data_json,
        occurred_at=safe_occurred_at,
        recorded_at=safe_recorded_at,
    )
    if replay is not None:
        return replay

    seq = len(rows) + 1
    event: Dict[str, Any] = {
        "schema": EVENT_SCHEMA,
        "seq": seq,
        "event_id": safe_event_id,
        "kind": safe_kind,
        "recorded_at": safe_recorded_at or _new_recorded_at(),
        "previous_sha256": None if not rows else rows[-1]["sha256"],
        "data": data,
    }
    if safe_occurred_at is not None:
        event["occurred_at"] = safe_occurred_at
    text = _render_event(event)
    _publish_new_event(root, _event_filename(seq, safe_event_id), text)

    published_rows = read_events(root)
    for row in published_rows:
        if row["event"]["event_id"] == safe_event_id:
            return row
    raise LedgerError(f"published ledger event cannot be read: {safe_event_id}")
