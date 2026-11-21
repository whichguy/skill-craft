## Failing now

- C-20 — `qty=1.00000000000000001` parses as quantity `1` instead of raising `RangeError`.
- C-22 — `price=150.000000000000001` parses as `150` cents instead of raising `RangeError`.
- C-30 — An extra `note` field is ignored, `ID=1` produces an ID of `NaN`, and `id =1` is accepted as ID `1`.
- C-31 — Omitting `id` or `shipped_at` still yields a record. Omitting `qty` or `price` raises `RangeError` instead of `SyntaxError`.
- C-32 — A repeated `qty` is accepted. When the values differ, the last value wins.
- C-36 — Empty, nonnumeric, and infinite IDs produce `0`, `NaN`, and `Infinity`, respectively.
- C-37 — An empty or whitespace-only price parses as zero cents.
- C-67 — `npm test` exercises the meter only. No discovered test exercises either orders helper.
- C-68 — `npm test` exits successfully after the two meter tests. The orders suite is absent.

The related scenarios U-5, U-7, and U-12 also fail.

## Discoveries

- State whether exponent notation and radix-prefixed integers are valid numeric spellings. | Observable: Parse a row containing `id=0x10;qty=1e2;price=0b11`. | Why: The current parser returns `16`, `100`, and `3`, respectively. C-35 leaves all three spellings open.
- Define whether a single carriage return can separate records. | Observable: Join two otherwise valid rows with a single `\r`. | Why: The current parser returned one record for the two rows. The specification covers LF and CRLF.
- Define the result when valid inputs produce a total outside the finite range of a JavaScript number. | Observable: Parse a price of 308 nines with quantity `2` and total that record. | Why: The parser accepts the price as `1e+308`, and the total returns `Infinity`.
