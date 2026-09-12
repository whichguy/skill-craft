"""Markdown-backed convergence records for ShipLoop's generic objectives.

The protocol owns Git, locks, commands, and Markdown transactions.  This
module deliberately owns only the durable record rules shared by substantive
outer objectives that do not have a more specific planner.  It has no CLI and
never declares a run successful: two trivial audited passes are merely ready
for the protocol's separate fresh-final-check gate.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import shiploop_store as store
import shiploop_until as until


VERSION = 1
PROTOCOL_VERSION = VERSION
HISTORY_LIMIT = 10
KINDS = (
    "approach",
    "survey",
    "sequence",
    "preparation-readiness",
    "post-inner",
    "coverage",
    "quality",
)
BASE_STAGES = {
    "approach": "approach",
    "survey": "survey",
    "sequence": "sequence",
    "preparation-readiness": "prepare",
    "post-inner": "post-inner",
    "coverage": "coverage",
    "quality": "quality",
}
STAGES = (
    "objective-review",
    "objective-plan",
    "objective-apply",
    "objective-verify",
    "objective-commit",
    "objective-finalize",
)
ASSESSMENT_KEYS = (
    "current_context",
    "implementation",
    "environment",
    "dependencies",
    "flows",
    "edge_conditions",
    "second_order_effects",
    "implicit_requirements",
    "test_strategy",
    "documentation",
)
CONTEXT_KEYS = (
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
FINDING_CATEGORIES = (
    "scope",
    "behavior",
    "implementation",
    "environment",
    "dependency",
    "flow",
    "edge-condition",
    "second-order",
    "implicit-requirement",
    "test",
    "documentation",
    "other",
)
RESULT_KEYS = {
    "objective-review": (
        "summary",
        "findings",
        "assessment",
        "history_assessment",
        "test_review",
        "learnings",
    ),
    "objective-plan": ("summary", "addresses", "body", "learnings"),
    "objective-apply": (
        "summary",
        "candidate",
        "material",
        "addresses",
        "resolutions",
        "test_changes",
        "learnings",
    ),
    "objective-verify": ("summary",),
    "objective-commit": ("summary", "commit"),
    "objective-finalize": ("summary",),
}

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,240}\Z")
_FINDING_RE = re.compile(r"[A-Za-z][A-Za-z0-9._:-]{0,159}\Z")
_SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
_GIT_RE = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")


class ObjectiveError(ValueError):
    """A generic objective receipt or result is not durable enough to advance."""


def need(ok: bool, message: str) -> None:
    if not ok:
        raise ObjectiveError(message)


def _text(value: Any, label: str) -> str:
    need(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty")
    return value.strip()


def _id(value: Any, label: str) -> str:
    need(isinstance(value, str) and _ID_RE.fullmatch(value), f"unsafe {label}")
    return value


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _kind(kind: Any) -> str:
    need(kind in KINDS, "unknown objective kind")
    return kind


def is_current(state: Mapping[str, Any]) -> bool:
    return state.get("objective_protocol_version") == VERSION


def kind_for_base_stage(stage: Any) -> str | None:
    return next((kind for kind, base in BASE_STAGES.items() if base == stage), None)


def is_base_stage(stage: Any) -> bool:
    return kind_for_base_stage(stage) is not None


def is_objective_stage(stage: Any) -> bool:
    return stage in STAGES


def loop_id(run_id: str, kind: str) -> str:
    return f"{_id(run_id, 'run ID')}-{_kind(kind)}-objective"


def receipt_name(loop: str) -> str:
    return f"objectives/{_id(loop, 'objective loop ID')}.md"


def candidate_name(loop: str) -> str:
    return f"objectives/{_id(loop, 'objective loop ID')}/candidate.md"


def pass_name(loop: str, pass_id: str) -> str:
    return f"objectives/{_id(loop, 'objective loop ID')}/passes/{_id(pass_id, 'objective pass ID')}.md"


def abandoned_name(loop: str, pass_id: str) -> str:
    return f"objectives/{_id(loop, 'objective loop ID')}/abandoned/{_id(pass_id, 'objective pass ID')}.md"


def certificate_name(loop: str) -> str:
    return f"objectives/{_id(loop, 'objective loop ID')}/certificate.md"


def history_page_name(loop: str, pass_id: str, skip: int) -> str:
    need(isinstance(skip, int) and skip >= 0, "objective history page skip must be nonnegative")
    return (
        f"objectives/{_id(loop, 'objective loop ID')}/history/"
        f"{_id(pass_id, 'objective pass ID')}-{skip}.md"
    )


def history_index_name(loop: str, pass_id: str, skip: int) -> str:
    """Name an index-only history archive that cannot satisfy review proof."""
    need(isinstance(skip, int) and skip >= 0, "objective history index skip must be nonnegative")
    return (
        f"objectives/{_id(loop, 'objective loop ID')}/history/"
        f"{_id(pass_id, 'objective pass ID')}-{skip}-index.md"
    )


def candidate_identity(body: Any) -> str:
    """Hash exact candidate bytes; whitespace changes are meaningful drift."""
    need(isinstance(body, str) and bool(body.strip()), "objective candidate must be nonempty Markdown")
    return _sha(body.encode("utf-8"))


def _context(context: Any) -> dict[str, str]:
    need(isinstance(context, Mapping), "objective context must be a mapping")
    need(set(context) == set(CONTEXT_KEYS), "objective context keys do not match the contract")
    normalized: dict[str, str] = {}
    for key in CONTEXT_KEYS:
        value = context[key]
        expression = _GIT_RE if key in ("git_baseline", "committed_tree_sha256") else _SHA_RE
        need(isinstance(value, str) and expression.fullmatch(value), f"objective context {key} is invalid")
        normalized[key] = value
    return normalized


def context_sha256(context: Any) -> str:
    return _sha(_canonical(_context(context)))


def _normal_finding(raw: Any) -> dict[str, str]:
    need(isinstance(raw, Mapping), "objective finding must be an object")
    finding_id = raw.get("id")
    need(isinstance(finding_id, str) and _FINDING_RE.fullmatch(finding_id), "objective finding ID must be stable and safe")
    severity = raw.get("severity")
    need(severity in ("material", "trivial"), "objective finding severity must be material or trivial")
    category = raw.get("category")
    need(category in FINDING_CATEGORIES, "objective finding category is unsupported")
    status = raw.get("status", "open")
    need(status in ("open", "resolved"), "objective finding status must be open or resolved")
    normalized = {
        "id": finding_id,
        "severity": severity,
        "category": category,
        "summary": _text(raw.get("summary"), f"objective finding {finding_id} summary"),
        "status": status,
    }
    for key in ("resolution_evidence", "resolved_pass"):
        if key in raw:
            normalized[key] = _text(raw[key], f"objective finding {finding_id} {key}")
    if status == "resolved":
        need(
            "resolution_evidence" in normalized and "resolved_pass" in normalized,
            f"resolved objective finding {finding_id} lacks closure provenance",
        )
    return normalized


def normal_findings(value: Any) -> list[dict[str, str]]:
    need(isinstance(value, list), "objective findings must be a list")
    rows = [_normal_finding(row) for row in value]
    need(len({row["id"] for row in rows}) == len(rows), "objective findings must not duplicate IDs")
    return rows


def ledger_sha256(findings: Any) -> str:
    normalized = normal_findings(findings)
    normalized.sort(key=lambda row: row["id"])
    return _sha(_canonical(normalized))


def identity(receipt: Mapping[str, Any]) -> str:
    candidate = receipt.get("candidate_sha256")
    ledger = receipt.get("ledger_sha256")
    context = receipt.get("context_sha256")
    need(
        all(isinstance(value, str) and _SHA_RE.fullmatch(value) for value in (candidate, ledger, context)),
        "objective receipt identity inputs are invalid",
    )
    return _sha(_canonical({"candidate_sha256": candidate, "ledger_sha256": ledger, "context_sha256": context}))


def _pass_id(loop: str, epoch: int, number: int) -> str:
    need(isinstance(epoch, int) and epoch >= 1, "objective pass epoch must be positive")
    need(isinstance(number, int) and number >= 1, "objective pass number must be positive")
    return f"{loop}-E{epoch}-P{number}"


def _make_pass(receipt: Mapping[str, Any], *, epoch: int, number: int, context: Mapping[str, Any]) -> dict[str, Any]:
    loop = _id(receipt.get("loop_id"), "objective loop ID")
    normalized_context = _context(context)
    return {
        "id": _pass_id(loop, epoch, number),
        "epoch": epoch,
        "number": number,
        "candidate_sha256": receipt["candidate_sha256"],
        "ledger_sha256": receipt["ledger_sha256"],
        "context_sha256": context_sha256(normalized_context),
        **normalized_context,
    }


def new_receipt(
    *,
    loop: str,
    kind: str,
    base_stage: str,
    candidate_body: str,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    loop = _id(loop, "objective loop ID")
    kind = _kind(kind)
    need(BASE_STAGES[kind] == base_stage, "objective kind/base stage mismatch")
    normalized_context = _context(context)
    findings: list[dict[str, str]] = []
    receipt: dict[str, Any] = {
        "version": VERSION,
        "loop_id": loop,
        "kind": kind,
        "base_stage": base_stage,
        "candidate_path": candidate_name(loop),
        "candidate_sha256": candidate_identity(candidate_body),
        "context": normalized_context,
        "context_sha256": context_sha256(normalized_context),
        "findings": findings,
        "ledger_sha256": ledger_sha256(findings),
        "epoch": 1,
        "pass": 1,
        "streak": 0,
        "completed_passes": [],
        "abandoned_passes": [],
        "status": "active",
    }
    receipt["identity_sha256"] = identity(receipt)
    receipt["current_pass"] = _make_pass(receipt, epoch=1, number=1, context=normalized_context)
    return receipt


def _archive_text(row: Mapping[str, Any], *, abandoned: bool = False) -> str:
    return store.dumps(
        dict(row),
        "ShipLoop abandoned objective pass" if abandoned else "ShipLoop completed objective pass",
    )


def _archive_row(root: Path, loop: str, row: Mapping[str, Any], *, abandoned: bool) -> None:
    path = root / (abandoned_name(loop, row["id"]) if abandoned else pass_name(loop, row["id"]))
    need(path.is_file() and not path.is_symlink(), "objective pass archive is missing or unsafe")
    actual = path.read_bytes()
    expected = _archive_text(row, abandoned=abandoned).encode("utf-8")
    need(actual == expected, "objective pass archive differs from its receipt")
    try:
        stored = store.read_record(path)
    except (store.StorageError, OSError) as exc:
        raise ObjectiveError(f"objective pass archive is unreadable: {exc}") from exc
    need(stored == dict(row), "objective pass archive is not semantically equal to its receipt")


def _cursor_before(row: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    return (int(row["epoch"]), int(row["number"])) < (int(current["epoch"]), int(current["number"]))


def _assert_pass_shape(receipt: Mapping[str, Any], row: Any, *, completed: bool) -> dict[str, Any]:
    need(isinstance(row, Mapping), "objective pass must be an object")
    epoch, number = row.get("epoch"), row.get("number")
    need(isinstance(epoch, int) and epoch >= 1 and isinstance(number, int) and number >= 1, "objective pass cursor is invalid")
    expected_id = _pass_id(receipt["loop_id"], epoch, number)
    need(row.get("id") == expected_id, "objective pass ID does not match its cursor")
    for key in ("candidate_sha256", "ledger_sha256", "context_sha256"):
        need(isinstance(row.get(key), str) and _SHA_RE.fullmatch(row[key]), f"objective pass {key} is invalid")
    for key in CONTEXT_KEYS:
        expression = _GIT_RE if key in ("git_baseline", "committed_tree_sha256") else _SHA_RE
        need(isinstance(row.get(key), str) and expression.fullmatch(row[key]), f"objective pass {key} is invalid")
    if completed:
        need(row.get("status") == "completed", "completed objective pass lacks status")
        need(row.get("verified") is True, "completed objective pass is not verified")
        need(row.get("outcome") in ("material", "trivial"), "completed objective pass outcome is invalid")
        need(isinstance(row.get("commit"), str) and _GIT_RE.fullmatch(row["commit"]), "completed objective pass commit is invalid")
    else:
        need(row.get("status") == "abandoned", "abandoned objective pass lacks status")
        _text(row.get("reason"), "abandoned objective pass reason")
    return dict(row)


def _assert_receipt_shape(receipt: Any) -> dict[str, Any]:
    need(isinstance(receipt, Mapping), "objective receipt must be an object")
    need(receipt.get("version") == VERSION, "unsupported objective receipt")
    loop = _id(receipt.get("loop_id"), "objective loop ID")
    kind = _kind(receipt.get("kind"))
    need(receipt.get("base_stage") == BASE_STAGES[kind], "objective receipt base stage mismatch")
    need(receipt.get("candidate_path") == candidate_name(loop), "objective candidate path is invalid")
    need(isinstance(receipt.get("candidate_sha256"), str) and _SHA_RE.fullmatch(receipt["candidate_sha256"]), "objective candidate digest is invalid")
    context = _context(receipt.get("context"))
    need(receipt.get("context_sha256") == context_sha256(context), "objective context digest mismatch")
    findings = normal_findings(receipt.get("findings"))
    need(receipt.get("ledger_sha256") == ledger_sha256(findings), "objective ledger digest mismatch")
    need(receipt.get("identity_sha256") == identity(receipt), "objective receipt identity mismatch")
    need(isinstance(receipt.get("epoch"), int) and receipt["epoch"] >= 1, "objective receipt epoch is invalid")
    need(isinstance(receipt.get("pass"), int) and receipt["pass"] >= 1, "objective receipt pass is invalid")
    need(isinstance(receipt.get("streak"), int) and receipt["streak"] >= 0, "objective receipt streak is invalid")
    need(receipt.get("status") in ("active", "finalized", "abandoned"), "objective receipt status is invalid")
    # Current passes intentionally have no status until archived.  Validate the
    # common cursor/context portion independently rather than treating them as
    # archived records.
    current = receipt.get("current_pass")
    need(isinstance(current, Mapping), "objective current pass is missing")
    expected_current = _pass_id(loop, receipt["epoch"], receipt["pass"])
    need(current.get("id") == expected_current, "objective current pass ID does not match receipt cursor")
    need(current.get("epoch") == receipt["epoch"] and current.get("number") == receipt["pass"], "objective current pass cursor is stale")
    for key in ("candidate_sha256", "ledger_sha256", "context_sha256"):
        need(current.get(key) == receipt.get(key), f"objective current pass {key} is stale")
    for key in CONTEXT_KEYS:
        need(key in current, f"objective current pass lacks {key}")
    _context({key: current[key] for key in CONTEXT_KEYS})
    need(current.get("context_sha256") == context_sha256({key: current[key] for key in CONTEXT_KEYS}), "objective current pass context digest is stale")
    for key in ("completed_passes", "abandoned_passes"):
        need(isinstance(receipt.get(key), list), f"objective {key} must be a list")
    seen_ids: set[str] = set()
    seen_commits: set[str] = set()
    for row in receipt["completed_passes"]:
        row = _assert_pass_shape(receipt, row, completed=True)
        need(row["id"] not in seen_ids and row["commit"] not in seen_commits, "objective archived passes are duplicated")
        need(_cursor_before(row, current), "completed objective pass must precede the current cursor")
        seen_ids.add(row["id"])
        seen_commits.add(row["commit"])
    for row in receipt["abandoned_passes"]:
        row = _assert_pass_shape(receipt, row, completed=False)
        need(row["id"] not in seen_ids, "objective archived pass IDs are duplicated")
        need(_cursor_before(row, current), "abandoned objective pass must precede the current cursor")
        seen_ids.add(row["id"])
    return dict(receipt)


def assert_receipt(root: Path, receipt: Any) -> dict[str, Any]:
    """Validate exact candidate bytes plus immutable Markdown pass archives."""
    normalized = _assert_receipt_shape(receipt)
    candidate = root / normalized["candidate_path"]
    need(candidate.is_file() and not candidate.is_symlink(), "objective candidate is missing or unsafe")
    need(candidate_identity(candidate.read_bytes().decode("utf-8")) == normalized["candidate_sha256"], "objective candidate changed outside the supported apply path")
    for row in normalized["completed_passes"]:
        _archive_row(root, normalized["loop_id"], row, abandoned=False)
    for row in normalized["abandoned_passes"]:
        _archive_row(root, normalized["loop_id"], row, abandoned=True)
    return normalized


def _sync_identity(receipt: dict[str, Any]) -> None:
    receipt["ledger_sha256"] = ledger_sha256(receipt["findings"])
    receipt["context_sha256"] = context_sha256(receipt["context"])
    receipt["identity_sha256"] = identity(receipt)
    current = receipt["current_pass"]
    current["candidate_sha256"] = receipt["candidate_sha256"]
    current["ledger_sha256"] = receipt["ledger_sha256"]
    current["context_sha256"] = receipt["context_sha256"]


def open_ids(receipt: Mapping[str, Any]) -> set[str]:
    return {row["id"] for row in normal_findings(receipt.get("findings")) if row["status"] == "open"}


def open_material_ids(receipt: Mapping[str, Any]) -> list[str]:
    return sorted(row["id"] for row in normal_findings(receipt.get("findings")) if row["status"] == "open" and row["severity"] == "material")


def all_clear(receipt: Mapping[str, Any]) -> bool:
    return not open_ids(receipt)


def apply_review(receipt: dict[str, Any], findings: Any) -> list[dict[str, str]]:
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
        need(not (old["severity"] == "material" and row["severity"] == "trivial"), f"objective finding {row['id']} severity cannot be silently downgraded")
        need(old["category"] == row["category"], f"objective finding {row['id']} category cannot change across passes")
        reopened = dict(row, status="open")
        reopened.pop("resolution_evidence", None)
        reopened.pop("resolved_pass", None)
        by_id[row["id"]] = reopened
    receipt["findings"] = [by_id[finding_id] for finding_id in order]
    _sync_identity(receipt)
    return normal_findings(receipt["findings"])


def check_assessment(value: Any) -> dict[str, str]:
    need(isinstance(value, Mapping), "objective assessment must be a mapping")
    need(set(value) == set(ASSESSMENT_KEYS), "objective assessment keys do not match the required rubric")
    return {key: _text(value[key], f"objective assessment {key}") for key in ASSESSMENT_KEYS}


def record_history(
    receipt: dict[str, Any],
    rows: Any,
    *,
    head: str,
    skip: int,
    archive_path: str | None = None,
    archive_sha256: str | None = None,
) -> dict[str, Any]:
    need(isinstance(rows, list) and rows, "objective history page must be nonempty")
    need(isinstance(skip, int) and skip >= 0, "objective history skip must be nonnegative")
    need(isinstance(head, str) and _GIT_RE.fullmatch(head), "objective history head is invalid")
    commits: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        need(isinstance(row, Mapping), "objective history row must be an object")
        sha = row.get("sha")
        body = row.get("body")
        need(isinstance(sha, str) and _GIT_RE.fullmatch(sha), "objective history SHA is invalid")
        need(isinstance(body, str) and bool(body.strip()), "objective history requires a complete nonempty commit body")
        need(sha not in seen, "objective history page repeats a commit")
        seen.add(sha)
        commits.append({"sha": sha, "body_sha256": _sha(body.encode("utf-8"))})
    page = {
        "skip": skip,
        "count": len(commits),
        "commits": commits,
        "page_sha256": _sha(_canonical(commits)),
    }
    if archive_path is not None or archive_sha256 is not None:
        need(
            isinstance(archive_path, str)
            and archive_path
            and isinstance(archive_sha256, str)
            and _SHA_RE.fullmatch(archive_sha256),
            "objective history archive binding is invalid",
        )
        page["archive_path"] = archive_path
        page["archive_sha256"] = archive_sha256
    current = receipt["current_pass"]
    prior = current.get("history")
    pages = [] if not isinstance(prior, Mapping) or prior.get("head") != head else list(prior.get("pages", []))
    pages = [item for item in pages if item.get("skip") != skip]
    pages.append(page)
    pages.sort(key=lambda item: item["skip"])
    current["history"] = {"head": head, "required_limit": HISTORY_LIMIT, "pages": pages}
    return page


def assert_history(receipt: Mapping[str, Any], rows: Any, *, head: str) -> None:
    need(isinstance(rows, list), "objective current Git history must be a list")
    current = receipt.get("current_pass")
    need(isinstance(current, Mapping), "objective current pass is missing")
    history = current.get("history")
    need(isinstance(history, Mapping) and history.get("head") == head, "read current Git history with shiploop history before objective review")
    need(history.get("required_limit") == HISTORY_LIMIT, "objective history did not record the required last ten full commit bodies")
    pages = history.get("pages")
    need(isinstance(pages, list) and pages, "objective history has no durable page receipt")
    recorded: dict[str, str] = {}
    for page in pages:
        need(isinstance(page, Mapping) and isinstance(page.get("commits"), list), "objective history page receipt is malformed")
        expected_digest = _sha(_canonical(page["commits"]))
        need(page.get("page_sha256") == expected_digest, "objective history page digest is stale")
        for item in page["commits"]:
            need(isinstance(item, Mapping), "objective history page commit is malformed")
            sha, body_digest = item.get("sha"), item.get("body_sha256")
            need(isinstance(sha, str) and _GIT_RE.fullmatch(sha) and isinstance(body_digest, str) and _SHA_RE.fullmatch(body_digest), "objective history receipt has invalid commit body evidence")
            recorded[sha] = body_digest
    for row in rows:
        need(isinstance(row, Mapping), "objective current Git history row is malformed")
        sha, body = row.get("sha"), row.get("body")
        need(isinstance(sha, str) and _GIT_RE.fullmatch(sha) and isinstance(body, str) and body.strip(), "objective review requires full current commit bodies")
        need(recorded.get(sha) == _sha(body.encode("utf-8")), "objective history receipt does not cover the current full commit body")


def check_addresses(receipt: Mapping[str, Any], value: Any) -> list[str]:
    need(isinstance(value, list) and all(isinstance(item, str) for item in value), "objective addresses must be a list of finding IDs")
    expected = open_ids(receipt)
    actual = set(value)
    need(len(actual) == len(value), "objective addresses must not duplicate IDs")
    need(actual == expected, "objective plan must address every open finding and no other IDs")
    return sorted(actual)


def resolve_findings(receipt: dict[str, Any], resolutions: Any, addresses: Any) -> list[str]:
    addressed = check_addresses(receipt, addresses)
    need(isinstance(resolutions, list), "objective resolutions must be a list")
    rows: dict[str, str] = {}
    for row in resolutions:
        need(isinstance(row, Mapping), "objective resolution must be an object")
        finding_id = row.get("id")
        need(isinstance(finding_id, str) and finding_id in addressed, "objective resolution refers to an unaddressed finding")
        need(finding_id not in rows, "objective resolutions must not duplicate IDs")
        rows[finding_id] = _text(row.get("evidence"), f"objective resolution {finding_id} evidence")
    need(set(rows) == set(addressed), "objective apply requires concrete evidence for every addressed finding")
    current_id = receipt["current_pass"]["id"]
    updated = []
    for finding in normal_findings(receipt["findings"]):
        item = dict(finding)
        if item["id"] in rows:
            item.update(status="resolved", resolution_evidence=rows[item["id"]], resolved_pass=current_id)
        updated.append(item)
    receipt["findings"] = updated
    _sync_identity(receipt)
    return addressed


def replace_candidate(receipt: dict[str, Any], body: Any) -> str:
    digest = candidate_identity(body)
    receipt["candidate_sha256"] = digest
    _sync_identity(receipt)
    return digest


def complete_pass(receipt: dict[str, Any], *, commit: str, outcome: str) -> dict[str, Any]:
    need(outcome in ("material", "trivial"), "objective pass outcome must be material or trivial")
    need(isinstance(commit, str) and _GIT_RE.fullmatch(commit), "objective audit commit must be a full SHA")
    current = receipt["current_pass"]
    need("review" in current and "plan" in current and "apply" in current, "objective pass lacks review, plan, or apply evidence")
    completed = dict(current)
    completed.update(
        status="completed",
        verified=True,
        outcome=outcome,
        commit=commit,
        candidate_sha256=receipt["candidate_sha256"],
        ledger_sha256=receipt["ledger_sha256"],
        context_sha256=receipt["context_sha256"],
    )
    need(not any(row.get("id") == completed["id"] or row.get("commit") == commit for row in receipt["completed_passes"]), "objective pass or audit commit already exists")
    receipt["completed_passes"].append(completed)
    decision = decide(receipt)
    receipt["streak"] = decision["trivial_streak"]
    return completed


def start_next_pass(receipt: dict[str, Any], *, context: Mapping[str, Any]) -> dict[str, Any]:
    need(receipt.get("status") == "active", "cannot start a pass for a finalized objective receipt")
    receipt["pass"] = int(receipt["pass"]) + 1
    receipt["context"] = _context(context)
    _sync_identity(receipt)
    receipt["current_pass"] = _make_pass(receipt, epoch=receipt["epoch"], number=receipt["pass"], context=receipt["context"])
    return receipt["current_pass"]


def abandon_current(receipt: dict[str, Any], *, reason: str, context: Mapping[str, Any]) -> dict[str, Any]:
    current = dict(receipt["current_pass"])
    current.update(status="abandoned", reason=_text(reason, "objective repair reason"))
    receipt["abandoned_passes"].append(current)
    receipt["epoch"] = int(receipt["epoch"]) + 1
    receipt["pass"] = 1
    receipt["streak"] = 0
    receipt["context"] = _context(context)
    _sync_identity(receipt)
    receipt["current_pass"] = _make_pass(receipt, epoch=receipt["epoch"], number=1, context=receipt["context"])
    return current


def abandon_objective(
    receipt: dict[str, Any], *, reason: str, context: Mapping[str, Any]
) -> dict[str, Any]:
    """Archive the active pass and permanently prevent this loop from certifying."""
    need(receipt.get("status") == "active", "only an active objective can be abandoned")
    archived = abandon_current(receipt, reason=reason, context=context)
    receipt["status"] = "abandoned"
    return archived


def decide(receipt: Mapping[str, Any]) -> dict[str, Any]:
    current_epoch = receipt.get("epoch")
    passes = [row for row in receipt.get("completed_passes", []) if row.get("epoch") == current_epoch]
    try:
        return until.decide(passes, open_findings=sorted(open_ids(receipt)))
    except until.UntilError as exc:
        raise ObjectiveError(str(exc)) from exc


def certificate(receipt: Mapping[str, Any], *, final_check_action: str, final_check_sha256: str, audit_head: str) -> dict[str, Any]:
    decision = decide(receipt)
    need(decision["phase"] == "ready" and all_clear(receipt), "objective certificate requires two verified trivial passes and no open findings")
    need(isinstance(final_check_action, str) and final_check_action.strip(), "objective final check action is required")
    need(isinstance(final_check_sha256, str) and _SHA_RE.fullmatch(final_check_sha256), "objective final check digest is invalid")
    need(isinstance(audit_head, str) and _GIT_RE.fullmatch(audit_head), "objective certificate audit head is invalid")
    return {
        "version": VERSION,
        "loop_id": receipt["loop_id"],
        "kind": receipt["kind"],
        "base_stage": receipt["base_stage"],
        "candidate_sha256": receipt["candidate_sha256"],
        "ledger_sha256": receipt["ledger_sha256"],
        "context_sha256": receipt["context_sha256"],
        "identity_sha256": receipt["identity_sha256"],
        "final_check_action": final_check_action,
        "final_check_sha256": final_check_sha256,
        "audit_head": audit_head,
        "trivial_streak": decision["trivial_streak"],
    }


def assert_certificate(receipt: Mapping[str, Any], value: Any) -> dict[str, Any]:
    """Validate a finalized objective certificate against its receipt only."""
    normalized = _assert_receipt_shape(receipt)
    need(normalized.get("status") == "finalized", "objective certificate requires a finalized receipt")
    need(isinstance(value, Mapping), "objective certificate must be an object")
    certificate_value = dict(value)
    need(certificate_value.get("version") == VERSION, "unsupported objective certificate")
    for key in (
        "loop_id",
        "kind",
        "base_stage",
        "candidate_sha256",
        "ledger_sha256",
        "context_sha256",
        "identity_sha256",
    ):
        need(
            certificate_value.get(key) == normalized.get(key),
            f"objective certificate {key} mismatch",
        )
    _text(certificate_value.get("final_check_action"), "objective certificate final check action")
    need(
        isinstance(certificate_value.get("final_check_sha256"), str)
        and _SHA_RE.fullmatch(certificate_value["final_check_sha256"]),
        "objective certificate final check digest is invalid",
    )
    need(
        isinstance(certificate_value.get("audit_head"), str)
        and _GIT_RE.fullmatch(certificate_value["audit_head"]),
        "objective certificate audit head is invalid",
    )
    decision = decide(normalized)
    need(
        decision["phase"] == "ready"
        and all_clear(normalized)
        and certificate_value.get("trivial_streak") == decision["trivial_streak"],
        "objective certificate lacks two verified trivial passes",
    )
    return certificate_value
