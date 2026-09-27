---
bump: minor
---
A verified BLOCKED result now routes the run to replanning. Settle it with
`verification.disposition: "replan"` (only with `passed: false`). The run then
starts no new work:

- `claim`, a fresh `start` and a retry of that attempt fail with `EREPLAN`;
- `next` returns `replan` and `release` actions plus a `replan` summary (steps,
  accepted, unfinished);
- work already in flight can still settle.

Rejected steps get a `retry` action with an attempt count, the reason and an
exact `call`. There is no retry limit.

A lock left by a process that no longer exists on this host is recovered
automatically; any other holder is refused with a message that names what to
do. A lost state file or settled receipt fails with `ESTATELOST` and names the
recovery.
