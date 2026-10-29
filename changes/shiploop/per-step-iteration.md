---
bump: minor
---
Each inline step is built, tested, documented and reviewed before the next step starts (design T section 8, a pilot).
- Each step runs implement, test and document, then its Improve review; the next step's implement follows. Before,
  every step was implemented first and the item was tested and documented once.
- The test stage builds out the step's part of the test spec. A case is due at the last step that lists its
  criterion. The focused command runs the cases due so far, earlier steps' included; a check runs from the last step
  its criteria are due at; the regression command runs at every step. RED applies only to the cases new at the step,
  against the step's base.
- Rule `item` moves from implement to document: one review per step covers its code, its tests and its docs, and
  leaves its edits uncommitted. When it changed a file, ShipLoop reruns the step's focused command at import. A step
  that changed no file starts no review. This replaces the wide-item rule.
- ShipLoop commits each step once its document stage and review are accepted. The next step's lint, mutation check,
  base check, document's left-out rule and review diff start from that commit. The item ends at carry-forward:
  verify is retired, and its checks run inside each step (see the verify-retired note).
- Each step's iteration (number, base and commit) is recorded in `RUN/iterations/<item>.json`.
