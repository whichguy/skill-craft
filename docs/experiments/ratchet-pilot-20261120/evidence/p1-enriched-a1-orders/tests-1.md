## Failing now

- C-12 — The parser accepts wrong-case and alternate key names, keys padded with spaces, and extra keys.
- C-13 — Omitting `id` returns an order with `id: NaN`. Omitting `shipped_at` on an open order returns an empty date. Omitting `qty` or `price` raises `RangeError` instead of `SyntaxError`.
- C-14 — Duplicate fields are accepted. For example, appending `;id=2` replaces the original ID.
- C-18 — Hexadecimal, binary, and octal spellings are accepted in all three numeric fields. Invalid and overflowing IDs can return `NaN` or `Infinity`. An empty price is converted to zero.
- C-20 — `id=` returns `0` and `id=abc` returns `NaN` instead of throwing `SyntaxError`.
- C-26 — `price=` returns `0` instead of throwing `RangeError`.
- C-36 — Unknown, missing, and duplicate keys and invalid IDs can return normally, so those cases produce no line diagnostic. The errors that were raised had the expected physical line labels.
- C-38 — When an unrecognized, missing, or duplicate key or an invalid ID competes with an invalid quantity or price, the parser reports the quantity or price `RangeError` first.
- C-61 — `npm test` never exercises `parseOrders`.
- C-62 — `npm test` never exercises `total`.
- C-63 — `npm test` exits 0 after two meter tests and exercises neither order helper.

U-4 also fails because the invalid ID on line 3 returns normally. U-8 fails because the package test run only exercises the meter.

## Discoveries

- A row error should identify the failed field or validation rule when competing rules use the same error class. | Observable: A line containing both `qty=0` and `price=-1` identifies quantity as the first failure. | Why: C-38 specifies an order that an error class and line number alone cannot always distinguish.
- A failed tick should leave the refused order's operands unread as well as those of all later orders. | Observable: Numeric operand getters on orders 10,001 and 10,002 are never called in an exhausted batch. | Why: The count in C-49 can still end at 10,001 if the refused order's operands were read before charging its tick.
