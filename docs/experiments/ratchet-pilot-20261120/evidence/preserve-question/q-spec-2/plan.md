# Plan: ticket assignment

## Approach

The change follows the existing layering: validator → store method → audit + outbox + save; the handler only validates and calls one store method.

Parts touched:

- `src/tickets/validate.js`: new `assignment(body)`. `onlyFields(body, ['assignee'])`. A missing `assignee` is 400. `null` returns `null`. A string goes through the existing `text(body, 'assignee', 64)`, which trims, rejects empty, counts after trimming and rejects control characters. Anything else is 400 "assignee must be a string or null". Add `assignee: 64` to `LIMITS`.
- `src/store.js`:
  - New `assign(id, assignee, actor)`: `find` (404), then `isActive(ticket.status)` else `ConflictError` (409). The status check comes before the no-op check (C-5). Then `apply(ticket, 'ticket.assigned', changes, actor, effects)`. `changes` is `{}` when the value is the same, which `apply` already turns into "no change, no audit, no notify, no save, `updated` kept". The effect is `notify(...)` only when `assignee !== null`.
  - `create()` sets `assignee: null` on the new ticket (C-9). Do not add `assignee` to `CREATED_FIELDS`: that would alter the existing created-audit entry, which `test/store.test.js` pins.
  - The constructor normalizes `assignee: ticket.assignee ?? null` for tickets from a passed-in `state`, so a store built from an old state object also works.
- `src/templates.js`: new `'ticket.assigned'` template. Without it the event goes dead after five retries. The subject carries the ticket id. The body names the ticket id and title and says it was assigned to them.
- `src/persistence.js`: `ticketRecord` gains `assignee: ticket.assignee ?? null`, so it is saved and an old record normalizes to `null`. `readTicket` validates the assignee: `null` is fine; otherwise it must be a string, non-empty, at most 64 characters, and without control characters. Anything else is refused as a `DataFileError` naming `tickets[i].assignee`. Do not require `assignee` to be present, and do not bump `VERSION`. An old file is still version 1 and still loads.
- `src/tickets/query.js`: `parseListQuery` reads `assignee`. The empty string becomes `filters.assignee = null`; any other value is kept exactly. `matchesFilters` changes from `some` to `every`, comparing `(ticket[field] ?? null) === value`.
- `src/app.js`: `router.put('/tickets/:id/assignee', ...)` runs `validate.assignment(await body(req))`, then `store.assign(params.id, assignee, actorOf(req))`, and answers 200.
- `src/format.js`: add an `ASSIGNEE` column to `TABLE_COLUMNS`, with `-` for unassigned. `RAW_COLUMNS` stays as it is.
- Docs: `docs/api.md` (endpoint, `assignee` field, filter, note that filters combine with "every"), `README.md` (CLI column), `CHANGELOG.md`, `docs/operations.md` (the assigned notification). Optionally a decision record. Docs only, not a gate.
- New tests: `test/assign.test.js` (API), plus cases added to new files rather than edits to old ones. Existing test files stay untouched.

Data shape: a ticket gains `assignee: string | null`. The audit entry is `{ assignee: { from, to } }`. The outbox event is `{ type: 'ticket.assigned', to: <agent>, ticket: id, data: { title } }`.

## Decisions

1. **Notification key includes the agent: `ticket.assigned:<id>:<agent>`.** The default key `type:ticket` would make an assignment to `bob` while `dana`'s is still pending return `dana`'s pending event, so `bob` is never told (breaks C-11 "two different agents notify each"). Rejected: the default key. Rejected: no key (`enqueue` requires one).
   - Consequence: assign `dana`, unassign, assign `dana` again within one worker interval sends one notification. This is the existing dedupe-while-pending behaviour, and the spec leaves this point to the requester (C-11 Open). Note it in the build report. Reassigning to someone else, or to `dana` after her notification was sent, does notify.
2. **Notification type `ticket.assigned`, with a new template.** The wording is free (C-11 Open). Tests must check only `to` and `ticket`, plus that the delivered line names the ticket id.
3. **Validation before store lookup, as in the other handlers.** A bad body on an unknown id gives 400, not 404. Order: body is a JSON object (`readJson`), then field checks, then 404, then 409, then the no-op check.
4. **Status gate uses `isActive` from `states.js`** (open or in_progress). It does not reuse `isFinal`, because `update()` lets resolved tickets change and assignment must not.
5. **Unassign is `null`, stored as `null`, never `''`.** The filter's empty value is mapped to `null`, so a ticket and a filter agree.
6. **The filter is an exact, case-sensitive match on the raw query value.** No trimming and no case folding (C-15 Open). A value that is only whitespace or contains control characters matches nothing and gives a 200 with an empty list, not 400. `assignee=` repeated: `params.get` takes the first, as the other filters do.
7. **`matchesFilters` becomes `every`.** The existing tests use only single filters and an empty filter set, so they pass. Keep the "undefined means not given" rule. The empty `filters = {}` case must still pass everything (`[].every` is true, so the early return can go).
8. **The CLI gets the column but no new option.** `--assignee` is not requested. `list --raw` is unchanged: four columns, no fifth. The weekly report and the "keep their positions" promise are safest that way (C-20 Open).
9. **`-` for unassigned in the table.** An agent literally named `-` is indistinguishable. Accepted; `show` and the API show the truth.
10. **ASSIGNEE column placed before UPDATED**, so the unpadded TITLE stays last and long titles don't move it.
11. **No new audit fields in `CREATED_FIELDS`;** the audit `action` is `ticket.assigned` (free per C-13 Open).
12. **`show` also gets an `assignee` line.** It is optional per C-19. Check `test/` for exact `details()` output first; none was found, and if a test pins it, skip this.

## Nuances

- **Notification dedupe key (C-11, C-12).** See Decision 1. The most likely wrong build is `this.notify(ticket, 'ticket.assigned', agent, at)` with the default key. The effect must also run only when `changes` is non-empty and the new value is not `null`. `apply` returns early when `changes` is empty, so the effect is never called for a no-op. The effect still has to skip `null`.
- **409 before no-op (C-5 vs C-7/C-8).** Re-assigning the same agent on a resolved ticket is 409, not 200. Check state first, and do not use `apply`'s empty-change shortcut to answer before the status check.
- **Validation errors leave no trace (C-3, C-4).** All of 400, 404 and 409 happen before any mutation: no `updated` change, audit entry, event or save. A 65-character name is refused, a 64-character name is accepted, and a trimmed name counts after trimming (a name of 64 characters plus spaces is valid). `text()` already does this. Count with `.length` as the other fields do; do not invent code-point counting.
- **Missing field vs `null` (C-4).** `body.assignee === undefined` is 400 (`{}`), while `null` is valid. `'assignee' in body` is the right test; a body `{"assignee": undefined}` cannot arrive over JSON. `{}` must not unassign by accident.
- **Unassigning an unassigned ticket (C-8).** `from === to === null`, so no change. Compare with `!==` after normalizing `undefined` to `null` (old in-memory tickets).
- **Old data (C-14).** The data file path is `load()` → `readTicket` → `ticketRecord`. If `ticketRecord` just copied `ticket.assignee`, it would be `undefined` and then be dropped by `JSON.stringify`, so the field must default to `null` in `ticketRecord` itself. Test with a hand-written version-1 file with no `assignee` anywhere. Also test a restart: save with a store, reopen with `TicketStore.open`, and via `createService` with `dataFile`. A hand-edited file with `"assignee": 5` or `""` must be refused with the record named, consistent with the other record checks.
- **Status changes keep the assignee (C-10).** `transition()` and `update()` touch only their own fields, so this holds naturally. Tests must cover resolve, close and reopen. A reopened ticket (resolved → open) with an assignee is assignable and reassignable again.
- **Every response shape carries `assignee` (C-9).** All returns copy the ticket object, so adding the field to the stored object is enough, including `POST /tickets` (201). `test/api.test.js:21` compares POST and GET bodies, which remains consistent. Key order does not matter.
- **`updated` on assign (C-1).** `apply` sets it to `clock.now()`. Tests use `manualClock`, so advance it between create and assign to see `updated` change, and check it does not change on a no-op.
- **Filters (C-15 to C-18).**
  - `assignee=` gives `null`, and `null !== undefined`, so the filter is "given". The "ignore undefined values" line in `matchesFilters` must not treat `null` as absent.
  - The invalid-value checks for `status` and `priority` still run, and a 400 on one of them beats a valid `assignee`.
  - `every` changes the result for `?status=open&priority=urgent`. Today it lists the union. The spec (C-17) and `docs/api.md` require the intersection.
  - Cursor paging over a filtered listing: `paginate` runs over the filtered, sorted list, so no ticket is repeated or missed. Test with `limit=1` or 2 across a mix.
  - No `assignee` parameter means no filtering. `assignee` is not special-cased against assigned tickets.
  - The CLI's `allTickets` passes `{}` filters; fine.
- **CLI (C-19, C-20).** `table()` pads every column but the last. Names up to 64 characters widen the column; fine. Do not touch `RAW_COLUMNS` order. The CLI opens a store with no persistence, so it still never writes. A data file from before this change must list with `-` in the ASSIGNEE column, which relies on the load defaults.
- **`PUT` routing.** `Router` already has `put`. A `PUT` to `/tickets/T-0001` (not the assignee path) still falls to the "does not answer PUT" 404 with the new message listing methods. No existing test should depend on the exact methods listing for `/tickets/:id/assignee`; it didn't exist. Trailing slash is ignored by the router already. `GET /tickets/T-0001/assignee` is answered 404 `not_found`, listing PUT, via `methodsFor`.
- **Actor header (C-13).** `actorOf` may throw on an `X-Actor` over 64 characters, after the body is validated. Either order gives 400 and no change.
- **Not a double notification when the worker runs.** Worker off in tests (`workerIntervalMs: 0`). To see delivery, call `service.worker.tick()` or whatever `createService` exposes (read `src/server.js` and `test/service.test.js` first), and read `notifier.delivered`, or use `notifyFile`.
- **Persistence order.** `save()` is inside `apply`, after the audit and the effects, as for the other changes. Do not call `save` twice.
- **Existing tests that must not break.** `test/store.test.js:22` and `:37` compare chosen fields and the audit, which are unaffected. `test/query.test.js` `matchesFilters` tickets have no `assignee` field; `?? null` keeps them working. `test/persistence.test.js:40` maps tickets through `fields`, unaffected.
- **`SHOW` details.** If a test pins `details()` output, skip the extra line.

## Build order

1. `validate.assignment` and `LIMITS`; unit-check with a quick node snippet.
2. `store.js`: normalization in the constructor, `create()`, then `assign()`; `templates.js` template. Check with a scratch script: assign, no-op, 409, notification keys for two agents.
3. `persistence.js`: `ticketRecord`, `readTicket`; check round trip, an old file, and a bad file.
4. `query.js`: `assignee` parse and `every`; check single and combined filters.
5. `app.js`: the PUT route; run the server on port 0 and curl the flows, then `npm test` (old tests must be green at this point).
6. `format.js` and the CLI column; run the CLI on a data file with and without assignees, and `npm run report:weekly`.
7. New tests under `test/` (API, store/validator, persistence, query, CLI, notification delivery).
8. Docs and changelog. Run `npm test` last and confirm that no existing test file changed (`git status` shows only added test files).

## How we will know

- **U-1 / C-1, C-3, C-4, C-6.** PUT for open and in-progress tickets: 200, the assignee, a later GET matches, other fields equal, `updated` advanced. Bad bodies: `{}`, `[]`, `"x"`, `{"assignee":5}`, `true`, `{}`-object, a list, `{"assignee":"a","x":1}`, `""`, `"   "`, a 65-character name, a name with a tab. Boundaries: 64 accepted, 64 plus surrounding spaces accepted and stored trimmed. Each refusal leaves the ticket, audit and outbox unchanged. `T-9999` is 404.
- **U-2 / C-2, C-8.** Unassign an assigned ticket gives `null`; unassign an unassigned one is a no-op with `updated`, audit and outbox unchanged.
- **C-5.** Resolved and closed tickets: every PUT (agent, `null`, the same agent, `null` on unassigned) gives 409, with nothing changed. A reopened ticket is assignable again.
- **C-7, C-12, C-13.** Same-agent PUT leaves the audit count and the outbox count the same. An unassign adds no notification. The audit entry has the `X-Actor` (or `system`) and `{assignee: {from, to}}`, and old entries are unchanged. Do not assert on `action`.
- **U-3 / C-11.** With the worker off, `GET /admin/outbox` shows pending items with `to: 'dana'` and `ticket: 'T-0001'`. Assigning `dana` then `bob` before delivery gives two events (the key nuance). After a worker tick, the delivered line (in memory or `NOTIFY_FILE`) is addressed to the agent and its subject or body mentions the ticket id. Do not assert wording or the type name. Do not assert on the undelivered re-assignment case.
- **U-4 / C-15 to C-18.** A mixed set with different assignees, statuses and priorities. Check `assignee=dana`, `assignee=dan` (empty result), `assignee=` (unassigned only, status 200), `assignee=dana&status=open`, `assignee=&priority=high`, `status=open&priority=urgent` (intersection), paging with `limit=1` over a filtered listing (no duplicates, none missed), and an unknown parameter ignored. The old invalid-value 400s still hold. Use agent names that differ by more than case.
- **C-9, C-10.** `assignee` is present, and `null` where unassigned, in the POST 201, GET one, GET list, PATCH, transition and PUT responses. Resolve, close and reopen keep it.
- **C-14.** Restart on one data file keeps the assignee. A hand-written version-1 file with no `assignee` loads and shows `null`. A file with a bad assignee is refused.
- **U-5 / C-19, C-20.** The table has an ASSIGNEE heading, the name is on its ticket's row only, and unassigned shows a mark. Old columns are intact. The `--raw` first four columns are unchanged, and `npm run report:weekly` gives the same counts on a data file with assigned tickets. The CLI does not modify the data file (compare bytes or mtime).
- **U-6 / C-21, C-22.** `npm test` passes, with `git diff` showing no edits to the existing test files and no change to `package.json`. Creating or patching a ticket without assignment queues no assignment notification.
- Tests must use `manualClock` for `updated`, port 0 through `withService`, temp folders for data files, and stop everything they start.
