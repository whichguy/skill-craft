#!/usr/bin/env python3
"""Check that coarsening the permuted values (score.py COARSE) leaves X1-T's decision p-values unchanged.

Takes X1-T's Terra xhigh per-run recall (../question-record-20261031/scores-intake-terra-xhigh.json, 16 runs per arm) and
tests B against A and C against A twice with the harness's exact one-sided permutation test (stats.permutation_p): once on
the values as scored (4 decimals) and once coarsened to 2 decimals.  Prints both p-values.  Usage: python3 check_coarse.py
"""
import json

from common import QR
from stats import permutation_p


def main() -> None:
    runs = json.loads((QR / "scores-intake-terra-xhigh.json").read_text())["runs"]
    by_arm = {arm: [r["recall"] for r in runs if r["arm"] == arm] for arm in "ABC"}
    for low, high in (("A", "B"), ("A", "C"), ("C", "B")):
        exact = permutation_p(by_arm[low], by_arm[high])
        coarse = permutation_p([round(v, 2) for v in by_arm[low]], [round(v, 2) for v in by_arm[high]])
        print(f"{high} vs {low}: exact (4 decimals) p = {exact:.6f}; coarsened (2 decimals) p = {coarse:.6f}")


if __name__ == "__main__":
    main()
