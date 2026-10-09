---
bump: patch
---
The Run Review export now carries four more records the E2E harness writes: how the harness classed the ending (PASS, FAILED, BLOCKED
or STOPPED, with its grounds), the build under test (plugin hash, prompt hash, host build, with the harness's reason for any it could not
measure), the environment (tools, browser, and the other runs that shared the machine while this one ran), and, for a run that did not
pass, how many of its checks pass in the worktree it never returned. Each is absent for a run exported from before the harness wrote it.
