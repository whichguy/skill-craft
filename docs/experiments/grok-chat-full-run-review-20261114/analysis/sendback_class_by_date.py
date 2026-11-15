"""How many implement send-backs say "the proof needs a test the test stage has not written", by day.

    python3 -I sendback_class_by_date.py TRACE_LIST

The class is the one docs/experiments/implement-send-back-class-20261101 studied: implement may not write tests, the step's
Proof is the test runner, and on a base with no tests it runs nothing or fails on a missing file.  It is recognised by the
model's own words in its send-back summary: the stage "forbids/prohibits" writing tests, or tests come "after implement" /
"before the test stage".  The recogniser is checked against a reading of all 28 retained implement send-backs
(sendback_reasons.py output): see CHECK below.  Day is the UTC date of the send-back.
"""
import collections
import datetime
import json
import os
import re
import sys

cut = datetime.datetime(2026, 10, 29, 15, 0).timestamp()
CLASS = re.compile(r"(forbid|prohibit|schedules after implement|before the test stage|later test stage|test stage (creates|writes|comes later))", re.I)
TESTY = re.compile(r"test", re.I)
files = [line.strip() for line in open(sys.argv[1]) if line.strip()]
exits = collections.Counter()
hits = collections.Counter()
other = collections.Counter()
runs_hit = set()
examples = []
for trace in files:
    try:
        lines = open(trace, errors="replace").read().splitlines()
    except OSError:
        continue
    for line in lines:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("ts", 0) < cut or r.get("kind") != "command" or r.get("verb") != "complete" or r.get("exit") != 0:
            continue
        stage = r.get("stage")
        if not (isinstance(stage, list) and len(stage) == 2) or stage[0] != "implement":
            continue
        day = r["at"][:10]
        exits[day] += 1
        if stage[1] not in ("step-plan", "test-spec", "plan"):
            continue
        path = os.path.join(os.path.dirname(trace), "results", r["action"] + ".md")
        summary = ""
        if os.path.isfile(path):
            block = re.search(r"```shiploop-state\n(.*?)\n```", open(path, errors="replace").read(), re.S)
            if block:
                try:
                    summary = (json.loads(block.group(1)).get("result") or {}).get("summary") or ""
                except ValueError:
                    pass
        if CLASS.search(summary) and TESTY.search(summary):
            hits[day] += 1
            runs_hit.add(trace)
        else:
            other[day] += 1
total_exits, total_hits, total_other = sum(exits.values()), sum(hits.values()), sum(other.values())
print("day         implement exits   proof-needs-later-test   other implement send-backs")
for day in sorted(exits):
    print("%s   %9d        %14d             %10d" % (day, exits[day], hits[day], other[day]))
print("total       %9d        %14d             %10d" % (total_exits, total_hits, total_other))
print("runs with at least one such send-back: %d" % len(runs_hit))
print("CHECK: a reading of the 28 retained implement send-backs found 21 of this class and 7 of other kinds; this "
      "recogniser finds %d and %d." % (total_hits, total_other))
