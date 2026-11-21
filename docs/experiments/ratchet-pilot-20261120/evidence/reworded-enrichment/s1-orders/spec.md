## Use cases

### U-1: A caller turns order text into order objects, to work with typed orders
Flow: The caller passes a string with one order per non-blank line, e.g. `id=1;qty=2;price=150;status=Open;shipped_at=` then a blank line then `id=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01`. They get back `[{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}]`.
Source: request

### U-2: A caller gets told which line of the text is wrong, to fix the input
Flow: The caller passes text with a bad order line. The call throws; the error's class says the kind of fault (RangeError for a bad qty or price, SyntaxError for a malformed field, bad status, bad shipped_at or status/date mismatch, TypeError for a non-string argument) and its message names the 1-based line.
Source: request

### U-3: A caller totals orders within the platform's work meter budget, to get the amount in cents
Flow: The caller passes the parsed orders to `total`. They get the sum of qty * price in cents (399 for the example). The shared work meter in `src/meter.js` is ticked once per order, so the call uses n ticks for n orders, far below the meter's 10,000-tick hard limit.
Source: request

### U-4: A maintainer runs the tests, to know the module works
Flow: The maintainer runs `npm test` and sees the existing meter tests and the new orders tests all pass.
Source: request

## Clauses

### C-1: `src/orders.js` exports `parseOrders` and `total`
Observable: `require('./src/orders')` (from the project root) returns an object whose `parseOrders` and `total` are functions.
Source: request; the CommonJS form follows existing: src/meter.js and package.json (no `"type": "module"`).

### C-2: `parseOrders` returns one order per non-blank line, in line order
Observable: For the two-order example text (with a blank line between the orders), the result deep-equals `[{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}]`. A blank line yields no order.
Source: request
Open: Whether a whitespace-only line counts as blank, and how `\r\n` line endings are treated, are not stated; the requester settles it. Only lines that are empty (zero characters) are certainly blank.

### C-3: A line is a list of `key=value` fields joined by `;`, and values are trimmed
Observable: `id= 1 ;qty=2 ;price= 150;status= Shipped ;shipped_at= 2026-10-01 ` parses to id 1, qty 2, price 150, status 'shipped', shippedAt '2026-10-01': the spaces around each value are removed.
Source: request
Open: Whether whitespace around a key (e.g. `id=1; qty=2`) is accepted, and what happens with a repeated key, an unknown key, or a missing key, are not stated; the requester settles it. A line holding each of the five keys once, with no whitespace around keys, is the only form the request defines.

### C-4: Each parsed order has `id`, `qty` and `price` as numbers
Observable: For `id=1;qty=2;price=150;...` the order has `id === 1`, `qty === 2`, `price === 150`, all of type number.
Source: request
Open: What happens for an `id` that is not a number (e.g. `id=abc`) is not stated (no error class is named for it); the requester settles it.

### C-5: `parseOrders` lower-cases the status
Observable: `status=Open` gives `status: 'open'`; `status=SHIPPED` (with a date) gives `status: 'shipped'` and does not throw.
Source: request (status is lower-cased); accepting any-case input as valid follows from lower-casing before the open/shipped check, implied: "status is lower-cased" and "a status other than open or shipped" read together.

### C-6: `shippedAt` is the shipped_at text, `''` when empty
Observable: `shipped_at=2026-10-01` gives `shippedAt: '2026-10-01'`; `shipped_at=` (on an open order) gives `shippedAt: ''`.
Source: request
Open: A line with no `shipped_at` field at all (as opposed to an empty one) is not stated; the requester settles whether it equals an empty value.

### C-7: Text with no orders gives an empty list
Observable: `parseOrders('')` returns `[]`; so does text of only empty lines (e.g. `'\n\n'`).
Source: implied: "one order per non-blank line" — no non-blank lines, no orders.

### C-8: A qty that is not a whole number of at least 1 throws RangeError naming the line
Observable: `qty=0`, `qty=-1`, `qty=1.5` and `qty=abc` each make `parseOrders` throw a `RangeError` whose message contains the line number. `qty=1` is accepted.
Source: request
Open: Whether other spellings of a whole number (`2.0`, `1e2`, `+3`, `0x10`) are accepted is not stated; the requester settles it. Plain digit strings and the values above are the certain cases.

### C-9: A price that is not whole cents of at least 0 throws RangeError naming the line
Observable: `price=-1`, `price=1.5` and `price=abc` each make `parseOrders` throw a `RangeError` whose message contains the line number. `price=0` and `price=150` are accepted.
Source: request
Open: Same as C-8 for other spellings of a whole number (`150.0`, `1e2`); the requester settles it.

### C-10: A field with no `=` throws SyntaxError naming the line
Observable: A line such as `id=1;qty` (or `id=1;qty=2;price=150;status`) makes `parseOrders` throw a `SyntaxError` whose message contains the line number.
Source: request

### C-11: A status other than open or shipped throws SyntaxError naming the line
Observable: `status=pending` (or `status=` empty) makes `parseOrders` throw a `SyntaxError` whose message contains the line number.
Source: request

### C-12: A shipped_at that is not `YYYY-MM-DD` throws SyntaxError naming the line
Observable: On a non-empty `shipped_at` such as `2026-1-5`, `10/01/2026` or `yesterday`, `parseOrders` throws a `SyntaxError` whose message contains the line number. `2026-10-01` is accepted on a shipped order.
Source: request
Open: Whether a well-formed but impossible date (`2026-02-30`, `2026-13-01`) is rejected is not stated; the requester settles it. The shape four digits, `-`, two digits, `-`, two digits is the certain rule.

### C-13: A shipped order without a shipped_at date throws SyntaxError naming the line
Observable: `status=shipped;shipped_at=` throws a `SyntaxError` whose message contains the line number.
Source: request

### C-14: An open order with a shipped_at date throws SyntaxError naming the line
Observable: `status=open;shipped_at=2026-10-01` throws a `SyntaxError` whose message contains the line number.
Source: request

### C-15: The line number in an error message is 1-based
Observable: A faulty first line is reported as line 1; in a text of a single faulty line after no blank lines before it, the message contains `1`. For a faulty second line with no blank lines before it, the message contains `2`.
Source: request
Open: With blank lines in the text, whether "line" counts physical lines (the faulty order in `ok\n\nbad` is line 3) or non-blank lines (line 2) is not stated; the requester settles it. Where no blank line precedes the faulty one the two readings agree. Likewise, which error is thrown when one line has several faults is not stated; only lines with a single fault are certain.

### C-16: A non-string argument to `parseOrders` throws TypeError
Observable: `parseOrders(undefined)`, `parseOrders(null)`, `parseOrders(42)`, `parseOrders({})` and `parseOrders(['id=1'])` each throw a `TypeError`.
Source: request

### C-17: `total` returns the sum of qty * price in cents
Observable: `total` of the example orders returns `399` (2*150 + 1*99). `total([])` returns `0`.
Source: request; the empty case is implied: the sum over no orders.

### C-18: `total` calls `meter.tick()` from `src/meter.js` exactly once per order
Observable: After `meter.reset()`, `total` of n orders leaves `meter.count()` at exactly n (2 for the example, 0 for `[]`), whatever the order's qty, price or status; and a replacement `meter.tick` installed by a test is called n times.
Source: request

### C-19: `total` past the meter's limit lets the meter's LimitError through
Observable: After `meter.reset()`, `total` of 10,000 orders returns normally; `total` of 10,001 orders throws `meter.LimitError` (the meter's own hard limit of 10,000 ticks, counted across all callers since the last `reset`).
Source: implied: the request keeps the meter's hard limit and requires one tick per order, so the meter's own behaviour applies; the limit value is from existing: src/meter.js.
Open: Whether `total` should avoid the error for lists over 10,000 orders is not stated and would conflict with one tick per order; the requester settles it. The meter's count is shared state: ticks from earlier calls in the same process also count toward the limit.

### C-20: The orders module has node:test tests and `npm test` passes
Observable: A test file under `test/` covering `src/orders.js` exists and uses node:test; `npm test` exits 0 with the new tests and the existing meter tests all passing.
Source: request

### C-21: The meter's existing behaviour is unchanged
Observable: `src/meter.js` still exports `LIMIT` (10000), `LimitError`, `tick`, `count`, `reset`, with tick throwing LimitError past 10,000 ticks; the existing `test/meter.test.js` tests still pass.
Source: existing: src/meter.js and test/meter.test.js (preserved where the change touches the meter).
