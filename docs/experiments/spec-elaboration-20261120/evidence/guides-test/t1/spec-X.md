# Help desk ticket requirements

## Requirements

### R-1 CSV upload creates tickets

Basis: “Let agents upload a CSV to bulk-create tickets” (2026-11-21). Existing create contract: docs/api.md, Create a ticket. Direct CSV and response conventions are design defaults.
- R-1a: POST /tickets/import with text/csv accepts one UTF-8 CSV with a header and at least one data record. Required columns are title and requester. The optional priority column defaults to normal when absent or blank. Header order is free. Header names are case-sensitive and may have surrounding whitespace.
- R-1b: LF and CRLF, optional UTF-8 BOM, and standard double-quoted CSV fields with doubled quote escapes are accepted. Embedded newlines can be parsed in a quoted field, then existing single-line ticket validation applies.
- R-1c: HTTP 201 returns {"items":[...]} with normal open tickets in CSV order. Each has a sequential ID, X-Actor audit attribution and one queued creation notification.
- R-1d: A bad header, bad quoting, incorrect column count, invalid field, empty upload, unsupported media type, or invalid UTF-8 returns 400 in the existing error envelope. Report the 1-based CSV record when applicable (header is record 1). Blank records are invalid. A final line terminator is permitted.
- Confirmation: CSV upload over real local HTTP, followed by ticket, audit and outbox reads. No hosted target is specified. JSON create, ticket fields, read-only commands and the existing trust boundary continue as documented.

### R-2 A batch is saved as a unit

Basis: scope wording above plus CONTRIBUTING.md, Changes go through the store, and docs/decisions/0008-json-data-file.md.
- R-2a: A rejected batch leaves tickets, audit, outbox and ID counters unchanged. A save failure returns the existing 500 envelope and leaves visible state unchanged. A corrected request can use the next ID.
- R-2b: A successful batch persists tickets, audit and outbox together through DATA_FILE when configured. Ordinary worker behavior and the persisted schema continue. Concurrent requests within one service serialize their mutations. Repeating a successful request creates another batch. No idempotency key, preview or background-import job.
- Confirmation: rejection with a valid first row, restart after success, and a simulated save failure with retry. Existing data is compatible.

## Non-functional requirements

Reuse MAX_BODY_BYTES (default 65536 bytes) to bound buffering, including chunked uploads. Use the existing internal trust boundary and X-Actor attribution. Upload contents are transient except for ordinary stored ticket fields and their audit and outbox effects. The API has no GUI. No independent throughput or latency target was provided.

## Behavior model

F-1: an internal agent sends the CSV bytes; the server checks media type, size, encoding, header, rows and actor; valid data enters T-1; the response returns persisted tickets. Malformed input enters T-2. Persistence failure enters T-3. Existing delivery worker subsequently consumes committed outbox events.

| Transition | Before and guard | Operation and observation | Cases |
| --- | --- | --- | --- |
| T-1 | Existing ticket state, valid file and actor | Store commits the batch and returns 201. A repeat allocates fresh IDs. | CSV-1, CSV-3 |
| T-2 | Body or actor invalid | Returns 400. No state change. Correct the upload and retry. | CSV-2 |
| T-3 | Valid upload, save fails | Returns 500. Prior state still visible. Retry can allocate same first ID. | CSV-4 |

## Retired

None.
