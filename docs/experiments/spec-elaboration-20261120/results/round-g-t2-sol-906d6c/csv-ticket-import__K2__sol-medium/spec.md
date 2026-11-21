# Ticket service specification

## Requirements

### R-1 Upload tickets from CSV

Basis: “Let agents upload a CSV to bulk-create tickets” (2026-11-21). Existing fields and responses are defined in docs/api.md. The internal HTTP API remains the mutation surface.

- C-1. POST /tickets/import with Content-Type: text/csv accepts a UTF-8 CSV file, with optional BOM and LF or CRLF. It requires title and requester headers and accepts optional priority, in any order. Quoted fields support commas and doubled quotes. Blank or omitted priority defaults to normal. A successful upload returns HTTP 201 and {"items":[...]} in CSV order with open tickets. Verify at the live HTTP boundary with both newline styles and read the created tickets back.
- C-2. Reject empty uploads, header-only files, unknown or duplicate headers, wrong-width data, malformed quotes, invalid UTF-8, invalid ticket fields, and a missing or incorrect media type with 400 in the existing JSON envelope. Report the source line for record-specific failures. Verify with table-driven HTTP cases. The header is line 1. Embedded line breaks parse as CSV syntax but ticket fields must obey the existing single-line validation rules.
- C-3. Bound uploaded bytes by MAX_BODY_BYTES. Verify at the exact limit and one byte over with the existing error envelope. Keep JSON creation behavior as documented and run its existing tests.

### R-2 Apply the batch together

Basis: all-or-nothing is the selected batch failure behavior. Consequences of creation follow docs/api.md and decisions 6–8.

- C-4. For each committed row, allocate an ID in normal sequence and write one ticket.created audit entry attributed to X-Actor (or system) and enqueue one existing requester notification. Verify IDs, audit, outbox and restart with a configured data file. The worker owns delivery after commit.
- C-5. A rejected upload or failed save leaves tickets, audit, outbox and ID allocation intact. Verify an invalid later row and a simulated persistence failure followed by a successful retry. A repeated successful request is a new creation, as with POST /tickets.

## Non-functional requirements

The existing request byte cap is the upload capacity bound. The upload stays in the current request lifecycle, with no retained CSV file. Ticket data follows the existing store and access boundary. There is no graphical interface, so visual requirements do not apply. No performance SLA is established by the request.

## Behavior model

| Flow | Transition | Owner and result | Cases |
| --- | --- | --- | --- |
| F-1 Import | T-1 Validate then commit | An agent sends CSV to the internal HTTP API. TicketStore stages records, saves one snapshot if configured, then publishes tickets, audit and outbox together. A subsequent request sees committed state. | C-1, C-3, C-4 |
| F-2 Rejection | T-2 Reject request | Invalid input returns 400. A failed save returns 500. The old store stays visible and a corrected retry may proceed. | C-2, C-3, C-5 |

The upload is transient request state. The service owns the durable ticket, audit, and notification records when DATA_FILE is enabled. Mutations commit synchronously in one process. The existing deployment model uses one writer per data file. There is no migration, new role, separate data retention rule, or import job.

## Retired

None.
