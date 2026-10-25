---
bump: patch
---
- **A base run's not-run refusal gives the exit code:** when a focused command ran none of its test IDs on the item's
  base, the refusal now starts with how it exited, for example `exited 3 and printed nothing: it did not run …`, before
  the existing advice and the output's last lines. It states only what the record holds; it does not guess whether the
  command failed to start or asserted before its first print.
