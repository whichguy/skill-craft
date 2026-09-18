"""Named, bounded trial selections for the ShipLoop live E2E harness.

Suite files select literal scenario prompts; they do not alter or supplement
those prompts.  A ``partial`` suite is an observed SDLC prefix and therefore
cannot claim a completed product.  A ``full`` suite has no stop boundary and
keeps every declared predecessor in suite order.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
SCENARIOS_PATH = HERE / "scenarios.json"
SUITES_PATH = HERE / "suites.json"

# Keep this set equal to ``run.PARTIAL_STAGES``.  A partial capture stops only
# after an accepted prelude stage, before the navigator can enter an ambiguous
# per-work-item inner loop.
STOP_AFTER_STAGES = frozenset((
    "intake", "discovery", "research", "research-improve", "spec",
    "spec-improve", "test-strategy", "plan", "plan-improve",
))
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class SuiteError(ValueError):
    """A suite cannot safely be run against the scenario catalog."""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SuiteError(f"cannot read suite input: {path}") from exc


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SuiteError(f"{label} must be a nonempty string")
    return value


def _slug(value: Any, label: str) -> str:
    value = _nonempty_string(value, label)
    if not _SLUG.fullmatch(value):
        raise SuiteError(f"{label} must be a lowercase hyphenated slug")
    return value


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SuiteError(f"{label} must be a positive integer")
    return value


def load_scenario_families(path: Path | str = SCENARIOS_PATH) -> list[dict[str, Any]]:
    """Load the lightweight part of the scenario catalog needed for suites."""
    catalog = _read_json(Path(path))
    if not isinstance(catalog, Mapping) or catalog.get("schema_version") != 1:
        raise SuiteError("unsupported scenario catalog")
    families = catalog.get("scenarios")
    if not isinstance(families, list):
        raise SuiteError("scenario catalog must contain a scenarios list")
    return deepcopy(families)


def scenario_steps(families: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return uniquely identified scenario steps and validate their links."""
    steps: dict[str, dict[str, Any]] = {}
    for family_index, family in enumerate(families):
        if not isinstance(family, Mapping):
            raise SuiteError(f"scenario family {family_index} must be an object")
        family_steps = family.get("steps")
        if not isinstance(family_steps, list):
            raise SuiteError(f"scenario family {family_index} must contain steps")
        for step_index, raw_step in enumerate(family_steps):
            if not isinstance(raw_step, Mapping):
                raise SuiteError(f"scenario step {family_index}:{step_index} must be an object")
            step = deepcopy(dict(raw_step))
            step_id = _nonempty_string(step.get("id"), "scenario step id")
            if step_id in steps:
                raise SuiteError(f"duplicate scenario step: {step_id}")
            _nonempty_string(step.get("kind"), f"scenario {step_id} kind")
            _nonempty_string(step.get("prompt"), f"scenario {step_id} prompt")
            dependency = step.get("depends_on")
            if dependency is not None:
                _nonempty_string(dependency, f"scenario {step_id} depends_on")
            steps[step_id] = step
    for step_id, step in steps.items():
        dependency = step.get("depends_on")
        if dependency is not None and dependency not in steps:
            raise SuiteError(f"scenario {step_id} depends on unknown step: {dependency}")
    return steps


def _expected_dependencies(step: Mapping[str, Any]) -> list[str]:
    dependency = step.get("depends_on")
    return [] if dependency is None else [dependency]


def validate_suites(
    document: Mapping[str, Any],
    families: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Validate and normalize suite data against the immutable scenario catalog."""
    if not isinstance(document, Mapping) or document.get("schema_version") != 1:
        raise SuiteError("unsupported suite catalog")
    raw_suites = document.get("suites")
    if not isinstance(raw_suites, list) or not raw_suites:
        raise SuiteError("suite catalog must contain a nonempty suites list")
    steps = scenario_steps(families)
    normalized: list[dict[str, Any]] = []
    suite_ids: set[str] = set()

    for suite_index, raw_suite in enumerate(raw_suites):
        if not isinstance(raw_suite, Mapping):
            raise SuiteError(f"suite {suite_index} must be an object")
        suite_id = _slug(raw_suite.get("id"), "suite id")
        if suite_id in suite_ids:
            raise SuiteError(f"duplicate suite: {suite_id}")
        suite_ids.add(suite_id)
        title = _nonempty_string(raw_suite.get("title"), f"suite {suite_id} title")
        description = _nonempty_string(raw_suite.get("description"), f"suite {suite_id} description")
        mode = raw_suite.get("mode")
        if mode not in {"partial", "full"}:
            raise SuiteError(f"suite {suite_id} mode must be partial or full")
        raw_cases = raw_suite.get("cases")
        if not isinstance(raw_cases, list) or not raw_cases:
            raise SuiteError(f"suite {suite_id} must contain cases")

        cases: list[dict[str, Any]] = []
        case_ids: set[str] = set()
        seen_steps_by_product: dict[str, set[str]] = {}
        product_keys: set[str] = set()
        for case_index, raw_case in enumerate(raw_cases):
            if not isinstance(raw_case, Mapping):
                raise SuiteError(f"suite {suite_id} case {case_index} must be an object")
            case_id = _slug(raw_case.get("id"), f"suite {suite_id} case id")
            if case_id in case_ids:
                raise SuiteError(f"suite {suite_id} has duplicate case: {case_id}")
            case_ids.add(case_id)
            step_id = _nonempty_string(raw_case.get("step"), f"suite {suite_id} case {case_id} step")
            if step_id not in steps:
                raise SuiteError(f"suite {suite_id} case {case_id} selects unknown step: {step_id}")
            product_key = _slug(raw_case.get("product_key"), f"suite {suite_id} case {case_id} product_key")
            stop_after_stage = raw_case.get("stop_after_stage")
            if mode == "partial":
                if stop_after_stage not in STOP_AFTER_STAGES:
                    raise SuiteError(f"partial suite {suite_id} case {case_id} needs a valid stop_after_stage")
            elif stop_after_stage is not None:
                raise SuiteError(f"full suite {suite_id} case {case_id} must not set stop_after_stage")
            timeout_seconds = _positive_int(raw_case.get("timeout_seconds"), f"suite {suite_id} case {case_id} timeout_seconds")
            max_turns = _positive_int(raw_case.get("max_turns"), f"suite {suite_id} case {case_id} max_turns")
            step = steps[step_id]
            expected_dependencies = _expected_dependencies(step)
            declared_dependencies = raw_case.get("depends_on")
            if declared_dependencies is None:
                declared_dependencies = []
            if not isinstance(declared_dependencies, list) or any(
                not isinstance(item, str) or not item for item in declared_dependencies
            ):
                raise SuiteError(f"suite {suite_id} case {case_id} depends_on must be a list of step ids")
            if declared_dependencies != expected_dependencies:
                raise SuiteError(
                    f"suite {suite_id} case {case_id} dependencies do not match scenario {step_id}"
                )
            if mode == "partial" and expected_dependencies:
                raise SuiteError(
                    f"partial suite {suite_id} case {case_id} is not independent: {step_id} has a predecessor"
                )
            if mode == "partial" and product_key in product_keys:
                raise SuiteError(f"partial suite {suite_id} reuses product_key: {product_key}")
            product_keys.add(product_key)
            prior_steps = seen_steps_by_product.setdefault(product_key, set())
            missing = [dependency for dependency in expected_dependencies if dependency not in prior_steps]
            if mode == "full" and missing:
                raise SuiteError(
                    f"full suite {suite_id} case {case_id} appears before predecessor: {', '.join(missing)}"
                )
            prior_steps.add(step_id)
            cases.append({
                "id": case_id,
                "sequence": case_index + 1,
                "step_id": step_id,
                "kind": step["kind"],
                "prompt": step["prompt"],
                "product_key": product_key,
                "depends_on": expected_dependencies,
                "stop_after_stage": stop_after_stage,
                "timeout_seconds": timeout_seconds,
                "max_turns": max_turns,
            })
        normalized.append({
            "id": suite_id,
            "title": title,
            "description": description,
            "mode": mode,
            "partial": mode == "partial",
            "completion_claim": "partial-prefix" if mode == "partial" else "full-chain",
            "cases": cases,
        })
    return normalized


def load_suites(
    families: Sequence[Mapping[str, Any]] | None = None,
    path: Path | str = SUITES_PATH,
) -> list[dict[str, Any]]:
    """Load named suites, checking every case against the scenario catalog."""
    selected_families = load_scenario_families() if families is None else families
    return validate_suites(_read_json(Path(path)), selected_families)


def list_suites(
    families: Sequence[Mapping[str, Any]] | None = None,
    path: Path | str = SUITES_PATH,
) -> list[dict[str, Any]]:
    """Return display-safe suite summaries without duplicating literal prompts."""
    return [{
        "id": suite["id"],
        "title": suite["title"],
        "description": suite["description"],
        "mode": suite["mode"],
        "partial": suite["partial"],
        "completion_claim": suite["completion_claim"],
        "case_count": len(suite["cases"]),
        "cases": [{
            "id": case["id"],
            "step_id": case["step_id"],
            "stop_after_stage": case["stop_after_stage"],
            "timeout_seconds": case["timeout_seconds"],
            "max_turns": case["max_turns"],
        } for case in suite["cases"]],
    } for suite in load_suites(families, path)]


def resolve_suite(
    suite_id: str,
    families: Sequence[Mapping[str, Any]] | None = None,
    *,
    only_case_ids: Sequence[str] | None = None,
    path: Path | str = SUITES_PATH,
) -> dict[str, Any]:
    """Resolve one suite, optionally retaining a selected case or step subset.

    Scenario dependencies are normalized to lists in every returned case. The
    metadata stays intact when a selected feature omits its predecessor. The
    caller must then require a separately retained, receipted predecessor
    rather than treating the selection as a complete run.
    """
    matches = [suite for suite in load_suites(families, path) if suite["id"] == suite_id]
    if len(matches) != 1:
        raise SuiteError(f"unknown suite: {suite_id}")
    suite = deepcopy(matches[0])
    requested = list(only_case_ids or [])
    if not requested:
        suite["selection"] = {
            "requested_case_ids": [],
            "dependency_complete": True,
            "missing_predecessor_step_ids": [],
        }
        return suite
    if any(not isinstance(item, str) or not item for item in requested):
        raise SuiteError("only_case_ids must contain nonempty case or step ids")
    selected = [case for case in suite["cases"] if case["id"] in requested or case["step_id"] in requested]
    matched = {case["id"] for case in selected} | {case["step_id"] for case in selected}
    unknown = [item for item in requested if item not in matched]
    if unknown:
        raise SuiteError(f"suite {suite_id} has no selected case or step: {', '.join(unknown)}")
    selected_steps = {case["step_id"] for case in selected}
    missing = sorted({dependency for case in selected for dependency in case["depends_on"] if dependency not in selected_steps})
    suite["cases"] = selected
    suite["selection"] = {
        "requested_case_ids": requested,
        "dependency_complete": not missing,
        "missing_predecessor_step_ids": missing,
    }
    return suite


__all__ = [
    "SCENARIOS_PATH",
    "STOP_AFTER_STAGES",
    "SUITES_PATH",
    "SuiteError",
    "list_suites",
    "load_scenario_families",
    "load_suites",
    "resolve_suite",
    "scenario_steps",
    "validate_suites",
]
