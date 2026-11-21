#!/usr/bin/env python3
"""Every recorded Improve review on one model, from its own pass log: what it cost and whether it changed anything (round 8).

For each ShipLoop run directory under the given roots whose model is MODEL this reads each review's pass log
(``run/improve/<reviewed action>/passes.md``: one row a pass with `tree changed`, `result changed`, `lines`,
`seconds`) and the stage of the action it reviewed (``run/results/<action>.md``). It prints

  1. the runs read: kind (a whole delivery or a seeded slice), case, ShipLoop version, last status, reviews;
  2. every review: run, reviewed stage, passes, seconds, whether a pass changed the tree or the result, lines;
  3. per reviewed stage: reviews, how many changed anything, minutes in all and a review, passes a review.

A review that changes something is not a defect caught: this bounds what dropping the review could lose.

Usage: python3 -I grok_review_scan.py MODEL ROOT [ROOT ...]
"""
import collections
import glob
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import iteration_census as base
import review_option_census as option
import review_yield_drivers as yields

ORDER = ("spec", "test-strategy", "plan", "step-plan", "test-spec", "implement", "document", "carry-forward",
         "system-test-author", "release-plan")


def main(model, roots):
    runs, rows = [], []
    for root in roots:
        for path in sorted(glob.glob(str(pathlib.Path(root) / "**" / ".shiploop-runs" / "*" / "run"), recursive=True)):
            run = pathlib.Path(path)
            folder = option.holder(run)
            if folder is None or folder.name.startswith("rehearsal"):
                continue
            invocation = option.load(folder / "invocation.json")
            if invocation.get("model") != model:
                continue
            record = option.read_run(run) or {}
            whole = invocation.get("kind") != "step-slice" and not invocation.get("seeded")
            versions = invocation.get("versions") or {}
            reviews = 0
            for log in sorted((run / "improve").glob("*/passes.md"), key=lambda p: p.stat().st_mtime):
                stage = (base.state(run / "results" / f"{log.parent.name}.md") or {}).get("stage")
                table = yields.passes(log)
                if not stage or not table:
                    continue

                def number(row, key):
                    return int(row[key]) if row.get(key, "").isdigit() else 0

                reviews += 1
                rows.append({"run": folder.name, "whole": whole, "stage": stage, "passes": len(table),
                             "seconds": sum(number(row, "seconds") for row in table),
                             "tree": any(row.get("tree changed") == "y" for row in table),
                             "result": any(row.get("result changed") == "y" for row in table),
                             "lines": sum(number(row, "lines") for row in table)})
            runs.append((folder.name, "whole delivery" if whole else "slice", invocation.get("case"),
                         versions.get("shiploop_version") or "checkout", record.get("status"), reviews))
    print(f"== 1. runs on {model} with at least one review ==")
    for name, kind, case, version, status, reviews in runs:
        if reviews:
            print(f"  {name:<28}{kind:<16}{case!s:<20}ShipLoop {version!s:<10}last status {status!s:<8}reviews {reviews}")
    print("\n== 2. every review ==")
    print(f"  {'run':<28}{'reviewed stage':<20}{'passes':>7}{'seconds':>9}{'tree':>6}{'result':>8}{'lines':>7}")
    for row in rows:
        print(f"  {row['run']:<28}{row['stage']:<20}{row['passes']:>7}{row['seconds']:>9}{'y' if row['tree'] else 'n':>6}"
              f"{'y' if row['result'] else 'n':>8}{row['lines']:>7}")
    for label, keep in (("whole deliveries", True), ("slices", False)):
        group = [row for row in rows if row["whole"] is keep]
        if not group:
            continue
        cells = collections.defaultdict(list)
        for row in group:
            cells[row["stage"]].append(row)
        print(f"\n== 3. by reviewed stage, {label} ({len({row['run'] for row in group})} runs, {len(group)} reviews) ==")
        print(f"  {'reviewed stage':<20}{'reviews':>8}{'changed anything':>18}{'tree':>6}{'result':>8}{'minutes in all':>16}"
              f"{'minutes a review, median':>26}{'passes a review, median':>25}")
        stages = [stage for stage in ORDER if stage in cells] + sorted(set(cells) - set(ORDER))
        for stage in stages:
            cell = cells[stage]
            changed = sum(row["tree"] or row["result"] for row in cell)
            print(f"  {stage:<20}{len(cell):>8}{f'{changed} ({changed / len(cell):.0%})':>18}{sum(row['tree'] for row in cell):>6}"
                  f"{sum(row['result'] for row in cell):>8}{sum(row['seconds'] for row in cell) / 60:>16.0f}"
                  f"{statistics.median(row['seconds'] for row in cell) / 60:>26.1f}{statistics.median(row['passes'] for row in cell):>25.0f}")
        changed = sum(row["tree"] or row["result"] for row in group)
        print(f"  {'all':<20}{len(group):>8}{f'{changed} ({changed / len(group):.0%})':>18}{sum(row['tree'] for row in group):>6}"
              f"{sum(row['result'] for row in group):>8}{sum(row['seconds'] for row in group) / 60:>16.0f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
