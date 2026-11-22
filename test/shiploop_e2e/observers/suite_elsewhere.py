#!/usr/bin/env python3
"""An observation, never a verdict: does the delivery's own node:test suite give the same result when npm is not on
PATH, and when it is started from another folder?

The requests ask for tests that `npm test` or `node --test` runs in the project, so a suite that only passes there is
not wrong by the request; this records how much it leans on where and how it was started. The same files are run each
time, named by their full paths, with a scratch HOME and a stated PATH, each run in its own process group under a
180 s ceiling.

Usage: python3 suite_elsewhere.py DELIVERED_TREE       prints one JSON object
Exit 0 whatever the delivery does; 2 for a usage error; 3 when no test file is found.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

VERSION = 1
LEFT_OUT = ("node_modules", "fixtures", "test-fixtures")
CEILING_SECONDS = 180


def test_files(tree: Path) -> list[str]:
    found = []
    for pattern in ("*.test.js", "*.test.mjs", "*.test.cjs"):
        for path in tree.rglob(pattern):
            if not set(path.relative_to(tree).parts) & set(LEFT_OUT):
                found.append(str(path))
    return sorted(found)


def run(node: str, files: list[str], cwd: Path, env: dict[str, str]) -> dict:
    begun = time.monotonic()
    process = subprocess.Popen([node, "--test", *files], cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        text, _ = process.communicate(timeout=CEILING_SECONDS)
        code: int | str = process.returncode
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        text, _ = process.communicate()
        code = f"no end within {CEILING_SECONDS} s"

    def count(word: str) -> int | None:
        found = re.findall(rf"^[#ℹ] {word} (\d+)", text, re.M)
        return int(found[-1]) if found else None
    return {"exit": code, "tests": count("tests"), "pass": count("pass"), "fail": count("fail"),
            "seconds": round(time.monotonic() - begun, 1)}


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not Path(argv[0]).is_dir():
        print("usage: suite_elsewhere.py DELIVERED_TREE", file=sys.stderr)
        return 2
    tree = Path(argv[0]).resolve()
    node = shutil.which("node")
    files = test_files(tree)
    out: dict = {"schema": "shiploop-e2e-observation/v1", "observer": "suite-elsewhere", "version": VERSION,
                 "test_files": len(files)}
    if not node or not files:
        out["summary"] = "not measured: " + ("no node on PATH" if not node else "no *.test.js file found")
        print(json.dumps(out))
        return 3
    with tempfile.TemporaryDirectory(prefix="suite-elsewhere-") as scratch:
        home, elsewhere, only_node = (Path(scratch) / name for name in ("home", "elsewhere", "bin"))
        for folder in (home, elsewhere, only_node):
            folder.mkdir()
        os.symlink(node, only_node / "node")
        usual = {"HOME": str(home), "TMPDIR": scratch, "PATH": os.pathsep.join([str(Path(node).parent), "/usr/bin", "/bin"])}
        bare = {**usual, "PATH": os.pathsep.join([str(only_node), "/usr/bin", "/bin"])}
        out["npm_on_the_usual_path"] = shutil.which("npm", path=usual["PATH"]) is not None
        out["in_the_project_folder"] = run(node, files, tree, usual)
        out["in_the_project_folder_without_npm"] = run(node, files, tree, bare)
        out["from_another_folder"] = run(node, files, elsewhere, usual)
    here, without, there = (out[key] for key in ("in_the_project_folder", "in_the_project_folder_without_npm",
                                                 "from_another_folder"))
    if None in (here["fail"], there["fail"], without["fail"]):
        out["summary"] = "not measured: a run printed no count"
    else:
        bare_more, more = without["fail"] - here["fail"], there["fail"] - here["fail"]
        parts = [f"{here['pass']} of {here['tests']} pass in the project folder",
                 "the same without npm" if bare_more == 0 else f"{bare_more} more fail without npm",
                 "the same from another folder" if more == 0 else f"{more} more fail from another folder"]
        out["summary"] = "; ".join(parts)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
