import json, sys
from pathlib import Path
C = Path(sys.argv[1]); TREE = Path(sys.argv[2])
sys.path.insert(0, str(TREE / "skills/backchain/scripts"))
import backchain_graph as graph
def load(p):
    try: return json.loads(Path(p).read_text())
    except Exception: return None
def canon(plan): return graph.js_stringify(graph.package(plan))
for d in sorted((C/"runs").iterdir()):
    if "-candidate-" not in d.name: continue
    a = d/"artifacts"
    runjs = sorted(a.rglob("run.json"))
    if not runjs: print(d.name, "NO run.json"); continue
    rd = runjs[0].parent
    run = load(rd/"run.json") or {}
    route = run.get("route")
    drs = sorted(set(a.rglob("dependency-review*.json")))
    dr = load(drs[0]) if drs else None
    nq = hi = None
    if isinstance(dr, dict):
        qs = dr.get("questions", []); nq = len(qs); hi = sum(1 for q in qs if q.get("priority")=="high")
    draft = load(rd/"draft.json") if (rd/"draft.json").is_file() else load(rd/"input/draft.json")
    base = load(rd/"loop/baseline.json")
    elab = None
    if draft is not None and base is not None:
        try: elab = canon(draft) != canon(base)
        except Exception as e: elab = f"err"
    cyc = sorted((rd/"cycles").iterdir()) if (rd/"cycles").is_dir() else []
    cls = []
    for c in cyc:
        r = load(c/"review.json"); cmp_ = load(c/"comparison.json")
        cls.append(f"{r.get('change_class') if r else None}/{len(r.get('findings',[])) if r else None}/chg={cmp_.get('changed') if isinstance(cmp_,dict) else '?'}")
    print("\t".join(str(x) for x in (d.name, route, rd.relative_to(a), [p.name for p in drs], nq, hi, "elab="+str(elab), ";".join(cls))))
