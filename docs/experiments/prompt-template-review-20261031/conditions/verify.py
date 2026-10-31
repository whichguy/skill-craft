#!/usr/bin/env python3
"""Parent check of the per-run condition test (plan.md, "Checks by the parent").

For each run, on fresh copies of the final worktree (``.git`` left out, so nothing touches the original's metadata):
every survivor's witness must pass on the unchanged copy and fail on its patched copy, while the run's full suite
passes on that patched copy; and up to three killed conditions, chosen by a seeded draw, must fail the suite. Patches
are applied with ``patch -p1``. Prints one line per check and exits 1 when any check disagrees with results.json.
Usage: ``python3 verify.py KEY [KEY ...]``.
"""
from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH = Path("/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/"
               "scratchpad/verify")
SUITES = {
    "codex-r2-user-listing": "npm test",
    "claude-csv-report": "python3 -m unittest",
    "v2170-ds-battleship": "node --test && node browser-check/page.js && node system-check/system.js",
    "bf-ds-ticket-assignment": "npm test",
    "grok-web-battleship": "node --test --test-reporter=spec",
}
RUNNER = {".py": ["python3"], ".js": ["node"], ".sh": ["bash"]}


def fresh(key: str, name: str) -> Path:
    spec = json.loads((HERE / (key + ".requirements.json")).read_text())
    target = SCRATCH / key / name
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(spec["repo"], target, ignore=shutil.ignore_patterns(".git", "__pycache__"), symlinks=True)
    return target


def run(command: list[str] | str, cwd: Path, work: Path, timeout: int = 600) -> int:
    env = dict(os.environ, WORK=str(work), PYTHONDONTWRITEBYTECODE="1")
    done = subprocess.run(command, cwd=cwd, env=env, shell=isinstance(command, str), capture_output=True,
                          text=True, timeout=timeout, check=False)
    return done.returncode


def locate(key: str, name: str) -> Path:
    """A results.json path, written relative to the run folder, to this folder, or absolute."""
    for path in (HERE / key / name, HERE / name, Path(name)):
        if path.is_file():
            return path
    raise SystemExit(f"{key}: no file {name}")


def witness(key: str, row: dict, work: Path) -> int:
    path = locate(key, row["witness"])
    return run(RUNNER[path.suffix] + [str(path)], path.parent, work)


def patched(key: str, row: dict, name: str) -> Path:
    work = fresh(key, name)
    patch = locate(key, row["patch"]).read_text()
    done = subprocess.run(["patch", "-p1", "-s"], cwd=work, input=patch, text=True, capture_output=True, check=False)
    if done.returncode:
        raise SystemExit(f"{key} {row['id']}: patch failed: {done.stdout}{done.stderr}")
    return work


def main() -> int:
    bad = 0
    for key in sys.argv[1:]:
        result = json.loads((HERE / key / "results.json").read_text())
        rows = result["conditions"]
        suite = SUITES[key]
        original = fresh(key, "original")
        base = run(suite, original, original)
        print(f"{key}: suite on unchanged copy exit {base}")
        bad += base != 0
        survivors = [row for row in rows if row.get("verdict") == "survived"]
        killed = [row for row in rows if row.get("verdict") == "killed" and row.get("patch")]
        sample = random.Random(311031).sample(killed, min(3, len(killed)))
        for row in survivors:
            work = patched(key, row, "variant")
            w0, w1, s1 = witness(key, row, original), witness(key, row, work), run(suite, work, work)
            ok = w0 == 0 and w1 != 0 and s1 == 0
            bad += not ok
            print(f"  survived {row['id']:8} witness orig {w0} variant {w1} suite {s1}  {'OK' if ok else 'DISAGREES'}")
        for row in sample:
            work = patched(key, row, "variant")
            s1 = run(suite, work, work)
            bad += s1 == 0
            print(f"  killed   {row['id']:8} suite {s1}  {'OK' if s1 else 'DISAGREES'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
