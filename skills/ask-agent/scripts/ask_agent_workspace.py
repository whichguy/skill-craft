#!/usr/bin/env python3
"""Verify, prepare, inspect, and conservatively close Ask Agent Git workspaces.

This is deliberately a small, local Git/filesystem boundary.  It does not
launch models, poll workers, schedule work, merge contributions, or decide
whether a worker's report is semantically acceptable.  Those remain parent and
native-host responsibilities.  Its durable records live outside both the
caller checkout and the removable worker worktree.
"""

from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator, Mapping, Sequence


RECEIPT_SCHEMA = "ask-agent.workspace.receipt.v1"
BASELINE_SCHEMA = "ask-agent.workspace.baseline.v1"
INSPECTION_SCHEMA = "ask-agent.workspace.inspection.v1"
DELIVERY_SCHEMA = "ask-agent.workspace.delivery.v1"
ACCEPTANCE_SCHEMA = "ask-agent.acceptance.v1"
CONTEXT_SCHEMA = "ask-agent.workspace.context.v1"
SKILL_IDENTITY_SCHEMA = "ask-agent.skill.identity.v1"
MANAGED_WORKTREE_CAPABILITIES_SCHEMA = "shiploop-chain-ask-agent-managed-worktree/v1"
MANAGED_WORKTREE_CAPABILITIES = (
    "helper-managed-worktree",
    "prepared-inspection",
    "returned-commit-delivery",
    "fingerprint-bound-close",
    "ignored-output-report",
)
VERSION = 1
# Derived evidence (contribution patch, inspection and delivery records) is
# stored per fingerprint and reused.  It lives one level below the stable
# `inspections/` and `delivery-evidence/` roots, in a directory named for the
# derivation version, so a helper whose fix changes how evidence is derived
# never reuses a copy an earlier version produced (0.7.4 and earlier wrote
# `inspections/<fingerprint>` directly).  Bump this when derivation changes.
EVIDENCE_DERIVATION = "v3"
SHA256_RE = re.compile(r"[0-9a-f]{64}")
GIT_SHA_RE = re.compile(r"[0-9a-f]{40,64}")
SEMVER_RE = re.compile(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)
MAX_SKILL_CARD_BYTES = 1024 * 1024
PROTECTED_PARTS = frozenset({".git", ".ask-agent", ".worktrees"})
GIT_CONTEXT_ENVIRONMENT = frozenset({
    "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_GLOBAL",
    "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM", "GIT_NAMESPACE",
})


class WorkspaceError(RuntimeError):
    """The requested operation cannot safely continue."""


def _fail(message: str) -> None:
    raise WorkspaceError(message)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        _fail(f"cannot read {path}: {exc}")
    return digest.hexdigest()


def _resolve_regular_file_allowing_symlink(path: Path, *, label: str) -> Path:
    """Resolve a selected path while allowing its host-installed symlink chain."""
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        _fail(f"cannot resolve {label}: {exc}")
    try:
        info = resolved.lstat()
    except OSError as exc:
        _fail(f"cannot inspect {label}: {exc}")
    if not stat.S_ISREG(info.st_mode):
        _fail(f"{label} must resolve to a regular file: {path}")
    return resolved


def _skill_card_version(card: Path) -> str:
    """Read a constrained scalar version without evaluating YAML or imports."""
    try:
        size = card.stat().st_size
    except OSError as exc:
        _fail(f"cannot inspect selected skill card: {exc}")
    if size > MAX_SKILL_CARD_BYTES:
        _fail("selected skill card is too large to parse safely")
    try:
        raw = card.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _fail(f"cannot read selected skill card as UTF-8: {exc}")
    if "\x00" in text:
        _fail("selected skill card has invalid frontmatter")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        _fail("selected skill card has no valid frontmatter")
    try:
        closing = next(index for index, line in enumerate(lines[1:], start=1) if line == "---")
    except StopIteration:
        _fail("selected skill card has unterminated frontmatter")
    version_lines = [line for line in lines[1:closing] if line.startswith("version:")]
    if len(version_lines) != 1:
        _fail("selected skill card must declare exactly one top-level version")
    value = version_lines[0][len("version:"):].strip()
    if value.startswith(("\"", "'")):
        quote = value[0]
        closing_quote = value.find(quote, 1)
        if closing_quote <= 1:
            _fail("selected skill card has malformed version metadata")
        trailing = value[closing_quote + 1:]
        if trailing.strip() and not re.fullmatch(r"[ \t]+#.*", trailing):
            _fail("selected skill card has malformed version metadata")
        value = value[1:closing_quote]
    else:
        comment = re.search(r"[ \t]+#", value)
        if comment is not None:
            value = value[:comment.start()].rstrip()
    if not SEMVER_RE.fullmatch(value):
        _fail("selected skill card has malformed semantic version metadata")
    return value


def identity(*, skill_card: Path) -> dict[str, Any]:
    """Prove that a host-selected card belongs to this executing helper package."""
    if not skill_card.is_absolute():
        _fail("selected skill card must be an absolute path")
    if skill_card.name != "SKILL.md":
        _fail("selected skill card must name SKILL.md")
    resolved_card = _resolve_regular_file_allowing_symlink(skill_card, label="selected skill card")
    resolved_helper = _resolve_regular_file_allowing_symlink(Path(__file__), label="executing workspace helper")
    if resolved_helper.name != "ask_agent_workspace.py" or resolved_helper.parent.name != "scripts":
        _fail("executing workspace helper is outside an Ask Agent package scripts directory")
    helper_root = resolved_helper.parent.parent
    package_card = _resolve_regular_file_allowing_symlink(
        helper_root / "SKILL.md",
        label="executing helper package skill card",
    )
    if resolved_card.parent != helper_root or resolved_card != package_card:
        _fail("selected skill card does not resolve to the executing helper package")
    return {
        "status": "verified",
        "schema": SKILL_IDENTITY_SCHEMA,
        "skill_card": os.fspath(skill_card),
        "resolved_skill_card": os.fspath(resolved_card),
        "resolved_helper": os.fspath(resolved_helper),
        "version": _skill_card_version(resolved_card),
        "skill_card_sha256": _sha256_file(resolved_card),
        "helper_sha256": _sha256_file(resolved_helper),
    }


def capabilities(*, skill_card: Path) -> dict[str, Any]:
    """Declare the verified helper interface without creating workspace state."""
    verified_identity = identity(skill_card=skill_card)
    return {
        "schema": MANAGED_WORKTREE_CAPABILITIES_SCHEMA,
        "version": verified_identity["version"],
        "capabilities": list(MANAGED_WORKTREE_CAPABILITIES),
    }


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _canonical_existing_directory(path: Path, *, label: str) -> Path:
    try:
        if path.is_symlink():
            _fail(f"{label} is a symlink: {path}")
        result = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        _fail(f"cannot resolve {label}: {exc}")
    if not result.is_dir() or result.is_symlink():
        _fail(f"{label} is not a real directory: {path}")
    return result


def _canonical_existing_file(path: Path, *, label: str) -> Path:
    try:
        info = path.lstat()
    except OSError as exc:
        _fail(f"cannot inspect {label}: {exc}")
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        _fail(f"{label} must be a regular non-symlink file: {path}")
    try:
        return path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        _fail(f"cannot resolve {label}: {exc}")


def _make_private_directory(path: Path, *, label: str) -> Path:
    """Create a directory tree while rejecting symlinks at owned boundaries."""
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    # Canonicalize existing system parents (for example macOS /var), then own
    # every component we create below that point.
    existing = candidate
    missing: list[str] = []
    while not existing.exists():
        missing.append(existing.name)
        existing = existing.parent
    parent = _canonical_existing_directory(existing, label=f"parent of {label}")
    for part in reversed(missing):
        parent = parent / part
        try:
            parent.mkdir(mode=0o700)
        except FileExistsError:
            pass
        try:
            info = parent.lstat()
        except OSError as exc:
            _fail(f"cannot inspect {label}: {exc}")
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            _fail(f"{label} has a symlink or non-directory component: {parent}")
        try:
            os.chmod(parent, 0o700)
        except OSError:
            pass
    return _canonical_existing_directory(parent, label=label)


def _owned_directory(parent: Path, name: str, *, label: str) -> Path:
    if not name or "/" in name or "\\" in name or name in {".", ".."}:
        _fail(f"unsafe {label} name")
    target = parent / name
    try:
        target.mkdir(mode=0o700)
    except FileExistsError:
        try:
            info = target.lstat()
        except OSError as exc:
            _fail(f"cannot inspect {label}: {exc}")
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            _fail(f"{label} is not an owned directory: {target}")
    try:
        os.chmod(target, 0o700)
    except OSError:
        pass
    return _canonical_existing_directory(target, label=label)


def _safe_rel(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        _fail(f"{label} must be a nonempty relative path")
    if "\\" in value or "\r" in value or "\n" in value:
        _fail(f"unsafe {label}: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        _fail(f"unsafe {label}: {value!r}")
    if any(part in PROTECTED_PARTS for part in path.parts):
        _fail(f"unsafe {label}: protected Git/runtime path")
    return path.as_posix()


def _normal_paths(values: Iterable[str], *, label: str) -> list[str]:
    try:
        result = sorted({_safe_rel(value, label=label) for value in values})
    except TypeError as exc:
        _fail(f"{label} must be a sequence of paths")
        raise AssertionError from exc
    return result


def _mkdir_under(root: Path, relative_parent: str) -> Path:
    current = root
    if not relative_parent:
        return current
    for part in PurePosixPath(relative_parent).parts:
        current = current / part
        try:
            current.mkdir(mode=0o700)
        except FileExistsError:
            pass
        try:
            info = current.lstat()
        except OSError as exc:
            _fail(f"cannot inspect owned path {current}: {exc}")
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            _fail(f"owned record path has a symlink or non-directory component: {current}")
    return current


def _under_owned(root: Path, relative: str, *, label: str) -> Path:
    rel = _safe_rel(relative, label=label)
    parent = _mkdir_under(root, PurePosixPath(rel).parent.as_posix() if str(PurePosixPath(rel).parent) != "." else "")
    target = parent / PurePosixPath(rel).name
    if not _is_under(target, root):  # defensive even after PurePosixPath validation
        _fail(f"unsafe {label}")
    return target


def _write_new_bytes(path: Path, data: bytes, *, mode: int = 0o444) -> None:
    try:
        fd = os.open(os.fspath(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        _fail(f"immutable record already exists: {path}")
    except OSError as exc:
        _fail(f"cannot create record {path}: {exc}")
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    except OSError as exc:
        _fail(f"cannot write record {path}: {exc}")
    finally:
        os.close(fd)
    try:
        os.chmod(path, mode)
    except OSError as exc:
        _fail(f"cannot protect immutable record {path}: {exc}")


def _write_new_json(path: Path, value: Any) -> None:
    _write_new_bytes(path, _json_bytes(value) + b"\n")


def _read_json_file(path: Path, *, label: str) -> Any:
    regular = _canonical_existing_file(path, label=label)
    try:
        return json.loads(regular.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"cannot read valid JSON from {label}: {exc}")
    raise AssertionError("unreachable")


@contextmanager
def _attempt_lock(attempt: Path) -> Iterator[None]:
    lock = attempt / ".lock"
    try:
        fd = os.open(
            os.fspath(lock),
            os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
    except OSError as exc:
        _fail(f"cannot open attempt lock: {exc}")
    try:
        if stat.S_ISLNK(os.fstat(fd).st_mode):
            _fail("attempt lock is unsafe")
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _clean_git_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key in list(environment):
        if _is_git_context_environment_name(key):
            environment.pop(key, None)
    for key in GIT_DIFF_ENVIRONMENT:
        environment.pop(key, None)
    environment["GIT_TERMINAL_PROMPT"] = "0"
    # Read-only source probes must not opportunistically refresh its index.
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    return environment


def _is_git_context_environment_name(key: str) -> bool:
    return key in GIT_CONTEXT_ENVIRONMENT or key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))


def _git_context_environment_overrides() -> list[str]:
    return sorted(
        key for key in os.environ
        if _is_git_context_environment_name(key)
    )


def _require_no_git_context_environment_overrides(operation: str) -> None:
    overrides = _git_context_environment_overrides()
    if overrides:
        _fail(f"{operation} refuses Git context environment overrides: " + ", ".join(overrides))


# Pin output settings that user/global config could otherwise change.  The
# helper hashes, compares and applies diff bytes, so colour escapes or
# alternative path prefixes would corrupt patches or fail verification.
GIT_OUTPUT_CONFIG = (
    "-c", "core.hooksPath=/dev/null",
    "-c", "color.ui=never",
    "-c", "color.diff=never",
    "-c", "diff.noprefix=false",
    "-c", "diff.mnemonicPrefix=false",
    "-c", "diff.relative=false",
    "-c", "diff.srcPrefix=a/",
    "-c", "diff.dstPrefix=b/",
    "-c", "diff.context=3",
    "-c", "diff.interHunkContext=0",
    "-c", "diff.suppressBlankEmpty=false",
)
# Explicit flags for every diff whose bytes are hashed, compared or applied.
# Command-line options outrank configuration, so these hold even for keys the
# pinned config above does not name (textconv drivers from user attributes,
# newer prefix keys).  Callers add the prefix choice and the diff operands.
PATCH_DIFF_FLAGS = (
    "--binary", "--full-index", "--no-ext-diff", "--no-textconv", "--no-color",
    "--unified=3", "--inter-hunk-context=0",
)
# Environment variables that change diff output or pathspec parsing regardless
# of configuration.  Git exports the pathspec ones to hooks and `!` aliases when
# it runs with, for example, --literal-pathspecs; `check-ignore` then refuses
# every path.
GIT_DIFF_ENVIRONMENT = frozenset({
    "GIT_DIFF_OPTS", "GIT_EXTERNAL_DIFF",
    "GIT_LITERAL_PATHSPECS", "GIT_GLOB_PATHSPECS", "GIT_NOGLOB_PATHSPECS", "GIT_ICASE_PATHSPECS",
})
DEFAULT_GIT_TIMEOUT_SECONDS = 300.0
MAX_GIT_TIMEOUT_SECONDS = 86400.0
# Failed-prepare cleanup often follows a Git timeout; it must not inherit a
# deliberately short limit and give up on the state that timeout left.
PROCESS_STOP_GRACE_SECONDS = 2.0
CLEANUP_GIT_TIMEOUT_SECONDS = 120.0


def _git_timeout() -> float:
    """Return the per-command Git timeout; ASK_AGENT_GIT_TIMEOUT overrides it."""
    raw = os.environ.get("ASK_AGENT_GIT_TIMEOUT")
    if raw is None or not raw.strip():
        return DEFAULT_GIT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        value = 0.0
    if not (math.isfinite(value) and 0 < value <= MAX_GIT_TIMEOUT_SECONDS):
        _fail(f"ASK_AGENT_GIT_TIMEOUT must be a positive number of seconds, at most {MAX_GIT_TIMEOUT_SECONDS:g}")
    return value


def _git(
    repo: Path,
    *arguments: str,
    input_bytes: bytes | None = None,
    check: bool = True,
    extra_environment: Mapping[str, str] | None = None,
    minimum_timeout: float = 0.0,
) -> subprocess.CompletedProcess[bytes]:
    timeout = max(_git_timeout(), minimum_timeout)
    environment = _clean_git_environment()
    environment.update(extra_environment or {})
    command = ["git", *GIT_OUTPUT_CONFIG, "-C", os.fspath(repo), *arguments]
    try:
        # Git runs some work (for example a worktree checkout) in child
        # processes.  Its own session lets a timeout or interrupt stop the
        # whole group, so no orphaned child keeps writing after we report.
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE if input_bytes is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            start_new_session=True,
        )
    except FileNotFoundError as exc:
        _fail("Git is required but was not found on PATH")
        raise AssertionError from exc
    try:
        stdout, stderr = process.communicate(input=input_bytes, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _stop_process_group(process)
        _fail(
            f"Git timed out after {timeout:g}s during {' '.join(arguments[:3])}; "
            "set ASK_AGENT_GIT_TIMEOUT to allow longer"
        )
        raise AssertionError from exc
    except BaseException:
        _stop_process_group(process)
        raise
    result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    if check and result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        _fail(f"Git {' '.join(arguments[:3])} failed{suffix}")
    return result


def _stop_process_group(process: subprocess.Popen[bytes]) -> None:
    """Stop a Git command and every child in its session, then reap it.

    SIGTERM comes first because Git removes its lock files and a half-created
    worktree on SIGTERM but cannot on SIGKILL; whatever still runs after a
    short grace is killed.
    """
    for signum, wait in ((signal.SIGTERM, PROCESS_STOP_GRACE_SECONDS), (signal.SIGKILL, 10.0)):
        try:
            os.killpg(process.pid, signum)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            process.communicate(timeout=wait)
        except (subprocess.TimeoutExpired, ValueError):
            pass


def _patch_diff(repo: Path, *arguments: str) -> bytes:
    """Return a repository diff in the exact form the helper hashes and applies."""
    return _git(repo, "diff", *PATCH_DIFF_FLAGS, "--src-prefix=a/", "--dst-prefix=b/", *arguments).stdout


def _git_text(repo: Path, *arguments: str) -> str:
    return _git(repo, *arguments).stdout.decode("utf-8", "surrogateescape").strip()


def _repo_root(path: Path) -> Path:
    start = _canonical_existing_directory(path, label="repository")
    root = Path(_git_text(start, "rev-parse", "--path-format=absolute", "--show-toplevel"))
    if not root.is_absolute():
        _fail("Git returned a non-absolute repository root")
    return _canonical_existing_directory(root, label="repository root")


def _common_dir(repo: Path) -> Path:
    value = Path(_git_text(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    if not value.is_absolute():
        _fail("Git returned a non-absolute common directory")
    return _canonical_existing_directory(value, label="Git common directory")


def _head(repo: Path) -> str:
    probe = _git(repo, "rev-parse", "--verify", "--quiet", "HEAD^{commit}", check=False)
    if probe.returncode:
        _fail("repository HEAD does not name a commit (empty repository or unborn branch); commit once before delegating")
    value = probe.stdout.decode("utf-8", "surrogateescape").strip()
    if not GIT_SHA_RE.fullmatch(value):
        _fail("repository HEAD is not a commit SHA")
    return value


def _branch(repo: Path) -> str:
    result = _git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if result.returncode:
        return "(detached)"
    value = result.stdout.decode("utf-8", "surrogateescape").strip()
    if not value or "\x00" in value or "\n" in value:
        _fail("Git returned an unsafe branch name")
    return value


def _git_path(repo: Path, name: str) -> Path:
    result = Path(_git_text(repo, "rev-parse", "--path-format=absolute", "--git-path", name))
    if not result.is_absolute():
        _fail(f"Git returned a non-absolute path for {name}")
    return result


def _index_bytes_digest(repo: Path) -> str:
    path = _git_path(repo, "index")
    try:
        info = path.lstat()
    except FileNotFoundError:
        return "missing"
    except OSError as exc:
        _fail(f"cannot inspect Git index: {exc}")
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        _fail("Git index is not a regular file")
    return _sha256_file(path)


def _split_nul_paths(data: bytes, *, label: str) -> list[str]:
    if data and not data.endswith(b"\0"):
        _fail(f"Git returned malformed {label}")
    return [_safe_rel(os.fsdecode(item), label=label) for item in data.split(b"\0") if item]


def _index_entries(repo: Path) -> list[dict[str, Any]]:
    raw = _git(repo, "ls-files", "--stage", "-z").stdout
    if raw and not raw.endswith(b"\0"):
        _fail("Git returned malformed index entries")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in raw.split(b"\0"):
        if not row:
            continue
        try:
            header, encoded_path = row.split(b"\t", 1)
            mode, object_id, stage = header.split(b" ")
            path = _safe_rel(os.fsdecode(encoded_path), label="index path")
            stage_number = int(stage)
        except (ValueError, UnicodeError) as exc:
            _fail(f"Git returned malformed index entry: {exc}")
        if stage_number != 0:
            _fail("unmerged/conflicted index entries are unsupported")
        grouped.setdefault(path, []).append(
            {"mode": mode.decode("ascii", "strict"), "object": object_id.decode("ascii", "strict"), "stage": stage_number}
        )
    return [{"path": path, "entries": grouped[path]} for path in sorted(grouped)]


def _refuse_special_index(repo: Path) -> None:
    if os.environ.get("GIT_INDEX_FILE"):
        _fail("special index state (GIT_INDEX_FILE) is unsupported")
    conflicts = _git(repo, "ls-files", "-u", "-z").stdout
    if conflicts:
        _fail("unmerged/conflicted index entries are unsupported")
    debug = _git(repo, "ls-files", "--debug").stdout.decode("utf-8", "replace")
    for value in re.findall(r"flags:\s*([0-9A-Fa-f]+)", debug):
        if int(value, 16) & 0x20000000:
            _fail("special index state: intent-to-add entries are unsupported")
    tags = _git(repo, "ls-files", "-v", "-z").stdout
    for row in tags.split(b"\0"):
        if not row:
            continue
        if len(row) < 3 or row[1:2] != b" ":
            _fail("Git returned malformed index flags")
        marker = row[:1]
        if marker == b"S" or marker.islower():
            _fail("special index state: assume-unchanged or skip-worktree entries are unsupported")
    sparse = _git(repo, "config", "--bool", "core.sparseCheckout", check=False)
    if sparse.returncode == 0 and sparse.stdout.decode("ascii", "replace").strip().lower() == "true":
        _fail("special index state: sparse checkout is unsupported")


def _refuse_submodules(repo: Path, entries: Sequence[Mapping[str, Any]]) -> None:
    paths = [entry["path"] for entry in entries if any(item["mode"] == "160000" for item in entry["entries"])]
    for relative in paths:
        child = repo / relative
        if child.is_dir() and not child.is_symlink():
            result = _git(child, "status", "--porcelain=v1", "-z", check=False)
            if result.returncode == 0 and result.stdout:
                _fail(f"dirty submodule is unsupported: {relative}")
        _fail(f"submodule content cannot be faithfully copied: {relative}")


def _paths_with_attribute(repo: Path, paths: Sequence[str], attribute: str) -> list[str]:
    """Return the paths for which `attribute` is set (neither unspecified nor unset)."""
    if not paths:
        return []
    payload = b"".join(os.fsencode(path) + b"\0" for path in paths)
    raw = _git(repo, "check-attr", "-z", attribute, "--stdin", input_bytes=payload).stdout
    parts = raw.split(b"\0")
    if parts and parts[-1] == b"":
        parts.pop()
    if len(parts) % 3:
        _fail(f"Git returned malformed {attribute} attributes")
    return [
        os.fsdecode(parts[index]) for index in range(0, len(parts), 3)
        if parts[index + 2] not in {b"unspecified", b"unset"}
        and not (attribute == "working-tree-encoding" and _is_utf8_name(parts[index + 2]))
    ]


def _is_utf8_name(value: bytes) -> bool:
    """Git treats these working-tree-encoding values as UTF-8 and converts nothing."""
    return value.lower().replace(b"-", b"") == b"utf8"


def _refuse_filter_ambiguity(repo: Path, paths: Sequence[str]) -> None:
    filtered = _paths_with_attribute(repo, paths, "filter")
    if filtered:
        _fail(f"Git filter ambiguity is unsupported at {filtered[0]}")


def _entry_at(root: Path, relative: str, *, label: str) -> dict[str, Any]:
    safe = _safe_rel(relative, label=label)
    path = root.joinpath(*PurePosixPath(safe).parts)
    try:
        info = path.lstat()
    except FileNotFoundError:
        _fail(f"missing {label}: {safe}")
    except OSError as exc:
        _fail(f"cannot inspect {label} {safe}: {exc}")
    mode = stat.S_IMODE(info.st_mode)
    if stat.S_ISREG(info.st_mode):
        return {"path": safe, "type": "file", "mode": mode, "size": info.st_size, "sha256": _sha256_file(path)}
    if stat.S_ISLNK(info.st_mode):
        try:
            target = os.readlink(path)
        except OSError as exc:
            _fail(f"cannot read symlink {safe}: {exc}")
        raw_target = os.fsencode(target)
        return {
            "path": safe,
            "type": "symlink",
            "mode": mode,
            "size": len(raw_target),
            "sha256": _sha256(raw_target),
            "target_b64": base64.b64encode(raw_target).decode("ascii"),
        }
    _fail(f"unsupported special file in {label}: {safe}")
    raise AssertionError("unreachable")


def _untracked_manifest(repo: Path) -> list[dict[str, Any]]:
    paths = _split_nul_paths(_git(repo, "ls-files", "--others", "--exclude-standard", "-z").stdout, label="untracked path")
    return [_entry_at(repo, path, label="untracked input") for path in sorted(paths)]


def _tracked_worktree_manifest(repo: Path) -> list[dict[str, Any]]:
    """Capture raw tracked working files independently of Git diff semantics."""
    paths = _split_nul_paths(_git(repo, "ls-files", "-z").stdout, label="tracked path")
    result: list[dict[str, Any]] = []
    for path in sorted(paths):
        candidate = repo.joinpath(*PurePosixPath(path).parts)
        try:
            candidate.lstat()
        except FileNotFoundError:
            # An unstaged delete is represented in the working-layer patch and
            # must be absent from the raw working-file comparison.
            continue
        except OSError as exc:
            _fail(f"cannot inspect tracked working file {path}: {exc}")
        result.append(_entry_at(repo, path, label="tracked working file"))
    return result


def _ignored_paths(repo: Path) -> list[str]:
    """Report omitted ignored entries; they are never copied, so never validated as copy targets.

    `--directory` collapses a wholly ignored directory (for example
    `node_modules/` or a `.worktrees/` store) to one entry ending in `/`.
    """
    raw = _git(repo, "ls-files", "--others", "--ignored", "--exclude-standard", "--directory", "-z").stdout
    if raw and not raw.endswith(b"\0"):
        _fail("Git returned malformed ignored paths")
    # ls-files can list a collapsed `dir/` and also files beneath it.  Sorted
    # entries sharing a prefix are contiguous, so one pass keeps only the
    # outermost entry.
    collapsed: list[str] = []
    for entry in sorted(os.fsdecode(item) for item in raw.split(b"\0") if item):
        if collapsed and collapsed[-1].endswith("/") and entry.startswith(collapsed[-1]):
            continue
        collapsed.append(entry)
    return collapsed


def _ignored_added_paths(worktree: Path, changes: Sequence[Mapping[str, Any]]) -> list[str]:
    """Return worker-added, untracked paths that the worktree's ignore rules exclude.

    These are generated outputs (caches, builds, installed dependencies), not
    contribution.  They remain in the fingerprinted worker state and are
    reported separately so the parent can see what close will discard.
    """
    candidates = [item["path"] for item in changes if item["change"] == "added" and "index" not in item["layers"]]
    if not candidates:
        return []
    # check-ignore parses stdin entries as pathspecs, so a name such as
    # `:config` would lose its colon to pathspec magic.  A `./` prefix makes
    # every entry a plain path; strip it again from the output.
    payload = b"".join(b"./" + os.fsencode(path) + b"\0" for path in candidates)
    result = _git(worktree, "check-ignore", "-z", "--stdin", input_bytes=payload, check=False)
    if result.returncode not in {0, 1}:
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        _fail("could not classify ignored worker paths" + (f": {detail[-1]}" if detail else ""))
    matched = {os.fsdecode(item.removeprefix(b"./")) for item in result.stdout.split(b"\0") if item}
    return [path for path in candidates if path in matched]


def _copy_entry(source_root: Path, entry: Mapping[str, Any], target_root: Path, *, label: str) -> None:
    relative = _safe_rel(str(entry.get("path", "")), label=label)
    source = source_root.joinpath(*PurePosixPath(relative).parts)
    observed = _entry_at(source_root, relative, label=label)
    if observed != dict(entry):
        _fail(f"{label} changed while it was being copied: {relative}")
    target = _under_owned(target_root, relative, label=label)
    try:
        target_info = target.lstat()
    except FileNotFoundError:
        target_info = None
    except OSError as exc:
        _fail(f"cannot inspect target {relative}: {exc}")
    if target_info is not None:
        # A staged deletion followed by an unstaged recreation is represented
        # both as a working-layer patch and as an untracked source path.  The
        # patch may have already recreated identical bytes; verify/reuse only
        # that exact case rather than overwriting it.
        if _same_copy(_entry_at(target_root, relative, label=f"existing copied {label}"), observed):
            return
        _fail(f"target path already exists while copying {label}: {relative}")
    if observed["type"] == "file":
        try:
            with source.open("rb") as input_handle:
                with target.open("xb") as output_handle:
                    shutil.copyfileobj(input_handle, output_handle, length=1024 * 1024)
            os.chmod(target, int(observed["mode"]))
        except OSError as exc:
            _fail(f"cannot copy {label} {relative}: {exc}")
    elif observed["type"] == "symlink":
        raw_target = base64.b64decode(str(observed["target_b64"]).encode("ascii"), validate=True)
        try:
            os.symlink(os.fsdecode(raw_target), target)
        except OSError as exc:
            _fail(f"cannot copy symlink {relative}: {exc}")
        if hasattr(os, "lchmod"):
            try:
                os.lchmod(target, int(observed["mode"]))
            except (OSError, NotImplementedError):
                pass  # Best effort; a symlink's own mode is not content Git or tools use.
    else:
        _fail(f"unsupported {label} entry type")
    if not _same_copy(_entry_at(target_root, relative, label=f"copied {label}"), observed):
        _fail(f"copied {label} did not verify: {relative}")


def _same_copy(copied: Mapping[str, Any], observed: Mapping[str, Any]) -> bool:
    """Compare a copy with its source, ignoring only a symlink's own permission bits.

    A symlink's mode comes from the creating process's umask and cannot be set
    on every platform; Git records none of it.  Regular-file modes stay exact.
    """
    if copied.get("type") == "symlink" and observed.get("type") == "symlink":
        return {**copied, "mode": None} == {**observed, "mode": None}
    return dict(copied) == dict(observed)


def _scan_workspace_files(root: Path, *, label: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    def visit(directory: Path, prefix: str) -> None:
        try:
            entries = sorted(list(os.scandir(directory)), key=lambda item: item.name)
        except OSError as exc:
            _fail(f"cannot scan {label}: {exc}")
        for item in entries:
            if not prefix and item.name == ".git":
                continue
            relative = f"{prefix}/{item.name}" if prefix else item.name
            safe = _safe_rel(relative, label=f"{label} path")
            try:
                info = item.stat(follow_symlinks=False)
            except OSError as exc:
                _fail(f"cannot inspect {label} path {safe}: {exc}")
            if stat.S_ISDIR(info.st_mode):
                visit(Path(item.path), safe)
            else:
                result.append(_entry_at(root, safe, label=label))

    visit(root, "")
    return sorted(result, key=lambda item: item["path"])


@dataclass(frozen=True)
class SourceCapture:
    head: str
    branch: str
    common_dir: str
    index_bytes_sha256: str
    index_entries: list[dict[str, Any]]
    staged_patch: bytes
    unstaged_patch: bytes
    tracked_files: list[dict[str, Any]]
    untracked: list[dict[str, Any]]
    ignored: list[str]

    def comparable(self) -> dict[str, Any]:
        return {
            "head": self.head,
            "branch": self.branch,
            "common_dir": self.common_dir,
            "index_bytes_sha256": self.index_bytes_sha256,
            "index_entries": self.index_entries,
            "staged_patch_sha256": _sha256(self.staged_patch),
            "unstaged_patch_sha256": _sha256(self.unstaged_patch),
            "tracked_files": self.tracked_files,
            "untracked": self.untracked,
        }


def _capture_source(source: Path) -> SourceCapture:
    _refuse_special_index(source)
    entries = _index_entries(source)
    _refuse_submodules(source, entries)
    tracked_files = _tracked_worktree_manifest(source)
    untracked = _untracked_manifest(source)
    _refuse_filter_ambiguity(source, [entry["path"] for entry in entries] + [entry["path"] for entry in untracked])
    return SourceCapture(
        head=_head(source),
        branch=_branch(source),
        common_dir=os.fspath(_common_dir(source)),
        index_bytes_sha256=_index_bytes_digest(source),
        index_entries=entries,
        staged_patch=_patch_diff(source, "--cached", "HEAD"),
        unstaged_patch=_patch_diff(source),
        tracked_files=tracked_files,
        untracked=untracked,
        ignored=_ignored_paths(source),
    )


def _registered_worktrees(repo: Path, *, minimum_timeout: float = 0.0) -> list[dict[str, str]]:
    """Read Git's registration view, rather than trusting a path on disk."""
    raw = _git(repo, "worktree", "list", "--porcelain", minimum_timeout=minimum_timeout).stdout.decode("utf-8", "surrogateescape")
    rows: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in raw.splitlines():
        if not line:
            if current:
                rows.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key in {"worktree", "HEAD", "branch"} and value:
            current[key] = value
    if current:
        rows.append(current)
    if not rows:
        _fail("Git reported no registered worktrees")
    return rows


def _registered_identity(repo: Path, path: Path) -> dict[str, str]:
    wanted = _canonical_existing_directory(path, label="worktree")
    for row in _registered_worktrees(repo):
        raw = row.get("worktree")
        if not raw:
            continue
        try:
            candidate = Path(raw).resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if candidate == wanted:
            return {
                "path": os.fspath(wanted),
                "head": row.get("HEAD", ""),
                "branch": row.get("branch", ""),
            }
    _fail(f"worktree is not registered by this repository: {wanted}")
    raise AssertionError("unreachable")


def _worker_state(worktree: Path) -> dict[str, Any]:
    _refuse_special_index(worktree)
    entries = _index_entries(worktree)
    files = _scan_workspace_files(worktree, label="worker worktree")
    cached = _patch_diff(worktree, "--cached", "HEAD")
    unstaged = _patch_diff(worktree)
    return {
        "head": _head(worktree),
        "branch": _branch(worktree),
        "index_entries": entries,
        "cached_patch_sha256": _sha256(cached),
        "unstaged_patch_sha256": _sha256(unstaged),
        "files": files,
    }


def _state_fingerprint(state: Mapping[str, Any]) -> str:
    return _sha256(_json_bytes(state))


def _inspection_fingerprint(
    state: Mapping[str, Any],
    artifacts: Sequence[str],
    discard: Sequence[str],
    ignored: Sequence[str] = (),
) -> str:
    """Bind acceptance to complete worker state and every path classification.

    Ignore rules can live outside the fingerprinted worktree (a global
    excludes file, the common `info/exclude`), so the ignored classification
    is bound explicitly.  It is included only when non-empty, keeping the
    fingerprint of the common case identical to earlier helper versions.
    """
    value: dict[str, Any] = {
        "state": state,
        "artifacts": sorted(artifacts),
        "discard": sorted(discard),
    }
    if ignored:
        value["ignored"] = sorted(ignored)
    return _sha256(_json_bytes(value))


def _copy_tree_entries(source_root: Path, entries: Sequence[Mapping[str, Any]], target_root: Path, *, label: str) -> None:
    for entry in entries:
        _copy_entry(source_root, entry, target_root, label=label)


def _git_visible_entries(entries: Sequence[Mapping[str, Any]], *, honor_exec: bool) -> list[dict[str, Any]]:
    """Project file entries onto what a Git checkout can reproduce.

    Git records only a regular file's executable bit (and nothing for a
    symlink's own permissions), so a checkout under a different umask or of a
    `chmod 600` file legitimately differs in raw permission bits.
    """
    projected: list[dict[str, Any]] = []
    for entry in entries:
        item = dict(entry)
        if item.get("type") == "symlink" or not honor_exec:
            item["mode"] = None
        else:
            item["mode"] = 0o755 if int(item["mode"]) & 0o100 else 0o644
        projected.append(item)
    return projected


def _honors_exec_bit(repo: Path) -> bool:
    result = _git(repo, "config", "--bool", "core.fileMode", check=False)
    return not (result.returncode == 0 and result.stdout.decode("ascii", "replace").strip() == "false")


def _verify_child_capture(worktree: Path, capture: SourceCapture, branch: str) -> dict[str, Any]:
    if _head(worktree) != capture.head:
        _fail("worker worktree HEAD does not match captured source HEAD")
    if _branch(worktree) != branch:
        _fail("worker worktree branch does not match its owned branch")
    if _index_entries(worktree) != capture.index_entries:
        _fail("worker worktree index entries differ from captured source index")
    staged = _patch_diff(worktree, "--cached", "HEAD")
    if staged != capture.staged_patch:
        _fail("worker worktree staged binary diff differs from captured source")
    unstaged = _patch_diff(worktree)
    if unstaged != capture.unstaged_patch:
        _fail("worker worktree unstaged binary diff differs from captured source")
    child_untracked = _untracked_manifest(worktree)
    if child_untracked != capture.untracked:
        _fail("worker worktree untracked inputs differ from captured source")
    expected_files = sorted(capture.tracked_files + capture.untracked, key=lambda item: item["path"])
    honor_exec = _honors_exec_bit(worktree)
    expected_visible = _git_visible_entries(expected_files, honor_exec=honor_exec)
    state = _worker_state(worktree)
    if _git_visible_entries(state["files"], honor_exec=honor_exec) != expected_visible:
        _fail("worker working-file bytes or Git-tracked modes differ from captured source")
    return state


def _label_fragment(label: str | None) -> str:
    raw = label or "worker"
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", raw.strip()).strip(".-")[:40]
    return value or "worker"


def _default_store(source: Path, common: Path) -> Path:
    digest = _sha256(os.fsencode(os.fspath(common)))[:20]
    configured = os.environ.get("XDG_STATE_HOME")
    state_home = Path(configured).expanduser() if configured else Path.home() / ".local" / "state"
    base = state_home / "ask-agent" / "workspaces" / digest
    return _make_private_directory(base, label="default workspace store")


def _resolve_store(source: Path, common: Path, store: Path | None) -> Path:
    root = _default_store(source, common) if store is None else _make_private_directory(store, label="workspace store")
    if _is_under(root, source) or root == source:
        _fail("workspace store must be outside the source working tree")
    for worktree in _registered_worktrees(source):
        raw = worktree.get("worktree")
        if not raw:
            continue
        try:
            registered = Path(raw).resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if _is_under(root, registered) or root == registered:
            _fail("workspace store must be outside every registered repository worktree")
    return root


def _new_attempt(store: Path) -> tuple[str, Path]:
    attempts = _owned_directory(store, "attempts", label="attempts directory")
    for _ in range(20):
        attempt_id = uuid.uuid4().hex
        candidate = attempts / attempt_id
        try:
            candidate.mkdir(mode=0o700)
        except FileExistsError:
            continue
        return attempt_id, _canonical_existing_directory(candidate, label="attempt directory")
    _fail("could not allocate a unique workspace attempt")
    raise AssertionError("unreachable")


def _record_failure(attempt: Path, message: str, **details: Any) -> str:
    path = attempt / "failure.json"
    if path.exists():
        return os.fspath(path)
    value: dict[str, Any] = {"schema": "ask-agent.workspace.failure.v1", "status": "failed", "reason": message}
    value.update(details)
    try:
        _write_new_json(path, value)
    except (WorkspaceError, OSError) as exc:
        # The original failure is still raised; do not let a secondary write
        # error hide it, but never claim a record exists when it does not.
        sys.stderr.write(f"ask-agent: could not write failure record {path}: {exc}\n")
        return f"unavailable ({exc})"
    return os.fspath(path)


def _baseline_paths(attempt: Path) -> dict[str, Path]:
    return {
        "baseline": attempt / "baseline.json",
        "baseline_files": attempt / "baseline-files",
        "staged_patch": attempt / "source-staged.patch",
        "unstaged_patch": attempt / "source-unstaged.patch",
        "receipt": attempt / "receipt.json",
    }


def _base_output(record: Mapping[str, Any], status: str) -> dict[str, Any]:
    return {
        "status": status,
        "receipt": record["receipt_path"],
        "worktree": record["worktree"],
        "branch": record["branch"],
        "baseline": record["baseline_path"],
    }


def _new_prepare(source_argument: Path, store_argument: Path | None, label: str | None) -> dict[str, Any]:
    source = _repo_root(source_argument)
    common = _common_dir(source)
    store = _resolve_store(source, common, store_argument)
    capture_before = _capture_source(source)
    attempt_id, attempt = _new_attempt(store)
    paths = _baseline_paths(attempt)
    worktree = attempt / "worktree"
    branch = f"ask-agent/{_label_fragment(label)}-{attempt_id[:12]}"
    add_attempted = False
    receipt_started = receipt_written = False
    try:
        with _attempt_lock(attempt):
            _write_new_bytes(paths["staged_patch"], capture_before.staged_patch)
            _write_new_bytes(paths["unstaged_patch"], capture_before.unstaged_patch)
            if _git(source, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode == 0:
                _fail(f"owned branch name is already in use: {branch}")
            # From here on Git may leave state behind even when the command
            # fails or times out (it creates the branch before checkout), so
            # cleanup inspects what actually exists rather than trusting the
            # return code.
            add_attempted = True
            added = _git(source, "worktree", "add", "-b", branch, os.fspath(worktree), capture_before.head, check=False)
            if added.returncode:
                detail = added.stderr.decode("utf-8", "replace").strip().splitlines()
                _fail("could not create owned Git worktree" + (f": {detail[-1]}" if detail else ""))
            worktree = _repo_root(worktree)
            identity = _registered_identity(source, worktree)
            if identity["head"] and identity["head"] != capture_before.head:
                _fail("registered worker worktree HEAD differs from captured source")
            expected_ref = f"refs/heads/{branch}"
            if identity["branch"] != expected_ref:
                _fail("registered worker worktree branch differs from owned branch")
            if capture_before.staged_patch:
                _git(worktree, "apply", "--binary", "--index", "--whitespace=nowarn", input_bytes=capture_before.staged_patch)
            if capture_before.unstaged_patch:
                _git(worktree, "apply", "--binary", "--whitespace=nowarn", input_bytes=capture_before.unstaged_patch)
            for entry in capture_before.untracked:
                _copy_entry(source, entry, worktree, label="untracked input")
            state = _verify_child_capture(worktree, capture_before, branch)
            capture_after = _capture_source(source)
            if capture_after.comparable() != capture_before.comparable():
                _fail("source changed during capture; prepare again once writers are quiescent")
            baseline_files = _owned_directory(attempt, "baseline-files", label="baseline file store")
            _copy_tree_entries(worktree, state["files"], baseline_files, label="baseline file")
            baseline = {
                "schema": BASELINE_SCHEMA,
                "version": VERSION,
                "attempt_id": attempt_id,
                "source": {
                    "root": os.fspath(source),
                    "common_dir": os.fspath(common),
                    "head": capture_before.head,
                    "branch": capture_before.branch,
                },
                "source_capture": capture_before.comparable(),
                "source_staged_patch": {
                    "path": os.fspath(paths["staged_patch"]),
                    "sha256": _sha256(capture_before.staged_patch),
                },
                "source_unstaged_patch": {
                    "path": os.fspath(paths["unstaged_patch"]),
                    "sha256": _sha256(capture_before.unstaged_patch),
                },
                "untracked": capture_before.untracked,
                "ignored_dependencies_omitted": capture_before.ignored,
                "worker_state": state,
                "worker_state_fingerprint": _state_fingerprint(state),
                "baseline_files": os.fspath(baseline_files),
                "quiescence": "caller asserted writers quiescent; observable source drift was checked before and after capture",
            }
            _write_new_json(paths["baseline"], baseline)
            baseline_sha = _sha256_file(paths["baseline"])
            receipt = {
                "schema": RECEIPT_SCHEMA,
                "version": VERSION,
                "status": "prepared",
                "attempt_id": attempt_id,
                "store": os.fspath(store),
                "source": {"root": os.fspath(source), "common_dir": os.fspath(common), "head": capture_before.head},
                "worktree": os.fspath(worktree),
                "branch": branch,
                "baseline": os.fspath(paths["baseline"]),
                "baseline_sha256": baseline_sha,
            }
            receipt_started = True
            _write_new_json(paths["receipt"], receipt)
            receipt_written = True
            record = _load_receipt(paths["receipt"])
            result = _base_output(record, "prepared")
            result.update({"source": os.fspath(source), "attempt": attempt_id, "ignored_dependencies_omitted": capture_before.ignored})
            return result
    except BaseException as exc:
        if receipt_written:
            # The attempt is prepared: its receipt names an intact worktree
            # that `prepare --receipt` reuses, so nothing is removed.
            note = f"prepare wrote its receipt; the workspace is kept for reuse with prepare --receipt {paths['receipt']}"
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                sys.stderr.write(f"ask-agent: {note}\n")
                raise
            raise WorkspaceError(f"{exc} ({note})") from exc
        # Any failure, including OSError or an interrupt, must not strand a
        # receipt-less worktree and branch in the caller's repository.
        cleanup = "worktree add was not attempted"
        if receipt_started:
            # A receipt this prepare did not finish writing names nothing
            # usable; remove it so a receipt always means a prepared attempt.
            try:
                paths["receipt"].unlink(missing_ok=True)
            except OSError:
                pass
        if add_attempted:
            try:
                cleanup = _discard_failed_preparation(source, attempt / "worktree", branch, capture_before.head)
            except Exception as cleanup_error:  # never mask the original failure
                cleanup = f"cleanup failed ({cleanup_error}); worktree and branch may remain"
        detail = str(exc)
        if not isinstance(exc, WorkspaceError):
            detail = f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__
        failure_path = _record_failure(attempt, detail, worktree=os.fspath(attempt / "worktree"), branch=branch, cleanup=cleanup)
        message = f"{detail} (prepare failed before dispatch; cleanup: {cleanup}; failure record: {failure_path})"
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            sys.stderr.write(f"ask-agent: {message}\n")
            raise
        raise WorkspaceError(message) from exc


def _discard_failed_preparation(source: Path, worktree: Path, branch: str, head: str) -> str:
    """Remove the worktree/branch this prepare just created; no worker has run in them.

    Without a receipt, `close` cannot manage them, so leaving them registered
    only accumulates orphaned worktrees and `ask-agent/*` branches in the
    caller's repository.  The branch is deleted only while it still points at
    the captured source HEAD, i.e. it holds no commits of its own.
    """
    notes: list[str] = []
    if _registered_path_present(source, worktree, minimum_timeout=CLEANUP_GIT_TIMEOUT_SECONDS):
        # Double force also removes a worktree Git left locked mid-creation
        # ("initializing").  The path is this attempt's own, so no one else
        # can hold that lock legitimately.
        removed = _git(source, "worktree", "remove", "--force", "--force", os.fspath(worktree), check=False,
                       minimum_timeout=CLEANUP_GIT_TIMEOUT_SECONDS)
        if removed.returncode and _registered_path_present(source, worktree, minimum_timeout=CLEANUP_GIT_TIMEOUT_SECONDS):
            # Git refuses to validate a half-created worktree (for example one
            # whose .git file was never written).  The directory is this
            # attempt's own, so delete it; Git then removes the registration.
            if os.path.lexists(worktree):
                shutil.rmtree(worktree)
            removed = _git(source, "worktree", "remove", "--force", "--force", os.fspath(worktree), check=False,
                           minimum_timeout=CLEANUP_GIT_TIMEOUT_SECONDS)
            if removed.returncode and _registered_path_present(source, worktree, minimum_timeout=CLEANUP_GIT_TIMEOUT_SECONDS):
                detail = removed.stderr.decode("utf-8", "replace").strip().splitlines()
                return (
                    "retained worktree registration and branch; Git refused removal"
                    + (f": {detail[-1]}" if detail else "")
                    + f"; recover with: rm -rf {shlex.quote(os.fspath(worktree))}; "
                    + f"git -C {shlex.quote(os.fspath(source))} worktree prune; then delete branch "
                    + f"{branch} only if it still points at {head}"
                )
        if os.path.lexists(worktree):
            # Git deregisters the worktree even when deleting its files fails,
            # for example while a killed checkout's child was still writing.
            shutil.rmtree(worktree)
            notes.append("removed worktree and its leftover files")
        else:
            notes.append("removed worktree")
    elif os.path.lexists(worktree):
        shutil.rmtree(worktree)  # the attempt's own path, never registered with Git
        notes.append("removed unregistered worktree directory")
    else:
        notes.append("no worktree was created")
    tip = _git(source, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False,
               minimum_timeout=CLEANUP_GIT_TIMEOUT_SECONDS)
    if tip.returncode:
        notes.append("no branch was created")
    elif tip.stdout.decode("ascii", "replace").strip() != head:
        notes.append(f"retained branch {branch} because it moved")
    else:
        deleted = _git(source, "branch", "-D", "--", branch, check=False,
                       minimum_timeout=CLEANUP_GIT_TIMEOUT_SECONDS)
        notes.append(f"deleted branch {branch}" if deleted.returncode == 0 else f"retained branch {branch}; deletion failed")
    return "; ".join(notes)


def _load_receipt(path: Path) -> dict[str, Any]:
    receipt_path = _canonical_existing_file(path, label="workspace receipt")
    if receipt_path.name != "receipt.json":
        _fail("workspace receipt must be the immutable receipt.json record")
    attempt = _canonical_existing_directory(receipt_path.parent, label="receipt attempt directory")
    raw = _read_json_file(receipt_path, label="workspace receipt")
    if not isinstance(raw, dict):
        _fail("workspace receipt must be a JSON object")
    required = {
        "schema", "version", "status", "attempt_id", "store", "source", "worktree", "branch", "baseline", "baseline_sha256",
    }
    if set(raw) != required or raw.get("schema") != RECEIPT_SCHEMA or raw.get("version") != VERSION or raw.get("status") != "prepared":
        _fail("workspace receipt has an unsupported schema")
    attempt_id = raw.get("attempt_id")
    if not isinstance(attempt_id, str) or not re.fullmatch(r"[0-9a-f]{32}", attempt_id) or attempt.name != attempt_id:
        _fail("workspace receipt has an invalid attempt identity")
    store = raw.get("store")
    worktree = raw.get("worktree")
    branch = raw.get("branch")
    baseline_path = raw.get("baseline")
    source = raw.get("source")
    if not all(isinstance(value, str) and value for value in (store, worktree, branch, baseline_path)):
        _fail("workspace receipt has invalid paths or branch")
    if not isinstance(source, dict) or set(source) != {"root", "common_dir", "head"}:
        _fail("workspace receipt has invalid source identity")
    if not all(isinstance(source.get(key), str) and source[key] for key in source):
        _fail("workspace receipt has invalid source identity")
    if not GIT_SHA_RE.fullmatch(source["head"]):
        _fail("workspace receipt has invalid source HEAD")
    if not isinstance(raw.get("baseline_sha256"), str) or not SHA256_RE.fullmatch(raw["baseline_sha256"]):
        _fail("workspace receipt has invalid baseline digest")
    store_root = _canonical_existing_directory(Path(store), label="receipt store")
    expected_attempt = store_root / "attempts" / attempt_id
    if expected_attempt != attempt or not _is_under(attempt, store_root):
        _fail("workspace receipt escapes its owned store")
    expected_baseline = attempt / "baseline.json"
    if Path(baseline_path) != expected_baseline:
        _fail("workspace receipt references an unexpected baseline path")
    baseline = _read_json_file(expected_baseline, label="workspace baseline")
    if _sha256_file(expected_baseline) != raw["baseline_sha256"]:
        _fail("workspace baseline digest does not match receipt")
    if not isinstance(baseline, dict) or baseline.get("schema") != BASELINE_SCHEMA or baseline.get("version") != VERSION:
        _fail("workspace baseline has an unsupported schema")
    if baseline.get("attempt_id") != attempt_id:
        _fail("workspace baseline belongs to a different attempt")
    if baseline.get("source", {}).get("root") != source["root"] or baseline.get("source", {}).get("common_dir") != source["common_dir"]:
        _fail("workspace baseline source identity does not match receipt")
    files_root = baseline.get("baseline_files")
    if not isinstance(files_root, str) or Path(files_root) != attempt / "baseline-files":
        _fail("workspace baseline references an unexpected file store")
    _canonical_existing_directory(Path(files_root), label="baseline file store")
    if not isinstance(baseline.get("worker_state"), dict) or not isinstance(baseline.get("worker_state_fingerprint"), str):
        _fail("workspace baseline lacks a worker-state record")
    if _state_fingerprint(baseline["worker_state"]) != baseline["worker_state_fingerprint"]:
        _fail("workspace baseline worker-state record is corrupt")
    result = dict(raw)
    result.update({
        "receipt_path": os.fspath(receipt_path),
        "attempt": attempt,
        "store_path": store_root,
        "baseline_path": os.fspath(expected_baseline),
        "baseline_data": baseline,
    })
    return result


def _validate_binding(record: Mapping[str, Any], *, require_worktree: bool = True) -> tuple[Path, Path | None]:
    """Validate canonical paths, repository identity, and Git registration."""
    source = _repo_root(Path(record["source"]["root"]))
    if os.fspath(source) != record["source"]["root"]:
        _fail("source checkout canonical path no longer matches receipt")
    common = _common_dir(source)
    if os.fspath(common) != record["source"]["common_dir"]:
        _fail("source Git common directory no longer matches receipt")
    if require_worktree:
        worker = _repo_root(Path(record["worktree"]))
        if os.fspath(worker) != record["worktree"] or worker == source:
            _fail("worker worktree identity no longer matches receipt")
        if _common_dir(worker) != common:
            _fail("worker worktree is no longer registered to the source repository")
        registration = _registered_identity(source, worker)
        if registration["branch"] != f"refs/heads/{record['branch']}":
            _fail("worker worktree registration branch no longer matches receipt")
        if _branch(worker) != record["branch"]:
            _fail("worker worktree current branch no longer matches receipt")
        return source, worker
    return source, None


def _selection_contains(selection: Sequence[str], path: str) -> bool:
    return any(path == item or path.startswith(item + "/") for item in selection)


def _changes(baseline: Mapping[str, Any], current: Mapping[str, Any]) -> list[dict[str, Any]]:
    baseline_files = {entry["path"]: entry for entry in baseline["files"]}
    current_files = {entry["path"]: entry for entry in current["files"]}
    baseline_index = {entry["path"]: entry["entries"] for entry in baseline["index_entries"]}
    current_index = {entry["path"]: entry["entries"] for entry in current["index_entries"]}
    all_paths = sorted(set(baseline_files) | set(current_files) | set(baseline_index) | set(current_index))
    result: list[dict[str, Any]] = []
    for path in all_paths:
        before_file = baseline_files.get(path)
        after_file = current_files.get(path)
        before_index = baseline_index.get(path)
        after_index = current_index.get(path)
        filesystem_changed = before_file != after_file
        index_changed = before_index != after_index
        if not filesystem_changed and not index_changed:
            continue
        if before_file is None:
            change = "added"
        elif after_file is None:
            change = "deleted"
        else:
            change = "modified"
        layers: list[str] = []
        if filesystem_changed:
            layers.append("filesystem")
        if index_changed:
            layers.append("index")
        result.append({"path": path, "change": change, "layers": layers})
    return result


def _copy_filtered_state(
    root: Path,
    source_root: Path,
    state: Mapping[str, Any],
    include_paths: set[str],
    *,
    label: str,
) -> None:
    entries = [entry for entry in state["files"] if entry["path"] in include_paths]
    _copy_tree_entries(source_root, entries, root, label=label)


def _make_delta_patch(
    record: Mapping[str, Any],
    current: Mapping[str, Any],
    changes: Sequence[Mapping[str, Any]],
    classified: Sequence[str],
    ignored: frozenset[str],
    fingerprint: str,
) -> tuple[str, str]:
    """Make an owned, content-only contribution patch without touching Git state."""
    attempt: Path = record["attempt"]
    inspection_root = _owned_directory(
        _owned_directory(attempt, "inspections", label="inspection records"),
        EVIDENCE_DERIVATION, label="current-derivation inspection records",
    )
    directory = inspection_root / fingerprint
    if directory.exists():
        existing = _canonical_existing_directory(directory, label="inspection record")
        if (existing / "contribution.patch").exists():
            patch = _canonical_existing_file(existing / "contribution.patch", label="contribution patch")
            return os.fspath(existing / "inspection.json"), os.fspath(patch)
        # Records are published by rename, so a directory without its patch
        # was damaged after publication.  It is helper-owned and cannot be
        # trusted; rebuild it rather than refusing this state forever.
        shutil.rmtree(existing)
    # Build in a private sibling and publish by rename, so an interrupted or
    # failed build never leaves a record that later calls mistake for complete.
    staging = inspection_root / f".partial-{fingerprint}-{uuid.uuid4().hex}"
    staging.mkdir(mode=0o700)
    try:
        staging = _canonical_existing_directory(staging, label="inspection staging record")
        # The side directories are named `a` and `b` and diffed with
        # --no-prefix, so headers already read `a/<path>`/`b/<path>` and the
        # patch bytes are used verbatim.  Rewriting the output instead would
        # also rewrite matching text inside changed lines.
        before = _owned_directory(staging, "a", label="inspection baseline")
        after = _owned_directory(staging, "b", label="inspection current state")
        changed_paths = {
            entry["path"] for entry in changes
            if entry["path"] not in ignored and not _selection_contains(classified, entry["path"])
        }
        baseline_files_root = _canonical_existing_directory(Path(record["baseline_data"]["baseline_files"]), label="baseline file store")
        _copy_filtered_state(before, baseline_files_root, record["baseline_data"]["worker_state"], changed_paths, label="inspection baseline file")
        worker = _repo_root(Path(record["worktree"]))
        _copy_filtered_state(after, worker, current, changed_paths, label="inspection current file")
        # --no-renames: `git apply` resolves a rename header's bare paths
        # without prefix stripping, so a detected rename could not apply.
        # The ceiling stops repository discovery at the staging directory, so
        # a repository that happens to enclose the store contributes no
        # configuration or attributes to the patch.  Without an index, a
        # global core.autocrlf would turn CRLF into LF on both sides.
        diff = _git(
            staging, "-c", "core.autocrlf=false", "diff", "--no-index", *PATCH_DIFF_FLAGS, "--no-renames", "--no-prefix",
            "--", "a", "b", check=False,
            extra_environment={"GIT_CEILING_DIRECTORIES": os.fspath(inspection_root)},
        )
        if diff.returncode not in {0, 1}:
            detail = diff.stderr.decode("utf-8", "replace").strip().splitlines()
            _fail("could not create contribution patch" + (f": {detail[-1]}" if detail else ""))
        _write_new_bytes(staging / "contribution.patch", diff.stdout)
        os.rename(staging, directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    directory = _canonical_existing_directory(directory, label="inspection record")
    return os.fspath(directory / "inspection.json"), os.fspath(directory / "contribution.patch")


def _exact_commit(repo: Path, value: str | None, *, label: str) -> str:
    """Resolve one explicit full commit SHA without accepting a movable ref."""
    if not isinstance(value, str) or not GIT_SHA_RE.fullmatch(value):
        _fail(f"{label} must be an exact full Git commit SHA")
    resolved = _git_text(repo, "rev-parse", "--verify", f"{value}^{{commit}}")
    if resolved != value:
        _fail(f"{label} did not resolve to that exact commit SHA")
    return resolved


def _nul_paths(repo: Path, *arguments: str, label: str) -> list[str]:
    return _split_nul_paths(_git(repo, *arguments).stdout, label=label)


def _residual_paths(worktree: Path) -> list[str]:
    """Return worker paths that remain outside HEAD after a commit handoff."""
    paths = set(_nul_paths(worktree, "diff", "--no-renames", "--name-only", "-z", "--cached", "HEAD", label="cached residual path"))
    paths.update(_nul_paths(worktree, "diff", "--no-renames", "--name-only", "-z", "HEAD", label="unstaged residual path"))
    paths.update(_nul_paths(worktree, "ls-files", "--others", "--exclude-standard", "-z", label="untracked residual path"))
    return sorted(paths)


def _clean_inherited_snapshot(record: Mapping[str, Any]) -> bool:
    """Commit delivery is deliberately limited to a clean captured caller state."""
    capture = record["baseline_data"].get("source_capture")
    if not isinstance(capture, Mapping):
        _fail("workspace baseline lacks a source capture for commit delivery")
    return (
        capture.get("staged_patch_sha256") == _sha256(b"")
        and capture.get("unstaged_patch_sha256") == _sha256(b"")
        and capture.get("untracked") == []
    )


def _write_delivery_evidence(
    record: Mapping[str, Any],
    fingerprint: str,
    evidence: Mapping[str, Any],
) -> str:
    """Persist mode-specific proof without changing the shared inspection record."""
    mode = evidence.get("mode")
    if mode not in {"patch", "commits", "report-only"}:
        _fail("delivery evidence has an unsupported mode")
    root = _owned_directory(
        _owned_directory(record["attempt"], "delivery-evidence", label="delivery evidence store"),
        EVIDENCE_DERIVATION, label="current-derivation delivery evidence",
    )
    directory = _owned_directory(root, fingerprint, label="delivery evidence directory")
    path = directory / f"{mode}.json"
    if path.exists():
        existing = _read_json_file(path, label="delivery evidence")
        if existing != dict(evidence):
            _fail("existing immutable delivery evidence does not match this inspection")
    else:
        _write_new_json(path, evidence)
    return os.fspath(path)


def _delivery_proof(
    record: Mapping[str, Any],
    worktree: Path,
    *,
    fingerprint: str,
    changed_paths: Sequence[str],
    contribution_paths: Sequence[str],
    artifacts: Sequence[str],
    discard: Sequence[str],
    contribution_patch: str,
    delivery_mode: str | None,
    commit_base: str | None,
    commits: Sequence[str],
) -> tuple[dict[str, Any] | None, str | None]:
    """Return optional mode-specific delivery evidence for a returned workspace.

    A patch is safe with an inherited dirty snapshot because it is generated
    against the captured worker baseline.  Commit handoff is intentionally
    narrower: its base must be a clean captured source HEAD, so a broad staging
    command cannot fold inherited caller work into a cherry-pick range.
    """
    if delivery_mode is None:
        if commit_base is not None or commits:
            _fail("commit arguments require an explicit --delivery-mode commits")
        return None, None
    if delivery_mode in {"patch", "report-only"} and (commit_base is not None or commits):
        _fail(f"{delivery_mode} delivery does not accept commit arguments")

    source_head = str(record["source"]["head"])
    common = {
        "schema": DELIVERY_SCHEMA,
        "version": VERSION,
        "receipt": record["receipt_path"],
        "fingerprint": fingerprint,
        "mode": delivery_mode,
        "base": source_head,
    }
    if delivery_mode == "patch":
        # The contribution patch carries working-tree bytes, but `git apply`
        # converts a new file through the target's attributes as they are
        # before the patch.  working-tree-encoding re-encodes and a filter
        # smudges already-converted bytes, and apply still exits 0, so refuse
        # when either the worker's or the caller's attributes convert a path.
        # (The worker's own view misses a patch that edits .gitattributes.)
        source, _ = _validate_binding(record, require_worktree=False)
        converted: set[str] = set()
        for attribute in ("working-tree-encoding", "filter"):
            for view in (worktree, source):
                converted.update(_paths_with_attribute(view, contribution_paths, attribute))
        if converted:
            _fail(
                "patch delivery cannot carry content that Git converts on write (working-tree-encoding "
                "or filter), because git apply would convert it again: " + ", ".join(sorted(converted))
                + "; use commits delivery or integrate these files by hand"
            )
        delivery = {
            "mode": "patch",
            "base": source_head,
            "contribution_patch": contribution_patch,
            "contribution_paths": list(contribution_paths),
        }
        evidence = dict(common)
        evidence.update(delivery)
        return delivery, _write_delivery_evidence(record, fingerprint, evidence)

    if delivery_mode == "report-only":
        inherited_paths = {
            item["path"] for item in record["baseline_data"]["worker_state"]["files"]
        } | {
            item["path"] for item in record["baseline_data"]["worker_state"]["index_entries"]
        }
        repository_input_changes = [path for path in changed_paths if path in inherited_paths]
        if repository_input_changes:
            _fail(
                "report-only delivery cannot classify edits to inherited repository inputs: "
                + ", ".join(repository_input_changes)
            )
        if contribution_paths:
            _fail(
                "report-only delivery has unclassified contribution paths: "
                + ", ".join(contribution_paths)
            )
        delivery = {
            "mode": "report-only",
            "base": source_head,
            "contribution_paths": [],
            "artifacts": list(artifacts),
            "discard": list(discard),
        }
        evidence = dict(common)
        evidence.update(delivery)
        return delivery, _write_delivery_evidence(record, fingerprint, evidence)

    if delivery_mode != "commits":  # argparse constrains this; retain import safety.
        _fail("delivery mode must be patch, commits, or report-only")
    if not _clean_inherited_snapshot(record):
        _fail(
            "commit delivery requires a clean inherited snapshot; retain this workspace "
            "and use delivery mode patch for caller staged, unstaged, or untracked inputs"
        )
    base = _exact_commit(worktree, commit_base, label="commit delivery base")
    if base != source_head:
        _fail("commit delivery base must equal the prepared source HEAD")
    if not commits:
        _fail("commit delivery requires at least one explicit --commit SHA")
    resolved_commits = [_exact_commit(worktree, commit, label="commit delivery contribution") for commit in commits]
    if len(set(resolved_commits)) != len(resolved_commits):
        _fail("commit delivery repeats a contribution commit SHA")
    head = _head(worktree)
    if resolved_commits[-1] != head:
        _fail("commit delivery final contribution SHA must equal the worker HEAD")
    range_commits = _git_text(worktree, "rev-list", "--reverse", f"{base}..{head}").splitlines()
    if range_commits != resolved_commits:
        _fail("commit delivery SHAs must name the complete base-to-HEAD contribution range in order")
    previous = base
    per_commit_paths: list[dict[str, Any]] = []
    for commit in resolved_commits:
        parents = _git_text(worktree, "show", "-s", "--format=%P", commit).split()
        if parents != [previous]:
            _fail("commit delivery requires a linear contribution range directly based on the prepared source HEAD")
        paths = _nul_paths(
            worktree,
            "diff",
            "--no-renames",
            "--name-only",
            "-z",
            "--diff-filter=ACDMRTUXB",
            previous,
            commit,
            label="individual committed contribution path",
        )
        if not paths:
            _fail(f"commit delivery contribution commit has no changed paths: {commit}")
        committed_classified = [path for path in paths if _selection_contains(list(artifacts) + list(discard), path)]
        if committed_classified:
            _fail(
                "commit delivery cannot put artifacts or discard paths in a contribution commit: "
                + ", ".join(committed_classified)
            )
        transient_paths = [path for path in paths if path not in contribution_paths]
        if transient_paths:
            _fail(
                "commit delivery contains paths outside the final worker contribution: "
                + ", ".join(transient_paths)
            )
        per_commit_paths.append({"commit": commit, "paths": paths})
        previous = commit

    commit_paths = _nul_paths(
        worktree,
        "diff",
        "--no-renames",
        "--name-only",
        "-z",
        "--diff-filter=ACDMRTUXB",
        base,
        head,
        label="committed contribution path",
    )
    classified = list(artifacts) + list(discard)
    committed_classified = [path for path in commit_paths if _selection_contains(classified, path)]
    if committed_classified:
        _fail(
            "commit delivery cannot classify committed paths as artifacts or discard: "
            + ", ".join(committed_classified)
        )
    residual_paths = _residual_paths(worktree)
    residual_unclassified = [path for path in residual_paths if not _selection_contains(classified, path)]
    if residual_unclassified:
        _fail(
            "commit delivery has residual staged, unstaged, or untracked deliverables: "
            + ", ".join(residual_unclassified)
        )
    if commit_paths != list(contribution_paths):
        _fail(
            "commit delivery committed paths do not exactly match the worker contribution: "
            f"committed={','.join(commit_paths) or '(none)'} "
            f"contribution={','.join(contribution_paths) or '(none)'}"
        )
    delivery = {
        "mode": "commits",
        "base": base,
        "commits": resolved_commits,
        "commit_paths": commit_paths,
        "per_commit_paths": per_commit_paths,
        "residual_paths": residual_paths,
    }
    evidence = dict(common)
    evidence.update(delivery)
    return delivery, _write_delivery_evidence(record, fingerprint, evidence)


def _inspect_record(
    record: Mapping[str, Any],
    phase: str,
    artifacts: Sequence[str] = (),
    discard: Sequence[str] = (),
    delivery_mode: str | None = None,
    commit_base: str | None = None,
    commits: Sequence[str] = (),
) -> dict[str, Any]:
    if phase not in {"prepared", "returned"}:
        _fail("inspection phase must be prepared or returned")
    if phase == "prepared" and (delivery_mode is not None or commit_base is not None or commits):
        _fail("delivery proof is available only for a returned workspace")
    artifact_paths = _normal_paths(artifacts, label="artifact path")
    discard_paths = _normal_paths(discard, label="discard path")
    overlap = sorted(set(artifact_paths) & set(discard_paths))
    if overlap:
        _fail(f"artifact and discard paths overlap: {overlap[0]}")
    _, worktree = _validate_binding(record)
    assert worktree is not None
    current = _worker_state(worktree)
    baseline_state = record["baseline_data"]["worker_state"]
    if phase == "prepared":
        if current != baseline_state:
            _fail("worker baseline drifted before dispatch; prepare retry cannot reuse this attempt")
        result = _base_output(record, "prepared")
        result.update({"phase": "prepared", "fingerprint": _state_fingerprint(current), "changed_paths": [], "contribution_paths": []})
        return result
    changes = _changes(baseline_state, current)
    # A filesystem-only patch is not proof of an index-only contribution (for
    # example `git add` followed by restoring the working file).  Preserve the
    # workspace rather than emitting misleading integration evidence.
    index_only = [item["path"] for item in changes if item["layers"] == ["index"]]
    if index_only:
        _fail("returned inspect refuses index-only worker deltas without separate staged evidence: " + ", ".join(index_only))
    changed_paths = [entry["path"] for entry in changes]
    for path in artifact_paths + discard_paths:
        if not any(path == changed or changed.startswith(path + "/") for changed in changed_paths):
            _fail(f"selected artifact/discard path is not a changed worker path: {path}")
    classified = artifact_paths + discard_paths
    # Explicit classification wins; remaining ignored generated output is
    # reported but is neither contribution nor patch content.  Ignored
    # entries are exact paths, so a set keeps this linear for large installs.
    ignored_paths = [
        path for path in _ignored_added_paths(worktree, changes)
        if not _selection_contains(classified, path)
    ]
    ignored = frozenset(ignored_paths)
    fingerprint = _inspection_fingerprint(current, artifact_paths, discard_paths, ignored_paths)
    contribution_paths = [
        path for path in changed_paths
        if path not in ignored and not _selection_contains(classified, path)
    ]
    inspection_path, patch_path = _make_delta_patch(record, current, changes, classified, ignored, fingerprint)
    inspection = {
        "schema": INSPECTION_SCHEMA,
        "version": VERSION,
        "receipt": record["receipt_path"],
        "phase": "returned",
        "fingerprint": fingerprint,
        "baseline_fingerprint": record["baseline_data"]["worker_state_fingerprint"],
        "changed": changes,
        "artifacts": artifact_paths,
        "discard": discard_paths,
        "contribution_paths": contribution_paths,
        "contribution_patch": patch_path,
        "git_state_changed": {
            "head": current["head"] != baseline_state["head"],
            "branch": current["branch"] != baseline_state["branch"],
            "cached_layer": current["cached_patch_sha256"] != baseline_state["cached_patch_sha256"],
            "unstaged_layer": current["unstaged_patch_sha256"] != baseline_state["unstaged_patch_sha256"],
        },
    }
    # Present only when non-empty, so records and output for the common case
    # stay byte-identical to earlier helper versions and exact-key consumers.
    if ignored_paths:
        inspection["ignored_paths"] = ignored_paths
    inspection_file = Path(inspection_path)
    if inspection_file.exists():
        existing = _read_json_file(inspection_file, label="inspection record")
        if existing != inspection:
            _fail("existing immutable inspection record does not match current inspection")
    else:
        _write_new_json(inspection_file, inspection)
    result = _base_output(record, "returned")
    result.update({
        "phase": "returned",
        "fingerprint": fingerprint,
        "changed_paths": changed_paths,
        "contribution_paths": contribution_paths,
        "artifacts": artifact_paths,
        "discard": discard_paths,
        "evidence": {"inspection": inspection_path, "contribution_patch": patch_path},
    })
    if ignored_paths:
        result["ignored_paths"] = ignored_paths
    delivery, delivery_evidence = _delivery_proof(
        record,
        worktree,
        fingerprint=fingerprint,
        changed_paths=changed_paths,
        contribution_paths=contribution_paths,
        artifacts=artifact_paths,
        discard=discard_paths,
        contribution_patch=patch_path,
        delivery_mode=delivery_mode,
        commit_base=commit_base,
        commits=commits,
    )
    if delivery is not None:
        result["delivery"] = delivery
        assert delivery_evidence is not None
        result["evidence"]["delivery"] = delivery_evidence
        result["delivery_evidence"] = delivery_evidence
    return result


def prepare(
    *,
    source: Path | None = None,
    store: Path | None = None,
    label: str | None = None,
    receipt: Path | None = None,
    writers_quiescent: bool = False,
) -> dict[str, Any]:
    """Create a fresh workspace or validate/reuse one exact pre-dispatch attempt."""
    if not writers_quiescent:
        _fail("prepare requires the explicit --writers-quiescent assertion")
    _require_no_git_context_environment_overrides("prepare")
    if receipt is not None:
        if label is not None or store is not None:
            _fail("prepare --receipt cannot select a new label or store")
        record = _load_receipt(receipt)
        if source is not None and _repo_root(source) != _repo_root(Path(record["source"]["root"])):
            _fail("prepare --source does not match the receipt source")
        source_root, _ = _validate_binding(record)
        current_source = _capture_source(source_root)
        expected_source = record["baseline_data"]["source_capture"]
        if current_source.comparable() != expected_source:
            _fail("source drifted since preparation; a same-attempt retry is unsafe")
        with _attempt_lock(record["attempt"]):
            result = _inspect_record(record, "prepared")
        result["reused"] = True
        return result
    if source is None:
        _fail("prepare requires --source or --receipt")
    return _new_prepare(source, store, label)


def inspect(
    *,
    receipt: Path,
    phase: str,
    artifacts: Sequence[str] = (),
    discard: Sequence[str] = (),
    delivery_mode: str | None = None,
    commit_base: str | None = None,
    commits: Sequence[str] = (),
) -> dict[str, Any]:
    """Verify the pre-dispatch baseline or inspect a returned worker state."""
    record = _load_receipt(receipt)
    with _attempt_lock(record["attempt"]):
        return _inspect_record(record, phase, artifacts, discard, delivery_mode, commit_base, commits)


def _required_string(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        _fail(f"acceptance {label} must be a nonempty string")
    return value


def _load_acceptance(path: Path) -> dict[str, Any]:
    value = _read_json_file(path, label="acceptance")
    if not isinstance(value, dict):
        _fail("acceptance must be a JSON object")
    required = {
        "schema", "inspection_fingerprint", "decision", "workers_stopped",
        "completion_reference", "acceptance_reference", "artifacts", "discard",
    }
    if set(value) != required or value.get("schema") != ACCEPTANCE_SCHEMA:
        _fail("acceptance has an unsupported schema")
    fingerprint = value.get("inspection_fingerprint")
    if not isinstance(fingerprint, str) or not SHA256_RE.fullmatch(fingerprint):
        _fail("acceptance has an invalid inspection_fingerprint")
    if value.get("decision") not in {"integrated", "report-consumed"}:
        _fail("acceptance decision must be integrated or report-consumed")
    if value.get("workers_stopped") is not True:
        _fail("acceptance must explicitly attest workers_stopped: true")
    _required_string(value.get("completion_reference"), label="completion_reference")
    _required_string(value.get("acceptance_reference"), label="acceptance_reference")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, list):
        _fail("acceptance artifacts must be a list")
    normalized_artifacts: list[dict[str, str]] = []
    seen_artifacts: set[str] = set()
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"path", "purpose"}:
            _fail("acceptance artifact must contain exactly path and purpose")
        path_value = _safe_rel(item.get("path"), label="acceptance artifact path")
        purpose = _required_string(item.get("purpose"), label="artifact purpose")
        if path_value in seen_artifacts:
            _fail(f"acceptance repeats artifact path: {path_value}")
        seen_artifacts.add(path_value)
        normalized_artifacts.append({"path": path_value, "purpose": purpose})
    discard = value.get("discard")
    if not isinstance(discard, list):
        _fail("acceptance discard must be a list")
    normalized_discard = _normal_paths(discard, label="acceptance discard path")
    overlap = set(normalized_discard) & seen_artifacts
    if overlap:
        _fail(f"acceptance artifact/discard overlap: {sorted(overlap)[0]}")
    result = dict(value)
    result["artifacts"] = normalized_artifacts
    result["discard"] = normalized_discard
    return result


def _artifact_file(worktree: Path, relative: str) -> Path:
    safe = _safe_rel(relative, label="artifact path")
    current = worktree
    parts = PurePosixPath(safe).parts
    for part in parts[:-1]:
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            _fail(f"cannot inspect artifact parent {safe}: {exc}")
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            _fail(f"artifact path traverses an unsafe parent: {safe}")
    path = current / parts[-1]
    try:
        info = path.lstat()
    except OSError as exc:
        _fail(f"cannot inspect artifact {safe}: {exc}")
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        _fail(f"artifact must be a regular non-symlink file: {safe}")
    return path


def _archive_artifact(record: Mapping[str, Any], worktree: Path, artifact: Mapping[str, str]) -> dict[str, str]:
    relative = artifact["path"]
    source = _artifact_file(worktree, relative)
    source_sha = _sha256_file(source)
    results = _owned_directory(record["attempt"], "results", label="durable results")
    target = _under_owned(results, relative, label="archive path")
    try:
        existing = target.lstat()
    except FileNotFoundError:
        existing = None
    except OSError as exc:
        _fail(f"cannot inspect archive target {relative}: {exc}")
    if existing is not None:
        if stat.S_ISLNK(existing.st_mode) or not stat.S_ISREG(existing.st_mode):
            _fail(f"archive target is unsafe: {relative}")
        if _sha256_file(target) != source_sha:
            _fail(f"archive collision has different bytes: {relative}")
    else:
        try:
            with source.open("rb") as input_handle:
                with target.open("xb") as output_handle:
                    shutil.copyfileobj(input_handle, output_handle, length=1024 * 1024)
            os.chmod(target, 0o444)
        except OSError as exc:
            _fail(f"cannot archive artifact {relative}: {exc}")
    if _sha256_file(target) != source_sha:
        _fail(f"archived artifact did not verify: {relative}")
    return {"path": relative, "purpose": artifact["purpose"], "archive": os.fspath(target), "sha256": source_sha}


def _read_closed_outcome(record: Mapping[str, Any]) -> dict[str, Any] | None:
    path = record["attempt"] / "close.json"
    if not path.exists():
        return None
    value = _read_json_file(path, label="close outcome")
    if not isinstance(value, dict) or value.get("schema") != "ask-agent.workspace.close.v1" or value.get("status") != "closed":
        _fail("close outcome has an unsupported schema")
    if value.get("receipt") != record["receipt_path"] or value.get("worktree") != record["worktree"] or value.get("branch") != record["branch"]:
        _fail("close outcome does not match workspace receipt")
    return value


def check_context(*, receipt: Path) -> dict[str, Any]:
    """Verify the helper process's current directory is the assigned worktree.

    This deliberately attests only the process executing this command.  It does
    not establish a native agent's startup directory or sandbox isolation.
    """
    record = _load_receipt(receipt)
    with _attempt_lock(record["attempt"]):
        if _read_closed_outcome(record) is not None:
            _fail("workspace is closed; cannot check its current operation context")
        _require_no_git_context_environment_overrides("current operation")
        _, worktree = _validate_binding(record)
        assert worktree is not None
        actual_cwd = _canonical_existing_directory(Path.cwd(), label="current working directory")
        if not _is_under(actual_cwd, worktree):
            _fail("current working directory is outside the assigned worker worktree")
        git_root = _repo_root(actual_cwd)
        if git_root != worktree:
            _fail("current Git root does not match the assigned worker worktree")
        result = _base_output(record, "verified")
        result.update({
            "schema": CONTEXT_SCHEMA,
            "version": VERSION,
            "attempt": record["attempt_id"],
            "actual_cwd": os.fspath(actual_cwd),
            "git_root": os.fspath(git_root),
            "head": _head(git_root),
            "operation": "current-process working directory and Git root",
            "scope": "does not attest native startup directory or sandbox isolation",
        })
        return result


def _registered_path_present(source: Path, worktree: Path, *, minimum_timeout: float = 0.0) -> bool:
    expected = os.path.normpath(os.fspath(worktree))
    for item in _registered_worktrees(source, minimum_timeout=minimum_timeout):
        raw = item.get("worktree")
        if raw and os.path.normpath(os.path.abspath(raw)) == expected:
            return True
    return False


def _load_close_eligibility(record: Mapping[str, Any]) -> dict[str, Any] | None:
    path = record["attempt"] / "close-eligibility.json"
    if not path.exists():
        return None
    value = _read_json_file(path, label="close eligibility")
    required = {"schema", "receipt", "fingerprint", "decision", "archived_artifacts"}
    if not isinstance(value, dict) or set(value) != required or value.get("schema") != "ask-agent.workspace.close-eligibility.v1":
        _fail("close eligibility has an unsupported schema")
    if value.get("receipt") != record["receipt_path"]:
        _fail("close eligibility belongs to a different receipt")
    if not isinstance(value.get("fingerprint"), str) or not SHA256_RE.fullmatch(value["fingerprint"]):
        _fail("close eligibility has an invalid fingerprint")
    if value.get("decision") not in {"integrated", "report-consumed"}:
        _fail("close eligibility has an invalid decision")
    artifacts = value.get("archived_artifacts")
    if not isinstance(artifacts, list):
        _fail("close eligibility has invalid archived artifacts")
    seen: set[str] = set()
    results = record["attempt"] / "results"
    checked: list[dict[str, str]] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {"path", "purpose", "archive", "sha256"}:
            _fail("close eligibility has an invalid archived artifact")
        relative = _safe_rel(artifact.get("path"), label="archived artifact path")
        purpose = _required_string(artifact.get("purpose"), label="archived artifact purpose")
        if relative in seen:
            _fail(f"close eligibility repeats archived artifact: {relative}")
        seen.add(relative)
        archive = artifact.get("archive")
        digest = artifact.get("sha256")
        expected = results.joinpath(*PurePosixPath(relative).parts)
        if not isinstance(archive, str) or Path(archive) != expected:
            _fail("close eligibility archive path escapes durable results")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            _fail("close eligibility has invalid artifact hash")
        actual = _canonical_existing_file(expected, label="archived artifact")
        if _sha256_file(actual) != digest:
            _fail("close eligibility archived artifact hash no longer matches")
        checked.append({"path": relative, "purpose": purpose, "archive": os.fspath(actual), "sha256": digest})
    result = dict(value)
    result["archived_artifacts"] = checked
    return result


def _closed_outcome(record: Mapping[str, Any], eligibility: Mapping[str, Any]) -> dict[str, Any]:
    results_root = record["attempt"] / "results"
    outcome = _base_output(record, "closed")
    outcome.update({
        "schema": "ask-agent.workspace.close.v1",
        "removed": True,
        "results_root": os.fspath(results_root),
        "archived_artifacts": eligibility["archived_artifacts"],
        "decision": eligibility["decision"],
        "inspection_fingerprint": eligibility["fingerprint"],
        "semantic_acceptance": "parent attestation; helper did not independently prove worker stop or integration",
    })
    return outcome


def _recover_closed_outcome(record: Mapping[str, Any]) -> dict[str, Any] | None:
    """Recover only the narrow post-removal/pre-outcome-write crash window."""
    eligibility = _load_close_eligibility(record)
    if eligibility is None:
        return None
    try:
        source, _ = _validate_binding(record, require_worktree=False)
    except WorkspaceError:
        return None
    worker_path = Path(record["worktree"])
    try:
        worker_path.lstat()
    except FileNotFoundError:
        missing = True
    except OSError:
        return None
    else:
        missing = False
    if not missing or _registered_path_present(source, worker_path):
        return None
    branch = _git(source, "show-ref", "--verify", "--quiet", f"refs/heads/{record['branch']}", check=False)
    if branch.returncode:
        return None
    outcome = _closed_outcome(record, eligibility)
    _write_new_json(record["attempt"] / "close.json", outcome)
    return outcome


def _retained(record: Mapping[str, Any], reason: str, **details: Any) -> dict[str, Any]:
    value = _base_output(record, "retained")
    value.update({"removed": False, "reason": reason})
    value.update(details)
    return value


def close(*, receipt: Path, acceptance: Path | None = None) -> dict[str, Any]:
    """Archive explicitly approved artifacts and remove only an eligible worker tree."""
    record = _load_receipt(receipt)
    with _attempt_lock(record["attempt"]):
        prior = _read_closed_outcome(record)
        if prior is not None:
            return prior
        recovered = _recover_closed_outcome(record)
        if recovered is not None:
            return recovered
        if acceptance is None:
            return _retained(record, "parent acceptance is required before close")
        try:
            accepted = _load_acceptance(acceptance)
        except WorkspaceError as exc:
            # An invalid attestation never authorizes removal.  Probe the
            # workspace first so a stronger local safety condition (such as an
            # index-only returned delta) is visible to the parent rather than
            # being hidden behind a malformed acceptance file.
            try:
                _inspect_record(record, "returned")
            except WorkspaceError as inspect_error:
                return _retained(record, f"cannot verify returned worker state: {inspect_error}")
            return _retained(record, f"acceptance is incomplete or invalid: {exc}")
        try:
            source, worktree = _validate_binding(record)
            assert worktree is not None
        except WorkspaceError as exc:
            return _retained(record, str(exc))
        artifacts = [item["path"] for item in accepted["artifacts"]]
        try:
            returned = _inspect_record(record, "returned", artifacts, accepted["discard"])
        except WorkspaceError as exc:
            return _retained(record, f"cannot verify returned worker state: {exc}")
        if returned["fingerprint"] != accepted["inspection_fingerprint"]:
            return _retained(record, "worker state changed after the accepted inspection fingerprint", observed_fingerprint=returned["fingerprint"])
        if accepted["decision"] == "report-consumed":
            inherited_paths = {
                item["path"] for item in record["baseline_data"]["worker_state"]["files"]
            } | {
                item["path"] for item in record["baseline_data"]["worker_state"]["index_entries"]
            }
            repository_input_changes = [path for path in returned["changed_paths"] if path in inherited_paths]
            if repository_input_changes:
                return _retained(
                    record,
                    "report-consumed acceptance cannot discard or archive edits to inherited repository inputs",
                    repository_input_changes=repository_input_changes,
                )
            if returned["contribution_paths"]:
                return _retained(
                    record,
                    "report-consumed acceptance has unapproved worker contribution paths",
                    contribution_paths=returned["contribution_paths"],
                )
        try:
            archived = [_archive_artifact(record, worktree, artifact) for artifact in accepted["artifacts"]]
        except WorkspaceError as exc:
            return _retained(record, f"cannot safely archive approved artifacts: {exc}")
        # Archiving may take long enough for an outside writer to arrive.  The
        # acceptance fingerprint covers every worker file (including ignored
        # generated entries), so check it again immediately before Git removal.
        # This cannot detect an ABA write after the check; workers_stopped stays
        # an explicit parent attestation for that remaining boundary.
        try:
            after_archive = _inspect_record(record, "returned", artifacts, accepted["discard"])
        except WorkspaceError as exc:
            return _retained(record, f"cannot verify worker state after artifact archive: {exc}", archived_artifacts=archived)
        if after_archive["fingerprint"] != accepted["inspection_fingerprint"]:
            return _retained(
                record,
                "worker state changed while approved artifacts were archived",
                observed_fingerprint=after_archive["fingerprint"],
                archived_artifacts=archived,
            )
        eligibility = record["attempt"] / "close-eligibility.json"
        current_eligibility = {
            "schema": "ask-agent.workspace.close-eligibility.v1",
            "receipt": record["receipt_path"],
            "fingerprint": returned["fingerprint"],
            "decision": accepted["decision"],
            "archived_artifacts": archived,
        }
        if not eligibility.exists():
            _write_new_json(eligibility, current_eligibility)
        elif _read_json_file(eligibility, label="close eligibility") != current_eligibility:
            # A prior close attempt with a different acceptance did not remove
            # the (still registered) worktree, so its eligibility never took
            # effect.  Publish this acceptance's record by atomic replacement
            # so the closed outcome describes the acceptance that removed it.
            replacement = record["attempt"] / f".close-eligibility-{uuid.uuid4().hex}.json"
            _write_new_json(replacement, current_eligibility)
            os.replace(replacement, eligibility)
        removed = _git(source, "worktree", "remove", "--force", os.fspath(worktree), check=False)
        if removed.returncode:
            detail = removed.stderr.decode("utf-8", "replace").strip().splitlines()
            return _retained(record, "Git refused eligible worktree removal" + (f": {detail[-1]}" if detail else ""), archived_artifacts=archived)
        # Git's registry is the deletion authority.  Check it is gone before
        # recording a durable closed outcome; the branch is intentionally kept.
        for item in _registered_worktrees(source):
            try:
                candidate = Path(item.get("worktree", "")).resolve(strict=True)
            except (OSError, RuntimeError):
                continue
            if candidate == worktree:
                return _retained(record, "Git still registers the worker worktree after removal", archived_artifacts=archived)
        eligibility_data = _load_close_eligibility(record)
        if eligibility_data is None:  # written above; retain a fail-closed guard for future edits
            _fail("close eligibility record disappeared before outcome write")
        outcome = _closed_outcome(record, eligibility_data)
        _write_new_json(record["attempt"] / "close.json", outcome)
        return outcome


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # pragma: no cover - exercised through main
        raise WorkspaceError(message)


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="ask_agent_workspace.py", description="Manage an Ask Agent Git worktree")
    commands = parser.add_subparsers(dest="command", required=True)
    identity_parser = commands.add_parser("identity")
    identity_parser.add_argument("--skill-card", required=True)
    capabilities_parser = commands.add_parser("capabilities")
    capabilities_parser.add_argument("--skill-card", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--source")
    prepare_parser.add_argument("--store")
    prepare_parser.add_argument("--label")
    prepare_parser.add_argument("--receipt")
    prepare_parser.add_argument("--writers-quiescent", action="store_true")
    inspect_parser = commands.add_parser("inspect")
    inspect_parser.add_argument("--receipt", required=True)
    inspect_parser.add_argument("--phase", required=True, choices=("prepared", "returned"))
    inspect_parser.add_argument("--artifact", action="append", default=[])
    inspect_parser.add_argument("--discard", action="append", default=[])
    inspect_parser.add_argument("--delivery-mode", choices=("patch", "commits", "report-only"))
    inspect_parser.add_argument("--commit-base")
    inspect_parser.add_argument("--commit", action="append", default=[])
    context_parser = commands.add_parser("check-context")
    context_parser.add_argument("--receipt", required=True)
    close_parser = commands.add_parser("close")
    close_parser.add_argument("--receipt", required=True)
    close_parser.add_argument("--acceptance")
    return parser


def _emit(value: Mapping[str, Any]) -> None:
    sys.stdout.write(json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n")


def _terminate(signum: int, _frame: Any) -> None:
    """Turn a termination signal into an exception so cleanup and Git stops run.

    Git runs in its own session, so a signal sent to the helper's process
    group no longer reaches it directly; unwinding through `_git` stops it.
    """
    raise SystemExit(128 + signum)


def main(argv: Sequence[str] | None = None) -> int:
    for signum in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, _terminate)
    try:
        parsed = _parser().parse_args(argv)
        if parsed.command == "identity":
            result = identity(skill_card=Path(parsed.skill_card))
        elif parsed.command == "capabilities":
            result = capabilities(skill_card=Path(parsed.skill_card))
        elif parsed.command == "prepare":
            result = prepare(
                source=Path(parsed.source) if parsed.source else None,
                store=Path(parsed.store) if parsed.store else None,
                label=parsed.label,
                receipt=Path(parsed.receipt) if parsed.receipt else None,
                writers_quiescent=parsed.writers_quiescent,
            )
        elif parsed.command == "inspect":
            result = inspect(
                receipt=Path(parsed.receipt),
                phase=parsed.phase,
                artifacts=parsed.artifact,
                discard=parsed.discard,
                delivery_mode=parsed.delivery_mode,
                commit_base=parsed.commit_base,
                commits=parsed.commit,
            )
        elif parsed.command == "check-context":
            result = check_context(receipt=Path(parsed.receipt))
        elif parsed.command == "close":
            result = close(receipt=Path(parsed.receipt), acceptance=Path(parsed.acceptance) if parsed.acceptance else None)
        else:  # argparse constrains this; retain a fail-closed guard for imports.
            _fail("unknown workspace command")
        _emit(result)
        return 0
    except (WorkspaceError, OSError, ValueError, OverflowError) as exc:
        _emit({"status": "error", "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
