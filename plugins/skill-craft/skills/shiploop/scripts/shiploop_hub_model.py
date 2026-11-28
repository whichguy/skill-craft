"""Read-only rich story, transition, gate, and artifact projection for the ShipLoop Multi-Run Hub.

Never acquires an exclusive lock, recovers pending transactions, or mutates any
run or repository file.  All untrusted run/repo text is bounded and screened
with ``shiploop_privacy`` and ``shiploop_observation_io.screen``.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
from typing import Any, Iterable, Mapping, Sequence

import shiploop_defaults as defaults
import shiploop_follow_on as follow_on
import shiploop_navigator as navigator
import shiploop_observation_io as obs_io
import shiploop_privacy as privacy
import shiploop_progress as progress
import shiploop_progress_data as progress_data
import shiploop_stage_spec as stage_spec
import shiploop_store as store
import shiploop_story as story_data
import shiploop_testing_status as testing_status
import shiploop_trace as trace_mod
import shiploop_unverified as unverified

SCHEMA = "shiploop-hub-detail/v1"
_MAX_ARTIFACT_BYTES = 256 * 1024
_MAX_SMALL_RECORD_BYTES = 128 * 1024
_RUN_ARTIFACT_PREFIXES = (
    "packets/",
    "results/",
    "tests/",
    "checks/",
    "expectations/",
    "notes/",
    "improve/",
    "experiments/",
    "decisions/",
    "owner-notes/",
    "loops/",
    "lint/",
    "fields/",
    "commits/",
)
_RUN_ARTIFACT_EXACT = frozenset((
    "request.md",
    "follow-on-request.md",
    "status.md",
    "context-index.md",
))
_REPO_DOC_EXACT = frozenset((
    "docs/shiploop/spec.md",
    "docs/ARCHITECTURE.md",
    "ARCHITECTURE.md",
    "docs/architecture.md",
    "docs/shiploop/architecture.md",
))


def _clean_text(value: Any, limit: int = 240) -> str:
    return privacy.clean_display_text(value, limit)


def _clean_multiline(value: Any, limit: int = 4000) -> str:
    if not isinstance(value, str):
        return ""
    text = privacy.redact_text(value)
    if privacy.sensitive_text(text):
        return "Credential-like text withheld."
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _first_sentence(value: Any, limit: int = 180) -> str:
    text = _clean_text(value, limit * 2)
    if not text:
        return ""
    head = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0]
    return head if len(head) <= limit else head[: limit - 1] + "…"


def _stat_entry(path: Path) -> tuple[Any, ...]:
    return progress._stat_entry(path)


def _dir_entries_sig(folder: Path, limit: int = 64) -> list[tuple[Any, ...]]:
    entries: list[tuple[Any, ...]] = [_stat_entry(folder)]
    try:
        if folder.is_dir() and not folder.is_symlink():
            for idx, child in enumerate(sorted(folder.iterdir())):
                if idx >= limit:
                    break
                if not child.is_symlink():
                    entries.append(_stat_entry(child))
    except OSError:
        pass
    return entries


def detail_watch_signature(
    run_dir: Path,
    state: Mapping[str, Any],
    entry: Mapping[str, Any] | None = None,
) -> tuple[Any, ...]:
    """Stat-only signature covering every artifact and live metadata displayed in the Hub run detail workspace."""
    parts: list[Any] = [
        state.get("revision"),
        state.get("status"),
        state.get("stage"),
        state.get("work_index"),
        progress._watch_signature(run_dir),
    ]
    if entry is not None:
        parts.append((
            entry.get("host"),
            entry.get("model"),
            entry.get("effort"),
            entry.get("owner_alive"),
        ))
    for folder_name in ("commits", "decisions", "lint"):
        parts.extend(_dir_entries_sig(run_dir / folder_name))
    child = state.get("active_improve")
    if isinstance(child, Mapping) and child.get("skill"):
        try:
            import shiploop_standalone_improve as standalone
            receipt_path = standalone.receipt_path(child)
            parts.extend(_dir_entries_sig(receipt_path.parent, limit=32))
        except Exception:  # noqa: BLE001
            pass
    return tuple(parts)


def detail_version_digest(sig: tuple[Any, ...]) -> str:
    """Short deterministic version string for a watch signature."""
    raw = json.dumps(sig, default=str, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _read_text_safe(base: Path, relative: str, limit: int = _MAX_SMALL_RECORD_BYTES) -> str | None:
    try:
        raw, _ = obs_io._read_beneath(base, relative, limit)
        return raw.decode("utf-8", errors="replace")
    except (FileNotFoundError, OSError, obs_io._UnsafeSource, ValueError):
        return None


def _read_store_safe(base: Path, relative: str, limit: int = _MAX_SMALL_RECORD_BYTES) -> Mapping[str, Any] | None:
    text = _read_text_safe(base, relative, limit)
    if text is None:
        return None
    try:
        loaded = store.loads(text)
        return loaded if isinstance(loaded, Mapping) else None
    except (store.StorageError, ValueError, RecursionError):
        return None


def _read_json_safe(base: Path, relative: str, limit: int = _MAX_SMALL_RECORD_BYTES) -> Mapping[str, Any] | None:
    text = _read_text_safe(base, relative, limit)
    if text is None:
        return None
    try:
        loaded = json.loads(text)
        return loaded if isinstance(loaded, Mapping) else None
    except (ValueError, RecursionError):
        return None


def _trace_tail_info(run_dir: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    """Read tail of ``trace.jsonl`` once to extract latest model/effort and latest packet timestamp."""
    out: dict[str, Any] = {"model": "", "effort": "", "latest_packet_at": None}
    path = run_dir / "trace.jsonl"
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return out
    try:
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size <= 0:
                return out
            offset = max(0, info.st_size - 64 * 1024)
            handle.seek(offset)
            chunk = handle.read(64 * 1024)
            if offset > 0:
                _, _, chunk = chunk.partition(b"\n")
            run_id = state.get("run_id")
            for raw_line in reversed(chunk.splitlines()):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line.decode("utf-8"))
                except (UnicodeError, ValueError):
                    continue
                if not isinstance(row, Mapping) or row.get("run_id", run_id) != run_id:
                    continue
                if not out["latest_packet_at"] and row.get("kind") == "packet" and isinstance(row.get("at"), str):
                    out["latest_packet_at"] = row["at"]
                if not out["model"] and row.get("kind") == "hook" and row.get("hook") == "model":
                    out["model"] = str(row.get("model") or "").strip()
                    out["effort"] = str(row.get("effort") or "").strip()
                if out["latest_packet_at"] and out["model"]:
                    break
    except OSError:
        return out
    return out


def _stage_started_at(
    timeline: Mapping[str, Any],
    state: Mapping[str, Any],
    *,
    latest_packet_at: str | None = None,
) -> str | None:
    history = state.get("history") or ()
    accepted = timeline.get("accepted") if isinstance(timeline.get("accepted"), Mapping) else {}
    if history:
        last_action = history[-1].get("action") if isinstance(history[-1], Mapping) else None
        if isinstance(last_action, str) and isinstance(accepted.get(last_action), str):
            return accepted[last_action]
    if latest_packet_at:
        return latest_packet_at
    started = timeline.get("started")
    return started if isinstance(started, str) else None


def run_summary_extras(
    run_dir: Path,
    state: Mapping[str, Any],
    timeline: Mapping[str, Any],
    entry: Mapping[str, Any],
) -> dict[str, Any]:
    """Additive lightweight summary fields attached to ``/api/runs`` items."""
    model = str(entry.get("model") or "").strip()
    effort = str(entry.get("effort") or "").strip()
    tail = _trace_tail_info(run_dir, state) if (not model or state.get("status") not in ("done", "halted")) else {
        "model": "", "effort": "", "latest_packet_at": None,
    }
    if not model and tail["model"]:
        model = tail["model"]
        effort = tail["effort"]

    history = state.get("history") or ()
    accepted_map = state.get("accepted") or {}
    latest_accomplishment: dict[str, Any] | None = None
    send_backs = 0
    for item in history:
        if isinstance(item, Mapping) and item.get("outcome") == "send-back":
            send_backs += 1
    if history and isinstance(history[-1], Mapping):
        last = history[-1]
        act = last.get("action")
        res = accepted_map.get(act) if isinstance(act, str) else None
        headline = ""
        if isinstance(res, Mapping):
            headline = _clean_text(res.get("headline"), 160) or _first_sentence(res.get("summary"), 160)
        if not headline:
            headline = _first_sentence(last.get("summary"), 160)
        latest_accomplishment = {
            "stage": str(last.get("stage") or ""),
            "workitem": last.get("workitem"),
            "outcome": str(last.get("outcome") or ""),
            "headline": headline,
        }

    testing_summary = ""
    try:
        t_obs = testing_status.testing_observability(run_dir, state)
        t_lines = testing_status.status_lines(t_obs)
        if t_lines:
            testing_summary = t_lines[0]
    except Exception:  # noqa: BLE001
        testing_summary = ""

    return {
        "model": _clean_text(model, 80),
        "effort": _clean_text(effort, 32),
        "started_at": timeline.get("started") if isinstance(timeline.get("started"), str) else None,
        "stage_started_at": _stage_started_at(timeline, state, latest_packet_at=tail["latest_packet_at"]),
        "steps_accepted": len(history),
        "send_backs_count": send_backs,
        "latest_accomplishment": latest_accomplishment,
        "testing_summary": testing_summary,
        "planning_review": str(state.get("planning_review") or ""),
        "lint": str(state.get("lint") or ""),
    }


def _parse_gate_line(raw_line: str) -> dict[str, Any]:
    line = _clean_text(raw_line, 240)
    if line.lower().startswith("gates:"):
        line = line[6:].strip()
    label, sep, rest = line.partition(":")
    if not sep:
        label, rest = "gate", line
    rest_clean = rest.strip()
    lower = rest_clean.lower()
    ok: bool | None = None
    if any(tok in lower for tok in ("passed", "ok", "reused", "0 failed", "verified")):
        ok = True
    if any(tok in lower for tok in ("fail", "refused", "not passed", "error", "mismatch")):
        ok = False
    if "skipped" in lower:
        ok = True
    return {"label": label.strip(), "detail": rest_clean, "ok": ok, "skipped": "skipped" in lower}


def _read_commit_sha(run_dir: Path, action_id: str) -> str | None:
    text = _read_text_safe(run_dir, f"commits/{action_id}.txt", 1024)
    if not text:
        return None
    sha = text.strip().splitlines()[0].strip()
    return sha if re.fullmatch(r"[0-9a-fA-F]{7,64}", sha) else None


def _read_improve_summary(run_dir: Path, action_id: str, imp_record: Any) -> dict[str, Any]:
    info: dict[str, Any] = {
        "reviewed": True,
        "phase": imp_record.get("runtime_phase") if isinstance(imp_record, Mapping) else None,
        "passes": 0,
        "lessons": "",
        "receipt_path": f"improve/{action_id}/receipt.md" if (run_dir / "improve" / action_id / "receipt.md").is_file() else None,
    }
    imp_dir = run_dir / "improve" / action_id
    try:
        if imp_dir.is_dir() and not imp_dir.is_symlink():
            info["passes"] = sum(
                1 for p in imp_dir.iterdir()
                if p.name.startswith("review-") and p.name.endswith(".md") and not p.is_symlink()
            )
    except OSError:
        pass
    rec = _read_store_safe(run_dir, f"improve/{action_id}/receipt.md")
    if rec:
        if isinstance(rec.get("passes"), int):
            info["passes"] = rec["passes"]
        if isinstance(rec.get("lessons"), str) and rec["lessons"].strip():
            info["lessons"] = _clean_text(rec["lessons"], 320)
        if not info["phase"] and isinstance(rec.get("runtime_phase"), str):
            info["phase"] = rec["runtime_phase"]
    return info


def _summarize_test_record(relative: str, rec: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(rec.get("kind") or "")
    if not kind:
        if "-step-proof" in relative:
            kind = "step-proof"
        elif "-red-check" in relative:
            kind = "red-check"
        elif "-mutation" in relative:
            kind = "mutation"
        elif "-base" in relative:
            kind = "base"
        elif "-verify" in relative or "-check" in relative:
            kind = "verify"
        else:
            kind = "test"
    passed = rec.get("passed")
    disposition = str(rec.get("disposition") or ("passed" if passed is True else "failed" if passed is False else "recorded"))
    reused = bool(rec.get("reused"))
    counts_bits: list[str] = []
    for run_row in rec.get("runs") or ():
        if isinstance(run_row, Mapping):
            cmd = _clean_text(run_row.get("command") or run_row.get("label") or "", 48)
            cnt = run_row.get("count")
            st = run_row.get("status")
            bit = f"{cmd}: {cnt} {st}" if cnt is not None else f"{cmd}: {st}"
            if bit.strip(": "):
                counts_bits.append(bit)
    if not counts_bits and isinstance(rec.get("summary"), str):
        counts_bits.append(_clean_text(rec["summary"], 140))
    if not counts_bits and isinstance(rec.get("skipped"), str):
        counts_bits.append(_clean_text(rec["skipped"], 140))
    return {
        "kind": kind,
        "label": kind.replace("-", " ").title(),
        "passed": passed if isinstance(passed, bool) else None,
        "disposition": disposition,
        "reused": reused,
        "detail": " · ".join(counts_bits),
        "path": relative,
    }


def _read_action_gates(
    run_dir: Path,
    action_id: str,
    test_names: Sequence[str],
    check_names: set[str],
    expectation_names: set[str],
) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    for name in test_names:
        if not (name.startswith(action_id + "-") and name.endswith(".md")):
            continue
        rel = f"tests/{name}"
        rec = _read_store_safe(run_dir, rel)
        if rec is not None:
            gates.append(_summarize_test_record(rel, rec))
    if f"{action_id}.md" in check_names:
        rel = f"checks/{action_id}.md"
        rec = _read_store_safe(run_dir, rel)
        if rec is not None:
            ans = str(rec.get("answer") or "")
            gates.append({
                "kind": "check",
                "label": "Check",
                "passed": ans == "yes" if ans in ("yes", "no") else None,
                "disposition": ans or "recorded",
                "reused": False,
                "detail": _clean_text(rec.get("reason") or " · ".join(rec.get("gate_lines") or ()), 180),
                "path": rel,
            })
    if f"{action_id}.md" in expectation_names:
        rel = f"expectations/{action_id}.md"
        rec = _read_store_safe(run_dir, rel)
        if rec is not None:
            rows = rec.get("results") if isinstance(rec.get("results"), list) else []
            matched = sum(1 for r in rows if isinstance(r, Mapping) and r.get("matches") is True)
            gates.append({
                "kind": "expectation",
                "label": "Expectations",
                "passed": matched == len(rows) if rows else None,
                "disposition": f"{matched}/{len(rows)} matched" if rows else "recorded",
                "reused": False,
                "detail": _clean_text(rec.get("summary") or "", 140),
                "path": rel,
            })
    return gates


def _read_action_lint(run_dir: Path, action_id: str, lint_names: Sequence[str]) -> dict[str, Any] | None:
    candidates = [n for n in lint_names if (n == f"{action_id}.md" or n.startswith(action_id + ".")) and n.endswith(".md")]
    if not candidates:
        return None
    rel = f"lint/{candidates[-1]}"
    rec = _read_store_safe(run_dir, rel)
    if rec is None:
        return None
    return {
        "kind": str(rec.get("kind") or "lint"),
        "exit_code": rec.get("exit_code"),
        "summary": _clean_text(rec.get("result_line") or rec.get("coverage_line") or "", 180),
        "path": rel,
    }


def _transition_note(
    entry: Mapping[str, Any],
    result: Mapping[str, Any],
    next_entry: Mapping[str, Any] | None,
    *,
    is_last_history: bool,
    current_stage: str | None,
    current_status: str | None,
    refusals: int,
    decision_answer: str | None,
) -> dict[str, Any]:
    outcome = str(entry.get("outcome") or "done")
    stage = str(entry.get("stage") or "")
    item = entry.get("workitem")

    if outcome == "send-back":
        target = ""
        try:
            if stage in stage_spec.SEND_BACK_MAP:
                target = stage_spec.send_back_target(stage)
        except Exception:  # noqa: BLE001
            target = ""
        reason = _first_sentence(result.get("summary") or entry.get("summary"), 180)
        return {
            "kind": "send-back",
            "target": target,
            "text": (f"Sent back to {target}" if target else "Sent back") + (f" — {reason}" if reason else ""),
        }

    if outcome == "add-work":
        added = [str(w.get("id")) for w in (result.get("work_items") or ()) if isinstance(w, Mapping) and w.get("id")]
        return {
            "kind": "add-work",
            "target": ", ".join(added),
            "text": "Added corrective work item(s): " + (", ".join(added) if added else "see result"),
        }

    if outcome == "blocked":
        reason = _first_sentence(result.get("summary") or entry.get("summary"), 180)
        if decision_answer:
            return {
                "kind": "blocked",
                "target": "resumed",
                "text": f"Blocked ({reason}) · Owner answered: {_first_sentence(decision_answer, 120)}",
            }
        return {"kind": "blocked", "target": "", "text": f"Blocked: {reason}" if reason else "Blocked"}

    replan = result.get("replan_remaining")
    if isinstance(replan, Mapping):
        affects = ", ".join(str(a) for a in (replan.get("affects") or ()) if a)
        reason = _first_sentence(replan.get("reason") or "", 150)
        return {
            "kind": "replan",
            "target": affects,
            "text": f"Fix-forward replan ({affects or 'remaining'})" + (f" — {reason}" if reason else ""),
        }

    if next_entry is not None:
        n_stage = str(next_entry.get("stage") or "")
        n_item = next_entry.get("workitem")
        target = f"{n_item} · {n_stage}" if n_item and n_item != item else n_stage
    elif is_last_history:
        target = "done" if current_status == "done" else str(current_stage or "")
    else:
        target = ""
    retry_note = ""
    if refusals > 0:
        retry_note = f" (after {refusals} refused callback{'s' if refusals != 1 else ''})"
    prefix = f"Advanced to {target}" if target and target != "done" else ("Completed run" if target == "done" else "Accepted")
    return {"kind": "done", "target": target, "text": prefix + retry_note}


def _read_pass_log_tail(run_dir: Path, action_id: str) -> dict[str, Any] | None:
    rel = f"notes/{action_id}.md"
    text = _read_text_safe(run_dir, rel, 64 * 1024)
    if text is None:
        return None
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    tail = "\n".join(_clean_text(ln, 220) for ln in lines[-6:])
    return {"path": rel, "lines": len(lines), "tail": tail, "bytes": len(text.encode("utf-8", errors="replace"))}


def _build_cli_commands(run_dir: Path, display_status: str) -> dict[str, str]:
    cli_path = Path(__file__).resolve().parent / "shiploop"
    q_cli = shlex.quote(str(cli_path))
    q_run = shlex.quote(str(run_dir))
    return {
        "status": f"python3 {q_cli} status --run-dir={q_run}",
        "resume": f"python3 {q_cli} resume --run-dir={q_run}",
        "note_prefix": f"python3 {q_cli} note --run-dir={q_run} --text ",
        "primary": f"python3 {q_cli} {'resume' if display_status == 'paused' else 'status'} --run-dir={q_run}",
    }


def _pipeline_with_durations(
    plan_rows: Sequence[Mapping[str, Any]],
    steps: Sequence[Mapping[str, Any]],
    plan_obs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    slot_seconds: dict[tuple[str | None, str], int] = {}
    for st in steps:
        sec = st.get("seconds")
        if isinstance(sec, (int, float)) and sec >= 0:
            key = (st.get("item"), str(st.get("stage") or ""))
            slot_seconds[key] = slot_seconds.get(key, 0) + int(round(sec))

    item_meta = {
        str(row.get("id")): row
        for row in (plan_obs.get("work_items") or ())
        if isinstance(row, Mapping) and row.get("id")
    }
    enriched: list[dict[str, Any]] = []
    dwell_rows: list[dict[str, Any]] = []
    total_seconds = 0

    for row in plan_rows:
        item_id = row.get("item")
        phase_sec = 0
        new_slots: list[dict[str, Any]] = []
        for slot in row.get("slots") or ():
            s_key = (item_id if row.get("phase") == "work" else None, str(slot.get("stage") or ""))
            sec = slot_seconds.get(s_key)
            if sec is not None:
                phase_sec += sec
            new_slots.append({**slot, "duration_seconds": sec})
        meta = item_meta.get(str(item_id), {}) if item_id else {}
        enriched.append({
            **row,
            "slice": meta.get("slice"),
            "concerns_mode": meta.get("concerns_mode"),
            "duration_seconds": phase_sec if any(s.get("duration_seconds") is not None for s in new_slots) else None,
            "slots": new_slots,
        })
        if any(s.get("duration_seconds") is not None for s in new_slots):
            total_seconds += phase_sec
            dwell_rows.append({
                "label": row.get("label"),
                "phase": row.get("phase"),
                "item": item_id,
                "seconds": phase_sec,
            })
    for d in dwell_rows:
        d["pct"] = round(100.0 * d["seconds"] / total_seconds, 1) if total_seconds > 0 else 0.0
    return enriched, dwell_rows


def _workspace_governance(run_dir: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    workspace_return = None
    leftovers = None
    try:
        workspace_return = navigator._workspace_return_projection(run_dir, state)
    except Exception:  # noqa: BLE001
        workspace_return = None
    if state.get("status") in ("done", "halted"):
        try:
            leftovers = navigator._leftovers(run_dir, state)
        except Exception:  # noqa: BLE001
            leftovers = None

    defaults_rows = defaults.recorded(state)
    default_revs = defaults.revisions(state)
    _, unv_stage, unv_rows = unverified.current_list(state)
    fo_rows = follow_on.recorded(state)
    fo_text = _read_text_safe(run_dir, follow_on.FILE, 32 * 1024)
    reconciliations = [
        {
            "action": str(r.get("action") or ""),
            "target": str(r.get("target") or ""),
            "summary": _clean_text(r.get("summary") or "", 220),
        }
        for r in (state.get("planning_reconciliations") or ())
        if isinstance(r, Mapping)
    ]
    return {
        "defaults": list(defaults_rows) if defaults_rows is not None else None,
        "default_revisions": default_revs,
        "unverified_stage": unv_stage,
        "unverified": list(unv_rows) if unv_rows is not None else None,
        "follow_on": list(fo_rows) if fo_rows is not None else None,
        "follow_on_request": _clean_multiline(fo_text, 4000) if fo_text else "",
        "reconciliations": reconciliations,
        "workspace_return": workspace_return,
        "leftovers": leftovers,
    }


def _model_by_action(events: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for ev in events:
        if ev.get("kind") == "hook" and ev.get("hook") == "model":
            act = ev.get("action") or ev.get("for_action")
            model = str(ev.get("model") or "").strip()
            effort = str(ev.get("effort") or "").strip()
            host = str(ev.get("host") or "").strip()
            if act and (model or effort):
                label = f"{host}:{model}/{effort}" if (host and model and effort) else (
                    f"{host}:{model}" if (host and model) else (model or effort)
                )
                labels[str(act)] = _clean_text(label, 80)
    return labels


def load_state_safe(run_dir: Path) -> Mapping[str, Any]:
    """Read ``state.md`` safely without symlinks or locks."""
    raw, _ = obs_io._read_beneath(Path(os.path.abspath(os.fspath(run_dir))), "state.md", 4 * 1024 * 1024)
    try:
        state = store.loads(raw.decode("utf-8"))
    except (UnicodeError, store.StorageError, RecursionError) as exc:
        raise ValueError("malformed state.md") from exc
    if not isinstance(state, Mapping):
        raise ValueError("state.md is not an object")
    return state


def _extract_duration_ms(record: Mapping[str, Any]) -> int | float | None:
    for key in ("ms", "duration_ms", "elapsed_ms"):
        val = record.get(key)
        if not isinstance(val, bool) and isinstance(val, (int, float)) and val >= 0:
            return val
    return None


def _nonneg_int(value: Any) -> int | None:
    if not isinstance(value, bool) and isinstance(value, int) and value >= 0:
        return value
    return None


def _extract_token_usage(record: Any) -> dict[str, int] | None:
    """Extract normalized non-negative token counts if explicitly recorded; return None otherwise."""
    if not isinstance(record, Mapping):
        return None
    sources: list[Mapping[str, Any]] = [record]
    for nested_key in ("token_usage", "usage"):
        nested = record.get(nested_key)
        if isinstance(nested, Mapping):
            sources.insert(0, nested)
    out: dict[str, int] = {}
    field_aliases = (
        ("input_tokens", ("input_tokens", "prompt_tokens", "input")),
        ("output_tokens", ("output_tokens", "completion_tokens", "output")),
        ("cached_tokens", ("cached_tokens", "cache_read_tokens", "cache_read_input_tokens", "cached_input")),
        ("cache_write_tokens", ("cache_write_tokens", "cache_creation_input_tokens", "cache_write")),
        ("reasoning_tokens", ("reasoning_tokens", "reasoning_output")),
        ("total_tokens", ("total_tokens", "tokens", "total")),
    )
    for src in sources:
        for dest_key, aliases in field_aliases:
            if dest_key in out:
                continue
            for alias in aliases:
                val = _nonneg_int(src.get(alias))
                if val is not None:
                    out[dest_key] = val
                    break
    if not out:
        return None
    if "total_tokens" not in out and ("input_tokens" in out or "output_tokens" in out):
        out["total_tokens"] = out.get("input_tokens", 0) + out.get("output_tokens", 0)
    return out


def _normalize_trace_tokens(raw: Any) -> dict[str, int] | None:
    """Normalize ``shiploop_trace`` delta-aggregated token stats into Hub ``token_usage`` shape."""
    if not isinstance(raw, Mapping):
        return None
    out: dict[str, int] = {}
    key_map = (
        ("input", "input_tokens"),
        ("output", "output_tokens"),
        ("cached_input", "cached_tokens"),
        ("cache_write", "cache_write_tokens"),
        ("reasoning_output", "reasoning_tokens"),
        ("total", "total_tokens"),
    )
    for src_key, dest_key in key_map:
        val = _nonneg_int(raw.get(src_key))
        if val is not None:
            out[dest_key] = val
    for opt_key in ("peak_context", "turns"):
        val = _nonneg_int(raw.get(opt_key))
        if val is not None and val > 0:
            out[opt_key] = val
    if not out:
        return None
    if "total_tokens" not in out and ("input_tokens" in out or "output_tokens" in out):
        out["total_tokens"] = out.get("input_tokens", 0) + out.get("output_tokens", 0)
    return out


def _merge_token_usage(records: Iterable[Mapping[str, Any] | None]) -> dict[str, int] | None:
    totals: dict[str, int] = {}
    any_seen = False
    for rec in records:
        if not isinstance(rec, Mapping):
            continue
        any_seen = True
        for k in ("input_tokens", "output_tokens", "cached_tokens", "cache_write_tokens", "reasoning_tokens", "total_tokens"):
            val = _nonneg_int(rec.get(k))
            if val is not None:
                totals[k] = totals.get(k, 0) + val
    if not any_seen or not totals:
        return None
    if "total_tokens" not in totals and ("input_tokens" in totals or "output_tokens" in totals):
        totals["total_tokens"] = totals.get("input_tokens", 0) + totals.get("output_tokens", 0)
    return totals


def _enrich_graphs(
    graphs: Sequence[Mapping[str, Any]],
    story_cards: Sequence[Mapping[str, Any]],
    work_items: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Attach recorded commit SHAs and step-proof verdicts onto accepted step-plan DAG nodes."""
    # Map each item's current step-plan action -> ordered implement cards after that step-plan.
    cards_by_item: dict[str, list[Mapping[str, Any]]] = {}
    for card in story_cards:
        item_id = card.get("item")
        if isinstance(item_id, str) and item_id:
            if card.get("stage") == "step-plan" and card.get("outcome") == "done":
                cards_by_item[item_id] = []
            elif card.get("stage") == "implement" and card.get("outcome") == "done":
                cards_by_item.setdefault(item_id, []).append(card)

    enriched: list[dict[str, Any]] = []
    for graph in graphs:
        if not isinstance(graph, Mapping):
            continue
        label = str(graph.get("label") or "")
        match = re.search(r"\(([^)]+)\)\s*$", label)
        wid = match.group(1) if match else ""
        impl_cards = cards_by_item.get(wid, [])
        nodes_out: list[dict[str, Any]] = []
        for idx, node in enumerate(graph.get("nodes") or ()):
            if not isinstance(node, Mapping):
                continue
            node_copy = dict(node)
            if idx < len(impl_cards):
                c = impl_cards[idx]
                if c.get("commit_sha"):
                    node_copy["commit_sha"] = c["commit_sha"]
                proof = next((g for g in (c.get("gates") or ()) if g.get("kind") == "step-proof"), None)
                if proof is not None:
                    node_copy["proof_passed"] = proof.get("passed")
                    node_copy["proof_reused"] = proof.get("reused")
            nodes_out.append(node_copy)
        enriched.append({**graph, "nodes": nodes_out})
    return enriched


def _capture_core_safe(run_root: Path) -> dict[str, Any]:
    """Capture ``state.md`` and ``timeline.json`` once using the existing shared-lock / archive pattern."""
    try:
        os.lstat(run_root / ".lock")
    except FileNotFoundError:
        if os.path.lexists(run_root / store.JOURNAL_NAME):
            raise ValueError("run busy or transaction pending") from None
        core = story_data.capture_core(run_root, consistency="unlocked-archive")
        if os.path.lexists(run_root / store.JOURNAL_NAME) or os.path.lexists(run_root / ".lock"):
            raise ValueError("run lock appeared or transaction pending during archive capture") from None
        return core
    with progress._lock(run_root, ".lock", shared=True) as acquired:
        if not acquired or os.path.lexists(run_root / store.JOURNAL_NAME):
            raise ValueError("run busy or transaction pending")
        return story_data.capture_core(run_root)


def build_run_detail(run_dir: Path, *, entry: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build the complete read-only Hub detail payload for one run directory."""
    run_root = Path(os.path.abspath(os.fspath(run_dir)))
    core = _capture_core_safe(run_root)
    state, timeline = story_data.core_values(core)
    trace_model = trace_mod.build(run_root, core=core)
    snap = progress_data.build_snapshot(run_root, core=core)

    snap_run = snap.get("run") if isinstance(snap.get("run"), Mapping) else {}
    plan_obs = snap.get("planning") if isinstance(snap.get("planning"), Mapping) else {}
    testing_obs = snap.get("testing_evidence") if isinstance(snap.get("testing_evidence"), Mapping) else {}
    inflight = snap_run.get("inflight") if isinstance(snap_run.get("inflight"), Mapping) else {}
    fallback_status, fallback_label = navigator.display_status(state)
    display_status = str(snap_run.get("display_status") or fallback_status)
    display_label = str(snap_run.get("display_label") or fallback_label)
    facts = snap.get("facts") if isinstance(snap.get("facts"), Mapping) else {}
    where = navigator._status_where(state)
    next_label, next_text = navigator._status_next(state)

    test_names = story_data._listing(run_root, "tests")
    check_names = set(story_data._listing(run_root, "checks"))
    expectation_names = set(story_data._listing(run_root, "expectations"))
    lint_names = story_data._listing(run_root, "lint")
    decision_names = set(story_data._listing(run_root, "decisions"))

    events = trace_model.get("events") or []
    events_by_action: dict[str, list[dict[str, Any]]] = {}
    for ev in events:
        owner_act = ev.get("action") or ev.get("for_action")
        if isinstance(owner_act, str) and owner_act:
            events_by_action.setdefault(owner_act, []).append(ev)

    model_map = _model_by_action(events)
    step_by_action = {
        str(st.get("action")): st
        for st in (trace_model.get("steps") or ())
        if isinstance(st, Mapping) and st.get("action")
    }
    work_titles = {
        str(w.get("id")): _clean_text(w.get("title") or "", 120)
        for w in (state.get("work_items") or ())
        if isinstance(w, Mapping) and w.get("id")
    }

    history = list(state.get("history") or ())
    accepted_map = state.get("accepted") or {}
    improve_results = state.get("improve_results") or {}
    accepted_at = timeline.get("accepted") if isinstance(timeline.get("accepted"), Mapping) else {}
    prev_end = timeline.get("started") if isinstance(timeline.get("started"), str) else None

    stage_now, action_now, item_now = navigator._active_cursor(state)
    active_improve = state.get("active_improve") if isinstance(state.get("active_improve"), Mapping) else None
    now_action_id = (active_improve.get("improve_action") if active_improve else None) or (
        action_now.get("id") if isinstance(action_now, Mapping) else None
    )

    story_cards: list[dict[str, Any]] = []
    for idx, h_entry in enumerate(history):
        act_id = str(h_entry.get("action") or "")
        res = accepted_map.get(act_id) if isinstance(accepted_map.get(act_id), Mapping) else {}
        st_row = step_by_action.get(act_id, {})
        act_events = events_by_action.get(act_id, [])
        refusals = [e for e in act_events if trace_mod.refused(e)]
        refusal_previews = [_clean_text(r.get("error") or "", 200) for r in refusals[:3]]
        ended_at = st_row.get("at") or (accepted_at.get(act_id) if isinstance(accepted_at.get(act_id), str) else None)
        first_pkt = next((e.get("at") for e in act_events if e.get("kind") == "packet" and e.get("at")), None)
        started_at = st_row.get("started_at") or first_pkt or prev_end
        dur_sec = st_row.get("seconds")
        canonical_basis = st_row.get("duration_basis")
        dur_basis = str(canonical_basis) if isinstance(canonical_basis, str) and canonical_basis != "unmeasured" else "first packet to accepted"
        if dur_sec is None and started_at and ended_at:
            t0, t1 = story_data._timestamp(started_at), story_data._timestamp(ended_at)
            if t0 is not None and t1 is not None and t1 >= t0:
                dur_sec = round(t1 - t0)
                dur_basis = "inferred transition dwell"
        if ended_at:
            prev_end = ended_at

        dec_answer = None
        if f"{act_id}.md" in decision_names:
            dec_raw = _read_text_safe(run_root, f"decisions/{act_id}.md", 8192)
            if dec_raw:
                dec_answer = _clean_text(dec_raw, 280)

        next_h = history[idx + 1] if idx + 1 < len(history) else None
        trans_note = _transition_note(
            h_entry,
            res,
            next_h,
            is_last_history=(idx == len(history) - 1),
            current_stage=stage_now,
            current_status=state.get("status"),
            refusals=len(refusals),
            decision_answer=dec_answer,
        )
        notes_rows = [
            {
                "note": str(nr.get("note") or ""),
                "did": str(nr.get("did") or ""),
                "detail": _clean_text(nr.get("detail") or "", 180),
                "item": nr.get("item"),
            }
            for nr in (res.get("notes") or ())
            if isinstance(nr, Mapping)
        ]

        imp_info = _read_improve_summary(run_root, act_id, improve_results[act_id]) if act_id in improve_results else None
        loop_rec = _read_json_safe(run_root, f"loops/{act_id}-terminal.json")
        loop_info = None
        if loop_rec:
            prog = loop_rec.get("progress") if isinstance(loop_rec.get("progress"), Mapping) else {}
            lr = loop_rec.get("last_report") if isinstance(loop_rec.get("last_report"), Mapping) else {}
            loop_info = {
                "iterations": prog.get("action_number") or loop_rec.get("action_number") or 1,
                "status": _clean_text(loop_rec.get("status") or "", 32),
                "handoff": _clean_text(lr.get("handoff") or lr.get("evidence") or "", 220),
            }

        card_events = [
            {
                "id": e.get("id"),
                "kind": e.get("kind"),
                "at": e.get("at"),
                "verb": e.get("verb"),
                "exit": e.get("exit"),
                "ms": _extract_duration_ms(e),
                "usage": _extract_token_usage(e),
                "summary": _clean_text(
                    e.get("error") or e.get("why") or e.get("text") or e.get("verb") or e.get("skill") or "",
                    220,
                ),
                "file": e.get("file"),
                "head_file": e.get("head_file"),
                "refused": trace_mod.refused(e),
                "repeat": bool(e.get("repeat")),
            }
            for e in act_events[-40:]
        ]
        card_tokens = _normalize_trace_tokens(st_row.get("tokens"))
        if card_tokens is None:
            card_tokens = _merge_token_usage([_extract_token_usage(e) for e in act_events] + [_extract_token_usage(res)])

        step_model = str(st_row.get("model") or "").strip()
        step_effort = str(st_row.get("effort") or "").strip()
        fallback_model = (f"{step_model}/{step_effort}" if (step_model and step_effort) else step_model) if step_model else ""

        headline = _clean_text(res.get("headline") or "", 180) or _first_sentence(res.get("summary") or h_entry.get("summary"), 180)
        story_cards.append({
            "seq": idx + 1,
            "action": act_id,
            "stage": str(h_entry.get("stage") or ""),
            "item": h_entry.get("workitem"),
            "item_title": work_titles.get(str(h_entry.get("workitem") or ""), ""),
            "outcome": str(h_entry.get("outcome") or "done"),
            "is_current": False,
            "headline": headline,
            "summary": _clean_multiline(res.get("summary") or h_entry.get("summary") or "", 1600),
            "lessons": _clean_text(res.get("lessons") or "", 320),
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_seconds": dur_sec,
            "wall_seconds": st_row.get("wall_seconds"),
            "active_seconds": st_row.get("active_seconds"),
            "paused_seconds": st_row.get("paused_seconds"),
            "duration_basis": dur_basis,
            "token_usage": card_tokens,
            "transition_note": trans_note,
            "owner_notes_handled": notes_rows,
            "commit_sha": _read_commit_sha(run_root, act_id),
            "improve": imp_info,
            "gates": _read_action_gates(run_root, act_id, test_names, check_names, expectation_names),
            "loop": loop_info,
            "lint": _read_action_lint(run_root, act_id, lint_names),
            "model_label": model_map.get(act_id, "") or _clean_text(fallback_model, 80),
            "counts": {
                "packets": sum(1 for e in act_events if e.get("kind") == "packet"),
                "refusals": len(refusals),
                "hooks": sum(1 for e in act_events if e.get("kind") == "hook" and e.get("hook") not in ("model", "usage")),
            },
            "refusal_previews": refusal_previews,
            "evidence_refs": [
                _clean_text(r, 180)
                for r in (res.get("evidence_refs") or ())[:12]
                if isinstance(r, str)
            ],
            "decision_answer": dec_answer,
            "result_path": f"results/{act_id}.md" if (run_root / "results" / f"{act_id}.md").is_file() else None,
            "events": card_events,
        })

    if state.get("status") != "done" and isinstance(now_action_id, str) and now_action_id:
        cur_action_for_files = (active_improve.get("action_id") if active_improve else None) or now_action_id
        cur_events = events_by_action.get(now_action_id, []) + (
            events_by_action.get(str(cur_action_for_files), [])
            if active_improve and cur_action_for_files != now_action_id else []
        )
        cur_refusals = [e for e in cur_events if trace_mod.refused(e)]
        trace_now = trace_model.get("now") if isinstance(trace_model.get("now"), Mapping) else {}
        cur_since = trace_now.get("since") or prev_end
        cur_tokens = _normalize_trace_tokens(trace_now.get("tokens"))
        if cur_tokens is None:
            cur_tokens = _merge_token_usage(_extract_token_usage(e) for e in cur_events)
        story_cards.append({
            "seq": len(story_cards) + 1,
            "action": now_action_id,
            "stage": "improve" if active_improve else str(stage_now or ""),
            "reviewing_stage": active_improve.get("stage") if active_improve else None,
            "item": item_now,
            "item_title": work_titles.get(str(item_now or ""), ""),
            "outcome": display_status,
            "is_current": True,
            "headline": _clean_text(next_text, 180),
            "summary": _clean_multiline(state.get("status_reason") or next_text, 1000),
            "lessons": "",
            "started_at": cur_since,
            "ended_at": None,
            "duration_seconds": None,
            "paused_seconds": trace_now.get("paused_seconds"),
            "duration_basis": "in-progress dwell",
            "token_usage": cur_tokens,
            "transition_note": {
                "kind": display_status,
                "target": "",
                "text": _clean_text(state.get("status_reason") or f"{display_label}: {where}", 220),
            },
            "owner_notes_handled": [],
            "commit_sha": None,
            "improve": {
                "reviewed": False,
                "active": True,
                "stage": active_improve.get("stage"),
                "review_mode": inflight.get("improve_review_mode"),
                "passes": inflight.get("improve_passes", 0),
            } if active_improve else None,
            "gates": _read_action_gates(run_root, str(cur_action_for_files), test_names, check_names, expectation_names),
            "loop": {
                "iterations": inflight.get("loop_iteration", 0),
                "status": inflight.get("loop_status", ""),
                "handoff": "",
            } if inflight.get("loop_iteration") else None,
            "lint": _read_action_lint(run_root, str(cur_action_for_files), lint_names),
            "model_label": model_map.get(now_action_id, ""),
            "counts": {
                "packets": sum(1 for e in cur_events if e.get("kind") == "packet"),
                "refusals": len(cur_refusals),
                "hooks": sum(1 for e in cur_events if e.get("kind") == "hook" and e.get("hook") not in ("model", "usage")),
            },
            "refusal_previews": [_clean_text(r.get("error") or "", 200) for r in cur_refusals[:3]],
            "evidence_refs": [],
            "decision_answer": None,
            "result_path": None,
            "events": [
                {
                    "id": e.get("id"),
                    "kind": e.get("kind"),
                    "at": e.get("at"),
                    "verb": e.get("verb"),
                    "exit": e.get("exit"),
                    "ms": _extract_duration_ms(e),
                    "usage": _extract_token_usage(e),
                    "summary": _clean_text(
                        e.get("error") or e.get("why") or e.get("text") or e.get("verb") or e.get("skill") or "",
                        220,
                    ),
                    "file": e.get("file"),
                    "head_file": e.get("head_file"),
                    "refused": trace_mod.refused(e),
                    "repeat": bool(e.get("repeat")),
                }
                for e in cur_events[-40:]
            ],
        })

    # Live focus details
    cur_action_obj = action_now if isinstance(action_now, Mapping) else {}
    cur_id = str(cur_action_obj.get("id") or now_action_id or "")
    step_task = ""
    if item_now and stage_now in ("implement", "test", "document"):
        sv = navigator.step_view(state, item_now)
        if sv is not None:
            step_task = _clean_text(sv.step.get("task") or "", 240)

    live_loop = None
    if cur_id and not active_improve:
        lrec = _read_json_safe(run_root, f"loops/{cur_id}-terminal.json")
        if lrec:
            prog = lrec.get("progress") if isinstance(lrec.get("progress"), Mapping) else {}
            lr = lrec.get("last_report") if isinstance(lrec.get("last_report"), Mapping) else {}
            live_loop = {
                "iteration": prog.get("action_number") or lrec.get("action_number") or 1,
                "status": _clean_text(lrec.get("status") or "", 32),
                "exit_assessment": _clean_text(lr.get("exit_assessment") or lrec.get("exit_assessment") or "", 64),
                "handoff": _clean_text(lr.get("handoff") or lr.get("evidence") or "", 280),
            }

    last_check = None
    if cur_id and not active_improve:
        crec = _read_store_safe(run_root, f"checks/{cur_id}.md")
        if crec:
            last_check = {
                "yes": crec.get("answer") == "yes",
                "created_at": crec.get("created_at"),
                "reason": _clean_text(crec.get("reason") or "", 240),
                "gates": [_parse_gate_line(gl) for gl in (crec.get("gate_lines") or ()) if isinstance(gl, str)],
                "path": f"checks/{cur_id}.md",
            }

    pass_log = _read_pass_log_tail(run_root, now_action_id) if isinstance(now_action_id, str) and now_action_id else None
    tail_info = _trace_tail_info(run_root, state)
    active_model = str((entry or {}).get("model") or tail_info["model"] or "")
    active_effort = str((entry or {}).get("effort") or tail_info["effort"] or "")
    active_host = str((entry or {}).get("host") or "")

    pipeline, dwell_breakdown = _pipeline_with_durations(trace_model.get("plan") or (), trace_model.get("steps") or (), plan_obs)

    # Enrich graphs with commit sha and step-proof status if known
    graphs = _enrich_graphs(snap.get("graphs") or (), story_cards, snap.get("work_items") or ())
    repo_root = Path(os.path.abspath(os.fspath(state["repo"])))
    documents = []
    for doc in snap.get("documents") or ():
        if not isinstance(doc, Mapping):
            continue
        doc_path = Path(os.path.abspath(str(doc.get("path") or "")))
        scope = "run"
        rel = ""
        try:
            rel = doc_path.relative_to(run_root).as_posix()
            scope = "run"
        except ValueError:
            try:
                rel = doc_path.relative_to(repo_root).as_posix()
                scope = "repo"
            except ValueError:
                rel = ""
        documents.append({
            "id": doc.get("id"),
            "title": doc.get("title"),
            "status": doc.get("status"),
            "summary": doc.get("summary"),
            "sha256": doc.get("sha256"),
            "observed_at": doc.get("observed_at"),
            "scope": scope,
            "relative": rel,
            "path": doc.get("path"),
        })

    # Lightweight trace events (newest 400)
    raw_events = events[-400:]
    trace_events = [
        {
            "id": e.get("id"),
            "kind": e.get("kind"),
            "at": e.get("at"),
            "action": e.get("action") or e.get("for_action"),
            "stage": e.get("stage")[0] if isinstance(e.get("stage"), list) and e.get("stage") else e.get("stage"),
            "item": e.get("item"),
            "verb": e.get("verb"),
            "exit": e.get("exit"),
            "ms": _extract_duration_ms(e),
            "usage": _extract_token_usage(e),
            "hook": e.get("hook"),
            "decision": e.get("decision"),
            "host": e.get("host"),
            "skill": e.get("skill"),
            "gate": e.get("gate"),
            "outcome": e.get("outcome"),
            "summary": _clean_text(
                e.get("error") or e.get("why") or e.get("text") or e.get("verb") or e.get("skill")
                or (story_data._packet_summary(e) if e.get("kind") == "packet" else e.get("kind") or ""),
                240,
            ),
            "file": e.get("file"),
            "head_file": e.get("head_file"),
            "refused": trace_mod.refused(e),
            "repeat": bool(e.get("repeat")),
            "crashed": e.get("crashed"),
            "accepted": e.get("accepted") or [],
        }
        for e in raw_events
    ]

    story_obj = snap.get("story") if isinstance(snap.get("story"), Mapping) else {}
    run_trace_info = trace_model.get("run") if isinstance(trace_model.get("run"), Mapping) else {}
    run_key = (entry or {}).get("run_key") or ""
    run_token_usage = _normalize_trace_tokens(run_trace_info.get("tokens"))
    if run_token_usage is None:
        run_token_usage = _merge_token_usage(_extract_token_usage(e) for e in events)

    payload = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "run": {
            "run_id": state["run_id"],
            "run_key": run_key,
            "run_dir": str(run_root),
            "repo": str(state.get("repo") or ""),
            "source_repo": (entry or {}).get("source_repo") or str(state.get("repo") or ""),
            "execution_mode": str(state.get("execution_mode") or "navigator"),
            "delegation": str(state.get("delegation") or "inline"),
            "planning_review": str(state.get("planning_review") or ""),
            "lint": str(state.get("lint") or ""),
            "host": active_host,
            "model": _clean_text(active_model, 80),
            "effort": _clean_text(active_effort, 32),
            "owner_alive": (entry or {}).get("owner_alive"),
            "revision": state.get("revision"),
            "status": state.get("status"),
            "display_status": display_status,
            "display_label": display_label,
            "prompt": _clean_multiline(state.get("prompt") or "", 12000),
            "goal": _clean_text(facts.get("goal") or "", 140),
            "started_at": timeline.get("started") if isinstance(timeline.get("started"), str) else None,
            "last_event_at": run_trace_info.get("last_event"),
            "elapsed_seconds": run_trace_info.get("elapsed"),
            "active_seconds": run_trace_info.get("active_seconds"),
            "paused_seconds": run_trace_info.get("paused_seconds"),
            "token_usage": run_token_usage,
            "has_report": state.get("status") in ("done", "halted") and (run_root / "report.html").is_file(),
        },
        "phases": facts.get("phases") or [],
        "live_now": {
            "status": state.get("status"),
            "display_status": display_status,
            "display_label": display_label,
            "stage": "improve" if active_improve else stage_now,
            "reviewing_stage": active_improve.get("stage") if active_improve else None,
            "item": item_now,
            "where": where,
            "purpose": _clean_text((trace_model.get("now") or {}).get("purpose") or "", 240),
            "reason": _clean_text(state.get("status_reason") or "", 400),
            "next_label": next_label,
            "next_text": _clean_text(next_text, 240),
            "action_id": now_action_id,
            "packet_file": (trace_model.get("now") or {}).get("packet"),
            "stage_started_at": _stage_started_at(
                timeline, state, latest_packet_at=(trace_model.get("now") or {}).get("since") or tail_info["latest_packet_at"]
            ),
            "step_id": inflight.get("step_id"),
            "step_number": inflight.get("step_number", 0),
            "step_total": inflight.get("step_total", 0),
            "step_task": step_task,
            "callback_attempts": inflight.get("callback_attempts", 0),
            "loop": live_loop,
            "improve": {
                "active": True,
                "stage": active_improve.get("stage"),
                "review_mode": inflight.get("improve_review_mode"),
                "passes": inflight.get("improve_passes", 0),
                "action_id": active_improve.get("improve_action"),
            } if active_improve else None,
            "last_check": last_check,
            "pass_log": pass_log,
            "cli_commands": _build_cli_commands(run_root, display_status),
        },
        "pipeline": pipeline,
        "dwell_breakdown": dwell_breakdown,
        "story_cards": story_cards,
        "request": trace_model.get("request"),
        "planning": plan_obs,
        "testing_evidence": testing_obs,
        "work_items": snap.get("work_items") or [],
        "graphs": graphs,
        "documents": documents,
        "notes": trace_model.get("notes") or [],
        "governance": _workspace_governance(run_root, state),
        "trace_summary": {
            "traced": bool(run_trace_info.get("traced")),
            "counts": trace_model.get("counts") or {},
            "sources": story_obj.get("sources") or [],
            "observations": story_obj.get("observations") or [],
            "lifecycle": story_obj.get("lifecycle") or {},
            "warnings": story_obj.get("warnings") or [],
            "token_usage": run_token_usage,
            "events": trace_events,
        },
    }
    return obs_io.screen(payload)


def read_run_artifact(
    run_dir: Path,
    state: Mapping[str, Any],
    scope: str,
    rel_path: str,
) -> dict[str, Any]:
    """Safely read one bounded, credential-screened artifact file for the Hub inspector drawer."""
    if scope not in ("run", "repo"):
        raise ValueError("invalid artifact scope")
    parts = obs_io._relative_parts(rel_path)
    normalized = "/".join(parts)
    if any(p.startswith(".") for p in parts):
        raise PermissionError("hidden artifact paths are refused")

    if scope == "run":
        allowed = (normalized in _RUN_ARTIFACT_EXACT) or normalized.startswith(_RUN_ARTIFACT_PREFIXES)
        if not allowed:
            raise PermissionError("run artifact path is outside allowed display folders")
        base = Path(os.path.abspath(os.fspath(run_dir)))
    else:
        repo_raw = state.get("repo")
        if not isinstance(repo_raw, str) or not repo_raw:
            raise PermissionError("repository path unavailable")
        base = Path(os.path.abspath(repo_raw))
        allowed_repo = normalized in _REPO_DOC_EXACT or normalized.startswith("docs/shiploop/")
        if not allowed_repo:
            # Also permit explicit accepted evidence_refs residing beneath repo with safe text extensions.
            base_abs = os.path.abspath(os.fspath(base))
            target_abs = os.path.abspath(os.fspath(base / normalized))
            known_refs: set[str] = set()
            for res in (state.get("accepted") or {}).values():
                if isinstance(res, Mapping):
                    for ref in res.get("evidence_refs") or ():
                        if isinstance(ref, str) and ref.strip():
                            ref_p = Path(ref)
                            cand = os.path.abspath(ref) if ref_p.is_absolute() else os.path.abspath(os.fspath(base / ref))
                            if cand == base_abs or cand.startswith(base_abs + os.sep):
                                known_refs.add(cand)
            if target_abs not in known_refs or Path(normalized).suffix.lower() not in (".md", ".txt", ".json"):
                raise PermissionError("repository path is not an allowed run document")

    raw, _ = obs_io._read_beneath(base, normalized, _MAX_ARTIFACT_BYTES + 1)
    truncated = len(raw) > _MAX_ARTIFACT_BYTES
    if truncated:
        raw = raw[:_MAX_ARTIFACT_BYTES]
    sha256 = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8", errors="replace")
    withheld = False
    if privacy.sensitive_text(text):
        withheld = True
        content = "Artifact content withheld because credential-like text matched the privacy screen."
    else:
        content = privacy.redact_text(text)

    return obs_io.screen({
        "schema": "shiploop-hub-artifact/v1",
        "scope": scope,
        "relative": normalized,
        "path": str(base / normalized),
        "sha256": sha256,
        "bytes": len(raw),
        "truncated": truncated,
        "withheld": withheld,
        "content": content,
    })


__all__ = (
    "SCHEMA",
    "build_run_detail",
    "detail_version_digest",
    "detail_watch_signature",
    "load_state_safe",
    "read_run_artifact",
    "run_summary_extras",
)
