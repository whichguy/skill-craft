# Ticket service specification

## Requirements

### R-1 Assign an immutable due time

- New tickets use their creation instant plus hours by priority (urgent 4, high 24, normal 72, low 168). API creation tests with a fixed clock confirm ISO UTC output and default priority.
- Operator default for this change: independent positive whole-hour DUE_HOURS_<PRIORITY> settings; unset or empty uses its priority default, unusable values fail with the variable name. Verify via configuration and startup.
- Priority edits, lifecycle transitions and configuration changes across restart preserve stored deadlines. Verify mutation and restart over a real data file. Clients cannot set due.

### R-2 List overdue active tickets

- Enabled GET /tickets?overdue=true includes open and in_progress tickets with due strictly before the request's clock instant; excludes resolved, closed, exact-boundary and future tickets. Check via HTTP with a manual clock.
- Default for this change: overdue restricts the existing status and priority filter result before cursor pagination; other overdue values preserve the ordinary listing. Verify page boundaries and filter combinations.

### R-3 Stage and gate deadlines

- Backfill all legacy tickets once from their own stored creation timestamps and current priorities. Preserve existing due, IDs, history and outbox, and persist before enablement. Verify idempotence and state readback using real files.
- Operator default for this change: offline migration under the documented single-writer model; enabled startup refuses a file with any missing due. Memory-only and new empty stores start normally.
- Until DUE_TIMES is exactly on, retain existing API shapes and query behavior, even with a migrated file. When enabled all HTTP ticket responses and human CLI show due, with stable raw CLI output as the default for machine consumers.

### R-4 Roll back safely

- Release 1.4.0 starts on the new release's data file and lists every ticket; verify over real HTTP and paginate where needed.
- Default for this change: capture a pre-rollback file snapshot to recover original due after 1.4.0 writes. Offline migration can use that snapshot to restore only due on matching tickets while retaining newer ticket data.

### R-5 Preserve existing behavior

- Remain dependency-free, honor PORT and preserve audit, notifications, error envelope, CLI and weekly report. Existing tests remain unmodified and pass together with new test/ node:test cases under npm test.
- Production promotion is outside local source delivery. No additional availability or scale target was specified; retain single-writer storage.

## Retired

None.
