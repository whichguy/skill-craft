# Product reader answer (w1/d1)

Paths are under PRODUCT (~/e2e-runs/r-20261121-2c3d50/w1/d1/work). Nothing was run; this is from reading the code.

## 1. What the product does

**a. How the help desk changes the hours.** Four environment variables, `DUE_HOURS_URGENT`, `DUE_HOURS_HIGH`, `DUE_HOURS_NORMAL`, `DUE_HOURS_LOW` (defaults 4/24/72/168). They are read once at process start and take effect after a restart, with no code change. `src/config.js`: `wholeNumber(env, \`DUE_HOURS_${priority.toUpperCase()}\`, hours, { min: 1, max: MAX_DUE_HOURS })`; `README.md` configuration table. They apply only to tickets that get a due time afterwards, because `docs/api.md` says "Editing the priority or changing the configured hours leaves an existing deadline intact", and `src/store.js` `backfillDueTimes` skips any ticket where `ticket.due !== undefined`.

**b. What an invalid setting does.** The service refuses to start. `src/config.js` `wholeNumber` throws `ConfigError` for a value that is not `^\d+$` (decimals, negatives, text) or is outside `min..max`, so 0 is refused. `src/server.js` `main` logs `cannot start: <message>` and exits with code 2. An unset or empty variable takes the default.

**c. A largest number of hours.** Yes: `MAX_DUE_HOURS = 2_400_000_000` in `src/tickets/due.js`, enforced as `max` in `src/config.js`. Note that the limit is not safe. 2.4e9 h x 3.6e6 ms = 8.64e15 ms, which is the entire JS Date range, so any ticket created now plus that value is outside the range. `dueAt` calls `.toISOString()` on an invalid date and throws `RangeError`. Backfill catches it and turns it into a startup refusal (`store.js`: "cannot calculate due time for <id>: resulting date is out of range"). `create()` in `store.js` has no such catch, so POST /tickets for that priority would end as a generic failure through `app.js`'s `if (!(error instanceof AppError)) log.error(...)` path. I judged that by arithmetic and did not run it. The practical ceiling is somewhat below the stated maximum.

**d. Who gives existing tickets their due times, and when.** The service itself, at startup, before it listens. `store.js` `TicketStore.open` calls `backfillDueTimes()` when `state && dueHours` (a data file was loaded), and `dueHours` is always set (`server.js`: `config.dueHours ?? DEFAULT_DUE_HOURS`). It computes `dueAt(ticket.created, hours[priority])` for every ticket with no `due`, then does one `save()`. It adds no audit entries or notifications (`docs/decisions/0009-ticket-due-times.md`). It happens whether or not `DUE_TIMES` is on (`docs/operations.md`: "Leave `DUE_TIMES` unset for a dark rollout. On startup, the service assigns every missing deadline ... before listening"). New tickets get `due` at creation even with the flag off (`store.js` `create`: `if (this.dueHours) ticket.due = ...`). The CLI (`bin/tickets.js` `openStore`) builds a store without persistence and does not backfill.

**e. `DUE_TIMES=on` with a ticket that has no due time.** Nothing special is refused. The startup backfill in (d) fills it and saves before listening, exactly as when the flag is off, and `docs/operations.md` step 2 says "An enabled startup also fills and saves any missing deadlines before serving." The only refusal is the out-of-range date case in (c)/(d), which stops startup with a `DataFileError`.

**f. A ticket due exactly now.** No, it is not overdue. `src/tickets/due.js`: `isOverdue` is `isActive(ticket.status) && Date.parse(ticket.due) < now`, strictly less than. `docs/api.md`: "A ticket becomes overdue immediately after its due time."

**g. Other limits, refusals or operator steps the request does not mention.**
- Only `open` and `in_progress` tickets can be overdue; resolved and closed ones never are (`due.js` `isActive`; `states.js` `ACTIVE`). The request did not say so.
- `overdue` is silently ignored when `DUE_TIMES` is off or the value is anything but `true` (`src/tickets/query.js`: `if (dueTimes && params.get('overdue') === 'true')`; `docs/api.md`). There is no error.
- A due time is also saved while the flag is off, but hidden from output (`store.js` `ticketView` deletes `due` when `!dueTimes`).
- The CLI: with `DUE_TIMES=on`, `list` adds a `DUE (UTC)` column and `show` a `due` line, shown only when the ticket has a saved due. `list --raw` stays four fields (`format.js` `RAW_COLUMNS`). The CLI never backfills, so a ticket with no saved due shows a blank cell and no `due` line.
- Rollback: release 1.4.0 loads the file but drops `due` when it saves. `docs/operations.md` tells operators to stop the writer and keep a copy of the upgraded file before rolling back, and to keep one writer per file. That copy is the only way to keep the historical due times. After 1.4.0 has written the file, the due times are lost and the new release recomputes them from the creation time on the next start, so a changed `DUE_HOURS_*` can give different values.
- Backup before upgrade, and verifying the data file after the first startup, are operator steps (`operations.md` steps 1 and 2).
- A malformed `due` in the data file (not a valid timestamp) stops startup (`persistence.js` `readTicket`: `time(ticket.due, ...)`).

## 2. Against the rows

For each of a to g:

- a: row 1
- b: no row (row 1 says "positive whole hours" but does not say what a bad value does)
- c: no row
- d: row 4
- e: row 4 (it says the startup fills missing values before listening, "even with the flag off", so the flag-on case is covered by the same startup step; it does not mention `DUE_TIMES=on` itself)
- f: row 2
- g: no row (the row 3 CLI decision is covered, but the other items in g are not: overdue only for open/in-progress, the silent ignore of `overdue`, the 1.4.0 rollback losing `due`, the out-of-range startup refusal)

For each row:

1. Row 1 (positive whole hours in `DUE_HOURS_<PRIORITY>` at startup): as the row says. `config.js` takes whole numbers from 1 up, read in `loadConfig` at start.
2. Row 2 (overdue strictly after the timestamp): as the row says. `Date.parse(ticket.due) < now`. The row does not mention that only active tickets can be overdue, but it does not contradict it.
3. Row 3 (CLI human list and show can display due with the flag on; raw stays four fields): as the row says. `bin/tickets.js` `list` adds `DUE_COLUMN` when `options.dueTimes`; `format.js` `details` adds `due`; `RAW_COLUMNS` is id, status, priority, title.
4. Row 4 (the first new startup fills missing values before listening, even with the flag off): as the row says. `store.js` `open` calls `backfillDueTimes` regardless of `dueTimes`, and it runs before `start()` listens.

not in any row: b, c, g
rows the product contradicts: none
