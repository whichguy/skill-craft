---
bump: minor
---
The keepalive stop hook asks for `shiploop next` again; the owed-report wording added in 1.18.0 is gone.
- A refused stop says "run `next` and follow the packet it prints", as before 1.18.0. `next` reprints the step's
  packet, which carries its Until Loop commands and its callback.
- `hook-status` no longer has `loop`, `callback` or `delegation`.
- Kept from 1.18.0: each reported Until Loop iteration counts as progress (`progress` is `<revision>.<callback
  attempts>.<loop iteration>`), and running `next` re-binds the run without wiping the stop's memory.
- Why: in the phase A E2E round on DeepSeek flash, both texts got the loop reported in 6 of 6 cleared steps with
  nothing redone, and the owed text took more commands. The round's two real early stops came where no loop was open,
  so the owed text would have printed the generic sentence anyway (test/shiploop_e2e/LEARNINGS.md, 2026-10-28).
