#!/usr/bin/env python3
"""Print chosen concern rows of each run's accepted plan (round 15). Reads run records only.
With --blind KEYFILE the runs are printed in a shuffled order under the labels P1, P2, ... and the key is written
to KEYFILE, so the rows can be read without knowing which run wrote them.
Usage: python3 -I plan_rows.py [--blind KEYFILE] IDS NAME=RUN_FOLDER ...   IDS is a comma-separated list of concern ids
"""
import glob, json, random, re, sys


def record(path):
    text = open(path, errors="replace").read()
    m = re.search(r"```shiploop-state\n(.*?)\n```", text, re.S)
    try:
        return json.loads(m.group(1)) if m else None
    except ValueError:
        return None


def main(argv):
    keyfile = None
    if argv[0] == "--blind":
        keyfile, argv = argv[1], argv[2:]
    wanted = argv[0].split(",")
    specs = list(argv[1:])
    if keyfile:
        random.SystemRandom().shuffle(specs)
        key = {f"P{number}": spec.split("=")[0] for number, spec in enumerate(specs, 1)}
        json.dump(key, open(keyfile, "w"), indent=1)
        specs = [f"P{number}=" + spec.split("=")[1] for number, spec in enumerate(specs, 1)]
    for spec in specs:
        name, folder = spec.split("=")
        runs = glob.glob(folder + "/.shiploop-runs/*/run")
        print("==", name)
        if not runs:
            print("   no run folder"); continue
        state = record(runs[0] + "/state.md") or {}
        plan = None
        for row in state.get("history", []):
            if row.get("stage") == "plan" and row.get("outcome") == "done":
                plan = (state.get("accepted") or {}).get(row.get("action"))
        if not isinstance(plan, dict) or "concerns" not in plan:
            print("   no accepted plan with concerns"); continue
        for item, rows in plan["concerns"].items():
            for r in rows:
                if r.get("id") in wanted:
                    text = r.get("decision") or r.get("reason") or ""
                    print(f"   {item} {r['id']} [{r['applies']}] owner={r.get('owner_stage')} anchor={r.get('anchor')}: {text}")


main(sys.argv[1:])
