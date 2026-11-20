#!/usr/bin/env python3
"""Slice minutes by the number of steps the plan held, whichever arm planned it (exploratory, round 6).

Round 6's baseline planner chose one step by itself in some slices, so its registered arm comparison has cells with
no contrast. This pools every baseline and F1 slice of rounds 4 to 6 (the L0 and K0 arms are left out) by driver and
case, and groups them by the steps of the first accepted step plan. It is not a registered reading: in a baseline
slice the planner chose the step count, and the rounds ran hours apart.

Each FOLDER holds census.json (stage_census.py), iteration.json (iteration_census.py --all) and snapshots.json
(slice_snapshots.py).

The steps and criteria of each slice's first accepted step plan are read from its run folder while that exists and
kept in slice-plans.json beside this script, so the table can be made again from the repository alone.

Usage: python3 -I steps_pooled.py FOLDER [FOLDER ...]
"""
import collections
import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import iteration_census as base
import slice_report

AFTER = ("test", "document", "improve:document")


def first_plan(rundir):
    """Steps and criteria of the first accepted done step plan (a redone plan after a send-back is not the cut)."""
    for path in sorted((rundir / "results").glob("nav-*.md"), key=lambda p: p.stat().st_mtime):
        record = base.state(path) or {}
        result = record.get("result")
        if record.get("stage") == "step-plan" and isinstance(result, dict) and result.get("outcome") == "done":
            return len(result.get("steps") or ()), len(result.get("criteria") or ())
    return None, None


def main(folders):
    rows, seen = [], set()
    kept_at = pathlib.Path(__file__).resolve().parent / "slice-plans.json"
    kept = json.loads(kept_at.read_text()) if kept_at.exists() else {}
    for folder in map(pathlib.Path, folders):
        census = json.loads((folder / "census.json").read_text())
        steps = collections.defaultdict(list)
        for step in json.loads((folder / "iteration.json").read_text())["steps"]:
            steps[pathlib.Path(step["run"]).parents[3].name].append(step)
        shots = json.loads((folder / "snapshots.json").read_text()) if (folder / "snapshots.json").exists() else {}
        for run in census:
            name = slice_report.name_of(run)
            arm = slice_report.arm_of(name)
            key = (run["folder"], name)
            if name.startswith("rehearsal") or arm not in ("base", "F1") or key in seen or not slice_report.inner_loop_done(run):
                continue
            seen.add(key)
            rundir = pathlib.Path(run["trace"]).parent
            if rundir.exists():
                kept[run["folder"]] = list(first_plan(rundir))
            planned, criteria = kept.get(run["folder"], (None, None))
            mine = steps.get(name, [])
            seconds = run["seconds"]
            end = (shots.get(name) or {}).get("end") or {}
            rows.append({"driver": f"{run['model']} {run['effort']}", "case": run["case"], "arm": arm, "name": name,
                         "planned": planned, "criteria": criteria, "built": len(mine),
                         "minutes": sum(seconds.values()) / 60, "after": sum(seconds.get(k, 0) for k in AFTER),
                         "parts": {label: sum(seconds.get(k, 0) for k in keys) for label, keys in slice_report.PARTS},
                         "lines": sum((s.get("built") or {}).get("code", 0) for s in mine),
                         "refused": sum(s.get("test_refused") or 0 for s in mine),
                         "sent_back": sum(count for key, count in run["outcomes"].items() if key.endswith("|send-back")),
                         "hidden": len(end.get("passed") or ()) if end.get("observed") else None})
    kept_at.write_text(json.dumps(kept, indent=1, sort_keys=True) + "\n")
    print(f"slices: {len(rows)} (baseline {sum(r['arm'] == 'base' for r in rows)}, F1 {sum(r['arm'] == 'F1' for r in rows)}), every one "
          "with its inner loop complete")
    cells = collections.defaultdict(list)
    for row in rows:
        cells[(row["driver"], row["case"])].append(row)
    print(f"\n{'driver':<24}{'case':<20}{'steps planned':>14}{'slices':>7}{'of them F1':>11}{'criteria':>10}{'minutes (each)':>30}{'mean':>7}"
          f"{'product lines':>14}{'test refusals':>14}{'send-backs':>11}{'hidden at end':>15}")
    for (driver, case), group in sorted(cells.items()):
        by_count = collections.defaultdict(list)
        for row in group:
            by_count[row["planned"]].append(row)
        for count, part in sorted(by_count.items(), key=lambda kv: (kv[0] is None, kv[0])):
            hidden = sorted({row["hidden"] for row in part if row["hidden"] is not None})
            print(f"{driver:<24}{case:<20}{count if count is not None else '?':>14}{len(part):>7}{sum(r['arm'] == 'F1' for r in part):>11}"
                  f"{statistics.median(r['criteria'] for r in part):>10.0f}{', '.join(f'{r["minutes"]:.1f}' for r in part):>30}"
                  f"{statistics.mean(r['minutes'] for r in part):>7.1f}{statistics.median(r['lines'] for r in part):>14.0f}"
                  f"{statistics.mean(r['refused'] for r in part):>14.1f}{sum(r['sent_back'] for r in part):>11}"
                  f"{', '.join(map(str, hidden)) or '-':>15}")
    print("\n== one step against two or more, same driver and case ==")
    ratios = []
    for (driver, case), group in sorted(cells.items()):
        one = [r["minutes"] for r in group if r["planned"] == 1]
        more = [r["minutes"] for r in group if r["planned"] and r["planned"] > 1]
        if one and more:
            change = statistics.mean(one) / statistics.mean(more) - 1
            ratios.append(change)
            print(f"  {driver:<24}{case:<20} one step {statistics.mean(one):.1f} min ({len(one)}); more {statistics.mean(more):.1f} min "
                  f"({len(more)}); {change:+.0%}; minutes saved per step removed "
                  f"{(statistics.mean(more) - statistics.mean(one)) / (statistics.mean(r['planned'] for r in group if r['planned'] and r['planned'] > 1) - 1):.1f}")
    if ratios:
        print(f"  cells with both shapes: {len(ratios)}; one step is faster in {sum(c < 0 for c in ratios)}, by 15% or more in "
              f"{sum(c <= -0.15 for c in ratios)}; median change {statistics.median(ratios):+.0%}")
    print("\n== where the difference is: mean seconds by part, one step and (two or more), same driver and case ==")
    print(f"{'driver':<24}{'case':<20}" + "".join(f"{label:>16}" for label, _ in slice_report.PARTS))
    for (driver, case), group in sorted(cells.items()):
        one = [r for r in group if r["planned"] == 1]
        more = [r for r in group if r["planned"] and r["planned"] > 1]
        if one and more:
            print(f"{driver:<24}{case:<20}" + "".join(
                f"{f'{statistics.mean(r["parts"][label] for r in one):.0f} ({statistics.mean(r["parts"][label] for r in more):.0f})':>16}"
                for label, _ in slice_report.PARTS))


if __name__ == "__main__":
    main(sys.argv[1:])
