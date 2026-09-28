#!/usr/bin/env python3
"""Live fan-out/fan-in check: a real host runs Plan Dispatcher on dummy steps.

No ShipLoop and no product. The graph is A and B (independent) and J (after
both). Each step's only work is a stamp script that records its start time,
sleeps, and records its end time. The host model drives the published
plan-dispatcher skill, following its exact calls and launching A and B as
native subagents where it can.

Graded by script, never by the model:
- complete:  the dispatcher reports every step accepted;
- fan-in:    J started at or after both A and B ended;
- fan-out:   whether A and B actually overlapped (reported; the order is the gate);
- native:    whether A and B ran as native workers (a launch handle) or in the
             parent conversation (a main-context executor).

  python3 test/shiploop_e2e/fanout.py --host codex    # GPT-6 Luna at max, the Codex default
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hosts  # noqa: E402
import run  # noqa: E402

SLEEP_SECONDS = 30
STAMP = '''import json, os, sys, time
step, directory, seconds = sys.argv[1], sys.argv[2], float(sys.argv[3])
os.makedirs(directory, exist_ok=True)
start = time.time()
time.sleep(seconds)
path = os.path.join(directory, step + ".json")
with open(path, "w") as handle:
    json.dump({"step": step, "start": start, "end": time.time(), "pid": os.getpid()}, handle)
print(path)
'''


def graph(stamp: Path, stamps: Path) -> dict:
    def step(step_id: str, deps: list[str]) -> dict:
        command = f"python3 {stamp} {step_id} {stamps} {SLEEP_SECONDS}"
        return {"id": step_id, "deps": deps, "contract": {
            "task": f"Dummy step {step_id}: run exactly `{command}` once and do nothing else.",
            "ready": [f"{stamp} exists"],
            "done": [f"{stamps / (step_id + '.json')} records the start and end of step {step_id}. "
                     f"Confirm by: cat {stamps / (step_id + '.json')}; pass when it holds start and end times"],
        }}
    return {"version": 1, "steps": [step("A", []), step("B", []), step("J", ["A", "B"])]}


def prompt(dispatch: Path, graph_file: Path, run_dir: Path) -> str:
    return (
        f"Run this dependency graph with Plan Dispatcher and nothing else. The helper is {dispatch}; the graph "
        f"file is {graph_file} (write {{\"owner\": \"fanout-parent\", \"graph\": <its contents>}} to an init "
        f"input file); the run directory is {run_dir}. Start with `node {dispatch} init {run_dir} <init file>`, "
        "then follow every returned action's exact call. Launch every claimable step at once, each as its own "
        "native subagent with a fresh context that executes only its packet and reports with the packet's "
        "report_argv; if this host cannot launch native subagents, run each step in this conversation with the "
        "main-context executor. Verify each report by reading the step's stamp file before settling, and "
        "settle with the returned call. Stop when the dispatcher reports the run complete. Steps are dummy "
        "work: do not write any other files or code."
    )


def overlap(a: dict, b: dict) -> float:
    return max(0.0, min(a["end"], b["end"]) - max(a["start"], b["start"]))


def grade(dispatch: Path, run_dir: Path, stamps: Path) -> dict:
    """Script-only verdicts from the dispatcher's state and the stamps the steps wrote."""
    view = {}
    done = subprocess.run(["node", str(dispatch), "next", str(run_dir)], capture_output=True, text=True)
    if done.returncode == 0:
        view = json.loads(done.stdout)
    state_file = run_dir / "plan-dispatcher-state.json"
    state = json.loads(state_file.read_text()) if state_file.is_file() else {"steps": {}, "attempts": {}}
    marks = {}
    for step in ("A", "B", "J"):
        path = stamps / (step + ".json")
        if path.is_file():
            marks[step] = json.loads(path.read_text())
    runner = {}
    for step in ("A", "B", "J"):
        current = (state["steps"].get(step) or {}).get("current_attempt")
        record = state["attempts"].get(current) or {}
        runner[step] = "native" if record.get("handle") else "main-context" if record.get("executor") else None
    complete = view.get("complete") is True
    fan_in = all(k in marks for k in "ABJ") and marks["J"]["start"] >= max(marks["A"]["end"], marks["B"]["end"])
    both = "A" in marks and "B" in marks
    return {
        "pass": complete and fan_in,
        "complete": complete,
        "fan_in_order": fan_in,
        "fan_out_overlap_seconds": round(overlap(marks["A"], marks["B"]), 1) if both else None,
        "fan_out_parallel": both and overlap(marks["A"], marks["B"]) > 0,
        "runner": runner,
        "stamps": marks,
        "attempts": {step: sum(1 for a in state["attempts"].values() if a.get("step") == step) for step in "ABJ"},
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--host", choices=sorted(hosts.HOSTS), default="codex")
    p.add_argument("--model")
    p.add_argument("--effort")
    p.add_argument("--output", type=Path)
    p.add_argument("--timeout", type=int, default=1800)
    for name in hosts.HOSTS:
        p.add_argument(f"--{name}-bin", default=name)
    p.add_argument("--source", default="marketplace", help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    host = hosts.host(args.host, getattr(args, args.host + "_bin"))
    out = run.new_output_dir(args.output, "fanout-" + args.host)
    work = out / "work"
    work.mkdir()
    env = host.env(out / "home")
    plugin_dir, _plugin, versions = run.marketplace_preflight(args, out, env)
    if versions["gate"]:
        raise SystemExit("version gate: " + "; ".join(versions["gate"]))
    dispatch = plugin_dir / "skills" / "plan-dispatcher" / "scripts" / "dispatch.js"
    stamp, stamps, run_dir = work / "stamp.py", work / "stamps", work / "dispatcher-run"
    stamp.write_text(STAMP)
    graph_file = work / "graph.json"
    graph_file.write_text(json.dumps(graph(stamp, stamps), indent=2) + "\n")
    model, effort = args.model or host.model, args.effort or host.effort
    argv_ = host.argv(prompt=host.invoke("skill-craft:plan-dispatcher", prompt(dispatch, graph_file, run_dir)),
                      prompt_file=out / "prompt.txt", cwd=work, model=model, effort=effort,
                      permission_mode="auto", max_turns=200, max_budget_usd=5.0,
                      plugin_dir=None if host.marketplace else plugin_dir)
    started = time.time()
    process = hosts.run_agent(argv_, work, env, out / "events.jsonl", out / "stderr.txt", args.timeout,
                              translate=host.translator())
    result = {"host": args.host, "model": model, "effort": effort, "versions": versions, "process": process,
              **grade(dispatch, run_dir, stamps), "output": str(out),
              "elapsed_seconds": round(time.time() - started, 1)}
    run.write_transcript(out / "events.jsonl", out / "transcript.md")
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(("PASS" if result["pass"] else "FAIL") + f"  fan-out/fan-in host={args.host} model={model} effort={effort}")
    print(f"  complete {result['complete']}  fan-in order {result['fan_in_order']}  "
          f"A/B overlap {result['fan_out_overlap_seconds']}s  runner {result['runner']}  output={out}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
