"""Durable planning-convergence records for ShipLoop.

This module deliberately owns no lock and performs no Git operations.  The
protocol holds the existing ShipLoop Markdown transaction lock, supplies Git
facts, and stores the returned records atomically.  Keeping this narrowly
focused makes the planning loops use the same Markdown authority as the rest
of ShipLoop without introducing a second session engine.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

import shiploop_until as until


PROTOCOL_VERSION = 2
KINDS = ("research", "behavior", "spec")
RUBRICS = {
    "research": (
        "prompt_coverage",
        "environment_conditions",
        "source_quality",
        "contradictions",
        "best_practices",
        "access_readiness",
        "invocation_contracts",
        "test_deploy_feasibility",
        "remaining_unknowns",
    ),
    "behavior": (
        "requirements",
        "states",
        "transitions",
        "edge_conditions",
        "sequences",
        "test_mapping",
        "ambiguities",
    ),
    "spec": (
        "requirements",
        "states",
        "transitions",
        "edge_conditions",
        "sequences",
        "test_mapping",
        "ambiguities",
        "clarity",
        "consistency",
        "feasibility",
    ),
}
_FINDING_ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9._:-]{0,159}\Z")
_ITERATION_ID_RE = re.compile(r"[A-Za-z0-9_-]+\Z")


class PlanningError(ValueError):
    """A durable planning record or result violates the planning contract."""


def need(ok: bool, message: str) -> None:
    if not ok:
        raise PlanningError(message)


def _text(value: Any, label: str) -> str:
    need(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty")
    return value.strip()


def _kind(kind: str) -> str:
    need(kind in KINDS, "unknown planning kind")
    return kind


def _origin(value: Any) -> dict[str, str]:
    """Normalize the accepted result that created this planning candidate."""
    need(isinstance(value, Mapping), "planning origin must be an object")
    need(
        set(value) == {"action_id", "result_sha256", "candidate_sha256"},
        "planning origin keys do not match the contract",
    )
    action_id = value.get("action_id")
    result_sha256 = value.get("result_sha256")
    candidate_sha256 = value.get("candidate_sha256")
    need(
        isinstance(action_id, str) and _ITERATION_ID_RE.fullmatch(action_id),
        "planning origin action ID is invalid",
    )
    for label, digest_value in (
        ("planning origin result digest", result_sha256),
        ("planning origin candidate digest", candidate_sha256),
    ):
        need(
            isinstance(digest_value, str)
            and re.fullmatch(r"[0-9a-f]{64}", digest_value),
            label + " is invalid",
        )
    return {
        "action_id": action_id,
        "result_sha256": result_sha256,
        "candidate_sha256": candidate_sha256,
    }


def _first_assessment(value: Any) -> dict[str, Any]:
    need(isinstance(value, Mapping), "planning first assessment must be an object")
    need(
        set(value) == {"action_id", "result_sha256", "candidate_sha256", "epoch"},
        "planning first assessment keys do not match the contract",
    )
    normalized = _origin(
        {
            key: value.get(key)
            for key in ("action_id", "result_sha256", "candidate_sha256")
        }
    )
    epoch = value.get("epoch")
    need(type(epoch) is int and epoch >= 1, "planning first assessment epoch is invalid")
    return dict(normalized, epoch=epoch)


def origin(receipt: Mapping[str, Any]) -> dict[str, str] | None:
    """Read optional provenance without manufacturing it for legacy receipts."""
    if "origin" not in receipt:
        return None
    return _origin(receipt["origin"])


def first_assessment(receipt: Mapping[str, Any]) -> dict[str, Any] | None:
    """Read the one first-review locator stored in the existing receipt."""
    if "first_assessment" not in receipt:
        return None
    return _first_assessment(receipt["first_assessment"])


def is_current(state: Mapping[str, Any]) -> bool:
    return state.get("planning_protocol_version") == PROTOCOL_VERSION


def candidate_names(kind: str) -> tuple[str, ...]:
    """Current candidate pages.  The spec pair is never promoted piecemeal."""
    _kind(kind)
    if kind == "research":
        return ("research.md", "research-evidence.md")
    return ("behavior.md",) if kind == "behavior" else (
        "spec-draft.md",
        "lifecycle-draft.md",
    )


def frozen_names(kind: str) -> tuple[str, ...]:
    _kind(kind)
    if kind == "research":
        return candidate_names(kind)
    return ("behavior.md",) if kind == "behavior" else ("spec.md", "lifecycle.md")


def receipt_name(kind: str) -> str:
    _kind(kind)
    return f"planning/{kind}.md"


def iteration_name(kind: str, iteration_id: str) -> str:
    _kind(kind)
    need(
        isinstance(iteration_id, str) and _ITERATION_ID_RE.fullmatch(iteration_id),
        "unsafe planning iteration ID",
    )
    return f"planning/{kind}-iterations/{iteration_id}.md"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def candidate_identity(root: Path, kind: str) -> dict[str, Any]:
    """Return a digest over exactly the candidate bytes, refusing symlinks."""
    texts: dict[str, str] = {}
    for name in candidate_names(kind):
        path = root / name
        need(path.is_file() and not path.is_symlink(), f"missing planning candidate {name}")
        try:
            texts[name] = path.read_bytes().decode("utf-8")
        except UnicodeError as exc:
            raise PlanningError(f"planning candidate {name} is not UTF-8 Markdown") from exc
    return candidate_identity_from_texts(kind, texts)


def candidate_identity_from_texts(kind: str, texts: Mapping[str, Any]) -> dict[str, Any]:
    """Return candidate identity for a transaction that has not landed yet."""
    _kind(kind)
    need(
        set(texts) == set(candidate_names(kind)),
        "planning candidate replacement has the wrong component names",
    )
    components: dict[str, str] = {}
    for name in candidate_names(kind):
        body = texts[name]
        need(isinstance(body, str) and body.strip(), f"planning candidate {name} is empty")
        components[name] = _sha(body.encode("utf-8"))
    return {
        "candidate_sha256": _sha(_canonical(components)),
        "candidate_components": components,
    }


def _normal_finding(raw: Any) -> dict[str, str]:
    need(isinstance(raw, Mapping), "planning finding must be an object")
    finding_id = raw.get("id")
    need(
        isinstance(finding_id, str) and _FINDING_ID_RE.fullmatch(finding_id),
        "planning finding id must be a stable safe identifier",
    )
    severity = raw.get("severity")
    need(severity in ("material", "trivial"), "planning finding severity must be material or trivial")
    summary = _text(raw.get("summary"), f"planning finding {finding_id} summary")
    status = raw.get("status", "open")
    need(status in ("open", "resolved"), "planning finding status must be open or resolved")
    normalized = {
        "id": finding_id,
        "severity": severity,
        "summary": summary,
        "status": status,
    }
    for key in ("resolution_evidence", "resolved_iteration"):
        if key in raw:
            normalized[key] = _text(raw[key], f"planning finding {finding_id} {key}")
    if status == "resolved":
        need(
            "resolution_evidence" in normalized and "resolved_iteration" in normalized,
            f"resolved planning finding {finding_id} lacks closure provenance",
        )
    return normalized


def normal_findings(value: Any) -> list[dict[str, str]]:
    need(isinstance(value, list), "planning findings must be a list")
    findings = [_normal_finding(row) for row in value]
    ids = [row["id"] for row in findings]
    need(len(set(ids)) == len(ids), "planning findings must not duplicate IDs")
    return findings


def ledger_sha256(findings: Any) -> str:
    normalized = normal_findings(findings)
    # The stored order is for humans; the identity is stable under a harmless
    # reordering and cannot be changed by an out-of-band content edit.
    normalized.sort(key=lambda row: row["id"])
    return _sha(_canonical(normalized))


def identity(receipt: Mapping[str, Any]) -> str:
    candidate = _text(receipt.get("candidate_sha256"), "planning candidate digest")
    ledger = _text(receipt.get("ledger_sha256"), "planning ledger digest")
    fields: dict[str, Any] = {
        "candidate_sha256": candidate,
        "ledger_sha256": ledger,
    }
    if (value := origin(receipt)) is not None:
        fields["origin"] = value
    if (value := first_assessment(receipt)) is not None:
        fields["first_assessment"] = value
    return _sha(_canonical(fields))


def _assert_receipt_shape(receipt: Any, kind: str) -> dict[str, Any]:
    need(isinstance(receipt, dict), "planning receipt must be an object")
    need(receipt.get("version") == PROTOCOL_VERSION, "unsupported planning receipt")
    need(receipt.get("kind") == kind, "planning receipt kind mismatch")
    candidate = receipt.get("candidate_components")
    need(isinstance(candidate, dict), "planning receipt candidate components are missing")
    need(set(candidate) == set(candidate_names(kind)), "planning receipt candidate component names mismatch")
    need(
        all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) for value in candidate.values()),
        "planning receipt candidate component digest is invalid",
    )
    need(
        isinstance(receipt.get("candidate_sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", receipt["candidate_sha256"]),
        "planning receipt candidate digest is invalid",
    )
    need(type(receipt.get("epoch")) is int and receipt["epoch"] >= 1, "planning receipt epoch must be positive")
    initial = origin(receipt)
    first = first_assessment(receipt)
    if first is not None:
        need(initial is not None, "planning first assessment requires origin provenance")
        need(
            first["candidate_sha256"] == initial["candidate_sha256"],
            "planning first assessment does not bind the origin candidate",
        )
        need(
            first["epoch"] <= receipt.get("epoch", 0),
            "planning first assessment cannot be from a future epoch",
        )
    findings = normal_findings(receipt.get("findings"))
    need(
        receipt.get("ledger_sha256") == ledger_sha256(findings),
        "planning ledger digest mismatch",
    )
    need(
        receipt.get("identity_sha256") == identity(receipt),
        "planning candidate/ledger identity mismatch",
    )
    need(
        isinstance(receipt.get("iteration"), int) and receipt["iteration"] >= 1,
        "planning receipt iteration must be positive",
    )
    need(
        isinstance(receipt.get("streak"), int) and receipt["streak"] >= 0,
        "planning receipt streak must be nonnegative",
    )
    current = receipt.get("current_iteration")
    need(isinstance(current, dict), "planning receipt current iteration is missing")
    _text(current.get("id"), "planning iteration id")
    _text(current.get("git_baseline"), "planning iteration Git baseline")
    _text(current.get("product_fingerprint"), "planning iteration product fingerprint")
    need(
        current.get("identity_sha256") == receipt.get("identity_sha256"),
        "planning current iteration identity is stale",
    )
    return receipt


def assert_receipt(root: Path, kind: str, receipt: Any) -> dict[str, Any]:
    """Validate schema and require the on-disk candidate to match the receipt."""
    receipt = _assert_receipt_shape(receipt, kind)
    actual = candidate_identity(root, kind)
    need(
        actual["candidate_sha256"] == receipt["candidate_sha256"]
        and actual["candidate_components"] == receipt["candidate_components"],
        "planning candidate changed outside the supported apply path",
    )
    return receipt


def set_identity(receipt: dict[str, Any], candidate: Mapping[str, Any]) -> None:
    """Update a receipt in the same transaction as a supported replacement."""
    need(
        isinstance(candidate.get("candidate_sha256"), str)
        and isinstance(candidate.get("candidate_components"), Mapping),
        "invalid planning candidate identity",
    )
    receipt["candidate_sha256"] = candidate["candidate_sha256"]
    receipt["candidate_components"] = dict(candidate["candidate_components"])
    receipt["ledger_sha256"] = ledger_sha256(receipt["findings"])
    receipt["identity_sha256"] = identity(receipt)
    _sync_current_identity(receipt)


def record_first_assessment(receipt: dict[str, Any], value: Any) -> dict[str, Any]:
    """Bind the first accepted review result without duplicating its body."""
    normalized = _first_assessment(value)
    initial = origin(receipt)
    need(initial is not None, "planning first assessment requires origin provenance")
    need(
        normalized["candidate_sha256"] == receipt.get("candidate_sha256"),
        "planning first assessment is not bound to the reviewed candidate",
    )
    need(
        normalized["candidate_sha256"] == initial["candidate_sha256"],
        "planning first assessment is not bound to the origin candidate",
    )
    need(
        normalized["epoch"] == receipt.get("epoch"),
        "planning first assessment is not from the current epoch",
    )
    existing = first_assessment(receipt)
    if existing is not None:
        need(existing == normalized, "planning first assessment cannot be replaced")
        return existing
    receipt["first_assessment"] = normalized
    receipt["identity_sha256"] = identity(receipt)
    _sync_current_identity(receipt)
    return normalized


def _sync_current_identity(receipt: Mapping[str, Any]) -> None:
    current = receipt.get("current_iteration")
    if not isinstance(current, dict):
        return
    current["candidate_sha256"] = receipt["candidate_sha256"]
    current["ledger_sha256"] = receipt["ledger_sha256"]
    current["identity_sha256"] = receipt["identity_sha256"]


def make_iteration(
    *,
    run_id: str,
    kind: str,
    epoch: int,
    number: int,
    git_baseline: str,
    product_fingerprint: str,
    candidate_sha256: str,
    ledger_sha256_value: str,
) -> dict[str, Any]:
    _kind(kind)
    need(isinstance(number, int) and number >= 1, "planning iteration must be positive")
    need(isinstance(epoch, int) and epoch >= 1, "planning epoch must be positive")
    for label, value in (
        ("run ID", run_id),
        ("Git baseline", git_baseline),
        ("product fingerprint", product_fingerprint),
        ("candidate digest", candidate_sha256),
        ("ledger digest", ledger_sha256_value),
    ):
        _text(value, f"planning {label}")
    return {
        "id": f"{run_id}-{kind}-E{epoch}-I{number}",
        "git_baseline": git_baseline,
        "product_fingerprint": product_fingerprint,
        "candidate_sha256": candidate_sha256,
        "ledger_sha256": ledger_sha256_value,
        "identity_sha256": _sha(
            _canonical(
                {
                    "candidate_sha256": candidate_sha256,
                    "ledger_sha256": ledger_sha256_value,
                }
            )
        ),
    }


def new_receipt(
    *,
    root: Path,
    state: Mapping[str, Any],
    kind: str,
    git_baseline: str,
    product_fingerprint: str,
    candidate: Mapping[str, Any] | None = None,
    origin: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = candidate_identity(root, kind) if candidate is None else dict(candidate)
    findings: list[dict[str, str]] = []
    ledger = ledger_sha256(findings)
    receipt: dict[str, Any] = {
        "version": PROTOCOL_VERSION,
        "kind": kind,
        **candidate,
        "findings": findings,
        "ledger_sha256": ledger,
        "epoch": int(state.get("planning_epoch", 1)),
        "iteration": 1,
        "streak": 0,
        "completed_iterations": [],
    }
    if origin is not None:
        normalized_origin = _origin(origin)
        need(
            normalized_origin["candidate_sha256"] == candidate["candidate_sha256"],
            "planning origin does not match the initial candidate",
        )
        receipt["origin"] = normalized_origin
    receipt["identity_sha256"] = identity(receipt)
    receipt["current_iteration"] = make_iteration(
        run_id=_text(state.get("run_id"), "run ID"),
        kind=kind,
        epoch=receipt["epoch"],
        number=1,
        git_baseline=git_baseline,
        product_fingerprint=product_fingerprint,
        candidate_sha256=receipt["candidate_sha256"],
        ledger_sha256_value=ledger,
    )
    _sync_current_identity(receipt)
    return receipt


def start_next_iteration(
    receipt: dict[str, Any],
    *,
    run_id: str,
    git_baseline: str,
    product_fingerprint: str,
) -> None:
    kind = _kind(receipt.get("kind"))
    next_number = int(receipt["iteration"]) + 1
    receipt["iteration"] = next_number
    receipt["current_iteration"] = make_iteration(
        run_id=run_id,
        kind=kind,
        epoch=receipt["epoch"],
        number=next_number,
        git_baseline=git_baseline,
        product_fingerprint=product_fingerprint,
        candidate_sha256=receipt["candidate_sha256"],
        ledger_sha256_value=receipt["ledger_sha256"],
    )
    _sync_current_identity(receipt)


def current_open_ids(receipt: Mapping[str, Any]) -> set[str]:
    return {row["id"] for row in normal_findings(receipt.get("findings")) if row["status"] == "open"}


def current_open_material_ids(receipt: Mapping[str, Any]) -> list[str]:
    """Stable IDs whose current pass must be treated as material work."""
    return sorted(
        row["id"]
        for row in normal_findings(receipt.get("findings"))
        if row["status"] == "open" and row["severity"] == "material"
    )


def apply_review(receipt: dict[str, Any], findings: Any) -> list[dict[str, str]]:
    """Merge a review into the stable ledger without silently closing rows."""
    reviewed = normal_findings(findings)
    prior = normal_findings(receipt.get("findings"))
    by_id = {row["id"]: dict(row) for row in prior}
    order = [row["id"] for row in prior]
    for row in reviewed:
        old = by_id.get(row["id"])
        if old is None:
            by_id[row["id"]] = dict(row, status="open")
            order.append(row["id"])
            continue
        need(
            not (old["severity"] == "material" and row["severity"] == "trivial"),
            f"planning finding {row['id']} severity cannot be silently downgraded",
        )
        # A recurring finding gets its original stable identity back even if a
        # previous pass recorded it as resolved.
        reopened = dict(row, status="open")
        reopened.pop("resolution_evidence", None)
        reopened.pop("resolved_iteration", None)
        by_id[row["id"]] = reopened
    merged = [by_id[finding_id] for finding_id in order]
    receipt["findings"] = merged
    receipt["ledger_sha256"] = ledger_sha256(merged)
    receipt["identity_sha256"] = identity(receipt)
    _sync_current_identity(receipt)
    return merged


def check_coverage_review(kind: str, value: Any) -> None:
    _kind(kind)
    need(isinstance(value, Mapping), "coverage_review must be a mapping")
    expected = set(RUBRICS[kind])
    missing = expected - set(value)
    need(
        not missing,
        "coverage_review is missing rubric dimensions: " + ", ".join(sorted(missing)),
    )
    for dimension in RUBRICS[kind]:
        entry = value[dimension]
        if isinstance(entry, str):
            _text(entry, f"coverage_review.{dimension}")
        elif isinstance(entry, Mapping):
            evidence = entry.get("evidence")
            reason = entry.get("reason")
            need(
                (isinstance(evidence, str) and evidence.strip())
                or (isinstance(reason, str) and reason.strip()),
                f"coverage_review.{dimension} needs nonempty evidence or reason",
            )
        else:
            raise PlanningError(
                f"coverage_review.{dimension} needs nonempty evidence or reason"
            )


def check_addresses(receipt: Mapping[str, Any], addresses: Any) -> list[str]:
    need(isinstance(addresses, list), "planning plan addresses must be a list")
    normalized = [_text(value, "planning plan address") for value in addresses]
    need(len(set(normalized)) == len(normalized), "planning plan addresses must not duplicate IDs")
    open_ids = current_open_ids(receipt)
    need(
        set(normalized) == open_ids,
        "planning plan addresses must list every and only open finding ID",
    )
    return normalized


def resolve_findings(
    receipt: dict[str, Any], resolutions: Any, addresses: list[str]
) -> list[str]:
    need(isinstance(resolutions, list), "planning apply resolutions must be a list")
    resolution_ids: list[str] = []
    resolution_evidence: dict[str, str] = {}
    for row in resolutions:
        need(isinstance(row, Mapping), "planning resolution must be an object")
        finding_id = _text(row.get("id"), "planning resolution id")
        resolution_evidence[finding_id] = _text(
            row.get("evidence"), f"planning resolution {finding_id} evidence"
        )
        resolution_ids.append(finding_id)
    need(
        len(set(resolution_ids)) == len(resolution_ids),
        "planning apply resolutions must not duplicate IDs",
    )
    known = current_open_ids(receipt)
    need(
        set(resolution_ids) <= known and set(resolution_ids) <= set(addresses),
        "planning apply resolutions contain an unknown or unplanned finding ID",
    )
    findings = normal_findings(receipt["findings"])
    resolved = set(resolution_ids)
    for row in findings:
        if row["id"] in resolved:
            row["status"] = "resolved"
            row["resolution_evidence"] = resolution_evidence[row["id"]]
            row["resolved_iteration"] = receipt["current_iteration"]["id"]
    receipt["findings"] = findings
    receipt["ledger_sha256"] = ledger_sha256(findings)
    receipt["identity_sha256"] = identity(receipt)
    _sync_current_identity(receipt)
    return resolution_ids


def all_clear(receipt: Mapping[str, Any]) -> bool:
    return not current_open_ids(receipt)


def countable_outcome(receipt: Mapping[str, Any], *, material: bool) -> str:
    """A pass can count only after its ledger has no unresolved finding."""
    if material or not all_clear(receipt):
        return "material"
    return "trivial"


def until_decision(receipt: Mapping[str, Any], *, extra_open: list[Any] | None = None) -> dict[str, Any]:
    """Use the shared evidence policy instead of trusting a cached streak.

    Older summary-only iteration rows cannot become convergence evidence by
    upgrade.  A current planner must carry the immutable audit commit and
    verified marker for every pass it asks the shared policy to count.
    """
    need(isinstance(receipt, Mapping), "planning receipt must be an object")
    epoch = receipt.get("epoch")
    need(isinstance(epoch, int) and epoch >= 1, "planning receipt epoch is invalid")
    rows = receipt.get("completed_iterations")
    need(isinstance(rows, list), "planning completed iterations must be a list")
    passes = []
    for row in rows:
        need(isinstance(row, Mapping), "planning completed iteration is invalid")
        row_epoch = row.get("epoch", epoch)
        need(isinstance(row_epoch, int), "planning completed iteration epoch is invalid")
        if row_epoch != epoch:
            continue
        passes.append(
            {
                "id": row.get("id"),
                "outcome": row.get("outcome"),
                "verified": row.get("verified"),
                "commit": row.get("commit"),
            }
        )
    open_findings = sorted(current_open_ids(receipt))
    if extra_open:
        open_findings.extend(extra_open)
    try:
        return until.decide(passes, open_findings=open_findings)
    except until.UntilError as exc:
        raise PlanningError(str(exc)) from exc


def acceptance(kind: str) -> list[str]:
    kind = _kind(kind)
    return [
        "research evidence"
        if kind == "research"
        else "behavior model"
        if kind == "behavior"
        else "specification"
    ]


def is_planning_stage(stage: str) -> bool:
    return stage in {
        "research",
        "research-review",
        "research-plan",
        "research-apply",
        "research-verify",
        "research-commit",
        "research-finalize",
        "behavior",
        "behavior-review",
        "behavior-plan",
        "behavior-apply",
        "behavior-verify",
        "behavior-commit",
        "behavior-finalize",
        "spec",
        "spec-review",
        "spec-plan",
        "spec-apply",
        "spec-verify",
        "spec-commit",
        "spec-finalize",
    }


def kind_for_stage(stage: str) -> str | None:
    if stage.startswith("research"):
        return "research"
    if stage.startswith("behavior"):
        return "behavior"
    if stage.startswith("spec-") or stage == "spec":
        return "spec"
    return None
