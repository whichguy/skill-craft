# Help desk tickets specification

## Requirements

### R-1 Agent CSV import

Basis: “Let agents upload a CSV to bulk-create tickets.” (2026-11-21). Existing creation and actor rules are in [Tickets API](../api.md) and decisions 4, 6, 7 and 8.

- Send a UTF-8 file as the raw `text/csv` body of `POST /tickets/import`. Header names `title` and `requester` are required, `priority` is optional, and order is flexible. Accept UTF-8 BOM, LF or CRLF, optional final newline, quoted commas and doubled quotes. Blank or omitted priority defaults to normal. A real HTTP test sends `priority,requester,title\r\n,agent@example.test,"Printer, floor ""2"""\r\nhigh,other@example.test,VPN` and observes 201 with two tickets in file order, the first with title `Printer, floor "2"` and priority normal and the second high.
- Use the existing ticket rules. Reject non-CSV media type, invalid UTF-8, malformed CSV, missing/unknown/duplicate headers, empty or header-only files, uneven rows, and invalid ticket fields. Return 400 `invalid` using the existing envelope with the CSV record number (header counts as 1) for file content errors. A real HTTP test sends a valid row before an invalid row and verifies no tickets, audit entries or outbox events and no consumed ticket IDs.
- Respect the service request byte ceiling, including UTF-8 bytes. HTTP checks cover the exact ceiling and one byte over. Parsed data is request-local. Exported CSV content is never stored wholesale or logged. Existing request logging records status and route.

### R-2 Imported ticket consistency

Basis: ticket creation rules in [Tickets API](../api.md), [notification outbox](../decisions/0006-notification-outbox.md), [audit log](../decisions/0007-append-only-audit-log.md) and [JSON data file](../decisions/0008-json-data-file.md).

- Create open tickets with sequential IDs, normal lifecycle, one creation audit entry with `X-Actor` or default `system`, and one normal receipt notification queued per ticket. A real HTTP test inspects list, per-ticket audit and outbox, then reopens the data file and verifies that state and the next ID.
- Treat each request as one committed batch. Validation failure or a data-file failure leaves earlier state and all sequences intact. Store-level tests inject an unsuccessful save and check the snapshot and next valid write.
- The service owns shared ticket state. One process serializes batch publication with other synchronous mutations, and file-backed state persists across restarts. Uploads have the same identity and repeat-submit semantics as ordinary POST creation. A repeated successful upload creates fresh tickets. No new job or upload storage is needed.
- Preserve JSON creation, listing, transitions, the data file format, read-only tools and requester notification delivery. Verify with the existing suite.

## Non-functional requirements

The HTTP API enforces the existing MAX_BODY_BYTES ceiling (default 65,536) and echoes neither file contents nor invalid cell values in errors. No new runtime dependencies or UI. No deployed target was supplied. Local HTTP and persistence verification is pending implementation.

## Retired

None.
