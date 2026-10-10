---
bump: minor
---
Test and quality loops now allow 11 refused runs per action (was 7) before `done` is no longer accepted, and a
check may fail after 7 genuine fix attempts (was 3) before the stage reports revise. The keepalive's
no-progress release follows at 22 continuations (twice the refused-run cap).
