"""Pure, Markdown-authoritative outer-work obligations for ShipLoop.

The protocol owns files, action transitions, paging, and permission checks.
This module only validates and evolves a bounded record that can be rendered to
``outer-work.md``.  It never contacts a target or makes deployment, publication,
or handoff effects happen.

Each accepted inner-stage request becomes one immutable event and one request
receipt.  Effective entries are deterministically derived from those events,
so a later renderer cannot silently mark required outer work complete.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

import shiploop_knowledge as knowledge
import shiploop_privacy as privacy
import shiploop_store as store


VERSION = 1
OUTER_STAGES = ("quality", "publish", "handoff")
MAX_EVENTS = 128
MAX_ENTRIES = 48
MAX_PREREQUISITES = 16

_ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9._:-]{0,159}\Z")
_ACTION_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}\Z")
_STAGE_RE = re.compile(r"[a-z][a-z0-9-]{0,79}\Z")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")

_REQUEST_FIELDS = frozenset(
    (
        "request_id",
        "expected_revision",
        "entry_id",
        "dedupe_key",
        "required_action",
        "target_stage",
        "target_alias",
        "prerequisites",
        "expected_outcome",
        "evidence",
        "authority_limitations",
        "rationale",
    )
)
_DEPENDENCY_FIELDS = (
    "entry_id",
    "dedupe_key",
    "required_action",
    "target_stage",
    "target_alias",
    "prerequisites",
    "expected_outcome",
    "evidence",
    "authority_limitations",
    "rationale",
)
_PROVENANCE_FIELDS = frozenset(("parent_action", "parent_step", "parent_stage"))
_RESOLUTION_FIELDS = frozenset(("entry_id", "expected_revision", "evidence", "reason"))
_RECEIPT_FIELDS = frozenset(
    ("request_id", "entry_id", "dedupe_key", "revision", "outcome", "obligation_created")
)
_ENTRY_FIELDS = frozenset(
    (
        "id",
        "dedupe_key",
        "required_action",
        "target_stage",
        "target_alias",
        "prerequisites",
        "expected_outcome",
        "evidence",
        "authority_limitations",
        "rationale",
        "status",
        "opened_by",
        "updated_by",
        "opened_revision",
        "updated_revision",
    )
)
_RESOLVED_ENTRY_FIELDS = _ENTRY_FIELDS | frozenset(("resolution",))


class OuterWorkError(ValueError):
    """Raised when an outer-work record or transition is unsafe or invalid."""


def need(ok: bool, message: str) -> None:
    if not ok:
        raise OuterWorkError(message)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _copy(value: Any) -> Any:
    return json.loads(_canonical(value).decode("utf-8"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _screen(value: Any) -> None:
    """Screen every bounded outer-work string without adopting knowledge row caps.

    The knowledge helper intentionally caps arbitrary discovery lists at 24.
    Outer work has a separately documented 128-event cap, so pass individual
    strings through that helper while this schema validates its own container
    sizes and fixed nesting shape.
    """
    def visit(item: Any, depth: int) -> None:
        need(depth <= 8, "outer-work payload nesting exceeds the bounded limit")
        if isinstance(item, str):
            try:
                knowledge.screen_payload(item)
            except knowledge.KnowledgeError as exc:
                raise OuterWorkError(str(exc)) from exc
        elif isinstance(item, Mapping):
            need(len(item) <= 16, "outer-work payload exceeds the bounded object limit")
            for key, child in item.items():
                need(isinstance(key, str), "outer-work payload has a non-string key")
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif isinstance(item, list):
            # Specific record validators own the event, entry, and prerequisite
            # limits; do not impose the knowledge discovery-list cap here.
            for child in item:
                visit(child, depth + 1)

    visit(value, 0)


def _text(value: Any, label: str) -> str:
    need(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty")
    text = value.strip()
    need(
        len(text) <= knowledge.MAX_TEXT,
        f"{label} exceeds the bounded outer-work text limit",
    )
    need(_CONTROL_RE.search(text) is None, f"{label} must be a one-line safe string")
    need(
        not privacy.sensitive_text(text),
        f"{label} appears to contain a credential secret",
    )
    _screen(text)
    return text


def _id(value: Any, label: str) -> str:
    need(
        isinstance(value, str) and _ID_RE.fullmatch(value) is not None,
        f"{label} must be a stable safe identifier",
    )
    need(
        not privacy.sensitive_text(value),
        f"{label} appears to contain a credential secret",
    )
    _screen(value)
    return value


def _revision(value: Any, label: str) -> int:
    need(type(value) is int and value >= 0, f"{label} must be a nonnegative integer")
    return value


def _target_stage(value: Any, label: str = "target_stage") -> str:
    need(value in OUTER_STAGES, f"{label} must be one of: {', '.join(OUTER_STAGES)}")
    return value


def _parent_stage(value: Any, label: str = "parent_stage") -> str:
    text = _text(value, label)
    need(_STAGE_RE.fullmatch(text) is not None, f"{label} must be a safe stage name")
    return text


def _texts(value: Any, label: str) -> list[str]:
    need(isinstance(value, list), f"{label} must be a list")
    need(len(value) <= MAX_PREREQUISITES, f"{label} exceeds the bounded outer-work limit")
    rows = [_text(item, f"{label} entry") for item in value]
    need(len(rows) == len(set(rows)), f"{label} must not duplicate entries")
    return rows


def _provenance(value: Any) -> dict[str, Any]:
    need(
        isinstance(value, Mapping) and set(value) == _PROVENANCE_FIELDS,
        "outer-work provenance has an unexpected schema",
    )
    step = value["parent_step"]
    need(
        step is None or (isinstance(step, str) and _ID_RE.fullmatch(step) is not None),
        "outer-work provenance parent_step must be null or a stable safe identifier",
    )
    if isinstance(step, str):
        _id(step, "outer-work provenance parent_step")
    parent_action = _text(value["parent_action"], "outer-work provenance parent_action")
    need(
        _ACTION_ID_RE.fullmatch(parent_action) is not None,
        "outer-work provenance parent_action must be a stable safe identifier",
    )
    result = {
        "parent_action": parent_action,
        "parent_step": step,
        "parent_stage": _parent_stage(value["parent_stage"], "outer-work provenance parent_stage"),
    }
    _screen(result)
    return result


def _request(value: Any) -> dict[str, Any]:
    need(
        isinstance(value, Mapping) and set(value) == _REQUEST_FIELDS,
        "outer-work request has an unexpected schema",
    )
    result = {
        "request_id": _id(value["request_id"], "outer-work request_id"),
        "expected_revision": _revision(
            value["expected_revision"], "outer-work expected_revision"
        ),
        "entry_id": _id(value["entry_id"], "outer-work entry_id"),
        "dedupe_key": _id(value["dedupe_key"], "outer-work dedupe_key"),
        "required_action": _text(value["required_action"], "outer-work required_action"),
        "target_stage": _target_stage(value["target_stage"]),
        "target_alias": _text(value["target_alias"], "outer-work target_alias"),
        "prerequisites": _texts(value["prerequisites"], "outer-work prerequisites"),
        "expected_outcome": _text(
            value["expected_outcome"], "outer-work expected_outcome"
        ),
        "evidence": _text(value["evidence"], "outer-work evidence"),
        "authority_limitations": _text(
            value["authority_limitations"], "outer-work authority_limitations"
        ),
        "rationale": _text(value["rationale"], "outer-work rationale"),
    }
    _screen(result)
    return result


def _resolution(value: Any) -> dict[str, Any]:
    need(
        isinstance(value, Mapping) and set(value) == _RESOLUTION_FIELDS,
        "outer-work resolution has an unexpected schema",
    )
    result = {
        "entry_id": _id(value["entry_id"], "outer-work resolution entry_id"),
        "expected_revision": _revision(
            value["expected_revision"], "outer-work resolution expected_revision"
        ),
        "evidence": _text(value["evidence"], "outer-work resolution evidence"),
        "reason": _text(value["reason"], "outer-work resolution reason"),
    }
    _screen(result)
    return result


def _dependency_from_request(request: Mapping[str, Any]) -> dict[str, Any]:
    return {field: _copy(request[field]) for field in _DEPENDENCY_FIELDS}


def _dependency_from_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "entry_id": entry["id"],
        "dedupe_key": entry["dedupe_key"],
        "required_action": entry["required_action"],
        "target_stage": entry["target_stage"],
        "target_alias": entry["target_alias"],
        "prerequisites": _copy(entry["prerequisites"]),
        "expected_outcome": entry["expected_outcome"],
        "evidence": entry["evidence"],
        "authority_limitations": entry["authority_limitations"],
        "rationale": entry["rationale"],
    }


def _request_fingerprint(request: Mapping[str, Any], provenance: Mapping[str, Any]) -> str:
    return _digest({"request": request, "provenance": provenance})


def _dependency_fingerprint(request: Mapping[str, Any]) -> str:
    return _digest(_dependency_from_request(request))


def _entry_from_request(
    request: Mapping[str, Any], provenance: Mapping[str, Any], revision: int
) -> dict[str, Any]:
    dependency = _dependency_from_request(request)
    return {
        "id": dependency.pop("entry_id"),
        **dependency,
        "status": "planned",
        "opened_by": _copy(provenance),
        "updated_by": _copy(provenance),
        "opened_revision": revision,
        "updated_revision": revision,
    }


def _updated_entry(
    prior: Mapping[str, Any], request: Mapping[str, Any], provenance: Mapping[str, Any], revision: int
) -> dict[str, Any]:
    entry = _entry_from_request(request, provenance, revision)
    entry["opened_by"] = _copy(prior["opened_by"])
    entry["opened_revision"] = prior["opened_revision"]
    return entry


def _resolution_record(
    resolution: Mapping[str, Any], provenance: Mapping[str, Any], revision: int
) -> dict[str, Any]:
    return {
        "evidence": resolution["evidence"],
        "reason": resolution["reason"],
        "provenance": _copy(provenance),
        "resolved_revision": revision,
    }


def _entry(value: Any) -> dict[str, Any]:
    need(isinstance(value, Mapping), "outer-work effective entry is invalid")
    status = value.get("status")
    expected = _RESOLVED_ENTRY_FIELDS if status == "resolved" else _ENTRY_FIELDS
    need(
        set(value) == expected,
        "outer-work effective entry has an unexpected schema",
    )
    need(status in ("planned", "resolved"), "outer-work entry status is invalid")
    result = {
        "id": _id(value["id"], "outer-work entry id"),
        "dedupe_key": _id(value["dedupe_key"], "outer-work entry dedupe_key"),
        "required_action": _text(value["required_action"], "outer-work entry required_action"),
        "target_stage": _target_stage(value["target_stage"], "outer-work entry target_stage"),
        "target_alias": _text(value["target_alias"], "outer-work entry target_alias"),
        "prerequisites": _texts(value["prerequisites"], "outer-work entry prerequisites"),
        "expected_outcome": _text(
            value["expected_outcome"], "outer-work entry expected_outcome"
        ),
        "evidence": _text(value["evidence"], "outer-work entry evidence"),
        "authority_limitations": _text(
            value["authority_limitations"], "outer-work entry authority_limitations"
        ),
        "rationale": _text(value["rationale"], "outer-work entry rationale"),
        "status": status,
        "opened_by": _provenance(value["opened_by"]),
        "updated_by": _provenance(value["updated_by"]),
        "opened_revision": _revision(
            value["opened_revision"], "outer-work entry opened_revision"
        ),
        "updated_revision": _revision(
            value["updated_revision"], "outer-work entry updated_revision"
        ),
    }
    need(
        result["opened_revision"] <= result["updated_revision"],
        "outer-work entry revisions are inconsistent",
    )
    if status == "resolved":
        raw_resolution = value["resolution"]
        expected_resolution = frozenset(
            ("evidence", "reason", "provenance", "resolved_revision")
        )
        need(
            isinstance(raw_resolution, Mapping) and set(raw_resolution) == expected_resolution,
            "outer-work entry resolution has an unexpected schema",
        )
        resolution = {
            "evidence": _text(
                raw_resolution["evidence"], "outer-work entry resolution evidence"
            ),
            "reason": _text(raw_resolution["reason"], "outer-work entry resolution reason"),
            "provenance": _provenance(raw_resolution["provenance"]),
            "resolved_revision": _revision(
                raw_resolution["resolved_revision"],
                "outer-work entry resolution resolved_revision",
            ),
        }
        need(
            resolution["resolved_revision"] == result["updated_revision"],
            "outer-work entry resolution must match its latest revision",
        )
        need(
            resolution["provenance"] == result["updated_by"],
            "outer-work entry resolution provenance must match its latest update",
        )
        result["resolution"] = resolution
    _screen(result)
    return result


def _entry_sort_key(entry: Mapping[str, Any]) -> tuple[int, str, str]:
    return (OUTER_STAGES.index(entry["target_stage"]), entry["dedupe_key"], entry["id"])


def _receipt(
    value: Any,
    request: Mapping[str, Any],
    *,
    revision: int,
    outcome: str,
    obligation_created: bool,
) -> dict[str, Any]:
    need(
        isinstance(value, Mapping) and set(value) == _RECEIPT_FIELDS,
        "outer-work request receipt has an unexpected schema",
    )
    result = {
        "request_id": _id(value["request_id"], "outer-work receipt request_id"),
        "entry_id": _id(value["entry_id"], "outer-work receipt entry_id"),
        "dedupe_key": _id(value["dedupe_key"], "outer-work receipt dedupe_key"),
        "revision": _revision(value["revision"], "outer-work receipt revision"),
        "outcome": value["outcome"],
        "obligation_created": value["obligation_created"],
    }
    need(result["outcome"] == outcome, "outer-work request receipt outcome is inconsistent")
    need(
        type(result["obligation_created"]) is bool
        and result["obligation_created"] is obligation_created,
        "outer-work request receipt obligation_created is inconsistent",
    )
    need(
        result["request_id"] == request["request_id"]
        and result["entry_id"] == request["entry_id"]
        and result["dedupe_key"] == request["dedupe_key"]
        and result["revision"] == revision,
        "outer-work request receipt does not match its request",
    )
    return result


def _append_receipt(request: Mapping[str, Any], revision: int, outcome: str) -> dict[str, Any]:
    return {
        "request_id": request["request_id"],
        "entry_id": request["entry_id"],
        "dedupe_key": request["dedupe_key"],
        "revision": revision,
        "outcome": outcome,
        "obligation_created": outcome == "created",
    }


def _event_append(
    value: Any,
    *,
    previous_revision: int,
    entries_by_id: dict[str, dict[str, Any]],
    entries_by_key: dict[str, dict[str, Any]],
    request_ids: set[str],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    expected = frozenset(
        (
            "kind",
            "revision",
            "request",
            "provenance",
            "request_sha256",
            "dependency_sha256",
            "receipt",
        )
    )
    need(
        isinstance(value, Mapping) and set(value) == expected,
        "outer-work append event has an unexpected schema",
    )
    need(value["kind"] == "append", "outer-work append event kind is invalid")
    revision = _revision(value["revision"], "outer-work append event revision")
    need(
        revision == previous_revision + 1,
        "outer-work events must have contiguous revisions",
    )
    request = _request(value["request"])
    provenance = _provenance(value["provenance"])
    need(
        request["expected_revision"] == previous_revision,
        "outer-work append event expected_revision is stale",
    )
    need(
        request["request_id"] not in request_ids,
        "outer-work events duplicate a request_id",
    )
    request_sha256 = value["request_sha256"]
    dependency_sha256 = value["dependency_sha256"]
    need(
        isinstance(request_sha256, str)
        and _SHA256_RE.fullmatch(request_sha256) is not None
        and request_sha256 == _request_fingerprint(request, provenance),
        "outer-work append event request fingerprint is invalid",
    )
    need(
        isinstance(dependency_sha256, str)
        and _SHA256_RE.fullmatch(dependency_sha256) is not None
        and dependency_sha256 == _dependency_fingerprint(request),
        "outer-work append event dependency fingerprint is invalid",
    )

    by_id = dict(entries_by_id)
    by_key = dict(entries_by_key)
    current_id = by_id.get(request["entry_id"])
    current_key = by_key.get(request["dedupe_key"])
    need(
        not (current_id is not None and current_key is not None and current_id is not current_key),
        "outer-work stable entry ID and dedupe key disagree",
    )
    need(
        current_id is None or current_id["dedupe_key"] == request["dedupe_key"],
        "outer-work entry ID cannot change dedupe_key",
    )
    need(
        current_key is None or current_key["id"] == request["entry_id"],
        "outer-work dedupe_key cannot change entry ID",
    )
    current = current_id or current_key
    if current is None:
        outcome = "created"
        updated = _entry_from_request(request, provenance, revision)
        by_id[updated["id"]] = updated
        by_key[updated["dedupe_key"]] = updated
    elif _dependency_fingerprint(request) == _digest(_dependency_from_entry(current)):
        outcome = "duplicate"
    else:
        outcome = "reopened" if current["status"] == "resolved" else "updated"
        updated = _updated_entry(current, request, provenance, revision)
        by_id[updated["id"]] = updated
        by_key[updated["dedupe_key"]] = updated

    receipt = _receipt(
        value["receipt"],
        request,
        revision=revision,
        outcome=outcome,
        obligation_created=outcome == "created",
    )
    event = {
        "kind": "append",
        "revision": revision,
        "request": request,
        "provenance": provenance,
        "request_sha256": request_sha256,
        "dependency_sha256": dependency_sha256,
        "receipt": receipt,
    }
    _screen(event)
    request_ids.add(request["request_id"])
    return event, by_id, by_key


def _event_resolve(
    value: Any,
    *,
    previous_revision: int,
    entries_by_id: dict[str, dict[str, Any]],
    entries_by_key: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    expected = frozenset(("kind", "revision", "resolution", "provenance"))
    need(
        isinstance(value, Mapping) and set(value) == expected,
        "outer-work resolve event has an unexpected schema",
    )
    need(value["kind"] == "resolve", "outer-work resolve event kind is invalid")
    revision = _revision(value["revision"], "outer-work resolve event revision")
    need(
        revision == previous_revision + 1,
        "outer-work events must have contiguous revisions",
    )
    resolution = _resolution(value["resolution"])
    provenance = _provenance(value["provenance"])
    need(
        resolution["expected_revision"] == previous_revision,
        "outer-work resolution expected_revision is stale",
    )
    current = entries_by_id.get(resolution["entry_id"])
    need(current is not None, "outer-work resolution names an unknown entry")
    need(
        current["status"] == "planned",
        "outer-work resolution requires a planned entry",
    )
    need(
        provenance["parent_stage"] == current["target_stage"],
        "outer-work resolution requires the matching target stage",
    )
    by_id = dict(entries_by_id)
    by_key = dict(entries_by_key)
    updated = _copy(current)
    updated.update(
        status="resolved",
        updated_by=_copy(provenance),
        updated_revision=revision,
        resolution=_resolution_record(resolution, provenance, revision),
    )
    by_id[updated["id"]] = updated
    by_key[updated["dedupe_key"]] = updated
    event = {
        "kind": "resolve",
        "revision": revision,
        "resolution": resolution,
        "provenance": provenance,
    }
    _screen(event)
    return event, by_id, by_key


def _derive_events(value: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    need(isinstance(value, list), "outer-work events must be a list")
    need(len(value) <= MAX_EVENTS, "outer-work events exceed the bounded limit")
    revision = 0
    request_ids: set[str] = set()
    entries_by_id: dict[str, dict[str, Any]] = {}
    entries_by_key: dict[str, dict[str, Any]] = {}
    events: list[dict[str, Any]] = []
    for raw_event in value:
        need(isinstance(raw_event, Mapping), "outer-work event is invalid")
        kind = raw_event.get("kind")
        if kind == "append":
            event, entries_by_id, entries_by_key = _event_append(
                raw_event,
                previous_revision=revision,
                entries_by_id=entries_by_id,
                entries_by_key=entries_by_key,
                request_ids=request_ids,
            )
        elif kind == "resolve":
            event, entries_by_id, entries_by_key = _event_resolve(
                raw_event,
                previous_revision=revision,
                entries_by_id=entries_by_id,
                entries_by_key=entries_by_key,
            )
        else:
            raise OuterWorkError("outer-work event kind is invalid")
        revision = event["revision"]
        events.append(event)
    need(len(entries_by_id) <= MAX_ENTRIES, "outer-work entries exceed the bounded limit")
    entries = sorted(entries_by_id.values(), key=_entry_sort_key)
    return events, entries


def empty() -> dict[str, Any]:
    """Return the only valid zero-revision outer-work ledger."""
    return {"version": VERSION, "revision": 0, "events": [], "entries": []}


def validate(ledger: Any) -> dict[str, Any]:
    """Return a normalized ledger only when its events prove its entries."""
    expected = frozenset(("version", "revision", "events", "entries"))
    need(
        isinstance(ledger, Mapping) and set(ledger) == expected,
        "outer-work ledger has an unexpected schema",
    )
    need(
        type(ledger["version"]) is int and ledger["version"] == VERSION,
        "outer-work ledger has an unsupported version",
    )
    revision = _revision(ledger["revision"], "outer-work ledger revision")
    events, derived_entries = _derive_events(ledger["events"])
    need(
        revision == len(events),
        "outer-work ledger revision does not match its append-only events",
    )
    need(isinstance(ledger["entries"], list), "outer-work ledger entries must be a list")
    need(len(ledger["entries"]) <= MAX_ENTRIES, "outer-work entries exceed the bounded limit")
    supplied_entries = [_entry(row) for row in ledger["entries"]]
    need(
        _canonical(supplied_entries) == _canonical(derived_entries),
        "outer-work effective entries do not match the append-only events",
    )
    result = {
        "version": VERSION,
        "revision": revision,
        "events": events,
        "entries": derived_entries,
    }
    _screen(result)
    return result


def render(ledger: Mapping[str, Any]) -> str:
    """Render the one authoritative ``outer-work.md`` record."""
    return store.dumps(validate(ledger), "ShipLoop outer work — script-maintained")


def append(
    ledger: Mapping[str, Any], request: Mapping[str, Any], provenance: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Append one request event or return its immutable idempotent receipt.

    A matching request ID must replay exactly.  A new request with equal
    dependency details receives a duplicate receipt without a second effective
    obligation; changed details replace the effective entry and reopen it when
    it had been resolved.
    """
    current = validate(ledger)
    normalized_request = _request(request)
    normalized_provenance = _provenance(provenance)
    for event in current["events"]:
        if event["kind"] != "append":
            continue
        if event["request"]["request_id"] != normalized_request["request_id"]:
            continue
        if (
            event["request"] == normalized_request
            and event["provenance"] == normalized_provenance
        ):
            return current, _copy(event["receipt"])
        raise OuterWorkError("outer-work request_id replay changed after receipt")
    need(
        normalized_request["expected_revision"] == current["revision"],
        "stale outer-work revision; retrieve current outer-work.md and retry",
    )

    entries_by_id = {entry["id"]: entry for entry in current["entries"]}
    entries_by_key = {entry["dedupe_key"]: entry for entry in current["entries"]}
    existing_id = entries_by_id.get(normalized_request["entry_id"])
    existing_key = entries_by_key.get(normalized_request["dedupe_key"])
    need(
        not (existing_id is not None and existing_key is not None and existing_id is not existing_key),
        "outer-work stable entry ID and dedupe key disagree",
    )
    need(
        existing_id is None
        or existing_id["dedupe_key"] == normalized_request["dedupe_key"],
        "outer-work entry ID cannot change dedupe_key",
    )
    need(
        existing_key is None or existing_key["id"] == normalized_request["entry_id"],
        "outer-work dedupe_key cannot change entry ID",
    )
    existing = existing_id or existing_key
    if existing is None:
        outcome = "created"
    elif _dependency_fingerprint(normalized_request) == _digest(
        _dependency_from_entry(existing)
    ):
        outcome = "duplicate"
    else:
        outcome = "reopened" if existing["status"] == "resolved" else "updated"

    next_revision = current["revision"] + 1
    receipt = _append_receipt(normalized_request, next_revision, outcome)
    event = {
        "kind": "append",
        "revision": next_revision,
        "request": normalized_request,
        "provenance": normalized_provenance,
        "request_sha256": _request_fingerprint(
            normalized_request, normalized_provenance
        ),
        "dependency_sha256": _dependency_fingerprint(normalized_request),
        "receipt": receipt,
    }
    events = [*current["events"], event]
    normalized_events, entries = _derive_events(events)
    next_ledger = validate(
        {
            "version": VERSION,
            "revision": next_revision,
            "events": normalized_events,
            "entries": entries,
        }
    )
    return next_ledger, _copy(receipt)


def select(
    ledger: Mapping[str, Any], target_stage: str | None = None
) -> list[dict[str, Any]]:
    """Return deterministic effective rows, optionally due through one stage."""
    current = validate(ledger)
    if target_stage is None:
        return _copy(current["entries"])
    stage = _target_stage(target_stage)
    maximum = OUTER_STAGES.index(stage)
    return _copy(
        [
            entry
            for entry in current["entries"]
            if OUTER_STAGES.index(entry["target_stage"]) <= maximum
        ]
    )


def pending_for_stage(ledger: Mapping[str, Any], target_stage: str) -> list[dict[str, Any]]:
    """Return unresolved required work that blocks this outer stage and later ones."""
    return [
        entry
        for entry in select(ledger, target_stage)
        if entry["status"] == "planned"
    ]


def check_read(
    ledger: Mapping[str, Any], receipt: Any, *, target_stage: str
) -> None:
    """Validate a result's full-record read binding; paging remains protocol-owned."""
    current = validate(ledger)
    stage = _target_stage(target_stage)
    expected = {
        "revision": current["revision"],
        "digest": hashlib.sha256(render(current).encode("utf-8")).hexdigest(),
        "target_stage": stage,
    }
    need(
        isinstance(receipt, Mapping)
        and set(receipt) == set(expected)
        and dict(receipt) == expected,
        "outer transition requires current outer_work_read revision, digest, and target_stage",
    )


def resolve(
    ledger: Mapping[str, Any], resolution: Mapping[str, Any], provenance: Mapping[str, Any]
) -> dict[str, Any]:
    """Append evidence-backed resolution for a planned row at its target stage."""
    current = validate(ledger)
    normalized_resolution = _resolution(resolution)
    normalized_provenance = _provenance(provenance)
    need(
        normalized_resolution["expected_revision"] == current["revision"],
        "stale outer-work revision; retrieve current outer-work.md and retry",
    )
    entries = {entry["id"]: entry for entry in current["entries"]}
    entry = entries.get(normalized_resolution["entry_id"])
    need(entry is not None, "outer-work resolution names an unknown entry")
    need(entry["status"] == "planned", "outer-work resolution requires a planned entry")
    need(
        normalized_provenance["parent_stage"] == entry["target_stage"],
        "outer-work resolution requires the matching target stage",
    )
    next_revision = current["revision"] + 1
    event = {
        "kind": "resolve",
        "revision": next_revision,
        "resolution": normalized_resolution,
        "provenance": normalized_provenance,
    }
    events = [*current["events"], event]
    normalized_events, effective_entries = _derive_events(events)
    return validate(
        {
            "version": VERSION,
            "revision": next_revision,
            "events": normalized_events,
            "entries": effective_entries,
        }
    )


def request_template(request_id: str, expected_revision: int) -> dict[str, Any]:
    """Return the narrow host-result shape for an inner-stage outer-work request."""
    return {
        "request_id": _id(request_id, "outer-work request_id"),
        "expected_revision": _revision(expected_revision, "outer-work expected_revision"),
        "entry_id": "[stable-outer-work-id]",
        "dedupe_key": "[stable-dedupe-key]",
        "required_action": "[concrete required outer action]",
        "target_stage": "[quality|publish|handoff]",
        "target_alias": "[target-or-environment-alias]",
        "prerequisites": ["[concrete prerequisite, or [] when none apply]"],
        "expected_outcome": "[observable outer outcome]",
        "evidence": "[current evidence or evidence location]",
        "authority_limitations": "[what this request cannot authorize]",
        "rationale": "[why the outer action is required]",
    }


def resolution_template(entry_id: str, expected_revision: int) -> dict[str, Any]:
    """Return the only accepted shape for evidence-backed outer resolution."""
    return {
        "entry_id": _id(entry_id, "outer-work resolution entry_id"),
        "expected_revision": _revision(
            expected_revision, "outer-work resolution expected_revision"
        ),
        "evidence": "[evidence that the required action was completed]",
        "reason": "[why the evidence resolves this required entry]",
    }


__all__ = [
    "MAX_ENTRIES",
    "MAX_EVENTS",
    "MAX_PREREQUISITES",
    "OUTER_STAGES",
    "OuterWorkError",
    "VERSION",
    "append",
    "check_read",
    "empty",
    "pending_for_stage",
    "render",
    "request_template",
    "resolve",
    "resolution_template",
    "select",
    "validate",
]
