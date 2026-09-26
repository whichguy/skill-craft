---
bump: minor
---
A recorded test command now passes only when it ran tests. ShipLoop reads the runner's summary (Jest, Vitest, pytest, unittest, Mocha, cargo, go, dotnet) and refuses a command that exits 0 after running no test, fewer than `min_tests`, or without showing each of its `ids`. A filter that matches nothing, such as `npm test -- -t <name>` printing "2 skipped", no longer counts as green. Step-plan test commands accept optional `ids` and `min_tests`. `test-red` is now script-checked too: the focused commands must fail inside a test, not before any test runs. Characterisation tests that already pass declare `red_na`.
