# Help desk tickets specification

## Requirements

### R-1 Bulk ticket upload

Basis: “Let agents upload a CSV to bulk-create tickets” (2026-11-21). The existing JSON creation contract in [API](../../docs/api.md), the read-only CLI in [README](../../README.md#command-line) and internal service access in [Operations](../../docs/operations.md#process) continue to apply. The specified upload shape is an implementation default for the agent workflow.

- An agent submits a file as the raw UTF-8 body of `POST /tickets/import` with `Content-Type: text/csv` (optional UTF-8 charset) and the existing optional `X-Actor`. A successful request returns HTTP 201 and `{ "items": [ ... ] }` with the full created tickets in input order. Confirm through HTTP and read back from the ordinary ticket endpoints.
- The header names `title` and `requester` are required, and `priority` is optional. Columns can be reordered and header names are case-sensitive. An omitted or blank priority defaults to `normal`; the ordinary priority values apply after trimming. Quoted fields, escaped quotes, commas inside quotes, an initial UTF-8 BOM, LF/CRLF and an optional final newline are accepted. The ordinary limits and priorities apply, including single-line title and requester. Confirm with uploaded fixtures.
- Empty/header-only files, missing, duplicate or unknown columns, malformed quoting, extra or missing cells, blank records, unsupported content type, malformed UTF-8 and invalid ticket fields return 400 with the service's error envelope. Where an error belongs to a record, the message names the CSV row (header is row 1). Confirm each failure and its diagnostic at the HTTP boundary. This flow uses the existing internal access and actor attribution. There is no new account, session, preview or upload history.

Replay fixture from an isolated, empty, worker-disabled service: use LF with header `requester,title,priority` and the records `maria@example.test,"VPN, ""floor 4""",` and `sam@example.test,Printer,high`. R-1 permits the upload and yields T-0001 then T-0002, both open, with priorities normal and high. R-2 permits reading both and their dependent records after the response. Submit the same file with the final `high` replaced by `later`. It yields 400 identifying row 3 and leaves the listed IDs at T-0001 and T-0002. This is a logical walk of the contract. Execution is due in implementation and consumer verification.

### R-2 All-or-nothing creation

Basis: the bulk-create request and the existing creation, audit and outbox contracts in [API](../../docs/api.md) and [decision 8](../../docs/decisions/0008-json-data-file.md).

- Open one ticket for each row, allocate sequential IDs, append one ordinary `ticket.created` audit entry with the request actor and queue one ordinary receipt for each requester. Confirm the order and contents through ticket reads, audit and outbox.
- Commit all rows together. An invalid upload or failed persistence leaves the prior tickets, audit, notifications and next identifiers intact. With DATA_FILE enabled, the service sees all the committed records on reopening the same version-1 file. Confirm via HTTP, a controlled save fault followed by recovery and a file reopen.
- HTTP success means creation committed. The worker continues to deliver receipts asynchronously using its existing retries. Requests share service-owned ticket state. A successfully repeated upload creates another batch under ordinary creation semantics. The uploaded file has request lifetime, while tickets, audit and queued receipts have the same retention and access as JSON-created tickets. Confirm ordinary outbox state and restart behavior locally.

## Non-functional requirements

### R-3 Upload bounds and diagnostics

Basis: the existing `MAX_BODY_BYTES` setting and the selected 100-row operational cap for one bulk request.

- An upload may contain 1–100 data records and must fit within `MAX_BODY_BYTES` (default 65536). Reject excess with HTTP 400 and no state change. Verify 100, 101 and an oversized body with a configured bound.
- Return actionable errors through the established JSON envelope without echoing field values. Use existing request, audit and worker observability. Confirm malformed input and save errors. The service exposes an API, so visual and browser requirements do not apply. No new latency SLA or dependency is required.

## Retired

None.
