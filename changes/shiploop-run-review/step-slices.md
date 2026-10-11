---
bump: patch
---
Run Review reads a step slice (`test/shiploop_e2e/slice.py`, which writes `slice-result.json` instead of `result.json`) as a slice: the run document has `kind: "slice"` and a `slice` record (work item, stop, stage at the stop, the not-reached sentence); a slice that reached its stop is `finished`, a cleared or otherwise ended one `stopped`; its outcome is PASS or FAILED naming the failing verdicts; the stages the harness seeded read seeded, not skipped; system tests and release read "not reached (slice)"; the return, the release, the quality phase and outer-stage refusals are not measured with a reason that names the slice. The page and facts.md say "step slice", and a slice is compared only with other slices. Whole runs export exactly as before.
