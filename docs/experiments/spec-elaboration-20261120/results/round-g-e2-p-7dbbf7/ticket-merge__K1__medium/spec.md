# Help desk ticket service: living spec

## Requirements

### R-1 Agents merge a duplicate ticket into another
Basis: request "Let agents merge duplicate tickets." (2026-11-21). Preserved: all existing endpoints, CLI, weekly-report columns. Changed: new operation. Evidence limit: "duplicate" is not detected automatically; an agent names both tickets. Pending: implementation and checks.
An agent merges ticket A (the duplicate) into ticket B (the target) with `POST /tickets/:id/merge`, body `{"into": "T-xxxx"}`, actor from `X-Actor`.
- Positive: merging an active duplicate returns 200 with the duplicate ticket, now `closed` with `mergedInto` = target id (reached by the merge, not by the lifecycle table in `src/tickets/states.js`, which is unchanged); the target ticket's fields and `updated` are unchanged. Example: with T-0001 and T-0002 open, `POST /tickets/T-0002/merge {"into":"T-0001"}` answers 200 with T-0002 `closed`, `mergedInto: "T-0001"`; `GET /tickets/T-0001` is byte-identical to before. Observed at the HTTP API; confirmed by api test.
- Failure: checks run in this order, the first failing one answers: (1) a body that is not exactly `{into: <ticket id>}` (missing, extra field, malformed id such as `T-7`) is 400 `invalid`; (2) unknown source is 404 `not_found`; (3) unknown target is 404 `not_found`; (4) the conflicts of R-2 are 409. Confirmed by api test, one case per step, including merging an unknown source into itself (404, not 409).
- Boundary: merging a ticket into itself is 409 `conflict`. Confirmed by store and api test.

### R-2 Which tickets may be merged
Basis: R-1; default Q2. Pending implementation.
- Positive: a source in open, in_progress or resolved status and a target in any non-closed, non-merged status is allowed.
- Failure: a source equal to its target (R-1 boundary), a closed source or a closed target is 409 `conflict` (a merged ticket is closed, so a source already merged, or a target that is itself merged, is covered; the message says it was merged); the failed merge changes nothing (no audit entry, no notification). Confirmed by store test.
- Boundary: resolved source and resolved target are allowed. A merged ticket then refuses `PATCH` and `transition` with 409 (closed is final). Confirmed by store test.

### R-3 A merge is audited and persisted
Basis: R-1; CONTRIBUTING.md "Changes go through the store"; decision 7. Pending implementation.
- Positive: one store call appends an audit entry `ticket.merged` on the source (changes: status and mergedInto) and on the target a `ticket.merge_received` entry with `changes: {mergedFrom: {from: null, to: <source id>}}` (an audit-only record: the target's ticket fields and `updated` do not change; the shape is a design decision for the architecture, AD-<n>); `GET /tickets/:id/audit` shows them; the data file saves once. Confirmed by store and persistence tests.
- Failure: n/a: a failed merge is covered by R-2.
- Boundary: a data file written before this feature loads unchanged (no `mergedInto`, still version 1); a merged ticket, with `mergedInto`, survives a save and reload (`src/persistence.js` `ticketRecord`/`readTicket` name every field the file keeps and must learn `mergedInto`, validated as a ticket id when present). Per CONTRIBUTING.md the data-file change gets a decision record in docs/decisions/. Confirmed by persistence test (round trip; old-file load).

### R-4 The duplicate's requester is notified
Basis: R-1; default Q4; CONTRIBUTING.md notification rules. Pending implementation.
- Positive: a `ticket.merged` outbox event for the source's requester, naming the target, with a template in `src/templates.js`; handlers never call the notifier. Confirmed by store and outbox test.
- Failure: no event when the merge is refused.
- Boundary: n/a: one event per merge, key `ticket.merged:<source id>`.

### R-5 The merge is visible in tickets and docs
Basis: R-1. Pending implementation.
- Positive: ticket JSON carries `mergedInto` only for a merged ticket; `GET /tickets/:id` and the listing show it; the CLI `show` prints it; `list --raw` columns keep their positions (a merged ticket lists as `closed`, so the weekly report counts it under closed; accepted, not separately reported). docs/api.md documents the endpoint and errors; CHANGELOG and version updated. Confirmed by api test, format test and review of docs.
- Failure: n/a.
- Boundary: unmerged tickets' JSON is byte-identical to before.

### Non-functional
Security: internal network, no new authentication; X-Actor only (default Q5). Performance, accessibility: excluded, no bound stated and a single in-memory update. No new dependencies.

## Retired
None.
