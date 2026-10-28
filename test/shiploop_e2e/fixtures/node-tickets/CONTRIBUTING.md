# Contributing

The help desk team maintains this service. Small fixes can go straight to a pull request; for anything that changes the
API, the data file or how notifications work, open an issue first, and record the decision (below).

## Conventions

- **No dependencies.** Node's standard library only (`node:http`, `node:fs`, `node:test`, ...). Do not add packages to
  `package.json`: the service runs on locked-down hosts with no registry access.
- **CommonJS, strict mode, named exports.** Each file starts with `'use strict';` and ends with
  `module.exports = { ... }`. No default exports (`module.exports = fn`), so a name always means the same thing.
- **Every error through the envelope.** A handler that rejects a request throws `InvalidError` (400), `NotFoundError`
  (404) or `ConflictError` (409) from `src/errors.js`, and the app answers it as `{"error": {"code", "message"}}`.
  Never write an error response by hand. "The ticket's state does not allow this" is a conflict (409), not a bad
  request (400). See [decision 4](docs/decisions/0004-error-envelope.md).
- **Changes go through the store.** Every change to a ticket is a method of `TicketStore` (`src/store.js`), which
  applies it, appends the audit entry, enqueues the notifications it causes and saves the data file in one step. Never
  assign to a ticket outside the store, and never append to the audit log or the outbox from anywhere else. A change
  that changes nothing is not a change: no audit entry, no notification. See [decision 7](docs/decisions/0007-append-only-audit-log.md).
- **Notifications only through the outbox.** A change enqueues its notification in the store; the worker delivers it.
  Request handlers never call the notifier. A new kind of notification needs a template in `src/templates.js`. See
  [decision 6](docs/decisions/0006-notification-outbox.md).
- **Background work runs in the worker.** Anything that happens on a schedule is a job of `src/worker.js`, never a
  timer of its own and never something a request does on the side. `WORKER_INTERVAL_MS=0` must stop all of it.
- **Listings are cursor pages.** A list endpoint answers `{ "items": [...], "next": <cursor or null> }`. See
  [decision 5](docs/decisions/0005-cursor-pagination.md).

## Tests

`npm test` runs `node --test`, which finds every file under `test/`. Each module has its own `test/<module>.test.js`;
HTTP tests start the service on port 0 with the worker off (`test/helpers.js`). A pull request keeps the whole suite
passing, and a change of behaviour comes with a test of it.

## Decisions

A decision that shapes the code (a format, a protocol, a rule other code relies on) gets a record in
[docs/decisions/](docs/decisions/): copy `template.md` to the next number, and add it to the index there. A record is
never edited after it is accepted, apart from its status: a decision that no longer holds is superseded by a new record.

## Releases

Bump the version in `package.json` and add a section to `CHANGELOG.md` in the same pull request.
