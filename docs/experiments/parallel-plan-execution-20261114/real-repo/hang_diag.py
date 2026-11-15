#!/usr/bin/env python3
"""hang_diag.py TREE N: run `node --test` in TREE up to N times with a 30 s limit (a normal run takes about 1.5 s); on the first hang, list the processes still alive in the
run's process group (each test file runs in its own child, so the one left running is the one that hung), then kill the group. Own processes only."""
import os
import signal
import subprocess
import sys

tree, n = sys.argv[1], int(sys.argv[2])
for i in range(n):
    p = subprocess.Popen(["node", "--test"], cwd=tree, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        out, _ = p.communicate(timeout=30)
        continue
    except subprocess.TimeoutExpired:
        pgid = os.getpgid(p.pid)
        alive = subprocess.run(["ps", "-axo", "pid,pgid,etime,pcpu,command"], capture_output=True, text=True).stdout.splitlines()
        mine = [line for line in alive if line.split(None, 2)[1:2] == [str(pgid)]]
        print(f"run {i + 1}: HUNG after 30 s; processes alive in its group:")
        for line in mine:
            print("  " + line[:240])
        os.killpg(pgid, signal.SIGKILL)
        try:
            p.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        sys.exit(0)
print(f"{n} runs, no hang")
