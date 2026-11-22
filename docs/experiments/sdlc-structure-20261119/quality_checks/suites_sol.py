#!/usr/bin/env python3
"""Sol pairs: each delivery's own suite, plain, started from another folder, and with no npm on PATH (round 13)."""
import glob, json, os, re, shutil, signal, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(sys.argv[1])
BASE_ENV = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "TMPDIR": os.environ.get("TMPDIR", "/tmp")}
node = shutil.which("node"); only_node = Path(tempfile.mkdtemp(prefix="qn-")); os.symlink(node, only_node / "node")


def run(args, cwd, label, env=None):
    t0 = time.time()
    p = subprocess.Popen([node, "--test", *args], cwd=cwd, env={**BASE_ENV, **(env or {})}, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        text, _ = p.communicate(timeout=120); code = p.returncode
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL); text, _ = p.communicate(); code = "no end within 120 s"

    def n(word):
        m = re.findall(rf"^[#ℹ] {word} (\d+)", text, re.M)
        return int(m[-1]) if m else None
    print(json.dumps({"run": label, "exit": code, "tests": n("tests"), "pass": n("pass"), "fail": n("fail"),
                      "seconds": round(time.time() - t0)}), flush=True)


trees = {f"{p}/{s}": ROOT / p / s for p in ("due-1", "due-2", "expenses-1", "expenses-2") for s in "XY"}
trees["base"] = ROOT / "base-due"
for name, tree in trees.items():
    run([], tree, f"{name} plain")
elsewhere = tempfile.mkdtemp(prefix="qe-")
for name, tree in trees.items():
    if name.startswith("due") or name == "base":
        run(sorted(glob.glob(str(tree / "test" / "*.test.js"))), elsewhere, f"{name} started from another folder")
        run([], tree, f"{name} with no npm on PATH", {"PATH": str(only_node)})
