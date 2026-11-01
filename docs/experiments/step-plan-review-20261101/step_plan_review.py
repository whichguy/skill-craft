#!/usr/bin/env python3
"""Read-only review of the step-plan stage over saved ShipLoop runs (2026-11-01).

Usage: python3 -I step_plan_review.py TRACES.txt OUT_DIR

TRACES.txt lists one RUN/trace.jsonl per line (a run directory holds trace.jsonl, state.md and results/).  For each run
it writes, as JSON lines in OUT_DIR:
  runs.jsonl          per run: case, host, model, effort, ShipLoop version, elapsed seconds, and per step-plan action
                      the authoring and Improve seconds, checks, refusals (first line) and Improve passes
  sendbacks.jsonl     every send-back to step-plan: the stage that sent it, headline, summary (cut), the wasted minutes
                      downstream (step-plan accept -> send-back) and the redo minutes (new step-plan packet -> accept)
  replay_ids.jsonl    every accepted step plan: the criteria the focused-ID rule leaves without an ID
                      (shiploop_test_loop.criteria_without_ids, the shipped function) and the next test-spec's outcome
  improve_passes.jsonl every step-plan Improve pass (RUN/improve/<action>/passes.md rows)
and prints the headline numbers.  It writes nothing else and changes no run.
"""
import json
import os
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3] / "skills" / "shiploop" / "scripts"))
import shiploop_test_loop as test_loop  # noqa: E402

STATE = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)


def events(trace):
    rows = []
    for line in open(trace, encoding="utf-8"):
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    return rows


def invocation(trace):
    folder = os.path.dirname(trace)
    while folder and folder != "/":
        path = os.path.join(folder, "invocation.json")
        if os.path.exists(path):
            try:
                data = json.load(open(path, encoding="utf-8"))
            except ValueError:
                return {}
            versions = data.get("versions") or {}
            return {"case": data.get("case"), "host": data.get("host"), "model": data.get("model"),
                    "effort": data.get("effort"), "shiploop": versions.get("shiploop_version")}
        folder = os.path.dirname(folder)
    return {}


def state_of(run):
    found = STATE.search(open(os.path.join(run, "state.md"), encoding="utf-8").read())
    return json.loads(found.group(1))


def result_of(run, state, action):
    kept = state.get("accepted", {}).get(action)
    if isinstance(kept, dict):
        return kept
    path = os.path.join(run, "results", action + ".md")
    if os.path.exists(path):
        found = STATE.search(open(path, encoding="utf-8").read())
        if found:
            try:
                return json.loads(found.group(1)).get("result") or {}
            except ValueError:
                pass
    return {}


def first_line(text, size=200):
    lines = (text or "").strip().splitlines()
    return re.sub(r"/Users/\S+", "PATH", lines[0])[:size] if lines else ""


def spans(rows):
    """Each action's [start, end) seconds: from its first packet (or the cursor move into it) to the move out."""
    start, end = {}, {}
    for row in rows:
        if row.get("kind") == "packet" and row.get("action") and row["action"] not in start:
            start[row["action"]] = row["ts"]
    for row in rows:
        if row.get("kind") == "command" and row.get("exit") == 0 and isinstance(row.get("cursor"), list):
            before, after = row["cursor"]
            if before != after:
                end.setdefault(before, row["ts"])
                start.setdefault(after, row["ts"])
    return start, end


def run_record(trace):
    rows = events(trace)
    start, end = spans(rows)
    packets = {}
    for row in rows:
        if row.get("kind") == "packet" and row.get("action") not in packets:
            packets[row.get("action")] = row
    commands = {}
    for row in rows:
        if row.get("kind") == "command" and row.get("action"):
            commands.setdefault(row["action"], []).append(row)
    moves = [(row["cursor"][0], row["cursor"][1], (row.get("stage") or [None, None])[1]) for row in rows
             if row.get("kind") == "command" and row.get("exit") == 0 and isinstance(row.get("cursor"), list)
             and row["cursor"][0] != row["cursor"][1]]
    plans = []
    for action, packet in packets.items():
        if packet.get("stage") != "step-plan":
            continue
        own = commands.get(action, [])
        plan = {"item": packet.get("item"), "chars": packet.get("chars"), "printed": packet.get("printed"),
                "author_s": round(end[action] - start[action], 1) if action in end else None,
                "checks": sum(1 for row in own if row.get("verb") == "check"),
                "refusals": [first_line(row.get("error")) for row in own
                             if row.get("verb") in ("check", "complete") and row.get("exit") not in (0, None)]}
        nxt = next(((after, stage) for before, after, stage in moves if before == action), None)
        if nxt and nxt[1] == "improve" and nxt[0] in end:
            plan["improve_s"] = round(end[nxt[0]] - start[nxt[0]], 1)
            plan["improve_passes"] = sum(1 for row in commands.get(nxt[0], []) if row.get("verb") == "improve-pass")
        plans.append(plan)
    return {"trace": trace, **invocation(trace), "elapsed_s": round(rows[-1]["ts"] - rows[0]["ts"], 1) if rows else 0,
            "step_plans": plans}


def sendbacks(trace):
    rows, run = events(trace), os.path.dirname(trace)
    state = state_of(run)
    found = []
    for row in rows:
        if row.get("kind") != "command" or (row.get("stage") or [None, None])[1] != "step-plan":
            continue
        for accepted in row.get("accepted") or ():
            if accepted.get("outcome") != "send-back":
                continue
            item = accepted.get("item")
            plans = [p for p in rows if p.get("kind") == "packet" and p.get("stage") == "step-plan"
                     and p.get("item") == item]
            before = [p for p in plans if p["ts"] < row["ts"] - 2]
            after = [p for p in plans if p["ts"] >= row["ts"] - 2]

            def accepted_at(action):
                return next((r["ts"] for r in rows if r.get("kind") == "command"
                             for a in r.get("accepted") or () if a.get("action") == action
                             and a.get("outcome") == "done"), None)
            plan_done = accepted_at(before[-1]["action"]) if before else None
            redo_done = accepted_at(after[0]["action"]) if after else None
            result = result_of(run, state, accepted["action"])
            found.append({"trace": trace, **invocation(trace), "at": row.get("at"), "from": accepted.get("stage"),
                          "item": item, "headline": result.get("headline"),
                          "summary": re.sub(r"/Users/\S+", "PATH", result.get("summary") or "")[:600],
                          "wasted_min": round((row["ts"] - plan_done) / 60, 2) if plan_done else None,
                          "redo_min": round((redo_done - after[0]["ts"]) / 60, 2) if redo_done and after else None})
    return found


def replay_ids(trace):
    run = os.path.dirname(trace)
    state = state_of(run)
    history = state.get("history", [])
    found = []
    for index, row in enumerate(history):
        if row.get("stage") != "step-plan" or row.get("outcome") != "done":
            continue
        plan = state.get("accepted", {}).get(row["action"])
        if not isinstance(plan, dict):
            continue
        spec = next((later for later in history[index + 1:] if later.get("workitem") == row.get("workitem")
                     and later.get("stage") in ("test-spec", "step-plan")), None)
        spec = spec if spec and spec.get("stage") == "test-spec" else None
        found.append({"trace": trace, "item": row.get("workitem"), "action": row["action"],
                      "missing": test_loop.criteria_without_ids(plan.get("test_commands") or (),
                                                                plan.get("criteria") or ()),
                      "test_spec": spec.get("outcome") if spec else None,
                      "test_spec_headline": (result_of(run, state, spec["action"]).get("headline") or "")[:160]
                      if spec else None})
    return found


def improve_passes(trace):
    run = os.path.dirname(trace)
    rows = []
    for passes in sorted(Path(run, "improve").glob("nav-*/passes.md")):
        for line in passes.read_text(encoding="utf-8").splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 8 and cells[0] == "step-plan":
                rows.append({"trace": trace, "action": passes.parent.name, "pass": cells[1], "label": cells[2],
                             "tree_changed": cells[3], "result_changed": cells[4],
                             "seconds": int(cells[7]) if cells[7].isdigit() else None})
    return rows


def main():
    traces = [line.strip() for line in open(sys.argv[1], encoding="utf-8") if line.strip()]
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    tables = {"runs": [run_record(t) for t in traces],
              "sendbacks": [row for t in traces for row in sendbacks(t)],
              "replay_ids": [row for t in traces for row in replay_ids(t)],
              "improve_passes": [row for t in traces for row in improve_passes(t)]}
    for name, rows in tables.items():
        with open(out / (name + ".jsonl"), "w", encoding="utf-8") as handle:
            for row in rows:
                short = {**row, "trace": row["trace"].replace(str(Path.home()) + "/", "~/")} if "trace" in row else row
                handle.write(json.dumps(short, sort_keys=True) + "\n")
    plans = [plan for run in tables["runs"] for plan in run["step_plans"]]
    author = [p["author_s"] / 60 for p in plans if p.get("author_s") is not None]
    improve = [p["improve_s"] / 60 for p in plans if p.get("improve_s") is not None]
    share = [100 * sum((p.get("author_s") or 0) + (p.get("improve_s") or 0) for p in run["step_plans"])
             / run["elapsed_s"] for run in tables["runs"] if run["elapsed_s"]]
    print("runs", len(tables["runs"]), "step-plan actions", len(plans))
    print("authoring min median %.2f mean %.2f; Improve min median %.2f mean %.2f (n %d); share of run median %.1f%%"
          % (statistics.median(author), statistics.mean(author), statistics.median(improve), statistics.mean(improve),
             len(improve), statistics.median(share)))
    print("checks", sum(p["checks"] for p in plans), "refusals", sum(len(p["refusals"]) for p in plans))
    print("send-backs to step-plan", len(tables["sendbacks"]), dict(Counter(r["from"] for r in tables["sendbacks"])))
    print("focused-ID rule:", dict(Counter((bool(r["missing"]), r["test_spec"]) for r in tables["replay_ids"])))
    reviews = Counter((r["trace"], r["action"]) for r in tables["improve_passes"])
    changed = {(r["trace"], r["action"]) for r in tables["improve_passes"]
               if "y" in (r["tree_changed"], r["result_changed"])}
    print("step-plan Improve reviews", len(reviews), "passes", len(tables["improve_passes"]), "changed the plan",
          len(changed))


if __name__ == "__main__":
    main()
