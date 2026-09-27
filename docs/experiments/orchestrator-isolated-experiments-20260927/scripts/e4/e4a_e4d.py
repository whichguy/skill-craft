#!/usr/bin/env python3
import os
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib
analyze = importlib.import_module("analyze")

BASE = analyze.BASE
RUN_DIRS = {
    "e2e-run6": "e2e-run6/.shiploop-runs/battleship/run",
    "e2e-run6b": "e2e-run6b/.shiploop-runs/battleship-scoring/run",
    "e2e-run7": "e2e-run7/shiploop-runs/battleship/run",
    "e2e-run7b": "e2e-run7b/.shiploop-runs/add-scoring/run",
    "e2e-run8b": "e2e-run8b/.shiploop-runs/add-scoring/run",
}

def load_state(run):
    p = os.path.join(BASE, RUN_DIRS[run], "state.md")
    txt = open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r'```shiploop-state\n(.*?)\n```', txt, re.S)
    return json.loads(m.group(1))

def write_paths_from_calls(window_calls):
    touched = []
    for wc in window_calls:
        if wc["toolName"] == "write":
            fp = wc["rawInput"].get("file_path")
            if fp: touched.append(("write", fp))
        elif wc["toolName"] == "search_replace":
            fp = wc["rawInput"].get("file_path") or wc["rawInput"].get("target_file")
            if fp: touched.append(("search_replace", fp))
        elif wc["toolName"] == "run_terminal_command":
            cmd = wc["rawInput"].get("command", "")
            for m in re.finditer(r'>\s*([./\w-][\w./-]*\.\w+)', cmd):
                touched.append(("shell-redirect", m.group(1)))
            for m in re.finditer(r'\bsed\s+-i[^\s]*\s+.*?\s([./\w-][\w./-]*\.\w+)', cmd):
                touched.append(("shell-sed", m.group(1)))
    return touched

def e4a(run):
    print(f"\n===== E4a {run} =====")
    s = json.load(open(os.path.join(analyze.OUTDIR, f"{run}.summary.json")))
    calls = analyze.build_calls(analyze.load_events(run))
    state = load_state(run)
    accepted = state.get("accepted", {})
    impl = [r for r in s["q1_results"] if r["stage"] == "implement"]
    impl_sorted = sorted(impl, key=lambda r: r["expose_call_idx"])
    for idx, r in enumerate(impl_sorted):
        window = calls[r["expose_call_idx"]+1 : r["complete_call_idx"]]
        touched = write_paths_from_calls(window)
        acc = accepted.get(r["action"], {})
        print(f"-- step {idx+1}/{len(impl_sorted)} action={r['action']} read={r['read_before_complete']}({r['read_kind']})")
        print(f"   files touched: {touched}")
        print(f"   accepted.outcome={acc.get('outcome')} summary={acc.get('summary','')[:220]!r}")

def e4d(run):
    print(f"\n===== E4d {run} =====")
    s = json.load(open(os.path.join(analyze.OUTDIR, f"{run}.summary.json")))
    state = load_state(run)
    accepted = state.get("accepted", {})
    q1 = s["q1_results"]
    for stage in ("select-work", "baseline", "test-author", "test-red"):
        rs = [r for r in q1 if r["stage"] == stage]
        for r in rs:
            acc = accepted.get(r["action"], {})
            print(f"-- stage={stage} action={r['action']} read_before_complete={r['read_before_complete']}")
            print(f"   outcome={acc.get('outcome')} summary={acc.get('summary','')!r}")
            if "system_commands" in acc:
                print(f"   system_commands={acc.get('system_commands')}")

def e4c(run):
    print(f"\n===== E4c {run} =====")
    events = analyze.load_events(run)
    bg_started = []
    for i, e in enumerate(events):
        if e.get("type") == "tool_call_update":
            raw = e.get("rawOutput")
            if isinstance(raw, dict) and raw.get("type") == "BackgroundTaskStarted":
                bg_started.append({"i": i, "task_id": raw.get("task_id"), "command": raw.get("command","")[:200], "summary": raw.get("summary","")})
        if e.get("type") == "tool_call" and e.get("toolName") == "run_terminal_command":
            if e.get("rawInput", {}).get("background"):
                bg_started.append({"i": i, "task_id": e.get("toolCallId"), "command": e.get("rawInput",{}).get("command","")[:200], "summary": "explicit background=true"})
    polls = {}
    kills = {}
    for i, e in enumerate(events):
        if e.get("type") == "tool_call":
            if e.get("toolName") == "get_command_or_subagent_output":
                for tid in e.get("rawInput", {}).get("task_ids", []):
                    polls.setdefault(tid, []).append(i)
            elif e.get("toolName") == "kill_command_or_subagent":
                tid = e.get("rawInput", {}).get("task_id")
                if tid:
                    kills.setdefault(tid, []).append(i)
    exposures_idx = []
    for i, e in enumerate(events):
        if e.get("type") == "tool_call_update" and e.get("status") == "completed":
            try:
                txt = e["content"][0]["content"]["text"]
            except Exception:
                continue
            if analyze.HEAD_RE.search(txt) or re.search(r'"outcome"\s*:\s*"(done|blocked)"', txt):
                exposures_idx.append(i)

    for bg in bg_started:
        tid = bg["task_id"]
        p = polls.get(tid, [])
        k = kills.get(tid, [])
        last_seen = max(p + k) if (p or k) else bg["i"]
        span = last_seen - bg["i"]
        progress_between = [x for x in exposures_idx if bg["i"] < x < last_seen]
        print(f"-- idx={bg['i']} task={tid}")
        print(f"   cmd={bg['command']!r}")
        print(f"   polls={len(p)} killed={'yes @'+str(k[0]) if k else 'no'} last_activity_idx={last_seen} event_span={span}")
        print(f"   shiploop progress events in window: {len(progress_between)}")

if __name__ == "__main__":
    for run in ["e2e-run6", "e2e-run6b", "e2e-run7", "e2e-run7b", "e2e-run8b"]:
        e4a(run)
        e4d(run)
        e4c(run)
