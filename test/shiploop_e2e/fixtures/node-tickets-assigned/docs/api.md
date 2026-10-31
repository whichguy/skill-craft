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
