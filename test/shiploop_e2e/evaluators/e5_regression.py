#!/usr/bin/env python3
"""E5: does each Improve fix carry a test that fails when the fix is reverted?

    python3 test/shiploop_e2e/evaluators/e5_regression.py score <sample>
    python3 test/shiploop_e2e/evaluators/e5_regression.py verify

- ``defect``: the case's seeded-defect probe on the final tree (seeded_defects.score): caught or not.
- Improve fix commits: commits in the product worktree since the seed whose message has a ``Key learnings:`` line (the
  form improve-commit enforces) and that change a product file (not a test, not docs/shiploop/ or run evidence).
  For each: the test it names (a ``Regression test:`` line naming a test file or test name), else the test files the
  commit changed. In a copy of the final tree, the commit's product files are put back to their parent version and the
  named test runs: ``fails_before_fix`` when it then fails (and passes on the final tree).
``value`` is 1 when there is at least one fix and every fix has a test that fails before it, else 0 (None: no worktree).
``verify``: seeded_defects verify for the case's probe, and a planted repository where a fix with a real regression test
is credited and a fix with none (or a test that passes without the fix) is not.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

CASE = "node-seeded-early-validation"
_LEARN = re.compile(r"^(Key learnings|Lessons|Learned):", re.M | re.I)
_NAMED = re.compile(r"^Regression test:\s*(.+)$", re.M | re.I)
_TEST = re.compile(r"(^|/)(test|tests|__tests__)/|\.test\.|\.spec\.|_test\.")
_OWN = ("docs/shiploop/", ".shiploop-improve/")
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def _git(tree: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(tree), *args], capture_output=True, text=True, env=GIT_ENV).stdout


def fix_commits(tree: Path, since: str) -> list[dict]:
    rows = []
    for sha in _git(tree, "rev-list", "--reverse", f"{since}..HEAD").split():
        message = _git(tree, "log", "-1", "--format=%B", sha)
        if not _LEARN.search(message):
            continue
        files = [p for p in _git(tree, "diff-tree", "--no-commit-id", "--name-only", "-r", sha).splitlines() if p]
        product = [p for p in files if not _TEST.search(p) and not p.startswith(_OWN)]
        if not product:
            continue
        named = _NAMED.search(message)
        rows.append({"sha": sha[:12], "full": sha, "product": product, "tests": [p for p in files if _TEST.search(p)],
                     "named": named.group(1).strip() if named else None})
    return rows


def _test_command(named: str | None, tests: list[str], tree: Path) -> str | None:
    if named:
        first = named.split()[0].strip("`'\",")
        if (tree / first).is_file():
            return f"node --test {first}"
        return f"node --test --test-name-pattern={named!r}"
    return ("node --test " + " ".join(tests)) if tests else None


def judge_fix(tree: Path, fix: dict) -> dict:
    command = _test_command(fix["named"], fix["tests"], tree)
    if command is None:
        return {**fix, "test": None, "fails_before_fix": False}
    with tempfile.TemporaryDirectory() as tmp:
        after = common.copy_tree(tree, Path(tmp) / "after")
        passes = common.sh(command, after)["exit"] == 0
        before = common.copy_tree(tree, Path(tmp) / "before")
        for path in fix["product"]:
            old = subprocess.run(["git", "-C", str(tree), "show", f"{fix['full']}^:{path}"], capture_output=True,
                                 env=GIT_ENV)
            if old.returncode == 0:
                (before / path).write_bytes(old.stdout)
            elif (before / path).exists():
                (before / path).unlink()
        fails = common.sh(command, before)["exit"] != 0
    return {**{k: v for k, v in fix.items() if k != "full"}, "test": command, "passes_after": passes,
            "fails_before_fix": passes and fails}


def judge(tree: Path, since: str) -> dict:
    fixes = [judge_fix(tree, fix) for fix in fix_commits(tree, since)]
    return {"value": int(bool(fixes) and all(f["fails_before_fix"] for f in fixes)), "fixes": fixes,
            "with_test": sum(1 for f in fixes if f["test"]), "fails_before_fix": sum(1 for f in fixes if f["fails_before_fix"])}


def score(sample: Path) -> dict:
    import seeded_defects  # noqa: PLC0415
    tree = common.worktree(sample)
    if tree is None or not tree.is_dir():
        return {"value": None, "why": "no final tree"}
    import json  # noqa: PLC0415
    since = json.loads((Path(sample) / "invocation.json").read_text())["seeded"]["start_head"]
    found = judge(tree, since)
    probe = seeded_defects.score(common.case(CASE), tree)
    found["defect_caught"] = not probe["present"]
    return found


def _planted(tmp: Path, with_test: bool, real: bool) -> tuple[Path, str]:
    """A repository at the naive tree, then one Improve fix commit, with or without a regression test."""
    case = common.case(CASE)
    tree = common.copy_tree(common.FIXTURES / case["fixture"], tmp)
    common.copy_tree(common.FIXTURES / case["seeded_defect"]["tree"] / "naive", tree)
    who = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    for args in (["init", "-q"], ["add", "-A"], [*who, "commit", "-qm", "naive"]):
        subprocess.run(["git", "-C", str(tree), *args], check=True, capture_output=True, env=GIT_ENV)
    base = _git(tree, "rev-parse", "HEAD").strip()
    fixed = common.FIXTURES / case["seeded_defect"]["tree"] / "fixed"
    (tree / "src/basket.js").write_text((fixed / "src/basket.js").read_text())
    message = "Validate the limit after it is set\n\nKey learnings: validate an input only after it is assigned\n"
    if with_test:
        test = (fixed / "test/basket.test.js").read_text()
        if not real:  # a test that passes with or without the fix
            test = test.replace("for (const limit of [0, -1, 1.5, '2', undefined])", "for (const limit of [])")
        (tree / "test/basket.test.js").write_text(test)
        message += "Regression test: test/basket.test.js\n"
    subprocess.run(["git", "-C", str(tree), "add", "-A"], check=True, env=GIT_ENV)
    subprocess.run(["git", "-C", str(tree), *who, "commit", "-qm", message], check=True, env=GIT_ENV)
    return tree, base


def verify() -> list[dict]:
    import seeded_defects  # noqa: PLC0415
    rows = [{"check": "seeded_defects verify", "rows": seeded_defects.verify(CASE),
             "ok": all(r["ok"] for r in seeded_defects.verify(CASE))}]
    for label, with_test, real, expect in (("fix with a real regression test", True, True, 1),
                                           ("fix with no test", False, False, 0),
                                           ("fix with a test that passes without it", True, False, 0)):
        with tempfile.TemporaryDirectory() as tmp:
            tree, base = _planted(Path(tmp) / "repo", with_test, real)
            found = judge(tree, base)
        rows.append({"check": label, "expect": expect, "got": found["value"], "fixes": len(found["fixes"]),
                     "ok": found["value"] == expect and len(found["fixes"]) == 1})
    return rows


if __name__ == "__main__":
    raise SystemExit(common.cli(sys.modules[__name__], sys.argv[1:]))
