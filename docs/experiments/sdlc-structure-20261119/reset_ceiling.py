#!/usr/bin/env python3
"""An upper bound on what a fresh session at stage or phase boundaries could save
(round 12). Claude host only. For each run: the context at each model call, read
from events.jsonl; the times the run entered the build and the after-build
stages, read from trace.jsonl. The simulation sets the context back to its size
at the first call when a boundary is crossed and lets it grow by the growth that
was actually seen. It leaves out what a fresh session would have to read again,
so the true saving is smaller. Prices are the ones the recorded bills imply.
Usage: python3 -I reset_ceiling.py <run folder> ...
"""
import datetime
import json
import statistics
import sys
from pathlib import Path

READ, WRITE, OUT = 0.10, 4.00, 10.00  # $ per million tokens, fitted to 14 recorded Sonnet 5.5 bills
BUILD = {"validate-existing", "implement"}


def run(folder):
    calls = {}
    for line in open(folder / "events.jsonl", errors="replace"):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get("type") != "assistant" or o.get("parent_tool_use_id"):
            continue
        m = o["message"]; u = m.get("usage") or {}
        ctx = (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
        ts = datetime.datetime.fromisoformat(o["timestamp"].replace("Z", "+00:00")).timestamp()
        c = calls.setdefault(m["id"], [ts, 0])
        c[1] = max(c[1], ctx)
    seq = sorted(calls.values())
    trace = next(folder.glob(".shiploop-runs/*/run/trace.jsonl"))
    marks = []; last = None; t_build = t_after = None
    for line in open(trace, errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        st = (r.get("stage") or [None, None])[-1]
        if not st or st == "improve":
            continue
        if st != last:
            marks.append(r["ts"]); last = st
        if t_build is None and st in BUILD:
            t_build = r["ts"]
        if t_after is None and st == "system-test-author":
            t_after = r["ts"]
    m = json.load(open(folder / "metrics.json")); u = m["sessions"][0]["usage"]
    bill = m["cost_usd"]
    actual = sum(c for _, c in seq)

    def simulate(bounds):
        bounds = sorted(b for b in bounds if b)
        total = 0; ctx = seq[0][1]; prev = seq[0]; bi = 0
        total += ctx
        for ts, c in seq[1:]:
            grow = max(c - prev[1], 0)
            crossed = False
            while bi < len(bounds) and ts >= bounds[bi]:
                bi += 1; crossed = True
            ctx = seq[0][1] + grow if crossed else ctx + grow
            total += ctx; prev = (ts, c)
        return total
    out = {"bill": bill, "reread_share": READ * u["cache_read_input_tokens"] / 1e6 / bill,
           "write_share": WRITE * u["cache_creation_input_tokens"] / 1e6 / bill, "out_share": OUT * u["output_tokens"] / 1e6 / bill}
    for name, bounds in (("two resets (before the build, after the build)", [t_build, t_after]), ("a reset at every stage", marks[1:])):
        sim = simulate(bounds)
        out[name] = (1 - sim / actual, READ * (actual - sim) / 1e6 / bill)
    return out


rows = [run(Path(f)) for f in sys.argv[1:]]
med = statistics.median
print(f"{len(rows)} runs; bill median ${med(r['bill'] for r in rows):.2f}")
print(f"the bill, median shares: re-reading the session so far {100*med(r['reread_share'] for r in rows):.0f}%, "
      f"text entering the session {100*med(r['write_share'] for r in rows):.0f}%, output {100*med(r['out_share'] for r in rows):.0f}%")
for name in ("two resets (before the build, after the build)", "a reset at every stage"):
    print(f"{name}: at most {100*med(r[name][0] for r in rows):.0f}% fewer re-read tokens, at most {100*med(r[name][1] for r in rows):.0f}% off the bill "
          f"(range {100*min(r[name][1] for r in rows):.0f}% to {100*max(r[name][1] for r in rows):.0f}%)")
