---
bump: patch
---
An inline implement step that changed no file since it began starts no step review. Its Proof still runs as the gate.
ShipLoop records the tree the step ended at beside the tree it began from, and the Improve checkpoint compares the two.
Every implement-step review's `passes.md` also records, without applying it, what the IMP-4 trigger would have done:
review only the first step of the item's current plan, and only a change to code or test files.
