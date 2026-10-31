---
bump: patch
---
Missing or rejected required acknowledgement of a valid current completion
operation keeps the action unfinished, including at an unchanged-progress host
stop. The hook and driver repeat a short
instruction derived from that action's receipt: continue partial work, preserve
recorded passes, and submit the actual required report or stage callback. They
never execute completion or restart commands. Recorded Improve reports and
completed Improve receipts pass the existing read-only bridge validators before
being offered for submission. A local, read-only saved-pass hint guard also
withholds completion for `unresolved` with a `satisfied` exit, which the runtime
already refuses; producer and bridge report acceptance rules stay unchanged.
`unresolved` with an `unsatisfied` or `unknown` exit retains its exact saved report
and `done` command without rerecording. When no valid
operation can be derived (including
stopped Improve, unreadable or mismatched receipts and invalid reports),
completion is empty: the generic fallback names `next` and preserves existing
no-progress exits, unfinished state and artifacts. This also covers a previously
saved `unresolved`/`satisfied` report; it is never offered as ready to resubmit.
Two host timeouts without progress retain the driver's stuck exit even with a
valid pending completion and no deadline. Clean zero-exit premature stops can
continue the same pending action. A fresh driver session first reads `next`
once to recover the current action, artifacts and conditions, then continues
only its remaining work and exact callback without restarting, reissuing or
replaying it. Bound Cursor/OpenCode resumes keep the direct continuation, as do
same-session Stop reasons, which offer `next` for lost context. Pauses, blocks,
ownership, host limits and hook errors retain their existing handling.
