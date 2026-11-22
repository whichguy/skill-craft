## Failing now

- C-34. Startup rejects saved numeric and empty-string assignees, but starts serving normally when a saved assignee has 65 plain letters.
- C-40. The human listing uses the same visible `-` for an unassigned ticket and for a ticket assigned to the accepted name `-`. The operator cannot tell the two states apart.
- C-44. `npm test` discovers and runs five new assignment cases under `test/`. They cover HTTP behavior, but none exercises ownership visibility in the CLI listing.
- C-45. When storage cannot be replaced, PUT returns 500 `internal` but the running service exposes Lee as the new owner with a new update time, audit entry, and pending notice. After restoring storage, an unrelated successful save makes that failed change visible after restart.

## Discoveries

- The CLI detail view should show the current assignee directly. | Observable: Run `node bin/tickets.js --data <file> show <id>` after assigning the ticket, then again after clearing it. | Why: The detail view shows ownership changes in its history but omits current ownership from the ticket fields, so the operator has to infer it from prior changes.
