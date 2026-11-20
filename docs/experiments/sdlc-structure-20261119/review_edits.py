#!/usr/bin/env python3
"""What kind of file each Improve review changed, finished current-era runs.

Before a review ShipLoop snapshots the candidate's working tree as a Git tree (run/improve/<action>-bind.md).
The first commit made after that snapshot holds the review's edits (ShipLoop commits a step once its review is
accepted, and commits docs/shiploop after other accepted stages). Diffing the snapshot against that commit's tree
names the files the review itself changed. Each path is classed with ShipLoop's own catalog
(shiploop_item_scope.classify: test, docs, config, metadata-nav, else code)."""
import collections
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, "/Users/dadleet/src/skill-craft/skills/shiploop/scripts")
import shiploop_item_scope as item_scope


def git(top, *args):
    done = subprocess.run(["git", "-C", str(top), *args], capture_output=True, text=True, check=False)
    return done.stdout if done.returncode == 0 else None

runs = [r for r in json.loads(pathlib.Path(sys.argv[1]).read_text()) if r["current_era"] and r["done"]]
rows = []
skipped = collections.Counter()
for run in runs:
    rundir = pathlib.Path(run["trace"]).parent
    worktree = rundir.parent / "worktree"
    log = git(worktree, "log", "--all", "--format=%H %ct %T %s")
    if log is None:
        skipped["no git log"] += 1
        continue
    commits = sorted((int(p[1]), p[0], p[2], p[3]) for p in (l.split(" ", 3) for l in log.splitlines()) if len(p) == 4)
    for passes in sorted((rundir / "improve").glob("nav-*/passes.md")):
        action = passes.parent.name
        table = [[c.strip() for c in l.strip().strip("|").split("|")] for l in passes.read_text().splitlines()]
        table = [c for c in table if len(c) >= 8 and c[1].isdigit()]
        if not table:
            continue
        stage = table[0][0]
        logged_tree = any(c[3] == "y" for c in table)
        bind = rundir / "improve" / f"{action}-bind.md"
        try:
            bound = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", bind.read_text(), re.DOTALL).group(1))
        except (OSError, ValueError, AttributeError, KeyError):
            skipped["no bind snapshot"] += 1
            continue
        after = next((c for c in commits if c[0] >= bind.stat().st_mtime - 1), None)
        if after is None:
            skipped["no later commit"] += 1
            rows.append({"stage": stage, "logged_tree": logged_tree, "paths": None})
            continue
        names = git(worktree, "diff-tree", "-r", "--no-renames", "--name-only", bound["tree"], after[2])
        if names is None:
            skipped["cannot diff"] += 1
            continue
        paths = [p for p in names.splitlines() if p and not p.startswith(".shiploop-improve/")]
        classes = sorted({item_scope.classify(p) for p in paths})
        rows.append({"stage": stage, "logged_tree": logged_tree, "paths": paths, "classes": classes,
                     "case": run.get("case"), "host": run.get("host"), "subject": after[3][:80], "dir": str(passes.parent)})
print("skipped:", dict(skipped))
usable = [r for r in rows if r["paths"] is not None]
agree = sum(1 for r in usable if bool(r["paths"]) == r["logged_tree"])
print(f"reviews diffed: {len(usable)}; diff agrees with ShipLoop's own 'tree changed' flag in {agree} ({agree / len(usable):.0%})")
print(f"\n{'reviewed stage':<20}{'reviews':>8}{'changed code':>14}{'changed tests':>15}{'code or tests':>15}{'docs/knowledge only':>21}{'nothing':>9}")
for stage in sorted({r["stage"] for r in usable}, key=lambda s: (-sum(1 for r in usable if r["stage"] == s), s)):
    group = [r for r in usable if r["stage"] == stage]
    n = len(group)
    code = sum("code" in r["classes"] for r in group)
    test = sum("test" in r["classes"] for r in group)
    either = sum(bool({"code", "test"} & set(r["classes"])) for r in group)
    docs = sum(bool(r["paths"]) and not ({"code", "test"} & set(r["classes"])) for r in group)
    none = sum(not r["paths"] for r in group)
    print(f"{stage:<20}{n:>8}{code / n:>14.0%}{test / n:>15.0%}{either / n:>15.0%}{docs / n:>21.0%}{none / n:>9.0%}")
pathlib.Path(sys.argv[2]).write_text(json.dumps(usable, indent=1))
