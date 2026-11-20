#!/usr/bin/env python3
"""How long is one piece of read-mostly work, by host? Median seconds per run in the stages and reviews a read-only
worker could share, set beside the fan-out break-even the parallel-execution study measured (seconds of the model's
own time per task below which fresh workers lose to one context: Claude 10 to 14, Grok 3 to 21, Codex 43 to 60;
docs/experiments/parallel-plan-execution-20261114/skill-layer-contract.md section 6).

Usage: python3 -I task_sizes.py <work>/census.json
"""
import collections
import json
import pathlib
import statistics
import sys

runs = [r for r in json.loads(pathlib.Path(sys.argv[1]).read_text()) if r["current_era"] and r["done"]]
LABELS = ["discovery", "research", "improve:spec", "improve:test-strategy", "improve:plan", "improve:step-plan",
          "improve:document", "improve:carry-forward", "product-acceptance"]
by_host = collections.defaultdict(lambda: collections.defaultdict(list))
for run in runs:
    host = f"{run.get('host')}/{run.get('model')}"
    steps = max(sum(run["steps"].values()), 1)
    for label in LABELS:
        value = run["seconds"].get(label)
        if value:
            # the step review runs once per step: report it per step
            by_host[host][label].append(value / steps if label == "improve:document" else value)
print(f"{'median seconds per run (step review: per step)':<48}" + "".join(f"{h.split('/')[1][:14]:>16}" for h in by_host))
for label in LABELS:
    cells = "".join(f"{statistics.median(by_host[h][label]) if by_host[h][label] else float('nan'):>16.0f}" for h in by_host)
    print(f"{label.replace('improve:', 'review of '):<48}{cells}")
print("runs: " + ", ".join(f"{h} {max(len(v) for v in by_host[h].values())}" for h in by_host))
