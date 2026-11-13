---
bump: minor
---
Step-plan refuses a test command recorded `focused` that only searches text (`grep`, `rg` and their kin). A focused
command must print test IDs and counts for the test stage, which a search cannot, so it used to fail only later. Record
such a command with suite `check`.
