# Initial control trial snapshot

Archived observations; normalized paths are labels, not runnable commands.

Baseline: `2c1e1448a19e85420b181f268e536cc184f7d4cb`. Final commit: `271a99c072a227eb61715bef3921fa76f6efd8b9`.

Fixed oracle: 188/210; mismatches: 22.

## Final commit message

```text
Fix range normalization contract
```

## SPEC.md

```markdown
# Range normalization contract

`normalize_ranges(ranges)` takes a list of two-element lists or tuples. Both
endpoints must be integers; booleans are invalid. Start must not exceed end.
Invalid endpoints, pair shape, or reversed ranges raise ValueError.
Return sorted, disjoint two-element lists. Merge overlap AND touching endpoints.
A contained range must never shorten the containing range. Empty input returns
an empty list. Neither the caller's outer list nor its nested pairs may change.

Keep this a small standard-library function. No dependencies, network, installs,
or publication. Improve the implementation, test cases, and PLAN.md together.
```

## PLAN.md

```markdown
# Current implementation plan

Validate each supplied pair before processing so malformed shapes, non-integer
endpoints (including booleans), and reversed bounds raise `ValueError` without
changing caller data. Copy valid pairs, sort those copies, then merge overlap
and integer-adjacent ranges while retaining the farthest endpoint. Tests cover
empty input, ordering, overlap, touching bounds, containment, immutability, and
the validation failures required by the contract.
```

## ranges.py

```python
"""Normalize inclusive integer ranges without mutating the caller's input."""


def normalize_ranges(ranges):
    """Return sorted, merged copies of valid inclusive integer ranges.

    ``ranges`` must be a list of two-item lists or tuples whose endpoints are
    non-boolean integers and whose start does not exceed its end.
    """
    if not isinstance(ranges, list):
        raise ValueError("ranges must be a list")

    validated = []
    for pair in ranges:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("each range must be a two-element list or tuple")

        start, end = pair
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
        ):
            raise ValueError("range endpoints must be integers, not booleans")
        if start > end:
            raise ValueError("range start must not exceed its end")
        validated.append([start, end])

    validated.sort()
    merged = []
    for start, end in validated:
        if merged and start <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
```

## test_ranges.py

```python
import copy
import unittest

from ranges import normalize_ranges


class RangeTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(normalize_ranges([]), [])

    def test_sorts_and_merges_overlapping_ranges(self):
        self.assertEqual(
            normalize_ranges([[8, 10], (1, 4), [3, 6]]), [[1, 6], [8, 10]]
        )

    def test_merges_touching_ranges(self):
        self.assertEqual(normalize_ranges([[4, 6], [1, 3]]), [[1, 6]])

    def test_contained_range_does_not_shorten_endpoint(self):
        self.assertEqual(normalize_ranges([[1, 10], [3, 4], [8, 12]]), [[1, 12]])

    def test_keeps_disjoint_ranges(self):
        self.assertEqual(
            normalize_ranges([[9, 10], [1, 2], [5, 6]]),
            [[1, 2], [5, 6], [9, 10]],
        )

    def test_does_not_mutate_outer_list_or_nested_pairs(self):
        ranges = [[5, 6], (1, 3), [3, 4]]
        original = copy.deepcopy(ranges)

        normalize_ranges(ranges)

        self.assertEqual(ranges, original)

    def test_rejects_invalid_shapes_endpoints_and_reversed_ranges(self):
        invalid_inputs = [
            None,
            [[1]],
            [[1, 2, 3]],
            ["12"],
            [[1, 2.0]],
            [[True, 2]],
            [[1, False]],
            [[3, 2]],
        ]

        for ranges in invalid_inputs:
            with self.subTest(ranges=ranges):
                with self.assertRaises(ValueError):
                    normalize_ranges(ranges)


if __name__ == "__main__":
    unittest.main()
```

## EXPERIMENT.md

```markdown
# Single-pass control evidence

- Scope: reviewed only this fixture's seed commit, `SPEC.md`, and the three
  authorized implementation artifacts; `SPEC.md` remains unchanged.
- Baseline: `python3 -m unittest -v` passed the two seed tests, which did not
  cover the full contract.
- Pass: validate and copy inputs before sorting; merge inclusive overlap and
  adjacent integer ranges; add focused contract tests and update the plan.
- Final validation: `python3 -m unittest -v` passed all 7 tests.
```
