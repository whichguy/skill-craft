#!/usr/bin/env python3
"""List the first ShipLoop start command of every archived E2E run (read-only, offline).

Usage: python3 -I start_routes.py [--since YYYY-MM-DD] [--json out.json]

For each run folder (invocation.json + events.jsonl) the script finds the first command that starts a ShipLoop run:
  workspace  = `workspace start` (isolated entry)        direct = `init` (direct entry)
and reports the case, host, model, effort, whether the model's folder check before it said "not a git repository", and
whether the prompt says "current directory" / "in place". Event streams of three hosts are read: Codex and Grok write
`tool_call` events with rawInput.command; Claude writes assistant `tool_use` blocks with input.command.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

ROOTS = [p for p in sorted(Path.home().glob("e2e-runs*")) if p.is_dir() and p.name != "e2e-runs-startroute"]
SKIP = {"home", "work", "node_modules", ".git", "platform", "battleship-run"}
WS = re.compile(r"workspace\s+start\b|['\"]workspace['\"]\s*,\s*['\"]start['\"]")
INIT = re.compile(r"(?:^|[\s'\",\[])init(?:[\s'\",\]])")
SHIP = re.compile(r"shiploop")


def commands(path: Path):
    """Yield (event index, command text, result text of the same call or '') in stream order."""
    pending = {}
    with path.open(errors="replace") as fh:
        for i, line in enumerate(fh, 1):
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if not isinstance(ev, dict):
                continue
            t = ev.get("type")
            if t == "tool_call":
                cmd = (ev.get("rawInput") or {}).get("command")
                if isinstance(cmd, list):
                    cmd = " ".join(map(str, cmd))
                if isinstance(cmd, str):
                    pending[ev.get("toolCallId")] = (i, cmd)
                    yield ("call", i, cmd, ev.get("toolCallId"))
            elif t == "tool_call_update":
                txt = ""
                for c in ev.get("content") or []:
                    try:
                        txt += (c.get("content") or {}).get("text") or ""
                    except Exception:
                        pass
                yield ("result", i, txt, ev.get("toolCallId"))
            elif t == "assistant":
                for blk in (ev.get("message") or {}).get("content") or []:
                    if isinstance(blk, dict) and blk.get("type") == "tool_use":
                        cmd = (blk.get("input") or {}).get("command")
                        if isinstance(cmd, str):
                            yield ("call", i, cmd, blk.get("id"))
            elif t == "user":
                for blk in (ev.get("message") or {}).get("content") or []:
                    if isinstance(blk, dict) and blk.get("type") == "tool_result":
                        c = blk.get("content")
                        txt = c if isinstance(c, str) else " ".join((x.get("text") or "") for x in c or [] if isinstance(x, dict))
                        yield ("result", i, txt, blk.get("tool_use_id"))


def first_start(path: Path):
    results = {}
    folder_check = None
    last_calls = []
    for kind, i, text, cid in commands(path):
        if kind == "result":
            results[cid] = text
            continue
        last_calls.append((i, text, cid))
        if re.search(r"git (status|rev-parse)", text):
            folder_check = (i, cid)
        if SHIP.search(text):
            if WS.search(text):
                return "workspace", i, text, folder_check, results
            if INIT.search(text) and ("--repo" in text or "--run-dir" in text):
                return "direct", i, text, folder_check, results
    return None, None, None, folder_check, results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-10-24")
    ap.add_argument("--json")
    args = ap.parse_args()
    since = dt.datetime.fromisoformat(args.since).timestamp()
    rows = []
    for root in ROOTS:
        for inv in root.rglob("invocation.json"):
            rel = inv.relative_to(root).parts
            if any(part in SKIP for part in rel[:-1]):
                continue
            run = inv.parent
            ev = run / "events.jsonl"
            if not ev.is_file() or ev.stat().st_mtime < since:
                continue
            try:
                d = json.loads(inv.read_text())
            except Exception:
                continue
            argv = d.get("argv") or []
            prompt = next((a for a in argv if isinstance(a, str) and len(a) > 80), "") or ""
            verb, idx, text, fc, results = first_start(ev)
            checked = ""
            if fc and fc[1] in results:
                checked = "not-git" if "not a git repository" in results[fc[1]] else "git"
            rows.append({
                "run": str(run).replace(str(Path.home()), "~"),
                "case": d.get("case"), "host": d.get("host"), "model": d.get("model"), "effort": d.get("effort"),
                "start": verb, "event": idx, "folder_check": checked,
                "prompt_current_dir": bool(re.search(r"current directory", prompt)),
                "prompt_in_place": bool(re.search(r"in[- ]place", prompt)),
                "command": (text or "")[:260],
            })
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=1))
    from collections import Counter
    print("runs with events since", args.since, ":", len(rows))
    print("first start:", dict(Counter(r["start"] for r in rows)))
    print("by host x start:")
    for k, v in sorted(Counter((r["host"], r["start"]) for r in rows).items(), key=lambda kv: str(kv)):
        print("  ", k, v)


if __name__ == "__main__":
    main()
