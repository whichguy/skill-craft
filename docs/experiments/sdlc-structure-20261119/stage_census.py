#!/usr/bin/env python3
"""Census of recorded ShipLoop runs: where the time goes by stage.

Reads <root>/**/.shiploop-runs/*/run/trace.jsonl (the navigator's own trace: one
`packet` row per issued packet, one `command` row per CLI call with the stage it
moved from and to and the results it accepted).

Attribution: the seconds between two consecutive `command` rows belong to the
stage the run was in during that gap (the later row's `stage[0]`). An Improve
review shows as stage `improve`; it is charged to `improve:<stage it reviews>`.
A gap longer than IDLE seconds is counted as idle (a stopped session, a wait for
the owner), not as stage time, and reported separately.

Usage: python3 -I stage_census.py OUT.json [ROOT ...]
"""
import json
import pathlib
import statistics
import sys

IDLE = 45 * 60
PRELUDE = ("intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare")
INNER = ("step-plan", "test-spec", "validate-existing", "implement", "test", "document", "carry-forward")
OUTER = ("system-test-author", "system-test", "product-acceptance", "release-plan", "release-check", "release",
         "release-verify", "operations", "handoff")
CURRENT = set(PRELUDE) | set(INNER) | set(OUTER)


def phase(stage):
    base = stage.split(":", 1)[1] if stage.startswith("improve:") else stage
    if base in PRELUDE:
        return "prelude"
    if base in INNER:
        return "inner"
    if base in OUTER:
        return "outer"
    return "other"


def read_run(trace):
    rows = []
    for line in trace.read_text(errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    commands = [r for r in rows if r.get("kind") == "command" and isinstance(r.get("stage"), list)]
    if len(commands) < 3:
        return None
    seconds, idle, refusals, outcomes, packets = {}, 0.0, {}, {}, {}
    items, steps, improve_passes = set(), {}, {}
    reviewed = None
    previous = commands[0]["ts"]
    stages_seen = set()
    for row in rows:
        if row.get("kind") == "packet" and row.get("stage"):
            packets.setdefault(row["stage"], []).append(row.get("chars") or 0)
    for row in commands:
        origin, _target = row["stage"]
        gap = row["ts"] - previous
        previous = row["ts"]
        if origin != "improve":
            reviewed = origin
        label = origin
        if origin == "improve":
            label = "improve:" + (reviewed or "?")
            if row.get("verb") == "improve-pass" and row.get("exit") == 0:
                improve_passes[reviewed] = improve_passes.get(reviewed, 0) + 1
        if origin:
            stages_seen.add(origin)
            if gap > IDLE:
                idle += gap
            else:
                seconds[label] = seconds.get(label, 0.0) + gap
            if row.get("exit") not in (0, None) and row.get("verb") in ("complete", "check", "improve-pass"):
                key = f"{label}|{row.get('verb')}"
                refusals[key] = refusals.get(key, 0) + 1
        for accepted in row.get("accepted") or []:
            key = f"{accepted['stage']}|{accepted['outcome']}"
            outcomes[key] = outcomes.get(key, 0) + 1
            if accepted.get("item"):
                items.add(accepted["item"])
                if accepted["stage"] == "implement" and accepted["outcome"] == "done":
                    steps[accepted["item"]] = steps.get(accepted["item"], 0) + 1
    last = commands[-1]
    done = last.get("status") == "done" or last["stage"][1] == "done"
    return {
        "seconds": seconds, "idle": idle, "refusals": refusals, "outcomes": outcomes,
        "items": len(items), "steps": steps, "done": done, "stages": sorted(stages_seen),
        "current_era": "validate-existing" in " ".join(outcomes) and stages_seen <= (CURRENT | {"improve"}),
        "packets": {k: v for k, v in packets.items()}, "improve_passes": improve_passes,
        "span": commands[-1]["ts"] - commands[0]["ts"], "first": rows[0].get("at"),
    }


def invocation(run_root):
    """The E2E folder two levels above .shiploop-runs holds invocation.json."""
    for parent in list(run_root.parents)[:5]:
        candidate = parent / "invocation.json"
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text())
            except ValueError:
                return {}
            return {"host": data.get("host"), "model": data.get("model"), "effort": data.get("effort"),
                    "case": data.get("case") or data.get("case_name"), "folder": str(parent)}
    return {}


def main(argv):
    out = pathlib.Path(argv[0])
    roots = [pathlib.Path(a) for a in argv[1:]] or sorted(pathlib.Path("/Users/dadleet").glob("e2e-runs*"))
    runs = []
    seen = set()
    for root in roots:
        for trace in sorted(root.glob("**/.shiploop-runs/*/run/trace.jsonl")):
            real = trace.resolve()
            if real in seen:
                continue
            seen.add(real)
            record = read_run(trace)
            if record is None:
                continue
            record.update(invocation(trace.parent))
            record["trace"] = str(trace)
            runs.append(record)
    out.write_text(json.dumps(runs, indent=1))
    report(runs)


def share_table(runs, title):
    totals = {}
    per_run_share = {}
    grand = 0.0
    for run in runs:
        total = sum(run["seconds"].values())
        if total <= 0:
            continue
        grand += total
        for stage, value in run["seconds"].items():
            totals[stage] = totals.get(stage, 0.0) + value
        for stage in set(run["seconds"]):
            per_run_share.setdefault(stage, []).append(run["seconds"][stage] / total)
    print(f"\n## {title}: {len(runs)} runs, {grand / 3600:.1f} stage-hours")
    order = [s for group in (PRELUDE, INNER, OUTER) for s in group]
    rows = []
    for stage in order:
        own = totals.get(stage, 0.0)
        review = totals.get("improve:" + stage, 0.0)
        shares = per_run_share.get(stage, [])
        rows.append((stage, own, review, statistics.median(shares) if shares else 0.0, len(shares)))
    print(f"{'stage':<20}{'own %':>8}{'review %':>10}{'both %':>8}{'median own % (runs with it)':>30}")
    for stage, own, review, median, count in rows:
        print(f"{stage:<20}{own / grand:>8.1%}{review / grand:>10.1%}{(own + review) / grand:>8.1%}{median:>20.1%} ({count})")
    by_phase = {}
    review_total = 0.0
    for stage, value in totals.items():
        by_phase[phase(stage)] = by_phase.get(phase(stage), 0.0) + value
        if stage.startswith("improve:"):
            review_total += value
    print("phase shares:", ", ".join(f"{k} {v / grand:.1%}" for k, v in sorted(by_phase.items())))
    print(f"Improve review share of all stage time: {review_total / grand:.1%}")
    build = totals.get("implement", 0.0) + totals.get("test", 0.0)
    print(f"implement + test (own time): {build / grand:.1%}; implement alone {totals.get('implement', 0.0) / grand:.1%}")
    planning = sum(totals.get(s, 0.0) + totals.get('improve:' + s, 0.0)
                   for s in ("intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare", "step-plan",
                             "test-spec"))
    print(f"before the first product edit (intake..test-spec, with reviews): {planning / grand:.1%}")
    return totals, grand


def report(runs):
    print(f"runs read: {len(runs)}")
    current = [r for r in runs if r["current_era"]]
    done = [r for r in current if r["done"]]
    print(f"current stage set: {len(current)}; of those finished: {len(done)}")
    hosts = {}
    for run in done:
        key = f"{run.get('host')}/{run.get('model')}"
        hosts[key] = hosts.get(key, 0) + 1
    print("finished current-era runs by host/model:", json.dumps(hosts, indent=0))
    share_table(done, "finished runs, current stage set")
    big = [r for r in done if sum(r["seconds"].values()) >= 3600]
    small = [r for r in done if sum(r["seconds"].values()) < 3600]
    if big:
        share_table(big, "finished runs of an hour or more")
    if small:
        share_table(small, "finished runs under an hour")
    # work items and steps
    items = [r["items"] for r in done]
    step_counts = [n for r in done for n in r["steps"].values()]
    print(f"\n## shape of the work: work items per finished run: "
          f"{ {n: items.count(n) for n in sorted(set(items))} }")
    print(f"implement actions accepted per work item: { {n: step_counts.count(n) for n in sorted(set(step_counts))} }")
    # outcomes
    outcomes = {}
    for run in current:
        for key, value in run["outcomes"].items():
            outcomes[key] = outcomes.get(key, 0) + value
    print("\n## accepted outcomes that are not `done` (all current-era runs, finished or not)")
    for key in sorted(outcomes):
        stage, outcome = key.split("|")
        if outcome != "done":
            total = sum(v for k, v in outcomes.items() if k.split("|")[0] == stage)
            print(f"{stage:<20}{outcome:<10}{outcomes[key]:>5} of {total} accepted results ({outcomes[key] / total:.1%})")
    runs_with_sendback = sum(1 for r in current if any(k.endswith("|send-back") for k in r["outcomes"]))
    runs_with_addwork = sum(1 for r in current if any(k.endswith("|add-work") for k in r["outcomes"]))
    print(f"runs with a send-back: {runs_with_sendback} of {len(current)}; with add-work: {runs_with_addwork}")
    # refusals
    refusals = {}
    for run in current:
        for key, value in run["refusals"].items():
            refusals[key] = refusals.get(key, 0) + value
    print("\n## refused commands by stage (exit != 0)")
    for key, value in sorted(refusals.items(), key=lambda kv: -kv[1])[:25]:
        print(f"{key:<40}{value:>6}")
    # improve passes
    passes = {}
    for run in done:
        for stage, value in run["improve_passes"].items():
            passes.setdefault(stage, []).append(value)
    print("\n## Improve passes per reviewed stage (finished runs): median, max, runs")
    for stage, values in sorted(passes.items()):
        print(f"{stage:<20}{statistics.median(values):>6}{max(values):>6}{len(values):>6}")
    # packet sizes
    sizes = {}
    for run in done:
        for stage, values in run["packets"].items():
            sizes.setdefault(stage, []).extend(values)
    print("\n## packet size by stage (chars): median, count")
    for stage in [s for g in (PRELUDE, INNER, OUTER) for s in g] + ["improve"]:
        if stage in sizes:
            print(f"{stage:<20}{statistics.median(sizes[stage]):>10.0f}{len(sizes[stage]):>8}")
    idle = sum(r["idle"] for r in done)
    print(f"\nidle gaps over {IDLE // 60} min excluded from stage time: {idle / 3600:.1f} h across finished runs")


if __name__ == "__main__":
    main(sys.argv[1:])
