# Delta 1

## What I used and tried

- Reviewed the request, `ratchet/spec.md`, `ratchet/fix-1.md` (including Discoveries and Disputed), the acceptance manifest, and the README. The checkout contained no plan, build, test-stage, or referee report.
- Ran the documented `npm test` command and the acceptance suite. All 6 project tests and all 81 acceptance checks passed.
- Loaded both modules in Node and ran the request's two-order example. Each total returned 399 cents and spent two ticks. Tried blank lines, LF and CRLF, malformed fields, wrong argument types, quantity and price minimums, date and status combinations, and quantity and price values around the safe-integer boundary.
- Parsed 10,001 records before and after exhausting the meter. Checked totals at 9,999, 10,000, and 10,001 ticks, then verified that a reset restored the budget and a fresh Node process started at zero.
- Reproduced the fix report's numeric conversion cases. Exact whole decimals remained valid. Fractions that converted to a whole number raised `RangeError` on line 3, including a quantity that rounded up to 1 and prices that rounded to 150 or underflowed to zero. Whole exponent and radix spellings also worked. Their support remains open under C-35.

## C-70 — Fractions hidden by numeric conversion

Preserves the whole-number requirement for the values supplied in the input text. Each of the four examples in C-70 raised the expected line-numbered `RangeError`.

product keeps to it: yes
