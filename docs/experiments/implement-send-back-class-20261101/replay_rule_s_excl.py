#!/usr/bin/env python3
"""Rule S with one correction (implement send-back study, 2026-11-01): the base search leaves out docs/shiploop, ShipLoop's own
knowledge folder.  In ShipLoop 1.26 and later the item-base tree holds docs/shiploop/environment.md, which records the focused
commands' test IDs, so `git grep` finds every ID there and the original replay_rule_s.py flags nothing in a greenfield run.
Everything else is the original script (docs/experiments/step-plan-review-20261101/replay_rule_s.py), unchanged.
Usage: python3 -I replay_rule_s_excl.py TRACES.txt OUT.jsonl"""
import json
import os
import re
import subprocess
import sys

STATE = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)


def norm(text):
    return " ".join(str(text).split())


def record(path):
    match = STATE.search(open(path, encoding="utf-8").read())
    return json.loads(match.group(1)) if match else {}


def result_of(run, state, action):
    kept = state.get("accepted", {}).get(action)
    if isinstance(kept, dict):
        return kept
    path = os.path.join(run, "results", action + ".md")
    return (record(path).get("result") or {}) if os.path.exists(path) else {}


def in_base(toplevel, tree, ident):
    try:
        done = subprocess.run(["git", "-C", toplevel, "grep", "-q", "-w", "-F", "-e", ident, tree, "--", ":(exclude)docs/shiploop"],
                              capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return {0: True, 1: False}.get(done.returncode)


def flagged(plan, toplevel, tree):
    steps = plan.get("steps") or []
    if not steps or not isinstance(steps[0], dict):
        return None
    segments = {norm(part) for part in re.split(r"&&|\|\||;", steps[0].get("proof") or "") if part.strip()}
    for row in plan.get("test_commands") or ():
        if not isinstance(row, dict) or row.get("suite") != "focused" or not row.get("ids"):
            continue
        if norm(row.get("command")) in segments:
            seen = [in_base(toplevel, tree, ident) for ident in row["ids"]]
            if None in seen:
                return {"command": row["command"], "unknown": True}
            if not any(seen):
                return {"command": row["command"], "ids": row["ids"]}
    return None


def main():
    out = []
    for trace in open(sys.argv[1], encoding="utf-8").read().split():
        run = os.path.dirname(trace)
        try:
            state = record(os.path.join(run, "state.md"))
        except OSError:
            continue
        history = state.get("history", [])
        for index, row in enumerate(history):
            if row.get("stage") != "step-plan" or row.get("outcome") != "done":
                continue
            item = row.get("workitem")
            base_file = os.path.join(run, "lint", "items", str(item) + ".md")
            if not os.path.exists(base_file):
                continue
            base = record(base_file)
            if not base.get("tree") or not base.get("toplevel") or not os.path.isdir(base["toplevel"]):
                continue
            plan = state.get("accepted", {}).get(row["action"])
            if not isinstance(plan, dict):
                continue
            hit = flagged(plan, base["toplevel"], base["tree"])
            outcome = None
            for later in history[index + 1:]:
                if later.get("workitem") != item:
                    continue
                if later.get("stage") == "step-plan":
                    break
                if later.get("stage") == "implement":
                    result = result_of(run, state, later["action"])
                    outcome = later.get("outcome") + (": " + str(result.get("headline") or "")[:90]
                                                      if later.get("outcome") == "send-back" else "")
                    break
            out.append({"run": run.replace(os.path.expanduser("~") + "/", "~/"), "item": item, "action": row["action"],
                        "flag": hit, "s1_implement": outcome,
                        "proof": norm((plan.get("steps") or [{}])[0].get("proof") or "")[:160]})
    with open(sys.argv[2], "w", encoding="utf-8") as handle:
        for row in out:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    hits = [r for r in out if r["flag"] and not r["flag"].get("unknown")]
    print("plans with a base", len(out), "flagged", len(hits), "unknown", sum(1 for r in out if r["flag"] and r["flag"].get("unknown")))
    for r in hits:
        print(" ", (r["s1_implement"] or "no implement")[:110], "|", r["proof"][:90], "|", r["run"][-50:])


if __name__ == "__main__":
    main()
