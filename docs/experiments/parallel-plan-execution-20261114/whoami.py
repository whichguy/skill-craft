#!/usr/bin/env python3
"""whoami.py: what a skill could read to tell which harness it runs in, as one JSON line (names only, never values).

Apparatus for docs/experiments/parallel-plan-execution-20261114 (journal entry E10). identity.py copies this file into a
trial's work directory with the repository root filled in. It reports

  detect_host  what the repository's own ShipLoop function says (skills/shiploop/scripts/shiploop_grants.py, imported
               read-only: innermost host first, from CODEX_*, GROK_* and CLAUDECODE)
  markers      the names (not values) of every environment variable that starts with a harness or vendor prefix
  ids          the last six characters of the variables that name a thread or session, so a parent's and a sub-agent's
               environments can be compared without recording a full identifier
  ancestors    the command names of this process's ancestors, nearest first
"""

import json
import os
import subprocess
import sys

REPO_ROOT = "@REPO@"
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "shiploop", "scripts"))
from shiploop_grants import detect_host  # noqa: E402

PREFIXES = ("CODEX", "GROK", "CLAUDE", "ANTHROPIC", "XAI", "OPENAI", "CURSOR")
ID_KEYS = ("CODEX_THREAD_ID", "GROK_SESSION_ID", "GROK_AGENT", "CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID")


def ancestors(limit: int = 8) -> list:
    names, pid = [], os.getpid()
    for _ in range(limit):
        row = subprocess.run(["ps", "-o", "ppid=,comm=", "-p", str(pid)], capture_output=True, text=True).stdout.split(None, 1)
        if len(row) < 2 or not row[0].isdigit() or int(row[0]) <= 1:
            break
        pid = int(row[0])
        parent = subprocess.run(["ps", "-o", "comm=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
        names.append(os.path.basename(parent))
    return names


def main() -> int:
    print(json.dumps({"detect_host": detect_host(), "markers": sorted(k for k in os.environ if k.startswith(PREFIXES)),
                      "ids": {k: os.environ[k][-6:] for k in ID_KEYS if os.environ.get(k)}, "ancestors": ancestors(), "pid": os.getpid()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
