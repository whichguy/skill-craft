"""Validate the mandatory pre-check documentation and reuse decision.

The protocol owns cursor transitions; this module only normalizes a small,
evidence-backed result and verifies paths against the active step worktree.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from shiploop_privacy import sensitive_text


class IterationDocumentationError(ValueError):
    pass


_DOC_DECISIONS = frozenset(("created", "updated", "reused", "not-needed"))
_SKILL_DECISIONS = frozenset(("created", "updated", "reused", "not-needed"))


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise IterationDocumentationError(message)


def _text(value: Any, label: str) -> str:
    _need(isinstance(value, str) and bool(value.strip()), f"{label} must be a nonempty string")
    _need("\n" not in value and "\r" not in value, f"{label} must be a safe single line")
    _need(
        not any(ord(character) < 0x20 or 0x7F <= ord(character) <= 0x9F for character in value),
        f"{label} must not contain C0/C1 control characters",
    )
    _need(not sensitive_text(value), f"{label} must not contain credentials")
    return value.strip()


def _relative_file(worktree: Path, value: Any, label: str) -> str:
    raw = _text(value, label)
    candidate = Path(raw)
    _need(not candidate.is_absolute() and ".." not in candidate.parts, f"{label} must be repo-relative")
    _need(not candidate.parts or candidate.parts[0] not in (".git", ".shiploop", ".worktrees"), f"{label} must not name repository control files")
    normalized = os.path.normpath(raw).replace(os.sep, "/")
    _need(normalized not in ("", ".") and not normalized.startswith("../"), f"{label} must stay inside the repository")
    path = worktree / normalized
    for parent in (path, *path.parents):
        _need(not parent.is_symlink(), f"{label} contains a symlink")
        if parent == worktree:
            break
    _need(path.is_file() and not path.is_symlink(), f"{label} must name an existing regular file")
    return normalized


def _paths(worktree: Path, value: Any, label: str, *, required: bool) -> list[str]:
    _need(isinstance(value, list), f"{label} must be a list")
    if required:
        _need(value, f"{label} must not be empty for this decision")
    rows = [_relative_file(worktree, item, label) for item in value]
    _need(len(rows) == len(set(rows)), f"{label} must not repeat paths")
    return rows


def _read_regular(worktree: Path, relative: str, label: str) -> str:
    path = worktree / relative
    try:
        body = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise IterationDocumentationError(f"{label} must be UTF-8 text") from exc
    _need(bool(body.strip()), f"{label} must not be empty")
    return body


_BLOCK_DESCRIPTION_STYLES = frozenset(("|", ">", "|-", ">-", "|+", ">+"))


def _without_yaml_comment(raw: str) -> str:
    """Remove a plain-scalar comment without pretending to parse all YAML."""
    quote: str | None = None
    escaped = False
    for index, character in enumerate(raw):
        if quote is not None:
            if quote == '"' and character == "\\" and not escaped:
                escaped = True
                continue
            if character == quote and not escaped:
                quote = None
            escaped = False
            continue
        if character in ("'", '"'):
            quote = character
        elif character == "#" and (index == 0 or raw[index - 1].isspace()):
            return raw[:index].rstrip()
    return raw.rstrip()


def _top_level_frontmatter_field(lines: list[str], name: str) -> tuple[int, str]:
    """Find exactly one simple unindented YAML field without a YAML dependency."""
    matches: list[tuple[int, str]] = []
    prefix = name + ":"
    for index, line in enumerate(lines):
        if line.startswith((" ", "\t")) or not line.startswith(prefix):
            continue
        raw = line[len(prefix):]
        matches.append((index, raw.strip()))
    _need(
        len(matches) == 1,
        f"reusable_skill SKILL.md frontmatter requires meaningful {name}",
    )
    return matches[0]


def _meaningful_scalar(raw: str, name: str) -> None:
    candidate = _without_yaml_comment(raw).strip()
    _need(
        bool(candidate)
        and candidate.casefold() not in ("null", "~")
        and not candidate.startswith(("[", "{"))
        and candidate not in _BLOCK_DESCRIPTION_STYLES
        and not candidate.startswith(("- ", "? ")),
        f"reusable_skill SKILL.md frontmatter requires meaningful {name}",
    )
    if candidate.startswith(("'", '"')):
        quote = candidate[0]
        _need(
            len(candidate) >= 2 and candidate.endswith(quote) and bool(candidate[1:-1].strip()),
            f"reusable_skill SKILL.md frontmatter requires meaningful {name}",
        )


def _nonempty_block_description(lines: list[str], start: int) -> None:
    block: list[str] = []
    for line in lines[start + 1:]:
        if line and not line.startswith((" ", "\t")):
            break
        block.append(line)
    _need(
        any(line.strip() for line in block),
        "reusable_skill SKILL.md frontmatter requires meaningful description",
    )


def _frontmatter_entrypoint(worktree: Path, relative: str) -> None:
    body = _read_regular(worktree, relative, "reusable_skill SKILL.md")
    lines = body.splitlines()
    _need(lines and lines[0] == "---", "reusable_skill SKILL.md requires frontmatter")
    try:
        close = lines.index("---", 1)
    except ValueError as exc:
        raise IterationDocumentationError("reusable_skill SKILL.md frontmatter is unterminated") from exc
    frontmatter = lines[1:close]
    _need(
        any(line.strip() for line in lines[close + 1:]),
        "reusable_skill SKILL.md body must not be empty",
    )
    _name_index, name = _top_level_frontmatter_field(frontmatter, "name")
    _meaningful_scalar(name, "name")
    description_index, description = _top_level_frontmatter_field(frontmatter, "description")
    if _without_yaml_comment(description).strip() in _BLOCK_DESCRIPTION_STYLES:
        _nonempty_block_description(frontmatter, description_index)
    else:
        _meaningful_scalar(description, "description")


_MARKDOWN_TARGET = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")


def _index_names_entrypoint(worktree: Path, index: str, entrypoint: str) -> bool:
    body = _read_regular(worktree, index, "reusable_skill reference")
    if entrypoint in body:
        return True
    for raw_target in _MARKDOWN_TARGET.findall(body):
        target = raw_target.strip("<>").split("#", 1)[0]
        if not target or "://" in target:
            continue
        candidate = (Path(index).parent / target)
        normalized = os.path.normpath(os.fspath(candidate)).replace(os.sep, "/")
        if normalized == entrypoint:
            return True
    return False


def _decision(worktree: Path, value: Any, label: str, decisions: frozenset[str]) -> dict[str, Any]:
    expected = {"decision", "rationale", "paths", "references"}
    _need(isinstance(value, dict) and set(value) == expected, f"{label} has an unexpected schema")
    decision = value.get("decision")
    _need(isinstance(decision, str), f"{label} decision must be a string")
    _need(decision in decisions, f"{label} decision is not allowed")
    changed = decision in ("created", "updated")
    paths = _paths(worktree, value["paths"], f"{label} paths", required=changed)
    references = _paths(worktree, value["references"], f"{label} references", required=decision != "not-needed")
    if decision == "not-needed":
        _need(not paths and not references, f"{label} not-needed must not name paths or references")
    return {"decision": decision, "rationale": _text(value["rationale"], f"{label} rationale"), "paths": paths, "references": references}


def _skill(worktree: Path, value: Any) -> dict[str, Any]:
    base = {"decision", "rationale", "paths", "references"}
    _need(isinstance(value, dict) and base.issubset(value), "reusable_skill has an unexpected schema")
    normalized = _decision(worktree, {key: value[key] for key in base}, "reusable_skill", _SKILL_DECISIONS)
    decision = normalized["decision"]
    if decision == "not-needed":
        _need(set(value) == base, "reusable_skill not-needed has unexpected detail fields")
        return normalized
    expected = base | {"purpose", "when", "how", "inputs", "validation"}
    _need(set(value) == expected, "reusable_skill has an unexpected schema")
    details = {key: _text(value[key], f"reusable_skill {key}") for key in ("purpose", "when", "how", "inputs", "validation")}
    _need(normalized["paths"], "reusable_skill must name its actual local SKILL.md")
    entrypoints = [path for path in normalized["paths"] if Path(path).name == "SKILL.md"]
    _need(len(entrypoints) == 1, "reusable_skill must name exactly one local SKILL.md entrypoint")
    root = str(Path(entrypoints[0]).parent).replace(os.sep, "/")
    _need(root not in ("", "."), "reusable_skill SKILL.md must be inside a local directory")
    _need(all(path == root + "/SKILL.md" or path.startswith(root + "/") for path in normalized["paths"]), "reusable_skill paths must stay in its local skill directory")
    _need(normalized["references"], "reusable_skill must name actual local reference paths")
    _frontmatter_entrypoint(worktree, entrypoints[0])
    index_refs = [
        path for path in normalized["references"]
        if not path.startswith(root + "/")
        and _index_names_entrypoint(worktree, path, entrypoints[0])
    ]
    _need(index_refs, "reusable_skill references must include an exposed local index that names SKILL.md")
    return {**normalized, **details}


def validate_skill_assessment(value: Any) -> dict[str, Any]:
    """Normalize the host-reported skill lookup bound to a step-plan result.

    These are references, not script-opened paths: a host may inspect installed
    skills outside the active repository.  The strict subset rule makes an
    asserted selection traceable to an inspected candidate without claiming
    that the script can judge the skill's semantic adequacy.
    """
    expected = {"inspected", "selected", "rationale", "usage"}
    _need(isinstance(value, dict) and set(value) == expected, "skill_assessment has an unexpected schema")
    _need(isinstance(value["inspected"], list) and isinstance(value["selected"], list), "skill_assessment inspected and selected must be lists")
    inspected = [_text(row, "skill_assessment inspected reference") for row in value["inspected"]]
    selected = [_text(row, "skill_assessment selected reference") for row in value["selected"]]
    _need(len(inspected) == len(set(inspected)), "skill_assessment inspected must not repeat references")
    _need(len(selected) == len(set(selected)), "skill_assessment selected must not repeat references")
    _need(set(selected).issubset(inspected), "skill_assessment selected must be a subset of inspected")
    rationale = _text(value["rationale"], "skill_assessment rationale")
    usage = _text(value["usage"], "skill_assessment usage")
    return {"inspected": inspected, "selected": selected, "rationale": rationale, "usage": usage}


def validate_result(value: Any, worktree: Path) -> dict[str, Any]:
    """Validate a completed document stage against the actual active worktree."""
    expected = {"summary", "documentation", "reusable_skill", "material", "learnings"}
    _need(isinstance(value, dict) and set(value) == expected, "iteration-document result has an unexpected schema")
    _need(worktree.is_dir() and not worktree.is_symlink(), "iteration-document worktree is unavailable")
    _need(type(value["material"]) is bool, "iteration-document material must be boolean")
    return {
        "summary": _text(value["summary"], "summary"),
        "documentation": _decision(worktree, value["documentation"], "documentation", _DOC_DECISIONS),
        "reusable_skill": _skill(worktree, value["reusable_skill"]),
        "material": value["material"],
        "learnings": _text(value["learnings"], "learnings"),
    }
