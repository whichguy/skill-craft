# Help desk ticket service

## Requirements

### R-1 Priority response times
From the 2026-11-21 response-time request. Each new ticket's due timestamp uses its creation instant and the configured hours for its effective priority. Defaults are urgent 4, high 24, normal 72 and low 168, and operators can change them without code edits. Confirm each priority and a configurable override through HTTP creation using a fixed clock. Check default priority and invalid configuration.

### R-2 Stable deadline
From the 2026-11-21 response-time request. Once stored, due survives updates, status transitions, restart and subsequent changes to priority hours. Confirm with mutation responses, disk inspection and a restart with different settings. Clients cannot set due through the existing ticket inputs.

### R-3 Ticket presentation and overdue listing
From the 2026-11-21 response-time request and docs/api.md. Flag on adds due to each HTTP ticket object. Only active open and in_progress tickets strictly past due match overdue=true. The overdue predicate also restricts matching tickets before pagination. Behavior at equality: excluded. Existing status/priority filter code and cursor behavior remain compatible. Confirm create, read, patch, transition, list, and filtered pages. The flag also displays due in human-readable CLI output. The fixed-column raw report stays compatible.

### R-4 Existing data and dark rollout
From the 2026-11-21 production rollout request and decision 8. Fill missing due from persisted creation time and priority, preserving existing due and unrelated records. Startup over an old file saves the complete upgrade before serving. A second startup does not perform another migration. Only DUE_TIMES=on exposes due or recognizes overdue=true. Confirm on-disk data, off-mode API and CLI, on-mode reads, and idempotence using a fixture copy. A failed backfill must leave the old file usable and no listener started.

### R-5 Rollback compatibility
From the 2026-11-21 rollback request. The baseline 1.4.0 executable can start over the same version-1 file emitted by the new release and list all tickets. Confirm with an immutable local copy of baseline code, new data and fresh HTTP reads. 1.4.0 rewrites only the keys it knows. The operations procedure records the deadline backup needed if 1.4.0 must write and later re-upgrade. The production target is operator-owned.

### R-6 Compatibility and verification
From the 2026-11-21 request and CONTRIBUTING.md. Existing node:test cases pass unchanged, and new cases run under npm test with no dependencies. Service startup honors PORT, and the CLI and weekly report keep existing entry points and raw layout.

## Non-functional requirements

Keep the single writer and atomic replace guarantees of decision 8. Reuse the current terminal table and detail views for the extra field, retaining errors and raw report output. The service adds no new identities, external dependencies, secrets, caches or background work.

## Retired

None.
