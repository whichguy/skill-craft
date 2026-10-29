"""Arm B continuation metrics for one slice folder: what the fresh session was told, its first commands, and how long it
took to report the loop iteration and get the cleared action accepted. Usage: arm_b_metrics.py SLICE_DIR [...] [--json]"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path


def _commands(entry):
    found = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("type") == "tool_use" and isinstance((o.get("input") or {}).get("command"), str):
                found.append((o.get("id"), o["input"]["command"]))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(entry)
    return found


def _results(entry):
    out = {}
    for c in ((entry.get("message") or {}).get("content") or []) if entry.get("type") == "user" else []:
        if isinstance(c, dict) and c.get("type") == "tool_result":
            body = c.get("content")
            if isinstance(body, list):
                body = " ".join(x.get("text", "") for x in body if isinstance(x, dict))
            out[c.get("tool_use_id")] = str(body or "")
    return out


def _ts(entry):
    raw = entry.get("timestamp")
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp() if raw else None


def measure(out: Path) -> dict:
    sessions = [json.loads(x) for x in (out / "sessions.jsonl").read_text().splitlines() if x.strip()]
    cont = next((s for s in sessions if s.get("row") == "start" and s.get("kind") == "continued"), None)
    result = json.loads((out / "slice-result.json").read_text()) if (out / "slice-result.json").exists() else {}
    row = {"slice": out.name, "pass": result.get("pass"), "verdicts": result.get("verdicts"),
           "redone": [r for c in result.get("clear") or [] for r in c.get("redone") or []]}
    if not cont:
        return {**row, "note": "no continued session"}
    told = json.loads(cont["told"]) if isinstance(cont.get("told"), str) else cont.get("told") or {}
    hook = told.get("hook") or {}
    loop = hook.get("loop") or {}
    row.update(condition=hook.get("condition"), loop_at_clear={k: loop.get(k) for k in ("kind", "status", "iteration")})
    lines = (out / "events.jsonl").read_text().splitlines()
    t0, calls, results = cont["t"], [], {}
    for line in lines[int(cont["events_line"]):]:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        results.update(_results(e))
        for cid, cmd in _commands(e):
            calls.append((cid, _ts(e), cmd))
    loop_next = loop.get("next") or ""
    first = [c for _, _, c in calls[:3]]
    row["first_commands"] = [re.sub(r"\S*/(scripts|bin)/", "", c)[:120] for c in first]
    row["first_is_loop_next"] = bool(first) and bool(loop_next) and first[0].strip().startswith(loop_next[:120])
    row["first_is_shiploop_next"] = bool(first) and bool(re.search(r"/scripts/shiploop next\b", first[0]))

    def secs(pred):
        hit = next(((t, c, results.get(cid, "")) for cid, t, c in calls if pred(c)), None)
        return (round(hit[0] - t0, 1) if hit and hit[0] else None), hit

    row["s_to_loop_report"], _ = secs(lambda c: "until_loop_ephemeral.py done" in c)
    completes = [(round(t - t0, 1) if t else None, "--check-only" in c, results.get(cid, "")[:140])
                 for cid, t, c in calls if re.search(r"/scripts/shiploop complete\b", c)]
    row["completes"] = completes
    accepted = next((s for s, chk, r in completes if not chk and ("committed" in r or "navigator |" in r)), None)
    row["s_to_accept"] = accepted
    row["refused_completes"] = sum(1 for _, chk, r in completes if not chk and "refus" in r.lower())
    row["commands_before_accept"] = sum(1 for _, t, _ in calls if accepted is None or (t and t - t0 <= accepted))
    return row


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    rows = [measure(Path(a)) for a in args]
    if "--json" in sys.argv:
        print(json.dumps(rows, indent=1))
    else:
        for r in rows:
            print(json.dumps(r, indent=1))
