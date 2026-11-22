# Product reader answer (w1/d3)

All files are under ~/e2e-runs/r-20261121-2c3d50/w1/d3/work.

## 1. What the product does

a. Hours: one environment variable per priority, `DUE_HOURS_URGENT|HIGH|NORMAL|LOW` (src/config.js `loadDueHours`:
`wholeNumber(env, \`DUE_HOURS_${priority.toUpperCase()}\`, hours, { min: 1, max: 8.64e15 / HOUR_MS })`; README.md
Configuration table). Defaults 4/24/72/168 (`DEFAULT_DUE_HOURS`). Read once when the process starts (`loadConfig`) and
only when `DUE_TIMES === 'on'`; a change takes effect at the next restart. It applies to new tickets and to missing
deadlines in a backfill (README: "apply to new tickets and missing deadlines in a backfill"). The backfill script
reads the same variables from its own environment (scripts/backfill-due.js `loadDueHours()`).

b. Invalid hours: `wholeNumber` throws `ConfigError` ("DUE_HOURS_X must be a whole number, not ..." for anything not
`^\d+$`, such as `1.5`, `-3`, `abc`; "must be from 1 to ..., not 0" for 0 or too large), naming the variable. That
stops the service at start (README: "A value the service cannot use ... stops it at start with a message naming the
variable"), and makes the backfill script exit 2. Empty/unset takes the default. The hours are only validated when
`DUE_TIMES=on` (`env.DUE_TIMES === 'on' ? loadDueHours(env) : null`), so with the switch off a bad value is ignored.

c. Largest: yes, `8.64e15 / HOUR_MS` = 2,400,000,000 hours (src/config.js `max: 8.64e15 / HOUR_MS`; 8.64e15 ms is
the JS Date limit). Also a ticket whose created time plus its hours falls outside the Date range is refused:
src/store.js `dueAt` throws "due time for <id> is outside the supported date range" (InvalidError on create,
DataFileError in the backfill).

d. The tickets already in the file are given due times only by the operator running the backfill with the service
stopped: `DATA_FILE=... npm run backfill:due` (scripts/backfill-due.js, `store.backfillDueTimes`; docs/operations.md
"Backfilling ticket due times"). Due = created + hours for the ticket's stored priority, saved atomically; tickets
that already have a due are left alone, so it can be rerun. Nothing assigns them at server start or automatically.

e. Started with `DUE_TIMES=on` and some ticket has no due: it refuses to start. src/store.js `TicketStore.open`:
`if (dueHours && state?.tickets.some((ticket) => ticket.due === undefined)) throw new DataFileError(persistence.file,
'ticket due times are missing; stop the writer and run npm run backfill:due')` (also docs/operations.md: "An enabled
service refuses to start if an existing file still contains tickets without due times"). An empty store starts fine.

f. No. src/store.js `list`: overdue = `isActive(ticket.status) && Date.parse(ticket.due) < now` (strict `<`), so a
ticket due exactly now is not overdue; it is overdue from the next instant.

g. Other limits/steps not in the request:
- `overdue=true` lists only active tickets (`isActive`: open, in_progress per src/tickets/states.js `ACTIVE`);
  resolved/closed tickets past due are never overdue.
- The overdue filter and the `due` field are hidden when the switch is off (src/app.js `visibleTicket`,
  `overdue = dueTimes && ...`): with off, `overdue=true` is silently ignored.
- Only the exact string `on` enables it (`env.DUE_TIMES === 'on'`); `ON`, `1`, `true` mean off, with no message.
- Due is computed once at create from the priority then; a later priority change does not move it (src/store.js
  `create` sets it once; comment on `dueAt`).
- The backfill requires `DATA_FILE` set and existing (exits 2 otherwise) and the file's operator must stop the writer
  and back up first (docs/operations.md). An optional `--from <snapshot>` recovers due times after a writable
  rollback to 1.4.0, and refuses if a snapshot ticket has a different creation time (store.js
  `backfillDueTimes`: "rollback snapshot has a different creation time").
- Rollback: 1.4.0 reads the file but its next save drops `due`; keep a pre-rollback copy (docs/operations.md
  "Rolling back to 1.4.0"). With the switch off, the current release keeps stored deadlines on save
  (src/persistence.js `...(ticket.due === undefined ? {} : { due: ticket.due })`).
- The CLI `bin/tickets.js` shows the DUE column only with `DUE_TIMES=on`.

## 2. Against the rows

Letters:
- a: row 1
- b: no row (row 1 says only that the values are positive whole hours, not what a bad one does)
- c: no row
- d: row 3
- e: no row (row 3 gives the order, backfill then flag on, but does not say the service refuses to start otherwise)
- f: row 2
- g: no row

Rows:
- row 1 (one DUE_HOURS_<PRIORITY> env setting per priority, positive whole hours): as the row says. Not a config file;
  `min: 1` and whole numbers via `/^\d+$/` in src/config.js.
- row 2 (overdue only from the first instant after due): as the row says. `Date.parse(ticket.due) < now` in
  src/store.js `list`; a ticket due exactly now is excluded.
- row 3 (stop the writer, explicit backfill, then start with flag on; not an automatic migration before listening):
  as the row says. scripts/backfill-due.js plus the refusal in `TicketStore.open`; no automatic migration exists.

not in any row: b, c, e, g
rows the product contradicts: none
