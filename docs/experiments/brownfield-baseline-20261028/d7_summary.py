"""D7 evidence: one compact record per E2E run of the brownfield cases, from the run folders the harness wrote.

    python3 d7_summary.py OUT_JSON RUN_DIR [RUN_DIR ...]

Per run: the case, its verdicts, every visible and held-out check with its grade, the planning window split into
authoring and Improve, each stage's minutes, the refusals by kind, and the size of the knowledge files the run
committed. Reads result.json, metrics.json and work/docs/shiploop/ only; the product repositories stay out of Git
(they are disposable probes).
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

CASES = Path(__file__).resolve().parents[3] / "test" / "shiploop_e2e" / "cases.json"
KINDS = [("size limit", r"characters|the limit is|keep it within"),
         ("Improve protocol", r"no draft to check|Run the improve skill"),
         ("lint action", r"is not the current action"),
         ("result format", r"headline must|invalid shiploop-state JSON|red_na|write the commit message with a file tool"),
         ("quality gate", r"mutation check|expectation E\d+ is absent|evidence_refs cite|Run this stage's checks again"
                          r"|every primary requirement")]


def kind(failure: dict) -> str:
    text = json.dumps(failure)
    return next((name for name, pattern in KINDS if re.search(pattern, text)), "other protocol")


def summary(run: Path, cases: dict) -> dict:
    result = json.loads((run / "result.json").read_text())
    metrics = json.loads((run / "metrics.json").read_text())
    case = result.get("case") or {}
    name = case.get("name") if isinstance(case, dict) else case
    grades = {row["id"]: row.get("grade") for row in
              ((cases.get(name) or {}).get("quality") or {}).get("acceptance", {}).get("checks", [])}
    acceptance = ((result.get("quality") or {}).get("acceptance") or {})
    planning = (metrics.get("planning") or {}).get("stages") or []
    stages = collections.defaultdict(lambda: [0, 0.0])
    for row in metrics.get("stages") or []:
        if not row.get("incomplete"):
            stages[row["stage"]][0] += 1
            stages[row["stage"]][1] += (row.get("seconds") or 0) / 60
    home = run / "work" / "docs" / "shiploop"
    span = result.get("span") or {}
    return {
        "run": run.name,
        "case": name,
        "outcome": result.get("outcome_class"),
        "pass": result.get("pass"),
        "committed": (result.get("committed") or {}).get("pass"),
        "minutes": round(((span.get("ended") or 0) - (span.get("started") or 0)) / 60, 1),
        "visible_checks": [{"pass": c.get("pass") if "pass" in c else c.get("returncode") == 0,
                            "command": str(c.get("command") or c.get("name"))[:160]} for c in result.get("checks") or []],
        "held_out": [{"id": row["id"], "grade": grades.get(row["id"]), "pass": row.get("pass")}
                     for row in acceptance.get("checks") or []],
        "planning": {
            "minutes": round(sum((r.get("seconds") or 0) for r in planning) / 60, 1),
            "improve_minutes": round(sum((r.get("improve_seconds") or 0) for r in planning) / 60, 1),
            "stages": [{"stage": r["stage"], "minutes": round((r.get("seconds") or 0) / 60, 1),
                        "improve_minutes": round((r.get("improve_seconds") or 0) / 60, 1)} for r in planning],
        },
        "stages": {stage: {"count": count, "minutes": round(minutes, 1)} for stage, (count, minutes) in stages.items()},
        "refusals": dict(collections.Counter(kind(f) for f in metrics.get("shiploop_failures") or [])),
        "knowledge_bytes": {path.name: path.stat().st_size for path in sorted(home.glob("*.md"))} if home.is_dir() else {},
    }


def main(out: str, runs: list[str]) -> None:
    cases = json.loads(CASES.read_text())
    rows = [summary(Path(run).expanduser(), cases) for run in runs]
    Path(out).write_text(json.dumps(rows, indent=1) + "\n")
    for row in rows:
        held = row["held_out"]
        print(f"{row['case']:18s} {row['outcome']:5s} held-out {sum(h['pass'] for h in held)}/{len(held)} "
              f"planning {row['planning']['minutes']} min (Improve {row['planning']['improve_minutes']}) "
              f"run {row['minutes']} min refusals {sum(row['refusals'].values())} {row['refusals']}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
