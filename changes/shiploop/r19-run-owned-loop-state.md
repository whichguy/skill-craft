---
bump: patch
---
Keep ordinary inner-stage Until Loop backing state in the run's existing loops
directory alongside its contract and runtime-owned receipt. Emitted launches now
pass that directory to the runtime; formatting stays read-only, and receipt,
resume, terminal deletion and parent acceptance rules are unchanged.
