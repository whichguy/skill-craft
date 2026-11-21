# Plan: ticket assignment

## Approach

The change follows the existing layering (handler validates -> one store method -> audit + outbox + save). Parts touched:

- `src/tickets/validate.js`: new `assignment(body)`: `onlyFields(body, ['assignee'])`; `assignee` must be present; `null` is allowed; otherwise it goes through the existing `text()` helper (string, trimmed, non-empty, no control chars, max length) with a new `LIMITS.assignee = 64` (same as requester). Returns the name or `null`.
- `src/app.js`: `router.put('/tickets/:id/assignee', ...)` -> `validate.assignment(await body(req))` -> `store.assign(params.id, assignee, actorOf(req))`, status 200. `router.put` already exists.
- `src/store.js`:
  - `create()` gives the new ticket `assignee: null`.
  - The constructor normalises loaded tickets: `{ assignee: null, ...ticket }` (older state has no key; also tolerate `undefined`).
  - New `assign(id, assignee, actor)`: `find` (404) -> `if (!isActive(ticket.status)) throw ConflictError` (409) -> if `ticket.assignee === assignee` return a copy -> otherwise `this.apply(ticket, assignee === null ? 'ticket.unassigned' : 'ticket.assigned', { assignee: { from, to } }, actor, effects)`. The effects callback notifies only when `assignee !== null`.
  - `isActive` already exists in `src/tickets/states.js` (open, in_progress).
- `src/templates.js`: new `'ticket.assigned'` template (`event.to` is the agent, `event.data.title`, `event.ticket`). Without it the worker retries and kills the event.
- `src/tickets/query.js`: parse `assignee` (see Decisions); `matchesFilters` changes from `some` to `every` and compares assignee against `ticket.assignee ?? null`.
- `src/persistence.js`: `ticketRecord` must include `assignee` (it whitelists fields, so otherwise the assignee is silently dropped at save: the C-14 trap). `readTicket` validates: `assignee` is `null`/absent (-> `null`) or a non-empty string, else `fail(...)`. Keep file `version` 1: an old file loads, with every ticket `null`.
- `src/format.js`: `RAW_COLUMNS` gets `'assignee'` appended as the 5th column (positions 1-4 untouched); `rawLine` maps `null` to the placeholder `-`. `TABLE_COLUMNS` gets an `ASSIGNEE` column (after PRIORITY; value `ticket.assignee ?? '-'`). `details()` (the `show` command) also lists `assignee`. `describeChanges` already copes with `from: null`.
- `bin/tickets.js`: needs no change (it reads tickets through `store.list`, so the new field flows through). No `--assignee` option is added (not requested).
- Docs: `docs/api.md` (new endpoint, `assignee` field, filter, the "every filter" wording that is now true), `README.md` (raw columns now five, first four fixed), `CHANGELOG.md` + `package.json` 1.5.0, a short `docs/decisions/0009-...` for the notification key (and add it to the decisions index). `docs/operations.md`: mention the new notification type if it lists types.

Data: ticket gains `assignee: string | null`. Audit entry `changes.assignee = { from, to }`. Outbox event `type: 'ticket.assigned'`, `to: <agent>`, `ticket: <id>`, `data: { title }`.

## Decisions

1. **Name rules reuse `text()`**: trimmed, max 64, no control chars. Reason: C-1's open point leaves it to the requester; matching the existing text fields is the least surprising, and C-3/C-22 already need non-empty/no control chars. Rejected: no trimming (`" dana"` and `"dana"` would be two agents, and a visible-looking name could be blank-padded).
2. **Validation happens in the handler, status checks in the store.** So a malformed body on a closed or unknown ticket is 400, not 409/404 (validation first, same as PATCH/transition). Rejected: checking the ticket first.
3. **Order inside `store.assign`: 404, then 409 (state), then no-change.** So repeating the current assignee on a resolved/closed ticket is 409 (C-8's taken answer), and nothing is changed. Unassigning an already-unassigned open ticket is a no-change 200.
4. **Notification key includes the audit seq of the change**: `ticket.assigned:<id>:<agent>:<seq>`, built inside the `effects` callback where `this.audit.size` is the seq of the entry just appended. Reason: the outbox dedupes a pending key, and a default key `type:ticket` (or `type:ticket:agent`) would swallow a real second assignment (C-11). Rejected: default key; `at` timestamp (a manual clock in tests gives equal times, so two changes would collide); a separate counter (extra state to persist).
5. **No notification on unassign** (C-12) and none for a no-change request; the only notify call is in the assign branch of effects.
6. **Audit action names**: `ticket.assigned` for a name, `ticket.unassigned` for null. Tests do not depend on them.
7. **Filter semantics.** `assignee` key present in the query -> `filters.assignee = value.trim()`; `''` means unassigned. Matching: `filters.assignee === '' ? ticket.assignee == null : ticket.assignee === filters.assignee`. Exact, case-sensitive. A filter value that is not a valid name (control chars, too long) simply matches nothing: no 400 (the spec says empty is valid and does not ask for validation of the rest; 400 would be an arbitrary new refusal). Rejected: representing "unassigned" as `null` in `filters` (then `given` filtering of `undefined` and `null` gets subtle); using `''` keeps `matchesFilters`'s existing `value !== undefined` test correct.
8. **`some` -> `every` in `matchesFilters`** is a fix of an existing bug that C-17 requires; the existing `test/query.test.js` only uses single filters, so it still passes unchanged.
9. **Raw column placeholder `-`** for unassigned in table and raw (visible, non-empty, so `awk`/`cut` by position keep working). Appended as column 5 so `scripts/weekly-report.js` is unaffected.
10. **Persistence version stays 1**; the loader defaults a missing assignee to `null`. Rejected: bumping the version (an old file would be refused, breaking C-14/U-5).
11. **`create()`'s audit entry (`CREATED_FIELDS`) stays as is**, so existing audit tests are unchanged; a new ticket's assignee is `null` without an audit line.
12. **PATCH keeps refusing `assignee`** (unknown field): assignment has its own endpoint.

## Nuances

- **Persistence drops the field (C-14).** `ticketRecord` is used both to save and to load; if `assignee` is not added there, everything works until restart. Add it, then test with a real `DATA_FILE` across two `createService` runs. Also test loading a hand-written old-format file (no `assignee` key) -> `null`, and that a file with `"assignee": ""` or `5` is refused with a `DataFileError`.
- **Outbox dedupe (C-11).** See decision 4. Also check that it is not over-corrected: re-sending the same name is a no-change and must enqueue nothing (C-8/C-12). Scenarios to test: dana then sam with the worker off -> two pending; dana, null, dana -> two pending to dana.
- **Missing template (C-10).** A `ticket.assigned` type with no template reaches `dead` after 5 attempts. Add the template, and test by running a delivery (`service` worker / `notifier.deliver` via helpers) that the event is sent and the message names the ticket and the assignment.
- **Existing tickets in memory/older state (C-9, U-5).** `store.constructor` copies tickets with spread; if `assignee` is `undefined` it would be omitted from JSON, and `GET /tickets?assignee=` would still need to treat it as unassigned. Normalise in the constructor and in the filter (`?? null`).
- **`update()` and `transition()` keep the assignee (C-9).** They mutate only their fields via `apply`, so it holds; add a test that PATCH, transition to resolved, then GET still shows the assignee, and that a resolved ticket can no longer be unassigned (C-6) though its assignee is shown.
- **`updated` and no-change (C-8).** `apply` returns early with no changes (no `updated`, audit, notification, save). The same-name branch must go through that path or return early; verify `updated` and the audit length are unchanged using the manual clock advanced between calls.
- **Name trimming vs. no-change.** `"dana "` trimmed equals `"dana"`, so it is a no-change. Compare the trimmed value.
- **`null` vs. missing vs. wrong type (C-3).** `{}` must be 400 (not treated as unassign); `{"assignee": undefined}` can't occur in JSON. `""`, `"  "`, `0`, `true`, `{}`, `[]` are 400. `text()`'s error says "must be a string"; for null handle before calling `text()`.
- **Error order for body vs. ticket (C-3, C-5, C-7).** 400 beats 404/409 since validation precedes the store. Tests for 404 and 409 must send a valid body.
- **Query parsing: `params.has('assignee')`**, not truthiness, since the empty value is meaningful. `URLSearchParams` decodes `+` as a space and `%20`; trimming then handles `?assignee=%20`.
- **Pagination with filters (C-15).** `store.list` filters before paginating; a cursor is just a ticket id, so the existing mechanism keeps the filter as long as the client repeats it. Test limit=1 over assignee-filtered tickets, and a cursor that points at a ticket not matching the filter (works via `compare`).
- **Existing `matchesFilters` unit test passes tickets without `assignee`**: the `?? null` handles that.
- **Raw column (C-19).** `rawLine` joins with tabs; an assignee name cannot contain tabs because of the control-char refusal (C-22), but a hand-edited data file could. The loader rejects non-strings only; optionally also reject control chars in loader for assignee. Do so with the same CONTROL check if cheap, else leave. Confirm `scripts/weekly-report.js` reads columns by index and gives the same counts before/after (run it against a data file with assigned tickets).
- **Table padding.** `table()` pads every column but the last; the new column sits in the middle, so widths adjust automatically; the title stays last.
- **Existing tests must not be edited.** New tests go in new files only (e.g. `test/assignment.test.js`, extra cases for query/format/persistence in new files rather than appended to old ones). Notice `test/api.test.js` line 180 checks the outbox pending list shape; it creates and resolves only, so no assignment events sneak in.
- **Notification `to` is the bare agent name**, not an address; the outbox requires a non-empty string, which the validator guarantees. Max length of `to` is irrelevant.
- **Concurrency**: the store is synchronous, so check-then-change in `assign` is atomic. Nothing to add.
- **Actor** comes from `X-Actor` (`actorOf`), default `system`; audit entry records it (C-13).

## Build order

1. `validate.assignment` (+ `LIMITS.assignee`); quick manual check in a scratch script.
2. `store.js`: `create` gets `assignee: null`, constructor normalises, `assign` with the key, template in `templates.js`. Run `npm test` (existing suite must stay green).
3. `persistence.js` record + validation; check save/load round trip and an old-format file.
4. `app.js` route; start the service on port 0 (or use `withService`) and exercise U-1/U-2 with curl-like calls.
5. `query.js`: assignee filter and `every`; check U-3 combinations.
6. `format.js` (raw column, table column, `show`) and run the CLI on a data file; run `scripts/weekly-report.js` before/after on the same file for identical counts.
7. New tests under `test/` (new files only), then full `npm test`.
8. Docs, CHANGELOG, version bump, decision record 0009 + index.

## How we will know

- **U-1 / C-1, C-10, C-12, C-13**: `withService` (worker off): create ticket, `PUT .../assignee {"assignee":"dana"}` with `X-Actor: kim` -> 200, `assignee: "dana"`; `GET` shows it; `/admin/outbox` pending has one event `{type: 'ticket.assigned', to: 'dana', ticket: 'T-0001'}`; audit last entry actor `kim`, `changes.assignee {from:null,to:'dana'}`. With the worker on (or running the delivery through the store/notifier), the delivered message mentions the ticket and assignment.
- **U-2 / C-2, C-6**: unassign -> 200 `null`, audit `{from:'dana',to:null}`, no new notification; on a resolved/closed ticket -> 409 and the assignee is kept.
- **C-3/C-4/C-22**: table of bad bodies (`""`, `"  "`, `1`, `true`, `{}`, `[]`, `{}` body, array body, no body, extra field, tab/newline) -> 400 `invalid`, ticket unchanged, outbox/audit unchanged.
- **C-5/C-7/C-8/C-11**: resolved and closed tickets -> 409; unknown id -> 404; repeat same name -> 200 with `updated`, audit length and outbox count unchanged; dana->sam and dana->null->dana make 2 pending each.
- **C-9**: every endpoint shows the `assignee` key; survives PATCH/transition.
- **U-3 / C-15-C-17**: tickets for dana/sam/none across statuses and priorities; `?assignee=dana`, `?assignee=`, `?assignee=nobody`, `?status=open&assignee=dana`, `?priority=high&assignee=`, `?status=open&priority=urgent` (intersection), plus limit/cursor paging with the filter.
- **U-4 / C-18, C-19**: run `node bin/tickets.js --data FILE list` and `list --raw` via `main()` with captured output (see existing tests for the pattern): assigned ticket's line contains the name; raw columns 1-4 equal the old values; the weekly report gives identical counts.
- **U-5 / C-14, C-20**: restart with `DATA_FILE`; an old-format file loads with `null`; the whole `npm test` passes with the existing test files untouched (`git diff --stat` shows no changed test files).
- **Must not forget in tests**: use new test files only; ordinary short names; do not assert notification wording, audit action name, or the placeholder; do not assert behaviour for the open points (resolved + same assignee, unassign of an unassigned ticket, trimming/length); clean up temp data files with `t.after`; ports via port 0 only.
