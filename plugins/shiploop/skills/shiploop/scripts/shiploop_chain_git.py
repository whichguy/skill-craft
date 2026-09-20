#!/usr/bin/env python3
"""Small fail-closed Git primitives for a persisted ShipLoop chain.

The caller owns the run lock, durable intent, and journal.  This module only
checks the Git boundaries used by that caller: an initiating checkout remains
frozen while a separately allocated worktree produces a committed descendant,
then the initiating branch fast-forwards to that exact commit.

These checks coordinate cooperative local processes.  ``fast_forward`` also
uses a nonblocking advisory lock in the actual target worktree's private Git
directory.  That lock only serializes cooperative chain returns; manual Git
writers can ignore it, and it is not a compare-and-swap or exactly-once
guarantee.  These checks deliberately do not claim to be a sandbox against a
malicious process that can modify the repository, Git metadata, or persisted
plan concurrently.
"""

from __future__ import annotations

import errno
import fcntl
import hashlib
import os
import re
import stat
import subprocess
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, Optional, Sequence


class ChainGitError(ValueError):
    """A chain Git boundary could not be proven safely."""


__all__ = [
    "ChainGitError",
    "adopt_managed_workspace",
    "adopt_workspace",
    "allocation_plan",
    "allocate",
    "bind_worker_instance",
    "fast_forward",
    "inspect_contribution",
    "inspect_prepared",
    "inspect_removed",
    "inspect_superseded_removed",
    "prepare_integration",
    "recover_allocation",
    "remove_worker",
    "remove_superseded_worker",
    "target_identity",
    "validate_target",
]


_IDENTITY_KEYS = ("repo", "git_dir", "common_dir", "branch", "head")
_WORKER_INSTANCE_KEYS = ("root", "git_dir")
_FILESYSTEM_INSTANCE_KEYS = ("device", "inode")
_SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_STEM = re.compile(
    r"(?P<run>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})-"
    r"(?P<attempt>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})-"
    r"(?P<digest>[0-9a-f]{16})"
)
_BRANCH_PREFIX = "shiploop/chain-"
_PATH_PREFIX = "shiploop-chain-"
_RETURN_LOCK_NAME = "shiploop-chain-return.lock"
_LEGACY_LIFECYCLE = "final-return"
_PER_STEP_LIFECYCLE = "per-step"
_PREPARED_MERGE_PREFIX = "ShipLoop chain prepared"
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
    raise ChainGitError(message)


def _git(
    repo: Path,
    *args: str,
    readonly: bool = True,
    pass_fds: Sequence[int] = (),
) -> subprocess.CompletedProcess[bytes]:
    """Run Git with an argv-only, non-interactive, sanitized environment."""
    inherited_fds = tuple(pass_fds)
    if any(isinstance(fd, bool) or not isinstance(fd, int) or fd < 0 for fd in inherited_fds):
        _fail("Git inherited file descriptor is invalid")
    env = dict(os.environ)
    for key in list(env):
        if key in _GIT_ENV_KEYS or key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
            env.pop(key, None)
    env["GIT_TERMINAL_PROMPT"] = "0"
    if readonly:
        env["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        return subprocess.run(
            ["git", "-c", "core.hooksPath=/dev/null", "-C", os.fspath(repo), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=env,
            shell=False,
            timeout=45,
            close_fds=True,
            pass_fds=inherited_fds,
        )
    except FileNotFoundError as exc:
        _fail("git is not available on PATH")
        raise AssertionError from exc
    except subprocess.TimeoutExpired as exc:
        _fail(f"git timed out while running {' '.join(args[:2])}")
        raise AssertionError from exc


def _git_text(repo: Path, *args: str, readonly: bool = True) -> str:
    result = _git(repo, *args, readonly=readonly)
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        _fail(f"git {' '.join(args[:2])} failed{suffix}")
    return result.stdout.decode("utf-8", "surrogateescape").strip()


def _absolute_path(value: Any, *, label: str) -> Path:
    raw = os.fspath(value) if isinstance(value, os.PathLike) else value
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        _fail(f"{label} must be a nonempty absolute path")
    path = Path(raw)
    if not path.is_absolute() or any(part in (".", "..") for part in path.parts):
        _fail(f"{label} must be a normalized absolute path")
    return path


def _existing_dir(path: Path, *, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        _fail(f"cannot resolve {label}: {exc}")
        raise AssertionError from exc
    if not resolved.is_dir():
        _fail(f"{label} is not a directory")
    return resolved


def _canonical_candidate(path: Path, *, label: str) -> Path:
    """Resolve an existing path or a nonexistent child through its real parent."""
    if not path.is_absolute():
        _fail(f"{label} must be absolute")
    cursor = path
    missing = []
    while not os.path.lexists(cursor):
        if cursor == cursor.parent or not cursor.name:
            _fail(f"cannot find an existing parent for {label}")
        missing.append(cursor.name)
        cursor = cursor.parent
    if cursor.is_symlink():
        _fail(f"{label} resolves through a symlink")
    resolved = _existing_dir(cursor, label=label)
    for part in reversed(missing):
        resolved /= part
    return resolved


def _reject_symlink_redirection(path: Path, *, label: str) -> None:
    """Reject caller-controlled links while allowing macOS's system aliases."""
    system_aliases = {
        Path("/var"): Path("/private/var"),
        Path("/tmp"): Path("/private/tmp"),
        Path("/etc"): Path("/private/etc"),
    }
    cursor = path
    while True:
        if cursor.is_symlink():
            try:
                target = cursor.resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                _fail(f"cannot resolve {label} symlink: {exc}")
                raise AssertionError from exc
            if system_aliases.get(cursor) != target:
                _fail(f"{label} resolves through a symlink")
        if cursor == cursor.parent:
            break
        cursor = cursor.parent


def _repo_root(value: Any) -> Path:
    if isinstance(value, Path):
        supplied = value
    elif isinstance(value, str) and value:
        supplied = Path(value)
    else:
        _fail("repository must be a directory path")
        raise AssertionError
    candidate = _existing_dir(supplied, label="repository")
    if _git_text(candidate, "rev-parse", "--is-inside-work-tree") != "true":
        _fail("repository is not a Git worktree")
    top = _git_text(candidate, "rev-parse", "--path-format=absolute", "--show-toplevel")
    if not Path(top).is_absolute():
        _fail("Git returned a non-absolute repository root")
    return _existing_dir(Path(top), label="repository root")


def _git_directory(repo: Path, argument: str, *, label: str) -> Path:
    value = _git_text(repo, "rev-parse", "--path-format=absolute", argument)
    path = Path(value)
    if not path.is_absolute():
        _fail(f"Git returned a non-absolute {label}")
    return _existing_dir(path, label=label)


def _git_path(repo: Path, name: str) -> Path:
    value = _git_text(repo, "rev-parse", "--path-format=absolute", "--git-path", name)
    path = Path(value)
    if not path.is_absolute():
        _fail(f"Git returned a non-absolute path for {name}")
    return path


def _branch(repo: Path) -> str:
    result = _git(repo, "symbolic-ref", "--quiet", "--short", "HEAD")
    if result.returncode:
        _fail("repository HEAD is detached; a named branch is required")
    value = result.stdout.decode("utf-8", "surrogateescape").strip()
    if not value or value.startswith("-") or "\x00" in value or "\n" in value or "\r" in value:
        _fail("repository branch is unsafe")
    return _branch_name(repo, value, label="repository branch")


def _branch_name(repo: Path, value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("-") or "\x00" in value:
        _fail(f"{label} is invalid")
    checked = _git(repo, "check-ref-format", f"refs/heads/{value}")
    if checked.returncode:
        _fail(f"{label} is invalid")
    return value


def _head(repo: Path) -> str:
    value = _git_text(repo, "rev-parse", "--verify", "HEAD")
    if not _SHA.fullmatch(value):
        _fail("repository HEAD is not a full commit SHA")
    return value


def _assert_clean(repo: Path) -> None:
    result = _git(
        repo,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignored=no",
    )
    if result.returncode:
        _fail("cannot inspect repository status")
    if result.stdout:
        _fail("repository must be clean, including staged and untracked paths")


def _assert_no_active_operation(repo: Path, git_dir: Path) -> None:
    """Reject clean paused Git operations before allocating or returning work."""
    markers = (
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "REBASE_HEAD",
        "rebase-apply",
        "rebase-merge",
        "sequencer",
        "BISECT_START",
    )
    for marker in markers:
        # Worktree-specific state normally lives in the private Git directory.
        # --git-path also covers Git versions/configurations that place a given
        # operation marker elsewhere without treating a sibling's state as the
        # initiating checkout's operation.
        paths = {git_dir / marker, _git_path(repo, marker)}
        if any(os.path.lexists(path) for path in paths):
            _fail(f"repository has an active Git operation: {marker}")


def target_identity(repo: Path | str) -> Dict[str, str]:
    """Return the canonical clean, symbolic-branch identity of one worktree."""
    root = _repo_root(repo)
    git_dir = _git_directory(root, "--absolute-git-dir", label="private Git directory")
    common_dir = _git_directory(root, "--git-common-dir", label="Git common directory")
    _assert_no_active_operation(root, git_dir)
    identity = {
        "repo": os.fspath(root),
        "git_dir": os.fspath(git_dir),
        "common_dir": os.fspath(common_dir),
        "branch": _branch(root),
        "head": _head(root),
    }
    _assert_clean(root)
    return identity


def _identity_values(value: Any) -> Dict[str, str]:
    if not isinstance(value, Mapping):
        _fail("target identity must be an object")
    result: Dict[str, str] = {}
    for key in _IDENTITY_KEYS:
        item = value.get(key)
        if not isinstance(item, str) or not item:
            _fail(f"target identity has invalid {key}")
        result[key] = item
    for key in ("repo", "git_dir", "common_dir"):
        _absolute_path(result[key], label=f"target identity {key}")
    if not _SHA.fullmatch(result["head"]):
        _fail("target identity has invalid head")
    return result


def _filesystem_instance(path: Path, *, label: str) -> Dict[str, int]:
    """Return the stable directory identity used by cooperative cleanup guards."""
    try:
        value = os.stat(path)
    except OSError as exc:
        _fail(f"cannot stat {label}: {exc}")
        raise AssertionError from exc
    if not stat.S_ISDIR(value.st_mode):
        _fail(f"{label} is not a directory")
    return {"device": value.st_dev, "inode": value.st_ino}


def _worker_instance(root: Path, git_dir: Path) -> Dict[str, Dict[str, int]]:
    # Device/inode values make a cooperating-writer ABA fence for recreated
    # worktrees.  They are not a security guarantee: filesystems may reuse an
    # inode pair, and a process that can rewrite Git/ledger state can race it.
    return {
        "root": _filesystem_instance(root, label="worker root"),
        "git_dir": _filesystem_instance(git_dir, label="worker private Git directory"),
    }


def _filesystem_instance_values(value: Any, *, label: str) -> Dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != set(_FILESYSTEM_INSTANCE_KEYS):
        _fail(f"{label} must contain exactly device and inode")
    result: Dict[str, int] = {}
    for key in _FILESYSTEM_INSTANCE_KEYS:
        item = value[key]
        if type(item) is not int or item < 0:
            _fail(f"{label} has invalid {key}")
        result[key] = item
    return result


def _worker_instance_values(value: Any) -> Dict[str, Dict[str, int]]:
    if not isinstance(value, Mapping) or set(value) != set(_WORKER_INSTANCE_KEYS):
        _fail("worker instance must contain exactly root and git_dir")
    return {
        key: _filesystem_instance_values(value[key], label=f"worker instance {key}")
        for key in _WORKER_INSTANCE_KEYS
    }


def _current_target(identity: Mapping[str, Any], *, allow_head_drift: bool) -> Dict[str, str]:
    """Validate immutable checkout identity, optionally permitting only HEAD movement."""
    saved = _identity_values(identity)
    current = target_identity(saved["repo"])
    for key in ("repo", "git_dir", "common_dir", "branch"):
        if current[key] != saved[key]:
            _fail(f"target {key} drifted")
    if not allow_head_drift and current["head"] != saved["head"]:
        _fail("target HEAD drifted")
    return current


def _exact_commit(repo: Path, value: Any, reference_head: str, *, label: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        _fail(f"{label} must be a full lowercase commit SHA")
    if len(value) != len(reference_head):
        _fail(f"{label} does not match this repository object format")
    result = _git(repo, "cat-file", "-e", value + "^{commit}")
    if result.returncode:
        _fail(f"{label} does not resolve to a commit in the shared repository")
    return value


def validate_target(identity: Mapping[str, Any], expected_head: Optional[str] = None) -> Dict[str, str]:
    """Recheck the exact frozen checkout identity before a chain mutation."""
    saved = _identity_values(identity)
    current = _current_target(saved, allow_head_drift=False)
    expected = saved["head"] if expected_head is None else expected_head
    expected = _exact_commit(Path(current["repo"]), expected, current["head"], label="expected HEAD")
    if current["head"] != expected:
        _fail("target HEAD drifted")
    return current


def _assert_safe_return_lock_stat(details: os.stat_result) -> None:
    if not stat.S_ISREG(details.st_mode):
        _fail("target return lock must be a regular non-symlink file")
    if details.st_nlink != 1:
        _fail("target return lock must not have hard links")


def _open_return_lock(path: Path) -> int:
    """Open one durable lock file without following or blocking on unsafe nodes."""
    try:
        existing = os.lstat(path)
    except FileNotFoundError:
        existing = None
    except OSError as exc:
        _fail(f"cannot inspect target return lock: {exc}")
        raise AssertionError from exc
    if existing is not None:
        _assert_safe_return_lock_stat(existing)

    flags = os.O_RDWR | os.O_CREAT | os.O_NONBLOCK
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(os.fspath(path), flags, 0o600)
    except OSError as exc:
        _fail(f"cannot open target return lock: {exc}")
        raise AssertionError from exc

    try:
        opened = os.fstat(descriptor)
        _assert_safe_return_lock_stat(opened)
        linked = os.lstat(path)
        _assert_safe_return_lock_stat(linked)
        if (opened.st_dev, opened.st_ino) != (linked.st_dev, linked.st_ino):
            _fail("target return lock changed while opening")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


@contextmanager
def _target_return_lock(repo: Path | str) -> Iterator[int]:
    """Take the durable, nonblocking advisory lock for one actual worktree."""
    actual_repo = _repo_root(repo)
    git_dir = _git_directory(actual_repo, "--absolute-git-dir", label="target private Git directory")
    lock_path = git_dir / _RETURN_LOCK_NAME
    descriptor = _open_return_lock(lock_path)
    acquired = False
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                _fail("target is busy with another cooperative chain return")
            _fail(f"cannot lock target return lock: {exc}")
        acquired = True
        yield descriptor
    finally:
        if acquired:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            except OSError:
                pass
        os.close(descriptor)


def _uuid(value: Any, *, label: str) -> str:
    if not isinstance(value, str):
        _fail(f"{label} must be a UUID string")
    try:
        parsed = uuid.UUID(value)
    except (TypeError, ValueError, AttributeError) as exc:
        _fail(f"{label} must be a UUID string")
        raise AssertionError from exc
    canonical = str(parsed)
    if value.lower() != canonical:
        _fail(f"{label} must use canonical UUID spelling")
    return canonical


def _names(identity: Mapping[str, str], run_id: str, attempt: str, base_commit: str) -> tuple[str, str]:
    seed = "\x00".join(
        tuple(identity[key] for key in _IDENTITY_KEYS) + (run_id, attempt, base_commit)
    ).encode("utf-8", "surrogateescape")
    stem = f"{run_id}-{attempt}-{hashlib.sha256(seed).hexdigest()[:16]}"
    return _PATH_PREFIX + stem, _BRANCH_PREFIX + stem


def _path_overlap(left: Path, right: Path) -> bool:
    try:
        left.relative_to(right)
        return True
    except ValueError:
        try:
            right.relative_to(left)
            return True
        except ValueError:
            return False


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _registered_worktrees(repo: Path) -> Sequence[Path]:
    raw = _git_text(repo, "worktree", "list", "--porcelain")
    result = []
    for line in raw.splitlines():
        if not line.startswith("worktree "):
            continue
        value = line[len("worktree "):]
        listed = _absolute_path(value, label="registered Git worktree")
        result.append(_canonical_candidate(listed, label="registered Git worktree"))
    if not result:
        _fail("Git reported no registered worktrees")
    return tuple(result)


def _assert_exclusive_worker_branch(repo: Path, path: Path, branch: str) -> None:
    """Reject a branch concurrently checked out by another registered worktree."""
    for registered in _registered_worktrees(repo):
        if registered == path:
            continue
        result = _git(registered, "symbolic-ref", "--quiet", "--short", "HEAD")
        if result.returncode == 1:
            continue
        if result.returncode:
            _fail("cannot inspect a registered worktree branch")
        other = result.stdout.decode("utf-8", "surrogateescape").strip()
        if other == branch:
            _fail("allocation branch is checked out by another registered worktree")


def _nearest_existing_dir(path: Path, *, label: str) -> Path:
    cursor = path
    while not os.path.lexists(cursor):
        if cursor == cursor.parent:
            _fail(f"cannot find an existing parent for {label}")
        cursor = cursor.parent
    if cursor.is_symlink():
        _fail(f"{label} resolves through a symlink")
    return _existing_dir(cursor, label=label)


def _looks_like_git_dir(path: Path) -> bool:
    return path.is_dir() and (path / "HEAD").is_file() and (path / "objects").is_dir()


def _reject_foreign_enclosure(identity: Mapping[str, str], path: Path) -> None:
    """Reject a location inside another worktree or raw Git metadata directory."""
    existing = _nearest_existing_dir(path, label="workspace location")
    probe = _git(existing, "rev-parse", "--is-inside-work-tree")
    if probe.returncode == 0 and probe.stdout.strip() == b"true":
        root = _repo_root(existing)
        common = _git_directory(root, "--git-common-dir", label="enclosing Git common directory")
        if os.fspath(common) != identity["common_dir"]:
            _fail("workspace location is enclosed by a foreign Git repository")
        return

    cursor = existing
    while True:
        if cursor.name == ".git" or _looks_like_git_dir(cursor):
            _fail("workspace location is inside Git metadata")
        if os.path.lexists(cursor / ".git"):
            _fail("workspace location is enclosed by Git metadata")
        if cursor == cursor.parent:
            break
        cursor = cursor.parent


def _assert_external_location(
    identity: Mapping[str, str],
    parent: Path,
    candidate: Path,
    *,
    owned_candidate: Optional[Path] = None,
) -> None:
    repo = Path(identity["repo"])
    for registered in _registered_worktrees(repo):
        if owned_candidate is not None and registered == owned_candidate:
            continue
        # A shared external .work-trees container normally contains sibling
        # allocations.  It must never itself be *inside* a worktree, while the
        # proposed child may not overlap any registered worktree in either
        # direction.
        if _inside(parent, registered):
            _fail("workspace parent overlaps a registered Git worktree")
        if _path_overlap(candidate, registered):
            _fail("workspace location overlaps a registered Git worktree")
    for metadata in (Path(identity["git_dir"]), Path(identity["common_dir"])):
        if _path_overlap(parent, metadata) or _path_overlap(candidate, metadata):
            _fail("workspace location overlaps Git metadata")
    _reject_foreign_enclosure(identity, parent)
    _reject_foreign_enclosure(identity, candidate)


def _workspace_parent(value: Any) -> Path:
    raw = _absolute_path(value, label="workspace parent")
    if ".work-trees" not in raw.parts:
        _fail("workspace parent must be inside an explicit .work-trees directory")
    _reject_symlink_redirection(raw, label="workspace parent")
    if not os.path.lexists(raw) or raw.is_symlink():
        _fail("workspace parent must be an existing non-symlink directory")
    parent = _canonical_candidate(raw, label="workspace parent")
    if not parent.is_dir():
        _fail("workspace parent must be a directory")
    return parent


def _owned_pair(identity: Mapping[str, str], path: Path, branch: Any, base_commit: str) -> None:
    if not isinstance(branch, str) or not branch.startswith(_BRANCH_PREFIX):
        _fail("allocation branch is not a ShipLoop-owned deterministic branch")
    if not path.name.startswith(_PATH_PREFIX):
        _fail("allocation path is not a ShipLoop-owned deterministic path")
    path_stem = path.name[len(_PATH_PREFIX):]
    branch_stem = branch[len(_BRANCH_PREFIX):]
    if path_stem != branch_stem:
        _fail("allocation path and branch do not name the same attempt")
    match = _STEM.fullmatch(path_stem)
    if match is None:
        _fail("allocation names do not encode canonical UUID attempts")
    run_id = _uuid(match.group("run"), label="allocation run ID")
    attempt = _uuid(match.group("attempt"), label="allocation attempt ID")
    expected_path, expected_branch = _names(identity, run_id, attempt, base_commit)
    if path.name != expected_path or branch != expected_branch:
        _fail("allocation names are not deterministic for the frozen target and base")


def _plan_lifecycle(plan: Mapping[str, Any]) -> str:
    lifecycle = plan.get("lifecycle", _LEGACY_LIFECYCLE)
    if lifecycle not in (_LEGACY_LIFECYCLE, _PER_STEP_LIFECYCLE):
        _fail("allocation plan has an unsupported lifecycle")
    return lifecycle


def allocation_plan(
    identity: Mapping[str, Any],
    workspace_parent: Path | str,
    run_id: str,
    attempt: str,
    base_commit: str,
    *,
    lifecycle: str = _LEGACY_LIFECYCLE,
) -> Dict[str, Any]:
    """Build a deterministic, still-unallocated worktree intent."""
    if lifecycle not in (_LEGACY_LIFECYCLE, _PER_STEP_LIFECYCLE):
        _fail("allocation lifecycle is unsupported")
    target = (
        validate_target(identity)
        if lifecycle == _LEGACY_LIFECYCLE
        else _current_target(identity, allow_head_drift=True)
    )
    parent = _workspace_parent(workspace_parent)
    base = _exact_commit(Path(target["repo"]), base_commit, target["head"], label="base commit")
    if lifecycle == _PER_STEP_LIFECYCLE and base != target["head"]:
        _fail("per-step allocation must start at the current target HEAD")
    run = _uuid(run_id, label="run ID")
    retry = _uuid(attempt, label="attempt")
    leaf, branch = _names(target, run, retry, base)
    candidate = _canonical_candidate(parent / leaf, label="allocation path")
    if candidate.parent != parent:
        _fail("allocation path escapes the explicit workspace parent")
    if os.path.lexists(candidate):
        _fail("allocation path is already occupied")
    _owned_pair(target, candidate, branch, base)
    _assert_external_location(target, parent, candidate)
    result: Dict[str, Any] = {
        "target": dict(target),
        "path": os.fspath(candidate),
        "branch": branch,
        "base_commit": base,
    }
    if lifecycle == _PER_STEP_LIFECYCLE:
        result.update({"lifecycle": lifecycle, "run_id": run, "attempt": retry})
    return result


def _normalized_plan(plan: Mapping[str, Any], *, allow_owned_allocation: bool) -> Dict[str, Any]:
    if not isinstance(plan, Mapping):
        _fail("allocation plan must be an object")
    for key in ("target", "path", "branch", "base_commit"):
        if key not in plan:
            _fail(f"allocation plan is missing {key}")
    lifecycle = _plan_lifecycle(plan)
    target = _identity_values(plan["target"])
    current = _current_target(target, allow_head_drift=lifecycle == _PER_STEP_LIFECYCLE)
    raw_path = _absolute_path(plan["path"], label="allocation path")
    candidate = _canonical_candidate(raw_path, label="allocation path")
    if os.fspath(raw_path) != os.fspath(candidate):
        _fail("allocation plan path is not canonical")
    managed_workspace = plan.get("managed_workspace", False)
    if type(managed_workspace) is not bool:
        _fail("managed workspace marker must be boolean")
    if managed_workspace:
        if lifecycle != _PER_STEP_LIFECYCLE:
            _fail("only per-step plans can use a helper-managed workspace")
        raw_parent = _absolute_path(plan.get("workspace_parent"), label="managed workspace parent")
        parent = _workspace_parent(os.fspath(raw_parent))
        if candidate == parent or not _inside(candidate, parent):
            _fail("managed workspace path must remain below its explicit .work-trees parent")
    else:
        if "workspace_parent" in plan:
            _fail("ordinary allocation plans cannot carry a managed workspace parent")
        parent = _workspace_parent(os.fspath(raw_path.parent))
        if candidate.parent != parent:
            _fail("allocation plan path is not a direct child of its .work-trees parent")
    base = _exact_commit(Path(current["repo"]), plan["base_commit"], current["head"], label="base commit")
    branch = _branch_name(Path(current["repo"]), plan["branch"], label="allocation branch")
    if branch == target["branch"]:
        _fail("allocation branch must differ from the target branch")

    worker: Optional[Dict[str, str]] = None
    worker_instance: Optional[Dict[str, Dict[str, int]]] = None
    if lifecycle == _PER_STEP_LIFECYCLE:
        run = _uuid(plan.get("run_id"), label="per-step plan run ID")
        retry = _uuid(plan.get("attempt"), label="per-step plan attempt")
    elif "worker" in plan:
        _fail("legacy allocation plan cannot bind an adopted worker")

    if "worker_instance" in plan:
        if lifecycle != _PER_STEP_LIFECYCLE:
            _fail("only per-step plans can bind a worker filesystem instance")
        worker_instance = _worker_instance_values(plan["worker_instance"])

    if "worker" in plan:
        if lifecycle != _PER_STEP_LIFECYCLE:
            _fail("only per-step plans can bind an adopted worker")
        worker = _identity_values(plan["worker"])
        if worker["repo"] != os.fspath(candidate):
            _fail("adopted worker root does not match its planned path")
        if worker["common_dir"] != target["common_dir"]:
            _fail("adopted worker does not share the planned Git common directory")
        if worker["git_dir"] == target["git_dir"]:
            _fail("adopted worker reuses the initiating checkout private Git directory")
        if worker["branch"] != branch:
            _fail("adopted worker branch does not match its plan")
        _branch_name(Path(current["repo"]), worker["branch"], label="adopted worker branch")
        if worker["head"] != base:
            _fail("adopted worker did not start at its declared base commit")
    else:
        _owned_pair(target, candidate, branch, base)
        if lifecycle == _PER_STEP_LIFECYCLE:
            expected_path, expected_branch = _names(target, run, retry, base)
            if candidate.name != expected_path or branch != expected_branch:
                _fail("per-step allocation names do not match their recorded attempt")
    _assert_external_location(
        target,
        parent,
        candidate,
        owned_candidate=candidate if allow_owned_allocation else None,
    )
    result: Dict[str, Any] = {
        "target": dict(target),
        "path": os.fspath(candidate),
        "branch": branch,
        "base_commit": base,
    }
    if lifecycle == _PER_STEP_LIFECYCLE:
        result.update({"lifecycle": lifecycle, "run_id": run, "attempt": retry})
    if managed_workspace:
        result.update({"managed_workspace": True, "workspace_parent": os.fspath(parent)})
    if worker is not None:
        result["worker"] = worker
    if worker_instance is not None:
        result["worker_instance"] = worker_instance
    return result


def adopt_workspace(
    target: Mapping[str, Any],
    workspace_parent: Path | str,
    run_id: str,
    attempt: str,
    base_commit: str,
    workspace: Path | str,
) -> Dict[str, Any]:
    """Bind one caller-created, clean Ask-Agent worktree to a per-step plan."""
    current = validate_target(target)
    base = _exact_commit(Path(current["repo"]), base_commit, current["head"], label="base commit")
    if base != current["head"]:
        _fail("adopted worker must start at the current target HEAD")
    run = _uuid(run_id, label="run ID")
    retry = _uuid(attempt, label="attempt")
    parent = _workspace_parent(workspace_parent)
    raw_path = _absolute_path(workspace, label="adopted workspace")
    _reject_symlink_redirection(raw_path, label="adopted workspace")
    if not os.path.lexists(raw_path) or raw_path.is_symlink() or not raw_path.is_dir():
        _fail("adopted workspace must be an existing non-symlink directory")
    path = _canonical_candidate(raw_path, label="adopted workspace")
    if path.parent != parent:
        _fail("adopted workspace must be a direct canonical child of its workspace parent")
    _assert_external_location(current, parent, path, owned_candidate=path)
    worker = target_identity(path)
    if worker["repo"] != os.fspath(path):
        _fail("adopted worker root does not match its workspace")
    if worker["common_dir"] != current["common_dir"]:
        _fail("adopted worker does not share the target Git common directory")
    if worker["git_dir"] == current["git_dir"]:
        _fail("adopted worker reuses the target private Git directory")
    if worker["branch"] == current["branch"]:
        _fail("adopted worker must use a branch distinct from the target")
    if worker["head"] != base:
        _fail("adopted worker HEAD does not match the declared base commit")
    plan = {
        "target": dict(current),
        "path": os.fspath(path),
        "branch": worker["branch"],
        "base_commit": base,
        "lifecycle": _PER_STEP_LIFECYCLE,
        "run_id": run,
        "attempt": retry,
        "worker": dict(worker),
    }
    return bind_worker_instance(plan)


def adopt_managed_workspace(
    target: Mapping[str, Any],
    workspace_parent: Path | str,
    run_id: str,
    attempt: str,
    base_commit: str,
    workspace: Path | str,
) -> Dict[str, Any]:
    """Bind one Ask-Agent-helper-owned worktree below the configured root.

    Ask Agent 0.6 owns an attempt store and places each linked worktree below
    it.  That differs from the direct-child layout owned by ShipLoop's legacy
    allocator, so retain a distinct plan marker rather than weakening the
    ordinary allocator's deterministic-path contract.
    """
    current = validate_target(target)
    base = _exact_commit(Path(current["repo"]), base_commit, current["head"], label="base commit")
    if base != current["head"]:
        _fail("managed worker must start at the current target HEAD")
    run = _uuid(run_id, label="run ID")
    retry = _uuid(attempt, label="attempt")
    parent = _workspace_parent(workspace_parent)
    raw_path = _absolute_path(workspace, label="managed workspace")
    _reject_symlink_redirection(raw_path, label="managed workspace")
    if not os.path.lexists(raw_path) or raw_path.is_symlink() or not raw_path.is_dir():
        _fail("managed workspace must be an existing non-symlink directory")
    path = _canonical_candidate(raw_path, label="managed workspace")
    if path == parent or not _inside(path, parent):
        _fail("managed workspace must remain below the explicit workspace parent")
    _assert_external_location(current, parent, path, owned_candidate=path)
    worker = target_identity(path)
    if worker["repo"] != os.fspath(path):
        _fail("managed worker root does not match its workspace")
    if worker["common_dir"] != current["common_dir"]:
        _fail("managed worker does not share the target Git common directory")
    if worker["git_dir"] == current["git_dir"]:
        _fail("managed worker reuses the target private Git directory")
    if worker["branch"] == current["branch"]:
        _fail("managed worker must use a branch distinct from the target")
    if worker["head"] != base:
        _fail("managed worker HEAD does not match the declared base commit")
    plan = {
        "target": dict(current),
        "path": os.fspath(path),
        "branch": worker["branch"],
        "base_commit": base,
        "lifecycle": _PER_STEP_LIFECYCLE,
        "run_id": run,
        "attempt": retry,
        "worker": dict(worker),
        "managed_workspace": True,
        "workspace_parent": os.fspath(parent),
    }
    return bind_worker_instance(plan)


def _branch_exists(repo: Path, branch: str) -> bool:
    result = _git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}")
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    _fail("cannot inspect allocation branch")
    raise AssertionError


def _is_ancestor_result(repo: Path, base: str, descendant: str, *, label: str) -> bool:
    result = _git(repo, "merge-base", "--is-ancestor", base, descendant)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    _fail(f"cannot inspect {label} ancestry")
    raise AssertionError


def _is_ancestor(repo: Path, base: str, descendant: str, *, label: str) -> None:
    if not _is_ancestor_result(repo, base, descendant, label=label):
        _fail(f"{label} does not descend from its declared base")


def _assert_allocated_worker(plan: Mapping[str, Any], worker: Mapping[str, str], *, exact_base: bool) -> Dict[str, str]:
    target = plan["target"]
    path = Path(plan["path"])
    actual = _identity_values(worker)
    if actual["repo"] != os.fspath(path):
        _fail("allocated worktree root does not match its planned path")
    if actual["common_dir"] != target["common_dir"]:
        _fail("allocated worktree does not share the planned Git common directory")
    if actual["git_dir"] == target["git_dir"]:
        _fail("allocated worktree reuses the initiating checkout private Git directory")
    if actual["branch"] != plan["branch"]:
        _fail("allocated worktree branch does not match its plan")
    bound = plan.get("worker")
    if bound is not None:
        saved_worker = _identity_values(bound)
        for key in ("repo", "git_dir", "common_dir", "branch"):
            if actual[key] != saved_worker[key]:
                _fail(f"adopted worker {key} drifted")
    bound_instance = plan.get("worker_instance")
    if bound_instance is not None:
        saved_instance = _worker_instance_values(bound_instance)
        actual_instance = _worker_instance(Path(actual["repo"]), Path(actual["git_dir"]))
        if actual_instance != saved_instance:
            _fail("allocated worktree filesystem identity drifted")
    registered = _registered_worktrees(Path(target["repo"]))
    if path not in registered:
        _fail("allocated path is not a registered Git worktree")
    _assert_exclusive_worker_branch(Path(target["repo"]), path, actual["branch"])
    branch_head = _git_text(Path(target["repo"]), "rev-parse", "--verify", f"refs/heads/{actual['branch']}")
    if branch_head != actual["head"]:
        _fail("allocated worktree branch does not point at its HEAD")
    if exact_base:
        if actual["head"] != plan["base_commit"]:
            _fail("new allocation did not start at its declared base commit")
    else:
        _is_ancestor(Path(actual["repo"]), plan["base_commit"], actual["head"], label="allocated worktree")
    return actual


def allocate(plan: Mapping[str, Any]) -> Dict[str, str]:
    """Create the planned linked worktree once; recovery is a separate action."""
    normalized = _normalized_plan(plan, allow_owned_allocation=False)
    if "worker" in normalized:
        _fail("an adopted workspace cannot be allocated again")
    # Allocation is a mutation, so a per-step plan may recover after a target
    # advance but may not create a newly stale worker from an old target head.
    validate_target(normalized["target"])
    target = Path(normalized["target"]["repo"])
    path = Path(normalized["path"])
    if os.path.lexists(path):
        _fail("allocation path is already occupied; use recover_allocation for an existing worktree")
    if _branch_exists(target, normalized["branch"]):
        _fail("allocation branch is already occupied; use recover_allocation for an existing worktree")
    result = _git(
        target,
        "worktree",
        "add",
        "-b",
        normalized["branch"],
        os.fspath(path),
        normalized["base_commit"],
        readonly=False,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        _fail(f"Git could not allocate the planned worktree{suffix}")
    worker = target_identity(path)
    verified = _assert_allocated_worker(normalized, worker, exact_base=True)
    validate_target(normalized["target"])
    return verified


def _recover_normalized(normalized: Mapping[str, Any]) -> Dict[str, str]:
    path = Path(normalized["path"])
    if not os.path.lexists(path) or path.is_symlink() or not path.is_dir():
        _fail("planned allocation path is unavailable for recovery")
    worker = target_identity(path)
    return _assert_allocated_worker(normalized, worker, exact_base=False)


def recover_allocation(plan: Mapping[str, Any]) -> Dict[str, str]:
    """Read-only validation of an already-created deterministic allocation."""
    normalized = _normalized_plan(plan, allow_owned_allocation=True)
    return _recover_normalized(normalized)


def inspect_contribution(plan: Mapping[str, Any], commit: str) -> Dict[str, Any]:
    """Prove an exact clean worker HEAD descends from the planned base."""
    normalized = _normalized_plan(plan, allow_owned_allocation=True)
    worker = _recover_normalized(normalized)
    exact = _exact_commit(Path(worker["repo"]), commit, worker["head"], label="contribution commit")
    if worker["head"] != exact:
        _fail("contribution commit is not the clean allocated worktree HEAD")
    return {"plan": normalized, "identity": worker, "commit": exact}


def _per_step_plan(plan: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = _normalized_plan(plan, allow_owned_allocation=True)
    if normalized.get("lifecycle") != _PER_STEP_LIFECYCLE:
        _fail("per-step integration requires a per-step allocation plan")
    return normalized


def bind_worker_instance(plan: Mapping[str, Any]) -> Dict[str, Any]:
    """Bind a newly allocated per-step worker to its root and private Git dirs.

    Call this immediately after allocation and persist the returned plan before
    the worker performs work.  Repeating it validates an existing binding.
    """
    normalized = _per_step_plan(plan)
    if "worker_instance" in normalized:
        _recover_normalized(normalized)
        return normalized
    path = Path(normalized["path"])
    if not os.path.lexists(path) or path.is_symlink() or not path.is_dir():
        _fail("planned allocation path is unavailable for worker-instance binding")
    worker = target_identity(path)
    _assert_allocated_worker(normalized, worker, exact_base=True)
    bound = dict(normalized)
    bound["worker_instance"] = _worker_instance(
        Path(worker["repo"]),
        Path(worker["git_dir"]),
    )
    result = _per_step_plan(bound)
    _assert_allocated_worker(result, worker, exact_base=True)
    return result


def _expected_target(plan: Mapping[str, Any], expected_target: str) -> tuple[Dict[str, str], str]:
    target = _current_target(plan["target"], allow_head_drift=True)
    exact = _exact_commit(
        Path(target["repo"]),
        expected_target,
        target["head"],
        label="expected target commit",
    )
    if target["head"] != exact:
        _fail("target HEAD does not match the expected target commit")
    return target, exact


def _source_workspace(plan: Mapping[str, Any], source_commit: str) -> tuple[Dict[str, str], str]:
    worker = _recover_normalized(plan)
    exact = _exact_commit(
        Path(worker["repo"]),
        source_commit,
        worker["head"],
        label="source contribution commit",
    )
    _is_ancestor(Path(worker["repo"]), plan["base_commit"], exact, label="source contribution commit")
    return worker, exact


def _prepared_message(source_commit: str, target_commit: str) -> str:
    return f"{_PREPARED_MERGE_PREFIX} source={source_commit} target={target_commit}"


def _commit_parents(repo: Path, commit: str) -> tuple[str, ...]:
    raw = _git_text(repo, "rev-list", "--parents", "-n", "1", commit)
    values = raw.split()
    if not values or values[0] != commit:
        _fail("Git returned an invalid prepared candidate parent list")
    return tuple(values[1:])


def _is_prepared_lineage(
    repo: Path,
    candidate: str,
    source_commit: str,
    *,
    expected_target: Optional[str] = None,
) -> bool:
    """Recognize helper merges plus one target-contained conflict-resolution merge."""
    cursor = candidate
    repair_seen = False
    for _ in range(256):
        if cursor == source_commit:
            return True
        parents = _commit_parents(repo, cursor)
        if len(parents) != 2:
            return False
        message = _git_text(repo, "log", "-1", "--format=%B", cursor)
        if message == _prepared_message(source_commit, parents[1]):
            cursor = parents[0]
            continue
        # Git's normal conflict-resolution commit has no helper message.  It
        # is permitted once when its merged target is contained in the current
        # expected target and its first-parent chain still reaches the recorded
        # source.  That permits an explicit repair to be re-prepared after a
        # later fast-forward, while rejecting arbitrary worker-side commits.
        if (
            not repair_seen
            and expected_target is not None
            and _is_ancestor_result(
                repo,
                parents[1],
                expected_target,
                label="conflict-resolution target",
            )
        ):
            repair_seen = True
            cursor = parents[0]
            continue
        return False
    _fail("prepared candidate lineage is too deep")
    raise AssertionError


def _prepared_proof(
    plan: Mapping[str, Any],
    source_commit: str,
    expected_target: str,
    candidate_commit: str,
) -> Dict[str, str]:
    target, expected = _expected_target(plan, expected_target)
    worker, source = _source_workspace(plan, source_commit)
    repo = Path(worker["repo"])
    candidate = _exact_commit(repo, candidate_commit, worker["head"], label="prepared candidate commit")
    _is_ancestor(repo, source, candidate, label="prepared candidate commit")
    _is_ancestor(repo, expected, candidate, label="prepared candidate commit")

    worker_head = worker["head"]
    if worker_head != candidate:
        _fail("prepared candidate is not the clean allocated worktree HEAD")
    if candidate != source and candidate != expected and not _is_prepared_lineage(
        repo,
        candidate,
        source,
        expected_target=expected,
    ):
        _fail("prepared candidate is not a recognized worker merge")
    return {
        "source_commit": source,
        "expected_target": expected,
        "candidate_commit": candidate,
        "workspace": worker["repo"],
    }


def prepare_integration(
    plan: Mapping[str, Any],
    source_commit: str,
    expected_target: str,
) -> Dict[str, str]:
    """Prepare a clean worker candidate that preserves source and target ancestry.

    This never mutates the target checkout.  A repeated call recognizes a prior
    helper-authored merge and either returns it or extends it for a newer target.
    Conflicts remain in the worker checkout for explicit recovery.
    """
    normalized = _per_step_plan(plan)
    _, expected = _expected_target(normalized, expected_target)
    worker, source = _source_workspace(normalized, source_commit)
    repo = Path(worker["repo"])
    worker_head = worker["head"]
    if worker_head != source and not _is_prepared_lineage(
        repo,
        worker_head,
        source,
        expected_target=expected,
    ):
        _fail("worker HEAD drifted after its source contribution")

    if _is_ancestor_result(repo, expected, worker_head, label="expected target commit"):
        candidate = worker_head
    elif _is_ancestor_result(repo, worker_head, expected, label="worker preparation"):
        _expected_target(normalized, expected)
        result = _git(
            repo,
            "merge",
            "--ff-only",
            "--no-overwrite-ignore",
            expected,
            readonly=False,
        )
        if result.returncode:
            detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
            suffix = f": {detail[-1]}" if detail else ""
            _fail(f"Git could not fast-forward the prepared worker{suffix}")
        candidate = _head(repo)
    else:
        # Recheck just before the only worker mutation.  A later target movement
        # leaves the prepared candidate intact but prevents a stale proof.
        _expected_target(normalized, expected)
        result = _git(
            repo,
            "merge",
            "--no-ff",
            "--no-edit",
            "--no-overwrite-ignore",
            "-m",
            _prepared_message(source, expected),
            expected,
            readonly=False,
        )
        if result.returncode:
            detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
            suffix = f": {detail[-1]}" if detail else ""
            _fail(f"Git could not prepare the worker integration{suffix}")
        candidate = _head(repo)
    return _prepared_proof(normalized, source, expected, candidate)


def inspect_prepared(
    plan: Mapping[str, Any],
    source_commit: str,
    expected_target: str,
    candidate_commit: str,
) -> Dict[str, str]:
    """Read-only proof that a prepared candidate still matches its exact target."""
    return _prepared_proof(
        _per_step_plan(plan),
        source_commit,
        expected_target,
        candidate_commit,
    )


def _assert_no_ignored_paths(repo: Path) -> None:
    result = _git(repo, "ls-files", "--others", "--ignored", "--exclude-standard", "-z")
    if result.returncode:
        _fail("cannot inspect ignored worker paths")
    if result.stdout:
        _fail("worker has ignored paths that must be preserved before removal")


def _integrated_target(plan: Mapping[str, Any], integrated_commit: str) -> tuple[Dict[str, str], str]:
    target = _current_target(plan["target"], allow_head_drift=True)
    exact = _exact_commit(
        Path(target["repo"]),
        integrated_commit,
        target["head"],
        label="integrated commit",
    )
    _is_ancestor(Path(target["repo"]), exact, target["head"], label="target HEAD")
    return target, exact


def _require_worker_instance_for_cleanup(plan: Mapping[str, Any]) -> None:
    if "worker_instance" not in plan:
        _fail(
            "per-step cleanup requires a recorded worker filesystem identity; "
            "old unbound plans remain readable but cannot remove a worktree"
        )


def inspect_removed(plan: Mapping[str, Any], integrated_commit: str) -> Dict[str, Any]:
    """Prove an already-recorded cleanup left no reusable worker allocation."""
    normalized = _per_step_plan(plan)
    target, integrated = _integrated_target(normalized, integrated_commit)
    path = Path(normalized["path"])
    if os.path.lexists(path):
        _fail("worker path still exists; cleanup is not complete")
    if path in _registered_worktrees(Path(target["repo"])):
        _fail("worker path remains registered after cleanup")
    branch = normalized["branch"]
    if not _branch_exists(Path(target["repo"]), branch):
        _fail("worker branch was removed; cleanup must retain recovery refs")
    worker_commit = _git_text(Path(target["repo"]), "rev-parse", "--verify", f"refs/heads/{branch}")
    worker_commit = _exact_commit(
        Path(target["repo"]),
        worker_commit,
        target["head"],
        label="retained worker contribution commit",
    )
    _is_ancestor(
        Path(target["repo"]),
        worker_commit,
        integrated,
        label="integrated commit",
    )
    return {
        "integrated_commit": integrated,
        "workspace": os.fspath(path),
        "branch": branch,
        "removed": True,
    }


def remove_worker(plan: Mapping[str, Any], integrated_commit: str) -> Dict[str, Any]:
    """Remove one clean, integrated worker without force; keep its branch ref."""
    normalized = _per_step_plan(plan)
    _require_worker_instance_for_cleanup(normalized)
    target, integrated = _integrated_target(normalized, integrated_commit)
    path = Path(normalized["path"])
    if not os.path.lexists(path):
        _fail("worker path is already absent; use inspect_removed after a cleanup intent")
    worker = _recover_normalized(normalized)
    _is_ancestor(
        Path(target["repo"]),
        worker["head"],
        integrated,
        label="integrated commit",
    )
    _assert_no_ignored_paths(Path(worker["repo"]))
    result = _git(
        Path(target["repo"]),
        "worktree",
        "remove",
        os.fspath(path),
        readonly=False,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        _fail(f"Git could not remove the worker worktree{suffix}")
    return inspect_removed(normalized, integrated)


def inspect_superseded_removed(
    plan: Mapping[str, Any],
    replacement_integrated_commit: str,
) -> Dict[str, Any]:
    """Prove a retired worker is absent while retaining its unintegrated ref."""
    normalized = _per_step_plan(plan)
    target, replacement = _integrated_target(normalized, replacement_integrated_commit)
    path = Path(normalized["path"])
    if os.path.lexists(path):
        _fail("superseded worker path still exists; cleanup is not complete")
    if path in _registered_worktrees(Path(target["repo"])):
        _fail("superseded worker path remains registered after cleanup")
    branch = normalized["branch"]
    if not _branch_exists(Path(target["repo"]), branch):
        _fail("superseded worker branch was removed; cleanup must retain recovery refs")
    worker_commit = _git_text(
        Path(target["repo"]),
        "rev-parse",
        "--verify",
        f"refs/heads/{branch}",
    )
    worker_commit = _exact_commit(
        Path(target["repo"]),
        worker_commit,
        target["head"],
        label="retained superseded worker commit",
    )
    return {
        "replacement_integrated_commit": replacement,
        "workspace": os.fspath(path),
        "branch": branch,
        "worker_commit": worker_commit,
        "removed": True,
    }


def remove_superseded_worker(
    plan: Mapping[str, Any],
    replacement_integrated_commit: str,
) -> Dict[str, Any]:
    """Remove one clean retired worker without asserting its commit integrated."""
    normalized = _per_step_plan(plan)
    _require_worker_instance_for_cleanup(normalized)
    target, replacement = _integrated_target(normalized, replacement_integrated_commit)
    path = Path(normalized["path"])
    if not os.path.lexists(path):
        _fail(
            "superseded worker path is already absent; "
            "use inspect_superseded_removed after a cleanup intent"
        )
    worker = _recover_normalized(normalized)
    _assert_no_ignored_paths(Path(worker["repo"]))
    result = _git(
        Path(target["repo"]),
        "worktree",
        "remove",
        os.fspath(path),
        readonly=False,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        _fail(f"Git could not remove the superseded worker worktree{suffix}")
    proof = inspect_superseded_removed(normalized, replacement)
    if proof["worker_commit"] != worker["head"]:
        _fail("superseded worker branch changed during cleanup")
    return proof


def fast_forward(identity: Mapping[str, Any], commit: str) -> Dict[str, str]:
    """Fast-forward one frozen branch under its cooperative target-return lock.

    The lock is advisory only: it prevents a second cooperative chain return
    from validating the same frozen target concurrently.  Manual Git writers
    that ignore it remain outside this helper's protection.
    """
    saved = _identity_values(identity)
    # Git resolves the actual private directory for the lock.  The full frozen
    # identity validation remains inside it, so a caller-supplied git_dir can
    # never choose where we write.
    with _target_return_lock(saved["repo"]) as lock_descriptor:
        target = validate_target(saved)
        repo = Path(target["repo"])
        exact = _exact_commit(repo, commit, target["head"], label="contribution commit")
        _is_ancestor(repo, target["head"], exact, label="contribution commit")
        validate_target(target, expected_head=target["head"])
        # The merge inherits the same open file description.  If this Python
        # process exits after launching Git, the advisory lock stays held until
        # the Git child completes its target mutation.
        result = _git(
            repo,
            "merge",
            "--ff-only",
            "--no-overwrite-ignore",
            exact,
            readonly=False,
            pass_fds=(lock_descriptor,),
        )
        if result.returncode:
            detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
            suffix = f": {detail[-1]}" if detail else ""
            _fail(f"Git could not fast-forward the initiating branch{suffix}")
        destination = target_identity(repo)
        for key in ("repo", "git_dir", "common_dir", "branch"):
            if destination[key] != target[key]:
                _fail(f"destination {key} changed during fast-forward")
        if destination["head"] != exact:
            _fail("destination HEAD is not the requested contribution commit")
        return destination
