#!/usr/bin/env python3
"""phases.py: where each second of a trial went, split into the parts that are fixed, per round and proportional to the work.

Apparatus for docs/experiments/parallel-plan-execution-20261114 (journal entry R4). It reads an exported trial folder
(invocation.json, ledger.jsonl, native.json, events.trimmed.jsonl) and splits the run into phases a skill layer would have to
budget for, in seconds from the launch:

  orient     launch to the parent's first `ready` call (host start-up, the packet, the first command)
  spawn      first `ready` to the last spawn (the parent deciding and issuing the spawns; A3 only)
  start      the last spawn to the first task `begin` (the host starting the children, each child reading its task; A3 only)
  work       the first `begin` to the last independent task's end (T1 to T4): the work, and for A3 its slowest member
  join       that last end to the dependent task's `begin` (T5, or W5 in a write plan): the parent noticing, asking `ready` (which merges
             the finished branches of an isolated write run), spawning, the child starting
  integrate  the dependent task's `begin` to its end (in a build plan this is where the combined checks sit)
  tail       the dependent task's end to the process's exit (verify, the final report, shutdown)

For A0 the parent does the tasks itself, so `spawn` and `start` are zero and `join` is the parent's gap between tasks.

Where the host starts each child as it is spawned (Codex), the first child's `begin` comes before the parent's later spawns, so
`spawn` is the time to the first spawn and the later spawns sit inside `work`; where the children begin when the parent yields
(Claude, Grok) all the spawns are in `spawn`. The whole run is the same either way: read `spawn + start + work` together when
comparing hosts, and `spawn` alone only within one host.

  python3 phases.py [TRIAL...]        trial names under evidence/ (default: the six registered-cell trials)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score  # noqa: E402

DEFAULT = ["r1h-claude-a0", "r1h-claude-a3", "r1-grok-a0", "r1-grok-a3", "r1-codex-a0", "r1-codex-a3"]


def load(name: str) -> dict:
    d = Path(os.environ.get("PPE_EVIDENCE", HERE / "evidence")) / name
    inv = json.loads((d / "invocation.json").read_text())
    ledger = [json.loads(line) for line in (d / "ledger.jsonl").read_text().splitlines()]
    native = json.loads((d / "native.json").read_text())
    plan = json.loads((d / "plan.json").read_text())
    view = []
    for line in (d / "events.trimmed.jsonl").read_text().splitlines():
        try:
            view += score.normalize(inv["host"], json.loads(line))
        except ValueError:
            continue
    return {"name": name, "inv": inv, "ledger": ledger, "native": native, "view": view, "last": plan["steps"][-1]["id"]}


def spawn_times(t: dict) -> list:
    if t["inv"]["host"] == "codex":
        parent = t["native"].get("parent") or {}
        return sorted(c["t"] for c in parent.get("calls", []) if c["kind"] == "agent_tool" and c["name"] == "spawn_agent")
    return sorted(i["t"] for i in t["view"] if i["kind"] == "spawn" and i["t"])


def split(name: str) -> dict:
    t = load(name)
    t0, t_end = t["inv"]["started"], t["inv"]["ended"]
    led = t["ledger"]
    begin = {e["step"]: e["ts"] for e in led if e["kind"] == "start"}
    end = {e["step"]: e["ts"] for e in led if e["kind"] == "end"}
    ready = [e["ts"] for e in led if e["kind"] == "ready"]
    first_begin = min(begin.values())
    last = t["last"]
    indep = [s for s in end if s != last]
    last_indep_end = max(end[s] for s in indep)
    sp = spawn_times(t)
    out = {"name": name, "arm": t["inv"]["arm"], "host": t["inv"]["host"], "whole": t_end - t0}
    # round-one spawns are those issued before the first task began; the dependent task's spawn comes later
    first_round = [s for s in sp if s <= first_begin + 0.5] if sp else []
    out["orient"] = ready[0] - t0
    if first_round:
        out["spawn"] = max(first_round) - ready[0]
        out["start"] = first_begin - max(first_round)
        out["spawn_calls"] = len(sp)
    else:                                                     # A0, or spawns recorded after the first begin (children began as they were spawned)
        out["spawn"], out["start"] = 0.0, first_begin - ready[0]
        out["spawn_calls"] = len(sp)
    out["work"] = last_indep_end - first_begin
    out["join"] = begin[last] - last_indep_end
    out["integrate"] = end[last] - begin[last]
    out["tail"] = t_end - end[last]
    out["task_seconds"] = {s: round(end[s] - begin[s], 1) for s in sorted(end)}
    out["agents"] = len(t["native"].get("agents", []))
    return out


def fmt(x):
    return f"{x:6.1f}"


def main(argv=None) -> int:
    names = (argv or sys.argv[1:]) or DEFAULT
    rows = [split(n) for n in names]
    cols = ("orient", "spawn", "start", "work", "join", "integrate", "tail")
    print(f"{'trial':<16} {'arm':<4}" + "".join(f"{c:>10}" for c in cols) + f"{'whole':>9}  independent tasks' own seconds")
    for r in rows:
        print(f"{r['name']:<16} {r['arm']:<4}" + "".join(f"{fmt(r[c]):>10}" for c in cols) + f"{fmt(r['whole']):>9}  " + str(r["task_seconds"]))
    print("\nshare of the whole run (percent)")
    for r in rows:
        print(f"{r['name']:<16} {r['arm']:<4}" + "".join(f"{100 * r[c] / r['whole']:>10.0f}" for c in cols))
    print("\nA3 minus A0 of the same host (seconds): what the fan-out added in each phase")
    for host_a0, host_a3 in (("r1h-claude-a0", "r1h-claude-a3"), ("r1-grok-a0", "r1-grok-a3"), ("r1-codex-a0", "r1-codex-a3")):
        a0, a3 = split(host_a0), split(host_a3)
        print(f"{a3['host']:<8}" + "".join(f"{c}={a3[c] - a0[c]:+6.1f}  " for c in cols) + f"whole={a3['whole'] - a0['whole']:+6.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
