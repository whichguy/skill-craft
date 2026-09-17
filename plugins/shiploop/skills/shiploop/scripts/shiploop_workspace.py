#!/usr/bin/env python3
"""Fail-closed external workspaces for a ShipLoop navigator run.

This module deliberately owns only the Git boundary around a whole navigator
run.  The navigator owns the delivery graph; this helper creates an isolated
worktree from the source checkout's *actual* starting content and returns only
an explicitly reviewed delta.  Its Markdown records are durable recovery
material, never a replacement for the navigator state.

The public functions are intentionally small:

``prepare``
    Capture a source checkout and create ``<workspace-root>/worktree``.
``plan_return``
    Write a reviewed-path return plan without changing the source checkout.
``execute_return``
    Apply the approved delta or perform a safe fast-forward merge.
``assert_binding`` / ``completed_receipt``
    Read-only guards for protocol start and terminal handoff.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess
import tempfile
import threading
from contextlib import contextmanager
from functools import wraps
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:  # Scripts are normally imported with their directory on sys.path.
    import shiploop_store as store
except ImportError:  # pragma: no cover - supports package-style local imports.
    from . import shiploop_store as store  # type: ignore


class WorkspaceError(RuntimeError):
    """The workspace cannot safely be prepared, returned, or recovered."""


SCHEMA = "shiploop-workspace"
PLAN_SCHEMA = "shiploop-workspace-return-plan"
RECEIPT_SCHEMA = "shiploop-workspace-return-receipt"
VERSION = 1
MANIFEST = "workspace.md"
RETURN_PLAN = "return-plan.md"
RETURN_RECEIPT = "return-receipt.md"

# These are harness/runtime locations, not product output.  The list is kept
# intentionally short and name-based so a real product directory is not
# silently treated as transient merely because it has a fashionable name.
# Only ShipLoop/Git control locations are universally transient.  Framework
# names such as ``coverage`` or ``.next`` can be intentional product content;
# callers can list those under ``exclude`` and must review every other path.
FORBIDDEN_PARTS = frozenset({".git", ".shiploop", ".until-loop", ".worktrees", ".shiploop-workspaces", ".shiploop-runs"})

_SHA = re.compile(r"[0-9a-f]{40,64}")
_LOCK_LOCAL = threading.local()

__all__ = [
    "WorkspaceError",
    "assert_binding",
    "completed_receipt",
    "execute_return",
    "plan_return",
    "prepare",
]


def _fail(message: str) -> None:
    raise WorkspaceError(message)


def _git(
    repo: Path,
    *args: str,
    input_bytes: Optional[bytes] = None,
    env: Optional[Mapping[str, str]] = None,
    readonly: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    """Run one non-interactive Git command without exposing file contents."""
    merged = dict(os.environ)
    for key in list(merged):
        if key in {
            "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
            "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS",
        } or key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
            merged.pop(key, None)
    merged["GIT_TERMINAL_PROMPT"] = "0"
    if readonly:
        # Avoid opportunistic index refreshes while fingerprinting the source.
        merged["GIT_OPTIONAL_LOCKS"] = "0"
    if env:
        merged.update(env)
    try:
        return subprocess.run(
            ["git", "-c", "core.hooksPath=/dev/null", "-C", os.fspath(repo), *args],
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=merged,
            timeout=45,
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
        _fail(f"git {' '.join(args[:2])} failed" + (f": {detail[-1]}" if detail else ""))
    return result.stdout.decode("utf-8", "surrogateescape").strip()


def _git_bytes(repo: Path, *args: str, readonly: bool = True) -> bytes:
    """Return Git bytes only when the producer command itself succeeded."""
    result = _git(repo, *args, readonly=readonly)
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        _fail(f"git {' '.join(args[:2])} failed" + (f": {detail[-1]}" if detail else ""))
    return result.stdout


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _safe_rel(value: str, *, label: str = "path") -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        _fail(f"{label} must be a nonempty relative path")
    if "\\" in value or "\n" in value or "\r" in value:
        _fail(f"unsafe {label}: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        _fail(f"unsafe {label}: {value!r}")
    return path.as_posix()


def _forbidden(path: str) -> bool:
    return any(part in FORBIDDEN_PARTS for part in PurePosixPath(path).parts)


def _normal_paths(values: Iterable[str], *, label: str) -> List[str]:
    try:
        result = sorted({_safe_rel(value, label=label) for value in values})
    except TypeError as exc:
        _fail(f"{label} must be an iterable of paths")
        raise AssertionError from exc
    for path in result:
        if _forbidden(path):
            _fail(f"{label} includes a protected runtime path: {path}")
    return result


def _matches_exclusion(path: str, excluded: Sequence[str]) -> bool:
    return any(path == item or path.startswith(item + "/") for item in excluded)


def _no_symlink_components(path: Path, *, label: str) -> None:
    """Reject a caller-controlled path symlink before canonicalizing it.

    macOS commonly exposes ``/var`` through the system ``/private/var`` link,
    so rejecting every lexical ancestor would reject normal ``tempfile``
    workspaces.  Git supplies canonical repository/common paths below; direct
    root and manifest children are the user-controlled boundary here.
    """
    try:
        if path.is_symlink():
            _fail(f"{label} is a symlink: {path}")
    except OSError as exc:
        _fail(f"cannot inspect {label}: {exc}")


def _resolved_directory(path: Path, *, label: str) -> Path:
    _no_symlink_components(path, label=label)
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        _fail(f"cannot resolve {label}: {exc}")
        raise AssertionError from exc
    if not resolved.is_dir() or resolved.is_symlink():
        _fail(f"{label} is not a real directory: {path}")
    return resolved


def _repo_root(repo: Path) -> Path:
    candidate = _resolved_directory(Path(repo), label="repository")
    top = _git_text(candidate, "rev-parse", "--path-format=absolute", "--show-toplevel")
    root = Path(top)
    if not root.is_absolute():
        _fail("Git returned a non-absolute repository root")
    return _resolved_directory(root, label="repository root")


def _common_dir(repo: Path) -> Path:
    value = _git_text(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    path = Path(value)
    if not path.is_absolute():
        _fail("Git returned a non-absolute common directory")
    return _resolved_directory(path, label="Git common directory")


def _branch(repo: Path) -> str:
    result = _git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", readonly=True)
    if result.returncode:
        _fail("source checkout is detached; a named branch is required for a safe return")
    branch = result.stdout.decode("utf-8", "surrogateescape").strip()
    if not branch or branch.startswith("-") or "\n" in branch:
        _fail("unsafe source branch")
    return branch


def _head(repo: Path) -> str:
    value = _git_text(repo, "rev-parse", "--verify", "HEAD")
    if not _SHA.fullmatch(value):
        _fail("repository HEAD is not a commit SHA")
    return value


def _git_path(repo: Path, name: str) -> Path:
    value = _git_text(repo, "rev-parse", "--path-format=absolute", "--git-path", name)
    path = Path(value)
    if not path.is_absolute():
        _fail(f"Git returned a non-absolute path for {name}")
    return path


def _index_digest(repo: Path) -> str:
    path = _git_path(repo, "index")
    try:
        return _sha256(path.read_bytes())
    except OSError as exc:
        _fail(f"cannot read Git index: {exc}")
        raise AssertionError from exc


def _ensure_supported(repo: Path, *, reject_runtime: bool = True) -> None:
    if _git_text(repo, "rev-parse", "--is-inside-work-tree") != "true":
        _fail("repository is not a Git worktree")
    unresolved = _git_bytes(repo, "ls-files", "-u", "-z")
    if unresolved:
        _fail("repository has unresolved index conflicts")
    entries = _git_bytes(repo, "ls-files", "--stage", "-z").split(b"\0")
    for entry in entries:
        if not entry:
            continue
        header, _, raw_path = entry.partition(b"\t")
        fields = header.split()
        if not fields:
            _fail("cannot parse Git index entry")
        path = _safe_rel(raw_path.decode("utf-8", "surrogateescape"), label="tracked path")
        if fields[0] == b"160000":
            _fail("submodules are unsupported in a managed workspace")
        if reject_runtime and _forbidden(path):
            _fail(f"tracked runtime path cannot enter a managed workspace: {path}")
    if reject_runtime:
        head_tree = _git_bytes(repo, "ls-tree", "-r", "-z", "--name-only", "HEAD")
        for raw_path in head_tree.split(b"\0"):
            if raw_path and _forbidden(_safe_rel(raw_path.decode("utf-8", "surrogateescape"), label="HEAD path")):
                _fail("tracked runtime path cannot enter a managed workspace, even when staged for deletion")
    sparse = _git(repo, "config", "--bool", "core.sparseCheckout", readonly=True)
    if sparse.returncode == 0 and sparse.stdout.strip().lower() == b"true":
        _fail("sparse checkouts are unsupported in a managed workspace")
    split = _git(repo, "config", "--bool", "core.splitIndex", readonly=True)
    if split.returncode == 0 and split.stdout.strip().lower() == b"true":
        _fail("split indexes are unsupported in a managed workspace")
    flags = _git_bytes(repo, "ls-files", "-v", "-t", "-z").split(b"\0")
    for entry in flags:
        if not entry:
            continue
        tag = entry.partition(b" ")[0]
        if b"S" in tag or any(97 <= byte <= 122 for byte in tag):
            _fail("assume-unchanged or skip-worktree entries are unsupported in a managed workspace")
    filters = _git(repo, "config", "--get-regexp", r"^filter\..*\.(clean|smudge|process)$", readonly=True)
    if filters.returncode == 0 and filters.stdout:
        _fail("custom Git filters are unsupported because snapshot normalization cannot be proven")
    if filters.returncode not in {0, 1}:
        _fail("cannot inspect Git filter configuration")


def _index_paths(repo: Path) -> List[str]:
    raw = _git_bytes(repo, "ls-files", "-z")
    return sorted(
        _safe_rel(item.decode("utf-8", "surrogateescape"), label="index path")
        for item in raw.split(b"\0")
        if item
    )


def _untracked(repo: Path) -> List[Dict[str, str]]:
    raw = _git_bytes(
        repo,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignored=no",
    )
    result: List[Dict[str, str]] = []
    for record in raw.split(b"\0"):
        if not record or not record.startswith(b"?? "):
            continue
        path = _safe_rel(record[3:].decode("utf-8", "surrogateescape"), label="untracked path")
        candidate = repo / path
        try:
            os.lstat(candidate)
        except OSError as exc:
            _fail(f"cannot inspect untracked path {path}: {exc}")
            raise AssertionError from exc
        if os.path.islink(candidate):
            kind = "symlink"
            digest = _sha256(os.readlink(candidate).encode("utf-8", "surrogateescape"))
        elif os.path.isfile(candidate):
            kind = "file"
            try:
                digest = _sha256(candidate.read_bytes())
            except OSError as exc:
                _fail(f"cannot read untracked path {path}: {exc}")
                raise AssertionError from exc
        else:
            _fail(f"unsupported untracked path type: {path}")
        result.append({"path": path, "sha256": digest, "kind": kind})
    return sorted(result, key=lambda row: row["path"])


def _temporary_index(root: Path) -> Tuple[int, Path]:
    try:
        descriptor, name = tempfile.mkstemp(prefix=".workspace-index-", dir=root)
    except OSError as exc:
        _fail(f"cannot create workspace temporary index: {exc}")
        raise AssertionError from exc
    return descriptor, Path(name)


def _snapshot_tree(repo: Path, root: Path, extras: Sequence[str] = ()) -> str:
    """Write a tree for actual working content without changing its real index."""
    descriptor, index = _temporary_index(root)
    os.close(descriptor)
    source_index = _git_path(repo, "index")
    try:
        shutil.copyfile(source_index, index)
    except OSError as exc:
        _fail(f"cannot copy Git index for a private snapshot: {exc}")
    env = {"GIT_INDEX_FILE": os.fspath(index), "GIT_OPTIONAL_LOCKS": "0"}
    try:
        # The copied index retains staged-new/staged-delete information that a
        # HEAD seed loses.  ``add -u`` then replaces it with the exact current
        # working content, all inside the alternate index.
        result = _git(repo, "add", "-u", "--", ".", env=env, readonly=True)
        if result.returncode:
            _fail("cannot capture working tree with git add -u")
        for path in extras:
            candidate = repo / path
            if not (candidate.exists() or candidate.is_symlink()):
                continue
            result = _git(repo, "add", "-f", "--", path, env=env, readonly=True)
            if result.returncode:
                _fail(f"cannot capture selected path: {path}")
        result = _git(repo, "write-tree", env=env, readonly=True)
        if result.returncode:
            _fail("cannot write private working-tree snapshot")
        tree = result.stdout.decode("utf-8", "surrogateescape").strip()
        if not _SHA.fullmatch(tree):
            _fail("Git returned an invalid snapshot tree")
        return tree
    finally:
        try:
            index.unlink()
        except OSError:
            pass


def _tree_paths(repo: Path, tree: str) -> List[str]:
    raw = _git_bytes(repo, "ls-tree", "-r", "-z", "--name-only", tree)
    return sorted(
        _safe_rel(item.decode("utf-8", "surrogateescape"), label="tree path")
        for item in raw.split(b"\0")
        if item
    )


def _fingerprint(repo: Path, root: Path, extras: Sequence[str] = ()) -> Dict[str, Any]:
    tracked_tree = _snapshot_tree(repo, root)
    working_tree = _snapshot_tree(repo, root, extras)
    return {
        "head": _head(repo),
        "branch": _branch(repo),
        "index_sha256": _index_digest(repo),
        "index_paths": _index_paths(repo),
        "tracked_tree": tracked_tree,
        "working_tree": working_tree,
        "extra_paths": list(extras),
        "untracked": _untracked(repo),
    }


def _fingerprint_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return dict(left) == dict(right)


def _workspace_root(repo: Path, requested: Path, common: Path) -> Tuple[Path, bool]:
    root = requested.absolute()
    _no_symlink_components(root.parent, label="workspace root parent")
    if _inside(root, repo) or _inside(repo, root) or _inside(root, common):
        _fail("workspace root must be external to both repository and Git metadata")
    if root.exists() or root.is_symlink():
        if root.is_symlink() or not root.is_dir():
            _fail("workspace root is not a real directory")
        manifest = root / MANIFEST
        if manifest.exists() and not manifest.is_symlink():
            return _resolved_directory(root, label="workspace root"), True
        _fail("workspace root is occupied; use a new dedicated root")
    if not root.parent.is_dir():
        _fail("workspace root parent does not exist")
    try:
        root.mkdir(mode=0o700)
    except OSError as exc:
        _fail(f"cannot create workspace root: {exc}")
    return _resolved_directory(root, label="workspace root"), False


def _record(root: Path, name: str, title: str) -> Dict[str, Any]:
    path = root / name
    if not path.is_file() or path.is_symlink():
        _fail(f"missing safe {title}: {path}")
    try:
        value = store.read_record(path)
    except store.StorageError as exc:
        _fail(f"cannot read {title}: {exc}")
        raise AssertionError from exc
    if not isinstance(value, dict):
        _fail(f"{title} must be a Markdown record object")
    return value


def _write(root: Path, records: Mapping[str, Tuple[Mapping[str, Any], str]]) -> None:
    try:
        store.transaction(
            root,
            {name: store.dumps(value, title=title) for name, (value, title) in records.items()},
        )
    except store.StorageError as exc:
        _fail(f"cannot persist workspace record: {exc}")


@contextmanager
def _workspace_lock(root: Path):
    """Serialize direct helper use and finish a crashed Markdown transaction."""
    key = os.fspath(root)
    held = getattr(_LOCK_LOCAL, "roots", set())
    if key in held:
        yield
        return
    lock = root / ".workspace.lock"
    try:
        if not hasattr(os, "O_NOFOLLOW"):
            _fail("secure workspace lock support is unavailable")
        descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    except OSError as exc:
        _fail(f"cannot open workspace lock: {exc}")
        raise AssertionError from exc
    try:
        try:
            import fcntl

            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                _fail("workspace lock is not a private regular file")
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (ImportError, OSError) as exc:
            _fail(f"workspace is busy or cannot be locked: {exc}")
        try:
            store.recover(root)
        except store.StorageError as exc:
            _fail(f"cannot recover workspace transaction: {exc}")
        held.add(key)
        _LOCK_LOCAL.roots = held
        try:
            yield
        finally:
            held.discard(key)
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass


def _locked_existing_root(function):
    """Wrap a public operation whose external workspace root already exists."""
    @wraps(function)
    def wrapped(workspace_root: Path, *args: Any, **kwargs: Any):
        root = _resolved_directory(Path(workspace_root), label="workspace root")
        with _workspace_lock(root):
            return function(root, *args, **kwargs)

    return wrapped


def _validate_manifest(root: Path, manifest: Mapping[str, Any]) -> Dict[str, Any]:
    required = {
        "schema", "version", "status", "source_repo", "source_branch", "source_head",
        "worktree", "run_dir", "branch", "baseline_commit", "baseline_tree",
        "initial_fingerprint", "selected_untracked", "excluded", "start_clean",
    }
    if not required.issubset(manifest) or manifest.get("schema") != SCHEMA or manifest.get("version") != VERSION:
        _fail("workspace manifest has an unsupported schema")
    if manifest.get("status") not in {"prepared", "return-planned", "returned", "blocked"}:
        _fail("workspace manifest has an invalid status")
    for key in ("source_repo", "worktree", "run_dir"):
        if not isinstance(manifest.get(key), str) or not Path(manifest[key]).is_absolute():
            _fail(f"workspace manifest has invalid {key}")
    for key in ("source_head", "baseline_commit", "baseline_tree"):
        if not isinstance(manifest.get(key), str) or not _SHA.fullmatch(manifest[key]):
            _fail(f"workspace manifest has invalid {key}")
    if not isinstance(manifest.get("source_branch"), str) or not manifest["source_branch"]:
        _fail("workspace manifest has invalid source branch")
    expected_branch = "codex/shiploop-" + _sha256(os.fspath(root).encode())[:16]
    if manifest.get("branch") != expected_branch:
        _fail("workspace manifest has invalid workspace branch")
    if type(manifest.get("start_clean")) is not bool:
        _fail("workspace manifest has invalid clean-start marker")
    for key in ("selected_untracked", "excluded"):
        values = manifest.get(key)
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            _fail(f"workspace manifest has invalid {key}")
        if values != _normal_paths(values, label=key):
            _fail(f"workspace manifest has noncanonical {key}")
    initial = manifest.get("initial_fingerprint")
    if not isinstance(initial, dict):
        _fail("workspace manifest has no initial fingerprint")
    if initial.get("head") != manifest["source_head"] or initial.get("branch") != manifest["source_branch"]:
        _fail("workspace manifest initial fingerprint identity mismatch")
    if manifest["start_clean"] and (
        manifest["baseline_commit"] != manifest["source_head"]
        or manifest["baseline_tree"] != initial.get("tracked_tree")
        or manifest["baseline_tree"] != initial.get("working_tree")
    ):
        _fail("clean-start workspace must use its exact source baseline")
    if Path(manifest["run_dir"]) != root / "run" or Path(manifest["worktree"]) != root / "worktree":
        _fail("workspace manifest escapes its dedicated root")
    return dict(manifest)


def _manifest(root: Path) -> Dict[str, Any]:
    return _validate_manifest(root, _record(root, MANIFEST, "workspace manifest"))


@_locked_existing_root
def assert_binding(root: Path, repo: Path) -> Dict[str, Any]:
    """Read-only check that an execution worktree came from this root."""
    root = _resolved_directory(Path(root), label="workspace root")
    manifest = _manifest(root)
    source = _repo_root(Path(manifest["source_repo"]))
    worktree = _resolved_directory(Path(manifest["worktree"]), label="workspace worktree")
    run_dir = _resolved_directory(Path(manifest["run_dir"]), label="workspace run directory")
    supplied = _repo_root(Path(repo))
    if supplied != worktree:
        _fail("workspace binding requires the prepared execution worktree")
    if source == worktree or run_dir != root / "run":
        _fail("workspace binding has invalid source/worktree separation")
    if _common_dir(source) != _common_dir(worktree):
        _fail("workspace source and execution checkout do not share Git metadata")
    if _git_text(worktree, "rev-parse", f"{manifest['baseline_commit']}^{{tree}}") != manifest["baseline_tree"]:
        _fail("workspace baseline commit does not match its captured tree")
    if _git(source, "cat-file", "-e", f"{manifest['baseline_commit']}^{{commit}}", readonly=True).returncode:
        _fail("workspace source no longer contains the baseline commit")
    if _branch(worktree) != manifest["branch"]:
        _fail("workspace branch no longer matches its manifest")
    if _git(worktree, "cat-file", "-e", f"{manifest['baseline_commit']}^{{commit}}", readonly=True).returncode:
        _fail("workspace baseline commit is unavailable")
    return manifest


def _private_commit(repo: Path, tree: str, parent: str) -> str:
    env = {
        "GIT_AUTHOR_NAME": "ShipLoop Workspace",
        "GIT_AUTHOR_EMAIL": "shiploop-workspace@local.invalid",
        "GIT_COMMITTER_NAME": "ShipLoop Workspace",
        "GIT_COMMITTER_EMAIL": "shiploop-workspace@local.invalid",
    }
    result = _git(repo, "commit-tree", tree, "-p", parent, "-m", "ShipLoop private workspace baseline", env=env)
    if result.returncode:
        _fail("cannot create private workspace baseline")
    value = result.stdout.decode("utf-8", "surrogateescape").strip()
    if not _SHA.fullmatch(value):
        _fail("Git returned an invalid private baseline commit")
    return value


def prepare(
    repo: Path,
    workspace_root: Path,
    include_untracked: Sequence[str] = (),
    exclude: Sequence[str] = (),
) -> Dict[str, Any]:
    """Create or safely re-read one external workspace without touching source bytes."""
    source = _repo_root(Path(repo))
    _ensure_supported(source)
    common = _common_dir(source)
    root, existing = _workspace_root(source, Path(workspace_root), common)
    selected = _normal_paths(include_untracked, label="include_untracked")
    excluded = _normal_paths(exclude, label="exclude")
    with _workspace_lock(root):
        return _prepare_locked(source, root, existing, selected, excluded)


def _prepare_locked(
    source: Path,
    root: Path,
    existing: bool,
    selected: Sequence[str],
    excluded: Sequence[str],
) -> Dict[str, Any]:
    if existing:
        manifest = _manifest(root)
        if Path(manifest["source_repo"]) != source:
            _fail("workspace root belongs to a different source repository")
        if manifest["selected_untracked"] != selected or manifest["excluded"] != excluded:
            _fail("workspace root retry has different capture options")
        assert_binding(root, Path(manifest["worktree"]))
        return manifest

    present_untracked = {row["path"]: row for row in _untracked(source)}
    for path in present_untracked:
        if _forbidden(path):
            _fail(f"transient/runtime source artifact blocks managed workspace capture: {path}")
    for path in selected:
        row = present_untracked.get(path)
        if row is None:
            _fail(f"selected untracked path is absent or ignored: {path}")
        if row["kind"] != "file":
            _fail(f"selected untracked path must be a regular file: {path}")
    for path in _index_paths(source):
        if _forbidden(path):
            _fail(f"tracked runtime path cannot enter a managed workspace: {path}")

    before = _fingerprint(source, root, selected)
    baseline_tree = before["working_tree"]
    source_head = before["head"]
    baseline_commit = source_head
    private_baseline = baseline_tree != _git_text(source, "rev-parse", "HEAD^{tree}")
    start_clean = not _git_bytes(source, "status", "--porcelain=v1", "--untracked-files=all")
    if private_baseline:
        baseline_commit = _private_commit(source, baseline_tree, source_head)
    # Recheck before making the linked worktree.  A source mutation is never
    # folded into a snapshot merely because it raced an expensive Git command.
    if not _fingerprint_equal(before, _fingerprint(source, root, selected)):
        _fail("source checkout changed during workspace capture; use a fresh root")
    branch = "codex/shiploop-" + _sha256(os.fspath(root).encode())[:16]
    if _git(source, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", readonly=True).returncode == 0:
        _fail("workspace branch already exists without a matching workspace record")
    worktree = root / "worktree"
    run_dir = root / "run"
    try:
        run_dir.mkdir(mode=0o700)
    except OSError as exc:
        _fail(f"cannot create workspace run directory: {exc}")
    result = _git(source, "worktree", "add", "-b", branch, os.fspath(worktree), baseline_commit)
    if result.returncode:
        _fail("cannot create isolated workspace worktree")
    after = _fingerprint(source, root, selected)
    manifest: Dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "prepared" if _fingerprint_equal(before, after) else "blocked",
        "source_repo": os.fspath(source),
        "source_branch": before["branch"],
        "source_head": source_head,
        "worktree": os.fspath(worktree),
        "run_dir": os.fspath(run_dir),
        "branch": branch,
        "baseline_commit": baseline_commit,
        "baseline_tree": baseline_tree,
        "initial_fingerprint": before,
        "selected_untracked": selected,
        "excluded": excluded,
        "start_clean": start_clean,
    }
    _write(root, {MANIFEST: (manifest, "ShipLoop workspace")})
    if manifest["status"] == "blocked":
        _fail("source checkout changed while creating the worktree; preserved root is blocked for recovery")
    assert_binding(root, worktree)
    return manifest


def _name_status(repo: Path, left: str, right: str) -> Dict[str, str]:
    raw = _git_bytes(repo, "diff", "--name-status", "-z", "--no-renames", left, right)
    rows = raw.split(b"\0")
    result: Dict[str, str] = {}
    index = 0
    while index < len(rows):
        if not rows[index]:
            index += 1
            continue
        status = rows[index].decode("ascii", "strict")[:1]
        index += 1
        if index >= len(rows) or status not in {"A", "D", "M", "T"}:
            _fail("unsupported Git diff status in workspace candidate")
        path = _safe_rel(rows[index].decode("utf-8", "surrogateescape"), label="candidate path")
        index += 1
        result[path] = {"A": "added", "D": "deleted"}.get(status, "modified")
    return result


def _history_paths(repo: Path, baseline: str) -> List[str]:
    raw = _git_bytes(repo, "log", "--format=", "--name-only", "-z", f"{baseline}..HEAD")
    return sorted(
        {
            _safe_rel(item.decode("utf-8", "surrogateescape"), label="candidate history path")
            for item in raw.split(b"\0")
            if item
        }
    )


def _candidate(manifest: Mapping[str, Any], root: Path) -> Tuple[Dict[str, Any], Dict[str, str], List[str]]:
    worktree = _resolved_directory(Path(manifest["worktree"]), label="workspace worktree")
    _ensure_supported(worktree, reject_runtime=False)
    if _branch(worktree) != manifest["branch"]:
        _fail("workspace branch changed after preparation")
    if _git(worktree, "merge-base", "--is-ancestor", manifest["baseline_commit"], "HEAD", readonly=True).returncode:
        _fail("workspace candidate no longer descends from its baseline")
    fingerprint = _fingerprint(worktree, root)
    changes = _name_status(worktree, manifest["baseline_tree"], fingerprint["tracked_tree"])
    for row in fingerprint["untracked"]:
        path = row["path"]
        if row["kind"] != "file":
            _fail(f"candidate has unsupported untracked path: {path}")
        changes.setdefault(path, "added")
    history = _history_paths(worktree, manifest["baseline_commit"])
    return fingerprint, changes, history


def _plan_rows(
    changes: Mapping[str, str], history: Sequence[str], excluded: Sequence[str]
) -> List[Dict[str, Any]]:
    rows = []
    for path in sorted(set(changes).union(history)):
        rows.append(
            {
                "path": path,
                "change": changes.get(path, "history-only"),
                "in_final_delta": path in changes,
                "in_history": path in history,
                "disposition": "exclude" if (_forbidden(path) or _matches_exclusion(path, excluded)) else "pending",
            }
        )
    return rows


def _reject_added_path_collisions(
    source: Path, baseline_tree: str, rows: Sequence[Mapping[str, Any]]
) -> None:
    """An ignored/untracked source file must never be overwritten by return."""
    baseline_paths = set(_tree_paths(source, baseline_tree))
    for row in rows:
        path = row["path"]
        if (
            not row["in_final_delta"]
            or row["disposition"] != "keep"
            or row["change"] != "added"
            or path in baseline_paths
        ):
            continue
        candidate = source / path
        if candidate.exists() or candidate.is_symlink():
            _fail(f"source has an untracked or ignored collision at candidate-added path: {path}")


RETURN_POLICY = (
    "fast-forward only for a clean source and committed clean candidate when every "
    "reviewed path is kept; otherwise apply only the reviewed working-tree delta "
    "without a merge or commit"
)


@_locked_existing_root
def plan_return(workspace_root: Path) -> Dict[str, Any]:
    """Generate the exact reviewed return surface; no source mutation occurs."""
    root = _resolved_directory(Path(workspace_root), label="workspace root")
    manifest = _manifest(root)
    if manifest["status"] == "blocked":
        _fail("blocked workspace cannot produce a return plan")
    source = _repo_root(Path(manifest["source_repo"]))
    initial = manifest["initial_fingerprint"]
    if not _fingerprint_equal(initial, _fingerprint(source, root, manifest["selected_untracked"])):
        _fail("source checkout drifted since preparation; return is blocked")
    candidate, changes, history = _candidate(manifest, root)
    plan: Dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "version": VERSION,
        "status": "pending",
        "return_policy": RETURN_POLICY,
        "source_fingerprint": initial,
        "candidate_fingerprint": candidate,
        "paths": _plan_rows(changes, history, manifest["excluded"]),
    }
    manifest["status"] = "return-planned"
    manifest["candidate_fingerprint"] = candidate
    _write(
        root,
        {
            MANIFEST: (manifest, "ShipLoop workspace"),
            RETURN_PLAN: (plan, "ShipLoop return plan"),
        },
    )
    return plan


def _validate_plan(
    root: Path, manifest: Mapping[str, Any], plan: Mapping[str, Any], candidate: Mapping[str, Any], changes: Mapping[str, str], history: Sequence[str]
) -> List[Dict[str, Any]]:
    required = {"schema", "version", "status", "return_policy", "source_fingerprint", "candidate_fingerprint", "paths"}
    if set(plan) != required or plan.get("schema") != PLAN_SCHEMA or plan.get("version") != VERSION:
        _fail("return plan has an unsupported schema")
    if plan.get("status") not in {"pending", "ready"}:
        _fail("return plan has an invalid status")
    if plan.get("return_policy") != RETURN_POLICY:
        _fail("return plan policy was edited")
    if not _fingerprint_equal(plan.get("source_fingerprint", {}), manifest["initial_fingerprint"]):
        _fail("return plan is bound to another source state")
    if not _fingerprint_equal(plan.get("candidate_fingerprint", {}), candidate):
        _fail("return plan is stale because candidate state changed")
    expected = _plan_rows(changes, history, manifest["excluded"])
    supplied = plan.get("paths")
    if not isinstance(supplied, list) or len(supplied) != len(expected):
        _fail("return plan paths do not match the candidate")
    expected_by_path = {row["path"]: row for row in expected}
    if len(expected_by_path) != len(supplied):
        _fail("return plan contains duplicate or missing path rows")
    rows: List[Dict[str, Any]] = []
    for item in supplied:
        if not isinstance(item, dict) or set(item) != set(expected[0] if expected else {"path", "change", "in_final_delta", "in_history", "disposition"}):
            _fail("return plan contains an invalid path row")
        path = item.get("path")
        if path not in expected_by_path:
            _fail("return plan contains an unknown path")
        basis = expected_by_path[path]
        if any(item.get(key) != basis[key] for key in ("path", "change", "in_final_delta", "in_history")):
            _fail("return plan path facts were edited")
        disposition = item.get("disposition")
        if disposition not in {"pending", "keep", "exclude"}:
            _fail("return plan has an invalid disposition")
        if _matches_exclusion(path, manifest["excluded"]) and disposition != "exclude":
            _fail("return plan cannot keep a caller-excluded path")
        if _forbidden(path) and disposition != "exclude":
            _fail("return plan cannot keep a protected runtime path")
        rows.append(dict(item))
    if any(row["disposition"] == "pending" for row in rows):
        _fail("return plan has unresolved path dispositions")
    return sorted(rows, key=lambda row: row["path"])


def _candidate_tree_with_kept_untracked(
    worktree: Path, root: Path, candidate_tree: str, rows: Sequence[Mapping[str, Any]]
) -> str:
    kept = [row["path"] for row in rows if row["in_final_delta"] and row["change"] == "added" and row["disposition"] == "keep"]
    if not kept:
        return candidate_tree
    descriptor, index = _temporary_index(root)
    os.close(descriptor)
    env = {"GIT_INDEX_FILE": os.fspath(index), "GIT_OPTIONAL_LOCKS": "0"}
    try:
        result = _git(worktree, "read-tree", candidate_tree, env=env, readonly=True)
        if result.returncode:
            _fail("cannot build candidate return tree")
        # Only untracked additions are absent from the tree.  A tracked added
        # path is already present, and re-adding it is harmless but unnecessary.
        for path in kept:
            if path in _tree_paths(worktree, candidate_tree):
                continue
            result = _git(worktree, "add", "-f", "--", path, env=env, readonly=True)
            if result.returncode:
                _fail(f"cannot capture approved candidate addition: {path}")
        result = _git(worktree, "write-tree", env=env, readonly=True)
        if result.returncode:
            _fail("cannot write candidate return tree")
        tree = result.stdout.decode("utf-8", "surrogateescape").strip()
        if not _SHA.fullmatch(tree):
            _fail("Git returned an invalid candidate return tree")
        return tree
    finally:
        try:
            index.unlink()
        except OSError:
            pass


def _patch(
    worktree: Path, baseline_tree: str, candidate_tree: str, rows: Sequence[Mapping[str, Any]]
) -> bytes:
    keep = [row["path"] for row in rows if row["in_final_delta"] and row["disposition"] == "keep"]
    if not keep:
        return b""
    result = _git(
        worktree,
        "diff",
        "--binary",
        "--full-index",
        "--no-ext-diff",
        "--no-renames",
        baseline_tree,
        candidate_tree,
        "--",
        *keep,
        readonly=True,
    )
    if result.returncode:
        _fail("cannot build reviewed return patch")
    return result.stdout


def _apply_cached_tree(repo: Path, root: Path, baseline_tree: str, patch: bytes) -> str:
    descriptor, index = _temporary_index(root)
    os.close(descriptor)
    env = {"GIT_INDEX_FILE": os.fspath(index), "GIT_OPTIONAL_LOCKS": "0"}
    try:
        result = _git(repo, "read-tree", baseline_tree, env=env, readonly=True)
        if result.returncode:
            _fail("cannot prepare expected return tree")
        for args in (("apply", "--cached", "--check", "-"), ("apply", "--cached", "-")):
            result = _git(repo, *args, input_bytes=patch, env=env, readonly=True)
            if result.returncode:
                _fail("reviewed return patch cannot be applied cleanly")
        result = _git(repo, "write-tree", env=env, readonly=True)
        if result.returncode:
            _fail("cannot calculate expected return tree")
        tree = result.stdout.decode("utf-8", "surrogateescape").strip()
        if not _SHA.fullmatch(tree):
            _fail("Git returned an invalid expected return tree")
        return tree
    finally:
        try:
            index.unlink()
        except OSError:
            pass


def _source_extras_after(source: Path, expected_tree: str) -> List[str]:
    head_tree = set(_tree_paths(source, _git_text(source, "rev-parse", "HEAD^{tree}")))
    index_paths = set(_index_paths(source))
    return sorted(set(_tree_paths(source, expected_tree)) - head_tree - index_paths)


def _tree_without_paths(repo: Path, root: Path, tree: str, paths: Sequence[str]) -> str:
    if not paths:
        return tree
    descriptor, index = _temporary_index(root)
    os.close(descriptor)
    env = {"GIT_INDEX_FILE": os.fspath(index), "GIT_OPTIONAL_LOCKS": "0"}
    try:
        for args in (("read-tree", tree), ("update-index", "--force-remove", "--", *paths)):
            result = _git(repo, *args, env=env, readonly=True)
            if result.returncode:
                _fail("cannot calculate tracked portion of returned source")
        result = _git(repo, "write-tree", env=env, readonly=True)
        if result.returncode:
            _fail("cannot write expected tracked return tree")
        value = result.stdout.decode("utf-8", "surrogateescape").strip()
        if not _SHA.fullmatch(value):
            _fail("Git returned an invalid tracked return tree")
        return value
    finally:
        try:
            index.unlink()
        except OSError:
            pass


def _file_row(repo: Path, path: str) -> Dict[str, str]:
    candidate = repo / path
    try:
        if candidate.is_symlink():
            return {
                "path": path,
                "sha256": _sha256(os.readlink(candidate).encode("utf-8", "surrogateescape")),
                "kind": "symlink",
            }
        if candidate.is_file():
            return {"path": path, "sha256": _sha256(candidate.read_bytes()), "kind": "file"}
    except OSError as exc:
        _fail(f"cannot read expected returned path {path}: {exc}")
    _fail(f"expected returned path is unavailable: {path}")
    raise AssertionError


def _ignored(repo: Path, path: str) -> bool:
    result = _git(repo, "check-ignore", "-q", "--", path, readonly=True)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    _fail(f"cannot determine ignore status for returned path: {path}")
    raise AssertionError


def _receipt(root: Path) -> Optional[Dict[str, Any]]:
    path = root / RETURN_RECEIPT
    if not path.exists():
        return None
    return _record(root, RETURN_RECEIPT, "return receipt")


def _plan_digest(plan: Mapping[str, Any]) -> str:
    # store.dumps is canonical JSON formatting for our supported primitive data.
    return _sha256(store.dumps(dict(plan), title="ShipLoop return plan").encode())


def _expected_dirty_source(
    source: Path,
    worktree: Path,
    root: Path,
    manifest: Mapping[str, Any],
    patch: bytes,
    rows: Sequence[Mapping[str, Any]],
) -> Tuple[Dict[str, Any], List[str]]:
    full_tree = _apply_cached_tree(source, root, manifest["baseline_tree"], patch)
    extras = _source_extras_after(source, full_tree)
    expected = dict(manifest["initial_fingerprint"])
    expected["tracked_tree"] = _tree_without_paths(source, root, full_tree, extras)
    expected["working_tree"] = full_tree
    expected["extra_paths"] = extras
    expected_rows = {row["path"]: dict(row) for row in expected["untracked"]}
    for row in rows:
        if row["in_final_delta"] and row["disposition"] == "keep" and row["change"] == "deleted":
            expected_rows.pop(row["path"], None)
    for path in extras:
        if _ignored(source, path):
            expected_rows.pop(path, None)
        else:
            expected_rows[path] = _file_row(worktree, path)
    expected["untracked"] = sorted(expected_rows.values(), key=lambda row: row["path"])
    return expected, extras


def _source_result_matches(
    source: Path, root: Path, receipt: Mapping[str, Any]
) -> bool:
    if (
        receipt.get("schema") != RECEIPT_SCHEMA
        or receipt.get("version") != VERSION
        or receipt.get("kind") not in {"working-tree-return", "fast-forward-merge", "no-change-return"}
    ):
        return False
    expected = receipt.get("expected_source")
    extras = receipt.get("source_extra_paths")
    if not isinstance(expected, dict) or not isinstance(extras, list) or any(not isinstance(x, str) for x in extras):
        return False
    if receipt.get("kind") == "fast-forward-merge":
        try:
            status = _git(source, "status", "--porcelain=v1", "--untracked-files=all", readonly=True)
            return (
                _head(source) == expected.get("head")
                and _branch(source) == expected.get("branch")
                and _git_text(source, "rev-parse", "HEAD^{tree}") == expected.get("tree")
                and status.returncode == 0
                and not status.stdout
            )
        except WorkspaceError:
            return False
    try:
        current = _fingerprint(source, root, extras)
    except WorkspaceError:
        return False
    return _fingerprint_equal(expected, current)


def _write_receipt(root: Path, manifest: Dict[str, Any], receipt: Dict[str, Any]) -> None:
    _write(root, {MANIFEST: (manifest, "ShipLoop workspace"), RETURN_RECEIPT: (receipt, "ShipLoop return receipt")})


@_locked_existing_root
def execute_return(workspace_root: Path) -> Dict[str, Any]:
    """Return reviewed work once; refuse drift and reconcile an interrupted return."""
    root = _resolved_directory(Path(workspace_root), label="workspace root")
    manifest = _manifest(root)
    source = _repo_root(Path(manifest["source_repo"]))
    worktree = _resolved_directory(Path(manifest["worktree"]), label="workspace worktree")
    assert_binding(root, worktree)
    existing = _receipt(root)
    if existing and existing.get("status") == "returned":
        current_candidate, _, _ = _candidate(manifest, root)
        if _fingerprint_equal(existing.get("candidate_fingerprint", {}), current_candidate) and _source_result_matches(source, root, existing):
            return existing
        _fail("completed return receipt no longer matches the candidate or source checkout")
    if existing and existing.get("status") == "applying":
        current_candidate, _, _ = _candidate(manifest, root)
        if _fingerprint_equal(existing.get("candidate_fingerprint", {}), current_candidate) and _source_result_matches(source, root, existing):
            existing["status"] = "returned"
            manifest["status"] = "returned"
            _write_receipt(root, manifest, existing)
            return existing
        _fail("interrupted return cannot be reconciled; source outcome is unknown and this helper will not replay or roll back it")
    if manifest["status"] == "blocked":
        _fail("blocked workspace cannot return work")
    if not _fingerprint_equal(manifest["initial_fingerprint"], _fingerprint(source, root, manifest["selected_untracked"])):
        _fail("source checkout drifted since preparation; return is blocked")
    plan = _record(root, RETURN_PLAN, "return plan")
    candidate, changes, history = _candidate(manifest, root)
    rows = _validate_plan(root, manifest, plan, candidate, changes, history)
    if any(_forbidden(row["path"]) for row in rows):
        _fail("candidate contains a protected transient/runtime path; preserve the workspace and remove it before return")
    _reject_added_path_collisions(source, manifest["baseline_tree"], rows)

    candidate_tree = _candidate_tree_with_kept_untracked(worktree, root, candidate["tracked_tree"], rows)
    patch = _patch(worktree, manifest["baseline_tree"], candidate_tree, rows)
    plan_digest = _plan_digest(plan)
    kind = "working-tree-return"
    expected_source: Dict[str, Any]
    extras: List[str]

    clean_candidate = not _git_bytes(worktree, "status", "--porcelain=v1", "--untracked-files=all")
    all_history_kept = all(row["disposition"] == "keep" for row in rows if row["in_history"])
    has_new_commits = _head(worktree) != manifest["baseline_commit"]
    if not patch and not (manifest["start_clean"] and clean_candidate and all_history_kept and has_new_commits):
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "version": VERSION,
            "status": "returned",
            "kind": "no-change-return",
            "source_before": manifest["initial_fingerprint"],
            "candidate_fingerprint": candidate,
            "plan_digest": plan_digest,
            "expected_source": manifest["initial_fingerprint"],
            "source_extra_paths": manifest["selected_untracked"],
        }
        manifest["status"] = "returned"
        _write_receipt(root, manifest, receipt)
        return receipt
    if manifest["start_clean"] and clean_candidate and all_history_kept:
        # A true fast-forward preserves candidate commits only after every
        # history path was explicitly reviewed.  Protected paths were rejected
        # before a plan existed, including add-then-delete transient commits.
        result = _git(source, "merge-base", "--is-ancestor", manifest["source_head"], "HEAD", readonly=True)
        if result.returncode:
            _fail("source branch no longer descends from its prepared HEAD")
        expected_source = {
            "head": _head(worktree),
            "branch": manifest["source_branch"],
            "tree": _git_text(worktree, "rev-parse", "HEAD^{tree}"),
        }
        kind = "fast-forward-merge"
        intent = {
            "schema": RECEIPT_SCHEMA, "version": VERSION, "status": "applying", "kind": kind,
            "source_before": manifest["initial_fingerprint"], "candidate_fingerprint": candidate,
            "plan_digest": plan_digest, "expected_source": expected_source, "source_extra_paths": [],
        }
        _write_receipt(root, manifest, intent)
        if not _fingerprint_equal(manifest["initial_fingerprint"], _fingerprint(source, root, manifest["selected_untracked"])):
            _fail("source checkout drifted before fast-forward; persisted intent requires reconciliation")
        result = _git(source, "merge", "--ff-only", "--no-overwrite-ignore", manifest["branch"])
        if result.returncode:
            _fail("fast-forward merge reported failure; source outcome is unknown and the persisted intent must be reconciled")
    else:
        # Never mutate the source index in the dirty-start route.  ``--check``
        # happens before the real apply, and the persisted intent lets retry
        # recognize an apply that completed just before a process crash.
        expected_source, extras = _expected_dirty_source(
            source, worktree, root, manifest, patch, rows
        )
        checked = _git(source, "apply", "--check", "-", input_bytes=patch)
        if checked.returncode:
            _fail("reviewed delta cannot be applied cleanly; source was not returned")
        intent = {
            "schema": RECEIPT_SCHEMA, "version": VERSION, "status": "applying", "kind": kind,
            "source_before": manifest["initial_fingerprint"], "candidate_fingerprint": candidate,
            "plan_digest": plan_digest, "expected_source": expected_source, "source_extra_paths": extras,
        }
        _write_receipt(root, manifest, intent)
        if not _fingerprint_equal(manifest["initial_fingerprint"], _fingerprint(source, root, manifest["selected_untracked"])):
            _fail("source checkout drifted before apply; persisted intent requires reconciliation")
        result = _git(source, "apply", "-", input_bytes=patch)
        if result.returncode:
            _fail("return apply reported failure; source outcome is unknown and the persisted intent must be reconciled")

    if not _source_result_matches(source, root, intent):
        _fail("return command completed but source outcome is not the recorded result")
    intent["status"] = "returned"
    manifest["status"] = "returned"
    _write_receipt(root, manifest, intent)
    return intent


@_locked_existing_root
def completed_receipt(workspace_root: Path, repo: Path) -> Optional[Dict[str, Any]]:
    """Read-only terminal gate for the execution worktree's completed return."""
    root = _resolved_directory(Path(workspace_root), label="workspace root")
    manifest = _manifest(root)
    worktree = _resolved_directory(Path(manifest["worktree"]), label="workspace worktree")
    assert_binding(root, worktree)
    receipt = _receipt(root)
    if not receipt or receipt.get("status") != "returned":
        return None
    source = _repo_root(Path(manifest["source_repo"]))
    supplied = _repo_root(Path(repo))
    if supplied not in {source, worktree}:
        return None
    try:
        current_candidate, _, _ = _candidate(manifest, root)
    except WorkspaceError:
        return None
    if not _fingerprint_equal(receipt.get("candidate_fingerprint", {}), current_candidate):
        return None
    return receipt if _source_result_matches(source, root, receipt) else None
