# Help desk ticket service specification

## Scope

The established API, operations and operator projections are documented in [Tickets API](../api.md), [Operations](../operations.md) and [README](../../README.md). Those contracts apply alongside the requirements below.

## Requirements

### R-1 Merge one duplicate into a chosen canonical ticket

Basis: “Let agents merge duplicate tickets.” (2026-11-21). Existing API actor and route conventions are in [Tickets API](../api.md). Selection is explicit and manual.

- MRG-1. On a fresh service, POST /tickets with `{"title":"VPN down","requester":"alex@example.test"}` and then `{"title":"VPN still down","requester":"sam@example.test","priority":"high"}`. Expect T-0001 and T-0002 respectively. An agent submits `POST /tickets/T-0002/merge` with JSON `{"to":"T-0001"}` and receives 200 and the updated duplicate. Its status is `closed`, `mergedInto` is T-0001 and its updated time advances when the clock advances. GET and the closed-ticket listing still expose T-0002 with the link, and GET of the canonical ticket returns its exact pre-merge record. Retain titles, requesters, priorities, IDs and creation times. Verify with the real local HTTP server.
- Both roles may start open, in progress or resolved. A merge closes the source through the merge action. Its normal PATCH and transition paths follow the existing closed rules, and the canonical ticket continues its normal lifecycle. MRG-1 and MRG-2 check HTTP behavior. Bulk operations, automatic matching, undo and content transfer are outside this operation.

### R-2 Validate merge requests and ensure one direct relationship

Basis: the ID and error conventions in [Tickets API](../api.md) and the terminal lifecycle in [decision 0002](../decisions/0002-prefixed-sequential-ids.md) and Tickets API.

- MRG-2. Reject an invalid JSON shape, missing or unknown field, noncanonical path or destination ID, or self-merge as 400 `invalid`. A well-formed request with a missing source or destination returns 404 `not_found`. A closed source without the same link, a closed destination, an already-merged destination, a source already merged elsewhere, or a source serving as canonical to any duplicate returns 409 `conflict`. Verify the existing envelope and unchanged ticket records, audit, and outbox after refusal.
- MRG-3. A repeat for the same pair returns 200 with an identical source record, including after normal closure of the canonical ticket. It adds no audit entry or notification and needs no save. Overlapping attempts of the same pair both return 200 and create one audit event. Overlapping attempts of one source into two targets yield one 200 and one 409. Opposite-direction attempts cannot create a cycle. If one request uses a ticket as a target while another attempts to merge that target away, one succeeds and the other conflicts so that the resulting relationship is direct. Verify via concurrent local HTTP calls and read-back.

### R-3 Preserve provenance and persist the merge

Basis: [append-only audit](../decisions/0007-append-only-audit-log.md), [outbox](../decisions/0006-notification-outbox.md) and [data file](../decisions/0008-json-data-file.md).

- MRG-1. The source audit gains one ordered `ticket.merged` entry with the request's `X-Actor` (or `system` by the existing rule), exact status before and after, link from null to destination, and the timestamp matching the source update. Both prior audit histories and the existing outbox are preserved. The operation adds no requester notification. Verify through audit and outbox reads.
- MRG-4. The one service process owns the relationship and audit. If configured, one file replacement makes both durable. Verify by starting with a version 1 file without merge fields, applying the operation, restarting the service and reading the committed link and audit over HTTP. Without a file they live for the process lifetime. The existing internal readership and retention apply.
- MRG-5. If saving fails before replacement, the in-process ticket and audit remain at the prior state and a retry after recovery can perform the operation. Verify using an injected save failure. On load, reject malformed, self-referential, missing-target, chained or non-closed-source merge records. A closed canonical remains a valid historical destination. Verify with persistence fixtures.

### R-4 Preserve operator and reporting interfaces

Basis: [README Command line](../../README.md#command-line) and [Operations](../operations.md#the-command-line-and-the-weekly-report).

- MRG-4. Read the saved ticket with `node bin/tickets.js --data FILE show T-0002`. For a merged source, display `mergedInto` with the existing label alignment and show its merge in History. Later readers reach the canonical ticket by its ID. Continue supporting old files and keep `list --raw` at four tab-separated columns in existing order. The weekly report still counts the original tickets, including the duplicate as closed. Verify using the real CLI and report commands on the same saved file.

## Non-functional requirements

Verify one coherent write or no state change on an injected save failure, consistent read-back across requests and restarts, and no extra writes on retries. Use existing API body limits, internal access scope, actor attribution, cursor semantics and read-only CLI layout. Verify CLI alignment and raw output exactly, with no changes to the established terminal conventions. This HTTP action has no graphical UI, client session, new permission layer, remote cache or asynchronous completion. Apply no additional performance threshold because none is specified for the existing help desk workload. Local test results cover the Node service and CLI. They provide no production access or throughput measurement.

## Retired

None.

