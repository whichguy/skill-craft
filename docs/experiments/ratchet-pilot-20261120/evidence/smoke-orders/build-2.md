## Done

- C-1 through C-68. Verified the existing implementation and project tests against all 68 frozen acceptance checks.
- C-69. The parser already reports quantity before price, even when the price field appears first. Added a regression test.
- C-70. The parser already reports an invalid ID before invalid status or shipping date. Added a regression test for both combinations.
- C-71. The parser already checks quantity and price after `Number` conversion. Added a test for rounding to `1`, underflow to `0`, and a quantity that still falls below `1` after conversion.
- C-72. `total` already uses `Number` multiplication and addition. Added a test for rounding and overflow in both the order amount and the running sum.
- C-73. `total` already stops on the first failed tick and retains that tick and the successful ticks in the shared count. Added a regression test that also verifies retry after a reset.
- Documented validation order, numeric rounding and overflow, and the count retained after a failed total in `README.md`. `npm test` passes all 18 tests, including the 13 existing cases.

## Not done

none

## Discoveries

- After the ID passes validation, the parser checks status, then the date format, then whether the status and date agree. | Observable: With `id=1;qty=1;price=0;status=pending;shipped_at=bad`, the error identifies `status`. Changing the status to `open` produces `line 1: shipped_at must use YYYY-MM-DD`. | Why: The clauses specify these error conditions individually and leave their precedence open. Both probes confirmed the existing order, which the README now records.
