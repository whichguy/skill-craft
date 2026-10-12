"""ShipLoop's one way to commit (SPEC S-12): every script that commits uses ``commit_paths``.

Committing is mechanical, so the scripts do it (S-5): the knowledge home after a
stage changes it, a work item's declared changes at integrate, an Improve
review's changes, and the empty baseline of a new repository.  The helper

* stages exactly the paths it is given (deletions included) and nothing else;
* skips any text file whose content looks like a credential (the privacy
  screen), unstaging it and naming it, never its value, so a secret does not
  reach a commit that a fast-forward return could put on the user's branch;
* uses the configured Git identity, or the workspace identity when none is
  configured (Git would otherwise refuse to commit);
* cleans a message with ``--cleanup=whitespace``, so a Markdown ``## `` heading in it survives a user's
  ``commit.cleanup=strip``;
* makes an empty commit (a recorded remote change) with ``--allow-empty --only``, which leaves whatever else is
  staged staged;
* resolves a commit ID a model typed (``resolve_commit``): Git decides what it names, never the text;
* runs Git without hooks and without ambient GIT_DIR-style redirection.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
from typing import List, Mapping, NamedTuple, Optional, Sequence, Tuple

import shiploop_privacy as privacy

WORKSPACE_IDENTITY = {
    "GIT_AUTHOR_NAME": "ShipLoop Workspace",
    "GIT_AUTHOR_EMAIL": "shiploop-workspace@local.invalid",
    "GIT_COMMITTER_NAME": "ShipLoop Workspace",
    "GIT_COMMITTER_EMAIL": "shiploop-workspace@local.invalid",
}
# Larger files are committed unscreened; the screen targets config and source text.
SCREEN_LIMIT_BYTES = 1_000_000
_REDIRECTION = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS"}


class CommitError(RuntimeError):
    """Git refused to stage or commit."""


class Committed(NamedTuple):
    """Result of a commit helper: the new commit, the paths it holds, and the paths skipped as credential-like."""
    commit: str            # the new commit ID, "" when nothing was committed
    paths: List[str]       # repository-relative paths in that commit
    skipped: List[str]     # changed paths left uncommitted because they look like they hold a credential


def git(repo: Path, *args: str, env: Optional[Mapping[str, str]] = None) -> subprocess.CompletedProcess:
    """Run ``git`` in ``repo`` without prompts or hooks, scrubbing inherited repository-redirecting environment;
    never raises on a nonzero exit.
    """
    merged = {key: value for key, value in os.environ.items()
              if key not in _REDIRECTION and not key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))}
    merged["GIT_TERMINAL_PROMPT"] = "0"
    merged.update(env or {})
    return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(repo), *args],
                          capture_output=True, text=True, check=False, env=merged)


def identity_env(repo: Path) -> Optional[Mapping[str, str]]:
    """None when the repository has an identity; otherwise the workspace identity."""
    configured = git(repo, "config", "user.email")
    return None if configured.returncode == 0 and configured.stdout.strip() else WORKSPACE_IDENTITY


def looks_secret(path: Path) -> bool:
    """A text file whose content the privacy screen flags."""
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size > SCREEN_LIMIT_BYTES:
            return False
        raw = path.read_bytes()
    except OSError:
        return False
    if b"\0" in raw:
        return False  # binary
    return privacy.sensitive_text(raw.decode("utf-8", "replace"))


def commit_paths(repo: Path, paths: Sequence[str], message: str, *, allow_empty: bool = False,
                 message_file: Optional[Path] = None) -> Committed:
    """Stage exactly ``paths`` (files or directories), screen them, and commit what remains.

    ``allow_empty`` with no paths records a commit with no files; it never takes what else is staged.
    """
    repo = Path(repo)
    given = ["-F", str(message_file)] if message_file is not None else ["-m", message]
    if allow_empty and not paths:
        done = git(repo, "commit", "-q", "--cleanup=whitespace", "--allow-empty", "--only", *given,
                   env=identity_env(repo))
        if done.returncode:
            raise CommitError("cannot create the commit: " + (done.stderr or done.stdout).strip())
        return Committed(git(repo, "rev-parse", "HEAD").stdout.strip(), [], [])
    # A path that is neither on disk nor known to Git has nothing to stage (a deletion is known to Git).
    tracked = set(git(repo, "ls-files", "-z", "--", *paths).stdout.split("\0")) if paths else set()
    paths = [path for path in paths if (repo / path).exists() or path in tracked
             or any(name.startswith(path.rstrip("/") + "/") for name in tracked)]
    if not paths:
        return Committed("", [], [])
    added = git(repo, "add", "-A", "--", *paths)
    if added.returncode:
        raise CommitError("cannot stage " + ", ".join(paths) + ": " + added.stderr.strip())
    staged = [line for line in git(repo, "diff", "--cached", "--name-only", "-z", "--", *paths).stdout.split("\0")
              if line]
    skipped = [path for path in staged if looks_secret(repo / path)]
    if skipped:
        git(repo, "reset", "-q", "--", *skipped)
    chosen = [path for path in staged if path not in skipped]
    if not chosen:
        return Committed("", [], skipped)
    done = git(repo, "commit", "-q", "--cleanup=whitespace", *given, "--", *chosen, env=identity_env(repo))
    if done.returncode:
        raise CommitError("cannot commit " + ", ".join(chosen) + ": " + (done.stderr or done.stdout).strip())
    return Committed(git(repo, "rev-parse", "HEAD").stdout.strip(), chosen, skipped)


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


def skipped_notice(skipped: Sequence[str]) -> str:
    """The line printed for files left out of a commit by the privacy screen (paths only, never values)."""
    if not skipped:
        return ""
    return ("Not committed, they look like they hold a credential: " + ", ".join(skipped)
            + ". Replace the value with a reference to where it is kept, then commit the file.")


__all__ = ("CommitError", "Committed", "WORKSPACE_IDENTITY", "commit_paths", "git", "identity_env",
           "looks_secret", "resolve_commit", "skipped_notice")
