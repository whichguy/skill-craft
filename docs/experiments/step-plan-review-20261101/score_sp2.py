#!/usr/bin/env python3
"""Score SP2, the step-plan slice A/B of the focused-ID rule (docs/shiploop-step-plan-review-2026-11-01.md §7),
read-only.  Usage: python3 -I score_sp2.py SP2_DIR [OUT.json]

For each slice folder <arm>-<case>-s<n> it reads the run's trace.jsonl and state.md and reports:
  short        the criteria the accepted step plan leaves without a focused ID (criteria_without_ids, the shipped
               function, so the same yardstick for both arms)
  gate         refusals by the new gate in the step-plan loop (arm T only can have them: how often a draft was short)
  refusals     every step-plan check or complete refusal
  test_spec    the test-spec outcomes in order (done, send-back) with each send-back's headline, and whether it is
               about IDs
  minutes      step-plan authoring and Improve minutes (summed over the item's step-plan actions)
  cases        test-spec cases per executed criterion of the plan the accepted test-spec followed
and prints a line per slice and a per-arm summary.
"""
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3] / "skills" / "shiploop" / "scripts"))
import shiploop_test_loop as test_loop  # noqa: E402

STATE = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)
GATE = "has no focused test ID of its own"
ABOUT_IDS = re.compile(r"(?i)\bids?\b|identifier|focused (test )?id|one case per|separate (test )?case")


def events(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def result_of(run, state, action):
    kept = state.get("accepted", {}).get(action)
    if isinstance(kept, dict):
        return kept
    path = run / "results" / (action + ".md")
    if path.exists():
        found = STATE.search(path.read_text(encoding="utf-8"))
        if found:
            try:
                return json.loads(found.group(1)).get("result") or {}
            except ValueError:
                pass
    return {}


def score(folder):
    run = folder / ".shiploop-runs" / "seed" / "run"
    record = {"slice": folder.name, "arm": folder.name.split("-", 1)[0]}
    if not (run / "trace.jsonl").exists():
        record["note"] = "no run"
        return record
    rows = events(run / "trace.jsonl")
    state = json.loads(STATE.search((run / "state.md").read_text(encoding="utf-8")).group(1))
    start, end, stage_of = {}, {}, {}
    for row in rows:
        if row.get("kind") == "packet" and row.get("action"):
            start.setdefault(row["action"], row["ts"])
            stage_of.setdefault(row["action"], (row.get("stage"), row.get("reviewed")))
    for row in rows:
        if row.get("kind") == "command" and row.get("exit") == 0 and isinstance(row.get("cursor"), list):
            before, after = row["cursor"]
            if before != after:
                end.setdefault(before, row["ts"])
                start.setdefault(after, row["ts"])
    author = sum(end[a] - start[a] for a, (s, r) in stage_of.items() if s == "step-plan" and a in end)
    review = sum(end[a] - start[a] for a, (s, r) in stage_of.items() if s == "improve" and r == "step-plan" and a in end)
    refusals = [re.sub(r"/\S+", "PATH", (row.get("error") or "").strip().splitlines()[0])[:160] for row in rows
                if row.get("kind") == "command" and row.get("exit") not in (0, None)
                and (row.get("stage") or [None])[0] == "step-plan" and row.get("error")]
    gate = [r for r in refusals if GATE in r]
    history = state.get("history", [])
    specs = []
    for row in history:
        if row.get("stage") == "test-spec":
            result = result_of(run, state, row["action"])
            text = (result.get("headline") or "") + " " + (result.get("summary") or "")
            specs.append({"outcome": row.get("outcome"), "headline": result.get("headline"),
                          "about_ids": row.get("outcome") == "send-back" and bool(ABOUT_IDS.search(text))})
    plans = [row for row in history if row.get("stage") == "step-plan" and row.get("outcome") == "done"]
    short, cases = [], None
    if plans:
        plan = state["accepted"][plans[-1]["action"]]
        short = test_loop.criteria_without_ids(plan.get("test_commands") or (), plan.get("criteria") or ())
        executed = [c for c in plan.get("criteria") or () if c.get("confirm") == "executed"]
        done_specs = [row for row in history if row.get("stage") == "test-spec" and row.get("outcome") == "done"]
        if done_specs and executed:
            got = state["accepted"][done_specs[-1]["action"]].get("test_cases") or []
            cases = round(len(got) / len(executed), 2)
        record["criteria"] = len(plan.get("criteria") or [])
        record["focused_ids"] = sum(len(t.get("ids") or []) for t in plan.get("test_commands") or ()
                                    if t.get("suite") == "focused")
    record.update({"short": short, "gate": len(gate), "refusals": refusals, "test_spec": specs,
                   "author_min": round(author / 60, 2), "review_min": round(review / 60, 2), "cases_per_criterion": cases,
                   "plans": len(plans)})
    return record


def main():
    root = Path(sys.argv[1])
    records = [score(folder) for folder in sorted(root.iterdir()) if folder.is_dir()]
    for r in records:
        if "note" in r:
            print(f"{r['slice']:28} {r['note']}")
            continue
        sends = [("ID" if s["about_ids"] else "other") for s in r["test_spec"] if s["outcome"] == "send-back"]
        print(f"{r['slice']:28} short={r['short']} gate={r['gate']} refusals={len(r['refusals'])} "
              f"test-spec send-backs={sends} author={r['author_min']} review={r['review_min']} "
              f"criteria={r.get('criteria')} ids={r.get('focused_ids')} cases/crit={r['cases_per_criterion']}")
    for arm in ("B", "T"):
        rows = [r for r in records if r.get("arm") == arm and "note" not in r]
        if not rows:
            continue
        minutes = [r["author_min"] + r["review_min"] for r in rows]
        print(f"arm {arm}: slices {len(rows)}, short accepted plans {sum(1 for r in rows if r['short'])}, "
              f"slices with a gate refusal {sum(1 for r in rows if r['gate'])}, test-spec ID send-backs "
              f"{sum(1 for r in rows for s in r['test_spec'] if s['about_ids'])}, other send-backs "
              f"{sum(1 for r in rows for s in r['test_spec'] if s['outcome'] == 'send-back' and not s['about_ids'])}, "
              f"step-plan minutes median {statistics.median(minutes):.2f}")
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(records, indent=1, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
