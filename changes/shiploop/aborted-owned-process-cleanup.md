---
bump: patch
---
When command capture aborts on POSIX, ShipLoop stops the private process group
if it still owns the leader and preserves the original error. Captured output
may be lost. Escaped processes and groups whose leader has already been reaped
are outside this cleanup. SIGKILL can leave workload locks and does not undo
previous writes.
