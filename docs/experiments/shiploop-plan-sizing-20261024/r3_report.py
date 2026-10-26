#!/usr/bin/env python3
"""Tabulate the E6 downstream round (R3) per experiment and arm from the score files `experiment.py score` wrote.

    python3 -B docs/experiments/shiploop-plan-sizing-20261024/r3_report.py OUT [--json FILE]

For every E6D experiment and arm it prints n, the share of slices that delivered the item (value 1), the steps
planned, the implement packets and their seconds per step, the item minutes, the Improve children and passes, the
send-backs, the turns and the peak input tokens (each as the per-sample list and its median). Quality first, then
tokens, then time (memory eval-decision-priority). `--json` writes the same rows plus each sample's record. It reads
only score.json files.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

FIELDS = ("steps", "implement_steps", "implement_seconds_per_step", "item_minutes", "improve_children", "improve_passes",
          "send_backs", "turns", "input_peak")


def rows(out: Path) -> list[dict]:
    table = []
    for exp in sorted(p for p in out.glob("E6D-*") if p.is_dir()):
        for arm in sorted(p for p in exp.iterdir() if p.is_dir()):
            scores = [json.loads(s.read_text()) for s in sorted(arm.glob("*/score.json"), key=lambda p: int(p.parent.name))]
            if not scores:
                continue
            values = [s["value"] for s in scores if isinstance(s.get("value"), (int, float))]
            row = {"experiment": exp.name, "arm": arm.name, "n": len(scores),
                   "delivered": round(sum(values) / len(values), 2) if values else None, "samples": scores}
            for field in FIELDS:
                found = [s.get(field) for s in scores]
                numbers = [v for v in found if isinstance(v, (int, float))]
                row[field] = found
                row[field + "_median"] = statistics.median(numbers) if numbers else None
            table.append(row)
    return table


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("out", type=Path)
    p.add_argument("--json", type=Path)
    args = p.parse_args(argv)
    table = rows(args.out)
    for row in table:
        print(f"{row['experiment']} {row['arm']}: n {row['n']}, delivered {row['delivered']}; "
              + "; ".join(f"{field} {row[field]} (median {row[field + '_median']})" for field in FIELDS))
    if args.json:
        args.json.write_text(json.dumps(table, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
