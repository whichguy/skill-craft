## Failing now

none

## Discoveries

- A shot request body can be padded to 8,192 bytes. The server refuses the same request at 8,193 bytes without applying the shot. | Observable: Pad valid shot JSON with whitespace and compare the two responses, then fire legally at the same square. | Why: The plan mentioned a body limit, but the specification gives no size or boundary.
- A shot sent in a request that disconnects before its declared body ends does not advance play, even when the bytes already received form valid JSON. | Observable: Send valid shot JSON with a larger Content-Length, close the connection, then compare the round with a control. | Why: A server that acts on the first parseable JSON value could apply a shot before the HTTP request is complete.
- The HTTP interface exposes no independent evidence of which occupied squares belong to the same ship. | Observable: Every occupied square reported as sunk is consistent with a fleet of one-square ships. | Why: A temporary test build that mislabeled every non-final hit as sunk passed C-17 because the open fleet composition also permits the same public responses.
