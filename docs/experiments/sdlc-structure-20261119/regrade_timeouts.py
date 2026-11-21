#!/usr/bin/env python3
"""Run again the hidden checks that ended in a harness timeout, and record both results (round 6, guard round).

The node-tickets base's own `node --test` run occasionally does not end (checks/base_tests.py gives it 120 seconds and
then reports "rc None"): measured on this machine at 2 of 80 repeats of the `suite` check on one finished delivery, one
of the two in the untouched base's own tests. A snapshot graded during such a hang shows a failed `suite` or `pristine`
that says nothing about the tree graded.

For every mark in SNAPSHOTS.json whose failed check carries a timeout note, this exports the same tree again (or, for
the end of a slice, its final working copy), runs that one check up to RUNS more times and stops at the first pass. A
check that passes is moved to the mark's `passed`; either way the mark gains `reran: {check: {first, runs, passed}}`
with the first note kept. Nothing else in the file changes.

Usage: python3.13 regrade_timeouts.py ITERATION.json SNAPSHOTS.json
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import slice_snapshots as ss

snap = ss.snap
RUNS = 3
TIMEOUT_NOTES = ("rc None", "did not end within", "timed out after")


def run_check(case, name, copy):
    """One hidden check of a case, as slice_snapshots runs it: (passed, the line that says what was seen)."""
    if case != "tickets-due-times":
        raise SystemExit(f"regrade_timeouts.py knows the tickets-due-times checks only, not {case}")
    env = dict(os.environ, E2E_CHECKS=str(ss.CHECKS))
    command = ([sys.executable, str(ss.CHECKS / "base_tests.py"), name, "node-tickets"] if name in ("suite", "pristine")
               else [sys.executable, str(ss.CHECKS / "due_times_probe.py"), name])
    try:
        done = subprocess.run(command, cwd=copy, env=env, capture_output=True, text=True, timeout=600, check=False)
    except subprocess.TimeoutExpired:
        return False, "timed out after 600 s"
    lines = [line for line in (done.stdout + done.stderr).strip().splitlines() if line.strip()]
    return done.returncode == 0, next((line for line in lines if line.startswith("FAIL")), (lines or [""])[-1])[:240]


def main(iteration, snapshots):
    data = json.loads(pathlib.Path(iteration).read_text())
    path = pathlib.Path(snapshots)
    report = json.loads(path.read_text())
    runs = {pathlib.Path(run["run"]).parents[3].name: run for run in data["runs"]}
    steps = {}
    for step in data["steps"]:
        steps.setdefault(pathlib.Path(step["run"]).parents[3].name, []).append(step)
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="regrade-"))
    changed = 0
    for name, row in sorted(report.items()):
        marks = [("end", None, row.get("end"))]
        for number, points in enumerate(row.get("steps") or (), 1):
            marks += [(f"S{number} {point}", (number, point), mark) for point, mark in points.items()]
        for label, where, mark in marks:
            hung = [check for check, note in ((mark or {}).get("failed") or {}).items()
                    if any(text in (note or "") for text in TIMEOUT_NOTES) and check not in (mark.get("reran") or {})]
            if not hung:
                continue
            worktree = pathlib.Path(runs[name]["worktree"])
            copy = scratch / f"{name}-{label.replace(' ', '-')}"
            copy.mkdir()
            if where is None:
                snap.quality.export_delivery(worktree, copy)
            else:
                tree = steps[name][where[0] - 1]["trees"][where[1]]
                subprocess.run(["tar", "-x", "-C", str(copy)], input=snap.git(worktree, "archive", tree, binary=True), check=True)
            for check in hung:
                first = mark["failed"][check]
                passed, note, used = False, first, 0
                while used < RUNS and not passed:
                    used += 1
                    passed, note = run_check(row["case"], check, copy)
                mark.setdefault("reran", {})[check] = {"first": first, "runs": used, "passed": passed}
                if passed:
                    del mark["failed"][check]
                    mark["passed"].append(check)
                else:
                    mark["failed"][check] = note
                changed += 1
                print(f"{name} {label}: {check} first ended in a timeout; run again {used} time{'s' if used != 1 else ''}: "
                      f"{'passes' if passed else 'still fails (' + note[:120] + ')'}", flush=True)
            snap.listeners.reap(copy)
            shutil.rmtree(copy, ignore_errors=True)
    path.write_text(json.dumps(report, indent=1))
    shutil.rmtree(scratch, ignore_errors=True)
    print(f"checks run again: {changed}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
