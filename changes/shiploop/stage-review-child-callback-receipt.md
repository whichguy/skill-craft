---
bump: patch
---
- **Improve stage, review and child:** a result now "starts an Improve stage" (the `improve` action with its own id),
  the work that stage does is the Improve review, and "Improve child" names only the Until Loop child runtime (its
  contract, state and CHILD folder: bound, active, stopped, restarted). The schedule sentences in navigator.md,
  run-options.md, improve-stages.md, the command cards, the planning-review refusals and `--planning-review`'s help say
  stage or review; the glossary defines all three and a retired-term row keeps "starts an Improve child" out.
- **Callback:** refusals say "run the same callback again" (not "the same complete command"), and the loop texts, the
  Improve handoff, the parent return, SKILL.md and the agent card say "the callback". The CLI verb is still
  `complete`.
- **Print marker and receipt:** every print now ends with `=== end ShipLoop print ===` (it was
  `=== end ShipLoop head ===`, which also ended whole packets). The Until Loop's record (an inner stage's `loops/<action>-terminal.json`, an
  Improve child's `CHILD/packet.json`) is its receipt, never a "terminal packet", and what the runtime prints at each
  step is an instruction, so "packet" means only what ShipLoop prints for a stage. The loop refusals ("no receipt
  exists at ..."), the Until Loop block's follow and receipt lines, the Done-when line and the child's `child receipt`
  resource say so.
