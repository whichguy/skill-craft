#!/usr/bin/env python3
"""E1: do the item's tests reject weaker implementations (stand-ins)?

    python3 test/shiploop_e2e/evaluators/e1_stand_ins.py score <sample>
    python3 test/shiploop_e2e/evaluators/e1_stand_ins.py verify

For each stand-in the case names (fixtures/stand-ins/<case>/<name>/, kept outside the product repository), a copy of the
final tree gets the stand-in's files laid over it and the case's ``focused`` command runs: ``killed`` when it fails,
``survived`` when it passes. The tree's own run of that command must pass first, or nothing is scored. ``value`` is 1
when every stand-in is killed, else 0. ``error_rows`` counts the test-spec rows whose oracle or RED names a thrown error.
``verify``: on the reference implementation with a weak test file (absence asserts only) every stand-in survives; with a
strong one every stand-in is killed.
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

CASE = "stand-in-parser"
_ERROR = re.compile(r"\b(throw|throws|thrown|reject|rejects|refus\w*|\w*Error)\b", re.I)


def judge(tree: Path, case: dict, case_name: str = CASE) -> dict:
    stand_ins = common.FIXTURES / "stand-ins" / case_name
    with tempfile.TemporaryDirectory() as tmp:
        own = common.sh(case["focused"], common.copy_tree(tree, Path(tmp) / "own"))
        rows = {}
        for name in case["stand_ins"]:
            copy = common.copy_tree(tree, Path(tmp) / name)
            common.copy_tree(stand_ins / name, copy)
            ran = common.sh(case["focused"], copy)
            rows[name] = {"result": "killed" if ran["exit"] != 0 else "survived", "exit": ran["exit"]}
    if own["exit"] != 0:
        return {"value": None, "own_tests_pass": False, "own": own, "stand_ins": rows,
                "why": "the final tree's own focused command fails, so a stand-in's failure proves nothing"}
    killed = sorted(n for n, r in rows.items() if r["result"] == "killed")
    return {"value": int(len(killed) == len(rows)), "own_tests_pass": True, "killed": killed,
            "killed_fraction": round(len(killed) / len(rows), 4) if rows else None, "stand_ins": rows}


def score(sample: Path, case_name: str = CASE) -> dict:
    tree = common.worktree(sample)
    if tree is None or not tree.is_dir():
        return {"value": None, "why": "no final tree"}
    found = judge(tree, common.case(case_name), case_name)
    spec = common.results(common.run_dir(sample), "test-spec")
    cases = (spec[-1].get("result") or {}).get("test_cases") or [] if spec else []
    found["error_rows"] = sum(1 for row in cases if _ERROR.search(f"{row.get('oracle', '')} {row.get('red', '')}"))
    found["test_cases"] = len(cases)
    return found


def verify(case_name: str = CASE) -> list[dict]:
    case = common.case(case_name)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for kind, expect in (("weak-tests", "survived"), ("strong-tests", "killed")):
            tree = common.copy_tree(common.FIXTURES / case["fixture"], Path(tmp) / kind)
            common.copy_tree(common.FIXTURES / "stand-ins" / case_name / "reference", tree)
            common.copy_tree(common.FIXTURES / "stand-ins" / case_name / kind, tree)
            found = judge(tree, case, case_name)
            got = {r["result"] for r in found["stand_ins"].values()}
            rows.append({"tree": kind, "expect": expect, "got": found["stand_ins"], "own_tests_pass": found["own_tests_pass"],
                         "ok": found["own_tests_pass"] and got == {expect}})
    return rows


if __name__ == "__main__":
    raise SystemExit(common.cli(sys.modules[__name__], sys.argv[1:]))
