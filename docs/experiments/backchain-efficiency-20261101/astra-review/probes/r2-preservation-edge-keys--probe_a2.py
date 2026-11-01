"""R2(a) end to end: freeze the honest incomplete candidate, add the invented fact in cycle 1, converge, finish."""
import json, subprocess, sys, hashlib, shutil
from pathlib import Path
D = Path(sys.argv[1]); T = D / "tree"
CLI = T / "skills/backchain/scripts/backchain.py"
RT = T / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py"
base = json.loads((T / "test/fixtures/backchain-export/confirmed.plan.json").read_text())
work = D / "work-a2"
if work.exists(): shutil.rmtree(work)
work.mkdir()
req = work / "request.md"; req.write_text("Planning only: make the CSV importer report rejected rows; release needs approval.\n")
def cli(*a):
    return subprocess.run([sys.executable, "-I", "-B", str(CLI), *a], capture_output=True, text=True, timeout=120)
inherited = json.loads(json.dumps(base)); inherited["goal_needs"].append("Release approved.")
inh = work / "inherited.json"; inh.write_text(json.dumps(inherited, indent=2))
run_dir = work / "run"
assert cli("prepare", "--run", str(run_dir), "--request", str(req), "--draft", str(inh)).returncode == 0
(run_dir / "plan.json").write_text(json.dumps(inherited, indent=2))
f = cli("freeze", "--run", str(run_dir)); print("freeze", f.returncode)
with open(run_dir / "loop/contract.json", "rb") as c:
    s = subprocess.run([sys.executable, "-B", str(RT), "start", "--receipt", str(run_dir / "loop/receipt.json")], stdin=c, capture_output=True, text=True)
print("start", s.returncode, s.stderr[-300:])
packet = json.loads(s.stdout)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ident():
    ev = run_dir / "evidence.json"
    return json.loads(ev.read_text())["cycles"][-1]["plan"]["sha256"] if ev.is_file() else sha(run_dir / "loop/baseline.json")
n = [0]
def cycle(packet, change_class, edit=None, exit_a="satisfied"):
    review = {"context_identity": "inspected", "change_class": change_class, "findings": [],
              "checks": ["traced every outcome backward"], "planning_gaps": [], "execution_blockers": [],
              "candidate_identity": ident()}
    if edit:
        p = json.loads((run_dir / "plan.json").read_text()); (run_dir / "plan.json").write_text(json.dumps(edit(p), indent=2))
    n[0] += 1; rp = work / f"review-{n[0]}.json"; rp.write_text(json.dumps(review))
    r = cli("record", "--run", str(run_dir), "--review", str(rp), "--exit", exit_a, "--continuation", "allowed")
    print(f"record {n[0]} exit={r.returncode}", r.stdout.strip().splitlines()[:2])
    rep = Path(r.stdout.splitlines()[0].removeprefix("Report: "))
    v = subprocess.run(packet["verify_script"], shell=True, executable="/bin/sh", cwd=str(run_dir), capture_output=True, text=True)
    print("  verify:", "all passed" in v.stdout)
    sub = subprocess.run(packet["done_argv"], input=rep.read_text(), capture_output=True, text=True)
    out = json.loads(sub.stdout); print("  runtime status:", out.get("status"))
    return out
def add_fact(p):
    p["initial_state"].append("Release approved."); return p
packet = cycle(packet, "material", add_fact, exit_a="unsatisfied")
packet = cycle(packet, "none")
fin = cli("finish", "--run", str(run_dir)); print("finish", fin.returncode, fin.stdout.strip()[-300:], fin.stderr.strip()[-300:])
res = json.loads((run_dir / "result.json").read_text())
print("result next_action:", repr(res["convergence"]["next_action"]), "initial_state:", res["plan"]["initial_state"])
c = cli("check", str(run_dir / "plan.json")); print(c.stderr.strip() or c.stdout.strip().splitlines()[-1])
