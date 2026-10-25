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
slot, never as a pass.
"""
from __future__ import annotations

import argparse
import html
import json
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import experiment  # noqa: E402

BLUE = "#2a78d6"
STYLE = (
    "<style>.s{display:flex;flex-direction:column;align-items:center;gap:3px;width:28px}"
    ".s i{display:block;width:14px;height:14px;border-radius:50%;box-sizing:border-box;margin:2px 0}"
    f".f{{background:{BLUE};width:18px!important;height:18px!important;margin:0!important}}.o{{border:2px solid {BLUE}}}"
    ".r{border:2px dashed #BA7517}.p{border:1.5px dotted var(--border-stronger)}.e{border:2px solid #A32D2D;border-radius:3px!important}"
    ".s em{font-style:normal;font-size:11px;color:var(--text-muted);height:14px}"
    ".c{background:var(--surface-1);border-radius:var(--radius);padding:10px 12px}.row{display:flex;gap:4px;justify-content:center;flex-wrap:wrap}"
    ".ft{display:flex;justify-content:space-between;align-items:center;gap:6px;margin-top:6px;font-size:12px;color:var(--text-secondary)}"
    ".ft span{font-size:11px;color:var(--text-muted)}.ok{font-weight:400;font-size:11px;padding:1px 6px;border-radius:var(--radius);"
    "background:var(--bg-success);color:var(--text-success)}.no{font-weight:400;font-size:11px;padding:1px 6px;"
    "border-radius:var(--radius);background:var(--bg-danger);color:var(--text-danger)}"
    ".h{font-size:13px;font-weight:500}.m{font-size:12px;color:var(--text-muted)}"
    ".pl{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:0 0 14px;font-size:12px}"
    ".ch{display:flex;align-items:center;gap:5px;padding:4px 8px;border-radius:var(--radius);border:0.5px solid var(--border)}"
    ".ch.done{background:var(--bg-success);color:var(--text-success);border-color:transparent}"
    ".ch.running{background:var(--bg-warning);color:var(--text-warning);border-color:transparent}"
    ".ch.waiting{color:var(--text-secondary);border-style:dashed}.ch.pending{color:var(--text-muted)}"
    ".ar{color:var(--text-muted)}.lg{flex-direction:row!important;width:auto!important;gap:5px!important}"
    "@media (prefers-reduced-motion:no-preference){.r{animation:sp 2s linear infinite}}@keyframes sp{to{transform:rotate(360deg)}}</style>")
ICONS = {"done": "ti-check", "running": "ti-loader-2", "waiting": "ti-hourglass", "pending": "ti-circle-dashed"}


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


def slot(s: dict) -> str:
    if s["state"] == "done":
        value = s.get("value")
        label = s.get("label") if s.get("label") is not None else ("–" if value is None else f"{value:.2f}".rstrip("0").rstrip("."))
        kind = "f" if value is not None and value >= 0.999 else "o"
        tip = f"value {value}" + (f", {s['label']} steps" if s.get("label") is not None else "")
    elif s["state"] == "running":
        kind, label, tip = "r", f"{round(s['minutes'])}m", f"running {round(s['minutes'])} min"
    elif s["state"] == "error":
        kind, label, tip = "e", "err", s.get("why", "")
    else:
        kind, label, tip = "p", "", "pending"
    return f'<span class="s" title="{html.escape(str(tip))}"><i class="{kind}"></i><em>{html.escape(str(label))}</em></span>'


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
    stamp = time.strftime("%H:%M", time.localtime(now))
    pct = round(100 * len(done) / len(slots)) if slots else 0
    parts = [f'<h2 class="sr-only">Experiment progress at {stamp}: {len(done)} of {len(slots)} samples finished, '
             f'{len(running)} running.</h2>', STYLE]
    if plan:
        chips = []
        for step in plan:
            state = step.get("state", "pending")
            note = f' · {html.escape(step["note"])}' if step.get("note") else ""
            chips.append(f'<span class="ch {state}"><i class="ti {ICONS.get(state, ICONS["pending"])}" aria-hidden="true"></i>'
                         f'{html.escape(step["step"])}{note}</span>')
        parts.append('<div class="pl">' + '<span class="ar" aria-hidden="true">→</span>'.join(chips) + "</div>")
    eta_text = f" · ETA about {time.strftime('%H:%M', time.localtime(eta))}" if left else " · complete"
    parts.append(f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin:0 0 6px">'
                 f'<span style="font-size:16px;font-weight:500">{len(done)} of {len(slots)} samples</span>'
                 f'<span style="font-size:13px;color:var(--text-secondary)">{stamp} · {len(running)} running{eta_text}</span></div>'
                 f'<div style="height:8px;background:var(--surface-1);border-radius:4px;overflow:hidden;margin:0 0 16px">'
                 f'<div style="width:{pct}%;height:100%;background:{BLUE}"></div></div>')
    columns = f"minmax(0,1.3fr) repeat({len(arms)},minmax(0,1fr))"
    parts.append(f'<div style="display:grid;grid-template-columns:{columns};gap:8px;align-items:center"><div></div>'
                 + "".join(f'<div class="h" style="text-align:center">{html.escape(a)}</div>' for a in arms))
    for exp_id, exp in exps.items():
        parts.append(f'<div><div class="h">{html.escape(exp_id)} · {html.escape(exp["case"])}</div>'
                     f'<div class="m">{html.escape(band(exp))}</div></div>')
        for arm in arms:
            states = grid[(exp_id, arm)]
            values = [s["value"] for s in states if s["state"] == "done" and s.get("value") is not None]
            mean = f"{statistics.mean(values):.2f}" if values else "–"
            verdict = None
            record = out / exp_id / f"decision-{control}-{arm}.json"
            if arm != control and record.exists():
                verdict = json.loads(record.read_text()).get("verdict")
            tag = ('<b class="ok">supports</b>' if verdict == "supports" else '<b class="no">contradicts</b>'
                   if verdict == "contradicts" else f"<span>{html.escape(verdict)}</span>" if verdict else "")
            parts.append(f'<div class="c"><div class="row">{"".join(slot(s) for s in states)}</div>'
                         f'<div class="ft"><span>mean {mean}</span>{tag}</div></div>')
    parts.append("</div>")
    parts.append('<div class="ft" style="justify-content:flex-start;flex-wrap:wrap;gap:14px;margin-top:12px">'
                 '<span class="s lg"><i class="f" style="width:10px!important;height:10px!important"></i>scored 1</span>'
                 '<span class="s lg"><i class="o"></i>scored below 1</span>'
                 '<span class="s lg"><i class="r" style="animation:none"></i>running (minutes)</span>'
                 '<span class="s lg"><i class="p"></i>pending</span><span>number = steps planned, or the value</span></div>')
    return "".join(parts)


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
