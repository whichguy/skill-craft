---
bump: minor
---
- **Concern map:** a done plan maps fifteen SDLC concerns for every work item: UI, API, messaging, state, migration
  before and after release, switchover, concurrency, platform services, scale, security, observability, configuration,
  performance and accessibility.
  - A concern that applies gets its decision, an anchor and the stage that owns it; one that does not gets a reason.
  - The step plan maps each applicable concern it owns to the steps that deliver it. Its packet prints the plan's
    applicable rows, and its template names them.
  - Step-plan duty 9's free-text plan record is shorter: the concern rows replace the bullets they covered.
  - `complete` refuses a plan with a missing or unknown row, and a step plan that leaves an owned concern unmapped.
