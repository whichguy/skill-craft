---
bump: minor
---
- **Step commits:** on the inline route ShipLoop commits each accepted implement step, before its Improve stage
  starts, as `feat(<item>/<step>): <headline>`. The message carries the step's summary and sections Key learnings,
  Key decisions, Evidence and Related commits.
  - An implement result's `learned` and `decisions` are required there, each a list of lines (`["none"]` allowed,
    1,200 characters each).
  - `learned_from` names the commits whose learnings the step used; each must be reachable from HEAD.
  - Each inline implement packet quotes the last two commits that are not ShipLoop records as its look-back,
    after the other quoted blocks.
  - Verify's item commit takes what changed after the last step.
