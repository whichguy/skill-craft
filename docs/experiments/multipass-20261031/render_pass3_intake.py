#!/usr/bin/env python3
"""What the first packet of a third pass tells its model about the files the second pass left. No model is called.

    python3 render_pass3_intake.py [PREFIX ...]          # default: every saved pair; writes pass3-intake-<prefix>.txt here

For each saved pair (docs/experiments/multipass-20261031/saved-pairs/<prefix>/) the script builds a small Git repository from the
second pass's three living files and a commit that records the first and second pass the way ShipLoop does (the knowledge commits
and the release-verify lessons commit), starts a real run on it with ``shiploop init`` and the prompt of the ``ticket-comments`` case,
and keeps two parts of the intake packet the run prints: the listing of the knowledge files the stage reads (a table of contents per
file, ``shiploop_navigator.READS_HEAD``) and the inherited learnings (the last commit messages). Both are what a model with a cleared
context reads of the repository before it plans.

Nothing outside a temporary folder is written, and the saved runs are not read: the inputs are the committed files.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CLI = ROOT / "skills" / "shiploop" / "scripts" / "shiploop"
PREFIXES = ("bf-codex-r1", "bf-codex-r2", "hooks-before", "hooks-after")
LIVING = ("spec.md", "environment.md", "architecture.md")
LESSONS = {"pass1": "Learned\nThe first pass's lesson.\n\nKey considerations\nA first consideration.\n\nOpen for the next run\nNone.",
           "pass2": "Learned\nThe second pass's lesson.\n\nKey considerations\nA second consideration.\n\nOpen for the next run\nNo known unfinished product work."}


def git(repo: Path, *args: str) -> None:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   check=True, capture_output=True, env=env)


def render(prefix: str) -> str:
    """The knowledge listing and the inherited learnings of the third pass's intake packet, for one saved pair."""
    prompt = json.loads((ROOT / "test" / "shiploop_e2e" / "cases.json").read_text())["ticket-comments"]["prompt"]
    with tempfile.TemporaryDirectory() as tmp:
        work, run = Path(tmp) / "work", Path(tmp) / "run"
        (work / "docs" / "shiploop").mkdir(parents=True)
        git(work, "init", "-q")
        (work / "README.md").write_text("The base the first pass started from.\n")
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", "base: node-tickets")
        for passed, subject in (("pass1", "docs(shiploop): record first-pass-1a2b3c knowledge at release-verify"),
                                ("pass2", "docs(shiploop): record second-pass-4d5e6f knowledge at release-verify")):
            for name in LIVING:
                (work / "docs" / "shiploop" / name).write_text((HERE / "saved-pairs" / prefix / passed / name).read_text())
            git(work, "add", "-A")
            git(work, "commit", "-q", "-m", subject + "\n\n" + LESSONS[passed])
        env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
        done = subprocess.run([sys.executable, "-B", str(CLI), "init", "--run-dir", str(run), "--repo", str(work), "--prompt", prompt],
                              capture_output=True, text=True, env=env, check=False)
        if done.returncode:
            raise SystemExit(f"shiploop init failed: {done.stderr[-400:]}")
        packet = next((run / "packets").glob("nav-*.md")).read_text()
    listing = re.search(r"^Knowledge files this stage reads.*?(?=^This action's pass log)", packet, re.S | re.M)
    learned = re.search(r"^Inherited learnings:.*?(?=^\S)", packet[packet.index("Inherited learnings:"):], re.S | re.M)
    text = ((listing.group(0) if listing else "(no knowledge listing in the packet)\n") + "\n"
            + (learned.group(0) if learned else "(no inherited learnings in the packet)\n"))
    # The folder and the short commit ids differ on every run; the engine's words around them are what is kept.
    text = re.sub(r"in \S+/work\.", "in <work>.", text)
    return re.sub(r"\| [0-9a-f]{7,12} (?=\S)", "| <commit> ", text)


def main(argv: list[str]) -> int:
    for prefix in argv or PREFIXES:
        (HERE / f"pass3-intake-{prefix}.txt").write_text(render(prefix))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
