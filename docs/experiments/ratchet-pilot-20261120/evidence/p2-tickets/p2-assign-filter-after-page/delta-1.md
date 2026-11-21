# Delta 1

## What I used and tried

- Compared the request, specification, fix report and referee report with the README, API reference, operations guide and cursor and outbox decisions. The checkout and its Git history contained no build report, test-stage report or plan. The C-74 dispute concerned the fixture's temporary path length. The valid `-` name and distinct identities for repeat handoffs are already covered by C-103, C-64, C-77 and C-132.
- Ran `npm test` and saw 125 tests pass. Started the service with `npm start` on a system-selected port. Exercised assignment, reassignment, clearing, no-ops, missing and inactive tickets, edits and transitions. Checked names of 1, 64 and 65 UTF-16 code units, supplementary characters, malformed inputs, and the actor, body and pagination boundaries.
- Combined status, priority and assignee filters across pages and changed assignments between requests. Ran the documented table, raw, show and weekly report commands. Forced a data-file save failure and retried, restarted on the same data, loaded a legacy file, and checked rejection of a malformed stored assignee. Restored an unavailable notification sink and observed retries and delivery to the original recipients.

## Clauses added

- C-193 — product keeps to it: no. `assignee=R%EFne` returned the ticket assigned to `R�ne`, just as its correctly encoded filter did. A PUT with byte `EF` followed by ASCII inside the name returned 200 and recorded the replacement character in the ticket, history and notification recipient.
- C-194 — product keeps to it: no. PUT and the encoded filter accepted internal U+0085, U+2028 and U+2029. For each separator, a raw listing of one ticket split into two lines using Python's `str.splitlines()`.
