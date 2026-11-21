#!/usr/bin/env python3
"""Round 8's Sol 6.2 high baseline beside round 7's Sol 6.2 medium runs of the same requests.

BASE.json is round 7's run list (runs-reviews/census.json); NEW.json is this round's (runs-effort/census.json),
both written by review_option_census.py. Only runs of MODEL are read. A base run's arm is the letter in its folder
name (`-S-1`, `-L-2`); the registered base for time is arm S.

Per run it prints the effort, the ShipLoop version, the recorded planning-review option, the harness's verdict, the
held-out checks, the planning choice of `ticket-due-times` (read from the `migrate` probe: the service fills the
data file when it starts, or it refuses to start switched on until an operator has run a script), minutes from
start to end and to two milestones, reviews run and how many changed anything (pass logs), refused commands, the
criteria and steps of the first step plan, work items, and how often the run's events name a file under the
user's own skill folders (Codex lists those to every session: 6c9055f1672a61ec43fc9776ba7728486bf66546).

Then, per request, the registered readings: high against the medium arm S runs at 15%, and the counts.

Usage: python3 -I effort_report.py BASE.json NEW.json [MODEL]
"""
import json
import pathlib
import re
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import iteration_census as base
import review_yield_drivers as yields

HOME = str(pathlib.Path.home())
USER_SKILLS = (f"{HOME}/.codex/skills/", f"{HOME}/.agents/skills/")
BUILD = ("implement", "test", "document", "test-spec", "validate-existing")


def load(path):
    try:
        return json.loads(pathlib.Path(path).read_text())
    except (OSError, ValueError):
        return {}


def row_of(run):
    folder, rundir = pathlib.Path(run["folder"]), pathlib.Path(run["run"])
    name = folder.name
    arm = re.search(r"-(S|L)-\d+$", name)
    result, invocation = load(folder / "result.json"), load(folder / "invocation.json")
    events = [json.loads(line) for line in (rundir / "trace.jsonl").read_text(errors="replace").splitlines() if line.strip()]
    accepted = [e for e in events if e.get("kind") == "command" and e.get("verb") == "complete" and e.get("exit") == 0
                and isinstance(e.get("stage"), list)]
    start = events[0]["ts"] if events else None

    def minutes_to(stage):
        moment = next((e["ts"] for e in accepted if e["stage"][1] == stage), None)
        return (moment - start) / 60 if moment and start else None

    checks = result.get("checks") or []
    choice = "-"
    for check in checks:
        if '.py" migrate' in check.get("command", ""):
            text = json.dumps(check)
            choice = ("fills at start" if check.get("pass") else
                      "operator step first" if "before it listened" in text or "did not start" in text else "other failure")
    reviews = changed = 0
    for log in (rundir / "improve").glob("*/passes.md"):
        table = yields.passes(log)
        if table:
            reviews += 1
            changed += any(row.get("tree changed") == "y" or row.get("result changed") == "y" for row in table)
    criteria = steps = None
    for path in sorted((rundir / "results").glob("nav-*.md"), key=lambda p: p.stat().st_mtime):
        record = base.state(path) or {}
        plan = record.get("result")
        if record.get("stage") == "step-plan" and isinstance(plan, dict) and plan.get("outcome") == "done":
            criteria, steps = len(plan.get("criteria") or ()), len(plan.get("steps") or ())
            break
    try:
        stream = (folder / "events.jsonl").read_text(errors="replace")
    except OSError:
        stream = ""
    span = result.get("span") or {}
    sessions = [json.loads(line) for line in (folder / "sessions.jsonl").read_text().splitlines() if line.strip()] \
        if (folder / "sessions.jsonl").exists() else []
    return {"name": name, "case": run["case"], "effort": run["effort"], "arm": arm.group(1) if arm else "-",
            "version": (invocation.get("versions") or {}).get("shiploop_version"), "option": run["option"],
            "done": run["status"] == "done", "passed": result.get("pass"), "checks": [bool(c.get("pass")) for c in checks],
            "choice": choice, "minutes": (span["ended"] - span["started"]) / 60 if span.get("ended") else None,
            "starts": sum(1 for s in sessions if s.get("row") == "start"),
            "planned": minutes_to("step-plan"), "system_test": minutes_to("system-test"),
            "reviews": reviews, "changed": changed,
            "refused": sum(1 for e in events if e.get("kind") == "command" and e.get("verb") in ("check", "complete")
                           and e.get("exit") not in (0, None)),
            "criteria": criteria, "steps": steps,
            "items": 1 + sum(1 for e in accepted if e["stage"] == ["carry-forward", "step-plan"]),
            "late": sum(1 for e in accepted if e["stage"][1] == "step-plan"
                        and e["stage"][0] not in ("prepare", "carry-forward", "step-plan", "improve", *BUILD)),
            "user_skills": sum(stream.count(root) for root in USER_SKILLS)}


def shown(value, digits=1):
    return "-" if value is None else f"{value:.{digits}f}"


def main(base_path, new_path, model="gpt-6.2-sol"):
    rows = []
    for path in (base_path, new_path):
        for run in json.loads(pathlib.Path(path).read_text()):
            name = pathlib.Path(run["folder"] or "").name
            if run.get("model") == model and not run.get("seeded") and not name.startswith("rehearsal"):
                rows.append(row_of(run))
    rows.sort(key=lambda r: (r["case"], r["effort"], r["arm"], r["name"]))
    print(f"{'run':<26}{'effort':<8}{'arm':<4}{'ShipLoop':<9}{'option':<7}{'pass':<5}{'checks':<7}{'planning choice':<21}{'min':>6}"
          f"{'to plan':>8}{'to sys-test':>12}{'reviews':>8}{'changed':>8}{'refused':>8}{'criteria':>9}{'steps':>6}{'items':>6}"
          f"{'late':>5}{'own skills':>11}")
    for r in rows:
        checks = f"{sum(r['checks'])}/{len(r['checks'])}"
        print(f"{r['name']:<26}{r['effort']:<8}{r['arm']:<4}{r['version']!s:<9}{r['option']!s:<7}"
              f"{('yes' if r['passed'] else 'NO') if r['done'] else '...':<5}{checks:<7}{r['choice']:<21}{shown(r['minutes']):>6}"
              f"{shown(r['planned']):>8}{shown(r['system_test']):>12}{r['reviews']:>8}{r['changed']:>8}{r['refused']:>8}"
              f"{r['criteria']!s:>9}{r['steps']!s:>6}{r['items']:>6}{r['late']:>5}{r['user_skills']:>11}"
              f"{'  ' + str(r['starts']) + ' sessions' if r['starts'] > 1 else ''}")
    print("(min: start to end; to plan / to sys-test: minutes to the first step plan and to the first entry into system-test; changed: "
          "reviews whose pass log shows a change; own skills: mentions of a file under the user's own skill folders in the run's events)")

    print("\n== the registered readings, by request ==")
    for case in sorted({r["case"] for r in rows}):
        medium = [r for r in rows if r["case"] == case and r["effort"] == "medium" and r["arm"] == "S"]
        medium_all = [r for r in rows if r["case"] == case and r["effort"] == "medium"]
        high = [r for r in rows if r["case"] == case and r["effort"] == "high"]
        if not high:
            continue
        print(f"{case}")
        unfinished = [r["name"] for r in high if not r["done"]]
        if unfinished:
            print(f"  not finished when this was made: {', '.join(unfinished)}")
        apart = [r["name"] for r in high if r["option"] != "stage"]
        if apart:
            print(f"  recorded an option other than stage by itself, reported apart: {', '.join(apart)}")
        cell = [r for r in high if r["done"] and r["option"] == "stage"]
        for key, label in (("minutes", "start to end (the registered measure)"), ("planned", "to the first step plan"),
                           ("system_test", "to the first entry into system-test")):
            a, b = [r[key] for r in medium if r[key] is not None], [r[key] for r in cell if r[key] is not None]
            if not a or not b:
                print(f"  minutes {label}: not available")
                continue
            change = statistics.mean(b) / statistics.mean(a) - 1
            word = "high is slower" if change >= 0.15 else "high is faster" if change <= -0.15 else "no readable difference"
            resumed = [r["name"] for r in medium + cell if r["starts"] > 1]
            print(f"  minutes {label}: medium S {', '.join(shown(v) for v in a)} (mean {statistics.mean(a):.1f}); high "
                  f"{', '.join(shown(v) for v in b)} (mean {statistics.mean(b):.1f}); change {change:+.1%}: {word}"
                  + (f"; resumed runs in this cell: {', '.join(resumed)}" if resumed and key == "minutes" else ""))
        print(f"  held-out checks: medium S {[f'{sum(r["checks"])}/{len(r["checks"])}' for r in medium]}, medium L "
              f"{[f'{sum(r["checks"])}/{len(r["checks"])}' for r in medium_all if r['arm'] == 'L']}, high "
              f"{[f'{sum(r["checks"])}/{len(r["checks"])}' for r in high if r['done']]}")
        if any(r["choice"] != "-" for r in high + medium_all):
            def count(group):
                return f"{sum(r['choice'] == 'operator step first' for r in group)} of {len(group)}"
            print(f"  planning choice, runs whose service refuses to start switched on until an operator step: medium {count(medium_all)} "
                  f"(S and L), high {count([r for r in high if r['done']])}; counted, no reading registered")
        print(f"  reviews that changed anything: medium S {[f'{r["changed"]} of {r["reviews"]}' for r in medium]}, high "
              f"{[f'{r["changed"]} of {r["reviews"]}' for r in high if r['done']]}")
        print(f"  first step plan, criteria in steps: medium {[f'{r["criteria"]} in {r["steps"]}' for r in medium_all]}, high "
              f"{[f'{r["criteria"]} in {r["steps"]}' for r in high]}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
