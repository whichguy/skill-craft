---
bump: minor
---

One commit path for every ShipLoop commit (knowledge home, the integrate item
commit, `improve-commit`, the empty-repository baseline): it stages exactly the
named paths, leaves any text file that looks like it holds a credential
uncommitted and names it (never its value), and uses the configured identity or
else the workspace identity. The knowledge-home commit gains that fallback.
ShipLoop now also commits `docs/shiploop/` after any accepted stage that changed
it (not only at the four closes), with the same credential and requirement-ID
checks; packets tell the model not to commit it itself.
