## Done

- C-1–C-2. Exported `parseOrders` and `total` from `src/orders.js`.
- C-3–C-19. Implemented string input, physical lines, blank line handling, field parsing and normalized order objects.
- C-20–C-34. Implemented numeric conversion, finite IDs and whole-number bounds for quantity and price.
- C-35–C-44. Implemented status and date validation, error ordering and physical line numbers. Parsing consumes zero meter ticks.
- C-45–C-52. Implemented the cents sum with one tick per order, the shared meter's limit and error propagation, and read-only access to orders.
- C-53–C-58. Added `node:test` coverage for parsing, totals and meter use. `npm test` passes with the existing runner and meter tests.
- C-59–C-68. Used the existing meter API and its established counting, reset and error behavior.
- Updated the README with the input format, return values, errors and shared tick budget.

## Not done

none

## Discoveries

- Within a validation category, quantity is checked before price, and ID is checked before status and shipping date. | Observable: `id=abc;qty=0;price=-1;status=pending;shipped_at=` reports the quantity error. With `qty=1` and `price=0`, it reports the ID error. | Why: C-42 and C-43 order categories without specifying which value error wins within each category.
- Totals use JavaScript `Number` arithmetic, including its precision and overflow behavior. | Observable: A parsed order with `qty=1e200` and `price=1e200` totals to `Infinity` with a fresh meter. | Why: C-34 allows finite whole inputs beyond the safe-integer range, and C-45 specifies multiplication and addition.
- A total that exceeds the budget stops at the first failed tick and retains the ticks already consumed, including the failed tick. | Observable: Start with 9,999 ticks and total three valid orders. The call throws and the count is 10,001. | Why: The meter counts a tick before enforcing its limit, and `total` propagates that error immediately.
