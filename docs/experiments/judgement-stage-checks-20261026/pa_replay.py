"""Replay the proposed product-acceptance coverage check on saved runs, with ShipLoop's own readers from main
(read-only): every current primary requirement has a test ShipLoop saw pass in a case for it, or an unverified row."""
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import shiploop_primary as primary, shiploop_store as store, shiploop_knowledge_home as knowledge
rows = []
for out in sorted(Path.home().glob("e2e-runs/2026*/*")):
    for run in out.glob(".shiploop-runs/*/run"):
        try:
            state = store.read_record(run / "state.md")
        except Exception:
            continue
        accepted = state.get("accepted") or {}
        pa = [r for r in accepted.values() if isinstance(r, dict) and r.get("stage") == "product-acceptance"]
        hist = [h for h in state.get("history") or () if h.get("stage") == "product-acceptance" and h.get("outcome") == "done"]
        if not hist:
            continue
        pa_result = accepted.get(hist[-1]["action"]) or {}
        try:
            prim = primary.primary_ids(state)
            passed = primary.passed_cases(run, state)
            held = knowledge.entries(Path(str(state["repo"])), "spec.md")
        except Exception as exc:
            rows.append({"run": f"{out.parent.name}/{out.name}", "error": f"{type(exc).__name__}: {str(exc)[:120]}"}); continue
        current = sorted((k for k, e in held.items() if not e.retired), key=lambda k: int(k.split("-")[1]))
        deferred = {str(r.get("requirement")) for r in pa_result.get("unverified") or () if isinstance(r, dict)}
        def gap(ids): return [r for r in ids if not passed.get(r) and r not in deferred]
        host = (json.loads((out / "invocation.json").read_text()).get("host") if (out / "invocation.json").is_file() else None)
        rows.append({"run": f"{out.parent.name}/{out.name}", "host": host, "primary": prim, "current": len(current),
                     "deferred": sorted(deferred), "primary_uncovered": gap(prim or []), "all_uncovered": gap(current),
                     "passed_requirements": len([r for r in current if passed.get(r)])})
for r in rows:
    print(json.dumps(r))
