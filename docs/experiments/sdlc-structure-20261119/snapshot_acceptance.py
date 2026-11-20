#!/usr/bin/env python3
"""How correct the product already was at each point of a recorded run, by the case's held-out acceptance checks.

ShipLoop snapshots the working copy as a Git tree at every lint gate, before every review and at every step commit
(iteration_census.py collects them). The E2E harness grades only the delivered product with held-out checks the
model never saw (test/shiploop_e2e/quality.py, `acceptance`). This script exports each snapshot of each graded run
into a throwaway folder and runs the same held-out checks on it, with the harness's own function:

  base              the tree the last step started from
  implement         when the last step's `implement` was accepted (the first complete implementation)
  test              when that step's `test` stage was accepted
  before_review     after `document`, before the step review
  commit            the step commit, after the step review
  before_end_review after `carry-forward`, before the end-of-work review
  delivered         the returned product (HEAD of the run's work folder)

A snapshot that a run does not have (no test stage, no review) takes the previous one's result. Results are cached by
case and tree, so an unchanged tree is graded once. No model is called.

Usage: python3.13 snapshot_acceptance.py ITERATION.json OUT.json [SHARD/OF]
"""
import collections
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "test" / "shiploop_e2e"))
import listeners
import quality

ORDER = ("base", "implement", "test", "before_review", "commit", "before_end_review", "delivered")


def git(top, *args, binary=False):
    done = subprocess.run(["git", "-C", str(top), *args], capture_output=True, text=not binary, check=False)
    return done.stdout if done.returncode == 0 else None


def grade(tops, tree, block, ports, scratch):
    """Export one tree from whichever repository holds it and run the held-out checks on the copy."""
    folder = pathlib.Path(tempfile.mkdtemp(prefix="snap-", dir=scratch))
    copy = folder / "copy"
    copy.mkdir()
    try:
        archive = next((data for data in (git(top, "archive", tree, binary=True) for top in tops) if data), None)
        if archive is None:
            return {"observed": False, "reason": "the tree is in neither repository"}
        subprocess.run(["tar", "-x", "-C", str(copy)], input=archive, check=True)
        groups = set()
        try:
            return quality.acceptance(copy, block, groups=groups, stop=lambda: None, logs=folder / "logs", ports=ports)
        finally:
            listeners.reap(folder)
    except (OSError, ValueError, subprocess.SubprocessError) as error:  # an ungradable snapshot is reported, never guessed
        return {"observed": False, "reason": f"{type(error).__name__}: {error}"[:300]}
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def main(iteration, out, shard="1/1"):
    part, parts = (int(n) for n in shard.split("/"))
    data = json.loads(pathlib.Path(iteration).read_text())
    cases = json.loads((REPO / "test" / "shiploop_e2e" / "cases.json").read_text())
    steps_of = collections.defaultdict(list)
    for step in data["steps"]:
        steps_of[step["run"]].append(step)
    out = pathlib.Path(out)
    done = json.loads(out.read_text()) if out.exists() else {"cache": {}, "runs": {}}
    scratch = out.parent / f"snap-work-{part}"
    scratch.mkdir(parents=True, exist_ok=True)
    for index, run in enumerate(sorted(data["runs"], key=lambda r: r["run"])):
        if index % parts != part - 1 or run["run"] in done["runs"]:
            continue
        spec = (cases.get(run.get("case")) or {}).get("quality") or {}
        block = spec.get("acceptance")
        folder = pathlib.Path(run["run"]).parents[3]
        try:
            recorded = (json.loads((folder / "result.json").read_text()).get("quality") or {}).get("acceptance") or {}
        except (OSError, ValueError):
            recorded = {}
        steps = [s for s in steps_of[run["run"]] if s.get("trees")]
        if not block or not recorded.get("observed") or not steps:
            continue
        work = folder / "work"
        tops = [pathlib.Path(run["worktree"]), work]
        last = steps[-1]["trees"]
        trees = {name: last.get(name) for name in ("base", "implement", "test", "before_review", "commit")}
        trees["before_end_review"] = run.get("end_review_tree")
        trees["delivered"] = (git(work, "rev-parse", "HEAD^{tree}") or "").strip() or None
        row = {"case": run["case"], "host": run["host"], "model": run["model"], "effort": run["effort"],
               "steps": len(steps), "ids": [c["id"] for c in block["checks"]], "recorded_passed": len(recorded.get("passed") or []),
               "recorded_ids": len(recorded.get("ids") or []), "snapshots": {}}
        previous = None
        for name in ORDER:
            tree = trees.get(name)
            if not tree:
                row["snapshots"][name] = {"tree": None, "same_as_previous": True, **(previous or {"observed": False})}
                continue
            key = f"{run['case']}:{tree}"
            if key not in done["cache"]:
                result = grade(tops, tree, block, list(spec.get("refuse_ports") or []), scratch)
                done["cache"][key] = {"observed": bool(result.get("observed")), "passed": result.get("passed"),
                                      "reason": result.get("reason"),
                                      "failed": {c["id"]: c.get("note") for c in result.get("checks") or [] if not c.get("pass")}}
            previous = done["cache"][key]
            row["snapshots"][name] = {"tree": tree, **previous}
        done["runs"][run["run"]] = row
        out.write_text(json.dumps(done, indent=1))
        marks = " ".join(f"{name}={len(s.get('passed') or [])}" if s.get("observed") else f"{name}=?"
                         for name, s in row["snapshots"].items())
        print(f"{run['case']:<24}{run['model']:<16}{len(row['ids']):>3} checks  {marks}", flush=True)
    shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
