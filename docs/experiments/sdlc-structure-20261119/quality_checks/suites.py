#!/usr/bin/env python3
"""Run each delivery's own test suite, plain and under the judges' test claims (round 13).

The argument is a folder holding <pair>/<side> product trees (copies of judge A's packets, with no git data).
Each run is `node --test` in a clean environment, in its own process group, with a 90 s limit; a run that does
not end is stopped with its group. Changed trees are temporary copies. Prints one JSON line per run.
Usage: python3 -I suites.py <folder of trees>
"""
import json, os, re, shutil, signal, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(sys.argv[1])
BASE_ENV = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "TMPDIR": os.environ.get("TMPDIR", "/tmp")}


def run(tree, label, env=None):
    t0 = time.time()
    p = subprocess.Popen(["node", "--test"], cwd=tree, env={**BASE_ENV, **(env or {})}, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        text, _ = p.communicate(timeout=90); code = p.returncode
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL); text, _ = p.communicate(); code = "no end within 90 s"

    def n(word):
        m = re.findall(rf"^[#ℹ] {word} (\d+)", text, re.M)
        return int(m[-1]) if m else None
    print(json.dumps({"run": label, "exit": code, "tests": n("tests"), "pass": n("pass"), "fail": n("fail"),
                      "seconds": round(time.time() - t0)}), flush=True)


def copy(tree):
    d = Path(tempfile.mkdtemp(prefix="qs-")) / "t"
    shutil.copytree(tree, d)
    return d


trees = {f"{p}/{s}": ROOT / p / s for p in ("due-1", "due-2", "expenses-1", "expenses-2") for s in "XY"}
for name, tree in trees.items():
    run(tree, f"{name} plain")
for name, tree in trees.items():
    if name.startswith("due"):
        run(tree, f"{name} with DUE_HOURS_URGENT=2 in the caller's environment", {"DUE_HOURS_URGENT": "2"})
for name, tree in trees.items():
    if not name.startswith("due"):
        continue
    d = copy(tree); f = d / "src" / "server.js"
    new, k = re.subn(r",\s*dueHours:\s*config\.dueHours(\s*\?\?\s*DEFAULT_DUE_HOURS)?", "", f.read_text())
    f.write_text(new)
    run(d, f"{name} with the hours no longer passed to the store in src/server.js ({k} edit)")
d = copy(trees["due-1/X"]); f = d / "docs" / "operations.md"; t = f.read_text()
f.write_text(t.replace("holds them", "contains them"))
run(d, f"due-1/X with 'holds them' reworded in docs/operations.md ({t.count('holds them')} place)")
