# Help desk tickets specification

## Scope

The internal ticket HTTP service is the consumer boundary. The operator CLI and weekly report read the same persisted tickets through their existing interfaces. The dashboard and production rollout are maintained outside this checkout.

## Requirements

### R-1 Agent CSV upload

Basis: “Let agents upload a CSV to bulk-create tickets.” (2026-11-21). Preserve the single-ticket JSON endpoint and its response, documented under Create a ticket in docs/api.md. Add the following service contract.

- R-1.a: An agent on the existing internal API posts a raw UTF-8 file to `POST /tickets/import` with `Content-Type: text/csv`. An optional UTF-8 BOM is accepted. A header with `title`, `requester`, and optional `priority` accepts columns in any order. Accept LF and CRLF, quoted commas, doubled quotes and an optional final newline. Return 201 with `{"items":[...]}`, one ordinary open ticket per data row in input order. Empty or omitted priority is normal. Verify via real local HTTP and ticket read-back.
- R-1.b: Reject an empty file, header-only file, missing, duplicate or unknown headers, wrong field counts, malformed quotes, invalid ticket values, invalid actor, other media types, invalid UTF-8 or over-limit input with 400 and the existing `invalid` envelope. Identify the first erroneous CSV record by one-based index (header is 1) where applicable. Do not echo CSV cell contents in errors. Verify at HTTP with malformed and invalid later rows and unchanged state.
- R-1.c: Preserve the JSON create, ticket reads, CLI/report format and existing operations; verify with the full suite.

### R-2 Ticket creation effects and failure recovery

Basis: ADRs 2, 4, 6, 7 and 8 plus bulk creation requested on 2026-11-21. Each imported ticket receives the next sequential ID, one `ticket.created` audit entry with the shared request actor, and one standard creation outbox event. The worker retains asynchronous delivery and retry ownership. A complete batch is committed as one mutation; bad input or a failed save leaves tickets, counters, audit and outbox as they were. Concurrent requests are serialized at mutation time by the synchronous store. Successful uploads are independent writes. Clients can correct and retry rejected input. A lost success response requires checking for already-created tickets before retry, since the same file can intentionally create another batch.

- R-2.a: From an empty service with the worker off, post `title,requester,priority\n"VPN, intermittent",first@example.test,high\nMonitor,second@example.test,` (where each \n represents a newline) with `X-Actor: dana`. Expect T-0001 high, T-0002 normal, two actor-attributed audits and two pending creation events. Restart on the same data file and confirm the tickets and effects survive. Requires a local test process and disposable file.
- R-2.b: From an empty service, submit a valid first data row and an invalid second data row. Expect 400 for record 3, an empty listing and outbox, then T-0001 for the next accepted creation. Simulate a failed save separately and check that the whole pre-existing snapshot survives and a subsequent retry uses the next unused ID. Verify through local HTTP and the store's persistence seam.

## Non-functional requirements

- Reuse the existing configured MAX_BODY_BYTES budget (65536 default). An input at the configured boundary is eligible and one beyond it gets the standard 400. Verify at HTTP with a small configured limit.
- Operate within the existing internal network trust boundary and attribute with X-Actor (system default). Retain only ordinary ticket/audit/outbox records. Do not retain the uploaded file or add a new logging sink. The operator surfaces and v1 file retain their formats, verified locally by regression tests and restart.
- Graphical design and hosted availability targets are outside the repository capability being changed.

## Retired

None.
