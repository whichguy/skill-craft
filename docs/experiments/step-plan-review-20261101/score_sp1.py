#!/usr/bin/env python3
"""Score SP1, the live check of the focused-ID rule (docs/shiploop-step-plan-review-2026-11-01.md §7), read-only.

Usage: python3 -I score_sp1.py RUNS_DIR [OUT.json]

For each run folder under RUNS_DIR (<case>-s<n>, written by run.py) it reads result.json (the harness verdict and the
held-out checks) and the ShipLoop run's trace.jsonl and state.md, and reports per run:
  - verdict: the harness's pass or fail, and the checks that failed;
  - id_sendbacks: test-spec send-backs whose result names test IDs or cases for criteria (prediction 1: none);
  - id_refusals: step-plan check or complete refusals by the new gate ("has no focused test ID of its own"), and
    whether a later step-plan draft was accepted (prediction 2);
  - uncovered: for every accepted step plan, the criteria shiploop_test_loop.criteria_without_ids leaves (prediction 3:
    none);
  - step_plan: authoring and Improve minutes and refusals per step-plan action, and every send-back to step-plan.
Prediction 4 (hidden checks hold) is the verdict.  It writes OUT.json when given and prints one line per run.
"""
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3] / "skills" / "shiploop" / "scripts"))
import shiploop_test_loop as test_loop  # noqa: E402

STATE = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)
GATE = "has no focused test ID of its own"
ID_WORDS = re.compile(r"(?i)\b(test )?ids?\b|identifier|case ids?|focused (test )?id")


def load_trace(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def run_folder(out):
    found = sorted(Path(out).glob(".shiploop-runs/*/run/trace.jsonl")) or sorted(Path(out).glob("**/run/trace.jsonl"))
    return found[0].parent if found else None


def result_of(run, state, action):
    kept = state.get("accepted", {}).get(action)
    if isinstance(kept, dict):
        return kept
    path = run / "results" / (action + ".md")
    if path.exists():
        match = STATE.search(path.read_text(encoding="utf-8"))
        if match:
            try:
                return json.loads(match.group(1)).get("result") or {}
            except ValueError:
                pass
    return {}


def score(out):
    record = {"run": out.name}
    verdict_path = out / "result.json"
    if verdict_path.exists():
        verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        record["verdict"] = verdict.get("outcome_class") or ("PASS" if verdict.get("pass") else "FAIL")
        checks = verdict.get("checks") or []
        record["checks"] = f"{sum(1 for c in checks if c.get('pass'))}/{len(checks)}"
        record["checks_failed"] = [c.get("command") for c in checks if isinstance(c, dict) and not c.get("pass")]
        span = verdict.get("span") or {}
        if span.get("started") and span.get("ended"):
            record["minutes"] = round((span["ended"] - span["started"]) / 60, 1)
        acceptance = ((verdict.get("quality") or {}).get("acceptance") or {})
        if acceptance.get("ids"):
            record["acceptance"] = f"{len(acceptance.get('passed') or [])}/{len(acceptance['ids'])}"
    run = run_folder(out)
    if run is None:
        record["note"] = "no ShipLoop run folder"
        return record
    rows = load_trace(run / "trace.jsonl")
    state = json.loads(STATE.search((run / "state.md").read_text(encoding="utf-8")).group(1))
    history = state.get("history", [])
    refusals, sendbacks = [], []
    for row in rows:
        if row.get("kind") != "command":
            continue
        if row.get("exit") not in (0, None) and (row.get("stage") or [None])[0] == "step-plan" and GATE in (row.get("error") or ""):
            refusals.append({"verb": row.get("verb"), "at": row.get("at"), "text": (row.get("error") or "")[:240]})
        for accepted in row.get("accepted") or ():
            if accepted.get("outcome") == "send-back" and (row.get("stage") or [None, None])[1] == "step-plan":
                result = result_of(run, state, accepted["action"])
                text = (result.get("headline") or "") + " " + (result.get("summary") or "")
                sendbacks.append({"from": accepted.get("stage"), "item": accepted.get("item"),
                                  "headline": result.get("headline"), "about_ids": bool(ID_WORDS.search(text))
                                  and accepted.get("stage") == "test-spec"})
    plans = [row for row in history if row.get("stage") == "step-plan" and row.get("outcome") == "done"]
    uncovered = {}
    for row in plans:
        plan = state.get("accepted", {}).get(row["action"]) or {}
        missing = test_loop.criteria_without_ids(plan.get("test_commands") or (), plan.get("criteria") or ())
        if missing:
            uncovered[row["action"]] = missing
    record.update({"id_refusals": refusals, "id_refusals_then_accepted": bool(refusals) and bool(plans),
                   "id_sendbacks": [s for s in sendbacks if s["about_ids"]], "sendbacks": sendbacks,
                   "uncovered": uncovered, "step_plans_accepted": len(plans)})
    return record


def main():
    root = Path(sys.argv[1])
    records = [score(folder) for folder in sorted(root.iterdir()) if folder.is_dir()]
    for r in records:
        print(f"{r['run']:22} verdict={r.get('verdict')} acceptance={r.get('acceptance')} minutes={r.get('minutes')} failed={r.get('checks_failed')} "
              f"id_sendbacks={len(r.get('id_sendbacks', []))} id_refusals={len(r.get('id_refusals', []))} "
              f"uncovered={len(r.get('uncovered', {}))} sendbacks={[s['from'] for s in r.get('sendbacks', [])]}")
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(records, indent=1, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
