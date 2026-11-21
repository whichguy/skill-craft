# Help desk ticket service specification

## Requirements

### R-1 Upload tickets as CSV

Basis: “Let agents upload a CSV to bulk-create tickets.” (2026-11-21). API source: docs/api.md, Create a ticket and Error envelope; README, Configuration. The existing JSON creation and read APIs retain their contracts.

- An agent with existing internal API access can send raw UTF-8 text/csv to POST /tickets/import. The first nonempty record is a header with title and requester, and optionally priority, in any order. Unknown and duplicate column names are errors. C-1 confirms a reordered, BOM-prefixed CRLF upload that contains a quoted comma and an escaped quote. The parser also accepts LF and a final record without a terminator. Empty physical lines are ignored.
- A successful upload returns HTTP 201 with JSON { items }, containing complete, open tickets in input order. Priority defaults to normal when its column is omitted or its cell is blank. Titles, requesters and explicit priorities follow existing create validation. C-1 checks decoded fields, IDs, state and default/explicit priority via the real HTTP route.
- Missing/empty required values, invalid priority, invalid UTF-8, bad header or quotes, inconsistent cell counts and no data each produce 400 invalid. Record-specific failures include a CSV row number, counting the header and ignoring empty physical lines. C-2 exercises these failures and verifies that list and outbox remain empty and the next valid submission starts at T-0001. Unsupported media type uses the same envelope.

### R-2 Apply import as one change

Basis: same request and existing contribution policy, docs/decisions/0002, 0006–0008. Ticket creation still owns sequence IDs, audit and one pending notification per record. Imported records are immediately visible through existing GETs; the worker owns subsequent delivery.

- The request either creates every row with X-Actor attribution and a normal creation audit entry and outbox event, or leaves all existing records and counters intact. With DATA_FILE, one save persists the batch under the existing v1 format. C-1 verifies GET, audit and outbox before and after restarting the service. C-3 injects a failed save and observes unchanged state and a successful retry with consecutive IDs.
- A completed request is an ordinary creation operation. Repeating a successful upload creates new tickets. No draft, deduplication key or separate upload record is retained. Import data follows existing ticket access and retention. Error messages refer to column/row rules and do not echo cells.

## Non-functional requirements

- Bounded processing under MAX_BODY_BYTES (default 65,536 bytes). A documented 100-ticket import cap is the synchronous operation's chosen default, limiting the number of ticket, audit and notification records assembled per request. C-4 checks exact limits and first rejection beyond each.
- Standard-library Node.js only. No persistence migration, additional service or client-side UI is required for the repository's HTTP deliverable. A deployed dashboard interaction has no identified target.
- Normal source delivery and verification are local; product acceptance uses the real loopback service and disposable data file.

## Retired

None.
