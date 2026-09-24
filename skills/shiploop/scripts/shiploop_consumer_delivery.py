"""Pure opt-in consumer-delivery declarations for the navigator.

The navigator still owns graph traversal.  This module only canonicalizes a
small host-declared contract, projects its accepted ledger, and rejects
declared omissions or contradictions.  It neither reads a product nor proves
that an authority, artifact, or consumer observation is true.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import html
import re
from typing import Any

import shiploop_planning_revision as planning_revision

DELIVERY_CONTRACT_VERSION = 1
_ANCHOR = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,159}$")
_OBLIGATION_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
_NECESSITIES = frozenset(("required", "not-required", "unresolved"))
_AUTHORITY_STATUSES = frozenset(("approved", "not-required", "unresolved"))
_AUTHORITY_KINDS = frozenset(("request", "user-decision", "repo-policy"))
_OBLIGATION_KINDS = frozenset(("pre-update", "effect", "identity", "behavior"))
_OBSERVATION_STATUSES = frozenset(
    ("passed", "already-current", "failed", "blocked", "unrun")
)
_PHASE_FOR_KIND = {
    "pre-update": "system-test",
    "effect": "release",
    "identity": "release",
    "behavior": "release-verify",
}
_OBSERVABLE_AT = {
    "system-test": frozenset(("pre-update",)),
    # Release planning may refresh pre-update evidence when a late planning
    # change invalidated it.  It does not authorize an effectful observation.
    "release-plan": frozenset(("pre-update",)),
    "release": frozenset(("effect", "identity")),
    "release-verify": frozenset(("behavior",)),
}
# A later action may retain a newly learned negative outcome for an already
# due obligation.  It must not fabricate a new positive receipt for an
# earlier phase: only the phase that owns an observation may report it passed.
_NEGATIVE_OBSERVABLE_AT = {
    "system-test": frozenset(("pre-update",)),
    "release-plan": frozenset(("pre-update",)),
    # These readiness stages occur after system-test but before release,
    # so they may retain a newly discovered failure of the due pre-update
    # evidence without inventing a positive receipt for it.
    "product-acceptance": frozenset(("pre-update",)),
    "release-check": frozenset(("pre-update",)),
    "release": frozenset(("pre-update", "effect", "identity")),
    "release-verify": _OBLIGATION_KINDS,
    # Operations follows release verification in the navigator graph, so every
    # obligation is already due and a later failure must remain durable.
    "operations": _OBLIGATION_KINDS,
    "handoff": _OBLIGATION_KINDS,
}
_POSITIVE_OBSERVATION_STATUSES = frozenset(("passed", "already-current"))
# At these stages, a required row from an earlier phase cannot be positively
# refreshed by this fixed graph action.  The packet must direct a clean new
# planning run rather than imply that repeating the current action can repair
# an old receipt.
_EARLIER_DUE_KINDS = {
    "product-acceptance": frozenset(("pre-update",)),
    "release-check": frozenset(("pre-update",)),
    "release": frozenset(("pre-update",)),
    "release-verify": frozenset(("pre-update", "effect", "identity")),
    "operations": _OBLIGATION_KINDS,
    "handoff": _OBLIGATION_KINDS,
}
_POST_RELEASE_PLAN_MUTATION_STAGES = frozenset(
    (
        "system-test-author", "system-test", "product-acceptance", "release-check",
        "release", "release-verify", "operations", "handoff",
    )
)


class ConsumerDeliveryError(ValueError):
    """A host declaration cannot safely advance the marked navigator run."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ConsumerDeliveryError(message)


_REPLAN_MESSAGE = (
    "The required delivery contract changed after release planning and requires replanning through "
    "the accepted outer replan edge, followed by fresh system-test and release-plan "
    "evidence for the current contract before another completion."
)


def _text(value: Any, label: str, *, allow_empty: bool = False) -> str:
    _need(isinstance(value, str), f"{label} must be text")
    if not allow_empty:
        _need(bool(value.strip()), f"{label} must be nonempty")
    return value


def _text_list(value: Any, label: str) -> list[str]:
    _need(isinstance(value, list), f"{label} must be a list")
    rows = [_text(item, label) for item in value]
    _need(len(rows) == len(set(rows)), f"{label} repeats a value")
    return rows


def _correction_source(value: Any, label: str) -> dict[str, str]:
    _need(isinstance(value, Mapping), f"{label} must be an object")
    allowed = {"kind", "reference", "approval_ref"}
    _need(set(value) <= allowed and {"kind", "reference"} <= set(value),
          f"{label} has unsupported or missing fields")
    kind = value.get("kind")
    _need(isinstance(kind, str) and kind in _AUTHORITY_KINDS,
          f"{label} kind is invalid")
    result = {
        "kind": kind,
        "reference": _text(value.get("reference"), f"{label} reference"),
    }
    approval = value.get("approval_ref")
    if kind == "repo-policy":
        result["approval_ref"] = _text(approval, f"{label} approval_ref")
    else:
        _need(approval is None, f"{label} approval_ref is allowed only for repo-policy")
    return result


def _authority(value: Any) -> dict[str, str]:
    _need(isinstance(value, Mapping), "delivery authority must be an object")
    allowed = {"status", "kind", "reference", "approval_ref", "target", "operation"}
    required = {"status", "kind", "reference", "target", "operation"}
    _need(set(value) <= allowed and required <= set(value),
          "delivery authority has unsupported or missing fields")
    status = value.get("status")
    _need(isinstance(status, str) and status in _AUTHORITY_STATUSES,
          "delivery authority status is invalid")
    source = _correction_source(
        {key: value[key] for key in ("kind", "reference", "approval_ref") if key in value},
        "delivery authority",
    )
    return {
        "status": status,
        **source,
        "target": _text(value.get("target"), "delivery authority target"),
        "operation": _text(value.get("operation"), "delivery authority operation"),
    }


def _obligations(value: Any) -> list[dict[str, Any]]:
    _need(isinstance(value, list), "delivery obligations must be a list")
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    for raw in value:
        _need(isinstance(raw, Mapping), "delivery obligation must be an object")
        required = {"id", "consumer", "target", "kind", "phase", "expected", "required"}
        _need(set(raw) == required, "delivery obligation has unsupported or missing fields")
        identifier = raw.get("id")
        _need(isinstance(identifier, str) and _OBLIGATION_ID.fullmatch(identifier) is not None,
              "delivery obligation ID is unsafe")
        _need(identifier not in ids, "delivery obligation ID repeats")
        ids.add(identifier)
        kind = raw.get("kind")
        _need(isinstance(kind, str) and kind in _OBLIGATION_KINDS,
              "delivery obligation kind is invalid")
        phase = raw.get("phase")
        _need(phase == _PHASE_FOR_KIND[kind],
              "delivery obligation phase does not match its kind")
        required_flag = raw.get("required")
        _need(type(required_flag) is bool, "delivery obligation required must be boolean")
        rows.append(
            {
                "id": identifier,
                "consumer": _text(raw.get("consumer"), "delivery obligation consumer"),
                "target": _text(raw.get("target"), "delivery obligation target"),
                "kind": kind,
                "phase": phase,
                "expected": _text(raw.get("expected"), "delivery obligation expected"),
                "required": required_flag,
            }
        )
    return rows


def _contract(value: Any) -> dict[str, Any]:
    _need(isinstance(value, Mapping), "delivery contract must be an object")
    required = {
        "consumer", "target", "behavior", "candidate", "operation", "necessity",
        "basis", "exclusions", "authority", "obligations",
    }
    _need(set(value) == required, "delivery contract has unsupported or missing fields")
    necessity = value.get("necessity")
    _need(isinstance(necessity, str) and necessity in _NECESSITIES,
          "delivery necessity is invalid")
    authority = _authority(value.get("authority"))
    target = _text(value.get("target"), "delivery target")
    operation = _text(value.get("operation"), "delivery operation")
    _need(authority["target"] == target, "delivery authority target does not match contract")
    _need(authority["operation"] == operation,
          "delivery authority operation does not match contract")
    obligations = _obligations(value.get("obligations"))
    result = {
        "consumer": _text(value.get("consumer"), "delivery consumer"),
        "target": target,
        "behavior": _text(value.get("behavior"), "delivery behavior"),
        "candidate": _text(value.get("candidate"), "delivery candidate"),
        "operation": operation,
        "necessity": necessity,
        "basis": _text(value.get("basis"), "delivery basis"),
        "exclusions": _text_list(value.get("exclusions"), "delivery exclusions"),
        "authority": authority,
        "obligations": obligations,
    }
    required_kinds = {
        row["kind"] for row in obligations if row["required"] is True
    }
    if necessity in {"required", "not-required"}:
        _need("behavior" in required_kinds,
              "resolved delivery contract needs a required behavior obligation")
    if necessity == "required":
        _need({"effect", "identity"} <= required_kinds,
              "required delivery contract needs effect and identity obligations")
    if necessity == "not-required":
        _need(not any(
            row["kind"] in {"effect", "identity"}
            for row in obligations
        ), "not-required delivery contract cannot retain effect or identity obligations")
    for row in obligations:
        if row["kind"] in {"effect", "identity"}:
            _need(row["target"] == authority["target"],
                  "delivery contract supports one activation target bound to delivery authority")
    return result


def _observation_rows(value: Any) -> list[dict[str, Any]]:
    _need(isinstance(value, list) and bool(value), "delivery observations must be a nonempty list")
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    for raw in value:
        _need(isinstance(raw, Mapping), "delivery observation must be an object")
        required = {"obligation_id", "status", "candidate", "target", "evidence_refs"}
        _need(set(raw) == required, "delivery observation has unsupported or missing fields")
        identifier = raw.get("obligation_id")
        _need(isinstance(identifier, str) and _OBLIGATION_ID.fullmatch(identifier) is not None,
              "delivery observation obligation ID is unsafe")
        _need(identifier not in ids, "delivery observation repeats an obligation")
        ids.add(identifier)
        status = raw.get("status")
        _need(isinstance(status, str) and status in _OBSERVATION_STATUSES,
              "delivery observation status is invalid")
        refs = _text_list(raw.get("evidence_refs"), "delivery observation evidence_refs")
        _need(bool(refs), "delivery observation evidence_refs must not be empty")
        rows.append(
            {
                "obligation_id": identifier,
                "status": status,
                "candidate": _text(raw.get("candidate"), "delivery observation candidate"),
                "target": _text(raw.get("target"), "delivery observation target"),
                "evidence_refs": refs,
            }
        )
    return rows


def canonical_assessment(value: Any) -> dict[str, Any]:
    """Return the canonical declaration; dynamic binding is checked by project()."""
    _need(isinstance(value, Mapping), "delivery_assessment must be an object")
    kind = value.get("kind")
    _need(isinstance(kind, str) and kind in {"contract", "observation"},
          "delivery_assessment kind is invalid")
    if kind == "contract":
        allowed = {"kind", "contract", "supersedes", "correction", "observations"}
        _need(set(value) <= allowed and {"kind", "contract"} <= set(value),
              "delivery contract assessment has unsupported or missing fields")
        result: dict[str, Any] = {"kind": "contract", "contract": _contract(value.get("contract"))}
        if "supersedes" in value:
            anchor = value.get("supersedes")
            _need(isinstance(anchor, str) and _ANCHOR.fullmatch(anchor) is not None,
                  "delivery supersedes anchor is unsafe")
            result["supersedes"] = anchor
        if "correction" in value:
            result["correction"] = _correction_source(value.get("correction"), "delivery correction")
        if "observations" in value:
            result["observations"] = _observation_rows(value.get("observations"))
        return result

    _need(set(value) == {"kind", "contract_anchor", "observations"},
          "delivery observation assessment has unsupported or missing fields")
    anchor = value.get("contract_anchor")
    _need(isinstance(anchor, str) and _ANCHOR.fullmatch(anchor) is not None,
          "delivery contract anchor is unsafe")
    return {
        "kind": "observation",
        "contract_anchor": anchor,
        "observations": _observation_rows(value.get("observations")),
    }


def _required_rows(contract: Mapping[str, Any], *, phase: str | None = None) -> list[dict[str, Any]]:
    return [
        row for row in contract["obligations"]
        if row["required"] is True and (phase is None or row["phase"] == phase)
    ]


def _same_obligation(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return dict(left) == dict(right)


def _requires_user_correction(prior: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    # Candidate changes describe a new artifact under the same requested
    # delivery outcome.  They can demand replanning, but are not themselves a
    # user scope reduction.  All other delivery requirement changes are.
    for key in ("consumer", "target", "behavior", "operation", "necessity", "exclusions", "authority"):
        if prior[key] != current[key]:
            return True
    previous = {row["id"]: row for row in _required_rows(prior)}
    replacement = {row["id"]: row for row in _required_rows(current)}
    for identifier, row in previous.items():
        replacement_row = replacement.get(identifier)
        if replacement_row is None or not _same_obligation(row, replacement_row):
            return True
    # Adding a new required check preserves (and can strengthen) the prior
    # outcome; it does not require the user to re-approve the existing scope.
    return False


def _material_post_plan_change(prior: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    if any(prior[key] != current[key] for key in (
        "candidate", "consumer", "target", "behavior", "operation", "necessity",
        "authority", "exclusions",
    )):
        return True
    previous = {row["id"]: row for row in _required_rows(prior)}
    replacement = {row["id"]: row for row in _required_rows(current)}
    return set(previous) != set(replacement) or any(
        not _same_obligation(row, replacement[identifier])
        for identifier, row in previous.items()
    )


def _preserved_observations(
    observations: Mapping[str, Mapping[str, Any]],
    prior: Mapping[str, Any],
    current: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    previous_by_id = {row["id"]: row for row in prior["obligations"]}
    current_by_id = {row["id"]: row for row in current["obligations"]}
    if prior["candidate"] != current["candidate"] or any(
        prior[key] != current[key]
        for key in ("consumer", "target", "operation", "necessity", "authority", "exclusions")
    ):
        return {}
    behavior_changed = prior["behavior"] != current["behavior"]
    retained: dict[str, dict[str, Any]] = {}
    for identifier, observation in observations.items():
        previous = previous_by_id.get(identifier)
        replacement = current_by_id.get(identifier)
        if (previous is not None and replacement is not None
                and _same_obligation(previous, replacement)
                and not (behavior_changed and previous["kind"] == "behavior")):
            retained[identifier] = deepcopy(dict(observation))
    return retained


def _apply_observations(
    projection: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    action: str,
    stage: str,
) -> None:
    contract = projection.get("contract")
    _need(isinstance(contract, Mapping), "delivery observation has no accepted contract")
    by_id = {row["id"]: row for row in contract["obligations"]}
    positive_permitted = _OBSERVABLE_AT.get(stage, frozenset())
    negative_permitted = _NEGATIVE_OBSERVABLE_AT.get(stage, frozenset())
    for observation in rows:
        obligation = by_id.get(observation["obligation_id"])
        _need(obligation is not None, "delivery observation names an unknown obligation")
        if observation["status"] in _POSITIVE_OBSERVATION_STATUSES:
            _need(obligation["kind"] in positive_permitted,
                  "positive delivery observation is not due at the current stage")
            if observation["status"] == "already-current":
                _need(obligation["kind"] in {"effect", "identity"},
                      "already-current applies only to effect or identity obligations")
        else:
            _need(obligation["kind"] in negative_permitted,
                  "negative delivery observation is earlier than its due phase")
        _need(observation["candidate"] == contract["candidate"],
              "delivery observation candidate is not current")
        _need(observation["target"] == obligation["target"],
              "delivery observation target does not match its obligation")
        projection["observations"][obligation["id"]] = {
            **deepcopy(observation),
            "source_action": action,
            "source_stage": stage,
        }


def _accepted_entries(state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    history = state.get("history")
    accepted = state.get("accepted")
    _need(isinstance(history, list) and isinstance(accepted, Mapping),
          "delivery projection requires a navigator ledger")
    return [
        {
            "action": entry["action"],
            "stage": entry["stage"],
            "outcome": entry["outcome"],
            "result": accepted[entry["action"]],
        }
        for entry in history
    ]


def _blank_projection(enabled: bool) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "contract": None,
        "anchor": None,
        "observations": {},
        "replan_required": None,
    }


def _superseded_planning_anchor(state: Mapping[str, Any], anchor: str | None) -> bool:
    if anchor is None:
        return False
    entry = next((row for row in state["history"] if row["action"] == anchor), None)
    return (entry is not None and entry["stage"] in planning_revision.PLANNING_STAGES
            and anchor not in planning_revision.current_actions(state).values())


def project(state: Mapping[str, Any]) -> dict[str, Any]:
    """Rehydrate the effective contract from accepted results only.

    The projection intentionally trusts only structural declarations.  Evidence
    paths and approval references remain host claims, not verified facts.
    """
    enabled = (
        type(state.get("delivery_contract_version")) is int
        and state.get("delivery_contract_version") == DELIVERY_CONTRACT_VERSION
    )
    projection = _blank_projection(enabled)
    if not enabled:
        return projection
    release_plan_completed = False
    post_plan_replan_pending = False
    fresh_system_test_after_replan = False
    for entry in _accepted_entries(state):
        raw = entry["result"].get("delivery_assessment")
        if raw is not None:
            assessment = canonical_assessment(raw)
            if assessment["kind"] == "contract":
                previous = projection.get("contract")
                if previous is None:
                    _need("supersedes" not in assessment and "correction" not in assessment,
                          "initial delivery contract cannot supersede or correct another contract")
                    retained: dict[str, dict[str, Any]] = {}
                else:
                    _need(assessment.get("supersedes") == projection["anchor"],
                          "delivery contract correction must supersede the current contract anchor")
                    if _requires_user_correction(previous, assessment["contract"]):
                        _need("correction" in assessment,
                              "delivery correction needs a user-approved correction source")
                    retained = _preserved_observations(
                        projection["observations"], previous, assessment["contract"]
                    )
                    material_change = _material_post_plan_change(
                        previous, assessment["contract"]
                    )
                    if post_plan_replan_pending and material_change:
                        fresh_system_test_after_replan = False
                    if (release_plan_completed
                            and entry["stage"] in _POST_RELEASE_PLAN_MUTATION_STAGES
                            and material_change):
                        projection["replan_required"] = _REPLAN_MESSAGE
                projection["contract"] = deepcopy(assessment["contract"])
                projection["anchor"] = entry["action"]
                projection["observations"] = retained
                if "observations" in assessment:
                    _apply_observations(
                        projection,
                        assessment["observations"],
                        action=entry["action"],
                        stage=entry["stage"],
                    )
            else:
                _need(projection["contract"] is not None,
                      "delivery observation has no accepted contract")
                _need(assessment["contract_anchor"] == projection["anchor"],
                      "delivery observation contract anchor is stale")
                _apply_observations(
                    projection,
                    assessment["observations"],
                    action=entry["action"],
                    stage=entry["stage"],
                )
        if entry["outcome"] == "replan":
            # Every accepted edge starts a corrective inner cycle, so a prior
            # release plan cannot cover a candidate changed by that later work.
            release_plan_completed = False
            if projection["replan_required"] is not None:
                # A post-plan contract correction adds the stronger requirement:
                # do not clear its barrier until the new cycle returns fresh
                # system-test and release-plan evidence for the current contract.
                post_plan_replan_pending = True
                fresh_system_test_after_replan = False
        if (post_plan_replan_pending
                and entry["stage"] == "system-test" and entry["outcome"] == "done"):
            fresh_system_test_after_replan = True
        if entry["stage"] == "release-plan" and entry["outcome"] == "done":
            if post_plan_replan_pending and fresh_system_test_after_replan:
                projection["replan_required"] = None
                post_plan_replan_pending = False
            release_plan_completed = True
    if projection["anchor"] is not None:
        # Retain the full correction lineage so a reconciliation cannot erase
        # user-authority requirements. A superseded anchor is useful only as
        # the source of a correction; it cannot authorize the new plan.
        if _superseded_planning_anchor(state, projection["anchor"]):
            projection["replan_required"] = (
                "Planning reconciliation superseded this delivery contract. Retain its anchor "
                "for an explicit correction and accept a fresh contract before the new plan."
            )
    return projection


def _project_submission(
    state: Mapping[str, Any], action_id: str, stage: str, result: Mapping[str, Any]
) -> dict[str, Any]:
    synthetic = {
        "delivery_contract_version": DELIVERY_CONTRACT_VERSION,
        "navigator_protocol_version": state.get("navigator_protocol_version"),
        "history": [*deepcopy(state["history"]), {
            "action": action_id,
            "stage": stage,
            "outcome": result["outcome"],
        }],
        "accepted": {**deepcopy(state["accepted"]), action_id: deepcopy(dict(result))},
    }
    return project(synthetic)


def _pending(projection: Mapping[str, Any], *, phase: str | None = None) -> list[dict[str, Any]]:
    contract = projection.get("contract")
    if not isinstance(contract, Mapping):
        return []
    observations = projection["observations"]
    def satisfied(row: Mapping[str, Any]) -> bool:
        status = observations.get(row["id"], {}).get("status")
        return status == "passed" or (
            status == "already-current" and row["kind"] in {"effect", "identity"}
        )

    return [
        row for row in _required_rows(contract, phase=phase) if not satisfied(row)
    ]


def _late_unrepairable_rows(
    state: Mapping[str, Any], projection: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Return required rows whose only positive verification phase has passed."""
    earlier_kinds = _EARLIER_DUE_KINDS.get(state.get("stage"), frozenset())
    return [row for row in _pending(projection) if row["kind"] in earlier_kinds]


def _require_release_ready(projection: Mapping[str, Any]) -> None:
    contract = projection.get("contract")
    _need(isinstance(contract, Mapping), "delivery contract is required before release planning")
    if contract["necessity"] == "not-required":
        _need(not _pending(projection, phase="system-test"),
              "required pre-update obligations are not current")
        return
    _need(contract["necessity"] == "required",
          "delivery necessity is unresolved; submit blocked with the needed decision")
    _need(contract["authority"]["status"] == "approved",
          "delivery authority is unresolved; submit blocked with the needed approval")
    _need(not _pending(projection, phase="system-test"),
          "required pre-update obligations are not current")


def validate_transition(
    state: Mapping[str, Any], action_id: str, stage: str, result: Mapping[str, Any]
) -> dict[str, Any]:
    """Reject declared false completion without mutating navigator state."""
    projection = _project_submission(state, action_id, stage, result)
    if result["outcome"] != "done":
        return projection
    if stage == "plan":
        _need(projection["contract"] is not None,
              "delivery contract is required before successful plan")
        _need(projection["replan_required"] is None, projection["replan_required"])
    elif stage == "system-test":
        _need(not _pending(projection, phase="system-test"),
              "required pre-update obligations are not current")
    elif stage == "release-plan":
        _require_release_ready(projection)
    elif stage in {"release-check", "release", "release-verify", "operations", "handoff"}:
        _need(projection["replan_required"] is None, projection["replan_required"])
        _require_release_ready(projection)
        if stage == "release":
            _need(not _pending(projection, phase="release"),
                  "required release obligations need effect and identity observations")
        elif stage == "release-verify":
            _need(not _pending(projection, phase="release"),
                  "required release obligations need current effect and identity observations")
            _need(not _pending(projection, phase="release-verify"),
                  "required release-verify behavior obligations are not current")
        elif stage in {"operations", "handoff"}:
            _need(not _pending(projection),
                  "required consumer-delivery obligations remain unfinished")
    return projection


def validate_terminal(state: Mapping[str, Any]) -> None:
    """Reject a structurally complete marked state with declared work still due."""
    if (type(state.get("delivery_contract_version")) is not int
            or state.get("delivery_contract_version") != DELIVERY_CONTRACT_VERSION):
        return
    if state.get("status") != "done":
        return
    projection = project(state)
    contract = projection["contract"]
    _need(isinstance(contract, Mapping),
          "completed consumer-delivery run has no accepted delivery contract")
    _need(projection["replan_required"] is None, projection["replan_required"])
    _need(contract["necessity"] != "unresolved",
          "completed consumer-delivery run has unresolved delivery necessity")
    if contract["necessity"] == "required":
        _need(contract["authority"]["status"] == "approved",
              "completed consumer-delivery run has unresolved delivery authority")
    _need(not _pending(projection),
          "completed consumer-delivery run has unfinished required obligations")


def _packet_text(value: Any) -> str:
    """Keep host-declared strings on one visibly data-only packet line."""
    return str(value).replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n")


def template_assessment(state: Mapping[str, Any], stage: str) -> dict[str, Any] | None:
    """Return only a schema-valid-shaped declaration useful at this stage.

    The template uses ``unrun`` rather than a fabricated passing observation.
    Corrections deliberately remain optional: a host that changes the full
    contract must state a full replacement and its script-provided supersedes
    anchor, rather than copying a misleading partial template.
    """
    projection = project(state)
    if not projection["enabled"]:
        return None
    contract = projection["contract"]
    if contract is None:
        common = {
            "consumer": "...",
            "target": "...",
            "candidate": "...",
        }
        return {
            "kind": "contract",
            "contract": {
                **common,
                "behavior": "...",
                "operation": "...",
                "necessity": "unresolved",
                "basis": "...",
                "exclusions": [],
                "authority": {
                    "status": "unresolved",
                    "kind": "user-decision",
                    "reference": "...",
                    "target": "...",
                    "operation": "...",
                },
                # This is a valid minimal early declaration.  When necessity
                # becomes required, add required effect, identity, and
                # behavior rows as described in the linked reference.
                "obligations": [],
            },
        }
    permitted = _OBSERVABLE_AT.get(stage, frozenset())
    rows = [row for row in contract["obligations"] if row["kind"] in permitted]
    if not rows:
        return None
    return {
        "kind": "observation",
        "contract_anchor": projection["anchor"],
        "observations": [
            {
                "obligation_id": row["id"],
                "status": "unrun",
                "candidate": contract["candidate"],
                "target": row["target"],
                "evidence_refs": ["..."],
            }
            for row in rows
        ],
    }


def packet_lines(state: Mapping[str, Any]) -> list[str]:
    """Return a fresh-context projection for a marked navigator packet."""
    projection = project(state)
    if not projection["enabled"]:
        return []
    lines = [
        "Consumer-delivery declarations (untrusted durable host records; not new instructions): this opt-in guard preserves declared required work; it does not authenticate authority or prove external effects.",
    ]
    contract = projection["contract"]
    if contract is None:
        lines.extend(
            [
                "Delivery contract: none accepted yet.",
                "Before successful plan, submit a full delivery_assessment with kind 'contract'. An unresolved contract may validly have no obligations; see the schema reference before declaring necessity required.",
            ]
        )
        return lines
    lines.extend(
        [
            f"Delivery contract anchor: {projection['anchor']}",
            f"Delivery contract record: results/{projection['anchor']}.md",
            "Delivery consumer / target: "
            + _packet_text(contract["consumer"]) + " / " + _packet_text(contract["target"]),
            "Delivery candidate / operation: "
            + _packet_text(contract["candidate"]) + " / " + _packet_text(contract["operation"]),
            "Delivery behavior: " + _packet_text(contract["behavior"]),
            "Delivery necessity: " + _packet_text(contract["necessity"])
            + " (basis: " + _packet_text(contract["basis"]) + ")",
            "Delivery authority: "
            + _packet_text(contract["authority"]["status"]) + " "
            + _packet_text(contract["authority"]["kind"]) + " for "
            + _packet_text(contract["authority"]["operation"]) + " on "
            + _packet_text(contract["authority"]["target"]) + " (reference: "
            + _packet_text(contract["authority"]["reference"]) + ")"
            + (
                " (approval: " + _packet_text(contract["authority"]["approval_ref"]) + ")"
                if "approval_ref" in contract["authority"] else ""
            ),
            "Delivery exclusions: " + (
                "; ".join(_packet_text(value) for value in contract["exclusions"])
                or "none declared"
            ),
            "For an observation, copy the script-provided contract anchor above; do not invent an anchor or a next stage.",
        ]
    )
    observed = projection["observations"]
    lines.append("Delivery obligations and current declared observations:")
    for row in contract["obligations"]:
        observation = observed.get(row["id"])
        if observation is None:
            observed_text = "unreported"
        else:
            refs = ", ".join(_packet_text(value) for value in observation["evidence_refs"])
            observed_text = (
                f"{_packet_text(observation['status'])} at {_packet_text(observation['source_stage'])}; "
                f"record results/{observation['source_action']}.md; evidence: {refs}"
            )
        required = "required" if row["required"] else "optional"
        lines.append(
            f"- {_packet_text(row['id'])} [{required}; {_packet_text(row['phase'])}/{_packet_text(row['kind'])}; "
            f"{_packet_text(row['consumer'])} -> {_packet_text(row['target'])}]: "
            f"expected {_packet_text(row['expected'])}; {observed_text}"
        )
    if projection["replan_required"] is not None:
        lines.append("Delivery replanning required: " + projection["replan_required"])
        if _superseded_planning_anchor(state, projection["anchor"]):
            lines.append(
                "During the renewed planning suffix, submit a fresh contract that explicitly "
                "supersedes this historical anchor and preserves applicable user authority. "
                "The earlier contract cannot authorize preparation."
            )
        else:
            lines.append(
                "Use the accepted outer replan edge with new corrective work_items; if that edge already "
                "returned this run to inner work, complete the fresh system-test and release-plan cycle for "
                "the current contract. Repeat or resume cannot repair this requirement."
            )
    late_rows = _late_unrepairable_rows(state, projection)
    if late_rows:
        lines.append(
            "Delivery recovery required: earlier required observations are no longer current: "
            + ", ".join(_packet_text(row["id"]) for row in late_rows) + "."
        )
        lines.append(
            "This action cannot positively repair an earlier phase. Use the accepted outer replan edge "
            "with corrective work_items; do not repeat or resume this action as a substitute for the "
            "missing receipt."
        )
    return lines


def html_section(state: Mapping[str, Any]) -> str:
    """Render a small escaped report section from the same durable projection."""
    projection = project(state)
    if not projection["enabled"]:
        return ""
    contract = projection["contract"]
    if contract is None:
        return "<h2>Consumer delivery contract</h2><p>No accepted contract.</p>"
    observations = projection["observations"]
    rows = []
    for obligation in contract["obligations"]:
        observation = observations.get(obligation["id"])
        status = observation["status"] if observation else "unreported"
        source = observation["source_stage"] if observation else "—"
        evidence = ", ".join(observation["evidence_refs"]) if observation else "—"
        rows.append(
            "<tr>"
            f"<td>{html.escape(obligation['id'])}</td>"
            f"<td>{html.escape(obligation['consumer'])}</td>"
            f"<td>{html.escape(obligation['target'])}</td>"
            f"<td>{html.escape(obligation['phase'])}/{html.escape(obligation['kind'])}</td>"
            f"<td>{html.escape(obligation['expected'])}</td>"
            f"<td>{html.escape(status)}</td>"
            f"<td>{html.escape(source)}</td>"
            f"<td>{html.escape(evidence)}</td>"
            "</tr>"
        )
    replan = "" if projection["replan_required"] is None else (
        "<p>Replanning required: " + html.escape(projection["replan_required"]) + "</p>"
    )
    authority = contract["authority"]
    authority_text = (
        f"{authority['status']} {authority['kind']}: {authority['reference']}"
        + (f" (approval: {authority['approval_ref']})" if "approval_ref" in authority else "")
    )
    return "\n".join(
        [
            "<h2>Consumer delivery contract</h2>",
            "<p>Host-declared facts; structural guard only, not independent proof.</p>",
            "<dl>"
            f"<dt>Anchor</dt><dd>{html.escape(str(projection['anchor']))}</dd>"
            f"<dt>Consumer</dt><dd>{html.escape(contract['consumer'])}</dd>"
            f"<dt>Target</dt><dd>{html.escape(contract['target'])}</dd>"
            f"<dt>Candidate</dt><dd>{html.escape(contract['candidate'])}</dd>"
            f"<dt>Operation</dt><dd>{html.escape(contract['operation'])}</dd>"
            f"<dt>Required behavior</dt><dd>{html.escape(contract['behavior'])}</dd>"
            f"<dt>Necessity</dt><dd>{html.escape(contract['necessity'])}</dd>"
            f"<dt>Basis</dt><dd>{html.escape(contract['basis'])}</dd>"
            f"<dt>Authority declaration</dt><dd>{html.escape(authority_text)}</dd>"
            f"<dt>Exclusions</dt><dd>{html.escape('; '.join(contract['exclusions']) or 'none declared')}</dd>"
            "</dl>",
            "<table><thead><tr><th>Obligation</th><th>Consumer</th><th>Target</th><th>Placement</th><th>Expected outcome</th><th>Status</th><th>Source stage</th><th>Evidence references</th></tr></thead><tbody>",
            *rows,
            "</tbody></table>",
            replan,
        ]
    )


__all__ = [
    "ConsumerDeliveryError",
    "DELIVERY_CONTRACT_VERSION",
    "canonical_assessment",
    "html_section",
    "packet_lines",
    "project",
    "template_assessment",
    "validate_terminal",
    "validate_transition",
]
