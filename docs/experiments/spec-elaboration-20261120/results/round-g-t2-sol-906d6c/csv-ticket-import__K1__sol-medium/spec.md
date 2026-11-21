# Ticket service specification

## Scope

The internal help desk API creates, lists and tracks tickets with audit and requester notifications. See docs/api.md and README.md for the existing contract.

## Requirements

### R-1 Agent CSV upload

Basis: “Let agents upload a CSV to bulk-create tickets.” (2026-11-21). Existing JSON creation remains as in docs/api.md, Create a ticket. This adds an HTTP surface for the existing agent client role and X-Actor convention. Defaults below reflect the available API. Local HTTP checks are the due verification surface.

- POST /tickets/import accepts a raw UTF-8 text/csv body with a header and at least one data row. Headers title and requester are required, priority is optional, order is flexible, and duplicate and unknown headers are invalid. Accept BOM, LF or CRLF, optional terminal line break, quoted commas and escaped doubled quotes. Verify by uploading a reordered spreadsheet-style file over loopback.
- Each row obeys normal ticket creation validation. Missing priority or an empty priority cell defaults to normal. HTTP 201 returns { items: [...] } in row order, with each item an open ticket with its own sequential ID. Verify through the creation response and per-ticket HTTP reads.
- Wrong media type, invalid encoding, empty/header-only input, malformed CSV, wrong-width rows, invalid headers, and invalid ticket fields yield HTTP 400 in the standard envelope. Row errors name the first failing CSV record (header is row one). Verify errors and that a valid leading row leaves no state after later failure.

### R-2 State and recovery

Basis: docs/api.md audit, outbox and actor conventions and decisions 0006–0008; extends those guarantees to R-1. Verification due in HTTP/store tests with a disposable data file or injected save failure.

- The service commits all imported tickets, sequential IDs, ticket.created audits with the request actor, and pending notifications as one synchronous change. Read audit and outbox, and reopen the data file to confirm the same committed state.
- Validation or failed save leaves tickets, IDs, audit, outbox and durable state at their previous values. Confirm with an unchanged snapshot and successful retry after removing the failure.
- Parsed content lives only in the request; accepted ticket, audit and event data follow usual retention. Existing worker delivery happens after enqueue; it does not determine HTTP success. A repeat of a successful upload creates new tickets. Synchronous store operations serialize concurrent submissions within a process.

## Non-functional requirements

- Apply existing MAX_BODY_BYTES (65536 by default) to raw bytes. Confirm exact configured limit succeeds and one extra byte fails with no changes.
- Keep the existing internal trust and audit model. Return regular errors without CSV field contents in diagnostics or new payload logging. No UI surface.

## Retired

None.
