#!/usr/bin/env python3
"""Which stage first wrote each level-2 heading of environment.md that is no named section, in the saved follow-on runs.

    python3 attribute_stray_headings.py RUNS_ROOT

RUNS_ROOT is the folder cut_saved_pairs.py reads (~/e2e-runs-brownfield/20261029). For each follow-on run's final environment.md
the script takes every level-2 heading that does not start with a name of ``shiploop_knowledge_home.SECTIONS['environment.md']`` and
finds, in that run's Git history (``git log -S``), the oldest knowledge commit whose version of the file holds it. ShipLoop commits
the home after every accepted stage with the subject ``docs(shiploop): record <run> knowledge at|after <stage>``, so the subject
names the stage. Writes stray-headings-by-stage.json: per run, the headings with their stage and the run (the first run's label is
the first pass's, the second's the follow-on's), and the totals by stage.

Read-only: it reads the run folders' repositories and writes one file beside this script.
"""

from __future__ import annotations

import collections
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "skills" / "shiploop" / "scripts"))
import shiploop_knowledge_home as knowledge  # noqa: E402

PREFIXES = ("bf-codex-r1", "bf-codex-r2", "hooks-before", "hooks-after")
NAMED = [word.lower() for word in knowledge.SECTIONS["environment.md"]]


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False).stdout


def main(root: Path) -> int:
    runs, totals = {}, collections.Counter()
    for prefix in PREFIXES:
        repo = root / f"{prefix}-ticket-escalation" / "work"
        text = (repo / "docs" / "shiploop" / "environment.md").read_text()
        stray = [line[3:].strip() for line in text.splitlines()
                 if line.startswith("## ") and not any(line[3:].strip().lower().startswith(word) for word in NAMED)]
        rows = []
        for heading in stray:
            found = git(repo, "log", "--reverse", "--format=%H%x00%s", "-S## " + heading, "--", "docs/shiploop/environment.md").splitlines()
            subject = found[0].split("\0")[1] if found else ""
            stage = re.search(r"knowledge (?:at|after) ([a-z-]+)$", subject)
            run = re.search(r"record (\S+) knowledge", subject)
            rows.append({"heading": heading, "stage": stage.group(1) if stage else None, "commit_subject": subject,
                         "run_label": run.group(1) if run else None})
            totals[stage.group(1) if stage else "not a knowledge commit"] += 1
        runs[prefix] = rows
    (HERE / "stray-headings-by-stage.json").write_text(json.dumps({"runs": runs, "totals_by_stage": dict(totals.most_common())},
                                                                 indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]).expanduser().resolve()))
