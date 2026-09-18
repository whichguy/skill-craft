# Controlled status contract — A

This is a fixture input, not evidence of a deployed service. W1 may call only
`GET /api/exports?accountId=<selectedAccountId>` while the page is visible and
after foreground recovery. The host independently authorizes that account ID;
the request selector does not confer authority. A `403` means the client must
retain no old account's response as current. A successful response repeats the
authorized `accountId`, a monotonically increasing integer `revision`, and an
array of jobs `{ id, label, status }`, where `status` is exactly `queued`,
`running`, `complete`, or `failed`.

The client accepts a response only when its request generation and echoed
account ID still match the current account, and its revision is at least the
currently held revision for that account generation. An equal revision is an
unchanged heartbeat; it must not replay a success cue. An account replacement
clears the held activity snapshot before the first matching response arrives.
Network failure or malformed data keeps the last valid same-account snapshot
visibly marked stale and offers a read-only refresh; it does not report a domain
retry or completion. The response has no timestamps, percent complete,
download path, operation reconciliation, notification permission, or storage
contract.

There is no POST, draft API, collection selector, additional endpoint,
subscription, socket, worker, server process, or deployment access in this
control. W2 persistent drafts remain a distinct blocked item.
