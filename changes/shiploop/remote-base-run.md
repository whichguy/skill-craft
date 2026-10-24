---
bump: patch
---
- **Base run on a hosted target:** the test stage's base run no longer runs a command that a platform card lists under
  Remote tests. Such a command tests a deployed target, which already holds the item's change, so a new test passed
  there and was refused for no fault of its own. Running it also deployed the base's files. The record names the card
  and the reason, and the candidate runs still judge the tests. When every command is remote, the base run records
  skipped, as the mutation check does.
