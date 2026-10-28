"""Per work item of each delivered E2E run: the files each implement step's own commit changed, and the groups the
steps form when steps that changed a shared file are joined.

ShipLoop commits each accepted inline implement step as ``feat(<item>/<step>): ...`` (``_step_commit``), so the
delivered history (``delivery/work.bundle``) holds every step's measured change. A step id that does not increase
starts a new round of the item; a step that changed no file has no commit and is not listed. Paths are classed by
ShipLoop's own catalog (``shiploop_item_scope.classify``).

Groups are counted four ways:
- ``all`` joins steps on any shared file, ``beh`` on shared code or test files, ``code`` on shared code files; a step
  with no file of the joining kind is a group of its own.
- ``C`` is the design's rule: join on shared code files, and a step that changed no code file joins the group of the
  step before it (the first step's, the group of the step after it).

Usage: python3 step_changes.py SKILL_CRAFT_ROOT SCRATCH_DIR RUN_DIR...
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT, SCRATCH, RUNS = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
import shiploop_item_scope as item_scope

STEP = re.compile(r"^feat\((W\d+)/(S\d+)\): ")


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def groups(steps, keep, attach=False):
    keys = [{path for path in files if keep(path)} for files in steps]
    parent = list(range(len(steps)))

    def root(index):
        while parent[index] != index:
            index = parent[index]
        return index

    for i in range(len(steps)):
        for j in range(i):
            if keys[i] & keys[j]:
                parent[root(i)] = root(j)
    if attach:
        keyed = [index for index, key in enumerate(keys) if key]
        for index, key in enumerate(keys):
            if not key and keyed:
                earlier = [other for other in keyed if other < index]
                parent[root(index)] = root(earlier[-1] if earlier else keyed[0])
    return len({root(index) for index in range(len(steps))})


def code(path):
    return item_scope.classify(path) == "code"


KINDS = {
    "all": (lambda path: True, False),
    "beh": (lambda path: item_scope.classify(path) in ("code", "test"), False),
    "code": (code, False),
    "C": (code, True),
}

for run in RUNS:
    name = Path(run).name
    clone = SCRATCH / name
    if not clone.exists():
        subprocess.run(["git", "clone", "-q", str(Path(run) / "delivery" / "work.bundle"), str(clone)], check=True)
    rounds = {}  # item -> list of rounds, each a list of (step, files)
    for line in git(clone, "log", "--all", "--reverse", "--format=%H %s").splitlines():
        sha, subject = line.split(" ", 1)
        match = STEP.match(subject)
        if not match:
            continue
        item, step = match.groups()
        files = [path for path in git(clone, "show", "--name-only", "--format=", sha).splitlines() if path]
        item_rounds = rounds.setdefault(item, [])
        if not item_rounds or int(step[1:]) <= int(item_rounds[-1][-1][0][1:]):
            item_rounds.append([])
        item_rounds[-1].append((step, files))
    for item, item_rounds in rounds.items():
        for number, steps in enumerate(item_rounds, 1):
            files = [row[1] for row in steps]
            counts = " ".join(f"{kind}={groups(files, keep, attach)}" for kind, (keep, attach) in KINDS.items())
            listed = " | ".join(f"{step}:{','.join(f'{p}[{item_scope.classify(p)}]' for p in row)}" for step, row in steps)
            print(f"{name:36} {item} r{number} changed-steps={len(steps)} {counts} | {listed}")
