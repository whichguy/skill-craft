---
bump: minor
---
Add `--delegation agents` hybrid portable-agents mode alongside `inline` (default) and legacy `ask-agent`: keeps the core SDLC build loop inline, dispatches Improve reviews directly via ShipLoop-written `CHILD/worker-brief.md` (forked for planning/outer reviews where supported with fresh fallback, fresh for `document` and `carry-forward` code reviews), adds optional F17 read-only fan-out in `discovery`, `research`, and `product-acceptance` with emit-time 2-line host hints from `host-bindings/v2`, keeps Claude Code's `PostToolUse(Skill)` gate active on `agents`, adds `--review-mode` provenance to `complete` and `passes.md`, and exposes read-only `shiploop host-binding`.
