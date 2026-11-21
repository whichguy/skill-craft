# Plan: ticket assignment

## Approach

The service is layered: `src/app.js` (route + validate + one store call) → `src/tickets/validate.js` → `src/store.js` (change +
audit + outbox + save in one step) → `src/persistence.js` (data file), with `src/templates.js` for notification text,
`src/tickets/query.js` for the listing filters and `src/format.js` + `bin/tickets.js` for the command line. The change
follows that path and adds nothing new structurally:

- **Ticket data**: a new field `assignee` (string or null) on the ticket object. `create()` sets `assignee: null`. The store
  constructor normalises loaded tickets (`assignee ?? null`) so a state without the field is safe too. `CREATED_FIELDS`
  stays as is (the creation audit entry must still list exactly title, priority, requester, status: C-9).
- **Route**: `router.put('/tickets/:id/assignee', ...)` in app.js (the Router already has `put`). Handler:
  `validate.assignment(await body(req))` → `store.assign(params.id, agent, actorOf(req))` → 200 with the ticket.
- **Validation** (`validate.js`): `assignment(body)`: `onlyFields(body, ['assignee'])`; `assignee` must be present
  (`'assignee' in body`, own key), be `null` (returns null) or a string run through the existing `text()` helper with a new
  `LIMITS.assignee = 64`. Anything else is `InvalidError`.
- **Store** (`store.js`): `assign(id, agent, actor)`: `find` (404) → status must be open/in_progress via `isActive`
  (else `ConflictError`, 409) → compute `changes` (`{assignee:{from,to}}` only if different) → `this.apply(...)` with an
  effect that notifies only when `agent !== null`. `apply()` already does "no change ⇒ nothing happens, returns copy".
- **Notification**: template `ticket.assigned` in templates.js (subject and body name the ticket id and title); outbox event
  `type: 'ticket.assigned'`, `to: agent`, key `ticket.assigned:<ticket>:<agent>`.
- **Persistence**: `ticketRecord` must include `assignee` (it is the one list of saved fields, used for both save and load);
  `readTicket` normalises missing to null and validates string-non-empty-or-null.
- **Listing**: `parseListQuery` reads `assignee` (empty value → filter `null`); `matchesFilters` is corrected to `every`.
- **Command line**: an ASSIGNEE column in `TABLE_COLUMNS` (placeholder `-`), `show` gains an assignee line; `RAW_COLUMNS` untouched.
- **Docs/housekeeping** (CONTRIBUTING asks for it): docs/api.md (ticket field, endpoint, filter, audit actions, notification),
  README (command line mention), CHANGELOG 1.5.0 + `package.json` version bump, operations.md only if it lists notification types.
  No decision record is required (no new format/protocol), but the key-dedup choice is worth one line in the CHANGELOG or code comment.

## Decisions

1. **Filter for "unassigned" is `null` inside `filters`, not `''`.** Tickets store null, so the generic `ticket[field] === value`
   in `matchesFilters` works unchanged; `matchesFilters` already skips only `undefined`. Rejected: a special-case branch on `''`.
   Keep `parseListQuery('')` returning `filters: {}` exactly (existing test deep-equals it): only add the key when `params.has('assignee')`.
2. **`matchesFilters` becomes `every`** (C-16). The present `some` is a latent bug (docs/api.md already says "every"); existing tests
   use single filters only, so nothing existing breaks. Fix in place and add a multi-filter unit test to a *new* file (existing test files
   stay unmodified: "pass as they are" — add new tests in new files, e.g. `test/assignment.test.js`, `test/assignment-cli.test.js`; do not edit test/*.test.js that exist).
3. **Outbox key includes the agent**: `ticket.assigned:T-0001:dana`. The default key (type+ticket) would make "assign to eve" be
   swallowed by a still-pending "assign to dana" notification (C-12) — the eve notification would never exist. Rejected: default key;
   rejected: no key (would break the outbox's dedup convention). Agent names are used raw in the key (may contain `:`; harmless, the key is only compared for equality).
4. **Agent name validation reuses `text()`** (trim, non-empty, ≤64, no control chars). This settles C-3's Open point in the way matching
   `requester`. The stored value is the trimmed one, so "exact comparison" is on the stored/trimmed value. Tests must use plain names only.
   Rejected: a bespoke rule that keeps whitespace. Length is `String.length` like other fields.
5. **Validation before lookup**: the handler validates the body (400) before the store checks existence (404) and state (409), as
   PATCH/transition do. So invalid-body-on-resolved ⇒ 400 and invalid-body-on-unknown-id ⇒ 400 (C-5 Open: this is the "reasonable answer"; report it).
6. **State check before the no-change check**: a resolved/closed ticket gets 409 even for a no-op (C-5). Order in `assign`: find → isActive → diff.
   Do not reuse `update()`'s `isFinal` check (resolved is still patchable, C-23).
7. **Audit action names**: `ticket.assigned` for setting/replacing, `ticket.unassigned` for null. Changes `{assignee:{from,to}}` (C-9). Add them to the docs' "Actions so far".
8. **Notify only on non-null `to`**, inside the `apply()` effects callback so the outbox write is in the same step as the audit entry and the save (C-10/C-11). Notification `data` carries `{ title }` (what `notify()` already puts) — the template needs only ticket id + title. Recipient `to` is the agent's name as given (no address book exists).
9. **`list --raw` unchanged** (C-18 Open: weekly-report reads by position; adding a 5th column is permitted but unnecessary risk). The table gets the column; put ASSIGNEE after PRIORITY and keep TITLE last (it is the unpadded, free-width column). Placeholder `-`.
10. **Persistence tolerance**: old files have no `assignee` → null. Don't bump the file `VERSION` (version check would refuse old files, and the change is backward-readable). Rejected: version 2 + migration.
11. **Do not change `PATCH`**: `ticketPatch` keeps `onlyFields(['title','priority'])`, so `assignee` there stays 400 (C-19).

## Nuances

- **Persistence silently drops the field (C-13).** `ticketRecord` in persistence.js is the whitelist for save *and* load; forgetting it passes every in-memory test and loses
  assignments on restart. Also `toDocument` gets the store's `snapshot()` (spreads tickets), so only `ticketRecord` needs the change. Test with a real `DATA_FILE`, restart, and an old-format file (tickets without the key).
- **`readTicket` builds from `ticketRecord(record)`**, so a missing key becomes `undefined` — normalise to null *after* that call, and validate `typeof string && !== ''` when not null (C-24).
- **Dedup key (C-12)** as in Decision 3. Also verify `T-0001→dana` + `T-0002→dana` gives two pending events (different tickets).
- **No-op detection (C-7)**: compare to the stored value, including null→null on an active ticket (200, `updated` unchanged, no audit, no outbox). Check that `apply()` returns the unchanged ticket and does not call `save()`.
- **Validation of presence**: `{}` and `{"assignee": undefined}` ⇒ 400; `JSON.parse` never gives undefined, so use `Object.hasOwn(body,'assignee')`. `{"assignee":"dana","x":1}` ⇒ 400 via `onlyFields`. Arrays/numbers/booleans/objects ⇒ 400. Non-object bodies are refused by `readJson` already (also for a `null` body).
- **Order of checks vs. empty body**: PUT with no body ⇒ 400 from `readJson`; don't read `req` after an early throw (the handler awaits the body first, as others do).
- **`matchesFilters` `every` with `undefined`**: keep the `value !== undefined` skip. Verify that `given.length === 0 ⇒ true` is still right and that `every` over the filtered list handles the null filter (`null !== undefined`, kept).
- **Query string `assignee=`**: `params.has('assignee')` true, `get` ⇒ `''` ⇒ filter null. `assignee` given twice: `get` returns the first (accepted). Do not trim or validate the filter value (C-22: unknown name ⇒ empty list, not 400). `status=` must stay 400 (C-22): do not generalise "empty means no filter" to the other filters.
- **Cursor paging with the filter (C-14)**: the filter is applied before `paginate`; nothing else changes. The cursor of one filtered listing is just a ticket id, so paging works; test limit=1 across several of dana's tickets.
- **Templates**: a type without a template goes dead after 5 attempts (C-10). Add the template *before* testing delivery and test `worker.tick()` / NOTIFY_FILE with a real worker run (see test/worker.test.js, test/service.test.js for how to run the worker with a manual clock).
- **Outbox `enqueue` requires non-empty strings for `to`**: guaranteed by validation; assign never calls `notify` with null.
- **Reassignment from dana to eve**: notification to eve only (C-11); the audit shows `from:'dana'`.
- **Resolved/closed tickets keep their assignee** (C-8): transitions and PATCH only touch their own fields through `apply()` (it assigns only the keys in `changes`), so no code is needed — but test it (assign, transition to resolved, read; reopen, read).
- **Ticket shape in tests that exist**: `test/store.test.js` destructures named fields, `test/api.test.js` compares the same object read two ways, persistence tests map fields — adding `assignee` to the ticket breaks none of them. Run the complete existing suite untouched before and after.
- **`X-Actor` (C-21)**: `actorOf(req)` throws 400 for a long header; call it where the others do, so it is validated for this route too. It is evaluated after body validation in other handlers' argument order; for a request with both errors either 400 is fine.
- **Router**: other methods at `/tickets/:id/assignee` fall to the 404 "does not answer" message — now it answers `PUT`; no code, just don't add a `GET`.
- **CLI**: `table()` pads by max width and the last column is not padded; with a new column before TITLE, assigned names of up to 64 chars widen the table — fine. `String(column.value(ticket))`: with a `null` assignee it would print "null"; the column value function must map null to the placeholder. `show`: add `assignee` to `details()` fields (`ticket.assignee ?? '-'`). `describeChanges` prints `assignee dana` for null→dana and `assignee dana -> null` for unassign — acceptable.
- **CLI reads state without persistence via `new TicketStore({state})`** — the constructor normalisation covers old files; and `fromDocument` (loader) too.
- **Test for CLI**: run `main()` directly with a captured `out` (exported), or spawn `node bin/tickets.js --data FILE list`; build the data file by running a store with `createPersistence(file)` in the test, no server needed. Also run `scripts/weekly-report.js --json` over a file with assignments to confirm the counts.
- **Tests must not rely on Open choices**: only plain names, the bounds 1/64/65 and `""`, a valid body on resolved/closed for 409, and an open ticket for 400s; no checks on audit `action`, on whether `list --raw` has extra columns, on the CLI header or placeholder (check the assigned line contains the name; an unassigned line has no agent name), nor on dana→null→dana dedup.
- **Time**: tests use `manualClock` (src/clock.js) so `updated` equality / change can be asserted by advancing the clock; a changed assignment must set `updated` to the new time (C-1), a no-op must not.
- **Ports/processes**: tests use `withService` (port 0, worker off). For worker-run tests follow test/service.test.js. Nothing started outside of tests.

## Build order

1. Run the existing suite (`npm test`) to record the baseline.
2. `src/tickets/query.js`: `every` fix + `assignee` filter; then `store.create`/constructor `assignee: null`; run the suite (query/store tests still green).
3. `src/persistence.js`: `ticketRecord` + `readTicket` normalise/validate; run persistence tests; hand-check an old-format file.
4. `src/templates.js`: `ticket.assigned`.
5. `src/tickets/validate.js`: `LIMITS.assignee`, `assignment()`.
6. `src/store.js`: `assign()`; `src/app.js`: the PUT route. Try by hand on a port-0 service, or go straight to tests.
7. `src/format.js` + `bin/tickets.js` (usage text unchanged; no new flags): column, `show` line.
8. New tests in new files (`test/assignment.test.js` for API/store/validate/query/template/persistence-restart; `test/assignment-cli.test.js` for the CLI and weekly report). Do not touch existing test files.
9. Docs: api.md, README, CHANGELOG 1.5.0, package.json version. Then full `npm test`.

## How we will know

- **U-1 / C-1, C-9, C-10, C-21**: PUT dana on an open ticket and an in_progress ticket → 200, `assignee`, `updated`; GET shows it; audit has the entry with actor from `X-Actor` / `system`; `/admin/outbox` pending has `to: dana`, `ticket`; run the worker with `NOTIFY_FILE` → status sent, one line with `to` and ticket id in its text. Reassign replaces.
- **U-2 / C-2**: null on an assigned ticket → null, audit from/to, no notification.
- **U-3 / C-3–C-7, C-11, C-12**: repeat → same `updated`, same audit count, same outbox count; `""`, 65 chars, number, array, missing, extra field, 400; resolved and closed → 409 for both name and null (and for null on unassigned); T-9999 → 404; error bodies have the envelope; after each refusal the ticket, audit and outbox are unchanged. dana→eve gives a pending eve event; T-0001/T-0002 both dana gives two. 1-char and exactly-64-char names accepted.
- **U-4 / C-14–C-16, C-22**: the T-0001..T-0003 scenario of C-16; `assignee=` lists only unassigned; unknown agent → empty `{items:[],next:null}`; limit/cursor paging over a filtered set; `status=open&priority=urgent` needs both; `status=` still 400; `offset=` ignored.
- **U-5 / C-17, C-18, C-25**: CLI against a data file with an assigned and an unassigned ticket; assigned line contains the name; unassigned has none; `--raw` columns 1–4 unchanged; `weekly-report.js --json` counts equal; `show` still works.
- **U-6 / C-10, C-11**: as U-1 plus no notification for unassign/no-op/refusals.
- **C-8, C-13, C-24**: every response shape has `assignee`; null for new tickets and old-format files; restart on the same `DATA_FILE` keeps it; a data file with `assignee: 5` or `""` is refused; resolved/reopen/PATCH keep the assignee.
- **C-19, C-20, C-23**: the entire existing suite unmodified and green, PATCH with `assignee` is still 400, PATCH on resolved still 200, created/resolved notifications unchanged, `npm test` runs the new files.
- **Not to forget in tests**: restart persistence with a real file, a real worker delivery (not just the outbox), the no-op producing no audit/outbox (compare counts, not just status), and that refused requests change nothing; both active statuses; using only the plain-name cases from the Open clauses.

## Preserved behaviour

- Error envelope and 400/404/409 split, no hand-written error responses: `src/errors.js`, `docs/api.md` Errors, CONTRIBUTING.md. (C-4, C-5, C-6, C-19)
- Changes only through the store; a change that changes nothing makes no audit entry, no notification and leaves `updated`: `src/store.js` `apply`, CONTRIBUTING.md, decision 7. (C-7)
- Creation audit entry lists exactly title, priority, requester, status: `src/store.js` `CREATED_FIELDS`, `test/store.test.js`. (C-9)
- Notifications only through the outbox, with templates; created and resolved notifications and their keys: `src/store.js`, `src/templates.js`, `test/store.test.js`. (C-10, C-19)
- Unknown body fields refused; PATCH takes only title and priority (so `assignee` there stays 400): `src/tickets/validate.js`, `docs/api.md`. (C-19)
- `PATCH` allowed on a resolved ticket, refused only on closed; lifecycle transitions; reopen: `src/store.js`, `src/tickets/states.js`. (C-23, added)
- Listing: id order, cursor paging, `status`/`priority` values validated (empty `status=` is 400), unknown parameters ignored, `parseListQuery('')` equals `{filters:{},limit:20,after:null}`: `test/query.test.js`, `src/tickets/query.js`. (C-22, added)
- The one existing divergence: `matchesFilters` uses `some` while `docs/api.md` says a ticket must match every filter — the spec (C-16) requires the documented behaviour; the existing tests do not depend on `some`.
- Data file: version 1, atomic write, strict load checks, old files still load: `src/persistence.js`, decision 8. (C-13, C-24, added)
- `X-Actor` rules: `src/http.js`. (C-21, added)
- Command line: read-only, usage, exit codes 0/1/2, `list --raw` columns 1–4 id/status/priority/title in place (the weekly report reads by position), `show`: `bin/tickets.js`, `src/format.js`, `README.md`, `scripts/weekly-report.js`. (C-18, C-25, added)
- Existing tests under `test/` pass unmodified; new tests go in new files: `package.json` `npm test` = `node --test`. (C-19, C-20)
- No dependencies, CommonJS with named exports: CONTRIBUTING.md.
- Not settled by what is here: whether `list --raw` may gain a trailing assignee column (README only requires positions 1–4 to stay; the plan leaves it out); whether the version bump / CHANGELOG are expected (CONTRIBUTING says releases bump them, so the plan does it).
