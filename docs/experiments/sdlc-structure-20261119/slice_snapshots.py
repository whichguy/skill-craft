#!/usr/bin/env python3
"""Grade every snapshot of an inner-loop slice with checks the model never saw (round 4's registered yardstick).

For each slice in ITERATION.json (iteration_census.py --all over the slices' folder) this exports the Git tree
ShipLoop snapshotted when each step's `implement` was accepted, when its `test` was accepted, before its step
review and at its step commit, plus the slice's final working copy, and runs the hidden checks on each:

  tickets-assign      the held-out module of the full ticket-assignment case (quality.acceptance); 14 of its 18
                      checks are scored, the four on the listing filter and the command line are reported apart
  shared-expenses-w1  the six checks of the full shared-expenses case (checks/expense_service.py)
  node-chess-engine   ten checks through the engine's public interface (chess_hidden.js): six published move-sequence
                      counts two to four moves deep, two replayed games, four statuses, four illegal moves, sorting
  tickets-due-times   the eight checks of the full ticket-due-times case (cases.json): the base's own tests still
                      passing with new ones beside them (suite) and unchanged (pristine), and the six modes of
                      checks/due_times_probe.py (migrate, restart, switch, rollback, off, cli)

A slice already in OUT.json is not graded again, and a slice with no slice-result.json yet (still running) is skipped.

Usage: python3.13 slice_snapshots.py ITERATION.json OUT.json
"""
import collections
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import snapshot_acceptance as snap

REPO = snap.REPO
CHECKS = REPO / "test" / "shiploop_e2e" / "checks"
OUTSIDE = ("assignee-filter", "filters-combine", "assignee-filter-pages", "cli-shows-assignee")
EXPENSE = ("unit", "contract", "split", "settle", "restart", "concurrency")
CHESS = ("count-start-3", "count-kiwipete-3", "count-position3-4", "count-position4-3", "count-position5-3",
         "count-position6-3", "game-fens", "status-positions", "illegal-moves-throw", "moves-sorted")
DUE = ("suite", "pristine", "migrate", "restart", "switch", "rollback", "off", "cli")
TOTALS = {"shared-expenses-w1": len(EXPENSE), "node-chess-engine": len(CHESS), "tickets-assign": 14,
          "tickets-due-times": len(DUE)}
POINTS = ("implement", "test", "before_review", "commit")


def expense(copy):
    """The six shared-expenses checks, each in its own process, as {passed: [...], failed: {id: last line}}."""
    passed, failed = [], {}
    env = dict(os.environ, E2E_CHECKS=str(CHECKS))
    for name in EXPENSE:
        try:
            done = subprocess.run([sys.executable, str(CHECKS / "expense_service.py"), name], cwd=copy, env=env,
                                  capture_output=True, text=True, timeout=180, check=False)
            ok, note = done.returncode == 0, (done.stdout.strip().splitlines() or done.stderr.strip().splitlines() or [""])[-1]
        except subprocess.TimeoutExpired:
            ok, note = False, "timed out after 180 s"
        if ok:
            passed.append(name)
        else:
            failed[name] = note[:240]
    return {"observed": True, "passed": passed, "failed": failed}


def chess(copy):
    """The ten chess checks, each in its own process, as {passed: [...], failed: {id: what it saw}}."""
    passed, failed = [], {}
    for name in CHESS:
        try:
            done = subprocess.run(["node", str(pathlib.Path(__file__).resolve().parent / "chess_hidden.js"), str(copy), name],
                                  capture_output=True, text=True, timeout=240, check=False)
            ok, note = done.returncode == 0, (done.stdout.strip().splitlines() or done.stderr.strip().splitlines() or [""])[-1]
        except subprocess.TimeoutExpired:
            ok, note = False, "timed out after 240 s"
        if ok:
            passed.append(name)
        else:
            failed[name] = note[:240]
    return {"observed": True, "passed": passed, "failed": failed}


def due_times(copy):
    """The eight ticket-due-times checks, each in its own process, as {passed: [...], failed: {id: last line}}."""
    passed, failed = [], {}
    env = dict(os.environ, E2E_CHECKS=str(CHECKS))
    for name in DUE:
        command = ([sys.executable, str(CHECKS / "base_tests.py"), name, "node-tickets"] if name in ("suite", "pristine")
                   else [sys.executable, str(CHECKS / "due_times_probe.py"), name])
        try:
            done = subprocess.run(command, cwd=copy, env=env, capture_output=True, text=True, timeout=600, check=False)
            lines = [line for line in (done.stdout + done.stderr).strip().splitlines() if line.strip()]
            ok, note = done.returncode == 0, next((line for line in lines if line.startswith("FAIL")), (lines or [""])[-1])
        except subprocess.TimeoutExpired:
            ok, note = False, "timed out after 600 s"
        if ok:
            passed.append(name)
        else:
            failed[name] = note[:240]
    return {"observed": True, "passed": passed, "failed": failed}


def grade(case, copy, folder, cases):
    if case == "shared-expenses-w1":
        return expense(copy)
    if case == "tickets-due-times":
        return due_times(copy)
    if case == "node-chess-engine":
        return chess(copy)
    spec = cases["ticket-assignment"]["quality"]
    result = snap.quality.acceptance(copy, spec["acceptance"], groups=set(), stop=lambda: None, logs=folder / "logs",
                                     ports=list(spec.get("refuse_ports") or []))
    rows = result.get("checks") or []
    return {"observed": bool(result.get("observed")), "reason": result.get("reason"),
            "passed": [c["id"] for c in rows if c.get("pass") and c["id"] not in OUTSIDE],
            "failed": {c["id"]: c.get("note") for c in rows if not c.get("pass") and c["id"] not in OUTSIDE},
            "outside_passed": [c["id"] for c in rows if c.get("pass") and c["id"] in OUTSIDE]}


def at(case, export, cases, scratch):
    folder = pathlib.Path(tempfile.mkdtemp(prefix="slice-", dir=scratch))
    copy = folder / "copy"
    copy.mkdir()
    try:
        export(copy)
        return grade(case, copy, folder, cases)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return {"observed": False, "reason": f"{type(error).__name__}: {error}"[:300]}
    finally:
        snap.listeners.reap(folder)
        shutil.rmtree(folder, ignore_errors=True)


def main(iteration, out):
    data = json.loads(pathlib.Path(iteration).read_text())
    cases = json.loads((REPO / "test" / "shiploop_e2e" / "cases.json").read_text())
    out = pathlib.Path(out)
    scratch = out.parent / "slice-snap-work"
    scratch.mkdir(parents=True, exist_ok=True)
    steps_of = collections.defaultdict(list)
    for step in data["steps"]:
        steps_of[step["run"]].append(step)
    report = json.loads(out.read_text()) if out.exists() else {}
    for run in sorted(data["runs"], key=lambda r: r["run"]):
        if run.get("case") not in TOTALS:
            continue
        worktree = pathlib.Path(run["worktree"])
        folder = pathlib.Path(run["run"]).parents[3]
        name = folder.name
        if name in report or not (folder / "slice-result.json").exists():
            continue  # graded already, or the slice is still running
        row = {"case": run["case"], "host": run["host"], "model": run["model"], "effort": run["effort"], "steps": []}
        cache = {}
        for number, step in enumerate(steps_of[run["run"]], 1):
            marks = {}
            for point in POINTS:
                tree = (step.get("trees") or {}).get(point)
                if not tree:
                    marks[point] = None
                    continue
                if tree not in cache:
                    def export(copy, tree=tree, worktree=worktree):
                        archive = snap.git(worktree, "archive", tree, binary=True)
                        if archive is None:
                            raise ValueError("the tree is not in the slice's repository")
                        subprocess.run(["tar", "-x", "-C", str(copy)], input=archive, check=True)
                    cache[tree] = at(run["case"], export, cases, scratch)
                marks[point] = cache[tree]
            row["steps"].append(marks)
        row["end"] = at(run["case"], lambda copy, worktree=worktree: snap.quality.export_delivery(worktree, copy), cases, scratch)
        report[name] = row
        total = TOTALS[run["case"]]
        line = []
        for number, marks in enumerate(row["steps"], 1):
            line.append(f"S{number} " + " ".join(
                f"{point}={len(m['passed']) if m and m.get('observed') else '?' if m else '-'}" for point, m in marks.items()))
        end = row["end"]
        out.write_text(json.dumps(report, indent=1))
        print(f"{name:<28}{run['model']:<18}{run['effort'] or '-':<7}of {total}: {'; '.join(line)}; end="
              f"{len(end['passed']) if end.get('observed') else '?'}", flush=True)
        for point, m in [("end", end)] + [(f"S{n} {p}", mm) for n, marks in enumerate(row["steps"], 1) for p, mm in marks.items()]:
            if m and m.get("failed"):
                print(f"    {point}: failed " + "; ".join(f"{k} ({(v or '')[:110]})" for k, v in m["failed"].items()))
    out.write_text(json.dumps(report, indent=1))
    shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
