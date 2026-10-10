"""What an Improve review changed in the candidate, and whether it committed it.

At ``improve-bind`` ShipLoop snapshots the candidate's working tree
(``improve/<action>-bind.md``).  At ``improve-complete`` it compares the current
tree with that snapshot:

* A file the review changed that still differs from ``HEAD`` is an uncommitted
  review edit, and the import is refused (owner rule 2026-09-26: an Improve
  review makes warranted changes and commits them).  Work that was already
  uncommitted before the review is not the review's and is left alone.  A
  receipt ``no_commit`` reason, citing the user's or repository's instruction,
  records the edits instead of refusing.
* When the end-of-work review changed the tree, ShipLoop reruns every completed
  item's recorded test commands before accepting.  An unchanged tree keeps the
  recorded passes: nothing is rerun.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import shiploop_lint as lint
import shiploop_store as store
import shiploop_test_loop as test_loop


def bind_path(action: str) -> str:
    return "improve/" + action + "-bind.md"


def _snapshot(run_dir: Path, repo: Path) -> Optional[Dict[str, str]]:
    top = lint.git_toplevel(repo)
    if top is None:
        return None
    prefix = lint.scope_prefix(top, repo)
    index = Path(run_dir) / "lint" / "tmp" / ("improve-" + uuid.uuid4().hex + ".index")
    try:
        tree = lint.snapshot_tree(top, Path(run_dir), index, prefix=prefix)
    except lint.LintError:
        return None
    finally:
        if index.exists():
            index.unlink()
    return {"toplevel": str(top), "prefix": prefix, "tree": tree}


def bind_writes(run_dir: Path, repo: Path, action: str) -> Dict[str, str]:
    """The snapshot record written when an Improve child is bound (none outside Git)."""
    snap = _snapshot(Path(run_dir), Path(repo))
    if snap is None:
        return {}
    return {bind_path(action): store.dumps(snap, "ShipLoop Improve bind snapshot")}


def _diff(top: Path, left: str, right: str) -> List[str]:
    result = lint._git(top, "diff-tree", "-r", "-z", "--no-renames", "--name-only", left, right)
    if result.returncode:
        raise lint.LintError("cannot diff " + left + " against " + right)
    return sorted(raw.decode("utf-8", "surrogateescape") for raw in result.stdout.split(b"\0") if raw)


def review_changes(run_dir: Path, repo: Path, action: str) -> Optional[Tuple[List[str], List[str]]]:
    """(paths the review changed, of those the ones not committed); ``None`` when unknown."""
    path = Path(run_dir) / bind_path(action)
    if not path.is_file():
        return None
    bound = store.read_record(path)
    if not isinstance(bound, Mapping):
        return None
    now = _snapshot(Path(run_dir), Path(repo))
    if now is None or now["toplevel"] != bound.get("toplevel"):
        return None
    top = Path(now["toplevel"])
    try:
        changed = [p for p in _diff(top, str(bound["tree"]), now["tree"]) if not lint._runtime_path(p)]
        head = lint._git(top, "rev-parse", "--verify", "-q", "HEAD^{tree}")
        head_tree = head.stdout.decode("ascii", "replace").strip() if head.returncode == 0 else \
            "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        dirty = set(_diff(top, head_tree, now["tree"]))
    except lint.LintError:
        return None
    return changed, [p for p in changed if p in dirty]


def uncommitted(changes: Optional[Tuple[List[str], List[str]]], receipt: Mapping[str, Any]) -> List[str]:
    """The files the review changed and left uncommitted ([] when none, when unknown, or when the receipt says not to)."""
    if changes is None or str(receipt.get("no_commit") or "").strip():
        return []
    return list(changes[1])


def commit_refusal(paths: List[str], message_path: str, command: str, complete_command: str) -> str:
    """The import refusal for the review's uncommitted edits.

    Line 1 is the fix and the exact command (last, so it can be copied).  The exit for a user's or repository's
    instruction not to commit is improve-complete's ``--no-commit`` flag, which fills the receipt's ``no_commit``;
    both improve-complete lines print the command, so a parent that has lost its packet needs nothing else.
    """
    return ("Commit this review's changes first: write the message to " + message_path + " with a file tool, "
            "then run: " + command + "\n"
            "ShipLoop Improve import: the review changed these files but did not commit them:\n"
            + "".join("- " + path + "\n" for path in paths)
            + "improve-commit commits exactly these files and needs a \"Key learnings:\" line in the message "
              "(\"Key learnings: none\" when nothing was learned); a git commit typed by hand skips that check.\n"
              "Then run the improve-complete command again: " + complete_command + "\n"
              "If the user or repository said not to commit, record their instruction instead: "
            + complete_command + " --no-commit \"<their instruction>\"")


def rerun_commands(state: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Every completed item's recorded test commands, once each, in item order."""
    seen: Dict[str, Dict[str, Any]] = {}
    for item in list(state.get("completed_work_items") or ()) + [
            row["id"] for row in state.get("work_items", ())]:
        _action, result = test_loop._step_plan(state, item)
        for row in result.get("test_commands") or ():
            seen.setdefault(row["command"], dict(row))
    return list(seen.values())


__all__ = ("bind_path", "bind_writes", "commit_refusal", "rerun_commands", "review_changes", "uncommitted")
