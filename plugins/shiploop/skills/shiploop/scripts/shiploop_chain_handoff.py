#!/usr/bin/env python3
"""Archive an Ask-Agent worker handoff before its worktree is cleaned up.

The dispatcher owns the archive directory and its journal.  This small module
only accepts a strictly local, untracked handoff directory inside the worker
worktree, copies its declared bytes to that archive, and later removes the
same temporary source files after proving both copies still match.  It neither
launches workers nor changes Git, dispatcher, or target state.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
from typing import Any, Mapping


class ChainHandoffError(ValueError):
    """Raised when a worker handoff cannot be safely archived or removed."""


__all__ = ["ChainHandoffError", "archive_handoff", "remove_imported_files", "validate_archive"]


_HANDOFF_SCHEMA = "shiploop-chain-handoff/v1"
_RECEIPT_SCHEMA = "shiploop-chain-import-receipt/v1"
_INTENT_SCHEMA = "shiploop-chain-import-intent/v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_ATTEMPT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,159}$")
_GIT_ENV_KEYS = frozenset(
    {
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_PARAMETERS",
    }
)


def _fail(message: str) -> None:
    raise ChainHandoffError(message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise ChainHandoffError(f"receipt is not JSON serializable: {exc}") from exc


def _path_text(value: Any, label: str) -> Path:
    try:
        raw = os.fspath(value)
    except TypeError as exc:
        raise ChainHandoffError(f"{label} must be an absolute path") from exc
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        _fail(f"{label} must be a nonempty absolute path")
    if os.path.normpath(raw) != raw:
        _fail(f"{label} must be a normalized absolute path")
    path = Path(raw)
    if not path.is_absolute() or any(part in (".", "..") for part in path.parts):
        _fail(f"{label} must be a normalized absolute path")
    return path


def _lstat(path: Path, label: str) -> os.stat_result:
    try:
        return os.lstat(path)
    except OSError as exc:
        raise ChainHandoffError(f"cannot inspect {label}: {exc}") from exc


def _no_symlinks(path: Path, label: str, *, allow_missing: bool = False) -> None:
    """Reject a link at every existing component of an absolute path."""
    if not path.is_absolute():  # Internal callers should already have normalized it.
        _fail(f"{label} must be absolute")
    cursor = Path(path.anchor)
    for index, component in enumerate(path.parts[1:], start=1):
        cursor /= component
        try:
            details = os.lstat(cursor)
        except FileNotFoundError:
            if allow_missing:
                return
            _fail(f"{label} does not exist")
        except OSError as exc:
            raise ChainHandoffError(f"cannot inspect {label}: {exc}") from exc
        if stat.S_ISLNK(details.st_mode):
            _fail(f"{label} resolves through a symlink")
        if index < len(path.parts) - 1 and not stat.S_ISDIR(details.st_mode):
            _fail(f"{label} has a non-directory parent")


def _existing_directory(value: Any, label: str) -> Path:
    path = _path_text(value, label)
    _no_symlinks(path, label)
    details = _lstat(path, label)
    if not stat.S_ISDIR(details.st_mode):
        _fail(f"{label} must be a directory")
    try:
        return path.resolve(strict=True)
    except OSError as exc:
        raise ChainHandoffError(f"cannot resolve {label}: {exc}") from exc


def _exclusive_archive_directory(value: Any, label: str) -> Path:
    """Return an existing archive root or create its missing private path safely."""
    path = _path_text(value, label)
    _no_symlinks(path, label, allow_missing=True)
    if os.path.lexists(path):
        return _existing_directory(path, label)
    cursor = path
    missing: list[str] = []
    while not os.path.lexists(cursor):
        if cursor == cursor.parent or not cursor.name:
            _fail(f"cannot find an existing parent for {label}")
        missing.append(cursor.name)
        cursor = cursor.parent
    parent = _existing_directory(cursor, label + " parent")
    for name in reversed(missing):
        child = parent / name
        try:
            os.mkdir(child, 0o700)
        except FileExistsError:
            details = _lstat(child, label)
            if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode):
                _fail(f"{label} appeared as an unsafe path")
        except OSError as exc:
            raise ChainHandoffError(f"cannot create {label}: {exc}") from exc
        parent = child
    return _existing_directory(parent, label)


def _candidate_path(value: Any, label: str) -> Path:
    path = _path_text(value, label)
    _no_symlinks(path, label, allow_missing=True)
    return path


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        _fail(f"{label} must be nonempty text")
    if len(value) > 4096:
        _fail(f"{label} is too long")
    return value


def _summary(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        _fail("handoff summary must be nonempty text")
    return value


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        _fail(f"{label} must be a lowercase SHA-256 digest")
    return value


def _commit(value: Any, label: str) -> str:
    if not isinstance(value, str) or _COMMIT.fullmatch(value) is None:
        _fail(f"{label} must be a lowercase full Git commit SHA")
    return value


def _attempt(value: Any, label: str = "attempt") -> str:
    if not isinstance(value, str) or _ATTEMPT.fullmatch(value) is None:
        _fail(f"{label} is invalid")
    return value


def _relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        _fail(f"{label} must be a nonempty slash-separated relative path")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or candidate.name in ("", ".", ".."):
        _fail(f"{label} must be a normalized relative path")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        _fail(f"{label} must be a normalized relative path")
    return value


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _expected(value: Any, workspace: Path) -> dict[str, str]:
    if not isinstance(value, Mapping):
        _fail("expected must be an object")
    required = {"run_id", "step", "attempt", "base_commit"}
    optional = {"workspace"}
    if set(value) - required - optional or not required <= set(value):
        _fail("expected has unsupported or missing fields")
    result = {
        "run_id": _text(value["run_id"], "expected.run_id"),
        "step": _text(value["step"], "expected.step"),
        "attempt": _attempt(value["attempt"], "expected.attempt"),
        "base_commit": _commit(value["base_commit"], "expected.base_commit"),
    }
    if "workspace" in value:
        expected_workspace = _existing_directory(value["workspace"], "expected.workspace")
        if expected_workspace != workspace:
            _fail("expected.workspace does not match workspace")
    return result


def _git(workspace: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    environment = dict(os.environ)
    for key in list(environment):
        if key in _GIT_ENV_KEYS or key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
            environment.pop(key, None)
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        return subprocess.run(
            ["git", "-c", "core.hooksPath=/dev/null", "-C", os.fspath(workspace), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            close_fds=True,
            env=environment,
            shell=False,
            timeout=30,
        )
    except FileNotFoundError as exc:
        raise ChainHandoffError("git is not available on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise ChainHandoffError(f"git timed out while running {' '.join(args[:2])}") from exc


def _git_workspace(workspace: Path) -> None:
    result = _git(workspace, "rev-parse", "--path-format=absolute", "--show-toplevel")
    if result.returncode:
        _fail("workspace is not a Git worktree")
    top = result.stdout.decode("utf-8", "surrogateescape").strip()
    if not top:
        _fail("Git did not return a workspace root")
    actual = _existing_directory(top, "Git workspace root")
    if actual != workspace:
        _fail("workspace must be the Git worktree root")


def _assert_untracked(workspace: Path, source: Path) -> None:
    try:
        relative = source.relative_to(workspace).as_posix()
    except ValueError:
        _fail("handoff source is outside workspace")
    result = _git(workspace, "ls-files", "--error-unmatch", "--", relative)
    if result.returncode == 0:
        _fail(f"handoff source is tracked by Git: {relative}")
    if result.returncode != 1:
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        _fail(f"cannot verify handoff source is untracked{suffix}")


def _json_object(data: bytes, label: str) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ChainHandoffError(f"{label} contains duplicate JSON key: {key!r}")
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise ValueError(f"invalid JSON constant: {value}")

    try:
        parsed = json.loads(
            data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid_constant
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError, ChainHandoffError) as exc:
        if isinstance(exc, ChainHandoffError):
            raise
        raise ChainHandoffError(f"{label} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        _fail(f"{label} must contain one JSON object")
    return parsed


def _signature(details: os.stat_result) -> dict[str, int]:
    return {
        "device": details.st_dev,
        "inode": details.st_ino,
        "size": details.st_size,
        "mtime_ns": details.st_mtime_ns,
        "ctime_ns": details.st_ctime_ns,
    }


def _regular_source(path: Path, label: str) -> tuple[dict[str, int], bytes]:
    _no_symlinks(path, label)
    before = _lstat(path, label)
    if not stat.S_ISREG(before.st_mode):
        _fail(f"{label} must be a regular file")
    if before.st_nlink != 1:
        _fail(f"{label} must not be hard-linked")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ChainHandoffError(f"cannot open {label}: {exc}") from exc
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            _fail(f"{label} is not a private regular file")
        if _signature(opened) != _signature(before):
            _fail(f"{label} changed while it was opened")
        chunks: list[bytes] = []
        while True:
            piece = os.read(descriptor, 1024 * 1024)
            if not piece:
                break
            chunks.append(piece)
        after_open = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after = _lstat(path, label)
    if _signature(after_open) != _signature(before) or _signature(after) != _signature(before):
        _fail(f"{label} changed while it was read")
    return _signature(before), b"".join(chunks)


def _source_record(path: Path, label: str, expected_digest: str | None = None) -> dict[str, Any]:
    signature, data = _regular_source(path, label)
    digest = _sha256(data)
    if expected_digest is not None and digest != expected_digest:
        _fail(f"{label} SHA-256 does not match its declaration")
    return {"path": str(path), "sha256": digest, **signature, "bytes": data}


def _verify_source_record(record: Mapping[str, Any], label: str) -> None:
    current = _source_record(Path(record["path"]), label, record["sha256"])
    for key in ("device", "inode", "size", "mtime_ns", "ctime_ns", "sha256"):
        if current[key] != record[key]:
            _fail(f"{label} changed after archival started")


def _scan_tree(root: Path, label: str) -> tuple[dict[str, Path], set[str]]:
    """List every regular file while rejecting links and special filesystem nodes."""
    _no_symlinks(root, label)
    root_details = _lstat(root, label)
    if not stat.S_ISDIR(root_details.st_mode):
        _fail(f"{label} must be a directory")
    files: dict[str, Path] = {}
    directories: set[str] = {""}

    def visit(directory: Path, relative: PurePosixPath) -> None:
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as exc:
            raise ChainHandoffError(f"cannot list {label}: {exc}") from exc
        for entry in entries:
            path = directory / entry.name
            child_relative = relative / entry.name
            relative_text = child_relative.as_posix()
            details = _lstat(path, f"{label}/{relative_text}")
            if stat.S_ISLNK(details.st_mode):
                _fail(f"{label}/{relative_text} must not be a symlink")
            if stat.S_ISDIR(details.st_mode):
                directories.add(relative_text)
                visit(path, child_relative)
            elif stat.S_ISREG(details.st_mode):
                files[relative_text] = path
            else:
                _fail(f"{label}/{relative_text} must be a regular file or directory")

    visit(root, PurePosixPath("."))
    return files, directories


def _handoff(value: Mapping[str, Any], expected: Mapping[str, str]) -> dict[str, Any]:
    required = {
        "schema",
        "run_id",
        "step",
        "attempt",
        "base_commit",
        "status",
        "commit",
        "summary",
        "files",
    }
    if set(value) != required:
        _fail("handoff must contain exactly its v1 schema keys")
    if value["schema"] != _HANDOFF_SCHEMA:
        _fail("handoff schema is unsupported")
    identity = {
        "run_id": _text(value["run_id"], "handoff.run_id"),
        "step": _text(value["step"], "handoff.step"),
        "attempt": _attempt(value["attempt"], "handoff.attempt"),
        "base_commit": _commit(value["base_commit"], "handoff.base_commit"),
    }
    for key, item in identity.items():
        if item != expected[key]:
            _fail(f"handoff {key} does not match expected identity")
    status = value["status"]
    if status not in {"SUCCEEDED", "FAILED", "BLOCKED"}:
        _fail("handoff status is invalid")
    if status == "SUCCEEDED":
        commit = _commit(value["commit"], "handoff.commit")
    elif value["commit"] is None:
        commit = None
    else:
        _fail("failed or blocked handoff commit must be null")
    rows = value["files"]
    if not isinstance(rows, list):
        _fail("handoff files must be a list")
    files: list[dict[str, str]] = []
    seen: set[str] = set()
    casefolded: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            _fail(f"handoff files[{index}] must contain exactly path and sha256")
        path = _relative_path(row["path"], f"handoff files[{index}].path")
        if path == "handoff.json":
            _fail("handoff.json is implicit and must not be declared as a result file")
        folded = path.casefold()
        if path in seen or folded in casefolded:
            _fail("handoff files contains a duplicate path")
        seen.add(path)
        casefolded.add(folded)
        files.append({"path": path, "sha256": _digest(row["sha256"], f"handoff files[{index}].sha256")})
    for path in seen:
        if any(other.startswith(path + "/") for other in seen):
            _fail("handoff files cannot use one path as another file's directory")
    return {**identity, "status": status, "commit": commit, "summary": _summary(value["summary"]), "files": files}


def _handoff_source_path(workspace: Path, attempt: str, handoff_path: Path) -> None:
    expected = workspace / ".shiploop-handoff" / attempt / "handoff.json"
    if handoff_path != expected:
        _fail("handoff path must be exactly workspace/.shiploop-handoff/<attempt>/handoff.json")
    _no_symlinks(handoff_path, "handoff path", allow_missing=True)


def _snapshot(
    workspace: Path,
    handoff_path: Path,
    handoff_digest: str,
    expected: Mapping[str, str],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    initial = _source_record(handoff_path, "handoff.json", handoff_digest)
    parsed = _handoff(_json_object(initial["bytes"], "handoff.json"), expected)
    handoff_dir = handoff_path.parent
    files, _ = _scan_tree(handoff_dir, "handoff directory")
    declared = {"handoff.json", *(row["path"] for row in parsed["files"])}
    actual = set(files)
    if actual - declared:
        _fail("handoff directory contains undeclared files: " + ", ".join(sorted(actual - declared)))
    if declared - actual:
        _fail("handoff directory is missing declared files: " + ", ".join(sorted(declared - actual)))

    records: dict[str, dict[str, Any]] = {}
    for relative in sorted(declared):
        source = files[relative]
        _assert_untracked(workspace, source)
        declared_digest = handoff_digest if relative == "handoff.json" else next(
            row["sha256"] for row in parsed["files"] if row["path"] == relative
        )
        records[relative] = _source_record(source, f"handoff source {relative}", declared_digest)
    if records["handoff.json"]["bytes"] != initial["bytes"]:
        _fail("handoff.json changed while its directory was inspected")
    return parsed, records


def _write_new(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise ChainHandoffError(f"cannot create archive file {path}: {exc}") from exc
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _mkdir_new(path: Path) -> None:
    try:
        os.mkdir(path, 0o700)
    except FileExistsError:
        raise
    except OSError as exc:
        raise ChainHandoffError(f"cannot create archive directory {path}: {exc}") from exc


def _archive_parent(target: Path, relative: str) -> Path:
    current = target / "files"
    if not current.exists():
        _mkdir_new(current)
    for component in PurePosixPath(relative).parts[:-1]:
        current /= component
        try:
            _mkdir_new(current)
        except FileExistsError:
            details = _lstat(current, f"archive directory {current}")
            if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode):
                _fail(f"archive directory is unsafe: {current}")
    return current


def _manifest_entry(record: Mapping[str, Any], kind: str) -> dict[str, Any]:
    return {
        "path": record["path"],
        "sha256": record["sha256"],
        "kind": kind,
        "device": record["device"],
        "inode": record["inode"],
        "size": record["size"],
        "mtime_ns": record["mtime_ns"],
        "ctime_ns": record["ctime_ns"],
    }


def _intent_body(
    workspace: Path,
    handoff_path: Path,
    handoff_digest: str,
    expected: Mapping[str, str],
) -> dict[str, str]:
    return {
        "schema": _INTENT_SCHEMA,
        "run_id": expected["run_id"],
        "step": expected["step"],
        "attempt": expected["attempt"],
        "base_commit": expected["base_commit"],
        "workspace": str(workspace),
        "handoff_path": str(handoff_path),
        "handoff_sha256": handoff_digest,
    }


def _receipt_body(
    workspace: Path,
    archive_dir: Path,
    target: Path,
    handoff_digest: str,
    handoff: Mapping[str, Any],
    records: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    archives = [
        {
            "path": row["path"],
            "sha256": row["sha256"],
            "archived_path": str(target / "files" / row["path"]),
        }
        for row in sorted(handoff["files"], key=lambda row: row["path"])
    ]
    manifest = [_manifest_entry(records["handoff.json"], "handoff")]
    manifest.extend(_manifest_entry(records[row["path"]], "file") for row in archives)
    return {
        "schema": _RECEIPT_SCHEMA,
        "run_id": handoff["run_id"],
        "step": handoff["step"],
        "attempt": handoff["attempt"],
        "base_commit": handoff["base_commit"],
        "workspace": str(workspace),
        "status": handoff["status"],
        "commit": handoff["commit"],
        "summary": handoff["summary"],
        "handoff": {
            "source_path": records["handoff.json"]["path"],
            "sha256": handoff_digest,
            "archived_path": str(target / "handoff.json"),
            "archived_sha256": handoff_digest,
        },
        "archives": archives,
        "deletion_manifest": manifest,
        "archive_dir": str(archive_dir),
        "receipt_path": str(target / "receipt.json"),
    }


def _read_archive(path: Path, label: str) -> bytes:
    _no_symlinks(path, label)
    details = _lstat(path, label)
    if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
        _fail(f"{label} must be a private regular archive file")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ChainHandoffError(f"cannot read {label}: {exc}") from exc
    after = _lstat(path, label)
    if _signature(after) != _signature(details):
        _fail(f"{label} changed while it was read")
    return data


def _archive_paths(handoff: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    files = {"intent.json", "handoff.json", "receipt.json"}
    directories = {"", "files"}
    for row in handoff["files"]:
        relative = row["path"]
        files.add("files/" + relative)
        parent = PurePosixPath("files") / PurePosixPath(relative).parent
        while parent.as_posix() not in (".", ""):
            directories.add(parent.as_posix())
            parent = parent.parent
    return files, directories


def _check_intent(target: Path, intent: Mapping[str, str]) -> None:
    path = target / "intent.json"
    raw = _read_archive(path, "archive intent")
    if raw != _canonical_json(intent):
        _fail("archive intent does not match this handoff identity and digest")
    if _json_object(raw, "archive intent") != intent:
        _fail("archive intent is malformed")


def _validate_partial_archive(
    target: Path,
    intent: Mapping[str, str],
    handoff: Mapping[str, Any],
    records: Mapping[str, Mapping[str, Any]],
) -> None:
    """Accept only an interrupted prefix of this exact archive transaction."""
    files, directories = _scan_tree(target, "partial archive target")
    allowed_files, allowed_directories = _archive_paths(handoff)
    allowed_files.remove("receipt.json")
    if set(files) - allowed_files:
        _fail("partial archive target contains unknown files")
    if not directories <= allowed_directories:
        _fail("partial archive target contains unknown directories")
    if "intent.json" not in files:
        _fail("partial archive target has no matching intent and must be retained for recovery")
    _check_intent(target, intent)
    for relative, record in records.items():
        archive_relative = "handoff.json" if relative == "handoff.json" else "files/" + relative
        if archive_relative in files and _sha256(
            _read_archive(files[archive_relative], "partial archived handoff file")
        ) != record["sha256"]:
            _fail("partial archive target has bytes that conflict with this handoff")


def _complete_archive(
    target: Path,
    workspace: Path,
    archive_dir: Path,
    handoff_path: Path,
    handoff_digest: str,
    expected: Mapping[str, str],
    handoff: Mapping[str, Any],
    records: Mapping[str, Mapping[str, Any]],
) -> None:
    intent = _intent_body(workspace, handoff_path, handoff_digest, expected)
    _validate_partial_archive(target, intent, handoff, records)
    archive_files = target / "files"
    if not os.path.lexists(archive_files):
        _mkdir_new(archive_files)
    else:
        details = _lstat(archive_files, "archive files directory")
        if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode):
            _fail("archive files directory is unsafe")
    archive_handoff = target / "handoff.json"
    if not os.path.lexists(archive_handoff):
        _write_new(archive_handoff, records["handoff.json"]["bytes"])
    for row in sorted(handoff["files"], key=lambda item: item["path"]):
        parent = _archive_parent(target, row["path"])
        destination = parent / PurePosixPath(row["path"]).name
        if not os.path.lexists(destination):
            _write_new(destination, records[row["path"]]["bytes"])
    for relative, record in records.items():
        _assert_untracked(workspace, Path(record["path"]))
        _verify_source_record(record, f"handoff source {relative}")
    body = _receipt_body(workspace, archive_dir, target, handoff_digest, handoff, records)
    _write_new(target / "receipt.json", _canonical_json(body))
    _make_immutable(target)


def _receipt_shape(
    receipt: Any,
    *,
    returned: bool,
    allow_missing_workspace: bool = False,
) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        _fail("receipt must be an object")
    required = {
        "schema",
        "run_id",
        "step",
        "attempt",
        "base_commit",
        "workspace",
        "status",
        "commit",
        "summary",
        "handoff",
        "archives",
        "deletion_manifest",
        "archive_dir",
        "receipt_path",
    }
    if returned:
        required.add("receipt_sha256")
    if set(receipt) != required:
        _fail("receipt has unsupported or missing fields")
    if receipt["schema"] != _RECEIPT_SCHEMA:
        _fail("receipt schema is unsupported")
    result = {
        "schema": receipt["schema"],
        "run_id": _text(receipt["run_id"], "receipt.run_id"),
        "step": _text(receipt["step"], "receipt.step"),
        "attempt": _attempt(receipt["attempt"], "receipt.attempt"),
        "base_commit": _commit(receipt["base_commit"], "receipt.base_commit"),
        "workspace": str(
            _candidate_path(receipt["workspace"], "receipt.workspace")
            if allow_missing_workspace
            else _existing_directory(receipt["workspace"], "receipt.workspace")
        ),
        "status": receipt["status"],
        "commit": receipt["commit"],
        "summary": _summary(receipt["summary"]),
        "handoff": receipt["handoff"],
        "archives": receipt["archives"],
        "deletion_manifest": receipt["deletion_manifest"],
        "archive_dir": str(_existing_directory(receipt["archive_dir"], "receipt.archive_dir")),
        "receipt_path": str(_candidate_path(receipt["receipt_path"], "receipt.receipt_path")),
    }
    if result["status"] not in {"SUCCEEDED", "FAILED", "BLOCKED"}:
        _fail("receipt status is invalid")
    if result["status"] == "SUCCEEDED":
        result["commit"] = _commit(result["commit"], "receipt.commit")
    elif result["commit"] is not None:
        _fail("failed or blocked receipt commit must be null")
    if returned:
        result["receipt_sha256"] = _digest(receipt["receipt_sha256"], "receipt.receipt_sha256")
    return result


def _validate_receipt(
    receipt: Any,
    *,
    expected: Mapping[str, str] | None = None,
    workspace: Path | None = None,
    handoff_path: Path | None = None,
    handoff_digest: str | None = None,
    check_archive: bool = True,
    require_immutable: bool = True,
    allow_missing_workspace: bool = False,
) -> dict[str, Any]:
    value = _receipt_shape(
        receipt,
        returned=True,
        allow_missing_workspace=allow_missing_workspace,
    )
    archive_dir = Path(value["archive_dir"])
    target = archive_dir / value["handoff"]["sha256"] if isinstance(value["handoff"], dict) and "sha256" in value["handoff"] else None
    handoff = value["handoff"]
    if not isinstance(handoff, dict) or set(handoff) != {"source_path", "sha256", "archived_path", "archived_sha256"}:
        _fail("receipt handoff has unsupported or missing fields")
    handoff_source = _candidate_path(handoff["source_path"], "receipt.handoff.source_path")
    declared_digest = _digest(handoff["sha256"], "receipt.handoff.sha256")
    if _digest(handoff["archived_sha256"], "receipt.handoff.archived_sha256") != declared_digest:
        _fail("receipt handoff archived digest does not match")
    if target is None:
        _fail("receipt handoff is invalid")
    expected_target = archive_dir / declared_digest
    if target != expected_target:
        _fail("receipt archive target is invalid")
    expected_handoff_archive = expected_target / "handoff.json"
    if _candidate_path(handoff["archived_path"], "receipt.handoff.archived_path") != expected_handoff_archive:
        _fail("receipt handoff archive path is invalid")
    expected_receipt_path = expected_target / "receipt.json"
    if Path(value["receipt_path"]) != expected_receipt_path:
        _fail("receipt path is invalid")
    if workspace is not None and Path(value["workspace"]) != workspace:
        _fail("receipt workspace does not match caller workspace")
    if handoff_path is not None and handoff_source != handoff_path:
        _fail("receipt handoff source path does not match caller handoff path")
    if handoff_digest is not None and declared_digest != handoff_digest:
        _fail("receipt handoff digest does not match caller digest")
    if expected is not None:
        for key in ("run_id", "step", "attempt", "base_commit"):
            if value[key] != expected[key]:
                _fail(f"receipt {key} does not match expected identity")
    expected_source_dir = Path(value["workspace"]) / ".shiploop-handoff" / value["attempt"] / "handoff.json"
    if handoff_source != expected_source_dir:
        _fail("receipt handoff source path is not owned by its workspace and attempt")

    archives = value["archives"]
    if not isinstance(archives, list):
        _fail("receipt archives must be a list")
    archive_paths: set[str] = set()
    archive_casefolded: set[str] = set()
    normalized_archives: list[dict[str, str]] = []
    for index, row in enumerate(archives):
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "archived_path"}:
            _fail(f"receipt archives[{index}] has unsupported or missing fields")
        relative = _relative_path(row["path"], f"receipt archives[{index}].path")
        if relative == "handoff.json" or relative in archive_paths or relative.casefold() in archive_casefolded:
            _fail("receipt archives contains duplicate or implicit handoff path")
        archive_paths.add(relative)
        archive_casefolded.add(relative.casefold())
        archived_path = _candidate_path(row["archived_path"], f"receipt archives[{index}].archived_path")
        if archived_path != expected_target / "files" / relative:
            _fail("receipt archive path is invalid")
        normalized_archives.append({"path": relative, "sha256": _digest(row["sha256"], f"receipt archives[{index}].sha256"), "archived_path": str(archived_path)})
    for path in archive_paths:
        if any(other.startswith(path + "/") for other in archive_paths):
            _fail("receipt archives use one path as another file's directory")
    if normalized_archives != archives:
        _fail("receipt archives are not normalized")

    manifest = value["deletion_manifest"]
    if not isinstance(manifest, list) or len(manifest) != len(normalized_archives) + 1:
        _fail("receipt deletion manifest has the wrong number of entries")
    source_entries: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(manifest):
        required = {"path", "sha256", "kind", "device", "inode", "size", "mtime_ns", "ctime_ns"}
        if not isinstance(row, dict) or set(row) != required:
            _fail(f"receipt deletion_manifest[{index}] has unsupported or missing fields")
        source = _candidate_path(row["path"], f"receipt deletion_manifest[{index}].path")
        if source in source_entries:
            _fail("receipt deletion manifest has duplicate paths")
        digest = _digest(row["sha256"], f"receipt deletion_manifest[{index}].sha256")
        if row["kind"] not in {"handoff", "file"}:
            _fail("receipt deletion manifest kind is invalid")
        integers: dict[str, int] = {}
        for key in ("device", "inode", "size", "mtime_ns", "ctime_ns"):
            item = row[key]
            if type(item) is not int or item < 0:
                _fail(f"receipt deletion manifest {key} is invalid")
            integers[key] = item
        source_entries[str(source)] = {"path": str(source), "sha256": digest, "kind": row["kind"], **integers}
    expected_sources = {
        str(handoff_source): (declared_digest, "handoff"),
        **{
            str(handoff_source.parent / row["path"]): (row["sha256"], "file")
            for row in normalized_archives
        },
    }
    if set(source_entries) != set(expected_sources):
        _fail("receipt deletion manifest does not match handoff files")
    for path, (digest, kind) in expected_sources.items():
        if source_entries[path]["sha256"] != digest or source_entries[path]["kind"] != kind:
            _fail("receipt deletion manifest does not match handoff file integrity")

    stored_path = Path(value["receipt_path"])
    stored = _json_object(_read_archive(stored_path, "archived receipt"), "archived receipt")
    body = {key: value[key] for key in value if key != "receipt_sha256"}
    if stored != body:
        _fail("archived receipt does not match supplied receipt")
    if _sha256(_canonical_json(stored)) != value["receipt_sha256"]:
        _fail("receipt SHA-256 does not match archived receipt")

    if check_archive:
        files, directories = _scan_tree(expected_target, "archive target")
        expected_files, expected_directories = _archive_paths({"files": normalized_archives})
        if set(files) != expected_files:
            _fail("archive target contains missing or unexpected files")
        if directories != expected_directories:
            _fail("archive target contains unexpected directories")
        _check_intent(
            expected_target,
            _intent_body(
                Path(value["workspace"]),
                handoff_source,
                declared_digest,
                {key: value[key] for key in ("run_id", "step", "attempt", "base_commit")},
            ),
        )
        if _sha256(_read_archive(expected_handoff_archive, "archived handoff")) != declared_digest:
            _fail("archived handoff SHA-256 does not match receipt")
        for row in normalized_archives:
            if _sha256(_read_archive(Path(row["archived_path"]), "archived result")) != row["sha256"]:
                _fail("archived result SHA-256 does not match receipt")
        if require_immutable:
            _verify_immutable(expected_target, files, directories)
    return value


def _verify_immutable(target: Path, files: Mapping[str, Path], directories: set[str]) -> None:
    for relative, path in files.items():
        details = _lstat(path, f"archive file {relative}")
        if stat.S_IMODE(details.st_mode) != 0o444:
            _fail(f"archive file is not immutable: {relative}")
    for relative in directories:
        path = target if not relative else target / relative
        details = _lstat(path, f"archive directory {relative or '.'}")
        if stat.S_IMODE(details.st_mode) != 0o555:
            _fail(f"archive directory is not immutable: {relative or '.'}")


def _make_immutable(target: Path) -> None:
    files, directories = _scan_tree(target, "new archive target")
    for path in files.values():
        try:
            os.chmod(path, 0o444)
        except OSError as exc:
            raise ChainHandoffError(f"cannot make archive file read-only: {exc}") from exc
    for relative in sorted(directories, key=lambda item: (item.count("/"), item), reverse=True):
        path = target if not relative else target / relative
        try:
            os.chmod(path, 0o555)
        except OSError as exc:
            raise ChainHandoffError(f"cannot make archive directory read-only: {exc}") from exc


def _discard_new_archive(target: Path, known_files: set[Path], known_directories: set[Path]) -> None:
    """Undo only paths this invocation reserved; unexpected paths are retained."""
    for path in sorted(known_files, key=lambda item: (len(item.parts), str(item)), reverse=True):
        if not os.path.lexists(path):
            continue
        try:
            _no_symlinks(path, "unpublished archive file")
            details = _lstat(path, "unpublished archive file")
            if stat.S_ISREG(details.st_mode):
                os.unlink(path)
        except OSError:
            pass
        except ChainHandoffError:
            pass
    for path in sorted(known_directories, key=lambda item: (len(item.parts), str(item)), reverse=True):
        if not os.path.lexists(path):
            continue
        try:
            _no_symlinks(path, "unpublished archive directory")
            details = _lstat(path, "unpublished archive directory")
            if stat.S_ISDIR(details.st_mode):
                os.rmdir(path)
        except OSError:
            pass
        except ChainHandoffError:
            pass


def _load_replay(
    archive_dir: Path,
    handoff_digest: str,
    expected: Mapping[str, str],
    workspace: Path,
    handoff_path: Path,
) -> dict[str, Any]:
    target = archive_dir / handoff_digest
    _no_symlinks(target, "archive target")
    details = _lstat(target, "archive target")
    if not stat.S_ISDIR(details.st_mode):
        _fail("archive target is not a directory")
    receipt_path = target / "receipt.json"
    body_bytes = _read_archive(receipt_path, "archived receipt")
    body = _json_object(body_bytes, "archived receipt")
    returned = {**body, "receipt_sha256": _sha256(body_bytes)}
    # receipt.json is the durable commit marker. A process can stop after it
    # is written but before chmod completes, so prove the exact archive first,
    # seal it again idempotently, then require every mode before callers may
    # use the receipt to remove worker-local source files.
    _validate_receipt(
        returned,
        expected=expected,
        workspace=workspace,
        handoff_path=handoff_path,
        handoff_digest=handoff_digest,
        require_immutable=False,
    )
    _make_immutable(target)
    return _validate_receipt(
        returned,
        expected=expected,
        workspace=workspace,
        handoff_path=handoff_path,
        handoff_digest=handoff_digest,
        require_immutable=True,
    )


def _owned_archive_paths(target: Path, handoff: Mapping[str, Any]) -> tuple[set[Path], set[Path]]:
    files = {target / "intent.json", target / "handoff.json", target / "receipt.json"}
    directories = {target, target / "files"}
    for row in handoff["files"]:
        destination = target / "files" / row["path"]
        files.add(destination)
        current = destination.parent
        while _inside(current, target):
            directories.add(current)
            if current == target:
                break
            current = current.parent
    return files, directories


def _recover_or_complete(
    target: Path,
    workspace: Path,
    archive_dir: Path,
    handoff_path: Path,
    handoff_digest: str,
    expected: Mapping[str, str],
    handoff: Mapping[str, Any],
    records: Mapping[str, Mapping[str, Any]],
    *,
    created: bool,
) -> dict[str, Any]:
    known_files, known_directories = _owned_archive_paths(target, handoff)
    try:
        if created:
            _write_new(
                target / "intent.json",
                _canonical_json(_intent_body(workspace, handoff_path, handoff_digest, expected)),
            )
        _complete_archive(
            target,
            workspace,
            archive_dir,
            handoff_path,
            handoff_digest,
            expected,
            handoff,
            records,
        )
    except BaseException:
        if created:
            _discard_new_archive(target, known_files, known_directories)
        raise
    return _load_replay(archive_dir, handoff_digest, expected, workspace, handoff_path)


def archive_handoff(
    workspace: str | os.PathLike[str],
    handoff_path: str | os.PathLike[str],
    handoff_sha256: str,
    expected: Mapping[str, Any],
    archive_dir: str | os.PathLike[str],
) -> dict[str, Any]:
    """Copy one declared worker handoff to a parent-owned immutable archive.

    ``expected`` requires ``run_id``, ``step``, ``attempt``, and
    ``base_commit``; it may also include the same absolute ``workspace`` path.
    A repeat with the same expected identity and handoff digest returns the
    persisted receipt even after the worker-local files have been removed.
    """
    source_workspace = _existing_directory(workspace, "workspace")
    requested_archive = _candidate_path(archive_dir, "archive_dir")
    if _inside(requested_archive, source_workspace) or _inside(source_workspace, requested_archive):
        _fail("archive_dir must be disjoint from the worker workspace")
    parent_archive = _exclusive_archive_directory(requested_archive, "archive_dir")
    if _inside(parent_archive, source_workspace) or _inside(source_workspace, parent_archive):
        _fail("archive_dir must be disjoint from the worker workspace")
    identity = _expected(expected, source_workspace)
    source_handoff = _candidate_path(handoff_path, "handoff_path")
    _handoff_source_path(source_workspace, identity["attempt"], source_handoff)
    digest = _digest(handoff_sha256, "handoff_sha256")
    _git_workspace(source_workspace)
    target = parent_archive / digest

    if os.path.lexists(target):
        _no_symlinks(target, "archive target")
        details = _lstat(target, "archive target")
        if not stat.S_ISDIR(details.st_mode):
            _fail("archive target is not a directory")
        if os.path.lexists(target / "receipt.json"):
            return _load_replay(parent_archive, digest, identity, source_workspace, source_handoff)
        # A complete receipt is the commit marker.  Without it, resume only a
        # matching intent whose source bytes are still available; never delete
        # a partial archive simply because it lacks a receipt.
        handoff, records = _snapshot(source_workspace, source_handoff, digest, identity)
        return _recover_or_complete(
            target,
            source_workspace,
            parent_archive,
            source_handoff,
            digest,
            identity,
            handoff,
            records,
            created=False,
        )

    handoff, records = _snapshot(source_workspace, source_handoff, digest, identity)
    try:
        _mkdir_new(target)
    except FileExistsError:
        if os.path.lexists(target / "receipt.json"):
            return _load_replay(parent_archive, digest, identity, source_workspace, source_handoff)
        return _recover_or_complete(
            target,
            source_workspace,
            parent_archive,
            source_handoff,
            digest,
            identity,
            handoff,
            records,
            created=False,
        )
    return _recover_or_complete(
        target,
        source_workspace,
        parent_archive,
        source_handoff,
        digest,
        identity,
        handoff,
        records,
        created=True,
    )


def _current_matches(entry: Mapping[str, Any]) -> bool:
    path = _candidate_path(entry["path"], "deletion manifest path")
    if not os.path.lexists(path):
        return False
    record = _source_record(path, "deletion manifest source", entry["sha256"])
    for key in ("device", "inode", "size", "mtime_ns", "ctime_ns", "sha256"):
        if record[key] != entry[key]:
            _fail("temporary handoff source changed since archive import")
    return True


def _remove_empty_directories(handoff_root: Path, manifest: list[Mapping[str, Any]]) -> tuple[list[str], list[str]]:
    candidates: set[Path] = {handoff_root}
    for entry in manifest:
        current = Path(entry["path"]).parent
        while _inside(current, handoff_root):
            candidates.add(current)
            if current == handoff_root:
                break
            current = current.parent
    removed: list[str] = []
    retained: list[str] = []
    for path in sorted(candidates, key=lambda item: (len(item.parts), str(item)), reverse=True):
        if not os.path.lexists(path):
            continue
        _no_symlinks(path, "temporary handoff directory")
        details = _lstat(path, "temporary handoff directory")
        if not stat.S_ISDIR(details.st_mode):
            _fail("temporary handoff directory changed type during cleanup")
        try:
            os.rmdir(path)
        except OSError:
            # A nonempty directory (or an unexpected filesystem failure) is
            # retained for the parent rather than being forced away.
            retained.append(str(path))
        else:
            removed.append(str(path))
    return removed, retained


def validate_archive(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Read and strictly verify a durable archive without requiring its worker.

    This deliberately performs no Git commands and does not create, chmod, or
    remove anything.  It accepts a receipt after the worker worktree is gone,
    while still proving its receipt body, declared archive tree, exact bytes,
    and immutable file and directory modes.
    """
    return _validate_receipt(receipt, allow_missing_workspace=True)


def remove_imported_files(receipt: Mapping[str, Any]) -> dict[str, list[str]]:
    """Delete only unchanged, archived worker-local temporary handoff files.

    Missing source files are treated as a recoverable prior partial cleanup.
    Changed files fail closed and are left in place.  Directories are removed
    only with ``rmdir`` after their exact recorded files have gone; unrelated
    files leave their directories retained.
    """
    checked = _validate_receipt(receipt)
    workspace = Path(checked["workspace"])
    _git_workspace(workspace)
    manifest = checked["deletion_manifest"]
    existing: list[Mapping[str, Any]] = []
    already_removed: list[str] = []
    for entry in manifest:
        if _current_matches(entry):
            _assert_untracked(workspace, Path(entry["path"]))
            existing.append(entry)
        else:
            already_removed.append(entry["path"])
    # Preflight every source before unlinking anything.  Recheck each one just
    # before unlink in case a cooperative writer raced this cleanup.
    for entry in existing:
        _current_matches(entry)
        _assert_untracked(workspace, Path(entry["path"]))
    deleted: list[str] = []
    for entry in sorted(existing, key=lambda row: (len(Path(row["path"]).parts), row["path"]), reverse=True):
        if not _current_matches(entry):
            already_removed.append(entry["path"])
            continue
        _assert_untracked(workspace, Path(entry["path"]))
        try:
            os.unlink(entry["path"])
        except FileNotFoundError:
            already_removed.append(entry["path"])
        except OSError as exc:
            raise ChainHandoffError(f"cannot remove imported temporary file {entry['path']}: {exc}") from exc
        else:
            deleted.append(entry["path"])
    handoff_root = Path(checked["handoff"]["source_path"]).parent
    directories_removed, directories_retained = _remove_empty_directories(handoff_root, manifest)
    return {
        "deleted": deleted,
        "already_removed": sorted(set(already_removed)),
        "directories_removed": directories_removed,
        "directories_retained": directories_retained,
    }
