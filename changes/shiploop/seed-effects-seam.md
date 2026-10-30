---
bump: patch
---
Internal change, no change to what a run does. The work ShipLoop's scripts do once a stage's gates have passed (the entry checks of the stage the run moves to, saving the state, the step, skill and knowledge commits, the step's iteration record) now lives in one function, `accept_effects`, which a producer's `complete`, an Improve import and the control commands call. Each does what it did before, in the same order. The function exists so a test harness can seed a run with those same effects instead of a copy of them. A hermetic test holds the seam and `complete` to the sequence they replaced: the same state, files and commits.
