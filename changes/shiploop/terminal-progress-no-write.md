---
bump: patch
---
Printing a done or halted run's packet no longer starts the progress observer. The observer had written
`.progress.lock` and refreshed `context-index.md` in a run folder that a terminal recovery must leave unchanged.
