# Ticket service specification

## Requirements

### R-1 Upload a CSV to create tickets

Basis: the 2026-11-21 request to let agents upload a CSV to bulk-create tickets. Preserve single-ticket
creation, HTTP audit attribution and the operator CLI's read-only behavior (docs/api.md and README.md).
The following import behavior is added and awaits implementation and local acceptance.

- A1 (HTTP). POST /tickets/import accepts raw UTF-8 text/csv, including an optional UTF-8 BOM, CRLF or LF
  record separators and an optional final newline. The first record must have unique, case-sensitive
  title and requester headers, with optional priority, in any order. Quoting supports commas and doubled
  quotes. Data records must match the header width. Empty or omitted priority uses normal. The existing
  field validation governs title, requester and nonempty priority.
- A2 (HTTP and read-back). With an empty store and X-Actor dana, send the records
  `title,requester,priority`, `"VPN, ""office""",maria@example.com,high` and
  `Printer,jay@example.com,`. Expect 201 with items T-0001 and T-0002 in that order, open, with priorities
  high and normal. GET /tickets sees both. Each has a ticket.created audit entry attributed to dana and
  one corresponding pending notification when the worker is off. With DATA_FILE, restart and read both
  tickets and their side effects. Entries with the same valid inputs are distinct tickets, as with
  individual creation. Missing or blank X-Actor uses system.
- A3 (HTTP). Wrong media type, invalid UTF-8, missing or invalid header, syntax or width errors, an invalid
  ticket field, or an upload with no data records receives a 400 invalid envelope. CSV record diagnostics
  use one-based record numbering with the header as record 1. With a valid first row and a second row
  using priority impossible, expect an error identifying record 3 and priority. GET /tickets and
  GET /admin/outbox remain empty. The next single create receives T-0001.
- A4 (store and persistence). With DATA_FILE, the live process owns shared state and saves the batch
  through one atomic file replacement. If saving fails, ticket IDs, audit sequence, tickets and outbox
  remain at their prior state. A following successful import uses the next previously available IDs.
  Confirm with injected persistence and a real file reload. Upload contents are request-local. Only
  ordinary validated domain records persist. The worker delivers pending notifications through its
  existing retry flow. A second successful submission creates new tickets.

## Non-functional requirements

- R-2 (HTTP). Enforce MAX_BODY_BYTES as for JSON requests and allow at most 500 data records per request to
  bound synchronous mutation and response size. Both limits yield a 400 invalid envelope without
  mutation. Check exact and overflow cases over loopback. Keep the Node 22+ standard-library constraint.
- R-3 (operability). Document a complete curl upload and the row, format, response and retry rules.
  Give actionable CSV errors without including raw data rows in errors. Check the documented command
  behavior against the local API. Existing request logging and internal network boundary apply.

## Retired

None.
