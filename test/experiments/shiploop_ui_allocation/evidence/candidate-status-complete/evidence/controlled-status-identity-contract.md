# Controlled read-only export-status and identity contract

This is an authoritative **controlled fixture input** for this diagnostic. It
defines a planned client/service contract, not an observed production host,
deployment, or authorization integration. It resolves the missing identity
bridge in `candidate-status-ready` without granting any mutation or deployment
authority.

## Account context and authorization

The existing native `#account` selector has option values that are stable opaque
account identifiers (`alpha` and `beta`). For an export-status read, the client
uses the selector's current value as the encoded `accountId` query value:

```
GET /api/exports?accountId=<encodeURIComponent(selectedAccountId)>
```

The selector is a request-context input only. It neither creates an
authorization session nor proves that the host switched accounts. At request
handling time, the same-origin host already has one authoritative
`authorizedAccountId`. It accepts the request only if the query `accountId`
equals that authoritative value; otherwise it returns `403` with
`{"code":"account_not_authorized"}`. The client never sends an authorization
credential, and it must not treat a selector value as an authorization claim.

For a controlled local test fixture, setup may arrange a matching or
non-matching `authorizedAccountId` before dispatching a request. That setup is
not evidence that the embedded host supplies a runtime account-selection bridge.

## Successful response and acceptance rule

A successful `200` response is complete for exactly the requested authorized
account:

```json
{
  "accountId": "alpha",
  "revision": 42,
  "jobs": [
    {"id": "exp-17", "status": "queued", "label": "September archive"}
  ]
}
```

`accountId` must exactly equal the request's captured selected account ID.
`revision` is a monotonically increasing integer **within that account only**.
Each job has a stable opaque `id`, a user-facing `label`, and `status` in
`queued`, `running`, `complete`, or `failed`. The response contains the complete
status snapshot for the supplied account.

The client accepts and renders a response only when all of these hold:

1. the request still belongs to the current selector generation;
2. the response `accountId` exactly matches that request's account ID; and
3. the response revision is newer than the held revision for that same account
   (an equal revision is a no-change heartbeat, and a lower revision is stale).

On account change, abort or make prior requests ineligible and clear the prior
account's export snapshot before a new account's response can render. A `403`,
identity mismatch, malformed response, or network failure must never expose the
previous account's jobs as the selected account's jobs. It may show a concise
retryable status message without leaking opaque IDs or server payloads.

## Lifecycle, user experience, and limits

Read only while the document is visible. On foreground, refetch the current
selector account's authoritative snapshot. Hidden pages do not poll; there is
no socket, background worker, persistent local cache, or durable draft storage.
Same-account status refreshes must not call existing list/detail/editor render
or focus/scroll paths, alter textarea value or selection, or discard a dirty
draft. An account replacement follows the existing privacy-preserving note-view
transition while export status waits for a matching new-account response.

Use a compact, persistent, accessible status surface and a separate polite
announcement only for meaningful changes. Motion must be restrained and work
with reduced-motion preferences; errors and recovery remain visible beyond any
transient cue. Existing Field Notes components, keyboard/touch behavior,
reading position, narrow layout, and navy/amber skin remain the premise.

This contract permits only the documented `GET /api/exports?accountId=...`
read. It deliberately supplies no POST, collection-selection, operation,
download, pagination, job-detail, subscription, or draft-storage route. A
focused local harness is allowed within W1. W2 persistent drafts remain blocked
because current controlled host facts report no client persistent storage and no
draft API.
