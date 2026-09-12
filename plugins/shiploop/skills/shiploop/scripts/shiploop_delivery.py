"""Bind the derived HTML report to the same transaction as terminal Markdown.

Inputs are already validated protocol state and proposed Markdown writes. This
module never performs a Git operation or writes files itself. A report is a
presentation of evidence, not a second source of workflow state.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import shiploop_store as store


class DeliveryError(ValueError):
    """Terminal evidence cannot safely support the requested report."""


def render_report(root: Path, *, overrides: dict[str, str] | None = None):
    """Load the renderer lazily so active actions do not load reporting code."""
    from shiploop_report import render_report as render

    return render(root, overrides=overrides)


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
    html, metadata = render_report(root, overrides=pending)
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
