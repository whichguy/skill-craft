#!/usr/bin/env python3
"""Rebuild the compact run folders in this directory from the saved runs under /Users/dadleet/e2e-runs.

Nothing reads those runs at test time; this script is how the committed extracts were made, so a reader can see what was kept
and re-derive them. Each folder keeps the SHAPE of a harness output folder (events.jsonl, timeline.jsonl, sessions.jsonl,
invocation*.json, and the ShipLoop run under .shiploop-runs/<work>/run with its state.md fence and timeline.json) and the REAL
line numbers and runner stamps of the saved run: lines that no reader looks at are empty lines, so ``events_line`` 4121 is line
4121 of the saved r3 run.

What is kept, per window the spec names (a fresh start or a compaction at line L): every event from the previous accepted
action's stamp to the accepting action's stamp plus MARGIN seconds, reduced to the keys the readers look at (tool calls, their
final results, session and compaction markers). For a compaction the part BEFORE the line is cut further to the file-edit calls
(`rewrote` compares only those), because a compaction comes late in a long stage. Dropped everywhere: thought and text chunks,
usage events, running updates, file contents, command output other than ShipLoop's own (a refusal line is what a reader needs).

sessions.jsonl is RECONSTRUCTED (the saved runs predate it): a start row per host launch with the `told` values parsed from
the resume prompt the run kept (`resume-*.txt` for Grok and Codex, the `-p` argument of invocation-resume-claude-*.json for
Claude), `t` from the invocation file's name, and no end rows.

    python3 test/fixtures/reorientation/extract.py            # all
    python3 test/fixtures/reorientation/extract.py r2         # the specs whose name starts with r2
"""

from __future__ import annotations

import bisect
import glob
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "shiploop_e2e"))
import metrics  # noqa: E402  (only its readers of a run's own files: timeline, history, acceptance stamps)

RUNS = Path("/Users/dadleet/e2e-runs")
MARGIN = 6.0  # seconds kept after the accepting action's stamp, so the calls that follow it are in the extract
NO_ACCEPT_SECONDS = 90.0  # how much of a window with no accepting action is kept
WRITE_TOOL = re.compile(r"write|edit|replace|create", re.I)
TOLD = re.compile(r'python3 "(?P<cli>[^"]+)" next --run-dir "(?P<run_dir>[^"]+)"')

SPECS = [
    {"name": "r3-battleship-grok-none", "run": "20261008/r3-battleship-grok-none",
     "windows": [{"line": 4121, "before": "all"}, {"line": 1536, "before": "writes"}, {"line": 8341, "before": "writes"}],
     "sessions": [("first", "start", 0, "invocation.json"),
                  ("fresh", "resume-run", 4121, "invocation-resume-grok-1791528536.json")]},
    {"name": "r2-battleship-grok-none", "run": "20261008/r2-battleship-grok-none",
     "windows": [{"line": 2704, "before": "all"}],
     "sessions": [("first", "start", 0, "invocation.json"),
                  ("fresh", "resume-run", 2704, "invocation-resume-claude-1791508003.json")]},
    # The four fresh sessions of the Luna xhigh run: only the start of each, to the first `next` that worked and a few events.
    {"name": "v1210-battleship-luna-xhigh", "run": "20261005/v1210-battleship-luna-xhigh",
     "slices": [(588, 600), (1206, 1222), (2126, 2140), (2627, 2640)],
     "sessions": [("first", "start", 0, "invocation.json"),
                  ("fresh", "resume-run", 588, "invocation-resume-codex-1791182671.json"),
                  ("fresh", "resume-run", 1206, "invocation-resume-codex-1791189879.json"),
                  ("fresh", "resume-run", 2126, "invocation-resume-codex-1791197087.json"),
                  ("fresh", "resume-run", 2627, "invocation-resume-codex-1791204298.json")]},
]


def text_of(value, limit: int) -> str:
    return value[:limit] if isinstance(value, str) else ""


def reduce_event(event: dict, shiploop_calls: set, write_only: bool = False):
    """The event cut to what the readers look at, or None when no reader looks at it."""
    kind = event.get("type")
    if kind == "system" and event.get("subtype") == "init":
        return {"type": "system", "subtype": "init", "claude_code_version": event.get("claude_code_version"),
                "session_id": event.get("session_id")}
    if kind == "assistant":
        blocks = [{"type": "tool_use", "id": b.get("id"), "name": b.get("name"), "input": reduce_input(b.get("input"))}
                  for b in (event.get("message") or {}).get("content") or []
                  if isinstance(b, dict) and b.get("type") == "tool_use"]
        if write_only:
            blocks = [b for b in blocks if WRITE_TOOL.search(b["name"] or "")]
        for b in blocks:
            if "shiploop" in json.dumps(b["input"]).lower():
                shiploop_calls.add(b["id"])
        return {"type": "assistant", "message": {"id": (event.get("message") or {}).get("id"), "content": blocks}} if blocks else None
    if write_only:
        return None
    if kind == "user":
        blocks = []
        for b in (event.get("message") or {}).get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_result":
                content = b.get("content")
                if isinstance(content, list):
                    content = "".join(str(p.get("text") or "") for p in content if isinstance(p, dict))
                blocks.append({"type": "tool_result", "tool_use_id": b.get("tool_use_id"),
                               "content": text_of(content, 600 if b.get("tool_use_id") in shiploop_calls else 40)})
        return {"type": "user", "message": {"content": blocks}} if blocks else None
    if kind == "tool_call":
        arg = reduce_input(event.get("rawInput"))
        if "shiploop" in json.dumps(arg).lower():
            shiploop_calls.add(event.get("toolCallId"))
        return {"type": "tool_call", "toolCallId": event.get("toolCallId"), "toolName": event.get("toolName") or event.get("title"),
                "rawInput": arg}
    if kind == "tool_call_update":
        if event.get("status") == "in_progress" or not isinstance(event.get("rawOutput"), dict):
            cancelled = event.get("status") == "failed" and "cancelled" in json.dumps(event.get("content") or "").lower()
            if not cancelled:
                return None
        raw = event.get("rawOutput") if isinstance(event.get("rawOutput"), dict) else None
        shown = metrics.visible(raw) if raw else ""
        keep = event.get("toolCallId") in shiploop_calls
        if not raw and not keep:
            shown = ""
        out = {"type": "tool_call_update", "toolCallId": event.get("toolCallId"), "status": event.get("status")}
        if raw is not None:
            out["rawOutput"] = {"exit_code": raw.get("exit_code"), "output_for_prompt": text_of(shown, 600 if keep else 0)}
        else:
            out["rawOutput"] = None
        if event.get("status") == "failed" and "cancelled" in json.dumps(event.get("content") or "").lower():
            out["content"] = event["content"]
        if raw is None and isinstance(event.get("content"), list) and event.get("status") in ("completed", "failed"):
            out["content"] = [{"type": "content", "content": {"type": "text", "text": text_of(
                (event["content"][0].get("content") or {}).get("text") if event["content"] and isinstance(event["content"][0], dict)
                else "", 600 if keep else 0)}}]
        return out
    if kind in ("available_commands",):
        return {"type": kind, "commands": [], "sessionId": event.get("sessionId")}
    if kind in ("auto_compact_started", "auto_compact_completed", "end", "result"):
        return {k: v for k, v in event.items() if k in ("type", "percentage", "stopReason", "subtype", "is_error", "num_turns",
                                                        "total_cost_usd", "sessionId", "session_id")}
    return None


def reduce_input(arg) -> dict:
    arg = arg if isinstance(arg, dict) else {}
    out = {k: arg[k] for k in ("command", "target_file", "file_path", "path", "question", "offset", "limit") if k in arg}
    command = out.get("command")
    if isinstance(command, str) and len(command) > 4000:
        out["command"] = command[:1500] + "\n...[cut by extract.py]...\n" + command[-1500:]
    return out


def read_lines(path: Path) -> list[str]:
    return path.read_text(errors="replace").splitlines()


def window_bounds(line: int, stamps: dict, accepted: list[dict]) -> tuple[float, float, int]:
    """(low stamp, high stamp, index of the accepting row): the previous accept to the accepting action plus the margin."""
    t = stamps[line]
    index = next((i for i, row in enumerate(accepted) if row["t"] is not None and row["t"] >= int(t)), None)
    if index is None:  # no action was accepted after this line: keep a stretch of it (a window the readers must call unmeasured)
        return accepted[-1]["t"], t + NO_ACCEPT_SECONDS, len(accepted)
    low = accepted[index - 1]["t"] if index else 0.0
    return low, accepted[index]["t"] + MARGIN, index


def build(spec: dict) -> None:
    source = RUNS / spec["run"]
    target = HERE / spec["name"]
    events = read_lines(source / "events.jsonl")
    stamps = metrics.timeline(source / "timeline.jsonl")
    run_dir = Path(glob.glob(str(source / ".shiploop-runs" / "*" / "run"))[0])
    accepted = metrics.stage_results(run_dir)
    ordered = sorted(stamps)
    times = [stamps[n] for n in ordered]
    keep: dict[int, str] = {}  # line -> "all" | "writes"
    for window in spec.get("windows", []):
        line = window["line"]
        low, high, _ = window_bounds(line, stamps, accepted)
        first = ordered[bisect.bisect_right(times, low)]
        last = ordered[min(bisect.bisect_right(times, high), len(ordered) - 1)]
        for n in range(first, last + 1):
            mode = "all" if n >= line or window["before"] == "all" else "writes"
            if keep.get(n) != "all":
                keep[n] = mode
    for first, last in spec.get("slices", []):
        for n in range(first, last):
            keep[n] = "all"
    shiploop_calls: set = set()
    kept: dict[int, dict] = {}
    for n in sorted(keep):
        try:
            event = json.loads(events[n])
        except ValueError:
            continue
        reduced = reduce_event(event, shiploop_calls, write_only=keep[n] == "writes") if isinstance(event, dict) else None
        if reduced is not None:
            kept[n] = reduced
    target.mkdir(parents=True, exist_ok=True)
    (target / "events.jsonl").write_text("\n".join(json.dumps(kept[n]) if n in kept else "" for n in range(len(events))) + "\n")
    (target / "timeline.jsonl").write_text("".join(
        json.dumps({"line": n, "t": stamps[n]}) + "\n" for n in sorted(kept) if n in stamps))
    # The ShipLoop run: its state.md fence and timeline.json, reduced to the keys the readers look at.
    state = metrics.engine_state(run_dir)
    keys = ("status", "stage", "revision", "planning_review", "history", "inner_loops", "work_items", "work_index")
    folder = target / ".shiploop-runs" / "work-fixture" / "run"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "state.md").write_text("# state\n\n```shiploop-state\n"
                                     + json.dumps({k: state[k] for k in keys if k in state}, indent=1) + "\n```\n")
    (folder / "timeline.json").write_text((run_dir / "timeline.json").read_text())
    # Launch records and the reconstructed sessions.jsonl.
    rows = []
    for kind, reason, line, name in spec["sessions"]:
        record = json.loads((source / name).read_text())
        stamp = int(re.search(r"-(\d+)\.json$", name).group(1)) if name != "invocation.json" else None
        told = None
        if kind != "first":
            if record["host"] == "claude":
                prompt = record["argv"][record["argv"].index("-p") + 1]
            else:
                prompt = (source / name.replace("invocation-", "").replace(".json", ".txt")).read_text()
            found = TOLD.search(prompt)
            told = {"cli": found.group("cli"), "run_dir": found.group("run_dir")} if found else None
        (target / name).write_text(json.dumps({k: record.get(k) for k in ("case", "host", "model", "versions")}, indent=1) + "\n")
        rows.append({"row": "start", "n": len(rows) + 1, "kind": kind, "reason": reason, "host": record["host"],
                     "model": record.get("model"), "t": float(stamp) if stamp else stamps.get(line),
                     "events_line": line, "told": told, "resumed_session": None, "reconstructed": True})
    (target / "sessions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"{spec['name']}: {len(kept)} events kept of {len(events)} lines, "
          f"{sum(p.stat().st_size for p in target.rglob('*') if p.is_file())} bytes")


def main() -> None:
    wanted = sys.argv[1:]
    for spec in SPECS:
        if not wanted or any(spec["name"].startswith(w) for w in wanted):
            build(spec)


if __name__ == "__main__":
    main()
