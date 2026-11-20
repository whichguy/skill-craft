#!/usr/bin/env python3
"""More cuts of the recorded runs (census.json from stage_census.py):
verbs, planning window, per-step costs, send-back cost, source-only releases."""
import collections
import json
import pathlib
import re
import statistics
import sys

runs = [r for r in json.loads(pathlib.Path(sys.argv[1]).read_text()) if r["current_era"]]
done = [r for r in runs if r["done"]]
def rows_of(run):
    out = []
    for line in pathlib.Path(run["trace"]).read_text().splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out
def med(values):
    return statistics.median(values) if values else float("nan")

verbs = collections.Counter(); verb_fail = collections.Counter()
window = collections.defaultdict(list); total_by_host = collections.defaultdict(list)
per_step = collections.defaultdict(list)
sendback_cost = collections.defaultdict(list)
release_na = release_all = 0
outer_tail = collections.defaultdict(list)
for run in runs:
    rows = rows_of(run)
    commands = [r for r in rows if r.get("kind") == "command"]
    for row in commands:
        verbs[row.get("verb")] += 1
        if row.get("exit") not in (0, None):
            verb_fail[row.get("verb")] += 1
    if not run["done"]:
        continue
    staged = [r for r in commands if isinstance(r.get("stage"), list)]
    start = staged[0]["ts"]
    first_impl = next((r["ts"] for r in staged if r["stage"][1] == "implement"), None)
    host = f"{run.get('host')}/{run.get('model')}"
    if first_impl:
        window[host].append((first_impl - start) / 60)
        total_by_host[host].append(sum(run["seconds"].values()) / 60)
    # per step: time in implement/test/document/improve:document between entering implement and leaving the document review
    previous = start; reviewed = None; current = collections.Counter(); in_step = False
    for row in staged:
        origin, target = row["stage"]; gap = row["ts"] - previous; previous = row["ts"]
        if origin != "improve":
            reviewed = origin
        label = origin if origin != "improve" else "improve:" + str(reviewed)
        if label in ("implement", "test", "document", "improve:document", "improve:test") and gap < 2700:
            current[label] += gap
        left_step = (label in ("document", "improve:document") and target not in ("improve", "document")) or \
                    (label == "test" and target not in ("test", "document", "improve"))
        if left_step and current:
            for key in ("implement", "test", "document", "improve:document"):
                per_step[key].append(current.get(key, 0.0))
            per_step["all"].append(sum(current.values()))
            current = collections.Counter()
    # send-back cost: seconds from the accepted send-back to the next accepted `done` of the same stage
    accepts = [(r["ts"], a) for r in staged for a in (r.get("accepted") or [])]
    for index, (ts, accepted) in enumerate(accepts):
        if accepted["outcome"] == "send-back":
            later = next((t for t, a in accepts[index + 1:] if a["stage"] == accepted["stage"] and a["outcome"] == "done"), None)
            if later:
                sendback_cost[accepted["stage"]].append((later - ts) / 60)
    # source-only releases
    try:
        state = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", pathlib.Path(run["trace"]).with_name("state.md").read_text(), re.DOTALL).group(1))
    except (OSError, ValueError, AttributeError, KeyError):
        continue
    stage_of = {a["action"]: a["stage"] for r in staged for a in (r.get("accepted") or [])}
    for action, result in (state.get("accepted") or {}).items():
        if stage_of.get(action) == "release":
            release_all += 1
            text = (str(result.get("summary")) + str(result.get("headline"))).lower()
            na = bool(re.search(r"not[- ]applicable|no deploy|source[- ]only|no (remote |release )?target|nothing to (deploy|release)|no release (action|step)|local(ly)? (only|delivery|checkout|return)|no publish", text))
            release_na += na
            tail = sum(v for k, v in run["seconds"].items() if k.split(":")[-1] in ("release-plan", "release-check", "release", "release-verify", "operations"))
            outer_tail["source-only" if na else "other"].append(tail / sum(run["seconds"].values()))

print("verbs (all current-era runs):", ", ".join(f"{v} {n} ({verb_fail[v]} refused)" for v, n in verbs.most_common(16)))
print("\nplanning window = start to the first implement packet, minutes (finished runs):")
for host, values in sorted(window.items(), key=lambda kv: -len(kv[1])):
    over = sum(v > 30 for v in values)
    print(f"  {host:<26} n={len(values):<4} median {med(values):6.1f}  max {max(values):6.1f}  over 30 min: {over}   median whole run {med(total_by_host[host]):6.1f}")
print("\nper build step (implement through its document review), seconds, finished runs:")
for key in ("implement", "test", "document", "improve:document", "all"):
    values = per_step[key]
    print(f"  {key:<18} n={len(values):<5} median {med(values):7.0f}  mean {sum(values) / len(values):7.0f}")
print("\nsend-back: minutes from the send-back to that stage's next accepted done:")
for stage, values in sendback_cost.items():
    print(f"  {stage:<20} n={len(values):<4} median {med(values):6.1f}  max {max(values):6.1f}")
print(f"\nrelease results that read as nothing-to-deploy: {release_na} of {release_all}")
for key, values in outer_tail.items():
    print(f"  {key}: release-plan..operations share of the run: median {med(values):.1%} (n={len(values)})")
