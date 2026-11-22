#!/usr/bin/env python3
"""Read round 15's confirmation round: per run, the harness verdicts and checks, the recorded run option, the work
items with their regression commands, every release-verify attempt (the returned tree, each command with whether
ShipLoop added it, its status, count, floor and the floor's record, and the outcome the action ended with), and the
observers on the delivered tree. Reads run folders; writes nothing into them.
Usage: python3 -I confirm_read.py OBSERVE_PY SCRATCH NAME=RUN_FOLDER ...
"""
import glob, json, re, subprocess, sys, tempfile
from pathlib import Path

CASES = {"ticket-due-times", "shared-expenses"}


def record(path):
    text = open(path, errors="replace").read()
    m = re.search(r"```shiploop-state\n(.*?)\n```", text, re.S)
    try:
        return json.loads(m.group(1)) if m else None
    except ValueError:
        return None


def release_verify(run):
    """Each release-verify test record of the run: where it ran, and each command with status, count and floor."""
    state = record(run + "/state.md") or {}
    rows = []
    for row in state.get("history", []):
        if row.get("stage") != "release-verify":
            continue
        for path in sorted(glob.glob(f"{run}/tests/{row['action']}-verify*.md")):
            rec = record(path) or {}
            observed = rec.get("observed") or {}
            rows.append({"outcome": row.get("outcome"), "where": observed.get("where"), "action": row["action"],
                         "record": path.split("/tests/")[-1], "head": str(observed.get("head") or "")[:12],
                         "tree": str(observed.get("tree") or "")[:12], "passed": rec.get("passed"),
                         "disposition": rec.get("disposition"),
                         "runs": [{"suite": r.get("suite"), "command": r.get("command"), "status": r.get("status"),
                                   "ran": (r.get("counts") or {}).get("ran"), "floor": r.get("accepted_ran"),
                                   "added": bool(r.get("from_step_plan")), "exit": r.get("exit"),
                                   "from": r.get("floor_from"), "seconds": r.get("seconds")}
                                  for r in rec.get("runs") or []]})
    refusals = []
    try:
        for line in open(run + "/trace.jsonl", errors="replace"):
            r = json.loads(line)
            if r.get("kind") == "command" and r.get("exit") and r.get("error") and (r.get("stage") or [None])[0] == "release-verify":
                refusals.append(" ".join(r["error"].split())[:260])
    except (OSError, ValueError):
        pass
    option = re.search(r'"planning_review": "([a-z]+)"', open(run + "/state.md", errors="replace").read())
    items = []
    accepted = state.get("accepted") or {}
    for item in state.get("work_items") or []:
        plans = [row["action"] for row in state.get("history", []) if row.get("stage") == "step-plan"
                 and row.get("workitem") == item.get("id") and row.get("outcome") == "done"]
        commands = [r["command"] for r in (accepted.get(plans[-1]) or {}).get("test_commands") or []
                    if r.get("suite") == "regression" or r.get("regression")] if plans else []
        items.append((item.get("id"), str(item.get("title") or "")[:70], commands))
    outer = [(row.get("stage"), row.get("outcome")) for row in state.get("history", [])
             if row.get("workitem") is None and row.get("stage") in ("release-plan", "release", "release-verify")]
    checks = [(row.get("action"), [c.get("command") for c in (accepted.get(row.get("action")) or {}).get("consumer_checks") or []])
              for row in state.get("history", []) if row.get("stage") == "release-plan" and row.get("outcome") == "done"]
    return rows, refusals, (option.group(1) if option else None), items, outer, checks


def main(argv):
    observe, scratch = argv[0], Path(argv[1])
    for spec in argv[2:]:
        name, folder = spec.split("=")
        print("==", name)
        try:
            res = json.load(open(folder + "/result.json"))
        except (OSError, ValueError):
            print("   no result.json yet"); continue
        checks = res.get("checks") or []
        verdicts = {k: (res.get(k) or {}).get("pass") for k in ("invoked", "plugin", "process", "shiploop", "committed")}
        metrics = {}
        try:
            metrics = json.load(open(folder + "/metrics.json"))
        except (OSError, ValueError):
            pass
        print(f"   case {res.get('case')} | {res.get('model')} {res.get('effort')} | pass {res.get('pass')} | verdicts {verdicts} | "
              f"checks {sum(1 for c in checks if c.get('pass'))}/{len(checks)} | cost {metrics.get('cost_usd')} | "
              f"build {(res.get('versions') or {}).get('local_head', '')[:9]}")
        for c in checks:
            if not c.get("pass"):
                print("   FAILED CHECK:", c.get("command"), "|", " ".join((c.get("output") or "").split())[-200:])
        runs = sorted(glob.glob(folder + "/.shiploop-runs/*/run"))
        if not runs:
            continue
        rows, refusals, option, items, outer, plans = release_verify(runs[-1])
        print("   planning reviews:", option, "| ShipLoop status:", (res.get("shiploop") or {}).get("status"),
              "| ShipLoop run folders:", len(runs))
        for item_id, title, commands in items:
            print(f"   work item {item_id} ({title}): regression commands {commands}")
        for action, commands in plans:
            print(f"   release-plan {action} recorded consumer checks: {[c[:110] for c in commands]}")
        print("   release stages in order:", " ".join(f"{stage}:{outcome}" for stage, outcome in outer))
        for r in rows:
            print(f"   release-verify attempt {r['record']} (the action ended {r['outcome']}; in {r['where']}; returned head "
                  f"{r['head']}, tree {r['tree']}; passed {r['passed']}, {r['disposition']}):")
            for c in r["runs"]:
                print(f"      {'ADDED' if c['added'] else 'check'} [{c['suite']}] {c['command'][:100]} -> {c['status']}, exit {c['exit']}, "
                      f"ran {c['ran']}, floor {c['floor']}" + (f" ({c['from']})" if c["from"] else "") + f", {c['seconds']} s")
        for text in refusals:
            print("   REFUSAL at release-verify:", text)
        case = res.get("case")
        head = (res.get("committed") or {}).get("head")
        bundle = Path(folder) / "delivery" / "work.bundle"
        if case in CASES and head and bundle.is_file():
            clone = Path(tempfile.mkdtemp(prefix="clone-", dir=scratch))
            tree = Path(tempfile.mkdtemp(prefix="tree-", dir=scratch))
            subprocess.run(["git", "clone", "-q", str(bundle), str(clone)], check=True)
            tar = subprocess.run(["git", "-C", str(clone), "archive", head], check=True, capture_output=True).stdout
            subprocess.run(["tar", "-x", "-C", str(tree)], input=tar, check=True)
            out = scratch / f"{name}-observations.json"
            subprocess.run([sys.executable, observe, case, str(tree), "--out", str(out)], capture_output=True, text=True, cwd=scratch)
            try:
                for o in json.load(open(out))["observations"]:
                    print(f"   observer {o.get('observer')}: {o.get('summary')}")
                    if o.get("observer") == "ticket-return":
                        print("      first start:", o.get("first_start"), "| ordinary:", {k: v for k, v in (o.get("ordinary_return") or {}).items() if k != "prepared_by"},
                              "| with the kept copy:", ({k: v for k, v in o["assisted_return"].items() if k != "prepared_by"} if o.get("assisted_return") else "no such option"))
                    if o.get("observer") == "expense-inputs":
                        print("      recorded, not judged:", o.get("recorded_not_judged"))
            except (OSError, ValueError, KeyError):
                print("   observers: no record written")


main(sys.argv[1:])
