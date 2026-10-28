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
     "legend": {"pass": "scored 1", "below": "scored below 1", "note": "number = steps planned"},
     "links": [{"label": "Run Review", "href": "/path/review-export/run-review.html"}]}

Every key but `rows` is optional; a cell needs `slots`. An `error` slot is drawn as an error, never as a pass, and an
unknown slot state as pending. `render(model)` returns the fragment; nothing is read or written besides the model.

One builder per kind of long job reads the job's own files and returns that model, so no tick script is written per job
(status consolidation, owner 2026-10-26):

    python3 test/shiploop_e2e/status_card.py build tier RECEIPT     # run-all.sh --output DIR: DIR or its receipt.json;
                                                                    # a run-all.sh log also works, its total unknown
    python3 test/shiploop_e2e/status_card.py build advisors RUN_DIR # an advisors panel run directory
    python3 test/shiploop_e2e/status_card.py build e2e RUN_FOLDER   # an E2E case run folder (events.jsonl, .shiploop-runs)

`build` prints the model as JSON; `--html` prints the card instead (the inline view); `--job JOB.json` prints the Live Run
Card's job document (the artifact view): the model plus `title`, `subtitle`, `status`, `updatedAt`, `events` (newest
first, 12 at most) and `findings`, with `progress.updatedAt` and `progress.etaAt`. JOB is `{title, subtitle, status,
events, findings, tiles, comparison, bands}`, every key optional; its events come before the builder's.

An e2e run with a run trace also gets `timeline` (`start`, `end`, `lanes`, `spans` of each stage and Improve review,
`marks` of each refused callback, epoch seconds) and `tiles` (elapsed, stages, Improve reviews, refusals, then one tile per
live trace check of run_trace.checks: keepalive text, packet reprint, owner note). In the job document, JOB's `tiles`
replace the builder's headline tiles and the trace-check tiles follow them, `comparison` (`{title, note, columns, rows: [{label, values, verdict:
{text, tone: ok|warn|bad}}], caption}`) is passed through, and `bands` (`[{start, end, label}]`, such as the periods the
machine slept) joins the timeline. A finding may carry `example`, `before`, `after` and `evidence` beside its `tag`,
`status` (firm, interim, early, superseded, missed), `title` and `text`. The Live Run Card page that draws all of this is
live_run_card.html beside this file (published at the artifact named in memory illustrated-status-card).

`build e2e RUN --job JOB.json --actions DIR` also writes one document per action to DIR/<action>.json (for the card's
jobs/<job>/actions/<action>): the prompt as sent, the host's dialogue (clipped per kind, first 20 and last 140 events of a
long action), the refused callbacks and an Improve action's review passes. It adds the inspector's `actions` index and
the `material` items to the job document, and lists in DIR/changed.json the actions whose document changed since the
last call. Material: an Improve pass classified non-trivial, a refusal from a substantive gate (a length cap or an
ordering slip is minor), a send-back or a block.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import html
import json
import re
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
LEGEND = {"pass": "passed", "below": "below target", "running": "running (minutes)", "pending": "pending",
          "error": "error, not a result", "note": ""}
# Each slot state's legend mark, in legend order. The legend names only the states the grid draws (an unknown state
# draws as pending): R3's card (2026-10-26) listed "scored 1" with no such slot and left its error slots unexplained.
LEGEND_MARKS = (("pass", '<i class="f" style="width:10px!important;height:10px!important"></i>'), ("below", '<i class="o"></i>'),
                ("running", '<i class="r" style="animation:none"></i>'), ("pending", '<i class="p"></i>'),
                ("error", '<i class="e"></i>'))


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
    drawn = {s.get("state") if s.get("state") in SLOT_CLASS else "pending"
             for row in model["rows"] for cell in row.get("cells") or [] for s in cell.get("slots") or []}
    note = f'<span>{_esc(legend["note"])}</span>' if legend.get("note") else ""
    parts.append('<div class="ft" style="justify-content:flex-start;flex-wrap:wrap;gap:14px;margin-top:12px">'
                 + "".join(f'<span class="s lg">{mark}{_esc(legend[state])}</span>'
                           for state, mark in LEGEND_MARKS if state in drawn)
                 + f'{note}</div>')
    if model.get("links"):
        parts.append('<div class="ft" style="justify-content:flex-start;flex-wrap:wrap;gap:14px">'
                     + "".join(f'<span>{_esc(link.get("label"))}: {_esc(link.get("href"))}</span>'
                               for link in model["links"]) + "</div>")
    return "".join(parts)


# --- builders: one per kind of long job.  Each reads only the job's own files and returns (model, meta), where meta is
# {title, subtitle, status: running|done|failed, events: [{at, kind, text}] newest first, eta_at: datetime|None}.

EVENTS = 12   # the Live Run Card shows the newest 12


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def _started(path: Path) -> float:
    stat = path.stat()
    return getattr(stat, "st_birthtime", stat.st_mtime)


def _progress(done: int, total: int, unit: str, running: int, now: datetime, mean: float | None,
              lanes: int = 1) -> tuple[dict, datetime | None]:
    """The model's progress and its ETA: what remains times the mean seconds per unit so far, over the lanes."""
    eta = (now + timedelta(seconds=(total - done) * mean / max(1, lanes))
           if mean and done and total > done else None)
    progress = {"done": done, "total": total, "unit": unit, "running": running, "stamp": now.strftime("%H:%M")}
    if eta:
        progress["eta"] = eta.strftime("%H:%M")
    return progress, eta


def _tier_log(text: str) -> tuple[list, dict, int, str, str]:
    """(selected (family, id), finished {id: record}, lanes, status, groups) from a run-all.sh log."""
    selected, finished, lanes, status, groups = [], {}, 1, "running", ""
    for line in text.splitlines():
        if (match := re.match(r"^==> \[([^\]]*)\] (\S+)$", line)):
            selected.append((match.group(1), match.group(2)))
        elif (match := re.match(r"^(OK|FAIL)\s+(\S+)$", line)):
            finished[match.group(2)] = {"status": "passed" if match.group(1) == "OK" else "failed"}
        elif (match := re.search(r"\(--jobs (\d+)\)", line)):
            lanes = int(match.group(1))
        if (match := re.match(r"^run-all\.sh: (PASS|FAILED)(?: \((.*) hermetic group selection\))?", line)):
            status, groups = ("passed" if match.group(1) == "PASS" else "failed"), match.group(2) or groups
    return selected, finished, lanes, status, groups


def build_tier(path: Path, now: datetime | None = None) -> tuple[dict, dict]:
    """A test tier: run-all.sh's --output receipt (the directory or its receipt.json), else its log."""
    now = now or datetime.now().astimezone()
    receipt = path / "receipt.json" if path.is_dir() else path
    known_total = receipt.suffix == ".json"
    if known_total:
        data = json.loads(receipt.read_text(encoding="utf-8"))
        selected = [(row["family"], row["id"]) for row in data.get("selected") or ()]
        finished = {row["id"]: row for row in data.get("completed") or ()}
        lanes, status = int(data.get("jobs") or 1), str(data.get("status") or "running")
        groups = ", ".join(data.get("groups") or ())
    else:
        selected, finished, lanes, status, groups = _tier_log(receipt.read_text(encoding="utf-8", errors="replace"))
    waiting = [suite for _family, suite in selected if suite not in finished]
    running = set(waiting[:lanes]) if status == "running" else set()
    families: dict[str, list[str]] = {}
    for family, suite in selected:
        families.setdefault(family, []).append(suite)
    rows, plan = [], []
    for family, suites in families.items():
        slots, failed = [], []
        for suite in suites:
            record = finished.get(suite)
            seconds = (record or {}).get("duration_seconds")
            tip = suite + (" (" + str(round(seconds)) + " s)" if seconds is not None else "")
            if record is None:
                slots.append({"state": "running" if suite in running else "pending", "tip": suite})
            elif record.get("status") == "passed":
                slots.append({"state": "pass", "tip": tip})
            else:
                slots.append({"state": "error", "tip": tip + ": " + str(record.get("status"))})
                failed.append(suite)
        ended = sum(1 for suite in suites if suite in finished)
        rows.append({"name": family, "sub": str(len(suites)) + " suites", "cells": [{
            "slots": slots, "summary": str(ended - len(failed)) + " of " + str(len(suites)) + " OK",
            "verdict": ("failed: " + ", ".join(failed)) if failed else ("passes" if ended == len(suites) else "")}]})
        plan.append({"step": family, "state": "done" if ended == len(suites) else
                     "running" if any(suite in running for suite in suites) else "pending"})
    durations = [row["duration_seconds"] for row in finished.values() if row.get("duration_seconds") is not None]
    progress, eta = _progress(len(finished), len(selected), "suites", len(running), now,
                              sum(durations) / len(durations) if durations else None, lanes)
    model = {"plan": plan, "progress": progress, "columns": ["suites"], "rows": rows,
             "legend": {"pass": "passed", "running": "running", "pending": "not started",
                        "note": "" if known_total else "total read from the log so far; --output gives the receipt"}}
    failures = [suite for suite, record in finished.items() if record.get("status") != "passed"]
    events = [{"at": _iso(now), "kind": "error", "text": "FAIL " + suite} for suite in failures]
    if status != "running":
        events.insert(0, {"at": _iso(now), "kind": "done" if status == "passed" else "error",
                          "text": "tier " + status + ": " + str(len(finished) - len(failures)) + " of "
                          + str(len(selected)) + " suites OK"})
    return model, {"title": "Test tier" + (" (" + groups + ")" if groups else ""),
                   "subtitle": str(len(selected)) + " suites, --jobs " + str(lanes),
                   "status": {"passed": "done"}.get(status, status), "events": events[:EVENTS], "eta_at": eta}


SEATS = {"opus": "Opus", "codex": "Astra", "grok": "Grok", "kimi": "Kimi"}


def build_advisors(run: Path, now: datetime | None = None) -> tuple[dict, dict]:
    """An advisors panel: two passes of parallel seats, then the host's final.md."""
    now = now or datetime.now().astimezone()
    # The seats are named by the files each pass writes as it starts (pass<n>-<seat>-prompt.md) or ends; before any,
    # the default four.
    found = {match.group(2) for path in run.glob("pass[12]-*.md")
             if (match := re.fullmatch(r"pass([12])-([a-z0-9]+)(?:-prompt)?\.md", path.name))}
    seats = [seat for seat in SEATS if seat in found or not found] + sorted(found - set(SEATS))
    rows, answered, events, verdicts = [], 0, [], []
    for number in (1, 2):
        host = run / ("pass" + str(number) + "-host.log")
        log = host.read_text(encoding="utf-8", errors="replace") if host.exists() else ""
        started = host.exists() or (number == 1 and (run / "prompt.txt").exists())
        ended = (run / ("pass" + str(number) + "-meta.json")).exists()
        slots = []
        for seat in seats:
            answer = run / ("pass" + str(number) + "-" + seat + ".md")
            size = answer.stat().st_size if answer.exists() else 0
            state = ("error" if "❌ pass" + str(number) + " " + seat + ":" in log else
                     "pass" if "✅ pass" + str(number) + " " + seat + ":" in log or size > 200 else
                     "error" if ended else "running" if started else "pending")
            answered += state == "pass"
            name = SEATS.get(seat, seat.title())
            slots.append({"state": state, "label": name[0],
                          "tip": name + (" (" + str(round(size / 1024)) + " KB)" if size else "")})
        events += [{"at": _iso(now), "kind": "done" if line.startswith("✅") else "error", "text": line.strip()}
                   for line in log.splitlines() if line.startswith(("✅", "❌"))]
        verdicts.append("done" if ended else "running" if started else "pending")
        rows.append({"name": "Pass " + str(number), "sub": "independent" if number == 1 else "each seat reads the others",
                     "cells": [{"slots": slots, "summary": str(sum(s["state"] == "pass" for s in slots)) + " of "
                                + str(len(slots)) + " answered", "verdict": verdicts[-1]}]})
    final = (run / "final.md").exists()
    plan = [{"step": "Pass 1", "state": verdicts[0]}, {"step": "Pass 2", "state": verdicts[1]},
            {"step": "Synthesis", "state": "done" if final else "pending"}]
    prompt = run / "prompt.txt"
    minutes = round((now.timestamp() - _started(prompt)) / 60) if prompt.exists() else None
    running = sum(slot["state"] == "running" for entry in rows for slot in entry["cells"][0]["slots"])
    progress, eta = _progress(answered + final, 2 * len(seats) + 1, "answers", running, now, None)
    names = [SEATS.get(seat, seat.title()) for seat in seats]
    model = {"plan": plan, "progress": progress, "columns": ["seats"], "rows": rows,
             "legend": {"pass": "answered", "running": "running", "pending": "not started",
                        "note": "letters: " + ", ".join(name[0] + " " + name for name in names)}}
    if final:
        events.append({"at": _iso(now), "kind": "done", "text": "final.md written"})
    return model, {"title": "Advisors " + run.name,
                   "subtitle": (str(minutes) + " min, " if minutes is not None else "") + str(len(seats)) + " seats",
                   "status": "done" if final else "running", "events": list(reversed(events))[:EVENTS], "eta_at": eta}


def build_e2e(folder: Path, now: datetime | None = None) -> tuple[dict, dict]:
    """An E2E case run: the ShipLoop run's stages by item (from its state), host restarts, refusals and the result."""
    import metrics  # the harness's own record reader, and its path to ShipLoop's stage table
    if str(metrics.SCRIPTS) not in sys.path:
        sys.path.insert(0, str(metrics.SCRIPTS))
    import shiploop_stage_spec as stage_spec
    now = now or datetime.now().astimezone()
    states = sorted(folder.glob(".shiploop-runs/*/run/state.md"))
    state = (metrics._state_block(states[0]) if states else None) or {}
    history = [entry for entry in state.get("history") or () if isinstance(entry, dict)]
    items = [entry.get("id") for entry in state.get("work_items") or () if isinstance(entry, dict)]
    index = state.get("work_index") if isinstance(state.get("work_index"), int) else 0
    finished_items = set(state.get("completed_work_items") or ())
    cursor = str(state.get("stage") or "")
    loops = state.get("inner_loops") or {}
    current = ((items[index], str((loops.get(items[index]) or {}).get("stage") or ""))
               if cursor == "inner-loop" and 0 <= index < len(items) else (None, cursor))
    reviewing = state.get("active_improve") is not None

    def row(name: str, item: str | None, stages: tuple[str, ...], over: bool) -> dict:
        """One slot per stage: done (a number when it ran more than once), current, blocked or not yet run; a part of
        the run that is over shows only the stages it ran."""
        slots, sends = [], 0
        for stage in stages:
            entries = [entry for entry in history if entry.get("stage") == stage and entry.get("workitem") == item]
            sends += sum(1 for entry in entries if entry.get("outcome") in ("send-back", "add-work"))
            done = sum(1 for entry in entries if entry.get("outcome") == "done")
            if current == (item, stage):
                slots.append({"state": "running", "label": "I" if reviewing else "",
                              "tip": stage + (" (Improve review)" if reviewing else "")})
            elif done:
                slots.append({"state": "pass", "label": str(done) if done > 1 else "", "tip": stage})
            elif any(entry.get("outcome") == "blocked" for entry in entries):
                slots.append({"state": "error", "tip": stage + ": blocked"})
            elif not over:
                slots.append({"state": "pending", "tip": stage})
        return {"name": name, "sub": str(sends) + " sent back or added work" if sends else "",
                "cells": [{"slots": slots}]}

    in_prelude = cursor in stage_spec.PRELUDE
    outer = cursor in stage_spec.OUTER
    rows = [row("Prelude", None, stage_spec.PRELUDE, not in_prelude)]
    rows += [row(item, item, stage_spec.INNER, item in finished_items) for item in items]
    rows.append(row("Outer", None, stage_spec.OUTER, cursor == "done"))
    result = folder / "result.json"
    plan = [{"step": "Prelude", "state": "running" if in_prelude else "done"}]
    plan += [{"step": item, "state": "done" if item in finished_items else "running" if current[0] == item
              else "pending"} for item in items]
    plan += [{"step": "Outer", "state": "done" if cursor == "done" else "running" if outer else "pending"},
             {"step": "Result", "state": "done" if result.exists() else "pending"}]
    slots = [slot for entry in rows for slot in entry["cells"][0]["slots"]]
    done = sum(slot["state"] == "pass" for slot in slots)
    minutes = (now.timestamp() - _started(folder)) / 60
    progress, eta = _progress(done, len(slots), "stages", sum(slot["state"] == "running" for slot in slots), now,
                              60 * minutes / done if done else None)
    try:
        with (folder / "events.jsonl").open(encoding="utf-8", errors="replace") as stream:
            refusals = sum(1 for line in stream if "ShipLoop navigator: " in line)
    except OSError:
        refusals = None
    restarts = len(list(folder.glob("resume-*.txt")))
    kinds = {"done": "done", "send-back": "warn", "add-work": "warn", "blocked": "error"}
    events = [{"at": _iso(now), "kind": kinds.get(str(entry.get("outcome")), "info"),
               "text": str(entry.get("outcome")) + ": " + str(entry.get("stage")) + " ("
               + str(entry.get("workitem") or "run") + ")"} for entry in reversed(history[-EVENTS:])]
    status = "done" if result.exists() else "failed" if state.get("status") == "blocked" else "running"
    model = {"plan": plan, "progress": progress, "columns": ["stages"], "rows": rows,
             "legend": {"pass": "done (a number: times run)", "running": "current (I: Improve review)",
                        "pending": "not yet run", "note": "a finished part shows only the stages it ran"}}
    # The run's own pages, run level first (E2E, 2026-10-26): Run Review answers how the run went, the flow viewer
    # what the model saw and did at each action.
    links = [{"label": label, "href": str(path)} for label, path in (
        ("Run Review", folder / "review-export" / "run-review.html"), ("flow", folder / "flow.html")) if path.exists()]
    if links:
        model["links"] = links
    line = _timeline(states[0].parent / "trace.jsonl", current[0], stage_spec) if states else None
    if line:
        model["timeline"] = line
    checks = _check_tiles(states[0].parent) if states else []
    if line or checks:
        model["tiles"] = (_e2e_tiles(line, progress) if line else []) + checks
    return model, {"title": "E2E " + folder.name, "subtitle": str(round(minutes)) + " min · "
                   + ("refusals not read" if refusals is None else str(refusals) + " refusals") + " · "
                   + str(restarts) + " host restarts", "status": status, "events": events, "eta_at": eta}


def _trace_rows(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and isinstance(row.get("ts"), (int, float)):
            rows.append(row)
    return rows


def _timeline(trace: Path, open_item: str | None, stage_spec) -> dict | None:
    """The run on one time axis, from ShipLoop's run trace (RUN/trace.jsonl, shiploop 1.12.0 and later): each accepted
    callback closes the span of the stage it finished and opens the next; an Improve review is its own span (kind
    `improve`) in the lane of the stage it reviews; each refused callback is a mark (`check` when it was a --check-only
    check). Lanes are Prelude, each work item, Outer. Times are epoch seconds; the stage the run is on has end None.
    None when the run has no trace."""
    rows = _trace_rows(trace) if trace.is_file() else []
    if not rows:
        return None
    items = {row.get("action"): row.get("item") for row in rows if row.get("kind") == "packet" and row.get("item")}
    spans, marks, lanes = [], [], []
    opened, reviewed = round(rows[0]["ts"], 1), (None, None)   # reviewed: the last stage span's (lane, stage)

    def lane(stage, action) -> str:
        if stage == "improve":
            return reviewed[0] or "Prelude"
        if stage in stage_spec.PRELUDE:
            return "Prelude"
        if stage in stage_spec.OUTER:
            return "Outer"
        return str(items.get(action) or open_item or "Work")

    def add(span: dict) -> None:
        spans.append(span)
        if span["lane"] not in lanes:
            lanes.append(span["lane"])

    last, printed = None, None   # printed: the action of a packet printed since the last accepted callback
    for row in rows:
        if row.get("kind") == "packet":
            printed = row.get("action") or printed
        stage = row.get("stage") if isinstance(row.get("stage"), list) and len(row["stage"]) == 2 else None
        if row.get("kind") != "command" or row.get("verb") != "complete" or not stage:
            continue
        at = round(row["ts"], 1)
        if row.get("exit") not in (0, None):
            marks.append({"at": at, "kind": "check" if row.get("check_only") else "refusal",
                          "lane": lane(stage[0], row.get("action")), "stage": stage[0], "text": str(row.get("error") or "")})
            continue
        if row.get("check_only"):
            continue
        name = reviewed[1] if stage[0] == "improve" else stage[0]
        span = {"lane": lane(stage[0], row.get("action")), "stage": name, "action": row.get("action"),
                "kind": "improve" if stage[0] == "improve" else "stage", "start": opened, "end": at}
        add(span)
        if span["kind"] == "stage":
            reviewed = (span["lane"], span["stage"])
        opened, last, printed = at, stage[1], None
    if last and last != "done":
        add({"lane": lane(last, printed), "stage": reviewed[1] if last == "improve" else last, "action": printed,
             "kind": "improve" if last == "improve" else "stage", "start": opened, "end": None})
    order = ["Prelude"] + [name for name in lanes if name not in ("Prelude", "Outer")] + ["Outer"]
    return {"start": round(rows[0]["ts"], 1), "end": opened if last == "done" else None,
            "lanes": [name for name in order if name in lanes], "spans": spans, "marks": marks}


def _e2e_tiles(line: dict, progress: dict) -> list[dict]:
    """The Live Run Card's headline numbers for a traced run: elapsed (live while it runs), stages, Improve reviews and
    refusals."""
    reviews = [span for span in line["spans"] if span["kind"] == "improve"]
    minutes = sum(span["end"] - span["start"] for span in reviews if span["end"] is not None) / 60
    checks = sum(mark["kind"] == "check" for mark in line["marks"])
    elapsed = {"label": "Elapsed", "live": "elapsed", "since": line["start"]}
    if line["end"] is not None:
        total = round(line["end"] - line["start"])
        elapsed = {"label": "Elapsed", "value": f"{total // 3600} h {total % 3600 // 60:02d} min"}
    return [elapsed,
            {"label": "Stages", "value": f'{progress.get("done", 0)} of {progress.get("total", 0)}'},
            {"label": "Improve reviews", "value": str(len(reviews)), "sub": f"{minutes:.1f} min"},
            {"label": "Refusals", "value": str(len(line["marks"])),
             "sub": f'{checks} a --check-only check' if checks == 1 else f"{checks} --check-only checks"}]


CHECK_LABELS = {"keepalive_text": "Keepalive text", "packet_reprint": "Packet reprint", "owner_note": "Owner note"}
CHECK_TONES = {"pass": "ok", "fail": "bad", "open": "warn"}
CHECK_SUB = 90  # characters of a check's evidence a tile shows; metrics.json keeps it whole


def _check_tiles(run_dir: Path) -> list[dict]:
    """The run trace's live checks (run_trace.checks) as tiles: the verdict, its evidence and a tone. A check the run has
    not exercised stays neutral, never a pass; a run without a trace has none."""
    import run_trace  # the harness's reader of RUN/trace.jsonl, as metrics.json's run_trace.checks uses it
    found = run_trace.checks(run_trace.read(run_dir)) or {}
    tiles = []
    for name, row in found.items():
        evidence = row["evidence"]
        tiles.append({"label": CHECK_LABELS.get(name, name), "value": row["verdict"], "tone": CHECK_TONES.get(row["verdict"], ""),
                      "sub": evidence if len(evidence) <= CHECK_SUB else evidence[:CHECK_SUB - 1] + "…", "check": name})
    return tiles


# --- action documents: what the Live Run Card's inspector opens for one action -----------------------------------------
# One document per action (jobs/<job>/actions/<action>, each under the database's 256 KiB): the prompt as sent, the
# host's dialogue in order, the refused callbacks and, for an Improve action, its review passes. Long bodies are clipped
# per kind (the model's own words longest) and a long action keeps its first and last events.

CLIP = {"say": 3000, "call": 700, "result": 600, "injected": 400, "hook": 400, "refusal": 1200, "keepalive": 400}
ACTION_EVENTS = 160   # an action document keeps its first 20 and last 140 events and counts the rest
PROMPT_CHARS = 60000
# A refused callback is minor when the model only has to shorten a field, write the result first, or finish a loop it
# started; any other gate (coverage, test layers, mutants, not_covered, ...) found something material.
MINOR_REFUSAL = re.compile(r"is \d+ characters; keep it within|characters together; the limit is|must be one line of at "
                           r"most \d+ characters|^no result file|"
                           r"evidence_refs cite files that do not exist|loop is still active|the following arguments are "
                           r"required|exactly one shiploop-state fence|^Run the improve skill|^Complete \S*review-\d+\.md "
                           r"\(missing or invalid|^not_covered is \[|requires outcome and summary|must be a short "
                           r"identifier|\.disposition must be one of")
# A review section runs from its heading ("Found:") to the next heading or the handoff, on one line or the lines below.
REVIEW_SECTION = r"^{name}:[ \t]*(.*?)(?=^(?:Read|Found|Changed|Checked|Class):|^## |\Z)"


def refusal_is_material(text: str) -> bool:
    return not MINOR_REFUSAL.search(str(text or "").strip())


def _review_section(text: str, name: str) -> str:
    found = re.search(REVIEW_SECTION.format(name=name), text, re.MULTILINE | re.DOTALL)
    return "\n".join(line.strip() for line in found.group(1).strip().splitlines() if line.strip())[:1500] if found else ""


def _review_title(found: str) -> str:
    """A pass's headline: its first item's bold lead, else its first sentence."""
    body = re.sub(r"^\d+\.\s*", "", " ".join(found.split())).strip()
    bold = re.match(r"\*\*(.+?)\*\*", body)
    if bold:
        return bold.group(1)[:240]
    sentence = re.match(r"(.+?[.;])(\s|$)", body)
    return (sentence.group(1) if sentence else body)[:240]


def review_passes(worktree: Path, stage: str, reviewed: str) -> list[dict]:
    """An Improve action's review passes, in order: each review-<n>.md's classification, its Found, Changed and Checked
    sections and a one-line title (the review folder is <stage>-<last 8 of the reviewed action>)."""
    folder = worktree / ".shiploop-improve" / f"{stage}-{str(reviewed)[-8:]}" / "reviews"
    passes = []
    for path in sorted(folder.glob("review-*.md"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0)):
        text = path.read_text(encoding="utf-8", errors="replace")
        head = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
        fields = dict(re.findall(r"^(\w[\w-]*):\s*(.*)$", head.group(1), re.MULTILINE)) if head else {}
        found = _review_section(text, "Found")
        passes.append({"pass": int(re.sub(r"\D", "", path.stem) or 0), "classification": fields.get("classification", ""),
                       "title": _review_title(found), "found": found, "changed": _review_section(text, "Changed"),
                       "checked": _review_section(text, "Checked")})
    return passes


def _clipped(kind: str, text) -> tuple[str, bool]:
    text, limit = str(text or ""), CLIP.get(kind, 600)
    return (text, False) if len(text) <= limit else (text[:limit] + "…", True)


def action_documents(flow_doc: dict, reviews) -> tuple[list[dict], dict[str, dict], list[dict]]:
    """From flow.build's actions: the inspector's index (one small row per action), one document per action, and every
    material item in time order: a review pass classified non-trivial, a refused callback from a substantive gate, a
    send-back or a block. ``reviews(stage, reviewed_action)`` returns an Improve action's passes."""
    index, docs, material = [], {}, []
    for action in flow_doc.get("actions") or ():
        name = action.get("action")
        events = [event for phase in action.get("phases") or () for event in phase.get("events") or ()]
        packet = next((phase["packet"] for phase in action.get("phases") or () if phase.get("packet")), None) or {}
        omitted = max(0, len(events) - ACTION_EVENTS)
        kept = events if not omitted else events[:20] + events[-(ACTION_EVENTS - 20):]
        dialogue = []
        for event in kept:
            text, clipped = _clipped(event.get("kind"), (event.get("body") or {}).get("text"))
            row = {"t": event.get("t"), "kind": event.get("kind"), "text": text, "clipped": clipped}
            if event.get("tool"):
                row["tool"] = event["tool"]
            if event.get("kind") == "refusal":
                row["check"] = bool(event.get("check_only"))
            dialogue.append(row)
        improve = action.get("stage") == "improve"
        stage = (str(action.get("reviewed_stage") or "") + " review") if improve else action.get("stage")
        refusals = [{"t": event.get("t"), "check": bool(event.get("check_only")),
                     "text": _clipped("refusal", (event.get("body") or {}).get("text"))[0],
                     "material": refusal_is_material((event.get("body") or {}).get("text"))}
                    for event in events if event.get("kind") == "refusal"]
        passes = reviews(action.get("reviewed_stage"), action.get("reviewed")) if improve else []
        found = [{"action": name, "stage": stage, "kind": "refusal", "t": r["t"], "title": r["text"].split("\n")[0][:240],
                  "detail": r["text"]} for r in refusals if r["material"]]
        found += [{"action": name, "stage": stage, "kind": "review", "t": None, "pass": p["pass"],
                   "title": p.get("title") or p["found"][:240] or "non-trivial pass",
                   "detail": "Found: " + p["found"] + "\nChanged: " + p["changed"]
                   + ("\nChecked: " + p["checked"] if p["checked"] else "")}
                  for p in passes if p["classification"] == "non-trivial"]
        if action.get("outcome") in ("send-back", "add-work", "blocked"):
            found.append({"action": name, "stage": stage, "kind": str(action["outcome"]), "t": None,
                          "title": str(action.get("stage")) + ": " + str(action["outcome"]), "detail": ""})
        sends = packet.get("sends") or []
        prompt = {"text": str(packet.get("text") or "")[:PROMPT_CHARS], "chars": packet.get("chars"),
                  "prints": packet.get("prints"), "reprints": packet.get("reprints"),
                  "file": (sends[0] or {}).get("file") if sends else None} if packet else None
        docs[name] = {"action": name, "index": action.get("index"), "stage": stage, "kind": "improve" if improve else "stage",
                      "item": action.get("work_item"), "outcome": action.get("outcome"), "prompt": prompt,
                      "dialogue": dialogue, "omitted": omitted, "refusals": refusals, "review": passes,
                      "material": found}
        times = [event.get("t") for event in events if isinstance(event.get("t"), (int, float))]
        index.append({"id": name, "index": action.get("index"), "stage": stage, "kind": "improve" if improve else "stage",
                      "item": action.get("work_item"), "outcome": action.get("outcome"), "events": len(events),
                      "refusals": len(refusals), "material": len(found), "says": sum(e.get("kind") == "say" for e in events),
                      "t0": min(times) if times else None, "t1": max(times) if times else None})
        material += found
    return index, docs, material


def build_e2e_actions(folder: Path, out_dir: Path) -> dict:
    """Write one action document per action to OUT_DIR/<action>.json and return {index, material, changed}: changed are
    the actions whose document differs from the last call's (OUT_DIR/manifest.json), the ones to write to the card."""
    import hashlib

    import flow  # the harness's per-action reader of the host stream and the run trace
    worktrees = sorted(folder.glob(".shiploop-runs/*/worktree"))
    worktree = worktrees[0] if worktrees else folder
    index, docs, material = action_documents(flow.build(folder), lambda stage, reviewed: review_passes(worktree, stage, reviewed))
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    try:
        before = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        before = {}
    after, changed = {}, []
    for name, doc in docs.items():
        text = json.dumps(doc, ensure_ascii=False)
        after[name] = hashlib.sha256(text.encode()).hexdigest()
        if before.get(name) != after[name]:
            (out_dir / f"{name}.json").write_text(text, encoding="utf-8")
            changed.append(name)
    manifest_path.write_text(json.dumps(after), encoding="utf-8")
    return {"index": index, "material": material, "changed": changed}


BUILDERS = {"tier": build_tier, "advisors": build_advisors, "e2e": build_e2e}


def job_document(model: dict, meta: dict, job: dict | None = None, now: datetime | None = None) -> dict:
    """The Live Run Card's job document: the model plus the job's title, status, events and findings."""
    now, job = now or datetime.now().astimezone(), job or {}
    progress = dict(model.get("progress") or {}, updatedAt=_iso(now))
    if meta.get("eta_at"):
        progress["etaAt"] = _iso(meta["eta_at"])
    document = {**model, "progress": progress, "title": job.get("title") or meta["title"],
                "subtitle": job.get("subtitle") or meta["subtitle"], "status": job.get("status") or meta["status"],
                "updatedAt": _iso(now), "events": (list(job.get("events") or ()) + list(meta["events"]))[:EVENTS],
                "findings": list(job.get("findings") or ())}
    if job.get("tiles"):
        # The job's tiles replace the builder's headline numbers; the trace checks are the run's, so they stay.
        document["tiles"] = list(job["tiles"]) + [tile for tile in model.get("tiles") or () if tile.get("check")]
    if job.get("comparison"):
        document["comparison"] = job["comparison"]
    if job.get("bands") and document.get("timeline"):
        document["timeline"] = {**document["timeline"], "bands": list(job["bands"])}
    return document


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if argv[:1] == ["build"]:
        parser = argparse.ArgumentParser(prog="status_card.py build")
        parser.add_argument("kind", choices=sorted(BUILDERS))
        parser.add_argument("path", type=Path)
        view = parser.add_mutually_exclusive_group()
        view.add_argument("--html", action="store_true", help="print the inline card instead of the model")
        view.add_argument("--job", type=Path, help="print the Live Run Card job document; JOB.json adds its keys")
        parser.add_argument("--actions", type=Path, help="e2e with --job: write each action's document to ACTIONS/ and "
                            "add the inspector's index and the material items; ACTIONS/changed.json lists the new ones")
        args = parser.parse_args(argv[1:])
        if args.actions and not (args.job and args.kind == "e2e"):
            parser.error("--actions needs e2e and --job")
        model, meta = BUILDERS[args.kind](args.path)
        if args.html:
            print(render(model))
        elif args.job:
            document = job_document(model, meta, json.loads(args.job.read_text(encoding="utf-8")))
            if args.actions:
                found = build_e2e_actions(args.path, args.actions)
                document["actions"], document["material"] = found["index"], found["material"]
                (args.actions / "changed.json").write_text(json.dumps(found["changed"]), encoding="utf-8")
            print(json.dumps(document, indent=1))
        else:
            print(json.dumps(model, indent=1))
        return 0
    text = Path(argv[0]).read_text() if argv else sys.stdin.read()
    print(render(json.loads(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
