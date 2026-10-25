---
bump: patch
---
- The lint pass resolves each catalogued linter's matched files, marker and tool once per pass instead of once
  per phase: `_discover`'s fix-apply and report phases previously each re-checked the marker file and re-walked
  `PATH` for every row, even though neither changes within one pass. No behavior change.
