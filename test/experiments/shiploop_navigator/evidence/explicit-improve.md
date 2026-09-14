# Explicit improve trial snapshot

Archived observations; normalized paths are labels, not runnable commands.

Baseline: `c0b69050cdddbc89b3b1843bde1de15df8c1b7e1`. Final commit: `530948fee5941d243a19caf0ce2028584e7e93e1`.

Fixed oracle: 210/210; mismatches: 0.

## Final commit message

```text
Fix closed range normalization

Review: Cycle 1 found material SPEC.md violations in validation, immutability, touching-interval merging, containment, tests, and PLAN.md.

Plan: Validate inputs before copying, sort copied endpoints, merge closed touching or overlapping ranges while retaining the farthest end, and cover the required boundaries.

Changes: Updated ranges.py, test_ranges.py, and PLAN.md only.

Validation: PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_ranges; git diff --check.

Key learnings: Green baseline tests did not cover the closed-interval boundary or caller-data immutability.

Remaining work: Perform two current-candidate trivial-only Improve reviews; clean review streak is 0 after this material change.
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

1. Validate that the input is a list of two-item lists or tuples with integer,
   non-boolean endpoints and a non-reversed order. Raise `ValueError` for each
   invalid case before mutating any caller-owned data.
2. Copy validated endpoints, sort those copies, and merge only overlapping or
   touching closed intervals. Preserve the farthest endpoint when a later range
   is contained by an earlier one.
3. Return newly created two-item lists and cover empty input, sorting, overlap,
   touching boundaries, containment, gaps, immutability, and invalid input with
   unit tests.
4. Verify the implementation with `python3 -m unittest -v test_ranges`.
```

## ranges.py

```python
"""Utilities for normalizing closed integer ranges."""


def normalize_ranges(ranges):
    """Return sorted, disjoint copies of valid closed integer ranges.

    The input must be a list of two-item lists or tuples whose endpoints are
    integers other than booleans. Invalid input raises ``ValueError`` without
    mutating the caller's list or any nested pair.
    """
    if not isinstance(ranges, list):
        raise ValueError("ranges must be a list")

    copied_ranges = []
    for pair in ranges:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("each range must be a two-item list or tuple")

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

        copied_ranges.append((start, end))

    merged = []
    for start, end in sorted(copied_ranges):
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

    def test_sorts_and_merges_overlapping_and_touching_ranges(self):
        ranges = [[7, 9], [1, 2], [2, 4], [3, 8]]

        self.assertEqual(normalize_ranges(ranges), [[1, 9]])

    def test_contained_range_does_not_shorten_its_container(self):
        ranges = [[1, 10], [2, 3], [10, 12]]

        self.assertEqual(normalize_ranges(ranges), [[1, 12]])

    def test_consecutive_but_non_touching_ranges_remain_separate(self):
        self.assertEqual(normalize_ranges([[1, 2], [3, 4]]), [[1, 2], [3, 4]])

    def test_does_not_mutate_outer_list_or_nested_pairs(self):
        ranges = [[5, 7], (1, 3), [3, 5]]
        original_pairs = list(ranges)
        original_values = [tuple(pair) for pair in ranges]

        self.assertEqual(normalize_ranges(ranges), [[1, 7]])
        self.assertEqual(ranges, original_pairs)
        self.assertEqual([tuple(pair) for pair in ranges], original_values)
        self.assertIs(ranges[0], original_pairs[0])
        self.assertIs(ranges[1], original_pairs[1])
        self.assertIs(ranges[2], original_pairs[2])

    def test_rejects_invalid_shapes_endpoints_and_ordering(self):
        invalid_inputs = [
            ((1, 2),),
            [1],
            [[1]],
            [[1, 2, 3]],
            [[1, "2"]],
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

## Worker review record

# Improve review record — nav-f8a43c5cedbd48df8991e3ccc29d29ea

## Scope and identity

- Authorized fixture scope: `ranges.py`, `test_ranges.py`, and `PLAN.md` in
  `<EXPLICIT_TRIAL>/improve-fixture`.
- Required behavior source: fixture `SPEC.md`, preserved without modification.
- Baseline descriptor: `c0b69050cdddbc89b3b1843bde1de15df8c1b7e1`.
- Cycle 1 resulting candidate descriptor: `530948fee5941d243a19caf0ce2028584e7e93e1`.
- No accepted product-work evidence preceded this action; the navigator state
  reports the earlier transitions as synthetic setup only, so it was not used
  as proof of implementation or verification.

## Cycle 1 — material repair

### Review and history

At the start of this cycle, the complete reachable history window contained the
single baseline commit `c0b69050cdddbc89b3b1843bde1de15df8c1b7e1` (“Seed
isolated range fixture”). Its body explicitly said that the existing tests were
incomplete and that `SPEC.md` was authoritative.

The fresh read-only independent review of the baseline found material failures:
in-place sorting mutated caller data; reversed pairs were skipped; touching
closed intervals did not merge; contained ranges could shorten a result;
invalid pair shapes and endpoints did not reliably raise `ValueError`; the
plan described those forbidden behaviors; and the two baseline tests left the
contract-critical boundaries uncovered. Self-review confirmed each finding
against `SPEC.md` and the baseline source.

### Plan before application

1. Validate the outer list, pair type and shape, integer non-boolean endpoints,
   and endpoint order before any caller-owned data can change.
2. Copy valid pairs, sort the copies, merge overlap or shared-endpoint contact,
   and keep the maximum end for contained ranges.
3. Replace the obsolete plan and add focused tests for the required normal,
   boundary, immutability, and invalid-input behavior.

### Applied changes and classification

Implemented that plan in the three authorized files and committed it as
`530948fee5941d243a19caf0ce2028584e7e93e1` (`Fix closed range normalization`).
This was material work, so the clean-review streak remained `0` (before `0`,
after `0`). The commit body records Review, Plan, Changes, Validation, Key
learnings, and Remaining work.

### Checks and evidence

- Baseline check: `python3 -m unittest -v test_ranges` passed 2 tests, which
  confirmed only the inadequate original suite.
- Candidate check: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v
  test_ranges` passed all 6 focused tests.
- Patch hygiene: `git diff --check` passed before the commit.
- The test cases cover empty input; sorting; overlap; shared-endpoint touching;
  consecutive non-touching intervals; containment; tuple pairs and caller-data
  preservation; malformed shape; non-integer endpoints; both boolean endpoint
  positions; and reversed ranges.

### Learnings and limitation

Passing the baseline suite was not meaningful evidence of contract compliance;
the closed-interval boundary and mutation behavior needed explicit tests. The
independent reviewer assessed the baseline before application, then its
findings were verified in the repaired candidate by self-review. The packet
allowed one fresh independent reviewer, so there is no separate fresh
post-commit review; that is the remaining review limitation for this cycle.

The first Python test run generated untracked `__pycache__/ranges.cpython-314.pyc`
and `__pycache__/test_ranges.cpython-314.pyc` files. They are disposable
test-generated artifacts outside the authorized source scope, were not staged
or committed, and are retained because the host rejected their removal command.

## Cycle 2

### Review and history

Inspected the complete available seven-message window before this distinct
review: `530948fee5941d243a19caf0ce2028584e7e93e1` (`Fix closed range
normalization`) and the baseline `c0b69050cdddbc89b3b1843bde1de15df8c1b7e1`
(`Seed isolated range fixture`), including their full bodies. The repaired
candidate still consists only of the authorized three-file change against the
baseline; the only working-tree artifact is the previously disclosed untracked
test bytecode directory.

Self-review found no unresolved contract failure or worthwhile authorized
change. Validation occurs before the function creates or sorts copied pairs;
the merge condition is `start <= current_end`, which merges a shared endpoint
but not a consecutive integer; and `max(current_end, end)` prevents containment
from shortening the result. For the specification's representative trace,
`[[1, 2], [2, 4]]` becomes copied, sorted input and then `[[1, 4]]`; the gap
case `[[1, 2], [3, 4]]` takes the separate-range branch and remains two output
lists. The tests also exercise those branches, immutable mixed list/tuple
input, and the specified invalid categories.

### Plan, checks, and assessment

No change plan: additional code, documentation, or tests would be cosmetic or
redundant after this review, so none was applied and no empty commit was made.
`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_ranges` passed all 6
tests. `git diff --check c0b69050cdddbc89b3b1843bde1de15df8c1b7e1..HEAD`
also passed. This is a completed trivial-only/no-change review with no
unresolved material finding; clean-review streak `0 -> 1`.

The independent-review limitation remains the same as Cycle 1: the one fresh
reviewer evaluated the pre-repair baseline, and this current-candidate cycle
was self-reviewed.

## Cycle 3

### Review and history

Performed a separate current-candidate review after re-reading the same full
available history window: `530948fee5941d243a19caf0ce2028584e7e93e1` and
`c0b69050cdddbc89b3b1843bde1de15df8c1b7e1`. Inspected the complete three-file
diff from baseline and the resulting implementation, tests, and plan again.
The implementation still satisfies the contract without mutating input: it
builds tuple copies only after validation, sorts only those copies, uses a
shared-endpoint-or-overlap test for closed intervals, and retains the greatest
end. The test suite names and exercises each contract family, and the plan
matches the actual algorithm and verification command.

No unresolved material finding, missing required test, or worthwhile trivial
improvement emerged. No plan was necessary, no files were changed, and no empty
commit was manufactured.

### Checks and assessment

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_ranges` again passed all
6 tests. `git diff --check c0b69050cdddbc89b3b1843bde1de15df8c1b7e1..HEAD`
again passed, and the baseline comparison still lists only `PLAN.md`,
`ranges.py`, and `test_ranges.py`. This is the second distinct completed
trivial-only/no-change review with current checks and no unresolved material
finding; clean-review streak `1 -> 2`.

The post-change review remains self-review because the one permitted fresh
independent review was used for the pre-repair material-finding pass. The
untracked bytecode artifact remains excluded from the candidate and commit.

## Final assessment

The final inventory is the authorized three-file commit
`530948fee5941d243a19caf0ce2028584e7e93e1` plus the non-source untracked
test bytecode directory described above. `SPEC.md` remains unchanged. The
material repair is backed by current tests, then two consecutive distinct
trivial-only/no-change reviews; the Improve action has converged subject to the
recorded absence of a fresh post-change reviewer.

## Submitted completion

# ShipLoop navigator result

```shiploop-state
{
  "evidence_refs": [
    "<EXPLICIT_TRIAL>/improve-run/notes/nav-f8a43c5cedbd48df8991e3ccc29d29ea.md",
    "<EXPLICIT_TRIAL>/improve-fixture"
  ],
  "outcome": "done",
  "summary": "Repaired the authorized range-normalization candidate and committed 530948fee5941d243a19caf0ce2028584e7e93e1. Current focused tests pass (6/6), baseline diff hygiene passes, and two distinct current-candidate trivial-only/no-change reviews completed after the material repair. The durable record notes the one independent baseline review and the untracked test-bytecode artifact excluded from the commit."
}
```

## Parent-observed accepted action and next state

```json
{
  "history": [
    {
      "action": "nav-f8a43c5cedbd48df8991e3ccc29d29ea",
      "outcome": "done",
      "stage": "product-improve",
      "summary": "Repaired the authorized range-normalization candidate and committed 530948fee5941d243a19caf0ce2028584e7e93e1. Current focused tests pass (6/6), baseline diff hygiene passes, and two distinct current-candidate trivial-only/no-change reviews completed after the material repair. The durable record notes the one independent baseline review and the untracked test-bytecode artifact excluded from the commit.",
      "workitem": "W1"
    }
  ],
  "stage": "integrate",
  "status": "active",
  "current_action": {
    "id": "nav-4bbe3c04591f4dc8b0d538899fe5c12d",
    "stage": "integrate"
  }
}
```

## Post-run housekeeping

The worker left two Python bytecode files after a forced-removal command was rejected. The parent verified their exact fixture paths, regular-file status and Python bytecode signature, removed only those two files without force, and removed the empty cache directory. This happened after the worker record and did not change tracked files or test outcomes. The final fixture worktree is clean.
