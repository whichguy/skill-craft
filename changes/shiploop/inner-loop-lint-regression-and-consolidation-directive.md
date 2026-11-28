---
bump: patch
---
Gate inner-loop `shiploop lint` on base-compared new regressions elsewhere in changed files (`new_elsewhere`, e.g. newly orphaned imports/variables), add a Tier-0 check for newly shadowed top-level Python definitions, and instruct `implement`, `test`, and `IMPLEMENT_STEP_REVIEW_FOCUS` to clear new file-wide lint regressions and consolidate duplicate helpers within scope.
