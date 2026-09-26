---
bump: minor
---
A fixable problem is no longer reported as `blocked`. When a work item's goal proves wrong or
unachievable while it is being built (test-spec through integration-verify), the stage reports
the new outcome `revise`: the item goes back to `step-plan` with that result as evidence, at most
twice per item, and then the user decides. A script-run test or quality loop that uses all its
iterations, or three refused test runs, now routes to `revise`; a loop cancelled before its limit
is refused, because a user's stop is `pause`. `blocked` stays for what only the user, an access
grant or an outside dependency can resolve. Saved runs from earlier versions are refused; start a
fresh run.
