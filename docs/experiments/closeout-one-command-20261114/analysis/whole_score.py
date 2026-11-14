#!/usr/bin/env python3
"""Score the round-2 whole deliveries (README, "Round 2: whole deliveries": measures W1 to W5).

    python3 whole_score.py B=<run> [<run> ...] T=<run> [<run> ...] [--json OUT]

A run is an E2E output folder (``run.py --output``): ``result.json``, ``metrics.json``, ``events.jsonl``,
``timeline.jsonl`` and ``.shiploop-runs/*/run/trace.jsonl``. No model judges anything.

Per inner action (step-plan, test-spec, validate-existing, implement, test, document, carry-forward) the close-out is read
by command text, as in ``closeout_score.py``: each ``shiploop check`` and ``shiploop complete`` is recognised in the call
that runs it with the ``--action`` it names, and the loop's ``done`` (run as ``until_loop_ephemeral.py done``, or through
a Python wrapper that holds ``exit_assessment`` and ``subprocess``) is given to the first accepted ``complete`` at or after it.
The trace rows of an action are walked against its recognised commands in order, and an action whose rows and commands
disagree is marked ``unmatched``. The close-out span runs from the first close-out command of the action's final attempt
(after its last refusal) to its accepted ``complete``, in tool calls and seconds.

Fields per action: stage, outcome (from the ``accepted`` lists, else ``done``), checks, passing checks, refusals (check,
complete, and those naming the loop), the script seconds of passing checks after the first (``dup_seconds``), close-out
calls and seconds, and ``fused`` (the last passing check ran in the same call as the accepted ``complete``).
"""
from __future__ import annotations

import collections
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import closeout_score as cs  # noqa: E402  (tool_calls, _jsonl)

INNER = ("step-plan", "test-spec", "validate-existing", "implement", "test", "document", "carry-forward")
_RUN = r"/shiploop['\"]?\s+"
VERB = re.compile(r"(?P<check>" + _RUN + r"check\s+--run-dir)|(?P<complete>" + _RUN + r"complete\s+--run-dir)"
                  r"|(?P<done>until_loop_ephemeral\.py['\"]?\s+['\"]?done['\"]?\s+['\"]?--state)")
ACTION = re.compile(r"--action[= ]\s*['\"]?(nav-[0-9a-f]+)")
LOOPY = re.compile(r"\bloop\b|receipt|next_argv|still active", re.I)  # not "ShipLoop"


def commands(text: str):
    """[(position, verb, action or None)] for the close-out commands a call's text runs."""
    found = []
    for match in VERB.finditer(text or ""):
        verb = next(key for key, value in match.groupdict().items() if value)
        action = None
        if verb != "done":
            tail = ACTION.search(text, match.end(), match.end() + 600)
            action = tail.group(1) if tail else None
        found.append((match.start(), verb, action))
    if "exit_assessment" in (text or "") and "subprocess" in (text or "") and not any(v == "done" for _, v, _ in found):
        found.append((text.find("exit_assessment"), "done", None))
    return sorted(found, key=lambda item: item[0])


def median(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def score_run(run: Path) -> dict:
    result = json.loads((run / "result.json").read_text()) if (run / "result.json").exists() else {}
    metrics = json.loads((run / "metrics.json").read_text()) if (run / "metrics.json").exists() else {}
    trace_file = next(iter(sorted(run.glob(".shiploop-runs/*/run/trace.jsonl"))), None)
    rows = [r for r in cs._jsonl(trace_file) if r] if trace_file else []
    calls = cs.tool_calls(run)
    stage_of, outcome_of = {}, {}
    for row in rows:
        if row.get("kind") == "packet":
            stage_of.setdefault(row["action"], row["stage"])
        for item in row.get("accepted") or []:
            outcome_of[item["action"]] = item.get("outcome")
    command_rows = collections.defaultdict(list)
    for row in rows:
        if row.get("kind") == "command" and row.get("verb") in ("check", "complete") and row.get("action"):
            command_rows[row["action"]].append(row)
    invocations = collections.defaultdict(list)
    dones = []
    for index, (_, _, text) in enumerate(calls):
        for position, verb, action in commands(text):
            if verb == "done":
                dones.append((index, position))
            elif action:
                invocations[action].append((index, position, verb))
    walked_of = {action: _walk(invocations.get(action, []), rs) for action, rs in command_rows.items()}
    # A chain stops at a refused check or complete: a loop done after it in the same call never ran.
    refused_at = {}
    for walked in walked_of.values():
        for call, _, row, position in walked or []:
            if row.get("exit") != 0:
                refused_at[call] = min(refused_at.get(call, position), position)
    ran_dones = [call for call, position in dones if position < refused_at.get(call, float("inf"))]
    # Each action's accepted complete: the call that ran its first passing complete row.
    final_call = {}
    for action, rs in command_rows.items():
        walked = walked_of[action]
        if walked is not None:
            for call, verb, row, _ in walked:
                if verb == "complete" and row.get("exit") == 0:
                    final_call[action] = call
                    break
    ends = sorted(final_call.values())
    actions = []
    for action, rs in sorted(command_rows.items(), key=lambda item: item[1][0]["ts"]):
        stage = stage_of.get(action)
        if stage not in INNER:
            continue
        accepted = next((r for r in rs if r["verb"] == "complete" and r.get("exit") == 0), None)
        entry = {"action": action, "stage": stage, "outcome": outcome_of.get(action, "done" if accepted else None),
                 "accepted": accepted is not None, "text_match": None, "co_calls": None, "co_seconds": None,
                 "fused": None, "close_out": None, "checks": sum(r["verb"] == "check" for r in rs),
                 "yes": sum(r["verb"] == "check" and r.get("exit") == 0 for r in rs),
                 "check_refusals": sum(r["verb"] == "check" and r.get("exit") != 0 for r in rs),
                 "complete_refusals": sum(r["verb"] == "complete" and r.get("exit") != 0 for r in rs),
                 "loop_refusals": sum(r.get("exit") != 0 and bool(LOOPY.search(str(r.get("error") or ""))) for r in rs),
                 "dup_seconds": round(sum(r.get("ms", 0) for r in [r for r in rs if r["verb"] == "check"
                                                                       and r.get("exit") == 0][1:]) / 1000, 1)}
        walked = walked_of[action] if accepted else None
        entry["text_match"] = None if not accepted else ("ok" if walked is not None else "unmatched")
        if walked is not None and action in final_call:
            final = final_call[action]
            prev = max([e for e in ends if e < final], default=-1)
            own_dones = [d for d in ran_dones if prev < d <= final]
            events = [(call, verb, row) for call, verb, row, _ in walked] + [(d, "done", None) for d in own_dones]
            events.sort(key=lambda e: (e[0], 0 if e[1] != "complete" else 1))
            refused = [i for i, e in enumerate(events) if e[2] is not None and e[2].get("exit") != 0]
            attempt = [e for e in events[(refused[-1] + 1) if refused else 0:] if e[0] <= final]
            entry["close_out"] = [[call, verb] for call, verb, _ in attempt]
            if attempt:
                entry["co_calls"] = final - attempt[0][0] + 1
                entry["co_seconds"] = round(accepted["ts"] - calls[attempt[0][0]][0], 1)
            yes_calls = [c for c, v, r, _ in walked if v == "check" and r.get("exit") == 0 and c <= final]
            entry["fused"] = bool(yes_calls) and yes_calls[-1] == final
        actions.append(entry)
    verdicts = {k: result.get(k) for k in ("invoked", "plugin", "process", "shiploop", "committed", "checks")}
    span = result.get("span") or metrics.get("span") or {}
    return {"run": str(run), "pass": bool(result.get("pass")), "verdicts": verdicts, "tool_calls": len(calls),
            "turns": metrics.get("turns"), "tokens": metrics.get("tokens"), "span": span,
            "local_head": result.get("local_head") or (result.get("versions") or {}).get("local_head"),
            "actions": actions}


def _walk(invs, rows):
    """Pair an action's recognised check and complete commands with its trace rows, in order; None when they disagree."""
    checks = [r for r in rows if r["verb"] == "check"]
    completes = [r for r in rows if r["verb"] == "complete"]
    ci = ki = 0
    walked = []
    stopped = None  # call index whose chain a refusal stopped
    for call, position, verb in sorted(invs, key=lambda i: (i[0], i[1])):
        if stopped == call:
            continue
        if verb == "check":
            if ci >= len(checks):
                return None
            row = checks[ci]
            ci += 1
        else:
            if ki >= len(completes):
                return None
            row = completes[ki]
            ki += 1
        walked.append((call, verb, row, position))
        if row.get("exit") != 0:
            stopped = call
    return walked if ci == len(checks) and ki == len(completes) else None


def summarize(runs):
    actions = [a for r in runs for a in r["actions"] if a["accepted"]]
    done = [a for a in actions if a["outcome"] == "done"]
    out = {"runs": len(runs), "pass": sum(r["pass"] for r in runs), "tool_calls": [r["tool_calls"] for r in runs],
           "turns": [r["turns"] for r in runs], "done_stages": len(done),
           "unmatched": sum(a["text_match"] == "unmatched" for a in done),
           "co_calls_median": median([a["co_calls"] for a in done]),
           "co_seconds_median": median([a["co_seconds"] for a in done]),
           "fused": sum(a["fused"] is True for a in done),
           "repeated_check_stages": sum(a["yes"] > 1 for a in done),
           "dup_seconds": round(sum(a["dup_seconds"] for a in done), 1),
           "check_refusals": sum(a["check_refusals"] for a in actions),
           "complete_refusals": sum(a["complete_refusals"] for a in actions),
           "loop_refusals": sum(a["loop_refusals"] for a in actions), "by_stage": {}}
    for stage in INNER:
        rows = [a for a in done if a["stage"] == stage]
        if rows:
            out["by_stage"][stage] = {
                "n": len(rows), "co_calls": sorted(a["co_calls"] for a in rows if a["co_calls"] is not None),
                "co_seconds": sorted(a["co_seconds"] for a in rows if a["co_seconds"] is not None),
                "fused": sum(a["fused"] is True for a in rows), "yes": [a["yes"] for a in rows],
                "dup_seconds": round(sum(a["dup_seconds"] for a in rows), 1),
                "unmatched": sum(a["text_match"] == "unmatched" for a in rows)}
    return out


def main(argv):
    out = None
    if "--json" in argv:
        at = argv.index("--json")
        out, argv = Path(argv[at + 1]), argv[:at] + argv[at + 2:]
    arms, current = collections.OrderedDict(), None
    for arg in argv:
        if "=" in arg and not arg.startswith("/") and not arg.startswith("~"):
            current, arg = arg.split("=", 1)[0], arg.split("=", 1)[1]
            arms.setdefault(current, [])
        arms[current].append(Path(arg).expanduser())
    report = {}
    for arm, runs in arms.items():
        scored = [score_run(run) for run in runs]
        report[arm] = {"summary": summarize(scored), "runs": scored}
        print(f"== {arm}: {json.dumps(report[arm]['summary'])}")
        for r in scored:
            print(f"   {Path(r['run']).name}: pass {r['pass']} verdicts {r['verdicts']} tool_calls {r['tool_calls']} turns {r['turns']}")
            for a in r["actions"]:
                if a["accepted"]:
                    print(f"      {a['stage']:18} {str(a['outcome']):10} match {a['text_match']:9} co {a['co_calls']} calls {a['co_seconds']} s "
                          f"fused {a['fused']} checks {a['checks']} yes {a['yes']} refused {a['check_refusals']}/{a['complete_refusals']}"
                          f" loop {a['loop_refusals']} dup {a['dup_seconds']} s")
    if out:
        out.write_text(json.dumps(report, indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
