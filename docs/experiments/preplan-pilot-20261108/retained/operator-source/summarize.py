"""Descriptive results, retaining judge disagreement and scope deviations."""
from pathlib import Path
from collections import Counter
import json
import statistics

from analyze import document

OP = Path(__file__).resolve().parent
manifest = json.loads((OP / "manifest.json").read_text())
analysis = json.loads((OP / "analysis.json").read_text())
scope = json.loads((OP / "scope-audit-findings.json").read_text())
deviations = {entry["sample"] for entry in scope["findings"]}
indexed = {row["id"]: row for row in analysis["rows"]}
pairs = []
for pair in analysis["pairs"]:
    name = f'{pair["case"]}-{pair["rep"]}'
    directory = OP / "pairs" / name
    if not (directory / "judge.json").exists():
        continue
    mapping = json.loads((directory / "mapping.json").read_text())
    judgment = document(json.loads((directory / "judge.json").read_text())["text"])
    outcome = judgment["final_quality"]
    if outcome in ("A_better", "B_better"):
        outcome = indexed[mapping[outcome[0]]]["arm"] + "_better"
    rows = {arm: indexed[name] for arm, name in pair["ids"].items()}
    times = {}
    for arm, row in rows.items():
        plan = next((s for s in row.get("stages", []) if s["stage"] == "plan"), {})
        times[arm] = {"host_seconds": row.get("host_seconds"), "plan_including_improve_seconds": plan.get("seconds")}
    pairs.append({
        "id": name,
        "case": pair["case"],
        "rep": pair["rep"],
        "samples": pair["ids"],
        "outcome": outcome,
        "clean_comparison_eligible": not (set(pair["ids"].values()) & deviations)
        and all(row.get("completion") for row in rows.values()),
        "scope_deviation_samples": sorted(set(pair["ids"].values()) & deviations),
        "times": times,
        "judgment": judgment,
        "mapping": mapping,
    })


def aggregate(selected):
    summary = {"pairs": len(selected), "outcomes": dict(Counter(p["outcome"] for p in selected)), "timing": {}}
    for field in ("host_seconds", "plan_including_improve_seconds"):
        values = {
            arm: [p["times"][arm][field] for p in selected if p["times"][arm][field] is not None]
            for arm in ("current", "early")
        }
        deltas = [p["times"]["early"][field] - p["times"]["current"][field]
                  for p in selected if all(p["times"][arm][field] is not None for arm in ("current", "early"))]
        summary["timing"][field] = {
            arm: {"n": len(v), "mean": statistics.mean(v) if v else None,
                  "median": statistics.median(v) if v else None,
                  "minimum": min(v) if v else None, "maximum": max(v) if v else None}
            for arm, v in values.items()
        }
        summary["timing"][field]["paired_early_minus_current"] = {
            "n": len(deltas), "mean": statistics.mean(deltas) if deltas else None,
            "median": statistics.median(deltas) if deltas else None,
        }
    return summary


rows = []
for row in analysis["rows"]:
    rows.append({k: row.get(k) for k in (
        "id", "case", "rep", "arm", "cohort", "completion", "plugin_identity_matches",
        "score", "possible", "host_seconds", "tokens", "criterion_set_valid",
        "quote_failures", "false_readiness_count", "material_rework_count",
        "unnecessary_investigation_count", "access_audit_findings",
    )})
result = {
    "status": "complete" if len(pairs) == 8 and all(row["completion"] for row in rows) else "partial",
    "scope": "Four constructed planning cases, two repetitions per arm; no significance test or default promotion.",
    "baseline": manifest["registration"]["baseline"],
    "source_freeze": manifest["source_commit"],
    "models": {"subject": manifest["registration"]["subject"], "judge": manifest["registration"]["judge"]},
    "all_pairs": aggregate(pairs),
    "clean_comparison_subset": aggregate([p for p in pairs if p["clean_comparison_eligible"]]),
    "scope_findings": scope["findings"],
    "pairs": pairs,
    "subjects": rows,
    "interpretation_limits": [
        "Pairwise judgments prioritize consequential final quality over raw rubric sums; retained corrections can qualify individual grades.",
        "A tie means no demonstrated final-quality advantage in this record, not statistical equivalence or proof of no effect.",
        "Counts of unnecessary investigation include extra reads or structural checks; they are not counts of experiments or material harms.",
        "Earlier evidence may originate in the shared test-strategy stage before treatment; do not attribute that to the early plan duty.",
        "Host and plan-stage times are descriptive under shared provider load and fixed four-subject cohorts; no generalized speed or monetary-cost claim.",
        "Missing subject terminal token usage remains null; peak input context is not total token consumption.",
        "Synthetic accepted prelude, planning-only boundary, one judge family and small calibration limit generalization.",
        "Scope-deviation pairs remain visible and are excluded from the clean comparative subset; no result-driven reruns.",
    ],
}
(OP / "results.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: result[k] for k in ("status", "all_pairs", "clean_comparison_subset")}, indent=2))
