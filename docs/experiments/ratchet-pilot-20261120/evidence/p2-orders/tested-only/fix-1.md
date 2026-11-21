## Fixed

- C-19 — The quantity check rejected only the literal `0` and missing values. It now enforces the inclusive minimum of 1.
- C-20 — Quantity validation now rejects empty, nonnumeric, nonfinite, and fractional values, including fractions that round to integers.
- C-22 — Price validation now examines the decimal digits so a fraction that rounds to whole cents still raises `RangeError`.
- C-30 — The field parser trimmed key names and accepted arbitrary keys. It now requires the five literal key spellings.
- C-31 — Missing fields fell through to coercion, defaults, or field-level errors. The parser now checks that all five keys are present before validating values.
- C-32 — A later field silently overwrote a repeated key. Repeated keys now raise `SyntaxError`, even when their values agree.
- C-34 — The parser already retained everything after the first equals sign, but the quantity check accepted `2=3`. Quantity validation now rejects the full value with `RangeError`.
- C-36 — Identifier conversion accepted blank and nonfinite results. The parser now requires nonempty text that converts to a finite number.
- C-37 — Numeric coercion turned empty price text into zero. The parser now rejects empty price text with `RangeError`.
- C-67 — Added `node:test` coverage for successful parsing, rejections, totals in cents, and the meter at and past its limit.
- C-68 — The existing `npm test` command now discovers and runs the orders tests alongside the meter tests.
- U-5 — Quantity and price validation now accepts the inclusive bounds and reports the physical line for out-of-range and fractional values.
- U-7 — Ambiguous field lists and unusable identifiers now produce line-numbered syntax errors.
- U-12 — The existing test command now exercises both order helpers and the meter without any setup changes.

## Disputed

none

## Discoveries

- Number conversion can erase a nonzero fraction by rounding or underflow | Observable: `Number.isInteger(Number('150.000000000000001'))` is true and `Number('1e-4000')` is zero | Why: validating the converted number alone accepts fractional prices as whole cents
- The parser retains JavaScript's existing numeric spellings for whole finite values, including exponent and radix notation | Observable: `qty=1200e-2` parses as 12 and `price=0x10` parses as 16 | Why: the specification leaves additional numeric spellings open, and the existing conversion already handled them
