#!/usr/bin/env python3
"""Rule D, the narrowest candidate for the implement send-back class (implement send-back study, 2026-11-01), replayed read-only
over saved step plans.  Usage: python3 -I replay_rule_d.py TRACES.txt OUT.jsonl

Rule D: the FIRST step's Proof is, as a whole, a generic suite command (``shiploop_item_scope.generic_command``: `npm test`,
`node --test`, `python3 -m unittest -v` ...), and an executed criterion of that step is covered by a focused command of the plan whose
test IDs appear in no tracked file of the item base outside docs/shiploop (ShipLoop's own knowledge files record the IDs; see
replay_rule_s_excl.py).  At that step's implement the criterion's test is unwritten (implement writes none), so a suite Proof runs
only the tests the base has: zero in a greenfield run.  It is the identifier form of the shipped rule C (which needs a test PATH in
the criterion's Confirm by), and the "generic suite Proof only" candidate the Proof-coverage replay (cc828f73) defined after seeing
its plans and did not adopt.  Each flagged step is linked to its implement outcome, as in replay_rule_s.py.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "skills", "shiploop", "scripts"))
import replay_rule_s_excl as base_tools  # noqa: E402
import shiploop_item_scope as scope  # noqa: E402


def flagged(plan, toplevel, tree):
    steps = plan.get("steps") or []
    if not steps or not isinstance(steps[0], dict):
        return None
    step = steps[0]
    proof = step.get("proof")
    if not isinstance(proof, str) or not scope.generic_command(proof):
        return None
    executed = {str(c.get("id")) for c in plan.get("criteria") or () if isinstance(c, dict) and c.get("confirm") == "executed"}
    mine = {str(c) for c in step.get("criteria") or ()} & executed
    for row in plan.get("test_commands") or ():
        if not isinstance(row, dict) or row.get("suite") != "focused" or not row.get("ids"):
            continue
        if not {str(c) for c in row.get("criteria") or ()} & mine:
            continue
        seen = [base_tools.in_base(toplevel, tree, ident) for ident in row["ids"]]
        if None in seen:
            return {"command": row["command"], "unknown": True}
        if not any(seen):
            return {"command": row["command"], "ids": row["ids"]}
    return None


def main():
    out = []
    for trace in open(sys.argv[1], encoding="utf-8").read().split():
        run = os.path.dirname(trace)
        try:
            state = base_tools.record(os.path.join(run, "state.md"))
        except OSError:
            continue
        history = state.get("history", [])
        for index, row in enumerate(history):
            if row.get("stage") != "step-plan" or row.get("outcome") != "done":
                continue
            item = row.get("workitem")
            base_file = os.path.join(run, "lint", "items", str(item) + ".md")
            if not os.path.exists(base_file):
                continue
            base = base_tools.record(base_file)
            if not base.get("tree") or not base.get("toplevel") or not os.path.isdir(base["toplevel"]):
                continue
            plan = state.get("accepted", {}).get(row["action"])
            if not isinstance(plan, dict):
                continue
            hit = flagged(plan, base["toplevel"], base["tree"])
            outcome = None
            for later in history[index + 1:]:
                if later.get("workitem") != item:
                    continue
                if later.get("stage") == "step-plan":
                    break
                if later.get("stage") == "implement":
                    outcome = later.get("outcome")
                    break
            out.append({"run": run.replace(os.path.expanduser("~") + "/", "~/"), "item": item, "action": row["action"],
                        "flag": hit, "s1_implement": outcome,
                        "proof": base_tools.norm((plan.get("steps") or [{}])[0].get("proof") or "")[:160]})
    with open(sys.argv[2], "w", encoding="utf-8") as handle:
        for row in out:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    hits = [r for r in out if r["flag"] and not r["flag"].get("unknown")]
    counts = {}
    for r in hits:
        counts[r["s1_implement"] or "no implement"] = counts.get(r["s1_implement"] or "no implement", 0) + 1
    print("plans with a base", len(out), "| flagged", len(hits), "| unknown", sum(1 for r in out if r["flag"] and r["flag"].get("unknown")),
          "| flagged by the next implement outcome:", counts)
    for r in hits:
        print(" ", (r["s1_implement"] or "no implement"), "|", r["proof"][:80], "|", r["run"][-48:])


if __name__ == "__main__":
    main()
