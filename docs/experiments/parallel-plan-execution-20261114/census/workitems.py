#!/usr/bin/env python3
"""workitems.py (journal E16, descriptive): how often does a recorded run have more than one work item, and do those items touch disjoint files?

ShipLoop splits a request into work items (roughly features); the queue runs them one after another. This is the level above the steps of E0:
if independent features are where concurrent execution is useful, how many recorded runs have two or more items at all?
Offline and read-only, over evidence/census.json (one row per step plan, hence per work item and re-plan). An item's paths are the union of
its steps' declared `paths`; two items overlap by gated.py's rule. A side with no recorded paths is counted apart.

  python3 -I workitems.py        prints the counts and writes evidence/workitems.txt
"""

from __future__ import annotations

import collections
import itertools
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gated  # noqa: E402


def main() -> int:
    rows = json.load(open(HERE / "evidence" / "census.json"))["plans"]
    by_run = collections.defaultdict(dict)        # run -> work item -> (paths, seconds, steps)
    for r in rows:
        run, item = r.get("run"), r.get("workitem")
        if not run or not item:
            continue
        paths = sorted({p for step in (r.get("paths") or []) for p in (step or [])})
        seconds = r.get("T_s")
        previous = by_run[run].get(item)
        if previous is None or (seconds and not previous[1]):
            by_run[run][item] = (paths, seconds, r.get("n"))
    lines = []
    emit = lambda text="": (print(text), lines.append(text))
    sizes = collections.Counter(len(v) for v in by_run.values())
    multi = {run: items for run, items in by_run.items() if len(items) >= 2}
    emit(f"runs with plans: {len(by_run)}; work items per run: {dict(sorted(sizes.items()))}")
    emit(f"runs with two or more work items: {len(multi)} ({len(multi) / len(by_run):.1%})")
    pairs = disjoint = overlap = nopaths = timed_pairs = 0
    shorter = 0.0
    for items in multi.values():
        for a, b in itertools.combinations(sorted(items), 2):
            (pa, ta, _), (pb, tb, _) = items[a], items[b]
            pairs += 1
            if not pa or not pb:
                nopaths += 1
            elif gated.overlap(pa, pb):
                overlap += 1
            else:
                disjoint += 1
                if ta and tb:
                    timed_pairs += 1
                    shorter += min(ta, tb)
    emit(f"item pairs in those runs: {pairs}; overlapping declared paths {overlap}; disjoint {disjoint}; a side with no recorded paths {nopaths}")
    emit(f"disjoint pairs with both items timed: {timed_pairs}; the shorter item's seconds summed (the most that overlapping the pair could save): {shorter:,.0f} s")
    total = sum((v[1] or 0) for items in by_run.values() for v in items.values())
    in_multi = sum((v[1] or 0) for items in multi.values() for v in items.values())
    emit(f"timed seconds in all runs {total:,.0f}; in runs with two or more items {in_multi:,.0f} ({in_multi / total:.1%})")
    family = {r["run"]: r["family"] for r in rows}
    families = collections.Counter(family.get(run) for run in multi)
    emit(f"runs with two or more items by request family: {families.most_common(6)} (of {len(families)} families)")
    (HERE / "evidence" / "workitems.txt").write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
