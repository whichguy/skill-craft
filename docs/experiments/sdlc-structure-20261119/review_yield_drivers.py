#!/usr/bin/env python3
"""What each Improve review changed, by driver and by the stage it reviewed (round 7).

For every ShipLoop run directory under the given roots this reads each review's own pass log
(``run/improve/<reviewed action>/passes.md``: one row per pass with `tree changed`, `result changed`, `lines` and
`seconds`) and the stage of the action it reviewed (``run/results/<action>.md``), and prints per driver and reviewed
stage: how many reviews ran, how many edited anything (the tree or the result), the lines they changed and the
seconds they took. A review that edits is not a defect caught: it bounds what dropping the review could lose.

A run folder whose name starts with "rehearsal" is left out. `--slices-only` or `--whole-only` keeps one kind.

Usage: python3 -I review_yield_drivers.py ROOT [ROOT ...] [--slices-only | --whole-only]
"""
import collections
import glob
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import iteration_census as base
import review_option_census as option

ORDER = ("spec", "test-strategy", "plan", "step-plan", "document", "carry-forward", "system-test-author", "release-plan")


def passes(path):
    """Rows of a passes.md table as dicts."""
    lines = [line for line in path.read_text(errors="replace").splitlines() if line.startswith("|")]
    if len(lines) < 3:
        return []
    head = [cell.strip() for cell in lines[0].strip("|").split("|")]
    return [dict(zip(head, (cell.strip() for cell in line.strip("|").split("|")))) for line in lines[2:]]


def main(argv):
    roots = [a for a in argv if not a.startswith("--")]
    rows = []
    for root in roots:
        for path in sorted(glob.glob(str(pathlib.Path(root) / "**" / ".shiploop-runs" / "*" / "run"), recursive=True)):
            run = pathlib.Path(path)
            folder = option.holder(run)
            if folder is None or folder.name.startswith("rehearsal"):
                continue
            invocation = option.load(folder / "invocation.json")
            whole = invocation.get("kind") != "step-slice" and not invocation.get("seeded")
            if ("--slices-only" in argv and whole) or ("--whole-only" in argv and not whole):
                continue
            driver = f"{invocation.get('model')} {invocation.get('effort') or '-'}"
            for log in sorted((run / "improve").glob("*/passes.md")):
                stage = (base.state(run / "results" / f"{log.parent.name}.md") or {}).get("stage")
                table = passes(log)
                if not stage or not table:
                    continue
                def number(row, key):
                    return int(row[key]) if row.get(key, "").isdigit() else 0
                rows.append({"driver": driver, "stage": stage, "folder": folder.name, "whole": whole,
                             "edited": any(row.get("edited") == "y" for row in table),
                             "tree": any(row.get("tree changed") == "y" for row in table),
                             "result": any(row.get("result changed") == "y" for row in table),
                             "lines": sum(number(row, "lines") for row in table),
                             "seconds": sum(number(row, "seconds") for row in table), "passes": len(table)})
    print(f"reviews read: {len(rows)} in {len({r['folder'] for r in rows})} runs "
          f"({len({r['folder'] for r in rows if r['whole']})} whole deliveries, {len({r['folder'] for r in rows if not r['whole']})} slices)")
    cells = collections.defaultdict(list)
    for row in rows:
        cells[(row["driver"], row["stage"])].append(row)
    print(f"\n{'driver':<26}{'reviewed stage':<20}{'reviews':>8}{'edited':>12}{'tree':>6}{'result':>8}{'lines, median of edits':>24}"
          f"{'seconds, median':>17}{'passes, median':>16}")
    for driver in sorted({d for d, _ in cells}):
        for stage in ORDER:
            group = cells.get((driver, stage))
            if not group:
                continue
            edits = [r["lines"] for r in group if r["edited"]]
            print(f"{driver:<26}{stage:<20}{len(group):>8}{f'{sum(r["edited"] for r in group)} ({sum(r["edited"] for r in group) / len(group):.0%})':>12}"
                  f"{sum(r['tree'] for r in group):>6}{sum(r['result'] for r in group):>8}"
                  f"{(f'{statistics.median(edits):.0f}' if edits else '-'):>24}{statistics.median(r['seconds'] for r in group):>17.0f}"
                  f"{statistics.median(r['passes'] for r in group):>16.0f}")


if __name__ == "__main__":
    main(sys.argv[1:])
