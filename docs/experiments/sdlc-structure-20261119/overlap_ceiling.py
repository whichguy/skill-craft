#!/usr/bin/env python3
"""What could overlap, and the most it could save, on the recorded runs.

1. Stage level, from ShipLoop's own stage table: neighbouring stages where the later one does not read the earlier
   one's result (`Stage.reads`), with each stage's edit classes (`Stage.edits`).
2. Step level, from each recorded step plan's `deps` and the navigator trace: the serial time of an item's build
   steps against the longest dependency path (every independent step started at once, no overhead), by host.

Usage: python3 -I overlap_ceiling.py <work>/census.json
"""
import collections
import json
import pathlib
import re
import statistics
import sys

sys.path.insert(0, "/Users/dadleet/src/skill-craft/skills/shiploop/scripts")
import itertools

import shiploop_stage_spec as spec

runs = [r for r in json.loads(pathlib.Path(sys.argv[1]).read_text()) if r["current_era"] and r["done"]]

# ---- 1. stage level
order = list(spec.PRELUDE) + list(spec.INNER) + list(spec.OUTER)
print("stage reads (what each stage's packet is given) and edit classes:")
reads = {}
for name in order:
    row = spec.stage(name)
    reads[name] = {r.split(":")[-1] for r in (row.reads or ())}
    print(f"  {name:<20} reads {sorted(reads[name]) or '-'}; edits {sorted(row.edits) or '-'}; review {row.improve or '-'}")
total = sum(sum(r["seconds"].values()) for r in runs)
stage_seconds = collections.Counter()
for run in runs:
    for label, value in run["seconds"].items():
        stage_seconds[label] += value
def both(name):
    return stage_seconds.get(name, 0.0) + stage_seconds.get("improve:" + name, 0.0)
print("\nneighbouring stages where the later does not read the earlier (share of run time: earlier, later, the smaller):")
ceiling = 0.0
for first, second in itertools.pairwise(order):
    if first not in reads[second]:
        a, b = both(first) / total, both(second) / total
        ceiling += min(a, b)
        print(f"  {first} -> {second}: {a:.1%}, {b:.1%}, {min(a, b):.1%}")
print(f"  sum of the smaller of each pair: {ceiling:.1%} of run time (an upper bound: pairs that share a stage cannot both overlap)")

# ---- 2. step level
def steps_of(run):
    """[(step id, deps, paths, seconds)] for a one-item run with no send-back, else None."""
    trace = pathlib.Path(run["trace"])
    rows = []
    for line in trace.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    commands = [r for r in rows if r.get("kind") == "command" and isinstance(r.get("stage"), list)]
    accepted = [a for r in commands for a in (r.get("accepted") or [])]
    if any(a["outcome"] != "done" for a in accepted) or sum(a["stage"] == "step-plan" for a in accepted) != 1:
        return None
    try:
        state = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", trace.with_name("state.md").read_text(), re.DOTALL).group(1))
    except (OSError, ValueError, AttributeError):
        return None
    plan_action = next(a["action"] for a in accepted if a["stage"] == "step-plan")
    plan = (state.get("accepted") or {}).get(plan_action) or {}
    steps = [s for s in plan.get("steps") or [] if isinstance(s, dict)]
    blocks, current, previous, reviewed = [], 0.0, commands[0]["ts"], None
    for row in commands:
        origin, target = row["stage"]
        gap = row["ts"] - previous
        previous = row["ts"]
        if origin != "improve":
            reviewed = origin
        label = origin if origin != "improve" else "improve:" + str(reviewed)
        if label in ("implement", "test", "document", "improve:document", "improve:test") and gap < 2700:
            current += gap
        left = (label in ("document", "improve:document") and target not in ("improve", "document")) or \
               (label == "test" and target not in ("test", "document", "improve"))
        if left and current:
            blocks.append(current)
            current = 0.0
    if len(blocks) != len(steps) or len(steps) < 2:
        return None
    return [(s["id"], list(s.get("deps") or []), set(s.get("paths") or []), blocks[n]) for n, s in enumerate(steps)]

by_host = collections.defaultdict(lambda: {"runs": 0, "wide": 0, "serial": 0.0, "saved": 0.0, "saved_disjoint": 0.0, "run_total": 0.0, "rows": []})
for run in runs:
    host = f"{run.get('host')}/{run.get('model')}"
    by_host[host]["run_total"] += sum(run["seconds"].values())
    steps = steps_of(run)
    if not steps:
        continue
    finish, finish_disjoint, ancestors = {}, {}, {}
    serial = sum(seconds for _, _, _, seconds in steps)
    running = []   # (finish time, paths) of steps placed so far, for the file-disjoint variant
    for ident, deps, paths, seconds in steps:
        start = max([finish[d] for d in deps if d in finish] or [0.0])
        finish[ident] = start + seconds
        # file-disjoint variant: a step also waits for every earlier step that shares one of its declared files
        start_disjoint = max([finish_disjoint[d] for d in deps if d in finish_disjoint]
                             + [end for end, other in running if other & paths] or [0.0])
        finish_disjoint[ident] = start_disjoint + seconds
        running.append((finish_disjoint[ident], paths))
    critical, critical_disjoint = max(finish.values()), max(finish_disjoint.values())
    record = by_host[host]
    record["runs"] += 1
    record["wide"] += critical < serial - 1
    record["serial"] += serial
    record["saved"] += serial - critical
    record["saved_disjoint"] += serial - critical_disjoint
    record["rows"].append((serial / 60, (serial - critical) / 60, (serial - critical_disjoint) / 60, len(steps),
                           sum(run["seconds"].values()) / 60, statistics.median(s for *_, s in steps)))
print("\nstep level: one-item runs with 2+ steps and no send-back; ideal overlap (every ready step at once, no overhead)")
print(f"{'host':<26}{'runs':>5}{'with width':>11}{'step time saved':>17}{'... file-disjoint only':>24}{'of ALL run time on host':>25}")
for host, record in sorted(by_host.items(), key=lambda kv: -kv[1]["run_total"]):
    if not record["runs"]:
        print(f"{host:<26}{0:>5}")
        continue
    print(f"{host:<26}{record['runs']:>5}{record['wide']:>11}{record['saved'] / record['serial']:>17.1%}"
          f"{record['saved_disjoint'] / record['serial']:>24.1%}{record['saved_disjoint'] / record['run_total']:>25.1%}")
print("\nthe runs where overlap would save the most (minutes): build-step time, saved, saved file-disjoint, steps, whole run, median step")
rows = sorted(((host, *row) for host, record in by_host.items() for row in record["rows"]), key=lambda r: -r[3])[:8]
for host, serial, saved, disjoint, count, whole, median in rows:
    print(f"  {host:<24} {serial:7.1f} {saved:7.1f} {disjoint:7.1f}  {count:>2} steps  run {whole:6.1f}  median step {median / 60:5.1f}")
