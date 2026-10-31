#!/usr/bin/env python3
"""Score XR (README.md, "XR") by its pre-registered rule.  Per output: M1, RUNTIME questions routed `experiment`; M2,
NOT_RUNTIME questions routed `experiment`; R, RUNTIME questions; ledger validity by ShipLoop's own shape check.  A judge answer
missing an output or a question id fails loudly.  Writes scores-routing.json.  Usage: score_routing.py
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "question-record-20261031"))
sys.path.insert(0, str(HERE.parents[2] / "skills" / "shiploop" / "scripts"))
from common import envelope_text, state_block  # noqa: E402
from stats import mean, permutation_p  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402


def judged(name: str) -> dict:
    text = envelope_text(HERE / "routing" / "judge" / f"{name}.out.json")
    match = re.search(r"\{.*\}", text, re.S)
    return json.loads(match.group(0))


def main() -> None:
    mapping = json.loads((HERE / "routing" / "judge" / "mapping.json").read_text())
    rows = []
    for name, labels in mapping.items():
        classes = judged(name)
        for label, where in labels.items():
            result = state_block(envelope_text(HERE / where["file"])) or {}
            questions = [q for q in result.get("questions") or [] if isinstance(q, dict)]
            verdicts = classes.get(label)
            if verdicts is None or {str(q.get("id")) for q in questions} - set(verdicts):
                raise SystemExit(f"{name} {label}: the judge left out an output or a question id")
            try:
                navigator._check_intake_questions("intake", result)
                valid = True
            except Exception as error:  # a refusal of the ledger's shape
                valid, why = False, str(error)[:160]
            runtime = [q for q in questions if verdicts[str(q["id"])] == "RUNTIME"]
            rows.append({"case": name.split("-", 1)[1].rsplit("-", 1)[0], "arm": where["arm"], "sample": where["sample"],
                         "questions": len(questions), "R": len(runtime),
                         "M1": sum(q.get("route") == "experiment" for q in runtime),
                         "M2": sum(q.get("route") == "experiment" and verdicts[str(q["id"])] != "RUNTIME" for q in questions),
                         "valid": valid, **({} if valid else {"why": why})})
    arms = {}
    for arm in ("A", "B"):
        mine = [r for r in rows if r["arm"] == arm]
        arms[arm] = {"outputs": len(mine), "M1": mean(r["M1"] for r in mine), "M2": mean(r["M2"] for r in mine),
                     "R": mean(r["R"] for r in mine), "questions": mean(r["questions"] for r in mine),
                     "runtime_share_routed": sum(r["M1"] for r in mine) / max(1, sum(r["R"] for r in mine)),
                     "invalid": sum(not r["valid"] for r in mine)}
    a = [float(r["M1"]) for r in rows if r["arm"] == "A"]
    b = [float(r["M1"]) for r in rows if r["arm"] == "B"]
    p = permutation_p(a, b)
    rise = arms["B"]["M1"] - arms["A"]["M1"]
    rule = {"M1_rise": rise, "p_one_sided": p, "M2_B_minus_A": arms["B"]["M2"] - arms["A"]["M2"],
            "invalid_B_minus_A": arms["B"]["invalid"] - arms["A"]["invalid"]}
    rule["moves_routing"] = bool(rise >= 1.0 and p < 0.05 and rule["M2_B_minus_A"] <= 0.5 and rule["invalid_B_minus_A"] <= 1)
    by_case = {}
    for case in sorted({r["case"] for r in rows}):
        by_case[case] = {arm: {"M1": mean(r["M1"] for r in rows if r["case"] == case and r["arm"] == arm),
                               "R": mean(r["R"] for r in rows if r["case"] == case and r["arm"] == arm)} for arm in ("A", "B")}
    report = {"rows": rows, "arms": arms, "cases": by_case, "rule": rule}
    (HERE / "scores-routing.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"arms": arms, "cases": by_case, "rule": rule}, indent=1))


if __name__ == "__main__":
    main()
