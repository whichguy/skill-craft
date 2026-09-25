---
bump: minor
---
`static-checks` now runs a quality loop on the Until Loop bound to the selected
Improve card. ShipLoop writes the loop contract. Each iteration traces every
changed public entry point with a valid, a boundary and an invalid input, then
reviews the change against the new *Code craft* rubric: argument checks,
contract docstrings, and comments that are useful rather than token-wasting.
The loop ends after an iteration with only trivial findings, and a third
iteration that still finds a material issue stops it. The stage accepts `done`
only with a terminal packet that matches the contract; `repeat` is no longer
accepted there.
- The *Code craft* rubric replaces the implementation constitution. Step plans
  gain an argument-check/docstring criterion, test specs gain rejection cases,
  `verify` checks the loop's entry-point inventory, and the end-of-work Improve
  reviews against the same rubric.
- The change inventory (tracked and untracked files since the item base) is
  recorded in every lint mode; `lint: off` still stops linters and auto-fix.
- Fixed: the lint snapshot failed when the run directory sat inside the
  checkout and was git-ignored.
