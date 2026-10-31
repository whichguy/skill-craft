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
being offered for submission. When no valid operation can be derived (including
stopped Improve, unreadable or mismatched receipts and invalid reports),
completion is empty: the generic fallback names `next` and preserves existing
no-progress exits, unfinished state and artifacts. Lost context can also use
`next`; pauses, blocks, ownership, host limits and hook errors retain their
existing handling.
