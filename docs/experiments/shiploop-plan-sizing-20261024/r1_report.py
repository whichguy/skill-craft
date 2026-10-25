#!/usr/bin/env python3
"""Tabulate an E6 round across cases and arms from the score files `experiment.py score` wrote.

    python3 -B docs/experiments/shiploop-plan-sizing-20261024/r1_report.py OUT [--json FILE]

OUT is the experiments output folder (`experiment.py run --out`). For every E6 experiment and arm with scored samples it
prints n, the mean value (the share of samples inside the case's band), the step counts, the largest criteria and
product-file counts of any step, the samples whose slice did not pass, and the mean minutes; `--json` writes the same
rows plus every sample's record, compact enough to commit as the round's evidence. It reads only score.json files;
decisions stay with `experiment.py decide`.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path


def rows(out: Path) -> list[dict]:
    table = []
    for exp in sorted(p for p in out.glob("E6-*") if p.is_dir()):
        for arm in sorted(p for p in exp.iterdir() if p.is_dir()):
            scores = [json.loads(s.read_text()) for s in sorted(arm.glob("*/score.json"), key=lambda p: int(p.parent.name))]
            if not scores:
                continue
            values = [s["value"] for s in scores if s.get("value") is not None]
            minutes = [s["seconds"] / 60 for s in scores if s.get("seconds")]
            table.append({
                "experiment": exp.name, "arm": arm.name, "n": len(scores), "scored": len(values),
                "mean_value": round(statistics.mean(values), 2) if values else None,
                "steps": [s.get("steps") for s in scores],
                "max_criteria": [s.get("max_criteria") for s in scores],
                "max_product_files": [s.get("max_product_files") for s in scores],
                "declared_paths": [s.get("declared_paths") for s in scores],
                "slice_failed": [s["sample"] for s in scores if not s.get("slice_pass")],
                "mean_minutes": round(statistics.mean(minutes), 1) if minutes else None,
                "commit": sorted({str(s.get("commit")) for s in scores}),
                "samples": [{k: s.get(k) for k in ("sample", "value", "steps", "band", "max_criteria",
                                                   "max_product_files", "declared_paths", "joined_layers", "seconds",
                                                   "slice_pass", "action")} for s in scores]})
    return table


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    table = rows(args.out)
    print(f"{'experiment':8} {'arm':3} {'n':>2} {'mean':>5}  steps            max crit   max files  min   failed")
    for r in table:
        print(f"{r['experiment']:8} {r['arm']:3} {r['n']:>2} {str(r['mean_value']):>5}  {str(r['steps']):16} "
              f"{str(r['max_criteria']):10} {str(r['max_product_files']):10} {str(r['mean_minutes']):5} {r['slice_failed']}")
    if args.json:
        args.json.write_text(json.dumps(table, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
