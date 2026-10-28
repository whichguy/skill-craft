---
bump: minor
---
The keepalive stop hook now asks for the report the run is owed, and its "no progress" release works as documented.
- While the step's Until Loop is active, a refused stop names its next iteration report (the receipt's read-only
  `next_argv`) and says to report finished work, or report it unresolved with the gap. Once a stage's loop has ended,
  it names the step's exact `complete` callback. Otherwise, and always under `delegation: ask-agent`, it keeps
  "run `next`". Every reason also names `next` for a model that lost context.
- Each reported iteration of a stage's Until Loop now counts as progress, as an Improve review's pass already did, so a
  model that reports iterations is never released as idle.
- Running `next` re-binds the run but no longer wipes the stop's memory. Before, the refusal's own advice reset the
  release, so a model that only ran `next` between stops was never let go (docs/shiploop-owed-outcome-evidence/
  rebind_repro.out).
- `hook-status` adds `loop`, `callback` and `delegation`; its `progress` is `<revision>.<callback attempts>.<loop
  iteration>`. The unused binding key `last_block_rev` is gone.
- No limit changed: background-task waits, the Grok continuation cap and `shiploop-drive` behave as before.
