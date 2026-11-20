#!/usr/bin/env python3
"""Collect what planning reviews actually changed, as diffs, for judging.

Tree edits (spec, test-strategy, plan, release-plan): `git diff <pre-review snapshot tree> <tree of the first commit
after it>`, limited to reviews ShipLoop's pass log flags as having changed files.
Result edits (step-plan, plan): unified diff of the stage result before the review
(run/improve/<action>-bind-result.json) and the accepted result in state.md, bookkeeping keys left out."""
import collections
import difflib
import json
import pathlib
import random
import re
import subprocess
import sys

S = pathlib.Path(sys.argv[1])
rows = json.loads(pathlib.Path(S / "review_edits.json").read_text())
BOOKKEEPING = {"evidence_refs", "check_refs", "review_refs", "lessons", "no_commit", "headline", "summary"}

def git(top, *args):
    done = subprocess.run(["git", "-C", str(top), *args], capture_output=True, text=True, errors="replace", check=False)
    return done.stdout if done.returncode == 0 else None

def state_of(rundir):
    return json.loads(re.search(r"```shiploop-state\n(.*?)\n```", (rundir / "state.md").read_text(), re.DOTALL).group(1))

items = []
states = {}
for row in rows:
    folder = pathlib.Path(row["dir"]); action = folder.name; rundir = folder.parent.parent
    stage = row["stage"]
    table = [[c.strip() for c in l.strip().strip("|").split("|")] for l in (folder / "passes.md").read_text().splitlines()]
    table = [c for c in table if len(c) >= 8 and c[1].isdigit()]
    result_changed = any(c[4] == "y" for c in table)
    parts = []
    if stage in ("spec", "test-strategy", "plan", "release-plan") and row["logged_tree"] and row["paths"]:
        bound = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", (rundir / "improve" / f"{action}-bind.md").read_text(), re.DOTALL).group(1))
        worktree = rundir.parent / "worktree"
        log = git(worktree, "log", "--all", "--format=%ct %T") or ""
        commits = sorted((int(a), b) for a, b in (l.split() for l in log.splitlines()))
        mtime = (rundir / "improve" / f"{action}-bind.md").stat().st_mtime
        after = next((t for ct, t in commits if ct >= mtime - 1), None)
        if after:
            diff = git(worktree, "diff", "-U1", "--no-color", bound["tree"], after, "--", *[p for p in row["paths"] if not p.startswith(".git")])
            if diff:
                keep = [l for l in diff.splitlines() if not l.startswith(("diff --git", "index ", "new file", "deleted file"))]
                parts.append("FILE EDITS:\n" + "\n".join(keep))
    if stage in ("step-plan", "plan", "release-plan") and result_changed:
        seed_path = rundir / "improve" / f"{action}-bind-result.json"
        if seed_path.exists():
            if rundir not in states:
                try:
                    states[rundir] = state_of(rundir)
                except (OSError, ValueError, AttributeError, KeyError):
                    states[rundir] = {}
            final = (states[rundir].get("accepted") or {}).get(action)
            try:
                seed = json.loads(seed_path.read_text())
            except ValueError:
                seed = None
            if isinstance(seed, dict) and isinstance(final, dict):
                def text(value):
                    return json.dumps({k: v for k, v in value.items() if k not in BOOKKEEPING}, indent=1, sort_keys=True, ensure_ascii=False).splitlines()
                delta = [l for l in difflib.unified_diff(text(seed), text(final), lineterm="", n=1) if not l.startswith(("---", "+++"))]
                if delta:
                    parts.append("STAGE RESULT EDITS (JSON, bookkeeping fields left out):\n" + "\n".join(delta))
    if parts:
        body = "\n\n".join(parts)
        items.append({"stage": stage, "case": row.get("case"), "host": row.get("host"), "action": action,
                      "chars": len(body), "diff": body})
by = collections.defaultdict(list)
for item in items:
    by[item["stage"]].append(item)
print("reviews with a recoverable diff:", {k: len(v) for k, v in by.items()})
print("median diff chars:", {k: sorted(i["chars"] for i in v)[len(v) // 2] for k, v in by.items()})
random.seed(20261119)
picked = []
for stage, group in by.items():
    group = sorted(group, key=lambda i: i["action"])
    picked += group if len(group) <= 40 else random.sample(group, 40)
random.shuffle(picked)
CAP = 5000
key = []
out = []
for n, item in enumerate(picked, 1):
    ident = f"D{n:03d}"
    body = item["diff"] if len(item["diff"]) <= CAP else item["diff"][:CAP] + f"\n[... cut: {len(item['diff']) - CAP} more characters of this diff ...]"
    out.append(f"=== {ident} | review of the `{item['stage']}` stage ===\n{body}")
    key.append({"item": ident, "stage": item["stage"], "case": item["case"], "host": item["host"], "action": item["action"], "chars": item["chars"]})
(S / "judge").mkdir(exist_ok=True)
(S / "judge" / "diff-key.json").write_text(json.dumps(key, indent=1))
half = (len(out) + 1) // 2
for name, part in (("diffs-1.txt", out[:half]), ("diffs-2.txt", out[half:])):
    (S / "judge" / name).write_text("\n\n".join(part) + "\n")
    print(name, len(part), "items", sum(len(p) for p in part), "chars")
print("sampled:", collections.Counter(k["stage"] for k in key))
