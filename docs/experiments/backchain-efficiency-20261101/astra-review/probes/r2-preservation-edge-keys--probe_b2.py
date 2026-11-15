"""R2(b) through prepare + freeze with a caller packet (source-aware route)."""
import json, sys, copy, subprocess, shutil
from pathlib import Path
D = Path(sys.argv[1]); T = D / "tree"
CLI = T / "skills/backchain/scripts/backchain.py"
sys.path.insert(0, str(T / "skills/backchain/scripts"))
import backchain_graph as graph
work = D / "work-b2"
if work.exists(): shutil.rmtree(work)
work.mkdir()
req = work / "request.md"; req.write_text("Planning only: repair the plan within the caller's bounds.\n")
def cli(*a): return subprocess.run([sys.executable, "-I", "-B", str(CLI), *a], capture_output=True, text=True, timeout=120)
def step(i, produces, inputs, origin="seed"):
    return {"id": i, "statement": produces[0], "produces": produces, "inputs": inputs, "origin": origin}
def plan(steps): return graph.package({"goal": "Everything is done.", "initial_state": ["Fact X."], "steps": steps, "parallel_groups": [], "unresolved": []})
def go(name, inh, cand, bounds):
    (work / f"{name}-inh.json").write_text(json.dumps(inh))
    (work / f"{name}-caller.json").write_text(json.dumps({"interface": "backchain-caller/v1", "action": "repair", "stage": "revise",
        "action_id": name, "owner": "probe", "edit_bounds": bounds}))
    rd = work / name
    p = cli("prepare", "--run", str(rd), "--request", str(req), "--draft", str(work / f"{name}-inh.json"), "--caller", str(work / f"{name}-caller.json"))
    assert p.returncode == 0, p.stderr
    (rd / "plan.json").write_text(json.dumps(cand))
    f = cli("freeze", "--run", str(rd))
    print(f"[{name}] freeze exit={f.returncode}", "" if f.returncode == 0 else f.stdout.strip().replace("\n", " ")[:300])
for ident in ("A<-B", "C"):
    inh = plan([step("A", ["A done."], []), step(ident, ["AB done."], []), step("S0", ["S0 done."], [])])
    cand = copy.deepcopy(inh); cand["steps"][1]["inputs"].append({"need": "S0 done.", "from": "S0"}); cand = graph.package(cand)
    go(f"consumer-{ident.replace('<-','_from_')}", inh, cand, {"provisional_step_ids": ["A"], "allow_new_edges": True})
for ident in ("null", "N"):
    inh = plan([step(ident, ["N done."], []), step("X", ["X done."], [{"need": "Fact X.", "from": None}])])
    cand = copy.deepcopy(inh); cand["steps"][1]["inputs"] = [{"need": "N done.", "from": ident}]; cand = graph.package(cand)
    go(f"supplier-{ident}", inh, cand, {"provisional_step_ids": ["X"], "provisional_edge_keys": ["X<-null"], "allow_new_edges": False})
