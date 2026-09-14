#!/usr/bin/env python3
"""Independent outcome checks for the isolated Improve fixture (not runtime gates)."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
import random


def expected_union(ranges):
    """A half-integer grid oracle independent of sorted-interval merging."""
    points = sorted({point for start, end in ranges for point in range(2 * start, 2 * end + 1)})
    groups = []
    for point in points:
        if groups and point == groups[-1][1] + 1:
            groups[-1][1] = point
        else:
            groups.append([point, point])
    return [[start // 2, end // 2] for start, end in groups]


def grade(fixture: Path, *, extended: bool = False):
    spec = importlib.util.spec_from_file_location("experiment_ranges", fixture / "ranges.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    normalize = module.normalize_ranges
    results = []
    def check(name, inputs, expected=None, invalid=False):
        before = copy.deepcopy(inputs)
        try:
            actual = normalize(inputs)
            passed = not invalid and actual == expected and inputs == before
            detail = {"actual": actual, "expected": expected, "input_preserved": inputs == before}
        except Exception as exc:
            passed = invalid and isinstance(exc, ValueError) and inputs == before
            detail = {"exception": type(exc).__name__, "input_preserved": inputs == before}
        results.append({"case": name, "passed": passed, **detail})

    check("empty", [], [])
    check("ordinary_overlap", [[1, 3], [2, 4]], [[1, 4]])
    check("touching", [[1, 2], [2, 4]], [[1, 4]])
    check("contained", [[1, 10], [2, 3]], [[1, 10]])
    check("non_mutating_unsorted", [[4, 5], [1, 2]], [[1, 2], [4, 5]])
    check("reversed", [[4, 5], [3, 1]], invalid=True)
    check("boolean", [[True, 2]], invalid=True)
    check("wrong_type", [["1", 2]], invalid=True)
    check("wrong_shape", [[1, 2, 3]], invalid=True)
    check("missing_pair", [None], invalid=True)
    rng = random.Random(9142026)
    for index in range(200):
        intervals = [sorted([rng.randint(-10, 10), rng.randint(-10, 10)])
                     for _ in range(rng.randrange(9))]
        rng.shuffle(intervals)
        check(f"grid_union_{index:03d}", intervals, expected_union(intervals))
    if extended:
        # Post-review coverage supplement; keep the preregistered 210 intact.
        check("extra_tuple_pairs", [(4, 5), [1, 2], (2, 4)], [[1, 5]])
        check("extra_float_start", [[1.0, 2]], invalid=True)
        check("extra_float_end", [[1, 2.0]], invalid=True)
        check("extra_false_start", [[False, 2]], invalid=True)
        check("extra_false_end", [[-1, False]], invalid=True)
        check("extra_true_end", [[0, True]], invalid=True)
    return {"seed": 9142026, "suite": "extended" if extended else "primary", "checks": len(results),
            "passed": sum(r["passed"] for r in results),
            "failed": sum(not r["passed"] for r in results), "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--extended", action="store_true", help="Also run six post-review type/tuple checks; not part of the preregistered score.")
    args = parser.parse_args()
    result = grade(args.fixture.resolve(), extended=args.extended)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "results"}))
    raise SystemExit(bool(result["failed"]))
