# Help desk ticket service specification

## Requirements

### R-1 Import tickets from a CSV

Basis is the 2026-11-21 request “Let agents upload a CSV to bulk-create tickets.” This adds an HTTP file upload for the internal agents described in README.md. Preserve the existing ticket and actor contracts in docs/api.md. The delivery surface is the local source and HTTP service.

- R-1.a. POST a UTF-8 file to `/tickets/import` with `Content-Type: text/csv` and optional UTF-8 charset. The header must contain `title` and `requester`, with optional `priority`, in any order. Accept LF and CRLF, optional UTF-8 BOM, quoted fields, commas and doubled quotes within quotes. Confirm over local HTTP by importing two records, with comma and quote in one title, one blank priority and one `high`. Expect 201 and `{ "items": [...] }` with tickets in file order.
- R-1.b. Reject invalid media type or UTF-8, empty or header-only input, invalid headers, malformed quoting, blank records, wrong column counts and invalid ticket fields with 400 `invalid`. Identify the first bad CSV record when the error can be located. The header is row 1. Confirm with malformed and invalid requests over local HTTP and verify no tickets, audit events or outbox entries appear. Existing title and requester rules require single-line values. An omitted or empty priority defaults to `normal`.
- R-1.c. Honor `MAX_BODY_BYTES` and a maximum of 100 data rows. Confirm 100 valid rows succeed and 101 fail. Configure a lower test byte limit to distinguish exact-limit and oversized files.

### R-2 Create imported tickets as one durable batch

Basis is the ticket, audit and persistence contracts in docs/api.md and docs/decisions/0006, 0007 and 0008, applied to the new upload.

- R-2.a. Every imported ticket receives its sequential ID, open status, creation audit entry with the normal `X-Actor` attribution and one pending receipt notification. Confirm over local HTTP using list, ticket audit and outbox with the worker off. Start empty. The two records in R-1.a receive T-0001 and T-0002. A subsequent JSON create receives T-0003. The outbox carries corresponding pending events and the audit entries are sequential.
- R-2.b. Publish all ticket, ID, audit and outbox changes together after one successful save when persistence is configured. A failed validation or save leaves live changes and sequence counters untouched. Confirm via save fault injection and a successful retry, and confirm accepted state persists by restarting the actual local service against its data file.
- R-2.c. Keep the upload body request-local. Its accepted ticket data follow existing store, logging and access rules. The worker sends notifications separately under its existing retry rules. Confirm no extra persisted state or notification job type. A second successful upload is a new create, so existing ticket IDs are never reused.
- R-2.d. Preserve the JSON create, list and operator reporting contracts, checked by the existing suite. No public delivery, app-level role system or schema migration is required.

## Non-functional requirements

The byte and row limits bound request-local memory and effects. Atomicity and restart compatibility are checked in R-2. CSV adds no dependency. Use synthetic requesters in tests. Production latency and availability are outside this source-delivery change. The service has an HTTP interface and no user interface change.

## Retired

None.
