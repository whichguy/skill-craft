"""For one saved run: each uncovered primary requirement's spec heading, the test-spec cases naming it, and whether
ShipLoop's verify records saw those IDs pass, skip or fail."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import shiploop_primary as primary, shiploop_store as store, shiploop_knowledge_home as knowledge, shiploop_planning_revision as pr, shiploop_test_loop as tl
out = Path(sys.argv[2]); run = next(out.glob(".shiploop-runs/*/run")); state = store.read_record(run / "state.md")
passed = primary.passed_cases(run, state); prim = primary.primary_ids(state) or []
held = knowledge.entries(Path(str(state["repo"])), "spec.md")
cur = pr.current_actions(state); acc = state.get("accepted") or {}
cases = []
for item in state.get("work_items") or ():
    a = cur.get((str(item.get("id")), "test-spec")); r = acc.get(a) if a else None
    cases += list((r or {}).get("test_cases") or [])
runs = []
for row in state.get("history") or ():
    if row.get("outcome") == "done" and row.get("workitem"):
        n = 1
        while (run / tl.verify_path(row["action"], n)).is_file():
            rec = store.read_record(run / tl.verify_path(row["action"], n)); n += 1
            for x in rec.get("runs") or ():
                runs.append((row["stage"], rec.get("passed"), x.get("status"), x.get("command", "")[:60], x.get("ids") or [], x.get("ids_missing") or []))
for req in prim:
    if passed.get(req): continue
    title = getattr(held.get(req), "title", None) or getattr(held.get(req), "heading", None) or str(held.get(req))[:90]
    named = [c for c in cases if req in knowledge.requirement_ids(str(c.get("requirement") or ""))]
    print(f"== {req}: {str(title)[:110]}")
    print(f"   cases naming it: {[c.get('id') for c in named] or 'none'}")
    for c in named[:4]:
        seen = [(st, p, s, cmd) for st, p, s, cmd, ids, miss in runs if c.get('id') in ids]
        print(f"   {c.get('id')}: in recorded runs {seen[:2] or 'never'}")
print("cases with no requirement:", [c.get("id") for c in cases if not knowledge.requirement_ids(str(c.get('requirement') or ''))][:8])
