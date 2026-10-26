#!/usr/bin/env python3
"""E4: on a target that keeps state, does the test gate's base run go red for the item's tests?

    python3 test/shiploop_e2e/evaluators/e4_base_state.py score <sample>
    python3 test/shiploop_e2e/evaluators/e4_base_state.py verify

From ShipLoop's own base-run records (run/tests/*-base<n>.md): the FIRST base run's focused commands. ``first_red`` is
True when each focused command's status was ``red`` (it failed on the item's base), False when one passed there (the
stale target held the item's code: a false RED that ShipLoop refused). ``red_routes``: of the test-spec rows, how many
say how the base state is produced (clean, empty, fresh, reset, --clean, destructive). ``value`` is 1 when the first
base run was red, else 0; None with no base run.
``verify`` reproduces the false RED for real: a target pre-loaded with the item's module, the item's tests on the base
tree, and the naive command passes; the clean-first command fails. The judge then reads a planted refused record as 0
and a planted red record as 1.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

CASE = "stateful-target"
_ROUTE = re.compile(r"\b(clean\w*|empty|emptie\w*|fresh|reset|wip\w*|destructive|--clean|remov\w*)\b", re.I)


def judge(bases: list[dict], test_cases: list[dict]) -> dict:
    routes = sum(1 for row in test_cases if _ROUTE.search(str(row.get("red", ""))))
    first = next((record for record in bases if any(r.get("suite") == "focused" for r in record.get("runs") or [])), None)
    if first is None:
        return {"value": None, "why": "no base run of a focused command", "red_routes": routes, "rows": len(test_cases)}
    statuses = [r.get("status") for r in first.get("runs") or [] if r.get("suite") == "focused"]
    red = all(s == "red" for s in statuses)
    return {"value": int(red), "first_red": red, "first_statuses": statuses, "base_runs": len(bases),
            "red_routes": routes, "rows": len(test_cases)}


def score(sample: Path) -> dict:
    folder = common.run_dir(sample)
    spec = common.results(folder, "test-spec")
    cases = (spec[-1].get("result") or {}).get("test_cases") or [] if spec else []
    return judge(common.base_runs(folder), cases)


def verify() -> list[dict]:
    case = common.case(CASE)
    stand = common.FIXTURES / "stand-ins" / CASE
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "target"
        shutil.copytree(stand / "deployed", target)
        base = common.copy_tree(common.FIXTURES / case["fixture"], Path(tmp) / "base")
        common.copy_tree(stand / "candidate" / "test", base / "test")  # the base run copies only the item's tests in
        env = {**os.environ, case["seed_state"]["env"]: str(target)}
        naive = common.sh("node --test --test-reporter=spec test/pricing.test.js", base, env)
        rows.append({"check": "stale target, naive command, item base", "expect": "passes (false RED)", "exit": naive["exit"],
                     "ok": naive["exit"] == 0})
        shutil.rmtree(target)
        shutil.copytree(stand / "deployed", target)
        clean = common.sh("node scripts/deploy.js --clean && node --test --test-reporter=spec test/pricing.test.js", base, env)
        rows.append({"check": "stale target, clean-first command, item base", "expect": "fails", "exit": clean["exit"],
                     "ok": clean["exit"] not in (0, None)})
    refused = judge([{"runs": [{"suite": "focused", "status": "passes-on-base"}]}, {"runs": [{"suite": "focused", "status": "red"}]}],
                    [{"red": "fails because discount is missing"}])
    good = judge([{"runs": [{"suite": "focused", "status": "red"}, {"suite": "regression", "status": "counted"}]}],
                 [{"red": "fails on the base after a --clean deploy empties the target"}])
    rows.append({"check": "planted refused first base run", "got": refused, "ok": refused["value"] == 0})
    rows.append({"check": "planted red first base run", "got": good, "ok": good["value"] == 1 and good["red_routes"] == 1})
    return rows


if __name__ == "__main__":
    raise SystemExit(common.cli(sys.modules[__name__], sys.argv[1:]))
