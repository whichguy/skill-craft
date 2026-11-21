# Help desk tickets

## Requirements

### R-1 Bulk-create tickets from a CSV

Basis: “Let agents upload a CSV to bulk-create tickets.” (2026-11-21). Existing single-create and response conventions follow [Tickets API](../api.md#conventions), [decision 4](../decisions/0004-error-envelope.md), and [decision 2](../decisions/0002-prefixed-sequential-ids.md). The starting baseline is the repository at 0a92b60773801765a3ebc4e73776d9ed2b9f8917. These criteria are due for verification against the local HTTP service.

- R-1.a. An internal API caller can POST a raw UTF-8 CSV file to `/tickets/import` with `Content-Type: text/csv`. The first record must contain the case-sensitive headers `title`, `requester`, and optionally `priority` in any order. A blank priority or absent priority column selects `normal`. Accept LF and CRLF, optional UTF-8 BOM and final line break, quoted commas and doubled quotes. Verify over HTTP with multiple records and exact field values, including the ordinary single-ticket validation rules.
- R-1.b. Return 201 and `{"items":[...]}` containing the created open tickets in CSV order. For a fresh service, the file `requester,title\nfirst@example.test,"VPN, floor 2"\nsecond@example.test,Printer` creates `T-0001` and `T-0002` with priority `normal`. Verify the response, listing and ticket reads over HTTP.
- R-1.c. A wrong media type, invalid UTF-8, missing or extra headers, unknown or duplicate headers, zero data rows, malformed CSV, unexpected column counts, or invalid ticket fields return the standard 400 `invalid` envelope. Fail on the first error and identify the logical record number when the error belongs to a record (row 1 is the header). A rejected batch leaves tickets, counters, audit, and outbox intact. Verify through HTTP with valid first and invalid later records followed by a successful creation.
- R-1.d. The real entry point uses the same internal access boundary and `X-Actor` attribution as POST /tickets. With header `X-Actor: casey`, each ticket has a normal `ticket.created` audit event attributed to casey and one receipt in the existing outbox. Verify both readbacks. The importer keeps no file or import history, and a second successful submission creates a second batch. The notification worker continues to own delivery.

### R-2 Publish the whole batch as one change

Basis: S1 and [decision 8](../decisions/0008-json-data-file.md), with [decision 6](../decisions/0006-notification-outbox.md) and [decision 7](../decisions/0007-append-only-audit-log.md). The current scope is one service process owning its store. Verification is due at the local store/persistence and HTTP boundaries.

- R-2.a. Commit ticket, audit, outbox and sequence changes together. A configured version 1 file is saved once, and reopening it exposes all rows, prior tickets and associated records. Simultaneous requests allocate distinct IDs because commit is synchronous. Verify persistence by reopening a disposable file and via concurrent HTTP requests.
- R-2.b. On a failed save, publish no in-memory import changes and consume no ticket, audit or outbox IDs. Verify with a failing persistence boundary followed by a successful retry. HTTP reports unexpected save errors through the standard 500 envelope. Memory-only mode retains state for the service lifetime as before.

## Non-functional requirements

Reject bodies over the existing configurable `MAX_BODY_BYTES` (default 65536) and batches above 500 data rows before writing. Verify both limits, including acceptance at 500 rows. Run on Node.js 22+ with only built-in modules (CONTRIBUTING.md). Existing request logging covers the route and its status without retaining file bytes. No rendered UI or additional service is in scope.

## Retired

None.

## Key questions

- K1 Help desk agents use the internal HTTP API and read newly created tickets (R-1).
- K2 Single-ticket creation, ticket lifecycle, CLI and worker contracts carry forward (R-1, R-2).
- K3 Raw text/csv in, 201 JSON items or the standard error envelope (R-1).
- K4 Columns, defaults, malformed inputs and bounds are defined in R-1 and Non-functional requirements.
- K5 The owner is TicketStore, with a synchronous commit to optional version 1 storage (R-2).
- K6 Node.js 22+ with built-ins only (Non-functional requirements).
- K7 The HTTP, ticket validation and store boundaries are inherited (R-1, R-2).
- K8 Loopback HTTP and disposable store checks confirm the acceptance lines (R-1, R-2).
- K9 Delivery is the local checkout, verified through the real HTTP API (R-1).
- K10 Body and row ceilings plus actionable diagnostics (R-1 and Non-functional requirements).
- K11 Failure must leave all state intact (R-1, R-2).
- K12 Agents are help desk staff and their audit actor uses the existing request header (R-1).
