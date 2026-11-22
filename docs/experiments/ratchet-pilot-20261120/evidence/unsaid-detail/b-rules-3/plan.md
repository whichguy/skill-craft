# Plan: ticket assignment

## Approach

Assignment is one more audited change in the store, with one more outbox notification, one more validator, one more route, one more filter and one more table column. Nothing new is invented; each piece follows the pattern beside it.

Parts touched:

- `src/tickets/validate.js`: new `assignment(body)`. It calls `onlyFields(body, ['assignee'])`, then requires the key `assignee` (`Object.hasOwn`). Null is returned as null. Anything else goes through the existing `text()` helper, which trims, refuses blank, refuses control characters and caps the length. The cap needs its own `LIMITS.assignee = 64`, the requester precedent. This is the answer to the Open point in C-3.
- `src/store.js`: new `assign(id, assignee, actor)`.
  - `find`; if `!isActive(status)` throw `ConflictError` (`isActive` already exists in `states.js`).
  - `changes = ticket.assignee === assignee ? {} : { assignee: { from: ticket.assignee, to: assignee } }`.
  - Call `this.apply(ticket, 'ticket.assigned', changes, actor, effects)`. The effect calls `notify` only when `assignee !== null`. `apply` already gives no-op, audit, `updated` and save.
  - `create()` adds `assignee: null` to the new ticket object. `CREATED_FIELDS` is NOT changed.
  - The constructor normalises loaded tickets with `assignee: ticket.assignee ?? null`.
- `src/store.js` `notify` takes a key argument already. Use key `ticket.assigned:${id}:${agent}`.
- `src/templates.js`: template `'ticket.assigned'`. Subject `[T-0042] Assigned to you`, body names the ticket id and title. Without it the event goes dead after 5 tries (C-12).
- `src/persistence.js`: add `assignee` to `ticketRecord` (otherwise it is silently dropped on every save, since the record function is a whitelist). `readTicket` must default a missing `assignee` to null (`record.assignee ?? null`) and check it is null or a non-empty string. `ticketRecord` runs inside `readTicket` on the raw record, so do the default there or in `ticketRecord` itself.
- `src/tickets/query.js`: `parseListQuery` reads `assignee` with `params.has('assignee')`; value `''` becomes `null` (unassigned), any other string is kept. It never throws. `matchesFilters` changes `some` to `every` (C-18) and compares `(ticket[field] ?? null) === value`. The existing code already skips `undefined` filter values, and `null` is not skipped, so null works as "unassigned".
- `src/app.js`: `router.put('/tickets/:id/assignee', ...)`. `Router.put` already exists. It reads the body, validates it, calls `store.assign(params.id, assignee, actorOf(req))` and answers 200. Handlers change nothing themselves.
- `src/format.js`: add `{ title: 'ASSIGNEE', value: t => t.assignee ?? '' }` to `TABLE_COLUMNS`. Leave `RAW_COLUMNS` alone (answer to the Open point in C-21: `--raw` unchanged). `details()` for `show` may stay as is; a line for the assignee is allowed but not required.
- `bin/tickets.js`: no change needed. Its `list` uses `table()`. It builds `TicketStore` from the loaded state, so the normalisation in the constructor covers old files.
- Docs: `docs/api.md` (new endpoint, `assignee` field, filter, the audit action and notification), README command-line paragraph, CHANGELOG, and `CONTRIBUTING.md` if it lists notification types. Optionally decision 0009 for the per-agent outbox key. Keep these short.

Data: a ticket gains `assignee: string | null`. The data file stays version 1 and gains an optional field, so old files load and new files stay readable by the same version check.

## Decisions

- **Assignee rules mirror the text fields**: trimmed, 1 to 64 characters, no control characters. Why: this is the nearest precedent, tab characters would break `list --raw`, and an untrimmed name would make `"dana "` and `"dana"` two agents. Rejected: accepting any non-empty string (breaks the tab-separated output and invites mismatched names). Tests only use short names such as `dana`, so either answer passes.
- **Audit action `ticket.assigned`** for both assign and unassign. Why: one action, with `from` and `to` showing which. Rejected: `ticket.unassigned` as a second action; it adds nothing the changes object does not say.
- **Notification type `ticket.assigned`**, `to` the agent's name unchanged (the name is the address), `data: { title }`. Wording: "Ticket T-0042 "title" was assigned to you."
- **Outbox key includes the agent**: `ticket.assigned:<id>:<agent>`. Why: the default key is per type and ticket, so while the worker is off, assigning to `dana` then `sam` would drop `sam`'s notice (C-14). Rejected: appending a counter or timestamp to the key, which would defeat deduplication for the same agent. The dana, sam, dana case leaves one pending notice for dana, which C-14 allows.
- **Reassignment notifies only the new agent; unassign notifies nobody** (C-13). No notice to the previous agent, to keep the Open point closed in the narrow way.
- **Order of checks in `assign`**: ticket exists (404), then body validity (400, done by the handler before the store is called), then state (409), then no-op. Order of faults across a request with several is unspecified, so the 404-before-400 question does not matter for tests that combine at most one fault. Keep the existing pattern: validate in the handler, then the store finds the ticket.
- **Repeat on a resolved or closed ticket answers 409.** The state check runs before the no-op check. This is the simplest reading of "only open and in-progress tickets can be assigned" and the C-5 Open point; tests do not check it.
- **Filter value null means unassigned** inside `filters`, which keeps the `{ field: value }` shape of `matchesFilters`.
- **`list --raw` is unchanged.**
- **No assignee in PATCH or POST bodies.** `ticketPatch` and `newTicket` keep refusing the unknown field.

## Nuances

- **`matchesFilters` uses `some`** (C-18). The existing tests pass with `some` only because each of them gives one filter. With the new filter, `?status=open&assignee=dana` would wrongly list every open ticket and every ticket of Dana's. Change to `every`. This also changes `?status=open&priority=urgent`, as the documented rule says. Add a test of two filters that differ; the existing tests do not cover it.
- **Empty `assignee=` versus absent**: `params.has` is true for `assignee=`, and `params.get` returns `''`. Do not use truthiness (`if (params.get('assignee'))`). `?assignee` with no `=` is also present and empty, so it means unassigned.
- **`matchesFilters` skips `undefined`** filter values but must not skip `null`. Old tickets loaded without the field have `undefined`; compare with `?? null`.
- **Persistence whitelist** (C-10): `ticketRecord` lists fields explicitly, so without the edit the assignee is dropped on the first save and the restart test fails. The `readTicket` default is needed for C-11, since `ticketRecord(old)` yields `assignee: undefined`, which `JSON.stringify` drops and the rest of the code would read as missing. Also check the loaded value: a hand-edited non-string, non-null or empty string refuses the file with the file's usual message (the load checks exist so a file cannot reach a state the service could not).
- **Existing store test at `test/store.test.js:37`** deep-compares a created ticket's audit entry. Do not add `assignee` to `CREATED_FIELDS`; creating is not an assignment and a new ticket has no from/to to show. Same for `test/store.test.js:22`, which picks named fields and is safe.
- **The no-op must not touch `updated`, audit or outbox** (C-7), which `apply` guarantees only if `changes` is empty. Compare against `ticket.assignee ?? null`; a ticket from an old file has `undefined` before the constructor fix, and unassigning it would otherwise be recorded as a change.
- **Snapshot and copies**: `get`, `list` and `create` return `{ ...ticket }`, so `assignee` flows through. The `apply` loop sets `ticket[field] = to`, so field name `assignee` needs no special case.
- **The notification effect runs inside `apply`, before `save`**, so the ticket, audit entry and outbox event land in one save. Do not call `notify` after `apply` returns (C-15, and crash safety).
- **Unassign on an already-unassigned ticket**: no-op 200. The body `{"assignee": null}` is valid even though it is falsy; check `hasOwn`, not truthiness.
- **JSON `null`, arrays, numbers**: `readJson` already refuses a body that is not an object. `{"assignee": []}` and `{"assignee": {}}` hit `text()`'s "must be a string" error.
- **PUT is already supported by `Router`** and `methodsFor` will list PUT in the 404/405 hint. Existing tests of that message are for other paths. The router regex `([^/]+)` matches `/tickets/T-1/assignee`, and the `/tickets/:id` route does not match it (the regex is anchored), so there is no clash.
- **Worker delivery**: a type with no template goes dead. Check with a test that calls the worker tick (see `test/worker.test.js`, `test/notifier.test.js` for how) and then looks at `/admin/outbox` for `sent` with `to: "dana"`.
- **Table alignment**: `table()` pads every column but the last. An empty ASSIGNEE cell needs `''`, not `null`: `String(null)` would print "null". Keep TITLE last because it is unpadded.
- **`bin/tickets.js` opens a store without persistence**: it never saves, so normalising in the constructor changes nothing on disk.
- **`npm test` is `node --test`**, which picks up every `test/*.test.js`. New files need that suffix and must use `withService` from `test/helpers.js` (port 0, worker off). Do not edit the existing tests.
- **Weekly report** reads `--raw` columns 2 and 3 by position, and stays valid because `RAW_COLUMNS` is untouched. Test it with a data file that holds assigned tickets.

## Build order

1. `matchesFilters` to `every` plus the `assignee` filter in `parseListQuery`. Run the existing tests; add unit tests in a new `test/assignee-query.test.js`.
2. Persistence: `assignee` in `ticketRecord`, default and check in `readTicket`; store constructor normalisation and `create` sets null. Run all tests; check an old-format file loads and a round trip keeps the value.
3. Validator `assignment` and `store.assign`, with the `ticket.assigned` template and the per-agent key. Store-level tests: assign, unassign, no-op, 409 states, audit entry, outbox contents, the dana-sam-dana order.
4. Route in `app.js`. API tests with `withService`: statuses 200/400/404/409, the `X-Actor` header in the audit, filters with paging, `/admin/outbox`, and `assignee` on every ticket-returning route.
5. Notification delivery through the worker (tick, then `notifier.delivered` or the sent list), restart persistence with `dataFile` in a temp dir under TMPDIR.
6. Table column in `format.js`; a CLI test calling `main(argv, { out })` on a data file, checking the `ASSIGNEE` title, the name on the right row, and that `--raw` lines are unchanged. Run `npm run report:weekly` against the same file.
7. Docs and changelog. Run `npm test` in full.

## How we will know

- **U-1** (C-1, C-8, C-12, C-14): PUT with `dana` on open and on in-progress tickets gives 200 and `assignee: "dana"`; GET agrees; `/tickets/:id/audit` has one entry with `changes.assignee {from: null, to: "dana"}` and the `X-Actor` actor; `/admin/outbox` has a pending event `to: "dana"` for the ticket; after a worker tick it is sent and its text contains the ticket id.
- **U-2** (C-2): null on an assigned ticket gives 200 and `assignee: null`; audit has `from: "dana", to: null`; no notice.
- **U-3** (C-7): repeat both forms; `updated`, audit length and outbox length are all unchanged. Use a manual clock advanced between calls so a changed `updated` would show.
- **U-4** (C-3, C-4, C-5, C-6): bodies `{"assignee": ""}`, `"   "`, `5`, `true`, `{}`, `[]`, `{}` with no field, `{"assignee":"a","x":1}`, a non-object body, and an empty body give 400 `invalid` with the ticket unchanged; resolved and closed tickets give 409 `conflict` (reach them with the transition route); unknown id gives 404 `not_found`; each answer is in the error envelope.
- **U-5** (C-16 to C-19): tickets with mixed assignees and statuses; `?assignee=dana`, `?assignee=` and `?assignee=nobody` (empty items, next null), `?status=open&assignee=dana`, `?status=open&priority=urgent`, and paging with `limit=1` and `cursor`.
- **U-6** (C-20, C-21): the CLI table has `ASSIGNEE`, the name on its row and a blank for the unassigned one, with the other columns still present; the `--raw` first four columns are unchanged; the weekly report counts match.
- **U-7** (C-9, C-10, C-11, C-22): an old data file (written by hand without `assignee`) starts, lists `assignee: null` everywhere, and filters as unassigned; stop and restart on a data file and see the values survive; the existing suite passes unmodified.

Test must-nots: do not assert the audit `action` name, the notification `type` or exact text, trimming/length behaviour, the repeat-on-resolved answer, or a `--raw` fifth column; do not combine two faults in one request; do not start servers on fixed ports (use `withService`); do not touch the existing test files.
