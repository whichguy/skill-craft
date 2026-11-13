"""For every inner send-back: which steps the redone plan changed, ordered by state history (not file mtime).

done   = steps of the plan in force that were documented before the send-back
kept   = done steps whose row (task, criteria, proof, paths) is identical in the next accepted plan, by position
changed_done = done steps whose row changed (a fix-forward rule would have had to revisit them)
Also: whether the redone plan only changed steps at or after the failing step, and plan-wide fields that changed.
"""
import json, os, re, sys, collections

def block(path):
    try:
        t = open(path, errors="replace").read()
    except OSError:
        return None
    m = re.search(r"```shiploop-state\n(.*?)\n```", t, re.S)
    try:
        return json.loads(m.group(1)) if m else None
    except ValueError:
        return None

KEYS = ("task", "criteria", "proof", "paths")
def row(s):
    return {k: s.get(k) for k in KEYS}

def main(path):
    seen = set(); out = []; tally = collections.Counter()
    for d in open(path).read().split():
        st = block(d + "/state.md")
        if not st or not st.get("history"):
            continue
        rid = st.get("run_id")
        if rid in seen:
            continue
        seen.add(rid)
        res = {}
        for h in st["history"]:
            r = block(f"{d}/results/{h['action']}.md")
            if r:
                res[h["action"]] = r
        items = collections.defaultdict(list)
        for h in st["history"]:
            r = res.get(h["action"])
            if r and r.get("workitem"):
                items[r["workitem"]].append(r)
        for wi, ev in items.items():
            plan = None; documented = 0
            pending = None
            for r in ev:
                stg = r["stage"]; rr = r.get("result", {}); oc = rr.get("outcome")
                if stg == "step-plan" and oc == "done":
                    if pending is not None:
                        old, k, sb_stage, summ = pending
                        new = rr.get("steps") or []
                        oldsteps = old.get("steps") or []
                        done_ids = range(k)
                        changed_done = [i + 1 for i in done_ids if i >= len(new) or row(oldsteps[i]) != row(new[i])]
                        plan_wide = [f for f in ("criteria", "test_commands", "expectations", "paths")
                                     if json.dumps(old.get(f), sort_keys=True) != json.dumps(rr.get(f), sort_keys=True)]
                        later_changed = [i + 1 for i in range(k, max(len(oldsteps), len(new)))
                                         if i >= len(oldsteps) or i >= len(new) or row(oldsteps[i]) != row(new[i])]
                        out.append(dict(run=d.replace("/Users/dadleet/", ""), item=wi, at=sb_stage, done=k,
                                        old_steps=len(oldsteps), new_steps=len(new), changed_done=changed_done,
                                        changed_from_failing=later_changed, plan_wide=plan_wide, summary=summ[:160]))
                        pending = None
                    plan = rr; documented = 0
                elif stg == "document" and oc == "done":
                    documented += 1
                elif oc == "send-back" and plan is not None:
                    pending = (plan, documented, stg, rr.get("summary") or rr.get("headline") or "")
    for o in out:
        tally["send-backs"] += 1
        tally["with done steps"] += o["done"] > 0
        tally["a done step's row changed"] += bool(o["changed_done"])
        tally["only failing/later steps changed"] += (not o["changed_done"]) and bool(o["changed_from_failing"])
        tally["no step row changed"] += (not o["changed_done"]) and not o["changed_from_failing"]
        tally["at " + o["at"]] += 1
    print(dict(tally))
    print()
    for o in out:
        if o["done"] > 0 or o["changed_done"]:
            print(json.dumps(o))


if __name__ == "__main__":
    main(sys.argv[1])
