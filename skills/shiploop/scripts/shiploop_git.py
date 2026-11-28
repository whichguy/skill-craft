"""ShipLoop's one way to commit (SPEC S-12): every script that commits uses ``commit_paths``.

Committing is mechanical, so the scripts do it (S-5): the knowledge home after a
stage changes it, a work item's declared changes at integrate, an Improve
review's changes, and the empty baseline of a new repository.  The helper

* stages exactly the paths it is given (deletions included) and nothing else;
* uses the configured Git identity, or the workspace identity when none is
  configured (Git would otherwise refuse to commit);
* cleans a message with ``--cleanup=whitespace``, so a Markdown ``## `` heading in it survives a user's
  ``commit.cleanup=strip``;
* makes an empty commit (a recorded remote change) with ``--allow-empty --only``, which leaves whatever else is
  staged staged;
* resolves a commit ID a model typed (``resolve_commit``): Git decides what it names, never the text;
* builds the tree a commit would hold without touching the real index (``planned_tree``), which the iteration's
  commit stage records before it commits;
* runs Git without hooks and without ambient GIT_DIR-style redirection.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Dict, List, Mapping, NamedTuple, Optional, Sequence, Tuple

WORKSPACE_IDENTITY = {
    "GIT_AUTHOR_NAME": "ShipLoop Workspace",
    "GIT_AUTHOR_EMAIL": "shiploop-workspace@local.invalid",
    "GIT_COMMITTER_NAME": "ShipLoop Workspace",
    "GIT_COMMITTER_EMAIL": "shiploop-workspace@local.invalid",
}
_REDIRECTION = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS"}


class CommitError(RuntimeError):
    """Git refused to stage or commit."""


class Committed(NamedTuple):
    """Result of a commit helper: the new commit and the paths it holds."""
    commit: str            # the new commit ID, "" when nothing was committed
    paths: List[str]       # repository-relative paths in that commit


def clean_git_env(env: Optional[Mapping[str, str]] = None, *, optional_locks: bool = False) -> Dict[str, str]:
    """Return process environment scrubbed of repository-redirecting and per-invocation git config variables."""
    merged = {key: value for key, value in os.environ.items()
              if key not in _REDIRECTION and not key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))}
    merged["GIT_TERMINAL_PROMPT"] = "0"
    if optional_locks:
        merged["GIT_OPTIONAL_LOCKS"] = "0"
    merged.update(env or {})
    return merged


def git(repo: Path, *args: str, env: Optional[Mapping[str, str]] = None) -> subprocess.CompletedProcess:
    """Run ``git`` in ``repo`` without prompts or hooks, scrubbing inherited repository-redirecting environment;
    never raises on a nonzero exit.
    """
    return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(repo), *args],
                          capture_output=True, text=True, check=False, env=clean_git_env(env))


def head_commit(repo: Path) -> Optional[str]:
    """Return the full HEAD commit SHA in ``repo``, or None outside Git / before any commit."""
    shown = git(Path(repo), "rev-parse", "--verify", "-q", "HEAD^{commit}")
    head = shown.stdout.strip()
    if shown.returncode == 0 and re.fullmatch(r"[0-9a-f]{40,64}", head):
        return head
    return None


def identity_env(repo: Path) -> Optional[Mapping[str, str]]:
    """None when the repository has an identity; otherwise the workspace identity."""
    configured = git(repo, "config", "user.email")
    return None if configured.returncode == 0 and configured.stdout.strip() else WORKSPACE_IDENTITY


def commit_paths(repo: Path, paths: Sequence[str], message: str, *, allow_empty: bool = False,
                 message_file: Optional[Path] = None) -> Committed:
    """Stage exactly ``paths`` (files or directories) and commit them.

    ``allow_empty`` with no paths records a commit with no files; it never takes what else is staged.
    """
    repo = Path(repo)
    given = ["-F", str(message_file)] if message_file is not None else ["-m", message]
    if allow_empty and not paths:
        done = git(repo, "commit", "-q", "--cleanup=whitespace", "--allow-empty", "--only", *given,
                   env=identity_env(repo))
        if done.returncode:
            raise CommitError("cannot create the commit: " + (done.stderr or done.stdout).strip())
        return Committed(git(repo, "rev-parse", "HEAD").stdout.strip(), [])
    paths = _stageable(repo, paths)
    if not paths:
        return Committed("", [])
    # A path whose deletion is already staged is in neither the checkout nor the index, and `git add` refuses it
    # by name; it needs no staging, only the commit below.
    indexed = set(git(repo, "ls-files", "-z", "--", *paths).stdout.split("\0"))
    unstaged = [path for path in paths if (repo / path).exists() or path in indexed
                or any(name.startswith(path.rstrip("/") + "/") for name in indexed)]
    added = git(repo, "add", "-A", "--", *unstaged) if unstaged else None
    if added is not None and added.returncode:
        raise CommitError("cannot stage " + ", ".join(unstaged) + ": " + added.stderr.strip())
    # Renames off: a moved file is two staged changes, and with rename detection this listing names only its new
    # path, so the commit below left the old path's deletion staged and uncommitted (a live delivery, 2026-11-21).
    staged = [line for line in git(repo, "diff", "--cached", "--name-only", "--no-renames", "-z", "--",
                                   *paths).stdout.split("\0") if line]
    if not staged:
        return Committed("", [])
    done = git(repo, "commit", "-q", "--cleanup=whitespace", *given, "--", *staged, env=identity_env(repo))
    if done.returncode:
        raise CommitError("cannot commit " + ", ".join(staged) + ": " + (done.stderr or done.stdout).strip())
    return Committed(git(repo, "rev-parse", "HEAD").stdout.strip(), staged)


def _stageable(repo: Path, paths: Sequence[str]) -> List[str]:
    """``paths`` less those with nothing to stage: neither on disk nor known to Git.  A deletion is known to Git:
    in the index while it is unstaged, and in HEAD alone once it is staged (``git mv``, or a ``git add -A``)."""
    tracked = set(git(repo, "ls-files", "-z", "--", *paths).stdout.split("\0")) if paths else set()
    if paths:
        tracked |= set(git(repo, "ls-tree", "-r", "-z", "--name-only", "HEAD", "--", *paths).stdout.split("\0"))
    return [path for path in paths if (repo / path).exists() or path in tracked
            or any(name.startswith(path.rstrip("/") + "/") for name in tracked)]


def planned_tree(repo: Path, paths: Sequence[str]) -> str:
    """The tree ``commit_paths(repo, paths, ...)`` would commit now: HEAD's tree with ``paths`` as the checkout holds
    them, built in a temporary index, so the real one is untouched.  "" when Git cannot build it."""
    repo = Path(repo)
    paths = _stageable(repo, paths)
    with tempfile.TemporaryDirectory(prefix="shiploop-tree-") as scratch:
        env = {"GIT_INDEX_FILE": str(Path(scratch) / "index")}
        if git(repo, "read-tree", "HEAD", env=env).returncode:
            return ""
        if paths and git(repo, "add", "-A", "--", *paths, env=env).returncode:
            return ""
        written = git(repo, "write-tree", env=env)
        return "" if written.returncode else written.stdout.strip()


_COMMIT_ID = re.compile(r"[0-9a-fA-F]{7,64}")


def resolve_commit(repo: Path, token: str) -> Tuple[str, str]:
    """(the full commit ID, "") when ``token`` names a commit reachable from HEAD; ("", why not) otherwise.

    Git decides, never the typed text: ``--disambiguate`` reads object names only (a branch spelled like hex
    cannot shadow one), a non-commit object is not a commit, and ``merge-base --is-ancestor`` checks HEAD.  The
    reason reads after "the ID" and never repeats the token.
    """
    repo = Path(repo)
    if _COMMIT_ID.fullmatch(token) is None:
        return "", "is not a commit ID (7 to 64 hexadecimal digits)"
    token = token.lower()
    if git(repo, "rev-parse", "--verify", "-q", "HEAD").returncode:
        return "", "cannot be checked: this repository has no commit yet"
    listed = git(repo, "rev-parse", "--disambiguate=" + token).stdout.split()
    commits = [name for name in listed if name.startswith(token)
               and git(repo, "cat-file", "-t", name).stdout.strip() == "commit"]
    if not commits:
        return "", "names no commit in this repository"
    if len(commits) > 1:
        return "", ("matches " + str(len(commits)) + " commits (" + ", ".join(name[:12] for name in commits)
                    + "); write more digits")
    reachable = git(repo, "merge-base", "--is-ancestor", commits[0], "HEAD")
    if reachable.returncode == 1:
        return "", "is not reachable from HEAD (it is on another branch, or was never merged here)"
    if reachable.returncode:
        return "", "could not be checked against HEAD: " + (reachable.stderr.strip() or "git failed")
    return commits[0], ""


__all__ = ("CommitError", "Committed", "WORKSPACE_IDENTITY", "commit_paths", "git", "identity_env", "planned_tree",
           "resolve_commit")
