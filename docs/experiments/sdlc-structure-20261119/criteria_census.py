#!/usr/bin/env python3
"""List, from each run's accepted step plans, the criteria marked `executed` that are about a document, the test
suite itself or release metadata, and not about the product's behaviour (round 15). A list to confirm by reading.
Usage: python3 -I criteria_census.py NAME=RUN_FOLDER ...
"""
import glob, json, re, sys

ABOUT = re.compile(r"\b(documented|documentation|README|CHANGELOG|changelog|docs/|decision record|package\.json|"
                   r"version (is|equals|at least)|suite (runs|is discoverable|exits)|prints every|every (TC|test) ID|"
                   r"test files? (sit|are|exist)|discoverable by)\b")


def record(path):
    text = open(path, errors="replace").read()
    m = re.search(r"```shiploop-state\n(.*?)\n```", text, re.S)
    try:
        return json.loads(m.group(1)) if m else None
    except ValueError:
        return None


def main(argv):
    total = marked_runs = 0
    for spec in argv:
        name, folder = spec.split("=")
        runs = glob.glob(folder + "/.shiploop-runs/*/run")
        state = (record(runs[0] + "/state.md") if runs else None) or {}
        latest = {}
        for row in state.get("history", []):
            if row.get("stage") == "step-plan" and row.get("outcome") == "done":
                latest[row.get("workitem")] = (state.get("accepted") or {}).get(row.get("action")) or {}
        executed = searched = 0; hits = []
        for item, plan in latest.items():
            for c in plan.get("criteria") or []:
                kind = c.get("confirm", "executed")
                executed += kind == "executed"; searched += kind == "searched"
                if kind == "executed" and ABOUT.search(c.get("text", "")):
                    hits.append((item, c["id"], " ".join(c["text"].split())[:230]))
        total += 1; marked_runs += bool(hits)
        print(f"{name:26s} step plans {len(latest)}; criteria executed {executed}, searched {searched}; executed and about a document, the suite or the release: {len(hits)}")
        for item, cid, text in hits:
            print(f"    {item} {cid}: {text}")
    print(f"\n{marked_runs} of {total} runs have at least one such criterion")


main(sys.argv[1:])
