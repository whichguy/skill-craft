---
bump: minor
---
New `shiploop backchain-check --candidate PATH`: checks a Backchain candidate plan against Backchain's seven structural invariants (a Python port of Backchain's reference validator, packaged first) and records a receipt and a snapshot under the run's `backchain/<action>/`. Backchain stages tell the host to run it after each candidate revision and to treat a failure as a loop finding; nothing is refused.
