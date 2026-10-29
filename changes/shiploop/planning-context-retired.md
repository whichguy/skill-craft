---
bump: patch
---
The read-only planning-context collector (`shiploop_planning_context`) is removed: it existed to bind planning material into ShipLoop's
implementation chain, which is retired, and nothing else read it. Its suites go with it (`shiploop-planning-context`,
`shiploop-v4-consumers`).
