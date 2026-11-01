---
bump: patch
---
Step-plan's proof bullet now says ShipLoop reruns a step's Proof at the step's done, so the Proof must be safe to repeat: a Proof
that creates state (a permission-set assignment, a record written to a data file) checks for it first or works on its own state.
