---
bump: patch
---
- The spec and plan packets now tell the host to start a Backchain child with Backchain's own commands: `prepare --run` the new "Backchain planning run directory" line (`<run>/backchain/<action>/run`), then `freeze`, which writes the child's start contract. Earlier packets told the host to write that contract by hand, which Backchain 0.7.0 does itself. The resource block lists `backchain/scripts/backchain.py`.
- `--backchain-passes converge` now means Backchain's default gate: the child completes at its first trivial review, and the request carries no `Backchain passes:` line (owner decision, 2026-11-01). Since Backchain 0.7.0 the converge text said "two consecutive trivial reviews", but its marker line never reached a printed packet, so converge runs already ran that gate.
