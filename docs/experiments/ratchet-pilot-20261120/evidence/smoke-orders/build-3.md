## Done

- C-1 through C-73. The existing orders and meter implementation, tests, and package configuration satisfy these clauses. The frozen acceptance gate covers this range. `npm test` passed all 21 tests, including all 18 existing cases, and the JavaScript syntax checks passed.
- C-74. The parser already checks status, date format, and status and date consistency in that order after validating the numbers. Added a regression test for the diagnostic at each step. The README already describes this order.
- C-75. The parser already preserves negative zero in `id` and `price`. Added regression coverage for explicit `-0` and negative underflow, and documented both in the README.
- C-76. `total` already adds order amounts in input array order. Added a regression test showing that different orders of the same amounts produce different rounded totals, and documented this behavior in the README.

## Not done

none

## Discoveries

- `total` returns positive zero when every order amount is negative zero. | Observable: Pass `parseOrders('id=1;qty=1;price=-0;status=open;shipped_at=')` to `total` and check `Object.is(result, 0)`. It returns `true`. | Why: The price and the product retain negative zero. Adding the product to the initial positive-zero running sum yields positive zero.
