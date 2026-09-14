"""Conservative invalidation of system-test evidence after product changes.

ShipLoop's completed step receipts are immutable: a later corrective change is
represented by a different completed DAG step, rather than by changing the
old receipt's SHA.  A system-test result therefore needs a snapshot of the
*whole completed product inventory at the instant that test was merged*.

This module is deliberately pure.  The protocol supplies the validated DAG,
receipt records, and an actual product identity made from the repository's
Git revision plus :func:`shiploop_evidence.fingerprint`.  This module never
claims that a host-provided impact declaration narrows a required retest: any
later non-system/non-publish completed product step, receipt identity drift,
or product-fingerprint/path drift makes the old system proof stale.  The
declaration is still strict, useful audit evidence for local cases,
documentation, and skills.

The intended durable use is:

1. call :func:`capture_system_proof` when a SYS owner is originally merged;
   store it under its SYS case ID and never overwrite it;
2. before quality/release, call :func:`assess_all` against the actual current
   completed receipts and product identity;
3. if it reports stale cases, complete a *new* equivalent SYS case and capture
   that new proof at its own merge; then validate an explicit mapping with
   :func:`validate_revalidation`.

The frozen original SYS case stays in the catalog.  A replacement maps to it;
it does not rewrite history or mutate a completed receipt.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from typing import Any


VERSION = 1
SYSTEM_ACTIVITIES = frozenset(("system-test-pre", "system-test-post"))
PUBLISH_ACTIVITY = "publish"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_STEP_ID = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]{0,159}$")
_ACTION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,160}$")
_SYS_ID = re.compile(r"^SYS-[A-Z0-9][A-Z0-9._-]{0,79}$")
_TEST_ID = re.compile(r"^T-[A-Z0-9][A-Z0-9._-]{0,79}$")


class InvalidationError(ValueError):
    """An invalidation snapshot, declaration, or replacement is unsafe."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidationError(message)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidationError("value is not JSON serializable") from exc


def digest(value: Any) -> str:
    """Return the canonical SHA-256 used in durable snapshot bindings."""
    return hashlib.sha256(_canonical(value)).hexdigest()


def _copy(value: Any) -> Any:
    return json.loads(_canonical(value).decode("utf-8"))


def _sha(value: Any, label: str) -> str:
    _need(isinstance(value, str) and _SHA256.fullmatch(value) is not None, f"{label} must be a SHA-256 digest")
    return value


def _git_sha(value: Any, label: str) -> str:
    _need(isinstance(value, str) and _GIT_SHA.fullmatch(value) is not None, f"{label} must be a Git SHA")
    return value


def _step_id(value: Any, label: str) -> str:
    _need(isinstance(value, str) and _STEP_ID.fullmatch(value) is not None, f"{label} must be a safe step ID")
    return value


def _action_id(value: Any, label: str) -> str:
    _need(isinstance(value, str) and _ACTION_ID.fullmatch(value) is not None, f"{label} must be a safe action ID")
    return value


def _sys_id(value: Any, label: str) -> str:
    _need(isinstance(value, str) and _SYS_ID.fullmatch(value) is not None, f"{label} must be a safe SYS case ID")
    return value


def _text(value: Any, label: str) -> str:
    _need(isinstance(value, str) and bool(value.strip()) and "\x00" not in value, f"{label} must be a nonempty string")
    return value


def _safe_path(value: Any, label: str) -> str:
    _need(
        isinstance(value, str)
        and bool(value)
        and len(value) <= 4096
        and value.isprintable(),
        f"{label} must be a safe repository-relative path",
    )
    _need(
        not value.startswith("/")
        and "\\" not in value
        and all(part not in ("", ".", "..") for part in value.split("/")),
        f"{label} must be a safe repository-relative path",
    )
    return value


def _catalog(value: Any) -> dict[str, dict[str, Any]]:
    """Normalize the system-test fields needed for immutable replacement."""
    if isinstance(value, Mapping) and "system_tests" in value:
        value = value["system_tests"]
    _need(isinstance(value, Mapping), "system-test catalog must be an object")
    cases = value.get("cases")
    _need(isinstance(cases, list), "system-test catalog cases must be a list")
    result: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(cases):
        label = f"system-test catalog case {index}"
        _need(isinstance(raw, Mapping), f"{label} must be an object")
        ident = _sys_id(raw.get("id"), f"{label}.id")
        _need(ident not in result, f"system-test catalog duplicates case {ident}")
        phase = raw.get("phase")
        _need(phase in ("pre_deployment", "post_deployment"), f"{label}.phase is invalid")
        test_step = _step_id(raw.get("test_step"), f"{label}.test_step")
        test_id = raw.get("test_id")
        _need(isinstance(test_id, str) and _TEST_ID.fullmatch(test_id) is not None, f"{label}.test_id is invalid")
        result[ident] = {
            "id": ident,
            "phase": phase,
            "requirement": _text(raw.get("requirement"), f"{label}.requirement"),
            "expected_outcome": _text(raw.get("expected_outcome"), f"{label}.expected_outcome"),
            "environment": _text(raw.get("environment"), f"{label}.environment"),
            "prerequisites": _string_ids(raw.get("prerequisites"), f"{label}.prerequisites"),
            "test_step": test_step,
            "test_id": test_id,
            "deployment_step": raw.get("deployment_step"),
        }
    return result


def _string_ids(value: Any, label: str) -> list[str]:
    _need(isinstance(value, list), f"{label} must be a list")
    out = [_step_id(item, f"{label} entry") for item in value]
    _need(len(out) == len(set(out)), f"{label} must not contain duplicate IDs")
    return out


def _steps(value: Any) -> dict[str, dict[str, Any]]:
    if isinstance(value, Mapping) and "steps" in value:
        value = value["steps"]
    _need(isinstance(value, list), "DAG steps must be a list")
    result: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(value):
        _need(isinstance(raw, Mapping), f"DAG step {index} must be an object")
        ident = _step_id(raw.get("id"), f"DAG step {index}.id")
        _need(ident not in result, f"DAG step IDs duplicate: {ident}")
        activity = raw.get("activity")
        _need(activity is None or isinstance(activity, str), f"DAG step {ident}.activity is invalid")
        produces = raw.get("produces", [])
        if isinstance(produces, str):
            produces = [produces]
        _need(isinstance(produces, list) and all(isinstance(item, str) for item in produces), f"DAG step {ident}.produces is invalid")
        result[ident] = {"id": ident, "activity": activity, "produces": list(produces)}
    return result


def _receipts(value: Any) -> dict[str, Mapping[str, Any]]:
    _need(isinstance(value, Mapping), "completed receipts must be an ID-to-receipt mapping")
    result: dict[str, Mapping[str, Any]] = {}
    for raw_id, raw in value.items():
        ident = _step_id(raw_id, "receipt step ID")
        _need(isinstance(raw, Mapping), f"receipt {ident} must be an object")
        result[ident] = raw
    return result


def normalize_product_identity(value: Any) -> dict[str, Any]:
    """Validate a product identity derived from real repository observations.

    ``worktree_fingerprint`` is the complete actual-worktree fingerprint.  The
    path map is a useful explainability layer and may be empty when no bounded
    path inventory was captured, but it never replaces the complete fingerprint.
    A Git revision alone is deliberately insufficient because an audit-only
    commit may change it without changing product bytes.
    """
    _need(isinstance(value, Mapping), "product identity must be an object")
    required = {"version", "revision", "worktree_fingerprint", "paths"}
    _need(set(value) == required, "product identity has an unsupported schema")
    _need(value.get("version") == VERSION, "product identity version is unsupported")
    paths = value.get("paths")
    _need(isinstance(paths, Mapping), "product identity paths must be a mapping")
    normalized_paths: dict[str, str] = {}
    for raw_path, raw_digest in paths.items():
        path = _safe_path(raw_path, "product identity path")
        _need(path not in normalized_paths, "product identity paths duplicate")
        normalized_paths[path] = _sha(raw_digest, f"product identity path {path}")
    return {
        "version": VERSION,
        "revision": _git_sha(value.get("revision"), "product identity revision"),
        "worktree_fingerprint": _sha(value.get("worktree_fingerprint"), "product identity worktree_fingerprint"),
        "paths": {path: normalized_paths[path] for path in sorted(normalized_paths)},
    }


def product_identity_digest(value: Any) -> str:
    """Canonical digest of a validated product identity."""
    return digest(normalize_product_identity(value))


def product_content_identity_digest(value: Any) -> str:
    """Digest product bytes and bounded paths while retaining revision as provenance.

    An audit-only Git commit changes ``revision`` but does not invalidate a
    proof whose actual worktree fingerprint and observed path values did not
    change.  Revalidation therefore binds this content identity rather than a
    full identity digest that includes the revision.
    """
    identity = normalize_product_identity(value)
    return digest(
        {
            "version": VERSION,
            "worktree_fingerprint": identity["worktree_fingerprint"],
            "paths": identity["paths"],
        }
    )


def _complete_product_inventory(
    steps: Mapping[str, Mapping[str, Any]], receipts: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Capture all merged non-SYS/non-publish candidates conservatively."""
    result: dict[str, dict[str, Any]] = {}
    for ident, step in steps.items():
        raw = receipts.get(ident)
        if raw is None or raw.get("status") != "complete":
            continue
        activity = step["activity"]
        if activity in SYSTEM_ACTIVITIES or activity == PUBLISH_ACTIVITY:
            continue
        merged = _git_sha(raw.get("merged_sha"), f"completed product receipt {ident}.merged_sha")
        final_head = raw.get("final_head")
        if final_head is not None:
            final_head = _git_sha(final_head, f"completed product receipt {ident}.final_head")
        # These digests cover the real typed record values.  Their detailed
        # validation belongs to the protocol that created them; here they are
        # immutable identity inputs that catch a changed/replaced receipt.
        result[ident] = {
            "id": ident,
            "merged_sha": merged,
            "final_head": final_head,
            "produces_sha256": digest(step["produces"]),
            "contract_done_sha256": digest(raw.get("contract_done")),
            "contract_closure_sha256": digest(raw.get("contract_closure")),
        }
    return result


def _proof_anchor(case: Mapping[str, Any], receipt: Mapping[str, Any]) -> dict[str, str]:
    _need(receipt.get("status") == "complete", f"system test {case['id']} owner is not complete")
    merged = _git_sha(receipt.get("merged_sha"), f"system test {case['id']} merged_sha")
    closure = receipt.get("contract_closure")
    _need(isinstance(closure, Mapping), f"system test {case['id']} lacks contract closure")
    _need(closure.get("fully_closed") is True and closure.get("integrated_sha") == merged,
          f"system test {case['id']} lacks integrated contract closure")
    saved = receipt.get("contract_done")
    _need(isinstance(saved, Mapping), f"system test {case['id']} lacks Definition of Done evidence")
    _need(saved.get("step") == case["test_step"], f"system test {case['id']} Definition of Done targets another step")
    record = saved.get("record")
    _need(isinstance(record, Mapping), f"system test {case['id']} Definition of Done record is invalid")
    envelope = record.get("envelope")
    _need(isinstance(envelope, Mapping), f"system test {case['id']} Definition of Done envelope is invalid")
    action = _action_id(envelope.get("verify_action"), f"system test {case['id']} verify_action")
    return {
        "test_step": case["test_step"],
        "merged_sha": merged,
        "verify_action": action,
        "check_sha256": _sha(saved.get("check_sha256"), f"system test {case['id']} check_sha256"),
        "contract_done_sha256": digest(saved),
        "contract_closure_sha256": digest(closure),
    }


def _snapshot_body(
    *, case: Mapping[str, Any], proof: Mapping[str, Any], product_identity: Mapping[str, Any], products: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "version": VERSION,
        "case": _copy(case),
        "proof": _copy(proof),
        "product_identity": _copy(product_identity),
        "products": {ident: _copy(products[ident]) for ident in sorted(products)},
    }


def capture_system_proof(
    catalog: Any,
    steps: Any,
    receipts: Any,
    *,
    case_id: str,
    product_identity: Any,
) -> dict[str, Any]:
    """Create an immutable SYS proof snapshot at the owner's original merge.

    Call this only from the completed original SYS owner merge path.  Do not
    retroactively create it at quality: that would incorrectly bless a test
    after later product work already changed its target.
    """
    cases = _catalog(catalog)
    ident = _sys_id(case_id, "system-test case_id")
    _need(ident in cases, "system-test case_id is not in the frozen catalog")
    normalized_steps = _steps(steps)
    normalized_receipts = _receipts(receipts)
    case = cases[ident]
    owner = normalized_steps.get(case["test_step"])
    _need(owner is not None and owner["activity"] in SYSTEM_ACTIVITIES,
          f"system test {ident} owner is not a system-test activity")
    receipt = normalized_receipts.get(case["test_step"])
    _need(receipt is not None, f"system test {ident} owner receipt is missing")
    proof = _proof_anchor(case, receipt)
    identity = normalize_product_identity(product_identity)
    products = _complete_product_inventory(normalized_steps, normalized_receipts)
    body = _snapshot_body(case=case, proof=proof, product_identity=identity, products=products)
    return {**body, "snapshot_sha256": digest(body)}


def validate_snapshot(value: Any) -> dict[str, Any]:
    """Reject tampering or a schema that loses any immutable proof binding."""
    _need(isinstance(value, Mapping), "system-test proof snapshot must be an object")
    required = {"version", "case", "proof", "product_identity", "products", "snapshot_sha256"}
    _need(set(value) == required, "system-test proof snapshot has an unsupported schema")
    _need(value.get("version") == VERSION, "system-test proof snapshot version is unsupported")
    case = _catalog({"cases": [value.get("case")]})
    _need(len(case) == 1, "system-test proof snapshot case is invalid")
    checked_case = next(iter(case.values()))
    proof = value.get("proof")
    _need(isinstance(proof, Mapping) and set(proof) == {
        "test_step", "merged_sha", "verify_action", "check_sha256", "contract_done_sha256", "contract_closure_sha256",
    }, "system-test proof snapshot anchor has an unsupported schema")
    _need(proof.get("test_step") == checked_case["test_step"], "system-test proof snapshot owner differs from case")
    checked_proof = {
        "test_step": _step_id(proof.get("test_step"), "system-test proof snapshot test_step"),
        "merged_sha": _git_sha(proof.get("merged_sha"), "system-test proof snapshot merged_sha"),
        "verify_action": _action_id(proof.get("verify_action"), "system-test proof snapshot verify_action"),
        "check_sha256": _sha(proof.get("check_sha256"), "system-test proof snapshot check_sha256"),
        "contract_done_sha256": _sha(proof.get("contract_done_sha256"), "system-test proof snapshot contract_done_sha256"),
        "contract_closure_sha256": _sha(proof.get("contract_closure_sha256"), "system-test proof snapshot contract_closure_sha256"),
    }
    identity = normalize_product_identity(value.get("product_identity"))
    raw_products = value.get("products")
    _need(isinstance(raw_products, Mapping), "system-test proof snapshot products must be a mapping")
    products: dict[str, dict[str, Any]] = {}
    for raw_id, raw in raw_products.items():
        ident = _step_id(raw_id, "system-test proof snapshot product ID")
        _need(isinstance(raw, Mapping) and set(raw) == {
            "id", "merged_sha", "final_head", "produces_sha256", "contract_done_sha256", "contract_closure_sha256",
        }, f"system-test proof snapshot product {ident} has an unsupported schema")
        _need(raw.get("id") == ident, f"system-test proof snapshot product {ident} ID differs")
        final_head = raw.get("final_head")
        products[ident] = {
            "id": ident,
            "merged_sha": _git_sha(raw.get("merged_sha"), f"system-test proof snapshot product {ident}.merged_sha"),
            "final_head": None if final_head is None else _git_sha(final_head, f"system-test proof snapshot product {ident}.final_head"),
            "produces_sha256": _sha(raw.get("produces_sha256"), f"system-test proof snapshot product {ident}.produces_sha256"),
            "contract_done_sha256": _sha(raw.get("contract_done_sha256"), f"system-test proof snapshot product {ident}.contract_done_sha256"),
            "contract_closure_sha256": _sha(raw.get("contract_closure_sha256"), f"system-test proof snapshot product {ident}.contract_closure_sha256"),
        }
    body = _snapshot_body(case=checked_case, proof=checked_proof, product_identity=identity, products=products)
    _need(value.get("snapshot_sha256") == digest(body), "system-test proof snapshot digest changed")
    return {**body, "snapshot_sha256": digest(body)}


def _path_changes(before: Mapping[str, str], after: Mapping[str, str]) -> dict[str, list[str]]:
    return {
        "added": sorted(set(after) - set(before)),
        "changed": sorted(path for path in set(before) & set(after) if before[path] != after[path]),
        "removed": sorted(set(before) - set(after)),
    }


def _product_changes(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    old_products = before["products"]
    new_products = after["products"]
    receipt_changes = {
        "added": sorted(set(new_products) - set(old_products)),
        "changed": sorted(ident for ident in set(old_products) & set(new_products) if old_products[ident] != new_products[ident]),
        "missing": sorted(set(old_products) - set(new_products)),
    }
    paths = _path_changes(before["product_identity"]["paths"], after["product_identity"]["paths"])
    fingerprint_changed = before["product_identity"]["worktree_fingerprint"] != after["product_identity"]["worktree_fingerprint"]
    return {
        "receipts": receipt_changes,
        "paths": paths,
        "worktree_fingerprint_changed": fingerprint_changed,
        "revision_changed": before["product_identity"]["revision"] != after["product_identity"]["revision"],
    }


def _has_actual_change(changes: Mapping[str, Any]) -> bool:
    receipts = changes["receipts"]
    paths = changes["paths"]
    return bool(
        changes["worktree_fingerprint_changed"]
        or receipts["added"] or receipts["changed"] or receipts["missing"]
        or paths["added"] or paths["changed"] or paths["removed"]
    )


def _paths(value: Iterable[Any], label: str) -> list[str]:
    out = [_safe_path(item, f"{label} entry") for item in value]
    _need(len(out) == len(set(out)), f"{label} must not duplicate paths")
    return sorted(out)


def _ids(value: Iterable[Any], label: str) -> list[str]:
    out = [_text(item, f"{label} entry") for item in value]
    _need(len(out) == len(set(out)), f"{label} must not duplicate IDs")
    return sorted(out)


def validate_impact_map(
    value: Any,
    *,
    known_local_cases: Iterable[str] = (),
    catalog: Any | None = None,
    known_documentation: Iterable[str] = (),
    known_skills: Iterable[str] = (),
    before_identity: Any | None = None,
    after_identity: Any | None = None,
) -> dict[str, Any]:
    """Validate a declared impact map without trusting it to narrow a retest.

    When both identities are supplied, the artifact rows must exactly match
    their actual observed path-digest delta.  This binds the declaration to
    real evidence instead of an LLM's asserted list of changed files.
    """
    _need(isinstance(value, Mapping), "invalidation impact map must be an object")
    required = {"version", "certainty", "changes", "affected"}
    _need(set(value) == required and value.get("version") == VERSION,
          "invalidation impact map has an unsupported schema")
    certainty = value.get("certainty")
    _need(certainty in ("known", "uncertain"), "invalidation impact certainty is invalid")
    changes = value.get("changes")
    _need(isinstance(changes, Mapping) and set(changes) == {"artifacts", "contracts", "produces"},
          "invalidation impact changes has an unsupported schema")
    rows = changes["artifacts"]
    _need(isinstance(rows, list), "invalidation impact artifacts must be a list")
    artifacts: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for index, row in enumerate(rows):
        label = f"invalidation impact artifact {index}"
        _need(isinstance(row, Mapping) and set(row) == {"path", "before_sha256", "after_sha256"},
              f"{label} has an unsupported schema")
        path = _safe_path(row.get("path"), f"{label}.path")
        _need(path not in seen_paths, "invalidation impact artifacts duplicate a path")
        seen_paths.add(path)
        previous, current = row.get("before_sha256"), row.get("after_sha256")
        _need(previous is None or _SHA256.fullmatch(previous) is not None, f"{label}.before_sha256 is invalid")
        _need(current is None or _SHA256.fullmatch(current) is not None, f"{label}.after_sha256 is invalid")
        _need(previous != current, f"{label} does not describe a changed artifact")
        artifacts.append({"path": path, "before_sha256": previous, "after_sha256": current})
    contracts = _ids(changes["contracts"], "invalidation impact contracts") if isinstance(changes["contracts"], list) else (_need(False, "invalidation impact contracts must be a list") or [])
    produces = _ids(changes["produces"], "invalidation impact produces") if isinstance(changes["produces"], list) else (_need(False, "invalidation impact produces must be a list") or [])
    affected = value.get("affected")
    _need(isinstance(affected, Mapping) and set(affected) == {"local_cases", "system_cases", "documentation", "skills"},
          "invalidation impact affected has an unsupported schema")
    local = _ids(affected["local_cases"], "invalidation impact local_cases") if isinstance(affected["local_cases"], list) else (_need(False, "invalidation impact local_cases must be a list") or [])
    system = _ids(affected["system_cases"], "invalidation impact system_cases") if isinstance(affected["system_cases"], list) else (_need(False, "invalidation impact system_cases must be a list") or [])
    documentation = _paths(affected["documentation"], "invalidation impact documentation") if isinstance(affected["documentation"], list) else (_need(False, "invalidation impact documentation must be a list") or [])
    skills = _paths(affected["skills"], "invalidation impact skills") if isinstance(affected["skills"], list) else (_need(False, "invalidation impact skills must be a list") or [])
    known_local = set(_ids(known_local_cases, "known local cases"))
    known_docs = set(_paths(known_documentation, "known documentation"))
    known_skill_paths = set(_paths(known_skills, "known skills"))
    _need(set(local) <= known_local, "invalidation impact names an unknown local case")
    _need(set(documentation) <= known_docs, "invalidation impact names unknown documentation")
    _need(set(skills) <= known_skill_paths, "invalidation impact names an unknown skill")
    if catalog is not None:
        cases = _catalog(catalog)
        _need(set(system) <= set(cases), "invalidation impact names an unknown SYS case")
    elif system:
        _need(False, "invalidation impact SYS cases require the authoritative catalog")
    before = normalize_product_identity(before_identity) if before_identity is not None else None
    after = normalize_product_identity(after_identity) if after_identity is not None else None
    if before is not None and after is not None:
        expected: list[dict[str, Any]] = []
        for path in sorted(set(before["paths"]) | set(after["paths"])):
            old, new = before["paths"].get(path), after["paths"].get(path)
            if old != new:
                expected.append({"path": path, "before_sha256": old, "after_sha256": new})
        _need(artifacts == expected, "invalidation impact artifacts do not match actual observed path changes")
        if before["worktree_fingerprint"] != after["worktree_fingerprint"] and not expected:
            _need(
                certainty == "uncertain",
                "invalidation impact cannot claim known scope when the complete fingerprint changed without an observed content-path delta",
            )
    return {
        "version": VERSION,
        "certainty": certainty,
        "changes": {"artifacts": artifacts, "contracts": contracts, "produces": produces},
        "affected": {"local_cases": local, "system_cases": system, "documentation": documentation, "skills": skills},
    }


def _current_context(steps: Any, receipts: Any, product_identity: Any) -> dict[str, Any]:
    normalized_steps = _steps(steps)
    normalized_receipts = _receipts(receipts)
    return {
        "steps": normalized_steps,
        "receipts": normalized_receipts,
        "product_identity": normalize_product_identity(product_identity),
        "products": _complete_product_inventory(normalized_steps, normalized_receipts),
    }


def assess(
    snapshot: Any,
    catalog: Any,
    steps: Any,
    receipts: Any,
    *,
    product_identity: Any,
    impact: Any | None = None,
    known_local_cases: Iterable[str] = (),
    known_documentation: Iterable[str] = (),
    known_skills: Iterable[str] = (),
) -> dict[str, Any]:
    """Assess one original SYS proof against the actual current product.

    A declaration cannot make ``stale`` false.  It is carried in the decision
    for an auditable replan, while the caller reopens every known local/doc/skill
    obligation conservatively whenever the original proof is stale.
    """
    checked = validate_snapshot(snapshot)
    cases = _catalog(catalog)
    case_id = checked["case"]["id"]
    _need(cases.get(case_id) == checked["case"], "frozen system-test case changed or disappeared")
    current = _current_context(steps, receipts, product_identity)
    owner = current["steps"].get(checked["case"]["test_step"])
    _need(owner is not None and owner["activity"] in SYSTEM_ACTIVITIES,
          "frozen system-test owner changed or is no longer a system-test activity")
    current_owner_receipt = current["receipts"].get(checked["case"]["test_step"])
    _need(current_owner_receipt is not None, "frozen system-test owner receipt disappeared")
    _need(
        _proof_anchor(checked["case"], current_owner_receipt) == checked["proof"],
        "frozen system-test proof anchor changed",
    )
    before = {"products": checked["products"], "product_identity": checked["product_identity"]}
    after = {"products": current["products"], "product_identity": current["product_identity"]}
    changes = _product_changes(before, after)
    declared = None
    if impact is not None:
        declared = validate_impact_map(
            impact,
            known_local_cases=known_local_cases,
            catalog=catalog,
            known_documentation=known_documentation,
            known_skills=known_skills,
            before_identity=checked["product_identity"],
            after_identity=current["product_identity"],
        )
    declared_change = bool(declared and (
        declared["certainty"] == "uncertain"
        or declared["changes"]["artifacts"]
        or declared["changes"]["contracts"]
        or declared["changes"]["produces"]
    ))
    stale = _has_actual_change(changes) or declared_change
    local = _ids(known_local_cases, "known local cases") if stale else []
    documentation = _paths(known_documentation, "known documentation") if stale else []
    skills = _paths(known_skills, "known skills") if stale else []
    return {
        "version": VERSION,
        "case_id": case_id,
        "snapshot_sha256": checked["snapshot_sha256"],
        "current_product_identity_sha256": digest(current["product_identity"]),
        "current_product_content_identity_sha256": product_content_identity_digest(current["product_identity"]),
        "changes": changes,
        "stale": stale,
        "reasons": (
            (["actual product identity or completed receipt changed"] if _has_actual_change(changes) else [])
            + (["declared impact is uncertain or names changed obligations"] if declared_change else [])
        ),
        "affected": {
            "local_cases": local,
            "system_cases": [case_id] if stale else [],
            "documentation": documentation,
            "skills": skills,
        },
        "declared_impact": declared,
    }


def _snapshot_mapping(value: Any) -> dict[str, dict[str, Any]]:
    _need(isinstance(value, Mapping), "system-test proof snapshots must be a case-ID mapping")
    result: dict[str, dict[str, Any]] = {}
    for raw_id, raw in value.items():
        ident = _sys_id(raw_id, "system-test proof snapshot case ID")
        checked = validate_snapshot(raw)
        _need(checked["case"]["id"] == ident, "system-test proof snapshot mapping key differs from case")
        result[ident] = checked
    return result


def assess_all(
    snapshots: Any,
    catalog: Any,
    steps: Any,
    receipts: Any,
    *,
    product_identity: Any,
    impact: Any | None = None,
    known_local_cases: Iterable[str] = (),
    known_documentation: Iterable[str] = (),
    known_skills: Iterable[str] = (),
) -> dict[str, Any]:
    """Assess every required SYS proof before a release-capable quality gate."""
    checked_snapshots = _snapshot_mapping(snapshots)
    cases = _catalog(catalog)
    _need(set(cases) <= set(checked_snapshots), "every required SYS case needs an original merge-time proof snapshot")
    # Validate the impact declaration once using the earliest snapshot whose
    # path inventory is available.  Each per-case call below repeats it against
    # its own baseline, which is necessary when SYS cases were merged at
    # different product epochs.
    decisions: dict[str, dict[str, Any]] = {}
    for case_id in sorted(cases):
        decisions[case_id] = assess(
            checked_snapshots[case_id], catalog, steps, receipts,
            product_identity=product_identity, impact=impact,
            known_local_cases=known_local_cases,
            known_documentation=known_documentation,
            known_skills=known_skills,
        )
    stale = sorted(case_id for case_id, decision in decisions.items() if decision["stale"])
    current = normalize_product_identity(product_identity)
    return {
        "version": VERSION,
        "current_product_identity_sha256": digest(current),
        "current_product_content_identity_sha256": product_content_identity_digest(current),
        "stale_case_ids": stale,
        "fresh_case_ids": sorted(set(cases) - set(stale)),
        "release": "requires-revalidation" if stale else "ready",
        "affected": {
            "local_cases": _ids(known_local_cases, "known local cases") if stale else [],
            "system_cases": stale,
            "documentation": _paths(known_documentation, "known documentation") if stale else [],
            "skills": _paths(known_skills, "known skills") if stale else [],
        },
        "decisions": decisions,
    }


def validate_revalidation(
    value: Any,
    decision: Any,
    snapshots: Any,
    catalog: Any,
) -> dict[str, Any]:
    """Validate new SYS proof mappings that discharge stale frozen cases.

    The replacement case must be a distinct current catalog case with the same
    phase, requirement, and expected outcome.  Its own original merge-time
    snapshot must bind the exact current product identity from ``decision``.
    Thus an old green SYS result cannot be relabeled as fresh, and a replacement
    becomes stale again automatically if another product change lands later.
    """
    _need(isinstance(decision, Mapping), "system-test invalidation decision must be an object")
    stale = decision.get("stale_case_ids")
    current_digest = decision.get("current_product_content_identity_sha256")
    _need(isinstance(stale, list) and all(isinstance(item, str) for item in stale),
          "system-test invalidation decision stale cases are invalid")
    _sha(current_digest, "system-test invalidation decision current product content identity")
    _need(isinstance(value, Mapping), "system-test revalidation must be an object")
    required = {"version", "product_content_identity_sha256", "replacements"}
    _need(set(value) == required and value.get("version") == VERSION,
          "system-test revalidation has an unsupported schema")
    _need(value.get("product_content_identity_sha256") == current_digest,
          "system-test revalidation binds another product content identity")
    rows = value.get("replacements")
    _need(isinstance(rows, list), "system-test revalidation replacements must be a list")
    cases = _catalog(catalog)
    proof_map = _snapshot_mapping(snapshots)
    replacements: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        label = f"system-test revalidation replacement {index}"
        _need(isinstance(row, Mapping) and set(row) == {"stale_case_id", "replacement_case_id"},
              f"{label} has an unsupported schema")
        old = _sys_id(row.get("stale_case_id"), f"{label}.stale_case_id")
        new = _sys_id(row.get("replacement_case_id"), f"{label}.replacement_case_id")
        _need(old in stale and old not in seen, f"{label} does not map one stale case")
        _need(new != old and new not in stale and new in cases and new in proof_map,
              f"{label} must name a distinct captured replacement SYS case")
        original = proof_map.get(old)
        _need(original is not None, f"{label} stale SYS proof snapshot is missing")
        old_case, new_case = original["case"], cases[new]
        _need(
            old_case["phase"] == new_case["phase"]
            and old_case["requirement"] == new_case["requirement"]
            and old_case["expected_outcome"] == new_case["expected_outcome"]
            and old_case["environment"] == new_case["environment"]
            and old_case["deployment_step"] == new_case["deployment_step"],
            f"{label} replacement does not preserve the frozen SYS requirement, outcome, environment, and target",
        )
        replacement = proof_map[new]
        _need(product_content_identity_digest(replacement["product_identity"]) == current_digest,
              f"{label} replacement proof is not fresh for the current product")
        seen.add(old)
        replacements.append({"stale_case_id": old, "replacement_case_id": new})
    _need(seen == set(stale), "system-test revalidation must map every stale SYS case exactly once")
    return {
        "version": VERSION,
        "product_content_identity_sha256": current_digest,
        "replacements": sorted(replacements, key=lambda row: row["stale_case_id"]),
    }


__all__ = [
    "InvalidationError",
    "PUBLISH_ACTIVITY",
    "SYSTEM_ACTIVITIES",
    "VERSION",
    "assess",
    "assess_all",
    "capture_system_proof",
    "digest",
    "normalize_product_identity",
    "product_identity_digest",
    "product_content_identity_digest",
    "validate_impact_map",
    "validate_revalidation",
    "validate_snapshot",
]
