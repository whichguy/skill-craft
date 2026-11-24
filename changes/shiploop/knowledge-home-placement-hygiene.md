---
bump: patch
---
Allow optional standing `## Delivery` headings in `docs/shiploop/environment.md` without false-positive placement notices (preserving `SECTIONS` compatibility alongside `## Release and promotion`) and emit a non-refusing placement notice when durable `docs/shiploop/` files introduce transient `.shiploop-runs/`, `.shiploop-improve/`, or `/tmp/shiploop-` paths.
