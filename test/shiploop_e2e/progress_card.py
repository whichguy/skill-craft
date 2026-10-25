#!/usr/bin/env python3
"""Render a progress card for template-field experiments (experiment.py) as an HTML fragment for an inline widget.

    python3 test/shiploop_e2e/progress_card.py --out DIR E6-K1 E6-K3 E6-K5 [--arms T,B,C] [--plan PLAN.json] [--parallel 3]

One row per experiment (its case and the case's `shape` band, or its metric), one column per arm (default: the first
experiment's arms; the first arm is the control), one slot per sample: filled when the sample scored 1, a ring when it
scored below 1 (labelled with its steps, or its value), a dashed spinning ring with its minutes while it runs, a dotted
ring while it waits. Each cell shows the arm's mean and, for a non-control arm, the verdict of the latest
`experiment.py decide <control> <arm>`. A progress bar counts finished samples and estimates the end from their mean
minutes at `--parallel` samples at a time (default: the number running, else 1).

`--plan` adds the plan strip that leads every status update (memory status-narrative-format): a JSON list of
`{"step": "...", "state": "done" | "running" | "waiting" | "pending", "note": "..."}` in order, drawn as chips joined by
arrows, each state carrying its own icon so state is never colour alone.

It reads only run folders and decision files and writes nothing. A sample whose evaluator fails shows as an error
slot, never as a pass. It builds a status_card.py model and lets that module draw it (the same card any long job uses).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import experiment  # noqa: E402
import status_card  # noqa: E402


def band(exp: dict) -> str:
    """The case's band as a short label, else the experiment's metric."""
    shape = (json.loads((HERE / "step_cases.json").read_text()).get(exp["case"]) or {}).get("shape")
    if not shape:
        return exp.get("metric", "")[:48]
    low, high = shape["steps"]
    text = (f"exactly {low} step" + ("s" if low != 1 else "") if low == high else
            f"band {low}+ steps" if high is None else f"band {low}-{high} steps")
    return text + (", layers apart" if shape.get("separate") else "")


def sample_state(sample: Path, module, now: float, scorer=None) -> dict:
    folder = sample / "slice"
    if not folder.exists():
        return {"state": "pending"}
    if not (folder / "slice-result.json").exists():
        return {"state": "running", "minutes": (now - folder.stat().st_birthtime) / 60}
    try:
        found = (scorer or module.score)(folder)
    except Exception as exc:  # shown as an error slot, never as a pass
        return {"state": "error", "why": str(exc)[:80]}
    minutes = None
    metrics_file = folder / "metrics.json"
    if metrics_file.exists():
        span = json.loads(metrics_file.read_text()).get("span") or {}
        if span.get("ended") and span.get("started"):
            minutes = (span["ended"] - span["started"]) / 60
    return {"state": "done", "value": found.get("value"), "label": found.get("steps"), "minutes": minutes}


def _slot(s: dict) -> dict:
    """A sample's state as a status_card slot."""
    if s["state"] == "done":
        value = s.get("value")
        label = s.get("label") if s.get("label") is not None else ("–" if value is None else f"{value:.2f}".rstrip("0").rstrip("."))
        tip = f"value {value}" + (f", {s['label']} steps" if s.get("label") is not None else "")
        return {"state": "pass" if value is not None and value >= 0.999 else "below", "label": label, "tip": tip}
    if s["state"] == "running":
        return {"state": "running", "label": f"{round(s['minutes'])}m", "tip": f"running {round(s['minutes'])} min"}
    if s["state"] == "error":
        return {"state": "error", "label": "err", "tip": s.get("why", "")}
    return {"state": "pending"}


def card(out: Path, exp_ids: list[str], arms: list[str] | None = None, plan: list[dict] | None = None,
         parallel: int | None = None, now: float | None = None, scorer=None) -> str:
    now = now or time.time()
    exps = {exp_id: experiment.load(exp_id) for exp_id in exp_ids}
    arms = arms or list(exps[exp_ids[0]]["arms"])
    control = arms[0]
    grid, slots = {}, []
    for exp_id, exp in exps.items():
        module = experiment.evaluator(exp) if scorer is None else None
        for arm in arms:
            states = [sample_state(out / exp_id / arm / str(n), module, now, scorer)
                      for n in range(1, exp.get("samples", 4) + 1)]
            grid[(exp_id, arm)] = states
            slots.extend(states)
    done = [s for s in slots if s["state"] == "done"]
    running = [s for s in slots if s["state"] == "running"]
    minutes = [s["minutes"] for s in done if s.get("minutes")]
    lanes = parallel or max(len(running), 1)
    left = len(slots) - len(done)
    eta = now + (left / lanes) * (statistics.mean(minutes) if minutes else 20) * 60
    rows = []
    for exp_id, exp in exps.items():
        cells = []
        for arm in arms:
            states = grid[(exp_id, arm)]
            values = [s["value"] for s in states if s["state"] == "done" and s.get("value") is not None]
            record = out / exp_id / f"decision-{control}-{arm}.json"
            verdict = json.loads(record.read_text()).get("verdict") if arm != control and record.exists() else None
            cells.append({"slots": [_slot(s) for s in states], "verdict": verdict,
                          "summary": f"mean {statistics.mean(values):.2f}" if values else "mean –"})
        rows.append({"name": f"{exp_id} · {exp['case']}", "sub": band(exp), "cells": cells})
    model = {"plan": plan or [], "columns": arms, "rows": rows,
             "progress": {"done": len(done), "total": len(slots), "unit": "samples", "running": len(running),
                          "stamp": time.strftime("%H:%M", time.localtime(now)),
                          "eta": time.strftime("%H:%M", time.localtime(eta)) if left else None},
             "legend": {"pass": "scored 1", "below": "scored below 1", "note": "number = steps planned, or the value"}}
    return status_card.render(model)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("experiments", nargs="+")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--arms", help="comma-separated, control first (default: the first experiment's arms)")
    p.add_argument("--plan", type=Path, help="JSON list of {step, state, note}")
    p.add_argument("--parallel", type=int)
    args = p.parse_args(argv)
    plan = json.loads(args.plan.read_text()) if args.plan else None
    print(card(args.out, args.experiments, args.arms.split(",") if args.arms else None, plan, args.parallel))
    return 0


if __name__ == "__main__":
    sys.exit(main())
