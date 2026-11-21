#!/usr/bin/env python3
"""Run the real case and end it at the stage that matters (round 9's small tests).

For each sample this starts a whole delivery with test/shiploop_e2e/run.py on Codex gpt-6.2-sol, all samples of one
call together, and watches the run's own files:

until the navigator has moved past the spec stage and, where the run has one, its review: the first accepted
`complete` that enters `test-strategy`. (A run ended at its first start needs no script: `run.py --stop-after-start`.)

Then it creates <output>/stop, which the harness reads as a request to end the run, and waits for run.py to exit. A
sample that does not get there within --limit minutes is stopped the same way and marked `not reached`.

It saves two copies of the specification into the sample's folder: `spec-as-written.md`, the file as the spec stage
left it (from the tree ShipLoop snapshotted when its review was bound; absent when the run had no spec review), and
`spec-as-accepted.md`, the file when the run was stopped. It prints one JSON line a sample: name, case, effort,
plugin, the option the run recorded, minutes to the stop and the two paths.

Usage: python3 stage_stop_samples.py --plugin-dir DIR --root OUT_ROOT [--checkout DIR] [--limit MINUTES]
                                     NAME:CASE:EFFORT [NAME:CASE:EFFORT ...]
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys
import time

OPTION = re.compile(r'"planning_review": "([a-z]+)"')
REPO = pathlib.Path(__file__).resolve().parents[3]


def run_dir(out):
    found = sorted(out.glob(".shiploop-runs/*/run"))
    return found[0] if found else None


def recorded_option(out):
    run = run_dir(out)
    try:
        match = OPTION.search((run / "state.md").read_text(errors="replace")) if run else None
    except OSError:
        match = None
    return match.group(1) if match else None


def past_spec(out):
    run = run_dir(out)
    if not run:
        return False
    try:
        rows = [json.loads(line) for line in (run / "trace.jsonl").read_text(errors="replace").splitlines() if line.strip()]
    except (OSError, ValueError):
        return False
    return any(r.get("kind") == "command" and r.get("verb") == "complete" and r.get("exit") == 0
               and isinstance(r.get("stage"), list) and r["stage"][1] == "test-strategy" for r in rows)


def save_specs(out):
    """The spec as the stage wrote it (the tree bound for its review) and as it stood at the stop."""
    run = run_dir(out)
    written = accepted = None
    worktree = run.parent / "worktree" if run else None
    if not worktree or not worktree.exists():
        return written, accepted
    current = worktree / "docs" / "shiploop" / "spec.md"
    if current.exists():
        accepted = out / "spec-as-accepted.md"
        accepted.write_text(current.read_text(errors="replace"))
    for bind in sorted((run / "improve").glob("*-bind.md"), key=lambda p: p.stat().st_mtime):
        tree = re.search(r'"tree": "([0-9a-f]{40})"', bind.read_text(errors="replace"))
        if not tree:
            continue
        shown = subprocess.run(["git", "-C", str(worktree), "show", f"{tree.group(1)}:docs/shiploop/spec.md"],
                               capture_output=True, text=True, check=False)
        if shown.returncode == 0 and shown.stdout.strip():
            written = out / "spec-as-written.md"
            written.write_text(shown.stdout)
        break  # the first review bound in a run is the spec's
    return written, accepted


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plugin-dir", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--checkout", default=str(REPO))
    parser.add_argument("--limit", type=float, default=15.0)
    parser.add_argument("samples", nargs="+")
    args = parser.parse_args()
    root = pathlib.Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    reached = past_spec
    live = []
    for sample in args.samples:
        name, case, effort = sample.split(":")
        out = root / name
        log = (root / f"{name}.log").open("w")
        process = subprocess.Popen(
            [sys.executable, "test/shiploop_e2e/run.py", "--case", case, "--host", "codex", "--model", "gpt-6.2-sol", "--effort", effort,
             "--source", "checkout", "--plugin-dir", args.plugin_dir, "--output", str(out), "--quiet"],
            cwd=args.checkout, stdout=log, stderr=subprocess.STDOUT)
        live.append({"name": name, "case": case, "effort": effort, "out": out, "process": process, "started": time.time(),
                     "stopped": None, "reached": False})
    while any(s["stopped"] is None for s in live):
        for s in live:
            if s["stopped"] is not None:
                continue
            over = time.time() - s["started"] > args.limit * 60
            if reached(s["out"]) or over or s["process"].poll() is not None:
                s["reached"] = bool(reached(s["out"]))
                s["out"].mkdir(parents=True, exist_ok=True)
                (s["out"] / "stop").write_text("round 9 small test: ended at the stage that matters\n")
                s["stopped"] = time.time()
        time.sleep(2)
    for s in live:
        try:
            s["process"].wait(timeout=300)
        except subprocess.TimeoutExpired:
            s["process"].terminate()
            s["process"].wait(timeout=60)
        run = run_dir(s["out"])
        written, accepted = save_specs(s["out"])
        print(json.dumps({"name": s["name"], "case": s["case"], "effort": s["effort"], "plugin": args.plugin_dir,
                          "reached": s["reached"], "option": recorded_option(s["out"]),
                          "minutes": round((s["stopped"] - s["started"]) / 60, 1), "run": str(run) if run else None,
                          "spec_as_written": str(written) if written else None,
                          "spec_as_accepted": str(accepted) if accepted else None}), flush=True)


if __name__ == "__main__":
    main()
