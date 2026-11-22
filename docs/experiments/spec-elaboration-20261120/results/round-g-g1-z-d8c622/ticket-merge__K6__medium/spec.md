# Help desk ticket requirements

## Requirements

### R-1 Merge a duplicate into a canonical ticket

Basis: “Let agents merge duplicate tickets.” (2026-11-21). Preserve the internal HTTP boundary and actor-label semantics in docs/api.md, Conventions and Endpoints. An agent submits an explicit source and target pair.

- On an eligible pair, `POST /tickets/T-0001/merge` with `{"into":"T-0002"}` and `X-Actor: dana` returns 200 and the source ticket, now `closed` with `mergedInto: "T-0002"` and a new `updated` time. The source retains its id, title, requester, priority and created time. The target is identical to its state before the merge. Confirm through HTTP response and subsequent GETs using two newly created tickets in a fresh service and an advanced test clock.
- Unfiltered lists still include both records in ID order. The source appears under `status=closed` and is absent from its previous status filter. Confirm on the same API, including its existing cursor shape. Closed sources reject edits and ordinary transitions through their existing guards.

### R-2 Reject invalid merges and allow safe retries

Basis: duplicate-tickets request (2026-11-21) and the error/lifecycle contracts in docs/api.md and ADR 0004. The same pair can be retried with 200 and equal source state, even after the canonical ticket closes. Different eligible sources may merge into the same canonical ticket.

- Malformed request objects, unknown fields, a missing or noncanonical `into` ID, and merging an existing ticket into itself produce 400 `invalid`. Missing source or target tickets produce 404 `not_found`. As with other routes, an unknown source path ID is a missing resource. Confirm with API tests of each request shape.
- A new merge conflicts (409 `conflict`) when the source or target is already closed, the source has been merged into a different ticket or is the canonical ticket for an earlier merge, or the target itself has been merged. The explicit same-pair retry takes precedence over the closed checks. Confirm the conflict cases and repeat case with HTTP and compare states and audit counts before and after.
- The store applies each accepted write synchronously in one process. On two competing requests for the same source with different targets, exactly one succeeds and one conflicts. Confirm through concurrent loopback clients.

### R-3 Preserve audit and durable state

Basis: duplicate-tickets request (2026-11-21), ADRs 0006–0008, and CONTRIBUTING.md Changes go through the store. Ticket records, audit and outbox remain owned by the store and persist under the existing DATA_FILE boundary when enabled. The link lives for the lifetime of the ticket. The existing internal API and CLI can read the record or audit. No copying of requester data, deletion, or new requester notification is required for this internal action.

- Append exactly one `ticket.merged` entry to source history on first success with actor, timestamp and before/after status and link. Preserve prior audit, canonical history and existing outbox. A retry, invalid request or failed save adds no audit record and changes no ticket. Confirm through audit and outbox reads and a controlled save exception followed by a successful retry.
- With DATA_FILE enabled, restarting preserves the closed source, link and audit entry. Version 1 files without the optional link still load. A present link must point from a closed ticket to a distinct, existing, unmerged ticket, which may have closed since the merge. Reject files violating that invariant. Verify via written files and reopen, including a legacy file and invalid links.

### R-4 Preserve the operator consumers

Basis: README Command line and docs/operations.md The command line and the weekly report. Preserve the four ordered TSV columns (ID, status, priority, title) and the report count keys. The source contributes one closed ticket and remains visible in its history. Verify real read-only CLI and report processes on a merged fixture.

## Non-functional requirements

- Compatibility: existing Node.js 22+ and built-ins only, standard 400/404/409 envelopes, same body-size limit and X-Actor validation.
- Integrity: failed pre-rename save leaves visible state unchanged. Report only what the HTTP read and test data file show. Single-process synchronous support matches the existing deployment model.
- Information boundary: X-Actor provides attribution under the existing internal access model. No new external recipient, route, session, cache, or async job is introduced. No UI surface changes.
- Performance: use the existing full-state snapshot model and avoid new request-time I/O beyond its one save. No measured performance target is specified. Preserve error and audit diagnostics through their current sinks.

## Open questions

No additional product decision blocks local implementation. Canonical-chain policy and the decision to omit a notification are implementation defaults for the requested internal operation. Production identity and access behavior were not observed and are outside the selected local delivery.

## Retired

None.
