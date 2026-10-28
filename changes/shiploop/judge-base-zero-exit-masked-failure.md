---
bump: patch
---
The base-run judge (`_judge_base`'s no-ids path) no longer calls a command
"passes-on-base" when it exits 0 but its own output reports a failed test —
the same wrapper-swallowed-exit masking that `judge()` was fixed against is
now also closed here, so a genuinely discriminating test is correctly
reported `red` instead of being told it does not detect the change.
