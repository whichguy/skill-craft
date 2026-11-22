## Failing now

- C-34: The service starts with a 65-letter assignee saved on a ticket. It rejects numeric and empty-string values and accepts a 64-letter value and a legacy record with no assignee.
- C-40: The human CLI prints the same row for an unassigned ticket and the same ticket assigned to the valid agent name `-`. The operator cannot distinguish the two ownership states.
- C-44: `npm test` discovers and runs five new assignment cases. They cover the HTTP and outbox behavior, with no case exercising CLI assignee visibility.
- C-45: Assigning, reassigning and clearing return 500 `internal` when storage is blocked. The running service still publishes the requested assignee, update timestamp and audit entry, plus a pending notice for a named recipient. After storage is restored, graceful shutdown saves the failed change and the restarted service exposes it.

## Discoveries

- The human listing should keep its unassigned indication distinguishable from every valid displayed agent name | Observable: List the same ticket while unassigned and while assigned to the literal `-` | Why: The API distinguishes null from `-`, but the CLI used the same dash for both.
- Current ownership in the CLI `show` view is an open point for the requester | Observable: Run `show` for an assigned ticket | Why: This build shows ownership changes in the history and has no separate current assignee field in the ticket details.
- A continuation cursor applies to current ownership after the last returned ID | Observable: Change owners on both sides of a page boundary, then fetch the next page with the original filters and cursor | Why: A newly matching ticket after the cursor appeared, while a newly matching ticket before it stayed outside the continuation.
