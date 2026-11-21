## Failing now

- C-25: The project’s `node:test` suite runs two meter cases. Neither case exercises `parseOrders` or `total`.
- C-26: `npm test` exits 0 after running only the two meter cases. It runs no order-helper cases.

## Discoveries

- The shared meter keeps the over-limit tick charged when a total fails. | Observable: Start at 9,999 ticks and total a batch of three orders. The call throws `meter.LimitError` and `meter.count()` is 10,001. | Why: The successful tick and the throwing tick both remain charged, and the error stops the batch before another order is metered.
