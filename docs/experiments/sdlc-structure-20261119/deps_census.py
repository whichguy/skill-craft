#!/usr/bin/env python3
"""Shape of the recorded step plans: steps, their `deps`, whether list order respects them,
how wide the dependency graph is, and whether deps-independent steps share files.
Reads the accepted step-plan results in state.md of every current-era run in census.json."""
import collections
import json
import pathlib
import re
import sys

runs = [r for r in json.loads(pathlib.Path(sys.argv[1]).read_text()) if r["current_era"]]
plans = []
for run in runs:
    trace = pathlib.Path(run["trace"])
    stage_of = {}
    for line in trace.read_text().splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        for accepted in row.get("accepted") or []:
            stage_of[accepted["action"]] = accepted["stage"]
    try:
        state = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", trace.with_name("state.md").read_text(), re.DOTALL).group(1))
    except (OSError, ValueError, AttributeError, KeyError):
        continue
    for action, result in (state.get("accepted") or {}).items():
        if stage_of.get(action) == "step-plan" and isinstance(result.get("steps"), list):
            plans.append((run, result))
        if stage_of.get(action) == "plan":
            run["queue"] = len(result.get("work_items") or [])
print(f"step plans read: {len(plans)} from {len(runs)} runs")
sizes = [len(p["steps"]) for _, p in plans]
print("steps per plan:", {n: sizes.count(n) for n in sorted(set(sizes))})
multi = [(r, p) for r, p in plans if len(p["steps"]) >= 2]
print(f"plans with 2+ steps: {len(multi)}")
missing = violations = chains = wide = disjoint_pairs_plans = overlap_pairs = indep_pairs = 0
widths = []
for run, plan in multi:
    steps = [s for s in plan["steps"] if isinstance(s, dict)]
    ids = [s.get("id") for s in steps]
    position = {i: n for n, i in enumerate(ids)}
    if any("deps" not in s for s in steps):
        missing += 1
        continue
    bad = any(position.get(d, 10**6) >= position[s["id"]] for s in steps for d in (s.get("deps") or []))
    violations += bad
    # depth levels
    depth = {}
    for s in steps:
        depth[s["id"]] = 1 + max([depth.get(d, 0) for d in (s.get("deps") or [])] or [0])
    width = max(collections.Counter(depth.values()).values())
    widths.append(width)
    is_chain = all((s.get("deps") or []) == ([ids[n - 1]] if n else []) for n, s in enumerate(steps))
    chains += is_chain
    wide += width > 1
    # ancestors
    ancestors = {}
    for s in steps:
        acc = set()
        for d in s.get("deps") or []:
            acc |= {d} | ancestors.get(d, set())
        ancestors[s["id"]] = acc
    found = False
    for a in range(len(steps)):
        for b in range(a + 1, len(steps)):
            ia, ib = steps[a]["id"], steps[b]["id"]
            if ia in ancestors[ib] or ib in ancestors[ia]:
                continue
            indep_pairs += 1
            if set(steps[a].get("paths") or []) & set(steps[b].get("paths") or []):
                overlap_pairs += 1
            else:
                found = True
    disjoint_pairs_plans += found
n = len(multi)
print(f"of those: deps missing on some step {missing}; list order breaks a dep {violations}; "
      f"pure serial chain {chains} ({chains / n:.0%}); graph wider than one {wide} ({wide / n:.0%})")
print("max width:", {w: widths.count(w) for w in sorted(set(widths))})
print(f"dependency-independent step pairs: {indep_pairs}; of those sharing a file path: {overlap_pairs} "
      f"({overlap_pairs / indep_pairs if indep_pairs else 0:.0%}); plans with an independent, file-disjoint pair: {disjoint_pairs_plans}")
queues = [r.get("queue") for r in runs if r.get("queue") is not None]
print("work items in the accepted plan's queue:", {q: queues.count(q) for q in sorted(set(queues))})
