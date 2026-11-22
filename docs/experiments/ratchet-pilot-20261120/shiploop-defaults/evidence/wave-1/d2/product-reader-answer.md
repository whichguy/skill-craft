# Product reader answer (run d2)

## 1. What the product does

**a. How the help desk changes the hours.** Four environment variables, `DUE_HOURS_URGENT`, `DUE_HOURS_HIGH`, `DUE_HOURS_NORMAL`, `DUE_HOURS_LOW` (README.md Configuration table; src/config.js `wholeNumber(env, \`DUE_HOURS_${priority.toUpperCase()}\`, hours, { min: 1, max: MAX_DUE_HOURS })`). They are read once by `loadConfig()` when the process starts, so a change takes effect only after a restart (docs/operations.md "Enable due times" step 2: "set the desired `DUE_HOURS_*` values in the service environment"). A changed value applies only to tickets created or backfilled after that restart; README: "Changing the hours or a ticket's priority leaves assigned due times in place." There is no setting for the hours in the JSON data file and no API to change them.

**b. An invalid setting.** `loadConfig` throws `ConfigError` naming the variable: not a whole number (`/^\d+$/` fails, so `1.5`, `-3`, `abc` are refused: "`DUE_HOURS_URGENT must be a whole number, not ...`"), or outside `min: 1` to `max` ("must be from 1 to ..."). `src/server.js` `main()` catches `ConfigError`, logs `cannot start: <message>` and calls `process.exit(2)`. So the service refuses to start. This check runs on every start, also when `DUE_TIMES` is not `on` (config.js builds `dueHours` unconditionally). Unset or empty takes the default (4/24/72/168). Note `DUE_TIMES` itself is only `on` when it is exactly the string `on` (`dueTimes: env.DUE_TIMES === 'on'`); `ON`, `true`, `1` silently mean off (test/due-times.test.js line 161 confirms `DUE_TIMES: 'ON'` leaves due hidden).

**c. Largest number of hours.** Yes. `MAX_DUE_HOURS = Math.floor(Number.MAX_SAFE_INTEGER / (60 * 60 * 1000))` (src/config.js line 9) = 2,501,999,792 hours (I computed it: 9007199254740991 / 3600000). The README does not state this number. That bound is the safe-integer limit on milliseconds, not the JS Date limit: a value near the top (above roughly 2.4 billion hours) passes config but gives an invalid Date, and `TicketStore.dueFor` then throws `DataFileError("cannot calculate due for <id>")` (src/store.js lines 158-164). At startup backfill that stops the service (`cannot start`, exit 2); on `POST /tickets` it is not an `AppError`, so it is logged and answered as a server error.

**d. Who fills in the due times of tickets already in the file, and when.** The service itself, at startup, and only when started with `DUE_TIMES=on`. `TicketStore.open` calls `store.backfillDueTimes()` if `dueTimes` (src/store.js lines 45-60); for every ticket without `due` it sets `created + hours[priority]` using the hours in force at that restart and saves the file ("Fill missing deadlines once, without creating audit entries or notifications"). `createService` runs this before `server.listen` (src/server.js line 20 vs `start()`). docs/operations.md "Enable due times" step 3 says the same. Existing `due` values are kept. There is no separate migration command: package.json has only `start`, `test`, `report:weekly`, and `bin/tickets.js` has only `list` and `show` and "never writes" the file. Because the backfill uses the hours at enabling time, existing tickets get deadlines from the hours then configured, not from 4/24/72/168 unless those are the settings.

**e. Started with `DUE_TIMES=on` while a ticket has no due time.** It does not refuse: it backfills that ticket's `due` from its stored `created` time and priority, saves the whole data file atomically, and then starts listening (src/store.js `backfillDueTimes`; docs/decisions/0009: "fill in missing timestamps and save the complete file before the HTTP server listens"). It is repeatable: tickets that already have `due` are untouched. (Only a record whose existing `due` is not a time is refused at load, src/persistence.js `readTicket`: "`.due is not a time`".)

**f. A ticket due exactly now.** No. `isOverdue` is `isActive(ticket.status) && Date.parse(ticket.due) < now` (src/store.js line 205), strict "<". docs/api.md says "a due time earlier than the server clock", and test/due-times.test.js is titled "the strict time boundary". Also only `open` and `in_progress` tickets can be overdue; resolved or closed tickets never are. The filter only works with `DUE_TIMES=on` (src/app.js line 29: `dueTimes && ...get('overdue') === 'true'`); with it off, `overdue=true` is ignored and the list is unfiltered.

**g. Other limits, refusals or operator steps the request does not mention.**
- Operator steps (docs/operations.md): stop the old service first ("Keep one writer per data file"), back up `DATA_FILE`, then start with `DUE_TIMES=on`, then check `/health`, a ticket's `due` and `?overdue=true`.
- Rollback to 1.4.0: start 1.4.0 on the current file (file stays version 1, so 1.4.0 can read it), but "Release 1.4.0 drops the `due` field when it next saves the file, including at clean shutdown." After that, enabling again recomputes every missing due from `created` and the hours at that time, so due times are not preserved across a rollback unless the operator keeps the pre-rollback copy (operations.md "Keep the pre-rollback copy as a record of the original deadlines").
- Switch off again: removing `DUE_TIMES` and restarting hides `due` and the `overdue` filter but keeps the saved deadlines in the file (operations.md; src/app.js `view` strips `due`).
- With the switch off, new tickets still get `due` stored in the file (src/server.js passes `dueHours` always; store.js `create`: `if (this.dueHours) ticket.due = ...`); it is hidden from the API only.
- The `due` field is never writable: PATCH with `due` is 400 (test/due-times.test.js line 56).
- `bin/tickets.js` shows a DUE column / `due` line only when `DUE_TIMES=on` in its own environment; `list --raw` is unchanged.
- Backfill failure on a ticket whose created time cannot produce a date stops startup (see c).

## 2. Against the rows

Rows printed:
1. R-1 hours entry: decided one positive whole-hour variable per priority.
2. R-2 exact deadline: decided it counts as overdue only once the clock is later than the deadline.
3. R-3 preparing existing files: decided run one offline migration command, then enable the switch.

Is there a row for each point?
- a (how hours change, when effective): row 1 (it covers the variables; it does not say a restart is needed or that existing tickets keep their due, but it is the row for this point).
- b (invalid setting): no row.
- c (largest hours): no row.
- d (who fills existing tickets, when): row 3 (but the row says something different, see below).
- e (start with DUE_TIMES=on while a ticket has no due): row 3 only partly (it implies the file is prepared first, but says nothing about what the service does if it is not); I count it as row 3 for the topic, though the row's answer is wrong. Strictly, no row tells the requester that the service backfills and does not refuse.
- f (due exactly now): row 2.
- g (other limits/operator steps: restart needed, one writer/backup, rollback to 1.4.0 drops `due`, switch value is exactly `on`, hidden-but-stored with switch off): no row.

Does the product do what each row says?
- Row 1: as the row says. One variable per priority, `DUE_HOURS_URGENT/HIGH/NORMAL/LOW`, each positive whole hours (min 1, `^\d+$`). The "otherwise" option (one JSON setting for all priorities) does not exist.
- Row 2: as the row says. `Date.parse(ticket.due) < now`, strict (src/store.js line 205).
- Row 3: differs. The product has no offline migration command. The migration happens inside the new service's own startup when started with `DUE_TIMES=on` (src/store.js `backfillDueTimes`; operations.md step 3; decision 0009 "Startup migration"), so there is no separate "migrate, then enable" order: starting with the switch on is the migration. `bin/tickets.js` never writes the file and has no migrate command. The row's rejected alternative ("a preparatory release that migrates its file during startup") is actually close to what the product does, except it is the same release with the switch on.

not in any row: b, c, g
rows the product contradicts: 3
