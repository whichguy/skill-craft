#!/usr/bin/env python3
"""Per-attempt export and arm-pairing check of a finished calibration epoch (stage 3, run.sh's output folder).

    python3 analyze_run.py OUT_FOLDER DEST_FOLDER

Writes DEST/attempts.jsonl (one compact row per registered attempt: outcome, floors, processed tokens, turns, minutes) and
DEST/paired.json. Both arms of a calibration epoch run one build, so control N and candidate N are twins: spread.py pools
every attempt of a case and deals random splits, which hides a difference between the arm labels. paired.json asks that
question directly: in how many twin pairs did the candidate arm use more of a measure, and what is the exact one-sided
sign-test probability of that count if the labels carried no information.
"""
import json
import math
import statistics
import sys
from pathlib import Path

out, dest = Path(sys.argv[1]), Path(sys.argv[2])
dest.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(out / "source" / "test" / "shiploop_e2e"))
import epoch, promotion, scorecard  # noqa: E402

root = out / "epoch"
registration = epoch.registration(root)
floors = list(registration.get("floors") or promotion.DEFAULT_FLOORS)
frozen = registration["qualification"]["cases"]
rows = []
for attempt in registration["attempts"]:
    row = {"id": attempt["id"], "case": attempt["case"], "arm": attempt["arm"]}
    try:
        output, _ = epoch.sealed_run(root, attempt["id"])
    except (OSError, ValueError) as error:
        row.update(sealed=False, why=str(error)[:200])
        rows.append(row)
        continue
    card = scorecard.score(output, required_case=frozen[attempt["case"]])
    efficiency, validity = card.get("efficiency") or {}, card.get("validity") or {}
    metrics = json.loads((output / "metrics.json").read_text())
    row.update(sealed=True, outcome=promotion._strict_outcome(card, floors)[0], floors=card.get("floors"),
               tokens=efficiency.get("tokens"), turns=efficiency.get("turns"), minutes=efficiency.get("minutes"),
               output_tokens=efficiency.get("output_tokens"), model_calls=metrics.get("model_calls"),
               totals_lower_bound=efficiency.get("totals_lower_bound"),
               attribution_valid=(validity.get("attribution") or {}).get("valid"),
               timing_valid=(validity.get("timing") or {}).get("valid"))
    rows.append(row)
(dest / "attempts.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def sign_p(more: int, n: int) -> float:
    """P(at least `more` of n twin pairs have the candidate higher) if the labels carried no information."""
    return sum(math.comb(n, k) for k in range(more, n + 1)) / 2 ** n


by = {(row["case"], row["arm"], int(row["id"].rsplit("-", 1)[1])): row for row in rows if row.get("sealed")}
report = {"measures": ["tokens", "turns", "minutes"], "cases": {}, "all": {}}
pooled = {m: [] for m in report["measures"]}
for case in registration["cases"]:
    entry = {}
    for measure in report["measures"]:
        pairs = []
        for (c, arm, n), row in sorted(by.items()):
            twin = by.get((c, "candidate", n))
            if c == case and arm == "control" and twin and isinstance(row.get(measure), (int, float)) \
                    and isinstance(twin.get(measure), (int, float)):
                pairs.append((n, row[measure], twin[measure]))
        if not pairs:
            continue
        changes = [(cand - ctrl) / ctrl for _, ctrl, cand in pairs if ctrl]
        higher = sum(1 for _, ctrl, cand in pairs if cand > ctrl)
        entry[measure] = {"pairs": len(pairs), "candidate_higher": higher,
                          "sign_test_p_one_sided": round(sign_p(higher, len(pairs)), 4),
                          "median_relative_change": round(statistics.median(changes), 4),
                          "control_median": statistics.median(c for _, c, _ in pairs),
                          "candidate_median": statistics.median(d for _, _, d in pairs)}
        pooled[measure] += [(case, n, ctrl, cand) for n, ctrl, cand in pairs]
    report["cases"][case] = entry
for measure, pairs in pooled.items():
    if pairs:
        higher = sum(1 for *_, ctrl, cand in pairs if cand > ctrl)
        changes = [(cand - ctrl) / ctrl for *_, ctrl, cand in pairs if ctrl]
        report["all"][measure] = {"pairs": len(pairs), "candidate_higher": higher,
                                  "sign_test_p_one_sided": round(sign_p(higher, len(pairs)), 4),
                                  "median_relative_change": round(statistics.median(changes), 4)}
(dest / "paired.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
print(json.dumps(report["all"], indent=1))
