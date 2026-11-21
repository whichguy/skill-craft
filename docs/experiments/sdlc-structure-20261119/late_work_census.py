#!/usr/bin/env python3
"""How often a stage after the build opened a new work item, by driver, and what it added (round 7, update).

Reads one or more run lists written by review_option_census.py (OUT.json: every run directory with its driver,
whether it is a whole delivery, and its last status) and, for each finished whole delivery, its `run/trace.jsonl`:

  planned items     accepted `carry-forward -> step-plan` moves: the plan's own later work items;
  late work         accepted moves into `step-plan` from any stage outside the build loop (not `prepare`,
                    `carry-forward`, a build stage or a review): a stage after the build opened a new work item;
  minutes added     from the first such move to the run's last accepted command.

It prints, per driver: runs, runs whose plan held more than one work item, runs with late work and which stage
opened it, the median minutes of runs without and with late work, and the median minutes added. A run listed in
more than one file is counted once.

Usage: python3 -I late_work_census.py CENSUS.json [CENSUS.json ...]
"""
import collections
import json
import pathlib
import statistics
import sys

BUILD = ("implement", "test", "document", "test-spec", "validate-existing")
NOT_LATE = ("prepare", "carry-forward", "step-plan", "improve", *BUILD)


def main(paths):
    rows, seen = [], set()
    for path in paths:
        for row in json.loads(pathlib.Path(path).read_text()):
            if row["run"] not in seen:
                seen.add(row["run"])
                rows.append(row)
    whole = [r for r in rows if not r.get("seeded") and r.get("kind") != "step-slice" and r.get("host") and r.get("status") == "done"]
    cells, missing = collections.defaultdict(list), 0
    for row in whole:
        trace = pathlib.Path(row["run"]) / "trace.jsonl"
        if not trace.exists():
            missing += 1
            continue
        events = [json.loads(line) for line in trace.read_text(errors="replace").splitlines() if line.strip()]
        accepted = [e for e in events if e.get("kind") == "command" and e.get("verb") == "complete" and e.get("exit") == 0
                    and isinstance(e.get("stage"), list) and isinstance(e.get("ts"), (int, float))]
        start = events[0].get("ts") if events else None
        if not accepted or not isinstance(start, (int, float)):
            continue
        late = [e for e in accepted if e["stage"][1] == "step-plan" and e["stage"][0] not in NOT_LATE]
        end = accepted[-1]["ts"]
        cells[f"{row['host']} {row['model']} {row['effort'] or '-'}"].append({
            "items": 1 + sum(1 for e in accepted if e["stage"] == ["carry-forward", "step-plan"]),
            "late": [e["stage"][0] for e in late], "minutes": (end - start) / 60,
            "added": (end - late[0]["ts"]) / 60 if late else 0.0, "folder": pathlib.Path(row["folder"] or row["run"]).name})
    total = sum(len(group) for group in cells.values())
    with_late = sum(1 for group in cells.values() for run in group if run["late"])
    print(f"finished whole deliveries read: {total} (trace missing for {missing}); with late work: {with_late}")
    print(f"\n{'driver':<40}{'runs':>5}{'plans of >1 item':>18}{'late work':>11}{'min, none':>11}{'min, late':>11}{'min added':>11}  opened by")
    for name, group in sorted(cells.items(), key=lambda kv: -len(kv[1])):
        late = [run for run in group if run["late"]]
        none = [run["minutes"] for run in group if not run["late"]]
        opened = collections.Counter(stage for run in late for stage in run["late"])
        print(f"{name:<40}{len(group):>5}{sum(run['items'] > 1 for run in group):>18}{len(late):>11}"
              f"{(f'{statistics.median(none):.0f}' if none else '-'):>11}"
              f"{(f'{statistics.median(run["minutes"] for run in late):.0f}' if late else '-'):>11}"
              f"{(f'{statistics.median(run["added"] for run in late):.0f}' if late else '-'):>11}  {dict(opened) or ''}")
    print("\n(min: first trace row to the last accepted command, waits included; min added: the first late move to that end)")
    print("runs with late work:")
    for name, group in sorted(cells.items()):
        for run in group:
            if run["late"]:
                print(f"  {name:<40}{run['folder']:<44}{run['minutes']:>6.0f} min, {run['added']:>4.0f} added, opened by {', '.join(run['late'])}")


if __name__ == "__main__":
    main(sys.argv[1:])
