"""The largest tool outputs of one run, with the minute each ran at and its command.

    python3 -I big_outputs.py RUN_DIR

RUN_DIR is the harness output directory.  ``events.jsonl`` holds the host's tool calls and their outputs and
``timeline.jsonl`` maps each event line to a wall-clock time.  A tool output's size is the larger of its content text and
its ``output_for_prompt``, in bytes; a byte is not a token (about four bytes to a token for code and logs), so this says
what filled the context, not what it cost.
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


calls = {}
with open(run + "/events.jsonl", encoding="utf-8", errors="replace") as handle:
    for i, line in enumerate(handle):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        kind = o.get("type")
        if kind == "tool_call":
            raw = o.get("rawInput") or {}
            command = raw.get("command") if isinstance(raw, dict) else None
            calls[o["toolCallId"]] = {"cmd": command or o.get("title"), "t0": t_at(i), "bytes": 0}
        elif kind == "tool_call_update" and o.get("toolCallId") in calls:
            size = 0
            for part in o.get("content") or []:
                inner = part.get("content") if isinstance(part, dict) else None
                if isinstance(inner, dict):
                    size += len((inner.get("text") or "").encode("utf-8", "replace"))
            output = o.get("rawOutput")
            if isinstance(output, dict):
                size = max(size, len((output.get("output_for_prompt") or "").encode("utf-8", "replace")))
            calls[o["toolCallId"]]["bytes"] = max(calls[o["toolCallId"]]["bytes"], size)

t_first = timeline[keys[0]]
ranked = sorted(calls.values(), key=lambda c: -c["bytes"])
total = sum(c["bytes"] for c in ranked)
print("tool calls %d; total tool-output bytes %s" % (len(calls), format(total, ",")))
for c in ranked[:10]:
    command = re.sub(r"\s+", " ", c["cmd"] or "")[:150]
    print("%9s B  +%5.0f min  %s" % (format(c["bytes"], ","), (c["t0"] - t_first) / 60, command))
top2 = sum(c["bytes"] for c in ranked[:2])
print("top 2 together: %s (%.1f%% of tool-output bytes)" % (format(top2, ","), top2 / total * 100))
