# Reader answer, run d5

## A. The start-up question

**yes.** Row 3 ("How does rollout populate the file?") reads: "Run npm run backfill:due while the writer is stopped. Enabled startup also fills any missing deadlines before serving." That says who fills the tickets in (a backfill command the operator runs; enabled startup does it too) and what an enabled start does while some have none ("fills any missing deadlines before serving"). It names a different workable answer: "Require a separate backfill and refuse startup when any value is missing."

Slight reservation: "while the writer is stopped" and the npm command name are operator wording, but the consequence is plain enough for a help-desk manager, so I do not drop it to `partly`.

What the specification requires on this point: R-3 says "an offline command supports preparation before opt-in and enabled startup ensures backfill before listening", so existing records get due from their creation time and stored priority, and an enabled start fills any that are missing before it serves.

## B. Each row

1. R-1 hours configuration: `open`. The request says only that the help desk can change the hours "without a code change", not how. R-1 states "operators configure DUE_HOURS_<PRIORITY> in positive whole hours", which is what the row says.
2. R-2 other overdue values and existing filters: `open`. The request defines only `overdue=true`. R-2 states "exact DUE_TIMES=on ... activates exact overdue=true", "ignore other overdue values", and "intersect with existing status/priority OR filter before cursor pagination", which matches "Only exact true activates it" and "intersects ... before paging".
3. R-3 rollout population: `open`. The request says the existing tickets get due times and that due times switch on only once the file holds them, but not who fills them or what an enabled start does. R-3 states "an offline command supports preparation before opt-in and enabled startup ensures backfill before listening". Its text does not mention the command's name or "while the writer is stopped"; see D.
4. R-2 CLI: `open`. The request does not mention the CLI display of due. R-2 states "show due in human CLI output with the flag on. The weekly report's four raw columns remain intact." This matches the row apart from the "list and show" naming (see D). A stricter reader could call it `added`, since the request says only that "every ticket shows its due time" and the HTTP response is the evident subject.

## C. Choices in the specification that no row mentions

- R-1: invalid DUE_HOURS values "name the variable at startup" (an invalid setting stops start-up with an error); unset or blank "uses default".
- R-1: the stored due is "an ISO UTC due value".
- R-1: restarts with changed hours keep the original due. The request settles this, so it is not a choice.
- R-1: positive whole hours only. It is partly in row 1, but the bound itself is not named as a choice.
- R-2: overdue is "now strictly after due", so a ticket due exactly now is not overdue. Reopened tickets are covered by the status test.
- R-2: the flag must be exactly `DUE_TIMES=on`.
- R-2: with the flag off, "persisted deadlines remain hidden and overdue is ignored".
- R-3: "preserving existing due"; a "clear error for a corrupt file".
- R-4: "Rollback writes can drop due metadata, consistent with the old codec, so operations documents retaining a separate copy." Going back to 1.4.0 can lose the due times, and the operator must keep a separate copy. This is the largest unmentioned consequence for the requester.

Counted as missed (five): invalid hours stop at startup; strict-after (equality is not overdue); rollback may drop due and a separate copy is needed; corrupt data file gives an error; exact `on` is the only on value.

## D. In a row but not in the specification

- The command name "npm run backfill:due". R-3 says only "an offline command".
- "while the writer is stopped". The specification has "single-writer" persistence in its non-functional requirements, but no instruction to stop the writer before the backfill.
- "Human list and show". R-2 says only "human CLI output"; it does not name list and show.
- "raw output keeps its four-column contract". R-2 says only "The weekly report's four raw columns remain intact". It does not state a general raw-output contract.
- The "Otherwise" alternatives are not in the specification, as expected for alternatives.

A: yes; rows: 4 (open 4, settled 0, added 0, unstated 0); missed: 5
