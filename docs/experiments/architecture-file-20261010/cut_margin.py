#!/usr/bin/env python3
"""Where does `cut -c1-250` of the retention refusal's line 1 end, by path length and callback?  (batch 1012 task A)

Repeat with:  python3 docs/experiments/architecture-file-20261010/cut_margin.py [OUT.json]   (from the repository root)

Builds a real Git repository whose architecture.md path has each length below, commits twelve decision IDs, drops them all, and
reads line 1 of the real refusal (shiploop_knowledge_home.check) with the CLI's 'ShipLoop navigator: ' prefix.  `command_ends`
is the 1-based column of the last character of 'again.'; the line is cut at column 250.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_knowledge_home as k  # noqa: E402

env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
PREFIX = "ShipLoop navigator: "
rows = []
with tempfile.TemporaryDirectory(prefix="cut-margin-") as temp:
    base = Path(temp).resolve()
    for length in (80, 100, 110, 120, 122, 130, 140):
        pad = length - len(str(base)) - 1 - len("/docs/shiploop/architecture.md")
        if pad < 1:
            continue
        repo = base / ("w" * pad)
        (repo / "docs/shiploop").mkdir(parents=True)
        path = repo / "docs/shiploop/architecture.md"
        path.write_text("".join("AD-%d choice\n" % n for n in range(1, 13)))
        for argv in (["init", "-q"], ["add", "."], ["-c", "user.email=a@b.invalid", "-c", "user.name=a", "commit", "-qm", "x"]):
            subprocess.run(["git", "-C", str(repo), *argv], env=env, check=True, capture_output=True)
        path.write_text("# Architecture\n")
        state = {"repo": str(repo), "prompt": "x", "run_id": "nav-000000"}
        for command in ("complete", "improve-complete"):
            line = PREFIX + k.check(state, "step-plan", command).splitlines()[0]
            ends = line.index("again.") + len("again.")
            rows.append({"path_length": len(str(path)), "command": command, "line_length": len(line), "command_ends": ends,
                         "fits_in_250": ends <= 250, "ids_on_line_1": "AD-1" in line})
for row in rows:
    print(row)
if len(sys.argv) > 1:
    Path(sys.argv[1]).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
