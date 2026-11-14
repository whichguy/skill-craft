#!/usr/bin/env python3
"""Score the registered close-out measures (M1-M4) for one or more stage-suite live results roots.

    python3 closeout_score.py B=<root> T=<root> [--json OUT]

Per sample (``<root>/<stage>/<scenario>/<n>/``) it reads ``stage-result.json`` (M1, the suite's own ``pass``), the run's
``trace.jsonl`` rows for the seeded action (``check`` and ``complete`` with their exit codes and times), and the host's
``events.jsonl`` with ``timeline.jsonl`` (each tool call's start and finish). A trace row belongs to the tool call
whose start-to-finish window holds its time.

- M2: tool calls after the call that ran the last ``check`` yes, up to and including the call that ran the accepted
  ``complete`` (0 when one call ran both).
- M3: seconds from that ``check`` yes to the accepted ``complete``.
- M4: tool calls and seconds from the first session's start to the accepted ``complete``.

M2 and M3 are for samples accepted with outcome done; a done sample with no ``check`` yes before acceptance is counted
as "no check". No model judges anything here.

Two matchings of trace rows to tool calls are reported, side by side:

- **window** (the registered one): a row belongs to the call whose window, widened by SLACK, holds its time. Adjacent
  calls overlap by the slack, so a zero-duration call (a file write) directly before a command can take that
  command's row: M2 is then too high by one. Kept as run; fields ``m2``, ``m3``, ``fused``.
- **text** (added after the first scoring, as its own line): each ``shiploop check``, loop ``done`` and ``shiploop
  complete`` is recognised in the command text of the call that runs it, and the trace rows are walked in order against
  those calls. A call whose chain stops at a refused check runs nothing after it (a chain joined with ``&&``). When the
  rows and the recognised invocations disagree, the sample is marked ``unmatched`` and its text fields are empty.
  Fields ``m2_text``, ``m3_text``, ``fused_text``, ``co_calls`` and ``co_seconds``. The last two are the close-out
  span: from the first close-out command of the final attempt (after the last refusal) to the accepted ``complete``,
  counted in tool calls and seconds. They compare the arms even where a sample never ran ``check``.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

SLACK = 0.5  # seconds: a trace row is written while its command runs, inside the tool call's window


def _jsonl(path: Path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            rows.append(None)
    return rows


def tool_calls(sample: Path):
    """[(start, end, command)] for each host tool call, in order."""
    events = _jsonl(sample / "events.jsonl")
    times = {}
    for row in _jsonl(sample / "timeline.jsonl"):
        if row:
            times[row["line"]] = row["t"]
    open_calls, calls = {}, []
    for index, row in enumerate(events):
        if not row or index not in times:
            continue
        if row.get("type") == "tool_call":
            raw = row.get("rawInput")
            command = raw.get("command") if isinstance(raw, dict) else None
            open_calls[row["toolCallId"]] = (times[index], command if isinstance(command, str) else json.dumps(raw))
        elif row.get("type") == "tool_call_update" and row.get("status") in ("completed", "failed"):
            started = open_calls.pop(row.get("toolCallId"), None)
            if started:
                calls.append((started[0], times[index], started[1]))
    calls.sort()
    return calls


import re

_RUN = r"/shiploop['\"]?\s+"
INVOCATION = re.compile(r"(?P<check>" + _RUN + r"check\s+--run-dir)|(?P<complete>" + _RUN + r"complete\s+--run-dir)"
                        r"|(?P<done>until_loop_ephemeral\.py['\"]?\s+done\s+--state)")


def invocations(command):
    """The close-out verbs a call's command text runs, in order of appearance.

    A loop ``done`` that a model runs through a Python wrapper (it reads ``done_argv`` from the receipt and runs it with
    ``subprocess``, writing the report in the same script) has no ``until_loop_ephemeral.py done`` text; it is
    recognised by ``exit_assessment`` and ``subprocess`` in the command and placed where the wrapper starts."""
    found = [(m.start(), next(k for k, v in m.groupdict().items() if v)) for m in INVOCATION.finditer(command or "")]
    if "exit_assessment" in (command or "") and "subprocess" in (command or "") and not any(
            verb == "done" for _, verb in found):
        found.append((command.find("exit_assessment"), "done"))
    return [verb for _, verb in sorted(found)]


def text_match(calls, trace, accepted):
    """Walk the calls against the trace's check and complete rows: [(call index, verb, exit or None)], or None."""
    checks = [r for r in trace if r["verb"] == "check"]
    completes = [r for r in trace if r["verb"] == "complete"]
    ci = ki = 0
    events = []
    for index, (_, _, command) in enumerate(calls):
        for verb in invocations(command):
            if verb == "done":
                events.append((index, "done", None))
            elif verb == "check":
                if ci >= len(checks):
                    return None
                events.append((index, "check", checks[ci]))
                ci += 1
                if checks[ci - 1].get("exit") != 0:
                    break  # the chain stops at a refused check
            else:
                if ki >= len(completes):
                    return None
                events.append((index, "complete", completes[ki]))
                ki += 1
                if completes[ki - 1].get("exit") != 0:
                    break
    return events if ci == len(checks) and ki == len(completes) else None


def call_index(calls, t):
    for index, (start, end, _) in enumerate(calls):
        if start - SLACK <= t <= end + SLACK:
            return index
    return None


def score_sample(sample: Path) -> dict:
    result = json.loads((sample / "stage-result.json").read_text())
    action = result.get("action_id") or (result.get("seeded") or {}).get("action")
    run_dir = Path((result.get("seeded") or {}).get("run_dir") or sample / ".shiploop-runs/seed/run")
    sessions = [r for r in _jsonl(sample / "sessions.jsonl") if r and r.get("row") == "start"]
    start = sessions[0]["t"] if sessions else None
    trace = [r for r in _jsonl(run_dir / "trace.jsonl")
             if r and r.get("kind") == "command" and r.get("action") == action and (start is None or r["ts"] >= start)]
    accepted = next((r for r in trace if r["verb"] == "complete" and r.get("exit") == 0), None)
    # A stage that parks at its Improve review records no accepted list on the complete row; the suite's own
    # stage-result outcome is the producer's accepted outcome then.
    outcome = (((accepted.get("accepted") or [{}])[0].get("outcome") or result.get("outcome"))
               if accepted else None)
    row = {"sample": str(sample), "pass": bool(result.get("pass")), "verdicts": result.get("verdicts"),
           "outcome": outcome, "checks": sum(r["verb"] == "check" for r in trace),
           "check_refusals": sum(r["verb"] == "check" and r.get("exit") != 0 for r in trace),
           "complete_refusals": sum(r["verb"] == "complete" and r.get("exit") != 0 for r in trace),
           "m2": None, "m3": None, "fused": None, "m4_calls": None, "m4_seconds": None,
           "m2_text": None, "m3_text": None, "fused_text": None, "co_calls": None, "co_seconds": None,
           "text_match": None}
    if not accepted:
        return row
    calls = tool_calls(sample)
    done_index = call_index(calls, accepted["ts"])
    if done_index is not None:
        row["m4_calls"] = done_index + 1
    if start is not None:
        row["m4_seconds"] = round(accepted["ts"] - start, 1)
    events = text_match(calls, trace, accepted)
    row["text_match"] = "ok" if events is not None else "unmatched"
    if events is not None:
        final = next((e for e in events if e[1] == "complete" and e[2].get("exit") == 0), None)
        refused = [i for i, e in enumerate(events) if e[2] is not None and e[2].get("exit") != 0]
        attempt = events[(refused[-1] + 1) if refused else 0:]
        attempt = [e for e in attempt if final is not None and e[0] <= final[0]]
        if final is not None and attempt:
            row["co_calls"] = final[0] - attempt[0][0] + 1
            row["co_seconds"] = round(accepted["ts"] - calls[attempt[0][0]][0], 1)
        yes_events = [e for e in events if e[1] == "check" and e[2].get("exit") == 0
                      and final is not None and e[0] <= final[0]]
        if outcome == "done" and final is not None and yes_events:
            row["m2_text"] = final[0] - yes_events[-1][0]
            row["m3_text"] = round(accepted["ts"] - yes_events[-1][2]["ts"], 1)
            row["fused_text"] = row["m2_text"] == 0
    if outcome != "done":
        return row
    yes = [r for r in trace if r["verb"] == "check" and r.get("exit") == 0 and r["ts"] <= accepted["ts"]]
    if not yes:
        row["fused"] = "no check"
        return row
    yes_index = call_index(calls, yes[-1]["ts"])
    row["m3"] = round(accepted["ts"] - yes[-1]["ts"], 1)
    if yes_index is not None and done_index is not None:
        row["m2"] = done_index - yes_index
        row["fused"] = row["m2"] == 0
    return row


def samples(root: Path):
    for result in sorted(root.glob("*/*/*/stage-result.json")):
        yield result.parent


def _median(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def summarize(rows):
    return {"samples": len(rows), "pass": sum(r["pass"] for r in rows),
            "done": sum(r["outcome"] == "done" for r in rows),
            "send_back": sum(r["outcome"] == "send-back" for r in rows),
            "m2_median": _median([r["m2"] for r in rows]), "m3_median": _median([r["m3"] for r in rows]),
            "fused": sum(r["fused"] is True for r in rows), "no_check": sum(r["fused"] == "no check" for r in rows),
            "m4_calls_median": _median([r["m4_calls"] for r in rows]),
            "m4_seconds_median": _median([r["m4_seconds"] for r in rows]),
            "m2_text_median": _median([r["m2_text"] for r in rows]),
            "m3_text_median": _median([r["m3_text"] for r in rows]),
            "fused_text": sum(r["fused_text"] is True for r in rows),
            "co_calls_median": _median([r["co_calls"] for r in rows]),
            "co_seconds_median": _median([r["co_seconds"] for r in rows]),
            "unmatched": sum(r["text_match"] == "unmatched" for r in rows),
            "check_refusals": sum(r["check_refusals"] for r in rows),
            "complete_refusals": sum(r["complete_refusals"] for r in rows)}


def main(argv):
    out = None
    if "--json" in argv:
        at = argv.index("--json")
        out, argv = Path(argv[at + 1]), argv[:at] + argv[at + 2:]
    report = {}
    for arg in argv:
        arm, root = arg.split("=", 1)
        rows = [score_sample(s) for s in samples(Path(root).expanduser())]
        cases = {}
        for r in rows:
            case = "/".join(Path(r["sample"]).parts[-3:-1])
            cases.setdefault(case, []).append(r)
        report[arm] = {"pooled": summarize(rows), "cases": {c: summarize(v) for c, v in sorted(cases.items())},
                       "rows": rows}
        print(f"== {arm}: {root}")
        print("   pooled", json.dumps(report[arm]["pooled"]))
        for case, value in report[arm]["cases"].items():
            print("  ", case, json.dumps(value))
        for r in rows:
            print("     ", "/".join(Path(r["sample"]).parts[-3:]), "pass" if r["pass"] else "FAIL", r["outcome"],
                  "m2", r["m2"], "m3", r["m3"], "m4", r["m4_calls"], r["m4_seconds"], "checks", r["checks"],
                  "refused", r["check_refusals"], r["complete_refusals"],
                  "| text:", r["text_match"], "m2", r["m2_text"], "m3", r["m3_text"], "co", r["co_calls"], r["co_seconds"])
    if out:
        out.write_text(json.dumps(report, indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
