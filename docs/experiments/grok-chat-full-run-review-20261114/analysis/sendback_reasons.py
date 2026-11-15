"""What the model said when an implement or test stage sent its plan back, across the retained runs.

    python3 -I sendback_reasons.py TRACE_LIST

TRACE_LIST names one ShipLoop ``trace.jsonl`` per line.  A send-back is the same event sendback_base.py counts: a
``complete`` that exited 0 and moved an implement or test action back to step-plan, test-spec or plan.  (An earlier version also
counted test -> implement, which is the next step of a multi-step item, not a send-back: its headlines read "Revalidated
controller tests".)  The model's explanation is the ``headline`` and ``summary`` of its submitted result,
``results/<action>.md`` beside the trace.  Nothing is classified here: the explanations are printed for a reader.
"""
import datetime
import json
import os
import re
import sys

cut = datetime.datetime(2026, 10, 29, 15, 0).timestamp()
files = [line.strip() for line in open(sys.argv[1]) if line.strip()]
found = []
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
        if not (isinstance(stage, list) and len(stage) == 2):
            continue
        a, b = stage
        if a not in ("implement", "test"):
            continue
        if b in ("step-plan", "test-spec", "plan"):
            found.append((trace, r["action"], a, b))


def explanation(trace, action):
    for folder in ("results", "inbox"):
        path = os.path.join(os.path.dirname(trace), folder, action + ".md")
        if not os.path.isfile(path):
            continue
        block = re.search(r"```shiploop-state\n(.*?)\n```", open(path, errors="replace").read(), re.S)
        if not block:
            continue
        try:
            result = json.loads(block.group(1)).get("result") or {}
        except ValueError:
            continue
        return (result.get("headline") or "").strip(), (result.get("summary") or "").strip()
    return None, None


print("send-backs at implement or test since 2026-10-29:", len(found), " (implement %d, test %d)" % (
    sum(1 for f in found if f[2] == "implement"), sum(1 for f in found if f[2] == "test")))
missing = 0
for n, (trace, action, a, b) in enumerate(found, 1):
    headline, summary = explanation(trace, action)
    run = "/".join(os.path.dirname(trace).replace(os.path.expanduser("~"), "~").split("/")[1:4])
    if headline is None:
        missing += 1
        print("%2d  %s -> %s  [%s]  (no result file)" % (n, a, b, run))
        continue
    text = "%2d  %s -> %s  [%s]\n    H: %s\n    S: %s" % (n, a, b, run, headline[:170], re.sub(r"\s+", " ", summary)[:330])
    print("\n".join(line.rstrip() for line in text.splitlines()))
print("\nwithout a readable result file:", missing)
