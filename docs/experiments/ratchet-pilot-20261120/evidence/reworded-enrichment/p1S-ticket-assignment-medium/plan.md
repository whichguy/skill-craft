# Plan: ticket assignment

## Approach

The service layers are: `src/app.js` (validate, call one store method) → `src/store.js` (check state, apply, audit,
enqueue, save) → `src/persistence.js` (data file) with `src/outbox.js`/`worker.js`/`notifier.js`/`templates.js` for
notifications, and `bin/tickets.js` + `src/format.js` for the command line. Assignment is one more store change that
follows the `update`/`transition` pattern exactly (CONTRIBUTING.md: all changes through the store). Parts touched:

- `src/tickets/validate.js`: new `assigneeBody(body)` → `string | null`. `onlyFields(body, ['assignee'])`; `'assignee' in body`
  must hold (a missing field is 400, not "unassign"); `null` → `null`; otherwise `text(body, 'assignee', 64)` (any
  non-string → 400 by `text`'s own check). Export a `LIMITS.assignee = 64`.
- `src/store.js`: `create` gives the ticket `assignee: null`; the constructor normalises every loaded ticket with
  `assignee: ticket.assignee ?? null`; new `assign(id, assignee, actor)`; `CREATED_FIELDS` is **not** changed (see Nuances).
- `src/app.js`: `router.put('/tickets/:id/assignee', ...)`: `validate.assigneeBody(await body(req))`, then `store.assign(...)`, 200.
  `Router.put` already exists.
- `src/templates.js`: template `ticket.assigned` (subject/body mention the ticket id and title).
- `src/tickets/query.js`: `assignee` filter parsing; `matchesFilters` becomes "every".
- `src/persistence.js`: `ticketRecord` includes `assignee`; `readTicket` defaults a missing one to `null` and validates it.
- `src/format.js` + `bin/tickets.js`: assignee column in the table, a fifth raw column, an `assignee` line in `show`.
- Docs: `docs/api.md` (endpoint, filter, `assignee` in the ticket shape, action name, notification type), README (command
  line example), `CHANGELOG.md`, `package.json` version 1.5.0 (CONTRIBUTING: releases). A decision record is optional;
  skip unless time allows (the filter fix and per-agent outbox key are the candidates).
- Tests: new files only, no edits to existing test files.

Data: ticket = existing fields + `assignee: string|null`. Audit entry change key `assignee: {from, to}`. Data file stays
`version: 1`: a missing `assignee` means `null`, so old files load and no migration is needed.

## Decisions

1. **Where the check lives.** Body shape → `validate.js` (400); existence and state → store (404/409). Validate first,
   then look up the ticket, as `PATCH` does, so a malformed body for a missing or closed ticket is 400. Rejected: looking up first.
2. **Trim and control characters (C-3 open).** Reuse `text()`: trimmed, `" dana "` stored as `dana`, `"  "` refused,
   control characters refused. Reason: same as `requester`, and a tab in a name would break `list --raw`. Length is
   measured after trimming. Rejected: a raw-length check with no trim.
3. **Case (C-15 open).** Case-sensitive exact match. Rejected: lower-casing, which would conflate stored names.
4. **Conflict vs no-op on resolved/closed (C-5 open).** Check status first: a resolved or closed ticket is 409 for any
   assignment request, including a repeat of the current value. Simple and strict. Rejected: allowing a no-op 200.
5. **No-op detection.** `assign` builds `changes` only if `ticket.assignee !== assignee`, then calls `apply`, which already
   skips audit, `updated`, effects and save when `changes` is empty (C-7, C-8, C-14).
6. **Audit action.** `ticket.assigned` for both assign and unassign. Documented in docs/api.md's action list. Reason: one
   action per endpoint like `ticket.transitioned`. Rejected: separate `ticket.unassigned`.
7. **Notification (C-11, C-12).** Type `ticket.assigned`, `to` = the agent name, `data: {title}` (the existing `notify`
   already sets this). Pass an explicit key `ticket.assigned:<id>:<agent>` to `notify`'s fifth parameter. The default key
   `type:ticket` would let a pending notification for dana swallow omar's. Enqueue only when the new value is not null
   (C-13). Rejected: telling the previous agent they lost the ticket (spec Open, not requested).
8. **Filter representation.** `parseListQuery` sets `filters.assignee = params.get('assignee')`, with `''` mapped to `null`
   (unassigned). `matchesFilters` compares `(ticket.assignee ?? null) === value`. The value is not trimmed or validated:
   an unknown or over-long name matches nothing, it is not an error. Rejected: 400 for a bad name.
9. **`matchesFilters` → every.** Replace `.some` with `.every`. docs/api.md and the request say every; the existing
   single-filter tests keep passing. This is a deliberate fix of an existing bug, because assignee+status is
   otherwise wrong. Add a unit test plus an API test for status+priority.
10. **CLI.** Table: add `ASSIGNEE` between `REQUESTER` and `UPDATED`; placeholder `-` for none; TITLE stays last (the
    last column is unpadded). Raw: append the assignee as a 5th column, empty string when unassigned (names cannot hold
    tabs or newlines because of decision 2). `RAW_COLUMNS` stays the four columns in place; add the fifth via a separate
    constant so `weekly-report` positions are untouched. No `--assignee` option on the CLI (not requested).
11. **Persistence.** Whitelist `assignee` in `ticketRecord`; in `readTicket`, a value of `undefined` becomes `null`; it
    must otherwise be null or a non-empty string, else `DataFileError`. Version stays 1.

## Nuances

- **Data file silently drops the field (C-10).** `ticketRecord` is a whitelist used for both save and load, so without
  the change an assignment vanishes at the next save, with no error. Test: assign, restart from the file, read it back.
  Also an old-format file (no `assignee`) must load as `null`, and persistence's `readTicket` calls `ticketRecord` first,
  so `undefined` must be normalised after it. Existing persistence test compares only seven fields, so it still passes.
- **Store constructor, not only persistence.** `TicketStore` may be built from a state directly (CLI `openStore`, tests),
  so normalise `assignee` in the constructor as well, or `matchesFilters` and output would see `undefined` (JSON would omit the field, violating C-9).
- **`matchesFilters` "any" bug (C-17).** With `some`, `?assignee=dana&status=open` would list all open tickets plus all of
  dana's. Fix to `every`; `null` is a legitimate filter value, so do not use a truthiness test and keep skipping only `undefined`.
- **Empty `assignee=` (C-16).** `params.has('assignee')` is true and the value is `''`; this must not fall into a
  "filter absent" path. `?assignee` with no `=` is also `''`, so unassigned. Two `assignee` params: first wins (`get`), as for other filters.
- **Pagination (C-18).** Filtering happens before `paginate`, so `next` is right; the CLI's `allTickets` passes filters through unchanged.
- **Outbox dedupe (C-12).** Per-agent key. Consequence: dana → omar → dana before delivery yields one pending dana
  notification (the key is still pending); accept and note it. After delivery the key is free, so a later reassignment to dana notifies again.
- **Idempotence (C-7).** No `updated` change, no audit, no event, and no save. Return the ticket copy. Also unassign of
  an unassigned ticket (C-8) must not emit an audit entry with `from: null, to: null`.
- **Unassign on a ticket that has an assignee** must produce `to: null` in the audit (not `undefined`; `freeze` keeps `null`).
  `describeChanges` prints `assignee dana -> null` for the CLI's history; acceptable. A change from null prints `assignee dana`.
- **Validation of types (C-4).** `{"assignee": 5}`, `true`, `[]`, `{}` → 400 via `text`. `{}` (no field) → 400, never an
  implicit unassign. `{"assignee":"a","x":1}` → 400 via `onlyFields`. Non-object bodies are already refused by `readJson`.
- **Limits (C-3).** 64 accepted, 65 refused, `""` refused, ticket unchanged and no audit/outbox after a refusal.
  Validation happens before the store call, so nothing is half-applied.
- **Creation (C-9, C-21).** `create` adds `assignee: null` but the creation audit entry's fields (`CREATED_FIELDS`) stay
  as they are, so existing audit expectations (`test/api.test.js` line ~158) hold. `POST`/`PATCH` bodies still refuse `assignee` because their `onlyFields` lists are unchanged.
- **Status gating in store, using `states.js`.** Use `isActive(status)` (`ACTIVE` = open, in_progress, already exported),
  not `isFinal`: `resolved` is not final (it can go to `closed` or back to `open`) yet may not be assigned. A transition
  never touches the assignee: a resolved or closed ticket keeps its assignee (still listed by the filter, shown by the CLI),
  and a reopened one has it again. Do not clear it on transition.
- **Order of effects inside `apply`.** `effects(at)` runs after the field is set and before `save`, so the notification and the ticket are saved together.
- **Notification recipient is a name, not an email.** The notifier only needs a non-empty string `to`; the template must
  not assume an `@`. A worker run delivers it; there is no template failure path because the type is registered.
- **Existing tests.** `test/notifier.test.js`/`outbox` tests are unaffected. Any test asserting the whole ticket shape
  with `deepEqual` would break on the new field; none was found by grep (api.test line 21 compares a created ticket to a GET of the same, both with the field).
- **Rollback.** An older service reading a new file drops assignees on its next save; no crash. Say so in the changelog.
- **Concurrency.** Store calls are synchronous, so two PUTs cannot interleave.
- **Ports and processes in tests.** Use `withService` (port 0, worker off) and `service.worker.tick()` to deliver, and
  `service.notifier.delivered` to read.

## Build order

1. `validate.js` `assigneeBody` + `test/validate.test.js`-style unit tests in a new file (`test/assignee.validate.test.js`).
2. `query.js` (filter + `every`) + new unit tests; run the existing `query.test.js`.
3. `persistence.js` `assignee` record/read + store constructor normalisation + a store-level restart test via a temp file.
4. `store.js` `assign`, `create` field; `templates.js` `ticket.assigned`; store tests (no-op, 409, audit, outbox, per-agent key, unassign).
5. `app.js` route; API tests via `withService` (U-1, U-2, U-3, errors, restart with `dataFile`, delivery through `worker.tick()`).
6. `format.js` + `bin/tickets.js`; CLI tests calling `main(argv, {env, out})` with a data file; check `weekly-report` `count` still right.
7. Docs, CHANGELOG, version. Then `npm test` for the whole suite.

## How we will know

- **U-1 / C-1, C-3, C-4, C-11, C-12:** PUT `dana` → 200, `assignee` `dana`, GET agrees; 64 / 65 / `""` / numeric / missing /
  extra field cases; `/admin/outbox` pending has `ticket.assigned` to `dana`; `worker.tick()` then `notifier.delivered`
  has a line to `dana` mentioning the id; assign dana then omar before tick → both delivered to their own agent.
- **U-2 / C-2, C-8, C-13:** unassign → `null`, no new outbox event; unassign again → no new audit entry, same `updated`.
- **C-5, C-6:** resolved and closed tickets (through `/transition`) → 409 and `assignee`/`updated` unchanged; `T-9999` → 404.
- **C-7, C-14:** repeat assign: same `updated`, audit length and outbox count unchanged; a real change shows `assignee`
  `from`/`to`, the `X-Actor` and `updated` equal to the entry's `at` (manual clock advanced between calls).
- **U-3 / C-15–C-18:** several tickets with mixed assignees, statuses and priorities; `?assignee=dana`, `?assignee=`,
  `+status`, `+priority`, `?status=open&priority=high`; paging with `limit=1` following `next`; a name differing only by case is not matched.
- **C-9, C-10:** every ticket response has `assignee`; a hand-written version-1 file without it loads as `null`; assign,
  stop, start again on the same file, the assignee remains.
- **U-4 / C-19, C-20:** `main(['--data', f, 'list'])` shows the name in the row and `-` for others; `--raw` first four
  columns identical and `weekly-report.count` over the lines gives the same counts.
- **U-5 / C-21, C-22:** `npm test` passes with no existing test file edited (check `git status` shows only added test files);
  POST/PATCH with `assignee` still 400.
- **A test must not forget:** the no-change cases check three things (updated, audit, outbox); 64/65 boundaries; the
  restart; the per-agent key; unassign sends nothing; status+priority "every"; stop every server and use port 0.
