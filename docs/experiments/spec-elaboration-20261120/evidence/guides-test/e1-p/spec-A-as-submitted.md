# Help desk ticket service: living spec

Basis for R-1..R-6: the request "Let agents merge duplicate tickets." (2026-11-21), the existing API in `docs/api.md`,
conventions in `CONTRIBUTING.md`. "Agents" are help desk staff; the service has no auth, so any caller naming itself in
`X-Actor` (default `system`) may merge (see R-6). The merged-ticket representation (duplicate ends `closed` with a
`mergedInto` link) is the recorded default, not a user decision.

## Requirements

### R-1 Merge a duplicate ticket into another
Endpoint `POST /tickets/:id/merge`, body `{ "into": "T-0001" }` (`:id` is the duplicate, `into` the surviving ticket).
- Positive: both tickets exist and are mergeable: 200 with the duplicate ticket, now `status: "closed"` and
  `mergedInto: "<into>"`. The surviving ticket is unchanged (title, priority, status, `updated`). Confirmed by an API test.
- Failure: unknown `:id` or unknown `into` is 404 `not_found`; body not an object, missing or non-ticket-id `into`, or an
  unknown field is 400 `invalid`. Confirmed by API tests.
- Boundary: ids use the existing `T-NNNN` form; no ticket is created or removed, ids are never reused.
- Preserved: all existing endpoints, ticket fields and lifecycle; `GET /tickets/:id` of a merged ticket still answers.
- Pending: implementation and tests.

### R-2 Refused merges
- Failure (409 `conflict`, message names the reason): merging a ticket into itself; a duplicate that is already closed
  (including already merged); a surviving ticket that is closed. A refused merge changes nothing: no audit entry, no
  notification, no save. Confirmed by store and API tests.
- Boundary: no chains: because closed tickets are refused as a target, a ticket merged into a ticket cannot be merged
  into a closed one.
- Open gap (default recorded): whether merging a closed duplicate should be allowed is a user decision; default refuses.

### R-3 The merge is audited
- Positive: one audit entry on the duplicate, action `ticket.merged`, the request's actor, changes
  `{ status: {from, to: "closed"}, mergedInto: {from: null, to: "<into>"} }`; the surviving ticket gets one entry, action
  `ticket.merge_received`, changes `{ mergedFrom: {from: null, to: "<duplicate id>"} }` (it records the link only: the
  ticket's own fields stay as they were). Visible in `GET /tickets/:id/audit` of each. Confirmed by store/API tests.
- Boundary: entries are appended in the same store call as the change (one save); the log stays append-only.
- Open gap: the surviving-ticket entry's shape is a spec default; the alternative is no entry on the survivor.

### R-4 The duplicate's requester is told
- Positive: one `ticket.merged` outbox notification to the duplicate's requester, key `ticket.merged:<id>`, rendered by
  a new template in `src/templates.js` that names both ticket ids. Delivered by the worker, never by the handler.
- Boundary: the surviving ticket's requester is not notified; a refused or repeated merge enqueues nothing.

### R-5 The merge survives a restart
- Positive: with `DATA_FILE`, a merged ticket reloads with `status`, `mergedInto`, and the audit entries intact.
- Boundary: `version` stays 1; a data file written before this change loads unchanged (no `mergedInto` means not merged);
  a record whose `mergedInto` is present but not a ticket id, or names no ticket, is refused as a corrupt data file.
- Confirmed by a persistence round-trip test.

### R-6 Who may merge
- Boundary: no authentication or role check is added; the audit records the actor from `X-Actor`, as for every change.
- Open gap: restricting merge to help desk agents needs an auth model the service lacks; owner: the user.

### R-7 Documentation and release bookkeeping
- `docs/api.md` documents the endpoint, field `mergedInto` and the audit actions; a decision record (docs/decisions/0009)
  records the closed-plus-link representation; `CHANGELOG.md` gains a 1.5.0 section and `package.json` version 1.5.0.
- The operators' CLI stays read-only: `show` prints a merged ticket normally and shows `mergedInto` in its details;
  `list` and `list --raw` columns are unchanged (the weekly report reads them by position).

## Non-functional requirements

- Dependencies: none added (CONTRIBUTING). Style: `'use strict'`, named exports, errors via the envelope.
- Consistency: a merge is applied atomically in memory (both tickets and the audit entries change in one store call, then
  one save); no performance bound is stated and none is invented.
- Security, accessibility, interface polish: excluded; no UI, and no auth exists in the service (R-6).
- State and data: affected resources are the ticket record (new optional `mergedInto`, plus `mergedFrom` only in the audit),
  the audit log and the outbox. Invariant: a ticket with `mergedInto` is `closed` and the target exists. Recovery: the
  data file is saved after the change; a restart reloads it (R-5). Unknown: none.

## Retired

None.
