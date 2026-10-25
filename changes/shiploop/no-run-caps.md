---
bump: minor
---
ShipLoop no longer stops work on a count or a clock (owner, 2026-10-24: no artificially imposed limits):
- No refused-run cap: `done` is judged on every submission however many runs were refused (was 11), and the packet
  still shows the tally. The test stage's remedy opens without a loop receipt only after a run that could not run.
- No send-back cap: a work item or an outer target can be sent back any number of times (was 2); `revisions` still
  counts them, and packets say "send-back N" instead of "N of 2".
- No keepalive release after 22 continuations without an accepted result; Grok's own 8-continuation turn cap stays.
- No whole-run time budget for the test stage (was 1,800 s), the mutation check (600 s) or the lint pass (120 s), and
  no 200-file lint cap: every command, mutant and changed file runs. Each command keeps its own hang guard.
