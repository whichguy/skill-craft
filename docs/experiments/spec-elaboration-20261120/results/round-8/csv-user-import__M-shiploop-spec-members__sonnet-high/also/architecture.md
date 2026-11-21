# Architecture

## Decisions

Stack, framework and datastore are not yet known (no repository for this stage). Decisions below are stack-neutral and
proposed; the plan confirms them against the real stack. Requirement references point to KNOWLEDGE/spec.md.

### AD-1 Synchronous multipart endpoint for the import

- Decision: one HTTP `multipart/form-data` operation with a single `file` field, answering with the result report in
  the same response. The concrete path (for example `POST /api/admin/user-imports`) is a placeholder chosen by the plan
  to match the product's routing conventions.
- Serves: R-1 to R-7, R-9, R-10; spec assumption A-7.
- Alternatives: background job with status polling. Rejected for now: it adds job state, recovery and a polling UI
  that the request does not need. Revisit when OG-6 shows volumes that cannot finish within one request.
- Consequence: the response is the completion, so no async-recovery contract is needed (spec, Service-boundary contracts).

### AD-2 Parsing and validation are one server-side pure function

- Decision: `bytes in, (rows | error list) out`, with no I/O, called before any write. The browser performs only
  convenience pre-checks; the server is the sole authority.
- Serves: R-2, R-3, R-4 (in-file part), R-6, NFR-9. Lets the validation rules be tested without a datastore.

### AD-3 Atomic commit relying on datastore guarantees

- Decision: all inserts plus the audit record go in one transaction, and email uniqueness is also enforced by a
  datastore unique constraint on the normalised email, in addition to the pre-check.
- Serves: R-5, R-10.
- Unverified: that the chosen datastore supports multi-row transactions and the constraint. No source or probe exists
  yet, so this is a requirement on the stack choice, not a claim; the plan verifies it against primary documentation or
  a probe before relying on it. If the store lacks either, R-5 and R-10 need a different mechanism and this AD is revised.
