---
bump: minor
---
Run Review follows ShipLoop's 8-stage inner loop (step-plan, test-spec, validate-existing, implement, test, document,
verify, carry-forward). The phases are now Understand, Specify, Plan, Build, Verify, Carry forward, System test and
Release; `defaults/stages.json` is regenerated (every inner stage ends on its Until Loop's `loop-terminal`, and the
catalog accepts implement's `improve: step`); an 8-stage run's `delivered.skill.assessed` comes from the last carry-forward
visit. A saved 17-stage run is read with its own frozen catalog and phases (see the stage-models note).
