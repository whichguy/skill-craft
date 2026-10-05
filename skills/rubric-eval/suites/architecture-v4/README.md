# architecture-v4

Suite architecture-v3 with the overbuild correction of 2026-09-27: criterion P3 (scope) and the overbuilt anchor no longer count an addition that makes a stated requirement work, or that correctness, security, data integrity or failure visibility demands, as overbuilding. Evidence: the value audit found 13 of 16 judge overbuilt flags in round 4 were such additions. Scenario overbuild notes (the owner's proportionality line) are unchanged.


Grades architecture plans for web products on hosted runtimes. The criteria,
grade anchors, composite groups and guardrails are in `rubric.json`; the
scenarios (each with an expected tier, applicable criteria and an overbuild
note), tiers and environments are in `scenarios.json`. `frames/plan.txt` wraps
an arm's text around a scenario for plan-stage experiments; `frames/review.txt`
wraps a review focus around an existing plan. The rubric's human-readable form
and its history live in the repository's `docs/shiploop-architecture-rubric.md`.
