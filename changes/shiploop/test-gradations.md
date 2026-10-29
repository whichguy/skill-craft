---
bump: minor
---
Each step runs graded tests instead of the whole regression every time (design T section 9.1 2d).
- A step plan's regression command may carry `"minimum": true`. That minimum regression, a fast suite that shows
  nothing basic broke, runs at every step. An unmarked regression command, the full regression, runs only at the
  item's last step, so no earlier step runs an exhaustive regression.
- A plan of two or more steps with test commands marks one regression command minimum, or gives `minimum_na` with the
  reason it has none. The refusal names both routes.
- Each step's test stage runs its own cases in detail, every earlier step's cases and the minimum regression. A step
  before the last that owes nothing runs no command, and its packet says why.
- The test packet names the full regression it leaves to the last step, and asks where each new test belongs: a new
  suite, the minimum suite or the full suites. It says that an MCP server or skill may test the new code in more
  detail, beside the unit and mock tests, once the model has checked this host offers it.
