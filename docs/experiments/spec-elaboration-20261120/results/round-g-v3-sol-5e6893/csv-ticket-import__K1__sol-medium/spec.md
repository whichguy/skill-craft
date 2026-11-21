# Help desk ticket service specification

## Requirements

### R-1 CSV ticket import

Basis: “Let agents upload a CSV to bulk-create tickets” (2026-11-21). Existing interface and roles are described in docs/api.md and the internal service boundary in docs/operations.md. The local HTTP API is the upload surface.

- Accept raw UTF-8 at POST /tickets/import with Content-Type text/csv. Allow BOM, LF and CRLF, field quoting, doubled quotes and one optional trailing line ending. The required header names are title and requester with optional priority, in any order. Blank priority defaults to normal. On a fresh service, the bytes `title,requester,priority\n"Printer, offline",ana@example.com,high\nVPN,bob@example.com,` yield 201 with JSON `{items}` containing T-0001 and T-0002, open, high and normal respectively, in file order. Confirm via live HTTP and GET /tickets.
- Return 400 invalid in the existing envelope for missing or unsupported media type, bad UTF-8, missing/duplicate/unknown headers, empty input, missing data, incorrect column count, broken quoting, or values that fail existing single-ticket validation. Identify the first bad logical CSV record (header is record 1) for record-level errors. An embedded newline can be parsed in a quoted field but cannot make a ticket whose fields violate single-line validation. Confirm through real HTTP, e.g. `title,requester,priority\nVPN,ana@example.com,emergency` returns 400 with record 2 and no ticket.
- Preserve single-ticket JSON API and the read-only CLI, report, and existing error contracts. Confirm via the full suite.

### R-2 Atomic, audited creation

Basis: S1 and existing ADRs 2, 6, 7, 8. Every accepted row receives the next ordinary ID and a ticket.created audit entry with X-Actor or system fallback plus a normal receipt notification. Reject the entire batch on any bad record. A pre-commit storage failure keeps ticket, audit, outbox and ID state intact. With DATA_FILE configured, an accepted batch reads back after restart using the existing format. A new successful upload always creates new tickets. No file, cache, client session or batch object is retained. Confirm with live HTTP read-back and restart and an injected store save failure.

### R-3 Resource limits and access

Basis: S1 and existing README configuration/internal network rules. The input is limited by MAX_BODY_BYTES and 100 ticket records. Test 100 and 101 rows and a configured byte cap at and over the boundary. The API uses existing internal access and X-Actor attribution. Error text contains record numbers and validation messages without echoing data rows. Ticket fields continue under existing storage and retention rules.

## Non-functional requirements

The bounded body and row checks run before store mutation. Verify the single persistence save with the store test. No UI, live relay check, deployment, new account layer or schema changes are required for local delivery. Runtime remains dependency-free Node 22+; run npm test and git diff --check.

## Key questions

- K1 Internal help desk agents use the HTTP endpoint and see created tickets (R-1).
- K2 Single-ticket creation, reporting and normal notifications retain their contracts (R-1, R-2).
- K3 Raw UTF-8 text/csv and JSON {items} with 201 (R-1).
- K4 Header, optional priority, malformed batch and limits (R-1, R-3).
- K5 TicketStore owns persistent ticket/audit/outbox state and publishes atomically (R-2).
- K6 Node 22+, standard library (Non-functional requirements).
- K7 HTTP/validation/store seams inherited (R-1, R-2).
- K8 Live HTTP, restart and store failure with npm test (R-1 through R-3).
- K9 Guarded local source return (environment.md).
- K10 Input limits, existing internal access and minimal errors (R-3).
- K11 Partial creation or reused identifiers are detected by rollback and regression checks (R-2).
- K12 Agent is the help desk role described in README.md and ADR 4, attributed by X-Actor (R-1, R-2).
