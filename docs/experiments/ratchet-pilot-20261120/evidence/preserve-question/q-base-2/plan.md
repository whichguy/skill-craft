# Plan: ticket assignment

## Approach

The change follows the existing layering (CONTRIBUTING.md: handlers validate and call one store method; the store applies, audits, enqueues and saves). Parts touched:

- `src/tickets/validate.js`: new `assignment(body)` returning `string | null`.
- `src/app.js`: `router.put('/tickets/:id/assignee', ...)` — `validate.assignment(await body(req))`, then `store.assign(id, assignee, actorOf(req))`, 200 with the ticket. No notifier call in the handler. The router already has `put`.
- `src/store.js`: `create()` adds `assignee: null`; new `assign(id, assignee, actor)`; the constructor normalises tickets from an old state (`assignee: ticket.assignee ?? null`).
- `src/templates.js`: a `ticket.assigned` template. Without it the worker cannot render the event and it ends up dead after 5 attempts.
- `src/persistence.js`: `ticketRecord` is a **whitelist** of fields, used both to save and to load. Without adding `assignee` there, the assignment would silently vanish on every save (C-22). Add `assignee: ticket.assignee ?? null`; in `readTicket` check it is null or a string of 1..64 characters, else a `DataFileError` like the other fields. `VERSION` stays 1: an old file loads with `assignee` undefined, which `?? null` turns into null.
- `src/tickets/query.js`: `parseListQuery` reads `assignee` (present and empty → `filters.assignee = null`; present and non-empty → the string verbatim); `matchesFilters` changes from `some` to `every`, and compares `(ticket.assignee ?? null) === value`.
- `src/format.js`: an `ASSIGNEE` column in `TABLE_COLUMNS`; optionally an `assignee` line in `details`.
- `bin/tickets.js`: no change needed for the table (it uses `TABLE_COLUMNS`). Optional `--assignee` is not requested; skip it.
- `docs/api.md`, README (command line section), CHANGELOG, a decision-free note; update docs in the same pass. Also record the outcome in a journal per the global instructions (`docs/assignment-journal.md`) — keep it short.
- Tests: new `test/assignment.test.js` (API via the existing `test/helpers.js`, store, query, format, persistence round trip, CLI). Existing tests are not edited.

Data: a ticket gains `assignee: string | null`. The audit entry for a change has action `ticket.assigned` and `changes: { assignee: { from, to } }`. The outbox event: type `ticket.assigned`, `to` = agent name, `ticket` = id, `data: { title }`.

## Decisions

1. **A dedicated `store.assign`, not an extension of `update`.** `update` refuses only a final (closed) ticket, so a resolved ticket can still be patched; assignment must also refuse resolved. Rejected: an `assignee` field on PATCH (loosens PATCH and its unknown-field refusal).
2. **State check with the existing `isActive(status)` in `src/tickets/states.js`** (open and in_progress), not `!isFinal`. It runs before the change is computed, so on a resolved/closed ticket every request is 409, including a no-op one (C-5's Open: 409, simplest and consistent).
3. **Order of errors:** body validation (400) happens in the handler before the store looks up the ticket, as in PATCH/transition; so an unknown id with a bad body answers 400, an unknown id with a good body 404. Then 404, then 409, then no-op/apply.
4. **Name rule: reuse the `text()` helper's rule** (trimmed, non-empty, ≤64 `.length`, no control characters), stored trimmed. Consistent with `requester` (C-3 Open). `text` takes `body[name]` and requires a string, so write `assignment` as: `onlyFields(body, ['assignee'])`; `undefined` → InvalidError; `null` → null; else `text(body, 'assignee', LIMITS.assignee)` (add `assignee: 64` to LIMITS). Rejected: a custom no-trim rule (differs from requester without being asked).
5. **Notification key `ticket.assigned:<id>:<agent>`**, passed as the `key` argument of `notify` (it already has the parameter). The default key (`type:ticket`) would let a pending notification to dana swallow the one to lee (C-12). Keying on agent also means dana→lee→dana before the worker runs does not queue dana twice; accepted (the first is still pending and will be delivered). Rejected: withdrawing the earlier pending event (Open in C-12; needs outbox changes).
6. **`to` is the agent name**, as C-10 says; no address mapping.
7. **`matchesFilters` becomes `every`** (C-17). The existing unit tests only use one filter at a time, so they still pass. The pagination count/`next` come from the filtered list, so nothing else changes.
8. **Filter `null` means unassigned.** `parseListQuery` yields `{ assignee: null }`; `matchesFilters` must not treat `null` like "not given" (it only skips `undefined`, which is right). The filter value is not trimmed or length-checked (C-18).
9. **`--raw` unchanged** (C-20): leave `RAW_COLUMNS` as is; do not append, which keeps `weekly-report.js` safe and the choice simplest.
10. **Placeholder for unassigned in the table: `-`.** The table is whitespace-aligned, not tab-separated, so an empty cell would misalign the reading.
11. **Column position:** insert ASSIGNEE after REQUESTER (before UPDATED), keeping TITLE last since the last column is unpadded and can contain anything.

## Nuances

- **Persistence whitelist (C-22, C-9, C-21).** The biggest trap: `ticketRecord` drops unknown fields on save, and `readTicket` calls it on load. Forgetting it passes every in-memory test and fails after restart. Also `snapshot()`/constructor copy tickets with spread, so a loaded old ticket has `assignee` undefined until normalised — normalise in `ticketRecord` (covers file loads, including the CLI, which uses `createPersistence(...).load()` then `new TicketStore({state})`) and also in the store constructor (covers `state` passed directly by tests).
- **Old data and `matchesFilters`.** A ticket with `assignee` undefined must match `assignee=` (unassigned) and show `null` in responses: normalise on read, and compare with `?? null` as a second guard. The existing `matchesFilters` unit test uses a ticket with no `assignee` field; it must still work.
- **Existing `some` bug (C-17).** Fixing it changes `?status=open&priority=high` for existing clients from "either" to "both". That is what docs/api.md says, so it is the intended behaviour; mention it in CHANGELOG.
- **No-op detection (C-6, C-7, C-14).** `apply()` already returns the unchanged ticket with no audit, no effects, no `updated` bump when `changes` is empty. Build `changes` only when `ticket.assignee !== assignee`. The notification must be inside `effects` so a no-op sends none, and only when `assignee !== null` (C-11).
- **Trimming and no-op.** `"dana "` stores `dana`; compare after trimming, or a repeat of `"dana "` would count as a change.
- **Body shapes (C-4).** `readJson` already rejects a non-object body; `onlyFields` rejects extras; a missing `assignee` must be 400, not read as null (`body.assignee === undefined`). A body that is itself an array or null is already refused by `readJson`; an array/object *value* of `assignee` is refused by `text` (not a string). `assignee: ""` and 65 characters → 400; whitespace-only → 400 via `text` (empty after trim).
- **Audit (C-13).** `describeChanges` prints `assignee null -> ` for from null as `assignee dana`; for unassign `assignee dana -> null` — acceptable. The audit `changes` object `from: null` is already the norm for created entries.
- **Notification content (C-10).** The template must name the ticket id and say it was assigned to them, e.g. subject `[T-0042] Assigned to you`, body `Ticket T-0042 "title" was assigned to you.` The `data` carries only `title` as for other events; the title is read at enqueue time.
- **Existing outbox expectations.** `test/api.test.js:180` asserts the exact pending list after creating tickets; assignment events are only added by the new endpoint, so unaffected. Do not add an assignee notification on `create`.
- **Restart with pending events (C-22).** `eventRecord`/`readEvent` in persistence carry the event fields; `readEvent` only requires `type` to be non-empty text, so `ticket.assigned` survives load (verified); still cover it in the restart test.
- **Unassign then notify nobody (C-11).** `null` → no event; `to` would be null and `enqueue` throws a TypeError for a non-string `to`, so guard explicitly.
- **Route matching.** `/tickets/:id/assignee` with a trailing slash works via the router; GET on it falls to the 404 "does not answer GET; it answers PUT" message — fine.
- **Ids.** The `:id` is not validated for shape; an unknown/odd id is 404 from `find`.
- **Closed ticket reopened.** resolved → open is allowed by the lifecycle; an existing assignee stays through transitions (not cleared). Do not clear the assignee on resolve/close (not requested).
- **The read-only CLI.** `openStore` builds a store without persistence, so nothing there may write.
- **Test isolation.** Never use fixed ports; use the existing helpers. Tests with `DATA_FILE` use temp dirs under the test's own tmp dir.

## Build order

1. `validate.js` (`assignment`, limit) — unit-check by running a quick script/test.
2. `store.js` (`create`, constructor normalisation, `assign`), `templates.js` (`ticket.assigned`). Run `npm test` — existing tests must be green.
3. `persistence.js` (`ticketRecord`, `readTicket`): round trip, old file without `assignee`.
4. `query.js` (`parseListQuery` assignee, `matchesFilters` every). Run `npm test`.
5. `app.js` route. Try by hand on a port-0/random-port server.
6. `format.js` ASSIGNEE column (+ `details` line); run the CLI on a data file with and without assignees; run `scripts/weekly-report.js` on it.
7. Tests in `test/assignment.test.js` (and a CLI section); run `npm test`.
8. Docs (api.md, README, CHANGELOG) and the journal.

## How we will know

- **U-1 / C-1, C-10, C-12, C-13, C-14:** start the service with `WORKER_INTERVAL_MS=0` on a random port; create a ticket, PUT `dana` → 200, assignee `dana`; GET shows it; `GET /admin/outbox` pending has a `ticket.assigned` event with `to: dana`; audit shows `changes.assignee {from:null,to:dana}`; `updated` moved. Reassign to `lee` before any worker run: both events pending. Then run the worker (in a test, via `createWorker`/helpers) and see `notifier.delivered` has a message to `lee` mentioning the ticket id.
- **U-2 / C-2, C-7:** PUT null → 200 null; again → no audit, same `updated`, no event.
- **U-3 / C-15–C-18:** several tickets with mixed statuses/priorities/assignees; `?assignee=dana`, `?assignee=`, `?assignee=dana&status=open`, `?status=open&priority=urgent` (AND), `?assignee=nobody` → empty, with `limit`/`cursor` paging across filtered results.
- **U-4 / C-19–C-21:** `node bin/tickets.js --data FILE list` header has `ASSIGNEE`, an assigned row has the name; `--raw` columns 1–4 unchanged; `scripts/weekly-report.js` counts equal before/after; a hand-written old-format file (no `assignee`) lists without error.
- **U-5 / C-23:** the unmodified existing suite passes.
- **Errors C-3, C-4, C-5, C-8:** `""`, 65 chars, missing field, number/boolean/array/object, extra field → 400 and no change; resolved and closed tickets (name and null) → 409 with no audit and no event; unknown id → 404. Boundary: exactly 64 accepted.
- **C-22:** with `DATA_FILE`, assign, build a fresh store/app from the file, see the assignee and the still-pending event.
- **Must not forget in tests:** assertions on "no new event/audit/`updated` change" for every no-op and refusal; the lee-after-dana dedup case; `assignee` present on POST, GET, list, PATCH, transition responses; old-format ticket → null; tests must not assume trimming, placeholders, or the audit action name (the Open clauses); no fixed ports; stop everything started.
