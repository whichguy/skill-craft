"""Pure early-observation checkpoints for ShipLoop.

The protocol owns action dispatch, Markdown files, and state-machine routing.
This module makes the small side callback safe to issue and replay. It does not
consume the parent action, create authority, claim a check passed, or write any
state itself.

An observation is intentionally narrower than carry-forward: it can add or
replace current knowledge before a successful check, but cannot resolve a
blocker through a side callback. The pure model represents ``pause`` so callers
can classify it safely; the protocol admits it only where a real recovery route
exists and otherwise rejects it before writing state. The normal controlled
route remains the only way to resolve an authority or contract decision.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

import shiploop_knowledge as knowledge


VERSION = 1
ACTION_PREFIX = "OBS-"
KIND = "unverified-observation"
VERIFICATION = "not-run"

_ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9._:-]{0,159}\Z")
_PARENT_ACTION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}\Z")
_STEP_RE = re.compile(r"[SD][0-9]+\Z")
_STAGE_RE = re.compile(r"[a-z][a-z0-9-]{0,79}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")

_TICKET_FIELDS = frozenset(
    (
        "version",
        "action",
        "parent_action",
        "parent_stage",
        "parent_step",
        "expected_knowledge_revision",
    )
)
_RESULT_FIELDS = frozenset(("summary", "knowledge_revision", "learnings", "discoveries"))
_RECEIPT_FIELDS = frozenset(
    (
        "version",
        "kind",
        "action",
        "parent_action",
        "parent_stage",
        "parent_step",
        "expected_knowledge_revision",
        "knowledge_revision",
        "knowledge_sha256",
        "checkpoint",
        "route",
        "input_digest",
    )
)

# A result that changes current knowledge after a bound check must not leave
# that proof available for finalization. The protocol provides whether a
# successful check is actually bound; this list keeps the stage policy small,
# inspectable, and testable.
POST_CHECK_STAGES = frozenset(
    (
        "verify",
        "carry-forward",
        "commit",
        "final-verify",
        "post-inner",
        "merge",
        "quality",
        "publish",
        "handoff",
        "objective-review",
        "objective-plan",
        "objective-apply",
        "objective-finalize",
    )
)


class ObservationError(ValueError):
    """Raised when an observation ticket, payload, or replay is unsafe."""


def need(ok: bool, message: str) -> None:
    if not ok:
        raise ObservationError(message)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _copy(value: Any) -> Any:
    return json.loads(_canonical(value).decode("utf-8"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _safe_id(value: Any, label: str) -> str:
    need(
        isinstance(value, str) and _ID_RE.fullmatch(value) is not None,
        f"{label} must be a stable safe identifier",
    )
    return value


def _parent_action(value: Any, label: str) -> str:
    need(
        isinstance(value, str) and _PARENT_ACTION_RE.fullmatch(value) is not None,
        f"{label} must be a stable safe identifier",
    )
    return value


def _revision(value: Any, label: str) -> int:
    need(type(value) is int and value >= 0, f"{label} must be a nonnegative integer")
    return value


def _stage(value: Any, label: str) -> str:
    need(
        isinstance(value, str) and _STAGE_RE.fullmatch(value) is not None,
        f"{label} must be a safe stage name",
    )
    return value


def _step(value: Any, label: str) -> str | None:
    need(
        value is None or (isinstance(value, str) and _STEP_RE.fullmatch(value) is not None),
        f"{label} must be null or a current safe step identifier",
    )
    return value


def action_id(parent_action: str, knowledge_revision: int) -> str:
    """Return the one script-issued side-action ID for a parent/revision pair."""
    parent = _parent_action(parent_action, "parent action")
    revision = _revision(knowledge_revision, "knowledge revision")
    return ACTION_PREFIX + _digest(
        {"parent_action": parent, "knowledge_revision": revision}
    )[:32]


def issue(
    parent_action: str,
    parent_stage: str,
    parent_step: str | None,
    knowledge_revision: int,
) -> dict[str, Any]:
    """Issue a deterministic ticket without mutating the parent cursor."""
    parent = _parent_action(parent_action, "parent action")
    stage = _stage(parent_stage, "parent stage")
    step = _step(parent_step, "parent step")
    revision = _revision(knowledge_revision, "knowledge revision")
    return {
        "version": VERSION,
        "action": action_id(parent, revision),
        "parent_action": parent,
        "parent_stage": stage,
        "parent_step": step,
        "expected_knowledge_revision": revision,
    }


def validate_ticket(value: Any) -> dict[str, Any]:
    need(
        isinstance(value, Mapping) and set(value) == _TICKET_FIELDS,
        "observation ticket has an unexpected schema",
    )
    need(
        type(value["version"]) is int and value["version"] == VERSION,
        "observation ticket has an unsupported version",
    )
    parent = _parent_action(value["parent_action"], "observation parent action")
    revision = _revision(
        value["expected_knowledge_revision"], "observation expected knowledge revision"
    )
    expected_action = action_id(parent, revision)
    need(
        value["action"] == expected_action,
        "observation action must be the script-issued parent/revision action",
    )
    return {
        "version": VERSION,
        "action": expected_action,
        "parent_action": parent,
        "parent_stage": _stage(value["parent_stage"], "observation parent stage"),
        "parent_step": _step(value["parent_step"], "observation parent step"),
        "expected_knowledge_revision": revision,
    }


def validate_submission(
    value: Any, ticket: Mapping[str, Any], *, step_ids: set[str]
) -> dict[str, Any]:
    """Normalize the closed early-observation result shape.

    This reuses the same bounded discovery fields as carry-forward, but omits
    resolutions. A side action can record a blocker; it cannot resolve one.
    """
    expected = validate_ticket(ticket)
    need(
        isinstance(value, Mapping) and set(value) == _RESULT_FIELDS,
        "early observation result has unknown or missing fields",
    )
    try:
        result = knowledge.validate_result(
            dict(value),
            expected_revision=expected["expected_knowledge_revision"],
            step_ids=step_ids,
        )
    except knowledge.KnowledgeError as exc:
        raise ObservationError(str(exc)) from exc
    # A future carry-forward extension must not silently enable a resolution
    # on this early side channel.
    need(
        set(result) == _RESULT_FIELDS,
        "early observation results cannot resolve carry-forward blockers",
    )
    for discovery in result["discoveries"]:
        if discovery["domain"] == "credential-availability":
            need(
                discovery["disposition"] == "pause",
                "credential availability observations must pause for explicit authority",
            )
    return result


def route(result: Mapping[str, Any], ticket: Mapping[str, Any]) -> dict[str, Any]:
    """Choose a conservative, data-only route for an accepted observation."""
    current = validate_ticket(ticket)
    discoveries = result.get("discoveries")
    need(isinstance(discoveries, list), "accepted observation has invalid discoveries")
    repairs = []
    pending = []
    pauses = []
    for discovery in discoveries:
        need(isinstance(discovery, Mapping), "accepted observation discovery is invalid")
        disposition = discovery.get("disposition")
        identifier = discovery.get("id")
        _safe_id(identifier, "accepted observation discovery id")
        if disposition == "current-step-repair":
            need(
                current["parent_step"] is not None
                and discovery.get("scope") == [current["parent_step"]],
                "current-step-repair observation must target the active parent step",
            )
            repairs.append(identifier)
        elif disposition == "pending-replan":
            pending.append(identifier)
        elif disposition == "pause":
            pauses.append(identifier)
        else:
            need(
                disposition == "informational",
                "accepted observation disposition is invalid",
            )
    if pauses:
        return {"kind": "pause", "discovery_ids": sorted(pauses)}
    if repairs:
        return {"kind": "current-step-repair", "discovery_ids": sorted(repairs)}
    if pending:
        return {"kind": "pending-replan", "discovery_ids": sorted(pending)}
    return {"kind": "informational", "discovery_ids": []}


def protect_route(
    route_value: Mapping[str, Any], ticket: Mapping[str, Any], *, proof_bound: bool
) -> dict[str, Any]:
    """Turn a seemingly informational late observation into a repair route.

    ``proof_bound`` must come from protocol-owned evidence, never a host claim.
    This prevents new current knowledge from silently preserving a check or
    outer-convergence proof that was bound before the observation existed.
    """
    current = validate_ticket(ticket)
    kind = route_value.get("kind") if isinstance(route_value, Mapping) else None
    identifiers = route_value.get("discovery_ids") if isinstance(route_value, Mapping) else None
    need(
        kind in {"informational", "pending-replan", "current-step-repair", "pause"}
        and isinstance(identifiers, list)
        and all(isinstance(item, str) for item in identifiers),
        "observation route is invalid",
    )
    if kind == "informational" and proof_bound and current["parent_stage"] in POST_CHECK_STAGES:
        return {"kind": "proof-repair", "discovery_ids": []}
    return {"kind": kind, "discovery_ids": sorted(identifiers)}


def provenance(
    ticket: Mapping[str, Any], *, context_fingerprint: str, recorded_at: str | None = None
) -> dict[str, Any]:
    """Create provenance that explicitly says no verification result exists."""
    current = validate_ticket(ticket)
    need(
        isinstance(context_fingerprint, str)
        and _SHA256_RE.fullmatch(context_fingerprint) is not None,
        "observation context fingerprint is invalid",
    )
    timestamp = knowledge.recorded_at() if recorded_at is None else recorded_at
    need(
        isinstance(timestamp, str) and bool(timestamp.strip()) and len(timestamp) <= knowledge.MAX_TEXT,
        "observation recorded_at must be bounded nonempty text",
    )
    return {
        "kind": KIND,
        "action": current["action"],
        "parent_action": current["parent_action"],
        "parent_stage": current["parent_stage"],
        "parent_step": current["parent_step"],
        "context_fingerprint": context_fingerprint,
        "reported_by": "host",
        "recorded_at": timestamp.strip(),
        "verification": VERIFICATION,
    }


def submission_digest(ticket: Mapping[str, Any], raw_result: Mapping[str, Any]) -> str:
    """Fingerprint the exact accepted host payload and its issued ticket."""
    current = validate_ticket(ticket)
    need(isinstance(raw_result, Mapping), "early observation raw result must be an object")
    return _digest({"ticket": current, "result": dict(raw_result)})


def checkpoint_path(ticket: Mapping[str, Any]) -> str:
    return "knowledge-history/" + validate_ticket(ticket)["action"] + ".md"


def build_checkpoint(
    *,
    ledger: Mapping[str, Any],
    previous_sha256: str,
    ticket: Mapping[str, Any],
    raw_result: Mapping[str, Any],
    step_ids: set[str],
    context_fingerprint: str,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    """Prepare, but do not persist, an atomic early-observation checkpoint."""
    current = validate_ticket(ticket)
    normalized = validate_submission(raw_result, current, step_ids=step_ids)
    rendered_previous = knowledge.render(ledger)
    need(
        previous_sha256 == knowledge.sha256_text(rendered_previous),
        "early observation previous knowledge hash does not match its ledger",
    )
    source = provenance(
        current,
        context_fingerprint=context_fingerprint,
        recorded_at=recorded_at,
    )
    try:
        next_ledger = knowledge.apply_result(ledger, normalized, source)
    except knowledge.KnowledgeError as exc:
        raise ObservationError(str(exc)) from exc
    next_body = knowledge.render(next_ledger)
    next_sha256 = knowledge.sha256_text(next_body)
    selected_route = route(normalized, current)
    return {
        "result": _copy(normalized),
        "ledger": next_ledger,
        "source": source,
        "route": selected_route,
        "input_digest": submission_digest(current, raw_result),
        "knowledge_sha256": next_sha256,
        "checkpoint": knowledge.checkpoint(
            kind=KIND,
            action=current["action"],
            previous_ledger=ledger,
            next_ledger=next_ledger,
            previous_sha256=previous_sha256,
            next_sha256=next_sha256,
            source=source,
            result=normalized,
        ),
    }


def receipt(ticket: Mapping[str, Any], prepared: Mapping[str, Any]) -> dict[str, Any]:
    """Create the immutable receipt root persists beside the checkpoint."""
    current = validate_ticket(ticket)
    expected = {
        "result",
        "ledger",
        "source",
        "route",
        "input_digest",
        "knowledge_sha256",
        "checkpoint",
    }
    need(
        isinstance(prepared, Mapping) and set(prepared) == expected,
        "prepared observation checkpoint has an unexpected schema",
    )
    revision = prepared["ledger"].get("revision") if isinstance(prepared["ledger"], Mapping) else None
    need(
        type(revision) is int
        and revision == current["expected_knowledge_revision"] + 1,
        "prepared observation checkpoint has an invalid next revision",
    )
    digest = prepared["input_digest"]
    sha = prepared["knowledge_sha256"]
    need(
        isinstance(digest, str) and _SHA256_RE.fullmatch(digest) is not None,
        "prepared observation input digest is invalid",
    )
    need(
        isinstance(sha, str) and _SHA256_RE.fullmatch(sha) is not None,
        "prepared observation knowledge hash is invalid",
    )
    selected_route = prepared["route"]
    need(isinstance(selected_route, Mapping), "prepared observation route is invalid")
    return {
        "version": VERSION,
        "kind": KIND,
        "action": current["action"],
        "parent_action": current["parent_action"],
        "parent_stage": current["parent_stage"],
        "parent_step": current["parent_step"],
        "expected_knowledge_revision": current["expected_knowledge_revision"],
        "knowledge_revision": revision,
        "knowledge_sha256": sha,
        "checkpoint": checkpoint_path(current),
        "route": _copy(selected_route),
        "input_digest": digest,
    }


def assert_replay(
    value: Any,
    ticket: Mapping[str, Any],
    raw_result: Mapping[str, Any],
    *,
    route_value: Mapping[str, Any],
) -> dict[str, Any]:
    """Accept one identical completed side callback and reject a changed retry."""
    current = validate_ticket(ticket)
    need(
        isinstance(value, Mapping) and set(value) == _RECEIPT_FIELDS,
        "observation receipt has an unexpected schema",
    )
    for key in (
        "version",
        "kind",
        "action",
        "parent_action",
        "parent_stage",
        "parent_step",
        "expected_knowledge_revision",
    ):
        expected = VERSION if key == "version" else KIND if key == "kind" else current[key]
        if key == "version":
            need(type(value[key]) is int, "observation receipt version is invalid")
        need(value[key] == expected, "observation receipt does not match the issued ticket")
    revision = value["knowledge_revision"]
    need(
        type(revision) is int and revision == current["expected_knowledge_revision"] + 1,
        "observation receipt has an invalid knowledge revision",
    )
    for key in ("knowledge_sha256", "input_digest"):
        need(
            isinstance(value[key], str) and _SHA256_RE.fullmatch(value[key]) is not None,
            f"observation receipt {key} is invalid",
        )
    need(value["checkpoint"] == checkpoint_path(current), "observation receipt checkpoint is invalid")
    need(value["route"] == dict(route_value), "observation receipt route does not match the accepted result")
    need(
        value["input_digest"] == submission_digest(current, raw_result),
        "conflicting replay of an accepted early observation",
    )
    return _copy(value)
