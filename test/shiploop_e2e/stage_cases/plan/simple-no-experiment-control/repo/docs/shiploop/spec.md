# Specification

## R-1
Fix `formatUsd(cents)` in `src/currency.js` so single-digit cent remainders are zero-padded to two digits (for example `105 -> "$1.05"`, `100 -> "$1.00"`).

## R-2
Keep `formatUsd` input validation for negative or non-integer inputs and keep `node --test` passing with zero external npm dependencies.
