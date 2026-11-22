# Help desk ticket service: living spec

## Requirements

### R-1 Agents merge a duplicate ticket into another
Basis: request "Let agents merge duplicate tickets." (2026-11-21). Preserved: all existing endpoints, CLI, weekly-report columns. Changed: new operation. Evidence limit: "duplicate" is not detected automatically; an agent names both tickets. Pending: implementation and checks.
An agent merges ticket A (the duplicate) into ticket B (the target) with `POST /tickets/:id/merge`, body `{"into": "T-xxxx"}`, actor from `X-Actor`.
- Positive: merging an active duplicate returns 200 with the duplicate ticket, now `closed` with `mergedInto` = target id; the target is unchanged. Observed at the HTTP API; confirmed by api test.
- Failure: unknown source or target id is 404 `not_found`; a body that is not `{into: <ticket id>}` (missing, extra field, malformed id) is 400 `invalid`. Confirmed by api test.
- Boundary: merging a ticket into itself is 409 `conflict`. Confirmed by store and api test.

### R-2 Which tickets may be merged
Basis: R-1; default Q2. Pending implementation.
- Positive: a source in open, in_progress or resolved status and a target in any non-closed, non-merged status is allowed.
- Failure: a closed source or closed target is 409 `conflict`; a target that is itself merged is 409 `conflict`; a source already merged is 409 `conflict`; the failed merge changes nothing (no audit entry, no notification). Confirmed by store test.
- Boundary: resolved source is allowed; resolved target is allowed. n/a otherwise.

### R-3 A merge is audited and persisted
Basis: R-1; CONTRIBUTING.md "Changes go through the store"; decision 7. Pending implementation.
- Positive: one store call appends an audit entry `ticket.merged` on the source (changes: status and mergedInto) and on the target a `ticket.merge_received` entry naming the source; `GET /tickets/:id/audit` shows them; the data file saves once. Confirmed by store and persistence tests.
- Failure: n/a: a failed merge is covered by R-2.
- Boundary: a data file written before this feature loads unchanged (no `mergedInto`); a merged ticket survives a restart. Confirmed by persistence test.

### R-4 The duplicate's requester is notified
Basis: R-1; default Q4; CONTRIBUTING.md notification rules. Pending implementation.
- Positive: a `ticket.merged` outbox event for the source's requester, naming the target, with a template in `src/templates.js`; handlers never call the notifier. Confirmed by store and outbox test.
- Failure: no event when the merge is refused.
- Boundary: n/a: one event per merge, key `ticket.merged:<source id>`.

### R-5 The merge is visible in tickets and docs
Basis: R-1. Pending implementation.
- Positive: ticket JSON carries `mergedInto` only for a merged ticket; `GET /tickets/:id` and the listing show it; the CLI `show` prints it; `list --raw` columns keep their positions. docs/api.md documents the endpoint and errors; CHANGELOG and version updated. Confirmed by api test, format test and review of docs.
- Failure: n/a.
- Boundary: unmerged tickets' JSON is byte-identical to before.

### Non-functional
Security: internal network, no new authentication; X-Actor only (default Q5). Performance, accessibility: excluded, no bound stated and a single in-memory update. No new dependencies.

## Retired
None.
