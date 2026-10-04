---
bump: patch
---
The chain guide's `finish` row and worked example no longer say finish needs every worker's worktree removed. Since 0.49.0 a retried or lost attempt's workspace is kept and listed under `retained_superseded`; the old wording could lead a model to remove it directly or to stop.
