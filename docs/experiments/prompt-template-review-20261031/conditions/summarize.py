#!/usr/bin/env python3
"""Pool the per-run condition test (plan.md) into one summary: counts per run, the pooled survival rate with and
without inferred conditions, and every survivor with its kind, quote, claiming case and reason. Writes
``summary.json`` beside this file and prints a table. Usage: ``python3 summarize.py``.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = {  # key: (subject, delivery)
    "codex-r2-user-listing": ("Codex Terra", "brownfield"),
    "claude-csv-report": ("Claude", "greenfield"),
    "bf-ds-ticket-assignment": ("DeepSeek flash", "brownfield"),
    "grok-web-battleship": ("Grok", "greenfield"),
    "v2170-ds-battleship": ("DeepSeek flash", "greenfield"),
}
# Conditions the worker inferred from two clauses rather than read from one (bf-ds report, R-6.7 and R-8.15).
INFERRED = {("bf-ds-ticket-assignment", "R-6.7"), ("bf-ds-ticket-assignment", "R-8.15")}
# Survivors that break the main outcome the request asks for (parent's reading, predeclared rule's "core outcome").
CORE = {("grok-web-battleship", ident) for ident in ("R-3.8", "R-3.9", "R-3.10", "R-3.13")} | {
    ("claude-csv-report", "R-3.6"), ("claude-csv-report", "R-3.8"), ("v2170-ds-battleship", "R-3.13")}


def absent(row: dict) -> bool:
    claim = str(row.get("claimed_by") or "none").strip().lower()
    return claim.startswith("none") or claim in ("", "-", "n/a") or "absent" in str(row.get("why_survived", ""))[:12].lower()


def main() -> int:
    runs, survivors = [], []
    for key, (subject, delivery) in RUNS.items():
        rows = json.loads((HERE / key / "results.json").read_text())["conditions"]
        witnessed = [row for row in rows if row.get("verdict") in ("killed", "survived")]
        lived = [row for row in witnessed if row["verdict"] == "survived"]
        requirements = sorted({row["requirement"] for row in witnessed}, key=lambda r: int(r.split("-")[1]))
        hit = sorted({row["requirement"] for row in lived}, key=lambda r: int(r.split("-")[1]))
        runs.append({"run": key, "subject": subject, "delivery": delivery, "witnessed": len(witnessed),
                     "killed": len(witnessed) - len(lived), "survived": len(lived),
                     "survival": round(len(lived) / len(witnessed), 3),
                     "requirements": len(requirements), "requirements_with_survivor": len(hit),
                     "excluded": sum(row.get("verdict") == "excluded" for row in rows),
                     "unwitnessed": sum(row.get("verdict") == "unwitnessed" for row in rows)})
        for row in lived:
            survivors.append({"run": key, "id": row["id"], "kind": row.get("kind"), "quote": row.get("quote"),
                              "claimed_by": row.get("claimed_by"), "absent": absent(row),
                              "inferred": (key, row["id"]) in INFERRED, "core": (key, row["id"]) in CORE,
                              "why": row.get("why_survived"), "owning_step": row.get("owning_step")})
    witnessed = sum(run["witnessed"] for run in runs)
    survived = sum(run["survived"] for run in runs)
    strict = [row for row in survivors if not row["inferred"]]
    pooled = {"witnessed": witnessed, "survived": survived, "survival": round(survived / witnessed, 3),
              "survival_without_inferred": round(len(strict) / (witnessed - len(INFERRED)), 3),
              "absent": sum(row["absent"] for row in survivors), "weak": sum(not row["absent"] for row in survivors),
              "core": sum(row["core"] for row in survivors),
              "kinds": {kind: sum(row["kind"] == kind for row in survivors)
                        for kind in sorted({row["kind"] for row in survivors})}}
    (HERE / "summary.json").write_text(json.dumps({"runs": runs, "pooled": pooled, "survivors": survivors},
                                                  indent=1) + "\n")
    print(f"{'run':26} {'subject':15} {'wit':>4} {'kill':>4} {'surv':>4} {'rate':>6}  req-with-survivor")
    for run in runs:
        print(f"{run['run']:26} {run['subject']:15} {run['witnessed']:4} {run['killed']:4} {run['survived']:4} "
              f"{run['survival']:6.1%}  {run['requirements_with_survivor']}/{run['requirements']}")
    print(json.dumps(pooled))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
