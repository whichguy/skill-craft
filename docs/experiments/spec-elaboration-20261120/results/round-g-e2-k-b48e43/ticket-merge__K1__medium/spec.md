# Help desk ticket service specification

## Requirements

### R-1 Agent-triggered duplicate merge

Basis: “Let agents merge duplicate tickets.” (2026-11-21). Existing write conventions in docs/api.md and lifecycle in src/tickets/states.js govern. The operation uses explicit IDs selected by the agent, with the current internal API and X-Actor convention. No other actor roles or automated matching are in scope.

- **R-1.a** Through local HTTP, create T-0001 and T-0002, then POST /tickets/T-0001/merge with {"into":"T-0002"} and X-Actor: dana. Expect 200 and T-0001 closed with mergedInto T-0002. GET and the closed-ticket list expose the link. GET T-0002 returns the same ticket as before, including its timestamp. The duplicate keeps its title, requester, priority, creation time and ID. The merge action may close an open, in-progress or resolved source. Ordinary transition rules remain in effect.
- **R-1.b** Local HTTP returns 400 invalid for malformed IDs or request body and 404 not_found for an unknown ticket. Self-merge, a closed source or target, and changing a previously merged ticket's destination return 409 conflict. An exact retry returns the current duplicate with its original merge timestamp and adds no events, including after restart. If the surviving ticket later merges, the earlier link remains followable through the next ticket. The duplicate cannot transition or be edited.

### R-2 Audit and notifications

Basis: duplicate merge request (2026-11-21), CONTRIBUTING and ADRs 0006–0007. Audit remains append-only with the existing access boundary and retention.

- **R-2.a** Local HTTP audit shows exactly one ticket.merged entry for the duplicate, with dana, the old/new status and the old/new link. A target's history remains unchanged. Rejections and retries leave audit and outbox unchanged.
- **R-2.b** Merge does not resolve the underlying issue and queues no requester notification. The HTTP outbox retains the original creation events; existing transition tests confirm resolution notices still work.

### R-3 State consistency and compatibility

Basis: duplicate merge request (2026-11-21) and ADR 0008. The store owns the source link and audit. Clients on the internal API observe committed state. IDs and histories remain durable for the lifetime of the tickets.

- **R-3.a** The file-backed test opens a version 1 file without merge fields, merges via HTTP, and restarts. The subsequent GET and audit return the same merge result. Existing unmerged JSON retains its original shape.
- **R-3.b** A synchronous save failure leaves live ticket and audit state unchanged. Retry after recovery produces one merge. Two calls are serialized by the store; identical requests observe one effect and competing destinations receive a conflict for the second attempt. Check at the store and local HTTP boundaries.

## Non-functional requirements

Reuse the existing body limit, request error envelope and platform dependencies. Verify local compatibility through npm test. The API has no new UI, identity mechanism, retention partition or external dependency. No new latency target was specified. Scenarios are defined for local verification and have no deployed verification dependency.

## Retired

None.
