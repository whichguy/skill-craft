# Coordinator-only synthetic defect matrix (current reference: `fixture-r2`)

This document is not copied into worker-visible roots.  It records the defect
families that the independent grader may materialize after a TEST worker has
finished.  The public fixture contract is [SPEC.md](SPEC.md).

| Family | Incorrect behavior in a generated hidden source copy |
| --- | --- |
| `wrong_actor` | Accept a body actor that does not match the authenticated token actor. |
| `duplicate` | Apply a second mutation effect for a repeated successful idempotency key. |
| `stale` | Apply a move when its expected version is old. |
| `cache` | Leave a pre-move state cache valid after a successful write. |
| `invalid_move` | Accept syntactically valid but illegal move geometry. |

`INNER` receives a source copy with only the retry/idempotency and stale-write
faults baked into it.  `OUTER` receives a served revision/configuration mismatch
and stale cache behavior.  `OUTER_HOLDOUT` receives a distinct scope/configuration
mismatch.  `TEST` receives only the correct source; the grader uses
`materialize_mutant` outside the worker root to make each family testable.

Generated worker app sources must not contain a defect selector, names of this
matrix, or a correct alternate implementation branch for the selected case.
`create_case` refuses a nonempty destination so an r2 worker root cannot inherit
old run artifacts. `CaseLayout.start` clears any ambient authoritative-receipt
environment variable; a coordinator must pass an external receipt path directly
when it intends the child service to retain one. The grader's in-process HTTP
harness and worker-test subprocesses follow the same rule: they clear an
inherited path unless that individual grader run explicitly sets one.

## Receipt boundary

`runtime-observations/` in a generated worker workspace is an inspection-only
copy. Its permission bits do not make it authoritative against another process
with the same local identity. The coordinator may set an absolute external
receipt path before it starts the fixture service. The service records only an
allowlisted HTTP outcome there: server-generated `receipt_id`, fixed
method/route, requested-body actor class, status, explicit documented error or
`null`, and persisted versions before and after the response. The receipt ID is
only a service-local counter: it does not correlate a response to a specific
worker or prove client receipt. The bracketing versions are not an atomic or
causal-isolation claim for concurrent requests. The runtime must also reject a
target inside the entire gateway workspace; the Store can only make the narrower
state-workspace check. Service metadata exposes fixed receipt availability/error
states so preflight can fail if retention is not available. No test or reviewer
should infer an unrecorded failure category, request body, header, credential,
arbitrary actor, or idempotency key from that receipt.

Historical study copies remain frozen at their own recorded bytes and revision.
This r2 matrix applies only to newly generated follow-up workspaces.
