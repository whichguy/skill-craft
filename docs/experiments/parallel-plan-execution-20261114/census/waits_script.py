#!/usr/bin/env python3
"""waits_script.py (journal E15, exploratory, not registered): what the 'script' class of waits.py is made of.

waits.py found that the model waits on ShipLoop's own commands for 18.6% of the pooled step time. This splits that class by the ShipLoop verb
the command names, compares the tool-call durations with the script's own elapsed time (`ms`, trace.jsonl) over the same windows, and splits it by host.

Second part: the test stage's own runs. ShipLoop's `check` at the test stage runs a base check, a candidate run and a mutation check itself
(skills/shiploop/scripts/shiploop_test_loop.py); their recorded command seconds are summed from tests/*-base[N].md, *-verify[N].md and
*-mutation[N].md (one file per attempt, the *-check.md copies not counted) and compared with the script's own elapsed seconds for those calls,
and with what running the three at once would save (their sum minus their longest, per action).

  python3 -I waits_script.py          prints the breakdown; writes evidence/waits-script.txt
"""

from __future__ import annotations

import collections
import json
import pathlib
import re
import datetime
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import census  # noqa: E402
import waits  # noqa: E402

VERB = re.compile(r"shiploop(?:\.py)?[\"']?\s+(?:--[\w-]+(?:=\S+|\s+\S+)?\s+)*([a-z][a-z-]*)")


def verb_of(text: str) -> str:
    match = VERB.search(text)
    return match.group(1) if match else "(other)"


def record_seconds(path: pathlib.Path):
    """(created_at epoch, seconds summed over the record's `seconds` fields) or None."""
    try:
        record = json.loads(path.read_text(errors="replace").split("```shiploop-state", 1)[1].split("```", 1)[0])
        made = datetime.datetime.fromisoformat(record["created_at"].replace("Z", "+00:00")).timestamp()
    except (IndexError, KeyError, ValueError, OSError):
        return None
    def walk(node):
        if isinstance(node, dict):
            return sum((v if k == "seconds" and isinstance(v, (int, float)) else walk(v)) for k, v in node.items())
        if isinstance(node, list):
            return sum(walk(v) for v in node)
        return 0
    return made, float(walk(record)), record.get("action")


def main() -> int:
    rows = [r for r in json.load(open(HERE / "evidence" / "census.json"))["plans"] if r.get("durations_s")]
    by_verb = collections.defaultdict(list)        # verb -> [seconds]
    by_host = collections.defaultdict(lambda: [0.0, 0.0, 0.0])    # host -> [script seconds, trace ms seconds, window seconds]
    trace_ms = collections.defaultdict(float)      # verb -> seconds the script itself reported
    per_call, windows_n = [], 0
    kinds = collections.defaultdict(float)
    by_action = collections.defaultdict(lambda: collections.defaultdict(float))
    check_test_s, window_total = 0.0, 0.0
    for row in rows:
        run = pathlib.Path(row["run"])
        trace = census.load_trace(run)
        wins, _ = census.windows(trace, row["action"], row["workitem"], row["n"]) if trace else ([], None)
        case = waits.case_root(run)
        if len(wins) != row["n"] or case is None:
            continue
        flow = json.load(open(case / "flow.json"))
        calls, _ = waits.intervals(case)
        for start, end in wins:
            windows_n += 1
            window_total += end - start
            host = flow.get("host")
            for pattern, kind in (("*-base[0-9]*.md", "base"), ("*-verify[0-9]*.md", "candidate"), ("*-mutation[0-9]*.md", "mutation")):
                for path in (run / "tests").glob(pattern):
                    found = record_seconds(path)
                    if found and start - 2 <= found[0] <= end + 2:
                        kinds[kind] += found[1]
                        by_action[(str(run), found[2])][kind] += found[1]
            host = flow.get("host")
            by_host[host][2] += end - start
            for call_start, call_end, tool, text in calls:
                overlap = min(call_end, end) - max(call_start, start)
                if overlap > 0 and waits.classify(tool, text) == "script":
                    by_verb[verb_of(text)].append(overlap)
                    by_host[host][0] += overlap
                    per_call.append(overlap)
            for r in trace:
                if r.get("kind") == "command" and start <= (r.get("ts") or 0) <= end and (r.get("ms") or 0) >= 0:
                    trace_ms[r.get("verb") or "?"] += (r.get("ms") or 0) / 1000
                    stage = r.get("stage")
                    if r.get("verb") == "check" and isinstance(stage, list) and len(stage) > 1 and stage[1] == "test":
                        check_test_s += (r.get("ms") or 0) / 1000
                    by_host[host][1] += (r.get("ms") or 0) / 1000
    lines = []
    emit = lambda text="": (print(text), lines.append(text))
    total = sum(sum(v) for v in by_verb.values())
    emit(f"windows {windows_n}; script-class calls {len(per_call):,}, {total:,.0f} s; per call mean {statistics.mean(per_call):.1f} s, median {statistics.median(per_call):.1f} s, p90 {sorted(per_call)[int(0.9 * (len(per_call) - 1))]:.1f} s, max {max(per_call):.0f} s")
    emit(f"the script's own elapsed time (trace.jsonl ms, every command row in those windows): {sum(trace_ms.values()):,.0f} s")
    emit()
    emit("by ShipLoop verb named in the command (tool-call seconds; calls; mean s; the script's own seconds for the same verb)")
    for verb, secs in sorted(by_verb.items(), key=lambda kv: -sum(kv[1]))[:14]:
        emit(f"  {verb:16s} {sum(secs):9,.0f} s  {len(secs):6,d} calls  mean {statistics.mean(secs):6.1f} s   script {trace_ms.get(verb, 0):8,.0f} s")
    emit()
    emit("by host (script-class seconds / window seconds; the script's own seconds / window seconds)")
    for host, (script_s, ms_s, window_s) in sorted(by_host.items()):
        emit(f"  {host:7s} {script_s / window_s:6.1%}   script's own {ms_s / window_s:6.2%}")
    emit()
    recorded = sum(kinds.values())
    emit(f"the test stage's own runs (recorded command seconds, summed over the windows): base {kinds['base']:,.0f} s, candidate {kinds['candidate']:,.0f} s, mutation {kinds['mutation']:,.0f} s, together {recorded:,.0f} s = {recorded / window_total:.2%} of the window time")
    emit(f"the script's own elapsed time for `check` at the test stage: {check_test_s:,.0f} s = {check_test_s / window_total:.2%} of the window time; so the recorded commands are {recorded / check_test_s:.0%} of it and the rest, {check_test_s - recorded:,.0f} s ({(check_test_s - recorded) / window_total:.2%} of the window time), is ShipLoop's own work around them")
    bound = sum(sum(v.values()) - max(v.values()) for v in by_action.values() if len(v) > 1)
    emit(f"running the base, candidate and mutation runs at once would save at most {bound:,.0f} s of command time ({bound / window_total:.2%} of the window time), over {sum(1 for v in by_action.values() if len(v) > 1)} actions that have more than one kind of run")
    (HERE / "evidence" / "waits-script.txt").write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
