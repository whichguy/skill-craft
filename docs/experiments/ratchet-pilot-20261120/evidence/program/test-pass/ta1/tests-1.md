## Failing now

- C-34 — The service started and listened with an explicit 65-letter assignee in the version 1 file. It correctly refused the numeric and empty-string values.
- C-44 — `npm test` ran the original tests and five new assignment cases. No new case exercised assignee visibility in the command-line listing.
- C-45 — A blocked save returned 500 `internal` and left the file bytes intact, but the running API exposed the attempted assignee, a new `updated` value and an audit entry. Assigning and reassigning also left a pending notice. A subsequent title edit saved the rejected assignment, its audit entry and its pending notice, which were still visible after restart.

## Discoveries

- Assignee-filtered cursors resume at the last returned ID against current ownership. | Observable: List Dana’s tickets two at a time, assign a later ID to Dana and reassign a later match to Lee, then pass the original `next` with the same filters. | Why: The next page included the newly matching ID and omitted the one assigned to Lee.
