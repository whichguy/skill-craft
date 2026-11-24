"""Causal fork-completeness verifier for delegated Codex ShipLoop E2E runs.

Checks parent and child Codex rollout logs (``home/**``) plus ShipLoop's
``trace.jsonl`` and Improve ``packet.json`` files to confirm spawned workers
complete before parent wait return and ``shiploop complete``, with zero
silently abandoned forks, nested spawns, or child ``shiploop complete`` calls.
"""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re

SHIPLOOP_COMPLETE_CMD = re.compile(
    r"""(?:^|[\s'"`])(?:[^\s'"`]*shiploop(?:\.py)?)(?:['"`])?\s+complete(?:\s|$)"""
)


def _epoch(text: object) -> float | None:
    if not isinstance(text, str) or not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _read_records(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open(errors="replace") as handle:
        for line in handle:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict):
                records.append(rec)
    return records


def _parse_json_obj(raw: object) -> dict:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw:
        return {}
    try:
        val = json.loads(raw)
        return val if isinstance(val, dict) else {}
    except ValueError:
        return {}


def _find_rollouts(out: Path) -> tuple[list[list[dict]], list[tuple[dict, list[dict]]]]:
    home = out / "home"
    if not home.is_dir():
        return [], []
    files: list[Path] = []
    for dp, _, fns in os.walk(home):
        for fn in fns:
            if fn.startswith("rollout-") and fn.endswith(".jsonl"):
                files.append(Path(dp) / fn)
    files.sort()
    parents: list[list[dict]] = []
    children: list[tuple[dict, list[dict]]] = []
    for fp in files:
        recs = _read_records(fp)
        if not recs:
            continue
        first = recs[0]
        meta = first.get("payload") if first.get("type") == "session_meta" and isinstance(first.get("payload"), dict) else {}
        src = meta.get("source")
        if isinstance(src, dict) and "subagent" in src:
            children.append((meta, recs))
        else:
            parents.append(recs)
    return parents, children


def _trace_info(run_dir: Path | None) -> tuple[list[dict], list[float]]:
    if run_dir is None:
        return [], []
    tp = run_dir / "trace.jsonl"
    if not tp.is_file():
        return [], []
    packets: list[dict] = []
    completes: list[float] = []
    for rec in _read_records(tp):
        ts = rec.get("ts")
        if not isinstance(ts, (int, float)):
            continue
        if rec.get("kind") == "packet":
            packets.append({"ts": float(ts), "stage": rec.get("stage"), "reviewed": rec.get("reviewed")})
        elif rec.get("kind") == "command" and rec.get("verb") == "complete":
            completes.append(float(ts))
    packets.sort(key=lambda e: e["ts"])
    completes.sort()
    return packets, completes


def _improve_packets(run_dir: Path | None) -> tuple[int, int]:
    if run_dir is None:
        return 0, 0
    imp = run_dir.parent / "worktree" / ".shiploop-improve"
    if not imp.is_dir():
        return 0, 0
    total = complete = 0
    for pkt in sorted(imp.glob("*/packet.json")):
        total += 1
        try:
            data = json.loads(pkt.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("status") == "complete":
            complete += 1
    return complete, total


def _child_own_slice(recs: list[dict], spawn_ts: float | None) -> list[dict]:
    for idx, rec in enumerate(recs[1:], 1):
        payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
        if rec.get("type") == "event_msg" and payload.get("type") == "thread_settings_applied":
            return recs[idx + 1 :]
    if spawn_ts is None:
        return recs[1:]
    own: list[dict] = []
    for rec in recs[1:]:
        ts = _epoch(rec.get("timestamp"))
        if ts is None or ts >= spawn_ts - 0.5:
            own.append(rec)
    return own


def _match_child(spawn: dict, children: list[tuple[dict, list[dict]]], used: set[int]) -> tuple[dict, list[dict]] | None:
    out = spawn.get("out") or {}
    tname = out.get("task_name")
    aid = out.get("agent_id")
    for idx, (meta, recs) in enumerate(children):
        if idx in used:
            continue
        if (tname and meta.get("agent_path") == tname) or (aid and meta.get("id") == aid):
            used.add(idx)
            return meta, recs
    sts = spawn.get("ts")
    if sts is not None:
        best_idx = None
        best_dt = 3.0
        for idx, (meta, _recs) in enumerate(children):
            if idx in used:
                continue
            cts = _epoch(meta.get("timestamp"))
            if cts is not None and abs(cts - sts) <= best_dt:
                best_dt = abs(cts - sts)
                best_idx = idx
        if best_idx is not None:
            used.add(best_idx)
            return children[best_idx]
    return None


def _target_matches(target: object, task_name: object, agent_id: object) -> bool:
    if not isinstance(target, str) or not target:
        return False
    if agent_id and target == agent_id:
        return True
    if isinstance(task_name, str) and task_name:
        return target == task_name or target == task_name.rsplit("/", 1)[-1]
    return False


def collect(out: Path, run_dir: Path | None = None) -> dict | None:
    """Measure causal fork completeness from rollout logs, trace.jsonl, and Improve packets."""
    out = Path(out)
    parents, children = _find_rollouts(out)
    if not parents:
        return None

    spawns: list[dict] = []
    waits: list[dict] = []
    interrupts: list[dict] = []
    cmap: dict[str, dict] = {}
    for recs in parents:
        for rec in recs:
            ts = _epoch(rec.get("timestamp"))
            payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
            if rec.get("type") == "response_item" and payload.get("type") == "function_call":
                name = payload.get("name")
                cid = payload.get("call_id")
                entry = {"ts": ts, "name": name, "call_id": cid, "args": _parse_json_obj(payload.get("arguments"))}
                if isinstance(cid, str):
                    cmap[cid] = entry
                if name == "spawn_agent":
                    spawns.append(entry)
                elif name == "wait_agent":
                    waits.append(entry)
                elif name == "interrupt_agent":
                    interrupts.append(entry)
            elif rec.get("type") == "response_item" and payload.get("type") == "function_call_output":
                cid = payload.get("call_id")
                if isinstance(cid, str) and cid in cmap:
                    cmap[cid]["ret_ts"] = ts
                    cmap[cid]["out"] = _parse_json_obj(payload.get("output"))

    if not spawns:
        return None

    spawns.sort(key=lambda e: e["ts"] or 0.0)
    waits.sort(key=lambda e: e["ts"] or 0.0)
    interrupts.sort(key=lambda e: e["ts"] or 0.0)

    packets, trace_completes = _trace_info(run_dir)
    packets_complete, packets_total = _improve_packets(run_dir)

    used: set[int] = set()
    rows: list[dict] = []
    total_completed = total_order_ok = total_abandoned = total_interrupted = 0
    total_nested_spawns = total_child_completes = total_waits = total_timeouts = 0

    for idx, spawn in enumerate(spawns):
        sts = spawn["ts"]
        next_sts = spawns[idx + 1]["ts"] if idx + 1 < len(spawns) else None
        out_d = spawn.get("out") or {}
        tname = out_d.get("task_name")
        aid = out_d.get("agent_id")
        fork_turns = spawn["args"].get("fork_turns")

        prev_pkts = [p for p in packets if sts is None or p["ts"] <= sts]
        stage = (prev_pkts[-1].get("reviewed") or prev_pkts[-1].get("stage")) if prev_pkts else None

        matched = _match_child(spawn, children, used)
        execs = nested_spawns = child_completes = 0
        task_complete_ts: float | None = None
        aborted = False
        if matched is not None:
            _meta, crecs = matched
            for rec in _child_own_slice(crecs, sts):
                cp = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
                rtype = rec.get("type")
                if rtype == "response_item" and cp.get("type") == "custom_tool_call" and cp.get("name") == "exec":
                    execs += 1
                    inp = cp.get("input") or ""
                    if isinstance(inp, str) and SHIPLOOP_COMPLETE_CMD.search(inp):
                        child_completes += 1
                elif rtype == "response_item" and cp.get("type") == "function_call" and cp.get("name") == "spawn_agent":
                    nested_spawns += 1
                elif rtype == "event_msg" and cp.get("type") == "task_complete":
                    cts = _epoch(rec.get("timestamp"))
                    if cts is not None:
                        task_complete_ts = cts
                elif rtype == "event_msg" and cp.get("type") == "turn_aborted":
                    aborted = True

        m_waits: list[dict] = []
        for w in waits:
            wts = w["ts"]
            if sts is not None and wts is not None and wts < sts:
                continue
            if next_sts is not None and wts is not None and wts >= next_sts:
                continue
            targets = w["args"].get("targets") or w["args"].get("ids") or []
            if targets and not any(_target_matches(t, tname, aid) for t in targets):
                continue
            m_waits.append(w)

        w_timeouts = sum(1 for w in m_waits if (w.get("out") or {}).get("timed_out") is True)
        fin_waits = [w for w in m_waits if (w.get("out") or {}).get("timed_out") is not True and w.get("ret_ts") is not None]
        wait_ret_ts = fin_waits[-1]["ret_ts"] if fin_waits else None
        next_tc_ts = next((t for t in trace_completes if sts is None or t > sts), None)

        later_same_stage = any(
            stage is not None and next(
                (p.get("reviewed") or p.get("stage") for p in reversed(packets)
                 if spawns[j]["ts"] is None or p["ts"] <= spawns[j]["ts"]),
                None,
            ) == stage
            for j in range(idx + 1, len(spawns))
        )
        explicit_interrupt = any(
            (sts is None or (it["ts"] or 0.0) > sts)
            and (next_sts is None or (it["ts"] or 0.0) <= next_sts)
            and _target_matches(it["args"].get("target"), tname, aid)
            for it in interrupts
        )
        completed = task_complete_ts is not None
        interrupted = (not completed) and (explicit_interrupt or (aborted and later_same_stage))
        abandoned = (not completed) and (not interrupted)
        order_ok = bool(
            completed
            and sts is not None
            and wait_ret_ts is not None
            and sts < task_complete_ts <= wait_ret_ts + 0.05
            and (next_tc_ts is None or task_complete_ts <= next_tc_ts)
        )

        total_completed += int(completed)
        total_order_ok += int(order_ok)
        total_abandoned += int(abandoned)
        total_interrupted += int(interrupted)
        total_nested_spawns += nested_spawns
        total_child_completes += child_completes
        total_waits += len(m_waits)
        total_timeouts += w_timeouts

        rows.append({
            "stage": stage,
            "task_name": tname,
            "fork_turns": fork_turns,
            "execs": execs,
            "completed": completed,
            "order_ok": order_ok,
            "interrupted": interrupted,
            "abandoned": abandoned,
            "nested_spawns": nested_spawns,
            "child_completes": child_completes,
            "waits": len(m_waits),
            "wait_timeouts": w_timeouts,
        })

    return {
        "spawns": len(spawns),
        "completed": total_completed,
        "order_ok": total_order_ok,
        "abandoned": total_abandoned,
        "interrupted": total_interrupted,
        "nested_spawns": total_nested_spawns,
        "child_completes": total_child_completes,
        "waits": total_waits,
        "wait_timeouts": total_timeouts,
        "packets_complete": packets_complete,
        "packets_total": packets_total,
        "children": rows,
    }


def summary_line(data: dict) -> str:
    """Format one compact summary line for metrics.summary_lines."""
    base = (
        f"fork completeness: {data['completed']}/{data['spawns']} completed "
        f"({data['order_ok']}/{data['completed']} order_ok, {data['interrupted']} interrupted, "
        f"{data['abandoned']} abandoned), waits {data['waits']} ({data['wait_timeouts']} timeouts), "
        f"nested_spawns {data['nested_spawns']}, child_completes {data['child_completes']}"
    )
    if data.get("packets_total"):
        base += f", packets {data['packets_complete']}/{data['packets_total']} complete"
    return base
