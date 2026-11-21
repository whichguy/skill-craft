## Failing now
none

All 77 tests in `acceptance/assign.spec.js` pass against the product as built; each clause C-1..C-21 and use case U-1..U-6 has an entry in `ratchet/acceptance.json` (command: `node --test --test-reporter=spec --test-name-pattern='^<id> ' acceptance/assign.spec.js`). The tests start `src/server.js` as a child process on port 0 (worker off, or on at 40 ms for delivery checks) and use the CLI and weekly report as processes; no internal functions are used. The file is named `.spec.js` so the product's `npm test` does not pick it up.

## Discoveries
- A request that changes nothing on a resolved or closed ticket is a 409 (build chose this); the specification leaves it open, so tests do not check it | Observable: `PUT` null on an unassigned closed ticket | Why: C-5 and C-7 overlap there, tests avoid it.
- `list --raw` now prints an assignee as a fifth column (empty for unassigned) | Observable: `node bin/tickets.js list --raw` | Why: C-19's Open point; tests check only the first four columns.
- A service that never saved (no change since start) leaves no data file, so the CLI refuses it with exit 2 | Observable: start and stop a service on a new DATA_FILE, then `tickets list` | Why: met while writing U-5; existing behaviour, unrelated to the change.
- Timing of `updated` is in milliseconds; tests sleep 20-30 ms between calls so "unchanged" is not vacuous | Observable: same-millisecond calls | Why: real clock in the spawned service.
