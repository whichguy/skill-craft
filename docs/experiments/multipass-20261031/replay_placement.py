#!/usr/bin/env python3
"""Replay the placement candidate's notice over the knowledge commits of real runs (no model, no lease, nothing written).

    python3 replay_placement.py TREE WORKDIR [WORKDIR ...]

TREE is a checkout of the candidate (its skills/shiploop/scripts is imported); each WORKDIR is a run's work repository.  For every
commit that touched docs/shiploop, the stage's edit is the commit against its parent, which is what the engine reads (the working
tree against HEAD, before it commits).  A ShipLoop knowledge commit ("docs(shiploop): record <run> knowledge at|after <stage>") is
one the notice would have seen; a step commit (feat(W1/S2): ...) rides with the step and the engine's close returns before it, so it
is listed apart.  Prints one row per commit with something to say, then a total per run.
"""
import re
import subprocess
import sys
from pathlib import Path

tree = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tree / "skills/shiploop/scripts"))
import shiploop_knowledge_home as k  # noqa: E402

KNOWLEDGE = re.compile(r"^docs\(shiploop\): record \S+ knowledge (?:at|after) ([a-z-]+)$")


def git(work: Path, *args: str) -> str | None:
    done = subprocess.run(["git", "-C", str(work), *args], capture_output=True, text=True)
    return done.stdout if done.returncode == 0 else None


def show(work: Path, rev: str, name: str) -> str:
    return git(work, "show", f"{rev}:docs/shiploop/{name}") or ""


def main() -> None:
    for work in map(Path, sys.argv[2:]):
        commits = (git(work, "log", "--reverse", "--format=%H%x00%s", "--", "docs/shiploop") or "").splitlines()
        seen = covered = stepped = 0
        rows = []
        for line in commits:
            sha, subject = line.split("\0", 1)
            parent = f"{sha}^" if git(work, "rev-parse", "--verify", "-q", f"{sha}^") else "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
            found = KNOWLEDGE.match(subject)
            for name in k.LIVING:
                before = show(work, parent, name) if parent != "4b825dc642cb6eb9a060e54bf8d69288fbee4904" else ""
                now = show(work, sha, name)
                if not now.strip() or before == now:
                    continue
                born = k._born_retired(name, before, now) if name in k._LIVE_SECTION else []
                heads = k._added_headings(name, before, now) if name in k._HEADING_FILES else []
                if not (born or heads):
                    continue
                where = found.group(1) if found else "step commit"
                seen += 1
                covered += bool(found)
                stepped += not found
                rows.append((where, name, born, heads))
        print(f"== {work.parent.name}: {len(rows)} (commit, file) pairs the notice would speak of; "
              f"{covered} at a knowledge commit, {stepped} in a step commit (not covered)")
        for where, name, born, heads in rows:
            print(f"   {where:20s} {name:16s} born-retired {born or '-'}   new headings {heads or '-'}")


if __name__ == "__main__":
    main()
