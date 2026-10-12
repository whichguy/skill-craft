---
bump: patch
---
On a ShipLoop Improve stage the child is already started: ShipLoop writes the opening and starts the runtime at the
transition. The skill continues the child from its receipt and never writes the opening or runs `improve-start`.
Lessons and a revised result go to the Improve stage's `complete` (`--notes`, `--final-result`).
