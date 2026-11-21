# Closing review

Read the request, the specification, README, and `ratchet/fix-1.md`, including its Discoveries and Disputed sections. The checkout contained no plan, build, test, or referee reports. Reviewed the existing acceptance scenarios and ran all 81 acceptance checks and all 8 tests from `npm test`. All passed.

Called the helpers directly in Node with the request's example, blank lines, CRLF, padded and mixed-case fields, malformed dates, mismatched statuses and dates, and non-string input. Checked minimum quantities and prices, values just below the minimums, and fractions that round to integers or underflow to zero. Used the shared meter at 9,999, 10,000, and 10,001 ticks, parsed 10,001 orders after the meter was exhausted, and checked that resetting the meter and starting a fresh Node process each restored the budget.

- C-70 — Reject written fractions that appear whole after numeric conversion. Each of the three inputs raised `RangeError` on physical line 3. product keeps to it: yes
- C-71 — Require a successful tick before calculating an order's contribution. With one tick left, the quantity and price getters recorded reads only for the first order, and tick 10,001 raised `LimitError`. product keeps to it: yes
