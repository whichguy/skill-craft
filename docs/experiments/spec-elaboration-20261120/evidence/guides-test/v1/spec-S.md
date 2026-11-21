# Help desk ticket service specification

## Scope

The internal Node HTTP API serves help-desk agents. The operator CLI and weekly report read the existing data file.

## Requirements

### R-1 Upload and create tickets

Basis: “Let agents upload a CSV to bulk-create tickets.” (2026-11-21). Existing creation conventions are in [Tickets API](../api.md#create-a-ticket-post-tickets).

- Agents send a raw UTF-8 file as `text/csv` to `POST /tickets/import`. The required header has `title` and `requester` and optionally `priority`, in any order. Column names are exact, unique and case-sensitive. Blank or omitted priority uses `normal`. Observe the HTTP response for both header shapes.
- Accept a leading UTF-8 BOM, LF or CRLF, an optional final newline, quoted commas and doubled quotes. Quoted fields must fit on one line. Observe literal values and defaults in the response. With empty storage, uploading `requester,title,priority` followed by `a@example.test,"VPN, ""office""",` and `b@example.test,Printer,high` creates `T-0001` and `T-0002` in that order, with titles `VPN, "office"` and `Printer` and priorities `normal` and `high`.
- Return 201 with `{ "items": [...] }` containing the open ticket objects in CSV order. Each ticket gets one normal creation audit entry and one enqueue for its requester. Read back the tickets, audit actors and pending events through HTTP, then restart from a data file and confirm the records and next ticket ID.

### R-2 Reject invalid imports without partial creation

Basis: the 2026-11-21 bulk creation request and existing [error envelope](../api.md#errors). Atomic rejection and a synchronous result are product defaults.

- Return 400 `invalid` for a wrong media type, malformed UTF-8 or CSV, empty/header-only input, invalid header, wrong row width, invalid ticket fields, invalid actor or an exceeded limit. CSV syntax and field errors identify the first failing CSV row where applicable, with the header numbered 1. Use a valid first data row and an invalid priority on the second to confirm row 3 is reported and the next ordinary creation still gets `T-0001`.
- Check the whole upload before any write. A save failure returns the standard 500 envelope and leaves ticket IDs, tickets, audits and pending notifications as they were. Exercise the storage failure seam and check live reads and the next successful ID.
- The store owns the batch and existing persisted ticket, audit and outbox resources. HTTP success means the batch is saved when persistence is configured and notifications are queued. The existing worker owns delivery and retries. Upload bytes live only for request processing. Imported data follows normal ticket retention and visibility. Each successful submission, including a repeated file, creates a new batch.

### R-3 Preserve existing creation and readers

Basis: [Tickets API](../api.md), [README](../../README.md#command-line), and [Operations](../operations.md#the-data-file).

- Preserve the single-ticket JSON endpoint, existing request and actor rules, and ticket reads. The old suite and a single POST after an import verify compatibility.
- Preserve data-file version 1 and the CLI/report projection. Reopen a file containing normal tickets and imported tickets and verify normal reads and the continued sequence.

## Non-functional requirements

- Reuse `MAX_BODY_BYTES` (default 65536, configurable up to 1 MiB) for raw uploads. Cap the number of data rows at 1,000 to bound synchronous creation and outbox scans. Verify exact byte and row limits and the first rejected values.
- Reuse the internal service boundary and existing audit identity. The error envelope may name a row and field. Request logging follows existing route/status logging and does not include upload contents.
- Preserve the standard-library-only Node 22+ runtime. The existing test suite verifies the local service. This API introduces no visual interface.

## Key questions

- K1 Agents upload to the HTTP service and read created tickets in the response. R-1
- K2 The additive route preserves JSON creation and operator reads. R-3
- K3 Use raw UTF-8 CSV, the documented header, and the existing JSON error envelope. R-1 and R-2
- K4 Reject the entire batch on invalid input and report the first bad row. R-2
- K5 The existing store is the shared state owner and the configured data file survives restart. R-2 and R-3
- K6 Node 22+ and standard library only. Non-functional requirements
- K7 The route, ticket validation and store preserve separate responsibilities. R-1 and R-2
- K8 Node test runner and real HTTP, restart and failure-boundary checks. R-1 through R-3
- K9 Deliver verified source to the original checkout. Scope
- K10 Reuse the existing byte limit and cap row work. Non-functional requirements
- K11 Verify late-row and storage failures consume no IDs or side effects. R-2
- K12 Agents are internal help desk operators; CSV is a comma-delimited file. Scope and R-1
