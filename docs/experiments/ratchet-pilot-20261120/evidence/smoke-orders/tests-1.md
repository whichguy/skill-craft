## Failing now

none

## Discoveries

- Quantity and price validation uses the rounded JavaScript numbers produced by conversion. | Observable: Parse `id=1;qty=0.99999999999999999;price=1e-324;status=open;shipped_at=` to get `qty === 1` and `price === 0`. | Why: The quantity rounds up to the minimum and the positive price underflows to zero before the whole-number and minimum checks.
- A total can overflow to `Infinity` even when all order values are finite. | Observable: Parse `id=1;qty=1e200;price=1e200;status=open;shipped_at=` and pass the result to `total` with a reset meter. It returns `Infinity` and uses one tick. | Why: The inputs pass finite whole-number validation and their product exceeds the finite range of JavaScript numbers.
- A total that exceeds the remaining tick budget keeps the ticks it used, including the first failed tick, and stops there. | Observable: Start at 9,999 ticks and total three valid orders. The call throws `LimitError` and the count is 10,001. Resetting the meter lets the same three orders complete using three ticks. | Why: The first order reaches the limit, the second consumes a tick and throws, and the third never reaches the meter.
