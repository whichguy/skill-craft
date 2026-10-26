"""What every experiment evaluator reads: a sample's records, never its transcript, and never a model's judgement.

A sample is a slice output folder (slice.py --output): invocation.json names the run folder, whose results/ and tests/
hold ShipLoop's accepted results and gate records (each a Markdown file with one ```shiploop-state JSON block), and whose
sibling worktree/ holds the final tree. Each evaluator module exposes ``score(sample) -> dict`` (``value`` is the number
experiment.py decides on, higher is better; None when the sample cannot be scored) and ``verify() -> list[dict]`` (each
row has ``ok``): planted-bad output detected, planted-good not.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
E2E = HERE.parent
FIXTURES = E2E / "fixtures"
STEP_CASES = E2E / "step_cases.json"
TIMEOUT_SECONDS = 120
_BLOCK = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)
# Run 4 (2026-10-20, chess, read-only): the records E2 and E3 verify against.
RUN4 = Path("/Users/dadleet/e2e-runs/20261020/chess-sf-full-9e52e8/.shiploop-runs/work-20261021-030256-ada3c6")
RUN4_STEP_PLAN = "nav-0075307f416b447f8ed245e2dac220b5"
RUN4_TEST_STRATEGY = "nav-2214de28670440dfac04d19c1b63cbb3"


def case(name: str) -> dict:
    return json.loads(STEP_CASES.read_text())[name]


def read_block(path: Path) -> dict | None:
    try:
        found = _BLOCK.search(Path(path).read_text())
        return json.loads(found.group(1)) if found else None
    except (OSError, ValueError):
        return None


def run_dir(sample: Path) -> Path | None:
    try:
        return Path(json.loads((Path(sample) / "invocation.json").read_text())["seeded"]["run_dir"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def worktree(sample: Path) -> Path | None:
    found = run_dir(sample)
    return found.parent / "worktree" if found else None


def results(folder: Path | None, stage: str | None = None) -> list[dict]:
    """Accepted results under ``folder``/results (the run folder), oldest first, optionally of one stage."""
    if folder is None or not (folder / "results").is_dir():
        return []
    rows = [read_block(p) for p in (folder / "results").glob("nav-*.md")]
    rows = [r for r in rows if isinstance(r, dict) and (stage is None or r.get("stage") == stage)]
    return sorted(rows, key=lambda r: (folder / "results" / f"{r.get('action')}.md").stat().st_mtime
                  if (folder / "results" / f"{r.get('action')}.md").exists() else 0)


def base_runs(folder: Path | None) -> list[dict]:
    """The test gate's base-run records (tests/*-base<n>.md), oldest first."""
    if folder is None or not (folder / "tests").is_dir():
        return []
    paths = sorted((folder / "tests").glob("*-base*.md"), key=lambda p: p.stat().st_mtime)
    return [r for r in (read_block(p) for p in paths) if isinstance(r, dict)]


def sh(command: str, cwd: Path, env: dict | None = None) -> dict:
    try:
        done = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
                              env=env)
    except subprocess.TimeoutExpired:
        return {"command": command, "exit": None, "output": f"timed out after {TIMEOUT_SECONDS} s"}
    return {"command": command, "exit": done.returncode, "output": (done.stdout + done.stderr)[-1500:]}


def copy_tree(source: Path, into: Path) -> Path:
    shutil.copytree(source, into, ignore=shutil.ignore_patterns(".git", "node_modules", ".shiploop-improve"),
                    dirs_exist_ok=True)
    return into


def cli(module, argv: list[str]) -> int:
    """``verify`` or ``score <sample>`` for one evaluator module, printing JSON."""
    if argv[:1] == ["verify"]:
        rows = module.verify()
        print(json.dumps(rows, indent=2))
        return 0 if rows and all(r["ok"] for r in rows) else 1
    if argv[:1] == ["score"] and len(argv) == 2:
        print(json.dumps(module.score(Path(argv[1])), indent=2))
        return 0
    print(module.__doc__)
    return 2
