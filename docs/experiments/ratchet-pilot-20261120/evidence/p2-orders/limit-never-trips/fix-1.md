## Fixed

- C-20 — Quantity validation accepted fractional text that rounded to an integer. It now checks the decimal digits in the original text.
- C-22 — Price validation had the same rounding gap. It now rejects fractional cents even when conversion produces an integer.
- C-30 — The parser trimmed keys and allowed unknown keys. It now requires the five exact spellings.
- C-31 — Missing fields slipped through or produced value errors. The parser now checks for all five fields before validating values.
- C-32 — A repeated key silently replaced the earlier value. It now raises `SyntaxError`, including when both values are equal.
- C-36 — Identifier conversion accepted empty text and returned nonfinite values for malformed input. An identifier now needs nonempty text that converts to a finite number.
- C-37 — Empty or whitespace-only price text converted to zero. It now raises `RangeError`.
- C-45 — `total` called `meter.tick()` 50 times per order. It now calls it once, including for zero-price orders.
- C-47 — Each total spent 50 times the intended shared budget. Repeated totals now consume only the number of orders processed.
- C-48 — Excess ticks caused totals to throw before processing all orders that fit the remaining budget. A total can now spend the last available tick and return its sum.
- C-67 — The project had no orders tests. Added coverage for parsed records, rejected input, cents, cumulative ticks, and the limit boundary.
- C-68 — `npm test` discovered only the meter suite. The same command now discovers and passes both suites.
- U-1 — The example produced the right cents with 100 ticks. It now returns 399 cents with two ticks.
- U-5 — Near-integer fractional input could evade range checks, and empty prices could pass as zero. These inputs now raise `RangeError` with the physical line number.
- U-7 — Unknown, missing, and repeated keys and invalid identifiers were accepted or reported with the wrong error type. They now raise `SyntaxError`.
- U-8 — Repeated totals overspent the shared budget. The example batches now bring the meter to two and then four ticks.
- U-9 — A batch of 10,000 orders ran out of ticks early. It now finishes at 10,000, and the first attempted tick beyond that propagates the meter's `LimitError`.
- U-12 — The default project test command did not exercise either orders helper. The new suite exercises both with the existing Node setup.

## Disputed

none

## Discoveries

- Floating-point conversion can erase a fractional value before the integer check | Observable: `Number.isInteger(Number('1.00000000000000001'))` returns `true`, and `Number('1e-400')` returns `0` | Why: Quantity and price need to check the original decimal digits, including the position set by any exponent.
- The parser already accepted numeric spellings beyond ordinary decimals | Observable: An order with `qty=0x2` and `price=1.50e2` parses with quantity `2` and price `150` | Why: The old parser used `Number()` and the specification leaves those spellings open, so validation preserves them when the value is a whole number.
