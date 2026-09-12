"""Markdown-backed convergence records for one ShipLoop execution step.

The protocol owns Git, locks, and Markdown transactions.  This module only
normalizes the small durable records which make a cold-context step-plan loop
repeatable: a plan candidate, a stable findings ledger, a bound context, and
immutable completed-pass summaries.  It deliberately does not extend the
upstream research/behavior/spec planning kinds.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import shiploop_knowledge as knowledge
import shiploop_store as store
import shiploop_until as until


VERSION = 1
ROUTES = ("initial", "improve")
RUBRIC = (
    "step_scope",
    "current_implementation",
    "environment",
    "dependencies",
    "flows",
    "edge_conditions",
    "second_order_effects",
    "implicit_requirements",
    "test_strategy",
    "documentation",
)
CONTEXT_EVIDENCE = ("step", "implementation", "environment", "dependencies")
SYSTEM_CONTEXT_EVIDENCE = (
    "context_sha256",
    "role_ids",
    "interface_ids",
    "interaction_ids",
    "question_ids",
    "observation_ids",
    "source_ids",
)
CONTEXT_KEYS = (
    "step_sha256",
    "dependency_sha256",
    "enclosing_review_sha256",
    "worktree",
    "git_baseline",
    "committed_tree_sha256",
    "worktree_fingerprint",
    "status_sha256",
    "spec_sha256",
    "environment_sha256",
    "behavior_sha256",
    "plan_sha256",
    "knowledge_sha256",
)
SYSTEM_CONTEXT_KEYS = (
    "research_candidate_sha256",
    "research_certificate_sha256",
    "research_evidence_sha256",
    "system_context_sha256",
)
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,191}\Z")
_FINDING_RE = re.compile(r"[A-Za-z][A-Za-z0-9._:-]{0,159}\Z")
_CONTEXT_REF_RE = re.compile(r"[A-Za-z][A-Za-z0-9._:-]{0,159}\Z")
_SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
_CATEGORIES = {
    "scope",
    "behavior",
    "implementation",
    "environment",
    "dependency",
    "flow",
    "edge-condition",
    "second-order-effect",
    "implicit-requirement",
    "test-strategy",
    "documentation",
}
_PLACEHOLDER_RE = re.compile(
    r"^(?:[-*]\s*)?(?:n/?a|none|tbd|unknown|not applicable|same as above)\.?$",
    re.IGNORECASE,
)


class StepPlanningError(ValueError):
    """A per-step planning artifact cannot support safe continuation."""


def need(ok: bool, message: str) -> None:
    if not ok:
        raise StepPlanningError(message)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_text(value: str) -> str:
    need(isinstance(value, str), "text digest requires a string")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_value(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, label: str, *, limit: int = 12000) -> str:
    need(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty")
    normalized = value.strip()
    need(len(normalized) <= limit, f"{label} exceeds the bounded step-plan limit")
    need(
        not _PLACEHOLDER_RE.fullmatch(normalized),
        f"{label} must be concrete rather than a placeholder",
    )
    return normalized


def _id(value: Any, label: str) -> str:
    need(isinstance(value, str) and _ID_RE.fullmatch(value), f"{label} is unsafe")
    return value


def _sha(value: Any, label: str) -> str:
    need(isinstance(value, str) and _SHA_RE.fullmatch(value), f"{label} is invalid")
    return value


def loop_id(run_id: str, step_id: str, route: str, iteration: str | None = None) -> str:
    """Return a durable loop ID distinct for an initial or Improve iteration."""
    _id(run_id, "run ID")
    _id(step_id, "step ID")
    need(route in ROUTES, "step-plan route is invalid")
    if route == "initial":
        need(iteration in (None, ""), "initial step plan cannot name an Improve iteration")
        value = f"{run_id}-{step_id}-initial"
    else:
        # The outer iteration remains durably linked from the step receipt,
        # but a cold nested-pass packet must not dump that enclosing receipt
        # identity merely because it appears inside the deterministic loop ID.
        outer = _id(iteration, "Improve iteration ID")
        value = f"{run_id}-{step_id}-improve-I{sha256_text(outer)[:16]}"
    return _id(value, "step-plan loop ID")


def receipt_name(value: str) -> str:
    return f"step-planning/{_id(value, 'step-plan loop ID')}.md"


def candidate_name(value: str) -> str:
    return f"step-planning/{_id(value, 'step-plan loop ID')}/candidate.md"


def pass_name(value: str, pass_id: str) -> str:
    return f"step-planning/{_id(value, 'step-plan loop ID')}/passes/{_id(pass_id, 'step-plan pass ID')}.md"


def abandoned_name(value: str, pass_id: str) -> str:
    return f"step-planning/{_id(value, 'step-plan loop ID')}/abandoned/{_id(pass_id, 'step-plan pass ID')}.md"


def certificate_name(value: str) -> str:
    return f"step-planning/{_id(value, 'step-plan loop ID')}/certificate.md"


def _run_file(root: Path, relative: str, label: str) -> Path:
    """Return an existing non-symlink Markdown record below ``root``.

    Receipts refer to archive records by deterministic relative paths.  Check
    every existing parent too: checking only the leaf would otherwise permit a
    symlinked ``passes`` or ``abandoned`` directory to replace durable evidence.
    """
    relative_path = Path(relative)
    need(
        not relative_path.is_absolute() and ".." not in relative_path.parts,
        f"unsafe {label} path",
    )
    path = root / relative_path
    for candidate in (path, *path.parents):
        need(not candidate.is_symlink(), f"{label} path contains a symlink")
        if candidate == root:
            break
    need(path.is_file(), f"{label} is missing")
    return path


def candidate_identity(body: Any) -> str:
    # Validate semantic non-emptiness without normalizing the bytes that are
    # bound.  A whitespace-only out-of-band edit must invalidate a receipt.
    _text(body, "step-plan candidate")
    return sha256_text(body)


def _normal_finding(raw: Any) -> dict[str, str]:
    need(isinstance(raw, Mapping), "step-plan finding must be an object")
    finding_id = raw.get("id")
    need(
        isinstance(finding_id, str) and _FINDING_RE.fullmatch(finding_id),
        "step-plan finding requires a stable safe ID",
    )
    severity = raw.get("severity")
    need(severity in ("material", "trivial"), "step-plan finding severity is invalid")
    category = raw.get("category", "implementation")
    need(category in _CATEGORIES, "step-plan finding category is invalid")
    status = raw.get("status", "open")
    need(status in ("open", "resolved"), "step-plan finding status is invalid")
    out = {
        "id": finding_id,
        "severity": severity,
        "category": category,
        "summary": _text(raw.get("summary"), f"step-plan finding {finding_id} summary"),
        "status": status,
    }
    if status == "resolved":
        out["resolution_evidence"] = _text(
            raw.get("resolution_evidence"),
            f"step-plan finding {finding_id} resolution evidence",
        )
        out["resolved_pass"] = _id(
            raw.get("resolved_pass"), f"step-plan finding {finding_id} resolved pass"
        )
        disposition = raw.get("disposition")
        if disposition is not None:
            need(
                disposition == "no-contract-change"
                and severity == "material"
                and category in ("scope", "behavior"),
                f"step-plan finding {finding_id} disposition is invalid",
            )
            out["disposition"] = disposition
    return out


def normal_findings(value: Any) -> list[dict[str, str]]:
    need(isinstance(value, list), "step-plan findings must be a list")
    rows = [_normal_finding(row) for row in value]
    ids = [row["id"] for row in rows]
    need(len(ids) == len(set(ids)), "step-plan findings must not duplicate IDs")
    return rows


def ledger_sha256(value: Any) -> str:
    rows = normal_findings(value)
    rows.sort(key=lambda row: row["id"])
    return sha256_value(rows)


def validate_context(value: Any) -> dict[str, str]:
    need(isinstance(value, Mapping), "step-plan context must be an object")
    present_system_keys = set(value) & set(SYSTEM_CONTEXT_KEYS)
    expected_keys = set(CONTEXT_KEYS)
    if present_system_keys:
        expected_keys.update(SYSTEM_CONTEXT_KEYS)
    missing = expected_keys - set(value)
    extra = set(value) - expected_keys
    need(not missing and not extra, "step-plan context has the wrong identity keys")
    out: dict[str, str] = {}
    for key in (*CONTEXT_KEYS, *SYSTEM_CONTEXT_KEYS):
        if key not in expected_keys:
            continue
        raw = value[key]
        if key == "worktree":
            text = _text(raw, "step-plan context worktree", limit=4096)
            need(Path(text).is_absolute(), "step-plan context worktree must be absolute")
            out[key] = text
        elif key == "git_baseline":
            need(
                isinstance(raw, str) and _COMMIT_RE.fullmatch(raw),
                "step-plan context Git baseline is invalid",
            )
            out[key] = raw
        else:
            out[key] = _sha(raw, f"step-plan context {key}")
    return out


def context_sha256(value: Any) -> str:
    return sha256_value(validate_context(value))


def identity(*, candidate_sha256: str, ledger_sha256_value: str, context_sha256_value: str) -> str:
    return sha256_value(
        {
            "candidate_sha256": _sha(candidate_sha256, "step-plan candidate digest"),
            "ledger_sha256": _sha(ledger_sha256_value, "step-plan ledger digest"),
            "context_sha256": _sha(context_sha256_value, "step-plan context digest"),
        }
    )


def _pass(
    *,
    loop: str,
    epoch: int,
    number: int,
    candidate_sha256_value: str,
    ledger_sha256_value: str,
    context_sha256_value: str,
    context: Mapping[str, str],
) -> dict[str, Any]:
    need(isinstance(epoch, int) and epoch >= 1, "step-plan epoch must be positive")
    need(isinstance(number, int) and number >= 1, "step-plan pass number must be positive")
    pass_id = _id(f"{loop}-E{epoch}-P{number}", "step-plan pass ID")
    return {
        "id": pass_id,
        "epoch": epoch,
        "number": number,
        "git_baseline": context["git_baseline"],
        "worktree_fingerprint": context["worktree_fingerprint"],
        "status_sha256": context["status_sha256"],
        "candidate_sha256": candidate_sha256_value,
        "ledger_sha256": ledger_sha256_value,
        "context_sha256": context_sha256_value,
        "identity_sha256": identity(
            candidate_sha256=candidate_sha256_value,
            ledger_sha256_value=ledger_sha256_value,
            context_sha256_value=context_sha256_value,
        ),
    }


def new_receipt(
    *,
    loop: str,
    step_id: str,
    route: str,
    return_stage: str,
    body: str,
    context: Mapping[str, str],
) -> dict[str, Any]:
    loop = _id(loop, "step-plan loop ID")
    step_id = _id(step_id, "step ID")
    need(route in ROUTES, "step-plan route is invalid")
    need(return_stage in ("implement", "improve-apply"), "step-plan return stage is invalid")
    expected = "implement" if route == "initial" else "improve-apply"
    need(return_stage == expected, "step-plan route and return stage disagree")
    candidate = candidate_identity(body)
    normalized_context = validate_context(context)
    ledger = ledger_sha256([])
    context_digest = context_sha256(normalized_context)
    receipt: dict[str, Any] = {
        "version": VERSION,
        "kind": "step-plan",
        "loop_id": loop,
        "step_id": step_id,
        "route": route,
        "return_stage": return_stage,
        "candidate_path": candidate_name(loop),
        "candidate_sha256": candidate,
        "findings": [],
        "ledger_sha256": ledger,
        "context": normalized_context,
        "context_sha256": context_digest,
        "epoch": 1,
        "pass": 1,
        "completed_passes": [],
        "abandoned_passes": [],
    }
    receipt["identity_sha256"] = identity(
        candidate_sha256=candidate,
        ledger_sha256_value=ledger,
        context_sha256_value=context_digest,
    )
    receipt["current_pass"] = _pass(
        loop=loop,
        epoch=1,
        number=1,
        candidate_sha256_value=candidate,
        ledger_sha256_value=ledger,
        context_sha256_value=context_digest,
        context=normalized_context,
    )
    return receipt


def _assert_pass(value: Any, receipt: Mapping[str, Any], *, completed: bool = False) -> dict[str, Any]:
    need(isinstance(value, Mapping), "step-plan pass must be an object")
    loop = _id(receipt.get("loop_id"), "step-plan loop ID")
    pass_id = _id(value.get("id"), "step-plan pass ID")
    need(pass_id.startswith(loop + "-E"), "step-plan pass does not belong to its loop")
    for key in ("epoch", "number"):
        need(isinstance(value.get(key), int) and value[key] >= 1, f"step-plan pass {key} is invalid")
    need(
        pass_id == f"{loop}-E{value['epoch']}-P{value['number']}",
        "step-plan pass ID does not match its epoch and number",
    )
    for key in (
        "git_baseline",
        "worktree_fingerprint",
        "status_sha256",
        "candidate_sha256",
        "ledger_sha256",
        "context_sha256",
        "identity_sha256",
    ):
        raw = value.get(key)
        if key == "git_baseline":
            need(isinstance(raw, str) and _COMMIT_RE.fullmatch(raw), "step-plan pass baseline is invalid")
        else:
            _sha(raw, f"step-plan pass {key}")
    expected_identity = identity(
        candidate_sha256=value["candidate_sha256"],
        ledger_sha256_value=value["ledger_sha256"],
        context_sha256_value=value["context_sha256"],
    )
    need(value["identity_sha256"] == expected_identity, "step-plan pass identity mismatch")
    if completed:
        need(value.get("verified") is True, "completed step-plan pass lacks verification")
        need(value.get("outcome") in ("material", "trivial"), "completed step-plan pass outcome is invalid")
        need(
            isinstance(value.get("commit"), str) and _COMMIT_RE.fullmatch(value["commit"]),
            "completed step-plan pass audit commit is invalid",
        )
    return dict(value)


def assert_receipt(root: Path, value: Any, *, loop: str | None = None) -> dict[str, Any]:
    need(isinstance(value, dict), "step-plan receipt must be an object")
    need(value.get("version") == VERSION, "unsupported step-plan receipt")
    need(value.get("kind") == "step-plan", "step-plan receipt kind mismatch")
    actual_loop = _id(value.get("loop_id"), "step-plan loop ID")
    if loop is not None:
        need(actual_loop == _id(loop, "step-plan loop ID"), "step-plan loop ID mismatch")
    _id(value.get("step_id"), "step-plan receipt step ID")
    route = value.get("route")
    need(route in ROUTES, "step-plan receipt route is invalid")
    return_stage = value.get("return_stage")
    need(return_stage == ("implement" if route == "initial" else "improve-apply"), "step-plan receipt return stage is invalid")
    need(value.get("candidate_path") == candidate_name(actual_loop), "step-plan candidate path mismatch")
    candidate_path = _run_file(root, value["candidate_path"], "step-plan candidate")
    body = candidate_path.read_bytes().decode("utf-8")
    need(
        candidate_identity(body) == _sha(value.get("candidate_sha256"), "step-plan candidate digest"),
        "step-plan candidate changed outside the revise action",
    )
    findings = normal_findings(value.get("findings"))
    ledger = ledger_sha256(findings)
    need(value.get("ledger_sha256") == ledger, "step-plan finding ledger digest mismatch")
    context = validate_context(value.get("context"))
    context_digest = context_sha256(context)
    need(value.get("context_sha256") == context_digest, "step-plan context digest mismatch")
    expected_identity = identity(
        candidate_sha256=value["candidate_sha256"],
        ledger_sha256_value=ledger,
        context_sha256_value=context_digest,
    )
    need(value.get("identity_sha256") == expected_identity, "step-plan receipt identity mismatch")
    need(isinstance(value.get("epoch"), int) and value["epoch"] >= 1, "step-plan epoch is invalid")
    need(isinstance(value.get("pass"), int) and value["pass"] >= 1, "step-plan pass is invalid")
    current = _assert_pass(value.get("current_pass"), value)
    for key in ("candidate_sha256", "ledger_sha256", "context_sha256", "identity_sha256"):
        need(current[key] == value[key], f"step-plan current pass {key} is stale")
    need(current["epoch"] == value["epoch"] and current["number"] == value["pass"], "step-plan current pass cursor is stale")
    completed = value.get("completed_passes")
    abandoned = value.get("abandoned_passes")
    need(isinstance(completed, list) and isinstance(abandoned, list), "step-plan pass archives are invalid")
    current_cursor = (current["epoch"], current["number"])
    seen_ids: set[str] = {current["id"]}
    seen_commits: set[str] = set()
    previous_completed: tuple[int, int] = (0, 0)
    for row in completed:
        parsed = _assert_pass(row, value, completed=True)
        cursor = (parsed["epoch"], parsed["number"])
        need(
            cursor > previous_completed,
            "step-plan completed pass archives are not in epoch/pass order",
        )
        need(
            cursor < current_cursor,
            "step-plan completed pass archive must precede the current cursor",
        )
        previous_completed = cursor
        need(parsed["id"] not in seen_ids, "step-plan completed passes duplicate an ID")
        need(parsed["commit"] not in seen_commits, "step-plan completed passes duplicate a commit")
        seen_ids.add(parsed["id"])
        seen_commits.add(parsed["commit"])
        archive = _run_file(
            root,
            pass_name(actual_loop, parsed["id"]),
            "step-plan completed pass archive",
        )
        expected = store.dumps(parsed, "ShipLoop completed step-plan pass").encode(
            "utf-8"
        )
        need(
            archive.read_bytes() == expected,
            "step-plan completed pass archive does not match its receipt entry",
        )
        need(
            store.read_record(archive) == parsed,
            "step-plan completed pass archive is not semantically valid",
        )
    previous_abandoned: tuple[int, int] = (0, 0)
    for row in abandoned:
        parsed = _assert_pass(row, value)
        cursor = (parsed["epoch"], parsed["number"])
        need(
            cursor > previous_abandoned,
            "step-plan abandoned pass archives are not in epoch/pass order",
        )
        need(
            cursor[0] < current_cursor[0],
            "step-plan abandoned pass archive must be from a prior repair epoch",
        )
        previous_abandoned = cursor
        need(parsed.get("status") == "abandoned", "step-plan abandoned pass status is invalid")
        _text(parsed.get("reason"), "step-plan abandoned pass reason")
        need(parsed["id"] not in seen_ids, "step-plan pass archive duplicates an ID")
        seen_ids.add(parsed["id"])
        archive = _run_file(
            root,
            abandoned_name(actual_loop, parsed["id"]),
            "step-plan abandoned pass archive",
        )
        expected = store.dumps(parsed, "ShipLoop abandoned step-plan pass").encode(
            "utf-8"
        )
        need(
            archive.read_bytes() == expected,
            "step-plan abandoned pass archive does not match its receipt entry",
        )
        need(
            store.read_record(archive) == parsed,
            "step-plan abandoned pass archive is not semantically valid",
        )
    return value


def _sync_identity(receipt: dict[str, Any]) -> None:
    receipt["ledger_sha256"] = ledger_sha256(receipt["findings"])
    receipt["context_sha256"] = context_sha256(receipt["context"])
    receipt["identity_sha256"] = identity(
        candidate_sha256=receipt["candidate_sha256"],
        ledger_sha256_value=receipt["ledger_sha256"],
        context_sha256_value=receipt["context_sha256"],
    )
    current = receipt.get("current_pass")
    if isinstance(current, dict):
        current.update(
            candidate_sha256=receipt["candidate_sha256"],
            ledger_sha256=receipt["ledger_sha256"],
            context_sha256=receipt["context_sha256"],
            identity_sha256=receipt["identity_sha256"],
        )


def apply_review(receipt: dict[str, Any], value: Any) -> list[dict[str, str]]:
    """Merge a review without allowing a missing row to close a prior finding."""
    reviewed = normal_findings(value)
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
            f"step-plan finding {row['id']} severity cannot be silently downgraded",
        )
        need(
            not (
                old["severity"] == "material"
                and old["category"] in ("scope", "behavior")
            )
            or row["category"] == old["category"],
            f"step-plan finding {row['id']} cannot recategorize a material {old['category']} finding",
        )
        reopened = dict(row, status="open")
        reopened.pop("resolution_evidence", None)
        reopened.pop("resolved_pass", None)
        by_id[row["id"]] = reopened
    receipt["findings"] = [by_id[finding_id] for finding_id in order]
    _sync_identity(receipt)
    return normal_findings(receipt["findings"])


def open_ids(receipt: Mapping[str, Any]) -> set[str]:
    return {row["id"] for row in normal_findings(receipt.get("findings")) if row["status"] == "open"}


def open_material_ids(receipt: Mapping[str, Any]) -> list[str]:
    return sorted(
        row["id"]
        for row in normal_findings(receipt.get("findings"))
        if row["status"] == "open" and row["severity"] == "material"
    )


def scope_or_behavior_findings(receipt: Mapping[str, Any]) -> list[str]:
    return sorted(
        row["id"]
        for row in normal_findings(receipt.get("findings"))
        if row["status"] == "open"
        and row["severity"] == "material"
        and row["category"] in ("scope", "behavior")
    )


def check_coverage_review(value: Any) -> dict[str, Any]:
    need(isinstance(value, Mapping), "step-plan coverage_review must be a mapping")
    missing = set(RUBRIC) - set(value)
    extra = set(value) - set(RUBRIC)
    need(not missing and not extra, "step-plan coverage_review must contain exactly the required dimensions")
    normalized: dict[str, Any] = {}
    for key in RUBRIC:
        item = value[key]
        if isinstance(item, str):
            normalized[key] = _text(item, f"step-plan coverage_review.{key}")
        elif isinstance(item, Mapping):
            need(set(item) <= {"evidence", "reason"}, f"step-plan coverage_review.{key} has unsupported fields")
            evidence = item.get("evidence")
            reason = item.get("reason")
            need(
                (isinstance(evidence, str) and evidence.strip())
                or (isinstance(reason, str) and reason.strip()),
                f"step-plan coverage_review.{key} needs concrete evidence or reason",
            )
            normalized[key] = {
                name: _text(item[name], f"step-plan coverage_review.{key}.{name}")
                for name in ("evidence", "reason")
                if name in item and isinstance(item[name], str) and item[name].strip()
            }
            knowledge.screen_payload(normalized[key])
        else:
            raise StepPlanningError(
                f"step-plan coverage_review.{key} needs concrete evidence or reason"
            )
    return normalized


def _context_reference_ids(value: Any, label: str) -> list[str]:
    need(isinstance(value, list), f"{label} must be a list")
    need(len(value) <= 64, f"{label} exceeds the bounded context limit")
    result: list[str] = []
    for item in value:
        need(
            isinstance(item, str) and _CONTEXT_REF_RE.fullmatch(item) is not None,
            f"{label} must contain stable context IDs",
        )
        result.append(item)
    need(len(result) == len(set(result)), f"{label} must not duplicate IDs")
    return result


def _system_context_evidence(
    value: Any, selected: Mapping[str, Any]
) -> dict[str, Any]:
    need(
        isinstance(value, Mapping) and set(value) == set(SYSTEM_CONTEXT_EVIDENCE),
        "step-plan system_context evidence has an unexpected schema",
    )
    expected_sha = _sha(
        selected.get("context_sha256"), "selected system-context digest"
    )
    actual_sha = _sha(
        value.get("context_sha256"), "step-plan system_context context_sha256"
    )
    need(
        actual_sha == expected_sha,
        "step-plan system_context evidence names another context digest",
    )
    normalized: dict[str, Any] = {"context_sha256": actual_sha}
    for field, projected_field in (
        ("role_ids", "roles"),
        ("interface_ids", "interfaces"),
        ("interaction_ids", "interactions"),
        ("question_ids", "questions"),
        ("observation_ids", "observations"),
        ("source_ids", "sources"),
    ):
        projected = selected.get(projected_field)
        need(
            isinstance(projected, list),
            f"selected system-context {projected_field} is invalid",
        )
        expected_ids = {
            row.get("id")
            for row in projected
            if isinstance(row, Mapping) and isinstance(row.get("id"), str)
        }
        need(
            len(expected_ids) == len(projected),
            f"selected system-context {projected_field} has invalid IDs",
        )
        actual_ids = _context_reference_ids(
            value.get(field), f"step-plan system_context {field}"
        )
        need(
            set(actual_ids) == expected_ids,
            f"step-plan system_context {field} must cite every and only selected ID",
        )
        normalized[field] = sorted(actual_ids)
    return normalized


def check_context_evidence(
    value: Any, *, system_context: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    need(isinstance(value, Mapping), "step-plan context_evidence must be a mapping")
    expected = set(CONTEXT_EVIDENCE)
    if system_context is not None:
        expected.add("system_context")
    missing = expected - set(value)
    extra = set(value) - expected
    need(
        not missing and not extra,
        "step-plan context_evidence must contain exactly the selected evidence sections",
    )
    normalized: dict[str, Any] = {}
    for key in CONTEXT_EVIDENCE:
        raw = value[key]
        values = [raw] if isinstance(raw, str) else raw
        need(isinstance(values, list) and values, f"step-plan context_evidence.{key} must be nonempty")
        rows = [_text(row, f"step-plan context_evidence.{key}", limit=2000) for row in values]
        need(len(rows) == len(set(rows)), f"step-plan context_evidence.{key} must not duplicate observations")
        knowledge.screen_payload(rows)
        normalized[key] = rows
    if system_context is not None:
        normalized["system_context"] = _system_context_evidence(
            value["system_context"], system_context
        )
    return normalized


def check_addresses(receipt: Mapping[str, Any], value: Any) -> list[str]:
    need(isinstance(value, list), "step-plan revise addresses must be a list")
    rows = [_text(row, "step-plan revise address", limit=160) for row in value]
    need(len(rows) == len(set(rows)), "step-plan revise addresses must not duplicate IDs")
    need(set(rows) == open_ids(receipt), "step-plan revise must address every and only open finding ID")
    return rows


def resolve_findings(receipt: dict[str, Any], value: Any, addresses: list[str]) -> list[str]:
    need(isinstance(value, list), "step-plan revise resolutions must be a list")
    evidence_by_id: dict[str, str] = {}
    for row in value:
        need(isinstance(row, Mapping), "step-plan resolution must be an object")
        finding_id = _text(row.get("id"), "step-plan resolution ID", limit=160)
        need(finding_id not in evidence_by_id, "step-plan revise resolutions duplicate an ID")
        evidence_by_id[finding_id] = _text(
            row.get("evidence"), f"step-plan resolution {finding_id} evidence"
        )
    known = open_ids(receipt)
    need(
        set(evidence_by_id) <= known and set(evidence_by_id) <= set(addresses),
        "step-plan revise resolves an unknown or unaddressed finding",
    )
    current_pass = _id(receipt["current_pass"]["id"], "step-plan pass ID")
    findings = normal_findings(receipt["findings"])
    blocked = sorted(
        row["id"]
        for row in findings
        if row["id"] in evidence_by_id
        and row["status"] == "open"
        and row["severity"] == "material"
        and row["category"] in ("scope", "behavior")
    )
    need(
        not blocked,
        "step-plan scope or behavior findings require an explicit broader-plan decision; "
        "they cannot be resolved by a step-plan revise: "
        + ", ".join(blocked),
    )
    for row in findings:
        if row["id"] in evidence_by_id:
            row.update(
                status="resolved",
                resolution_evidence=evidence_by_id[row["id"]],
                resolved_pass=current_pass,
            )
    receipt["findings"] = findings
    _sync_identity(receipt)
    return sorted(evidence_by_id)


def resolve_no_contract_change_findings(receipt: dict[str, Any], value: Any) -> list[str]:
    """Close only a false-positive scope/behavior classification explicitly.

    A scope or behavior finding normally requires a broader-plan decision.  If
    a host can demonstrate that the approved contract is unchanged, retain the
    original material finding with a durable ``no-contract-change`` disposition
    and force a new review pass; ordinary revise must never make that call.
    """
    need(isinstance(value, list), "step-plan disposition resolutions must be a list")
    blockers = scope_or_behavior_findings(receipt)
    evidence_by_id: dict[str, str] = {}
    for row in value:
        need(isinstance(row, Mapping), "step-plan disposition resolution must be an object")
        finding_id = _text(row.get("id"), "step-plan disposition resolution ID", limit=160)
        need(finding_id not in evidence_by_id, "step-plan disposition resolutions duplicate an ID")
        evidence_by_id[finding_id] = _text(
            row.get("evidence"),
            f"step-plan no-contract-change {finding_id} evidence",
        )
    need(
        set(evidence_by_id) == set(blockers),
        "step-plan no-contract-change disposition must cover every and only material scope or behavior finding",
    )
    current_pass = _id(receipt["current_pass"]["id"], "step-plan pass ID")
    findings = normal_findings(receipt["findings"])
    for row in findings:
        if row["id"] in evidence_by_id:
            row.update(
                status="resolved",
                resolution_evidence=evidence_by_id[row["id"]],
                resolved_pass=current_pass,
                disposition="no-contract-change",
            )
    receipt["findings"] = findings
    _sync_identity(receipt)
    return sorted(evidence_by_id)


def replace_candidate(receipt: dict[str, Any], body: Any) -> str:
    receipt["candidate_sha256"] = candidate_identity(body)
    _sync_identity(receipt)
    return receipt["candidate_sha256"]


def start_next_pass(receipt: dict[str, Any], context: Mapping[str, str]) -> None:
    normalized_context = validate_context(context)
    receipt["pass"] = int(receipt["pass"]) + 1
    receipt["context"] = normalized_context
    _sync_identity(receipt)
    receipt["current_pass"] = _pass(
        loop=receipt["loop_id"],
        epoch=receipt["epoch"],
        number=receipt["pass"],
        candidate_sha256_value=receipt["candidate_sha256"],
        ledger_sha256_value=receipt["ledger_sha256"],
        context_sha256_value=receipt["context_sha256"],
        context=normalized_context,
    )


def rebind_after_repair(receipt: dict[str, Any], context: Mapping[str, str]) -> None:
    """Create a new repair epoch while retaining every prior audit record."""
    normalized_context = validate_context(context)
    receipt["epoch"] = int(receipt["epoch"]) + 1
    receipt["pass"] = 1
    receipt["context"] = normalized_context
    _sync_identity(receipt)
    receipt["current_pass"] = _pass(
        loop=receipt["loop_id"],
        epoch=receipt["epoch"],
        number=1,
        candidate_sha256_value=receipt["candidate_sha256"],
        ledger_sha256_value=receipt["ledger_sha256"],
        context_sha256_value=receipt["context_sha256"],
        context=normalized_context,
    )


def current_epoch_passes(receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    epoch = receipt.get("epoch")
    return [
        dict(row)
        for row in receipt.get("completed_passes", [])
        if isinstance(row, Mapping) and row.get("epoch") == epoch
    ]


def all_clear(receipt: Mapping[str, Any]) -> bool:
    return not open_ids(receipt)


def certificate(
    receipt: Mapping[str, Any], *, final_check_action: str, final_check_sha256: str, audit_head: str
) -> dict[str, Any]:
    loop = _id(receipt.get("loop_id"), "step-plan loop ID")
    final_pass = _assert_pass(receipt.get("current_pass"), receipt)
    need(all_clear(receipt), "step-plan certificate requires no open findings")
    try:
        readiness = until.decide(
            current_epoch_passes(receipt), open_findings=sorted(open_ids(receipt))
        )
    except until.UntilError as exc:
        raise StepPlanningError(str(exc)) from exc
    need(
        readiness["phase"] == "ready",
        "step-plan certificate requires two consecutive verified trivial passes",
    )
    need(
        audit_head == final_pass["git_baseline"],
        "step-plan certificate audit head must be the fresh final-check baseline",
    )
    return {
        "version": VERSION,
        "kind": "step-plan-certificate",
        "loop_id": loop,
        "step_id": _id(receipt.get("step_id"), "step-plan certificate step ID"),
        "route": receipt.get("route"),
        "return_stage": receipt.get("return_stage"),
        "candidate_sha256": receipt.get("candidate_sha256"),
        "ledger_sha256": receipt.get("ledger_sha256"),
        "context_sha256": receipt.get("context_sha256"),
        "identity_sha256": receipt.get("identity_sha256"),
        "final_pass_id": final_pass["id"],
        "final_check_action": _id(final_check_action, "step-plan final check action"),
        "final_check_sha256": _sha(final_check_sha256, "step-plan final check digest"),
        "audit_head": audit_head,
        "epoch": receipt.get("epoch"),
    }


def assert_certificate(value: Any, receipt: Mapping[str, Any]) -> dict[str, Any]:
    need(isinstance(value, Mapping), "step-plan certificate must be an object")
    need(value.get("version") == VERSION and value.get("kind") == "step-plan-certificate", "step-plan certificate shape is invalid")
    for key in (
        "loop_id",
        "step_id",
        "route",
        "return_stage",
        "candidate_sha256",
        "ledger_sha256",
        "context_sha256",
        "identity_sha256",
        "epoch",
    ):
        need(value.get(key) == receipt.get(key), f"step-plan certificate {key} mismatch")
    current = _assert_pass(receipt.get("current_pass"), receipt)
    need(value.get("final_pass_id") == current["id"], "step-plan certificate final pass mismatch")
    _id(value.get("final_check_action"), "step-plan certificate final check action")
    _sha(value.get("final_check_sha256"), "step-plan certificate final check digest")
    need(
        isinstance(value.get("audit_head"), str) and _COMMIT_RE.fullmatch(value["audit_head"]),
        "step-plan certificate audit head is invalid",
    )
    need(
        value["audit_head"] == current["git_baseline"],
        "step-plan certificate audit head is not the final-check baseline",
    )
    try:
        readiness = until.decide(
            current_epoch_passes(receipt), open_findings=sorted(open_ids(receipt))
        )
    except until.UntilError as exc:
        raise StepPlanningError(str(exc)) from exc
    need(
        readiness["phase"] == "ready",
        "step-plan certificate lacks two consecutive verified trivial passes",
    )
    return dict(value)
