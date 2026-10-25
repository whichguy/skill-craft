---
bump: patch
---
The test-stage judge no longer calls a command "passed" when it exits 0 but its
own output reports a failed test (a wrapper or build step swallowing the
runner's real nonzero exit). The refusal for that case now names the runner's
tally instead of the bare, misleading `exit 0`.
