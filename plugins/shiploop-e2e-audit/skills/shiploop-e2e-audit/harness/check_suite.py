#!/usr/bin/env python3
"""Run named no-model apparatus suites. Live Grok runs use run.py explicitly."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import unittest

import layout

HERE = layout.HARNESS_ROOT
GROUPS = {
    "mock": ("test_behavior_capture", "test_dag_replay", "test_protocol_compat", "test_trace_corpus", "test_recovery_isolation"),
    "harness": ("test_capture", "test_timeout_cleanup", "test_evidence", "test_grok_adapter", "test_grading", "test_run", "test_suites", "test_audit", "test_check_suite", "test_checkout_binding"),
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
    parser.add_argument("--skill-root", type=Path,
                        help="separate ShipLoop package to fingerprint and exercise")
    args = parser.parse_args(argv)
    names = selected(args.suite)
    import dag_replay

    try:
        subject_root, subject_selection = layout.resolve_skill_binding(args.skill_root)
        subject = dag_replay._source_fingerprint(subject_root)
        if not (subject_root / "scripts" / "shiploop_navigator.py").is_file():
            raise dag_replay.DagReplayError("selected ShipLoop skill root has no shiploop_navigator.py")
    except (OSError, ValueError, dag_replay.DagReplayError) as exc:
        parser.error(str(exc))
    checkout = layout.canonical_source_checkout()
    harness = {
        "root": str(HERE),
        "package_root": str(layout.PACKAGE_ROOT),
        "source_checkout": str(checkout) if checkout else None,
    }
    selected_subject = {
        "root": subject["root"],
        "package_sha256": subject["package_sha256"],
        "file_count": subject["file_count"],
        "selection": subject_selection,
        "default_selection": layout.default_skill_binding()[1],
        "dag_replay_selected": "test_dag_replay" in names,
    }
    if args.list:
        print(json.dumps({"suite": args.suite, "modules": names, "model_calls": 0,
                          "harness": harness, "selected_subject": selected_subject}, indent=2))
        return 0
    if args.output:
        try:
            output = layout.validate_new_external_output(args.output, subject_root=subject_root)
        except ValueError as exc:
            parser.error(str(exc))
        output.mkdir(parents=True)
    else:
        output = None
    previous_root = layout._selected_skill_root
    previous_default = dag_replay.DEFAULT_SKILL_ROOT
    layout.set_selected_skill_root(subject_root)
    dag_replay.DEFAULT_SKILL_ROOT = subject_root
    try:
        sys.path.insert(0, str(HERE))
        tests = unittest.defaultTestLoader.loadTestsFromNames(names)
        started = time.monotonic()
        result = unittest.TextTestRunner(verbosity=1).run(tests)
    finally:
        dag_replay.DEFAULT_SKILL_ROOT = previous_default
        layout.set_selected_skill_root(previous_root)
    complete = result.wasSuccessful() and not result.skipped and not result.expectedFailures
    receipt = {"schema": "shiploop-e2e-apparatus-check/1", "suite": args.suite, "modules": names,
               "model_calls": 0, "tests": result.testsRun, "failures": len(result.failures),
               "errors": len(result.errors), "skipped": len(result.skipped), "expected_failures": len(result.expectedFailures),
               "duration_seconds": time.monotonic() - started, "status": "passed" if complete else "incomplete-or-failed",
               "harness": harness, "selected_subject": selected_subject,
               "limitations": "Fixture apparatus evidence only; does not establish generated application or hosted behavior."}
    if output:
        (output / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
