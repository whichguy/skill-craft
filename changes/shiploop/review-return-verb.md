---
bump: minor
---
New `shiploop workspace review-return --keep PATH... --exclude PATH...` records the return plan's keep/exclude decisions, so a model no longer hand-edits `return-plan.md`. `plan-return` now prints the tally, every undecided path and the exact command (and keeps the decisions already recorded for the same path on a fresh plan), a blocked `return` names the undecided paths and the verb on its first line, and a stale plan names `plan-return` as the next step.
