#!/usr/bin/env python3
"""What skills/shiploop/scripts/shiploop_lessons.py reads in the commits of saved E2E runs (read-only).

Repeat with:  PYTHONDONTWRITEBYTECODE=1 python3 docs/experiments/commit-contract-engine-20261010/scan_saved_commits.py [RUNS_ROOT]

RUNS_ROOT defaults to ~/e2e-runs; every <date>/<case>/work repository is read with `git log` (nothing is written
or run besides git).  Commits are classed from their own text: "improve_style" has a `Review:` line and a `Plan:`
(the Improve card's record), "knowledge_script" has a subject that starts `docs(shiploop):`, everything else is
"other".  `one_paragraph` counts Improve-style commits that write every label in one paragraph ("Review: x. Plan: y.
... Key learnings: z."), a shape the grammar does not read (a refusal asks for the label on a line of its own).
Writes saved-commits-scan.json beside this file.
"""
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "skills" / "shiploop" / "scripts"))
import shiploop_lessons as commit_lessons  # noqa: E402

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "e2e-runs"
repos = sorted(glob.glob(str(root / "*" / "*" / "work")))
total = {"repos": 0, "commits": 0}
classes = {name: {"commits": 0, "with_lessons": 0, "lessons_none": 0, "with_remote_change": 0, "with_citation_lines": 0,
                  "one_paragraph": 0} for name in ("improve_style", "knowledge_script", "other")}
for repo in repos:
    if not os.path.exists(repo + "/.git"):
        continue
    total["repos"] += 1
    out = subprocess.run(["git", "-C", repo, "log", "--format=%H%x00%B%x01"], capture_output=True, text=True).stdout
    for entry in out.split("\x01"):
        entry = entry.strip("\n")
        if not entry:
            continue
        _sha, body = entry.split("\x00", 1)
        total["commits"] += 1
        improve = re.search(r"(?m)^Review:", body) and re.search(r"\bPlan:", body)
        subject = body.splitlines()[0] if body.strip() else ""
        kind = "improve_style" if improve else ("knowledge_script" if subject.startswith("docs(shiploop):") else "other")
        row = classes[kind]
        row["commits"] += 1
        lesson = commit_lessons.lessons(body)
        row["with_lessons"] += bool(lesson)
        row["lessons_none"] += lesson.strip().lower().rstrip(".") == "none"
        row["with_remote_change"] += bool(commit_lessons.remote_change(body))
        row["with_citation_lines"] += bool(commit_lessons.citations(body))
        row["one_paragraph"] += bool(kind == "improve_style" and not lesson
                                     and re.search(r"(?mi)\bKey learnings?:", body))
result = {"runs_root": "~/e2e-runs", **total, "classes": classes}
out_path = HERE / "saved-commits-scan.json"
out_path.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
print(json.dumps(result, indent=1))
