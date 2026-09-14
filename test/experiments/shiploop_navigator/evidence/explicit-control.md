# Explicit control trial snapshot

Archived observations; normalized paths are labels, not runnable commands.

Baseline: `c0b69050cdddbc89b3b1843bde1de15df8c1b7e1`. Final commit: `5feb37d04870bbd31ddc61c08456d61e4a07026d`.

Fixed oracle: 210/210; mismatches: 0.

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

These are closed intervals on a continuous number line, with integer endpoints.
Touching means a shared endpoint, not merely consecutive integer values.
For example, [[1, 2], [2, 4]] becomes [[1, 4]], while [[1, 2], [3, 4]] stays
[[1, 2], [3, 4]] because the gap between 2 and 3 must remain.
```

## PLAN.md

```markdown
# Range normalization implementation plan

1. Validate that the outer value is a list and every item is a two-element
   list or tuple. Reject non-integer endpoints (including booleans) and
   reversed ranges with `ValueError`.
2. Copy validated pairs into a working list before sorting, preserving both the
   caller's outer list and every nested pair.
3. Sort copied pairs and merge when the next start is less than or equal to the
   current end. Keep the larger end so a contained range cannot shorten its
   container. This treats touching as a shared endpoint, not integer adjacency.
4. Exercise empty input, sorting, overlap, touching, a one-integer gap,
   containment, tuple pairs, immutability, and every specified invalid-input
   category with `unittest`.
```

## ranges.py

```python
"""Normalize closed integer ranges without modifying the caller's input."""


def normalize_ranges(ranges):
    """Return sorted, disjoint copies of closed integer ranges.

    Input pairs may be lists or tuples. Invalid input is rejected before any
    sorting or merging so the caller's list and nested pairs remain unchanged.
    """
    if not isinstance(ranges, list):
        raise ValueError("ranges must be a list of two-element lists or tuples")

    validated = []
    for pair in ranges:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("each range must be a two-element list or tuple")

        start, end = pair
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
        ):
            raise ValueError("range endpoints must be integers, not booleans")
        if start > end:
            raise ValueError("range start must not exceed range end")

        validated.append([start, end])

    validated.sort()
    merged = []
    for start, end in validated:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
```

## test_ranges.py

```python
import unittest

from ranges import normalize_ranges


class RangeTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(normalize_ranges([]), [])

    def test_sorts_and_merges_overlapping_ranges(self):
        self.assertEqual(
            normalize_ranges([[5, 8], [1, 3], [2, 6]]),
            [[1, 8]],
        )

    def test_merges_touching_ranges(self):
        self.assertEqual(normalize_ranges([[1, 2], [2, 4]]), [[1, 4]])

    def test_keeps_consecutive_but_non_touching_ranges_separate(self):
        self.assertEqual(normalize_ranges([[1, 2], [3, 4]]), [[1, 2], [3, 4]])

    def test_contained_range_does_not_shorten_its_container(self):
        self.assertEqual(normalize_ranges([[1, 10], [3, 4]]), [[1, 10]])

    def test_accepts_tuple_pairs(self):
        self.assertEqual(normalize_ranges([(4, 5), (1, 2)]), [[1, 2], [4, 5]])

    def test_does_not_mutate_outer_list_or_nested_pairs(self):
        ranges = [[5, 7], [1, 5], (9, 10)]
        original_outer = list(ranges)
        original_pairs = [pair[:] if isinstance(pair, list) else pair for pair in ranges]

        self.assertEqual(normalize_ranges(ranges), [[1, 7], [9, 10]])
        self.assertEqual(ranges, original_outer)
        self.assertEqual(ranges, original_pairs)

    def test_rejects_invalid_endpoints(self):
        for invalid in ([[True, 2]], [[1, False]], [[1.0, 2]], [["1", 2]]):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    normalize_ranges(invalid)

    def test_rejects_invalid_pair_shapes(self):
        for invalid in ([1, 2], [[1]], [[1, 2, 3]], ["ab"]):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    normalize_ranges(invalid)

    def test_rejects_reversed_ranges(self):
        with self.assertRaises(ValueError):
            normalize_ranges([[4, 3]])


if __name__ == "__main__":
    unittest.main()
```

## EXPERIMENT.md

```markdown
# Single engineering-pass record

## Work completed

- Read the fixture's seed history and `SPEC.md`, then replaced the incomplete
  in-place normalization logic with validate-copy-sort-merge behavior.
- `normalize_ranges` now rejects malformed pairs, non-integer endpoints
  (including booleans), and reversed ranges with `ValueError`.
- Merging covers overlap and shared-endpoint touching, retains the larger end
  for contained ranges, and leaves a one-integer gap separate.
- Expanded `test_ranges.py` and updated `PLAN.md` to describe and exercise the
  stated contract.

## Checks run

- `python3 -m unittest -v` — 10 tests passed.
- `python3 -m py_compile ranges.py test_ranges.py` — passed.
- `git diff --check` — passed.

## Scope and limitations

- This was one bounded implementation and test pass in this fixture only; no
  dependency installation, network access, publication, broader campaign, or
  independent review was performed.
- The function intentionally accepts the documented outer `list` and nested
  `list`/`tuple` pair forms; other collection types raise `ValueError`.
```
