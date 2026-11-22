#!/usr/bin/env python3
"""Run the real case and end it when the run enters a chosen stage (round 15; round 9's method on any host).

Each sample is a whole delivery started with test/shiploop_e2e/run.py; all samples of one call start together.
The script watches each run's own trace and, at the first accepted `complete` that enters --until, creates
<output>/stop, which the harness reads as a request to end the run. A sample that does not get there within
--limit minutes is stopped the same way and marked `reached: false`.

Nothing is copied or judged here: the run folder keeps the plan and the step plan as the run accepted them.
Prints one JSON line a sample.

Usage: python3 stop_at_stage.py --plugin-dir DIR --root OUT_ROOT --until STAGE [--checkout DIR] [--limit MINUTES]
                                [--planning-review stage|none] NAME:CASE:HOST:MODEL:EFFORT [...]
"""
import argparse
import json
import pathlib
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[3]


def run_dirs(out):
    """Every ShipLoop run folder of the sample, oldest first: a session may halt its first run and start another."""
    return sorted(out.glob(".shiploop-runs/*/run"))


def run_dir(out):
    found = run_dirs(out)
    return found[-1] if found else None


def entered(out, stage):
    for run in run_dirs(out):
        try:
            rows = [json.loads(line) for line in (run / "trace.jsonl").read_text(errors="replace").splitlines()
                    if line.strip()]
        except (OSError, ValueError):
            continue
        if any(r.get("kind") == "command" and r.get("verb") == "complete" and r.get("exit") == 0
               and isinstance(r.get("stage"), list) and r["stage"][1] == stage for r in rows):
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plugin-dir", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--until", required=True, help="end the run when it enters this stage")
    parser.add_argument("--checkout", default=str(REPO))
    parser.add_argument("--limit", type=float, default=25.0)
    parser.add_argument("--planning-review", choices=("stage", "none"),
                        help="pass this run option to every sample (default: none passed, the run's own choice)")
    parser.add_argument("samples", nargs="+")
    args = parser.parse_args()
    root = pathlib.Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    live = []
    for sample in args.samples:
        name, case, host, model, effort = sample.split(":")
        out = root / name
        log = (root / f"{name}-log.txt").open("w")
        process = subprocess.Popen(
            [sys.executable, "test/shiploop_e2e/run.py", "--case", case, "--host", host, "--model", model,
             "--effort", effort, "--source", "checkout", "--plugin-dir", args.plugin_dir, "--output", str(out), "--quiet",
             *(["--planning-review", args.planning_review] if args.planning_review else [])],
            cwd=args.checkout, stdout=log, stderr=subprocess.STDOUT)
        live.append({"name": name, "case": case, "host": host, "model": model, "effort": effort, "out": out,
                     "process": process, "started": time.time(), "stopped": None, "reached": False})
    while any(s["stopped"] is None for s in live):
        for s in live:
            if s["stopped"] is not None:
                continue
            over = time.time() - s["started"] > args.limit * 60
            if entered(s["out"], args.until) or over or s["process"].poll() is not None:
                s["reached"] = entered(s["out"], args.until)
                s["out"].mkdir(parents=True, exist_ok=True)
                (s["out"] / "stop").write_text(f"round 15 sample: ended on entering {args.until}\n")
                s["stopped"] = time.time()
        time.sleep(2)
    for s in live:
        try:
            s["process"].wait(timeout=300)
        except subprocess.TimeoutExpired:
            s["process"].terminate()
            s["process"].wait(timeout=60)
        run = run_dir(s["out"])
        print(json.dumps({"name": s["name"], "case": s["case"], "host": s["host"], "model": s["model"],
                          "effort": s["effort"], "plugin": args.plugin_dir, "until": args.until, "reached": s["reached"],
                          "minutes": round((s["stopped"] - s["started"]) / 60, 1), "run": str(run) if run else None}),
              flush=True)


if __name__ == "__main__":
    main()
