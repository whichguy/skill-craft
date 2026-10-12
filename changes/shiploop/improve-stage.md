---
bump: minor
---
Improve is now a stage of its own in ShipLoop's sequence (owner, 2026-10-11). After each reviewed stage, the run
issues an `improve` action with its own id. Its packet says to run the improve skill on the result, then run
`complete --action=<improve id>`.
- **ShipLoop sets the review up at the transition.** It binds the card, writes the opening from the run's state,
  freezes the contract and starts the runtime. The model never writes the opening or starts the child.
- **`complete` imports the review.** `improve-complete` is removed; its `--notes`, `--final-result` and
  `--no-commit` flags are on `complete`.
- **`improve-start` only restarts** a stopped or refused review, with `--restart-stopped`.
- **Other Improve commands** (`improve-bind`, `improve-commit`, `improve-reconcile`) take the Improve stage's id.
- **The packet file** is `packets/<improve id>.md`. The status block and the dry run show `improve` as its own step.
- **Duplicate reviews are refused.** `complete` refuses a review that repeats another Improve stage's review in the
  same run. In the 2.1.0 live run, a model-written script faked three of four reviews from one template.
- **Old runs are refused.** A run whose Improve child predates this change cannot be resumed; start a fresh run.
