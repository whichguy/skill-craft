---
bump: minor
---
At `release-verify`, a consumer check that is a test command the run recorded (with or without `NAME=value` settings in front of it) must now run at least as many tests as the work area's latest accepted run of that command, with a count ShipLoop can read. A check that skips or lacks tests the work area ran is refused, with two exits: `add-work` to make the tests run where a consumer runs them, or `send-back` to have `release-plan` record a narrower check by its own command. The packet shows each such check's floor.
