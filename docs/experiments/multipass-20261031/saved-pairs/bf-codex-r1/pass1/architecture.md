# Architecture

## Decisions
### AD-1 Store-owned assignment
Extend existing validation, store, file projection and notification template; store atomically records assignment, audit and unique notification event per real assignment. Keep legacy files compatible. Reuse worker retries. Extend listing predicate to conjunction and preserve raw positional columns. No dependencies.

## Real-boundary checks
All checks planned against local isolated service and temporary data/notification files: API state and errors, outbox worker delivery, persistence restart and legacy load, CLI and weekly report, and full suite. They verify local enqueue and delivery, not any remote relay or deployment, neither of which is requested or available. No browser, cache, external access or identity service is involved. Worker failure/retry remains covered by existing tests. Before-and-after state and negative controls must be asserted in new tests.

## Stack and structure
Node CommonJS service: src/app.js routes to src/store.js; src/tickets validates and filters; src/persistence.js projects version-1 JSON; src/templates.js renders worker events; src/format.js serves CLI. Assignment adds a store method and route, field on ticket records, validation and template in existing namespaces; no new package or shared name collision. Legacy missing field becomes null, present names validated; existing audit/outbox relationships and retention remain. Local CLI reads same data file.

## Conventions and interfaces
CONTRIBUTING.md governs errors, audit, notifications and tests. HTTP request/response remains synchronous; worker retries outbox independently. No new configuration, service, cache or connection. Existing runtime authorization and log handling remain; no new UI.

## Verification status
Local item verification passed assignment, persisted legacy and restart, worker delivery, API filtering, CLI/report and full regression. The integrated system test and clean-copy release verification passed on the returned source. Service maintainers own revalidation with npm test after service or harness changes. No remote relay target was requested or observed; local delivery to the configured notifier is not evidence of an external relay.

## Superseded
None.
