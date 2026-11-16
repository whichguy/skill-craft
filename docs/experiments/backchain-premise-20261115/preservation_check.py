#!/usr/bin/env python3
"""Did either arm of the 2026-11-15 value study break the inherited-plan rules Backchain's contract scripts enforce?

For each case with an inherited plan, compares every final plan (both arms, three models) with the inherited one:
- without caller edit bounds (Backchain's `legacy` mode): every inherited step id, its `origin`, every inherited input
  edge (need, from), the `goal` and `goal_needs` stay; a confirmation of a produce whose text is unchanged stays whole;
  added `initial_state` facts are listed (Backchain refuses one only when it closes a need the inherited plan left
  open, which needs judgement and is not decided here);
- with caller edit bounds (`source-aware` mode): protected and running-or-completed steps stay unchanged, protected
  edges and protected facts stay, a new step or edge appears only when the bounds allow it, and `goal_needs` stays.

This restates freeze's rules (references/convergence.md, "Obligations a candidate keeps", and caller-contract.md); it
is not the released code, so a difference here is a candidate violation to read, not a verdict. The inherited plans are
the cohort's cases, pinned by hash in ../backchain-value-20261115/evidence/freeze.json; they sit in the private
harness, so give their path:
    BACKCHAIN_COHORT_CASES=<backchain>/results/backchain-efficiency-20261101/cohort/cases.json \
        python3 -I docs/experiments/backchain-premise-20261115/preservation_check.py
Writes preservation-check.json beside this script.
"""
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLANS = HERE.parent / "backchain-value-20261115" / "evidence" / "plans.json"


def edge_keys(plan):
    return {f"{s['id']}<-{i['from'] if i['from'] is not None else 'null'}"
            for s in plan.get("steps", []) for i in s.get("inputs", [])}


def edges(plan):
    return {(s["id"], i["need"], i["from"]) for s in plan.get("steps", []) for i in s.get("inputs", [])}


def norm(text):
    return " ".join(str(text).split())


def legacy_violations(old, new):
    found = []
    new_steps = {s["id"]: s for s in new.get("steps", [])}
    for step in old["steps"]:
        mine = new_steps.get(step["id"])
        if mine is None:
            found.append(f"inherited step {step['id']} removed")
            continue
        if mine.get("origin") != step.get("origin"):
            found.append(f"{step['id']} origin changed")
        kept = {(c["produces"], c["by"], c["level"]) for c in mine.get("confirm", [])}
        for conf in step.get("confirm", []):
            unchanged = conf["produces"] in mine.get("produces", [])
            if unchanged and (conf["produces"], conf["by"], conf["level"]) not in kept:
                found.append(f"{step['id']} confirmation of an unchanged produce changed")
    for consumer, need, supplier in sorted(edges(old) - edges(new), key=str):
        found.append(f"inherited edge {consumer}<-{supplier} ({need[:60]}) removed or rewritten")
    if norm(old.get("goal", "")) != norm(new.get("goal", "")):
        found.append("goal changed")
    if old.get("goal_needs", []) != new.get("goal_needs", []):
        found.append("goal_needs changed")
    stated = {norm(x) for x in old.get("initial_state", [])}
    added = [f for f in new.get("initial_state", []) if norm(f) not in stated]
    # The mechanical half of the "silent inv-7 repair" rule: an added fact that declares an inherited `from: null`
    # need the inherited plan left undeclared. (A need the inherited plan never wrote as an edge needs judgement.)
    open_null = {norm(i["need"]) for s in old["steps"] for i in s.get("inputs", [])
                 if i["from"] is None and norm(i["need"]) not in stated}
    for fact in added:
        if norm(fact) in open_null:
            found.append(f"added initial_state fact closes an inherited undeclared null need: {fact[:60]}")
    return found, added


def step_body(step):
    """A step without its inputs: edges are judged separately, by edge key."""
    return json.dumps({k: v for k, v in step.items() if k != "inputs"}, sort_keys=True)


def bounded_violations(old, new, bounds):
    """caller-contract.md: running/completed and protected items stay; an existing item changes only if its exact
    ID/key is provisional; new steps need allow_new_steps; a new or changed edge to an existing consumer needs
    allow_new_edges and a provisional, not running/completed consumer; a protected fact the inherited plan states in
    initial_state stays there, and one it never stated is not added (contradiction needs judgement: not checked)."""
    found = []
    old_steps = {s["id"]: s for s in old["steps"]}
    new_steps = {s["id"]: s for s in new.get("steps", [])}
    done = set(bounds.get("running_or_completed_step_ids", []))
    frozen = set(bounds.get("protected_step_ids", [])) | done
    provisional = set(bounds.get("provisional_step_ids", [])) - frozen
    for sid, step in old_steps.items():
        if sid not in new_steps:
            if sid not in provisional:
                found.append(f"non-provisional step {sid} removed")
        elif step_body(new_steps[sid]) != step_body(step) and sid not in provisional:
            found.append(f"non-provisional step {sid} changed")
    for key in bounds.get("protected_edge_keys", []):
        if key not in edge_keys(new):
            found.append(f"protected edge {key} removed")
    stated = {norm(f) for f in old.get("initial_state", [])}
    facts = {norm(f) for f in new.get("initial_state", [])}
    for fact in bounds.get("protected_facts", []):
        if norm(fact) in stated and norm(fact) not in facts:
            found.append(f"protected fact removed from initial_state: {fact[:60]}")
    added_steps = set(new_steps) - set(old_steps)
    if added_steps and not bounds.get("allow_new_steps", False):
        found.append(f"new steps {sorted(added_steps)} without allow_new_steps")
    old_by_consumer = {sid: edges({"steps": [s]}) for sid, s in old_steps.items()}
    for sid, step in new_steps.items():
        if sid not in old_steps:
            continue
        if edges({"steps": [step]}) != old_by_consumer[sid]:
            if sid not in provisional:
                found.append(f"edges of non-provisional consumer {sid} changed")
            elif (edge_keys({"steps": [step]}) - edge_keys({"steps": [old_steps[sid]]})
                  and not bounds.get("allow_new_edges", False)):
                found.append(f"new edge to {sid} without allow_new_edges")
    if old.get("goal_needs", []) != new.get("goal_needs", []):
        found.append("goal_needs changed")
    return found, []


def main() -> None:
    cases = json.loads(Path(os.environ["BACKCHAIN_COHORT_CASES"]).read_text())
    cases = cases.get("cases", cases)
    cases = list(cases.values()) if isinstance(cases, dict) else cases
    plans = json.loads(PLANS.read_text())
    plans = plans.get("plans", plans)
    rows, totals = [], {"backchain": 0, "none": 0}
    for case in cases:
        if not case.get("draft"):
            continue
        for model in ("grok", "sol", "sonnet"):
            for arm in ("backchain", "none"):
                final = plans[f"{case['id']}--{arm}--{model}"]["plan"]
                bounds = case.get("edit_bounds")
                found, added = (bounded_violations(case["draft"], final, bounds) if bounds
                                else legacy_violations(case["draft"], final))
                totals[arm] += bool(found)
                rows.append({"case": case["id"], "model": model, "arm": arm,
                             "mode": "source-aware" if bounds else "legacy",
                             "candidate_violations": found, "added_initial_state_facts": len(added)})
    out = {"plans_checked": len(rows), "plans_with_a_candidate_violation": totals, "rows": rows}
    (HERE / "preservation-check.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"{len(rows)} plans; with a candidate violation: Backchain {totals['backchain']}, no skill {totals['none']}")
    for r in rows:
        if r["candidate_violations"]:
            print(f"  {r['case']} {r['model']} {r['arm']} ({r['mode']}): {r['candidate_violations']}")


if __name__ == "__main__":
    main()
