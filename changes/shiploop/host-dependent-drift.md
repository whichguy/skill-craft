---
bump: minor
---
A system command row may be marked `"host_dependent": true` (its cases need a host tool: a browser, a device, an account, a service). At `system-test` ShipLoop then also runs the accepted regression commands and refuses when any of that row's `ids` is shown, run or failed, in their output, with the remedy to give the case its own opt-in command or make it skip unless an opt-in setting is present. The system-test-author duty and SKILL.md say so. This is the script check behind the settled-fact line from the earlier test-strategy change: a delivered repo's plain `node --test` that needed macOS Chrome passed every gate.
