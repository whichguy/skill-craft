# Plan: ticket assignment

## Approach

The change follows the layering the repo already has (README "How it fits together", CONTRIBUTING): handler → validate → one store method → audit + outbox + save.

Parts touched:

- `src/tickets/validate.js`: new `assignment(body)`: `onlyFields(body, ['assignee'])`, then `assignee` must be present (`'assignee' in body`), and be `null` or a non-empty string; returns the string or `null`.
- `src/store.js`: new `assign(id, assignee, actor)`. New tickets get `assignee: null`. The constructor normalises loaded tickets (`assignee` missing → `null`). `CREATED_FIELDS` is NOT changed (see Nuances).
- `src/app.js`: `router.put('/tickets/:id/assignee', ...)`. `router.put` already exists in `src/router.js`. Returns 200 and the ticket.
- `src/templates.js`: new template `ticket.assigned` (subject/body name the ticket id and title; the agent is the addressee).
- `src/tickets/query.js`: `parseListQuery` reads `assignee`; `matchesFilters` becomes AND (`every`).
- `src/persistence.js`: `ticketRecord` saves `assignee`; `readTicket` accepts a missing `assignee` as `null`, and otherwise requires `null` or a non-empty string. `VERSION` stays 1.
- `src/format.js` and `bin/tickets.js`: ASSIGNEE table column, `assignee` line in `details`, `--assignee` option, usage text.
- Docs: `docs/api.md`, `README.md` (command line), `CHANGELOG.md`, `package.json` version bump (1.4.0 → 1.5.0, per CONTRIBUTING "Releases"). `docs/decisions/` gets no new record unless a reason appears; if the builder wants to record the AND-filter fix or the notification key, add `0009-…` plus its index entry. Do not edit accepted records.
- Tests: new files only, e.g. `test/assignment.test.js` (HTTP + store) and additions in new files for query, persistence and CLI. Do NOT edit existing test files (they must pass "as they are").

## Decisions

1. **Where the assignee check lives.** Body shape → `validate.assignment` (400). Ticket state → `store.assign` (409). Order in the handler is validate first, then the store (so 400 beats 409 and 404 for a bad body, matching how `PATCH` and `transition` already behave). Resolves C-4's Open as "reasonable answer: 400 first", reported by the builder. Existing behaviour: 404 for an unknown id comes from `store.find`, after body validation. Tests must not combine these.
2. **Name text rules (C-1/C-3 Opens).** Reuse the existing `text()` helper with limit 64 (same as `requester`): trims, refuses whitespace-only, control characters and over-length. Consistency with requester/actor wins over inventing new rules. `text()` is built around `body[name]` and says "must be a string", so a `null` is handled before calling it. The stored name is the trimmed value; tests use untrimmed-safe names only. The builder states in the report that trimming and the 64 limit were chosen.
3. **Presence of the field.** `{}` has no `assignee`: 400. `{"assignee": null}` is explicit unassign. `undefined` can't occur in JSON, but test with `'assignee' in body`, not `body.assignee === undefined`, so a body missing the key is not mistaken for null.
4. **Audit.** One entry, action `ticket.assigned` for a non-null result, `ticket.unassigned` for null (names free per C-9), `changes: { assignee: { from, to } }` via the existing `apply()`. Reusing `apply` gives "no change → no audit, no `updated` bump, no notify" for free, and sets `updated`.
5. **Order inside `assign`.** `find` → status check (`isActive`, 409 even for a no-op, C-4) → compute change → `apply`. The status check goes BEFORE the no-op shortcut. The existing `update()` does the reverse-ish (isFinal); do not copy it: `update` allows resolved tickets, assignment must not. Use `isActive` from `states.js`.
6. **Notification key (C-10/C-11).** `store.notify` defaults the key to `type:ticketId`, and the outbox drops a second event with the same key while the first is pending. A reassignment from dana → omar before the worker runs would silently lose omar's notification. Pass an explicit key that includes the agent: `ticket.assigned:${id}:${agent}`. Rejected alternative: a key with the audit seq/time: that would enqueue duplicates for A→B→A-quickly cases; including the agent is enough and still dedupes a truly identical pending notification. Note A→B→A while A's first is still pending: A's pending event is returned (not requeued): A is still told once, accepted.
   `to` is the agent name as stored. The outbox requires a non-empty string, which is guaranteed by validation. `data` carries `{ title }` via `notify`; the template may only use `event.ticket`, `event.data.title`, `event.to`.
7. **Effects only on assign, not unassign (C-12).** The `effects` callback is passed only when `assignee !== null`.
8. **Filter semantics.** `parseListQuery`: `params.has('assignee')` → `filters.assignee = value === '' ? null : value`. `null` flows through `matchesFilters` because its guard is `value !== undefined`. Exact, case-sensitive match (C-13). `matchesFilters` switches `some` → `every` (C-15). Existing tests only use one filter at a time, so they still pass. Never throw `invalid` for assignee (C-16). For `?assignee=a&assignee=b`, `params.get` returns the first: acceptable.
9. **CLI.** Add `ASSIGNEE` column to `TABLE_COLUMNS` before `TITLE` (title stays last, unpadded) with `ticket.assignee ?? '-'`. `list --raw` stays byte-identical (decision for C-19's Open: do not carry assignee in raw; zero risk for the weekly report). `--assignee VALUE` is added to the option list in `parseArgs` (`options.query.set('assignee', value)`; the empty string must be accepted, and `argv[index+1] === undefined` is the only "missing value" case). Rejected: adding it to raw as column 5.
   `details` gets an `assignee` field line (`-` when null). `describeChanges` prints `assignee dana` for `from: null` and `assignee dana -> null` when unassigning; improve to show `-` only if trivial, otherwise leave.
10. **Persistence format.** Add the field with no version bump: old files lack it and load as `null`; a file written now with `assignee` is readable by the same version. Rejected: `VERSION` 2 (would refuse old files, violates C-7).

## Nuances

- **C-15 / existing code.** `matchesFilters` is `some` today: a latent bug that docs/api.md says is the opposite. Adding `assignee` without fixing it makes `status=open&assignee=dana` list every open ticket plus all of dana's. Fix to `every`. Also the CLI's `allTickets` goes through the same function.
- **`CREATED_FIELDS` and `test/store.test.js` line 37.** That existing test does `deepEqual` on the create audit entry's `changes`. Adding `assignee` to `CREATED_FIELDS` would break it. Leave it; a new ticket's audit entry does not list `assignee`.
- **Tests that deepEqual a ticket.** `test/store.test.js:22` destructures specific fields (safe). `test/api.test.js:21` compares POST body with GET body (both gain `assignee`, safe). Run the full suite after the first change to the ticket shape, to catch any others.
- **Existing data (C-7).** Three places create ticket objects from saved data: `persistence.readTicket`/`ticketRecord`, the `TicketStore` constructor (used directly by the CLI's `openStore` and by tests passing `state`), and `snapshot()`. Normalise in `readTicket` AND the constructor (`assignee: ticket.assignee ?? null`), otherwise a ticket from a state object shows no `assignee` key at all, and `?assignee=` (null) would not match `undefined`. The `ticketRecord` function is shared by save and load: using `ticket.assignee ?? null` there covers both. Validate on load: non-null non-string or empty string → `DataFileError`.
- **Restart (C-8).** `ticketRecord` is the whitelist for the data file: forgetting `assignee` there means the field silently vanishes on save. Test with a real temp data file, start, assign, stop, start again.
- **Persistence ordering.** `apply()` calls `save()` after `effects`. The notification is therefore saved in the same write as the assignment. Keep using it; don't call `outbox.enqueue` or `save` separately.
- **No-op rules (C-2, C-6).** Same agent → `apply` gets empty `changes` → returns copy, no audit/notify/`updated`. Compare against stored (trimmed) name, so `" dana "` on a ticket assigned to `dana` is also a no-op.
- **Closed/resolved no-op (C-4).** 409 even when nothing would change. The status check must come before the no-op check.
- **Unknown fields (C-3).** `{ "assignee": "a", "x": 1 }` → 400. `PATCH` must keep refusing `assignee` (C-20); do not add it to `ticketPatch`'s allowed fields.
- **Non-object bodies** (array, string, number, empty) are already `InvalidError` from `readJson`; do not re-check. An array body for `onlyFields` is excluded by `readJson`.
- **Method routing.** `PUT` on `/tickets/:id/assignee` now exists; the 404 hint for other methods (`router.methodsFor`) will list PUT. `GET` on that path stays a 404 `not_found` envelope. Check `test/router.test.js`/`api.test.js` don't assert the exact message for this path (they test other paths).
- **Template (C-10).** A notification type without a template gets retried and goes dead. The template `ticket.assigned` must exist, or the worker records failures. Test delivering through the worker + notifier (see `test/worker.test.js` for how the worker is driven with a manual clock) and check `notifier.delivered` has `to: 'dana'` and a subject/body naming the ticket.
- **Outbox `to` is not an email.** Open point in C-10; do nothing special, report it.
- **Pending notification after unassign/transition.** A pending `ticket.assigned` is still delivered after a later unassign (C-12 only says no new notification). Do not cancel outbox events.
- **Status transitions (C-20).** `transition` and `update` use `apply`, which assigns only the changed fields, so the assignee is kept. Resolved/closed tickets keep their assignee and still show it, and still match `assignee=` filters.
- **Cursor paging with filters.** `store.list` filters before `paginate`, and the CLI's `allTickets` passes the last item id as cursor; unchanged with a null filter value. Check a page boundary where the next page's first tickets have a different assignee.
- **Query value edge cases.** `assignee=` → `''` → null; `assignee=%20` → `' '` is a name nobody has (empty result, not null; no trimming of filter values). `?assignee` with no `=` is also `''` (URLSearchParams) → unassigned.
- **CLI `show`/`list` read-only.** The CLI store has no persistence; the constructor normalisation must not write. `--assignee ""` must survive `parseArgs`: do not treat an empty string as missing. Table placeholder must not be the text `null`.
- **Weekly report (C-19).** Run `node scripts/weekly-report.js --data FILE --json` before and after on the same data; counts must be identical.
- **Version bump** in `package.json`: do it with the CHANGELOG entry; no test reads the version (grep first).
- **Docs.** `docs/api.md` filter text currently says a filter value that is not a status or priority is `invalid`; add that `assignee` is never invalid, and describe the empty value. Keep the ticket example's `assignee` field.

## Build order

1. `validate.assignment`, `templates['ticket.assigned']`, `query.js` (`assignee` parse + `every`). Run `npm test` (existing tests must pass).
2. Store: constructor normalisation, `create` sets `assignee: null`, `assign()`. Run `npm test`.
3. Persistence: `ticketRecord`/`readTicket`. Run `npm test`; then manually round-trip an old-format file.
4. App route. Smoke test by hand on a free port (PORT=0 is not supported by `npm start`; use a random high port and stop it by pid), or by the new HTTP tests.
5. CLI: format.js, bin/tickets.js. Run it against a data file from step 4.
6. New tests (below), then full `npm test`.
7. Docs, CHANGELOG, version.

## How we will know

New test files only; use `withService` and the manual clock from `test/helpers.js`, with `workerIntervalMs: 0` and drive the worker explicitly where delivery is checked.

- **U-1 / C-1, C-5, C-4, C-3:** PUT dana on open and on in-progress → 200, `assignee` dana, `updated` changes, GET agrees. Resolved and closed → 409 `conflict`, unchanged, also for same agent and for null. T-9999 → 404. Bodies `""`, `5`, `true`, `[]`, `{}`, `{}` missing field, extra field, non-JSON → 400 and the ticket unchanged. Don't combine bad body with closed ticket.
- **U-2 / C-2:** unassign → null; unassign an unassigned ticket → 200, `updated` unchanged, audit length unchanged.
- **C-6:** same agent twice → second call: `updated` unchanged, audit length +0, outbox pending count +0.
- **U-3 / C-10, C-11, C-12:** after assign, `/admin/outbox` pending has an entry `to: 'dana'`, `ticket: T-0001`; run the worker (or call due notifications and the notifier as `worker.test.js` does) and see the delivered line with the ticket id in subject/body. Assign dana then omar before delivery → both pending. Unassign → no new event.
- **C-9:** audit gains one entry with `changes.assignee` `{from, to}` and the `X-Actor`; none for no-ops.
- **C-7, C-8:** new ticket has `assignee: null`; every list item has the key; a hand-written old-format data file (no `assignee`) loads and shows null; assign, stop, restart on the same file, still assigned; the file still loads after an unassign.
- **U-4 / C-13–C-16:** list by agent, by empty `assignee=`, by `status`+`assignee`, by all three filters, a ticket matching only one filter excluded, unknown agent → `{items: [], next: null}`, paging with `limit=1` through assignee-filtered results, existing `status=bogus` still 400. Add a direct `matchesFilters` AND test in a new file.
- **U-5 / C-17–C-19:** CLI `main()` with a temp data file and captured streams: row shows dana's name, unassigned row has no `null`, `show` shows it, data file bytes unchanged after `list`; `--raw` columns 1–4 equal the old values; `--assignee ""` and `--assignee dana` filters; weekly report JSON counts unchanged.
- **U-6 / C-20:** whole existing suite passes unmodified; `PATCH` with `assignee` → 400; transition keeps the assignee and still notifies the requester on create and resolve.
- **C-21:** grep the docs for the endpoint, the filter and the CHANGELOG entry.

Do not forget: tests must pass whichever answer the builder took for an Open point (whitespace, max length, 400-vs-409 order, audit action names, case-matching, raw column), so they use plain lowercase names and never combine failures. Stop every server by pid; use port 0 or a random high port; no network installs.
