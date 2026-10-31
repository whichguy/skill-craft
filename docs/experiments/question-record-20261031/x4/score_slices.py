#!/usr/bin/env python3
"""Score X4's step-plan slices (README.md, "X4"; run on the Codex harness, Terra 6.1 high, all tools) with SG1's rule.

Each slice folder is ``~/e2e-runs-x4/<day>/<arm>-s<k>`` (slice.py --case tickets-assign --seed-at step-plan
--stop-after step-plan).  The step plan graded is the FIRST step-plan result the run accepted; the item base is the
execution worktree's files (tracked and untracked, not ignored) when the slice stopped, since step-plan changes no product
file.  A fault is any SG1 flag: rule A (a Proof names a test-class path the base lacks) or rule B (a path the base lacks
that only a later step declares).  Also kept: the refusals the run's trace records during step-plan (each a `check` or
`complete` with a nonzero exit).  Writes ../scores-x4-slices.json.  Usage: x4/score_slices.py [GLOB]
"""
import glob
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import SKILL_SCRIPTS  # noqa: E402
from stats import mean, permutation_p  # noqa: E402

sys.path.insert(0, str(SKILL_SCRIPTS))
import shiploop_item_scope as scope  # noqa: E402
import shiploop_store as store  # noqa: E402

TOOL = HERE.parents[1] / "sdlc-gates-20261030" / "sg1_proof_order.py"
_spec = importlib.util.spec_from_file_location("sg1_proof_order", TOOL)
sg1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sg1)


def files_at(worktree: Path) -> set[str]:
    tracked = subprocess.run(["git", "-C", str(worktree), "ls-files"], capture_output=True, text=True).stdout.split("\n")
    others = subprocess.run(["git", "-C", str(worktree), "ls-files", "--others", "--exclude-standard"],
                            capture_output=True, text=True).stdout.split("\n")
    return {path for path in tracked + others if path}


def score(folder: Path) -> dict:
    arm, sample = folder.name.split("-s")
    row = {"slice": folder.name, "arm": arm, "sample": int(sample)}
    runs = sorted(folder.glob(".shiploop-runs/*/run"))
    if not runs:
        return {**row, "parsed": False, "why": "no run folder"}
    run = runs[0]
    state = store.read_record(run / "state.md")
    first = next((h for h in state.get("history") or () if h.get("stage") == "step-plan" and h.get("outcome") == "done"),
                 None)
    plan = (state.get("accepted") or {}).get(first["action"]) if first else None
    if not isinstance(plan, dict) or not plan.get("steps"):
        return {**row, "parsed": False, "why": "no accepted step plan"}
    present = files_at(Path(state["repo"]))
    checked = sg1.check_plan(plan, scope.classify, lambda step, path: path in present)
    trace = [json.loads(line) for line in (run / "trace.jsonl").read_text().splitlines() if line.strip()]
    refusals = [t for t in trace if t.get("kind") == "command" and t.get("verb") in ("check", "complete")
                and t.get("exit") not in (0, None) and "step-plan" in (t.get("stage") or [])[:1]]
    metrics = {}
    if (folder / "metrics.json").is_file():
        metrics = json.loads((folder / "metrics.json").read_text())
    return {**row, "parsed": True, "fault": bool(checked["flags"]), "flags": checked["flags"],
            "judged": checked["judged"], "unjudged": checked["unjudged"], "steps": len(plan["steps"]),
            "proofs": [s.get("proof") for s in plan["steps"] if isinstance(s, dict)],
            "refusals": [(t.get("verb"), (t.get("error") or "")[:160]) for t in refusals],
            "active_minutes": metrics.get("active_minutes") or metrics.get("minutes")}


def main() -> None:
    pattern = sys.argv[1] if len(sys.argv) > 1 else "~/e2e-runs-x4/20261031/[AQ]-s*"
    rows = [score(Path(p)) for p in sorted(glob.glob(os.path.expanduser(pattern))) if Path(p).is_dir()]
    report = {"rows": rows, "arms": {}}
    for arm in ("A", "Q"):
        parsed = [r for r in rows if r["arm"] == arm and r["parsed"]]
        report["arms"][arm] = {"n": len([r for r in rows if r["arm"] == arm]), "parsed": len(parsed),
                               "faults": sum(r["fault"] for r in parsed),
                               "fault_rate": mean(r["fault"] for r in parsed) if parsed else None,
                               "refusals": mean(len(r["refusals"]) for r in parsed) if parsed else None}
    a = [0.0 if r["fault"] else 1.0 for r in rows if r["arm"] == "A" and r.get("parsed")]
    q = [0.0 if r["fault"] else 1.0 for r in rows if r["arm"] == "Q" and r.get("parsed")]
    report["p_one_sided_fewer_faults"] = permutation_p(a, q) if a and q else None
    (HERE.parent / "scores-x4-slices.json").write_text(json.dumps(report, indent=2) + "\n")
    for r in rows:
        print(r["slice"], "parsed" if r["parsed"] else r.get("why"), "fault" if r.get("fault") else "clean",
              [(f["step"], f["rule"], f["path"]) for f in r.get("flags") or []], "refusals", len(r.get("refusals") or []))
        for proof in r.get("proofs") or []:
            print("    proof:", (proof or "")[:160])
    print(json.dumps(report["arms"]), "p", report["p_one_sided_fewer_faults"])


if __name__ == "__main__":
    main()
