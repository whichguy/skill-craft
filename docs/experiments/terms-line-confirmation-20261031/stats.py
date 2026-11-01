"""The decision statistics of README.md: the harness's exact one-sided permutation test and a paired sign-flip test.

``permutation_p`` is test/shiploop_e2e/experiment.py's ``permutation_p`` (the `decide` rule since a9e398e9), copied so
this folder imports no harness module; values are rounded to 4 decimals first, as that function's docstring advises.
"""
import itertools
from collections import Counter
from decimal import Decimal
from math import comb


def permutation_p(control: list[float], candidate: list[float]) -> float:
    """The exact one-sided p that ``candidate``'s mean exceeds ``control``'s by chance (experiment.py, unchanged)."""
    values = [Decimal(repr(round(float(v), 4))) for v in control + candidate]
    exponent = min(v.as_tuple().exponent for v in values)
    scaled = [int(v.scaleb(-exponent)) for v in values]
    n_control = len(control)
    observed = sum(scaled[:n_control])
    ways = [Counter() for _ in range(n_control + 1)]
    ways[0][0] = 1
    for number, value in enumerate(scaled, start=1):
        for size in range(min(number, n_control), 0, -1):
            for total, count in list(ways[size - 1].items()):
                ways[size][total + value] += count
    return sum(count for total, count in ways[n_control].items() if total <= observed) / comb(len(scaled), n_control)


def sign_flip_p(control: list[float], candidate: list[float]) -> float:
    """Exact one-sided p for paired samples: the share of the 2^n sign patterns of the differences whose mean is at
    least the observed one (ties count against the candidate)."""
    diffs = [round(b - a, 6) for a, b in zip(control, candidate)]
    observed = sum(diffs)
    count = total = 0
    for signs in itertools.product((1, -1), repeat=len(diffs)):
        total += 1
        if sum(s * d for s, d in zip(signs, diffs)) >= observed - 1e-9:
            count += 1
    return count / total


def mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else float("nan")
