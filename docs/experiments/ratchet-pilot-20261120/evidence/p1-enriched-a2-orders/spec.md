## Use cases

### U-1: A caller parses the example orders to get records for totaling
Flow: Call `parseOrders('id=1;qty=2;price=150;status=Open;shipped_at=\n\nid=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01')`. The result is `[{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}]`. With a fresh meter, pass those records to `total` to get `399` cents with two ticks.
Source: request

### U-2: A caller parses empty text or formatted lines to get the records present
Flow: Pass `''` or text containing only whitespace-only lines and receive `[]`. Pass a record with padded values and fields in a different order to get the same record as for its unpadded form. Parse two records separated by CRLF to get two records.
Source: implied: one order per non-blank line, with values trimmed and fields identified by key

### U-3: A caller parses successive batches to get the records for each batch
Flow: Parse a batch with two rows carrying the same `id` and get two results in input order. Parse another batch and get only the records from that call. Call `parseOrders('')` afterward and get `[]`.
Source: implied: each call reads one order per non-blank line of its argument

### U-4: A caller supplies the wrong argument type to learn that parsing requires text
Flow: Call `parseOrders(42)` or call `parseOrders()` and receive a `TypeError`.
Source: request

### U-5: A caller submits quantities and prices near their lower bounds to distinguish valid orders from invalid ones
Flow: A record with `qty=1` and `price=0` parses successfully. A record with `qty=0`, `price=-1`, `qty=1.5`, or `price=0.5` substituted into the appropriate field raises `RangeError`. If that record is on physical line 3 after a good record and a blank line, the error identifies line 3.
Source: request

### U-6: A caller submits malformed or inconsistent records to locate the offending line
Flow: Submit separate records containing a field without `=`, `status=pending`, a shipped date of `2026-1-01`, an empty shipped date for a shipped order, or a populated shipped date for an open order. Each call raises `SyntaxError` identifying the line where that record occurs.
Source: request

### U-7: A caller submits an ambiguous field list to discover which input is accepted
Flow: Submit otherwise valid records with an unexpected key, an absent key, a repeated key, or an empty segment. Each record raises `SyntaxError`. An empty or nonnumeric `id` also raises `SyntaxError`. A shipped record whose date has the specified digit pattern is accepted even when the day is outside the calendar month.
Source: implied: the field grammar, numeric identifier, and shipped date rules need outcomes for these inputs

### U-8: A caller totals orders repeatedly to get cents within the shared work budget
Flow: Start with the meter at zero. Total an empty array to get `0` with zero ticks. Total the two example orders twice to get `399` each time. The count is `2` after the first total and `4` after the second.
Source: implied: each call sums its input and spends one shared meter tick per order

### U-9: A caller reaches the meter limit to learn whether a total can finish
Flow: From a fresh meter, total 10,000 orders each with quantity `1` and price `1`. The total is `10000` cents and the meter count is `10000`. A later nonempty total raises the meter's `LimitError` on tick 10,001. Starting at count `9999`, a three-order total uses the last successful tick and stops with `LimitError` on tick 10,001. Resetting the meter through its existing API allows another total to succeed.
Source: request

### U-10: A caller parses a batch larger than the totaling budget to read every record
Flow: Parse 10,001 valid records and receive 10,001 results. The meter count is the same before and after parsing. The meter's limit applies when the caller requests a total.
Source: implied: parsing reads one order per non-blank line and the request assigns the meter budget to totaling

### U-11: An existing meter consumer starts or restarts Node to continue using its current API
Flow: Load `src/meter.js` as before and observe count `0` in a fresh process. Tick twice to observe `2`, then reset to observe `0`. A fresh process starts at `0` again. The consumer can use the same calls after the orders module is added or after returning to the previous revision.
Source: existing: src/meter.js

### U-12: A maintainer starts using the new helpers with the project's existing test command
Flow: Load `src/orders.js` in the existing Node project and supply the order text directly. The caller needs no configuration or data migration. Run `npm test` to run the meter tests and the new orders tests under `node:test` and get a successful exit.
Source: implied: the request adds a Node module and tests to the project described in README.md

## Clauses

### C-1: `src/orders.js` exports `parseOrders`
Observable: `require('./src/orders.js').parseOrders` is callable.
Source: request

### C-2: `src/orders.js` exports `total`
Observable: `require('./src/orders.js').total` is callable.
Source: request

### C-3: `parseOrders` throws `TypeError` for a non-string argument
Observable: Calls with `42`, `null`, an array, a boxed string, or no argument each throw `TypeError`.
Source: request

### C-4: Parsing an empty string returns an empty array
Observable: `parseOrders('')` returns `[]`.
Source: implied: one result per non-blank line

### C-5: Blank lines contribute zero records
Observable: Parsing `'\n \t\n'` returns `[]`. Inserting such blank lines between valid records leaves the number of records unchanged.
Source: request

### C-6: Each non-blank line of valid order text yields one record
Observable: Two copies of `id=1;qty=2;price=150;status=Open;shipped_at=` joined with `\n` yield two records.
Source: request

### C-7: `parseOrders` returns records in input line order
Observable: Two valid lines with IDs `2` and `1` in that sequence return an array with IDs `[2, 1]`.
Source: implied: the two-line example returns records in the same sequence as the input

### C-8: Each parsing call uses its own input text
Observable: After a call with a valid record with ID `1`, a call with a single valid record with ID `2` returns one record whose ID is `2`.
Source: implied: U-3 and `parseOrders(text)` reads its supplied text

### C-9: An order line uses semicolons to separate its `key=value` fields
Observable: `id=1;qty=2;price=150;status=Open;shipped_at=` parses as a record with all five input fields represented.
Source: request

### C-10: The field key determines what a field means
Observable: `status=Open;price=150;shipped_at=;id=1;qty=2` produces the same record as the first line in U-1.
Source: implied: the request identifies fields by key

### C-11: A parsed order has the properties `id`, `qty`, `price`, `status`, and `shippedAt`
Observable: A record from valid text has exactly those five own enumerable properties.
Source: request

### C-12: `parseOrders` trims field values
Observable: `id= 1 ;qty= 2 ;price= 150 ;status= Open ;shipped_at=   ` produces the same record as the first line in U-1. Padding the date value for the shipped order in U-1 as `shipped_at= 2026-10-01 ` leaves its record unchanged.
Source: request

### C-13: A parsed `id` is a number
Observable: In a valid order, `id=1` yields `id` equal to the number `1`.
Source: request

### C-14: A parsed `qty` is a number
Observable: In a valid order, `qty=2` yields `qty` equal to the number `2`.
Source: request

### C-15: A parsed `price` is a number in cents
Observable: In a valid order, `price=150` yields `price` equal to the number `150`.
Source: request

### C-16: The parsed status is lowercase
Observable: Valid orders containing `status=Open` and `status=ShIpPeD` yield `status` values `'open'` and `'shipped'`, respectively.
Source: request

### C-17: A dated order returns the shipped date as text
Observable: A shipped order with `shipped_at=2026-10-01` has `shippedAt` equal to the string `'2026-10-01'`.
Source: request

### C-18: An empty shipped date is represented by the empty string
Observable: An open order with `shipped_at=` has `shippedAt` equal to `''`.
Source: request

### C-19: Quantity has an inclusive minimum of `1`
Observable: With the other fields valid, `qty=1` is accepted and `qty=0` or `qty=-1` throws `RangeError`.
Source: request

### C-20: A quantity that is not a whole number raises `RangeError`
Observable: With the other fields valid, `qty=1.5`, `qty=two`, `qty=Infinity`, and `qty=` each throw `RangeError`.
Source: request

### C-21: Price has an inclusive minimum of `0` cents
Observable: With the other fields valid, `price=0` is accepted and `price=-1` throws `RangeError`.
Source: request

### C-22: A price that is not a whole number raises `RangeError`
Observable: With the other fields valid, `price=0.5`, `price=free`, and `price=Infinity` each throw `RangeError`.
Source: request

### C-23: A field without `=` raises `SyntaxError`
Observable: `id=1;qty=2;price=150;status;shipped_at=` throws `SyntaxError`.
Source: request

### C-24: A status other than `open` or `shipped` after normalization raises `SyntaxError`
Observable: With the other fields valid, `status=pending` and `status=` each throw `SyntaxError`.
Source: request

### C-25: A nonempty shipped date must have the `YYYY-MM-DD` shape
Observable: In otherwise valid shipped orders, `shipped_at=026-10-01`, `shipped_at=2026-1-01`, `shipped_at=2026-10-1`, `shipped_at=2026-aa-01`, `shipped_at=2026/10/01`, and `shipped_at=2026-10-01T00:00:00Z` each throw `SyntaxError`.
Source: request

### C-26: A shipped order requires a populated shipped date
Observable: `id=1;qty=2;price=150;status=shipped;shipped_at=` throws `SyntaxError`.
Source: request

### C-27: An open order requires an empty shipped date
Observable: `id=1;qty=2;price=150;status=open;shipped_at=2026-10-01` throws `SyntaxError`.
Source: request

### C-28: A line-validation error identifies the physical input line by its 1-based number
Observable: For any invalid record reported by the parser, the message identifies line `1` when the record is first. After one valid line and one blank line, the message identifies line `3` for that same record.
Source: request

### C-29: CRLF can separate order lines
Observable: Two valid records joined with `\r\n` yield two records.
Source: choice: accept ordinary Windows text in addition to the LF text shown in the example

### C-30: A field whose key differs from the named key spellings raises `SyntaxError`
Observable: Appending `;note=x` to a valid line throws `SyntaxError`. Replacing its `id=1` with `ID=1` or `id =1` also throws `SyntaxError`.
Source: choice: use the five listed keys literally because the request specifies normalization only for values

### C-31: A line missing any named key raises `SyntaxError`
Observable: Remove one key and its field from the first line in U-1. The shortened line throws `SyntaxError` for each of the five possible removals, including removing `shipped_at=`.
Source: choice: require explicit fields so an absent value and an intentionally empty shipped date remain distinguishable

### C-32: A repeated key within one order line raises `SyntaxError`
Observable: Appending `;qty=3` to the first line in U-1 throws `SyntaxError`.
Source: choice: a line gives each order property one value and provides no priority between conflicting fields

### C-33: An empty semicolon-delimited segment raises `SyntaxError`
Observable: Prepending `;` to the first line in U-1, appending `;` to it, or doubling one of its separator semicolons each throws `SyntaxError`.
Source: choice: treat a delimiter as requiring a field on each side

### C-34: The first `=` in a field separates the key from its value
Observable: With the other fields valid, `qty=2=3` throws `RangeError` because the quantity text is `2=3`.
Source: choice: retain the complete field value for its field-specific validation

### C-35: Decimal numeric text is interpreted by its numeric value
Observable: In an otherwise valid order, `id=-2.5;qty=2.0;price=150.0` yields the numbers `-2.5`, `2`, and `150`, respectively.
Source: choice: ordinary decimal text suffices for the requested fields, with support for other numeric spellings left open

### C-36: An identifier without a finite numeric value raises `SyntaxError`
Observable: With the other fields valid, `id=`, `id=abc`, and `id=Infinity` each throw `SyntaxError`.
Source: choice: treat unusable identifier text as a malformed field since the request provides no identifier error rule

### C-37: An empty price raises `RangeError`
Observable: With the other fields valid, `price=` and `price=   ` each throw `RangeError`.
Source: choice: an empty price supplies no cents value, even though JavaScript can coerce empty text to zero

### C-38: The whole-number rules impose no safe-integer ceiling
Observable: An otherwise valid order with `qty=9007199254740992` and `price=9007199254740992` is accepted.
Source: choice: the stated minimums and JavaScript number representation suffice without a separate maximum for these fields

### C-39: Shipped date validation checks the written shape without calendar validation
Observable: An otherwise valid shipped order with `shipped_at=2026-02-30` is accepted.
Source: choice: the request specifies the date pattern and supplies no calendar rule

### C-40: One applicable validation error suffices when an input has multiple faults
Observable: An otherwise valid line with both `qty=0` and `status=pending` throws either the quantity's `RangeError` or the status's `SyntaxError`.
Source: choice: the request supplies no priority among validation errors

### C-41: Parsing has no 10,000-record cap from the meter
Observable: Parsing 10,001 valid order lines returns 10,001 records.
Source: implied: the hard limit is on meter ticks, and the parser returns one record per non-blank line

### C-42: Parsing leaves the meter count unchanged
Observable: Start with the meter at `1`. After a call to parse a valid order, the count is `1`. After a call that throws on an invalid order, it is still `1`.
Source: choice: the request allocates meter work to totaling, so reading order text consumes none of that shared budget

### C-43: `total` returns the sum of `qty * price` in cents
Observable: Calling `total` with the two order objects in U-1 returns the number `399`.
Source: request

### C-44: The total of zero orders is `0`
Observable: `total([])` returns the number `0`.
Source: implied: the empty sum in the definition of `total`

### C-45: `total` calls the platform's `meter.tick()` once per order it totals
Observable: From a meter count of `0`, totaling one valid order with `qty=2` and `price=0` invokes `meter.tick()` once. From the same baseline, totaling the two orders in U-1 invokes it twice. An observer can instrument `src/meter.js` before loading `src/orders.js`.
Source: request

### C-46: Totaling zero orders makes zero meter calls
Observable: Starting at count `10000` or `10001`, calling `total([])` completes with zero calls to `meter.tick()`.
Source: implied: one tick per order, of which the empty input has zero

### C-47: Totals spend the meter budget cumulatively across calls
Observable: Start at count `0` and total the two example orders twice in the same process. The meter reads `2` after the first call and `4` after the second call.
Source: implied: the request uses the shared meter in src/meter.js, whose count persists across calls

### C-48: A total can consume exactly the remaining meter budget
Observable: With the meter at `0`, total 10,000 orders having quantity `1` and price `1`. The call returns `10000` cents. With the meter already at `9999`, the call for one such order returns `1` cent.
Source: implied: one tick per order and the meter throws only past 10,000 ticks

### C-49: `total` propagates the meter's `LimitError` on the first over-budget tick
Observable: Set the count to `9999` with existing meter calls. Totaling three valid orders throws the `LimitError` from tick 10,001. Starting at count `10000`, even totaling one order throws the meter's `LimitError`.
Source: implied: U-9 and the hard limit on the required meter calls

### C-50: A failed meter call ends the total's meter work
Observable: Start at count `9999` and observe meter calls while totaling three valid orders. There are two attempts, ending with the failed tick at count `10001`.
Source: implied: the meter's hard limit interrupts the total at the first failed tick

### C-51: An explicit meter reset restores the budget available to `total`
Observable: After an over-budget total, call `meter.reset()` and then total one order with quantity `1` and price `1`. The call returns `1` cent.
Source: implied: U-9 and the existing reset behavior in src/meter.js

### C-52: `total` leaves the supplied orders unchanged
Observable: After totaling the two orders in U-1, the original input array has the same two entries in the same order with the same property values.
Source: choice: a calculation on caller-supplied orders can leave those orders reusable

### C-53: The specified `total` input is an array of valid order objects
Observable: An argument outside the shape of `parseOrders` output, such as a non-array, a sparse array, or an entry with an invalid `qty` or `price`, has no prescribed return value or error type.
Source: choice: the request gives argument validation rules only for `parseOrders`

### C-54: Using the order helpers requires no application configuration
Observable: A fresh Node process in the checkout can require `src/orders.js`, parse the U-1 text, and total its result using the existing project setup.
Source: implied: U-12 adds a Node module with text and array inputs to the existing project

### C-55: Order text can be supplied directly by the caller
Observable: A caller can pass an existing string in the requested line format to `parseOrders` and receive records without converting stored data or importing it into the project.
Source: implied: U-12 and `parseOrders(text)` takes the order data as its argument

### C-56: The meter has an initial count of `0` in a fresh Node process
Observable: Require `src/meter.js` in a fresh process and call `count()` before any ticks. The result is `0`, even if an earlier process used the meter.
Source: existing: src/meter.js

### C-57: The meter exports `LIMIT` equal to `10000`
Observable: `require('./src/meter.js').LIMIT` equals the number `10000`.
Source: existing: src/meter.js

### C-58: `meter.tick()` increments the count by one
Observable: After resetting the meter, a first tick leaves `count()` at `1` and a second tick leaves it at `2`.
Source: existing: src/meter.js

### C-59: The meter permits tick 10,000
Observable: Starting at `0`, a sequence of 10,000 calls to `meter.tick()` completes successfully.
Source: existing: README.md

### C-60: The meter rejects ticks past 10,000 with its exported `LimitError`
Observable: Starting at `0`, call `meter.tick()` 10,001 times. Call 10,001 throws an instance of `meter.LimitError`. A further attempt does so again.
Source: existing: src/meter.js

### C-61: The meter's `LimitError` derives from `Error`
Observable: `new meter.LimitError()` is an instance of `Error`.
Source: existing: src/meter.js

### C-62: The meter retains its existing limit error message
Observable: On tick 10,001 the meter error's message is `meter: more than 10000 ticks`.
Source: existing: src/meter.js

### C-63: A tick still counts when the meter rejects it
Observable: After the first over-limit call, `meter.count()` returns `10001`.
Source: existing: src/meter.js

### C-64: Reading the meter count preserves the count
Observable: After two successful ticks from `0`, two successive `meter.count()` calls both return `2`.
Source: existing: src/meter.js

### C-65: `meter.reset()` restores the count to `0`
Observable: From a count of `2` or `10001`, call `reset()`. The next `count()` returns `0`.
Source: existing: src/meter.js

### C-66: `npm test` continues to use Node's built-in test runner
Observable: Running `npm test` uses Node's built-in test runner to discover the project tests.
Source: existing: package.json

### C-67: `node:test` coverage exercises the new order helpers
Observable: The discovered orders tests exercise successful parsing, rejected input, the total in cents, and the per-order meter budget at its boundaries.
Source: request

### C-68: `npm test` succeeds with the orders coverage present
Observable: `npm test` exits with status `0` with both the meter and orders suites included.
Source: request

### C-69: Loading the orders module leaves the meter count unchanged
Observable: In a process that has not loaded `src/orders.js`, bring the meter to count `1`. Requiring `src/orders.js` leaves the count at `1`.
Source: choice: loading the helpers consumes none of the shared budget available for totaling orders
