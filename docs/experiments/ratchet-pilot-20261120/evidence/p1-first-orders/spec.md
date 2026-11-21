### C-1: The CommonJS module `src/orders.js` exports `parseOrders(text)` as a function.
Observable: `typeof require('./src/orders.js').parseOrders` is `'function'`.
Source: request

### C-2: The CommonJS module `src/orders.js` exports `total(orders)` as a function.
Observable: `typeof require('./src/orders.js').total` is `'function'`.
Source: request

### C-3: `parseOrders` rejects any argument other than a primitive string with `TypeError`.
Observable: Calling `parseOrders` with no argument or with `null`, `42`, `[]`, or `new String('')` throws `TypeError` in each case.
Source: request

### C-4: `parseOrders` returns an empty array for empty text.
Observable: `parseOrders('')` returns `[]`.
Source: request

### C-5: `parseOrders` skips blank physical lines.
Observable: `parseOrders('\n\n')` returns `[]`.
Source: request

### C-6: `parseOrders` treats whitespace-only physical lines as blank.
Observable: `parseOrders(' \t\n\t ')` returns `[]`.
Source: choice: The request does not define blank, so blank means empty after JavaScript `trim()`.

### C-7: `parseOrders` returns one order per non-blank line in input order.
Observable: `parseOrders('id=1;qty=2;price=150;status=Open;shipped_at=\n\nid=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01')` returns `[{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}]`. Changing the second `id` to `1` still returns two objects in the same order, now both with `id:1`.
Source: request

### C-8: `parseOrders` accepts CRLF line endings.
Observable: `parseOrders('id=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01\r\nid=1;qty=1;price=0;status=open;shipped_at=\r\n')` returns `[{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'},{id:1,qty:1,price:0,status:'open',shippedAt:''}]`.
Source: choice: Accept the common Windows line ending as well as the LF shown in the request.

### C-9: `parseOrders` splits each non-blank line into fields at semicolons.
Observable: `parseOrders('id=1;qty=2;price=3;status=open;shipped_at=')` returns `[{id:1,qty:2,price:3,status:'open',shippedAt:''}]`.
Source: request

### C-10: `parseOrders` trims whitespace from both ends of every field value.
Observable: `parseOrders('id= 1\t;qty=\t2 ;price= 3 ;status= Open\t;shipped_at= \t')` returns `[{id:1,qty:2,price:3,status:'open',shippedAt:''}]`. `parseOrders('id=1;qty=2;price=3;status=shipped;shipped_at=\t2026-10-01 ')` returns `[{id:1,qty:2,price:3,status:'shipped',shippedAt:'2026-10-01'}]`.
Source: request

### C-11: `parseOrders` returns an object with exactly the properties `id`, `qty`, `price`, `status`, `shippedAt` for each order.
Observable: `Object.keys(parseOrders('id=1;qty=1;price=0;status=open;shipped_at=')[0]).sort()` returns `['id','price','qty','shippedAt','status']`.
Source: request

### C-12: `parseOrders` accepts the five named fields in any order.
Observable: `parseOrders('shipped_at=;price=3;status=open;id=2;qty=1')` returns `[{id:2,qty:1,price:3,status:'open',shippedAt:''}]`.
Source: choice: Named fields identify themselves, so no positional constraint is needed.

### C-13: `parseOrders` rejects an unknown field key with `SyntaxError`.
Observable: `parseOrders('id=1;qty=1;price=0;status=open;shipped_at=;extra=1')` throws `SyntaxError` with a message beginning `Line 1: `.
Source: choice: Treat the five listed keys as a closed set to expose misspellings.

### C-14: `parseOrders` matches field keys literally.
Observable: Replacing `qty=1` in `'id=1;qty=1;price=0;status=open;shipped_at='` with either `qty =1` or `Qty=1` throws `SyntaxError` with a message beginning `Line 1: `.
Source: choice: The request specifies trimming for values and gives the spelling of the keys.

### C-15: `parseOrders` rejects any repeated field key with `SyntaxError`.
Observable: `parseOrders('id=1;qty=1;price=0;status=open;shipped_at=;qty=1')` throws `SyntaxError` with a message beginning `Line 1: `.
Source: choice: Each output property has one source field, including when repeated values agree.

### C-16: `parseOrders` rejects a line missing any of the five named fields with `SyntaxError`.
Observable: Starting with `'id=1;qty=1;price=0;status=open;shipped_at='`, omitting any one whole field plus its separator throws `SyntaxError` with a message beginning `Line 1: `, including when `shipped_at=` is the omitted field.
Source: choice: The input lists all five keys, and an open order can express its empty date explicitly as `shipped_at=`.

### C-17: `parseOrders` rejects a field without `=` with `SyntaxError`.
Observable: `parseOrders('id=1;qty;price=0;status=open;shipped_at=')` throws `SyntaxError` with a message beginning `Line 1: `.
Source: request

### C-18: `parseOrders` treats an empty semicolon-delimited segment as a field without `=`.
Observable: Both `parseOrders('id=1;;qty=1;price=0;status=open;shipped_at=')` and `parseOrders('id=1;qty=1;price=0;status=open;shipped_at=;')` throw `SyntaxError` with a message beginning `Line 1: `.
Source: choice: Every segment must carry a field, including a segment after a trailing semicolon.

### C-19: `parseOrders` uses the first `=` in a field as the key/value separator.
Observable: `parseOrders('id=1;qty=1=2;price=0;status=open;shipped_at=')` throws `RangeError` with a message beginning `Line 1: ` because the quantity value is `1=2`.
Source: choice: Preserve the full value for validation when a segment contains additional equals signs.

### C-20: `parseOrders` converts non-empty numeric field text with JavaScript `Number`.
Observable: `parseOrders('id=001;qty=2.0;price=1e2;status=open;shipped_at=')` returns `[{id:1,qty:2,price:100,status:'open',shippedAt:''}]`.
Source: choice: The request constrains numeric values without specifying a decimal spelling for them.

### C-21: `parseOrders` accepts any finite numeric `id`.
Observable: `parseOrders('id=-1.5;qty=1;price=0;status=open;shipped_at=')[0].id` is the number `-1.5`.
Source: choice: The request gives `id` a numeric type without the integer or lower-bound restrictions it gives `qty` and `price`.

### C-22: `parseOrders` rejects an empty or non-finite `id` with `SyntaxError`.
Observable: In `'id=1;qty=1;price=0;status=open;shipped_at='`, replacing the `id` value with `''`, `'abc'`, `'NaN'`, or `'Infinity'` throws `SyntaxError` with a message beginning `Line 1: ` in each case.
Source: choice: An absent numeric value or one that does not represent a finite number is a malformed identifier.

### C-23: `parseOrders` accepts `1` as the minimum quantity.
Observable: `parseOrders('id=1;qty=1;price=0;status=open;shipped_at=')[0].qty` is the number `1`.
Source: request

### C-24: `parseOrders` rejects a quantity below `1` with `RangeError`.
Observable: In `'id=1;qty=1;price=0;status=open;shipped_at='`, replacing `qty=1` with `qty=0` or `qty=-1` throws `RangeError` with a message beginning `Line 1: ` in each case.
Source: request

### C-25: `parseOrders` rejects a quantity that is not a whole number with `RangeError`.
Observable: In `'id=1;qty=1;price=0;status=open;shipped_at='`, replacing the `qty` value with `''`, `'1.5'`, `'2x'`, `'NaN'`, or `'Infinity'` throws `RangeError` with a message beginning `Line 1: ` in each case.
Source: request

### C-26: `parseOrders` accepts `0` as the minimum price in cents.
Observable: `parseOrders('id=1;qty=1;price=0;status=open;shipped_at=')[0].price` is the number `0`.
Source: request

### C-27: `parseOrders` rejects a price below `0` with `RangeError`.
Observable: `parseOrders('id=1;qty=1;price=-1;status=open;shipped_at=')` throws `RangeError` with a message beginning `Line 1: `.
Source: request

### C-28: `parseOrders` rejects a price that is not whole cents with `RangeError`.
Observable: In `'id=1;qty=1;price=0;status=open;shipped_at='`, replacing the `price` value with `'0.5'`, `'2x'`, `'NaN'`, or `'Infinity'` throws `RangeError` with a message beginning `Line 1: ` in each case.
Source: request

### C-29: `parseOrders` rejects an empty price with `RangeError`.
Observable: `parseOrders('id=1;qty=1;price= \t;status=open;shipped_at=')` throws `RangeError` with a message beginning `Line 1: `.
Source: choice: An empty price does not supply an amount in cents, even though JavaScript converts `''` to `0`.

### C-30: `parseOrders` imposes no safe-integer ceiling on a whole quantity or price representable as a JavaScript `Number`.
Observable: `parseOrders('id=1;qty=9007199254740992;price=9007199254740992;status=open;shipped_at=')` returns `[{id:1,qty:9007199254740992,price:9007199254740992,status:'open',shippedAt:''}]`.
Source: choice: Apply the stated integer checks to the converted numbers because the request supplies lower bounds only.

### C-31: `parseOrders` lowercases the status value.
Observable: `parseOrders('id=1;qty=1;price=0;status=OPEN;shipped_at=\nid=2;qty=1;price=0;status=ShIpPeD;shipped_at=2026-10-01').map(order => order.status)` returns `['open','shipped']`.
Source: request

### C-32: `parseOrders` rejects any normalized status outside `open` or `shipped` with `SyntaxError`.
Observable: In `'id=1;qty=1;price=0;status=open;shipped_at='`, replacing the `status` value with `''`, `'pending'`, or `'opened'` throws `SyntaxError` with a message beginning `Line 1: ` in each case.
Source: request

### C-33: `parseOrders` returns the trimmed `shipped_at` text as `shippedAt`.
Observable: `parseOrders('id=1;qty=1;price=0;status=shipped;shipped_at= 2026-10-01 ')[0].shippedAt` is the string `'2026-10-01'`.
Source: request

### C-34: `parseOrders` represents an empty `shipped_at` as the empty string.
Observable: `parseOrders('id=1;qty=1;price=0;status=open;shipped_at=')[0].shippedAt` is `''`.
Source: request

### C-35: `parseOrders` rejects a non-empty `shipped_at` outside the exact ASCII shape `YYYY-MM-DD` with `SyntaxError`.
Observable: In `'id=1;qty=1;price=0;status=shipped;shipped_at=2026-10-01'`, replacing the `shipped_at` value with `'26-10-01'`, `'2026-1-01'`, `'2026-10-1'`, `'2026/10/01'`, `'２０２６-10-01'`, or `'2026-10-01T00:00:00Z'` throws `SyntaxError` with a message beginning `Line 1: ` in each case.
Source: request

### C-36: `parseOrders` validates date shape without enforcing calendar validity.
Observable: `parseOrders('id=1;qty=1;price=0;status=shipped;shipped_at=2026-02-30')[0].shippedAt` is `'2026-02-30'`.
Source: choice: The request specifies a text format and leaves calendar validation unspecified.

### C-37: `parseOrders` rejects a `shipped` order with empty `shipped_at` using `SyntaxError`.
Observable: `parseOrders('id=1;qty=1;price=0;status=Shipped;shipped_at= \t')` throws `SyntaxError` with a message beginning `Line 1: `.
Source: request

### C-38: `parseOrders` rejects an `open` order with a non-empty `shipped_at` using `SyntaxError`.
Observable: `parseOrders('id=1;qty=1;price=0;status=Open;shipped_at=2026-10-01')` throws `SyntaxError` with a message beginning `Line 1: `.
Source: request

### C-39: `parseOrders` reports the 1-based physical line number in every line validation error, counting blank lines.
Observable: Starting with `'id=1;qty=1;price=0;status=open;shipped_at='`, substitute one field at a time with `qty=0`, `price=-1`, `qty`, `status=pending`, `shipped_at=2026/10/01`, `status=shipped`, or `shipped_at=2026-10-01`. Prepending `'\nid=2;qty=1;price=0;status=open;shipped_at=\r\n \t\n'` yields an error whose message begins `Line 4: ` in each case.
Source: request

### C-40: `parseOrders` formats each line validation error message with a `Line N: ` prefix.
Observable: `parseOrders('\nid=1;qty=0;price=0;status=open;shipped_at=')` throws with `error.message.startsWith('Line 2: ') === true`.
Source: choice: Use one stable prefix for the line number while leaving the diagnostic text to the implementation.

### C-41: `parseOrders` reports the earliest invalid input line when multiple lines are invalid.
Observable: `parseOrders('id=1;qty=0;price=0;status=open;shipped_at=\nid=2;qty=1;price=0;status=pending;shipped_at=')` throws `RangeError` with a message beginning `Line 1: `.
Source: choice: Process lines in input order so the first error identifies the first line to fix.

### C-42: `parseOrders` reports same-line errors in structural, field-value, then status/date-agreement order.
Observable: `parseOrders('id=1;qty=0;price=0;status=open;shipped_at=;extra=1')` throws `SyntaxError`. `parseOrders('status=pending;id=1;qty=0;price=0;shipped_at=')` throws `RangeError`. `parseOrders('id=1;qty=1;price=-1;status=open;shipped_at=2026-10-01')` throws `RangeError`. Each message begins `Line 1: `. Within field-value validation, precedence is `id`, `qty`, `price`, `status`, `shipped_at`.
Source: choice: Check field structure first, validate individual values in the order listed in the request, then check agreement between valid values.

### C-43: `parseOrders` leaves the work meter count unchanged.
Observable: After `meter.reset(); meter.tick()`, `parseOrders('id=1;qty=1;price=0;status=open;shipped_at=')` leaves `meter.count()` equal to `1`.
Source: choice: The request attaches the meter budget to `total`.

### C-44: `total` returns the sum of `qty * price` in cents for the supplied orders.
Observable: With a freshly reset meter, `total(parseOrders('id=1;qty=2;price=150;status=Open;shipped_at=\n\nid=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01'))` returns the number `399`. Passing the equivalent array `[{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}]` directly also returns `399`.
Source: request

### C-45: `total` returns `0` cents for an empty array.
Observable: `total([])` returns the number `0`.
Source: request

### C-46: `total` leaves the supplied order data unchanged.
Observable: With a freshly reset meter, passing `[{id:1,qty:2,price:150,status:'open',shippedAt:''}]` to `total` leaves the array deeply equal to `[{id:1,qty:2,price:150,status:'open',shippedAt:''}]`. Freezing the array and its object before the call still yields `300`.
Source: choice: Summation needs only to read the supplied orders.

### C-47: `total` calls the `tick` export from `src/meter.js` exactly once per supplied order in a successful call.
Observable: With `meter.tick` wrapped by a counting spy before loading `src/orders.js`, `total` on 137 copies of `{id:1,qty:1,price:0,status:'open',shippedAt:''}` makes exactly `137` calls to the export with a freshly reset meter. A subsequent `total([])` makes `0` additional calls.
Source: request

### C-48: `total` uses the meter's existing cumulative count.
Observable: After `meter.reset(); meter.tick()`, calling `total([{id:1,qty:1,price:7,status:'open',shippedAt:''}])` twice leaves `meter.count()` at `3`.
Source: existing: src/meter.js

### C-49: `total` can sum 10,000 orders against a freshly reset meter.
Observable: After `meter.reset()`, passing 10,000 copies of `{id:1,qty:1,price:1,status:'open',shippedAt:''}` to `total` returns `10000`.
Source: request

### C-50: `total` propagates the meter's hard-limit exception on the 10,001st cumulative tick.
Observable: After `meter.reset()` followed by 10,000 direct calls to `meter.tick()`, `total([{id:1,qty:1,price:1,status:'open',shippedAt:''}])` throws `meter.LimitError` with message exactly `'meter: more than 10000 ticks'`.
Source: existing: src/meter.js

### C-51: `total` stops ticking at the first tick that throws.
Observable: After `meter.reset()`, passing 10,002 copies of `{id:1,qty:1,price:1,status:'open',shippedAt:''}` to `total` throws `meter.LimitError` with `meter.count()` equal to `10001` immediately afterward.
Source: choice: An exhausted meter ends the summation at the failing tick.

### C-52: `src/meter.js` exposes its hard limit as `LIMIT`.
Observable: `require('./src/meter.js').LIMIT` equals the number `10000`.
Source: existing: src/meter.js

### C-53: The meter starts with zero ticks in a fresh process.
Observable: Before any call to `tick()` or `reset()`, `require('./src/meter.js').count()` returns `0`.
Source: existing: src/meter.js

### C-54: Each successful `meter.tick()` increments the count by one.
Observable: After `meter.reset(); meter.tick(); meter.tick()`, `meter.count()` returns `2`.
Source: existing: test/meter.test.js

### C-55: `meter.reset()` clears the cumulative tick count.
Observable: After `meter.reset(); meter.tick(); meter.tick(); meter.reset()`, `meter.count()` returns `0`.
Source: existing: test/meter.test.js

### C-56: `meter.tick()` succeeds at exactly 10,000 ticks since reset.
Observable: After `meter.reset()`, 10,000 successive calls to `meter.tick()` complete with `meter.count()` equal to `10000`.
Source: existing: README.md

### C-57: `meter.tick()` throws `meter.LimitError` for every tick past 10,000 since reset.
Observable: After `meter.reset()` followed by 10,000 successful calls to `meter.tick()`, calls 10,001 and 10,002 each throw `meter.LimitError` with message exactly `'meter: more than 10000 ticks'`.
Source: existing: src/meter.js

### C-58: A `meter.tick()` that throws still increments the count.
Observable: After `meter.reset()` followed by 10,000 successful calls to `meter.tick()`, catching the exception from one more call leaves `meter.count()` equal to `10001`.
Source: existing: src/meter.js

### C-59: `meter.LimitError` remains an `Error` subclass.
Observable: `new (require('./src/meter.js').LimitError)('probe') instanceof Error` is `true`.
Source: existing: src/meter.js

### C-60: `npm test` continues to run the Node.js built-in test runner.
Observable: The `scripts.test` value in `package.json` is `'node --test'`.
Source: existing: package.json

### C-61: The existing meter tests remain part of the suite.
Observable: `npm test` still runs `meter counts ticks and resets` and `meter throws past its limit` from `test/meter.test.js`.
Source: existing: test/meter.test.js

### C-62: The new orders module has automated coverage using `node:test`.
Observable: The new `node:test` cases discovered by `npm test` cover the parser's accepted orders and input errors, the `399`-cent total, and the meter budget and hard-limit boundary for `total`.
Source: request

### C-63: `npm test` passes with the orders module present.
Observable: Running `npm test` from the project root exits with status `0`.
Source: request
