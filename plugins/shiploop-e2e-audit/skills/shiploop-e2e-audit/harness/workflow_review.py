"""Validate analyst-owned workflow evidence; never infer review truth from prose.

Only version 2 reviews are accepted; each carries explicit selected-test and
Improve-review records. These are external audit records, not ShipLoop state or
a new completion gate.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

# Every accepted result at these stages passed through its own Improve child.
from dag_replay import _PLANNING_CHECKPOINTS as PLANNING_REVIEW_STAGES
from grading import _artifact_result


WORKFLOW_REVIEW_SCHEMA = "shiploop-e2e-workflow-review/2"
DIMENSIONS = (
    "literal-request-and-selected-source", "dag-execution-and-callback-attribution",
    "platform-and-consumer-contract-preserved", "planned-tests-reconciled-with-observations",
    "improve-evidence-and-reviewer-scope", "recovery-return-and-context-hygiene",
    "incremental-behavior-and-source-lineage", "performance-and-model-settings-observable",
)
STATUSES = {"supported-pass", "supported-gap", "unverified", "not-applicable"}
METHODS = {"interaction", "engine", "http", "dom", "source", "none"}


def _evidence(rows: object, root: Path, label: str, errors: list[str]) -> None:
    if not isinstance(rows, list) or not rows:
        errors.append(f"{label}: missing pinned evidence")
        return
    for index, row in enumerate(rows):
        if not _artifact_result(row, root=root, check_id=label, index=index)["valid"]:
            errors.append(f"{label}: invalid evidence {index}")


_SUPPORTED_PROTOCOLS = (4,)


def _observed_improve_actions(result: dict, errors: list[str], unknown: list[str]) -> tuple[set[str], bool, bool]:
    """Return current-run completed Improve actions without inferring review truth.

    Navigator protocol 4 stores a completed Improve receipt by its
    ordinary producer action ID, and only checkpoint actions carry one. The
    inventory is therefore exactly the recorded actions. As in the navigator,
    every record must belong to an accepted action and every accepted ``plan``
    action must have one. A snapshot of any other protocol cannot supply an
    inventory. A partial or malformed snapshot is an audit limitation, never a
    completed child record manufactured from an active producer.
    """
    has_lifecycle = "lifecycle" in result
    has_navigation = "navigation" in result
    if not has_lifecycle and not has_navigation:
        return set(), False, False
    lifecycle = result.get("lifecycle")
    navigation = result.get("navigation")
    if not isinstance(lifecycle, Mapping):
        unknown.append("current-run lifecycle container is malformed")
        return set(), False, False
    if not isinstance(navigation, Mapping):
        unknown.append("current-run navigation container is malformed")
        return set(), False, False
    run_id = lifecycle.get("run_id")
    states = navigation.get("states", [])
    if not isinstance(run_id, str) or not isinstance(states, list):
        unknown.append("current-run navigation identity or states are malformed")
        return set(), False, False

    observed: set[str] = set()
    inventories: set[frozenset[str]] = set()
    protocols: set[object] = set()
    known = False
    comparable = True
    for row in states:
        state = row.get("state") if isinstance(row, Mapping) else None
        if not isinstance(state, Mapping) or state.get("run_id") != run_id:
            continue
        known = True
        protocol = state.get("navigator_protocol_version")
        protocols.add(protocol if type(protocol) is int else None)
        if type(protocol) is not int or protocol not in _SUPPORTED_PROTOCOLS:
            unknown.append("current-run navigator protocol is unsupported; only protocol 4 supplies Improve inventory")
            comparable = False
            continue
        history = state.get("history")
        if not isinstance(history, list):
            errors.append("current-run navigator history is malformed")
            continue

        action_ids: list[str] = []
        plan_ids: set[str] = set()
        malformed_history = False
        for entry in history:
            action = entry.get("action") if isinstance(entry, Mapping) else None
            if not isinstance(action, str) or not action:
                malformed_history = True
                break
            action_ids.append(action)
            if entry.get("stage") in PLANNING_REVIEW_STAGES:
                plan_ids.add(action)
        if malformed_history or len(set(action_ids)) != len(action_ids):
            errors.append("current-run accepted history is malformed")
            continue

        records = state.get("improve_results")
        if records is None:
            unknown.append("current-run Improve records are missing")
            comparable = False
            continue
        if not isinstance(records, Mapping):
            errors.append("current-run Improve records are malformed")
            continue
        record_ids = set(records)
        if any(not isinstance(action, str) or not action for action in record_ids):
            errors.append("current-run Improve record ID is malformed")
            continue
        if any(not isinstance(receipt, Mapping) for receipt in records.values()):
            errors.append("current-run Improve receipt is malformed")
            continue
        extra = record_ids - set(action_ids)
        missing_plans = plan_ids - record_ids
        if extra:
            errors.append("current-run Improve records have no accepted parent action")
        if missing_plans:
            unknown.append("current-run accepted planning-stage result has no Improve record")
            comparable = False
        if not extra and not missing_plans:
            observed.update(record_ids)
            inventories.add(frozenset(record_ids))
    if not known:
        unknown.append("current-run navigator state is missing")
        comparable = False
    if len(inventories) > 1:
        unknown.append("current-run Improve inventory is ambiguous across snapshots")
        comparable = False
    if len(protocols) > 1:
        unknown.append("current-run navigator protocol is ambiguous across snapshots")
        comparable = False
    return observed, known, comparable


def validate_review(review: dict, result: dict, evidence_root: Path) -> dict:
    """Check bindings and explicit evidence obligations; absent facts stay unknown."""
    errors: list[str] = []
    gaps: list[str] = []
    unknown: list[str] = []
    if not isinstance(review, dict):
        return {"status": "invalid", "errors": ["review must be an object"], "gaps": [], "unverified": []}
    if review.get("schema") != WORKFLOW_REVIEW_SCHEMA:
        errors.append(f"unsupported workflow review schema; only {WORKFLOW_REVIEW_SCHEMA} is accepted")
    expected = {key: result.get(key) for key in ("trial_id", "candidate_digest", "baseline_digest", "skill_digest")}
    expected["harness_digest"] = result.get("harness_snapshot", {}).get("package_sha256")
    for key, value in expected.items():
        if key not in review or review[key] != value:
            errors.append(f"{key}: review binding mismatch")
    for key in ("reviewer", "reviewed_at", "scope"):
        if not isinstance(review.get(key), str) or not review[key].strip():
            errors.append(f"{key}: required")
    root = Path(evidence_root)
    if not root.is_dir() or root.is_symlink():
        errors.append("invalid evidence root")
    root = root.resolve()
    dimensions = review.get("dimensions", [])
    if not isinstance(dimensions, list):
        errors.append("dimensions must be a list")
        dimensions = []
    seen: set[str] = set()
    for row in dimensions:
        if not isinstance(row, dict) or row.get("id") not in DIMENSIONS:
            errors.append("unknown dimension")
            continue
        key = row["id"]
        if key in seen:
            errors.append(f"{key}: duplicate dimension")
        seen.add(key)
        status = row.get("status")
        if status not in STATUSES:
            errors.append(f"{key}: invalid status")
        elif status == "unverified":
            unknown.append(key)
        else:
            _evidence(row.get("evidence"), root, key, errors)
            if not isinstance(row.get("notes"), str) or not row["notes"].strip():
                errors.append(f"{key}: missing explanation")
            if status == "supported-gap":
                gaps.append(key)
    unknown.extend(sorted(set(DIMENSIONS) - seen))

    inventory = review.get("inventory")
    expected_tests: set[str] | None = None
    expected_improves: set[str] | None = None
    if not isinstance(inventory, dict):
        unknown.append("pinned selected-test and Improve inventory not recorded")
    else:
        _evidence(inventory.get("evidence"), root, "inventory", errors)
        for field in ("selected_test_ids", "improve_action_ids"):
            values = inventory.get(field)
            if (not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values)
                    or len(set(values)) != len(values)):
                errors.append(f"inventory: invalid {field}")
            elif field == "selected_test_ids":
                expected_tests = set(values)
            else:
                expected_improves = set(values)
        if expected_improves is not None:
            observed_improves, observed_known, comparable = _observed_improve_actions(
                result, errors, unknown
            )
            if observed_known and comparable and expected_improves != observed_improves:
                gaps.append("Improve inventory differs from accepted current-run actions")

    selected = review.get("selected_tests")
    if not isinstance(selected, list) or not selected:
        unknown.append("selected-test reconciliation not recorded")
    else:
        ids: set[str] = set()
        for row in selected:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
                errors.append("invalid selected test")
                continue
            key = row["id"]
            if key in ids:
                errors.append(f"{key}: duplicate selected test")
            ids.add(key)
            if row.get("required_method") not in METHODS or row.get("observed_method") not in METHODS:
                errors.append(f"{key}: unknown observation method")
            disposition = row.get("disposition")
            if disposition == "passed":
                _evidence(row.get("evidence"), root, key, errors)
                if row.get("observed_method") != row.get("required_method") or row.get("observed_method") == "none":
                    gaps.append(f"{key}: selected observation was substituted")
            elif disposition in {"failed", "unrun", "blocked"}:
                gaps.append(f"{key}: {disposition}")
            elif disposition == "not-applicable":
                if not row.get("reason") or row.get("requirement_withdrawn") is not True:
                    gaps.append(f"{key}: unsupported N/A for selected requirement")
                _evidence(row.get("evidence"), root, key, errors)
            else:
                errors.append(f"{key}: invalid test disposition")
        if expected_tests is not None and ids != expected_tests:
            gaps.append("selected-test rows do not cover the pinned inventory exactly")

    improves = review.get("improve_reviews")
    if not isinstance(improves, list) or not improves:
        unknown.append("Improve availability and scope not recorded")
    else:
        ids = set()
        for row in improves:
            if not isinstance(row, dict) or not isinstance(row.get("action_id"), str) or not row["action_id"]:
                errors.append("invalid Improve record")
                continue
            key = row["action_id"]
            if key in ids:
                errors.append(f"{key}: duplicate Improve record")
            ids.add(key)
            _evidence(row.get("evidence"), root, key, errors)
            if not row.get("scope") or row.get("current_candidate") is not True:
                gaps.append(f"{key}: missing current-candidate review scope")
            available = row.get("independent_availability")
            if available == "available":
                if row.get("fresh_review_completed") is not True:
                    gaps.append(f"{key}: available fresh review not completed")
            elif available == "unavailable":
                if not row.get("fallback_limitation"):
                    gaps.append(f"{key}: self-review limitation missing")
            else:
                unknown.append(f"{key}: independent reviewer availability unknown")
        if expected_improves is not None and ids != expected_improves:
            gaps.append("Improve records do not cover the pinned inventory exactly")
    status = "invalid" if errors else "supported-gap" if gaps else "unverified" if unknown else "supported-pass"
    return {"schema": "shiploop-e2e-workflow-assessment/1", "status": status,
            "errors": errors, "gaps": gaps, "unverified": sorted(set(unknown)),
            "note": "Validates analyst declarations and pinned evidence, not their semantic truth; no ShipLoop state changed."}
