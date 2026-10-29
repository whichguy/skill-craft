---
bump: patch
---
A session end the host reports is now recorded in the run's `trace.jsonl`, so a run shows that the host's session-end hook
freed it.
- The hook writes a `hook` row (`hook=session-end`, `decision=release`, `released`, and the host's `reason`).
  `released` is true when that session's claim on the run was removed, and false when the stop hook had already released
  it (a normal exit) or another session owns the run. `shiploop trace` prints it like any hook row.
- `release_owner` returns whether it removed a claim.
