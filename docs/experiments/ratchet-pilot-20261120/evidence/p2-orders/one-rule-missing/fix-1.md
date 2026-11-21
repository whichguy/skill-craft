## Fixed

- C-16 — The parser used lowercase status for the allowed-status check only. It now uses the normalized value for the shipping-date check and the returned record.
- C-20 — A fractional quantity could round to an integer during conversion. The parser now checks whether the written decimal is whole.
- C-22 — A fractional price could round to a whole cent during conversion. Price now uses the same whole-number check as quantity.
- C-30 — The parser trimmed keys and accepted arbitrary names. It now requires the five literal key spellings.
- C-31 — Absent fields reached value validation or received implicit defaults. The parser now checks that all five keys are present before validating their values.
- C-32 — A repeated key silently replaced its earlier value. The parser now rejects the second occurrence.
- C-36 — Missing numeric text could coerce to zero, and nonfinite identifiers could reach the returned record. The parser now requires a nonempty identifier with a finite numeric value.
- C-37 — An empty price coerced to zero. The parser now rejects an empty price with `RangeError`.
- C-54 — The example in a fresh Node process returned `Open`. The normalized record now matches the example and totals 399 cents with the existing setup.
- C-55 — Parsing caller-supplied text returned the original status casing. It now returns the lowercase status.
- C-67 — The project lacked discoverable orders tests. The new `node:test` suite exercises successful parsing, rejection, totaling, and the meter boundary.
- C-68 — `npm test` exercised only the meter. The existing command now discovers and passes both suites.
- U-1 — The example returned `Open` for the first record. It now returns `open`, and the parsed records total 399 cents in two ticks.
- U-2 — Formatted input retained mixed-case status or failed the shipping-date check. Both statuses now use the same normalization for LF and CRLF input.
- U-3 — Successive batches returned records with the original status casing. Each batch now returns normalized records in input order.
- U-5 — The valid lower-bound record returned `Open`, and rounded fractions or an empty price could be accepted. Status is now normalized and invalid numeric values raise `RangeError` with their physical line number.
- U-7 — Unknown, missing, and repeated keys and unusable identifiers could slip through validation or produce a numeric error. The parser now raises `SyntaxError` for those fields.
- U-10 — Large batches returned `Open` for each record. They now return lowercase status while leaving the meter count alone.
- U-12 — The fresh-process example returned the wrong status casing, and project test discovery lacked orders coverage. Both paths now work with the existing setup.

## Disputed

none

## Discoveries

- JavaScript conversion can hide a nonzero fractional part through rounding or underflow | Observable: `Number.isInteger(Number('1.00000000000000001'))` and `Number.isInteger(Number('1e-999'))` both return `true` | Why: The parser must inspect the decimal digits to reject fractional input while retaining support for whole values above the safe-integer ceiling.
