## Use cases

### U-1: A caller turns a block of order text into order objects, to work with typed orders
Flow: The caller does `require('./src/orders')` and calls `parseOrders` with text of one order per line, for example `'id=1;qty=2;price=150;status=Open;shipped_at=\n\nid=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01'`. They get back `[{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}]`. The blank line between the orders yields no order.
Source: request

### U-2: A caller with empty or blank-only text gets no orders, not an error
Flow: The caller passes `''`, `'\n'` or `'   \n  '` to `parseOrders` and gets `[]`.
Source: implied: "one order per non-blank line" — a text with no non-blank line holds no orders

### U-3: A caller who supplied a bad line learns which line is bad and what kind of fault it is
Flow: The caller passes text where one line breaks a rule (for example `qty=0` on the third line of the text). `parseOrders` throws an error whose message names line 3, and whose class (RangeError or SyntaxError) tells the kind of fault: a number out of range, or a malformed or inconsistent line. No orders are returned.
Source: request ("each naming the 1-based line in its message")

### U-4: A caller passes something that is not text and is told it is the wrong type
Flow: The caller passes `undefined`, `null`, a number, an object or an array to `parseOrders` and gets a TypeError.
Source: request

### U-5: A caller totals a batch of parsed orders, to get the amount in cents
Flow: The caller passes the array from `parseOrders` (the U-1 example) to `total` and gets `399`. An empty array gives `0`.
Source: request

### U-6: The platform operator keeps the shared work meter within its budget
Flow: The meter is shared by the whole process and throws `LimitError` past 10,000 ticks in total. Each `total` call ticks once per order, so a batch of N orders costs N ticks, and the operator can read `meter.count()` before and after to see exactly N. A batch that would take the process past 10,000 ticks stops with the meter's `LimitError`.
Source: request ("its budget is one tick per order, far below the meter's hard limit of 10,000 ticks")

### U-7: A maintainer runs the tests to confirm the module and the existing meter still work
Flow: The maintainer runs `npm test` and sees every test pass, the existing meter tests and the new orders tests alike.
Source: request ("Cover it with node:test tests; npm test must pass")

## Clauses

### C-1: `src/orders.js` can be loaded and exports `parseOrders` and `total` as functions
Observable: From the project root, `require('./src/orders')` succeeds without error under plain `node` (the project is CommonJS: `package.json` has no `"type": "module"`), and `typeof` of its `parseOrders` and `total` properties is `'function'`.
Source: request

### C-2: The request's worked example parses to exactly the stated result
Observable: `parseOrders('id=1;qty=2;price=150;status=Open;shipped_at=\n\nid=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01')` deep-strictly equals `[{id:1,qty:2,price:150,status:'open',shippedAt:''},{id:2,qty:1,price:99,status:'shipped',shippedAt:'2026-10-01'}]`.
Source: request

### C-3: Each non-blank line yields one order, in the order the lines appear
Observable: Text with three non-blank lines returns an array of length 3 whose elements correspond to the lines top to bottom. A line is blank when it is empty or holds only whitespace (as removed by JavaScript `String.prototype.trim`); blank lines yield no element wherever they sit (start, middle, end).
Source: request ("one order per non-blank line")

### C-4: Empty text and blank-only text return an empty array
Observable: `parseOrders('')`, `parseOrders('\n\n')` and `parseOrders('  \t\n   ')` each return `[]`.
Source: implied: U-2, "one order per non-blank line"

### C-5: Lines are separated by `\n`, and a `\r` before it is not part of the line's last value
Observable: `'id=1;qty=1;price=1;status=open;shipped_at=\r\nid=2;qty=1;price=1;status=open;shipped_at='` returns two orders with `shippedAt` `''` each. A trailing newline at the end of the text creates no extra order. A lone `\r` not followed by `\n` is not a line separator.
Source: choice: text from files on Windows ends lines with `\r\n`, and the request says values are trimmed; a lone `\r` is left unspecified so the loosest reading holds

### C-6: A line is split into fields at `;`, and each field into key and value at its first `=`
Observable: `status=open;id=3;qty=1;price=5;shipped_at=` (fields in a different order from the example) returns `{id:3,qty:1,price:5,status:'open',shippedAt:''}`; the fields may come in any order. A value may itself contain `=`: for `shipped_at=a=b` the value is `a=b` (which then fails the date rule in C-21).
Source: request ("fields `key=value` joined by `;`"); implied: key order is not fixed by the request

### C-7: Whitespace around keys and values is removed
Observable: `' id = 4 ; qty = 2 ; price = 10 ; status = OPEN ; shipped_at = '` returns `{id:4,qty:2,price:10,status:'open',shippedAt:''}`.
Source: request ("values are trimmed"); choice: keys are trimmed too, because a reader who writes `id = 4` expects the key to be found

### C-8: A field with a key that is not `id`, `qty`, `price`, `status` or `shipped_at` throws SyntaxError naming the line
Observable: `'id=1;qty=1;price=1;status=open;shipped_at=;note=x'` throws SyntaxError whose message contains the line number `1`. Keys are matched case-sensitively, so `ID=1` is also an unknown key.
Source: choice: the request lists the five keys; silently dropping a mistyped key such as `quantity=2` would hide a fault the caller relies on being told about

### C-9: A key that appears twice in one line throws SyntaxError naming the line
Observable: `'id=1;id=2;qty=1;price=1;status=open;shipped_at='` throws SyntaxError whose message contains `1`.
Source: choice: the request is silent, and picking one of two values silently would give a wrong order without warning

### C-10: `id`, `qty` and `price` in the result are numbers
Observable: For `id=7;qty=3;price=250;...`, `typeof` each of `id`, `qty`, `price` is `'number'` and the values are `7`, `3` and `250`. A value of plain decimal digits with leading zeros, such as `007`, gives `7`.
Source: request

### C-11: `id` must be a whole number of at least 0, else RangeError naming the line
Observable: `id=0` and `id=12` are accepted. `id=-1`, `id=1.5`, `id=abc`, `id=` (empty) and a line with no `id` field each throw RangeError whose message contains the line number.
Source: choice: the request says only that id is a number; a missing or non-numeric id would make the order unidentifiable, and RangeError matches how the request treats the other numeric fields

### C-12: `qty` must be a whole number of at least 1, else RangeError naming the line
Observable: `qty=1` and `qty=250` are accepted. Each of `qty=0`, `qty=-1`, `qty=1.5`, `qty=abc`, `qty=` (empty), `qty=1e2`, `qty=+2` and a line with no `qty` field throws RangeError whose message contains the line number.
Source: request ("qty must be a whole number of at least 1"); choice: the accepted written form is plain decimal digits only, so the forms `1e2`, `+2`, `0x10` and `2.0` are rejected rather than interpreted

### C-13: `price` must be whole cents of at least 0, else RangeError naming the line
Observable: `price=0` and `price=150` are accepted (0 is a valid price). Each of `price=-1`, `price=1.50`, `price=abc`, `price=` (empty), `price=1e2` and a line with no `price` field throws RangeError whose message contains the line number.
Source: request ("price whole cents of at least 0"); choice: the written form is plain decimal digits only, as for qty, so `1.50` (a fraction of a cent-unit) is rejected

### C-14: `id`, `qty` and `price` must not exceed 9007199254740991 (`Number.MAX_SAFE_INTEGER`), else RangeError naming the line
Observable: `qty=9007199254740991` is accepted and returns exactly that number; `qty=9007199254740992` throws RangeError whose message contains the line number. The same holds for `id` and `price`.
Source: choice: beyond that value a JavaScript number no longer holds the written whole number exactly, so a "whole number" would silently become a different one

### C-15: A field with no `=` throws SyntaxError naming the line
Observable: `'id=1;qty=2;price=150;status'` throws SyntaxError whose message contains the line number. An empty field between or after `;` (as in `'id=1;;qty=1;...'` or a line ending with `;`) has no `=` and throws SyntaxError the same way.
Source: request ("a field with no `=` ... throws SyntaxError"); implied: an empty field has no `=`

### C-16: `status` must be `open` or `shipped` after trimming and lower-casing, else SyntaxError naming the line
Observable: `Open`, `OPEN`, `open`, `Shipped` and `SHIPPED` are accepted and returned as `'open'` or `'shipped'`. `pending`, `closed`, `status=` (empty) and a line with no `status` field each throw SyntaxError whose message contains the line number.
Source: request

### C-17: The returned `status` is the lower-cased value
Observable: `status=OPEN` returns `status:'open'`; `status=Shipped` (with a valid shipped_at) returns `status:'shipped'`.
Source: request

### C-18: `shippedAt` is the trimmed `shipped_at` text, and `''` when it is empty or the field is absent
Observable: `shipped_at=2026-10-01` returns `shippedAt:'2026-10-01'`; `shipped_at=` returns `shippedAt:''`; a line with no `shipped_at` field at all returns `shippedAt:''` and does not throw.
Source: request ("'' when empty"); choice: an absent shipped_at is treated as empty, because a shipped_at that is not given is the same fact as one that is empty

### C-19: Each returned order holds exactly the properties `id`, `qty`, `price`, `status` and `shippedAt`
Observable: `Object.keys` of every returned order is exactly those five names (in any order), and the returned array is a new array on each call.
Source: request

### C-20: A non-empty `shipped_at` that is not in the form `YYYY-MM-DD` throws SyntaxError naming the line
Observable: `2026-1-5`, `2026/10/01`, `01-10-2026`, `2026-10-01T00:00:00`, `20261001` and `tomorrow` each throw SyntaxError whose message contains the line number, for an open order and for a shipped order alike. The form is four digits, `-`, two digits, `-`, two digits, with ASCII digits only.
Source: request

### C-21: A `shipped_at` in the right form must also be a real calendar date, else SyntaxError naming the line
Observable: `2026-02-30`, `2026-13-01`, `2026-00-10` and `2026-04-31` throw SyntaxError whose message contains the line number; `2028-02-29` (leap day) and `2026-12-31` are accepted. Years `0001` to `9999` are accepted; year `0000` is rejected.
Source: choice: a date that does not exist cannot be a shipping date; the request says "YYYY-MM-DD" and a builder reading only the request would otherwise not know whether month 13 passes

### C-22: A shipped order must have a `shipped_at` date, else SyntaxError naming the line
Observable: `status=shipped;shipped_at=` and `status=shipped` with no shipped_at field each throw SyntaxError whose message contains the line number.
Source: request ("a shipped order needs a shipped_at date")

### C-23: An open order must not have a `shipped_at`, else SyntaxError naming the line
Observable: `status=open;shipped_at=2026-10-01` throws SyntaxError whose message contains the line number; `status=Open;shipped_at=` is accepted.
Source: request ("an open order must not have one")

### C-24: Every error message names the 1-based line number of the offending line, counting blank lines
Observable: In `'id=1;qty=1;price=1;status=open;shipped_at=\n\nid=2;qty=0;price=1;status=open;shipped_at='` the bad order is on line 3 (the blank line 2 is counted), so the RangeError message contains `3` as a whole number and does not contain `2` or `1` as a stand-alone number. The wording and layout of the rest of the message are not fixed.
Source: request ("each naming the 1-based line in its message"); choice: lines are counted over the text as written, blank lines included, because that is the number an editor shows for the line

### C-25: With several bad lines, the earliest bad line is the one reported, and no partial result is returned
Observable: Text whose line 2 has `qty=0` and whose line 4 has `status=bogus` throws RangeError naming line 2. `parseOrders` never returns an array when any line is bad; it throws.
Source: choice: the request fixes one error per call; the first one in the text is the one the caller meets first. Which error a single line reports when it breaks two rules at once is not fixed.

### C-26: A non-string argument to `parseOrders` throws TypeError
Observable: `parseOrders(undefined)`, `parseOrders(null)`, `parseOrders(42)`, `parseOrders({})`, `parseOrders([])`, `parseOrders(true)` and `parseOrders(new String('id=1'))` each throw TypeError, and `parseOrders()` (no argument) throws TypeError. The empty string is a string and does not throw (C-4).
Source: request; choice: a `String` object is not a string primitive and is refused

### C-27: `total` returns the sum of `qty * price` over the orders, in cents
Observable: `total(parseOrders(<the C-2 example text>))` returns `399` (2*150 + 1*99). `total([{qty:3,price:0}])` returns `0`. `total([{qty:2,price:5},{qty:4,price:25}])` returns `110`. The result is a plain number, not a formatted string.
Source: request

### C-28: `total` of an empty array returns 0 and ticks the meter zero times
Observable: With the meter reset, `total([])` returns `0` and `meter.count()` is still `0`.
Source: implied: U-5, and "exactly once per order" with zero orders

### C-29: `total` calls `meter.tick()` exactly once per order
Observable: With the meter reset, `total` of N orders leaves `meter.count()` equal to N, for N = 1, 2, 5 and 1000 and whatever the orders' values (including `qty*price` of 0). With `meter.tick` replaced by a counting function on the `src/meter.js` module object, that function is called exactly N times, once per order and not at any other time; so `total` must look up `tick` on the meter module at call time rather than keep its own copy from load time.
Source: request ("must call meter.tick() from src/meter.js exactly once per order")

### C-30: `total` stays within the meter's limit for a batch of up to 10,000 orders on a fresh meter
Observable: With the meter reset, `total` of 10,000 orders returns the right sum with no error, and `meter.count()` is `10000`. Cost is one tick per order and no more, so no tick is spent on a setup step, on a second pass or on a per-field basis.
Source: request ("its budget is one tick per order, far below ... 10,000 ticks"); implied: the limit of 10,000 in `src/meter.js` (`LIMIT = 10000`, throws when ticks exceed it)

### C-31: When ticks would pass 10,000, `total` lets the meter's own `LimitError` escape unchanged
Observable: With the meter reset, `total` of 10,001 orders throws an error that is `instanceof` the `LimitError` exported by `src/meter.js`, and its message is the meter's (`meter: more than 10000 ticks`). `total` does not catch it, wrap it, or call `meter.reset()` to avoid it.
Source: request ("past which the meter throws"); implied: the meter's limit is hard and must not be worked around

### C-32: `parseOrders` never ticks the meter
Observable: With the meter reset, `parseOrders` of text with 20,000 valid lines returns 20,000 orders without error and `meter.count()` is still `0`.
Source: choice: the request assigns the tick to `total` only, and the meter's budget is for `total`; spending ticks while parsing would break the one-tick-per-order budget

### C-33: A non-array argument to `total` throws TypeError and ticks the meter zero times
Observable: `total(undefined)`, `total(null)`, `total('text')`, `total(5)` and `total({length:1})` each throw TypeError, and `meter.count()` is unchanged.
Source: choice: the request is silent; the TypeError rule for `parseOrders` (C-26) is the pattern the request sets for wrong-typed arguments

### C-34: `total` does not change the orders it is given
Observable: After `total(orders)`, every order in `orders` still deep-strictly equals its value before the call, and the array has the same length.
Source: implied: a function that returns a sum has no reason to change its input

### C-35: `total` is exact for sums up to 9007199254740991; beyond that the result is not guaranteed
Observable: `total([{qty:1,price:9007199254740991}])` returns `9007199254740991`. A sum above `Number.MAX_SAFE_INTEGER` is a JavaScript number and may be inexact; the exact outcome there is unconfirmed and not required, and `total` does not throw for it.
Source: choice: C-14 lets each field reach the safe-integer maximum, so the sum can pass it; the request names no cap on the total

### C-36: `src/meter.js` behaves as before
Observable: `meter.LIMIT` is `10000`, `tick()` throws `LimitError` on the 10,001st tick since the last `reset()`, `count()` returns the number of ticks, `reset()` sets it to 0, and the existing `test/meter.test.js` tests pass unchanged.
Source: existing: src/meter.js, test/meter.test.js

### C-37: `package.json` still runs `npm test` as `node --test`, with no added dependencies
Observable: `package.json`'s `scripts.test` is `node --test`, and it has no `dependencies` or `devDependencies` entries; the project works with nothing installed from the network.
Source: existing: package.json; implied: the request asks for node:test tests, which the Node.js built-in runner provides

### C-38: There are `node:test` tests for the orders module, and `npm test` exits 0
Observable: Running `npm test` prints passing results for the existing meter tests and for a new test file under `test/` (named `*.test.js` so `node --test` finds it), and exits with status 0. The new tests cover: the C-2 example; blank and empty text; every rule in C-8 to C-25 with its error class and the line number in the message; TypeError for non-string input; `total` returning 399 for the example; the exact tick count per order; the 10,000-order boundary and the `LimitError` at 10,001.
Source: request ("Cover it with node:test tests; npm test must pass")

### C-39: The new tests do not depend on the meter's state left by other tests
Observable: Each test that reads or relies on `meter.count()` or the 10,000 limit calls `meter.reset()` first, and the file leaves the meter reset when it ends, so the orders tests pass when run alone (`node --test test/orders.test.js`), in any order, and together with `test/meter.test.js`.
Source: implied: the meter's tick count is state shared by the whole process, and one test's ticks would otherwise push another test past 10,000
