#!/usr/bin/env python3
"""Which runs ran with planning reviews off, who asked for it, and what the reviews of each run cost (round 7).

For every ShipLoop run directory under the given roots (``**/.shiploop-runs/*/run``) this reads

  state.md        the run option ``planning_review`` (``stage`` or ``none``);
  trace.jsonl     the run's last recorded status, and the seconds between navigator commands, charged to the stage
                  the run was in; an Improve review is charged to the stage it reviews (the `packet` row that issued
                  it names it);
  invocation.json / result.json of the E2E folder that holds the run: host, model, effort, case, whether the harness
                  seeded the run (a slice), whether the harness itself asked for the option, and whether the run passed.

It prints, for whole deliveries (not seeded) that finished:
  1. runs by host, model and effort with the option each recorded, and for `none` whether the harness asked for it;
  2. minutes and the share of run time in reviews, by option, for the cells that hold both options;
  3. review seconds by reviewed stage as a share of run time, by host, model and effort.

Usage: python3 -I review_option_census.py OUT.json ROOT [ROOT ...]
"""
import collections
import glob
import itertools
import json
import pathlib
import re
import statistics
import sys

OPTION = re.compile(r'"planning_review": "([a-z]+)"')
IDLE = 45 * 60
REVIEWED = ("spec", "test-strategy", "plan", "step-plan", "document", "carry-forward", "system-test-author", "release-plan")


def holder(run):
    """The E2E folder that holds this run: the nearest parent with an invocation.json or a result.json."""
    for parent in run.parents:
        if (parent / "invocation.json").exists() or (parent / "result.json").exists():
            return parent
    return None


def load(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def read_run(run):
    try:
        state = (run / "state.md").read_text(errors="replace")
        rows = [json.loads(line) for line in (run / "trace.jsonl").read_text(errors="replace").splitlines() if line.strip()]
    except (OSError, ValueError):
        return None
    option = OPTION.search(state)
    status = next((row["status"] for row in reversed(rows) if row.get("status")), None)
    folder = holder(run)
    invocation = load(folder / "invocation.json") if folder else {}
    result = load(folder / "result.json") if folder else {}
    reviewed = {row.get("action"): row.get("reviewed") for row in rows if row.get("kind") == "packet" and row.get("stage") == "improve"}
    commands = [row for row in rows if row.get("kind") == "command" and isinstance(row.get("ts"), (int, float))]
    seconds = collections.Counter()
    for before, row in itertools.pairwise(commands):
        gap = row["ts"] - before["ts"]
        if gap < 0 or gap > IDLE:
            continue
        stage = row.get("stage")
        stage = stage[0] if isinstance(stage, list) else stage
        if stage == "improve":
            cursor = row.get("cursor")
            action = cursor[0] if isinstance(cursor, list) else row.get("action")
            seconds["review:" + str(reviewed.get(action) or "?")] += gap
        elif stage:
            seconds[str(stage)] += gap
    prompt = ""
    for name in ("prompt.txt", "host-prompt.txt"):
        try:
            prompt += (folder / name).read_text(errors="replace") if folder else ""
        except OSError:
            pass
    acceptance = (result.get("quality") or {}).get("acceptance") or {}
    return {"run": str(run), "folder": str(folder) if folder else None,
            "option": option.group(1) if option else None, "status": status,
            "host": invocation.get("host") or result.get("host"), "model": invocation.get("model") or result.get("model"),
            "effort": invocation.get("effort") or result.get("effort"), "case": invocation.get("case") or result.get("case"),
            "kind": invocation.get("kind"), "seeded": bool(invocation.get("seeded") or result.get("seeded")),
            "asked": "--planning-review none" in prompt or "--planning-review=none" in prompt or invocation.get("planning_review") == "none",
            "passed": result.get("pass"), "checks": [bool(c.get("pass")) for c in result.get("checks") or ()],
            "hidden": [len(acceptance.get("passed") or ()), len(acceptance.get("ids") or ())] if acceptance.get("observed") else None,
            "first": rows[0].get("at") if rows else None, "seconds": dict(seconds)}


def driver(row):
    return f"{row['host']} {row['model']} {row['effort'] or '-'}"


def main(out, roots):
    found = []
    for root in roots:
        for path in sorted(glob.glob(str(pathlib.Path(root) / "**" / ".shiploop-runs" / "*" / "run"), recursive=True)):
            row = read_run(pathlib.Path(path))
            if row:
                found.append(row)
    pathlib.Path(out).write_text(json.dumps(found, indent=1))
    whole = [r for r in found if not r["seeded"] and r["kind"] != "step-slice" and r["host"] and r["option"]]
    done = [r for r in whole if r["status"] == "done"]
    print(f"run directories read: {len(found)}; whole deliveries with a recorded option: {len(whole)}; of them finished: {len(done)}")

    print("\n== 1. the option each finished whole delivery recorded, by driver ==")
    print(f"{'driver':<40}{'runs':>6}{'stage':>7}{'none':>6}{'none, harness asked':>21}{'none, not asked':>17}{'first':>12}{'last':>12}")
    cells = collections.defaultdict(list)
    for row in done:
        cells[driver(row)].append(row)
    for name, group in sorted(cells.items(), key=lambda kv: -len(kv[1])):
        none = [r for r in group if r["option"] == "none"]
        days = sorted((r["first"] or "")[:10] for r in group)
        print(f"{name:<40}{len(group):>6}{sum(r['option'] == 'stage' for r in group):>7}{len(none):>6}"
              f"{sum(r['asked'] for r in none):>21}{sum(not r['asked'] for r in none):>17}{days[0]:>12}{days[-1]:>12}")
    unasked = [r for r in done if r["option"] == "none" and not r["asked"]]
    print(f"finished whole deliveries that recorded `none` without the harness asking: {len(unasked)}")
    for row in unasked[:20]:
        print(f"    {(row['first'] or '')[:10]} {driver(row):<36} {row['case']:<24} pass={row['passed']} hidden={row['hidden']} "
              f"{sum(row['seconds'].values()) / 60:.0f} min  {row['folder']}")

    def minutes(row):
        return sum(row["seconds"].values()) / 60

    def review_share(row):
        total = sum(row["seconds"].values())
        return sum(v for k, v in row["seconds"].items() if k.startswith("review:")) / total if total else 0.0

    print("\n== 2. stage against none, same driver and case (finished whole deliveries) ==")
    both = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in done:
        both[(driver(row), row["case"])][row["option"]].append(row)
    for (name, case), arms in sorted(both.items()):
        if arms["stage"] and arms["none"]:
            def line(group):
                hidden = [r["hidden"] for r in group if r["hidden"]]
                return (f"{len(group)} runs, median {statistics.median(minutes(r) for r in group):.0f} min, reviews "
                        f"{statistics.median(review_share(r) for r in group):.0%} of run time, passed {sum(bool(r['passed']) for r in group)}"
                        + (f", hidden checks {sum(h[0] for h in hidden)} of {sum(h[1] for h in hidden)}" if hidden else ""))
            print(f"  {name:<36}{case:<24} stage: {line(arms['stage'])} | none: {line(arms['none'])}")

    print("\n== 3. review seconds by reviewed stage as a share of run time (finished whole deliveries, option stage) ==")
    print(f"{'driver':<40}{'runs':>6}{'min':>6}{'all reviews':>13}" + "".join(f"{stage:>14}" for stage in REVIEWED))
    for name, group in sorted(cells.items(), key=lambda kv: -len(kv[1])):
        staged = [r for r in group if r["option"] == "stage"]
        if len(staged) < 2:
            continue
        total = sum(sum(r["seconds"].values()) for r in staged)
        print(f"{name:<40}{len(staged):>6}{statistics.median(minutes(r) for r in staged):>6.0f}"
              f"{sum(v for r in staged for k, v in r['seconds'].items() if k.startswith('review:')) / total:>13.0%}"
              + "".join(f"{sum(r['seconds'].get('review:' + stage, 0) for r in staged) / total:>14.1%}" for stage in REVIEWED))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
