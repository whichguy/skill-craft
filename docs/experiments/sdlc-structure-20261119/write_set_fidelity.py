#!/usr/bin/env python3
"""Do the files a step plan declares for each step predict what the step's commit changes?

For every finished current-era run: read the accepted step plan(s) (`steps[].paths`, `steps[].deps`), find each
step's commit in the run's worktree by its subject (`<type>(<item>/<step>): ...`), and compare the commit's changed
paths with the step's declared paths. Then, for pairs of steps of one item that the plan makes independent (no
dependency path) and file-disjoint (no declared path in common), check whether their commits share a file.

Usage: python3 -I write_set_fidelity.py <work>/census.json
"""
import collections
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, "/Users/dadleet/src/skill-craft/skills/shiploop/scripts")
import shiploop_item_scope as item_scope

runs = [r for r in json.loads(pathlib.Path(sys.argv[1]).read_text()) if r["current_era"] and r["done"]]

def git(top, *args):
    done = subprocess.run(["git", "-C", str(top), *args], capture_output=True, text=True, errors="replace", check=False)
    return done.stdout if done.returncode == 0 else None

def kind(path):
    if path.startswith("docs/shiploop/"):
        return "knowledge home"
    return item_scope.classify(path)

def covered(path, declared):
    return any(path == d or path.startswith(d.rstrip("/") + "/") for d in declared)

steps_seen = within = 0
extra_kinds = collections.Counter()     # step commits with at least one undeclared path of this kind
extra_code_or_test = 0
pairs = pairs_share = 0
pair_kinds = collections.Counter()
pairs_share_beyond_docs = 0
plans_used = 0
for run in runs:
    trace = pathlib.Path(run["trace"])
    worktree = trace.parent.parent / "worktree"
    stage_of = {}
    for line in trace.read_text().splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        for accepted in row.get("accepted") or []:
            stage_of[accepted["action"]] = (accepted["stage"], accepted.get("item"))
    try:
        state = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", trace.with_name("state.md").read_text(), re.DOTALL).group(1))
    except (OSError, ValueError, AttributeError):
        continue
    log = git(worktree, "log", "--all", "--format=%H%x09%s")
    if log is None:
        continue
    commits = {}
    for line in log.splitlines():
        sha, _, subject = line.partition("\t")
        match = re.match(r"\w+\((W\d+|[\w-]+)/(S\d+)\)", subject)
        if match:
            commits.setdefault((match.group(1), match.group(2)), sha)
    for action, result in (state.get("accepted") or {}).items():
        stage, item = stage_of.get(action, (None, None))
        if stage != "step-plan" or not isinstance(result.get("steps"), list):
            continue
        plans_used += 1
        steps = [s for s in result["steps"] if isinstance(s, dict)]
        actual, declared, ancestors = {}, {}, {}
        for step in steps:
            sha = commits.get((item, step.get("id")))
            if not sha:
                continue
            names = git(worktree, "diff-tree", "-r", "--no-renames", "--name-only", "--no-commit-id", sha)
            if names is None:
                continue
            changed = {p for p in names.splitlines() if p and p != ".gitignore" and not p.startswith(".shiploop-improve/")}
            actual[step["id"]] = changed
            declared[step["id"]] = set(step.get("paths") or [])
            steps_seen += 1
            extra = {p for p in changed if not covered(p, declared[step["id"]])}
            within += not extra
            kinds = {kind(p) for p in extra}
            for name in kinds:
                extra_kinds[name] += 1
            extra_code_or_test += bool(kinds & {"code", "test"})
        for step in steps:
            acc = set()
            for dep in step.get("deps") or []:
                acc |= {dep} | ancestors.get(dep, set())
            ancestors[step["id"]] = acc
        ids = [s["id"] for s in steps if s["id"] in actual]
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                one, two = ids[a], ids[b]
                if one in ancestors.get(two, set()) or two in ancestors.get(one, set()):
                    continue
                if declared[one] & declared[two]:
                    continue
                pairs += 1
                shared = actual[one] & actual[two]
                if shared:
                    pairs_share += 1
                    kinds = {kind(p) for p in shared}
                    for name in kinds:
                        pair_kinds[name] += 1
                    pairs_share_beyond_docs += bool(kinds - {"knowledge home", "docs"})
print(f"step plans read {plans_used}; step commits matched to a planned step {steps_seen}")
print(f"step commits that changed only paths the step declared: {within} ({within / steps_seen:.0%})")
print("step commits with an undeclared path, by kind of that path (a commit can count in several):")
for name, count in extra_kinds.most_common():
    print(f"  {name:<16}{count:>5} ({count / steps_seen:.0%})")
print(f"step commits with an undeclared CODE or TEST path: {extra_code_or_test} ({extra_code_or_test / steps_seen:.0%})")
print(f"\npairs of steps the plan makes independent and file-disjoint, both committed: {pairs}")
if pairs:
    print(f"  whose commits nevertheless share a file: {pairs_share} ({pairs_share / pairs:.0%})")
    print(f"  ... sharing something other than documents and the knowledge home: {pairs_share_beyond_docs} ({pairs_share_beyond_docs / pairs:.0%})")
    print("  kinds of shared file:", ", ".join(f"{k} {v}" for k, v in pair_kinds.most_common()))
