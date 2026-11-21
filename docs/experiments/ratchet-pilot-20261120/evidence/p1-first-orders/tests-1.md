## Failing now

- C-13 Returned an order and ignored `extra=1`.
- C-14 Accepted `qty =1`. The `Qty=1` probe threw `RangeError`.
- C-15 Accepted a repeated `id=1`. A repeated `qty=2` replaced the original quantity.
- C-16 Returned `id: NaN` for a missing `id` and `shippedAt: ''` for a missing `shipped_at` on an open order.
- C-17 Threw `SyntaxError` with `line 1: field without =`.
- C-18 Threw `SyntaxError` for an empty field with the lowercase prefix `line 1: `.
- C-19 Threw `RangeError` for `qty=1=2` with the lowercase prefix `line 1: `.
- C-22 Returned `id: 0` for an empty ID and `id: Infinity` for `id=Infinity`.
- C-24 Threw `RangeError` for quantity zero with the lowercase prefix `line 1: `.
- C-25 Threw `RangeError` for an empty quantity with the lowercase prefix `line 1: `.
- C-27 Threw `RangeError` for a negative price with the lowercase prefix `line 1: `.
- C-28 Threw `RangeError` for a fractional price with the lowercase prefix `line 1: `.
- C-29 Returned `price: 0` for empty and whitespace-only price text.
- C-32 Threw `SyntaxError` for an empty status with the lowercase prefix `line 1: `.
- C-35 Threw `SyntaxError` for `26-10-01` with the lowercase prefix `line 1: `.
- C-37 Threw `SyntaxError` for a shipped order with an empty date and used `line 1: `.
- C-38 Threw `SyntaxError` for an open order with a date and used `line 1: `.
- C-39 Reported the correct physical line number for the quantity probe, using `line 4: `.
- C-40 Used `line 2: ` for the second physical line. The required prefix is `Line 2: `.
- C-41 Threw the first line's `RangeError` with the lowercase prefix `line 1: `.
- C-42 Threw `RangeError` for `qty=0` when an unknown field on the same line required a structural `SyntaxError` first.
- C-63 `npm test` exited with status 1. It ran 62 tests, with 41 passing and 21 failing.

## Discoveries

- Define the handling of a lone `\r` between records. | Observable: Parse two valid open records with different IDs joined by a lone `\r`. | Why: The current parser returned one order, and the specification names LF and CRLF.
- Totals use JavaScript `Number` arithmetic, including `Infinity` on overflow. | Observable: Parse an order with quantity `Number.MAX_VALUE` and price `2`, then total it. | Why: The parser accepted both amounts and `total` returned `Infinity`. The specification describes which amounts are accepted and leaves overflow behavior unspecified.
- Give validation errors a stable field identifier when validation precedence chooses between errors of the same class. | Observable: With both `qty=0` and `price=-1` on a line, the identifier names `qty` even when `price` appears first. | Why: Both failures require `RangeError` and the same line prefix, so the specified output cannot distinguish which validation ran first. The same issue applies to `status` and `shipped_at`.
