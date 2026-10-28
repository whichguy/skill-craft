---
bump: minor
---
The step exit criteria's stopping rule is a criterion, not a count: a step reports send-back when the same check
still fails in the same way after a genuine fix, and the fix taught nothing new about why. It replaces "the same check
still fails after 7 genuine fix attempts".
- The implement duty, implement's and each step's Until Loop Repeat condition, the chain step contract, the skill
  card, test-loop.md, parallel-chain.md and execution-planning.md say so; `shiploop_stage_spec.STUCK_FIX` holds the
  wording and `GENUINE_FIX_ATTEMPTS` is gone.
- The E2E SPEC's S-10 carve-out is amended: no count remains. Owner, 2026-10-28, in line with their 2026-10-11 rule
  "I want the thing achieved, I don't care how many loops".
- New end-to-end tests check what the model receives: the rule in the rendered implement packet and in the Until
  Loop's own instruction, and the stop hook naming a real loop's commands and the step's own callback.
