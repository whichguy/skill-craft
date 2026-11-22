# Part D2: the second sorting (a Sonnet subagent, the nine questions under shuffled names)

## The key (not shown to the reader)

```
q1 g7 C
q2 g2 A
q3 g5 B
q4 g8 C
q5 g9 C
q6 g6 B
q7 g1 A
q8 g3 A
q9 g4 B
```

## The brief

# Brief: sorting nine questions

You are a careful reader. Nine short files each hold one question that a session chose to put to the person who
requested a change to an existing help-desk ticket service, with two runner-up points. You sort each by fixed
definitions. Read only; write nothing; run no command except to read files. Do not judge which question is better.

## The files

Folders `q1` to `q9` in
`<scratch>/lens/d2-reading/`.
Each holds `question.md` (lines `Question:`, `Clause:`, `Why this one:`, `If no answer comes:`, and two `Next:`
lines) and `request.txt`, one letter saying which request the question was written for. Beside them, `product/` is
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

1. **Asked:** does the `Question:` line ask about the request's point, alone or among other things? `yes` or `no`.
   A question about a neighbouring matter (for example how long a preparation step may pause writes, or which
   response hours apply to old tickets) is `no` unless it also asks who or what fills the due times, or what the
   service does at start.
2. **Next:** does one of the two `Next:` lines name the request's point? `yes` (say which line) or `no`.
3. **Settled by the files:** could someone answer the `Question:` from the files under `product/` alone, with no
   word from the requester or from anyone who runs systems outside this folder? `yes` (name the file and the
   passage) or `no` (say in a few words what the files leave undecided). A question about what the requester wants
   in future, or about how a system outside the folder behaves, is `no` even when the files show today's behaviour.
4. **Topic:** the question's subject in at most eight words.

## What to send back

One entry for each of `q1` to `q9`, in order: the request letter, then the four answers, each with the words of the
file that decided it. Then one closing line: for each letter A, B and C, how many of its three questions are
`Asked: yes`.

## The reader's report, word for word

Entries for q1 to q9. Every `Asked` is `no`, so the closing line is 0, 0 and 0.

**q1 (request C)**
- Asked: no. The line asks "should agents see exactly the same deadlines for previously assigned tickets when due times return, or may operators recalculate the lost deadlines using each ticket's then-current priority and response hours". It is about deadlines after a 1.4.0 rollback, not about who fills the due times or what the service does at start.
- Next: no. The lines are "C-18. If response hours change before preparation, should existing tickets receive deadlines based on the original defaults or the hours in effect at preparation?" and "C-17. Can operators briefly pause ticket writes to prepare the file, or must the help desk keep accepting and updating tickets throughout preparation?". Neither names the point.
- Settled by files: no. `product/docs/decisions/0008-json-data-file.md` says "Loading ... keeps only the fields it knows", and `src/persistence.js` `ticketRecord` lists only id, title, priority, requester, status, created, updated. So 1.4.0 drops unknown fields. The files do not decide whether the requester wants exact deadlines kept or recalculated.
- Topic: deadlines kept or recalculated after 1.4.0 rollback.

**q2 (request A)**
- Asked: no. The line asks "should the mail relay receive that name and look up the recipient, or should the ticket service look up Dana's email address in an agent directory maintained by help-desk operators". It is about who resolves the recipient, not the longest agent name.
- Next: no. The lines are "Decide whether a reopened ticket returns to its previous agent or enters the unassigned queue for dispatch." and "Decide whether "Dana Lee" and "dana lee" identify the same agent for repeat assignments and filtering." Neither is about name length.
- Settled by files: no. `src/notifier.js` writes `to: event.to` as supplied to the `NOTIFY_FILE` line, and `docs/operations.md` says "which the mail relay tails". There is no agent directory in `product/`. How the relay treats a name, and whether operators will keep a directory, is outside the folder.
- Topic: name sent to relay or directory lookup.

**q3 (request B)**
- Asked: no. The line asks "should the service send "Dana" to the existing mail relay as the recipient and rely on the relay to find Dana, or should operators maintain a name-to-email mapping". It is silent on which ticket states allow assigning.
- Next: no. The lines are "Decide whether names such as "Dana" and "dana" identify the same agent for assignment and filtering ..." and "Decide whether to append an assignee column to the script-facing listing or show it only in the operator's table ...". Neither is about states.
- Settled by files: no. Same reading as q2: `to` is passed through as given and there is no directory. Relay behaviour and operator practice are outside the folder.
- Topic: name sent to relay or name-to-email mapping.

**q4 (request C)**
- Asked: no. The line asks "must the service recover the exact deadlines users already saw, which requires keeping a record through rollback, or may it recalculate from each ticket's creation time, saved priority and the response hours in effect at reactivation". It is about rollback and recalculation, not who fills the due times or what happens at start.
- Next: no. The lines are "C-16. Can agents pause ticket writes for a maintenance window while operators prepare the file, or must writes stay available throughout preparation? When should tickets accepted before activation first lock in their deadlines?" and "C-12. When an agent filters overdue tickets by both status and priority ...". The first concerns pausing writes and when deadlines lock in; neither says who puts due times in the file or what the service does at start with `DUE_TIMES=on`.
- Settled by files: no. As in q1, decision 0008 and `ticketRecord` show 1.4.0 drops unknown fields. Whether the requester wants exact or recalculated deadlines is not in the files.
- Topic: exact deadlines versus recalculation after rollback.

**q5 (request C)**
- Asked: no. The line asks "must agents see the exact same deadlines as before the rollback, or may the service recalculate them using each ticket's current priority and the response hours in effect at re-upgrade". It is about rollback and re-upgrade only.
- Next: yes, the second line: "C-16 — If operators enable due times before preparation is complete, refuse startup, prepare before serving, or keep serving the old API responses until preparation succeeds." That names what the service does when due times are on and the file is not yet prepared. The first line, "C-15 — For tickets created while due times are off, lock in the priority and response hours at creation or use those in effect when deadlines are prepared.", does not.
- Settled by files: no. Same as q1 and q4: the files show field-dropping on a 1.4.0 save, not what the requester wants.
- Topic: deadlines through rollback and re-upgrade.

**q6 (request B)**
- Asked: no. The line asks "should the service pass "Dana" directly to the existing mail relay ... or should the service look up "Dana" in a help-desk directory". It says nothing about ticket states.
- Next: no. The lines are "C-4 — Decide whether differently capitalized or accented spellings can identify the same agent for assignment and filtering." and "C-15 — Decide whether assigning a ticket back to the same agent while their first notice is still waiting sends a second notice or shares the waiting one." Neither names states.
- Settled by files: no. Same reading as q2: `src/outbox.js` `enqueue` takes `to` as a string and `src/notifier.js` writes it out, with no directory. The relay's behaviour and who maintains addresses are outside the folder.
- Topic: pass name to relay or directory lookup.

**q7 (request A)**
- Asked: no. The line asks "Should callers enter a name like `dana` and rely on the existing mail relay to route that name, or should operators maintain a list mapping agent names to verified inboxes, with callers unable to assign tickets to names missing from the list?" It is about routing and an operator list, not name length.
- Next: no. The lines are "C-3 — Decide whether spelling variants such as `Dana` and `dana` identify the same agent ..." and "C-19 — Decide whether Dana gets one notice or two when a ticket goes from Dana to Sam and back to Dana before the first notice is sent." Neither is about length.
- Settled by files: no. The product has no agent list, and the outbox dedupes only by `key`. Whether the requester wants callers limited to listed names, and how the relay routes, is outside the folder.
- Topic: relay routing or operator-maintained agent-inbox list.

**q8 (request A)**
- Asked: no. The line asks "should the mail relay look up Dana's email address from that name, or should the ticket service look up the address from an agent directory that help-desk operators maintain". Same matter as q2; nothing on name length.
- Next: no. The lines are "Decide whether "Dana Lee" and "dana lee" name the same agent ..." and "Decide whether to deliver a queued notice after the ticket has been reassigned or cleared ...". Neither names length.
- Settled by files: no. Same as q2: the files show the name passed through as given, not who resolves the address.
- Topic: relay lookup versus service-side agent directory.

**q9 (request B)**
- Asked: no. The line asks "should the ticket service hand the name to the mail relay for the relay to look up, or should the ticket service look up Dana's verified delivery address before handing off the notice". It is silent on ticket states.
- Next: no. The lines are "C-18 — If a ticket changes hands before a notice goes out, should the previous assignee still receive it, or should only the current assignee receive one notice?" and "C-28 — Should "Dana" and "dana" identify the same agent for filtering and repeat assignments, and should visually identical Unicode spellings also match?" Neither names states.
- Settled by files: no. Same as q2: `to` is handed on as supplied. Whether the relay resolves names, and who keeps a lookup current, is outside the folder.
- Topic: relay resolves name or service looks up address.

Closing line: A 0 of 3 Asked: yes, B 0 of 3 Asked: yes, C 0 of 3 Asked: yes.
