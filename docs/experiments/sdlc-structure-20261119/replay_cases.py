#!/usr/bin/env python3
"""Find the recorded cases for the reader replay: an end-of-work review that fixed code or tests right after a
step review had passed the same lines.

For every finished current-era run in census.json, take each end-of-work (carry-forward) review whose pass log says
it changed the tree and whose snapshot-to-commit diff (review_edits.json) names a code or test file. Pair it with the
last step review (the Improve review of `document`) bound before it. The case is usable when both hold:
- the end-of-work review's code and test patch applies cleanly to the tree the step review was bound on, so the
  lines it fixed were in front of the step reviewer, unchanged;
- every file it fixed is part of that step's own change (its Review base against the bound tree), so the fix was
  inside what that step review was asked to read.
Items of one step get ids c01.., longer items (their last step) m01...

Usage: python3 -I replay_cases.py WORK        (reads WORK/census.json and WORK/review_edits.json,
                                               writes WORK/replay/cases.json and prints the table)
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "skills/shiploop/scripts"))
import shiploop_item_scope as item_scope

STATE = re.compile(r"```shiploop-state\n(.*?)\n```", re.DOTALL)
BASE = re.compile(r"^Review base .*? diff ([0-9a-f]{40}) ([0-9a-f]{40})", re.MULTILINE)


def git(top, *args, env=None, stdin=None):
    done = subprocess.run(["git", "-C", str(top), *args], capture_output=True, text=True, check=False,
                          env=env, input=stdin)
    return done.returncode, done.stdout


def reviews(rundir):
    """Every Improve review of the run: (bind time, reviewed stage, action, bound tree, tree changed)."""
    rows = []
    for passes in sorted((rundir / "improve").glob("nav-*/passes.md")):
        action = passes.parent.name
        table = [[c.strip() for c in line.strip().strip("|").split("|")] for line in passes.read_text().splitlines()]
        table = [c for c in table if len(c) >= 8 and c[1].isdigit()]
        bind = rundir / "improve" / f"{action}-bind.md"
        try:
            bound = json.loads(STATE.search(bind.read_text()).group(1))
        except (OSError, ValueError, AttributeError, KeyError):
            continue
        if table:
            rows.append((bind.stat().st_mtime, table[0][0], action, bound["tree"], any(c[3] == "y" for c in table)))
    return sorted(rows)


def applies(worktree, tree, patch):
    """True when the patch applies to that tree (checked in a throwaway index, nothing written to the checkout)."""
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(pathlib.Path(tmp) / "index"))
        if git(worktree, "read-tree", tree, env=env)[0] != 0:
            return False
        return git(worktree, "apply", "--cached", "--check", "-", env=env, stdin=patch)[0] == 0


def main(work):
    runs = [r for r in json.loads((work / "census.json").read_text()) if r["current_era"] and r["done"]]
    edits = json.loads((work / "review_edits.json").read_text())
    fixed = {}
    for row in edits:
        if row["stage"] == "carry-forward" and row["logged_tree"] and {"code", "test"} & set(row["classes"]):
            fixed[row["dir"]] = row
    cases, dropped = [], {}
    for run in runs:
        rundir = pathlib.Path(run["trace"]).parent
        worktree = rundir.parent / "worktree"
        mine = [row for path, row in fixed.items() if pathlib.Path(path).parent.parent == rundir]
        if not mine:
            continue
        code, log = git(worktree, "log", "--all", "--format=%H %ct %T %s")
        if code != 0:
            dropped["no git log"] = dropped.get("no git log", 0) + len(mine)
            continue
        commits = sorted((int(p[1]), p[0], p[2], p[3]) for p in (line.split(" ", 3) for line in log.splitlines())
                         if len(p) == 4)
        every = reviews(rundir)
        for row in mine:
            action = pathlib.Path(row["dir"]).name
            end = next((r for r in every if r[2] == action), None)
            steps = [r for r in every if r[1] == "document" and end and r[0] < end[0]]
            if not end or not steps:
                dropped["no step review before it"] = dropped.get("no step review before it", 0) + 1
                continue
            step = steps[-1]
            after = next((c for c in commits if c[0] >= end[0] - 1), None)
            paths = [p for p in row["paths"] if item_scope.classify(p) in ("code", "test")]
            patch = git(worktree, "diff", "--no-renames", end[3], after[2], "--", *paths)[1]
            same = all(git(worktree, "rev-parse", f"{step[3]}:{p}")[1] == git(worktree, "rev-parse", f"{end[3]}:{p}")[1]
                       for p in paths)
            handoff = worktree / ".shiploop-improve" / f"document-{step[2][-8:]}" / "handoff.md"
            base = BASE.search(handoff.read_text()) if handoff.exists() else None
            item_steps = max(run["steps"].values()) if run["steps"] else 0
            changed = git(worktree, "diff-tree", "-r", "--no-renames", "--name-only", base.group(1), step[3])[1] \
                if base else ""
            case = {
                "run": str(rundir), "case": run.get("case"), "host": run.get("host"), "model": run.get("model"),
                "item_steps": item_steps, "step_action": step[2], "step_tree": step[3], "step_review_edited": step[4],
                "end_action": action, "end_tree": end[3], "fix_commit": after[1], "fix_subject": after[3],
                "fix_paths": paths, "fix_lines": sum(1 for line in patch.splitlines()
                                                     if line[:1] in "+-" and line[:3] not in ("+++", "---")),
                "patch_applies_to_step_tree": applies(worktree, step[3], patch), "files_unchanged_between": same,
                "fix_inside_step_change": bool(base) and all(p in changed.splitlines() for p in paths),
                "handoff": str(handoff) if handoff.exists() else None,
                "review_base": base.group(1) if base else None, "bound": base.group(2) if base else None,
            }
            cases.append(case)
    applying = [c for c in cases if c["patch_applies_to_step_tree"] and c["handoff"] and c["review_base"]]
    usable = [c for c in applying if c["fix_inside_step_change"]]
    primary = [c for c in usable if c["item_steps"] <= 1]
    longer = [c for c in usable if c["item_steps"] > 1]
    for letter, group in (("c", primary), ("m", longer)):
        for n, case in enumerate(sorted(group, key=lambda c: (c["case"] or "", c["run"])), 1):
            case["id"] = f"{letter}{n:02d}"
    out = work / "replay"
    out.mkdir(exist_ok=True)
    (out / "cases.json").write_text(json.dumps(cases, indent=1))
    print(f"end-of-work reviews that changed code or tests (pass log and diff agree): {len(fixed)}")
    print(f"dropped before pairing: {dropped}")
    print(f"paired with the step review before them: {len(cases)}")
    print(f"  the fix applies cleanly to the tree the step review was bound on: "
          f"{sum(c['patch_applies_to_step_tree'] for c in cases)}")
    print(f"  of those, with the step review's own hand-off still on disk: {len(applying)}")
    print(f"  of those, every fixed file inside that step's own change: {len(usable)}")
    print(f"  items of one step: {len(primary)}; longer items (their last step): {len(longer)}")
    print(f"\n{'id':<5}{'case':<20}{'model':<15}{'steps':>6}{'fix lines':>10}  {'step review edited':<20}fix")
    for case in sorted(usable, key=lambda c: c["id"]):
        print(f"{case['id']:<5}{(case['case'] or '?'):<20}{(case['model'] or '?'):<15}{case['item_steps']:>6}"
              f"{case['fix_lines']:>10}  {('yes' if case['step_review_edited'] else 'no'):<20}{case['fix_subject'][:58]}")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]))
