# Help desk ticket service specification

## Scope

The internal HTTP API owns ticket writes. Preserve the single-ticket API, lifecycle, audit semantics, notification delivery, version-1 data files and read-only CLI/report in [the API guide](../api.md) and [operations guide](../operations.md). The 8d2525c baseline suite covered those behaviors. The CSV workflow adds a synchronous HTTP operation.

## Requirements

### R-1 Create multiple tickets from a CSV upload

Basis is “Let agents upload a CSV to bulk-create tickets.” (2026-11-21). The upload uses the conventions of [the ticket API](../api.md#conventions) and [CSV syntax and media type](https://www.rfc-editor.org/rfc/rfc4180). Wire details are chosen defaults.

- R-1a. POST /tickets/import accepts a UTF-8 text/csv body with a required case-sensitive header naming title and requester and optionally priority, in any order. Quoted fields, embedded commas, doubled quotes, LF or CRLF separators, a leading BOM and an optional final newline are supported. The HTTP test submits raw file bytes and checks decoded values and original row order.
- R-1b. A valid upload with one or more data records returns 201 with an items array of the newly opened tickets in CSV order. IDs use the existing sequence, fields use the existing create rules, and absent or blank priority is normal. An HTTP test pre-creates a ticket, uploads two rows, and reads both back by ID.
- R-1c. Invalid encoding, wrong media type, malformed quoting, unknown or duplicate columns, incorrect record widths, empty or header-only files, invalid ticket fields and bodies over the configured limit return the existing 400 invalid envelope. Errors identify the first failing CSV record (header is 1) where available. HTTP tests include invalid data after a valid row and confirm no ticket, audit, notification or ID is consumed.

### R-2 Preserve creation audit, notifications and persistence

Basis is the requested bulk creation through the existing service and accepted [audit](../decisions/0007-append-only-audit-log.md), [outbox](../decisions/0006-notification-outbox.md) and [data file](../decisions/0008-json-data-file.md) decisions.

- R-2a. A successful upload records one ticket.created audit entry per ticket with the existing X-Actor convention and queues one normal notification per requester. The worker still owns delivery. Confirm audit actor, action and order via the audit route, and pending events via the existing outbox route with the worker disabled.
- R-2b. Tickets, IDs, audit records and notification events are one synchronous batch. With DATA_FILE set they survive restart together. A failed save returns 500 with previous state and counters intact. Test an existing data file, an induced save failure, a corrected retry, and restart. Mutations share the service process and resolve in commit order. No staging survives the request.
- R-2c. Upload bytes are held only for the request. Existing internal access applies, with no extra role system. X-Actor identifies the audit label, and successful repeated uploads create additional tickets. Request bodies and row data are excluded from error messages and logs, apart from normal persisted ticket/audit/outbox records. Confirm via HTTP fixtures and handler review.

## Non-functional requirements

Use the established MAX_BODY_BYTES ceiling and error format for interoperability and bounded request memory. Verify configured boundary cases with real HTTP requests. Atomic replacement and synchronous publication protect the existing store integrity contract. Standard library only and Node.js 22+ are binding repository conventions. No graphical surface, new persistence schema, operational SLA or deployed acceptance is in scope.

## Retired

None.
