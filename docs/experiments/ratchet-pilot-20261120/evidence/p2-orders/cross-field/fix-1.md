## Fixed

- C-20 — Converting quantity text to a number rounded some fractions to integers. The parser now checks the written decimal digits, including scientific notation. For the numeric spellings left open by C-35, it uses JavaScript's numeric conversion.
- C-22 — The price check had the same rounding problem. It now rejects written fractions, including ones that round to zero.
- C-26 — A shipped record could have an empty `shipped_at` value. It now requires a date.
- C-27 — An open record could have a date. It now requires an empty `shipped_at` value.
- C-30 — The parser accepted unexpected keys and trimmed key whitespace. It now requires the five literal key spellings.
- C-31 — Missing fields could be accepted or cause a value error. The parser now checks for all required keys before validating values.
- C-32 — A repeated field overwrote the earlier value. The parser now rejects any repeated key.
- C-36 — Empty, nonnumeric, and infinite identifiers passed through numeric conversion. The parser now requires nonempty identifier text with a finite numeric value.
- C-37 — JavaScript converted the empty price to zero. The parser now requires nonempty price text.
- C-67 — The project lacked orders tests. The new `node:test` suite covers successful and rejected parsing, totals in cents, and totals at and beyond the meter limit.
- C-68 — `npm test` exercised only the meter. Its existing discovery now runs both suites.
- U-5 — Fractions rounded to whole numbers passed the lower-bound scenario. The exact decimal check now rejects them and the error gives the physical line.
- U-6 — Status and date were validated independently. Both inconsistent combinations now raise a line-numbered `SyntaxError`.
- U-7 — The parser accepted ambiguous field lists and invalid identifiers. It now validates literal keys, presence, uniqueness, and identifier values.
- U-12 — The existing test command omitted the order helpers because the project had no orders suite. It now discovers and runs the orders tests.

## Disputed

none

## Discoveries

- JavaScript can round a written nonzero decimal fraction to an integer or underflow it to zero. | Observable: `Number('1.00000000000000001')` is `1` and `Number('1e-400')` is `0`. | Why: Checking only the converted number accepted inputs that violate the whole-number rule.
- The workflow check records actual helper invocations during `npm test`. | Observable: C-67 compares the length of the array passed to `total` with the remaining meter budget at the start of the call. | Why: The boundary coverage needs to exercise the helper using the shared meter.
