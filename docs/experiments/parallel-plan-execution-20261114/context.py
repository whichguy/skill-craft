#!/usr/bin/env python3
"""context.py: how big every model call's context was, per thread, read from a raw trial folder.

Apparatus for docs/experiments/parallel-plan-execution-20261114 (journal entry R4). A single context that does all the work
carries everything it has read and said into every later call, so its input tokens grow faster than the work does; a fresh
sub-agent starts again from a small base. This reads each host's own per-call record and prints, per thread, the number of
calls, the first and last call's input tokens (the base and the size when it finished), the growth per call and the sum:

  claude  the stream's assistant messages (one usage per message id, the parent and each sub-agent by parent_tool_use_id)
  codex   each thread's rollout file: every token_count's last_token_usage.input_tokens (cached part included)
  grok    logs/unified.jsonl: one shell.turn.inference_done per model call with the session id, prompt_tokens, the cached part
          and the model's own elapsed milliseconds

  python3 context.py TRIAL_DIR [TRIAL_DIR ...]            print the table
  python3 context.py TRIAL_DIR --export evidence/NAME     also write evidence/NAME/context.json (compact: the series only)
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
import sys


def _rows(path: Path) -> list:
    out = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def claude_series(trial: Path) -> dict:
    seen, threads = set(), {}
    for rec in _rows(trial / "events.raw.jsonl"):
        ev = rec.get("ev")
        if not isinstance(ev, dict) or ev.get("type") != "assistant":
            continue
        msg = ev.get("message") or {}
        usage = msg.get("usage")
        key = msg.get("id") or id(ev)
        if not usage or key in seen:
            continue
        seen.add(key)
        owner = ev.get("parent_tool_use_id")
        actor = f"agent:{str(owner)[-6:]}" if owner else "parent"
        size = sum(usage.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        threads.setdefault(actor, {"series": [], "output": 0})["series"].append(size)
        threads[actor]["output"] += usage.get("output_tokens") or 0
    return threads


def codex_series(trial: Path) -> dict:
    threads = {}
    for path in sorted(glob.glob(str(trial / "home" / ".codex" / "sessions" / "*" / "*" / "*" / "rollout-*.jsonl"))):
        rows = _rows(Path(path))
        meta = next((r["payload"] for r in rows if r.get("type") == "session_meta" and isinstance(r.get("payload"), dict)), {})
        source = meta.get("source")
        child = isinstance(source, dict) and bool((source.get("subagent") or {}).get("thread_spawn"))
        actor = f"thread:{str(meta.get('id'))[-6:]}" if child else "parent"
        series, last_total, output = [], None, 0
        for r in rows:
            pl = r.get("payload")
            if isinstance(pl, dict) and pl.get("type") == "token_count" and pl.get("info"):
                total = pl["info"].get("total_token_usage", {}).get("total_tokens")
                if total == last_total:      # the rollout repeats a token_count when nothing new was billed
                    continue
                last_total = total
                use = pl["info"].get("last_token_usage") or {}
                series.append(use.get("input_tokens") or 0)
                output += use.get("output_tokens") or 0
        if series:
            threads[actor] = {"series": series, "output": output}
    return threads


def grok_series(trial: Path) -> dict:
    path = trial / "home" / ".grok" / "logs" / "unified.jsonl"
    threads: dict = {}
    order: list = []
    for r in _rows(path) if path.is_file() else []:
        if r.get("msg") != "shell.turn.inference_done" or not r.get("sid"):
            continue
        ctx = r.get("ctx") or {}
        if r["sid"] not in threads:
            threads[r["sid"]] = {"series": [], "output": 0, "model_ms": 0, "cached": []}
            order.append(r["sid"])
        t = threads[r["sid"]]
        t["series"].append(ctx.get("prompt_tokens") or 0)
        t["cached"].append(ctx.get("cached_prompt_tokens") or 0)
        t["output"] += ctx.get("completion_tokens") or 0
        t["model_ms"] += ctx.get("model_elapsed_ms") or 0
    named = {}
    for n, sid in enumerate(order):
        named["parent" if n == 0 else f"agent:{sid[-6:]}"] = threads[sid]
    return named


def read_trial(trial: Path) -> dict:
    inv = json.loads((trial / "invocation.json").read_text())
    host = inv["host"]
    threads = {"claude": claude_series, "codex": codex_series, "grok": grok_series}[host](trial)
    out = {}
    for actor, t in threads.items():
        s = t["series"]
        n = len(s)
        out[actor] = {"calls": n, "first": s[0], "last": s[-1], "sum": sum(s), "growth_per_call": round((s[-1] - s[0]) / (n - 1), 1) if n > 1 else None,
                      "output": t.get("output"), "model_ms": t.get("model_ms"), "series": s}
    return {"trial": trial.name, "host": host, "arm": inv.get("arm"), "threads": out}


def table(item: dict) -> str:
    lines = [f"{item['trial']}  ({item['host']}, {item['arm']})"]
    lines.append(f"  {'thread':<14}{'calls':>6}{'first':>9}{'last':>9}{'growth/call':>13}{'sum':>11}{'output':>8}")
    for actor, t in item["threads"].items():
        g = "-" if t["growth_per_call"] is None else f"{t['growth_per_call']:,.0f}"
        lines.append(f"  {actor:<14}{t['calls']:>6}{t['first']:>9,}{t['last']:>9,}{g:>13}{t['sum']:>11,}{(t['output'] or 0):>8,}")
    total = sum(t["sum"] for t in item["threads"].values())
    lines.append(f"  {'all threads':<14}{sum(t['calls'] for t in item['threads'].values()):>6}{'':>9}{'':>9}{'':>13}{total:>11,}")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("trials", nargs="+")
    parser.add_argument("--export", help="a directory to write context.json into (only valid with one trial)")
    args = parser.parse_args(argv)
    if args.export and len(args.trials) != 1:
        parser.error("--export takes exactly one trial")
    for name in args.trials:
        item = read_trial(Path(name))
        print(table(item))
        if args.export:
            Path(args.export).mkdir(parents=True, exist_ok=True)
            (Path(args.export) / "context.json").write_text(json.dumps(item, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
