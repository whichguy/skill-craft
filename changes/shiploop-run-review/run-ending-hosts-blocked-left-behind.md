---
bump: patch
---
The Run Review export and page now say how a run ended. A run the harness ended while ShipLoop still read active is `stopped`,
with the stage it never accepted and the minutes and turns that cost, shown as a "How it ended" card and a hatched last column in
the picture; a blocked run shows its question and options; the listeners the harness ended and whether the unreturned product
passes its checks in the worktree are recorded. A run resumed on another host lists both hosts and exports no mixed calls, context
or compaction figure, and a visit with no model call no longer prints "0 calls". The default run name carries the case, and the
text about refusals, per-visit context and `Checked by:` lines now matches the runs.
