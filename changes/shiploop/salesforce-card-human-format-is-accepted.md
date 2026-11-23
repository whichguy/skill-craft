---
bump: patch
---
The Salesforce platform guide no longer says that a focused `sf apex run test` command in the default or `--result-format human` format is refused as unread. ShipLoop accepts such a command when it exits 0 and its output names every listed test ID; it does not read each test's outcome or a test count from that format, so only the exit code catches a failed test. The guide still says to record the command with `--result-format tap`, whose `ok` and `not ok` lines ShipLoop reads and counts.
