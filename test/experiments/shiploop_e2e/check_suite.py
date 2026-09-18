#!/usr/bin/env python3
"""Run named no-model apparatus suites. Live Grok runs use run.py explicitly."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import unittest


HERE = Path(__file__).resolve().parent
GROUPS = {
    "mock": ("test_behavior_capture", "test_dag_replay", "test_protocol_compat", "test_trace_corpus", "test_recovery_isolation"),
    "harness": ("test_capture", "test_evidence", "test_grok_adapter", "test_grading", "test_run", "test_suites", "test_audit", "test_check_suite"),
    "games": ("test_tictactoe", "test_oracle_games", "test_gas_artifact", "test_verify_suite", "test_driver_transport"),
    "workflow": ("test_workflow_review", "test_campaign", "test_recovery_isolation"),
    "regressions": ("test_trace_corpus", "test_gas_artifact", "test_verify_suite", "test_workflow_review", "test_recovery_isolation"),
}


def selected(group: str) -> list[str]:
    available = {p.stem for p in HERE.glob("test_*.py")}
    if group == "all":
        return sorted(available)
    if group not in GROUPS:
        raise ValueError("unknown apparatus suite")
    # Some transports are covered by test_verify_suite; do not require a second
    # test file solely because a bounded implementation uses a separate module.
    required = set(GROUPS[group]) - {"test_driver_transport"}
    missing = required - available
    if missing:
        raise ValueError("incomplete apparatus suite: " + ", ".join(sorted(missing)))
    return sorted(set(GROUPS[group]) & available)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=["all", *GROUPS], default="all")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    names = selected(args.suite)
    if args.list:
        print(json.dumps({"suite": args.suite, "modules": names, "model_calls": 0}, indent=2))
        return 0
    if args.output:
        output = args.output.expanduser().resolve()
        if output.exists() or output.is_relative_to(HERE.parents[2]):
            parser.error("output must be a new directory outside the source checkout")
        output.mkdir(parents=True)
    else:
        output = None
    sys.path.insert(0, str(HERE))
    tests = unittest.defaultTestLoader.loadTestsFromNames(names)
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=1).run(tests)
    complete = result.wasSuccessful() and not result.skipped and not result.expectedFailures
    receipt = {"schema": "shiploop-e2e-apparatus-check/1", "suite": args.suite, "modules": names,
               "model_calls": 0, "tests": result.testsRun, "failures": len(result.failures),
               "errors": len(result.errors), "skipped": len(result.skipped), "expected_failures": len(result.expectedFailures),
               "duration_seconds": time.monotonic() - started, "status": "passed" if complete else "incomplete-or-failed",
               "limitations": "Fixture apparatus evidence only; does not establish generated application or hosted behavior."}
    if output:
        (output / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
