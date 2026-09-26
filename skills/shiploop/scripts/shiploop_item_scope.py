"""What a work item declares it will change, and what it actually changed.

ShipLoop leaves an item's test stages out only on proof: the accepted step plan
declares ``paths``, records no test command (``test_commands_na``), and every
declared path is in a non-behavioural class of the package-owned catalog
(``references/path-classes.json``).  A path no rule matches counts as code.
After ``implement``, the item's real diff against its base tree must stay inside
those declared, non-behavioural paths, or ``done`` is refused.
"""

from __future__ import annotations

import fnmatch
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import shiploop_lint as lint
import shiploop_test_loop as test_loop

CATALOG = Path(__file__).resolve().parent.parent / "references" / "path-classes.json"
# Stages an item without tests leaves out, in graph order.
TEST_STAGES = ("test-spec", "baseline", "test-author", "test-red", "test-green", "test-refine", "regression")
# Of those, the stages decided after implement from the item's actual diff.
AFTER_IMPLEMENT = ("test-green", "test-refine", "regression")


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


__all__ = ("AFTER_IMPLEMENT", "TEST_STAGES", "ItemScopeError", "behavioural", "changed_paths", "classify",
           "declared", "no_test_item", "normalise_paths", "outside", "scope_refusal")
