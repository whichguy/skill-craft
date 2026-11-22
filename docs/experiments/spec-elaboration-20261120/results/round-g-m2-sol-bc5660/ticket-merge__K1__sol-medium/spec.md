# Help desk tickets specification

## Requirements

### R-1 Agent-directed duplicate merge

Basis: “Let agents merge duplicate tickets.” (2026-11-21). Preserve the existing HTTP conventions and ticket lifecycle in docs/api.md.

- M1. With two open tickets T-0001 and T-0002 in a fresh service, POST /tickets/T-0001/merge with JSON {"into":"T-0002"} and X-Actor: dana returns 200 with T-0001 in terminal status merged and mergedInto T-0002. GET for each ID confirms that the source retains its existing content and the target record is unchanged.
- M2. GET /tickets/T-0001/audit contains one ticket.merged event with actor dana and changes for status and mergedInto (null to T-0002). Its earlier history stays intact. Target history and the requester outbox stay unchanged. Compare HTTP snapshots.
- M3. Repeating the same merge returns the same source with its prior timestamp and creates no audit entry, including after the canonical record later closes. Concurrent incompatible requests have one winner and leave one audit event. Check over HTTP against a shared process.
- M4. Missing, malformed or additional inputs and self-merge are 400 invalid. Unknown well-formed source or target is 404 not_found. Closed source, final target, a different target for an already merged source, or merging a source already referenced by other duplicates are 409 conflict. A valid source or target may be open, in progress or resolved. Verify errors plus absence of side effects.
- M5. Merged tickets cannot be edited, transitioned or created through the ordinary lifecycle. GET list with status merged shows them, and status open excludes them. Verify HTTP filtering and lifecycle rejections.

### R-2 Durable and readable duplicate record

Derived from R-1 and README.md, docs/operations.md and docs/decisions/0008-json-data-file.md.

- M6. A version-1 file with old nonmerged records still loads. A merged record needs an existing nonmerged canonical ID and only merged records may have that field. Malformed, dangling, self-referential and chained records are rejected on startup. A persisted merge survives restart with its link and audit history. Simulate a save failure to verify the store exposes neither a failed merge nor its proposed audit entry and permits a successful retry.
- M7. The read-only CLI show output shows mergedInto. List raw retains the four established columns and the weekly report counts merged separately. Confirm with actual command output using state saved by the HTTP service.
- TicketStore owns the link as long as the source ticket is retained. It is visible via existing internal reads. All writes are serialized in the server and persist synchronously when DATA_FILE is set. The canonical's title, requester, priority and history are never copied to the source or sent as merge-related mail.

## Non-functional requirements

Reuse the internal HTTP and read-only CLI boundaries. Preserve the API body limits and error envelope. A merge runs within the existing synchronous store and whole-file persistence model, with no additional latency bound in the request. Use a side-effect-free retry and failed-write test to confirm consistency. CLI show retains aligned terminal details and existing error output. No new screen, session, identity, network, worker or graphical interaction is required.

## Retired

None.
