# 4. Errors in one envelope

Date: 2025-01-27
Status: Accepted

## Context

The first handlers answered errors in whatever shape was at hand: a string, `{ "error": "..." }`, `{ "message": "..." }`.
The agents' dashboard had a branch per shape, and two of them showed "undefined" to agents.

## Decision

We will answer every error in one envelope:

```json
{ "error": { "code": "<code>", "message": "<for people>" } }
```

with four codes, each with its status: `invalid` 400 (the request is malformed), `not_found` 404 (no such ticket or
route), `conflict` 409 (well formed, but the ticket's state does not allow it), `internal` 500 (a fault of ours; the
message says nothing more).

Code that rejects a request throws `InvalidError`, `NotFoundError` or `ConflictError` from `src/errors.js`; one place in
`src/app.js` turns any thrown error into the envelope. Nothing writes an error response by hand.

## Consequences

- Clients branch on `code`, never on the message, which we are free to reword.
- "Not allowed in this state" (closing a ticket that is still open, changing a closed one) is always 409, never 400:
  the client did nothing wrong in the request itself, the ticket has to change first.
- An unexpected exception becomes `internal` without leaking a stack trace; it is logged.
