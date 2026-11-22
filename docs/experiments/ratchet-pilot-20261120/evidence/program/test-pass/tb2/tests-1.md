## Failing now

- C-6 — After assigning `Dana`, a PUT of `" Dana "` succeeds and leaves the ticket, audit and outbox unchanged. Filtering by the same padded spelling omits that ticket.
- C-34 — Startup accepts a version 1 file with a 65-letter assignee on `T-0002`. The API then returns all 65 letters as that ticket's assignee.
- C-44 — `npm test` discovers and runs the new assignment cases under `test/`. Those cases cover HTTP assignment, clearing, active states, repeats, notifications and filtering. They do not exercise CLI ownership visibility.
- C-45 — A blocked save returns 500 `internal`, but the running service exposes the attempted assignee, a newer update time, an extra audit entry and a pending notice. An unrelated successful edit later saves those effects, and they are visible after restart.

## Discoveries

- A graceful shutdown can rewrite a legacy file after a read-only API session. | Observable: Start with an untouched version 1 file, GET one ticket, send SIGTERM and compare the file bytes. | Why: The shutdown saved a new version 1 snapshot with explicit null assignees, so persistence checks need to observe the file before graceful shutdown.
- Assignee-filtered cursors page through current ownership. | Observable: After the first page, assign the same agent a ticket above and a ticket below the last returned ID, and clear a match on the remaining page. The next page includes the new match above the cursor and excludes the other two. | Why: A dispatcher changing ownership during dashboard pagination can change which tickets appear on the remaining pages.
- A saved outbox event ID is a positive whole number, and the next event ID must exceed every saved event ID. | Observable: Restart with a version 1 file whose next event ID equals the last assignment event ID, or whose assignment event ID is zero or fractional. Startup refuses the file and identifies the invalid record. | Why: A restored outbox needs to allocate an unused identity for its next notice.
- Saved assignment audit deltas need both endpoints and saved notices need object data and a nonnegative whole attempt count. | Observable: Remove either endpoint from a saved assignment audit delta, or change a saved notice's data to null or an array or its attempts to a negative number or fraction. Startup refuses the file and identifies the invalid record. | Why: Testing the loader with one bad field at a time exposed several independent startup checks that ordinary restarts never exercise.

## Checks nothing here can break

- C-8 now checks a missing ID in an empty service and a missing ID among existing tickets, including a clear request. The starting product's unknown-route handler also returns the exact two values specified by C-8, HTTP 404 and `error.code: not_found`. The existing-test breakage and supplied source faults leave those values intact. A separate copy that returned `400 invalid` for a missing ticket failed C-8. Route availability is covered by C-1 and C-3.

## Faults that change nothing

- `src/app.js:16`, `false` → `true`, changes the fallback for an omitted `logRequests` argument. The server entry point always supplies the boolean from `LOG_REQUESTS`, so the fallback is unreachable through the service.

## Regression checks

- R-1 failed on both `src/format.js:36` faults. Reversing the comparison displaced the column contents. Changing subtraction to addition padded the final cell with trailing spaces.
- R-2 failed on all seven `src/persistence.js` faults. It covers reuse of the last event ID, incomplete audit deltas, non-object audit or event data, invalid attempt counts and invalid event IDs.

All 51 manifest commands ran and printed their item names. The longest finished in about 16 seconds.
