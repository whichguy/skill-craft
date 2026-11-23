#!/usr/bin/env python3
"""Read-only: split the ShipLoop >= 2.4 runs of scan_spec_after_plan.json by engine (main or a candidate branch).

An engine is "main" when the run's invocation.json records source "plugin" (a released install) or a local_head that
`git merge-base --is-ancestor` finds on main of the skill-craft checkout given as argv[2].  For each group: runs, runs
with a post-plan spec.md commit that removed or changed a line, by stage, and the same for lines that are not
traceability lines (classify_removed_lines.kind).  Usage:
    python3 engine_split.py scan_spec_after_plan.json /Users/dadleet/src/skill-craft
"""
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify_removed_lines import SPEC, kind, minor  # noqa: E402


def engine(folder, repo):
    try:
        versions = json.load(open(Path(folder) / "invocation.json")).get("versions") or {}
    except (OSError, ValueError):
        return "unknown"
    if versions.get("source") != "checkout":
        return "main"
    head = versions.get("local_head")
    if not head:
        return "unknown"
    done = subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", head, "main"], capture_output=True)
    return "main" if done.returncode == 0 else "candidate"


def main():
    rows = json.load(open(sys.argv[1]))
    repo = sys.argv[2]
    groups = defaultdict(lambda: {"runs": 0, "any": Counter(), "intent": Counter(), "intent_runs": set()})
    for row in rows:
        if not row.get("has_boundary") or minor(row.get("shiploop")) < (2, 4):
            continue
        group = groups[engine(row["folder"], repo)]
        group["runs"] += 1
        stages_any, stages_intent = set(), set()
        for commit in row["post_plan"]:
            if not commit["removed"]:
                continue
            stages_any.add(commit["stage"])
            diff = subprocess.run(["git", "-C", row["folder"] + "/work", "show", "--format=", "--unified=0",
                                   commit["commit"], "--", SPEC], capture_output=True, text=True,
                                  errors="replace").stdout
            removed = [line[1:] for line in diff.splitlines()
                       if line.startswith("-") and not line.startswith("---") and line[1:].strip()]
            if any(kind(line) != "trace" for line in removed):
                stages_intent.add(commit["stage"])
        for stage in stages_any:
            group["any"][stage] += 1
        for stage in stages_intent:
            group["intent"][stage] += 1
        if stages_intent:
            group["intent_runs"].add(row["folder"])
    for name, group in sorted(groups.items()):
        print(name, "runs:", group["runs"])
        print("   runs with a removed or changed spec line after the plan, by stage:", dict(group["any"]))
        print("   ... where a removed line is not a traceability line, by stage:", dict(group["intent"]))
        print("   ... such runs:", sorted(path.replace(str(Path.home()) + "/", "~/") for path in group["intent_runs"]))


if __name__ == "__main__":
    main()
