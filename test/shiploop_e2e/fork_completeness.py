"""Causal fork-completeness verifier for delegated ShipLoop E2E runs (Codex, Claude, Grok).

Checks:
- Codex: parent and child rollout logs (``home/**/rollout-*.jsonl``);
- Claude & Grok: normalized/native host event streams (``events.jsonl``),
plus ShipLoop's ``trace.jsonl`` and Improve ``packet.json`` files when present,
to verify spawned workers complete before parent wait return and parent
``shiploop complete``, with zero silently abandoned forks, nested spawns, or
child ``shiploop complete`` calls (leaving child internals as ``None`` where a
host's stream does not expose them).
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
_CLAUDE_SPAWN_TOOLS = frozenset(("Agent", "Task"))


def _epoch(text: object) -> float | None:
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return float(text)
    if not isinstance(text, str) or not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _event_ts(rec: dict) -> float | None:
    for key in ("timestamp", "ts", "t"):
        ts = _epoch(rec.get(key))
        if ts is not None:
            return ts
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


def _stage_at(packets: list[dict], ts: float | None) -> str | None:
    """Resolve the active or reviewed ShipLoop stage in effect at ``ts``."""
    if not packets or ts is None:
        return None
    for packet in reversed(packets):
        if packet["ts"] <= ts:
            return packet.get("reviewed") or packet.get("stage")
    return None


def _summarize(
    rows: list[dict],
    packets_complete: int,
    packets_total: int,
    *,
    child_internals_observable: bool = True,
) -> dict:
    """Aggregate per-child fork completeness rows into one shared result mapping."""
    return {
        "spawns": len(rows),
        "completed": sum(int(bool(r["completed"])) for r in rows),
        "order_ok": sum(int(bool(r["order_ok"])) for r in rows),
        "abandoned": sum(int(bool(r["abandoned"])) for r in rows),
        "interrupted": sum(int(bool(r["interrupted"])) for r in rows),
        "nested_spawns": (
            sum(int(r["nested_spawns"] or 0) for r in rows) if child_internals_observable else None
        ),
        "child_completes": (
            sum(int(r["child_completes"] or 0) for r in rows) if child_internals_observable else None
        ),
        "waits": sum(int(r["waits"] or 0) for r in rows),
        "wait_timeouts": sum(int(r["wait_timeouts"] or 0) for r in rows),
        "packets_complete": packets_complete,
        "packets_total": packets_total,
        "children": rows,
    }


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
    return None


def _target_matches(target: object, tname: object, aid: object) -> bool:
    if not isinstance(target, str) or not target:
        return False
    if aid and target == aid:
        return True
    if tname and (target == tname or str(tname).endswith("/" + target) or target.endswith("/" + str(tname))):
        return True
    return False


def _collect_codex(
    parents: list[list[dict]],
    children: list[tuple[dict, list[dict]]],
    run_dir: Path | None,
) -> dict | None:
    spawns: list[dict] = []
    waits: list[dict] = []
    interrupts: list[dict] = []
    pending: dict[str, dict] = {}
    for recs in parents:
        for rec in recs:
            if rec.get("type") != "response_item":
                continue
            p = rec.get("payload")
            if not isinstance(p, dict):
                continue
            ts = _epoch(rec.get("timestamp"))
            pt = p.get("type")
            if pt == "function_call":
                cid = p.get("call_id")
                name = p.get("name")
                entry = {"ts": ts, "ret_ts": None, "args": _parse_json_obj(p.get("arguments")), "out": {}}
                if isinstance(cid, str):
                    pending[cid] = entry
                if name == "spawn_agent":
                    spawns.append(entry)
                elif name == "wait_agent":
                    waits.append(entry)
                elif name == "interrupt_agent":
                    interrupts.append(entry)
            elif pt == "function_call_output":
                cid = p.get("call_id")
                entry = pending.get(cid) if isinstance(cid, str) else None
                if entry is not None:
                    entry["ret_ts"] = ts
                    entry["out"] = _parse_json_obj(p.get("output"))

    if not spawns:
        return None

    spawns.sort(key=lambda e: e["ts"] or 0.0)
    packets, trace_completes = _trace_info(run_dir)
    packets_complete, packets_total = _improve_packets(run_dir)

    used_children: set[int] = set()
    rows: list[dict] = []

    for idx, sp in enumerate(spawns):
        sts = sp["ts"]
        next_sts = spawns[idx + 1]["ts"] if idx + 1 < len(spawns) else None
        out_map = sp.get("out") or {}
        tname = out_map.get("task_name") or sp["args"].get("task_name")
        aid = out_map.get("agent_id")
        fork_turns = sp["args"].get("fork_turns")
        stage = _stage_at(packets, sts)

        matched = _match_child(sp, children, used_children)
        nested_spawns = child_completes = execs = 0
        task_complete_ts: float | None = None
        aborted = False
        if matched is not None:
            _meta, crecs = matched
            for rec in _child_own_slice(crecs, sts):
                rtype = rec.get("type")
                cp = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
                if rtype == "response_item":
                    cpt = cp.get("type")
                    if cpt == "function_call" and cp.get("name") == "spawn_agent":
                        nested_spawns += 1
                    elif cpt == "custom_tool_call" and cp.get("name") == "exec":
                        execs += 1
                        if SHIPLOOP_COMPLETE_CMD.search(str(cp.get("input") or "")):
                            child_completes += 1
                    elif cpt == "function_call" and cp.get("name") in ("exec_command", "shell", "shell_command"):
                        execs += 1
                        if SHIPLOOP_COMPLETE_CMD.search(str(cp.get("arguments") or "")):
                            child_completes += 1
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
            stage is not None and _stage_at(packets, spawns[j]["ts"]) == stage
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

    return _summarize(rows, packets_complete, packets_total, child_internals_observable=True)


def _before_parent_complete(
    spawn_seq: int,
    ret_seq: int | None,
    spawn_ts: float | None,
    ret_ts: float | None,
    parent_completes: list[tuple[int, float | None]],
    trace_completes: list[float],
) -> bool:
    if ret_seq is None:
        return False
    next_parent = next((item for item in parent_completes if item[0] > spawn_seq), None)
    if next_parent is not None and ret_seq >= next_parent[0]:
        return False
    if spawn_ts is not None and ret_ts is not None:
        next_tc = next((t for t in trace_completes if t > spawn_ts), None)
        if next_tc is not None and ret_ts > next_tc:
            return False
    return True


def _collect_claude(events: list[dict], run_dir: Path | None) -> dict | None:
    spawns: list[dict] = []
    by_id: dict[str, dict] = {}
    nested_by_parent: dict[str, int] = {}
    child_completes_by_parent: dict[str, int] = {}
    child_execs_by_parent: dict[str, int] = {}
    stops: list[tuple[int, object]] = []
    parent_completes: list[tuple[int, float | None]] = []

    for seq, ev in enumerate(events):
        etype = ev.get("type")
        parent_id = ev.get("parent_tool_use_id")
        ts = _event_ts(ev)
        if etype == "assistant":
            for block in (ev.get("message") or {}).get("content") or []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = str(block.get("name") or "")
                bid = block.get("id")
                args = block.get("input") if isinstance(block.get("input"), dict) else {}
                if parent_id is None:
                    if name in _CLAUDE_SPAWN_TOOLS:
                        entry = {
                            "seq": seq,
                            "ts": ts,
                            "id": bid,
                            "args": args,
                            "ret_seq": None,
                            "ret_ts": None,
                            "background": bool(args.get("run_in_background")),
                            "agent_id": None,
                            "bg_done_seq": None,
                            "bg_done_ts": None,
                        }
                        spawns.append(entry)
                        if isinstance(bid, str) and bid:
                            by_id[bid] = entry
                    elif name == "TaskStop":
                        stops.append((seq, args.get("task_id") or args.get("id")))
                    elif name == "Bash" and SHIPLOOP_COMPLETE_CMD.search(str(args.get("command") or "")):
                        parent_completes.append((seq, ts))
                elif isinstance(parent_id, str):
                    if name in _CLAUDE_SPAWN_TOOLS:
                        nested_by_parent[parent_id] = nested_by_parent.get(parent_id, 0) + 1
                    elif name == "Bash":
                        child_execs_by_parent[parent_id] = child_execs_by_parent.get(parent_id, 0) + 1
                        if SHIPLOOP_COMPLETE_CMD.search(str(args.get("command") or "")):
                            child_completes_by_parent[parent_id] = child_completes_by_parent.get(parent_id, 0) + 1
        elif etype == "user" and parent_id is None:
            for block in (ev.get("message") or {}).get("content") or []:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                tid = block.get("tool_use_id")
                entry = by_id.get(tid) if isinstance(tid, str) else None
                if entry is None:
                    continue
                content = block.get("content")
                text = content if isinstance(content, str) else json.dumps(content or "")
                parsed = _parse_json_obj(content)
                agent_id = parsed.get("agentId") or parsed.get("agent_id") or parsed.get("task_id")
                if not agent_id:
                    m = re.search(r"agentId:\s*([A-Za-z0-9_-]+)", text)
                    if m:
                        agent_id = m.group(1)
                if isinstance(agent_id, str) and agent_id:
                    entry["agent_id"] = agent_id
                if entry["background"] and (
                    parsed.get("status") == "async_launched" or "async agent launched" in text.lower()
                ):
                    continue
                if entry["ret_seq"] is None:
                    entry["ret_seq"] = seq
                    entry["ret_ts"] = ts
        elif etype == "system" and ev.get("subtype") == "task_notification":
            tid = ev.get("task_id") or ev.get("agent_id")
            status = str(ev.get("status") or "")
            for entry in spawns:
                if (tid and tid in (entry["id"], entry["agent_id"])) and status in ("completed", "done", ""):
                    entry["bg_done_seq"] = seq
                    entry["bg_done_ts"] = ts

    if not spawns:
        return None

    packets, trace_completes = _trace_info(run_dir)
    packets_complete, packets_total = _improve_packets(run_dir)
    rows: list[dict] = []

    for sp in spawns:
        sts = sp["ts"]
        done_seq = sp["bg_done_seq"] if sp["bg_done_seq"] is not None else sp["ret_seq"]
        done_ts = sp["bg_done_ts"] if sp["bg_done_ts"] is not None else sp["ret_ts"]
        explicit_stop = any(
            s_seq > sp["seq"] and target in (sp["id"], sp["agent_id"])
            for s_seq, target in stops
        )
        completed = done_seq is not None and not explicit_stop
        interrupted = (not completed) and explicit_stop
        abandoned = (not completed) and (not interrupted)
        order_ok = bool(completed and _before_parent_complete(
            sp["seq"], done_seq, sts, done_ts, parent_completes, trace_completes
        ))
        sid = sp["id"] or ""
        rows.append({
            "stage": _stage_at(packets, sts),
            "task_name": sp["args"].get("description") or sp["args"].get("subagent_type") or sid,
            "fork_turns": sp["args"].get("subagent_type"),
            "execs": child_execs_by_parent.get(sid, 0),
            "completed": completed,
            "order_ok": order_ok,
            "interrupted": interrupted,
            "abandoned": abandoned,
            "nested_spawns": nested_by_parent.get(sid, 0),
            "child_completes": child_completes_by_parent.get(sid, 0),
            "waits": 0,
            "wait_timeouts": 0,
        })

    return _summarize(rows, packets_complete, packets_total, child_internals_observable=True)


def _collect_grok(events: list[dict], run_dir: Path | None) -> dict | None:
    spawns: list[dict] = []
    waits: list[dict] = []
    kills: list[tuple[int, object]] = []
    parent_completes: list[tuple[int, float | None]] = []
    by_call_id: dict[str, dict] = {}

    for seq, ev in enumerate(events):
        etype = ev.get("type")
        ts = _event_ts(ev)
        if etype == "tool_call":
            cid = ev.get("toolCallId")
            tool = str(ev.get("toolName") or ev.get("title") or "")
            args = ev.get("rawInput") if isinstance(ev.get("rawInput"), dict) else {}
            if tool == "spawn_subagent":
                entry = {
                    "seq": seq,
                    "ts": ts,
                    "id": cid,
                    "args": args,
                    "ret_seq": None,
                    "ret_ts": None,
                    "status": None,
                    "out": {},
                }
                spawns.append(entry)
                if isinstance(cid, str) and cid:
                    by_call_id[cid] = entry
            elif tool == "get_command_or_subagent_output":
                entry = {"seq": seq, "ts": ts, "id": cid, "args": args, "ret_seq": None, "ret_ts": None, "out": {}}
                waits.append(entry)
                if isinstance(cid, str) and cid:
                    by_call_id[cid] = entry
            elif tool == "kill_command_or_subagent":
                kills.append((seq, args.get("task_id") or args.get("id") or args.get("target")))
            elif tool == "run_terminal_command" and SHIPLOOP_COMPLETE_CMD.search(str(args.get("command") or "")):
                parent_completes.append((seq, ts))
        elif etype == "tool_call_update":
            cid = ev.get("toolCallId")
            status = ev.get("status")
            entry = by_call_id.get(cid) if isinstance(cid, str) else None
            if entry is not None and status in ("completed", "failed"):
                entry["ret_seq"] = seq
                entry["ret_ts"] = ts
                entry["status"] = status
                if isinstance(ev.get("rawOutput"), dict):
                    entry["out"] = ev["rawOutput"]

    if not spawns:
        return None

    packets, trace_completes = _trace_info(run_dir)
    packets_complete, packets_total = _improve_packets(run_dir)
    rows: list[dict] = []

    for idx, sp in enumerate(spawns):
        s_seq = sp["seq"]
        next_seq = spawns[idx + 1]["seq"] if idx + 1 < len(spawns) else None
        out_map = sp.get("out") or {}
        tid = out_map.get("task_id") or out_map.get("id") or out_map.get("subagent_id")
        tname = out_map.get("task_name") or sp["args"].get("task_name") or tid or sp["id"]
        background = bool(sp["args"].get("background"))

        m_waits: list[dict] = []
        for w in waits:
            if w["seq"] < s_seq or (next_seq is not None and w["seq"] >= next_seq):
                continue
            targets = list(w["args"].get("task_ids") or w["args"].get("ids") or [])
            for key in ("task_id", "id"):
                if isinstance(w["args"].get(key), str):
                    targets.append(w["args"][key])
            if targets and not any(t in (tid, tname, sp["id"]) for t in targets):
                continue
            m_waits.append(w)

        w_timeouts = sum(
            1 for w in m_waits
            if (w.get("out") or {}).get("timed_out") is True or (w.get("out") or {}).get("status") == "timed_out"
        )
        fin_waits = [
            w for w in m_waits
            if w.get("ret_seq") is not None
            and (w.get("out") or {}).get("timed_out") is not True
            and (w.get("out") or {}).get("status") not in ("running", "timed_out")
        ]

        explicit_kill = any(
            k_seq > s_seq and (next_seq is None or k_seq <= next_seq) and target in (tid, tname, sp["id"])
            for k_seq, target in kills
        )

        if background:
            fin_seq = fin_waits[-1]["ret_seq"] if fin_waits else None
            fin_ts = fin_waits[-1]["ret_ts"] if fin_waits else None
        else:
            fin_seq = sp["ret_seq"] if sp["status"] == "completed" else None
            fin_ts = sp["ret_ts"] if sp["status"] == "completed" else None

        completed = fin_seq is not None and not explicit_kill
        interrupted = (not completed) and (explicit_kill or sp["status"] == "failed")
        abandoned = (not completed) and (not interrupted)
        order_ok = bool(completed and _before_parent_complete(
            s_seq, fin_seq, sp["ts"], fin_ts, parent_completes, trace_completes
        ))

        rows.append({
            "stage": _stage_at(packets, sp["ts"]),
            "task_name": tname,
            "fork_turns": None,
            "execs": None,
            "completed": completed,
            "order_ok": order_ok,
            "interrupted": interrupted,
            "abandoned": abandoned,
            "nested_spawns": None,
            "child_completes": None,
            "waits": len(m_waits),
            "wait_timeouts": w_timeouts,
        })

    return _summarize(rows, packets_complete, packets_total, child_internals_observable=False)


def collect(out: Path, run_dir: Path | None = None) -> dict | None:
    """Compute causal fork-completeness metrics for a delegated ShipLoop E2E run."""
    parents, children = _find_rollouts(out)
    if parents or children:
        return _collect_codex(parents, children, run_dir)
    events_path = out / "events.jsonl"
    if not events_path.is_file():
        return None
    events = _read_records(events_path)
    if not events:
        return None
    claude = _collect_claude(events, run_dir)
    if claude is not None:
        return claude
    return _collect_grok(events, run_dir)


def summary_line(data: dict) -> str:
    """Format one compact summary line for metrics.summary_lines."""
    nested = "n/a" if data.get("nested_spawns") is None else str(data["nested_spawns"])
    child_comp = "n/a" if data.get("child_completes") is None else str(data["child_completes"])
    base = (
        f"fork completeness: {data['completed']}/{data['spawns']} completed "
        f"({data['order_ok']}/{data['completed']} order_ok, {data['interrupted']} interrupted, "
        f"{data['abandoned']} abandoned), waits {data['waits']} ({data['wait_timeouts']} timeouts), "
        f"nested_spawns {nested}, child_completes {child_comp}"
    )
    if data.get("packets_total"):
        base += f", packets {data['packets_complete']}/{data['packets_total']} complete"
    return base
