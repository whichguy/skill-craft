# Help desk ticket service

## Requirements

Basis for R-1 through R-5 is the response-time request of 2026-11-21. Baseline is 1.4.0 at 8c526a1, documented in README.md, docs/api.md and docs/operations.md.

### R-1 Immutable due time

Each creation records an ISO UTC due time based on its creation timestamp and priority, with 4, 24, 72 and 168 hour defaults and per-priority environment overrides (positive whole hours by default). Verify all four priorities, an override, restart and a priority edit on a real HTTP response and file. A priority edit and different hours leave assigned deadlines intact. Invalid hours fail configuration with the variable named.

### R-2 Enabled ticket views and overdue listing

Ticket responses and human CLI views show due only when DUE_TIMES is exactly on. Raw CLI columns remain stable. HTTP overdue=true selects open and in_progress tickets strictly before the current clock (default interpretation), intersects status/priority filters, and runs before pagination. Other values retain existing query semantics. Verify with a fixed clock, terminal states, filter intersections and cursor pages.

### R-3 Existing tickets and activation

Operator runs a separate, offline migration before enabling a previously used data file (default procedure). Backfill missing due from stored creation time and priority, preserve dates already assigned and preserve IDs, audit and outbox. The enabled service refuses to start on an incomplete existing file. Verify file contents, retry, and readiness through the actual migration and service entry points. The service remains the sole writer during operation.

### R-4 Rollback

The 1.4.0 program starts on the migrated file and lists the same tickets. Verify by booting the original source. An operator may preserve the pre-rollback version-1 file and reuse its deadlines during re-upgrade while retaining ticket updates made under 1.4.0.

### R-5 Existing surfaces

Feature off preserves HTTP and CLI output and ignores overdue. Verify on new and migrated data and run the 117 existing tests unmodified alongside added node:test coverage.

## Non-functional requirements

Retain the dependency-free Node runtime, version-1 data and atomic file replacement. Compare legacy and enabled CLI output, preserving existing layout and raw column positions. The scope adds no network dependency, identity, cache, new processor or graphical UI.

## Retired

None.
