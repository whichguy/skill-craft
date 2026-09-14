# Initial improve trial snapshot

Archived observations; normalized paths are labels, not runnable commands.

Baseline: `5f980697b361af6cd4bcad7c438aee773771b916`. Final commit: `048f2e5f84f4b147b97c7826b6fff8a38e12db3d`.

Fixed oracle: 188/210; mismatches: 22.

## Final commit message

```text
Improve range normalization

Review:
Material defects in validation, immutability, adjacency merging, containment, and required coverage were fixed. Two subsequent clean review cycles reached streak 2.

Plan:
Validate inputs without mutation, normalize a sorted copy, and cover each required range behavior.

Changes:
Validate ranges and endpoints, merge touching ranges without shortening containment, expand unittest coverage, and update PLAN.md.

Validation:
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v (7 passed); git diff --check.

Key learnings:
A passing baseline suite did not cover the specification; disjoint sorted output needed its own regression case.

Remaining work:
None within the authorized fixture scope.
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
# Range normalization plan

1. Validate that the outer value is a list and every member is a two-element
   list or tuple with non-boolean integer endpoints in ascending order. Raise
   `ValueError` for invalid input without changing the caller's data.
2. Sort a validated copy, then merge overlapping or adjacent integer ranges
   while retaining the greatest end point when a range is contained.
3. Cover empty input, sorting, overlap, adjacency, containment, tuple pairs,
   immutability, malformed pairs, invalid endpoint types, booleans, and
   reversed ranges with `unittest`.

Validate with `python3 -m unittest -v`.
```

## ranges.py

```python
def normalize_ranges(ranges):
    if not isinstance(ranges, list):
        raise ValueError("ranges must be a list")

    validated_ranges = []
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
            raise ValueError("range endpoints must be integers")
        if start > end:
            raise ValueError("range start must not exceed range end")
        validated_ranges.append((start, end))

    merged = []
    for start, end in sorted(validated_ranges):
        if merged and start <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
```

## test_ranges.py

```python
import unittest
from copy import deepcopy

from ranges import normalize_ranges


class RangeTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(normalize_ranges([]), [])

    def test_sorts_and_merges_overlapping_and_touching_ranges(self):
        self.assertEqual(
            normalize_ranges([[6, 7], [1, 3], [3, 5], [8, 9]]),
            [[1, 9]],
        )

    def test_sorts_disjoint_ranges_without_merging_gaps(self):
        self.assertEqual(
            normalize_ranges([[10, 11], [4, 5], [1, 2]]),
            [[1, 2], [4, 5], [10, 11]],
        )

    def test_contained_range_does_not_shorten_its_container(self):
        self.assertEqual(normalize_ranges([[1, 10], [3, 4]]), [[1, 10]])

    def test_accepts_tuple_pairs_without_mutating_input(self):
        source = [[5, 6], (1, 3), [4, 4]]
        original = deepcopy(source)

        self.assertEqual(normalize_ranges(source), [[1, 6]])
        self.assertEqual(source, original)

    def test_rejects_invalid_pairs_and_endpoints(self):
        invalid_inputs = [
            [[1]],
            [[1, 2, 3]],
            ["not a pair"],
            [[1, "2"]],
            [[True, 2]],
            [[1, False]],
            [[3, 1]],
        ]

        for ranges in invalid_inputs:
            with self.subTest(ranges=ranges):
                with self.assertRaises(ValueError):
                    normalize_ranges(ranges)

    def test_rejects_a_non_list_outer_container(self):
        with self.assertRaises(ValueError):
            normalize_ranges(((1, 2),))

if __name__ == '__main__':
    unittest.main()
```

## Worker review record

# Improve review record: nav-059566cfe87542668b2f4e5c6008665e

## Scope and candidate identity

- Authorized repository: `<INITIAL_TRIAL>/improve-fixture`.
- Authorized product files: `ranges.py`, `test_ranges.py`, and `PLAN.md` only; `SPEC.md` was preserved.
- Baseline: `5f980697b361af6cd4bcad7c438aee773771b916` (`Seed isolated range fixture`).
- Resulting committed candidate: `048f2e5f84f4b147b97c7826b6fff8a38e12db3d` (`Improve range normalization`).
- No network, installation, dependency, remote, or publication action was used.

Each review cycle read the full reachable history window. The repository had one reachable commit, so its complete message was the available history for all three cycles. The seed commit correctly warned that its two passing tests did not establish complete specification coverage.

## Cycle 1 — material review and repair

**Findings and classification.** Material defects were found against `SPEC.md`: the implementation sorted the caller's list in place, silently skipped reversed ranges, did not validate pair shape or endpoint types, did not reject booleans, merged only strict overlaps, and could shorten a containing range. The original two tests did not exercise those required behaviors. A first corrected candidate also lacked a direct regression case proving that sorted separated ranges remain disjoint; that missing required coverage was treated as material and added before checks.

**Plan.** Validate every input pair before sorting a copy; merge overlaps and integer-adjacent ranges using the greatest end point; return new list pairs; and add meaningful specification-oriented tests. Update `PLAN.md` to describe the implementation and verification approach.

**Changes.** `ranges.py` now validates the outer list, pair shape, endpoints, booleans, and order without mutating caller data; normalizes a sorted validated copy; and uses `max()` while merging touching ranges. `test_ranges.py` covers empty input, sorting, overlap, adjacency, separated output, containment, tuple pairs, immutability, malformed pairs, invalid endpoints, booleans, reversed ranges, and a non-list outer container. `PLAN.md` matches that behavior.

**Checks.** The baseline `python3 -m unittest -v` passed 2 insufficient tests. After the changes, `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v` passed 7 tests, and `git diff --check` passed. Generated bytecode from the initial baseline check was identified as this action's disposable artifact and removed; later test runs suppressed bytecode generation.

**Streak.** 0 to 0: material defects and material edits reset convergence.

## Independent review

A fresh read-only reviewer scoped to the fixture, baseline, specification, and three authorized product files found no actionable correctness, security, scope, or specification-compliance issue. It independently ran the then-current six-test suite. The reviewer examined the first corrected candidate before the later test-only separated-output regression was added. The final test addition and subsequent clean cycles were self-reviewed; this is the residual review limitation, not a claim that the reviewer saw a later file version.

## Cycle 2 — clean review

The full available Git history, `SPEC.md`, final candidate diff, implementation, tests, and plan were re-read. Validation, non-mutation, touching merge, containment preservation, sorted disjoint output, and scoped documentation all matched the required behavior. No worthwhile change or unresolved material finding remained. `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v` passed 7 checks and the diff was whitespace-clean.

**Streak.** 0 to 1.

## Cycle 3 — clean review

The same full history window and current candidate were independently re-read as a distinct final pass. No new material finding, regression, consumer issue, or documentation mismatch was found. `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v` again passed all 7 tests.

**Streak.** 1 to 2. This established two consecutive completed clean reviews with current checks.

## Commit and final inventory

After checks, only `ranges.py`, `test_ranges.py`, and `PLAN.md` were staged and committed in `048f2e5`. The commit body records Review, Plan, Changes, Validation, Key learnings, and Remaining work. A post-commit seven-test run passed, `git diff --check 5f980697..HEAD` passed, and the fixture worktree was clean with no untracked artifacts. No remaining authorized product work was identified.

## Submitted completion

# ShipLoop navigator result

```shiploop-state
{
  "evidence_refs": [
    "<INITIAL_TRIAL>/improve-run/notes/nav-059566cfe87542668b2f4e5c6008665e.md"
  ],
  "outcome": "done",
  "summary": "Improved and committed the scoped range-normalization candidate as 048f2e5. Material validation, immutability, touching-merge, containment, plan, and coverage defects were repaired; two subsequent distinct clean reviews reached streak 2. Final committed check: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v (7 passed); working tree clean."
}
```

## Parent-observed accepted action and next state

```json
{
  "history": [
    {
      "action": "nav-059566cfe87542668b2f4e5c6008665e",
      "outcome": "done",
      "stage": "product-improve",
      "summary": "Improved and committed the scoped range-normalization candidate as 048f2e5. Material validation, immutability, touching-merge, containment, plan, and coverage defects were repaired; two subsequent distinct clean reviews reached streak 2. Final committed check: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v (7 passed); working tree clean.",
      "workitem": "W1"
    }
  ],
  "stage": "integrate",
  "status": "active",
  "current_action": {
    "id": "nav-6ca6da50eae94c4aa516d0285f6a748f",
    "stage": "integrate"
  }
}
```
