## A. Start-up question: yes (borderline on plain wording)

Row 3: "Run the one-shot backfill with the service stopped, then enable the feature. Enabled startup also fills missing dues before listening. Otherwise: Rely entirely on startup backfill."
- Who or what fills them: the one-shot backfill, or the enabled start itself ("Enabled startup also fills missing dues").
- What an enabled start does while some are missing: it fills them in before the service listens, so it does not refuse or serve without them.
- Another workable answer: "Rely entirely on startup backfill."
- Caveat: "backfill", "dues" and "listening" are mechanism words. I judged them understandable to a help-desk manager, and the consequence is stated, so I did not downgrade to partly.

Specification on this point (R-3): "use a one-shot offline command and catch up missing dues before enabled startup listens."

## B. Rows

1. open. The request says hours must change "without a code change" but not how. R-1 states "use individual positive whole-hour SLA_HOURS_<PRIORITY> environment settings", which matches the row.
2. open. The request says "whose due time has passed", which does not settle equality. R-2 states "a due instant strictly before now", so overdue only after that instant, as the row says.
3. open. The request says only that the file holds due times before activation, not how it gets them. R-3 states "one-shot offline command and catch up missing dues before enabled startup listens", and "The single service process or the offline operator owns the data file at any one time" supports "with the service stopped".
4. open. The request is silent on other query values. R-2 states "only literal overdue=true narrows a list", which matches the row.

## C. Choices in the specification that no row mentions

- R-1: invalid SLA_HOURS values "naming the setting". What an invalid setting does (an error that names the setting) is not in any row. Unset values using the defaults is settled by the request.
- R-1: "elapsed hours" (wall-clock, not business hours) is an interpretation of "hours".
- R-2: due is exposed as an "ISO due" value, on "ticket reads, create, edit, transition and lists". The format and the surfaces are choices.
- R-4: "operator instructions preserve the due-bearing copy and protect later ticket changes during re-upgrade". 1.4.0 "discards the optional due field", so this procedure is a decision about what happens after a rollback, and no row covers it.
- R-3: backfill takes "existing created and priority" and leaves "audit, outbox, ticket IDs, update times or assigned values" untouched. It is mostly implied by the request ("keep them from then on"). Which hours policy applies to existing tickets is not stated, but "restart with a changed policy" suggests the current policy.
- R-2: "Preserve the status/priority OR filter, sort, cursor and envelope" is preservation, not a choice.

## D. In a row but not in the specification

Nothing substantive. Each "Decided" statement traces to R-1, R-2 or R-3. The only gap is that "with the service stopped" is implied by R-3's single-owner sentence and not stated outright. The "Otherwise" answers are alternatives and are not expected in the specification.

A: yes; rows: 4 (open 4, settled 0, added 0, unstated 0); missed: 4
