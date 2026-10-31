---
bump: patch
---
Require verbose learning commits after every completed E2E run or bounded
experiment, including failed, interrupted, rejected and undecided attempts.
Restore the accepted baseline and retain an empty learning commit when no
change qualifies, preserving original commits and raw failure evidence.
Record reproducible scenarios, measurements, unknowns and full influential
hashes with their specific contribution. Search recent and older Git history
and read relevant full messages before planning the next trial or change.
