"""R2(a): legacy inherited boundary does not enforce goal, initial_state, or origin."""
import json, subprocess, sys
from pathlib import Path
D = Path(sys.argv[1]); T = D / "tree"
CLI = T / "skills/backchain/scripts/backchain.py"
base = json.loads((T / "test/fixtures/backchain-export/confirmed.plan.json").read_text())
work = D / "work-a"
work.mkdir(exist_ok=True)
req = work / "request.md"; req.write_text("Planning only: make the CSV importer report rejected rows; release needs approval.\n")

def cli(*a):
    return subprocess.run([sys.executable, "-I", "-B", str(CLI), *a], capture_output=True, text=True, timeout=120)

# Inherited plan: an extra goal need nobody produces -> valid but incomplete.
inherited = json.loads(json.dumps(base))
inherited["goal_needs"] = inherited["goal_needs"] + ["Release approved."]
inh_path = work / "inherited.json"; inh_path.write_text(json.dumps(inherited, indent=2))
r = cli("check", str(inh_path)); print("inherited check:", r.returncode, r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr)
print("  completion:", json.loads(r.stdout.split("\n", 1)[0]) if False else None)

def mutate(name, fn):
    run_dir = work / name
    if run_dir.exists():
        import shutil; shutil.rmtree(run_dir)
    p = cli("prepare", "--run", str(run_dir), "--request", str(req), "--draft", str(inh_path))
    assert p.returncode == 0, p.stderr
    cand = fn(json.loads(json.dumps(inherited)))
    (run_dir / "plan.json").write_text(json.dumps(cand, indent=2))
    f = cli("freeze", "--run", str(run_dir))
    first = f.stdout.splitlines()[0] if f.stdout else ""
    print(f"[{name}] freeze exit={f.returncode} first-line={first!r}")
    if f.returncode != 0:
        print("   ", f.stdout.strip()[:600])
    c = cli("check", str(run_dir / "plan.json"))
    print(f"[{name}] check exit={c.returncode}: {c.stderr.strip() or c.stdout.strip().splitlines()[-1]}")
    e = cli("export", str(run_dir / "plan.json"), "--out", str(work / f"{name}.graph.json"))
    print(f"[{name}] export exit={e.returncode} {(e.stderr or '').strip()[:200]}")
    return run_dir

def invented_fact(p):
    p["initial_state"].append("Release approved.")
    return p

def changed_goal(p):
    p["goal"] = "The CSV importer is deleted."
    return p

def changed_origin(p):
    p["steps"][1]["origin"] = "discovered"
    p["steps"][1]["produces"].append("Release approved.")  # keep it complete-able? no: separate effect
    return p

def changed_origin_only(p):
    p["steps"][1]["origin"] = "discovered"
    return p

def control_edge_removed(p):
    p["steps"][1]["inputs"] = p["steps"][1]["inputs"][:1]
    return p

def control_goal_needs(p):
    p["goal_needs"] = p["goal_needs"][:1]
    return p

for name, fn in (("invented-fact", invented_fact), ("changed-goal", changed_goal),
                 ("changed-origin-only", changed_origin_only),
                 ("control-edge-removed", control_edge_removed), ("control-goal-needs-dropped", control_goal_needs)):
    mutate(name, fn)
