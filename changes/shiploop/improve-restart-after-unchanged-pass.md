---
bump: patch
---
A completed Improve child that ended on one unchanged trivial pass, with files changed after its bind, now restarts
through `improve-start --restart-stopped`. Before this change, `improve-complete` refused it and told the model to "run
the loop's next review", but that loop was already complete and `--restart-stopped` refused any child that was not
stopped. The run had no route forward and paused (live node-add-route slice, 2026-10-11). The refusal's first line now
ends with the restart command. A test runs that command through the real CLI.
