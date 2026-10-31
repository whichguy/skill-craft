#!/usr/bin/env python3
"""Score pilot X1 from the judge answers: a decision counts as covered only when the judge's quote is found in the output.

Writes scores.json and prints per-arm and per-case tables plus exact permutation p-values.
"""
import itertools
import json
import re
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ("A", "B", "C")


def norm(text: str) -> str:
    text = text.replace('\\"', '"').replace("\\n", " ").lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def judge_json(path: Path) -> dict:
    text = json.loads(path.read_text()).get("text") or ""
    match = re.search(r"\{.*\}", text, re.S)
    return json.loads(match.group(0))


def subject_text(path: Path) -> str:
    return json.loads(path.read_text()).get("text") or ""


def parsed_result(text: str):
    match = re.search(r"```shiploop-state\s*(\{.*\})\s*```", text, re.S)
    try:
        return json.loads(match.group(1)) if match else None
    except json.JSONDecodeError:
        return None


def perm_p(a: list, b: list) -> float:
    """Exact two-sided permutation p for the difference in means of two independent samples."""
    observed = abs(statistics.mean(a) - statistics.mean(b))
    pooled = a + b
    count = total = 0
    for idx in itertools.combinations(range(len(pooled)), len(a)):
        chosen = set(idx)
        x = [pooled[i] for i in chosen]
        y = [pooled[i] for i in range(len(pooled)) if i not in chosen]
        total += 1
        if abs(statistics.mean(x) - statistics.mean(y)) >= observed - 1e-12:
            count += 1
    return count / total


def main() -> None:
    cases = {c["id"]: c for c in json.loads((HERE / "cases.json").read_text())["cases"]}
    mapping = json.loads((HERE / "judge" / "mapping.json").read_text())
    runs = []
    unverified = []
    for case_id, labels in mapping.items():
        verdict = judge_json(HERE / "judge" / f"{case_id}.out.json")["outputs"]
        decisions = [g["id"] for g in cases[case_id]["ground_truth"]]
        for label, info in labels.items():
            out_path = HERE / "outputs" / info["file"]
            text = subject_text(out_path)
            meta = json.loads((out_path.parent / (out_path.stem + ".meta.json")).read_text())
            result = parsed_result(text)
            grade = verdict.get(label, {})
            covered, matches, conflicts = [], 0, 0
            for ident in decisions:
                row = (grade.get("decisions") or {}).get(ident) or {}
                ok = bool(row.get("covered")) and bool(row.get("quote")) and norm(row["quote"]) in norm(text)
                if row.get("covered") and not ok:
                    unverified.append({"case": case_id, "label": label, "decision": ident, "quote": row.get("quote")})
                if ok:
                    covered.append(ident)
                if ok and row.get("default_matches") == "yes":
                    matches += 1
                if ok and row.get("default_matches") == "no":
                    conflicts += 1
            questions = (result or {}).get("questions") or []
            runs.append({
                "case": case_id, "arm": info["arm"], "sample": info["sample"], "label": label,
                "recall": len(covered) / len(decisions), "covered": covered,
                "missed": [d for d in decisions if d not in covered],
                "default_yes": matches, "default_no": conflicts,
                "items_total": grade.get("items_total"), "noise": grade.get("noise"),
                "noise_examples": grade.get("noise_examples"),
                "questions": len(questions),
                "routes": {r: sum(1 for q in questions if q.get("route") == r)
                           for r in ("inspect", "research", "experiment", "default", "person")},
                "chars": len(text), "seconds": meta.get("seconds"), "parsed": result is not None,
            })
    (HERE / "scores.json").write_text(json.dumps({"runs": runs, "unverified_quotes": unverified}, indent=2) + "\n")

    print(f"runs: {len(runs)}; unverified judge quotes: {len(unverified)}")
    print("\nPer arm (mean over cases and samples):")
    print(f"{'arm':4} {'recall':>7} {'items':>6} {'noise':>6} {'dflt yes':>9} {'dflt no':>8} {'chars':>7} {'secs':>6}")
    for arm in ARMS:
        rows = [r for r in runs if r["arm"] == arm]
        print(f"{arm:4} {statistics.mean(r['recall'] for r in rows):7.3f} "
              f"{statistics.mean(r['items_total'] or 0 for r in rows):6.1f} "
              f"{statistics.mean(r['noise'] or 0 for r in rows):6.1f} "
              f"{statistics.mean(r['default_yes'] for r in rows):9.2f} {statistics.mean(r['default_no'] for r in rows):8.2f} "
              f"{statistics.mean(r['chars'] for r in rows):7.0f} {statistics.mean(r['seconds'] or 0 for r in rows):6.0f}")
    print("\nPer case recall (mean of samples):")
    print(f"{'case':20} " + " ".join(f"{a:>6}" for a in ARMS))
    for case_id in mapping:
        print(f"{case_id:20} " + " ".join(
            f"{statistics.mean(r['recall'] for r in runs if r['case'] == case_id and r['arm'] == a):6.3f}" for a in ARMS))
    print("\nExact permutation p (two-sided, samples treated as independent; optimistic since samples share a case):")
    for x, y in (("B", "A"), ("C", "A"), ("B", "C")):
        a = [r["recall"] for r in runs if r["arm"] == x]
        b = [r["recall"] for r in runs if r["arm"] == y]
        print(f"  {x} vs {y}: diff {statistics.mean(a) - statistics.mean(b):+.3f}, p = {perm_p(a, b):.4f}")
    print("\nMissed decisions by arm:")
    for arm in ARMS:
        missed = {}
        for r in runs:
            if r["arm"] == arm:
                for d in r["missed"]:
                    missed[d] = missed.get(d, 0) + 1
        print(f"  {arm}: " + ", ".join(f"{d}x{n}" for d, n in sorted(missed.items())))


if __name__ == "__main__":
    main()
