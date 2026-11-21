# Ticket service specification

## Requirements

### R-1 Configurable, fixed due time

Basis: help-desk due-time request, 2026-11-21, creation and immutability clauses. The server uses the existing ticket clock and creates `due` as a UTC ISO timestamp, equal to `created` plus elapsed hours. Defaults: urgent 4, high 24, normal 72, low 168. Each priority is independently configurable through the environment. An omitted priority still defaults to normal. Invalid configured hours fail startup and name the setting. HTTP tests use a fixed clock, test all defaults, and show that a priority change, a transition, or an hours change across restart preserves the original deadline. A ticket created after reconfiguration uses the new value.

### R-2 Visible due time and overdue selection

Basis: help-desk due-time request, 2026-11-21, API and flag clauses. With the exact environment value `DUE_TIMES=on`, create, get, update, transition, and list responses carry `due`. An overdue response includes only open and in-progress tickets whose deadline strictly precedes the request clock. Status and priority narrow that set before pagination. Resolved and closed tickets stay excluded. The existing cursor envelope and ID order apply. With any other flag value, response bodies and list query behavior match 1.4.0. Verify with localhost HTTP, including due equality and one millisecond later, status/priority, and paginated selection. The optional query is active for the exact value `true`.

### R-3 Existing file backfill and persistence

Basis: help-desk due-time request, 2026-11-21, stored tickets and rollout clauses. With DATA_FILE configured, startup fills missing due times from each row's stored created time and priority, retains due on previously migrated rows, and writes the data before serving. This happens even when due visibility is off. Every subsequent ticket create saves its due time. Existing ticket records, IDs, audit and outbox remain valid. Check preexisting and partially migrated version 1 data, inspect the file during service startup before making a write request, and restart with changed hours. Missing and invalid due are distinct: an invalid value reports a data file validation error. The CLI reads the same file and does not backfill or write it.

### R-4 Rollback and regression compatibility

Basis: help-desk due-time request, 2026-11-21, rollback and regression clauses. Version 1.4.0 must start on the file the candidate wrote and list the same tickets. Check using the exact baseline executable and candidate-generated fixture, including preexisting and new records. The original node:test suite and CLI raw and weekly report formats remain intact. Document production backfill, activation, rollback and the older writer's metadata loss. Tests for the new behavior run under npm test.

## Non-functional requirements

The service remains a single-writer, dependency-free Node service. One pass fills missing deadlines at startup. Reuse atomic file replacement, so failed migration does not publish partial deadline data or start serving it. Confirm with fixture read-back and forced save failure. The existing CLI table and detail style apply to enabled due output, and the four columns of raw output remain compatible with the weekly report. No new graphical UI, background task or network service is needed.

## Retired

None.
