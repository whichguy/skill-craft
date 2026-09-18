#!/usr/bin/env python3
"""Fail-closed receipt validation for ShipLoop end-to-end trials.

This checker validates a coordinator-provided receipt after the one-shot runner
has exited.  It never launches a model, reruns a trial, or feeds a verdict back
into a live prompt.  Invoke it as a separate, terminal observer and retain its
single JSON object from stdout with the native runner stdout/stderr and pinned
artifacts, for example::

    python3 test/experiments/shiploop_e2e/grading.py \\
      --receipt "$trial/verification-receipt.json" \\
      --trial-id ttt-highlight-01 \\
      --candidate-digest "$candidate_digest" \\
      --required-check local-tests \\
      --required-check browser-smoke \\
      --evidence-root "$trial/evidence" > "$trial/receipt-validation.json"

For an incremental trial, also pass ``--baseline-digest``.  The validator then
requires that the receipt bind that baseline exactly and contain a passed,
artifact-backed ``incremental_review``. Passing and failing declarations both
need pinned local artifacts. A passed receipt says only that the named checker
declared passing statuses with pinned local artifacts. It does not establish
application semantics, hosted delivery, or that a Git ancestry relationship
proves the change was incremental.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


RECEIPT_SCHEMA = "shiploop-e2e-receipt/1"
VALIDATION_SCHEMA = "shiploop-e2e-receipt-validation/1"
CHECK_STATUSES = frozenset(("pass", "fail", "blocked", "unverified"))
INCREMENTAL_STATUSES = frozenset(("pass", "fail", "unverified"))


def _issue(code: str, message: str, **context: Any) -> dict[str, Any]:
    """Return a stable, machine-readable validation diagnostic."""
    return {"code": code, "message": message, **context}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validated_required_checks(value: Any) -> tuple[list[str], list[dict[str, Any]]]:
    """Normalize the caller-owned required check IDs without accepting aliases."""
    errors: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return [], [_issue("invalid_required_checks", "required_checks must be a list of non-empty strings")]

    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            errors.append(_issue("invalid_required_check", "required check IDs must be non-empty strings", index=index))
            continue
        if item in seen:
            errors.append(_issue("duplicate_required_check", "required check IDs must be unique", check_id=item))
            continue
        seen.add(item)
        result.append(item)
    return result, errors


def _validated_evidence_root(value: Path) -> tuple[Path | None, list[dict[str, Any]]]:
    """Resolve an existing, physical directory used as the artifact boundary."""
    try:
        root = Path(value)
        if root.is_symlink():
            return None, [_issue("invalid_evidence_root", "evidence_root must not be a symbolic link")]
        if not root.is_dir():
            return None, [_issue("invalid_evidence_root", "evidence_root must be an existing directory")]
        return root.resolve(strict=True), []
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return None, [_issue("invalid_evidence_root", "evidence_root could not be resolved", error=type(exc).__name__)]


def _artifact_result(entry: Any, *, root: Path | None, check_id: str | None, index: int) -> dict[str, Any]:
    """Validate one pinned artifact without following symlinks outside ``root``."""
    errors: list[dict[str, Any]] = []
    path_value: str | None = None
    declared_digest: str | None = None
    context = {"check_id": check_id, "evidence_index": index}
    if not isinstance(entry, dict):
        return {
            "path": None,
            "sha256": None,
            "valid": False,
            "errors": [_issue("invalid_evidence", "evidence entries must be objects", **context)],
        }

    raw_path = entry.get("path")
    raw_digest = entry.get("sha256")
    if not isinstance(raw_path, str) or not raw_path:
        errors.append(_issue("invalid_evidence_path", "evidence path must be a non-empty relative string", **context))
    else:
        path_value = raw_path
    if not isinstance(raw_digest, str) or len(raw_digest) != 64 or any(char not in "0123456789abcdef" for char in raw_digest.lower()):
        errors.append(_issue("invalid_evidence_digest", "evidence sha256 must be a 64-character hexadecimal digest", **context))
    else:
        declared_digest = raw_digest

    if root is None:
        errors.append(_issue("invalid_evidence_root", "artifacts cannot be checked without a safe evidence_root", **context))
    elif path_value is not None:
        relative = Path(path_value)
        if relative.is_absolute() or not relative.parts or any(part == ".." for part in relative.parts):
            errors.append(_issue("unsafe_evidence_path", "evidence path must stay beneath evidence_root", path=path_value, **context))
        else:
            candidate = root / relative
            try:
                current = root
                for part in relative.parts:
                    current = current / part
                    if current.is_symlink():
                        errors.append(_issue("evidence_symlink", "evidence paths may not traverse symbolic links", path=path_value, **context))
                        break
                if not errors:
                    if not candidate.exists():
                        errors.append(_issue("missing_evidence", "evidence file does not exist", path=path_value, **context))
                    elif candidate.is_symlink() or not candidate.is_file():
                        errors.append(_issue("invalid_evidence_file", "evidence must be an ordinary file", path=path_value, **context))
                    else:
                        resolved = candidate.resolve(strict=True)
                        try:
                            resolved.relative_to(root)
                        except ValueError:
                            errors.append(_issue("unsafe_evidence_path", "evidence resolved outside evidence_root", path=path_value, **context))
                        if not errors and declared_digest is not None:
                            actual = _sha256(candidate)
                            if actual != declared_digest.lower():
                                errors.append(_issue("evidence_digest_mismatch", "evidence sha256 does not match file bytes", path=path_value, **context))
            except (OSError, RuntimeError, ValueError) as exc:
                errors.append(_issue("invalid_evidence_file", "evidence file could not be inspected", path=path_value, error=type(exc).__name__, **context))

    return {"path": path_value, "sha256": declared_digest, "valid": not errors, "errors": errors}


def _evidence_results(value: Any, *, root: Path | None, check_id: str | None, require_evidence_for: str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate an evidence list and require pins for declared outcomes."""
    errors: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return [], [_issue("invalid_evidence", "evidence must be a list", check_id=check_id)]
    if require_evidence_for == "pass" and not value:
        errors.append(_issue("missing_pass_evidence", "a passing status requires at least one pinned artifact", check_id=check_id))
    elif require_evidence_for == "fail" and not value:
        errors.append(_issue("missing_failure_evidence", "a failing status requires at least one pinned artifact", check_id=check_id))
    rows = [_artifact_result(entry, root=root, check_id=check_id, index=index) for index, entry in enumerate(value)]
    for row in rows:
        errors.extend(row["errors"])
    return rows, errors


def _binding_result(receipt: dict[str, Any], *, trial_id: str, candidate_digest: str, baseline_digest: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Require an exact receipt-to-trial binding, including an explicit null baseline."""
    expected = {
        "trial_id": trial_id,
        "candidate_digest": candidate_digest,
        "baseline_digest": baseline_digest,
    }
    received = {name: receipt.get(name) for name in expected}
    errors: list[dict[str, Any]] = []
    for name, expected_value in expected.items():
        if name not in receipt:
            errors.append(_issue("missing_binding", "receipt is missing a required binding", field=name))
        elif receipt[name] != expected_value:
            errors.append(_issue("binding_mismatch", "receipt binding does not match the validated trial", field=name))
    return {"expected": expected, "received": received, "valid": not errors}, errors


def _check_row(entry: Any, *, index: int, root: Path | None) -> dict[str, Any]:
    """Normalize a declared checker result; callers decide whether its ID is required."""
    if not isinstance(entry, dict):
        error = _issue("invalid_check", "check entries must be objects", index=index)
        return {
            "index": index,
            "id": None,
            "status": None,
            "status_valid": False,
            "evidence": [],
            "evidence_valid": False,
            "valid": False,
            "errors": [error],
        }

    check_id = entry.get("id")
    errors: list[dict[str, Any]] = []
    if not isinstance(check_id, str) or not check_id:
        errors.append(_issue("invalid_check_id", "check IDs must be non-empty strings", index=index))
        check_id = None

    status = entry.get("status")
    status_valid = isinstance(status, str) and status in CHECK_STATUSES
    if not status_valid:
        errors.append(_issue("invalid_check_status", "check status must be pass, fail, blocked, or unverified", check_id=check_id, index=index))

    evidence, evidence_errors = _evidence_results(
        entry.get("evidence"),
        root=root,
        check_id=check_id,
        require_evidence_for=status if status in ("pass", "fail") else None,
    )
    errors.extend(evidence_errors)
    return {
        "index": index,
        "id": check_id,
        "status": status if isinstance(status, str) else None,
        "status_valid": status_valid,
        "evidence": evidence,
        "evidence_valid": not evidence_errors,
        "valid": status_valid and not evidence_errors and check_id is not None,
        "errors": errors,
    }


def _incremental_row(value: Any, *, root: Path | None) -> dict[str, Any]:
    """Normalize the explicitly external incremental-review declaration."""
    if not isinstance(value, dict):
        error = _issue("invalid_incremental_review", "incremental_review must be an object")
        return {"status": None, "status_valid": False, "evidence": [], "evidence_valid": False, "valid": False, "errors": [error]}

    status = value.get("status")
    status_valid = isinstance(status, str) and status in INCREMENTAL_STATUSES
    errors: list[dict[str, Any]] = []
    if not status_valid:
        errors.append(_issue("invalid_incremental_status", "incremental review status must be pass, fail, or unverified"))
    evidence, evidence_errors = _evidence_results(
        value.get("evidence"),
        root=root,
        check_id="incremental_review",
        require_evidence_for=status if status in ("pass", "fail") else None,
    )
    errors.extend(evidence_errors)
    return {
        "status": status if isinstance(status, str) else None,
        "status_valid": status_valid,
        "evidence": evidence,
        "evidence_valid": not evidence_errors,
        "valid": status_valid and not evidence_errors,
        "errors": errors,
    }


def validate_receipt(
    receipt: dict,
    *,
    trial_id: str,
    candidate_digest: str,
    required_checks: list[str],
    evidence_root: Path,
    baseline_digest: str | None = None,
) -> dict[str, Any]:
    """Validate one external receipt without inferring behavior from its prose.

    ``product_status == "passed"`` requires every required checker to occur
    exactly once with status ``pass`` and valid, non-empty pinned evidence.  A
    declared required failure is ``failed`` only when the receipt itself is
    valid and carries non-empty pinned evidence. Missing, blocked, and
    unverified declarations stay ``unverified``.
    Invalid bindings, malformed schema, duplicates, and bad artifacts are
    ``error``; failed rows remain in the diagnostics but cannot be attributed
    to the candidate.
    """
    errors: list[dict[str, Any]] = []
    unverified_reasons: list[dict[str, Any]] = []
    if not isinstance(receipt, dict):
        receipt = {}
        errors.append(_issue("invalid_receipt", "receipt must be an object"))

    normalized_required, required_errors = _validated_required_checks(required_checks)
    errors.extend(required_errors)
    if not isinstance(trial_id, str) or not trial_id:
        errors.append(_issue("invalid_trial_id", "trial_id must be a non-empty string"))
    if not isinstance(candidate_digest, str) or not candidate_digest:
        errors.append(_issue("invalid_candidate_digest", "candidate_digest must be a non-empty string"))
    if baseline_digest is not None and (not isinstance(baseline_digest, str) or not baseline_digest):
        errors.append(_issue("invalid_baseline_digest", "baseline_digest must be null or a non-empty string"))

    if receipt.get("schema") != RECEIPT_SCHEMA:
        errors.append(_issue("unsupported_receipt_schema", "receipt schema must be shiploop-e2e-receipt/1"))
    bindings, binding_errors = _binding_result(
        receipt,
        trial_id=trial_id,
        candidate_digest=candidate_digest,
        baseline_digest=baseline_digest,
    )
    errors.extend(binding_errors)
    root, root_errors = _validated_evidence_root(evidence_root)
    errors.extend(root_errors)

    raw_checks = receipt.get("checks")
    if not isinstance(raw_checks, list):
        errors.append(_issue("invalid_checks", "checks must be a list"))
        raw_checks = []
    rows = [_check_row(entry, index=index, root=root) for index, entry in enumerate(raw_checks)]
    for row in rows:
        errors.extend(row["errors"])

    by_id: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row["id"] is not None:
            by_id.setdefault(row["id"], []).append(row)
    for check_id, occurrences in by_id.items():
        if len(occurrences) > 1:
            error = _issue("duplicate_check", "each check ID may occur only once", check_id=check_id)
            errors.append(error)
            for row in occurrences:
                row["errors"].append(error)
                row["valid"] = False

    required_results: dict[str, dict[str, Any]] = {}
    for check_id in normalized_required:
        occurrences = by_id.get(check_id, [])
        if not occurrences:
            required_results[check_id] = {
                "present": False,
                "status": "unverified",
                "evidence_valid": False,
                "valid": False,
            }
            unverified_reasons.append(_issue("missing_required_check", "a required checker has no declaration", check_id=check_id))
            continue
        row = occurrences[0]
        required_results[check_id] = {
            "present": True,
            "status": row["status"],
            "evidence_valid": row["evidence_valid"],
            "valid": row["valid"],
        }
        if row["status"] in ("blocked", "unverified"):
            unverified_reasons.append(_issue("required_check_not_passed", "a required checker is not passing", check_id=check_id, status=row["status"]))

    unknown_checks = [
        {"id": row["id"], "index": row["index"], "status": row["status"], "valid": row["valid"]}
        for row in rows
        if row["id"] is not None and row["id"] not in normalized_required
    ]

    incremental = _incremental_row(receipt.get("incremental_review"), root=root)
    errors.extend(incremental["errors"])
    incremental_required = baseline_digest is not None
    if incremental_required and incremental["status"] in ("unverified", None):
        unverified_reasons.append(_issue("incremental_review_not_passed", "incremental trials require a passed independent review", status=incremental["status"]))

    if not incremental_required:
        declared_incremental_status = "not-applicable"
    elif incremental["status"] == "fail":
        declared_incremental_status = "failed"
    elif incremental["status"] == "pass" and incremental["valid"]:
        declared_incremental_status = "passed"
    else:
        declared_incremental_status = "unverified"

    declared_failure = any(result["status"] == "fail" for result in required_results.values())
    if declared_incremental_status == "failed":
        declared_failure = True
    all_required_pass = not errors and bool(normalized_required) and all(
        result["present"] and result["status"] == "pass" and result["valid"]
        for result in required_results.values()
    )
    incremental_status = (
        "unverified" if errors and incremental_required else declared_incremental_status
    )
    incremental_pass = incremental_status in ("not-applicable", "passed")

    if errors:
        product_status = "error"
    elif declared_failure:
        product_status = "failed"
    elif all_required_pass and incremental_pass:
        product_status = "passed"
    else:
        product_status = "unverified"

    return {
        "schema": VALIDATION_SCHEMA,
        "product_status": product_status,
        "receipt_valid": not errors,
        "bindings": bindings,
        "required_checks": required_results,
        "checks": rows,
        "unknown_checks": unknown_checks,
        "incremental_required": incremental_required,
        "incremental_status": incremental_status,
        "incremental_review": incremental,
        "all_required_checks_pass": all_required_pass,
        "errors": errors,
        "unverified_reasons": unverified_reasons,
        "limitations": [
            "This validates checker declarations and artifact pins, not application semantics.",
            "A passed incremental review does not make structural ancestry proof of incremental behavior.",
            "Hosted delivery requires separate activation and consumer-path evidence.",
        ],
    }


def write_template(
    path: Path,
    *,
    trial_id: str,
    candidate_digest: str,
    required_checks: list[str],
    baseline_digest: str | None = None,
) -> dict[str, Any]:
    """Write a version-1, all-unverified receipt skeleton and return its value."""
    checks, errors = _validated_required_checks(required_checks)
    if errors:
        raise ValueError("required_checks must contain unique non-empty strings")
    if not isinstance(trial_id, str) or not trial_id:
        raise ValueError("trial_id must be a non-empty string")
    if not isinstance(candidate_digest, str) or not candidate_digest:
        raise ValueError("candidate_digest must be a non-empty string")
    if baseline_digest is not None and (not isinstance(baseline_digest, str) or not baseline_digest):
        raise ValueError("baseline_digest must be null or a non-empty string")
    template = {
        "schema": RECEIPT_SCHEMA,
        "trial_id": trial_id,
        "candidate_digest": candidate_digest,
        "baseline_digest": baseline_digest,
        "checks": [{"id": check_id, "status": "unverified", "evidence": []} for check_id in checks],
        "incremental_review": {"status": "unverified", "evidence": []},
    }
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(template, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return template


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a ShipLoop E2E external verification receipt.")
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--candidate-digest", required=True)
    parser.add_argument("--baseline-digest")
    parser.add_argument("--required-check", action="append", dest="required_checks", default=[])
    parser.add_argument("--evidence-root", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Emit one validation JSON object to stdout; zero means ``product_status`` passed."""
    args = _parse_args(argv)
    try:
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        receipt = {}
        result = validate_receipt(
            receipt,
            trial_id=args.trial_id,
            candidate_digest=args.candidate_digest,
            required_checks=args.required_checks,
            evidence_root=args.evidence_root,
            baseline_digest=args.baseline_digest,
        )
        result["errors"].insert(0, _issue("receipt_read_error", "receipt file could not be read as JSON", error=type(exc).__name__))
        result["receipt_valid"] = False
        result["product_status"] = "error"
    else:
        result = validate_receipt(
            receipt,
            trial_id=args.trial_id,
            candidate_digest=args.candidate_digest,
            required_checks=args.required_checks,
            evidence_root=args.evidence_root,
            baseline_digest=args.baseline_digest,
        )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["product_status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
