---
bump: patch
---
A test runner recorded as suite `check` is still counted: when a check command's output shows a runner summary, the record carries the counts and a zero-test run is refused (`no-tests`) instead of passing on its exit code. The test-strategy duty now asks for a capability probe of a host-dependent tool (for a browser, load a local page and read its title back, not the version) and for a failed probe to be recorded as an access gap with the requirement it leaves unobserved.
