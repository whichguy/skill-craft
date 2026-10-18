---
bump: minor
---
ShipLoop's Improve children follow Improve's own stop rule again, the one the bundled Until Loop runtime (upstream 0.10.0, vendored unchanged) applies: a review ends after two consecutive trivial passes, or after a first pass that is trivial and leaves the workspace unchanged. The one-unchanged-pass rule and its stricter gate for code reviews, which earlier notes on this line announced, do not ship.
- Every Improve child starts at `required_trivial_reviews: 2` with the two-pass exit and repeat conditions, whatever stage it reviews; its contract lists no `candidate_paths`.
- The import takes the last two review files, or the one review of an unchanged first pass, and reads the runtime's `trivial_streak` and `unchanged_first_pass`; the change gate and the restart route key on an unchanged first pass.
- The Improve handoff's pass and evidence lines, and the README and Improve-stage reference, say the same.
