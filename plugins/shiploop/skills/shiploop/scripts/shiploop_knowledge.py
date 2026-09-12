"""Bounded, Markdown-authoritative carry-forward knowledge for ShipLoop.

The protocol owns action transitions and storage transactions.  This module
keeps the knowledge record deliberately small: it validates host-reported
observations, builds a current scoped view, and preserves every replacement in
the caller's immutable checkpoint record.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import shiploop_store as store


VERSION = 1
DOMAINS = (
    "research",
    "environment",
    "credential-availability",
    "invocation-contract",
    "system-value",
    "test-strategy",
    "documentation",
)
DISPOSITIONS = (
    "informational",
    "current-step-repair",
    "pending-replan",
    "pause",
)

_ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9._:-]{0,159}\Z")
_STEP_RE = re.compile(r"[SD][0-9]+\Z")
_CREDENTIAL_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:api[_-]?key|secret|password|passwd|access[_-]?token|refresh[_-]?token|"
    r"auth(?:orization)?|bearer|private[_-]?key)\b\s*[:=]\s*(?:['\"]?)[^\s'\"`]+"
)
_SECRET_URL_RE = re.compile(
    r"(?i)https?://[^\s?#]+[^\s]*[?&](?:api[_-]?key|key|secret|password|passwd|"
    r"token|access[_-]?token|refresh[_-]?token)=[^&#\s]+"
)
_URL_USERINFO_RE = re.compile(r"(?i)https?://[^/\s:@]+:[^/\s@]+@")
_TOKEN_PREFIX_RE = re.compile(
    r"\b(?:sk|ghp|github_pat|xox[baprs])[_-][A-Za-z0-9_-]{12,}\b|\bAKIA[A-Z0-9]{16}\b"
)
_PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")

MAX_TEXT = 2000
MAX_DISCOVERIES = 24
MAX_LEARNINGS = 16


class KnowledgeError(ValueError):
    """Raised when a carry-forward record is unsafe or inconsistent."""


def need(ok: bool, message: str) -> None:
    if not ok:
        raise KnowledgeError(message)


def _text(value: Any, label: str, *, limit: int = MAX_TEXT) -> str:
    need(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty")
    text = value.strip()
    need(len(text) <= limit, f"{label} exceeds the bounded carry-forward limit")
    return text


def _safe_id(value: Any, label: str) -> str:
    need(isinstance(value, str) and _ID_RE.fullmatch(value), f"{label} must be a stable safe identifier")
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def recorded_at() -> str:
    """Script-recorded time, deliberately not a claim about observation time."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def screen_payload(value: Any) -> None:
    """Reject obvious secrets without echoing the potentially sensitive text.

    This is intentionally defense in depth, not a claim to identify every
    credential representation.
    """
    def visit(item: Any, depth: int) -> None:
        need(depth <= 8, "carry-forward payload nesting exceeds the bounded limit")
        if isinstance(item, str):
            need(
                len(item) <= MAX_TEXT,
                "carry-forward payload exceeds the bounded text limit",
            )
            if (
                _CREDENTIAL_ASSIGNMENT_RE.search(item)
                or _SECRET_URL_RE.search(item)
                or _URL_USERINFO_RE.search(item)
                or _TOKEN_PREFIX_RE.search(item)
                or _PRIVATE_KEY_RE.search(item)
            ):
                raise KnowledgeError(
                    "carry-forward result appears to contain a credential secret"
                )
        elif isinstance(item, Mapping):
            need(len(item) <= 16, "carry-forward payload exceeds the bounded object limit")
            for key, child in item.items():
                need(isinstance(key, str), "carry-forward payload has a non-string key")
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif isinstance(item, list):
            need(len(item) <= MAX_DISCOVERIES, "carry-forward payload exceeds the bounded list limit")
            for child in item:
                visit(child, depth + 1)

    visit(value, 0)


def _scope(value: Any, step_ids: set[str], label: str) -> list[str]:
    need(isinstance(value, list) and value, f"{label} must be a nonempty list")
    need(all(isinstance(item, str) for item in value), f"{label} entries must be strings")
    need(len(value) == len(set(value)), f"{label} must not duplicate entries")
    if value == ["all"]:
        return ["all"]
    need("all" not in value, f"{label} may use all only by itself")
    for step_id in value:
        need(_STEP_RE.fullmatch(step_id) is not None, f"{label} has an unsafe step ID")
        need(step_id in step_ids, f"{label} names a step outside the current plan")
    return list(value)


def _discovery(value: Any, step_ids: set[str]) -> dict[str, Any]:
    expected = {
        "id",
        "domain",
        "observation",
        "evidence",
        "scope",
        "disposition",
        "rationale",
        "revalidate",
    }
    need(isinstance(value, dict) and set(value) == expected, "discovery has an unexpected schema")
    discovery_id = _safe_id(value["id"], "discovery id")
    domain = value["domain"]
    need(domain in DOMAINS, "discovery domain is not allowed")
    disposition = value["disposition"]
    need(disposition in DISPOSITIONS, "discovery disposition is not allowed")
    return {
        "id": discovery_id,
        "domain": domain,
        "observation": _text(value["observation"], "discovery observation"),
        "evidence": _text(value["evidence"], "discovery evidence"),
        "scope": _scope(value["scope"], step_ids, "discovery scope"),
        "disposition": disposition,
        "rationale": _text(value["rationale"], "discovery rationale"),
        "revalidate": _text(value["revalidate"], "discovery revalidate"),
    }


def _resolution(value: Any) -> dict[str, str]:
    expected = {"id", "decision", "evidence", "reason"}
    need(isinstance(value, dict) and set(value) == expected, "carry-forward resolution has an unexpected schema")
    need(value["decision"] == "no-contract-change", "carry-forward resolution must keep the frozen contract unchanged")
    return {
        "id": _safe_id(value["id"], "carry-forward resolution id"),
        "decision": "no-contract-change",
        "evidence": _text(value["evidence"], "carry-forward resolution evidence"),
        "reason": _text(value["reason"], "carry-forward resolution reason"),
    }


def validate_result(value: Any, *, expected_revision: int, step_ids: set[str]) -> dict[str, Any]:
    """Normalize the narrow carry-forward input schema before it is persisted."""
    expected = {"summary", "knowledge_revision", "learnings", "discoveries"}
    optional = {"resolutions"}
    need(isinstance(value, dict), "carry-forward result must be an object")
    need(set(value).issubset(expected | optional) and expected.issubset(value), "carry-forward result has unknown or missing fields")
    revision = value["knowledge_revision"]
    need(type(revision) is int and revision >= 0, "knowledge_revision must be a nonnegative integer")
    need(
        revision == expected_revision,
        "stale knowledge revision; retrieve current knowledge and retry",
    )
    raw_discoveries = value["discoveries"]
    need(isinstance(raw_discoveries, list), "discoveries must be a list (use [] for no discovery)")
    need(len(raw_discoveries) <= MAX_DISCOVERIES, "discoveries exceeds the bounded carry-forward limit")
    discoveries = [_discovery(item, step_ids) for item in raw_discoveries]
    ids = [item["id"] for item in discoveries]
    need(len(ids) == len(set(ids)), "discoveries must not duplicate stable IDs")
    raw_resolutions = value.get("resolutions", [])
    need(isinstance(raw_resolutions, list), "resolutions must be a list")
    need(len(raw_resolutions) <= MAX_DISCOVERIES, "resolutions exceeds the bounded carry-forward limit")
    resolutions = [_resolution(item) for item in raw_resolutions]
    resolution_ids = [item["id"] for item in resolutions]
    need(len(resolution_ids) == len(set(resolution_ids)), "resolutions must not duplicate IDs")
    normalized = {
        "summary": _text(value["summary"], "summary"),
        "knowledge_revision": revision,
        "learnings": _text(value["learnings"], "learnings"),
        "discoveries": discoveries,
    }
    if "resolutions" in value:
        normalized["resolutions"] = resolutions
    # The shape/size checks above keep secret screening bounded. Unknown
    # arbitrary nested input is rejected before any recursive inspection.
    screen_payload(normalized)
    return normalized


def empty_ledger() -> dict[str, Any]:
    return {
        "version": VERSION,
        "revision": 0,
        "entries": [],
        "obligations": [],
        "blockers": [],
        "learnings": [],
        "last_checkpoint": None,
    }


def _ledger_shape(ledger: Any) -> dict[str, Any]:
    expected = {
        "version",
        "revision",
        "entries",
        "obligations",
        "blockers",
        "learnings",
        "last_checkpoint",
    }
    need(isinstance(ledger, dict) and set(ledger) == expected, "knowledge ledger has an unexpected schema")
    need(ledger["version"] == VERSION, "knowledge ledger has an unsupported version")
    need(type(ledger["revision"]) is int and ledger["revision"] >= 0, "knowledge ledger revision is invalid")
    for key in ("entries", "obligations", "blockers", "learnings"):
        need(isinstance(ledger[key], list), f"knowledge ledger {key} is invalid")
    return ledger


def render(ledger: Mapping[str, Any]) -> str:
    _ledger_shape(dict(ledger))
    return store.dumps(dict(ledger), "ShipLoop current operational knowledge — host reported")


def read_bound(root: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    path = root / "knowledge.md"
    need(path.is_file() and not path.is_symlink(), "missing script-maintained knowledge.md")
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise KnowledgeError("knowledge ledger is not UTF-8 Markdown") from exc
    expected_hash = state.get("knowledge_sha256")
    expected_revision = state.get("knowledge_revision")
    need(isinstance(expected_hash, str) and re.fullmatch(r"[0-9a-f]{64}", expected_hash) is not None, "knowledge state hash is invalid")
    need(type(expected_revision) is int and expected_revision >= 0, "knowledge state revision is invalid")
    need(
        sha256_bytes(raw) == expected_hash,
        "knowledge hash drift; restore script-maintained knowledge.md before continuing",
    )
    ledger = _ledger_shape(store.loads(text))
    need(ledger["revision"] == expected_revision, "knowledge revision does not match state binding")
    expected_action = state.get("knowledge_action_id")
    need(isinstance(expected_action, str), "knowledge state action binding is invalid")
    if ledger["revision"]:
        last = ledger["last_checkpoint"]
        need(
            isinstance(last, dict) and last.get("action") == expected_action,
            "knowledge action does not match state binding",
        )
    else:
        need(not expected_action, "empty knowledge ledger has an unexpected action binding")
    return ledger


def _copy(value: Any) -> Any:
    return json.loads(_canonical(value).decode("utf-8"))


def _source(source: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "action",
        "iteration",
        "check_action",
        "worktree_fingerprint",
        "step",
        "reported_by",
        "recorded_at",
    }
    need(set(source) == expected, "knowledge provenance is invalid")
    for key in (
        "action",
        "iteration",
        "check_action",
        "worktree_fingerprint",
        "step",
        "reported_by",
        "recorded_at",
    ):
        _text(source[key], f"knowledge provenance {key}")
    need(source["reported_by"] == "host", "knowledge observations must remain host-reported")
    return dict(source)


def _entry_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        need(isinstance(row, dict) and isinstance(row.get("id"), str), "knowledge ledger entry is invalid")
        need(row["id"] not in result, "knowledge ledger has duplicate stable IDs")
        result[row["id"]] = row
    return result


def _open_blockers(ledger: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    blocks = _entry_by_id(list(ledger["blockers"]))
    for blocker in blocks.values():
        need(blocker.get("status") in ("open", "resolved"), "knowledge blocker status is invalid")
    return {key: row for key, row in blocks.items() if row.get("status") == "open"}


def apply_result(
    ledger: Mapping[str, Any], result: Mapping[str, Any], source: Mapping[str, Any]
) -> dict[str, Any]:
    """Apply one checkpoint without losing open obligations or blockers."""
    next_ledger = _copy(_ledger_shape(dict(ledger)))
    provenance = _source(source)
    entries = _entry_by_id(next_ledger["entries"])
    obligations = _entry_by_id(next_ledger["obligations"])
    blockers = _entry_by_id(next_ledger["blockers"])
    open_blocks = _open_blockers(next_ledger)

    for resolution in result.get("resolutions", []):
        blocker = open_blocks.get(resolution["id"])
        need(
            blocker is not None,
            "carry-forward resolution must name an active blocker",
        )
        blocker["status"] = "resolved"
        blocker["resolution"] = dict(resolution, source=provenance)
        entry = entries.get(resolution["id"])
        if entry is not None:
            entry["status"] = "resolved"
            entry["resolution"] = dict(resolution, source=provenance)

    next_revision = next_ledger["revision"] + 1
    for discovery in result["discoveries"]:
        prior = entries.get(discovery["id"])
        if prior is not None:
            need(
                prior.get("domain") == discovery["domain"],
                "discovery ID may not change domain",
            )
        entry = dict(discovery, source=provenance, recorded_revision=next_revision)
        if prior is None:
            next_ledger["entries"].append(entry)
            entries[entry["id"]] = entry
        else:
            next_ledger["entries"].remove(prior)
            next_ledger["entries"].append(entry)
            entries[entry["id"]] = entry

        if discovery["disposition"] == "pending-replan":
            obligation = obligations.get(discovery["id"])
            if obligation is None:
                obligation = {
                    "id": discovery["id"],
                    "scope": discovery["scope"],
                    "rationale": discovery["rationale"],
                    "source": provenance,
                    "status": "open",
                    "scheduled_steps": [],
                }
                if discovery["domain"] == "research":
                    obligation["research_required"] = True
                next_ledger["obligations"].append(obligation)
                obligations[obligation["id"]] = obligation
            else:
                obligation.update(
                    scope=discovery["scope"],
                    rationale=discovery["rationale"],
                    source=provenance,
                    status="open",
                    scheduled_steps=[],
                )
                if discovery["domain"] == "research":
                    obligation["research_required"] = True
        elif discovery["disposition"] == "pause":
            blocker = blockers.get(discovery["id"])
            if blocker is None:
                blocker = {
                    "id": discovery["id"],
                    "scope": discovery["scope"],
                    "reason": discovery["rationale"],
                    "source": provenance,
                    "status": "open",
                }
                next_ledger["blockers"].append(blocker)
                blockers[blocker["id"]] = blocker
            else:
                blocker.update(
                    scope=discovery["scope"],
                    reason=discovery["rationale"],
                    source=provenance,
                    status="open",
                )
                blocker.pop("resolution", None)

    next_ledger["learnings"].append({"text": result["learnings"], "source": provenance})
    if len(next_ledger["learnings"]) > MAX_LEARNINGS:
        next_ledger["learnings"] = next_ledger["learnings"][-MAX_LEARNINGS:]
    next_ledger["revision"] = next_revision
    next_ledger["last_checkpoint"] = provenance
    return next_ledger


def has_open_blockers(ledger: Mapping[str, Any]) -> bool:
    return bool(_open_blockers(ledger))


def open_pending_obligations(ledger: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in ledger["obligations"]:
        need(isinstance(row, dict), "knowledge obligation is invalid")
        if row.get("status") == "open":
            rows.append(row)
    return rows


def map_pending_obligations(
    ledger: Mapping[str, Any], mapping: Mapping[str, list[str]], source: Mapping[str, Any]
) -> dict[str, Any]:
    next_ledger = _copy(_ledger_shape(dict(ledger)))
    provenance = _source(source)
    by_id = _entry_by_id(next_ledger["obligations"])
    for obligation_id, steps in mapping.items():
        _safe_id(obligation_id, "pending obligation id")
        need(
            isinstance(steps, list)
            and steps
            and all(isinstance(step, str) and _STEP_RE.fullmatch(step) for step in steps)
            and len(steps) == len(set(steps)),
            "pending obligation mapping steps are invalid",
        )
        obligation = by_id.get(obligation_id)
        need(obligation is not None and obligation.get("status") == "open", "pending obligation is not open")
        obligation.update(
            status="scheduled",
            scheduled_steps=list(steps),
            scheduled_source=provenance,
        )
    next_ledger["revision"] += 1
    next_ledger["last_checkpoint"] = provenance
    return next_ledger


def scope_for(active_step: str | None) -> list[str]:
    return ["all", active_step] if active_step else ["all"]


def _in_scope(row: Mapping[str, Any], active_step: str | None) -> bool:
    if active_step is None:
        return True
    scope = row.get("scope")
    return isinstance(scope, list) and (
        scope == ["all"] or (active_step is not None and active_step in scope)
    )


def scoped_view(ledger: Mapping[str, Any], active_step: str | None) -> dict[str, Any]:
    """Return bounded current facts plus every outstanding cross-step obligation."""
    ledger = _ledger_shape(dict(ledger))
    required_ids = {
        row["id"]
        for row in ledger["obligations"]
        if row.get("status") in ("open", "scheduled")
    }
    required_ids.update(
        row["id"] for row in ledger["blockers"] if row.get("status") == "open"
    )
    entries = [
        row
        for row in ledger["entries"]
        if _in_scope(row, active_step) or row.get("id") in required_ids
    ]
    # Do not hide future-step planning obligations merely because the current
    # step's facts are scoped down. They remain bounded and visible to a cold
    # consumer at review/post-inner/scheduling.
    obligations = [
        row
        for row in ledger["obligations"]
        if row.get("status") in ("open", "scheduled")
    ]
    blockers = [row for row in ledger["blockers"] if row.get("status") == "open"]
    return {
        "version": VERSION,
        "knowledge_revision": ledger["revision"],
        "scope": scope_for(active_step),
        "entries": entries,
        "obligations": obligations,
        "blockers": blockers,
        "learnings": ledger["learnings"][-1:],
    }


def context_text(ledger: Mapping[str, Any], active_step: str | None) -> str:
    return store.dumps(scoped_view(ledger, active_step), "ShipLoop current knowledge — host reported")


def checkpoint(
    *,
    kind: str,
    action: str,
    previous_ledger: Mapping[str, Any],
    next_ledger: Mapping[str, Any],
    previous_sha256: str,
    next_sha256: str,
    source: Mapping[str, Any],
    result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "version": VERSION,
        "kind": kind,
        "action": action,
        "previous_knowledge_revision": previous_ledger["revision"],
        "knowledge_revision": next_ledger["revision"],
        "previous_knowledge_sha256": previous_sha256,
        "knowledge_sha256": next_sha256,
        "source": dict(source),
        "ledger": dict(next_ledger),
    }
    if result is not None:
        record["result"] = dict(result)
    return record
