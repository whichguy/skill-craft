#!/usr/bin/env python3
"""Build QB1's subject prompts for arms Qb, Sb, Bq and Bs (README.md) from X1's committed prompts for A and B.

Every new prompt equals its base byte for byte except the inserted item 9 and result-template rows, and the script checks
that by undoing the edit.  Qb and Sb start from arm A (the duty without item 9) and add the bank item and an ``answers``
template row; Bq and Bs start from arm B and replace only the eleven catalog lines.  Usage: python3 build.py
"""
import re

from bank import bank_item9, catalog_block
from common import CASES, HERE, X1

A_LAST = "8. Implement nothing; add no scope. `evidence_refs`: each source used.\n"
A_TAIL = '  "outcome": "done",\n  "summary"'
ANSWERS = ('  "answers": [\n'
           '    {"answer": "...", "basis": "S1|inspect|research|experiment|default|person|na", "id": "K1.1"}\n'
           '  ],\n')
CATALOG_RE = re.compile(r"   - K1 Outcome and consumer:.*?what would show it early\.\n", re.DOTALL)


def build_case(case_id: str) -> dict:
    base_a = (X1 / "prompts" / f"{case_id}-A.md").read_text()
    base_b = (X1 / "prompts" / f"{case_id}-B.md").read_text()
    assert base_a.count(A_LAST) == 1 and base_a.count(A_TAIL) == 1, case_id
    assert len(CATALOG_RE.findall(base_b)) == 1, case_id
    out = {}
    for arm, form in (("Qb", "Q"), ("Sb", "S")):
        item = bank_item9(form)
        text = base_a.replace(A_LAST, A_LAST + item, 1).replace(
            A_TAIL, '  "outcome": "done",\n' + ANSWERS + '  "summary"', 1)
        undone = text.replace(item, "", 1).replace(ANSWERS, "", 1)
        assert undone == base_a, (case_id, arm)
        out[arm] = text
    old_block = CATALOG_RE.search(base_b).group(0)
    for arm, form in (("Bq", "Q"), ("Bs", "S")):
        block = catalog_block(form)
        text = CATALOG_RE.sub(lambda _m, block=block: block, base_b, count=1)
        assert text.replace(block, old_block, 1) == base_b, (case_id, arm)
        out[arm] = text
    return out


def main() -> None:
    sizes = {}
    for case in CASES:
        for arm, text in build_case(case["id"]).items():
            (HERE / "prompts" / f"{case['id']}-{arm}.md").write_text(text)
            sizes.setdefault(arm, []).append(len(text))
    for arm in ("A", "B"):
        sizes[arm] = [len((X1 / "prompts" / f"{case['id']}-{arm}.md").read_text()) for case in CASES]
    print("prompt characters per arm (mean over the four cases):")
    for arm in ("A", "B", "Qb", "Sb", "Bq", "Bs"):
        print(f"  {arm:3} {sum(sizes[arm]) / len(sizes[arm]):8.0f}")


if __name__ == "__main__":
    main()
