---
bump: patch
---
On the Ask-Agent route, ShipLoop now writes the Improve child's contract and
starts the child itself, as it already did on the inline route. The parent
writes the opening and runs `improve-start`. The improve-agent worker then
continues the started child from the receipt's `next_argv`; it no longer
hand-builds the contract or copies the binding line.

A stopped child restarts with `improve-start --restart-stopped` on both
routes. The frozen contract lists the `host-owner.md` owner record for a
delegated child.
