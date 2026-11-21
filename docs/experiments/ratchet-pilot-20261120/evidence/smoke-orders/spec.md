### C-1: `src/orders.js` exports a function named `parseOrders`.
Observable: `typeof require('./src/orders.js').parseOrders` is `'function'`.
Source: request

### C-2: `src/orders.js` exports a function named `total`.
Observable: `typeof require('./src/orders.js').total` is `'function'`.
Source: request

### C-3: `parseOrders` rejects non-string arguments with `TypeError`.
Observable: Calling `parseOrders` with no argument or with `null`, `1`, `false`, `{}`, `[]`, or `new String('')` throws `TypeError` in each case.
Source: request

### C-4: `parseOrders` skips blank lines.
Observable: `parseOrders('')` and `parseOrders('\n \t\n\n')` each return `[]`.
Source: request

### C-5: `parseOrders` returns one order object per non-blank line in input order.
Observable: `parseOrders('id=1;qty=2;price=150;status=Open;shipped_at=\n\nid=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01')` deep-equals `[{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}]`.
Source: request

### C-6: `parseOrders` splits input into physical lines at LF characters.
Observable: `parseOrders('id=1;qty=2;price=150;status=\ropen;shipped_at=\r\n\r\nid=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01\r\n')` returns `[{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}]`.
Source: choice: Splitting at LF handles LF and CRLF input through the same value-trimming rule.

### C-7: `parseOrders` trims surrounding whitespace from each field value before interpreting it.
Observable: `parseOrders('id= 1 ;qty=\t2\t;price= 150 ;status= Shipped ;shipped_at= 2026-10-01 ')` returns `[{id:1,qty:2,price:150,status:'shipped',shippedAt:'2026-10-01'}]`.
Source: request

### C-8: `parseOrders` returns `id` as a number.
Observable: The first order from `parseOrders('id=12;qty=2;price=150;status=open;shipped_at=')` has `id === 12`.
Source: request

### C-9: `parseOrders` returns `qty` as a number.
Observable: The first order from `parseOrders('id=1;qty=2;price=150;status=open;shipped_at=')` has `qty === 2`.
Source: request

### C-10: `parseOrders` returns `price` as a number of cents.
Observable: The first order from `parseOrders('id=1;qty=2;price=150;status=open;shipped_at=')` has `price === 150`.
Source: request

### C-11: `parseOrders` lowercases the status value.
Observable: `parseOrders('id=1;qty=2;price=150;status=oPeN;shipped_at=\nid=2;qty=1;price=99;status=sHiPpEd;shipped_at=2026-10-01')` returns orders with statuses `['open', 'shipped']` in that order.
Source: request

### C-12: `parseOrders` exposes a nonempty `shipped_at` value as text in `shippedAt`.
Observable: The first order from `parseOrders('id=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01')` has `shippedAt === '2026-10-01'`.
Source: request

### C-13: `parseOrders` represents an empty `shipped_at` value as `''` in `shippedAt`.
Observable: The first order from `parseOrders('id=1;qty=2;price=150;status=open;shipped_at= \t ')` has `shippedAt === ''`.
Source: request

### C-14: `parseOrders` recognizes the field keys by their exact spelling.
Observable: For `id=1;qty=2;price=150;status=open;shipped_at=`, replacing `id=1` with `ID=1`, replacing it with `id =1`, or appending `;note=x` each produces `SyntaxError` naming line 1.
Source: choice: The request lists the available keys and specifies trimming for values.

### C-15: `parseOrders` requires every listed key on each non-blank line.
Observable: Removing any single field and its adjoining separator from `id=1;qty=2;price=150;status=open;shipped_at=` produces `SyntaxError` naming line 1, including when the omitted field is `shipped_at=`.
Source: choice: The record has a fixed set of fields, with `shipped_at=` representing the empty value explicitly.

### C-16: `parseOrders` rejects a repeated key on the same line with `SyntaxError`.
Observable: Both `parseOrders('id=1;qty=2;price=150;status=open;shipped_at=;qty=2')` and `parseOrders('id=1;qty=2;price=150;status=open;shipped_at=;qty=3')` throw `SyntaxError` naming line 1.
Source: choice: Each field maps to a single property, so a repeated key is ambiguous.

### C-17: `parseOrders` accepts the fields in any order on a line.
Observable: `parseOrders('status=Open;price=150;shipped_at=;id=1;qty=2')` returns `[{id:1,qty:2,price:150,status:'open',shippedAt:''}]`.
Source: choice: The key identifies the field independently of its position.

### C-18: `parseOrders` throws `SyntaxError` for any semicolon-delimited field without an `=`.
Observable: Given `id=1;qty=2;price=150;status=open;shipped_at=`, appending `;memo`, appending `;`, prepending `;`, or replacing `;qty=` with `;;qty=` each produces `SyntaxError` naming line 1.
Source: request

### C-19: `parseOrders` uses the first `=` in each field as the key-value separator.
Observable: `parseOrders('id=1;qty=2=3;price=150;status=open;shipped_at=')` throws `RangeError` naming line 1 because the quantity text is `2=3`.
Source: choice: Keeping the full text after the separator lets field validation detect an invalid value.

### C-20: `parseOrders` converts nonempty numeric field values using JavaScript `Number` conversion.
Observable: `parseOrders('id=+1;qty=2e0;price=0x96;status=open;shipped_at=')` returns `[{id:1,qty:2,price:150,status:'open',shippedAt:''}]`.
Source: choice: JavaScript's number conversion defines the numeric spelling without a separate input grammar.

### C-21: `parseOrders` requires a finite numeric value for `id`.
Observable: In `id=1;qty=2;price=150;status=open;shipped_at=`, substituting `''`, `'abc'`, `'NaN'`, or `'Infinity'` for the id value each produces `SyntaxError` naming line 1.
Source: choice: A missing or nonfinite id value is malformed, with no id range specified.

### C-22: `parseOrders` accepts finite fractional or negative values for `id`.
Observable: `parseOrders('id=-1.5;qty=2;price=150;status=open;shipped_at=')` returns `[{id:-1.5,qty:2,price:150,status:'open',shippedAt:''}]`.
Source: choice: The request constrains the integrality and minimums of `qty` and `price` only.

### C-23: `parseOrders` accepts the same `id` on separate lines.
Observable: `parseOrders('id=1;qty=1;price=150;status=open;shipped_at=\nid=1;qty=2;price=150;status=open;shipped_at=')` returns `[{id:1,qty:1,price:150,status:'open',shippedAt:''},{id:1,qty:2,price:150,status:'open',shippedAt:''}]`.
Source: choice: Each line represents an order independently, with no uniqueness rule for ids.

### C-24: `parseOrders` accepts `1` as the minimum quantity.
Observable: The first order from `parseOrders('id=1;qty=1;price=150;status=open;shipped_at=')` has `qty === 1`.
Source: request

### C-25: `parseOrders` rejects a quantity below `1` with `RangeError`.
Observable: In `id=1;qty=2;price=150;status=open;shipped_at=`, substituting `'0'` or `'-1'` for the quantity each produces `RangeError` naming line 1.
Source: request

### C-26: `parseOrders` throws `RangeError` for a converted quantity with a fractional part.
Observable: `parseOrders('id=1;qty=1.5;price=150;status=open;shipped_at=')` throws `RangeError` naming line 1.
Source: request

### C-27: `parseOrders` rejects any quantity text that fails to yield a finite number with `RangeError`.
Observable: In `id=1;qty=2;price=150;status=open;shipped_at=`, substituting `'2x'`, `'NaN'`, or `'Infinity'` for the quantity each produces `RangeError` naming line 1.
Source: request

### C-28: `parseOrders` rejects an empty quantity with `RangeError`.
Observable: `parseOrders('id=1;qty= \t ;price=150;status=open;shipped_at=')` throws `RangeError` naming line 1.
Source: request

### C-29: `parseOrders` accepts `0` as the minimum price in cents.
Observable: The first order from `parseOrders('id=1;qty=2;price=0;status=open;shipped_at=')` has `price === 0`.
Source: request

### C-30: `parseOrders` rejects a negative price with `RangeError`.
Observable: `parseOrders('id=1;qty=2;price=-1;status=open;shipped_at=')` throws `RangeError` naming line 1.
Source: request

### C-31: `parseOrders` throws `RangeError` for a converted price with a fractional part.
Observable: `parseOrders('id=1;qty=2;price=0.5;status=open;shipped_at=')` throws `RangeError` naming line 1.
Source: request

### C-32: `parseOrders` rejects any price text that fails to yield a finite number with `RangeError`.
Observable: In `id=1;qty=2;price=150;status=open;shipped_at=`, substituting `'150x'`, `'NaN'`, or `'Infinity'` for the price each produces `RangeError` naming line 1.
Source: request

### C-33: `parseOrders` rejects an empty price with `RangeError`.
Observable: `parseOrders('id=1;qty=2;price= \t ;status=open;shipped_at=')` throws `RangeError` naming line 1.
Source: choice: An empty numeric field supplies no value, even though JavaScript converts `''` to `0`.

### C-34: `parseOrders` accepts converted finite whole values beyond JavaScript's safe integer range when they satisfy the stated minimums.
Observable: `parseOrders('id=1;qty=9007199254740992;price=9007199254740992;status=open;shipped_at=')` returns `[{id:1,qty:9007199254740992,price:9007199254740992,status:'open',shippedAt:''}]`.
Source: choice: The request sets lower bounds for quantity and price, with JavaScript numbers as the output type.

### C-35: `parseOrders` rejects any normalized status outside `open` or `shipped` with `SyntaxError`.
Observable: In `id=1;qty=2;price=150;status=open;shipped_at=`, substituting `''`, `'pending'`, or `'opened'` for the status each produces `SyntaxError` naming line 1.
Source: request

### C-36: `parseOrders` rejects a nonempty `shipped_at` value outside the `YYYY-MM-DD` format with `SyntaxError`.
Observable: In `id=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01`, replacing the date with `'26-10-01'`, `'20260-10-01'`, `'2026-1-01'`, `'2026-10-1'`, `'2026/10/01'`, `'2026-10-01T00:00:00Z'`, or `'２０２６-１０-０１'` each produces `SyntaxError` naming line 1. The format uses four ASCII digits, two ASCII digits, then two ASCII digits, separated by hyphens.
Source: request

### C-37: `parseOrders` accepts shipped dates based on their text format alone.
Observable: `parseOrders('id=2;qty=1;price=99;status=shipped;shipped_at=2026-02-30')` returns `[{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-02-30'}]`.
Source: choice: The request specifies a date format and returns the value as text. It leaves calendar validation unspecified.

### C-38: `parseOrders` throws `SyntaxError` when a shipped order has an empty `shipped_at` value.
Observable: `parseOrders('id=2;qty=1;price=99;status=Shipped;shipped_at= \t ')` throws `SyntaxError` naming line 1.
Source: request

### C-39: `parseOrders` throws `SyntaxError` when an open order has a nonempty `shipped_at` value.
Observable: `parseOrders('id=1;qty=2;price=150;status=Open;shipped_at=2026-10-01')` throws `SyntaxError` naming line 1.
Source: request

### C-40: Each order-line validation error names the 1-based physical line in its message.
Observable: Each string formed by prefixing `id=1;qty=2;price=150;status=open;shipped_at=\r\n \t\r\n` to an invalid order line throws with a message naming line 3, for both `id=2;qty=0;price=99;status=open;shipped_at=` and `id=2;qty=1;price=99;status=pending;shipped_at=`. An invalid order on the first physical line names line 1.
Source: request

### C-41: `parseOrders` reports the first invalid physical line when several lines are invalid.
Observable: `parseOrders('\nid=1;qty=0;price=150;status=open;shipped_at=\nid=2;qty=1;price=99;status=pending;shipped_at=')` throws `RangeError` naming line 2.
Source: choice: Reporting the first invalid line follows the order in which records are read.

### C-42: `parseOrders` gives field-structure errors precedence over numeric range errors on the same line.
Observable: `parseOrders('id=1;qty=0;price=150;status=open;shipped_at=;broken')` throws `SyntaxError` naming line 1.
Source: choice: A line must supply its fields before the values can be validated.

### C-43: `parseOrders` gives quantity or price range errors precedence over other value errors on a structurally valid line.
Observable: `parseOrders('id=1;qty=0;price=150;status=pending;shipped_at=')` throws `RangeError` naming line 1.
Source: choice: Checking the numeric bounds before the remaining values gives a deterministic error class for a line with both kinds of value errors.

### C-44: `parseOrders` leaves the shared meter count unchanged.
Observable: After resetting the meter and ticking it once, parsing `id=1;qty=2;price=150;status=open;shipped_at=` leaves `meter.count()` at `1`.
Source: choice: The request assigns meter ticks to `total`.

### C-45: `total` returns the sum of each order's `qty * price` in cents.
Observable: With a reset meter, `total([{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}])` returns the number `399`.
Source: request

### C-46: `total` returns `0` for an empty order array.
Observable: `total([]) === 0`.
Source: request

### C-47: `total` calls `tick()` from `src/meter.js` exactly once per order.
Observable: A spy on `src/meter.js`'s `tick` export installed before loading `src/orders.js` records exactly `3` calls when `total` receives `[{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:0,status:'open',shippedAt:''},{id:2,qty:1,price:0,status:'open',shippedAt:''}]`.
Source: request

### C-48: `total` performs zero meter ticks for an empty order array.
Observable: After the meter is reset and ticked once, `total([])` leaves `meter.count()` at `1`.
Source: request

### C-49: `total` accumulates ticks from the meter's current count.
Observable: After the meter is reset and ticked twice, two successive calls to `total`, each with `[{id:1,qty:1,price:1,status:'open',shippedAt:''}]`, leave `meter.count()` at `3` after the first call and `4` after the second.
Source: request

### C-50: `total` succeeds when the last order uses the 10,000th tick.
Observable: After a meter reset, `total` on an array of `10000` copies of `{id:1,qty:1,price:1,status:'open',shippedAt:''}` returns `10000`, with `meter.count()` at `10000`.
Source: request

### C-51: `total` propagates the meter's `LimitError` when the next order exceeds the 10,000-tick limit.
Observable: After `10000` ticks since reset, `total([{id:1,qty:1,price:1,status:'open',shippedAt:''}])` throws `meter.LimitError` with message `meter: more than 10000 ticks`.
Source: request

### C-52: `total` preserves the input orders.
Observable: With a reset meter, calling `total` on a frozen array containing the frozen order `{id:1,qty:2,price:150,status:'open',shippedAt:''}` returns `300`.
Source: choice: Summing the order values requires only reading the input array and its objects.

### C-53: The project has `node:test` coverage for `parseOrders`.
Observable: `npm test` discovers a `node:test` case that passes `id=1;qty=2;price=150;status=Open;shipped_at=\n\nid=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01` to `parseOrders` and asserts `[{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}]`.
Source: request

### C-54: The project has `node:test` coverage for `total`'s sum.
Observable: `npm test` discovers a `node:test` case that calls `total` with `[{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}]` and asserts the result `399`.
Source: request

### C-55: The project has `node:test` coverage for `total`'s one-tick-per-order budget.
Observable: `npm test` discovers a `node:test` case that calls `total` with `[{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}]` and asserts exactly `2` ticks for the call.
Source: request

### C-56: `npm test` passes after the orders module is added.
Observable: Running `npm test` from the project root exits with status `0` and reports `0` failed tests.
Source: request

### C-57: `npm test` uses Node's built-in test runner.
Observable: `require('./package.json').scripts.test === 'node --test'`.
Source: existing: package.json

### C-58: The existing meter tests continue to pass.
Observable: `node --test test/meter.test.js` reports `2` passing tests and `0` failures.
Source: existing: test/meter.test.js

### C-59: The meter exposes its hard limit as `10000`.
Observable: `require('./src/meter.js').LIMIT === 10000`.
Source: existing: src/meter.js

### C-60: The meter exposes `LimitError` as a subclass of `Error`.
Observable: `new (require('./src/meter.js').LimitError)() instanceof Error` is `true`.
Source: existing: src/meter.js

### C-61: The meter starts at zero ticks in a fresh Node process.
Observable: The first `require('./src/meter.js').count()` in a fresh process returns `0`.
Source: existing: src/meter.js

### C-62: A successful call to `meter.tick()` increments the meter by exactly one tick.
Observable: After `meter.reset()`, `meter.count()` returns `1` after the first `meter.tick()` and `2` after the second.
Source: existing: src/meter.js

### C-63: Reading `meter.count()` leaves the tick count unchanged.
Observable: After `meter.reset()` followed by one call to `meter.tick()`, two consecutive calls to `meter.count()` both return `1`.
Source: existing: src/meter.js

### C-64: `meter.reset()` sets the count to zero.
Observable: After two successful ticks, calling `meter.reset()` leaves `meter.count()` at `0`. The count also becomes `0` if reset immediately after a limit error.
Source: existing: src/meter.js

### C-65: The meter allows exactly 10,000 ticks from a reset before a limit error.
Observable: After `meter.reset()`, the first `10000` calls to `meter.tick()` complete normally, leaving `meter.count()` at `10000`.
Source: existing: src/meter.js

### C-66: The meter throws `LimitError` on every tick past 10,000 since reset.
Observable: After `meter.reset()` and `10000` successful calls to `meter.tick()`, the 10,001st call throws `meter.LimitError`. If execution continues without a reset, the 10,002nd call also throws `meter.LimitError`.
Source: existing: README.md

### C-67: The meter reports the existing limit error message.
Observable: The error from the 10,001st tick since reset has `message === 'meter: more than 10000 ticks'`.
Source: existing: src/meter.js

### C-68: The meter counts a tick even when that tick throws `LimitError`.
Observable: After catching the error from the 10,001st tick since reset, `meter.count() === 10001`.
Source: existing: src/meter.js

### C-69: `parseOrders` reports the quantity error when both quantity and price are invalid on a structurally valid line.
Observable: `parseOrders('price=-1;id=1;qty=0;status=open;shipped_at=')` throws `RangeError` whose message identifies `qty` on line 1, even though `price` appears first.
Source: discovery: The build report and a direct parser probe with both range errors confirmed which field the diagnostic identifies.

### C-70: `parseOrders` reports the ID error before status or shipping-date errors on a structurally valid line with valid quantity and price.
Observable: `parseOrders('status=pending;price=0;shipped_at=invalid;id=abc;qty=1')` throws `SyntaxError` whose message identifies `id` on line 1. Replacing `pending` with `shipped` leaves the ID diagnostic in place when the date is invalid.
Source: discovery: The build report and direct parser probes with competing value errors confirmed which field the diagnostic identifies.

### C-71: `parseOrders` applies the quantity and price bounds to the rounded values produced by `Number` conversion.
Observable: `parseOrders('id=1;qty=0.99999999999999999;price=1e-324;status=open;shipped_at=')` returns an order with `qty === 1` and `price === 0`. Using `qty=0.9999999999999999` instead throws `RangeError` naming line 1.
Source: discovery: The test report and direct parser probes showed that input can round or underflow to an accepted boundary before validation.

### C-72: `total` uses JavaScript `Number` arithmetic for each order amount and the running sum, including rounding and overflow.
Observable: With a fresh meter, totaling a parsed order with `qty=3` and `price=3002399751580331` returns `9007199254740992`. A parsed order with `qty=1e200` and `price=1e200` totals to `Infinity`, as do two parsed orders each with `qty=1` and `price=1e308`.
Source: discovery: The build and test reports showed product overflow, the README describes `Number` precision, and direct totals reproduced rounding and overflow in both multiplication and addition.

### C-73: An over-budget `total` call stops at the first failed tick and leaves the shared count including the successful ticks and the failed tick.
Observable: Starting at 9,999 ticks, calling `total` on three one-cent orders throws `meter.LimitError` and leaves `meter.count()` at `10001`. After `meter.reset()`, the same call returns `3` and leaves the count at `3`.
Source: discovery: The build and test reports and a direct retry probe showed the retained count and the effect of a reset after a batch fails partway through.

### C-74: After validating the numeric fields, `parseOrders` checks status, then the shipping date format, then whether the status and date agree.
Observable: With `id=1;qty=1;price=0;status=pending;shipped_at=bad`, `parseOrders` throws `SyntaxError` identifying `status` on line 1. Changing the status to `open` produces `SyntaxError` identifying the date format on line 1. With `status=open` and `shipped_at=2026-10-01`, it throws `SyntaxError` saying `shipped_at` must be empty on line 1.
Source: discovery: The second build and test reports and the README describe this validation order. Direct parser probes reproduced the diagnostics for competing status and date errors.

### C-75: `parseOrders` preserves negative zero in `id` and `price` when `Number` conversion yields negative zero.
Observable: Parsing `id=-2e-324;qty=1;price=-2e-324;status=open;shipped_at=` returns an order for which both `Object.is(order.id, -0)` and `Object.is(order.price, -0)` are `true`. Both checks also hold when the input spells each value as `-0`.
Source: discovery: The second test report showed that negative underflow preserves the sign of zero. Direct parser probes confirmed this for underflow and explicit negative zero.

### C-76: `total` adds order amounts to the running sum in input array order.
Observable: With `qty: 1` on every order and a meter reset before each call, an array with prices `[9007199254740992, 1, 1]` totals to `9007199254740992`, and an array with prices `[1, 1, 9007199254740992]` totals to `9007199254740994`.
Source: discovery: The second test report and direct totals showed that reordering the same amounts can change the result through rounding.

### C-77: Within the meter budget, `total` returns positive zero for a nonempty array whose order amounts are all negative zero.
Observable: Let `order` be the first result of `parseOrders('id=1;qty=1;price=-0;status=open;shipped_at=')`. With the meter reset before each call, `Object.is(total([order]), 0)` and `Object.is(total([order, order]), 0)` are both `true`.
Source: discovery: The third build and test reports identified the sign of the sum. Direct public API probes confirmed it for single and multiple orders, including a price that underflowed to negative zero.
