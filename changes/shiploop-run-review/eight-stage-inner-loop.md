---
bump: minor
---
Run Review follows ShipLoop's 8-stage inner loop (step-plan, test-spec, validate-existing, implement, test, document,
verify, carry-forward). The phases are now Understand, Specify, Plan, Build, Verify, Carry forward, System test and
Release; `defaults/stages.json` is regenerated (every inner stage ends on its Until Loop's `loop-terminal`, and the
catalog accepts implement's `improve: step`); `delivered.skill.assessed` comes from the last carry-forward visit. The
removed stage names stay only in a read-only alias table so saved evidence of older runs still places each visit in the
phase of the stage that replaced it.
