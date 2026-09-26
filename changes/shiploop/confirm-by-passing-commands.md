---
bump: minor
---
A completion criterion is now confirmed only by a command ShipLoop runs and sees pass. A done
`step-plan` lists its `criteria` and names, in each test command's `criteria`, the ones that command
confirms; an uncovered criterion is refused. A new `check` command kind (judged by exit code) covers
content with no test runner, such as a README that must document a flag. `verify` reruns every
recorded command. `system-test-author` must record `system_commands` and `release-plan`
`consumer_checks` (or an empty list with the reason); ShipLoop runs them when `system-test` and
`release-verify` report done and refuses unless each passes.
