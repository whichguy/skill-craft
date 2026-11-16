#!/usr/bin/env python3
"""score.py: the measures of the parallel-plan-execution probes, a merged timeline and an ASCII Gantt.

Apparatus for docs/experiments/parallel-plan-execution-20261114 (see its README, "Measures" and Amendments A2 to A4). Every
measure is a script reading the trial's ledger, the host's raw events and the invocation record; no judge is involved.

  score.py TRIAL...             score each trial folder: writes score.json, timeline.txt, gantt.txt, prints a summary
  score.py --compare TRIAL...   one table across trials; an arm is compared only with the A0 of its own host, version, model,
                                effort, feature profile and fixture, and only when both trials are valid
  score.py --shapes TRIAL       the host event types a trial's stream held (to extend the readers)

A trial folder holds work/plan.json, work/run/ (ledger.jsonl, out/), events.raw.jsonl (one record per host stdout
line: ``recv`` seconds, then ``ev`` the parsed event or ``raw`` the text), invocation.json and packet.md.
"""

from __future__ import annotations

import argparse
import collections
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dagkit  # noqa: E402
import ticketfix  # noqa: E402  (the real-repository oracle of README Amendment A14)
import writefix  # noqa: E402

FINAL_RE = re.compile(r"^FINAL (\{.*\})\s*$", re.M)
RUN_CALL = re.compile(r"dagkit\.py\s+(?:run|begin)\b")
# Whether a host's raw stream says which agent ran a tool call. Claude's stream-json carries parent_tool_use_id; Codex and
# Grok are False until E1 shows their streams attribute (README, Amendment A2).
ATTRIBUTABLE = {"claude": True, "codex": False, "grok": False}
CLAUDE_SPAWN = ("agent", "task")


def shell_parallel(command: str) -> bool:
    """True when a shell command text backgrounds or fans out work (not a path that merely contains the word parallel)."""
    c = command
    for token in ("2>&1", ">&2", "1>&2", "&>", "&&"):
        c = c.replace(token, " ")
    if "&" in c:
        return True
    return bool(re.search(r"\b(nohup|setsid|disown)\b|xargs\s+(-\S+\s+)*-P|(^|[|;]\s*)parallel\s|;\s*wait\b", c))


# ------------------------------------------------------------------ ledger measures (host independent)

def ancestors(plan: dict) -> dict:
    anc: dict = {}
    for s in plan["steps"]:
        anc[s["id"]] = set(s["deps"]).union(*(anc[d] for d in s["deps"])) if s["deps"] else set()
    return anc


def peak_concurrency(intervals: list) -> int:
    marks = sorted([(a, 1) for a, _ in intervals] + [(b, -1) for _, b in intervals], key=lambda m: (m[0], m[1]))
    now = peak = 0
    for _, delta in marks:
        now += delta
        peak = max(peak, now)
    return peak


def ledger_measures(plan: dict, events: list, run: dagkit.Run | None = None) -> dict:
    """M1, M3, M4, M5, M9 and M11 from the ledger alone (the plan fixes what is independent)."""
    state = dagkit.derive(plan, events)
    deps = {s["id"]: s["deps"] for s in plan["steps"]}
    ids = [s["id"] for s in plan["steps"]]
    last_ts = events[-1]["ts"] if events else 0.0
    iv = {i: (state[i]["start"], state[i]["end"] if state[i]["end"] is not None else last_ts)
          for i in ids if state[i]["start"] is not None}
    starts = [a for a, _ in iv.values()]
    ended = [state[i]["end"] for i in ids if state[i]["end"] is not None]
    out: dict = {"steps": len(ids), "started": len(iv), "ended": len(ended)}
    out["makespan_s"] = round(max(ended) - min(starts), 3) if starts and ended else None
    out["first_start_ts"], out["last_end_ts"] = (min(starts) if starts else None), (max(ended) if ended else None)
    secs = [s.get("kit", {}).get("seconds") for s in plan["steps"]]
    declared = all(isinstance(x, (int, float)) for x in secs)      # a task step declares no duration: its time is the agent's
    out["serial_sum_declared_s"] = sum(secs) if declared else None
    cp: dict = {}
    if declared:
        for s in plan["steps"]:
            cp[s["id"]] = max([cp[d] for d in s["deps"]], default=0) + s["kit"]["seconds"]
    out["critical_path_declared_s"] = max(cp.values()) if cp else None
    out["peak_concurrency"] = peak_concurrency(list(iv.values())) if iv else 0
    anc = ancestors(plan)
    pairs = []
    for n, a in enumerate(ids):
        for b in ids[n + 1:]:
            if a in anc[b] or b in anc[a] or a not in iv or b not in iv:
                continue
            overlap = max(0.0, min(iv[a][1], iv[b][1]) - max(iv[a][0], iv[b][0]))
            shorter = max(1e-9, min(iv[a][1] - iv[a][0], iv[b][1] - iv[b][0]))
            pairs.append({"pair": [a, b], "overlap_s": round(overlap, 3), "frac_of_shorter": round(overlap / shorter, 3)})
    out["independent_pairs"] = len(pairs)
    out["pairs_overlapped"] = sum(1 for p in pairs if p["frac_of_shorter"] >= 0.5)
    out["pairs"] = pairs
    refused = [e for e in events if e["kind"] == "refused"]
    out["refused"] = len(refused)
    out["refused_by_category"] = dict(collections.Counter(e["detail"].get("category") or "uncategorised" for e in refused))
    out["starts_before_dep_end"] = sum(
        1 for i in iv for d in deps[i] if state[d]["end_seq"] is None or state[i]["start_seq"] < state[d]["end_seq"])
    out["steps_started_twice"] = sum(1 for i in ids if state[i]["starts"] > 1)
    out["terminal_duplicates"] = sum(1 for i in ids if state[i]["terminals"] > 1)
    out["steps_without_end"] = sum(1 for i in ids if state[i]["state"] == "running")
    out["claims_without_start"] = sum(1 for i in ids if state[i]["claimed"] and not state[i]["starts"])
    settled = {i for i in ids if dagkit._settled_this_attempt(events, i)}   # the current attempt of each step settled (a retry settles again)
    settle_s = next((e["detail"].get("settle") for e in events if e["kind"] == "init"), 0) or 0
    out["settle_s"], out["settled_steps"] = settle_s, len(settled)
    out["settled_all"] = all(i in settled for i in ids if state[i]["end"] is not None) if settle_s else None   # a step that ended without its settle
    if run is not None and (run.dir / "meta.json").is_file():
        kind, line = dagkit.verdict(run)
        out["verify"], out["verify_line"] = kind, line
    out["expected_verdict"] = plan.get("expected_verdict", "OK")
    out["verify_as_expected"] = out.get("verify") == out["expected_verdict"]
    lat = {}
    for i in ids:
        if deps[i] and i in iv and all(state[d]["end"] is not None for d in deps[i]):
            lat[i] = round(iv[i][0] - max(state[d]["end"] for d in deps[i]), 3)
    out["dispatch_latency_s"] = lat
    out["dispatch_latency_mean_s"] = round(sum(lat.values()) / len(lat), 3) if lat else None
    scales = {e["detail"].get("scale") for e in events if e["kind"] in ("init", "start")}
    out["time_scale"] = sorted(s for s in scales if s is not None)
    out["scaled_trial"] = any(s != 1 for s in scales if s is not None)
    if plan.get("name") == "ragged6" and "S1" in iv and "S3" in iv:
        out["refill"] = bool(iv["S1"][0] <= iv["S3"][0] < iv["S1"][1])
    else:
        out["refill"] = None
    out["states"] = {i: state[i]["state"] for i in ids}
    return out


def fidelity(measures: dict, claim: dict | None) -> dict:
    """M7: the parent's FINAL object against the ledger; it must name every planned step exactly once."""
    if claim is None:
        return {"final_found": False, "fidelity_ok": False}
    states = measures["states"]
    actual = {"done": {i for i, s in states.items() if s == "done"}, "failed": {i for i, s in states.items() if s == "failed"},
              "not_run": {i for i, s in states.items() if s in ("blocked", "pending")}}
    out: dict = {"final_found": True}
    ok = True
    named = [str(x) for key in ("done", "failed", "not_run") for x in claim.get(key, [])]
    for key in ("done", "failed", "not_run"):
        said = set(map(str, claim.get(key, [])))
        out[f"false_{key}"] = sorted(said - actual[key])
        out[f"missed_{key}"] = sorted(actual[key] - said)
        ok = ok and not out[f"false_{key}"] and not out[f"missed_{key}"]
    out["unaccounted"] = sorted(set(states) - set(named))
    out["listed_twice"] = sorted(x for x in set(named) if named.count(x) > 1)
    out["unknown_listed"] = sorted(set(named) - set(states))
    out["running_at_end"] = sorted(i for i, s in states.items() if s == "running")
    out["fidelity_ok"] = bool(ok and not out["unaccounted"] and not out["listed_twice"] and not out["unknown_listed"]
                              and not out["running_at_end"])
    return out


# ------------------------------------------------------------------ host events (best effort; refined after E1)

def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_text_of(c.get("text") if isinstance(c, dict) and "text" in c else c.get("content", "") if isinstance(c, dict) else c)
                         for c in content)
    return ""


def normalize(host: str, rec: dict) -> list:
    """Host events as {t, actor, kind, name, text, full, extra}; kinds: call, spawn, wait, return, result, text, final, usage.

    ``text`` is cut for display; ``full`` keeps the whole command or prompt for classification."""
    t, ev = rec.get("recv"), rec.get("ev")
    if not isinstance(ev, dict):
        return []
    typ = ev.get("type")
    out = []

    def add(kind, actor="parent", name="", text="", full=None, **extra):
        out.append({"t": t, "actor": actor, "kind": kind, "name": name, "text": text[:140] if kind in ("call", "spawn") else text,
                    "full": text if full is None else full, **extra})

    if host == "claude":
        owner = ev.get("parent_tool_use_id")
        actor = f"agent:{str(owner)[-6:]}" if owner else "parent"
        if typ == "assistant":
            msg = ev.get("message") or {}
            for block in msg.get("content") or []:
                if block.get("type") == "tool_use":
                    name = block.get("name", "")
                    inp = block.get("input") or {}
                    spawn = name.lower() in CLAUDE_SPAWN
                    text = (str(inp.get("description") or "") + " | " + str(inp.get("prompt") or "")) if spawn else str(inp.get("command") or json.dumps(inp))
                    add("spawn" if spawn else "call", actor, name, text, id=block.get("id"), background=bool(inp.get("run_in_background")))
                elif block.get("type") == "text" and block.get("text", "").strip():
                    add("text", actor, "", block["text"])
            usage = msg.get("usage")
            if usage and not owner:
                add("usage", actor, "", "", usage=usage)
        elif typ == "user":
            for block in (ev.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    add("result", actor, "", _text_of(block.get("content"))[:140], id=block.get("tool_use_id"))
        elif typ == "result":
            add("final", "parent", "", str(ev.get("result") or ""), usage=ev.get("usage"), cost=ev.get("total_cost_usd"),
                model_usage=ev.get("modelUsage"), turns=ev.get("num_turns"), duration_ms=ev.get("duration_ms"))
        elif typ == "system":
            add("system", "parent", str(ev.get("subtype") or ""), json.dumps({k: v for k, v in ev.items() if k in ("subtype", "model", "description", "task_id", "tool_use_id", "status", "tools")})[:300])
    elif host == "codex":
        thread = ev.get("thread_id") or (ev.get("item") or {}).get("thread_id")
        item = ev.get("item") or {}
        itype = item.get("type")
        actor = "parent" if not thread else f"thread:{str(thread)[-6:]}"
        if typ in ("item.started", "item.completed"):
            started = typ == "item.started"
            if itype == "command_execution":
                add("call" if started else "result", actor, "shell", str(item.get("command") or ""), id=item.get("id"), exit=item.get("exit_code"))
            elif itype == "agent_message" and not started:
                add("text", actor, "", str(item.get("text") or ""))
            elif itype == "collab_tool_call":  # Codex's multi-agent tools: spawn_agent, wait, send_input, close_agent, ...
                tool = str(item.get("tool") or "")
                if "spawn" in tool:
                    kind = "spawn" if started else "result"
                elif "wait" in tool:
                    kind = "wait" if started else "return"
                else:
                    kind = "call" if started else "result"
                detail = {k: item.get(k) for k in ("prompt", "receiver_thread_ids", "agents_states", "status") if item.get(k) not in (None, [], {})}
                add(kind, actor, tool, json.dumps(detail)[:300], id=item.get("id"))
            elif itype and itype not in ("reasoning", "agent_message", "error"):
                add("call" if started else "result", actor, str(item.get("tool") or item.get("name") or itype),
                    json.dumps({k: v for k, v in item.items() if k in ("prompt", "status", "tool")})[:160], id=item.get("id"))
        elif typ == "turn.completed":
            add("usage", actor, "", "", usage=ev.get("usage"))
    elif host == "grok":
        if typ == "tool_call":
            name = str(ev.get("toolName") or ev.get("title") or "")
            low = name.lower()
            kind = "spawn" if low.startswith("spawn") else "wait" if ("subagent" in low and "output" in low) else "call"
            raw = ev.get("rawInput") or {}
            add(kind, "parent", name, str(raw.get("command") or raw.get("prompt") or json.dumps(raw)), id=ev.get("toolCallId"))
        elif typ == "tool_call_update" and ev.get("status") in ("completed", "failed"):
            add("result", "parent", "", "", id=ev.get("toolCallId"))
        elif typ == "text":
            add("text", "parent", "", str(ev.get("data") or ""))
        elif typ == "end":
            add("usage", "parent", "", "", usage=ev.get("usage"), cost=ev.get("total_cost_usd"))
    return out


def host_view(trial: Path, host: str) -> list:
    path = trial / "events.raw.jsonl"
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            out.extend(normalize(host, json.loads(line)))
        except ValueError:
            continue
    if host == "codex":   # the stream shows neither spawns nor children's commands; the rollout files do
        for th in codex_threads(trial):
            for c in th["calls"]:
                if c["kind"] == "agent_tool" and c["name"] == "spawn_agent":
                    out.append({"t": c["t"], "actor": "parent", "kind": "spawn", "name": "spawn_agent", "text": c["text"][:140], "full": c["text"]})
                elif c["kind"] == "cmd" and th["child"]:
                    out.append({"t": c["t"], "actor": th["actor"], "kind": "call", "name": "shell", "text": c["text"][:140], "full": c["text"]})
    elif host == "grok":  # re-attribute each call to the session the log says ran it
        _, owner = grok_agents(trial)
        for i in out:
            if i.get("id") in owner:
                i["actor"] = owner[i["id"]]
    out.sort(key=lambda i: (i["t"] is None, i["t"] or 0.0))
    return out



# ------------------------------------------------------------------ native agent records (each host's own account of its sub-agents)

def _epoch(iso: str) -> float:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def _jsonl(path: Path) -> list:
    rows = []
    if path.is_file():
        for line in path.read_text(errors="replace").splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def claude_agents(trial: Path) -> list:
    """Claude's stream carries task_started (with subagent_type), task_progress (tokens) and task_notification per sub-agent."""
    agents: dict = {}
    for rec in _jsonl(trial / "events.raw.jsonl"):
        ev = rec.get("ev") or {}
        if ev.get("type") != "system":
            continue
        sub, tid = ev.get("subtype"), ev.get("task_id")
        if sub == "task_started" and ev.get("subagent_type"):
            agents[tid] = {"id": tid, "actor": f"agent:{str(ev.get('tool_use_id'))[-6:]}", "kind": ev.get("subagent_type"),
                           "start": rec["recv"], "end": None, "background": ev.get("is_backgrounded"), "depth": ev.get("spawn_depth"),
                           "tokens": None, "success": None}
        elif tid in agents and sub == "task_progress":
            agents[tid]["tokens"] = (ev.get("usage") or {}).get("total_tokens", agents[tid]["tokens"])
        elif tid in agents and sub == "task_notification":
            agents[tid]["end"], agents[tid]["success"] = rec["recv"], ev.get("status") == "completed"
        elif tid in agents and sub == "task_updated" and agents[tid]["end"] is None and (ev.get("patch") or {}).get("status") == "completed":
            agents[tid]["end"] = rec["recv"]
    return list(agents.values())


def _codex_cmds(payload: dict) -> list:
    """The shell commands inside a Codex `exec` tool call (a script wrapped around tools.exec_command)."""
    text = str(payload.get("input") or payload.get("arguments") or "")
    out = []
    for m in re.finditer(r'cmd:\s*("(?:[^"\\]|\\.)*")', text):
        try:
            out.append(json.loads(m.group(1)))
        except ValueError:
            continue
    return out


def codex_threads(trial: Path) -> list:
    """One record per Codex thread from its rollout file: the parent and every sub-agent (its metadata names its parent and depth)."""
    out = []
    for path in sorted((trial / "home" / ".codex" / "sessions").glob("*/*/*/rollout-*.jsonl")):
        rows = _jsonl(path)
        meta = next((r["payload"] for r in rows if r.get("type") == "session_meta" and isinstance(r.get("payload"), dict)), None)
        if not meta or not rows:
            continue
        source = meta.get("source")
        spawn = ((source.get("subagent") or {}).get("thread_spawn") if isinstance(source, dict) else None) or None
        tokens = [r["payload"]["info"]["total_token_usage"] for r in rows if isinstance(r.get("payload"), dict)
                  and r["payload"].get("type") == "token_count" and r["payload"].get("info")]
        calls = []
        for r in rows:
            pl = r.get("payload")
            if isinstance(pl, dict) and pl.get("type") in ("custom_tool_call", "function_call") and r.get("timestamp"):
                ts = _epoch(r["timestamp"])
                if pl.get("name") in ("spawn_agent", "wait_agent", "close_agent", "send_input", "resume_agent"):
                    calls.append({"t": ts, "kind": "agent_tool", "name": pl["name"], "text": str(pl.get("arguments") or "")[:160]})
                else:
                    calls += [{"t": ts, "kind": "cmd", "name": "shell", "text": c} for c in _codex_cmds(pl)]
        out.append({"id": meta.get("id"), "actor": f"thread:{str(meta.get('id'))[-6:]}" if spawn else "parent", "child": bool(spawn),
                    "depth": (spawn or {}).get("depth"), "nickname": meta.get("agent_nickname"), "version": meta.get("multi_agent_version"),
                    "start": _epoch(rows[0]["timestamp"]), "end": _epoch(rows[-1]["timestamp"]), "tokens": tokens[-1] if tokens else None,
                    "calls": calls})
    return out


def grok_agents(trial: Path) -> tuple[list, dict]:
    """(sub-agent records, tool_call_id to actor) from Grok's unified.jsonl, which names every tool call's session."""
    rows = _jsonl(trial / "home" / ".grok" / "logs" / "unified.jsonl")
    agents: dict = {}
    session_of: dict = {}
    for r in rows:
        msg, ctx = r.get("msg", ""), r.get("ctx") or {}
        if msg == "subagent spawn credentials" and ctx.get("subagent_id"):
            agents[ctx["subagent_id"]] = {"id": ctx["subagent_id"], "actor": f"agent:{ctx['subagent_id'][-6:]}", "kind": ctx.get("subagent_type"),
                                          "model": ctx.get("effective_model"), "start": _epoch(r["ts"]), "end": None, "success": None,
                                          "tokens": None, "turns": None}
        elif msg == "subagent completed" and ctx.get("subagent_id") in agents:
            a = agents[ctx["subagent_id"]]
            a.update(end=_epoch(r["ts"]), success=ctx.get("success"), turns=ctx.get("turns"), tokens=ctx.get("total_tokens"), duration_ms=ctx.get("duration_ms"))
        elif msg == "shell.tool.exec_done" and ctx.get("tool_call_id"):
            session_of[ctx["tool_call_id"]] = r.get("sid")
    owner = {}
    for call_id, sid in session_of.items():
        child = next((a for aid, a in agents.items() if sid and (aid == sid or aid.endswith(sid[-8:]))), None)
        owner[call_id] = child["actor"] if child else "parent"
    return list(agents.values()), owner


def native_agents(trial: Path, host: str) -> dict:
    """The host's own record of its sub-agents: {"source", "agents": [...]} with start and end seconds (epoch), kind, depth, tokens."""
    if host == "claude":
        return {"source": "claude stream (system task events)", "agents": claude_agents(trial)}
    if host == "codex":
        threads = codex_threads(trial)
        return {"source": "codex rollout files", "agents": [a for a in threads if a["child"]], "threads": len(threads), "parent": next((a for a in threads if not a["child"]), None)}
    if host == "grok":
        agents, _ = grok_agents(trial)
        return {"source": "grok logs/unified.jsonl", "agents": agents}
    return {"source": None, "agents": []}


def agent_peak(agents: list) -> int:
    return peak_concurrency([(a["start"], a["end"]) for a in agents if a.get("start") and a.get("end")])


def _load(text: str) -> dict | None:
    try:
        return json.loads(text)
    except ValueError:
        return None


def final_claim(view: list) -> dict | None:
    """The parent's last FINAL object; a child's report is not the run's report. A host that streams its closing message in
    pieces (Grok's text deltas) is read from the trailing run of the parent's text, joined."""
    pieces: list = []
    for item in reversed(view):
        if item["actor"] != "parent":
            continue
        if item["kind"] in ("final", "text"):
            found = FINAL_RE.findall(item["text"])
            if found:
                return _load(found[-1])
            if item["kind"] == "text":
                pieces.append(item["text"])
        elif item["kind"] in ("call", "spawn", "wait", "return", "result"):
            break
    found = FINAL_RE.findall("".join(reversed(pieces)))
    return _load(found[-1]) if found else None


def tokens(view: list, host: str, native: dict | None = None) -> dict:
    """M8: what the host reports, or None for an unreported figure (never zero). ``input`` is the host's uncached input field;
    ``input_all`` adds cached reads and writes. Claude's result ``usage`` is the parent only, one result event per parent turn (summed
    here), and ``modelUsage`` is the whole run, cumulative (it is larger by the sub-agents' share); Codex's turn usage is the parent and each child's rollout adds its own;
    Grok's end usage includes its sub-agent sessions (established from its per-call log, journal R4)."""
    out: dict = {"source": None, "input": None, "output": None, "cache_read": None, "cost_usd": None, "peak_parent_input": None,
                 "children_included": None, "parent_input_all": None, "children_input_all": None, "input_all": None, "output_all": None}
    usages = [i for i in view if i["kind"] == "usage" and i.get("usage")]
    finals = [i for i in view if i["kind"] == "final"]
    if host == "claude" and finals and any(f.get("usage") for f in finals):
        # One result event per parent turn: a background sub-agent's completion re-enters the parent as a new turn in -p mode, each result's
        # usage covers its own turn only, and modelUsage and the cost are cumulative (README Amendment A7).
        u = {k: sum((f.get("usage") or {}).get(k) or 0 for f in finals)
             for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")}
        out.update(source="claude.result", input=u.get("input_tokens"), output=u.get("output_tokens"),
                   cache_read=u.get("cache_read_input_tokens"), cache_create=u.get("cache_creation_input_tokens"), cost_usd=finals[-1].get("cost"))
        parent_all = sum(u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        out["parent_input_all"] = parent_all
        mu = finals[-1].get("model_usage") or {}
        if mu:
            out["input_all"] = sum((m.get("inputTokens") or 0) + (m.get("cacheReadInputTokens") or 0) + (m.get("cacheCreationInputTokens") or 0) for m in mu.values())
            out["output_all"] = sum(m.get("outputTokens") or 0 for m in mu.values())
            out["children_input_all"] = out["input_all"] - parent_all
            out["children_included"] = False
        peaks = [(i["usage"].get("input_tokens") or 0) + (i["usage"].get("cache_read_input_tokens") or 0)
                 + (i["usage"].get("cache_creation_input_tokens") or 0) for i in usages]
        out["peak_parent_input"] = max(peaks) if peaks else None
    elif usages:
        def total(*keys):
            vals = [u["usage"].get(k) for u in usages for k in keys if u["usage"].get(k) is not None]
            return sum(vals) if vals else None
        out.update(source=f"{host}.usage", input=total("input_tokens"), output=total("output_tokens"),
                   cache_read=total("cache_read_input_tokens", "cached_input_tokens"), reasoning=total("reasoning_output_tokens"),
                   cost_usd=next((u.get("cost") for u in reversed(usages) if u.get("cost") is not None), None))
        if host == "codex":   # the parent's turn usage counts input_tokens including its cached part
            parent_in = out["input"]
            kids = [a["tokens"] for a in (native or {}).get("agents", []) if a.get("tokens")]
            out["children_without_usage"] = sum(1 for a in (native or {}).get("agents", []) if not a.get("tokens"))   # a total missing a child is incomplete, not smaller
            kids_in = sum(k.get("input_tokens") or 0 for k in kids)
            out.update(parent_input_all=parent_in, children_input_all=kids_in if native else None, children_included=False if native else None,
                       input_all=(parent_in or 0) + kids_in, output_all=(out["output"] or 0) + sum(k.get("output_tokens") or 0 for k in kids))
        else:   # grok: the end usage covers the parent and every sub-agent session (r1-grok-a3: 659,155 = parent 185,909 + five children 473,246, from the per-call log)
            whole = (out["input"] or 0) + (out["cache_read"] or 0)
            kids = bool((native or {}).get("agents"))
            out.update(parent_input_all=None if kids else whole, children_included=True if kids else None, input_all=whole, output_all=out["output"])
    return out


def mechanism(view: list, measures: dict, attributable: bool = False) -> dict:
    """M10: how the work was run. ``native-agents`` needs the kit's run calls attributed to child agents; spawns beside
    parent-run steps are ``parent-executed``, and where the host cannot attribute calls the class says so."""
    spawns = [i for i in view if i["kind"] == "spawn"]
    calls = [i for i in view if i["kind"] == "call" and RUN_CALL.search(i.get("full") or i["text"])]
    shell_par = [i for i in view if i["kind"] == "call" and "dagkit.py" in (i.get("full") or i["text"]) and shell_parallel(i.get("full") or i["text"])]
    by_actor = collections.Counter(c["actor"] for c in calls)
    by_child = sum(n for a, n in by_actor.items() if a != "parent")
    peak = measures.get("peak_concurrency", 0)
    if shell_par:
        kind = "shell-parallel"
    elif spawns and attributable:
        kind = "native-agents" if calls and by_child == len(calls) else "parent-executed" if by_child == 0 else "mixed"
    elif spawns:
        kind = "native-agents-unattributed" if peak > 1 else "native-agents-serial-unattributed"
    elif peak > 1:
        kind = "unknown-parallel"
    elif calls:
        kind = "parent-executed"
    else:
        kind = "serial"
    return {"kind": kind, "spawns": len(spawns), "run_calls": len(calls), "run_calls_by_actor": dict(by_actor),
            "attributable_host": attributable, "background_spawns": sum(1 for s in spawns if s.get("background"))}



def answers(trial: Path, plan: dict) -> dict | None:
    """Each task's recorded answer against the oracle the launcher wrote beside work/ (None for a timed-unit plan)."""
    oracle = trial / "oracle.json"
    if not oracle.is_file():
        return None
    expected = json.loads(oracle.read_text())
    got, rows = 0, {}
    for s in plan["steps"]:
        path = trial / "work" / "run" / "out" / f"{s['id']}.json"
        recorded = json.loads(path.read_text()).get("result", {}).get("answer") if path.is_file() else None
        ok = recorded is not None and recorded == expected.get(s["id"])
        got += ok
        rows[s["id"]] = {"expected": expected.get(s["id"]), "recorded": recorded, "correct": ok}
    return {"correct": got, "total": len(plan["steps"]), "all_correct": got == len(plan["steps"]), "tasks": rows,
            "expected_final": expected.get(plan["steps"][-1]["id"])}


def tails(view: list, events: list, proc_end: float | None) -> dict:
    """M6: seconds from the process's exit back to the last work terminal event, the parent's final report and the last
    collection return, kept apart so late chatter cannot hide a long tail."""
    ends = [e["ts"] for e in events if e["kind"] in ("end", "fail")]
    report = next((i["t"] for i in view if i["kind"] in ("text", "final") and i["actor"] == "parent" and FINAL_RE.search(i["text"])), None)
    if report is None:
        marks = [i["t"] for i in view if i["kind"] in ("final", "usage") and i["actor"] == "parent" and i["t"]]
        report = max(marks) if marks else None
    returns = [i["t"] for i in view if i["kind"] == "return" and i["t"]]

    def tail(t):
        return round(proc_end - t, 3) if (proc_end and t) else None
    return {"tail_from_last_end_s": tail(max(ends) if ends else None), "tail_from_final_report_s": tail(report),
            "tail_from_last_child_return_s": tail(max(returns) if returns else None)}


# ------------------------------------------------------------------ rendering

def render_timeline(trial: Path, plan: dict, events: list, view: list, inv: dict) -> str:
    rows = []
    for e in events:
        extra = {k: v for k, v in e["detail"].items() if k in ("reason", "sha", "seconds", "line", "result", "category")}
        text = json.dumps(extra, separators=(",", ":")) if extra else ""
        rows.append((e["ts"], 0, e["seq"], "L", "ledger", e["kind"], e["step"] or "-", text[:150]))
    for n, i in enumerate(view):
        if i["t"] is None or i["kind"] in ("usage",):
            continue
        what = (i["name"] + " " + i["text"].replace("\n", " ")).strip()
        rows.append((i["t"], 1, n, "H", i["actor"], i["kind"], i["name"] or "-", what[:150]))
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    t0 = rows[0][0] if rows else 0.0
    head = [f"trial   {trial.name}", f"host    {inv.get('host')} {inv.get('version')} {inv.get('model')} {inv.get('effort')}",
            f"plan    {plan.get('name')}  arm {inv.get('arm')}  variant {inv.get('variant')}",
            "source  L = kit ledger (ground truth for steps)   H = host event stream (arrival time)", ""]
    body = [f"+{r[0] - t0:8.3f}  {r[3]}  {r[4][:13]:<13} {r[5]:<8} {r[6][:12]:<12} {r[7]}" for r in rows]
    return "\n".join(head + body) + "\n"


def render_gantt(plan: dict, events: list, view: list, width: int = 64) -> str:
    state = dagkit.derive(plan, events)
    last_ts = events[-1]["ts"] if events else 0.0
    iv = {i: (state[i]["start"], state[i]["end"] if state[i]["end"] is not None else last_ts) for i in state if state[i]["start"] is not None}
    if not iv:
        return "no step started\n"
    t0, t1 = min(a for a, _ in iv.values()), max(b for _, b in iv.values())
    span = max(t1 - t0, 1e-6)

    def col(t):
        return min(width - 1, max(0, int((t - t0) / span * width)))
    lines = [f"seconds from the first step start; one column = {span / width:.2f} s; █ ran, ▒ failed, ░ never ended"]
    for s in plan["steps"]:
        i = s["id"]
        if i not in iv:
            lines.append(f"{i:<3} |{' ' * width}| not started ({state[i]['state']})")
            continue
        a, b = iv[i]
        fill = "▒" if state[i]["state"] == "failed" else "░" if state[i]["state"] == "running" else "█"
        left, right = col(a), max(col(a) + 1, col(b))
        row = " " * left + fill * (right - left)
        lines.append(f"{i:<3} |{row:<{width}}| {a - t0:6.1f} to {b - t0:6.1f}  ({b - a:5.1f} s)")
    marks = [" "] * width
    for e in events:
        if e["kind"] == "ready" and t0 <= e["ts"] <= t1 + 1e-6:
            marks[col(e["ts"])] = "r"
    for i in view:
        if i["kind"] == "spawn" and i["t"] and t0 - 5 <= i["t"] <= t1 + 5:
            marks[col(min(max(i["t"], t0), t1))] = "^"
    lines.append(f"{'':<3} |{''.join(marks)}| r = a ready call, ^ = a sub-agent started")
    axis = [" "] * width
    for k in range(0, width, 8):
        label = f"{(t0 + span * k / width) - t0:.0f}"
        for j, ch in enumerate(label):
            if k + j < width:
                axis[k + j] = ch
    lines.append(f"{'':<3}  {''.join(axis)}")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ one trial and the comparison

def write_measures(trial: Path, plan: dict, run: dagkit.Run, events: list) -> dict | None:
    """A write plan (README Amendment A10): the hidden oracle's verdict on the final tree and what isolation and merging cost, from the ledger.

    ``script_s`` is the kit's own time (opening workspaces, committing, merging); ``merge_latency_s`` is, per merge, the seconds from the
    attempt's end to its merge (the merge happens at the next ``ready`` call, so the latency is the parent's turn plus the merge)."""
    meta = run.meta()
    if not meta.get("repo"):
        return None
    reported = {}
    for s in plan["steps"]:
        out = run.dir / "out" / f"{s['id']}.json"
        reported[s["id"]] = json.loads(out.read_text()).get("result", {}).get("answer") if out.is_file() else None
    oracle = trial / "oracle" / "hidden_tests.py"
    if plan.get("fixture") == "tickets":   # the real service: each feature's checks and held-out acceptance, the whole tree's, the interaction checks (ticketfix.evaluate)
        seeded = any(e["kind"] == "replay_seed" for e in events)   # A15: the earlier part of the ledger is E17's; its candidates are not this trial's to judge (the final tree is the one merge's candidate)
        verdict = {"deferred": True, "valid": False} if os.environ.get("PPE_DEFER_ORACLE") == "1" else ticketfix.evaluate(trial, meta, events, candidates=not seeded)
    else:
        verdict = writefix.evaluate(oracle, Path(meta["repo"]), reported) if oracle.is_file() else None

    def seconds(kind):
        return round(sum(e["detail"].get("seconds") or 0 for e in events if e["kind"] == kind), 3)
    last_end, latency, notes = {}, {}, {}
    for e in events:
        if e["kind"] == "end":
            last_end[e["step"]] = e["ts"]
        elif e["kind"] == "merged" and e["step"] in last_end:
            latency[f"{e['step']}#{e['detail'].get('attempt')}"] = round(e["ts"] - last_end[e["step"]], 2)
        elif e["kind"] == "commit" and e["detail"].get("scope_notes"):
            notes[f"{e['step']}#{e['detail'].get('attempt')}"] = e["detail"]["scope_notes"]
    conflicts = [e for e in events if e["kind"] == "conflict"]
    return {"mode": meta.get("workspace"), "oracle": verdict, "workspace_s": seconds("workspace"), "commit_s": seconds("commit"), "merge_s": seconds("merged") + seconds("conflict"),
            "script_s": round(seconds("workspace") + seconds("commit") + seconds("merged") + seconds("conflict"), 3),
            "workspaces": sum(1 for e in events if e["kind"] == "workspace"), "merges": sum(1 for e in events if e["kind"] == "merged"),
            "conflicts": len(conflicts), "conflict_paths": sorted({p for e in conflicts for p in e["detail"].get("paths", [])}),
            "retries": sum(1 for e in events if e["kind"] == "retry"), "scope_notes": notes, "merge_latency_s": latency,
            "refused_empty": sum(1 for e in events if e["kind"] == "refused" and e["detail"].get("category") == "empty"),
            "refused_missing": sum(1 for e in events if e["kind"] == "refused" and e["detail"].get("category") == "missing-output"),
            **real_measures(events)}


def real_measures(events: list) -> dict:
    return {**_real_measures(events), **_real_accounting(events)}


def _real_accounting(events: list) -> dict:
    """README Amendment A14's definitions, in one place. ``kit_total_s``: every second the kit itself spent, counted once: opening workspaces, committing,
    merging (a conflict's, a red one's with its undo, a clean one's), the landing together with its own re-test, and every other re-test.
    ``first_round_s``: the earliest first attempt's begin to the latest first attempt's end; ``slowest_first_s``: the longest single first attempt;
    ``first_attempt_overlap``: the files two tasks' first attempts both changed (the overlap that really happened, not the one expected);
    ``lock_wait_s``: how long kit commands stood behind another (a re-test holds the lock while it runs)."""
    def total(kind, key="seconds"):
        return sum(e["detail"].get(key) or 0 for e in events if e["kind"] == kind)
    landing_s = total("landed")
    retest_s = sum(e["detail"].get("seconds") or 0 for e in events if e["kind"] == "retest" and not e["detail"].get("landing"))
    kit_total = total("workspace") + total("commit") + total("merged") + total("conflict") + total("redtest") + total("redtest", "reset_s") + landing_s + retest_s
    spans = {}
    for e in events:   # each task's first attempt: the first start to the first end after it
        if e["kind"] == "start" and e["step"] not in spans:
            spans[e["step"]] = [e["ts"], None]
        elif e["kind"] == "end" and e["step"] in spans and spans[e["step"]][1] is None:
            spans[e["step"]][1] = e["ts"]
    firsts = {s: round(b - a, 1) for s, (a, b) in spans.items() if b}
    files = {e["step"]: set(e["detail"].get("files") or []) for e in events if e["kind"] == "commit" and e["detail"].get("attempt") == 1}
    ids = sorted(files)
    overlap = {f"{x}+{y}": sorted(files[x] & files[y]) for i, x in enumerate(ids) for y in ids[i + 1:] if files[x] & files[y]}
    return {"kit_total_s": round(kit_total, 3), "landing_s": round(landing_s, 3),
            "first_round_s": round(max(b for a, b in spans.values() if b) - min(a for a, b in spans.values()), 1) if spans and all(b for a, b in spans.values()) else None,
            "slowest_first_s": max(firsts.values()) if firsts else None, "first_attempt_s": firsts, "first_attempt_files": {s: sorted(f) for s, f in files.items()},
            "first_attempt_overlap": overlap, "lock_wait_s": round(sum(e["detail"].get("waited_s") or 0 for e in events if e["kind"] in ("start", "end")), 3),
            "faults": [e["detail"].get("what") for e in events if e["kind"] == "fault"], "noop_fixes": sum(1 for e in events if e["kind"] == "commit" and e["detail"].get("noop")),
            "retest_reruns_kept": sum(len(e["detail"].get("reruns") or []) for e in events if e["kind"] == "retest")}


def _real_measures(events: list) -> dict:
    """README Amendment A14 (a real repository): the re-test of the merged tree, the landing, and what recovery took, from the ledger."""
    retests = [e for e in events if e["kind"] == "retest" and not e["detail"].get("landing")]
    fix_ws = [e for e in events if e["kind"] == "workspace" and e["detail"].get("fix")]
    landed = next((e for e in events if e["kind"] == "landed"), None)
    work = {}
    for e in events:   # each attempt's own seconds: its begin (start) to its complete (end), in order
        if e["kind"] == "start":
            work.setdefault(e["step"], []).append([e["ts"], None])
        elif e["kind"] in ("end", "fail") and work.get(e["step"]):
            work[e["step"]][-1][1] = e["ts"]
    return {"retests": len(retests), "retest_s": round(sum(e["detail"].get("seconds") or 0 for e in retests), 3),
            "retest_reruns": sum(1 for e in retests if (e["detail"].get("tries") or 1) > 1),
            "redtests": sum(1 for e in events if e["kind"] == "redtest"), "mergefails": sum(1 for e in events if e["kind"] == "mergefail"),
            "retry_causes": sorted(e["detail"].get("cause") or "conflict" for e in events if e["kind"] == "retry"),
            "fix_attempts": len(fix_ws), "fix_markers": sorted({p for e in fix_ws for p in e["detail"].get("unmerged", [])}),
            "landed": None if landed is None else {"ok": landed["detail"].get("ok"), "files": len(landed["detail"].get("files", [])), "ts": landed["ts"]},
            "attempt_s": {s: [round(b - a, 1) for a, b in spans if b] for s, spans in work.items()},
            "attempt_peak": _peak([(a, b or events[-1]["ts"]) for spans in work.values() for a, b in spans])}


def _peak(spans: list) -> int:
    """The most attempts (of any task) running at one moment, over every attempt's begin to complete: the ledger's own peak forgets earlier attempts."""
    marks = sorted([(a, 1) for a, _ in spans] + [(b, -1) for _, b in spans], key=lambda m: (m[0], m[1]))
    now = best = 0
    for _, d in marks:
        now += d
        best = max(best, now)
    return best


def score_trial(trial: Path) -> dict:
    trial = Path(trial)
    plan = json.loads((trial / "work" / "plan.json").read_text())
    run = dagkit.Run(trial / "work" / "run")
    events = run.events()
    inv = json.loads((trial / "invocation.json").read_text()) if (trial / "invocation.json").is_file() else {}
    host = inv.get("host", "")
    view = host_view(trial, host)
    native = native_agents(trial, host)
    m = ledger_measures(plan, events, run)
    claim = final_claim(view)
    m.update(fidelity(m, claim))
    ans = answers(trial, plan)
    m["answers"] = ans
    m["write"] = write_measures(trial, plan, run, events)
    if ans is not None and claim is not None:
        m["final_answer_ok"] = claim.get("answer") == ans["expected_final"]
    elif plan.get("fixture") == "tickets" and claim is not None:   # no oracle.json for the real service: the answer must be what the last task recorded
        last = run.dir / "out" / f"{plan['steps'][-1]['id']}.json"
        recorded = json.loads(last.read_text()).get("result", {}).get("answer") if last.is_file() else None
        m["final_answer_ok"] = recorded is not None and claim.get("answer") == recorded
    # attribution: Claude's stream names the agent of every call; Codex's rollouts and Grok's log name it for theirs
    attributable = bool(host == "claude" or native["agents"] or (host == "codex" and native.get("threads")) or (host == "grok" and native["agents"]))
    m["mechanism"] = mechanism(view, m, attributable)
    m["native"] = {"source": native["source"], "agents": len(native["agents"]), "peak": agent_peak(native["agents"]),
                   "kinds": sorted({str(a.get("kind")) for a in native["agents"]}), "depths": sorted({a.get("depth") for a in native["agents"] if a.get("depth") is not None}),
                   "background": sorted({bool(a.get("background")) for a in native["agents"] if "background" in a}),
                   "intervals_s": [{"actor": a["actor"], "start": round(a["start"] - (m["first_start_ts"] or a["start"]), 2) if a.get("start") else None,
                                    "end": round(a["end"] - (m["first_start_ts"] or a["end"]), 2) if a.get("end") else None, "tokens": a.get("tokens")}
                                   for a in native["agents"]]}
    m["tokens"] = tokens(view, host, native)
    # A15, the audit of what a worker could have used that it should not: every git command a sub-agent ran and every one the parent ran (whole, up to 4,000 characters: the
    # workers are told not to run git; a flag is "no access detected", never "access ruled out"), the paths under /Users/dadleet a sub-agent named outside this trial's own folder
    # (E17's raw trials and this repository's evidence hold solutions), and how much the sub-agents did: their tool calls and how many ran the project's tests
    calls = [i for i in view if i["kind"] == "call"]
    worker = [i for i in calls if i["actor"] != "parent"]
    m["worker_git"] = [(i.get("full") or "")[:4000] for i in worker if re.search(r"\bgit\b", i.get("full") or "")]
    m["parent_git"] = [(i.get("full") or "")[:4000] for i in calls if i["actor"] == "parent" and re.search(r"\bgit\b", i.get("full") or "")]
    m["worker_outside"] = sorted({p for i in worker for p in re.findall(r"/Users/dadleet/[^\s'\"\\)\]}>,;]+", i.get("full") or "") if not p.startswith(str(trial.resolve()))})[:40]
    m["worker_calls"] = len(worker)
    m["worker_tests"] = sum(1 for i in worker if re.search(r"\b(?:npm\s+(?:run\s+)?test|node\s+--test)\b", i.get("full") or ""))
    proc_end, launched = inv.get("ended"), inv.get("started")
    ends = [i["t"] for i in view if i["t"]] + [e["ts"] for e in events]
    m["process"] = {"status": inv.get("status"), "returncode": inv.get("returncode"), "elapsed_s": inv.get("elapsed_s"),
                    "last_activity_tail_s": round(proc_end - max(ends), 3) if proc_end and ends else None,
                    **tails(view, events, proc_end), "lingering_after_exit": inv.get("lingering_after_exit"),
                    "orphans_terminated": inv.get("orphans_terminated")}
    verified = [e["ts"] for e in events if e["kind"] == "verify" and e["detail"].get("verdict") in ("OK", "PARTIAL")]
    m["timings"] = {"launch_to_first_start_s": round(m["first_start_ts"] - launched, 3) if launched and m["first_start_ts"] else None,
                    "launch_to_last_end_s": round(m["last_end_ts"] - launched, 3) if launched and m["last_end_ts"] else None,
                    "launch_to_verified_s": round(max(verified) - launched, 3) if launched and verified else None,
                    "launch_to_exit_s": round(proc_end - launched, 3) if launched and proc_end else None}
    m["valid"] = bool(inv.get("status") == "exited" and not m["scaled_trial"] and m["steps_without_end"] == 0
                      and m["verify_as_expected"] and m["fidelity_ok"] and m["terminal_duplicates"] == 0
                      and m.get("settled_all") is not False and (ans is None or ans["all_correct"]) and (plan.get("fixture") != "tickets" or m.get("final_answer_ok") is not False)
                      and (m["write"] is None or bool((m["write"]["oracle"] or {}).get("valid"))))
    m["identity"] = {k: inv.get(k) for k in ("host", "version", "model", "effort", "plan", "arm", "variant", "workspace", "loadavg", "enabled_features")}
    (trial / "score.json").write_text(json.dumps(m, indent=1, default=str) + "\n")
    (trial / "timeline.txt").write_text(render_timeline(trial, plan, events, view, inv))
    (trial / "gantt.txt").write_text(render_gantt(plan, events, view))
    return m


def summary_line(trial: Path, m: dict) -> str:
    i, p, t = m["identity"], m["process"], m["tokens"]
    tag = "+v2" if "multi_agent_v2" in (i.get("enabled_features") or []) else ""
    return (f"{trial.name:<28} {(i.get('host') or '-') + tag:<9} {i.get('plan') or '-':<8} {i.get('arm') or '-':<3}{i.get('variant') or '':<2} "
            f"{(p.get('status') or '-'):<8} valid={m['valid']} makespan={m['makespan_s']} peak={m['peak_concurrency']} refused={m['refused']} "
            f"early={m['starts_before_dep_end']} dup={m['steps_started_twice']} verify={m.get('verify')} "
            f"final={'ok' if m.get('fidelity_ok') else ('bad' if m.get('final_found') else 'none')} mech={m['mechanism']['kind']} "
            f"refill={m['refill']} tail_end_s={p.get('tail_from_last_end_s')} tail_final_s={p.get('tail_from_final_report_s')} "
            f"agents={m['native']['agents']} agent_peak={m['native']['peak']} "
            + (f"correct={m['answers']['correct']}/{m['answers']['total']} " if m.get("answers") else "")
            + (f"ws={i.get('workspace')} oracle={'ok' if (m['write']['oracle'] or {}).get('valid') else 'BAD'} merges={m['write']['merges']} conflicts={m['write']['conflicts']} " if m.get("write") else "")
            + f"in_all={t.get('input_all')} out_all={t.get('output_all')} cost={t.get('cost_usd')}")


def baseline_key(identity: dict) -> tuple:
    return (identity.get("host"), identity.get("version"), identity.get("model"), identity.get("effort"),
            tuple(sorted(identity.get("enabled_features") or [])), identity.get("plan"))


def compare_rows(rows: list) -> list:
    """Add vs_A0 (the arm's makespan over the matching A0's) and realized (the fraction of the ideal saving) to each valid
    non-A0 row; the matching A0 shares host, version, model, effort, feature profile and fixture and is itself valid."""
    base: dict = collections.defaultdict(list)
    for r in rows:
        if r["identity"].get("arm") == "A0" and r.get("valid") and r.get("makespan_s"):
            base[baseline_key(r["identity"])].append(r["makespan_s"])
    out = []
    for r in rows:
        r = dict(r)
        same = base.get(baseline_key(r["identity"]), [])
        r["n_baseline"] = len(same)
        if same and r.get("valid") and r.get("makespan_s") and r["identity"].get("arm") != "A0":
            a0 = sum(same) / len(same)
            cp = r["critical_path_declared_s"]
            r["vs_A0"] = round(r["makespan_s"] / a0, 3)
            r["realized"] = round((a0 - r["makespan_s"]) / (a0 - cp), 3) if cp is not None and a0 > cp else None
        out.append(r)
    return out


def compare(trials: list) -> str:
    rows = []
    for t in trials:
        t = Path(t)
        m = json.loads((t / "score.json").read_text()) if (t / "score.json").is_file() else score_trial(t)
        rows.append({"path": str(t), "identity": m["identity"], "makespan_s": m["makespan_s"],
                     "critical_path_declared_s": m["critical_path_declared_s"], "valid": m["valid"], "_m": m})
    lines = []
    for r in compare_rows(rows):
        line = summary_line(Path(r["path"]), r["_m"])
        if "vs_A0" in r:
            line += f" vs_A0={r['vs_A0']}x realized={r['realized']}"
        elif r["identity"].get("arm") != "A0":
            line += f" (no valid A0 of this profile: n={r['n_baseline']}, or this trial is invalid)"
        lines.append(line)
    return "\n".join(lines)


def shapes(trial: Path) -> str:
    counts: collections.Counter = collections.Counter()
    for line in (trial / "events.raw.jsonl").read_text(errors="replace").splitlines():
        try:
            ev = json.loads(line).get("ev")
        except ValueError:
            continue
        if isinstance(ev, dict):
            item = ev.get("item") if isinstance(ev.get("item"), dict) else {}
            counts[(ev.get("type"), ev.get("subtype") or ev.get("status") or item.get("type") or item.get("tool") or "")] += 1
    return "\n".join(f"{n:5}  {a}  {b}" for (a, b), n in counts.most_common())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("trials", nargs="+")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--shapes", action="store_true")
    args = parser.parse_args(argv)
    if args.shapes:
        print(shapes(Path(args.trials[0])))
    elif args.compare:
        print(compare(args.trials))
    else:
        for t in args.trials:
            print(summary_line(Path(t), score_trial(Path(t))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
