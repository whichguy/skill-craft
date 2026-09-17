# Synthetic Checkers capability fixture (current reference: `fixture-r2`)

This is a deliberately small, loopback-only client/server fixture for the
ShipLoop capability-selection experiment.  It is **not** a complete Checkers
application and it is not evidence about Google Apps Script, Salesforce, or a
hosted service.  It was adapted from the prior synthetic local HTTP control in
`/tmp/shiploop-discovery-v4.*`; this fixture has no dependency on that temporary
directory at runtime.

## Scope

The authoritative server persists one eight-by-eight board, the side whose turn
it is, a monotonically increasing `version`, an optional forced multi-jump
origin, a move history, and an idempotency ledger.  The browser is only an HTTP
client.  Application RPC is HTTP (`GET /api/state`, `GET /api/meta`, and
`POST /api/move`), never MCP.  A separate `runtime-observations/` directory is
an inspection root intended for an already-installed filesystem MCP; the
fixture does not create, install, or invoke an MCP server.

The implemented rules are intentionally limited to one piece moving at a time:

* Coordinates are lower-case `a1` through `h8`.  Only squares whose **zero-based**
  file index plus rank is odd are playable.  `a1` is playable; `b3` is not.
* Red men move toward increasing ranks and promote on rank 8.  Black men move
  toward decreasing ranks and promote on rank 1.  Kings move in either diagonal
  direction.
* A quiet move advances one legal diagonal square into an empty square.  A
  capture jumps two legal diagonal squares over one opposing piece into an empty
  square.  If any piece belonging to the current actor can capture, a quiet
  move is rejected.  When a capture leaves the same piece another capture, that
  actor keeps the turn and the next move must start at its landing square.
* The fixture does not implement draws, clocks, captures chosen by a remote
  opponent, board setup editing, forced move notation, repetition, game-over,
  spectator authorization, matchmaking, or a complete visual board.  A test
  must not infer those requirements.

## HTTP contract

The API responses are JSON; `GET /` serves the fixture's HTML page.
`GET /api/state` is a read-only state read and may be served from the server
cache.  `GET /api/meta` exposes the served revision, effective service
configuration, and a synthetic description of the RPC and observation boundary.
It does not expose mutation tokens.

`POST /api/move` accepts this body:

```json
{
  "actor": "red",
  "from": "b2",
  "to": "c3",
  "expectedVersion": 1,
  "idempotencyKey": "unique-client-request-id"
}
```

It requires `Authorization: Bearer <synthetic actor token>`.  The token maps to
one actor and one scope.  A correct server requires the body actor to match the
authenticated actor, the authenticated scope to include the configured write
scope, and the body actor to own the current turn.

The request body must be a JSON object. `actor` must be the string `red` or
`black`; JSON arrays, objects, booleans, numbers, `null`, and other strings are
invalid actors. A non-object JSON body is `400 invalid_json`; an invalid actor
is `400 invalid_actor`. These results leave persistence unchanged.

Validation order is part of the fixture contract:

1. The HTTP body must parse as a JSON object. A non-object or malformed body is
   `400 invalid_json`.
2. Before authorization, the service normalizes the named values in this order:
   `actor` must be `red` or `black`; `expectedVersion` must be an integer other
   than a boolean; `idempotencyKey` must be a nonempty string; then `from` and
   `to` must each have coordinate syntax and be playable. Missing or malformed
   values fail at their first applicable normalization check.
3. Only after that normalization does the service validate the authorization
   token and required scope. Therefore a JSON object with an invalid coordinate
   and no `Authorization` header returns `400 invalid_coordinate`, rather than
   a token error.
4. A previously successful key with exactly the same normalized request returns
   the original successful state with `idempotentReplay: true` and does not
   modify persistence or version.  The same key with different fields returns
   `409 idempotency_conflict`.
5. `expectedVersion` must equal the current version or the server returns
   `409 version_mismatch` without changing persistence.
6. Actor, turn, occupancy, geometry, mandatory capture, and forced
   multi-jump rules must all pass before the state changes.

Successful first writes return 200 with `idempotentReplay: false`; a successful
replay returns 200 with `idempotentReplay: true`.  Malformed input returns 400,
authentication or scope failures return 403, legal/ownership failures return
422, and stale/idempotency conflicts return 409. Error names explicitly shown
in this contract are stable for those cases. An observation must not invent an
error category for an unspecified process or transport failure.

## Frozen examples

The default board begins with a red man at `b2`, a black man at `g7`, and no
available captures.  Its version is 1 and red moves first.

| Request | Expected result |
| --- | --- |
| Red token, `red`, `b2` to `c3`, expected version 1, new key | 200; red occupies `c3`, turn becomes black, version becomes 2. |
| The exact same request and key again | 200; `idempotentReplay: true`, version remains 2. |
| Black token, `black`, `g7` to `f6`, expected version 2, new key | 200; turn becomes red and version becomes 3. |
| Red token with body actor `black` when black has the turn | 403 `actor_mismatch`; a token cannot impersonate the other actor. |
| A valid actor request with expected version 1 after the first write | 409 `version_mismatch`; the board must not change. |
| Red `b2` to `b3`, or `z9` to `a1` | 422 for illegal geometry or 400 for malformed coordinate; neither may change the board. |
| Red body with `z9` to `a1`, version 1, and no `Authorization` header | 400 `invalid_coordinate`; normalization precedes authorization and persistence does not change. |

Additional generated scenario boards make captures and multi-jumps observable.
Their state files state their exact initial pieces and trace; tests must read
those public files rather than infer a full game.

## Persistence, caching, and observations

The server writes the entire state atomically to `state.json` in its generated
workspace.  A new `Store` over the same workspace observes a completed move.
`GET /api/state` caches a copied state for the configured TTL.  A correct
successful move invalidates that cache before it returns; therefore a following
state read sees the new version.

The server appends redacted event records to
`runtime-observations/events.jsonl`. Request-derived event fields are limited to
inspection-only normalized values: an applied-move record may contain `actor`
only as `red` or `black`, plus `fromSquare` and `toSquare` only after they have
passed coordinate syntax and playability checks. Other request-derived values
are fixed error/status vocabulary or persisted version observations. Raw request
bodies, headers, tokens, idempotency keys, arbitrary actor values, rejected
coordinates, and extra body fields are never written there. The generated
directory is only an inspection surface: permission bits do not protect it from
another process with the same local identity, so it cannot establish integrity,
completion, or an HTTP status claim. The setup manifest identifies it as the
only root for the existing filesystem-MCP reader.

When the coordinator supplies an absolute external receipt path through its
runtime configuration, the service also writes one allowlisted receipt per
explicit HTTP response outside the worker workspace. Each record has only
`event`, server-generated `receipt_id`, `method`, fixed `route`, safe
`actor_class` (`red`, `black`, or `invalid`) for the requested body role,
`status`, explicit `error` or `null`, and `version_before`/`version_after`.
`receipt_id` is only a service-local counter; it does not correlate a response
to a particular worker or prove that a client received it. The version values
are persisted observations sampled before and after the response path; they do
not establish causal isolation, atomic response ordering, or a transaction if
requests overlap. The service never copies request bodies, headers, credentials,
arbitrary actor strings, or idempotency keys into this record. The
coordinator-owned copy is evidence only when it is actually retained; a missing
receipt does not establish a hidden outcome. Its availability and a fixed
configuration/write error are exposed in service metadata so a coordinator can
fail preflight rather than treat a dropped receipt as success.

## Worker-visible bounds

Each generated case provides this contract, its ordinary source and thin tests,
connection information, a modest skill/capability catalog, and the read-only
observation root.  It may include an interaction trace or served configuration
that makes a real verification boundary visible.  It does not expose evaluator
implementations, other arms, private test harnesses, or post-run implementation
variants.  A worker may use native reads and ordinary Python/HTTP tools; using a
filesystem MCP is optional and receives no special credit.

The generated fixture uses only loopback HTTP and temporary files.  It does not
run an agent, call an external network endpoint, install packages, use real
credentials, or deploy software.
