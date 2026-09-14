"""Bind the derived HTML report to the same transaction as terminal Markdown.

Inputs are already validated protocol state and proposed Markdown writes. This
module never performs a Git operation or writes files itself. A report is a
presentation of evidence, not a second source of workflow state.
"""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import re
from typing import Any

import shiploop_objectives as objectives
import shiploop_store as store


class DeliveryError(ValueError):
    """Terminal evidence cannot safely support the requested report."""


_REPORT_FIXED_INPUTS = frozenset(
    (
        "state.md",
        "history.md",
        "lifecycle.md",
        "backchain/plan.md",
        "quality.md",
        "handoff.md",
        "shiploop-improvements.md",
        "preflight.md",
        "preparation.md",
        "coverage.md",
        "delivery.md",
        "outer-work.md",
    )
)
_PLANNING_DIRECT_INPUTS = frozenset(
    f"{kind}{suffix}.md"
    for kind in ("research", "behavior", "spec")
    for suffix in ("", "-certificate")
)
_PLANNING_ITERATION_DIRECTORY = re.compile(r"^(?:research|behavior|spec)-iterations$")
_PLANNING_ITERATION_NAME = re.compile(r"^[A-Za-z0-9_-]+\.md$")
_SPECIALIST_RECEIPT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,240}\.md$")
_GENERATED_ARTIFACTS = frozenset(("report.html", "report-metadata.md"))


def render_report(root: Path, *, overrides: dict[str, str] | None = None):
    """Load the renderer lazily so active actions do not load reporting code."""
    from shiploop_report import render_report as render

    return render(root, overrides=overrides)


def _normalise_pending_path(value: object) -> str | None:
    """Accept only a portable, direct run-relative write path."""
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return None
    try:
        path = PurePosixPath(value)
    except (TypeError, ValueError):
        return None
    if path.is_absolute() or value != path.as_posix():
        return None
    parts = path.parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        return None
    return "/".join(parts)


def _is_objective_receipt_path(relative: str) -> bool:
    parts = relative.split("/")
    if len(parts) != 2 or parts[0] != "objectives" or not parts[1].endswith(".md"):
        return False
    loop = parts[1][:-3]
    try:
        return objectives.receipt_name(loop) == relative
    except objectives.ObjectiveError:
        return False


def _is_objective_certificate_path(relative: str) -> bool:
    parts = relative.split("/")
    if len(parts) != 3 or parts[0] != "objectives" or parts[2] != "certificate.md":
        return False
    try:
        return objectives.certificate_name(parts[1]) == relative
    except objectives.ObjectiveError:
        return False


def _bound_handoff_certificate(state: dict[str, Any]) -> str | None:
    """Return the single nested certificate that a terminal state may expose."""
    if state.get("delivery_objective_protocol_version") != 1:
        return None
    binding = state.get("objective")
    if not isinstance(binding, dict):
        return None
    loop = binding.get("loop_id")
    try:
        receipt = objectives.receipt_name(loop)
        candidate = objectives.candidate_name(loop)
        certificate = objectives.certificate_name(loop)
    except objectives.ObjectiveError:
        return None
    if not (
        binding.get("kind") == "handoff"
        and binding.get("base_stage") == "handoff"
        and binding.get("status") == "finalized"
        and binding.get("receipt") == receipt
        and binding.get("candidate") == candidate
        and binding.get("certificate") == certificate
    ):
        return None
    return certificate


def _is_report_input_path(relative: str, *, certificate: str | None) -> bool:
    """Return whether the bounded renderer may consume this write-ahead text."""
    if relative in _REPORT_FIXED_INPUTS:
        return True
    parts = relative.split("/")
    if len(parts) == 2:
        directory, filename = parts
        if directory in {"results", "steps", "checks", "check-attempts"}:
            return filename.endswith(".md")
        if directory == "objectives":
            return _is_objective_receipt_path(relative)
        if directory == "step-planning":
            return _SPECIALIST_RECEIPT_NAME.fullmatch(filename) is not None
        if directory == "planning":
            return filename in _PLANNING_DIRECT_INPUTS
    return (
        len(parts) == 3
        and parts[0] == "planning"
        and _PLANNING_ITERATION_DIRECTORY.fullmatch(parts[1]) is not None
        and _PLANNING_ITERATION_NAME.fullmatch(parts[2]) is not None
    ) or (relative == certificate and _is_objective_certificate_path(relative))


def _report_inputs(pending: dict[str, str], state: dict[str, Any]) -> dict[str, str]:
    """Filter the full terminal WAL to renderer inputs without hiding unsafe writes.

    The protocol transaction can contain durable objective internals.  The
    final handoff certificate is an explicit report input; arbitrary nested
    drafts or paths are not silently admitted.  The returned mapping is only
    the render overlay—the caller still commits the full atomic write set.
    """
    selected: dict[str, str] = {}
    certificate = _bound_handoff_certificate(state)
    for raw_relative, text in pending.items():
        relative = _normalise_pending_path(raw_relative)
        if relative is None:
            raise DeliveryError("terminal write path is unsafe")
        if not isinstance(text, str):
            raise DeliveryError(f"terminal write {relative} is not text")
        if relative in _GENERATED_ARTIFACTS:
            continue
        if not _is_report_input_path(relative, certificate=certificate):
            raise DeliveryError(
                f"terminal write is not an accepted report input: {relative}"
            )
        if relative in selected:
            raise DeliveryError(f"duplicate terminal report input: {relative}")
        selected[relative] = text
    return selected


def _report_path(root: Path) -> Path:
    """Refuse links/non-files rather than replace an unrelated report target."""
    path = root / "report.html"
    for current in (path, *path.parents):
        if current.is_symlink():
            raise DeliveryError("report path contains a symlink")
        if current == root:
            break
    if path.exists() and not path.is_file():
        raise DeliveryError("report.html must be a regular file")
    return path


def prepare_terminal_report(
    root: Path, state: dict[str, Any], writes: dict[str, str]
) -> dict[str, str]:
    """Return one atomic write-set; successful terminal state requires evidence.

    The renderer excludes ``state.report`` from its source identity to avoid a
    circular digest. No mutation of ``state`` occurs until rendering succeeds.
    """
    if state.get("stage") not in ("done", "halted"):
        raise DeliveryError("report generation requires a terminal run")
    _report_path(root)
    pending = dict(writes)
    pending["state.md"] = store.dumps(state, "ShipLoop state")
    html, metadata = render_report(root, overrides=_report_inputs(pending, state))
    success = state.get("stage") == "done" and state.get("phase") == "done"
    if success and not (
        metadata.get("outcome") == "complete"
        and metadata.get("evidence_complete") is True
    ):
        reasons = "; ".join(str(item) for item in metadata.get("evidence_errors", []))
        raise DeliveryError("terminal report evidence incomplete: " + (reasons or "unverified outcome"))
    if not success and metadata.get("outcome") == "complete":
        raise DeliveryError("unfinished run cannot produce a complete report")
    state["report"] = {
        "path": "report.html",
        "sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
        "source_digest": metadata["source_digest"],
        "outcome": metadata["outcome"],
        "evidence_complete": metadata["evidence_complete"],
        "schema_version": metadata["schema_version"],
    }
    pending["report.html"] = html
    pending["state.md"] = store.dumps(state, "ShipLoop state")
    return pending


def valid_complete_report(root: Path, state: dict[str, Any]) -> bool:
    """Check terminal status, HTML bytes, and current authoritative sources.

    Fail closed on missing, malformed, stale, or unsafe derived artifacts. This
    verifies consistency with accepted evidence, not semantic correctness.
    """
    if state.get("phase") != "done" or state.get("stage") != "done":
        return False
    record = state.get("report")
    if not isinstance(record, dict) or record.get("path") != "report.html":
        return False
    if record.get("outcome") != "complete" or record.get("evidence_complete") is not True:
        return False
    try:
        if state.get("managed_improve_protocol_version") == 1:
            # The HTML is a bounded projection. Its success gate also checks
            # the exact managed proof bound by the authoritative parent state.
            import shiploop_improve_bridge as improve_bridge

            if improve_bridge.validate_imported_certificate(root, state) is None:
                return False
        path = _report_path(root)
        if hashlib.sha256(path.read_bytes()).hexdigest() != record.get("sha256"):
            return False
        html, metadata = render_report(root)
        return (
            metadata.get("outcome") == "complete"
            and metadata.get("evidence_complete") is True
            and metadata.get("source_digest") == record.get("source_digest")
            and hashlib.sha256(html.encode("utf-8")).hexdigest() == record.get("sha256")
        )
    except (OSError, ValueError, TypeError, KeyError):
        return False
