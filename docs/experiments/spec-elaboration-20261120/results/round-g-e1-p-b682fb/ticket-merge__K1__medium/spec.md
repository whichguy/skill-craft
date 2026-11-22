# Help desk ticket service: living spec

Basis for R-1..R-7: the request "Let agents merge duplicate tickets." (2026-11-21), the existing API in `docs/api.md`,
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
- Replay: with T-0001 and T-0002 both `open`, `POST /tickets/T-0002/merge` with header `X-Actor: dana` and body
  `{"into":"T-0001"}` answers 200 with `{"id":"T-0002","status":"closed","mergedInto":"T-0001", ...}` whose `updated` is the
  merge time; `GET /tickets/T-0001` is byte-for-byte what it was before; `GET /tickets/T-0002/audit` ends with a `ticket.merged`
  entry by actor `dana` and `GET /tickets/T-0001/audit` with a `ticket.merge_received` entry by `dana`.
- Boundary: ids use the existing `T-NNNN` form; no ticket is created or removed, ids are never reused. `mergedInto` is
  present only on a merged ticket (absent, not null, on every other ticket, so existing ticket bodies are unchanged).
  `:id` that is not a ticket id is 404, as for `GET /tickets/:id`.
- Preserved: all existing endpoints, ticket fields and lifecycle; `GET /tickets/:id` of a merged ticket still answers.
- Pending: implementation and tests.

### R-2 Refused merges
- Failure (409 `conflict`, message names the reason): merging a ticket into itself; a duplicate that is already closed
  (including already merged); a surviving ticket that is closed. A refused merge changes nothing: no audit entry, no
  notification, no save. Confirmed by store and API tests.
- Order of checks (first failure wins): request body 400; unknown `:id` 404; unknown `into` 404; self-merge 409; closed
  duplicate 409; closed target 409. A malformed body is 400 even when the ticket is also closed.
- Boundary: chains are allowed and not flattened. A is merged into B; B (still open) may later be merged into C. Then
  A.`mergedInto` stays B and B.`mergedInto` is C; `mergedInto` always records the direct target. Cycles cannot occur
  because a merged ticket is closed and a closed ticket is refused as a target. Replay: with T-0001..T-0004 all `open`, after T-0002
  into T-0001, merging T-0003 into T-0002 is 409 (T-0002 is closed); merging T-0001 into T-0004 is 200, and then T-0002
  still has `mergedInto` T-0001.
- Open gap (default recorded): whether merging a closed duplicate should be allowed is a user decision; default refuses.

### R-3 The merge is audited
- Positive: one audit entry on the duplicate, action `ticket.merged`, the request's actor, changes
  `{ status: {from, to: "closed"}, mergedInto: {from: null, to: "<into>"} }`; the surviving ticket gets one entry, action
  `ticket.merge_received`, changes `{ mergedFrom: {from: null, to: "<duplicate id>"} }` (`from` is always null: each entry records one received
  duplicate, so a second merge into the same survivor adds a second entry; the survivor's own fields and `updated` stay as
  they were, and `mergedFrom` is not a ticket field). Visible in `GET /tickets/:id/audit` of each. Confirmed by store/API tests.
- Boundary: entries are appended in the same store call as the change (one save); the log stays append-only.
- Open gap: the surviving-ticket entry's shape is a spec default; the alternative is no entry on the survivor.

### R-4 The duplicate's requester is told
- Positive: one `ticket.merged` outbox notification to the duplicate's requester, key `ticket.merged:<id>`, rendered by
  a new template in `src/templates.js` that names both ticket ids; the event's `data` carries `{ title, into }` (the
  duplicate's title and the surviving id), which the outbox persists as it does any `data` object. Delivered by the worker, never by the handler.
- Boundary: the surviving ticket's requester is not notified; a refused or repeated merge enqueues nothing.

### R-5 The merge survives a restart
- Positive: with `DATA_FILE`, a merged ticket reloads with `status`, `mergedInto`, and the audit entries intact.
- Boundary: `version` stays 1; a data file written before this change loads unchanged (no `mergedInto` means not merged);
  a record whose `mergedInto` is present but is not a ticket id, is its own id, names no ticket in the file, or sits on a
  ticket that is not `closed` is refused as a corrupt data file (the invariant in the state-and-data section).
- Confirmed by a persistence round-trip test.

### R-6 Who may merge
- Boundary: no authentication or role check is added; the audit records the actor from `X-Actor`, as for every change.
- Open gap: restricting merge to help desk agents needs an auth model the service lacks; owner: the user.

### R-7 Documentation and release bookkeeping
- `docs/api.md` documents the endpoint, field `mergedInto` and the audit actions; a decision record (docs/decisions/0009)
  records the closed-plus-link representation; `CHANGELOG.md` gains a 1.5.0 section and `package.json` version 1.5.0.
- The operators' CLI stays read-only: `show` prints a merged ticket normally, with one extra detail line after `updated`, only when `mergedInto` is present: label `merged into`, value
  `T-0001`, laid out like the other detail lines (two-space indent, label padded to the longest label printed, two spaces);
  an unmerged ticket's `show` output is unchanged byte for byte (its history lines already render the new audit entries);
  `list` and `list --raw` columns are unchanged (the weekly report reads them by position).

Observed consequence (not a change): the weekly report and `GET /tickets?status=closed` count a merged ticket as closed.

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
