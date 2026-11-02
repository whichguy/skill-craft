---
bump: minor
---
- `finish` with a caller packet reports converged planning only on a final review whose source review is complete; an incomplete one is an incomplete result with its next action. The review's `planning_gaps` and `execution_blockers` must be lists of strings, so a missing or misshapen list no longer reads as "no gap" or crashes.
- Legacy elaboration of an inherited plan now refuses a changed `goal`, a changed step `origin`, and a new `initial_state` fact that closes a need the inherited plan left open (the silent inv-7 repair). Other added facts are reported.
- New `export --run DIR`: exports only the plan a finished run converged on, and refuses a run that did not converge or whose plan changed after `finish`. `finish` now prints this command. `export PLAN` is unchanged.
