---
bump: patch
---
At system-test, the check that sends a run back when its default suite shows a host-dependent case no longer runs or reads a regression command that tests a hosted runtime (a command a platform card lists under Remote tests, or one aimed at a target that keeps state). That runtime is the project's own default, so the host-dependent mark on its cases is true and was only costing a send-back loop. A regression command that runs locally is still checked for the marked cases, so an optional host tool in the default suite is still refused.
