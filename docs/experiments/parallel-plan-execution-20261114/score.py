#!/usr/bin/env python3
"""score.py: the measures of the parallel-plan-execution probes, a merged timeline and an ASCII Gantt.

Apparatus for docs/experiments/parallel-plan-execution-20261114 (see its README, "Measures"). Every measure is a
script reading the trial's ledger, the host's raw events and the invocation record; no judge is involved.

  score.py TRIAL...             score each trial folder: writes score.json, timeline.txt, gantt.txt, prints a summary
  score.py --compare TRIAL...   one table across trials, with each arm's realized fraction of the ideal saving
  score.py --shapes TRIAL       the host event types a trial's stream held (to extend the readers)

A trial folder holds work/plan.json, work/run/ (ledger.jsonl, out/), events.raw.jsonl (one record per host stdout
line: ``recv`` seconds, then ``ev`` the parsed event or ``raw`` the text), invocation.json and packet.md.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dagkit  # noqa: E402

FINAL_RE = re.compile(r"^FINAL (\{.*\})\s*$", re.M)
SPAWN_NAMES = ("agent", "task", "subagent", "spawn")
SHELL_PARALLEL = re.compile(r"(\s&\s|\s&$|&\s*$|xargs\s+-P|\bparallel\b|\bnohup\b|\bsetsid\b|\bdisown\b|;\s*wait\b)")


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
    out["serial_sum_declared_s"] = sum(s["kit"]["seconds"] for s in plan["steps"])
    cp: dict = {}
    for s in plan["steps"]:
        cp[s["id"]] = max([cp[d] for d in s["deps"]], default=0) + s["kit"]["seconds"]
    out["critical_path_declared_s"] = max(cp.values()) if cp else 0
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
    out["refused"] = sum(1 for e in events if e["kind"] == "refused")
    out["starts_before_dep_end"] = sum(
        1 for i in iv for d in deps[i] if state[d]["end_seq"] is None or state[i]["start_seq"] < state[d]["end_seq"])
    out["steps_started_twice"] = sum(1 for i in ids if state[i]["starts"] > 1)
    out["steps_without_end"] = sum(1 for i in ids if state[i]["state"] == "running")
    if run is not None and (run.dir / "meta.json").is_file():
        kind, line = dagkit.verdict(run)
        out["verify"], out["verify_line"] = kind, line
    lat = {}
    for i in ids:
        if deps[i] and i in iv and all(state[d]["end"] is not None for d in deps[i]):
            lat[i] = round(iv[i][0] - max(state[d]["end"] for d in deps[i]), 3)
    out["dispatch_latency_s"] = lat
    out["dispatch_latency_mean_s"] = round(sum(lat.values()) / len(lat), 3) if lat else None
    scales = {e["detail"].get("scale") for e in events if e["kind"] == "start"}
    out["time_scale"] = sorted(s for s in scales if s is not None)
    if plan.get("name") == "ragged6" and "S1" in iv and "S3" in iv:
        out["refill"] = bool(iv["S1"][0] <= iv["S3"][0] < iv["S1"][1])
    else:
        out["refill"] = None
    out["states"] = {i: state[i]["state"] for i in ids}
    return out


def fidelity(measures: dict, claim: dict | None) -> dict:
    """M7: the FINAL object against the ledger's states."""
    if claim is None:
        return {"final_found": False, "fidelity_ok": False}
    states = measures["states"]
    actual = {"done": {i for i, s in states.items() if s == "done"}, "failed": {i for i, s in states.items() if s == "failed"},
              "not_run": {i for i, s in states.items() if s in ("blocked", "pending")}}
    out: dict = {"final_found": True}
    ok = True
    for key in ("done", "failed", "not_run"):
        said = set(map(str, claim.get(key, [])))
        out[f"false_{key}"] = sorted(said - actual[key])
        out[f"missed_{key}"] = sorted(actual[key] - said)
        ok = ok and not out[f"false_{key}"] and not out[f"missed_{key}"]
    out["fidelity_ok"] = ok
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
    """Host events as {t, actor, kind, name, text, extra}; kinds: call, spawn, result, return, text, final, usage."""
    t, ev = rec.get("recv"), rec.get("ev")
    if not isinstance(ev, dict):
        return []
    typ = ev.get("type")
    out = []

    def add(kind, actor="parent", name="", text="", **extra):
        out.append({"t": t, "actor": actor, "kind": kind, "name": name, "text": text, **extra})

    if host == "claude":
        owner = ev.get("parent_tool_use_id")
        actor = f"agent:{str(owner)[-6:]}" if owner else "parent"
        if typ == "assistant":
            msg = ev.get("message") or {}
            for block in msg.get("content") or []:
                if block.get("type") == "tool_use":
                    name = block.get("name", "")
                    inp = block.get("input") or {}
                    spawn = name.lower() in SPAWN_NAMES
                    text = (inp.get("description") or inp.get("prompt") or "") if spawn else (inp.get("command") or json.dumps(inp)[:120])
                    add("spawn" if spawn else "call", actor, name, str(text)[:140], id=block.get("id"),
                        background=bool(inp.get("run_in_background")))
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
            add("system", "parent", str(ev.get("subtype") or ""), json.dumps({k: v for k, v in ev.items() if k in ("subtype", "model", "description", "task_id", "tool_use_id", "status")})[:160])
    elif host == "codex":
        thread = ev.get("thread_id") or (ev.get("item") or {}).get("thread_id")
        item = ev.get("item") or {}
        itype = item.get("type")
        actor = "parent" if not thread else f"thread:{str(thread)[-6:]}"
        if typ in ("item.started", "item.completed"):
            started = typ == "item.started"
            if itype == "command_execution":
                add("call" if started else "result", actor, "shell", str(item.get("command") or "")[:140], id=item.get("id"),
                    exit=item.get("exit_code"))
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
                detail = {k: item.get(k) for k in ("prompt", "receiver_thread_ids", "agents_states", "status")
                          if item.get(k) not in (None, [], {})}
                add(kind, actor, tool, json.dumps(detail)[:200], id=item.get("id"))
            elif itype and itype not in ("reasoning", "agent_message", "error"):
                add("call" if started else "result", actor, str(item.get("tool") or item.get("name") or itype),
                    json.dumps({k: v for k, v in item.items() if k in ("prompt", "status", "tool")})[:160], id=item.get("id"))
        elif typ == "turn.completed":
            add("usage", actor, "", "", usage=ev.get("usage"))
    elif host == "grok":
        if typ == "tool_call":
            name = str(ev.get("toolName") or ev.get("title") or "")
            spawn = any(k in name.lower() for k in SPAWN_NAMES)
            raw = ev.get("rawInput") or {}
            add("spawn" if spawn else "call", "parent", name, str(raw.get("command") or raw.get("prompt") or json.dumps(raw))[:140],
                id=ev.get("toolCallId"))
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
    return out


def final_claim(view: list) -> dict | None:
    for item in reversed(view):
        if item["kind"] in ("final", "text"):
            found = FINAL_RE.findall(item["text"])
            if found:
                try:
                    return json.loads(found[-1])
                except ValueError:
                    return None
    return None


def tokens(view: list, host: str) -> dict:
    """M8: what the host reports, or None for an unreported figure (never zero)."""
    out: dict = {"source": None, "input": None, "output": None, "cache_read": None, "cost_usd": None, "peak_parent_input": None}
    usages = [i for i in view if i["kind"] == "usage" and i.get("usage")]
    finals = [i for i in view if i["kind"] == "final"]
    if host == "claude" and finals and finals[-1].get("usage"):
        u = finals[-1]["usage"]
        out.update(source="claude.result", input=u.get("input_tokens"), output=u.get("output_tokens"),
                   cache_read=u.get("cache_read_input_tokens"), cache_create=u.get("cache_creation_input_tokens"),
                   cost_usd=finals[-1].get("cost"))
        peaks = [(i["usage"].get("input_tokens") or 0) + (i["usage"].get("cache_read_input_tokens") or 0)
                 + (i["usage"].get("cache_creation_input_tokens") or 0) for i in usages]
        out["peak_parent_input"] = max(peaks) if peaks else None
    elif usages:
        def total(key):
            vals = [u["usage"].get(key) for u in usages if u["usage"].get(key) is not None]
            return sum(vals) if vals else None
        out.update(source=f"{host}.usage", input=total("input_tokens"), output=total("output_tokens"),
                   cache_read=total("cache_read_input_tokens") if host != "codex" else total("cache_read_input_tokens"),
                   cost_usd=next((u.get("cost") for u in reversed(usages) if u.get("cost") is not None), None))
    return out


def mechanism(view: list, measures: dict) -> dict:
    """M10: how the work was run, from the events and the ledger."""
    spawns = [i for i in view if i["kind"] == "spawn"]
    calls = [i for i in view if i["kind"] == "call" and "dagkit.py" in i["text"] and " run " in i["text"]]
    shell_par = [c for c in view if c["kind"] == "call" and "dagkit.py" in c["text"] and SHELL_PARALLEL.search(c["text"])]
    by_agent = collections.Counter(c["actor"] for c in calls)
    attributed = any(a != "parent" for a in by_agent)
    peak = measures.get("peak_concurrency", 0)
    if shell_par:
        kind = "shell-parallel"
    elif spawns and peak > 1:
        kind = "native-agents"
    elif spawns:
        kind = "native-agents-serial"
    elif peak > 1:
        kind = "unknown-parallel"
    elif calls:
        kind = "parent-executed"
    else:
        kind = "serial"
    return {"kind": kind, "spawns": len(spawns), "run_calls": len(calls), "run_calls_by_actor": dict(by_agent),
            "attributed": attributed, "background_spawns": sum(1 for s in spawns if s.get("background"))}


# ------------------------------------------------------------------ rendering

def render_timeline(trial: Path, plan: dict, events: list, view: list, inv: dict) -> str:
    rows = []
    for e in events:
        extra = {k: v for k, v in e["detail"].items() if k in ("reason", "sha", "seconds", "line", "result")}
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

def score_trial(trial: Path) -> dict:
    trial = Path(trial)
    plan = json.loads((trial / "work" / "plan.json").read_text())
    run = dagkit.Run(trial / "work" / "run")
    events = run.events()
    inv = json.loads((trial / "invocation.json").read_text()) if (trial / "invocation.json").is_file() else {}
    host = inv.get("host", "")
    view = host_view(trial, host)
    m = ledger_measures(plan, events, run)
    m.update(fidelity(m, final_claim(view)))
    m["mechanism"] = mechanism(view, m)
    m["tokens"] = tokens(view, host)
    ends = [i["t"] for i in view if i["t"]] + [e["ts"] for e in events]
    last_activity = max(ends) if ends else None
    m["process"] = {"status": inv.get("status"), "returncode": inv.get("returncode"), "elapsed_s": inv.get("elapsed_s"),
                    "tail_s": round(inv["ended"] - last_activity, 3) if inv.get("ended") and last_activity else None}
    m["identity"] = {k: inv.get(k) for k in ("host", "version", "model", "effort", "plan", "arm", "variant", "loadavg",
                                             "enabled_features")}
    (trial / "score.json").write_text(json.dumps(m, indent=1, default=str) + "\n")
    (trial / "timeline.txt").write_text(render_timeline(trial, plan, events, view, inv))
    (trial / "gantt.txt").write_text(render_gantt(plan, events, view))
    return m


def summary_line(trial: Path, m: dict) -> str:
    i, p, t = m["identity"], m["process"], m["tokens"]
    tag = "+v2" if "multi_agent_v2" in (i.get("enabled_features") or []) else ""
    return (f"{trial.name:<28} {(i.get('host') or '-') + tag:<9} {i.get('plan') or '-':<8} {i.get('arm') or '-':<3}{i.get('variant') or '':<2} "
            f"{(p.get('status') or '-'):<8} makespan={m['makespan_s']} peak={m['peak_concurrency']} refused={m['refused']} "
            f"early={m['starts_before_dep_end']} dup={m['steps_started_twice']} verify={m.get('verify')} "
            f"final={'ok' if m.get('fidelity_ok') else ('bad' if m.get('final_found') else 'none')} mech={m['mechanism']['kind']} "
            f"refill={m['refill']} tail_s={p.get('tail_s')} tok_in={t.get('input')} tok_out={t.get('output')} cost={t.get('cost_usd')}")


def compare(trials: list) -> str:
    scored = [(Path(t), json.loads((Path(t) / "score.json").read_text()) if (Path(t) / "score.json").is_file() else score_trial(Path(t))) for t in trials]
    base: dict = {}
    for t, m in scored:
        i = m["identity"]
        if i.get("arm") == "A0" and m["makespan_s"]:
            base[(i["host"], i["plan"])] = m["makespan_s"]
    lines = []
    for t, m in scored:
        i = m["identity"]
        a0 = base.get((i["host"], i["plan"]))
        cp, line = m["critical_path_declared_s"], summary_line(t, m)
        if a0 and m["makespan_s"] and a0 > cp:
            line += f" realized={(a0 - m['makespan_s']) / (a0 - cp):.2f} vs_A0={m['makespan_s'] / a0:.2f}x"
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
