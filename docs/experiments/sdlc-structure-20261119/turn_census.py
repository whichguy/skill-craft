#!/usr/bin/env python3
"""What the model's turns are spent on in a recorded run, by kind of command.

Each tool call in the host's command stream (events.jsonl with timeline.jsonl) is charged the seconds from the end of
the call before it to its own end: the model's time deciding and writing the call, plus the call itself. Calls are
classed by what they touch:

  loop      the Until Loop runtime (start, done, next)
  callback  a ShipLoop command that submits or checks a result (complete, check, red-check, improve-*)
  packet    a ShipLoop command that fetches or records (next, status, context, note, lint, view, trace, workspace)
  records   reading or writing files of the run folder (packets, result drafts, notes, loop files)
  guides    reading the skill's own files (the reference guides a packet points at)
  review notes  reading or writing a review's scratch folder (.shiploop-improve/)
  knowledge reading or writing the knowledge home, docs/shiploop/ (spec, architecture, environment)
  tests     running the product's tests
  product   everything else: reading, editing and running the product

Codex runs recorded before its adapter reported file edits show only shell commands: the time the model spent writing a
file is then charged to the next visible command, usually a callback. Read those rows as an upper bound for `callback`
and a lower bound for `product` and `records`; the Grok rows and the Codex rows that list edits do not have this bias.

Usage: python3 -I turn_census.py CENSUS.json [--all]   (--all also reads runs that did not finish, such as slices)
"""
import collections
import json
import pathlib
import sys

import iteration_census as base

SUBMIT = {"complete", "check", "red-check", "improve-pass", "improve-commit", "improve-start", "improve-bind",
          "improve-reconcile"}
KINDS = ("loop", "callback", "packet", "records", "guides", "review notes", "knowledge", "tests", "product")


def kind(call):
    text = call["command"]
    if "until_loop" in text:
        return "loop"
    verb = base.SHIPLOOP.search(text)
    if verb:
        return "callback" if verb.group(1) in SUBMIT else "packet"
    if base.TEST_RUN.search(text) and "--help" not in text:
        return "tests"
    if "/docs/shiploop/" in text or text.startswith("docs/shiploop/"):
        return "knowledge"
    if "/skills/shiploop/" in text or "/skills/improve/" in text:
        return "guides"
    if "/.shiploop-improve/" in text:
        return "review notes"
    if "/.shiploop-runs/" in text and "/worktree" not in text:
        return "records"
    return "product"


def main(census, everything=False):
    runs = [r for r in json.loads(pathlib.Path(census).read_text()) if r["current_era"] and (r["done"] or everything)]
    groups = collections.defaultdict(lambda: {"runs": 0, "seconds": collections.Counter(), "calls": collections.Counter()})
    for run in runs:
        calls = base.commands(pathlib.Path(run["folder"]))
        if not calls:
            continue
        edits = "edits listed" if any(c["tool"] in base.EDIT_TOOLS for c in calls) else "edits not listed"
        group = groups[(run.get("host"), run.get("model"), run.get("effort") or "-", edits)]
        group["runs"] += 1
        previous = calls[0]["t"]
        for call in calls:
            end = call["end"] or call["t"]
            spent = end - previous
            previous = max(previous, end)
            if spent > 45 * 60 or spent < 0:
                continue
            label = kind(call)
            group["seconds"][label] += spent
            group["calls"][label] += 1
    print(f"{'host model effort':<44}{'runs':>5}  " + "".join(f"{k:>13}" for k in KINDS) + "   (share of the model's time; calls per run below)")
    for key, group in sorted(groups.items(), key=lambda pair: -pair[1]["runs"]):
        total = sum(group["seconds"].values()) or 1.0
        print(f"{' '.join(key):<44}{group['runs']:>5}  " + "".join(f"{group['seconds'][k] / total:>13.0%}" for k in KINDS))
        print(f"{'':<44}{'':>5}  " + "".join(f"{group['calls'][k] / group['runs']:>13.0f}" for k in KINDS))


if __name__ == "__main__":
    main(sys.argv[1], "--all" in sys.argv)
