#!/usr/bin/env python3
"""waits.py (journal E15, README Amendment A13): how much of a recorded ShipLoop step is waiting that one context could overlap?

Offline and read-only. For each timed step window of the census (evidence/census.json rows with `durations_s`, windows recomputed
with census.windows from the run's trace.jsonl) it reads the case folder's flow.json and timeline.jsonl, pairs every `call` event
with the next unmatched `result` event in time order (first in, first out), and adds each call's duration, clipped to the window,
to its class. The classes and the predictions are the ones A13 fixed before any result was computed.

  python3 -I waits.py             prints the summary and the predictions; writes evidence/waits.txt and evidence/waits.json

Classes of a call: verify (a shell tool whose command matches VERIFY and does not contain "shiploop"), script (a shell tool whose command
contains "shiploop"), inspect (any other shell command), file (Read, Write, Edit and the other hosts' file tools), other (search, skills,
delegation, everything else). The model's own time is the window minus all tool-call time. Cross-check: the sum of runs[].seconds of the
tests/*-verify*.md records created inside the window.
"""

from __future__ import annotations

import collections
import datetime
import json
import pathlib
import re
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import census  # noqa: E402

SHELL = {"Bash", "run_terminal_command", "shell", "exec_command", "local_shell"}
FILE_TOOLS = {"Read", "Write", "Edit", "MultiEdit", "NotebookEdit", "read_file", "write", "search_replace", "list_dir", "Grep", "grep", "Glob"}
VERIFY = re.compile(r"\b(test|tests|pytest|jest|vitest|mocha|unittest|lint|eslint|ruff|tsc|mypy|build|compile|install|check)\b"
                    r"|npm (run|test|ci|install)|node --test|go (test|build|vet)|cargo |\bmvn\b|\bgradle\b|\bmake\b|\bsf |sfdx|apex", re.I)
SALESFORCE = re.compile(r"\bsf |sfdx|apex", re.I)


def case_root(run: pathlib.Path):
    for path in [run, *run.parents][:7]:
        if (path / "flow.json").is_file() and (path / "timeline.jsonl").is_file():
            return path
    return None


def intervals(flow: dict, origin: float) -> list:
    """[(start_epoch, end_epoch, tool, text)] with calls and results paired first in, first out."""
    events = []
    for action in flow.get("actions", []):
        for phase in action.get("phases", []):
            for event in phase.get("events") or []:
                if event.get("kind") in ("call", "result") and isinstance(event.get("t"), (int, float)):
                    events.append(event)
    events.sort(key=lambda event: event["t"])
    pending, out = collections.deque(), []
    for event in events:
        if event["kind"] == "call":
            pending.append(event)
        elif pending:
            call = pending.popleft()
            out.append((origin + call["t"], origin + event["t"], call.get("tool") or "", (call.get("body") or {}).get("text") or ""))
    return out


def classify(tool: str, text: str) -> str:
    if tool in SHELL:
        if "shiploop" in text:
            return "script"
        return "verify" if VERIFY.search(text) else "inspect"
    return "file" if tool in FILE_TOOLS else "other"


def verify_record_seconds(run: pathlib.Path, start: float, end: float) -> float:
    total = 0.0
    for path in sorted((run / "tests").glob("*-verify*.md")):
        try:
            text = path.read_text(errors="replace")
            block = text.split("```shiploop-state", 1)[1].split("```", 1)[0]
            record = json.loads(block)
            made = datetime.datetime.fromisoformat(record["created_at"].replace("Z", "+00:00")).timestamp()
        except (IndexError, KeyError, ValueError, OSError):
            continue
        if start - 2 <= made <= end + 2:
            total += sum(float(r.get("seconds") or 0) for r in record.get("runs") or [])
    return total


def main() -> int:
    rows = [r for r in json.load(open(HERE / "evidence" / "census.json"))["plans"] if r.get("durations_s")]
    out_rows, skipped = [], collections.Counter()
    drift = []
    for row in rows:
        run = pathlib.Path(row["run"])
        trace = census.load_trace(run)
        wins, _ = census.windows(trace, row["action"], row["workitem"], row["n"]) if trace else ([], None)
        if len(wins) != row["n"]:
            skipped["windows differ from the census"] += 1
            continue
        case = case_root(run)
        if case is None:
            skipped["no flow.json and timeline.jsonl beside the run"] += 1
            continue
        try:
            flow = json.load(open(case / "flow.json"))
            timeline = [json.loads(line) for line in open(case / "timeline.jsonl") if line.strip()]
        except (OSError, ValueError):
            skipped["flow or timeline unreadable"] += 1
            continue
        origin = timeline[0]["t"]
        for action in flow.get("actions", [])[:3]:      # self-check of the time origin on events that carry a line number
            for phase in action.get("phases", []):
                for event in (phase.get("events") or [])[:20]:
                    line = event.get("line")
                    if isinstance(line, int) and line < len(timeline) and isinstance(event.get("t"), (int, float)):
                        drift.append(abs(origin + event["t"] - timeline[line]["t"]))
        calls = intervals(flow, origin)
        for index, (start, end) in enumerate(wins):
            seconds = collections.defaultdict(float)
            verify_calls = []
            salesforce = False
            for call_start, call_end, tool, text in calls:
                overlap = min(call_end, end) - max(call_start, start)
                if overlap <= 0:
                    continue
                kind = classify(tool, text)
                seconds[kind] += overlap
                if kind == "verify":
                    verify_calls.append(overlap)
                    salesforce = salesforce or bool(SALESFORCE.search(text))
            window = end - start
            out_rows.append({"action": row["action"], "step": index + 1, "family": row["family"], "host": flow.get("host"), "window_s": round(window, 1),
                             "verify_s": round(seconds["verify"], 1), "script_s": round(seconds["script"], 1), "inspect_s": round(seconds["inspect"], 1),
                             "file_s": round(seconds["file"], 1), "other_s": round(seconds["other"], 1), "verify_calls": len(verify_calls),
                             "overlap_bound_s": round(sum(verify_calls) - max(verify_calls), 1) if len(verify_calls) > 1 else 0.0,
                             "record_s": round(verify_record_seconds(run, start, end), 1), "salesforce": salesforce})
    W = sum(r["window_s"] for r in out_rows)
    tool_s = lambda r: r["verify_s"] + r["script_s"] + r["inspect_s"] + r["file_s"] + r["other_s"]
    lines = []
    emit = lambda text="": (print(text), lines.append(text))
    emit(f"timed census rows {len(rows)}; step windows measured {len(out_rows)} in {len({r['action'] for r in out_rows})} plans; skipped plans {dict(skipped)}")
    emit(f"time origin check on events with a line number: n {len(drift)}, median |epoch0 + t - timeline[line]| {statistics.median(drift):.3f} s, max {max(drift):.2f} s" if drift else "time origin check: no event carried a line number")
    emit(f"hosts {dict(collections.Counter(r['host'] for r in out_rows))}; windows {W:,.0f} s in total, median {statistics.median(r['window_s'] for r in out_rows):.0f} s")
    emit()
    emit("pooled share of the window time, by class (and the model's own time)")
    for key in ("verify_s", "script_s", "inspect_s", "file_s", "other_s"):
        emit(f"  {key[:-2]:8s} {sum(r[key] for r in out_rows):9.0f} s  {sum(r[key] for r in out_rows) / W:6.1%}")
    emit(f"  {'model':8s} {W - sum(tool_s(r) for r in out_rows):9.0f} s  {1 - sum(tool_s(r) for r in out_rows) / W:6.1%}   (window minus all tool-call time)")
    emit(f"  cross-check, script-run verify records inside the windows: {sum(r['record_s'] for r in out_rows):.0f} s = {sum(r['record_s'] for r in out_rows) / W:.2%}")
    share = [r["verify_s"] / r["window_s"] for r in out_rows if r["window_s"] > 0]
    emit()
    emit(f"per window verify share: median {statistics.median(share):.1%}, p90 {sorted(share)[int(0.9 * (len(share) - 1))]:.1%}, max {max(share):.1%}")
    secs = sorted(r["verify_s"] for r in out_rows)
    emit(f"per window verify seconds: median {statistics.median(secs):.1f}, p90 {secs[int(0.9 * (len(secs) - 1))]:.1f}, p99 {secs[int(0.99 * (len(secs) - 1))]:.1f}, max {secs[-1]:.1f}; windows with at least 30 s: {sum(s >= 30 for s in secs)} of {len(secs)}, with at least 60 s: {sum(s >= 60 for s in secs)}")
    bound = sum(r["overlap_bound_s"] for r in out_rows)
    emit(f"overlap upper bound (verify-class seconds minus the longest, per window): {bound:.0f} s = {bound / W:.2%} of the pooled window time; windows with two or more verify calls: {sum(r['verify_calls'] > 1 for r in out_rows)}")
    by_family = collections.defaultdict(lambda: [0.0, 0.0])
    for r in out_rows:
        by_family[r["family"]][0] += r["verify_s"]
        by_family[r["family"]][1] += r["window_s"]
    fam = [v / w for v, w in by_family.values() if w]
    emit(f"family-weighted verify share (each of {len(fam)} families once): mean {statistics.mean(fam):.1%}, median {statistics.median(fam):.1%}")
    for host in sorted({r["host"] for r in out_rows}):
        sub = [r for r in out_rows if r["host"] == host]
        w = sum(r["window_s"] for r in sub)
        emit(f"  host {host:7s} windows {len(sub):4d}, verify {sum(r['verify_s'] for r in sub) / w:6.1%}, model {1 - sum(tool_s(r) for r in sub) / w:6.1%}")
    sf = [r for r in out_rows if r["salesforce"]]
    rest = [r for r in out_rows if not r["salesforce"]]
    sf_share = sum(r["verify_s"] for r in sf) / sum(r["window_s"] for r in sf) if sf else None
    rest_share = sum(r["verify_s"] for r in rest) / sum(r["window_s"] for r in rest)
    emit(f"windows naming sf, sfdx or apex: {len(sf)}" + (f", pooled verify share {sf_share:.1%} against {rest_share:.1%} for the others" if sf else ""))
    emit()
    emit("predictions as registered (A13)")
    emit(f"  P64 pooled verify share under 10%: {sum(r['verify_s'] for r in out_rows) / W < 0.10}  ({sum(r['verify_s'] for r in out_rows) / W:.2%})")
    emit(f"  P65 median window verify share under 5%: {statistics.median(share) < 0.05}  ({statistics.median(share):.2%})")
    emit(f"  P66 at least 90% of windows under 30 s of verify time: {sum(s < 30 for s in secs) / len(secs) >= 0.9}  ({sum(s < 30 for s in secs) / len(secs):.1%})")
    emit(f"  P67 model time over 60% of the pooled window time: {1 - sum(tool_s(r) for r in out_rows) / W > 0.6}  ({1 - sum(tool_s(r) for r in out_rows) / W:.1%})")
    if len(sf) >= 10:
        emit(f"  P68 sf windows at least 3 times the others: {sf_share >= 3 * rest_share}  ({sf_share:.2%} against {rest_share:.2%})")
    else:
        emit(f"  P68 too few windows naming sf, sfdx or apex ({len(sf)} of the 10 needed)")
    emit(f"  P69 overlap upper bound under 3%: {bound / W < 0.03}  ({bound / W:.2%})")
    (HERE / "evidence" / "waits.txt").write_text("\n".join(lines) + "\n")
    (HERE / "evidence" / "waits.json").write_text(json.dumps(out_rows, indent=0) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
