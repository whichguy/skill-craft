# Help-desk ticket service: specification

## Requirements

### R-1 Due time per ticket
Basis: request of 2026-11-22 ("Each ticket gets a due time ... 4, 24, 72, 168 hours"). Source: src/store.js create, src/tickets/priorities.js.
Every ticket has a due time = its `created` time plus the response hours of its priority at creation. Defaults 4 urgent, 24 high, 72 normal, 168 low.
- Positive: a ticket created at T with priority high has due = T + 24 h, as an ISO 8601 UTC string like `created`. Confirmed by store and HTTP tests.
- Failure: n/a: creation errors are unchanged.
- Boundary: each of the four priorities gets its own hours. Confirmed by a unit test per priority.
- Preserved: audit entry of creation lists the same four fields (title, priority, requester, status); no notification changes.

### R-2 Hours are configurable without a code change
Basis: request of 2026-11-22 ("help desk must be able to change those hours without a code change"); default of this date: environment variables.
Environment variables DUE_HOURS_URGENT, DUE_HOURS_HIGH, DUE_HOURS_NORMAL, DUE_HOURS_LOW, each a whole number from 1 to 100000 (about 11 years; default of this date, it keeps created + hours a valid date); unset or empty takes the default of R-1. A settings object or store built without these keys (as test/helpers.js TEST_SETTINGS and `new TicketStore({ clock })` do today) uses the defaults of R-1, and a missing DUE_TIMES key means off.
- Positive: DUE_HOURS_HIGH=10 makes a new high ticket due 10 h after creation. Confirmed by config test and a service test.
- Failure: DUE_HOURS_HIGH=abc or 0 stops the service at start with a message naming the variable (ConfigError, exit 2), like other settings. Confirmed by config test.
- Boundary: 1 and 100000 are accepted; 0 and 100001 are refused at start the same way. Confirmed by config test.

### R-3 Due time is set once
Basis: request ("A ticket's due time is set once").
- Positive: after PATCH changing priority, the ticket's due is unchanged, and a transition leaves it unchanged. Confirmed by store and HTTP tests.
- Positive: a ticket created under one set of hours keeps its due when the service restarts with other hours. Confirmed by a persistence-level test.
- Failure: a PATCH or any request body naming `due` is refused 400 as an unknown field (existing rule). Confirmed by HTTP test.
- Preserved: PATCH changes only title and priority, audit entries for them are unchanged and carry no `due`.

### R-4 Tickets show `due` when switched on
Basis: request ("Every ticket shows its due time as `due`").
With DUE_TIMES=on, every ticket body (list items, GET, POST, PATCH, transition) has `due`.
- Positive: GET /tickets/:id and every list item hold `due`; created ticket body too. Confirmed by HTTP tests.
- Boundary: only the exact value `on` switches on; anything else, including unset, empty, `ON`, `1`, `true`, is off.

### R-5 Overdue listing
Basis: request ("`GET /tickets?overdue=true` lists only the open and in-progress tickets whose due time has passed").
With DUE_TIMES=on, `overdue=true` returns only tickets with status open or in_progress (states.ACTIVE) whose due is strictly before now, in the usual cursor-page envelope and id order.
- Positive: one overdue open, one overdue in_progress, one not yet due, one overdue resolved, one overdue closed: only the first two return. Confirmed by HTTP test through `withService({ dueTimes: true, clock })` with `manualClock` (src/clock.js) advanced past the due times; the tickets reach resolved and closed through POST /tickets/:id/transition (open, in_progress, resolved, closed).
- Boundary: due exactly equal to now is not overdue (default of this date, strictly passed).
- Failure: `overdue=false` or any other value than `true` is 400 `invalid` (default of this date). Confirmed by HTTP test.
- Combination: overdue narrows whatever else the listing returns (it is not part of the existing OR of status and priority, which is left as is); paging with `limit` and `cursor` works on the narrowed list. Confirmed by HTTP test.

### R-6 Existing tickets get due times and keep them
Basis: request ("The tickets already in the production data file get due times too, from their own creation time and priority, and keep them from then on").
When the service loads a data file, every ticket without `due` gets created + hours(priority) under the hours in force then, and the file is saved at start so it holds them. No audit entry, `updated` unchanged. A ticket that already has `due` keeps it.
- Positive: a v1 file written by 1.4.0 with tickets of each priority starts, the file afterwards holds `due` for each, computed from its created time (not from the start time). Confirmed by persistence/service test.
- Boundary: second start with different hours leaves every `due` unchanged. Confirmed by test.
- Failure: a ticket whose `due` is present but not a time is refused at load naming the record (like other records). Confirmed by persistence test.
- Preserved: audit, outbox, nextNumber and ticket fields other than due are unchanged by the backfill.
- Preserved: the backfill and its save happen when the service opens the store, not in the loader that bin/tickets.js and scripts/weekly-report.js use; those never write the data file and load a file with `due` without error. Confirmed by a test that runs the loader on a file and checks its bytes and mtime-independent content are unchanged, and by `list --raw` output equal to before.

### R-7 Switch: DUE_TIMES gates what the service says
Basis: request ("until the DUE_TIMES environment variable is `on`, the service answers exactly as it does today").
Whatever DUE_TIMES says, the service computes and stores `due` (R-1, R-6). Without `on`: no response body has `due`, and `overdue` is ignored as an unknown query parameter is today (full list returned, no error); the command line and the weekly report print what they print today.
- Positive: with DUE_TIMES unset, all endpoints' responses equal the 1.4.0 responses, byte for byte for the same data (create, get, list, patch, transition, audit, admin/outbox). Confirmed by HTTP tests comparing against the old shape and, in the test stage, by running base commit 23f8879 against the same requests.
- Boundary: `?overdue=true` with the switch off returns all tickets; `?overdue=banana` returns no error.
- Preserved: the data file holds `due` even with the switch off (the precondition for switching on).

### R-8 Roll back to 1.4.0
Basis: request ("operators must be able to go back to the current release, 1.4.0 ... start on the data file the new release wrote and show every ticket").
The data file format stays `version: 1`, `due` an additive optional ticket field that 1.4.0 ignores.
- Positive: 1.4.0's loader (base commit) starts on a file written by the new release and returns every ticket with its original fields. Confirmed by running the base commit code against the new release's output (test-stage experiment, saved) and a permanent test that the saved file has `version` 1 and that its top-level keys, ticket keys (the 1.4.0 set id, title, priority, requester, status, created, updated plus only `due`), audit keys and outbox keys equal the 1.4.0 sets listed in the test. The experiment is replayable as: `git archive 23f8879 src | tar -x -C <empty scratch dir>`, start a `createPersistence(file).load()` from that copy on a file the new release saved after a ticket was created, patched and transitioned, and record that all tickets load; its output is kept in the run's scratch/evidence.
- Failure/known limit: 1.4.0 re-saves without `due`; upgrading again backfills from the then-current hours (documented in docs/operations.md).
- Preserved: version stays 1; audit and outbox sections are unchanged.

### R-9 Existing behaviour and tests
Basis: request ("Everything the service already does keeps working, and its existing tests must still pass as they are").
- Positive: the 117 existing tests pass unedited. Confirmed by `npm test`, and by `git diff` on test/ showing only new files.
- Preserved: CLI `list --raw` column positions, error envelope, cursor paging, audit and outbox behaviour.

### R-10 Tests and release notes
Basis: request ("Add node:test tests under test/ ... `npm test` runs them"); CONTRIBUTING.md releases and decisions.
New node:test files under test/ cover R-1 to R-8 and run in `npm test`. Version 1.5.0, a CHANGELOG section, a decision record docs/decisions/0009, README config table, docs/api.md and docs/operations.md (rollout: deploy with DUE_TIMES off, check the file holds `due`, switch on; rollback to 1.4.0).
- Positive: `npm test` passes with the new files; the docs name every new variable.

## Non-functional requirements

- Compatibility: file format and 1.4.0 loading, covered by R-8. Verified by experiment.
- Dependencies: none added (CONTRIBUTING.md). Verified by package.json diff.
- Performance, security, accessibility, interface polish: excluded; no bound in the request, no new interface, in-memory list.

## Retired
None.
