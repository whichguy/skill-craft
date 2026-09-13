"""Pure validation and rendering for the DAG-owned system-test catalog.

``backchain/plan.md`` remains authoritative.  This module deliberately has no
state, filesystem, command, or deployment effects; callers persist the output
of :func:`render` only as a readable derivative.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

import shiploop_privacy as privacy


VERSION = 1
MAX_CASES = 128
PHASES = ("pre_deployment", "post_deployment")
STATUSES = ("required", "not-applicable")
_SYSTEM_ACTIVITY = {
    "pre_deployment": "system-test-pre",
    "post_deployment": "system-test-post",
}
_CASE_KEYS = frozenset(
    (
        "id",
        "phase",
        "requirement",
        "expected_outcome",
        "environment",
        "prerequisites",
        "test_step",
        "test_id",
        "deployment_step",
    )
)
_CATALOG_KEYS = frozenset(("version", "phases", "cases"))
_PHASE_KEYS = frozenset(("status", "reason"))
_SYS_ID = re.compile(r"SYS-[A-Z0-9][A-Z0-9._-]{0,79}\Z")
_STEP_ID = re.compile(r"[A-Za-z][A-Za-z0-9._:-]{0,159}\Z")
_TEST_ID = re.compile(r"T-[A-Z0-9][A-Z0-9._-]{0,79}\Z")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class SystemTestError(ValueError):
    """A system-test catalog is malformed or incompatible with its DAG."""


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise SystemTestError(message)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def _copy(value: Any) -> Any:
    return json.loads(_canonical(value).decode())


def _text(value: Any, label: str) -> str:
    _need(isinstance(value, str), f"{label} must be a nonempty concrete string")
    text = value.strip()
    _need(
        bool(text) and _CONTROL.search(text) is None,
        f"{label} must be a nonempty one-line string",
    )
    _need(len(text) <= 4000, f"{label} exceeds the bounded text limit")
    _need(
        not privacy.sensitive_text(text),
        f"{label} appears to contain a credential secret",
    )
    return text


def _id(value: Any, label: str, pattern: re.Pattern[str] = _STEP_ID) -> str:
    _need(
        isinstance(value, str) and pattern.fullmatch(value) is not None,
        f"{label} must be a stable safe identifier",
    )
    _need(
        not privacy.sensitive_text(value),
        f"{label} appears to contain a credential secret",
    )
    return value


def _steps(dag: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = dag.get("steps")
    _need(isinstance(raw, list), "DAG steps must be a list")
    result: dict[str, Mapping[str, Any]] = {}
    for index, step in enumerate(raw):
        _need(isinstance(step, Mapping), f"DAG step {index} must be an object")
        ident = _id(step.get("id"), f"DAG step {index}.id")
        _need(ident not in result, f"DAG step IDs must not duplicate: {ident}")
        result[ident] = step
    return result


def _parents(steps: Mapping[str, Mapping[str, Any]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {ident: set() for ident in steps}
    for ident, step in steps.items():
        inputs = step.get("inputs", [])
        _need(isinstance(inputs, list), f"step {ident}.inputs must be a list")
        for item in inputs:
            _need(
                isinstance(item, Mapping),
                f"step {ident}.inputs entry must be an object",
            )
            parent = item.get("from")
            # ShipLoop's baseline facts use ``from: null``.  They are inputs,
            # but not edges between DAG steps.
            if parent is None:
                continue
            _need(
                isinstance(parent, str) and parent in steps,
                f"step {ident} has an unknown prerequisite step",
            )
            _need(parent != ident, f"step {ident} must not depend on itself")
            result[ident].add(parent)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(ident: str) -> None:
        _need(ident not in visiting, "DAG prerequisites contain a cycle")
        if ident in visited:
            return
        visiting.add(ident)
        for parent in result[ident]:
            visit(parent)
        visiting.remove(ident)
        visited.add(ident)

    for ident in result:
        visit(ident)
    return result


def _precedes(parents: Mapping[str, set[str]], earlier: str, later: str) -> bool:
    """Whether ``earlier`` is a strict transitive predecessor of ``later``."""
    todo = list(parents[later])
    seen: set[str] = set()
    while todo:
        current = todo.pop()
        if current == earlier:
            return True
        if current not in seen:
            seen.add(current)
            todo.extend(parents[current])
    return False


def _catalog_from(value: Any) -> Any:
    if isinstance(value, Mapping):
        if "system_tests" in value:
            return value["system_tests"]
        # A prior DAG without the optional catalog is a supported legacy
        # baseline, not an attempted catalog object.
        if "steps" in value:
            return None
    return value


def _contract_test(step: Mapping[str, Any], test_id: str, expected: str) -> bool:
    contract = step.get("contract")
    if not isinstance(contract, Mapping) or not isinstance(contract.get("tests"), list):
        return False
    return any(
        isinstance(row, Mapping)
        and row.get("id") == test_id
        and row.get("expected_outcome") == expected
        for row in contract["tests"]
    )


def _normal_catalog(raw: Any) -> dict[str, Any]:
    _need(
        isinstance(raw, Mapping) and set(raw) == _CATALOG_KEYS,
        "system_tests must have exactly version, phases, and cases",
    )
    _need(
        type(raw["version"]) is int and raw["version"] == VERSION,
        "system_tests.version must be the exact supported integer",
    )
    phases_raw = raw["phases"]
    _need(
        isinstance(phases_raw, Mapping) and set(phases_raw) == set(PHASES),
        "system_tests.phases must name pre_deployment and post_deployment",
    )
    phases: dict[str, dict[str, str]] = {}
    for phase in PHASES:
        decision = phases_raw[phase]
        _need(
            isinstance(decision, Mapping) and set(decision) == _PHASE_KEYS,
            f"system_tests.phases.{phase} has an unexpected schema",
        )
        status = decision["status"]
        _need(status in STATUSES, f"system_tests.phases.{phase}.status is invalid")
        reason = _text(decision["reason"], f"system_tests.phases.{phase}.reason")
        _need(
            len(reason) <= 1000,
            f"system_tests.phases.{phase}.reason exceeds the bounded limit",
        )
        phases[phase] = {"status": status, "reason": reason}
    rows = raw["cases"]
    _need(
        isinstance(rows, list) and len(rows) <= MAX_CASES,
        "system_tests.cases exceeds the bounded limit",
    )
    cases: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, value in enumerate(rows):
        label = f"system_tests.cases[{index}]"
        _need(
            isinstance(value, Mapping) and set(value) == _CASE_KEYS,
            f"{label} has an unexpected schema",
        )
        ident = _id(value["id"], f"{label}.id", _SYS_ID)
        _need(ident not in ids, f"system_tests case IDs must not duplicate: {ident}")
        ids.add(ident)
        phase = value["phase"]
        _need(phase in PHASES, f"{label}.phase is invalid")
        prereqs = value["prerequisites"]
        _need(
            isinstance(prereqs, list) and len(prereqs) <= 32,
            f"{label}.prerequisites is invalid",
        )
        normalized_prereqs = [
            _id(item, f"{label}.prerequisites entry") for item in prereqs
        ]
        _need(
            len(normalized_prereqs) == len(set(normalized_prereqs)),
            f"{label}.prerequisites must not duplicate",
        )
        deployment = value["deployment_step"]
        _need(
            deployment is None or isinstance(deployment, str),
            f"{label}.deployment_step must be null or an ID",
        )
        if deployment is not None:
            deployment = _id(deployment, f"{label}.deployment_step")
        cases.append(
            {
                "id": ident,
                "phase": phase,
                "requirement": _text(value["requirement"], f"{label}.requirement"),
                "expected_outcome": _text(
                    value["expected_outcome"], f"{label}.expected_outcome"
                ),
                "environment": _text(value["environment"], f"{label}.environment"),
                "prerequisites": normalized_prereqs,
                "test_step": _id(value["test_step"], f"{label}.test_step"),
                "test_id": _id(value["test_id"], f"{label}.test_id", _TEST_ID),
                "deployment_step": deployment,
            }
        )
    for phase in PHASES:
        phase_cases = [case for case in cases if case["phase"] == phase]
        _need(
            bool(phase_cases) == (phases[phase]["status"] == "required"),
            f"system_tests phase {phase} must have cases exactly when required",
        )
    return {"version": VERSION, "phases": phases, "cases": cases}


def validate(
    dag: Any,
    lifecycle: Any,
    required: bool = False,
    previous: Any = None,
    locked_steps: tuple[str, ...] = (),
) -> dict[str, Any] | None:
    """Validate the optional catalog and its DAG placement, returning a copy."""
    _need(isinstance(dag, Mapping), "DAG must be an object")
    _need(isinstance(lifecycle, Mapping), "lifecycle must be an object")
    prior = _catalog_from(previous)
    if "system_tests" not in dag:
        _need(not required, "system_tests catalog is required")
        _need(prior is None, "system_tests catalog cannot be removed once enabled")
        return None
    raw = dag["system_tests"]
    catalog = _normal_catalog(raw)
    steps = _steps(dag)
    parents = _parents(steps)
    publish = lifecycle.get("publish")
    _need(publish in ("none", "dag", "outer-loop"), "lifecycle.publish is invalid")
    locked = set(locked_steps)
    _need(
        all(isinstance(item, str) for item in locked), "locked_steps must contain IDs"
    )
    if prior is not None:
        old = _normal_catalog(prior)
        current_by_id = {case["id"]: case for case in catalog["cases"]}
        for case in old["cases"]:
            if case["test_step"] in locked or case["deployment_step"] in locked:
                _need(
                    current_by_id.get(case["id"]) == case,
                    f"locked system-test case must remain unchanged: {case['id']}",
                )
    targeted = {phase: set() for phase in PHASES}
    typed = {phase: set() for phase in PHASES}
    for ident, step in steps.items():
        activity = step.get("activity")
        for phase, expected_activity in _SYSTEM_ACTIVITY.items():
            if activity == expected_activity:
                typed[phase].add(ident)
    for case in catalog["cases"]:
        phase, owner = case["phase"], case["test_step"]
        _need(
            owner in steps,
            f"system-test case {case['id']} references unknown test_step",
        )
        _need(
            steps[owner].get("activity") == _SYSTEM_ACTIVITY[phase],
            f"system-test case {case['id']} test_step has the wrong activity",
        )
        _need(
            _contract_test(steps[owner], case["test_id"], case["expected_outcome"]),
            f"system-test case {case['id']} does not match test_step contract.tests",
        )
        for prerequisite in case["prerequisites"]:
            _need(
                prerequisite in steps,
                f"system-test case {case['id']} has an unknown prerequisite",
            )
            _need(
                prerequisite != owner and _precedes(parents, prerequisite, owner),
                f"system-test case {case['id']} prerequisite must transitively precede test_step",
            )
        deployment = case["deployment_step"]
        if phase == "pre_deployment":
            if publish == "dag":
                _need(
                    deployment is not None,
                    f"pre-deployment case {case['id']} requires deployment_step for DAG publish",
                )
                _need(
                    deployment in steps
                    and steps[deployment].get("activity") == "publish",
                    f"pre-deployment case {case['id']} deployment_step must be a publish step",
                )
                _need(
                    _precedes(parents, owner, deployment),
                    f"pre-deployment case {case['id']} must precede deployment_step",
                )
                targeted[phase].add(deployment)
            else:
                _need(
                    deployment is None,
                    f"pre-deployment case {case['id']} deployment_step must be null without DAG publish",
                )
        else:
            _need(
                publish == "dag",
                f"post-deployment case {case['id']} requires lifecycle.publish=dag",
            )
            _need(
                deployment is not None
                and deployment in steps
                and steps[deployment].get("activity") == "publish",
                f"post-deployment case {case['id']} deployment_step must be a publish step",
            )
            _need(
                _precedes(parents, deployment, owner),
                f"post-deployment case {case['id']} must depend on deployment_step",
            )
            targeted[phase].add(deployment)
    for phase in PHASES:
        _need(
            typed[phase]
            <= {
                case["test_step"] for case in catalog["cases"] if case["phase"] == phase
            },
            f"typed {phase} system-test activity has no case",
        )
    publish_steps = {
        ident for ident, step in steps.items() if step.get("activity") == "publish"
    }
    for phase in PHASES:
        if catalog["phases"][phase]["status"] == "required" and publish_steps:
            _need(
                publish_steps <= targeted[phase],
                f"every publish step needs a {phase} system-test case",
            )
    return _copy(catalog)


def render(dag: Any) -> str:
    """Render only a readable derivative; it never asserts a test passed."""
    _need(
        isinstance(dag, Mapping) and "system_tests" in dag,
        "system_tests catalog is missing",
    )
    catalog = _normal_catalog(dag["system_tests"])
    lines = [
        "# System-test requirements",
        "",
        "Authoritative catalog: `backchain/plan.md` → `system_tests`. This file records requirements and is not test-pass evidence.",
        "",
        "## Phase decisions",
        "",
    ]
    for phase in PHASES:
        decision = catalog["phases"][phase]
        lines.append(f"- `{phase}`: **{decision['status']}** — {decision['reason']}")
    for phase in PHASES:
        lines.extend(["", f"## {phase}", ""])
        cases = [case for case in catalog["cases"] if case["phase"] == phase]
        if not cases:
            lines.append(
                "No cases are required for this explicitly not-applicable phase."
            )
        for case in cases:
            prereqs = ", ".join(case["prerequisites"]) or "none"
            deployment = case["deployment_step"] or "none"
            lines.extend(
                (
                    f"### {case['id']}",
                    "",
                    f"- Requirement: {case['requirement']}",
                    f"- Expected outcome: {case['expected_outcome']}",
                    f"- Environment: {case['environment']}",
                    f"- Prerequisite steps: {prereqs}",
                    f"- Test owner: {case['test_step']} / {case['test_id']}",
                    f"- Deployment step: {deployment}",
                )
            )
    return "\n".join(lines) + "\n"
