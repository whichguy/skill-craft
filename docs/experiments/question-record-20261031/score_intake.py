#!/usr/bin/env python3
"""Score X1-T (README.md) from the Opus judge answers, by X1's rule: a decision counts as covered only when the judge's
quote is found in that output (X1's ``norm``).  Writes scores-intake-<slug>.json and prints the tables and the rules.
Usage: score_intake.py [SUBJECT_SLUG]
"""
import importlib.util
import json
import re
import sys

from common import CASE, HERE, X1, envelope_text, state_block
from stats import mean, permutation_p

_spec = importlib.util.spec_from_file_location("x1_score", X1 / "score.py")
x1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(x1)
ARMS = ("A", "B", "C")


def judge_json(path):
    text = json.loads(path.read_text()).get("text") or ""
    match = re.search(r"\{.*\}", text, re.S)
    return json.loads(match.group(0))


def main() -> None:
    slug = sys.argv[1] if len(sys.argv) > 1 else "terra"
    mapping = json.loads((HERE / "judge" / f"intake-{slug}-mapping.json").read_text())
    runs, unverified = [], []
    for name, labels in mapping.items():
        case_id = name.split(f"intake-{slug}-", 1)[1].rsplit("-p", 1)[0]
        verdict = judge_json(HERE / "judge" / f"{name}.out.json")["outputs"]
        decisions = [g["id"] for g in CASE[case_id]["ground_truth"]]
        for label, info in labels.items():
            out_path = HERE.parent / info["file"]
            text = envelope_text(out_path)
            meta = json.loads(out_path.with_name(out_path.stem + ".meta.json").read_text())
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
            questions = (result or {}).get("questions") or []
            runs.append({"case": case_id, "arm": info["arm"], "sample": info["sample"], "label": label, "judge": name,
                         "recall": round(len(covered) / len(decisions), 4), "covered": covered,
                         "missed": [d for d in decisions if d not in covered], "default_yes": yes, "default_no": no,
                         "agreement": (yes / (yes + no)) if yes + no else None,
                         "items_total": grade.get("items_total"), "noise": grade.get("noise"),
                         "noise_examples": grade.get("noise_examples"), "questions": len(questions),
                         "routes": {r: sum(1 for q in questions if q.get("route") == r)
                                    for r in ("inspect", "research", "experiment", "default", "person")},
                         "chars": len(text), "seconds": meta.get("seconds"), "parsed": result is not None})
    report = {"subject": slug, "runs": runs, "unverified_quotes": unverified, "arms": {}, "tests": {}, "rules": {}}
    for arm in ARMS:
        rows = [r for r in runs if r["arm"] == arm]
        yes, no = sum(r["default_yes"] for r in rows), sum(r["default_no"] for r in rows)
        report["arms"][arm] = {
            "n": len(rows), "recall": mean(r["recall"] for r in rows),
            "covered": sum(len(r["covered"]) for r in rows), "decisions": sum(len(r["covered"]) + len(r["missed"]) for r in rows),
            "default_yes": yes, "default_no": no, "agreement": yes / (yes + no) if yes + no else None,
            "items": mean(r["items_total"] or 0 for r in rows), "noise": mean(r["noise"] or 0 for r in rows),
            "chars": mean(r["chars"] for r in rows), "seconds": mean(r["seconds"] or 0 for r in rows),
            "questions": mean(r["questions"] for r in rows)}
    for x, y in (("A", "B"), ("A", "C"), ("C", "B")):
        a = [r["recall"] for r in runs if r["arm"] == x]
        b = [r["recall"] for r in runs if r["arm"] == y]
        report["tests"][f"{y} vs {x}"] = {"diff": mean(b) - mean(a), "p_one_sided": permutation_p(a, b)}
    arms = report["arms"]
    report["rules"]["D2 stands"] = (abs(arms["B"]["recall"] - arms["C"]["recall"]) < 0.05
                                    and (arms["B"]["agreement"] or 0) <= (arms["C"]["agreement"] or 0))
    report["rules"]["intake wording reopens (C - A >= 0.15)"] = arms["C"]["recall"] - arms["A"]["recall"] >= 0.15
    (HERE / f"scores-intake-{slug}.json").write_text(json.dumps(report, indent=2) + "\n")

    print(f"subject {slug}: runs {len(runs)}, unverified judge quotes {len(unverified)}")
    print(f"{'arm':4} {'recall':>7} {'cov':>7} {'agree':>6} {'yes':>4} {'no':>4} {'items':>6} {'noise':>6} {'chars':>7} {'secs':>6} {'q':>5}")
    for arm in ARMS:
        a = arms[arm]
        print(f"{arm:4} {a['recall']:7.3f} {a['covered']:3}/{a['decisions']:3} {a['agreement'] or 0:6.2f} {a['default_yes']:4} "
              f"{a['default_no']:4} {a['items']:6.1f} {a['noise']:6.1f} {a['chars']:7.0f} {a['seconds']:6.1f} {a['questions']:5.1f}")
    for key, value in report["tests"].items():
        print(f"  {key}: diff {value['diff']:+.3f}, one-sided p = {value['p_one_sided']:.4f}")
    print("per case recall:")
    for case_id in CASE:
        print(f"  {case_id:18} " + " ".join(f"{arm} {mean(r['recall'] for r in runs if r['case'] == case_id and r['arm'] == arm):.3f}" for arm in ARMS))
    for arm in ARMS:
        missed = {}
        for r in runs:
            if r["arm"] == arm:
                for d in r["missed"]:
                    missed[d] = missed.get(d, 0) + 1
        print(f"  missed {arm}: " + ", ".join(f"{d}x{n}" for d, n in sorted(missed.items())))
    print("rules:", json.dumps(report["rules"]))


if __name__ == "__main__":
    main()
