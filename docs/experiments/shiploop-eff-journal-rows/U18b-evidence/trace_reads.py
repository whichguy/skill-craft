"""Run 4's Improve-file reads, in order, grouped by the Improve stage whose handoff was read (read-only on the run folder).

Prints a markdown table: stage, then each read of the route card, the Improve SKILL.md and improve-context.md, with its
line window (offset:limit as the host's read_file got them; "whole" when neither was given), plus the result bytes the host
returned when the event stream holds them.
"""
import json
import re
import sys
from collections import OrderedDict

EVENTS = "/Users/dadleet/e2e-runs/20261020/chess-sf-full-9e52e8/events.jsonl"
WATCH = ("skills/improve/references/shiploop-route.md", "skills/improve/SKILL.md",
         "skills/shiploop/references/improve-context.md")

calls = OrderedDict()
order = []
with open(EVENTS, encoding="utf-8") as handle:
    for line in handle:
        if '"read_file"' not in line and '"tool_call_update"' not in line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        ident = event.get("toolCallId")
        if event.get("type") == "tool_call" and event.get("toolName") == "read_file" and event.get("status") == "pending":
            raw = event.get("rawInput") or {}
            calls[ident] = {"path": raw.get("target_file", ""), "offset": raw.get("offset"), "limit": raw.get("limit"),
                            "bytes": None}
            order.append(ident)
        elif ident in calls and event.get("type") in ("tool_call_update", "tool_call"):
            content = event.get("content")      # what the model saw (rawOutput is the host's wrapper of it)
            if content is not None and event.get("status") in ("completed", "failed"):
                calls[ident]["bytes"] = len(json.dumps(content))

stage = None
rows = []
for ident in order:
    call = calls[ident]
    path = call["path"]
    match = re.search(r"\.shiploop-improve/([a-z-]+-[0-9a-f]{8})/handoff\.md$", path)
    if match:
        stage = match.group(1)
        rows.append((stage, "handoff.md", call))
        continue
    for watched in WATCH:
        if path.endswith(watched) and stage is not None:
            rows.append((stage, watched.split("/")[-1] if "SKILL" not in watched else "improve/SKILL.md", call))

print("| Improve stage (child dir) | file | window (offset:limit) | result bytes (JSON) |")
print("|---|---|---|---|")
for stage, name, call in rows:
    window = ("whole" if call["offset"] is None and call["limit"] is None
              else str(call["offset"] or 1) + ":" + str(call["limit"] or "end"))
    print("| " + stage + " | " + name + " | " + window + " | " + (str(call["bytes"]) if call["bytes"] else "n/a") + " |")
route = [call for _stage, name, call in rows if name == "shiploop-route.md"]
print()
print("route reads:", len(route), "result bytes:", sum(call["bytes"] or 0 for call in route), file=sys.stderr)
