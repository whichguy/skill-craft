#!/usr/bin/env python3
"""R7 probe: can a plan edited after the last recorded review be exported? What does finish's hint export?

Runs only against the archived tree at f5fb7d64 (argv[1]); every file goes under argv[2].
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

TREE = Path(sys.argv[1]).resolve()
WORK = Path(sys.argv[2]).resolve()
CLI = TREE / "skills/backchain/scripts/backchain.py"
LOOP = TREE / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py"
CONFIRMED = TREE / "test/fixtures/backchain-export/confirmed.plan.json"


def run(*args):
    return subprocess.run([sys.executable, "-I", "-B", str(CLI), *args], capture_output=True, text=True,
                          cwd=str(WORK), timeout=120)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def without_one_edge(plan):
    edited = json.loads(json.dumps(plan))
    edited["steps"][1]["inputs"] = edited["steps"][1]["inputs"][:1]
    return edited


def assessment(identity, change_class="none", gaps=()):
    return {"context_identity": "inspected", "change_class": change_class, "candidate_identity": identity,
            "findings": [], "checks": ["traced every outcome backward"], "planning_gaps": list(gaps),
            "execution_blockers": []}


def converged_run(name, gaps=()):
    run_dir = WORK / name
    request = WORK / f"{name}-request.md"
    request.write_text("Planning only: make the CSV importer report rejected rows with line numbers.\n")
    p = run("prepare", "--run", str(run_dir), "--request", str(request))
    assert p.returncode == 0, p.stderr
    text = CONFIRMED.read_text()
    (run_dir / "draft.json").write_text(text)
    (run_dir / "plan.json").write_text(text)
    f = run("freeze", "--run", str(run_dir))
    assert f.returncode == 0, f.stdout + f.stderr
    with open(run_dir / "loop/contract.json", "rb") as contract:
        s = subprocess.run([sys.executable, "-B", str(LOOP), "start", "--receipt", str(run_dir / "loop/receipt.json")],
                           stdin=contract, capture_output=True, text=True, timeout=60)
    assert s.returncode == 0, s.stderr
    packet = json.loads(s.stdout)
    review = WORK / f"{name}-assessment.json"
    review.write_text(json.dumps(assessment(digest(run_dir / "loop/baseline.json"), gaps=gaps)))
    exit_assessment = "unsatisfied" if gaps else "satisfied"
    continuation = "blocked" if gaps else "allowed"
    r = run("record", "--run", str(run_dir), "--review", str(review), "--exit", exit_assessment,
            "--continuation", continuation)
    assert r.returncode == 0, r.stdout + r.stderr
    report = Path(r.stdout.splitlines()[0].removeprefix("Report: "))
    v = subprocess.run(packet["verify_script"], shell=True, executable="/bin/sh", cwd=str(run_dir),
                       capture_output=True, text=True, timeout=120)
    d = subprocess.run(packet["done_argv"], input=report.read_text(), capture_output=True, text=True, timeout=60)
    assert d.returncode == 0, d.stderr
    return run_dir, json.loads(d.stdout), v


out = {}

# A: converged run, then the working plan.json is edited after finish, then the hint's export is run.
run_dir, final, _ = converged_run("A")
fin = run("finish", "--run", str(run_dir))
result = json.loads((run_dir / "result.json").read_text())
hint = [line for line in fin.stdout.splitlines() if "export" in line]
plan_path = run_dir / "plan.json"
plan_path.write_text(json.dumps(without_one_edge(json.loads(plan_path.read_text())), indent=2))
exp = run("export", str(plan_path))
graph_out = json.loads(exp.stdout) if exp.returncode == 0 else None
ver = run("verify", "--run", str(run_dir))
out["A_after_finish_edit"] = {
    "loop_status": final["status"], "finish_rc": fin.returncode, "finish_stdout": fin.stdout.strip(),
    "result_status": result["status"], "hint_lines": hint,
    "export_rc": exp.returncode, "export_stderr": exp.stderr.strip()[:300],
    "export_plan_sha256": graph_out and graph_out["source"]["plan_sha256"],
    "result_output_sha256": result["convergence"]["candidate"]["output_sha256"],
    "exported_S2_deps": graph_out and [s["deps"] for s in graph_out["steps"] if s["id"] == "S2"],
    "result_S2_inputs_from": [i["from"] for s in result["plan"]["steps"] if s["id"] == "S2" for i in s["inputs"]],
    "verify_rc": ver.returncode, "verify": json.loads(ver.stdout),
}
# Does export accept result.json (the accepted artifact) instead?
exp_result = run("export", str(run_dir / "result.json"))
out["A_export_result_json"] = {"rc": exp_result.returncode, "stderr": exp_result.stderr.strip()[:300]}

# B: incomplete run (planning gap, loop stopped blocked). Export of the working plan still succeeds.
run_dir_b, final_b, _ = converged_run("B", gaps=["a normative source is missing"])
fin_b = run("finish", "--run", str(run_dir_b))
exp_b = run("export", str(run_dir_b / "plan.json"))
out["B_incomplete_run"] = {"loop_status": final_b["status"], "finish_rc": fin_b.returncode,
                           "finish_stdout": fin_b.stdout.strip()[-300:],
                           "result_status": json.loads((run_dir_b / "result.json").read_text())["status"],
                           "export_rc": exp_b.returncode}

# C: edit between record/submit and finish: finish refuses convergence, export still succeeds.
run_dir_c, final_c, _ = converged_run("C")
pc = run_dir_c / "plan.json"
pc.write_text(json.dumps(without_one_edge(json.loads(pc.read_text())), indent=2))
fin_c = run("finish", "--run", str(run_dir_c))
exp_c = run("export", str(pc))
out["C_edit_before_finish"] = {"loop_status": final_c["status"], "finish_rc": fin_c.returncode,
                               "finish_stdout": fin_c.stdout.strip()[-400:], "export_rc": exp_c.returncode}

print(json.dumps(out, indent=2))
