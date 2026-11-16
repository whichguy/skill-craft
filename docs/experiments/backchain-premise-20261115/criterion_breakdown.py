#!/usr/bin/env python3
"""Per-criterion reading of the 2026-11-15 Backchain value study's blind grades.

Reads ../backchain-value-20261115/evidence/grades.json (both Opus passes for all 60 attempts) and writes
criterion-breakdown.json beside this script:
- for each universal criterion (graded on 9 or more of the 10 cases): mean points per arm and model, 0 to 2;
- for each case-specific criterion (the case's planted trap or obligation): the paired difference of points
  summed over both passes, Backchain minus no skill, per model, and the tally of better, worse and tied pairs.

Points: met 2, partial 1, missed 0; `na` rows are left out, as in the study's own score. Run from any directory:
    python3 -I docs/experiments/backchain-premise-20261115/criterion_breakdown.py
"""
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
GRADES = HERE.parent / "backchain-value-20261115" / "evidence" / "grades.json"
POINTS = {"met": 2, "partial": 1, "missed": 0}
MODELS = ("grok", "sol", "sonnet")


def main() -> None:
    grades = json.loads(GRADES.read_text())["grades"]
    per_arm = collections.defaultdict(lambda: collections.defaultdict(list))
    cases_of = collections.defaultdict(set)
    paired = collections.defaultdict(dict)
    for label, passes in grades.items():
        case, arm, model = label.split("--")
        for record in passes.values():
            for row in record["rows"]:
                if row["grade"] == "na":
                    continue
                points = POINTS[row["grade"]]
                per_arm[row["id"]][f"{arm}/{model}"].append(points)
                cases_of[row["id"]].add(case)
                cell = paired[(case, model, row["id"])]
                cell[arm] = cell.get(arm, 0) + points
    universal = sorted(c for c in per_arm if len(cases_of[c]) >= 9)
    out = {"source": str(GRADES.relative_to(HERE.parent.parent.parent)), "points": POINTS,
           "universal": {}, "case_specific": {"tally": {"better": 0, "worse": 0, "tie": 0}, "differences": []}}
    for criterion in universal:
        out["universal"][criterion] = {
            key: round(sum(v) / len(v), 2) for key, v in sorted(per_arm[criterion].items())}
    for (case, model, criterion), cell in sorted(paired.items()):
        if criterion in universal or len(cell) < 2:
            continue
        diff = cell["backchain"] - cell["none"]
        out["case_specific"]["tally"]["better" if diff > 0 else "worse" if diff < 0 else "tie"] += 1
        if diff:
            out["case_specific"]["differences"].append(
                {"case": case, "model": model, "criterion": criterion, "backchain_minus_none": diff})
    (HERE / "criterion-breakdown.json").write_text(json.dumps(out, indent=1) + "\n")
    tally = out["case_specific"]["tally"]
    print(f"universal criteria: {len(universal)}; case-specific pairs: {sum(tally.values())} "
          f"(better {tally['better']}, worse {tally['worse']}, tie {tally['tie']})")


if __name__ == "__main__":
    main()
