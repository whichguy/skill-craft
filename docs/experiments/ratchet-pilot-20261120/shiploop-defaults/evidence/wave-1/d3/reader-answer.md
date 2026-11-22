# Answer, run d3

## A. The start-up question

Answer: partly.

Row 3 is about this: "How do operators populate deadlines before activation? Decided: Stop the writer, run an explicit backfill, then start with the flag on. Otherwise: Run migration automatically before the new server listens."

- Who or what fills the due times in: the operator, by running "an explicit backfill". That is stated, though "backfill", "the writer" and "the flag" are mechanism words, not manager language.
- What an enabled start does while some tickets have none: the row never says. It does not say that the service refuses to start, or that it starts and serves some tickets without a due time. The reader can only guess it from "then start with the flag on".
- Another answer: named ("Run migration automatically before the new server listens"), and it is workable.

So the row leaves out the consequence for the person who runs the service, and it leans on mechanism words. That is `partly`.

What the specification requires: R-3 says "Starting with DUE_TIMES=on and an existing incomplete file fails before serving", after "stop the file writer and run an explicit command before enabling", and "Backfill assigns due for every missing ticket deadline from the stored created time and priority".

## B. Each row

1. open. The request says only that the help desk "must be able to change those hours without a code change", not how. R-1 states the decision: "operators override a priority through DUE_HOURS_<PRIORITY> using positive whole hours." The other answer, a separate configuration file, is workable.
2. open. The request says "whose due time has passed", which does not settle the exact instant. R-2 states the decision: "strictly past due" and "equality is excluded". This matches the row's "first instant after due". Someone could argue "passed" already means strictly after, but I read it as not settled.
3. open. The request says the data file must hold the due times before the switch-on, but not how they get there. R-3 states the decision: "stop the file writer and run an explicit command before enabling".

## C. Choices the specification made that no row has

- R-3: "Starting with DUE_TIMES=on and an existing incomplete file fails before serving." The alternatives are to start and serve the missing tickets with no due time, or to fill them in automatically. This is the consequence that row 3 left out.
- R-3: "An absent file for first start and the in-memory mode can safely start empty."
- R-3: "Backfill assigns due for every missing ticket deadline ... including closed tickets."
- R-1: "Invalid active configuration fails clearly." The row 1 decision covers only "positive whole hours" and does not say what an invalid setting does.
- R-5: "Preserve the current file before a writable rollback", and a later reactivation "can use that copy to restore missing assigned deadlines by ticket ID".
- R-4: "Human CLI output exposes due when on and the file holds it. Raw CLI columns retain their positions."
- R-4: "Preserve stored due through new-version writes while disabled." Also, "any value other than on" counts as off.
- Non-functional requirements: "A failed backfill must leave the original file intact."

That is 8 listed items. I count 7 distinct choices, because the first two R-1/R-3 failure behaviours and the others differ in kind. I use 7 in the summary line, counting "invalid setting fails" and "any value other than on is off" as the same kind of choice.

## D. In a row but not in the specification

Nothing. All three rows' decisions appear in the specification: R-1 for row 1, R-2 for row 2, R-3 for row 3. The "Otherwise" answers are alternatives, not requirements.

A: partly; rows: 3 (open 3, settled 0, added 0, unstated 0); missed: 7
