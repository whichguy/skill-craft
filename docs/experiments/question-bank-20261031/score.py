#!/usr/bin/env python3
"""Score QB1 (README.md) from the Opus judge answers, by X1's rule: a decision counts as covered only when the judge's
quote is found in that output (X1's ``norm``).  Adds the cost measures (tokens, seconds), reads each arm's rows, runs the
pre-registered tests and rules, and writes scores.json.  Usage: python3 score.py
"""
import importlib.util
import json
import re
from collections import Counter

from common import ARMS, CASE, HERE, X1, envelope, envelope_text, state_block
from stats import mean, permutation_p

_spec = importlib.util.spec_from_file_location("x1_score", X1 / "score.py")
x1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(x1)
BANK_ARMS = ("Qb", "Sb")
LEDGER_ARMS = ("B", "Bq", "Bs")
X1T_XHIGH = {"A": 0.513, "B": 0.981}  # X1-T's Terra xhigh recall (question-record-20261031/scores-intake-terra-xhigh.json)


def judge_json(path):
    text = json.loads(path.read_text()).get("text") or ""
    return json.loads(re.search(r"\{.*\}", text, re.DOTALL).group(0))


def rows_of(arm, result):
    """The arm's rows (bank answers or ledger questions) and a count of their basis (bank) or route (ledger)."""
    if arm in BANK_ARMS:
        rows = (result or {}).get("answers") or []
        kinds = Counter("request" if re.search(r"\bs\d+\b", str(r.get("basis", "")).strip().lower())
                        else str(r.get("basis", "")).strip().lower() for r in rows)
    elif arm in LEDGER_ARMS:
        rows = (result or {}).get("questions") or []
        kinds = Counter(str(q.get("route", "")).strip().lower() for q in rows)
    else:
        rows, kinds = [], Counter()
    return rows, kinds


def collect():
    mapping = json.loads((HERE / "judge" / "mapping.json").read_text())
    runs, unverified = [], []
    for name, labels in mapping.items():
        case_id = name.removeprefix("qb1-").rsplit("-", 1)[0]
        verdict = judge_json(HERE / "judge" / f"{name}.out.json")["outputs"]
        decisions = [g["id"] for g in CASE[case_id]["ground_truth"]]
        for label, info in labels.items():
            out = HERE.parent / info["file"]
            text = envelope_text(out)
            usage = envelope(out).get("usage") or {}
            meta = json.loads(out.with_name(out.stem + ".meta.json").read_text())
            result = state_block(text)
            grade = verdict.get(label, {})
            covered, yes, no = [], 0, 0
            for ident in decisions:
                row = (grade.get("decisions") or {}).get(ident) or {}
                ok = bool(row.get("covered")) and bool(row.get("quote")) and x1.norm(row["quote"]) in x1.norm(text)
                if row.get("covered") and not ok:
                    unverified.append({"case": case_id, "label": label, "decision": ident, "quote": row.get("quote")})
                if ok:
                    covered.append(ident)
                    yes += row.get("default_matches") == "yes"
                    no += row.get("default_matches") == "no"
            rows, kinds = rows_of(info["arm"], result)
            runs.append({
                "case": case_id, "arm": info["arm"], "sample": info["sample"], "label": label, "judge": name,
                "recall": round(len(covered) / len(decisions), 4), "covered": covered,
                "missed": [d for d in decisions if d not in covered], "default_yes": yes, "default_no": no,
                "items_total": grade.get("items_total") or 0, "noise": grade.get("noise") or 0,
                "rows": len(rows), "kinds": dict(kinds), "person": kinds.get("person", 0),
                "out_tokens": usage.get("output_tokens", 0), "reasoning": usage.get("reasoning_output_tokens", 0),
                "uncached_in": usage.get("input_tokens", 0) - usage.get("cached_input_tokens", 0),
                "chars": len(text), "seconds": meta.get("seconds") or 0, "parsed": result is not None})
    return runs, unverified


def summarize(runs, arm):
    rs = [r for r in runs if r["arm"] == arm]
    yes, no = sum(r["default_yes"] for r in rs), sum(r["default_no"] for r in rs)
    items, noise = sum(r["items_total"] for r in rs), sum(r["noise"] for r in rs)
    covered = sum(len(r["covered"]) for r in rs)
    tokens = sum(r["out_tokens"] for r in rs)
    kinds = Counter()
    for r in rs:
        kinds.update(r["kinds"])
    return {
        "n": len(rs), "recall": mean(r["recall"] for r in rs), "covered": covered,
        "decisions": sum(len(r["covered"]) + len(r["missed"]) for r in rs), "default_yes": yes, "default_no": no,
        "agreement": yes / (yes + no) if yes + no else None, "items": items / len(rs),
        "noise_share": noise / items if items else None, "out_tokens": mean(r["out_tokens"] for r in rs),
        "reasoning": mean(r["reasoning"] for r in rs), "uncached_in": mean(r["uncached_in"] for r in rs),
        "chars": mean(r["chars"] for r in rs), "seconds": mean(r["seconds"] for r in rs),
        "rows": mean(r["rows"] for r in rs), "person": mean(r["person"] for r in rs),
        "covered_per_1k_out": covered / tokens * 1000 if tokens else None, "unparsed": sum(not r["parsed"] for r in rs),
        "kinds": {k: round(v / len(rs), 2) for k, v in sorted(kinds.items())}}


# The exact test's work grows with the number of distinct sums, so at 32 runs per arm the values it permutes are coarsened:
# recall to two decimals (a decision is 10 or 11 points of a case), output tokens to the nearest 10.  check_coarse.py
# shows the coarsening leaves X1-T's p-values unchanged.
COARSE = {"recall": lambda v: round(v, 2), "out_tokens": lambda v: round(v / 10)}


def values(runs, arm, key):
    coarsen = COARSE.get(key, lambda v: v)
    return [coarsen(r[key]) for r in runs if r["arm"] == arm]


def higher_p(runs, low_arm, high_arm, key):
    """Exact one-sided p that ``high_arm``'s mean of ``key`` exceeds ``low_arm``'s by chance (the harness's rule)."""
    return permutation_p(values(runs, low_arm, key), values(runs, high_arm, key))


def lower_p(runs, high_arm, low_arm, key):
    """Exact one-sided p that ``low_arm``'s mean of ``key`` is below ``high_arm``'s by chance."""
    return permutation_p([-v for v in values(runs, high_arm, key)], [-v for v in values(runs, low_arm, key)])


def form_verdict(runs, arms, question_arm, statement_arm):
    """Rules R1 and R2: does the question form (or the statement form) move coverage by 5 points, or cost by 15%?"""
    q, s = arms[question_arm], arms[statement_arm]
    gap = q["recall"] - s["recall"]
    ratio = q["out_tokens"] / s["out_tokens"] if s["out_tokens"] else None
    out = {"recall_gap_q_minus_s": gap, "token_ratio_q_over_s": ratio,
           "p_q_recall_higher": higher_p(runs, statement_arm, question_arm, "recall"),
           "p_s_recall_higher": higher_p(runs, question_arm, statement_arm, "recall"),
           "p_q_tokens_lower": lower_p(runs, statement_arm, question_arm, "out_tokens"),
           "p_s_tokens_lower": lower_p(runs, question_arm, statement_arm, "out_tokens")}
    if gap >= 0.05 and out["p_q_recall_higher"] < 0.05:
        out["coverage"] = "question form raises coverage"
    elif -gap >= 0.05 and out["p_s_recall_higher"] < 0.05:
        out["coverage"] = "statement form raises coverage"
    else:
        out["coverage"] = "no coverage difference of 5 points"
    if ratio is not None and ratio <= 0.85 and out["p_q_tokens_lower"] < 0.05:
        out["cost"] = "question form is cheaper by 15% or more"
    elif ratio is not None and ratio >= 1 / 0.85 and out["p_s_tokens_lower"] < 0.05:
        out["cost"] = "statement form is cheaper by 15% or more"
    else:
        out["cost"] = "no cost difference of 15%"
    return out


def main() -> None:
    runs, unverified = collect()
    arms = {arm: summarize(runs, arm) for arm in ARMS}
    report = {"runs": runs, "unverified_quotes": unverified, "arms": arms, "rules": {}}
    report["rules"]["R1 fixed bank, Qb against Sb"] = form_verdict(runs, arms, "Qb", "Sb")
    report["rules"]["R2 generated ledger, Bq against Bs"] = form_verdict(runs, arms, "Bq", "Bs")
    best = max(("Qb", "Sb"), key=lambda a: (round(arms[a]["recall"], 2), -arms[a]["out_tokens"]))
    x, b = arms[best], arms["B"]
    clauses = {"recall within 3 points of B": x["recall"] >= b["recall"] - 0.03,
               "output tokens at most 75% of B": x["out_tokens"] <= 0.75 * b["out_tokens"],
               "default agreement within 2 points of B": (x["agreement"] or 0) >= (b["agreement"] or 0) - 0.02,
               "noise share at most 5 points above B": (x["noise_share"] or 0) <= (b["noise_share"] or 0) + 0.05}
    report["rules"]["R3 fixed bank replaces the generated ledger"] = {
        "bank_arm": best, "clauses": clauses, "holds": all(clauses.values()),
        "p_b_recall_higher_than_bank": higher_p(runs, best, "B", "recall"),
        "p_bank_tokens_lower_than_b": lower_p(runs, "B", best, "out_tokens")}
    report["rules"]["R4 anchors replicate X1-T xhigh"] = {
        arm: {"now": arms[arm]["recall"], "x1t": X1T_XHIGH[arm],
              "within_5_points": abs(arms[arm]["recall"] - X1T_XHIGH[arm]) <= 0.05} for arm in ("A", "B")}
    report["rules"]["R5 recall ceiling (all arms 0.95 or more)"] = all(a["recall"] >= 0.95 for a in arms.values())
    (HERE / "scores.json").write_text(json.dumps(report, indent=2) + "\n")

    print(f"runs {len(runs)}, unverified judge quotes {len(unverified)}, unparsed outputs {sum(a['unparsed'] for a in arms.values())}")
    print(f"{'arm':3} {'n':>3} {'recall':>7} {'agree':>6} {'noise':>6} {'rows':>5} {'person':>6} {'out_tok':>8} {'reason':>7} "
          f"{'in_unc':>7} {'chars':>6} {'secs':>5} {'cov/1k':>7}")
    for arm in ARMS:
        a = arms[arm]
        print(f"{arm:3} {a['n']:3d} {a['recall']:7.3f} {a['agreement'] or 0:6.2f} {a['noise_share'] or 0:6.2f} {a['rows']:5.1f} "
              f"{a['person']:6.2f} {a['out_tokens']:8.0f} {a['reasoning']:7.0f} {a['uncached_in']:7.0f} {a['chars']:6.0f} "
              f"{a['seconds']:5.1f} {a['covered_per_1k_out'] or 0:7.2f}")
    print("per case recall:")
    for case_id in CASE:
        print(f"  {case_id:18} " + " ".join(
            f"{arm} {mean(r['recall'] for r in runs if r['case'] == case_id and r['arm'] == arm):.3f}" for arm in ARMS))
    for arm in ARMS:
        missed = Counter(d for r in runs if r["arm"] == arm for d in r["missed"])
        print(f"  missed {arm}: " + ", ".join(f"{d}x{n}" for d, n in sorted(missed.items())))
    print("basis or route per output (rows by kind):")
    for arm in ARMS:
        print(f"  {arm:3} {arms[arm]['kinds']}")
    print("rules:")
    print(json.dumps(report["rules"], indent=2))


if __name__ == "__main__":
    main()
