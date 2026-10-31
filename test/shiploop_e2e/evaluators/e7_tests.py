#!/usr/bin/env python3
"""E7: do the item's tests kill mutants of the product lines the slice wrote, above all limits and guard clauses?

    python3 test/shiploop_e2e/evaluators/e7_tests.py score <sample>
    python3 test/shiploop_e2e/evaluators/e7_tests.py verify

The product lines are the JavaScript source lines the final tree adds or changes against the slice's seed commit
(invocation.json ``seeded.start_head``): tracked changes by ``git diff -U0`` and every line of an untracked file, never a
test file, a dependency or a ShipLoop record (quality.JS_TEST_FILE, quality.JS_NOT_SOURCE_FOLDERS). Every ``js-1`` site
(quality.sites) on those lines is laid over a copy of the tree, one at a time, and the case's ``mutation`` command
(else ``focused``) runs: ``killed`` when it fails or times out, ``survived`` when it passes. The tree's own run must pass
first, or nothing is scored.

``value`` is the killed fraction of the TARGET classes, ``rel-bound`` and ``logic-flip``: a limit moved by one or a
compound guard's clauses swapped, the 40 of 57 product survivors of docs/shiploop-test-stage-prompt-design-2026-10-30.md
§3. ``all_ratio`` is the killed fraction of every class. Recorded, not scored: the stand-in kill fraction (when the case
names stand-ins, as E1b), the new test files' titles per case ID and assertion calls per title, and the test stage's
seconds from metrics.json. ``verify``: the stand-in-rules reference with the weak test file scores below the same
reference with the strong file and the boundary file (fixtures/stand-ins/stand-in-rules/boundary-tests).
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

sys.path.insert(0, str(common.E2E))
import quality  # noqa: E402  (the js-1 catalog: sites, JS_TEST_FILE, JS_NOT_SOURCE_FOLDERS, OPERATOR_ID)

TARGET = ("rel-bound", "logic-flip")
MUTANT_SECONDS = 60
SOURCE = (".js", ".cjs", ".mjs")
_ID = re.compile(r"\bTC[-_]\d+\b")
_TITLE = re.compile(r"\b(describe|test|it)(?:\.\w+)?\s*\(\s*(['\"`])((?:\\.|(?!\2).)*)\2")
_ASSERT = re.compile(r"\bassert(?:\.\w+)?\s*\(|\bexpect\s*\(|\bt\.assert\.\w+\s*\(")


def _git(tree: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(tree), *args], capture_output=True, text=True, check=True).stdout


def _product(path: str) -> bool:
    parts = path.split("/")
    return (path.endswith(SOURCE) and not quality.JS_TEST_FILE.search(path)
            and not any(part in quality.JS_NOT_SOURCE_FOLDERS or part.startswith(".shiploop") for part in parts[:-1]))


def changed_lines(tree: Path, seed: str) -> dict[str, set[int]]:
    """Per product file, the 1-based lines the tree adds or changes against ``seed`` (untracked files: every line)."""
    out: dict[str, set[int]] = {}
    current = None
    for line in _git(tree, "diff", "-U0", "--no-renames", seed, "--").splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
            continue
        found = re.match(r"@@ -\S+ \+(\d+)(?:,(\d+))? @@", line)
        if found and current and _product(current):
            start, count = int(found.group(1)), int(found.group(2) or 1)
            out.setdefault(current, set()).update(range(start, start + count))
    for path in _git(tree, "ls-files", "--others", "--exclude-standard").splitlines():
        if _product(path) and (tree / path).is_file():
            out[path] = set(range(1, len((tree / path).read_text(errors="ignore").splitlines()) + 1))
    return {path: lines for path, lines in out.items() if lines}


def new_test_files(tree: Path, seed: str) -> list[str]:
    changed = _git(tree, "diff", "--name-only", "--no-renames", seed, "--").splitlines()
    changed += _git(tree, "ls-files", "--others", "--exclude-standard").splitlines()
    return sorted({p for p in changed if p.endswith(SOURCE) and quality.JS_TEST_FILE.search(p) and (tree / p).is_file()})


def run(command: str, cwd: Path) -> tuple[int | None, str]:
    proc = subprocess.Popen(command, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            start_new_session=True, env={**os.environ, "CI": "1", "NODE_OPTIONS": ""})
    try:
        output, _ = proc.communicate(timeout=MUTANT_SECONDS)
        return proc.returncode, output[-3000:]
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return None, "timeout"


def mutate(tree: Path, lines: dict[str, set[int]], command: str) -> dict:
    """Every js-1 site on ``lines`` of ``tree`` (a copy is mutated, never ``tree``), killed or survived."""
    with tempfile.TemporaryDirectory() as tmp:
        copy = common.copy_tree(tree, Path(tmp) / "tree")
        own, output = run(command, copy)
        if own != 0:
            return {"own_tests_pass": False, "own_exit": own, "own_output": output[-800:], "mutants": []}
        mutants = []
        for rel in sorted(lines):
            path = copy / rel
            source = path.read_text()
            for site in quality.sites(source):
                if site["line"] not in lines[rel]:
                    continue
                path.write_text(source[:site["start"]] + site["new"] + source[site["end"]:])
                started = time.monotonic()
                code, _ = run(command, copy)
                path.write_text(source)
                mutants.append({"file": rel, "line": site["line"], "op": site["op"], "from": site["old"], "to": site["new"],
                                "status": "survived" if code == 0 else "killed", "timeout": code is None,
                                "text": source.splitlines()[site["line"] - 1].strip()[:140],
                                "seconds": round(time.monotonic() - started, 2)})
    return {"own_tests_pass": True, "mutants": mutants}


def _fraction(rows: list[dict]) -> float | None:
    return round(sum(r["status"] == "killed" for r in rows) / len(rows), 4) if rows else None


def judge(tree: Path, seed: str, command: str) -> dict:
    lines = changed_lines(tree, seed)
    found = mutate(tree, lines, command)
    rows = found["mutants"]
    target = [r for r in rows if r["op"] in TARGET]
    by_op: dict[str, list[int]] = {}
    for r in rows:
        by_op.setdefault(r["op"], [0, 0])[r["status"] == "survived"] += 1
    return {"value": _fraction(target) if found["own_tests_pass"] else None, "operator_id": quality.OPERATOR_ID,
            "own_tests_pass": found["own_tests_pass"], **({k: found[k] for k in ("own_exit", "own_output") if k in found}),
            "product_files": sorted(lines), "changed_lines": sum(len(v) for v in lines.values()),
            "target_total": len(target), "target_survived": sum(r["status"] == "survived" for r in target),
            "all_total": len(rows), "all_survived": sum(r["status"] == "survived" for r in rows),
            "all_ratio": _fraction(rows), "by_op": {op: {"killed": k, "survived": s} for op, (k, s) in sorted(by_op.items())},
            "survivors": [r for r in rows if r["status"] == "survived"],
            "timeouts": sum(r["timeout"] for r in rows)}


def test_shape(tree: Path, seed: str) -> dict:
    """Tests per case ID and assertion calls per test in the test files the slice added or changed.

    A test counts toward the IDs in its own title, else toward those of the last ``describe`` title before it (an
    approximation: nesting is not parsed)."""
    titles, asserts, ids = [], 0, {}
    files = new_test_files(tree, seed)
    for rel in files:
        text = (tree / rel).read_text(errors="ignore")
        asserts += len(_ASSERT.findall(text))
        group: set[str] = set()
        for match in _TITLE.finditer(text):
            kind, title = match.group(1), match.group(3)
            if kind == "describe":
                group = set(_ID.findall(title))
                continue
            titles.append(title)
            for ident in set(_ID.findall(title)) or group:
                ids[ident] = ids.get(ident, 0) + 1
    return {"test_files": files, "test_titles": len(titles), "assert_calls": asserts,
            "asserts_per_title": round(asserts / len(titles), 2) if titles else None,
            "titles_per_id": ids, "mean_titles_per_id": round(sum(ids.values()) / len(ids), 2) if ids else None}


def _stage_seconds(sample: Path, stage: str) -> float | None:
    try:
        stages = json.loads((Path(sample) / "metrics.json").read_text()).get("stages") or []
    except (OSError, ValueError):
        return None
    seconds = [row.get("seconds") for row in stages if row.get("stage") == stage and row.get("seconds") is not None]
    return round(sum(seconds), 1) if seconds else None


def score(sample: Path) -> dict:
    sample = Path(sample)
    tree = common.worktree(sample)
    try:
        invocation = json.loads((sample / "invocation.json").read_text())
        name, seed = invocation["case"], invocation["seeded"]["start_head"]
    except (OSError, ValueError, KeyError, TypeError):
        return {"value": None, "why": "no invocation.json with a case and a seed commit"}
    if tree is None or not tree.is_dir():
        return {"value": None, "why": "no final tree"}
    case = common.case(name)
    found = {"case": name, "seed": seed, **judge(tree, seed, case.get("mutation") or case["focused"]),
             **test_shape(tree, seed),
             "test_seconds": _stage_seconds(sample, "test"), "test_spec_seconds": _stage_seconds(sample, "test-spec"),
             "implement_seconds": _stage_seconds(sample, "implement")}
    if case.get("stand_ins"):
        import e1_stand_ins  # noqa: PLC0415
        stand = e1_stand_ins.judge(tree, case, name)
        found["stand_in_fraction"] = stand.get("killed_fraction")
        found["stand_ins_killed"] = stand.get("killed")
    return found


def verify() -> list[dict]:
    """The stand-in-rules reference scores lower with the weak test file than with the strong and boundary ones."""
    name = "stand-in-rules"
    case = common.case(name)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for kind, layers in (("weak-tests", ("weak-tests",)), ("boundary-tests", ("strong-tests", "boundary-tests"))):
            tree = common.copy_tree(common.FIXTURES / case["fixture"], Path(tmp) / kind)
            subprocess.run(["git", "init", "-q", str(tree)], check=True)
            subprocess.run(["git", "-C", str(tree), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(tree), "-c", "user.name=e7", "-c", "user.email=e7@example.invalid",
                            "commit", "-qm", "seed"], check=True)
            seed = _git(tree, "rev-parse", "HEAD").strip()
            common.copy_tree(common.FIXTURES / "stand-ins" / name / "reference", tree)
            for layer in layers:
                common.copy_tree(common.FIXTURES / "stand-ins" / name / layer, tree)
            found = judge(tree, seed, case.get("mutation") or case["focused"])
            rows.append({"tree": kind, "value": found["value"], "target_total": found["target_total"],
                         "all_ratio": found["all_ratio"], "own_tests_pass": found["own_tests_pass"]})
    weak, strong = rows
    ok = (weak["own_tests_pass"] and strong["own_tests_pass"] and weak["target_total"] > 0
          and None not in (weak["value"], strong["value"]) and weak["value"] < strong["value"])
    for row in rows:
        row["ok"] = ok
    return rows


if __name__ == "__main__":
    raise SystemExit(common.cli(sys.modules[__name__], sys.argv[1:]))
