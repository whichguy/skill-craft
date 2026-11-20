#!/usr/bin/env python3
"""Which files do the steps of one item all write? For items with two or more committed steps: the share of the
item's step commits that touch each file, grouped by kind, and how many test files an item's steps write.

Usage: python3 -I shared_files.py <work>/census.json
"""
import collections
import json
import pathlib
import re
import statistics
import subprocess
import sys

sys.path.insert(0, "/Users/dadleet/src/skill-craft/skills/shiploop/scripts")
import shiploop_item_scope as item_scope

runs = [r for r in json.loads(pathlib.Path(sys.argv[1]).read_text()) if r["current_era"] and r["done"]]

def git(top, *args):
    done = subprocess.run(["git", "-C", str(top), *args], capture_output=True, text=True, errors="replace", check=False)
    return done.stdout if done.returncode == 0 else None

def kind(path):
    return "knowledge home" if path.startswith("docs/shiploop/") else item_scope.classify(path)

items = 0
every_step = collections.Counter()      # items in which some file of this kind is written by EVERY step
test_files = []
one_test_file_shared = 0
for run in runs:
    worktree = pathlib.Path(run["trace"]).parent.parent / "worktree"
    log = git(worktree, "log", "--all", "--format=%H%x09%s")
    if log is None:
        continue
    by_item = collections.defaultdict(dict)
    for line in log.splitlines():
        sha, _, subject = line.partition("\t")
        match = re.match(r"\w+\((W\d+|[\w-]+)/(S\d+)\)", subject)
        if match:
            by_item[match.group(1)].setdefault(match.group(2), sha)
    for steps in by_item.values():
        if len(steps) < 2:
            continue
        written = []
        for sha in steps.values():
            names = git(worktree, "diff-tree", "-r", "--no-renames", "--name-only", "--no-commit-id", sha) or ""
            written.append({p for p in names.splitlines() if p and p != ".gitignore"})
        items += 1
        common = set.intersection(*written)
        for name in {kind(p) for p in common}:
            every_step[name] += 1
        tests = {p for paths in written for p in paths if kind(p) == "test"}
        test_files.append(len(tests))
        one_test_file_shared += any(kind(p) == "test" for p in common)
print(f"items with two or more committed steps: {items}")
print("items in which EVERY step's commit writes the same file, by kind of that file:")
for name, count in every_step.most_common():
    print(f"  {name:<16}{count:>4} ({count / items:.0%})")
print(f"test files written across an item's steps: median {statistics.median(test_files)}, "
      f"distribution { {n: test_files.count(n) for n in sorted(set(test_files))} }")
print(f"items where every step writes one and the same test file: {one_test_file_shared} ({one_test_file_shared / items:.0%})")
