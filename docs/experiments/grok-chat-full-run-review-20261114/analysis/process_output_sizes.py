"""The size of the largest ps, lsof or pgrep output in each retained run whose host events record tool outputs.

    python3 -I process_output_sizes.py

Reads every ~/e2e-runs and ~/e2e-runs-sp events.jsonl over 100 KB.  Runs whose host writes tool_call / tool_call_update
events (Codex and Grok) give each command and its output text; runs of the other host shape are counted as unread, never as
zero.  A byte is not a token (about four bytes to a token for logs).  The census in process_census.sh counts the runs that
ran such a command at all; this measures how much one of them printed.
"""
import json
import os
import re

LOOSE = re.compile(r"(\bps -|\bps aux|\blsof\b|\bpgrep\b)")
roots = [os.path.expanduser("~/e2e-runs"), os.path.expanduser("~/e2e-runs-sp")]
# os.walk, not glob: glob's ** skips hidden directories, which hold a third of the retained events files
files = sorted(os.path.join(folder, name) for root in roots for folder, _dirs, names in os.walk(root) for name in names
               if name == "events.jsonl" and os.path.getsize(os.path.join(folder, name)) > 100_000)
unread = scanned = with_command = 0
maxima = []
for path in files:
    ids = {}
    biggest = 0
    seen_call = False
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if '"tool_call' not in line:
                continue
            try:
                o = json.loads(line)
            except ValueError:
                continue
            kind = o.get("type")
            if kind == "tool_call":
                seen_call = True
                raw = o.get("rawInput") or {}
                command = raw.get("command") if isinstance(raw, dict) else None
                if isinstance(command, str) and LOOSE.search(command):
                    ids[o["toolCallId"]] = command
            elif kind == "tool_call_update" and o.get("toolCallId") in ids:
                size = 0
                for part in o.get("content") or []:
                    inner = part.get("content") if isinstance(part, dict) else None
                    if isinstance(inner, dict):
                        size += len((inner.get("text") or "").encode("utf-8", "replace"))
                output = o.get("rawOutput")
                if isinstance(output, dict):
                    size = max(size, len((output.get("output_for_prompt") or "").encode("utf-8", "replace")))
                biggest = max(biggest, size)
    if not seen_call:
        unread += 1
        continue
    scanned += 1
    if ids:
        with_command += 1
        maxima.append((biggest, path))
maxima.sort(reverse=True)
print("event files over 100 KB: %d; read (tool_call shape): %d; not read (other shape): %d" % (len(files), scanned, unread))
print("read runs with a ps, lsof or pgrep command: %d" % with_command)
for floor in (10_000, 50_000, 100_000, 200_000):
    print("  largest such output at least %7s bytes: %d runs" % (format(floor, ","), sum(1 for size, _ in maxima if size >= floor)))
print("largest five:")
for size, path in maxima[:5]:
    print("  %9s B  %s" % (format(size, ","), path.replace(os.path.expanduser("~"), "~")[-90:]))
