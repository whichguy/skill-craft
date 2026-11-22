# Part D2b: the second sorting (a Sonnet subagent, the nine files under shuffled names)

## The key (not shown to the reader)

```
q1 k9 C
q2 k7 C
q3 k2 A
q4 k1 A
q5 k6 B
q6 k4 B
q7 k5 B
q8 k3 A
q9 k8 C
```

## The brief

# Brief: sorting nine files of three questions each

You are a careful reader. Nine short files each hold three questions that a session chose to put to the person who
requested a change to an existing help-desk ticket service, under the headings `## Cost`, `## Ordinary use` and
`## Disagreement`. You sort each by fixed
definitions. Read only; write nothing; run no command except to read files. Do not judge which question is better.

## The files

Folders `q1` to `q9` in
`<scratch>/lens/d2b-reading/`.
Each holds `question.md` (under each of the three headings: lines `Question:`, `Clause:` and `If no answer
comes:`) and `request.txt`, one letter saying which request the question was written for. Beside them, `product/` is
the service as it was before the change (its code, tests and documents).

## The three requests and, for each, one point

- **A.** The request adds ticket assignment and says of an agent only that it "is a non-empty name". *The point:*
  the longest name an agent may have.
- **B.** The request adds ticket assignment and does not say in which ticket states a ticket may be assigned or
  unassigned. *The point:* the ticket states (open, in progress, resolved, closed) in which a ticket may be
  assigned or unassigned.
- **C.** The request adds due times to tickets, says the tickets already in the production data file get due times
  too, and that due times are switched on only once the data file holds them (`DUE_TIMES=on`). *The point:* who or
  what puts the due times into the existing data file, and what the service does when it is started with
  `DUE_TIMES=on` while the file holds tickets without due times (for example: a separate preparation step and a
  refusal to start, or the service filling them in itself at start).

## What to decide for each of `q1` to `q9`

1. **Asked:** does one of the three `Question:` lines ask about the request's point, alone or among other things?
   `yes` (say under which heading) or `no`.
   A question about a neighbouring matter (for example how long a preparation step may pause writes, or which
   response hours apply to old tickets) is `no` unless it also asks who or what fills the due times, or what the
   service does at start.
2. **Disagreement names the filters:** does the `Question:` under `## Disagreement` ask about how a listing
   combines its status and priority filters (matching both, or either)? `yes` or `no`; if it is `none` or about
   something else, say what.
3. **Settled by the files:** for each of the three questions: could someone answer it from the files under `product/` alone, with no
   word from the requester or from anyone who runs systems outside this folder? `yes` (name the file and the
   passage) or `no` (say in a few words what the files leave undecided). A question about what the requester wants
   in future, or about how a system outside the folder behaves, is `no` even when the files show today's behaviour.
4. **Topics:** each question's subject in at most eight words.

## What to send back

One entry for each of `q1` to `q9`, in order: the request letter, then the four answers, each with the words of the
file that decided it. Then one closing line: for each letter A, B and C, how many of its three questions are
`Asked: yes`.

## The reader's report, word for word

Sorted all nine from the files in d2b-reading. None of them asks about its request's point, so `Asked` is `no` for all nine. The `Disagreement` question is about the status/priority filters in all nine. `Settled` is `no` for all 27 questions.

Product passages I relied on (paths under `product/`):
- Combining filters: `docs/api.md` says "a ticket is listed only when it matches every filter given". `src/tickets/query.js` `matchesFilters` uses `given.some(...)`, so either filter matches. `bin/tickets.js` `list` uses the same `parseListQuery` and `store.list`, so the command line behaves like the API.
- Mail relay: `src/notifier.js` writes `to: event.to` unchanged into `NOTIFY_FILE`, "which the mail relay tails". `src/store.js` only notifies requesters, with `ticket.requester` as `to`.
- Command line: `src/format.js` `RAW_COLUMNS` is id, status, priority, title, and `README.md` says the weekly report reads them by position. The table and `details` have no due column.
- Names today: `src/tickets/validate.js` ("A required single-line text field: trimmed, not empty") trims text fields. Existing filters compare with `===`. There is no agent, assignee, due-time or response-hours concept anywhere in `product/`.
- File format: `docs/decisions/0008-json-data-file.md` says "keeps only the fields it knows".

On `Settled`, a `no` means the files leave it undecided, because it concerns what the requester wants or how a system outside the folder behaves. Where the files show today's behaviour I say so.

**q1 (C)**
1. Asked: no. All three questions are neighbouring matters.
2. Disagreement filters: yes. "overdue tickets with status open and priority urgent ... both ... or ... either".
3. Settled:
   - Cost: no. It asks what the requester wants if operators roll back and upgrade again, and the response hours are not in `product/`. The persistence passage shows 1.4.0 drops unknown fields.
   - Ordinary use: no. It asks what the requester wants for the command-line views, and the files show only today's columns.
   - Disagreement: no. The files show both behaviours but not which to keep.
4. Topics:
   - Cost: deadlines kept or recalculated after rollback.
   - Ordinary use: deadline in command-line views.
   - Disagreement: combined status/priority filters on overdue search.

**q2 (C)**
1. Asked: no.
2. Disagreement filters: yes. "only tickets that meet both filters ... or all overdue tickets that are open or urgent".
3. Settled:
   - Cost: no. Same reason as q1 Cost.
   - Ordinary use: no. Same reason as q1 Ordinary use.
   - Disagreement: no.
4. Topics:
   - Cost: restoring promised deadlines after rollback.
   - Ordinary use: deadline in command-line list and show.
   - Disagreement: combined status/priority filters on overdue search.

**q3 (A)**
1. Asked: no. No question asks about the longest name.
2. Disagreement filters: yes. "open and urgent tickets shows only tickets that are both ... also shows tickets that meet just one".
3. Settled:
   - Cost: no. Whether the relay can route from the name as entered is outside the folder.
   - Ordinary use: no. Assignment does not exist in the files, so what happens to the assignee on resolve is the requester's call.
   - Disagreement: no. "existing dashboards" are outside the folder, and the files show only the filter rule itself.
4. Topics:
   - Cost: mail routing for a name entered at assignment.
   - Ordinary use: assignee kept or cleared on resolution.
   - Disagreement: narrowing combined filters versus keeping dashboards' results.

**q4 (A)**
1. Asked: no.
2. Disagreement filters: yes. "open and urgent ... the service currently includes any open ticket or any urgent ticket".
3. Settled:
   - Cost: no. It depends on what the relay accepts and on an administrator mapping, both outside the folder.
   - Ordinary use: no. It is a requester choice. Existing filters use `===` and fields are trimmed, but nothing covers agent names.
   - Disagreement: no.
4. Topics:
   - Cost: relay identifier or administrator-mapped name.
   - Ordinary use: case sensitivity of agent names.
   - Disagreement: combined status/priority filters, compatibility versus guide.

**q5 (B)**
1. Asked: no. None of the three questions asks about the states in which a ticket may be assigned or unassigned.
2. Disagreement filters: yes. "open and urgent tickets also shows open tickets that aren't urgent and urgent tickets that aren't open".
3. Settled:
   - Cost: no. Relay behaviour and the operators' name list are outside the folder.
   - Ordinary use: no, but it is the closest to settled of the 27. `src/tickets/validate.js` shows that existing text fields are trimmed. The files do not say whether a new assignee field follows that rule. The `assignee=` empty-value and whitespace-only cases appear only in the clause, not in `product/`.
   - Disagreement: no.
4. Topics:
   - Cost: name to relay or operator-maintained address list.
   - Ordinary use: whitespace around agent names.
   - Disagreement: combined filters on existing searches.

**q6 (B)**
1. Asked: no.
2. Disagreement filters: yes. "a search for open and urgent tickets requires both, but today's service returns tickets that are open or urgent".
3. Settled:
   - Cost: no. Relay behaviour is outside the folder, and where the address mapping lives is the requester's call.
   - Ordinary use: no. Existing filters are exact-match, but how agent names behave is the requester's call.
   - Disagreement: no.
4. Topics:
   - Cost: relay resolves name or service looks up address.
   - Ordinary use: case-sensitive agent names.
   - Disagreement: combined filters on existing searches.

**q7 (B)**
1. Asked: no.
2. Disagreement filters: yes. "open, urgent tickets currently shows tickets that are open or urgent".
3. Settled:
   - Cost: no. Relay behaviour is outside the folder, and the files hold no agent directory.
   - Ordinary use: no. Same reason as q6 Ordinary use.
   - Disagreement: no.
4. Topics:
   - Cost: any name, or directory-limited names.
   - Ordinary use: case-insensitive assignee filtering.
   - Disagreement: combined filters on existing searches.

**q8 (A)**
1. Asked: no.
2. Disagreement filters: yes. It also covers the command line: "`tickets list --status open --priority urgent`".
3. Settled:
   - Cost: no. Relay behaviour and the operators' mapping are outside the folder.
   - Ordinary use: no. Same reason as q4 Ordinary use.
   - Disagreement: no. The files show the command line uses the same either-match code as the API today, but not whether it should change.
4. Topics:
   - Cost: relay-deliverable name or mapped display name.
   - Ordinary use: capitalization of assignee names.
   - Disagreement: command-line combined filters when the API is corrected.

**q9 (C)**
1. Asked: no.
2. Disagreement filters: yes. "status and priority must both match, but today's list accepts either match ... overdue, open, urgent".
3. Settled:
   - Cost: no. Same reason as q1 Cost.
   - Ordinary use: no. Same reason as q1 Ordinary use.
   - Disagreement: no.
4. Topics:
   - Cost: exact promised deadlines after rollback.
   - Ordinary use: deadline in command-line list and show.
   - Disagreement: combined status/priority filters on overdue search.

**Borderline `Asked` calls, in case you read them differently.** q1 Cost ("may the upgrade assign new deadlines"), q2 Cost ("may they assign fresh deadlines") and q9 Cost ("may it calculate replacement deadlines") all presuppose a step that fills deadlines. They ask whether a rollback plus re-upgrade may recompute them, not who or what fills the existing data file or what the service does at start with `DUE_TIMES=on`. I counted them as the neighbouring rollback matter and marked them `no`. If you count them as `yes`, the C count below rises to 3.

Closing line: Asked: yes counts are A 0 of 3 (q3, q4, q8), B 0 of 3 (q5, q6, q7), C 0 of 3 (q1, q2, q9).
