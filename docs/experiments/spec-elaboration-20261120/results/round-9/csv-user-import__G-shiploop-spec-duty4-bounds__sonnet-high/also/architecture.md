# Architecture — User administration

Structure and technology decisions only. Product behaviour lives in `spec.md`. All decisions below are **proposed**
by the spec stage with no repository or runtime evidence; the plan stage confirms or replaces them against the real
stack (see the revalidation condition on each).

## Decisions

### AD-1 Process the import synchronously inside one request/response

- Supports: R-5, R-6, R-7, R-8, R-11 (spec assumption A-3).
- Decision: parse, validate and write within the upload request; the outcome is in the response. No job queue,
  background worker, status endpoint or notification.
- Alternatives: background job with polling (more moving parts, needs durable job state and its recovery).
- Revalidate: if G-1 shows the runtime's request time limit cannot cover `MAX_ROWS` rows being created, choose an
  asynchronous design and write new R-<n> for job status and completion.

### AD-2 Validate fully in memory, then one atomic write; the store's uniqueness is the final arbiter

- Supports: R-4, R-5, R-8.
- Decision: phase 1 parses and validates every row and checks existing emails (no writes). Phase 2 creates all users
  in a single transaction relying on a unique constraint on the case-insensitive email; a constraint violation rolls
  back everything and becomes the `CONFLICT` outcome. If the store has no multi-row atomic write (G-6), compensate by
  deleting the users created by the failed attempt, recorded by their ids.
- Alternatives: per-row writes with partial success (rejected by A-1).
- Revalidate: when G-6 is answered.

### AD-3 Enforce the byte bound while streaming

- Supports: R-7.
- Decision: count bytes as the body is read and abort at `MAX_BYTES`; do not rely on a declared `Content-Length` alone.
  Parse from the bounded in-memory buffer; never write the upload under a client-supplied name.
- Revalidate: when G-1 sets `MAX_BYTES` and the runtime body limit is known.

### AD-4 No retained copy of the upload or result

- Supports: R-10 (assumption A-6).
- Decision: the file is request-scoped; the result is returned and not stored; the audit record holds ids and counts only.
- Revalidate: if import history is later required.
