# Help desk tickets specification

## Scope

This repository serves the internal help desk HTTP API and read-only operator tools. The baseline is README, docs/api.md and the adopted decisions at 8d2525c. The added requirement follows the 2026-11-21 request to let agents upload a CSV to bulk-create tickets.

## Requirements

### R-1 Upload a CSV and create tickets

- **R-1.a Upload.** An agent sends a UTF-8 file as the body of POST /tickets/import with Content-Type text/csv. The first record contains exactly title, requester and optionally priority, in any order. Accept quoted cells, doubled quotes, LF or CRLF, an optional leading BOM and an optional final line ending. Apply normal single-ticket field rules and default a missing or blank priority to normal. Boundary: accept one data record and accept up to 1,000 subject to MAX_BODY_BYTES. Confirm through real loopback HTTP with a BOM, reordered header, and a quoted comma and quote.
- **R-1.b Success.** Return 201 JSON with an items array of normal ticket objects, in input order, initially open with sequential IDs. Each ticket is immediately visible via GET /tickets and has one ticket.created audit entry with the request actor and one pending notification. When persistence is configured, restart preserves tickets, events, and sequences. Confirm through the live service with the worker disabled and an isolated data file.
- **R-1.c Rejection.** Wrong media type, invalid UTF-8, missing/duplicate/unknown headers, missing data, malformed CSV, wrong column counts, invalid values, an oversized body or excess rows return the standard 400 invalid envelope. Include a one-based CSV record number when the fault is tied to a record, counting the header as record 1. No tickets, audit entries, notifications or counters change when the upload is rejected. A save failure returns the standard 500 internal envelope with no staged records published. Confirm through loopback failures, state readback and a controlled persistence failure before a successful retry.
- **R-1.d Compatibility.** Existing JSON POST /tickets, queries, operator tools, worker and version-1 file remain compatible. No new identity or UI is needed. Confirm with the full suite and upload plus subsequent JSON creation.

State is held by the existing store. A successful upload uses one synchronous commit, with other data changes ordered by the service event loop. The CSV body is transient. Existing ticket fields, audit attribution and pending notifications follow current state lifetimes and access. Audit labels follow X-Actor or system; the header supplies attribution only. Error messages carry record numbers and field names rather than submitted cell contents. A fresh successful upload is another set of new tickets; clients verify the result before retrying an ambiguous connection failure. No queued import, upload history, idempotency key or change to external delivery completion is in scope.

Verification walk from an empty service with worker disabled: send the header requester,title,priority followed by records ava@example.test,"Wi-Fi, floor 2",high and ben@example.test,"Printer says ""jam""",. POST permits both valid rows and returns T-0001 high and T-0002 normal in order. GET /tickets and GET /tickets/T-0002/audit can observe the stored tickets and attribution. GET /admin/outbox can observe two pending ticket.created events. Then upload the same header followed by cal@example.test,Monitor flickers,low and dee@example.test,Mouse freezes,immediate. It returns 400, mentions record 3 and leaves the two original tickets and two pending events. The next JSON POST /tickets with title Dock unplugged and requester eli@example.test receives T-0003. This is a logical walkthrough from the API contract. Execution is due during work-item and local release verification.

## Non-functional requirements

Bound the body by the existing configurable byte ceiling (default 65,536) and the batch by the 1,000-row product default. Check limit and limit-plus-one in the service tests. Use the current error envelope without exposing file contents. Existing network access and notification recovery apply. Graphical design and accessibility checks are outside the machine-only API surface. No latency objective was provided.

## Retired

None.
