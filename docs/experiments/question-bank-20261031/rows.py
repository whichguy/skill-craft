#!/usr/bin/env python3
"""Which rows carry the coverage (QB1, exploratory; README.md): where each covered decision's judge quote sits.

For every covered decision (a judge quote that a script found in the output) this finds the row the quote lies in: a bank
row of arms Qb and Sb (``answers``, keyed by id), a ledger row of arms B, Bq and Bs (``questions``, keyed by category), or
the output's ``summary``, or elsewhere.  It prints, per arm, how the coverage is shared among rows and how few of the
most-used rows reach 95% of it.  The judge gives one quote per decision, so this attributes each decision to one place;
it shows where coverage was found, not that the other rows could not have found it.  Usage: python3 rows.py
"""
import importlib.util
import json
import re
from collections import Counter

from common import CASE, HERE, X1, envelope_text, state_block

_spec = importlib.util.spec_from_file_location("x1_score", X1 / "score.py")
x1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(x1)


def judge_json(path):
    text = json.loads(path.read_text()).get("text") or ""
    return json.loads(re.search(r"\{.*\}", text, re.DOTALL).group(0))


def locate(arm, result, quote):
    """The key of the row of ``result`` that holds ``quote``: a bank id, a ledger category, 'summary' or 'elsewhere'."""
    needle = x1.norm(quote)
    if arm in ("Qb", "Sb"):
        for row in (result or {}).get("answers") or []:
            if needle in x1.norm(json.dumps(row)):
                return str(row.get("id"))
    elif arm in ("B", "Bq", "Bs"):
        for row in (result or {}).get("questions") or []:
            if needle in x1.norm(json.dumps(row)):
                return str(row.get("category") or "no category")
    if needle in x1.norm(str((result or {}).get("summary") or "")):
        return "summary"
    return "elsewhere"


def main() -> None:
    mapping = json.loads((HERE / "judge" / "mapping.json").read_text())
    where = {}
    totals = Counter()
    for name, labels in mapping.items():
        case_id = name.removeprefix("qb1-").rsplit("-", 1)[0]
        verdict = judge_json(HERE / "judge" / f"{name}.out.json")["outputs"]
        for label, info in labels.items():
            out = HERE.parent / info["file"]
            text = envelope_text(out)
            result = state_block(text)
            for ident in (g["id"] for g in CASE[case_id]["ground_truth"]):
                row = ((verdict.get(label) or {}).get("decisions") or {}).get(ident) or {}
                if row.get("covered") and row.get("quote") and x1.norm(row["quote"]) in x1.norm(text):
                    where.setdefault(info["arm"], Counter())[locate(info["arm"], result, row["quote"])] += 1
                    totals[info["arm"]] += 1
    for arm in ("A", "B", "Bq", "Bs", "Qb", "Sb"):
        counts = where.get(arm, Counter())
        total = totals[arm]
        print(f"\narm {arm}: {total} covered decisions; where the judge's quote sits")
        running = 0
        reached = None
        for rank, (key, n) in enumerate(counts.most_common(), 1):
            running += n
            if reached is None and running >= 0.95 * total:
                reached = rank
            print(f"  {key:10} {n:4d}  {n / total:5.1%}  cumulative {running / total:5.1%}")
        print(f"  places holding 95% of the coverage: {reached}")


if __name__ == "__main__":
    main()
