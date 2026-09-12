"""Bounded system-context links for versioned ShipLoop research evidence.

This module deliberately keeps the detailed narrative in ``research.md`` and
``research-evidence.md``.  It validates only the compact references needed for
cold planning context: observed system facets, roles, surveyed interfaces, and
the selected interaction contracts that connect them.  It does not discover a
platform, execute a probe, create a DAG, or decide whether host-reported
evidence is true.

Legacy research evidence has the exact two-key ``questions``/``sources``
schema.  Callers opt into this extension only after their run state declares
``system_context_protocol_version: 1``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

import shiploop_knowledge as knowledge
import shiploop_research as research
import shiploop_store as store


SYSTEM_CONTEXT_PROTOCOL_VERSION = 1
MAX_ROWS = research.MAX_ROWS
MAX_REFS = research.MAX_REFS
MAX_PROJECTION_ROWS = 8

_MISSING = object()
_ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9._:-]{0,159}\Z")
_SCOPES = {"local-only", "integrated"}
_OBSERVATION_KINDS = {"code", "state", "system", "environment-role"}
_OBSERVATION_STATUSES = {"observed", "blocked", "not-applicable"}
_ROLE_STATUSES = _OBSERVATION_STATUSES
_CONTRACT_STATUSES = {"resolved", "blocked", "not-applicable"}
_RISK_LEVELS = {"low", "medium", "high"}


class SystemContextError(ValueError):
    """A versioned system-context record is malformed or inconsistent."""


def need(ok: bool, message: str) -> None:
    if not ok:
        raise SystemContextError(message)


def context_current(state: Any) -> bool:
    """Return whether a state explicitly selected this extension.

    Missing is the only legacy form.  A supplied non-v1 marker fails closed so
    a newer or malformed record cannot accidentally receive legacy validation.
    """
    need(isinstance(state, Mapping), "state must be an object for system context")
    marker = state.get("system_context_protocol_version", _MISSING)
    if marker is _MISSING:
        return False
    need(
        type(marker) is int and marker == SYSTEM_CONTEXT_PROTOCOL_VERSION,
        f"system_context_protocol_version must be {SYSTEM_CONTEXT_PROTOCOL_VERSION}",
    )
    return True


def _text(value: Any, label: str) -> str:
    need(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty")
    result = value.strip()
    need(len(result) <= knowledge.MAX_TEXT, f"{label} exceeds the bounded context limit")
    return result


def _id(value: Any, label: str) -> str:
    need(
        isinstance(value, str) and _ID_RE.fullmatch(value) is not None,
        f"{label} must be a stable safe identifier",
    )
    return value


def _rows(value: Any, label: str, *, required: bool = False) -> list[Any]:
    need(isinstance(value, list), f"{label} must be a list")
    need(len(value) <= MAX_ROWS, f"{label} exceeds the bounded context limit")
    if required:
        need(bool(value), f"{label} must be nonempty")
    return value


def _refs(
    value: Any,
    label: str,
    *,
    known: set[str] | None = None,
    required: bool = False,
) -> list[str]:
    need(isinstance(value, list), f"{label} must be a list")
    need(len(value) <= MAX_REFS, f"{label} exceeds the bounded context limit")
    result = [_id(item, f"{label} entry") for item in value]
    need(len(result) == len(set(result)), f"{label} must not duplicate entries")
    if required:
        need(bool(result), f"{label} must be nonempty")
    if known is not None:
        unknown = sorted(set(result) - known)
        need(not unknown, f"{label} names unknown ID(s): {', '.join(unknown)}")
    return result


def _screen(value: Mapping[str, Any]) -> None:
    """Apply the existing secret/size screen without leaking untrusted values."""
    try:
        knowledge.screen_payload(value)
    except Exception as exc:  # Normalize the public helper's error class.
        raise SystemContextError(str(exc)) from exc


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _base_research_state(value: Any) -> dict[str, Any]:
    """Validate extended question rows through the frozen legacy validator."""
    expected = {"questions", "sources", "system_context"}
    need(
        isinstance(value, Mapping) and set(value) == expected,
        "versioned research_state has an unexpected schema",
    )
    raw_questions = _rows(value["questions"], "research questions", required=True)
    base_questions: list[dict[str, Any]] = []
    extensions: list[dict[str, list[str]]] = []
    expected_question = {
        "id",
        "question",
        "origin",
        "status",
        "answer",
        "sources",
        "revalidate",
        "rationale",
        "parents",
        "contract_refs",
        "role_refs",
        "interface_refs",
    }
    for index, row in enumerate(raw_questions):
        label = f"research questions[{index}]"
        need(
            isinstance(row, Mapping) and set(row) == expected_question,
            "versioned research question has an unexpected schema",
        )
        base_questions.append(
            {
                key: row[key]
                for key in (
                    "id",
                    "question",
                    "origin",
                    "status",
                    "answer",
                    "sources",
                    "revalidate",
                    "rationale",
                )
            }
        )
        extensions.append(
            {
                "parents": _refs(row["parents"], f"{label}.parents"),
                "contract_refs": _refs(
                    row["contract_refs"], f"{label}.contract_refs"
                ),
                "role_refs": _refs(row["role_refs"], f"{label}.role_refs"),
                "interface_refs": _refs(
                    row["interface_refs"], f"{label}.interface_refs"
                ),
            }
        )
    try:
        legacy = research.validate_state(
            {"questions": base_questions, "sources": value["sources"]}
        )
    except research.ResearchError as exc:
        raise SystemContextError(str(exc)) from exc
    questions: list[dict[str, Any]] = []
    for row, extension in zip(legacy["questions"], extensions, strict=True):
        questions.append({**row, **extension})
    return {
        "questions": questions,
        "sources": legacy["sources"],
        "system_context": value["system_context"],
    }


def _survey_index(machine: Any) -> tuple[dict[str, Mapping[str, Any]], set[tuple[str, str]], bool]:
    """Read only frozen platform/interface identity, without duplicating discovery."""
    need(isinstance(machine, Mapping), "machine must be an object for system context")
    raw = machine.get("platform_discovery", _MISSING)
    if raw is _MISSING:
        return {}, set(), False
    need(isinstance(raw, Mapping), "machine.platform_discovery must be an object")
    applicable = raw.get("applicable")
    need(
        type(applicable) is bool,
        "machine.platform_discovery.applicable must be a boolean",
    )
    platforms = raw.get("platforms")
    need(isinstance(platforms, list), "machine.platform_discovery.platforms must be a list")
    by_id: dict[str, Mapping[str, Any]] = {}
    interfaces: set[tuple[str, str]] = set()
    for index, row in enumerate(platforms):
        need(
            isinstance(row, Mapping),
            f"machine.platform_discovery.platforms[{index}] must be an object",
        )
        platform_id = _id(
            row.get("id"), f"machine.platform_discovery.platforms[{index}].id"
        )
        need(platform_id not in by_id, "machine.platform_discovery platform IDs must be unique")
        by_id[platform_id] = row
        raw_interfaces = row.get("interfaces", [])
        need(
            isinstance(raw_interfaces, list),
            f"machine.platform_discovery.platforms[{index}].interfaces must be a list",
        )
        for interface_index, interface in enumerate(raw_interfaces):
            need(
                isinstance(interface, Mapping),
                "machine.platform_discovery interface must be an object",
            )
            name = _text(
                interface.get("name"),
                "machine.platform_discovery.platforms"
                f"[{index}].interfaces[{interface_index}].name",
            )
            pair = (platform_id, name)
            need(pair not in interfaces, "machine.platform_discovery interface identity must be unique")
            interfaces.add(pair)
    if applicable is False:
        need(not by_id, "local-only platform discovery must not declare platforms")
    return by_id, interfaces, applicable


def _role(
    value: Any,
    *,
    known_sources: set[str],
    known_platforms: set[str],
    index: int,
) -> dict[str, Any]:
    expected = {
        "id",
        "label",
        "status",
        "permitted_actions",
        "isolation",
        "platform_refs",
        "source_refs",
        "revalidate",
    }
    need(
        isinstance(value, Mapping) and set(value) == expected,
        "system-context role has an unexpected schema",
    )
    label = f"system_context.roles[{index}]"
    status = value["status"]
    need(status in _ROLE_STATUSES, f"{label}.status is invalid")
    result = {
        "id": _id(value["id"], f"{label}.id"),
        "label": _text(value["label"], f"{label}.label"),
        "status": status,
        "permitted_actions": _text(value["permitted_actions"], f"{label}.permitted_actions"),
        "isolation": _text(value["isolation"], f"{label}.isolation"),
        "platform_refs": _refs(
            value["platform_refs"],
            f"{label}.platform_refs",
            known=known_platforms,
        ),
        "source_refs": _refs(
            value["source_refs"],
            f"{label}.source_refs",
            known=known_sources,
            required=status == "observed",
        ),
        "revalidate": _text(value["revalidate"], f"{label}.revalidate"),
    }
    _screen(result)
    return result


def _survey_ref(value: Any, *, known_interfaces: set[tuple[str, str]], label: str) -> dict[str, str] | None:
    if value is None:
        return None
    expected = {"platform_id", "name"}
    need(
        isinstance(value, Mapping) and set(value) == expected,
        f"{label}.survey_ref has an unexpected schema",
    )
    result = {
        "platform_id": _id(value["platform_id"], f"{label}.survey_ref.platform_id"),
        "name": _text(value["name"], f"{label}.survey_ref.name"),
    }
    need(
        (result["platform_id"], result["name"]) in known_interfaces,
        f"{label}.survey_ref must name a frozen surveyed interface",
    )
    return result


def _interface(
    value: Any,
    *,
    known_sources: set[str],
    known_roles: set[str],
    known_interfaces: set[tuple[str, str]],
    index: int,
) -> dict[str, Any]:
    expected = {
        "id",
        "kind",
        "identity",
        "survey_ref",
        "role_refs",
        "source_refs",
        "idiom",
        "status",
        "revalidate",
    }
    need(
        isinstance(value, Mapping) and set(value) == expected,
        "system-context interface has an unexpected schema",
    )
    label = f"system_context.interfaces[{index}]"
    status = value["status"]
    need(status in _CONTRACT_STATUSES, f"{label}.status is invalid")
    result = {
        "id": _id(value["id"], f"{label}.id"),
        "kind": _text(value["kind"], f"{label}.kind"),
        "identity": _text(value["identity"], f"{label}.identity"),
        "survey_ref": _survey_ref(
            value["survey_ref"], known_interfaces=known_interfaces, label=label
        ),
        "role_refs": _refs(
            value["role_refs"], f"{label}.role_refs", known=known_roles, required=True
        ),
        "source_refs": _refs(
            value["source_refs"],
            f"{label}.source_refs",
            known=known_sources,
            required=status == "resolved",
        ),
        "idiom": _text(value["idiom"], f"{label}.idiom"),
        "status": status,
        "revalidate": _text(value["revalidate"], f"{label}.revalidate"),
    }
    _screen(result)
    return result


def _interaction(
    value: Any,
    *,
    known_sources: set[str],
    known_roles: set[str],
    known_interfaces: Mapping[str, Mapping[str, Any]],
    known_questions: set[str],
    index: int,
) -> dict[str, Any]:
    expected = {
        "id",
        "caller_interface_id",
        "callee_interface_id",
        "role_refs",
        "operation",
        "question_refs",
        "source_refs",
        "input_output",
        "state_semantics",
        "failure_semantics",
        "idiom",
        "risk",
        "depth_rationale",
        "status",
        "required",
        "consumer_steps",
    }
    need(
        isinstance(value, Mapping) and set(value) == expected,
        "system-context interaction has an unexpected schema",
    )
    label = f"system_context.interactions[{index}]"
    status = value["status"]
    need(status in _CONTRACT_STATUSES, f"{label}.status is invalid")
    need(type(value["required"]) is bool, f"{label}.required must be a boolean")
    caller = _id(value["caller_interface_id"], f"{label}.caller_interface_id")
    callee = _id(value["callee_interface_id"], f"{label}.callee_interface_id")
    need(caller in known_interfaces, f"{label}.caller_interface_id names an unknown interface")
    need(callee in known_interfaces, f"{label}.callee_interface_id names an unknown interface")
    roles = _refs(
        value["role_refs"], f"{label}.role_refs", known=known_roles, required=True
    )
    endpoint_roles = set(known_interfaces[caller]["role_refs"]) | set(
        known_interfaces[callee]["role_refs"]
    )
    need(
        endpoint_roles.issubset(set(roles)),
        f"{label}.role_refs must cover caller and callee roles",
    )
    questions = _refs(
        value["question_refs"],
        f"{label}.question_refs",
        known=known_questions,
        required=True,
    )
    result = {
        "id": _id(value["id"], f"{label}.id"),
        "caller_interface_id": caller,
        "callee_interface_id": callee,
        "role_refs": roles,
        "operation": _text(value["operation"], f"{label}.operation"),
        "question_refs": questions,
        "source_refs": _refs(
            value["source_refs"],
            f"{label}.source_refs",
            known=known_sources,
            required=status == "resolved",
        ),
        "input_output": _text(value["input_output"], f"{label}.input_output"),
        "state_semantics": _text(value["state_semantics"], f"{label}.state_semantics"),
        "failure_semantics": _text(
            value["failure_semantics"], f"{label}.failure_semantics"
        ),
        "idiom": _text(value["idiom"], f"{label}.idiom"),
        "risk": value["risk"],
        "depth_rationale": _text(value["depth_rationale"], f"{label}.depth_rationale"),
        "status": status,
        "required": value["required"],
        "consumer_steps": _refs(
            value["consumer_steps"],
            f"{label}.consumer_steps",
            required=value["required"],
        ),
    }
    need(result["risk"] in _RISK_LEVELS, f"{label}.risk is invalid")
    need(
        not (result["required"] and result["status"] == "not-applicable"),
        f"{label}.required interaction cannot be not-applicable",
    )
    _screen(result)
    return result


def _observation(
    value: Any,
    *,
    known_sources: set[str],
    known_roles: set[str],
    known_interfaces: set[str],
    index: int,
) -> dict[str, Any]:
    expected = {
        "id",
        "kind",
        "status",
        "summary",
        "source_refs",
        "role_refs",
        "interface_refs",
    }
    need(
        isinstance(value, Mapping) and set(value) == expected,
        "system-context observation has an unexpected schema",
    )
    label = f"system_context.observations[{index}]"
    kind = value["kind"]
    status = value["status"]
    need(kind in _OBSERVATION_KINDS, f"{label}.kind is invalid")
    need(status in _OBSERVATION_STATUSES, f"{label}.status is invalid")
    result = {
        "id": _id(value["id"], f"{label}.id"),
        "kind": kind,
        "status": status,
        "summary": _text(value["summary"], f"{label}.summary"),
        "source_refs": _refs(
            value["source_refs"],
            f"{label}.source_refs",
            known=known_sources,
            required=status == "observed",
        ),
        "role_refs": _refs(value["role_refs"], f"{label}.role_refs", known=known_roles),
        "interface_refs": _refs(
            value["interface_refs"], f"{label}.interface_refs", known=known_interfaces
        ),
    }
    if kind == "environment-role":
        need(bool(result["role_refs"]), f"{label}.role_refs must be nonempty")
    _screen(result)
    return result


def _acyclic_parents(questions: Mapping[str, Mapping[str, Any]]) -> None:
    pending: set[str] = set()
    complete: set[str] = set()

    def visit(question_id: str) -> None:
        if question_id in complete:
            return
        need(question_id not in pending, "research question parents must be acyclic")
        pending.add(question_id)
        for parent in questions[question_id]["parents"]:
            visit(parent)
        pending.remove(question_id)
        complete.add(question_id)

    for question_id in questions:
        visit(question_id)


def _validate_context(
    value: Any,
    research_state: Mapping[str, Any],
    machine: Any,
) -> dict[str, Any]:
    expected = {
        "version",
        "scope",
        "rationale",
        "observations",
        "roles",
        "interfaces",
        "interactions",
    }
    need(
        isinstance(value, Mapping) and set(value) == expected,
        "system_context has an unexpected schema",
    )
    need(
        type(value["version"]) is int and value["version"] == SYSTEM_CONTEXT_PROTOCOL_VERSION,
        f"system_context.version must be {SYSTEM_CONTEXT_PROTOCOL_VERSION}",
    )
    scope = value["scope"]
    need(scope in _SCOPES, "system_context.scope is invalid")
    platforms, surveyed_interfaces, platform_applicable = _survey_index(machine)
    sources = research_state["sources"]
    known_sources = {row["id"] for row in sources}
    questions = {row["id"]: row for row in research_state["questions"]}
    known_questions = set(questions)
    for question in questions.values():
        question["parents"] = _refs(
            question["parents"],
            f"research question {question['id']} parents",
            known=known_questions,
        )
        need(
            question["id"] not in question["parents"],
            f"research question {question['id']} cannot parent itself",
        )
    _acyclic_parents(questions)

    roles = [
        _role(
            row,
            known_sources=known_sources,
            known_platforms=set(platforms),
            index=index,
        )
        for index, row in enumerate(_rows(value["roles"], "system_context.roles", required=True))
    ]
    role_ids = [row["id"] for row in roles]
    need(len(role_ids) == len(set(role_ids)), "system_context roles must not duplicate IDs")
    role_by_id = {row["id"]: row for row in roles}

    interfaces = [
        _interface(
            row,
            known_sources=known_sources,
            known_roles=set(role_by_id),
            known_interfaces=surveyed_interfaces,
            index=index,
        )
        for index, row in enumerate(
            _rows(value["interfaces"], "system_context.interfaces")
        )
    ]
    interface_ids = [row["id"] for row in interfaces]
    need(
        len(interface_ids) == len(set(interface_ids)),
        "system_context interfaces must not duplicate IDs",
    )
    interface_by_id = {row["id"]: row for row in interfaces}

    interactions = [
        _interaction(
            row,
            known_sources=known_sources,
            known_roles=set(role_by_id),
            known_interfaces=interface_by_id,
            known_questions=known_questions,
            index=index,
        )
        for index, row in enumerate(
            _rows(value["interactions"], "system_context.interactions")
        )
    ]
    interaction_ids = [row["id"] for row in interactions]
    need(
        len(interaction_ids) == len(set(interaction_ids)),
        "system_context interactions must not duplicate IDs",
    )
    interaction_by_id = {row["id"]: row for row in interactions}

    for question in questions.values():
        question["contract_refs"] = _refs(
            question["contract_refs"],
            f"research question {question['id']} contract_refs",
            known=set(interaction_by_id),
        )
        question["role_refs"] = _refs(
            question["role_refs"],
            f"research question {question['id']} role_refs",
            known=set(role_by_id),
        )
        question["interface_refs"] = _refs(
            question["interface_refs"],
            f"research question {question['id']} interface_refs",
            known=set(interface_by_id),
        )
    for interaction in interactions:
        for question_id in interaction["question_refs"]:
            need(
                interaction["id"] in questions[question_id]["contract_refs"],
                "interaction/question contract links must be reciprocal",
            )
        if interaction["status"] == "resolved":
            unresolved = [
                question_id
                for question_id in interaction["question_refs"]
                if questions[question_id]["status"] in ("open", "blocked")
            ]
            need(
                not unresolved,
                "resolved interaction references unresolved question(s): "
                + ", ".join(unresolved),
            )
    for question in questions.values():
        for interaction_id in question["contract_refs"]:
            need(
                question["id"] in interaction_by_id[interaction_id]["question_refs"],
                "research question/contract links must be reciprocal",
            )

    observations = [
        _observation(
            row,
            known_sources=known_sources,
            known_roles=set(role_by_id),
            known_interfaces=set(interface_by_id),
            index=index,
        )
        for index, row in enumerate(
            _rows(value["observations"], "system_context.observations", required=True)
        )
    ]
    observation_ids = [row["id"] for row in observations]
    need(
        len(observation_ids) == len(set(observation_ids)),
        "system_context observations must not duplicate IDs",
    )
    missing_observations = sorted(
        _OBSERVATION_KINDS - {row["kind"] for row in observations}
    )
    need(
        not missing_observations,
        "system_context requires code/state/system/environment-role observations: "
        + ", ".join(missing_observations),
    )

    surveyed_pairs = {
        (ref["platform_id"], ref["name"])
        for row in interfaces
        if (ref := row["survey_ref"]) is not None
    }
    covered_platforms = {platform for row in roles for platform in row["platform_refs"]}
    if platform_applicable:
        need(scope == "integrated", "applicable surveyed platforms require integrated context")
        need(
            set(platforms).issubset(covered_platforms),
            "system_context roles must cover every applicable surveyed platform",
        )
        need(
            surveyed_interfaces.issubset(surveyed_pairs),
            "system_context interfaces must reference every selected surveyed interface",
        )
    if scope == "local-only":
        need(
            not platform_applicable,
            "local-only system context cannot omit an applicable surveyed platform",
        )
        need(
            not surveyed_pairs,
            "local-only system context cannot reference surveyed interfaces",
        )
    if scope == "integrated":
        need(bool(interfaces), "integrated system context requires an interface inventory")
        need(bool(interactions), "integrated system context requires an interaction inventory")

    return {
        "version": SYSTEM_CONTEXT_PROTOCOL_VERSION,
        "scope": scope,
        "rationale": _text(value["rationale"], "system_context.rationale"),
        "observations": observations,
        "roles": roles,
        "interfaces": interfaces,
        "interactions": interactions,
    }


def validate_context(value: Any, research_state: Any, machine: Any) -> dict[str, Any]:
    """Validate one context against extended research evidence and frozen survey IDs."""
    normalized = _base_research_state(research_state)
    return _validate_context(value, normalized, machine)


def validate_research_state(value: Any, machine: Any) -> dict[str, Any]:
    """Normalize the v1 research-state extension selected by a new run marker."""
    normalized = _base_research_state(value)
    context = _validate_context(normalized["system_context"], normalized, machine)
    return {
        "questions": normalized["questions"],
        "sources": normalized["sources"],
        "system_context": context,
    }


def blocking_ids(value: Any, machine: Any) -> list[str]:
    """Return required unresolved context boundaries without making a scheduling graph."""
    state = validate_research_state(value, machine)
    questions = {row["id"]: row for row in state["questions"]}
    blocking: set[str] = set()
    for interaction in state["system_context"]["interactions"]:
        if not interaction["required"]:
            continue
        if interaction["status"] != "resolved":
            blocking.add("interaction:" + interaction["id"])
        for question_id in interaction["question_refs"]:
            if questions[question_id]["status"] in ("open", "blocked"):
                blocking.add("question:" + question_id)
    return sorted(blocking)


def _base_only(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "questions": [
            {
                key: row[key]
                for key in (
                    "id",
                    "question",
                    "origin",
                    "status",
                    "answer",
                    "sources",
                    "revalidate",
                    "rationale",
                )
            }
            for row in value["questions"]
        ],
        "sources": value["sources"],
    }


def validate_transition(previous: Any, current: Any, machine: Any) -> None:
    """Preserve stable context identities across a complete research replacement."""
    old = validate_research_state(previous, machine)
    new = validate_research_state(current, machine)
    try:
        research.validate_transition(_base_only(old), _base_only(new))
    except research.ResearchError as exc:
        raise SystemContextError(str(exc)) from exc

    def preserve_rows(
        key: str, identity_keys: tuple[str, ...], label: str
    ) -> None:
        old_rows = {row["id"]: row for row in old["system_context"][key]}
        new_rows = {row["id"]: row for row in new["system_context"][key]}
        missing = sorted(set(old_rows) - set(new_rows))
        need(not missing, f"research apply cannot remove prior {label}: " + ", ".join(missing))
        for record_id in sorted(set(old_rows) & set(new_rows)):
            for identity_key in identity_keys:
                need(
                    old_rows[record_id][identity_key]
                    == new_rows[record_id][identity_key],
                    f"{label} {record_id} cannot change {identity_key} under a stable ID",
                )

    preserve_rows("roles", ("label",), "system-context role")
    preserve_rows("interfaces", ("identity", "survey_ref"), "system-context interface")
    preserve_rows(
        "interactions",
        ("caller_interface_id", "callee_interface_id", "operation"),
        "system-context interaction",
    )


def meaningful_change(previous: Any, current: Any, machine: Any) -> bool:
    """Classify any new system relationship as material for research convergence."""
    old = validate_research_state(previous, machine)
    new = validate_research_state(current, machine)
    try:
        if research.meaningful_change(_base_only(old), _base_only(new)):
            return True
    except research.ResearchError as exc:
        raise SystemContextError(str(exc)) from exc
    return _canonical_bytes(old["system_context"]) != _canonical_bytes(
        new["system_context"]
    ) or any(
        old_question != new_question
        for old_question, new_question in zip(
            old["questions"], new["questions"], strict=True
        )
    )


def _brief_text(value: str, limit: int = 240) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _limited(rows: list[dict[str, Any]], limit: int) -> tuple[list[dict[str, Any]], int]:
    ordered = sorted(rows, key=lambda row: row["id"])
    return ordered[:limit], max(0, len(ordered) - limit)


def _question_closure(
    questions: Mapping[str, Mapping[str, Any]], selected: set[str]
) -> set[str]:
    pending = list(selected)
    while pending:
        question_id = pending.pop()
        for parent in questions[question_id]["parents"]:
            if parent not in selected:
                selected.add(parent)
                pending.append(parent)
    return selected


def project_context(
    value: Any,
    research_state: Any,
    machine: Any,
    *,
    step_id: str | None = None,
    consumer_ids: tuple[str, ...] | list[str] = (),
    limit: int = MAX_PROJECTION_ROWS,
) -> dict[str, Any]:
    """Project selected-step contracts and direct-consumer constraints safely.

    ``consumer_ids`` is supplied by the existing DAG caller.  This helper
    filters declared consumer IDs; it does not infer or schedule graph edges.
    Exact full evidence remains at ``research-evidence.md`` when rows are
    omitted by the packet bound.
    """
    need(
        type(limit) is int and 1 <= limit <= MAX_PROJECTION_ROWS,
        f"system-context projection limit must be 1..{MAX_PROJECTION_ROWS}",
    )
    targets: set[str] = set()
    if step_id is not None:
        targets.add(_id(step_id, "system-context projection step_id"))
    need(isinstance(consumer_ids, (tuple, list)), "system-context consumer_ids must be a list")
    targets.update(
        _id(item, "system-context projection consumer ID") for item in consumer_ids
    )
    state = validate_research_state(research_state, machine)
    context = _validate_context(value, state, machine)
    questions = {row["id"]: row for row in state["questions"]}
    interactions = context["interactions"]
    selected_interactions = [
        row
        for row in interactions
        if not targets or bool(set(row["consumer_steps"]) & targets)
    ]
    selected_question_ids = _question_closure(
        questions,
        {
            question_id
            for row in selected_interactions
            for question_id in row["question_refs"]
        },
    )
    selected_interface_ids = {
        interface_id
        for row in selected_interactions
        for interface_id in (row["caller_interface_id"], row["callee_interface_id"])
    }
    interface_by_id = {row["id"]: row for row in context["interfaces"]}
    selected_role_ids = {
        role_id
        for row in selected_interactions
        for role_id in row["role_refs"]
    }
    selected_role_ids.update(
        role_id
        for interface_id in selected_interface_ids
        for role_id in interface_by_id[interface_id]["role_refs"]
    )
    selected_observations = [
        row
        for row in context["observations"]
        if not row["role_refs"]
        or bool(set(row["role_refs"]) & selected_role_ids)
        or bool(set(row["interface_refs"]) & selected_interface_ids)
    ]
    source_ids = {
        source_id
        for row in selected_interactions + selected_observations
        for source_id in row["source_refs"]
    }
    role_by_id = {row["id"]: row for row in context["roles"]}
    for role_id in selected_role_ids:
        source_ids.update(role_by_id[role_id]["source_refs"])
    for interface_id in selected_interface_ids:
        source_ids.update(interface_by_id[interface_id]["source_refs"])
    for question_id in selected_question_ids:
        source_ids.update(questions[question_id]["sources"])
    source_by_id = {row["id"]: row for row in state["sources"]}

    role_rows, role_omitted = _limited(
        [role_by_id[row_id] for row_id in selected_role_ids], limit
    )
    interface_rows, interface_omitted = _limited(
        [interface_by_id[row_id] for row_id in selected_interface_ids], limit
    )
    interaction_rows, interaction_omitted = _limited(selected_interactions, limit)
    question_rows, question_omitted = _limited(
        [questions[row_id] for row_id in selected_question_ids], limit
    )
    observation_rows, observation_omitted = _limited(selected_observations, limit)
    source_rows, source_omitted = _limited(
        [source_by_id[row_id] for row_id in source_ids], limit
    )

    def brief(row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            key: _brief_text(value) if isinstance(value, str) else value
            for key, value in row.items()
            if key not in {"supports", "limitations"}
        }

    omitted = {
        name: count
        for name, count in (
            ("roles", role_omitted),
            ("interfaces", interface_omitted),
            ("interactions", interaction_omitted),
            ("questions", question_omitted),
            ("observations", observation_omitted),
            ("sources", source_omitted),
        )
        if count
    }
    return {
        "version": SYSTEM_CONTEXT_PROTOCOL_VERSION,
        "evidence_locator": "research-evidence.md",
        "context_sha256": hashlib.sha256(_canonical_bytes(context)).hexdigest(),
        "selected_step_id": step_id,
        "direct_consumer_ids": sorted(targets - ({step_id} if step_id else set())),
        "roles": [brief(row) for row in role_rows],
        "interfaces": [brief(row) for row in interface_rows],
        "interactions": [brief(row) for row in interaction_rows],
        "questions": [brief(row) for row in question_rows],
        "observations": [brief(row) for row in observation_rows],
        "sources": [brief(row) for row in source_rows],
        "blocking_ids": blocking_ids(state, machine),
        "omitted": omitted,
    }


def read_evidence_binding(root: Path | str, state: Any, machine: Any) -> dict[str, Any]:
    """Read and bind the current evidence file for later plan identity checks."""
    if not context_current(state):
        return {"legacy": True}
    path = Path(root) / "research-evidence.md"
    need(
        path.is_file() and not path.is_symlink(),
        "missing regular research-evidence.md for system-context binding",
    )
    try:
        typed = validate_research_state(store.read_record(path), machine)
    except UnicodeError as exc:
        raise SystemContextError("research evidence is not UTF-8 Markdown") from exc
    context = typed["system_context"]
    return {
        "system_context_protocol_version": SYSTEM_CONTEXT_PROTOCOL_VERSION,
        "research_evidence_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "context_sha256": hashlib.sha256(_canonical_bytes(context)).hexdigest(),
        "question_ids": [row["id"] for row in typed["questions"]],
        "role_ids": [row["id"] for row in context["roles"]],
        "interface_ids": [row["id"] for row in context["interfaces"]],
        "interaction_ids": [row["id"] for row in context["interactions"]],
        "blocking_ids": blocking_ids(typed, machine),
    }
