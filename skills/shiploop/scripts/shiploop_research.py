"""Typed, Markdown-backed research evidence for ShipLoop convergence.

The protocol owns actions, Git facts, and transactions.  This module only
normalizes the compact question/source state that accompanies a potentially
large free-form research report.  It deliberately does not judge whether a
source is true or whether the host interpreted it correctly.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import shiploop_knowledge as knowledge
import shiploop_store as store


QUESTION_STATUSES = ("resolved", "open", "blocked", "not-applicable")
SOURCE_AUTHORITIES = ("primary", "local", "secondary", "probe")
RUBRIC = (
    "prompt_coverage",
    "environment_conditions",
    "source_quality",
    "contradictions",
    "best_practices",
    "access_readiness",
    "invocation_contracts",
    "test_deploy_feasibility",
    "remaining_unknowns",
)
ASSESSMENT_STATUSES = ("not-needed", "resolved", "required", "blocked")
MAX_ROWS = 64
MAX_REFS = 24
_ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9._:-]{0,159}\Z")


class ResearchError(ValueError):
    """A research candidate or execution assessment is invalid."""


def need(ok: bool, message: str) -> None:
    if not ok:
        raise ResearchError(message)


def _text(value: Any, label: str) -> str:
    need(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty")
    text = value.strip()
    # Research reports may be large.  The typed evidence is intentionally
    # compact so it remains safe and useful in cold-context packets.
    need(len(text) <= knowledge.MAX_TEXT, f"{label} exceeds the bounded evidence limit")
    return text


def _id(value: Any, label: str) -> str:
    need(
        isinstance(value, str) and _ID_RE.fullmatch(value),
        f"{label} must be a stable safe identifier",
    )
    return value


def _freshness(value: Any, label: str) -> str:
    text = _text(value, label)
    need(
        text.casefold() not in {"unknown", "tbd", "none"},
        f"{label} must record a real version, observation, or revalidation trigger",
    )
    return text


def _copy(value: Any) -> Any:
    return json.loads(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def script_as_of() -> str:
    """Script-recorded finalization time, distinct from source freshness."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _safe_rows(value: Any, label: str) -> list[Any]:
    need(isinstance(value, list), f"{label} must be a list")
    need(len(value) <= MAX_ROWS, f"{label} exceeds the bounded evidence limit")
    return value


def _safe_refs(value: Any, label: str, *, required: bool) -> list[str]:
    need(isinstance(value, list), f"{label} must be a list")
    need(len(value) <= MAX_REFS, f"{label} exceeds the bounded evidence limit")
    refs = [_text(item, f"{label} entry") for item in value]
    need(len(set(refs)) == len(refs), f"{label} must not duplicate entries")
    if required:
        need(bool(refs), f"{label} must be nonempty")
    # The carry-forward screen is deliberately reused only for bounded,
    # structured references; never apply it to the free-form report body.
    knowledge.screen_payload({"references": refs})
    return refs


def _source(value: Any) -> dict[str, str]:
    expected = {
        "id",
        "reference",
        "authority",
        "version_or_observed_at",
        "supports",
        "limitations",
    }
    need(
        isinstance(value, Mapping) and set(value) == expected,
        "research source has an unexpected schema",
    )
    authority = value["authority"]
    need(authority in SOURCE_AUTHORITIES, "research source authority is invalid")
    result = {
        "id": _id(value["id"], "research source id"),
        "reference": _text(value["reference"], "research source reference"),
        "authority": authority,
        "version_or_observed_at": _freshness(
            value["version_or_observed_at"], "research source version_or_observed_at"
        ),
        "supports": _text(value["supports"], "research source supports"),
        "limitations": _text(value["limitations"], "research source limitations"),
    }
    knowledge.screen_payload(result)
    return result


def _question(value: Any) -> dict[str, Any]:
    expected = {
        "id",
        "question",
        "origin",
        "status",
        "answer",
        "sources",
        "revalidate",
        "rationale",
    }
    need(
        isinstance(value, Mapping) and set(value) == expected,
        "research question has an unexpected schema",
    )
    status = value["status"]
    need(status in QUESTION_STATUSES, "research question status is invalid")
    origin = _text(value["origin"], "research question origin")
    need(
        re.search(r"\b(?:prompt|spec|discovery)\b", origin, flags=re.IGNORECASE)
        is not None,
        "research question origin must reference prompt, spec, or discovery",
    )
    sources = _safe_refs(value["sources"], "research question sources", required=False)
    if status == "resolved":
        need(bool(sources), "resolved research question requires supporting sources")
    result = {
        "id": _id(value["id"], "research question id"),
        "question": _text(value["question"], "research question"),
        "origin": origin,
        "status": status,
        # For open/blocked this is the concrete gap; for not-applicable it is
        # the required N/A reason.  A single field keeps the durable schema
        # compact while preserving optional positive source support for an
        # applicability decision.
        "answer": _text(value["answer"], "research question answer or gap"),
        "sources": sources,
        "revalidate": _freshness(value["revalidate"], "research question revalidate"),
        "rationale": _text(value["rationale"], "research question rationale"),
    }
    knowledge.screen_payload(result)
    return result


def _system_context_adapter(machine: Any, enabled: bool):
    """Load the optional v1 extension lazily to preserve legacy import shape."""
    if not enabled:
        return None
    need(machine is not None, "system-context research validation requires machine")
    import shiploop_system_context as system_context

    return system_context


def validate_state(
    value: Any,
    *,
    machine: Any = None,
    system_context_enabled: bool = False,
) -> dict[str, Any]:
    """Normalize source/question evidence without screening report prose.

    Existing callers receive the exact original two-key schema.  New callers
    must explicitly select the system-context extension through the run marker
    and pass the frozen survey machine for reference validation.
    """
    system_context = _system_context_adapter(machine, system_context_enabled)
    if system_context is not None:
        try:
            return system_context.validate_research_state(value, machine)
        except system_context.SystemContextError as exc:
            raise ResearchError(str(exc)) from exc
    expected = {"questions", "sources"}
    need(
        isinstance(value, Mapping) and set(value) == expected,
        "research_state has an unexpected schema",
    )
    questions = [_question(row) for row in _safe_rows(value["questions"], "research questions")]
    sources = [_source(row) for row in _safe_rows(value["sources"], "research sources")]
    need(bool(questions), "research_state requires an explicit bounded question inventory")
    question_ids = [row["id"] for row in questions]
    source_ids = [row["id"] for row in sources]
    need(len(set(question_ids)) == len(question_ids), "research questions must not duplicate stable IDs")
    need(len(set(source_ids)) == len(source_ids), "research sources must not duplicate stable IDs")
    known_sources = set(source_ids)
    for question in questions:
        need(
            set(question["sources"]).issubset(known_sources),
            f"research question {question['id']} names an unknown source ID",
        )
    return {"questions": questions, "sources": sources}


def render_state(
    value: Mapping[str, Any],
    *,
    machine: Any = None,
    system_context_enabled: bool = False,
) -> str:
    return store.dumps(
        validate_state(
            value,
            machine=machine,
            system_context_enabled=system_context_enabled,
        ),
        "ShipLoop research evidence — host reported",
    )


def read_state(
    root: Path,
    *,
    machine: Any = None,
    system_context_enabled: bool = False,
) -> dict[str, Any]:
    path = root / "research-evidence.md"
    need(path.is_file() and not path.is_symlink(), "missing research-evidence.md")
    try:
        return validate_state(
            store.read_record(path),
            machine=machine,
            system_context_enabled=system_context_enabled,
        )
    except UnicodeError as exc:
        raise ResearchError("research evidence is not UTF-8 Markdown") from exc


def validate_transition(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    *,
    machine: Any = None,
    system_context_enabled: bool = False,
) -> None:
    """Preserve question/source identity across supported research apply actions."""
    system_context = _system_context_adapter(machine, system_context_enabled)
    if system_context is not None:
        try:
            system_context.validate_transition(previous, current, machine)
            return
        except system_context.SystemContextError as exc:
            raise ResearchError(str(exc)) from exc
    old = validate_state(previous)
    new = validate_state(current)
    old_questions = {row["id"]: row for row in old["questions"]}
    new_questions = {row["id"]: row for row in new["questions"]}
    missing = sorted(set(old_questions) - set(new_questions))
    need(
        not missing,
        "research apply cannot remove prior questions: " + ", ".join(missing),
    )
    old_sources = {row["id"]: row for row in old["sources"]}
    new_sources = {row["id"]: row for row in new["sources"]}
    missing_sources = sorted(set(old_sources) - set(new_sources))
    need(
        not missing_sources,
        "research apply cannot remove prior sources: " + ", ".join(missing_sources),
    )
    for source_id in sorted(set(old_sources).intersection(new_sources)):
        before, after = old_sources[source_id], new_sources[source_id]
        need(
            before["reference"] == after["reference"]
            and before["authority"] == after["authority"],
            f"research source {source_id} cannot change reference or authority under a stable ID",
        )


def meaningful_change(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    *,
    machine: Any = None,
    system_context_enabled: bool = False,
) -> bool:
    """Conservatively classify semantic research changes for the trivial streak."""
    system_context = _system_context_adapter(machine, system_context_enabled)
    if system_context is not None:
        try:
            return system_context.meaningful_change(previous, current, machine)
        except system_context.SystemContextError as exc:
            raise ResearchError(str(exc)) from exc
    old = validate_state(previous)
    new = validate_state(current)
    old_questions = {row["id"]: row for row in old["questions"]}
    new_questions = {row["id"]: row for row in new["questions"]}
    if set(old_questions) != set(new_questions):
        return True
    for question_id, before in old_questions.items():
        after = new_questions[question_id]
        if any(
            before[key] != after[key]
            for key in (
                "question",
                "origin",
                "status",
                "answer",
                "sources",
                "revalidate",
                "rationale",
            )
        ):
            return True
    old_sources = {row["id"]: row for row in old["sources"]}
    new_sources = {row["id"]: row for row in new["sources"]}
    if set(old_sources) != set(new_sources):
        return True
    # A freshness/version refresh alone is corroboration, not automatically a
    # new conclusion.  Any changed identity, support, or limitation is not.
    for source_id, before in old_sources.items():
        after = new_sources[source_id]
        if any(
            before[key] != after[key]
            for key in ("reference", "authority", "supports", "limitations")
        ):
            return True
    return False


def unresolved_ids(
    value: Mapping[str, Any],
    *,
    machine: Any = None,
    system_context_enabled: bool = False,
) -> list[str]:
    state = validate_state(
        value,
        machine=machine,
        system_context_enabled=system_context_enabled,
    )
    unresolved = [
        row["id"]
        for row in state["questions"]
        if row["status"] in ("open", "blocked")
    ]
    if system_context_enabled:
        system_context = _system_context_adapter(machine, True)
        try:
            unresolved.extend(
                item
                for item in system_context.blocking_ids(state, machine)
                if item.startswith("interaction:")
            )
        except system_context.SystemContextError as exc:
            raise ResearchError(str(exc)) from exc
    return unresolved


def validate_assessment(value: Any) -> dict[str, Any]:
    expected = {"status", "summary", "evidence", "questions"}
    need(
        isinstance(value, Mapping) and set(value) == expected,
        "research_assessment has an unexpected schema",
    )
    status = value["status"]
    need(status in ASSESSMENT_STATUSES, "research_assessment status is invalid")
    requires_detail = status != "not-needed"
    result = {
        "status": status,
        "summary": _text(value["summary"], "research_assessment summary"),
        "evidence": _safe_refs(
            value["evidence"], "research_assessment evidence", required=requires_detail
        ),
        "questions": _safe_refs(
            value["questions"], "research_assessment questions", required=requires_detail
        ),
    }
    knowledge.screen_payload(result)
    return result
