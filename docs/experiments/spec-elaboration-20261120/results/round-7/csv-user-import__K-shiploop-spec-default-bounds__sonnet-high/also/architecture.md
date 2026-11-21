# Architecture decisions: User administration

Structure and technology choices only. Product behaviour lives in `spec.md` as R-<n>. No repository was inspected
(see spec.md "Baseline and evidence limits"), so each decision is stated stack-neutrally and is **proposed** until the
plan checks it against the real stack; the plan may substitute an equivalent mechanism without changing the R-<n>
acceptance lines the decision serves.

## Decisions

### AD-1: Synchronous single-request import, no background job
- Status: accepted (default; revisit on a trigger below).
- Serves: R-8, R-9, R-10; assumption A-8.
- Decision: the import runs inside the one HTTP request that carries the file and answers with the final result
  (success or the complete error report). No queue, worker, operation record or polling endpoint.
- Why: the caps (1,000 rows, 1 MiB; assumption A-4) keep the work small; atomic all-or-nothing (R-8) is simplest to
  state and verify when the answer is the commit result; nothing is left running if the admin closes the page.
- Consequence: a lost response leaves an *unknown outcome* for the client; recovery is re-upload, made safe by R-7
  (already-created emails are rejected) and stated truthfully by the UI (R-10).
- Revalidate if: the row or size cap is raised, NFR-3's latency bound resolves below what 1,000 rows need on the
  target runtime, or the runtime's request time limit (gap G-3) is below that.

### AD-2: One datastore transaction per import; unique index on normalized email is the final arbiter
- Status: accepted (default); depends on gap G-2 (store capabilities unconfirmed).
- Serves: R-7, R-8, R-11.
- Decision: pre-validation (row rules, in-file duplicates, existing-email lookup) exists to build the full error
  report. Creation then runs as **one transaction** inserting every user and the audit event together, protected by a
  unique constraint on the case-normalized (trimmed, lower-cased) email. A uniqueness violation at commit rolls the
  whole transaction back and is reported as `already_exists` for the conflicting rows (R-7 race clause).
- Why: validation-then-insert alone races with a second admin or any other user-creation path; only a store-level
  constraint closes that. Putting the audit event in the same transaction gives "every created user has an audit
  event" without a distributed protocol.
- If the user store cannot offer multi-row transactions or a case-insensitive unique constraint, that is an open
  prerequisite (G-2), not a reason to weaken R-7/R-8.
- Revalidate if: the user store or audit store moves to a different system.

### AD-3: Endpoint contract
- Status: accepted (default); the path conforms to the product's existing API conventions if they differ.
- Serves: R-1, R-2, R-9.
- Decision: `POST /api/admin/users/import`, `multipart/form-data`, exactly one part named `file`. Responses are
  `application/json` with the statuses and bodies in spec.md R-9. The admin UI calls this same endpoint; there is no
  UI-only back door, so API clients and the UI share one contract and one set of checks.
- Authorization is evaluated per request against the caller's **current** role in the user store, not a role claim
  cached in a long-lived token (R-1 revocation clause).

### AD-4: Enforce the size cap while reading, not after buffering
- Status: accepted (default).
- Serves: R-2, NFR-1.
- Decision: reject on a declared length above 1,048,576 bytes, and also count bytes while reading so a body without
  or with a false length is cut off once it passes the cap. The handler never holds more than the cap plus one read
  chunk.
- Why: the cap is a protection against oversized bodies; checking after full buffering would not protect the process.

### AD-5: Use a maintained CSV parser, not hand-rolled splitting
- Status: accepted in principle; the library is chosen in the plan once the stack is known (gap G-2).
- Serves: R-3.
- Decision: parsing is done by a maintained RFC 4180-style parser configured strict (so unterminated quotes fail as
  `malformed_csv`), fed the decoded UTF-8 text. The parser must pass every R-3 fixture (quoted commas, doubled
  quotes, quoted newlines, CRLF, BOM-stripped input, blank-record numbering); a parser that cannot is rejected, not
  worked around by splitting on commas.
- Parsing and validation are a pure function of (bytes, set of existing emails) -> (users or errors) so they can be
  unit-checked without the UI or datastore.

### AD-6: Limits live in one place
- Status: accepted (default).
- Serves: R-2, R-4, R-5, R-10; NFR-9.
- Decision: the size cap, row cap, email and name length limits and the role set are defined once and consumed by the
  validator, the endpoint, and the UI's instruction text and client-side size pre-check, so the displayed limits cannot
  drift from the enforced ones. The server remains the authority; the client pre-check only saves a round trip.
