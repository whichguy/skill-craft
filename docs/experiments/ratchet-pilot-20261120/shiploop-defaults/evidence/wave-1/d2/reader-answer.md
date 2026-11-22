# Answers for run d2

## A. The start-up question: partly

Row 3 is about existing files: "How do existing files get prepared before enabling? Decided: Run one offline migration command, then enable the switch. Otherwise: Start a preparatory release that migrates its file during startup."

- It states who or what fills in the due times: "one offline migration command".
- It names another workable answer: "Start a preparatory release that migrates its file during startup."
- It does not say what the service does when started with DUE_TIMES on while some ticket has no due time. No row says the service refuses to start, starts and shows blanks, or fills them in. The person who runs the service is not told what happens if they enable the switch too early.
- "Migration" and "preparatory release" are mechanism words that a help-desk manager may not follow.

What the specification requires: the operator runs a separate offline migration that backfills the missing due times, and "The enabled service refuses to start on an incomplete existing file." This is clause R-3: "Operator runs a separate, offline migration before enabling a previously used data file (default procedure). Backfill missing due from stored creation time and priority... The enabled service refuses to start on an incomplete existing file."

## B. Each row

1. open. The request says the hours must be changeable "without a code change" but not how. R-1 states "per-priority environment overrides (positive whole hours by default)", which matches the row's "One positive whole-hour variable per priority".
2. open. The request says only "whose due time has passed", which does not settle the exact instant. R-2 states "strictly before the current clock (default interpretation)", which matches "It counts once the clock is later than the deadline."
3. open. The request says the existing tickets "get due times too" and that due times are switched on "only once the data file holds them", but not how the file is prepared. R-3 states "Operator runs a separate, offline migration before enabling a previously used data file (default procedure)", which matches the row.

## C. Specification choices that no row mentions

- Invalid hours fail configuration with the variable named (R-1: "Invalid hours fail configuration with the variable named").
- The format of the stored and shown due time is an ISO UTC timestamp (R-1: "ISO UTC due time").
- The enabled service refuses to start on an incomplete existing file (R-3). This is the start-up behaviour that question A asks about, and no row has it.
- overdue=true intersects the status and priority filters and is applied before pagination (R-2).
- Other values of overdue keep the existing query behaviour (R-2: "Other values retain existing query semantics"), and with the feature off overdue is ignored (R-5).
- The human CLI views show due only when DUE_TIMES is exactly `on`, and the raw CLI columns stay unchanged (R-2).
- The operator may keep the pre-rollback version-1 file and reuse its deadlines during a re-upgrade while keeping ticket updates made under 1.4.0 (R-4).
- Migration preserves IDs, audit and outbox, and the service stays the sole writer (R-3). These are partly implied by the request, so this item is weak.

## D. Anything in a row that is not in the specification

Nothing. Each row's "Decided" text appears in R-1, R-2 or R-3. The "Otherwise" alternatives are not in the specification, which is expected because they are the options not chosen.

A: partly; rows: 3 (open 3, settled 0, added 0, unstated 0); missed: 7
