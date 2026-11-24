---
bump: patch
---
Allow optional standing `## Delivery` and `## Release` headings in `docs/shiploop/environment.md` without false-positive placement notices (preserving `SECTIONS` compatibility) and emit a non-refusing placement notice when durable `docs/shiploop/` files introduce transient `.shiploop-runs/`, `.shiploop-improve/`, or `/tmp/shiploop-` paths.
