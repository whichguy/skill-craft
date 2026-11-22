# Help desk tickets specification

## Requirements

### R-1 Agent-directed duplicate merge

Basis: “Let agents merge duplicate tickets.” (2026-11-21). Existing HTTP actor, errors and lifecycle come from docs/api.md. Eligibility, one-hop linkage, retry and notification policy are implementation defaults chosen for this request.

- R-1a. An agent selects an existing non-closed duplicate and a different existing non-closed canonical ticket with `POST /tickets/:id/merge` and JSON `{"into":"T-0042"}`. A success returns 200 and the closed source with `mergedInto`. GET and list show the link and the duplicate belongs to closed results. Canonical ticket fields, both requesters and their earlier histories are preserved. Verify over loopback HTTP.
- R-1b. Missing or malformed body fields or merge IDs yield 400. A well-formed missing ticket yields 404. Self-merge, a closed source or target, a merged target, a different target on retry, and moving a canonical ticket with existing duplicates all conflict with 409. A same-target retry succeeds with the prior source even if the canonical ticket subsequently closed. Existing patch and transition rules keep the duplicate closed. Verify envelope and unchanged state over HTTP.
- R-1c. A successful merge appends one `ticket.merged` audit entry to the duplicate, with status and target changes and normal X-Actor attribution (system fallback). It enqueues no notification. Rejected calls and matching retries add no audit or outbox event. Verify through history and outbox reads.

### R-2 Durable storage and reader compatibility

Basis: accepted decisions 5, 7 and 8, README.md Command line, and R-1.

- R-2a. TicketStore owns the merge and prepares the ticket and audit together. A failed save leaves in-memory ticket, audit, outbox and disk unchanged. A successful save survives restart. Competing requests serialize through the existing synchronous store, and only the first differing merge succeeds. Verify via save-failure injection, concurrent HTTP and restart.
- R-2b. Version-1 snapshots without a merge link remain readable; ordinary records keep their API shape. A persisted merge link is valid only on a closed source and points directly to a different existing unmerged record. Invalid links stop load. Verify with data-file fixtures. Preserve cursor pagination, ordinary lifecycle and raw report columns using the suite and a raw CLI check.

## Non-functional requirements

Internal HTTP access retains the existing network boundary and audit-label convention. A merge adds only the target ID and creates no new requester-data exposure through notifications. Synchronous single-process storage and atomic snapshot installation follow the existing volume assumptions in decision 8. No new latency objective, deployment, browser surface or external dependency applies.

## Retired

None.

## Questions settled

- Q1 Result. R-1a and R-1b define a 200 with the closed duplicate and target, or an error envelope. R-2a requires all-or-nothing completion on save failure.
- Q2 Authority. R-1a and R-1c use the internal HTTP API and the established audit actor to identify who closed and linked the duplicate.
- Q3 Existing machinery. R-1c and R-2a reuse audit, the data file and the outbox boundary. A single request changes one ticket and appends one audit entry.
- Q4 Hostile and odd input. R-1b inherits JSON parsing and the configured body-size limit, rejects unknown fields and uses canonical IDs to prevent arbitrary values entering the link.
- Q5 Forms. R-1a and R-1b accept one exact canonical ticket ID as the path value and a single JSON string ID as `into`, with no surrounding whitespace or case folding.
