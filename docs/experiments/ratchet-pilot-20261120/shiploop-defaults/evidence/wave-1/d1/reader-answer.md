# Reader answer, run d1

## A. The start-up question: partly

Row 4 is about this: "The first new startup fills missing values before listening, even with the flag off. Otherwise: A separate offline migration would add an operator command."

- Who fills them in: the service itself, at its first new startup. This is stated.
- Another answer: a separate offline migration (an operator command). This is named.
- What an enabled start does while some tickets are missing a due time: no row says. The row only says the missing values are filled before listening, with the flag on or off. It never tells the person running the service what happens when DUE_TIMES is on and a ticket still has no due time.
- Wording: "fills missing values before listening" and "the flag" assume the reader knows the mechanism. A help-desk manager is not told what the person running the service will see.

So it is `partly`. It names who fills them and another answer, but leaves out the enabled-start consequence and is mechanism-worded.

What the specification requires, in one sentence: on the new release the service itself loads and validates the file, fills each missing due time from the ticket's persisted creation time and priority, and saves atomically before listening. R-3, first bullet: "On the new release, load and validate the v1 file, fill missing deadlines from each persisted creation time and priority, and atomically save before listening." The clause makes no mention of the DUE_TIMES setting and says nothing about an enabled start finding tickets without due times.

## B. Each row

1. open. The request does not say how the hours are changed. R-1 states it: "Set any of DUE_HOURS_URGENT, DUE_HOURS_HIGH, DUE_HOURS_NORMAL and DUE_HOURS_LOW to positive whole hours before start."
2. open. The request says only "whose due time has passed" and does not settle the exact instant. R-2 states it: "overdue=true selects only open and in_progress tickets strictly past due", and tests "an equal time".
3. open. The request does not say how the command-line tool shows `due`. R-2 states it: "Only exact DUE_TIMES=on exposes due on ticket HTTP responses and human CLI output ... Keep the four raw CLI fields stable." The row's words "list and show" are not literally in R-2.
4. open. The request does not say who fills the existing tickets. R-3 states it: "On the new release, load and validate the v1 file, fill missing deadlines ... and atomically save before listening." R-3 does not condition this on the flag, and it says "dark rollout" must be documented. The row's words "even with the flag off" are implied by R-3 but never written in it.

## C. Choices the specification made that no row has

- What an invalid hours setting does (R-1): "named rejection of invalid values".
- Hours must be positive whole numbers, and due times are exact UTC ISO whole-hour offsets (R-1, S2-S4). Row 1 mentions "positive whole hours" but not the rejection.
- Only the exact value `on` switches due times on (R-2): "Only exact DUE_TIMES=on".
- overdue=true is applied before cursor pagination and in addition to existing filters (R-2): "before cursor pagination and in addition to existing filters".
- With the switch off, overdue=true is treated like an unknown parameter (R-2): "the query behaves like an unknown parameter".
- Rollback handling (R-3): "Document single writer, dark rollout and preserving deadline values through rollback writes".
- The file is rewritten at startup only if data changed, and the save is atomic (Scope: "only rewrites on startup if data changed"; R-3).
- The file is validated on load (R-3), with no stated outcome for an invalid file.

Missed, counting the clearest: invalid-hours rejection, the exact `on` match, overdue with filters and pagination, rollback and single-writer handling, rewrite only if changed. That is 5.

## D. In a row, not in the specification

- Row 4, "even with the flag off": not stated literally; only implied by the unconditional R-3 clause and "dark rollout".
- Row 3, "The human list and show": R-2 says "human CLI output" and does not name list and show.
- Nothing else. The "Otherwise" alternatives in each row are not specification content.

A: partly; rows: 4 (open 4, settled 0, added 0, unstated 0); missed: 5
