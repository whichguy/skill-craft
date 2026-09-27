---
bump: patch
---

Keepalive binds a session to a run from a packet marker only when the command
that printed it drives the run (`workspace start`, `init`, `next`, `resume`,
`complete`, Improve bind/complete/reconcile). A session that merely reads a
packet file, log or transcript containing a live marker is no longer bound and
kept alive for a run it does not drive. The `--run-dir` fallback also reads only the command that ran, never its
output, so callback text printed in a log or event dump no longer binds.
