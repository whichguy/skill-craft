# Specification

## Scope

The help-desk HTTP API and operator CLI retain the existing dependency-free Node runtime, ticket lifecycle, audit, notifications and report. The response-time promise adds a deadline to tickets under an environment-controlled rollout. See README.md, docs/api.md and docs/operations.md.

## Requirements

### R-1 Configurable and immutable due times

Basis: help-desk response-time policy. On creation assign an ISO UTC deadline from creation plus the priority's configured hours. Defaults are urgent 4, high 24, normal 72 and low 168. Priority edits and policy changes keep assigned dates. Verify all four defaults via HTTP, a configured override, priority updates, and a restart under changed hours.

### R-2 Ticket views and overdue queries

Basis: help-desk agent listing and read workflow. Include due on enabled HTTP ticket responses and human-readable CLI views that read assigned deadlines. With overdue=true, use a single clock reading to include only open and in-progress tickets strictly past due, before pagination, constrained by any requested status and priority. Verify ticket response shapes, exact-time exclusion, lifecycle states, combined filters and pagination. The raw CLI columns stay stable.

### R-3 Migration and rollout gate

Basis: operations data-file contract. Backfill missing deadlines from each ticket's stored creation and priority, preserve previously assigned dates and save before serving. Keep audit, outbox, ticket count and IDs and write a whole version-1 document. Until DUE_TIMES is exactly on, omit due and ignore overdue at the HTTP boundary. Verify with pre-feature and partially migrated files, an off-mode start and writes, and a restart with changed hours.

### R-4 Rollback and regression

Basis: 1.4.0 release compatibility and CONTRIBUTING.md. 1.4.0 serves every ticket when started against the file emitted by the new release. Verify with the immutable 1.4.0 source and both legacy and newly written tickets. Existing tests remain unchanged and pass with new node:test cases under npm test. Document the rollback write limitation and the production rollout procedure.

## Non-functional requirements

Use the existing single-writer, atomic JSON replacement and centralized request errors. Existing audit attribution, worker delivery and access boundaries remain applicable. Deadline backfill is a single pass over tickets and adds no scheduling, dependencies or network access. No new authentication or presentation surfaces are needed.
