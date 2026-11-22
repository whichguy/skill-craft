# Answer, run d6

## A. The start-up question: partly

Row 3 says who fills the existing tickets in and names another answer: "Startup prepares missing deadlines before opening the port, including startup with the flag off. Otherwise: Use a separate offline migration command, requiring a separate operator invocation."

It never says what a start with DUE_TIMES on does when some ticket has no due time. A reader can only infer that nothing is missing, because startup always fills them. No row states the consequence for the person who runs the service, so this is `partly`, not `yes`.

What the specification requires, in one sentence: R-4 says "startup fills only missing deadlines from each stored creation time and priority and persists them before serving even with the flag off", so an enabled start never serves a ticket without a due time (R-4; also the non-functional line "Migration must finish before listening").

## B. Each row

1. Row 1, R-1, how operators set response hours: `open`. The request says only "must be able to change those hours without a code change" and does not say how. R-1 states "positive whole hours from DUE_HOURS_<PRIORITY> override only that priority", which matches the row's decided answer.
2. Row 2, R-3, overdue at the exact deadline: `open`. The request says "whose due time has passed" and does not settle equality. R-3 states "strict cutoff, independently intersected with existing filters before pagination", which matches "once the deadline has passed. Existing filters still apply."
3. Row 3, R-4, what prepares the data: `open`. The request says existing tickets "get due times too" and does not say what does it. R-4 states startup fills them before serving "even with the flag off", which matches the row.

## C. Spec choices no row mentions

- R-1: what an invalid setting does. "invalid values identify the setting", and "Verify override loading and rejection through configuration tests". Row 1 mentions only "positive whole hours".
- R-1: the due time is stored as "a UTC ISO timestamp".
- R-2: "human CLI output" shows due, while "Raw CLI columns, weekly report, audit and outbox retain their existing contracts". This is a choice about the command-line tool, and no row mentions it.
- R-4: the backfill leaves "audit/outbox" unchanged, and "Restarts never rewrite an existing due value".

## D. In a row, not in the specification

Nothing. Each decided answer is in its clause: R-1 for the DUE_HOURS_* variables, R-3 for the exact-deadline rule with existing filters, and R-4 for startup backfill with the flag off. The "Otherwise" alternatives appear only in the rows, as intended.

A: partly; rows: 3 (open 3, settled 0, added 0, unstated 0); missed: 4
