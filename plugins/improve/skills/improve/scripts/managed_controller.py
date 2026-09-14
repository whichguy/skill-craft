"""Pure phase and convergence controller for a managed Improve invocation.

This module deliberately has no filesystem, Git, process, Markdown, or CLI
dependency.  A consumer validates its own typed receipts and external effects,
then supplies compact evidence references to ``apply``.  The controller owns
only the legal child phases, completed-pass counter, and terminal proof shape.

It is intentionally separate from Improve's standalone until-loop runtime.
The standalone runtime keeps its established JSON state and behavior; a
ShipLoop-style consumer persists the returned records in its own durable state.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any


VERSION = "improve-managed-controller/v1"
BINDING_KIND = "managed-improve-binding"
CHILD_KIND = "managed-improve-child"
CERTIFICATE_KIND = "managed-improve-certificate"

INCOMPLETE_STATUSES = frozenset(
    ("blocked", "needs-prerequisite", "needs-replan", "stopped")
)
TERMINAL_STATUSES = frozenset((*INCOMPLETE_STATUSES, "converged"))

# Planning is deliberately three separate target profiles.  A research child
# never silently progresses into behavior or specification work.
PROFILE_STAGES: dict[str, tuple[str, ...]] = {
    "research": (
        "research-review",
        "research-plan",
        "research-apply",
        "research-verify",
        "research-commit",
        "research-finalize",
    ),
    "behavior": (
        "behavior-review",
        "behavior-plan",
        "behavior-apply",
        "behavior-verify",
        "behavior-commit",
        "behavior-finalize",
    ),
    "spec": (
        "spec-review",
        "spec-plan",
        "spec-apply",
        "spec-verify",
        "spec-commit",
        "spec-finalize",
    ),
    "objective": (
        "objective-review",
        "objective-plan",
        "objective-apply",
        "objective-verify",
        "objective-commit",
        "objective-finalize",
    ),
    "step-plan": (
        "step-plan-review",
        "step-plan-disposition",
        "step-plan-revise",
        "step-plan-verify",
        "step-plan-commit",
        "step-plan-finalize",
    ),
    "product": (
        "review",
        "improve-plan",
        "improve-plan-verify",
        "improve-apply",
        "test-refine",
        "test-author",
        "iteration-document",
        "skill-validate",
        "verify",
        "carry-forward",
        "commit",
        "final-verify",
    ),
}

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,255}\Z")
_SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


class ManagedImproveError(ValueError):
    """A managed Improve binding, child record, or result is unsafe to use."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ManagedImproveError(message)


def _json(value: Any, label: str) -> Any:
    """Return a detached canonical JSON-compatible value without doing I/O."""
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return json.loads(encoded)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ManagedImproveError(f"{label} must be JSON-compatible") from exc


def _digest(value: Any) -> str:
    canonical = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    _need(isinstance(value, Mapping), f"{label} must be an object")
    normalized = _json(dict(value), label)
    _need(isinstance(normalized, dict), f"{label} must be an object")
    return normalized


def _text(value: Any, label: str) -> str:
    _need(isinstance(value, str) and value.strip(), f"{label} is required")
    _need(len(value) <= 4096 and "\x00" not in value, f"{label} is invalid")
    return value


def _id(value: Any, label: str) -> str:
    value = _text(value, label)
    _need(bool(_ID_RE.fullmatch(value)), f"{label} must be a safe stable ID")
    return value


def _sha(value: Any, label: str) -> str:
    _need(isinstance(value, str) and bool(_SHA_RE.fullmatch(value)), f"{label} is invalid")
    return value


def _commit(value: Any, label: str) -> str:
    _need(
        isinstance(value, str) and bool(_COMMIT_RE.fullmatch(value)),
        f"{label} must be a full lowercase Git SHA",
    )
    return value


def _refs(value: Any, label: str) -> list[str]:
    _need(isinstance(value, list) and value, f"{label} requires at least one reference")
    normalized: list[str] = []
    seen: set[str] = set()
    for row in value:
        ref = _text(row, label)
        _need(ref not in seen, f"{label} cannot repeat a reference")
        seen.add(ref)
        normalized.append(ref)
    return normalized


def _input_identity(value: Any) -> dict[str, Any]:
    identity = _mapping(value, "input_identity")
    _need(identity, "input_identity cannot be empty")
    return identity


def _output_identity(value: Any) -> dict[str, Any]:
    identity = _mapping(value, "output_identity")
    _need(identity, "output_identity cannot be empty")
    _sha(identity.get("identity_digest"), "output_identity identity_digest")
    return identity


def _review_policy(value: Any) -> dict[str, bool]:
    if value is None:
        return {"required": False, "fallback_allowed": False}
    policy = _mapping(value, "independent_review")
    _need(
        set(policy) == {"required", "fallback_allowed"},
        "independent_review has unsupported fields",
    )
    _need(
        type(policy["required"]) is bool
        and type(policy["fallback_allowed"]) is bool,
        "independent_review fields must be booleans",
    )
    _need(
        policy["required"] or not policy["fallback_allowed"],
        "independent review fallback requires independent review to be required",
    )
    return {"required": policy["required"], "fallback_allowed": policy["fallback_allowed"]}


def _profile(value: Any) -> str:
    _need(isinstance(value, str) and value in PROFILE_STAGES, "unsupported managed Improve profile")
    return value


def _commit_policy(value: Any) -> str:
    _need(
        value == "audit-every-iteration",
        "managed Improve requires explicit audit-every-iteration commit policy",
    )
    return "audit-every-iteration"


def _binding_payload(
    *,
    parent_action: str,
    child_action_id: str,
    profile: str,
    input_identity: Mapping[str, Any],
    policy_digest: str,
    executor_digest: str,
    commit_policy: str,
    independent_review: Mapping[str, bool],
) -> dict[str, Any]:
    identity = _input_identity(input_identity)
    return {
        "version": VERSION,
        "kind": BINDING_KIND,
        "parent_action": _id(parent_action, "parent_action"),
        "child_action_id": _id(child_action_id, "child_action_id"),
        "profile": _profile(profile),
        "input_identity": identity,
        "input_identity_sha256": _digest(identity),
        "policy_digest": _sha(policy_digest, "policy_digest"),
        "executor_digest": _sha(executor_digest, "executor_digest"),
        "commit_policy": _commit_policy(commit_policy),
        "independent_review": _review_policy(independent_review),
    }


def new_binding(
    *,
    parent_action: str,
    child_action_id: str,
    profile: str,
    input_identity: Mapping[str, Any],
    policy_digest: str,
    executor_digest: str,
    commit_policy: str = "audit-every-iteration",
    independent_review: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    """Create an immutable, content-addressed child binding.

    ``input_identity`` is deliberately consumer-defined, but is frozen and
    digested here.  The consumer keeps any mutable execution projection outside
    the binding.
    """
    payload = _binding_payload(
        parent_action=parent_action,
        child_action_id=child_action_id,
        profile=profile,
        input_identity=input_identity,
        policy_digest=policy_digest,
        executor_digest=executor_digest,
        commit_policy=commit_policy,
        independent_review=_review_policy(independent_review),
    )
    return {**payload, "binding_sha256": _digest(payload)}


def assert_binding(value: Any) -> dict[str, Any]:
    """Reject altered, partial, stale, or non-versioned bindings."""
    binding = _mapping(value, "managed Improve binding")
    required = {
        "version",
        "kind",
        "parent_action",
        "child_action_id",
        "profile",
        "input_identity",
        "input_identity_sha256",
        "policy_digest",
        "executor_digest",
        "commit_policy",
        "independent_review",
        "binding_sha256",
    }
    _need(set(binding) == required, "managed Improve binding has unsupported fields")
    _need(binding["version"] == VERSION and binding["kind"] == BINDING_KIND, "unsupported managed Improve binding")
    payload = _binding_payload(
        parent_action=binding["parent_action"],
        child_action_id=binding["child_action_id"],
        profile=binding["profile"],
        input_identity=binding["input_identity"],
        policy_digest=binding["policy_digest"],
        executor_digest=binding["executor_digest"],
        commit_policy=binding["commit_policy"],
        independent_review=binding["independent_review"],
    )
    _need(
        binding.get("input_identity_sha256") == payload["input_identity_sha256"],
        "managed Improve binding input identity digest mismatch",
    )
    _need(
        binding.get("binding_sha256") == _digest(payload),
        "managed Improve binding digest mismatch",
    )
    return {**payload, "binding_sha256": binding["binding_sha256"]}


def _initial_phase(profile: str) -> str:
    return PROFILE_STAGES[profile][0]


def _review_phase(profile: str) -> str:
    return PROFILE_STAGES[profile][0]


def _commit_phase(profile: str) -> str:
    return PROFILE_STAGES[profile][-2]


def _final_phase(profile: str) -> str:
    return PROFILE_STAGES[profile][-1]


def _execution(value: Any, *, phase: str | None, child_action_id: str) -> dict[str, Any]:
    if value is None:
        return {
            "phase": phase,
            "stage": "managed-improve",
            "action": child_action_id,
            "completed_actions": [],
            "overlay": {},
        }
    execution = _mapping(value, "managed Improve execution projection")
    _need(
        set(execution) == {"phase", "stage", "action", "completed_actions", "overlay"},
        "managed Improve execution projection has unsupported fields",
    )
    _need(execution["phase"] == phase, "execution projection phase disagrees with child phase")
    _text(execution["stage"], "execution projection stage")
    _text(execution["action"], "execution projection action")
    _need(isinstance(execution["completed_actions"], list), "execution completed_actions must be a list")
    completed = _json(execution["completed_actions"], "execution completed_actions")
    _need(isinstance(completed, list), "execution completed_actions must be a list")
    overlay = _mapping(execution["overlay"], "execution overlay")
    return {
        "phase": phase,
        "stage": execution["stage"],
        "action": execution["action"],
        "completed_actions": completed,
        "overlay": overlay,
    }


def decide(passes: list[dict[str, Any]], *, open_findings: list[Any]) -> dict[str, Any]:
    """Derive two-trivial readiness exactly as ShipLoop's existing helper does.

    This remains readiness rather than success.  A final fresh-evidence phase
    is still required before a managed invocation can become ``converged``.
    """
    if not isinstance(passes, list) or not isinstance(open_findings, list):
        raise ManagedImproveError("managed Improve requires completed-pass and open-finding lists")
    ids: set[str] = set()
    commits: set[str] = set()
    streak = 0
    for row in passes:
        if not isinstance(row, Mapping):
            raise ManagedImproveError("managed Improve pass must be a record")
        pass_id = row.get("id")
        commit = row.get("commit")
        if not isinstance(pass_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", pass_id):
            raise ManagedImproveError("managed Improve pass requires a safe stable ID")
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
            raise ManagedImproveError("managed Improve pass requires a full audit commit SHA")
        if pass_id in ids or commit in commits:
            raise ManagedImproveError("managed Improve repeated pass or commit cannot count twice")
        if row.get("verified") is not True:
            raise ManagedImproveError("managed Improve cannot count an unverified pass")
        if row.get("outcome") not in ("material", "trivial"):
            raise ManagedImproveError("managed Improve pass outcome must be material or trivial")
        ids.add(pass_id)
        commits.add(commit)
        streak = streak + 1 if row["outcome"] == "trivial" else 0
    done_when = streak >= 2 and not open_findings
    return {"phase": "ready" if done_when else "active", "trivial_streak": streak}


def _flags(profile: str, phase: str, value: Any) -> dict[str, str]:
    if value is None:
        flags: dict[str, Any] = {}
    else:
        flags = _mapping(value, "managed Improve route flags")

    if profile == "step-plan" and phase == "step-plan-review":
        _need(set(flags) == {"disposition"}, "step-plan review requires an explicit disposition flag")
        _need(
            flags["disposition"] in {"required", "not-required"},
            "step-plan disposition must be required or not-required",
        )
        return {"disposition": flags["disposition"]}

    if profile == "product" and phase == "iteration-document":
        _need(
            set(flags) == {"documentation_disposition", "skill_disposition"},
            "iteration documentation requires explicit documentation and skill dispositions",
        )
        _need(
            flags["documentation_disposition"] in {"updated", "not-needed"},
            "documentation_disposition must be updated or not-needed",
        )
        _need(
            flags["skill_disposition"] in {"validate", "not-needed"},
            "skill_disposition must be validate or not-needed",
        )
        return {
            "documentation_disposition": flags["documentation_disposition"],
            "skill_disposition": flags["skill_disposition"],
        }

    if profile == "product" and phase == "carry-forward":
        _need(
            set(flags) == {"disposition"},
            "carry-forward requires an explicit disposition flag",
        )
        _need(
            flags["disposition"] in {"continue", "pause", "repair"},
            "carry-forward disposition must be continue, pause, or repair",
        )
        return {"disposition": flags["disposition"]}

    _need(not flags, f"{phase} does not accept route flags")
    return {}


def _repair_flags(profile: str, value: Any) -> dict[str, str]:
    """Accept the one recovery disposition that cannot be inferred from review."""
    if value is None:
        flags: dict[str, Any] = {}
    else:
        flags = _mapping(value, "managed Improve repair flags")
    if profile != "step-plan":
        _need(not flags, "only step-plan repair accepts route flags")
        return {}
    if not flags:
        return {}
    _need(set(flags) == {"disposition"}, "step-plan repair requires one disposition flag")
    _need(
        flags["disposition"] in {"required", "not-required"},
        "step-plan repair disposition must be required or not-required",
    )
    return {"disposition": flags["disposition"]}


def route(
    profile: str,
    current_stage: str,
    event: str = "complete",
    *,
    passes: list[dict[str, Any]] | None = None,
    open_findings: list[Any] | None = None,
    flags: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Select the only legal next phase for a managed child.

    Callers may not provide a next stage.  A commit adds a completed pass before
    this function is called; if its evidence is not ready, the controller loops
    to the profile review phase.  The final phase is reachable only after two
    current trivial passes and no open findings.
    """
    profile = _profile(profile)
    _need(current_stage in PROFILE_STAGES[profile], "stage is not legal for managed Improve profile")
    _need(
        event == "complete" or event == "repair" or event in INCOMPLETE_STATUSES,
        "unsupported managed Improve event",
    )
    if event in INCOMPLETE_STATUSES:
        return {"status": event, "current_phase": None, "paused": False}
    if event == "repair":
        repair_flags = _repair_flags(profile, flags)
        if profile == "step-plan" and repair_flags.get("disposition") == "required":
            return {
                "status": "active",
                "current_phase": "step-plan-disposition",
                "paused": True,
                "reset_convergence": True,
            }
        return {
            "status": "active",
            "current_phase": _review_phase(profile),
            "paused": False,
            "reset_convergence": True,
        }
    _need(event == "complete", "unsupported managed Improve event")

    normalized_flags = _flags(profile, current_stage, flags)
    if profile == "step-plan" and current_stage == "step-plan-review":
        return {
            "status": "active",
            "current_phase": (
                "step-plan-disposition"
                if normalized_flags["disposition"] == "required"
                else "step-plan-revise"
            ),
            "paused": False,
        }
    if profile == "step-plan" and current_stage == "step-plan-disposition":
        # A disposition rebinds the candidate and starts a fresh review pass.
        return {"status": "active", "current_phase": "step-plan-review", "paused": False}
    if profile == "product" and current_stage == "iteration-document":
        return {
            "status": "active",
            "current_phase": (
                "skill-validate"
                if normalized_flags["skill_disposition"] == "validate"
                else "verify"
            ),
            "paused": False,
        }
    if profile == "product" and current_stage == "carry-forward":
        disposition = normalized_flags["disposition"]
        if disposition == "pause":
            return {"status": "active", "current_phase": "carry-forward", "paused": True}
        if disposition == "repair":
            return {
                "status": "active",
                "current_phase": "review",
                "paused": False,
                "reset_convergence": True,
            }
        return {"status": "active", "current_phase": "commit", "paused": False}

    if current_stage == _commit_phase(profile):
        if passes is None:
            passes = []
        if open_findings is None:
            open_findings = []
        readiness = decide(passes, open_findings=open_findings)
        return {
            "status": "active",
            "current_phase": _final_phase(profile)
            if readiness["phase"] == "ready"
            else _review_phase(profile),
            "trivial_streak": readiness["trivial_streak"],
            "paused": False,
        }

    if current_stage == _final_phase(profile):
        if passes is None:
            passes = []
        if open_findings is None:
            open_findings = []
        readiness = decide(passes, open_findings=open_findings)
        _need(
            readiness["phase"] == "ready",
            "managed Improve final verification requires two verified trivial passes and no open findings",
        )
        return {
            "status": "converged",
            "current_phase": None,
            "trivial_streak": readiness["trivial_streak"],
            "paused": False,
        }

    stages = PROFILE_STAGES[profile]
    next_index = stages.index(current_stage) + 1
    _need(next_index < len(stages), "managed Improve stage cannot be advanced")
    return {"status": "active", "current_phase": stages[next_index], "paused": False}


def _independent_review(value: Any, required: Mapping[str, bool]) -> dict[str, Any] | None:
    if value is None:
        _need(not required["required"], "required independent review is missing")
        return None
    review = _mapping(value, "independent_review result")
    status = review.get("status")
    if status == "performed":
        _need(set(review) == {"status", "evidence_ref"}, "performed independent review has unsupported fields")
        return {"status": "performed", "evidence_ref": _text(review["evidence_ref"], "independent review evidence_ref")}
    _need(status == "unavailable", "independent review status is invalid")
    _need(
        required["required"] and required["fallback_allowed"],
        "independent reviewer unavailable without an allowed recorded fallback",
    )
    _need(
        set(review) == {"status", "fallback", "reason", "evidence_ref"}
        and review["fallback"] == "self-review",
        "independent review fallback must record self-review",
    )
    return {
        "status": "unavailable",
        "fallback": "self-review",
        "reason": _text(review["reason"], "independent review fallback reason"),
        "evidence_ref": _text(review["evidence_ref"], "independent review fallback evidence_ref"),
    }


def _completed_pass(value: Any, binding: Mapping[str, Any]) -> dict[str, Any]:
    row = _mapping(value, "completed_pass")
    allowed = {"id", "outcome", "verified", "commit", "evidence_ref", "independent_review"}
    _need(set(row) <= allowed and {"id", "outcome", "verified", "commit", "evidence_ref"} <= set(row), "completed_pass has unsupported or missing fields")
    _need(row["outcome"] in {"material", "trivial"}, "completed_pass outcome is invalid")
    _need(row["verified"] is True, "completed_pass must be verified")
    pass_id = _id(row["id"], "completed_pass id")
    _need(
        bool(re.fullmatch(r"[A-Za-z0-9_-]+", pass_id)),
        "completed_pass id must be compatible with convergence evidence",
    )
    normalized: dict[str, Any] = {
        "id": pass_id,
        "outcome": row["outcome"],
        "verified": True,
        "commit": _commit(row["commit"], "completed_pass commit"),
        "evidence_ref": _text(row["evidence_ref"], "completed_pass evidence_ref"),
    }
    review = _independent_review(row.get("independent_review"), binding["independent_review"])
    if review is not None:
        normalized["independent_review"] = review
    return normalized


def _fresh_evidence(value: Any, binding: Mapping[str, Any], output: Mapping[str, Any]) -> dict[str, Any]:
    evidence = _mapping(value, "fresh_evidence")
    required = {"binding_sha256", "action", "identity_digest", "checks", "evidence_ref", "result"}
    _need(set(evidence) == required, "fresh_evidence has unsupported or missing fields")
    _need(evidence["binding_sha256"] == binding["binding_sha256"], "fresh_evidence binding is stale")
    _id(evidence["action"], "fresh_evidence action")
    _need(
        evidence["identity_digest"] == output["identity_digest"],
        "fresh_evidence identity does not match output identity",
    )
    _sha(evidence["identity_digest"], "fresh_evidence identity_digest")
    _need(evidence["result"] == "passed", "fresh_evidence result is not passed")
    checks = evidence["checks"]
    _need(isinstance(checks, list) and checks, "fresh_evidence requires passed checks")
    normalized_checks: list[dict[str, str]] = []
    seen: set[str] = set()
    for check in checks:
        check = _mapping(check, "fresh_evidence check")
        _need(set(check) == {"id", "result", "evidence_ref"}, "fresh_evidence check has unsupported fields")
        check_id = _id(check["id"], "fresh_evidence check id")
        _need(check_id not in seen, "fresh_evidence cannot repeat a check")
        _need(check["result"] == "passed", "fresh_evidence check did not pass")
        seen.add(check_id)
        normalized_checks.append(
            {
                "id": check_id,
                "result": "passed",
                "evidence_ref": _text(check["evidence_ref"], "fresh_evidence check evidence_ref"),
            }
        )
    return {
        "binding_sha256": binding["binding_sha256"],
        "action": evidence["action"],
        "identity_digest": evidence["identity_digest"],
        "checks": normalized_checks,
        "evidence_ref": _text(evidence["evidence_ref"], "fresh_evidence evidence_ref"),
        "result": "passed",
    }


def _record(value: Any, binding: Mapping[str, Any], expected_sequence: int, expected_phase: str) -> dict[str, Any]:
    record = _mapping(value, "managed Improve phase record")
    _need(record.get("sequence") == expected_sequence, "managed Improve phase record sequence is invalid")
    _need(record.get("phase") == expected_phase, "managed Improve phase record phase is invalid")
    kind = record.get("kind")
    _need(
        kind == "complete" or kind in INCOMPLETE_STATUSES or kind in {"repair", "resume"},
        "managed Improve phase record kind is invalid",
    )
    base = {"sequence", "kind", "phase", "evidence_refs", "flags"}
    if kind in {"repair", "resume"}:
        _need(set(record) == base | {"reason"}, f"managed Improve {kind} record has unsupported fields")
        if kind == "repair":
            flags = _repair_flags(binding["profile"], record["flags"])
        else:
            _need(record["flags"] == {}, "managed Improve resume record cannot carry route flags")
            flags = {}
        return {
            "sequence": expected_sequence,
            "kind": kind,
            "phase": expected_phase,
            "evidence_refs": _refs(record.get("evidence_refs"), "phase evidence_refs"),
            "flags": flags,
            "reason": _text(record["reason"], f"managed Improve {kind} reason"),
        }
    if kind in INCOMPLETE_STATUSES:
        _need(set(record) == base | {"reason"}, "incomplete managed Improve record has unsupported fields")
        _need(record["flags"] == {}, "incomplete managed Improve record cannot carry route flags")
        return {
            "sequence": expected_sequence,
            "kind": kind,
            "phase": expected_phase,
            "evidence_refs": _refs(record.get("evidence_refs"), "phase evidence_refs"),
            "flags": {},
            "reason": _text(record["reason"], "incomplete managed Improve reason"),
        }

    allowed = set(base)
    if expected_phase == _commit_phase(binding["profile"]):
        allowed |= {"audit_commit", "completed_pass", "open_findings"}
    if expected_phase == _final_phase(binding["profile"]):
        allowed |= {"output_identity", "fresh_evidence"}
    _need(set(record) == allowed, "managed Improve complete record has unsupported or missing fields")
    normalized: dict[str, Any] = {
        "sequence": expected_sequence,
        "kind": "complete",
        "phase": expected_phase,
        "evidence_refs": _refs(record.get("evidence_refs"), "phase evidence_refs"),
        "flags": _flags(binding["profile"], expected_phase, record.get("flags")),
    }
    if expected_phase == _commit_phase(binding["profile"]):
        completed = _completed_pass(record["completed_pass"], binding)
        audit_commit = _commit(record["audit_commit"], "audit_commit")
        _need(
            audit_commit == completed["commit"],
            "audit_commit must match the completed review pass commit",
        )
        _need(isinstance(record["open_findings"], list), "open_findings must be a list")
        normalized.update(
            audit_commit=audit_commit,
            completed_pass=completed,
            open_findings=_json(record["open_findings"], "open_findings"),
        )
    if expected_phase == _final_phase(binding["profile"]):
        output = _output_identity(record["output_identity"])
        normalized.update(
            output_identity=output,
            fresh_evidence=_fresh_evidence(record["fresh_evidence"], binding, output),
        )
    return normalized


def _replay(
    binding: Mapping[str, Any], records: list[Any]
) -> tuple[
    str,
    str | None,
    bool,
    list[dict[str, Any]],
    list[Any],
    dict[str, Any] | None,
    dict[str, Any] | None,
]:
    """Recalculate a child state from phase records so state is never trusted."""
    profile = binding["profile"]
    status = "active"
    phase: str | None = _initial_phase(profile)
    paused = False
    passes: list[dict[str, Any]] = []
    history_passes: list[dict[str, Any]] = []
    open_findings: list[Any] = []
    output: dict[str, Any] | None = None
    fresh: dict[str, Any] | None = None
    interrupted_phase: str | None = None
    for index, raw in enumerate(records, start=1):
        if status in INCOMPLETE_STATUSES:
            _need(
                interrupted_phase is not None,
                "managed Improve incomplete child lost its interrupted phase",
            )
            record = _record(raw, binding, index, interrupted_phase)
            _need(record["kind"] == "resume", "managed Improve incomplete child requires an explicit resume")
            status = "active"
            phase = interrupted_phase
            paused = False
            interrupted_phase = None
            continue
        _need(status == "active" and phase is not None, "managed Improve has records after terminal state")
        record = _record(raw, binding, index, phase)
        if record["kind"] == "resume":
            _need(paused, "managed Improve resume requires an incomplete or paused child")
            paused = False
            continue
        _need(
            not paused or record["kind"] != "complete",
            "managed Improve paused child requires explicit resume before completion",
        )
        if record["kind"] in INCOMPLETE_STATUSES:
            interrupted_phase = phase
            route_result = route(profile, phase, record["kind"])
        elif record["kind"] == "repair":
            route_result = route(profile, phase, "repair", flags=record["flags"])
            # Old records remain durable history, but a repair begins a new
            # convergence epoch and cannot inherit its predecessor's streak.
            passes = []
            open_findings = []
            output = None
            fresh = None
        else:
            if phase == _commit_phase(profile):
                history_passes.append(record["completed_pass"])
                passes.append(record["completed_pass"])
                open_findings = record["open_findings"]
            if phase == _final_phase(profile):
                output = record["output_identity"]
                fresh = record["fresh_evidence"]
            route_result = route(
                profile,
                phase,
                passes=passes,
                open_findings=open_findings,
                flags=record["flags"],
            )
            if route_result.get("reset_convergence") is True:
                passes = []
                open_findings = []
                output = None
                fresh = None
        status = route_result["status"]
        phase = route_result["current_phase"]
        paused = route_result.get("paused") is True
    # Validate the active epoch for readiness and all historic records for
    # duplicate pass/commit detection after a repair reset.
    decide(passes, open_findings=open_findings)
    decide(history_passes, open_findings=[])
    return status, phase, paused, passes, open_findings, output, fresh


def new_child(binding: Mapping[str, Any]) -> dict[str, Any]:
    """Start a child at its profile's first review phase."""
    binding = assert_binding(binding)
    phase = _initial_phase(binding["profile"])
    return {
        "version": VERSION,
        "kind": CHILD_KIND,
        "binding": binding,
        "binding_sha256": binding["binding_sha256"],
        "profile": binding["profile"],
        "status": "active",
        "current_phase": phase,
        "paused": False,
        "passes": [],
        "open_findings": [],
        "phase_records": [],
        "output_identity": None,
        "output_identity_sha256": None,
        "fresh_evidence": None,
        "execution": _execution(None, phase=phase, child_action_id=binding["child_action_id"]),
    }


def assert_child(value: Any) -> dict[str, Any]:
    """Validate a child by replaying controller-owned phase records."""
    child = _mapping(value, "managed Improve child")
    required = {
        "version",
        "kind",
        "binding",
        "binding_sha256",
        "profile",
        "status",
        "current_phase",
        "paused",
        "passes",
        "open_findings",
        "phase_records",
        "output_identity",
        "output_identity_sha256",
        "fresh_evidence",
        "execution",
    }
    _need(set(child) == required, "managed Improve child has unsupported fields")
    _need(child["version"] == VERSION and child["kind"] == CHILD_KIND, "unsupported managed Improve child")
    binding = assert_binding(child["binding"])
    _need(child["binding_sha256"] == binding["binding_sha256"], "managed Improve child binding mismatch")
    _need(child["profile"] == binding["profile"], "managed Improve child profile mismatch")
    _need(isinstance(child["phase_records"], list), "managed Improve phase_records must be a list")
    status, phase, paused, passes, findings, output, fresh = _replay(
        binding, child["phase_records"]
    )
    _need(child["status"] == status, "managed Improve child status disagrees with records")
    _need(child["current_phase"] == phase, "managed Improve child phase disagrees with records")
    _need(type(child["paused"]) is bool and child["paused"] == paused, "managed Improve child pause state disagrees with records")
    _need(_json(child["passes"], "managed Improve passes") == passes, "managed Improve child passes disagree with records")
    _need(_json(child["open_findings"], "managed Improve open_findings") == findings, "managed Improve child findings disagree with records")
    _need(child["output_identity"] == output, "managed Improve child output identity disagrees with records")
    _need(
        child["output_identity_sha256"] == (_digest(output) if output is not None else None),
        "managed Improve child output identity digest disagrees with records",
    )
    _need(child["fresh_evidence"] == fresh, "managed Improve child fresh evidence disagrees with records")
    if status == "converged":
        readiness = decide(passes, open_findings=findings)
        _need(readiness["phase"] == "ready" and output is not None and fresh is not None, "managed Improve convergence lacks current final evidence")
    elif status in INCOMPLETE_STATUSES:
        _need(phase is None and not paused, "incomplete managed Improve child retains an active state")
    else:
        _need(status == "active" and phase in PROFILE_STAGES[binding["profile"]], "managed Improve active child phase is invalid")
    execution = _execution(child["execution"], phase=phase, child_action_id=binding["child_action_id"])
    return {
        "version": VERSION,
        "kind": CHILD_KIND,
        "binding": binding,
        "binding_sha256": binding["binding_sha256"],
        "profile": binding["profile"],
        "status": status,
        "current_phase": phase,
        "paused": paused,
        "passes": passes,
        "open_findings": findings,
        "phase_records": _json(child["phase_records"], "managed Improve phase_records"),
        "output_identity": output,
        "output_identity_sha256": _digest(output) if output is not None else None,
        "fresh_evidence": fresh,
        "execution": execution,
    }


def _event(value: Any, *, phase: str, profile: str) -> dict[str, Any]:
    event = _mapping(value, "managed Improve event")
    kind = event.get("kind")
    _need(
        kind == "complete" or kind == "repair" or kind in INCOMPLETE_STATUSES,
        "managed Improve event kind is invalid",
    )
    _need(event.get("phase") == phase, "managed Improve event phase is stale or skipped")
    base = {"kind", "phase", "evidence_refs", "flags"}
    if kind in INCOMPLETE_STATUSES:
        _need(set(event) == base | {"reason"}, "incomplete managed Improve event has unsupported fields")
        return {
            "kind": kind,
            "phase": phase,
            "evidence_refs": _refs(event.get("evidence_refs"), "event evidence_refs"),
            "flags": {},
            "reason": _text(event["reason"], "managed Improve event reason"),
        }
    if kind == "repair":
        _need(set(event) == base | {"reason"}, "managed Improve repair event has unsupported fields")
        return {
            "kind": "repair",
            "phase": phase,
            "evidence_refs": _refs(event.get("evidence_refs"), "event evidence_refs"),
            "flags": _repair_flags(profile, event.get("flags")),
            "reason": _text(event["reason"], "managed Improve repair reason"),
        }
    return event


def apply(child: Mapping[str, Any], event: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply one adapter-validated phase result and return the controlled route.

    The event is deliberately compact.  Its refs identify consumer-validated
    receipts; the controller does not accept a generic ``done`` claim or a
    caller-selected successor phase.
    """
    normalized = assert_child(child)
    _need(normalized["status"] == "active" and normalized["current_phase"] is not None, "managed Improve child is not active")
    phase = normalized["current_phase"]
    parsed = _event(event, phase=phase, profile=normalized["profile"])
    _need(
        not normalized["paused"] or parsed["kind"] != "complete",
        "managed Improve paused child requires explicit resume before completion",
    )
    record: dict[str, Any] = {
        "sequence": len(normalized["phase_records"]) + 1,
        **parsed,
    }
    # ``_record`` validates phase-specific commit/final fields and rejects any
    # generic done flag as an unsupported event field.
    validated_record = _record(record, normalized["binding"], record["sequence"], phase)
    records = [*normalized["phase_records"], validated_record]
    status, next_phase, paused, passes, findings, output, fresh = _replay(
        normalized["binding"], records
    )
    execution = dict(normalized["execution"])
    execution["phase"] = next_phase
    updated = {
        **normalized,
        "status": status,
        "current_phase": next_phase,
        "paused": paused,
        "passes": passes,
        "open_findings": findings,
        "phase_records": records,
        "output_identity": output,
        "output_identity_sha256": _digest(output) if output is not None else None,
        "fresh_evidence": fresh,
        "execution": execution,
    }
    updated = assert_child(updated)
    result: dict[str, Any] = {
        "status": updated["status"],
        "current_phase": updated["current_phase"],
        "paused": updated["paused"],
    }
    if phase == _commit_phase(updated["profile"]) or status == "converged":
        result["trivial_streak"] = decide(
            updated["passes"], open_findings=updated["open_findings"]
        )["trivial_streak"]
    return updated, result


def stop(
    child: Mapping[str, Any],
    status: str,
    reason: str,
    *,
    evidence_refs: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Record a non-success terminal status through the normal event path."""
    normalized = assert_child(child)
    _need(status in INCOMPLETE_STATUSES, "managed Improve stop status is invalid")
    _need(normalized["current_phase"] is not None, "managed Improve child has no phase to stop")
    return apply(
        normalized,
        {
            "kind": status,
            "phase": normalized["current_phase"],
            "evidence_refs": evidence_refs,
            "flags": {},
            "reason": reason,
        },
    )


def resume(
    child: Mapping[str, Any],
    *,
    reason: str,
    evidence_refs: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resume an interrupted child or clear one active controller-owned pause."""
    normalized = assert_child(child)
    incomplete = normalized["status"] in INCOMPLETE_STATUSES
    active_pause = normalized["status"] == "active" and normalized["paused"] is True
    _need(incomplete or active_pause, "only an incomplete or paused managed Improve child can resume")
    _need(normalized["phase_records"], "managed Improve child lacks a resumable record")
    if incomplete:
        interrupted = normalized["phase_records"][-1]
        _need(
            isinstance(interrupted, Mapping)
            and interrupted.get("kind") in INCOMPLETE_STATUSES
            and isinstance(interrupted.get("phase"), str),
            "incomplete managed Improve child has no resumable phase",
        )
        phase = interrupted["phase"]
    else:
        phase = normalized["current_phase"]
        _need(isinstance(phase, str), "paused managed Improve child has no active phase")
    record = {
        "sequence": len(normalized["phase_records"]) + 1,
        "kind": "resume",
        "phase": phase,
        "evidence_refs": evidence_refs,
        "flags": {},
        "reason": reason,
    }
    records = [*normalized["phase_records"], record]
    status, phase, paused, passes, findings, output, fresh = _replay(
        normalized["binding"], records
    )
    _need(status == "active" and phase == record["phase"] and not paused, "managed Improve resume did not restore its phase")
    execution = dict(normalized["execution"])
    execution["phase"] = phase
    updated = assert_child(
        {
            **normalized,
            "status": status,
            "current_phase": phase,
            "paused": False,
            "passes": passes,
            "open_findings": findings,
            "phase_records": records,
            "output_identity": output,
            "output_identity_sha256": _digest(output) if output is not None else None,
            "fresh_evidence": fresh,
            "execution": execution,
        }
    )
    return updated, {"status": "active", "current_phase": phase, "paused": False, "resumed": True}


def packet_metadata(child: Mapping[str, Any]) -> dict[str, Any]:
    """Return the narrow packet state a consumer may project into its owner."""
    normalized = assert_child(child)
    readiness = decide(normalized["passes"], open_findings=normalized["open_findings"])
    return {
        "version": VERSION,
        "binding_sha256": normalized["binding_sha256"],
        "parent_action": normalized["binding"]["parent_action"],
        "child_action_id": normalized["binding"]["child_action_id"],
        "profile": normalized["profile"],
        "status": normalized["status"],
        "current_phase": normalized["current_phase"],
        "paused": normalized["paused"],
        "trivial_streak": readiness["trivial_streak"],
        "execution": normalized["execution"],
    }


def _certificate_payload(child: Mapping[str, Any]) -> dict[str, Any]:
    child = assert_child(child)
    _need(child["status"] == "converged", "managed Improve certificate requires a converged child")
    readiness = decide(child["passes"], open_findings=child["open_findings"])
    _need(readiness["phase"] == "ready", "managed Improve certificate lacks two verified trivial passes")
    _need(child["output_identity"] is not None and child["fresh_evidence"] is not None, "managed Improve certificate lacks fresh final evidence")
    refs: list[str] = []
    for record in child["phase_records"]:
        for ref in record["evidence_refs"]:
            if ref not in refs:
                refs.append(ref)
        completed = record.get("completed_pass")
        if isinstance(completed, Mapping):
            for ref in (completed["evidence_ref"],):
                if ref not in refs:
                    refs.append(ref)
            independent = completed.get("independent_review")
            if isinstance(independent, Mapping) and independent["evidence_ref"] not in refs:
                refs.append(independent["evidence_ref"])
        fresh = record.get("fresh_evidence")
        if isinstance(fresh, Mapping):
            for ref in [fresh["evidence_ref"], *(check["evidence_ref"] for check in fresh["checks"])]:
                if ref not in refs:
                    refs.append(ref)
    binding = child["binding"]
    return {
        "version": VERSION,
        "kind": CERTIFICATE_KIND,
        "status": "converged",
        "binding_sha256": binding["binding_sha256"],
        "parent_action": binding["parent_action"],
        "child_action_id": binding["child_action_id"],
        "profile": binding["profile"],
        "input_identity": binding["input_identity"],
        "input_identity_sha256": binding["input_identity_sha256"],
        "output_identity": child["output_identity"],
        "output_identity_sha256": child["output_identity_sha256"],
        "passes": child["passes"],
        "open_findings": [],
        "evidence_refs": refs,
        "fresh_evidence": child["fresh_evidence"],
        "trivial_streak": readiness["trivial_streak"],
        "replay_key": _digest(
            {
                "binding_sha256": binding["binding_sha256"],
                "child_action_id": binding["child_action_id"],
                "output_identity_sha256": child["output_identity_sha256"],
            }
        ),
    }


def terminal_certificate(child: Mapping[str, Any]) -> dict[str, Any]:
    """Produce a terminal proof whose digest binds input, output and evidence."""
    payload = _certificate_payload(child)
    return {**payload, "certificate_sha256": _digest(payload)}


def _assert_certificate_for_binding(binding: Mapping[str, Any], value: Any) -> dict[str, Any]:
    binding = assert_binding(binding)
    certificate = _mapping(value, "managed Improve certificate")
    required = {
        "version",
        "kind",
        "status",
        "binding_sha256",
        "parent_action",
        "child_action_id",
        "profile",
        "input_identity",
        "input_identity_sha256",
        "output_identity",
        "output_identity_sha256",
        "passes",
        "open_findings",
        "evidence_refs",
        "fresh_evidence",
        "trivial_streak",
        "replay_key",
        "certificate_sha256",
    }
    _need(set(certificate) == required, "managed Improve certificate has unsupported fields")
    _need(
        certificate["version"] == VERSION
        and certificate["kind"] == CERTIFICATE_KIND
        and certificate["status"] == "converged",
        "unsupported managed Improve certificate",
    )
    for key in (
        "binding_sha256",
        "parent_action",
        "child_action_id",
        "profile",
        "input_identity",
        "input_identity_sha256",
    ):
        _need(certificate[key] == binding[key], f"managed Improve certificate {key} mismatch")
    output = _output_identity(certificate["output_identity"])
    _need(certificate["output_identity_sha256"] == _digest(output), "managed Improve certificate output identity digest mismatch")
    _need(isinstance(certificate["passes"], list), "managed Improve certificate passes must be a list")
    passes = [_completed_pass(row, binding) for row in certificate["passes"]]
    _need(passes == certificate["passes"], "managed Improve certificate passes are not canonical")
    _need(certificate["open_findings"] == [], "managed Improve certificate has unresolved findings")
    readiness = decide(passes, open_findings=certificate["open_findings"])
    _need(
        readiness["phase"] == "ready" and certificate["trivial_streak"] == readiness["trivial_streak"],
        "managed Improve certificate lacks two verified trivial passes",
    )
    refs = _refs(certificate["evidence_refs"], "managed Improve certificate evidence_refs")
    _need(refs == certificate["evidence_refs"], "managed Improve certificate evidence refs are not canonical")
    fresh = _fresh_evidence(certificate["fresh_evidence"], binding, output)
    _need(fresh == certificate["fresh_evidence"], "managed Improve certificate fresh evidence is not canonical")
    required_refs = [
        *(row["evidence_ref"] for row in passes),
        fresh["evidence_ref"],
        *(check["evidence_ref"] for check in fresh["checks"]),
    ]
    for row in passes:
        independent = row.get("independent_review")
        if isinstance(independent, Mapping):
            required_refs.append(independent["evidence_ref"])
    _need(
        all(ref in refs for ref in required_refs),
        "managed Improve certificate omits required evidence references",
    )
    expected_replay = _digest(
        {
            "binding_sha256": binding["binding_sha256"],
            "child_action_id": binding["child_action_id"],
            "output_identity_sha256": certificate["output_identity_sha256"],
        }
    )
    _need(certificate["replay_key"] == expected_replay, "managed Improve certificate replay key mismatch")
    payload = {key: certificate[key] for key in certificate if key != "certificate_sha256"}
    _need(certificate["certificate_sha256"] == _digest(payload), "managed Improve certificate digest mismatch")
    return certificate


def assert_terminal_certificate(child: Mapping[str, Any], value: Any) -> dict[str, Any]:
    """Accept only this child's exact current terminal certificate."""
    normalized = assert_child(child)
    expected = terminal_certificate(normalized)
    certificate = _assert_certificate_for_binding(normalized["binding"], value)
    _need(certificate == expected, "managed Improve certificate is stale for this child")
    return certificate


# Convenient aliases for consumers that use generic certificate/packet naming.
def current_packet(child: Mapping[str, Any]) -> dict[str, Any]:
    return packet_metadata(child)


def certificate(child: Mapping[str, Any]) -> dict[str, Any]:
    return terminal_certificate(child)


def assert_certificate(subject: Mapping[str, Any], value: Any) -> dict[str, Any]:
    """Validate against a child when available, otherwise against its binding."""
    candidate = _mapping(subject, "managed Improve certificate subject")
    if candidate.get("kind") == CHILD_KIND:
        return assert_terminal_certificate(candidate, value)
    return _assert_certificate_for_binding(candidate, value)


__all__ = [
    "BINDING_KIND",
    "CERTIFICATE_KIND",
    "CHILD_KIND",
    "INCOMPLETE_STATUSES",
    "ManagedImproveError",
    "PROFILE_STAGES",
    "TERMINAL_STATUSES",
    "VERSION",
    "apply",
    "assert_binding",
    "assert_certificate",
    "assert_child",
    "assert_terminal_certificate",
    "certificate",
    "current_packet",
    "decide",
    "new_binding",
    "new_child",
    "packet_metadata",
    "route",
    "resume",
    "stop",
    "terminal_certificate",
]
