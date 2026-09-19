#!/usr/bin/env python3
"""Deterministic process worker for lifecycle tests, never a model substitute.

One JSON assignment arrives on stdin. The worker writes/tests actual Python
code in its assigned checkout, emits a readiness observation, and waits for a
parent release line before committing and returning a local handoff. This
barrier makes overlap assertions deterministic without timing sleeps.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

assignment = json.loads(sys.stdin.readline())
workspace = Path(assignment["workspace"])
os.chdir(workspace)
step = assignment["step"]
sources = {
    "A": ("chain_add.py", "def add(left, right):\n    return left + right\n",
          "from chain_add import add; assert add(-4,1)==-3; assert add(2,3)==5"),
    "B": ("chain_format.py", "def normalize(text):\n    return ' '.join(text.strip().lower().split())\n",
          "from chain_format import normalize; assert normalize('  RESULT  FIVE ')=='result five'"),
    "C": ("chain_sum.py", "from chain_add import add\ndef total(values):\n    result=0\n    for value in values:\n        result=add(result,value)\n    return result\n",
          "from chain_sum import total; assert total([2,3,-1])==4; assert total([])==0"),
    "J": ("chain_report.py", "from chain_sum import total\nfrom chain_format import normalize\ndef report(label, values):\n    return f'{normalize(label)}: {total(values)}'\n",
          "from chain_report import report; assert report(' RESULT ',[2,3])=='result: 5'"),
}
name, source, check = sources[step]
(workspace / name).write_text(source)
subprocess.run([sys.executable, "-B", "-c", check], check=True, cwd=workspace)
print(json.dumps({"phase": "code_ready", "pid": os.getpid(), "cwd": str(workspace),
                  "step": step}), flush=True)
if sys.stdin.readline().strip() != "release":
    raise SystemExit("missing explicit fixture release")
git = ["git", "-c", "user.name=Chain Code Fixture", "-c", "user.email=chain@example.invalid"]
subprocess.run([*git, "add", name], check=True)
subprocess.run([*git, "commit", "-qm", "Implement " + step], check=True)
commit = subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip()
handoff = workspace / ".shiploop-handoff" / assignment["attempt"] / "handoff.json"
handoff.parent.mkdir(parents=True, exist_ok=True)
checks = handoff.parent / "checks.json"
checks.write_text(json.dumps({"passed": True, "check": check, "cwd": str(workspace),
                             "git_root": subprocess.check_output([*git, "rev-parse", "--show-toplevel"], text=True).strip(),
                             "commit": commit, "fixture_worker": True}) + "\n")
manifest = {"schema": "shiploop-chain-handoff/v1", "run_id": assignment["run_id"],
            "step": step, "attempt": assignment["attempt"],
            "base_commit": assignment["base_commit"], "status": "SUCCEEDED",
            "commit": commit, "summary": "Generated and checked " + name,
            "files": [{"path": "checks.json", "sha256": hashlib.sha256(checks.read_bytes()).hexdigest()}]}
handoff.write_text(json.dumps(manifest) + "\n")
print(json.dumps({"handoff": str(handoff), "sha256": hashlib.sha256(handoff.read_bytes()).hexdigest(),
                  "commit": commit, "phase": "completed"}), flush=True)
