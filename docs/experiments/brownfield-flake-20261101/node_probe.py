#!/usr/bin/env python3
"""Micro-probe: run the base's own `node --test` many times at once, as the calibration suite does, and keep every failing run's error lines.

    python3 node_probe.py FIXTURE_DIR [CONCURRENCY] [ROUNDS] [TAG]

Copies FIXTURE_DIR (test/shiploop_e2e/fixtures/node-tickets) CONCURRENCY times, runs `node --test` in all copies at once, ROUNDS times, and prints
one JSON line: runs, failures, and for each failure the failing test names and the lines that name the error. Writes nothing but temp folders (removed).
"""

import collections
import concurrent.futures
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

fixture = Path(sys.argv[1]).resolve()
concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 16
rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 5
tag = sys.argv[4] if len(sys.argv) > 4 else ""
root = Path(tempfile.mkdtemp(prefix="node-probe-"))
copies = []
for i in range(concurrency):
    target = root / f"c{i}"
    shutil.copytree(fixture, target, ignore=shutil.ignore_patterns("node_modules", ".git"))
    copies.append(target)


def one(folder: Path) -> dict:
    began = time.monotonic()
    done = subprocess.run(["node", "--test"], cwd=folder, capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
    text = done.stdout + "\n" + done.stderr
    names = re.findall(r"^\s*✖ (.+?) \(", text, re.M)
    errors = [ln.strip() for ln in text.splitlines() if re.search(r"Error:|code:|ECONN|EADDR|hang up|ETIMEDOUT|timed out", ln)]
    block = text[text.find("failing tests:"):][:2600] if "failing tests:" in text else text[-2600:]
    return {"rc": done.returncode, "seconds": round(time.monotonic() - began, 1), "failed_tests": names[:6], "error_lines": errors[:8], "block": block}


results = []
started = time.monotonic()
for round_number in range(rounds):
    with concurrent.futures.ThreadPoolExecutor(concurrency) as pool:
        results.extend(pool.map(one, copies))
failures = [r for r in results if r["rc"] != 0]
signatures = collections.Counter()
for r in failures:
    blob = " ".join(r["error_lines"])
    signatures["socket hang up/ECONNRESET" if re.search(r"hang up|ECONNRESET", blob) else
               "refused/in use/timeout" if re.search(r"ECONNREFUSED|EADDRINUSE|ETIMEDOUT|timed out", blob) else
               "wrong answer (ERR_ASSERTION)" if "ERR_ASSERTION" in blob else "other"] += 1
print(json.dumps({"tag": tag, "concurrency": concurrency, "rounds": rounds, "runs": len(results), "failures": len(failures),
                  "seconds": round(time.monotonic() - started, 1), "load": os.getloadavg()[0], "signatures": dict(signatures),
                  "failing": failures}))
shutil.rmtree(root, ignore_errors=True)
