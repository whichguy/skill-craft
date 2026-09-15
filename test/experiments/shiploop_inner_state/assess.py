#!/usr/bin/env python3
"""Grade the trial's state boundary and fixed fixture, not review semantics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]


def record(path: Path) -> dict:
    return json.loads(path.read_text().split("```shiploop-state\n", 1)[1].split("```", 1)[0])


def assess(trial: Path) -> dict:
    before = record(trial / "initial-state.md")
    after = record(trial / "run/state.md")
    original = before["inner_loops"]["W2"]["action"]["id"]
    checks = {
        "protocol2": before["navigator_protocol_version"] == after["navigator_protocol_version"] == 2,
        "one_revision": after["revision"] == before["revision"] + 1,
        "one_history_entry": len(after["history"]) == len(before["history"]) + 1,
        "history_prefix_preserved": after["history"][:-1] == before["history"],
        "one_accepted_action": set(after["accepted"]) == set(before["accepted"]) | {original},
        "prior_results_preserved": all(after["accepted"].get(k) == v for k, v in before["accepted"].items()),
        "w1_unchanged": before["inner_loops"]["W1"] == after["inner_loops"]["W1"] == {"stage": "done", "action": None},
        "root_parked": after["stage"] == "inner-loop" and after["action"] is None,
        "same_selection": before["work_index"] == after["work_index"] == 1,
        "one_improve_return": after["history"][-1]["stage"] == "product-improve"
                              and after["history"][-1]["workitem"] == "W2"
                              and after["history"][-1]["action"] == original
                              and after["history"][-1]["outcome"] == "done",
        "w2_integrate_pending": after["inner_loops"]["W2"]["stage"] == "integrate"
                                and after["inner_loops"]["W2"]["action"]["stage"] == "integrate",
        "no_inner_subphases_or_counters": all(set(value) == {"stage", "action"}
                                              for value in after["inner_loops"].values()),
    }
    oracle = runpy.run_path(str(ROOT / "test/experiments/shiploop_entry_recovery/oracle.py"))["grade"]
    grade = oracle(trial / "fixture/lines.py")
    tests = subprocess.run([sys.executable, "-B", "-m", "unittest", "-v", "test_lines"],
                           cwd=trial / "fixture", capture_output=True, text=True, timeout=30)
    checks["fixture_oracle"] = grade["passed"] == grade["total"]
    checks["fixture_unit_tests"] = tests.returncode == 0
    return {"passed": all(checks.values()), "checks": checks, "oracle": grade,
            "unit_test_output": tests.stdout + tests.stderr,
            "limit": "Mechanical checks do not count or validate semantic review cycles; inspect campaign/reviewer notes separately."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trial", type=Path)
    args = parser.parse_args()
    result = assess(args.trial.resolve())
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
