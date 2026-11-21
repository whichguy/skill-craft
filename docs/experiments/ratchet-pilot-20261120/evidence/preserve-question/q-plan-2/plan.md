# Plan: ticket assignment

## Approach
The change follows the existing layering (README "How it fits together"): handler → validate → one store method → audit + outbox + save.

Touched parts:
- `src/tickets/validate.js`: new `assignee(body)`: `onlyFields(body, ['assignee'])`; `body.assignee === undefined` → InvalidError (a missing field is 400); `null` → `null`; otherwise `text(body, 'assignee', LIMITS.assignee)` with a new `LIMITS.assignee = 64`. `text` trims, refuses empty-after-trim, >64 and control characters (same rules as `requester`; settles C-3's Open the way the code already invites). Non-string/number/object/boolean → 400 via `text`'s "must be a string".
- `src/store.js`: new method `assign(id, assignee, actor)`. Order: `find` (404) → `isActive(ticket.status)` else ConflictError (409) → compute change `{assignee:{from, to}}` only if different → `apply(ticket, 'ticket.assigned', changes, actor, effects)`. `apply` already gives the no-op (no audit, no `updated`, no save, returns a copy), the audit entry, `updated`, and runs effects. Effect: when `to !== null`, `this.notify(ticket, 'ticket.assigned', to, at, key)` where key is ticket.assigned:<id>:<agent>. `create` adds `assignee: null` to the new ticket (not to `CREATED_FIELDS`). The constructor normalizes a ticket without `assignee` to `null`.
- `src/templates.js`: template `'ticket.assigned'` (subject `[T-0042] Assigned to you`, body names ticket id and title). Without it the event would retry and end dead (C-10).
- `src/app.js`: `router.put('/tickets/:id/assignee', ...)` → `validate.assignee(await body(req))`, `store.assign(...)`, 200. The router already has `put`.
- `src/tickets/query.js`: `parseListQuery` reads `assignee` when `params.has('assignee')`: `''` → `null` (unassigned), else the raw string, no validation. `matchesFilters` compares `(ticket.assignee ?? null) === value`.
- `src/persistence.js`: `ticketRecord` gains `assignee`; `readTicket` turns a missing/undefined `assignee` into `null` and refuses (DataFileError) a value that is neither null nor a non-empty string of ≤64. `VERSION` stays 1.
- `src/format.js`, `bin/tickets.js`: ASSIGNEE column in the table; `show` prints an `assignee` line; usage text. `--raw` decision below.
- Docs/housekeeping: `docs/api.md` (endpoint, `assignee` field, filter), README, CHANGELOG + `package.json` version 1.5.0 (CONTRIBUTING "Releases"), optionally a decision record. No product behaviour depends on them.
- Tests (new files only): `test/assign.test.js` (HTTP + store), additions in new files for query/persistence/format/CLI; never edit existing test files.

Data: ticket = existing fields + `assignee: string|null`. Audit: `{action:'ticket.assigned', changes:{assignee:{from,to}}}` (audit `readAudit` accepts any action; `from:null` is fine). Outbox event: `{type:'ticket.assigned', to:<agent>, ticket, key, data:{title}}`.

## Decisions
- **One action name `ticket.assigned` for assign and unassign** (rather than `ticket.unassigned`): one store method, the change record shows from/to; C-13's Open allows it. Rejected: two names, more code and no benefit.
- **Reuse `text()` rules for the name** (trim, reject empty/whitespace-only, control chars): the CLI's `--raw` is tab-separated and a tab/newline in a name would corrupt it, so control characters must be refused. The stored name is the trimmed one. Rejected: raw length check only.
- **Outbox key includes the agent: `ticket.assigned:<id>:<agent>`**: the default `type:ticket` key would let a pending notice for `dana` swallow the one for `lee` (C-11). Same agent twice while pending collapses to one (Open). Rejected: unique key per call (a no-op already enqueues nothing, but dana→lee→dana would double-notify).
- **Notification `to` is the agent name as stored**; no address mapping (C-10 Open).
- **Unassign notifies nobody; the previous agent is not told** (C-12, C-11 Open).
- **Check order: validate body (400) → 404 → 409 → no-op.** Resolved/closed + same value is a 409 (C-5), so the state check precedes the no-op check. Matches `update`/`transition`.
- **`matchesFilters` becomes `every`.** It currently uses `some` (src/tickets/query.js), contradicting docs/api.md ("matches every filter given") and C-17; it is unobservable today only because one filter at a time is tested. Existing tests pass either way. Rejected: leaving it, which would make `status=open&assignee=dana` list the union.
- **Empty `assignee=` → filter value `null`.** `matchesFilters` already skips only `undefined`, so `null` is a real filter. An agent name is never `null`, so no ambiguity.
- **Assignee filter is exact, case-sensitive, untrimmed, any text, no 400** (C-15, C-18). `assignee=%20dana` matches nothing.
- **`--raw` gets assignee as a 5th tab field** (placeholder `-` when unassigned) appended after title, so fields 1–4 keep their positions; the weekly report reads columns 1–3 only. Rationale: "the command-line listing". Alternative (leave raw alone) is also valid per C-20's Open; the 5th-field choice must be reported. Table: `ASSIGNEE` column after PRIORITY, placeholder `-`, TITLE stays last (last column is unpadded).
- **No new persistence version**: loading normalizes. Rejected: VERSION 2, which would make the previous version refuse files and the new one refuse old files.
- **Transitions never touch `assignee`** (C-26).

## Nuances
- **`matchesFilters` `some` bug (C-17).** Fix to `every`. Test with two filters where one matches and the other does not.
- **Persistence drops unknown fields (C-9).** `ticketRecord` whitelists fields: without adding `assignee` there, assignments vanish on the next save/restart and the CLI (which reads the file through the same record functions) would never show them. `readTicket` must default old tickets to `null` (otherwise `undefined` fails equality, `?assignee=` misses them, and JSON omits the key). Also the CLI builds `TicketStore` with `state` from `load()`, so normalization in `readTicket` covers it; normalizing in the constructor too covers stores built from other states (tests).
- **No-op returns the same shape (C-7).** `apply` returns a copy and skips everything when `changes` is empty; do not set `updated` or call `save`. Assign `null` on an unassigned ticket is a no-op 200 only if the ticket is open/in_progress; resolved/closed gives 409 (C-5/C-7 meet).
- **Mutation inside `apply` happens before effects**, so `notify` reads the updated ticket; pass the new agent as `to` explicitly, never `ticket.requester` (the default recipient everywhere else).
- **Outbox rejects empty `to`** (TypeError → 500). Validation guarantees a non-empty trimmed string; do not let `null` reach `notify`.
- **Missing field vs `null`**: `{}` is 400, `{"assignee": null}` is OK; check `=== undefined` first, not falsiness. Also `""` and `"   "` → 400. Arrays/`null` bodies already 400 in `readJson`. 64 characters counted after trim (JS length; a 64-char name is accepted, 65 refused).
- **Wrong-method message (C-24)**: adding PUT changes `methodsFor('/tickets/T-1/assignee')` only; do not register PUT on other paths. Existing router tests use their own router.
- **PATCH must still refuse `assignee`** (C-21): do not add it to `ticketPatch`'s allowed fields.
- **Audit on create unchanged (C-23)**: do not add `assignee` to `CREATED_FIELDS`; test/api.test.js and the CLI history show it.
- **Audit `changes` describe in CLI `show`**: `describeChanges` prints `assignee dana` for from-null and `assignee dana -> null` for unassign; acceptable. A from-`null` is data, not absence.
- **CLI table**: `String(null)` would print `null`; the column value must be `ticket.assignee ?? '-'`. Alignment: header/width computed from rows, so no further change. Empty-list message `no tickets` untouched.
- **Raw line**: `RAW_COLUMNS.map(c => ticket[c])` would join a `null` as an empty string (Array.join renders null as ''), producing a trailing empty field; map to `-` explicitly if a 5th column is kept.
- **Notification delivery (C-10)**: the worker is off in tests (interval 0); tests drive `service.worker.tick()` and read `service.notifier.delivered` and `GET /admin/outbox`. Check the status is `sent`, not `dead`.
- **Restart tests**: use `DATA_FILE` in a temp dir (os.tmpdir under TMPDIR), create the service twice with `createService`, stop the first. Old-file test: write a version-1 document with no `assignee` by hand (or strip it from a saved one).
- **Race/ordering**: the store is synchronous, so each PUT is atomic; no locking is needed. Handlers must call exactly one store method.
- **Stopped ticket keeps assignee** when resolved/closed (C-26); the assigned-agent's tickets listing therefore includes finished tickets unless `status` is given.
- **Ids are case and encoding sensitive**; `PUT /tickets/T-0042/assignee` with percent-encoded segments is decoded by the router already.

## Build order
1. `query.js`: `every`, `assignee` filter; quick unit check with `node -e` or a new `test/assignee-query.test.js`; run `npm test`.
2. `validate.js` `assignee`; `store.js` (`assign`, `create`, constructor), `templates.js`; unit-check the store (audit, outbox, no-op, 409, 404).
3. `persistence.js` record + read; check save/load round trip and an old file.
4. `app.js` route; HTTP check with `withService`.
5. `format.js`/`bin/tickets.js`; run the CLI against a saved file and run `scripts/weekly-report.js` for unchanged counts.
6. New tests under `test/` (see below); docs, CHANGELOG, version.
7. Full `npm test`, confirming existing test files are byte-identical (`git diff --stat test/`).

## How we will know
- **U-1** (C-1, C-3, C-5, C-6, C-10, C-11, C-13, C-14): PUT with a name on an open and an in-progress ticket → 200, `assignee` set, `GET` agrees; audit has one entry with from/to and the `X-Actor`; `updated` moves with the clock; outbox pending has `to: dana`; `worker.tick()` → notifier delivered to `dana` mentioning the ticket id, none dead. 64 vs 65 chars, `""`, number, object, boolean, `{}`, array body, extra field → 400 and no change. resolved/closed → 409, nothing changes or is enqueued. T-9999 → 404. dana→lee→dana pending includes a `lee` notification.
- **U-2** (C-2, C-7, C-12): unassign → 200 null, audit entry, no new notification; again → 200 with `updated` and audit count unchanged; same-agent re-assign → no audit, no outbox, `updated` same.
- **U-3** (C-8, C-9, C-21, C-23, C-26): `assignee: null` on 201, GET, list items, PATCH and transition responses; PATCH with `assignee` → 400; transitions keep assignee; restart with `DATA_FILE` keeps it; a v1 file without `assignee` loads and shows null.
- **U-4** (C-15–C-18): mix of tickets; `assignee=dana`, `assignee=` (empty), `assignee=nobody` (200, empty), combined with `status`/`priority` (AND, with a case where OR would differ), paging with `limit` and `cursor` across a filter, bad `status` still 400.
- **U-5** (C-19, C-20, C-25): run `main(['--data', file, 'list'], {out})` or the script: ASSIGNEE header and values and a placeholder; `--raw` fields 1–4 unchanged (tests check only those); `scripts/weekly-report.js --json` counts equal before/after; `--status` filter; `show`; exit codes.
- **U-6** (C-21, C-24, C-22): all existing test files unmodified and green; wrong-method 404; `npm test` runs new files.
- A test must not forget: not asserting open-point answers (whitespace handling, action name, raw 5th column, placeholder text, check order 400 vs 409, notification wording or type), using free ports (port 0 via `withService`), cleaning temp dirs, and the two-filter `every` case.

## Preserved behaviour
- Error envelope `{error:{code,message}}`, 400/404/409 mapping, unknown fields refused — `src/errors.js`, `src/tickets/validate.js`, docs/api.md, CONTRIBUTING.md (C-4, C-21).
- Create/PATCH/transition semantics, no-op = no audit/notification/`updated` change, closed tickets reject PATCH — `src/store.js`, `docs/api.md`.
- Creation and resolved notifications to the requester, outbox keys and dedupe, templates, dead-letter after 5 attempts — `src/outbox.js`, `src/templates.js`, `src/worker.js`, docs/operations.md.
- `ticket.created` audit entry fields — `src/store.js` `CREATED_FIELDS` (C-23).
- Cursor-paged listing in id order, `status`/`priority` validation, `limit` 1–100, ignored unknown params — `src/tickets/query.js`, `test/query.test.js` (C-17/18/21).
- Router: method-not-allowed reported as 404 with allowed methods — `src/router.js`, `src/app.js` (C-24).
- Data file: version 1, atomic write, strict load validation, older files still load — `src/persistence.js`, docs/decisions/0008 (C-9).
- Command line: read-only, `--raw` positions 1–4 (id, status, priority, title), weekly report by position, exit codes 0/1/2 — `README.md`, `src/format.js`, `scripts/weekly-report.js`, `bin/tickets.js` (C-20, C-25).
- No dependencies, CommonJS with named exports, worker interval 0 turns off background work — `CONTRIBUTING.md`, `package.json`.
- Not settled by what is here: whether the filter `matchesFilters` using `some` is relied on by anything (nothing found: the existing tests use single filters); the docs say `every`, so the plan fixes it. Whether `show` should print the assignee is not settled; planned yes (additive).
