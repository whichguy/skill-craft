# Help desk ticket service specification

## Scope

The existing service accepts ticket changes through the internal HTTP API. The CLI reads the optional data file. Scope of these requirements is ticket creation and CSV import. The baseline is README and docs/api.md at 8d2525c, with local tests at that revision.

## Requirements

### R-1 Upload a CSV to create tickets

Basis: “Let agents upload a CSV to bulk-create tickets.” (2026-11-21, S1). Add a write operation at `POST /tickets/import`. An authorized network caller submits raw UTF-8 `text/csv` with a header of exactly `title` and `requester`, optionally `priority`, in any order. Match the existing HTTP trust boundary, including X-Actor audit attribution. The import creates new, open tickets and returns 201 with `{ "items": [...] }` in file order. Existing ticket and pagination shapes remain supported. The CLI remains a reader.

- CSV-01 (local HTTP, implementation and release): on a fresh service send `title,requester,priority\r\n"VPN, ""slow""",a@example.test,high\r\nPrinter,b@example.test,\r\n`. Confirm response items have IDs T-0001 and T-0002, titles `VPN, "slow"` and `Printer`, priorities `high` and `normal`, respective requesters, and open status. Confirm list and individual reads produce the same records.
- CSV-02 (local HTTP, implementation and release): accept LF, CRLF, optional final line break, a UTF-8 BOM, and optional priority column. Ignore physically empty lines. Validate every field through the existing create contract, including single-line title and requester.
- CSV-03 (local HTTP, implementation and release): wrong content type, invalid UTF-8, empty or header-only input, wrong header set or width, bad quoting and invalid fields return 400 invalid. Row-specific messages identify the 1-based CSV record, counting the header and physically empty lines. An error in a later record leaves all ticket effects absent.

### R-2 Import writes are atomic and use ordinary creation effects

Basis: S1 and preserved API Create a ticket, ADRs 0002, 0006, 0007 and 0008. In the same synchronous operation assign sequential IDs, append one `ticket.created` audit per ticket and enqueue one creation notification per requester. Store publishes the batch only after a successful save when a data file is configured. The worker independently delivers the queued notifications and owns retries.

- CSV-04 (local HTTP and restart, implementation and release): start with an existing ticket in a test data file. Import two rows with `X-Actor: dana`. Confirm sequential IDs after the existing ticket, audit action/actor and matching pending notifications in both the live service and reopened data file.
- CSV-05 (store and local HTTP, implementation and release): an invalid later row consumes no ID or event or audit sequence. A failed persistence save leaves the existing state and IDs unchanged. A retry after the failed save assigns the next available IDs.
- CSV-06 (full suite, implementation and release): existing JSON POST /tickets creates one ticket as before and the file schema remains compatible.

Source data is transient during request processing. Ordinary ticket records, their audit entries and outbox events share the existing access and lifetime rules. A single serving process owns the state; the synchronous mutation serializes concurrent accepted calls. A successful upload can be repeated to create new tickets just like a single create. There is no new cache, upload job, retained CSV, identity layer, data migration or notification channel.

### R-3 Bounded import

Basis: S1 and the existing request body limit documented in README, Configuration.

- CSV-07 (local HTTP, implementation and release): apply the existing `MAX_BODY_BYTES` limit and accept at most 100 ticket rows. Reject over-limit input with 400 invalid and zero mutation. At the row limit, a valid batch within the byte cap succeeds.

## Non-functional requirements

The resource limits are in R-3.

- The Node 22+ standard-library-only policy from CONTRIBUTING applies. Existing error envelopes and operator audit/outbox visibility apply. No separate latency SLA or graphical surface is specified. Raw uploads and rejected field values do not enter product logs via this feature.

## Retired

None.
