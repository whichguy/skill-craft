# Help desk tickets specification

## Scope

The internal HTTP service described in docs/api.md at the 8d2525c baseline. The November 21, 2026 request adds the support agent's CSV upload. Existing ticket reads, JSON creation, transitions, audit, notifications, version 1 data files, CLI and weekly report retain their documented behavior.

## Requirements

### R-1 Upload a CSV and create tickets

Basis: November 21, 2026 request to let agents upload a CSV to bulk-create tickets, and docs/api.md's existing create and actor conventions. On the internal HTTP API, POST /tickets/import accepts one UTF-8 CSV as the raw body with media type text/csv (optional parameters). Require one header with title and requester and optional priority, in any order, using those exact names. Each data record maps to the ordinary ticket fields. An omitted or empty priority defaults to normal. Text and priority follow existing validation. Support comma separation, quoted fields, doubled quotes, LF or CRLF, a UTF-8 BOM, and an optional final record terminator. Every record has the header's number of fields.

On success return HTTP 201 with a JSON object containing items, in file order. Each item is a complete open ticket with its assigned sequential ID. GET /tickets, GET /tickets/:id and the audit read must observe the resulting tickets and the existing actor from X-Actor (or system). Each ticket queues one ticket.created event for its requester. The existing internal network boundary applies.

Check at the HTTP surface with a fresh service and UTF-8 CSV containing two records, including a comma and doubled quotes in a title, then read the records, audit and outbox. Use this payload with X-Actor: dana on an empty service:

```csv
title,requester,priority
"Printer, says ""offline""",ada@example.test,
VPN disconnects,lin@example.test,high
```

Expect T-0001 with title `Printer, says "offline"`, requester `ada@example.test` and priority normal, followed by T-0002 with title `VPN disconnects`, requester `lin@example.test` and priority high. Each audit entry records dana and each pending event targets its own requester. Repeat read-back after opening the same configured data file. Confirmation pending implementation.

### R-2 Reject an invalid file without effects

Basis: the same upload request and existing invalid envelope. Reject empty/header-only input, missing/duplicate/unknown headings, malformed CSV or UTF-8, wrong media type, wrong field count, invalid ticket fields, or body larger than MAX_BODY_BYTES with HTTP 400 and error.code invalid. Where applicable include the first offending record number (header is 1), without echoing uploaded values. CSV is request-scoped and the original file is not retained.

Check a valid first data record followed by a second with priority `emergency`. Expect `invalid` naming row 3. Verify the subsequent ticket, audit, outbox and persisted state still match the baseline. An ordinary valid create must still get the next available ID. Test at and above the byte cap, and malformed/header-only rows at the HTTP surface. Confirmation pending implementation.

### R-3 Commit batch effects together

Basis: docs/decisions/0006-notification-outbox.md, docs/decisions/0007-append-only-audit-log.md and docs/decisions/0008-json-data-file.md. All ticket, ID, audit and outbox changes for an import are committed together. Where DATA_FILE is set, save the unchanged version 1 shape once before the successful response. If a save fails, respond with the existing internal error envelope and retain the previous in-memory state and durable data. A corrected or recovered retry after rejection starts with the next unused ID. Repeating a successful create produces new tickets. No upload/session record is held after the response. The existing worker delivers queued notifications asynchronously.

Check an injected persistence failure, recover and retry, comparing snapshots and save calls. Confirm the real file-backed HTTP success survives restart. Confirmation pending implementation.

## Non-functional requirements

Existing MAX_BODY_BYTES applies (65536 by default); verify a precisely sized payload and one byte above. The service uses standard-library CommonJS on Node 22+. Access follows the existing internal HTTP service boundary. No graphical surface or additional throughput/latency SLA was requested.

## Behavior model

F-1 (R-1, R-3): An agent sends raw CSV. The server validates every row, then stages normal ticket changes. T-1 commits those changes and returns 201. The agent can read tickets and audit immediately. The worker subsequently owns notification delivery.

F-2 (R-2, R-3): T-2 rejects bad transport or records with 400 before committing. T-3 reports a save failure with 500 before publishing staged changes. No ID or notification is consumed by an unsuccessful upload. The caller can correct and retry. Client disconnect prior to a complete body exits before writes. A disconnect after processing may leave committed records, so retries of uncertain success are not deduplicated.

| Transition | Before and guard | Result | Verification |
| --- | --- | --- | --- |
| T-1 | Existing store, full valid CSV | IDs, open tickets, audit and outbox advance as one synchronous change | HTTP create/read and file reopen |
| T-2 | Existing store, invalid request | Original store retained and 400 returned | HTTP rejection and next ID |
| T-3 | Existing store, valid request with failed durable save | Original store retained and 500 returned | Failed save with recovery test |

The service owns shared ticket and outbox state. In memory mode it lasts until process exit. File mode retains it under the version 1 data file policy. Synchronous commits serialize concurrent request writes within the existing single-process writer model. Requester values are stored and exposed under the same policy as ordinary ticket creation. Batch progress tracking, cancellation after submission, migrations and expiry add no state.

## Retired

None.
