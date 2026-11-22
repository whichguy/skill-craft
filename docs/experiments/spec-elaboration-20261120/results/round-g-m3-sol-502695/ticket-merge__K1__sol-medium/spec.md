# Help desk tickets

## Requirements

### R-1 Merge a duplicate into an existing ticket

Basis: “Let agents merge duplicate tickets” (2026-11-21). Preserve the HTTP conventions in docs/api.md and lifecycle in src/tickets/states.js. Terminal merged status and audit-only notification policy are implementation assumptions. The helpdesk agent chooses the duplicate and target.

- M1. Create two tickets on a fresh service. An internal caller sends `POST /tickets/T-0001/merge` with `{"into":"T-0002"}` and `X-Actor: dana`. The 200 response and subsequent GET show T-0001 as `merged` with `mergedInto: "T-0002"`. Its original id, title, priority, requester and created time are retained, its updated time records the change, and T-0002 is identical before and afterward. Verify with real HTTP.
- M2. Only the case-sensitive `into` field and canonical ticket IDs are accepted. Leading zero aliases, missing, blank, wrong-typed and oversized inputs follow the existing 400 envelope. An unknown valid source or target returns 404. Existing body and actor limits apply, with `system` attribution when the header is absent. Verify with real HTTP.
- M3. Self-merge, closed source, merged destination, reassignment and an attempt to merge a source with an existing incoming link conflict (409). Exact retries return 200 and the existing source without changing updated, history or outbox. Merged tickets cannot transition or be patched. Ordinary transition requests cannot set `merged`. Verify through real HTTP and compare the state after rejection. A target may retain any ordinary status, including closed, to let agents link a report to the record that already covers it.
- M4. The duplicate remains retrievable either by ID or in listings, with `status=merged` filtering it. The CLI retains its four raw column positions, and counts include the merged status. Verify via real HTTP, a persisted file and the CLI/report entry points. Creation, update and transition of ordinary tickets and existing status-filter semantics are preserved.

### R-2 Keep merges traceable and durable

Basis: the 2026-11-21 merge request, ADRs 6–8 and docs/api.md. The internal service owns the link and audit. Both records remain subject to existing access and retention policies.

- M5. Each successful new merge appends exactly one source `ticket.merged` audit record with actor, timestamp and changes to status and mergedInto. The target audit and notification outbox are unchanged. Verify via the existing HTTP read endpoints. Creation and resolution notifications remain under worker ownership.
- M6. After restart with DATA_FILE, the source link, terminal state, unchanged target and audit remain visible. Previous version-1 files load unchanged. A file with a merged record and a missing, invalid, self-referential or merged target, or link on an ordinary ticket, is refused. Verify using service and persistence tests.
- M7. A failed save exposes a 500 on the HTTP boundary and leaves the source, target, history and outbox at their prior state. A subsequent successful retry records exactly one merge. Concurrent requests are ordered by the synchronous store and cannot establish contradictory links. Verify with a failed write simulation and opposing HTTP requests.

## Non-functional requirements

Node 22+ and no external dependencies, matching package.json and CONTRIBUTING.md. Preserve the current internal access model and body limit. The merge introduces no new personal fields, logs or outbound delivery. The existing single-writer JSON snapshot defines capacity and persistence limits. This API change adds no graphical interaction or service dependency. The read-only CLI uses its existing output conventions. The release test is `npm test` in a clean local copy and the original workspace receives only the reviewed change.

## Retired

None.

## Questions settled

- Q1. A 200 response returns the merged source and target link. The error envelope reports validation, missing tickets and conflicts. A failed save leaves no partial merge (R-1, R-2).
- Q2. Existing internal API callers may record a merge and attribute it with X-Actor under the current access model (R-1).
- Q3. A merge adds one audit event, uses the existing snapshot and body limits, and leaves the outbox alone (R-1, R-2).
- Q4. Reject malformed, oversized and inconsistent requests using the existing errors (R-1).
- Q5. Parse canonical case-sensitive ticket IDs, preserve ISO timestamps and validate the existing actor field (R-1, R-2).
