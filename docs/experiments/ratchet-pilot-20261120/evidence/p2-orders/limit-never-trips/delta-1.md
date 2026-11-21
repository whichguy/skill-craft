# Closing look

Reviewed the request, `ratchet/spec.md`, `ratchet/fix-1.md`, the acceptance manifest and checks, and the README. The checkout had no build, tests, or referee reports or `ratchet/plan.md`. The fix report had no disputes and documented fractional inputs masked by numerical conversion, along with acceptance of other numeric spellings.

Ran `npm test` and the five acceptance suites. All six project tests and all 81 acceptance checks passed. Used the public helpers directly in Node with the request example, repeated totals, LF and CRLF, blank lines, non-string arguments, malformed fields, date and status mismatches, the quantity and price minima, and numeric spellings near validation boundaries. Exercised the shared meter at counts 9,999, 10,000, and 10,001, parsed 10,001 records after exhausting the budget, reset the meter, and started a fresh Node process.

- **C-70** — product keeps to it: yes. The fractional quantity, fractional cents, and fractional price that converts to zero each raised `RangeError` on physical line 3. Integral decimal and scientific spellings still parsed. Radix spellings also parsed in the probe and remain unspecified under C-35.
- **C-71** — product keeps to it: yes. With one tick left, the observed sequence was tick 10,000, the first order's two numeric field reads, then the rejected tick 10,001. After resetting the meter, the same input could be totaled.
- **C-72** — product keeps to it: no. The unmarked CRLF example decoded with `Buffer.toString('utf8')` totals 399 cents. With a leading UTF-8 signature, the parser reports an unknown field on line 1. The clause recognizes the initial code point as an encoding signature so callers can pass Windows-formatted records directly after decoding.
