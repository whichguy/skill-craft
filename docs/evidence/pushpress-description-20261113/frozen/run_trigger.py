#!/usr/bin/env python3
"""Count which skills a `claude -p` run calls, for a list of prompts, against one skill-craft plugin payload.

One run = one `claude -p` invocation in a scratch directory outside every repository, with the user's settings, plugins and MCP servers
switched off (--restricted, --strict-mcp-config), one tool (Skill) and a turn cap, so the only question asked is: which skill does the model
call first for this prompt. Nothing is stored but the skill names called, the init event's skill-list hash, cost and turn counts; never an answer.

usage: run_trigger.py --payload <plugin dir> --prompts <prompts.json> --label <name> --out <result.json> [--runs 2] [--jobs 4]
                      [--max-turns 1] [--model sonnet] [--per-run-cap 0.3] [--cap-usd 3.0] [--cwd <dir>] [--only ID,ID]
prompts.json: {"prompts": [{"id", "text", "expect_fire" (bool), "category"}...]}   (the format of the Round 9 trigger test)
"""
import argparse
import concurrent.futures as cf
import datetime
import hashlib
import json
import os
import subprocess
import sys
import threading
import time

p = argparse.ArgumentParser()
p.add_argument("--payload", required=True)
p.add_argument("--prompts", required=True)
p.add_argument("--label", required=True)
p.add_argument("--out", required=True)
p.add_argument("--runs", type=int, default=2)
p.add_argument("--jobs", type=int, default=4)
p.add_argument("--max-turns", type=int, default=1)
p.add_argument("--model", default="sonnet")
p.add_argument("--per-run-cap", type=float, default=0.3)
p.add_argument("--cap-usd", type=float, default=3.0)
p.add_argument("--cwd", required=True)
p.add_argument("--only", default="")
a = p.parse_args()
a.payload = os.path.abspath(a.payload)  # the subprocess runs in --cwd, so a relative payload path would silently load no plugin
a.cwd = os.path.abspath(a.cwd)
a.prompts = os.path.abspath(a.prompts)
a.out = os.path.abspath(a.out)

prompts = json.load(open(a.prompts))["prompts"]
if a.only:
    keep = set(a.only.split(","))
    prompts = [x for x in prompts if x["id"] in keep]
env = dict(os.environ, SHIPLOOP_KEEPALIVE="off")
lock = threading.Lock()
spent = [0.0]
stop = [False]


def parse(stdout):
    init, skills_called, result = None, [], None
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            init = ev
        elif ev.get("type") == "assistant":
            for c in (ev.get("message") or {}).get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Skill":
                    inp = c.get("input") or {}
                    skills_called.append(str(inp.get("skill") or inp.get("name") or inp.get("command") or "?"))
        elif ev.get("type") == "result":
            result = ev
    return init, skills_called, result


def one(item, run_no):
    if stop[0]:
        return dict(id=item["id"], run=run_no, skipped="cost cap reached")
    cmd = ["claude", "-p", "--restricted", "--strict-mcp-config", "--plugin-dir", a.payload, "--tools", "Skill",
           "--max-turns", str(a.max_turns), "--max-budget-usd", str(a.per_run_cap), "--no-session-persistence",
           "--output-format", "stream-json", "--verbose", "--model", a.model, item["text"]]
    attempts = 0
    while True:
        attempts += 1
        t0 = time.time()
        try:
            r = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, cwd=a.cwd, env=env, timeout=240)
            stdout, rc, err = r.stdout, r.returncode, r.stderr[-300:]
        except subprocess.TimeoutExpired as e:
            stdout, rc, err = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), -9, "timeout"
        init, called, result = parse(stdout)
        if result is not None or attempts >= 2:
            break
    cost = float((result or {}).get("total_cost_usd") or 0)
    with lock:
        spent[0] += cost
        if spent[0] > a.cap_usd:
            stop[0] = True
    skills = sorted((init or {}).get("skills") or [])
    has_skill = any(s.split(":")[-1] == "pushpress" for s in skills)
    rec = dict(id=item["id"], run=run_no, attempts=attempts, rc=rc, called=called, init_has_pushpress_skill=has_skill,
               pushpress_fired=any(c.split(":")[-1] == "pushpress" for c in called),
               result_subtype=(result or {}).get("subtype"), turns=(result or {}).get("num_turns"), cost_usd=round(cost, 5),
               seconds=round(time.time() - t0, 1), init_skills_sha=hashlib.sha256("\n".join(skills).encode()).hexdigest()[:16],
               init_model=(init or {}).get("model"), init_n_skills=len(skills), init_tools=sorted((init or {}).get("tools") or []),
               init_mcp=len((init or {}).get("mcp_servers") or []))
    if result is None:
        rec["error"] = (err or "no result event")[:300]
    elif not has_skill:
        rec["error"] = "isolation check failed: the pushpress skill is not in the init skill list (plugin not loaded)"
    return rec


jobs = [(it, r) for it in prompts for r in range(1, a.runs + 1)]
recs = []
with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
    futs = [ex.submit(one, it, r) for it, r in jobs]
    for f in cf.as_completed(futs):
        recs.append(f.result())
recs.sort(key=lambda x: (x["id"], x["run"]))
by = {it["id"]: it for it in prompts}
out = dict(label=a.label, started=datetime.datetime.now().astimezone().isoformat(timespec="seconds"), model=a.model, max_turns=a.max_turns,
           runs_per_prompt=a.runs, payload_pushpress_skill_sha256=hashlib.sha256(
               open(os.path.join(a.payload, "skills", "pushpress", "SKILL.md"), "rb").read()).hexdigest(),
           prompts_sha256=hashlib.sha256(open(a.prompts, "rb").read()).hexdigest(), claude=subprocess.run(
               ["claude", "--version"], capture_output=True, text=True).stdout.strip(), partial=stop[0], total_cost_usd=round(spent[0], 4),
           records=recs)
json.dump(out, open(a.out, "w"), indent=1)
print(f"{a.label}: {len(recs)} runs, cost ${spent[0]:.3f}, partial={stop[0]}, errors={sum(1 for r in recs if 'error' in r)}, "
      f"distinct init skill lists: {sorted({(r.get('init_n_skills'), r.get('init_skills_sha')) for r in recs if 'init_skills_sha' in r})}")
by_prompt = {}
for r in recs:
    by_prompt.setdefault(r["id"], []).append(r)
for pid, rs in by_prompt.items():
    fired = sum(1 for r in rs if r.get("pushpress_fired"))
    others = sorted({c for r in rs for c in r.get("called", []) if c.split(":")[-1] != "pushpress"})
    exp = by[pid].get("expect_fire")
    print(f"  {pid:5s} expect={'fire ' if exp else 'quiet'} fired {fired}/{len(rs)}  others={others or '-'}  | {by[pid]['text'][:70]}")
