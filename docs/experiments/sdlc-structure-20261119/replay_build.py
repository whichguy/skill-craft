#!/usr/bin/env python3
"""Materialize the reader-replay cases: what each recorded step reviewer was handed, as a read-only folder.

For each case in WORK/replay/cases.json that has an id (replay_cases.py), write

  WORK/rv/cases/<id>/tree/              the working tree the step review was bound on (read-only)
  WORK/rv/cases/<id>/step-change.diff   that step's change: its Review base against the bound tree
  WORK/rv/cases/<id>/review-focus.md    the recorded review's own hand-off: what it looks for, the code craft
                                        rules, what the reviewed stage worked from and the stage's result
  WORK/rv/cases/<id>/records/           the run records that hand-off names (results, test runs, the request)
  WORK/key/<id>/                        the end-of-work review's fix, for the judges only: fix.patch,
                                        fix-message.txt, end-review.md

Paths of the original run are replaced by TREE, RECORDS and GUIDES so a reader cannot follow them to the run's
later history; a tree file that quotes such a path gets the same replacement and is counted in the printed table
(nothing else in the tree is touched). `--also RUN_SUBSTRING` adds one excluded case as x01, for rehearsing the apparatus.

Usage: python3 -I replay_build.py WORK [--also RUN_SUBSTRING]
"""
import json
import pathlib
import re
import shutil
import stat
import subprocess
import sys

KEEP = ("## What this review looks for", "## Code craft", "## What the reviewed stage worked from")
DROP_LINE = re.compile(r"^(Recovery command|python3 |Keepalive marker|State: |Pause |Restart |Halt )")
NAMED = re.compile(r"RUN/((?:results|lint|tests|loops|fields|notes|inbox|packets)/[A-Za-z0-9._-]+)")


def git(top, *args, binary=False):
    done = subprocess.run(["git", "-C", str(top), *args], capture_output=True, check=False)
    return done.stdout if binary else done.stdout.decode(errors="replace")


def scrub(text, worktree, rundir):
    """Replace the original run's absolute paths with symbols."""
    text = text.replace(str(worktree), "TREE").replace(str(rundir), "RECORDS")
    text = re.sub(r"/[^\s`'\"()]*?/skills/shiploop/references", "GUIDES", text)
    text = re.sub(r"/[^\s`'\"()]*?/skills/(shiploop|improve)/[^\s`'\"()]*", r"<the \1 skill's file>", text)
    return re.sub(r"/Users/[^\s`'\"()]*e2e-run[^\s`'\"()]*", "<a path of the original run>", text)


def focus(handoff, worktree, rundir):
    """The parts of the recorded hand-off a reader needs; the callback and commit mechanics are left out."""
    sections, current = {}, None
    for line in handoff.splitlines():
        if line.startswith("## "):
            current = line.strip()
            sections[current] = []
        elif current:
            sections[current].append(line)
    out = []
    for name in KEEP:
        body = [line for line in sections.get(name, []) if not DROP_LINE.match(line)]
        out += [name, *body, ""]
    review = "\n".join(sections.get("## The review", []))
    result = re.search(r"# Stage result awaiting Improve\n\n```shiploop-state\n.*?\n```", review, re.DOTALL)
    if result:
        out += ["## The reviewed stage's result (as the step reviewer received it)", result.group(0), ""]
    return scrub("\n".join(out), worktree, rundir)


def make_read_only(root):
    for path in sorted(root.rglob("*"), reverse=True):
        if not path.is_symlink():
            path.chmod(path.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    root.chmod(root.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def build(case, work):
    rundir = pathlib.Path(case["run"])
    worktree = rundir.parent / "worktree"
    home = work / "rv" / "cases" / case["id"]
    if home.exists():
        subprocess.run(["chmod", "-R", "u+w", str(home)], check=False)
        shutil.rmtree(home)
    tree = home / "tree"
    tree.mkdir(parents=True)
    archive = subprocess.run(["git", "-C", str(worktree), "archive", case["step_tree"]], capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", str(tree), "--exclude", ".shiploop-improve", "--exclude", ".until-loop"],
                   input=archive.stdout, check=True)
    scrubbed = 0
    for path in tree.rglob("*"):
        if path.is_file() and not path.is_symlink():
            try:
                text = path.read_text()
            except (OSError, UnicodeDecodeError):
                continue
            if "e2e-run" in text:
                path.write_text(scrub(text, worktree, rundir))
                scrubbed += 1
    (home / "step-change.diff").write_text(scrub(git(worktree, "diff", "--no-renames", case["review_base"], case["step_tree"],
                                               "--", ".", ":(exclude).shiploop-improve", ":(exclude).until-loop"),
                                               worktree, rundir))
    handoff = pathlib.Path(case["handoff"]).read_text()
    (home / "review-focus.md").write_text(focus(handoff, worktree, rundir))
    records = home / "records"
    names = sorted(set(NAMED.findall(handoff)) | {"request.md", "notes/plan.md", "notes/current-system-baseline.md"})
    kept = []
    for name in names:
        source = rundir / name
        if source.is_file() and "improve" not in name and "final-result" not in name:
            target = records / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(scrub(source.read_text(errors="replace"), worktree, rundir))
            kept.append(name)
    make_read_only(tree)
    key = work / "key" / case["id"]
    key.mkdir(parents=True, exist_ok=True)
    (key / "fix.patch").write_text(git(worktree, "diff", "--no-renames", case["end_tree"], case["fix_commit"], "--",
                                       *case["fix_paths"]))
    (key / "fix-message.txt").write_text(git(worktree, "show", "-s", "--format=%B", case["fix_commit"]))
    notes = sorted((worktree / ".shiploop-improve" / f"carry-forward-{case['end_action'][-8:]}" / "reviews")
                   .glob("review-*.md"))
    (key / "end-review.md").write_text("\n\n".join(scrub(n.read_text(errors="replace"), worktree, rundir)
                                                    for n in notes))
    files = sum(1 for p in tree.rglob("*") if p.is_file())
    print(f"{case['id']}  tree files {files:>4}  step diff {len((home / 'step-change.diff').read_text().splitlines()):>5} lines  "
          f"focus {len((home / 'review-focus.md').read_text()):>6} chars  records {len(kept):>2}  "
          f"fix {len((key / 'fix.patch').read_text().splitlines()):>3} lines  tree files with a run path replaced {scrubbed}")


def main(argv):
    work = pathlib.Path(argv[0])
    cases = json.loads((work / "replay" / "cases.json").read_text())
    chosen = [c for c in cases if c.get("id")]
    if "--also" in argv:
        extra = next(c for c in cases if not c.get("id") and c["handoff"] and argv[argv.index("--also") + 1] in c["run"])
        extra["id"] = "x01"
        chosen.append(extra)
    for case in sorted(chosen, key=lambda c: c["id"]):
        build(case, work)


if __name__ == "__main__":
    main(sys.argv[1:])
