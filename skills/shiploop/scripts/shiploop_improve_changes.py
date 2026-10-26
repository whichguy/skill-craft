"""What an Improve review changed in the candidate, and whether it committed it.

At ``improve-bind`` ShipLoop snapshots the candidate's working tree
(``improve/<action>-bind.md``).  At the Improve stage's ``complete`` it compares the current
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

The tree is not the whole candidate: a stage whose product is its result block (a step plan, a test spec) is reviewed
in ``inbox/<action>.md`` and returned as ``inbox/<action>-final-result.md``, outside the tree.  ``result_identity``
fingerprints that result, so a pass that edits only the result is counted as an edit (advisors panel, 2026-10-25:
a tree-only count read test-spec reviews as 0 of 9 edited when 5 of 9 had edited their result).

``changed_lines`` and ``result_lines`` size a pass's edit in lines, for the convergence gate: a Haiku 5.5 review
(battleship, 2026-10-25) ran 12 passes whose edits shrank to 1-4 lines each and labelled every one non-trivial.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import shiploop_lint as lint
import shiploop_store as store
import shiploop_test_loop as test_loop


def bind_path(action: str) -> str:
    """Run-relative path of the binding file for Improve ``action``."""
    return "improve/" + action + "-bind.md"


def bind_result_path(action: str) -> str:
    """Run-relative path of the result text bound for Improve ``action`` (``result_text``), the first pass's baseline."""
    return "improve/" + action + "-bind-result.json"


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


def snapshot_tree(run_dir: Path, repo: Path) -> str:
    """The candidate's working content as a Git tree, untracked files included ("" outside Git or when the snapshot
    fails): the tree an inline implement step begins from (the navigator's ``_step_entry``), which its Improve review
    diffs against the bind snapshot."""
    snap = _snapshot(Path(run_dir), Path(repo))
    return snap["tree"] if snap else ""


_UNREAD = object()


def _result_block(run_dir: Path, action: str) -> Any:
    """The result block under review: the final result once one is written, else the inbox result the review edits in
    place; ``_UNREAD`` when neither can be read."""
    for name in (action + "-final-result.md", action + ".md"):
        path = Path(run_dir) / "inbox" / name
        if not path.is_file():
            continue
        try:
            record = store.read_record(path)
        except store.StorageError:
            return _UNREAD
        return record.get("result", record) if isinstance(record, Mapping) else record
    return _UNREAD


def result_identity(run_dir: Path, action: str) -> Optional[str]:
    """A fingerprint of the result block under review; ``None`` when it cannot be read (unknown, never "unchanged").
    The parsed block is hashed, so a verbatim copy into the final-result file is not an edit."""
    block = _result_block(run_dir, action)
    if block is _UNREAD:
        return None
    return hashlib.sha256(json.dumps(block, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def result_text(run_dir: Path, action: str) -> Optional[str]:
    """The result block under review as indented, key-sorted JSON, one value per line, so a line diff sizes an edit;
    ``None`` when it cannot be read."""
    block = _result_block(run_dir, action)
    if block is _UNREAD:
        return None
    return json.dumps(block, sort_keys=True, ensure_ascii=False, indent=1) + "\n"


def result_lines(before: Optional[str], after: Optional[str]) -> Optional[int]:
    """Lines removed plus added from ``before`` to ``after`` (two ``result_text`` values); ``None`` when either is
    unknown."""
    if before is None or after is None:
        return None
    matcher = difflib.SequenceMatcher(None, before.splitlines(), after.splitlines(), autojunk=False)
    return sum((i2 - i1) + (j2 - j1) for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag != "equal")


def changed_lines(repo: Path, left: Optional[str], right: Optional[str]) -> Optional[int]:
    """Lines removed plus added between two snapshot trees, runtime paths left out (a binary file counts as one line);
    ``None`` when either tree is unknown or Git cannot diff them."""
    top = lint.git_toplevel(Path(repo)) if left and right else None
    if top is None:
        return None
    result = lint._git(top, "diff-tree", "-r", "-z", "--no-renames", "--numstat", str(left), str(right))
    if result.returncode:
        return None
    total = 0
    for raw in result.stdout.split(b"\0"):
        added, _tab, rest = raw.decode("utf-8", "surrogateescape").partition("\t")
        deleted, _tab, path = rest.partition("\t")
        if not path or lint._runtime_path(path):
            continue
        total += 1 if added == "-" else int(added) + int(deleted)
    return total


def bind_writes(run_dir: Path, repo: Path, action: str) -> Dict[str, str]:
    """The snapshot record written when an Improve child is bound (none outside Git): the tree and the result's
    fingerprint, the baselines a pass's edits are measured against."""
    snap = _snapshot(Path(run_dir), Path(repo))
    if snap is None:
        return {}
    text = result_text(Path(run_dir), action)
    return {bind_path(action): store.dumps(dict(snap, result=result_identity(Path(run_dir), action)),
                                           "ShipLoop Improve bind snapshot"),
            **({bind_result_path(action): text} if text is not None else {})}


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
        changed = [path for path in _diff(top, str(bound["tree"]), now["tree"]) if not lint._runtime_path(path)]
        head = lint._git(top, "rev-parse", "--verify", "-q", "HEAD^{tree}")
        head_tree = head.stdout.decode("ascii", "replace").strip() if head.returncode == 0 else \
            "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        dirty = set(_diff(top, head_tree, now["tree"]))
    except lint.LintError:
        return None
    return changed, [path for path in changed if path in dirty]


def uncommitted(changes: Optional[Tuple[List[str], List[str]]], receipt: Mapping[str, Any]) -> List[str]:
    """The files the review changed and left uncommitted ([] when none, when unknown, or when the receipt says not to)."""
    if changes is None or str(receipt.get("no_commit") or "").strip():
        return []
    return list(changes[1])


def commit_refusal(paths: List[str], message_path: str, command: str, complete_command: str) -> str:
    """The import refusal for the review's uncommitted edits.

    Line 1 is the fix and the exact command (last, so it can be copied).  The exit for a user's or repository's
    instruction not to commit is complete's ``--no-commit`` flag (on the Improve stage), which fills the receipt's ``no_commit``;
    both complete lines print the command, so a parent that has lost its packet needs nothing else.
    """
    return ("Commit this review's changes first: write the message to " + message_path + " with a file tool, "
            "then run: " + command + "\n"
            "ShipLoop Improve import: the review changed these files but did not commit them:\n"
            + "".join("- " + path + "\n" for path in paths)
            + "improve-commit commits exactly these files and needs a \"Key learnings:\" line in the message "
              "(\"Key learnings: none\" when nothing was learned); a git commit typed by hand skips that check.\n"
              "Then run the callback again: " + complete_command + "\n"
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


__all__ = ("bind_path", "bind_result_path", "bind_writes", "changed_lines", "commit_refusal", "rerun_commands",
           "result_identity", "result_lines", "result_text", "review_changes", "snapshot_tree", "uncommitted")
