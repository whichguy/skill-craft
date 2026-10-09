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
(`rewrote` compares only those), because a compaction comes late in a long stage. Dropped everywhere: thought and text chunks, file contents, command output other than ShipLoop's own (a refusal line is what a reader needs).

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
     "windows": [{"line": 1900, "before": "writes"}, {"line": 2704, "before": "all"}],
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
    """The event cut to what the readers look at, or None when no reader looks at it. The calls an event starts and whether an
    update is Grok's permission refusal are read by the harness's own readers (metrics.tool_call_events, cancelled_update), so
    the fixtures are built by the code the tests then run."""
    kind = event.get("type")
    calls = [(call_id, tool, reduce_input(arg)) for call_id, tool, arg in metrics.tool_call_events(event)]
    for call_id, _tool, arg in calls:
        if "shiploop" in json.dumps(arg).lower():
            shiploop_calls.add(call_id)
    if kind == "system" and event.get("subtype") == "init":
        return {"type": "system", "subtype": "init", "claude_code_version": event.get("claude_code_version"),
                "session_id": event.get("session_id")}
    if write_only:  # the part of a compaction's stage before it: only the file-edit calls matter to `rewrote`
        calls = [c for c in calls if WRITE_TOOL.search(c[1] or "")]
        if kind == "assistant":
            return {"type": "assistant", "message": {"id": (event.get("message") or {}).get("id"), "content": [
                {"type": "tool_use", "id": i, "name": n, "input": a} for i, n, a in calls]}} if calls else None
        return {"type": "tool_call", "toolCallId": calls[0][0], "toolName": calls[0][1], "rawInput": calls[0][2]} \
            if kind == "tool_call" and calls else None
    if kind == "assistant":
        return {"type": "assistant", "message": {"id": (event.get("message") or {}).get("id"), "content": [
            {"type": "tool_use", "id": i, "name": n, "input": a} for i, n, a in calls]}} if calls else None
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
    if kind == "tool_call" and calls:
        return {"type": "tool_call", "toolCallId": calls[0][0], "toolName": calls[0][1], "rawInput": calls[0][2]}
    if kind == "tool_call_update":
        raw = event.get("rawOutput") if isinstance(event.get("rawOutput"), dict) else None
        refused = metrics.cancelled_update(event)
        if raw is None and not refused:
            return None
        keep = event.get("toolCallId") in shiploop_calls
        out = {"type": "tool_call_update", "toolCallId": event.get("toolCallId"), "status": event.get("status")}
        # A running update (status in_progress, a placeholder exit 0) is kept, with no output: it is the shape ToolLog.feed
        # must not read as a result.
        out["rawOutput"] = None if raw is None else {
            "exit_code": raw.get("exit_code"), "output_for_prompt": text_of(metrics.visible(raw), 600 if keep else 0)}
        if refused:
            out["content"] = event["content"]
        return out
    if kind == "usage":  # Grok's one event per model call: it is also how a stream is known to be Grok's, so compactions count
        used = event.get("usage") if isinstance(event.get("usage"), dict) else {}
        return {"type": "usage", "usage": {k: v for k, v in used.items() if isinstance(v, int)}}
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
    kept_state = {k: state[k] for k in keys if k in state}
    # A history row keeps what the readers join on (stage, outcome, work item, action id), not its summary text.
    kept_state["history"] = [{k: row.get(k) for k in ("stage", "outcome", "workitem", "action")}
                             for row in state.get("history", []) if isinstance(row, dict)]
    (folder / "state.md").write_text("# state\n\n```shiploop-state\n" + json.dumps(kept_state, indent=1) + "\n```\n")
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
