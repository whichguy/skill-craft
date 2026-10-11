"""What a work item declares it will change, and what it actually changed.

ShipLoop leaves an item's ``test`` stage out only on proof: the accepted step plan
declares ``paths``, records no test command (``test_commands_na``), and every
declared path is in a non-behavioural class of the package-owned catalog
(``references/path-classes.json``).  A path no rule matches counts as code.
After ``implement``, the item's real diff against its base tree must stay inside
those declared, non-behavioural paths, or ``done`` is refused (``scope_refusal``).

ShipLoop leaves an item's ``document`` stage out when the item's real diff since its
base tree touches no behavioural path (``behavioural``: code or test), owner decision 7
of 2026-10-10.  When the diff cannot be read, document is issued.
"""

from __future__ import annotations

import fnmatch
import json
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import shiploop_lint as lint
import shiploop_test_loop as test_loop

CATALOG = Path(__file__).resolve().parent.parent / "references" / "path-classes.json"
# The stage an item without test commands leaves out (decided after implement, whose done is refused
# when the real diff leaves the declared non-behavioural paths).
TEST_STAGES = ("test",)
# The stage an item whose real diff touches no code or test path leaves out (owner decision 7, 2026-10-10).
DOCUMENT_STAGE = "document"
# Every stage ShipLoop can record as not applicable, in graph order.
LEFT_OUT_STAGES = TEST_STAGES + (DOCUMENT_STAGE,)
# The prefix a script-recorded stage's summary starts with; the E2E metrics and Run Review key on it.
NOT_APPLICABLE = "Not applicable to this item"


class ItemScopeError(ValueError):
    """A declared path list is malformed."""


def _catalog() -> Dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _matches(path: str, pattern: str) -> bool:
    if pattern.startswith("**/"):
        rest = pattern[3:]
        return fnmatch.fnmatchcase(path, rest) or fnmatch.fnmatchcase(path, "*/" + rest)
    return fnmatch.fnmatchcase(path, pattern)


def classify(path: str, catalog: Optional[Mapping[str, Any]] = None) -> str:
    """The first matching class for a repository-relative path; ``code`` when none matches."""
    catalog = catalog or _catalog()
    for name in catalog["order"]:
        if any(_matches(path, pattern) for pattern in catalog["classes"][name]):
            return name
    return "code"


def behavioural_paths(paths: Sequence[str], catalog: Optional[Mapping[str, Any]] = None) -> List[str]:
    """The entries of ``paths`` that count as code or test (any class outside ``non_behavioural``)."""
    catalog = catalog or _catalog()
    allowed = set(catalog["non_behavioural"])
    return [path for path in paths if classify(path, catalog) not in allowed]


def behavioural(paths: Sequence[str], catalog: Optional[Mapping[str, Any]] = None) -> bool:
    """True when any of ``paths`` is code or test, so the change needs the document stage.

    ``paths`` are repository-relative (an item's changed paths); a path no catalog rule matches counts as code.
    """
    if isinstance(paths, (str, bytes)) or not all(isinstance(path, str) for path in paths):
        raise ItemScopeError("behavioural takes a list of repository-relative paths")
    return bool(behavioural_paths(paths, catalog))


def normalise_paths(value: Any) -> List[str]:
    """Validate a step plan's ``paths``: repository-relative files or globs the item will change."""
    if not isinstance(value, list) or not value:
        raise ItemScopeError("paths must list the repository-relative files or globs this item will change")
    rows: List[str] = []
    for entry in value:
        if not isinstance(entry, str) or not entry.strip() or "\n" in entry:
            raise ItemScopeError("each path must be one nonblank repository-relative path or glob")
        path = entry.strip()
        path = path[2:] if path.startswith("./") else path
        if path.startswith("/") or ".." in Path(path).parts:
            raise ItemScopeError("paths must stay inside the repository: " + entry)
        rows.append(path)
    if len(set(rows)) != len(rows):
        raise ItemScopeError("paths must not repeat")
    return rows


def no_test_item(state: Mapping[str, Any], work_item: str) -> Optional[str]:
    """The reason this item's test stage can be left out, or ``None`` when it must run.

    Proof needs the final accepted step plan to record no test command with a
    reason, and to declare paths that are all non-behavioural.
    """
    _action, result = test_loop._step_plan(state, work_item)
    if result.get("test_commands") != [] or not result.get("test_commands_na") or not result.get("paths"):
        return None
    if behavioural_paths(result["paths"]):
        return None
    return ("the step plan records no test command (" + str(result["test_commands_na"]).rstrip(".")
            + ") and declares only non-code paths: " + ", ".join(result["paths"]))


def no_document_item(run_dir: Path, work_item: str) -> Optional[str]:
    """The reason this item's document stage can be left out, or ``None`` when it must run.

    Proof is the item's real diff since its base tree: it must be readable, and touch no code or test path.
    An item that changed no file gets no document stage either: there is no behaviour to document.
    """
    changed = changed_paths(run_dir, work_item)
    if changed is None or behavioural(changed):
        return None
    if not changed:
        return "the item changed no file since its base"
    return "the item's changes since its base touch no code or test path: " + ", ".join(changed)


def left_out(state: Mapping[str, Any], work_item: str, stage: str,
             run_dir: Optional[Path] = None) -> Optional[str]:
    """The reason ShipLoop records ``stage`` as not applicable to this item, or ``None`` when it is issued.

    ``test`` is left out when the step plan records no test command and declares only non-code paths;
    ``document`` when the item's real diff (read from ``run_dir``) touches no code or test path.  Without
    ``run_dir`` document is always issued.
    """
    if stage in TEST_STAGES:
        return no_test_item(state, work_item)
    if stage == DOCUMENT_STAGE and run_dir is not None:
        return no_document_item(Path(run_dir), work_item)
    return None


def declared(state: Mapping[str, Any], work_item: str) -> List[str]:
    _action, result = test_loop._step_plan(state, work_item)
    return list(result.get("paths") or ())


def changed_paths(run_dir: Path, work_item: str, *, timeout: float = 60.0) -> Optional[List[str]]:
    """Repository-relative paths the item changed since its base tree; ``None`` when unknown."""
    return changed_since(run_dir, lint.read_base(Path(run_dir), work_item), timeout=timeout)


def changed_since(run_dir: Path, base: Optional[Mapping[str, Any]], *,
                  timeout: float = 60.0) -> Optional[List[str]]:
    """Repository-relative paths whose working content differs from ``base``; ``None`` when unknown.

    ``base`` is a snapshot record with ``toplevel``, ``prefix`` and ``tree`` (``lint.read_base``, or the
    checkout snapshot an expectation entry records).  Untracked files count; ignored files and ShipLoop runtime
    metadata do not.
    """
    if not base or not base.get("toplevel") or not base.get("tree"):
        return None
    top = Path(base["toplevel"])
    prefix = str(base.get("prefix") or ".")
    index = Path(run_dir) / "lint" / "tmp" / ("scope-" + uuid.uuid4().hex + ".index")
    try:
        current = lint.snapshot_tree(top, Path(run_dir), index, prefix=prefix, timeout=timeout)
    except lint.LintError:
        return None
    finally:
        if index.exists():
            index.unlink()
    result = lint._git(top, "diff-tree", "-r", "-z", "--no-renames", "--name-only", base["tree"], current,
                       timeout=timeout)
    if result.returncode:
        return None
    paths = [raw.decode("utf-8", "surrogateescape") for raw in result.stdout.split(b"\0") if raw]
    lead = "" if prefix in (".", "") else prefix.rstrip("/") + "/"
    return sorted(path[len(lead):] for path in paths
                  if path.startswith(lead) and not lint._runtime_path(path))


def outside(paths: Sequence[str], allowed: Sequence[str]) -> List[str]:
    """Changed paths that match none of the declared paths or globs (ShipLoop's knowledge home aside)."""
    return [path for path in paths if not path.startswith("docs/shiploop/") and not any(path == rule or _matches(path, rule)
                                              or fnmatch.fnmatchcase(path, rule) for rule in allowed)]


def withheld(run_dir: Path, state: Mapping[str, Any]) -> Optional[Callable[[str], bool]]:
    """The paths a worktree run never commits (``workspace.never_committed`` over workspace.md's exclusions).

    ``None`` for an in-place run, which has no workspace manifest.  Raises ItemScopeError when the manifest of a
    worktree run cannot be read.
    """
    if state.get("execution_mode") != "navigator-worktree":
        return None
    import shiploop_workspace as workspace
    try:
        excluded = workspace.excluded_paths(Path(run_dir).parent)
    except workspace.WorkspaceError as exc:
        raise ItemScopeError("cannot read the workspace manifest: " + str(exc)) from exc
    return lambda path: workspace.never_committed(path, excluded)


def commit_scope(changed: Sequence[str], allowed: Sequence[str],
                 never: Optional[Callable[[str], bool]] = None) -> Tuple[List[str], List[str]]:
    """Split an item's changed paths into (those ShipLoop commits, those it leaves).

    ShipLoop commits the paths the step plan declared (``allowed``), ShipLoop's own knowledge home and any other
    changed file in the ``docs`` path class: the document stage edits documentation, and a README or AGENTS.md it adds
    outside the declared paths was otherwise committed by the model by hand (3 of 16 recorded runs).  A path ``never``
    holds (``withheld``: a worktree run's protected and caller-excluded paths, which ``workspace.commit_leftovers``
    skips too) is never committed.  Every other undeclared file is left: plan-return commits it in a worktree run.
    """
    undeclared = set(outside(changed, allowed))
    left = [path for path in changed
            if (never is not None and never(path)) or (path in undeclared and classify(path) != "docs")]
    return [path for path in changed if path not in left], left


def commit_item(run_dir: Path, state: Mapping[str, Any], work_item: str,
                message: str) -> Tuple[str, List[str], List[str]]:
    """Commit the item's changed files per ``commit_scope``: declared paths, documentation and the knowledge home.

    Returns (new commit ID or '', changed paths left alone (undeclared and not documentation, or withheld by the
    workspace), paths the privacy screen left uncommitted).  The model never
    writes this commit: committing is mechanical (SPEC S-5), and headless hosts
    refuse model-written ``git commit`` shell.
    """
    import shiploop_git
    changed = changed_paths(run_dir, work_item)
    if not changed:
        return "", [], []
    chosen, undeclared = commit_scope(changed, declared(state, work_item), withheld(run_dir, state))
    try:
        committed = shiploop_git.commit_paths(Path(str(state["repo"])), chosen, message)
    except shiploop_git.CommitError as exc:
        raise ItemScopeError(str(exc)) from exc
    return committed.commit, undeclared, committed.skipped


def scope_refusal(run_dir: Path, state: Mapping[str, Any], work_item: str) -> str:
    """Why implement's done is refused for an item whose test stage is left out ('' when it is fine)."""
    reason = no_test_item(state, work_item)
    if reason is None:
        return ""
    changed = changed_paths(run_dir, work_item)
    if changed is None:
        return ("ShipLoop leaves this item's test stage out because its step plan declares only non-code "
                "paths, but it cannot read the item's changes to confirm that. Report blocked so the step plan "
                "can be revised with test commands.")
    code = behavioural_paths(changed)
    stray = outside(changed, declared(state, work_item))
    if not code and not stray:
        return ""
    lines = ["ShipLoop leaves this item's test stage out because its step plan declared only non-code paths ("
             + ", ".join(declared(state, work_item)) + "), but the change goes further:"]
    lines += ["- " + path + " (" + classify(path) + ")" for path in code]
    lines += ["- " + path + " (not declared)" for path in stray if path not in code]
    lines.append("Keep the change within the declared paths, or report blocked naming these paths so the step "
                 "plan can be revised with the paths and test commands this change needs; its test stage then runs.")
    return "\n".join(lines)


__all__ = ("DOCUMENT_STAGE", "LEFT_OUT_STAGES", "NOT_APPLICABLE", "TEST_STAGES", "ItemScopeError",
           "behavioural", "behavioural_paths", "changed_paths", "changed_since", "classify", "commit_item",
           "commit_scope", "declared", "left_out", "no_document_item", "no_test_item", "normalise_paths", "outside",
           "scope_refusal", "withheld")
