# Plan: ticket assignment

## Approach

The change follows the layering CONTRIBUTING.md already fixes: handler validates → one store method changes, audits,
notifies, saves. Parts touched:

- `src/tickets/validate.js`: new `assignment(body)` → returns the agent name or `null`.
- `src/store.js`: new `assign(id, assignee, actor)`; `create` gives new tickets `assignee: null`; the constructor
  normalises loaded tickets (`assignee: ticket.assignee ?? null`).
- `src/app.js`: `router.put('/tickets/:id/assignee', ...)` (the router already has `put`; nothing in `http.js`/`server.js`
  limits methods).
- `src/templates.js`: template `ticket.assigned`.
- `src/persistence.js`: `ticketRecord` keeps `assignee` (as `ticket.assignee ?? null`); `readTicket` checks it is null or a
  non-empty string of at most 64 characters. Version stays 1 (an absent field loads as null, decision 8).
- `src/tickets/query.js`: `assignee` filter in `parseListQuery`; `matchesFilters` changes from `some` to `every`.
- `src/format.js`: an ASSIGNEE column in `TABLE_COLUMNS`; `RAW_COLUMNS` untouched; `details` shows an `assignee` line.
- Docs: `docs/api.md` (ticket field, endpoint, filter, audit action list, notification), `README.md` (CLI), `CHANGELOG.md`
  and `package.json` to 1.5.0 (CONTRIBUTING "Releases"). No new decision record needed.
- New tests under `test/`; existing test files are not edited.

The ticket object becomes `{id,title,priority,requester,status,created,updated,assignee}`. Data: `assignee` is `null` or a
trimmed string, kept in the ticket record, in the data file and in the audit `changes`.

## Decisions

1. **Reuse `text(body, 'assignee', 64)` for the name** (trim, non-empty, ≤64, no control characters), after handling
   `null` first. Resolves C-3's Open points the way `requester` already behaves; control characters would also break the
   tab-separated CLI. Rejected: a looser raw-string check.
2. **Validation shape** (C-4): `onlyFields(body, ['assignee'])`; then `Object.hasOwn(body,'assignee')` else InvalidError;
   `null` → null; anything not a string → InvalidError (via `text`'s "must be a string").
3. **Order of errors**: body validation (400) before the ticket lookup (404), as `PATCH` does; then status check (409);
   so a bad body on a closed ticket is 400.
4. **Status check before no-op check** (C-5 Open): resolved/closed always 409, even if the request repeats the current
   assignee or null. Simplest and consistent with "only open and in-progress tickets can be assigned or unassigned".
   Rejected: 200 no-op on closed tickets.
5. **Active test** uses `isActive` from `src/tickets/states.js` (already exported, previously unused).
6. **Audit**: one action `ticket.assigned` for both assign and unassign, `changes: { assignee: {from, to} }`; goes through
   the existing `apply()`, which already gives the no-op behaviour (no audit, `updated` kept, no effects, no save).
   Rejected: separate `ticket.unassigned` (more strings for no benefit).
7. **Notification**: type `ticket.assigned`, `to` = the agent's name as stored, key
   `ticket.assigned:<ticketId>:<agent>` (C-12). Enqueued only inside `apply`'s `effects` callback, only when the new
   assignee is non-null. Data `{ title }` like the others. Template: subject `[T-0001] Assigned to you`, body names the
   ticket and title. Rejected: the default key `type:ticket` (would drop the new agent's notification while another
   is pending). Add `assignee`-free data only; the notifier needs no change.
8. **`list --raw` is not extended** (C-19 Open): keeps four columns. Weekly report untouched. The table gets an
   `ASSIGNEE` column after `PRIORITY`, unassigned shown as `-`.
9. **Filter representation**: `filters.assignee` is the string, or `null` for an empty `assignee=`. `matchesFilters`
   compares `ticket[field] === value`, so null matches unassigned tickets (all tickets are normalised to null, never
   undefined). No validation of the value; exact, case-sensitive, untrimmed match.
10. **`matchesFilters` → `every`** (C-16). The existing function ignores `undefined` filter values; keep that.
11. **No `--assignee` option on the CLI** (not requested), so `parseArgs` is unchanged.
12. **Assignee kept across resolve/close/reopen** (C-8 Open): no clearing code.

## Nuances

- **C-16 latent bug**: `matchesFilters` uses `some`. Today single-filter tests pass either way; with the `assignee`
  filter combined with `status` it would be wrong. Change to `every` and add a combined-filter test (status+priority too).
- **Existing store test** (`test/store.test.js:37`) deep-equals the `ticket.created` audit entry: do NOT add `assignee` to
  `CREATED_FIELDS`, and do not audit the null initial assignee. The same test at line 22 picks named fields, so the extra
  `assignee` key does not break it.
- **Persistence (C-9)**: `ticketRecord` is used for saving and for loading, so adding the field there covers both; old
  files lack it, so `?? null` is needed in `ticketRecord` (a bare `ticket.assignee` yields `undefined`, which JSON drops
  and the filter would not match `null`). Also normalise in the `TicketStore` constructor, since tests and the CLI build
  stores from states directly. Validate in `readTicket` only when not null.
- **`updated` and no-op** (C-6, C-7): rely on `apply()`; do not set `updated` or call `save()` yourself. For
  unassign-on-unassigned, `ticket.assignee` null vs `null` → empty changes → no-op. Compare with `!==` on the trimmed value.
- **Notification only on change** (C-13): enqueue inside `effects`, never before the changes check; unassign enqueues
  nothing; refused requests throw before anything.
- **Dedup across the whole state**: key is dedup'd only while pending; once sent, re-assigning dana→sam→dana notifies
  dana again (a real change). That is intended.
- **`ticket` in `notify`** is read after mutation: `data.title` is unaffected by assignment.
- **PATCH and POST** still refuse `assignee` (C-20): `ticketPatch`/`newTicket` `onlyFields` lists stay unchanged. Confirm in
  a test.
- **Copies**: `store.get`/`list` return `{...ticket}` copies, so the new field flows out automatically; `snapshot` also.
- **Empty query value**: `URLSearchParams.has('assignee')` is true for `?assignee=`, and `get` returns `''`; map `''` to
  `null`. `?assignee` (no `=`) is also `''` → unassigned. A repeated `assignee` parameter: `get` takes the first;
  accept it.
- **Paging with filters** (C-14): `paginate` takes `after` as an id, independent of the filter; verify `next`/`cursor`
  work with `assignee=` by a test with `limit=1`.
- **URL-encoding**: tests must percent-encode agent names with special characters in the query (`encodeURIComponent`).
- **CLI table**: names have no tabs/newlines (control chars refused), so the table stays aligned. `format.table` coerces
  with `String(...)`; the `value` function must return `'-'` for null (otherwise it prints "null"). Check `no tickets`
  still prints for an empty list. Old data files in the CLI store: normalisation in the constructor gives null.
- **CLI and `RAW_COLUMNS`**: `rawLine` maps only `RAW_COLUMNS`; leave it, and run `scripts/weekly-report.js` against
  a data file in a test to prove unchanged counts.
- **Persistence validation versus names**: validating `assignee` ≤64 on load matches what the API enforces; do not be
  stricter (no control-char check on load, to avoid refusing a file the service itself wrote).
- **Worker/outbox visibility**: tests run with the worker off (`workerIntervalMs: 0`); read `/admin/outbox` pending. For
  delivery, call `service` worker tick as `test/worker.test.js`/`api.test.js` do, or use `NOTIFY_FILE` and read the line.
- **The `Open:` points** are handled by decisions 1, 4, 8, 12 and the audit action name (6). Tests check only what the
  clauses state: `changes`, recipient and ticket, name in the row, no 409/200 assertion for repeated values on closed
  tickets.

## Build order

1. `query.js`: `every` plus the `assignee` filter; run the existing suite (query tests).
2. `store.js` + `persistence.js`: normalise, `ticketRecord`, `readTicket`, `create` sets null, `assign`; run the suite
   (the store and persistence tests must stay green).
3. `validate.js` `assignment` and `templates.js` `ticket.assigned`.
4. `app.js` route; smoke with a server on port 0 (curl PUT, GET, filter, audit, outbox, restart with a `DATA_FILE`).
5. `format.js` (column, `details` line) and check `bin/tickets.js list` and `npm run report:weekly` on a data file.
6. Tests: `test/assign.test.js` (store + API: C-1 to C-13, C-20), `test/assignee-filter.test.js` (C-14 to C-17 and
   `matchesFilters`), additions to the CLI/format tests in a new file `test/assignee-cli.test.js` (C-18, C-19), a
   persistence test on an old-format file (C-9) and the templates render in the new files.
7. Docs, CHANGELOG, version bump; run `npm test` (all existing plus new) and report the summary.

## How we will know

- **U-1**: PUT `{"assignee":"dana"}` on an open and on an in-progress ticket: 200, `assignee: "dana"`, GET agrees,
  `/admin/outbox` pending holds one `ticket.assigned` event to `dana` for that ticket, `/tickets/:id/audit` has the change;
  after a worker tick the notifier's `delivered` (or `NOTIFY_FILE`) has it. Forget not: 64 characters pass, 65 and `""`
  → 400 `invalid` with nothing changed; bad bodies (missing, `5`, `true`, `{}`, extra field) → 400; resolved/closed
  → 409 with `assignee` and `updated` unchanged; unknown id → 404; same agent twice → no new audit, `updated`, or
  outbox event; dana then sam before delivery → two events.
- **U-2**: PUT null → 200 with null; null on an unassigned ticket → 200 no-op; no notification; 409 on closed.
- **U-3**: tickets for dana, sam and nobody across statuses and priorities: `?assignee=dana`, `?assignee=`,
  `?assignee=nobody` (empty list, 200), `?assignee=dana&status=open`, `?status=open&priority=urgent`, `?assignee=&status=in_progress`,
  and paging with `limit=1`.
- **U-4**: build a data file (a `DATA_FILE` store, or `TicketStore` + persistence), run `main(['--data',f,'list'])` with
  captured `out`, check the assigned row contains the name and the empty-list output is `no tickets`; run `list --raw`
  and check the tab columns 1–4 are unchanged; run `scripts/weekly-report.js --json` and compare the counts.
- **U-5**: the full existing suite unmodified; PATCH/POST with `assignee` → 400; transitions and PATCH keep the
  assignee; the `assignee` key appears in create/get/list/patch/transition responses (null for new); a hand-written old
  data file without `assignee` starts the service and shows null; assign, stop, restart on the same `DATA_FILE`,
  and the assignee persists.
- A test of this change must not forget: the combined-filter case (the `some` bug), the old-format file, the
  restart, the pending-key behaviour for a different agent, null and no-op sending no notification, `updated`
  unchanged on refusal, and that tests pass whichever `Open:` answer was taken.
