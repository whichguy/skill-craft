#!/usr/bin/env python3
"""Tally the Codex threads of one step-slice run: how many, what each cost, and which workers the parent started.

    python3 tally_threads.py <slice output dir>  >  threads.json

A Codex round keeps every thread (the parent's and each worker's) as a rollout file under <output>/home/.codex.  The parent's
`spawn_agent` calls name the workers (`task_name`) and the context they start with (`fork_turns`: "none" is a fresh context).  The
messages between agents are encrypted on this host, so what a worker was told cannot be read; only its name, count and cost can.
"""
import json
import sys
from pathlib import Path


def main(out: Path) -> dict:
    files = sorted((out / "home" / ".codex").rglob("rollout-*.jsonl"), key=lambda f: f.stat().st_size, reverse=True)
    totals = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "reasoning_output_tokens": 0}
    threads, spawned = [], []
    for index, path in enumerate(files):
        usage, calls = {}, 0
        for line in path.read_text().splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            payload = event.get("payload") or {}
            if payload.get("type") == "token_count" and payload.get("info"):
                usage = payload["info"].get("total_token_usage") or usage
            if payload.get("type") in ("function_call", "custom_tool_call"):
                calls += 1
            if index == 0 and payload.get("type") == "function_call" and payload.get("name") == "spawn_agent":
                try:
                    args = json.loads(payload.get("arguments") or "{}")
                except ValueError:
                    args = {}
                spawned.append({"task_name": args.get("task_name"), "fork_turns": args.get("fork_turns")})
        for key in totals:
            totals[key] += usage.get(key, 0)
        threads.append({"role": "parent" if index == 0 else "worker", "tool_calls": calls, **{k: usage.get(k, 0) for k in totals}})
    return {"threads": len(files), "totals": totals, "workers_spawned_by_the_parent": spawned, "per_thread": threads}


if __name__ == "__main__":
    json.dump(main(Path(sys.argv[1])), sys.stdout, indent=1)
    print()
