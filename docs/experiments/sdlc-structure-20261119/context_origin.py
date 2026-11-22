#!/usr/bin/env python3
"""What fills a Claude session's context, and what is re-read (round 12).

Reads events.jsonl of a run folder (Claude host only: each model call carries its
own token usage). The context at a call is input + cache read + cache written.
Its growth to the next call is shared, by text length, between the command the
model wrote and the result of the tool it called, classed by a few text marks.
Every token added at call k is read again at each later call, so its share of
the re-read total is its size times the calls that follow.
Usage: python3 -I context_origin.py <run folder> ...
"""
import collections
import json
import re
import statistics
import sys
from pathlib import Path


def klass(tool, command, result):
    if tool == "Skill":
        return "skill card loaded"
    if tool == "Read":
        return "file read with the Read tool"
    if "ShipLoop navigator |" in result:
        return "stage instructions printed by ShipLoop"
    if re.search(r"scripts/shiploop|scratch/stage\.py|shiploop ", command):
        return "other ShipLoop command output"
    if re.search(r"npm (run )?test|node --test|pytest|npm start", command):
        return "test or server output"
    if re.search(r"\b(cat|sed|head|tail|grep|rg|ls|find|git (diff|log|show|status))\b", command):
        return "shell reads (cat, grep, git diff ...)"
    return "other shell output"


def one(folder):
    calls = collections.OrderedDict()
    results = {}
    for line in open(folder / "events.jsonl", errors="replace"):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get("parent_tool_use_id"):
            continue
        m = o.get("message") or {}
        if o.get("type") == "assistant":
            u = m.get("usage") or {}
            c = calls.setdefault(m.get("id"), {"ctx": 0, "out": 0, "tools": []})
            c["ctx"] = max(c["ctx"], (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0))
            c["out"] = max(c["out"], u.get("output_tokens") or 0)
            for b in m.get("content") or []:
                if b.get("type") == "tool_use":
                    c["tools"].append((b.get("id"), b.get("name"), json.dumps(b.get("input") or {})))
        elif o.get("type") == "user" and isinstance(m.get("content"), list):
            for b in m["content"]:
                if b.get("type") == "tool_result":
                    results[b.get("tool_use_id")] = json.dumps(b.get("content"))
    seq = [c for c in calls.values() if c["ctx"]]
    grow = collections.Counter(); reread = collections.Counter()
    n = len(seq)
    grow["start of session (system text, tools, skill list, first prompt)"] = seq[0]["ctx"]
    reread["start of session (system text, tools, skill list, first prompt)"] = seq[0]["ctx"] * n
    for i in range(n - 1):
        c = seq[i]
        delta = seq[i + 1]["ctx"] - c["ctx"]
        if delta <= 0:
            continue
        later = n - 1 - i
        # Per-call output counts in this stream are partial snapshots, so the growth
        # is shared between the call's own text and the tool result by their lengths.
        if c["tools"]:
            tid, tool, cmd = c["tools"][0]
            res = results.get(tid, "")
            own = delta * len(cmd) / max(len(cmd) + len(res), 1)
            if tool == "Skill":
                own = 0  # the card arrives as a message after a short tool result
            k = klass(tool, cmd, res)
        else:
            own, k = 0, "between turns (reminders, notices)"
        mine = "the model's own commands (files and results it writes are inside them)"
        grow[mine] += own; reread[mine] += own * later
        grow[k] += delta - own; reread[k] += (delta - own) * later
    return n, seq[-1]["ctx"], grow, reread


def main(folders):
    allg = collections.defaultdict(list); allr = collections.defaultdict(list); ns = []; ends = []
    for f in folders:
        n, end, grow, reread = one(Path(f))
        ns.append(n); ends.append(end)
        tg = sum(grow.values()); tr = sum(reread.values())
        for k in set(grow) | set(allg):
            allg[k].append(100 * grow.get(k, 0) / tg); allr[k].append(100 * reread.get(k, 0) / tr)
        print(f"{Path(f).name}: {n} model calls, context at the end {end:,}, re-read total by this count {tr:,.0f}")
    print(f"\n{len(folders)} runs; model calls median {statistics.median(ns):.0f}; context at the end median {statistics.median(ends):,.0f}")
    print(f"{'share of final context':>23} {'share of re-read tokens':>24}   origin (medians over the runs)")
    for k in sorted(allr, key=lambda k: -statistics.median(allr[k])):
        print(f"{statistics.median(allg[k]):22.0f}% {statistics.median(allr[k]):23.0f}%   {k}")


main(sys.argv[1:])
