#!/usr/bin/env python3
"""E7's noise check beside experiment.py's A/A-spread rule (docs/shiploop-test-stage-prompt-design-2026-10-30.md §7b).

    python3 -I docs/experiments/test-stage-prompt-20261030/e7_analysis.py

Reads e7-results.json (next to this file). For each case it prints every arm's mean, sd and survivors per sample. It
prints a one-sided permutation p for each arm against A, and against the A-condition: A's samples plus every arm-M
sample whose stage mutation check found no survivor (`m_no_feedback`), whose test stage therefore saw exactly A's
packet and feedback. It also prints the A-vs-A gap between those two groups, and E7-K2's arms split by the guard shape
implement wrote (`implement_sites`, §7c).

E7-F (§7c, the implementation held fixed) is read by the rule fixed before its runs: an arm is adopted only if it beats A
at a one-sided exact permutation p < 0.05 over all samples and its gain exceeds A's split-half gap (samples 1-4 against
5-8). It also prints how many samples left the recorded implementation as it was (`product_as_recorded`).
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


def by_arm(data: dict, case: str) -> dict[str, list[dict]]:
    arms: dict[str, list[dict]] = {}
    for s in sorted((s for s in data["samples"] if s["experiment"] == case), key=lambda s: s["sample"]):
        arms.setdefault(s["arm"], []).append(s)
    return arms


def describe(case: str, arms: dict[str, list[dict]]) -> None:
    print(f"== {case}")
    for arm, got in arms.items():
        values = [s["value"] for s in got]
        print(f"  {arm}: n={len(values)} mean={st.mean(values):.3f} sd={st.stdev(values):.3f} "
              f"survivors/sample={st.mean(s['target_survived'] for s in got):.2f}")


def shapes(arms: dict[str, list[dict]]) -> None:
    print("== E7-K2 by implement guard shape (implement_sites; 0-1: implement wrote no load guard, the test stage did)")
    for arm, got in arms.items():
        cells: dict[str, list[float]] = {}
        for s in got:
            sites = s["implement_sites"]
            cells.setdefault(str(sites) if sites >= 5 else "test stage", []).append(s["value"])
        print(f"  {arm}: " + "; ".join(f"{k}: n={len(v)} mean={st.mean(v):.2f}" for k, v in sorted(cells.items())))


def fixed(arms: dict[str, list[dict]]) -> None:
    a = [s["value"] for s in arms["A"]]
    gap = abs(st.mean(a[:4]) - st.mean(a[4:8])) if len(a) >= 8 else None
    print(f"  A split-half gap (samples 1-4 vs 5-8): {gap if gap is None else round(gap, 3)}")
    print("  product as recorded: " + ", ".join(
        f"{arm} {sum(bool(s.get('product_as_recorded')) for s in got)}/{len(got)}" for arm, got in arms.items()))
    for x, y in (("A", "D"), ("A", "C"), ("D", "C")):
        if x in arms and y in arms:
            gain, p = perm([s["value"] for s in arms[x]], [s["value"] for s in arms[y]])
            adopted = p < 0.05 and gap is not None and gain > gap
            print(f"  {x} vs {y}: gain {gain}, p {p}" + (" -> meets the rule" if adopted and x == "A" else ""))


def main() -> None:
    data = json.loads((HERE / "e7-results.json").read_text())
    for case in ("E7-K1", "E7-K2"):
        arms = by_arm(data, case)
        describe(case, arms)
        a = [s["value"] for s in arms["A"]]
        m_as_a = [s["value"] for s in arms["M"] if s["sample"] in M_NO_FEEDBACK[case]]
        print(f"  A vs M without feedback (A/A): {perm(a, m_as_a)}")
        for arm, got in arms.items():
            if arm != "A":
                values = [s["value"] for s in got]
                print(f"  A vs {arm}: {perm(a, values)}; "
                      f"A-condition (n={len(a) + len(m_as_a)}) vs {arm}: {perm(a + m_as_a, values)}")
    shapes(by_arm(data, "E7-K2"))
    if arms := by_arm(data, "E7-F"):
        describe("E7-F (implementation fixed: E7-K2 A/6)", arms)
        fixed(arms)


if __name__ == "__main__":
    main()
