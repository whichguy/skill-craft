## Use cases

### U-1: A caller parses order text to get order records
Flow: The caller passes `'id=1;qty=2;price=150;status=Open;shipped_at=\n\nid=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01'` to `parseOrders` from `src/orders.js`. They receive `[{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}]`.
Source: request

### U-2: A caller checks why order text was rejected
Flow: The caller parses an otherwise valid open order with `qty=0` on the third input line, following two blank lines, and gets a `RangeError` whose message identifies line 3. With `qty=1` and `status=pending` on that line, they get a `SyntaxError` whose message identifies line 3. Passing `null` instead of text throws `TypeError`.
Source: request

### U-3: A caller totals orders to get their value in cents
Flow: The caller passes the array from U-1 to `total` from `src/orders.js` and gets `399`. The shared meter records two additional ticks. Calling `total` with an empty array returns `0` and adds zero ticks.
Source: request

### U-4: A caller reaches the shared work limit while totaling orders
Flow: With the meter at 9,999 ticks, the caller totals a single order with `qty=1` and `price=99` and gets `99`. The count reaches 10,000. The next call with that order throws the meter's `LimitError`. After calling the existing `meter.reset()`, the caller can total the same order again and gets `99` with the count at 1.
Source: implied: the per-order tick requirement uses the shared meter in src/meter.js

### U-5: A maintainer runs the project tests to verify the order helpers
Flow: The maintainer runs `npm test`. The `node:test` coverage for both order helpers runs with the existing meter tests, and the command succeeds.
Source: request

## Clauses

### C-1: src/orders.js exports a callable parseOrders function
Observable: A Node.js caller loads `src/orders.js` and can call its `parseOrders` export with the text in U-1.
Source: request

### C-2: src/orders.js exports a callable total function
Observable: A Node.js caller loads `src/orders.js` and can call its `total` export with the orders in U-1.
Source: request

### C-3: parseOrders accepts an order line of semicolon-separated key=value fields for id, qty, price, status, and shipped_at
Observable: Passing `'id=1;qty=2;price=150;status=Open;shipped_at='` yields a single order.
Source: request
Open: The requester decides which field permutations are accepted, whether whitespace around keys is accepted, how additional equals signs are interpreted, and how missing, repeated, or unknown keys and empty segments from extra semicolons are handled.

### C-4: parseOrders returns one order per non-blank input line
Observable: The input in U-1 yields two orders. An empty string or text consisting of lines with only spaces or tabs, such as `' \n\t\n'`, yields `[]`.
Source: request
Open: The requester decides which additional line separators are supported beyond the LF breaks in U-1.

### C-5: parseOrders returns orders in input line order
Observable: The array in U-1 has the order from line 1 at index 0 and the order from line 3 at index 1.
Source: implied: the line-to-array mapping shown in U-1

### C-6: parseOrders trims each field value
Observable: Passing `'id= 2 ;qty= 1 ;price= 99 ;status= SHIPPED ;shipped_at= 2026-10-01 '` yields the second object in U-1.
Source: request

### C-7: Each parsed order has the fields id, qty, price, status, and shippedAt
Observable: The first returned object in U-1 is structurally equal to `{id:1,qty:2,price:150,status:'open',shippedAt:''}`.
Source: request

### C-8: A parsed id is a number
Observable: The `id` values in U-1 are the numbers `1` and `2`.
Source: request
Open: The requester decides admissible id values, accepted numeric spellings beyond the examples, and the handling of an empty or nonnumeric id or an id that cannot be represented exactly.

### C-9: A parsed qty is a number
Observable: The `qty` values in U-1 are the numbers `2` and `1`.
Source: request
Open: The requester decides whether forms such as signed, exponent, or nondecimal notation are accepted and how quantity text beyond JavaScript's largest safe integer, 9,007,199,254,740,991, is handled. Above that bound distinct whole quantities can convert to the same number.

### C-10: A parsed price is a number in cents
Observable: The `price` values in U-1 are the numbers `150` and `99`. An otherwise valid order with `price=0` has numeric price `0`.
Source: request
Open: The requester decides whether forms such as signed, exponent, or nondecimal notation are accepted, whether an empty price can stand for zero, and how price text beyond JavaScript's largest safe integer, 9,007,199,254,740,991, is handled. Above that bound distinct whole prices can convert to the same number.

### C-11: A parsed status is lower-cased
Observable: `status=Open` in the first order line of U-1 produces `status:'open'`. Replacing `status=shipped` in the second line with `status=ShIpPeD` produces `status:'shipped'`.
Source: request

### C-12: A parsed shippedAt holds the trimmed shipped_at text
Observable: The first order in U-1 has `shippedAt:''` for the empty field. The second has the string `shippedAt:'2026-10-01'`.
Source: request

### C-13: parseOrders throws RangeError for a qty outside the whole numbers starting at 1
Observable: The second order in U-1 accepts `qty=1`. When the only change to that line is `qty=0`, `qty=-1`, `qty=1.5`, `qty=two`, or `qty=Infinity`, the call throws `RangeError`.
Source: request

### C-14: parseOrders throws RangeError for a price outside the whole cents starting at 0
Observable: The first order line in U-1 accepts `price=0`. When the only change to that line is `price=-1`, `price=0.5`, `price=free`, or `price=Infinity`, the call throws `RangeError`.
Source: request

### C-15: parseOrders throws SyntaxError for a field with no equals sign
Observable: Replacing `qty=2` with `qty` on the first order line of U-1 throws `SyntaxError`.
Source: request

### C-16: parseOrders throws SyntaxError if the normalized status is outside the set open and shipped
Observable: Replacing `status=Open` on the first order line of U-1 with either `status=pending` or `status=` throws `SyntaxError`.
Source: request

### C-17: parseOrders throws SyntaxError for nonempty shipped_at text outside the YYYY-MM-DD format
Observable: Replacing `shipped_at=2026-10-01` on the shipped order line in U-1 with `shipped_at=2026-1-01`, `shipped_at=2026/10/01`, or `shipped_at=2026-10-01T00:00:00Z` throws `SyntaxError`. The format has four year digits, two month digits, and two day digits with hyphens between the groups.
Source: request
Open: The requester decides whether values in this format must also represent real calendar dates, such as whether `2026-02-30` is rejected.

### C-18: parseOrders throws SyntaxError when a shipped order has empty shipped_at text
Observable: Replacing the shipped date in U-1 with `shipped_at=` while keeping `status=shipped` throws `SyntaxError`.
Source: request

### C-19: parseOrders throws SyntaxError when an open order has a shipped_at date
Observable: Replacing the empty shipped_at value in U-1 with `2026-10-01` while keeping `status=Open` throws `SyntaxError`.
Source: request

### C-20: Each required order-line validation error identifies the original 1-based input line in its message
Observable: Each required `RangeError` or `SyntaxError` can be triggered in isolation after two LF line breaks. Its message identifies line 3 even if the preceding lines are blank. On the first input line it identifies line 1. The TypeError for a non-string argument has no order line to identify.
Source: request
Open: The requester decides which failure takes precedence when multiple fields or lines are invalid.

### C-21: parseOrders throws TypeError for a non-string argument
Observable: Passing `null`, `undefined`, `1`, an array, or a boxed string object throws `TypeError`.
Source: request

### C-22: total returns the sum in cents of qty multiplied by price for each order
Observable: Both orders in U-1 contribute to the result regardless of status, so the caller gets `399` from `2 × 150 + 1 × 99`. A single order with `qty=1` and `price=0` contributes `0`. An empty array totals `0`.
Source: request
Open: The requester decides any input contract beyond arrays of valid orders and any precision or overflow policy for products or sums beyond JavaScript's largest safe integer, 9,007,199,254,740,991, where distinct whole-cent totals can have the same numeric representation.

### C-23: total calls tick from src/meter.js exactly once per order
Observable: With the shared meter at 5, calling `total` on the two orders in U-1 raises `meter.count()` to 7. Repeating the call raises it to 9. Calling `total([])` leaves it at 9.
Source: request

### C-24: total is subject to the meter's shared hard limit of 10,000 ticks
Observable: With the count at 9,999, totaling the single 99-cent order in U-4 succeeds and advances the count to 10,000. Totaling that order again attempts tick 10,001 and throws the exported `meter.LimitError`.
Source: existing: src/meter.js

### C-25: The order helpers are covered by node:test tests
Observable: The maintainer can find `node:test` cases that exercise `parseOrders` and `total`.
Source: request

### C-26: npm test passes with the order helpers included
Observable: Running `npm test` runs the order tests together with the existing tests and exits with status 0.
Source: request

### C-27: A caller can total orders again after resetting the meter following its limit error
Observable: After the `LimitError` in U-4, calling `meter.reset()` and totaling the same single order returns `99` with `meter.count()` at `1`.
Source: implied: U-4 includes recovery after the meter limit is exceeded
