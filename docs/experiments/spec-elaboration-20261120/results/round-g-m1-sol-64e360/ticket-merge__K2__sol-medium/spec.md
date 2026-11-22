# Help desk tickets specification

## Scope

The help desk HTTP API is the service write surface. See [the API contract](../api.md), [operations](../operations.md), and [contributor conventions](../../CONTRIBUTING.md).

## Requirements

### R-1 Agent-directed duplicate merge

Basis: “Let agents merge duplicate tickets.”, 2026-11-21. The endpoint and domain details are implementation defaults for that request. Preserve the existing actor convention, request envelope, and response formats for unaffected tickets.

- R-1.a. POST /tickets/T-0002/merge with JSON `{"targetId":"T-0001"}` and X-Actor dana returns 200 with T-0002, now closed, with mergedInto T-0001. Start with two open tickets created through POST /tickets. GET /tickets/T-0002 and the closed listing show the same duplicate. The primary stays byte-for-byte equivalent as a ticket object. Source title, requester, priority and created time stay the same. HTTP case C-1.
- R-1.b. A source can be open, in progress or resolved. A target can be open, in progress or resolved. Reject self-merge, an ordinary closed endpoint, retargeting, targeting a merged ticket, or merging a primary that already has incoming duplicates with 409 and zero state change. A primary with incoming links can still follow its usual lifecycle. Existing update/transition guards make a closed duplicate terminal. HTTP case C-2.
- R-1.c. The route requires exactly one field, targetId, and canonical source and target IDs. Missing, malformed, or extra input returns 400. Well-formed missing endpoints return 404. HTTP case C-2.
- R-1.d. An identical retry returns the already merged ticket, including its original updated time, even if the primary now closed. It adds no audit, notification or write. If two targets compete for one source, one succeeds and the other conflicts. HTTP case C-3.

### R-2 Durable and auditable merge

Basis: 2026-11-21 duplicate-merge request and accepted audit and data-file decisions [7](../decisions/0007-append-only-audit-log.md) and [8](../decisions/0008-json-data-file.md).

- R-2.a. Each actual merge adds one ticket.merged event to the source history, with actor and time and from/to for status and mergedInto. Older history stays readable. Merge leaves the outbox as it was. Nothing from the target requester is copied to the duplicate or sent as a new message. HTTP cases C-1/C-3.
- R-2.b. The store owns state and commits the duplicate and its audit together when DATA_FILE is configured. Successful merge survives restart. A write failure leaves both unchanged in the running service and the last saved snapshot, and a retry can succeed exactly once. Restart and injected-write cases C-4/C-5.
- R-2.c. Old v1 files with no link still load. Links persist as an optional field and must name another existing record without forming a chain. Existing list, cursor, raw CLI and report contracts still work. Persistence and CLI case C-4.

## Non-functional requirements

The operation uses the standard-library Node 22+ runtime and single process owner. During a merge the service makes one whole-file commit through the existing rename boundary, with no new worker, global service or backing store. The primary and original data remain readable via existing internal API access. Test cases C-1 through C-5 and the full local suite verify behavior. The repository supplies no numerical latency target. There is no new rendered interface or external target in this request.

## Behavior model

F-1 (R-1, R-2) is one synchronous HTTP operation. The agent identifies the duplicate in the URL and the primary in JSON. Validation precedes store lookup. The store verifies the link rule, commits T-1 and returns the duplicate. A subsequent GET and audit read are independent observations. F-2 repeats the request or restarts the service and reads the same result.

| Transition | Before and trigger | Result and recovery | Cases |
|---|---|---|---|
| T-1 | Both tickets exist and are nonclosed, source differs from target and has no incoming links. Agent requests merge. | Source becomes a closed duplicate linked to primary, one audit event. Primary still follows the normal lifecycle. Save error preserves pre-merge state. | C-1, C-4, C-5 |
| T-2 | Malformed input, missing record, or ineligible existing records. | Error envelope, with no ticket, audit or outbox changes. | C-2 |
| T-3 | Same source and primary link already exists. | Return existing duplicate unchanged. A competing primary conflicts. | C-3 |

The store owns tickets, links, audit and outbox. Links and audit share the ticket's retention and restart lifetime. In-memory mode ends at process shutdown. Existing internal reads expose the duplicate link; the request adds no new role or private field. Deletion, automatic duplicate detection, and cross-host coordination are outside this HTTP operation.

## Verification

C-1 through C-3 use the actual ephemeral HTTP service. C-4 uses an old-format file, real restart and CLI subprocess. C-5 uses the store's persistence seam to force a write error. Planned until exercised in the implementation stages.

## Retired

No requirements retired.
