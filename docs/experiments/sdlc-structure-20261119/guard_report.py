#!/usr/bin/env python3
"""The guard round's registered measures and readings (round 6): arm F1 against the shipped text on an item large
enough to need cutting.

FOLDER holds census.json (stage_census.py), iteration.json (iteration_census.py --all) and snapshots.json
(slice_snapshots.py) of the guard slices. Each slice's first accepted step plan is read from its run folder while that
exists and kept in FOLDER/plans.json, so the report can be made again from the repository alone.

A slice whose folder name holds "-F1" is the arm whose step plan is asked for the fewest steps (at most 12 criteria
and 6 product files a step); a name that starts with "rehearsal" is not counted. A plan-only run (stopped after
step-plan) is listed by its plan alone.

Usage: python3 -I guard_report.py FOLDER
"""
import collections
import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import iteration_census as base
import slice_report

CRITERIA, FILES = 12, 6
NOT_AT_IMPLEMENT = ("suite",)  # counts the new tests, which the test stage writes after implement


def arm_of(name):
    return "F1" if "-F1" in name else "base"


def first_plan(rundir):
    """The first accepted done step plan: criteria, and each step's criteria count and product files."""
    for path in sorted((rundir / "results").glob("nav-*.md"), key=lambda p: p.stat().st_mtime):
        record = base.state(path) or {}
        result = record.get("result")
        if record.get("stage") == "step-plan" and isinstance(result, dict) and result.get("outcome") == "done":
            def product(paths):
                return [p for p in paths or () if base.item_scope.classify(p) == "code"]
            return {"criteria": len(result.get("criteria") or ()), "files": product(result.get("paths")),
                    "steps": [{"id": step.get("id"), "criteria": len(step.get("criteria") or ()),
                               "files": product(step.get("paths")), "listed": bool(step.get("paths")),
                               "task": str(step.get("task") or "")[:160]}
                              for step in result.get("steps") or () if isinstance(step, dict)]}
    return None


def built_files(worktree, mine):
    """The product files each built step changed, from its base tree to its step commit (None where a tree is missing)."""
    out = []
    for step in mine:
        trees = step.get("trees") or {}
        listing = base.git(worktree, "diff", "--name-only", "--no-renames", trees["base"], trees["commit"]) \
            if trees.get("base") and trees.get("commit") else None
        out.append(None if listing is None else sorted(
            path for path in listing.splitlines()
            if path and not path.startswith(base.SKIP_PREFIX) and base.item_scope.classify(path) == "code"))
    return out


def shape(plan):
    if not plan:
        return "no plan"
    per_step = ", ".join(str(step["criteria"]) for step in plan["steps"])
    files = ", ".join(str(len(step["files"])) if step["listed"] else "-" for step in plan["steps"])
    return (f"{plan['criteria']} criteria, {len(plan['steps'])} step{'s' if len(plan['steps']) != 1 else ''} ({per_step}); "
            f"product files {len(plan['files'])} (per step {files})")


def past(plan):
    return plan["criteria"] > CRITERIA or len(plan["files"]) > FILES


def over(plan):
    """Steps over a number: by the files a step lists, and where the plan lists none, by the files its commit changed."""
    names = [step["id"] for step in plan["steps"] if step["criteria"] > CRITERIA or len(step["files"]) > FILES]
    for number, files in enumerate(plan.get("built") or (), 1):
        if files is not None and len(files) > FILES and f"built step {number}" not in names:
            names.append(f"built step {number} ({len(files)} product files)")
    return names


def main(folder):
    folder = pathlib.Path(folder)
    census = json.loads((folder / "census.json").read_text())
    steps = collections.defaultdict(list)
    iteration = json.loads((folder / "iteration.json").read_text())
    for step in iteration["steps"]:
        steps[pathlib.Path(step["run"]).parents[3].name].append(step)
    worktrees = {pathlib.Path(run["run"]).parents[3].name: run.get("worktree") for run in iteration["runs"]}
    shots = json.loads((folder / "snapshots.json").read_text()) if (folder / "snapshots.json").exists() else {}
    kept_at = folder / "plans.json"
    kept = json.loads(kept_at.read_text()) if kept_at.exists() else {}
    rows = []
    for run in census:
        name = slice_report.name_of(run)
        if name.startswith("rehearsal"):
            continue
        rundir = pathlib.Path(run["trace"]).parent
        mine = steps.get(name, [])
        if rundir.exists():
            plan = first_plan(rundir)
            if plan is not None and worktrees.get(name) and pathlib.Path(worktrees[name]).exists():
                plan["built"] = built_files(worktrees[name], mine)
            kept[run["folder"]] = plan
        seconds = run["seconds"]
        mark = shots.get(name) or {}
        last = (mark.get("steps") or [{}])[-1].get("implement") if mark.get("steps") else None
        rows.append({"name": name, "driver": f"{run['model']} {run['effort']}", "arm": arm_of(name), "plan": kept.get(run["folder"]),
                     "plan_only": "-plan-" in name, "done": slice_report.inner_loop_done(run),
                     "minutes": sum(seconds.values()) / 60, "seconds": seconds, "built": len(mine),
                     "refused": sum(s.get("test_refused") or 0 for s in mine),
                     "sent_back": sum(count for key, count in run["outcomes"].items() if key.endswith("|send-back")),
                     "after": sum((s.get("after_implement") or {}).get("code", 0) for s in mine),
                     "lines": sum((s.get("built") or {}).get("code", 0) for s in mine),
                     "first": last, "end": mark.get("end"), "marks": mark.get("steps") or []})
    kept_at.write_text(json.dumps(kept, indent=1, sort_keys=True) + "\n")
    rows.sort(key=lambda r: (r["driver"], r["arm"], r["name"]))

    print("== the plans ==")
    for row in rows:
        plan = row["plan"]
        print(f"{row['name']:<28}{row['driver']:<24}{row['arm']:<5}{shape(plan)}"
              + ("" if not plan else f"; past {CRITERIA} criteria or {FILES} product files: {'yes' if past(plan) else 'no'}"
                 + (f"; steps over a number: {', '.join(over(plan))}" if over(plan) else "")))
        for step in (plan or {}).get("steps", []):
            print(f"      {step['id']}: {', '.join(step['files']) or '(no paths listed)'} | {step['task']}")
        for number, files in enumerate((plan or {}).get("built") or (), 1):
            print(f"      built step {number}: " + ("(a tree is missing)" if files is None else f"{len(files)} product files: {', '.join(files)}"))

    full = [row for row in rows if not row["plan_only"]]
    print("\n== the slices ==")
    print(f"{'slice':<24}{'driver':<24}{'arm':<5}{'done':>5}{'min':>7}{'steps':>6}" + "".join(f"{label:>12}" for label, _ in slice_report.PARTS)
          + f"{'test refused':>13}{'send-backs':>11}{'product lines':>14}{'changed after':>14}{'first impl':>11}{'end':>6}")
    for row in full:
        def score(mark, skip=()):
            if not mark or not mark.get("observed"):
                return "-"
            total = 8 - len(skip)
            return f"{len([c for c in mark['passed'] if c not in skip])}/{total}"
        print(f"{row['name']:<24}{row['driver']:<24}{row['arm']:<5}{'yes' if row['done'] else 'NO':>5}{row['minutes']:>7.1f}{row['built']:>6}"
              + "".join(f"{sum(row['seconds'].get(k, 0) for k in keys):>12.0f}" for _, keys in slice_report.PARTS)
              + f"{row['refused']:>13}{row['sent_back']:>11}{row['lines']:>14}{row['after']:>14}"
              + f"{score(row['first'], NOT_AT_IMPLEMENT):>11}{score(row['end']):>6}")
    print("(seconds per part; steps: implement actions accepted; first impl: the last step's implement snapshot on the seven "
          "checks other than suite; end: the eight checks on the slice's final working copy)")
    for row in full:
        for label, mark in [("first implementation", row["first"]), ("end", row["end"])]:
            failed = {k: v for k, v in ((mark or {}).get("failed") or {}).items() if not (label.startswith("first") and k in NOT_AT_IMPLEMENT)}
            if failed:
                print(f"  {row['name']} fails at its {label}: " + "; ".join(f"{k} ({(v or '')[:150]})" for k, v in failed.items()))
        repaired = []
        marks = row["marks"]
        if marks and row["first"] and row["first"].get("observed"):
            failing = set(row["first"].get("failed") or ()) - set(NOT_AT_IMPLEMENT)
            for point in ("test", "before_review", "commit"):
                mark = marks[-1].get(point)
                if mark and mark.get("observed"):
                    fixed = failing - set(mark.get("failed") or ())
                    repaired += [f"{check} passes from the last step's {point} snapshot" for check in sorted(fixed)]
                    failing -= fixed
            if row["end"] and row["end"].get("observed"):
                fixed = failing - set(row["end"].get("failed") or ())
                repaired += [f"{check} passes only at the end (after the step commit)" for check in sorted(fixed)]
        if repaired:
            print(f"  {row['name']}: " + "; ".join(repaired))

    print("\n== the registered readings, by driver ==")
    cells = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in full:
        cells[row["driver"]][row["arm"]].append(row)
    for driver, arms in sorted(cells.items()):
        f1, plain = arms["F1"], arms["base"]
        if not f1 or not plain:
            continue
        print(f"{driver}")
        for row in f1:
            plan = row["plan"]
            if not plan:
                continue
            if not past(plan):
                verdict = "inside the numbers, one step: the cut is not exercised" if len(plan["steps"]) == 1 else "inside the numbers and cut anyway"
            else:
                verdict = ("past the numbers and cut, no step over a number" if len(plan["steps"]) > 1 and not over(plan)
                           else "past the numbers and cut, a step over a number" if len(plan["steps"]) > 1
                           else "PAST THE NUMBERS AND NOT CUT")
            print(f"  cut: {row['name']}: {shape(plan)}: {verdict}")
        mean_plain = statistics.mean(r["minutes"] for r in plain)
        mean_f1 = statistics.mean(r["minutes"] for r in f1)
        change = mean_f1 / mean_plain - 1
        print(f"  time: baseline {', '.join(f'{r["minutes"]:.1f}' for r in plain)} min (mean {mean_plain:.1f}); F1 "
              f"{', '.join(f'{r["minutes"]:.1f}' for r in f1)} min (mean {mean_f1:.1f}); change {change:+.1%}: "
              f"{'F1 saves time' if change <= -0.15 else 'F1 is slower' if change >= 0.15 else 'no readable difference'}")
        ends = lambda group: [len(r["end"]["passed"]) if r["end"] and r["end"].get("observed") else None for r in group]
        least = min((e for e in ends(plain) if e is not None), default=None)
        lost = least is None or any(e is None or e < least for e in ends(f1))
        print(f"  quality at the end (of 8): baseline {ends(plain)}, F1 {ends(f1)}: {'LOSS' if lost else 'no loss seen'}")
        def seven(row):
            mark = row["first"]
            return None if not mark or not mark.get("observed") else {c for c in mark["passed"] if c not in NOT_AT_IMPLEMENT}
        firsts = [seven(r) for r in plain]
        common = set.intersection(*[f for f in firsts if f is not None]) if any(f is not None for f in firsts) and all(f is not None for f in firsts) else set()
        shows = [r["name"] for r in f1 if seven(r) is not None and common - seven(r)]
        print(f"  first implementation (of 7): baseline {[None if f is None else len(f) for f in firsts]}, F1 "
              f"{[None if seven(r) is None else len(seven(r)) for r in f1]}: the named risk {'SHOWS in ' + ', '.join(shows) if shows else 'does not show'}")
        print(f"  steps planned: baseline {[len(r['plan']['steps']) if r['plan'] else None for r in plain]}, F1 "
              f"{[len(r['plan']['steps']) if r['plan'] else None for r in f1]}; steps built: baseline {[r['built'] for r in plain]}, F1 "
              f"{[r['built'] for r in f1]}; test refusals: baseline {[r['refused'] for r in plain]}, F1 {[r['refused'] for r in f1]}; "
              f"send-backs: baseline {[r['sent_back'] for r in plain]}, F1 {[r['sent_back'] for r in f1]}")


if __name__ == "__main__":
    main(sys.argv[1])
