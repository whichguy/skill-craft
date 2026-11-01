#!/usr/bin/env python3
"""X-A's registered measure (README.md): per sample of step-plan/proof-runs-focused-suite, whether the step plan has a Proof
that needs a test not yet written (proofscore form 1 or form 2), the focused-ID shortage, refusals and the oracle's verdict.

    python3 -I score_xa.py B=~/e2e-runs-sp/20261101/round2/xa-B T=~/e2e-runs-sp/20261101/round2/xa-T --out xa_scores.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import proofscore  # noqa: E402
import samples  # noqa: E402
sys.path.insert(0, str(samples.ROOT / "skills/shiploop/scripts"))
import shiploop_test_loop as test_loop  # noqa: E402

SCENARIO = "step-plan/proof-runs-focused-suite"


def score(arm: str, root: Path) -> list[dict]:
    rows = []
    for folder in samples.folders(root, SCENARIO):
        read = samples.read(SCENARIO, folder)
        row = {"arm": arm, "sample": read["sample"], "ran": read["ran"], "error": read["error"]}
        bundle = read["bundle"]
        if bundle is not None:
            plan = bundle.result or {}
            base = samples.tree_files(bundle.seed_tree)
            found = proofscore.classify(plan, base, base)
            row.update({
                "outcome": plan.get("outcome"),
                "form1": found["form1"], "form2": found["form2"],
                "faulty": bool(found["form1"] or found["form2"]),
                "proofs": {str(step.get("id")): step.get("proof") for step in plan.get("steps") or () if isinstance(step, dict)},
                "steps": len(plan.get("steps") or ()),
                "criteria_without_ids": test_loop.criteria_without_ids(plan.get("test_commands") or [], plan.get("criteria") or []),
                "focused_commands": [c.get("command") for c in plan.get("test_commands") or () if isinstance(c, dict) and c.get("suite") == "focused"],
                "refusals": samples.refusals(bundle.trace),
                "oracle_pass": (read["verdict"] or {}).get("pass"),
                "oracle_ids": (read["verdict"] or {}).get("ids"),
            })
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("arms", nargs="+", help="ARM=RESULTS_ROOT")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    rows = []
    for spec in args.arms:
        arm, _, root = spec.partition("=")
        rows += score(arm, Path(root).expanduser())
    args.out.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    for arm in dict.fromkeys(row["arm"] for row in rows):
        mine = [row for row in rows if row["arm"] == arm]
        ran = [row for row in mine if row.get("outcome") is not None]
        print(f"{arm}: {len(mine)} samples, {len(ran)} scored; faulty {sum(r['faulty'] for r in ran)} "
              f"(form 1 {sum(bool(r['form1']) for r in ran)}, form 2 {sum(bool(r['form2']) for r in ran)}); "
              f"short of IDs {sum(bool(r['criteria_without_ids']) for r in ran)}; not done {sum(r['outcome'] != 'done' for r in ran)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
