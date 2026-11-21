## Use cases

### U-1: An application developer parses order text to calculate a total in cents
Flow: Load `src/orders.js` with `require` in Node.js. Pass `id=1;qty=2;price=150;status=Open;shipped_at=\n\nid=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01` to `parseOrders`, where `\n` denotes a line feed. Receive `[{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}]`. Pass the result to `total` and receive `399` with two ticks charged to the platform meter.
Source: request

### U-2: An application developer parses formatted text to obtain an ordered set of records
Flow: Submit CRLF-separated records with whitespace-only lines, values padded with spaces, and fields in a different order. `shipped_at= 2026-10-01 ;status= sHiPpEd ;price= 99 ;id= 2 ;qty= 1 ` produces `{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}`. The parser keeps the records in the order in which their lines appear. Parsing the same text again gives the same values.
Source: implied: the per-line format, value trimming, and status normalization in the request

### U-3: An application developer processes an empty batch to get a zero total
Flow: Pass `''` or `' \r\n\t\n'` to `parseOrders` and receive `[]`. Pass `[]` to `total` and receive `0`. The meter count stays at its starting value.
Source: implied: one record per non-blank line and one tick per order

### U-4: An application developer corrects invalid input using the reported error
Flow: Pass a non-string such as `null` and receive `TypeError`. In a string, put a valid order on line 1, a blank line on line 2, and an invalid order on line 3. An invalid quantity or price raises `RangeError`. A malformed field, unsupported status, malformed date, or status/date mismatch raises `SyntaxError`. The line error identifies line `3`, and the parser returns no batch for that call.
Source: request

### U-5: An application developer totals batches repeatedly while sharing the meter budget
Flow: Starting at count `0`, total the two orders from U-1 twice. Each call returns `399`, and the meter counts are `2` and `4` after the respective calls. A direct `meter.tick()` then raises the count to `5`. A caller can reset the meter through its existing API before starting a new budget.
Source: implied: each total call charges the existing meter once per order

### U-6: An application developer reaches the meter limit and sees the platform error
Flow: From a count of `0`, total 10,000 orders with `qty:1` and `price:1` and receive `10000` at count `10000`. An empty batch still returns `0`. The next nonempty batch fails on its first order with `meter.LimitError` and count `10001`. From a reset meter, attempting 10,002 such orders likewise fails at order 10,001 with count `10001`.
Source: existing: src/meter.js

### U-7: A maintainer runs the package from a fresh or restarted Node process
Flow: In a fresh checkout, use Node and npm to run the package tests or load the helpers directly. Existing order text can be passed directly to the parser. A fresh Node process starts with meter count `0`, even when an earlier process reached `10001`. The helpers operate on the supplied values in memory. Returning to the prior checkout leaves the existing meter API and test invocation available.
Source: implied: the new module consumes text and order arrays in the existing Node package with a process-local meter

### U-8: A maintainer runs the test suite to verify the new helpers and the existing meter
Flow: Run `npm test` from the package directory. Node's test runner exercises `parseOrders`, `total`, and the existing meter tests. The command exits with status `0` when all tests pass.
Source: request

## Clauses

### C-1: `src/orders.js` exports `parseOrders`
Observable: `require('./src/orders.js').parseOrders` is callable.
Source: request

### C-2: `src/orders.js` exports `total`
Observable: `require('./src/orders.js').total` is callable.
Source: request

### C-3: `parseOrders` requires a primitive string argument
Observable: Omitting the argument or passing `undefined`, `null`, `42`, `true`, an array, a Buffer, or `new String('')` throws `TypeError`.
Source: request

### C-4: `parseOrders` uses LF as the physical line separator, including in CRLF text
Observable: The same two valid rows separated by `\n` or `\r\n` produce the same two records. Each LF advances the physical line number by one, including the LF in a CRLF pair. The last row can end at the end of the input.
Source: choice: The request gives LF input and ordinary Node text files also use CRLF.

### C-5: `parseOrders` skips lines that are empty after JavaScript string trimming
Observable: `parseOrders('')` and `parseOrders(' \r\n\t\n')` each return `[]`. A blank line between records adds no record.
Source: request

### C-6: `parseOrders` returns an array with one object per non-blank line on success
Observable: The input in U-1 yields an array of length `2`, whose elements are order objects.
Source: request

### C-7: The returned array follows physical input order
Observable: The input in U-1 yields `id:1` before `id:2`. Reversing those lines yields `id:2` before `id:1`.
Source: implied: reading one order per non-blank line in U-1

### C-8: Semicolons delimit the fields of an order line
Observable: `id=1;qty=2;price=150;status=Open;shipped_at=` yields a single record with five fields. A trailing `;` creates an empty field, which is subject to the same `=` requirement as the other fields.
Source: request

### C-9: The first `=` in each field separates its key from its value
Observable: In `qty=2=3`, the value is `2=3`. Using this field in an otherwise valid line raises the quantity `RangeError`.
Source: choice: The first separator gives the full field value to its validator.

### C-10: A field without `=` raises `SyntaxError`
Observable: A line containing a bare `qty` field or a trailing `;` raises `SyntaxError` identifying its physical line.
Source: request

### C-11: Field values are trimmed before validation or conversion
Observable: `id= 2 ;qty= 1 ;price= 99 ;status= sHiPpEd ;shipped_at= 2026-10-01 ` yields `{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}`. A whitespace-only `shipped_at` value becomes `''`.
Source: request

### C-12: Field keys match the five declared names exactly
Observable: A field named `ID`, ` id`, `id `, `shippedAt`, or `extra` raises `SyntaxError` identifying the line. The recognized keys are `id`, `qty`, `price`, `status`, and `shipped_at`.
Source: choice: The request enumerates the keys and specifies trimming for values.

### C-13: Each order line supplies every declared key
Observable: Omitting any one of `id`, `qty`, `price`, `status`, or `shipped_at` from a valid line raises `SyntaxError` identifying the line. An open order supplies `shipped_at=` for its empty date.
Source: implied: the line holds the five named fields in the request

### C-14: Each key occurs at most once per line
Observable: Appending `;id=2` to an otherwise valid row already containing `id=1` raises `SyntaxError` identifying the line.
Source: choice: An order record provides one value for each key.

### C-15: Order IDs may recur across lines
Observable: Two valid rows with `id=1` yield two records, each with numeric `id:1`.
Source: implied: every non-blank line holds one order

### C-16: Field order within a row is arbitrary
Observable: `status=Open;shipped_at=;price=150;qty=2;id=1` yields the same order as the first line in U-1.
Source: choice: Explicit keys identify the values irrespective of their positions.

### C-17: A parsed order exposes exactly the five requested properties
Observable: The object for the first line in U-1 has the properties `id`, `qty`, `price`, `status`, and `shippedAt` with values `1`, `2`, `150`, `'open'`, and `''`, respectively.
Source: request

### C-18: Numeric fields use finite base-10 JavaScript `Number` values
Observable: Numeric spelling permits an optional sign, at least one decimal digit before or after an optional decimal point, and an optional `e` or `E` exponent with a signed or unsigned integer. `01`, `+2.0`, `.5`, and `1e2` convert to `1`, `2`, `0.5`, and `100` for field validation. Empty strings, `0x10`, `NaN`, `Infinity`, and overflow such as `1e309` fail numeric conversion for the field's error rule.
Source: choice: The request requires numbers and leaves their text spelling and conversion unspecified.

### C-19: The parsed `id` is the converted number
Observable: `id=1` yields numeric `1`. `id=-1.5` yields numeric `-1.5` in an otherwise valid row.
Source: request

### C-20: An invalid numeric `id` raises `SyntaxError`
Observable: An otherwise valid row with `id=` or `id=abc` raises `SyntaxError` identifying its line.
Source: choice: An invalid ID is a malformed field value and the request reserves `RangeError` for quantity and price.

### C-21: The parsed `qty` is the converted number
Observable: `qty=2.0` yields numeric `2` in an otherwise valid row.
Source: request

### C-22: A quantity that fails numeric conversion raises `RangeError`
Observable: `qty=`, `qty=many`, and `qty=Infinity` each raise `RangeError` identifying the line in an otherwise valid row.
Source: implied: the quantity must be a whole number

### C-23: A converted quantity that is fractional raises `RangeError`
Observable: `qty=1.5` raises `RangeError` identifying the line. `qty=9007199254740992` satisfies the whole-number check as a JavaScript `Number`.
Source: request

### C-24: A quantity below `1` raises `RangeError`
Observable: `qty=0` and `qty=-1` each raise `RangeError` identifying the line. `qty=1` is accepted in an otherwise valid row.
Source: request

### C-25: The parsed `price` is the converted number of cents
Observable: `price=150` yields numeric `150` in an otherwise valid row.
Source: request

### C-26: A price that fails numeric conversion raises `RangeError`
Observable: `price=`, `price=free`, and `price=Infinity` each raise `RangeError` identifying the line in an otherwise valid row.
Source: implied: the price must be a whole number of cents

### C-27: A converted price that is fractional raises `RangeError`
Observable: `price=0.5` raises `RangeError` identifying the line. `price=9007199254740992` satisfies the whole-number check as a JavaScript `Number`.
Source: request

### C-28: A price below `0` raises `RangeError`
Observable: `price=-1` raises `RangeError` identifying the line. `price=0` is accepted in an otherwise valid row.
Source: request

### C-29: The parsed `status` is lower-cased
Observable: `status=Open` yields `'open'` and `status=sHiPpEd` yields `'shipped'` when the corresponding date value is valid.
Source: request

### C-30: The only valid normalized statuses are `open` and `shipped`
Observable: `status=pending` and `status=` each raise `SyntaxError` identifying the line in an otherwise valid row.
Source: request

### C-31: `shippedAt` is the trimmed text of `shipped_at`
Observable: The first order in U-1 has `shippedAt:''`. The second has `shippedAt:'2026-10-01'` as a string.
Source: request

### C-32: Nonempty `shipped_at` values must have the exact `YYYY-MM-DD` shape
Observable: For a shipped order, `2026-10-01` is accepted. `26-10-01`, `2026-1-01`, `2026/10/01`, and `2026-10-01T00:00:00Z` each raise `SyntaxError` identifying the line. The three parts contain four, two, and two ASCII digits, respectively.
Source: request

### C-33: The date check applies to text shape only
Observable: In an otherwise valid shipped order, `shipped_at=2026-02-30` yields `shippedAt:'2026-02-30'`.
Source: choice: The request specifies `YYYY-MM-DD` formatting for a value returned as text.

### C-34: A shipped order requires a nonempty `shipped_at` value
Observable: `status=shipped;shipped_at=` in an otherwise valid line raises `SyntaxError` identifying the line. The same status with `shipped_at=2026-10-01` is accepted.
Source: request

### C-35: An open order requires an empty `shipped_at` value
Observable: `status=open;shipped_at=2026-10-01` in an otherwise valid line raises `SyntaxError` identifying the line. The same status with `shipped_at=` is accepted.
Source: request

### C-36: Every row validation error identifies the 1-based physical line in its message
Observable: The message for an invalid row after a valid row and a blank row identifies line `3`. The message for an invalid first row identifies line `1`.
Source: request

### C-37: `parseOrders` throws for the first invalid physical line
Observable: Given a valid line 1, blank line 2, `qty=0` on line 3, and `status=pending` on line 4, with the other fields valid, the call throws the `RangeError` for line `3`. The exception ends the call without returning the earlier valid record.
Source: implied: the parser reads orders by line and throws for invalid input

### C-38: Validation within a row uses a fixed precedence
Observable: The parser checks field structure first, then `id`, `qty`, `price`, normalized `status`, date shape, and status/date agreement in that order. A row with both `qty=0` and `status=pending` raises `RangeError` when its structure and `id` are valid. A row with a missing key and `qty=0` raises `SyntaxError`.
Source: choice: A fixed precedence gives a predictable error class when a row has multiple defects.

### C-39: Parsing consumes zero meter ticks
Observable: At meter count `10000`, parsing 10,001 valid lines succeeds with 10,001 records and count `10000`. A parse that raises a row validation error leaves the count at its starting value as well.
Source: implied: the request assigns the per-order meter budget to `total`

### C-40: `total` accepts a dense array of records with numeric operands
Observable: Both the array produced in U-1 and `[{qty:2,price:150},{qty:1,price:99}]` can be passed directly to `total`.
Source: choice: The request defines the sum using only these two properties of each array entry.

### C-41: `total` sums each entry's `qty * price` in cents
Observable: The two entries in U-1 contribute `300` and `99`, so `total` returns the number `399`. Open and shipped entries both contribute.
Source: request

### C-42: `total` accumulates products from left to right using JavaScript `Number` arithmetic
Observable: With sufficient tick budget, `[{qty:9007199254740992,price:1},{qty:1,price:1},{qty:1,price:1}]` totals `9007199254740992`. Moving the large entry to the end yields `9007199254740994`.
Source: choice: The request uses JavaScript numbers and specifies a numerical sum.

### C-43: `total([])` returns numeric `0`
Observable: An empty array returns `0` at meter counts `0`, `10000`, and `10001`.
Source: implied: the sum of an empty collection in U-3

### C-44: `total` calls the existing `src/meter.js` `tick()` exactly once per order entry it processes
Observable: On a reset meter, totaling two entries raises the count to `2`, including when both entries reference the same zero-price order. An empty array charges `0` ticks.
Source: request

### C-45: Meter usage accumulates across calls to `total` within a Node process
Observable: Starting at count `0`, two successive calls with the U-1 array return `399` each. The existing meter's `count()` reports `2` after the first call and `4` after the second.
Source: implied: U-5 uses the shared process-local meter for every call

### C-46: Calling `total` leaves its input intact
Observable: The U-1 array and each contained record can be frozen before calling `total`. The call still returns `399` in the available budget and both entries retain their original values and positions.
Source: implied: U-5 totals the same input again and the request describes a calculation

### C-47: `total` succeeds when its final tick brings the shared count to `10000`
Observable: After `meter.reset()`, 10,000 orders with `qty:1` and `price:1` yield `10000` with meter count `10000`. From count `9999`, one such order yields `1` with count `10000`.
Source: implied: U-6 uses the full existing meter budget at one tick per order

### C-48: `total` propagates the first error thrown by `meter.tick()`
Observable: Starting at count `10000`, totaling one order throws the meter's own `LimitError` instance with message `meter: more than 10000 ticks`. The count becomes `10001`.
Source: implied: the existing meter throws when the hard limit is exceeded

### C-49: `total` stops processing a batch when a tick throws
Observable: Starting at count `0`, totaling 10,002 orders with `qty:1` and `price:1` throws on order 10,001 and leaves the count at `10001`.
Source: implied: U-6 reaches the hard limit during a batch

### C-50: The meter exports a fixed `LIMIT` of `10000`
Observable: `require('./src/meter.js').LIMIT` is the number `10000` in a fresh Node process.
Source: existing: src/meter.js

### C-51: A fresh Node process begins with a meter count of `0`
Observable: After one Node process reaches `10001`, a separate Node process that loads the meter reads `0` from `count()` before its first tick.
Source: existing: src/meter.js

### C-52: Loading the order helpers consumes zero ticks
Observable: In a fresh Node process, requiring `src/orders.js` before reading `meter.count()` leaves it at `0`.
Source: implied: the request meters orders processed by `total`

### C-53: Each call to `meter.tick()` increments the shared count by one
Observable: Two direct ticks after a reset bring the count to `2`. A tick attempted at `10000` also increments the count, to `10001`, before throwing.
Source: existing: src/meter.js

### C-54: `meter.tick()` throws whenever the incremented count exceeds `10000`
Observable: After a reset, ticks 1 through 10,000 return normally. Ticks 10,001 and 10,002 each throw an instance of the exported `meter.LimitError`.
Source: existing: src/meter.js

### C-55: `meter.LimitError` is an `Error` subclass
Observable: An error thrown by `meter.tick()` beyond its hard limit is an instance of both `meter.LimitError` and `Error`.
Source: existing: src/meter.js

### C-56: The meter limit error retains its exact message
Observable: Calling `meter.tick()` at count `10000` throws with the message `meter: more than 10000 ticks`.
Source: existing: src/meter.js

### C-57: `meter.count()` reads the current count without charging a tick
Observable: After two ticks from a reset, consecutive reads of `meter.count()` each return `2`.
Source: existing: src/meter.js

### C-58: `meter.reset()` sets the shared count to `0`
Observable: After a `LimitError` at count `10001`, `meter.reset()` yields count `0` and the next direct tick succeeds at count `1`.
Source: existing: src/meter.js

### C-59: The order helpers work with the package's existing stock Node runtime setup
Observable: From a fresh checkout, the U-1 sequence runs by requiring the two local modules in Node with its default settings. It uses the supplied string and array in memory and requires zero external dependencies or stored order data.
Source: implied: U-7 uses the existing package with a text parser and an array total

### C-60: `npm test` invokes Node's built-in test runner
Observable: Running `npm test` from the package directory invokes `node --test`.
Source: existing: package.json

### C-61: The new parser has `node:test` coverage
Observable: The test run exercises the U-1 parse result, input normalization, parser boundaries, and error classes with physical line labels.
Source: request

### C-62: The new total has `node:test` coverage
Observable: The test run exercises the `399` result in U-1, empty and repeated totals, exact tick counts, and the success and error cases at counts `10000` and `10001`.
Source: request

### C-63: The package test suite passes with the order helpers present
Observable: `npm test` exits with status `0` after running the new order tests and the existing meter tests.
Source: request
