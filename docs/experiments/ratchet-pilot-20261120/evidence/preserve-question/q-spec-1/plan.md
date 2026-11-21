# Plan: ticket assignment

## Approach

The change follows the existing layering (README "How it fits together"): the handler validates and calls one store method; the store applies, audits, enqueues and saves.

Parts touched:

- `src/tickets/validate.js`: new `assignment(body)` returning `string | null`. `onlyFields(body, ['assignee'])`, then require the key (`Object.hasOwn`), `null` passes, otherwise the value goes through the existing `text(body, 'assignee', 64)` helper.
- `src/app.js`: `router.put('/tickets/:id/assignee', ...)` (the router already has `put`): `validate.assignment(await body(req))`, then `store.assign(params.id, assignee, actorOf(req))`, answered 200.
- `src/store.js`:
  - `create` sets `assignee: null`. Do not add it to `CREATED_FIELDS`, or the creation audit entry changes.
  - The constructor normalizes `assignee: ticket.assignee ?? null` for loaded tickets.
  - New `assign(id, assignee, actor)`, described below.
- `src/templates.js`: a `ticket.assigned` template. Without it the event is retried and goes dead.
- `src/persistence.js`: `ticketRecord` keeps `assignee`; `readTicket` validates it. VERSION stays 1.
- `src/tickets/query.js`: the `assignee` filter in `parseListQuery`, and `matchesFilters` changed from `some` to `every`.
- `src/format.js`: an ASSIGNEE column in `TABLE_COLUMNS`; `details` shows assignee. `RAW_COLUMNS` is untouched.
- `bin/tickets.js`: no change is needed, because the table comes from `format.js`.
- Docs: `docs/api.md` (endpoint, the `assignee` field, the filter), README (CLI), CHANGELOG, and a version bump to 1.5.0 (CONTRIBUTING requires the bump). Optionally a decision record `0009` for the notification key. Only the status of a decision record may be edited, so do not edit 0006.

Data: a ticket gains `assignee: string | null`. The audit entry has `changes: { assignee: { from, to } }`. The outbox event is `{ type: 'ticket.assigned', to: <agent>, ticket: id, key: 'ticket.assigned:<id>:<agent>', data: { title } }`.

### `store.assign(id, assignee, actor)`

1. `find` the ticket (404).
2. If `!isActive(ticket.status)`, throw `ConflictError` (409), before the no-op check.
3. Build `changes = ticket.assignee === assignee ? {} : { assignee: { from: ticket.assignee, to: assignee } }`.
4. Return `this.apply(ticket, action, changes, actor, effects)`. `apply` already gives the no-op behaviour: no audit entry, no `updated`, no notification, and no `save` either.
5. The effect, only when `assignee !== null`, is `this.notify(ticket, 'ticket.assigned', assignee, at, `ticket.assigned:${id}:${assignee}`)`.

## Decisions

- **Reuse `text()` for the agent name.** The name is trimmed, must be non-empty, at most 64 characters after trimming, and may have no control characters. This resolves the C-3 `Open:` the same way as `requester`. Control characters matter because the name is printed in the tab-separated CLI output and used as `to`. Rejected: raw length checking, which would store `"  dana "` and break exact-match filtering.
- **Dedupe key is `ticket.assigned:<id>:<agent>`, not the default `type:ticket`** (C-11). With the default key, assigning dana and then lee while dana's message is pending returns dana's event and lee is never told. Including the agent keeps "dana → lee → dana" at one pending dana event, and dana was told. Rejected: no dedupe (the key is mandatory) and a unique key per assignment (it would send dana two mails for a flip-flop).
- **Audit actions are `ticket.assigned` when the new value is a name and `ticket.unassigned` when it is null.** Tests accept any non-empty action. Rejected: one action for both, which is less readable in `show`.
- **Status check before the no-op check.** On a resolved or closed ticket every request gets 409, including a repeat of the current value (C-5 `Open:`). It is simplest and strictly follows "only open and in-progress can be assigned".
- **Validation (400) before the store lookup (404 and 409)**, as PATCH and transition already do. A bad body for an unknown id is therefore 400, and an invalid body for a closed ticket is 400, not 409.
- **No notification on unassign or reassign away** (C-12).
- **`to` is the agent name**, as given (C-10 `Open:`). No address mapping.
- **Filter semantics.** In `parseListQuery`, `params.has('assignee')` gives `filters.assignee = value === '' ? null : value`. The match is exact and case-sensitive (C-14). In `matchesFilters`, compare `(ticket.assignee ?? null) === value`, so a ticket object without the key (as in the existing unit test) counts as unassigned. `given` already keeps `null` because it only drops `undefined`.
- **`matchesFilters` uses `every`.** This is a real bug fix (C-17). The existing tests pass either way because they use one filter at a time.
- **No `--assignee` CLI option.** The request does not ask for it, and it would change usage text.
- **Data file stays version 1.** An older file has no `assignee`, which loads as null. A new file read by an old service has its unknown field dropped; no downgrade guarantee is needed.
- **Table column:** `ASSIGNEE` right after `REQUESTER`, with `-` when unassigned. `--raw` is unchanged (C-19).

## Nuances

- **Filter bug (C-17, U-4).** `some` today makes `?status=open&assignee=dana` return every open ticket plus every dana ticket. Fix it and add a unit test with two filters. Also test the cursor with combined filters: `limit=1` pages must hold exactly the matches.
- **Empty filter versus absent (C-15, C-16).** `assignee=` must give a `null` filter, not be ignored. `filters.assignee === undefined` is the only "absent". Do not write `if (value)`. Existing `status=` stays `invalid`.
- **Falsy-value traps.** In `assign`, compare with `===`, never truthiness. A `null` assignee must flow through `apply`. `apply` sets `ticket[field] = to`, so null is stored, not dropped.
- **Persistence (C-9).** `ticketRecord` names every saved field; if `assignee` is not added there, restart silently loses it. `readTicket` runs `ticketRecord` on the raw record, so use `record.assignee ?? null` in the shared function so an old file loads as null. Then validate: it must be null or a non-empty string of at most 64 characters, else `fail`. Also normalize in the store constructor, because store tests build state directly. A test must write an old-format file (no `assignee`) and load it.
- **Missing template.** Without `ticket.assigned` in `TEMPLATES`, the worker retries five times and marks the event dead. Subject and body must name the ticket (C-10). Test delivery with the worker's `deliverOutbox` job, or `service` helpers in `test/helpers.js`, not just the outbox contents.
- **Outbox and `data` (C-10).** `notify` puts only `title` in `data`. Keep it that way, so the existing `readEvent` validation holds.
- **Clock and `updated` (C-1, C-3/U-3).** `apply` writes `updated`. For the "unchanged" assertions the test must advance the manual clock between calls, or "unchanged" is vacuous. Check `src/clock.js` for the manual clock's advance method.
- **Refused requests change nothing (C-3, C-4, C-5, C-12).** Verify by reading the ticket, the audit and `/admin/outbox` afterwards. The 409 must not enqueue.
- **Body shapes (C-4).** A body that is `[]`, `null`, a string or empty is already refused by `readJson`. `{}` and `{"assignee": undefined}` (the key absent) and `{"assignee":"a","x":1}` need the explicit check. The value check must run after the `onlyFields` check. A name that is not a string (`5`, `true`, `{}`, `[]`) gives 400 `invalid`. `text()` already throws for non-strings.
- **Limits (C-3).** 64 characters accepted, 65 refused. Count after trim. Test exactly these boundaries with plain letters.
- **Other routes keep `assignee` refused (C-20).** `PATCH` still has `onlyFields(['title','priority'])`. `POST /tickets` must also still refuse `assignee`, so no assignee at creation.
- **Responses (C-8).** Every route returns a copy of the ticket from the store, so `assignee` appears on create, get, list, patch and transition once the ticket has the field. Check each route in a test, and check that a `PATCH` or transition on an assigned ticket keeps its assignee. It must not be reset.
- **Transitions and assignment.** A ticket that is assigned and then resolved keeps its assignee (nothing in the request says otherwise); a resolved ticket still shows it and can be filtered by it. `?assignee=` (unassigned) lists across all statuses (C-15).
- **Routing.** `/tickets/:id/assignee` has a `:id` segment followed by a fixed segment, which does not collide with `/tickets/:id/audit`. A `GET` on it falls into the router's 404 with the "answers PUT" message; fine.
- **CLI table (C-18).** `table()` pads by header width and cell length, so a longer name widens the column; the last column (TITLE) is not padded, and `ASSIGNEE` must not be last. `String(column.value(ticket))` must not print `null`. Use `ticket.assignee ?? '-'`. The table path is not covered by existing tests, so add one running `main(['list'], { out })` against a data file, or the CLI with `--data`. `--raw` first four columns must be unchanged, and the weekly report should be run once as a check.
- **`details`/`describeChanges`.** `describeChanges` with `from === null` prints `assignee dana`; with `to === null` it prints `assignee dana -> null`. Acceptable; optionally print `-`. Do not break the existing format for other fields.
- **Audit actor (C-13).** `X-Actor` passes through `actorOf`, so test with the header and without it (`system`).
- **Restart with pending notification.** The outbox is saved with the change in one `save()`, so a restart after assigning keeps the pending event. The test can reopen the store with the same file and read `outboxReport()`.
- **Existing behaviour that must not drift (C-20).** Do not modify any existing test file. New tests go in new files (for example `test/assignment.test.js`, with additions kept to new files rather than appended to existing ones). The creation audit entry still lists four fields. Test `api.test.js:180` expects an exact pending list, which remains true because creating a ticket does not assign.

## Build order

1. `query.js`: the `every` fix and the `assignee` filter, then run `npm test` (the existing suite must pass).
2. `store.js`, `persistence.js`, `templates.js`: the ticket field, `assign`, load and save, the template. Check by hand with a script that creates a store, assigns, saves, reloads, and renders the event.
3. `validate.js` and `app.js`: the route. Start a service on port 0 and exercise 200, 400, 404 and 409.
4. `format.js`: the table column; run the CLI on a data file; run `npm run report:weekly` and compare the counts with the previous ones.
5. New tests: `test/assignment.test.js` (API, store, outbox, worker delivery, persistence, filters), plus unit tests for validation, `matchesFilters` and `format`/CLI (in new files).
6. Docs, CHANGELOG, version bump; then `npm test` in full.

## How we will know

- **U-1 (C-1, C-3, C-4, C-6, C-8, C-10, C-11, C-13):** PUT with a name on an open ticket and on an in-progress ticket, giving 200 and `assignee` in the body and in a later GET. `updated` moves with the clock. The audit shows one entry with `assignee: {from: null, to: 'dana'}` and the actor. `/admin/outbox` shows one pending `to: 'dana'`; after `store`/worker delivery the notifier holds a message whose subject and body name the ticket. Then dana → lee before delivery leaves two events. The invalid bodies (65 characters, empty, `5`, `true`, `{}`, `[]`, missing key, extra field, non-object body) give 400, with the ticket, audit and outbox unchanged. An unknown id gives 404.
- **U-2 (C-2, C-5, C-12):** `null` on an assigned ticket gives null; the audit has `to: null`; no notification added. On resolved and closed tickets, both a name and null give 409 `conflict` with nothing changed.
- **U-3 (C-7, C-12):** repeat the same name; null on an unassigned ticket. Both give 200, with clock advanced so `updated` is demonstrably unchanged, and no new audit entry or outbox event.
- **U-4 (C-14 to C-17):** a mix of tickets across status, priority and assignee. `?assignee=dana`, `?assignee=` (any status), no parameter, `?status=open&assignee=dana`, `?status=open&priority=urgent` (not a union), a combined filter with `limit=1` and the cursor. Also the existing `status=` still gives 400.
- **U-5 (C-18, C-19):** create a data file through the store, run `node bin/tickets.js --data FILE list`; assigned shows the name, unassigned shows `-`; `list --raw` has the same four first columns; the weekly report counts agree.
- **U-6 (C-9, C-20, C-21):** restart on the same `DATA_FILE`: assignee and the pending event survive; an old-format file loads with null. All existing tests unmodified and green; `npm test` shows the new files running.

What a test must not forget: advance the clock for "unchanged `updated`" checks; check the outbox and audit after every refused and no-op request; check the notification is delivered and not merely enqueued; check an assigned ticket keeps its assignee through PATCH and transition; check the filter combination is "all", not "any"; use names without surrounding whitespace or control characters and not differing by case only (the `Open:` points); do not assert the audit action name, the wording of the message, or the unassigned marker beyond "not another ticket's name".
