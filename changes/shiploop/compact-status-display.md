---
bump: minor
---
The status hook now shows a two-line summary (where the run is; what finished and what comes next) instead of the full 11-line block, and the model no longer reprints the status block: it tells the user at most one line per step and shows the whole block only when asked. `shiploop status` and `status.md` still carry the full block.
