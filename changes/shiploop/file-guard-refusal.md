---
bump: minor
---
- **A file guard is refused at step-plan:** a done step plan is refused when a focused command checks for a file
  (`test`, `[` or `[[` with `-e`, `-f`, `-d` or `-s`; `ls`; `stat`) or prints a path before its tests run. A `test`
  that compares values is a test, not a guard. On the item's base that
  guard fails on the missing file and prints its own message, so it fakes RED. The refusal says to run the tests
  directly: a test of new code that fails to load on the base is a real failure, and ShipLoop reads it.
- **The red placeholder states the bar:** a test case's `red` asks for the assertion that fails on the base because the
  behaviour is missing, not because a file is.
