---
bump: minor
---
Test and quality loops now allow 11 refused runs per action (was 7) before `done` is no longer accepted, and a
check may fail after 7 genuine fix attempts (was 3) before the stage reports revise. The keepalive's
no-progress release follows at 22 continuations (twice the refused-run cap).
The fix-attempt rule is now the constant `shiploop_stage_spec.GENUINE_FIX_ATTEMPTS`, and a test pins every prose copy
of the three caps to their constants; the static-checks paragraph of SKILL.md now says the 11th refused run.
