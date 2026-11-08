#!/usr/bin/env python3
"""Replay planning-score arithmetic offline; evidence validity is an input, not a claim."""
import argparse
import json
import math
from pathlib import Path
import sys

DIMENSIONS = ("acceptance_actionability", "evidence_grounding", "prerequisite_handoff", "verification_closure")
RESOURCES = ("cached_input_tokens", "uncached_input_tokens", "output_tokens", "seconds")
STATUSES = {"missed": 0, "partial": 1, "fulfilled": 2, "unknown": None, "justified_block": None}


def contrast(current, candidate):
    if len(current) != 2 or len(candidate) != 2 or any(x is None for x in current + candidate):
        return "unknown"
    if min(candidate) > max(current):
        return "gain"
    if max(candidate) < min(current):
        return "regression"
    if len(set(current + candidate)) == 1:
        return "equal_anchors"
    return "judge_disagreement"


def resource_delta(current, candidate):
    def number(value):
        return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None
    deltas = {}
    for key in RESOURCES:
        a, b = number(current.get(key)), number(candidate.get(key))
        deltas[key] = {"current": a, "candidate": b,
                       "delta": b - a if a is not None and b is not None else None,
                       "percent": 100 * (b - a) / a if a is not None and b is not None and a > 0 else None}
    values = [row["delta"] for row in deltas.values()]
    if any(v is None for v in values):
        disposition = "unknown"
    elif all(v == 0 for v in values):
        disposition = "observed_equal_resources"
    elif all(v <= 0 for v in values):
        disposition = "candidate_observed_componentwise_reduction"
    elif all(v >= 0 for v in values):
        disposition = "candidate_observed_componentwise_increase"
    else:
        disposition = "observed_resource_tradeoff"
    return {"disposition": disposition, "deltas": deltas}


def compare(data):
    if not isinstance(data, dict):
        raise ValueError("replay must be an object")
    if data.get("schema") != "planning-score-replay/1":
        raise ValueError("unsupported replay schema")
    expected = data["expected_trials"]
    if not expected or any(not isinstance(x, str) or not x for x in expected) or len(expected) != len(set(expected)):
        raise ValueError("expected_trials must contain distinct trial IDs")
    trials = {trial: {} for trial in expected}
    records = data["records"]
    for row in records:
        trial, pass_id = row["trial"], row["pass"]
        if trial not in trials or type(pass_id) is not int or pass_id not in (1, 2):
            raise ValueError("unknown trial or pass")
        if pass_id in trials[trial]:
            raise ValueError("duplicate trial/pass")
        if row["status"] not in ("valid", "invalid"):
            raise ValueError("grade status must be valid or invalid")
        if row["status"] == "valid":
            if set(row["dimensions"]) != set(DIMENSIONS):
                raise ValueError("dimension IDs must match")
            for value in row["dimensions"].values():
                if value is not None and (type(value) is not int or value not in range(4)):
                    raise ValueError("anchor must be an integer 0..3 or null")
            for layers in row["obligations"].values():
                if set(layers) != {"spec", "plan"} or any(v not in STATUSES for v in layers.values()):
                    raise ValueError("invalid obligation status")
        if not isinstance(row["findings"], list):
            raise ValueError("findings must be a list")
        trials[trial][pass_id] = row
    pairs = []
    pair_ids = set()
    for pair in data["pairs"]:
        key, a, b = pair["id"], pair["current"], pair["candidate"]
        if key in pair_ids or a == b or a not in trials or b not in trials:
            raise ValueError("duplicate pair or unknown/self pair")
        pair_ids.add(key)
        arms = [list(trials[t].values()) for t in (a, b)]
        ready = all(len(rows) == 2 and all(r["status"] == "valid" for r in rows) for rows in arms)
        dimensions = {}
        for dim in DIMENSIONS:
            values = [[r.get("dimensions", {}).get(dim) if r["status"] == "valid" else None
                       for r in sorted(rows, key=lambda r: r["pass"])] for rows in arms]
            dimensions[dim] = {"current": values[0], "candidate": values[1],
                               "comparison": contrast(*values) if ready else "unknown"}
        coverage = {}
        if ready:
            sets = [set(r["obligations"]) for rows in arms for r in rows]
            if any(ids != sets[0] for ids in sets):
                raise ValueError("paired obligation IDs differ")
            for obligation in sorted(sets[0]):
                coverage[obligation] = {}
                for layer in ("spec", "plan"):
                    values = [[r["obligations"][obligation][layer] for r in sorted(rows, key=lambda r: r["pass"])] for rows in arms]
                    coverage[obligation][layer] = {"current": values[0], "candidate": values[1],
                        "comparison": contrast(*[[STATUSES[v] for v in arm] for arm in values])}
        pairs.append({"id": key, "valid_four_grades": ready, "dimensions": dimensions, "coverage": coverage,
                      "confirmed_gains": [k for k, v in dimensions.items() if v["comparison"] == "gain"],
                      "confirmed_regressions": [k for k, v in dimensions.items() if v["comparison"] == "regression"],
                      "findings": {arm: [{"pass": r["pass"], "grade_status": r["status"], "items": r["findings"]} for r in rows]
                                   for arm, rows in zip(("current", "candidate"), arms)},
                      "resources": resource_delta(pair["resources"]["current"], pair["resources"]["candidate"]),
                      "retention": "requires evidence-based judgment; minor costs or findings are not automatic vetoes"})
    return {"schema": "planning-score-comparison/1", "attempted_grades": len(records),
            "valid_grades": sum(r["status"] == "valid" for r in records),
            "missing_passes": [{"trial": t, "pass": p} for t in expected for p in (1, 2) if p not in trials[t]],
            "pairs": pairs, "qualitative_observations": data.get("qualitative_observations", []),
            "all_subject_attempts_resources": data.get("all_subject_attempts_resources"),
            "limits": ["Trusted grade-validity labels are not revalidated against full evidence by this arithmetic replay.",
                       "Repeated judgments do not add independent subject replications.",
                       "No scalar winner, statistical noninferiority, dollar-cost or causal improvement claim."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, help="New result file; existing files are never overwritten")
    args = parser.parse_args()
    try:
        def reject_constant(value):
            raise ValueError("non-finite JSON number")
        result = compare(json.loads(args.input.read_text(), parse_constant=reject_constant))
        text = json.dumps(result, indent=2, allow_nan=False) + "\n"
        if args.output:
            with args.output.open("x") as stream:
                stream.write(text)
        else:
            print(text, end="")
    except (KeyError, TypeError, ValueError, OSError) as error:
        print(f"comparison failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
