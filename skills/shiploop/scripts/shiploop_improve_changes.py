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

``changed_lines`` and ``result_lines`` size a pass's edit in lines, for the convergence gate: a Haiku 5.5 spec review
in a live run (2026-10-25) ran 12 passes whose edits shrank to 1-4 lines each and labelled every one non-trivial.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
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


def bind_spec_path(action: str) -> str:
    """Run-relative exact candidate-spec text bound when an Improve child starts."""
    return "improve/" + action + "-bind-spec.md"


def spec_pass_path(number: int) -> str:
    """Filename for exact candidate-spec text beside the active child's Improve pass record."""
    return "current-spec-" + str(number) + ".md"


def current_spec_snapshot(state: Mapping[str, Any]) -> Optional[Tuple[str, str]]:
    """(SHA-256, exact UTF-8 candidate text), or None only for an unbound pure fixture.

    A bound production state is validated by ``shiploop_current_spec.path``;
    a missing or damaged run binding is an error, never a fallback to the
    repository aggregate.
    """
    if not state.get("spec_root"):
        return None
    import shiploop_current_spec as current_spec

    raw = current_spec.path(state).read_bytes()
    text = raw.decode("utf-8")
    return hashlib.sha256(raw).hexdigest(), text


def current_spec_review_digest(run_dir: Path, state: Mapping[str, Any], action: str) -> Optional[str]:
    """The latest active child's pass digest, independent of the live candidate.

    Missing or unreadable pass evidence is unknown. Reading this identity must
    never replace it with a fresh hash of the file awaiting acceptance.
    """
    child = state.get("active_improve")
    if not isinstance(child, Mapping) or child.get("action_id") != action:
        return None
    try:
        import shiploop_standalone_improve as standalone

        reviews = standalone.receipt_path(child).parent / "reviews"
    except (OSError, ValueError, RuntimeError):
        return None
    passes = []
    try:
        for path in reviews.glob("pass-*.json"):
            match = re.fullmatch(r"pass-([1-9][0-9]*)\.json", path.name)
            if match:
                passes.append((int(match.group(1)), path))
        if not passes:
            return None
        # A stopped review can be restarted and restart its pass number while
        # retaining old pass evidence. Pick the newest written receipt, not the
        # highest historical pass number.
        _number, path = max(passes, key=lambda row: row[1].stat().st_mtime_ns)
        record = json.loads(path.read_text(encoding="utf-8"))
        prior = record.get("current_spec") if isinstance(record, Mapping) else None
    except (OSError, ValueError, store.StorageError):
        return None
    if not isinstance(prior, str) or not re.fullmatch(r"[0-9a-f]{64}", prior):
        return None
    return prior


def current_spec_changed_since_review(run_dir: Path, state: Mapping[str, Any], action: str) -> Optional[bool]:
    """Whether the live candidate differs from the latest recorded pass.

    ``None`` means no successful pass evidence exists or it is unreadable,
    which the caller must treat as unknown and refuse for a bound state.
    """
    snapshot = current_spec_snapshot(state)
    if snapshot is None:
        return False
    reviewed = current_spec_review_digest(run_dir, state, action)
    return None if reviewed is None else reviewed != snapshot[0]


def current_spec_changed_since_bind(run_dir: Path, state: Mapping[str, Any], action: str) -> Optional[bool]:
    """Whether the candidate differs from the exact content this Improve review began with."""
    snapshot = current_spec_snapshot(state)
    if snapshot is None:
        return False
    try:
        record = store.read_record(Path(run_dir) / bind_path(action))
    except (OSError, ValueError, store.StorageError):
        return None
    prior = record.get("current_spec") if isinstance(record, Mapping) else None
    if not isinstance(prior, str) or not re.fullmatch(r"[0-9a-f]{64}", prior):
        return None
    return prior != snapshot[0]


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


def bind_writes(run_dir: Path, repo: Path, action: str,
                state: Mapping[str, Any] | None = None) -> Dict[str, str]:
    """The binding for tree, result, and run-local current-spec identities.

    The tree is optional (non-Git runs still bind their result and current
    spec). The exact spec bytes are retained beside the digest so later passes
    can measure text changes without reading a moving baseline.
    """
    snap = _snapshot(Path(run_dir), Path(repo))
    spec = current_spec_snapshot(state) if state is not None else None
    text = result_text(Path(run_dir), action)
    if snap is None and spec is None and text is None:
        return {}
    bound = dict(snap or {})
    bound["result"] = result_identity(Path(run_dir), action)
    writes = {bind_path(action): store.dumps(bound, "ShipLoop Improve bind snapshot")}
    if text is not None:
        writes[bind_result_path(action)] = text
    if spec is not None:
        digest, spec_text = spec
        bound["current_spec"] = digest
        writes[bind_path(action)] = store.dumps(bound, "ShipLoop Improve bind snapshot")
        writes[bind_spec_path(action)] = spec_text
    return writes


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


def paths_since(run_dir: Path, repo: Path, tree: str) -> Optional[List[str]]:
    """The paths whose working content differs from the snapshot ``tree`` (``snapshot_tree``'s), ShipLoop's runtime
    files left out; ``None`` when unknown (outside Git, or a tree Git cannot diff)."""
    now = _snapshot(Path(run_dir), Path(repo))
    if now is None or not tree:
        return None
    try:
        return [path for path in _diff(Path(now["toplevel"]), tree, now["tree"]) if not lint._runtime_path(path)]
    except lint.LintError:
        return None


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


__all__ = ("bind_path", "bind_result_path", "bind_spec_path", "bind_writes", "changed_lines", "commit_refusal",
           "current_spec_changed_since_bind", "current_spec_changed_since_review", "current_spec_snapshot",
           "paths_since", "rerun_commands", "result_identity", "result_lines", "result_text", "review_changes",
           "snapshot_tree", "spec_pass_path", "uncommitted")
