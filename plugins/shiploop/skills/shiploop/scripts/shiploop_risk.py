#!/usr/bin/env python3
"""Pure validators for versioned lifecycle security, fuzz, and maintenance policy.

The protocol owns Markdown reads and state-version selection.  This module only
validates caller-provided objects, so it cannot schedule work, inspect a host,
contact an advisory source, or turn a maintenance plan into an automatic
updater.  A caller that has opted into ``risk_policy_version`` must pass
``required=True``; legacy callers may omit the policy entirely.
"""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any


RISK_POLICY_VERSION = 1
_RISK_DECISIONS = frozenset(("required", "not-applicable", "blocked"))
_MAINTENANCE_DECISIONS = frozenset(
    ("dag", "operate-later", "not-applicable", "blocked")
)
_POLICY_KEYS = frozenset(("risk_policy_version", "security", "fuzz", "maintenance"))
_TEST_ID = re.compile(r"^T-[A-Z0-9][A-Z0-9._-]{0,79}$")
_FUTURE_WORD = re.compile(r"\b(?:future|later|defer(?:red)?|after)\b", re.IGNORECASE)
_CONTROL = re.compile(r"[\x00-\x08\x0a-\x1f\x7f]")
_PLACEHOLDER = re.compile(
    r"^\s*(?:tbd|todo|unknown|none|n/?a|same as above|\.\.\.)\s*$",
    re.IGNORECASE,
)


def _text(value: Any, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str):
        errors.append(f"{label} must be a concrete nonempty string")
        return None
    text = value.strip()
    if not text or _CONTROL.search(text) or _PLACEHOLDER.fullmatch(text):
        errors.append(f"{label} must be a concrete nonempty string")
        return None
    return text


def _mapping(value: Any, label: str, errors: list[str]) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        errors.append(f"{label} must be an object")
        return None
    return value


def _keys(
    value: Mapping[str, Any],
    label: str,
    required: frozenset[str],
    errors: list[str],
    *,
    optional: frozenset[str] = frozenset(),
) -> None:
    missing = sorted(key for key in required if key not in value)
    non_string = sorted(repr(key) for key in value if not isinstance(key, str))
    unsupported = sorted(
        key
        for key in value
        if isinstance(key, str) and key not in required and key not in optional
    )
    if missing:
        errors.append(f"{label} is missing keys: {', '.join(missing)}")
    if non_string:
        errors.append(f"{label} has non-string keys: {', '.join(non_string)}")
    if unsupported:
        errors.append(f"{label} has unsupported keys: {', '.join(unsupported)}")


def _decision(
    value: Mapping[str, Any],
    label: str,
    choices: frozenset[str],
    errors: list[str],
) -> str | None:
    decision = value.get("decision")
    if not isinstance(decision, str) or decision not in choices:
        errors.append(f"{label}.decision must be one of: {', '.join(sorted(choices))}")
        return None
    return decision


def _case_ids(value: Any, label: str, errors: list[str]) -> list[str] | None:
    if not isinstance(value, list) or not value:
        errors.append(f"{label} must be a nonempty list of exact T-* case IDs")
        return None
    ids: list[str] = []
    for index, raw in enumerate(value):
        text = _text(raw, f"{label}[{index}]", errors)
        if text is None:
            continue
        if not _TEST_ID.fullmatch(text):
            errors.append(f"{label}[{index}] must be an exact T-* case ID")
            continue
        ids.append(text)
    duplicates = sorted({ident for ident in ids if ids.count(ident) > 1})
    if duplicates:
        errors.append(f"{label} must not repeat case IDs: {', '.join(duplicates)}")
    return ids if len(ids) == len(value) and not duplicates else None


def _risk_decision(value: Any, name: str, errors: list[str]) -> None:
    label = f"risk_policy.{name}"
    record = _mapping(value, label, errors)
    if record is None:
        return
    decision = _decision(record, label, _RISK_DECISIONS, errors)
    _text(record.get("rationale"), f"{label}.rationale", errors)
    if decision == "required":
        _keys(record, label, frozenset(("decision", "rationale", "case_ids")), errors)
        _case_ids(record.get("case_ids"), f"{label}.case_ids", errors)
    elif decision == "blocked":
        # A blocked spec may retain concrete planned cases for the later DAG,
        # but it cannot use them to pass the sequence gate.
        _keys(
            record,
            label,
            frozenset(("decision", "rationale")),
            errors,
            optional=frozenset(("case_ids",)),
        )
        if "case_ids" in record:
            _case_ids(record["case_ids"], f"{label}.case_ids", errors)
    elif decision == "not-applicable":
        _keys(
            record,
            f"{label} not-applicable",
            frozenset(("decision", "rationale")),
            errors,
        )


def _selected_maintenance(
    record: Mapping[str, Any],
    *,
    operate_later: bool,
    errors: list[str],
) -> None:
    label = "risk_policy.maintenance"
    required = frozenset(
        (
            "decision",
            "rationale",
            "owner",
            "advisory_source",
            "cadence",
            "mechanism",
            "validation",
            "rollback",
            "step_id",
        )
    )
    _keys(
        record,
        label,
        required,
        errors,
    )
    rationale = _text(record.get("rationale"), f"{label}.rationale", errors)
    for field in (
        "owner",
        "advisory_source",
        "cadence",
        "mechanism",
        "validation",
        "rollback",
    ):
        _text(record.get(field), f"{label}.{field}", errors)
    if operate_later:
        if record.get("step_id") is not None:
            errors.append(f"{label}.operate-later step_id must be null")
        if rationale is not None and not _FUTURE_WORD.search(rationale):
            errors.append(
                f"{label}.operate-later rationale must explicitly describe future work"
            )
    else:
        _text(record.get("step_id"), f"{label}.step_id", errors)


def _maintenance_decision(value: Any, errors: list[str]) -> None:
    label = "risk_policy.maintenance"
    record = _mapping(value, label, errors)
    if record is None:
        return
    decision = _decision(record, label, _MAINTENANCE_DECISIONS, errors)
    if decision == "dag":
        _selected_maintenance(record, operate_later=False, errors=errors)
    elif decision == "operate-later":
        _selected_maintenance(record, operate_later=True, errors=errors)
    else:
        _text(record.get("rationale"), f"{label}.rationale", errors)
    if decision in ("not-applicable", "blocked"):
        _keys(
            record, f"{label} {decision}", frozenset(("decision", "rationale")), errors
        )


def validate_policy(policy: Any, required: bool = False) -> list[str]:
    """Return lifecycle risk-policy schema gaps without reading or changing state.

    ``None`` is a legacy absence only when ``required`` is exactly ``False``.
    Once a policy object exists, an omitted, boolean, float, string, or unknown
    version is always invalid rather than silently treated as legacy.
    """
    errors: list[str] = []
    if type(required) is not bool:
        return ["risk-policy required flag must be a boolean"]
    if policy is None:
        return (
            ["lifecycle.risk_policy is required for the current risk-policy version"]
            if required
            else []
        )
    record = _mapping(policy, "lifecycle.risk_policy", errors)
    if record is None:
        return errors
    _keys(record, "lifecycle.risk_policy", _POLICY_KEYS, errors)
    if "risk_policy_version" not in record:
        errors.append("lifecycle.risk_policy.risk_policy_version is required")
    else:
        version = record.get("risk_policy_version")
        if type(version) is not int:
            errors.append(
                "lifecycle.risk_policy.risk_policy_version must be integer 1, not a legacy default"
            )
        elif version != RISK_POLICY_VERSION:
            errors.append(
                "lifecycle.risk_policy.risk_policy_version "
                f"{version!r} is unsupported; expected {RISK_POLICY_VERSION}"
            )
    _risk_decision(record.get("security"), "security", errors)
    _risk_decision(record.get("fuzz"), "fuzz", errors)
    _maintenance_decision(record.get("maintenance"), errors)
    return errors


def _dag_steps(dag: Any, errors: list[str]) -> dict[str, list[Mapping[str, Any]]]:
    record = _mapping(dag, "DAG", errors)
    if record is None:
        return {}
    rows = record.get("steps")
    if not isinstance(rows, list) or not rows:
        errors.append("DAG steps must be a nonempty list")
        return {}
    by_id: dict[str, list[Mapping[str, Any]]] = {}
    for index, raw in enumerate(rows):
        step = _mapping(raw, f"DAG steps[{index}]", errors)
        if step is None:
            continue
        identifier = _text(step.get("id"), f"DAG steps[{index}].id", errors)
        if identifier is None:
            continue
        by_id.setdefault(identifier, []).append(step)
    return by_id


def _test_locations(
    steps: Mapping[str, list[Mapping[str, Any]]], errors: list[str]
) -> dict[str, list[str]]:
    locations: dict[str, list[str]] = {}
    for step_id, rows in steps.items():
        for duplicate_index, step in enumerate(rows):
            contract = step.get("contract")
            if not isinstance(contract, Mapping):
                continue
            tests = contract.get("tests")
            if not isinstance(tests, list):
                continue
            for index, raw in enumerate(tests):
                if not isinstance(raw, Mapping):
                    continue
                identifier = raw.get("id")
                if not isinstance(identifier, str) or not _TEST_ID.fullmatch(
                    identifier
                ):
                    continue
                location = f"{step_id}.contract.tests[{index}]"
                if duplicate_index:
                    location = f"{location} duplicate-step[{duplicate_index}]"
                locations.setdefault(identifier, []).append(location)
    return locations


def _has_produces(step: Mapping[str, Any]) -> bool:
    produces = step.get("produces")
    if isinstance(produces, str):
        return bool(produces.strip())
    return (
        isinstance(produces, list)
        and bool(produces)
        and all(isinstance(item, str) and item.strip() for item in produces)
    )


def _is_upstream(
    supplier: str,
    consumer: str,
    steps: Mapping[str, list[Mapping[str, Any]]],
) -> tuple[bool, str | None]:
    """Prove an exact transitive DAG dependency without repairing malformed rows."""
    seen: set[str] = set()
    stack = [consumer]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        rows = steps.get(current)
        if rows is None or len(rows) != 1:
            return False, f"DAG step {current} is not uniquely defined"
        inputs = rows[0].get("inputs")
        if not isinstance(inputs, list):
            return False, f"DAG step {current}.inputs is malformed"
        for index, raw in enumerate(inputs):
            if not isinstance(raw, Mapping):
                return False, f"DAG step {current}.inputs[{index}] is malformed"
            upstream = raw.get("from")
            if upstream is None:
                continue
            if not isinstance(upstream, str) or not upstream:
                return False, f"DAG step {current}.inputs[{index}].from is malformed"
            if upstream == supplier:
                return True, None
            if upstream not in steps:
                return False, f"DAG step {current}.inputs[{index}].from is unknown"
            stack.append(upstream)
    return False, None


def validate_dag(policy: Any, dag: Any) -> list[str]:
    """Return sequence-only gaps for a validated, versioned risk policy.

    This always requires a current policy: protocol callers skip this function
    for legacy runs.  It verifies only declared case/producer identities and
    ordering; it does not run the cases, query advisories, or schedule an
    ``operate-later`` record.
    """
    errors = validate_policy(policy, required=True)
    if errors:
        return errors
    assert isinstance(policy, Mapping)  # Narrowed by validate_policy above.
    steps = _dag_steps(dag, errors)
    if not steps:
        return errors
    locations = _test_locations(steps, errors)

    for domain in ("security", "fuzz"):
        record = policy[domain]
        assert isinstance(record, Mapping)
        decision = record["decision"]
        if decision == "blocked":
            errors.append(
                f"{domain} testing is blocked; resolve it before sequence can proceed"
            )
            continue
        if decision != "required":
            continue
        case_ids = record["case_ids"]
        assert isinstance(case_ids, list)
        for case_id in case_ids:
            matches = locations.get(case_id, [])
            if not matches:
                errors.append(
                    f"{domain} case ID {case_id} is not present in DAG contract.tests"
                )
            elif len(matches) != 1:
                errors.append(
                    f"{domain} case ID {case_id} maps ambiguously to: {', '.join(matches)}"
                )
    # One case can intentionally cover both dimensions.  The ambiguity that
    # matters is a duplicate definition in the DAG, which is checked above by
    # requiring each selected case to resolve to exactly one contract test.

    maintenance = policy["maintenance"]
    assert isinstance(maintenance, Mapping)
    decision = maintenance["decision"]
    if decision == "blocked":
        errors.append("maintenance is blocked; resolve it before sequence can proceed")
        return errors
    if decision != "dag":
        return errors
    step_id = maintenance["step_id"]
    assert isinstance(step_id, str)
    matches = steps.get(step_id, [])
    if not matches:
        errors.append(
            f"maintenance step_id {step_id} does not name an existing DAG step"
        )
        return errors
    if len(matches) != 1:
        errors.append(
            f"maintenance step_id {step_id} maps ambiguously to duplicate DAG steps"
        )
        return errors
    if not _has_produces(matches[0]):
        errors.append(
            f"maintenance DAG step {step_id} must be a producer with nonempty produces"
        )
        return errors
    publishers = [
        identifier
        for identifier, rows in steps.items()
        for item in rows
        if item.get("activity") == "publish"
    ]
    for publisher in publishers:
        if publisher == step_id:
            errors.append(
                f"maintenance step {step_id} must precede publication step {publisher}; they cannot be the same step"
            )
            continue
        ordered, problem = _is_upstream(step_id, publisher, steps)
        if problem is not None:
            errors.append(
                f"maintenance step {step_id} cannot prove ordering before publication {publisher}: {problem}"
            )
        elif not ordered:
            errors.append(
                f"maintenance step {step_id} must precede publication step {publisher} through DAG inputs"
            )
    return errors
