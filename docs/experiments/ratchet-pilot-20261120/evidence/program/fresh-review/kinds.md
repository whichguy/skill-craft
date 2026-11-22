# Part R: the seventeen distinct findings sorted by kind, twice

## The brief the second reader was given

# Brief: sort seventeen verified findings by kind

Seventeen differences were found by reviewers in delivered changes to a help-desk ticket service, and each was
then reproduced by running the products, so each is a true statement about what a delivered product does. Your job
is to sort each by **what kind of thing it is**, by fixed definitions. You do not say whether it matters or what
should be done about it. Read only; run nothing; write nothing.

## What you may read

Under
`<scratch>/lens/r-verify/`:
`products/starting/` (the service before either change: its code, tests and documents; the requests call it
release 1.4.0) and `request-due-times.txt`. Nothing else.

## The two requests

**Request 1 (findings F1 to F7):** "Add ticket assignment. `PUT /tickets/:id/assignee` with a JSON body
`{"assignee": "<agent>"}` assigns the ticket to that agent, and `{"assignee": null}` unassigns it; an agent is a
non-empty name of at most 64 characters. Only open and in-progress tickets can be assigned or unassigned. Assigning
a ticket to the agent it already has changes nothing. Every ticket shows its `assignee` (null when unassigned). The
agent a ticket is assigned to is notified that it was assigned to them. `GET /tickets` gains an `assignee` filter:
`assignee=<agent>` keeps that agent's tickets and an empty `assignee=` keeps the unassigned ones; a ticket must
match every filter given. The command-line listing shows each ticket's assignee. Everything the service already
does keeps working, and its existing tests must still pass as they are."

**Request 2 (findings C1 to C7 and D1 to D3):** the text of `request-due-times.txt` (read it).

## The seventeen findings (each verified true of the delivered product)

- **F1.** A `PATCH` of the title or priority of a *resolved* ticket is refused with 409; the starting product
  allowed it (it refuses only a closed ticket).
- **F2.** The command-line `list --status S --priority P` now shows only tickets matching both; the starting
  product's command line showed tickets matching either. (The starting product's HTTP list also matched either,
  while its `docs/api.md` says a listing matches every filter given.)
- **F3.** The command-line table shows `-` in the assignee column both for an unassigned ticket and for a ticket
  assigned to an agent whose name is the single character `-`.
- **F4.** `list --raw` now prints a fifth tab-separated field (the assignee, empty when unassigned) after the four
  the starting product printed (id, status, priority, title). The weekly report's counts are unchanged.
- **F5.** A data file edited by hand to hold a 65-character assignee is loaded and served, while the API refuses
  to set such a name. (The starting product's loader likewise loads an over-long requester or title.)
- **F6.** When a ticket goes from agent A to agent B and back to A while A's first notice has not yet been sent,
  no notice is queued for the second assignment to A: A is sent one notice, not two.
- **F7.** `GET /tickets?assignee=dana&assignee=lee` uses the first value and ignores the second. (The starting
  product does the same for a repeated `status`.)
- **C1.** With `DUE_TIMES=on`, `GET /tickets?status=open&priority=urgent` returns only tickets matching both; the
  starting product, and this product with the switch off, return tickets matching either.
- **C2.** With the switch off, creating a ticket when the stored ticket counter is at the largest safe integer
  returns 500; the starting product returns 201.
- **C3.** A stored due time earlier than the ticket's creation time is accepted by preparation and enabled start
  when the creation time is written in a legacy spelling with an explicit offset.
- **C4.** Running the preparation command on a `DATA_FILE` that is a symbolic link replaces the link with a regular
  file. (The starting product also replaces such a link on its first save.)
- **C5.** With the switch off, when a save fails the delivered product undoes the change in memory; the starting
  product keeps the change in memory.
- **C6.** With the switch unset, `list --raw` and the weekly report print a tab or a line break inside a stored
  title as a visible escape (`\t`, `\n`); the starting product prints them as they are.
- **C7.** With the switch unset, two stored titles that differ only in a carriage return against the two
  characters backslash and `r` print identically in `list --raw`; the starting product prints them differently.
- **D1.** A ticket created while the switch is off is saved without a due time; when the switch is later turned on,
  its due time is worked out from the priority and response hours it has then, not those at its creation.
- **D2.** A response-hours setting so large that no due time can be represented is accepted at start; creating a
  ticket of that priority then returns 500.
- **D3.** When release 1.4.0 saves the data file after a roll-back, the due times are dropped; turning the new
  release on again works them out afresh, from the priority and hours of that moment.

## The kinds

- **A, breaks the request's own words.** The request states, in so many words, a behaviour the delivered product
  does not have. Quote the words.
- **B, changes existing behaviour the request does not ask to change.** The starting product did something
  observable, the delivered product does otherwise, and no sentence of the request asks for that change. (For
  request 2, behaviour with the switch off or unset counts here or under A, as you judge the request's words.)
- **C, a choice on a point the request leaves open.** The request's words admit what the delivered product does,
  and the starting product had no such behaviour to preserve, or did the same.
- **D, a gap in new behaviour.** New behaviour does something poor in a case the request does not speak of (an
  unhandled corner), and it is neither A nor B.

For each finding also say **reach**: `ordinary` if it can arise in ordinary use of the service, or `extreme` if it
needs hand-edited data, a failing disk, a setting or number at the edge of what the runtime can hold, or a file
arrangement an operator would have to set up on purpose.

## What to send back

One line for each of the seventeen, in the order above: the id, the kind (one letter; if you hesitate between
two, give the one you choose and name the other), the reach, and one sentence of reason that quotes the request
or names the file of the starting product you relied on. Then one closing line with the count of each kind.

## My sorting (written before the second reader's came back)

```
My sorting of the seventeen distinct findings, written 18:33:41 before the second reader's sorting came back
F1 B ordinary
F2 B ordinary
F3 D ordinary
F4 C ordinary
F5 D extreme
F6 A ordinary (hesitated: D)
F7 C ordinary
C1 B ordinary
C2 A extreme
C3 D extreme
C4 C extreme
C5 A extreme
C6 B ordinary (hesitated: A)
C7 B extreme
D1 C ordinary
D2 D extreme
D3 C ordinary
```

## The second reader's sorting (a Sonnet subagent), word for word

F1. B, ordinary. The request only says "Only open and in-progress tickets can be assigned or unassigned" and does not ask to change PATCH, but starting `src/store.js` `update` refuses only a closed ticket (`isFinal`).
F2. B, ordinary (hesitated with C). The starting `matchesFilters` in `src/tickets/query.js` uses `some`, so the command line showed either-matches, and no sentence about the command line asks to change that. The request's "a ticket must match every filter given" is in the `GET /tickets` sentence, so it admits the change there and only arguably carries over to the command line.
F3. D, ordinary (hesitated with C). The request says only that "the command-line listing shows each ticket's assignee", and an agent is any "non-empty name", so `-` is a legal name that collides with the placeholder for null. The starting table has no null-placeholder to preserve.
F4. C, ordinary (hesitated with B). The request says "The command-line listing shows each ticket's assignee", which admits an assignee field in `list --raw`. Starting `README.md` ("so they must keep their positions") and `scripts/weekly-report.js` read only columns 1 to 4, so appending a fifth field keeps them intact.
F5. C, extreme. The request sets the 64-character limit only for the API, and the starting loader in `src/persistence.js` (`readTicket`/`text`) likewise has no length check on requester or title.
F6. C, ordinary (hesitated with D). The request says only that the agent "is notified that it was assigned to them", which one pending notice satisfies. The starting outbox in `src/outbox.js` already merges a pending notice with the same key ("a second notification with the same key waits for the first").
F7. C, ordinary. The request says nothing about repeated parameters, and starting `parseListQuery` in `src/tickets/query.js` takes `params.get` (first value) for a repeated `status`.
C1. B, ordinary. The starting listing returns either-matches (`some` in `src/tickets/query.js`), and request 2 says nothing about filter combination. With the switch on, "Everything the service already does keeps working" is what is broken, and the on and off modes now differ.
C2. A, extreme. "until the DUE_TIMES environment variable is `on`, the service answers exactly as it does today"; the starting product returns 201 here and the delivered product returns 500 with the switch off.
C3. D, extreme. The request does not speak of validating a stored due time against its creation time. The legacy-offset spelling slips past a new check in the new preparation and start behaviour, which needs hand-edited data.
C4. C, extreme. The starting `save` in `src/persistence.js` writes a temporary file and `renameSync`s it over `DATA_FILE`, which replaces a symlink the same way. The request does not speak of links, and a link set up on purpose is needed.
C5. A, extreme (hesitated with B). "until the DUE_TIMES environment variable is `on`, the service answers exactly as it does today"; the starting store (`apply`/`create` in `src/store.js`) keeps the change in memory when `save()` throws, and the delivered product with the switch off does otherwise. It needs a failing disk.
C6. A, extreme. "until the DUE_TIMES environment variable is `on`, the service answers exactly as it does today", and starting `rawLine` in `src/format.js` prints titles verbatim. A tab or line break in a stored title needs hand-edited data, because starting `src/tickets/validate.js` `text` forbids control characters.
C7. A, extreme. This has the same words and the same starting `rawLine` as C6, and a title with a carriage return or a literal backslash and `r` needs hand-edited data (control characters are refused by `validate.js`).
D1. D, ordinary (hesitated with A). The request ("A ticket's due time is set once") speaks of tickets already in the file and of switching on only after the file holds due times, but not of a ticket created while the switch is off. Its due time is later worked out from the priority and hours of that later moment.
D2. D, extreme. The request says the help desk "must be able to change those hours" and is silent on a value too large to represent. The new start validation accepts it and creation then fails with 500. It needs a setting at the edge of what the runtime can hold.
D3. D, ordinary (hesitated with A). The request requires 1.4.0 to "still start on the data file the new release wrote and show every ticket", and that holds. But the starting `ticketRecord` in `src/persistence.js` writes only the known fields, so 1.4.0's save drops `due`. The request does not say what happens to due times after a roll-back and a later switch-on, so they are worked out afresh. A roll-back is an expected operation.

Counts: A 4 (C2, C5, C6, C7), B 3 (F1, F2, C1), C 5 (F4, F5, F6, F7, C4), D 5 (F3, C3, D1, D2, D3). Reach: ordinary 9 (F1, F2, F3, F4, F6, F7, C1, D1, D3), extreme 8 (F5, C2, C3, C4, C5, C6, C7, D2).
