---
bump: patch
---
A chain step that needed a retry no longer blocks the chain from finishing. The retried attempt's Ask-Agent workspace is still kept as evidence (never deleted); `chain finish` now completes and lists it under `retained_superseded` instead of refusing forever.
