# Help desk ticket service specification

## Requirements

### R-1 Agent-directed duplicate merge

Basis: “Let agents merge duplicate tickets.” (2026-11-21). Preserves the existing HTTP mutation and actor conventions in docs/api.md. Adds a single-pair operation to the existing trusted internal API. An agent explicitly identifies both records.

- **R-1.a** POST /tickets/:id/merge with JSON containing only the required canonical ticket ID `targetId` returns 200 with the duplicate ticket, now closed and containing `mergedInto` equal to the target ID. GET by either ID still works. Only the source's status, link and updated time change. Verify against the local HTTP service with records that have different titles, priorities and requesters.
- **R-1.b** Malformed IDs, wrong or extra fields, malformed or oversized bodies and self-merges return 400. Valid IDs missing a record return 404. These use the existing error envelope. Ticket IDs are case-sensitive canonical strings and are accepted without trimming. Verify status, error code and no side effects over HTTP.
- **R-1.c** A new merge requires distinct non-closed source and target tickets. A former duplicate cannot become the target or be relinked. A ticket with inbound links cannot become a duplicate. Multiple duplicates may link to the same primary, which may transition normally and later close. Disallowed states return 409. Repeating the same source and target returns the existing closed record and adds no history, even after the primary closes. Verify over HTTP, including competing source requests.

### R-2 History, recovery and compatibility

Basis: the 2026-11-21 merge request and the existing contracts in docs/api.md, README.md and decisions 0004, 0007 and 0008. Retains ticket identity, history, handler limits, outbox behavior, status vocabulary and raw report columns.

- **R-2.a** The source history appends one `ticket.merged` entry with the existing actor convention and UTC timestamp, the previous and closed statuses, and `mergedInto` from null to the target ID. Both prior histories remain available. The merge is internal and queues no notification. Verify via HTTP audit and outbox readback.
- **R-2.b** The service owns the optional link in memory and saves it with the source change and audit in the same DATA_FILE update. After restart the link and audit survive. Legacy records without the field retain their previous shape. Current readers reject an invalid link, including missing targets, self-links, chains and linked non-closed sources. A failed save returns 500 and keeps live and saved ticket, audit and outbox state as they were. Verify with version 1 fixtures, restart, injected save failure and a successful retry.
- **R-2.c** The closed duplicate leaves active status filters and appears in closed filters. It still occupies one row in unfiltered lists and in the weekly count. CLI raw columns stay id, status, priority and title. Verify HTTP lists, CLI raw output and the weekly report against a fixture written by the real merge route.

## Non-functional requirements

Reliability and integrity are defined by R-1.c and R-2.b under the single-process owner documented in decision 0008. The merge uses the existing body limit and internal access boundary. Separate requester records remain in the trusted API and data file. No new requester-facing messages, dependency, configuration, graphical interface, production service target or latency SLA is introduced. Compatibility and operability are observable through the HTTP contract, audit, restart and existing CLI/report tools.

## Questions settled

- Q1 Result. R-1.a, R-1.b, R-1.c and R-2.b define success, conflict, invalid input, missing records and a failed save with no partial merge.
- Q2 Authority. R-1 uses the existing internal API and lets its agents explicitly close a duplicate and point it to the primary. R-2.a records X-Actor attribution.
- Q3 Existing machinery. R-1.b and R-2 use the shared request limit, store, audit, data file and CLI/report contracts. Each accepted request affects one source and adds one audit entry.
- Q4 Hostile and odd input. R-1.b applies strict JSON, field and ID validation and the configured request limit. R-2.b checks links before loaded state is exposed.
- Q5 Forms of a value. R-1.a and R-1.b accept canonical case-sensitive IDs and one required named field. R-2 defines the optional link, null audit predecessor and UTC timestamp.
