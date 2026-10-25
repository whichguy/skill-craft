#!/usr/bin/env python3
"""Did the step-plan Improve change what E6 scores? Compare each sample's plan before and after its Improve child.

    python3 -B docs/experiments/shiploop-plan-sizing-20261024/improve_drift.py OUT [--json FILE]

E6 scores a slice's last accepted step-plan result, which is the plan after the stage's Improve child (a final result
replaces the submitted one). The submitted plan survives as the Improve record's `seed_result` in the run's state.md.
For every finished sample under OUT this prints the step counts before and after Improve, the largest step's criteria
characters before and after, and the samples whose final plan has a step over the navigator's 1,200-character
criteria limit. It reads run folders only.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
from evaluators import common  # noqa: E402

CRITERIA_LIMIT = 1200  # shiploop_navigator.STEP_CRITERIA_LIMIT at 9ed4ec24 and main 288075c9


def largest_step(result: dict) -> int:
    texts = {c.get("id"): c.get("text") or "" for c in result.get("criteria") or []}
    return max([sum(len(texts.get(c, "")) for c in step.get("criteria") or []) for step in result.get("steps") or []] or [0])


def seed(run: Path) -> dict | None:
    state = common.read_block(run / "state.md") or {}
    for record in (state.get("improve_results") or {}).values():
        found = record.get("seed_result") if isinstance(record, dict) else None
        if isinstance(found, dict) and "steps" in found:
            return found
    return None


def rows(out: Path) -> list[dict]:
    table = []
    for marker in sorted(out.glob("E6-*/*/*/slice/slice-result.json")):
        folder = marker.parent
        run = common.run_dir(folder)
        plans = [r for r in common.results(run, "step-plan") if (r.get("result") or {}).get("outcome") == "done"]
        if not plans:
            continue
        final, before = plans[-1]["result"], seed(run)
        table.append({"experiment": folder.parts[-4], "arm": folder.parts[-3], "sample": int(folder.parts[-2]),
                      "steps_before": len(before["steps"]) if before else None, "steps_after": len(final["steps"]),
                      "largest_before": largest_step(before) if before else None, "largest_after": largest_step(final)})
    return table


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("out", type=Path)
    p.add_argument("--json", type=Path)
    args = p.parse_args(argv)
    table = rows(args.out)
    seeded = [r for r in table if r["steps_before"] is not None]
    changed = [r for r in seeded if r["steps_before"] != r["steps_after"]]
    growth = [r["largest_after"] - r["largest_before"] for r in seeded]
    over = [r for r in table if r["largest_after"] > CRITERIA_LIMIT]
    print(f"{len(table)} samples, {len(seeded)} with the submitted plan on record; Improve changed the step count in "
          f"{len(changed)}")
    for r in changed:
        print(f"  {r['experiment']} {r['arm']} {r['sample']}: {r['steps_before']} -> {r['steps_after']} steps")
    if growth:
        print(f"largest step's criteria characters through Improve: median {statistics.median(growth):+}, "
              f"max {max(growth):+}, grew in {sum(g > 0 for g in growth)} of {len(growth)}")
    print(f"final plans with a step over {CRITERIA_LIMIT:,} criteria characters: {len(over)}")
    for r in over:
        print(f"  {r['experiment']} {r['arm']} {r['sample']}: {r['largest_before']} -> {r['largest_after']}")
    if args.json:
        args.json.write_text(json.dumps(table, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
