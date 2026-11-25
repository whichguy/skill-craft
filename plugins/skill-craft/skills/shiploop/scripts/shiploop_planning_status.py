#!/usr/bin/env python3
"""Read-only planning Until Loop observability, experiment inventory, and draft snapshots.

Reads only bounded regular files beneath the run root (and the run's optional
``Plan Improve`` scratch directory) through ``shiploop_observation_io`` and
redacts display strings with ``shiploop_privacy``.  Never mutates product files
or refuses a run's records.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Mapping, Sequence

import shiploop_assumptions as assumptions
import shiploop_loops as loops
import shiploop_observation_io as obs_io
import shiploop_planning_revision as planning_revision
import shiploop_privacy as privacy
import shiploop_store as store

EXPERIMENTS_DIR = "experiments"
SNAPSHOT_RE = re.compile(r"^plan-iter-(\d+)\.md$")
_MAX_EXPERIMENTS = 24
_MAX_SNAPSHOTS = 24
_MAX_SCAN_FILES = 64
_MAX_META_BYTES = 16 * 1024
_MAX_RECEIPT_BYTES = 128 * 1024


def _utc_iso(stamp_ns: int | None) -> str | None:
    if stamp_ns is None:
        return None
    return datetime.fromtimestamp(stamp_ns / 1_000_000_000, timezone.utc).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")


def _clean_text(value: Any, limit: int = 200) -> str:
    if not isinstance(value, str):
        return ""
    line = " ".join(privacy.redact_text(value).split())
    if not line or privacy.sensitive_text(line):
        return "Credential-like text withheld." if privacy.sensitive_text(line) else ""
    return line if len(line) <= limit else line[: limit - 1] + "…"


def _excerpt_decision(text: str, limit: int = 200) -> str:
    cleaned_lines = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                cleaned_lines.append(heading)
            continue
        cleaned_lines.append(stripped)
        if len(" ".join(cleaned_lines)) >= limit:
            break
    return _clean_text(" ".join(cleaned_lines), limit)


def read_loop_state(root: Path, action_id: str | None) -> dict[str, Any] | None:
    """Return bounded redacted status for ``action_id``'s Until Loop receipt, or None."""
    if not isinstance(action_id, str) or not action_id:
        return None
    try:
        raw, mtime_ns = obs_io._read_beneath(root, loops.terminal_path(action_id), _MAX_RECEIPT_BYTES)
        record = json.loads(raw.decode("utf-8"))
    except (FileNotFoundError, obs_io._UnsafeSource, OSError, UnicodeError, ValueError):
        return None
    if not isinstance(record, Mapping):
        return None
    progress = record.get("progress") if isinstance(record.get("progress"), Mapping) else {}
    last_report = record.get("last_report") if isinstance(record.get("last_report"), Mapping) else {}
    number = progress.get("action_number", record.get("action_number"))
    action_number = number if isinstance(number, int) and not isinstance(number, bool) and number > 0 else 1
    status = _clean_text(record.get("status"), 32) or "unknown"
    exit_assessment = _clean_text(last_report.get("exit_assessment") or record.get("exit_assessment"), 32) or None
    classification = _clean_text(last_report.get("classification") or record.get("classification"), 32) or None
    summary = _clean_text(
        last_report.get("handoff") or last_report.get("evidence") or record.get("summary") or progress.get("reason"),
        240,
    )
    updated_at = _clean_text(record.get("at") or record.get("updated_at") or record.get("created_at"), 64) or _utc_iso(mtime_ns)
    return {
        "action_id": action_id,
        "status": status,
        "action_number": action_number,
        "exit_assessment": exit_assessment,
        "classification": classification,
        "summary": summary,
        "updated_at": updated_at,
    }


def _scan_one_experiment(base: Path, rel_dir: str, name: str, *, origin: str) -> dict[str, Any] | None:
    """Inspect one non-symlink experiment sandbox directory safely beneath ``base``."""
    try:
        parts = obs_io._relative_parts(rel_dir)
        fd = obs_io._parent_fd(base, parts)
    except (FileNotFoundError, obs_io._UnsafeSource, OSError):
        return None
    file_count = 0
    nonempty_count = 0
    latest_mtime_ns: int | None = None
    has_meta = False
    has_decision = False
    try:
        with os.scandir(fd) as entries:
            for entry in entries:
                if file_count >= _MAX_SCAN_FILES:
                    break
                try:
                    info = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                if stat.S_ISLNK(info.st_mode):
                    continue
                if stat.S_ISREG(info.st_mode):
                    file_count += 1
                    if info.st_size > 0:
                        nonempty_count += 1
                    latest_mtime_ns = max(latest_mtime_ns or 0, info.st_mtime_ns)
                    if entry.name == "meta.json":
                        has_meta = True
                    elif entry.name == "decision.md":
                        has_decision = True
                elif stat.S_ISDIR(info.st_mode):
                    # Count one shallow subdir level so nested probe outputs still reflect live progress.
                    sub_path = os.path.join(os.fspath(base / rel_dir), entry.name)
                    try:
                        sub_info = os.lstat(sub_path)
                        if not stat.S_ISDIR(sub_info.st_mode) or stat.S_ISLNK(sub_info.st_mode):
                            continue
                        with os.scandir(sub_path) as sub_entries:
                            for sub_entry in sub_entries:
                                if file_count >= _MAX_SCAN_FILES:
                                    break
                                sinfo = sub_entry.stat(follow_symlinks=False)
                                if not stat.S_ISLNK(sinfo.st_mode) and stat.S_ISREG(sinfo.st_mode):
                                    file_count += 1
                                    if sinfo.st_size > 0:
                                        nonempty_count += 1
                                    latest_mtime_ns = max(latest_mtime_ns or 0, sinfo.st_mtime_ns)
                    except OSError:
                        continue
    except OSError:
        return None

    question = None
    hypothesis = ""
    outcome = ""
    plan_changed = None
    explicit_status = ""
    summary = ""
    if has_meta:
        try:
            raw, mtime_ns = obs_io._read_beneath(base, f"{rel_dir}/meta.json", _MAX_META_BYTES)
            meta = json.loads(raw.decode("utf-8"))
            if isinstance(meta, Mapping):
                question = _clean_text(meta.get("question"), 32) or None
                hypothesis = _clean_text(meta.get("hypothesis"), 200)
                outcome = _clean_text(meta.get("outcome") or meta.get("finding"), 200)
                explicit_status = _clean_text(meta.get("status"), 32)
                if isinstance(meta.get("plan_changed"), bool):
                    plan_changed = meta["plan_changed"]
                latest_mtime_ns = max(latest_mtime_ns or 0, mtime_ns)
        except (FileNotFoundError, obs_io._UnsafeSource, OSError, UnicodeError, ValueError):
            pass
    if has_decision:
        try:
            raw, mtime_ns = obs_io._read_beneath(base, f"{rel_dir}/decision.md", _MAX_META_BYTES)
            summary = _excerpt_decision(raw.decode("utf-8", errors="replace"), 200)
            latest_mtime_ns = max(latest_mtime_ns or 0, mtime_ns)
        except (FileNotFoundError, obs_io._UnsafeSource, OSError):
            pass
    if not summary:
        summary = outcome or hypothesis
    derived_status = explicit_status or ("recorded" if (has_decision or has_meta or nonempty_count > 0) else "created")
    return {
        "id": _clean_text(name, 80) or "experiment",
        "origin": origin,
        "relative": f"{rel_dir}/decision.md" if has_decision else rel_dir,
        "status": derived_status,
        "question": question,
        "plan_changed": plan_changed,
        "summary": summary,
        "file_count": file_count,
        "updated_at": _utc_iso(latest_mtime_ns),
    }


def _scan_dir_experiments(base: Path, rel_root: str, *, origin: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    experiments: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    try:
        parts = obs_io._relative_parts(rel_root)
        fd = obs_io._parent_fd(base, parts)
    except (FileNotFoundError, obs_io._UnsafeSource, OSError):
        return experiments, snapshots
    subdirs: list[str] = []
    snap_rows: list[tuple[int, str, int, str | None]] = []
    try:
        with os.scandir(fd) as entries:
            for entry in entries:
                try:
                    info = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                if stat.S_ISLNK(info.st_mode):
                    continue
                if stat.S_ISDIR(info.st_mode) and not entry.name.startswith("."):
                    subdirs.append(entry.name)
                elif stat.S_ISREG(info.st_mode) and origin == "plan":
                    match = SNAPSHOT_RE.fullmatch(entry.name)
                    if match:
                        snap_rows.append((int(match.group(1)), entry.name, info.st_size, _utc_iso(info.st_mtime_ns)))
    except OSError:
        return experiments, snapshots

    for name in sorted(subdirs)[:_MAX_EXPERIMENTS]:
        row = _scan_one_experiment(base, f"{rel_root}/{name}", name, origin=origin)
        if row is not None:
            experiments.append(row)
    for iteration, name, size, updated_at in sorted(snap_rows)[:_MAX_SNAPSHOTS]:
        snapshots.append({
            "iteration": iteration,
            "name": name,
            "relative": f"{rel_root}/{name}",
            "bytes": size,
            "updated_at": updated_at,
        })
    return experiments, snapshots


def scan_experiments(root: Path, state: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Safely inventory ``RUN/experiments/`` sandboxes, ``plan-iter-<n>.md`` snapshots, and ``Plan Improve`` probes."""
    root = Path(root)
    experiments, snapshots = _scan_dir_experiments(root, EXPERIMENTS_DIR, origin="plan")
    repo_text = state.get("repo")
    run_id = state.get("run_id")
    if isinstance(repo_text, str) and repo_text and isinstance(run_id, str) and run_id:
        improve_base = Path(repo_text)
        rel_improve = f".shiploop-improve/.experiments/{run_id}"
        try:
            imp_fd = obs_io._parent_fd(improve_base, obs_io._relative_parts(rel_improve))
        except (FileNotFoundError, obs_io._UnsafeSource, OSError):
            imp_fd = -1
        if imp_fd >= 0:
            imp_children: list[str] = []
            try:
                with os.scandir(imp_fd) as entries:
                    for entry in entries:
                        try:
                            info = entry.stat(follow_symlinks=False)
                        except OSError:
                            continue
                        if not stat.S_ISLNK(info.st_mode) and stat.S_ISDIR(info.st_mode) and not entry.name.startswith("."):
                            imp_children.append(entry.name)
            except OSError:
                imp_children = []
            for action_dir in sorted(imp_children)[:4]:
                sub_exps, _ = _scan_dir_experiments(improve_base, f"{rel_improve}/{action_dir}", origin="Plan Improve")
                experiments.extend(sub_exps)
    return experiments[:_MAX_EXPERIMENTS], snapshots[:_MAX_SNAPSHOTS]


def snapshot_plan_draft(root: Path, action_id: str, draft_path: Path) -> Path | None:
    """Save a non-destructive per-iteration snapshot of the plan draft under ``RUN/experiments/plan-iter-<n>.md``."""
    try:
        draft = Path(draft_path)
        if draft.is_symlink() or not draft.is_file():
            return None
        text = draft.read_text(encoding="utf-8", errors="replace")
        loop_state = read_loop_state(root, action_id)
        iteration = loop_state["action_number"] if loop_state else 1
        target = Path(root) / EXPERIMENTS_DIR / f"plan-iter-{iteration}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        store.atomic_write_text(target, text)
        return target
    except OSError:
        return None


def _question_match(q_id: str, rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    for row in rows:
        if row.get("question") == q_id:
            return row
    pattern = re.compile(rf"\b{re.escape(q_id)}\b")
    for row in rows:
        statement_text = str(row.get("statement") or row.get("assumption") or "")
        if pattern.search(statement_text) or pattern.search(str(row.get("check") or "")):
            return row
    return None


def plan_observability(root: Path | None, state: Mapping[str, Any]) -> dict[str, Any]:
    """Collect a redacted, bounded snapshot of `plan`'s loop, intake experiment questions, experiments, and slices."""
    current = planning_revision.current_actions(state)
    active = state.get("status") == "active"
    active_stage = state.get("stage")
    action_obj = state.get("action") if isinstance(state.get("action"), Mapping) else {}
    active_action = action_obj.get("id")
    improve = state.get("active_improve") if isinstance(state.get("active_improve"), Mapping) else None
    if active_stage == "plan" and isinstance(active_action, str):
        plan_action = active_action
    elif isinstance(improve, Mapping) and improve.get("stage") == "plan" and isinstance(improve.get("action_id"), str):
        plan_action = improve["action_id"]
    else:
        plan_action = current.get((None, "plan"))
    accepted = state.get("accepted") or {}
    plan_result = accepted.get(plan_action) if isinstance(plan_action, str) else None
    plan_accepted = isinstance(plan_result, Mapping)
    draft_result = (
        plan_result
        if plan_accepted
        else (
            improve.get("seed_result")
            if isinstance(improve, Mapping) and improve.get("stage") == "plan"
            and isinstance(improve.get("seed_result"), Mapping)
            else None
        )
    )
    draft_present = isinstance(draft_result, Mapping)

    loop_info = read_loop_state(Path(root), plan_action) if root is not None and isinstance(plan_action, str) else None
    experiments, snapshots = scan_experiments(Path(root), state) if root is not None else ([], [])

    raw_assumptions = (
        draft_result.get("assumptions")
        if draft_present and isinstance(draft_result.get("assumptions"), list)
        else []
    )
    probed_rows: list[dict[str, Any]] = []
    evidenced_count = 0
    open_count = 0
    with_effect = 0
    for row in raw_assumptions:
        if not isinstance(row, Mapping):
            continue
        disp = row.get("disposition")
        if disp == "probed":
            effect = _clean_text(row.get("effect"), 220)
            if effect:
                with_effect += 1
            ev = row.get("evidence")
            probed_rows.append({
                "id": _clean_text(row.get("id"), 32) or "A?",
                "question": _clean_text(row.get("question"), 32) or None,
                "statement": _clean_text(row.get("statement") or row.get("assumption"), 200),
                "check": _clean_text(row.get("check"), 200),
                "effect": effect,
                "evidence_count": len(ev) if isinstance(ev, list) else 0,
            })
        elif disp == "evidenced":
            evidenced_count += 1
        elif disp == "open":
            open_count += 1

    questions_out: list[dict[str, Any]] = []
    for item in assumptions.experiment_questions(state):
        q_id = _clean_text(item.get("id"), 32)
        matched = _question_match(q_id, raw_assumptions) if draft_present else None
        if matched is not None:
            q_status = _clean_text(matched.get("disposition"), 32) or "pending"
            assumption_id = _clean_text(matched.get("id"), 32) or None
            effect = _clean_text(matched.get("effect"), 200)
        else:
            exp_match = next((exp for exp in experiments if exp.get("question") == q_id), None)
            q_status = "probing" if exp_match else "pending"
            assumption_id = None
            effect = exp_match.get("summary", "") if exp_match else ""
        questions_out.append({
            "id": q_id,
            "question": _clean_text(item.get("question"), 220),
            "status": q_status,
            "assumption_id": assumption_id,
            "effect": effect,
        })

    concerns_map = draft_result.get("concerns") if draft_present and isinstance(draft_result.get("concerns"), Mapping) else {}
    raw_items = (
        draft_result.get("work_items")
        if not plan_accepted and draft_present and isinstance(draft_result.get("work_items"), list) and draft_result.get("work_items")
        else state.get("work_items") or ()
    )
    work_items_out: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, Mapping):
            continue
        item_id = _clean_text(item.get("id"), 32)
        item_slice = _clean_text(item.get("slice"), 32) or None
        raw_concerns = concerns_map.get(item.get("id")) if isinstance(concerns_map, Mapping) else None
        concerns_mode = "deferred" if raw_concerns == "deferred" else "mapped" if isinstance(raw_concerns, list) else None
        work_items_out.append({
            "id": item_id,
            "title": _clean_text(item.get("title"), 120),
            "slice": item_slice,
            "concerns_mode": concerns_mode,
        })

    payload = {
        "active": active_stage == "plan" and active,
        "plan_accepted": plan_accepted,
        "plan_action": plan_action if isinstance(plan_action, str) else None,
        "loop": loop_info,
        "experiment_questions": questions_out,
        "experiments": experiments,
        "snapshots": snapshots,
        "assumptions_summary": {
            "total": len(probed_rows) + evidenced_count + open_count,
            "probed": len(probed_rows),
            "evidenced": evidenced_count,
            "open": open_count,
            "with_effect": with_effect,
        },
        "probed_rows": probed_rows,
        "work_items": work_items_out,
    }
    return obs_io.screen(payload)


def fingerprint_digest(observability: Mapping[str, Any]) -> str:
    """Stable hash of live planning state so polling refreshes when loop iterations or sandboxes advance."""
    raw = json.dumps(observability, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def status_lines(observability: Mapping[str, Any]) -> list[str]:
    """Return 0 or 1 concise, path-free, command-free lines for `shiploop status`."""
    if observability.get("active"):
        parts: list[str] = []
        loop_info = observability.get("loop")
        if isinstance(loop_info, Mapping):
            parts.append(f"iter {loop_info.get('action_number', 1)} ({loop_info.get('status', 'active')})")
        experiments = observability.get("experiments") or ()
        if experiments:
            names = ", ".join(str(exp.get("id"))[:24] for exp in experiments[:3])
            more = f" (+{len(experiments) - 3})" if len(experiments) > 3 else ""
            parts.append(f"{len(experiments)} sandbox{'es' if len(experiments) != 1 else ''}: {names}{more}")
        questions = observability.get("experiment_questions") or ()
        if questions:
            qs = ", ".join(str(row.get("id")) for row in questions[:4])
            more_q = f" (+{len(questions) - 4})" if len(questions) > 4 else ""
            parts.append(f"Qs: {qs}{more_q}")
        snapshots = observability.get("snapshots") or ()
        if snapshots:
            parts.append(f"{len(snapshots)} draft snapshot{'s' if len(snapshots) != 1 else ''}")
        if parts:
            return ["Plan loop: " + " · ".join(parts)]
        return []

    if not observability.get("plan_accepted"):
        return []
    loop_info = observability.get("loop")
    summary = observability.get("assumptions_summary") or {}
    probed = int(summary.get("probed") or 0)
    experiments = observability.get("experiments") or ()
    iters = int(loop_info.get("action_number") or 1) if isinstance(loop_info, Mapping) else 1
    parts = []
    if iters > 1:
        parts.append(f"{iters} loop iters")
    if probed or experiments:
        count = probed or len(experiments)
        parts.append(f"{count} experiment{'s' if count != 1 else ''} probed")
    slices = [row.get("slice") for row in observability.get("work_items") or () if row.get("slice")]
    if slices:
        parts.append("slices " + "->".join(str(s) for s in slices[:4]) + ("..." if len(slices) > 4 else ""))
    if parts:
        return ["Plan:      " + " · ".join(parts)]
    return []


__all__ = (
    "EXPERIMENTS_DIR",
    "SNAPSHOT_RE",
    "fingerprint_digest",
    "plan_observability",
    "read_loop_state",
    "scan_experiments",
    "snapshot_plan_draft",
    "status_lines",
)
