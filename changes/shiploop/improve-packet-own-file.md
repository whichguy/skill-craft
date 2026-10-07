---
bump: patch
---
A packet printed while an Improve child owns the action is now written to `packets/<action>-improve.md`; the producer packet stays at `packets/<action>.md`. Before, the child's packet overwrote the producer's at the same path, so after a run the producer packet of every reviewed planning stage (spec, test-strategy, plan, step-plan, test-spec) could not be audited (10 of 46 visits in one real run).
