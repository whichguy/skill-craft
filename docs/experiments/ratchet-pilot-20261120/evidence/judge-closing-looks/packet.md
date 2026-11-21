# Added requirements to classify

A product was built from a written request and passed all of its tests. A review stage then used the running
product and ADDED requirements to the specification, each one something the specification "did not yet say". Your
job is to judge each added requirement against the request it belongs to: does it belong in the specification of
THAT request?

Give every item exactly one label:

- R, required: the request's words, or what they plainly imply, or (where the request changes an existing product)
  the documented behaviour of that product, require it. A delivery that does not do this is wrong.
- E, expected: the request does not require it, but without it a user would meet a real defect (data lost or
  corrupted, a crash, a wrong or misleading answer). A careful engineer would do it unasked.
- C, choice: the request is silent and more than one behaviour would be correct. The item picks one of them; a
  correct delivery could do otherwise.
- X, excess or wrong: it adds scope the request does not ask for, or it goes against the request.

Judge the requirement, not how well it is worded. Use only what is on this page: do not look for files, and do not
run anything. Where you are unsure between two labels, choose the one further down the list.

Answer with one JSON list and nothing else, one object for each item, in the order given:

[{"id": "D01", "label": "R", "why": "one short sentence"}, ...]

## Request "node-chess-engine"

Build a chess rules engine as a Node.js module src/chess.js (CommonJS, no dependencies; npm test runs node --test). A position is a FEN string. startFen() returns the standard start position. legalMoves(fen) returns an array of every legal move for the side to move in UCI form (for example e2e4, and e7e8q for a promotion), sorted alphabetically. applyMove(fen, move) returns the FEN after the move, with correct castling rights, en-passant square, halfmove clock and fullmove number, or throws IllegalMoveError (a class the module also exports) when the move is not legal. The en-passant target square is set after every two-square pawn push, whether or not a capture is possible (the FEN-spec convention). status(fen) returns ongoing, check, checkmate or stalemate for the side to move. Implement all piece moves, castling on both sides (never out of, through or into check; in UCI it is the king's two-square move: e1g1, e1c1, e8g8, e8c8), en passant, promotion to q, r, b or n, check, checkmate and stalemate. Cover the rules with node --test tests in test/: known games (fool's mate, scholar's mate), castling, en passant, promotion, stalemate and move counts from standard test positions. Keep legalMoves on a middlegame position under 50 ms and a depth-2 legal-move count of the start position under 2 seconds. npm test must pass.

This request starts from an empty project.

### Items for request "node-chess-engine"

D02. Added requirement: An occupied en-passant target can still be used for an ordinary pawn capture.
    How it would be observed: In `4k3/8/3n4/3pP3/8/8/8/4K3 w - d6 0 2`, `e5d6` captures the knight on `d6` and leaves the black pawn on `d5`.

D03. Added requirement: A castling flag with a missing home king or rook stays unusable in a played continuation.
    How it would be observed: From `k7/8/8/8/8/8/7R/4K3 w K - 0 1`, the caller can play `h2h1 a8a7`. The resulting position omits `e1g1` from `legalMoves`, and `applyMove` rejects it with `IllegalMoveError`.

D04. Added requirement: Analysis positions remain usable when the inactive king is already attacked.
    How it would be observed: In `4k3/8/8/8/8/8/4R3/4K3 w - - 0 1`, `status` returns `'ongoing'`, `legalMoves` includes `e2e7`, and applying `e2e7` produces a FEN that reports `'check'` for Black.

D08. Added requirement: A legal double push that blocks check can be captured en passant, even if the capture reopens the check.
    How it would be observed: From `4k3/1p6/8/2P5/B7/8/8/7K b - - 0 1`, Black is in check. Playing `b7b5` blocks the bishop and returns `4k3/8/8/1pP5/B7/8/8/7K w - b6 0 2`. From that FEN alone, `legalMoves` includes `c5b6`. Applying it removes the blocker on `b5`, clears the target, and returns `4k3/8/1P6/8/B7/8/8/7K b - - 0 2`, for which `status` returns `'check'`.

D21. Added requirement: A stale special-move field leaves the rest of the position usable.
    How it would be observed: `4k3/8/8/8/8/8/8/4K3 w K - 0 1` reports `'ongoing'`, allows `e1e2`, and omits `e1g1` from its legal moves. `4k3/8/8/4P3/8/8/8/4K3 w - d6 0 2` also reports `'ongoing'`, allows `e5e6`, and omits `e5d6`.

D33. Added requirement: The first successful move clears unsupported castling flags for either color in the returned FEN.
    How it would be observed: A flag is cleared when its king or corresponding friendly rook is absent from its home square before the move. From `r2k3r/8/8/8/8/8/P7/RN2K3 w Qqk - 0 1`, `a2a3` returns `r2k3r/8/8/8/8/P7/8/RN2K3 b Q - 0 1`. Both black flags are gone immediately, and White retains `Q` even with `b1` occupied.

D34. Added requirement: En-passant eligibility is independent of the move counters.
    How it would be observed: In `4k3/8/8/3pP3/8/8/8/4K3 w - d6 12 2`, `legalMoves` includes `e5d6`. Applying it removes the pawn on `d5` and resets the halfmove clock to `0`.

D36. Added requirement: The position APIs accept equivalent FEN field formatting.
    How it would be observed: For `'\tr3k2r/8/8/8/8/8/8/R3K2R  w\tqkQK - 0008 0015\n'`, `legalMoves` and `status` match the same position written with single spaces, `KQkq`, and counters `8 15`. Applying `e1g1` produces `r3k2r/8/8/8/8/8/8/R4RK1 b kq - 9 15`.

D49. Added requirement: Each contiguous run of empty squares in a FEN rank uses a single digit.
    How it would be observed: All position APIs throw an `Error` for `4k3/44/8/8/8/8/8/4K3 w - - 0 1`, and accept the position with that rank written as `8` for otherwise valid calls.

D51. Added requirement: An en-passant target is unusable if the double push would have left the pushing side's king in check.
    How it would be observed: In `4k3/8/2B5/3pP3/8/8/8/K7 w - d6 0 2`, `legalMoves` omits `e5d6` and `applyMove` rejects it with `IllegalMoveError`. The alleged `d7d5` would have opened the bishop's diagonal from `c6` to the black king on `e8`. The position remains usable for ordinary moves such as `a1a2`.

## Request "shared-expenses"

Build a small shared-expenses service in Node.js (no npm dependencies). server.js listens on the port in the PORT environment variable and keeps its data in the JSON file named by the DATA_FILE environment variable, so groups and expenses survive a restart. POST /groups with {"id": "<group id>", "members": ["<name>", ...]} creates a group: 201, 409 if the id exists, and 400 unless members holds at least two distinct non-empty names. POST /groups/<id>/expenses records an expense paid by one member. {"payer": "<name>", "cents": <positive integer>, "split": "equal"} shares it equally among all members, with any cents left over after an even division going one each to the members listed first. {"payer": "<name>", "cents": <positive integer>, "split": "exact", "shares": {"<name>": <cents>, ...}} makes each member listed in shares owe that many whole cents (zero is allowed), and the shares must add up to cents. It answers 201 with {"expense": <n>}, where n is 1 for the group's first expense, then 2, and so on; 400 for an unknown payer or member, a non-positive or non-integer amount, an unknown split, or shares that do not add up. GET /groups/<id>/balances returns an object with each member's net cents, what they paid minus what they owe, so the balances add up to 0. GET /groups/<id>/settlements returns a JSON array of {"from", "to", "cents"} payments that bring every balance to 0: repeatedly the member who owes most pays the member who is owed most the smaller of the two amounts, and ties go to the member listed first. Every route under /groups/<id> answers 404 for an unknown group. Concurrent requests must never lose an expense. Cover the behaviour with node:test tests under test/ that run with `node --test`.

This request starts from an empty project.

### Items for request "shared-expenses"

D11. Added requirement: An incomplete HTTP upload has no effect on the store.
    How it would be observed: If the connection closes before the full HTTP body arrives, a group creation leaves the ID available and an expense upload leaves the balances and next expense number unchanged. This also holds when the bytes already received form a valid JSON object.

D12. Added requirement: Overlapping server processes cannot silently discard acknowledged writes to the same data file.
    How it would be observed: If an operator starts a replacement on a free port using the current process's `DATA_FILE`, the service may refuse overlapping access. If both processes acknowledge expenses in the same group, they assign distinct expense numbers and both contributions survive after the processes stop and the service restarts.

D13. Added requirement: Tighter admission limits preserve previously recorded data.
    How it would be observed: A supported snapshot from before a tighter group ID or expense amount limit still loads with its recorded groups and expenses. A previously created ID whose request fits the HTTP transport budget continues to work on all three group routes. Previously recorded cents above a new input limit still contribute exactly to balances and settlements, and the sequence continues from the last recorded expense.

D14. Added requirement: An expense beyond the service's exact representation capacity leaves the committed state intact.
    How it would be observed: When a whole-cent amount exceeds the capacity of the service's exact representation, the request returns an error, committed balances remain unchanged after restart, and the next valid expense receives the unused number.

D20. Added requirement: Using a symbolic link as DATA_FILE cannot silently split an existing store into two copies.
    How it would be observed: With `DATA_FILE` set to a symbolic link to an existing store, the service either reports that the configuration is unsupported before acknowledging a write or preserves the link and updates its target. After a successful expense request, restarting through either path recovers the same expense.

D27. Added requirement: The API documents how to address accepted IDs that a URL client would normalize.
    How it would be observed: If `.` or `..` is accepted as a group ID, the API documentation gives a working request form for that literal ID and identifies when the client must send the request target verbatim.

D28. Added requirement: A query string does not change the operation or the addressed group.
    How it would be observed: From the same starting state, a request with a query string has the same result as its query-free counterpart on each of the four API routes. A `?` inside an ID remains part of that ID when encoded as `%3F` in the path segment.

D29. Added requirement: An operator hands over a store created after an earlier process started
    How it would be observed: One process starts successfully before the configured parent directory exists. After the directory is created, another process obtains ownership there and records expenses, then shuts down. The first process can acquire the now-available store. Its first balances GET sees the saved expenses before any write is sent to it, and its next expense continues the saved sequence.

D32. Added requirement: The API documents the HTTP size budget separately from the group ID limit.
    How it would be observed: When the service limits combined request-target and header size, the API documents that limit. The query string counts toward that budget. A request for a maximum-size group ID works with an ordinary query that fits the budget. A query that takes the request over that budget may cause rejection before routing and leaves the store unchanged.

D40. Added requirement: The service documents and enforces its group ID size limit in percent-encoded bytes.
    How it would be observed: An otherwise valid ID at the documented limit can be created and used on all three group-specific routes with ordinary HTTP headers, including after restart. An otherwise valid new ID one encoded byte over the limit returns 400. At a 48 KiB limit, 4,096 `🌒` characters fit, and appending one ASCII letter exceeds the limit.

D41. Added requirement: The service documents any fixed per-expense amount limit and applies it to new inputs.
    How it would be observed: The API documents the largest supported expanded decimal length for a new expense when it imposes a fixed limit. An otherwise valid amount at that limit is accepted when the resulting state is representable, and an amount one digit beyond it is rejected. A representable balance or settlement can grow past that length and is returned with all its digits, including after restart.

D42. Added requirement: A hard-linked DATA_FILE cannot silently split an existing store into separate snapshots.
    How it would be observed: When two hard links name one existing store, an operator using either path with a single server receives an explicit refusal that preserves both paths and the stored bytes, or a successful expense remains visible with the same number and balance contribution after restarting through either path.

D45. Added requirement: A running service cannot silently overwrite a changed store with stale data.
    How it would be observed: If a different valid snapshot is put at the configured `DATA_FILE` after the service loaded it and before a new expense is submitted, the service either rejects the expense and leaves the replacement bytes intact or applies the expense to the replacement snapshot. This also holds for an in-place replacement that retains the original file identity, byte length and modification time.

D48. Added requirement: An operator restarts after an interrupted snapshot save
    How it would be observed: The service stops unexpectedly during a save before the candidate becomes the committed store. The operator restarts with the same `DATA_FILE` while any abandoned candidate is still present. The service recovers the last committed groups and balances, and the next valid expense receives the unused number.

D50. Added requirement: The documented HTTP size budget tells clients how to stay within its usable boundary.
    How it would be observed: The API states whether a request exactly at the stated byte limit fits and explains how to allow for header fields when sizing a request target with a query. A client using the documented rule can send an otherwise valid request near the limit without a size rejection.

D53. Added requirement: Malformed UTF-8 is rejected before it can change stored identifiers.
    How it would be observed: An otherwise valid POST body with a malformed UTF-8 byte sequence receives 400 and leaves the store unchanged. An otherwise loadable JSON snapshot with malformed UTF-8 fails startup and retains its original bytes.

D55. Added requirement: A client reconnects after losing an expense response
    How it would be observed: A client fully uploads an expense and loses the connection before reading the response. If the service committed it, reconnecting and restarting preserve its contribution and expense number. Sending the same expense again records a separate expense with the next number.

D56. Added requirement: Successful JSON results identify their HTTP media type.
    How it would be observed: A successful expense response, balances response or settlements response has a `Content-Type` of `application/json`, with optional parameters.

D59. Added requirement: An operator adopts a replacement snapshot after a stale-write refusal
    How it would be observed: An operator finds that a valid replacement snapshot was installed while the service still held its previous state, and the service refuses the next save. The operator stops every process using the store, keeps the selected replacement at `DATA_FILE`, and restarts. Balances and settlements reflect the replacement before clients send another write, and the next expense continues the replacement's saved sequence.

## Request "ticket-assignment"

This directory is an existing Node.js service with no npm dependencies (README.md describes it): a help-desk ticket API, src/server.js, which `npm start` runs on the port in the PORT environment variable, with a command-line tool in bin/. Add ticket assignment. `PUT /tickets/:id/assignee` with a JSON body `{"assignee": "<agent>"}` assigns the ticket to that agent, and `{"assignee": null}` unassigns it; an agent is a non-empty name of at most 64 characters. Only open and in-progress tickets can be assigned or unassigned. Assigning a ticket to the agent it already has changes nothing. Every ticket shows its `assignee` (null when unassigned). The agent a ticket is assigned to is notified that it was assigned to them. `GET /tickets` gains an `assignee` filter: `assignee=<agent>` keeps that agent's tickets and an empty `assignee=` keeps the unassigned ones; a ticket must match every filter given. The command-line listing shows each ticket's assignee. Everything the service already does keeps working, and its existing tests must still pass as they are. Add node:test tests under test/ for the new behaviour; `npm test` runs them with the existing ones.

This request changes an existing product. Its documents, before the change:

<document name="README.md">
# Help desk tickets

The ticket service behind the IT help desk. People report problems, agents work them through to closed, and every change
is on record. It is a small Node.js service with no dependencies:

- an HTTP API for tickets ([docs/api.md](docs/api.md));
- an append-only audit log of every change to a ticket;
- notifications to requesters, written to an outbox and sent by a background worker;
- an optional data file, so the service keeps its state across restarts;
- `bin/tickets.js`, a command line for operators, and `scripts/weekly-report.js`, the support leads' weekly report.

## Running

Node.js 22 or later. There is nothing to install: the service uses only Node's standard library.

```sh
npm start                    # node src/server.js, on PORT (4180 by default)
PORT=8080 DATA_FILE=data/tickets.json NOTIFY_FILE=data/notifications.jsonl npm start
npm test                     # node --test
```

## Configuration

Every setting is an environment variable. Unset or empty means the default.

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `4180` | the port the API listens on |
| `DATA_FILE` | none | the JSON file the state is saved to after every change and loaded from at start; without it the state lives in memory and is gone when the process ends |
| `NOTIFY_FILE` | none | the file the notifier appends one JSON line to per notification (the mail relay tails it); without it notifications are kept in memory |
| `WORKER_INTERVAL_MS` | `500` | how often the background worker runs; `0` turns it off, and notifications stay pending |
| `MAX_BODY_BYTES` | `65536` | the largest request body accepted |
| `LOG_REQUESTS` | off | `1` logs one line per request on standard error |

A value the service cannot use (`PORT=http`, say) stops it at start with a message naming the variable.
[docs/operations.md](docs/operations.md) covers the data file, the worker and what to do with dead notifications.

## How it fits together

```
src/server.js        puts the service together from its settings and starts it
src/app.js           the HTTP routes; src/router.js and src/http.js are the plumbing
src/store.js         the tickets, the audit log and the outbox, changed together
src/tickets/         ids, the lifecycle (states.js), priorities, request checks, the listing's query
src/pagination.js    cursor pages
src/audit.js         the append-only audit log
src/outbox.js        pending notifications; src/backoff.js times the retries
src/worker.js        the background worker; src/notifier.js and src/templates.js send and word notifications
src/persistence.js   the data file
src/format.js        how the command line prints tickets
bin/tickets.js       the operators' command line
scripts/             the weekly report
```

A request reaches a handler in `src/app.js`, which checks it (`src/tickets/validate.js`) and calls one method of the
store. The store changes the ticket, appends the audit entry, enqueues any notification and saves the data file in one
step. Every few hundred milliseconds the worker delivers the outbox's due notifications. The decisions behind this are in
[docs/decisions/](docs/decisions/).

## Command line

`bin/tickets.js` reads the data file (`DATA_FILE`, or `--data FILE`); it never changes it.

```sh
DATA_FILE=data/tickets.json node bin/tickets.js list --status open
node bin/tickets.js --data data/tickets.json list --priority urgent --raw
node bin/tickets.js --data data/tickets.json show T-0042
```

`list` prints a table. `list --raw` prints one ticket per line with the columns separated by tabs: id, status, priority,
title. `scripts/weekly-report.js` runs `list --raw` and reads these columns by position, so they must keep their
positions.

```sh
DATA_FILE=data/tickets.json npm run report:weekly
node scripts/weekly-report.js --data data/tickets.json --json    # the counts as JSON, for the dashboard
```

## Development

The conventions are in [CONTRIBUTING.md](CONTRIBUTING.md) and the decisions in [docs/decisions/](docs/decisions/).
Changes are listed in [CHANGELOG.md](CHANGELOG.md).
</document>

<document name="docs/api.md">
# Tickets API

The service answers on `http://<host>:<PORT>` (4180 by default). Requests with a body send JSON; every response is JSON
(`content-type: application/json; charset=utf-8`).

## Conventions

- **Ticket ids** are `T-` and a number of at least four digits: `T-0001`, `T-0042`, `T-10000`. Numbers are given out in
  order and never reused ([decision 2](decisions/0002-prefixed-sequential-ids.md)).
- **Times** are ISO 8601 in UTC: `2025-09-01T08:15:00.000Z`.
- **The actor.** A request that changes something may name who is making the change in the `X-Actor` header (at most
  64 characters). The audit log records it; without the header the actor is `system`.
- **Unknown fields** in a request body are refused (400), so a misspelt field is never silently ignored.

## Errors

Every error is answered in one envelope ([decision 4](decisions/0004-error-envelope.md)):

```json
{ "error": { "code": "conflict", "message": "ticket T-0007 cannot go from open to resolved: it can go to in_progress" } }
```

| Code | Status | When |
|---|---|---|
| `invalid` | 400 | the request is malformed: a body that is not a JSON object, a missing or wrong field, a query value out of range |
| `not_found` | 404 | no such ticket, or no such route |
| `conflict` | 409 | the request is well formed, but the ticket's state does not allow it |
| `internal` | 500 | a fault in the service; the message says nothing more |

The message is for people; clients branch on `code`.

## The ticket

```json
{
  "id": "T-0042",
  "title": "VPN drops every hour",
  "priority": "high",
  "requester": "maria@example.com",
  "status": "open",
  "created": "2025-09-01T08:15:00.000Z",
  "updated": "2025-09-01T08:15:00.000Z"
}
```

| Field | Meaning |
|---|---|
| `id` | the ticket's id |
| `title` | one line of text, at most 200 characters |
| `priority` | `low`, `normal`, `high` or `urgent` |
| `requester` | who reported it (usually an email address), at most 64 characters |
| `status` | `open`, `in_progress`, `resolved` or `closed` |
| `created` | when it was opened |
| `updated` | when it last changed; a request that changes nothing leaves it as it was |

## Endpoints

### Create a ticket: `POST /tickets`

```json
{ "title": "VPN drops every hour", "requester": "maria@example.com", "priority": "high" }
```

`priority` is optional (`normal`). Answers 201 with the new ticket, whose status is `open`. The requester is notified
that the ticket was received.

### List tickets: `GET /tickets`

| Parameter | Meaning |
|---|---|
| `status` | only tickets with this status |
| `priority` | only tickets with this priority |
| `limit` | how many tickets a page holds: a whole number from 1 to 100, 20 when absent |
| `cursor` | the `next` of the previous page, to get the page after it |

Filters combine: a ticket is listed only when it matches every filter given, so `?status=open&priority=urgent` lists the
open tickets that are urgent. A filter value that is not a status or a priority is `invalid`.

Tickets come in id order, a page at a time ([decision 5](decisions/0005-cursor-pagination.md)):

```json
{ "items": [ { "id": "T-0001", "...": "..." }, { "id": "T-0002", "...": "..." } ], "next": "eyJ2IjoxLCJhZnRlciI6IlQtMDAwMiJ9" }
```

`next` is null on the last page. Otherwise, pass it as `cursor`, with the same filters, to get the next page. A cursor is
opaque: build none by hand. A cursor the service did not issue is `invalid`.

### Get a ticket: `GET /tickets/:id`

Answers 200 with the ticket, or 404 `not_found`.

### Change a ticket: `PATCH /tickets/:id`

```json
{ "title": "VPN drops every hour on the 3rd floor", "priority": "urgent" }
```

Either field, or both. Answers 200 with the ticket. A closed ticket can no longer change (409 `conflict`). Sending the
values the ticket already has changes nothing: no audit entry, and `updated` stays.

### Move a ticket along its lifecycle: `POST /tickets/:id/transition`

```json
{ "to": "in_progress" }
```

```
open ──► in_progress ──► resolved ──► closed
  ▲                          │
  └─────────── reopen ───────┘
```

Answers 200 with the ticket. A move the lifecycle does not allow from the ticket's status is 409 `conflict`; a `to` that is
not a status is 400 `invalid`. `closed` is final. When a ticket is resolved, its requester is notified.

### A ticket's history: `GET /tickets/:id/audit`

Every change to the ticket, oldest first ([decision 7](decisions/0007-append-only-audit-log.md)):

```json
{
  "items": [
    { "seq": 12, "ticket": "T-0042", "action": "ticket.created", "actor": "system", "at": "2025-09-01T08:15:00.000Z",
      "changes": { "title": { "from": null, "to": "VPN drops every hour" }, "priority": { "from": null, "to": "high" },
                   "requester": { "from": null, "to": "maria@example.com" }, "status": { "from": null, "to": "open" } } },
    { "seq": 15, "ticket": "T-0042", "action": "ticket.transitioned", "actor": "dana", "at": "2025-09-01T09:02:11.000Z",
      "changes": { "status": { "from": "open", "to": "in_progress" } } }
  ]
}
```

`seq` numbers the entries of the whole log. `changes` holds, for each field the change touched, its value before and
after. Actions so far: `ticket.created`, `ticket.updated`, `ticket.transitioned`.

### The outbox: `GET /admin/outbox`

For operators. Every notification the service has enqueued, by state:

```json
{
  "pending": [],
  "sent": [
    { "id": 7, "key": "ticket.created:T-0042", "type": "ticket.created", "to": "maria@example.com", "ticket": "T-0042",
      "data": { "title": "VPN drops every hour" }, "status": "sent", "attempts": 1, "created": "2025-09-01T08:15:00.000Z",
      "nextAttemptAt": null, "lastError": null, "sentAt": "2025-09-01T08:15:00.412Z" }
  ],
  "dead": []
}
```

[Operations](operations.md) explains pending, sent and dead.

### Health: `GET /health`

`{ "status": "ok" }` while the service answers.
</document>

<document name="docs/operations.md">
# Operations

How the service runs in production, and what to look at when something is wrong. The settings are in the
[README](../README.md#configuration).

## Process

One Node.js process per host, behind the internal load balancer, started with `npm start` by the host's service manager.
It logs to standard error, one line per event; `LOG_REQUESTS=1` adds a line per request. `SIGTERM` stops it cleanly: the
worker stops, the server finishes the requests in flight and the state is saved.

`GET /health` answers `{ "status": "ok" }` while the process serves requests.

## The data file

With `DATA_FILE` set, the whole state (tickets, the audit log and the outbox) is one JSON document, rewritten after every
change through a temporary file and a rename ([decision 8](decisions/0008-json-data-file.md)). A crash leaves either the
state before the change or the state after it.

- Back it up by copying it; the copy is consistent, because the file is only ever replaced whole.
- At start the service checks every record. A file it cannot use stops it with a message that names the record, for
  example `data/tickets.json: tickets[3].priority is not a priority`. Fix the record, or restore the backup.
- Ticket numbers are never reused: the file keeps the next number, and a file whose next number is not above every
  ticket's is refused.
- The file grows with the audit log, which is never trimmed. At the help desk's volume that is a few megabytes a year.

## Notifications

A change that should tell someone something (a ticket received, a ticket resolved) enqueues a notification in the outbox
as part of the change ([decision 6](decisions/0006-notification-outbox.md)). The worker runs every `WORKER_INTERVAL_MS`
and delivers the notifications that are due: with `NOTIFY_FILE` set, it appends one JSON line per notification to that
file, which the mail relay tails.

- **Pending** notifications are waiting to be delivered. A failed delivery is tried again 1 s later, then 2 s, 4 s and
  8 s after the next failures (never more than five minutes).
- **Dead** notifications failed five times. The worker logs a warning for each. They stay in the outbox until the data
  file is restored or edited; look at `lastError`.
- **Sent** notifications stay too, as a record.
- A notification has a key. While a notification with a key is pending, enqueueing the same key again changes nothing,
  so a ticket resolved, reopened and resolved again within a few seconds sends one "resolved" notification, not two.

`GET /admin/outbox` lists them all by state. With `WORKER_INTERVAL_MS=0` the worker does not run and notifications stay
pending; that is how to look at what a change enqueues.

## The command line and the weekly report

`bin/tickets.js` and `scripts/weekly-report.js` read the data file and never write it, so they are safe to run beside
the service. The support leads' report runs every Monday at 07:00 from the operations host's crontab:

```sh
DATA_FILE=/srv/tickets/data/tickets.json node /srv/tickets/scripts/weekly-report.js --json > /srv/dashboard/weekly.json
```
</document>

### Items for request "ticket-assignment"

D01. Added requirement: A listing continuation uses current ownership for tickets beyond its cursor
    How it would be observed: After the first page of Dana's tickets, reassign one ticket beyond the cursor away from Dana and assign another ticket beyond the cursor to Dana. With the same filters and cursor and a large enough page size, the next page excludes the first ticket and includes the second in id order.

D05. Added requirement: Assignment eligibility uses the committed status after a failed lifecycle save
    How it would be observed: Force an `in_progress` ticket's move to `resolved` to fail during state file replacement. The transition returns HTTP 500. The ticket remains `in_progress`, with no resolution audit entry or requester notice for the failed move. Restore storage and reassign it successfully without reopening it.

D06. Added requirement: A saved owner or pending assignment recipient must be unambiguous
    How it would be observed: In separate copies of a version 1 snapshot, give one ticket two `assignee` members with different values, or give one pending assignment event two `to` members with different names. This includes members whose JSON-escaped keys decode to the same key. Startup refuses each copy with a diagnostic identifying the file and field, preserves its bytes and delivers no notices.

D07. Added requirement: The service and operator commands refuse snapshots with malformed UTF-8 outside ownership records
    How it would be observed: Replace a byte inside a title in an otherwise valid saved snapshot with `0xFF`. The service refuses startup, and the CLI listing and weekly report fail with a diagnostic identifying the data file and its encoding problem. The commands emit no ticket rows or report counts and leave the snapshot bytes intact.

D09. Added requirement: An upgrade can deliver an earlier assignment notice after its owner was cleared
    How it would be observed: In a release that accepted a name with an internal U+2028, assign a ticket to that name and clear the assignment while the worker is off. Restart on the saved file in the current release with the worker enabled. The ticket is unassigned, and the pending assignment notice appears in the configured notification file with its original recipient, id and key.

D10. Added requirement: A notification path that aliases the state file after startup is a retryable delivery failure
    How it would be observed: Start with separate state and sink destinations, then replace the sink with a symlink to the state file before a pending assignment notice is delivered. The notice remains pending after the first attempt and reports the path conflict in `lastError`. The state file remains a usable snapshot. Restore a separate sink before the next attempt and verify delivery of the same notice key.

D15. Added requirement: An assignment body must give one unambiguous ownership instruction
    How it would be observed: With an active ticket assigned to Sam, PUT the raw body `{"assignee":"Dana","assignee":null}`. It receives `400 invalid` and leaves Sam assigned. Reversing the order of those two members also receives `400 invalid`.

D16. Added requirement: A data file with malformed UTF-8 in a saved assignee is refused at startup
    How it would be observed: Put a raw invalid UTF-8 byte in the assignee string of an otherwise usable version-1 file. The service stops before accepting requests and reports the data file's encoding error.

D17. Added requirement: An assignee cannot introduce a line break into a raw CLI record
    How it would be observed: Try assigning names with an embedded U+0085, U+2028 or U+2029 between two words. If the assignment is accepted, `list --raw` still emits one record per ticket for readers that recognize those characters as line breaks, with the assignee confined to the fifth field.

D18. Added requirement: An assignment body with malformed UTF-8 is rejected
    How it would be observed: Send JSON-shaped bytes containing a raw `0xFF` inside the assignee string. Receive HTTP 400 with code `invalid`. The ticket, its audit history, and the outbox retain their prior state.

D19. Added requirement: An operator can trace a notice to the exact assignment that queued it
    How it would be observed: Assign a ticket to Dana, hand it to Sam, and assign it to Dana again with a different actor. After restart, use the documented notice key to match each of Dana's outbox events and delivered records to its own audit entry and actor.

D22. Added requirement: Retargeting a state link during service leaves both snapshots intact
    How it would be observed: Start on a state symlink, then point it to a different usable snapshot. A real assignment returns HTTP 500. Both files retain their prior bytes, and the API retains its committed assignee, history and outbox. Restore the original link and retry. The assignment commits to the original snapshot.

D23. Added requirement: Agent names cannot contain Unicode line breaks
    How it would be observed: A PUT with U+0085, U+2028 or U+2029 inside an agent name receives `400 invalid`. Each of those characters would otherwise split the name across lines for a reader of the CLI output that recognizes Unicode line boundaries.

D24. Added requirement: CLI assignment history distinguishes a cleared assignee from any agent name
    How it would be observed: Assign a ticket to an agent named `—`, reassign it to an agent named `null`, and then clear it. In `show`, a reader can identify the unassigned value and both named values on the appropriate sides of the history changes.

D25. Added requirement: Malformed UTF-8 cannot stand for an agent name
    How it would be observed: A PUT whose assignee string contains the raw byte 0xFF receives `400 invalid`. A listing request with `?assignee=D%FFana` also receives `400 invalid`. A client can still assign the literal name `D�ana` and select it with `?assignee=D%EF%BF%BDana`.

D26. Added requirement: Assignment saves through a state-file symlink keep the linked snapshot current
    How it would be observed: Configure `DATA_FILE` as a symlink to an existing version-1 snapshot and use a separate notification sink. If startup accepts the state path, a successful assignment leaves the symlink and its target reading the same committed owner, audit entry and outbox event. If the path is unsupported, startup identifies it before accepting requests.

D30. Added requirement: A failed title save leaves the committed title available for assignment notices
    How it would be observed: Force a title edit to fail during state file replacement. The edit returns HTTP 500 and the ticket and audit still show the committed title and history. Restore storage and assign the ticket. The saved ticket and the new assignment notice use the committed title.

D31. Added requirement: A malformed percent escape cannot select an agent with a literal percent sign
    How it would be observed: With a ticket assigned to `Dana%`, `GET /tickets?assignee=Dana%25` finds it. `GET /tickets?assignee=Dana%` receives `400 invalid`.

D35. Added requirement: Splitting a UTF-8 character across upload chunks preserves the assignee
    How it would be observed: Send a valid assignment body for `Daña 😀` with the bytes of the emoji split between HTTP body chunks. The PUT succeeds with the exact name, the assignee filter finds the ticket, and the assignment notice uses that name as its recipient.

D37. Added requirement: A resolvable state symlink can select a new snapshot
    How it would be observed: Start with `DATA_FILE` pointing through a symlink to a missing snapshot in a directory the service can create. Start with an empty store, create and assign a ticket, and read the saved assignment through both paths. The configured symlink remains in place.

D38. Added requirement: The service reports a path conflict between the state file and notification sink
    How it would be observed: Configure `DATA_FILE` and `NOTIFY_FILE` with the same path. The operator receives a diagnostic for the path conflict. If the service starts and queues an assignment notice, the notice remains visibly undelivered.

D39. Added requirement: The human-readable CLI distinguishes names containing text direction overrides
    How it would be observed: For an owner spelled `owner\u202eABC\u202c` with a right-to-left override, the human-readable listing and ticket details and history distinguish that name from `ownerCBA`. Direction controls in a displayed owner name cannot reorder the surrounding ticket fields or history text.

D43. Added requirement: An assignment notice retains the ticket title from the time of assignment
    How it would be observed: Suspend the worker, assign a ticket, and then rename the ticket. Restart with delivery enabled. The queued notice and delivered message identify the ticket using its title at the time of that assignment.

D44. Added requirement: Opening a legacy data file for service reads leaves it untouched
    How it would be observed: Start with a version 1 data file that omits assignees and the worker disabled. Read and list its tickets. Before any mutation or shutdown, the file still has its original bytes, including its original `savedAt` and omitted fields.

D46. Added requirement: Corrupt saved assignment names are refused before serving or delivery
    How it would be observed: In separate copies of a valid version 1 file, replace a byte inside a current assignee or a pending assignment recipient with `0xFF`. Startup refuses each copy with a diagnostic naming the file, leaves its bytes intact and delivers no notices. A copy with a correctly encoded literal U+FFFD in either value still opens and preserves that value.

D47. Added requirement: CLI history distinguishes an unassignment from assignment to a literal name
    How it would be observed: Assign Dana, clear ownership, assign Dana again and then assign the agent named `"null"`. The ownership changes in `tickets show` distinguish the clear from the named assignment.

D52. Added requirement: Raw CLI consumers can identify record boundaries when titles contain Unicode line separators
    How it would be observed: Create a ticket whose title contains U+2028. Splitting the raw listing at LF (U+000A) yields one record for that ticket and preserves the original title in field four. The CLI documentation identifies LF as the record delimiter and explains that a title may contain other Unicode line separators.

D54. Added requirement: The raw CLI documents how consumers recover the exact assignee
    How it would be observed: Use the documented fifth-field decoding rule on tickets assigned to a name with U+2028, a name with the corresponding literal escape text, and a name with an ordinary backslash. A script recovers all three originals exactly, including any characters that resemble the encoding's escape introducer.

D57. Added requirement: An assignee filter with malformed UTF-8 is rejected
    How it would be observed: Assign a ticket to `Ana�`. The properly encoded `GET /tickets?assignee=Ana%EF%BF%BD` finds the ticket. `GET /tickets?assignee=Ana%FF` receives HTTP 400 with code `invalid`.

D58. Added requirement: Every reader diagnoses malformed UTF-8 anywhere in a saved snapshot
    How it would be observed: Put a raw invalid UTF-8 byte in a ticket title in an otherwise usable version-1 snapshot. Service startup, the CLI and the weekly report each fail with the file path and an encoding diagnostic. The file bytes stay intact.
