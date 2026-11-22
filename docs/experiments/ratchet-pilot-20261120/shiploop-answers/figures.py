#!/usr/bin/env python3
"""One row per delivery of a round, from the file ``read_answers.py --json`` wrote.  argv: ANSWERS_JSON.

Columns: the delivery, its driver, the harness's outcome, the case's held-out checks, the five of them that start the
service on a data file without due times, minutes, the seconds of the spec stage and of the stage that applies an
answer, turns, model calls, output tokens, the cost where the host reports one, callbacks the script held, refusals
that name ``answers``, other refusals, each note with where the engine says it stands, the rows of the list, and the
row the stand-in requester chose (or why it sent nothing)."""
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    rows = json.load(handle)
head = ("name | driver | outcome | checks | start-up checks of 5 | minutes | spec s | test-strategy s | turns | "
        "model calls | output tokens | cost | callbacks held | refusals naming answers | other refusals | "
        "notes (standing) | rows in list | stand-in")
print(head)
for r in rows:
    trace = r.get("trace") or {}
    startup = r.get("startup") or {}
    notes = ", ".join(f"{n.get('id')} {n.get('stands')}" for n in r.get("notes") or []) or "-"
    req = r.get("requester") or {}
    choice = req.get("choice") or {}
    if choice.get("selector"):
        stand = f"{req.get('mode')} {choice.get('selector')}"
    else:
        stand = (req.get("ended") or "nothing sent")
    other = sum((trace.get("other_refusals_by_stage") or {}).values())
    cost = r.get("cost_usd")
    print(" | ".join(str(x) for x in (
        r.get("name"), f"{r.get('host')} {r.get('model')}", r.get("outcome"),
        f"{r.get('checks_passed')}/{r.get('checks')}", sum(1 for v in startup.values() if v),
        r.get("minutes"), r.get("spec_seconds"), r.get("strategy_seconds"), r.get("turns"), r.get("model_calls"),
        r.get("output_tokens"), "-" if cost is None else f"{cost:.2f}", len(trace.get("held") or []),
        len(trace.get("naming_answers") or []), other, notes, len(r.get("list") or []), stand)))
