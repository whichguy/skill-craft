## Failing now

none

## Discoveries

- Within the meter budget, `total` returns positive zero when every order amount is negative zero. | Observable: Take the order parsed from `id=1;qty=1;price=-0;status=open;shipped_at=` and call `total([order])` and `total([order, order])`, resetting the meter before each call. `Object.is(result, 0)` is true in both cases. | Why: The parsed price and the product retain negative zero, but adding the product to the initial positive-zero sum yields positive zero.
