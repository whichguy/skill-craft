#!/usr/bin/env python3
"""Whole-run tokens and seconds of E-EFF1 run folders, for the decision (plan section 3: the decision uses run totals).

    python3 -B run_totals.py totals RUN_FOLDER...                 # one JSON object per folder
    python3 -B run_totals.py classes RUN_FOLDER...                # the same, split by the class each session ran in
    python3 -B run_totals.py refusals RUN_FOLDER...               # navigator refusals, restart-induced ones apart
    python3 -B run_totals.py tokens POOL.jsonl --out tokens.json [--class all|M|I2]   # the file `place --tokens` reads

Tokens are what the host CLI reports per model call (Grok `usage` events): `input_tokens` is the whole prompt, the
uncached part plus `cache_read_input_tokens` and `cache_creation_input_tokens`; `output_tokens` already includes
`reasoning_tokens`. The decision's token count is prompt plus output (rubric-eval SPEC section 8); output alone and the
reasoning share are kept beside it because effort acts on them. Seconds are the host sessions' own span, the sum of
end minus start in sessions.jsonl (the harness's waits between sessions are not counted); without that file the first
to the last event time. A folder with no usage events has no token count (None), never zero.

Classes (effort.py): a session belongs to the class of the launch that started it, read from effort.json in launch order, so
`classes` needs a run made with --effort-schedule and refuses (None) a folder whose launches and sessions do not line up.
`--class M` or `--class I2` gives each artifact the totals of that class only, for the analysis beside the run totals
(plan section 10); a run with no session of that class has None, which `analyze` leaves out and never counts as zero.

Refusals: the navigator's refusals in the event stream, each counted once (the stream repeats a result). A refusal is
restart-induced when it is one of the two `improve-pass` refusals that R1 showed a boundary causes ("Write this pass's
review", "This review loop has already ended") and it fell in a session the harness started for a boundary (reason
`effort`). They are reported apart and left out of the refusal gate in both arms; every other refusal stays in it.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _int(value) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def totals(out: Path) -> dict:
    out = Path(out)
    prompt = output = reasoning = calls = 0
    try:
        lines = (out / "events.jsonl").read_text(errors="replace").splitlines()
    except OSError:
        lines = []
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "usage" and isinstance(event.get("usage"), dict):
            use = event["usage"]
            calls += 1
            prompt += _int(use.get("input_tokens")) + _int(use.get("cache_read_input_tokens")) \
                + _int(use.get("cache_creation_input_tokens"))
            output += _int(use.get("output_tokens"))
            reasoning += _int(use.get("reasoning_tokens"))
    seconds, sessions, open_starts = 0.0, 0, {}
    try:
        for line in (out / "sessions.jsonl").read_text(errors="replace").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("row") == "start":
                open_starts[row["n"]] = row["t"]
            elif row.get("row") == "end" and row.get("n") in open_starts:
                seconds += max(0.0, row["t"] - open_starts.pop(row["n"]))
                sessions += 1
    except OSError:
        pass
    return {"run": str(out), "model_calls": calls, "prompt_tokens": prompt if calls else None,
            "output_tokens": output if calls else None, "reasoning_tokens": reasoning if calls else None,
            "tokens": prompt + output if calls else None, "seconds": round(seconds, 1) if sessions else None,
            "sessions": sessions, "sessions_unended": len(open_starts)}


RESTART_REFUSALS = ("Write this pass's review", "This review loop has already ended")
NAVIGATOR = "ShipLoop navigator: "


def _sessions(out: Path) -> list[dict]:
    """Sessions in start order with their first event line, end time and reason; unended ones carry no end."""
    rows, ends = [], {}
    try:
        lines = (Path(out) / "sessions.jsonl").read_text(errors="replace").splitlines()
    except OSError:
        return rows
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("row") == "start":
            rows.append(row)
        elif row.get("row") == "end":
            ends[row.get("n")] = row
    return [dict(r, end_t=ends[r["n"]]["t"] if r["n"] in ends else None) for r in rows]


def class_totals(out: Path) -> dict | None:
    """Totals per class ({"M": {...}, "I2": {...}, "D": {...}}), or None when the run has no schedule record or its
    launches and sessions do not line up."""
    out = Path(out)
    try:
        launches = json.loads((out / "effort.json").read_text())["launches"]
    except (OSError, ValueError, KeyError):
        return None
    starts = _sessions(out)
    if not starts or len(starts) != len(launches):
        return None
    try:
        lines = (out / "events.jsonl").read_text(errors="replace").splitlines()
    except OSError:
        lines = []
    found: dict = {}
    for index, session in enumerate(starts):
        first = session["events_line"]
        last = starts[index + 1]["events_line"] if index + 1 < len(starts) else len(lines)
        cls = launches[index]["class"]
        g = found.setdefault(cls, {"sessions": 0, "seconds": 0.0, "model_calls": 0, "prompt_tokens": 0,
                                   "output_tokens": 0, "reasoning_tokens": 0})
        g["sessions"] += 1
        g["seconds"] += (session["end_t"] - session["t"]) if session["end_t"] else 0.0
        for line in lines[first:last]:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict) and event.get("type") == "usage" and isinstance(event.get("usage"), dict):
                use = event["usage"]
                g["model_calls"] += 1
                g["prompt_tokens"] += _int(use.get("input_tokens")) + _int(use.get("cache_read_input_tokens")) \
                    + _int(use.get("cache_creation_input_tokens"))
                g["output_tokens"] += _int(use.get("output_tokens"))
                g["reasoning_tokens"] += _int(use.get("reasoning_tokens"))
    for g in found.values():
        g["seconds"] = round(g["seconds"], 1)
        g["tokens"] = g["prompt_tokens"] + g["output_tokens"]
        calls = g["model_calls"]
        g["reasoning_per_call"] = round(g["reasoning_tokens"] / calls, 1) if calls else None
        g["output_per_call"] = round(g["output_tokens"] / calls, 1) if calls else None
    return found


def refusals(out: Path) -> dict:
    """Navigator refusals in the event stream, each once: {"total", "restart_induced", "other"} with the messages."""
    out = Path(out)
    starts = _sessions(out)
    try:
        lines = (out / "events.jsonl").read_text(errors="replace").splitlines()
    except OSError:
        lines = []
    found, previous = [], None
    for index, line in enumerate(lines):
        if NAVIGATOR not in line or "rawOutput" not in line:
            continue
        message = re.split(r'["\\]', line.split(NAVIGATOR, 1)[1], maxsplit=1)[0][:90]  # up to the JSON string's end or escape
        if previous is not None and index - previous[0] <= 1 and message[:40] == previous[1][:40]:
            previous = (index, message)  # the stream repeats a result on the next line
            continue
        previous = (index, message)
        session = None
        for row in starts:
            if row["events_line"] <= index:
                session = row
        induced = bool(session and session.get("reason") == "effort"
                       and any(message.startswith(p) for p in RESTART_REFUSALS))
        found.append({"line": index, "session": session["n"] if session else None, "restart_induced": induced,
                      "message": message})
    induced = [r for r in found if r["restart_induced"]]
    return {"total": len(found), "restart_induced": len(induced), "other": len(found) - len(induced),
            "restart_induced_messages": [r["message"][:60] for r in induced],
            "other_messages": [r["message"][:60] for r in found if not r["restart_induced"]]}


def tokens_file(pool_path: Path, out_path: Path, cls: str = "all") -> dict:
    """{artifact id: {input_tokens, output_tokens, seconds}} with every artifact carrying its run's totals, or with
    only the totals of class `cls` (M or I2; None where the run had no session of it)."""
    by_run, found = {}, {}
    for line in Path(pool_path).read_text().splitlines():
        if not line.strip():
            continue
        art = json.loads(line)
        run = art["source"]["run"]
        if run not in by_run:
            by_run[run] = totals(Path(run)) if cls == "all" else (class_totals(Path(run)) or {})
        t = by_run[run] if cls == "all" else by_run[run].get(cls)
        if t is None:  # no session of this class in the run: left out of the comparison, never zero
            found[art["id"]] = {"input_tokens": None, "output_tokens": None, "seconds": None}
        elif cls == "all":
            found[art["id"]] = {"input_tokens": t["prompt_tokens"], "output_tokens": t["output_tokens"],
                                "seconds": t["seconds"]}
        else:
            found[art["id"]] = {"input_tokens": t["prompt_tokens"], "output_tokens": t["output_tokens"],
                                "seconds": t["seconds"]}
    Path(out_path).write_text(json.dumps(found, indent=1) + "\n")
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("totals", "classes", "refusals"):
        sub.add_parser(name).add_argument("runs", nargs="+")
    t = sub.add_parser("tokens")
    t.add_argument("pool")
    t.add_argument("--out", required=True)
    t.add_argument("--class", dest="cls", choices=("all", "M", "I2"), default="all")
    args = ap.parse_args()
    if args.cmd in ("totals", "classes", "refusals"):
        fn = {"totals": totals, "classes": class_totals, "refusals": refusals}[args.cmd]
        for run in args.runs:
            print(json.dumps({"run": run, args.cmd: fn(Path(run))} if args.cmd != "totals" else fn(Path(run))))
    else:
        print(f"{len(tokens_file(Path(args.pool), Path(args.out), args.cls))} artifacts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
