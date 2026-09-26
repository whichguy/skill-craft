---
bump: patch
---
The keepalive binds a session from a `shiploop` command only when that command
drives the run (`init`, `next`, `resume`, `complete`, `improve-*`). A read-only
query such as `hook-status`, `status` or `report` from another session no longer
claims the run and keeps that other session looping on it.
