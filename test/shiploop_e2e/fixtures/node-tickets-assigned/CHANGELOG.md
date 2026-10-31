# Changelog

## 1.4.0 (2025-09-15)

- The operator command line, `bin/tickets.js` (`list`, `show`), and the weekly report, `scripts/weekly-report.js`.
- `list --raw` prints tab-separated columns for scripts.
- Titles and requesters must be a single line of text.

## 1.3.0 (2025-07-08)

- The data file (`DATA_FILE`): the service keeps its tickets, audit log and outbox across restarts
  ([decision 8](docs/decisions/0008-json-data-file.md)).

## 1.2.0 (2025-05-20)

- `GET /tickets` pages with cursors: `{ "items", "next" }` and `?cursor=`, in place of `?offset=` and `total`
  ([decision 5](docs/decisions/0005-cursor-pagination.md), which supersedes decision 3).
- Requesters are told when a ticket is created and when it is resolved, through an outbox and a background worker
  ([decision 6](docs/decisions/0006-notification-outbox.md)).
- `GET /admin/outbox` shows pending, sent and dead notifications.

## 1.1.0 (2025-03-24)

- Every change to a ticket is recorded in an append-only audit log, with the actor from the `X-Actor` header
  ([decision 7](docs/decisions/0007-append-only-audit-log.md)); `GET /tickets/:id/audit`.
- `PATCH /tickets/:id` changes a ticket's title or priority.

## 1.0.0 (2025-02-03)

- Tickets: create, read, list with `status` and `priority` filters, and the lifecycle open, in progress, resolved,
  closed.
- Errors in one envelope ([decision 4](docs/decisions/0004-error-envelope.md)).
