# Controlled status contract — B

This fixture input, rather than a deployed service claim, authorizes only
`GET /api/exports?accountId=<selectedAccountId>` while visible and after a
foreground recovery. The host independently authorizes the account selector. A
success response repeats the authorized `accountId`, a monotonic integer
`revision`, and jobs `{ id, label, status }`, with `status` exactly `queued`,
`running`, `complete`, or `failed`. A `403`, identity mismatch, malformed
response, replaced account generation, or older revision cannot replace the
current display.

An equal revision is an unchanged heartbeat and cannot replay a completion cue.
Changing accounts clears the prior snapshot before a first matching response.
Network failure keeps a visibly stale, same-account snapshot with a read-only
refresh option. There are no timestamps, progress percentages, per-job event
history, operation reconciliation, download path, notification permission, or
delivery receipt in the contract.

No POST, other endpoint, subscription, WebSocket, storage, server process,
worker, framework/package availability, or remote deployment is supplied.
Persistent drafts are a separate blocked W2 item.
