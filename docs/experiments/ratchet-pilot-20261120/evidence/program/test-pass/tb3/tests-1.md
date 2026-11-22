## Failing now

- C-34. Startup accepted an explicit 65-letter assignee in the saved record for T-0002 and began listening. It refused the numeric and empty-string values and accepted the 64-letter value and the legacy missing field.
- C-44. `npm test` discovered and passed five new assignment cases. Those cases covered HTTP assignment and clearing, state constraints, repeats, notices and filtering. None exercised CLI ownership visibility.
- C-45. Blocking replacement returned 500 `internal`, but the running ticket changed from Lee to Dana, its update time advanced, and a new audit entry and pending notice appeared. Saving an unrelated ticket after restoring storage carried those failed changes across restart.

## Discoveries

- A cursor marks a position in the current assignee-filtered results, so reassignment can add a match on a later page only if its ID is after that position. | Observable: Read the first page for Dana, assign Dana a ticket on either side of the returned cursor, and follow that cursor with the same filter. | Why: The newly matching ticket after the cursor appeared on the next page, while the newly matching earlier ticket was already behind the cursor.
- The file relay carries notification wording in `subject` and `body`, alongside event identity, recipient and ticket. | Observable: Read the JSON line emitted to `NOTIFY_FILE` after assigning T-0001 to Dana. | Why: The assignment was described in both `subject` and `body`. The specification's phrase “a message” describes their content, and the emitted line has no `message` field.
- A missing ticket and an unregistered route can return the same not-found status and code. | Observable: Compare assignment PUTs for existing and absent ticket IDs before and after adding the route. | Why: The starting product returned `404 not_found` for both, so the missing-ticket request alone also passed on a service without assignment.

## Fault checks verified

- C-8 passes on the build and fails on the starting product and on a copy that bypasses the missing-ticket check. The latter returned 500 for the missing ticket.
- R-1 checks existing startup validation separately from the assignment clauses. On seven separate copies of the build, it detected acceptance of a reused next outbox ID (`src/persistence.js` line 92), partial audit deltas (both edits on line 160), negative or fractional attempt counts (line 170), non-object notification data (both edits on line 180), and an event ID of zero (line 194).

## Faults that change nothing

- `src/app.js` line 16, `false` to `true`. The service passes a boolean from `LOG_REQUESTS` on every start, so the modified fallback is never used by `npm start`.
- `src/format.js` line 36, `===` to `!==`. The edit removes padding from the earlier cells and may pad the last cell. The ticket rows, cell separators and ownership values are still visible. C-40 allows different human-readable layouts.
- `src/format.js` line 36, `-` to `+`. The last cell gains trailing spaces on shorter rows. The displayed values, field positions and raw output remain the same.
