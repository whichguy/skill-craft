---
bump: minor
---
The step-plan template now gives each step a countable size: at most 4 criteria and 3 product files (a file that only
describes another changed file counts with it; tests, docs and the step's own proof script do not). More than that, a
second module or layer, two separately confirmable behaviours or two outcomes joined with "and" make another step.
Each step's `paths` now name every file it changes. On a remote-only target the steps share one proof script, so a
split costs one more run, not a new script. The unused `STEP_SIZING` constant, an older copy of the sizing rule, is
removed.
