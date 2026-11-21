## Use cases

### U-1: A caller turns order text into order objects, to work with typed orders
Flow: The caller passes `parseOrders` the text `id=1;qty=2;price=150;status=Open;shipped_at=\n\nid=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01` and gets `[{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}]`. The blank line yields no order.
Source: request

### U-2: A caller hands in bad order text, to learn which line is wrong and why
Flow: The caller passes text where one line breaks a rule. `parseOrders` throws a RangeError, SyntaxError or TypeError whose message names the 1-based line (TypeError: no line, the argument is not text).
Source: request

### U-3: A caller totals parsed orders, to get the sum in cents within the platform meter's budget
Flow: The caller passes the two example orders to `total` and gets `399`. The meter is ticked once per order, so 2 ticks here.
Source: request

### U-4: A maintainer runs the tests, to confirm the module works
Flow: The maintainer runs `npm test` and sees all node:test tests pass, the new ones and the existing meter tests.
Source: request

## Clauses

### C-1: `src/orders.js` is a CommonJS module exporting the functions `parseOrders` and `total`
Observable: `require('./src/orders')` returns an object whose `parseOrders` and `total` are functions.
Source: implied: the request names the module and its exports; `src/meter.js` and the existing tests use CommonJS (`require`/`module.exports`), and package.json has no `"type":"module"`.

### C-2: `parseOrders` returns one order per non-blank line, in line order
Observable: For the example text it returns an array of exactly 2 orders, id 1 then id 2. Text of only blank lines or `''` returns `[]`.
Source: request
Open: Whether a line of only whitespace counts as blank (assumed yes, since values are trimmed). Who settles: the requester.

### C-3: Each line is read as fields `key=value` joined by `;`, with values trimmed
Observable: padding around values does not change the result: `id=1;qty= 2 ;price=150;status= Open ;shipped_at= 2026-10-01 ` gives the same fields as the unpadded line.
Source: request
Open: Whether keys are trimmed too, whether a field's value may itself contain `=` (the first `=` splits), whether a trailing `;` or empty field is accepted, and how `\r\n` line endings are treated. Who settles: the requester. Tests should not rely on any of these.

### C-4: Each order has id, qty and price as numbers
Observable: For `id=1;qty=2;price=150;...` the order has `id === 1`, `qty === 2`, `price === 150` (type number, not string).
Source: request

### C-5: status is lower-cased
Observable: `status=Open` gives `status === 'open'`; `status=SHIPPED` gives `'shipped'`.
Source: request

### C-6: shippedAt is the shipped_at text, '' when empty
Observable: `shipped_at=2026-10-01` gives `shippedAt === '2026-10-01'`; `shipped_at=` gives `shippedAt === ''`.
Source: request
Open: Whether an open order whose line omits the `shipped_at` key altogether is valid (with `shippedAt: ''`), and likewise whether other keys may be missing, unknown or repeated, and whether id must be a valid number. Who settles: the requester. Tests should supply all five keys with valid values unless testing a stated rule.

### C-7: A qty that is not a whole number of at least 1 throws a RangeError naming the line
Observable: `qty=0`, `qty=-1` and `qty=1.5` on line 1 each make `parseOrders` throw a RangeError whose message contains `1`; the same failure on line 3 has a message that names `3`.
Source: request
Open: What the line number counts when blank lines precede the bad line (physical line of the text, assumed, versus the n-th order), and how a non-numeric qty such as `abc` or an empty qty is classified. Who settles: the requester. Tests should use texts with no blank lines before the bad line when checking the number.

### C-8: A price that is not a whole number of cents of at least 0 throws a RangeError naming the line
Observable: `price=-1` and `price=1.5` throw a RangeError whose message names the line; `price=0` is accepted and gives `price === 0`.
Source: request
Open: Same line-number and non-numeric questions as C-7.

### C-9: A field without `=` throws a SyntaxError naming the line
Observable: A line like `id=1;qty` throws a SyntaxError whose message names the line.
Source: request

### C-10: A status other than open or shipped throws a SyntaxError naming the line
Observable: `status=pending` throws a SyntaxError whose message names the line. `status=Open` and `status=SHIPPED` are not errors (case is folded, C-5).
Source: request

### C-11: A non-empty shipped_at that is not YYYY-MM-DD throws a SyntaxError naming the line
Observable: `shipped_at=2026-1-1` and `shipped_at=yesterday` throw a SyntaxError whose message names the line; `shipped_at=2026-10-01` is accepted.
Source: request
Open: Whether a well-formed but impossible date such as `2026-02-30` is rejected. Who settles: the requester. Tests should not use impossible dates.

### C-12: A shipped order without a shipped_at date throws a SyntaxError naming the line
Observable: `status=shipped;shipped_at=` throws a SyntaxError whose message names the line.
Source: request

### C-13: An open order with a shipped_at date throws a SyntaxError naming the line
Observable: `status=open;shipped_at=2026-10-01` throws a SyntaxError whose message names the line.
Source: request

### C-14: A non-string argument to parseOrders throws a TypeError
Observable: `parseOrders(undefined)`, `parseOrders(null)`, `parseOrders(42)` and `parseOrders([])` each throw a TypeError.
Source: request

### C-15: When a line breaks more than one rule, some rule's error is thrown
Observable: A line with `qty=0` and `status=pending` throws either a RangeError or a SyntaxError naming the line; no order is returned.
Source: choice: the request does not rank the rules, and a caller relies only on the failure and the line.
Open: Which error wins when several rules fail on one line or on several lines (first line first is assumed). Who settles: the requester.

### C-16: `total` returns the sum of qty * price over the orders, in cents
Observable: `total` of the example's two parsed orders is `399`; `total([])` is `0`.
Source: request

### C-17: `total` calls `meter.tick()` from `src/meter.js` exactly once per order
Observable: With `meter.reset()` first, `total` of the 2 example orders leaves `meter.count() === 2`; of `[]` leaves `0`; of 5 orders leaves `5`. It ticks on the same meter instance `require('./src/meter')` exports, not a copy.
Source: request

### C-18: `total` stays within the meter's limit for any number of orders up to the limit
Observable: After `meter.reset()`, `total` of 10,000 orders returns their sum with `meter.count() === 10000` and no error. Because the budget is one tick per order, 10,001 orders reach the meter's hard limit: `total` throws the meter's `LimitError` (`meter.LIMIT` is 10,000).
Source: request: the budget of one tick per order, far below the hard limit of 10,000 ticks, past which the meter throws.

### C-19: The new behaviour is covered by node:test tests and `npm test` passes
Observable: `npm test` exits 0 and runs tests for `parseOrders` (the example, each rule above) and `total` (399, tick counts); the existing meter tests still pass.
Source: request
