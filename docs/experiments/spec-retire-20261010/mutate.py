#!/usr/bin/env python3
"""usage: mutate.py <suite> <file-relative-to-WT> <rows.json>   rows: [{"name":..., "old":..., "new":..., "tests": optional -k filter}]
Each row replaces exactly one occurrence, runs the suite, restores the file byte for byte, and records red/green."""
import json, subprocess, sys, shutil, os
from pathlib import Path
WT = Path("/Users/dadleet/src/skill-craft/.claude/worktrees/b1011z-aaa47e/.claude/worktrees/b1012r-1bbefb")
suite, rel, rows_path = sys.argv[1], sys.argv[2], sys.argv[3]
target = WT / rel
original = target.read_bytes()
backup = Path(os.environ.get("TMPDIR", "/tmp")) / "mutate-backup.bin"
rows = json.load(open(rows_path))
results = []
env = dict(os.environ, SHIPLOOP_PROGRESS="off", SHIPLOOP_KEEPALIVE="off")
try:
    for row in rows:
        text = original.decode()
        if text.count(row["old"]) != 1:
            results.append((row["name"], "BAD PATTERN (count %d)" % text.count(row["old"]))); continue
        target.write_text(text.replace(row["old"], row["new"]))
        cmd = [sys.executable, "-B", str(WT / "test" / (suite + ".test.py"))] + row.get("args", [])
        done = subprocess.run(cmd, cwd=WT, env=env, capture_output=True, text=True)
        tail = [l for l in (done.stderr + done.stdout).splitlines() if l.startswith(("FAIL:", "ERROR:"))][:3]
        results.append((row["name"], "RED" if done.returncode else "GREEN (survived)", tail))
finally:
    target.write_bytes(original)
record = Path(os.environ.get("MUTATION_RECORD", "")) if os.environ.get("MUTATION_RECORD") else None
for r in results:
    print(r[:2], (r[2][:1] if len(r) > 2 else ""))
    if record:
        with record.open("a") as handle:
            handle.write(json.dumps({"label": os.environ.get("MUTATION_LABEL", ""), "suite": suite, "file": rel, "mutant": r[0],
                                     "result": r[1], "first_failure": (r[2][0] if len(r) > 2 and r[2] else "")}) + "\n")
