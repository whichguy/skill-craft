---
bump: patch
---
Test-strategy's `test_layers` and `targets` have one size bound again: their printed lines together (1,200
characters). The per-field limits are gone: code 60, harness 80, reason 160, target 60, base_state_route 240.
- The printed lines are what the step-plan head carries, and the combined bound already keeps them inside the host's
  output cut. A single long field is accepted while the lines fit.
- Why: in the phase A E2E round the per-field limits refused 6 fields (for example a 61-character target and a
  293-character base_state_route). Each cost a rewrite and a resubmit, and none protected the head
  (test/shiploop_e2e/LEARNINGS.md, 2026-10-28).
