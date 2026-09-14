"""Strict, reusable evidence shapes for ShipLoop's managed SDLC nodes.

The protocol owns transitions and persistent Markdown state.  This module only
normalizes small, target-specific records before a caller binds them to a
current contract, check manifest, and action.  In particular, it never accepts
a host-reported ``passed`` flag as proof that a selected check ran.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

from shiploop_privacy import sensitive_text


VERSION = 1
MAX_CASES = 128
MAX_PATHS = 32
MAX_CHECK_IDS = 64
MAX_ARGV = 128

_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_PLACEHOLDER = re.compile(
    r"\b(?:tbd|todo|to be determined|placeholder|same as above|as appropriate|"
    r"works? as expected|fill (?:this )?in|later)\b",
    re.IGNORECASE,
)
_CASE_ID = re.compile(r"CASE-[A-Z0-9][A-Z0-9._-]{0,79}\Z")
_CONTRACT_ID = re.compile(r"T-[A-Z0-9][A-Z0-9._-]{0,79}\Z")
_CHECK_ID = re.compile(r"[A-Za-z][A-Za-z0-9._:-]{0,159}\Z")
_MARKDOWN_TARGET = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")

_CONTROL_ROOTS = frozenset((".git", ".shiploop", ".worktrees"))
_COVERAGE_SURFACES = (
    "unit",
    "mock_fake",
    "integration",
    "end_to_end",
    "browser_service_api",
)
_COVERAGE_DISPOSITIONS = frozenset(
    ("selected", "not-applicable", "required-but-blocked")
)
_REFINEMENT_DISPOSITIONS = frozenset(("authored", "updated", "reused"))
_SKILL_DECISIONS = frozenset(("created", "updated", "reused", "not-needed"))


class SdlcError(ValueError):
    """A managed-SDLC record is malformed, unsafe, or incomplete."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise SdlcError(message)


def _text(value: Any, label: str, *, concrete: bool = False) -> str:
    _need(isinstance(value, str), f"{label} must be a nonempty concrete string")
    result = value.strip()
    _need(bool(result) and _CONTROL.search(result) is None, f"{label} must be a nonempty one-line string")
    _need(len(result) <= 4000, f"{label} exceeds the bounded text limit")
    _need(not sensitive_text(result), f"{label} appears to contain a credential secret")
    if concrete:
        _need(_PLACEHOLDER.search(result) is None, f"{label} must not be a placeholder")
    return result


def _identifier(value: Any, label: str, pattern: re.Pattern[str] = _CHECK_ID) -> str:
    _need(isinstance(value, str) and pattern.fullmatch(value) is not None, f"{label} must be a stable safe identifier")
    _need(not sensitive_text(value), f"{label} appears to contain a credential secret")
    return value


def _safe_relative(value: Any, label: str) -> str:
    raw = _text(value, label)
    _need("\\" not in raw, f"{label} must use a safe repository-relative path")
    candidate = Path(raw)
    _need(not candidate.is_absolute() and ".." not in candidate.parts, f"{label} must be repo-relative")
    normalized = os.path.normpath(raw).replace(os.sep, "/")
    _need(normalized not in ("", ".") and not normalized.startswith("../"), f"{label} must stay inside the repository")
    first = Path(normalized).parts[0] if Path(normalized).parts else ""
    _need(first not in _CONTROL_ROOTS, f"{label} must not name repository control files")
    return normalized


def _worktree(worktree: Path) -> Path:
    _need(isinstance(worktree, Path), "worktree must be a pathlib.Path")
    _need(worktree.is_dir() and not worktree.is_symlink(), "worktree is unavailable")
    return worktree


def _existing_file(worktree: Path, value: Any, label: str) -> str:
    relative = _safe_relative(value, label)
    path = worktree / relative
    for parent in (path, *path.parents):
        _need(not parent.is_symlink(), f"{label} contains a symlink")
        if parent == worktree:
            break
    _need(path.is_file() and not path.is_symlink(), f"{label} must name an existing regular file")
    return relative


def _test_path(value: Any, label: str, *, exists: bool, worktree: Path | None = None) -> str:
    if exists:
        _need(worktree is not None, "internal test-path validation requires a worktree")
        relative = _existing_file(worktree, value, label)
    else:
        relative = _safe_relative(value, label)
    lowered = relative.casefold()
    _need(
        any(token in lowered for token in ("test", "spec")),
        f"{label} must name a concrete test or spec path",
    )
    return relative


def _selector(value: Any, label: str) -> tuple[str, str]:
    raw = _text(value, label)
    path, separator, member = raw.partition("::")
    normalized = _test_path(path, label, exists=False)
    if separator:
        _need(bool(member.strip()), f"{label} selector suffix must be nonempty")
        _text(member, f"{label} selector suffix")
    return raw, normalized


def _string_list(value: Any, label: str, *, concrete: bool = False) -> list[str]:
    _need(isinstance(value, list) and value, f"{label} must be a nonempty list")
    _need(len(value) <= MAX_PATHS, f"{label} exceeds the bounded item limit")
    rows = [_text(item, label, concrete=concrete) for item in value]
    _need(len(rows) == len(set(rows)), f"{label} must not repeat values")
    return rows


def _manifest_ids(value: Iterable[str] | None) -> frozenset[str] | None:
    if value is None:
        return None
    _need(not isinstance(value, (str, bytes)), "check_ids must be an iterable of identifiers")
    try:
        rows = [_identifier(item, "check_ids entry") for item in value]
    except TypeError as exc:
        raise SdlcError("check_ids must be an iterable of identifiers") from exc
    _need(len(rows) == len(set(rows)), "check_ids must not repeat identifiers")
    return frozenset(rows)


def _check_id_list(
    value: Any,
    label: str,
    *,
    allowed: frozenset[str] | None,
) -> list[str]:
    _need(isinstance(value, list) and value, f"{label} must be a nonempty list")
    _need(len(value) <= MAX_CHECK_IDS, f"{label} exceeds the bounded item limit")
    rows = [_identifier(item, label) for item in value]
    _need(len(rows) == len(set(rows)), f"{label} must not repeat identifiers")
    if allowed is not None:
        unknown = [item for item in rows if item not in allowed]
        _need(not unknown, f"{label} names check IDs absent from the supplied manifest: {', '.join(unknown)}")
    return rows


def _coverage(value: Any, label: str) -> list[dict[str, str]]:
    _need(isinstance(value, list) and len(value) == len(_COVERAGE_SURFACES), f"{label} must name every coverage surface exactly once")
    by_surface: dict[str, dict[str, str]] = {}
    for index, row in enumerate(value):
        row_label = f"{label}[{index}]"
        _need(isinstance(row, Mapping) and set(row) == {"surface", "disposition", "reason"}, f"{row_label} has an unexpected schema")
        surface = row["surface"]
        _need(surface in _COVERAGE_SURFACES, f"{row_label}.surface is invalid")
        _need(surface not in by_surface, f"{label} must not repeat a coverage surface")
        disposition = row["disposition"]
        _need(disposition in _COVERAGE_DISPOSITIONS, f"{row_label}.disposition is invalid")
        by_surface[surface] = {
            "surface": surface,
            "disposition": disposition,
            "reason": _text(row["reason"], f"{row_label}.reason", concrete=True),
        }
    _need(set(by_surface) == set(_COVERAGE_SURFACES), f"{label} must name every coverage surface")
    return [by_surface[surface] for surface in _COVERAGE_SURFACES]


def _normal_plan_case(value: Any, label: str, *, allowed_checks: frozenset[str] | None) -> dict[str, Any]:
    expected = {
        "case_id",
        "contract_id",
        "requirement",
        "inputs",
        "expected_outcome",
        "test_selectors",
        "check_ids",
        "environment",
        "fixture",
    }
    _need(isinstance(value, Mapping) and set(value) == expected, f"{label} has an unexpected schema")
    inputs = _string_list(value["inputs"], f"{label}.inputs", concrete=True)
    requirement = _text(value["requirement"], f"{label}.requirement", concrete=True)
    outcome = _text(value["expected_outcome"], f"{label}.expected_outcome", concrete=True)
    comparable = " ".join(outcome.casefold().split())
    _need(comparable != " ".join(requirement.casefold().split()), f"{label}.expected_outcome must be independent of the requirement")
    _need(all(comparable != " ".join(item.casefold().split()) for item in inputs), f"{label}.expected_outcome must be independent of the inputs")
    selectors: list[str] = []
    paths: list[str] = []
    for index, item in enumerate(_string_list(value["test_selectors"], f"{label}.test_selectors")):
        selector, path = _selector(item, f"{label}.test_selectors[{index}]")
        selectors.append(selector)
        paths.append(path)
    _need(len(selectors) == len(set(selectors)), f"{label}.test_selectors must not repeat selectors")
    return {
        "case_id": _identifier(value["case_id"], f"{label}.case_id", _CASE_ID),
        "contract_id": _identifier(value["contract_id"], f"{label}.contract_id", _CONTRACT_ID),
        "requirement": requirement,
        "inputs": inputs,
        "expected_outcome": outcome,
        "test_selectors": selectors,
        "check_ids": _check_id_list(value["check_ids"], f"{label}.check_ids", allowed=allowed_checks),
        "environment": _text(value["environment"], f"{label}.environment", concrete=True),
        "fixture": _text(value["fixture"], f"{label}.fixture", concrete=True),
    }


def _required_ids(value: Iterable[str], label: str, pattern: re.Pattern[str]) -> set[str]:
    _need(not isinstance(value, (str, bytes)), f"{label} must be an iterable of identifiers")
    try:
        rows = [_identifier(item, label, pattern) for item in value]
    except TypeError as exc:
        raise SdlcError(f"{label} must be an iterable of identifiers") from exc
    _need(len(rows) == len(set(rows)), f"{label} must not repeat identifiers")
    return set(rows)


def validate_local_test_plan(
    value: Any,
    *,
    required_contract_ids: Iterable[str] = (),
    required_case_ids: Iterable[str] = (),
    check_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Normalize an explicit local-test plan before product code changes.

    ``check_ids`` is an optional caller-supplied current manifest.  Passing it
    validates selector references; omitting it intentionally does not pretend
    that a host claimed a future check exists or passed.
    """
    _need(isinstance(value, Mapping) and set(value) == {"cases", "coverage"}, "local_test_plan has an unexpected schema")
    _need(isinstance(value["cases"], list) and value["cases"], "local_test_plan.cases must be a nonempty list")
    _need(len(value["cases"]) <= MAX_CASES, "local_test_plan.cases exceeds the bounded limit")
    allowed_checks = _manifest_ids(check_ids)
    cases = [
        _normal_plan_case(row, f"local_test_plan.cases[{index}]", allowed_checks=allowed_checks)
        for index, row in enumerate(value["cases"])
    ]
    case_ids = [row["case_id"] for row in cases]
    _need(len(case_ids) == len(set(case_ids)), "local_test_plan case IDs must not duplicate")
    required_contracts = _required_ids(required_contract_ids, "required_contract_ids", _CONTRACT_ID)
    required_cases = _required_ids(required_case_ids, "required_case_ids", _CASE_ID)
    present_contracts = {row["contract_id"] for row in cases}
    present_cases = set(case_ids)
    missing_contracts = sorted(required_contracts - present_contracts)
    missing_cases = sorted(required_cases - present_cases)
    _need(not missing_contracts, f"local_test_plan is missing required contract IDs: {', '.join(missing_contracts)}")
    _need(not missing_cases, f"local_test_plan is missing required case IDs: {', '.join(missing_cases)}")
    return {"cases": cases, "coverage": _coverage(value["coverage"], "local_test_plan.coverage")}


def test_plan_references(value: Any) -> dict[str, Any]:
    """Return stable case, contract, check, and intended-path references."""
    plan = validate_local_test_plan(value)
    check_ids: list[str] = []
    paths: list[str] = []
    outcomes: dict[str, list[str]] = {}
    for row in plan["cases"]:
        for check_id in row["check_ids"]:
            if check_id not in check_ids:
                check_ids.append(check_id)
        for selector in row["test_selectors"]:
            _raw, path = _selector(selector, "normalized test selector")
            if path not in paths:
                paths.append(path)
        outcomes.setdefault(row["contract_id"], []).append(row["expected_outcome"])
    return {
        "case_ids": [row["case_id"] for row in plan["cases"]],
        "contract_ids": list(dict.fromkeys(row["contract_id"] for row in plan["cases"])),
        "contract_expected_outcomes": outcomes,
        "check_ids": check_ids,
        "test_paths": paths,
    }


def _oracle(value: Any, label: str, plan_case: Mapping[str, Any]) -> dict[str, str]:
    _need(isinstance(value, Mapping) and "decision" in value, f"{label} has an unexpected schema")
    decision = value["decision"]
    if decision == "unchanged":
        _need(set(value) == {"decision"}, f"{label} unchanged has unexpected detail fields")
        return {"decision": "unchanged"}
    _need(decision == "corrected", f"{label}.decision is invalid")
    expected = {
        "decision",
        "old_expected_outcome",
        "new_expected_outcome",
        "basis",
        "preserved_coverage",
    }
    _need(set(value) == expected, f"{label} corrected has an unexpected schema")
    old = _text(value["old_expected_outcome"], f"{label}.old_expected_outcome", concrete=True)
    new = _text(value["new_expected_outcome"], f"{label}.new_expected_outcome", concrete=True)
    _need(old == plan_case["expected_outcome"], f"{label}.old_expected_outcome must match the planned independent outcome")
    _need(new != old, f"{label}.new_expected_outcome must actually change the oracle")
    _need(new != plan_case["requirement"], f"{label}.new_expected_outcome must remain independent of the requirement")
    _need(new not in plan_case["inputs"], f"{label}.new_expected_outcome must remain independent of the inputs")
    return {
        "decision": "corrected",
        "old_expected_outcome": old,
        "new_expected_outcome": new,
        "basis": _text(value["basis"], f"{label}.basis", concrete=True),
        "preserved_coverage": _text(value["preserved_coverage"], f"{label}.preserved_coverage", concrete=True),
    }


def _normal_refinement_case(
    value: Any,
    label: str,
    *,
    plan_case: Mapping[str, Any],
    worktree: Path,
    allowed_checks: frozenset[str] | None,
) -> dict[str, Any]:
    base = {"case_id", "disposition", "test_paths", "check_ids", "coverage", "oracle"}
    _need(isinstance(value, Mapping) and base.issubset(value), f"{label} has an unexpected schema")
    disposition = value["disposition"]
    _need(disposition in _REFINEMENT_DISPOSITIONS, f"{label}.disposition is invalid")
    expected = base | ({"adequacy_reason"} if disposition == "reused" else set())
    _need(set(value) == expected, f"{label} has an unexpected schema")
    paths = [
        _test_path(item, f"{label}.test_paths[{index}]", exists=True, worktree=worktree)
        for index, item in enumerate(_string_list(value["test_paths"], f"{label}.test_paths"))
    ]
    _need(len(paths) == len(set(paths)), f"{label}.test_paths must not repeat paths")
    normalized: dict[str, Any] = {
        "case_id": _identifier(value["case_id"], f"{label}.case_id", _CASE_ID),
        "disposition": disposition,
        "test_paths": paths,
        "check_ids": _check_id_list(value["check_ids"], f"{label}.check_ids", allowed=allowed_checks),
        "coverage": _text(value["coverage"], f"{label}.coverage", concrete=True),
        "oracle": _oracle(value["oracle"], f"{label}.oracle", plan_case),
    }
    if disposition == "reused":
        normalized["adequacy_reason"] = _text(value["adequacy_reason"], f"{label}.adequacy_reason", concrete=True)
    return normalized


def validate_test_refinement(
    value: Any,
    plan: Any,
    worktree: Path,
    *,
    check_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Validate post-code test authoring/refinement against the accepted plan."""
    worktree = _worktree(worktree)
    accepted_plan = validate_local_test_plan(plan)
    by_case = {row["case_id"]: row for row in accepted_plan["cases"]}
    _need(isinstance(value, Mapping) and set(value) == {"cases"}, "test_refinement has an unexpected schema")
    _need(isinstance(value["cases"], list) and value["cases"], "test_refinement.cases must be a nonempty list")
    _need(len(value["cases"]) <= MAX_CASES, "test_refinement.cases exceeds the bounded limit")
    allowed_checks = _manifest_ids(check_ids)
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(value["cases"]):
        label = f"test_refinement.cases[{index}]"
        _need(isinstance(raw, Mapping), f"{label} must be an object")
        case_id = _identifier(raw.get("case_id"), f"{label}.case_id", _CASE_ID)
        _need(case_id in by_case, f"{label}.case_id is not a planned case")
        _need(case_id not in seen, "test_refinement case IDs must not duplicate")
        seen.add(case_id)
        normalized.append(
            _normal_refinement_case(
                raw,
                label,
                plan_case=by_case[case_id],
                worktree=worktree,
                allowed_checks=allowed_checks,
            )
        )
    missing = sorted(set(by_case) - seen)
    _need(not missing, f"test_refinement must cover every planned case: {', '.join(missing)}")
    return {"cases": normalized}


def test_refinement_references(value: Any, plan: Any, worktree: Path) -> dict[str, Any]:
    """Return actual test paths/check IDs after strict post-code validation."""
    refinement = validate_test_refinement(value, plan, worktree)
    check_ids: list[str] = []
    paths: list[str] = []
    for row in refinement["cases"]:
        for check_id in row["check_ids"]:
            if check_id not in check_ids:
                check_ids.append(check_id)
        for path in row["test_paths"]:
            if path not in paths:
                paths.append(path)
    return {"case_ids": [row["case_id"] for row in refinement["cases"]], "check_ids": check_ids, "test_paths": paths}


def _argv(value: Any, label: str) -> list[str]:
    _need(isinstance(value, list) and value, f"{label} must be a nonempty argv list")
    _need(len(value) <= MAX_ARGV, f"{label} exceeds the bounded item limit")
    rows = [_text(item, f"{label}[{index}]") for index, item in enumerate(value)]
    _need(
        not any(
            part.startswith("<")
            or "replace-with" in part.casefold()
            or "replace_with" in part.casefold()
            for part in rows
        ),
        f"{label} must not contain placeholder arguments",
    )
    return rows


def _binding_case_ids(value: Any, label: str) -> list[str]:
    _need(isinstance(value, list) and value, f"{label} must be a nonempty list")
    _need(len(value) <= MAX_CASES, f"{label} exceeds the bounded item limit")
    rows = [_identifier(item, label, _CASE_ID) for item in value]
    _need(len(rows) == len(set(rows)), f"{label} must not repeat case IDs")
    return rows


def _binding_selectors(value: Any, label: str) -> tuple[list[str], dict[str, str]]:
    _need(isinstance(value, list) and value, f"{label} must be a nonempty list")
    _need(len(value) <= MAX_PATHS, f"{label} exceeds the bounded item limit")
    selectors: list[str] = []
    paths: dict[str, str] = {}
    for index, raw in enumerate(value):
        selector, path = _selector(raw, f"{label}[{index}]")
        _need(selector not in selectors, f"{label} must not repeat selectors")
        selectors.append(selector)
        paths[selector] = path
    return selectors, paths


def _selection(
    value: Any,
    label: str,
    worktree: Path,
    selectors: list[str],
    selector_paths: Mapping[str, str],
) -> dict[str, str]:
    _need(isinstance(value, Mapping) and "mode" in value, f"{label} has an unexpected schema")
    mode = value["mode"]
    _need(mode in ("direct", "suite"), f"{label}.mode is invalid")
    expected = {"mode", "evidence"} | ({"evidence_path"} if mode == "suite" else set())
    _need(set(value) == expected, f"{label} has an unexpected schema")
    normalized = {
        "mode": mode,
        "evidence": _text(value["evidence"], f"{label}.evidence", concrete=True),
    }
    if mode == "suite":
        evidence_path = _existing_file(worktree, value["evidence_path"], f"{label}.evidence_path")
        evidence_body = _read_utf8(worktree, evidence_path, f"{label}.evidence_path")
        _need(
            all(selector in evidence_body or selector_paths[selector] in evidence_body for selector in selectors),
            f"{label}.evidence_path must identify every selected path or selector",
        )
        normalized["evidence_path"] = evidence_path
    return normalized


def _manifest_checks(manifest: Any) -> dict[str, dict[str, Any]] | None:
    """Read only the current manifest fields needed for command identity."""
    if manifest is None:
        return None
    _need(isinstance(manifest, Mapping), "test_bindings manifest must be an object")
    rows = manifest.get("checks")
    _need(isinstance(rows, list) and rows, "test_bindings manifest.checks must be a nonempty list")
    result: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(rows):
        label = f"test_bindings manifest.checks[{index}]"
        _need(isinstance(raw, Mapping), f"{label} must be an object")
        _need({"id", "kind", "argv"}.issubset(raw), f"{label} is missing id, kind, or argv")
        ident = _identifier(raw["id"], f"{label}.id")
        _need(ident not in result, "test_bindings manifest must not repeat check IDs")
        kind = raw["kind"]
        _need(kind in ("lint", "test"), f"{label}.kind must be lint or test")
        result[ident] = {"kind": kind, "argv": _argv(raw["argv"], f"{label}.argv")}
    return result


def _refinement_plan_bindings(plan: Mapping[str, Any], refinement: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    planned = {row["case_id"]: row for row in plan["cases"]}
    authored = {row["case_id"]: row for row in refinement["cases"]}
    _need(set(planned) == set(authored), "test_bindings requires every planned case to have authored test evidence")
    for case_id, plan_case in planned.items():
        refined_case = authored[case_id]
        _need(
            set(plan_case["check_ids"]) == set(refined_case["check_ids"]),
            f"test_bindings {case_id} must retain the planned check IDs",
        )
        planned_paths = {_selector(selector, f"test_bindings {case_id} selector")[1] for selector in plan_case["test_selectors"]}
        _need(
            planned_paths == set(refined_case["test_paths"]),
            f"test_bindings {case_id} must map every planned selector to its authored test path",
        )
    return planned, authored


def validate_test_bindings(
    value: Any,
    plan: Any,
    refinement: Any,
    worktree: Path,
    *,
    manifest: Any = None,
) -> dict[str, Any]:
    """Bind planned/authored local test cases to exact test-command argv.

    Without ``manifest`` this validates a pre-verify binding record only.  A
    caller must provide the current manifest at verify time to establish that
    each ID is still a test check with the exact recorded argv.  This validates
    command identity and mapping, not whether a test assertion is semantically
    adequate or whether the command passed.
    """
    worktree = _worktree(worktree)
    accepted_plan = validate_local_test_plan(plan)
    accepted_refinement = validate_test_refinement(refinement, accepted_plan, worktree)
    planned, authored = _refinement_plan_bindings(accepted_plan, accepted_refinement)
    _need(isinstance(value, Mapping) and set(value) == {"bindings"}, "test_bindings has an unexpected schema")
    rows = value["bindings"]
    _need(isinstance(rows, list) and rows, "test_bindings.bindings must be a nonempty list")
    _need(len(rows) <= MAX_CHECK_IDS, "test_bindings.bindings exceeds the bounded limit")
    manifest_checks = _manifest_checks(manifest)
    expected_pairs = {
        (case_id, check_id)
        for case_id, row in authored.items()
        for check_id in row["check_ids"]
    }
    expected_selector_pairs = {
        (case_id, selector)
        for case_id, row in planned.items()
        for selector in row["test_selectors"]
    }
    seen_checks: set[str] = set()
    bound_pairs: set[tuple[str, str]] = set()
    bound_selector_pairs: set[tuple[str, str]] = set()
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(rows):
        label = f"test_bindings.bindings[{index}]"
        expected = {"check_id", "argv", "case_ids", "selectors", "selection"}
        _need(isinstance(raw, Mapping) and set(raw) == expected, f"{label} has an unexpected schema")
        check_id = _identifier(raw["check_id"], f"{label}.check_id")
        _need(check_id not in seen_checks, "test_bindings must not repeat a check ID")
        seen_checks.add(check_id)
        argv = _argv(raw["argv"], f"{label}.argv")
        case_ids = _binding_case_ids(raw["case_ids"], f"{label}.case_ids")
        _need(all(case_id in authored for case_id in case_ids), f"{label}.case_ids names an unplanned or unauthored case")
        selectors, selector_paths = _binding_selectors(raw["selectors"], f"{label}.selectors")
        selection = _selection(
            raw["selection"],
            f"{label}.selection",
            worktree,
            selectors,
            selector_paths,
        )
        if manifest_checks is not None:
            current = manifest_checks.get(check_id)
            _need(current is not None, f"{label}.check_id is absent from the current manifest")
            _need(current["kind"] == "test", f"{label}.check_id must name a test check in the current manifest")
            _need(current["argv"] == argv, f"{label}.argv must exactly match the current manifest command")
        for case_id in case_ids:
            _need(check_id in authored[case_id]["check_ids"], f"{label}.check_id is not declared for {case_id}")
            pair = (case_id, check_id)
            _need(pair not in bound_pairs, "test_bindings must not repeat a case/check mapping")
            bound_pairs.add(pair)
        for selector in selectors:
            owners = [case_id for case_id in case_ids if selector in planned[case_id]["test_selectors"]]
            _need(owners, f"{label}.selectors names a selector not planned for its declared cases")
            for case_id in owners:
                _need(selector_paths[selector] in authored[case_id]["test_paths"], f"{label}.selectors path is not an authored test path for {case_id}")
                bound_selector_pairs.add((case_id, selector))
        if selection["mode"] == "direct":
            _need(
                all(selector in argv or selector_paths[selector] in argv for selector in selectors),
                f"{label} direct selection must name every selected path or selector in argv",
            )
        normalized.append(
            {
                "check_id": check_id,
                "argv": argv,
                "case_ids": case_ids,
                "selectors": selectors,
                "selection": selection,
            }
        )
    missing_pairs = sorted(f"{case_id}/{check_id}" for case_id, check_id in expected_pairs - bound_pairs)
    missing_selectors = sorted(f"{case_id}/{selector}" for case_id, selector in expected_selector_pairs - bound_selector_pairs)
    _need(not missing_pairs, "test_bindings must cover every authored case/check mapping: " + ", ".join(missing_pairs))
    _need(not missing_selectors, "test_bindings must cover every planned selector: " + ", ".join(missing_selectors))
    return {"bindings": normalized}


def test_binding_references(
    value: Any,
    plan: Any,
    refinement: Any,
    worktree: Path,
    *,
    manifest: Any = None,
) -> dict[str, Any]:
    """Expose current command/evidence references after strict binding validation."""
    bindings = validate_test_bindings(value, plan, refinement, worktree, manifest=manifest)
    selectors: list[str] = []
    paths: list[str] = []
    suite_evidence_paths: list[str] = []
    argv_by_check: dict[str, list[str]] = {}
    for row in bindings["bindings"]:
        argv_by_check[row["check_id"]] = list(row["argv"])
        for selector in row["selectors"]:
            if selector not in selectors:
                selectors.append(selector)
            _normalized_selector, path = _selector(selector, "normalized test binding selector")
            if path not in paths:
                paths.append(path)
        if row["selection"]["mode"] == "suite":
            evidence_path = row["selection"]["evidence_path"]
            if evidence_path not in suite_evidence_paths:
                suite_evidence_paths.append(evidence_path)
    return {
        "check_ids": [row["check_id"] for row in bindings["bindings"]],
        "case_ids": list(dict.fromkeys(case_id for row in bindings["bindings"] for case_id in row["case_ids"])),
        "selectors": selectors,
        "test_paths": paths,
        "suite_evidence_paths": suite_evidence_paths,
        "argv_by_check": argv_by_check,
    }


def _read_utf8(worktree: Path, relative: str, label: str) -> str:
    try:
        text = (worktree / relative).read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SdlcError(f"{label} must be UTF-8 text") from exc
    _need(bool(text.strip()), f"{label} must not be empty")
    return text


_BLOCK_DESCRIPTION_STYLES = frozenset(("|", ">", "|-", ">-", "|+", ">+"))


def _without_yaml_comment(raw: str) -> str:
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


def _frontmatter_field(lines: list[str], name: str) -> tuple[int, str]:
    prefix = name + ":"
    matches = [
        (index, line[len(prefix):].strip())
        for index, line in enumerate(lines)
        if not line.startswith((" ", "\t")) and line.startswith(prefix)
    ]
    _need(len(matches) == 1, f"skill_validation entrypoint requires meaningful {name}")
    return matches[0]


def _meaningful_frontmatter_scalar(raw: str, name: str) -> None:
    candidate = _without_yaml_comment(raw).strip()
    _need(
        bool(candidate)
        and candidate.casefold() not in ("null", "~")
        and not candidate.startswith(("[", "{"))
        and candidate not in _BLOCK_DESCRIPTION_STYLES
        and not candidate.startswith(("- ", "? ")),
        f"skill_validation entrypoint requires meaningful {name}",
    )
    if candidate.startswith(("'", '"')):
        quote = candidate[0]
        _need(
            len(candidate) >= 2 and candidate.endswith(quote) and bool(candidate[1:-1].strip()),
            f"skill_validation entrypoint requires meaningful {name}",
        )


def _nonempty_frontmatter_block(lines: list[str], start: int) -> None:
    block: list[str] = []
    for line in lines[start + 1:]:
        if line and not line.startswith((" ", "\t")):
            break
        block.append(line)
    _need(
        any(line.strip() for line in block),
        "skill_validation entrypoint requires meaningful description",
    )


def _frontmatter_skill(worktree: Path, relative: str) -> None:
    body = _read_utf8(worktree, relative, "skill_validation entrypoint")
    lines = body.splitlines()
    _need(lines and lines[0] == "---", "skill_validation entrypoint requires frontmatter")
    try:
        close = lines.index("---", 1)
    except ValueError as exc:
        raise SdlcError("skill_validation entrypoint frontmatter is unterminated") from exc
    _need(any(line.strip() for line in lines[close + 1:]), "skill_validation entrypoint body must not be empty")
    frontmatter = lines[1:close]
    _name_index, name = _frontmatter_field(frontmatter, "name")
    _meaningful_frontmatter_scalar(name, "name")
    description_index, description = _frontmatter_field(frontmatter, "description")
    if _without_yaml_comment(description).strip() in _BLOCK_DESCRIPTION_STYLES:
        _nonempty_frontmatter_block(frontmatter, description_index)
    else:
        _meaningful_frontmatter_scalar(description, "description")


def _index_names_entrypoint(worktree: Path, index: str, entrypoint: str) -> bool:
    body = _read_utf8(worktree, index, "skill_validation index")
    if entrypoint in body:
        return True
    for raw_target in _MARKDOWN_TARGET.findall(body):
        target = raw_target.strip("<>").split("#", 1)[0]
        if not target or "://" in target:
            continue
        candidate = Path(index).parent / target
        normalized = os.path.normpath(os.fspath(candidate)).replace(os.sep, "/")
        if normalized == entrypoint:
            return True
    return False


def validate_skill_validation(
    value: Any,
    worktree: Path,
    *,
    check_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Validate a conditional repo-local skill outcome without installing it."""
    worktree = _worktree(worktree)
    _need(isinstance(value, Mapping) and "decision" in value and "rationale" in value, "skill_validation has an unexpected schema")
    decision = value["decision"]
    _need(decision in _SKILL_DECISIONS, "skill_validation.decision is invalid")
    rationale = _text(value["rationale"], "skill_validation.rationale", concrete=True)
    if decision == "not-needed":
        _need(set(value) == {"decision", "rationale"}, "skill_validation not-needed has unexpected detail fields")
        return {"decision": decision, "rationale": rationale}
    expected = {
        "decision",
        "rationale",
        "entrypoint",
        "index",
        "executable_examples",
        "failure_recovery",
        "host_limitations",
    }
    _need(set(value) == expected, "skill_validation has an unexpected schema")
    entrypoint = _existing_file(worktree, value["entrypoint"], "skill_validation.entrypoint")
    _need(Path(entrypoint).name == "SKILL.md", "skill_validation.entrypoint must name SKILL.md")
    _need(str(Path(entrypoint).parent) not in ("", "."), "skill_validation.entrypoint must be inside a local skill directory")
    index = _existing_file(worktree, value["index"], "skill_validation.index")
    _need(index != entrypoint, "skill_validation.index must be distinct from SKILL.md")
    _frontmatter_skill(worktree, entrypoint)
    _need(_index_names_entrypoint(worktree, index, entrypoint), "skill_validation.index must expose the local SKILL.md entrypoint")
    _need(isinstance(value["executable_examples"], list) and value["executable_examples"], "skill_validation.executable_examples must be a nonempty list")
    _need(len(value["executable_examples"]) <= MAX_PATHS, "skill_validation.executable_examples exceeds the bounded limit")
    allowed_checks = _manifest_ids(check_ids)
    examples: list[dict[str, str]] = []
    paths: set[str] = set()
    example_checks: set[str] = set()
    for position, row in enumerate(value["executable_examples"]):
        label = f"skill_validation.executable_examples[{position}]"
        _need(isinstance(row, Mapping) and set(row) == {"path", "check_id", "purpose"}, f"{label} has an unexpected schema")
        path = _existing_file(worktree, row["path"], f"{label}.path")
        _need(path not in paths, "skill_validation.executable_examples must not repeat paths")
        paths.add(path)
        check_id = _identifier(row["check_id"], f"{label}.check_id")
        _need(check_id not in example_checks, "skill_validation.executable_examples must not repeat check IDs")
        if allowed_checks is not None:
            _need(check_id in allowed_checks, f"{label}.check_id is absent from the supplied manifest")
        example_checks.add(check_id)
        examples.append({"path": path, "check_id": check_id, "purpose": _text(row["purpose"], f"{label}.purpose", concrete=True)})
    return {
        "decision": decision,
        "rationale": rationale,
        "entrypoint": entrypoint,
        "index": index,
        "executable_examples": examples,
        "failure_recovery": _text(value["failure_recovery"], "skill_validation.failure_recovery", concrete=True),
        "host_limitations": _text(value["host_limitations"], "skill_validation.host_limitations", concrete=True),
    }


def skill_validation_references(value: Any, worktree: Path) -> dict[str, list[str]]:
    """Return actual local paths and selected check IDs for a skill outcome."""
    result = validate_skill_validation(value, worktree)
    if result["decision"] == "not-needed":
        return {"paths": [], "check_ids": []}
    return {
        "paths": [result["entrypoint"], result["index"], *[row["path"] for row in result["executable_examples"]]],
        "check_ids": [row["check_id"] for row in result["executable_examples"]],
    }


_NODE_ROWS = (
    ("N01", 1, "inspect_context", "Inspect Git, code, docs and environment", "Establish current repository and environment evidence", False, False),
    ("N02", 2, "research_spec", "Draft research, behavior and specification", "Draft accepted behavior and requirement candidates", False, False),
    ("N03", 3, "improve_research_spec", "IMPROVE research and specification", "Converge the research and specification bundle", True, False),
    ("N04", 4, "global_test_plan", "Plan global system tests and release checks", "Make cross-boundary cases and release checks explicit", False, False),
    ("N05", 5, "improve_global_test_plan", "IMPROVE the global test plan", "Converge the global system-test plan", True, False),
    ("N06", 6, "delivery_dag", "Build delivery DAG and step contracts", "Bind producers, consumers, prerequisites, and contracts", False, False),
    ("N07", 7, "improve_delivery_plan", "IMPROVE the delivery plan", "Converge delivery ordering and step contracts", True, False),
    ("N08", 8, "select_work_item", "Prepare and select a ready work item", "Bind one eligible work item and its inputs", False, False),
    ("N09", 9, "local_implementation_plan", "Draft the local implementation plan", "Define scoped edits and boundaries before code changes", False, False),
    ("N10", 10, "local_test_plan", "Plan local cases and expected outcomes", "Define local cases, fixtures, coverage and selected checks", False, False),
    ("N11", 11, "improve_local_plan", "IMPROVE the local plan and test plan", "Converge the coupled implementation and local-test plan", True, False),
    ("N12", 12, "baseline_checks", "Run required baseline checks", "Observe prerequisites before dependent changes", False, False),
    ("N13", 13, "implement", "Implement the scoped work", "Produce the authorized candidate", False, False),
    ("N14", 14, "post_code_test_refinement", "Refine cases from actual code findings", "Make learned boundaries and failure cases explicit", False, False),
    ("N15", 15, "author_local_tests", "Author or refine executable local tests", "Map planned cases to concrete executable tests", False, False),
    ("N16", 16, "update_documentation", "Update README and interface documentation", "Keep observable interfaces and documentation current", False, False),
    ("N17", 17, "skill_needed", "Reusable skill work needed?", "Decide whether a reusable repo-local procedure is warranted", False, True),
    ("N18", 18, "build_skill", "Create or update the repo-local skill", "Produce a needed reusable local skill", False, False),
    ("N19", 19, "improve_skill", "IMPROVE skill and validate its use", "Converge skill guidance and validate actual use", True, False),
    ("N20", 20, "local_checks", "Run lint, build, type and local checks", "Execute selected current local checks", False, False),
    ("N21", 21, "improve_product_bundle", "IMPROVE the code, tests and docs together", "Converge the coupled product bundle", True, False),
    ("N22", 22, "fresh_step_evidence", "Fresh final step checks and Done evidence", "Bind completion to fresh current evidence", False, False),
    ("N23", 23, "broader_reassessment", "Capture discoveries and reassess broader work", "Route learned broader obligations to their owners", False, False),
    ("N24", 24, "improve_pending_plan", "IMPROVE the revised pending plan", "Converge compatible pending-plan revisions", True, False),
    ("N25", 25, "integrate_work_item", "Integrate the verified work item", "Release verified work to its consumers", False, False),
    ("N26", 26, "more_work_items", "More required work items?", "Decide whether required work remains", False, True),
    ("N27", 27, "author_global_tests", "Author global system tests and fixtures", "Implement planned system tests and fixtures", False, False),
    ("N28", 28, "improve_system_tests", "IMPROVE the system-test implementation", "Converge the system-test suite", True, False),
    ("N29", 29, "pre_deployment_tests", "Execute pre-deployment integration and journey tests", "Observe assembled product behavior before release", False, False),
    ("N30", 30, "improve_integrated_product", "IMPROVE the integrated product", "Converge scoped whole-product corrections", True, False),
    ("N31", 31, "release_checks", "Run final whole-product acceptance and release checks", "Establish current acceptance evidence", False, False),
    ("N32", 32, "publish", "Publish the exact checked candidate", "Perform the authorized side-effecting release", False, True),
    ("N33", 33, "post_deployment_tests", "Execute post-deployment system tests and smoke checks", "Observe the actual deployed target", False, False),
    ("N34", 34, "handoff_evidence", "Assemble handoff and operational evidence", "Assemble accurate delivery and recovery evidence", False, False),
    ("N35", 35, "improve_handoff", "IMPROVE handoff accuracy and completeness", "Converge handoff claims and limitations", True, False),
    ("N36", 36, "terminal_evidence", "Validate terminal evidence and finish", "Accept only current terminal evidence", False, False),
)
_CATALOG_KEYS = frozenset(("id", "number", "stage", "label", "responsibility", "improve", "conditional"))
_CANONICAL_CATALOG = tuple(
    MappingProxyType(
        {
            "id": ident,
            "number": number,
            "stage": stage,
            "label": label,
            "responsibility": responsibility,
            "improve": improve,
            "conditional": conditional,
        }
    )
    for ident, number, stage, label, responsibility, improve, conditional in _NODE_ROWS
)
SDLC_NODE_CATALOG = _CANONICAL_CATALOG
SDLC_STAGE_RESPONSIBILITIES = MappingProxyType(
    {
        row["stage"]: MappingProxyType(
            {
                "node_id": row["id"],
                "stage": row["stage"],
                "label": row["label"],
                "responsibility": row["responsibility"],
                "improve": row["improve"],
                "conditional": row["conditional"],
            }
        )
        for row in _CANONICAL_CATALOG
    }
)

# The flat catalog describes SDLC outputs; packets retain the existing narrower
# protocol-stage names while the managed bridge is introduced.  These aliases
# let packet/report rendering name the corresponding SDLC responsibility
# without changing authoritative cursor stage names.
_PACKET_STAGE_ALIASES = MappingProxyType(
    {
        "schedule": "select_work_item",
        "preflight": "inspect_context",
        "approach": "research_spec",
        "survey": "research_spec",
        "sequence": "delivery_dag",
        "prepare": "select_work_item",
        "research": "research_spec",
        "research-review": "improve_research_spec",
        "research-plan": "improve_research_spec",
        "research-apply": "improve_research_spec",
        "research-verify": "improve_research_spec",
        "research-commit": "improve_research_spec",
        "research-finalize": "improve_research_spec",
        "behavior": "research_spec",
        "behavior-review": "improve_research_spec",
        "behavior-plan": "improve_research_spec",
        "behavior-apply": "improve_research_spec",
        "behavior-verify": "improve_research_spec",
        "behavior-commit": "improve_research_spec",
        "behavior-finalize": "improve_research_spec",
        "spec": "research_spec",
        "spec-review": "improve_research_spec",
        "spec-plan": "improve_research_spec",
        "spec-apply": "improve_research_spec",
        "spec-verify": "improve_research_spec",
        "spec-commit": "improve_research_spec",
        "spec-finalize": "improve_research_spec",
        "objective-review": "improve_delivery_plan",
        "objective-plan": "improve_delivery_plan",
        "objective-apply": "improve_delivery_plan",
        "objective-verify": "improve_delivery_plan",
        "objective-commit": "improve_delivery_plan",
        "objective-finalize": "improve_delivery_plan",
        "step-plan": "local_implementation_plan",
        "step-plan-review": "improve_local_plan",
        "step-plan-disposition": "improve_local_plan",
        "step-plan-revise": "improve_local_plan",
        "step-plan-verify": "improve_local_plan",
        "step-plan-finalize": "improve_local_plan",
        "step-plan-commit": "improve_local_plan",
        "improve-plan": "improve_local_plan",
        "improve-plan-verify": "improve_local_plan",
        "implement": "implement",
        "test-refine": "post_code_test_refinement",
        "test-author": "author_local_tests",
        "iteration-document": "update_documentation",
        "skill-validate": "improve_skill",
        "verify": "local_checks",
        "review": "improve_product_bundle",
        "improve-apply": "improve_product_bundle",
        "carry-forward": "improve_product_bundle",
        "commit": "improve_product_bundle",
        "final-verify": "fresh_step_evidence",
        "post-inner": "broader_reassessment",
        "merge": "integrate_work_item",
        "coverage": "improve_integrated_product",
        "quality": "release_checks",
        "publish": "publish",
        "handoff": "handoff_evidence",
        "done": "terminal_evidence",
        "halted": "terminal_evidence",
    }
)


def sdlc_node_catalog() -> list[dict[str, Any]]:
    """Return a mutable rendering-safe copy of the stable 36-node catalog."""
    return [dict(row) for row in _CANONICAL_CATALOG]


def validate_sdlc_node_catalog(value: Any) -> list[dict[str, Any]]:
    """Fail closed if a rendered/catalog copy no longer represents this SDLC."""
    _need(isinstance(value, (list, tuple)) and len(value) == 36, "SDLC catalog must contain exactly 36 nodes")
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(value):
        label = f"SDLC catalog node {index}"
        _need(isinstance(row, Mapping) and set(row) == _CATALOG_KEYS, f"{label} has an unexpected schema")
        _need(type(row["number"]) is int and row["number"] == index + 1, f"{label}.number must match its stable position")
        _need(type(row["improve"]) is bool and type(row["conditional"]) is bool, f"{label} flags must be boolean")
        normalized_row = {
            "id": _text(row["id"], f"{label}.id"),
            "number": row["number"],
            "stage": _text(row["stage"], f"{label}.stage"),
            "label": _text(row["label"], f"{label}.label"),
            "responsibility": _text(row["responsibility"], f"{label}.responsibility"),
            "improve": row["improve"],
            "conditional": row["conditional"],
        }
        _need(normalized_row == dict(_CANONICAL_CATALOG[index]), f"{label} differs from the stable SDLC catalog")
        normalized.append(normalized_row)
    return normalized


def stage_responsibility(stage_or_node: Any, *, base_stage: Any = None, profile: Any = None) -> dict[str, Any]:
    """Return the packet/report responsibility for a stable stage or N-ID."""
    raw_stage = _text(stage_or_node, "SDLC stage")
    if raw_stage == "managed-improve":
        parked_profiles = {
            "research": "research-review",
            "behavior": "behavior-review",
            "spec": "spec-review",
            "objective": "objective-review",
            "step-plan": "step-plan-review",
            "product": "review",
        }
        _need(isinstance(profile, str) and profile in parked_profiles,
              "Parked managed Improve requires a known profile")
        raw_stage = parked_profiles[profile]
    key = raw_stage
    if raw_stage.startswith("objective-") and base_stage is not None:
        base = _text(base_stage, "SDLC objective base stage")
        key = _PACKET_STAGE_ALIASES.get(base, base)
    else:
        key = _PACKET_STAGE_ALIASES.get(key, key)
    if key in SDLC_STAGE_RESPONSIBILITIES:
        return dict(SDLC_STAGE_RESPONSIBILITIES[key])
    for row in _CANONICAL_CATALOG:
        if key == row["id"]:
            return {
                "node_id": row["id"],
                "stage": row["stage"],
                "label": row["label"],
                "responsibility": row["responsibility"],
                "improve": row["improve"],
                "conditional": row["conditional"],
            }
    raise SdlcError("SDLC stage is not in the stable catalog")


__all__ = (
    "SDLC_NODE_CATALOG",
    "SDLC_STAGE_RESPONSIBILITIES",
    "SdlcError",
    "sdlc_node_catalog",
    "skill_validation_references",
    "stage_responsibility",
    "test_binding_references",
    "test_plan_references",
    "test_refinement_references",
    "validate_local_test_plan",
    "validate_sdlc_node_catalog",
    "validate_skill_validation",
    "validate_test_bindings",
    "validate_test_refinement",
)
