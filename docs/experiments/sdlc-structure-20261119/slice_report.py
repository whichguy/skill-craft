#!/usr/bin/env python3
"""Round 4's registered measures, one row per inner-loop slice, and the arm comparison.

Reads three files made from the slices' folder:
  CENSUS.json     stage_census.py OUT ROOT          (seconds per stage, refusals, accepted outcomes)
  ITERATION.json  iteration_census.py ... --all     (per step: own test runs, loop iterations, product lines changed)
  SNAPSHOTS.json  slice_snapshots.py                (hidden checks passed at each snapshot)

A slice whose folder name holds "-L0-" is the arm with the stage Until Loop switched off. A hidden check that fails
at the end of every tickets-assign slice is listed and left out of the score (the registered rule for a check tied
to the part of the larger request the one-step case leaves out).

Usage: python3 -I slice_report.py CENSUS.json ITERATION.json SNAPSHOTS.json
"""
import collections
import json
import pathlib
import statistics
import sys

PARTS = (("step-plan", ("step-plan",)), ("its review", ("improve:step-plan",)), ("test-spec", ("test-spec", "validate-existing")),
         ("implement", ("implement",)), ("test", ("test",)), ("document", ("document",)),
         ("step review", ("improve:document",)), ("carry-fwd", ("carry-forward", "improve:carry-forward")))


def name_of(run):
    return pathlib.Path(run["folder"]).name


def inner_loop_done(run):
    """The harness's own verdict (slice-result.json, `inner_loop`); the trace's accepted carry-forward where it is absent."""
    try:
        verdict = json.loads((pathlib.Path(run["folder"]) / "slice-result.json").read_text())["verdicts"]["inner_loop"]
        return bool(verdict.get("pass") if isinstance(verdict, dict) else verdict)
    except (OSError, ValueError, KeyError):
        return run["outcomes"].get("carry-forward|done", 0) > 0


def main(census, iteration, snapshots):
    runs = {name_of(r): r for r in json.loads(pathlib.Path(census).read_text())}
    data = json.loads(pathlib.Path(iteration).read_text())
    shots = json.loads(pathlib.Path(snapshots).read_text())
    steps = collections.defaultdict(list)
    for step in data["steps"]:
        steps[pathlib.Path(step["run"]).parents[3].name].append(step)
    loops = {pathlib.Path(r["run"]).parents[3].name: r["loops"] for r in data["runs"]}
    names = sorted(n for n in runs if not n.startswith("rehearsal"))
    everywhere = None
    for name in names:
        if runs[name].get("case") == "tickets-assign" and name in shots:
            failed = set(shots[name]["end"].get("failed") or {})
            everywhere = failed if everywhere is None else everywhere & failed
    everywhere = everywhere or set()
    print(f"hidden tickets-assign checks failing at the end of every slice, left out of the score: {sorted(everywhere) or 'none'}")

    def score(name, mark):
        if not mark or not mark.get("observed"):
            return None
        total = 6 if runs[name]["case"] == "shared-expenses-w1" else 14 - len(everywhere)
        return len([c for c in mark["passed"] if c not in everywhere]), total

    def show(pair):
        return "-" if pair is None else f"{pair[0]}/{pair[1]}"

    print(f"\n{'slice':<30}{'driver':<22}{'done':>5}{'min':>6}{'steps':>6}" + "".join(f"{label:>12}" for label, _ in PARTS)
          + f"{'refused':>9}{'loops>1':>8}{'red runs':>9}{'code after':>11}{'hidden: first':>14}{'end':>7}")
    rows = []
    for name in names:
        run = runs[name]
        seconds = run["seconds"]
        done = inner_loop_done(run)
        mine = steps.get(name, [])
        last = (shots.get(name) or {}).get("steps") or []
        first = score(name, last[-1].get("implement")) if last else None
        end = score(name, (shots.get(name) or {}).get("end"))
        refused = sum(run["refusals"].values())
        repeated = sum(1 for _, number in loops.get(name, []) if number and number > 1)
        red = sum((s.get("test") or {}).get("test_fails", 0) for s in mine)
        after = sum((s.get("after_implement") or {}).get("code", 0) for s in mine)
        row = {"name": name, "case": run["case"], "driver": f"{run['model']} {run['effort']}", "arm": "L0" if "-L0-" in name else "base",
               "seconds": seconds,
               "done": done, "minutes": sum(seconds.values()) / 60, "first": first, "end": end, "refused": refused,
               "review": sum(v for k, v in seconds.items() if k.startswith("improve:")), "total": sum(seconds.values())}
        rows.append(row)
        print(f"{name:<30}{row['driver']:<22}{'yes' if done else 'NO':>5}{row['minutes']:>6.1f}{len(mine):>6}"
              + "".join(f"{sum(seconds.get(k, 0) for k in keys):>12.0f}" for _, keys in PARTS)
              + f"{refused:>9}{repeated:>8}{red:>9}{after:>11}{show(first):>14}{show(end):>7}")
    print("(seconds per part; refused: check, complete and review-pass commands ShipLoop refused; loops>1: stage Until Loops that "
          "took a second iteration; red runs: the model's own failing test runs inside test; code after: product-code lines "
          "changed after implement was accepted; hidden first: the last step's implement snapshot)")

    print("\n== by driver, baseline slices ==")
    groups = collections.defaultdict(list)
    for row in rows:
        if row["arm"] == "base":
            groups[row["driver"]].append(row)
    for driver, group in sorted(groups.items()):
        firsts = [r["first"] for r in group if r["first"]]
        ends = [r["end"] for r in group if r["end"]]
        print(f"  {driver:<22}{len(group)} slices; minutes {', '.join(f'{r["minutes"]:.1f}' for r in group)}; reviews "
              f"{sum(r['review'] for r in group) / sum(r['total'] for r in group):.0%} of slice time; first implementation "
              f"passes every hidden check in {sum(a == b for a, b in firsts)} of {len(firsts)}; end of slice in "
              f"{sum(a == b for a, b in ends)} of {len(ends)}")

    print("\n== share of slice time by part, baseline slices ==")
    for driver, group in sorted(groups.items()):
        total = sum(r["total"] for r in group)
        early = sum(r["seconds"].get(k, 0) for r in group for k in ("step-plan", "improve:step-plan", "test-spec", "validate-existing"))
        print(f"  {driver:<22}" + "; ".join(f"{label} {sum(r['seconds'].get(k, 0) for r in group for k in keys) / total:.0%}"
                                           for label, keys in PARTS) + f" | before the first product edit {early / total:.0%}")

    print("\n== arm L0 (stage Until Loop off) against the baseline, same driver and case ==")
    cells = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in rows:
        cells[(row["driver"], row["case"])][row["arm"]].append(row)
    for (driver, case), arms in sorted(cells.items()):
        if not arms["L0"] or not arms["base"]:
            continue
        base, off = arms["base"], arms["L0"]
        mean_base = statistics.mean(r["minutes"] for r in base)
        mean_off = statistics.mean(r["minutes"] for r in off)
        least = min((r["end"][0] for r in base if r["end"]), default=None)
        kept = all(r["end"] and least is not None and r["end"][0] >= least for r in off)
        print(f"  {driver:<22}{case:<20} baseline {', '.join(f'{r["minutes"]:.1f}' for r in base)} min (mean {mean_base:.1f}); "
              f"L0 {', '.join(f'{r["minutes"]:.1f}' for r in off)} min (mean {mean_off:.1f}); change {mean_off / mean_base - 1:+.0%}; "
              f"L0 completes {sum(r['done'] for r in off)} of {len(off)}; hidden checks at the end: baseline "
              f"{', '.join(str(r['end'][0]) if r['end'] else '?' for r in base)}, L0 "
              f"{', '.join(str(r['end'][0]) if r['end'] else '?' for r in off)} ({'no loss seen' if kept else 'LOSS'}); refused: "
              f"baseline {', '.join(str(r['refused']) for r in base)}, L0 {', '.join(str(r['refused']) for r in off)}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
