#!/usr/bin/env python3
"""Versioned Definition-of-Ready and Definition-of-Done step contracts.

This module deliberately contains no host state or git commands.  Callers supply
the selected-step identities and the verify record they just obtained; a contract
receipt is therefore evidence-bound rather than a mutable ``ready: true`` flag.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Collection, Mapping, Sequence
from typing import Any, Dict, List, Optional


CONTRACT_VERSION = 1
EVIDENCE_VERSION = 1
QUALITY_FLOOR_VERSION = 1
QUALITY_FLOOR = {
    "version": QUALITY_FLOOR_VERSION,
    "requirements": (
        "Every criterion has a stable ID, a concrete condition, and an evidence "
        "method. Product checks, documentation obligations, and integration are "
        "certified through evidence rather than status booleans."
    ),
}

_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9][A-Z0-9._-]{0,79})+$")
_HEAD_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_IDENTITY_RE = re.compile(r"^[0-9a-f]{64}$")
_PLACEHOLDER_RE = re.compile(
    r"^\s*(?:tbd|todo|none|n/?a|unknown|same as above|\.\.\.|<[^>]+>)\s*$",
    re.IGNORECASE,
)
_CONTROL_RE = re.compile(r"[\x00-\x08\x0a-\x1f\x7f]")
_PHASES = {
    "ready",
    "implement",  # Compatibility spelling; it still means pre-edit readiness.
    "final-verify",
    "post-inner",
    "merge",
}
_EVIDENCE_SOURCES = {"manual-observation", "verify-record", "host-reported"}


class ContractError(ValueError):
    """A versioned step contract or its evidence is not certifiable."""


def _error(message: str) -> None:
    raise ContractError(message)


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _error(f"{label} must be an object")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str):
        _error(f"{label} must be a nonempty string")
    text = value.strip()
    if not text or _CONTROL_RE.search(text) or _PLACEHOLDER_RE.match(text):
        _error(f"{label} must be concrete and nonempty")
    return text


def _id(value: Any, label: str, prefix: str) -> str:
    ident = _text(value, label)
    if not ident.startswith(prefix) or not _ID_RE.fullmatch(ident):
        kind = {
            "R-": "ready",
            "D-": "done",
            "T-": "test",
            "DOC-": "documentation",
        }.get(prefix, prefix.rstrip("-"))
        _error(f"{label} must be a stable {kind} criterion ID")
    return ident


def _string_list(value: Any, label: str) -> List[str]:
    if not isinstance(value, list) or not value:
        _error(f"{label} must link one or more produces")
    out = [_text(item, f"{label}[{index}]") for index, item in enumerate(value)]
    if len(set(out)) != len(out):
        _error(f"{label} must not repeat produces")
    return out


def _step_produces(step: Mapping[str, Any]) -> List[str]:
    produces = step.get("produces")
    if isinstance(produces, str):
        return [_text(produces, "step.produces")]
    return _string_list(produces, "step.produces")


def _exact_keys(value: Mapping[str, Any], label: str, required: Collection[str]) -> None:
    missing = sorted(set(required) - set(value))
    extra = sorted(set(value) - set(required))
    if missing:
        _error(f"{label} is missing keys: {', '.join(missing)}")
    if extra:
        _error(f"{label} has unsupported keys: {', '.join(extra)}")


def _rows(value: Any, label: str) -> List[Mapping[str, Any]]:
    if not isinstance(value, list) or not value:
        _error(f"{label} must be a nonempty list")
    rows: List[Mapping[str, Any]] = []
    for index, row in enumerate(value):
        rows.append(_as_mapping(row, f"{label}[{index}]"))
    return rows


def _normalize_ready(value: Any) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for index, row in enumerate(_rows(value, "contract.ready")):
        label = f"ready[{index}]"
        _exact_keys(row, label, {"id", "condition", "evidence_method"})
        out.append(
            {
                "id": _id(row["id"], f"{label}.id", "R-"),
                "condition": _text(row["condition"], f"{label}.condition"),
                "evidence_method": _text(
                    row["evidence_method"], f"{label}.evidence_method"
                ),
            }
        )
    return out


def _normalize_done(value: Any, declared_produces: Collection[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for index, row in enumerate(_rows(value, "contract.done")):
        label = f"done[{index}]"
        _exact_keys(
            row,
            label,
            {"id", "condition", "produces", "evidence_method", "completion"},
        )
        produces = _string_list(row["produces"], f"done {_text(row['id'], f'{label}.id')}")
        unknown = sorted(set(produces) - set(declared_produces))
        if unknown:
            _error(f"{label}.produces are not exact step produces: {', '.join(unknown)}")
        completion = _text(row["completion"], f"{label}.completion")
        if completion not in {"integrated", "deployed"}:
            _error(f"{label}.completion must be integrated or deployed")
        out.append(
            {
                "id": _id(row["id"], f"{label}.id", "D-"),
                "condition": _text(row["condition"], f"{label}.condition"),
                "produces": produces,
                "evidence_method": _text(
                    row["evidence_method"], f"{label}.evidence_method"
                ),
                "completion": completion,
            }
        )
    return out


def _normalize_tests(value: Any, declared_produces: Collection[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for index, row in enumerate(_rows(value, "contract.tests")):
        label = f"tests[{index}]"
        _exact_keys(
            row,
            label,
            {"id", "produces", "expected_outcome", "surface", "evidence_method"},
        )
        ident = _id(row["id"], f"{label}.id", "T-")
        produces = _string_list(row["produces"], f"tests {ident}")
        unknown = sorted(set(produces) - set(declared_produces))
        if unknown:
            _error(f"{label}.produces are not exact step produces: {', '.join(unknown)}")
        out.append(
            {
                "id": ident,
                "produces": produces,
                "expected_outcome": _text(
                    row["expected_outcome"], f"{label}.expected_outcome"
                ),
                "surface": _text(row["surface"], f"{label}.surface"),
                "evidence_method": _text(
                    row["evidence_method"], f"{label}.evidence_method"
                ),
            }
        )
    return out


def _normalize_documentation(value: Any) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for index, row in enumerate(_rows(value, "contract.documentation")):
        label = f"documentation[{index}]"
        _exact_keys(row, label, {"id", "condition", "evidence_method"})
        condition = _text(row["condition"], f"{label}.condition")
        if "unchanged" in condition.lower() and "because" not in condition.lower():
            _error(f"{label}.condition must explain an unchanged-documentation rationale")
        out.append(
            {
                "id": _id(row["id"], f"{label}.id", "DOC-"),
                "condition": condition,
                "evidence_method": _text(
                    row["evidence_method"], f"{label}.evidence_method"
                ),
            }
        )
    return out


def _ensure_unique_ids(contract: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
    ids = [
        row["id"]
        for key in ("ready", "done", "tests", "documentation")
        for row in contract[key]
    ]
    duplicates = sorted({ident for ident in ids if ids.count(ident) > 1})
    if duplicates:
        _error(f"contract criterion IDs must be globally unique: {', '.join(duplicates)}")


def contract_for_step(step: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalize one opt-in step contract without inventing any criterion."""
    raw_step = _as_mapping(step, "step")
    raw = _as_mapping(raw_step.get("contract"), "step.contract")
    _exact_keys(
        raw,
        "step.contract",
        {"objective", "ready", "done", "tests", "documentation"},
    )
    objective = _text(raw["objective"], "contract.objective")
    statement = _text(raw_step.get("statement"), "step.statement")
    if objective != statement:
        _error("contract.objective must exactly equal the bounded step.statement")
    declared_produces = _step_produces(raw_step)
    contract: Dict[str, Any] = {
        "objective": objective,
        "ready": _normalize_ready(raw["ready"]),
        "done": _normalize_done(raw["done"], declared_produces),
        "tests": _normalize_tests(raw["tests"], declared_produces),
        "documentation": _normalize_documentation(raw["documentation"]),
    }
    _ensure_unique_ids(contract)
    done_covered = {
        produce for row in contract["done"] for produce in row["produces"]
    }
    tests_covered = {
        produce for row in contract["tests"] for produce in row["produces"]
    }
    missing_done = sorted(set(declared_produces) - done_covered)
    if missing_done:
        _error(
            "every exact step.produces item must be linked by done criteria: "
            + ", ".join(missing_done)
        )
    missing_tests = sorted(set(declared_produces) - tests_covered)
    if missing_tests:
        _error(
            "every exact step.produces item must be linked by tests: "
            + ", ".join(missing_tests)
        )
    return contract


def migration_required(dag: Any) -> bool:
    """Whether a DAG needs an explicit migration before contract certification."""
    return not isinstance(dag, Mapping) or dag.get("contract_version") != CONTRACT_VERSION


def dag_gaps(dag: Any, *, require_contract: bool = False) -> List[str]:
    """Return contract-only gaps; legacy DAGs remain valid until opted in."""
    if not isinstance(dag, Mapping):
        return ["DAG must be an object"] if require_contract else []
    version = dag.get("contract_version")
    if version is None:
        if require_contract:
            return [
                "DAG is missing contract_version; explicit step-contract migration is required"
            ]
        return []
    if version != CONTRACT_VERSION:
        return [
            f"DAG contract_version {version!r} is unsupported; expected {CONTRACT_VERSION}"
        ]
    steps = dag.get("steps")
    if not isinstance(steps, list) or not steps:
        return ["DAG steps must be a nonempty list before validating step contracts"]
    gaps: List[str] = []
    for index, step in enumerate(steps):
        try:
            contract_for_step(_as_mapping(step, f"steps[{index}]"))
        except ContractError as exc:
            sid = step.get("id") if isinstance(step, Mapping) else None
            prefix = f"step {sid}" if isinstance(sid, str) else f"steps[{index}]"
            gaps.append(f"{prefix} contract: {exc}")
    return gaps


def contract_identity(contract: Mapping[str, Any]) -> str:
    """Stable digest for the normalized contract carried by each evidence receipt."""
    try:
        encoded = json.dumps(
            contract, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        _error(f"contract cannot be canonicalized: {exc}")
    return hashlib.sha256(encoded).hexdigest()


def _supplier_ids(step: Mapping[str, Any]) -> List[str]:
    inputs = step.get("inputs") or []
    if not isinstance(inputs, list):
        _error("step.inputs must be a list")
    suppliers: List[str] = []
    for index, item in enumerate(inputs):
        row = _as_mapping(item, f"step.inputs[{index}]")
        supplier = row.get("from")
        if supplier is None:
            continue
        suppliers.append(_text(supplier, f"step.inputs[{index}].from"))
    return sorted(set(suppliers))


def dependency_readiness(
    step: Mapping[str, Any], *, completed_suppliers: Collection[str]
) -> Dict[str, Any]:
    """Classify dependency eligibility only; it never certifies code readiness."""
    normalized = contract_for_step(step)
    complete = {str(item) for item in completed_suppliers}
    missing = [supplier for supplier in _supplier_ids(step) if supplier not in complete]
    return {
        "status": "blocked" if missing else "ready-to-plan",
        "missing_dependencies": missing,
        "certified_ready_to_code": False,
        "contract_sha256": contract_identity(normalized),
        "readiness_evaluated_at": "selected-step/cold-resume",
    }


def packet_view(step: Mapping[str, Any], *, cold_resume: bool = True) -> Dict[str, Any]:
    """Return a compact, display-safe contract packet for the selected step."""
    contract = contract_for_step(step)
    return {
        "contract_version": CONTRACT_VERSION,
        "quality_floor_version": QUALITY_FLOOR_VERSION,
        "contract_sha256": contract_identity(contract),
        "objective": contract["objective"],
        "ready": contract["ready"],
        "done_integrated": [
            row for row in contract["done"] if row["completion"] == "integrated"
        ],
        "done_deployed": [
            row for row in contract["done"] if row["completion"] == "deployed"
        ],
        "tests": contract["tests"],
        "documentation": contract["documentation"],
        "certified_ready_to_code": False,
        "readiness_evaluated_at": (
            "selected-step/cold-resume" if cold_resume else "selected-step"
        ),
        "completion_boundary": (
            "all-required-done-before-merge; integration-asserted-at-merge; "
            "deployment-only-with-host-reported-evidence"
        ),
    }


def _identity(value: Any, label: str, pattern: re.Pattern[str]) -> str:
    text = _text(value, label)
    if not pattern.fullmatch(text):
        _error(f"{label} has an invalid identity format")
    return text


def validate_certified_rebind(
    *,
    certified_head: Any,
    current_head: Any,
    certified_artifact_identity: Any,
    artifact_identity: Any,
    ancestry: Any,
) -> Dict[str, Any]:
    """Accept a same-tree evidence rebind only from caller-provided git ancestry.

    ``ancestry`` must be a concrete sequence from the current repository query,
    containing the certified head.  A boolean or a prose assertion is never a
    substitute for that chain.
    """
    certified = _identity(certified_head, "certified_head", _HEAD_RE)
    current = _identity(current_head, "current_head", _HEAD_RE)
    certified_artifact = _identity(
        certified_artifact_identity, "certified_artifact_identity", _IDENTITY_RE
    )
    current_artifact = _identity(artifact_identity, "artifact_identity", _IDENTITY_RE)
    if not isinstance(ancestry, Sequence) or isinstance(ancestry, (str, bytes)):
        _error("certified rebind ancestry must be a concrete sequence of commit identities")
    chain = [_identity(item, "certified rebind ancestry item", _HEAD_RE) for item in ancestry]
    if certified_artifact != current_artifact:
        _error("certified rebind artifact identity changed; new product verification is required")
    if certified not in chain:
        _error("certified rebind ancestry does not contain the certified head")
    if not chain or chain[0] != current:
        _error("certified rebind ancestry must start at the current head")
    return {
        "certified_head": certified,
        "current_head": current,
        "artifact_identity": current_artifact,
        "ancestry": chain,
    }


def _verify_checks(
    verify_record: Any,
) -> tuple[
    Mapping[str, Any],
    Mapping[str, Any],
    Mapping[str, Any],
    Dict[str, Mapping[str, Any]],
    Dict[str, Mapping[str, Any]],
]:
    record = _as_mapping(verify_record, "verify_record")
    manifest = _as_mapping(record.get("manifest"), "verify_record.manifest")
    results = _as_mapping(record.get("results"), "verify_record.results")
    manifest_rows = manifest.get("checks")
    result_rows = results.get("checks")
    if not isinstance(manifest_rows, list) or not isinstance(result_rows, list):
        _error("verify_record manifest and results must include checks lists")
    manifests: Dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(manifest_rows):
        check = _as_mapping(row, f"verify_record.manifest.checks[{index}]")
        check_id = _text(check.get("id"), f"verify_record.manifest.checks[{index}].id")
        if check_id in manifests:
            _error(f"verify_record manifest repeats check ID {check_id}")
        manifests[check_id] = check
    results_by_id: Dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(result_rows):
        check = _as_mapping(row, f"verify_record.results.checks[{index}]")
        check_id = _text(check.get("id"), f"verify_record.results.checks[{index}].id")
        if check_id in results_by_id:
            _error(f"verify_record results repeat check ID {check_id}")
        results_by_id[check_id] = check
    return record, manifest, results, manifests, results_by_id


def _require_verify_action(results: Mapping[str, Any]) -> str:
    action = _text(
        results.get("action_id", results.get("action")), "verify_record.results.action_id"
    )
    if results.get("all_passed") is not True:
        _error("verify_record did not pass all checks")
    if results.get("content_changed") not in (False, None):
        _error("verify_record changed content; a fresh stable verification is required")
    return action


def _evidence_rows(value: Any, label: str, required: Collection[str]) -> Dict[str, Mapping[str, Any]]:
    if not isinstance(value, list):
        _error(f"evidence.{label} must be a list of evidence rows")
    rows: Dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(value):
        row = _as_mapping(raw, f"evidence row {label}[{index}]")
        _exact_keys(row, f"evidence row {label}[{index}]", required)
        ident = _text(row.get("id"), f"evidence row {label}[{index}].id")
        if ident in rows:
            _error(f"evidence row {label} repeats criterion ID {ident}")
        rows[ident] = row
    return rows


def _require_verify_record_reference(
    criterion: Mapping[str, Any],
    reference: str,
    manifests: Mapping[str, Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
    *,
    label: str,
) -> None:
    """Bind a claimed script-derived observation to one passed manifest check."""
    if not reference.startswith("check:"):
        _error(f"evidence.{label} {criterion['id']} verify-record reference must be check:<id>")
    check_id = _text(reference[len("check:") :], f"evidence.{label} {criterion['id']}.reference")
    manifest = manifests.get(check_id)
    result = results.get(check_id)
    if manifest is None or result is None:
        _error(f"evidence.{label} {criterion['id']} is not bound to a real verify-record check")
    if manifest.get("kind") != "test" or result.get("kind") != "test":
        _error(f"verify-record check {check_id} must be a test check")
    if result.get("status") != "passed" or result.get("exit") != 0:
        _error(f"verify-record check {check_id} did not pass")
    produces = criterion.get("produces")
    if produces is not None:
        acceptance = manifest.get("acceptance")
        if not isinstance(acceptance, list) or not set(produces).issubset(
            {item for item in acceptance if isinstance(item, str)}
        ):
            _error(f"verify-record check {check_id} acceptance does not cover {criterion['id']}")


def _require_criterion_rows(
    criteria: Sequence[Mapping[str, Any]],
    rows: Mapping[str, Mapping[str, Any]],
    *,
    label: str,
    require_condition: bool = False,
    manifests: Optional[Mapping[str, Mapping[str, Any]]] = None,
    results: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> List[str]:
    required_ids = {row["id"] for row in criteria}
    unexpected = sorted(set(rows) - required_ids)
    if unexpected:
        _error(f"evidence.{label} names criteria outside the contract: {', '.join(unexpected)}")
    missing = sorted(required_ids - set(rows))
    if missing:
        _error(f"evidence.{label} is missing required criterion evidence: {', '.join(missing)}")
    discharged: List[str] = []
    for criterion in criteria:
        row = rows[criterion["id"]]
        if require_condition and _text(
            row.get("condition"), f"evidence row {label}.{criterion['id']}.condition"
        ) != criterion["condition"]:
            _error(f"evidence.{label} {criterion['id']} condition must exactly match the contract")
        method = _text(row.get("method"), f"evidence row {label}.{criterion['id']}.method")
        if method != criterion["evidence_method"]:
            _error(f"evidence.{label} {criterion['id']} method must exactly match contract evidence_method")
        source = _text(row.get("source"), f"evidence row {label}.{criterion['id']}.source")
        if source not in _EVIDENCE_SOURCES:
            _error(f"evidence.{label} {criterion['id']} source must name a concrete evidence source")
        if criterion.get("completion") == "deployed" and source != "host-reported":
            _error(f"deployed done criterion {criterion['id']} requires host-reported evidence")
        reference = _text(row.get("reference"), f"evidence row {label}.{criterion['id']}.reference")
        if source == "verify-record":
            if manifests is None or results is None:
                _error(f"evidence.{label} {criterion['id']} cannot bind a missing verify record")
            _require_verify_record_reference(
                criterion, reference, manifests, results, label=label
            )
        _text(row.get("observed"), f"evidence row {label}.{criterion['id']}.observed")
        discharged.append(criterion["id"])
    return discharged


def _require_test_rows(
    criteria: Sequence[Mapping[str, Any]],
    rows: Mapping[str, Mapping[str, Any]],
    manifests: Mapping[str, Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
) -> List[str]:
    required_ids = {row["id"] for row in criteria}
    unexpected = sorted(set(rows) - required_ids)
    if unexpected:
        _error(f"evidence.tests names criteria outside the contract: {', '.join(unexpected)}")
    missing = sorted(required_ids - set(rows))
    if missing:
        _error(f"evidence.tests is missing required criterion evidence: {', '.join(missing)}")
    discharged: List[str] = []
    for criterion in criteria:
        ident = criterion["id"]
        row = rows[ident]
        check_id = _text(row.get("check_id"), f"evidence row tests.{ident}.check_id")
        if check_id != ident:
            _error(f"evidence.tests {ident} check_id must exactly equal its criterion ID")
        if _text(
            row.get("expected_outcome"), f"evidence row tests.{ident}.expected_outcome"
        ) != criterion["expected_outcome"]:
            _error(f"evidence.tests {ident} expected_outcome must exactly match the contract")
        if _text(row.get("source"), f"evidence row tests.{ident}.source") != "verify-record":
            _error(f"evidence.tests {ident} source must be verify-record")
        _text(row.get("observed_outcome"), f"evidence row tests.{ident}.observed_outcome")
        manifest = manifests.get(check_id)
        result = results.get(check_id)
        if manifest is None or result is None:
            _error(f"evidence.tests {ident} is not bound to a real verify-record check")
        acceptance = manifest.get("acceptance")
        if not isinstance(acceptance, list) or not set(criterion["produces"]).issubset(
            {item for item in acceptance if isinstance(item, str)}
        ):
            _error(f"verify-record check {check_id} acceptance does not cover its exact produces")
        if manifest.get("kind") != "test" or result.get("kind") != "test":
            _error(f"verify-record check {check_id} must be a test check")
        if result.get("status") != "passed" or result.get("exit") != 0:
            _error(f"verify-record check {check_id} did not pass")
        discharged.append(ident)
    return discharged


def _require_planning_record(
    criteria: Sequence[Mapping[str, Any]],
    record: Mapping[str, Any],
    results: Mapping[str, Any],
    manifests: Mapping[str, Mapping[str, Any]],
    result_checks: Mapping[str, Mapping[str, Any]],
) -> None:
    if record.get("planning_passed") is not True:
        _error("ready evidence requires a fresh planning verify record with planning_passed true")
    for criterion in criteria:
        ident = criterion["id"]
        check = manifests.get(ident)
        result = result_checks.get(ident)
        if check is None or result is None:
            _error(f"ready criterion {ident} is not bound to a dedicated planning verify check")
        if check.get("kind") != "test" or result.get("kind") != "test":
            _error(f"ready criterion {ident} must be bound to a test check")
        if check.get("acceptance") != ["step plan"]:
            _error(f"ready criterion {ident} check acceptance must exactly equal ['step plan']")
        if result.get("status") != "passed" or result.get("exit") != 0:
            _error(f"ready criterion {ident} planning verify check did not pass")


def _internal_envelope(
    *,
    phase: str,
    contract: Mapping[str, Any],
    verify_action: str,
    head: str,
    environment_identity: str,
    artifact_identity: str,
) -> Dict[str, str | int]:
    return {
        "version": EVIDENCE_VERSION,
        "phase": phase,
        "contract_sha256": contract_identity(contract),
        "verify_action": verify_action,
        "head": head,
        "environment_identity": environment_identity,
        "artifact_identity": artifact_identity,
    }


def _public_rows(
    rows: Mapping[str, Mapping[str, Any]], criteria: Sequence[Mapping[str, Any]]
) -> List[Dict[str, Any]]:
    """Preserve caller evidence order only after strict contract validation."""
    return [dict(rows[criterion["id"]]) for criterion in criteria]


def validate_discharge(
    step: Mapping[str, Any],
    evidence: Mapping[str, Any],
    *,
    phase: str,
    verify_record: Mapping[str, Any],
    head: str,
    environment_identity: str,
    artifact_identity: str,
    certified_rebind: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate a simple public receipt against authoritative runtime metadata.

    At ``ready`` the public payload is exactly ``{"ready": [...]}``.  At
    product phases it is exactly ``{"done": [...], "tests": [...],
    "documentation": [...]}``.  The caller supplies the authoritative current
    identities separately, so an LLM cannot echo or forge durable state.  The
    returned ``record`` is intentionally internal state: it carries the bound
    envelope and validated receipt for cold-resume checks.
    """
    if phase not in _PHASES:
        _error(f"unsupported contract evidence phase {phase!r}")
    contract = contract_for_step(step)
    raw = _as_mapping(evidence, "evidence")
    selected_head = _identity(head, "selected head", _HEAD_RE)
    selected_environment = _identity(environment_identity, "selected environment_identity", _IDENTITY_RE)
    selected_artifact = _identity(artifact_identity, "selected artifact_identity", _IDENTITY_RE)
    record, _, results, manifests, result_checks = _verify_checks(verify_record)
    verify_action = _require_verify_action(results)
    envelope = _internal_envelope(
        phase=phase,
        contract=contract,
        verify_action=verify_action,
        head=selected_head,
        environment_identity=selected_environment,
        artifact_identity=selected_artifact,
    )
    if phase in {"ready", "implement"}:
        _exact_keys(raw, "ready_evidence", {"ready"})
        ready_rows = _evidence_rows(
            raw["ready"],
            "ready",
            {"id", "condition", "method", "source", "reference", "observed"},
        )
        _require_planning_record(
            contract["ready"], record, results, manifests, result_checks
        )
        discharged_ready = _require_criterion_rows(
            contract["ready"],
            ready_rows,
            label="ready",
            require_condition=True,
            manifests=manifests,
            results=result_checks,
        )
        ready_public = {"ready": _public_rows(ready_rows, contract["ready"])}
        done_public: Optional[Dict[str, List[Dict[str, Any]]]] = None
        validated_receipt: Dict[str, Any] = {
            "discharged": {"ready": discharged_ready},
            "status": "ready-certified",
            "ready_is_pre_edit": True,
            "fully_closed": False,
        }
    else:
        _exact_keys(raw, "done_evidence", {"done", "tests", "documentation"})
        done_rows = _evidence_rows(
            raw["done"],
            "done",
            {"id", "method", "source", "reference", "observed"},
        )
        test_rows = _evidence_rows(
            raw["tests"],
            "tests",
            {"id", "check_id", "expected_outcome", "observed_outcome", "source"},
        )
        documentation_rows = _evidence_rows(
            raw["documentation"],
            "documentation",
            {"id", "method", "source", "reference", "observed"},
        )
        discharged_done = _require_criterion_rows(
            contract["done"],
            done_rows,
            label="done",
            manifests=manifests,
            results=result_checks,
        )
        discharged_tests = _require_test_rows(
            contract["tests"], test_rows, manifests, result_checks
        )
        discharged_documentation = _require_criterion_rows(
            contract["documentation"],
            documentation_rows,
            label="documentation",
            manifests=manifests,
            results=result_checks,
        )
        if phase in {"post-inner", "merge"}:
            if certified_rebind is None:
                _error("post-inner or merge evidence requires a certified same-tree rebind chain")
            rebind = _as_mapping(certified_rebind, "certified_rebind")
            _exact_keys(
                rebind,
                "certified_rebind",
                {
                    "certified_head",
                    "certified_artifact_identity",
                    "certified_verify_action",
                    "certified_contract_sha256",
                    "ancestry",
                },
            )
            if _text(
                rebind["certified_verify_action"], "certified_rebind.certified_verify_action"
            ) != verify_action:
                _error("certified rebind must bind the original verify action")
            if _text(
                rebind["certified_contract_sha256"],
                "certified_rebind.certified_contract_sha256",
            ) != contract_identity(contract):
                _error("certified rebind must bind the selected step contract")
            validate_certified_rebind(
                certified_head=rebind.get("certified_head"),
                current_head=selected_head,
                certified_artifact_identity=rebind.get("certified_artifact_identity"),
                artifact_identity=selected_artifact,
                ancestry=rebind.get("ancestry"),
            )
        ready_public = None
        done_public = {
            "done": _public_rows(done_rows, contract["done"]),
            "tests": _public_rows(test_rows, contract["tests"]),
            "documentation": _public_rows(
                documentation_rows, contract["documentation"]
            ),
        }
        deployed = [
            row["id"] for row in contract["done"] if row["completion"] == "deployed"
        ]
        integrated = [
            row["id"] for row in contract["done"] if row["completion"] == "integrated"
        ]
        validated_receipt = {
            "discharged": {
                "done": discharged_done,
                "tests": discharged_tests,
                "documentation": discharged_documentation,
            },
            "status": "done-evidence-certified",
            "integrated_done": integrated,
            "deployed_done": deployed,
            "all_required_done_discharged": True,
            "integration_assertion_required": phase == "merge",
            "fully_closed": False,
            "fully_closed_after_integration_assertion": phase == "merge",
        }
    return {
        "ready_evidence": ready_public,
        "done_evidence": done_public,
        "record": {
            "envelope": envelope,
            "validated_receipt": validated_receipt,
        },
    }
