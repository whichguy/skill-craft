#!/usr/bin/env python3
"""How often each way of reading SG2 returns `supports`, for stated true catch rates; writes sg2-pool-power.json beside it.

    python3 docs/experiments/sdlc-gates-20261030/sg2_pool_power.py

For true per-sample catch rates (A, B), the same in all four cases, it adds up the probability of every outcome that the
rule reads as `supports`: the pool (`sg2_pool.pooled_p`, 4 cases of 4 against 4), one case alone at 4 and at 8 per arm
(`experiment.permutation_p`, what `decide` does), and one case alone at 16 per arm. Rate pairs with A equal to B give the
rate of false `supports` (the p < 0.05 bound is not reached exactly because outcomes are discrete). Exact enumeration, no
sampling. Samples are taken to be independent and identically distributed within an arm and case.
"""
from __future__ import annotations

import itertools
import json
import sys
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "test" / "shiploop_e2e"))
import experiment
import sg2_pool

RATES = ((0.25, 0.75), (0.25, 1.0), (0.5, 1.0), (0.2, 0.6), (0.1, 0.7), (0.5, 0.9), (0.25, 0.25), (0.5, 0.5))
CASES = 4


def pmf(n: int, p: float) -> list[float]:
    return [comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(n + 1)]


def single_power(n: int, pa: float, pb: float) -> float:
    """One case alone with n binary samples per arm."""
    a_pmf, b_pmf = pmf(n, pa), pmf(n, pb)
    total = 0.0
    for a in range(n + 1):
        need = next((b for b in range(a, n + 1) if experiment.permutation_p([1] * a + [0] * (n - a), [1] * b + [0] * (n - b))
                     < experiment.SIGNIFICANCE), None)
        if need is not None:
            total += a_pmf[a] * sum(b_pmf[b] for b in range(need, n + 1))
    return total


def pooled_power(n: int, pa: float, pb: float) -> float:
    """CASES cases of n against n, blocked."""
    a_pmf, b_pmf = pmf(n, pa), pmf(n, pb)
    outcomes = [(a, b) for a in range(n + 1) for b in range(n + 1)]
    supported: dict[tuple, bool] = {}
    total = 0.0
    for combo in itertools.product(outcomes, repeat=CASES):
        weight = 1.0
        for a, b in combo:
            weight *= a_pmf[a] * b_pmf[b]
        if weight == 0:
            continue
        key = tuple(sorted(combo))  # the cases are exchangeable, so the order does not change p
        if key not in supported:
            supported[key] = sg2_pool.pooled_p([([1] * a + [0] * (n - a), [1] * b + [0] * (n - b)) for a, b in key]) \
                < experiment.SIGNIFICANCE
        total += weight * supported[key]
    return total


def thresholds(n: int = 4) -> dict[int, int]:
    """Catches by A out of CASES * n, and the fewest by B that the pool reads as `supports`, both spread evenly over the cases."""
    def spread(total: int) -> list[int]:
        return [total // CASES + (1 if i < total % CASES else 0) for i in range(CASES)]
    found = {}
    for a in range(CASES * n + 1):
        for b in range(a, CASES * n + 1):
            blocks = [([1] * x + [0] * (n - x), [1] * y + [0] * (n - y)) for x, y in zip(spread(a), spread(b))]
            if sg2_pool.pooled_p(blocks) < experiment.SIGNIFICANCE:
                found[a] = b
                break
    return found


def main() -> int:
    rows = [{"A": pa, "B": pb, "one_case_4_per_arm": round(single_power(4, pa, pb), 3),
             "one_case_8_per_arm": round(single_power(8, pa, pb), 3),
             "one_case_16_per_arm": round(single_power(16, pa, pb), 3),
             "pool_4_cases_of_4": round(pooled_power(4, pa, pb), 3)} for pa, pb in RATES]
    report = {"rule": "supports = exact one-sided permutation p < 0.05", "cases": CASES, "slices": {
              "pool_4_cases_of_4": CASES * 2 * 4, "one_case_8_per_arm_x4_cases": CASES * 2 * 8},
              "power": rows, "even_spread_thresholds_of_16": thresholds()}
    (HERE / "sg2-pool-power.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
