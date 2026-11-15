#!/usr/bin/env python3
"""flake_loop.py TREE N [LIMIT_S]: run `node --test` in TREE N times, one after the other, and say how many runs failed or hung and which tests failed.

Own process only: each run is a child of this script with a limit of LIMIT_S seconds (default 120, the oracle's own limit; a normal run takes 1 to 5 s even on a
busy machine); a hung run is killed with its process group.
"""
import collections
import os
import re
import signal
import subprocess
import sys
import time

tree, n = sys.argv[1], int(sys.argv[2])
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 120
fails = collections.Counter()
bad = hung = 0
started = time.time()
for i in range(n):
    p = subprocess.Popen(["node", "--test"], cwd=tree, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        out, _ = p.communicate(timeout=limit)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        out, _ = p.communicate()
        hung += 1
        print(f"run {i + 1}: HUNG (killed at {limit} s)", flush=True)
        continue
    if p.returncode != 0:
        bad += 1
        names = re.findall(r"^\s*✖ (.+?) \(", out, flags=re.M)
        for name in names:
            fails[name] += 1
        print(f"run {i + 1}: rc {p.returncode}, failed: {names[:4]}", flush=True)
print(f"{tree}: {n} runs, {bad} failed, {hung} hung, {time.time() - started:.0f} s; failing tests: {dict(fails)}")
