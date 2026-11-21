## On the starting project

Existing clauses whose commands fail:

- C-7. 1.4.0 ignores the response-hours setting and starts with `DUE_HOURS_URGENT=oops`. The configuration-error convention is existing, but applying it to the new setting is new.
- C-22. 1.4.0 starts without attempting startup preparation, so there is no preparation save to interrupt. The same fault controls reached the replacement boundary and preserved complete old and new states when exercised against ordinary 1.4.0 saves.

Other clauses whose commands pass:

- C-3. 1.4.0 already returns the legacy statuses and JSON, ignores `overdue`, and ignores additive deadline fields while reading.
- C-13. The ordinary listing already includes tickets under its existing filters and cursor rules, independently of additive deadline fields in the input.
- C-23. The starting service preserves the required business fields through startup and reading. The deadline assignment itself is covered by C-17.
- C-28. The starting writer already produces version-one files that the original release can start on.
- C-29. The original release already pages through and directly reads every ordinary record in the starting writer's file. U-6 additionally requires evidence that both kinds of deadline were present in the input to rollback.
- C-33. The original tests execute and pass unchanged.

All 42 item commands ran and printed their own test names. U-5 and U-7 pass because the legacy client and read-only CLI workflows already work. The other use cases fail on the missing due-time behavior or missing added tests. C-34 verifies that the npm test run adds executed, passing `node:test` cases under `test/`. Identifying the behavior those new cases actually assert requires reviewing them when the build arrives.

## Assumed

- The plan's `ada051d8b4eca7b4b67a5b904f50fc7dd5612ff6` object is unavailable locally. The adapter can use `72d982867f943160fbde9456c9f523c5001dd7f3`, this checkout's unmodified 1.4.0 base, for rollback and baseline comparison.
- The literal 8080, 4180 and 65535 cases observe the requested bind port and substitute port zero at Node's bind boundary to keep the tests on free ports. A separate explicit-port test uses the real configured port.
- The clock and fault controls run through Node's standard APIs in the `npm start` child. The interruption control targets the active-file replacement boundary described in the plan.

## Discoveries

- Legacy status queries use the first supplied status when that parameter is repeated. | Observable: `GET /tickets?status=open&status=resolved` lists open tickets, and `status=done&status=open` returns `400 invalid`. | Why: Comparing rollout clients against 1.4.0 exposed a repeat-value rule for the existing status filter.
- Legacy ticket timestamps can include an explicit UTC offset or an expanded ISO year. | Observable: A version-one file with those creation timestamps starts in 1.4.0, and direct reads preserve the stored spelling. | Why: Preparation fixtures need to exercise elapsed-time arithmetic across legacy spellings.
- An empty raw CLI listing emits zero rows, and the weekly JSON report retains every status and priority key with a zero count. | Observable: Run `list --raw` and the weekly report against an empty version-one file. | Why: The dashboard relies on the zero-valued keys even when there are no records to aggregate.
