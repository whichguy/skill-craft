#!/usr/bin/env python3
"""E7's noise check beside experiment.py's A/A-spread rule (docs/shiploop-test-stage-prompt-design-2026-10-30.md §7b).

    python3 -I docs/experiments/test-stage-prompt-20261030/e7_analysis.py

Reads e7-results.json (next to this file). For each case it prints every arm's mean, sd and survivors per sample. It
prints a one-sided permutation p for each arm against A, and against the A-condition: A's samples plus every arm-M
sample whose stage mutation check found no survivor (`m_no_feedback`), whose test stage therefore saw exactly A's
packet and feedback. It also prints the A-vs-A gap between those two groups.
"""
import itertools
import json
import random
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Arm-M samples whose stage mutation check (RUN/tests/*-mutation-check.md) killed every sampled mutant, so the test
# stage got no feedback A would not have got: all of E7-K1, and E7-K2 except sample 5 (one survivor).
M_NO_FEEDBACK = {"E7-K1": {1, 2, 3, 4}, "E7-K2": {1, 2, 3, 4, 6, 7, 8}}


def perm(x: list[float], y: list[float], iters: int = 200000) -> tuple[float, float]:
    """(mean(y) - mean(x), one-sided p that a random relabelling gives a difference at least as large)."""
    observed, pool, n = st.mean(y) - st.mean(x), x + y, len(x)
    if len(pool) <= 20:
        splits = list(itertools.combinations(range(len(pool)), n))
        hits = sum(st.mean([pool[i] for i in range(len(pool)) if i not in set(s)]) - st.mean([pool[i] for i in s])
                   >= observed - 1e-12 for s in splits)
        return round(observed, 3), round(hits / len(splits), 4)
    rng, hits = random.Random(7), 0
    for _ in range(iters):
        rng.shuffle(pool)
        hits += st.mean(pool[n:]) - st.mean(pool[:n]) >= observed - 1e-12
    return round(observed, 3), round(hits / iters, 4)


def main() -> None:
    data = json.loads((HERE / "e7-results.json").read_text())
    for case in ("E7-K1", "E7-K2"):
        rows = [s for s in data["samples"] if s["experiment"] == case]
        arms = {}
        for s in rows:
            arms.setdefault(s["arm"], []).append(s)
        print(f"== {case}")
        for arm, got in arms.items():
            values = [s["value"] for s in got]
            print(f"  {arm}: n={len(values)} mean={st.mean(values):.3f} sd={st.stdev(values):.3f} "
                  f"survivors/sample={st.mean(s['target_survived'] for s in got):.2f}")
        a = [s["value"] for s in arms["A"]]
        m_as_a = [s["value"] for s in arms["M"] if s["sample"] in M_NO_FEEDBACK[case]]
        print(f"  A vs M without feedback (A/A): {perm(a, m_as_a)}")
        for arm, got in arms.items():
            if arm != "A":
                values = [s["value"] for s in got]
                print(f"  A vs {arm}: {perm(a, values)}; "
                      f"A-condition (n={len(a) + len(m_as_a)}) vs {arm}: {perm(a + m_as_a, values)}")


if __name__ == "__main__":
    main()
