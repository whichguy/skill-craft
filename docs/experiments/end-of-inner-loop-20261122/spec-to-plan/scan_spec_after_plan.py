#!/usr/bin/env python3
"""Read-only census: how often a saved ShipLoop E2E delivery changed docs/shiploop/spec.md after its plan stage.

For each saved run folder under ~/e2e-runs*/ (a folder holding invocation.json and a Git checkout in work/), list the
commits that touched docs/shiploop/spec.md after the plan boundary: the last commit whose subject says
"knowledge (at|after) plan", else from the "knowledge at prepare" commit on.  Each such commit is classified by its
subject (a ShipLoop knowledge commit names its stage; "feat(W<n>/S<n>)" is a step commit; anything else is "other",
for example an Improve review's own commit) and by its diff of spec.md: lines added, lines removed (a removed or
changed line; blank lines ignored), and R-<n> IDs new since the boundary.

Runs only `git log` and `git show`; writes one JSON file and prints a summary.  Usage:
    python3 scan_spec_after_plan.py OUT.json
"""
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

SPEC = "docs/shiploop/spec.md"
STAGE = re.compile(r"knowledge (?:at|after) ([a-z][a-z-]*)$")
STEP = re.compile(r"^feat\((W[^/()]+)/(S[^()]+)\)")
RID = re.compile(r"\bR-\d+\b")
PRUNE = {"work", "home", "delivery", "review-export", "node_modules", ".git", ".shiploop-runs"}


def git(repo, *args):
    try:
        done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=60,
                              errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def run_folders():
    for base in sorted(Path.home().glob("e2e-runs*")):
        if not base.is_dir():
            continue
        for current, dirs, files in os.walk(base):
            if "invocation.json" in files:
                dirs[:] = []
                yield Path(current)
                continue
            dirs[:] = [name for name in dirs if name not in PRUNE]


def spec_ids(repo, commit):
    text = git(repo, "show", commit + ":" + SPEC)
    return set(RID.findall(text)) if text is not None else set()


def classify(subject):
    match = STAGE.search(subject)
    if match:
        return match.group(1)
    if STEP.match(subject):
        return "step-commit"
    return "other"


def scan(folder):
    repo = folder / "work"
    if not (repo / ".git").exists():
        return None
    try:
        invocation = json.loads((folder / "invocation.json").read_text())
    except (OSError, ValueError):
        invocation = {}
    versions = invocation.get("versions") or {}
    log = git(repo, "log", "--reverse", "--format=%H%x09%s")
    if log is None:
        return None
    commits = [line.split("\t", 1) for line in log.splitlines() if "\t" in line]
    boundary = None
    for index, (sha, subject) in enumerate(commits):
        stage = STAGE.search(subject)
        if stage and stage.group(1) == "plan":
            boundary = index           # the plan's own commit; later commits are post-plan
    if boundary is None:
        for index, (sha, subject) in enumerate(commits):
            stage = STAGE.search(subject)
            if stage and stage.group(1) == "prepare":
                boundary = index - 1   # the prepare close itself is post-plan
                break
    row = {"folder": str(folder), "shiploop": versions.get("shiploop_version"), "host": invocation.get("host"),
           "model": invocation.get("model"), "case": invocation.get("case"), "has_boundary": boundary is not None,
           "post_plan": []}
    if boundary is None:
        return row
    base_sha = commits[boundary][0] if boundary >= 0 else None
    base_ids = spec_ids(repo, base_sha) if base_sha else set()
    touched = git(repo, "log", "--reverse", "--format=%H", "--", SPEC)
    touched = set((touched or "").split())
    for sha, subject in commits[boundary + 1:]:
        if sha not in touched:
            continue
        diff = git(repo, "show", "--format=", "--unified=0", sha, "--", SPEC) or ""
        added = [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
        removed = [line[1:] for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")]
        added = [line for line in added if line.strip()]
        removed = [line for line in removed if line.strip()]
        now_ids = spec_ids(repo, sha)
        row["post_plan"].append({
            "commit": sha, "subject": subject[:160], "stage": classify(subject),
            "added": len(added), "removed": len(removed),
            "new_ids": sorted(now_ids - base_ids, key=lambda ident: int(ident.split("-")[1])),
            "removed_sample": [line[:200] for line in removed[:3]],
        })
    return row


def main():
    out = Path(sys.argv[1])
    rows = [found for found in (scan(folder) for folder in run_folders()) if found is not None]
    out.write_text(json.dumps(rows, indent=1) + "\n")
    with_boundary = [row for row in rows if row["has_boundary"]]
    by_stage_any, by_stage_removed, by_stage_newid = Counter(), Counter(), Counter()
    runs_removed, runs_newid, runs_any = set(), set(), set()
    per_version = defaultdict(lambda: [0, 0, 0])
    for row in with_boundary:
        version = str(row["shiploop"] or "?")
        major = ".".join(version.split(".")[:2])
        per_version[major][0] += 1
        removed_here = False
        for commit in row["post_plan"]:
            by_stage_any[commit["stage"]] += 1
            runs_any.add(row["folder"])
            if commit["removed"]:
                by_stage_removed[commit["stage"]] += 1
                runs_removed.add(row["folder"])
                removed_here = True
        ids_after = set()
        for commit in row["post_plan"]:
            fresh = [ident for ident in commit["new_ids"] if ident not in ids_after]
            if fresh:
                by_stage_newid[commit["stage"]] += 1
                runs_newid.add(row["folder"])
                ids_after.update(fresh)
        if removed_here:
            per_version[major][1] += 1
        if any(commit["new_ids"] for commit in row["post_plan"]):
            per_version[major][2] += 1
    print("run folders with a work checkout:", len(rows))
    print("with a plan or prepare knowledge commit (the boundary):", len(with_boundary))
    print("runs with any post-plan spec.md commit:", len(runs_any))
    print("runs with a post-plan spec.md commit that removed or changed a line:", len(runs_removed))
    print("runs whose spec gained an R-<n> after the plan:", len(runs_newid))
    print("post-plan spec.md commits by stage (any):", dict(by_stage_any.most_common()))
    print("  ... that removed or changed a line:", dict(by_stage_removed.most_common()))
    print("  ... that added a new R-<n>:", dict(by_stage_newid.most_common()))
    print("per ShipLoop minor version [runs, runs with a removed/changed line, runs with a new R-<n>]:")
    for major in sorted(per_version, key=lambda text: [int(part) if part.isdigit() else -1 for part in text.split(".")]):
        print("  ", major, per_version[major])


if __name__ == "__main__":
    main()
