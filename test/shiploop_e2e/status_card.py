#!/usr/bin/env python3
"""Render a status card for long-running work as an HTML fragment for an inline widget.

    python3 test/shiploop_e2e/status_card.py MODEL.json     # or the model on stdin

The owner's status style for runs, test tiers, experiment rounds and reviews (memory illustrated-status-card): a plan
strip of the agreed steps (each state with its own icon, so state is never colour alone), a progress bar with an
estimated end, and a grid of units of work (rows) by variants (columns) holding one slot per sample or attempt. The
model is JSON:

    {"plan": [{"step": "R1 K1", "state": "done" | "running" | "waiting" | "pending", "note": "..."}],
     "progress": {"done": 20, "total": 36, "unit": "samples", "running": 3, "stamp": "18:36", "eta": "20:27"},
     "columns": ["T control", "B prose"],
     "rows": [{"name": "K1 chess engine", "sub": "band 3+ steps",
               "cells": [{"slots": [{"state": "pass" | "below" | "running" | "pending" | "error",
                                     "label": "3", "tip": "3 steps"}],
                          "summary": "mean 0.25", "verdict": "supports" | "contradicts" | "<other text>"}]}],
     "legend": {"pass": "scored 1", "below": "scored below 1", "note": "number = steps planned"}}

Every key but `rows` is optional; a cell needs `slots`. An `error` slot is drawn as an error, never as a pass, and an
unknown slot state as pending. `render(model)` returns the fragment; nothing is read or written besides the model.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

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
PLAN_ICONS = {"done": "ti-check", "running": "ti-loader-2", "waiting": "ti-hourglass", "pending": "ti-circle-dashed"}
SLOT_CLASS = {"pass": "f", "below": "o", "running": "r", "pending": "p", "error": "e"}
LEGEND = {"pass": "passed", "below": "below target", "running": "running (minutes)", "pending": "pending", "note": ""}


def _esc(value) -> str:
    return html.escape("" if value is None else str(value))


def _slot(slot: dict) -> str:
    kind = SLOT_CLASS.get(slot.get("state"), "p")
    tip = slot.get("tip") or slot.get("state") or "pending"
    return f'<span class="s" title="{_esc(tip)}"><i class="{kind}"></i><em>{_esc(slot.get("label"))}</em></span>'


def _verdict(text) -> str:
    if not text:
        return ""
    if text == "supports":
        return '<b class="ok">supports</b>'
    if text == "contradicts":
        return '<b class="no">contradicts</b>'
    return f"<span>{_esc(text)}</span>"


def render(model: dict) -> str:
    progress = model.get("progress") or {}
    done, total = progress.get("done", 0), progress.get("total", 0)
    stamp = progress.get("stamp", "")
    unit = f' {_esc(progress["unit"])}' if progress.get("unit") else ""
    parts = [f'<h2 class="sr-only">Status at {_esc(stamp)}: {done} of {total}{unit} finished, '
             f'{progress.get("running", 0)} running.</h2>', STYLE]
    if model.get("plan"):
        chips = []
        for step in model["plan"]:
            state = step.get("state") if step.get("state") in PLAN_ICONS else "pending"
            note = f' · {_esc(step["note"])}' if step.get("note") else ""
            chips.append(f'<span class="ch {state}"><i class="ti {PLAN_ICONS[state]}" aria-hidden="true"></i>'
                         f'{_esc(step.get("step"))}{note}</span>')
        parts.append('<div class="pl">' + '<span class="ar" aria-hidden="true">→</span>'.join(chips) + "</div>")
    if progress:
        eta = f' · ETA about {_esc(progress["eta"])}' if progress.get("eta") else (" · complete" if total and done >= total else "")
        pct = round(100 * done / total) if total else 0
        parts.append(f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin:0 0 6px">'
                     f'<span style="font-size:16px;font-weight:500">{done} of {total}{unit}</span>'
                     f'<span style="font-size:13px;color:var(--text-secondary)">{_esc(stamp)} · {progress.get("running", 0)} running{eta}</span></div>'
                     f'<div style="height:8px;background:var(--surface-1);border-radius:4px;overflow:hidden;margin:0 0 16px">'
                     f'<div style="width:{pct}%;height:100%;background:{BLUE}"></div></div>')
    columns = model.get("columns") or []
    width = max([len(columns)] + [len(r.get("cells") or []) for r in model["rows"]])
    parts.append(f'<div style="display:grid;grid-template-columns:minmax(0,1.3fr) repeat({width},minmax(0,1fr));gap:8px;'
                 'align-items:center"><div></div>'
                 + "".join(f'<div class="h" style="text-align:center">{_esc(c)}</div>' for c in columns)
                 + "".join("<div></div>" for _ in range(width - len(columns))))
    for row in model["rows"]:
        parts.append(f'<div><div class="h">{_esc(row.get("name"))}</div><div class="m">{_esc(row.get("sub"))}</div></div>')
        for cell in row.get("cells") or []:
            summary = f'<span>{_esc(cell["summary"])}</span>' if cell.get("summary") else "<span></span>"
            parts.append(f'<div class="c"><div class="row">{"".join(_slot(s) for s in cell.get("slots") or [])}</div>'
                         f'<div class="ft">{summary}{_verdict(cell.get("verdict"))}</div></div>')
    parts.append("</div>")
    legend = {**LEGEND, **(model.get("legend") or {})}
    note = f'<span>{_esc(legend["note"])}</span>' if legend.get("note") else ""
    parts.append('<div class="ft" style="justify-content:flex-start;flex-wrap:wrap;gap:14px;margin-top:12px">'
                 f'<span class="s lg"><i class="f" style="width:10px!important;height:10px!important"></i>{_esc(legend["pass"])}</span>'
                 f'<span class="s lg"><i class="o"></i>{_esc(legend["below"])}</span>'
                 f'<span class="s lg"><i class="r" style="animation:none"></i>{_esc(legend["running"])}</span>'
                 f'<span class="s lg"><i class="p"></i>{_esc(legend["pending"])}</span>{note}</div>')
    return "".join(parts)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    text = Path(argv[0]).read_text() if argv else sys.stdin.read()
    print(render(json.loads(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
