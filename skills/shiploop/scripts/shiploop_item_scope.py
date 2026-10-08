"""What a work item declares it will change, and what it actually changed.

ShipLoop leaves an item's test stages out only on proof: the accepted step plan
declares ``paths``, records no test command (``test_commands_na``), and every
declared path is in a non-behavioural class of the package-owned catalog
(``references/path-classes.json``).  A path no rule matches counts as code.
After ``implement``, the item's real diff against its base tree must stay inside
those declared, non-behavioural paths, or ``done`` is refused.

ShipLoop leaves an item's two skill stages out when its accepted step plan records
``skill_na`` (no repo-local skill is selected, created or changed).  That is the
model's own declaration, so it is checked twice: a declared path that is a skill file
refuses the step plan, and ``document``'s done is refused when the item's real diff
touches one.  The catalog's ``skill_surface`` lists are data read only here; they are
not a path class, so ``classify`` and ``behavioural`` never read them.
"""

from __future__ import annotations

import fnmatch
import json
import uuid
from pathlib import Path
from typing import Tuple, Any, Dict, List, Mapping, Optional, Sequence

import shiploop_lint as lint
import shiploop_test_loop as test_loop

CATALOG = Path(__file__).resolve().parent.parent / "references" / "path-classes.json"
# Stages an item without tests leaves out, in graph order.
TEST_STAGES = ("test-spec", "baseline", "test-author", "test-red", "test-green", "test-refine", "regression")
# Of those, the stages decided after implement from the item's actual diff.
AFTER_IMPLEMENT = ("test-green", "test-refine", "regression")
# The two skill stages an item without skill work leaves out, after document.
SKILL_STAGES = ("skill-assess", "skill-validate")
LEFT_OUT_STAGES = TEST_STAGES + SKILL_STAGES
# The two stages that hold a skill_na declaration to account: the step plan that records it (a skill file in its paths
# refuses it) and document, whose done is refused when the item's real diff touches a skill file.  The navigator's gates
# and the Checked-by text of those stages both read these names.
SKILL_NA_PLAN_STAGE = "step-plan"
SKILL_NA_DIFF_STAGE = "document"
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


def behavioural(paths: Sequence[str], catalog: Optional[Mapping[str, Any]] = None) -> List[str]:
    """The paths that count as code or test, i.e. that need the test stages."""
    catalog = catalog or _catalog()
    allowed = set(catalog["non_behavioural"])
    return [path for path in paths if classify(path, catalog) not in allowed]


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
    """The reason this item's test stages can be left out, or ``None`` when they must run.

    Proof needs the final accepted step plan to record no test command with a
    reason, and to declare paths that are all non-behavioural.
    """
    _action, result = test_loop._step_plan(state, work_item)
    if result.get("test_commands") != [] or not result.get("test_commands_na") or not result.get("paths"):
        return None
    if behavioural(result["paths"]):
        return None
    return ("the step plan records no test command (" + str(result["test_commands_na"]).rstrip(".")
            + ") and declares only non-code paths: " + ", ".join(result["paths"]))


def _skill_na(state: Mapping[str, Any], work_item: str) -> Optional[str]:
    """The latest accepted done step plan's ``skill_na`` reason, or ``None`` (it is nonblank text when present)."""
    _action, result = test_loop._step_plan(state, work_item)
    reason = result.get("skill_na")
    return reason.strip() if isinstance(reason, str) and reason.strip() else None


def no_skill_item(state: Mapping[str, Any], work_item: str) -> Optional[str]:
    """The reason this item's skill stages can be left out, or ``None`` when they must run.

    The latest accepted done step plan carries ``skill_na``, its own reason that no repo-local skill is
    selected, created or changed.  The declaration is the model's, so the step-plan gate refuses it beside
    a skill file in ``paths`` and ``skill_scope_refusal`` refuses ``document``'s done when the item's real
    diff touches one.
    """
    reason = _skill_na(state, work_item)
    return None if reason is None else (
        "the step plan records that no repo-local skill is selected, created or changed ("
        + reason.rstrip(".") + ")")


def left_out(state: Mapping[str, Any], work_item: str, stage: str) -> Optional[str]:
    """The reason ShipLoop records ``stage`` as not applicable to this item, or ``None`` when it is issued."""
    if stage in TEST_STAGES:
        return no_test_item(state, work_item)
    if stage in SKILL_STAGES:
        return no_skill_item(state, work_item)
    return None


def skill_surface(paths: Sequence[str], kind: str = "declared") -> List[str]:
    """The entries of ``paths`` that are skill or agent-instruction files, from the catalog's ``skill_surface``.

    ``kind`` is ``declared`` (the step plan's ``paths``, which also name AGENTS.md, CLAUDE.md, GEMINI.md and
    .mcp.json) or ``observed`` (the item's real diff: strict skill files only, because the document stage is
    told to maintain AGENTS.md).  Each entry is matched as written, so a wildcard directory is not analysed:
    the observed check is the backstop.  ShipLoop's own knowledge home is exempt.
    """
    patterns = _catalog()["skill_surface"][kind]
    return [path for path in paths if not path.startswith("docs/shiploop/")
            and any(_matches(path, pattern) for pattern in patterns)]


def declared(state: Mapping[str, Any], work_item: str) -> List[str]:
    _action, result = test_loop._step_plan(state, work_item)
    return list(result.get("paths") or ())


def changed_paths(run_dir: Path, work_item: str, *, timeout: float = 60.0) -> Optional[List[str]]:
    """Repository-relative paths the item changed since its base tree; ``None`` when unknown."""
    base = lint.read_base(Path(run_dir), work_item)
    if base is None:
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


def commit_item(run_dir: Path, state: Mapping[str, Any], work_item: str,
                message: str) -> Tuple[str, List[str], List[str]]:
    """Commit the item's changed files that its step plan declared, plus the knowledge home.

    Returns (new commit ID or '', changed paths left alone because the step plan did
    not declare them, paths the privacy screen left uncommitted).  The model never
    writes this commit: committing is mechanical (SPEC S-5), and headless hosts
    refuse model-written ``git commit`` shell.
    """
    import shiploop_git
    changed = changed_paths(run_dir, work_item)
    if not changed:
        return "", [], []
    undeclared = outside(changed, declared(state, work_item))
    chosen = [path for path in changed if path not in undeclared]
    try:
        committed = shiploop_git.commit_paths(Path(str(state["repo"])), chosen, message)
    except shiploop_git.CommitError as exc:
        raise ItemScopeError(str(exc)) from exc
    return committed.commit, undeclared, committed.skipped


def scope_refusal(run_dir: Path, state: Mapping[str, Any], work_item: str) -> str:
    """Why implement's done is refused for an item whose test stages were left out ('' when it is fine)."""
    reason = no_test_item(state, work_item)
    if reason is None:
        return ""
    changed = changed_paths(run_dir, work_item)
    if changed is None:
        return ("ShipLoop left this item's test stages out because its step plan declares only non-code "
                "paths, but it cannot read the item's changes to confirm that. Report blocked so the step plan "
                "can be revised with test commands.")
    code = behavioural(changed)
    stray = outside(changed, declared(state, work_item))
    if not code and not stray:
        return ""
    lines = ["ShipLoop left this item's test stages out because its step plan declared only non-code paths ("
             + ", ".join(declared(state, work_item)) + "), but the change goes further:"]
    lines += ["- " + path + " (" + classify(path) + ")" for path in code]
    lines += ["- " + path + " (not declared)" for path in stray if path not in code]
    lines.append("Keep the change within the declared paths, or report blocked naming these paths so the step "
                 "plan can be revised with the paths and test commands this change needs; its test stages then run.")
    return "\n".join(lines)


def skill_scope_refusal(run_dir: Path, state: Mapping[str, Any], work_item: str) -> str:
    """Why document's done is refused for an item whose skill stages were left out ('' when it is fine)."""
    reason = _skill_na(state, work_item)
    if reason is None:
        return ""
    head = ("ShipLoop left this item's skill-assess and skill-validate stages out because its step plan declared "
            "skill_na (" + reason.rstrip(".") + "), but ")
    way_out = ("To keep the change, report revise: the item goes back to its step plan (it spends one of the "
               "item's revisions, and its test stages run again), where you resubmit the plan without skill_na; "
               "both skill stages then run.")
    changed = changed_paths(run_dir, work_item)
    if changed is None:
        return head + "ShipLoop cannot read the item's changes to confirm that. " + way_out
    touched = skill_surface(changed, "observed")
    if not touched:
        return ""
    return "\n".join([head + "the change touches skill files:", *("- " + path for path in touched), way_out])


__all__ = ("AFTER_IMPLEMENT", "LEFT_OUT_STAGES", "NOT_APPLICABLE", "SKILL_NA_DIFF_STAGE", "SKILL_NA_PLAN_STAGE",
           "SKILL_STAGES", "TEST_STAGES", "ItemScopeError",
           "behavioural", "changed_paths", "classify", "declared", "left_out", "no_skill_item", "no_test_item",
           "normalise_paths", "outside", "scope_refusal", "skill_scope_refusal", "skill_surface")
