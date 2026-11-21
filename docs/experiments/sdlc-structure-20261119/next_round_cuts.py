#!/usr/bin/env python3
"""Quick cuts read after round 7 to choose the next round (exploratory, not registered).

ROUND.json is round 7's run list (runs-reviews/census.json); ALL.json is review_option_census.py's list of every
recorded run. Both give seconds by stage per run, a review charged to the stage it reviews; `down` (the time no
host ran) is taken out where a list has it.

  A  this round's whole deliveries, by driver and case: mean seconds by stage, and the seconds between each refused
     `check` or `complete` command and the next command, by stage, with the most common refusal texts;
  B  the criteria each work item's accepted step plan held, by run;
  C  the recorded Grok whole deliveries: active minutes by part and by reviewed stage.

Usage: python3 -I next_round_cuts.py ROUND.json ALL.json
"""
import collections
import itertools
import json
import pathlib
import re
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import iteration_census as base

STAGES = ("intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare", "step-plan", "test-spec",
          "validate-existing", "implement", "test", "document", "carry-forward", "system-test-author", "system-test",
          "product-acceptance", "release-plan", "release-check", "release", "release-verify", "operations", "handoff")
PLANNING, TAIL = STAGES[:7], STAGES[16:]


def seconds(row, key):
    return row["seconds"].get(key, 0) - (row.get("down") or {}).get(key, 0)


def counted(row):
    name = pathlib.Path(row["folder"] or "").name
    return bool(re.search(r"-(S|L)-\d+$", name)) and not name.startswith("rehearsal")


def cut_a(rows):
    print("== A. this round's whole deliveries: mean seconds by stage, and the seconds after refused commands ==")
    cells = collections.defaultdict(list)
    for row in rows:
        cells[(f"{row['model']} {row['effort']}", row["case"])].append(row)
    for (driver, case), group in sorted(cells.items()):
        total = statistics.mean(sum(seconds(r, k) for k in r["seconds"]) for r in group)
        reviews = statistics.mean(sum(seconds(r, k) for k in r["seconds"] if k.startswith("review:")) for r in group)
        print(f"\n{driver}, {case}: {len(group)} runs, mean {total / 60:.1f} minutes with a host running")
        parts = [(stage, statistics.mean(seconds(r, stage) for r in group)) for stage in STAGES]
        print("  " + "; ".join(f"{stage} {value:.0f}s ({value / total:.0%})" for stage, value in parts if value >= 1)
              + f"; all reviews {reviews:.0f}s ({reviews / total:.0%})")
        count, cost, reasons = collections.Counter(), collections.Counter(), collections.Counter()
        for row in group:
            trace = pathlib.Path(row["run"]) / "trace.jsonl"
            commands = [e for e in (json.loads(line) for line in trace.read_text(errors="replace").splitlines() if line.strip())
                        if e.get("kind") == "command"]
            for refused, following in itertools.pairwise(commands):
                if refused.get("verb") in ("check", "complete") and refused.get("exit") not in (0, None):
                    stage = refused.get("stage")
                    stage = stage[0] if isinstance(stage, list) else stage
                    gap = following["ts"] - refused["ts"]
                    if 0 <= gap < 900:
                        count[stage] += 1
                        cost[stage] += gap
                    reasons[re.sub(r"/\S+", "<path>", str(refused.get("error") or ""))[:80]] += 1
        runs = len(group)
        print(f"  refused commands: {sum(count.values()) / runs:.1f} a run; seconds until the next command after each: "
              f"{sum(cost.values()) / runs:.0f}s a run ({sum(cost.values()) / runs / total:.0%} of the run)")
        print("  by stage (count a run, seconds a run): " + "; ".join(f"{stage} {n / runs:.1f}, {cost[stage] / runs:.0f}s"
                                                                     for stage, n in count.most_common(8)))
        print("  most common refusal texts: " + " | ".join(f"{n}x {text}" for text, n in reasons.most_common(4) if text))


def cut_b(rows):
    print("\n== B. criteria in each work item's accepted step plan, by run ==")
    for row in sorted(rows, key=lambda r: pathlib.Path(r["folder"]).name):
        items = {}
        for path in sorted((pathlib.Path(row["run"]) / "results").glob("nav-*.md"), key=lambda p: p.stat().st_mtime):
            record = base.state(path) or {}
            result = record.get("result")
            if record.get("stage") == "step-plan" and isinstance(result, dict) and result.get("outcome") == "done":
                items[record.get("workitem")] = (len(result.get("criteria") or ()), len(result.get("steps") or ()))
        print(f"  {pathlib.Path(row['folder']).name:<26}" + "; ".join(f"{item}: {c} criteria in {s} step{'s' if s != 1 else ''}"
                                                                    for item, (c, s) in items.items())
              + f"   total {sum(c for c, _ in items.values())}")


def cut_c(rows):
    print("\n== C. the recorded Grok whole deliveries: active minutes by part ==")
    grok = [r for r in rows if r.get("host") == "grok" and r.get("status") == "done" and not r.get("seeded") and r.get("kind") != "step-slice"]
    for row in sorted(grok, key=lambda r: (r["model"], r.get("first") or "")):
        total = sum(row["seconds"].values())
        reviews = {k[7:]: v for k, v in row["seconds"].items() if k.startswith("review:")}

        def part(keys, row=row):
            return sum(row["seconds"].get(k, 0) for k in keys) / 60

        print(f"  {row['model']} {row['effort']} {row['case']:<20}{(row.get('first') or '')[:10]} pass={row.get('passed')} option "
              f"{row['option']}: {total / 60:.0f} min | planning {part(PLANNING):.0f} | step-plan, test-spec "
              f"{part(('step-plan', 'test-spec', 'validate-existing')):.0f} | implement {part(('implement',)):.0f} | test "
              f"{part(('test',)):.0f} | document {part(('document',)):.0f} | system tests {part(('system-test-author', 'system-test')):.0f} | "
              f"acceptance to handoff {part(TAIL):.0f} | reviews {sum(reviews.values()) / 60:.0f} ({sum(reviews.values()) / total:.0%})")
        print("      reviews by reviewed stage, minutes: " + ", ".join(f"{k} {v / 60:.0f}" for k, v in sorted(reviews.items())))


if __name__ == "__main__":
    this_round = [r for r in json.loads(pathlib.Path(sys.argv[1]).read_text()) if counted(r)]
    cut_a(this_round)
    cut_b(this_round)
    cut_c(json.loads(pathlib.Path(sys.argv[2]).read_text()))
