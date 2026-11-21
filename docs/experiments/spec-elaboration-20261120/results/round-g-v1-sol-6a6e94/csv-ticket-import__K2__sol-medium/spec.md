# Help desk tickets specification

## Scope

Internal HTTP ticket service. The API and accepted decision records retain the standing contracts for ordinary ticket operations, reads, audit, notifications and DATA_FILE. The prior behavior is retrievable at 0a92b60 (README, docs/api.md and docs/decisions). CSV import extends the HTTP surface. Basis for added requirements is “Let agents upload a CSV to bulk-create tickets” (2026-11-21), with transport and failure choices taken as documented working assumptions.

## Requirements

### R-1 Bulk creation via CSV

Add an agent-facing POST /tickets/import endpoint accepting a raw UTF-8 text/csv request. Preserve POST /tickets JSON and the existing internal access model (docs/api.md, Conventions and Create a ticket).

- Send `title,requester,priority\n"VPN, floor 4",a@example.test,urgent\nPrinter,b@example.test,\n` with X-Actor set to dana. On a fresh instance, the upload returns 201 with items T-0001 and T-0002 in that order, open, with priorities urgent and normal respectively. Read them through the normal ticket API. Confirm via real HTTP before return.
- Require title and requester headers and allow priority in any header order. A missing or blank priority uses normal. Accept UTF-8 BOM, CRLF or LF, quoted values, doubled quotes and an optional terminal newline. Confirm the actual text and fields on returned tickets with reordered headers and quoted Unicode input. Blank data records are invalid. Parse quoted record boundaries before applying normal single-line field rules.
- Keep existing individual create, listing, cursor and CLI contracts. Confirm in the existing full suite. The feature has no rendered interface or new role assignment.

### R-2 Actionable rejection and upload limits

Add validation for the new upload while preserving the error envelope and MAX_BODY_BYTES in docs/api.md Errors and README Configuration.

- For malformed quoting, wrong field count, invalid ticket value, empty or header-only input, duplicate/unknown/missing column, unsupported content type or invalid UTF-8, return 400 with the existing invalid envelope. Identify the first offending CSV record by starting line for errors localized to one record, including header mistakes on line 1. Confirm with HTTP tests and check response messages for record errors.
- Count the entire raw request against MAX_BODY_BYTES. Accept a valid body exactly at the limit and return 400 for an oversized body. Confirm with real HTTP and a small configured limit.
- Invalid input leaves tickets, next ticket number, audit and outbox as they were. Send one valid row followed by an invalid row, check the empty normal listing and outbox, then create one JSON ticket and verify its first ID and audit sequence. Run at the HTTP boundary.

### R-3 Ordinary side effects and durable batch visibility

Preserve documented semantics in docs/api.md A ticket's history and The outbox, and decisions 2, 6, 7 and 8. Every success inserts its tickets, creation audit entries and pending requester notifications as one store operation, using current ID and actor rules and version 1 persistence.

- Confirm one ticket.created entry per ticket with the upload actor and one pending creation event per requester. Restart on the saved file and confirm tickets, audit, events and next ID via HTTP. Worker delivery remains asynchronous and separate from the 201.
- A data-file save error returns the standard internal error and leaves live and saved state untouched. Retry after repair and verify IDs, one audit and event per ticket. Parallel uploads or single creates must have unique IDs and no interleaving inside a batch. Verify at the store and HTTP boundaries.
- Raw CSV belongs to the HTTP request for its lifetime; the persisted records follow the usual ownership and visibility. A new successful submission creates new tickets. New replay token, raw upload retention and access controls are outside this request.

## Non-functional requirements

Reuse the configured byte bound and existing field limits to constrain resource use. A persistent upload writes one complete snapshot, checked with an instrumented store save and local restart. Preserve the standard-library-only Node >=22 requirement and existing error/logging conventions. Verify with the full test suite. Use local synthetic data. No separate performance SLA, graphical accessibility work or production verification target is specified.

## Retired

None.
