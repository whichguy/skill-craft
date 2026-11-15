"""Every host tool call of one run with its duration, and the stretches where the builder polled for a file.

    python3 -I tool_ledger.py RUN_DIR

RUN_DIR is the harness output directory. ``events.jsonl`` holds the host's tool_call / tool_call_update events and
``timeline.jsonl`` maps each event line to a wall-clock time, so a call's duration is the time of its terminal update
minus the time of its call.  Observed tool time is a floor on busy time: the rest of the run is model time between
calls (reasoning, streaming, stream retries), which this script does not measure.

A polling stretch is four or more consecutive short read-only calls (ls, tail, cat, find, stat, head, wc, test) naming a
platform, review or receipt path, each starting less than four minutes after the one before.  That is a heuristic: it
estimates how long the builder waited on files another party writes; it is not a ShipLoop measurement.
"""
import bisect
import json
import re
import sys

run = sys.argv[1]
timeline = {}
for line in open(run + "/timeline.jsonl"):
    o = json.loads(line)
    timeline[o["line"]] = o["t"]
keys = sorted(timeline)


def t_at(i):
    j = bisect.bisect_right(keys, i) - 1
    return timeline[keys[j]] if j >= 0 else None


calls, order = {}, []
with open(run + "/events.jsonl", encoding="utf-8", errors="replace") as f:
    for i, line in enumerate(f):
        try:
            o = json.loads(line)
        except Exception:
            continue
        kind = o.get("type")
        if kind == "tool_call":
            raw = o.get("rawInput") or {}
            calls[o["toolCallId"]] = {"name": o.get("toolName"),
                                      "cmd": raw.get("command") if isinstance(raw, dict) else None,
                                      "t0": t_at(i)}
            order.append(o["toolCallId"])
        elif kind == "tool_call_update" and o.get("status") in ("completed", "failed"):
            if o.get("toolCallId") in calls:
                calls[o["toolCallId"]]["t1"] = t_at(i)

done = [calls[c] for c in order if calls[c].get("t0") and calls[c].get("t1")]
total = sum(c["t1"] - c["t0"] for c in done)
print("tool calls: %d   observed tool time: %.1f min" % (len(done), total / 60))


def inner(cmd):
    if not cmd:
        return ""
    m = re.match(r"^/bin/(?:zsh|bash|sh) -lc (.*)$", cmd, re.S)
    s = m.group(1) if m else cmd
    return s.strip().strip("\"'").replace('\\"', '"')


def is_poll(s):
    if "<<" in s or ">" in s.replace("2>&1", "").replace("2>/dev/null", ""):
        return False
    return bool(re.match(r"^(ls|tail|stat|test|find|cat|head|wc)\b", s.strip()))


terminal = [(c, inner(c["cmd"])) for c in done if c["name"] == "run_terminal_command"]
episodes, cur = [], []
for c, s in terminal:
    fast = (c["t1"] - c["t0"]) < 5
    poll = is_poll(s) and fast and re.search(r"platform/|sf-callout|/review|receipt|request\.json|status\.json|trace", s)
    if poll:
        if cur and c["t0"] - cur[-1][0]["t1"] > 240:
            episodes.append(cur)
            cur = []
        cur.append((c, s))
    elif cur and c["t0"] - cur[-1][0]["t1"] > 240:
        episodes.append(cur)
        cur = []
if cur:
    episodes.append(cur)
t_first = done[0]["t0"]
polls = wall = 0
print("\npolling stretches (>= 4 polls):")
for ep in episodes:
    if len(ep) < 4:
        continue
    span = ep[-1][0]["t1"] - ep[0][0]["t0"]
    polls += len(ep)
    wall += span
    print("  starts +%4.0f min  %3d polls  spans %5.1f min" % ((ep[0][0]["t0"] - t_first) / 60, len(ep), span / 60))
print("TOTAL %d poll calls spanning %.1f min of wall clock" % (polls, wall / 60))
