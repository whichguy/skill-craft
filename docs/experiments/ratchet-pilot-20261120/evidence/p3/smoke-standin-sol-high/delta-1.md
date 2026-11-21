# Ratchet delta 1

Compared the request with C-1 through C-68, the discoveries in `build-1.md` and `tests-1.md`, and the README. Reviewed the orders and meter modules and their existing checks. Ran `npm test` (13 passing) and all 68 existing acceptance checks (68 passing).

Called the public API from Node with the request and README examples, LF and CRLF, blank lines, reordered fields, malformed and repeated fields, non-string input, and status and date errors. Checked error messages on physical lines and with competing invalid values. Exercised quantity and price at and below their minimums, at the safe-integer boundary, at the largest finite `Number`, and beyond the finite range. Also checked numeric spellings that round to a boundary, format-only shipped dates, and both multiplication and sum overflow.

Exercised the shared meter across repeated totals, at 9,999 and 10,000 ticks, and past the limit. Parsed a 10,001-order batch and totaled an empty array with the meter exhausted. Retried the over-budget batch before and after a reset. Ended a Node process with the meter exhausted and verified that a new process started at zero and could total an order.

- C-69 reports the quantity error when both quantity and price are invalid. product keeps to it: yes
- C-70 reports the ID error before status or shipping-date errors when quantity and price are valid. product keeps to it: yes
- C-71 applies the numeric bounds after conversion can round or underflow to a boundary. product keeps to it: yes
- C-72 uses `Number` rounding and overflow for order amounts and the running sum. product keeps to it: yes
- C-73 stops an over-budget batch at the first failed tick and retains the consumed ticks. product keeps to it: yes
