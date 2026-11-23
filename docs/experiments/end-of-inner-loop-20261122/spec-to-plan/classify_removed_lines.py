#!/usr/bin/env python3
"""Read-only: classify each spec.md line removed or changed after the plan, in runs of ShipLoop 2.4 and later.

Input: the JSON that scan_spec_after_plan.py wrote.  For each post-plan commit with a removed line, reread its diff of
docs/shiploop/spec.md (git show only) and sort each removed, non-blank line into:

- trace: a traceability line, the kind a step or carry-forward writes about where a requirement is met: it starts with
  Met, Observed, Implemented, Pending, Verified, Satisfied, Status, Covered, Checked, Confirmed or Tested (after a
  list marker), or ends with a step mark such as (W1/S1);
- heading: a Markdown heading line (an R-<n> heading rewritten counts here);
- other: anything else, usually a requirement or acceptance sentence.

Prints per stage the counts, and every "other" and "heading" line of each commit (cut to 220 characters), so a reader
can judge which changed what a requirement asks.  Usage:
    python3 classify_removed_lines.py scan_spec_after_plan.json > classify_removed_lines.txt
"""
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict

SPEC = "docs/shiploop/spec.md"
TRACE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?(?:\*\*|_)?(?:Met|Observed|Implemented|Pending|Verified|Satisfied|"
                   r"Status|Covered|Checked|Confirmed|Tested|Proved|Shown)\b", re.I)
MARK = re.compile(r"\((?:W[^/()\s]+)/(?:S[^()\s]+)\)[.;]?\s*$")
HEADING = re.compile(r"^\s*#{1,6}\s")


def minor(version):
    parts = str(version or "?").split(".")
    try:
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return 0, 0


def kind(line):
    if HEADING.match(line):
        return "heading"
    if TRACE.match(line) or MARK.search(line):
        return "trace"
    return "other"


def main():
    rows = json.load(open(sys.argv[1]))
    counts = defaultdict(Counter)
    commits_with_other = Counter()
    for row in rows:
        if not row.get("has_boundary") or minor(row.get("shiploop")) < (2, 4):
            continue
        repo = row["folder"] + "/work"
        for commit in row["post_plan"]:
            if not commit["removed"]:
                continue
            diff = subprocess.run(["git", "-C", repo, "show", "--format=", "--unified=0", commit["commit"], "--", SPEC],
                                  capture_output=True, text=True, errors="replace", timeout=60).stdout
            removed = [line[1:] for line in diff.splitlines()
                       if line.startswith("-") and not line.startswith("---") and line[1:].strip()]
            sorted_lines = defaultdict(list)
            for line in removed:
                sorted_lines[kind(line)].append(line)
                counts[commit["stage"]][kind(line)] += 1
            if sorted_lines["other"] or sorted_lines["heading"]:
                commits_with_other[commit["stage"]] += 1
                print("==", commit["stage"], "|", row.get("shiploop"), row.get("host"), "|",
                      row["folder"].replace("/Users/dadleet/", "~/"), "|", commit["commit"][:12], "|",
                      commit["subject"][:90])
                for label in ("heading", "other"):
                    for line in sorted_lines[label]:
                        print("   ", label, "-", line.strip()[:220])
    print()
    print("removed or changed lines by stage and kind (ShipLoop >= 2.4):")
    for stage, found in sorted(counts.items()):
        print("  ", stage, dict(found))
    print("commits with a removed heading or other line, by stage:", dict(commits_with_other))


if __name__ == "__main__":
    main()
