"""R1 probe: a caller-backed finish over a genuine prepare/freeze/start/record/verify/submit loop (RunTests helpers),
then finish --review with an incomplete source review. Run with python3 -I probe_r1.py TREE."""
import importlib.util
import json
import sys
from pathlib import Path

tree = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("bt", tree / "test/backchain-toolkit.test.py")
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)
print("CLI under test:", bt.CLI)

t = bt.RunTests("test_a_source_aware_run_returns_plan_and_review")
t.setUp()
bounds = {"provisional_step_ids": [], "provisional_edge_keys": [], "allow_new_steps": False,
          "allow_new_edges": False, "protected_step_ids": [], "protected_edge_keys": [], "protected_facts": [],
          "running_or_completed_step_ids": []}
run_dir, frozen = t.caller_run(lambda plan: plan, "probe", bounds)
assert frozen.returncode == 0, frozen.stdout + frozen.stderr
final = t.cycle(run_dir, t.start(run_dir), bt.assessment("none"))
print("loop terminal status:", final["status"])

stale = {"id": "F-1", "material": True, "kind": "stale_source", "source_ids": ["SRC-1"], "candidate_refs": ["S2"],
         "recommended_change": ""}
incomplete = {"source_review_status": "incomplete"}


def without(key, **changes):
    review = t.final_review(run_dir, **changes)
    review.pop(key)
    return review


cases = [
    ("A control: complete, no findings", t.final_review(run_dir)),
    ("B incomplete + material stale_source, planning_gaps []",
     t.final_review(run_dir, coverage=incomplete, findings=[stale])),
    ("C incomplete + material stale_source, planning_gaps ABSENT",
     without("planning_gaps", coverage=incomplete, findings=[stale])),
    ("D incomplete + material stale_source, planning_gaps null",
     t.final_review(run_dir, coverage=incomplete, findings=[stale], planning_gaps=None)),
    ("E incomplete + unresolved + disposition unresolved",
     t.final_review(run_dir, coverage=incomplete, findings=[stale], unresolved=["normative SRC-1 is stale"],
                    candidate={"output_sha256": bt.file_digest(run_dir / "plan.json"), "disposition": "unresolved"})),
    ("F incomplete, planning_gaps ['missing normative source'] (gap honoured?)",
     t.final_review(run_dir, coverage=incomplete, findings=[stale], planning_gaps=["missing normative source"])),
    ("G planning_gaps a bare string", t.final_review(run_dir, planning_gaps="missing normative source")),
    ("H planning_gaps a dict", t.final_review(run_dir, planning_gaps={"gap": 1})),
    ("I planning_gaps empty string", t.final_review(run_dir, planning_gaps="")),
    ("J complete + material finding (no gap)", t.final_review(run_dir, findings=[stale])),
]
path = t.base / "review-under-test.json"
for label, review in cases:
    result_file = run_dir / "result.json"
    if result_file.exists():
        result_file.unlink()
    path.write_text(json.dumps(review))
    done = bt.run("finish", "--run", str(run_dir), "--review", str(path))
    status = json.loads(result_file.read_text())["status"] if result_file.exists() else "(no result.json)"
    hint = " export " in done.stdout
    print(f"--- {label}\n    exit={done.returncode} result.status={status} export_hint={hint}")
    print("    stdout:", done.stdout.strip().replace("\n", " | ")[:400])
    if done.stderr.strip():
        print("    stderr tail:", done.stderr.strip().splitlines()[-1][:300])
    if result_file.exists():
        res = json.loads(result_file.read_text())
        print("    review.coverage:", res["review"]["coverage"], "convergence.planning_gaps:",
              res["review"]["convergence"]["planning_gaps"])
