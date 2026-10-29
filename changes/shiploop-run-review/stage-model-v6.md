---
bump: minor
---
Runs of ShipLoop's 7-stage inner loop (no verify stage, state version 10) read as stage model v6, with 7 phases and the
engine's current catalog. Saved 8-stage runs (state versions 5 to 9, or a verify visit) still read as v5 from the frozen
`defaults/stages-v5.json` catalog, phases and phase texts, and 17-stage runs as v4.
