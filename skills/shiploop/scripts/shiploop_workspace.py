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
``plan_return`` / ``review_return``
    Write a reviewed-path return plan without changing the source checkout, then
    record the host's keep/exclude decisions in it (the host never edits the file).
``execute_return``
    Apply the approved delta or perform a safe fast-forward merge; after a
    verified return, carry later product changes as a follow-up return.
``assert_binding`` / ``completed_receipt``
    Protocol-start and terminal-handoff guards. Their exclusive-lock path may
    recover a crashed Markdown transaction before it evaluates the receipt.
``completed_receipt_snapshot``
    A non-mutating packet/report projection that accepts only an already-stable
    workspace and receipt.
``returned_result`` / ``export_returned_result``
    Read what the latest completed return delivered, and make a clean copy of
    exactly that tree under the workspace root.  Neither writes a repository:
    ``release-verify`` runs its consumer checks in the copy, never in the user's
    checkout (a file written there would make the receipt non-current) and never
    in the work area (which holds files the return excluded).
"""

from __future__ import annotations

import hashlib
import os
import re
import shlex
import shutil
import stat
import subprocess
import tempfile

import shiploop_git
import shiploop_grants
import shiploop_knowledge_home as knowledge_home
import threading
from contextlib import contextmanager
from functools import wraps
from pathlib import Path, PurePosixPath
from typing import Any, Container, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:  # Scripts are normally imported with their directory on sys.path.
    import shiploop_store as store
except ImportError:  # pragma: no cover - supports package-style local imports.
    from . import shiploop_store as store  # type: ignore


class WorkspaceError(RuntimeError):
    """The workspace cannot safely be prepared, returned, or recovered."""


class ReviewRefused(WorkspaceError):
    """A return plan cannot be reviewed as asked; ``undecided`` lists the paths still to decide, for the caller to show."""

    def __init__(self, message: str, undecided: Iterable[str] = ()) -> None:
        super().__init__(message)
        self.undecided = list(undecided)


class PendingDispositions(ReviewRefused):
    """The return plan still holds paths nobody decided; the caller names them and the verb that decides them."""

    def __init__(self, undecided: Iterable[str]) -> None:
        super().__init__("return plan has unresolved path dispositions", undecided)


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
FORBIDDEN_PARTS = frozenset({".git", ".shiploop", ".until-loop", ".shiploop-improve", ".worktrees", ".shiploop-workspaces", ".shiploop-runs"})

_SHA = re.compile(r"[0-9a-f]{40,64}")
_LOCK_LOCAL = threading.local()

# The clean copy of the returned result that release-verify's consumer checks run in.
CONSUMER_COPY = "consumer-check"
_RETURN_KINDS = ("fast-forward-merge", "working-tree-return", "no-change-return")

__all__ = [
    "CONSUMER_COPY",
    "PendingDispositions",
    "ReviewRefused",
    "WorkspaceError",
    "assert_binding",
    "completed_receipt",
    "returned_before",
    "completed_receipt_snapshot",
    "ROUTE_TEXT",
    "execute_return",
    "expected_return",
    "export_returned_result",
    "plan_return",
    "plan_summary",
    "prepare",
    "returned_result",
    "review_return",
    "rollback_lines",
    "route_sentence",
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
            timeout=_git_timeout(),
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



def workspace_branch(root: Path) -> str:
    """The execution branch for a workspace root; host-neutral, one per root."""
    return "shiploop/run-" + _sha256(os.fspath(root).encode())[:16]

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


def _git_timeout() -> float:
    """Seconds one Git command may take: SHIPLOOP_GIT_TIMEOUT, default 45."""
    raw = os.environ.get("SHIPLOOP_GIT_TIMEOUT", "")
    try:
        value = float(raw) if raw else 45.0
    except ValueError:
        _fail("SHIPLOOP_GIT_TIMEOUT must be a number of seconds")
        raise AssertionError
    if value <= 0:
        _fail("SHIPLOOP_GIT_TIMEOUT must be positive")
    return value


def _index_digest(repo: Path) -> str:
    """Digest of the index's staged entries (mode, object ID, stage, path).

    Hashing the raw index file made a stat-only rewrite (``touch`` then ``git
    status``) look like a source change; the entries are what the return uses.
    """
    return _sha256(_git_bytes(repo, "ls-files", "--stage", "-z", readonly=True))


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
        result = _git(repo, "add", "-u", env=env, readonly=True)
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
        "index_entries_sha256": _index_digest(repo),
        "index_paths": _index_paths(repo),
        "tracked_tree": tracked_tree,
        "working_tree": working_tree,
        "extra_paths": list(extras),
        "untracked": _untracked(repo),
    }


def _fingerprint_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return dict(left) == dict(right)


def _tree_entries(repo: Path, tree: str) -> Dict[str, Tuple[str, str]]:
    """Read a tree without materializing a private index or object."""
    if not isinstance(tree, str) or not _SHA.fullmatch(tree):
        _fail("receipt has an invalid snapshot tree")
    raw = _git_bytes(repo, "ls-tree", "-r", "-z", tree, readonly=True)
    entries: Dict[str, Tuple[str, str]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        header, separator, raw_path = record.partition(b"\t")
        fields = header.split()
        if separator != b"\t" or len(fields) != 3:
            _fail("Git returned an invalid snapshot tree entry")
        try:
            mode = fields[0].decode("ascii", "strict")
            object_type = fields[1].decode("ascii", "strict")
            object_id = fields[2].decode("ascii", "strict")
        except UnicodeDecodeError as exc:
            _fail(f"Git returned an invalid snapshot tree entry: {exc}")
            raise AssertionError from exc
        path = _safe_rel(
            raw_path.decode("utf-8", "surrogateescape"), label="snapshot tree path"
        )
        if object_type != "blob" or not _SHA.fullmatch(object_id) or path in entries:
            _fail("Git returned an invalid snapshot tree entry")
        entries[path] = (mode, object_id)
    return entries


def _tree_matches_working_tree(repo: Path, tree: str) -> bool:
    """Compare tracked working content to a recorded tree without an index write."""
    result = _git(
        repo,
        "diff",
        "--quiet",
        "--no-ext-diff",
        "--no-textconv",
        tree,
        "--",
        readonly=True,
    )
    return result.returncode == 0


def _filemode_enabled(repo: Path) -> bool:
    """Return the effective mode-comparison policy used by Git snapshots."""
    result = _git(repo, "config", "--bool", "core.filemode", readonly=True)
    if result.returncode == 1 and not result.stderr:
        # Git defaults to honoring executable bits when this setting is absent.
        return True
    if result.returncode:
        _fail("cannot inspect Git core.filemode configuration")
    value = result.stdout.strip().lower()
    if value == b"true":
        return True
    if value == b"false":
        return False
    _fail("Git returned an invalid core.filemode value")
    raise AssertionError


def _working_path_object_id(
    repo: Path, path: str, mode: str, *, filemode_enabled: bool
) -> Optional[str]:
    """Hash one untracked receipt path without asking Git to write the object."""
    candidate = repo / path
    try:
        metadata = os.lstat(candidate)
    except OSError:
        return None
    if mode == "120000":
        if not stat.S_ISLNK(metadata.st_mode):
            return None
        try:
            contents = os.readlink(candidate).encode("utf-8", "surrogateescape")
        except OSError:
            return None
        result = _git(repo, "hash-object", "--stdin", input_bytes=contents, readonly=True)
    elif mode in {"100644", "100755"}:
        if not stat.S_ISREG(metadata.st_mode):
            return None
        actual_mode = "100755" if metadata.st_mode & stat.S_IXUSR else "100644"
        if filemode_enabled and actual_mode != mode:
            return None
        if not filemode_enabled and mode != "100644":
            return None
        result = _git(
            repo,
            "hash-object",
            f"--path={path}",
            "--",
            path,
            readonly=True,
        )
    else:
        return None
    if result.returncode:
        return None
    value = result.stdout.decode("utf-8", "surrogateescape").strip()
    return value if _SHA.fullmatch(value) else None


def _fingerprint_matches_snapshot(
    repo: Path,
    expected: Mapping[str, Any],
    extras: Sequence[str] = (),
    *,
    require_regular_untracked: bool = False,
) -> bool:
    """Match a recorded fingerprint through read-only Git and filesystem reads."""
    try:
        if not isinstance(expected, Mapping):
            return False
        normalized_extras = [_safe_rel(path, label="receipt extra path") for path in extras]
        if normalized_extras != list(extras) or len(set(normalized_extras)) != len(normalized_extras):
            return False
        tracked_tree = expected.get("tracked_tree")
        working_tree = expected.get("working_tree")
        if not isinstance(tracked_tree, str) or not isinstance(working_tree, str):
            return False
        tracked_entries = _tree_entries(repo, tracked_tree)
        working_entries = _tree_entries(repo, working_tree)
        changed_paths = sorted(
            path
            for path in set(tracked_entries).union(working_entries)
            if tracked_entries.get(path) != working_entries.get(path)
        )
        if changed_paths != normalized_extras:
            return False
        if any(path not in working_entries for path in normalized_extras):
            return False
        current = {
            "head": _head(repo),
            "branch": _branch(repo),
            "index_entries_sha256": _index_digest(repo),
            "index_paths": _index_paths(repo),
            "tracked_tree": tracked_tree,
            "working_tree": working_tree,
            "extra_paths": normalized_extras,
            "untracked": _untracked(repo),
        }
        if require_regular_untracked and any(
            row["kind"] != "file" for row in current["untracked"]
        ):
            return False
        if not _fingerprint_equal(expected, current):
            return False
        if not _tree_matches_working_tree(repo, tracked_tree):
            return False
        filemode_enabled = _filemode_enabled(repo)
        return all(
            _working_path_object_id(
                repo,
                path,
                working_entries[path][0],
                filemode_enabled=filemode_enabled,
            )
            == working_entries[path][1]
            for path in normalized_extras
        )
    except WorkspaceError:
        return False


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
    # Before the first write: a host sandbox that refuses either location
    # would otherwise fail mid-creation.  Nothing exists yet to clean up.
    shiploop_grants.require(
        [(root.parent, "isolated worktree and run state", root.parent),
         (common, "git worktree add and every commit", common)])
    if not root.parent.is_dir():
        # The usual layout (<beside the repo>/.shiploop-runs/<name>) needs one new
        # directory; create exactly that level, never a deeper missing tree.
        if root.parent.exists() or root.parent.is_symlink() or not root.parent.parent.is_dir():
            _fail("workspace root parent does not exist")
        try:
            root.parent.mkdir(mode=0o700)
        except OSError as exc:
            _fail(f"cannot create workspace root parent: {exc}")
    try:
        root.mkdir(mode=0o700)
    except OSError as exc:
        _fail(f"cannot create workspace root: {exc}")
    return _resolved_directory(root, label="workspace root"), False


RUNS_DIR = ".shiploop-runs"


def require_grants(workspace_root: Path) -> None:
    """Resume-time check: a harness restarted without its grants fails here, not mid-commit."""
    worktree = Path(workspace_root) / "worktree"
    if not worktree.is_dir():
        return
    common = _common_dir(worktree)
    parent = Path(workspace_root).parent
    shiploop_grants.require(
        [(Path(workspace_root) / "run", "run state", parent), (worktree, "product changes", parent),
         (common, "every commit", common)])


def default_root(repo: Path, stamp: str) -> Path:
    """``<main-checkout-parent>/.shiploop-runs/<name>-<stamp>``: one stable directory to grant once.

    Anchored at the main checkout, not the caller's checkout: started from a
    linked worktree such as ``<main>/.claude/worktrees/x``, the caller's
    parent lies inside the main checkout.
    """
    candidate = _resolved_directory(Path(repo), label="repository")
    if _git(candidate, "rev-parse", "--is-inside-work-tree", readonly=True).returncode:
        main = candidate  # an empty directory start will bootstrap here
    else:
        source = _repo_root(candidate)
        common = _common_dir(source)
        main = common.parent if common.name == ".git" else source
    return main.parent / RUNS_DIR / f"{main.name}-{stamp}"


def require_parent_grant(workspace_root: Path) -> None:
    """Start-time check that needs no repository yet: the root's parent is writable."""
    parent = Path(workspace_root).absolute().parent
    shiploop_grants.require([(parent, "isolated worktree and run state", parent)])


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


@contextmanager
def _workspace_snapshot_lock(root: Path):
    """Acquire only an existing shared lock; never recover or create state."""
    lock = root / ".workspace.lock"
    if not hasattr(os, "O_NOFOLLOW"):
        yield False
        return
    try:
        descriptor = os.open(lock, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        yield False
        return
    try:
        try:
            import fcntl

            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                yield False
                return
            fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except (AttributeError, ImportError, OSError):
            yield False
            return
        try:
            os.lstat(root / store.JOURNAL_NAME)
        except FileNotFoundError:
            yield True
        except OSError:
            yield False
        else:
            # Any journal, even a malformed or unsafe one, needs the regular
            # recovery path before a display can make a current claim.
            yield False
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
    expected_branch = workspace_branch(root)
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
    if "index_entries_sha256" not in initial:
        _fail("workspace manifest was written by an older ShipLoop (its fingerprint hashes the raw "
              "Git index); return that workspace by hand or start a fresh one")
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


def _assert_binding(root: Path, repo: Path) -> Dict[str, Any]:
    """Check a binding while the caller has already chosen its lock policy."""
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


@_locked_existing_root
def assert_binding(root: Path, repo: Path) -> Dict[str, Any]:
    """Read-only check that an execution worktree came from this root."""
    return _assert_binding(root, repo)


_WORKSPACE_IDENTITY = shiploop_git.WORKSPACE_IDENTITY


def bootstrap_empty(repo: Path) -> Optional[str]:
    """Make an empty, non-Git starting directory a repository with one empty commit.

    Only a directory with no entries at all that is not inside any Git work
    tree qualifies; anything else is left to the normal checks.  The commit
    uses the user's configured identity when there is one, otherwise the
    workspace identity.  Returns the baseline commit, or None when nothing
    was done.
    """
    candidate = _resolved_directory(Path(repo), label="repository")
    if any(candidate.iterdir()):
        return None
    inside = _git(candidate, "rev-parse", "--is-inside-work-tree", readonly=True)
    if inside.returncode == 0:
        return None
    if _git(candidate, "init", "-q", "-b", "main").returncode:
        _fail("cannot initialize a Git repository in the empty starting directory")
    try:
        shiploop_git.commit_paths(candidate, [], "Empty baseline for the first ShipLoop run", allow_empty=True)
    except shiploop_git.CommitError:
        _fail("cannot create the empty baseline commit")
    return _head(candidate)


def _private_commit(repo: Path, tree: str, parent: str) -> str:
    result = _git(repo, "commit-tree", tree, "-p", parent, "-m", "ShipLoop private workspace baseline",
                  env=_WORKSPACE_IDENTITY)
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
    branch = workspace_branch(root)
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


def _candidate_matches_snapshot(manifest: Mapping[str, Any], receipt: Mapping[str, Any]) -> bool:
    """Verify the candidate fingerprint without a temporary index or tree write."""
    try:
        worktree = _resolved_directory(
            Path(manifest["worktree"]), label="workspace worktree"
        )
        _ensure_supported(worktree, reject_runtime=False)
        if _branch(worktree) != manifest["branch"]:
            return False
        if _git(
            worktree,
            "merge-base",
            "--is-ancestor",
            manifest["baseline_commit"],
            "HEAD",
            readonly=True,
        ).returncode:
            return False
        return _fingerprint_matches_snapshot(
            worktree,
            receipt.get("candidate_fingerprint", {}),
            require_regular_untracked=True,
        )
    except (KeyError, TypeError, WorkspaceError):
        return False


def _plan_rows(
    changes: Mapping[str, str],
    history: Sequence[str],
    excluded: Sequence[str],
    decided: Optional[Mapping[str, str]] = None,
) -> List[Dict[str, Any]]:
    """One row per candidate path.  Rules decide protected, caller-excluded and knowledge paths; a path no rule
    decides is ``pending`` unless ``decided`` carries an earlier keep/exclude for the same path."""
    rows = []
    for path in sorted(set(changes).union(history)):
        rows.append(
            {
                "path": path,
                "change": changes.get(path, "history-only"),
                "in_final_delta": path in changes,
                "in_history": path in history,
                # ShipLoop's committed knowledge home always returns with the candidate.
                "disposition": ("exclude" if (_forbidden(path) or _matches_exclusion(path, excluded))
                                else "keep" if knowledge_home.in_home(path)
                                else (decided or {}).get(path, "pending")),
            }
        )
    return rows


def _recorded_decisions(root: Path) -> Dict[str, str]:
    """The keep/exclude decisions the last return plan holds, by path; a plan that cannot be read holds none."""
    try:
        paths = _record(root, RETURN_PLAN, "return plan")["paths"]
        return {row["path"]: row["disposition"] for row in paths if row["disposition"] in ("keep", "exclude")}
    except (WorkspaceError, KeyError, TypeError):
        return {}


def _reject_added_path_collisions(
    source: Path,
    baseline_tree: str,
    rows: Sequence[Mapping[str, Any]],
    returned: Iterable[str] = (),
) -> None:
    """An ignored/untracked source file must never be overwritten by return.

    ``returned`` names paths an earlier verified return already placed in the
    source; a follow-up return may update those.
    """
    baseline_paths = set(_tree_paths(source, baseline_tree)).union(returned)
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


# What a return of each kind does, in the words review-return and the packets use.
ROUTE_TEXT = {
    "fast-forward-merge": "a fast-forward of the original branch to the run branch",
    "working-tree-return": "the kept files applied to the original working tree, with no Git merge or commit",
    "no-change-return": "no change to the original checkout",
}


def _retained_child_evidence(row: Mapping[str, Any], untracked_paths: Container[str]) -> bool:
    """A final Improve child's receipt must stay untracked in the worker until the parent imports it after return.

    Only excluded, untracked, never-committed child evidence qualifies; a committed or staged receipt, or a protected
    path in history, still blocks the return.
    """
    return (row["path"].startswith(".shiploop-improve/")
            and row["path"] in untracked_paths
            and row["disposition"] == "exclude" and not row["in_history"])


def _fast_forward_ok(worktree: Path, manifest: Mapping[str, Any], candidate: Mapping[str, Any],
                     rows: Sequence[Mapping[str, Any]]) -> bool:
    """Whether the reviewed candidate may fast-forward the source: the one rule execute_return follows.

    The source started clean, the candidate has no tracked change and no untracked file other than retained child
    evidence (which does not make a committed product candidate dirty), and every history path is kept.
    """
    untracked = {row["path"] for row in candidate["untracked"]}
    clean_tracked = not _git_bytes(worktree, "status", "--porcelain=v1", "--untracked-files=no")
    only_retained = all(_retained_child_evidence(row, untracked) for row in rows if row["path"] in untracked)
    all_history_kept = all(row["disposition"] == "keep" for row in rows if row["in_history"])
    return bool(manifest["start_clean"] and clean_tracked and only_retained and all_history_kept)


def _return_kind(prior_kind: Optional[str], fast_forward_ok: bool, has_new_commits: bool, has_patch: bool) -> str:
    """The route a return takes: execute_return follows it and expected_return reports it, one rule for both.

    A follow-up keeps the route of the return it follows; a first return is nothing to return, a fast-forward or a
    working-tree return.
    """
    if prior_kind in ("fast-forward-merge", "working-tree-return"):
        return prior_kind
    if not has_patch and not (fast_forward_ok and has_new_commits):
        return "no-change-return"
    return "fast-forward-merge" if fast_forward_ok else "working-tree-return"


RETURN_POLICY = (
    "fast-forward only for a clean source and committed candidate with no tracked "
    "changes, when every history path is kept and its only untracked files are "
    "reviewed excluded .shiploop-improve evidence; otherwise apply only the "
    "reviewed working-tree delta without a merge or commit"
)


@_locked_existing_root
def commit_leftovers(workspace_root: Path) -> shiploop_git.Committed:
    """Commit product files still uncommitted in the candidate before the return is planned.

    A file written after the last work item (a system test, a release note) is
    otherwise untracked at return, which forces the working-tree route and keeps
    every run commit off the user's branch.  Committing it here lets the reviewed
    plan fast-forward; a path the review then excludes still falls back to the
    working-tree route.  Run evidence, protected paths, caller exclusions and
    files the credential screen flags are never committed.
    """
    root = _resolved_directory(Path(workspace_root), label="workspace root")
    manifest = _manifest(root)
    worktree = _resolved_directory(Path(manifest["worktree"]), label="workspace worktree")
    if _branch(worktree) != manifest["branch"]:
        _fail("workspace branch changed after preparation")
    tracked = [name for name in _git_bytes(worktree, "diff", "--name-only", "-z", "HEAD").decode(
        "utf-8", "surrogateescape").split("\0") if name]
    paths = sorted({*tracked, *(row["path"] for row in _untracked(worktree))})
    chosen = [path for path in paths if not _forbidden(path) and not _matches_exclusion(path, manifest["excluded"])]
    if not chosen:
        return shiploop_git.Committed("", [], [])
    try:
        return shiploop_git.commit_paths(worktree, chosen, "chore(shiploop): commit files written after the last "
                                         "work item, before the return")
    except shiploop_git.CommitError as exc:
        _fail(str(exc))


@_locked_existing_root
def plan_return(workspace_root: Path, fresh: Iterable[str] = ()) -> Dict[str, Any]:
    """Generate the exact reviewed return surface; no source mutation occurs.

    A new plan reviews every path again, but a path the last plan decided keep or exclude keeps that decision (the
    same path; rows carry no content digest) so a model that lost its context does not decide twice.  ``fresh``
    names paths whose earlier decision must not carry, such as a file ``commit_leftovers`` skipped as credential-like.
    """
    root = _resolved_directory(Path(workspace_root), label="workspace root")
    manifest = _manifest(root)
    if manifest["status"] == "blocked":
        _fail("blocked workspace cannot produce a return plan")
    source = _repo_root(Path(manifest["source_repo"]))
    initial = manifest["initial_fingerprint"]
    # A follow-up plan still reviews the whole delta from the baseline.  The
    # source it starts from is the previous receipt's result, which return
    # verifies before it changes anything.
    previous = _receipt(root)
    if not (previous and previous.get("status") == "returned") and not _fingerprint_equal(
        initial, _fingerprint(source, root, manifest["selected_untracked"])
    ):
        _fail("source checkout drifted since preparation; return is blocked")
    candidate, changes, history = _candidate(manifest, root)
    skipped = set(fresh)
    decided = {path: value for path, value in _recorded_decisions(root).items() if path not in skipped}
    plan: Dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "version": VERSION,
        "status": "pending",
        "return_policy": RETURN_POLICY,
        "source_fingerprint": initial,
        "candidate_fingerprint": candidate,
        "paths": _plan_rows(changes, history, manifest["excluded"], decided),
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
    root: Path, manifest: Mapping[str, Any], plan: Mapping[str, Any], candidate: Mapping[str, Any], changes: Mapping[str, str], history: Sequence[str],
    *, allow_pending: bool = False,
) -> List[Dict[str, Any]]:
    required = {"schema", "version", "status", "return_policy", "source_fingerprint", "candidate_fingerprint", "paths"}
    if set(plan) != required or plan.get("schema") != PLAN_SCHEMA or plan.get("version") != VERSION:
        _fail("return plan has an unsupported schema")
    if plan.get("status") not in {"pending", "ready"}:
        _fail(f"return plan has an invalid status {plan.get('status')!r}; the allowed values are 'pending' and "
              "'ready', and neither is edited by hand: record decisions with workspace review-return")
    if plan.get("return_policy") != RETURN_POLICY:
        _fail("return plan policy was edited")
    if not _fingerprint_equal(plan.get("source_fingerprint", {}), manifest["initial_fingerprint"]):
        _fail("return plan is bound to another source state")
    if not _fingerprint_equal(plan.get("candidate_fingerprint", {}), candidate):
        _fail("return plan is stale because candidate state changed; run plan-return again (decisions already "
              "recorded are kept)")
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
            _fail(f"return plan cannot keep a caller-excluded path: {path}")
        if _forbidden(path) and disposition != "exclude":
            _fail(f"return plan cannot keep a protected runtime path: {path}")
        if knowledge_home.in_home(path) and disposition == "exclude" and not _matches_exclusion(
                path, manifest["excluded"]):
            _fail(f"return plan cannot exclude {path}: it is ShipLoop's knowledge (docs/shiploop/, SHIPLOOP.md), "
                  "which later runs inherit")
        rows.append(dict(item))
    undecided = [row["path"] for row in rows if row["disposition"] == "pending"]
    if undecided and not allow_pending:
        raise PendingDispositions(sorted(undecided))
    return sorted(rows, key=lambda row: row["path"])


def _summarize(plan: Mapping[str, Any], caller_excluded: Sequence[str]) -> Dict[str, Any]:
    """Counts by disposition, the undecided paths, and the excludes a review (not a rule) decided."""
    rows = plan["paths"]
    return {
        "total": len(rows),
        "keep": sum(row["disposition"] == "keep" for row in rows),
        "exclude": sum(row["disposition"] == "exclude" for row in rows),
        "pending": [row["path"] for row in rows if row["disposition"] == "pending"],
        "reviewed_excludes": [row["path"] for row in rows if row["disposition"] == "exclude"
                              and not _forbidden(row["path"]) and not _matches_exclusion(row["path"], caller_excluded)],
    }


def plan_summary(workspace_root: Path) -> Dict[str, Any]:
    """What the current return plan holds, read without changing anything (see ``_summarize``)."""
    root = _resolved_directory(Path(workspace_root), label="workspace root")
    return _summarize(_record(root, RETURN_PLAN, "return plan"), _manifest(root)["excluded"])


def _decisions(rows: Sequence[Mapping[str, Any]], keep: Iterable[str], exclude: Iterable[str]) -> Dict[str, str]:
    """The disposition each named path or directory decides.

    A name decides the plan row it equals, whatever that row holds now, and the still-undecided rows beneath it when
    it is a directory.  The most specific name wins (``--keep src --exclude src/tmp``); the same name in both lists,
    or a name that is no row and holds none, is refused with the undecided paths so the caller can correct it.
    """
    undecided = [row["path"] for row in rows if row["disposition"] == "pending"]
    chosen: Dict[str, Tuple[int, str]] = {}
    clashes: set = set()
    unknown: List[str] = []
    for action, names in (("keep", keep), ("exclude", exclude)):
        for raw in names:
            try:
                name = _safe_rel(raw, label=f"--{action} path (relative to the execution checkout)")
            except WorkspaceError as exc:
                raise ReviewRefused(str(exc), undecided) from exc
            found = False
            for row in rows:
                path = row["path"]
                if path != name and not path.startswith(name + "/"):
                    continue
                found = True
                if path != name and row["disposition"] != "pending":
                    continue
                if path not in chosen or len(name) > chosen[path][0]:
                    chosen[path] = (len(name), action)
                elif len(name) == chosen[path][0] and chosen[path][1] != action:
                    clashes.add(path)
            if not found:
                unknown.append(name)
    if unknown:
        raise ReviewRefused("not a path in the return plan: " + ", ".join(unknown), undecided)
    if clashes:
        raise ReviewRefused("named in both --keep and --exclude: " + ", ".join(sorted(clashes)), undecided)
    return {path: action for path, (_, action) in chosen.items()}


@_locked_existing_root
def review_return(workspace_root: Path, keep: Iterable[str] = (), exclude: Iterable[str] = ()) -> Dict[str, Any]:
    """Record keep/exclude decisions in the return plan, so the host supplies judgement and never edits the file.

    The decisions are checked against the plan exactly as the return checks it (protected runtime paths, caller
    exclusions and ShipLoop's knowledge are refused by name), and a refusal records nothing.  The plan's status is
    the script's own label: ``ready`` once nothing is undecided.  Returns the decisions this call recorded
    (``kept``, ``excluded``) and the plan's ``summary``.
    """
    root = _resolved_directory(Path(workspace_root), label="workspace root")
    manifest = _manifest(root)
    if manifest["status"] != "return-planned":
        _fail("no return plan is awaiting review; run plan-return first")
    plan = _record(root, RETURN_PLAN, "return plan")
    candidate, changes, history = _candidate(manifest, root)
    rows = _validate_plan(root, manifest, plan, candidate, changes, history, allow_pending=True)
    chosen = _decisions(rows, keep, exclude)
    for row in rows:
        row["disposition"] = chosen.get(row["path"], row["disposition"])
    reviewed = {**plan, "paths": rows,
                "status": "pending" if any(row["disposition"] == "pending" for row in rows) else "ready"}
    _validate_plan(root, manifest, reviewed, candidate, changes, history, allow_pending=True)
    if chosen:
        _write(root, {RETURN_PLAN: (reviewed, "ShipLoop return plan")})
    return {
        "kept": sorted(path for path, action in chosen.items() if action == "keep"),
        "excluded": sorted(path for path, action in chosen.items() if action == "exclude"),
        "summary": _summarize(reviewed if chosen else plan, manifest["excluded"]),
    }


@_locked_existing_root
def expected_return(workspace_root: Path) -> Optional[str]:
    """The route a return would take now, by the rule ``execute_return`` follows; None while paths are undecided.

    Advisory: the return itself still refuses a moved source, a collision or a stale plan.
    """
    root = _resolved_directory(Path(workspace_root), label="workspace root")
    manifest = _manifest(root)
    worktree = _resolved_directory(Path(manifest["worktree"]), label="workspace worktree")
    candidate, changes, history = _candidate(manifest, root)
    rows = _validate_plan(root, manifest, _record(root, RETURN_PLAN, "return plan"), candidate, changes, history,
                          allow_pending=True)
    if any(row["disposition"] == "pending" for row in rows):
        return None
    receipt = _receipt(root)
    prior_kind = receipt.get("kind") if receipt and receipt.get("status") == "returned" else None
    return _return_kind(prior_kind, _fast_forward_ok(worktree, manifest, candidate, rows),
                        _head(worktree) != manifest["baseline_commit"],
                        any(row["in_final_delta"] and row["disposition"] == "keep" for row in rows))


def route_sentence(workspace_root: Path) -> str:
    """How this run's return will go, from workspace.md alone (read-only; raises WorkspaceError when unreadable)."""
    manifest = _manifest(_resolved_directory(Path(workspace_root), label="workspace root"))
    branch = manifest["source_branch"]
    if manifest["start_clean"]:
        return (f"Return route (from workspace.md): this run started from a clean {branch}. The return fast-forwards "
                f"{branch} to the run branch {manifest['branch']} when the candidate is committed and every path in "
                "its history is kept; if the plan excludes a committed path or leaves a file uncommitted, it applies "
                "only the kept files to the working tree instead, which is not a Git merge or commit.")
    return (f"Return route (from workspace.md): this run started from a dirty {branch}. The return applies only the "
            "kept files to the working tree: it is not a Git merge or commit, and your original index and work are "
            "left as they were.")


def rollback_lines(workspace_root: Path) -> List[str]:
    """Commands that undo each return the route above can make, from workspace.md alone (read-only).

    The anchors are the manifest's ``source_head`` and ``baseline_commit`` and the run branch, never a receipt's
    ``source_before`` (which is the previous result in a follow-up).  Every call runs in the source repository, so the
    recipes survive removing the execution worktree and name no run path.  Raises WorkspaceError when unreadable.
    """
    manifest = _manifest(_resolved_directory(Path(workspace_root), label="workspace root"))
    git = "git -C " + shlex.quote(manifest["source_repo"])
    head, base, run = manifest["source_head"], manifest["baseline_commit"], manifest["branch"]
    lines = ["Rollback of the return (SHAs and branches are from workspace.md; write the plan's rollback as plain `git` "
             "commands run from the repository root with these values, never this run's absolute paths):"]
    if manifest["start_clean"]:
        lines += [
            f"- A fast-forward, with {manifest['source_branch']} checked out and nothing committed after the "
            f"returned commits: `{git} reset --keep {head}`",
            "- A fast-forward with later commits on top. This makes the tree equal to the one before the return, so it "
            "also undoes what those later commits changed (to keep their changes, reverse only the run's files with "
            "the last recipe instead); it needs a clean working tree and discards uncommitted edits: "
            f"`{git} restore --source={head} --staged --worktree :/ && {git} commit -m "
            "'Roll back the ShipLoop return'`",
        ]
    lines.append(f"- A working-tree return, or only the run's files after a fast-forward (needs the run branch {run} and "
                 f"commit {base} to still exist; <kept paths> are the keep rows of the return plan; the reversal is left "
                 f"uncommitted): `{git} diff --binary {base} {run} -- <kept paths> | "
                 f"{git} apply -R`")
    return lines


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
    if not patch:
        return baseline_tree
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


def _source_result_matches_snapshot(source: Path, receipt: Mapping[str, Any]) -> bool:
    """Verify a returned source through read-only receipt comparisons only."""
    try:
        _ensure_supported(source, reject_runtime=False)
    except WorkspaceError:
        return False
    if (
        receipt.get("schema") != RECEIPT_SCHEMA
        or receipt.get("version") != VERSION
        or receipt.get("kind")
        not in {"working-tree-return", "fast-forward-merge", "no-change-return"}
    ):
        return False
    expected = receipt.get("expected_source")
    extras = receipt.get("source_extra_paths")
    if (
        not isinstance(expected, dict)
        or not isinstance(extras, list)
        or any(not isinstance(path, str) for path in extras)
    ):
        return False
    if receipt.get("kind") == "fast-forward-merge":
        try:
            status = _git(
                source,
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
                readonly=True,
            )
            return (
                _head(source) == expected.get("head")
                and _branch(source) == expected.get("branch")
                and _git_text(source, "rev-parse", "HEAD^{tree}") == expected.get("tree")
                and status.returncode == 0
                and not status.stdout
            )
        except WorkspaceError:
            return False
    return _fingerprint_matches_snapshot(source, expected, extras)


def _returned_paths(source: Path, receipt: Mapping[str, Any]) -> set:
    """Paths the source holds because an earlier return put them there."""
    expected = receipt.get("expected_source", {})
    if receipt.get("kind") == "fast-forward-merge":
        return set(_tree_paths(source, expected["tree"]))
    if receipt.get("kind") == "working-tree-return":
        return set(_tree_paths(source, expected["working_tree"]))
    return set()


def _write_receipt(root: Path, manifest: Dict[str, Any], receipt: Dict[str, Any]) -> None:
    _write(root, {MANIFEST: (manifest, "ShipLoop workspace"), RETURN_RECEIPT: (receipt, "ShipLoop return receipt")})


@_locked_existing_root
def execute_return(workspace_root: Path) -> Dict[str, Any]:
    """Return reviewed work; refuse drift and reconcile an interrupted return.

    Product changes committed after a verified return (for example a fix found
    by a post-deploy check) return as a follow-up from that receipt's recorded
    source state, by the same route, and the new receipt keeps the old one.
    """
    root = _resolved_directory(Path(workspace_root), label="workspace root")
    manifest = _manifest(root)
    source = _repo_root(Path(manifest["source_repo"]))
    worktree = _resolved_directory(Path(manifest["worktree"]), label="workspace worktree")
    assert_binding(root, worktree)
    existing = _receipt(root)
    previous: Optional[Dict[str, Any]] = None
    # True when the source already moved past the previous receipt: the
    # follow-up then only records a source that holds its exact result.
    adopt = False
    if existing and existing.get("status") == "returned":
        current_candidate, _, _ = _candidate(manifest, root)
        source_at_receipt = _source_result_matches(source, root, existing)
        if source_at_receipt and _fingerprint_equal(
            existing.get("candidate_fingerprint", {}), current_candidate
        ):
            return existing
        previous = existing
        adopt = not source_at_receipt
    elif existing and existing.get("status") == "applying":
        current_candidate, _, _ = _candidate(manifest, root)
        if _fingerprint_equal(existing.get("candidate_fingerprint", {}), current_candidate) and _source_result_matches(source, root, existing):
            existing["status"] = "returned"
            manifest["status"] = "returned"
            _write_receipt(root, manifest, existing)
            return existing
        prior = existing.get("previous_receipt")
        if isinstance(prior, dict) and _source_result_matches(source, root, prior):
            # The interrupted follow-up left the source exactly as the previous
            # receipt recorded it, so nothing was applied and it can be retried.
            previous = prior
        else:
            _fail("interrupted return cannot be reconciled; source outcome is unknown and this helper will not replay or roll back it")
    if manifest["status"] == "blocked":
        _fail("blocked workspace cannot return work")

    def source_unchanged() -> bool:
        if previous is not None:
            return _source_result_matches(source, root, previous)
        return _fingerprint_equal(
            manifest["initial_fingerprint"],
            _fingerprint(source, root, manifest["selected_untracked"]),
        )

    if not adopt and not source_unchanged():
        _fail("source checkout drifted since preparation; return is blocked")
    plan = _record(root, RETURN_PLAN, "return plan")
    candidate, changes, history = _candidate(manifest, root)
    rows = _validate_plan(root, manifest, plan, candidate, changes, history)
    # The final Improve child must retain its terminal receipt until the parent
    # imports it after return. Permit only excluded, untracked child evidence;
    # a committed/staged receipt or a protected path in history still blocks.
    untracked_paths = {row["path"] for row in candidate["untracked"]}
    if any(_forbidden(row["path"]) and not _retained_child_evidence(row, untracked_paths) for row in rows):
        _fail("candidate contains a protected transient/runtime path; preserve the workspace and remove it before return")
    if not adopt:
        _reject_added_path_collisions(
            source,
            manifest["baseline_tree"],
            rows,
            _returned_paths(source, previous) if previous else (),
        )

    candidate_tree = _candidate_tree_with_kept_untracked(worktree, root, candidate["tracked_tree"], rows)
    patch = _patch(worktree, manifest["baseline_tree"], candidate_tree, rows)
    plan_digest = _plan_digest(plan)

    fast_forward_ok = _fast_forward_ok(worktree, manifest, candidate, rows)
    has_new_commits = _head(worktree) != manifest["baseline_commit"]
    prior_kind = previous.get("kind") if previous else None

    def record(
        kind: str, expected_source: Mapping[str, Any], extras: Sequence[str], mutate: Any
    ) -> Dict[str, Any]:
        receipt: Dict[str, Any] = {
            "schema": RECEIPT_SCHEMA, "version": VERSION,
            "status": "returned" if mutate is None else "applying", "kind": kind,
            "source_before": previous["expected_source"] if previous else manifest["initial_fingerprint"],
            "candidate_fingerprint": candidate, "plan_digest": plan_digest,
            "expected_source": dict(expected_source), "source_extra_paths": list(extras),
        }
        if previous is not None:
            receipt["previous_receipt"] = previous
        if adopt:
            # Someone already brought this result into the source (for
            # example by copying the fix by hand).  Record it only when the
            # source is exactly the reviewed result; anything else is drift.
            if not _source_result_matches(source, root, receipt):
                _fail(
                    "source checkout changed after the previous return and does not "
                    "hold the reviewed follow-up result; reconcile it before returning"
                )
            receipt["status"] = "returned"
            receipt["source_already_returned"] = True
            mutate = None
        manifest["status"] = "returned"
        if mutate is None:
            # Nothing reaches the source: its verified state already is the result.
            _write_receipt(root, manifest, receipt)
            return receipt
        _write_receipt(root, manifest, receipt)
        if not source_unchanged():
            _fail("source checkout drifted before return; persisted intent requires reconciliation")
        mutate()
        if not _source_result_matches(source, root, receipt):
            _fail("return command completed but source outcome is not the recorded result")
        receipt["status"] = "returned"
        _write_receipt(root, manifest, receipt)
        return receipt

    def fast_forward() -> None:
        result = _git(source, "merge", "--ff-only", "--no-overwrite-ignore", manifest["branch"])
        if result.returncode:
            _fail("fast-forward merge reported failure; source outcome is unknown and the persisted intent must be reconciled")

    def fast_forward_target() -> Dict[str, Any]:
        return {
            "head": _head(worktree),
            "branch": manifest["source_branch"],
            "tree": _git_text(worktree, "rev-parse", "HEAD^{tree}"),
        }

    def apply(delta: bytes) -> Any:
        # Never mutate the source index in the working-tree route.  ``--check``
        # happens before the persisted intent, which lets retry recognize an
        # apply that completed just before a process crash.
        if adopt:
            return delta  # record() verifies the source instead of applying
        if _git(source, "apply", "--check", "-", input_bytes=delta).returncode:
            _fail("reviewed delta cannot be applied cleanly; source was not returned")

        def run() -> None:
            if _git(source, "apply", "-", input_bytes=delta).returncode:
                _fail("return apply reported failure; source outcome is unknown and the persisted intent must be reconciled")
        return run

    if prior_kind == "fast-forward-merge":
        # The source branch already holds the earlier candidate commits; only a
        # further fast-forward keeps it a plain descendant of what it received.
        if not fast_forward_ok:
            _fail(
                "a follow-up to a fast-forward return needs a clean, committed "
                "candidate with every history path kept; commit the product change "
                "and keep untracked output out of the worktree"
            )
        prior_head = previous["expected_source"]["head"]
        if _head(worktree) == prior_head:
            return record("fast-forward-merge", previous["expected_source"], [], None)
        if _git(worktree, "merge-base", "--is-ancestor", prior_head, "HEAD", readonly=True).returncode:
            _fail("workspace candidate no longer descends from the previously returned commit")
        return record("fast-forward-merge", fast_forward_target(), [], fast_forward)
    if prior_kind == "working-tree-return":
        # The source working tree holds the earlier delta, so move it from that
        # recorded result to the result the whole reviewed delta now produces.
        expected_source, extras = _expected_dirty_source(
            source, worktree, root, manifest, patch, rows
        )
        if expected_source == previous["expected_source"] and extras == previous["source_extra_paths"]:
            return record("working-tree-return", expected_source, extras, None)
        delta = _git(
            source, "diff", "--binary", "--full-index", "--no-ext-diff", "--no-textconv",
            "--no-renames", previous["expected_source"]["working_tree"],
            expected_source["working_tree"], readonly=True,
        )
        if delta.returncode:
            _fail("cannot build follow-up return patch")
        if not delta.stdout:
            return record("working-tree-return", expected_source, extras, None)
        return record("working-tree-return", expected_source, extras, apply(delta.stdout))

    kind = _return_kind(prior_kind, fast_forward_ok, has_new_commits, bool(patch))
    if kind == "no-change-return":
        return record(
            "no-change-return", manifest["initial_fingerprint"], manifest["selected_untracked"], None
        )
    if kind == "fast-forward-merge":
        # A true fast-forward preserves candidate commits only after every
        # history path was explicitly reviewed.  Protected paths were rejected
        # before a plan existed, including add-then-delete transient commits.
        result = _git(source, "merge-base", "--is-ancestor", manifest["source_head"], "HEAD", readonly=True)
        if result.returncode:
            _fail("source branch no longer descends from its prepared HEAD")
        return record("fast-forward-merge", fast_forward_target(), [], fast_forward)
    expected_source, extras = _expected_dirty_source(
        source, worktree, root, manifest, patch, rows
    )
    return record("working-tree-return", expected_source, extras, apply(patch))


@_locked_existing_root
def follow_up_knowledge_return(workspace_root: Path) -> Optional[Dict[str, Any]]:
    """Return ShipLoop's own knowledge commit after a verified return, by that return's route (plan P11).

    Runs only when a return was recorded and every path changed since its candidate
    head is ShipLoop knowledge (docs/shiploop/, SHIPLOOP.md) with nothing else dirty
    in the candidate; then it plans and executes the follow-up return, whose own
    checks refuse a moved source. Returns the new receipt, or None when it does not
    apply. A refusal (WorkspaceError) propagates; the caller leaves the return to the
    handoff guard. It never commits leftovers, retries or rolls back.
    """
    root = _resolved_directory(Path(workspace_root), label="workspace root")
    receipt = _receipt(root)
    if not receipt or receipt.get("status") != "returned":
        return None
    manifest = _manifest(root)
    worktree = _resolved_directory(Path(manifest["worktree"]), label="workspace worktree")
    head = str((receipt.get("candidate_fingerprint") or {}).get("head") or "")
    if not _SHA.fullmatch(head):
        return None
    changed = [name for name in _git_bytes(worktree, "diff", "--name-only", "-z", head, "HEAD").decode(
        "utf-8", "surrogateescape").split("\0") if name]
    dirty = [line[3:] for line in _git_bytes(worktree, "status", "--porcelain=v1", "--untracked-files=all").decode(
        "utf-8", "surrogateescape").splitlines() if line and not _forbidden(line[3:])]
    if not changed or dirty or not all(knowledge_home.in_home(path) for path in changed):
        return None
    # The new plan reviews the whole delta again: paths the last reviewed plan decided keep that decision
    # (plan_return carries it); the only new paths are knowledge, which the plan keeps.
    plan = plan_return(root)
    if any(row["disposition"] == "pending" for row in plan["paths"]):
        return None
    plan["status"] = "ready"
    _write(root, {RETURN_PLAN: (plan, "ShipLoop return plan")})
    return execute_return(root)


def _worktree_branches(source: Path) -> Dict[str, str]:
    """Registered worktrees of the source repository, by checked-out branch."""
    listed = _git(source, "worktree", "list", "--porcelain", readonly=True)
    if listed.returncode:
        return {}
    found: Dict[str, str] = {}
    path = None
    for line in listed.stdout.decode("utf-8", "replace").splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line.startswith("branch refs/heads/") and path:
            found[line[len("branch refs/heads/"):]] = path
    return found


def leftovers(workspace_root: Path, attempt_branches: Iterable[str] = ()) -> Optional[Dict[str, Any]]:
    """What this run left in the source repository, read live from Git, with removal commands.

    ShipLoop never deletes these itself: branches are recovery references and a
    kept attempt is evidence. It lists them so the user decides. `git branch -d`
    is used wherever the branch is merged into the source branch, because it
    refuses to delete unmerged work; only a kept (rejected or lost) attempt needs
    `git branch -D`, and its note says that discards that attempt's work.
    """
    try:
        manifest = _manifest(_resolved_directory(Path(workspace_root), label="workspace root"))
        source = _repo_root(Path(manifest["source_repo"]))
    except WorkspaceError:
        return None
    heads = _git(source, "for-each-ref", "--format=%(refname:short)", "refs/heads/", readonly=True)
    merged = _git(source, "branch", "--format=%(refname:short)", "--merged", manifest["source_branch"],
                  readonly=True)
    if heads.returncode or merged.returncode:
        return None
    existing = set(heads.stdout.decode("utf-8", "replace").split())
    merged_names = set(merged.stdout.decode("utf-8", "replace").split())
    run_branch = manifest.get("branch")
    in_run: set = set()
    if isinstance(run_branch, str) and run_branch in existing:
        listed = _git(source, "branch", "--format=%(refname:short)", "--merged", run_branch, readonly=True)
        in_run = set(listed.stdout.decode("utf-8", "replace").split()) if not listed.returncode else set()
    checked_out = _worktree_branches(source)
    git = "git -C " + shlex.quote(os.fspath(source))
    items: List[Dict[str, Any]] = []
    for branch in dict.fromkeys(attempt_branches):
        if branch not in existing:
            continue
        if branch in checked_out:
            is_merged = branch in merged_names
            items.append({
                "kind": "kept attempt", "branch": branch, "path": checked_out[branch], "merged": is_merged,
                # No --force: Git refuses to remove a worktree holding uncommitted work, which a lost
                # worker may have left; the user adds --force only to discard it.
                "commands": [f"{git} worktree remove {shlex.quote(checked_out[branch])}",
                             f"{git} branch {'-d' if is_merged else '-D'} {shlex.quote(branch)}"],
                "note": ("a rejected or lost chain attempt, kept as evidence. If the worktree removal refuses, "
                         "it holds uncommitted work from that attempt; add --force only to discard it"
                         + ("" if is_merged else ". Its commits are not merged: -D discards them")),
            })
        elif branch in merged_names:
            items.append({"kind": "merged attempt branch", "branch": branch, "path": None, "merged": True,
                          "commands": [f"{git} branch -d {shlex.quote(branch)}"],
                          "note": "its commits are in " + manifest["source_branch"]})
        elif branch in in_run:
            # Integrated into the run, but the run is not returned: nothing to offer yet.
            items.append({"kind": "attempt branch in the run", "branch": branch, "path": None, "merged": False,
                          "commands": [],
                          "note": "its commits are in " + str(run_branch) + ", which is not returned to "
                                  + manifest["source_branch"] + "; keep it until the run is returned"})
        else:
            items.append({"kind": "unmerged attempt branch", "branch": branch, "path": None, "merged": False,
                          "commands": [f"{git} branch -D {shlex.quote(branch)}"],
                          "note": "not merged into " + manifest["source_branch"] + "; removing it discards those commits"})
    if isinstance(run_branch, str) and run_branch in existing:
        is_merged = run_branch in merged_names
        commands = []
        if is_merged:
            # Only a returned run's workspace is offered for removal; an unreturned one holds the work.
            if run_branch in checked_out:
                commands.append(f"{git} worktree remove {shlex.quote(checked_out[run_branch])}")
            commands.append(f"{git} branch -d {shlex.quote(run_branch)}")
        items.append({
            "kind": "run branch and workspace", "branch": run_branch, "path": checked_out.get(run_branch),
            "merged": is_merged, "commands": commands,
            "note": ("returned into " + manifest["source_branch"] + "; remove it once you no longer need the run's files"
                     if is_merged else "not returned to " + manifest["source_branch"] + "; keep it while the run may "
                     "resume or return"),
        })
    return {"source": os.fspath(source), "source_branch": manifest["source_branch"], "items": items}


def returned_before(workspace_root: Path) -> bool:
    """Whether a return was recorded at all (a stale receipt still counts)."""
    try:
        receipt = _receipt(_resolved_directory(Path(workspace_root), label="workspace root"))
    except WorkspaceError:
        return False
    return bool(receipt) and receipt.get("status") == "returned"


def completed_receipt(workspace_root: Path, repo: Path) -> Optional[Dict[str, Any]]:
    """Recovery-capable terminal gate for the worktree's completed return."""
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


def completed_receipt_snapshot(workspace_root: Path, repo: Path) -> Optional[Dict[str, Any]]:
    """Return a current receipt only when display verification can stay read-only.

    Unlike the terminal guard, this function never creates the workspace lock,
    replays a Markdown transaction, creates an alternate Git index, or asks Git
    to write a tree. A missing lock, pending transaction, or busy workspace is
    deliberately an unverified display result.
    """
    try:
        root = _resolved_directory(Path(workspace_root), label="workspace root")
    except WorkspaceError:
        return None
    with _workspace_snapshot_lock(root) as locked:
        if not locked:
            return None
        try:
            manifest = _manifest(root)
            worktree = _resolved_directory(
                Path(manifest["worktree"]), label="workspace worktree"
            )
            _assert_binding(root, worktree)
            receipt = _receipt(root)
            if not receipt or receipt.get("status") != "returned":
                return None
            source = _repo_root(Path(manifest["source_repo"]))
            supplied = _repo_root(Path(repo))
            if supplied not in {source, worktree}:
                return None
            if not _candidate_matches_snapshot(manifest, receipt):
                return None
            return receipt if _source_result_matches_snapshot(source, receipt) else None
        except (KeyError, TypeError, WorkspaceError):
            return None


def returned_result(workspace_root: Path) -> Optional[Dict[str, Any]]:
    """What the newest completed return delivered, read without writing anything; None when no return is recorded.

    ``None`` means only that the receipt is absent or not ``returned``.  A manifest or receipt that cannot be read,
    an unsupported kind or a tree id that is not a Git object name raises ``WorkspaceError``: the caller surfaces
    that, it is not "no return".  The result names the ``tree`` the receipt records (``expected_source.tree`` for a
    fast-forward, ``expected_source.working_tree`` for the other two kinds), the candidate ``head`` the receipt
    covers, and ``ahead``: whether the work area has moved past that head since.

    This deliberately does not call ``completed_receipt_snapshot``: that compares the whole candidate fingerprint,
    including untracked files, so a file the model writes at release-verify would make it report "not current"
    although the receipt still names exactly what was delivered.  It takes the same shared snapshot lock, so a
    busy workspace or a pending transaction is an error here, not a half-applied read.
    """
    root = _resolved_directory(Path(workspace_root), label="workspace root")
    with _workspace_snapshot_lock(root) as locked:
        if not locked:
            _fail("the workspace is busy, has a pending transaction or lacks its lock file, so its return cannot "
                  "be read now")
        manifest = _manifest(root)
        receipt = _receipt(root)
        if not receipt or receipt.get("status") != "returned":
            return None
        worktree = _resolved_directory(Path(manifest["worktree"]), label="workspace worktree")
        _assert_binding(root, worktree)
        kind = receipt.get("kind")
        expected = receipt.get("expected_source")
        candidate = receipt.get("candidate_fingerprint")
        if (receipt.get("schema") != RECEIPT_SCHEMA or receipt.get("version") != VERSION or kind not in _RETURN_KINDS
                or not isinstance(expected, dict) or not isinstance(candidate, dict)):
            _fail("the return receipt has an unsupported schema or kind")
        tree = expected.get("tree" if kind == "fast-forward-merge" else "working_tree")
        head = candidate.get("head")
        if not (isinstance(tree, str) and _SHA.fullmatch(tree) and isinstance(head, str) and _SHA.fullmatch(head)):
            _fail("the return receipt records no valid result tree or candidate head")
        return {
            "kind": kind, "tree": tree, "head": head, "ahead": _head(worktree) != head,
            "source": manifest["source_repo"], "receipt": os.fspath(root / RETURN_RECEIPT),
            "plan": os.fspath(root / RETURN_PLAN), "copy": os.fspath(root / CONSUMER_COPY),
        }


def export_returned_result(workspace_root: Path) -> Dict[str, Any]:
    """Make ``<workspace root>/consumer-check`` hold exactly the tree the newest completed return delivered.

    The tree goes through a private index inside the workspace root (``read-tree``, then ``checkout-index``), run
    from the execution worktree because it shares the source's object database; so the source's index, HEAD,
    branches and files, the object database and the work area are all left as they were.  It is not
    ``git archive``: attributes such as ``export-ignore`` do not apply, and line-ending attributes convert as in a
    normal checkout.  The copy has no ``.git``, no ignored file and no file the return plan excluded.

    An earlier copy of this one directory is replaced; anything else at that path (a symlink, a file) is refused,
    never followed or removed.  A failure leaves no partial copy.  Returns ``returned_result``'s mapping plus
    ``path``.
    """
    root = _resolved_directory(Path(workspace_root), label="workspace root")
    found = returned_result(root)
    if found is None:
        _fail("no completed return is recorded, so there is no returned result to copy")
    destination = root / CONSUMER_COPY
    if os.path.lexists(destination):
        if destination.is_symlink():
            _fail(f"{destination} is a symlink; remove it before ShipLoop makes its copy there")
        if not destination.is_dir():
            _fail(f"{destination} is not a directory; remove it before ShipLoop makes its copy there")
        try:
            shutil.rmtree(destination)
        except OSError as exc:
            _fail(f"cannot replace the previous copy at {destination}: {exc}")
    descriptor, index = _temporary_index(root)
    os.close(descriptor)
    env = {"GIT_INDEX_FILE": os.fspath(index)}
    worktree = root / "worktree"
    try:
        for args in (("read-tree", found["tree"]),
                     ("checkout-index", "-a", "-f", "--prefix=" + os.fspath(destination) + "/")):
            result = _git(worktree, *args, env=env, readonly=True)
            if result.returncode:
                detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
                _fail(f"git {args[0]} failed while copying the returned result"
                      + (f": {detail[-1]}" if detail else ""))
        try:
            destination.mkdir(exist_ok=True)  # a tree with no file produces no directory
        except OSError as exc:
            _fail(f"cannot create the copy at {destination}: {exc}")
    except WorkspaceError:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    finally:
        try:
            index.unlink()
        except OSError:
            pass
    return {**found, "path": os.fspath(destination)}
