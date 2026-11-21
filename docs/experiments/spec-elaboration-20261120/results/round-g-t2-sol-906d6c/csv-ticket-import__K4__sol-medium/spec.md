# Help desk tickets specification

## Scope

Internal ticket-service consumers use HTTP for writes. The read-only CLI and existing single-ticket routes keep their contracts from README.md and docs/api.md.

## Requirements

### R-1 CSV ticket creation

Basis: “Let agents upload a CSV to bulk-create tickets.” (2026-11-21). Existing field and actor contracts are in docs/api.md under Create a ticket and Conventions.

- Send a UTF-8 CSV as the request body to POST /tickets/import with Content-Type: text/csv. Accept a UTF-8 BOM, LF or CRLF, quoted cells, doubled quotes and columns in any order. The header must contain title and requester and may contain priority. An absent or blank priority means normal.
- A CSV containing `title,requester,priority` followed by `Printer jam,help@example.com,high` and `VPN drops,ops@example.com,` returns 201 with items in that order. In a fresh service the IDs are T-0001 and T-0002, both open, with high and normal priorities. Confirm via the real HTTP endpoint and by reading both tickets back.
- Reject wrong media type, invalid UTF-8, malformed CSV, missing or duplicate headers, unknown headers, wrong field counts, invalid ticket values, empty batches and oversized bodies using the 400 error envelope. Identify the 1-based CSV record in errors tied to a record. A valid first row followed by an invalid priority must create zero tickets and leave the next ID unchanged. Confirm via HTTP against fresh state.
- Record each ticket's existing ticket.created audit and queued requester receipt. A single batch survives restart with all corresponding entries. A failed persistence save leaves the live ticket state, sequence, audit and outbox unchanged. Confirm via HTTP restart and a controlled store save failure.
- Each accepted request creates new tickets. The request body is transient and is never saved separately or included in errors. The ticket fields, audits and outbox follow existing retention and access rules. The shared store serializes synchronous mutations across HTTP requests and worker callbacks. Existing single-ticket create and read paths remain covered by the full suite.

## Non-functional requirements

Honor MAX_BODY_BYTES, 65536 bytes by default, and report oversized requests through the existing envelope. No new dependency or application identity surface. The HTTP-only scope has no rendered interface.

## Retired

None.
