#!/usr/bin/env python3
"""Read-only scan of the saved E2E work repos for the architecture-file change (batch 1012 task A).

Repeat with:  python3 docs/experiments/architecture-file-20261010/home_scan.py [OUT.json]
(from the repository root; needs the saved runs under /Users/dadleet/e2e-runs, which are only read: GIT_OPTIONAL_LOCKS=0, no
checkout, no write, and `git show` for committed versions).

Three questions, answered per saved home that has a docs/shiploop directory:
  1. prepare: which of the five living files does the prepare close find missing?  (The feature files differ per run, so the
     close is narrowed to the living files; the point is what a home an earlier version wrote meets at its next prepare.)
  2. prefix: does any home file already use the token AD-<n> (the architecture's decision prefix) or D-<n> (the prefix a model
     already uses for product decisions)?  A home that uses AD- would make the new retention read numbers it did not write.
  3. replay: over every committed version of docs/shiploop/spec.md (R-<n>) and docs/shiploop/architecture.md (AD-<n>), how many
     consecutive version pairs drop an ID?  (This is the false-refusal base rate of the HEAD baseline.)
"""
import collections
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
os.environ["GIT_OPTIONAL_LOCKS"] = "0"
import shiploop_knowledge_home as k  # noqa: E402

RUNS = "/Users/dadleet/e2e-runs"
AD, D, R = re.compile(r"\b(AD-\d+)\b"), re.compile(r"\b(D-\d+)\b"), re.compile(r"\b(R-\d+)\b")


def git(work, *args):
    return subprocess.run(["git", "-C", work, "-c", "core.hooksPath=/dev/null", *args], capture_output=True, text=True)


def pairs(work, name, pattern):
    """(versions, consecutive pairs, pairs that drop an ID) over the committed versions of docs/shiploop/<name>."""
    shas = [s for s in git(work, "log", "--format=%H", "--reverse", "--", k.HOME + "/" + name).stdout.split() if s]
    previous, versions, total, drops = None, 0, 0, []
    for sha in shas:
        shown = git(work, "show", sha + ":" + k.HOME + "/" + name)
        if shown.returncode:
            previous = None  # deleted in that commit
            continue
        now = set(pattern.findall(shown.stdout))
        versions += 1
        if previous is not None:
            total += 1
            gone = sorted(previous - now)
            if gone:
                drops.append([sha[:8], gone])
        previous = now
    return versions, total, drops


homes, missing, tokens = [], collections.Counter(), collections.Counter({"AD-<n>": 0, "D-<n>": 0})
replay = {"spec.md": [0, 0, []], "architecture.md": [0, 0, []]}
living = k.CLOSES["prepare"]
k.CLOSES["prepare"] = ("README.md", "spec.md", "environment.md", "test-strategy.md", k.ARCHITECTURE)
try:
    for work in sorted(glob.glob(RUNS + "/2026*/*/work")):
        if not os.path.isdir(work + "/docs/shiploop"):
            continue
        name = work[len(RUNS) + 1:-len("/work")]
        homes.append(name)
        refusal = k.check({"repo": work, "prompt": "x", "run_id": "nav-000000"}, "prepare")
        missing[tuple(line[2:].rsplit("/docs/shiploop/", 1)[-1] for line in refusal.splitlines() if line.startswith("- /"))] += 1
        text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in Path(work, "docs/shiploop").rglob("*.md"))
        for label, pattern in (("AD-<n>", AD), ("D-<n>", D)):
            if pattern.search(text):
                tokens[label] += 1
        for file, pattern in (("spec.md", R), ("architecture.md", AD)):
            versions, total, drops = pairs(work, file, pattern)
            replay[file][0] += versions
            replay[file][1] += total
            replay[file][2] += [[name] + row for row in drops]
finally:
    k.CLOSES["prepare"] = living
result = {
    "homes": len(homes),
    "prepare_missing": {", ".join(key) or "(nothing)": count for key, count in missing.items()},
    "homes_using_token": dict(tokens),
    # null, not 0, when there is no pair to judge: a file no saved home has says nothing about the rate
    "replay": {file: {"versions": v, "consecutive_pairs": t, "pairs_dropping_an_id": len(d) if t else None, "drops": d}
               for file, (v, t, d) in replay.items()},
}
print(json.dumps(result, indent=1))
if len(sys.argv) > 1:
    Path(sys.argv[1]).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
