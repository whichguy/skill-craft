#!/usr/bin/env python3
"""Two free cuts behind the plan review of round 9: how builders stop processes, and what each spec decided.

  A  For every run folder under the given roots: whether its events hold a `pkill` or `killall` command (a stop by
     name or pattern) and whether they hold a `kill` aimed at a process id. By driver, read from the folder name.
  B  For every Sol whole delivery of `ticket-due-times` under the roots: its held-out checks, and the lines of its
     `docs/shiploop/spec.md` that say how tickets already in the data file get their due times. The reader, not this
     script, says which reading a line takes; the lines are printed so that anyone can.

Usage: python3 -I plan_review_cuts.py ROOT [ROOT ...]
"""
import collections
import json
import pathlib
import re
import sys

BY_NAME = re.compile(r"\b(pkill|killall)\b")
BY_PID = re.compile(r"\bkill (-[A-Z0-9]+ )?(\$[A-Za-z_{(]|\"?\$\(cat|[0-9]{3,})")
SPEC_LINE = re.compile(r"(backfill|back-fill|migrat|missing due|lacks? a due|without a due|data file)", re.IGNORECASE)
HOW = re.compile(r"(start|serv|stopp|offline|operator|maintenance|before|command|npm run|script)", re.IGNORECASE)


def driver_of(name):
    return "sonnet" if "sonnet" in name else "grok" if "grok" in name else "sol" if "sol" in name else "other"


def main(roots):
    folders = [f for root in roots for f in sorted(pathlib.Path(root).iterdir()) if (f / "events.jsonl").exists()]
    counts = collections.defaultdict(lambda: [0, 0, 0])
    named = []
    for folder in folders:
        text = (folder / "events.jsonl").read_text(errors="replace")
        row = counts[driver_of(folder.name)]
        row[0] += 1
        if BY_NAME.search(text):
            row[1] += 1
            named.append(folder.name)
        row[2] += bool(BY_PID.search(text))
    print(f"== A. how builders stop processes ({len(folders)} run folders) ==")
    print(f"  {'driver':<8}{'runs':>6}{'stop by name or pattern':>26}{'kill by a process id':>22}")
    for driver, (runs, by_name, by_pid) in sorted(counts.items()):
        print(f"  {driver:<8}{runs:>6}{by_name:>26}{by_pid:>22}")
    print("  runs with a stop by name or pattern: " + ", ".join(named))

    print("\n== B. what each Sol spec of ticket-due-times says about tickets already on file ==")
    for folder in folders:
        if driver_of(folder.name) != "sol" or "due" not in folder.name or not (folder / "result.json").exists():
            continue
        specs = list(folder.glob(".shiploop-runs/*/worktree/docs/shiploop/spec.md"))
        if not specs or "plan" in folder.name:
            continue
        checks = json.loads((folder / "result.json").read_text()).get("checks") or []
        if len(checks) != 8:
            continue
        lines = [line.strip() for line in specs[0].read_text(errors="replace").splitlines()
                 if SPEC_LINE.search(line) and HOW.search(line) and "due" in line.lower()]
        lines.sort(key=lambda line: -len(re.findall(r"backfill|back-fill|migrat", line, re.IGNORECASE)))
        print(f"  {folder.name}: held-out {sum(bool(c.get('pass')) for c in checks)} of 8")
        for line in lines[:2]:
            print(f"      {line[:230]}")


if __name__ == "__main__":
    main(sys.argv[1:])
