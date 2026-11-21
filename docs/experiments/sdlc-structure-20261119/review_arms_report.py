#!/usr/bin/env python3
"""Round 7's registered measures and readings: arm S (as shipped, planning reviews pinned on) against arm L (lean).

Reads CENSUS.json, which review_option_census.py writes from the round's run folders (every run's recorded option,
verdict, case checks and seconds by stage, with each review charged to the stage it reviewed). A run's arm is the
letter in its folder name (`-S-1`, `-L-2`); folders that start with "rehearsal" are not counted.

It prints one row per run, then per driver and case the registered readings: whether each run's recorded option is
its arm's, minutes, the verdicts and case checks, and where the minutes differ by part.

Two things the registration did not foresee are read from files beside CENSUS.json:

  interrupted.json   {run folder name: note} for runs whose host another run's process kill ended or interrupted
                     (R60). Such a run's start-to-end minutes are not comparable, so a cell with one is also read
                     at a milestone every run reached before the kill: the first time the run enters `system-test`
                     (all build items done, the system tests written and, in arm S, reviewed).
  reruns.json        {run folder name: {check: {"first": note, "runs": n, "passed": n}}} for a case check that was
                     run again on the saved work after its verdict was lost (R55); a check that passes every rerun
                     counts as passed, and the first result is printed beside it.
  unfinished.json    {run folder name: {"checks": [...], "note": ...}} for a run that had not ended when the report
                     was made: the checks graded on a named earlier commit of it, and why.

Usage: python3 -I review_arms_report.py CENSUS.json
"""
import collections
import json
import pathlib
import re
import statistics
import sys

PLANNING = ("intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare")
PARTS = (("planning stages", PLANNING),
         ("planning reviews", ("review:spec", "review:test-strategy", "review:plan", "review:step-plan")),
         ("step-plan, test-spec", ("step-plan", "test-spec", "validate-existing")),
         ("implement", ("implement",)), ("test", ("test",)), ("document", ("document",)),
         ("step reviews", ("review:document",)),
         ("carry-forward + review", ("carry-forward", "review:carry-forward")),
         ("system tests", ("system-test-author", "system-test")),
         ("their review", ("review:system-test-author",)),
         ("acceptance to handoff", ("product-acceptance", "release-plan", "review:release-plan", "release-check", "release",
                                    "release-verify", "operations", "handoff")))
EXPECTED = {"S": "stage", "L": "none"}
INNER = ("implement", "test", "document", "test-spec", "validate-existing")


def arm_of(name):
    found = re.search(r"-(S|L)-\d+$", name)
    return found.group(1) if found else None


def beside(census, name):
    path = pathlib.Path(census).parent / name
    return json.loads(path.read_text()) if path.exists() else {}


def main(census):
    rows = []
    interrupted, reruns = beside(census, "interrupted.json"), beside(census, "reruns.json")
    unfinished = beside(census, "unfinished.json")
    for run in json.loads(pathlib.Path(census).read_text()):
        name = pathlib.Path(run["folder"] or "").name
        arm = arm_of(name)
        if not arm or name.startswith("rehearsal") or run.get("seeded"):
            continue
        trace = pathlib.Path(run["run"]) / "trace.jsonl"
        events = [json.loads(line) for line in trace.read_text(errors="replace").splitlines() if line.strip()] if trace.exists() else []
        reviews = [e.get("reviewed") for e in events if e.get("kind") == "packet" and e.get("stage") == "improve"]
        refused = sum(1 for e in events if e.get("kind") == "command" and e.get("verb") in ("check", "complete") and e.get("exit") not in (0, None))
        accepted = [e for e in events if e.get("kind") == "command" and e.get("verb") == "complete" and e.get("exit") == 0
                    and isinstance(e.get("stage"), list)]
        result = json.loads((pathlib.Path(run["folder"]) / "result.json").read_text()) if (pathlib.Path(run["folder"]) / "result.json").exists() else {}
        span = result.get("span") or {}
        start = events[0]["ts"] if events else None
        entered = next((e["ts"] for e in accepted if e["stage"][1] == "system-test"), None)
        planned = next((e["ts"] for e in accepted if e["stage"][1] == "step-plan"), None)
        built = next((e["ts"] for e in accepted if e["stage"][1] == "system-test-author"), None)
        fixed = reruns.get(name) or {}
        checks = list(run["checks"])
        labels = [c.get("command", "").split('.py" ')[-1].split()[0] for c in result.get("checks") or ()]
        for index, label in enumerate(labels):
            again = fixed.get(label)
            if again and index < len(checks) and not checks[index] and again["runs"] and again["passed"] == again["runs"]:
                checks[index] = True
        running = run["status"] != "done"
        if name in unfinished and running:
            checks = list(unfinished[name]["checks"])
        metrics = result.get("metrics") or {}
        so_far = (events[-1]["ts"] - start) / 60 if events and start else 0.0
        rows.append({**run, "name": name, "arm": arm, "driver": f"{run['model']} {run['effort']}", "checks": checks,
                     "first_checks": run["checks"], "interrupted": interrupted.get(name),
                     "verdicts": {key: bool((result.get(key) or {}).get("pass")) if isinstance(result.get(key), dict) else bool(result.get(key))
                                  for key in ("invoked", "plugin", "process", "shiploop", "committed")},
                     "milestone": (entered - start) / 60 if entered and start else None,
                     "planning": (planned - start) / 60 if planned and start else None,
                     "build": (built - planned) / 60 if built and planned else None,
                     "authoring": (entered - built) / 60 if entered and built else None,
                     "review_minutes": sum(v - (run.get("down") or {}).get(k, 0) for k, v in run["seconds"].items()
                                           if k.startswith("review:")) / 60,
                     "running": running, "regraded": name in unfinished and running,
                     "minutes": so_far if running else (span["ended"] - span["started"]) / 60 if span.get("ended") else so_far,
                     "part_cost": bool(metrics.get("unreported_sessions")), "stopped": sum((run.get("down") or {}).values()) / 60,
                     "reviews": reviews, "refused": refused,
                     "implements": sum(1 for e in accepted if e["stage"][0] == "implement"),
                     "sent_back": sum(1 for e in accepted if e["stage"][0] in INNER and e["stage"][1] == "step-plan"),
                     "items": 1 + sum(1 for e in accepted if e["stage"] == ["carry-forward", "step-plan"]),
                     "added_work": sum(1 for e in accepted if e["stage"][1] == "step-plan" and e["stage"][0] not in
                                       ("prepare", "carry-forward", "step-plan", "improve", *INNER)),
                     "cost": metrics.get("cost_usd"), "turns": metrics.get("turns")})
    rows.sort(key=lambda r: (r["driver"], r["case"], r["arm"], r["name"]))

    print(f"{'run':<28}{'driver':<24}{'arm':<4}{'option':>7}{'pass':>6}{'checks':>8}{'min':>7}{'reviews':>8}{'refused':>8}{'items':>6}{'implements':>11}"
          f"{'send-backs':>11}{'work added':>11}{'turns':>7}{'dollars':>9}{'to system-test':>16}")
    for row in rows:
        checks = row["checks"]
        cost = f"{row['cost']:.2f}{'*' if row['part_cost'] else ''}" if row["cost"] else "-"
        print(f"{row['name']:<28}{row['driver']:<24}{row['arm']:<4}{row['option']!s:>7}"
              f"{'-' if row['running'] else 'yes' if row['passed'] else 'NO':>6}"
              f"{f'{sum(checks)}/{len(checks)}':>8}{(f'{row["minutes"]:.1f}' + ('+' if row['running'] else '')):>7}{len(row['reviews']):>8}"
              f"{row['refused']:>8}{row['items']:>6}{row['implements']:>11}"
              f"{row['sent_back']:>11}{row['added_work']:>11}{row['turns'] or '-':>7}{cost:>9}"
              f"{(f'{row["milestone"]:.1f}' if row['milestone'] else '-'):>16}{'  interrupted' if row['interrupted'] else ''}"
              f"{', still running' if row['running'] else ''}")
    print("(min: start to end of the run, or with a + the minutes so far of a run still going; pass: the harness's overall verdict; "
          "reviews: Improve review packets issued; refused: check and complete commands ShipLoop refused; items: work items of "
          "the plan that were built; send-backs: a build stage returned the item to its step plan; work added: a stage after the "
          "build opened a new work item; dollars with a *: the resumed session only, the session the kill ended reported none)")
    for row in rows:
        print(f"  {row['name']}: reviews of {collections.Counter(row['reviews']).most_common()}")
    for row in rows:
        if row["interrupted"]:
            print(f"  {row['name']}: {row['interrupted']}")
        if row["name"] in unfinished and row["status"] != "done":
            print(f"  {row['name']}: {unfinished[row['name']]['note']}")
        if row["checks"] != row["first_checks"] and not row["regraded"]:
            print(f"  {row['name']}: checks as first graded {sum(row['first_checks'])}/{len(row['first_checks'])}; after reruns "
                  f"{sum(row['checks'])}/{len(row['checks'])}: {json.dumps(reruns.get(row['name']))[:300]}")

    cells = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in rows:
        cells[(row["driver"], row["case"])][row["arm"]].append(row)
    print("\n== the registered readings, by driver and case ==")
    for (driver, case), arms in sorted(cells.items()):
        shipped, lean = arms["S"], arms["L"]
        if not shipped or not lean:
            continue
        print(f"{driver}, {case}")
        running = [r["name"] for r in shipped + lean if r["status"] != "done"]
        if running:
            print(f"  not finished when this was made: {', '.join(running)}")
            if any(name not in unfinished for name in running):
                continue
        wrong = [r["name"] for r in shipped + lean if r["option"] != EXPECTED[r["arm"]]]
        print(f"  option recorded is the arm's: {'yes, in every run' if not wrong else 'NO: ' + ', '.join(wrong)}")
        def compare(key, label, shipped=shipped, lean=lean, read=True):
            if any(r[key] is None for r in shipped + lean):
                print(f"  {label}: not reached by {', '.join(r['name'] for r in shipped + lean if r[key] is None)}")
                return
            def shown(group):
                return ", ".join(f"{r[key]:.1f}" + ("+" if key == "minutes" and r["running"] else "") for r in group)
            if not read:
                print(f"  {label}: S {shown(shipped)} min; L {shown(lean)} min; not read")
                return
            mean_s, mean_l = statistics.mean(r[key] for r in shipped), statistics.mean(r[key] for r in lean)
            change = mean_l / mean_s - 1
            print(f"  {label}: S {shown(shipped)} min (mean {mean_s:.1f}); L {shown(lean)} min (mean {mean_l:.1f}); change {change:+.1%}: "
                  f"{'L saves time' if change <= -0.15 else 'L is slower' if change >= 0.15 else 'no readable difference'}")

        hit = [r["name"] for r in shipped + lean if r["interrupted"]]
        if hit:
            print(f"  interrupted by another run's process kill: {', '.join(hit)}; start-to-end minutes are not comparable in this cell "
                  "(they hold a stop, a wait and a resume)")
        compare("minutes", "time, start to end (the registered measure)" + (", not comparable here" if hit else ""), read=not hit)
        compare("milestone", "time to the first entry into system-test (fallback, not registered)")
        compare("planning", "  of it, to the first step plan (intake to prepare, with the planning reviews in S)")
        compare("build", "  of it, from there to the system-test author (the build items, their reviews, added work items)")
        compare("authoring", "  of it, writing the system tests (and in S their review)")
        compare("review_minutes", "minutes in Improve reviews, the whole run with a host running (an unfinished run so far)")
        if hit:
            for row in shipped + lean:
                row["worked"] = row["minutes"] - row["stopped"]
            print("  minutes with a host running (start to end less the time no host ran; not registered, and a resumed session "
                  "re-reads the run): S " + ", ".join(f"{r['worked']:.1f}" + ("+" if r["running"] else "") for r in shipped)
                  + "; L " + ", ".join(f"{r['worked']:.1f}" + ("+" if r["running"] else "") for r in lean) + "; not read")
        def failed(row):
            """The harness verdicts a run failed; a process verdict lost to the other run's kill is named as such."""
            if row["status"] != "done":
                return ["unfinished"]
            return [key + (" (lost to the kill)" if key == "process" and row["interrupted"] else "")
                    for key, ok in row["verdicts"].items() if not ok]

        def lost_verdict(row):
            if row["status"] != "done":
                return False  # an unfinished run has no verdicts yet; it is named above
            return any(not ok and not (key == "process" and row["interrupted"]) for key, ok in row["verdicts"].items())

        least = min(sum(r["checks"]) for r in shipped)
        lost = [r["name"] for r in lean if lost_verdict(r) or sum(r["checks"]) < least]
        print(f"  quality: harness verdicts failed: S {[failed(r) for r in shipped]}, L {[failed(r) for r in lean]}; held-out checks: S "
              f"{[f'{sum(r["checks"])}/{len(r["checks"])}' for r in shipped]}, L {[f'{sum(r["checks"])}/{len(r["checks"])}' for r in lean]}: "
              f"{'LOSS in ' + ', '.join(lost) if lost else 'no loss seen (every L run has at least the least S run)'}")
        print(f"  reviews run: S {[len(r['reviews']) for r in shipped]}, L {[len(r['reviews']) for r in lean]}; refused: S "
              f"{[r['refused'] for r in shipped]}, L {[r['refused'] for r in lean]}; work items built: S {[r['items'] for r in shipped]}, L {[r['items'] for r in lean]}; "
              f"send-backs: S {[r['sent_back'] for r in shipped]}, L "
              f"{[r['sent_back'] for r in lean]}; work added: S {[r['added_work'] for r in shipped]}, L {[r['added_work'] for r in lean]}")
        def part(row, keys):
            """Seconds a run spent in these stages with a host running: the time no host ran is taken out."""
            return sum(row["seconds"].get(k, 0) - (row.get("down") or {}).get(k, 0) for k in keys)

        print("  mean seconds by part with a host running, S and (L)" + (", an unfinished run counted as far as it got" if running else "")
              + ": " + "; ".join(f"{label} {statistics.mean(part(r, keys) for r in shipped):.0f} "
                                 f"({statistics.mean(part(r, keys) for r in lean):.0f})" for label, keys in PARTS))


if __name__ == "__main__":
    main(sys.argv[1])
