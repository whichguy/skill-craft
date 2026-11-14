#!/usr/bin/env python3
"""Calibrate the `ticket-due-times` case's held-out probe before any run: every variant of the reference delivery
(test/fixtures/quality/reference_due_times.py) through every probe mode and the base's pristine tests.

    python3 -I docs/experiments/planning-points-probe-20261114/calibrate.py [SCRATCH]

Expected (registered in README.md beside this file): the base fails migrate, restart and switch and passes rollback,
off, cli and pristine; the reference passes everything; each defect fails at least the mode it targets and passes
every mode it does not touch (the table EXPECTED below). Writes evidence/calibration.json and exits 1 when any cell
differs from EXPECTED.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PROBE = REPO / "test" / "shiploop_e2e" / "checks" / "due_times_probe.py"
BASE_TESTS = REPO / "test" / "shiploop_e2e" / "checks" / "base_tests.py"
REFERENCE = REPO / "test" / "fixtures" / "quality" / "reference_due_times.py"
MODES = ("migrate", "restart", "switch", "rollback", "off", "cli", "pristine")

# What each variant must do in each mode: True pass, False fail.
EXPECTED = {
    "base": {"migrate": False, "restart": False, "switch": False, "rollback": True, "off": True, "cli": True,
             "pristine": True},
    "reference": dict.fromkeys(MODES, True),
    "version-two": {**dict.fromkeys(MODES, True), "rollback": False, "pristine": False},
    "priority-moves-due": {**dict.fromkeys(MODES, True), "restart": False},
    "due-not-persisted": {**dict.fromkeys(MODES, True), "restart": False},
    "no-backfill": {**dict.fromkeys(MODES, True), "migrate": False, "restart": False, "switch": False},
    "flag-ignored": {**dict.fromkeys(MODES, True), "off": False},
    "overdue-active": {**dict.fromkeys(MODES, True), "migrate": False},
}


def load_reference():
    spec = importlib.util.spec_from_file_location("reference_due_times", REFERENCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(argv, cwd) -> tuple[int, str]:
    done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=600, stdin=subprocess.DEVNULL)
    return done.returncode, (done.stdout + done.stderr).strip()


def main(argv) -> int:
    reference = load_reference()
    scratch = pathlib.Path(argv[0]) if argv else pathlib.Path(tempfile.mkdtemp(prefix="due-times-calibration-"))
    scratch.mkdir(parents=True, exist_ok=True)
    cells, wrong = {}, []
    for variant in reference.VARIANTS:
        dest = scratch / variant
        if dest.exists():
            raise SystemExit(f"{dest} exists; give an empty scratch folder")
        reference.build(dest, variant)
        # The pristine check reads the tree git tracks or would track; a bare copy is copied whole.
        own, own_out = run(["node", "--test"], dest)
        cells[variant] = {"own_suite_exit": own}
        for mode in MODES:
            argv_ = [sys.executable, str(BASE_TESTS), "pristine", "node-tickets"] if mode == "pristine" else \
                [sys.executable, str(PROBE), mode]
            began = time.monotonic()
            code, out = run(argv_, dest)
            passed = code == 0
            cells[variant][mode] = {"pass": passed, "exit": code, "seconds": round(time.monotonic() - began, 1),
                                    "fails": [line for line in out.splitlines() if line.startswith("FAIL:")][:8]}
            if passed != EXPECTED[variant][mode]:
                wrong.append(f"{variant} {mode}: {'passed' if passed else 'failed'}, expected "
                             f"{'pass' if EXPECTED[variant][mode] else 'fail'}")
        print(variant.ljust(20), " ".join(f"{mode}={'P' if cells[variant][mode]['pass'] else 'F'}" for mode in MODES),
              f"own-suite-exit={own}", flush=True)
    record = {"probe": str(PROBE.relative_to(REPO)), "reference": str(REFERENCE.relative_to(REPO)), "expected": EXPECTED,
              "cells": cells, "mismatches": wrong}
    (HERE / "evidence").mkdir(exist_ok=True)
    (HERE / "evidence" / "calibration.json").write_text(json.dumps(record, indent=1) + "\n")
    for line in wrong:
        print("MISMATCH: " + line)
    print(f"{len(wrong)} mismatches; evidence/calibration.json written")
    return 1 if wrong else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
