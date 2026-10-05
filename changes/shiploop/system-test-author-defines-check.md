---
bump: patch
---
The packet for the stage that records the whole-product test commands (system-test-author) now says which suite a command belongs in: a command that is not a test runner (a shell pipeline, a grep, a curl probe) is suite `check`, judged by its exit code, and `focused` and `regression` are for runners whose output ShipLoop can count. Before, the stage named the three suites without defining `check`, so a shell pipeline recorded as `focused` was refused at system-test ("could not read how many tests it ran") and could only be repaired by a replan.
