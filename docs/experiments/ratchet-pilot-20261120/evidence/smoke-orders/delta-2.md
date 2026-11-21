# Ratchet delta 2

Compared the request and README with C-1 through C-73. Reviewed the orders and meter modules, both build and test reports, and the first delta. The reports list no unfinished work or failing checks, and the workspace contains no fix or referee reports. `npm test` passed all 18 tests, and the four existing acceptance suites passed all 81 tests.

Called the public API from Node with the request and README examples, LF and CRLF input, blank lines, reordered fields, malformed records, and non-string arguments. Checked physical line numbers, competing validation errors, date format and status consistency, and numeric values at and just beyond the quantity and price minimums, the safe-integer boundary, and the finite `Number` range. Probed negative zero, rounding in different array orders, and overflow in multiplication and addition.

Parsed 10,001 records, exercised the shared meter at 9,999, 10,000, and 10,001 ticks, and checked empty totals and parsing at the limit. Retried an over-budget batch after a meter reset. A fresh Node process started at zero and totaled a one-cent order after the prior process exited with the meter over budget.

- C-74 checks status before shipping date format and checks the format before status and date consistency. product keeps to it: yes
- C-75 preserves negative zero in `id` and `price` after conversion. product keeps to it: yes
- C-76 adds order amounts in input array order, which can affect rounding. product keeps to it: yes
