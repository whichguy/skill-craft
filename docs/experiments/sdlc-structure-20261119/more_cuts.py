#!/usr/bin/env python3
"""Further cuts over finished current-era runs: planning experiments, end-of-work review yield by step count,
why step-plan checks are refused, and how much packet text the unused plan-graph check takes."""
import collections
import json
import pathlib
import re
import sys

S = pathlib.Path(sys.argv[1])  # the working folder that holds census.json and review_edits.json
runs = [r for r in json.loads(pathlib.Path(S / "census.json").read_text()) if r["current_era"] and r["done"]]
edits = json.loads(pathlib.Path(S / "review_edits.json").read_text())
by_dir = {}
for row in edits:
    by_dir.setdefault(str(pathlib.Path(row["dir"]).parent.parent), []).append(row)
dispositions = collections.Counter(); reconciled = 0; plans = 0; probed_runs = 0
cf = collections.defaultdict(lambda: [0, 0, 0])
refusal_text = collections.Counter()
for run in runs:
    rundir = pathlib.Path(run["trace"]).parent
    try:
        state = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", (rundir / "state.md").read_text(), re.DOTALL).group(1))
    except (OSError, ValueError, AttributeError, KeyError):
        continue
    stage_of = {}
    for line in pathlib.Path(run["trace"]).read_text().splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        for accepted in row.get("accepted") or []:
            stage_of[accepted["action"]] = accepted["stage"]
        if row.get("kind") == "command" and row.get("exit") not in (0, None) and isinstance(row.get("stage"), list) \
                and row["stage"][0] == "step-plan" and row.get("error"):
            text = re.sub(r"/[^\s'\"`)]+", "<path>", row["error"])
            text = re.sub(r"\b(nav-[0-9a-f]+|[SCEWR]-?\d+|TC[_-]?\d+|\d+)\b", "N", text)
            refusal_text[text[:95]] += 1
    reconciled += bool(state.get("planning_reconciliations"))
    for action, result in (state.get("accepted") or {}).items():
        if stage_of.get(action) == "plan":
            plans += 1
            kinds = [a.get("disposition") for a in result.get("assumptions") or [] if isinstance(a, dict)]
            dispositions.update(kinds)
            probed_runs += "probed" in kinds
    steps = max(run["steps"].values()) if run["steps"] else 0
    bucket = "1 step" if steps <= 1 else "2+ steps"
    for row in by_dir.get(str(rundir), []):
        if row["stage"] == "carry-forward":
            cf[bucket][0] += 1
            cf[bucket][1] += bool(row["logged_tree"])
            cf[bucket][2] += bool(row["logged_tree"] and {"code", "test"} & set(row.get("classes") or []))
print(f"plans {plans}; assumptions by disposition {dict(dispositions)}; plans with a probed assumption {probed_runs}; "
      f"runs with a planning reconciliation {reconciled}")
print("end-of-work (carry-forward) review, by the item's step count: reviews, edited files, edited code or tests")
for bucket, (n, edited, code) in cf.items():
    print(f"  {bucket:<9} n={n:<4} edited {edited / n:.0%}  code or tests {code / n:.0%}")
print("most common refused step-plan commands (text normalised):")
for text, count in refusal_text.most_common(14):
    print(f"  {count:4}  {text}")
