#!/usr/bin/env python3
"""For each delivery of a round: how long an answer had to arrive in.  argv: ROOT NAME...

Reads each run's ``timeline.json`` (when each action's result was accepted) and ``state.md`` (the run's actions in
order, by stage).  The list is printed in the packet of the stage after the spec (``test-strategy``), which is issued
when the spec's result is accepted.  Prints, per delivery, the seconds from that moment to the first accepted
``test-strategy`` result (an answer must be on file before that stage submits, so this is the most time an in-time
answer had), to the first accepted ``plan``, and to the last accepted ``plan`` (later than the first only when the
planning went round again), with the count of planning reconciliations."""
import datetime
import glob
import json
import re
import sys

root, names = sys.argv[1], sys.argv[2:]


def when(text):
    return datetime.datetime.fromisoformat(str(text))


print("name | spec accepted to strategy accepted, s | to first plan accepted, s | to last plan accepted, s | reconciliations")
for name in names:
    runs = sorted(glob.glob(f"{root}/{name}/.shiploop-runs/*/run"))
    if not runs:
        print(name, "| no run folder")
        continue
    run = runs[-1]
    with open(run + "/state.md", errors="replace") as handle:
        state_text = handle.read()
    state = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", state_text, re.DOTALL).group(1))
    with open(run + "/timeline.json", encoding="utf-8") as handle:
        accepted = (json.load(handle).get("accepted")) or {}
    times = {}
    for row in state.get("history") or []:
        if row.get("action") in accepted:
            times.setdefault(row.get("stage"), []).append(when(accepted[row["action"]]))
    try:
        shown = min(times["spec"])
        strategy = min(t for t in times["test-strategy"] if t >= shown)
        plans = sorted(t for t in times["plan"] if t >= shown)
        print(f"{name} | {(strategy - shown).total_seconds():.0f} | {(plans[0] - shown).total_seconds():.0f} | "
              f"{(plans[-1] - shown).total_seconds():.0f} | {len(state.get('planning_reconciliations') or [])}")
    except (ValueError, KeyError, IndexError) as error:
        print(name, "| not readable:", type(error).__name__, error)
