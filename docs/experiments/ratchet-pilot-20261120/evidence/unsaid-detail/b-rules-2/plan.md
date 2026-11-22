# Plan: ticket assignment

## Approach

The service is layered: handlers (src/app.js) validate and call one store method; the store (src/store.js) checks state, applies a change via `apply()`, appends the audit entry, enqueues notifications and saves; persistence (src/persistence.js) has record functions naming every saved field; the outbox dedupes by `key`; templates (src/templates.js) render by outbox `type`; the CLI (bin/tickets.js + src/format.js) reads the data file. Assignment is one more store change that follows this pattern exactly. Parts touched:

- `src/store.js`: `assignee` on every ticket (null on create; normalised to null for tickets loaded without one); new method `assign(id, agent, actor)` built on `apply()`.
- `src/tickets/validate.js`: new `assignment(body)` returning the agent string or null.
- `src/app.js`: `router.put('/tickets/:id/assignee', ...)` (Router already has `put`); handler = validate, then `store.assign`. No notifier or direct mutation in the handler.
- `src/templates.js`: a template for the new notification type (without one the event goes dead after 5 tries).
- `src/tickets/query.js`: `assignee` filter parsing and `matchesFilters` fixed from "any" to "every" (C-16).
- `src/persistence.js`: `assignee` in `ticketRecord`; load defaults and checks it.
- `src/format.js`: ASSIGNEE column in the table; `details()` shows assignee; `describeChanges` reads sensibly for null.
- Docs: docs/api.md (new endpoint, filter, `assignee` field), README Command line, CHANGELOG. Docs only; keep them short.
- Tests: new `test/assign.test.js` (API-level, with the worker off), plus new test files or new additions for query/persistence/format. Existing test files stay byte-for-byte untouched (add new files rather than editing old ones).

Data: ticket `{..., assignee: string|null}`. Audit entry: `action` `ticket.assigned`, `changes: { assignee: { from, to } }`. Outbox event: `type: 'ticket.assigned'`, `to: <agent>`, `ticket: id`, `key: 'ticket.assigned:<id>:<agent>'`, `data: { title }`.

## Decisions

1. **One store method `assign(id, agent|null, actor)`**, using `apply()` with `{assignee:{from,to}}`. `apply()` already gives "no change means no audit, no `updated` change, no effects, no save" (C-7, C-8) and bumps `updated` (C-2). Rejected: a separate code path for unassign.
2. **Check order in the store**: `find` (404) then final-state check, then diff. The state check must come before the no-change check, so a same-agent or null-to-null request on a resolved/closed ticket is 409 (C-5). Use `isActive(ticket.status)` (open/in_progress), not `!isFinal`, since `resolved` is not final but must refuse. Rejected: reusing `isFinal` as `update()` does; it would let a resolved ticket be assigned.
3. **Handler order**: body validation first (400), then the store (404/409), as PATCH does. A malformed body on an unknown or closed ticket is therefore 400; the spec says tests must not combine these.
4. **Validation** (`assignment`): `onlyFields(body, ['assignee'])`; require `Object.hasOwn(body, 'assignee')` (absent is 400, not an unassign); `null` returns null; otherwise it must be a string, trimmed, non-empty, at most 64 characters, no control characters (reuse the `text()` rules with a new `LIMITS.assignee = 64`, same as requester). Open points taken: trim and 64, matching existing text fields; report these in the build report. Rejected: leaving names untrimmed, because " dana " vs "dana" would produce phantom reassignments and a tab-separated CLI risk.
5. **Compare after trimming**: no-change test is `ticket.assignee === agent` on the trimmed value. Exact, case-sensitive (C-14 Open: loosest is exact).
6. **Notification**: only when `to !== null` and the change is real, inside the `effects` callback of `apply()`, via `this.notify(ticket, 'ticket.assigned', agent, at, key)`. Key includes ticket id and agent so assignments to different agents never swallow each other, and it cannot collide with `ticket.created:T-n` / `ticket.resolved:T-n` (C-11). Rejected: the default key `ticket.assigned:<id>`, which would drop the `eli` notification while `dana`'s is pending. Unassign enqueues nothing (C-12); reassignment notifies only the new agent.
7. **Filter representation**: `filters.assignee` is a string, or `null` for the empty `assignee=`. `matchesFilters` currently drops only `undefined`, so `null` stays "given". Change `.some` to `.every` (C-16; existing unit tests only use single filters, so they keep passing). Compare with `(ticket.assignee ?? null) === value`.
8. **CLI**: table gets an `ASSIGNEE` column placed just before TITLE (title is the last, unpadded, free-text column), placeholder `-` for unassigned. `list --raw` is left unchanged (C-18 Open; weekly-report reads by position and the README documents four columns). No `--assignee` CLI option (not requested). `show` also prints an assignee line (additive; check existing tests do not pin its exact output).
9. **Persistence**: add `assignee` to `ticketRecord`; in `readTicket`, treat an absent/undefined `assignee` as null (old files), accept null or a non-empty string, otherwise `fail(...)`. Keep `VERSION` at 1 (the change is backward compatible, and ADR 0008 says old files keep loading). Rejected: bumping the version, which would refuse the previous files.
10. **No new ADR required**; add a short one only if cheap (optional).

## Nuances

- **Old data files (U-5, C-19).** `ticketRecord` would yield `assignee: undefined` for old records, which `JSON.stringify` drops, so a naive load shows no key. Default to null on load, and also in the `TicketStore` constructor (`{ assignee: null, ...ticket }`) because tests and the CLI build stores from state directly. Distinguish absent (valid, null) from wrong type (refuse at start, e.g. `""`, `5`, `false`).
- **Constructor normalisation order**: write `{ ...ticket, assignee: ticket.assignee ?? null }` (assignee after the spread), since `{ assignee: null, ...ticket }` is overridden by an explicit `assignee: undefined` key from `ticketRecord`.
- **The string `"null"` is a name**, not an unassign: never coerce strings (`"null"`, `"none"`). `?assignee=null` matches an agent called `null`, not unassigned tickets; only the empty value means unassigned.
- **`create()`** must set `assignee: null` on the ticket but `CREATED_FIELDS` must stay as is, so the created audit entry does not list assignee (C-20; store.test pins it). Tickets returned by every endpoint get the key because they are copies of the stored object (C-1).
- **Filter semantics change (C-16).** Fixing `.some` to `.every` changes `?status=open&priority=urgent` behaviour; this is a bug fix the docs already promise. Do not special-case. The empty `assignee=` must not be treated as "no filter": use `params.has('assignee')`, and `params.get` returns `''` which maps to null. `?assignee=` must never be 400. Repeated `assignee` params: use the first (`get`), as the other filters do.
- **Cursor paging with the filter**: the cursor is an id; `list()` filters, then paginates, so it works unchanged. Test a page boundary across a filtered set.
- **Notification dedupe (C-11).** Walk the three cases: dana then eli (two pending); dana, null, eli (dana pending, eli new); dana, eli, dana while dana's is still pending (the key is already pending, so no third event; dana still has one pending). A pending "received" for the requester must be untouched. Once the worker delivers, the key is free again, so reassigning to dana later enqueues anew (that is a real new change, correct).
- **Notification `to`** is the agent's name, not an email; the notifier writes it as is. The outbox rejects an empty `to`, which validation already prevents. The template must name the ticket id (C-10) and use `event.data.title`.
- **Audit entry only for real changes**; actor from `actorOf(req)`. Note `actorOf` can throw 400 for an overlong X-Actor; call it before the store, as other handlers do. `readAudit` already accepts `from: null`/`to: null`, so reload works.
- **`updated`** moves only on a real change; the new-assignee request on a closed ticket changes nothing at all (409 with no side effect). Because the store's `apply` assigns `ticket[field] = to` generically, `assignee` is written straight onto the ticket; no special code.
- **State is untouched by other changes (C-13).** `PATCH` still uses `onlyFields(['title','priority'])`, so an `assignee` field stays 400; do not widen it. `transition` does not clear the assignee. Resolved tickets keep their last assignee and still appear under `?assignee=dana` (and under `?assignee=` only if null).
- **`describeChanges`** prints `from === null` as `assignee dana`, but for unassign `to` is null and would print `assignee dana -> null`. Acceptable but better to print `assignee dana -> (none)`; keep the existing outputs for other fields identical.
- **CLI table width**: names in the ASSIGNEE column pad correctly through `table()` because it computes widths from the cells; `String(null)` must never appear: map null to `-`.
- **Existing tests unchanged**: store.test destructures named fields (fine), persistence test compares `fields` (fine), api tests compare same-endpoint bodies (fine). After building, run the whole suite before adding new tests to confirm nothing existing broke.
- **Restart**: `apply()` saves, and the unchanged path does not; nothing else must save. A test restarts by opening a new service/store over the same `DATA_FILE`, and reads with the CLI's `main()` (it takes `out` and `env`).
- **Route/method errors**: `GET /tickets/:id/assignee` hits the existing 404-with-methods message; nothing to build. Ticket id in the path is decoded by the router; an unknown id is a store 404.
- **Worker off** in tests (`workerIntervalMs: 0`) so pending events can be read from `GET /admin/outbox`; for delivery tests use the `service.test.js` style with a `NOTIFY_FILE`/in-memory notifier, and a template check that `render({type:'ticket.assigned', ...})` does not throw.
- **Clock**: tests use `manualClock`; advance it between changes so `updated` differences are observable.

## Build order

1. Baseline: run `npm test` (117 pass) to confirm the starting state.
2. `validate.assignment` + `LIMITS.assignee`; unit-check by hand.
3. `store.js`: `assignee: null` in `create`, constructor normalisation, `assign()`; `templates.js` template. Check with a small node script or the new store tests.
4. `persistence.js` record/load changes; round-trip and old-file checks.
5. `app.js` PUT route; exercise with the API tests (200/400/404/409, no-change, audit, outbox).
6. `query.js` filter + every-semantics; list tests incl. paging and combined filters.
7. `format.js` + CLI table/show; CLI tests with `main()`; confirm `list --raw` and `weekly-report` counts unchanged.
8. Docs (api.md, README, CHANGELOG).
9. Full `npm test`; then a real run on a random free port with `DATA_FILE` and a restart, stopping the process by its pid.

## How we will know

- **U-1**: PUT `{"assignee":"dana"}` on an open and on an in-progress ticket gives 200 with `assignee:"dana"`, `updated` advanced; GET shows it; `/audit` has one new entry with `changes.assignee {from:null,to:"dana"}` and the X-Actor; `/admin/outbox` has one pending event `to:"dana"` for that ticket; a worker tick or delivery line names the ticket id. Reassignment to `eli` works (not asserting on whether it is wanted beyond the loosest reading).
- **U-2**: `{"assignee":null}` gives 200 and null; audit `from:"dana",to:null`; no new outbox event; null-to-null leaves `updated`, audit and outbox as they were.
- **U-3**: with dana, eli, unassigned and mixed states: `?assignee=dana`, `?assignee=` (includes resolved/closed unassigned), `?status=open&assignee=dana`, `?status=open&priority=urgent` (every-filter fix), an unknown agent gives empty `items` and `next:null`, paging with `limit=1` and `cursor` over a filtered set.
- **U-4**: CLI `list` output has an ASSIGNEE heading and dana's name on dana's row; unassigned row has no `null`; `list --raw` lines still begin with the four columns and `scripts/weekly-report.js` counts are unchanged.
- **U-5**: a service with `DATA_FILE`, assign, stop, start a new service on the same file: still assigned; hand-written old-format file (no `assignee`) loads with `assignee:null`; a file with `assignee: 5` or `""` is refused at load with a DataFileError.
- **Must not forget to test**: 400 cases (empty, whitespace, number, boolean, object, array, absent key, tab/newline, extra field, array/non-object body) each leaving ticket, audit and outbox unchanged; 409 on resolved and closed for a name, for null and for the same agent; 404 unknown id; same-agent no-change (no audit, `updated`, outbox); the three dedupe sequences plus an earlier pending "received" surviving; PATCH/POST with `assignee` still 400; transition and PATCH keep the assignee; created ticket audit omits assignee; `POST /tickets` shows `assignee:null`. Tests must use plain names under 64 characters, no leading/trailing spaces, names differing by more than case, must not assert the audit `action`, the outbox `type`, the message wording, the raw placeholder or the raw column, and must not combine a malformed body with a closed ticket.
