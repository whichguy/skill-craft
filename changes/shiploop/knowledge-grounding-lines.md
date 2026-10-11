---
bump: minor
---
Packets now carry the knowledge home's architecture and spec-retire lines.

- **Every inner packet** names its grounding files by absolute path: living spec, feature spec, environment,
  architecture and test strategy (`knowledge_home.grounding`). A missing or blank file is left out, and nothing is
  printed when there are none.
- **plan and step-plan** say what architecture.md holds (`ARCHITECTURE_HOLDS`).
  - Keep every AD-<n> ID, and move a decision that no longer holds under '## Superseded'.
  - Name credential handling without secret values.
  - plan records each structural choice as the next AD-<n>; step-plan adds one for a structural decision and cites
    it.
- **prepare** writes a missing architecture.md from the plan.
- **The spec duty** numbers requirements R-<n> only: a structural choice is an AD-<n> in architecture.md.
- **spec, plan and step-plan** state that a change to docs/shiploop/ losing an R-<n> or AD-<n> ID is refused.
- **The plan packet** asks plan.md to begin with the living-spec pin (`Spec: docs/shiploop/spec.md @ <sha12>`).
- **The handoff packet** states when ShipLoop retires the feature spec.
- **The stages that write the home's README** link the feature list, not a feature spec.
- **The stages from intake through plan** name earlier features.
