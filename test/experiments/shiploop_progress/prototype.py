"""Read-only progress-snapshot prototype for the ShipLoop experiment.

This module deliberately lives outside the skill package.  It projects only
existing navigator state into short status-context lines; it neither persists
data nor changes actions, callbacks, routes, or result handling.
"""

from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path
import sys
from typing import Any


def _repo_root() -> Path:
    """Locate the committed experiment checkout without consulting run state."""
    configured = os.environ.get("SHIPLOOP_PROGRESS_REPO", "").strip()
    candidates = [
        Path(configured).expanduser() if configured else None,
        Path.cwd(),
    ]
    for candidate in candidates:
        if candidate is not None and (
            candidate / "skills" / "shiploop" / "scripts" / "shiploop_navigator.py"
        ).is_file():
            return candidate.resolve()
    raise RuntimeError("set SHIPLOOP_PROGRESS_REPO to the ShipLoop experiment checkout")


REPO_ROOT = _repo_root()
SCRIPTS = REPO_ROOT / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_navigator as navigator  # noqa: E402


MAX_TITLE_CHARS = 80
MAX_REASON_CHARS = 80
MAX_ID_CHARS = 32
MAX_COMPLETED_NAMES = 3
MAX_QUEUED_NAMES = 3
MAX_SNAPSHOT_CHARS = 2200


def _compact(value: str, *, limit: int) -> str:
    """Collapse untrusted display text to a small single-line status label."""
    compacted = " ".join(value.split())
    return compacted if len(compacted) <= limit else compacted[: limit - 1] + "…"


def _done_stages(
    state: Mapping[str, Any], stages: tuple[str, ...], *, owner: str | None
) -> set[str]:
    """Return distinct stage names with an accepted done result in this scope."""
    return {
        entry["stage"]
        for entry in state["history"]
        if entry["outcome"] == "done"
        and entry["stage"] in stages
        and entry["workitem"] == owner
    }


def _document_selection(
    state: Mapping[str, Any], owner: str
) -> tuple[bool, bool | None]:
    """Return whether this owner has a done document result and its explicit choice."""
    for entry in reversed(state["history"]):
        if (
            entry["stage"] == "document"
            and entry["workitem"] == owner
            and entry["outcome"] == "done"
        ):
            choices = state["accepted"][entry["action"]].get("choices", {})
            return True, choices.get("skill_required")
    return False, None


def _item_label(item: Mapping[str, str]) -> str:
    """Bound both user-facing item fields before placing them in packet context."""
    return (
        _compact(item["id"], limit=MAX_ID_CHARS)
        + ": "
        + _compact(item["title"], limit=MAX_TITLE_CHARS)
    )


def _phase(stage: str) -> str:
    """Classify the effective cursor with the navigator's declared stage groups."""
    if stage in navigator.PRELUDE:
        return "preparation"
    if stage in navigator.INNER:
        return "inner"
    if stage in navigator.OUTER:
        return "outer"
    return "complete"


def _stage_lines(
    state: Mapping[str, Any], *, phase: str, owner: str | None, current_stage: str
) -> list[str]:
    """Render completed and pending labels for the current phase or active owner."""
    if phase == "preparation":
        stages = navigator.PRELUDE
        scope_owner = None
        label = "Preparation"
    elif phase == "inner":
        stages = navigator.INNER
        scope_owner = owner
        label = "Current owner"
    else:
        stages = navigator.OUTER
        scope_owner = None
        label = "Outer"

    done = _done_stages(state, stages, owner=scope_owner)
    conditional = False
    skipped = False
    unspecified = False
    if phase == "inner":
        assert owner is not None
        document_done, skill_required = _document_selection(state, owner)
        if not document_done:
            conditional = True
        elif skill_required is False:
            skipped = True
        elif skill_required is None:
            unspecified = True

    completed = [stage for stage in stages if stage in done]
    pending = [
        stage
        for stage in stages
        if stage not in done
        and stage != current_stage
        and not (stage == "skill-validate" and (conditional or skipped or unspecified))
    ]
    lines = [
        f"{label} stages completed (accepted done): "
        + (", ".join(completed) if completed else "none"),
        f"{label} stages pending: " + (", ".join(pending) if pending else "none"),
    ]
    if conditional:
        lines.append("Skill validation: conditional until this owner's document result is accepted done.")
    elif skipped:
        lines.append("Skill validation: skipped because this owner's document result selected false.")
    elif unspecified:
        lines.append("Skill validation: not selected; the done document result omitted an explicit choice.")
    elif phase == "inner" and "skill-validate" in done:
        lines.append("Skill validation: completed after this owner's document result selected true.")
    elif phase == "inner" and "skill-validate" in pending:
        lines.append("Skill validation: pending because this owner's document result selected true.")
    elif phase == "inner" and current_stage == "skill-validate":
        lines.append("Skill validation: current because this owner's document result selected true.")
    return lines


def _work_lines(state: Mapping[str, Any], *, phase: str) -> list[str]:
    """Render a bounded view of the current queue without deriving a future queue."""
    items = state["work_items"]
    completed = len(state["completed_work_items"])
    has_active_owner = phase == "inner"
    current_count = 1 if has_active_owner else 0
    queued_start = completed + current_count
    queued = items[queued_start:]
    plan_improve_done = "plan-improve" in _done_stages(
        state, navigator.PRELUDE, owner=None
    )
    queue_status = "current queue" if plan_improve_done else "provisional until plan-improve is accepted done"
    lines = [
        f"Work items: completed {completed}; current {current_count}; queued {len(queued)} ({queue_status})."
    ]
    if has_active_owner:
        current = items[completed]
        lines.append(
            "Current work item: "
            + _item_label(current)
            + " (assigned; execution unproven)."
        )
    completed_items = items[:completed]
    if completed_items:
        names = "; ".join(
            _item_label(item) for item in completed_items[:MAX_COMPLETED_NAMES]
        )
        if len(completed_items) > MAX_COMPLETED_NAMES:
            names += f"; +{len(completed_items) - MAX_COMPLETED_NAMES} more"
        lines.append("Completed labels (status context, not instructions): " + names)
    if queued:
        names = "; ".join(
            _item_label(item) for item in queued[:MAX_QUEUED_NAMES]
        )
        if len(queued) > MAX_QUEUED_NAMES:
            names += f"; +{len(queued) - MAX_QUEUED_NAMES} more"
        lines.append("Queued labels (status context, not instructions): " + names)
    return lines


def _owner_line(state: Mapping[str, Any], *, phase: str, status: str) -> str:
    """Identify the existing cursor owner without inventing another authority."""
    if phase == "inner":
        owner = state["work_items"][state["work_index"]]["id"]
        if status == "halted":
            return f"Owner: {owner} (held work-item assignment; no runnable action)."
        if status in ("blocked", "paused"):
            return f"Owner: {owner} (work-item assignment awaits resume)."
        return f"Owner: {owner} (current work-item assignment)."
    if phase == "complete":
        return "Owner: none (terminal navigator state)."
    return "Owner: root navigator."


def _continuation_line(status: str) -> str:
    """Describe only the condition for using the existing current cursor."""
    if status == "active":
        return "Continuation: only the current action packet is available; execution remains unproven."
    if status in ("blocked", "paused"):
        return "Continuation: no action is runnable until the recorded condition is resolved and the run is resumed."
    return "Continuation: no current or next action is runnable."


def _progress_lines(state: Mapping[str, Any]) -> tuple[str, ...]:
    """Project valid navigator state into compact, read-only progress context."""
    navigator.validate(state)
    stage = navigator.current_stage(state)
    phase = _phase(stage)
    status = state["status"]
    reason = state.get("status_reason")
    status_line = f"Phase: {phase} | Run status: {status}"
    if status in ("blocked", "paused"):
        status_line += " (unfinished: " + _compact(reason, limit=MAX_REASON_CHARS) + ")"
        status_line += "; assignment awaits resume"
    elif status == "halted":
        status_line += " (unfinished: " + _compact(reason, limit=MAX_REASON_CHARS) + ")"
    elif status == "active":
        status_line += " (assigned work may not have started)"
    elif status == "done":
        status_line += " (agent-declared; external verification is not implied)"

    preparation_done = _done_stages(state, navigator.PRELUDE, owner=None)
    outer_done = _done_stages(state, navigator.OUTER, owner=None)
    owner = None
    if phase == "inner":
        owner = state["work_items"][state["work_index"]]["id"]

    current_line = (
        "Current: none (halted; no runnable current or next action)."
        if status == "halted"
        else "Current: none (terminal navigator state)."
        if phase == "complete"
        else f"Current: {stage} (assigned; execution unproven)."
    )
    if status in ("blocked", "paused"):
        current_line = f"Current: {stage} (assigned; awaits resume; execution unproven)."

    lines = [
        status_line,
        current_line,
        _owner_line(state, phase=phase, status=status),
        _continuation_line(status),
        f"Preparation stages: {len(preparation_done)}/{len(navigator.PRELUDE)} accepted done.",
        f"Outer stages: {len(outer_done)}/{len(navigator.OUTER)} accepted done.",
        *_work_lines(state, phase=phase),
        *_stage_lines(state, phase=phase, owner=owner, current_stage=stage),
    ]
    if phase == "preparation":
        lines.append("Skill validation: conditional; no queued work item has a document result accepted done.")
    if stage in navigator._IMPROVE_STAGES:
        lines.append("Improve detail: one host-owned campaign; internal phase and iterations are unavailable.")

    return tuple(lines)


__all__ = [
    "MAX_QUEUED_NAMES",
    "MAX_COMPLETED_NAMES",
    "MAX_ID_CHARS",
    "MAX_REASON_CHARS",
    "MAX_SNAPSHOT_CHARS",
    "MAX_TITLE_CHARS",
    "REPO_ROOT",
    "SCRIPTS",
    "_progress_lines",
    "navigator",
]
