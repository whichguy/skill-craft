# Help desk ticket service specification

## Requirements

### R-1 Assigned deadlines
Basis: 2026-11-21 request, S2–S4. At creation the service assigns an ISO UTC due time from the same creation timestamp and that ticket's priority: urgent 4 hours, high 24, normal 72, low 168. Overrides come from per-priority environment variables. Test all four defaults, an override, invalid configuration and persistence across priority edits and configuration changes. Clients cannot supply due on create or patch.

### R-2 Enabled ticket views and filtering
Basis: 2026-11-21 request, S5 and S7. Only literal DUE_TIMES=on exposes due on all ticket response bodies and human CLI views. When enabled, literal overdue=true limits GET /tickets to open and in_progress tickets with due strictly earlier than the request clock instant, for example an urgent ticket created at 08:00 UTC is not overdue at 12:00:00.000 UTC and is overdue one millisecond later. It intersects the current priority/status filter group and runs before cursor pagination. Other overdue values preserve ordinary listing. With the flag off, ticket responses and list query behavior match 1.4.0. Verify through the HTTP server with a manual clock and the CLI with a test file. Raw CLI columns stay fixed.

### R-3 Persisted backfill
Basis: 2026-11-21 request, S6–S7. An existing ticket missing due gets creation time plus the configured hours for its stored priority, including final tickets. Backfill runs even with the display flag off and saves before requests are served. Existing due values are retained through restart and no ticket history, outbox, or updated timestamp changes from backfill. One process owns writes under the operations contract. A failed save prevents service startup. Verify by inspecting the file during an off startup, restarting with changed settings, and simulating a failed write.

### R-4 1.4.0 rollback
Basis: 2026-11-21 request, S8. The exact 1.4.0 service can start on a candidate-written file and show every ticket. Verify by booting the baseline code on copies and comparing ticket IDs and existing fields. Its serializer drops due metadata on rewrite, so an operator needs the prior due-bearing snapshot for future re-upgrade reconciliation.

### R-5 Existing contracts and tests
Basis: 2026-11-21 request, S1 and S9–S10. Preserve Node >=22, package entrypoints, PORT, audit, notifications, listing, CLI and weekly report behavior. Add dependency-free node:test cases under test/ and run npm test, with existing tests unchanged.

## Non-functional requirements

Preserve single-owner atomic whole-file saves and existing audit and outbox consistency. Time comparisons use UTC instants and the injected clock. The human CLI uses the existing aligned table and detail labels; no new interactive surface is introduced. Local verification uses disposable files. Production timing and dataset size get no new bound.

## Retired

None.
