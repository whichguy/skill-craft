"""Freeze the workspace records the Run Review "delivered" card reads, from four saved runs (read only), as delivered.json beside this script.

A ShipLoop run works in its own worktree on its own branch and, when it is done, returns the product to the branch it started from
(`shiploop workspace return`). Three records say what happened, each a ```shiploop-state JSON block in a markdown file under the run
directory: workspace.md (the source branch and head, the run branch, `status`), return-plan.md (every changed path with its `change`
and `disposition`) and return-receipt.md (`kind`, `status`, and the source head before and after). The runs are a returned one, a returned
one with tests and a README, a blocked one and a stopped one, so the tests can read a product that was merged back and two that were not.
Only the keys the card reads are kept; the fingerprints and the .shiploop-improve evidence lists are dropped.

    python3 docs/experiments/run-review-r23-20261009/collect_delivered.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = Path("/Users/dadleet/e2e-runs")
SAVED = ["20261009/s6-after-spec", "20261008/r3-checkers-sonnet", "20261008/r1-battleship-grok-none", "20261008/r3-battleship-grok-none"]


def state(path: Path):
    if not path.is_file():
        return None
    match = re.search(r"```shiploop-state\n(.*?)\n```", path.read_text(), re.S)
    return json.loads(match.group(1)) if match else None


def main() -> int:
    found = {}
    for name in SAVED:
        out = RUNS / name
        result = json.loads((out / "result.json").read_text())
        run_dir = Path((result.get("shiploop") or {}).get("run_dir") or "")
        root = run_dir.parent if run_dir.name == "run" else run_dir
        ws, plan, receipt = (state(root / f) for f in ("workspace.md", "return-plan.md", "return-receipt.md"))
        record = {"workspace": None, "plan": None, "receipt": None}
        if ws:
            record["workspace"] = {k: ws.get(k) for k in ("status", "source_branch", "source_head", "branch", "baseline_commit", "start_clean")}
        if plan:
            record["plan"] = {"status": plan.get("status"), "return_policy": plan.get("return_policy"),
                              "paths": [{k: p.get(k) for k in ("path", "change", "disposition", "in_history")}
                                        for p in plan.get("paths") or [] if not str(p.get("path", "")).startswith(".shiploop-improve/")]}
        if receipt:
            record["receipt"] = {k: receipt.get(k) for k in ("kind", "status", "source_before", "expected_source")}
        found[name] = record
    (HERE / "delivered.json").write_text(json.dumps(found, indent=1, sort_keys=True) + "\n")
    for name, r in found.items():
        print(name, "workspace", (r["workspace"] or {}).get("status"), "| plan paths", len((r["plan"] or {}).get("paths", [])), "| receipt", (r["receipt"] or {}).get("kind"), (r["receipt"] or {}).get("status"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
