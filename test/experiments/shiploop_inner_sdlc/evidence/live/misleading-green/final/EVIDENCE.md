# Worker evidence

## Material finding and regression

At the seed candidate, `allocate_cents(5, [1, 1, 1])` returned `[1, 1, 1]`.
Its shares summed to 3 rather than 5, which violates the immutable contract's
exact-total requirement. The added regression expects `[2, 2, 1]`, proving both
conservation and input-order allocation of the two remaining cents; it failed
before the repair.

## Applied repair

`allocate_cents` now computes floor shares once, then increments each earliest
share for `total_cents - sum(shares)` remaining cents. The input weights remain
read-only.

## Durable contract coverage

The unit suite also exercises an unequal remainder (`10` cents across `[1, 2,
3]`), verifies that this call leaves its input unchanged, covers the valid zero
total, and rejects boolean totals or weights, a zero weight, an empty list, and
a non-list weight collection.

## Current checks

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest -v`: 5 tests passed.
- A bounded standard-library check covered 17,340 valid allocations (totals
  0 through 50; 1 through 4 positive weights, each 1 through 4), verifying the
  specified result, exact total, and unchanged inputs. It also confirmed six
  invalid-input cases raise `ValueError`.

The navigator action's run note retains its review-cycle assessment and any
independent-review limitation or scope.
