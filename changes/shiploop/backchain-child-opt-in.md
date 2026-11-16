---
bump: minor
---
New runs call no Backchain child by default. `--backchain-passes` now defaults to `none`, and `none` offers no Backchain child at any stage: no whole `plan`/`draft`, no read-only `review`/`audit` and no `repair`/`revise`. The planning guide's dependency audit and the record-only `backchain-check` stay. Opt in at `init` or `workspace start` with `--backchain-passes one` (one review/fix/check cycle) or `converge` (Backchain's default gate); both behave as before. Basis: the 2026-11-15 value study found no meaningful plan-quality edge for Backchain on Grok 4.6 xhigh, Sol 6.1 medium or Sonnet 5.5 high, at 10-15 times the tokens. `--planning-review none` in a default run now leaves the plan with no model-run second look.
