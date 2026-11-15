#!/usr/bin/env python3
"""Rates with exact 95 percent intervals from serve_race_probe.py's JSON lines.

    python3 rate_summary.py matrix.jsonl [more.jsonl ...]

One line per row: calls, early exits (and their error codes), the rate per call, and the Clopper-Pearson 95 percent interval of that rate;
then the same for the two kinds of collision together (an early exit, and a foreign listener: another candidate holding the port).
"""

import json
import math
import sys


def binom_cdf(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def interval(k: int, n: int) -> tuple[float, float]:
    """Clopper-Pearson: the p at which the chance of k or fewer is 2.5 percent (upper) and of k or more is 2.5 percent (lower)."""
    def solve(f, lo=0.0, hi=1.0):
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) else (lo, mid)
        return (lo + hi) / 2
    upper = 1.0 if k == n else solve(lambda p: binom_cdf(k, n, p) > 0.025)
    lower = 0.0 if k == 0 else solve(lambda p: 1 - binom_cdf(k - 1, n, p) < 0.025)
    return lower, upper


if __name__ == "__main__":
    for path in sys.argv[1:]:
        for line in open(path):
            row = json.loads(line)
            early, n = row["outcomes"].get("early exit", 0), row["calls"]
            lo, hi = interval(early, n)
            other = {k: v for k, v in row["outcomes"].items() if k not in ("passed", "early exit", "passed after retry")}
            retried = row["outcomes"].get("passed after retry", 0)
            collisions = early + row["outcomes"].get("foreign listener", 0)
            clo, chi = interval(collisions, n)
            print(f"{row['tag']:12} workers={row['workers']:2} calls={n:5} retried={retried:2} early_exits={early:2} {row['early_exit_codes']} other={other} "
                  f"rate={100 * early / n:.3f}% (95%: {100 * lo:.3f}% to {100 * hi:.3f}%); collisions={collisions} "
                  f"{100 * collisions / n:.3f}% (95%: {100 * clo:.3f}% to {100 * chi:.3f}%); window median {row['window_s']['median']} s "
                  f"max {row['window_s']['max']} s, {row['seconds']} s, load {row['load1_at_end']:.0f}")
