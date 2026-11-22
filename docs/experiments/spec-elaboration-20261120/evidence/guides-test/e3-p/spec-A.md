# Help desk ticket service: spec

Baseline: README.md, docs/api.md, docs/decisions/ at commit 6aa51a6 (existing system, 117 passing tests). Existing behaviour not listed below is preserved (R-6).

## Requirements

### R-1 Agents can merge a duplicate ticket into another
Basis: request "Let agents merge duplicate tickets." (2026-11-21). "Agents" = help-desk staff using the HTTP API, identified by `X-Actor` (assumption A1, research.md).
Behaviour: `POST /tickets/:id/merge` with JSON `{ "into": "<id>" }`, `:id` = the duplicate, `into` = the surviving ticket. Answers 200 with the duplicate ticket after the merge: status `closed`, new field `mergedInto` = the survivor's id, `updated` = merge time. The survivor is not changed.
Acceptance:
- Setup (replayable on a fresh in-memory service, worker off): `POST /tickets` `{"title":"VPN drops","requester":"maria@example.com"}` gives T-0001; the same with title `VPN dropping` gives T-0002; both are `open` (src/store.js `create`).
- Positive: from that setup, `POST /tickets/T-0002/merge` `{"into":"T-0001"}` answers 200 and `status:"closed"`, `mergedInto:"T-0001"`; `GET /tickets/T-0002` returns the same; `GET /tickets/T-0001` is unchanged (same `updated`). Same for a duplicate that is `in_progress` (after `POST /tickets/T-0002/transition` `{"to":"in_progress"}`) or `resolved` (then `{"to":"resolved"}`), each allowed by src/tickets/states.js. Confirmed by API test (test/api.test.js style).
- Boundary: a merge where the survivor is `resolved` or `in_progress` is allowed; the survivor's status is not changed.
- Failure: see R-2.

### R-2 Refused merges
Acceptance (each confirmed by an API test; errors use the envelope, CONTRIBUTING.md):
- Check order: body validation (400) first, then the duplicate's existence (404), then the survivor's (404), then state rules (409), so each case below has one answer.
- Body not an object, `into` missing, not a string, or not a valid ticket id format, or unknown extra field: 400 `invalid`.
- Unknown duplicate id or unknown `into` id: 404 `not_found`; nothing changes.
- `into` equal to the duplicate: 409 `conflict` ("cannot merge a ticket into itself").
- Duplicate already `closed` (including already merged), or survivor `closed` (including a merged ticket): 409 `conflict`; nothing changes (no audit, no notification).
- Merging twice is therefore a 409 on the second call.

### R-3 Merge is audited
Acceptance: after the merge in R-1, `GET /tickets/T-0002/audit` ends with one entry `action:"ticket.merged"`, `actor` = the `X-Actor` header (or `system`), `changes` = `{ "status": {from:"open",to:"closed"}, "mergedInto": {from:null,to:"T-0001"} }`; entries stay numbered with `seq` in sequence, earlier entries untouched. A refused merge (R-2) adds no entry. The survivor's audit gains no entry (default). docs/api.md lists `ticket.merged` among actions. Confirmed by API and store tests.

### R-4 The duplicate's requester is told
Acceptance: after a merge, `GET /admin/outbox` lists one `pending` event `type:"ticket.merged"`, `key:"ticket.merged:T-0002"`, `to` = the duplicate's requester, `ticket:"T-0002"`, `data.title` and `data.into:"T-0001"`; its rendered text (src/templates.js) names both ids. A refused merge enqueues nothing. Request handlers do not call the notifier. Confirmed by store/notifier tests.

### R-5 Merge survives restart and the data file stays safe
Acceptance: with `DATA_FILE`, after a merge a new store loaded from the file returns the duplicate with `status:"closed"` and `mergedInto`. A data file written before this change (no `mergedInto`) still loads (version stays 1). A saved ticket without a merge omits `mergedInto` (not `null`). On load, `mergedInto` that is not a ticket id of the file, equals the ticket's own id, or is present on a ticket not `closed` is refused with a DataFileError naming the ticket. Confirmed by test/persistence-style tests.

### R-6 Existing behaviour is preserved
Acceptance: `npm test` baseline suite (117 tests) still passes unchanged. Unmerged tickets omit the `mergedInto` key (in API JSON and in the data file). Ids, pagination cursors, `PATCH`/`transition` rules (closed ticket final), error envelope and `bin/tickets.js list --raw` columns (id, status, priority, title) keep their positions. `scripts/weekly-report.js` counts a merged duplicate as `closed` (assumption A4).

### R-7 Merge is documented and visible to operators
Acceptance: docs/api.md documents the endpoint, `mergedInto` field and `ticket.merged` action and notification; ADR docs/decisions/0009 records the merge rules (index updated); CHANGELOG.md section and `package.json` version bump to 1.5.0 (CONTRIBUTING.md Releases); `bin/tickets.js show T-0002` displays the merge target. Confirmed by file review and a CLI test.

## Non-functional requirements
- Operating conditions: Node >=22, standard library only (binding, CONTRIBUTING.md). Verified by package.json unchanged dependencies.
- Atomicity: a merge applies status, `mergedInto`, audit, outbox and save in one store step (`apply`); verified by R-3/R-4 tests.
- Performance, accessibility, UI polish: excluded; no UI, no bound stated by the request.
- Security: no authentication exists in the service (internal network, README); none added (A1).

## Open gaps / decisions
- A2 merge rules and A4 report counting are recorded defaults, owner: spec (this stage); no person-only gaps.
- Out of scope: unmerge, merging comments/history into the survivor, bulk or automatic duplicate detection, changing survivor fields.

## Retired
(none)
