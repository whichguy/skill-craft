---
bump: minor
---
An Improve child whose first review is trivial and leaves the candidate unchanged now completes after that one pass. The import accepts a receipt with that single review when the terminal packet reports `unchanged_first_pass`, and cross-checks the claim against the tree ShipLoop recorded at `improve-bind`. Packets explain the one-pass case.
