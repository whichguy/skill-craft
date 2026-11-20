#!/usr/bin/env python3
"""Score snapshot_acceptance.py's output: how correct the product already was at each point of a run.

Reads one or more output files (one per shard), keeps the runs whose delivered product passes every held-out check
when graded again today (so a check module that changed since the run does not count against a snapshot), and
prints, for each snapshot, the share of runs that pass every check and the share of checks passed; then every run
in which an earlier snapshot failed a check that the delivered product passes, with the stage that first passed it.

Usage: python3 -I snapshot_score.py OUT.json [OUT.json ...]
"""
import collections
import json
import pathlib
import sys

ORDER = ("base", "implement", "test", "before_review", "commit", "before_end_review", "delivered")
FIXED_BY = {"test": "the test stage", "before_review": "the document stage", "commit": "the step review",
            "before_end_review": "carry-forward", "delivered": "the end-of-work review or a later stage"}


def main(paths):
    runs = {}
    for path in paths:
        runs.update(json.loads(pathlib.Path(path).read_text())["runs"])
    usable, changed, unobserved = {}, 0, 0
    for name, run in runs.items():
        shots = run["snapshots"]
        if any(not shots[point].get("observed") for point in ORDER[1:]):
            unobserved += 1
            continue
        if len(shots["delivered"]["passed"]) != len(run["ids"]):
            changed += 1
            continue
        usable[name] = run
    print(f"graded runs: {len(runs)}; left out: {unobserved} with a snapshot that could not be graded, {changed} whose "
          f"delivered product does not pass every check when graded again; scored: {len(usable)}")
    print(f"\n{'snapshot':<20}{'runs passing every check':>26}{'checks passed':>18}")
    for point in ORDER:
        clean = sum(len(r["snapshots"][point].get("passed") or []) == len(r["ids"]) for r in usable.values()
                    if r["snapshots"][point].get("observed"))
        seen = [r for r in usable.values() if r["snapshots"][point].get("observed")]
        checks = sum(len(r["ids"]) for r in seen)
        passed = sum(len(r["snapshots"][point]["passed"]) for r in seen)
        print(f"{point:<20}{clean:>12} of {len(seen):<3}{clean / len(seen):>7.0%}{passed:>10} of {checks:<5}{passed / checks:>6.1%}")
    print("\nby model and effort, runs whose `implement` snapshot passes every check:")
    groups = collections.defaultdict(list)
    for run in usable.values():
        groups[(run["model"], run["effort"] or "-", "one step" if run["steps"] == 1 else "several steps")].append(run)
    for key, group in sorted(groups.items(), key=lambda pair: -len(pair[1])):
        clean = sum(len(r["snapshots"]["implement"]["passed"]) == len(r["ids"]) for r in group)
        print(f"  {' '.join(key):<40}{clean:>4} of {len(group)}")
    print("\nruns where a snapshot failed a check the delivered product passes:")
    fixed = collections.Counter()
    for name, run in sorted(usable.items(), key=lambda pair: pair[1]["case"]):
        shots = run["snapshots"]
        late = {}
        for check in run["ids"]:
            if check in shots["implement"]["passed"]:
                continue
            first = next(point for point in ORDER[2:] if check in shots[point]["passed"])
            late[check] = (first, (shots["implement"]["failed"] or {}).get(check) or "")
        regress = [check for check in run["ids"] if check in shots["implement"]["passed"]
                   and any(check not in shots[point]["passed"] for point in ORDER[2:])]
        if not late and not regress:
            continue
        print(f"  {run['case']} ({run['model']} {run['effort']}, {run['steps']} steps) {pathlib.Path(name).parents[3].name}")
        for check, (first, note) in late.items():
            fixed[FIXED_BY[first]] += 1
            print(f"    {check}: failed at implement, first passes after {FIXED_BY[first]} | {note[:150]}")
        for check in regress:
            print(f"    {check}: passed at implement and failed at a later snapshot")
    print("\nchecks failing at `implement` and passing in the delivered product, by the stage after which they first pass:",
          dict(fixed) or "none")


if __name__ == "__main__":
    main(sys.argv[1:])
