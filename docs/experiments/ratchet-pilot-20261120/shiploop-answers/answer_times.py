#!/usr/bin/env python3
"""When each delivery's answer was written, beside when its list was printed and when its run ended.

argv: ROOT ANSWERS_JSON.  ROOT holds the deliveries; ANSWERS_JSON is what ``read_answers.py --json`` wrote for them.
The list is printed in the packet issued when the spec's first result is accepted (``timeline.json``).  Prints, per
delivery with a note, the seconds from that moment to the note and the minutes the run went on after the note."""
import datetime
import glob
import json
import re
import sys

root, rows = sys.argv[1], sys.argv[2]


def when(text):
    return datetime.datetime.fromisoformat(str(text).replace(" ", "T"))


print("name | list printed | answer written | seconds from the list to the answer | run ended | "
      "minutes from the answer to the end")
with open(rows, encoding="utf-8") as handle:
    deliveries = json.load(handle)
for row in deliveries:
    if not row.get("notes"):
        continue
    run = max(glob.glob(f"{root}/{row['name']}/.shiploop-runs/*/run"))
    with open(run + "/state.md", encoding="utf-8", errors="replace") as handle:
        state = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", handle.read(), re.DOTALL).group(1))
    with open(run + "/timeline.json", encoding="utf-8") as handle:
        accepted = json.load(handle).get("accepted") or {}
    shown = min(when(accepted[entry["action"]]) for entry in state["history"]
                if entry["stage"] == "spec" and entry["action"] in accepted)
    note, end = when(row["notes"][0]["written_at"]), when(row["ended_at"])
    print(f"{row['name']} | {shown:%H:%M:%S} | {note:%H:%M:%S} | {(note - shown).total_seconds():.0f} | "
          f"{end:%H:%M:%S} | {(end - note).total_seconds() / 60:.1f}")
