---
bump: minor
---
Default `shiploop-drive` model routing to prelude-only planning (`intake`..`prepare` plus prelude `improve` reviews on the planning profile, with a single switch to the execution profile at `step-plan` through `handoff`) to maximize prompt cache hits, and add an opt-in `--plan-reflect-and-improve` flag (and `plan_reflect_and_improve` routing config key, off by default) to also route `reflect-and-revise` and all `improve` stages to the planning profile.
