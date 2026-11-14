"""For send-backs after a documented step: did the item-wide changes (criteria, test commands, expectations) touch
anything a done step owns? A done step owns its criteria IDs; a test command touches it when the command's ids/criteria
include one of those criteria or its test IDs."""
import json, re, sys, collections
sys.path.insert(0, ".")
from fixforward import block  # noqa: E402

def by_id(xs, key="id"):
    return {x.get(key): x for x in (xs or []) if isinstance(x, dict)}

for d in open(sys.argv[1]).read().split():
    st = block(d + "/state.md")
    if not st or not st.get("history"):
        continue
    ev = []
    for h in st["history"]:
        r = block(f"{d}/results/{h['action']}.md")
        if r and r.get("workitem"):
            ev.append(r)
    items = collections.defaultdict(list)
    for r in ev:
        items[r["workitem"]].append(r)
    for wi, rs in items.items():
        plan = None; documented = 0; pending = None
        for r in rs:
            rr = r.get("result", {}); oc = rr.get("outcome")
            if r["stage"] == "step-plan" and oc == "done":
                if pending:
                    old, k = pending
                    owned = {c for s in (old.get("steps") or [])[:k] for c in (s.get("criteria") or [])}
                    oc_, nc_ = by_id(old.get("criteria")), by_id(rr.get("criteria"))
                    crit_changed = sorted(i for i in set(oc_) | set(nc_) if json.dumps(oc_.get(i), sort_keys=True) != json.dumps(nc_.get(i), sort_keys=True))
                    def cmds(p):
                        return {json.dumps(c, sort_keys=True) for c in (p.get("test_commands") or [])}
                    removed = [json.loads(c) for c in cmds(old) - cmds(rr)]
                    added = [json.loads(c) for c in cmds(rr) - cmds(old)]
                    def touches(c):
                        ids = set(c.get("ids") or []) | set(c.get("criteria") or [])
                        return sorted(ids & owned) if ids else "no ids listed"
                    print(json.dumps(dict(run=d.split("/")[-4] if "shiploop-runs" in d else d.split("/")[-1], item=wi, done=k,
                                          owned_by_done=sorted(owned), criteria_changed=crit_changed,
                                          changed_owned=sorted(set(crit_changed) & owned),
                                          cmds_removed=[(c.get("suite"), touches(c)) for c in removed],
                                          cmds_added=[(c.get("suite"), touches(c)) for c in added])))
                    pending = None
                plan = rr; documented = 0
            elif r["stage"] == "document" and oc == "done":
                documented += 1
            elif oc == "send-back" and plan is not None and documented > 0:
                pending = (plan, documented)
