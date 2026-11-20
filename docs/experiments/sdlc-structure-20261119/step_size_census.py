#!/usr/bin/env python3
"""What sets the number of build steps in an item, and what does one more step cost?

Reads iteration_census.py's output (ITERATION.json: every build step with its seconds by part, the product lines it
built, its refusals and what the review changed) and, from each run folder, the item's accepted step plan (its
criteria, and each step's criteria and paths).

It prints:
  1. the shape of the step plans: steps per item, criteria per item and per step, product files per step, and how
     many items are planned at the fewest steps the template's bound of 4 criteria a step allows;
  2. what a step costs by its size (product-code lines built at `implement`): seconds of implement, test, document
     and the step review, the share refused at `test`, the share whose review changed product code, and a straight
     line of the seconds after `implement` on the lines built (its intercept is the cost a step pays whatever its
     size);
  3. the same request cut into more or fewer steps: within one case, model and effort, the build seconds and the
     product lines of a run against its number of steps (a pooled within-cell slope);
     and the plan stages' seconds (step-plan, its review, test-spec) the same way;
  4. the delivered product's hidden checks (the E2E result's held-out acceptance) by the run's step count.

Usage: python3 -I step_size_census.py ITERATION.json [CENSUS.json]
"""
import collections
import json
import math
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import iteration_census as base

item_scope = base.item_scope
BOUND = 4
BANDS = ((1, 25), (26, 75), (76, 200), (201, 10**9))
PARTS = ("implement_s", "test_s", "document_s", "review_s")


def plans_of(rundir):
    """The latest accepted done step plan of each work item."""
    found = {}
    for path in sorted((rundir / "results").glob("nav-*.md"), key=lambda p: p.stat().st_mtime):
        record = base.state(path) or {}
        result = record.get("result")
        if record.get("stage") == "step-plan" and isinstance(result, dict) and result.get("outcome") == "done":
            found[record.get("workitem")] = result
    return found


def product(paths):
    return [path for path in paths or () if item_scope.classify(path) == "code"]


def median(values, digits=0):
    values = [v for v in values if v is not None]
    return "-" if not values else f"{statistics.median(values):.{digits}f}"


def rate(events, total):
    return f"{events} of {total} ({events / total:.0%})" if total else "0 of 0"


def spread(values):
    counts = collections.Counter(values)
    return ", ".join(f"{key}: {counts[key]}" for key in sorted(counts))


def within(cells, x, y):
    """Pooled within-cell slope of y on x, the cells that vary in x, and the rows in them."""
    top = bottom = 0.0
    used = rows = 0
    for group in cells.values():
        pairs = [(row[x], row[y]) for row in group if row.get(x) is not None and row.get(y) is not None]
        if len({a for a, _ in pairs}) < 2:
            continue
        mean_x = statistics.mean(a for a, _ in pairs)
        mean_y = statistics.mean(b for _, b in pairs)
        top += sum((a - mean_x) * (b - mean_y) for a, b in pairs)
        bottom += sum((a - mean_x) ** 2 for a, _ in pairs)
        used += 1
        rows += len(pairs)
    return (top / bottom if bottom else None), used, rows


def acceptance(run):
    """(checks passed, checks) of the delivered product, from the E2E result that holds this run; None if ungraded."""
    for parent in pathlib.Path(run).parents:
        result = parent / "result.json"
        if result.exists():
            try:
                block = (json.loads(result.read_text()).get("quality") or {}).get("acceptance") or {}
            except (OSError, ValueError):
                return None
            if block.get("observed") and block.get("ids"):
                return len(block.get("passed") or ()), len(block["ids"])
            return None
    return None


def main(argv):
    data = json.loads(pathlib.Path(argv[0]).read_text())
    census = {row["trace"]: row for row in json.loads(pathlib.Path(argv[1]).read_text())} if len(argv) > 1 else {}
    by_item = collections.defaultdict(list)
    for step in data["steps"]:
        by_item[(step["run"], step["item"])].append(step)
    plans = {}
    for run in {run for run, _ in by_item}:
        plans[run] = plans_of(pathlib.Path(run).parent)

    print(f"build steps read: {len(data['steps'])} in {len(by_item)} items of {len(plans)} runs")
    print("\n== 1. the step plans ==")
    shapes, per_step, files_per_step, matched = [], [], [], 0
    for (run, item), steps in by_item.items():
        plan = plans[run].get(item)
        if not plan:
            continue
        rows = [row for row in plan.get("steps") or () if isinstance(row, dict)]
        criteria = len(plan.get("criteria") or ())
        shapes.append({"steps": len(rows), "criteria": criteria, "fewest": max(1, math.ceil(criteria / BOUND)),
                       "files": len(product(plan.get("paths")))})
        for row in rows:
            per_step.append(len(row.get("criteria") or ()))
            if row.get("paths"):
                files_per_step.append(len(product(row["paths"])))
        if len(rows) == len(steps):
            matched += 1
            for row, step in zip(rows, steps):
                step["criteria_n"] = len(row.get("criteria") or ())
    print(f"items with an accepted step plan: {len(shapes)}; steps planned per item: {spread(s['steps'] for s in shapes)}")
    print(f"criteria per item: median {median(s['criteria'] for s in shapes)}, by count: {spread(s['criteria'] for s in shapes)}")
    print(f"criteria per planned step: {spread(per_step)}; steps over the bound of {BOUND}: {rate(sum(c > BOUND for c in per_step), len(per_step))}")
    print(f"product files per planned step (steps that list paths): {spread(files_per_step)}; over 3: "
          f"{rate(sum(f > 3 for f in files_per_step), len(files_per_step))}")
    multi = [s for s in shapes if s["steps"] > 1]
    print(f"items of two or more steps: {rate(len(multi), len(shapes))}; of them the bound alone requires two or more (over "
          f"{BOUND} criteria) in {rate(sum(s['fewest'] > 1 for s in multi), len(multi))}")
    print(f"items planned at the fewest steps the bound allows: {rate(sum(s['steps'] == s['fewest'] for s in shapes), len(shapes))}; "
          f"above it: {rate(sum(s['steps'] > s['fewest'] for s in shapes), len(shapes))}; below it (a step over the bound): "
          f"{rate(sum(s['steps'] < s['fewest'] for s in shapes), len(shapes))}")
    small = [s for s in shapes if s["criteria"] <= 12 and s["files"] <= 6]
    print(f"items of at most 12 criteria and 6 product files: {rate(len(small), len(shapes))}; their steps: {spread(s['steps'] for s in small)}")
    print(f"items whose plan and recorded steps agree in number (used for criteria per step below): {rate(matched, len(shapes))}")

    print("\n== 2. what a step costs, by the product-code lines its implement built ==")
    sized = [s for s in data["steps"] if isinstance(s.get("built"), dict) and "test_s" in s]
    print(f"steps with a test stage and a measured implement diff: {len(sized)}")
    print(f"{'code lines':<12}{'steps':>6}{'criteria':>9}{'implement':>10}{'test':>7}{'document':>9}{'review':>8}{'after impl':>11}"
          f"{'test refused':>14}{'review changed code':>21}")
    for low, high in BANDS:
        group = [s for s in sized if low <= s["built"].get("code", 0) <= high]
        if not group:
            continue
        after = [s.get("test_s", 0) + s.get("document_s", 0) + (s.get("review_s") or 0) for s in group]
        reviewed = [s for s in group if isinstance(s.get("in_review"), dict)]
        label = f"{low}-{high}" if high < 10**9 else f"{low}+"
        print(f"{label:<12}{len(group):>6}{median(s.get('criteria_n') for s in group):>9}{median(s['implement_s'] for s in group):>10}"
              f"{median(s.get('test_s') for s in group):>7}{median(s.get('document_s') for s in group):>9}"
              f"{median(s.get('review_s') for s in group):>8}{median(after):>11}"
              f"{rate(sum(bool(s.get('test_refused')) for s in group), len(group)):>14}"
              f"{rate(sum(s['in_review'].get('code', 0) > 0 for s in reviewed), len(reviewed)):>21}")
    none = [s for s in sized if not s["built"].get("code")]
    print(f"(seconds are medians; {len(none)} steps built no product-code line and are left out)")
    cells = collections.defaultdict(list)
    for s in sized:
        if s["built"].get("code"):
            cells[(s.get("case"), s.get("model"), s.get("effort"))].append(
                {"lines": s["built"]["code"], "implement": s["implement_s"],
                 "after": s.get("test_s", 0) + s.get("document_s", 0) + (s.get("review_s") or 0)})
    for label, key in (("implement", "implement"), ("test, document and the step review", "after")):
        slope, used, rows = within(cells, "lines", key)
        pooled = [row for group in cells.values() for row in group]
        if slope is None:
            continue
        intercept = statistics.mean(r[key] for r in pooled) - slope * statistics.mean(r["lines"] for r in pooled)
        print(f"  {label}: {slope * 100:+.0f} seconds per 100 product-code lines within case and model ({rows} steps in {used} "
              f"cells); at the mean step ({statistics.mean(r['lines'] for r in pooled):.0f} lines, "
              f"{statistics.mean(r[key] for r in pooled):.0f} s) that leaves {intercept:.0f} seconds that do not depend on its size")

    print("\n== 3. the same request in more or fewer steps (runs of one case, model and effort) ==")
    by_run = collections.defaultdict(list)
    for step in data["steps"]:
        by_run[step["run"]].append(step)
    runs = collections.defaultdict(list)
    for run, steps in by_run.items():
        if not all("test_s" in s for s in steps):
            continue
        first = steps[0]
        row = {"steps": len(steps), "build": sum(sum(s.get(p) or 0 for p in PARTS) for s in steps),
               "lines": sum((s.get("built") or {}).get("code", 0) for s in steps),
               "refused": sum(s.get("test_refused") or 0 for s in steps)}
        totals = census.get(run)
        if totals:
            seconds = totals["seconds"]
            row["plan"] = sum(seconds.get(k, 0) for k in ("step-plan", "improve:step-plan", "test-spec", "validate-existing"))
            row["inner"] = row["plan"] + sum(seconds.get(k, 0) for k in ("implement", "test", "document", "improve:document",
                                                                      "carry-forward", "improve:carry-forward"))
        row["hidden"] = acceptance(run)
        runs[(first.get("case"), first.get("model"), first.get("effort"))].append(row)
    varied = {cell: group for cell, group in runs.items() if len({r["steps"] for r in group}) > 1}
    print(f"cells: {len(runs)}; with runs that differ in step count: {len(varied)} ({sum(len(g) for g in varied.values())} runs)")
    for label, key, unit in (("build seconds (implement, test, document, step review)", "build", "seconds"),
                             ("product-code lines built", "lines", "lines"), ("`test` refusals", "refused", "refusals"),
                             ("plan-stage seconds (step-plan, its review, test-spec, validate-existing)", "plan", "seconds"),
                             ("inner-loop seconds, plan stages to carry-forward", "inner", "seconds")):
        slope, used, rows = within(runs, "steps", key)
        if slope is not None:
            print(f"  one more step goes with {slope:+.1f} {unit} of {label} ({rows} runs in {used} cells)")
    print("  the cells with the most runs:")
    for cell, group in sorted(varied.items(), key=lambda kv: -len(kv[1]))[:8]:
        by_count = collections.defaultdict(list)
        for row in group:
            by_count[row["steps"]].append(row)
        print(f"    {cell[0]} | {cell[1]} {cell[2]}: " + "; ".join(
            f"{count} steps: {len(rows)} runs, build {median(r['build'] for r in rows)} s, {median(r['lines'] for r in rows)} lines"
            for count, rows in sorted(by_count.items())))

    print("\n== 4. hidden checks of the delivered product, by the run's step count ==")
    graded = [(cell, row) for cell, group in runs.items() for row in group if row["hidden"]]
    for label, keep in (("one step", lambda n: n == 1), ("two or more steps", lambda n: n > 1)):
        group = [row for _, row in graded if keep(row["steps"])]
        print(f"  {label}: runs passing every hidden check {rate(sum(r['hidden'][0] == r['hidden'][1] for r in group), len(group))}; "
              f"checks passed {rate(sum(r['hidden'][0] for r in group), sum(r['hidden'][1] for r in group))}")
    both = collections.defaultdict(lambda: collections.defaultdict(list))
    for cell, row in graded:
        both[cell]["one" if row["steps"] == 1 else "more"].append(row)
    for cell, shapes in sorted(both.items(), key=lambda kv: str(kv[0])):
        if shapes["one"] and shapes["more"]:
            print(f"    {cell[0]} | {cell[1]} {cell[2]}: " + "; ".join(
                f"{name}: {sum(r['hidden'][0] == r['hidden'][1] for r in rows)} of {len(rows)} runs pass every check, build "
                f"{median(r['build'] for r in rows)} s" for name, rows in (("one step", shapes["one"]), ("more", shapes["more"]))))


if __name__ == "__main__":
    main(sys.argv[1:])
