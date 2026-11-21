# Plan: ticket assignment

Covers U-1..U-6 and C-1..C-34 of `ratchet/spec.md`. No new dependencies; CommonJS, `'use strict'`, named exports
(CONTRIBUTING.md). Existing test files are never edited.

## Approach

A ticket gains one field, `assignee` (string or `null`). It travels through the layers the same way `priority` does,
with one new store method and one new notification type.

| Part | Change |
|---|---|
| `src/tickets/validate.js` | new `assignment(body)`: `onlyFields(body, ['assignee'])`, field must be present (own property), then `null` or a valid agent name; returns the assignee (string or null). |
| `src/app.js` | `router.put('/tickets/:id/assignee', ...)`: `validate.assignment(await body(req))` then `store.assign(params.id, assignee, actorOf(req))`; answer `{ status: 200, body: ticket }`. The router already has `put`. |
| `src/store.js` | `create()` sets `assignee: null`; constructor normalizes loaded tickets (`assignee: t.assignee ?? null`); new `assign(id, assignee, actor)`; `list()` unchanged apart from the filter semantics below. |
| `src/tickets/query.js` | `parseListQuery`: `params.has('assignee')` sets `filters.assignee = params.get('assignee') === '' ? null : value`. **`matchesFilters` must become AND** (see Nuances 1). |
| `src/templates.js` | add `'ticket.assigned'` template, otherwise the event goes dead (C-18). |
| `src/persistence.js` | `ticketRecord` adds `assignee`; `readTicket` accepts a missing or null assignee as `null` and validates a string (non-empty, no control characters, at most 64 characters). |
| `src/format.js` | `TABLE_COLUMNS` gains `ASSIGNEE`; `details()` shows the assignee line. |
| docs | `docs/api.md` (new endpoint, `assignee` field and filter, new notification), `README.md` (CLI table), `CHANGELOG.md` + `package.json` version bump to 1.5.0 (CONTRIBUTING "Releases"), an optional short decision record `docs/decisions/0009-...md` (the assignment notification key), added to the index in docs/decisions/README.md. |
| `test/` | new files only (see How we will know). |

Data: the ticket record is `{ id, title, priority, requester, status, created, updated, assignee }`. The data file stays
`version: 1`: the field is optional on read and always written, so old files load and new files remain readable by the
same code (no migration). The audit entry for a change is `{ assignee: { from, to } }`; the outbox event is
`{ key, type: 'ticket.assigned', to: <agent>, ticket, data: { title } }`.

## Decisions

1. **Filters combine with AND by fixing `matchesFilters` (`some` -> `every`).** Reason: C-25 and docs/api.md demand
   it; today's `some` is OR and is only invisible because no test combines two filters. Rejected: leave it and
   special-case `assignee` (would leave `status=open&priority=urgent` wrong, C-25 names it).
   Check `test/query.test.js` still passes: it tests single filters only, so it does.
2. **The "unassigned" filter is the value `null` in `filters`.** `assignee=` (present, empty) -> `null`;
   `assignee=dana` -> `'dana'`; absent -> key not set. `matchesFilters` compares `ticket.assignee === value` after the
   store has normalized undefined to `null`. Rejected: a separate `unassigned: true` flag (two ways to say one thing).
3. **`store.assign` order of checks:** find ticket (404) -> status not active (409) -> same value (return as is, no
   audit/notify) -> apply. Validation of the body (400) runs in the handler before the store, so a bad body on an
   unknown ticket is 400 (as PATCH does). Resolved/closed answers 409 even when the value equals the current one
   (C-8 Open: chosen the simple, uniform rule "only open and in-progress tickets can be assigned or unassigned";
   tests do not depend on it). Use `isActive` from `src/tickets/states.js`; do not hard-code the status list.
4. **Agent name validation:** a new function in `validate.js`, not `text()` (whose length check and error text are
   about a named field and which I do not want to alter). It must: be a string (else 400); **test the control-character
   regex (`CONTROL`, exported from or copied in `validate.js`) on the raw value before trimming** (C-5: `"dana\n"` and
   `"\tdana"` must be 400; `text()` checks after `trim()`, which would let a trailing newline through, so do not copy
   its order); then `trim()` it (C-3 Open: same as requester/title, so a space-only name is empty -> 400 and `" dana "`
   is stored as `dana`); refuse empty; refuse more than 64 characters. Count characters as code points
   (`[...name].length`) so "64 characters" is not 32 emoji; ASCII behaviour is identical. Length is checked after
   trimming. The loader checks a saved name strictly (it does not trim: a string, non-empty, at most 64 characters, no control
   character), throwing `DataFileError` through its `fail`, since a stored name never has edge spaces. Rejected: no
   trimming in the API (stored names with edge spaces would never match a filter typed without them).
5. **Audit action names:** `ticket.assigned` when the new value is a name (including a reassignment),
   `ticket.unassigned` when it is null. Tests do not check the name (C-15 Open). `changes` is exactly
   `{ assignee: { from, to } }`, built the way `update()` builds it, and applied through the existing `apply()` so
   audit, `updated`, effects and `save()` stay one step.
6. **Notification key `ticket.assigned:<ticket id>:<agent>`**, passed as the 5th argument of `notify`. Reason: the
   default key `type:ticket` would drop `sam`'s event while `dana`'s is pending (C-19). Including the agent keeps
   "dana then sam" two events, and the ticket id keeps two tickets for one agent two events (C-20). A ticket id
   contains no `:`, so the key is unambiguous. Known and accepted: dana -> sam -> dana before delivery dedups the third
   to dana's still-pending event (dana is still told once, and it is still pending). Rejected: a counter or the audit
   seq in the key (would double-notify an agent who is already about to be told).
7. **Effects only for a new name:** the `effects` callback passed to `apply` notifies only when `assignee !== null`
   (C-21). Nobody is notified on unassign, and never the previous assignee or the requester.
8. **Template wording:** subject `[T-0007] Assigned to you`, body `Ticket T-0007 "<title>" was assigned to you.` using
   `event.ticket` and `event.data.title` (the same `data` that `notify` already stores). Rejected: putting the agent
   name in `data` (it is `to`).
9. **CLI:** table gets an `ASSIGNEE` column inserted before `TITLE` (the last column is unpadded, so a long title stays
   last); an unassigned cell reads `-` (C-28 Open). `list --raw` is left at its four columns (C-29 Open): the weekly
   report reads by position and the safest way to keep it is not to touch the raw format. No `--assignee` CLI option
   (not requested). `show` gets an `assignee` line (`-` when none): harmless and useful.
10. **Persistence:** `ticketRecord` writes `assignee: ticket.assignee ?? null`; `readTicket` validates it with the
    same rules as the API's name (string, non-empty, at most 64, single line) or null/absent -> null. A hand-edited
    bad assignee fails loading with a `DataFileError` like other bad fields.
11. **Tests are new files:** `test/assign.test.js` (HTTP + store), `test/assign-notify.test.js` or the same file,
    `test/cli-assignee.test.js`. They use `withService`/`client` from `test/helpers.js` and `manualClock`. Never edit
    `helpers.js` (it is an existing test file); add any new helper locally in the new files.

## Nuances

1. **`matchesFilters` is OR today (C-25, C-27).** `given.some(...)` means `?status=open&assignee=dana` would list every
   open ticket and every dana ticket. Switch to `every`. Re-run `test/query.test.js` and `test/api.test.js`.
2. **Filter value `null` versus "not given" (C-22, C-23, C-24).** `matchesFilters` drops entries whose value is
   `undefined`; `null` must stay a real filter. Do not use a truthiness test anywhere (`if (filters.assignee)` would
   turn `assignee=` into "no filter"). Use `params.has('assignee')`, because `params.get` returns `''` for both `?assignee=`
   and `?assignee` (both mean unassigned) and `null` for absent.
3. **Old tickets have no `assignee` property (C-12).** In-memory: the store constructor's `{ ...ticket }` copy would leave
   it `undefined`, which `JSON.stringify` drops (so the ticket would not "show" `assignee`) and which `=== null` does not
   match (the `assignee=` listing would miss it). Normalize in both the persistence loader and the store constructor
   (the CLI builds `new TicketStore({ state })` from `load()`, and tests may pass a state directly).
4. **The data file only keeps fields `ticketRecord` names (C-13).** Forgetting to add `assignee` there loses every
   assignment on restart, silently, while all in-memory tests pass. Test with a real `DATA_FILE` and a second
   `createService`/`TicketStore.open` on the same file, and via `bin/tickets.js`.
5. **A same-value request must return before `apply` touches anything (C-9, C-10).** `apply` already returns early on empty
   `changes`, so build `changes` as `{}` when `ticket.assignee === assignee`, and do the 409 check **before** that
   (decision 3). Do not set `updated` or notify on the no-op; the no-op's answer is the unchanged ticket with 200.
6. **Reassignment notifies only the new agent, once per new assignment (C-17..C-21, C-19).** Check the key, and that
   the notify call is inside `effects` so a refused/no-op request enqueues nothing. The outbox key check
   (`pendingWithKey`) only dedups pending events; after `dana`'s event is sent, assigning her the same ticket again
   (after someone else) enqueues a fresh one, as intended.
7. **No template means dead (C-18).** The event type string in `notify` and the key in `TEMPLATES` must match exactly
   (`ticket.assigned`). Test with the worker on (`workerIntervalMs` small plus a manual `service.worker.tick()`, or
   call `tick()` with interval 0) and assert `sent` holds the event, `dead` is empty, and the notifier's delivered line
   names `T-0007` and is `to: 'dana'`. Because `render` throws only inside the worker, a missing template is invisible
   to tests that look only at `/admin/outbox` pending.
8. **`save()` happens once per change inside `apply`; no second save, no change outside the store (CONTRIBUTING).** The
   handler must not assign to the ticket, append audit entries, or call the notifier.
9. **Concurrency (C-16):** Node runs `store.assign` synchronously, and the body is read before it, so requests
   interleave only at body reads. Do not add an `await` between reading the ticket and applying (do not make `assign`
   async). The audit chain `from == previous to` then holds for free; test with `Promise.all` of several PUTs.
10. **Error classes and codes (C-3..C-8, C-33):** use `InvalidError` (400) for body problems, `ConflictError` (409) for
    state, `NotFoundError` (404) for an unknown id, from `src/errors.js`; never write a response by hand. Missing field
    -> 400, not `null` (use `Object.hasOwn(body, 'assignee')`; `body.assignee === undefined` is also fine because JSON
    cannot carry `undefined`). `onlyFields` runs first so `{"assignee":"dana","team":"x"}` is 400 (C-6). A body that is
    not an object is already rejected by `readJson` (C-33). `PATCH`/`POST` stay as they are, so `assignee` in those
    bodies is refused as an unknown field (C-34); do not add it to their allowed fields.
10b. **Control characters at the edges (C-5):** a test of C-5 must include a name whose control character is at the end
    or start (`"dana\n"`), and one inside (`"da\tna"`); the raw-value check in Decision 4 covers both. The tab/newline
    ban is what keeps `list --raw` one line per ticket, should a later change add the assignee there.
11. **Actor header (C-15):** `actorOf(req)` throws `InvalidError` for an `X-Actor` over 64 characters; call it in the
    handler before the store so the ticket is not changed on that error.
12. **Moving and editing keep the assignee (C-14):** `transition` and `update` call `apply` with their own `changes`, so
    the assignee is untouched; just do not "clear on resolve". A resolved ticket keeps its agent, and a reopened one
    shows it again. The CLI and listing show it for every status (C-22/C-23 include resolved/closed).
13. **Existing outputs that deep-compare tickets:** test/api.test.js line 21 compares `GET` to the `POST` body (both
    gain `assignee: null`, equal); store/persistence tests pick fields. `list()` and `get()` return copies, so
    `assignee` is copied too. Nothing existing breaks by the new key, but check by running the suite after the first
    store edit.
14. **CLI table layout (C-28, C-29):** `table()` computes widths from `String(column.value(ticket))`, so the cell function must
    return `'-'` for null (not `null`, which would print "null"). Keep the weekly report working: `RAW_COLUMNS`
    unchanged; run `scripts/weekly-report.js --json` before and after on a data file with assigned tickets and compare.
15. **Pagination (C-26):** `paginate` runs after filtering, with `compareIds`, so nothing new is needed; test with a
    page size smaller than the match count and with other agents' tickets interleaved (so a page has to skip tickets).
    Cursors stay valid with the same filters only; do not put the filter in the cursor.
16. **Names with special characters:** a name like `dana smith`, `jose@x.com` or `Zoë` is valid and compared exactly
    (case-sensitive: `Dana` is not `dana`). In URLs the client percent-encodes; `URLSearchParams` decodes `+` as space.
    A 64-character name's event `to` is long but valid for the outbox (non-empty string).
17. **Docs and release:** `docs/api.md` states that the notification goes to the agent, the new 409/400 cases and the new
    filter; the changelog entry and version bump are part of the pull request per CONTRIBUTING. The API-doc line "A
    filter value that is not a status or a priority is `invalid`" must be reworded so it does not claim `assignee` is
    validated that way.

## Build order

1. **Baseline:** `npm test` green before any edit; note the count.
2. **Query layer** (`src/tickets/query.js`): `assignee` parsing and `matchesFilters` -> AND. Run `npm test`
   (existing query/api tests still green). Then a quick node REPL check of `parseListQuery(new URLSearchParams('assignee='))`.
3. **Persistence + store data:** `ticketRecord`/`readTicket` and the store's `create` and constructor normalization.
   Check: create a ticket, `snapshot()`, round-trip through a temp file; load a hand-written file with no `assignee`.
4. **Validation** (`validate.assignment`), **store.assign** and the template. Check in a node script with the store
   alone: assign, reassign, same value, unassign, resolved ticket 409, outbox contents with the worker off.
5. **HTTP route** in `src/app.js`. Check with `withService`-style script or by starting the server on a random port (port 0) and curl.
6. **Command line:** `format.js` table column and `details`; run `bin/tickets.js list` on a data file written by step 5; then
   `scripts/weekly-report.js --json` before/after.
7. **Tests:** write the new test files, run `npm test` (whole suite).
8. **Docs, changelog, version.** Last, so they describe what was actually built.
9. Final: `npm test`, `git status` shows only intended files, no existing test file modified.

## How we will know

- **U-1 / C-1, C-3..C-9, C-11, C-14:** start the service on port 0, `POST /tickets`, `PUT /tickets/T-0001/assignee`
  `{"assignee":"dana"}` -> 200 with `assignee: "dana"` and new `updated` (use `manualClock().advance` to see the time
  change); `GET` shows it; repeat the same PUT -> 200, same `updated`, audit length unchanged, outbox unchanged;
  reassign to `sam`. Names of 1, 64 (ok) and 65, `""`, `"   "`, tab/newline (400); body without field, numbers,
  booleans, arrays, objects, extra field, non-object body (400); `T-9999` -> 404; transition a ticket to resolved and
  PUT a different name -> 409 with assignee/updated/audit unchanged; closed likewise; `PUT null` on resolved with an
  assignee -> 409. Transition and PATCH keep the assignee; `PATCH {assignee}` and `POST` with `assignee` -> 400.
- **U-2 / C-2, C-10:** PUT `null` on an assigned open ticket -> `assignee: null`, audit entry `{from:'dana',to:null}`;
  again -> no change, no new entry.
- **U-3 / C-17..C-21:** worker off: `GET /admin/outbox` pending contains `{type, to:'dana', ticket}` for the assignment and
  nothing for unassign, same-value, refused; dana then sam -> both events present; `T-0007` and `T-0008` to dana -> two
  events; the requester has only the `ticket.created` (and `ticket.resolved`) events. Worker on (tick manually): event
  ends `sent`, `dead` empty, notifier `delivered` line `to: 'dana'`, names the ticket. Also with `notifyFile`.
- **U-4 / C-22..C-27:** seed tickets of mixed status, priority and assignee; `?assignee=dana`, `?assignee=` (and `?assignee`),
  unknown name -> `items: []`, `next: null`; `?status=open&assignee=dana`, `?status=open&priority=urgent`,
  `?assignee=&status=in_progress&priority=high`; paging with `limit=2` and `cursor` through all of dana's tickets; invalid
  `status`/`priority`/`limit` still 400. Add unit tests of `parseListQuery`/`matchesFilters` in a new file with AND cases.
- **U-5 / C-28, C-29:** write a data file via the store with persistence, run `main(['--data', file, 'list'], { out })`
  (as an in-process call, like the other tests could) or `execFileSync(process.execPath, ['bin/tickets.js', ...])`; the
  header has `ASSIGNEE`, the dana row contains `dana`, an unassigned row does not name an agent; `--status`, `--priority`
  still filter; `list --raw` first four columns unchanged; `weekly-report.js --json` counts equal those of the same
  tickets unassigned.
- **U-6 / C-12, C-13, C-15, C-16:** audit lists the change with the actor from `X-Actor` (`system` by default); over-long
  actor -> 400 and nothing changed; concurrency: `Promise.all` of 5+ PUTs with distinct names, then audit chain
  `from == previous to`, final assignee equals the last `to`. Restart: `createService` with a temp `dataFile`, assign,
  `stop()`, create a new service on the same file, assignee still there (and after unassign too); a pre-change data file
  (written without `assignee`, e.g. by deleting the key from a saved document) loads, shows `null`, appears in the
  `assignee=` listing and in the CLI.
- **C-30, C-31, C-32:** `npm test` exits 0 with old and new tests; `git diff --stat` shows no edit to files under `test/`
  that existed before (only added files); the requester's `created` and `resolved` notifications still arrive once each.
- **A test of this change must not forget:** a second, different ticket (a change applied to the wrong ticket passes a
  one-ticket test); the unchanged `updated` on no-ops (needs an advancing manual clock); the worker-on delivery (a missing
  template is only visible there); `assignee=` meaning unassigned including resolved tickets; the combined-filter AND
  cases (the pre-existing OR bug); a restart round trip; no audit/outbox side effect on every refused request; and no
  dependence on open points (trim behaviour, the unassigned cell text, 409 versus 200 for same-value on resolved,
  action name, fifth raw column): test only names without edge spaces and the different-value refusal.
