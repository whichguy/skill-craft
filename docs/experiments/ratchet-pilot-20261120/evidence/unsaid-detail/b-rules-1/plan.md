# Plan: ticket assignment

## Approach

The change follows the existing layering (CONTRIBUTING.md): route handler validates and calls one store method; the
store checks state, applies, audits, enqueues the notification, saves. Parts touched:

- `src/tickets/validate.js`: new `assignment(body)` returning `string | null`. `onlyFields(body, ['assignee'])`; a
  missing key → InvalidError; `null` → null; otherwise the string rules of the existing `text()` helper (string type,
  trimmed, non-empty, control characters refused) with a max of 64 (a new `LIMITS.assignee`, same as requester).
  Whitespace-only, numbers, booleans, arrays, objects → `invalid`.
- `src/app.js`: `router.put('/tickets/:id/assignee', ...)` → `store.assign(params.id, validate.assignment(await body(req)), actorOf(req))`, 200 with the ticket.
  `Router.put` already exists. Other methods on that path already give the router's 404-with-hint.
- `src/store.js`: `assign(id, assignee, actor)`; `create` adds `assignee: null`; the constructor normalises
  `assignee ?? null` on every ticket it is handed (tests and the CLI build `TicketStore` straight from a state).
- `src/templates.js`: template `ticket.assigned` (subject `[T-0001] Assigned to you`, body naming ticket and title).
- `src/persistence.js`: `ticketRecord` gains `assignee: ticket.assignee ?? null`; `readTicket` validates it (null or
  non-empty string, else `fail`). `VERSION` stays 1: an old file has no field and loads as null (decision 8: "a field
  older files do not have takes its default").
- `src/tickets/query.js`: `parseListQuery` reads `assignee` (`params.has('assignee')`): `''` → `filters.assignee = null`
  (unassigned), otherwise the raw string (no trim, case-sensitive); never invalid. `matchesFilters` changes `some` →
  `every` (docs already promise "every"; the current `some` is a latent bug that only shows once two filters exist).
  `ticket[field] === value` then works for null as well, since tickets are normalised.
- `src/format.js` and `bin/tickets.js`: table column `ASSIGNEE` (placed before TITLE, so the unpadded last column stays
  the title) showing the name or `-`. `RAW_COLUMNS` untouched (C-20); `weekly-report.js` untouched. Optionally add an
  `assignee` line to `details()` (show). USAGE text unchanged (no `--assignee` option required).
- Docs: `docs/api.md` (endpoint, `assignee` on the ticket, filter table row, notification kind), `README.md` (command
  line example), `CHANGELOG.md` + `package.json` version bump to 1.5.0 (CONTRIBUTING "Releases"). A decision record
  is not needed.
- Tests: new files only (existing test files are not edited): `test/assignment.test.js` (HTTP + store),
  `test/assignment-persistence.test.js` or in the same file, `test/assignee-filter.test.js`, CLI listing test.

## Decisions

1. **One store method `assign`, one audit action pair**: `ticket.assigned` for an assign or reassign,
   `ticket.unassigned` for a null. Changes: `{ assignee: { from, to } }`. Reuses `apply()` so no-op = no audit, no
   `updated` change, no effects. Rejected: reusing `update()`/PATCH (PATCH must keep refusing `assignee`, C-21; and
   `update` only blocks closed, not resolved).
2. **Status check precedes the no-op check** (C-4 Open): in `assign`, `if (!isActive(ticket.status)) throw ConflictError`
   first, so a no-op on resolved/closed is 409. Rejected: 200 for no-ops, because the request says only open and
   in-progress tickets can be assigned or unassigned. `isActive` already exists in states.js.
3. **Order of errors**: body validation (400) runs in the handler before the store looks up the ticket (404/409). Not
   relied on by checks (C-5 Open); it is the pattern of PATCH.
4. **Name rules** (C-3 Open): trim like other text fields, max 64 characters, no control characters, stored trimmed.
   A name of 1–64 printable chars without surrounding space is stored as given, as required. Rejected: also forbidding
   `@` etc.; the request does not say.
5. **Notification kind `ticket.assigned`**, `to` = the agent's name, `data: { title }`, key
   `ticket.assigned:<ticket>:<agent>` (C-11): the default key `type:ticket` would let a pending notification to dana
   swallow the one to lee. With the agent in the key, re-assigning back to dana while hers is still pending is absorbed
   (required by C-11). `store.notify` already takes a `key` parameter. Rejected: a per-assignment counter in the key
   (would queue duplicates to the same agent).
6. **No notification on unassign or to the requester** (C-12, C-13): the effects callback runs `notify` only when `to !== null`.
7. **Unassigned filter is stored as `null` internally**, `''` only at the URL boundary. Rejected: comparing `''` to
   tickets (needs special-casing in the matcher).
8. **`matchesFilters` `some`→`every`** is a deliberate change to behaviour covered by C-17; existing query tests use a
   single filter and stay green.
9. **Table column position**: before TITLE. Placeholder `-`. Header `ASSIGNEE`.
10. **Data file version stays 1**; `assignee` is written as `null` explicitly (JSON drops `undefined`), so every
   saved ticket carries the key.

## Nuances

- **Persistence silently drops fields (C-9, U-5)**: `ticketRecord` is both the save and the load whitelist. Forget it
  and assignments vanish at the next restart/CLI read, while in-memory tests pass. Add the field there with `?? null`;
  `readTicket` runs `ticketRecord` over old records, where the field is `undefined`, so the `?? null` is what gives old
  files `null`. Validate after defaulting.
- **Old data in memory**: `TicketStore` copies tickets from a state it is given; normalise `assignee ?? null`, or old
  tickets would serialise without the key / fail `=== null` filter matching (C-8, C-16).
- **`matchesFilters` uses `some`** (C-17): with `status` + `assignee` it would list tickets matching either. Fix to
  `every`. Also keep `value !== undefined` skipping, but `null` is a real filter value, not skipped.
- **Empty `assignee=` vs absent** (C-16): use `params.has`, not truthiness. `assignee=%20` (space) is a filter for
  the name " ", matches nothing; not an error.
- **Dedup key** (C-11): see Decision 5. Test with worker off: dana, lee → two pending; back to dana → still two
  pending (dana's absorbed); then run the worker and assign to dana again → new event (key free after sent).
- **No-op and `updated` (C-6/C-7)**: `apply()` with empty changes returns early, but only if `changes` is built by
  comparing `ticket.assignee !== assignee`. Compare after normalisation, trimmed value.
- **Clock**: tests use `manualClock`; `updated` only differs if the clock is advanced. Tests proving "`updated`
  unchanged" must advance the clock between the creation and the no-op, and proving "`updated` becomes change time"
  must too.
- **Template required**: an unknown type gets retried and ends `dead` (C-10). The template must read only `event.ticket`
  and `event.data.title`. A name that is not an e-mail is fine for `NOTIFY_FILE`/memory notifier (Open in C-10).
- **Transitions keep the assignee (C-21)**: `transition` only changes status; do not touch assignee. Reopen keeps it.
  A resolved ticket cannot be reassigned (409) until reopened.
- **PATCH still refuses `assignee`** (unknown field) and `POST /tickets` too: do not add `assignee` to their
  `onlyFields`.
- **Audit entry for created ticket**: do not add `assignee` to `CREATED_FIELDS` (would add a change to existing audit
  output; existing tests may check it).
- **Persistence tests of existing suite** compare `loaded.audit`/`outbox`; ticket record gains a field which any test
  doing deep equality of a ticket from a fresh store must tolerate — run the existing suite early to see.
- **CLI `describeChanges`**: for from=null prints `assignee dana`; unassign prints `assignee dana -> null`. Acceptable.
  Table rows must not contain tabs/newlines; names are checked for control characters on entry. Hand-edited files:
  `readTicket` should refuse a non-string/empty assignee.
- **Raw output**: leave `RAW_COLUMNS` alone; adding a fifth column is optional and risky — do not.
- **Body edge cases**: `{}` → 400 (missing), `{"assignee":"a","x":1}` → 400, JSON array/`null` body → 400 by `readJson`.
  Use `Object.hasOwn`/`'assignee' in body`, so `{"assignee": undefined}` can't occur anyway (JSON).
- **Concurrency**: the store is synchronous; no locking needed (C-23).
- **Paging with filter** (C-18): `list()` filters before paginating and the cursor is only an id, so filters work
  unchanged; test with `limit=1`.

## Build order

1. Run `npm test` for a baseline.
2. `query.js`: `every`, `assignee` filter; run existing query tests. 
3. `persistence.js`: field in record, default and validation; run persistence tests; add a hand-made old-format file check.
4. `store.js`: normalise, `create`, `assign`; `templates.js`: template.
5. `validate.js` + `app.js` route; try with a real server on a free port (port 0) and curl.
6. `format.js`/`bin/tickets.js` column; run the CLI on a data file, run `weekly-report.js --json` before/after to compare.
7. Write the new test files; then docs, CHANGELOG, version. Run full `npm test`.

## How we will know

- **U-1**: PUT dana on open and in-progress tickets → 200, `assignee: "dana"`; GET agrees; `GET /admin/outbox` has one
  pending `ticket.assigned` to `dana` for the ticket; start with the worker on (interval small, NOTIFY_FILE) and see it
  `sent` and one file line with subject and body naming the ticket. Reassign replaces; audit has from/to.
- **U-2**: PUT null → 200 null; no outbox event; audit entry; a second null → 200, no audit entry, same `updated`.
- **U-3**: tickets with mixed assignees/status/priority; `?assignee=dana`, `?assignee=`, `?assignee=nobody` (empty
  page, 200), combinations with `status`/`priority` (must be AND), `limit=1` paging with cursors, no repeats or gaps.
- **U-4**: data file with assigned and unassigned tickets: `list` table has the name on each ticket's row; `list --raw`
  columns 1–4 unchanged; `weekly-report --json` counts equal before the change.
- **U-5**: existing suite unmodified passes; old-format data file (no `assignee`) loads with null; assign, restart with
  `DATA_FILE`, same `assignee`; PATCH with `assignee` still 400.
- **Must not forget in tests**: 400 variants (empty, whitespace, number, boolean, array, object, missing, extra field,
  non-object body) leave the ticket unchanged; 404; 409 on resolved/closed for assign, unassign and no-ops, with
  `assignee`/`updated` unchanged; transition keeps assignee; no-op leaves audit and outbox untouched; C-11 dedup; no
  requester notification; worker-off keeps `pending`; `assignee` present on POST/GET/list/PATCH/transition responses;
  AND filtering; advance the clock when asserting `updated`; clean up servers (use `withService`); no dependency added.

A second full pass over spec, code and this plan found nothing further that changes the build; no clauses were added to the spec.
