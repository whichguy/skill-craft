# Ratchet delta 3

Compared the request and README with C-1 through C-76. Reviewed the orders and meter modules, the prior deltas, and all three build and test reports. The reports list no unfinished work or failing checks, and the workspace contains no fix or referee reports. `npm test` passed all 21 tests, and the four acceptance suites passed all 87 tests.

Ran the request and README examples through the public API in Node. Probed LF and CRLF input, blank lines, reordered fields, non-string arguments, malformed records, physical line numbers, and competing validation errors. Checked quantity and price at and below their minimums, around zero underflow, at the safe-integer boundary, and at and past the finite `Number` limit. Also checked format-only shipped dates, rounding in different array orders, and overflow in both order amounts and the running sum.

Parsed 10,001 records and exercised the shared meter at 9,999, 10,000, and 10,001 ticks and beyond. Tried valid and invalid parsing and an empty total with the meter exhausted. Retried an over-budget batch before and after a reset. After a Node process exited with the meter exhausted, a fresh process started at zero and totaled a one-cent order.

Used `Object.is` to check the sign of each order amount and of the total for one- and two-order batches. The amounts were negative zero with both an explicit `-0` price and a negative price that underflowed to zero. Both batch sizes returned positive zero and used one tick per order.

- C-77 specifies positive zero for an in-budget, nonempty total of negative-zero order amounts. product keeps to it: yes
