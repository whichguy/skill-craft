#!/usr/bin/env python3
"""Where does `cut -c1-250` of line 1 of the knowledge refusals end, by path length, callback and refusal?  (batch 1012 task A)

Repeat with:  python3 docs/experiments/architecture-file-20261010/cut_margin.py [OUT.json]   (from the repository root)

Builds a real Git repository whose architecture.md path has each length below, commits twelve decision IDs, then reads line 1 of the
real refusal (shiploop_knowledge_home.check) with the CLI's 'ShipLoop navigator: ' prefix, for the two refusals a cleared-context
model meets there: a dropped ID ("dropped-id": the file loses its IDs) and a line the credential screen flags ("credential").
`verb_ends` is the 1-based column where the route's callback name ends in the final instruction (the last 'complete' of the line for
`complete`, the last 'improve-complete' for `improve-complete`); `last_step_ends` is the column of the line's last character; the
line is cut at column 250.  The saved E2E execution checkouts put architecture.md at 125 to 137 characters (six paths measured
2026-10-10), so the rows from 125 to 137 are the ones that matter; the unit tests assert the same at every width from 125 to 137.
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
LENGTHS = (110, 120, 125, 127, 130, 134, 135, 137, 140, 145)
WRITES = {"dropped-id": "# Architecture\n", "credential": "# Architecture\nPassword: bcrypt, cost 12\n"}
rows = []
with tempfile.TemporaryDirectory(prefix="cut-margin-") as temp:
    base = Path(temp).resolve()
    for length in LENGTHS:
        pad = length - len(str(base)) - 1 - len("/docs/shiploop/architecture.md")
        if pad < 1:
            continue
        repo = base / ("w" * pad)
        (repo / "docs/shiploop").mkdir(parents=True)
        path = repo / "docs/shiploop/architecture.md"
        path.write_text("".join("AD-%d choice\n" % n for n in range(1, 13)))
        for argv in (["init", "-q"], ["add", "."], ["-c", "user.email=a@b.invalid", "-c", "user.name=a", "commit", "-qm", "x"]):
            subprocess.run(["git", "-C", str(repo), *argv], env=env, check=True, capture_output=True)
        state = {"repo": str(repo), "prompt": "x", "run_id": "nav-000000"}
        for refusal, text in WRITES.items():
            path.write_text(text)
            for command in ("complete", "improve-complete"):
                line = PREFIX + k.check(state, "step-plan", command).splitlines()[0]
                verb_ends = line.rindex(command) + len(command)
                rows.append({"path_length": len(str(path)), "refusal": refusal, "command": command, "line_length": len(line),
                             "verb_ends": verb_ends, "verb_fits_in_250": verb_ends <= 250, "last_step_ends": len(line),
                             "all_fits_in_250": len(line) <= 250, "ids_on_line_1": "AD-1" in line})
for row in rows:
    print(row)
if len(sys.argv) > 1:
    Path(sys.argv[1]).write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
