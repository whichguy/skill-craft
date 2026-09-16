#!/usr/bin/env python3
"""Freeze synthetic C recovery packets from real guarded navigator transitions.

This intentionally exercises only the local, opt-in navigator guard.  It does
not inspect a product, contact a target, use credentials, or execute a release.
The packet snapshots are generated from ``new_state``, ``apply``, ``control``,
``save``, and ``render``; cursor IDs, contract anchors, and accepted receipts
are never hand-written.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_consumer_delivery as consumer_delivery  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402


SYNTHETIC_REPOSITORY = "synthetic://shiploop-consumer-delivery/no-live-target"


def result(
    *, outcome: str = "done", summary: str = "Synthetic local navigator result.", **extra: object
) -> dict[str, object]:
    """Return the smallest ordinary navigator result with declared extras."""
    return {"outcome": outcome, "summary": summary, **extra}


def contract(*, candidate: str = "candidate-v1") -> dict[str, object]:
    """Return a sanitized private-consumer contract for this local fixture."""
    return {
        "consumer": "synthetic private game page",
        "target": "synthetic-private-head",
        "behavior": "a drag visibly follows the selected piece",
        "candidate": candidate,
        "operation": "sync the approved synthetic private source target",
        "necessity": "required",
        "basis": "The synthetic feature must be usable by its declared private player.",
        "exclusions": ["public access", "versioned deployment"],
        "authority": {
            "status": "approved",
            "kind": "repo-policy",
            "reference": "SYNTHETIC-SHIPLOOP.md#private-head-update",
            "approval_ref": "Synthetic fixture policy permits only this private target update.",
            "target": "synthetic-private-head",
            "operation": "sync the approved synthetic private source target",
        },
        "obligations": [
            {
                "id": "pre-drag",
                "consumer": "synthetic private game page",
                "target": "synthetic-private-head",
                "kind": "pre-update",
                "phase": "system-test",
                "expected": f"existing move checks pass for {candidate}",
                "required": True,
            },
            {
                "id": "update-effect",
                "consumer": "synthetic private game page",
                "target": "synthetic-private-head",
                "kind": "effect",
                "phase": "release",
                "expected": "the approved synthetic source update is recorded",
                "required": True,
            },
            {
                "id": "update-identity",
                "consumer": "synthetic private game page",
                "target": "synthetic-private-head",
                "kind": "identity",
                "phase": "release",
                "expected": f"the synthetic target identifies {candidate}",
                "required": True,
            },
            {
                "id": "visual-drag",
                "consumer": "synthetic private game page",
                "target": "synthetic-private-head",
                "kind": "behavior",
                "phase": "release-verify",
                "expected": "a dragged piece visibly follows the pointer",
                "required": True,
            },
        ],
    }


def observation(
    state: dict[str, object], *identifiers: str, status: str = "passed"
) -> dict[str, object]:
    """Bind one or more synthetic observations to the effective contract."""
    projection = consumer_delivery.project(state)
    current = projection["contract"]
    assert isinstance(current, dict)
    return {
        "kind": "observation",
        "contract_anchor": projection["anchor"],
        "observations": [
            {
                "obligation_id": identifier,
                "status": status,
                "candidate": current["candidate"],
                "target": "synthetic-private-head",
                "evidence_refs": [f"synthetic-evidence/{identifier}.md"],
            }
            for identifier in identifiers
        ],
    }


def save(run_root: Path | None, state: dict[str, object]) -> None:
    """Persist actual Markdown state only when this fixture has a run root."""
    if run_root is not None:
        navigator.save(run_root, state)


def new_run(run_root: Path | None, purpose: str, *, guarded: bool = True) -> dict[str, object]:
    """Create and persist a navigator state whose prompt declares no live system."""
    state = navigator.new_state(
        SYNTHETIC_REPOSITORY,
        "Synthetic local guarded recovery fixture only. "
        "No product, credential, network, consumer, target, or deployment exists. "
        f"It models {purpose}. Do not execute an operation from this fixture.",
        delivery_contract=guarded,
    )
    save(run_root, state)
    return state


def advance(
    state: dict[str, object],
    expected_stage: str,
    *,
    run_root: Path | None = None,
    outcome: str = "done",
    summary: str = "Synthetic local navigator result.",
    **extra: object,
) -> dict[str, object]:
    """Use the public transition API and persist every accepted result."""
    assert navigator.current_stage(state) == expected_stage
    action = navigator.current_action(state)
    before = deepcopy(state)
    updated = navigator.apply(
        state, action["id"], result(outcome=outcome, summary=summary, **extra)
    )
    assert state == before
    navigator.validate(updated)
    save(run_root, updated)
    return updated


def advance_until(
    state: dict[str, object], target_stage: str, *, run_root: Path | None = None
) -> dict[str, object]:
    """Walk ordinary current actions without inventing a transition cursor."""
    while navigator.current_stage(state) != target_stage:
        state = advance(state, navigator.current_stage(state), run_root=run_root)
    return state


def accept_contract(
    state: dict[str, object], *, run_root: Path | None = None, candidate: str = "candidate-v1"
) -> dict[str, object]:
    """Reach plan-improve and accept the fixture's declared contract."""
    return accept_contract_value(
        state, contract(candidate=candidate), run_root=run_root
    )


def accept_contract_value(
    state: dict[str, object], value: dict[str, object], *, run_root: Path | None = None
) -> dict[str, object]:
    """Reach plan-improve and accept one fully declared fixture contract."""
    state = advance_until(state, "plan-improve", run_root=run_root)
    return advance(
        state,
        "plan-improve",
        run_root=run_root,
        delivery_assessment={"kind": "contract", "contract": value},
    )


def to_release_verify(
    state: dict[str, object], *, run_root: Path | None = None
) -> dict[str, object]:
    """Reach release-verify with required pre-update, effect, and identity receipts."""
    state = advance_until(state, "system-test", run_root=run_root)
    state = advance(
        state,
        "system-test",
        run_root=run_root,
        delivery_assessment=observation(state, "pre-drag"),
    )
    state = advance(state, "outer-improve", run_root=run_root)
    state = advance(state, "release-plan", run_root=run_root)
    state = advance(
        state,
        "release",
        run_root=run_root,
        delivery_assessment=observation(state, "update-effect", "update-identity"),
    )
    assert navigator.current_stage(state) == "release-verify"
    return state


def to_release_plan(
    state: dict[str, object],
    *,
    run_root: Path | None = None,
    value: dict[str, object] | None = None,
) -> dict[str, object]:
    """Reach release-plan with a current required synthetic pre-update receipt."""
    state = accept_contract_value(state, value or contract(), run_root=run_root)
    state = advance_until(state, "system-test", run_root=run_root)
    state = advance(
        state,
        "system-test",
        run_root=run_root,
        delivery_assessment=observation(state, "pre-drag"),
    )
    state = advance(state, "outer-improve", run_root=run_root)
    assert navigator.current_stage(state) == "release-plan"
    return state


def to_release(
    state: dict[str, object],
    *,
    run_root: Path | None = None,
    value: dict[str, object] | None = None,
) -> dict[str, object]:
    """Reach release after valid planning, ready to record effect and identity."""
    state = to_release_plan(state, run_root=run_root, value=value)
    state = advance(state, "release-plan", run_root=run_root)
    assert navigator.current_stage(state) == "release"
    return state


def to_handoff(
    state: dict[str, object], *, run_root: Path | None = None
) -> dict[str, object]:
    """Reach handoff after all required current synthetic delivery observations."""
    state = to_release_verify(state, run_root=run_root)
    state = advance(
        state,
        "release-verify",
        run_root=run_root,
        delivery_assessment=observation(state, "visual-drag"),
    )
    assert navigator.current_stage(state) == "handoff"
    return state


def write_packet(output: Path, name: str, run_root: Path, state: dict[str, object]) -> Path:
    """Snapshot an actual renderer packet after durable Markdown state is saved."""
    packet = navigator.render(None, run_root, state)
    path = output / name
    path.write_text(packet, encoding="utf-8")
    return path


def login_recovery(output: Path) -> dict[str, object]:
    """Preserve a completed synthetic effect while login blocks visual proof."""
    run_root = output / "login-after-upload-run"
    run_root.mkdir()
    state = new_run(run_root, "an unchanged candidate with a later login boundary")
    state = accept_contract(state, run_root=run_root)
    state = to_release_verify(state, run_root=run_root)
    state = advance(
        state,
        "release-verify",
        run_root=run_root,
        outcome="blocked",
        summary=(
            "Synthetic private-page login blocks the visual drag check; the synthetic "
            "effect and identity records are retained."
        ),
        delivery_assessment=observation(state, "visual-drag", status="blocked"),
    )
    assert state["status"] == "blocked"
    assert navigator.current_stage(state) == "release-verify"
    blocked_projection = consumer_delivery.project(state)
    assert blocked_projection["observations"]["update-effect"]["status"] == "passed"
    assert blocked_projection["observations"]["update-identity"]["status"] == "passed"
    assert blocked_projection["observations"]["visual-drag"]["status"] == "blocked"

    state = navigator.control(state, "resume")
    navigator.validate(state)
    save(run_root, state)
    assert state["status"] == "active"
    assert navigator.current_stage(state) == "release-verify"
    release_entries = [entry for entry in state["history"] if entry["stage"] == "release"]
    assert len(release_entries) == 1

    packet = write_packet(output, "login-after-upload-recovery.md", run_root, state)
    text = packet.read_text(encoding="utf-8")
    assert "release-verify" in text
    assert "update-effect [required; release/effect" in text
    assert "passed at release" in text
    assert "visual-drag [required; release-verify/behavior" in text
    assert "blocked at release-verify" in text
    assert (
        "do not re-upload without evidence that retrying is appropriate"
        in " ".join(text.split())
    )
    return {
        "packet": str(packet.relative_to(output)),
        "state": str((run_root / "state.md").relative_to(output)),
        "current_stage": navigator.current_stage(state),
        "effectful_release_entries": len(release_entries),
        "outcome": "resumed visual verification without a second synthetic upload",
    }


def candidate_replan_recovery(output: Path) -> dict[str, object]:
    """Keep a material post-plan candidate change blocked at its current action."""
    run_root = output / "post-plan-candidate-change-run"
    run_root.mkdir()
    state = new_run(run_root, "a material candidate change after release planning")
    state = accept_contract(state, run_root=run_root)
    state = advance_until(state, "system-test", run_root=run_root)
    state = advance(
        state,
        "system-test",
        run_root=run_root,
        delivery_assessment=observation(state, "pre-drag"),
    )
    state = advance(state, "outer-improve", run_root=run_root)
    state = advance(state, "release-plan", run_root=run_root)
    prior = consumer_delivery.project(state)
    assert prior["anchor"] is not None

    state = advance(
        state,
        "release",
        run_root=run_root,
        outcome="blocked",
        summary=(
            "Synthetic candidate-v2 was declared after release planning; the current "
            "effectful action must remain blocked for a new planning run."
        ),
        delivery_assessment={
            "kind": "contract",
            "contract": contract(candidate="candidate-v2"),
            "supersedes": prior["anchor"],
            "correction": {
                "kind": "user-decision",
                "reference": (
                    "Synthetic fixture user selects candidate-v2 for the existing "
                    "private delivery scope."
                ),
            },
        },
    )
    assert state["status"] == "blocked"
    projection = consumer_delivery.project(state)
    assert projection["replan_required"] is not None
    assert "update-effect" not in projection["observations"]
    assert "update-identity" not in projection["observations"]

    state = navigator.control(state, "resume")
    navigator.validate(state)
    save(run_root, state)
    assert state["status"] == "active"
    assert navigator.current_stage(state) == "release"
    packet = write_packet(output, "post-plan-candidate-change-recovery.md", run_root, state)
    text = packet.read_text(encoding="utf-8")
    assert "Delivery replanning required:" in text
    assert "Do not complete this effectful action." in text
    assert "new planning run" in text
    assert "update-effect" in text and "unreported" in text
    return {
        "packet": str(packet.relative_to(output)),
        "state": str((run_root / "state.md").relative_to(output)),
        "current_stage": navigator.current_stage(state),
        "effect_observation": "unreported",
        "outcome": "resumed release remains replan-required; no synthetic effect was declared",
    }


StateAndSubmission = tuple[dict[str, object], dict[str, object]]


def _submit(state: dict[str, object], submission: dict[str, object]) -> dict[str, object]:
    """Use a current public action without mutating the source state."""
    action = navigator.current_action(state)
    before = deepcopy(state)
    updated = navigator.apply(state, action["id"], submission)
    assert state == before
    return updated


def _rejected_submission(
    state: dict[str, object], submission: dict[str, object], expected_error: str
) -> str:
    """Assert the public guard rejects an omission without consuming its action."""
    before = deepcopy(state)
    action = navigator.current_action(state)
    try:
        navigator.apply(state, action["id"], submission)
    except navigator.NavigatorError as exc:
        error = str(exc)
    else:  # pragma: no cover - each caller asserts a deliberately red control.
        raise AssertionError("guard control unexpectedly advanced")
    assert expected_error in error
    assert state == before
    return error


def _bypassed_submission(
    state: dict[str, object],
    submission: dict[str, object],
    *,
    bypass_terminal: bool = False,
) -> dict[str, object]:
    """Mutate only in-process guard entry points for a causal negative control."""
    action = navigator.current_action(state)
    before = deepcopy(state)
    with patch.object(consumer_delivery, "validate_transition", return_value={}):
        if bypass_terminal:
            with patch.object(consumer_delivery, "validate_terminal", return_value=None):
                updated = navigator.apply(state, action["id"], submission)
        else:
            updated = navigator.apply(state, action["id"], submission)
    assert state == before
    return updated


def _unresolved_authority_contract() -> dict[str, object]:
    """Return a schema-valid required contract that intentionally lacks authority."""
    value = contract()
    authority = value["authority"]
    assert isinstance(authority, dict)
    authority["status"] = "unresolved"
    authority["kind"] = "user-decision"
    authority["reference"] = "Synthetic fixture has no approved delivery decision."
    authority.pop("approval_ref")
    return value


def _source_only_contract() -> dict[str, object]:
    """Return a valid source-only declaration that still retains behavior proof."""
    value = contract()
    value["necessity"] = "not-required"
    value["basis"] = "Synthetic fixture explicitly scopes this run to source-only work."
    value["authority"] = {
        "status": "not-required",
        "kind": "request",
        "reference": "Synthetic original request says source-only.",
        "target": "synthetic-private-head",
        "operation": "sync the approved synthetic private source target",
    }
    value["obligations"] = [
        row for row in value["obligations"]
        if isinstance(row, dict) and row["kind"] in {"pre-update", "behavior"}
    ]
    return value


def _source_only_with_optional_activation() -> dict[str, object]:
    """Return the forbidden source-only shape with optional activation rows."""
    value = _source_only_contract()
    optional_activation = [
        {**deepcopy(row), "required": False}
        for row in contract()["obligations"]
        if isinstance(row, dict) and row["kind"] in {"effect", "identity"}
    ]
    value["obligations"].extend(optional_activation)
    return value


def _missing_plan_contract() -> StateAndSubmission:
    state = advance_until(
        new_run(None, "a missing-plan-contract negative control"), "plan-improve"
    )
    return state, result()


def _valid_plan_contract() -> StateAndSubmission:
    state = advance_until(
        new_run(None, "a valid-plan-contract counterpart"), "plan-improve"
    )
    return state, result(delivery_assessment={"kind": "contract", "contract": contract()})


def _source_only_optional_activation() -> StateAndSubmission:
    state = advance_until(
        new_run(None, "a source-only optional-activation schema control"), "plan-improve"
    )
    return state, result(
        delivery_assessment={
            "kind": "contract",
            "contract": _source_only_with_optional_activation(),
        }
    )


def _valid_source_only_contract() -> StateAndSubmission:
    state = advance_until(
        new_run(None, "a valid source-only contract counterpart"), "plan-improve"
    )
    return state, result(
        delivery_assessment={"kind": "contract", "contract": _source_only_contract()}
    )


def _at_system_test() -> dict[str, object]:
    state = new_run(None, "a pre-update-obligation control")
    state = accept_contract(state)
    return advance_until(state, "system-test")


def _missing_precheck() -> StateAndSubmission:
    return _at_system_test(), result()


def _valid_precheck() -> StateAndSubmission:
    state = _at_system_test()
    return state, result(delivery_assessment=observation(state, "pre-drag"))


def _missing_authority() -> StateAndSubmission:
    state = new_run(None, "an unresolved-authority release-plan control")
    state = to_release_plan(state, value=_unresolved_authority_contract())
    return state, result()


def _valid_authority() -> StateAndSubmission:
    state = to_release_plan(new_run(None, "an approved-authority counterpart"))
    return state, result()


def _missing_release_receipts() -> StateAndSubmission:
    return to_release(new_run(None, "a missing-release-receipts control")), result()


def _valid_release_receipts() -> StateAndSubmission:
    state = to_release(new_run(None, "a valid-release-receipts counterpart"))
    return state, result(
        delivery_assessment=observation(state, "update-effect", "update-identity")
    )


def _at_release_verify(purpose: str) -> dict[str, object]:
    state = accept_contract(new_run(None, purpose))
    return to_release_verify(state)


def _missing_behavior() -> StateAndSubmission:
    return _at_release_verify("a missing-behavior control"), result()


def _valid_behavior() -> StateAndSubmission:
    state = _at_release_verify("a valid-behavior counterpart")
    return state, result(delivery_assessment=observation(state, "visual-drag"))


def _post_plan_candidate_change() -> StateAndSubmission:
    state = to_release(new_run(None, "a post-plan-candidate-change control"))
    prior = consumer_delivery.project(state)
    assert isinstance(prior["anchor"], str)
    return state, result(
        delivery_assessment={
            "kind": "contract",
            "contract": contract(candidate="candidate-v2"),
            "supersedes": prior["anchor"],
            "correction": {
                "kind": "user-decision",
                "reference": "Synthetic fixture user selected candidate-v2.",
            },
        }
    )


def _candidate_planned_before_release() -> StateAndSubmission:
    state = to_release(
        new_run(None, "a candidate-v2-planned-before-release counterpart"),
        value=contract(candidate="candidate-v2"),
    )
    return state, result(
        delivery_assessment=observation(state, "update-effect", "update-identity")
    )


def _handoff_with_outstanding_behavior() -> StateAndSubmission:
    state = to_handoff(
        accept_contract(new_run(None, "a handoff-outstanding-obligation control"))
    )
    state = advance(
        state,
        "handoff",
        outcome="blocked",
        summary="Synthetic later observation marks the required behavior failed.",
        delivery_assessment=observation(state, "visual-drag", status="failed"),
    )
    state = navigator.control(state, "resume")
    navigator.validate(state)
    assert navigator.current_stage(state) == "handoff"
    return state, result()


def _valid_handoff() -> StateAndSubmission:
    return to_handoff(accept_contract(new_run(None, "a valid-handoff counterpart"))), result()


def _record_guard_case(
    identifier: str,
    rejected_setup: Callable[[], StateAndSubmission],
    expected_error: str,
    valid_setup: Callable[[], StateAndSubmission],
    *,
    bypass_terminal: bool = False,
) -> dict[str, object]:
    """Record public rejection, a scoped mutation, and a valid counterpart."""
    rejected_state, rejected_submission = rejected_setup()
    current_stage = navigator.current_stage(rejected_state)
    rejection = _rejected_submission(
        rejected_state, rejected_submission, expected_error
    )

    bypass_state, bypass_submission = rejected_setup()
    bypassed = _bypassed_submission(
        bypass_state, bypass_submission, bypass_terminal=bypass_terminal
    )
    if bypass_terminal:
        # The terminal mutation deliberately makes a state invalid again once
        # the patch ends, so inspect only its script-produced successor fields.
        bypass_stage = bypassed["stage"]
        bypass_status = bypassed["status"]
        revalidates_after_patch = False
    else:
        navigator.validate(bypassed)
        bypass_stage = navigator.current_stage(bypassed)
        bypass_status = bypassed["status"]
        revalidates_after_patch = True

    valid_state, valid_submission = valid_setup()
    valid = _submit(valid_state, valid_submission)
    navigator.validate(valid)
    return {
        "id": identifier,
        "normal_public_api": {
            "stage": current_stage,
            "apply": "rejected",
            "error": rejection,
            "state_unchanged": True,
        },
        "test_only_guard_mutation": {
            "patched_entry_points": (
                ["validate_transition", "validate_terminal"]
                if bypass_terminal
                else ["validate_transition"]
            ),
            "apply": "advanced",
            "stage_after": bypass_stage,
            "status_after": bypass_status,
            "revalidates_after_patch": revalidates_after_patch,
            "limitation": (
                "This is an in-process test mutation, not a supported production route."
            ),
        },
        "valid_counterpart": {
            "apply": "advanced",
            "stage_after": navigator.current_stage(valid),
            "status_after": valid["status"],
        },
    }


def _record_schema_case(
    identifier: str,
    rejected_setup: Callable[[], StateAndSubmission],
    expected_error: str,
    valid_setup: Callable[[], StateAndSubmission],
) -> dict[str, object]:
    """Record an earlier schema gate that has no safe transition-level bypass."""
    rejected_state, rejected_submission = rejected_setup()
    current_stage = navigator.current_stage(rejected_state)
    rejection = _rejected_submission(
        rejected_state, rejected_submission, expected_error
    )
    valid_state, valid_submission = valid_setup()
    valid = _submit(valid_state, valid_submission)
    navigator.validate(valid)
    return {
        "id": identifier,
        "normal_public_api": {
            "stage": current_stage,
            "apply": "rejected",
            "error": rejection,
            "state_unchanged": True,
        },
        "test_only_guard_mutation": {
            "apply": "not-representable",
            "reason": (
                "The malformed contract is rejected by canonicalization before the "
                "shared transition guard. Patching validate_transition alone cannot "
                "produce a safely valid accepted state."
            ),
            "limitation": (
                "This is intentionally recorded as a schema gate, not inflated into "
                "a synthetic production-bypass claim."
            ),
        },
        "valid_counterpart": {
            "apply": "advanced",
            "stage_after": navigator.current_stage(valid),
            "status_after": valid["status"],
        },
    }


def _packet_measurements(output: Path) -> dict[str, object]:
    """Measure frozen packet bytes and current result-template host fields only."""
    samples = [
        ("login-after-upload-recovery.md", "login-after-upload-run/state.md"),
        (
            "post-plan-candidate-change-recovery.md",
            "post-plan-candidate-change-run/state.md",
        ),
    ]
    c2_packet = output.parent / "C2" / "post-plan-candidate-change-current-renderer.md"
    if c2_packet.is_file():
        samples.append(
            (
                "../C2/post-plan-candidate-change-current-renderer.md",
                "post-plan-candidate-change-run/state.md",
            )
        )
    base_result = result()
    base_bytes = len(
        json.dumps(base_result, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    )
    packet_bytes: list[dict[str, object]] = []
    field_overhead: list[dict[str, object]] = []
    for packet_name, state_name in samples:
        packet_path = (output / packet_name).resolve()
        state_path = output / state_name
        if not packet_path.is_file() or not state_path.is_file():
            raise ValueError(f"missing frozen C packet or Markdown state: {packet_name}")
        state = store.read_record(state_path)
        navigator.validate(state)
        stage = navigator.current_stage(state)
        assessment = consumer_delivery.template_assessment(state, stage)
        assert assessment is not None
        with_field = {**base_result, "delivery_assessment": assessment}
        guarded_bytes = len(
            json.dumps(with_field, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        )
        packet_bytes.append({"packet": packet_name, "utf8_bytes": len(packet_path.read_bytes())})
        field_overhead.append(
            {
                "packet": packet_name,
                "stage": stage,
                "base_result_json_utf8_bytes": base_bytes,
                "guarded_result_json_utf8_bytes": guarded_bytes,
                "delivery_assessment_added_utf8_bytes": guarded_bytes - base_bytes,
            }
        )
    return {
        "packet_bytes": {
            "measurement": "UTF-8 byte length of each frozen renderer packet; not tokens or time.",
            "samples": packet_bytes,
        },
        "result_template_host_field_overhead": {
            "measurement": (
                "UTF-8 bytes added by the script-provided delivery_assessment field in "
                "sorted, indented json.dumps result data; not tokens or time."
            ),
            "samples": field_overhead,
        },
    }


def guard_controls(output: Path) -> dict[str, object]:
    """Run deterministic non-model controls without altering the shipped guard."""
    plain = new_run(None, "an unmarked backward-compatibility control", guarded=False)
    plain = advance_until(plain, "release-verify")
    plain = advance(plain, "release-verify")
    assert navigator.current_stage(plain) == "handoff"

    controls = [
        _record_guard_case(
            "missing-plan-contract", _missing_plan_contract, "delivery contract", _valid_plan_contract
        ),
        _record_schema_case(
            "source-only-optional-activation-contradiction",
            _source_only_optional_activation,
            "not-required delivery contract",
            _valid_source_only_contract,
        ),
        _record_guard_case(
            "missing-pre-update-check", _missing_precheck, "pre-update", _valid_precheck
        ),
        _record_guard_case(
            "unresolved-release-authority", _missing_authority, "authority is unresolved", _valid_authority
        ),
        _record_guard_case(
            "missing-release-effect-and-identity",
            _missing_release_receipts,
            "release obligations need effect and identity",
            _valid_release_receipts,
        ),
        _record_guard_case(
            "missing-release-verify-behavior", _missing_behavior, "release-verify behavior", _valid_behavior
        ),
        _record_guard_case(
            "post-plan-candidate-change-requires-replanning",
            _post_plan_candidate_change,
            "requires replanning",
            _candidate_planned_before_release,
        ),
        _record_guard_case(
            "handoff-outstanding-required-obligation",
            _handoff_with_outstanding_behavior,
            "unfinished",
            _valid_handoff,
            bypass_terminal=True,
        ),
    ]
    return {
        "synthetic": True,
        "model_scores": "not measured by this deterministic control",
        "unmarked_backward_compatibility": {
            "id": "unmarked-generic-missing-evidence",
            "configuration": "delivery guard not opted in",
            "public_apply": "accepted",
            "stage_after": navigator.current_stage(plain),
        },
        "controls": controls,
        "measurements": _packet_measurements(output),
        "authoring_observations": [
            {
                "id": "release-plan-phase-order",
                "observed": (
                    "Original A/B release-plan teachbacks conflated a non-executing plan "
                    "with later release and consumer-verification work; the frozen B2 "
                    "follow-up records the corrected phase-order criterion."
                ),
                "source": "test/experiments/shiploop_delivery/README.md#exploratory-b2-phase-order-follow-up",
            },
            {
                "id": "candidate-specific-contract-correction",
                "observed": (
                    "During C fixture authoring, changing candidate-specific expected "
                    "fields with candidate-v2 required a declared synthetic user-decision "
                    "correction. The post-plan recovery fixture therefore carries that "
                    "correction rather than a hand-edited anchor."
                ),
                "source": "prepare_guard_packets.py#candidate-replan-recovery",
            },
            {
                "id": "source-only-optional-activation",
                "observed": (
                    "Review found that a source-only declaration could previously retain "
                    "optional effect or identity rows. This schema control records the "
                    "current rejection and a behavior-retaining source-only counterpart."
                ),
                "source": "test/shiploop-consumer-delivery.test.py#test-not-required-contract-rejects-optional-activation-rows-for-any-authority-state",
            },
        ],
    }


def manifest(login: dict[str, object], replan: dict[str, object]) -> str:
    """Describe how to use the packet snapshots without leaking a model answer."""
    return f"""# C guarded recovery fixtures

These are synthetic local packets generated by the real opt-in navigator APIs.
They are not deployment evidence, do not name a live target, and do not authorize
any operation. Send only one packet at a time to a fresh-context, read-only
teachback; do not give the interpreter this manifest or its deterministic control.

## Packets for independent teachback

- `{login['packet']}` — resumed `release-verify` after a retained synthetic
  effect/identity and a blocked login-boundary visual check. State:
  `{login['state']}`.
- `{replan['packet']}` — resumed `release` after a material candidate change
  accepted as blocked after `release-plan`. State: `{replan['state']}`.

The first asks whether recovery preserves the already-recorded effect and stays
at verification. The second asks whether the resumed release remains
replan-required, must be reported blocked for a new planning run, and avoids an
effect. The packet itself is the only durable input for each teachback;
responses must not claim an external effect.

## Deterministic control

`guard-controls.md` records an execution-only local control. It compares an
unmarked generic navigator, a public marked rejection, and a deliberately
test-patched guard function. It is not a model score and does not demonstrate a
production bypass.
"""


def prepare(output: Path) -> dict[str, object]:
    """Create a frozen C set, refusing to overwrite an existing experiment."""
    if output.exists():
        raise ValueError(f"refusing to overwrite existing fixture set: {output}")
    output.mkdir(parents=True)
    login = login_recovery(output)
    replan = candidate_replan_recovery(output)
    controls = guard_controls(output)
    control_path = output / "guard-controls.md"
    control_path.write_text(
        store.dumps(controls, "Synthetic ShipLoop delivery-guard controls"),
        encoding="utf-8",
    )
    manifest_path = output / "manifest.md"
    manifest_path.write_text(manifest(login, replan), encoding="utf-8")
    return {
        "synthetic": True,
        "packets": [login["packet"], replan["packet"]],
        "states": [login["state"], replan["state"]],
        "control": str(control_path.relative_to(output)),
        "manifest": str(manifest_path.relative_to(output)),
    }


def refresh_controls(output: Path) -> dict[str, object]:
    """Refresh only the deterministic control record beside frozen C packets."""
    if not output.is_dir():
        raise ValueError(f"frozen C fixture directory does not exist: {output}")
    controls = guard_controls(output)
    control_path = output / "guard-controls.md"
    control_path.write_text(
        store.dumps(controls, "Synthetic ShipLoop delivery-guard controls"),
        encoding="utf-8",
    )
    return {
        "synthetic": True,
        "control": str(control_path.relative_to(output)),
        "packets_preserved": [
            "login-after-upload-recovery.md",
            "post-plan-candidate-change-recovery.md",
        ],
    }


def _sha256(path: Path) -> str:
    """Return an explicit integrity digest for a frozen local artifact."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_current_renderer_c2(output: Path) -> dict[str, object]:
    """Freeze a separately labeled current-renderer packet without touching C."""
    output = output.resolve()
    historical_packet = output / "post-plan-candidate-change-recovery.md"
    run_root = output / "post-plan-candidate-change-run"
    state_path = run_root / "state.md"
    if not historical_packet.is_file() or not state_path.is_file():
        raise ValueError("C candidate-recovery packet and Markdown state are required")
    c2_root = output.parent / "C2"
    if c2_root.exists():
        raise ValueError(f"refusing to overwrite existing current-renderer follow-up: {c2_root}")

    state = store.read_record(state_path)
    navigator.validate(state)
    current_packet = navigator.render(None, run_root, state)
    c2_root.mkdir()
    packet_path = c2_root / "post-plan-candidate-change-current-renderer.md"
    packet_path.write_text(current_packet, encoding="utf-8")
    provenance_path = c2_root / "provenance.md"
    provenance = {
        "synthetic": True,
        "kind": "current-renderer-follow-up",
        "historical_packet": "../C/post-plan-candidate-change-recovery.md",
        "historical_packet_sha256": _sha256(historical_packet),
        "historical_state": "../C/post-plan-candidate-change-run/state.md",
        "historical_state_sha256": _sha256(state_path),
        "current_renderer_packet": packet_path.name,
        "current_renderer_packet_sha256": _sha256(packet_path),
        "renderer": "shiploop_navigator.render(None, C run root, C Markdown state)",
        "current_renderer_equals_historic_packet": (
            current_packet.encode("utf-8") == historical_packet.read_bytes()
        ),
        "preservation_policy": (
            "C remains the historical teachback fixture. Its digest, rather than current "
            "renderer equality, is the integrity condition after later wording changes."
        ),
    }
    provenance_path.write_text(
        store.dumps(provenance, "Synthetic ShipLoop C2 packet provenance"),
        encoding="utf-8",
    )
    return {
        "synthetic": True,
        "packet": str(packet_path.relative_to(output.parent)),
        "provenance": str(provenance_path.relative_to(output.parent)),
        "historical_packet_preserved": historical_packet.name,
    }


def verify_frozen_packets(output: Path) -> dict[str, object]:
    """Check C's historical integrity plus renderer equality where still intended."""
    output = output.resolve()
    login_packet = output / "login-after-upload-recovery.md"
    login_run = output / "login-after-upload-run"
    historical_packet = output / "post-plan-candidate-change-recovery.md"
    candidate_run = output / "post-plan-candidate-change-run"
    c2_root = output.parent / "C2"
    c2_packet = c2_root / "post-plan-candidate-change-current-renderer.md"
    provenance_path = c2_root / "provenance.md"
    required = (
        login_packet,
        login_run / "state.md",
        historical_packet,
        candidate_run / "state.md",
        c2_packet,
        provenance_path,
    )
    if not all(path.is_file() for path in required):
        raise ValueError("frozen C and C2 packet artifacts are incomplete")

    login_state = store.read_record(login_run / "state.md")
    navigator.validate(login_state)
    assert navigator.render(None, login_run, login_state).encode("utf-8") == login_packet.read_bytes()

    provenance = store.read_record(provenance_path)
    assert isinstance(provenance, dict)
    assert provenance["historical_packet_sha256"] == _sha256(historical_packet)
    assert provenance["historical_state_sha256"] == _sha256(candidate_run / "state.md")
    assert provenance["current_renderer_packet_sha256"] == _sha256(c2_packet)

    candidate_state = store.read_record(candidate_run / "state.md")
    navigator.validate(candidate_state)
    assert navigator.render(None, candidate_run, candidate_state).encode("utf-8") == c2_packet.read_bytes()
    return {
        "login_c_matches_current_renderer": True,
        "historic_candidate_c_matches_recorded_hash": True,
        "current_candidate_c2_matches_current_renderer": True,
        "historic_candidate_c_sha256": _sha256(historical_packet),
        "current_candidate_c2_sha256": _sha256(c2_packet),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=EXPERIMENT / "packets" / "C",
        help="Fixture directory to create; defaults to packets/C and refuses overwrite.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Assert current temporary invariants and frozen C/C2 packet integrity.",
    )
    mode.add_argument(
        "--refresh-controls",
        action="store_true",
        help="Rewrite only guard-controls.md beside an existing frozen C packet set.",
    )
    mode.add_argument(
        "--freeze-c2",
        action="store_true",
        help="Freeze a separately labeled current-renderer candidate-recovery packet.",
    )
    args = parser.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory(prefix="shiploop-guard-packets-") as temp:
            summary = prepare(Path(temp) / "C")
        frozen = verify_frozen_packets(EXPERIMENT / "packets" / "C")
        print(json.dumps({"checked": True, **summary, "frozen": frozen}, indent=2, sort_keys=True))
        return 0
    if args.refresh_controls:
        summary = refresh_controls(args.output.resolve())
        print(json.dumps({"output": str(args.output.resolve()), **summary}, indent=2, sort_keys=True))
        return 0
    if args.freeze_c2:
        summary = freeze_current_renderer_c2(args.output.resolve())
        print(json.dumps({"output": str(args.output.resolve()), **summary}, indent=2, sort_keys=True))
        return 0
    summary = prepare(args.output.resolve())
    print(json.dumps({"output": str(args.output.resolve()), **summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
